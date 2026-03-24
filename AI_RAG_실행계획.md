# AI/RAG 파트 주간 실행 계획 (황윤호)

> 프로젝트: 사용자 맞춤 카드 상품 자율 추천 대화형 AI
> 기간: 2026.03.23(월) ~ 2026.03.30(월) 발표
> 역할: 임베딩 생성, FAISS Vector DB 구축, 검색 로직, Multi-query/Hybrid search, GPT 연결

---

## 전체 타임라인 요약

| 일자 | 요일 | 핵심 목표 | 산출물 |
|------|------|-----------|--------|
| 3/23 | 월 | 환경 세팅 + 파이프라인 뼈대 | 프로젝트 구조, 의존성 설치 |
| 3/24 | 화 | 데이터 전처리 + 임베딩 생성 | chunked 문서, 임베딩 벡터 |
| 3/25 | 수 | FAISS Vector DB 구축 + 기본 검색 | FAISS 인덱스 파일, 기본 retriever |
| 3/26 | 목 | 고도화 (Multi-query + Hybrid Search) | 고도화된 retriever |
| 3/27 | 금 | GPT 연결 + 추천 체인 완성 | 전체 RAG 체인 동작 |
| 3/28 | 토 | 프론트 연동 + 통합 테스트 | Streamlit 연동 완료 |
| 3/29 | 일 | 평가 지원 + 버그 수정 + 발표 준비 | 최종 안정화 |

---

## Day 1 — 3/23(월): 환경 세팅 + 파이프라인 뼈대

### 할 일
- [ ] 프로젝트 폴더 구조 생성
- [ ] 필수 라이브러리 설치 및 `requirements.txt` 작성
- [ ] `.env` 파일에 OpenAI API 키 세팅
- [ ] 박민아님에게 크롤링 데이터 형식 협의 (필수 필드 요청)
- [ ] 파이프라인 뼈대 코드 작성 (빈 함수 껍데기)

### 필수 라이브러리
```
openai
langchain
langchain-openai
langchain-community
faiss-cpu
sentence-transformers
rank-bm25
tiktoken
python-dotenv
```

### 크롤링 데이터에 요청할 필수 필드
```json
{
  "card_name": "카드명",
  "card_type": "신용/체크",
  "card_company": "카드사",
  "annual_fee": "연회비",
  "benefits": "주요 혜택 (텍스트)",
  "benefit_categories": ["교통", "편의점", "쇼핑", ...],
  "detail_description": "상세 설명 전문",
  "image_url": "카드 이미지 URL",
  "card_url": "카드고릴라 상세 페이지 URL"
}
```

### 프로젝트 구조 (제안)
```
card-recommend-ai/
├── data/
│   ├── raw/              # 크롤링 원본 데이터
│   ├── processed/        # 전처리된 데이터
│   └── vectordb/         # FAISS 인덱스 저장
├── src/
│   ├── embedding.py      # 임베딩 생성 모듈
│   ├── vectorstore.py    # FAISS DB 구축/관리
│   ├── retriever.py      # 검색 로직 (기본/고도화)
│   ├── chain.py          # GPT 연결 RAG 체인
│   └── utils.py          # 유틸리티 함수
├── app.py                # Streamlit 앱 (프론트 담당 연동)
├── config.py             # 설정 관리
├── requirements.txt
├── .env
└── README.md
```

---

## Day 2 — 3/24(화): 데이터 전처리 + 임베딩 생성

### 전제: 박민아님 크롤링 데이터 수령

### 할 일
- [ ] 크롤링 데이터 품질 확인 (결측치, 이상치)
- [ ] 카드별 Document 객체 생성 (LangChain Document 포맷)
- [ ] Chunking 전략 결정 및 구현
- [ ] 임베딩 모델 선정 및 임베딩 벡터 생성

### Chunking 전략
카드 데이터 특성상 **카드 단위 chunking**이 적합:
```python
# 각 카드를 하나의 Document로 구성
Document(
    page_content=f"""
    카드명: {card_name}
    카드사: {card_company}
    카드종류: {card_type}
    연회비: {annual_fee}
    주요혜택: {benefits}
    상세설명: {detail_description}
    """,
    metadata={
        "card_name": card_name,
        "image_url": image_url,
        "card_url": card_url,
        "card_type": card_type,
        "card_company": card_company,
        "benefit_categories": benefit_categories
    }
)
```

### 임베딩 모델 옵션
| 모델 | 장점 | 단점 |
|------|------|------|
| `text-embedding-3-small` (OpenAI) | 고성능, 간편 | 비용 발생 |
| `jhgan/ko-sroberta-multitask` (HuggingFace) | 무료, 한국어 특화 | 로컬 리소스 필요 |
| `intfloat/multilingual-e5-large` | 다국어 우수 | 무거움 |

**권장**: 평가 시 HuggingFace 오픈소스 모델도 필요하므로, `jhgan/ko-sroberta-multitask`를 메인으로 사용하고 OpenAI 임베딩은 비교용으로 활용

---

## Day 3 — 3/25(수): FAISS Vector DB 구축 + 기본 검색

### 할 일
- [ ] FAISS 인덱스 생성 및 저장
- [ ] 기본 유사도 검색 (similarity search) 구현
- [ ] top-k 파라미터 실험 (k=3, 5, 7)
- [ ] 검색 결과 확인 및 디버깅

### FAISS 구축 핵심 코드 흐름
```python
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. 임베딩 모델 로드
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask"
)

# 2. FAISS 인덱스 생성
vectorstore = FAISS.from_documents(documents, embeddings)

# 3. 저장
vectorstore.save_local("data/vectordb/faiss_index")

# 4. 기본 검색 테스트
results = vectorstore.similarity_search("대중교통 할인 많은 카드", k=5)
```

### metadata 활용 포인트
- 검색 결과에서 `image_url`을 꺼내 프론트에 전달 → 카드 이미지 출력
- `card_url`로 원본 페이지 링크 제공

---

## Day 4 — 3/26(목): 고도화 — Multi-query + Hybrid Search ⭐

> 프로젝트 가이드에서 "수업 중 배우지 않은 고도화 기법 2가지 이상" 요구

### 고도화 기법 1: Multi-Query Retriever
사용자 질문을 여러 관점으로 재구성하여 검색 범위를 넓힘

```python
from langchain.retrievers.multi_query import MultiQueryRetriever

multi_retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
)
# "교통비 아끼고 싶어요" →
#   "대중교통 할인 카드", "버스 지하철 적립 카드", "통근 혜택 카드" 등으로 변환
```

### 고도화 기법 2: Hybrid Search (BM25 + Vector)
키워드 기반 검색(BM25)과 의미 기반 검색(Vector)을 결합

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 retriever
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 5

# Vector retriever
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 앙상블 (가중치 조절 가능)
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6]  # 의미 검색에 더 높은 가중치
)
```

### (보너스) 고도화 기법 3: Semantic Chunking
문서가 길 경우 의미 단위로 자동 분할 — 카드 데이터는 이미 카드 단위이므로, 혜택 상세 설명이 길 경우에만 적용

### 할 일
- [ ] Multi-Query Retriever 구현 및 테스트
- [ ] BM25 Retriever 구현
- [ ] EnsembleRetriever로 Hybrid Search 구현
- [ ] 기본 검색 vs 고도화 검색 결과 비교
- [ ] 가중치(weights) 튜닝

---

## Day 5 — 3/27(금): GPT 연결 + 추천 체인 완성

### 할 일
- [ ] 추천용 프롬프트 템플릿 작성 (배형선님과 협업)
- [ ] RetrievalQA 또는 LCEL 체인 구성
- [ ] 페르소나 기반 추천 테스트
- [ ] 응답에 카드 이미지 URL + 추천 사유 포함되도록 설계
- [ ] stream 출력 지원 구현

### RAG 체인 핵심 구조
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 프롬프트 (배형선님과 협의하여 완성)
prompt = ChatPromptTemplate.from_template("""
당신은 카드 추천 전문가입니다.

사용자 정보:
{persona}

참고할 카드 정보:
{context}

사용자의 소비 패턴과 니즈를 분석하여 가장 적합한 카드 3장을 추천해주세요.
각 카드에 대해 다음을 포함하세요:
1. 카드명과 카드사
2. 이 사용자에게 추천하는 구체적인 이유
3. 예상 월 절약 금액 (가능한 경우)

추천 사유는 사용자의 소비 패턴과 연결하여 논리적으로 설명해주세요.
""")

# 체인 구성
chain = (
    {
        "context": ensemble_retriever | format_docs,
        "persona": RunnablePassthrough()
    }
    | prompt
    | ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, streaming=True)
    | StrOutputParser()
)
```

### 프론트 연동 인터페이스 (류희준님에게 전달)
```python
def get_recommendation(persona_text: str) -> dict:
    """
    Returns:
        {
            "answer": "추천 결과 텍스트",
            "source_cards": [
                {"card_name": "...", "image_url": "...", "card_url": "..."},
                ...
            ]
        }
    """
```

---

## Day 6 — 3/28(토): 프론트 연동 + 통합 테스트

### 할 일
- [ ] Streamlit 앱과 RAG 체인 연동 (류희준님과 협업)
- [ ] stream 출력 동작 확인
- [ ] 카드 이미지 출력 확인
- [ ] 5개 페르소나 전체 테스트
- [ ] 엣지 케이스 확인 (빈 입력, 관련 없는 질문 등)
- [ ] Moderation API 적용 확인

---

## Day 7 — 3/29(일): 평가 지원 + 최종 안정화

### 할 일
- [ ] Code Based Evaluation용 임베딩 유사도 함수 제공
- [ ] Base 모델 vs 고도화 모델 비교 데이터 생성
- [ ] 평가 자동화 스크립트 지원
- [ ] 발표 자료용 RAG 파이프라인 다이어그램 제작
- [ ] 최종 버그 수정

### 평가에 필요한 기능 (류희준님에게 제공)
```python
# 1. Base 모델 응답 (RAG 없이)
def get_base_response(persona_text: str) -> str:
    """GPT-3.5에 직접 질문 (검색 증강 없음)"""

# 2. 고도화 모델 응답 (RAG 적용)
def get_rag_response(persona_text: str) -> str:
    """RAG 체인을 통한 추천"""

# 3. 임베딩 유사도 계산
def compute_similarity(text1: str, text2: str) -> float:
    """HuggingFace 임베딩으로 코사인 유사도 계산"""
```

---

## 핵심 협업 포인트

| 누구와 | 언제 | 내용 |
|--------|------|------|
| 박민아 (데이터) | Day 1~2 | 크롤링 데이터 형식 협의, 데이터 수령 |
| 배형선 (프롬프트) | Day 4~5 | 추천 프롬프트 공동 설계 |
| 류희준 (프론트+평가) | Day 5~7 | API 인터페이스 전달, 평가 함수 제공 |

---

## 리스크 & 대응

| 리스크 | 대응 방안 |
|--------|-----------|
| 크롤링 데이터 지연 | Day 1에 샘플 데이터 직접 5~10개 만들어서 파이프라인 먼저 개발 |
| 임베딩 품질 저하 | 여러 모델 비교 실험, chunking 방식 조정 |
| 검색 정확도 부족 | weights 튜닝, metadata 필터링 추가 |
| GPT 응답 불안정 | 프롬프트 개선, temperature 조절, Few-shot 예시 추가 |
