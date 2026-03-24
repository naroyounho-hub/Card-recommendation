import json
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

import config
from src.utils import validate_card_data

_embedding_model = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """임베딩 모델 싱글톤 로드"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL_NAME
        )
    return _embedding_model


def load_card_data(json_path: str = None) -> list[dict]:
    """JSON 파일에서 카드 데이터 로드"""
    if json_path is None:
        json_path = config.CARD_DATA_FILE

    with open(json_path, "r", encoding="utf-8") as f:
        cards = json.load(f)

    valid_cards = []
    for card in cards:
        if validate_card_data(card):
            valid_cards.append(card)
        else:
            print(f"[WARNING] 필수 필드 누락 - 스킵: {card.get('card_name', 'unknown')}")

    return valid_cards


def _parse_categories(categories) -> list[str]:
    """benefit_categories를 리스트로 변환 (문자열 '|' 구분 또는 리스트 모두 지원)"""
    if isinstance(categories, list):
        return categories
    if isinstance(categories, str):
        return [c.strip() for c in categories.split("|") if c.strip()]
    return []


def card_to_document(card: dict) -> Document:
    """단일 카드 dict → LangChain Document 변환

    검색용 page_content에는 benefits(간결)만 포함하여 검색 정확도를 높이고,
    LLM 컨텍스트용 detail_description은 metadata에 저장하여 응답 시 활용.
    """
    categories = _parse_categories(card['benefit_categories'])

    # 검색용: benefits 중심 (임베딩 품질 ↑, 토큰 절약)
    page_content = (
        f"카드명: {card['card_name']}\n"
        f"카드사: {card['card_company']}\n"
        f"카드종류: {card['card_type']}\n"
        f"연회비: {card['annual_fee']}\n"
        f"주요혜택: {card['benefits']}\n"
        f"혜택 카테고리: {', '.join(categories)}"
    )

    metadata = {
        "card_name": card["card_name"],
        "card_type": card["card_type"],
        "card_company": card["card_company"],
        "annual_fee": card.get("annual_fee", ""),
        "benefit_categories": categories,
        "detail_description": card.get("detail_description", ""),
        "image_url": card.get("image_url", ""),
        "card_url": card.get("card_url", ""),
    }

    return Document(page_content=page_content, metadata=metadata)


def create_documents(json_path: str = None) -> list[Document]:
    """전체 파이프라인: JSON 로드 → Document 리스트 반환"""
    cards = load_card_data(json_path)
    return [card_to_document(card) for card in cards]
