# Taller 2 · Fase 2: Creación de la Base de Conocimiento de Documentos

## 1. Documentos identificados

Se identificaron 3 tipos de documentos de EcoMarket, cada uno relevante para un
tipo distinto de consulta de atención al cliente, ubicados en
`Data/knowledge_base/`:

| Documento | Tipo | Contenido | Consultas que resuelve |
|---|---|---|---|
| `politica_devoluciones.md` | Texto/PDF (simulado como Markdown) | Reglas de devolución por categoría de producto, plazos, costos de envío de retorno, casos de escalamiento humano | "¿Puedo devolver este producto?", "¿Cuánto tarda el reembolso?" |
| `preguntas_frecuentes.json` | JSON semiestructurado | 10 preguntas frecuentes con respuesta, categorizadas (envíos, pagos, cuenta, sostenibilidad, devoluciones, productos) | "¿Qué métodos de pago aceptan?", "¿Son reciclables sus empaques?" |
| `catalogo_productos.csv` | Hoja de cálculo (CSV) | Catálogo de 10 productos con SKU, categoría, precio, stock y descripción | "¿Cuánto cuesta la botella térmica?", "¿Tienen shampoo sólido disponible?" |

### Nota de diseño: qué se deja **fuera** de la base RAG

`Data/orders.json` (los 10 pedidos de ejemplo del Taller 1) **no** se indexa en
el sistema RAG. Como se documentó en la
[conclusión de la Fase 3 del Taller 1](../Docs/fase3_aplicacion.md), consultar el
estado de un pedido específico es una búsqueda exacta por `tracking_number`, no
una búsqueda semántica: el sistema RAG puede recuperar el fragmento
"parecido" a la pregunta, pero no garantiza que sea el pedido correcto, lo cual
es inaceptable para un dato transaccional. Por eso el estado de pedidos se sigue
resolviendo con una búsqueda determinística en código (ver
`src/rag/order_lookup.py`), y el sistema RAG se reserva para conocimiento
general de la empresa (políticas, catálogo, FAQs) donde sí aporta valor recuperar
el fragmento semánticamente más relevante.

## 2. Estrategia de segmentación (chunking)

Se evaluaron tres estrategias:

1. **Tamaño fijo (fixed-size chunking)**: cortar cada documento cada N
   caracteres, sin importar el contenido. Es la más simple, pero puede partir una
   oración o una condición de devolución justo a la mitad, perdiendo el contexto
   necesario para responder bien (ej. separar "no se acepta devolución" de "si el
   empaque ha sido abierto").
2. **Por párrafos**: respeta los saltos de párrafo del documento. Funciona bien
   para `politica_devoluciones.md`, pero no aplica igual para el CSV o el JSON,
   que no tienen "párrafos" naturales.
3. **Recursiva (`RecursiveCharacterTextSplitter` de LangChain)**: intenta cortar
   primero por separadores "grandes" (secciones `##`, párrafos `\n\n`) y solo si
   un fragmento sigue siendo muy grande, cae a separadores más pequeños (oración,
   espacio). Es una combinación adaptativa de las dos anteriores.

**Estrategia elegida: segmentación recursiva, con reglas distintas por tipo de
documento**:

- **`politica_devoluciones.md`** → `RecursiveCharacterTextSplitter` con
  `chunk_size=500` y `chunk_overlap=80`, usando como separadores prioritarios los
  encabezados de sección (`\n## `, `\n### `) y luego párrafos (`\n\n`). Esto
  asegura que cada chunk contenga una sección completa (ej. toda la política de
  "productos de higiene") en lugar de partirla a la mitad. El `overlap` evita que
  se pierda contexto en el borde entre una regla y su excepción.
- **`preguntas_frecuentes.json`** → no se trocea con el splitter de texto: cada
  objeto `{pregunta, respuesta}` del JSON **ya es un chunk natural** (una unidad
  de sentido completa y autocontenida). Trocear una FAQ a la mitad no tendría
  sentido semántico, así que el "chunking" aquí es a nivel de registro, no de
  caracteres.
- **`catalogo_productos.csv`** → de forma análoga, cada **fila** (un producto) es
  un chunk natural: se serializa como una pequeña ficha de texto
  (`"Producto: X | Categoría: Y | Precio: $Z | Stock: W | Descripción: ..."`)
  para que el embedding capture el significado completo del producto, en vez de
  vectorizar celdas sueltas de una tabla sin contexto.

Esta combinación (recursivo para texto largo, "un registro = un chunk" para datos
estructurados) es mejor que aplicar tamaño fijo a todo, porque respeta la unidad
de sentido natural de cada tipo de documento: en texto libre esa unidad es la
sección/párrafo, mientras que en datos tabulares/JSON esa unidad ya viene
delimitada por el propio formato del archivo.

## 3. Indexación

El proceso de indexación (implementado en `src/rag/build_index.py`) sigue estos
pasos:

1. **Carga (`load`)**: cada tipo de documento usa el loader de LangChain
   adecuado a su formato — `TextLoader`/lectura de Markdown para la política,
   un loader propio que itera el JSON de FAQs, y un loader propio que itera las
   filas del CSV del catálogo.
2. **Segmentación (`split`)**: se aplica la estrategia descrita en la sección 2
   a cada documento, generando una lista de fragmentos de texto (`chunks`), cada
   uno con metadatos (`source`, `categoria`/`sku` cuando aplica) para poder
   rastrear de qué documento salió la respuesta.
3. **Embedding**: cada chunk se convierte en un vector de 384 dimensiones con
   `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (justificado en
   la [Fase 1](taller2_fase1_componentes.md)).
4. **Carga en la base vectorial**: los vectores, junto con el texto original del
   chunk y sus metadatos, se insertan en una colección de **ChromaDB** persistida
   en `Data/vector_store/`. Esto se hace una sola vez (o cada vez que cambian los
   documentos fuente); en tiempo de consulta el sistema **no** vuelve a
   embeber los documentos, solo la pregunta del usuario, y busca por similitud
   coseno los `k` chunks más cercanos.

El resultado es una base de conocimiento consultable: dada una pregunta del
cliente, el sistema recupera los fragmentos más relevantes (sin importar de cuál
de los 3 documentos vengan) y se los entrega al LLM como contexto para generar la
respuesta final, en lugar de que el LLM responda solo con lo que "recuerda" de su
entrenamiento.
