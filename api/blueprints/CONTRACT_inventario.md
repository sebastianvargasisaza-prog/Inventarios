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
