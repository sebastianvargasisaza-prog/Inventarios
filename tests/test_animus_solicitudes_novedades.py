"""El módulo de Daniela cerrado: pedir cosas y registrar novedades del equipo (3-ago).

Sebastián: *"que ese módulo de ÁNIMUS Daniela tenga una pestaña Solicitudes como el módulo,
donde pueda solicitar cosas, y le diga el estado autorizada pagada en tránsito, y allí mismo
haga la recepción -- creo que eso cerraría su módulo. También, como ella es la encargada de los
empleados de ÁNIMUS, debería tener algo para novedades internas, permisos, cosas
administrativas, para notificar a Recursos Humanos y Gerencia y que vaya quedando la
trazabilidad"*.

Las dos se apoyan en flujos que YA existían, así que lo que estos tests fijan no es la
maquinaria sino las **tres costuras** donde se rompía:

1. El aviso a Recursos Humanos se GUARDABA en una columna y nunca se enviaba. Guardar a quién
   hay que avisar no es avisar (M118), y una bandeja que nunca suena se ve igual que una al día
   (M127) -- por eso el hueco era invisible.
2. El destinatario por defecto era `luis_enrique`, **dado de baja** (mig 375).
3. Quien registraba la novedad de otro no la volvía a ver nunca: el filtro de la bandeja es por
   empleado, así que la de Mayerlin no aparecía para Daniela.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZDAN'


def _cli(app, quien='daniela'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pude loguear a %s' % quien
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida y en PG persiste."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM notificaciones_empleados WHERE asunto LIKE ?", ('%' + MARCA + '%',))
        cur.execute("DELETE FROM notificaciones_app WHERE titulo LIKE ?", ('%' + MARCA + '%',))
        cur.execute("DELETE FROM solicitudes_compra_items WHERE numero IN "
                    "(SELECT numero FROM solicitudes_compra WHERE observaciones LIKE ?)",
                    ('%' + MARCA + '%',))
        cur.execute("DELETE FROM solicitudes_compra WHERE observaciones LIKE ?", ('%' + MARCA + '%',))
        conn.commit()


def _html_animus():
    """El HTML se extrae del FUENTE, no se importa: el módulo no exporta un `HTML` y además
    así el test no depende de que el blueprint arranque (mismo patrón del test hermano)."""
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'animus_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError('no encontré el HTML de /animus')


# ── SOLICITUDES ──────────────────────────────────────────────────────────────

def test_daniela_pide_algo_y_le_queda_el_seguimiento(app, db_clean):
    """De punta a punta: pide, y su solicitud aparece con el paso del ciclo."""
    _limpiar(app)
    c = _cli(app)
    r = c.post('/api/solicitudes-compra', headers=csrf_headers(), json={
        'empresa': 'Animus', 'categoria': 'Consumibles', 'tipo': 'Compra', 'area': 'ANIMUS',
        'urgencia': 'Normal', 'solicitante': 'daniela',
        'observaciones': MARCA + ' papel burbuja · 3 rollo',
        'items': [{'codigo_mp': '', 'nombre_mp': 'Papel burbuja', 'cantidad_g': 3,
                   'unidad': 'rollo', 'justificacion': 'para despachos'}]})
    assert r.status_code in (200, 201), r.data[:250]
    numero = r.get_json().get('numero')
    assert numero and numero.startswith('SOL-')

    d = c.get('/api/solicitudes-compra/mis?estado=abiertas').get_json()
    mia = [x for x in d['solicitudes'] if x['numero'] == numero]
    assert mia, 'la solicitud no le aparece a quien la pidió'
    assert mia[0]['paso'] == 1 and not mia[0]['cerrado']
    assert mia[0]['paso_label'], 'sin etiqueta del paso no se sabe en qué va'


def test_el_ciclo_avanza_cuando_la_OC_avanza(app, db_clean):
    """Lo que ve Daniela sale del estado REAL de la OC · si la pantalla dedujera su propio
    estado, ella y Catalina verían cosas distintas del mismo pedido (M5)."""
    from database import get_db
    _limpiar(app)
    c = _cli(app)
    numero = c.post('/api/solicitudes-compra', headers=csrf_headers(), json={
        'empresa': 'Animus', 'categoria': 'Consumibles', 'area': 'ANIMUS',
        'solicitante': 'daniela', 'observaciones': MARCA + ' cinta',
        'items': [{'nombre_mp': 'Cinta', 'cantidad_g': 2, 'unidad': 'und'}]
    }).get_json()['numero']

    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, fecha, valor_total) "
                    "VALUES (?,?,?,date('now','-5 hours'),?)",
                    (MARCA + '-OC-1', 'Papelería Central', 'Pagada', 50000))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?",
                    (MARCA + '-OC-1', numero))
        conn.commit()

    x = [s for s in c.get('/api/solicitudes-compra/mis').get_json()['solicitudes']
         if s['numero'] == numero][0]
    assert x['paso'] == 4, 'una OC pagada debe leerse como en tránsito'
    assert x['puede_marcar_recibido'] is True, 'lo que va en camino tiene que poder recibirse'
    assert x['oc_proveedor'] == 'Papelería Central'

    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (MARCA + '-OC-1',))
        conn.commit()


def test_la_pantalla_tiene_la_pestana_de_solicitudes():
    html = _html_animus()
    assert "switchTab('solic')" in html and 'id="tab-solic"' in html
    assert 'id="sol-body"' in html and 'abrirSolicitud()' in html
    assert 'marcarRecibido(' in html, 'no se puede marcar que llegó'
    # el loader tiene que conocerla, o la pestaña abre vacía para siempre (M112)
    assert "name === 'solic'" in html


# ── NOVEDADES DEL EQUIPO ─────────────────────────────────────────────────────

def test_daniela_registra_la_novedad_de_alguien_de_su_equipo(app, db_clean):
    _limpiar(app)
    r = _cli(app).post('/api/bienestar/notificaciones', headers=csrf_headers(), json={
        'empleado_username': 'mayerlin', 'empleado_nombre': 'Mayerlin',
        'tipo': 'permiso', 'asunto': MARCA + ' permiso de dos horas',
        'fecha_inicio': '2026-08-05'})
    assert r.status_code == 201, r.data[:250]
    from database import get_db
    with app.app_context():
        f = get_db().execute(
            "SELECT empleado_username, registrado_por FROM notificaciones_empleados "
            "WHERE asunto LIKE ?", ('%' + MARCA + '%',)).fetchone()
    assert f[0] == 'mayerlin', 'quedó a nombre de quien la escribió, no del empleado'
    assert f[1] == 'daniela', 'sin quién la registró se pierde la trazabilidad'


def test_el_aviso_a_RRHH_y_gerencia_SALE_de_verdad(app, db_clean):
    """El endpoint guardaba `notificado_a` y nunca llamaba a la campana: la novedad quedaba
    registrada y nadie se enteraba."""
    _limpiar(app)
    r = _cli(app).post('/api/bienestar/notificaciones', headers=csrf_headers(), json={
        'empleado_username': 'mayerlin', 'empleado_nombre': 'Mayerlin',
        'tipo': 'permiso', 'asunto': MARCA + ' cita del jueves'})
    assert r.status_code == 201
    from database import get_db
    with app.app_context():
        avisados = [x[0] for x in get_db().execute(
            "SELECT destinatario FROM notificaciones_app WHERE tipo='novedad_personal' "
            "AND titulo LIKE ?", ('%' + MARCA + '%',)).fetchall()]
    assert avisados, 'nadie recibió el aviso de la novedad'
    assert 'sebastian' in avisados, 'gerencia no se enteró'
    assert any(x in avisados for x in ('gloria', 'mayra')), 'Recursos Humanos no se enteró'


def test_el_destinatario_por_defecto_no_incluye_a_alguien_dado_de_baja(app, db_clean):
    """Era 'sebastian,luis_enrique' escrito a mano · luis fue dado de baja (mig 375), así que
    la mitad de los avisos apuntaba a alguien que ya no trabaja."""
    _limpiar(app)
    r = _cli(app).post('/api/bienestar/notificaciones', headers=csrf_headers(), json={
        'empleado_username': 'mayerlin', 'tipo': 'permiso',
        'asunto': MARCA + ' revisar destinatarios'})
    dest = r.get_json()['notificado_a']
    assert 'luis_enrique' not in dest and 'luis' not in dest
    assert len(dest) >= 2, 'el aviso tiene que llegarle a más de una persona'


def test_quien_NO_maneja_personal_no_registra_a_nombre_de_otro(app, db_clean):
    """Si no, cualquiera podría pedir un permiso a nombre de un compañero."""
    _limpiar(app)
    r = _cli(app, 'laura').post('/api/bienestar/notificaciones', headers=csrf_headers(), json={
        'empleado_username': 'mayerlin', 'tipo': 'permiso',
        'asunto': MARCA + ' no deberia pasar'})
    assert r.status_code == 403, r.data[:250]


def test_la_novedad_que_registro_le_queda_a_la_vista(app, db_clean):
    """El filtro de la bandeja es por empleado, así que la de Mayerlin era invisible para
    Daniela · quien la registra tiene que poder seguirla."""
    _limpiar(app)
    c = _cli(app)
    c.post('/api/bienestar/notificaciones', headers=csrf_headers(), json={
        'empleado_username': 'mayerlin', 'empleado_nombre': 'Mayerlin',
        'tipo': 'permiso', 'asunto': MARCA + ' la tiene que ver'})
    filas = c.get('/api/bienestar/notificaciones').get_json()['notificaciones']
    mias = [x for x in filas if MARCA in (x.get('asunto') or '')]
    assert mias, 'la novedad que registró no le aparece'
    assert mias[0]['registrado_por'] == 'daniela'


def test_el_maestro_de_empleados_alimenta_el_desplegable(app, db_clean):
    """Escribir el nombre a mano crearía una persona distinta por cada forma de escribirlo y
    RRHH no podría agrupar nada (M115)."""
    r = _cli(app).get('/api/animus/empleados')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert d['ok'] is True and isinstance(d['empleados'], list)
    for e in d['empleados']:
        assert e['username'], 'un empleado sin llave no se puede usar para registrar la novedad'


def test_la_pantalla_tiene_la_pestana_de_novedades():
    html = _html_animus()
    assert "switchTab('novedades')" in html and 'id="tab-novedades"' in html
    assert 'id="nov-body"' in html and 'abrirNovedad()' in html
    for campo in ('nv-empleado', 'nv-tipo', 'nv-asunto', 'nv-desde', 'nv-adjunto'):
        assert 'id="%s"' % campo in html, campo
    assert "name === 'novedades'" in html


def test_la_pestana_NO_trae_las_solicitudes_de_planta(app, db_clean):
    """Sebastián (4-ago): "no entiendo por qué quedó esto acá, si no tiene nada que ver: es
    solicitudes de compras que Daniela haga para ÁNIMUS".

    La pestaña mostraba las SOL auto-generadas de PLANTA (materias primas del plan de
    producción) porque el endpoint sólo filtra por solicitante. Las categorías de planta son
    las mismas que definen `fuente=planta`: filtrar por otro criterio las haría solaparse
    (INV-1 · las 3 fuentes son mutuamente excluyentes)."""
    from database import get_db
    _limpiar(app)
    c = _cli(app)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        # una de planta (no debe salir) y una de ÁNIMUS (sí)
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "observaciones, area, empresa, categoria) VALUES "
                    "(?, date('now','-5 hours'), 'Pendiente', 'daniela', ?, 'Produccion', "
                    "'Espagiria', 'Materia Prima')", (MARCA + '-PLANTA', MARCA + ' auto-generada MP'))
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "observaciones, area, empresa, categoria) VALUES "
                    "(?, date('now','-5 hours'), 'Pendiente', 'daniela', ?, 'ANIMUS', "
                    "'Animus', 'Consumibles')", (MARCA + '-ANIMUS', MARCA + ' papel burbuja'))
        conn.commit()
    nums = [x['numero'] for x in
            c.get('/api/solicitudes-compra/mis?ambito=animus').get_json()['solicitudes']]
    assert MARCA + '-ANIMUS' in nums, 'no trae lo que Daniela pide para ÁNIMUS'
    assert MARCA + '-PLANTA' not in nums, 'trae las solicitudes de materia prima de planta'


def test_sin_el_ambito_la_bandeja_de_Catalina_no_cambia(app, db_clean):
    """Con dientes: el filtro es ADITIVO · si cambiara el default, Catalina dejaría de ver las
    solicitudes de planta en su bandeja."""
    from database import get_db
    _limpiar(app)
    c = _cli(app)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "observaciones, area, empresa, categoria) VALUES "
                    "(?, date('now','-5 hours'), 'Pendiente', 'daniela', ?, 'Produccion', "
                    "'Espagiria', 'Materia Prima')", (MARCA + '-PL2', MARCA + ' auto MP'))
        conn.commit()
    nums = [x['numero'] for x in c.get('/api/solicitudes-compra/mis').get_json()['solicitudes']]
    assert MARCA + '-PL2' in nums, 'el filtro dejó de ser aditivo'


# ── SOLO LA GENTE DE ÁNIMUS · Y EL SOPORTE COMO FOTO (4-ago) ─────────────────

def test_el_desplegable_trae_SOLO_a_la_gente_de_animus(app, db_clean):
    """Sebastián: *"aquí solo deben salir Daniela Murillo, Karol, Valentina, Jeferson, Álvaro y
    Samyra"*. Quién pertenece a ÁNIMUS es una DECISIÓN, no algo deducible del maestro (que no
    los distingue): vive en `app_settings` para corregirla sin desplegar."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM empleados WHERE codigo LIKE 'ZZE%'")
        for cod, nom, ape in (('ZZE1', 'ZzKarol', 'Perez'), ('ZZE2', 'ZzJeferson', 'Ruiz'),
                              ('ZZE3', 'ZzNadie', 'DeAnimus')):
            cur.execute("INSERT INTO empleados (codigo, nombre, apellido, estado, cargo) "
                        "VALUES (?,?,?,'Activo','Op')", (cod, nom, ape))
        cur.execute("INSERT INTO app_settings (clave, valor) VALUES "
                    "('animus_personal','ZzKarol,ZzJeferson') "
                    "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor")
        conn.commit()
    d = _cli(app).get('/api/animus/empleados').get_json()
    nombres = [e['nombre'] for e in d['empleados']]
    assert d['filtrada'] is True
    assert any('ZzKarol' in n for n in nombres), 'no trajo a quien sí es de ÁNIMUS · %s' % d
    assert any('ZzJeferson' in n for n in nombres)
    assert not any('ZzNadie' in n for n in nombres), 'trajo gente que no es de ÁNIMUS'


def test_a_quien_NO_encuentra_en_el_maestro_lo_DECLARA(app, db_clean):
    """Si no, esa persona simplemente no aparece en el desplegable y nadie sabe por qué
    (M100 · lo que no se pudo resolver se dice, no se calla)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM empleados WHERE codigo LIKE 'ZZE%'")
        cur.execute("INSERT INTO empleados (codigo, nombre, apellido, estado) "
                    "VALUES ('ZZE1','ZzKarol','Perez','Activo')")
        cur.execute("INSERT INTO app_settings (clave, valor) VALUES "
                    "('animus_personal','ZzKarol,ZzSamyra') "
                    "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor")
        conn.commit()
    d = _cli(app).get('/api/animus/empleados').get_json()
    assert 'ZzSamyra' in d['sin_cruzar']
    assert 'ZzSamyra' in d['aviso'], 'no avisa a quién no encontró'


def test_sin_lista_configurada_lo_DICE_en_vez_de_filtrar_a_ciegas(app, db_clean):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("UPDATE app_settings SET valor='' WHERE clave='animus_personal'")
        conn.commit()
    d = _cli(app).get('/api/animus/empleados').get_json()
    assert d['filtrada'] is False and d['aviso']


def test_el_soporte_se_SUBE_no_se_pega_un_enlace():
    """Un campo de enlace obliga a que la foto ya viva en algún lado; nadie tiene una URL de la
    incapacidad, la tiene en el celular."""
    html = _html_animus()
    assert 'id="nv-foto"' in html and 'type="file"' in html
    assert 'subirSoporte()' in html
    assert 'capture="environment"' in html, 'no deja sacar la foto con la cámara'
    # y el soporte se puede VER desde la lista, no es sólo una etiqueta
    assert 'ver soporte' in html


def test_una_subida_que_falla_NO_deja_el_soporte_como_guardado(app, db_clean):
    """Un "subido" que no subió nada es peor que un error: el soporte se daría por guardado."""
    html = _html_animus()
    i = html.index('async function subirSoporte(')
    cuerpo = html[i:i + 2000]
    assert "document.getElementById('nv-adjunto').value = ''" in cuerpo, \
        'ante un error no limpia el campo · la novedad quedaría diciendo que tiene soporte'


def test_espagiria_tiene_la_misma_pestana_de_novedades():
    """Sebastián: *"en el módulo Espagiria también coloca lo mismo que hicimos en el de ÁNIMUS,
    las solicitudes de permisos tal cual"*. Usa los MISMOS endpoints: dos tablas darían dos
    bandejas de RRHH y dos números de ausencias (M1/M37)."""
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'espagiria_html.py'),
                   encoding='utf-8').read()
    html = max((n.value.value for n in _ast.walk(_ast.parse(src))
                if isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000), key=len)
    assert 'id="esp-tab-novedades"' in html and "esw('novedades')" in html
    assert 'id="modal-env"' in html and 'guardarNovedadEsp()' in html
    assert '/api/bienestar/notificaciones' in html, 'no usa el circuito compartido de RRHH'
    assert "name === 'novedades'" in html, 'el conmutador no la carga'


def test_el_modal_de_solicitar_pago_deja_subir_la_factura():
    """Sebastián: *"que puedan anexar una foto si es algo que tiene ya factura"*. Se conserva
    además el campo de enlace: una cotización que llegó por correo ya tiene URL y obligar a
    bajarla y volver a subirla sería absurdo."""
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    for arch, pfx in (('espagiria_html.py', 'ep'), ('compras_html.py', 'cp')):
        src = _io.open(_os.path.join(raiz, 'api', 'templates_py', arch), encoding='utf-8').read()
        assert 'id="%s-foto"' % pfx in src, '%s no deja subir la factura' % arch
        assert 'carpeta=cotizaciones' in src, '%s no manda la foto a su carpeta' % arch
        assert 'id="%s-cotiz"' % pfx in src, '%s perdió el campo de enlace' % arch
        assert 'width:620px;' in src, '%s: el modal no se agrandó' % arch
