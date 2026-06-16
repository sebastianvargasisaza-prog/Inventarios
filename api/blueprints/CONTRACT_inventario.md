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
- `_mee_stock_real(c, codigo_mee)` · stock canonical desde SUM(movimientos_mee)
- `_pendiente_en_compras_g` (import desde compras) · dedup cola SOLs+OCs

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
