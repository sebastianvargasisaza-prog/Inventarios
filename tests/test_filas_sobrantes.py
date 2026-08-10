# -*- coding: utf-8 -*-
"""Las filas de presentación que sobraron de corridas viejas.

Sebastián (9-ago), mirando el LIP SERUM: cinco filas de 10 ml, dos con nombre de tono
(`GLOSSMALVA`, `GLOSSMERLOT`), dos llamadas `TONO-MEE-ENV-016/017` y una apuntando a `MEE-IMP-001`,
que no existe en el maestro. Las `TONO-*` las creó un emparejador viejo que **creaba**
presentaciones en vez de completar las que ya estaban: por eso el producto quedó con dos juegos.

Dos filas iguales reparten el bulto entre las dos y cada una pide su empaque, así que se compra el
doble de lo que se usa. Y una que apunta a un código inexistente no se puede comprar ni descontar:
la necesidad queda invisible (M100).

La limpieza da de BAJA (activo=0), reversible y auditada; nunca borra.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

P = 'SOBRA LIP SERUM'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'SOB-%'")
        c.commit()


def _sembrar(app):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('SOB-FR','LIP GLOSS BLANCO','Frasco',0)")
        # la buena: tiene SKU propio
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,sku_shopify,activo) "
                  "VALUES (?,'GLOSSMALVA','10 ml',10,'SOB-FR','SOBMALVA',1)", (P,))
        # la que dejo el emparejador viejo: mismo frasco, mismo volumen, sin SKU
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) "
                  "VALUES (?,'TONO-SOB-FR','10 ml',10,'SOB-FR',1)", (P,))
        # la que apunta a un codigo que no existe
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) "
                  "VALUES (?,'V10','10 ml',10,'SOB-NOEXISTE',1)", (P,))
        c.commit()


def _sobrantes(admin_client):
    r = admin_client.get('/api/mee/filas-sobrantes')
    assert r.status_code == 200, r.data[:200]
    return [x for x in r.get_json()['sobrantes'] if x['producto'] == P]


def test_encuentra_la_duplicada_y_la_del_codigo_fantasma(app, admin_client):
    _sembrar(app)
    cods = {x['cod']: x['motivo'] for x in _sobrantes(admin_client)}
    assert cods.get('TONO-SOB-FR') == 'duplicada', \
        'no vio la que dejo el emparejador viejo: %s' % cods
    assert cods.get('V10') == 'envase_fantasma', \
        'no vio la que apunta a un codigo inexistente: %s' % cods
    _limpiar(app)


def test_NUNCA_toca_la_que_tiene_SKU_propio(app, admin_client):
    """Esa es la buena: su venta es la que separa el tono (M19)."""
    from database import get_db
    _sembrar(app)
    assert not [x for x in _sobrantes(admin_client) if x['cod'] == 'GLOSSMALVA'], \
        'marco como sobrante la buena'
    with app.app_context():
        pid = get_db().execute(
            "SELECT id FROM producto_presentaciones "
            " WHERE producto_nombre=? AND presentacion_codigo='GLOSSMALVA'", (P,)).fetchone()[0]
    r = admin_client.post('/api/mee/filas-sobrantes-baja', json={'ids': [pid]},
                          headers={'Origin': 'http://localhost'})
    assert not r.get_json()['bajas'], 'dio de baja una fila con SKU propio'
    assert r.get_json()['saltadas'], 'no dice por que la salto'
    _limpiar(app)


def test_dar_de_baja_es_REVERSIBLE_y_deja_quien(app, admin_client):
    from database import get_db
    _sembrar(app)
    so = _sobrantes(admin_client)
    r = admin_client.post('/api/mee/filas-sobrantes-baja',
                          json={'ids': [x['id'] for x in so]},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['bajas'], r.data[:200]
    with app.app_context():
        c = get_db()
        apagadas = c.execute("SELECT COUNT(*) FROM producto_presentaciones "
                             " WHERE producto_nombre=? AND activo=0", (P,)).fetchone()[0]
        assert apagadas == 2, 'no las apago (o las borro): %d' % apagadas
        vivas = c.execute("SELECT COUNT(*) FROM producto_presentaciones "
                          " WHERE producto_nombre=? AND activo=1", (P,)).fetchone()[0]
        assert vivas == 1, 'apago la buena, o dejo viva una que no debia: %d' % vivas
        aud = c.execute("SELECT COUNT(*) FROM audit_log "
                        " WHERE accion='PRES_SOBRANTE_DE_BAJA'").fetchone()[0]
        assert aud >= 2, 'no dejo rastro de quien'
    _limpiar(app)
