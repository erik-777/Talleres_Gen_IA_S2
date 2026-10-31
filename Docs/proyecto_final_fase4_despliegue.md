# Proyecto Final — Fase 4: Despliegue de la aplicación

## 1. Selección de la herramienta: Streamlit

| Criterio | Streamlit | Gradio |
|---|---|---|
| **Interfaz de chat** | `st.chat_input` + `st.chat_message`: chat nativo con avatares e historial. | `gr.ChatInterface`: chat completo en una línea. Gradio gana en rapidez inicial. |
| **Mostrar *qué hizo* el agente** | Cada respuesta puede llevar debajo un `st.expander` con las herramientas llamadas, sus argumentos y resultados (`st.json`) y los guardrails activados (`st.warning`), todo en la misma burbuja del chat. | Requiere salir de `ChatInterface` y construir un layout con `gr.Blocks` y eventos, o usar los "metadata" de mensajes, que son más limitados para mostrar JSON. |
| **Controles de la demo** | Barra lateral con botones de ejemplos, "nueva conversación" y "reiniciar datos" en pocas líneas, con `st.session_state` para la sesión de memoria del agente. | Posible con `gr.Blocks`, pero con más código de eventos. |
| **Modelo de ejecución** | Script que se re-ejecuta en cada interacción: simple de razonar. El agente y el índice RAG quedan en caché entre ejecuciones a nivel de módulo. | Basado en callbacks; igual de válido. |
| **Despliegue** | Streamlit Community Cloud, o `streamlit run` en cualquier servidor. | Hugging Face Spaces (excelente), o `launch(share=True)` para un enlace temporal. |

**Decisión: Streamlit.** Para un *agente*, lo importante de la interfaz no es solo
mostrar la respuesta, sino hacer **visible y auditable cada acción** que tomó (qué
herramienta, con qué datos, qué decidió). Así lo pide la demostración ("demostrar el
uso de herramientas") y así lo recomienda el análisis de la Fase 3 (transparencia y
observabilidad). Streamlit permite incrustar esa traza en cada mensaje del chat de
forma natural. Gradio habría sido igual de válido para un chat simple, y algo más
rápido de montar.

## 2. Implementación de la interfaz (`src/agent/app.py`)

- **Campo de texto** (`st.chat_input`) para el mensaje del cliente y **área de chat** con
  el historial de la conversación.
- Bajo cada respuesta del agente, un desplegable **"Acciones del agente:
  ✅ verificar_elegibilidad_devolucion → 🏷️ generar_etiqueta_devolucion"** con argumentos,
  resultado JSON y latencia de cada herramienta. Si el agente respondió sin herramientas,
  se indica explícitamente ("Respondió directamente, sin usar herramientas"), lo que
  hace visible la capacidad de discernir cuándo usarlas.
- **Descarga de la etiqueta:** cuando el agente genera una devolución, aparece debajo de
  la respuesta un botón **"📄 Descargar etiqueta RMA-… (PDF)"** con la etiqueta imprimible
  (remitente, bodega de destino, código de barras de la guía, fecha límite y quién paga
  el envío). Es el resultado tangible de la acción del agente.
- **Datos simulados explícitos:** los enlaces de rastreo usan el dominio reservado
  `ecomarket.example` (RFC 2606), para no enviar al usuario a un sitio real ajeno al
  proyecto, y la barra lateral lo advierte.
- **Barra lateral:** descripción, modelo y fecha simulada, 9 **botones de ejemplo** que
  cubren todos los caminos del diagrama de flujo, "Nueva conversación" (nueva sesión de
  memoria) y "Reiniciar datos de la demo" (borra etiquetas, rechazos y tickets simulados).
- **Manejo de errores visible:** si Ollama no está corriendo o falta el modelo, la app
  muestra cómo solucionarlo y deshabilita el chat en vez de fallar. Los precios con `$`
  se escapan para que Streamlit no los interprete como fórmulas LaTeX.

## 3. Cómo ejecutar

```bash
# Desde la raíz del repositorio
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ollama serve                 # si no está corriendo ya
ollama pull qwen2.5:3b       # modelo del agente (1.9 GB)

cd src/rag && python3 build_index.py && cd ../..   # índice RAG (solo la primera vez)

streamlit run src/agent/app.py
```

Se abre en `http://localhost:8501`. La primera consulta general tarda unos segundos
más, porque carga el modelo de embeddings del RAG.

Alternativas sin interfaz: `cd src/agent && python3 agent.py` (chat en terminal que
imprime cada llamada a herramienta) y `python3 evaluate.py` (batería de pruebas).

## 4. Guion sugerido para la demostración del video (3-4 min)

Antes de grabar: pulsar **"Reiniciar datos de la demo"** y hacer una consulta de
calentamiento (fuera de cámara) para que el modelo ya esté cargado en memoria.

| # | Prompt (botón de ejemplo) | Qué demuestra | Resultado esperado |
|---|---|---|---|
| 1 | "Hola, buenos días" (escrito a mano) | Responde **sin herramientas** cuando no hacen falta | Saludo; "Respondió directamente" |
| 2 | Pregunta general (RAG) | Integración del RAG del Taller 2 como herramienta | 📚 `buscar_informacion_ecomarket` → solo envíos dentro de Colombia |
| 3 | Devolución elegible (ECO1012) | Flujo feliz completo | ✅ verificar → 🏷️ generar: código RMA, guía, bodega, fecha límite, EcoMarket paga el envío. **Descargar y abrir el PDF de la etiqueta** |
| 4 | Devolución que pide más datos (ECO1011) → escribir "No, nunca la he usado" | Multi-turno: el agente pide el dato que falta y continúa | `requiere_informacion` → pregunta → verificar de nuevo → etiqueta |
| 5 | Fuera de plazo (ECO1013) o no elegible (ECO1006) | Manejo de rechazo amable | Explica "46 días > 30" o "empaque abierto de higiene" |
| 6 | Alto valor (ECO1014) | Escalamiento por política | 🧑‍💼 ticket TCK, aprobación humana requerida |
| 7 | Pedido inexistente (ECO9999) | Manejo de errores | Explica que el pedido no existe y el formato correcto |
| 8 | Riesgo de seguridad | Router por reglas sin LLM | 🚨 escalamiento inmediato con mensaje de prioridad |

Abrir el desplegable "Acciones del agente" en los casos 3, 4 y 6 para mostrar los
argumentos y resultados JSON de las herramientas.
