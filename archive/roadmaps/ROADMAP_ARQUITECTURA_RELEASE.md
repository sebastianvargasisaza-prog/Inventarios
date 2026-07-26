# Roadmap · Arquitectura, Mantenibilidad y Release → "100%"

> Campaña de incrementos seguros. **Regla de oro:** cada paso se mergea verde
> (golden 232 + JS + reviewer) y es reversible. NADA de big-bang rewrite en un
> sistema regulado con usuarios reales. La red de seguridad va PRIMERO; recién
> con ella encendida tocamos los archivos grandes.
>
> Estado por paso: ⬜ pendiente · 🔄 en curso · ✅ hecho

## Diagnóstico base (8-jun-2026)
- ~234k LOC Python · 36 blueprints · 233 migraciones · 1.688 tests (232 golden).
- Dolores: `admin.py` 27k líneas · `dashboard_html.py` 24k (HTML+JS en strings de
  Python) · `programacion.py` 18k · CI corre SQLite pero prod es PG (drift = causa
  #1 de reprocesos) · sin staging · Sentry apagado · push directo a main.

---

## TRACK A · Release & Ops (la RED DE SEGURIDAD · va primero)

### A1 ⬜ Paridad PG en CI
`conftest` ya corre la suite contra PG (`EOS_DB_BACKEND=postgres`). Agregar job
con servicio `postgres:16` que corra los golden contra PG. **Mata la causa #1 de
reprocesos.** Introduce de paso el flujo por PR (Track A3).

### A2 ⬜ Encender observabilidad
`sentry_sdk` ya está integrado en `index.py` · falta `SENTRY_DSN` en Render +
confirmar que captura. Dejar de volar a ciegas en prod.

### A3 ⬜ Disciplina de PR + staging
- Branch `staging` → servicio Render `inventarios-staging` (réplica, BD aparte).
- Cambios de riesgo entran por PR (status check `test` obligatorio · ya existe
  la regla, hoy se bypassa). Hotfixes triviales pueden seguir directos.

### A4 ⬜ Schema-doctor en CI
Correr `/admin/schema-doctor` (o su lógica) como check que falle si el esquema
PG diverge de las migraciones. Cierra el drift de raíz.

### A5 ⬜ Endurecer el guardián de despliegue
Pre-push ya corre golden. Agregar: smoke contra staging post-deploy +
rollback de 1 comando documentado en RUNBOOK.

---

## TRACK B · Arquitectura & Mantenibilidad (incremental · tras A1-A2)

### B1 ⬜ Sacar HTML/JS de los strings de Python (el de mayor impacto)
`dashboard_html.py` (24k) y los templates inline son donde se esconde una FAMILIA
ENTERA de bugs (la clase `\n` cruda, `json`/`_json`). Mover a `.html` (Jinja) +
`.js` reales **elimina esa clase de bug** y hace el frontend lintable/revisable.
- **Piloto:** migrar UNA página, probar verde, fijar el patrón.
- Luego rodar página por página. Cada una = 1 PR verde.

### B2 ⬜ Partir los mega-archivos
`admin.py` 27k · `programacion.py` 18k · `plan.py` 18k → módulos cohesivos por
sub-dominio. Solo DESPUÉS de A1 (PG-CI) y con los golden cubriendo. Mover sin
cambiar comportamiento; el test net es el seguro.

### B3 ⬜ Linter + formato + tipos incrementales
`ruff` + `black` en pre-commit. Type hints en las funciones críticas (resolver
de stock, kardex, liberación). Atrapa errores antes del runtime.

### B4 ⬜ Matar el doble-backend en dev
Si prod ya es PG, hacer PG el default también en dev/CI (SQLite solo opcional).
Borra el drift en origen.

---

## Secuencia recomendada
1. **A1 (PG-CI)** ← empezamos aquí. Barato, alto impacto, protege todo lo demás.
2. A2 (Sentry) · A3 (staging+PR) — completar la red.
3. B1 piloto (sacar 1 template) — probar el patrón de arquitectura.
4. Rodar B1 + arrancar B2 con la red ya puesta.

## Bitácora
- 8-jun: roadmap creado. Próximo: A1.
