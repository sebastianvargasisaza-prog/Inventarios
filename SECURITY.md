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

## Decisiones aplazadas (documentadas para futuro)

Tres ítems del roadmap NO se implementan en el estado actual. Esta sección documenta qué son, por qué se aplazan, y cuándo ejecutarlos.

### B. CSP sin `'unsafe-inline'` — APLAZADO

**Estado actual**: el CSP permite `'unsafe-inline'` en `script-src` y `style-src` porque los templates en `api/templates_py/` tienen JS+CSS embebido. Lo que SÍ está activo (defense in depth):
- `frame-ancestors 'none'` (anti clickjacking moderno)
- `form-action 'self'` (forms solo van a este host)
- `base-uri 'self'` (anti rebase URL injection)
- `object-src 'none'` (no plugins/applets)
- `Cross-Origin-Opener-Policy: same-origin`

**Cuándo implementar el resto**:
- Cuando la app deje de ser solo interna (clientes externos pueden inyectar contenido)
- Cuando se incorpore renderizado de input de usuarios (markdown, comentarios) que pueda contener HTML
- Cuando se descubra cualquier XSS real (lección reactiva)

**Cómo implementar** (~6-10 horas):
1. Migrar `api/templates_py/*.py` a Jinja2 templates en `api/templates/` (ítem E5).
2. Generar `request.csp_nonce = secrets.token_urlsafe(16)` en `before_request`.
3. Inyectar `nonce="{{ csp_nonce }}"` en cada `<script>` y `<style>`.
4. Cambiar CSP a `script-src 'self' 'nonce-XXX'` y eliminar `'unsafe-inline'`.

### C. CSRF tokens explícitos — IMPLEMENTADO

`X-CSRF-Token` header validado contra `session['csrf_token']`. Capa adicional sobre el Origin/Referer check existente. Endpoint `/api/csrf-token` para que el frontend lo lea. **Backwards compatible**: si el frontend NO lo envía, sigue funcionando con sólo el Origin check.

### D. Migración SQLite → Postgres — APLAZADO

**Estado actual**: SQLite con WAL mode + busy_timeout 5s + 3 workers Gunicorn. Soporta múltiples lectores + 1 escritor concurrente sin locks observables hasta ~30-50 users haciendo writes simultáneos.

**Por qué NO migrar ahora**:
1. **Cero beneficio HOY**: la app tiene 19 users máximo. SQLite es perfectamente adecuado.
2. **Riesgo alto**: hay 600+ archivos SQL con queries que pueden ser SQLite-specific (`INSERT OR IGNORE`, `INSERT OR REPLACE`, `datetime('now', 'utc')`, `PRAGMA`). Migrar a Postgres requiere validar cada uno.
3. **Costo**: $7/mes (Render Postgres Starter) + 1-2 días de trabajo + ventana de migración con downtime.
4. **SQLite tiene ventajas operacionales**: 1 archivo, fácil backup (ya tenemos), sin red entre app y DB.

**Cuándo migrar** (señales claras):
- Logs muestran "database is locked" recurrente
- Latencia de writes > 500ms percentil 95 sostenido
- Usuarios concurrentes activos > 30 simultáneamente
- Necesidad de réplicas read-only o multi-región

**Plan de migración** (cuando llegue el momento, ~1-2 días):
1. Crear Render Postgres database
2. Setear env var `DATABASE_URL=postgresql://...`
3. Refactorizar `database.py:get_db()` para usar `psycopg2.connect(DATABASE_URL)` si la env var está, fallback SQLite
4. Identificar y portar queries SQLite-specific (búsqueda: `INSERT OR`, `PRAGMA`, `datetime\(`)
5. Migrar datos: `sqlite3 inventario.db .dump | psql $DATABASE_URL` con ajustes manuales
6. Validar con tests existentes apuntando a Postgres
7. Switch en producción durante ventana de mantenimiento

### E5. Migrar templates inline a Jinja2 — APLAZADO

**Estado actual**: 19 archivos en `api/templates_py/` son strings Python gigantes con HTML+CSS+JS embebido (algunos > 2000 líneas).

**Por qué NO migrar ahora**:
1. **Funciona perfectamente** — no hay bug que arreglar
2. **Riesgo de UX**: cualquier escape mal hecho rompe alguna pantalla en producción
3. **Beneficio bajo en aislado**: el principal valor es habilitar CSP nonce (B), que también está aplazado

**Cuándo migrar**:
- Cuando se decida implementar B (CSP nonce)
- Cuando se contrate más devs y la lectura/edición de templates monolíticos sea cuello de botella
- Cuando se necesite reutilizar componentes entre módulos

**Plan de migración** (~1 día por cada 5 templates):
1. `pip install Jinja2` (ya viene con Flask)
2. Crear `api/templates/` con archivos `.html` separados
3. Renderizar con `flask.render_template('foo.html', usuario=...)` en lugar de `Response(FOO_HTML.replace('{usuario}', ...))`
4. Migrar de a uno: dashboard → marketing → admin → resto
5. Mantener `templates_py/*.py` paralelo durante migración (feature flag)
6. Eliminar `templates_py/` cuando todos migrados

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
