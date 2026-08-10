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


def test_el_tono_sale_del_SKU_cuando_lo_lleva_escrito(app, admin_client):
    """LIP SERUM: los SKU son `GLOSSMALVA`, `GLOSSMERLOT`. Comparten el prefijo `GLOSS` y lo que
    sobra ES el tono. El prefijo se calcula de los datos, sin ninguna lista que mantener (M122).

    Existe para no dejar a nadie esperando al cron de las 21:30 teniendo el dato a la vista; en
    cuanto corre el sync de Shopify, `tono_label` lo pisa con lo que Shopify diga.
    """
    from database import get_db
    PL = 'EXPTONO LIP'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PL,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PL,))
        c.execute("DELETE FROM maestro_mee WHERE codigo='EXL-FR'")
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('EXL-FR','LIP GLOSS BLANCO SIN SERG','Frasco',0)")
        for sk in ('GLOSSMALVA', 'GLOSSMERLOT', 'GLOSSCAFECLARO'):
            c.execute("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) "
                      "VALUES (?,?,10,1)", (sk, PL))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) VALUES (?,'V10','10 ml',10,'EXL-FR',1)",
                  (PL,))
        c.commit()
    j = admin_client.get('/api/mee/expandir-tonos').get_json()
    p = [x for x in j['propuestas'] if x['producto'] == PL]
    assert p, 'no propuso abrir las filas del lip serum: %s' % j.get('sin_tono')
    tonos = {t['tono'].upper() for t in p[0]['tonos']}
    assert {'MALVA', 'MERLOT'} <= tonos, 'no sacó el tono del SKU: %s' % tonos
    assert all(t['fuente_tono'] for t in p[0]['tonos']), 'no dice de dónde salió el tono'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PL,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PL,))
        c.execute("DELETE FROM maestro_mee WHERE codigo='EXL-FR'")
        c.commit()


def test_NO_confunde_TAMANOS_con_tonos(app, admin_client):
    """`SAH15` y `SAH30` comparten prefijo y lo que sobra son números: eso no nombra un tono. Si
    los tomara, abriría "tonos" que son en realidad dos tamaños del mismo producto."""
    from database import get_db
    PS = 'EXPTONO SUERO TAM'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PS,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PS,))
        c.execute("DELETE FROM maestro_mee WHERE codigo='EXS-FR'")
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('EXS-FR','FRASCO SUERO','Frasco',0)")
        for sk, vol in (('EXSAH15', 15), ('EXSAH30', 30)):
            c.execute("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) "
                      "VALUES (?,?,?,1)", (sk, PS, vol))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) VALUES (?,'V15','15 ml',15,'EXS-FR',1)",
                  (PS,))
        c.commit()
    j = admin_client.get('/api/mee/expandir-tonos').get_json()
    assert not [x for x in j['propuestas'] if x['producto'] == PS], \
        'tomó dos TAMAÑOS como si fueran tonos'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PS,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PS,))
        c.execute("DELETE FROM maestro_mee WHERE codigo='EXS-FR'")
        c.commit()
