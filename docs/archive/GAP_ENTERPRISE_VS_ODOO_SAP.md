# 🧠 Cortex Labs vs Enterprise (Odoo, SAP, Monday, NetSuite)

**Para:** Sebastián / Alejandro
**Fecha:** Abril 2026
**Pregunta:** ¿Qué nos falta para ser "nivel enterprise" como Odoo / SAP?

---

## TL;DR honesto

Tenemos **el 65-70% de un Odoo Community vertical de cosméticos**.
Para llegar a **paridad enterprise** (poder venderle a un Quala, una Belcorp local,
una Recamier) necesitamos cerrar **12 brechas críticas** distribuidas en 3 frentes:

| Frente | Estado | Esfuerzo restante |
|---|---|---|
| **Funcional** (módulos) | Muy fuerte ✅ | 2-3 meses |
| **Plataforma** (multi-tenant, SSO, audit) | Débil ⚠️ | 4-6 meses |
| **Confianza enterprise** (certificaciones, SLA) | No existe ❌ | 8-12 meses |

**Buena noticia:** ya somos mejores que Odoo en **varias cosas verticales**:
checklist pre-producción con cálculo agregado, integración Shopify→flujo de caja
en tiempo real, IA conversacional para ejecutivos, OCR facturas con regex
colombiano-fiscal, RACI integrado a compromisos.

---

## 1. Comparativo honesto por dimensión

### Funcionalidad core (módulos operativos)

| Capacidad | Cortex Labs | Odoo Enterprise | SAP S/4HANA | Monday |
|---|---|---|---|---|
| Inventario multi-bodega | ✅ | ✅ | ✅ | ❌ |
| Lotes y trazabilidad | ✅ | ✅ | ✅ | ❌ |
| Fórmulas (BoM) | ✅ | ✅ | ✅ | ❌ |
| Producción / programación | ✅ | ✅ | ✅ | ❌ |
| **Checklist pre-producción agregado** | ✅ **único** | ❌ | ❌ | ❌ |
| Compras + RFQ + OC | ✅ | ✅ | ✅ | ⚠️ |
| Pagos + conciliación bancaria | ✅ | ✅ | ✅ | ❌ |
| P&L multi-empresa | ✅ | ✅ | ✅ | ❌ |
| Contabilidad (asientos, mayor) | ⚠️ básico | ✅ | ✅ | ❌ |
| Facturación electrónica DIAN | ⚠️ pendiente PSP | ✅ vía addon | ✅ | ❌ |
| RRHH / Nómina | ⚠️ básico | ✅ | ✅ | ❌ |
| CRM | ⚠️ básico | ✅ | ✅ | ✅ |
| Marketing | ⚠️ básico | ✅ | ⚠️ | ⚠️ |
| Calidad BPM (NC, calibraciones) | ✅ | ⚠️ vía módulo | ✅ | ❌ |
| **IA conversacional CEO** | ✅ **único** | ❌ | ⚠️ Joule (caro) | ❌ |
| **OCR de facturas COL** | ✅ **único** | ⚠️ genérico | ⚠️ genérico | ❌ |
| **RACI integrado** | ✅ **único** | ❌ | ❌ | ⚠️ |
| Shopify sync nativo | ✅ | ⚠️ vía addon | ⚠️ vía addon | ❌ |
| Tareas / Compromisos | ✅ | ✅ | ✅ | ✅ |
| Documentos / wiki | ⚠️ básico | ✅ | ✅ | ✅ |
| Calendario / reuniones | ⚠️ básico | ✅ | ✅ | ✅ |
| BI / dashboards ad-hoc | ⚠️ fijos | ✅ | ✅ | ⚠️ |
| Gestión de proyectos | ⚠️ básico | ✅ | ⚠️ vía módulo | ✅ |

**Veredicto funcional:** somos **competitivos** en operación de planta cosmética.
Tenemos cosas que **ellos no tienen**. Pero nos faltan **2-3 módulos secundarios**
para "completitud" (CRM serio, BI ad-hoc, documental).

### Plataforma y arquitectura

| Capacidad | Cortex Labs | Odoo | SAP | Estado nuestro |
|---|---|---|---|---|
| Multi-tenant real (un código → N empresas) | ❌ | ✅ | ✅ | **Brecha #1** |
| SSO Google Workspace / Microsoft 365 | ❌ | ✅ | ✅ | **Brecha #2** |
| RBAC granular (rol + permisos por acción) | ⚠️ | ✅ | ✅ | **Brecha #3** |
| Audit log inmutable (qué hizo cada usuario) | ⚠️ parcial | ✅ | ✅ | **Brecha #4** |
| Soft delete / papelera de reciclaje | ❌ | ✅ | ✅ | **Brecha #5** |
| API REST documentada (OpenAPI) | ⚠️ no doc | ✅ | ✅ | **Brecha #6** |
| Webhooks salientes (eventos a 3ros) | ❌ | ✅ | ✅ | **Brecha #7** |
| Multi-idioma (i18n) | ❌ | ✅ | ✅ | **Brecha #8** |
| Multi-moneda real (FX rates) | ❌ | ✅ | ✅ | **Brecha #9** |
| Workflow engine (BPMN configurable) | ❌ | ✅ | ✅ | **Brecha #10** |
| Marketplace / addons | ❌ | ✅ | ✅ | Nice-to-have |
| Backup + restore documentado | ⚠️ Render | ✅ | ✅ | **Brecha #11** |
| Logs centralizados (Datadog/Sentry) | ❌ | ✅ | ✅ | **Brecha #12** |

**Veredicto plataforma:** acá es donde duele. Para venderle a una empresa de
80+ personas necesitan SSO, RBAC granular, audit log, multi-tenant, y backups
documentados. Sin eso es un "no-go" automático.

### Confianza enterprise (lo que pide el área de TI del cliente)

| Capacidad | Cortex Labs | Odoo | SAP |
|---|---|---|---|
| Certificación ISO 27001 | ❌ | ✅ | ✅ |
| Certificación SOC 2 Type II | ❌ | ✅ | ✅ |
| Habeas Data Colombia (Ley 1581) | ⚠️ no doc | ✅ | ✅ |
| Cumplimiento INVIMA documentado | ⚠️ código sí, doc no | ⚠️ | ✅ |
| Acuerdo de procesamiento de datos (DPA) | ❌ | ✅ | ✅ |
| SLA 99.9% uptime contractual | ❌ | ✅ | ✅ |
| Soporte 24/7 (al menos email) | ❌ | ✅ | ✅ |
| Onboarding profesional (consultor implementador) | ❌ | ✅ | ✅ |
| Roadmap público + changelog | ❌ | ✅ | ✅ |

**Veredicto confianza:** para vender a empresa mediana-grande sí necesitas
ISO 27001 + SLA contractual. Esto **NO** lo solucionas con código. Es proceso,
auditoría externa, y dinero ($25-60K USD/año el ISO 27001 inicial).

---

## 2. Las 12 brechas críticas — priorizadas

### TIER 1 — INDISPENSABLE para vender a otro lab (3-6 meses)

#### Brecha #1: Multi-tenant real
**Problema:** hoy tenemos UNA base de datos con UN cliente (HHA). Si Belcorp
quiere usar Cortex Labs, ¿le levantamos otra instancia? ¿Le creamos otra DB?
**Solución:**
- Opción A (más rápida, "single-DB multi-tenant"): añadir columna `tenant_id`
  a TODAS las tablas + middleware Flask que filtre automáticamente por
  `tenant_id` del usuario logueado. **Esfuerzo: 6-8 semanas.**
- Opción B (más limpia, "DB-per-tenant"): un schema o DB por cliente, con
  un dispatcher al login. **Esfuerzo: 10-12 semanas.**
**Recomendación:** A para los primeros 5 clientes, B cuando lleguemos a 20+.

#### Brecha #2: SSO Google Workspace
**Problema:** hoy autenticamos con usuario+password. Toda empresa COL >50
personas usa Google Workspace o Microsoft 365 y exige "Login con Google".
**Solución:** integrar `Authlib` con Google OAuth + email matching contra
tabla `usuarios`. **Esfuerzo: 1-2 semanas.**

#### Brecha #3: RBAC granular
**Problema:** hoy es "admin sí/no" + roles por módulo. Falta:
- Permisos por acción (ej. "puede VER OCs pero NO aprobar")
- Permisos por monto (ej. "aprueba OCs hasta $5M, no más")
- Permisos por bodega/empresa
**Solución:** tabla `permisos(rol, recurso, accion, condicion)` + decoradores
`@requires_permission('compras.aprobar', monto_max=5000000)`.
**Esfuerzo: 3-4 semanas.**

#### Brecha #4: Audit log inmutable
**Problema:** hay log parcial (`pago_eventos`, `bitacora`) pero no es
sistemático. Cliente de TI pregunta: "¿quién cambió este precio el martes?"
**Solución:** trigger SQL que copie a `audit_log(tabla, fila_id, campo,
valor_antes, valor_despues, usuario, ts)` cualquier UPDATE/DELETE.
+ vista `/admin/audit-log` con filtros.
**Esfuerzo: 2-3 semanas.**

#### Brecha #11: Backup + restore documentado
**Problema:** Render hace backups, pero no tenemos procedimiento DOCUMENTADO
para "si la DB se corrompe, ¿cómo restauramos en <2h?"
**Solución:** runbook + scripts `scripts/backup_full.py` y `scripts/restore.py`
+ test de DR (disaster recovery) trimestral documentado.
**Esfuerzo: 1 semana + cultura.**

### TIER 2 — DIFERENCIAL profesional (4-6 meses)

#### Brecha #5: Soft delete / papelera
**Problema:** si Catalina borra una OC por error, no hay forma de recuperarla.
**Solución:** columna `deleted_at` en tablas core + UI papelera + restore.
**Esfuerzo: 2 semanas.**

#### Brecha #6: API REST documentada (OpenAPI)
**Problema:** tenemos endpoints pero sin spec. Un cliente que quiere
integrarse con su WMS no sabe qué llamar.
**Solución:** Flask-RESTX o `apispec` → genera `/api/docs` Swagger UI.
**Esfuerzo: 2-3 semanas.**

#### Brecha #7: Webhooks salientes
**Problema:** Cuando se aprueba una OC, Cortex no avisa a sistemas externos.
**Solución:** tabla `webhooks(evento, url, secret)` + worker que dispara POST
al ocurrir el evento. Con retry exponencial.
**Esfuerzo: 2 semanas.**

#### Brecha #12: Logs centralizados (Sentry)
**Problema:** si algo falla en producción, miramos logs de Render. No hay
alertas, no hay agrupación de errores.
**Solución:** Sentry SDK (gratis hasta 5K eventos/mes). Para uptime: BetterStack.
**Esfuerzo: 1 semana.**

### TIER 3 — INTERNACIONALIZACIÓN (cuando vendamos fuera de COL)

#### Brecha #8: Multi-idioma (i18n)
**Problema:** todo en español. Para vender a México, Perú, Chile da igual.
Para vender a Brasil, USA, Europa, no.
**Solución:** Flask-Babel + extraer todos los strings a `messages.po` →
inglés / portugués. **Esfuerzo: 4-6 semanas (mucho texto que extraer).**

#### Brecha #9: Multi-moneda
**Problema:** todo en COP. Si vendemos a ANIMUS US o un cliente extranjero,
falta tipo de cambio.
**Solución:** tabla `tipo_cambio(moneda, fecha, valor_cop)` con job que
trae datos del Banrep. Cada documento puede tener moneda y se reporta en
COP funcional.
**Esfuerzo: 3-4 semanas.**

#### Brecha #10: Workflow engine
**Problema:** hoy los flujos están hardcoded. Cliente quiere "OC > $10M
debe pasar por dos aprobaciones" → cambio de código.
**Solución:** Camunda Lite o construir mini-engine con tabla `workflows` +
estados + transiciones.
**Esfuerzo: 6-8 semanas. (Postergable.)**

---

## 3. Lo que NO se resuelve con código

### Certificaciones (TIER 0 enterprise — sin esto no entras a corporativos grandes)

#### ISO 27001
- **Qué es:** estándar internacional de seguridad de información.
- **Costo año 1:** $25K-40K USD (consultor + auditor + remediaciones)
- **Tiempo:** 8-12 meses
- **Cuándo:** cuando tengas 3-5 clientes y empieces a hablar con corporativos
- **Recomendación:** **no antes de mid-2026**. Es prematuro.

#### SOC 2 Type II
- Más enfocado a SaaS USA/multinacionales
- Costo y tiempo similar a ISO 27001
- **Cuándo:** solo si vamos a vender afuera de LATAM

#### Habeas Data Colombia (Ley 1581 de 2012)
- **Costo:** ~$3-8M COP (abogado + registro SIC)
- **Tiempo:** 1-2 meses
- **Cuándo:** ANTES del primer cliente externo
- **Acción:** redactar Política de Tratamiento de Datos + registrar BD ante SIC

### SLA contractual
- **Qué es:** compromiso escrito de "estaremos arriba el 99.9% del tiempo"
- **Implica:** monitoreo activo (BetterStack/Pingdom), créditos por
  incumplimiento, alguien de guardia
- **Costo monitoreo:** $25-100 USD/mes
- **Costo "alguien de guardia":** sueldo de junior dev o contrato con freelancer
- **Cuándo:** desde el primer cliente externo

### Soporte
- **Email-only:** ya lo damos a Catalina/Luz
- **Email + WhatsApp Business + Slack Connect:** estándar SaaS COL
- **Telefónico:** no, salvo enterprise
- **Inversión:** Zendesk Suite Team ($55 USD/usuario/mes) cuando seamos
  3+ vendiendo. Antes, Gmail + plantillas.

---

## 4. Roadmap sugerido para "nivel enterprise"

### Fase 1 — Q3 2026 (Jul-Sep): Brechas Tier 1
- Brechas #2 (SSO Google) — 2 semanas
- Brecha #4 (audit log) — 3 semanas
- Brecha #11 (backup runbook) — 1 semana
- Brecha #3 (RBAC granular) — 4 semanas

**Costo:** ~10 semanas dev = ~$30M COP si lo haces tú.
**Hito:** podemos venderle a labs medianos con confianza.

### Fase 2 — Q4 2026 (Oct-Dic): Multi-tenant
- Brecha #1 (multi-tenant single-DB) — 8 semanas
- Brecha #5 (soft delete) — 2 semanas
- Brecha #12 (Sentry) — 1 semana

**Costo:** ~11 semanas dev.
**Hito:** primer cliente externo en producción.

### Fase 3 — Q1 2027 (Ene-Mar): API + integraciones
- Brecha #6 (OpenAPI docs) — 3 semanas
- Brecha #7 (webhooks) — 2 semanas
- Habeas Data registro SIC — 1 mes paralelo

**Hito:** 3 clientes y partners empiezan a integrar.

### Fase 4 — Q2-Q4 2027: Confianza enterprise
- Empezar ISO 27001 (8-12 meses)
- Multi-idioma + multi-moneda
- Workflow engine

**Hito:** 10+ clientes, ARR $1B+ COP, listos para Latam.

---

## 5. ¿Realmente queremos competir con SAP?

**No.** SAP S/4HANA cuesta $5K-50K USD/usuario/año, vendido a Top 500.
Su barrera no es funcional, es organizacional (ya está en el cliente,
nadie lo saca).

### Donde SÍ podemos competir directo:

**Odoo Community (gratis)** y **Odoo Enterprise ($31 USD/usuario/mes)**
en el segmento **labs cosméticos / farma / nutracéuticos colombianos**.

**Por qué les ganamos:**
1. **Vertical:** ellos son ERP genérico, nosotros sabemos de cosméticos
2. **DIAN-nativo:** no addon, está integrado al diseño
3. **IA-first:** tenemos asistente IA conectado a todos los datos
4. **Implementación rápida:** Odoo en un lab toma 6-12 meses con consultor.
   Cortex Labs en 4-6 semanas.
5. **Precio Colombia-realista:** USD ajustado a poder adquisitivo local
6. **Soporte en español 100%, hora COL**

### Donde NO debemos competir:
- Empresas Top 500 que ya usan SAP/Oracle — perdido por estructura
- Empresas con TI fuerte que prefieren Odoo Enterprise self-hosted —
  perdido por escala de soporte
- Industrias no-cosméticas (alimentos, retail, manufactura no farmacéutica) —
  fuera del foco

---

## 6. Decisiones que necesitamos de Sebastián

1. **¿Q3 2026 dedicamos a brechas Tier 1?** (Sí/No)
2. **¿Validamos primer cliente externo Q4 2026?** (Sí/No, ¿quién?)
3. **¿Empezamos Habeas Data SIC en mayo 2026?** (Sí/No)
4. **¿Contratamos consultor ISO 27001 en Q3 2027?** (Sí/No)
5. **¿Cuándo paramos de "hacer features" y empezamos a "endurecer plataforma"?**

---

## 7. Resumen ejecutivo

| Pregunta | Respuesta honesta |
|---|---|
| ¿Somos Odoo? | 65% de la funcionalidad, mejor en cosméticos, peor en plataforma |
| ¿Somos SAP? | No, ni queremos ser |
| ¿Podemos vender HOY a otro lab COL? | Sí, **con riesgo aceptable** si el cliente entiende que somos v1.0 |
| ¿Podemos vender HOY a corporativo Top 500? | No |
| ¿Cuánto para "enterprise serio"? | 12-18 meses + $300-500M COP de inversión |
| ¿Vale la pena? | Sí, si llegamos a 20 clientes el margen es 80%+ |

---

**Siguiente paso recomendado:** leer `ROADMAP_MOVIL_NATIVO.md` — para
que la app esté en App Store y Play Store (no solo PWA).
