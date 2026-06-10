# 🧠 CERO ERROR · catálogo vivo de errores y reglas anti-bug

> **Este archivo se carga AUTOMÁTICAMENTE en cada sesión** (vía `@import` desde `CLAUDE.md`).
> Es el "cerebro cero-error" de EOS. Sebastián exige **CERO ERROR**.
> **Cuando encuentres o arregles un bug con un patrón nuevo, AGRÉGALO aquí en el mismo commit.**
> Mantenlo denso y accionable (checklist, no narrativa). La historia detallada vive en `SESSION_LOG/`.

Última actualización: **2026-06-08**

---

## ⭐ Las 5 reglas que más errores evitan (LEE PRIMERO)

1. **VERIFICAR contra código real antes de aplicar cualquier fix.** Los hallazgos de agentes/memoria alucinan (~50%): inventan funciones, reportan bugs ya arreglados, confunden conceptos. NUNCA apliques un hallazgo sin leer el código que cita y confirmar que el bug es real. La memoria es punto-en-el-tiempo: verifica file:line antes de afirmar.
2. **Suite golden ANTES de cada push.** `pytest tests/test_golden_paths.py -q` debe dar verde (232 al 8-jun-2026). El guardian pre-push la corre; si es roja, el push se bloquea. No usar `--no-verify` salvo autorización explícita.
3. **No tocar lo FIJO.** `produccion_programada.origen IN ('eos_plan','eos_b2b','eos_retroactivo')` es decisión deliberada del usuario. Ningún DELETE/UPDATE masivo lo toca: siempre `AND COALESCE(origen,'') NOT IN ('eos_plan','eos_b2b','eos_retroactivo')`.
4. **Stock = SUM(movimientos) canónico**, vía `_get_mp_stock(conn)`. El CASE cuenta Ajuste como entrada: `CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END`. Nunca `WHEN tipo='Entrada' THEN cantidad ELSE -cantidad` (resta los Ajuste). Excluir siempre `estado_lote IN ('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO')`.
5. **SQL/seguridad:** comillas simples `''` (en PG `""` = identificador vacío), placeholders `?` siempre (nunca f-string con input), `audit_log` obligatorio ANTES del commit en toda mutación regulada (INVIMA, inventario, SOL/OC, `produccion_programada`), datos bancarios solo admin+contadora (Habeas Data Ley 1581).

**Antes de cambiar algo crítico**, lee en orden: `CLAUDE.md` → `api/blueprints/CONTRACT_<modulo>.md` → `tests/test_golden_paths.py`.

**🧬 Fórmulas/maestro (audit corazón 9-jun):** la app tenía DOS poblaciones de fórmulas — 28 alineadas al Excel maestro con códigos canónicos (MP000xx · 23 coinciden EXACTO) y ~19 legacy/duplicadas con códigos fantasma (MPxxxSO01, resueltos por `mp_formula_bridge`). Reglas: (a) el Excel maestro (`FORMULAS_MAESTRO_v2_1`) trae el **código de MP en la columna CÓD. BATCH** → es la fuente de verdad para reconciliar (determinista, no agentes). (b) **Descontinuar fórmula = `activo=0`, NUNCA DELETE** (GMP/INVIMA conserva registros · reversible · no rompe golden de seed-state). (c) Antes de "agregar ingredientes faltantes" a una fórmula, **verificá si ya existe un duplicado COMPLETO** (caso BLUSH BALM: "Blush Balm" 67% incompleta vs "BLUSH BALM" 100% = Excel · el fix era dedup, no agregar). (d) Códigos fantasma que NO cruzan ni por bridge se corrigen con el Excel, **no se adivinan** (matching difuso = molécula equivocada · ej. N-acetil-cisteína→glucosamina).

---

## 🔑 META-LECCIONES (aplican a TODO el sistema)

- **M1 · UN SOLO resolver canónico por entidad.** Si existe un resolver con tiers (id → nombre exacto → nombre normalizado → alias → bridge), TODO lookup de esa entidad usa ESE helper o replica TODOS los tiers. Busca el helper canónico antes de escribir un lookup nuevo (`_get_mp_stock`, `_lookup_stock_5tier`, `_resolver_material_bodega`, `_pendiente_en_compras_g`, `stock_mp_disponible`, `_mee_stock_real`). **NUNCA un `SELECT ... FROM movimientos WHERE material_id IN (...)` con el código CRUDO de fórmula** (sin bridge) → los códigos fantasma (`MPxxxSO01`, 116 de ellos en prod) dan 0g = déficit falso/sobre-compra. **La cadena planear→solicitar→recibir usa UN solo código canónico (el de bodega resuelto)**: colapsá la demanda al código de bodega ANTES de calcular déficit y escribí la SOL con ese código (si no, el pendiente no cruza → SOLs duplicadas). Cazado 9-jun en `generar_plan` (auto_plan.py), `_seleccionar_variante_optima` y `_check_mp_para_pedido_b2b` (plan.py). ⚠ El bridge `mp_formula_bridge` puede estar MAL: 24 destinos no existen en maestro (fantasma→fantasma) y 2 con INCI equivocado (Ác. Ferúlico→Etil ascórbico, Betaína→Betaglucano) — corregir con Excel maestro, NO adivinar.
- **M2 · Normalización IDÉNTICA en clave y lookup.** La función que normaliza la CLAVE de un dict debe ser la MISMA en el `.get()`. (Bug: `_norm_prod` colapsa dobles espacios pero el lookup usaba `.upper().strip()` → caían a 0.) **Aplica también a lookups SQL por nombre de producto:** `_generar_mbr_desde_formula` (brd.py) buscaba la fórmula con `WHERE producto_nombre=?` EXACTO → el registro de envasado dice 'Suero Exfoliante Nova PHA' pero la fórmula está 'SUERO EXFOLIANTE NOVA PHA' = **SIN_FORMULA** (no genera el MBR). Fix 9-jun: `WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))` en headers+items. Regla: cualquier match por nombre de producto entre tablas distintas va con `UPPER(TRIM(...))` a ambos lados.
- **M3 · UNA sola ruta canónica de mutación; los demás delegan.** Iniciar/terminar/completar/cancelar producción y descontar MP/MEE tienen UN punto canónico (`prog_completar_evento`, `prog_iniciar_produccion`). Botones, Kanban y acciones-rápidas DELEGAN, nunca reimplementan parcial.
- **M4 · NUNCA tragar excepciones en mutaciones.** Prohibido `try/except: pass` en INSERT/UPDATE. El `except` hace rollback + log + devuelve la causa REAL en JSON. Un INSERT "que no puede fallar" se verifica (rowcount / SELECT después).
- **M5 · El número MOSTRADO = el número que DECIDE.** Display y lógica de alerta/color/orden usan la MISMA métrica. (Bug: "Alcanza" mostraba días físicos pero la urgencia usaba días con pipeline → agotado salía verde.)
- **M6 · FÍSICO vs EN-CAMINO, separados.** Alertas de quiebre usan stock físico real; pipeline/producción programada se muestra aparte. Stock 0 = CRÍTICO aunque haya lote programado. Si la venta sube y el lote llega tarde → alerta ADELANTAR.
- **M7 · TOTAL vs PORCIÓN relevante, explícito.** Antes de sumar pregunta: ¿esto es para Animus solo, para un cliente, o total? (La sugerencia de próxima producción usa la porción Animus; la demanda de MP usa el lote completo.)
- **M8 · Datos externos agregados: SCOPEAR, no sumar ciego.** Al leer Shopify/multi-location/multi-bodega, filtra a la entidad correcta (solo ÁNIMUS LAB); si no podés, MAX o la dominante, NUNCA la SUMA (una location fantasma negativa daba -235).
- **M9 · Snapshot vs VIVO.** Una vista "fuente de la verdad" no sirve snapshots viejos en silencio. Auto-refresh si stale (>10min), lock-guarded, y mostrar la antigüedad. Si el usuario dice "debe ser en vivo", es porque el snapshot lo engaña.

---

## 🟥 LA causa #1 de reprocesos: drift SQLite ↔ PostgreSQL

Tests corren en **SQLite** (local, pasan ✅) pero producción es **PostgreSQL**. Lo que SQLite no ve y rompe en PG:

- **Columnas de migraciones no aplicadas** → 500 (ej. `solicitudes_compra.influencer_id`). El tracker puede MENTIR (ALTER falló en silencio pero quedó marcado aplicado). Verifica columnas REALES vía `information_schema`, no el tracker.
- **`date('now','-5 hours')` / `datetime('now',...)` en DML.** EOS tiene capa de compat en `api/pg_functions.sql` (define `date()`, `datetime()`, `julianday()`, `instr()`, `printf()`, `group_concat()`) → multi-arg `date`/`julianday` SÍ funcionan; NO los marques como bug sin revisar ese archivo. PERO en DML (INSERT/UPDATE) usa **fecha calculada en Python como parámetro**, no `date('now')`.
- **`""` vs `''`** (identificador vacío en PG), **alias del SELECT en HAVING** (no permitido; en ORDER BY sí), **`json_each()`** (SQLite-only, no está en pg_functions → parsea en Python).
- **Un INSERT que falla aborta TODA la transacción en PG** → aísla lo no-crítico con SAVEPOINT.
- **Columna del SELECT que no está en GROUP BY ni agregada** → error duro en PG (`must appear in the GROUP BY clause`); SQLite elige un valor arbitrario y "funciona". Toda columna no-agrupada va en el GROUP BY o dentro de un agregado (`MIN/MAX(...)`). (Bug 8-jun: ranking proveedores, alertas-vivas, calidad-equipos, equipos-venc cron, agente reorden — varios 500 en prod.)
- **Alias del SELECT en HAVING**: PG no lo acepta (en ORDER BY sí). El adaptador (`pg_compat.rewrite_having_alias`) lo expande automáticamente — PERO no escribas en el HAVING una **columna calificada** (`m.tipo`) cuyo nombre coincida con un alias del SELECT (`... AS tipo`): chocaban y se manglaba a `m.(COALESCE(...))` → "syntax error at or near (" (arreglado 8-jun con lookbehind `(?<!\.)`). Regla práctica: en HAVING repite la expresión agregada completa, no el alias.
- **`ON CONFLICT(...) DO UPDATE SET col = col + 1` (col sin calificar) → "column reference is ambiguous" en PG** (choca con `excluded.col`). SQLite lo acepta. Califica con el nombre de tabla: `col = <tabla>.col + 1`. ⚠ Esto tenía el **rate-limit de login DESACTIVADO en prod** (el INSERT fallaba y un `except:pass` lo tragaba → brute-force sin tope) + contadores de crons rotos. Cazado 8-jun. Vale para cualquier auto-incremento en upsert.
- **`CASE WHEN <param_int>` (usar 0/1 como booleano) → "argument of CASE/WHEN must be type boolean" en PG.** SQLite acepta 0/1. Usa `CASE WHEN ? <> 0 THEN ...` (o pasa un bool). (Bug 8-jun: recoleccion de recalls daba 500 en PG.)
- **`char(N)` es SQLite-only; PG usa `chr(N)`** (en PG `char` es un TIPO). No mezclar — pon el carácter en el parámetro (`nueva + "\n"`) o evita la función. (Bug 8-jun: notas_avance quedaban vacías en PG.)
- **Alias IMPLÍCITO en HAVING** (`SUM(...) stk ... HAVING stk`): el reescritor del adaptador solo expande alias con `AS` → un alias implícito en HAVING da "column stk does not exist" en PG. Usa `AS stk` (o repite la expresión). (Bug 8-jun: stock retenido salía vacío.)
- **Query con error dentro de `try/except` NO recupera la transacción en PG.** Cuando una query falla, PG aborta TODA la transacción; atrapar la excepción en Python no la sana y las queries siguientes del mismo request fallan con "transaction aborted" → 500 en cascada (caso alertas-vivas: una query secundaria envuelta en `except:pass` reventaba el endpoint entero). Arregla la query, o aísla con SAVEPOINT.
- **Tipo de columna que no coincide con lo que el código inserta** → 500 en PG, tolerado en SQLite (tipado dinámico). Ej: columna `INTEGER` que recibe un código string → `invalid input syntax for type integer`. Verifica que el tipo del `CREATE TABLE` coincide con el valor real (los IDs de cliente B2B son TEXT). (Bug vivo 8-jun: portal RFQ → 500.)
- **La suite SOLO atrapa esto si corre en modo PG.** Tests en SQLite pasan con bugs PG escondidos. Gate montado: el CI corre el job **`test-postgres`** (PG real) en cada push/PR, y local hay **`bash scripts/guardian.sh --pg`** (contra pgdev). Si tocas el esquema, regenera `api/pg_schema.sql` (`dump_sqlite_schema.py` → `translate_schema_to_pg.py` → copiar a `api/`), o el harness PG falla en el setup (eso mismo te avisa del drift).

**Defensas:** (a) `_insert_dyn`/`_cols_tabla` (patrón en marketing.py) → INSERT por columnas existentes, nunca 500 por columna faltante. (b) Columnas que el código ESCRIBE van en `_SCHEMA_CRITICO` (admin.py) + correr `/admin/schema-doctor` tras deploy. (c) Nada destructivo sin preview → confirmación → backup → reversible (audit_log guarda valor previo); matching difuso de un click jamás (el auto-corregir glucosamina→cisteína se revirtió por audit_log; score<90 ⇒ solo sugerencia).

**Regla por cada cambio que toca BD:** ¿`date('now')` en DML? → param Python. ¿INSERT con columnas nuevas? → `_insert_dyn` o agregar a `_SCHEMA_CRITICO` + Doctor. ¿Masivo/destructivo? → preview+backup+reversible. Tras deploy → schema-doctor + smoke del endpoint tocado.

---

## ✅ Auto-check antes de cada Edit/Write (mis propios errores recurrentes)

- [ ] **Leí el archivo antes de editar** (el harness exige Read antes de Edit).
- [ ] **Verifiqué el schema de la tabla** (`grep "CREATE TABLE.*<tabla>" api/database.py` o `pg_schema.sql`) antes de SELECT/UPDATE con columna desconocida. Confirma `producto` vs `producto_nombre`, `precio_kg` vs `precio_unitario`, `lead_time_dias` (no `dias_lead_time_promedio`).
- [ ] **Query con JOIN → califico TODA columna** en WHERE/ORDER BY con alias (`estado` suele estar en >1 tabla → `ambiguous column`).
- [ ] **Helper nuevo:** `grep -nE "^def <nombre>|^function <nombre>"` antes de declarar (evitar duplicados como `_esc()`, `refreshNow()`). Si existe, reusar.
- [ ] **No insertar `def` helper entre `@bp.route` y su `def`** (roba el decorator). Helpers privados arriba o DESPUÉS del endpoint.
- [ ] **Strings JS dentro de template Python** (`'''<script>...</script>'''`): escapar `\n` como `\\n` (si no, el `<script>` entero rompe → "Cargando…" eterno). Verificar con `ast`, no con node sobre el fuente.
- [ ] **No concatenar `'$' + fmt(...)`** — `fmt()` ya prefija `$` (daría `$$1.234`). Verifica el return de cualquier helper antes de usarlo.
- [ ] **Renombré variable → `grep` nombre nuevo Y viejo**, todos los usos actualizados. Si no hace falta renombrar, no renombres.
- [ ] **2 loops consecutivos sobre listas relacionadas:** en el loop 2 usa la variable del item ACTUAL (`p["producto_nombre"]`), NO la del loop anterior (Python no crea scope nuevo en `for` → queda el último valor).
- [ ] **Comparar strings de tablas distintas con `==`:** normalizar `.strip().lower()` en AMBOS lados (joins implícitos en Python: "Suero AH" vs "SUERO AH").
- [ ] **Campo de estado → whitelist explícita** (`if estado_nuevo not in _ESTADOS_VALIDOS: return 400`), no aceptar cualquier string.
- [ ] **UPDATE bulk → `WHERE id=?` o llave única** sin duplicados (no `WHERE numero_oc+codigo_mp` si 2 items mismo MP).
- [ ] **Race condition (3 workers Gunicorn):** UPDATE de stock/estado en CAS (`UPDATE ... WHERE ... AND estado=?` + check `rowcount==1`) o `BEGIN IMMEDIATE`. `MAX(0, x-?)` ESCONDE underflow, no lo arregla.
- [ ] **Helper para "evitar duplicar X" → aplicarlo en TODOS los canales** que generan X (grep), no solo uno. Idempotencia en creación: button-disable + re-check + dedup case-insensitive incluyendo todos los estados activos.
- [ ] **Guards de `produccion_programada`:** chequear `estado` Y `inicio_real_at` Y `inventario_descontado_at` Y `origen` (Fijo) antes de cancelar/borrar/sobrescribir. La colisión/dedup del cron usa la MISMA clave y filtro que el INSERT.
- [ ] **`audit_log` ANTES del `conn.commit()`** (si va después, nunca persiste con el cursor del caller).
- [ ] **Atajo que obsoleta/regenera un registro regulado** (MBR/EBR/lote) → `audit_log` por cada cambio, igual que el endpoint canónico. Caso 9-jun: `mbr/preparar-aprobado?regenerar` obsoletaba MBRs (UPDATE estado='obsoleto') **sin auditar** mientras el `obsoletar_mbr` propio sí audita. SELECT los ids antes del UPDATE → audit_log cada uno → luego el commit final.
- [ ] **Feature nueva → test golden que la cubra ANTES de declararla lista.** Suite verde ≠ correctness, solo no-regresión de lo ya cubierto. Bug crítico → test que lo reproduzca.
- [ ] **Cambios globales** (cortex.css, before/after_request) se prueban con MUCHO cuidado: una animación CSS puede tapar la pantalla y bloquear clicks (caso real 28-may, 7.6s de bloqueo).
- [ ] **Comentario al modificar bloque:** `# FIX · YYYY-MM-DD · descripción · ref bug/auditoría`.

---

## 🚢 Push / deploy

- **Commit y push son pasos independientes.** El DNS de Sebastián falla intermitente. Tras cada commit verifica con `git ls-remote origin main` antes de push, y `git log origin/main` después. Render despliega auto al push a `main`; migraciones se aplican al boot (`api/index.py`). Verificar deploy: `curl app.eossuite.com/api/health`.

---

## 🔒 Postura de seguridad (NO re-litigar)

- **Auth = capa de aplicación** (sesiones Flask + roles en `config.py`/`auth.py`). EOS conecta a PG con UN solo rol (dueño, vía `DATABASE_URL`).
- **NO activar PostgreSQL RLS** (decisión Sebastián 8-jun): con rol dueño se ignora (no-op) y con `FORCE` sin políticas da DENY total → **caída de producción**. RLS solo aplicaría con rol no-dueño + contexto por request + políticas por tabla (re-arquitectura). No es el modelo de EOS.
- **CORS/Origin ya enforced**: `csrf_origin_check` (auth.py) → 403 si Origin/Referer ≠ host en métodos que mutan. No hay `Access-Control-Allow-Origin` permisivo.
- **Security headers** en `add_security_headers` (auth.py): HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP, COOP/CORP, Permissions-Policy. Datos bancarios solo admin+contadora (Habeas Data Ley 1581).

## 🧪 Aislamiento de tests en PG (NO perseguir)

La suite completa (1720) en una sola sesión PG comparte la BD. `db_clean` resetea
tablas volátiles + transaccionales (solicitudes/OCs/audit_zero_error). Quedan **2
falsos-positivos de contaminación SOLO en la corrida full** (pasan en aislamiento
y en el gate): `planificacion::solicitar_bulk_sin_deficits_ok` y
`producciones_faltantes::test_atrasada`. Dependen de stock/producción
(`movimientos`/`produccion_programada`). **NO resetear `movimientos`** (es el stock
seedeado · zerearlo rompe cientos de tests). El gate CI corre golden (verde), no la
full-suite, así que no afecta nada. No vale la pena perseguirlos.

**⏰ Golden date-frágiles (arreglar, sí afectan el gate):** un golden con `fecha_programada`
HARDCODED se rompe SOLO cuando rueda el calendario. Casos 9-jun: `necesidades.lotes_pendientes`
filtra `fecha >= hoy-7d` (plan.py:3910) → fecha fija `2026-06-01` salió del window y dio
`lotes_pendientes_n=0`; y la regla "lote grande = 1/día" (same-day, plan.py:5009) → un golden con
fecha relativa que cae en la fecha fija de OTRO golden (hoy+7) lo ocupa → 422. Fix: usar **fecha
relativa a hoy** en el input/assert, y que el test **limpie su fecha objetivo** antes de programar
(auto-contención). No tocar el código (las reglas son correctas).

## 🔁 Cómo mantener este archivo (para que "conozca todo lo nuevo")

Al cerrar una sesión donde se encontró/arregló un bug con patrón no listado aquí:
1. Agrega una línea al checklist o meta-lección correspondiente (densa, una idea).
2. Actualiza la fecha "Última actualización".
3. Inclúyelo en el MISMO commit del fix. El agente `scribe` también lo hace al actualizar CONTRACT/SESSION_LOG.
