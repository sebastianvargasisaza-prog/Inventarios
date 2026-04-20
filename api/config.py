# config.py — constantes y credenciales del sistema
# Fase B refactor: extraído de index.py
import os

COMPRAS_USERS = {
    # ── Gerencia / Admin ──────────────────────────────────────────────────
    'sebastian':  os.environ.get('PASS_SEBASTIAN',  'hha2026'),       # CEO
    'alejandro':  os.environ.get('PASS_ALEJANDRO',  'hha2026'),       # Admin
    'hernando':   os.environ.get('PASS_HERNANDO',   'espagiria2026'), # Director Técnico
    # ── Compras / Gerencia ────────────────────────────────────────────────
    'catalina':   os.environ.get('PASS_CATALINA',   'hha2026'),       # Asistente de Compras
    'luz':        os.environ.get('PASS_LUZ',        'hha2026'),       # Asistente de Gerencia
    'daniela':    os.environ.get('PASS_DANIELA',    'hha2026'),       # Asistente Gerencia ÁNIMUS
    'valentina':  os.environ.get('PASS_VALENTI