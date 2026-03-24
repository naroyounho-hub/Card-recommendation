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


def format_docs(docs, max_docs: int = 10) -> str:
    """Document 리스트를 프롬프트용 텍스트로 포맷팅 (토큰 제한 적용)"""
    import tiktoken
    enc = tiktoken.encoding_for_model(config.LLM_MODEL_NAME)
    result = []
    total_tokens = 0
    for doc in docs[:max_docs]:
        doc_tokens = len(enc.encode(doc.page_content))
        if total_tokens + doc_tokens > config.MAX_CONTEXT_TOKENS:
            break
        result.append(doc.page_content)
        total_tokens += doc_tokens
    return "\n\n---\n\n".join(result)


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


def get_base_response(persona_text: str) -> str:
    """평가용: RAG 없이 GPT에 직접 질문"""
    prompt = _build_prompt(config.BASE_PROMPT_TEMPLATE)
    llm = _get_llm()
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"persona": persona_text})
