"""Los controles ESTÁNDAR son controles de verdad, no una tabla decorativa (29-jul).

Roadmap 🔴: *"Los MBR no tienen IPCs definidos, así que el legajo cae a los controles
estándar y muestra 'pendiente' con ✓ a la vez"*. Al medirlo contra el código el hueco era
más grande que el síntoma visual: **los dos gates de IPC miran sólo `ipc_specs` /
`ipc_resultados`**, así que todo lo que pasa por la vía estándar —que hoy es TODO, porque
ningún MBR define specs— quedaba fuera de control:

1. un estándar marcado **No cumple** (pH fuera de rango, olor rancio) NO abría desviación y
   NO bloqueaba la liberación → producto no conforme liberable;
2. `conforme=1` se aceptaba con el resultado VACÍO → la fila decía "pendiente" y "✓" a la
   vez (M5: el número que se muestra es el que decide), y una firma sobre un dato que no
   existe no es un registro;
3. el mismo hecho físico (pH fuera de spec) abría desviación por una vía y nada por la otra
   (M45: un control que vive en dos caminos y sólo uno lo aplica).
"""
from .conftest import TEST_PASSWORD, csrf_headers

LOTE = 'DEMO-IPCEST-1'      # sandbox: liberar sin e-firma · los gates regulatorios siguen
LOTE_REAL = 'ZZ-IPCEST-REAL'  # lote real: los DEMO saltean los gates a propósito


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _sembrar(app, estado='en_proceso', lote=LOTE):
    """Legajo limpio. Limpia ANTES (M103) y con nombre FIJO: idempotente entre
    corridas (`ebr_ejecuciones.lote` es UNIQUE · con nombres aleatorios la 3ª corrida
    del gate revienta con los datos de las anteriores)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()
        if f:
            cu.execute("DELETE FROM ipc_estandar_resultados WHERE ebr_id=?", (f[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        # Las desviaciones del lote se borran DESPUÉS de sus hijas y de quien las apunta:
        # `desviaciones_eventos` tiene FK y el resultado del IPC guarda `desviacion_id`
        # (foreign_keys=ON en toda conexión → borrar la madre primero revienta).
        _ds = [r[0] for r in cu.execute(
            "SELECT id FROM desviaciones WHERE lotes_afectados LIKE ?",
            ('%' + lote + '%',)).fetchall()]
        for _d in _ds:
            cu.execute("UPDATE ipc_estandar_resultados SET desviacion_id=NULL "
                       "WHERE desviacion_id=?", (_d,))
            cu.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (_d,))
            cu.execute("DELETE FROM desviaciones WHERE id=?", (_d,))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (1, 1, lote, lote, estado, 'fabricacion', 'sebastian',
             '2026-07-29T10:00:00', 1000, 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.commit()
    return eid


def _registrar(cli, eid, **body):
    return cli.post('/api/brd/ebr/%d/ipc-estandar' % eid, headers=_h(), json=body)


def _toggle(app, valor):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO app_settings (clave, valor) VALUES ('exigir_ipc_estandar', ?) "
            "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (valor,))
        conn.commit()


# ══ 1 · el agujero grande: un NO CUMPLE que no frenaba nada ═════════════════════

def test_estandar_no_conforme_BLOQUEA_la_liberacion(app, db_clean):
    """Nadie marca 'No cumple' por accidente: es una declaración de no conformidad.
    Liberar con eso encima es exactamente lo que no puede pasar (INVIMA Res. 2214)."""
    eid = _sembrar(app)
    cli = _login(app)
    r = _registrar(cli, eid, control_codigo='ph', valor_texto='9.8', conforme=False)
    assert r.status_code in (200, 201), r.data[:300]

    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET estado='completado' WHERE id=?", (eid,))
        conn.commit()

    r = cli.post('/api/brd/ebr/%d/liberar' % eid, headers=_h(), json={})
    assert r.status_code == 409, (
        'liberó un lote con un control estándar NO CONFORME (%s): %s'
        % (r.status_code, r.data[:300]))
    # Frena la desviación que el propio control abrió (primera línea) o el gate directo.
    assert (r.get_json() or {}).get('codigo') in (
        'DESVIACION_ABIERTA', 'IPC_ESTANDAR_NO_CONFORME'), r.data[:300]


def test_el_gate_bloquea_aunque_la_desviacion_NO_cruce_por_texto(app, db_clean):
    """El gate por desviación depende de que `lotes_afectados` matchee el lote como
    texto libre. Por eso el IPC del MBR tiene ADEMÁS un gate directo por ebr_id, y los
    estándar no lo tenían: si el texto no cruza, el lote salía igual. Acá se rompe el
    cruce textual a propósito para dejar sólo el gate directo en pie."""
    from database import get_db
    eid = _sembrar(app)
    cli = _login(app)
    r = _registrar(cli, eid, control_codigo='ph', valor_texto='9.8', conforme=False)
    assert r.status_code in (200, 201), r.data[:300]
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE desviaciones SET lotes_afectados='OTRO-LOTE' WHERE lotes_afectados LIKE ?",
            ('%' + LOTE + '%',))
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET estado='completado' WHERE id=?", (eid,))
        conn.commit()

    r = cli.post('/api/brd/ebr/%d/liberar' % eid, headers=_h(), json={})
    assert r.status_code == 409, (
        'sin el cruce textual de la desviación, el lote NO CONFORME salió: %s'
        % r.data[:300])
    assert (r.get_json() or {}).get('codigo') == 'IPC_ESTANDAR_NO_CONFORME', r.data[:300]


def test_resultado_sin_adjudicar_NO_se_libera(app, db_clean):
    """Valor anotado y nadie dijo si cumple: falta la firma de Calidad, igual que el
    cualitativo del MBR (que ya bloqueaba con conforme NULL)."""
    from database import get_db
    eid = _sembrar(app)
    cli = _login(app)
    r = _registrar(cli, eid, control_codigo='apariencia', valor_texto='grumos leves')
    assert r.status_code in (200, 201), r.data[:300]
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET estado='completado' WHERE id=?", (eid,))
        conn.commit()
    r = cli.post('/api/brd/ebr/%d/liberar' % eid, headers=_h(), json={})
    assert r.status_code == 409, r.data[:300]
    assert (r.get_json() or {}).get('codigo') == 'IPC_ESTANDAR_SIN_ADJUDICAR', r.data[:300]


def test_control_conforme_NO_frena_la_liberacion(app, db_clean):
    """Dientes del gate: con los controles en Cumple / No aplica, el lote sale.
    Un gate que bloquea siempre no es un control, es una traba."""
    from database import get_db
    eid = _sembrar(app)
    cli = _login(app)
    _registrar(cli, eid, control_codigo='ph', valor_texto='5.4', conforme=True)
    _registrar(cli, eid, control_codigo='olor', no_aplica=True)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET estado='completado' WHERE id=?", (eid,))
        conn.commit()
    r = cli.post('/api/brd/ebr/%d/liberar' % eid, headers=_h(), json={})
    assert r.status_code == 200, r.data[:300]


def test_estandar_no_conforme_abre_desviacion_fail_closed(app, db_clean):
    """El mismo hecho físico por las dos vías tiene que abrir desviación: si sólo la
    abre el camino del MBR, el gate de liberación (que mira desviaciones) no ve nada."""
    eid = _sembrar(app)
    r = _registrar(_login(app), eid, control_codigo='olor', valor_texto='rancio',
                   conforme=False)
    assert r.status_code in (200, 201), r.data[:300]
    j = r.get_json()
    assert j.get('desviacion'), 'un No-cumple sin desviación no deja rastro: %r' % j

    from database import get_db
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM desviaciones WHERE lotes_afectados LIKE ?",
            ('%' + LOTE + '%',)).fetchone()[0]
    assert n == 1, 'desviaciones creadas: %d' % n


# ══ 2 · "pendiente" y "✓" en la misma fila ══════════════════════════════════════

def test_cumple_sin_resultado_se_RECHAZA(app, db_clean):
    """Un control 'Cumple' con el resultado vacío mostraba 'pendiente' y '✓' a la vez.
    El arreglo va en el ORIGEN, no en la vista: sin dato no hay conformidad que firmar."""
    eid = _sembrar(app)
    r = _registrar(_login(app), eid, control_codigo='densidad', conforme=True)
    assert r.status_code == 400, (
        'aceptó "Cumple" sin resultado (%s) → la fila queda contradictoria' % r.status_code)


def test_no_cumple_sin_resultado_tambien_se_RECHAZA(app, db_clean):
    """Simétrico: un 'No cumple' sin el valor medido no sirve como evidencia de la
    no conformidad, y es la que abre desviación."""
    eid = _sembrar(app)
    r = _registrar(_login(app), eid, control_codigo='densidad', conforme=False)
    assert r.status_code == 400, r.data[:200]


def test_cumple_con_resultado_pasa(app, db_clean):
    """Dientes del guard anterior: con dato, entra."""
    eid = _sembrar(app)
    r = _registrar(_login(app), eid, control_codigo='densidad', valor_texto='0.916 g/mL',
                   conforme=True)
    assert r.status_code in (200, 201), r.data[:300]
    assert r.get_json().get('desviacion') is None, 'un Cumple no abre desviación'


def test_no_aplica_sigue_pasando_sin_valor(app, db_clean):
    """'No aplica' (conforme=2) es una respuesta completa en sí misma: no exige valor,
    no abre desviación y no bloquea (ya estaba así · no se toca)."""
    eid = _sembrar(app)
    r = _registrar(_login(app), eid, control_codigo='color', no_aplica=True)
    assert r.status_code in (200, 201), r.data[:300]
    assert r.get_json()['conforme'] == 2


# ══ 3 · exigir los 5 estándar · toggle default OFF = NO-OP TOTAL (M68) ══════════

def test_toggle_apagado_es_NO_OP_TOTAL(app, db_clean):
    """Con el toggle en 0 nada cambia para el piso: se puede completar sin registrar
    un solo control estándar. Un beta que igual bloquea en un caso es una traba
    fantasma esperando a aparecer."""
    _toggle(app, '0')
    eid = _sembrar(app, lote=LOTE_REAL)   # lote REAL: un DEMO saltea los gates por diseño
    r = _login(app).post('/api/brd/ebr/%d/completar' % eid, headers=_h(),
                         json={'cantidad_real_g': 950})
    assert r.status_code == 200, r.data[:300]


def test_toggle_encendido_exige_los_cinco(app, db_clean):
    """Prueba que el trinquete MUERDE (M104): encendido, completar sin los estándar
    devuelve 409 y dice CUÁLES faltan."""
    _toggle(app, '1')
    try:
        eid = _sembrar(app, lote=LOTE_REAL)
        r = _login(app).post('/api/brd/ebr/%d/completar' % eid, headers=_h(),
                             json={'cantidad_real_g': 950})
        assert r.status_code == 409, r.data[:300]
        j = r.get_json()
        assert j.get('codigo') == 'IPC_ESTANDAR_PENDIENTES'
        assert len(j.get('controles') or []) == 5, j
    finally:
        _toggle(app, '0')


def test_el_toggle_existe_en_seguridad_planta_y_lo_prende_admin(app, db_clean, admin_client):
    """Un control que sólo se puede prender editando la base no se prende nunca. Y el
    golden no abre páginas admin (M78), así que el render va en su propio test."""
    r = admin_client.get('/admin/seguridad-planta')
    assert r.status_code == 200
    body = r.data.decode('utf-8', 'replace')
    assert 'setIpcEstandar' in body, 'el botón del toggle no está en la página'

    r = admin_client.get('/api/admin/seguridad-planta')
    assert r.status_code == 200
    claves = [c.get('clave') for c in (r.get_json() or {}).get('controles', [])]
    assert 'exigir_ipc_estandar' in claves, claves

    r = admin_client.post('/api/admin/exigir-ipc-estandar', json={'activo': True})
    assert r.status_code == 200, r.data[:200]
    assert r.get_json()['activo'] is True
    from database import get_db
    with app.app_context():
        v = get_db().cursor().execute(
            "SELECT valor FROM app_settings WHERE clave='exigir_ipc_estandar'").fetchone()[0]
    assert str(v) == '1'
    admin_client.post('/api/admin/exigir-ipc-estandar', json={'activo': False})


def test_toggle_encendido_con_los_cinco_registrados_deja_completar(app, db_clean):
    """El otro lado del trinquete: registrados (con valor o 'No aplica'), pasa."""
    _toggle(app, '1')
    try:
        eid = _sembrar(app, lote=LOTE_REAL)
        cli = _login(app)
        _registrar(cli, eid, control_codigo='densidad', valor_texto='0.916', conforme=True)
        _registrar(cli, eid, control_codigo='ph', valor_texto='5.4', conforme=True)
        for cod in ('olor', 'color', 'apariencia'):
            _registrar(cli, eid, control_codigo=cod, no_aplica=True)
        r = cli.post('/api/brd/ebr/%d/completar' % eid, headers=_h(),
                     json={'cantidad_real_g': 950})
        assert r.status_code == 200, r.data[:300]
    finally:
        _toggle(app, '0')
