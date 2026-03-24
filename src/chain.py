import json as json_module

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import config
from src.embedding import create_documents, get_embedding_model
from src.vectorstore import load_vectorstore, build_and_save
from src.retriever import get_advanced_retriever, get_base_retriever

# config에서 프롬프트 템플릿 로드 (프롬프트 엔지니어링은 config.py에서)
def _build_prompt(template_str: str) -> ChatPromptTemplate:
    """config의 프롬프트 템플릿에 시스템 프롬프트를 주입하여 ChatPromptTemplate 생성"""
    filled = template_str.replace("{{system_prompt}}", config.SYSTEM_PROMPT)
    return ChatPromptTemplate.from_template(filled)

RECOMMEND_PROMPT = _build_prompt(config.RECOMMEND_PROMPT_TEMPLATE)
STRUCTURED_PROMPT = _build_prompt(config.STRUCTURED_PROMPT_TEMPLATE)


def _truncate_by_tokens(text: str, enc, max_tokens: int) -> str:
    """텍스트를 max_tokens 이하로 자르기"""
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens]) + "..."


def format_docs(docs, max_docs: int = 10, max_tokens_per_doc: int = 3000) -> str:
    """Document 리스트를 프롬프트용 텍스트로 포맷팅 (토큰 제한 적용)

    검색은 benefits 기반이지만, LLM에는 metadata의 detail_description을 합쳐서 전달.
    카드당 전체 텍스트를 max_tokens_per_doc으로 제한하여 토큰 폭발 방지.
    """
    import tiktoken
    enc = tiktoken.encoding_for_model(config.LLM_MODEL_NAME)
    result = []
    total_tokens = 0
    for doc in docs[:max_docs]:
        detail = doc.metadata.get("detail_description", "")
        full_text = doc.page_content
        if detail:
            full_text += f"\n상세설명: {detail}"
        # 카드당 토큰 제한 (page_content에 detail이 이미 포함된 경우도 방어)
        full_text = _truncate_by_tokens(full_text, enc, max_tokens_per_doc)
        doc_tokens = len(enc.encode(full_text))
        if total_tokens + doc_tokens > config.MAX_CONTEXT_TOKENS:
            break
        result.append(full_text)
        total_tokens += doc_tokens
    # 최종 안전장치: 전체 컨텍스트도 토큰 제한
    final = "\n\n---\n\n".join(result)
    return _truncate_by_tokens(final, enc, config.MAX_CONTEXT_TOKENS)


def extract_source_cards(docs) -> list[dict]:
    """Document metadata에서 카드 정보 추출"""
    seen = set()
    cards = []
    for doc in docs:
        name = doc.metadata.get("card_name", "")
        if name and name not in seen:
            seen.add(name)
            cards.append({
                "card_name": name,
                "card_company": doc.metadata.get("card_company", ""),
                "card_type": doc.metadata.get("card_type", ""),
                "image_url": doc.metadata.get("image_url", ""),
                "card_url": doc.metadata.get("card_url", ""),
            })
    return cards


def _get_llm(streaming: bool = False):
    return ChatOpenAI(
        model=config.LLM_MODEL_NAME,
        temperature=config.LLM_TEMPERATURE,
        streaming=streaming,
    )


def _load_retriever_and_docs():
    """retriever와 documents를 로드. 인덱스가 없으면 자동 빌드."""
    documents = create_documents()
    try:
        vectorstore = load_vectorstore()
    except Exception:
        vectorstore = build_and_save()
    retriever = get_advanced_retriever(vectorstore, documents)
    return retriever, documents


def get_recommendation(persona_text: str) -> dict:
    """메인 인터페이스: 페르소나 텍스트 → 추천 결과"""
    retriever, _ = _load_retriever_and_docs()

    docs = retriever.invoke(persona_text)
    context = format_docs(docs)
    source_cards = extract_source_cards(docs)

    llm = _get_llm()
    chain = RECOMMEND_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "persona": persona_text})

    return {"answer": answer, "source_cards": source_cards}


def get_recommendation_stream(persona_text: str):
    """스트리밍 버전: 토큰 단위로 yield + source_cards 반환"""
    retriever, _ = _load_retriever_and_docs()

    docs = retriever.invoke(persona_text)
    context = format_docs(docs)
    source_cards = extract_source_cards(docs)

    llm = _get_llm(streaming=True)
    chain = RECOMMEND_PROMPT | llm | StrOutputParser()

    def stream_generator():
        for chunk in chain.stream({"context": context, "persona": persona_text}):
            yield chunk

    return stream_generator(), source_cards


def get_structured_recommendation(persona_text: str) -> dict:
    """구조화된 추천: JSON 형태로 카드별 추천 이유와 절약 금액 반환"""
    retriever, _ = _load_retriever_and_docs()

    docs = retriever.invoke(persona_text)
    context = format_docs(docs)
    source_cards = extract_source_cards(docs)

    llm = _get_llm()
    chain = STRUCTURED_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"context": context, "persona": persona_text})

    try:
        recommendations = json_module.loads(raw)
    except json_module.JSONDecodeError:
        # JSON 파싱 실패 시 ```json ... ``` 블록 추출 시도
        import re
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            recommendations = json_module.loads(match.group())
        else:
            recommendations = []

    # source_cards의 image_url, card_url, card_type을 recommendations에 병합
    source_map = {c["card_name"]: c for c in source_cards}
    for rec in recommendations:
        src = source_map.get(rec.get("card_name"), {})
        rec["image_url"] = src.get("image_url", "")
        rec["card_url"] = src.get("card_url", "")
        # card_type이 LLM 응답에 없으면 source에서 가져오기
        if not rec.get("card_type"):
            rec["card_type"] = src.get("card_type", "신용")

    return {"recommendations": recommendations, "source_cards": source_cards}


def get_chat_stream(user_message: str, chat_history: list[dict]):
    """대화형 스트리밍: 대화 히스토리 + RAG 검색 결과를 반영하여 스트리밍 응답 생성

    Args:
        user_message: 현재 사용자 메시지
        chat_history: [{"role": "user"|"assistant", "content": "..."}, ...]

    Returns:
        (stream_generator, source_cards)
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    retriever, _ = _load_retriever_and_docs()
    docs = retriever.invoke(user_message)
    context = format_docs(docs)
    source_cards = extract_source_cards(docs)

    # 메시지 구성: 시스템 → 히스토리(최근 6턴) → 현재 질문(카드 컨텍스트 포함)
    messages = [SystemMessage(content=config.CHAT_SYSTEM_PROMPT)]

    # 히스토리는 최근 6턴(12메시지)만, 각 메시지 500토큰 제한
    import tiktoken
    enc = tiktoken.encoding_for_model(config.LLM_MODEL_NAME)
    for msg in chat_history[-12:]:
        content = _truncate_by_tokens(msg["content"], enc, 500)
        if msg["role"] == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))

    # 현재 질문에 검색된 카드 정보를 함께 전달
    current_prompt = f"""[참고 카드 정보]
{context}

[사용자 질문]
{user_message}"""
    messages.append(HumanMessage(content=current_prompt))

    llm = _get_llm(streaming=True)

    def stream_generator():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    return stream_generator(), source_cards


def get_base_response(persona_text: str) -> str:
    """평가용: RAG 없이 GPT에 직접 질문"""
    prompt = _build_prompt(config.BASE_PROMPT_TEMPLATE)
    llm = _get_llm()
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"persona": persona_text})
