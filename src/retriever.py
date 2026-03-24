from langchain_openai import ChatOpenAI
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

import config


def get_base_retriever(vectorstore, k: int = None):
    """기본 유사도 검색 retriever"""
    if k is None:
        k = config.RETRIEVER_TOP_K
    return vectorstore.as_retriever(search_kwargs={"k": k})


def get_bm25_retriever(documents, k: int = None) -> BM25Retriever:
    """BM25 키워드 기반 retriever"""
    if k is None:
        k = config.RETRIEVER_TOP_K
    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = k
    return bm25


def get_hybrid_retriever(vectorstore, documents, bm25_weight=None, vector_weight=None):
    """Hybrid Search: BM25 + Vector 앙상블 retriever"""
    if bm25_weight is None:
        bm25_weight = config.BM25_WEIGHT
    if vector_weight is None:
        vector_weight = config.VECTOR_WEIGHT

    bm25 = get_bm25_retriever(documents)
    vector = get_base_retriever(vectorstore)

    return EnsembleRetriever(
        retrievers=[bm25, vector],
        weights=[bm25_weight, vector_weight],
    )


def get_multiquery_retriever(base_retriever, llm=None):
    """Multi-Query Retriever: 질문을 여러 관점으로 재구성하여 검색"""
    if llm is None:
        llm = ChatOpenAI(
            model=config.LLM_MODEL_NAME,
            temperature=0.3,
        )
    return MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )


def get_advanced_retriever(vectorstore, documents):
    """최종 고도화 retriever: Hybrid → Multi-Query 래핑"""
    hybrid = get_hybrid_retriever(vectorstore, documents)
    return get_multiquery_retriever(hybrid)
