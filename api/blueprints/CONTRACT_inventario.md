# CONTRACT · `inventario.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**
> Cualquier cambio que rompa estos contratos requiere migración explícita.

Última revisión: 2026-05-07

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `movimientos` | INSERT | Recepción MP, ajuste conteo, eliminar lote, transferir |
| `movimientos` | UPDATE | Cambio de proveedor de un lote, cambio de estado_lote |
| `conteos_fisicos` | INSERT/UPDATE | Iniciar conteo, cerrar conteo |
| `conteo_items` | INSERT OR REPLACE | Guardar conteo, aplicar ajuste |
| `maestro_mps` | INSERT/UPDATE | Crear MP nueva (admin), update flags |
| `lotes_realistas` | (deprecated, no usar) | — |
| `audit_log` | INSERT | Cada operación crítica |

## Tablas que LEE

- `maestro_mps`, `movimientos`, `conteos_fisicos`, `conteo_items`,
  `formula_headers`, `formula_items`, `precio_historico_mp`.

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · Stock = SUMA(movimientos)
- Toda función que calcule stock debe usar `_get_mp_stock(conn)` o equivalente.
- NUNCA cachear stock fuera del kardex.
- NUNCA crear tabla paralela "stock_actual_g" (probado: causa drift).

### INV-2 · Movimientos requieren material_id Y lote
- `material_id` no puede ser NULL/empty.
- `lote` puede ser empty SOLO para movimientos legacy o material agregado.
- `tipo` ∈ {'Entrada', 'Salida'} case-sensitive en INSERT (queries hacen UPPER).

### INV-3 · Ajuste conteo usa lote REAL
- `/api/conteo/<id>/ajustar` debe insertar movimiento con `lote = it['lote']`.
- Solo si `it['lote']` está vacío → fallback `'AJUSTE-<conteo_id>'`.
- **GOLDEN PATH 1** lo verifica: `test_golden_conteo_ciclico_ajuste_afecta_lote_real`.

### INV-4 · Threshold gerencia 5%
- En `/guardar`: `requiere_gerencia = 1 if abs(diff/stock_sis) > 0.05 else 0`.
- En `/ajustar`: si `requiere_gerencia` y not `aprobado_gerencia`, solo
  `ADMIN_USERS` pueden override (auto-set `aprobado_gerencia=1`).
- Norma: BDG-PRO-002.

### INV-5 · audit_log siempre
- Cada operación destructiva o de inventario INSERT en `audit_log` con:
  `usuario, accion, tabla, registro_id, detalle, ip, fecha`.
- Sin audit_log → NO se debe deployar.

### INV-6 · Producción NUNCA consume material vencido (INVIMA Res. 2214)
- El FEFO del descuento, `verificar-stock`/`simular_produccion` y los helpers de
  lote-de-pesaje excluyen lotes con `date(fecha_venc_Entrada) < date('now','-5 hours')`
  (mismo límite que el cron `job_marcar_vencidos`), aunque `estado_lote` aún sea
  VIGENTE porque el cron diario no corrió. `NULL`/'' = sin venc = usable.
- Las VISTAS de bodega (`/api/lotes`, retenido) siguen ancladas en `estado_lote`
  (fuente única que el cron alinea diario · no crear 2ª fuente de verdad).
- `consumo_manual` NO aplica este filtro (se usa para dar de baja vencidos). M25.

---

## Endpoints downstream que CONSUMEN sus tablas

| Endpoint externo | Lee | Si rompo `inventario.py`... |
|---|---|---|
| `programacion.py /producciones-faltantes` | `movimientos`, `maestro_mps` | ...Centro Programación muestra stock errado |
| `programacion.py /aplicar-plan` | `movimientos`, `mp_lead_time_config` | ...auto_plan propone compras erradas |
| `compras.py /solicitudes-agrupadas` | `solicitudes_compra_items` | ...Catalina ve datos mezclados |
| `auto_plan.py todos los crons` | `movimientos`, `maestro_mps` | ...IA hace decisiones con stock viejo |
| Bodega Materias Primas (UI) | `movimientos` por lote | ...stock por lote no refleja ajustes |

---

## Sprint Fórmulas PRO · 20-may-2026

Nuevas tablas (mig 147):
- `app_settings (clave, valor, descripcion, actualizado_at_utc, actualizado_por)` ·
  k-v genérico para overrides runtime. clave='formula_pin' permite admin
  cambiar PIN de fórmulas desde UI sin tocar env vars en Render.
- `formula_versiones (producto_nombre, version, items_json, motivo_cambio,
  creado_por)` · INVIMA compliance · cada edición de fórmula archiva la
  versión anterior antes de UPDATE.

Nuevos endpoints:
- `GET/POST /api/admin/formulas/pin` (admin) · ver origen del PIN sin
  revelar valor / setear nuevo PIN ≥4 chars · audit_log FORMULA_PIN_CAMBIADO.
- `POST /api/formulas/import-excel?dry_run=0|1` (admin) · acepta XLSX
  (openpyxl) o CSV/TSV auto-detect. Headers case-insensitive: producto,
  codigo_mp, porcentaje (obligatorios) + nombre_mp, unidad_base_g,
  descripcion (opcionales). Valida contra maestro_mps activo · rechaza
  fórmulas con MPs inexistentes. dry_run devuelve plan sin tocar BD.
  audit_log FORMULAS_IMPORT_EXCEL.
- `GET /api/formulas/export-excel` · descarga XLS HTML con 1 fila por
  ingrediente · round-trip con import.
- `POST /api/formulas/duplicar {producto_origen, producto_nuevo}` ·
  copia fórmula con nuevo nombre · 409 si destino ya existe ·
  audit_log FORMULA_DUPLICAR.
- `GET /api/formulas/<prod>/versiones` · historial JSON últimas 50.
- `GET /api/formulas/<prod>/uso` · count lotes + última prog + última
  terminada + kg totales producidos.

Invariante nueva:
- POST /api/formulas que EDITA existente DEBE archivar versión anterior
  en formula_versiones (INVIMA). body.motivo_cambio opcional pero
  recomendado · queda en motivo_cambio de la versión.

## Endpoints que expone

- `GET  /api/maestro-mps` · listado MPs
- `POST /api/maestro-mps` · crear MP (admin)
- `GET  /api/maestro-mps/export-lista-simple[?fmt=xlsx|csv]` · default XLSX
  nativo (Excel en español rompe CSV con coma · usar XLSX o `?fmt=csv` con
  `;`). 4 columnas: codigo · nombre comercial · nombre INCI · tipo · solo
  activas · NO expone precio / proveedor / stock (uso de planeación)
- `GET  /api/proveedores-unicos` · datalist autocomplete
- `GET  /api/lotes` · listado lotes MP con stock > 0 (paginación opcional
  via `?limit=N&offset=N`, `?solo_criticos=1` para vencidos/<30d).
  Excluye estados NO usables (cuarentena/rechazado/vencido/agotado/bloqueado · A1)
- `GET  /api/lotes/retenido` · lotes NO disponibles con saldo físico (RECHAZADO/
  VENCIDO/BLOQUEADO), netos por lote, umbral >0.01, UPPER-insensible. Read-only.
  Complementa `/api/lotes/cuarentena` (solo CUARENTENA/_EXTENDIDA) para que el
  material retenido siga TRAZABLE (INVIMA Res. 2214) y cuadre el conteo físico
- `GET  /api/lotes/<material_id>/<lote>/movimientos` · historial del lote
  específico server-side, ≤ 500 filas, acepta `_SIN_LOTE_` como marcador
  · Sebastián 20-may-2026 Sprint Bodega MP PRO (antes Historial bajaba
  todos los movimientos y filtraba en JS).
- `GET  /api/dashboard/insights` · widgets Dashboard PRO #2 (Planta AHORA,
  mes actual, stats extra) en una sola llamada
- `GET  /api/maestro-mps/duplicados-deteccion` · admin · detecta MPs con
  nombre_comercial/nombre_inci normalizados iguales pero codigo_mp distinto.
  Retorna grupos + stats por variante (stock, movs, lotes, fórmulas, sols)
- `POST /api/maestro-mps/unificar` · admin · unifica códigos duplicados en
  uno canónico. Body: `{canonico, codigos_a_unir, dry_run, token}`. dry_run
  default true (cuenta filas sin tocar). dry_run=false requiere token
  `UNIFICAR_MP_2026`. Transaccional: UPDATEa 13 tablas que referencian
  material_id/codigo_mp (movimientos, formula_items, solicitudes_compra_items,
  ordenes_compra_items, mp_lead_time_config, mp_formula_bridge,
  precios_mp_historico, conteo_items, conteo_ciclico_calendario,
  conteo_ciclico_config, ebr_pesajes, especificaciones_mp, alertas) y
  desactiva (activo=0) los codigos viejos. audit_log UNIFICAR_MP_DUPLICADOS.
- `GET  /api/proveedores-duplicados[?similitud=0.85]` · detecta proveedores
  duplicados. Capa 1: normalización (lowercase, sin tildes, sin sufijos
  jurídicos SAS/LTDA/SA/SL/CIA/INC/CORP/LLC/BV/GMBH/AG/CO/SRL/SAC/SPA, sin
  `. , ; : & - _ / \\`). Capa 2: Levenshtein ≥ threshold para typos. Carga
  desde 11 tablas que tienen proveedor (no solo movs+maestro). Retorna
  grupos con stats (refs_totales, usos, count_variantes).
- `GET  /api/mee/movimientos[?codigo&tipo&q&limit&offset&incluir_anulados]`
  · Sprint MEE PRO 20-may-2026 · historial paginado server-side con
  búsqueda full-text. Antes solo limit=50 sin offset ni q.
- `POST /api/mee/recalcular-stock` body `{codigo?: str}` · Sprint MEE
  PRO. Anti-drift de `maestro_mee.stock_actual` (cache) recalculando
  desde `SUM(movimientos_mee)`. Si codigo se pasa, solo ese. Si null,
  recalcula TODOS los activos (admin only). audit_log RECALCULAR_STOCK_MEE.
- `GET  /api/movimientos/recientes[?limit&offset&q&tipo&desde&hasta&solo_anulados]`
  · Sprint Movimientos PRO 20-may-2026 · paginado + filtros server-side.
  Antes el frontend bajaba todo /api/movimientos y filtraba en JS.
  Devuelve items[] con id + material_id + lote + cantidad + tipo +
  proveedor + numero_oc + numero_factura + operador + observaciones +
  estado_lote + flag anulado. Limit max 500.
- `POST /api/movimientos` ahora exige lote para tipo='Entrada' (sin
  lote rompe kardex y FEFO) · 400 con lote_obligatorio=true. Si vacío
  para Salida/Ajuste sigue permitiendo (puede ser conteo cíclico).
  Agregado audit_log REGISTRAR_MOVIMIENTO_MANUAL.
- `GET  /api/alertas/all` · endpoint consolidado Sprint Alertas PRO
  20-may-2026 · 6 categorías en una llamada (mps_sin_stock,
  mps_bajo_minimo, lotes_vencidos, lotes_proximos, mees_bajo_minimo,
  lotes_cuarentena) + stats + agrupado por proveedor. Filtra
  alertas_silenciadas activas.
- `POST /api/alertas/silenciar` · silencia alerta puntual con motivo
  (≥10) + expira_dias opcional. Tipos: mps_sin_stock, mps_bajo_minimo,
  lote_venc, lote_cuarentena, mee_bajo_minimo. audit_log SILENCIAR_ALERTA.
- `DELETE /api/alertas/silenciar/<id>` · re-activar (activo=0).
- `GET  /api/analisis-abc[?modo=&tipo_material=&subtipo=&excluir_cuarentena=]`
  · Pareto ABC refactor 20-may-2026. Agrupa por `material_id` (no
  por nombre · evita doble cuenta). Modos:
  - `valor` (default) = stock × precio_referencia (Pareto financiero)
  - `consumo_90d` / `consumo_180d` / `consumo_365d` = SUM salidas × precio
  - `stock_actual` = gramos en bodega (modo legacy)
  Filtros: `excluir_cuarentena=1`, `subtipo=Activo`, `tipo_material=MP|MEE`,
  `incluir_sin_movimientos=0` (en modos consumo excluye items sin salidas).
  Devuelve `items[]` con ranking + clasificacion (A/B/C/D) + counts +
  total_metric + metric_unit + valor_por_clase. Compat: `items_legacy[]`
  con shape viejo (material, cantidad, valor%, clasificacion).
- `GET  /api/recepcion/recientes[?limit=N&offset=N&q=X]` · listado entradas
  recientes server-side con paginación y búsqueda (LIKE escape para %_).
  JOIN con maestro_mps para INCI · incluye numero_oc + numero_factura.
  Sebastián 20-may-2026 Sprint Recepciones PRO #7+#13.
- `POST /api/recepcion/<mov_id>/anular` · admin · crea movimiento Salida
  inverso + audit_log ANULAR_RECEPCION_MP. Si la recepción venía de OC,
  descuenta `cantidad_recibida_g` de `ordenes_compra_items`.
  Sebastián 20-may-2026 fix #8. **Audit 13-jun (M31):** la Salida ESPEJA el
  `estado_lote` ORIGINAL (no `'ANULADO'`) → net-zero exacto en TODA vista
  (canónico y auditar-minimos); antes 'ANULADO' dejaba stock negativo en
  cuarentena o fantasma en VIGENTE. Guard `LOTE_YA_MOVIDO` (409): no anula si
  el stock RAW del lote < cantidad (lote ya consumido). Idempotencia +
  anti-doble-anulación concurrente vía **CAS** (UPDATE condicional sobre la
  Entrada con chequeo de rowcount); doble llamada o carrera entre workers →
  409 (`prev` ya-existe o `ANULACION_YA_RECLAMADA`). NO usar SELECT-luego-INSERT
  para idempotencia en multi-worker PG.
- `GET  /api/recepcion/<codigo_mp>/precio-historico` · últimos 10 precios
  para frontend (alerta delta).
- `POST /api/proveedores-unificar` · acepta `dry_run` (cuenta sin tocar) o
  apply real. Transaccional sobre 11 tablas:
  movimientos.proveedor, maestro_mps.proveedor, maestro_mee.proveedor,
  ordenes_compra.proveedor, solicitudes_compra.proveedor,
  solicitudes_compra_items.proveedor, solicitudes_compra_items.proveedor_sugerido,
  pagos_oc.proveedor, mp_lead_time_config.proveedor_principal,
  mee_lead_time_config.proveedor_default, precios_mp_historico.proveedor.
  audit_log UNIFICAR_PROVEEDORES. Sebastián 20-may-2026.
- `POST /api/movimientos` · INSERT recepción/salida
- `GET  /api/conteo/estanterias` · agrupación por estantería
- `GET  /api/conteo/materiales` · MPs en estantería
- `POST /api/conteo/iniciar` · crear conteos_fisicos row
- `POST /api/conteo/<id>/guardar` · INSERT items con diff calculado
- `POST /api/conteo/<id>/cerrar` · auto-aplica <5%, queda pendiente >=5%
- `POST /api/conteo/<id>/ajustar` · aplica ajuste manual (admin si gerencia)
- `GET  /api/conteo/alertas-gerencia` · pendientes >5%
- `GET  /api/conteo/historial` · listado de conteos pasados

---

## Cambios recientes que rompieron algo (post-mortems)

### 2026-05-07 · Ajuste sintético no afectaba lote real
- **Bug**: `/ajustar` insertaba con `lote='AJUSTE-XX'` (sintético).
- **Síntoma**: Bodega muestra stock viejo del lote original.
- **Fix**: usar `it['lote']` real. Fallback solo si vacío.
- **Test que cazaría**: `test_golden_conteo_ciclico_ajuste_afecta_lote_real`.

### 2026-05-21 · Auditoría TOTAL · 76 bugs cerrados

**Endpoints sin auth (CRÍTICO · expuestos públicamente):**
- `/api/stock` · `/api/lotes` · `/api/maestro-mps/<x>` ahora exigen `_require_session`
- `update_stock_minimo` exige COMPRAS/ADMIN + audit_log UPDATE_STOCK_MINIMO
- `anular_movimiento` bloquea bypass user='' (validación previa)
- `consumo_manual` rechaza stock negativo (422 STOCK_INSUFICIENTE)
  · flag `forzar_sobreconsumo` solo admin

**INVIMA mejoras:**
- `liberar_lote` acepta CUARENTENA_EXTENDIDA (no solo CUARENTENA)
- `liberar_cuarentena`: decision whitelist + estado actual validado · no revive RECHAZADO
- COA + lote_proveedor + ficha_seguridad en `movimientos` (mig 151)
- `mee_import_bulk` ahora `audit_log` IMPORT_BULK_MEE
- Alertas reabastecimiento excluyen CUARENTENA/RECHAZADO/VENCIDO

**Helpers nuevos:**
- `_mee_stock_real(c, codigo_mee)` · stock de UN envase · Fase 0 (19-jun) ALINEADO a
  `_get_mee_stock` (programacion): tipos case-insensitive + fallback a `stock_actual`
  SOLO si no hay movimientos. Sin callers hoy (se mantiene fiel para uso futuro).
- `_pendiente_en_compras_g` (import desde compras) · dedup cola SOLs+OCs

**Fase 0 · Normalización de envases (MEE) · mig 279 (19-jun):**
- `maestro_mee` gana `nombre_inci` (descripción canónica/atributo) + `material_referencia`
  (envase base del que deriva un serigrafiado · Fase 2). Activo/Inactivo vive en `maestro_mee.estado`.
- Resolver canónico de envases en programacion.py: `_norm_envase_name` (= `_norm_mp_name`),
  `_resolver_envase_bodega(c, codigo)` (id → puente `mee_aliases` con `codigo_mee` set).
- `_get_mee_stock` PASS-3: pliega el puente de duplicados → lookup por código duplicado
  o canónico devuelve el TOTAL canónico (paridad con `_get_mp_stock` · el kardex NO se toca).
- `/api/admin/maestro-envases-diff` (read-only · duplicados por nombre normalizado + stock) y
  `/api/admin/maestro-envases-aplicar` (fusionar→puente+estado Inactivo · deshacer · backfill-inci).
  NUNCA tocan `movimientos_mee` · reversibles por audit + acción `deshacer`. Página `/admin/maestro-envases`.

**Cron `auto_reparar_huerfanas` (4 AM):**
- Detecta `formula_items.material_id` sin movimientos asociados
- Auto-repara con MP correcto (nombre/INCI match · stock real)
- ORDER BY stock DESC, codigo_mp ASC determinístico
- audit_log REPARAR_HUERFANO_FORMULA con antes/después

**Cron `mee_drift_sync` (3 AM):**
- Detecta drift > 0.5g entre `maestro_mee.stock_actual` y SUM(movimientos_mee)
- Resincroniza cache automático · log top 10 drifts

### 2026-05-22 · Auditoría abastecimiento · 12 bugs cerrados

**_get_mp_stock corregido (programacion.py):**
- WHERE excluye `UPPER(estado_lote) IN ('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO')`
- CASE explícito: Entrada+Ajuste+Ajuste+ suman · Salida+Ajuste- restan
- Aplicado en pass 1, pass 2 y bridge tier

**Mismo fix replicado en 3 sitios:**
- `/api/stock` (inventario.py:3924)
- `/api/alertas-reabastecimiento` (inventario.py:3884)
- `/api/compras/prediccion-demanda` (compras.py:8506)

**Alertas reabastecimiento incluye dedup:**
- Cada item: `en_cola_g` + `deficit` neto + `cubierto_por_cola` flag
- Frontend puede mostrar badge informativo si en_cola > 0

**Migración 154:** `formula_items.incluye_merma INTEGER DEFAULT 0`
- Si =1, auto_plan NO re-aplica merma (cantidad_g_por_lote ya la incluye)

### 2026-05-29 · Auditoría ronda 2 · fixes inventario/calidad
- **FEFO de registro real** (`del_formula` líneas ~1970 y ~2829): el WHERE de
  selección de lotes ahora excluye también `VENCIDO` y `AGOTADO` (antes solo
  CUARENTENA/CUARENTENA_EXTENDIDA/RECHAZADO). Alinea con
  `inventario_helpers.ESTADOS_LOTE_NO_DISPONIBLES` y `_get_mp_stock`. Evita
  consumir MP vencida/agotada en producción (trazabilidad INVIMA).
- **DELETE `/api/formulas/<nombre>`**: ahora exige RBAC (ADMIN o CALIDAD, igual
  que `patch_codigo_pt`) y escribe `audit_log(accion='ELIMINAR_FORMULA')` con
  snapshot del nº de items. Antes cualquier logueado borraba fórmulas reguladas
  sin rastro. Devuelve 404 si la fórmula no existe.
- **`cc-review`**: el `firmante` ahora se toma de la sesión autenticada (`user`),
  no de `d.get('firmante')` del payload (era falsificable y se grababa así en
  audit_log).

### 2026-05-29 (b) · Firma electrónica Part 11 en disposición de lote MP
- **INV · liberación de lote de MP en cuarentena REQUIERE e-signature.** Los 3
  endpoints que disponen un lote (`POST /api/lotes/liberar`,
  `POST /api/lotes/cc-review`, `POST /api/lotes/cuarentena/<id>/liberar`) ahora
  exigen `signature_id` válido en `e_signatures` (helper `_validar_e_sign`),
  bound al `record_table='movimientos'`, `record_id=<mov_id>`, `signer_username`
  = sesión, y `meaning`:
  - APROBAR/Aprobado/estado APROBADO → `meaning='libera'`
  - RECHAZAR/Rechazado/estado RECHAZADO → `meaning='rechaza'`
  - CUARENTENA_EXTENDIDA → `meaning='aprueba'`
- Sin firma válida → **400** con `{requiere_firma:true, sign_meaning, record_id}`
  (no 401: el user está autenticado, falta firmar). RBAC (`_require_qc`) se
  evalúa ANTES, así que un no-QC sigue recibiendo 403.
- Flujo UI (dashboard_html / financiero_html): al recibir `requiere_firma`,
  `_firmarLoteEsign` pide password (+TOTP si MFA) → `/api/sign/challenge` →
  `/api/sign` → reintenta cc-review con `signature_id`.
- Cubierto por golden **GP-61** `test_golden_liberar_lote_mp_requiere_efirma`
  (sin firma→400, firma de otro lote→400 binding, firma correcta→200).
- Los 3 endpoints son el equivalente para MP del gate que `brd.py` ya tenía en
  EBR (producto terminado). Parte del reemplazo progresivo de MyBatch.

## 🗓️ Modo inventario · recepción directo a inventario (16-jun)

- **`database.recepcion_auto_vigente(conn)`** resuelve el interruptor: 1º
  `app_settings.clave='recepcion_auto_vigente'` (toggle por botón · sin Render),
  2º env `RECEPCION_AUTO_VIGENTE`. **Default OFF = INVIMA cuarentena-first.**
  `config.recepcion_auto_vigente_env()` es solo el fallback de env.
- Cuando está ON: recepción de OC (`compras.recibir_oc`) e ingreso manual
  (`/api/recepcion`) entran `estado_lote='VIGENTE'` en vez de `'CUARENTENA'`. El
  valor explícito del operario (`cuarentena` en el body) manda sobre el default.
- **`GET/POST /api/inventario/modo-inventario`** (POST = ADMIN) lee/define el
  toggle en `app_settings` (audit `SET_MODO_INVENTARIO`). UI: botón en la pestaña
  Cuarentena del dashboard.
- **`POST /api/lotes/cuarentena/liberar-inventario`** (ADMIN · solo si el modo está
  ON): mueve CUARENTENA/_EXTENDIDA → VIGENTE en bloque, SIN e-sign (excepción del
  día de inventario · audit `LIBERAR_CUARENTENA_INVENTARIO` por lote). Al apagar el
  modo, esta ruta responde 409 y vuelve la liberación formal con firma.
- ⚠ Cubierto por `tests/test_recepcion_auto_vigente.py`. El default OFF mantiene
  verdes los golden de recepción/cuarentena (no cambiar el default en código).

## 🧮 Descuento directo · consolidación por código de bodega (25-jul · auditoría)

**Invariante nuevo (INV-8):** `_handle_produccion_inner` y `simular_produccion`
CONSOLIDAN los ítems de fórmula por el código de BODEGA resuelto **antes** de mirar
stock. Antes se planificaba una entrada por FILA y cada fila hacía su propio SELECT
FEFO y su propio pre-check contra LOS MISMOS lotes: dos filas que apuntan al mismo
material (código repetido en `formula_items`, que no tiene UNIQUE, o dos códigos que
`_resolver_material_bodega` colapsa en uno) pasaban AMBAS viendo el stock completo y
descontaban el doble → **stock NEGATIVO por lote, en silencio** (el kardex afirmaba
que un lote entregó gramos que no tenía · trazabilidad falsa ante INVIMA).

Es el mismo dedup que el path programado (`_calcular_mp_consumo_produccion`) tiene
desde el 1-jun (P0-1); la ruta de Fabricación directa se había quedado sin él.

Corolario: el simulador ("Verificar stock") consolida igual, así que da el MISMO
veredicto que el descuento real (M5). Tests: `tests/test_descuento_dedup_codigo.py`.

## 🔐 Escribir una fórmula maestra exige rol (25-jul · auditoría)

**INV-13:** `POST /api/formulas` está gateado a `TECNICA_USERS | ADMIN_USERS`, el MISMO set
que la página `/tecnica`. Antes solo exigía sesión, así que cualquier usuario autenticado
(una operaria de dispensación, marketing, la contadora) podía reescribir una receta llamando
el endpoint a mano — verificado en la auditoría con una sesión de planta. Es dato regulado
INVIMA: define qué y cuánto se dispensa, y alimenta el descuento FEFO, la compra y el MBR.
Patrón M32: el gate de la PÁGINA y el de la MUTACIÓN son dos controles distintos.

## 🔄 La caché del dashboard se saltea en tests (25-jul · auditoría)

`GET /api/inventario` cachea 45 s por worker (PERF 9-jul). **Desde el 25-jul NO aplica si
`app.config['TESTING']` o si llega `?fresco=1`.** Con la caché activa, un test que leía el
baseline, sembraba datos y volvía a leer recibía la respuesta VIEJA: 3 KPIs de Planta (lotes
vencidos, críticos a 30 días, cuarentena) figuraban rotos con el endpoint sano.
**Regla: toda caché de endpoint debe poder saltearse, o los tests dejan de ser deterministas
y esconden bugs reales.**

## 🚪 `/api/mee` tiene UNA sola ruta de creación (25-jul)

`POST /api/mee` lo atiende **`inventario.mee_crear`** (gate `_require_planta_write`). Antes
`compras.handle_mee` también declaraba POST con un gate más estricto (`_require_compras_write`)
que **nunca corría**, porque Werkzeug resuelve la primera regla registrada — daba la ilusión
de un control que no existía. `compras.handle_mee` quedó GET-only (catálogo de envases).

## 🔒 INV-10 · La RECETA de una fórmula sólo la ve quien tiene permiso INVIMA (25-jul)

`GET /api/formulas` exigía únicamente estar logueado: cualquier usuario (planta, marketing,
contabilidad) recibía las 40 recetas completas con **código de MP y porcentaje**. Verificado con
una sesión real de un usuario común. El candado de la pantalla ("Fórmulas desbloqueadas /
Bloquear") es un **PIN de navegador**: la receta ya había viajado al browser antes de pedirlo, así
que ocultaba sin proteger — un control que parece control y no lo es (misma clase que `/diag/*`
abierto a internet, M95).

**Invariante:** el resolver único es `inventario._puede_ver_formulas()` sobre
`config.FORMULAS_VER_USERS` = Dirección Técnica ∪ Control de Calidad ∪ Aseguramiento ∪ Dirección
(override sin redeploy: `FORMULAS_VER_USERS_OVERRIDE`). **Fail-closed**: si la config no carga, no
se muestra la receta.

Quien no tiene permiso **no recibe 403**: recibe la misma estructura con `items: []`,
`solo_nombres: true` y un `motivo`. Los NOMBRES tienen que seguir viajando o el módulo nace roto
(M32): los consumen el select de Fabricación (`loadFormulas` → `#prod-sel`) y el formulario de
pedido B2B. El operario sigue viendo lo que debe pesar en el legajo de SU lote — lo que se cierra
es *navegar el recetario*.

⚠ Pendiente de la misma auditoría: hay endpoints que devuelven porcentajes sin gate de rol. Los
**operativos** (pesajes-plan, dispensado, rótulos, simular, factibilidad, listo-producir) son
correctos así — el operario los necesita para su lote. Los de **volcado de catálogo**
(`/api/plan/diag-formulas-dump`, `/api/programacion/trail-explosion`,
`/api/programacion/diag-formula-anomalia`, `/api/plan/diag-mp/<codigo>`, `/api/formula/costo`)
deberían pasar por `_puede_ver_formulas`. Tests: `tests/test_formulas_permiso_invima.py`.

⚠ **Ampliado 26-jul:** el gate se extendió a los VOLCADOS de catálogo vía el helper único
`inventario.gate_ver_formulas()` (lo importan los otros blueprints): `/api/plan/diag-formulas-dump`,
`/api/programacion/trail-explosion` (+ su página `/planta/trail-explosion`),
`/api/programacion/diag-formula-anomalia`, `/api/plan/diag-mp/<codigo>` y `/api/formula/costo`.
Lo OPERATIVO sigue abierto a propósito — hoja de pesaje, dispensado, rótulos, `simular`,
factibilidad, `listo-producir`: el operario los necesita para SU lote y cerrarlos dejaría a la
planta sin poder trabajar. Esa es la línea: se cierra NAVEGAR el recetario, no fabricar.

## 📦 INV-9 · Mover un envase entre kardex es Salida compensatoria + Entrada (25-jul)

Un envase recibido por OC cuyo código todavía no estaba en `maestro_mee` caía a la rama MP de
`recibir_oc` y entraba a **`movimientos`** (kardex de materia prima): inflaba el inventario de MP,
dejaba su stock de envase en 0 (abastecimiento lo volvía a pedir) y se saltaba la cuarentena de
envases. Origen tapado (enrutado por prefijo `MEE-`/`ENV-`); las unidades ya escritas se corrigen
con `admin.admin_envases_kardex_mp_mover`.

**Invariante:** mover unidades entre kardex NUNCA es un `UPDATE material_id` ni un DELETE. Se hace
como toda reversa del sistema (INV-1 / M31):

| Paso | Dónde | Detalle |
|---|---|---|
| Salida compensatoria | `movimientos` | mismo `lote` y **mismo `estado_lote` que la Entrada original** → net-zero EXACTO en toda vista (una Salida con otro estado descuadra las vistas que filtran por estado) |
| Entrada | `movimientos_mee` | mismo `lote_ref`, y el estado se **conserva**: CUARENTENA sigue en cuarentena, RECHAZADO sigue rechazado |
| Alta | `maestro_mee` | solo si el código no existía · `ON CONFLICT (codigo) DO NOTHING` · `stock_actual` arranca en 0 (el default de la tabla es 2000) |
| Rastro | `audit_log` | `MOVER_ENVASE_A_KARDEX_MEE`, antes/después, **antes del commit** (M22) |

Guards duros: nunca toca un código presente en `maestro_mps` (eso es materia prima de verdad);
los estados sin equivalente en el kardex de envases (VENCIDO/AGOTADO/BLOQUEADO — `_get_mee_stock`
solo excluye CUARENTENA y RECHAZADO) se **reportan pero no se mueven**, o llegarían allá como
disponibles; el movimiento ancla se reclama con CAS antes de escribir (anti-doble-click en los 3
workers); `dry_run` por defecto. La vista previa y el apply comparten el núcleo
`_envases_kardex_mp_plan` — el número que se muestra es el que decide (M5).

Página: `/admin/envases-kardex-mp`. Detección continua: `envases_en_kardex_mp` en
`/api/admin/auditoria-lotes`. Tests: `tests/test_envases_kardex_mp.py` (en el gate).

## 🔎 La auditoría de lotes ahora LISTA lo que falta, no lo cuenta (26-jul)

Sebastián: *"dame la lista"*. Un conteo no se puede accionar. `/api/admin/auditoria-lotes` devuelve:

| Campo | Qué trae | Por qué importa |
|---|---|---|
| `lotes_sin_vencimiento` | fila por lote **con stock** · código, lote, g, proveedor, último movimiento y **`en_cuarentena`** | si está en cuarentena, el dato se completa ANTES de liberar y no hay nada que corregir hacia atrás |
| `lotes_sin_ubicacion` | idem | |
| `mps_sin_inci` | MPs activas sin INCI, con su stock | el INCI es lo que va en el rótulo y el expediente; sin stock no urge |
| `producciones_en_curso_sin_legajo` | lote iniciado sin EBR, **con `descontó_mp`** | ahora que el batch record vive, esto no debería existir. `descontó_mp` es lo que decide: si descontó, la MP salió del kardex y cerrarla a la ligera deja el stock mintiendo; si no, es una fila zombie cancelable sin tocar inventario |

Sólo lista lotes **con stock**: uno agotado sin fecha de vencimiento es historia, no un pendiente.

⚠ Dos columnas fantasma que cazaron los tests al escribir esto (M12a): `tipo` existe en
`maestro_mps` **y** en `movimientos` (con JOIN hay que calificar toda columna), y
`produccion_programada` **no tiene** columna de lote — `lotes` es el CONTEO de lotes del evento y
el número de lote físico vive en `ebr_ejecuciones.lote_codigo`.

Estado al 26-jul: 21 sin vencimiento (12 en cuarentena) · 62 sin ubicación (47 en cuarentena) ·
30 MPs sin INCI (1 con stock) · 1 producción en curso sin legajo (`PROD-03764` ESENCIA ILUMINADORA,
producto ya descontinuado, trabada desde el 30-jun).


## 🔬 El F01 escribe al kardex lo que Calidad verifica contra el envase (27-jul)

Sebastián: *"Calidad allí hace la recepción, deben poder poner todos los datos de su F01 pero a
la vez editar el rótulo en todos los pasos de la recepción"*.

El F01 ya pedía lote real, cantidad pesada y vencimiento, pero los guardaba **sólo en
`recepcion_tecnica_doc`**: el kardex se quedaba con el lote provisional que asigna la recepción
administrativa y con la cantidad comprada. Y el **rótulo se imprime leyendo `movimientos`**, así
que el envase se rotulaba con datos viejos. Las correcciones sólo aterrizaban al aprobar el F02,
que es el último paso.

Ahora `POST /api/calidad/recepcion-tecnica` (origen MP) escribe al kardex:
- `lote_proveedor` → `movimientos.lote` (**todas** las filas de ese lote, no sólo la Entrada, o la
  ubicación y las salidas quedan colgando de una llave que ya no existe) + `movimientos.lote_proveedor`;
- `cantidad_recibida` → `movimientos.cantidad` (lo que entra a bodega es lo que **pesó**);
- `fecha_vencimiento` → `movimientos.fecha_vencimiento` (sin esto el cron de vencidos nunca lo marca);
- `area_almacenamiento` → `movimientos.estanteria` (va al rótulo).

**Sólo mientras el lote está en CUARENTENA** (M86): corregir hacia atrás un lote ya consumido
corrompería el kardex. Todo queda en `audit_log` con `F01_CORRIGE_KARDEX` y el valor anterior.

Cierra el circuito con INV-11 de `CONTRACT_compras.md`: la recepción administrativa deja un lote
provisional que **no se puede liberar**, el F01 pone el real, y ahí sí se libera.
Tests: `tests/test_f01_escribe_kardex.py` (en el gate).


## 📦 INV-12 · Recepción de envases por LÍNEAS y por CAJAS · sin OC (30-jul · mig 398)

Sebastián: *"mañana llegan 9 palets de China, no tenemos la orden de compra en EOS (las pidió
Alejandro) y llegan a planta · necesito hacerle recepción administrativa para que después Calidad
haga lo suyo"*, y *"llegan 40 cajas de niacinamida cada una con 200 envases, en otra vienen los
goteros, las tapas · que me permita imprimir los rótulos 1 de 30, 2 de 30"*.

- **La OC es texto libre y opcional.** Su ausencia no puede frenar una recepción física que ya
  llegó al muelle.
- **`POST /api/mee/recepcion-lineas`** · `preview: true` NO escribe nada: cruza cada código contra
  el maestro y devuelve qué falta con los totales. El apply es **TODO-o-NADA** (si falta un código,
  409 `CODIGOS_SIN_MAESTRO` y cero escrituras): una recepción es un hecho único con su factura, y
  media recepción escrita es peor que ninguna porque nadie sabe qué entró.
- **La cantidad se DERIVA de las cajas** (`n_cajas × unidades_por_caja`, con
  `unidades_ultima_caja` opcional porque la última casi siempre viene incompleta). Lo que se cuenta
  en el muelle son cajas; si se teclearan las dos cosas, divergen (M71). Sin `n_cajas`, una
  `cantidad` suelta = 1 recipiente.
- **Las cajas se GUARDAN** (`movimientos_mee.n_cajas` / `unidades_por_caja`, mig 398 · nuleables,
  toda recepción anterior sigue igual). Sin eso, el día que Calidad reimprima el rótulo de la caja
  7 el sistema tendría que adivinar cuántas cajas eran (M115).
- **Idempotencia con token del CLIENTE** (`recepcion_id` + UNIQUE de `oc_recepcion_dedup`, mig
  265): el servidor no puede distinguir un doble-envío de una segunda recepción legítima del mismo
  material (M45). Sin esto un doble-click mete 9 palets dos veces.
- Todo entra en **CUARENTENA** (`recepcion_auto_vigente` manda) → **UNA sola campana** a Calidad
  con el resumen, no una por línea (12 alertas seguidas es fatiga y se dejan de mirar).
- Códigos y lotes con `.strip()` en el punto de escritura: un tabulador pegado a un código es una
  CLAVE DISTINTA = stock invisible en el kardex (M100).
- Pantalla `/planta/recepcion-envases` (pegar packing list → ver qué cruza → crear los que faltan
  con `stock_actual` **0 explícito**, porque `maestro_mee` tiene `DEFAULT 2000` y un alta
  descuidada inventa 2000 unidades · M100 → recibir).

### El rótulo va por CAJA · `GET /rotulos-recepcion-mee`
`?mov=<id>` (las cajas de esa línea) · `?movs=1,2,3` (toda la recepción en un imprimible) ·
`?caja=7` (sólo esa caja, que es lo que Calidad necesita cuando revisa caja por caja y cambia el
rótulo de una). **Un solo renderizador** (`_rotulo_mee_sheet`) para la ruta de a uno y la de por
caja: dos renderizadores del mismo documento regulado divergen y el que queda viejo imprime otra
cosa (M1). El **estado va MARCADO desde el kardex** (☒ Cuarentena / ☒ Aprobado), no con las tres
casillas vacías: al liberar y reimprimir, el rótulo sale correcto sin que nadie se acuerde de
tacharlo. La última caja lleva el resto, no una cantidad igual que no suma lo recibido.

### ⚠ El bug que esto destapó (M5/M26 · 2ª instancia)
`/api/mee/stock` (la pantalla de Envases) y `/api/mee/alertas` sumaban el stock **sin excluir
CUARENTENA ni RECHAZADO**, mientras el canónico `_get_mee_stock` —el que usa producción y
planeación— **sí las excluye**. Con un contenedor recién recibido la pantalla lo mostraba como
**disponible** y la alerta de bajo mínimo se apagaba con material retenido: dos números para lo
mismo y el que se ve es el que miente. Ahora el disponible es idéntico al canónico y lo retenido va
**aparte y visible** (`en_cuarentena`, `rechazado`), porque si sólo bajás el número el operario no
entiende por qué no subió (M6). El contador de bajo-mínimo del encabezado también se cuenta sobre
el disponible, no sobre el cache. Y la recepción **ya no infla `maestro_mee.stock_actual`** con lo
retenido: entra al cache cuando Calidad libera.

**PENDIENTE (Sebastián 30-jul):** Calidad revisa **caja por caja** y puede necesitar liberar unas y
rechazar otras de la misma línea. Hoy `mee_cuarentena_resolver` libera o rechaza el movimiento
COMPLETO. La liberación parcial por caja es la pasada siguiente; se hace antes de que Laura haga el
F01 de este contenedor.

### Vive DENTRO de Recepción, como una pestaña
Sebastián (30-jul): *"no puede quedar todo de manera loca, pueden quedar en recepción pero como
una pestaña para recepcionar este tipo de cosas"*. Nació como página aparte
(`/planta/recepcion-envases`) y estaba en el lugar equivocado: **el punto de entrada lo define el
TIPO de cosa que llega**, no la feature que la construyó, y una página al lado es una función que
nadie encuentra.

`/recepcion` gana una barra de pestañas por tipo: **Con orden de compra** (todo lo que ya había,
intacto) y **Contenedor sin OC · envases por cajas**. La ruta vieja **redirige** a
`/recepcion#envases` (borrarla dejaría el enlace que ya existe apuntando a la nada · M112).

Tres trampas de compartir documento, todas cerradas y con test:
- **No se reusa `showTab` ni las clases `tab-btn`/`tab-content`**: esa función está cableada a las
  4 sub-pestañas del monitoreo de OCs y APAGA todos sus paneles antes de encender el destino, así
  que con un destino ajeno dejaría la pantalla en blanco (M61/M112). Clase (`rt-*`) y función
  (`rtIr`) propias.
- **El panel va prefijado** (`env-` en ids, `env` en funciones): la página ya tenía su propia
  `esc()`, y una segunda declaración del mismo nombre pisa la primera y rompe la pantalla ajena
  sin un solo error (M59). Un test falla si cualquier función queda declarada dos veces en la
  página renderizada.
- **Se inyecta UNA vez con `assert`** (`__PANEL_ENVASES__` en `despachos.recepcion_panel`): si el
  placeholder no matchea, la pestaña queda con botones que llaman a funciones que no se cargaron
  (M116). El panel vive en `templates_py/recepcion_envases_panel.py`, no duplicado.

**PENDIENTE de esa conversación:** falta la pestaña de **EQUIPOS** (Sebastián va a pasar la lista).
Hoy existe `equipos_planta` (código, área, tipo, capacidad, estado operacional) y la bitácora de
calibración de Aseguramiento, pero NO el lado de activo (serial, marca, modelo, proveedor, factura,
garantía, vida útil) ni la calificación IQ/OQ/PQ, que para un equipo es lo que la cuarentena es
para un material: llega y no se puede usar hasta que Aseguramiento lo califica y calibra.

Tests: `tests/test_recepcion_envases_lineas.py` (en el gate · 22 casos, incluida la pestaña, el
redirect de la ruta vieja y el guard anti-colisión de funciones).


## 📦 INV-13 · Calidad dispone CAJA POR CAJA (mig 399)

Sebastián (30-jul): *"ya cuando calidad haga verificación entonces revisa caja por caja y si es
necesario cambia los rótulos"*. Liberar o rechazar el movimiento COMPLETO no alcanzaba: de 24
cajas pueden pasar 22 y venir 2 golpeadas, y había que elegir entre aprobar las malas o rechazar
las buenas.

- **La cantidad de CADA caja se guarda al recibir** (`mee_cajas_disposicion`). En el muelle se
  abre caja por caja y cada una puede traer distinto; derivarla dos veces con dos cuentas termina
  en un cartón que dice una cosa y un sistema que dice otra (M5). El rótulo de la caja y la
  disposición leen la MISMA fila.
- `POST /api/mee/cuarentena/<mov>/cajas` · sólo Calidad · rechazar **exige motivo** (una auditoría
  pregunta por qué) · no se puede **cerrar a medias** (409 `CAJAS_SIN_REVISAR`: una caja sin
  revisar quedaría ni disponible ni rechazada) · CAS sobre el estado para que dos cierres
  concurrentes no partan el movimiento dos veces.
- **Al cerrar se parte la cuenta**: el movimiento original queda con lo aprobado y en VIGENTE, y
  lo rechazado sale en su propia fila en RECHAZADO. El total se conserva (800 = 400 + 400) y el
  disponible es sólo lo aprobado.
- ⚠ **`n_cajas` NO se toca y las filas por caja NO se mueven.** Renumerar dejaría al cartón que
  dice "3 de 3" hablando de una caja que el sistema ya no tiene — y es justo la que hay que
  reimprimir marcada. La numeración física de algo ya rotulado es un hecho, no un derivado (M115).
- **El rótulo imprime el estado de SU caja** (☒ Rechazado / ☒ Aprobado), leído del kardex: al
  reimprimir sale correcto sin que nadie tache nada.
- **El código de barras identifica la CAJA**, no la referencia: `MEE-<recepción>-<caja>`. Dos
  cajas del mismo frasco tienen que distinguirse porque una puede quedar rechazada y la otra no.
  `GET /api/mee/escanear?token=…` lo resuelve, y la bandeja de Calidad tiene el campo de escaneo
  (la pistola teclea y se abre esa caja).

Tests: `tests/test_cajas_disposicion_calidad.py` (en el gate · 15 casos).


## ✅ Revisión de RECEPCIÓN DE MATERIA PRIMA · el recorrido completo camina (30-jul)

Sebastián: *"quiero que revises materias primas, que sí se recepcionen, que sí pase todo, que no
tenga bugs"*. Se verificó **caminando el flujo por los endpoints reales**, no leyendo código
(M94), y el resultado es que la cadena funciona de punta a punta:

    OC autorizada → recepción administrativa (cuenta bultos, lote provisional)
      → Entrada en CUARENTENA · NO cuenta como stock disponible
      → le llega a Calidad en el pipeline de recepción
      → F01 conforme: lote REAL + peso de balanza + vencimiento + ubicación → **al kardex**
      → el rótulo imprime el lote real (se imprime del kardex · M109)
      → firma electrónica Part 11 (meaning `libera`) → F02 aprobado
      → recién ahí el lote SUMA al stock disponible

**No se encontró ningún bug en el flujo principal.** Los guards que ya costaron caídas siguen
en pie y quedaron fijados con test: ítem de OC con `codigo_mp` vacío (el 500 de producción del
10-jul · M81) no tumba la recepción, doble envío con el mismo token no duplica, parciales
sucesivas suman lo pedido, un "código" con espacios se rechaza (una factura de servicios no
entra a la bodega), con OC la factura es obligatoria, y no se recibe 5× lo comprado sin forzar.

⚠ Tres cosas que el E2E dejó claras y conviene no re-litigar: (1) el F02 **exige firma
electrónica** para disponer el lote — no es una traba, es el control que le pone nombre a la
liberación; (2) la clave del payload de recepción es `cantidad_recibida` (no `..._g`); (3) el F02
firma con `aprobo_por` / `responsable_analisis`.

Tests: `tests/test_mp_recepcion_e2e.py` (en el gate · 9 casos).

## 📅 La hoja de pesaje dice el VENCIMIENTO de la MP que se usa (30-jul)

Sebastián: *"en el rótulo de pesaje que vaya la fecha de vencimiento de la materia prima que
usan"*. El rótulo de dispensación ya lo imprimía; la **hoja de pesaje del batch record**
(`/brd/dispensado/<ebr>`, el papel que el operario sigue en piso) no — y es donde más importa,
porque es el punto de USO. Sale del **kardex** para el `(material, lote)` que se pesó de verdad
(el maestro no tiene lotes), sin lote pesado se declara que falta en vez de inventar una fecha
(M115), y si el lote ya venció **se marca en rojo**: una MP vencida no puede entrar al producto
(INVIMA Res. 2214 · M25).

Tests: `tests/test_hoja_pesaje_vencimiento.py` (en el gate · 3 casos).


## 🏷️ INV-14 · El rótulo de pesaje REPARTE por lote y no inventa cantidad (30-jul)

Sebastián, a punto de producir SUERO MULTIPÉPTIDOS de 45 kg: *"del palmitoyl tripéptido-4 hay
sólo uno, con menor cantidad de la que se requiere, y cuando le doy rótulos de pesaje me saca ESE
con la cantidad necesaria a pesar de que no hay (...) debería tomar el lote más viejo con la
cantidad que hay + otro rótulo con el otro lote que tenga lo que falta, porque así estaría
registrando lo que no es"*.

`/rotulos/<producto>/<kg>` resolvía **un** lote (el más próximo a vencer con stock) y le imprimía
el peso teórico **completo** sin mirar si alcanzaba. Es un registro regulado (PRD-PRO-001-F08)
documentando un lote y una cantidad que no existen, y el operario terminaba completando de otro
lote **sin rótulo**.

- **El reparto sale de `_distribuir_fefo`, el MISMO que usa el descuento de producción.** Si
  fueran dos cuentas distintas, el papel y el kardex divergirían (M1/M5). Un rótulo **por lote**,
  con la cantidad de ESE lote, su ubicación y su vencimiento.
- Cada hoja marca **"Parte k de n"** y el peso dice *"Peso de ESTE lote · de X g en total"*: nadie
  puede confundir la parte con el total.
- ⚠ **`_distribuir_fefo` LANZA si el stock no alcanza** (correcto para un descuento: no se
  descuenta lo que no hay). Para el rótulo se le pide el reparto de **lo disponible** (stock
  canónico · regla #4) y la diferencia queda como **faltante declarado**: sale su propia hoja con
  *"NO HAY STOCK PARA ESTA CANTIDAD · faltan X g"*, nunca un lote inventado. La primera versión
  atrapaba esa excepción y caía al comportamiento viejo — o sea, no cambiaba nada justo en el caso
  que importaba; lo cazaron los tests.
- **Aviso en pantalla (no impreso)** con la lista de qué MP no alcanza y cuánto falta, antes de
  bajar a bodega.

Tests: `tests/test_rotulo_pesaje_reparto_lotes.py` (en el gate · 5 casos, incluido uno que compara
el reparto del rótulo contra el del descuento para que no puedan divergir).

### El rótulo IMPRESO · por qué salía "sin divisiones ni cuadritos" (30-jul)

Del piso: *"al imprimir los rótulos no se ven como en la foto, salen sin divisiones ni cuadritos"*.
Dos causas, las dos en el CSS:

1. **El navegador NO imprime fondos ni rellenos** salvo que el CSS lo exija. Sin
   `print-color-adjust: exact` (+ `-webkit-`) desaparecen el gris de las etiquetas, el relleno del
   peso y el rayado de las casillas para escribir: el papel sale casi en blanco.
2. **Las líneas iban en `#e4e4e7`.** Un gris clarísimo se ve bien en pantalla y en una **térmica
   monocroma sale invisible**. En `@media print` los bordes van en **negro** explícito (no por
   token: el token es claro a propósito) y los rellenos en un gris que sí marca.

**Regla: un imprimible que se apoya en fondos y en líneas grises no sobrevive a la impresora.**
Todo documento regulado que se imprime va con `print-color-adjust: exact` y con los bordes
declarados en un color que marque en térmica. Se verifica **simulando la impresión** (aplicar las
reglas del `@media print` como hoja normal y mirarlas), no imprimiendo a ojo.

**Rediseño del mismo día** (Sebastián: *"lo que debería ir más grande es el nombre de la materia
prima y cuánto pesar; el título va más pequeño a un lado; quitá esas líneas de firmas"*): el
título del formato pasó a una línea chica junto al logo, el **nombre de la MP y el peso son el
héroe** de la etiqueta, y la cuadrícula ganó divisiones verticales (`td+td`). Los dos bloques
grandes de firma se retiraron, pero **el registro de quién pesó NO se pierde**: quedó como celda
`Pesó / hora` dentro de la cuadrícula (un rótulo GMP sin ejecutor no es un registro). Alto impreso
medido: **84 mm** sobre la etiqueta de 100 mm.

## 👁️ INV-15 · La verificación de MP MUESTRA los lotes (30-jul)

Sebastián, en vivo: *"goma xantana tenía dos lotes, pero al fabricar sólo jalaba uno -- el de
poca cantidad -- y lo mostraba como sin stock"*.

El motor está bien y se verificó antes de tocar nada: `_validar_stock_para_produccion` y el
camino directo de `/api/produccion` **suman todos los lotes usables** del código. Lo que faltaba
era decirlo: el faltante viajaba con `disponible_g / falta_g` y la pantalla no mostraba **cuáles**
lotes hay ni por qué algunos no se pueden tocar.

- Helper canónico **`_lotes_de_material(c, cod)`** (programacion.py) → `{usables, retenidos}`.
  Usable = lo que el FEFO va a consumir, en orden de vencimiento. Retenido = existe en bodega
  pero producción no puede tocarlo, **con el motivo**: cuarentena sin liberar, rechazado,
  bloqueado, o **vencido por fecha aunque el cron todavía no lo haya marcado** (mismo criterio
  que el FEFO · M25, o la pantalla diría algo distinto de lo que el descuento hace).
- Los **dos caminos** (fabricación directa y arranque programado) devuelven `lotes_usables` y
  `lotes_retenidos` desde ese único helper: no puede haber una pantalla contando una historia y
  otra contando otra (M5).
- La UI los pinta en el popup de "no se puede fabricar" y en el detalle inline.
- **Diagnóstico por NOMBRE**: `GET /api/admin/mp-diag?q=goma` (admin) lista TODOS los códigos que
  matchean, cada uno con sus lotes y estados, y avisa cuando hay más de uno con stock —
  producción consume UN código por ítem de fórmula, así que el stock del otro **no se suma**.
  Con `?codigo=` sigue funcionando igual. La página `/admin/mp-diag` trae el buscador.

Tests: `tests/test_lotes_visibles_verificacion.py` (en el gate · 6 casos, con el escenario de
Sebastián sembrado tal cual: un lote chico usable + uno grande en cuarentena).

## 🔧 INV-16 · Recepción de EQUIPOS · la calificación es su cuarentena (30-jul)

Sebastián: *"los equipos llegan, necesito que Compras los recepcione, o Luz en Espagiria"*.
Va como **pestaña de `/recepcion`** (el punto de entrada lo define el TIPO de cosa que llega ·
M120), no como página aparte.

- **Quién**: `POST /api/recepcion/equipos` → `COMPRAS_ACCESS ∪ {luz} ∪ ADMIN`. **Calificar es
  OTRO permiso** (`_autorizados_equipos` = Calidad ∪ Aseguramiento ∪ Admin): el que recibe no
  aprueba su propia recepción.
- **`estado_calificacion` es la cuarentena del equipo** (mig 402): nace `PENDIENTE` y
  `_equipos_de_area` lo EXCLUYE, así que producción no lo puede elegir. Al calificar
  (`POST /api/calidad/equipos/<cod>/calificar`) pasa a `CALIFICADO` + `estado_operacional=operativo`
  y recién ahí aparece. Rechazado → `baja`, **sin borrar** (GMP): queda registrado.
  Los 102 equipos que ya existían quedan en `NO_APLICA` y siguen saliendo igual — la migración
  es aditiva y no les inventa una calificación que nadie hizo (M117).
- **CAS** en la calificación: dos clicks (o dos workers) no pueden dejar el equipo en dos
  estados distintos → 409 si ya no está pendiente (M27). Y deja **evento en la hoja de vida**
  (`equipos_eventos` tipo `validacion`, que es el valor que admite el CHECK · M62): sin ese
  registro nadie puede demostrar que se calificó antes de usarlo.
- **Código**: `<PREFIJO>-<ZONA>-NNN` continuando la numeración que ya existe (`BL-PRD-007`,
  `PR-COC-002` para Control de Calidad). El correlativo se extrae **en Python**, nunca con
  `CAST(SUBSTR(...))` (M45). Si el equipo trae placa propia, se respeta.
- **Un serial es UN equipo**: no se puede pegar el mismo a N unidades (400) ni repetir uno ya
  registrado (409).
- **Rótulo** `GET /rotulos-equipo?cods=A,B` con código de barras, en el mismo lenguaje visual
  que los demás rótulos de Planta (`_rotulo_recep_css`), y dice **"PENDIENTE DE CALIFICACIÓN ·
  NO USAR"** mientras no esté calificado.

Tests: `tests/test_recepcion_equipos.py` (en el gate · 12 casos, con los permisos probados en
los dos sentidos y el equipo pendiente ausente de su área hasta calificarse).

## 📦 INV-17 · Los ENVASES entran DISPONIBLES · la revisión no es un candado (30-jul)

Sebastián: *"aquí no deben caer en cuarentena de una, que ingresen a inventario para ser usados;
lo que queda es para Calidad revisar estados, pero no en cuarentena"*. Cambia la decisión del
25-jul (que había dejado el gate de envases apagado a medias) y **no toca la materia prima**: la
MP sigue entrando en CUARENTENA, que es lo que exige INVIMA.

- `POST /api/mee/recepcion-lineas` escribe `estado='VIGENTE'`: el envase cuenta como stock
  disponible desde que se recibe. Se puede forzar cuarentena con `{"cuarentena": true}`.
- **El estado de la CAJA es de REVISIÓN, no del kardex**: nace `'PENDIENTE'`. Antes heredaba el
  estado del movimiento y eso mezclaba dos cosas distintas (dónde está el material vs si alguien
  ya lo miró). El valor legado `'CUARENTENA'` se lee como pendiente.
- ⚠ **Quitar el candado casi se lleva puesta la revisión**: la bandeja de Calidad
  (`/api/calidad/recepcion-pipeline`) listaba SOLO lo que estaba en cuarentena, así que la
  revisión caja por caja habría desaparecido de la pantalla el mismo día, en silencio (M112).
  Ahora también lista lo que llegó por cajas y nadie revisó (`n_cajas>0` y sin `[REVISADO]`), y
  la fila trae `cajas_por_revisar` — la pantalla decide con ESO, no con el estado del kardex.
- **El control es el rechazo**: si el material entra disponible, lo que lo sostiene es que
  rechazar SAQUE del stock. Cerrar la disposición con 2 de 24 cajas rechazadas baja el
  disponible de 4.800 a 4.400 y deja la fila de rechazo aparte (total intacto y trazable).
- **CAS por MARCA, no por estado**: ya no hay transición CUARENTENA→VIGENTE sobre la que
  reclamar, así que el cierre se reclama con `[REVISADO]` en `observaciones`
  (`WHERE ... NOT LIKE '%[REVISADO]%'` + rowcount, patrón de M31). La marca **se quita del
  imprimible**: es del sistema, no va en un formato regulado.
- **CACHE `maestro_mee.stock_actual`**: si entró en cuarentena no se sumó nada → se suma lo
  aprobado; si entró disponible ya se sumó todo → se **resta lo rechazado**. Sumar lo aprobado en
  el segundo caso contaría el material dos veces (el stock canónico se corrige solo · M26).
- **Rótulo honesto**: mientras queden cajas por revisar dice `☒ Pendiente revisión`, no
  "Aprobado" (marcarlo al recibir sería decir que Calidad ya pasó) ni "Cuarentena" (ya no lo
  está). El número de caja es un **chip destacado** (`Caja 1 de 24`) y el lote se lleva la fila
  entera: en la columna angosta salía partido como "CN-" / "2607-A", y un lote mal transcrito en
  un registro regulado es un problema real. Alto medido: 83,6 mm de los 96 útiles.

Tests: `test_recepcion_envases_lineas.py` + `test_cajas_disposicion_calidad.py` (los dos en el
gate). Los 6 casos que fijaban la regla vieja se actualizaron **con el motivo escrito**: no se
rompieron, cambió la decisión (M97). Los nuevos fijan lo que ahora sostiene el control —
`test_la_revision_de_calidad_NO_desaparece` y `test_lo_que_calidad_RECHAZA_sale_del_stock`.

## 🔎 INV-18 · La consulta rápida: qué lote y DÓNDE está (30-jul)

Sebastián, mirando "Verificar stock" antes de fabricar: *"aquí pienso que debería ser un punto de
consulta rápida · como aquí dice si alcanza o no, debería salir el lote y la posición de la
materia prima, así pueden ir consultando sin salirse de allí"*.

- `POST /api/produccion/simular` devuelve por ingrediente `lotes` (los que el FEFO va a consumir,
  con cantidad, vencimiento y **ubicación**) y `lotes_bloqueados` (los que existen en bodega pero
  no se pueden tocar, con el motivo). Sale del helper canónico `_lotes_de_material` (INV-15), así
  que dice lo MISMO que el aviso de faltante y que el descuento real.
- La ubicación se lee de la **Entrada** del lote, que es donde se guarda al recepcionar.
- `GET /api/alertas/all` → los lotes vencidos traen `ubicacion`: dar de baja 12 lotes sin saber
  dónde están es recorrer la bodega buscando cada uno.

## 🏷️ INV-19 · Lote INTERNO cuando el proveedor no manda lote (30-jul)

Sebastián: *"es posible que no tengan lote · qué tal si ponés la opción de lote interno, y te
inventás cómo serían para la trazabilidad"*.

`POST /api/mee/recepcion-lineas` con el lote vacío genera **`INT-AAMMDD-NNN`**: fecha de recepción
(el hecho que lo origina) + correlativo del día, extraído en Python (nunca `CAST(SUBSTR(...))` ·
M45). Dos referencias del mismo contenedor **no comparten lote**: ante un reclamo, apunta a UNA
recepción concreta y no a "lo que llegó ese día".

El rótulo lo imprime marcado **"interno EOS (el proveedor no envió lote)"**. Si se confundiera con
un lote del proveedor, mañana alguien le reclama a China por un número que EOS se inventó (M115:
sin dato no se inventa un default que parezca real).

**La cola de calificación de Calidad la decide QUIEN RECIBE** (`requiere_calificacion` en
`/api/mee/crear-auto`, default NO): antes toda referencia nueva nacía `calificado=0` y la bandeja
acumulaba material que nadie pidió revisar — una bandeja con 22 ítems que no hay que mirar deja de
mirarse. La campana también se calló para los que no la requieren.

Tests: `tests/test_consulta_rapida_planta.py` + `test_recepcion_envases_lineas.py` (en el gate).

## 🔐 Permiso del import masivo de envases (30-jul)

`POST /api/mee/import-bulk` mutaba el maestro y el stock sin permiso de rol. Gate **proporcional**:
planta sigue cargando (`_require_planta_write` · es su día a día y trabarlo sería una traba
fantasma · M68), pero **`modo='replace'`, que ARCHIVA en masa todo lo que no venga en el archivo,
exige ADMIN** (409 `REPLACE_SOLO_ADMIN`). Test en los dos sentidos:
`tests/test_permisos_barrido_30jul.py`.

## ⚖️ INV-20 · La corrección de una colisión de código es NET-ZERO o no es corrección (2-ago)

El 9-jul un consumo retroactivo descontó materia prima por el **código equivocado** (MyBatch y EOS
usan el mismo número para moléculas distintas). El 15-jul se corrigió… **de un solo lado**: se
agregó el descuento al código correcto y nunca se devolvió el del equivocado.

Las cantidades cuadran al gramo en los tres pares, así que la corrección **identificó bien** el
material; lo que faltó fue la otra pata:

| Código equivocado | Salió mal el 9-jul | Se corrigió a | El 15-jul |
|---|---|---|---|
| `MP00300` Eversoft YCS-30S | 1.400 + 105 g | `MP00103` Ceramide NP | ✓ |
| `MP00301` Ethylhexylglycerin | 3.150 + 1.050 g | `MP00030` Propylheptyl | ✓ |
| `MP00302` Isododecane | 140 g | `MP00301` Ethylhexylglycerin | ✓ |

Resultado: esos tres muestran **menos stock del que hay en el estante** y el consumo figura
registrado dos veces. `MP00303` y `MP00298` no tienen desbalance (sus correcciones se hicieron sin
haber descontado mal antes).

**Por qué la herramienta del 15-jul no lo cerró sola:** `descuento_retro_corregir` revierte sólo si
se le vuelve a subir el Excel Y el marcador coincide exacto; si el `wrong` sale vacío, el paso 1 no
hace nada y el paso 2 aplica igual → media corrección, sin un solo error a la vista.

`GET/POST /api/admin/colisiones-net-zero` (ADMIN · `_plan_colisiones_net_zero` compartido por la
previa y el apply · M101) se apoya en el kardex, no en el Excel:

- **Empareja por EVIDENCIA, no por parecido.** Tier 1 = el marcador (`[retro-corr B|Y|L|N]` conserva
  bulk, lote y cantidad del `[retro B|X|...|N]` original: sólo cambia el código). **Acepta los DOS
  formatos del marcador de descuento**: el actual `bulk|código|lote|cantidad` y el de julio
  `bulk|código|cantidad` (el lote se le agregó después) -- los movimientos reales del 9-jul tienen
  el de tres campos, así que sin esto todo caía al tier 2. Tier 2 = la cantidad, y **sólo si es
  inequívoca**. Lo que no cruza se reporta en `sin_pareja` y NO se toca.
- **Tope duro:** nunca devuelve más de lo que la corrección movió al código correcto — devolver de
  más es inventar material. Lo que excede sale en `excedente`, sin escribir.
- **Net-zero real (M31):** la Entrada va al **mismo lote**, espejando el `estado_lote` original (un
  lote en cuarentena vuelve a cuarentena: no se libera material por la puerta de atrás) y
  **conservando el vencimiento** (si se pierde, el cron de vencidos deja de verlo y el FEFO lo trata
  como eterno · M118/M25).
- **CAS sobre la Salida original** antes de escribir (M27: con 3 workers un SELECT-luego-INSERT deja
  pasar los dos y devuelve el doble). El marcador `[retro-corr-rev #<id>]` es **el mismo** que usa la
  herramienta del 15-jul, así que las dos se detectan mutuamente (M3).
- Auditado antes del commit (`COLISION_NET_ZERO`) y reversible.

UI: panel inferior de `/admin/corregir-colisiones`. Tests: `tests/test_colisiones_net_zero.py`
(en el gate · el tope y el espejo de estado probados con dientes).

### El origen, tapado (2-ago)

`descuento_retro_corregir` (la herramienta del 15-jul) revierte el descuento equivocado **sólo si
el marcador calza**. Los movimientos del 9-jul llevan el marcador viejo de tres campos, así que no
calzaba: el paso 1 no hacía nada, el paso 2 aplicaba igual, y el consumo quedaba contado dos veces
**sin un solo error a la vista**. Ahora, si el marcador no encuentra el descuento equivocado, lo
busca por CANTIDAD (y sólo si es inequívoco) antes de aplicar la otra pata; si de verdad no hay
nada que revertir, lo **declara** en `aviso` en vez de aplicar en silencio.

**Regla general: si una operación tiene dos patas, la segunda no puede depender de que la primera
haya encontrado algo. O las dos, o ninguna -- y si la primera no encontró nada, eso se dice.**

Tests: `test_colisiones_net_zero.py::test_la_herramienta_del_15jul_ya_no_puede_hacer_media_correccion`
y `::test_avisa_cuando_no_encuentra_el_descuento_equivocado`.

## 📥 INV-21 · Una OC AUTORIZADA se puede RECIBIR (3-ago)

`GET /api/ordenes-compra/pendientes-recepcion` llena el desplegable de "¿qué OC estás
recibiendo?" del formulario de ingreso. Filtraba:

```sql
WHERE oc.estado IN ('Aprobada','Enviada','Parcial')
```

**`Autorizada` no estaba** — que es justo el estado normal de una OC esperando la mercancía.
Catalina: *"se me están perdiendo las órdenes autorizadas"*. Medido contra producción con sus
dos OCs de ese día: `/recepcion` listaba **51** OCs y el desplegable le ofrecía **3**, ninguna
suya. Al ir a registrar el ingreso, sus órdenes no existían.

**`'Enviada'` no es un estado de `ordenes_compra`**: pertenece a la máquina de estados de las
COTIZACIONES (`Borrador → Enviada → Recogida`). Estaba ocupando el lugar del estado que
faltaba, y por eso el hueco pasó desapercibido.

**Invariante:** el conjunto es `('Aprobada','Autorizada','Pagada','Parcial')`.

- **`Pagada` entra**: pagar por anticipado y recibir después es normal acá (M47). Si no
  aparece, esa mercancía no se puede registrar cuando llega.
- **`Recibida` NO entra**: ya se recibió completa.
- **Se excluyen `CATEGORIAS_PAGO_DIRECTO` + influencers**: nadie "recibe" un servicio ni una
  cuenta de cobro, y ofrecerlos en el desplegable de ingreso al kardex invita a meter al
  inventario algo que no existe físicamente.

⚠ El mismo filtro roto vivía en el KPI de OCs pendientes de `gerencia.py` (M45: un patrón
vive replicado en los sitios que copiaron el idiom).

Tests: `tests/test_oc_autorizada_visible.py` (incluye el guard de que ningún filtro de
`ordenes_compra` vuelva a usar el estado fantasma `'Enviada'`).


## 📦 INV-14 · La recepción de un envase declara QUÉ TRAE EL BULTO (5-ago · mig 418)

Sebastián, con la pantalla delante: *"aquí debería existir la lógica de ese envase tiene parte?
viene con gotero? y si lo compramos con plegadiza y llega con plegadiza desde China, ALLÍ es donde
debe vivir todo porque allí se da la recepción"*.

**La distinción que hace que funcione:** `mee_partes` es la RECETA del envase — dice que el frasco
LLEVA gotero, y eso no cambia. Que **ESTE embarque VINO** con el gotero adentro es un hecho del
EMBARQUE: el mismo frasco puede venir armado de China y suelto de un proveedor local. Por eso se
CONFIRMA al recibir y no se deduce del maestro.

Reglas duras de `POST /api/mee/recepcion-lineas`:
- Cada pieza confirmada entra con su **propio movimiento** en `movimientos_mee`, por
  `unidades_del_bulto × cantidad_por_envase`. La cantidad se MULTIPLICA, nunca se teclea: dos
  números para el mismo hecho divergen el día que cambien las unidades (M71/M99).
- La pieza **hereda lote y vencimiento del bulto**. Una Entrada sin vencimiento la deja fuera del
  cron de vencidos y el FEFO la trata como eterna (M118).
- Queda **amarrada** al movimiento del frasco por `[recep #N]`, así que la recepción se puede
  deshacer entera.
- Una pieza que **no existe en `maestro_mee` NO entra y se DECLARA** en `avisos`. Un código mal
  tecleado que entra igual crea stock fantasma que nadie puede reponer (M100).
- `mee_partes.incluido_default` (mig 418) es **memoria, no regla**: premarca la casilla la próxima
  vez. Un dato que alguien tiene que recordar termina viejo (M109).
- La respuesta devuelve `partes_ingresadas` NOMBRÁNDOLAS. Sumarlas al total dejaría a quien recibe
  sin forma de verificar que el gotero quedó registrado.

Tests: `tests/test_recepcion_partes_envase.py` (en el gate).

## 🏷️ INV-27 · UN solo renderizador para el rótulo de MP (6-ago)

Alejandro pidió imprimir los rótulos de N materias primas de una sola vez (`GET
/rotulos-recepcion?movs=1,2,3`), y desde Recepción por número de lote
(`GET /api/lotes/por-numero?lotes=L-1,L-2` → resuelve a movimientos).

- **Es EL MISMO rótulo.** El armado vive en `_rotulo_mp_hojas(codigo, lote, cantidad, args,
  estado)` y lo usan los DOS caminos: el individual (`/rotulo-recepcion/...`) y el bloque. Es un
  documento **REGULADO** (COC-PRO-002-F07): dos renderizadores divergen y terminan imprimiendo
  distinto según por dónde se pida (M1/M93). La extracción se hizo **cortando el cuerpo por
  líneas**, sin reescribir la maqueta -- un error de transcripción ahí no se ve hasta que lo lee
  la auditoría.
- **El ESTADO (CUARENTENA / APROBADO / RECHAZADO) sale del KARDEX** (`movimientos.estado_lote`),
  **nunca de la URL**. Verificado con test: `?estado=APROBADO` sobre un lote en cuarentena no lo
  cambia. Un rótulo que miente pegado a un bidón es peor que no tener rótulo.
- **El peso visual va en la PALABRA y un borde grueso, no en un relleno de color**: en térmica el
  navegador no imprime fondos sin `print-color-adjust: exact` y un gris claro es invisible
  (M123). Reemplaza el recuadro "colocar sticker", que existía porque el estado se pegaba a mano.
- **Los campos del F01/F02 salen en BLANCO** mientras no se hayan hecho: un dato inventado miente
  con formato de verdad (M115). Al hacerlos se reimprime el mismo rótulo y sale completo.
- **Lo que no se pudo rotular se DECLARA** (lotes no encontrados, movimientos sin código):
  imprimir 3 de 5 sin avisar es peor que fallar, porque el que pega no sabe cuál falta (M124).

⚠ El **lote en recepción sigue siendo OPCIONAL** (decisión de Sebastián, 27-jul: trababa la
recepción administrativa). Si queda vacío entra el provisional `OC-<oc>-<n>` y Calidad carga el
real en el F01, que **sí** reemplaza el del kardex.

Tests: `tests/test_rotulos_en_bloque.py` (en el gate).


### INV-12 · El mínimo de un envase deja QUIÉN y desde qué valor (8-ago-2026)

`PUT /api/maestro-mps/<codigo>/mee-stock-minimo` escribe `maestro_mee.stock_minimo`, que es lo que
**dispara la sugerencia de comprar** ese envase: subirlo de más compra de más, bajarlo de más deja
la línea sin frascos. Queda auditado con el valor anterior (sin él no se puede revertir), igual que
el puente base↔serigrafiado (M139) y el método de marcación.

Tests: `tests/test_rastro_maestro_envases.py` (en el gate).

---

## El aviso de STOCK INSUFICIENTE nombra los materiales (16-ago-2026)

El 422 de `verificar-stock` decía *"No se puede producir 1kg de X: **2 MP(s) sin stock
suficiente**"*. El detalle viajaba en `faltantes`, pero el MENSAJE -- que es lo que la persona lee
-- sólo traía el número, así que no se podía saber qué comprar ni qué lote liberar sin abrir la
respuesta cruda. Sebastián se trabó dos veces con ese aviso caminando el demo.

**Regla:** un aviso que FRENA tiene que decir qué lo destraba. Ahora nombra hasta cuatro
materiales con lo que se necesita y lo que hay (`falta MP00123 (necesita 900 g, hay 0)`) y
**declara cuántos quedaron sin nombrar** en vez de recortar en silencio (M148/M155).

El detalle completo sigue en `faltantes`, con los lotes retenidos y por qué no cuentan (M124): un
total que excluye sin nombrar lo excluido se lee como "no hay", cuando lo que pasa es que el
material está en cuarentena o vencido.

## 🚪 El registro de acondicionamiento descuenta por la PUERTA COMPARTIDA (17-ago)

`POST /api/acondicionamiento` **ya no descuenta por su cuenta**. Delega en
`brd.descontar_mee_del_lote`, la misma puerta que usa el cierre del legajo
(`/api/brd/ebr/<id>/cerrar-acondicionamiento`), y por eso reclama el libro mayor
`produccion_checklist.consumido_at` con CAS antes de mover nada. El contrato completo, con el
borde del orden inverso y la semántica de `sin_libro_mayor`, vive en **INV-24 de
`CONTRACT_brd.md`** — se documenta allá porque la regla es del batch record, no del kardex.

Antes descontaba directo (Salida cruda + `UPDATE stock_actual`), sin libro mayor, sin CAS y sin
`audit_log`: registrar el acondicionamiento acá **y** cerrar el legajo sacaba el mismo envase dos
veces. Reproducido por los dos endpoints: 2 salidas y 200 unidades donde había 100.

La respuesta ahora devuelve `descuentos`, `saltados` y `sin_libro_mayor`, y el descuento deja
`audit_log` (`ACONDICIONAMIENTO_DESCONTAR_MEE`). Tests:
`tests/test_acondicionamiento_doble_descuento.py` y `tests/test_demo_camina_envasado_y_acond.py`
(los dos en el gate).

### INV-13 · El stock VENDIBLE de un lote se crea por UN solo camino, y una vez (18-ago-2026)

`stock_pt` es el stock por SKU que alimenta despachos y el cruce con Shopify. Hay **dos
puertas** por las que un lote se vuelve vendible y las dos escriben por el MISMO helper:

| Puerta | Quién | Marca de idempotencia |
|---|---|---|
| Pantalla de Liberaciones (`PATCH /api/liberacion/<id>` estado=Liberado) | Calidad | `[lib#<id>]` |
| Firma del Director Técnico en el legajo (`POST /api/brd/ebr/<id>/liberar`) | DT | `[ebr#<id>]` |

**Reglas duras:**

1. **Un solo escritor: `inventario.crear_stock_pt`.** Ningún endpoint arma su propio
   `INSERT INTO stock_pt` desde una liberación. Dos copias divergen el día que alguien
   toque una, y entonces el mismo lote entra al stock con reglas distintas según por
   dónde se liberó (M3/M99).
2. **La idempotencia se ancla al ACTO, no al par (sku, lote).** Con esa llave, una
   segunda liberación PARCIAL legítima del mismo lote y el mismo SKU se saltearía en
   silencio -- y perder unidades es peor que duplicarlas, porque no se ve (M134/M80).
3. **`liberacion_update` va con CAS** (`WHERE id=? AND estado NOT IN ('Liberado','Rechazado')`
   + `rowcount`). Sin eso, tres clics creaban TRES filas de stock vendible del mismo lote
   y un lote RECHAZADO por Calidad se volvía a liberar con un clic (reproducido 18-ago).
   Un stock que no existe no da ningún síntoma: se vende, y la falta aparece en el despacho.
4. **Sólo la fase que CIERRA el lote crea producto terminado.** Si al lote le queda
   envasado o acondicionamiento, crear stock ahí sería vender un granel. La regla vive
   en `brd._hay_fase_posterior_lote`, que usan el completar y el liberar.
5. **El SKU no se adivina.** Sale del registro de acondicionamiento o de la presentación,
   y sólo si es inequívoco. Lo que no cruza se DECLARA (`sin_resolver`) en la respuesta y
   en el audit: un lote entrando al stock del producto equivocado tampoco da error, se
   vende (M19/M137).

Guards: `tests/test_liberar_crea_stock_vendible.py` (en el gate).

---

## INV-12 · Cuadre rápido: una acción por lote (21-ago-2026)

`POST /api/inventario/cuadre` deja UN lote en lo que hay físicamente, en el mismo request, y la
pantalla es `/planta/cuadre` (enlazada desde Bodega MP). Es la puerta para cuadrar parado frente
al estante; el conteo cíclico sigue siendo el proceso para el conteo programado.

Invariantes:
1. **El movimiento va con cantidad > 0** y con un tipo VÁLIDO: `Entrada`/`Salida`/`Ajuste` son
   los únicos que `trg_mov_tipo_valido` acepta. Sumar es `Ajuste` (el canónico lo cuenta como
   entrada), restar es `Salida`. `'Ajuste +'`/`'Ajuste -'` NO son tipos, aunque el lector del
   stock los entienda.
2. **Conserva el estado del lote**: un cuadre sobre un lote en cuarentena lo deja en cuarentena.
   Ajustar no es liberar.
3. **Conserva el vencimiento y la ubicación**: sin fecha, el FEFO trataría el saldo como eterno.
4. **Diferencia cero no escribe kardex**, pero deja `CUADRE_CONFIRMA` en el rastro: confirmar que
   un lote cuadra es información, no un no-evento.
5. **Dar de alta un (material, lote) que el sistema no tenía exige motivo** — una entrada sin
   documento debe decir de dónde salió.
6. **Token por acción** (`oc_recepcion_dedup`), reclamado ANTES de calcular la diferencia: un
   doble clic devuelve 409 y no ajusta dos veces.

Guard: `tests/test_cuadre_inventario.py` (9 casos, en el gate).

### INV-12b · Ubicaciones: unificar y ubicar lo suelto (21-ago-2026)

- `GET /api/inventario/ubicaciones-agrupadas` agrupa las estanterías que son la MISMA escrita
  distinto (sin acentos, sin mayúsculas, sin plural final; **los números no se tocan**: `10` y
  `1` son estanterías distintas).
- `POST /api/inventario/unificar-ubicacion` las deja con un solo nombre. **Rechaza unificar dos
  ubicaciones que no normalizan igual**: eso movería material de un estante a otro sin que nadie
  lo haya movido. No toca cantidades ni lotes, y queda auditado con las variantes movidas.
- `GET /api/inventario/cuadre-lotes?est=X` trae los lotes de esa estantería **más los lotes SIN
  ubicar de esos mismos materiales**, marcados `sin_ubicar`: si sólo se listara lo ubicado, quien
  cuadra el estante no se entera de que ese material tiene otro lote suelto. Con `est=` vacío
  devuelve la cola completa de lo que no está en ningún lado.
- Ubicar un lote suelto reusa `PATCH /api/lotes/<material>/<lote>/ubicacion` (no se duplicó).

Guard: `tests/test_cuadre_inventario.py`.

---

## INV-15 · La fecha de vencimiento del kardex vive en **ISO** (`YYYY-MM-DD`)

**Desde el 21-ago-2026** (mig 443). `movimientos.fecha_vencimiento` y
`movimientos_mee.fecha_vencimiento` se guardan SIEMPRE en ISO. Una fecha en texto
(`26-Dic-2026`) no da error y hace dos cosas a la vez, las dos silenciosas:

- el cálculo del stock distribuible compara con `date(fecha_vencimiento)`, que ante un texto
  devuelve **NULL** → la comparación es falsa → **el lote se cae del stock** y el FEFO no lo
  consume. En producción eso fue *"PROPYLENE GLYCOL · disponible 0g · FALTA 4000g"* con 29 kg
  VIGENTES en bodega;
- `job_marcar_vencidos` usa el mismo `date(...)`, así que un lote **realmente vencido** con la
  fecha así **nunca se marca**: el control de vencimiento deja de sonar sin avisar.

**Reglas:**

1. Todo punto de entrada que reciba la fecha del usuario la pasa por
   **`audit_helpers.fecha_iso`** antes de escribirla (recepción manual, recepción de OC, F01,
   liberación de Calidad, corrección de lote, ajuste masivo de admin).
2. `fecha_iso` acepta lo que la gente y los Excel escriben (`26-Dic-2026`, `5-Dic-2025`,
   `26/12/2026`, `26-12-2026`, ISO con o sin hora) y **devuelve `''` si no la puede leer**:
   una fecha de vencimiento **no se adivina** (inventarla deja entrar material vencido).
3. Un lote con fecha **ilegible** se muestra como RETENIDO con ese motivo, nunca como usable:
   si el FEFO no lo va a consumir, la pantalla no puede prometerlo (M5).
4. `GET /api/inventario/fechas-vencimiento-raras` lista lo que quedó fuera de ISO (read-only,
   con el stock que cada uno esconde). El vencimiento de una **factura de proveedor** es otro
   dominio y no entra acá.

5. **El orden FEFO pone el lote SIN FECHA al final.** `COALESCE(col, '9999-12-31')` NO alcanza:
   la columna es `TEXT DEFAULT ''`, así que un lote sin fecha guarda la **cadena vacía y no
   NULL**, y la vacía ordena antes que cualquier fecha. Con el COALESCE a secas se gastaba
   primero el material que nunca vence y el que caduca el mes entrante se quedaba hasta
   vencerse. Va **`COALESCE(NULLIF(TRIM(CAST(col AS TEXT)), ''), '9999-12-31')`**, y vale para
   los 7 sitios que ordenan lotes por vencimiento -- incluidas las VISTAS, porque si la pantalla
   ofrece un orden y el kardex descuenta otro, el operario baja del estante el lote equivocado.
6. **La PANTALLA, el GATE de arranque y el DESCUENTO deciden lo mismo sobre cada lote.** Los
   tres excluyen los 6 estados no producibles (con `UPPER`) y aplican la guarda de vencimiento
   por FECHA aunque el cron todavía no haya marcado el lote (M25). Un lote que uno de los tres
   trate distinto produce o bien *"disponible 0g"* junto a *"lotes a usar"*, o bien la forma
   peligrosa: el gate deja arrancar y el descuento no encuentra de dónde sacar.
7. **El vigía diario lo hace visible.** `job_salud_materias_primas` (7:40) lleva la firma
   `fecha_vencimiento_que_el_motor_no_lee` entre las **graves**: sin ella, un lote con la fecha
   en texto es invisible por las dos puntas (no cuenta como stock y el cron no lo puede vencer).

Guards: `tests/test_fecha_vencimiento_iso.py` (8 casos · incluye la migración probada con datos
sembrados, el límite del cron declarado y un barrido del fuente con piso de medición) y
`tests/test_cadena_descuento_coherente.py` (la invariante de los tres caminos + el orden FEFO).
Los dos en el gate.

---

## INV-16 · El rótulo de ingreso de envase ES el formato **COC-PRO-002-F06**

**Desde el 21-ago-2026.** `/rotulo-recepcion-mee/...` y `/rotulos-recepcion-mee?mov=...`
imprimen el formato oficial *Identificación de Material de Envase* (versión 02, vigencia
21-Jul-2026 a 20-Jul-2029). Antes citaba **COC-PRO-002-F04**, que es otro formato, y sin
versión, página ni vigencia.

1. **El bloque de control sale de UNA constante** (`F06_CONTROL`) y el encabezado tiene las
   tres zonas del oficial: logo | `FORMATO` + título | código/versión/página/vigencia. Dos
   rótulos con su propio bloque divergen, y el día que Aseguramiento libere la versión 03 uno
   seguiría diciendo 02 -- los dos con cara de oficiales (M251).
2. **Los campos son los del formato**: nombre del insumo, tipo (las **dos** casillas
   `MATERIAL DE EMPAQUE` / `MATERIAL DE ENVASE`, nunca la de materia prima, que tiene su propio
   formato), código interno, lote, cantidad, proveedor, fecha de recepción, **fecha de
   análisis**, observaciones, estado, realizado por y aprobado por.
3. **La fecha de análisis sale del hecho registrado** (`mee_cajas_disposicion.dispuesto_at_utc`,
   anclada a Colombia · M24). Si nadie revisó la caja va **vacía** para llenarla a mano: poner
   la fecha de impresión sería fechar un análisis que no ocurrió.
4. **Un rótulo POR CAJA.** `?mov=<id>` usa las cajas declaradas al recibir (`n_cajas`,
   `unidades_por_caja`) y numera *"Caja N de M"*; sin cajas declaradas imprime uno. **Todo botón
   que imprima el rótulo de una recepción manda el MOVIMIENTO**, no el código y la cantidad --
   con eso imprimía uno solo y las demás cajas quedaban sin identificar.
5. **Las marcas del SISTEMA no se imprimen** (`_MARCAS_SISTEMA_OBS`). Son correctas en la base
   pero en el cartón se leen como una nota de quien recibió. Se quitan sólo las declaradas:
   filtrar cualquier corchete borraría lo que la gente escribe entre corchetes a propósito.
6. **Cabe en la etiqueta**: medido con las reglas del `@media print` aplicadas, **96,8 mm de
   alto sobre 100 y cero desbordes**. Antes daba 131 mm, o sea que cada rótulo se partía en dos
   etiquetas. El alto depende de que el bloque de control conserve su ancho fijo y su tamaño.

7. **Está hecho para la térmica de 10x10.** Medido en el navegador con las reglas del
   `@media print` aplicadas y con el PEOR caso (nombre de 65 caracteres, lote largo,
   observación de tres renglones): **95,3 mm de alto sobre 100, 4,7 mm de margen, cero
   desbordes y cero celdas solapadas**. Antes daba **137,7 mm**: cada rótulo se comía dos
   etiquetas. Lo que sostiene esa medida:
   - **`print-color-adjust: exact`** -- sin él el navegador descarta los fondos y el chip del
     estado marcado se imprime sin relleno (M123);
   - **el logo BINARIZADO** (`_rotulo_logo_termico`, que reusa el binarizador del F02): la
     térmica es de 1 bit y cada gris lo resuelve con una trama de puntos, así que un PNG con
     antialiasing sale rayado (M256). Si no se puede convertir, cae al logo normal;
   - **las etiquetas sin fondo gris**: en 1 bit un `#e6e6ea` a 5pt es ruido de puntos debajo
     del texto. La jerarquía se hace con peso y caja;
   - **el nombre del insumo se ESCALA** según su largo (cuatro escalones, clases `n1`..`n4`),
     nunca se trunca: un rótulo de identificación cortado no identifica (M203);
   - **el ancho de las columnas**: con las etiquetas más anchas, "CAFARCOL" se partía en
     "CAFARC / OL" y la fecha en dos renglones.
8. **El encabezado sale de `_encabezado_formato(logo, ctl)`**, con el bloque de control por
   parámetro: sumar otro formato es una constante más, no un segundo encabezado copiado.

⚠ Pendiente de Aseguramiento: el rótulo de ingreso de **materia prima** cita `COC-PRO-002-F07`
**sin versión, página ni vigencia**, y el de **identificación de equipo** no cita formato
alguno. No se completan inventando los datos -- una vigencia inventada en un documento regulado
es peor que no tenerla (M19/M93).

Guards: `tests/test_rotulo_envase_f06.py` (14 casos, en el gate · incluye el barrido de
`COALESCE` con el fallback muerto y sus excepciones enumeradas, el escalado del nombre y las
reglas que sostienen los 95,3 mm).

## INV-28 · El desglose por CAJAS de un envase se DERIVA del kardex (21-ago-2026)

Sebastián: *"si agrego 37 cajas, ¿cómo sé que hay 37 y cuántas hay en cada una? ¿allí aplica
FEFO? ¿va diciendo qué caja coger, cuáles usamos, en cuáles quedan alguna cantidad?"*.

**Invariante dura: `sum(saldo de cada tanda) == saldo del código`.** Es la razón de que el
desglose se derive en vez de guardarse: si viviera aparte, divergiría del kardex el día que
alguno de los **veinte** escritores de `movimientos_mee` se olvide de actualizarlo, y ahí la
pantalla diría una cosa y el descuento otra.

**Endpoints**
- `GET /api/mee/<codigo>/cajas` — read-only. Devuelve `saldo_total`, `tandas[]` (cada una con
  `cajas_completas`, `suelto`, `caja_abierta`, `sin_desglose`, `bajas[]`), `retenidas[]`,
  `tomar_de` e `instruccion`. Cualquier autenticado.
- `POST /api/mee/<codigo>/merma-caja` — da de baja material de UNA tanda.
  Body `{mov_id, caja?, cantidad, motivo, token?}`. `_require_planta_write`. Auditado
  (`BAJA_CAJA_MEE`). Idempotente por token contra `oc_recepcion_dedup` (numero_oc `'BAJA-MEE'`).

**Helper canónico:** `mee_estado_por_cajas(c, cod)` en `inventario.py`. Todo consumidor le pide
a él; nadie recalcula el desglose (dos cuentas del mismo hecho divergen · M5/M99).

**Reglas que NO se relajan**
1. **FEFO por tanda** con `NULLIF` en el orden: `fecha_vencimiento` es `TEXT DEFAULT ''`, así que
   un `COALESCE` pelado consumiría PRIMERO la tanda sin fecha, o sea al revés del FEFO (M263).
2. **El saldo canónico usa la MISMA regla que `_get_mee_stock`**: una Entrada en CUARENTENA o
   RECHAZADO no es stock, un `Ajuste` cuenta con su signo (M26).
3. **Las excepciones NO siguen FEFO.** Una caja rota sale de SU tanda: se ancla en
   `mee_cajas_disposicion` y se descuenta de su tanda ANTES de repartir el resto. Sin esa fila,
   la Salida existe igual y el reparto se la cobra a la tanda más vieja.
4. **La llave de una baja es NEGATIVA.** `mee_cajas_disposicion` tiene `UNIQUE(mov_id, caja)` y
   Calidad ocupa 1..N con sus propias filas: un número real chocaría con el de Calidad de esa
   caja, y dos bajas de la misma caja entre sí (son dos hechos legítimos). El número declarado va
   en el `motivo`, que es donde se lee.
5. **`dispuesto_at_utc` va VACÍO en una baja.** Esa columna alimenta la **fecha de análisis del
   rótulo F06**, que es un formato regulado: una baja de bodega no es un análisis de Calidad y no
   puede firmarle la fecha (M258). El cuándo vive en `audit_log`.
6. **Lo que ninguna tanda explica se DECLARA** (`sin_atribuir`), nunca se reparte: cuadrar el
   número inventando de dónde salió el material es peor que un desglose incompleto (M124/M148).
7. **Una entrada sin `n_cajas` se marca `sin_desglose`**, no se muestra en cero: todo el
   histórico entró así y un 0 se leería como *"no quedan cajas"* (M236).
8. **Se valida ANTES de reclamar el token.** Si un rechazo lo quemara, quien corrige la cantidad
   y reenvía recibiría *"ya se registró"*, que es mentira y lo deja sin poder hacerlo.

Tests: `tests/test_cajas_fefo_envases.py` (en el gate).

## INV-29 · El bloque de control de un formato sale de UN registro (21-ago-2026)

Aseguramiento declaró no negociable que todo formato impreso lleve **Código · Versión · Página ·
Vigencia**: es la evidencia de que el registro se llenó en la versión vigente (M251). El rótulo
de ingreso de MP sólo decía el código y la fecha de impresión.

**Fuente única:** tabla `formatos_control` (mig 444) + `audit_helpers.formato_control(c, codigo)`
y `formato_control_html(...)`. `control_vigente_campos(c, codigo)` devuelve SÓLO versión / página
/ vigencia, para poder enchufar el registro a un formato que ya imprime **sin tocarle el título
ni el layout** (cambiar lo que imprime un documento regulado no se hace de pasada · M105/M251b).

- El rótulo de MP (`COC-PRO-002-F07`) arma su bloque **una vez por hoja**, no por recipiente: una
  tanda son 40 rótulos (M43).
- `F02_CONTROL` y `F06_CONTROL` siguen en el código como **respaldo** (si la migración no corrió,
  el rótulo no sale sin identificar) pero lo que esté cargado en la tabla MANDA.
- **Lo que falta se DECLARA en el papel** (`ctrl-falta`, recuadro negro: en térmica un gris no
  marca · M123). No se inventa una versión: un dato de control fabricado en un documento regulado
  es peor que su ausencia, porque nadie lo corrige (M19/M242).

**Pantalla:** `/admin/formatos-control` + pestaña *Control de formatos* en Aseguramiento.
Gate = Aseguramiento ∪ Calidad ∪ Dirección Técnica ∪ admin (se pregunta por la CAPACIDAD, no por
la lista de un puesto · M210/M257). Cambiar una versión queda auditado con el valor previo
(`FORMATO_CONTROL_ACTUALIZAR`): ante un rótulo con la versión equivocada la pregunta es *cuál
decía antes* (M175).

⚠ **Abierto para Aseguramiento:** dos documentos distintos citan `COC-PRO-002-F07` — el rótulo de
ingreso de MP y la hoja *Controles en proceso* del cuaderno de producción (`programacion.py`).
Cuál de los dos está mal lo decide el dueño del documento, no el código (M19/M251b).

Tests: `tests/test_formatos_control_unico.py` (en el gate).

## INV-30 · El rótulo de materia prima ES el formato COC-PRO-002-F05 (22-ago-2026)

Sebastián mandó el Excel oficial: **COC-PRO-002-F05 · IDENTIFICACIÓN DE MATERIAS PRIMAS**,
versión 02, página 1 de 1, vigente 21-Jul-2026 → 20-Jul-2029. El rótulo citaba **F07**, o sea el
código de otro documento. Con esto queda **cerrado** el conflicto que INV-29 dejaba abierto: el
que reclamaba el F07 era este rótulo, y no le correspondía.

**Campos (comparados uno a uno contra el Excel · M264).** Salen del sistema: nombre comercial,
INCI, código interno, lote, cantidad, proveedor, fecha de recepción, vencimiento, ubicación.
Salen **en blanco con su etiqueta**, porque el formato se imprime para llenarse y ese dato no
vive en ninguna columna: **forma química**, fecha de análisis, observaciones, estado (sticker),
realizado por y **verificado por**.

- La etiqueta es parte del documento: dice **CÓDIGO INTERNO** y **VERIFICADO**, no "Código MP" ni
  "Revisado por".
- **No lleva "tipo de insumo"**: éste ES el formato de materias primas, así que ofrecer tres
  casillas invita a marcar la equivocada (M264). El de envases (F06) sí tiene sus dos.
- El encabezado usa `_encabezado_formato` -- las **tres zonas** del formato oficial, el mismo
  helper que el F06 (M1). El bloque de control sale de `_f05_control_vigente()`, que lo pide al
  registro único (INV-29).

**Cabe en UNA etiqueta térmica, y se mide IMPRIMIENDO.** Chrome a PDF respeta el `@page` del
CSS, así que **contar páginas mide el resultado**: una hoja que da dos páginas es el defecto.
Medido así, el rótulo daba 115mm sobre 100 y **se venía partiendo en dos desde antes** (el árbol
sin los cambios daba lo mismo · M110). Lo que lo resolvió: las tres zonas usan el ancho en vez
del alto, y el nombre se **escala** (`n1..n4`) en vez de cortarse (M203). Verificado con el peor
caso: nombre de 65 caracteres, INCI de mezcla, lote y proveedor largos.

Tests: `tests/test_formatos_control_unico.py`, `tests/test_rotulos_en_bloque.py` (en el gate).

## INV-31 · El operario reparte a mano de qué lote sale cada gramo (22-ago-2026)

Sebastián lo eligió con esas palabras. Un reparto manual sobre un kardex regulado es una puerta
nueva al inventario, así que:

**Cadena:** `POST /api/planta/fabricacion/crear-iniciar` con `reparto_lotes` = `{codigo_mp:
{lote: gramos}}` → `prog_iniciar_produccion(reparto=)` → `_descontar_mp_produccion(reparto=)` →
`_distribuir_con_reparto(...)`. Si el reparto se quedara en la pantalla, el kardex descontaría
por FEFO y la persona creería que pesó de los lotes que eligió (M5/M109).

**Punto único:** `_lotes_disponibles_fefo(c, codigo_mp)` — la consulta de lotes consumibles que
**el FEFO y el reparto COMPARTEN**. Si fueran dos, el día que una se ajuste (un estado más, la
guarda de vencimiento por fecha) la otra dejaría pasar lo que la primera bloquea, y el reparto
sería la puerta de atrás para consumir lo que Calidad retuvo (M1/M3/M31).

**Lo que se rechaza, con su motivo y sin caer a FEFO en silencio:** un lote que no está entre los
disponibles (`REPARTO_LOTE_NO_USABLE`), más gramos de los que ese lote tiene
(`REPARTO_MAYOR_QUE_LOTE`) y una suma que no da lo que la fórmula pide (`REPARTO_NO_CUADRA`) —
un reparto que no cuadra se ve resuelto y con eso se descuenta (M195).

**Viaja con el POST del acto de producir, sin tabla intermedia**: vale para ESA fabricación, y
guardarlo aparte crearía un estado que alguien después lee como preferencia fija.

Tests: `tests/test_reparto_manual_lotes.py` (en el gate).

## INV-32 · El cuadre dice cuál ya se revisó, y qué no se vio (22-ago-2026)

*"No sé cuáles revisé y cuáles no"* · *"ya hice toda la estantería 10 y no sé qué me faltó"*.

El contador decía **0 de 54** con la estantería entera declarada, porque sumaba una variable del
navegador. **La verdad ya estaba en el `audit_log`**: cada declaración escribe
`CUADRE_INVENTARIO` (ajustó) o `CUADRE_CONFIRMA` (coincide). `GET /api/inventario/cuadre-lotes`
lo lee y devuelve por lote `revisado_hoy`, `revisado_por`, `revisado_hora`, `revisado_como`, más
`revisados_hoy` / `falta_revisar` / `revisado_lectura_fallo`.

- **Sólo lo de HOY** (día Colombia; el audit guarda UTC, así que se convierte · M24): un lote
  declarado hace un mes contaría como revisado hoy y el conteo mediría otra cosa (M174).
- **Confirmar que coincide cuenta como revisado** aunque no escriba kardex; si sólo contaran los
  ajustes, el lote que estaba bien quedaría pendiente para siempre.
- **UNA consulta** para toda la estantería, no una por fila (M43).
- Un fallo de lectura se DECLARA: *"no pude mirar"* y *"no revisaste nada"* son cosas distintas
  (M100).
- En la pantalla: la fila revisada se ve distinta, hay filtro **"ver sólo lo que falta"**, y el
  botón **"Acabé"** lista lo que nadie tocó y lo deja resolver ahí mismo (M121). Declarar desde
  esa lista lo saca de ella (M129).

⚠ **Los tests usan un material propio por caso**: el `audit_log` es append-only por trigger, así
que no se puede limpiar entre tests y el rastro de uno contamina al siguiente (M102/M103).

Tests: `tests/test_cuadre_que_falta_revisar.py` (en el gate).

## INV-33 · El informe de cierre del inventario (22-ago-2026)

*"Que quede algo al final, como informe: lo que se encontró y lo que no, así les pido que me
busquen esas específicas, para cerrar el inventario full"*.

`GET /api/inventario/cuadre-informe?desde=&hasta=` (default hoy) + pantalla
`/planta/cuadre-informe`, enlazada desde el cuadre.

**De dónde sale cada cosa:**
- lo **declarado** (coincide · ajustado · no está · apareció) sale del `audit_log`. Lo que se dio
  por no encontrado quedó en CERO y desapareció del inventario, así que **del stock actual no se
  puede reconstruir**: el rastro es la única fuente para eso;
- lo **sin revisar** sale del inventario vivo menos lo declarado;
- `sistema` (lo que se creía tener) se lee del **`antes`** del audit (`{'stock': ...}`), no del
  `despues`. Suponerlo ahí devolvía 0, y un cero se lee como un hecho (M220/M245).

**`a_buscar`** junta lo no encontrado y lo que nadie miró: los dos mandan a la misma acción, y
separarlos obliga a mirar dos veces. Es la lista que se imprime o se copia para el equipo.

**El rango es un parámetro** porque un inventario completo toma varios días; con default hoy, un
informe de un conteo de tres días diría que falta casi todo (M174).

⚠ **El informe NO cierra nada**: dar un lote por perdido es un ajuste que decide una persona, no
el efecto secundario de pedir un reporte (M19). Un guard verifica que pedirlo dos veces no mueva
un gramo.

Tests: `tests/test_cuadre_que_falta_revisar.py` (en el gate).
