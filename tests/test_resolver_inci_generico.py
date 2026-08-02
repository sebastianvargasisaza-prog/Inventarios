"""Un INCI que comparten MUCHOS materiales no identifica a ninguno (2-ago).

Caso real: la Crema Renova Body lleva Fresa Cremosa (`MP00019`, 0,1%) y Fragancia Pistacho
(`MP00062`, 0,2%). Los dos tienen INCI `PARFUM`, que en el maestro comparten DIEZ fragancias
distintas -- y sólo el pistacho se ha comprado alguna vez.

El resolver caía al tier INCI (porque la fresa tiene stock 0) y elegía el pistacho, así que:
  · la Fresa Cremosa NO aparecía en abastecimiento -- nadie la compraría
  · el Pistacho aparecía con 88,5 g = sus 59 g + los 29,5 g de la fresa

El guard contra INCI ambiguo YA existía, pero medía la ambigüedad sobre los códigos CON STOCK:
con uno solo con stock no disparaba. La ambigüedad es del INCI, no del stock.

Golpea sobre todo a las materias primas que NUNCA se compraron, que son justo las que tienen
que salir en la tabla para comprarlas.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

INCI_GEN = 'QA PARFUM GENERICO'
INCI_UNICO = 'QA PANTENOL UNICO'
SIN_STOCK, CON_STOCK = 'MPQAINCI1', 'MPQAINCI2'
OTROS = ['MPQAINCI3', 'MPQAINCI4', 'MPQAINCI5']
DUP_SIN, DUP_CON = 'MPQAINCI6', 'MPQAINCI7'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sembrar():
    """M103: limpiar ANTES · la BD de tests es compartida."""
    todos = [SIN_STOCK, CON_STOCK, DUP_SIN, DUP_CON] + OTROS
    db = _db()
    try:
        db.execute("DELETE FROM movimientos WHERE material_id IN (%s)"
                   % ','.join('?' * len(todos)), todos)
        db.execute("DELETE FROM maestro_mps WHERE codigo_mp IN (%s)"
                   % ','.join('?' * len(todos)), todos)
        # INCI GENÉRICO: 5 materiales distintos lo comparten, uno solo con stock
        for cod in [SIN_STOCK, CON_STOCK] + OTROS:
            db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                       "VALUES (?,?,?,1)", (cod, 'QA fragancia ' + cod[-1], INCI_GEN))
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
                   "estado_lote) VALUES (?,?,?,'Entrada','2026-07-01 08:00:00','L-QA','VIGENTE')",
                   (CON_STOCK, 'QA fragancia 2', 5000.0))
        # INCI que SÍ identifica: sólo DOS códigos (el duplicado legítimo, tipo pantenol)
        for cod in (DUP_SIN, DUP_CON):
            db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                       "VALUES (?,?,?,1)", (cod, 'QA pantenol', INCI_UNICO))
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
                   "estado_lote) VALUES (?,?,?,'Entrada','2026-07-01 08:00:00','L-QA2','VIGENTE')",
                   (DUP_CON, 'QA pantenol', 4000.0))
        db.commit()
    finally:
        db.close()


def _resolver(app, cod, nombre):
    """Corre el impl con una conexión directa, dentro del contexto (algunos helpers de caché
    tocan flask.g). Devuelve el código de bodega al que resuelve."""
    try:
        from api.blueprints.programacion import _resolver_material_bodega_impl as f
    except Exception:
        from blueprints.programacion import _resolver_material_bodega_impl as f
    db = _db()
    try:
        with app.app_context():
            return f(db.cursor(), cod, nombre)
    finally:
        db.close()


def test_un_INCI_que_comparten_muchos_NO_redirige(app):
    """La fresa no puede resolverse al pistacho porque los dos digan PARFUM."""
    _sembrar()
    assert _resolver(app, SIN_STOCK, 'QA fragancia 1') == SIN_STOCK, (
        'se resolvió a otro material sólo por compartir un INCI genérico')


def test_el_duplicado_legitimo_SIGUE_resolviendo(app):
    """Dos códigos del MISMO material (pantenol líquido/polvo) tienen que seguir cruzándose,
    o producción diría "sin stock" teniendo el material bajo el otro código."""
    _sembrar()
    assert _resolver(app, DUP_SIN, 'QA pantenol') == DUP_CON


def test_el_que_tiene_stock_se_resuelve_a_si_mismo(app):
    _sembrar()
    assert _resolver(app, CON_STOCK, 'QA fragancia 2') == CON_STOCK
