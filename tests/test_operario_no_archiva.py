# -*- coding: utf-8 -*-
"""El operario modifica y carga, pero no elimina ni archiva. Y todo cambio queda con su autor.

Sebastián 7-ago-2026: *"los operarios pueden modificar un inventario, ingresar un producto, pero
no eliminar ni archivar, y los cambios quedan con el usuario que lo modifica"*.

La regla se escribió por EXCLUSIÓN (`config.puede_archivar` = todos menos `PLANTA_USERS`) y no con
una lista de permitidos por endpoint: una lista escrita a mano siempre deja afuera a alguien que
nadie se acordó de incluir, y eso no se descubre leyendo código, se descubre con la persona
trabada en pleno turno (M32/M121).

⚠ Los dos bordes importan por igual. Un test que sólo comprueba el 403 del operario pasa verde
aunque el gate haya bloqueado también a compras, que es cambiar un hueco por una traba.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

TEST_PASSWORD = 'TestPass123'
OPERARIO = 'mayerlin'      # de PLANTA_USERS


def _cliente(app, quien):
    c = app.test_client()
    r = c.post('/login', data={'username': quien, 'password': TEST_PASSWORD},
               headers={'Origin': 'http://localhost'}, follow_redirects=False)
    assert r.status_code == 302, 'no pude loguear a %s (%s)' % (quien, r.status_code)
    return c


def test_la_regla_esta_escrita_por_EXCLUSION(app):
    """Si se escribiera como lista de permitidos, agregar un rol mañana lo dejaría trabado."""
    from config import puede_archivar, PLANTA_USERS
    for u in PLANTA_USERS:
        assert puede_archivar(u) is False, '%s es operario y podría archivar' % u
    for u in ('catalina', 'mayra', 'laura', 'miguel', 'luz', 'sebastian', 'alejandro', 'hernando'):
        assert puede_archivar(u) is True, '%s quedó trabado y no es operario' % u
    assert puede_archivar('') is False, 'sin usuario no se decide que sí'
    assert puede_archivar(None) is False


def _seed_presentacion(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre='OPERARIO TEST'")
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo) VALUES ('OPERARIO TEST','V30','30 ml',30,1)")
        c.commit()
        r = c.execute("SELECT id FROM producto_presentaciones WHERE producto_nombre='OPERARIO TEST'"
                      ).fetchone()
        return r[0]


def test_el_operario_SI_puede_modificar(app):
    """La mitad que se rompe si el gate se pone de más: él carga y corrige su trabajo."""
    pid = _seed_presentacion(app)
    r = _cliente(app, OPERARIO).put('/api/planta/presentaciones/%d' % pid,
                                    json={'etiqueta': '30 ml corregido'},
                                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, 'se le trabó al operario algo que SÍ puede hacer: %s' % r.data[:200]


def test_el_operario_NO_puede_archivar(app):
    pid = _seed_presentacion(app)
    r = _cliente(app, OPERARIO).delete('/api/planta/presentaciones/%d' % pid,
                                       headers={'Origin': 'http://localhost'})
    assert r.status_code == 403, 'el operario archivó una presentación'
    from database import get_db
    with app.app_context():
        act = get_db().execute("SELECT activo FROM producto_presentaciones WHERE id=?", (pid,)).fetchone()
    assert act and act[0] == 1, 'la fila quedó archivada pese al 403'


def test_compras_SI_puede_archivar(app):
    """El otro borde · sin esto, el guard podría estar bloqueando a todo el mundo y pasaría igual."""
    pid = _seed_presentacion(app)
    r = _cliente(app, 'catalina').delete('/api/planta/presentaciones/%d' % pid,
                                         headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, 'se trabó a compras: %s' % r.data[:200]


def test_el_cambio_queda_con_su_AUTOR(app):
    """*"los cambios quedan con el usuario que lo modifica"* · sin autor, un número que decide qué
    envase se compra no se puede explicar después."""
    from database import get_db
    pid = _seed_presentacion(app)
    with app.app_context():
        get_db().execute("DELETE FROM audit_log WHERE tabla='producto_presentaciones' AND registro_id=?",
                         (str(pid),))
        get_db().commit()
    _cliente(app, OPERARIO).put('/api/planta/presentaciones/%d' % pid,
                                json={'etiqueta': '30 ml v2'},
                                headers={'Origin': 'http://localhost'})
    with app.app_context():
        r = get_db().execute(
            "SELECT usuario, accion FROM audit_log WHERE tabla='producto_presentaciones' "
            "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(pid),)).fetchone()
    assert r, 'el cambio no dejó rastro'
    assert r[0] == OPERARIO, 'el rastro no dice quién lo modificó (%s)' % (r[0],)
    assert r[1] == 'EDITAR_PRESENTACION'


def test_el_archivado_tambien_deja_QUIEN_y_el_estado_previo(app):
    from database import get_db
    pid = _seed_presentacion(app)
    with app.app_context():
        get_db().execute("DELETE FROM audit_log WHERE tabla='producto_presentaciones' AND registro_id=?",
                         (str(pid),))
        get_db().commit()
    _cliente(app, 'catalina').delete('/api/planta/presentaciones/%d' % pid,
                                     headers={'Origin': 'http://localhost'})
    with app.app_context():
        r = get_db().execute(
            "SELECT usuario, accion, antes FROM audit_log WHERE tabla='producto_presentaciones' "
            "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(pid),)).fetchone()
    assert r and r[0] == 'catalina' and r[1] == 'ARCHIVAR_PRESENTACION'
    # el estado PREVIO es lo que permite deshacer · un audit sin `antes` no sirve para revertir
    assert r[2] and 'V30' in str(r[2]), 'el rastro no guarda cómo estaba antes'


def test_TODOS_los_archivadores_de_maestro_llevan_el_gate(app):
    """El barrido que evita que el próximo nazca sin gate (M45: un patrón vive en varios sitios).

    No se cuenta cuántos hay: se enumeran los que se revisaron uno por uno y se exige que cada uno
    consulte el permiso. Una lista escrita a mano se pudre, así que además se afirma DÓNDE está
    cada bloque, y si alguien mueve el código el test lo dice.
    """
    import io as _io
    revisados = [
        ('api/blueprints/inventario.py', 'mee_item_detalle'),
        ('api/blueprints/programacion.py', 'planta_presentaciones_detail'),
        ('api/blueprints/programacion.py', 'planta_equipos_detail'),
        ('api/blueprints/programacion.py', 'mp_bridge_delete'),
        ('api/blueprints/auto_plan.py', 'sku_mee_config_modificar'),
        ('api/blueprints/compras.py', 'consumible_editar'),
    ]
    import ast
    faltan = []
    for rel, fn in revisados:
        src = _io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()
        arbol = ast.parse(src)
        hallada = False
        for n in ast.walk(arbol):
            if isinstance(n, ast.FunctionDef) and n.name == fn:
                hallada = True
                cuerpo = ast.get_source_segment(src, n) or ''
                if 'puede_archivar' not in cuerpo:
                    faltan.append('%s::%s' % (rel, fn))
        if not hallada:
            faltan.append('%s::%s (ya no existe · el test quedó viejo)' % (rel, fn))
    assert not faltan, 'archivan un registro maestro SIN consultar el permiso: %s' % faltan
