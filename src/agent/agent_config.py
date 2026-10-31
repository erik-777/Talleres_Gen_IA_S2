import os
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAG_DIR = BASE_DIR / "src" / "rag"

# Los módulos del Taller 2 usan imports planos (`from config import ...`), así
# que se agregan al path para reutilizarlos sin duplicar código.
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from config import CATALOG_FILE, OLLAMA_BASE_URL, ORDERS_FILE  # noqa: E402  (src/rag/config.py)

# Modelo del agente: necesita soporte de tool calling. llama3.2:1b (Talleres 1-2)
# elige mal las herramientas. Se compararon qwen2.5:3b y qwen3:4b (ver
# Docs/proyecto_final_fase2_implementacion.md): qwen3:4b elige mejor pero tarda
# 16-256 s por turno en un equipo de 8GB, inviable para la demo en vivo. Se
# puede cambiar con la variable de entorno AGENT_MODEL.
# Ver justificación en Docs/proyecto_final_fase1_arquitectura.md.
AGENT_MODEL = os.environ.get("AGENT_MODEL", "qwen2.5:3b")

# Guardrails posteriores al agente (agent.py). Se pueden desactivar con
# AGENT_GUARDRAILS=0 para medir qué tan bien se comporta el LLM por sí solo.
GUARDRAILS_ENABLED = os.environ.get("AGENT_GUARDRAILS", "1") != "0"

# Fecha "de hoy" simulada para que la ventana de 30 días sea reproducible con
# los pedidos de ejemplo (todos de abril de 2026), en vez de depender del reloj.
SIMULATED_TODAY = date(2026, 4, 25)

RETURN_WINDOW_DAYS = 30
HIGH_VALUE_THRESHOLD_COP = 500_000
LABEL_SHIPPING_DEADLINE_DAYS = 7
RETURN_WAREHOUSE_ADDRESS = "Bodega EcoMarket - Calle 15 # 32-80, Yumbo, Valle del Cauca"

RETURNS_DIR = BASE_DIR / "Data" / "returns"
LABELS_DIR = RETURNS_DIR / "etiquetas"
REGISTRY_FILE = RETURNS_DIR / "registro_devoluciones.json"

LOGS_DIR = BASE_DIR / "Data" / "logs"
ACTION_LOG_FILE = LOGS_DIR / "agent_actions.jsonl"

__all__ = [
    "BASE_DIR", "CATALOG_FILE", "OLLAMA_BASE_URL", "ORDERS_FILE", "AGENT_MODEL", "GUARDRAILS_ENABLED",
    "SIMULATED_TODAY", "RETURN_WINDOW_DAYS", "HIGH_VALUE_THRESHOLD_COP",
    "LABEL_SHIPPING_DEADLINE_DAYS", "RETURN_WAREHOUSE_ADDRESS", "RETURNS_DIR",
    "LABELS_DIR", "REGISTRY_FILE", "LOGS_DIR", "ACTION_LOG_FILE",
]
