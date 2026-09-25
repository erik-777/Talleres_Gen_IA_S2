"""Punto de entrada de la Fase 3 del Taller 2: integra el sistema RAG
(embeddings + ChromaDB + LangChain) construido sobre el modelo de atención al
cliente del Taller 1.

Ejecutar con: cd src/rag && python3 main.py
"""

from build_index import VECTOR_STORE_DIR, build_index, load_index
from chain import answer_general_query
from order_lookup import extract_tracking_number, find_order, format_order_status


def route_query(query, vector_store):
    """Router simple: si la consulta trae un número de seguimiento, se resuelve
    con búsqueda determinística en código (no con RAG, ver justificación en
    Docs/taller2_fase2_base_conocimiento.md); en cualquier otro caso, se usa el
    sistema RAG sobre la base de conocimiento general de EcoMarket."""
    tracking_number = extract_tracking_number(query)
    if tracking_number:
        order = find_order(tracking_number)
        if order:
            return format_order_status(order)
        return (
            f"No encontré ningún pedido con el número de seguimiento "
            f"{tracking_number}. Verifica el número o contacta a soporte humano."
        )
    return answer_general_query(query, vector_store=vector_store)


if __name__ == "__main__":
    if VECTOR_STORE_DIR.exists():
        print(f"Reutilizando índice existente en {VECTOR_STORE_DIR}")
        vector_store = load_index()
    else:
        print("Construyendo índice vectorial por primera vez...")
        vector_store, total_chunks = build_index()
        print(f"Índice construido con {total_chunks} chunks.")

    demo_queries = [
        "¿Cuánto cuesta la botella térmica de acero y hay disponible?",
        "Compré un shampoo sólido pero ya abrí el empaque, ¿lo puedo devolver?",
        "¿EcoMarket hace envíos a otros países?",
        "¿Cuál es el estado de mi pedido ECO1004?",
        "¿Cuál es el estado de mi pedido ECO9999?",
        "¿Cuál es la capital de Francia?",
    ]

    for query in demo_queries:
        print(f"\n--- Pregunta: {query} ---")
        print(route_query(query, vector_store))
