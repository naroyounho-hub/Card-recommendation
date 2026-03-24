import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 경로
BASE_DIR = Path(__file__).parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
CARD_DATA_FILE = BASE_DIR / "cards_data_cut.json"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
# FAISS는 한글 경로를 지원하지 않으므로 영문 경로 사용
VECTORDB_DIR = Path.home() / ".card_recommend_ai" / "vectordb"
FAISS_INDEX_PATH = VECTORDB_DIR / "faiss_index"

# 임베딩 모델
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"

# LLM
LLM_MODEL_NAME = "gpt-3.5-turbo"
LLM_TEMPERATURE = 0.3

# 컨텍스트 제한 (토큰 수)
MAX_CONTEXT_TOKENS = 8000

# 검색 파라미터
RETRIEVER_TOP_K = 5
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6

# 시스템 프롬프트 (프롬프트 엔지니어링 영역)
SYSTEM_PROMPT = """당신은 카드 추천 전문가입니다.
사용자의 소비 패턴과 라이프스타일을 깊이 분석하여 최적의 카드를 추천합니다.
추천 시 반드시 사용자의 구체적인 소비 습관과 연결하여 논리적으로 설명해주세요."""

RECOMMEND_PROMPT_TEMPLATE = """{{system_prompt}}

사용자 정보:
{persona}

참고할 카드 정보:
{context}

사용자의 소비 패턴과 니즈를 분석하여 가장 적합한 카드 3장을 추천해주세요.
각 카드에 대해 다음을 포함하세요:
1. 카드명과 카드사
2. 이 사용자에게 추천하는 구체적인 이유
3. 예상 월 절약 금액 (가능한 경우)

추천 사유는 사용자의 소비 패턴과 연결하여 논리적으로 설명해주세요."""

STRUCTURED_PROMPT_TEMPLATE = """{{system_prompt}}

사용자 정보:
{persona}

참고할 카드 정보:
{context}

사용자의 소비 패턴과 니즈를 분석하여 **신용카드 3장**과 **체크카드 3장**, 총 6장을 추천해주세요.
반드시 신용카드와 체크카드를 각각 3장씩 포함해야 합니다.

반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 절대 포함하지 마세요:
[
  {{{{
    "card_name": "카드명",
    "card_company": "카드사",
    "card_type": "신용 또는 체크",
    "reason": "이 사용자에게 추천하는 구체적인 이유 (소비 패턴과 연결하여 3~4문장으로 설명)",
    "monthly_saving": "예상 월 절약 금액 (예: 약 15,000원)",
    "benefits_summary": ["주요 혜택 1 (예: 온라인 쇼핑 10% 할인)", "주요 혜택 2", "주요 혜택 3"]
  }}}}
]"""

BASE_PROMPT_TEMPLATE = """{{system_prompt}}

사용자 정보:
{persona}

사용자의 소비 패턴과 니즈를 분석하여 가장 적합한 카드 3장을 추천해주세요."""

# API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
