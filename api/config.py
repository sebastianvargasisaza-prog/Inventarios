# config.py -- constantes y credenciales del sistema
import os

COMPRAS_USERS = {
    "sebastian":  os.environ.get("PASS_SEBASTIAN",  "hha2026"),
    "alejandro":  os.environ.get("PASS_ALEJANDRO",  "hha2026"),
    "hernando":   os.environ.get("PASS_HERNANDO",   "espagiria2026"),
    "catalina":   os.environ.get("PASS_CATALINA",   "hha2026"),
    "luz":        os.environ.get("PASS_LUZ",        "hha2026"),
    "daniela":    os.environ.get("PASS_DANIELA",    "hha2026"),
    "valentina":  os.environ.get("PASS_VALENTINA",  "espagiria2026"),
    "jefferson":  os.environ.get("PASS_JEFFERSON",  "espagiria2026"),
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

COMPRAS_ACCESS  = {"luz", "catalina", "mayra", "daniela", "alejandro", "sebastian"}
FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}
CLIENTES_ACCESS = {"mayra", "luz", "catalina", "valentina", "daniela", "alejandro", "sebastian"}
TECNICA_USERS   = {"hernando", "miguel", "alejandro", "sebastian"}

# PIN para desbloquear vista de cantidades en Formulas (cambiar via env var FORMULA_PIN)
FORMULA_PIN = os.environ.get("FORMULA_PIN", "7531")
