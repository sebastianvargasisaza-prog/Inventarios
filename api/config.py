# config.py -- constantes y credenciales del sistema
import os

# Contraseñas por usuario.
# Producción DEBE setear cada PASS_<USER> como hash PBKDF2 (ver
# scripts/gen_password_hashes.py). Si la env var falta, queda el
# fallback plaintext temporal — validate_config() lo detecta al startup
# y emite un warning estructurado en logs.
COMPRAS_USERS = {
    "sebastian":  os.environ.get("PASS_SEBASTIAN",  "hha2026"),
    "alejandro":  os.environ.get("PASS_ALEJANDRO",  "hha2026"),
    "hernando":   os.environ.get("PASS_HERNANDO",   "espagiria2026"),
    "catalina":   os.environ.get("PASS_CATALINA",   "hha2026"),
    "luz":        os.environ.get("PASS_LUZ",        "hha2026"),
    "daniela":    os.environ.get("PASS_DANIELA",    "hha2026"),
    "valentina":  os.environ.get("PASS_VALENTINA",  "espagiria2026"),
    "jefferson":  os.environ.get("PASS_JEFFERSON",  "espagiria2026"),
    "felipe":     os.environ.get("PASS_FELIPE",     "animus2026"),
    "mayra":      os.environ.get("PASS_MAYRA",      "hha2026"),
    "gloria":     os.environ.get("PASS_GLORIA",     "hha2026"),
    "laura":      os.environ.get("PASS_LAURA",      "espagiria2026"),
    "miguel":     os.environ.get("PASS_MIGUEL",     "espagiria2026"),
    "yuliel":     os.environ.get("PASS_YULIEL",     "espagiria2026"),
    "luis":       os.environ.get("PASS_LUIS",       "espagiria2026"),
    "smurillo":   os.environ.get("PASS_SMURILLO",   "espagiria2026"),
    "sergio":     os.environ.get("PASS_SERGIO",     "espagiria2026"),
    "mayerlin":   os.environ.get("PASS_MAYERLIN",   "espagiria2026"),
    "camilo":     os.environ.get("PASS_CAMILO",     "espagiria2026"),
}
ADMIN_USERS     = {"sebastian", "alejandro"}
CONTADORA_USERS = {"mayra"}
RRHH_USERS      = {"gloria", "daniela", "luz", "mayra", "alejandro", "sebastian"}
CALIDAD_USERS   = {"laura", "miguel", "yuliel", "alejandro", "sebastian"}
PLANTA_USERS    = {"luis", "smurillo", "sergio", "mayerlin", "camilo"}

DB_PATH = os.environ.get("DB_PATH", "/var/data/inventario.db")


# Contraseñas plaintext conocidas que NUNCA deben usarse en producción.
# validate_config() las detecta y emite un warning por cada usuario afectado.
_INSECURE_PLAINTEXT_DEFAULTS = {"hha2026", "espagiria2026", "animus2026"}

COMPRAS_ACCESS  = {"luz", "catalina", "mayra", "daniela", "alejandro", "sebastian"}
FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}
CLIENTES_ACCESS = {"mayra", "luz", "catalina", "valentina", "daniela", "alejandro", "sebastian"}
TECNICA_USERS   = {"hernando", "miguel", "alejandro", "sebastian"}
MARKETING_USERS = {"jefferson", "sebastian", "alejandro", "felipe"}

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

    # Passwords plaintext
    plaintext_users = []
    for user, pwd in COMPRAS_USERS.items():
        if pwd in _INSECURE_PLAINTEXT_DEFAULTS:
            plaintext_users.append(user)
        elif not pwd.startswith("pbkdf2:") and not pwd.startswith("scrypt:"):
            # Password custom pero plaintext (no hash)
            plaintext_users.append(user)
    if plaintext_users:
        issues.append({
            "severity": "CRITICAL" if any(
                COMPRAS_USERS[u] in _INSECURE_PLAINTEXT_DEFAULTS
                for u in plaintext_users
            ) else "HIGH",
            "code": "PLAINTEXT_PASSWORDS",
            "msg": f"{len(plaintext_users)} usuario(s) con password plaintext "
                   f"(o usando fallback inseguro). "
                   f"Corre 'python scripts/gen_password_hashes.py' y pega los "
                   f"PASS_<USER> resultantes en Render → Environment. "
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
