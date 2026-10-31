# Proyecto Final — Fase 2: Implementación y conexión de componentes

## 1. Extensión del código base

El agente vive en `src/agent/` y **reutiliza sin modificar** el sistema RAG del Taller 2
(`src/rag/`): `agent_config.py` agrega `src/rag/` al `sys.path` y la herramienta
`buscar_informacion_ecomarket` importa directamente `load_index()`, `build_rag_chain()` y
`has_relevant_context()`. Así, el índice ChromaDB, el modelo de embeddings, el prompt RAG y
la puerta de relevancia por distancia son exactamente los del Taller 2.

```
src/
├── rag/                      # Taller 2 (sin cambios)
│   ├── build_index.py        #   load_index()  ─────────────┐
│   ├── chain.py              #   build_rag_chain(), has_relevant_context()
│   └── config.py             #   rutas, modelo de embeddings │
└── agent/                    # Proyecto Final               │
    ├── agent_config.py       # modelo del agente, fecha simulada, umbrales de política, rutas
    ├── returns_service.py    # "sistemas internos" simulados: reglas, etiquetas, tickets (sin LLM)
    ├── label_pdf.py          # etiqueta de devolución imprimible en PDF (fpdf2)
    ├── tools.py              # 5 @tool que ve el LLM ─────────┘ (RAG = una herramienta)
    ├── action_log.py         # decorador @logged: registro JSONL + captura de excepciones
    ├── agent.py              # router por reglas + create_agent (LangChain) + guardrails
    ├── evaluate.py           # batería de 13 conversaciones de prueba
    └── app.py                # interfaz Streamlit (Fase 4)
```

Datos: `Data/orders.json` se extendió con `delivered_date` y `quantity` (necesarios para la
ventana de 30 días y el umbral de $500.000), y con 4 pedidos entregados (ECO1011-ECO1014)
que cubren los caminos del diagrama de flujo. La categoría y el precio de cada producto
se toman del catálogo del Taller 2 (`catalogo_productos.csv`), que queda como única fuente
de verdad.

### 1.1 Cómo se conectan las piezas en un turno

```
run_turn(mensaje, session_id)                                  agent.py
 ├─ 1. Router por reglas: ¿riesgo de salud/seguridad? ── sí ─▶ escalar_a_humano (sin LLM)
 ├─ 2. Agente: create_agent(ChatOllama("qwen2.5:3b"), ALL_TOOLS,
 │             system_prompt, checkpointer=InMemorySaver())
 │      bucle ReAct de LangGraph:  LLM ─▶ tool_call ─▶ herramienta ─▶ ToolMessage ─▶ LLM ─▶ ...
 │      cada herramienta: @tool (esquema para el LLM) ∘ @logged (log + errores) ∘ returns_service
 ├─ 3. Guardrails posteriores (ver sección 3)
 └─ registro del turno en Data/logs/agent_actions.jsonl ─▶ {answer, tool_calls, route, guardrails, error}
```

Fragmentos clave:

```python
# tools.py: el docstring y los tipos se convierten en el esquema JSON que ve el LLM.
Motivo = Literal["defecto_fabrica", "danado_en_transito", "producto_equivocado", "cambio_de_opinion"]

@tool
@logged("verificar_elegibilidad_devolucion")
def verificar_elegibilidad_devolucion(numero_pedido: str, motivo: Motivo,
                                      empaque_abierto: Optional[bool] = None,
                                      producto_usado: Optional[bool] = None) -> dict:
    """Verifica si un pedido puede devolverse según la política de EcoMarket. ..."""
    return returns_service.evaluate_return_eligibility(numero_pedido, motivo, empaque_abierto, producto_usado)
```

```python
# agent.py: inicialización del agente.
llm = ChatOllama(model=AGENT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.0)
agent = create_agent(llm, ALL_TOOLS, system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver())
agent.invoke({"messages": [HumanMessage(mensaje)]},
             config={"configurable": {"thread_id": session_id}, "recursion_limit": 12})
```

El `checkpointer` guarda por sesión la conversación **incluidos los resultados de las
herramientas**. Sin él (primera versión, que pasaba solo el texto del historial), en el
turno 2 el modelo no sabía qué había verificado en el turno 1, y en las pruebas llegó a
**inventar una etiqueta completa** (RMA, guía y dirección falsas).

## 2. Manejo de respuestas: éxito y error

El manejo de errores ocurre en cuatro capas, de la más interna a la más externa:

| Capa | Qué maneja | Cómo |
|---|---|---|
| **Backend** (`returns_service.py`) | Errores de negocio: pedido inexistente, motivo inválido, no elegible, falta información | Nunca lanza excepciones por estos casos: devuelve `{"ok": false, "error": "<código>", "mensaje": "<texto legible>"}` o una `decision` con su `explicacion`. |
| **Herramienta** (`@logged`) | Errores inesperados: archivo corrupto, bug, índice RAG ausente | `try/except` que convierte cualquier excepción en `{"ok": false, "error": "error_interno", ...}`. El LLM recibe un resultado que puede explicar, en lugar de que se rompa el bucle del agente. |
| **Agente** (`run_turn`) | Ollama caído, timeout, límite de pasos (`recursion_limit=12`, evita bucles infinitos de herramientas), respuesta vacía | `try/except` → mensaje de respaldo fijo y amable (`FALLBACK_ERROR_MESSAGE`); el detalle técnico queda en el log y en la UI. Si la respuesta está vacía, se reintenta una vez. |
| **Interfaz** (`app.py`) | Ollama no disponible o modelo no descargado | Verificación al cargar: muestra el comando exacto para solucionarlo y deshabilita el chat. |

El **formato hacia el usuario** lo redacta el LLM a partir de los campos estructurados
de la herramienta (`explicacion`, `pregunta_pendiente`, códigos y fechas). El prompt de
sistema exige no inventar datos y, ante `ok=false`, explicar el problema y qué puede
hacer el cliente. Ejemplos reales de la evaluación:

- **Éxito:** "¡Listo! Tu devolución del pedido ECO1012 fue aprobada. Código de devolución:
  RMA-ECO1012-385357 · Guía (EcoEnvíos): ECOENV3853571012 · Envía el producto a: Bodega
  EcoMarket … · Fecha límite de envío: 2026-05-02 · Costo del envío de retorno: lo asume
  EcoMarket · Etiqueta: descárgala en PDF con el botón que aparece debajo de este mensaje …"
- **Rechazo:** "Lo siento, pero no puedo generar una etiqueta de devolución para este pedido
  ya que se han pasado los 30 días desde su entrega…"
- **Error:** "Lo siento, pero no encontré un pedido con ese número. Por favor, verifica que
  el número esté correcto y inténtalo nuevamente."
- **Escalamiento:** "El valor del pedido ($534,000 COP) supera el límite de $500,000 COP
  para aprobación automática. Por eso, un agente humano revisará tu solicitud (ticket
  TCK-0001)…"

## 3. Guardrails: lo que el código garantiza aunque el LLM falle

Un modelo de 3B parámetros decide bien *la mayoría* de las veces, pero en un proceso
que genera guías y reembolsos "la mayoría" no basta. Después de que el agente responde,
`_apply_guardrails()` revisa el turno con reglas determinísticas:

| Guardrail | Se activa cuando… | Acción |
|---|---|---|
| `reintento_respuesta_vacia` | El modelo devolvió una respuesta vacía (a veces emite una llamada a herramienta malformada) | Reintenta una vez |
| `completar_dato_pendiente` | El turno anterior quedó en `requiere_informacion` ("¿la botella fue usada?"), el cliente respondió con un sí/no claro y el LLM no volvió a verificar | El código re-verifica con ese dato (`producto_usado=False`, etc.) |
| `completar_etiqueta` | La verificación del turno dio `elegible` pero no hay etiqueta generada con éxito | El código genera la etiqueta y responde con una plantilla fija |
| `completar_escalamiento` | La verificación dio `requiere_escalamiento` y el LLM no escaló | El código crea el ticket |
| `fundamentar_con_rag` | El LLM respondió una **pregunta informativa sin usar ninguna herramienta** (es decir, de su "memoria") | Se reemplaza por la respuesta del RAG; si la puerta de relevancia la rechaza, se responde que solo se atienden temas de EcoMarket |
| `codigo_inventado_bloqueado` | La respuesta contiene un `RMA-…`, `TCK-…` o `ECOENV…` que no aparece en ningún resultado de herramienta | Se bloquea la respuesta y se registra una alerta |

Junto con el **router de seguridad previo** y la **re-validación dentro de
`generar_etiqueta_devolucion`**, el resultado es que el LLM controla la conversación,
pero **no puede aprobar algo que la política rechaza, ni dejar a medias algo que la
política aprueba**.

Los guardrails se desactivan con `AGENT_GUARDRAILS=0`, lo que permite medir su efecto.

## 4. Evaluación del comportamiento

`src/agent/evaluate.py` corre 13 conversaciones que cubren todos los caminos del diagrama
de flujo. Para cada una define las herramientas **esperadas** y las **prohibidas**. Por
ejemplo, en una devolución no elegible está prohibido `generar_etiqueta_devolucion`, y en
un saludo está prohibida cualquier herramienta. Así se prueba justamente lo que pide el
enunciado: **discernir cuándo usar herramientas y cuándo responder directamente**. Cada
caso parte de un registro de devoluciones limpio.

### 4.1 Resultados

| Configuración | Casos OK | Casos rescatados por guardrails | Latencia por turno | Reporte |
|---|---|---|---|---|
| `qwen2.5:3b` **sin** guardrails | **8/13** | — | ~1-8 s | [ver](proyecto_final_evaluacion_qwen2_5-3b_sin_guardrails.md) |
| `qwen2.5:3b` **con** guardrails (configuración final) | **13/13** | 6 | ~2-11 s (~20 s la primera consulta RAG, que carga el modelo de embeddings) | [ver](proyecto_final_evaluacion_qwen2_5-3b.md) |
| `qwen3:4b` (sin *thinking*) | **13/13** | 0 | 16-256 s | [ver](proyecto_final_evaluacion_qwen3-4b.md) |

Por caso, con `qwen2.5:3b`:

| Caso | Sin guardrails | Con guardrails |
|---|---|---|
| Saludo → sin herramientas | ✅ | ✅ |
| Envíos internacionales → RAG | ❌ respondió de memoria (por suerte, correcto) | ✅ `fundamentar_con_rag` |
| Precio de la botella → RAG | ❌ respuesta vacía → mensaje de "problema técnico" | ✅ reintento + RAG: $89.000 |
| Estado de ECO1004 → `consultar_pedido` | ✅ | ✅ |
| "Quiero hacer una devolución" → pedir datos, sin herramientas | ✅ | ✅ |
| Devolución elegible ECO1012 → verificar + etiqueta | ❌ verificó, pero no generó la etiqueta | ✅ `completar_etiqueta` |
| Higiene con empaque abierto → no elegible | ✅ | ✅ |
| Fuera de plazo (46 días) → no elegible | ✅ | ✅ |
| Multi-turno: pide "¿fue usada?" → "nunca la usé" → etiqueta | ❌ llamó a la etiqueta sin verificar (bloqueada por la re-validación) | ✅ `completar_dato_pendiente` + `completar_etiqueta` |
| Alto valor ECO1014 → escalar | ❌ verificó, pero no escaló | ✅ `completar_escalamiento` |
| Pedido inexistente → error explicado | ✅ | ✅ |
| "Capital de Francia" → no atender | ✅* respondió "París" sin herramientas | ✅ "Solo puedo ayudarte con temas de EcoMarket" |
| "Me quemé la mano" → escalar | ✅ (router) | ✅ (router) |

\* La evaluación solo verifica herramientas, por eso el caso "pasa" sin guardrails,
aunque la respuesta viola la instrucción del prompt de no atender temas ajenos.

### 4.2 Hallazgos

1. **El LLM pequeño falla al *encadenar* acciones, no al *iniciarlas*.** `qwen2.5:3b` casi
   siempre elige bien la primera herramienta (verificar, consultar). Lo que no hace de
   forma confiable es el segundo paso (generar la etiqueta, escalar), aun cuando el
   resultado de la herramienta le dice literalmente `"siguiente_paso": "Llama ahora a
   generar_etiqueta_devolucion"`. Es la misma lección del Taller 2 ("recuperar el
   contexto correcto no garantiza que un modelo pequeño lo use bien") trasladada a las
   acciones.
2. **El fallo más peligroso fue silencioso.** Sin memoria de herramientas, el modelo
   escribió una etiqueta de devolución completa y verosímil que no existía. Nada en el
   texto lo delataba; solo se detecta comparando contra los resultados reales de las
   herramientas, que es lo que hace `codigo_inventado_bloqueado`.
3. **Responder de memoria es el modo de fallo por defecto.** El prompt dice "llama a la
   herramienta, no respondas de memoria", y aun así el modelo respondió preguntas de
   EcoMarket sin el RAG. Escribir esa instrucción en mayúsculas ("usa SIEMPRE …") empeoró
   el resultado: el modelo copió la palabra en un intento malformado de llamar a la
   herramienta.
4. **Un modelo más capaz reduce la necesidad de guardrails, pero no la elimina como
   diseño.** `qwen3:4b` pasó los 13 casos sin activar ningún guardrail, a un costo de
   latencia inviable en este hardware. Con un servidor con GPU sería la opción preferida,
   y los guardrails quedarían como red de seguridad que, idealmente, nunca se activa (y
   cuya activación es justamente una métrica de monitoreo; ver Fase 3).
5. **Limitación de la evaluación:** 13 casos, una corrida, `temperature=0`. Los casos se
   usaron también para ajustar el prompt y los guardrails, así que el 13/13 es un
   resultado *en entrenamiento*. Un conjunto de prueba independiente (conversaciones
   reales anonimizadas) daría una medida más honesta.

### 4.3 Cómo reproducir

```bash
cd src/agent
python3 evaluate.py                          # configuración final
AGENT_GUARDRAILS=0 python3 evaluate.py       # línea base sin guardrails
AGENT_MODEL=qwen3:4b python3 evaluate.py     # requiere: ollama pull qwen3:4b
python3 agent.py                             # chat en terminal mostrando cada llamada a herramienta
```
