"""Cuando un cliente pide por el portal, tiene que verse donde cada uno mira.

Sebastián 14-ago-2026: "también le debe salir a Luz aquí: tu cliente tal acaba de
pedir · y a mí en CEO · y generar alerta por correo".

El pedido queda PENDIENTE y sólo entra al plan cuando alguien lo confirma, así que
un aviso que no llega es un cliente esperando sin que nada falle a la vista.
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _sembrar_pedido(cliente='Cliente Que Pidio', producto='ZAVI PRODUCTO', uds=400):
    _exec("DELETE FROM pedidos_b2b WHERE cliente_id LIKE 'ZAVI%'")
    return _exec(
        "INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, cantidad_uds, "
        "ml_unidad, fecha_estimada, estado, urgencia, creado_at_utc, creado_por) "
        "VALUES ('ZAVI1', ?, ?, ?, 30, '2026-12-01', 'pendiente', 'alta', "
        "'2026-08-10T09:00:00Z', 'portal:cliente@zavi.test')",
        (cliente, producto, uds))


def test_a_luz_le_sale_en_su_panel(app, db_clean):
    _sembrar_pedido()
    from config import ESPAGIRIA_ACCESS
    usuario = 'luz' if 'luz' in ESPAGIRIA_ACCESS else sorted(ESPAGIRIA_ACCESS)[0]
    d = _login(app, usuario).get('/api/espagiria/quick-actions').get_json()
    secciones = {s.get('id'): s for s in (d.get('secciones') or [])}
    sec = secciones.get('pedidos_portal_por_confirmar')
    assert sec, 'el pedido del cliente no aparece en el panel de Luz: %s' % list(secciones)
    assert sec['items'], 'la sección está pero sin el pedido'
    assert 'Cliente Que Pidio' in str(sec['items']), 'no dice QUIÉN pidió'
    assert sec.get('link'), 'no hay a dónde ir a confirmarlo'


def test_al_ceo_le_sale_en_su_cola(app, db_clean):
    _sembrar_pedido()
    d = _login(app).get('/api/centro/decisiones').get_json()
    dec = d.get('decisiones') or d.get('items') or []
    mias = [x for x in dec if 'esperando confirmación' in str(x.get('titulo', ''))]
    assert mias, 'el pedido del cliente no llega a la cola del CEO'
    assert 'Cliente Que Pidio' in str(mias[0].get('detalle', '')), 'no dice quién pidió'
    assert 'día' in str(mias[0].get('detalle', '')), (
        'no dice hace cuánto espera · un aviso que no envejece se vuelve ruido')


def test_ningun_aviso_del_portal_lleva_a_una_ruta_inexistente(app, db_clean):
    """El aviso del pedido apuntaba a /dashboard#programacion, que no existe.

    El guard de M202 sólo miraba los enlaces a /admin, así que este pasó por al lado:
    ahora se revisan TODOS los `link=` del módulo.
    """
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas = {str(r.rule) for r in app.url_map.iter_rules()}
    malos = []
    for arch in ('api/blueprints/portal.py', 'api/blueprints/espagiria.py',
                 'api/blueprints/hub.py'):
        with open(os.path.join(raiz, arch), encoding='utf-8') as fh:
            texto = fh.read()
        for enlace in set(re.findall(r"link=['\"](/[^'\"]*)['\"]", texto)):
            base = enlace.split('?')[0].split('#')[0]
            if base and base not in rutas:
                malos.append('%s -> %s' % (arch, enlace))
    assert not malos, 'avisos que llevan a una ruta inexistente: %s' % malos


def test_el_correo_se_intenta_y_lo_que_no_sale_se_dice(app, db_clean, caplog):
    """Sin correos cargados el aviso queda en la campana, y eso se DECLARA.

    Un envío que se da por hecho y no salió es indistinguible de uno que llegó (M198).
    """
    import io as _io
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with _io.open(os.path.join(raiz, 'api', 'blueprints', 'portal.py'), encoding='utf-8') as fh:
        src = fh.read()
    i = src.find('def portal_crear_pedido')
    j = src.find('\n@bp.route', i + 10)
    cuerpo = src[i:j]
    assert '_enviar_email_async' in cuerpo, 'el pedido nuevo ya no manda correo'
    assert 'usuarios_identidad' in cuerpo, 'los destinatarios ya no salen de los usuarios reales'
    assert 'quedó sólo' in cuerpo or 'no salió' in cuerpo, (
        'si el correo no sale, tiene que quedar dicho en el log')
