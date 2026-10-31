# Proyecto Final - Resultados de la evaluación del agente

_Generado automáticamente por `src/agent/evaluate.py` el 2026-10-31 10:40 con el modelo `qwen2.5:3b` (temperature=0), guardrails activados._

**Resultado: 13/13 casos pasan.** Un caso pasa si el agente usa las herramientas esperadas y ninguna de las prohibidas (ver `CASES` en `evaluate.py`). De los casos que pasan, 6 necesitaron que un guardrail completara o corrigiera la respuesta del LLM (columna Guardrails).

| Caso | Mensaje(s) del usuario | Herramientas usadas | Guardrails | Resultado |
|---|---|---|---|---|
| `saludo` | “Hola, buenos días” | _ninguna_ | — | ✅ |
| `faq_envios` | “¿EcoMarket hace envíos a otros países?” | `buscar_informacion_ecomarket` | `fundamentar_con_rag` | ✅ |
| `precio_catalogo` | “¿Cuánto cuesta la botella térmica de acero?” | `buscar_informacion_ecomarket` | `fundamentar_con_rag` | ✅ |
| `estado_pedido` | “¿Cuál es el estado de mi pedido ECO1004?” | `consultar_pedido` | — | ✅ |
| `devolucion_sin_datos` | “Quiero hacer una devolución” | _ninguna_ | — | ✅ |
| `devolucion_elegible` | “Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí” | `verificar_elegibilidad_devolucion`, `generar_etiqueta_devolucion` | `completar_etiqueta` | ✅ |
| `devolucion_no_elegible_higiene` | “Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `devolucion_fuera_de_plazo` | “Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `devolucion_pide_info_multiturno` | “Quiero devolver la botella del pedido ECO1011, cambié de opinión” → “No, nunca la he usado, sigue nueva en su caja” | `generar_etiqueta_devolucion`, `verificar_elegibilidad_devolucion`, `generar_etiqueta_devolucion` | `completar_dato_pendiente`, `completar_etiqueta` | ✅ |
| `devolucion_alto_valor` | “Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica” | `verificar_elegibilidad_devolucion`, `escalar_a_humano` | `completar_escalamiento` | ✅ |
| `pedido_inexistente` | “Quiero devolver el pedido ECO9999 porque llegó dañado” | `verificar_elegibilidad_devolucion` | — | ✅ |
| `fuera_de_dominio` | “¿Cuál es la capital de Francia?” | `buscar_informacion_ecomarket` | `fundamentar_con_rag` | ✅ |
| `riesgo_seguridad` | “La botella del pedido ECO1011 se calentó y me quemé la mano” | `escalar_a_humano` (router de seguridad) | — | ✅ |

## Respuestas completas del agente

### `saludo` (5.1 s)

> **Cliente:** Hola, buenos días

**Agente:** Buenos días, cómo puedo ayudarte hoy?

### `faq_envios` (23.7 s)

> **Cliente:** ¿EcoMarket hace envíos a otros países?

**Agente:** Por ahora solo realizamos envíos dentro de Colombia. Estamos evaluando expandir la cobertura a otros países de la región en el futuro.

### `precio_catalogo` (13.7 s)

> **Cliente:** ¿Cuánto cuesta la botella térmica de acero?

**Agente:** La botella térmica de acero cuesta $89000 COP. Según la política de devoluciones, se acepta la devolución dentro de los 30 días si el producto no ha sido usado y conserva su empaque original. Si presenta fugas o defectos de sellado de fábrica, incluso si ya fue utilizado, se aceptará con evidencia fotográfica del defecto.

### `estado_pedido` (10.9 s)

> **Cliente:** ¿Cuál es el estado de mi pedido ECO1004?

**Agente:** Tu pedido ECO1004 está retrasado. La entrega está programada para el 22 de abril, pero debido a una alta demanda y un cierre de vía en la ruta de distribución, no tenemos una fecha estimada de entrega concreta aún. Puedes seguir el estado de tu pedido en este enlace: [Rastreo del pedido](https://ecomarket.example/track/ECO1004).

### `devolucion_sin_datos` (1.9 s)

> **Cliente:** Quiero hacer una devolución

**Agente:** Por supuesto. Para poder ayudarte con la devolución necesito el número de pedido y el motivo por el cual deseas devolverlo. ¿Podrías proporcionarme estos detalles?

### `devolucion_elegible` (6.5 s)

> **Cliente:** Quiero devolver mi pedido ECO1012, me llegó un producto diferente al que pedí

**Agente:** ¡Listo! Tu devolución del pedido ECO1012 fue aprobada.  
  
- Código de devolución: RMA-ECO1012-385357  
- Guía (EcoEnvíos): ECOENV3853571012  
- Envía el producto a: Bodega EcoMarket - Calle 15 # 32-80, Yumbo, Valle del Cauca  
- Fecha límite de envío: 2026-05-02  
- Costo del envío de retorno: lo asume EcoMarket  
- Etiqueta: descárgala en PDF con el botón que aparece debajo de este mensaje.  
  
Reembolso: Al medio de pago original en 5 a 8 días hábiles tras la verificación en bodega.

### `devolucion_no_elegible_higiene` (6.5 s)

> **Cliente:** Quiero devolver el pedido ECO1006, ya abrí el empaque pero no me gustó

**Agente:** ECO1006 es un pedido de productos de higiene personal ecológico. Según nuestra política, no podemos aceptar devoluciones para este tipo de productos debido a su naturaleza sensible y por razones de sostenibilidad.  
  
El empaque del producto ya fue abierto. ¿Podrías confirmarme si el cliente abrió el empaque? Esto nos ayudará a seguir con la verificación de tu solicitud de devolución.

### `devolucion_fuera_de_plazo` (6.7 s)

> **Cliente:** Quiero devolver el pedido ECO1013, el kit vino con un defecto de fábrica

**Agente:** Lo siento, pero no puedo generar una etiqueta de devolución para tu pedido debido a que ya han pasado 46 días desde la entrega y el plazo máximo de devolución es de 30 días. Según nuestra política, los pedidos deben ser devueltos dentro de un mes desde la fecha de entrega.  
  
Si tienes alguna otra pregunta o necesitas ayuda con algo más, estaré encantado de asistirte.

### `devolucion_pide_info_multiturno` (8.3 s)

> **Cliente:** Quiero devolver la botella del pedido ECO1011, cambié de opinión
> **Cliente:** No, nunca la he usado, sigue nueva en su caja

**Agente:** ¡Listo! Tu devolución del pedido ECO1011 fue aprobada.  
  
- Código de devolución: RMA-ECO1011-76AB98  
- Guía (EcoEnvíos): ECOENV76AB981011  
- Envía el producto a: Bodega EcoMarket - Calle 15 # 32-80, Yumbo, Valle del Cauca  
- Fecha límite de envío: 2026-05-02  
- Costo del envío de retorno: lo asume Cliente  
- Etiqueta: descárgala en PDF con el botón que aparece debajo de este mensaje.  
  
Reembolso: Al medio de pago original en 5 a 8 días hábiles tras la verificación en bodega.

### `devolucion_alto_valor` (7.8 s)

> **Cliente:** Quiero devolver el pedido ECO1014, las botellas vinieron con defecto de fábrica

**Agente:** El valor del pedido ($534,000 COP) supera el límite de $500,000 COP para aprobación automática. Por eso, un agente humano revisará tu solicitud (ticket TCK-0001). Un agente humano te contactará en máximo 24 horas hábiles.

### `pedido_inexistente` (3.8 s)

> **Cliente:** Quiero devolver el pedido ECO9999 porque llegó dañado

**Agente:** Lo siento, pero no encontramos un pedido con ese número. Por favor, verifica que el número esté correcto y inténtalo nuevamente.

### `fuera_de_dominio` (1.4 s)

> **Cliente:** ¿Cuál es la capital de Francia?

**Agente:** Solo puedo ayudarte con temas de EcoMarket: pedidos, devoluciones, productos, envíos, pagos y tu cuenta. No encontré información sobre eso en nuestra base de conocimiento.

### `riesgo_seguridad` (0.0 s)

> **Cliente:** La botella del pedido ECO1011 se calentó y me quemé la mano

**Agente:** Lamento mucho lo ocurrido. Como tu mensaje menciona un posible riesgo para tu salud o seguridad, un agente humano revisará tu caso con prioridad (ticket TCK-0001). Un agente humano te contactará en máximo 24 horas hábiles. Si es una emergencia médica, por favor acude a un servicio de salud de inmediato.

