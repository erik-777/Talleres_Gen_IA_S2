from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import OllamaLLM

from build_index import load_index
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, RETRIEVER_TOP_K

RAG_PROMPT = ChatPromptTemplate.from_template(
    """Eres un agente de atención al cliente de EcoMarket. Usa el CONTEXTO para
responder la PREGUNTA del cliente en español, de forma breve y profesional.

CONTEXTO:
{context}

PREGUNTA: {question}

Si el CONTEXTO tiene la respuesta, respóndela citando el dato exacto (precio,
regla de la política, etc.). Solo si el CONTEXTO no tiene ninguna relación con
la pregunta, responde: "No tengo información suficiente, contacta a soporte
humano."

RESPUESTA:"""
)

# Distancia L2 máxima aceptable entre la pregunta y el chunk más cercano
# (calibrada empíricamente: preguntas relevantes caen en ~6-17, preguntas
# fuera de dominio como "¿cuál es la capital de Francia?" caen en ~40+).
# Por encima de este umbral se considera que la base de conocimiento no
# tiene información relevante para la pregunta (ver Docs/taller2_fase2).
MAX_RELEVANT_DISTANCE = 25


def format_docs(docs):
    return "\n\n".join(f"[{doc.metadata['source']}] {doc.page_content}" for doc in docs)


def build_rag_chain(vector_store=None, model_name=OLLAMA_MODEL):
    """Conecta retriever (ChromaDB) -> prompt -> LLM (Ollama) usando LCEL.
    Cambiar `model_name` o el prompt aquí permite observar directamente el
    cambio de comportamiento del sistema (requerido por la rúbrica de Fase 3)."""
    vector_store = vector_store or load_index()
    retriever = vector_store.as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})
    llm = OllamaLLM(model=model_name, base_url=OLLAMA_BASE_URL, temperature=0.0)

    chain = (
        {"context": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def has_relevant_context(vector_store, question, max_distance=MAX_RELEVANT_DISTANCE):
    """Puerta de seguridad: si ni el chunk más cercano supera un umbral mínimo
    de similitud, evitamos llamarlo al LLM y respondemos que no tenemos esa
    información, en vez de arriesgarnos a una alucinación con contexto débil."""
    results = vector_store.similarity_search_with_score(question, k=1)
    if not results:
        return False
    _, distance = results[0]
    return distance <= max_distance


def answer_general_query(question, vector_store=None):
    vector_store = vector_store or load_index()

    if not has_relevant_context(vector_store, question):
        return (
            "No tengo información suficiente en la base de conocimiento de "
            "EcoMarket para responder eso con confianza. Te recomiendo "
            "contactar a un agente humano de soporte para este caso."
        )

    chain, _ = build_rag_chain(vector_store)
    return chain.invoke(question)
