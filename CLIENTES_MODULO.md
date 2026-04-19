# Módulo CLIENTES — Diseño Técnico
**Versión:** 1.0 | **Fecha diseño:** 2026-04-17
**Integra con:** `producciones`, `stock_pt` (nuevo), `pedidos` (nuevo), `solicitudes_compra`

---

## Concepto central

Cuando producción registra un lote terminado y selecciona **cliente destino** (ÁNIMUS Lab, Fernando Mesa, u otro), el sistema alimenta automáticamente el inventario de producto terminado (`stock_pt`). Desde ahí, el módulo de Clientes gestiona pedidos, despachos, y da visibilidad de facturación.

**Flujo completo:**
```
Producción → stock_pt (PT disponible)
                 ↓
Pedido confirmado → PT reservado
                 ↓
Despacho registrado → PT consumido + trazabilidad de lote
                 ↓
Dashboard cliente → facturación acumulada / historial
```

---

## 1. SCHEMA SQL — 6 tablas nuevas

```sql
-- Registro de clientes
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,                         -- CLI-001
    nombre TEXT NOT NULL,
    empresa TEXT DEFAULT 'ÁNIMUS',              -- ÁNIMUS / Espagiria
    tipo TEXT DEFAULT 'Distribuidor',           -- Distribuidor | Maquila | Retail | DTC | Interno
    contacto TEXT DEFAULT '',
    email TEXT DEFAULT '',
    telefono TEXT DEFAULT '',
    nit TEXT DEFAULT '',
    condiciones_pago TEXT DEFAULT '30 días',
    descuento_pct REAL DEFAULT 0,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT,
    observaciones TEXT DEFAULT ''
);

-- Órdenes de venta / pedidos por cliente
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,                         -- PED-2026-0001
    cliente_id INTEGER REFERENCES clientes(id),
    fecha TEXT,
    fecha_entrega_est TEXT,
    estado TEXT DEFAULT 'Confirmado',           -- Borrador|Confirmado|Produciendo|Listo|Despachado|Facturado|Cancelado
    empresa TEXT DEFAULT 'ÁNIMUS',
    valor_total REAL DEFAULT 0,
    observaciones TEXT DEFAULT '',
    creado_por TEXT DEFAULT '',
    fecha_despacho TEXT DEFAULT '',
    numero_factura TEXT DEFAULT ''
);

-- Ítems del pedido (SKU + cantidad + precio)
CREATE TABLE IF NOT EXISTS pedidos_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_pedido TEXT,
    sku TEXT,
    descripcion TEXT,
    cantidad INTEGER DEFAULT 0,
    precio_unitario REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    lote_pt TEXT DEFAULT ''                     -- asignado al despachar
);

-- Inventario de producto terminado (alimentado desde producción)
CREATE TABLE IF NOT EXISTS stock_pt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    descripcion TEXT DEFAULT '',
    lote_produccion TEXT DEFAULT '',            -- referencia a producciones.id
    fecha_produccion TEXT,
    unidades_inicial INTEGER DEFAULT 0,
    unidades_disponible INTEGER DEFAULT 0,
    precio_base REAL DEFAULT 0,
    empresa TEXT DEFAULT 'ÁNIMUS',
    estado TEXT DEFAULT 'Disponible',           -- Disponible|Reservado|Despachado|Cuarentena
    observaciones TEXT DEFAULT ''
);

-- Cabecera de despachos
CREATE TABLE IF NOT EXISTS despachos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,                         -- DES-2026-0001
    numero_pedido TEXT DEFAULT '',
    cliente_id INTEGER,
    fecha TEXT,
    operador TEXT DEFAULT '',
    observaciones TEXT DEFAULT '',
    estado TEXT DEFAULT 'Completado'
);

-- Ítems despachados (trazabilidad lote PT → cliente)
CREATE TABLE IF NOT EXISTS despachos_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_despacho TEXT,
    sku TEXT,
    descripcion TEXT,
    lote_pt TEXT,
    cantidad INTEGER DEFAULT 0,
    precio_unitario REAL DEFAULT 0
);
```

---

## 2. MIGRACIÓN: Cambios en tablas existentes

```sql
-- Agregar campo cliente_destino a producciones (opcional, retrocompatible)
ALTER TABLE producciones ADD COLUMN cliente_destino TEXT DEFAULT 'ÁNIMUS';
ALTER TABLE producciones ADD COLUMN sku TEXT DEFAULT '';
ALTER TABLE producciones ADD COLUMN unidades INTEGER DEFAULT 0;
```

El campo `cliente_destino` permite que al registrar producción se especifique si es para ÁNIMUS, Fernando Mesa, u otro cliente. Esto dispara la creación automática en `stock_pt`.

---

## 3. SEED DATA — Clientes iniciales

```sql
INSERT OR IGNORE INTO clientes 
(codigo, nombre, empresa, tipo, contacto, email, condiciones_pago, descuento_pct, fecha_creacion)
VALUES 
('CLI-001', 'ÁNIMUS Lab', 'ÁNIMUS', 'Interno', 'Sebastián Vargas', 'sebastianvargasisaza@gmail.com', 'Inmediato', 0, datetime('now')),
('CLI-002', 'Fernando Mesa', 'ÁNIMUS', 'Distribuidor', 'Fernando Mesa', '', '30 días', 0, datetime('now'));
```

---

## 4. API ENDPOINTS (8 rutas nuevas)

| Método | Ruta | Función |
|---|---|---|
| GET/POST | `/api/clientes` | Listar / crear clientes |
| GET/PUT | `/api/clientes/<id>` | Detalle / editar cliente |
| GET | `/api/clientes/<id>/stats` | Facturación, último pedido, total deuda |
| GET/POST | `/api/pedidos` | Listar / crear pedido |
| GET/PATCH | `/api/pedidos/<numero>` | Detalle / cambiar estado |
| GET/POST | `/api/stock-pt` | Inventario PT disponible |
| POST | `/api/despachos` | Registrar despacho + consumir stock PT |
| GET | `/api/clientes/<id>/historial` | Historial de pedidos + lotes despachados |

### Endpoint crítico: `/api/stock-pt` POST
Llamado automáticamente desde `handle_produccion()` cuando `cliente_destino` viene en el payload:

```python
# Agregar al final de handle_produccion() después del commit:
if data.get('cliente_destino') and data.get('sku'):
    unidades = int(data.get('unidades', 0))
    c.execute("""INSERT INTO stock_pt 
                 (sku, descripcion, lote_produccion, fecha_produccion,
                  unidades_inicial, unidades_disponible, empresa, estado)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (data['sku'], producto, lote_ref, fecha,
               unidades, unidades, 'ÁNIMUS', 'Disponible'))
```

### Endpoint clave: `GET /api/clientes/<id>/stats`
```python
def get_cliente_stats(id):
    # Total facturado (suma de pedidos Facturados/Despachados)
    c.execute("""SELECT COUNT(*), SUM(valor_total), MAX(fecha)
                 FROM pedidos WHERE cliente_id=? AND estado NOT IN ('Cancelado','Borrador')""", (id,))
    # Pedidos pendientes de despacho
    c.execute("""SELECT COUNT(*), SUM(valor_total)
                 FROM pedidos WHERE cliente_id=? AND estado IN ('Confirmado','Produciendo','Listo')""", (id,))
    # Facturas vencidas (estado=Despachado y fecha > condiciones_pago)
    # → return: total_pedidos, total_facturado, ultimo_pedido, pendiente_cobro
```

---

## 5. INTEGRACIÓN CON PRODUCCIÓN — Cambio en formulario

En el formulario de producción del Dashboard, agregar:

```html
<!-- Campos adicionales en modal-produccion -->
<div class="form-row" id="pt-fields" style="display:none">
  <label>SKU producto terminado:</label>
  <input type="text" id="prod-sku" placeholder="TRX-120-FM">
  
  <label>Unidades a registrar:</label>
  <input type="number" id="prod-unidades" placeholder="500">
  
  <label>Destino:</label>
  <select id="prod-cliente-destino">
    <option value="">-- No registrar en PT --</option>
    <option value="ÁNIMUS Lab">ÁNIMUS Lab</option>
    <option value="Fernando Mesa">Fernando Mesa</option>
  </select>
</div>

<label>
  <input type="checkbox" id="toggle-pt" onchange="togglePTFields()">
  Registrar producto terminado
</label>
```

Cuando se activa el checkbox, aparecen los campos y el POST a `/api/produccion` incluye `sku`, `unidades`, `cliente_destino`.

---

## 6. ESTRUCTURA UI — Módulo Clientes

### Tarjeta en el Hub HHA Group
```
┌─────────────────────────────────┐
│  👥  CLIENTES                   │
│  ÁNIMUS Lab + Espagiria         │
│  Pedidos · Stock PT · Despachos │
└─────────────────────────────────┘
```

### Pestañas del módulo
```
[Dashboard] [Clientes] [Pedidos] [Stock PT] [Despachos]
```

**Tab Dashboard:**
- Tarjetas: Unidades PT disponibles | Pedidos activos | Monto pendiente despacho | Facturación mes
- Tabla: top clientes por volumen (mes actual)
- Alertas: pedidos vencidos sin despachar

**Tab Clientes:**
- Tabla: código, nombre, tipo, empresa, último pedido, total facturado, estado
- Click → detalle con historial completo de pedidos y lotes despachados

**Tab Pedidos:**
- Kanban o tabla filtrable por estado: Confirmado → Produciendo → Listo → Despachado → Facturado
- Botón "Nuevo pedido" (seleccionar cliente → agregar líneas SKU/cantidad/precio)
- Botón "Marcar despachado" → abre modal para asignar lotes PT disponibles

**Tab Stock PT:**
- Tabla: SKU | Descripción | Lote producción | Fecha | Unidades disponibles | Empresa | Estado
- Semáforo: verde (>50% disponible) | amarillo (<20%) | rojo (0)
- Filtro por empresa (ÁNIMUS / Espagiria)

**Tab Despachos:**
- Historial de despachos con: número, cliente, fecha, ítems, lotes entregados
- Click → detalle con trazabilidad completa (lote PT → lotes MP usados)

---

## 7. TRAZABILIDAD COMPLETA — El salto de calidad

Con este módulo, la trazabilidad cierra en ambas direcciones:

**Hacia atrás (backward):** "¿Qué MPs usé para el lote que le envié a Fernando Mesa?"
```
DES-2026-0001 → lote_pt=PROD-00047 → producciones.id=47
→ movimientos WHERE observaciones LIKE '%PROD-00047%'
→ Lista de MPs + lotes usados ✅
```

**Hacia adelante (forward):** "El lote de Niacinamida ESP240310NIA fue a qué producción y luego a qué cliente?"
```
movimientos WHERE lote='ESP240310NIA' AND tipo='Salida'
→ observaciones → PROD-XXXXX
→ stock_pt WHERE lote_produccion=PROD-XXXXX
→ despachos_items → cliente ✅
```

Esto es lo que INVIMA requiere para trazabilidad de cosméticos. Lo tenemos casi sin esfuerzo extra.

---

## 8. FERNANDO MESA — Configuración específica

FM tiene un patrón predecible: 500 unidades / 9 SKUs / cada 2 meses.

**Automatización propuesta:**
- `pedidos` tiene campo `tipo='Recurrente'` 
- Cuando el último pedido de FM supera 60 días desde despacho → generar alerta "FM: próximo pedido estimado"
- Opcionalmente: crear borrador automático de pedido con los 9 SKUs a 500 unidades con precios ya configurados

**Precio FM precargado en clientes:**
Los precios ya están en memoria:
```
LBHA: $16,807 | TRX: $31,933 | NIAC: $16,807 | AZHC: $36,592 | SBHA: $15,126
ECEN: $15,126 | EILU: $24,000 | CUREA: $33,613 | GELH: (pendiente)
```

Valor potencial pedido FM: ~$189,004 × 500 uds = **~$94.5M COP por ciclo**

Estos precios se pueden guardar en `pedidos_items` como defaults cuando se crea un pedido de CLI-002.
