# -*- coding: utf-8 -*-
"""Catalina reparte el lote entre frascos cuando el habitual no alcanza.

Sebastián (12-ago): *"no alcanza el envase habitual, entonces 70 unidades van en este envase y 30
en este otro, y esto se va a reflejar en el calendario"*.

Hasta hoy sólo existía un override de UN envase para todo el lote: sirve para cambiar el frasco
entero, no para partirlo -- que es justo el caso que aparece cuando el stock no da.

Dos reglas sostienen que esto sirva:

  · **El reparto tiene que CERRAR.** Uno que no cuadra es peor que ninguno: se ve resuelto, y con
    eso se compra y se descuenta, así que faltarían o sobrarían frascos sin que nadie se entere
    hasta el piso.
  · **Una decisión, tres consumidores.** Entra por el helper canónico de composición, así que la
    misma decisión llega a lo que se compra, lo que se descuenta y lo que el operario alista. Si
    se escribiera en un solo lado, vuelve el problema de comprar una cosa y descontar otra.
"""
import pytest

TEST_PASSWORD = "TestPass123"
PROD = "REPTEST SUERO LOTE"


@pytest.fixture
def planta(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "smurillo", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM produccion_envase_reparto WHERE produccion_id IN "
                  " (SELECT id FROM produccion_programada WHERE producto LIKE 'REPTEST%')")
        c.execute("DELETE FROM produccion_programada WHERE producto LIKE 'REPTEST%'")
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'REPTEST%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'RP-%'")
        conn.commit()


def _sembrar(app):
    from datetime import datetime, timedelta
    f = (datetime.utcnow() + timedelta(days=25)).date().isoformat()
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        for cod, desc in (('RP-HABITUAL', 'Frasco 30 ml habitual'),
                          ('RP-ALTERNO', 'Frasco 30 ml alterno'),
                          ('RP-TAPA', 'Tapa 30 ml')):
            # `stock_actual` explícito en 0: el CREATE TABLE tiene DEFAULT 2000 (M100).
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, "
                      " estado) VALUES (?,?,'Envase',0,'Activo')", (cod, desc))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, activo) "
                  " VALUES (?,'V30','30ml',30,'RP-HABITUAL',1)", (PROD,))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?,?,?,'pendiente','eos_plan')", (PROD, f, 3.0))
        conn.commit()
        return c.lastrowid


def _total(planta, pid):
    return planta.get('/api/planta/produccion/%d/reparto-envases' % pid).get_json()


def test_el_reparto_que_no_cierra_se_RECHAZA(app, planta):
    """Uno que no cuadra se ve resuelto, y con eso se compra y se descuenta."""
    _limpiar(app); pid = _sembrar(app)
    d = _total(planta, pid)
    total = d['unidades_totales']
    assert total > 10, 'el lote no rinde nada: el test no mide lo que dice'
    r = planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                    json={'reparto': [{'envase_codigo': 'RP-HABITUAL', 'unidades': 10}]},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 422, 'aceptó un reparto que no cierra'
    j = r.get_json()
    assert j['codigo'] == 'NO_CIERRA'
    assert j['lote_rinde'] and j['reparte'] == 10 and j.get('diferencia') is not None, \
        'no dijo cuánto falta: obliga a adivinar'


def test_reparte_70_30_y_queda_FIJADO(app, planta):
    """El caso de Sebastián, punta a punta."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    a = round(total * 0.7)
    b = round(total - a)
    r = planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                    json={'reparto': [{'envase_codigo': 'RP-HABITUAL', 'unidades': a},
                                      {'envase_codigo': 'RP-ALTERNO', 'unidades': b}],
                          'motivo': 'no alcanza el habitual'},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    d = _total(planta, pid)
    assert d['reparto_decidido'] is True
    cods = sorted((v['envase_codigo'] or '').upper() for v in d['variantes'])
    assert cods == ['RP-ALTERNO', 'RP-HABITUAL'], 'el reparto no llegó a la composición: %s' % cods
    uds = {(v['envase_codigo'] or '').upper(): v['unidades_estimadas'] for v in d['variantes']}
    assert abs(uds['RP-HABITUAL'] - a) < 0.01 and abs(uds['RP-ALTERNO'] - b) < 0.01


def test_la_decision_llega_a_la_COLA_de_marcacion(app, planta):
    """Una decisión, tres consumidores. Si sólo se guardara, se compraría el frasco viejo."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                json={'reparto': [{'envase_codigo': 'RP-HABITUAL', 'unidades': round(total * 0.7)},
                                  {'envase_codigo': 'RP-ALTERNO',
                                   'unidades': round(total - round(total * 0.7))}]},
                headers={'Origin': 'http://localhost'})
    filas = [x for x in (planta.get('/api/programacion/serigrafia-cola').get_json().get('items')
                         or []) if x.get('producto') == PROD]
    cods = sorted((x.get('envase_codigo') or '').upper() for x in filas)
    assert 'RP-ALTERNO' in cods, \
        'la cola de trabajo no vio la decisión: se pediría el frasco viejo · %s' % cods


def test_no_deja_el_mismo_envase_dos_veces(app, planta):
    """Dos renglones del mismo frasco son dos órdenes del mismo frasco."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    r = planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                    json={'reparto': [{'envase_codigo': 'RP-HABITUAL', 'unidades': total / 2},
                                      {'envase_codigo': 'RP-HABITUAL', 'unidades': total / 2}]},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 400 and r.get_json()['codigo'] == 'ENVASE_REPETIDO'


def test_un_codigo_inexistente_se_RECHAZA(app, planta):
    """Una decisión apuntando al vacío no se puede comprar ni descontar, y nadie lo vería hasta
    que falte el frasco."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    r = planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                    json={'reparto': [{'envase_codigo': 'RP-NO-EXISTE', 'unidades': total}]},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 400 and r.get_json()['codigo'] == 'CODIGO_INEXISTENTE'


def test_un_lote_YA_DESCONTADO_no_se_re_reparte(app, planta):
    """El kardex ya salió con los frascos viejos: cambiar la decisión después no devuelve nada y
    dejaría la compra apuntando a un frasco y el kardex a otro."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("UPDATE produccion_programada SET inventario_descontado_at=? "
                              " WHERE id=?", ('2026-08-01 10:00:00', pid))
        conn.commit()
    r = planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                    json={'reparto': [{'envase_codigo': 'RP-ALTERNO', 'unidades': total}]},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 409 and r.get_json()['codigo'] == 'YA_DESCONTADO'


def test_quitar_el_reparto_vuelve_a_lo_automatico(app, planta):
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                json={'reparto': [{'envase_codigo': 'RP-ALTERNO', 'unidades': total}]},
                headers={'Origin': 'http://localhost'})
    assert _total(planta, pid)['reparto_decidido'] is True
    planta.post('/api/planta/produccion/%d/reparto-envases' % pid, json={'reparto': []},
                headers={'Origin': 'http://localhost'})
    d = _total(planta, pid)
    assert d['reparto_decidido'] is False
    assert (d['variantes'][0]['envase_codigo'] or '').upper() == 'RP-HABITUAL', \
        'no volvió al frasco de la presentación'


def test_la_decision_queda_auditada(app, planta):
    """Cambiar con qué frasco se envasa decide una compra: sin rastro no se puede revisar."""
    _limpiar(app); pid = _sembrar(app)
    total = _total(planta, pid)['unidades_totales']
    planta.post('/api/planta/produccion/%d/reparto-envases' % pid,
                json={'reparto': [{'envase_codigo': 'RP-ALTERNO', 'unidades': total}],
                      'motivo': 'no alcanza el habitual'},
                headers={'Origin': 'http://localhost'})
    with app.app_context():
        from database import get_db
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM audit_log WHERE accion='REPARTO_ENVASES_FIJAR' "
            "  AND registro_id=?", (str(pid),)).fetchone()
    assert n[0] >= 1, 'fijar el reparto no dejó rastro'


def test_la_pantalla_tiene_como_llegar_al_reparto(app, planta):
    """Dos veces hoy construí endpoints sin puerta. El guard mira el HTML REAL que se sirve:
    buscar el nombre en el fuente encontraría mi propio comentario (M121/M154)."""
    html = planta.get('/admin/marcacion-envases').get_data(as_text=True)
    assert 'abrirReparto(' in html, 'no hay botón para repartir'
    assert 'id="reparto-modal"' in html, 'el botón abre un modal que no existe'
    for fn in ('function abrirReparto', 'function guardarReparto', 'function sumaReparto',
               'function quitarReparto'):
        assert fn in html, 'el modal llama a algo que no está definido: %s' % fn
    assert '/reparto-envases' in html, 'la pantalla no apunta al endpoint'
