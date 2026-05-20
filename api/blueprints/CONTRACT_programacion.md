# CONTRACT · `programacion.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**

Última revisión: 2026-05-07

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
| `_sync_log` | INSERT | Cada corrida del sync Calendar |
| `audit_log` | INSERT | Operaciones destructivas |

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
