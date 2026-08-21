# -*- coding: utf-8 -*-
"""Contar por CAJAS y poder imprimir la etiqueta de cada una · 21-ago-2026.

Sebastián, con el inventario de envases delante: *"acabo de contar que hay 13 cajas cada una con
164 envases, necesito que quede así y poder imprimirlas en material de envase"*.

Contar 2.132 envases de a uno no lo hace nadie: se cuentan las cajas y lo que trae cada una. Ese
es el dato del muelle, y además es el único que permite imprimir un rótulo por caja -- que ya
existía y no tenía de dónde sacar las cajas cuando el conteo entraba por el ajuste de stock.

Las cajas **mandan** sobre el total: escribir el total por un lado y el desglose por otro deja
que digan cosas distintas del mismo conteo (M5).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_COD = 'MEE-CAJAS-TEST'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _limpiar():
    """Limpieza ANTES de sembrar, con código FIJO (M103)."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        for (i,) in conn.execute("SELECT id FROM movimientos_mee WHERE mee_codigo=?",
                                 (_COD,)).fetchall():
            conn.execute("DELETE FROM mee_cajas_disposicion WHERE mov_id=?", (i,))
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (_COD,))
        conn.execute("DELETE FROM maestro_mee WHERE codigo=?", (_COD,))
        conn.commit()
    finally:
        conn.close()


def _sembrar():
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
         "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
         (_COD, 'FRASCO VIDRIO OPALIZADO ENANO', 'Envase', 'HEBEI YAYOUJIA'))


def test_contar_13_cajas_de_164_deja_el_stock_en_2132(app, db_clean):
    """El caso exacto: las cajas mandan y el total se deriva."""
    _sembrar()
    try:
        c = _login(app)
        r = c.post('/api/mee/%s/ajustar' % _COD,
                   json={'n_cajas': 13, 'unidades_por_caja': 164,
                         'motivo': 'conteo fisico'}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        assert d['stock_nuevo'] == 2132, \
            "13 x 164 son 2.132 y quedó en %r" % (d['stock_nuevo'],)
        assert d.get('mov_id'), "no devuelve el movimiento: sin él no se puede imprimir la tanda"
        assert d.get('n_cajas') == 13 and d.get('unidades_por_caja') == 164
    finally:
        _limpiar()


def test_las_cajas_quedan_GUARDADAS_en_el_movimiento(app, db_clean):
    """Si el desglose no queda, el rótulo por caja no tiene de dónde salir."""
    _sembrar()
    try:
        c = _login(app)
        d = c.post('/api/mee/%s/ajustar' % _COD,
                   json={'n_cajas': 13, 'unidades_por_caja': 164, 'motivo': 'conteo fisico'},
                   headers=csrf_headers()).get_json()
        conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            fila = conn.execute(
                "SELECT n_cajas, unidades_por_caja, cantidad, COALESCE(observaciones,'') "
                "  FROM movimientos_mee WHERE id=?", (d['mov_id'],)).fetchone()
        finally:
            conn.close()
        assert fila, "no quedó el movimiento"
        assert fila[0] == 13 and float(fila[1]) == 164.0, \
            "el desglose por cajas no se guardó: %r" % (fila,)
        assert '13 caja' in fila[3], "el rastro no dice que se contó por cajas: %r" % (fila[3],)
    finally:
        _limpiar()


def test_de_13_cajas_salen_13_ROTULOS_numerados(app, db_clean):
    """Lo que Sebastián necesita imprimir."""
    _sembrar()
    try:
        c = _login(app)
        d = c.post('/api/mee/%s/ajustar' % _COD,
                   json={'n_cajas': 13, 'unidades_por_caja': 164, 'motivo': 'conteo fisico'},
                   headers=csrf_headers()).get_json()
        html = c.get('/rotulos-recepcion-mee?mov=%d' % d['mov_id']).get_data(as_text=True)
        assert html.count('class="sheet"') == 13, \
            "se contaron 13 cajas y salieron %d rótulos" % html.count('class="sheet"')
        assert 'Caja 1 de 13' in html and 'Caja 13 de 13' in html, \
            "los rótulos no vienen numerados por caja"
        # y cada uno dice lo que trae ESA caja, no el total
        assert '164' in html, "el rótulo de la caja no dice cuántos trae"
    finally:
        _limpiar()


def test_sin_cajas_el_ajuste_sigue_funcionando_igual(app, db_clean):
    """Aditivo: quien ajusta escribiendo el total directo no cambia en nada (M117)."""
    _sembrar()
    try:
        c = _login(app)
        r = c.post('/api/mee/%s/ajustar' % _COD,
                   json={'cantidad_nueva': 500, 'motivo': 'conteo fisico'},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        assert d['stock_nuevo'] == 500
        assert not d.get('n_cajas'), "inventó un desglose por cajas que nadie declaró"
    finally:
        _limpiar()


def test_el_modal_tiene_los_campos_y_el_boton_imprime_la_TANDA(app, db_clean):
    """Un endpoint sin puerta no existe (M121). Y el estado de la tanda anterior NO puede
    sobrevivir a abrir otro envase, o el botón imprimiría las cajas del envase de antes."""
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app), '/inventarios')
    assert 'id="mee-adj-ncajas"' in js and 'id="mee-adj-porcaja"' in js, \
        "no hay dónde escribir las cajas"
    assert 'function meeCalcCajas' in js, "el total no se calcula solo"
    assert 'rotulos-recepcion-mee?mov=' in js, \
        "el botón Rótulo no imprime la tanda: seguiría sacando una etiqueta con el total"
    i = js.find('async function meeAjustar(')
    assert i != -1
    apertura = js[i:i + 1400]
    assert 'delete m.dataset.movAjuste' in apertura, \
        "el movimiento de la tanda anterior sobrevive al abrir otro envase"
    assert 'mee-adj-ncajas' in apertura, "los campos de cajas no se limpian al abrir"
