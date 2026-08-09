# -*- coding: utf-8 -*-
"""Una fila por TONO, para los productos que hoy tienen UNA sola para todos.

Sebastián (9-ago): *"resuelve eso de las filas por tono"*. El BLUSH BALM tiene una sola
presentación para los ocho tonos -- mismo frasco de aluminio, misma caja -- y lo único que cambia
es la ETIQUETA. Con una sola fila hay un solo casillero para ocho etiquetas distintas.

Es distinto del LIP SERUM, que ya tiene una fila por tono porque ahí cambia el FRASCO.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

P = 'EXPTONO BLUSH'


def _sembrar(app, tonos=(('EXB101', 'Hot Pink'), ('EXB201', 'Malva'), ('EXB301', 'Borgona'))):
    from database import get_db
    with app.app_context():
        c = get_db()
        _limpiar(app)
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('EXT-FR','FRASCO ALUMINIO 6ml','Frasco',0)")
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('EXT-CJA','PLEGADIZA BLUSH','Plegadiza',0)")
        for sk, tono in tonos:
            c.execute("INSERT INTO sku_producto_map (sku,producto_nombre,tono_label,volumen_ml,"
                      "activo) VALUES (?,?,?,6,1)", (sk, P, tono))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,caja_codigo,activo) "
                  "VALUES (?,'V6','6 ml',6,'EXT-FR','EXT-CJA',1)", (P,))
        c.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'EXT-%'")
        c.commit()


def _filas(app):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT presentacion_codigo, COALESCE(sku_shopify,''), COALESCE(etiqueta_codigo,''), "
            "       COALESCE(envase_codigo,''), COALESCE(caja_codigo,''), COALESCE(activo,1) "
            "  FROM producto_presentaciones WHERE producto_nombre=? ORDER BY id", (P,)).fetchall()


def test_abre_una_fila_por_tono_copiando_el_empaque_comun(app, admin_client):
    _sembrar(app)
    r = admin_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [P]},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.data[:200]
    assert len(r.get_json()['creadas']) == 3
    fs = _filas(app)
    activas = [f for f in fs if f[5]]
    assert len(activas) == 3, 'quedaron %d filas activas: %s' % (len(activas), fs)
    for f in activas:
        assert f[1], 'una fila de tono sin SKU: no se puede separar su venta'
        assert f[3] == 'EXT-FR' and f[4] == 'EXT-CJA', 'no copió el empaque común'
    _limpiar(app)


def test_la_ETIQUETA_queda_vacia_a_proposito(app, admin_client):
    """Es lo único que cambia entre tonos: rellenarla adivinando le pondría a un color la etiqueta
    de otro (M19/M137)."""
    _sembrar(app)
    admin_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [P]},
                      headers={'Origin': 'http://localhost'})
    for f in _filas(app):
        if f[5]:
            assert not f[2], 'le puso una etiqueta a un tono sin que nadie la eligiera'
    _limpiar(app)


def test_la_fila_GENERICA_queda_de_baja(app, admin_client):
    """Si quedara activa, el grupo tendría una fila SIN SKU y el reparto volvería a pesar por
    volumen: se pediría la misma cantidad de cada etiqueta, que es lo que la expansión viene a
    arreglar. Se da de baja (reversible), no se borra."""
    _sembrar(app)
    r = admin_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [P]},
                          headers={'Origin': 'http://localhost'})
    assert r.get_json().get('bajas'), 'no dio de baja la fila genérica'
    gen = [f for f in _filas(app) if f[0] == 'V6']
    assert gen and gen[0][5] == 0, 'la genérica sigue activa: el reparto vuelve a ser uniforme'
    _limpiar(app)


def test_NO_expande_si_algun_SKU_no_declara_su_tono(app, admin_client):
    """Sin el tono no se puede saber qué fila es cuál, y ocho filas indistinguibles son peores que
    una (M100). El tono lo trae el sync de Shopify."""
    _sembrar(app, tonos=(('EXB101', 'Hot Pink'), ('EXB201', '')))
    j = admin_client.get('/api/mee/expandir-tonos').get_json()
    assert not [p for p in j['propuestas'] if p['producto'] == P], 'expandió sin saber los tonos'
    assert [x for x in j['sin_tono'] if x['producto'] == P], 'no dice por qué no puede'
    _limpiar(app)


def test_correrlo_DOS_veces_no_duplica(app, admin_client):
    _sembrar(app)
    admin_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [P]},
                      headers={'Origin': 'http://localhost'})
    n1 = len(_filas(app))
    admin_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [P]},
                      headers={'Origin': 'http://localhost'})
    assert len(_filas(app)) == n1, 'duplicó filas al correrlo de nuevo'
    _limpiar(app)
