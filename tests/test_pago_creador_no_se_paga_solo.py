# -*- coding: utf-8 -*-
"""Un pago a creador no se marca Pagado por el paso del tiempo, y mirar una pantalla no mueve plata.

Sebastián 7-ago, sobre el hallazgo: *"resuelve el uno"*.

Había una regla que, si el pago llevaba más de 7 días publicado y no tenía OC válida, lo daba por
**Pagado**. Se escribió para limpiar históricos y quedó **sin fecha de corte**, o sea armada para
siempre: cualquier pago futuro registrado sin OC se iba a declarar pagado sólo por envejecer, sin
que saliera un peso ni entrara nada al libro. Y corría dentro de un **GET**, así que pasaba con
sólo abrir el panel (M113: un GET que muta duplica el daño de cualquier defecto de lectura).

Lo que queda: el estado del dinero se deriva de un HECHO de dinero (la OC pagada o rechazada),
una sola copia de la regla (M45), disparada por el reloj y por un POST explícito.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _seed(app, con_oc_pagada=False, publicado_hace=40):
    from database import get_db
    from datetime import date, timedelta
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM pagos_influencers WHERE influencer_nombre LIKE 'PSE %'")
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-PSE-1'")
        pub = (date.today() - timedelta(days=publicado_hace)).isoformat()
        if con_oc_pagada:
            c.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total) "
                      "VALUES ('OC-PSE-1','Creador X','Pagada',100000)")
            c.execute("INSERT INTO pagos_influencers (influencer_nombre, valor, fecha, "
                      "fecha_publicacion, numero_oc, estado) VALUES "
                      "('PSE CON OC', 100000, ?, ?, 'OC-PSE-1', 'Pendiente')", (pub, pub))
        else:
            c.execute("INSERT INTO pagos_influencers (influencer_nombre, valor, fecha, "
                      "fecha_publicacion, numero_oc, estado) VALUES "
                      "('PSE SIN OC', 100000, ?, ?, '', 'Pendiente')", (pub, pub))
        c.commit()


def _estado(app, nombre):
    from database import get_db
    with app.app_context():
        r = get_db().execute("SELECT estado FROM pagos_influencers WHERE influencer_nombre=?",
                             (nombre,)).fetchone()
    return r[0] if r else None


def test_ABRIR_el_panel_no_marca_nada_como_pagado(app, admin_client):
    """El caso que se estaba escapando: publicado hace 40 días, sin OC, y con sólo abrir la
    pantalla quedaba 'Pagada'. Nadie puede mostrar que esa plata salió."""
    _seed(app, con_oc_pagada=False, publicado_hace=40)
    r = admin_client.get('/api/marketing/influencers-panel')
    assert r.status_code == 200
    admin_client.get('/api/marketing/pagos-influencers')
    assert _estado(app, 'PSE SIN OC') == 'Pendiente', \
        'un pago sin respaldo se dio por pagado solo · el estado del dinero salió de una fecha'


def test_la_reconciliacion_SI_marca_lo_que_tiene_evidencia(app):
    """El otro borde: si la OC está pagada, el pago está pagado. Sin esto el guard podría estar
    bloqueando todo y pasaría igual de verde."""
    from database import get_db
    try:
        from blueprints.marketing import _reconciliar_pagos_influencer as rec
    except ImportError:
        from marketing import _reconciliar_pagos_influencer as rec
    _seed(app, con_oc_pagada=True)
    with app.app_context():
        c = get_db()
        res = rec(c, usuario='test')
        c.commit()
    assert res['pagadas'] >= 1, 'no reconcilió un pago cuya OC ya está pagada'
    assert _estado(app, 'PSE CON OC') == 'Pagada'


def test_es_IDEMPOTENTE(app):
    """Corre por cron tres veces al día: la segunda pasada no puede volver a contar lo mismo."""
    from database import get_db
    try:
        from blueprints.marketing import _reconciliar_pagos_influencer as rec
    except ImportError:
        from marketing import _reconciliar_pagos_influencer as rec
    _seed(app, con_oc_pagada=True)
    with app.app_context():
        c = get_db()
        rec(c, usuario='test'); c.commit()
        segunda = rec(c, usuario='test'); c.commit()
    assert segunda['pagadas'] == 0 and segunda['rechazadas'] == 0, \
        'la segunda corrida vuelve a tocar filas · no es idempotente'


def test_la_regla_de_los_7_DIAS_ya_no_existe_en_ningun_lado(app):
    """El barrido que impide que vuelva por la puerta de atrás (M45: un patrón vive en varios
    sitios · esta regla estaba en un GET y podría re-aparecer en otro)."""
    import ast
    import io as _io
    import re as _re
    src = _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'marketing.py'), encoding='utf-8').read()
    # ⚠ Sin comentarios: si no, el test encuentra MI PROPIA explicación de por qué se retiró y
    # falla (o pasa) por la razón equivocada · me pasó cuatro veces (M154).
    limpio = _re.sub(r'#[^\n]*', '', src)
    limpio = _re.sub(r'"""(?:.|\n)*?"""', '', limpio)
    assert 'fecha_publicacion <' not in limpio.replace(' ', '').replace('fecha_publicacion<', 'fecha_publicacion <'), \
        'volvió una regla que decide el estado del dinero por una fecha'
    # y ningún GET puede volver a mutar el estado de un pago
    arbol = ast.parse(src)
    culpables = []
    for n in ast.walk(arbol):
        if not isinstance(n, ast.FunctionDef):
            continue
        mets = None
        es_ruta = False
        for d in n.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == 'route':
                es_ruta = True
                for kw in d.keywords:
                    if kw.arg == 'methods':
                        try:
                            mets = [x.value for x in kw.value.elts]
                        except Exception:
                            pass
        if not es_ruta:
            continue
        if set(m.upper() for m in (mets or ['GET'])) != {'GET'}:
            continue
        cuerpo = ast.get_source_segment(src, n) or ''
        cuerpo = _re.sub(r'#[^\n]*', '', cuerpo)
        if _re.search(r"UPDATE\s+pagos_influencers\s+SET[^\"']{0,80}estado\s*=", cuerpo, _re.I | _re.S):
            culpables.append(n.name)
    assert not culpables, 'un GET volvió a mutar el estado de un pago: %s' % culpables


def test_lo_que_NO_tiene_respaldo_se_puede_VER(app, admin_client):
    """Retirar la regla no puede significar que esos pagos desaparezcan del radar: un pendiente
    que nadie mira envejece igual. Se listan para que una persona decida (M19/M124)."""
    _seed(app, con_oc_pagada=False, publicado_hace=40)
    r = admin_client.get('/api/marketing/pagos-sin-evidencia')
    assert r.status_code == 200
    j = r.get_json()
    assert any(x['creador'] == 'PSE SIN OC' for x in j['items']), \
        'el pago sin respaldo no aparece en ninguna parte'
    assert j.get('que_hacer'), 'no dice qué hacer con ellos'
