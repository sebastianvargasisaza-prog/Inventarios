# config.py -- constantes y credenciales del sistema
import os

# Contraseñas por usuario. Cada PASS_<USER> en Render debe ser un hash
# PBKDF2 (ver scripts/gen_password_hashes.py).
#
# Si una env var falta, el usuario queda con string vacío — el flujo de
# login en core.py rechaza correctamente (no matchea ninguna contraseña),
# por lo que ese usuario simplemente no puede entrar hasta que se
# configure su PASS_<USER>. validate_config() reporta cuáles faltan en
# logs estructurados al startup.
def _pwd(env_var):
    """Lee password (hash) desde env var, retorna '' si falta."""
    return os.environ.get(env_var, "").strip()

COMPRAS_USERS = {
    "sebastian":  _pwd("PASS_SEBASTIAN"),
    "alejandro":  _pwd("PASS_ALEJANDRO"),
    "hernando":   _pwd("PASS_HERNANDO"),
    "catalina":   _pwd("PASS_CATALINA"),
    "luz":        _pwd("PASS_LUZ"),
    "daniela":    _pwd("PASS_DANIELA"),
    "valentina":  _pwd("PASS_VALENTINA"),
    "jefferson":  _pwd("PASS_JEFFERSON"),
    "felipe":     _pwd("PASS_FELIPE"),
    "mayra":      _pwd("PASS_MAYRA"),
    "gloria":     _pwd("PASS_GLORIA"),
    "laura":      _pwd("PASS_LAURA"),
    "miguel":     _pwd("PASS_MIGUEL"),
    "yuliel":     _pwd("PASS_YULIEL"),
    "luis":       _pwd("PASS_LUIS"),
    "smurillo":   _pwd("PASS_SMURILLO"),
    "sergio":     _pwd("PASS_SERGIO"),
    "mayerlin":   _pwd("PASS_MAYERLIN"),
    "camilo":     _pwd("PASS_CAMILO"),
}
ADMIN_USERS     = {"sebastian", "alejandro"}
# Mayra (contadora) + Catalina (asistente compras): mismo perfil financiero/contable
CONTADORA_USERS = {"mayra", "catalina"}
# Gloria (sólo RRHH), + asistentes de gerencia (daniela ÁNIMUS, luz Espagiria),
# + contadora/asist. compras (mayra, catalina), + admins.
RRHH_USERS      = {"gloria", "daniela", "luz", "mayra", "catalina", "alejandro", "sebastian"}
CALIDAD_USERS   = {"laura", "miguel", "yuliel", "alejandro", "sebastian"}
PLANTA_USERS    = {"luis", "smurillo", "sergio", "mayerlin", "camilo"}

DB_PATH = os.environ.get("DB_PATH", "/var/data/inventario.db")


# Contraseñas plaintext conocidas que NUNCA deben usarse en producción.
# validate_config() las detecta y emite un warning por cada usuario afectado.
_INSECURE_PLAINTEXT_DEFAULTS = {"hha2026", "espagiria2026", "animus2026"}

# Compras: contabilidad/finanzas + admins. (Daniela y Luz se movieron a marketing
# de su empresa — ya no participan del flujo de compras del holding.)
COMPRAS_ACCESS  = {"catalina", "mayra", "alejandro", "sebastian"}
FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}
# Clientes: contabilidad + asistentes (ventas, gerencias) + admins.
CLIENTES_ACCESS = {"mayra", "catalina", "valentina", "daniela", "luz", "alejandro", "sebastian"}
TECNICA_USERS   = {"hernando", "miguel", "alejandro", "sebastian"}
# Marketing: equipo de marketing + asistentes de gerencia (cada una para su empresa).
MARKETING_USERS = {"jefferson", "felipe", "daniela", "luz", "alejandro", "sebastian"}
# Acceso al módulo ÁNIMUS Lab (skincare): asistente de gerencia + admins.
ANIMUS_ACCESS   = {"daniela", "alejandro", "sebastian"}
# Acceso al módulo Espagiria (pendiente de crear blueprint): asist. gerencia + admins.
ESPAGIRIA_ACCESS = {"luz", "alejandro", "sebastian"}

# PIN para desbloquear vista de cantidades en Fórmulas.
# DEBE setearse via env var FORMULA_PIN. Si falta, se genera un PIN
# aleatorio efímero (cambia en cada redeploy) — equivalente a deshabilitar
# el desbloqueo hasta que se configure correctamente.
import secrets as _secrets
_formula_pin_env = os.environ.get("FORMULA_PIN", "").strip()
if _formula_pin_env and _formula_pin_env != "7531":
    FORMULA_PIN = _formula_pin_env
else:
    # PIN aleatorio de 12 dígitos: nadie lo conoce, efectivamente bloquea
    # el desbloqueo hasta que el admin configure FORMULA_PIN en Render.
    FORMULA_PIN = "".join(_secrets.choice("0123456789") for _ in range(12))
    _FORMULA_PIN_INSECURE = True
del _formula_pin_env, _secrets

# Emails de usuarios para notificaciones (configurar via env vars en Render)
USER_EMAILS = {
    "jefferson":  os.environ.get("EMAIL_JEFFERSON",  "jermun1992@gmail.com"),
    "hernando":   os.environ.get("EMAIL_HERNANDO",   ""),
    "catalina":   os.environ.get("EMAIL_CATALINA",   ""),
    "luz":        os.environ.get("EMAIL_LUZ",        ""),
    "daniela":    os.environ.get("EMAIL_DANIELA",    ""),
    "sebastian":  os.environ.get("EMAIL_SEBASTIAN",  "sebastianvargasisaza@gmail.com"),
    "alejandro":  os.environ.get("EMAIL_ALEJANDRO",  ""),
}


def validate_config():
    """Valida configuración de seguridad al startup.

    No crashea la app — emite warnings estructurados (JSON line) que aparecen
    en los logs de Render/Datadog. El admin los ve y puede priorizar el fix
    sin que se caiga producción.

    Retorna lista de issues encontrados (cada uno: dict con severity, code, msg).
    """
    import json as _json
    import logging as _logging
    from datetime import datetime as _dt

    issues = []

    # SECRET_KEY
    if not os.environ.get("SECRET_KEY"):
        issues.append({
            "severity": "CRITICAL",
            "code": "MISSING_SECRET_KEY",
            "msg": "SECRET_KEY no definido en env. Sesiones falsificables. "
                   "Defínelo en Render → Environment con un valor aleatorio "
                   "(>= 32 chars). Ej: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        })

    # Passwords: detectar plaintext, faltantes (env var no configurada),
    # y usar hash legacy. Sin hash → usuario no puede entrar.
    missing_users = []
    plaintext_users = []
    for user, pwd in COMPRAS_USERS.items():
        if not pwd:
            missing_users.append(user)
        elif pwd in _INSECURE_PLAINTEXT_DEFAULTS:
            plaintext_users.append(user)
        elif not (pwd.startswith("pbkdf2:") or pwd.startswith("scrypt:")):
            # Password custom pero plaintext (no hash) — alguien pegó el
            # password en lugar del hash en la env var. Inseguro.
            plaintext_users.append(user)

    if missing_users:
        issues.append({
            "severity": "HIGH",
            "code": "MISSING_USER_PASSWORD",
            "msg": f"{len(missing_users)} usuario(s) sin password configurada "
                   f"(env var PASS_<USER> ausente). Estos usuarios NO pueden "
                   f"entrar hasta que se configure su variable en Render. "
                   f"Usuarios afectados: {', '.join(missing_users)}"
        })

    if plaintext_users:
        issues.append({
            "severity": "CRITICAL",
            "code": "PLAINTEXT_PASSWORDS",
            "msg": f"{len(plaintext_users)} usuario(s) con password en plaintext "
                   f"en env vars. Las PASS_<USER> deben ser hashes pbkdf2: o "
                   f"scrypt:. Corre 'python scripts/gen_password_hashes.py' y "
                   f"pega los hashes (no las passwords) en Render → Environment. "
                   f"Usuarios afectados: {', '.join(plaintext_users)}"
        })

    # FORMULA_PIN
    if globals().get("_FORMULA_PIN_INSECURE"):
        issues.append({
            "severity": "MEDIUM",
            "code": "MISSING_FORMULA_PIN",
            "msg": "FORMULA_PIN no definido (o usa fallback público '7531'). "
                   "Se generó un PIN aleatorio efímero — el desbloqueo de "
                   "fórmulas no funcionará hasta definir FORMULA_PIN en Render."
        })

    # API keys de servicios externos (advertencia, no crítico)
    optional_keys = {
        "ANTHROPIC_API_KEY": "Agencia Ads no funcionará",
        "GHL_API_KEY":       "GoHighLevel sync deshabilitado",
        "SHOPIFY_TOKEN":     "Shopify sync deshabilitado",
        "INSTAGRAM_TOKEN":   "Instagram sync deshabilitado",
        "META_APP_ID":       "Meta refresh token deshabilitado",
        "EMAIL_PASSWORD":    "Notificaciones por email deshabilitadas",
        "SENTRY_DSN":        "Alertas proactivas de errores deshabilitadas",
    }
    missing_optional = [
        f"{k} ({desc})"
        for k, desc in optional_keys.items()
        if not os.environ.get(k)
    ]
    if missing_optional:
        issues.append({
            "severity": "INFO",
            "code": "MISSING_INTEGRATIONS",
            "msg": f"{len(missing_optional)} integración(es) opcional(es) sin "
                   f"credenciales: {'; '.join(missing_optional)}"
        })

    # Loguear cada issue como línea JSON estructurada
    logger = _logging.getLogger("inventario.config")
    for issue in issues:
        log_entry = {
            "ts":       _dt.utcnow().isoformat() + "Z",
            "level":    issue["severity"],
            "category": "config_validation",
            **issue,
        }
        if issue["severity"] in ("CRITICAL", "HIGH"):
            logger.error(_json.dumps(log_entry, ensure_ascii=False))
        else:
            logger.warning(_json.dumps(log_entry, ensure_ascii=False))

    return issues
