# -*- coding: utf-8 -*-
"""Cambiar el empaque de un producto deja QUIÉN lo cambió.

Sebastián, dictando permisos (7-ago): *"los operarios pueden modificar un inventario, ingresar un
producto, pero no eliminar ni archivar, y **los cambios quedan con el usuario que lo modifica**"*.

Los ocho endpoints que editan `producto_presentaciones` no dejaban ninguno. Importa más que en
otras tablas: de ahí salen el envase, la tapa, la caja y la etiqueta que se COMPRAN y se
DESCUENTAN (M55). Cambiar acá el frasco de un producto no da error -- da una compra equivocada, y
sin rastro no hay forma de saber quién ni cuándo (M19/M137).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PROD = 'RASTRO EMPAQUE TEST'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        # audit_log NO se limpia: es append-only por trigger (Part 11 11.10(e)) y borrarlo es
        # justo lo que el registro existe para impedir. Los rastros se filtran por producto.
        c.execute("DELETE FROM maestro_mee WHERE codigo IN ('RE-FR-A','RE-FR-B')")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('RE-FR-A','FRASCO A 30','Frasco',0)")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('RE-FR-B','FRASCO B 30','Frasco',0)")
        c.commit()


def _rastros(app, accion=None):
    from database import get_db
    with app.app_context():
        q = ("SELECT accion, usuario, COALESCE(antes,''), COALESCE(despues,'') FROM audit_log "
             " WHERE tabla='producto_presentaciones' AND COALESCE(detalle,'') LIKE ?")
        par = ['%' + PROD + '%']
        if accion:
            q += " AND accion=?"
            par.append(accion)
        return get_db().execute(q, par).fetchall()


def test_CREAR_un_envase_deja_rastro(app, admin_client):
    _limpiar(app)
    r = admin_client.get('/api/programacion/pres-crear?producto=%s&envase=RE-FR-A&volumen_ml=30'
                         % PROD.replace(' ', '%20'))
    assert r.status_code == 200 and r.get_json().get('ok'), r.data[:200]
    filas = _rastros(app, 'PRES_CREAR')
    assert filas, 'crear el envase de un producto no dejó rastro'
    assert filas[0][1], 'el rastro no dice QUIÉN'
    _limpiar(app)


def test_CAMBIAR_el_envase_guarda_el_ANTERIOR(app, admin_client):
    """El rastro sirve para deshacer sólo si guarda de qué envase se venía: con un frasco
    equivocado, la pregunta es *"¿cuál era antes?"*, no *"¿cuál es ahora?"*."""
    _limpiar(app)
    admin_client.get('/api/programacion/pres-crear?producto=%s&envase=RE-FR-A&volumen_ml=30'
                     % PROD.replace(' ', '%20'))
    r = admin_client.get('/api/programacion/pres-set-envase?producto=%s&presentacion_codigo=V30'
                         '&envase=RE-FR-B' % PROD.replace(' ', '%20'))
    assert r.status_code == 200, r.data[:200]
    filas = _rastros(app, 'PRES_SET_ENVASE')
    assert filas, 'cambiar el envase no dejó rastro'
    antes, despues = filas[-1][2], filas[-1][3]
    assert 'RE-FR-A' in antes, 'el rastro no guarda el envase ANTERIOR: %s' % antes[:200]
    assert 'RE-FR-B' in despues, 'el rastro no guarda el envase nuevo: %s' % despues[:200]
    _limpiar(app)


def test_DAR_DE_BAJA_una_presentacion_deja_rastro(app, admin_client):
    _limpiar(app)
    admin_client.get('/api/programacion/pres-crear?producto=%s&envase=RE-FR-A&volumen_ml=30'
                     % PROD.replace(' ', '%20'))
    r = admin_client.get('/api/programacion/pres-quitar?producto=%s&presentacion_codigo=V30'
                         % PROD.replace(' ', '%20'))
    assert r.status_code == 200, r.data[:200]
    assert _rastros(app, 'PRES_QUITAR'), 'quitar una presentación no dejó rastro'
    _limpiar(app)


def test_NINGUN_endpoint_que_edita_el_empaque_se_queda_sin_rastro(app):
    """Enumerar los ocho no alcanza: el que se escriba mañana nace sin rastro y nadie lo nota.

    Se verifica sobre el fuente que toda función que ESCRIBE `producto_presentaciones` llame al
    helper del rastro (o a `audit_log` directo, como hace el guardado de la tabla de
    normalización).
    """
    import ast
    import io
    import re
    ruta = os.path.join(RAIZ, 'api', 'blueprints', 'programacion.py')
    src = io.open(ruta, encoding='utf-8').read()
    lineas = src.splitlines()
    sin = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.FunctionDef):
            continue
        if not any(isinstance(d, ast.Call) and getattr(d.func, 'attr', '') == 'route'
                   for d in n.decorator_list):
            continue
        cuerpo = '\n'.join(lineas[n.lineno - 1:(n.end_lineno or n.lineno)])
        escribe = re.search(r'(UPDATE|INSERT\s+INTO)\s+producto_presentaciones\b', cuerpo, re.I)
        if escribe and '_pres_rastro' not in cuerpo and 'audit_log' not in cuerpo:
            sin.append('%s (línea %d)' % (n.name, n.lineno))
    assert not sin, 'editan el empaque sin dejar quién: %s' % sin
