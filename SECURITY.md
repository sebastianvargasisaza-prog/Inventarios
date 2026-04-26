# Seguridad — Inventarios HHA Group

Documento de referencia para el estado de seguridad y los pendientes que requieren configuración manual en Render.

---

## Estado actual

### ✅ Implementado

- **Autenticación**: sesión Flask con `HTTPONLY`, `SECURE`, `SAMESITE=Lax`, expiración 30 días, timeout idle 8h.
- **Hash de passwords**: soporte PBKDF2 (`werkzeug.security.check_password_hash`). Activo si la env var empieza con `pbkdf2:`.
- **Rate limiting**: por IP **y** por (IP, username) — 5 intentos / 15 min lockout. SQLite-backed, multi-worker safe.
- **Auth en API**: `before_request` rechaza con 401 cualquier `/api/*` sin sesión (excepto `/api/login`, `/api/health`).
- **CSRF protection (light)**: `before_request` valida `Origin`/`Referer` en POST/PUT/DELETE/PATCH. Bloquea CSRF clásico sin requerir tokens en frontend.
- **Headers de seguridad**: `X-Frame-Options=SAMEORIGIN`, `X-Content-Type-Options=nosniff`, `Strict-Transport-Security`, `Referrer-Policy=strict-origin-when-cross-origin`.
- **Logging estructurado**: cada request loguea `request_id` (UUID4 truncado) → correlación entre workers. Errores 5xx capturan stack trace.
- **Validación de config al startup**: `validate_config()` emite warnings JSON estructurados si faltan secretos críticos.
- **WAL mode + busy_timeout 5s**: SQLite seguro con N workers Gunicorn.

### ⚠️ Pendientes que REQUIEREN tu acción en Render

Estos no pueden arreglarse desde el código — necesitan que configures variables de entorno.

#### 1. CRÍTICO — Migrar passwords plaintext a PBKDF2

Hoy: `config.py` tiene fallbacks plaintext (`hha2026`, `espagiria2026`, `animus2026`) si las env vars `PASS_<USER>` no están en Render.

**Pasos**:

```bash
# 1. Genera los hashes localmente (NO van a git)
cd Inventarios
python scripts/gen_password_hashes.py
# Te pide cada password en pantalla, no se guarda en disco

# 2. Copia el output (PASS_SEBASTIAN=pbkdf2:..., etc.) a:
#    Render Dashboard → Service "inventarios" → Environment
#    Pega cada variable y guarda

# 3. Render redeployará. Confirma que cada usuario puede entrar.

# 4. Una vez validado, AVÍSAME en Claude para que elimine los
#    fallbacks plaintext de config.py (cierra el riesgo).
```

#### 2. CRÍTICO — `SECRET_KEY` en Render

Hoy: `index.py:45` tiene un fallback `'hha-group-2026-secretkey-x9kq'` si la env var no existe. Permite falsificar sesiones.

**Pasos**:

```bash
# 1. Genera un SECRET_KEY aleatorio
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Pégalo en Render → Service → Environment → SECRET_KEY

# 3. Avísame en Claude y elimino el fallback hardcoded.
```

#### 3. ALTO — `FORMULA_PIN` en Render

Hoy: si la env var no existe (o vale `7531`), el sistema genera un PIN aleatorio efímero (cambia en cada redeploy). Eso deshabilita el desbloqueo de fórmulas hasta que lo configures.

**Pasos**:

```bash
# 1. Decide el PIN (mín. 6 dígitos, idealmente 8-12)
# 2. Pégalo en Render → Environment → FORMULA_PIN
```

#### 4. MEDIO — API keys de integraciones

Si quieres usar las integraciones, configura en Render:

| Variable | Necesaria para |
|---|---|
| `ANTHROPIC_API_KEY` | Agencia Ads + agentes ÁNIMUS |
| `GHL_API_KEY` + `GHL_LOCATION_ID` | GoHighLevel sync |
| `SHOPIFY_TOKEN` + `SHOPIFY_SHOP` | Shopify sync |
| `INSTAGRAM_TOKEN` + `INSTAGRAM_USER_ID` | Instagram sync |
| `META_APP_ID` + `META_APP_SECRET` | Refresh token Instagram |
| `EMAIL_REMITENTE` + `EMAIL_PASSWORD` | Notificaciones SMTP |

`validate_config()` listará cuáles faltan en los logs al startup.

---

## Items de seguridad no resueltos (refactor multi-sesión)

### CSP sin `'unsafe-inline'`

Hoy: `auth.py:142` permite `'unsafe-inline'` en `script-src` y `style-src`. Necesario porque todos los templates en `api/templates_py/` tienen JS y CSS inline.

**Para arreglarlo**: migrar inline scripts/styles a archivos servidos por Flask con headers `nonce` o `hash`. ~6-10 horas de refactor.

### CSRF tokens explícitos (defense in depth)

El Origin/Referer check actual bloquea CSRF estándar. Para defense-in-depth, agregar `Flask-WTF` con tokens en cada form/AJAX. ~4-6 horas.

### Migración SQLite → Postgres

Hoy: SQLite con WAL aguanta tu carga actual. Si crece a >50 users concurrentes con writes frecuentes, vas a tener locks.

**Para escalar**: usar Render Postgres (managed). ~1 día (schema + migración de datos + cambio de drivers en `database.py`).

### Eliminar inline templates

Los archivos `api/templates_py/*_html.py` son strings Python gigantes con HTML+CSS+JS inline. Migrar a Jinja2 templates en `api/templates/` separa concerns y habilita CSP nonce-based.

---

## Cómo verificar el estado actual

Después de cada deploy en Render, busca en los logs:

```
"category":"config_validation"
```

Cada línea con esa categoría es un issue de config detectado. Severidades:
- `CRITICAL`: passwords/SECRET_KEY plaintext o fallback público
- `HIGH`: hashes legacy o fallbacks no-pbkdf2
- `MEDIUM`: FORMULA_PIN sin configurar
- `INFO`: integraciones opcionales sin credenciales

Cuando todos los CRITICAL estén resueltos, esta sección dejará de aparecer en los logs.

---

## Reportar incidentes

Si detectas un comportamiento sospechoso (logins inesperados, datos modificados sin razón, errores 403 inusuales):

1. Abre logs en Render: `Service → Logs`
2. Filtra por `event="login_failure"` o `event="csrf_blocked"` o `level="ERROR"`
3. El `request_id` de cada error es buscable — copia el ID y rastrea toda la cadena de la sesión.

Para un fix urgente, documentar el `request_id` afectado y el rango de tiempo (UTC).
