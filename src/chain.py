import json as json_module
import re
import tiktoken

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import config
from src.embedding import create_documents, get_embedding_model
from src.vectorstore import load_vectorstore, build_and_save
from src.retriever import get_advanced_retriever

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


def format_docs(docs, max_docs: int = 15, max_tokens_per_doc: int = 3000) -> str:
    """Document 리스트를 프롬프트용 텍스트로 포맷팅 (토큰 제한 적용)

    검색은 benefits 기반이지만, LLM에는 metadata의 detail_description을 합쳐서 전달.
    카드당 전체 텍스트를 max_tokens_per_doc으로 제한하여 토큰 폭발 방지.
    """
    enc = tiktoken.encoding_for_model(config.LLM_MODEL_NAME)
    result = []
    total_tokens = 0
    for i, doc in enumerate(docs[:max_docs], 1):
        detail = doc.metadata.get("detail_description", "")
        full_text = f"[카드 {i}]\n{doc.page_content}"
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


# 모듈 레벨 singleton 캐싱 — 매 요청마다 JSON 재로딩 방지
_cached_retriever = None
_cached_docs = None


def _load_retriever_and_docs():
    """retriever와 documents를 로드. 인덱스가 없으면 자동 빌드. 결과는 캐싱."""
    global _cached_retriever, _cached_docs
    if _cached_retriever is not None:
        return _cached_retriever, _cached_docs
    documents = create_documents()
    try:
        vectorstore = load_vectorstore()
    except Exception:
        vectorstore = build_and_save()
    retriever = get_advanced_retriever(vectorstore, documents)
    _cached_retriever = retriever
    _cached_docs = documents
    return _cached_retriever, _cached_docs


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


_FEMALE_KEYWORDS = {"여성", "여자", "여학생", "여배우"}
_FOREIGN_KEYWORDS = {"외국인", "유학생", "중국", "일본", "미국", "베트남", "태국", "필리핀", "인도네시아", "몽골", "러시아", "프랑스", "독일", "영국", "캐나다", "호주"}


def _is_female_or_foreigner(persona_text: str) -> bool:
    """페르소나 텍스트에서 여성 또는 외국인 여부 감지"""
    return any(kw in persona_text for kw in _FEMALE_KEYWORDS | _FOREIGN_KEYWORDS)


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
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            recommendations = json_module.loads(match.group())
        else:
            recommendations = []

    # source_cards에서 카드명 매칭 (정확 → 부분 → 카드사+타입 매칭)
    def _find_source(rec, source_cards, used_names):
        rec_name = rec.get("card_name", "")
        rec_company = rec.get("card_company", "")
        rec_type = rec.get("card_type", "")
        if not rec_name:
            return {}
        # 1단계: 정확 매칭
        for sc in source_cards:
            if sc["card_name"] == rec_name and sc["card_name"] not in used_names:
                return sc
        # 2단계: 부분 매칭
        for sc in source_cards:
            if sc["card_name"] not in used_names:
                if rec_name in sc["card_name"] or sc["card_name"] in rec_name:
                    return sc
        # 3단계: 카드사 + 카드타입 매칭 (LLM이 일반적 이름을 쓴 경우)
        if rec_company:
            for sc in source_cards:
                if sc["card_name"] not in used_names:
                    sc_type = sc.get("card_type", "")
                    if rec_company in sc.get("card_company", "") or sc.get("card_company", "") in rec_company:
                        if ("체크" in rec_type) == ("체크" in sc_type):
                            return sc
        return {}

    used_names = set()
    for rec in recommendations:
        src = _find_source(rec, source_cards, used_names)
        if src:
            used_names.add(src["card_name"])
        if not rec.get("image_url"):
            rec["image_url"] = src.get("image_url", "")
        if not rec.get("card_url"):
            rec["card_url"] = src.get("card_url", "")
        # 매칭된 source가 있으면 카드명도 정확한 이름으로 교정
        if src and src.get("card_name"):
            rec["card_name"] = src["card_name"]
        # card_type 정규화: "체크"가 포함되면 체크, 아니면 신용
        ct = str(rec.get("card_type") or src.get("card_type") or "신용")
        rec["card_type"] = "체크" if "체크" in ct else "신용"

    # 매칭 안 된 카드는 같은 타입의 source 카드로 대체
    for rec in recommendations:
        if not rec.get("image_url"):
            rec_type = rec.get("card_type", "신용")
            for sc in source_cards:
                if sc["card_name"] not in used_names:
                    sc_type = sc.get("card_type", "")
                    if ("체크" in rec_type) == ("체크" in sc_type):
                        used_names.add(sc["card_name"])
                        rec["card_name"] = sc["card_name"]
                        rec["card_company"] = sc.get("card_company", "")
                        rec["image_url"] = sc.get("image_url", "")
                        rec["card_url"] = sc.get("card_url", "")
                        break

    # 여성/외국인에게 나라사랑카드 추천 금지: 해당 카드 제거 후 source_cards에서 대체
    if _is_female_or_foreigner(persona_text):
        filtered = []
        for rec in recommendations:
            if "나라사랑" in rec.get("card_name", ""):
                rec_type = rec.get("card_type", "체크")
                replaced = False
                for sc in source_cards:
                    if sc["card_name"] not in used_names and "나라사랑" not in sc["card_name"]:
                        sc_type = sc.get("card_type", "")
                        if ("체크" in rec_type) == ("체크" in sc_type):
                            used_names.add(sc["card_name"])
                            rec = {
                                "card_name": sc["card_name"],
                                "card_company": sc.get("card_company", ""),
                                "card_type": rec_type,
                                "reason": rec.get("reason", ""),
                                "monthly_saving": rec.get("monthly_saving", ""),
                                "benefits_summary": rec.get("benefits_summary", []),
                                "image_url": sc.get("image_url", ""),
                                "card_url": sc.get("card_url", ""),
                            }
                            replaced = True
                            break
                if not replaced:
                    # 대체 카드가 없으면 그냥 제외
                    continue
            filtered.append(rec)
        recommendations = filtered

    # 신용 3장 / 체크 3장 보장: 부족하면 상대쪽에서 재분류
    credit = [r for r in recommendations if r["card_type"] == "신용"]
    check = [r for r in recommendations if r["card_type"] == "체크"]
    while len(credit) > 3 and len(check) < 3:
        moved = credit.pop()
        moved["card_type"] = "체크"
        check.append(moved)
    while len(check) > 3 and len(credit) < 3:
        moved = check.pop()
        moved["card_type"] = "신용"
        credit.append(moved)
    recommendations = credit[:3] + check[:3]

    return {"recommendations": recommendations, "source_cards": source_cards}


def get_chat_stream(user_message: str, chat_history: list[dict]):
    """대화형 스트리밍: 대화 히스토리 + RAG 검색 결과를 반영하여 스트리밍 응답 생성

    Args:
        user_message: 현재 사용자 메시지
        chat_history: [{"role": "user"|"assistant", "content": "..."}, ...]

    Returns:
        (stream_generator, source_cards)
    """
    retriever, _ = _load_retriever_and_docs()
    docs = retriever.invoke(user_message)
    context = format_docs(docs)
    source_cards = extract_source_cards(docs)

    # 메시지 구성: 시스템 → 히스토리(최근 6턴) → 현재 질문(카드 컨텍스트 포함)
    messages = [SystemMessage(content=config.CHAT_SYSTEM_PROMPT)]

    # 히스토리는 최근 6턴(12메시지)만, 각 메시지 500토큰 제한
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
