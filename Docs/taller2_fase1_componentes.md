# Taller 2 · Fase 1: Selección de Componentes Clave del Sistema RAG

Este documento justifica las decisiones de arquitectura para incorporar un sistema
RAG (Retrieval-Augmented Generation) a la solución de atención al cliente de
EcoMarket construida en el [Taller 1](../README.md), manteniendo la misma
restricción que ya guio esa solución: **cero dependencias de pago**, todo debe
poder ejecutarse localmente.

## 1. Modelo de embeddings

**Elegido: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`**, servido
localmente vía HuggingFace/`sentence-transformers` (sin llamadas a API externas).

### Por qué este y no un modelo propietario (OpenAI `text-embedding-3`, Cohere, etc.)

| Factor | Modelo propietario (ej. OpenAI embeddings) | `paraphrase-multilingual-MiniLM-L12-v2` |
|---|---|---|
| Costo | Por token, requiere API key y tarjeta de crédito | Gratuito, corre en CPU local |
| Idioma español | Muy bueno, pero es una caja negra | Entrenado explícitamente en 50+ idiomas incluido español, con buen desempeño documentado en tareas de similitud semántica en español |
| Privacidad de datos | Los documentos de EcoMarket (pedidos, políticas) salen hacia un tercero | Los datos nunca salen del servidor/laptop de EcoMarket |
| Dependencia de infraestructura externa | Requiere conectividad constante a la API | Funciona sin internet una vez descargado el modelo |
| Tamaño / latencia | N/A (llamada remota) | ~470MB, genera embeddings de 384 dimensiones en milisegundos por fragmento en CPU |

El caso de EcoMarket (un e-commerce que ya eligió en el Taller 1 un LLM
open-source local —Llama 3.2 1B vía Ollama— precisamente para evitar costos de
API y mantener el control sobre los datos de clientes) hace que un modelo de
embeddings propietario sea inconsistente con esa misma decisión: introduciría de
nuevo una dependencia de pago y una fuga de datos de clientes (números de pedido,
motivos de devolución) hacia un tercero, justo el tipo de riesgo de privacidad que
se identificó en la Fase 2 del Taller 1.

La alternativa open-source de HuggingFace es multilingüe (crítico, porque toda la
base de conocimiento de EcoMarket está en español), suficientemente precisa para
un caso de uso de recuperación semántica de FAQs/políticas (no requiere la
precisión de punta de un modelo de última generación, solo diferenciar bien temas
como "devoluciones", "envíos", "pagos"), y con costo de cómputo bajo (modelo
"MiniLM", pensado para correr rápido en CPU, no requiere GPU).

## 2. Base de datos vectorial

**Elegida: ChromaDB**, en modo embebido/local con persistencia en disco
(`Data/vector_store/`).

### Comparación

| | ChromaDB | Pinecone | Weaviate |
|---|---|---|---|
| Modelo de despliegue | Embebida en el proceso Python, persiste en disco local | Servicio administrado en la nube (SaaS) | Servidor propio (self-hosted, típicamente Docker) o Weaviate Cloud |
| Costo | Gratuito, sin límite de uso ni cuenta | Plan gratuito limitado, luego cobra por uso/almacenamiento | Gratuito si es self-hosted; el plan cloud cobra |
| Facilidad de uso para este caso | Alta: `pip install chromadb` y ya, ideal para un repo educativo que cualquiera debe poder clonar y correr | Media: requiere crear cuenta, API key, y depende de tener internet | Baja para este contexto: requiere levantar y mantener un contenedor/servicio |
| Escalabilidad | Adecuada para la escala de EcoMarket en este taller (cientos/miles de documentos); no pensada para volúmenes masivos multi-nodo | Diseñada para escalar a millones de vectores con baja latencia gestionada | Escala muy bien y agrega búsqueda híbrida (vectorial + BM25), pero con más complejidad operativa |
| Encaja con la restricción "sin costos ni servicios externos" | Sí | No (requiere cuenta en un servicio externo) | Parcialmente (self-hosted es gratis, pero añade una pieza de infraestructura a operar) |

### Justificación

Para el volumen y naturaleza de los documentos de EcoMarket (política de
devoluciones, un catálogo de ~10 productos, un set de FAQs: en total decenas de
fragmentos, no millones), la escalabilidad masiva de Pinecone o Weaviate es
irrelevante y su complejidad operativa (cuentas, API keys, contenedores) no
aporta valor en este contexto educativo/de prototipo. ChromaDB permite que el
flujo completo —desde los documentos crudos hasta la respuesta del LLM— corra
con `python3 src/main.py` en cualquier máquina que clone el repositorio, sin
necesidad de credenciales ni servicios externos, igual que se hizo con Ollama en
el Taller 1.

Si EcoMarket creciera a un catálogo de miles de productos y millones de
interacciones históricas indexadas, la recomendación cambiaría hacia Weaviate
self-hosted (para mantener el control de datos que ya es un valor de la empresa)
o Pinecone si se acepta delegar la infraestructura a un tercero a cambio de
menor esfuerzo operativo.

## 3. Framework de orquestación

Se usa **LangChain**, tal como sugiere el enunciado del taller, para conectar:
carga de documentos (`document_loaders`) → segmentación
(`RecursiveCharacterTextSplitter`) → embeddings (`HuggingFaceEmbeddings`) →
almacenamiento/búsqueda (`Chroma`) → generación aumentada (`Ollama` +
`RetrievalQA`/chain manual). El detalle de esta integración está en la
[Fase 3](../src/rag/README.md).
