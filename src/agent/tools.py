"""Herramientas (tools) del agente de EcoMarket.

Cada herramienta es una función con argumentos tipados: LangChain toma el
nombre, el docstring y el esquema de argumentos para describírsela al LLM, que
decide cuándo llamarla. La lógica real vive en returns_service.py (devoluciones)
y en src/rag/ (sistema RAG del Taller 2).
"""

from typing import Literal, Optional

from langchain_core.tools import tool

import returns_service
from action_log import logged
from agent_config import AGENT_MODEL

Motivo = Literal["defecto_fabrica", "danado_en_transito", "producto_equivocado", "cambio_de_opinion"]

_rag_cache = {}


def _get_rag():
    """Carga perezosa del índice y la cadena RAG del Taller 2 (tarda unos
    segundos por el modelo de embeddings, así que se hace una sola vez)."""
    if not _rag_cache:
        from build_index import load_index  # src/rag/
        from chain import build_rag_chain

        vector_store = load_index()
        _rag_cache["vector_store"] = vector_store
        _rag_cache["chain"], _ = build_rag_chain(vector_store, model_name=AGENT_MODEL)
    return _rag_cache["vector_store"], _rag_cache["chain"]


@tool
@logged("buscar_informacion_ecomarket")
def buscar_informacion_ecomarket(pregunta: str) -> dict:
    """Responde preguntas generales sobre EcoMarket usando la base de conocimiento
    (RAG): políticas de devolución en general, envíos, pagos, cuenta, sostenibilidad,
    precios y stock del catálogo. NO sirve para consultar un pedido específico ni para
    tramitar una devolución."""
    from chain import has_relevant_context

    vector_store, chain = _get_rag()
    if not has_relevant_context(vector_store, pregunta):
        return {"ok": False, "error": "sin_informacion",
                "mensaje": "La base de conocimiento de EcoMarket no tiene información sobre esto."}
    return {"ok": True, "respuesta": chain.invoke(pregunta)}


@tool
@logged("consultar_pedido")
def consultar_pedido(numero_pedido: str) -> dict:
    """Consulta el estado, producto, categoría y fecha de entrega de un pedido.
    numero_pedido tiene el formato ECO + 4 dígitos, ej. ECO1004."""
    return returns_service.get_order_summary(numero_pedido)


@tool
@logged("verificar_elegibilidad_devolucion")
def verificar_elegibilidad_devolucion(
    numero_pedido: str,
    motivo: Motivo,
    empaque_abierto: Optional[bool] = None,
    producto_usado: Optional[bool] = None,
) -> dict:
    """Verifica si un pedido puede devolverse según la política de EcoMarket.
    Úsala SIEMPRE antes de generar una etiqueta.
    - motivo: defecto_fabrica, danado_en_transito, producto_equivocado o cambio_de_opinion.
    - empaque_abierto / producto_usado: pásalos solo si el cliente lo dijo; si no, déjalos vacíos.
    Devuelve 'decision': elegible, no_elegible, requiere_informacion (preguntar
    'pregunta_pendiente' al cliente) o requiere_escalamiento (escalar a humano)."""
    return returns_service.evaluate_return_eligibility(numero_pedido, motivo, empaque_abierto, producto_usado)


@tool
@logged("generar_etiqueta_devolucion")
def generar_etiqueta_devolucion(
    numero_pedido: str,
    motivo: Motivo,
    empaque_abierto: Optional[bool] = None,
    producto_usado: Optional[bool] = None,
) -> dict:
    """Genera la etiqueta/guía de envío de una devolución YA verificada como elegible.
    Usa los mismos argumentos que en verificar_elegibilidad_devolucion. Devuelve el
    código de devolución (RMA), la guía, la dirección de la bodega y la fecha límite."""
    return returns_service.create_return_label(numero_pedido, motivo, empaque_abierto, producto_usado)


@tool
@logged("escalar_a_humano")
def escalar_a_humano(motivo_escalamiento: str, numero_pedido: Optional[str] = None) -> dict:
    """Crea un ticket para que un agente humano atienda el caso. Úsala cuando la
    verificación devuelva requiere_escalamiento, cuando el cliente reporte un producto
    peligroso o un riesgo para su salud, o cuando el cliente pida hablar con una persona."""
    return returns_service.create_escalation_ticket(motivo_escalamiento, numero_pedido)


ALL_TOOLS = [
    buscar_informacion_ecomarket,
    consultar_pedido,
    verificar_elegibilidad_devolucion,
    generar_etiqueta_devolucion,
    escalar_a_humano,
]
