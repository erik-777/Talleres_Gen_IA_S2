"""Backend simulado de devoluciones de EcoMarket.

Todo lo que decide si una devolución procede vive aquí, en código
determinístico, y no en el LLM: el agente solo decide *cuándo* llamar estas
funciones y cómo explicarle el resultado al cliente. Las reglas son una
traducción literal de Data/knowledge_base/politica_devoluciones.md.
"""

import csv
import hashlib
import json
from datetime import date, datetime, timedelta

from agent_config import (
    CATALOG_FILE,
    HIGH_VALUE_THRESHOLD_COP,
    LABEL_SHIPPING_DEADLINE_DAYS,
    LABELS_DIR,
    ORDERS_FILE,
    REGISTRY_FILE,
    RETURN_WAREHOUSE_ADDRESS,
    RETURN_WINDOW_DAYS,
    SIMULATED_TODAY,
)

MOTIVOS = {
    "defecto_fabrica": "defecto de fábrica",
    "danado_en_transito": "producto dañado en el transporte",
    "producto_equivocado": "producto equivocado en el despacho",
    "cambio_de_opinion": "cambio de opinión del cliente",
}
# Sección 1 de la política: EcoMarket paga el envío de retorno solo si la
# causa es atribuible a EcoMarket.
MOTIVOS_IMPUTABLES_A_ECOMARKET = {"defecto_fabrica", "danado_en_transito", "producto_equivocado"}

# Instrucción explícita para el agente: un modelo pequeño encadena mejor las
# herramientas si el resultado le dice qué hacer a continuación.
SIGUIENTE_PASO = {
    "elegible": "Llama ahora a generar_etiqueta_devolucion con los mismos argumentos.",
    "no_elegible": "Explica la razón al cliente. No generes etiqueta.",
    "requiere_informacion": "Haz al cliente la pregunta_pendiente y espera su respuesta.",
    "requiere_escalamiento": "Llama ahora a escalar_a_humano y entrega el número de ticket.",
}

SECCION_POLITICA = {
    "botellas": "2.1 Botellas y termos reutilizables",
    "cepillos": "2.2 Cepillos y accesorios de bambú",
    "cubiertos reutilizables": "2.3 Cubiertos reutilizables",
    "productos perecederos": "2.4 Productos perecederos",
    "productos de higiene": "2.5 Productos de higiene personal",
    "contenedores de vidrio": "2.6 Contenedores de vidrio reutilizables",
}


# --------------------------------------------------------------------------
# Acceso a datos
# --------------------------------------------------------------------------

def normalize_order_number(numero_pedido):
    return (numero_pedido or "").strip().upper()


def find_order(numero_pedido):
    orders = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
    numero_pedido = normalize_order_number(numero_pedido)
    return next((o for o in orders if o["tracking_number"] == numero_pedido), None)


def find_product(nombre_producto):
    with CATALOG_FILE.open(encoding="utf-8") as f:
        return next((row for row in csv.DictReader(f) if row["nombre"] == nombre_producto), None)


def _load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {"rechazos": [], "etiquetas": {}, "tickets": []}


def _save_registry(registry):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_registry():
    """Borra devoluciones, rechazos y tickets simulados (útil entre demos)."""
    if REGISTRY_FILE.exists():
        REGISTRY_FILE.unlink()
    if LABELS_DIR.exists():
        for label in LABELS_DIR.glob("*.txt"):
            label.unlink()


def _error(codigo, mensaje):
    return {"ok": False, "error": codigo, "mensaje": mensaje}


# --------------------------------------------------------------------------
# Consulta de pedido
# --------------------------------------------------------------------------

def get_order_summary(numero_pedido):
    order = find_order(numero_pedido)
    if not order:
        return _error(
            "pedido_no_encontrado",
            f"No existe ningún pedido con el número '{numero_pedido}'. "
            "Los números de pedido tienen el formato ECO seguido de 4 dígitos (ej. ECO1002).",
        )
    product = find_product(order["product"])
    summary = {
        "ok": True,
        "numero_pedido": order["tracking_number"],
        "producto": order["product"],
        "categoria": product["categoria"] if product else "desconocida",
        "cantidad": order["quantity"],
        "estado": order["status"],
        "fecha_estimada_entrega": order["estimated_delivery"],
        "fecha_entrega": order["delivered_date"],
        "enlace_rastreo": order["tracking_link"],
    }
    if order["delay_reason"]:
        summary["motivo_retraso"] = order["delay_reason"]
    return summary


# --------------------------------------------------------------------------
# Elegibilidad de devolución
# --------------------------------------------------------------------------

def _category_rule(categoria, motivo, empaque_abierto, producto_usado):
    """Aplica la sección 2 de la política. Devuelve (decision, explicacion,
    pregunta_pendiente). `None` en empaque_abierto/producto_usado significa que
    el cliente aún no lo ha dicho; si la regla lo necesita, se pide."""
    imputable = motivo in MOTIVOS_IMPUTABLES_A_ECOMARKET

    if categoria == "productos perecederos":
        if motivo in {"defecto_fabrica", "danado_en_transito"}:
            return ("requiere_escalamiento",
                    "Los perecederos no admiten devolución estándar; un producto vencido o en "
                    "mal estado se gestiona como reclamo de calidad con un agente humano.", None)
        return ("no_elegible", "Los productos perecederos no admiten devoluciones.", None)

    if categoria == "productos de higiene":
        if motivo in {"danado_en_transito", "producto_equivocado"}:
            return ("elegible", "Producto de higiene dañado o equivocado en el despacho.", None)
        if empaque_abierto is None:
            return ("requiere_informacion", "", "¿El empaque del producto ya fue abierto?")
        if empaque_abierto:
            return ("no_elegible", "Los productos de higiene con empaque abierto no se aceptan "
                    "por razones sanitarias.", None)
        return ("elegible", "Producto de higiene con empaque sin abrir.", None)

    if categoria == "cepillos":
        if imputable:
            return ("elegible", "Cepillo con defecto o error de despacho.", None)
        if empaque_abierto is None:
            return ("requiere_informacion", "", "¿El empaque del cepillo ya fue abierto?")
        if empaque_abierto:
            return ("no_elegible", "Un cepillo con el empaque abierto y sin defecto no se acepta "
                    "por razones de higiene.", None)
        return ("elegible", "Cepillo con empaque sin abrir.", None)

    if categoria in {"botellas", "cubiertos reutilizables", "contenedores de vidrio"}:
        if imputable:
            nota = " Se requerirá evidencia fotográfica del defecto." if motivo == "defecto_fabrica" else ""
            return ("elegible", f"Producto con {MOTIVOS[motivo]}.{nota}", None)
        if producto_usado is None:
            return ("requiere_informacion", "", "¿El producto ya fue usado?")
        if producto_usado:
            return ("no_elegible", "Por cambio de opinión solo se aceptan productos sin usar "
                    "de esta categoría.", None)
        return ("elegible", "Producto sin usar devuelto por cambio de opinión.", None)

    return ("requiere_escalamiento",
            f"La categoría '{categoria}' no está cubierta por la política de devoluciones.", None)


def evaluate_return_eligibility(numero_pedido, motivo, empaque_abierto=None, producto_usado=None):
    if motivo not in MOTIVOS:
        return _error("motivo_invalido",
                      f"Motivo '{motivo}' no reconocido. Opciones: {', '.join(MOTIVOS)}.")

    order = find_order(numero_pedido)
    if not order:
        return get_order_summary(numero_pedido)  # mismo error de pedido no encontrado

    product = find_product(order["product"])
    categoria = product["categoria"] if product else "desconocida"
    valor = int(product["precio_cop"]) * order["quantity"] if product else None
    result = {
        "ok": True,
        "numero_pedido": order["tracking_number"],
        "producto": order["product"],
        "categoria": categoria,
        "motivo": MOTIVOS[motivo],
        "valor_pedido_cop": valor,
        "politica_aplicada": SECCION_POLITICA.get(categoria, "3. Escalamiento"),
        "costo_envio_retorno": "EcoMarket" if motivo in MOTIVOS_IMPUTABLES_A_ECOMARKET else "Cliente",
    }

    def decide(decision, explicacion, pregunta=None):
        result.update(decision=decision, elegible=decision == "elegible", explicacion=explicacion,
                      siguiente_paso=SIGUIENTE_PASO[decision])
        if pregunta:
            result["pregunta_pendiente"] = pregunta
            result["dato_pendiente"] = "empaque_abierto" if "empaque" in pregunta else "producto_usado"
        return result

    if order["status"] != "Entregado" or not order["delivered_date"]:
        return decide("no_elegible", f"El pedido aún no ha sido entregado (estado: {order['status']}). "
                      "Solo se pueden devolver pedidos entregados.")

    dias = (SIMULATED_TODAY - date.fromisoformat(order["delivered_date"])).days
    result["dias_desde_entrega"] = dias
    if dias > RETURN_WINDOW_DAYS:
        return decide("no_elegible", f"Han pasado {dias} días desde la entrega; el plazo máximo "
                      f"de devolución es de {RETURN_WINDOW_DAYS} días.")

    decision, explicacion, pregunta = _category_rule(categoria, motivo, empaque_abierto, producto_usado)

    # Sección 3: casos que el agente no debe decidir solo.
    if decision == "elegible" and valor and valor > HIGH_VALUE_THRESHOLD_COP:
        return decide("requiere_escalamiento", f"El valor del pedido (${valor:,} COP) supera el "
                      f"límite de ${HIGH_VALUE_THRESHOLD_COP:,} COP para aprobación automática.")
    registry = _load_registry()
    previous_rejection = any(r["numero_pedido"] == order["tracking_number"] for r in registry["rechazos"])
    if decision == "elegible" and previous_rejection:
        # El cliente fue rechazado antes y ahora, con respuestas distintas, sí
        # calificaría: posible intento de "jugar" con el agente -> humano.
        return decide("requiere_escalamiento", "Este pedido ya tuvo una solicitud de devolución "
                      "rechazada y las condiciones reportadas cambiaron; debe revisarlo un humano.")

    if decision == "no_elegible" and not previous_rejection:
        registry["rechazos"].append({
            "numero_pedido": order["tracking_number"],
            "motivo": motivo,
            "empaque_abierto": empaque_abierto,
            "producto_usado": producto_usado,
            "fecha": datetime.now().isoformat(timespec="seconds"),
        })
        _save_registry(registry)

    return decide(decision, explicacion, pregunta)


# --------------------------------------------------------------------------
# Generación de etiqueta
# --------------------------------------------------------------------------

def create_return_label(numero_pedido, motivo, empaque_abierto=None, producto_usado=None):
    """Genera la guía de devolución. Vuelve a validar la elegibilidad en vez de
    confiar en que el agente la verificó antes (defensa en profundidad: un LLM
    no puede 'saltarse' la política llamando directo a esta función)."""
    registry = _load_registry()
    existing = registry["etiquetas"].get(normalize_order_number(numero_pedido))
    if existing:
        return {**existing, "ok": True, "ya_existia": True}

    eligibility = evaluate_return_eligibility(numero_pedido, motivo, empaque_abierto, producto_usado)
    if not eligibility["ok"]:
        return eligibility
    if eligibility["decision"] != "elegible":
        return _error(
            f"devolucion_{eligibility['decision']}",
            "No se generó la etiqueta: " + (eligibility.get("explicacion")
                                             or eligibility.get("pregunta_pendiente", "")),
        )

    order_id = eligibility["numero_pedido"]
    digest = hashlib.sha1(f"{order_id}-{motivo}".encode()).hexdigest()[:6].upper()
    rma = f"RMA-{order_id}-{digest}"
    label = {
        "numero_pedido": order_id,
        "codigo_devolucion": rma,
        "guia_transportadora": f"ECOENV{digest}{order_id[-4:]}",
        "transportadora": "EcoEnvíos",
        "direccion_bodega": RETURN_WAREHOUSE_ADDRESS,
        "fecha_limite_envio": (SIMULATED_TODAY + timedelta(days=LABEL_SHIPPING_DEADLINE_DAYS)).isoformat(),
        "costo_envio_retorno": eligibility["costo_envio_retorno"],
        "url_etiqueta": f"https://ecomarket.com/devoluciones/{rma}.pdf",
        "reembolso": "Al medio de pago original en 5 a 8 días hábiles tras la verificación en bodega.",
    }

    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    (LABELS_DIR / f"{rma}.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in label.items()) + "\n", encoding="utf-8"
    )
    registry["etiquetas"][order_id] = label
    _save_registry(registry)
    return {"ok": True, "ya_existia": False, **label}


# --------------------------------------------------------------------------
# Escalamiento a humano
# --------------------------------------------------------------------------

def create_escalation_ticket(motivo_escalamiento, numero_pedido=None):
    registry = _load_registry()
    ticket_id = f"TCK-{len(registry['tickets']) + 1:04d}"
    ticket = {
        "ticket": ticket_id,
        "numero_pedido": normalize_order_number(numero_pedido) or None,
        "motivo": motivo_escalamiento,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "tiempo_respuesta": "Un agente humano te contactará en máximo 24 horas hábiles.",
    }
    registry["tickets"].append(ticket)
    _save_registry(registry)
    return {"ok": True, **ticket}
