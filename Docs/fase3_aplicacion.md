# Fase 3. Aplicación de la ingeniería de prompts

## 3.0 Configuración del ejercicio

Como lo permite el enunciado del taller, se usa un **modelo open-source** para evidenciar
el impacto de la ingeniería de prompts, sin depender de una API de pago: **Llama 3.2 (1B)**,
ejecutado localmente con [Ollama](https://ollama.com).

El código en `src/` no simula las respuestas con lógica de Python: arma el prompt final
(rol + contexto recuperado + instrucciones) y se lo envía al modelo real a través de
`src/llm_client.py`. Las respuestas mostradas abajo son la salida real del modelo,
generada corriendo `python src/main.py` (ver `README.md` en la raíz del repositorio para
instrucciones de instalación y ejecución).

## 3.1 Ejercicio 1: estado de un pedido

Se preparó un documento con el estado de 10 pedidos (`Data/orders.json`), que actúa como
la base de datos simulada de EcoMarket.

### Prompt básico

```text
Dame el estado del pedido ECO1004.
```

**Salida real del modelo:**

> Lo siento, pero no tengo acceso a información en tiempo real o a bases de datos
> específicas de pedidos anteriores. Mi capacidad para proporcionar detalles sobre un
> pedido específico es limitada a mi entrenamiento hasta diciembre de 2023 [...]

Sin rol, sin contexto y sin datos, el modelo no tiene forma de responder correctamente:
en el mejor caso admite que no sabe, en el peor podría inventar un estado de pedido.

### Prompt mejorado

Ver plantilla completa en `src/prompts.py` (`ORDER_PROMPT_TEMPLATE`). Incluye:

- **Rol**: "Actúa como un agente de servicio al cliente de EcoMarket".
- **Contexto**: la base de pedidos completa, inyectada como texto.
- **Instrucciones explícitas**: tono, campos obligatorios en la respuesta, manejo de
  retrasos y manejo de pedidos no encontrados.

**Salida real del modelo (ECO1004, pedido retrasado):**

> Estimado cliente, [...] tu pedido está actualmente en tránsito y tiene una fecha
> estimada de entrega del 22-04-2026. El enlace de rastreo para este pedido es:
> https://ecomarket.com/track/ECO1004. En cuanto a la causa del retraso [...] alta
> demanda logística por cierre vial en la ruta de distribución [...]

El modelo recuperó correctamente el estado, la fecha, el enlace y el motivo del retraso
directamente del contexto suministrado, algo que el prompt básico no pudo hacer.

### Límite observado (conecta con la Fase 2)

Al consultar un número de seguimiento **inexistente** (`ECO9999`) con el prompt mejorado,
el modelo debía indicar explícitamente que no lo encontró. En su lugar, **alucinó** un
estado plausible ("En tránsito", con fecha y enlace inventados):

> El número de seguimiento consultado es ECO9999. Actualmente, el estado del pedido es
> "En tránsito" [...]

Esto confirma en la práctica el riesgo de **alucinación** identificado en la
[Fase 2](fase2_evaluacion.md): incluso con instrucciones explícitas de "no inventar
información", un modelo pequeño puede fallar en seguirla de forma consistente. En
producción esto refuerza la necesidad de una capa de validación determinista (buscar el
`tracking_number` en la base de datos en código, *antes* de llamar al LLM, y bloquear la
respuesta si no existe) en lugar de confiar en que el modelo "decida" si el dato existe.

## 3.2 Ejercicio 2: devolución de producto

Plantilla completa en `src/prompts.py` (`RETURN_PROMPT_TEMPLATE`). El reto era lograr que
el modelo distinga productos devolvibles de no devolvibles (perecederos, higiene) y
responda con empatía en ambos casos.

**Caso devolvible (botella, sin usar):**

> [...] la categoría del producto es "botellas" y según nuestra política de devolución,
> se acepta devolución dentro de los 30 días si el producto no ha sido usado y conserva
> su empaque [...] te recomiendo seguir adelante con la devolución.

Correcto: identifica la categoría, cita la condición relevante y da el siguiente paso.

**Caso no devolvible (producto de higiene, empaque abierto):**

> [...] el producto es un shampoo sólido natural y su estado de empaque no ha sido
> abierto por razones de salubridad. Por lo tanto, la devolución está permitida [...]

Aquí el modelo **contradice la política** suministrada: el empaque sí estaba abierto y la
categoría es "productos de higiene", por lo que la devolución debía negarse. El modelo de
1B de parámetros mezcló condiciones de otra categoría del contexto en su justificación.

Esto es exactamente el escenario descrito en la Fase 2 como "una respuesta bien redactada
pero operativamente equivocada": el tono es correcto y convincente, pero la decisión de
negocio es incorrecta. Es la evidencia más clara del taller de por qué **un LLM no debe
tener la última palabra en decisiones con impacto económico** sin una verificación
determinista (código que valide `return_allowed` contra la categoría exacta antes de
enviar la respuesta al cliente), y por qué el diseño de la Fase 1 incluye un módulo de
escalamiento humano para casos de baja confianza.

## 3.3 Conclusión

La comparación básico vs. mejorado muestra el impacto directo de la ingeniería de
prompts: rol + contexto + instrucciones explícitas convierten un modelo genérico en un
asistente útil y anclado a datos reales. Al mismo tiempo, ejecutar los prompts contra un
modelo real (no una simulación en Python) expuso limitaciones concretas —alucinación de
datos inexistentes y errores al aplicar reglas— que justifican, en un sistema real, la
capa de recuperación/validación determinista descrita en la Fase 1, en lugar de delegar
el 100% de la decisión al LLM.
