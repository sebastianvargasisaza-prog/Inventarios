# -*- coding: utf-8 -*-
"""Registro en contingencia · tarea B-13 del ASG-PRO-014 (numeral 5.6.2).

Lo que se protege: que el papel que se llenó durante un apagón ENTRE al expediente del lote, y
que entre diciendo la verdad. La regla dura es que el registro conserve la fecha del HECHO y que
la de carga la ponga el servidor: si se pudiera cargar como si hubiera sido contemporáneo, una
contingencia legítima se volvería un registro falso, y eso es peor que el hueco que viene a tapar.
"""
from datetime import datetime, timedelta

import pytest

TEST_PASSWORD = "TestPass123"


def _hoy_col():
    return (datetime.utcnow() - timedelta(hours=5)).date()


@pytest.fixture
def planta_client(app):
    """Sesión de alguien de planta · es quien registró en papel durante el turno."""
    c = app.test_client()
    r = c.post("/login", data={"username": "smurillo", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, "login de planta falló en la fixture: %s" % r.status_code
    return c


def _campos(**extra):
    base = {'tipo_registro': 'dispensacion',
            'fecha_hecho': _hoy_col().isoformat(),
            'ejecutado_por': 'Mayerlin Rodriguez'}
    base.update(extra)
    return base


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("DELETE FROM registros_contingencia WHERE ejecutado_por LIKE 'CTG-%'")
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Lo que hace legítimo el registro tardío: las DOS fechas
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_guarda_la_fecha_del_hecho_y_aparte_la_de_carga(app, planta_client):
    """La fecha del hecho sale del papel; la de carga la pone el SERVIDOR, no el cliente."""
    _limpiar(app)
    ayer = (_hoy_col() - timedelta(days=1)).isoformat()
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(fecha_hecho=ayer, ejecutado_por='CTG-Mayerlin',
                                        lote='LOTE-CTG-1'),
                           content_type='multipart/form-data')
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    d = r.get_json()
    assert d['ok'] is True

    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT fecha_hecho, cargado_at, cargado_por FROM registros_contingencia WHERE id=?",
            (d['id'],)).fetchone()
    assert f[0] == ayer, 'no conservó la fecha del hecho'
    assert f[1].startswith(_hoy_col().isoformat()), 'la fecha de carga no es la de hoy del servidor'
    assert f[2] == 'smurillo', 'no guardó quién cargó'


def test_el_cliente_no_puede_dictar_la_fecha_de_carga(app, planta_client):
    """DIENTES · aunque el formulario mande `cargado_at`, el servidor lo ignora.

    Si se pudiera fijar desde afuera, un registro tardío podría hacerse pasar por contemporáneo,
    que es justo lo que este mecanismo existe para impedir.
    """
    _limpiar(app)
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(ejecutado_por='CTG-Falsificador',
                                        cargado_at='2020-01-01 00:00:00',
                                        cargado_por='otra-persona'),
                           content_type='multipart/form-data')
    assert r.status_code == 200
    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT cargado_at, cargado_por FROM registros_contingencia WHERE id=?",
            (r.get_json()['id'],)).fetchone()
    assert not f[0].startswith('2020'), 'el cliente logró dictar la fecha de carga'
    assert f[1] == 'smurillo', 'el cliente logró dictar quién cargó'


def test_rechaza_una_fecha_en_el_futuro(app, planta_client):
    """Un registro tardío es legítimo; uno del futuro es un dato imposible."""
    _limpiar(app)
    manana = (_hoy_col() + timedelta(days=1)).isoformat()
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(fecha_hecho=manana, ejecutado_por='CTG-X'),
                           content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'futuro' in r.get_json()['error'].lower()


def test_avisa_cuando_se_carga_fuera_del_plazo_pero_NO_bloquea(app, planta_client):
    """El plazo son 24 horas · pasado eso se avisa, no se rechaza: el dato ya existe en papel."""
    _limpiar(app)
    hace_5 = (_hoy_col() - timedelta(days=5)).isoformat()
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(fecha_hecho=hace_5, ejecutado_por='CTG-Tardio'),
                           content_type='multipart/form-data')
    assert r.status_code == 200, 'un registro tardío TIENE que poder entrar'
    avisos = ' '.join(r.get_json()['avisos']).lower()
    assert '24 horas' in avisos or 'días después' in avisos, r.get_json()['avisos']


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El soporte se pide, no se exige
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_sin_foto_entra_igual_y_queda_marcado(app, planta_client):
    """Bloquear por falta de foto reabriría el hueco que la contingencia viene a tapar."""
    _limpiar(app)
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(ejecutado_por='CTG-SinFoto'),
                           content_type='multipart/form-data')
    assert r.status_code == 200
    d = r.get_json()
    assert d['sin_soporte'] is True
    assert any('soporte' in a.lower() or 'evidencia' in a.lower() for a in d['avisos'])

    lista = planta_client.get('/api/planta/contingencia').get_json()
    assert lista['pendientes_soporte'] >= 1, 'un pendiente de soporte tiene que salir en la lista'


def test_rechaza_un_formato_de_archivo_que_no_es_evidencia(app, planta_client):
    import io as _io
    _limpiar(app)
    datos = _campos(ejecutado_por='CTG-Exe')
    datos['soporte'] = (_io.BytesIO(b'MZ...'), 'virus.exe')
    r = planta_client.post('/api/planta/contingencia', data=datos,
                           content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'formato' in r.get_json()['error'].lower()


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Lo que le da sentido a todo: el papel entra al EXPEDIENTE del lote
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_con_lote_queda_colgado_del_expediente(app, planta_client):
    """Sin esto el registro existiría en una tabla propia y el expediente del lote seguiría
    teniendo el mismo hueco · que es exactamente el problema que se venía a resolver."""
    _limpiar(app)
    lote = 'LOTE-CTG-EXPEDIENTE'
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("DELETE FROM documentos_regulados WHERE lote=?", (lote,))
        conn.commit()

    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(ejecutado_por='CTG-Expediente', lote=lote,
                                        tipo_registro='despeje_linea'),
                           content_type='multipart/form-data')
    assert r.status_code == 200

    with app.app_context():
        from database import get_db
        f = get_db().cursor().execute(
            "SELECT tipo_doc, titulo, ref_tabla FROM documentos_regulados "
            "WHERE lote=? AND COALESCE(anulado,0)=0", (lote,)).fetchone()
    assert f is not None, 'el registro no se inscribió en el expediente del lote'
    assert f[0] == 'CONTINGENCIA-DESPEJE_LINEA'
    assert 'contingencia' in f[1].lower(), 'el expediente tiene que decir que fue una contingencia'
    assert f[2] == 'registros_contingencia'


def test_sin_lote_avisa_que_no_cuelga_de_ningun_expediente(app, planta_client):
    _limpiar(app)
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(ejecutado_por='CTG-SinLote'),
                           content_type='multipart/form-data')
    assert r.status_code == 200
    assert any('lote' in a.lower() for a in r.get_json()['avisos'])


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Validación y permisos
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_exige_lo_que_firma_el_papel(app, planta_client):
    _limpiar(app)
    sin_quien = _campos(ejecutado_por='')
    r = planta_client.post('/api/planta/contingencia', data=sin_quien,
                           content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'ejecut' in r.get_json()['error'].lower()

    sin_fecha = _campos(fecha_hecho='')
    r = planta_client.post('/api/planta/contingencia', data=sin_fecha,
                           content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'fecha' in r.get_json()['error'].lower()


def test_tipo_de_registro_contra_lista_blanca(app, planta_client):
    _limpiar(app)
    r = planta_client.post('/api/planta/contingencia',
                           data=_campos(tipo_registro='lo_que_se_me_ocurra'),
                           content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'validos' in r.get_json()


def test_planta_calidad_y_aseguramiento_pueden_cargar(app):
    """El borde de los DOS lados: quien estuvo en el turno entra, y el resto no.

    Un test que sólo verifica el 403 pasa verde aunque el gate haya trabado a todo el mundo
    (M171).
    """
    for usuario in ('smurillo', 'laura', 'miguel'):
        c = app.test_client()
        r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
                   headers={"Origin": "http://localhost"}, follow_redirects=False)
        if r.status_code != 302:
            continue                     # usuario no configurado en este entorno
        resp = c.post('/api/planta/contingencia',
                      data=_campos(ejecutado_por='CTG-%s' % usuario),
                      content_type='multipart/form-data')
        assert resp.status_code == 200, '%s debería poder cargar: %s' % (
            usuario, resp.get_data(as_text=True)[:200])


def test_quien_no_estuvo_en_el_turno_no_carga(logged_client):
    """valentina (comercial) no registra producción y no puede cargar registros regulados."""
    r = logged_client.post('/api/planta/contingencia', data=_campos(),
                           content_type='multipart/form-data')
    assert r.status_code == 403


def test_sin_sesion_no_se_puede_leer(client):
    assert client.get('/api/planta/contingencia').status_code in (401, 302)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La pantalla y su enlace
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_la_pantalla_abre(planta_client):
    r = planta_client.get('/planta/contingencia')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'fecha del hecho' in html.lower()
    assert '/api/planta/contingencia' in html


def test_la_pantalla_esta_enlazada():
    """M121 · una pantalla sin enlace obliga a teclear la URL, y eso es no existir · y el día que
    se usa es justo el día en que nadie va a andar buscando."""
    import io
    import re
    s = io.open('api/templates_py/dashboard_html.py', encoding='utf-8').read()
    # Se quitan los comentarios HTML para no encontrar la propia explicación (M154).
    sin_comentarios = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    assert re.search(r'''href=["']/planta/contingencia["']''', sin_comentarios), \
        'la pantalla de contingencia no está enlazada desde Planta'
