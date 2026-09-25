from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

KNOWLEDGE_BASE_DIR = BASE_DIR / "Data" / "knowledge_base"
POLICY_FILE = KNOWLEDGE_BASE_DIR / "politica_devoluciones.md"
FAQ_FILE = KNOWLEDGE_BASE_DIR / "preguntas_frecuentes.json"
CATALOG_FILE = KNOWLEDGE_BASE_DIR / "catalogo_productos.csv"

ORDERS_FILE = BASE_DIR / "Data" / "orders.json"

VECTOR_STORE_DIR = BASE_DIR / "Data" / "vector_store"
COLLECTION_NAME = "ecomarket_knowledge_base"

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

OLLAMA_MODEL = "llama3.2:1b"
OLLAMA_BASE_URL = "http://localhost:11434"

RETRIEVER_TOP_K = 5
