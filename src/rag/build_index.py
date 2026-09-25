from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import COLLECTION_NAME, EMBEDDING_MODEL_NAME, VECTOR_STORE_DIR
from knowledge_loader import load_all_chunks


def get_embedding_model():
    """Modelo de embeddings open-source, multilingüe, corre local en CPU.
    Justificación completa en Docs/taller2_fase1_componentes.md."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def build_index(reset=False):
    """Carga los 3 documentos de la base de conocimiento, los trocea y los
    indexa (embeddings + metadatos) en una colección persistente de ChromaDB."""
    embeddings = get_embedding_model()

    if reset and VECTOR_STORE_DIR.exists():
        import shutil

        shutil.rmtree(VECTOR_STORE_DIR)

    chunks = load_all_chunks()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(VECTOR_STORE_DIR),
    )
    return vector_store, len(chunks)


def load_index():
    """Abre la colección ya persistida sin volver a embeber los documentos."""
    embeddings = get_embedding_model()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_STORE_DIR),
    )


if __name__ == "__main__":
    _, total_chunks = build_index(reset=True)
    print(f"Índice construido en {VECTOR_STORE_DIR} con {total_chunks} chunks.")
