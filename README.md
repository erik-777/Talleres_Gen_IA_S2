# EcoMarket AI Support

Solución propuesta para el Taller Práctico #1: "Optimización de la Atención al Cliente
en una Empresa de E-commerce", su extensión en el Taller Práctico #2, que incorpora un
sistema RAG (Generación Aumentada por Recuperación), y el **Proyecto Final**, que agrega
un agente de IA capaz de tramitar devoluciones de forma autónoma, con interfaz web. El caso: EcoMarket recibe miles de
consultas diarias (80% repetitivas: pedidos, devoluciones, producto) con un tiempo de
respuesta promedio de 24 horas.

## Taller 1: ingeniería de prompts

| Fase | Contenido | Archivo |
|---|---|---|
| 1. Selección y justificación del modelo de IA | Arquitectura híbrida propuesta (LLM + recuperación de datos) y por qué | [Docs/fase1_modelo.md](Docs/fase1_modelo.md) |
| 2. Fortalezas, limitaciones y riesgos éticos | Alucinaciones, sesgo, privacidad, impacto laboral y mitigaciones | [Docs/fase2_evaluacion.md](Docs/fase2_evaluacion.md) |
| 3. Ingeniería de prompts | Prompt básico vs. mejorado, ejercicios de pedido/devolución y resultados reales del modelo | [Docs/fase3_aplicacion.md](Docs/fase3_aplicacion.md) |

Datos de soporte para la Fase 3 del Taller 1 (simulan la base de datos interna de EcoMarket):

- `Data/orders.json`: 14 pedidos de ejemplo (estado, entrega estimada, enlace de rastreo;
  el Proyecto Final agregó `delivered_date`, `quantity` y los pedidos ECO1011-ECO1014).
- `Data/return_policies.json`: políticas de devolución por categoría de producto.

## Taller 2: sistema RAG

| Fase | Contenido | Archivo |
|---|---|---|
| 1. Selección de componentes RAG | Justificación del modelo de embeddings y la base de datos vectorial | [Docs/taller2_fase1_componentes.md](Docs/taller2_fase1_componentes.md) |
| 2. Base de conocimiento | Documentos identificados, estrategia de chunking e indexación | [Docs/taller2_fase2_base_conocimiento.md](Docs/taller2_fase2_base_conocimiento.md) |
| 3. Integración y ejecución del código | Implementación con LangChain + ChromaDB + Ollama | [src/rag/README.md](src/rag/README.md) |

Base de conocimiento para el sistema RAG (`Data/knowledge_base/`):

- `politica_devoluciones.md`: política de devoluciones detallada por categoría (simula un PDF).
- `preguntas_frecuentes.json`: 10 preguntas frecuentes de envíos, pagos, cuenta y sostenibilidad.
- `catalogo_productos.csv`: catálogo de 10 productos con precio, categoría y stock.

## Cómo ejecutar el sistema RAG (Taller 2)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd src/rag
python3 build_index.py   # construye el índice vectorial una sola vez
python3 main.py            # corre el router (RAG + búsqueda determinística de pedidos)
```

Requiere Ollama corriendo con `llama3.2:1b` (ver instalación abajo). Más detalle de la
arquitectura y cómo modificar el código para observar cambios de comportamiento en
[src/rag/README.md](src/rag/README.md).

## Cómo ejecutar el código de la Fase 3

El código llama a un modelo de lenguaje **real** (no simula respuestas con Python) para
evidenciar el impacto de la ingeniería de prompts, usando un modelo **open-source** local
vía [Ollama](https://ollama.com), tal como lo permite el enunciado del taller.

1. Instalar Ollama: https://ollama.com/download (o `brew install ollama` en macOS).
2. Descargar el modelo usado en este proyecto:
   ```bash
   ollama pull llama3.2:1b
   ```
3. Asegurarse de que el servicio de Ollama esté corriendo (`ollama serve`, o el servicio
   en segundo plano que instala la app de Ollama).
4. Ejecutar la demo:
   ```bash
   cd src
   python3 main.py
   ```

Esto imprime, en orden: el prompt básico vs. el prompt mejorado para una consulta de
pedido, un caso de pedido inexistente, y dos casos de devolución (uno permitido y uno no
permitido). El análisis de esas salidas está en
[Docs/fase3_aplicacion.md](Docs/fase3_aplicacion.md).

## Proyecto Final: agente de IA para devoluciones

| Fase | Contenido | Archivo |
|---|---|---|
| 1. Diseño de la arquitectura | Arquitectura híbrida (agente + router por reglas), 5 herramientas, LangChain vs LlamaIndex, elección del modelo, diagrama de flujo | [Docs/proyecto_final_fase1_arquitectura.md](Docs/proyecto_final_fase1_arquitectura.md) |
| 2. Implementación | Estructura del código, manejo de éxito/error, guardrails, evaluación del comportamiento | [Docs/proyecto_final_fase2_implementacion.md](Docs/proyecto_final_fase2_implementacion.md) |
| 3. Análisis crítico | Riesgos éticos y de seguridad (observados y mitigados), monitoreo, propuestas de mejora | [Docs/proyecto_final_fase3_analisis.md](Docs/proyecto_final_fase3_analisis.md) |
| 4. Despliegue | Streamlit vs Gradio, interfaz, cómo ejecutar, guion de la demo | [Docs/proyecto_final_fase4_despliegue.md](Docs/proyecto_final_fase4_despliegue.md) |

### Cómo ejecutar el agente (Proyecto Final)

```bash
source .venv/bin/activate && pip install -r requirements.txt
ollama pull qwen2.5:3b                              # modelo del agente (tool calling)
cd src/rag && python3 build_index.py && cd ../..    # índice RAG, solo la primera vez

streamlit run src/agent/app.py                      # interfaz web (http://localhost:8501)
cd src/agent && python3 evaluate.py                 # batería de pruebas del agente
```

## Estructura del repositorio

```
GEN-IA-S2/
├── README.md
├── requirements.txt
├── Data/
│   ├── orders.json
│   ├── return_policies.json
│   ├── knowledge_base/        # documentos fuente del sistema RAG (Taller 2)
│   │   ├── politica_devoluciones.md
│   │   ├── preguntas_frecuentes.json
│   │   └── catalogo_productos.csv
│   ├── vector_store/           # índice de ChromaDB persistido (generado, no versionado)
│   ├── returns/                # etiquetas y registro de devoluciones simuladas (generado)
│   └── logs/                   # agent_actions.jsonl: registro de acciones del agente (generado)
├── Docs/
│   ├── fase1_modelo.md
│   ├── fase2_evaluacion.md
│   ├── fase3_aplicacion.md
│   ├── taller2_fase1_componentes.md
│   └── taller2_fase2_base_conocimiento.md
├── src/
│   ├── main.py             # Taller 1: arma los prompts con contexto real y llama al LLM
│   ├── prompts.py           # Taller 1: plantillas de prompts (básico y mejorado)
│   ├── llm_client.py         # Taller 1: cliente HTTP hacia Ollama
│   ├── rag/                  # Taller 2: sistema RAG (LangChain + ChromaDB + Ollama)
│       ├── README.md
│       ├── config.py
│       ├── knowledge_loader.py
│       ├── build_index.py
│       ├── chain.py
│       ├── order_lookup.py
│   │   └── main.py
│   └── agent/                # Proyecto Final: agente de devoluciones + interfaz Streamlit
│       ├── agent_config.py   # modelo, fecha simulada, umbrales de la política, rutas
│       ├── returns_service.py # backend simulado: reglas de elegibilidad, etiquetas, tickets
│       ├── tools.py          # las 5 herramientas (@tool) que ve el LLM
│       ├── action_log.py     # registro de acciones (observabilidad)
│       ├── agent.py          # router + agente LangChain + guardrails
│       ├── evaluate.py       # evaluación del comportamiento
│       └── app.py            # interfaz web (Streamlit)
└── Talleres/
    ├── Taller 1.pdf
    └── Taller2.md
```
