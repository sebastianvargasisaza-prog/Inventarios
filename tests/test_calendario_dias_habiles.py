"""El calendario NO acepta lotes en fin de semana ni en festivo, por NINGÚN camino (25-jul).

Sebastián: "de lunes a viernes en días no festivos · aquí todo debe ser perfecto".

Hay TRES caminos que ponen o mueven una fecha en el calendario y sólo dos validaban:

    ✅ POST /api/plan/programar                  (validaba L-V + festivo, con override)
    ✅ POST /api/plan/proximas/<id>/reprogramar  (arrastrar · validaba, con override)
    ❌ POST /api/plan/programar-manual           (el ➕ del calendario · NO validaba NADA)

El ➕ es justamente el camino que se usa a diario desde la vista de calendario, así que se podía
dejar un lote en sábado o en un festivo sin que la app dijera una palabra. Estos tests fijan que
los tres se comporten igual: rechazan con 422 y permiten forzar explícitamente.
"""
from datetime import date

from .conftest import TEST_PASSWORD, csrf_headers

# Fechas ancla verificadas contra el calendario colombiano real:
SABADO = '2026-07-11'
DOMINGO = '2026-07-12'
FESTIVO_LUNES = '2026-07-20'    # Independencia (fijo)
FESTIVO_VIERNES = '2026-08-07'  # Batalla de Boyacá (fijo)
HABIL_MARTES = '2026-07-07'
HABIL_JUEVES = '2026-07-09'

PROD = 'ZZ CAL DIAS HABILES'


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        try:
            conn.commit()
        except Exception:
            pass


def _programar_manual(c, fecha, forzar=False):
    body = {'producto': PROD, 'fecha': fecha, 'kg': 10}
    if forzar:
        body['skip_validacion_dia'] = True
    return c.post('/api/plan/programar-manual', json=body)


def test_sanity_las_fechas_ancla_son_lo_que_digo(app):
    """Si el calendario de festivos cambiara, estos tests deben avisar en vez de mentir."""
    from blueprints.plan import es_festivo_colombia
    assert date.fromisoformat(SABADO).weekday() == 5
    assert date.fromisoformat(DOMINGO).weekday() == 6
    assert es_festivo_colombia(date.fromisoformat(FESTIVO_LUNES))
    assert es_festivo_colombia(date.fromisoformat(FESTIVO_VIERNES))
    for h in (HABIL_MARTES, HABIL_JUEVES):
        d = date.fromisoformat(h)
        assert d.weekday() < 5 and not es_festivo_colombia(d)


def test_boton_mas_del_calendario_rechaza_fin_de_semana(app):
    c = _login(app)
    _limpiar(app)
    try:
        for f in (SABADO, DOMINGO):
            r = _programar_manual(c, f)
            assert r.status_code == 422, (f, r.status_code, r.get_data(as_text=True)[:200])
            d = r.get_json()
            assert d.get('codigo') == 'DIA_NO_HABIL', d
            assert d.get('puede_forzar') is True, 'debe ofrecer forzar, no ser un muro'
    finally:
        _limpiar(app)


def test_boton_mas_del_calendario_rechaza_festivo(app):
    c = _login(app)
    _limpiar(app)
    try:
        for f in (FESTIVO_LUNES, FESTIVO_VIERNES):
            r = _programar_manual(c, f)
            assert r.status_code == 422, (f, r.status_code, r.get_data(as_text=True)[:200])
            assert r.get_json().get('codigo') == 'DIA_FESTIVO', r.get_json()
    finally:
        _limpiar(app)


def test_se_puede_forzar_a_proposito(app):
    """Forzar sigue siendo posible (demos, jornada especial) pero EXPLÍCITO, no por descuido."""
    c = _login(app)
    _limpiar(app)
    try:
        r = _programar_manual(c, FESTIVO_LUNES, forzar=True)
        assert r.status_code == 200, r.get_data(as_text=True)[:200]
        with app.app_context():
            from database import get_db
            n = get_db().execute(
                "SELECT COUNT(*) FROM produccion_programada WHERE producto=? AND "
                "substr(fecha_programada,1,10)=?", (PROD, FESTIVO_LUNES)).fetchone()[0]
            assert n == 1, 'forzado explícito debe entrar'
    finally:
        _limpiar(app)


def test_martes_y_jueves_se_aceptan_sin_forzar(app):
    """La regla es L-V, no L/M/V: un martes o jueves entra normal."""
    c = _login(app)
    _limpiar(app)
    try:
        for f in (HABIL_MARTES, HABIL_JUEVES):
            r = _programar_manual(c, f)
            assert r.status_code == 200, (f, r.get_data(as_text=True)[:200])
    finally:
        _limpiar(app)


def test_los_tres_caminos_aplican_LA_MISMA_regla(app):
    """Un martes se acepta y un festivo se rechaza en los tres endpoints que fijan fecha.

    Es la incoherencia que motivó todo: el calendario aceptaba un día que los generadores
    nunca elegían, y el ➕ aceptaba días que sus dos hermanos rechazaban.
    """
    c = _login(app)
    _limpiar(app)
    try:
        # 1) ➕ del calendario
        assert _programar_manual(c, HABIL_MARTES).status_code == 200
        assert _programar_manual(c, FESTIVO_LUNES).status_code == 422

        # 2) arrastrar (reprogramar) el lote recién creado
        with app.app_context():
            from database import get_db
            pid = get_db().execute(
                "SELECT id FROM produccion_programada WHERE producto=? ORDER BY id DESC LIMIT 1",
                (PROD,)).fetchone()[0]
        r_ok = c.post('/api/plan/proximas/%d/reprogramar' % pid, json={'nueva_fecha': HABIL_JUEVES})
        assert r_ok.status_code == 200, r_ok.get_data(as_text=True)[:200]
        r_no = c.post('/api/plan/proximas/%d/reprogramar' % pid, json={'nueva_fecha': FESTIVO_VIERNES})
        assert r_no.status_code == 422, r_no.get_data(as_text=True)[:200]

        # 3) el helper canónico que usan los generadores automáticos
        import blueprints.auto_plan as ap
        assert ap._next_dia_produccion(date.fromisoformat(HABIL_MARTES)) == date.fromisoformat(HABIL_MARTES)
        assert ap._next_dia_produccion(date.fromisoformat(FESTIVO_LUNES)) != date.fromisoformat(FESTIVO_LUNES)
    finally:
        _limpiar(app)
