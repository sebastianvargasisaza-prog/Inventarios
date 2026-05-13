# Auditoría cimientos Planta · 13-may-2026

> Propósito: antes de seguir construyendo features (vista MyBatch, refactor
> admin.py, mejoras Planta), Sebastián pidió validar que los datos que
> hoy muestran las pantallas son **REALES** — no caches paralelas, sumas
> correctas, descuentos atómicos, Shopify confiable.
>
> Conclusión: cimientos sólidos. 1 área que necesita verificación
> manual (cron Shopify). 0 bugs nuevos detectados.

---

## 1 · Mapa: pantalla → dato → fuente

| Pantalla | Ruta | Quién la usa | Dato que muestra | Endpoint API | Tabla fuente | Invariante |
|---|---|---|---|---|---|---|
| Bodega MP | `/inventario` | Mayerlin, Luis Enrique | Stock por MP por lote | `GET /api/inventario` + `GET /api/bodega-mp` | `movimientos` | stock = SUM(movimientos) |
| Bodega MEE | `/mee` | Mayerlin | Stock material empaque | `GET /api/mee` | `maestro_mee.stock_actual` + `movimientos_mee` (audit) | persistido pero con drift detector |
| Programación | `/programacion` | Luis Enrique, Sebastián | Cronograma + faltantes MP | `GET /api/programacion/resumen` | `produccion_programada` (espejo Calendar) + `_get_mp_stock` | Calendar = fuente de verdad |
| Prioridad agotamiento | `/admin/animus-prioridad` | Sebastián, Daniela | Qué PT se está agotando, qué hay que producir | `GET /api/admin/animus-prioridad-agotamiento` | `sku_velocity` (Shopify orders 60d) + `_resolved_stock_por_sku` | CC>SHOPIFY · usa Available |
| Mp-alcanza | `/programacion` (tab) | Luis Enrique | ¿Las MPs alcanzan para 60/90/180d? | `GET /api/programacion/mp-alcanza-multi` | `formula_items` × demand vs `_get_mp_stock` | Pre-check antes de iniciar |
| Realidad zero-error | `/admin/realidad-cero-error` | Sebastián | Score consolidado integridad (formula/catálogo/producciones/ingresos/ajustes) | `GET /api/admin/validar-planta` | 5 secciones agregadas | Score 0-100 · ≥95 healthy |
| Dashboard ejecutivo | `/modulos` + `/hub` | Sebastián | KPIs caja/ventas/producción | varios endpoints | varios | — |

**Las MISMAS tablas alimentan TODAS las pantallas.** No hay "vista A" con
dato distinto a "vista B" para el mismo concepto · todo va al mismo
kardex `movimientos`.

---

## 2 · Stock MP · invariante VERIFICADO

**Fórmula canónica:** `_get_mp_stock(conn)` en `programacion.py:605`

```python
SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA')
         THEN cantidad ELSE -cantidad END)
FROM movimientos
GROUP BY material_id
```

✅ **Sin cache paralela:**
- NO existe `maestro_mps.stock_actual_g` (el bug histórico que se eliminó)
- Cada `GET /api/inventario` recalcula desde `movimientos`

✅ **2-pass para sinónimos:** si el mismo `material_id` (ej `MP00121`)
aparece en kardex con 2 nombres distintos (`PROPYLENE GLYCOL` vs
`PROPILENGLICOL`), el stock se agrupa por material_id canónico · indexa
los 2 nombres al mismo total. **NO se split-cuenta.**

✅ **Estados de lote** (mig 97 trigger BD):
- `VIGENTE` (default · disponible para producir)
- `CUARENTENA` (recibido pendiente QC · stock visible pero NO descuenta)
- `VENCIDO` / `RECHAZADO` / `AGOTADO` (no disponible)
- Helpers separados: `stock_mp_total` (incluye cuarentena) vs
  `stock_mp_disponible` (solo VIGENTE)

🟢 **No detectado:** cero displays que mientan sobre el stock real.

---

## 3 · Stock MEE · paralelo pero auditado

**Caso especial documentado:** MEE SÍ persiste `stock_actual` en `maestro_mee`
(O(1) para lookups frecuentes) ADEMÁS de tener audit trail completo en
`movimientos_mee`. Para evitar drift:

- Función única `aplicar_movimiento_mee(c, codigo, tipo, cantidad)` que
  hace ambos INSERT movimiento + UPDATE stock_actual atómicos
- Drift detector: `stock_mee_drift(c, codigo)` compara persistido vs
  calculado · si ≠ 0 hay bug operacional
- Endpoint `/admin/validar-planta §5 AJUSTES` corre el drift en todos
  los MEE
- **Bug B4 cazado anoche** (mee_import_bulk perdía signo) ya fixed +
  golden path · no se repite

🟢 **Verificado.** MEE no es punto débil ahora.

---

## 4 · Descuento al iniciar producción · ATÓMICO

**Flujo `POST /api/programacion/programar/<id>/iniciar`** (programacion.py):

```
1. Auth check
2. SELECT pp WHERE id=? · lock por inventario_descontado_at='' guard
3. _descontar_mp_produccion(c, evento_id, user):
   a. Pre-check: ¿tiene fórmula? · si no → return 422 SIN_FORMULA
   b. Pre-check: ¿hay stock suficiente cada MP? · si no → 422 SIN_STOCK
   c. FEFO por MP: SELECT lotes WHERE estado='VIGENTE' ORDER BY fv ASC
   d. INSERT movimientos tipo='Salida' por cada lote consumido
   e. UPDATE pp SET inventario_descontado_at=datetime('now')
4. UPDATE pp SET inicio_real_at=datetime('now')
5. UPDATE areas_planta SET estado='ocupada' WHERE id=pp.area_id
6. INSERT audit_log INICIAR_PRODUCCION (con MPs consumidas detalladas)
7. Hook auto-EBR (NON-FATAL si falla)
8. COMMIT
```

✅ **Idempotencia por `inventario_descontado_at`:** segundo click del
operario verifica WHERE `inventario_descontado_at IS NULL` · si ya está
seteado, retorna `{ok: True, ya_iniciada: True}` sin descontar de nuevo.

✅ **Atomicidad:** todo en una transacción SQLite WAL · si crash en
paso 3d, rollback completo · stock kardex queda intacto.

✅ **Pre-check antes de tocar:** ningún INSERT a movimientos hasta que
estamos seguros que HAY stock · no quedan "Salidas parciales".

🟢 **Audit profundo anoche (B1-B6) cubrió 6 bugs** en este flujo.

---

## 5 · Shopify sync · usa Available con fallback

**`_sync_shopify_orders()` en programacion.py:**

1. Primero pide `inventory_levels.json` que SÍ trae `available` (= On hand - Committed)
2. Si esa API call falla → fallback a `inventory_quantity` (On hand) del primer endpoint
3. Response incluye flag `used_available: bool` para que el frontend muestre el estado

✅ Fix completo desde commit `a65a5ce` (12-may-2026 · "feat(shopify-sync): usar AVAILABLE en lugar de ON HAND fix #D").

⚠️ **Pendiente verificar manualmente:**
- ¿Existe un cron Render que corra esto cada día? (commit `6d819a6` dice
  "feat(cron): sync stock Shopify automatico diario 5:30am Colombia").
  Confirmar que está activo · si no, el plan de cada día arranca con
  data de ayer.
- Sebastián: abre Render → Cron Jobs → buscar uno con `shopify-sync` o
  similar. Si no está → agregarlo.

🟢 **Lógica correcta** · solo verificar que el cron está vivo.

---

## 6 · Códigos · FK trigger activo

Mig 98 (10-may-2026) instala trigger `trg_fi_material_id_fk` que
**bloquea con RAISE(ABORT)** cualquier `INSERT INTO formula_items` con
`material_id` que no exista en `maestro_mps` activo. No puede haber
huérfanos a futuro.

```sql
CREATE TRIGGER trg_fi_material_id_fk
BEFORE INSERT ON formula_items
FOR EACH ROW
WHEN NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != ''
 AND NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp = NEW.material_id AND activo = 1)
BEGIN
  SELECT RAISE(ABORT, 'material_id no existe en maestro_mps activo');
END
```

✅ **Otros UNIQUE / FK activos:**
- `formula_headers.producto_nombre UNIQUE`
- `maestro_mps.codigo_mp UNIQUE`
- `formula_headers.codigo_pt UNIQUE` parcial (mig 117 nueva)
- `ebr_ejecuciones.numero_op UNIQUE` parcial (mig 117 nueva)
- `ebr_ejecuciones.lote UNIQUE`
- `audit_log` append-only (mig 105 trigger)
- `e_signatures` append-only (mig 107 trigger)
- MBR aprobado inmutable (mig 109 triggers)
- EBR liberado/rechazado inmutable (mig 111 triggers)
- IPC specs de MBR aprobado inmutables (mig 112 triggers)
- Cleaning log post-QC inmutable (mig 113 trigger)

🟢 **Defensa fuerte.** No solo en código, también en motor SQLite.

---

## 7 · ¿Qué hace falta verificar a mano?

Tres puntos · ~10 min en total:

### Punto 1 · Auditoría /admin/validar-planta corre limpia hoy
- Abrir `https://app.eossuite.com/admin/realidad-cero-error`
- Verificar score ≥ 95 · si hay flags rojos, mostrármelos
- Razón: si score es bajo, hay datos huérfanos pre-mig 98 que no se
  limpiaron · el trigger evita NUEVOS huérfanos pero no fixea viejos

### Punto 2 · Cron Shopify activo en Render
- Render dashboard → buscar "Cron Jobs" del servicio inventarios-0363
- Debe haber un cron 5:30am Colombia que pega
  `/api/admin/cron-sync-shopify-stock` o similar
- Si NO existe, agregarlo

### Punto 3 · Spot-check de un producto real
- Tomar 1 SKU activo Animus (ej Suero Antiaging Hydra)
- En Shopify ver `Available` (no On hand)
- En `/admin/animus-prioridad` ver "stock total" del mismo SKU
- Deben coincidir ± 1 unidad (puede haber pipeline 7d en vuelo)

---

## 8 · Decisión para próximas sesiones

Con cimientos validados, las opciones son:

**A · Construir vista del operario en Planta** (lo que tu intuición pidió)
- Pantalla por operario · ve qué le toca hoy
- Botones grandes para reportar inicio/fin/pesaje
- Integra el BRD/EBR de forma transparente · no hay "modo BRD separado"

**B · Refactor admin.py** · empezar a partir el monolito (35h, va para varios días)

**C · MyBatch real** · esperar export de Daniela primero (no hace falta tocar código antes)

**D · SGD review** (lo que mencionaste · revisar qué dice el SGD sobre BRD físico/digital)

Mi recomendación: **A · vista operario integrada con BRD invisible**.
Es lo que más mueve la aguja para Mayerlin / Luis Enrique / Sebastián
Murillo en su día a día y aprovecha 100% el trabajo de Fase 1 BRD ya
deployado.

Pero si querés primero la revisión del SGD para no perder cosas
regulatorias, también es buen orden · te tomo una hora con ese
documento y armamos checklist.
