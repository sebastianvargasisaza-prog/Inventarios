# Análisis de Ecosistema — Sistema de Inventarios Espagiria
**Fecha:** 2026-04-17 | **Revisado por:** Claude (análisis estático, sin modificaciones al código)
**Base:** `/api/index.py` — 3,529 líneas, 37 rutas, 13 tablas SQLite

---

## 1. MAPA DEL SISTEMA

### Módulos activos

| Módulo | URL | Auth | Rutas API que consume |
|---|---|---|---|
| **Hub HHA Group** | `/` | Sin auth | — |
| **Dashboard / Inventario** | `/inventarios` | Sin auth | 20 endpoints |
| **Compras** | `/compras` | Session (compras_user) | 7 endpoints |
| **Solicitudes** | `/solicitudes` | Sin auth | 2 endpoints |

### Tablas SQLite (13 total)

| Tabla | Propósito | Sistema stock |
|---|---|---|
| `movimientos` | Event log MPs — fuente de verdad | Event sourcing (`tipo='Entrada'`/`'Salida'`) |
| `maestro_mps` | Catálogo MPs + stock_minimo | Solo metadatos |
| `maestro_mee` | Catálogo MEE + `stock_actual` (mutable) | Mutable (campo directo) |
| `movimientos_mee` | Audit trail MEE | Solo auditoría, NO calcula stock |
| `formula_headers` | Cabecera de fórmulas cosméticas | — |
| `formula_items` | Componentes % por fórmula | — |
| `producciones` | Registro de lotes producidos | — |
| `ordenes_compra` | OCs generadas | — |
| `ordenes_compra_items` | Ítems por OC | — |
| `solicitudes_compra` | Solicitudes de compra | — |
| `solicitudes_compra_items` | Ítems por solicitud | — |
| `proveedores` | Catálogo de proveedores | — |
| `alertas` | Alertas estáticas (tabla vestigial) | — |

---

## 2. BUGS CRÍTICOS

### 🔴 BUG #1 — `recibir_oc()` escribe `tipo='ingreso'` (CRÍTICO)

**Ubicación:** `@app.route('/api/ordenes-compra/<numero_oc>/recibir')` ~línea 3373

```python
# QUÉ HACE (INCORRECTO):
(codigo, nombre, cantidad, 'ingreso', fecha, ...)

# QUÉ ESPERAN TODAS LAS DEMÁS CONSULTAS:
SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END)
```

**Impacto:** Cada vez que se recibe una OC desde el módulo de Compras:
1. El registro entra en `movimientos` con `tipo='ingreso'`
2. Ninguna consulta de stock lo cuenta como Entrada
3. Peor aún: el cálculo `ELSE -cantidad` lo trata como **SALIDA** — el stock calculado **cae en negativo** por cada OC recibida

**Flujo Compras completamente roto:** Solicitud → Aprobación → OC → Recepción → ❌ Inventario no se actualiza, se degrada

**Fix:** Una sola línea. Cambiar `'ingreso'` → `'Entrada'`

---

### 🔴 BUG #2 — `generar_oc_automatica()` usa columnas inexistentes

**Ubicación:** ~línea 3185

```python
# INCORRECTO — columna 'cantidad_solicitada' no existe en ordenes_compra_items:
INSERT INTO ordenes_compra_items (..., cantidad_solicitada, unidad) VALUES (?,?,?,?,?)

# SCHEMA REAL:
ordenes_compra_items (id, numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
```

**Impacto:** La función de auto-generación de OCs por stock bajo mínimo falla con error SQL en producción. Las OCs se crean pero sin ítems.

**Fix (en patch_fase1.py):** Ya preparado — cambiar a `cantidad_g` y eliminar `unidad`.

---

### 🔴 BUG #3 — `/api/reset-movimientos` sin autenticación ni confirmación

**Ubicación:** ~línea 2945

```python
@app.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM movimientos")  # Borra TODO sin verificar nada
```

**Impacto:** Cualquier persona que descubra esta URL puede borrar todo el historial de inventario con un simple POST. Sin auth, sin confirmación, sin backup automático. **Riesgo existencial para los datos.**

**Fix inmediato:** Agregar `if 'compras_user' not in session or session['compras_user'] not in ADMIN_USERS: return 401`. Idealmente deshabilitar la ruta en producción.

---

### 🟡 BUG #4 — Análisis ABC agrupa por nombre, no por código

**Ubicación:** `/api/analisis-abc`

```sql
GROUP BY material_nombre  -- ❌
-- Debería ser:
GROUP BY material_id      -- ✅
```

**Impacto:** Si el mismo MP fue recibido con variaciones de nombre ("Glicerina", "GLICERINA", "glicerina USP"), aparece como 3 ítems separados en el ABC, distorsionando la clasificación.

---

### 🟡 BUG #5 — `dashboard-stats` incluye lotes vencidos en el cálculo de stock bajo mínimo

**Ubicación:** `/api/dashboard-stats` ~línea 3088

El subquery que cuenta MPs bajo mínimo no filtra por `estado_lote`. Stock de material vencido se cuenta como stock válido, ocultando alertas reales de reabastecimiento.

---

### 🟡 BUG #6 — `solicitudes_compra` GET no retorna `valor_estimado`

El GET `/api/solicitudes-compra` hace JOIN con ítems para calcular `valor_total`, pero no lo retorna en el payload estándar de listado. El frontend no puede mostrar el valor de cada solicitud en la tabla. **(Fix en patch_fase1.py)**

---

## 3. BRECHAS DE INTEGRACIÓN

### Brecha #1 — Compras ↔ Inventario: el puente está roto

```
[Solicitud] → [Aprobación] → [OC] → [Recepción] → [Movimientos]
                                            ↑
                              tipo='ingreso' (no 'Entrada')
                                   Stock NUNCA se actualiza
```

El módulo de Compras existe como isla. Todo el flujo de aprobación funciona correctamente hasta el último paso. Solo se necesita cambiar `'ingreso'` → `'Entrada'` para que el ciclo complete.

---

### Brecha #2 — Producción ↔ MEE: no hay descuento automático de empaque

Cuando se registra una producción en `/api/produccion`:
- ✅ Descuenta MPs por FEFO desde `movimientos`
- ❌ NO descuenta envases, tapas, etiquetas, plegables de `maestro_mee`

El operador debe hacer dos operaciones separadas: registrar la producción y luego ir a MEE a hacer ajuste manual. Sin guía de qué MEE usar por producto.

**Lo que falta:** Tabla `formula_mee` que mapee producto → {codigo_mee, und_por_unidad_producida}

---

### Brecha #3 — MEE completamente desconectado del módulo de Compras

El sistema tiene alertas de MEE bajo mínimo (`/api/alertas-mee`), pero:
- No se pueden incluir ítems MEE en solicitudes de compra
- No se pueden incluir ítems MEE en OCs
- No hay ruta de reabastecimiento para empaque

Si falta un envase, no hay flujo formal para pedirlo. La compra queda fuera del sistema.

---

### Brecha #4 — Proveedores tabla vs campo libre en OC

Existe la tabla `proveedores` con CRUD completo, pero al crear una OC el proveedor es texto libre. No hay validación contra el catálogo. Resultados:
- Posibles duplicados: "Chemicalabor", "CHEMICALABOR", "Chemicallabor"
- OCs asignadas a proveedores que no existen en el catálogo
- Reportes de compras por proveedor serán inconsistentes

---

### Brecha #5 — Alertas estáticas vs dinámicas: sistema duplicado

Hay dos sistemas de alertas que no se conectan:
- **`/api/alertas`** (tabla `alertas`): alertas insertadas manualmente vía POST desde el frontend. Tabla estática. Prácticamente vestigial.
- **`/api/alertas-reabastecimiento`**: calcula en tiempo real desde `movimientos` vs `stock_minimo`. Esto es lo que usa el Dashboard.

La tabla `alertas` debería eliminarse o redefinirse como "alertas descartadas/confirmadas por el usuario" para agregar valor real al flujo.

---

### Brecha #6 — Dashboard "Generar OC" no navega al resultado

El Dashboard tiene un botón que llama `/api/generar-oc-automatica` y genera las OCs, pero el usuario recibe solo un toast de confirmación. No hay redirección a Compras para ver las OCs generadas, revisarlas o aprobarlas. Flujo ciego.

---

### Brecha #7 — Fórmulas no tienen versioning

Las fórmulas se guardan con `INSERT OR REPLACE`. Cada cambio sobreescribe la versión anterior sin dejar rastro. Si se modifica una fórmula activa, se pierde el registro de qué fórmula se usó en cada lote de producción histórico.

---

## 4. ANÁLISIS POR MÓDULO

### 4.1 Dashboard / Inventario (20 rutas — módulo más completo)

| Función | Estado | Observación |
|---|---|---|
| Ver stock por MP | ✅ Funciona | Cálculo FEFO correcto |
| Ver lotes + vencimientos | ✅ Funciona | Incluye alerta de días |
| Registrar recepción | ✅ Funciona | `tipo='Entrada'` correcto |
| Registrar producción (FEFO) | ✅ Funciona | Lógica FEFO bien implementada |
| Fórmulas CRUD | ✅ Funciona | Sin versioning |
| Análisis ABC | ⚠️ Parcial | Agrupa por nombre, no código |
| Dashboard stats | ⚠️ Parcial | No filtra lotes vencidos en stock |
| Rótulos MP | ✅ Funciona | Genera HTML imprimible con barcode |
| Rótulo recepción | ✅ Funciona | — |
| Alertas reabastecimiento | ✅ Funciona | Base del sistema de alertas |
| Maestro MPs CRUD | ✅ Funciona | — |
| Reset movimientos | 🔴 Peligroso | Sin auth — deshabilitar en prod |

### 4.2 MEE — Materiales de Envase y Empaque

| Función | Estado | Observación |
|---|---|---|
| CRUD maestro MEE | ✅ Funciona | — |
| Ajuste manual stock | ✅ Funciona | Registra en movimientos_mee |
| Entrada/Salida unitaria | ✅ Funciona | Valida stock negativo |
| Salida por lote (producción) | ✅ Funciona | Usado para descuento masivo |
| Alertas MEE bajo mínimo | ✅ Funciona | — |
| Integración con Compras OC | ❌ No existe | Brecha crítica de operación |
| Integración con Producción | ❌ No existe | Descuento no automático |

**Observación importante sobre modelo de stock MEE:** A diferencia de MPs (event sourcing), MEE usa `stock_actual` mutable en `maestro_mee`. `movimientos_mee` es solo auditoría — no recalcula el stock. Si `maestro_mee.stock_actual` se desincroniza con los movimientos (por un bug, crash mid-transaction o carga manual), hay inconsistencia silenciosa. El sistema no tiene forma de "reconciliar" porque no tiene la lógica de recalcular desde movimientos_mee.

### 4.3 Compras (7 rutas — módulo en construcción)

| Función | Estado | Observación |
|---|---|---|
| Login/logout | ✅ Funciona | Fix aplicado sesión anterior |
| Ver OCs | ✅ Funciona | — |
| Crear OC manual | ✅ Funciona | Items con cantidad_g y precio |
| Auto-generar OC por alerta | 🔴 Roto | Bug columna cantidad_solicitada |
| Ver detalle OC | ⚠️ Parcial | Sin total calculado (patch_fase1) |
| Cambiar estado OC | ✅ Funciona | Con control por rol |
| Recibir OC → Inventario | 🔴 Roto | tipo='ingreso' no actualiza stock |
| Proveedores CRUD | ✅ Funciona | Desconectado de OC |
| Ver solicitudes | ⚠️ Parcial | Sin valor total (patch_fase1) |
| Aprobar solicitud → OC | ✅ Funciona | Crea OC desde solicitud correctamente |
| Rechazar solicitud | ✅ Funciona | — |

### 4.4 Solicitudes (2 rutas — módulo público)

| Función | Estado | Observación |
|---|---|---|
| Crear solicitud compra/pago | ✅ Funciona | Formulario dinámico implementado |
| Consultar estado por número | ✅ Funciona | — |
| Sin autenticación | ⚠️ Diseño | Cualquiera puede crear solicitudes |

---

## 5. FLUJOS COMPLETOS — ESTADO REAL

### Flujo A: Recepción de MP directa (Dashboard)
```
Operador → /inventarios → "Ingresar" → /api/recepcion [POST]
→ INSERT movimientos tipo='Entrada' ✅
→ Stock actualiza inmediatamente ✅
→ FUNCIONA COMPLETO
```

### Flujo B: Recepción de MP vía OC (Compras)
```
Solicitud → Aprobación → OC creada → Recepción OC
→ INSERT movimientos tipo='ingreso' ❌
→ Stock NO actualiza (cuenta como salida negativa)
→ FLUJO COMPLETAMENTE ROTO — PRIORIDAD 1
```

### Flujo C: Producción de lote
```
Operador → "Registrar producción" → /api/produccion [POST]
→ Busca fórmula por producto_nombre ✅
→ FEFO: descuenta por lote más próximo a vencer ✅
→ MEE: NO descuenta automáticamente ❌
→ PARCIALMENTE FUNCIONAL
```

### Flujo D: Alerta → Compra → Stock
```
Dashboard detecta MP bajo mínimo ✅
→ "Generar OC automática" → OC creada ✅
→ OC enviada a proveedor (manual, fuera del sistema) ➡ no automatizado
→ Material llega → "Recibir OC" → stock no actualiza ❌
→ FLUJO ROTO EN ÚLTIMO PASO
```

### Flujo E: Solicitud de compra pública
```
Cualquier persona → /solicitudes → Crea SOL-XXXX ✅
→ Compras recibe notificación (manual, no hay push) ➡ no automatizado
→ Compras aprueba → OC creada opcionalmente ✅
→ OC recibida → mismo problema del Flujo B ❌
```

---

## 6. PRIORIDADES DE INTERVENCIÓN

### Tier 0 — ESTA SEMANA (antes de operar Compras)

| # | Fix | Línea | Impacto |
|---|---|---|---|
| T0-1 | `tipo='ingreso'` → `tipo='Entrada'` en `recibir_oc()` | ~3373 | Activa todo el flujo Compras |
| T0-2 | `cantidad_solicitada` → `cantidad_g` en `generar_oc_automatica()` | ~3185 | OC auto sin crash |
| T0-3 | Auth en `/api/reset-movimientos` | ~2945 | Seguridad crítica |

### Tier 1 — Patch Fase 1 (patch_fase1.py listo)

- Ver detalle OC con total calculado
- `valor_total` en tabla solicitudes
- Columnas visuales mejoradas en Compras
- Fix `addItemOC()` nombres correctos

### Tier 2 — Patch Fase 2 (próximo sprint)

- Autocomplete MP en formulario OC
- Recepción parcial de OC (no solo 100%)
- PDF/print de OC
- Audit trail de cambios de estado
- Vincular proveedor de `proveedores` tabla al crear OC

### Tier 3 — Integraciones estructurales

- **MEE + Compras:** Permitir ítems MEE en solicitudes y OCs
- **MEE + Producción:** `formula_mee` para descuento automático de empaque
- **Proveedores → OC:** Validación al crear OC contra catálogo
- **Fórmulas versioning:** Guardar snapshot de fórmula al registrar producción

### Tier 4 — Madurez operativa (del roadmap)

- Analytics y dashboard de Compras (Fase 3)
- Historial de precios por MP + proveedor (Fase 4)
- Proveedores 360° (Fase 5)
- BPM avanzado + COA (Fase 6)

---

## 7. MEJORAS ADICIONALES NO EN EL ROADMAP

### 7.1 Reconciliación MEE
Agregar endpoint `/api/mee/<codigo>/reconciliar` que recalcule `stock_actual` desde la suma de `movimientos_mee`. Permite detectar y corregir inconsistencias entre el campo mutable y el audit trail.

### 7.2 Notificaciones (WhatsApp/Email)
El sistema ya genera `email_body` en `generar_oc_automatica()` pero nadie lo recibe. Integrar con la API de WhatsApp que ya está en construcción para enviar alertas automáticas cuando:
- MP cae bajo mínimo
- OC es aprobada/rechazada
- Lote próximo a vencer (<30 días)

### 7.3 Asociación Producto → SKU → MEE
Actualmente no hay tabla que diga "el producto VITAC usa ENV-XXX (1 und) + ETIQ-YYY (1 und) + PLEG-ZZZ (1 und)". Esta tabla desbloquea:
- Descuento automático de MEE al registrar producción
- Proyección de inventario de empaque para plan de producción
- Alertas MEE por producto específico

### 7.4 Plan de producción
Con fórmulas + MEE vinculados, se puede calcular: "Para producir X unidades del Plan Fernando Mesa, necesito Y kg de MP y Z unidades de empaque. ¿Alcanza el stock actual?"

### 7.5 Protección del `/solicitudes` público
Actualmente cualquier persona con la URL puede crear solicitudes. Considerar:
- Token de acceso por empresa (Espagiria vs ÁNIMUS)
- O al menos un código simple por empresa para distinguir fuente

---

## 8. RESUMEN EJECUTIVO

**Estado del sistema:** Funcional para operaciones básicas de inventario MP. Los módulos de Dashboard, Producción (FEFO) y MEE operan correctamente. El módulo de Compras tiene el flujo principal roto por un bug de una línea que, una vez corregido, activa un ciclo completo de aprovisionamiento.

**Riesgo inmediato más alto:** Bug T0-1 (`tipo='ingreso'`). Si se usa Compras en producción sin este fix, el inventario se vuelve progresivamente incorrecto — cada OC recibida reduce el stock calculado en lugar de aumentarlo.

**Riesgo de seguridad:** `/api/reset-movimientos` sin auth. Una sola llamada borra todo.

**Con los tres fixes de Tier 0 más patch_fase1.py, el sistema queda operativo para uso real en Compras.** Los Tiers 2-4 son evolución progresiva, no requisitos para arrancar.
