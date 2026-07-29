# Modelo de ÓRDENES del batch record · lo que falta para cerrar el legajo

> Levantado el **28-jul-2026** de MyBatch (el sistema de referencia), a partir de las capturas
> que pasó Sebastián de una orden de envasado y una de acondicionamiento REALES.
> Esto es la **especificación**, no una propuesta: así tiene que quedar.

## La regla que ordena todo

Sebastián: *"tanto fabricación, envasado como acondicionamiento, todas inician con una ORDEN;
esa orden se le entrega al operario, y después empieza el proceso"*.

O sea, en las tres fases hay **dos objetos distintos** y hoy los mezclamos:

1. **La ORDEN** — la autoriza Producción (y en acondicionamiento la aprueba Calidad), dice
   QUÉ y CUÁNTO hay que hacer, y es lo que se le entrega al operario. Una orden puede tener
   VARIOS lotes ("Adicionar lote").
2. **LAS INSTRUCCIONES / el legajo del lote** — es la ejecución de UN lote: el operario va
   registrando y firmando cada sección.

`ORDEN 1 ─── n LOTES ─── cada lote su legajo de secciones`

---

## Fabricación · OP-AAAA-NN

Ya existe en EOS como legajo. Falta que la ORDEN sea un objeto propio, con el mismo
encabezado que las otras dos.

## Envasado · OF-AAAA-NN

### Encabezado de la orden
| Campo | Ejemplo real |
|---|---|
| N° de orden | `OF-2026-77` |
| Producto | `PT-LIPVOL-10-001 LIP SERUM VOLUMINIZADOR CON PÉPTIDOS NF` |
| N° Lote Bulk | `262021` |
| Tamaño Bulk | `17000,0 Gr - 12658,95 mL` ← **las dos unidades** |
| Cantidad por Envasar | `12658,95 mL` |
| **Densidad Bulk** | `0,916 g/mL` ← sin esto no se convierte Gr → mL |
| Estado Actual | `Aprobado` |
| Elaborado por | Jefe de producción + usuario + fecha |
| Supervisado por | Jefe de producción + usuario + fecha |
| Observaciones | texto |

Acciones: **Adicionar lote** · Descargar (PDF) · Atrás.

### Legajo por lote · `OF-2026-77 · Lote N° 262021`
Encabezado del lote: producto + **envase** (`ENV-COLGLOSS-15-01 - Envase colapsable x 10.0mL`),
Programado por, **Unidades** (100), N° Lote Bulk, Fecha Inicio, Fecha Final, Estado Actual.

Secciones, en este orden:
1. **Precauciones** — texto del MBR.
2. **Despejes de Línea** — sub-fases `Inicial` (y final) · tabla `VERIFICACIÓN | CUMPLE | ACCIONES` · botón Registrar · imprimible PDF.
3. **Recepción de Material de Envase** — `MATERIAL | N° LOTE | CANT. REQUERIDA | CANT. RECIBIDA | RECIBIDO POR`.
4. **Envasado** — pasos numerados: `ACTIVIDAD | REALIZADO POR | VERIFICADO POR` (dos firmas distintas).
5. **Controles en Proceso** — `CONTROL | RESULTADO | OBSERVACIONES | REALIZADO POR` + botón *Control de volumen*. Los firma **Calidad**, no producción.
6. **Observaciones Generales del Proceso** — `DESCRIPCIÓN | REALIZADA POR | FECHA Y HORA`. Sirve para las pausas ("se pausa el envasado para dar cubrimiento a otro proceso").
7. **Registros Físicos del Proceso** — `CÓDIGO | DESCRIPCIÓN | DOCUMENTO` (los PDF firmados que se adjuntan).

## Acondicionamiento · OA-AAAA-NNN

### Encabezado de la orden
Igual al de envasado **más una firma**: `Aprobado por` = **Jefe de calidad**. Envasado sólo
tiene elaborado/supervisado; acondicionamiento suma la aprobación de Calidad.

### Lotes de Producto por Presentación
`PRESENTACIÓN | N° DE LOTE | UNID. | ÁREA/LÍNEA | UNID. EMPACADAS | FECHA | ESTADO`

### Materiales de Empaque
`N° LOTE ENVASADO | MATERIAL DE EMPAQUE | CANT. REQUERIDA | RECIBIDA | DEVUELTA | UTILIZADA | AVERIADA | DIFERENCIA`

Ojo: **devuelta, averiada y diferencia** son columnas propias. Es la conciliación de material
de empaque, y hoy EOS no la tiene.

### Aprobación de Artes / Codificación
`DESCRIPCIÓN | VER (PDF) | APROBADO POR | OBSERVACIONES` — lo aprueba Calidad antes de empacar.

### Legajo por lote
Mismas secciones que envasado, con dos diferencias:
- **Controles en Proceso** se agrupa por control: `Control N° 1`, `Control Inicial`… y la tabla
  es `ATRIBUTO | CUMPLE | OBSERVACIÓN | REALIZADO POR` (atributos, no medidas).
- El despeje registra además la **fecha y hora** de cada verificación.

---

## CONTRASTE CONTRA EOS · medido el 28-jul, no estimado

**6 de los 8 puntos ya estaban construidos.** Es M28 en su forma más pura: la lista de arriba
se armó mirando MyBatch, y al medirla contra el código real casi todo existía. Si se hubiera
construido "lo que falta" sin medir, se habrían reescrito cinco cosas que ya funcionan — en
datos regulados, que es donde reescribir es más caro.

| # | Punto | Estado real | Dónde vive |
|---|---|---|---|
| 1 | La ORDEN como objeto propio (1 orden → N lotes) | **FALTA** | hoy el legajo `ebr_ejecuciones` ES la unidad, con la llave sufijada `-OF`/`-OA` (M10) |
| 2 | Densidad del granel + cantidad en mL | **YA ESTÁ** | `densidad_g_ml` + puente OP→OF (`mL = real_g / densidad`) · test en el gate |
| 3 | Despeje con sub-fase e imprimible | **YA ESTÁ** | `ebr_despeje_items.etapa` + `verificado_por` / `verificado_at_utc` (mig 222) |
| 4 | Recepción de material de envase (requerida vs **recibida**) | **cerrado el 28-jul** | faltaban `recibida` / `recibido_por` · mig 391 |
| 5 | Dos firmas por paso (realizado / verificado) | **YA ESTÁ** | `operario_username` + `qc_username` + `qc_e_sign_id` + `requiere_qc` |
| 6 | Conciliación de empaque | **YA ESTÁ** | `ebr_envase_materiales`: `devuelta` / `utilizada` / `averiada` · la *diferencia* se DERIVA, no se guarda (M71) |
| 7 | Aprobación de artes / codificación | **YA ESTÁ** | `ebr_artes_codificacion` (mig 211) + gate que bloquea liberar sin arte aprobada |
| 8 | Observaciones del proceso con fecha y hora | **YA ESTÁ** | `ebr_observaciones` (`descripcion`, `registrado_por`, `registrado_at_utc`) |

---

## El mapa REAL de MyBatch (28-jul · leído del sistema, no de capturas)

Sebastián dio acceso al MyBatch de Espagiria. La ruta `/filling/` devuelve el 404 de Django con
**el mapa completo de URLs**, así que la arquitectura se leyó entera sin hacer un solo click
dentro de un registro regulado.

**Las tres fases tienen exactamente la misma forma.** Eso es lo importante: no son tres flujos
distintos, es un patrón repetido.

| Paso | Fabricación `productionorder` | Envasado `filling` | Acondicionamiento `packing` |
|---|---|---|---|
| Crear la orden | `add/` | `add/` · `add_bulk/` | `add/` |
| Aprobar la orden | `approval/<pk>` | `approved/<pk>` | `approved/<pk>` **+ `approved_quality/<pk>`** |
| **Agregar un lote** | — (1 OP = 1 lote) | `add_batch/<pk>` | `add_batch/<pk>` |
| Material **de la orden** | `add_mp/<pk>` | `add_material/<pk>` | `add_pack/<pk>` |
| **Recibir** material (por lote) | `register_reception_material/<pk>` | `material_received/<pk>` | `material_received/<pk>` |
| **Verificar** lo recibido | `verified_reception_material/<pk>` | `material_verified/<pk>` | `material_verified/<pk>` |
| Devolver material | — | `returned_material/<pk>` | `material_returned/<pk>` |
| Corregir la devolución | — | `correction_returned_material/<pk>` | `material_returned_correction/<pk>` |
| Poner en proceso | `in_process/<pk>` | `in_process_batch/<pk>` | `in_process/<pk>` |
| Unidades finales | — | `batch_unit_end/<pk>` | `batch_units_end/<pk>` |
| Liberar | `release_qa/` · `release_mfg/` | — | `batch_approved/` · `mass_release/` |
| PDF | `pdf/<pk>` | `pdf/<pk>` | `pdf/<pk>` |

### Lo que confirma (y ya no hace falta suponer)

1. **La ORDEN es un objeto propio en las tres fases**, con su `detail`, `update`, `pdf` y su
   aprobación. No es una etiqueta del legajo.
2. **`add_batch/<pk>` existe en envasado y acondicionamiento**: una orden agrupa N lotes.
   En fabricación NO existe — una OP es un lote. Por eso el botón "Adicionar lote" sólo
   aparece en las dos últimas fases.
3. **Acondicionamiento tiene DOS aprobaciones separadas**: `approved` (producción) y
   `approved_quality` (calidad). Coincide con la captura de la OA-2026-102, que muestra
   "Supervisado por: Jefe de producción" **y** "Aprobado por: Laura González, Jefe de calidad".
4. **El material se define en la ORDEN y se recibe en el LOTE** — que es exactamente el modelo
   que se implementó el 28-jul (`recibida` / `recibido_por` por lote). Lo que falta es el paso
   siguiente: **`material_verified`**, la segunda firma sobre lo recibido.

### Lo que apareció y no estaba en el radar

- `filling/density_bulk/<pk>` — la densidad se registra como una **acción sobre la orden**, no
  como un campo suelto.
- `filling/remainder/<pk>` — el **remanente** de granel: lo que sobró sin envasar.
- `productionorder/add_premix`, `list_premix`, `discount_premix` — **premezclas** como objeto
  propio, con descuento de inventario.
- `productionorder/adjust_mopo*` — ajustar la orden **con aprobación** (`adjust_mopo_approved`).
- `productionorder/register_weight` · `verified_weight` · `comment_weight` · `weight_pdf` —
  pesaje con **verificación**, comentario y rótulo imprimible.
- `productionorder/correction_lot_size` — corregir el tamaño de lote (con su variante líquidos).
- `productionorder/add_equipment_mfg` — equipos asignados a la orden.
- `packing/generate-barcode-pdf` · `ticket/print` — **tickets de código de barras**.
- `packing/mass_release` — liberación masiva de lotes de acondicionamiento.
- Módulos **compartidos** por las tres fases: `lineclearance` (despejes), `precautions`,
  `instructions`, `controlprocess`. En EOS esas piezas están adentro del EBR; en MyBatch son
  módulos propios que las tres fases consumen.
- `operationsrecord`, `changecontrol`, `assurance`, `audit`, `document`.

⚠ **Este mapa dice QUÉ existe, no que todo haga falta.** Antes de construir cualquiera de
estos, se mide contra EOS (M28): la mitad ya está.

### Lo único grande que falta, y por qué no se construyó solo

**La ORDEN como objeto propio.** Hoy EOS modela el legajo por LOTE; MyBatch modela una orden
que agrupa N lotes. Los dos representan lo mismo, pero la orden agrega tres cosas que el legajo
por lote no tiene:

1. Un encabezado que se **aprueba una vez** para todos los lotes (en acondicionamiento, la firma
   del jefe de calidad va en la ORDEN, no en cada lote).
2. El botón **"Adicionar lote"**: hoy cada legajo nace suelto y se ata por el sufijo de la llave.
3. Un **número de orden** que es lo que se le entrega impreso al operario.

**No se construyó todavía a propósito.** Cambia la unidad de trabajo de un registro regulado
(INVIMA / Part 11): los legajos existentes tendrían que colgarse de una orden retroactiva, y eso
es una decisión de Sebastián, no una inferencia mía. Cuando se haga, va de a una fase y con la
migración probada contra PG con datos sembrados, como el resto.
