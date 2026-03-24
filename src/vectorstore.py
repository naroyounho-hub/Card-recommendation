from pathlib import Path
from langchain_community.vectorstores import FAISS

import config
from src.embedding import create_documents, get_embedding_model


def create_vectorstore(documents, embedding_model=None) -> FAISS:
    """Document 리스트 + 임베딩 모델 → FAISS 벡터스토어 생성"""
    if embedding_model is None:
        embedding_model = get_embedding_model()
    return FAISS.from_documents(documents, embedding_model)


def save_vectorstore(vectorstore: FAISS, path=None) -> None:
    """FAISS 인덱스를 디스크에 저장"""
    if path is None:
        path = str(config.FAISS_INDEX_PATH)
    Path(path).mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(path)
    print(f"[INFO] FAISS 인덱스 저장 완료: {path}")


def load_vectorstore(embedding_model=None, path=None) -> FAISS:
    """저장된 FAISS 인덱스 로드"""
    if embedding_model is None:
        embedding_model = get_embedding_model()
    if path is None:
        path = str(config.FAISS_INDEX_PATH)
    return FAISS.load_local(
        path, embedding_model, allow_dangerous_deserialization=True
    )


def build_and_save(json_path=None) -> FAISS:
    """편의 함수: JSON → Documents → FAISS 생성 → 저장 → 반환"""
    documents = create_documents(json_path)
    print(f"[INFO] {len(documents)}개 카드 Document 생성 완료")

    embedding_model = get_embedding_model()
    vectorstore = create_vectorstore(documents, embedding_model)
    save_vectorstore(vectorstore)

    return vectorstore
