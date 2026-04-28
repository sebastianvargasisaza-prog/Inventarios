# Facturación Electrónica DIAN — propuesta para Alejandro

> **De:** Sebastián
> **Para:** Alejandro Morales
> **Tema:** Habilitar facturación electrónica timbrada para Espagiria
> **Fecha:** 2026-04-28

---

## Resumen ejecutivo (TL;DR)

Necesitamos contratar un Proveedor Tecnológico (PSP) autorizado por la
DIAN para timbrar electrónicamente las facturas de **Espagiria** (servicios
de maquila + ventas B2B aliados). Inversión: **$90K-$200K COP/mes**.
Tiempo de implementación: **2 semanas** desde firma de contrato.

**ANIMUS Lab queda fuera** de esta propuesta porque ya usa **Siigo**
para sus ventas DTC. Esta decisión solo afecta a Espagiria.

**Nuestra app HHA-ERP ya tiene el módulo de facturación construido**
(numeración secuencial fiscal, PDF legal, libro de ventas, export SIIGO).
Solo falta el último paso: integración con un PSP que timbre cada
factura ante la DIAN.

---

## 1. Por qué necesitamos esto AHORA

### Contexto regulatorio
Desde 2019 la DIAN obliga facturación electrónica timbrada para empresas
con ingresos >$X millones/año. Espagiria como manufactura B2B emite
facturas a:
- Aliados como **Fernando Mesa** (~$94.5M COP / ciclo de 60 días)
- Servicios de maquila a otras marcas (cuando reactivamos ese pipeline)
- Cuentas de cobro y honorarios profesionales

**Hoy emitimos PDF con numeración propia (FV-ESP-2026-NNNN), pero NO
están timbradas con la DIAN.** Eso técnicamente no cumple normatividad
para los volúmenes que manejamos.

### Riesgo si no lo hacemos
- Sanciones DIAN: 1% del valor no facturado correctamente, hasta
  $13.500.000 COP por mes de incumplimiento
- Aliados B2B grandes pueden rechazar pagar facturas no timbradas
- En auditoría externa (cuando crezcamos), encontrarán el hueco

### Lo bueno: ya hicimos casi todo el camino
Nuestra app HHA-ERP ya tiene:
- ✅ Numeración fiscal por empresa (`FV-ESP-2026-0001`, `FM-ESP-...` para
  facturas de maquila)
- ✅ PDF profesional con membrete, datos del cliente, IVA desglosado
- ✅ Tabla `facturas` con todo lo legal: emisor, receptor, items,
  subtotal, IVA %, retenciones, total
- ✅ Cartera (AR aging) automática
- ✅ Export a SIIGO ya funcionando
- ✅ Workflow: emitir → cobrar pago → marcar pagada
- ✅ Cobranza automática alimenta `flujo_ingresos`

**Lo único que falta:** mandar el XML de cada factura al PSP, que lo
timbra con la DIAN, recibimos el CUFE (número único de identificación)
y guardamos el XML firmado.

---

## 2. Qué hace nuestra app que un PSP solo NO hace

| Capacidad | Solo PSP | HHA-ERP + PSP |
|---|---|---|
| Timbrar factura DIAN | ✅ | ✅ |
| Generar la factura desde un pedido | ❌ (manual) | ✅ desde `pedidos` automático |
| Conectar factura a cobranza | ❌ | ✅ pago alimenta `flujo_ingresos` |
| Conectar factura a maquila | ❌ | ✅ orden maquila → factura `FM-ESP-` automática |
| AR aging por cliente | ❌ | ✅ con detalle de qué factura debe |
| P&L que refleja factura cobrada | ❌ | ✅ multi-empresa |
| Notificación email al cliente con PDF | ❌ | ✅ ya tenemos SMTP integrado |
| Reporte SIIGO mensual para contabilidad | ❌ | ✅ export Excel |
| Anulación con motivo y trazabilidad | ❌ | ✅ |
| IA para detectar factura duplicada / outlier | ❌ | ✅ próximamente |

**Resumen:** un PSP solo da timbrado. Nuestra app conecta TODA la
operación: pedido → factura → cobranza → flujo → P&L.

---

## 3. Comparativo de PSPs autorizados DIAN

He investigado los 4 más usados en cosmética colombiana:

### Opción A — FacturaTech ⭐ (recomendado para empezar)
- **Precio:** $90.000 COP/mes plan básico
- **Volumen:** hasta **100 facturas/mes** (suficiente para Espagiria hoy)
- **Documentos:** Factura electrónica + Notas crédito/débito + Documento soporte
- **API:** REST simple, sandbox para pruebas
- **Tiempo de integración:** 8-12 horas de desarrollo (yo lo hago)
- **Ventajas:** Más barato, fácil onboarding, documentación clara
- **Desventaja:** Si vendemos >100 facturas/mes, hay que pagar por excedente

### Opción B — Siigo ⭐ (recomendado si queremos consolidar)
- **Precio:** **Ya lo pagamos para ANIMUS** (~$99K-$199K/mes según plan)
- **Si Espagiria entra al mismo Siigo:** podríamos negociar plan unificado
- **Ventajas:**
  - Un solo proveedor para todo el holding
  - Contabilidad ya está ahí
  - El export de SIIGO que tenemos hoy se vuelve sync directo
  - Mayra trabaja en una sola plataforma
- **Desventaja:** API más compleja que FacturaTech, requiere autenticación
  OAuth y módulo Siigo Cloud

### Opción C — The Factory HKA
- **Precio:** $180.000 COP/mes plan profesional
- **Volumen:** ilimitado
- **Ventajas:** Muy estable, soporte 24/7, SDK Python oficial
- **Desventaja:** Más caro que FacturaTech para volumen <500/mes

### Opción D — Carvajal Tecnología
- **Precio:** $200.000 COP/mes
- **Volumen:** ilimitado, planes enterprise para volumen masivo
- **Ventajas:** El más usado por grandes empresas en Colombia
- **Desventaja:** Overkill para Espagiria, oneroso para arrancar

---

## 4. Mi recomendación

### Plan A: empezar con **FacturaTech** ($90K/mes)
- Cubre los 100 facturas/mes que estimamos para Espagiria
- Si crecemos a >100, migramos a Siigo o HKA
- Riesgo bajo, fricción mínima

### Plan B: consolidar TODO en **Siigo**
- ANIMUS ya está allí
- Espagiria entraría como segunda empresa
- Mayra opera todo en una sola plataforma
- Negociar precio combinado

**Mi voto: Plan B** — pagar un poco más en Siigo pero unificar el
holding. Mayra agradecería no manejar 2 sistemas. Y el sync con
nuestra HHA-ERP queda más limpio (ya tenemos export SIIGO).

---

## 5. Lo que se hace en cada plataforma (claridad)

### ✅ HHA-ERP (nuestro sistema)
- Manejo operacional COMPLETO
- Inventario, compras, producción, calidad, RRHH
- Tesorería (caja, P&L, runway)
- Marketing + influencers
- Pedidos B2B aliados (Espagiria)
- **Genera la factura** (numeración, PDF, XML)
- **Manda al PSP para timbrado**
- **Recibe CUFE timbrado** y lo guarda en `facturas.cufe`
- AR aging, cobranza, flujo automático
- Emite comprobante de egreso a influencers

### ✅ Siigo (donde ya estamos para ANIMUS)
- Contabilidad oficial DIAN
- Reportes tributarios (renta, IVA, retención)
- Estados financieros legales
- Conciliación bancaria contable
- **Si extendemos: timbrado de Espagiria también**

### Lo que NO mezclamos
- HHA-ERP NO reemplaza a Siigo en contabilidad legal
- Siigo NO reemplaza a HHA-ERP en operación diaria
- Cada uno hace lo suyo, integrados

---

## 6. Plan de implementación (cuando aprobemos)

### Semana 1: contratos
- [ ] Decidir Plan A (FacturaTech) o Plan B (Siigo extendido)
- [ ] Firmar contrato con el PSP elegido
- [ ] Recibir credenciales API (API key, NIT emisor habilitado, URL endpoint)

### Semana 2: integración técnica
- [ ] Sebastián pasa credenciales a Claude Code
- [ ] Claude implementa endpoint `POST /api/contabilidad/facturas/<num>/timbrar`
- [ ] Tests con sandbox del PSP (sin tocar producción)
- [ ] Probar emisión de 5 facturas de prueba

### Semana 3: producción
- [ ] Migrar a credenciales de producción
- [ ] Emitir primera factura real timbrada (a Fernando Mesa por su próximo pedido)
- [ ] Validar que llega a la DIAN (consulta CUFE)
- [ ] Catalina/Mayra entrenan flujo nuevo

### Total: 3 semanas desde firma hasta primera factura real timbrada.

---

## 7. ROI y costos

### Inversión año 1
| Concepto | Monto anual |
|---|---|
| FacturaTech ($90K x 12) | $1.080.000 COP |
| Implementación HHA-ERP (incluida en mantenimiento) | $0 |
| Contratos y onboarding | $0 (Sebastián + asistente jurídico) |
| **Total año 1** | **$1.080.000 COP** |

### Beneficios año 1
- Cumplimiento regulatorio DIAN: evitar sanción $13.5M/mes potencial
- Acceso a clientes B2B grandes que exigen factura electrónica
- Mayra ahorra ~5h/mes de re-digitar facturas en SIIGO (eso vale algo)
- Posibilidad de timbrar al instante (cliente recibe la factura con
  validez fiscal en segundos)

**Payback:** 1 mes (la primera vez que evitamos una sanción ya
recuperamos 12 años de mensualidad de FacturaTech).

---

## 8. Decisión que necesitamos

Alejandro, las preguntas concretas:

1. **¿Plan A (FacturaTech) o Plan B (Siigo extendido)?**
2. **¿Volumen real de facturas Espagiria mes a mes?** (para confirmar que
   el plan elegido es suficiente)
3. **¿Quien firma el contrato — tú o Sebastián?**
4. **¿Cuándo arrancamos?** (sugerido: esta semana)

Si me das el OK por chat o en próximo comité, esta semana firmamos y
en 3 semanas tenemos a Espagiria emitiendo factura electrónica timbrada
sin que Mayra cambie ningún proceso.

---

*Documento generado con apoyo del sistema HHA-ERP — la app que ya construimos
para esto.*
