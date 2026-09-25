import json
import re

from config import ORDERS_FILE

TRACKING_PATTERN = re.compile(r"\bECO\d{4}\b", re.IGNORECASE)


def extract_tracking_number(query):
    match = TRACKING_PATTERN.search(query)
    return match.group(0).upper() if match else None


def find_order(tracking_number):
    """Búsqueda exacta en código (no semántica): el estado de un pedido es un
    dato transaccional, no debe resolverse por similitud de embeddings.
    Ver 'Nota de diseño' en Docs/taller2_fase2_base_conocimiento.md."""
    orders = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
    for order in orders:
        if order["tracking_number"] == tracking_number:
            return order
    return None


def format_order_status(order):
    message = (
        f"Tu pedido {order['tracking_number']} ({order['product']}) está "
        f"actualmente en estado: {order['status']}. Fecha estimada de entrega: "
        f"{order['estimated_delivery']}. Enlace de rastreo: {order['tracking_link']}."
    )
    if order["delay_reason"]:
        message += f" Motivo del retraso: {order['delay_reason']}."
    return message
