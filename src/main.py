import json
from pathlib import Path

from llm_client import generate
from prompts import ORDER_PROMPT_BASIC, ORDER_PROMPT_TEMPLATE, RETURN_PROMPT_TEMPLATE


BASE_DIR = Path(__file__).resolve().parent.parent
ORDERS_FILE = BASE_DIR / "Data" / "orders.json"
POLICIES_FILE = BASE_DIR / "Data" / "return_policies.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_orders_context(orders):
    lines = []
    for order in orders:
        lines.append(
            f"- tracking_number: {order['tracking_number']} | "
            f"producto: {order['product']} | "
            f"estado: {order['status']} | "
            f"entrega estimada: {order['estimated_delivery']} | "
            f"link: {order['tracking_link']} | "
            f"motivo retraso: {order['delay_reason'] or 'N/A'}"
        )
    return "\n".join(lines)


def format_policies_context(policies):
    lines = []
    for policy in policies:
        lines.append(
            f"- categoría: {policy['category']} | "
            f"devolución permitida: {'sí' if policy['return_allowed'] else 'no'} | "
            f"condiciones: {policy['conditions']}"
        )
    return "\n".join(lines)


def generate_order_response_basic(tracking_number):
    """Prompt sin rol, sin contexto ni datos: el modelo no tiene forma de saber la respuesta real."""
    prompt = ORDER_PROMPT_BASIC.format(tracking_number=tracking_number)
    return generate(prompt)


def generate_order_response_improved(tracking_number):
    """Prompt con rol, instrucciones explícitas y la base de pedidos como contexto."""
    orders = load_json(ORDERS_FILE)
    prompt = ORDER_PROMPT_TEMPLATE.format(
        orders_data=format_orders_context(orders),
        tracking_number=tracking_number,
    )
    return generate(prompt)


def generate_return_response(product_name, category, package_status, reason):
    policies = load_json(POLICIES_FILE)
    prompt = RETURN_PROMPT_TEMPLATE.format(
        policies_data=format_policies_context(policies),
        product_name=product_name,
        category=category,
        package_status=package_status,
        reason=reason,
    )
    return generate(prompt)


if __name__ == "__main__":
    tracking_number = "ECO1004"

    print("=== Ejercicio 1: estado de pedido ===")
    print(f"\n--- Prompt básico (sin contexto) para {tracking_number} ---")
    print(generate_order_response_basic(tracking_number))

    print(f"\n--- Prompt mejorado (con contexto) para {tracking_number} ---")
    print(generate_order_response_improved(tracking_number))

    print("\n--- Prompt mejorado con tracking inexistente (ECO9999) ---")
    print(generate_order_response_improved("ECO9999"))

    print("\n=== Ejercicio 2: devolución de producto ===")
    print("\n--- Caso no devolvible (producto de higiene abierto) ---")
    print(
        generate_return_response(
            product_name="Shampoo sólido natural",
            category="productos de higiene",
            package_status="abierto",
            reason="No cumplió mis expectativas",
        )
    )

    print("\n--- Caso devolvible (botella sin usar) ---")
    print(
        generate_return_response(
            product_name="Botella térmica de acero reutilizable",
            category="botellas",
            package_status="cerrado, sin usar",
            reason="Cambié de opinión",
        )
    )
