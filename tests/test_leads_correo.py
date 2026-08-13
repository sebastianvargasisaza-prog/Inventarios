# -*- coding: utf-8 -*-
"""Los prospectos que llegan al correo de dirección entran al pipeline sin perderse.

Sebastián (13-ago): *"los leads llegan a mi correo direccion@animuslb.com y allí sólo llegan de
maquila porque los de Ánimus llegan a otro (...) normalmente llegan con el título cotización de
maquila o algo, y la mayoría son formularios de la página web"*.

Eso resuelve sin heurísticas la parte que yo no quería adivinar: **el BUZÓN es el filtro**. Meter
la regla en el contenido del mensaje habría llenado de ruido el único lugar donde se mira quién
falta, y un registro con ruido no queda incompleto: queda FALSO.
"""
import pytest

TEST_PASSWORD = "TestPass123"


@pytest.fixture
def luz(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "luz", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM leads_correo WHERE message_id LIKE 'LCTEST%'")
        c.execute("DELETE FROM maquila_pipeline WHERE empresa LIKE 'LCTEST%'")
        conn.commit()


def _lead(app, msgid, empresa='LCTEST COSMETICA SAS', asunto='Cotizacion de maquila'):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO leads_correo (message_id, remitente, asunto, fecha_correo, "
                  " cuerpo, empresa, contacto, telefono, email_contacto, producto) "
                  " VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (msgid, 'Ana <ana@lctest.co>', asunto, '2026-08-10 09:00:00',
                   'Empresa: %s\nNombre: Ana Perez\nTelefono: 3001234567' % empresa,
                   empresa, 'Ana Perez', '3001234567', 'ana@lctest.co', 'Serum facial'))
        conn.commit()
        return c.lastrowid


# ------------------------------------------------------------------ el parseo

def test_lee_los_campos_del_formulario_por_etiqueta(app):
    from leads_correo import parsear
    d = parsear('Cotizacion de maquila',
                'Empresa: LCTEST COSMETICA SAS\nNombre: Ana Perez\n'
                'Telefono: 3001234567\nProducto: Serum facial con niacinamida',
                'Ana <ana@lctest.co>')
    assert d['empresa'] == 'LCTEST COSMETICA SAS'
    assert d['contacto'] == 'Ana Perez'
    assert d['telefono'] == '3001234567'
    assert 'Serum' in d['producto']
    assert d['empresa_inferida'] is False


def test_sin_empresa_usa_el_contacto_pero_lo_MARCA_como_inferido(app):
    """Rellenar adivinando y no decirlo hace que alguien lea un nombre propio como razón social."""
    from leads_correo import parsear
    d = parsear('Consulta', 'Nombre: Carlos Gomez\nTelefono: 3009999999',
                'Carlos <carlos@x.co>')
    assert d['empresa'] == 'Carlos Gomez'
    assert d['empresa_inferida'] is True, 'lo dio por razón social sin decirlo'


def test_un_formulario_que_no_se_puede_parsear_NO_se_descarta(app):
    """Perder el cliente es peor que tener la ficha incompleta."""
    from leads_correo import parsear
    d = parsear('Hola', 'buenas, quiero cotizar unas cremas', 'Pedro <pedro@x.co>')
    assert d['empresa'], 'se quedó sin nada con qué identificarlo'
    assert d['empresa_inferida'] is True


# ------------------------------------------------------- del correo al pipeline

def test_el_correo_abre_su_tarjeta_en_el_pipeline(app, luz):
    _limpiar(app)
    lid = _lead(app, 'LCTEST-1')
    r = luz.post('/api/comercial/leads-correo/%d/al-pipeline' % lid, json={},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    d = r.get_json()
    assert d['nueva_tarjeta'] is True and d['pipeline_id']
    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT stage, origen, contacto_nombre FROM maquila_pipeline WHERE id=?",
            (d['pipeline_id'],)).fetchone()
    assert f[0] == 'consulta' and f[1] == 'correo direccion' and f[2] == 'Ana Perez'


def test_dos_correos_de_la_MISMA_empresa_no_abren_dos_tarjetas(app, luz):
    """La misma persona escribe dos veces legítimamente. Eso no puede volverse dos tarjetas."""
    _limpiar(app)
    a = _lead(app, 'LCTEST-A')
    b = _lead(app, 'LCTEST-B', asunto='Re: Cotizacion de maquila')
    p1 = luz.post('/api/comercial/leads-correo/%d/al-pipeline' % a, json={},
                  headers={'Origin': 'http://localhost'}).get_json()
    p2 = luz.post('/api/comercial/leads-correo/%d/al-pipeline' % b, json={},
                  headers={'Origin': 'http://localhost'}).get_json()
    assert p2['pipeline_id'] == p1['pipeline_id'] and p2['nueva_tarjeta'] is False, \
        'abrió una segunda tarjeta del mismo cliente'


def test_descartar_conserva_el_correo_y_su_motivo(app, luz):
    """Un filtro que bota sin dejar rastro es un filtro en el que no se puede confiar."""
    _limpiar(app)
    lid = _lead(app, 'LCTEST-D')
    r = luz.post('/api/comercial/leads-correo/%d/al-pipeline' % lid,
                 json={'descartar': True, 'motivo': 'es publicidad'},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['descartado'] is True
    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT descartado, motivo_descarte FROM leads_correo WHERE id=?", (lid,)).fetchone()
    assert f and f[0] == 1 and f[1] == 'es publicidad', 'lo borró en vez de descartarlo'


def test_la_lista_vacia_DICE_si_es_porque_no_se_leyo(app, luz):
    """Un cero que nadie pudo medir se lee como "no hay nada que hacer" y significa lo contrario."""
    _limpiar(app)
    d = luz.get('/api/comercial/leads-correo').get_json()
    assert d['buzon_configurado'] is False
    assert d.get('aviso') and 'no se leyó' in d['aviso'] or 'no se leyo' in (d.get('aviso') or ''), \
        'una lista vacía sin explicación se lee como "no llegó nada": %s' % d.get('aviso')


def test_leer_sin_buzon_configurado_dice_QUE_falta(app, luz):
    r = luz.post('/api/comercial/leads-correo/leer', json={},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 503
    d = r.get_json()
    assert d['codigo'] == 'SIN_BUZON' and 'IMAP_LEADS' in (d.get('como') or ''), \
        'no dijo qué falta configurar: %s' % d


def test_compras_no_ve_los_leads(app):
    """El pipeline sigue siendo confidencial: los dos bordes."""
    c = app.test_client()
    c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
           headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert c.get('/api/comercial/leads-correo').status_code == 403
    assert c.post('/api/comercial/leads-correo/leer', json={},
                  headers={'Origin': 'http://localhost'}).status_code == 403


# ------------------------------------------------------ la pantalla existe de verdad

def test_la_pantalla_tiene_como_llegar_a_los_endpoints(app, luz):
    """Casi le digo a Sebastián que apretara un botón que no existía.

    Construí los tres endpoints y ninguna pantalla los llamaba: una capacidad a la que nadie puede
    llegar no existe (M121). El guard mira el HTML REAL que se sirve, no el fuente.
    """
    html = luz.get('/comercial').get_data(as_text=True)
    assert 'pane-correo' in html, 'no hay pestaña para el correo'
    assert "switchPane('correo')" in html, 'la pestaña no lleva a ningún lado'
    for fn in ('cargarLeadsCorreo', 'leerBuzon', 'leadAlPipeline', 'leadDescartar'):
        assert ('function %s' % fn) in html, 'el botón llama a %s y no está definida' % fn
    # y los botones apuntan a los endpoints que existen
    assert '/api/comercial/leads-correo' in html


# ------------------------------------------------ barrer el ruido sin ir de a uno

def test_descarta_todo_lo_pendiente_de_un_remitente(app, luz):
    """Sebastián, tras la primera lectura: *"llegaron muchos que no son"*.

    Era esperable: a un correo de dirección le llega de todo. El filtro estructural sigue siendo
    correcto (mantiene afuera a los de Ánimus); lo que faltaba era barrer el ruido en bloque.

    Se barre por REMITENTE, que es un hecho del mensaje. Por palabras del asunto se botaría el
    "cotización de maquila" que venga con una redacción rara, y perder un cliente es mucho peor
    que dejar pasar publicidad.
    """
    _limpiar(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        for i in range(3):
            c.execute("INSERT INTO leads_correo (message_id, remitente, asunto, empresa) "
                      "VALUES (?,?,?,?)",
                      ('LCTEST-N%d' % i, 'Boletin <news@spam-lctest.co>', 'Novedades', 'LCTEST X'))
        c.execute("INSERT INTO leads_correo (message_id, remitente, asunto, empresa) "
                  "VALUES ('LCTEST-OK','Ana <ana@lctest.co>','Cotizacion','LCTEST COSMETICA SAS')")
        conn.commit()

    r = luz.post('/api/comercial/leads-correo/descartar-remitente',
                 json={'correo': 'news@spam-lctest.co', 'motivo': 'boletin'},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['descartados'] == 3, r.get_data(as_text=True)[:200]
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        otro = c.execute("SELECT descartado FROM leads_correo WHERE message_id='LCTEST-OK'").fetchone()
        n = c.execute("SELECT COUNT(*) FROM leads_correo WHERE message_id LIKE 'LCTEST-N%' "
                      "  AND descartado=1 AND motivo_descarte='boletin'").fetchone()
    assert otro[0] == 0, 'se llevó puesto un remitente distinto'
    assert n[0] == 3, 'no descartó los tres ni guardó el motivo'


def test_el_barrido_NO_toca_lo_que_ya_paso_al_pipeline(app, luz):
    """Ahí ya hubo una decisión de una persona; deshacerla en bloque sería pisarla."""
    _limpiar(app)
    lid = _lead(app, 'LCTEST-YA')
    luz.post('/api/comercial/leads-correo/%d/al-pipeline' % lid, json={},
             headers={'Origin': 'http://localhost'})
    r = luz.post('/api/comercial/leads-correo/descartar-remitente',
                 json={'correo': 'ana@lctest.co'}, headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['descartados'] == 0
    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT descartado FROM leads_correo WHERE id=?", (lid,)).fetchone()
    assert f[0] == 0, 'descartó uno que ya estaba en el pipeline'


def test_compras_no_puede_barrer(app):
    c = app.test_client()
    c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
           headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert c.post('/api/comercial/leads-correo/descartar-remitente',
                  json={'correo': 'x@y.co'},
                  headers={'Origin': 'http://localhost'}).status_code == 403
