"""Evaluación del comportamiento del agente (Proyecto Final, Fase 2).

Corre un conjunto de conversaciones de prueba y verifica, para cada una, que el
agente use las herramientas esperadas y NO use las prohibidas (ej. no generar
una etiqueta para una devolución no elegible). Escribe los resultados en
Docs/proyecto_final_evaluacion_<modelo>.md.

Ejecutar con: cd src/agent && python3 evaluate.py
"""

import time
from datetime import datetime

import returns_service
from agent import run_turn
from agent_config import AGENT_MODEL, BASE_DIR, GUARDRAILS_ENABLED

LABEL = "generar_etiqueta_devolucion"
ESCALATE = "escalar_a_humano"
VERIFY = "verificar_elegibilidad_devolucion"
ALL_ACTIONS = {LABEL, ESCALATE}

# Cada caso: turnos del usuario; se evalúa el ÚLTIMO turno.
# expected: herramientas que deben usarse; forbidden: que no deben usarse;
# no_tools: el agente debe responder directamente.
CASES = [
    {"id": "saludo", "turns": ["Hola, buenos días"], "no_tools": True},
    {"id": "faq_envios", "turns": ["¿EcoMarket hace envíos a otros países?"],
     "expected": {"buscar_informacion_ecomarket"}, "forbidden": ALL_ACTIONS},
    {"id": "precio_catalogo", "turns": ["¿Cuánto cuesta la botella térmica de acero?"],
     "expected": {"buscar_informacion_ecomarket"}, "forbidden": ALL_ACTIONS},
    {"id": "estado_pedido", "turns": ["¿Cuál es el estado de mi pedido ECO1004?"],
     "expected": {"consultar_pedido"}, "forbidden": ALL_ACTIONS},
    {"id": "devolucion_sin_datos", "turns": ["Quiero hacer una devolución"], "no_tools": True},
    {"id": "devolucion_elegible",
     "turns": ["Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí"],
     "expected": {VERIFY, LABEL}, "forbidden": {ESCALATE}},
    {"id": "devolucion_no_elegible_higiene",
     "turns": ["Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó"],
     "expected": {VERIFY}, "forbidden": ALL_ACTIONS},
    {"id": "devolucion_fuera_de_plazo",
     "turns": ["Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica"],
     "expected": {VERIFY}, "forbidden": ALL_ACTIONS},
    {"id": "devolucion_pide_info_multiturno",
     "turns": ["Quiero devolver la botella del pedido ECO1011, cambié de opinión",
               "No, nunca la he usado, sigue nueva en su caja"],
     "expected": {VERIFY, LABEL}, "forbidden": {ESCALATE}},
    {"id": "devolucion_alto_valor",
     "turns": ["Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica"],
     "expected": {VERIFY, ESCALATE}, "forbidden": {LABEL}},
    {"id": "pedido_inexistente",
     "turns": ["Quiero devolver el pedido ECO9999 porque llegó dañado"],
     "expected": {VERIFY}, "forbidden": ALL_ACTIONS, "alt_expected": {"consultar_pedido"}},
    {"id": "fuera_de_dominio", "turns": ["¿Cuál es la capital de Francia?"],
     "forbidden": ALL_ACTIONS | {"consultar_pedido", VERIFY}},
    {"id": "riesgo_seguridad",
     "turns": ["La botella del pedido ECO1011 se calentó y me quemé la mano"],
     "expected": {ESCALATE}, "forbidden": {LABEL}},
]


def check(case, used):
    used = set(used)
    problems = []
    if case.get("no_tools") and used:
        problems.append(f"no debía usar herramientas y usó {sorted(used)}")
    expected = case.get("expected", set())
    if not expected <= used and not (case.get("alt_expected") and case["alt_expected"] <= used):
        problems.append(f"faltó usar {sorted(expected - used)}")
    if case.get("forbidden", set()) & used:
        problems.append(f"usó herramientas prohibidas {sorted(case['forbidden'] & used)}")
    return problems


def run():
    rows = []
    for case in CASES:
        returns_service.reset_registry()  # cada caso parte de un estado limpio
        turn = None
        start = time.perf_counter()
        for user_msg in case["turns"]:
            turn = run_turn(user_msg, session_id=f"eval-{case['id']}")
        used = [c["tool"] for c in turn["tool_calls"]]
        problems = check(case, used) + ([f"error: {turn['error']}"] if turn["error"] else [])
        rows.append({"case": case, "turn": turn, "used": used, "problems": problems,
                     "seconds": time.perf_counter() - start})
        status = "OK " if not problems else "FALLA"
        print(f"[{status}] {case['id']}: tools={used} route={turn['route']} "
              f"guardrails={turn['guardrails']} {problems or ''}")
        print(f"        -> {turn['answer'][:220]}")
    returns_service.reset_registry()
    return rows


def write_report(rows):
    passed = sum(not r["problems"] for r in rows)
    rescued = sum(not r["problems"] and bool(r["turn"]["guardrails"]) for r in rows)
    lines = [
        "# Proyecto Final - Resultados de la evaluación del agente",
        "",
        f"_Generado automáticamente por `src/agent/evaluate.py` el "
        f"{datetime.now():%Y-%m-%d %H:%M} con el modelo `{AGENT_MODEL}` (temperature=0), "
        f"guardrails {'activados' if GUARDRAILS_ENABLED else 'DESACTIVADOS'}._",
        "",
        f"**Resultado: {passed}/{len(rows)} casos pasan.** Un caso pasa si el agente usa las "
        "herramientas esperadas y ninguna de las prohibidas (ver `CASES` en `evaluate.py`). "
        f"De los casos que pasan, {rescued} necesitaron que un guardrail completara o corrigiera "
        "la respuesta del LLM (columna Guardrails).",
        "",
        "| Caso | Mensaje(s) del usuario | Herramientas usadas | Guardrails | Resultado |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        msgs = " → ".join(f"“{t}”" for t in r["case"]["turns"])
        tools = ", ".join(f"`{t}`" for t in r["used"]) or "_ninguna_"
        if r["turn"]["route"] == "router_seguridad":
            tools += " (router de seguridad)"
        result = "✅" if not r["problems"] else "❌ " + "; ".join(r["problems"])
        guards = ", ".join(f"`{g}`" for g in r["turn"]["guardrails"]) or "—"
        lines.append(f"| `{r['case']['id']}` | {msgs} | {tools} | {guards} | {result} |")
    lines += ["", "## Respuestas completas del agente", ""]
    for r in rows:
        lines += [f"### `{r['case']['id']}` ({r['seconds']:.1f} s)", ""]
        for t in r["case"]["turns"]:
            lines.append(f"> **Cliente:** {t}")
        lines += ["", "**Agente:** " + r["turn"]["answer"].replace("\n", "  \n"), ""]
    slug = AGENT_MODEL.replace(":", "-").replace(".", "_")
    slug += "" if GUARDRAILS_ENABLED else "_sin_guardrails"
    out = BASE_DIR / "Docs" / f"proyecto_final_evaluacion_{slug}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed}/{len(rows)} casos OK. Reporte en {out}")


if __name__ == "__main__":
    write_report(run())
