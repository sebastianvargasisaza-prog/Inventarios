# Vender HHA-ERP como SaaS — propuesta estratégica

> **De:** Sebastián Vargas Isaza, CEO HHA Group
> **Para:** Alejandro Morales, Co-fundador HHA Group
> **Tema:** Convertir nuestra app interna en producto comercial vendible
> **Fecha:** 2026-04-28
> **Decisión solicitada:** ¿Vamos por esta línea de negocio nueva o no?

---

## TL;DR

Construimos en 6 meses un sistema operativo digital que cubre TODA la
operación de un laboratorio cosmético: inventario, compras, producción,
calidad, marketing, finanzas, contabilidad, dirección técnica, RRHH,
comunicación interna con IA, integración Shopify, parser de actas con
Claude. **No existe producto equivalente en Colombia para nuestro vertical**.

Mercado potencial: **80-150 laboratorios cosméticos colombianos** que hoy
operan con Excel, papel, o ERPs genéricos (SAP/Odoo) que no entienden
cosmética.

Modelo de negocio: SaaS mensual **$290K-$1.29M COP por cliente**.

A 24 meses con 80 clientes activos: **MRR $90M COP/mes = ARR $1.080M
COP/año**.

Inversión necesaria: **4-6 meses de desarrollo dedicado** + capital
para contratar 1 SDR y 1 customer success a partir del cliente 5.

**Lo que recomiendo hoy:** validar la decisión Q4 2026, mientras
seguimos consolidando HHA Group internamente. Si en septiembre el
sistema está sólido, lanzamos.

---

## 1. Contexto: ¿qué tenemos en las manos?

### El sistema actual (cifras reales)
- **27.940 líneas de código** Python+JS, 19 módulos
- **278 tests automatizados** corriendo en CI
- **38 migraciones de schema** aplicadas
- **+377 endpoints REST** operativos
- **12 personas usándolo a diario** en HHA Group
- **Producción real** desde hace 6 meses con cero downtime crítico
- **PWA instalable** en celular como app nativa

### Lo que cubre operacionalmente (de extremo a extremo)
1. **Inventario MPs** con FEFO, lotes, vencimientos
2. **Compras**: solicitudes → OCs → pago con comprobante PDF
3. **Producción**: programación, fórmulas BOM, déficit automático
4. **Calidad**: cuarentena, NCs, CAPA, CoA, estabilidades, calibraciones,
   auditorías
5. **Dirección Técnica**: fórmulas con versionado, INVIMA, SOPs
   con vencimientos
6. **Marketing**: campañas, influencers con ciclo de pago, ROI por
   campaña, integración Shopify
7. **Tesorería**: caja, P&L multi-empresa, AR/AP aging, runway,
   facturas con SIIGO export
8. **RRHH**: empleados, nómina con flujo automático, ausencias, SGSST
9. **Comunicación interna**: tareas con matriz RACI, chat, parser
   de actas comité, quejas con análisis IA Claude
10. **IA agentes**: análisis semanal automático CEO con Claude

### Lo que NO existe en el mercado colombiano
| Capacidad | SAP | Odoo | Soluciones nicho | HHA-ERP |
|---|---|---|---|---|
| Vertical cosmética | ❌ | ❌ | parcial | ✅ |
| Diagnóstico INCI fórmulas | ❌ | ❌ | ❌ | ✅ |
| Versionado fórmulas con BPM | ❌ | ❌ | parcial | ✅ |
| Integración Shopify cosmético | ❌ | ❌ | ❌ | ✅ |
| Parser actas Gemini → tareas | ❌ | ❌ | ❌ | ✅ |
| IA Claude integrada | ❌ | ❌ | ❌ | ✅ |
| Onboarding self-service rápido | ❌ | parcial | ❌ | en construcción |
| Precio mensual <$1.5M COP | ❌ | parcial | varía | ✅ |
| Implementación <2 semanas | ❌ | 3-6 meses | 1-3 meses | ✅ |

---

## 2. Mercado potencial — números

### Segmento principal: laboratorios cosméticos colombianos
- **~80-150 empresas** según ANDI Cámara Cosmética
- Tamaño: 5-50 empleados, ventas $500M-$10.000M COP/año
- Hoy operan con: Excel (60%), Holded/Alegra/Siigo solo (20%),
  SAP/Odoo (15%), papel (5%)
- Pain points reales (validados con tu propia experiencia):
  - Trazabilidad de fórmulas perdida en Excel
  - INVIMA vencidos sin alerta
  - Compras descoordinadas con producción
  - Marketing influencers no integrado a contabilidad
  - No hay vista única para dueño/CEO

### Segmentos adyacentes (Año 2)
- Laboratorios farmacéuticos genéricos (~30-50 empresas)
- Marcas DTC cosméticas que tercerizan producción (~100+)
- Maquiladores de cuidado personal (~20+)

### Mercado total direccionable (TAM)
**Año 1:** 80-150 cosmética COL
**Año 2:** +50 farma + 100 DTC = ~280 empresas total
**Año 3 (LATAM):** México, Perú, Chile = ~600+ empresas

---

## 3. Modelo de negocio

### Pricing propuesto

| Plan | Mensual COP | Incluye | Target |
|---|---|---|---|
| **Lab Starter** | $290.000 | Inventario + Compras + Calidad + 5 usuarios + 100 OCs/mes | Lab pequeño 1-3 productos |
| **Lab Pro** | $590.000 | + Marketing + Tesorería + 15 usuarios + 500 OCs/mes + IA básica | Lab mediano 5-15 productos |
| **Lab Enterprise** | $1.290.000 | + Multi-empresa + Maquila + ilimitado + IA premium + onboarding asistido | Lab grande con varias marcas |

### Add-ons opcionales
| Add-on | Mensual COP |
|---|---|
| Factura electrónica DIAN integrada | $190.000 |
| Sync Shopify automático | $90.000 |
| IA agentes premium (análisis estratégico semanal) | $290.000 |
| Multi-empresa adicional | $190.000 |

### Setup fee (one-time)
- Lab Starter: gratis (self-service)
- Lab Pro: $1.500.000 COP (onboarding asistido 1 semana)
- Lab Enterprise: $3.000.000 COP (onboarding 2 semanas + capacitación)

### Pricing internacional (LATAM)
- USD: $79 / $159 / $349 mensual (planes equivalentes)
- México, Perú, Chile como mercados secundarios año 2

---

## 4. Por qué nosotros podemos ganar

### Diferenciadores defensivos
1. **Domain expertise real** — tú eres médico que opera laboratorio cosmético.
   Los KPIs, fórmulas, INVIMA, BPM, FEFO — los entiendes en serio. SAP no.
2. **Velocidad** — Yo puedo agregar features en horas/días, no meses.
   Cosa que cliente pida y nosotros podemos hacer.
3. **Precio** — $290K-$1.29M COP/mes vs SAP $5M-$15M. Accesible.
4. **Implementación rápida** — Onboarding en 1-2 semanas vs 3-6 meses
   de SAP. Nuestro mercado pyme lo necesita ya.
5. **IA nativa** — Claude integrado de origen, no parche.
6. **Validado en producción** — funciona para HHA Group, no es vaporware.
7. **Mobile-first** — PWA instalable. SAP/Odoo no son mobile-first.

### Riesgos a mitigar
1. **Soporte multi-cliente** — al sumar 10+ clientes, una incidencia
   puede tumbar a varios. Necesitamos staging robusto + monitoring.
2. **Aislamiento de datos** — cliente A nunca debe ver datos cliente B.
   Tests exhaustivos de aislamiento.
3. **Dependencia de Claude (Anthropic)** — si suben precio API, afecta
   margen. Mitigación: contrato anual a precio fijo o multi-modelo.
4. **Competencia** — Holded, Alegra son nacionales y conocidos. Nuestro
   diferenciador es el VERTICAL. Si entran en cosmética, perdemos
   moat. Mitigación: ir rápido + contratos anuales.

---

## 5. Plan de ejecución

### Fase 0 — Hardening (Q3 2026, 2-3 meses)
- Multi-tenant arquitectura
- Tests de aislamiento exhaustivos
- Backup encryption
- Rate limiting global
- Monitoreo + alertas Sentry
- **Costo:** desarrollo dedicado + Sebastián supervisando
- **Sin gasto comercial todavía**

### Fase 1 — Pilotos (Q4 2026, 2 meses)
- 3-5 clientes piloto (referidos del gremio cosmético colombiano)
- Plan Starter gratis 3 meses a cambio de testimonio + feedback
- Iteración intensa con su feedback real
- **Costo:** marketing 0, ventas Sebastián
- **Métrica clave:** retention >80% al pasar a paid

### Fase 2 — Lanzamiento comercial (Q1 2027)
- Landing page profesional
- Pricing público
- 20-30 clientes objetivo año 1
- **Equipo a contratar:**
  - 1 SDR (Sales Development Rep) cuando llegues a 10 clientes — $4M COP/mes
  - 1 Customer Success cuando llegues a 25 — $5M COP/mes
- **Marketing:** $5M COP/mes para LinkedIn ads + ferias INCOSMETICS

### Fase 3 — Escalamiento (Q2-Q4 2027)
- 50-100 clientes
- Expansión a farma genéricos + DTC
- Considerar levantamiento de capital seed para acelerar
- Mes 24: spin-off potencial

---

## 6. Proyección financiera 24 meses

| Mes | Clientes | MRR (COP) | ARR (COP) | Costos op (COP) | Resultado mes |
|---|---|---|---|---|---|
| 6 | 5 | $4M | $48M | $4M (yo+Sebastián tiempo) | $0 |
| 12 | 25 | $25M | $300M | $12M (+SDR+CS) | $13M positivo |
| 18 | 50 | $52M | $625M | $20M | $32M positivo |
| 24 | 80 | $90M | $1.080M | $30M | $60M positivo |

**EBITDA año 2 estimado: $400-500M COP.**

### Valoración potencial mes 24
SaaS B2B vertical con $1B ARR + crecimiento 80%/año = múltiplo ARR x4-x6
= **$4.000M-$6.000M COP de valoración**.

Si decides venderlo o levantar capital, 25-35% equity podría salir por
$1.000M-$2.000M COP.

---

## 7. Lo que necesitamos decidir entre los dos

### Decisión 1: ¿Vamos o no?
- ✅ **Sí, vamos** → empezamos hardening en Q3 2026, primer cliente piloto Q4
- ⛔ **No, sigamos enfocados en HHA Group** → archivamos esta línea, reenfoque
- 🤔 **Aún no decidimos** → revisamos en 3 meses

### Decisión 2: ¿Cómo nos repartimos esta nueva línea?
- Sebastián lidera producto + ventas iniciales
- Alejandro lidera operación HHA Group + revisión estratégica del SaaS
- Posible esquema: 50/50 ambos en el SaaS, o estructura diferente

### Decisión 3: ¿Spin-off o dentro de HHA Group?
- **Dentro de HHA:** Año 1, validar PMF (Product-Market Fit). Aprovechamos
  recursos compartidos (oficina, contadora, etc.).
- **Spin-off:** Año 2, levantamiento capital, equipo dedicado, equity
  separado.

### Decisión 4: ¿Cuánto invertimos antes de tener primer revenue?
- Mínimo viable: **$0 directos** (yo desarrollo, Sebastián vende, sin
  marketing pago)
- Con marketing modesto: **$5M COP/mes** durante 3 meses pilotaje =
  **$15M COP total**
- Con marketing agresivo y SDR temprano: **$20M COP/mes** desde mes 6 =
  **$60M COP año 1 antes de break-even**

---

## 8. Lo que YO (Sebastián) gano y lo que TÚ (Alejandro) ganas

### Ganamos los dos
1. **Diversificación de ingresos** del holding más allá de Espagiria + ANIMUS
2. **Activo digital escalable** que vale más que la suma de las partes
3. **Posicionamiento** como innovadores en el sector cosmético
4. **Equity en producto SaaS** — históricamente múltiplos x4-x10 vs holding manufacturero
5. **Independencia geográfica** — el SaaS puede operar desde cualquier lugar

### Lo que tú específicamente ganas
- Sin tener que abandonar tu rol en HHA Group operación
- Co-propietario de un activo digital que puede valer $4-6 mil millones COP en 24 meses
- Voz en decisiones estratégicas + operación HHA Group sigue siendo tu foco
- Rol de contrapeso/board del SaaS sin operación día a día

### Lo que YO específicamente gano
- Aprovechar el sistema que ya construí
- Construir un activo escalable
- Tener equity más allá de manufactura
- Validar mi capacidad de crear producto digital

---

## 9. Mi propuesta concreta para conversar

**Esta semana o la próxima:**

1. **Reunión 1 hora** entre nosotros para que me digas tu reacción honesta:
   ¿lo ves, no lo ves, dudas?
2. Si te interesa: **decidir Decisión 1 + 2** (vamos o no, cómo repartimos)
3. Si NO te interesa: **archivamos limpiamente** y seguimos enfocados
   en HHA Group operación

**Mi ask:** que leas este documento, lo pienses 2-3 días, y me digas
si quieres que conversemos. No requiere decisión inmediata.

**Mi sesgo declarado:** estoy entusiasmado con esta posibilidad. Pero
también sé que HHA Group operación es nuestro core hoy y no quiero
arriesgar eso. Por eso propongo Q3-Q4 2026 (no antes).

---

## 10. Apéndice: por qué creo que esto vale la pena (mi tesis personal)

He visto a muchos laboratorios cosméticos en Colombia operar con
herramientas que no les dan visibilidad real:
- No saben cuánto les cuesta producir cada lote
- Pierden lotes vencidos por no tener alertas
- Tienen INVIMA caducados sin saber
- No tienen idea de su runway de caja
- Marketing es opaco, no saben qué influencer trae revenue

Yo entiendo ese dolor porque LO VIVÍ. Y construí la solución porque
necesitaba operar Espagiria + ANIMUS sin volverme loco.

Si lo que construí me sirve a mí, le sirve a otros 80-150 laboratorios
en mi misma situación. La pregunta no es **si tiene mercado** — sí lo
tiene. La pregunta es **si nosotros queremos invertir 6 meses + capital
en convertirlo en producto vendible**.

Esa decisión es nuestra y por eso te la traigo a discutir.

---

*Sebastián Vargas Isaza · MD MPH · CEO HHA Group · 2026-04-28*
