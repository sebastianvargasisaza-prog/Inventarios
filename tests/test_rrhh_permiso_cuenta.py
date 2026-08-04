"""Un permiso aprobado tiene que llegar a los números de Recursos Humanos (4-ago).

El mismo hecho -- alguien no va a trabajar tal día -- se registraba en DOS tablas: la novedad que
cargan Daniela o Luz (`notificaciones_empleados`) y la ausencia que RRHH cuenta (`ausencias`).
El indicador de ausentismo lee SOLO la segunda.

O sea que desde que construimos las novedades, un permiso aprobado **no contaba en ningún lado**:
RRHH mostraba el ausentismo como si nadie hubiera faltado y su pestaña de Ausencias no listaba
ninguno. Es M37 exacto -- dos tablas para el mismo hecho y un cálculo que lee una sola.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZRH'


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ausencias WHERE COALESCE(observaciones,'') LIKE ?",
                    ('%' + MARCA + '%',))
        cur.execute("DELETE FROM ausencias WHERE empleado_id IN "
                    "(SELECT id FROM empleados WHERE codigo LIKE ?)", (MARCA + '%',))
        cur.execute("DELETE FROM notificaciones_empleados WHERE asunto LIKE ?",
                    ('%' + MARCA + '%',))
        cur.execute("DELETE FROM empleados WHERE codigo LIKE ?", (MARCA + '%',))
        conn.commit()


def _empleado(app, cod=MARCA + '1'):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO empleados (codigo, nombre, apellido, estado, cargo, empresa) "
                    "VALUES (?,?,?,'Activo','Operaria','Animus')", (cod, 'ZzMaria', 'Lopez'))
        eid = cur.lastrowid
        conn.commit()
    return cod, eid


def _novedad(cli, cod, **kw):
    body = {'empleado_username': cod, 'empleado_nombre': 'ZzMaria Lopez', 'tipo': 'permiso',
            'asunto': MARCA + ' permiso del jueves', 'fecha_inicio': '2026-08-06'}
    body.update(kw)
    r = cli.post('/api/bienestar/notificaciones', json=body, headers=csrf_headers())
    assert r.status_code == 201, r.data[:250]
    return r.get_json()['id']


def _ausencias_de(app, eid):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT tipo, fecha_inicio, dias, estado, observaciones FROM ausencias "
            "WHERE empleado_id=?", (eid,)).fetchall()


# ── EL PUENTE ────────────────────────────────────────────────────────────────

def test_un_permiso_APROBADO_cuenta_como_ausencia(app, db_clean):
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod)
    assert not _ausencias_de(app, eid), 'contó antes de que Recursos Humanos la aprobara'
    r = c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
               json={'estado': 'aprobada'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    aus = _ausencias_de(app, eid)
    assert aus, 'el permiso aprobado no llegó a Recursos Humanos'
    assert aus[0][0] == 'Permiso' and aus[0][3] == 'Aprobada'
    assert aus[0][1] == '2026-08-06'


def test_una_novedad_PENDIENTE_todavia_no_es_una_ausencia(app, db_clean):
    """Contarla antes de aprobarla inflaría el indicador con cosas que quizá se rechacen."""
    _limpiar(app)
    cod, eid = _empleado(app)
    _novedad(_cli(app), cod)
    assert not _ausencias_de(app, eid)


def test_aprobar_DOS_veces_no_duplica_el_dia(app, db_clean):
    """Idempotente por marcador · si no, el ausentismo se dispararía con un doble click."""
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod)
    for _ in range(2):
        c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
               json={'estado': 'aprobada'}, headers=csrf_headers())
    assert len(_ausencias_de(app, eid)) == 1


def test_rechazar_despues_de_aprobar_deja_de_contar_pero_NO_borra(app, db_clean):
    """El rastro de que existió es lo que permite entender el número de un mes pasado."""
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod)
    c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
           json={'estado': 'aprobada'}, headers=csrf_headers())
    c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
           json={'estado': 'rechazada'}, headers=csrf_headers())
    aus = _ausencias_de(app, eid)
    assert aus, 'borró la ausencia en vez de dejar de contarla'
    assert aus[0][3] == 'Rechazada'


def test_los_dias_salen_del_rango_de_fechas(app, db_clean):
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod, tipo='enfermedad', fecha_inicio='2026-08-10',
                   fecha_fin='2026-08-12')
    c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
           json={'estado': 'aprobada'}, headers=csrf_headers())
    aus = _ausencias_de(app, eid)
    assert aus[0][0] == 'Incapacidad'
    assert aus[0][2] == 3, 'del 10 al 12 son 3 días, no %s' % aus[0][2]


def test_una_novedad_ADMINISTRATIVA_no_es_una_ausencia(app, db_clean):
    """Con dientes: si toda novedad contara como falta, el ausentismo mediría cualquier cosa."""
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod, tipo='otro', asunto=MARCA + ' se dañó la impresora')
    c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
           json={'estado': 'aprobada'}, headers=csrf_headers())
    assert not _ausencias_de(app, eid), 'contó una novedad administrativa como falta'


def test_si_la_persona_no_esta_en_el_maestro_NO_inventa_un_empleado(app, db_clean):
    """Colgar la ausencia de un id cualquiera ensuciaría el legajo de otra persona · queda
    declarado en el log para que se corrija el maestro (M100)."""
    _limpiar(app)
    c = _cli(app)
    nid = _novedad(c, 'zz-no-existe-en-el-maestro')
    r = c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
               json={'estado': 'aprobada'}, headers=csrf_headers())
    assert r.status_code == 200, 'la aprobación no puede caerse porque falte el maestro'
    from database import get_db
    with app.app_context():
        n = get_db().execute(
            "SELECT COUNT(*) FROM ausencias WHERE COALESCE(observaciones,'') LIKE ?",
            ('%[novedad#' + str(nid) + ']%',)).fetchone()[0]
    assert n == 0


def test_el_ausentismo_de_RRHH_ya_ve_el_permiso(app, db_clean):
    """El número que Recursos Humanos mira tiene que moverse · es el punto de todo esto."""
    _limpiar(app)
    cod, eid = _empleado(app)
    c = _cli(app)
    nid = _novedad(c, cod, fecha_inicio='2026-08-06', fecha_fin='2026-08-06')
    c.post('/api/bienestar/notificaciones/%d/resolver' % nid,
           json={'estado': 'aprobada'}, headers=csrf_headers())
    from database import get_db
    with app.app_context():
        d = get_db().execute(
            "SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE estado='Aprobada' "
            "AND fecha_inicio LIKE '2026-08%'").fetchone()[0]
    assert d >= 1, 'el permiso aprobado no suma al ausentismo del mes'


# ── Y LLEGA AL CEO ───────────────────────────────────────────────────────────

def test_un_permiso_sin_resolver_llega_a_la_cola_del_CEO(app, db_clean):
    """Sebastián: *"que vaya trayendo todo, permisos y cosas así"*. Un permiso pedido para
    mañana que nadie aprobó no es un pendiente administrativo: es alguien que no sabe si puede
    faltar."""
    _limpiar(app)
    cod, _ = _empleado(app)
    c = _cli(app)
    from tz_colombia import hoy_colombia
    _novedad(c, cod, fecha_inicio=hoy_colombia().isoformat())
    d = c.get('/api/centro/decisiones').get_json()
    fila = [x for x in d['decisiones'] if 'Permisos y novedades' in x.get('titulo', '')]
    assert fila, 'el permiso pendiente no llegó al Centro de Mando'
    assert fila[0]['accion'] == '/rrhh'
    assert 'hoy o mañana' in fila[0]['detalle'], 'no distingue lo que empieza ya'


def test_un_permiso_LEJANO_no_urge_al_CEO(app, db_clean):
    """Con dientes: la urgencia la da la FECHA, no la cantidad · si todo urgiera, la cola se
    volvería ruido (M129)."""
    _limpiar(app)
    cod, _ = _empleado(app)
    c = _cli(app)
    _novedad(c, cod, fecha_inicio='2026-12-24')
    d = c.get('/api/centro/decisiones').get_json()
    fila = [x for x in d['decisiones'] if 'Permisos y novedades' in x.get('titulo', '')]
    if fila:
        assert fila[0]['nivel'] == 'info', 'un permiso de diciembre no es para atender hoy'
