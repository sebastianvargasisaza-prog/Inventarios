"""El ingreso a EOS · Sebastián 14-ago-2026: "se ve feito, no premium".

Lo que fija este test es el CONTRATO de la pantalla, que es lo que se rompe al
rediseñar: si el form deja de postear donde el backend espera, o los campos
cambian de nombre, nadie puede entrar y la pantalla se ve perfecta.
"""


def test_el_login_conserva_su_contrato(app):
    html = app.test_client().get('/login').data.decode('utf-8')
    for pieza in ('name="username"', 'name="password"', 'action="/login?next=',
                  'type="submit"'):
        assert pieza in html, 'el login perdió %s' % pieza


def test_el_login_puede_pintar_el_error_que_le_inyecta_el_backend(app):
    """El backend mete `<div class="err">…</div>` en el placeholder · si el estilo de
    esa clase desaparece, el mensaje sale sin formato o directamente invisible."""
    html = app.test_client().get('/login').data.decode('utf-8')
    assert '.err{' in html, 'no quedó el estilo del error'
    r = app.test_client().post('/login', data={'username': 'nadie', 'password': 'x'},
                               follow_redirects=False)
    cuerpo = r.data.decode('utf-8')
    if r.status_code == 200:
        assert 'class="err"' in cuerpo, 'el error no se pintó'


def test_el_simbolo_de_la_marca_se_lee(app):
    """Iba `stroke="#6d28d9"` DENTRO de un tile violeta: violeta sobre violeta (M114).

    Es el defecto que no da error y sólo se ve mirando: el logo casi no aparecía.
    """
    html = app.test_client().get('/login').data.decode('utf-8')
    # `brand-mark` a secas encuentra la REGLA CSS, no el elemento · se ancla al atributo.
    i = html.find('class="brand-mark"')
    assert i > 0, 'no está la marca'
    ventana = html[i:i + 700]
    assert 'stroke="#ffffff"' in ventana, 'el símbolo volvió a ir en violeta sobre el tile violeta'


def test_el_login_vive_sobre_los_tokens_del_sistema(app):
    """Sin esto la pantalla ignora el tema y vuelve a ser una isla oscura."""
    html = app.test_client().get('/login').data.decode('utf-8')
    assert 'cortex.css' in html, 'no enlaza el sistema de diseño'
    assert 'var(--cx-' in html, 'volvió a pintar con colores a mano'
    assert 'prefers-color-scheme' in html, 'dejó de respetar el tema del sistema'
