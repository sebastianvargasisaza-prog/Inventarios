"""17-jun · El diagnóstico de cruce debe detectar stock bajo código HERMANO cuando
el INCI es el mismo blend escrito en DISTINTO ORDEN (y con marca comercial distinta).

Caso real Biosure FE: la fórmula usa MP00068 'Biosure FE' (INCI
'PHENOXYETHANOL (AND) ETHYLHEXYLGLYCERIN') con 0 g, pero el físico se cargó como
'SOLBROL PEH' (INCI 'ETHYLHEXYLGLYCERIN PHENOXYETHANOL') bajo otro código. Antes
norm() no ordenaba tokens → no cruzaba, y el guard de nombre comercial lo bloqueaba.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_cruce_detecta_inci_orden_invertido(app, db_clean):
    # código que usa la fórmula · INCI con "(AND)" · SIN stock
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('MPBIOTEST', 'Biosure FE', 'PHENOXYETHANOL (AND) ETHYLHEXYLGLYCERIN', 1)")
    # código hermano · MISMO blend, INCI en orden invertido, marca distinta · CON stock
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('MPSOLBTEST', 'Solbrol PEH', 'ETHYLHEXYLGLYCERIN PHENOXYETHANOL', 1)")
    _exec("INSERT INTO movimientos (material_id, cantidad, tipo, lote, fecha, estado_lote) "
          "VALUES ('MPSOLBTEST', 16100, 'Entrada', 'L-SOLB', date('now','-5 hours'), 'VIGENTE')")
    # fórmula que usa el código sin stock
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('ZZ-BIOTEST', 10, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('ZZ-BIOTEST', 'MPBIOTEST', 'Biosure FE', 1, 100)")

    import sys
    api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    with app.app_context():
        from blueprints.admin import diagnosticar_cruce_global
        rep = diagnosticar_cruce_global()

    # la fórmula ZZ-BIOTEST debe tener su Biosure marcado DUPLICADO_INCI apuntando al hermano
    prod = next((p for p in rep['productos'] if p['producto'] == 'ZZ-BIOTEST'), None)
    assert prod is not None, "la fórmula bloqueada debe aparecer"
    bio = next((b for b in prod['bloqueos'] if b['material_id'] == 'MPBIOTEST'), None)
    assert bio is not None
    assert bio['categoria'] == 'DUPLICADO_INCI', f"debe cruzar el blend invertido · got {bio['categoria']} · {bio['detalle']}"
    assert bio['detalle']['codigo_con_stock'] == 'MPSOLBTEST'
    assert bio['detalle']['stock_g'] >= 16000
