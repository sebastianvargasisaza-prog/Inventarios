# Seguridad base EOS · 12-may-2026

Estado actual de la infraestructura de seguridad y los pasos pendientes para
tener una app de producción sólida lista para el primer cliente (Espagiria).

## ✅ Lo que YA está hecho (no tocar)

| Pieza | Estado | Detalle |
|---|---|---|
| SQLite WAL mode | ✅ activo | `journal_mode=WAL`, mejor concurrencia y seguridad |
| Synchronous FULL en prod | ✅ activo | Máxima durabilidad de escrituras |
| Backups automáticos | ✅ activo | `api/backup.py` con verificación integrity_check |
| Cron integrity check | ✅ activo | `cron_db_integrity_check` corre quick_check + alerta SEC HIGH si falla |
| Tabla `db_health_log` | ✅ migración 102 | Histórico de checks para detección de drift |
| Sistema emergency restore | ✅ probado 12-may | Procedure documentado, funcionó en incidente real |
| Audit log | ✅ activo | tabla `audit_log` con categorías |
| Rate limiting login | ✅ activo | 5 intentos, lockout 15 min |
| CSRF protection | ✅ activo | 2 capas (Origin/Referer + token) |
| Auth global `/api/*` | ✅ activo | `require_auth_for_api` en `auth.py` |
| MFA TOTP framework | ✅ implementado | `blueprints/mfa.py`, 551 líneas, pyotp + backup code |
| Headers de seguridad | ✅ activo | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |
| Cloudflare proxy | ✅ activo | DDoS L3/L4, SSL/TLS 1.3, CDN global, rate limit básico |

## 🆕 Cambio aplicado en esta sesión (rama `feature/seguridad-y-batch-base`)

**`api/auth.py` — Enforcement de MFA para usuarios `ADMIN_USERS`:**

- Nuevo helper `_user_has_mfa_active(username)` consulta `users_mfa`
- Nuevo hook `enforce_mfa_for_admins` en `register_hooks`
- Política:
  - Admin sin MFA puede **leer** y navegar (GET) para llegar al setup
  - Admin sin MFA NO puede ejecutar **mutaciones** (POST/PUT/DELETE/PATCH)
    excepto endpoints del propio setup MFA
  - Bandera `session['mfa_warning']=True` para banner UI
- Bypass automático en testing mode (`app.testing` o pytest)
- Paths exentos: `/login`, `/logout`, `/api/mfa/*`, `/login/mfa`, `/seguridad`,
  `/api/csrf-token`, `/api/health`, `/static/`, `/favicon`

**Why:** phishing de password de admin sin MFA = compromiso total del holding
HHA Group (Espagiria + Animus + EOS). MFA es P0 según audit zero-error
30-abr-2026.

## 🔴 Lo que TÚ tienes que hacer (acciones manuales)

### 1. Activar TU MFA (Sebastián svargas) — **HOY mismo** · 2 minutos

Sin esto, el día que mergees este branch a `main` y deploy a prod, **te vas a
auto-bloquear de hacer mutaciones**. Sí, el cambio te aplica a ti también.

**Pasos:**
1. Entra a https://app.eossuite.com/login con tu usuario `sebastian`
2. Una vez logueado, ve a https://app.eossuite.com/seguridad
3. Click en "Activar MFA"
4. Escanea el QR con **Google Authenticator** / **Authy** / **1Password** / **Microsoft Authenticator**
5. Pega el código de 6 dígitos para confirmar
6. **Guarda el backup code** en un lugar seguro (1Password, papel, donde sea)

### 2. Activar MFA para Alejandro · 2 minutos

Mismo proceso con su usuario `alejandro`. Su MFA es **doble seguro**: si
pierdes el tuyo, él puede llamar `/api/mfa/admin-disable` para deshabilitar
tu MFA y recuperarte.

### 3. Verificar plan Cloudflare (no urgente, 1 minuto)

Entra a https://dash.cloudflare.com y mira esquina superior derecha del dominio
`eossuite.com`. Si dice **"Free"** → todo OK, ya tienes lo que necesitamos.
Si dice **"Pro"/"Business"** → confirma cuánto pagas/mes para ajustar el
inventario de costos.

### 4. Cloudflare R2 — postpone hasta que generemos PDFs

No hagas esto todavía. Lo activamos cuando construyamos el módulo
`batch_record` y empecemos a generar PDFs/CoAs reales. Costo proyectado: $5/mes.

### 5. DKIM/SPF/DMARC para `eossuite.com` — postpone

También cuando arranquemos email transaccional con Resend. Por ahora, los
emails desde SMTP genérico funcionan limitadamente.

## 📊 Costos totales hoy (verificado en tu dashboard Render)

| Servicio | Plan | USD/mes |
|---|---|---|
| Render Web Service "Inventarios" | Standard | $25.25 |
| Render PostgreSQL "inventarios-db" | Free | $0 |
| Cloudflare DNS + Pages + Proxy | Free | $0 |
| GitHub + Actions | Free | $0 |
| Sentry | Free tier | $0 |
| **TOTAL** | | **$25 USD/mes** |

## 📋 Roadmap de infra (en orden de prioridad real)

| # | Cambio | Cuándo | Costo |
|---|---|---|---|
| 1 | Activar MFA admin (manual) | HOY | $0 |
| 2 | Merge `feature/seguridad-y-batch-base` a main | Cuando tu MFA esté activo | $0 |
| 3 | Construir módulo `batch_record` (absorber MYBATCH) | Próximas 10 semanas | $0 |
| 4 | Cloudflare R2 (cuando generemos PDFs masivos) | Sprint 2 del batch_record | +$5/mes |
| 5 | Resend + DKIM/SPF (cuando saquemos email serio) | Sprint 3 del batch_record | $0 |
| 6 | Render Background Worker (si concurrencia crece) | Cuando llegue 2do cliente | +$7/mes |
| 7 | Migrar SQLite → Postgres (ya hay BD provisionada free) | Cuando BD llegue a 800MB o crezcan los workers | $0 |
| 8 | Cloudflare Pro WAF managed rules | Cuando llegue 1er cliente externo | +$20/mes |
| 9 | Staging environment | Cuando llegue 2do cliente externo | +$25/mes |
| 10 | SOC 2 Type I + pentest | Cuando llegue 1er Enterprise | $15K USD una vez |

## 🚨 NO hagas esto

- ❌ NO merges este branch a `main` antes de activar TU MFA. Te bloqueas a ti
  mismo.
- ❌ NO compartas tu backup code con nadie. Si lo necesitas, está en tu 1Password.
- ❌ NO deshabilites MFA de Alejandro sin coordinar — pierdes la red de seguridad.
