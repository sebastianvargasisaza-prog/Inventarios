# Eje 1 · Madurez multi-tenant SaaS

**Veredicto**: 🔴 **BLOQUEANTE** — el horizonte de 3-6 meses no es viable para "vender a otros labs" en sentido SaaS público (autoservicio + billing + isolation por tenant). Es viable un modelo **single-tenant deployment-por-cliente con white-label** en 3-4 meses, que NO es lo mismo.

**TL;DR (5 líneas honestas)**

1. La app no tiene `tenant_id` en NINGUNA tabla (cero ocurrencias en ~167 tablas de `api/database.py`). Existe un campo `empresa` con valores `'Espagiria' | 'ANIMUS' | 'Animus' | 'HHA'` pero es para distinguir las DOS marcas internas del holding, no para aislamiento — está hardcodeado, mal normalizado (case-insensitive ad-hoc en queries: `programacion.py:753`), y solo presente en ~16 de las ~167 tablas.
2. Auth/RBAC está construida 100% sobre **usuarios físicos hardcodeados** (`sebastian`, `alejandro`, `mayra`, `catalina`, `daniela`, `luz`, `mayerlin`, ...) en `api/config.py:16-44` y referenciados por nombre propio en SQL (`auto_plan_jobs.py:1260: LOWER(email) LIKE '%alejandro%'`). El RBAC NO es por roles abstractos sino por listas de personas.
3. SQLite con WAL en `/var/data/inventario.db` con 1 disco Render: arquitectura DB-único-archivo no soporta DB-por-tenant ni aislamiento físico real; las **47 cron jobs** (verificado: 23 nominales en `auto_plan_jobs.py:565-611` + 24 watchers horarios en `:612-615`) corren globalmente sobre toda la DB.
4. 104 migraciones append-only + sistema `safe_alter()` + 50 golden paths + 99+ tests + 59 triggers SQL + lock distribuido `cron_locks` = arquitectura interna sólida pero CASADA a single-tenant. Agregar `tenant_id` retroactivamente a 167 tablas es ~3-4 meses solo de migración + verificación + reescritura de cada query — alrededor del 30-40% del SQL toca, no el 60%, pero la disciplina de aislamiento es perfecta o no es.
5. Cero billing, cero onboarding, cero SSO, cero subdomain routing, branding hardcodeado en `api/branding.py:17-26` con `PRODUCT_NAME="EOS"` y `COMPANY_NAME="HHA Group"`, emails internos del holding en seeds (`sebastianvargasisaza@gmail.com` en `api/config.py:108`).

## Bloqueantes para vender a otros labs en 3-6 meses

| # | Bloqueante | Esfuerzo | Cómo se ataca |
|---|---|---|---|
| 1 | Cero `tenant_id` en 167 tablas. Cualquier cliente B vería datos del A en cualquier query si no se filtra. | 8-12 semanas | Mig 105+: `tenant_id INTEGER NOT NULL DEFAULT 1` en ~50 tablas top + índice compuesto `(tenant_id, ...)`. Backfill = todo `tenant_id=1` (HHA). Wrapper en `get_db()` que inyecte filtro o reescritura de cada query (~1000+ lugares). SQLite no tiene RLS. |
| 2 | RBAC por nombre propio. `ADMIN_USERS={"sebastian","alejandro"}` (`api/config.py:37`); SQL como `WHERE LOWER(email) LIKE '%alejandro%'` (`auto_plan_jobs.py:1260`); `['sebastian','alejandro','catalina']` literal en `auto_plan_jobs.py:234`. | 4-6 semanas | Tablas `users(id, tenant_id, username, password_hash, email)` + `user_roles(user_id, role)`. Reemplazar todos los `if user in ADMIN_USERS:` (~150 lugares). Eliminar nombres propios de queries. |
| 3 | 47 cron jobs globales (`auto_plan_jobs.py:565-615`). Cada job consulta toda la DB; en multi-tenant un job fallando en cliente A bloquea el lote. | 3-4 semanas | Refactor `_loop_multi_cron` (`auto_plan_jobs.py:3197`) para iterar tenants. `cron_locks` (mig 81) necesita columna `tenant_id`. Emails que van a `EMAIL_GERENCIA` global → `tenant_settings.email_gerencia`. |
| 4 | Sin onboarding ni billing. No hay `/signup`, no hay tabla `tenants`, no hay Stripe/Paddle. Crear un usuario hoy = editar `api/config.py` + setear `PASS_<USER>` en Render → redeploy. | 4-6 semanas | Construir desde cero: `tenants(id, slug, nombre, plan, billing_status, created_at)`, `tenant_users(tenant_id, user_id, role)`, wizard onboarding, integración Stripe (USD) + Bold/Wompi (COP), webhooks de cancelación que congelen tenant. |
| 5 | Single-DB en Render con 1 disco de 1GB (`render.yaml:8-11`, `:41-44`). SQLite no soporta concurrencia decente cross-tenant; 5+ clientes activos = `database is locked` cascadas pese a WAL. Backups (`api/backup.py`) son del archivo entero — no hay restore selectivo por tenant. | 2-4 sem decisión + 4-8 sem ejecución | Decisión arquitectónica abajo. |
| 6 | Branding hardcodeado. `api/branding.py:17-26` define producto y compañía. PDFs incluyen literal "Espagiria Laboratorios" (`inventario.py:4064`, `:4215`, `:4255`). 960 ocurrencias de "HHA/Espagiria/ANIMUS/INVIMA" en `api/`. | 2-3 semanas | Mover a `tenant_settings(logo_url, brand_name, brand_primary, company_legal, ...)`. Reemplazar literales en `api/blueprints/**` y `api/templates_py/**`. |
| 7 | Calendar + Shopify + GHL + Email son globales (env vars únicas en `render.yaml`). Cada lab tiene su propia cuenta. | 3-4 semanas | `tenant_integrations(tenant_id, integration, credentials_encrypted)`. Cifrado at-rest. Cron jobs iteran tenants con credenciales válidas. |
| 8 | Sin SSO/SAML/OAuth. Cero referencias en `api/`. | 2-3 sem (Google) o 4-6 sem (SAML) | No bloqueante para primeros 5-10 deals si los labs son chicos; postponer post-launch. |

**Total para SaaS verdadero (1 deployment, N tenants): 6-9 meses con 1-2 ingenieros senior. NO 3-6.**
**Camino alternativo viable en 3-4 meses: deployment-por-cliente "white-label hosted"** (ver decisión #3).

## Mejoras incrementales (no bloquean lanzamiento)
- Hash passwords PBKDF2/scrypt forzado (`api/config.py:172`) — mantener.
- MFA TOTP ya implementado (`api/blueprints/mfa.py`, mig 57) — generalizar a no-admins.
- `audit_log` con ~485 ocurrencias — sólido; agregar `tenant_id` y queda multi-tenant ready.
- CSRF + Origin check (`api/auth.py:309`) — bien.
- Sentry con scrub PII (`api/index.py:17-49`) — agregar `tenant_id` como tag.
- `safe_alter()` (`api/database.py:59`) y framework idempotente — excelente base.
- Tests + 50 golden paths: cobertura sólida pero asumen single-tenant; cada GP duplicada como "GP-X-cross-tenant".

## Decisiones arquitectónicas que tienes que tomar YA

### 1. ¿SQLite + tenant_id, Postgres single-DB, o DB-por-tenant?

| Opción | Pros | Contras | Recomendación |
|---|---|---|---|
| A. SQLite single-DB + tenant_id | Cero migración engine. Mantiene 484+ queries con literales SQLite. | 1 writer global → `database is locked` con 5+ tenants activos. Backup monolítico, restore selectivo imposible. | NO recomendado. |
| B. Postgres single-DB + tenant_id | Concurrencia real, RLS posible, PITR backup, escalable. | 6-9 sem portando 352 `INSERT OR REPLACE`, 59 triggers, 1363 `datetime('now')`/`date()`, 161 `AUTOINCREMENT`, `PRAGMA *`. 104 migraciones a reescribir. Riesgo de romper 50 golden paths. | Solo si horizonte 9+ meses. |
| C. SQLite DB-por-tenant (`/var/data/tenants/<slug>/inventario.db`) | Aislamiento físico perfecto. Backup/restore por cliente trivial. Mantiene SQLite-específico SIN cambios de syntax. | `get_db()` (`api/database.py:31`) lee constante `DB_PATH` — hay que reescribir. ~135 invocaciones directas a `sqlite3.connect(DB_PATH)` (auth.py, mfa.py, backup.py, `admin.py:106`). Render disk de 1GB tope ~10-15 clientes con datos reales. | **RECOMENDADO** para 3-6 meses. |

### 2. RBAC: refactor por roles forzoso
Estado actual (constantes `ADMIN_USERS={"sebastian","alejandro"}`) NO es viable. `api/config.py:16-72` enumera 19 personas reales. Cambio: tablas `roles` + `user_roles`, `has_role(user, 'admin')`. Eliminar TODAS las menciones a nombres propios (~100+ lugares grep-ables).

### 3. Multi-tenancy lógico vs físico
**Recomendación: PHYSICAL deployment-per-tenant durante meses 1-6, lógico después.** En 3-6 meses no se logra el rigor de aislamiento lógico que requiere INVIMA/farma sin pruebas exhaustivas. Render deploy-per-customer ~$15/cliente; a $290k COP/mes (ROADMAP_SAAS_2026.md:69) margen >85%. Mes 7+: cuando el #11º cliente justifique el rewrite a multi-tenancy lógico con Postgres + RLS.

## Inventario actual (datos)

- **Total tablas SQL: ~167** (105 `CREATE TABLE IF NOT EXISTS` en `MIGRATIONS` + 62 en `init_db()` clásico de `api/database.py`).
- **Tablas críticas que requerirían `tenant_id` (top 20)**: `movimientos`, `maestro_mps`, `producciones`, `formula_headers`, `formula_items` (PROPIEDAD INTELECTUAL — leak catastrófico), `solicitudes_compra` + items, `ordenes_compra` + items + `pagos_oc`, `proveedores`, `clientes`, `pedidos` + items, `produccion_programada`, `audit_log` (regulatoria INVIMA), `users_passwords` + `users_mfa`, `flujo_ingresos` + `flujo_egresos`, `empleados` + `nomina_registros`, `quejas_clientes` + `recalls` + `desviaciones` + `control_cambios`, `sgd_documentos` + `sgd_versiones`, `equipos_planta` + `calibraciones`, `chat_threads` + `chat_messages`, `marketing_campanas` + `marketing_influencers`, `notificaciones_app`, `facturas` + items + pagos + `comprobantes_pago`. **No requieren** `tenant_id`: `schema_migrations`, `rate_limit`.
- **Constantes hardcodeadas que necesitan ser por-tenant (20)**: `LIMITES_APROBACION_OC` (`config.py:79`), `FORMULA_PIN` (`config.py:91`), `MARGEN_PLANEACION_DIAS` (`auto_plan.py:48`), threshold gerencia 5% (`inventario.py:3453: UMBRAL_ESCALA = 0.05`), `AREA_USERS` (`config.py:122`), `USER_EMAILS` (`config.py:102`), TODAS las 13 listas de roles en `config.py:16-72`, `BACKUP_INTERVAL_HOURS=6` / `BACKUP_RETENTION_DAYS=14` (`backup.py:37-41`), `BACKUP_OFFSITE_URL` (`backup.py:49`), `_LOCKOUT_SECS=900` / `_MAX_ATTEMPTS=5` (`auth.py:13-14`), `PERMANENT_SESSION_LIFETIME=30days` (`index.py:122`), regla pipeline 7 días (`MEMORY.md`), Mayerlin fija en dispensación (mig 82, triggers `trg_pp_fija_*`), `APP_BASE_URL=https://app.eossuite.com` (`config.py:53`), branding completo (`branding.py`), `GCAL_ICAL_URL` / `GCAL_API_KEY`, `SHOPIFY_TOKEN` / `SHOPIFY_SHOP`, `GHL_API_KEY` / `GHL_LOCATION_ID`, `EMAIL_REMITENTE` / `EMAIL_PASSWORD`, PDFs con literal "Espagiria Laboratorios" (`inventario.py:4064`, `:4215`, `:4255`).
- **Queries con SQL específico de SQLite no-portable**:
  - `INSERT OR REPLACE` / `INSERT OR IGNORE`: **352 ocurrencias en 20 archivos** (top: `database.py:284`, `auto_plan.py:8`, `marketing.py:17`).
  - `PRAGMA` runtime: 392 en 32 archivos.
  - `datetime('now')` / `date(...)`: 1363 en 35 archivos.
  - `AUTOINCREMENT`: 161 declaraciones en `database.py`.
  - Triggers SQLite: 59 (mig 82, 83, 97, 98).
  - `sqlite3.connect(DB_PATH)` directos (bypassan `get_db()`): 135 en 10 archivos (`auth.py`, `mfa.py`, `backup.py`, `admin.py:106` peor ofensor).
  - `PRAGMA integrity_check`/`quick_check`/`incremental_vacuum` para health/maintenance.
  - **Veredicto portabilidad Postgres: ALTO costo, 6-9 semanas.**

**Hallazgo extra:** ya existe a medias el concepto `empresa` (541 ocurrencias en 38 archivos) con valores `'Espagiria'`, `'ANIMUS'`, `'Animus'`, `'HHA'`. Solo en ~16 tablas, sin índice ni FK, queries con filtros ad-hoc tipo `UPPER(TRIM(COALESCE(empresa,''))) = UPPER(?)` (`programacion.py:753`). **Es la peor versión posible de tenant_id**: existe pero no aísla, da falsa seguridad. Para multi-tenant verdadero hay que IGNORARLO y crear `tenant_id INTEGER NOT NULL FK tenants(id)` en paralelo, no extender el concepto roto.

## Hoja de ruta sugerida (3-6 meses)
**Premisa: deployment-por-cliente con SQLite (Opción C). NO multi-tenant lógico real.**
- **Mes 1**: tablas `tenants/users/tenant_users/roles/user_roles/tenant_settings/tenant_integrations` (mig 105-110). Middleware `g.tenant`. Refactor RBAC por roles. Mover branding/email/limites/PIN/threshold/AREA_USERS a `tenant_settings`. Eliminar nombres propios de SQL.
- **Mes 2**: wizard `/onboarding` (empresa → primer admin → seed catálogos). `scripts/provision_tenant.sh` que crea service Render via API + DB blank + subdominio. Documentar `RUNBOOK_TENANT_PROVISIONING.md`.
- **Mes 3**: `tenant_integrations` cifrado at-rest. Refactor sync Calendar/Shopify/GHL para credenciales por DB. Cron jobs reciben `tenant_id`. Suite tests cross-tenant (50+ tests "A nunca ve B"). Pen-test interno.
- **Mes 4-6**: Stripe USD + Bold/Wompi COP, `subscriptions` table, webhooks de cancelación. Beta 1-2-3 clientes. Migración asistida (`scripts/import_legacy_inventory.py`). SSO Google OAuth. Plan migración Postgres mes 12.

**Lo que NO entra en 3-6 meses:** multi-tenancy lógico real, SAML enterprise, marketplace de fórmulas, white-label completo (dominio + email + branding del cliente), exportable audit logs SOC 2 / ISO 27001.

## Riesgos
1. **Cross-tenant leak en deployments compartidos** si se mete un 2º cliente al mismo service: 1000+ queries sin filtro `tenant_id` lo causan inmediato. Mitigación: nunca permitir 2 tenants en mismo deployment hasta mes 12+.
2. **Concurrencia SQLite**: cada cliente = 1 deployment Render = 1 disco = 1 SQLite, costo lineal pero concurrencia resuelta por aislamiento físico.
3. **104 migraciones N veces**: cada deployment las corre al startup (~15-30s). Mitigación: snapshot DB ya migrada al provision.
4. **47 cron jobs × N clientes** = 470 jobs si hay 10 clientes. Sentry/Watchman budget. Aceptable.
5. **Regulación cosmética por país**: hoy todo asume Colombia/INVIMA (BDG-PRO-002, COC-PRO-008, ASG-PRO-001). México (COFEPRIS) o Perú (DIGEMID) requieren plantillas regulatorias separadas. No bloqueante para primeros 5-10 colombianos.
6. **PI de fórmulas**: `formula_items` contiene 21+ fórmulas reales de productos cosméticos HHA (Blush Balm, Suero Vit C, etc., mig 104). El provisioning a otros clientes NO debe seedear catálogo privado. Confirmar con Sebastián.
7. **Calendar como single source of truth**: cada cliente debe conectar su propio Google Calendar. Sin Google Workspace = construir calendar interno (4-6 sem extras fuera de scope).
8. **Personas reales en triggers SQL** (`mayerlin` fija dispensación, mig 82): específicos del staff Espagiria. Mover a `tenant_settings` o eliminar trigger y validar en Python — rompe golden paths, requiere coordinación.
9. **`audit_log` regulatorio sin `tenant_id`**: en multi-tenant un auditor INVIMA del cliente B no puede recibir log mezclado. Migración crítica.
10. **Bus factor 1 (Sebastián)**: 600-800 horas de dev + CEO + único dev → horizonte realista se duplica. Recomendación: contratar 1 ingeniero senior dedicado durante los 6 meses.
