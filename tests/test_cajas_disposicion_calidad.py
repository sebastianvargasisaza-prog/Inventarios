"""Calidad dispone CAJA POR CAJA y el rótulo de cada caja dice la verdad (30-jul · mig 399).

Sebastián: *"llegan 40 cajas de niacinamida cada una con 200 envases (...) que me permita
imprimir los rótulos 1 de 30, 2 de 30 (...) y ya cuando calidad haga verificación entonces
revisa caja por caja y si es necesario cambia los rótulos"*.

Dos cosas que este archivo fija:
  · la **cantidad de cada caja** se guarda al recibir (en el muelle cada caja puede traer
    distinto). Si se derivara dos veces con dos cuentas, el cartón diría una cosa y el
    sistema otra (M5);
  · liberar o rechazar el movimiento COMPLETO no alcanza: de 24 cajas pueden pasar 22 y venir
    2 golpeadas, y había que elegir entre aprobar las malas o rechazar las buenas.
"""
from .conftest import TEST_PASSWORD, csrf_headers

COD = 'ZZ-MEE-CAJAS'
LOTE = 'CN-CAJA-1'


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


def _sembrar(app):
    """Referencia limpia · `stock_actual` 0 EXPLÍCITO (la tabla tiene DEFAULT 2000 · M100)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for r in cu.execute("SELECT id FROM movimientos_mee WHERE mee_codigo=?", (COD,)).fetchall():
            cu.execute("DELETE FROM mee_cajas_disposicion WHERE mov_id=?", (r[0],))
        cu.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (COD,))
        cu.execute("DELETE FROM maestro_mee WHERE codigo=?", (COD,))
        cu.execute("DELETE FROM oc_recepcion_dedup WHERE recepcion_id LIKE 'ZZCJ%'")
        cu.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                   "stock_actual, stock_minimo, estado) VALUES (?,?,?,?,0,0,'Activo')",
                   (COD, 'Frasco de prueba cajas', 'Envase', 'und'))
        conn.commit()


def _recibir(cli, cajas, tok):
    return cli.post('/api/mee/recepcion-lineas', headers=_h(), json={
        'proveedor': 'Proveedor China SA', 'factura_numero': 'IMP-CAJ-1',
        'zona': 'Z3 / A2 / 5', 'recepcion_id': tok,
        'lineas': [{'codigo': COD, 'lote_proveedor': LOTE, 'cajas_detalle': cajas}]})


def _disponible(app):
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _get_mee_stock
        return float(_get_mee_stock(get_db()).get(COD.upper(), 0) or 0)


# ══ 1 · cada caja con SU cantidad ═══════════════════════════════════════════════

def test_la_cantidad_de_cada_caja_se_guarda(app, db_clean):
    """En el muelle se abre caja por caja: la 3 puede venir con 150 y no por eso se
    'redondea' el kardex."""
    _sembrar(app)
    r = _recibir(_login(app), [200, 200, 150], 'ZZCJ-1')
    assert r.status_code == 201, r.data[:400]
    j = r.get_json()
    mv = j['movimientos'][0]
    assert mv['cantidad'] == 550, mv
    assert [c['cantidad'] for c in mv['cajas']] == [200, 200, 150], mv['cajas']
    from database import get_db
    with app.app_context():
        filas = get_db().cursor().execute(
            "SELECT caja, cantidad, estado FROM mee_cajas_disposicion WHERE mov_id=? ORDER BY caja",
            (mv['mov_id'],)).fetchall()
    assert [(int(f[0]), float(f[1])) for f in filas] == [(1, 200), (2, 200), (3, 150)]
    assert all(str(f[2]).upper() == 'CUARENTENA' for f in filas)


def test_el_rotulo_imprime_la_cantidad_de_ESA_caja(app, db_clean):
    """El rótulo se pega a un cartón: si dijera el promedio, el conteo físico nunca cuadra."""
    _sembrar(app)
    mv = _recibir(_login(app), [200, 200, 150], 'ZZCJ-2').get_json()['movimientos'][0]
    body = _login(app).get('/rotulos-recepcion-mee?mov=%d&caja=3' % mv['mov_id']).data.decode('utf-8', 'replace')
    assert 'Caja 3 de 3' in body
    assert '150' in body, 'no imprimió la cantidad de la caja 3'


def test_el_codigo_de_barras_identifica_la_CAJA(app, db_clean):
    """Dos cajas del mismo frasco tienen que distinguirse al escanear: una puede quedar
    rechazada y la otra no."""
    _sembrar(app)
    mv = _recibir(_login(app), [100, 100], 'ZZCJ-3').get_json()['movimientos'][0]
    body = _login(app).get('/rotulos-recepcion-mee?mov=%d' % mv['mov_id']).data.decode('utf-8', 'replace')
    assert 'MEE-%d-1' % mv['mov_id'] in body
    assert 'MEE-%d-2' % mv['mov_id'] in body


def test_escanear_resuelve_la_caja(app, db_clean):
    """*"pueden escanear entonces código de barras y hacer lo que corresponde"*."""
    _sembrar(app)
    cli = _login(app)
    mv = _recibir(cli, [200, 150], 'ZZCJ-4').get_json()['movimientos'][0]
    r = cli.get('/api/mee/escanear?token=MEE-%d-2' % mv['mov_id'])
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['caja'] == 2 and j['n_cajas'] == 2
    assert j['cantidad_caja'] == 150
    assert j['estado_caja'].upper() == 'CUARENTENA'
    assert j['lote'] == LOTE and j['codigo'] == COD


def test_escanear_un_codigo_que_no_es_de_caja_avisa_claro(app, db_clean):
    r = _login(app).get('/api/mee/escanear?token=HOLA-123')
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'TOKEN_INVALIDO'


# ══ 2 · la disposición parcial ══════════════════════════════════════════════════

def test_aprobar_unas_y_rechazar_otras(app, db_clean):
    """Lo que no se podía: 2 cajas golpeadas de 4 no obligan a rechazar las 4."""
    _sembrar(app)
    cli = _login(app)
    mv = _recibir(cli, [200, 200, 200, 200], 'ZZCJ-5').get_json()['movimientos'][0]
    mid = mv['mov_id']
    r = _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(), json={
        'cajas': [{'caja': 1, 'estado': 'APROBADO'}, {'caja': 2, 'estado': 'APROBADO'},
                  {'caja': 3, 'estado': 'RECHAZADO', 'motivo': 'cartón mojado'},
                  {'caja': 4, 'estado': 'RECHAZADO', 'motivo': 'frascos rotos'}],
        'cerrar': True})
    assert r.status_code == 200, r.data[:400]
    j = r.get_json()
    assert j['aprobado'] == 400 and j['rechazado'] == 400, j
    assert _disponible(app) == 400, 'el disponible no es sólo lo aprobado: %r' % _disponible(app)
    from database import get_db
    with app.app_context():
        total = get_db().cursor().execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos_mee WHERE mee_codigo=? AND tipo='Entrada'",
            (COD,)).fetchone()[0]
    assert float(total) == 800, 'el total recibido se perdió al partir: %r' % total


def test_el_rotulo_de_la_caja_rechazada_sale_RECHAZADO(app, db_clean):
    """*"si es necesario cambia los rótulos"*: reimprimir la caja 3 tiene que salir marcada,
    sin que nadie se acuerde de tachar nada."""
    _sembrar(app)
    cli = _login(app)
    mid = _recibir(cli, [200, 200, 200], 'ZZCJ-6').get_json()['movimientos'][0]['mov_id']
    _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(), json={
        'cajas': [{'caja': 1, 'estado': 'APROBADO'}, {'caja': 2, 'estado': 'APROBADO'},
                  {'caja': 3, 'estado': 'RECHAZADO', 'motivo': 'frascos rotos'}],
        'cerrar': True})
    b3 = cli.get('/rotulos-recepcion-mee?mov=%d&caja=3' % mid).data.decode('utf-8', 'replace')
    b1 = cli.get('/rotulos-recepcion-mee?mov=%d&caja=1' % mid).data.decode('utf-8', 'replace')
    # &#9746; es la casilla MARCADA · la 3 marca Rechazado, la 1 marca Aprobado
    assert '&#9746; Rechazado' in b3, 'la caja rechazada no sale marcada'
    assert '&#9746; Aprobado' in b1, 'la caja aprobada no sale marcada'


def test_rechazar_exige_motivo(app, db_clean):
    """Un rechazo sin motivo no sirve como registro: la auditoría pregunta por qué."""
    _sembrar(app)
    mid = _recibir(_login(app), [100, 100], 'ZZCJ-7').get_json()['movimientos'][0]['mov_id']
    r = _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(),
                                  json={'cajas': [{'caja': 1, 'estado': 'RECHAZADO'}]})
    assert r.status_code == 400, r.data[:300]
    assert r.get_json().get('codigo') == 'MOTIVO_REQUERIDO'


def test_no_se_cierra_con_cajas_sin_revisar(app, db_clean):
    """Cerrar a medias dejaría cajas en el limbo: ni disponibles ni rechazadas."""
    _sembrar(app)
    mid = _recibir(_login(app), [100, 100, 100], 'ZZCJ-8').get_json()['movimientos'][0]['mov_id']
    r = _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(), json={
        'cajas': [{'caja': 1, 'estado': 'APROBADO'}], 'cerrar': True})
    assert r.status_code == 409, r.data[:300]
    assert r.get_json().get('codigo') == 'CAJAS_SIN_REVISAR'


def test_solo_calidad_dispone(app, db_clean):
    """Quien recibe no decide si el material sirve."""
    _sembrar(app)
    mid = _recibir(_login(app), [100], 'ZZCJ-9').get_json()['movimientos'][0]['mov_id']
    r = _login(app, 'mayerlin').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(),
                                     json={'cajas': [{'caja': 1, 'estado': 'APROBADO'}]})
    assert r.status_code == 403, r.data[:300]


def test_todas_aprobadas_libera_todo(app, db_clean):
    """Dientes del otro lado: si las 3 pasan, el disponible es el total y no hay fila de rechazo."""
    _sembrar(app)
    mid = _recibir(_login(app), [100, 100, 100], 'ZZCJ-10').get_json()['movimientos'][0]['mov_id']
    r = _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(), json={
        'cajas': [{'caja': k, 'estado': 'APROBADO'} for k in (1, 2, 3)], 'cerrar': True})
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['mov_rechazo'] is None
    assert _disponible(app) == 300


def test_la_numeracion_de_las_cajas_NO_se_renumera(app, db_clean):
    """El rótulo pegado en el cartón dice "3 de 3". Si al aprobar 2 el sistema pasara a
    "2 cajas", ese cartón hablaría de una caja que ya no existe: la numeración física es un
    hecho, no un derivado (M115)."""
    _sembrar(app)
    cli = _login(app)
    mid = _recibir(cli, [100, 100, 100], 'ZZCJ-11').get_json()['movimientos'][0]['mov_id']
    _login(app, 'laura').post('/api/mee/cuarentena/%d/cajas' % mid, headers=_h(), json={
        'cajas': [{'caja': 1, 'estado': 'APROBADO'}, {'caja': 2, 'estado': 'APROBADO'},
                  {'caja': 3, 'estado': 'RECHAZADO', 'motivo': 'roto'}], 'cerrar': True})
    body = cli.get('/rotulos-recepcion-mee?mov=%d' % mid).data.decode('utf-8', 'replace')
    assert 'Caja 3 de 3' in body, 'se renumeraron las cajas físicas'
    assert body.count('class="sheet"') == 3


# ══ 3 · la pantalla de Calidad ══════════════════════════════════════════════════

def test_calidad_ve_el_escaneo_y_el_boton_de_cajas(app, db_clean):
    """Si no le llega a la pantalla de Laura, la función no existe para ella. El golden no
    abre pantallas (M78), así que el render va en su propio test."""
    _sembrar(app)
    _recibir(_login(app), [100, 100], 'ZZCJ-12')
    r = _login(app, 'laura').get('/calidad')
    assert r.status_code == 200, r.status_code
    body = r.data.decode('utf-8', 'replace')
    assert 'cjs-scan' in body, 'falta el campo de escaneo de la caja'
    assert 'cjsEscanear' in body, 'el JS de la revisión por caja no se inyectó'
    assert 'cjsAbrir' in body, 'falta el abridor de la revisión'


def test_ningun_boton_de_calidad_quedo_sin_funcion(app, db_clean):
    """M112: un botón que llama a lo que no existe no falla, no hace nada, y se despliega."""
    import re
    body = _login(app, 'laura').get('/calidad').data.decode('utf-8', 'replace')
    llamadas = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\(', body))
    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', body))
    huerfanas = llamadas - definidas - {'alert', 'confirm', 'print'}
    assert not huerfanas, 'botones sin función en /calidad: %s' % sorted(huerfanas)


def test_el_panel_de_cajas_no_pisa_funciones_de_calidad(app, db_clean):
    """Comparten documento: una función repetida pisa la de la página sin un solo error (M59)."""
    import re
    body = _login(app, 'laura').get('/calidad').data.decode('utf-8', 'replace')
    nombres = re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', body)
    dupes = sorted({n for n in nombres if nombres.count(n) > 1})
    assert not dupes, 'funciones declaradas dos veces en /calidad: %s' % dupes
