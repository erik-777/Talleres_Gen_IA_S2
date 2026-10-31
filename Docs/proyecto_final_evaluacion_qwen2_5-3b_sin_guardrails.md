# Proyecto Final - Resultados de la evaluación del agente

_Generado automáticamente por `src/agent/evaluate.py` el 2026-10-31 10:35 con el modelo `qwen2.5:3b` (temperature=0), guardrails DESACTIVADOS._

**Resultado: 8/13 casos pasan.** Un caso pasa si el agente usa las herramientas esperadas y ninguna de las prohibidas (ver `CASES` en `evaluate.py`). De los casos que pasan, 0 necesitaron que un guardrail completara o corrigiera la respuesta del LLM (columna Guardrails).

| Caso | Mensaje(s) del usuario | Herramientas usadas | Guardrails | Resultado |
|---|---|---|---|---|
| `saludo` | “Hola, buenos días” | _ninguna_ | — | ✅ |
| `faq_envios` | “¿EcoMarket hace envíos a otros países?” | _ninguna_ | — | ❌ faltó usar ['buscar_informacion_ecomarket'] |
| `precio_catalogo` | “¿Cuánto cuesta la botella térmica de acero?” | _ninguna_ | — | ❌ faltó usar ['buscar_informacion_ecomarket'] |
| `estado_pedido` | “¿Cuál es el estado de mi pedido ECO1004?” | `consultar_pedido` | — | ✅ |
| `devolucion_sin_datos` | “Quiero hacer una devolución” | _ninguna_ | — | ✅ |
| `devolucion_elegible` | “Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí” | `verificar_elegibilidad_devolucion` | — | ❌ faltó usar ['generar_etiqueta_devolucion'] |
| `devolucion_no_elegible_higiene` | “Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `devolucion_fuera_de_plazo` | “Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `devolucion_pide_info_multiturno` | “Quiero devolver la botella del pedido ECO1011, cambié de opinión” → “No, nunca la he usado, sigue nueva en su caja” | `generar_etiqueta_devolucion` | — | ❌ faltó usar ['verificar_elegibilidad_devolucion'] |
| `devolucion_alto_valor` | “Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica” | `verificar_elegibilidad_devolucion` | — | ❌ faltó usar ['escalar_a_humano'] |
| `pedido_inexistente` | “Quiero devolver el pedido ECO9999 porque llegó dañado” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `fuera_de_dominio` | “¿Cuál es la capital de Francia?” | _ninguna_ | — | ✅ |
| `riesgo_seguridad` | “La botella del pedido ECO1011 se calentó y me quemé la mano” | `escalar_a_humano` (router de seguridad) | — | ✅ |

## Respuestas completas del agente

### `saludo` (0.7 s)

> **Cliente:** Hola, buenos días

**Agente:** Buenos días, cómo puedo ayudarte hoy?

### `faq_envios` (1.3 s)

> **Cliente:** ¿EcoMarket hace envíos a otros países?

**Agente:** Lo siento, EcoMarket actualmente no realiza envíos a otros países. Ofrecemos servicios exclusivamente para Colombia.

### `precio_catalogo` (1.9 s)

> **Cliente:** ¿Cuánto cuesta la botella térmica de acero?

**Agente:** Para obtener el precio exacto de la botella térmica de acero, necesitaría que me proporciones más detalles como su tamaño y modelo. ¿Podrías proporcionar esa información?

### `estado_pedido` (5.8 s)

> **Cliente:** ¿Cuál es el estado de mi pedido ECO1004?

**Agente:** Tu pedido ECO1004 está retrasado. La entrega está programada para el 22 de abril, pero debido a una alta demanda y un cierre de vía en la ruta de distribución, no tenemos una fecha estimada de entrega concreta aún. Puedes seguir el estado de tu pedido en este enlace: [Rastreo del pedido](https://ecomarket.example/track/ECO1004).

### `devolucion_sin_datos` (1.7 s)

> **Cliente:** Quiero hacer una devolución

**Agente:** Por supuesto. Para poder ayudarte con la devolución necesito el número de pedido y el motivo por el cual deseas devolverlo. ¿Podrías proporcionarme estos detalles?

### `devolucion_elegible` (6.4 s)

> **Cliente:** Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí

**Agente:** Tu pedido ECO1012 está elegible para una devolución. Voy a generar la etiqueta de devolución. Llámame cuando quieras descargarla y recibirás un código RMA, una guía, la dirección de la bodega y la fecha límite para enviar el producto de regreso.  
  
Haz clic en este botón para descargar la etiqueta de devolución: [Descargar Etiqueta](#)

### `devolucion_no_elegible_higiene` (7.4 s)

> **Cliente:** Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó

**Agente:** ECO1006 es un pedido de productos de higiene personal ecológico. Según nuestra política, no podemos aceptar devoluciones para este tipo de productos debido a su naturaleza sensible y por razones de sostenibilidad.  
  
El empaque del producto ya fue abierto. ¿Podrías confirmarme si el cliente abrió el empaque? Esto nos ayudará a seguir con la verificación de tu solicitud de devolución.

### `devolucion_fuera_de_plazo` (7.0 s)

> **Cliente:** Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica

**Agente:** Lo siento, pero no puedo generar una etiqueta de devolución para tu pedido debido a que ya han pasado 46 días desde la entrega y el plazo máximo de devolución es de 30 días. Según nuestra política, los pedidos deben ser devueltos dentro de un mes desde la fecha de entrega.  
  
Si tienes alguna otra pregunta o necesitas ayuda con algo más, estaré encantado de asistirte.

### `devolucion_pide_info_multiturno` (9.2 s)

> **Cliente:** Quiero devolver la botella del pedido ECO1011, cambié de opinión
> **Cliente:** No, nunca la he usado, sigue nueva en su caja

**Agente:** La botella no llegó a ser usada. Voy a necesitar que me digas si el envase está abierto o si has abierto el empaque.  
  
Pregunta: ¿El envase está abierto?

### `devolucion_alto_valor` (8.1 s)

> **Cliente:** Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica

**Agente:** El pedido ECO1014 ha sido verificado como elegible para una devolución por defecto de fábrica. Sin embargo, debido al valor del pedido ($534,000 COP), la aprobación automática no es posible y necesitamos que un agente humano lo atienda.  
  
Llama ahora a escalar_a_humano con el motivo "defecto_fabrica" para continuar con el proceso. Te proporcionarán una guía de envío y la dirección de nuestra bodega donde puedes enviar tu devolución.

### `pedido_inexistente` (4.7 s)

> **Cliente:** Quiero devolver el pedido ECO9999 porque llegó dañado

**Agente:** Lo siento, pero no encontramos un pedido con ese número. Por favor, verifica que el número esté correcto y inténtalo nuevamente.

### `fuera_de_dominio` (0.8 s)

> **Cliente:** ¿Cuál es la capital de Francia?

**Agente:** La capital de Francia es París.

### `riesgo_seguridad` (0.1 s)

> **Cliente:** La botella del pedido ECO1011 se calentó y me quemé la mano

**Agente:** Lamento mucho lo ocurrido. Como tu mensaje menciona un posible riesgo para tu salud o seguridad, un agente humano revisará tu caso con prioridad (ticket TCK-0001). Un agente humano te contactará en máximo 24 horas hábiles. Si es una emergencia médica, por favor acude a un servicio de salud de inmediato.

