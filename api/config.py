# config.py — constantes y credenciales del sistema
# Fase B refactor: extraído de index.py
import os

COMPRAS_USERS = {
    'sebastian': os.environ.get('PASS_SEBASTIAN', 'hha2026'),
    'alejandro': os.environ.get('PASS_ALEJANDRO', 'hha2026'),
    'catalina':  os.environ.get('PASS_CATALINA',  'hha2026'),
    'luz':       os.environ.get('PASS_LUZ',       'hha2026'),
    'mayra':     os.environ.get('PASS_MAYRA',     'hha2026'),
}
ADMIN_USERS = {'sebastian', 'alejandro'}
CONTADORA_USERS = {'mayra'}   # puede todo EXCEPTO Aprobar/Pagar OC

DB_PATH = os.environ.get('DB_PATH', '/var/data/inventario.db')
