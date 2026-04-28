# Roadmap hacia SaaS multi-tenant — HHA Group → Producto

> Cuando estés listo para vender el sistema a otros laboratorios cosméticos
> colombianos, este documento es la hoja de ruta técnica + comercial.
> Hoy NO está implementado, es plan estratégico.

---

## Contexto

Sebastián construyó este sistema para HHA Group (Espagiria + ÁNIMUS Lab).
Actualmente tiene cosas que NINGÚN ERP/SaaS comercial le da:
- Diagnóstico automático de fórmulas con corrección INCI
- Versionado de fórmulas con snapshot
- Comunicación interna con RACI + parser actas comité Gemini
- Sync Shopify automático a flujo financiero
- IA agentes (Claude) integrados para análisis
- Cumplimiento INVIMA + SOPs vencimiento
- Pipeline maquila B2B (cuando se reactive)

**Mercado potencial Colombia:**
- ~80-150 laboratorios cosméticos pequeños/medianos
- ~30-50 laboratorios farmacéuticos genericos
- ~100+ marcas DTC que también necesitan sistema operativo

**Posicionamiento:** "ERP especializado para laboratorios cosméticos colombianos"
con vertical depth que SAP/Odoo no dan + integración local (DIAN, SIIGO,
Shopify, GoHighLevel).

---

## Fases del salto SaaS

### Fase 0 — Hardening (DONDE ESTAMOS)
- ✅ Sistema operacionalmente sólido
- ✅ Tests 278+ pasando
- ✅ Multi-empresa P&L (Espagiria + ÁNIMUS) ya separado
- ✅ Aislamiento por roles (CEO/Mayra/Catalina/Luz/etc.)
- 🔴 Falta: branch protection + CI bloqueante
- 🔴 Falta: rate limiting global (ya hay parcial)
- 🔴 Falta: backups con encriptación + restore testing periódico

### Fase 1 — Refactor Multi-Tenant (3-4 meses)

**Schema:**
- Agregar `tenant_id` a TODAS las tablas (35+ migraciones idempotentes)
- Crear `tenants` con: id, slug, nombre_empresa, plan, created_at, billing_status
- Crear `tenant_users` para relación M:N (un usuario puede pertenecer a varios tenants — útil para Sebastián como super-admin)

**Auth:**
- Subdomain routing: `cliente1.hha-erp.com`, `cliente2.hha-erp.com`
- O path-based: `app.hha-erp.com/t/cliente1/modulos`
- Cada request lleva contexto de tenant en sesión + middleware que filtra TODOS los queries
- Aislamiento estricto: tests que validan que cliente A NUNCA vea datos de cliente B

**Provisioning:**
- Onboarding wizard: nombre empresa, NIT, logo, primer admin user
- Schema seed: catálogo MPs base, plantillas SOPs comunes, calendario cosmético genérico
- Configuración Shopify/SIIGO/email opcional

**Estimación: 200-300 horas de desarrollo + tests aislamiento exhaustivos.**

### Fase 2 — Billing + Comercial (1-2 meses)

**Pricing modelo sugerido:**

| Plan | Precio mensual | Incluye |
|---|---|---|
| **Lab Starter** | $290.000 COP | Inventario + Compras + Calidad + 5 usuarios + 100 OCs/mes |
| **Lab Pro** | $590.000 COP | + Marketing + Tesorería + 15 usuarios + 500 OCs/mes + IA básica |
| **Lab Enterprise** | $1.290.000 COP | + Multi-empresa + Maquila + ilimitado + IA premium + onboarding asistido |
| **Add-on DIAN** | $190.000 COP | E-factura timbrada via PSP integrado |
| **Add-on Shopify** | $90.000 COP | Sync automático ventas |

**Setup fee:** $1.5M-$3M COP por cliente (onboarding + migración datos + capacitación 5h).

**Pricing internacional (LATAM):**
- USD: $79 / $159 / $349 mensual (planes equivalentes)
- Mercado: México, Perú, Chile (similares regulaciones cosméticas)

**Integraciones billing:**
- Wompi o MercadoPago para Colombia
- Stripe para internacional
- Webhook → upgrade/downgrade plan automático
- Suspensión por mora >30 días (read-only) → bloqueo total >60 días

### Fase 3 — Onboarding Self-Service (1 mes)

**Flujo:**
1. Cliente entra a `hha-erp.com` → "Probar gratis 14 días"
2. Form: empresa, NIT, email, teléfono
3. Auto-crea tenant + admin user + envia password
4. Wizard 6 pasos:
   - Logo + colores (white-label)
   - Empresas del holding (1 a N)
   - Productos terminados base
   - Catálogo MPs inicial (CSV upload o seleccionar de plantilla cosmética)
   - Usuarios + roles
   - Integraciones (Shopify, email, etc.)
5. Invita su equipo
6. Demo automatizado: dashboard precargado con datos sintéticos
7. Día 14: convertir a pagado o downgrade a free tier (limitado)

### Fase 4 — Marketing + Ventas (continuo)

**Inbound:**
- Landing page con casos de uso cosmética
- Blog: "Cómo automatizar control de calidad ISO 22716"
- LinkedIn campañas a directores técnicos / dueños labs
- Comparativa SAP vs HHA-ERP (precio, vertical, tiempo onboarding)

**Outbound:**
- Sebastián vende los primeros 5-10 clientes (referencias en gremio cosmético)
- ANDI Cámara de la Industria Cosmética → presentación
- Conferencias INCOSMETICS LATAM, Cosmoprof
- Partnerships con consultorías regulatorias (ellas recomiendan tu sistema)

**Ventas:**
- Mes 6: contratar 1 SDR (Sales Development Rep) cuando llegues a $5M MRR
- Mes 12: 1 AE (Account Executive) para enterprise + 1 Customer Success

---

## Métricas objetivo

| Mes 6 | Mes 12 | Mes 24 |
|---|---|---|
| 5 clientes activos | 25 clientes | 80 clientes |
| MRR $4M COP | MRR $25M COP | MRR $90M COP |
| ARR $48M COP | ARR $300M COP | ARR $1.080M COP |

A mes 24 el SaaS factura ~$1B COP/año, lo cual lo hace negocio independiente
y vendible (múltiplo SaaS x4-x6 = $4-6B valoración).

---

## Decisiones que necesitas tomar (cuando arranquemos)

1. **¿Multi-tenant o multi-instance?**
   - Multi-tenant: 1 base de datos compartida con tenant_id (más eficiente, requiere aislamiento perfecto)
   - Multi-instance: 1 BD por cliente (más simple, más caro de operar a escala)
   - Mi voto: multi-tenant con SQLite por ahora, migrar a Postgres con RLS cuando >50 clientes

2. **¿Cobrar onboarding o gratis?**
   - Cobrar: filtra clientes serios, da revenue inmediato
   - Gratis: reduce fricción de venta
   - Mi voto: cobrar setup de $1.5M para Pro/Enterprise, gratis para Starter

3. **¿Vertical solo cosmética o ampliar?**
   - Cosmética puro: domain expertise, defensibilidad
   - Cosmética + farma + nutracéuticos: 3x mercado pero diluye el message
   - Mi voto: Año 1 solo cosmética, Año 2 expandir a farma genéricos

4. **¿Tú eres CEO del SaaS o lo separas de HHA Group?**
   - Si es spin-off: necesita razón social separada, equipo dedicado, levantamiento capital
   - Si queda en HHA: aprovechas equipo actual pero limitas crecimiento
   - Mi voto: año 1 dentro de HHA (validar PMF), año 2 spin-off + raise

---

## Lo que YA tienes hecho que acelera el salto

- Schema migration system robusto (38+ aplicadas, idempotente, multi-worker safe)
- Backups automáticos
- Tests E2E
- Email notifications system
- IA Claude integrada
- Sync Shopify
- Multi-empresa P&L
- Auth con roles
- Audit log
- Rate limiting parcial
- CSRF protection
- Mobile responsive (parcial)
- PWA instalable

**Estimación de salto a v1 SaaS comercial: 4-6 meses dedicados.**

Cuando estés listo, dime y empezamos por Fase 0 hardening + diseño multi-tenant detallado.
