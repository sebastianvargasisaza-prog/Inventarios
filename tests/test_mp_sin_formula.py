"""Materia prima con stock que NINGUNA fórmula declara (1-ago).

La forma general de la pregunta del lauryl glucoside. Al mirar su familia aparecieron varios
materiales comprados que ninguna fórmula nombra, y cada uno es una de dos cosas -- las dos caras:

  · plata parada (se compró y no entra a ningún producto), o
  · **el kardex mintiendo**: en planta se usa y ninguna fórmula lo descuenta, así que el stock
    queda inflado y nadie lo vuelve a comprar porque el sistema cree que no se consume.

Lo que separa una de otra es si el material **salió alguna vez** del kardex. El endpoint no
decide: lista con esa evidencia.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD_PARADO = 'ZZSF-PARADO'
COD_USADO = 'ZZSF-USADO'
COD_FANTASMA = 'ZZSF-FANTASMA'
PROD = 'ZZSF PRODUCTO'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    for cod in (COD_PARADO, COD_USADO, COD_FANTASMA):
        _sql("DELETE FROM movimientos WHERE material_id=?", (cod,))
        _sql("DELETE FROM formula_items WHERE material_id=?", (cod,))
        _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        _sql("DELETE FROM mp_formula_bridge WHERE bodega_material_id=? OR formula_material_id=?",
             (cod, cod))
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))


def _mp(cod, nombre):
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES (?,?,?,1,1)", (cod, nombre, nombre.upper()))


def _entrada(cod, g, lote):
    _sql("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
         "estado_lote, fecha) VALUES (?,?, 'Entrada', ?, ?, 'VIGENTE', '2026-08-01')",
         (cod, cod, g, lote))


def _pedir(app):
    r = _login(app).get('/api/programacion/mp-sin-formula')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_una_MP_con_stock_que_ninguna_formula_usa_aparece(app, db_clean):
    _limpiar()
    _mp(COD_PARADO, 'ZZ parado')
    _entrada(COD_PARADO, 12480, 'ZZL-1')
    try:
        j = _pedir(app)
        fila = [x for x in j['items'] if x['codigo'] == COD_PARADO]
        assert fila, 'no listó la MP con stock que ninguna fórmula declara'
        assert fila[0]['stock_g'] == 12480.0, fila[0]
        assert fila[0]['salio_alguna_vez'] is False, fila[0]
    finally:
        _limpiar()


def test_la_que_SI_esta_en_una_formula_NO_aparece(app, db_clean):
    """Dientes: si listara todo, la lista sería ruido y dejaría de mirarse."""
    _limpiar()
    _mp(COD_USADO, 'ZZ usado')
    _entrada(COD_USADO, 5000, 'ZZU-1')
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,10)",
         (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,2.0)", (PROD, COD_USADO, 'ZZ usado'))
    try:
        j = _pedir(app)
        assert not [x for x in j['items'] if x['codigo'] == COD_USADO], (
            'reportó como huérfana una MP que SÍ está en una fórmula')
    finally:
        _limpiar()


def test_el_PUENTE_cuenta_como_uso(app, db_clean):
    """M1 · una fórmula puede nombrar el material con un código FANTASMA que puentea a éste.
    Sin mirar el puente, media bodega saldría como huérfana y la lista no serviría."""
    _limpiar()
    _mp(COD_USADO, 'ZZ usado por puente')
    _entrada(COD_USADO, 3000, 'ZZP-1')
    # el código que la fórmula nombra existe pero NO tiene stock: el material real es el otro.
    # (Un fantasma puro no se puede sembrar: el trigger de `formula_items` exige que el
    # material_id esté en el maestro activo · M38. En producción son anteriores al trigger.)
    _mp(COD_FANTASMA, 'ZZ nombre heredado')
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,10)",
         (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,1.0)", (PROD, COD_FANTASMA, 'ZZ fantasma'))
    _sql("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
         "VALUES (?,?,1)", (COD_FANTASMA, COD_USADO))
    try:
        j = _pedir(app)
        assert not [x for x in j['items'] if x['codigo'] == COD_USADO], (
            'ignoró el puente y la reportó como huérfana')
    finally:
        _limpiar()


def test_separa_la_que_YA_SALIO_del_kardex(app, db_clean):
    """La señal que importa: si salió sin que ninguna fórmula la declare, se está consumiendo
    por fuera y su stock está inflado -- eso es un problema, no plata parada."""
    _limpiar()
    _mp(COD_PARADO, 'ZZ consumida a escondidas')
    _entrada(COD_PARADO, 10000, 'ZZS-1')
    _sql("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
         "estado_lote, fecha) VALUES (?,?, 'Salida', 1500, 'ZZS-1', 'VIGENTE', '2026-08-01')",
         (COD_PARADO, COD_PARADO))
    try:
        j = _pedir(app)
        fila = [x for x in j['items'] if x['codigo'] == COD_PARADO]
        assert fila and fila[0]['salio_alguna_vez'] is True, fila
        assert COD_PARADO in [x['codigo'] for x in j['ojo_se_consumen_sin_formula']], j
    finally:
        _limpiar()


def test_marca_el_POSIBLE_STOCK_DUPLICADO(app, db_clean):
    """Lo destapó el resultado real (1-ago): MP00181 y MPCENTESO01 con 893 g CADA UNO,
    MP00161 y MPCARNSO01 con 141 g cada uno. `_get_mp_stock` NO pliega el puente (indexa por
    material_id y por variantes de NOMBRE), así que esos son DOS conjuntos de movimientos
    distintos -- no un alias del mismo. Si el puente dice que son el mismo material, el
    inventario está contando lo mismo dos veces y el valor en libros sale inflado.

    No se afirma que esté duplicado: se marca para que alguien lo cuente.
    """
    _limpiar()
    _mp(COD_PARADO, 'ZZ fantasma con stock')
    _entrada(COD_PARADO, 893, 'ZZD-1')
    _mp(COD_USADO, 'ZZ canonico con stock')
    _entrada(COD_USADO, 893, 'ZZD-2')
    _sql("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
         "VALUES (?,?,1)", (COD_PARADO, COD_USADO))
    try:
        j = _pedir(app)
        fila = [x for x in j['items'] if x['codigo'] == COD_PARADO]
        assert fila, j['items'][:3]
        assert fila[0]['puenteado_a'] == COD_USADO, fila[0]
        assert fila[0]['destino_tambien_tiene_stock'] is True, fila[0]
        assert fila[0]['stock_del_destino_g'] == 893.0, fila[0]
        assert COD_PARADO in [x['codigo'] for x in j['ojo_posible_stock_duplicado']], j
    finally:
        _limpiar()


def test_NO_marca_duplicado_si_el_destino_esta_en_cero(app, db_clean):
    """Dientes: un puente cuyo destino no tiene stock es una migración BIEN hecha (el saldo se
    movió), no un duplicado. Si marcara esos, la lista sería ruido."""
    _limpiar()
    _mp(COD_PARADO, 'ZZ fantasma con stock')
    _entrada(COD_PARADO, 500, 'ZZD-3')
    _mp(COD_USADO, 'ZZ canonico vacio')
    _sql("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
         "VALUES (?,?,1)", (COD_PARADO, COD_USADO))
    try:
        j = _pedir(app)
        fila = [x for x in j['items'] if x['codigo'] == COD_PARADO]
        assert fila and fila[0]['destino_tambien_tiene_stock'] is False, fila
        assert COD_PARADO not in [x['codigo'] for x in j['ojo_posible_stock_duplicado']], j
    finally:
        _limpiar()
