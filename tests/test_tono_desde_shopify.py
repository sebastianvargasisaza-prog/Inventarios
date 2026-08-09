# -*- coding: utf-8 -*-
"""El TONO de cada SKU sale de Shopify, no de una lista escrita a mano.

Sebastián (9-ago): *"revisemos en Shopify, Shopify tiene ya definido los tonos y los nombres,
entonces ya los envases tienen esos nombres y las etiquetas"*.

Tenía razón: los tonos están en Shopify. Lo que faltaba es que EOS los guardara. El sync de
órdenes se queda sólo con `sku` y `cantidad` y tira el nombre; y el job que trae el CATÁLOGO
(`products.json?fields=id,title,variants`, que ya corre para el stock) capturaba el título del
PRODUCTO pero no el de la VARIANTE, que es justo el tono.

Por eso `sku_producto_map.tono_label` estaba vacío en las 55 filas, y los ocho tonos del blush
vivían en una lista escrita a mano en el código (`BLUSH_TONOS`), que se pudre el día que alguien
agrega un color (M122).
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _fuente():
    import io as _io
    return _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'auto_plan_jobs.py'),
                    encoding='utf-8').read()


def test_el_job_CAPTURA_el_titulo_de_la_variante(app):
    """Sin esto el tono nunca entra al sistema, por más que Shopify lo tenga."""
    src = _fuente()
    codigo = '\n'.join(l.split('#')[0] for l in src.splitlines())   # sin comentarios (M154)
    assert "variant.get('title'" in codigo, \
        'el job no captura el título de la VARIANTE: el tono se pierde en el camino'


def test_el_tono_se_GUARDA_en_sku_producto_map(app):
    src = _fuente()
    codigo = '\n'.join(l.split('#')[0] for l in src.splitlines())
    assert re.search(r'UPDATE sku_producto_map SET tono_label', codigo), \
        'captura el tono y no lo guarda: el dato se pierde igual'
    assert 'default title' in codigo.lower(), \
        'Shopify usa "Default Title" para productos sin variantes: eso NO es un tono'


def test_solo_escribe_donde_el_SKU_ya_esta_mapeado(app):
    """No inventa filas: un SKU que nadie mapeó a un producto no se cuela por la puerta de atrás."""
    src = _fuente()
    i = src.find('UPDATE sku_producto_map SET tono_label')
    assert i > 0
    ventana = src[i:i + 300]
    assert 'WHERE UPPER(TRIM(sku))=' in ventana, 'escribe sin acotar por SKU'
    assert 'INSERT INTO sku_producto_map' not in ventana, 'crea filas que nadie mapeó'


def test_el_tono_guardado_APARECE_en_la_tabla_de_normalizacion(app, admin_client):
    """La cadena completa: lo que Shopify dice tiene que llegar a la pantalla donde se carga."""
    from database import get_db
    P = 'TONOSH PRODUCTO'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM sku_producto_map WHERE sku='TONOSH1'")
        c.execute("DELETE FROM maestro_mee WHERE codigo='TONOSH-FR'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('TONOSH-FR','FRASCO TONOSH','Frasco',0)")
        c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, tono_label, activo) "
                  "VALUES ('TONOSH1', ?, 'Hot Pink', 1)", (P,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, sku_shopify, activo) "
                  "VALUES (?,'V6','6 ml',6,'TONOSH-FR','TONOSH1',1)", (P,))
        c.commit()
    j = admin_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in j['filas'] if f['producto'] == P]
    assert fila and fila[0].get('tono') == 'Hot Pink', \
        'el tono de Shopify no llega a la pantalla: %s' % (fila[0] if fila else None)
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM sku_producto_map WHERE sku='TONOSH1'")
        c.execute("DELETE FROM maestro_mee WHERE codigo='TONOSH-FR'")
        c.commit()


def test_hay_una_puerta_para_TRAER_los_tonos_sin_esperar_al_cron(app, admin_client):
    """El catálogo se sincroniza 5:30 / 13:30 / 21:30. Sin esta puerta, para abrir las filas por
    tono habría que esperar horas: una capacidad que llega tarde, para el que está trabajando
    ahora, no existe (M121).

    Corre en SEGUNDO PLANO: sostener una llamada de red con paginado dentro del request retiene
    uno de los tres workers hasta 40 segundos, que es como se satura la app (M43/M89).
    """
    r = admin_client.post('/api/mee/traer-tonos-shopify', headers={'Origin': 'http://localhost'})
    assert r.status_code in (200, 202), r.data[:200]
    assert r.get_json().get('ok') is True
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'programacion.py'),
                   encoding='utf-8').read()
    i = src.find('def mee_traer_tonos_shopify')
    assert i > 0
    cuerpo = src[i:i + 2200]
    assert 'Thread(' in cuerpo, 'lo corre dentro del request: retiene un worker'
    assert 'job_sync_stock_shopify_diario' in cuerpo, \
        'no delega en el job del cron: dos caminos para el mismo hecho divergen (M1/M3)'
