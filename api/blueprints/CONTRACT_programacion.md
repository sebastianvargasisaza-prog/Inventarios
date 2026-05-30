# CONTRACT · `programacion.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**

Última revisión: 2026-05-23 (Fix #3 · Abastecimiento lee Calendar completo)

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `produccion_programada` | INSERT | Sync Calendar, manual nueva |
| `produccion_programada` | UPDATE | Iniciar, cambiar área, descontar inventario |
| `produccion_programada` | DELETE | Limpiar duplicados, espejo Calendar, admin borra |
| `solicitudes_compra` | INSERT | Bulk solicitar faltantes (agrupado por proveedor) |
| `solicitudes_compra_items` | INSERT | Faltantes detectados |
| `mp_lead_time_config` | INSERT/UPDATE | Configuración manual o sync desde compras |
| `produccion_checklist` | INSERT/UPDATE/DELETE | Pre-producción items |
| `movimientos` | INSERT | Salida MP al iniciar/completar (con `produccion_id`); Entrada compensatoria al revertir |
| `_sync_log` | INSERT | Cada corrida del sync Calendar |
| `audit_log` | INSERT | Operaciones destructivas + crear producción (`CREAR_PRODUCCION_PROGRAMADA`) |

## Tablas que LEE

- TODAS las del módulo + `formula_headers`, `formula_items`,
  `sku_producto_map`, `maestro_mps`, `maestro_mee`, `sku_mee_config`,
  `volumen_unitario_producto`, `areas_planta`, `operarios_planta`.

## APIs externas que llama

- **Google Calendar** vía iCal (env `GCAL_ICAL_URL`) o API (env
  `GCAL_API_KEY`). Función: `_fetch_calendar_events(days_ahead)`.
- Devuelve `{events:[], error:str|None, source:str}`.
- Si error → NO destruir nada.

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · Calendar = ÚNICA fuente de verdad
- App lee Calendar, NO escribe.
- `produccion_programada` se sincroniza con Calendar.
- Si Calendar dice X y DB dice Y → Calendar gana.

### INV-2 · Sync respeta guard inicio/descontado
- `inicio_real_at` set → producción en curso, NO TOCAR jamás.
- `inventario_descontado_at` set → ya descontó MPs, NO TOCAR.
- Si Calendar borra un evento que ya estaba en curso, audit_log
  `SYNC_CALENDAR_SKIP_EN_CURSO` y dejar para revisión manual.

### INV-3 · force_mirror solo lo dispara user explícito
- Default behavior (`force_mirror=False`): solo cancela `origen='calendar'`.
- `force_mirror=True`: HARD DELETE de cualquier orfan (manual + calendar).
- Solo se dispara desde el botón "📅 Re-sync Calendar" (admin).
- Background cron NUNCA debe pasar force_mirror=True.

### INV-4 · Idempotencia
- INSERT a `produccion_programada` idempotente por `(producto, fecha_programada)`.
- INSERT a `_sync_log` registra timestamp de cada corrida.

### INV-5 · Faltantes calculados en kardex
- `/producciones-faltantes` usa `_get_mp_stock(conn)` (NO query directo a tabla).
- Aggregación por `material_id` + nombre normalizado (acentos, etc.).

### INV-6 · Fijo vs Sugerido en `produccion_programada` (19-may-2026)
- **Fijo**: `origen IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')`. Lo que el
  usuario arrastró/editó, pedidos B2B, backfills. **Intocable** por procesos
  automáticos.
- **Sugerido**: `origen IN ('eos_canonico', 'calendar', 'manual', 'auto_plan',
  'sugerido')`. Mutable por regeneradores.
- Cualquier UPDATE/DELETE bulk en `produccion_programada` que no sea
  iniciado-por-usuario-explícito debe incluir
  `AND COALESCE(origen,'') NOT IN ('eos_plan','eos_b2b','eos_retroactivo')`
  tanto en SELECT de candidatos como en el UPDATE/DELETE.
- `limpiar_duplicados_producciones` ahora hace **soft cancel** (UPDATE
  estado='cancelado' + observaciones marcadas) en lugar de DELETE duro, para
  preservar evidencia y permitir recuperación.
- Test que protege: `test_golden_limpiar_duplicados_respeta_fijo`.

### INV-8 · Solo operario asignado / jefe / admin puede iniciar/terminar/completar (19-may-2026)

`POST /api/programacion/programar/<id>/iniciar`, `/terminar` y `/completar` validan
con `_caller_puede_operar_produccion()`:
- `ADMIN_USERS` (sebastian / alejandro) → siempre OK
- `es_jefe_produccion=1` (Luis Enrique) → OK
- Operario mapeado desde `compras_user` cuyo `id` figure en uno de los 4
  `operario_*_id` de la producción → OK
- Cualquier otro caso → 403 con código `no_asignado`

Antes los endpoints solo chequeaban login → operario A descontaba MPs de
producciones asignadas a operario B. Test: `test_golden_operario_no_puede_iniciar_produccion_ajena`.

### INV-10 · Abastecimiento = Calendar completo (Fix #3 · 23-may-2026)

`abastecimiento_consumo_horizontes` (`/api/abastecimiento/consumo-horizontes`)
ahora lee TODO el Calendar, no solo Fijo. Sebastián: "el abastecimiento
debería ser tomado desde el calendario donde tenemos programado todo por
varios meses".

- **Default** (sin param): `origen IN ('eos_plan','eos_b2b','eos_retroactivo',
  'eos_canonico','auto_plan','sugerido')` · TODO lo del Calendar.
- **`?solo_fijo=1`** (legacy): solo `eos_plan/b2b/retroactivo`.
- Antes (`comprometido` default) → solo Fijo · causaba que Abastecimiento
  mostrara números distintos al Calendar (3 fuentes paralelas divergentes).
- Promoción a Fijo: REPROGRAMAR_PRODUCCION_PROGRAMADA y EDITAR_KG_PRODUCCION
  promueven Sugerida → eos_plan al moverla · sin duplicar consumo MP.

`modo=run_rate` sigue agregando proyección velocidad×días encima del Calendar
(para análisis what-if), descontando Calendar para evitar doble-conteo.

SELECT incluye `pp.origen` como 7° campo · unpack en ambos loops
(`for ... in prod_rows` líneas 8158 + 8303). Tests:
`test_golden_abastecimiento_consumo_horizontes` valida default + solo_fijo.

### INV-9 · `_auto_asignar_operarios` es atómico (todo-o-nada) (19-may-2026)

La función valida que los 4 roles tengan candidato antes de tocar la BD.
Si el pool no alcanza (todos fijos o jefes), aborta retornando `None` sin
modificar la producción, preservando el estado previo. El UPDATE final usa
valores absolutos (no COALESCE) porque los 4 están garantizados.

Antes el caller NULLeaba los 4 operarios ANTES de invocar el helper · si el
helper no podía llenar todos, quedaba la producción con roles parciales NULL.
Test: `test_golden_auto_asignar_operarios_no_deja_roles_null_parcial`.

### INV-7 · Auditoría bulk-mutaciones a `produccion_programada` (19-may-2026)

Auditoría completa post-incidente del 19-may. Lista de TODOS los puntos
que mutan en bulk + status. Si agregas uno nuevo, debe entrar acá.

| Endpoint / función | Tipo | ¿Respeta Fijo? | Notas |
|---|---|---|---|
| `programacion.py limpiar_duplicados_producciones` (~7211) | soft UPDATE | ✅ (commit b5edbc0) | era DELETE duro; fix 19-may |
| `programacion.py _sync_calendar_a_produccion_programada` espejo (~9222) | DELETE bulk | ✅ | `NOT IN (Fijos)` cuando `force_mirror=True` |
| `programacion.py _sync_calendar_a_produccion_programada` legacy (~9230) | UPDATE cancel | ✅ | solo `origen='calendar'` |
| `admin.py` SKU remapeado cleanup (~10356) | UPDATE cancel | ✅ | solo `origen='calendar'` |
| `admin.py limpiar_produccion_zombies` cancel-viejas (~21086) | DELETE | ✅ | filtra >30d cancelados (no afecta presente) |
| `admin.py limpiar_produccion_zombies` prog-viejas (~21094) | UPDATE cancel | ✅ | `NOT IN (Fijos)` + >7d sin iniciar |
| `admin.py limpiar_produccion_zombies` dedup gcal (~21116) | UPDATE cancel | ✅ | `NOT IN (Fijos)` |
| `plan.py limpiar_duplicados_plan` (~3702) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py generar_plan_perfecto` (~3854) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py regenerar_canonicos` (~4233) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py aplicar_ia_bulk` (~10698) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py aplicar_ia_anual` (~10869) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |

Single-row UPDATE/DELETE `WHERE id=?` son seguros por diseño (user-driven
explícito, con guard de `inicio_real_at`/`inventario_descontado_at` cuando
aplica). No necesitan filter por origen.

Tests goldens que protegen:
- `test_golden_plan_fijo_sobrevive_regenerar` (plan.py regeneradores)
- `test_golden_limpiar_duplicados_respeta_fijo` (programacion.py limpiar_duplicados)
- `test_golden_limpiar_duplicados_respeta_guard` (no toca iniciadas)

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `programacion.py`... |
|---|---|---|
| Tab Plan en `/planta` | `/producciones-faltantes` | ...Luis Enrique no ve qué producir |
| `compras.py /agrupadas` | `solicitudes_compra_items` | ...Catalina ve duplicados |
| `auto_plan.py crons` | `produccion_programada`, `mp_lead_time_config` | ...IA propone mal |
| Operación Live | `produccion_programada` | ...turno arranca con info errada |

---

## Endpoints que expone

- `GET  /api/programacion/producciones-faltantes` · vista plana
- `GET  /api/programacion/producciones-agrupadas` · una fila por producto
- `POST /api/programacion/solicitar-faltantes-bulk` · crea SOLs por proveedor
- `POST /api/programacion/limpiar-duplicados-producciones` · respeta guard
- `POST /api/programacion/checklist/sync-calendar` · sync · `?force_mirror=true`
- `DELETE /api/programacion/produccion-programada/<id>/borrar` · admin
- `GET  /api/programacion/debug-producto/<producto>` · diagnóstico admin
- `POST /api/planta/auto-asignar-hoy` · admin · bulk re-asignación IA del día
  (área + 4 operarios). Excluye orígenes Fijos · respeta lo Fijo · escribe
  `auto_asignacion_log` y `audit_log` (`AUTO_ASIGNAR_HOY_BULK`).

---

## Cambios recientes (post-mortems)

### 2026-05-07 · Sync espejo no borraba orfanos manuales
- **Bug**: filtro `WHERE origen='calendar'` excluía manuales.
- **Síntoma**: AZHC Lun 11 manual fantasma sobrevivía aunque Calendar
  lo movió a Jue 14.
- **Fix**: param `force_mirror=True` quita el filtro. UI lo dispara
  desde el botón explícito.
- **Test que cazaría**: `test_golden_sync_calendar_espejo_borra_orfan_manual`.

### 2026-05-07 · Sync early-return con events vacíos
- **Bug**: `if not events: return 0` impedía cleanup en force_mirror.
- **Síntoma**: en tests sin Calendar API, force_mirror no hacía nada.
- **Fix**: solo return early si hay error API (`cal.get('error')`).
  Events vacíos legítimos siguen al cleanup.

### 2026-05-12 · Hook auto-EBR al iniciar producción (Fase 1 BRD)
- `prog_iniciar_produccion` ahora llama `_intentar_crear_ebr_auto()`
  después del audit_log de INICIAR_PRODUCCION.
- Si hay MBR aprobado para el producto, crea EBR vinculado por
  `produccion_id` con pasos clonados (estado='pendiente').
- **NON-FATAL**: si falla la creación del EBR (excepción cualquiera),
  loguea warning pero NO bloquea el inicio de producción. Esto es
  invariante crítica: el flujo Mayerlin/operario aprieta 'Iniciar' NO
  debe romperse por bugs del BRD.
- Idempotente vs `produccion_id` (re-iniciar no duplica EBR).
- Lote auto-generado: `<prod-short>-<evento_id>-<YYYYMMDD>` (UTC).
- Response incluye campo `brd_ebr` con resultado.
- Tablas escritas adicionales (delegadas a brd.py vía cursor compartido):
  `ebr_ejecuciones`, `ebr_pasos_ejecutados`.
- **Test que cazaría regresión**:
  `test_golden_brd_hook_auto_ebr_al_iniciar_produccion`.

### 2026-05-28 · Reversión precisa de MP por `produccion_id` (mig 201)
- `revertir-completado` revertía las Salidas de MP filtrando por
  `observaciones LIKE 'Producción ... {producto} — {fecha}%'`. Dos
  producciones del MISMO producto+fecha colisionaban → revertir una
  devolvía el MP de ambas (inventario fantasma · drift +).
- **Mig 201**: `movimientos.produccion_id` (+ índice). Las Salidas de
  `_descontar_mp_produccion` (iniciar) y `prog_completar_evento` (completar)
  guardan `produccion_id = evento_id`.
- La reversión filtra por `produccion_id` EXACTO; el LIKE por texto queda
  solo como fallback para movimientos legacy (`produccion_id IS NULL`).
- Mismo patrón que ya usaba la reversión MEE vía `lote_ref`.
- **Test que cazaría regresión**:
  `test_revertir_completado_no_cross_reversal_mp`.

### 2026-05-29 · Auditoría ronda 2 · audit_log en mutaciones de produccion_programada
- **`prog_revertir_completado`**: agregado `audit_log(accion='REVERTIR_COMPLETADO')`
  antes del commit (operación inversa de COMPLETAR_PRODUCCION, regulada INVIMA).
- **`planta_aceptar_produccion`**: agregado `audit_log(accion='ACEPTAR_PRODUCCION')`
  tras asignar área + crear tareas (registra quién aceptó/cuándo).

### 2026-05-30 · planta_aceptar_produccion crea/vincula EBR (MyBatch fase 1)
- Al aceptar, si `config.EBR_MODE` ∈ ('warn','strict'), llama
  `brd.crear_ebr_desde_mbr` para crear/vincular el EBR del lote (audit
  CREAR_EBR_AUTO). Con 'strict' BLOQUEA (409 SIN_MBR_APROBADO) antes de mutar si
  el producto no tiene MBR aprobado. Default 'off' = sin cambios. Ver CONTRACT_brd.md.
