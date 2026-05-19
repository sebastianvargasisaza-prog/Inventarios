# CONTRACT · `compras.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**

Última revisión: 2026-05-19

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `solicitudes_compra` | INSERT/UPDATE/DELETE | Crear SOL, aprobar, limpiar planta |
| `solicitudes_compra_items` | INSERT/UPDATE/DELETE | Items de SOL |
| `ordenes_compra` | INSERT/UPDATE | Crear OC desde SOL, aprobar, recibir |
| `oc_items` | INSERT/UPDATE | Items de OC |
| `pagos_oc` | INSERT | Pago registrado |
| `comprobantes_pago` | INSERT | PDF generado |
| `maestro_mps` | UPDATE | Sync proveedor desde PATCH SOL |
| `mp_lead_time_config` | INSERT/UPDATE | Sync proveedor + crear si falta |
| `precio_historico_mp` | INSERT | Cambio de precio_unit_g en SOL |
| `audit_log` | INSERT | Cada operación |

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · 3 fuentes de SOL no se mezclan
Filtros `?fuente=` en `/api/solicitudes-compra` y `/agrupadas-por-proveedor`:
- `planta`: `categoria IN ('Materia Prima','Empaque','Material de Empaque')`
- `usuarios`: `categoria NOT IN (planta + influencer)`
- `influencers`: `categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')`
- Sin param: legacy compatible (todas).

### INV-2 · PATCH item sincroniza GLOBAL
Cuando Catalina edita un item:
- `proveedor` cambió → UPDATE `maestro_mps.proveedor` + UPSERT
  `mp_lead_time_config.proveedor_principal`.
- `precio_unit_g` cambió → UPDATE `maestro_mps.precio_referencia` =
  `precio_unit_g * 1000` ($/kg).
- Audit: `SYNC_PROVEEDOR_GLOBAL`.
- **GOLDEN PATH 3** lo verifica.

### INV-3 · Solo admin puede modificar permisos / aprobar override
- `_require_admin` para reset password, hard delete SOL, override aprobación.
- `_require_compras_write` para CRUD SOL/OC normal (compras + admin).

### INV-4 · No revertir Pago en Pagada
- Una OC marcada como Pagada NO puede volver a Borrador.
- Si error, crear OC nueva o cancelar la actual con motivo (audit).

### INV-5 · Limpiar SOLs planta solo no-OC
- `/limpiar-solicitudes-planta` borra solo `estado='Pendiente'` AND
  `numero_oc=''`. NUNCA toca SOLs con OC vinculada.

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `compras.py`... |
|---|---|---|
| `programacion.py /faltantes-bulk` | `solicitudes_compra` schema | ...bulk crea SOLs malformadas |
| `auto_plan.py /aplicar-plan` | `mp_lead_time_config` (sync) | ...auto_plan no ve nuevo proveedor |
| `inventario.py /maestro-mps` | `maestro_mps` (sync) | ...stock display con proveedor viejo |
| Tab Planta en `/compras` | `/agrupadas?fuente=planta` | ...Catalina ve mezclado |
| Tab Influencers | `?fuente=influencers` | ...se solapa con Marketing |

---

## Endpoints que expone

### Solicitudes
- `GET  /api/solicitudes-compra?fuente=...&categoria=...`
- `POST /api/solicitudes-compra` · crear (cualquier user)
- `PATCH /api/solicitudes-compra/<num>/items` · sync GLOBAL
- `POST /api/compras/limpiar-solicitudes-planta` · cleanup

### Agrupadas
- `GET /api/compras/solicitudes-agrupadas-por-proveedor?fuente=...`
- `POST /api/compras/consolidar-auto-pendientes`
- `POST /api/compras/limpiar-y-regenerar-auto-plan`

### Órdenes de compra
- `GET  /api/ordenes-compra` · listado filtrado
- `POST /api/ordenes-compra` · crear desde SOL
- `PATCH /api/ordenes-compra/<num>` · approve/cancel
- `POST /api/ordenes-compra/<num>/items` · agregar item
- `PATCH /api/ordenes-compra/<num>/items/<id>` · editar item
- `DELETE /api/ordenes-compra/<num>/items/<id>` · borrar item

### Pagos
- `POST /api/ordenes-compra/<num>/pagar` · registrar pago
- `GET  /api/comprobantes-pago/<oc>` · PDF

### Influencers
- `GET  /api/solicitudes-compra?categoria=Influencer/Marketing Digital`
- `POST /api/compras/influencer/limpiar-no-pagadas`

---

## Cambios recientes (post-mortems)

### 2026-05-06 · 3 fuentes mezcladas en tab Solicitudes
- **Bug**: Catalina veía planta + influencer mezclado en tab "Solicitudes".
- **Fix**: `?fuente=` filter + 3 tabs separados en UI.
- **Test que cazaría**: `test_golden_3_fuentes_solicitudes_no_se_mezclan`.

### 2026-05-06 · PATCH no propagaba al cron
- **Bug**: cambiar proveedor en SOL no se reflejaba en próximo
  auto_plan (que lee `mp_lead_time_config` con COALESCE).
- **Fix**: PATCH ahora UPSERT a `mp_lead_time_config`.
- **Test que cazaría**: `test_golden_patch_sol_sincroniza_global`.

### 2026-05-19 · RBAC inconsistente · 4 endpoints sin guarda (auditoría)
- **Bug**: `DELETE /api/ordenes-compra/<oc>`, `POST /api/generar-oc-automatica`
  y `PATCH /api/solicitudes-compra/<n>/estado` no verificaban permisos de
  Compras (solo sesión, o nada); `PUT /api/ordenes-compra/<oc>` permitía
  revertir una OC Pagada a cualquier estado → violaba INV-4.
- **Fix**: los tres primeros ahora exigen `_require_compras_write`; el PUT
  rechaza cambiar el estado de una OC Pagada. Las cuatro operaciones auditan.
