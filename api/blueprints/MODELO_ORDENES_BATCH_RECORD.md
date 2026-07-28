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

## Qué hay que contrastar contra EOS antes de construir

Esto es la foto de MyBatch. **Antes de tocar nada** hay que medir, contra el código real,
cuánto de esto ya existe (M28: la mitad de los "faltantes" suelen estar hechos):

- [ ] ¿La ORDEN existe como objeto propio en las tres fases, o hoy sólo hay legajo?
- [ ] ¿Guardamos `densidad` y `cantidad por envasar en mL`? (M105 ya lo marcó como faltante)
- [ ] ¿El despeje tiene sub-fase inicial/final y su imprimible?
- [ ] ¿Recepción de material de envase por lote, con requerida vs recibida?
- [ ] ¿Los pasos tienen DOS firmas (realizado / verificado)?
- [ ] ¿Existe la conciliación de empaque (devuelta / utilizada / averiada / diferencia)?
- [ ] ¿Existe la aprobación de artes por Calidad?
- [ ] ¿Las observaciones del proceso admiten registrar una pausa con fecha y hora?

⚠ Nada de esto se construye a ciegas: cada punto se verifica contra el código y se hace **de a
uno**, con su test. Es batch record — dato regulado INVIMA (ver `CONTRACT_brd.md`).
