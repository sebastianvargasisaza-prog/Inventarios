# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> _Última actualización del mapa: **2026-06-08** (36 blueprints, 232 golden paths, EBR/MyBatch activo). Si trabajas mucho y notas que algo aquí ya no coincide con el código, actualiza este archivo en el mismo commit._

## 🧠 CERO ERROR — leer SIEMPRE

El catálogo vivo de errores y reglas anti-bug se carga automáticamente desde aquí:

@.claude/CERO_ERROR.md

**Regla dura:** cuando encuentres o arregles un bug con un patrón nuevo, agrégalo a `.claude/CERO_ERROR.md` en el MISMO commit. Así el "cerebro cero-error" siempre conoce lo nuevo. Sebastián exige **cero error**.

## Idioma y usuario
- SIEMPRE responder en español
- Usuario: Sebastián Vargas, CEO HHA Group, MD MPH
- Construye el sistema él mismo, prefiere iteración rápida con patches pequeños
- Confirmar antes de hacer cambios destructivos (commits, deletes, force push)

## What this is

Internal SaaS for **ÁNIMUS Lab + Espagiria Laboratorio** (Colombian cosmetics/skincare manufacturer) — covers inventory (kardex), purchasing, production scheduling, quality (INVIMA-regulated), CRM, RRHH, and accounting. Single Flask monolith on SQLite, deployed on Render at `app.eossuite.com`. UI strings, comments, and most docs are in Spanish.

## Commands

```bash
# Local dev (auto-loads .env via python-dotenv if present)
python -m api.index          # Flask debug server
gunicorn api.index:app       # production-like

# Tests — single DB per session, no /var/data writes
pytest tests/ -v --tb=short
pytest tests/test_golden_paths.py -q                      # 232 protected user journeys (~100s)
pytest tests/test_golden_paths.py::<test_name> -xvs       # single test, full output
pytest -k "compras"                                       # by keyword

# Anti-regression gates (install once with `bash scripts/install_hooks.sh`)
bash scripts/guardian.sh --quick   # pre-push: golden paths only (~3s)
bash scripts/guardian.sh --full    # + smoke + 3fuentes + producciones (~30s)
python scripts/reviewer.py         # pre-commit: contract/style/danger checks
python scripts/reviewer.py --strict   # warnings become errors

# Smoke test against deployed app
python scripts/smoke_test.py https://app.eossuite.com

# Bypass (emergencies only — investigate hook failures, do not skip them)
git commit --no-verify
git push   --no-verify
```

CI: `.github/workflows/test.yml` runs the full pytest suite on push/PR to main with Python 3.12.7. It also compiles every `api/**/*.py` with `-W error::SyntaxWarning`.

## Architecture

### Flask monolith with one blueprint per domain
`api/index.py` boots the app, runs `init_db()` (which executes the idempotent `MIGRATIONS` list in `api/database.py`), starts background daemons (marketing metrics loop, auto-plan cron, multi-cron), and registers **36 blueprints** from `api/blueprints/`. Blueprint names map to business domains: `inventario`, `compras`, `programacion`, `aseguramiento` (quality/compliance), `brd` (Batch Record Digital / EBR — reemplazo de MyBatch, datos regulatorios más críticos), `animus`, `espagiria`, `comercial`, `maquila`, `rrhh`, `mfa`, etc. Each blueprint owns its tables, endpoints, and HTML view (rendered server-side from `api/templates_py/`).

**Navegar archivos gigantes (no leerlos enteros):** algunos archivos son enormes — `admin.py` (~27.700 líneas, 176 rutas), `dashboard_html.py` (~24.400), `programacion.py` (~18.800), `plan.py` (~18.700). Para `admin.py` usa la tabla de saltos **`api/blueprints/MAP_admin.md`** (carga bajo demanda, no en el arranque). En general: `grep -n '<ruta o función>'` para ubicar la línea, luego `Read` con `offset`/`limit` sobre esa zona. Nunca abras el archivo completo "para ver".

### Three documents govern any change to a critical blueprint
Before touching `inventario.py`, `compras.py`, `programacion.py`, or `brd.py` (EBR/MyBatch — regulado INVIMA/GMP), read in this order:
1. **`MEMORY.md`** — static domain rules that must never silently change (5% gerencia threshold, Calendar = single source of truth, kardex-only stock, 3 SOL sources, gramos-only display, etc.). Editing this file requires a `SESSION_LOG/YYYY-MM-DD-N.md` entry.
2. **`api/blueprints/CONTRACT_<module>.md`** — invariants per blueprint (tables it writes/reads, endpoint list, downstream consumers, post-mortems). When you add an endpoint or change an invariant, update the CONTRACT in the same commit.
3. **`tests/test_golden_paths.py`** — 232 E2E journeys that are the executable spec of those invariants. Never modify a golden path to make a failing change pass; the code adapts to the test.

### Stock = SUM(movimientos), always
The `movimientos` table is the canonical kardex. Compute stock with `_get_mp_stock(conn)` from `programacion.py` — never with a parallel `stock_actual_g` cache (caused drift in the past). Every `INSERT INTO movimientos` requires a real `lote`; the synthetic fallback `'AJUSTE-CICLICO-<id>'` is only allowed when the source row has no lote at all.

### Production planning has TWO layers · Fijo vs Sugerido
Sebastián 19-may-2026 (rediseño post-incidente): `produccion_programada` separa lo que el usuario **fijó** de lo que la IA **sugiere**. Esto es ley dura · violarla pierde el plan del usuario.

- **Fijo** — `origen IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')`. Lo que el usuario decidió (arrastró o editó en el calendario), pedidos B2B y backfills históricos. **NUNCA tocado por procesos automáticos.** Cualquier `UPDATE ... SET estado='cancelado'` o `DELETE` que opere sobre un conjunto de filas DEBE excluir explícitamente esos orígenes:
  `AND COALESCE(origen,'') NOT IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')`
- **Sugerido** — `origen IN ('eos_canonico', 'calendar', 'manual', 'auto_plan', 'sugerido')`. La IA, el plan canónico y Google Calendar lo producen. Los regeneradores (`regenerar_canonicos`, `generar_plan_perfecto`), la limpieza Calendar-first y `LIMPIAR_PRODUCCION_ZOMBIES` pueden cancelarlo.

**Promoción automática a Fijo**: `REPROGRAMAR_PRODUCCION_PROGRAMADA` y `EDITAR_KG_PRODUCCION` ponen `origen='eos_plan'` al UPDATE — tocar = fijar. Test que lo protege: `test_golden_plan_fijo_sobrevive_regenerar`.

**Google Calendar** sigue como entrada de sugerencias (ya no es la única fuente de verdad). `_sync_calendar_a_produccion_programada()` con `force_mirror=True` ya NO borra Fijo (fix 19-may). Background crons pasan `force_mirror=False`. Rows con `inicio_real_at` o `inventario_descontado_at` set tampoco se tocan.

**Botones peligrosos** ("Regenerar canónicos", "Generar plan perfecto") muestran confirmación honesta: cancelan solo las Sugeridas, lo Fijo NO se toca.

### Three sources of purchase requests (SOLs) that must not bleed into each other
`?fuente=` filters `/api/solicitudes-compra` and `/api/compras/solicitudes-agrupadas-por-proveedor`:
- `planta` → categoría in (Materia Prima, Empaque, Material de Empaque)
- `usuarios` → everything not planta and not influencer
- `influencers` → categoría in (Influencer/Marketing Digital, Cuenta de Cobro)

Catalina's UI tabs depend on these never overlapping. PATCHing a SOL item also writes through to `maestro_mps.proveedor / precio_referencia` and upserts `mp_lead_time_config` — that's INV-2 in `CONTRACT_compras.md`, covered by GP-3.

### Batch Record Digital (EBR) · reemplazo de MyBatch · `brd.py`
Datos regulatorios MÁS críticos del sistema (Part 11 / GMP INVIMA). Tres capas: **MBR** (Master Batch Record, procedimiento aprobado por QA) → **EBR** (ejecución de UN lote real) → **IPCs** (in-process controls con specs y bloqueo OOS) + cleaning log + pesajes (reconciliación teórico vs real) + PDF maestro auditable. Invariantes duras (todas con triggers de DB, ver `CONTRACT_brd.md`):
- **MBR aprobado es INMUTABLE** (mig 109) — para cambiar: `obsoletar` versión + crear `version+1`. IPC specs siguen el estado del MBR (mig 112).
- **EBR liberado/rechazado es INMUTABLE** (mig 111) — pasos, IPCs y pesajes asociados también.
- Toda operación crítica escribe `audit_log` + usa `e_signatures` (firma con identity snapshot).
- Se enciende por fases: `EBR_MODE` off → warn → strict. Si "no se ve funcional", primero verificar que NO está apagado (sin MBR aprobados) antes de buscar un bug.

### SQLite + WAL + multi-worker Gunicorn
`_configure_conn` in `api/database.py` sets `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON` on every connection. Connections are per-request (Flask `g`) and closed in `teardown_appcontext`. With 3 sync workers in production, `cron_locks` table (migration 81) prevents duplicate cron runs across workers. Migrations are an append-only list of `(version, description, sql)` tuples in `MIGRATIONS` — never edit a past entry; add new ones at the end. Use `safe_alter()` for idempotent DDL (it only swallows "duplicate column" / "already exists" errors and re-raises everything else).

### Auth, roles, and MFA
`api/config.py` defines role sets read from env vars (`PASS_<USER>` must be a `pbkdf2:` or `scrypt:` hash from `scripts/gen_password_hashes.py` — plaintext is rejected with a CRITICAL config warning at startup). Key sets: `ADMIN_USERS = {sebastian, alejandro}` (override gerencia, hard delete, reset password); `COMPRAS_USERS` (everyone with login); plus per-domain access lists (`COMPRAS_ACCESS`, `CALIDAD_USERS`, `PLANTA_USERS`, etc.). MFA (TOTP via pyotp) is enforced for admins.

### Anti-regression sandwich
- **pre-commit** runs `scripts/reviewer.py` → flags missing CONTRACT updates, missing tests for new endpoints, edits to high-risk functions (`conteo_ajustar`, `_sync_calendar_a_produccion_programada`, `update_sol_items`, `limpiar_duplicados_producciones`), and dangerous patterns (synthetic lote defaults, restrictive `WHERE origen='calendar'` filters, f-string SQL).
- **pre-push** runs `scripts/guardian.sh --quick` → 232 golden paths, ~100s. If red, push is blocked.
- Three subagents in `.claude/agents/` (`guardian`, `reviewer`, `scribe`) automate the same gates inside Claude Code sessions. After landing changes, invoke `scribe` to update CONTRACT/MEMORY/SESSION_LOG.

## Conventions specific to this codebase

- **All MP quantities display in grams** with thousands separators. Never show kg in primary UI (Alejandro's directive). The `produccion_programada.cantidad_kg` column is internal — not for display.
- **Spanish for user-facing strings**, code identifiers, error messages, and most code comments. Don't translate.
- **MP stock for planning uses Shopify `Available`, not `On hand`** — `Committed` is already sold.
- **A fabricated lot takes ~7 days** to be Available in Shopify; add the production pipeline to effective stock when planning.
- **Mayerlin is fixed in dispensación** — operario assignments enforce this with DB triggers (migration 82). When adding planta features, verify `fija_en_dispensacion=1` is honored, or `trg_pp_fija_*` will block the INSERT.
- **`audit_log` is mandatory** on any operation that mutates inventory, SOLs, OCs, regulated quality records, **o `produccion_programada`**. Reviewer flags missing audits. Una cancelación/borrado de `produccion_programada` que no auditó es la que hizo desaparecer la programación del 19-may sin dejar rastro.
- **SQL string literals usan `''`, no `""`**. En PostgreSQL `""` es identificador vacío (inválido) — `COALESCE(col,"")` falla silenciosamente y la vista queda vacía. `pg_compat.translate_placeholders` ahora reescribe `""` → `''` fuera de literales, pero escribilo bien desde el principio. Tests en `test_pg_compat.py` protegen el comportamiento.
- Use the **`safe_alter`** helper for migrations; never wrap DDL in bare `try/except: pass` (silences typos).

## Operational references

- **`RUNBOOK.md`** — deploy, rollback, env vars, diagnostic endpoints, common errors.
- **`GOLDEN_PATHS_INVENTORY.md`** — coverage matrix (50 GPs across 10 modules).
- **`SECURITY.md`** — secrets handling, MFA, password policy.
- **`SESSION_LOG/`** — chronological log of AI-assisted sessions; new entries follow the template in `scribe.md`.
- **`tests/conftest.py`** — fixtures (`client`, `logged_client`, `admin_client`); every test runs against a per-session temp DB seeded with all `PASS_<USER>` env vars set to a known PBKDF2 hash for `TestPass123`.

## Files and directories to ignore

- `inventario.db`, `*.db`, `*.db-wal`, `*.db-shm` — local databases (gitignored, sometimes appear in working tree).
- `node_modules/`, `__pycache__/`, `.pytest_cache/`, `archive/`, `BROCHURE_*.docx`, `DOCUMENTO_*.docx`, `ROADMAP_*.docx` — not part of the runtime app.
- Top-level `auditoria_*.py`, `cadencias_*.py`, `extract_*.py`, `verificar_*.py`, `lotes_realistas.py`, `tabla_maestra.py`, `bf_y_plan.py`, `plan_*.py`, `sah_completo_v3.py` — one-off analysis scripts, not imported by the app.
