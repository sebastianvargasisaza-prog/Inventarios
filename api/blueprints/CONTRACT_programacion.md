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
