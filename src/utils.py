import numpy as np
import tiktoken


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """tiktoken으로 토큰 수 카운트"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def compute_similarity(text1: str, text2: str, embedding_model=None) -> float:
    """두 텍스트 간 코사인 유사도 계산 (평가용)"""
    if embedding_model is None:
        from src.embedding import get_embedding_model
        embedding_model = get_embedding_model()

    vec1 = embedding_model.embed_query(text1)
    vec2 = embedding_model.embed_query(text2)

    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


REQUIRED_CARD_FIELDS = [
    "card_name", "card_type", "card_company", "annual_fee",
    "benefits", "benefit_categories", "detail_description"
]


def validate_card_data(card: dict) -> bool:
    """카드 데이터 필수 필드 존재 여부 검증"""
    for field in REQUIRED_CARD_FIELDS:
        if field not in card or not card[field]:
            return False
    return True
