"""Registro de acciones del agente (observabilidad, Fase 3).

Cada llamada a una herramienta queda como una línea JSON en
Data/logs/agent_actions.jsonl: quién (sesión), qué herramienta, con qué
argumentos, qué resultado y cuánto tardó. Es la base para auditoría y
alertas (ver Docs/proyecto_final_fase3_analisis.md).
"""

import functools
import json
import time
import uuid
from contextvars import ContextVar
from datetime import datetime

from agent_config import ACTION_LOG_FILE

current_session_id = ContextVar("current_session_id", default="sin-sesion")
# Llamadas a herramientas del turno actual, para mostrarlas en la UI.
current_turn_calls = ContextVar("current_turn_calls", default=None)


def new_session_id():
    return uuid.uuid4().hex[:8]


def write_event(event):
    ACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": datetime.now().isoformat(timespec="seconds"),
             "session_id": current_session_id.get(), **event}
    with ACTION_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def logged(tool_name):
    """Envuelve la función de una herramienta: registra la llamada y convierte
    cualquier excepción en un resultado de error que el agente puede explicar,
    en lugar de romper la conversación."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(**kwargs):
            start = time.perf_counter()
            try:
                result = func(**kwargs)
            except Exception as exc:  # noqa: BLE001 - cualquier fallo del backend
                result = {"ok": False, "error": "error_interno",
                          "mensaje": f"La herramienta falló inesperadamente: {exc}"}
            latency_ms = round((time.perf_counter() - start) * 1000)

            call = {"tool": tool_name, "args": kwargs, "result": result, "latency_ms": latency_ms}
            calls = current_turn_calls.get()
            if calls is not None:
                calls.append(call)

            status = "ok" if not isinstance(result, dict) or result.get("ok", True) else result.get("error")
            write_event({"event": "tool_call", "tool": tool_name, "args": kwargs,
                         "status": status, "decision": result.get("decision") if isinstance(result, dict) else None,
                         "latency_ms": latency_ms})
            return result

        return wrapper

    return decorator
