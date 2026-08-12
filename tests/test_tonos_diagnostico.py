# -*- coding: utf-8 -*-
"""Por qué un producto multitono no se expande · y QUÉ componente lleva el tono.

Sebastián (12-ago): *"para los lip existe el envase con el nombre del tono, y el blush todos son
el mismo envase, solo cambia la etiqueta"*.

Eso es lo que ninguna herramienta miraba: **el tono no vive siempre en el mismo componente**. Una
expansión que asuma uno de los dos deja al otro sin resolver, y desde afuera se ve idéntico a que
la herramienta no hiciera nada.

Este diagnóstico no cambia nada, mide. Y sobre todo, cuando no se puede expandir DICE POR QUÉ: un
"no se pudo" sin motivo obliga a adivinar entre tres causas con tres arreglos distintos (M127).
"""
import pytest

TEST_PASSWORD = "TestPass123"


@pytest.fixture
def planta_client(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "smurillo", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre LIKE 'TONO TEST%'")
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'TONO TEST%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'TT-%'")
        conn.commit()


def _sku(app, producto, sku, tono, vol=10):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO sku_producto_map (sku, producto_nombre, tono_label, volumen_ml, es_regalo) "
            "VALUES (?,?,?,?,0)", (sku, producto, tono, vol))
        conn.commit()


def _mee(app, codigo, desc, categoria):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
            "VALUES (?,?,?,0)", (codigo, desc, categoria))
        conn.commit()


def test_detecta_que_el_tono_lo_lleva_el_ENVASE(app, planta_client):
    """El caso REAL del lip serum: hay un frasco por color, y el frasco NO se llama como el
    producto.

    En produccion el producto es "LIP SERUM VOLUMINIZADOR PEPTIDOS" y sus frascos "LIPS GLOSS
    BLANCO / CAFE CLARO": comercialmente lo mismo, sin una palabra en comun. Exigir parecido de
    nombres lo dejaria sin resolver. El vinculo lo da un HECHO: uno de esos frascos ya esta
    asignado a una presentacion del producto, y de ahi salen las palabras de la familia.
    """
    _limpiar(app)
    for t in ('MERLOT', 'MOCCA', 'PEACH'):
        _sku(app, 'TONO TEST VOLUMINIZADOR', 'LIPTEST' + t, t)
        _mee(app, 'TT-ENV-' + t, 'LIPSTEST GLOSSTEST ' + t + ' SIN SERIGRAFIA 10ml', 'Frasco')
    # el hecho que ancla la familia: una presentacion ya usa uno de esos frascos
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
            "volumen_ml, envase_codigo, activo, es_default) "
            "VALUES ('TONO TEST VOLUMINIZADOR','V10','10 ml',10,'TT-ENV-MERLOT',1,1)")
        conn.commit()
    d = planta_client.get('/api/mee/tonos-diagnostico?producto=TONO TEST VOLUMINIZADOR').get_json()
    p = [x for x in d['productos'] if 'TONO TEST VOLUMINIZADOR' in x['producto']][0]
    assert p['tonos_n'] == 3
    assert p['lleva_el_tono'] == 'envase'
    assert p['puede_expandirse'] is True
    assert p['coincidencias']['envase'] == 3, (
        'no reconocio los hermanos del frasco ya asignado: %s' % p['detalle'])


def test_detecta_que_el_tono_lo_lleva_la_ETIQUETA(app, planta_client):
    """El caso del blush: un solo frasco de aluminio y una etiqueta por tono.

    DIENTES · sin este test, un detector que dijera 'envase' SIEMPRE pasaría el anterior, y el
    blush seguiría sin resolverse exactamente igual que hoy.
    """
    _limpiar(app)
    _mee(app, 'TT-ENV-UNICO', 'FRASCO ALUMINIO BLUSH BALM 6ml', 'Frasco')
    for t in ('CORAL', 'ROSA', 'TERRACOTA'):
        _sku(app, 'TONO TEST BLUSH', 'BLUSHTEST' + t, t, vol=6)
        _mee(app, 'TT-ETQ-' + t, 'ETIQUETA BLUSH BALM ' + t, 'Etiqueta')
    d = planta_client.get('/api/mee/tonos-diagnostico?producto=TONO TEST BLUSH').get_json()
    p = [x for x in d['productos'] if 'TONO TEST BLUSH' in x['producto']][0]
    assert p['tonos_n'] == 3
    assert p['lleva_el_tono'] == 'etiqueta', 'el blush lleva el tono en la etiqueta, no en el frasco'
    assert p['coincidencias']['etiqueta'] == 3
    assert p['coincidencias']['envase'] == 0


def test_sin_tono_en_shopify_lo_DICE(app, planta_client):
    """El caso que hoy se ve como 'no cambia nada': las variantes existen y no traen el tono."""
    _limpiar(app)
    for i in range(3):
        _sku(app, 'TONO TEST MUDO', 'MUDO%d' % i, '')
    d = planta_client.get('/api/mee/tonos-diagnostico?producto=TONO TEST MUDO').get_json()
    p = [x for x in d['productos'] if 'TONO TEST MUDO' in x['producto']][0]
    assert p['tonos_n'] == 0
    assert p['puede_expandirse'] is False
    assert 'no traen el nombre del tono' in p['motivo']
    assert len(p['sin_tono']) == 3


def test_con_tonos_pero_sin_empaque_que_los_nombre_lo_DICE(app, planta_client):
    """Tres causas distintas con tres arreglos distintos: hay que poder saber cuál es."""
    _limpiar(app)
    for t in ('AZUL', 'VERDE'):
        _sku(app, 'TONO TEST HUERFANO', 'HUERF' + t, t)
    d = planta_client.get('/api/mee/tonos-diagnostico?producto=TONO TEST HUERFANO').get_json()
    p = [x for x in d['productos'] if 'TONO TEST HUERFANO' in x['producto']][0]
    assert p['tonos_n'] == 2
    assert p['lleva_el_tono'] is None
    assert p['puede_expandirse'] is False
    assert 'ninguno aparece en el nombre' in p['motivo']


def test_no_confunde_un_tono_contenido_en_otra_palabra(app, planta_client):
    """Un tono de dos letras dentro de otra palabra no es ese tono."""
    _limpiar(app)
    _sku(app, 'TONO TEST CORTO', 'CORTO1', 'RO')
    _mee(app, 'TT-ENV-ROSA', 'FRASCO ROSADO 10ml', 'Frasco')
    d = planta_client.get('/api/mee/tonos-diagnostico?producto=TONO TEST CORTO').get_json()
    p = [x for x in d['productos'] if 'TONO TEST CORTO' in x['producto']][0]
    assert p['coincidencias']['envase'] == 0, 'un tono de dos letras no puede emparejar'


def test_requiere_sesion(client):
    assert client.get('/api/mee/tonos-diagnostico').status_code in (401, 302)
