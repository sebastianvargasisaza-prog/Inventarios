# HHA Group — Ecosistema Digital Completo
**Fecha:** 2026-04-17 | **Alcance:** Espagiria Laboratorios + ÁNIMUS Lab
**Propósito:** Mapear todo lo que necesita una holding de manufactura cosmética + marca premium para operar con inteligencia real

---

## 1. MAPA DE LA HOLDING

```
HHA GROUP
├── Espagiria Laboratorios (manufacturing arm)
│   ├── Manufactura propia: fórmulas ÁNIMUS
│   ├── Maquila: manufactura para terceros (clientes maquila)
│   ├── I&D: desarrollo de nuevas fórmulas
│   └── Calidad: BPM, COA, INVIMA
│
└── ÁNIMUS Lab (brand arm)
    ├── Producto: portafolio skincare científico piel latina
    ├── Comercial: distribuidores (Fernando Mesa), DTC, retail
    ├── Marketing: influencers, contenido, posicionamiento
    └── Regulatorio: Notificaciones Sanitarias, fichas técnicas
```

**Flujo de valor interno:**
Espagiria manufactura → cobra a ÁNIMUS (transfer price) → ÁNIMUS vende → cobra a clientes

---

## 2. SISTEMAS YA CONSTRUIDOS ✅

| Sistema | Estado | Módulo |
|---|---|---|
| Inventario MPs + FEFO + lotes | ✅ Operativo | Dashboard |
| MEE (envases, etiquetas) | ✅ Operativo | Dashboard / MEE |
| Fórmulas cosméticas | ✅ Operativo | Dashboard |
| Producción con FEFO | ✅ Operativo | Dashboard |
| Compras + OC + Solicitudes | 🔧 Fix pending | Compras / Solicitudes |
| Rótulos GMP | ✅ Operativo | Dashboard |
| Alertas de reabastecimiento | ✅ Operativo | Dashboard |

---

## 3. EN DISEÑO — Este sprint

| Sistema | Estado | Documento |
|---|---|---|
| Clientes + Pedidos | 📐 Diseñado | CLIENTES_MODULO.md |
| Stock Producto Terminado | 📐 Diseñado | CLIENTES_MODULO.md |
| Despachos + Trazabilidad forward | 📐 Diseñado | CLIENTES_MODULO.md |

---

## 4. LO QUE FALTA — POR DOMINIO

### 4.1 FINANZAS — El motor de decisiones (ausente)

**Lo más crítico que no existe:**

**A. Cuentas por cobrar**
FM paga a 30 días. ¿Cuánto le debes cobrar? ¿Cuándo vence? ¿Está atrasado? Hoy no sabes. Con el módulo de Clientes + Pedidos se puede construir con solo agregar `fecha_vencimiento_pago` y `fecha_pago_real` a `despachos`.

**B. Costo de producción por lote**
El sistema sabe *qué* MPs se usaron (FEFO). No sabe *cuánto costaron*. Con precios en `ordenes_compra_items` ya existentes, se puede calcular: costo MP por kg producido → costo por unidad → margen bruto.

Fórmula: `Costo_lote = Σ(cantidad_mp_g × precio_mp_por_g) + MEE_por_unidad × unidades`

**C. Transferencia interna Espagiria → ÁNIMUS**
Cuando Espagiria manufactura para ÁNIMUS, ¿a qué precio se lo cobra? Eso es un ingreso para Espagiria y un costo para ÁNIMUS. Sin esto, no se puede ver la rentabilidad real de cada empresa.

**D. Flujo de caja proyectado**
"Próximos 30 días: cobrar a FM $94.5M, pagar a Chemicalabor $12M, pagar nómina $8M. Posición neta: +$74.5M." Esto se puede construir con: pedidos pendientes de cobro + OCs pendientes de pago + nómina fija.

**E. Análisis de rentabilidad por SKU**
`Precio_venta - COGS - Empaque - Maquila_fee = Margen_ÁNIMUS`
Hoy no sabes cuáles SKUs son rentables y cuáles drenan caja.

---

### 4.2 REGULATORIO / CALIDAD — Riesgo latente

Espagiria opera bajo BPM. Tiene MyBatch como EBR para fabricación. Lo que falta en el sistema propio:

**A. Registro de Notificaciones Sanitarias INVIMA**
Tabla simple:
```
sku | producto | ns_numero | fecha_otorgamiento | fecha_vencimiento | estado
```
Alerta cuando una NS vence en menos de 90 días. Sin esto, podrías estar vendiendo con registro vencido sin saberlo.

**B. COA (Certificate of Analysis) por lote de producción**
Cada lote debe tener un COA con: MPs usados + lotes + resultados de control de calidad. Con la trazabilidad que ya existe en `movimientos` + la producción FEFO, generar el COA es cuasi-automático. Solo falta agregar los campos de resultado de pruebas (pH, viscosidad, microbiología, etc.).

**C. Control de cambios de fórmula**
Si se modifica una fórmula, hay que documentarlo. Actualmente `INSERT OR REPLACE` sobreescribe sin dejar rastro. Tabla `formula_versiones` resuelve esto.

**D. Cuarentena de lotes**
Cuando un MP llega, debería pasar por cuarentena hasta que QC lo libera. Actualmente va directo a disponible. Campo `estado_lote = 'CUARENTENA'` ya existe en `movimientos` pero no hay flujo de liberación.

**E. Reclamaciones y quejas**
Si un cliente reporta un problema con un producto, ¿dónde queda documentado? ¿Cómo se hace el recall? Tabla `reclamaciones` con enlace al lote despachado → trazabilidad inversa.

---

### 4.3 MAQUILA — Línea de negocio invisible

Espagiria puede y debería ofrecer maquila a otras marcas. Eso requiere:

**A. Clientes maquila** (tipo='Maquila' en tabla `clientes`)
Diferente a clientes de producto: el cliente maquila trae su fórmula (o la desarrollamos), paga por kg producido + costo de empaque.

**B. Órdenes de maquila**
Similar a pedidos pero con: fórmula del cliente (confidencial), especificaciones de empaque del cliente, precio por kg o por unidad pactado, lead time de producción.

**C. Facturación de servicio**
Diferente a la venta de producto: la factura es por servicio de manufactura, no por producto. NIT del cliente, valor del servicio, IVA sobre servicio.

**D. Confidencialidad de fórmulas**
Las fórmulas de clientes maquila no deben mezclarse con las de ÁNIMUS. Flag `es_confidencial = 1` en `formula_headers` + acceso restringido.

---

### 4.4 CADENA DE SUMINISTRO — Inteligencia que falta

**A. Lead times por proveedor**
Actualmente no se registra cuánto demora cada proveedor en entregar. Si Chemicalabor tarda 15 días, el punto de reorden debería activarse 15 días antes de llegar al mínimo, no cuando ya se llegó al mínimo.

Tabla: `proveedores.lead_time_dias INTEGER DEFAULT 7`

**B. Historial de precios por MP**
Los precios cambian. Si el mes pasado pagué $45/kg por Niacinamida y este mes me cobran $52/kg, quiero saberlo y poder negociar. Tabla `historial_precios_mp (codigo_mp, proveedor, precio_kg, fecha, numero_oc)`.

**C. Forecast de consumo**
Con historial de producción (ya existe), calcular: "en promedio uso X kg de Niacinamida por mes. A ritmo actual, el stock alcanza para N semanas." Esto convierte el punto de reorden fijo en un punto de reorden dinámico.

**D. Evaluación de proveedores**
¿El proveedor llegó a tiempo? ¿La calidad fue la esperada? ¿El precio fue correcto? Tabla `evaluaciones_proveedor` con score acumulado. Base para la calificación ya mencionada en el roadmap de Compras.

---

### 4.5 COMERCIAL / CRM — Lo que ÁNIMUS necesita crecer

**A. Pipeline de nuevos clientes**
FM no puede ser el único distribuidor indefinidamente. ¿Hay prospectos? ¿En qué etapa están? Una tabla `prospectos` con estado del pipeline (contacto inicial → muestra → negociación → primer pedido) es el CRM mínimo.

**B. Historial de muestras**
Antes de que un cliente haga su primer pedido, pide muestras. ¿A quién se mandaron? ¿Cuándo? ¿Qué pasó? Esto alimenta el pipeline.

**C. Pricing por canal**
ÁNIMUS tiene: precio retail (PVP), precio distribuidor (FM), precio maquila (Espagiria → terceros). Tabla `lista_precios (sku, canal, precio, fecha_desde, fecha_hasta)`.

**D. Proyección de ingresos**
Con pedidos recurrentes (FM), proyectar: "Si FM sigue el mismo ritmo, facturamos $189M los próximos 2 meses." + Variable: nuevos clientes en pipeline.

---

### 4.6 PRODUCCIÓN AVANZADA — La fábrica conectada

**A. Planeación de producción**
"Para cubrir el pedido de FM del mes 6, necesito producir: TRX × 60kg, NIAC × 60kg, etc. ¿Tengo MPs? ¿Tengo MEE? ¿Tengo capacidad?" Esto es MRP básico.

**B. Rendimiento real vs. teórico**
La fórmula dice 1000g de producto. ¿Cuánto se produce realmente? Si hay mermas por evaporación o transfer, el rendimiento real es menor. Campo `rendimiento_pct` en `producciones`.

**C. Capacidad productiva**
¿Cuántos kg puede procesar Espagiria por semana? Si FM pide 540 kg de granel, ¿en cuántos días se puede producir? Tabla `capacidad_equipos`.

**D. Formula → MEE automático** *(ya identificado en análisis de brechas)*
Por SKU: qué envase, qué tapa, qué etiqueta, qué plegable usa. Una unidad consume exactamente 1 envase + 1 tapa + 1 etiqueta. Esto conecta la producción con el descuento automático de MEE.

---

### 4.7 RECURSOS HUMANOS / OPERACIONES

**A. Certificaciones de operarios (GMP)**
En BPM, cada operario debe estar entrenado y certificado para las operaciones que realiza. Tabla `operarios_certificaciones (operario, operacion, fecha_certificacion, fecha_vencimiento)`.

**B. Registro de incidentes**
Si algo sale mal en producción (derrame, contaminación, error de pesaje), debe documentarse. Tabla `incidentes_produccion` con link al lote afectado.

---

## 5. PRIORIZACIÓN — CUÁNDO HACER QUÉ

### Sprint 1 — Este fin de semana
1. Bugs T0 (tipo='ingreso', columna OC, reset sin auth)
2. patch_fase1.py (mejoras Compras)
3. **Módulo Clientes + stock_pt + Pedidos básico**

### Sprint 2 — Próximas 2 semanas
4. Despachos + trazabilidad forward
5. COA semi-automático por lote
6. Cuentas por cobrar básico (fecha_vencimiento en despachos)

### Sprint 3 — Mes 2
7. COGS por lote (requiere precios en MPs)
8. Formula → MEE automático
9. Cuarentena + liberación de lotes
10. Lead times en proveedores

### Sprint 4 — Mes 3
11. Historial de precios MP
12. Forecast de consumo dinámico
13. Módulo maquila básico
14. INVIMA registry

### Sprint 5 — Mes 4-5
15. MRP básico (pedido → plan producción → plan compras)
16. Rentabilidad por SKU
17. Pipeline de clientes / CRM mínimo
18. Flujo de caja proyectado

### Largo plazo (Mes 6+)
19. Transfer pricing Espagiria ↔ ÁNIMUS
20. Integración WhatsApp (ya en construcción)
21. Evaluación automática de proveedores
22. Certificaciones operarios

---

## 6. PROPUESTA DE VALOR TOTAL DEL SISTEMA

Cuando todo esté construido, HHA Group tendrá:

**Para Espagiria:**
- Control total de MPs y MEE en tiempo real
- Trazabilidad GMP forward + backward
- COA por lote automático
- Módulo maquila con fórmulas de clientes protegidas
- Compras inteligente con lead times y forecast

**Para ÁNIMUS Lab:**
- Inventario PT por SKU en tiempo real
- Pedidos y despachos a FM y otros distribuidores
- Trazabilidad hacia el cliente (lote que le entregué a FM el mes pasado)
- Revenue tracking por SKU y por cliente
- Pipeline de nuevos distribuidores

**Para HHA Group (holding):**
- Vista consolidada de operaciones de las dos empresas
- Rentabilidad por SKU (precio - COGS)
- Flujo de caja proyectado
- Indicadores de eficiencia productiva
- Alertas regulatorias (NS INVIMA por vencer)

**Todo esto en un solo sistema propio**, sin Odoo, sin SAP, construido exactamente para este negocio, operado por WhatsApp + panel web.

---

## 7. INDICADORES CLAVE A MONITOREAR (KPIs)

| Indicador | Fuente | Frecuencia |
|---|---|---|
| Stock MP crítico (bajo mínimo) | `alertas-reabastecimiento` | Tiempo real |
| Unidades PT disponibles por SKU | `stock_pt` | Tiempo real |
| Pedidos pendientes de despacho | `pedidos` | Diario |
| Días de cuentas por cobrar (FM) | `despachos` + pagos | Semanal |
| COGS por lote de producción | `movimientos` + `ordenes_compra_items` | Por producción |
| Margen bruto por SKU | Precio - COGS | Mensual |
| Vencimientos próximos (MPs) | `movimientos.fecha_vencimiento` | Semanal |
| NS INVIMA por vencer | `invima_registry` | Mensual |
| Rotación de inventario MP | `movimientos` | Mensual |
| OTD (On-Time Delivery) FM | `pedidos.fecha_entrega_est` vs real | Por pedido |
