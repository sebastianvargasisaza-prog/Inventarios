# config.py — constantes y credenciales del sistema
# Fase B refactor: extraído de index.py
import os

COMPRAS_USERS = {
    'sebastian': os.environ.get('PASS_SEBASTIAN', 'hha2026'),
    'alejandro': os.environ.get('PASS_ALEJANDRO', 'hha2026'),
    'catalina':  os.environ.get('PASS_CATALINA',  'hha2026'),
    'luz':       os.environ.get('PASS_LUZ',       'hha2026'),
    'mayra':     os.environ.get('PASS_MAYRA',     'hha2026'),
    'gloria':    os.environ.get('PASS_GLORIA',    'hha2026'),
    'daniela':   os.environ.get('PASS_DANIELA',   'hha2026'),
    # Operarios de planta — acceso a /planta (dashboard inventarios)
    'planta':    os.environ.get('PASS_PLANTA',    'espagiria2026'),
}
ADMIN_USERS     = {'sebastian', 'alejandro'}
CONTADORA_USERS = {'mayra'}                               # Finanzas + consulta
RRHH_USERS      = {'gloria', 'daniela', 'luz', 'mayra'}  # Acceso a /rrhh
PLANTA_USERS    = {'planta'}                              # Solo acceso a /planta (inventarios)

DB_PATH = os.environ.get('DB_PATH', '/var/data/inventario.db')
