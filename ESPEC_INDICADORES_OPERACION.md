# Especificación — Indicadores de operación en EOS

**Solicitado por:** Gerencia (Sebastián Vargas)
**Fecha:** 17-ago-2026
**Para:** implementación en EOS

---

## Por qué

Hoy Gerencia se entera del estado de la operación preguntando. No hay reporte.
Y el dato que sí existe en EOS no es confiable: Control de Calidad reportó el
14-ago que el módulo de cuarentena marca 62 insumos pendientes y que ese número
no corresponde con la planta.

El objetivo no es agregar pantallas. Es que **EOS sea la única fuente y que diga
la verdad**, para que el reporte semanal salga de la plataforma y nadie tenga que
redactarlo.

Regla que se quiere sostener con esto: **si no está en EOS, no pasó.**

---

## PASO 0 — Antes de construir

Revisar qué de esto ya existe en el modelo actual. No duplicar. Reportar:

- Qué indicadores se pueden calcular hoy con los datos que ya se capturan.
- Cuáles necesitan un campo nuevo.
- Cuáles necesitan un cambio de proceso y no de software.

---

## BLOQUE 1 — Despachos

| # | Indicador | Definición exacta |
|---|---|---|
| 1 | Pedidos recibidos | Pedidos creados en el período |
| 2 | Pedidos despachados | Pedidos con fecha de despacho en el período |
| 3 | Pedidos pendientes de despacho | Sin fecha de despacho. **Mostrar la antigüedad en días del más viejo** |
| 4 | Cumplimiento de promesa | % de pedidos entregados dentro de 5–7 días hábiles desde la creación |
| 5 | Pedidos con guía generada | Con número de guía registrado |
| 6 | **Pedidos con entrega confirmada** | Con fecha de entrega confirmada registrada |
| 7 | **Despachados sin confirmación** | Con guía, sin confirmación de entrega. **Mostrar días transcurridos** |

**El 6 y el 7 son los importantes.** Hoy cerramos el ciclo cuando el pedido sale,
no cuando llega. Sin ellos no sabemos cuántos pedidos llegaron de verdad.

---

## BLOQUE 2 — Incidencias con transportadora

| # | Indicador | Definición |
|---|---|---|
| 8 | Incidencias abiertas / cerradas | Con causa clasificada |
| 9 | Devoluciones | Con motivo clasificado |

Causas sugeridas como lista cerrada, no texto libre: dirección errada, cliente
ausente, daño en tránsito, demora de transportadora, rechazo del cliente, otro.

Texto libre solo en "otro", y ese campo se revisa mensualmente para ver si hay
que crear una causa nueva.

---

## BLOQUE 3 — Inventario

| # | Indicador | Definición |
|---|---|---|
| 10 | Stock disponible por SKU | **Usar Available, nunca On hand.** Lo Committed ya está vendido |
| 11 | SKUs en cero o bajo mínimo | Requiere mínimo definido por SKU |
| 12 | **Diferencia EOS vs conteo físico** | Por SKU, contra el último conteo registrado. Mostrar fecha del conteo |

**El 12 es el que mide si EOS dice la verdad.** Sin él, todos los demás
indicadores son una opinión.

---

## CAMBIO DE PROCESO — punto de entrada de materiales

Este no es un reporte, es una corrección y es la causa del problema del bloque 3.

Hoy un material entra a EOS cuando se genera la guía de transporte o cuando se
paga. Resultado documentado el 14-ago: el Propylheptyl Caprilate figura ingresado
en cuarentena y nunca llegó físicamente a la planta.

**Regla nueva:** un material entra al inventario únicamente cuando alguien
confirma la recepción física contra la orden de compra.

Implicación en EOS:
- Separar el estado **"en tránsito"** (guía generada, pago hecho) del estado
  **"en cuarentena"** (recibido físicamente).
- Solo "en cuarentena" cuenta como inventario.
- El paso de "en tránsito" a "en cuarentena" requiere usuario, fecha y hora.
- Alerta de materiales en tránsito con más de X días sin recepción.

---

## REPORTE SEMANAL

Generado por la plataforma, no redactado por nadie.

- Los 12 indicadores, comparando contra la semana anterior.
- Se envía por correo automáticamente los lunes a las 7:00 a. m. (COT).
- Destinatarios configurables. Inicialmente: Gerencia y Asistente de Gerencia
  de ÁNIMUS.
- El mismo reporte debe poder consultarse en pantalla en cualquier momento.

---

## CRITERIOS DE ACEPTACIÓN

1. Los 12 indicadores se calculan sobre datos reales, sin cifras cableadas.
2. Un pedido no puede marcarse como entregado sin fecha de confirmación.
3. Un material no puede sumar al inventario sin registro de recepción física.
4. El reporte semanal llega solo, sin que nadie lo ejecute.
5. El indicador 12 muestra la fecha del último conteo físico. Si no hay conteo
   registrado, lo dice explícitamente en lugar de mostrar cero.

---

## LO QUE NO SE PIDE

- No hacer gráficas bonitas todavía. Primero que los números existan y sean ciertos.
- No migrar nada. Trabajar sobre el modelo actual.
- No construir indicadores comerciales en esta primera entrega. Van después.
