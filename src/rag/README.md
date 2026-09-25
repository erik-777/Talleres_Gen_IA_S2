# Taller 2 · Fase 3: Integración y Ejecución del Código RAG

Este paquete implementa, con **LangChain**, el sistema RAG diseñado en las
Fases 1 y 2 del Taller 2 sobre la base del asistente de EcoMarket del Taller 1.

## Cómo se conectan las piezas

```
Data/knowledge_base/*  (política .md, FAQ .json, catálogo .csv)
        │  knowledge_loader.py  (carga + chunking por tipo de documento)
        ▼
   chunks (langchain_core.documents.Document)
        │  build_index.py
        │  HuggingFaceEmbeddings("paraphrase-multilingual-MiniLM-L12-v2")
        ▼
   ChromaDB persistida en Data/vector_store/  (embedding + búsqueda por similitud)
        │  chain.py: vector_store.as_retriever(k=5)
        ▼
   contexto recuperado (top-k chunks)
        │  chain.py: RAG_PROMPT (rol + contexto + pregunta + instrucciones)
        ▼
   OllamaLLM("llama3.2:1b")  →  respuesta final al cliente
```

`main.py` añade un **router** delante de este flujo: si la pregunta contiene un
número de seguimiento (`ECO####`), se resuelve con `order_lookup.py`
(búsqueda exacta en código sobre `Data/orders.json`, sin pasar por el LLM ni
por RAG); en cualquier otro caso, se resuelve con el pipeline RAG completo.
Esta separación está justificada en
[`Docs/taller2_fase2_base_conocimiento.md`](../../Docs/taller2_fase2_base_conocimiento.md).

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Rutas y nombres de modelo centralizados (embedding, LLM, colección de Chroma) |
| `knowledge_loader.py` | Carga y trocea (`chunking`) cada uno de los 3 tipos de documento |
| `build_index.py` | Genera los embeddings y los persiste en ChromaDB (`build_index`), o abre el índice ya existente (`load_index`) |
| `chain.py` | Arma la cadena LCEL retriever → prompt → LLM; incluye la puerta de relevancia (`has_relevant_context`) que evita alucinar cuando no hay contexto suficiente |
| `order_lookup.py` | Búsqueda determinística de pedidos (no pasa por RAG) |
| `main.py` | Router + demo ejecutable de extremo a extremo |

## Cómo ejecutar

Requiere Ollama corriendo con `llama3.2:1b` (igual que en el Taller 1, ver
`README.md` en la raíz del repositorio).

```bash
cd "GEN-IA-S2"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd src/rag
python3 build_index.py   # construye el índice vectorial (una sola vez)
python3 main.py           # corre las consultas de demostración
```

La primera ejecución descarga el modelo de embeddings de HuggingFace
(~470MB) y puede tardar unos minutos; las siguientes ejecuciones reutilizan
el modelo en caché local y el índice ya persistido en `Data/vector_store/`.

## Cómo observar un cambio de comportamiento (modificando código/prompt)

Dos ejemplos rápidos de la conexión entre las piezas, útiles para verificar
que realmente se entiende el flujo:

- **Cambiar el prompt**: editar `RAG_PROMPT` en `chain.py` — por ejemplo,
  quitar la instrucción "No inventes información que no esté en el contexto"
  y volver a correr `main.py` con la pregunta "¿Cuál es la capital de
  Francia?": el modelo deja de negarse y empieza a alucinar una respuesta, en
  vez de reconocer que la pregunta está fuera de la base de conocimiento.
- **Cambiar el retriever**: bajar `RETRIEVER_TOP_K` en `config.py` de 5 a 1 y
  volver a correr `main.py` con la pregunta de devolución del shampoo: al
  recuperar un solo chunk (el del catálogo de producto) en lugar de también
  el de la política de devoluciones, el modelo pierde el contexto de la regla
  de devolución y responde de forma incompleta o genérica.

## Limitaciones y suposiciones

- Se usa **`llama3.2:1b`** (1B de parámetros) por ser el mismo modelo local y
  gratuito ya validado en el Taller 1; es un modelo pequeño y ocasionalmente
  inconsistente en seguir instrucciones al pie de la letra (ver
  `Docs/fase3_aplicacion.md` del Taller 1), por lo que la "puerta de
  relevancia" por distancia (`MAX_RELEVANT_DISTANCE` en `chain.py`) actúa como
  salvaguarda determinística adicional en lugar de confiar 100% en que el
  modelo decida cuándo no sabe algo.
- **Hallazgo durante las pruebas**: con `temperature=0.0` (necesario para que
  las respuestas sean reproducibles) y el prompt inicial, el modelo llegaba a
  responder "no tengo información suficiente" a preguntas cuyo contexto
  recuperado sí contenía la respuesta correcta (ej. el precio de la botella
  térmica), algo que con `temperature=0.2` no pasaba siempre pero tampoco era
  consistente entre corridas. Esto confirma, en el contexto de RAG, la misma
  conclusión del Taller 1: **la recuperación de contexto correcta no garantiza
  que un LLM pequeño lo use bien al generar la respuesta**. La mitigación
  aplicada fue reescribir el prompt (`RAG_PROMPT` en `chain.py`) de forma más
  directa y explícita ("si el CONTEXTO tiene la respuesta, respóndela citando
  el dato exacto"), lo que en las pruebas mejoró notablemente la fidelidad al
  contexto recuperado, aunque persisten pequeños errores puntuales (ej. el
  modelo redondeó "$89.000" a "$89.900" en una corrida) — otra evidencia de por
  qué datos transaccionales exactos (precios, estados de pedido) no deberían
  depender de que el LLM los transcriba correctamente de memoria de lo leído.
- **Consistencia verificada con `temperature=0.0`**: se corrió `main.py` 3
  veces seguidas sobre las mismas 6 preguntas de demostración y las 6
  respuestas fueron idénticas byte a byte en las 3 corridas — a diferencia de
  `temperature=0.2`, donde la misma pregunta podía dar una respuesta correcta
  en una corrida y "no tengo información" en la siguiente. Para un caso de uso
  de atención al cliente, donde dos clientes con la misma pregunta deberían
  recibir la misma respuesta, `temperature=0.0` es la elección correcta a
  pesar de que reduce ligeramente la naturalidad del texto generado.
- **Falla de fundamentación reproducible, no del retriever**: para la pregunta
  "¿EcoMarket hace envíos a otros países?", el retriever recupera
  correctamente en primer lugar el chunk exacto de la FAQ (distancia L2 6.77,
  muy por debajo del umbral de 25) y la puerta de relevancia lo deja pasar sin
  problema; sin embargo, el LLM de todas formas responde "no tengo
  información suficiente". Es un fallo 100% reproducible (idéntico en las 3
  corridas), lo que descarta que sea una falla del pipeline de recuperación:
  el contexto correcto llega al modelo, pero el modelo de 1B de parámetros no
  logra reconocerlo como relevante para esa pregunta en particular. Es la
  evidencia más clara de este taller de que un sistema RAG resuelve el
  problema de *tener* la información correcta disponible, pero no elimina por
  sí solo el riesgo de que un modelo pequeño falle al *usarla*.
- El umbral de distancia (`MAX_RELEVANT_DISTANCE = 25`) se calibró
  empíricamente observando las distancias L2 reales que devuelve ChromaDB con
  este modelo de embeddings sobre la base de conocimiento de este taller; con
  un corpus mucho más grande o heterogéneo este valor tendría que
  recalibrarse.
- No se usó una GPU: todo el pipeline (embeddings + LLM) corre en CPU, lo cual
  es suficiente para el volumen de datos de este taller (31 chunks) pero no
  representa el tiempo de respuesta que tendría un despliegue en producción
  con miles de documentos.
