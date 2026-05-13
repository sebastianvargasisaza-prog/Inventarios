# Eje 3 · Deuda técnica y madurez operacional

**Veredicto**: 🔴 **ALTO RIESGO** para el salto SaaS multi-tenant + Batch Record digital regulado en 3-6 meses tal como está hoy.

**Top 3 deudas que bloquean el salto**:
1. **Single-tenant total**: 0 hits de `tenant_id|org_id|workspace_id` en todo `api/`. Las 170 tablas, 883 endpoints y 1.028 `fetchall()` necesitan refactor tenant-aware antes de poder vender un segundo cliente.
2. **`admin.py` y `database.py` son monolitos no validables GMP**: 22.570 LoC + 134 endpoints en uno; 524 KB + 99 migraciones registradas en el otro. Auditor INVIMA con experiencia en CSV (Computer System Validation) los rechaza tal cual.
3. **Audit log mutable + sin DR probado**: la tabla `audit_log` no tiene write-once protection (admin con shell SQLite puede UPDATE/DELETE), y el script `test_backup_restoration.py` existe pero no corre en CI — para 21 CFR Part 11 ambos son invalidantes.

---

**TL;DR**:
- La app **funciona** y tiene un cinturón de seguridad razonable para 1 tenant + 19 users (golden paths E2E, MFA admins, CSRF doble capa, WAL): es base sólida para que **EOS siga corriendo**, pero NO está estructurada para multi-tenant.
- **Bloqueante #1 multi-tenant**: cero `tenant_id`/`org_id` en 170+ tablas (grep: 0 hits en `api/`). Refactor de 99 migraciones append-only + 883 endpoints es 6-12 semanas antes del primer cliente externo.
- **Bloqueante #2 BRD regulado**: `admin.py` (22.570 LoC, 134 endpoints) y `database.py` (524 KB) son monolitos imposibles de validar para Batch Record GMP/INVIMA.
- Cobertura tests es engañosa: 23/50 golden paths verdes; con `pytest-cov` real estimaría 25-35% de líneas. `auto_plan` (10.853 LoC) y `marketing` (4.940 LoC) casi sin cubrir.
- Ops básicas razonables (backup nocturno + Sentry opcional + 47 cron jobs internos + integrity check) pero **sin staging, sin restore probado en CI mensual, SQLite single point of failure**.

## Heat map por área

| Área | Estado | Evidencia |
|---|---|---|
| Cobertura tests | 🟡 | 100 archivos · 1.318 funciones · 30.618 LoC tests vs 89.616 LoC blueprints (ratio 1:2.9). 23/50 golden paths verdes (`GOLDEN_PATHS_INVENTORY.md:132`). 9 blueprints sin tests propios: hub, gerencia, contabilidad, despachos, comunicacion, notif, core, auto_plan_jobs, mfa-parcial |
| Seguridad (no-pentest) | 🟡 | Bien: MFA admin enforced (`auth.py:251`), CSRF Origin+token (`auth.py:309`), rate-limit IP+user (`auth.py:137`), PBKDF2, validate_config startup, fallback plaintext eliminado (`config.py:12`). Mal: 42 `execute(f"...")` con SQL dinámico (mayoría son whitelist de tabla, igual son olor); CSP con `'unsafe-inline'` (`auth.py:404`); rotar SECRET_KEY = invalidar todas las sesiones |
| Observabilidad | 🟡 | Logs JSON con request_id (`index.py:407`); Sentry opcional; 0 endpoint Prometheus (grep `/metrics`: 0 hits); `/api/admin/health-detailed` excelente (15 secciones, `index.py:516`); pero **nadie despierta a las 3am** sin monitor externo (UptimeRobot/Pingdom no veo evidencia) |
| Performance/escalabilidad | 🔴 | 3 workers Gunicorn sync + SQLite WAL: techo ~30 users concurrentes (auto-confesado `SECURITY.md:120`). 47 cron jobs **internos** corren en worker pool — job lento bloquea HTTP. 1.028 `fetchall()` muchos sin LIMIT; `auto_plan.py` tiene 121. SQLite no viable >5 tenants |
| Calidad código | 🔴 | `admin.py` = 22.570 LoC, 134 endpoints, 196 fetchall, 298 except Exception. `database.py` = 524 KB, 99 migraciones, 176 CREATE TABLE. `programacion.py` = 12.992 LoC. **Top 4 = 53.259 LoC = 59% de blueprints**. 1.290 `except Exception` (1 cada ~70 LoC). Sin type hints sistemáticos. Sin linter config |
| Documentación | 🟡 | `CLAUDE.md` excelente. `RUNBOOK.md` cubre rollback/backup/errores. `SECURITY.md` honesto. `GOLDEN_PATHS_INVENTORY.md` tracking activo. **Solo 3 CONTRACT_*.md** para 27 blueprints (11%). Sin OpenAPI/Swagger (grep: 0 hits). SESSION_LOG con 2 entradas |
| Operaciones (backup/DR/deploy) | 🟡 | Backup automático cada 23h trigger oportunista (`index.py:312`); `test_backup_restoration.py` existe **pero NO en CI**. **Sin staging**: push main→prod (`RUNBOOK.md:62`). Migraciones append-only sin downgrade (`RUNBOOK.md:111`). 1 solo workflow CI |

## Heat map por blueprint (top 10 por LoC)

| Blueprint | LoC | Endpoints | Tests propios | Cobertura est. | CONTRACT.md | Estado |
|---|---|---|---|---|---|---|
| `admin.py` | **22.570** | 134 | 3 archivos · ~69 funciones | 10-15% | ✗ | 🔴 monolito · candidato #1 a partir |
| `programacion.py` | 12.992 | 98 | parcial vía `test_planta_*` + golden paths | 25-30% | ✓ | 🟡 cubierto en críticos · enorme |
| `auto_plan.py` | 10.853 | 89 | 1 archivo | 5-10% | ✗ | 🔴 IA+cron+plan · 193 except Exception |
| `compras.py` | 6.844 | 64 | 4 archivos · 62 funciones | 30-40% | ✓ | 🟡 GP-3/5 cubiertos |
| `inventario.py` | 5.944 | 93 | 2 archivos · 27 funciones | 30-35% | ✓ | 🟡 GP INV-1/4/8 |
| `marketing.py` | 4.940 | 43 | 2 archivos · 31 funciones | 15-20% | ✗ | 🟡 sin contrato |
| `auto_plan_jobs.py` | 3.253 | 0 (crons) | 0 | ~5% | ✗ | 🔴 47 jobs · sin tests |
| `aseguramiento.py` | 3.011 | 43 | 7 archivos · ~107 funciones | 40-50% | ✗ | 🟢 cubierto · sin contrato (GMP) |
| `calidad.py` | 2.131 | 33 | 3 archivos · 35 funciones | 30-35% | ✗ | 🟡 |
| `animus.py` | 2.038 | 31 | 2 archivos · 36 funciones | 35-45% | ✗ | 🟡 100% golden paths |

**Sin tests propios**: hub.py (1.179), gerencia.py (899), contabilidad.py (756), comunicacion.py (842), core.py (858), notif.py (325), despachos.py (230), mfa.py (parcial).

## Quick wins (≤1 día cada uno)
1. **Activar `pytest --cov`** en CI (ya está `pytest-cov==6.0.0` en deps, no se usa). Costo: 1h.
2. **Correr `test_backup_restoration.py` mensual** en GitHub Actions (`backup-test.yml` con cron `0 2 1 * *`). Costo: 30min.
3. **Uptime monitor externo** (UptimeRobot free → `/api/health`). Costo: 15min.
4. **24 CONTRACT_*.md faltantes** plantilla mínima por blueprint. Costo: 1 día.
5. **Staging environment Render** (clonar service, branch `staging` autodeploy). Costo: 30min.
6. **`LIMIT 200` default** en endpoints listado más usados. Costo: 1 día.
7. **Auditar los 42 `execute(f"...")` restantes** (mayoría whitelist de tabla pero documentar). Costo: 1 día.

## Trabajos medianos (1-2 semanas)
1. **Partir `admin.py` (22.570 LoC) en 4-5 sub-blueprints** por dominio: ops/reportes/mp_master/users/diagnostico. Solo mover, sin tocar lógica. 1.5 semanas.
2. **Migrar `templates_py/` (36 archivos · 0 `render_template`) a Jinja2 reales**, habilita CSP nonce. 1-2 semanas.
3. **Endpoint `/metrics` con `prometheus_client`** + Grafana Cloud free. 1 semana.
4. **Decorator `@safe_endpoint`** para reemplazar 1.290 `except Exception`. 1 semana.
5. **Subir cobertura golden paths a 50/50 verdes**. 1 semana.

## Trabajos grandes que bloquean el salto SaaS+BRD
1. **Multi-tenancy desde cero** — `tenant_id` en ~170 tablas, 1.028 fetchall calls, sesión, hooks de auth/rate_limit/audit, backfill datos históricos, migración SQLite→Postgres. **6-10 semanas FT**.
2. **Batch Record FDA 21 CFR Part 11 / INVIMA BPM** — firma electrónica avanzada inexistente; `audit_log` mutable; `formula_items` UPDATE directo (no immutable history aunque exista `formulas_versiones`); sin URS/IQ/OQ/PQ; backup off-site (`BACKUP_OFFSITE_URL` mencionado pero no configurado, `index.py:641`). **8-16 semanas**.
3. **Refactor `auto_plan.py`** (10.853 LoC, 89 endpoints, 5-10% coverage) en `planificacion`/`cron_jobs_planta`/`ia_assistant` + cobertura a 60%. **3-4 semanas**.
4. **SQLite → Postgres con cero downtime** (600+ queries SQLite-specific: INSERT OR IGNORE/REPLACE, datetime('now'), PRAGMA). El plan de `SECURITY.md:118` (1-2 días) subestima. Multi-tenant lo exige. **3-5 semanas FT**.

## Inventario de números
- **LoC api/blueprints**: 89.616 (28 archivos, top 4 = 53.259 = 59%).
- **LoC api/templates_py**: 48.924 (36 archivos HTML inline en strings Python).
- **LoC api/ root files**: 10.776 (`index.py` 52KB, `database.py` 524KB, `auth.py` 18KB, `backup.py` 13KB).
- **LoC tests**: 30.618 (100 archivos, 1.318 funciones `test_*`).
- **Ratio test:código** (tests vs blueprints): **1:2.9**.
- **TODO/FIXME/HACK genuinos**: ~0 en blueprints (645 falsos positivos por "todos/todas" en español). Deuda no se trackea con `# TODO` → señal de **deuda invisible**.
- **Tablas SQL**: ~170 (176 `CREATE TABLE IF NOT EXISTS`).
- **Endpoints**: **883** (876 en blueprints + 7 en `index.py`).
- **Migraciones registradas**: **99** (versiones 1→104 con saltos, `database.py:224`).
- **Cron jobs internos**: **47** confirmados (24 `JOBS_SCHEDULE` + 23 `watcher_health_HH`; `auto_plan_jobs.py:565`).
- **Blueprints registrados**: 28 (`index.py:228-254`).
- **CONTRACT_*.md cobertura**: **3/27 = 11%**.
- **`except Exception`**: 1.290 en blueprints (1 cada ~70 LoC).
- **`fetchall()`**: 1.028 en blueprints.
- **Funciones top-level en `admin.py`**: 134.
- **`tenant_id|org_id|workspace_id`** en `api/`: **0 hits**.
- **`prometheus|/metrics`**: **0 hits**.
- **`render_template`**: **0 hits** (todo HTML inline).
- **`openapi|swagger`**: **0 hits**.
- **Tests por blueprint crítico**: inventario 2 · compras 4 · programacion 0 directos · aseguramiento 7 · admin 3 · animus 2 · marketing 2 · auto_plan 1 · **0 archivos**: hub, gerencia, contabilidad, despachos, comunicacion, notif, core, auto_plan_jobs.

## Riesgos top 5
1. **🔴 Single-tenant arquitectura** — bloqueante absoluto SaaS. (0 hits `tenant_id|org_id|workspace_id`).
2. **🔴 `admin.py` anti-patrón GMP** — 22.570 LoC + 134 endpoints + 196 fetchall + 298 except Exception en un archivo no se valida CSV INVIMA/FDA.
3. **🔴 Audit log mutable** — sin trigger SQLite write-once + admin con acceso shell = invalidante 21 CFR Part 11.
4. **🟡 Cron jobs internos en worker pool** — 47 jobs comparten Gunicorn workers, job lento bloquea HTTP, inaceptable multi-tenant.
5. **🟡 Sin staging y DR no probado** — push main→prod directo, `test_backup_restoration.py` no agendado en CI; RTO/RPO 4h/24h aspiracionales.

## Conclusión ejecutiva
EOS hoy es **base operativa sólida para 1 cliente regulado mediano** (HHA Group · 19 users · ÁNIMUS + Espagiria) con cinturón anti-regresión genuino (golden paths + reviewer + guardian + 3 subagentes) → 🟢 para ese caso.

Para **3-6 meses → SaaS multi-tenant + BRD digital regulado**: 🔴, **necesita 4-6 meses de refactor previo**.

- **Plan "evolución gradual"** (multi-tenant → BRD fase 2 → acreditación fase 3): 3 meses fundación + 4-6 meses BRD GMP.
- **Plan "rápido a primer cliente externo no-regulado"** (clon Animus-Lab no-INVIMA): factible en ~3 meses con compromisos (Postgres lift-and-shift, BRD pospuesto, admin.py monolito).
