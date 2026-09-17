# EcoMarket AI Support

Solución propuesta para el Taller Práctico #1: "Optimización de la Atención al Cliente
en una Empresa de E-commerce". El caso: EcoMarket recibe miles de consultas diarias
(80% repetitivas: pedidos, devoluciones, producto) con un tiempo de respuesta promedio
de 24 horas.

## Estructura del proyecto

| Fase | Contenido | Archivo |
|---|---|---|
| 1. Selección y justificación del modelo de IA | Arquitectura híbrida propuesta (LLM + recuperación de datos) y por qué | [Docs/fase1_modelo.md](Docs/fase1_modelo.md) |
| 2. Fortalezas, limitaciones y riesgos éticos | Alucinaciones, sesgo, privacidad, impacto laboral y mitigaciones | [Docs/fase2_evaluacion.md](Docs/fase2_evaluacion.md) |
| 3. Ingeniería de prompts | Prompt básico vs. mejorado, ejercicios de pedido/devolución y resultados reales del modelo | [Docs/fase3_aplicacion.md](Docs/fase3_aplicacion.md) |

Datos de soporte para la Fase 3 (simulan la base de datos interna de EcoMarket):

- `Data/orders.json`: 10 pedidos de ejemplo (estado, entrega estimada, enlace de rastreo).
- `Data/return_policies.json`: políticas de devolución por categoría de producto.

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

## Estructura del repositorio

```
GEN-IA-S2/
├── README.md
├── Data/
│   ├── orders.json
│   └── return_policies.json
├── Docs/
│   ├── fase1_modelo.md
│   ├── fase2_evaluacion.md
│   └── fase3_aplicacion.md
├── src/
│   ├── main.py          # arma los prompts con contexto real y llama al LLM
│   ├── prompts.py        # plantillas de prompts (básico y mejorado)
│   └── llm_client.py      # cliente HTTP hacia Ollama
└── Talleres/
    └── Taller 1.pdf
```
