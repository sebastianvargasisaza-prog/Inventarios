# -*- coding: utf-8 -*-
"""«Aprobé la solicitud y se me perdió» · 21-ago-2026.

Catalina aprobó la SOL-2026-0292 de Miguel Valencia y no la encontró. Medido en el código, se le
fue por un hueco de tres capas -- M129 otra vez, ahora en solicitudes:

  1. si el ÁREA es *Producción*, la pantalla aprueba con `crear_oc:false` (correcto: ésas se
     consolidan por proveedor en la bandeja, no una OC por solicitud);
  2. la lista de solicitudes filtra `Pendiente` por defecto -> al aprobarse, desaparece;
  3. la bandeja de agrupadas TAMBIÉN filtra `Pendiente` por defecto -> tampoco está ahí.

Aprobada, sin OC, y fuera de las dos pantallas donde se la busca. Y el mensaje decía sólo
*"✓ Solicitud aprobada"*, sin decir a dónde se fue.

Dos arreglos: el mensaje ahora nombra la pantalla y el filtro, y `/api/compras/donde-esta/<n>`
contesta la pregunta para cualquier solicitud u orden.
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_SOL = 'SOL-QA-0292'
_OC = 'OC-QA-0292'


def _login(app, user="catalina"):
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
    _sql("DELETE FROM solicitudes_compra WHERE numero=?", (_SOL,))
    _sql("DELETE FROM ordenes_compra WHERE numero_oc=?", (_OC,))


def _sembrar_sol(estado='Aprobada', area='Produccion', numero_oc=''):
    _limpiar()
    _sql("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, area, categoria, "
         "numero_oc, aprobado_por, fecha_aprobacion) VALUES (?,?,?,?,?,?,?,?,?)",
         (_SOL, '2026-08-20', estado, 'Miguel Valencia', area, 'Materia Prima',
          numero_oc, 'catalina', '2026-08-21'))


def test_una_solicitud_aprobada_SIN_orden_dice_donde_quedo(app, db_clean):
    """El caso exacto de Catalina: aprobada, de Producción, sin OC."""
    _sembrar_sol()
    try:
        r = _login(app).get('/api/compras/donde-esta/%s' % _SOL)
        assert r.status_code == 200, r.data[:200]
        d = r.get_json()
        assert d['encontrado'], "no encontró una solicitud que existe"
        assert d['solicitud']['estado'] == 'Aprobada'
        assert d['solicitud']['solicitante'] == 'Miguel Valencia'
        assert d.get('donde_esta'), "no dice dónde quedó"
        assert 'agrupadas' in d['donde_esta'].lower(), \
            "no manda a la bandeja donde de verdad está: %r" % d['donde_esta']
        assert d.get('filtro', {}).get('estado') == 'Aprobada', \
            "no dice con qué filtro se ve, que es lo que la hacía invisible"
        # y el rastro cuenta quién la aprobó
        assert any('catalina' in (p.get('que') or '').lower() for p in d['pasos']), \
            "el rastro no dice quién la aprobó"
    finally:
        _limpiar()


def test_si_genero_orden_sigue_el_rastro_hasta_la_orden(app, db_clean):
    _sembrar_sol(numero_oc=_OC)
    _sql("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total, fecha, "
         "categoria) VALUES (?,?,?,?,?,?)",
         (_OC, 'PRESQUIM', 'Autorizada', 1500000, '2026-08-21', 'MP'))
    try:
        d = _login(app).get('/api/compras/donde-esta/%s' % _SOL).get_json()
        assert d['encontrado']
        assert d.get('orden', {}).get('numero_oc') == _OC, \
            "no siguió el rastro hasta la orden que generó"
        assert d['orden']['estado'] == 'Autorizada'
        assert d.get('donde_esta'), "no dice dónde está la orden"
        assert d.get('siguiente_paso'), "no dice qué sigue"
        # el rastro tiene los dos tramos: la solicitud y la orden
        assert len(d['pasos']) >= 2, "el rastro se quedó en la solicitud: %r" % (d['pasos'],)
    finally:
        _limpiar()


def test_se_puede_preguntar_por_el_numero_de_la_ORDEN(app, db_clean):
    """Quien busca no siempre tiene el número de la solicitud."""
    _limpiar()
    _sql("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total, fecha, "
         "categoria) VALUES (?,?,?,?,?,?)",
         (_OC, 'PRESQUIM', 'Recibida', 900000, '2026-08-21', 'MP'))
    try:
        d = _login(app).get('/api/compras/donde-esta/%s' % _OC).get_json()
        assert d['encontrado'], "no encontró una orden que existe"
        assert d['orden']['estado'] == 'Recibida'
        assert 'pagar' in (d.get('donde_esta') or '').lower(), \
            "una orden recibida se ve en Por pagar: %r" % d.get('donde_esta')
    finally:
        _limpiar()


def test_un_numero_que_no_existe_lo_DICE_en_vez_de_devolver_vacio(app, db_clean):
    """Un resultado vacío se lee como "no hay nada que hacer"; acá significa otra cosa (M100)."""
    _limpiar()
    d = _login(app).get('/api/compras/donde-esta/SOL-QA-NO-EXISTE-9999').get_json()
    assert d['encontrado'] is False
    assert d.get('donde_esta'), "no explica que no existe"
    assert 'SOL-' in d['donde_esta'], "no dice cómo se escriben los números"


def test_el_buscador_tiene_PUERTA_en_la_pantalla(app, db_clean):
    """Un endpoint sin botón no existe (M121/M197). El buscador va en el ENCABEZADO, visible
    desde cualquier pestaña: una solicitud se pierde justo cuando uno no sabe en qué pestaña
    buscarla. Se mide sobre la pantalla SERVIDA, con sus bundles (M216)."""
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app, 'sebastian'), '/compras')
    assert 'id="dd-num"' in js, "no hay dónde escribir el número"
    assert 'dondeQuedo()' in js, "el buscador no llama a nada"
    assert 'function dondeQuedo' in js, "la función que abre el buscador no existe"
    assert '/api/compras/donde-esta/' in js, "el buscador no consulta el rastreador"
    assert 'id="dd-modal"' in js and 'id="dd-body"' in js,         "no hay dónde mostrar la respuesta"
    # y el modal se puede CERRAR: uno sin salida obliga a recargar la página (M254)
    i = js.find('id="dd-modal"')
    assert "display='none'" in js[i:i + 1400], "el modal no tiene forma de cerrarse"


def test_la_pantalla_avisa_a_donde_se_fue_cuando_NO_genera_orden(app, db_clean):
    """La causa, no el síntoma: aprobar sin OC dejaba la solicitud invisible y el mensaje no
    lo decía. Se mide sobre la pantalla SERVIDA (M216)."""
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app, 'sebastian'), '/compras')
    i = js.find("Solicitud aprobada")
    assert i != -1, "no está el mensaje de aprobación"
    bloque = js[i:i + 1200]
    assert 'if(!d.numero_oc)' in bloque.replace(' ', ''), \
        "el mensaje no contempla el caso sin orden de compra, que es el que se pierde"
    assert 'agrupadas' in bloque.lower(), \
        "no nombra la bandeja donde queda una solicitud de producción"
    assert 'Aprobada' in bloque, "no dice con qué filtro volver a encontrarla"
