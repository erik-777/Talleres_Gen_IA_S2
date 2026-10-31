"""Interfaz web del agente de EcoMarket (Proyecto Final, Fase 4).

Ejecutar desde la raíz del repositorio con:
    streamlit run src/agent/app.py
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import returns_service  # noqa: E402
from action_log import new_session_id  # noqa: E402
from agent import run_turn  # noqa: E402
from agent_config import AGENT_MODEL, BASE_DIR, OLLAMA_BASE_URL, SIMULATED_TODAY  # noqa: E402

EXAMPLES = {
    "Pregunta general (RAG)": "¿EcoMarket hace envíos a otros países?",
    "Estado de pedido": "¿Cuál es el estado de mi pedido ECO1004?",
    "Devolución elegible": "Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí",
    "Devolución que pide más datos": "Quiero devolver la botella del pedido ECO1011, cambié de opinión",
    "Devolución no elegible": "Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó",
    "Fuera de plazo": "Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica",
    "Alto valor (escala)": "Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica",
    "Pedido inexistente": "Quiero devolver el pedido ECO9999 porque llegó dañado",
    "Riesgo de seguridad": "La botella del pedido ECO1011 se calentó y me quemé la mano",
}

TOOL_ICONS = {
    "buscar_informacion_ecomarket": "📚",
    "consultar_pedido": "📦",
    "verificar_elegibilidad_devolucion": "✅",
    "generar_etiqueta_devolucion": "🏷️",
    "escalar_a_humano": "🧑‍💼",
}


@st.cache_data(ttl=30, show_spinner=False)
def ollama_available():
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3) as resp:
            models = [m["name"] for m in json.loads(resp.read())["models"]]
        return AGENT_MODEL in models, models
    except OSError:
        return False, []


def render_trace(turn):
    calls = turn.get("tool_calls", [])
    label_parts = [f"{TOOL_ICONS.get(c['tool'], '🔧')} {c['tool']}" for c in calls]
    if turn.get("route") == "router_seguridad":
        label_parts.insert(0, "🚨 router de seguridad")
    if not label_parts:
        st.caption("Respondió directamente, sin usar herramientas.")
        return
    with st.expander("Acciones del agente: " + " → ".join(label_parts)):
        for c in calls:
            st.markdown(f"**{TOOL_ICONS.get(c['tool'], '🔧')} `{c['tool']}`** · {c['latency_ms']} ms")
            st.json({"argumentos": c["args"], "resultado": c["result"]}, expanded=False)
        if turn.get("guardrails"):
            st.warning("Guardrails activados: " + ", ".join(turn["guardrails"]))


def render_labels(turn, key_prefix):
    """Botón de descarga para cada etiqueta que el agente generó en el turno."""
    for c in turn.get("tool_calls", []):
        if c["tool"] != "generar_etiqueta_devolucion" or not c["result"].get("ok"):
            continue
        rma = c["result"]["codigo_devolucion"]
        path = BASE_DIR / c["result"].get("archivo_etiqueta", f"__sin_archivo__/{rma}.pdf")
        if path.exists():
            st.download_button(f"📄 Descargar etiqueta {rma} (PDF)", data=path.read_bytes(),
                               file_name=path.name, mime="application/pdf",
                               key=f"{key_prefix}-{rma}")
        else:
            st.caption(f"La etiqueta {rma} ya no está disponible (se reiniciaron los datos de la demo).")


def show_text(text):
    # st.markdown interpreta "$...$" como LaTeX y las respuestas traen precios en $.
    st.markdown(text.replace("$", "\\$"))


def reset_conversation():
    st.session_state.session_id = new_session_id()
    st.session_state.messages = []


st.set_page_config(page_title="EcoMarket · Asistente", page_icon="🌱", layout="centered")

if "session_id" not in st.session_state:
    reset_conversation()

with st.sidebar:
    st.header("🌱 EcoMarket")
    st.write("Asistente con agente de IA: responde preguntas, consulta pedidos y "
             "**tramita devoluciones** (verifica elegibilidad y genera la etiqueta).")
    st.caption(f"Modelo: `{AGENT_MODEL}` vía Ollama · Fecha simulada: {SIMULATED_TODAY}")
    st.caption(f"Sesión: `{st.session_state.session_id}`")
    st.caption("⚠️ Proyecto académico con datos simulados: los enlaces de rastreo "
               "(ecomarket.example) no llevan a un sitio real. Las etiquetas sí se generan "
               "en PDF y se descargan desde el chat.")

    st.subheader("Ejemplos")
    for title, prompt in EXAMPLES.items():
        if st.button(title, use_container_width=True):
            st.session_state.pending_prompt = prompt

    st.divider()
    if st.button("🗨️ Nueva conversación", use_container_width=True):
        reset_conversation()
        st.rerun()
    if st.button("♻️ Reiniciar datos de la demo", use_container_width=True,
                 help="Borra las etiquetas, rechazos y tickets simulados."):
        returns_service.reset_registry()
        reset_conversation()
        st.rerun()

st.title("Asistente de atención al cliente")

ok, models = ollama_available()
if not ok:
    st.error(
        f"No se encontró el modelo `{AGENT_MODEL}` en Ollama ({OLLAMA_BASE_URL}). "
        f"Inicia el servicio con `ollama serve` y descarga el modelo con `ollama pull {AGENT_MODEL}`."
        + (f" Modelos disponibles: {', '.join(models)}" if models else "")
    )

if not st.session_state.messages:
    st.info("¡Hola! Pregúntame por un pedido (ej. ECO1004), por nuestras políticas o "
            "pídeme tramitar una devolución. También puedes probar los ejemplos de la barra lateral.")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🌱" if msg["role"] == "assistant" else None):
        show_text(msg["content"])
        if msg["role"] == "assistant":
            render_labels(msg["turn"], key_prefix=f"msg{i}")
            render_trace(msg["turn"])

prompt = st.chat_input("Escribe tu mensaje...", disabled=not ok)
prompt = prompt or st.session_state.pop("pending_prompt", None)

if prompt and ok:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        show_text(prompt)
    with st.chat_message("assistant", avatar="🌱"):
        with st.spinner("Pensando..."):
            turn = run_turn(prompt, session_id=st.session_state.session_id)
        show_text(turn["answer"])
        render_labels(turn, key_prefix=f"msg{len(st.session_state.messages)}")
        render_trace(turn)
        if turn["error"]:
            st.caption(f"Detalle técnico: {turn['error']}")
    st.session_state.messages.append({"role": "assistant", "content": turn["answer"], "turn": turn})
