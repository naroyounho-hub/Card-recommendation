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
RETRIEVER_TOP_K = 15
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

⚠️ 중요 규칙:
- 반드시 신용카드 정확히 3장, 체크카드 정확히 3장을 포함하세요.
- **반드시 위 [참고할 카드 정보]에 있는 카드만 추천하세요.** 참고 카드 정보에 없는 카드는 절대 추천하지 마세요.
- card_name은 참고 카드 정보에 있는 카드명을 정확히 그대로 사용하세요. 임의로 변경하거나 축약하지 마세요.
- 6장 미만으로 응답하지 마세요.
- 사용자가 여성이거나 외국인(유학생 포함)인 경우, 나라사랑카드(군인 전용 카드)는 절대 추천하지 마세요.

반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 절대 포함하지 마세요.
신용카드 3개를 먼저, 그 다음 체크카드 3개 순서로 총 6개 객체를 포함하는 JSON 배열:
각 객체 형식: {{{{ "card_name": "카드명", "card_company": "카드사명", "card_type": "신용"|"체크", "reason": "이 사용자에게 추천하는 이유", "monthly_saving": "약 X만원", "benefits_summary": ["혜택1", "혜택2", "혜택3"] }}}}"""

BASE_PROMPT_TEMPLATE = """{{system_prompt}}

사용자 정보:
{persona}

사용자의 소비 패턴과 니즈를 분석하여 가장 적합한 카드 3장을 추천해주세요."""

CHAT_SYSTEM_PROMPT = """당신은 카드 추천 전문가 AI 어시스턴트입니다.
사용자의 소비 패턴과 라이프스타일을 깊이 분석하여 최적의 카드를 추천합니다.

규칙:
- 사용자가 소비 패턴이나 카드 관련 질문을 하면, 아래 [참고 카드 정보]를 활용하여 구체적으로 답변하세요.
- 추천 시 카드명, 카드사, 추천 이유, 예상 절약 금액을 포함하세요.
- 후속 질문(예: "더 저렴한 카드는?", "체크카드로는?")에도 대화 맥락을 유지하며 답변하세요.
- 카드와 무관한 질문에는 정중히 카드 추천 관련 대화로 안내하세요.
- 친절하고 전문적인 톤을 유지하세요."""

# API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
