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

## Endpoints que expone

- `GET  /api/maestro-mps` · listado MPs
- `POST /api/maestro-mps` · crear MP (admin)
- `GET  /api/maestro-mps/export-lista-simple[?fmt=xlsx|csv]` · default XLSX
  nativo (Excel en español rompe CSV con coma · usar XLSX o `?fmt=csv` con
  `;`). 4 columnas: codigo · nombre comercial · nombre INCI · tipo · solo
  activas · NO expone precio / proveedor / stock (uso de planeación)
- `GET  /api/proveedores-unicos` · datalist autocomplete
- `GET  /api/lotes` · listado lotes MP con stock > 0 (paginación opcional
  via `?limit=N&offset=N`, `?solo_criticos=1` para vencidos/<30d)
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
  inverso con `estado_lote='ANULADO'` + audit_log ANULAR_RECEPCION_MP.
  Idempotente (segunda llamada → 409). Si la recepción venía de OC,
  descuenta `cantidad_recibida_g` de `ordenes_compra_items`.
  Sebastián 20-may-2026 fix #8.
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
