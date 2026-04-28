# Pendientes que requieren tu acción (Sebastián)

> Lista de los puntos del roadmap que NO puedo hacer yo solo — necesitan
> credenciales, contratos comerciales o decisiones de negocio que solo
> tú puedes tomar.

---

## 🔴 Acción inmediata (15 min cada uno)

### #4 — Configurar EMAIL_USERS faltantes en Render

Hoy tenemos 14 usuarios mapeados pero solo unos pocos tienen email
configurado. Para que las notificaciones de tareas RACI lleguen a
todos, agrega estas env vars en Render:

```
EMAIL_HERNANDO=hernando@tu-dominio.com
EMAIL_CATALINA=catalina@tu-dominio.com
EMAIL_LUZ=luz@tu-dominio.com
EMAIL_DANIELA=daniela@tu-dominio.com
EMAIL_ALEJANDRO=alejandro@tu-dominio.com
EMAIL_MIGUEL=miguel@tu-dominio.com
EMAIL_FELIPE=felipe@tu-dominio.com
EMAIL_VALENTINA=valentina@tu-dominio.com
EMAIL_MAYRA=mayra@tu-dominio.com
EMAIL_EVELIN=evelin@tu-dominio.com
EMAIL_GISSETH=gisseth@tu-dominio.com
EMAIL_LAURA=laura@tu-dominio.com
```

Render → tu servicio → Environment → Add Environment Variable. Copy/paste
una por una. **No requiere redeploy** (las env vars se leen al request
time, no al startup).

### #18 — Branch protection en GitHub (CI/CD bloqueante)

El workflow `tests.yml` ya existe y corre pytest. Pero hoy un push
con tests rojos NO está bloqueado. Para hacerlo bloqueante:

1. GitHub → repositorio → Settings → Branches → Branch protection rules → Add rule
2. Branch name pattern: `main`
3. Activar:
   - ☑ Require a pull request before merging
   - ☑ Require status checks to pass before merging
   - ☑ Buscar y agregar el check `tests`
   - ☑ Require branches to be up to date
4. Save

**Resultado:** push directo a main bloqueado si tests fallan. Ahora forzamos PR + tests verdes.

---

## 🟡 Decisión + contrato comercial (1-2 semanas)

### #15 — Factura electrónica timbrada DIAN via PSP

Hoy emitimos facturas con PDF + numeración propia, pero NO están
timbradas electrónicamente con la DIAN. Para venta a clientes B2B
(Fernando Mesa) eso es regulatorio.

**Opciones de PSP autorizado:**

| PSP | Plan inicial | Timbrado | Integración |
|---|---|---|---|
| **Carvajal** | desde $200K/mes | ilimitado | API REST |
| **FacturaTech** | desde $90K/mes | hasta 100/mes | API REST |
| **The Factory HKA** | desde $180K/mes | ilimitado | API REST + SDK |
| **Siigo** | tienes export, falta integrar e-factura | ilimitado | API |

**Lo que tú haces:**
1. Decidir PSP según volumen mensual estimado de facturas
2. Firmar contrato + obtener API credentials
3. Pasarme: API key, URL endpoint, NIT del emisor

**Lo que yo hago después:**
1. Endpoint nuevo `POST /api/contabilidad/facturas/<num>/timbrar`
2. Llamada al PSP con XML/JSON de la factura
3. Guarda CUFE + URL del XML timbrado en la factura
4. Si PSP responde error, queda en estado `Pendiente Timbrado` con razón

~12h de implementación + tests cuando tenga las credenciales.

---

## 🟢 Decisión de negocio (Q3-Q4 2026)

### #19-21 — SaaS multi-tenant para vender el sistema

Este es el salto grande. Cuando estés listo para vendelo a otros
laboratorios cosméticos colombianos, el sistema necesita:

**Decisiones de producto que tú tienes que tomar:**

1. **Pricing**:
   - ¿Mensual fijo? ($ COP por usuario, por mes)
   - ¿Por volumen de transacciones? (X OCs/mes incluido, plus por excedente)
   - ¿Tier por features? (Básico = inventario+compras / Pro = + marketing+IA / Enterprise = + multi-empresa)

2. **Onboarding**:
   - ¿Self-service? (cliente nuevo se registra y configura solo)
   - ¿Asistido? (tu equipo configura por ellos en 1-2 semanas, cobras setup fee)
   - ¿White-label? (cada cliente ve su propio branding)

3. **Posicionamiento**:
   - ¿Solo cosmética? (vertical específico — ventaja: domain expertise)
   - ¿Manufactura general? (más mercado pero más competencia con SAP/Odoo)
   - ¿Solo Colombia o LATAM? (regulación DIAN vs facturación global)

4. **Equipo comercial**:
   - ¿Tú vendes los primeros 3-5 clientes?
   - ¿Contratas SDR/AE cuando llegues a $X MRR?

**Lo técnico que viene cuando decidas:**

- **Schema multi-tenant**: agregar `tenant_id` a TODAS las tablas (35+ migrations)
- **Auth con tenant scope**: cada request lleva contexto de empresa
- **Onboarding flow**: wizard de configuración inicial (logo, NIT, productos, usuarios)
- **Billing**: integración con Stripe/MercadoPago/Wompi
- **Aislamiento de datos**: tests exhaustivos que cliente A nunca vea datos de cliente B
- **Migraciones backwards-compatible**: actualización del SaaS sin downtime para 100+ tenants

Estimado: 2-3 meses de trabajo dedicado para versión 1 vendible.

---

## 📋 Resumen de qué hago yo vs qué haces tú

| # | Tarea | Quien |
|---|---|---|
| 1 | Limpiar finanzas en operaciones | ✅ Yo |
| 2 | Migrar compromisos | ✅ Yo |
| 3 | Calidad CoA + especificaciones | ✅ Yo |
| **4** | **Configurar EMAIL_USERS** | **🙋 Tú (15 min)** |
| 5 | PWA instalable | ✅ Yo |
| 6 | Visuales unificados | ✅ Yo |
| 7 | Calidad CAPA + estabilidades | ✅ Yo |
| 8 | Conteos cíclicos Daniela | ✅ Yo |
| 9 | Reporte semanal CEO email | ✅ Yo |
| 10 | Batch records Hernando | ✅ Yo |
| 11 | ROI marketing campañas | ✅ Yo |
| 12 | Conciliación bancaria | ✅ Yo |
| 13 | Aislar admin.py | ✅ Yo |
| 14 | Decisión técnica vs inventario | ✅ Yo (con tu visto bueno arquitectónico) |
| **15** | **Factura electrónica DIAN (PSP)** | **🙋 Tú firma contrato + me das credenciales** |
| 16 | IA agentes propios | ✅ Yo |
| 17 | Multi-empresa P&L separado | ✅ Yo |
| **18** | **CI/CD branch protection** | **🙋 Tú (5 min en GitHub Settings)** |
| **19** | **Multi-tenant SaaS arquitectura** | **🙋 Tú decides + yo implemento (Q4 2026)** |
| **20** | **Onboarding self-service** | **🙋 Tú diseña + yo implemento** |
| **21** | **Pricing y planes comerciales** | **🙋 Tú estrategia comercial** |

**Arrancando con los 17 técnicos en orden de impacto.**
