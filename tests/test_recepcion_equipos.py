"""Recepción de EQUIPOS · el equipo que llega no se puede usar hasta que lo califiquen (30-jul).

Sebastián: *"los equipos aún no los tengo, llegó, pero necesito que Compras los recepcione, o Luz
en Espagiria, ¿cómo hacemos?"* → **Catalina y Luz registran la llegada; Aseguramiento califica**.

Un equipo tiene la misma forma que una materia prima: llega, se registra con lo que trae (serial,
marca, factura, cuánto costó) y **no entra a producción hasta que alguien lo aprueba**. Ahí la
cuarentena se llama CALIFICACIÓN (IQ/OQ/PQ) y no la hace quien recibió.

Lo que este archivo fija:
  · quién puede registrar (y quién no · un permiso sin probar el borde es una puerta abierta);
  · el equipo nace PENDIENTE y **no aparece en la lista de equipos del área** hasta calificarse;
  · calificar es de Aseguramiento, deja EVENTO en la hoja de vida y no se puede hacer dos veces;
  · un serial no se le puede pegar a N equipos, ni repetirse;
  · la pestaña existe DENTRO de /recepcion, con sus funciones e ids propios.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

NOMBRE = 'ZZTEST Balanza de prueba'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        filas = cur.fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    for (cod,) in _sql("SELECT codigo FROM equipos_planta WHERE nombre LIKE 'ZZTEST%'"):
        _sql("DELETE FROM equipos_eventos WHERE equipo_codigo=?", (cod,))
    _sql("DELETE FROM equipos_planta WHERE nombre LIKE 'ZZTEST%'")


def _registrar(cli, **extra):
    body = {'nombre': NOMBRE, 'tipo_prefijo': 'BL', 'area_codigo': 'FAB1',
            'ubicacion': 'Fabricación 1', 'empresa': 'ESPAGIRIA', 'marca': 'AXIS',
            'modelo': 'ACN-220', 'proveedor': 'ZZ Proveedor', 'factura': 'FV-9001',
            'valor_cop': 4500000, 'fecha_ingreso': '2026-07-30'}
    body.update(extra)
    return cli.post('/api/recepcion/equipos', headers=_h(), json=body)


# ══ registrar la llegada ════════════════════════════════════════════════════════

def test_el_equipo_nace_PENDIENTE_de_calificacion(app, db_clean):
    """Lo esencial: llegó, quedó registrado con su factura y su valor, y NO se puede usar."""
    _limpiar()
    r = _registrar(_login(app), serial='SN-ZZ-001')
    assert r.status_code == 201, r.data[:400]
    j = r.get_json()
    cod = j['codigos'][0]
    assert j['estado'] == 'PENDIENTE'
    fila = _sql("SELECT estado_calificacion, estado_operacional, serial, factura, valor_cop, "
                "recibido_por, empresa FROM equipos_planta WHERE codigo=?", (cod,))[0]
    assert fila[0] == 'PENDIENTE', 'nació usable: se saltó la calificación'
    assert fila[1] == 'calibracion', fila
    assert fila[2] == 'SN-ZZ-001' and fila[3] == 'FV-9001', 'no guardó lo que trae el equipo'
    assert float(fila[4]) == 4500000, 'sin el valor no se puede valorizar el activo'
    assert fila[5] == 'sebastian', 'no quedó quién recibió'


def test_el_codigo_continua_la_numeracion_que_ya_existe(app, db_clean):
    """`BL-PRD-00N`: el prefijo sale del tipo y la zona de PRD/COC, como los 102 que ya están."""
    _limpiar()
    cli = _login(app)
    r = _registrar(cli, cantidad=3)
    assert r.status_code == 201, r.data[:400]
    cods = r.get_json()['codigos']
    assert len(cods) == 3 and len(set(cods)) == 3, 'códigos repetidos: %r' % cods
    for cod in cods:
        assert cod.startswith('BL-PRD-'), cod
    # y en calidad la zona es COC, no PRD
    r2 = _registrar(cli, area_codigo='CC', tipo_prefijo='PR', nombre=NOMBRE + ' calidad')
    assert r2.get_json()['codigos'][0].startswith('PR-COC-'), r2.get_json()


def test_un_serial_no_se_le_puede_pegar_a_varios_equipos(app, db_clean):
    """El serial identifica UNA máquina. Repetirlo en N inventa un dato que después nadie
    puede desarmar sin saber cuál era cuál."""
    _limpiar()
    cli = _login(app)
    r = _registrar(cli, cantidad=2, serial='SN-ZZ-DUP')
    assert r.status_code == 400, r.data[:300]
    r = _registrar(cli, serial='SN-ZZ-UNICO')
    assert r.status_code == 201, r.data[:300]
    r = _registrar(cli, serial='SN-ZZ-UNICO')
    assert r.status_code == 409, 'aceptó dos equipos con el mismo serial: %s' % r.data[:300]


def test_solo_compras_luz_o_admin_registran(app, db_clean):
    """Con dientes en los dos sentidos: si nadie queda afuera, el permiso no es un control."""
    _limpiar()
    r = _registrar(_login(app, 'catalina'))
    assert r.status_code == 201, 'Catalina (Compras) debería poder: %s' % r.data[:300]
    r = _registrar(_login(app, 'luz'), nombre=NOMBRE + ' espagiria')
    assert r.status_code == 201, 'Luz (Espagiria) debería poder: %s' % r.data[:300]
    r = _registrar(_login(app, 'mayerlin'), nombre=NOMBRE + ' planta')
    assert r.status_code == 403, 'un operario de planta no registra activos: %s' % r.data[:300]


# ══ la calificación es de Aseguramiento ═════════════════════════════════════════

def test_calificar_lo_hace_ASEGURAMIENTO_y_deja_evento(app, db_clean):
    _limpiar()
    cod = _registrar(_login(app)).get_json()['codigos'][0]
    r = _login(app, 'miguel').post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                                   json={'resultado': 'CALIFICADO', 'iq': True, 'oq': True,
                                         'pq': True, 'notas': 'ZZTEST calificación de recepción'})
    assert r.status_code == 200, r.data[:400]
    fila = _sql("SELECT estado_calificacion, estado_operacional, calificado_por "
                "FROM equipos_planta WHERE codigo=?", (cod,))[0]
    assert fila[0] == 'CALIFICADO' and fila[1] == 'operativo', fila
    assert fila[2] == 'miguel', 'no quedó quién calificó'
    ev = _sql("SELECT tipo_evento, resultado FROM equipos_eventos WHERE equipo_codigo=?", (cod,))
    assert ev and ev[0][0] == 'validacion', (
        'sin evento en la hoja de vida nadie puede demostrar que se calificó antes de usarlo: %r' % ev)


def test_no_se_califica_dos_veces(app, db_clean):
    """Dos clicks (o dos workers) no pueden dejar el equipo en dos estados distintos."""
    _limpiar()
    cod = _registrar(_login(app)).get_json()['codigos'][0]
    cli = _login(app, 'miguel')
    r1 = cli.post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                  json={'resultado': 'CALIFICADO'})
    assert r1.status_code == 200, r1.data[:300]
    r2 = cli.post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                  json={'resultado': 'RECHAZADO', 'notas': 'ZZTEST segundo intento'})
    assert r2.status_code == 409, 'se recalificó un equipo ya calificado: %s' % r2.data[:300]


def test_rechazar_exige_motivo_y_saca_el_equipo_de_operacion(app, db_clean):
    _limpiar()
    cod = _registrar(_login(app)).get_json()['codigos'][0]
    cli = _login(app, 'miguel')
    r = cli.post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                 json={'resultado': 'RECHAZADO'})
    assert r.status_code == 400, 'rechazó sin motivo: el registro no explicaría nada'
    r = cli.post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                 json={'resultado': 'RECHAZADO', 'notas': 'ZZTEST llegó golpeado'})
    assert r.status_code == 200, r.data[:300]
    fila = _sql("SELECT estado_calificacion, estado_operacional, activo FROM equipos_planta "
                "WHERE codigo=?", (cod,))[0]
    assert fila[0] == 'RECHAZADO' and fila[1] == 'baja'
    assert int(fila[2]) == 1, 'un equipo rechazado NO se borra: queda registrado (GMP)'


def test_el_que_recibe_no_califica(app, db_clean):
    """Misma separación que rige los controles en proceso: recibir y aprobar son dos actos."""
    _limpiar()
    cod = _registrar(_login(app, 'catalina')).get_json()['codigos'][0]
    r = _login(app, 'catalina').post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                                     json={'resultado': 'CALIFICADO'})
    assert r.status_code == 403, 'quien recibió pudo aprobar su propia recepción: %s' % r.data[:300]


# ══ un equipo sin calificar NO está disponible para fabricar ════════════════════

def test_pendiente_no_aparece_entre_los_equipos_del_area(app, db_clean):
    """Es el punto de todo: mientras esté pendiente, producción no lo puede elegir."""
    _limpiar()
    cod = _registrar(_login(app), area_codigo='FAB1').get_json()['codigos'][0]
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _equipos_de_area
        c = get_db().cursor()
        antes = [e['codigo'] for e in _equipos_de_area(c, 'FAB1')]
        assert cod not in antes, 'un equipo sin calificar aparece como usable: %r' % antes[:6]
    _login(app, 'miguel').post('/api/calidad/equipos/%s/calificar' % cod, headers=_h(),
                               json={'resultado': 'CALIFICADO'})
    with app.app_context():
        from blueprints.programacion import _equipos_de_area
        despues = [e['codigo'] for e in _equipos_de_area(get_db().cursor(), 'FAB1')]
    assert cod in despues, 'calificado y sigue sin aparecer: la calificación no sirvió de nada'


def test_los_equipos_que_YA_estaban_no_se_tocan(app, db_clean):
    """La migración es aditiva: los 102 que llevan años en uso quedan en NO_APLICA y siguen
    saliendo igual. Inventarles una calificación que nadie hizo sería fabricar historia."""
    _sql("DELETE FROM equipos_planta WHERE codigo='ZZ-VIEJO-001'")
    _sql("INSERT INTO equipos_planta (codigo,nombre,area_codigo,tipo,activo) "
         "VALUES ('ZZ-VIEJO-001','ZZTEST equipo viejo','FAB2','otro',1)")
    est = _sql("SELECT COALESCE(estado_calificacion,'') FROM equipos_planta "
               "WHERE codigo='ZZ-VIEJO-001'")[0][0]
    assert est in ('NO_APLICA', ''), 'el default cambió y le inventó un estado: %r' % est
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _equipos_de_area
        cods = [e['codigo'] for e in _equipos_de_area(get_db().cursor(), 'FAB2')]
    assert 'ZZ-VIEJO-001' in cods, 'el filtro nuevo escondió equipos que sí se usan'


# ══ la pantalla ═════════════════════════════════════════════════════════════════

def test_la_pestana_vive_dentro_de_recepcion(app, db_clean):
    """No como página aparte: el punto de entrada lo define el TIPO de cosa que llega."""
    body = _login(app).get('/recepcion').data.decode('utf-8', 'replace')
    assert 'rt-btn-eq' in body and 'id="rt-eq"' in body, 'no quedó la pestaña Equipos'
    assert '__PANEL_EQUIPOS__' not in body, 'el placeholder no se reemplazó'
    assert 'function eqpGuardar' in body, 'el panel no se inyectó'
    # ninguna función del panel puede pisar una de la página que lo hospeda
    for fn in ('eqpEsc', 'eqpGuardar', 'eqpCargar', 'eqpPintar'):
        assert body.count('function ' + fn + '(') == 1, 'función %s duplicada' % fn


def test_el_rotulo_del_equipo_avisa_que_no_se_puede_usar(app, db_clean):
    _limpiar()
    cod = _registrar(_login(app)).get_json()['codigos'][0]
    r = _login(app).get('/rotulos-equipo?cods=' + cod)
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert cod in body and 'JsBarcode' in body, 'el rótulo salió sin código de barras'
    assert 'NO USAR' in body, 'el rótulo no avisa que el equipo todavía no está calificado'
