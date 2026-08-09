# -*- coding: utf-8 -*-
"""El memo por request de los catálogos por PRODUCTO no puede cambiar ni una respuesta.

PERF 8-ago (sonda local · regla 0.5): `/api/plan/dashboard` hacía 176 consultas y **61 eran la
misma tabla chica** (`sku_planeacion_config`), pedida de a una fila por producto desde tres
sitios distintos, más 22 de la presentación default. Se leen una vez por request.

Un atajo que puede contestar distinto no es un atajo (M128), así que lo que se prueba acá no es
que sea rápido: es que la respuesta sea **la misma** con el memo puesto y con el memo apagado.
Apagarlo devuelve al camino consulta-por-consulta, que es el que estaba antes.
"""
import hashlib
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

RUTAS = ['/api/plan/dashboard', '/api/plan/necesidades', '/api/plan/salud-cadenas',
         '/api/plan/factibilidad', '/api/centro/decisiones']

# Campos que cambian solos en cada llamada (relojes): comparar el hash crudo los delataría y el
# guard fallaría por la razón equivocada (M152).
VOLATILES = ('generado_en', 'generado_at', 'timestamp', 'ts', 'ahora')


def _limpio(dato):
    if isinstance(dato, dict):
        return {k: _limpio(v) for k, v in sorted(dato.items()) if k not in VOLATILES}
    if isinstance(dato, list):
        return [_limpio(x) for x in dato]
    return dato


def _huella(cli, ruta):
    r = cli.get(ruta)
    assert r.status_code == 200, '%s dio %s' % (ruta, r.status_code)
    return hashlib.sha256(
        json.dumps(_limpio(r.get_json()), sort_keys=True, default=str).encode()).hexdigest()


def test_la_respuesta_es_LA_MISMA_con_el_memo_y_sin_el(app, admin_client):
    import blueprints.auto_plan as A
    con = {r: _huella(admin_client, r) for r in RUTAS}
    orig = A._mapas_producto
    A._mapas_producto = lambda c: None          # camino de siempre, consulta por consulta
    try:
        sin = {r: _huella(admin_client, r) for r in RUTAS}
    finally:
        A._mapas_producto = orig
    distintas = [r for r in RUTAS if con[r] != sin[r]]
    assert not distintas, 'el memo cambia la respuesta de: %s' % distintas


def test_el_memo_RESPETA_el_orden_de_la_presentacion_default(app, admin_client):
    """La presentación se elegía con `activo=1 ORDER BY es_default DESC, id ASC LIMIT 1`.

    Si el mapa se quedara con otra fila, el volumen cambiaría y con él los kg del plan. Se siembra
    el caso que lo distingue: una presentación NO default con id MENOR (la que ganaría si el orden
    fuera sólo por id) y la default con id mayor.
    """
    from database import get_db
    from blueprints.auto_plan import _mapas_producto
    P = 'MEMOPROD ORDEN TEST'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, es_default, activo) VALUES (?,'V15','15 ml',15,0,1)", (P,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, es_default, activo) VALUES (?,'V30','30 ml',30,1,1)", (P,))
        c.commit()
        try:
            m = _mapas_producto(c)
            assert m is not None and m.get('pres') is not None
            fila = m['pres'].get(P)
            assert fila and fila['volumen_ml'] == 30, \
                'el mapa eligió otra presentación que el LIMIT 1 original: %s' % (fila,)
        finally:
            c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
            c.commit()


def test_una_venta_esperada_en_CERO_no_es_un_override(app, admin_client):
    """La consulta original filtraba `COALESCE(venta_esperada_mes,0) > 0`: cero y NULL significan
    "sin fijar". Si el mapa devolviera el 0 como override, la velocidad del producto caería a cero
    y el motor dejaría de programarlo (M128 · el atajo contestando distinto)."""
    from database import get_db
    from blueprints.auto_plan import venta_esperada_override
    P = 'MEMOPROD CERO TEST'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (P,))
        c.execute("INSERT INTO sku_planeacion_config (producto_nombre, venta_esperada_mes) "
                  "VALUES (?,0)", (P,))
        c.commit()
        try:
            assert venta_esperada_override(c, P) is None, 'tomó un 0 como venta fijada'
            c.execute("UPDATE sku_planeacion_config SET venta_esperada_mes=304.4 "
                      " WHERE producto_nombre=?", (P,))
            c.commit()
            try:
                from flask import g as _g
                if hasattr(_g, '_prod_mapas'):
                    delattr(_g, '_prod_mapas')      # el memo es por request
            except Exception:
                pass
            v = venta_esperada_override(c, P)
            assert v and abs(v - 10.0) < 0.01, 'no leyó la venta fijada: %s' % v
        finally:
            c.execute("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (P,))
            c.commit()
