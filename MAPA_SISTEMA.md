# MAPA DEL SISTEMA · EOS / ERP HHA Group

Referencia de arquitectura para no romper cosas al modificar. Flask monolito + SQLite,
~34 blueprints, deploy en Render (`app.eossuite.com`). Construido por Sebastián Vargas
(CEO HHA Group) para ÁNIMUS Lab + Espagiria Laboratorio.

> **Antes de tocar `inventario.py`, `compras.py`, `programacion.py` o `plan.py`:**
> leer `MEMORY.md` → el `CONTRACT_<modulo>.md` → los golden paths. Son módulos críticos.

---

## 1. Arranque y plomería

| Archivo | Qué hace |
|---------|----------|
| `api/index.py` | Boot · crea Flask, configura SECRET_KEY (efímera si falta env var), registra ~34 blueprints, corre `init_db()`, arranca 3 daemons (marketing loop, auto-plan cron, multi-cron). Hooks before/after_request. |
| `api/auth.py` | Seguridad · cadena de `before_request`: timeout sesión 8h, `require_auth_for_api` (bloquea /api/ sin sesión salvo `PUBLIC_API`), `enforce_mfa_for_admins`, `csrf_origin_check`. Rate limiting tabla `rate_limit`. |
| `api/config.py` | Roles · `ADMIN_USERS={sebastian,alejandro}`, `COMPRAS_USERS`, `CALIDAD_USERS`, `PLANTA_USERS`, etc. Passwords desde env `PASS_<USER>` (hash). |
| `api/database.py` | DB · `_configure_conn` (journal_mode=DELETE, synchronous=FULL, busy_timeout=15s), `get_db()` per-request, lista `MIGRATIONS` append-only. |
| `api/templates_py/` | UIs server-side · cada blueprint sirve HTML desde un string Python. `dashboard_html.py` es el grande (1.2 MB). Patrón de pestañas con `switchTab()` / `switchProgTab()`. |

**Multi-cron** · ~47 jobs en `auto_plan_jobs.py` → `JOBS_SCHEDULE`. Loop interno cada 5 min, dedup vía `cron_locks`. Jobs clave: `lunes_7am_workflow`, `sync_shopify`, `watcher_health_HH` (cada hora · incluye auto-healing de BD).

---

## 2. Módulos de negocio CORE (críticos · tienen CONTRACT + golden paths)

### `inventario.py` — kardex de MP y MEE
- **Stock = SUM(movimientos)**, siempre. Recepción, conteos cíclicos, lotes, trazabilidad, envasado/acondicionamiento/liberación.
- Endpoints: `POST /api/movimientos`, `/api/recepcion`, `/api/maestro-mps`, `/api/conteo/*`, `/api/lotes/*`, `/api/trazabilidad/*`.
- **Zona peligrosa:** `conteo_ajustar` (~3889), `eliminar_lote`, `_shopify_sync_producto`.

### `compras.py` — solicitudes (SOL), órdenes (OC), proveedores
- 3 fuentes de SOL separadas: planta / usuarios / influencers (filtro `?fuente=`).
- Endpoints: `/api/solicitudes-compra`, `/api/ordenes-compra`, `/api/compras/oc-desde-solicitudes`, recepción/pago de OC.
- **Zona peligrosa:** `update_sol_items` (~6097, sincroniza GLOBAL a maestro_mps), `recibir_oc` (escribe kardex).

### `programacion.py` — producción, calendario, planta (el más grande, 13k líneas)
- Sincroniza Google Calendar → `produccion_programada`, gestiona áreas/operarios, descuenta MP/MEE al producir.
- **`_get_mp_stock` (~605) = cálculo de stock canónico de TODO el sistema.** Lo consumen plan, auto_plan, compras.
- Endpoints clave: `producciones-faltantes`, `solicitar-faltantes-bulk`, `programar/<id>/{iniciar,terminar,completar}`.
- **Zona peligrosa:** `_sync_calendar_a_produccion_programada` (~8743), `_descontar_mp_produccion`, `limpiar_duplicados_producciones`.

### `plan.py` — necesidades, autoplan IA, canónicos, B2B
- `_calcular_animus_dtc` (~478) = motor del semáforo de necesidades (velocidad de venta, cobertura).
- `regenerar_canonicos` lee `producto_canonico_config` y genera el plan 365d. `_proxima_fecha_habil` (festivos L-V).
- Endpoints: `/api/plan/necesidades`, `/regenerar-canonicos`, `/api/pedidos-b2b`, `/api/programacion/producciones-faltantes`.
- Pestaña Abastecimiento (en dashboard) consume `producciones-faltantes` + `solicitar-faltantes-bulk`.
- **Zona peligrosa:** `regenerar_canonicos`, `aplicar-ia-bulk/anual`, `_calcular_animus_dtc`.

---

## 3. Blueprints secundarios

| Módulo | Qué hace |
|--------|----------|
| `core.py` | Login, logout, hub, navegación, cambiar-password |
| `mfa.py` | MFA TOTP · `/seguridad`, `/login/mfa`. Tabla `users_mfa` |
| `admin.py` | Panel admin · backups, emergency-restore, users, diagnósticos |
| `auto_plan.py` / `auto_plan_jobs.py` | Auto-Plan Maestro (lunes 7am) + los 47 jobs del multi-cron |
| `animus.py` | ÁNIMUS Lab D2C · Shopify/IG sync, conteo cíclico, agentes IA |
| `espagiria.py` | Panel radar Espagiria (Luz · gerencia) |
| `comercial.py` / `maquila.py` | Pipeline maquila B2B, prospectos, recall, despacho |
| `rrhh.py` | Empleados, nómina, ausencias, SGSST |
| `aseguramiento.py` | Calidad · desviaciones, cambios, quejas, recalls, SGD |
| `calidad.py` / `tecnica.py` / `compliance.py` | Calidad operativa, dirección técnica (fórmulas, INVIMA), BPM/CAPA |
| `gerencia.py` / `financiero.py` / `contabilidad.py` | Dashboards gerenciales, P&L, facturas, tesorería |
| `clientes.py` | CRM mayorista, aliados, pedidos, stock PT, despachos |
| `brd.py` | Batch Record Digital (MBR/EBR/IPC) GMP |
| `firmas.py` / `identidad.py` | Firma electrónica 21 CFR Part 11 |
| `hub.py` / `chat.py` / `notif.py` | Escritorio, chat interno, notificaciones |
| `marketing.py` / `comunicacion.py` / `bienestar.py` | Campañas, tareas RACI, portal empleados |
| `despachos.py` / `operario.py` | Recepción MP / cuarentena, vista mobile "Mi día" |

---

## 4. Capa de datos · tablas por dominio

- **Inventario MP:** `movimientos` (kardex canónico), `maestro_mps`, `mp_formula_bridge`, `mp_lead_time_config`, `conteos_fisicos`/`conteo_items`.
- **Bodega MEE (envases):** `maestro_mee` (stock persistido en `stock_actual`), `movimientos_mee`, `sku_mee_config`, `mee_lead_time_config`.
- **Compras:** `solicitudes_compra`/`_items`, `ordenes_compra`/`_items`, `proveedores`, `pagos_oc`, `comprobantes_pago`.
- **Producción/Plan:** `produccion_programada` (espejo Calendar), `formula_headers`/`formula_items`, `producto_canonico_config`, `pedidos_b2b`, `autoplan_decisiones`.
- **Calidad/INVIMA:** `desviaciones`, `control_cambios`, `quejas_clientes`, `recalls`, `mbr_*`/`ebr_*`, `e_signatures`, `usuarios_identidad`.
- **RRHH/Planta:** `empleados`, `nomina_*`, `operarios_planta`, `areas_planta`.
- **Gobierno:** `audit_log` (append-only, trigger bloquea UPDATE/DELETE), `schema_migrations`, `cron_locks`, `backup_log`, `users_passwords`/`users_mfa`.

**Relaciones clave:** `produccion_programada.producto` → `formula_headers.producto_nombre` → `formula_items` → (`mp_formula_bridge`) → `movimientos.material_id`. Recepción de OC genera filas en `movimientos`.

---

## 5. Reglas de negocio críticas (NUNCA romper)

1. **Stock MP = SUM(movimientos)** · nunca un caché paralelo.
2. **Todo INSERT a movimientos lleva lote real** · sintético solo si no hay lote.
3. **Calendar = única fuente de verdad de producción** · la app lee/espeja, nunca escribe.
4. **Filas con `inicio_real_at` o `inventario_descontado_at`** nunca las toca el sync ni limpieza.
5. **`force_mirror=True`** (hard delete) solo desde botón admin; crons siempre `False`.
6. **Threshold gerencia 5%** · diferencia ≥5% requiere aprobación admin.
7. **3 fuentes de SOL no se mezclan** (planta/usuarios/influencers).
8. **PATCH item de SOL sincroniza global** a `maestro_mps` + `mp_lead_time_config`.
9. **Display siempre en gramos** (excepto interno `cantidad_kg`).
10. **`audit_log` append-only y obligatorio** en mutaciones de inventario/SOL/OC/calidad.
11. **Planeación usa Shopify `Available`**, no `On hand`.
12. **Mayerlin fija en dispensación** · triggers DB protegen `fija_en_dispensacion=1`.

**MFA / sesión:** SECRET_KEY debe estar fija en env var de Render (si no, cada deploy invalida cookies). Cookie `mfa_trusted` rolling 60 días.

**BD:** journal_mode=DELETE (no WAL · WAL se corrompía en el disco de red de Render). Backups cada 1h. Auto-healing en el watcher horario restaura si se corrompe.

---

## 6. Cálculo de stock

- **MP** · `_get_mp_stock(conn)` en `programacion.py:605` · suma el kardex `movimientos` (Entrada suma, resto resta), resuelve por `material_id` y por nombre normalizado.
- **MEE (envases)** · `maestro_mee.stock_actual` · valor persistido (NO se recalcula on-the-fly). `movimientos_mee` es el kardex de auditoría.

---

## 7. Redes de seguridad anti-regresión

- **`tests/test_golden_paths.py`** · 141 tests E2E · spec ejecutable de los invariantes. Nunca modificar un test para hacer pasar un cambio (salvo que la regla de negocio cambie deliberadamente).
- **`scripts/reviewer.py`** · gate pre-commit · flagea blueprint sin CONTRACT, endpoint nuevo sin test, edición de funciones críticas, valida JS embebido con `node --check`.
- **`scripts/guardian.sh`** · gate pre-push · corre los golden paths; si rojo, bloquea el push.
- **`MEMORY.md`** · reglas estáticas inmutables del dominio.
- **`CONTRACT_<modulo>.md`** · invariantes por blueprint crítico.
- **Migraciones** · `MIGRATIONS` en `database.py` es append-only · usar `safe_alter` para DDL idempotente · nunca editar entradas pasadas.
