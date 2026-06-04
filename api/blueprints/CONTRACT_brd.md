# CONTRACT · `brd.py` (Batch Record Digital)

> **Para agentes IA · LEER ANTES de modificar este blueprint.**
> Este blueprint contiene los datos regulatorios más críticos del sistema
> (records de fabricación INVIMA / GMP). Cualquier cambio que rompa
> inmutabilidad o trazabilidad es BLOQUEANTE.

Última revisión: 2026-05-12

---

## Contexto

`brd.py` reemplaza progresivamente a **MYBATCH** (sistema externo de batch
records que HHA usaba). Implementa Part 11 §11.10(e), §11.50, §11.70,
§11.100(b), §11.200 + buenas prácticas GMP.

Capas:
1. **MBR** (Master Batch Record) · procedimiento aprobado por QA.
2. **EBR** (Executed Batch Record) · ejecución de UN lote real.
3. **IPCs** · in-process controls con specs y bloqueo OOS.
4. **Cleaning log** · limpieza de equipos con validación QC visual.
5. **Pesajes** · reconciliación granular MP teórico vs real.
6. **PDF maestro** · legajo auditable descargable.

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `mbr_templates` | INSERT/UPDATE | crear draft, editar, transición de estado |
| `mbr_pasos` | INSERT/UPDATE/DELETE | gestión pasos del MBR (solo en draft) |
| `ipc_specs` | INSERT/DELETE | gestión specs IPC (solo en draft) |
| `ebr_ejecuciones` | INSERT/UPDATE | iniciar EBR, completar, liberar/rechazar |
| `ebr_pasos_ejecutados` | INSERT/UPDATE | clonar al iniciar EBR, ejecutar paso |
| `ipc_resultados` | INSERT | reportar medición IPC |
| `ebr_pesajes` | INSERT | reportar pesaje granular MP |
| `equipo_limpieza_log` | INSERT/UPDATE | ciclo limpieza operario+QC |
| `e_signatures` | (LEE solamente) | valida signature_id de aprobaciones |
| `audit_log` | INSERT | cada operación crítica |

## Tablas que LEE

- `mbr_templates`, `mbr_pasos`, `ipc_specs`, `ebr_*`, `ipc_resultados`,
  `ebr_pesajes`, `equipo_limpieza_log`, `e_signatures`,
  `usuarios_identidad` (para identity snapshot en firmas),
  `formula_items` (para cálculo de teóricos en reconciliación).

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · MBR aprobado es INMUTABLE
Migración 109 trigger `trg_mbr_aprobado_no_edit` bloquea UPDATE de
`titulo`, `descripcion`, `lote_size_g`, `formula_version_id` cuando
`estado='aprobado'`. `mbr_pasos` también inmutable post-aprobación
(triggers `trg_mbr_pasos_no_*_aprobado`). Si necesitás cambiar algo
APROBADO, el flujo es: `obsoletar` la versión actual + `crear` nueva
con `version+1`.

### INV-2 · IPC specs siguen el estado del MBR
Migración 112 trigger `trg_ipcspec_no_*_aprobado`. Igual razón que INV-1.

### INV-3 · EBR liberado/rechazado es INMUTABLE
Migración 111 trigger `trg_ebr_liberado_no_edit` bloquea UPDATE de
`cantidad_real_g`, `yield_pct`, `liberado_signature_id`, `notas`,
`estado` cuando `estado IN ('liberado','rechazado')`. Pasos, IPCs y
pesajes asociados también inmutables (triggers correspondientes).

### INV-4 · Aprobación/liberación REQUIERE e-signature válida
- `POST /api/brd/mbr/<id>/aprobar` valida signature_id contra
  `e_signatures WHERE meaning='aprueba' AND record_table='mbr_templates'
  AND record_id=mbr_id AND signer_username=user`.
- `POST /api/brd/ebr/<id>/liberar` análogo con `meaning='libera'`.
- `POST /api/brd/ebr/<id>/rechazar` análogo con `meaning='rechaza'`.
- Sin firma válida → 400 (no 401 — el user está autenticado pero no firmó).

### INV-5 · Pasos críticos del EBR REQUIEREN e-sign
Si `mbr_pasos.requiere_e_sign=1`, el endpoint
`POST /api/brd/ebr/<id>/pasos/<orden>/completar` exige `signature_id`
con `meaning='ejecuta'` y `record_table='ebr_pasos_ejecutados'`. Si
`requiere_qc=1`, también `qc_signature_id` con `meaning='supervisa'`.

### INV-6 · IPCs obligatorios bloquean completar EBR
`POST /api/brd/ebr/<id>/completar` rechaza con 409 si:
- Hay `ipc_specs WHERE obligatorio=1` sin resultado en `ipc_resultados`.
- Hay `ipc_resultados WHERE conforme=0 AND spec.obligatorio=1`.

GMP: out-of-spec debe abrir desviación antes de continuar. Hoy bloqueamos
completar; el siguiente release puede agregar workflow desviación-link.

### INV-7 · Cantidad teórica se calcula SERVER-SIDE
`POST /api/brd/ebr/<id>/pesajes` NO acepta `cantidad_teorica_g` del
cliente. Se calcula como `formula_items.porcentaje × cantidad_objetivo_g`.
Esto evita que el operario manipule el teórico para ocultar deltas
fuera de spec.

### INV-8 · Cleaning log validado por QC es INMUTABLE
Migración 113 trigger `trg_limpieza_no_edit_qc`: una vez `qc_e_sign_id`
está set, no se puede cambiar `visual_ok`, `qc_e_sign_id`,
`completado_at_utc`, ni `equipo_codigo`. Errores se documentan abriendo
nuevo log.

### INV-9 · audit_log captura todas las transiciones de estado
Cada cambio de estado en MBR/EBR/cleaning genera audit. Las descargas
de PDF EBR también (acción `DOWNLOAD_EBR_PDF`).

### INV-10 · PDF EBR contiene SHA-256 estable del CONTENIDO
El hash del footer NO es el hash del PDF (eso cambia con timestamp gen).
Es hash de campos estables del EBR (id, lote, cantidad, signature_id,
counts). Permite verificar que el PDF se generó desde un EBR específico
no alterado.

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `brd.py`... |
|---|---|---|
| `programacion.py` (futuro) | `ebr_ejecuciones.produccion_id` | ...producciones planificadas pierden ref a su EBR |
| `inventario.py` (futuro) | `ebr_pesajes.lote_mp` | ...trazabilidad lote MP → producto terminado se rompe |
| `aseguramiento.py` (futuro) | desviaciones podrían linkear ipc_resultados | ...desviaciones huérfanas |
| Calidad UI | `/api/brd/ebr?estado=en_revision_qc` | ...QC no ve los pendientes a liberar |
| INVIMA auditor (manual) | descarga PDF EBR | ...evidencia regulatoria no se entrega |

---

## Endpoints que expone

### MBR
- `GET    /api/brd/mbr` · listar (filtros producto, estado)
- `GET    /api/brd/mbr/<id>` · detalle con pasos
- `POST   /api/brd/mbr` · crear draft
- `PATCH  /api/brd/mbr/<id>` · editar header (solo draft)
- `POST   /api/brd/mbr/<id>/pasos` · agregar paso
- `PATCH  /api/brd/mbr/<id>/pasos/<paso_id>` · editar paso
- `DELETE /api/brd/mbr/<id>/pasos/<paso_id>` · borrar paso
- `POST   /api/brd/mbr/<id>/submit` · draft → en_revision
- `POST   /api/brd/mbr/<id>/aprobar` · requiere signature_id
- `POST   /api/brd/mbr/<id>/obsoletar` · aprobado → obsoleto + motivo

### IPC specs (parte del MBR)
- `GET    /api/brd/mbr/<id>/ipc-specs`
- `POST   /api/brd/mbr/<id>/ipc-specs` · solo draft
- `DELETE /api/brd/mbr/<id>/ipc-specs/<spec_id>` · solo draft

### EBR
- `GET    /api/brd/ebr` · listar (filtros estado, lote)
- `GET    /api/brd/ebr/<id>` · detalle con pasos
- `POST   /api/brd/ebr` · iniciar (clona **solo los pasos de la fase** del MBR aprobado · Batch B). `lote` es UNIQUE: para el mismo lote físico en varias fases, usar sufijo (·-OF/-OA) y `asignar-lote-fisico` para el lote real.
- `POST   /api/brd/ebr/<id>/pasos/<orden>/iniciar`
- `POST   /api/brd/ebr/<id>/pasos/<orden>/completar` · valida e-sign
- `POST   /api/brd/ebr/<id>/completar` · valida IPCs (bloquea conforme=0 **o NULL** obligatorio) + calcula yield
- `POST   /api/brd/ebr/<id>/asignar-lote-fisico` · reemplaza el lote provisional `PP<id>` por el lote físico real (propaga a `movimientos` Entrada). Solo antes de liberar. (audit 3-jun)
- `POST   /api/brd/ebr/<id>/liberar` · QC firma `meaning='libera'`. Gates: desviación abierta, **IPC OOS sin desviación resuelta (fail-closed, por ebr_id)**, y en `EBR_MODE=strict` exige pesajes verificados + conciliación.
- `POST   /api/brd/ebr/<id>/rechazar` · QC firma `meaning='rechaza'` + motivo

### IPC resultados (parte del EBR)
- `GET  /api/brd/ebr/<id>/ipc-resultados`
- `POST /api/brd/ebr/<id>/ipc-resultados` · operario reporta medición · OOS abre desviación auto

### Estaciones MyBatch en el runner (reemplazo completo)
- `GET/POST /api/brd/ebr/<id>/despeje` · despeje de línea (checklist CUMPLE · MyBatch ②) · mig 215
- `GET/POST /api/brd/ebr/<id>/precauciones` · precauciones + equipos (MyBatch ①) · mig 216
- `GET/POST /api/brd/ebr/<id>/registros-fisicos` + `GET .../<rid>/pdf` · adjuntar PDF/referencia (MyBatch ⑦) · mig 217
- `GET/POST /api/brd/ebr/<id>/conciliacion-material` · conciliación envase/empaque (mig 210)
- `GET/POST /api/brd/ebr/<id>/artes` + `/artes/<id>/aprobar` · artes/codificación (mig 211)
- `GET/POST /api/brd/ebr/<id>/observaciones` · bitácora (mig 213)
- `POST /api/brd/ebr/<id>/pesajes/<pid>/verificar` · 2ª firma de pesaje (mig 208)

### Pesajes (reconciliación granular)
- `GET  /api/brd/ebr/<id>/pesajes` · listado
- `POST /api/brd/ebr/<id>/pesajes` · operario reporta pesaje
- `GET  /api/brd/ebr/<id>/reconciliacion` · ok / outliers / no_pesados

### Cleaning log
- `GET  /api/brd/cleaning?equipo=X` · listado
- `GET  /api/brd/cleaning/equipo/<X>/ultima` · última + apto_para_uso
- `POST /api/brd/cleaning` · operario inicia limpieza
- `POST /api/brd/cleaning/<id>/completar` · operario marca fin
- `POST /api/brd/cleaning/<id>/validar` · QC firma visual_ok

### PDF maestro
- `GET /api/brd/ebr/<id>/pdf` · descarga legajo completo (audit_log captura)

---

## Permisos

| Acción | Roles permitidos |
|---|---|
| Crear/editar MBR draft | cualquier user logueado |
| Submit MBR a revisión | creador o ADMIN_USERS |
| Aprobar/obsoletar MBR | ADMIN_USERS o CALIDAD_USERS |
| Iniciar EBR | cualquier user logueado |
| Ejecutar pasos EBR | cualquier user logueado (paso requiere e-sign del propio user) |
| Liberar/rechazar EBR | ADMIN_USERS o CALIDAD_USERS |
| QC validar cleaning | ADMIN_USERS o CALIDAD_USERS |

---

## Cambios recientes

### 2026-05-12 · Fase 1 BRD completa (F1-F8 sin C2)
- Migraciones 109-114.
- Blueprint nuevo `brd.py` (~1.700 LoC).
- 7 golden paths nuevos (GP-55 a GP-60 + reconciliación).
- F2 lock post-aprobación con triggers en producciones/OC postergado
  (necesita análisis caso por caso de workflows existentes).

### Pendiente para próxima iteración
- UI dashboard `/brd` (listados read-only mínimos hechos en otra commit).
- Desviación auto-link cuando IPC sale fuera spec.
- Importar más fórmulas reales como MBR draft (hoy solo Blush Balm).
- Hookear `produccion_programada.iniciar` para crear EBR auto.
- Pack CSV (URS / IQ / OQ / PQ) cuando se vaya a auditoría INVIMA.

### 2026-05-30 · Reemplazo MyBatch fase 1 · EBR automático al aceptar producción
- Helper nuevo `crear_ebr_desde_mbr(cur, *, producto_nombre, lote, produccion_id,
  cantidad_objetivo_g, usuario, notas)`: crea (o reusa, idempotente por
  produccion_id) un EBR desde el MBR APROBADO más reciente del producto, clona
  sus pasos. NO commitea ni audita (lo hace el caller). Devuelve
  {ok, id, numero_op, pasos} o {ok:False, error:'NO_MBR_APROBADO'|'LOTE_DUPLICADO'}.
- `programacion.planta_aceptar_produccion` lo invoca según `config.EBR_MODE`:
  - 'off' (default): no crea EBR (sin cambios).
  - 'warn': crea EBR si hay MBR aprobado; si falta, deja aceptar con aviso en log.
  - 'strict': BLOQUEA aceptar (409 SIN_MBR_APROBADO) si el producto no tiene MBR
    aprobado · BPM. El chequeo es ANTES de mutar.
  - lote del EBR provisional = 'PP<produccion_id>'; el lote físico real se
    enlazará al completar (refinamiento fase futura). Modelo: 1 EBR por
    produccion_programada.
- Activar 'strict' SOLO cuando todos los MBR estén cargados/aprobados (sino frena
  planta). Cubierto por golden GP-62 test_golden_ebr_auto_al_aceptar_produccion.

### 2026-05-30 · Fase 2 · IPC fuera de spec → desviación/CAPA automática (mig 203)
- `reportar_ipc_resultado`: si conforme=0, abre desviación automática vía
  `aseguramiento.crear_desviacion_auto` (tipo proceso, lotes_afectados=lote EBR,
  descripción con parámetro+valor+rango) y enlaza en `ipc_resultados.desviacion_id`
  (mig 203). Devuelve {desviacion:{codigo,id}}. Deploy-safe.
- `liberar_ebr`: GATE nuevo · 409 DESVIACION_ABIERTA si existe una desviación con
  el lote del EBR en lotes_afectados y estado NOT IN ('cerrada','anulada'). El
  lote no se libera hasta resolver la desviación (clasificar→investigar→CAPA→cerrar).
- Golden GP-64. La desviación sigue su workflow normal en /aseguramiento.
