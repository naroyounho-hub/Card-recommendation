# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

사용자 맞춤 카드 상품 추천 대화형 AI — RAG (Retrieval-Augmented Generation) 파이프라인 기반.
크롤링된 카드 데이터를 임베딩하여 FAISS Vector DB에 저장하고, 사용자 페르소나/질문에 맞는 카드를 검색 후 GPT로 추천 응답을 생성한다.

## Environment

- Windows 10 Pro, Python 3.13
- API keys: `.env` 파일에 `OPENAI_API_KEY` 저장, `python-dotenv`로 로드

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# Streamlit 앱 실행
streamlit run app.py
```

## Architecture

**RAG 파이프라인 흐름:**
1. **데이터 전처리** (`src/embedding.py`) — 크롤링 JSON → LangChain Document 객체 (카드 단위 chunking)
2. **벡터 DB** (`src/vectorstore.py`) — FAISS 인덱스 생성/저장/로드 (`data/vectordb/`)
3. **검색** (`src/retriever.py`) — Hybrid Search (BM25 + Vector EnsembleRetriever), Multi-Query Retriever
4. **추천 체인** (`src/chain.py`) — LCEL 체인: retriever → 프롬프트 → GPT → 파싱
5. **프론트엔드** (`app.py`) — Streamlit UI, stream 출력 지원

**핵심 기술 스택:** LangChain, FAISS, sentence-transformers (`jhgan/ko-sroberta-multitask`), OpenAI GPT, BM25 (rank-bm25)

**데이터 흐름:**
- 원본 크롤링 데이터: `data/raw/` (JSON, 카드고릴라 기반)
- 전처리 결과: `data/processed/`
- FAISS 인덱스: `data/vectordb/faiss_index`

**외부 인터페이스:**
```python
def get_recommendation(persona_text: str) -> dict:
    # Returns: {"answer": str, "source_cards": [{"card_name", "image_url", "card_url"}, ...]}
```

## Key Design Decisions

- **카드 단위 chunking**: 카드 데이터 특성상 각 카드를 하나의 Document로 구성 (혜택 상세가 긴 경우에만 Semantic Chunking 고려)
- **임베딩 모델**: `jhgan/ko-sroberta-multitask` (한국어 특화, 무료) 메인 사용, OpenAI 임베딩은 비교용
- **Hybrid Search 가중치**: BM25 0.4 / Vector 0.6 기본값, 튜닝 필요
- **평가용 Base 모델 함수 분리**: RAG 없는 직접 GPT 응답(`get_base_response`)과 RAG 응답(`get_rag_response`)을 분리하여 비교 평가 지원

## 언어

사용자는 한국어를 사용한다. 코드 주석과 UI 텍스트에 한국어가 포함된다.
