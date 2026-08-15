# MyBatch ↔ EOS · mapa de clonación para la certificación

> Relevado el **15-ago-2026** entrando a MyBatch de Espagiria
> (`esparigia-mybatch-...run.app`) con el usuario de Sebastián, perfil **Planeador**.
> Sebastián: *"necesitamos clonarlo perfecto ... ésta es la que regula INVIMA, y
> ellos ya están habilitados; la idea es reemplazarlos por EOS cuando pidamos la
> certificación"*.
>
> Este documento dice **qué tiene MyBatch, sección por sección**, y **qué tiene EOS
> hoy**, verificado contra el código y contra un recorrido E2E por los endpoints
> reales, no contra la memoria.

---

## 0 · Cómo se verificó (para que se pueda repetir)

| Qué | Cómo |
|---|---|
| Las pantallas de MyBatch | Se abrieron una por una y se leyó el texto completo de cada instructivo |
| Qué tiene EOS | `grep` del esquema + `url_map` real + los endpoints abiertos uno por uno |
| Que EOS lo recorre entero | `tests/test_ebr_e2e_demo.py` (fabricación) y `tests/test_ebr_e2e_envasado_acond.py` (envasado y acondicionamiento), los tres **en el gate** |

Las tres fases pasan hoy. Un rojo en cualquiera bloquea el push.

---

## 1 · El menú de MyBatch (perfil Planeador)

```
INICIO            tablero con 7 contadores
MANUFACTURA       /productionorder/list/        Órdenes de producción
                  /filling/list/                Envasado
                  /packing/list/                Acondicionamiento
                  /productionorder/list_premix/ Premezclas
                  /productionorder/program/     Programa de producción (calendario)
ASEGURAMIENTO     /assurance/batch_list_master/ Maestro de lotes
SOPORTE TÉCNICO   (sin opciones para este perfil)
```

**Contadores del inicio:** Fabricación pendientes / en proceso · Envasado pendientes /
lotes en proceso · Acondicionamiento pendientes / programados · Lotes en cuarentena.

**Estados oficiales** (leyenda del calendario, y es la máquina de estados que mira INVIMA):
`Pendiente · Programado · En Proceso · Aprobado · Cuarentena · Liberado · No Conforme/Rechazado/Cancelado`.

---

## 2 · FABRICACIÓN · "Instrucciones de Manufactura" (OP)

**Cabecera:** N° de orden · producto · N° de lote bulk · cantidad ordenada (Gr) ·
**área o línea** · fecha inicio · fecha final · estado actual.
**Acciones:** Timeline Batch Record · Orden · Descargar orden · Actualizar.

| # | Sección MyBatch | Contenido | EOS |
|---|---|---|---|
| 1 | Precauciones | texto + *agregar equipo* | ✅ `ebr_precauciones` |
| 2 | Despeje de línea · **Dispensación** | 13 verificaciones con Cumple | ✅ `ebr_despeje_linea` + `ebr_despeje_items` |
| 3 | Dispensado de materias primas | MP · **%** · **N° lote** · cant. a pesar · cant. pesada · **Ajustes** | ✅ `ebr_pesajes` (+ `ebr_ajustes_mp`) |
| 4 | Despeje de línea · **Fabricación** | las mismas 13, en el otro momento | ⚠️ EOS registra el despeje por área; **no distingue las dos etapas** |
| 5 | Fabricación/Mezcla | pasos con **Realizado por** + **Verificado por** + *Resultado* | ✅ `ebr_pasos_ejecutados` (doble firma) |
| 6 | Controles en proceso | Olor · Color · Densidad 25°C · pH 25°C · Apariencia | ✅ IPC estándar + specs del MBR |
| 7 | Observaciones generales | texto con autor y hora | ✅ `ebr_observaciones` |
| 8 | Registros físicos | adjuntos | ✅ `ebr_registros_fisicos` |

**Lo que EOS hace y MyBatch no:** descuenta la materia prima del kardex por FEFO al
iniciar, con lote y vencimiento reales; bloquea si el material está vencido o en
cuarentena; y calcula el rendimiento contra la fórmula.

---

## 3 · ENVASADO · "Orden de Envasado" (OF) + "Instrucciones de Envasado"

### 3.1 La orden

| Campo MyBatch | EOS |
|---|---|
| N° lote bulk · Tamaño bulk (Gr **y** mL) | ✅ |
| **Densidad bulk (g/mL)** | ✅ existe (mig 212, "puente OP→OF") |
| **Cantidad por envasar** = saldo del granel | ⚠️ se calcula el mL envasable; **el saldo no se muestra como tal** |
| Estado · elaborado por · supervisado por · observaciones | ✅ |
| **Lotes de producto por presentación**: presentación · lote · unidades · **área/línea** · cantidad (mL) · **unid. final** · **% rendimiento** · estado | ✅ presentaciones con unidades y cliente · ⚠️ **falta % de rendimiento por presentación** |
| **Materiales de envase**: requerida · devuelta · utilizada · **averiada** · **diferencia** | ✅ las seis (mig 433 · la diferencia se deriva, no se guarda) |

### 3.2 El instructivo

| # | Sección MyBatch | EOS |
|---|---|---|
| 1 | Precauciones | ✅ |
| 2 | Despejes de línea (12 verificaciones) | ✅ (mismo orden · mig 381) |
| 3 | **Recepción de material de envase**: material · N° lote · cant. requerida · cant. recibida · **recibido por** | ✅ `material-envase` + `/verificar` |
| 4 | Envasado · 5 pasos con realizado/verificado | ✅ |
| 5 | Controles en proceso · **control de volumen** ("Control de llenado 30mL → 30,0mL CUMPLE") | ✅ control de llenado y de peso propios de la fase (15-ago) |
| 6 | Observaciones generales | ✅ |
| 7 | Registros físicos | ✅ |

**Lo que EOS hace y MyBatch no:** el envase sale del kardex de verdad (con su cuarentena
y su serigrafiado), y las unidades se reparten **por cliente** — desde el 15-ago eso se
ve en la LISTA de órdenes (cliente, unidades y la foto del frasco que le corresponde),
no sólo abriendo el legajo.

---

## 4 · ACONDICIONAMIENTO · "Orden" (OA) + "Instructivo"

### 4.1 La orden

| Campo MyBatch | EOS |
|---|---|
| Elaborado por · estado · supervisado por · observaciones | ✅ |
| Lotes de producto por presentación · **unid. empacadas** · fecha · estado | ✅ |
| Acción **"Aprobar Etiqueta"** por presentación | ✅ gate de artes (`ebr_artes_codificacion`) |
| **Materiales de empaque**: requerida · recibida · devuelta · utilizada · **averiada** · diferencia | ✅ las seis (mig 433) |
| Aprobación de artes / codificación | ✅ |

### 4.2 El instructivo

**Cabecera:** unidades a procesar · lote bulk · fecha inicio/final · estado ·
**cant. procesada** · **averías** · **cant. disponible** · **rendimiento %** ·
**justificación del rendimiento** · registrado por (operario) · supervisado por
(jefe de producción) · **aprobado por (jefe de calidad)**.

| # | Sección MyBatch | EOS |
|---|---|---|
| 1 | Precauciones | ✅ |
| 2 | Despejes de línea (13, **con fecha por ítem**) | ✅ |
| 3 | **Recepción de material de empaque** (varias tandas: 367 + 75 + 100) | ✅ acepta varias filas |
| 4 | Acondicionamiento · 4 pasos con realizado/verificado | ✅ |
| 5 | **Controles de atributos** · 14 ítems de Calidad (integridad de la caja, adherencia de la etiqueta, sellado, legibilidad…) | ✅ los 14, y sólo en esta fase (15-ago) |
| 6 | Observaciones generales | ✅ |
| 7 | Registros físicos | ✅ |

**Ejemplo real leído:** rendimiento **127,25 %** (367 pedidas, 467 procesadas) con la
explicación en observaciones: *"se suman 100 unidades a la orden inicial por 367 de un
cliente que canceló"*. MyBatch pide justificación cuando el rendimiento se sale de
rango, y ahí queda el rastro.

---

## 5 · Lo que falta para el clon (lista corta y verificada)

| # | Hueco | Dónde | Estado |
|---|---|---|---|
| 1 | `cant_averiada` + diferencia en la conciliación | envasado y acondicionamiento | ✅ **hecho** 15-ago (mig 433 · `tests/test_conciliacion_averiada.py`) |
| 3 | Los 14 controles de atributos | acondicionamiento | ✅ **hecho** 15-ago · y de paso envasado pasó a pedir control de llenado en vez de densidad y pH (`tests/test_ipc_estandar_por_fase.py`) |
| 2 | Las dos etapas del despeje (dispensación / fabricación) | fabricación | pendiente · MyBatch registra dos momentos distintos; EOS los junta |
| 4 | Rendimiento por presentación + justificación | envasado y acondicionamiento | pendiente · el % existe a nivel lote; falta por presentación y el motivo cuando se sale de rango |
| 5 | Saldo del granel ("cantidad por envasar") visible | envasado | pendiente · hoy hay que calcularlo de cabeza |

Ninguno de los cinco rompe nada hoy: son **campos y datos que se agregan**, no cambios
en lo que ya está firmado (aditivo · M117).

---

## 6 · Lo que NO se copia (y por qué)

- **El calendario de MyBatch** es una grilla de estados. EOS tiene plan autónomo con
  ventas de Shopify, cadencias y buffer de 20 días: es superior y ya está en uso.
- **Las órdenes se numeran distinto** (MyBatch OP/OF/OA-año-N; EOS ya tiene su propia
  serie). No se toca: renumerar registros firmados es falsificar historia (M105).
- **MyBatch no toca inventario.** EOS descuenta materia prima y envases del kardex, con
  FEFO, cuarentena y vencimiento. Eso es lo que Sebastián llama "EOS es superior: jala
  todo", y no tiene equivalente que copiar.

---

## 8 · Aseguramiento: maestro, cuarentena y alta de granel

**Maestro de lotes** (`/assurance/batch_list_master/`) · 123 registros:
`N° de lote · producto · presentación · estado · unid. teóricas · unid. liberadas`.
La fila es por **(lote, presentación)**, no por lote: el mismo 262151 aparece dos
veces, una por cada tamaño.

**Lotes en cuarentena** (`/assurance/batch_quarantine_list/`) · mismas columnas
filtradas por estado. Ahí se ve algo que conviene copiar: **la liberación es
PARCIAL** (692 teóricas / 136 liberadas · 2666 / 2484). Un lote puede quedar
parcialmente liberado y el resto retenido.

**Alta de granel** (`/assurance/add_batch_bulk/`): descripción del granel (elegido
de los 30 productos, con código `PT-…`), presentación, N° de lote, N° de unidades,
observaciones.

**Acondicionamiento por TANDAS** — en la orden OA-2026-85 la misma presentación
aparece **cuatro veces** para el mismo lote (367, 75, 100 y 100 unidades), cada
una con su propio estado (`Programado` / `Aprobado ✓`) y su acción **Aprobar
Etiqueta**. Es decir: una orden agrupa varias tandas del mismo lote, y cada tanda
tiene su ciclo y su etiqueta aprobada por separado.

**Códigos de producto:** MyBatch identifica el producto terminado con un código
(`PT-TRIACTIVE-30-001`) y EOS lo hace por nombre. Para la certificación conviene
que el legajo de EOS **muestre también ese código**, porque es el que aparece en
los registros ya firmados de MyBatch.

---

## 7 · Vistas por rol

Sebastián entra como **Planeador**. Las vistas de director técnico, jefe de producción,
Calidad y operarios **no se pudieron ver** (harían falta sus credenciales). Lo que sí
quedó registrado, porque el propio documento lo firma, es **quién hace qué**:

| Acto | Quién lo firma en MyBatch |
|---|---|
| Programar la orden | Jefe de producción |
| Dispensar, ejecutar pasos, recibir material | Operario de producción |
| Verificar cada paso | Jefe de producción |
| Controles en proceso y de atributos | Jefe de calidad |
| Aprobar el acondicionamiento | Jefe de calidad |

EOS ya tiene esos roles y la doble firma; falta contrastar la vista de cada uno cuando
se pueda entrar con sus usuarios.
