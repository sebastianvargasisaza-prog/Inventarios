"""El rastro de un material: cada salida con de dónde vino (2-ago).

Las colisiones de código dejaron materiales con salidas que NINGUNA fórmula explica --
`MP00300` es Eversoft YCS-30S en EOS y ceramida en el batch record, y tiene 1.505 g que
salieron sin que ningún producto lo declare.

Un stock que se mueve sin explicación es la huella de que alguien descontó por el código
equivocado. Para saberlo hay que ver CADA movimiento con su origen -- no el saldo, que ya
sabemos que no alcanza (M124: cuando algo se excluye o no cuadra, hay que enumerar por qué).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'ZZKDX-MAT'
PROD = 'ZZKDX PRODUCTO'


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
    _sql("DELETE FROM movimientos WHERE material_id=?", (COD,))
    _sql("DELETE FROM formula_items WHERE material_id=?", (COD,))
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))


def _pedir(app, q=COD):
    r = _login(app).get('/api/programacion/kardex-material?q=' + q)
    assert r.status_code == 200, r.data[:300]
    return r.get_json()['materiales'][0]


def test_una_salida_SIN_formula_que_la_explique_se_declara(app, db_clean):
    """El caso MP00300: entró, salió, y ninguna fórmula lo nombra."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES (?,?,?,1,1)", (COD, 'ZZ material', 'ZZ INCI'))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "estado_lote, operador) VALUES (?,?,16800,'Entrada','2026-06-01','ZZL-1','VIGENTE','zz')",
         (COD, 'ZZ material'))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "estado_lote, operador, observaciones) VALUES "
         "(?,?,1505,'Salida','2026-06-20','ZZL-1','VIGENTE','zz','consumo manual ZZ')",
         (COD, 'ZZ material'))
    try:
        j = _pedir(app)
        assert j['formulas_activas_que_lo_usan'] == [], j
        assert len(j['salidas']) == 1, j['salidas']
        assert 'por fuera de una f' in j['veredicto'], j['veredicto']
        assert j['salidas'][0]['observaciones'].startswith('consumo manual'), j['salidas'][0]
    finally:
        _limpiar()


def test_marca_las_salidas_SIN_produccion_asociada(app, db_clean):
    """Una salida sin `produccion_id` no vino del descuento automático de un lote: alguien la
    hizo a mano. Saberlo cambia a quién hay que preguntarle."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES (?,?,?,1,1)", (COD, 'ZZ material', 'ZZ INCI'))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "estado_lote, operador) VALUES (?,?,500,'Salida','2026-06-20','ZZL-1','VIGENTE','zz')",
         (COD, 'ZZ material'))
    try:
        j = _pedir(app)
        assert len(j['salidas_sin_produccion']) == 1, j
        assert 'SIN producci' in j['veredicto'], j['veredicto']
    finally:
        _limpiar()


def test_si_una_formula_lo_usa_las_salidas_estan_explicadas(app, db_clean):
    """Dientes: si marcara todo como inexplicado, la señal se vuelve ruido."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES (?,?,?,1,1)", (COD, 'ZZ material', 'ZZ INCI'))
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,1)", (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,5)", (PROD, COD, 'ZZ material'))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "estado_lote, operador) VALUES (?,?,500,'Salida','2026-06-20','ZZL-1','VIGENTE','zz')",
         (COD, 'ZZ material'))
    try:
        j = _pedir(app)
        assert PROD in j['formulas_activas_que_lo_usan'], j
        assert 'explicadas' in j['veredicto'], j['veredicto']
    finally:
        _limpiar()
