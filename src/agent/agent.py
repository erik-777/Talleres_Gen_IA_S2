"""Agente de atención al cliente de EcoMarket (Proyecto Final, Fase 2).

Arquitectura (ver diagrama en Docs/proyecto_final_fase1_arquitectura.md):

    mensaje -> [1. router por reglas] -> [2. agente LangChain: LLM + 5 herramientas] -> [3. guardrails] -> respuesta
                    |                          |-- buscar_informacion_ecomarket (RAG del Taller 2)
                    |                          |-- consultar_pedido
                    |                          |-- verificar_elegibilidad_devolucion
                    |                          |-- generar_etiqueta_devolucion
                    |                          '-- escalar_a_humano
                    '-- riesgo de salud/seguridad -> escalar_a_humano directo (sin LLM)

El LLM decide qué herramienta usar y redacta la respuesta; las reglas de negocio
(elegibilidad, etiquetas) viven en código determinístico (returns_service.py) y
los guardrails garantizan que el proceso se complete y que el agente no invente
códigos de devolución que ninguna herramienta generó.
"""

import json
import re
import time

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from action_log import current_session_id, current_turn_calls, write_event
from agent_config import AGENT_MODEL, GUARDRAILS_ENABLED, OLLAMA_BASE_URL, SIMULATED_TODAY
from tools import (
    ALL_TOOLS,
    buscar_informacion_ecomarket,
    escalar_a_humano,
    generar_etiqueta_devolucion,
    verificar_elegibilidad_devolucion,
)

SYSTEM_PROMPT = f"""Eres el asistente virtual de atención al cliente de EcoMarket, una tienda
de productos ecológicos en Colombia. Respondes siempre en español, de forma breve, clara y amable.
La fecha de hoy es {SIMULATED_TODAY.isoformat()}.

Cómo trabajar:
1. Preguntas sobre EcoMarket (envíos, pagos, cuenta, productos, precios, stock, políticas
   en general): llama a la herramienta buscar_informacion_ecomarket. No respondas de memoria.
2. Estado de un pedido: usa consultar_pedido.
3. Solicitud de devolución:
   a. Necesitas el número de pedido (ECO + 4 dígitos) y el motivo. Si falta alguno,
      pídeselo al cliente antes de usar herramientas.
   b. Llama a verificar_elegibilidad_devolucion y sigue su campo 'siguiente_paso'.
      Elige el motivo así: no le gustó / ya no lo quiere -> cambio_de_opinion; vino
      defectuoso o no funciona -> defecto_fabrica; llegó roto o dañado -> danado_en_transito;
      llegó otro producto -> producto_equivocado. Si el cliente dijo que abrió el empaque
      o que usó el producto (o que no), pásalo en empaque_abierto / producto_usado.
   c. Si es elegible, llama a generar_etiqueta_devolucion y entrega al cliente el código
      de devolución, la guía, la dirección de la bodega, la fecha límite y quién paga el envío.
   d. Si falta información, haz la pregunta_pendiente; cuando el cliente responda, vuelve
      a llamar a verificar_elegibilidad_devolucion con el dato nuevo.
4. Saludos, agradecimientos o charla breve: responde directamente sin herramientas.
5. Temas ajenos a EcoMarket (cultura general, tareas, etc.): no los respondas; di
   amablemente que solo puedes ayudar con temas de EcoMarket.

Reglas:
- Nunca inventes números de pedido, códigos de devolución, guías, tickets, fechas ni precios:
  usa solo lo que devuelvan las herramientas.
- Nunca digas que una devolución fue aprobada si no generaste la etiqueta.
- Si una herramienta devuelve ok=false, explica el problema al cliente y dile qué puede hacer.
"""

# 1. Router por reglas (antes del LLM): los reportes de riesgo para la salud o
# la seguridad se escalan siempre a un humano (sección 3 de la política). No se
# deja esta decisión a un modelo de 3B que podría no reconocerla.
SAFETY_PATTERN = re.compile(
    r"\b(quem\w*|intoxic\w*|alergi\w*|herid\w*|cortad[oa]s?|me cort[eéó]|explot\w*|incendi\w*|"
    r"t[oó]xic\w*|peligros\w*|hospital\w*|lesi[oó]n\w*|envenen\w*|sangr\w*)",
    re.IGNORECASE,
)
ORDER_PATTERN = re.compile(r"\bECO\d{4}\b", re.IGNORECASE)
# Códigos que solo pueden venir de una herramienta; si aparecen en la respuesta
# y no en ningún resultado de herramienta, el LLM los inventó.
GENERATED_CODE_PATTERN = re.compile(r"\b(RMA-[A-Z0-9-]+|TCK-\d+|ECOENV[A-Z0-9]+)\b")

FALLBACK_ERROR_MESSAGE = (
    "Lo siento, en este momento no puedo procesar tu solicitud por un problema técnico. "
    "Por favor intenta de nuevo en unos minutos o escribe a soporte@ecomarket.com."
)
EMPTY_RESPONSE_NUDGE = "(Por favor responde a mi mensaje anterior.)"
OUT_OF_SCOPE_MESSAGE = (
    "Solo puedo ayudarte con temas de EcoMarket: pedidos, devoluciones, productos, envíos, "
    "pagos y tu cuenta. No encontré información sobre eso en nuestra base de conocimiento."
)

# Preguntas informativas (para el guardrail de fundamentación) y respuestas
# sí/no a una pregunta pendiente de la verificación de devolución.
QUESTION_PATTERN = re.compile(
    r"\?|\b(cu[aá]nt[oa]s?|cu[aá]l(es)?|qu[eé]|c[oó]mo|d[oó]nde|cu[aá]ndo|hacen|tienen|"
    r"aceptan|puedo|existe|hay)\b", re.IGNORECASE)
RETURN_INTENT_PATTERN = re.compile(r"devol\w*|devuelv\w*|reembols\w*|etiqueta|ECO\d{4}", re.IGNORECASE)
NEGATIVE_ANSWER = re.compile(
    r"^\s*no\b|\bnunca\b|\bsin (usar|abrir)\b|\bnuev[oa]\b|\bcerrad[oa]\b|\bintact[oa]\b|"
    r"\bsellad[oa]\b", re.IGNORECASE)
POSITIVE_ANSWER = re.compile(
    r"^\s*s[ií]\b|\bya (lo |la )?(us|abr)\w*|\babiert[oa]\b|\busad[oa]\b|\bla us[eé]\b|"
    r"\blo us[eé]\b|\blo abr[ií]\b|\bla abr[ií]\b", re.IGNORECASE)

UNSURE_ANSWER = re.compile(r"\bno s[eé]\b|\bno recuerdo\b|\btal vez\b|\bcreo\b", re.IGNORECASE)

# Verificaciones que quedaron esperando un dato del cliente, por sesión.
_pending_verification = {}

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        # reasoning=False desactiva el modo "thinking" de qwen3: en CPU/8GB triplica
        # la latencia sin mejorar la elección de herramientas en nuestras pruebas.
        llm = ChatOllama(model=AGENT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.0,
                         reasoning=False if AGENT_MODEL.startswith("qwen3") else None)
        # El checkpointer guarda la conversación completa por sesión (incluyendo
        # resultados de herramientas), así el agente recuerda en el turno 2 qué
        # verificó en el turno 1.
        _agent = create_agent(llm, ALL_TOOLS, system_prompt=SYSTEM_PROMPT,
                              checkpointer=InMemorySaver())
    return _agent


def _invoke(message, session_id):
    result = get_agent().invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": session_id}, "recursion_limit": 12},
    )
    tool_outputs = " ".join(m.content for m in result["messages"] if isinstance(m, ToolMessage))
    return result["messages"][-1].content.strip(), tool_outputs


# --------------------------------------------------------------------------
# 3. Guardrails posteriores al agente
# --------------------------------------------------------------------------

def _format_label(label):
    return (
        f"¡Listo! Tu devolución del pedido {label['numero_pedido']} fue aprobada.\n\n"
        f"- Código de devolución: {label['codigo_devolucion']}\n"
        f"- Guía ({label['transportadora']}): {label['guia_transportadora']}\n"
        f"- Envía el producto a: {label['direccion_bodega']}\n"
        f"- Fecha límite de envío: {label['fecha_limite_envio']}\n"
        f"- Costo del envío de retorno: lo asume {label['costo_envio_retorno']}\n"
        f"- Etiqueta: {label['url_etiqueta']}\n\n"
        f"Reembolso: {label['reembolso']}"
    )


def _parse_yes_no(message):
    # La negación tiene prioridad: "nunca la he usado" contiene "usado".
    if UNSURE_ANSWER.search(message):
        return None  # ambiguo: se deja la respuesta del LLM
    if NEGATIVE_ANSWER.search(message):
        return False
    if POSITIVE_ANSWER.search(message):
        return True
    return None


def _apply_guardrails(message, answer, tool_outputs, calls, guardrails, session_id):
    """Corrige al LLM cuando no siguió el proceso: completa la verificación
    pendiente, genera la etiqueta / escala si la verificación lo indicaba, obliga
    a fundamentar las respuestas informativas en el RAG y bloquea códigos
    inventados."""
    used = {c["tool"] for c in calls}

    # 3a. El turno anterior dejó una pregunta_pendiente y el cliente respondió,
    # pero el LLM no volvió a verificar: se completa el dato y se verifica.
    pending = _pending_verification.get(session_id)
    if pending and "verificar_elegibilidad_devolucion" not in used:
        value = _parse_yes_no(message)
        if value is not None:
            guardrails.append("completar_dato_pendiente")
            verificar_elegibilidad_devolucion.invoke({**pending["args"], pending["campo"]: value})
            used = {c["tool"] for c in calls}

    verifications = [c for c in calls if c["tool"] == "verificar_elegibilidad_devolucion"
                     and c["result"].get("ok")]

    if verifications:
        last = verifications[-1]
        decision = last["result"]["decision"]
        label_ok = any(c["tool"] == "generar_etiqueta_devolucion" and c["result"].get("ok") for c in calls)
        if decision == "elegible" and not label_ok:
            guardrails.append("completar_etiqueta")
            label = generar_etiqueta_devolucion.invoke(last["args"])
            if label.get("ok"):
                return _format_label(label)
        if decision == "requiere_escalamiento" and "escalar_a_humano" not in used:
            guardrails.append("completar_escalamiento")
            ticket = escalar_a_humano.invoke({
                "motivo_escalamiento": last["result"]["explicacion"],
                "numero_pedido": last["result"]["numero_pedido"],
            })
            return (f"{last['result']['explicacion']} Por eso, un agente humano revisará tu "
                    f"solicitud (ticket {ticket['ticket']}). {ticket['tiempo_respuesta']}")
        if "completar_dato_pendiente" in guardrails:
            if decision == "no_elegible":
                return f"Lo siento, tu devolución no procede: {last['result']['explicacion']}"
            if decision == "requiere_informacion":
                return last["result"]["pregunta_pendiente"]

    # 3b. Fundamentación: una pregunta informativa respondida sin ninguna
    # herramienta salió de la "memoria" del LLM; se responde con el RAG, cuya
    # puerta de relevancia también filtra los temas ajenos a EcoMarket.
    if (not calls and QUESTION_PATTERN.search(message)
            and not RETURN_INTENT_PATTERN.search(message)):
        guardrails.append("fundamentar_con_rag")
        rag = buscar_informacion_ecomarket.invoke({"pregunta": message})
        return rag["respuesta"] if rag.get("ok") else OUT_OF_SCOPE_MESSAGE

    invented = [code for code in GENERATED_CODE_PATTERN.findall(answer) if code not in tool_outputs]
    if invented:
        guardrails.append("codigo_inventado_bloqueado")
        write_event({"event": "alerta", "tipo": "codigo_inventado", "codigos": invented, "respuesta": answer})
        return ("Aún no he generado ninguna etiqueta de devolución para tu caso. Para hacerlo "
                "necesito verificar la elegibilidad: ¿me confirmas el número de pedido (ECO + 4 "
                "dígitos) y el motivo de la devolución?")
    return answer


def _remember_pending(calls, session_id):
    verifications = [c for c in calls if c["tool"] == "verificar_elegibilidad_devolucion"
                     and c["result"].get("ok")]
    if not verifications:
        return
    last = verifications[-1]
    if last["result"]["decision"] == "requiere_informacion":
        _pending_verification[session_id] = {"args": last["args"], "campo": last["result"]["dato_pendiente"]}
    else:
        _pending_verification.pop(session_id, None)


def _safety_route(message):
    match = ORDER_PATTERN.search(message)
    ticket = escalar_a_humano.invoke({
        "motivo_escalamiento": f"Reporte de posible riesgo de seguridad/salud: {message[:300]}",
        "numero_pedido": match.group(0).upper() if match else None,
    })
    return (
        "Lamento mucho lo ocurrido. Como tu mensaje menciona un posible riesgo para tu "
        "salud o seguridad, un agente humano revisará tu caso con prioridad "
        f"(ticket {ticket['ticket']}). {ticket['tiempo_respuesta']} "
        "Si es una emergencia médica, por favor acude a un servicio de salud de inmediato."
    )


def run_turn(message, session_id="cli"):
    """Procesa un mensaje del cliente dentro de una sesión (la memoria de la
    conversación se indexa por session_id). Devuelve la respuesta, las
    herramientas usadas, la ruta y los guardrails activados (para la UI y la
    evaluación)."""
    current_session_id.set(session_id)
    calls = []
    current_turn_calls.set(calls)
    guardrails = []
    error = None
    start = time.perf_counter()

    if SAFETY_PATTERN.search(message):
        route = "router_seguridad"
        answer = _safety_route(message)
    else:
        route = "agente"
        try:
            answer, tool_outputs = _invoke(message, session_id)
            if GUARDRAILS_ENABLED:
                if not answer:
                    guardrails.append("reintento_respuesta_vacia")
                    answer, tool_outputs = _invoke(EMPTY_RESPONSE_NUDGE, session_id)
                answer = _apply_guardrails(message, answer, tool_outputs, calls, guardrails, session_id)
                _remember_pending(calls, session_id)
            answer = answer or FALLBACK_ERROR_MESSAGE
        except Exception as exc:  # noqa: BLE001 - Ollama caído, límite de pasos, etc.
            error = f"{type(exc).__name__}: {exc}"
            answer = FALLBACK_ERROR_MESSAGE

    write_event({"event": "turn", "route": route, "user_message": message,
                 "tools_used": [c["tool"] for c in calls], "guardrails": guardrails,
                 "error": error, "latency_ms": round((time.perf_counter() - start) * 1000)})
    return {"answer": answer, "tool_calls": calls, "route": route,
            "guardrails": guardrails, "error": error}


if __name__ == "__main__":
    print("Agente EcoMarket (escribe 'salir' para terminar)")
    while (user := input("\nTú: ").strip()).lower() not in {"salir", "exit", "quit"}:
        turn = run_turn(user)
        for call in turn["tool_calls"]:
            print(f"  [tool] {call['tool']}({call['args']}) -> {json.dumps(call['result'], ensure_ascii=False)}")
        if turn["guardrails"]:
            print(f"  [guardrails] {turn['guardrails']}")
        print(f"Agente: {turn['answer']}")
