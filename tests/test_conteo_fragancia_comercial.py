"""17-jun · El conteo físico mapea fragancias (INCI genérico PARFUM) por NOMBRE
COMERCIAL, no por INCI. Antes el match por INCI agarraba el primer código PARFUM
arbitrario → el stock de pistacho caía en otra fragancia (o en 0)."""
import os
import sqlite3


def _seed(cod, com, inci):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
                     (cod, com, inci))
        conn.commit()
    finally:
        conn.close()


def test_fragancia_resuelve_por_comercial(app, db_clean):
    import sys
    api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from blueprints.inventario import _resolver_codigo_mp_conteo
    # dos fragancias DISTINTAS con el MISMO INCI genérico PARFUM · nombres únicos
    # (que no colisionen con el catálogo del seed)
    _seed('MPFRAA01', 'Fragancia mocaZZ test', 'PARFUM')
    _seed('MPFRAB01', 'Fragancia pistaZZ test', 'PARFUM')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # sin código, INCI=PARFUM (genérico), comercial=pistaZZ → debe ir a MPFRAB01
        cod, how = _resolver_codigo_mp_conteo(conn, '', 'PARFUM', 'Fragancia pistaZZ test')
        assert cod == 'MPFRAB01', f"pistacho debe mapear por comercial · got {cod} ({how})"
        assert how == 'por_comercial'
        # y el mocaccino al suyo
        cod2, _ = _resolver_codigo_mp_conteo(conn, '', 'PARFUM', 'Fragancia mocaZZ test')
        assert cod2 == 'MPFRAA01', f"mocaccino debe ir a su código · got {cod2}"
    finally:
        conn.close()


def test_blend_inci_orden_invertido_cruza(app, db_clean):
    """Un blend con el INCI en distinto orden (y '(AND)') debe cruzar al código de
    bodega (caso Solbrol/Biosure → MP00068). Antes daba 'sin match' tras desactivar
    el duplicado."""
    import sys
    api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from blueprints.inventario import _resolver_codigo_mp_conteo
    # INCI único (que no colisione con MP reales del seed) · blend de 2 componentes
    _seed('MPBLEND01', 'Blend ZZ test', 'ZZALPHAGLYCOL (AND) ZZBETAPHENOL')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # el conteo trae el INCI en orden invertido, sin '(AND)'
        cod, how = _resolver_codigo_mp_conteo(conn, '', 'ZZBETAPHENOL ZZALPHAGLYCOL', 'otro nombre')
        assert cod == 'MPBLEND01' and how == 'por_inci', f"blend debe cruzar por INCI ordenado · got {cod} ({how})"
    finally:
        conn.close()


def test_inci_normal_sigue_por_inci(app, db_clean):
    """Un INCI específico (no genérico) sigue resolviendo por INCI."""
    import sys
    api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from blueprints.inventario import _resolver_codigo_mp_conteo
    _seed('MPNIAC99', 'Niacinamida X', 'NIACINAMIDE TESTX')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        cod, how = _resolver_codigo_mp_conteo(conn, '', 'NIACINAMIDE TESTX', 'cualquier nombre')
        assert cod == 'MPNIAC99' and how == 'por_inci'
    finally:
        conn.close()
