"""Recepción administrativa de ENVASES por líneas · sin OC (30-jul).

Sebastián: *"mañana llegan 9 palets de China, no tenemos la orden de compra en EOS
(las pidió Alejandro) y llegan a planta · necesito hacerle recepción administrativa
para que después Calidad haga lo suyo"*.

El camino de a un código existía (`/api/mee/movimiento`) y funciona sin OC. Con 10+
referencias son 15 formularios y 15 pop-ups de rótulo, así que la recepción se hace por
LÍNEAS: se carga el packing list, se ve qué cruza contra el maestro ANTES de escribir, y
entra todo en una pasada.

Dos reglas duras que este archivo fija:
  · **la vista previa no escribe NADA** y el apply es TODO-o-NADA: una recepción es un
    hecho único con su factura, no 12 hechos independientes que pueden quedar a medias;
  · **entra en CUARENTENA y NO cuenta como disponible** hasta que Calidad libere con el
    F01. El bug que esto destapó: la pantalla de Envases sumaba el stock SIN excluir
    cuarentena mientras el canónico (`_get_mee_stock`, el que usa producción) SÍ la
    excluye → los 9 palets se veían disponibles antes de que Laura los liberara (M5/M26).
"""
from .conftest import TEST_PASSWORD, csrf_headers

COD_A = 'ZZ-MEE-FRASCO30'
COD_B = 'ZZ-MEE-TAPA'
COD_FANTASMA = 'ZZ-MEE-NO-EXISTE'
LOTE_PROV = 'CN-2607-A'


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
    """Dos códigos MEE en el maestro y CERO movimientos. Limpia ANTES (M103).
    ⚠ `maestro_mee` tiene `stock_actual DEFAULT 2000` → el alta va con 0 EXPLÍCITO o
    inventa 2000 unidades que nadie recibió (M100)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for cod in (COD_A, COD_B, COD_FANTASMA):
            cu.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
            cu.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        cu.execute("DELETE FROM oc_recepcion_dedup WHERE recepcion_id LIKE 'ZZTOK%'")
        for cod, desc, uni in ((COD_A, 'Frasco vidrio 30 ml', 'und'),
                               (COD_B, 'Tapa negra rosca', 'und')):
            cu.execute(
                "INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                "stock_actual, stock_minimo, estado) VALUES (?,?,?,?,0,0,'Activo')",
                (cod, desc, 'Envase', uni))
        conn.commit()


def _disponible_canonico(app, codigo):
    """Lo que ve producción/planeación: el helper canónico, que excluye cuarentena."""
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _get_mee_stock
        return float(_get_mee_stock(get_db()).get(codigo.upper(), 0) or 0)


def _lineas(**over):
    """La línea real de un contenedor: llega en CAJAS. 'cantidad' es DERIVADA
    (n_cajas × unidades_por_caja), no se teclea aparte (M71: un dato derivado no es
    fuente de verdad y si se teclea, diverge)."""
    base = {
        'proveedor': 'Proveedor China SA',
        'factura_numero': 'IMP-2026-77',
        'zona': 'Bodega envases',
        'lineas': [
            {'codigo': COD_A, 'n_cajas': 24, 'unidades_por_caja': 200,
             'lote_proveedor': LOTE_PROV},
            {'codigo': COD_B, 'n_cajas': 42, 'unidades_por_caja': 200,
             'lote_proveedor': 'CN-2607-B'},
        ],
    }
    base.update(over)
    return base


# ══ 1 · la vista previa NO escribe ══════════════════════════════════════════════

def test_preview_no_escribe_nada_y_marca_lo_que_no_cruza(app, db_clean):
    _sembrar(app)
    body = _lineas()
    body['lineas'].append({'codigo': COD_FANTASMA, 'cantidad': 1200,
                           'lote_proveedor': 'CN-2607-B'})
    body['preview'] = True
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body)
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['total_lineas'] == 3
    assert j['total_unidades'] == 4800 + 8400 + 1200
    faltantes = [x['codigo'] for x in j['lineas'] if not x['existe']]
    assert faltantes == [COD_FANTASMA], j['lineas']
    # el que cruza trae su descripción del maestro (para que se vea QUÉ se está recibiendo)
    ok_a = next(x for x in j['lineas'] if x['codigo'] == COD_A)
    assert 'Frasco' in ok_a['descripcion']
    assert _disponible_canonico(app, COD_A) == 0, 'la vista previa escribió stock'


def test_preview_avisa_dos_lineas_del_mismo_codigo_y_lote(app, db_clean):
    """Dos veces el mismo (código, lote) en un envío casi siempre es el packing list
    pegado dos veces. No se rechaza (puede ser legítimo: dos palets del mismo lote),
    se AVISA para que lo mire antes de recibir."""
    _sembrar(app)
    body = _lineas(lineas=[
        {'codigo': COD_A, 'cantidad': 4800, 'lote_proveedor': LOTE_PROV},
        {'codigo': COD_A, 'cantidad': 4800, 'lote_proveedor': LOTE_PROV},
    ])
    body['preview'] = True
    j = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body).get_json()
    assert j.get('avisos'), 'no avisó el duplicado dentro del mismo envío'
    assert any('repetida' in a.lower() or 'duplic' in a.lower() for a in j['avisos']), j


# ══ 2 · el apply · sin OC, TODO-o-NADA ══════════════════════════════════════════

def test_recibe_sin_orden_de_compra(app, db_clean):
    """El caso real: las pidió Alejandro y no hay OC en EOS. La OC es texto libre y
    opcional; su ausencia no puede frenar una recepción física que ya llegó."""
    _sembrar(app)
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                         json=_lineas(recepcion_id='ZZTOK-1'))
    assert r.status_code == 201, r.data[:400]
    j = r.get_json()
    assert j['recibidas'] == 2
    assert len(j['movimientos']) == 2


def test_si_falta_UN_codigo_no_se_escribe_NADA(app, db_clean):
    """Una recepción es un hecho único con su factura. Media recepción escrita es peor
    que ninguna: nadie sabe qué entró y qué no."""
    _sembrar(app)
    body = _lineas(recepcion_id='ZZTOK-2')
    body['lineas'].append({'codigo': COD_FANTASMA, 'cantidad': 1200,
                           'lote_proveedor': 'X'})
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body)
    assert r.status_code == 409, r.data[:300]
    assert r.get_json().get('codigo') == 'CODIGOS_SIN_MAESTRO'
    assert COD_FANTASMA in (r.get_json().get('faltantes') or [])
    assert _disponible_canonico(app, COD_A) == 0, 'escribió a medias'
    from database import get_db
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo IN (?,?)",
            (COD_A, COD_B)).fetchone()[0]
    assert n == 0, 'quedaron %d movimientos de una recepción rechazada' % n


def test_cantidad_invalida_rechaza_todo(app, db_clean):
    _sembrar(app)
    body = _lineas(recepcion_id='ZZTOK-3',
                   lineas=[{'codigo': COD_A, 'cantidad': 0, 'lote_proveedor': 'X'}])
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body)
    assert r.status_code == 400, r.data[:300]


def test_codigo_con_tabulador_o_espacios_se_normaliza(app, db_clean):
    """M100: un tabulador pegado a un código es una CLAVE DISTINTA → 1000 envases
    invisibles en el kardex, sin un solo error a la vista. Se normaliza al escribir."""
    _sembrar(app)
    body = _lineas(recepcion_id='ZZTOK-4', lineas=[
        {'codigo': '\t' + COD_A + ' ', 'cantidad': 100, 'lote_proveedor': ' L1 '}])
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body)
    assert r.status_code == 201, r.data[:300]
    from database import get_db
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT mee_codigo, lote_ref FROM movimientos_mee WHERE mee_codigo=?",
            (COD_A,)).fetchone()
    assert row is not None, 'el código quedó guardado con basura alrededor'
    assert row[1] == 'L1'


# ══ 3 · entra en CUARENTENA y NO cuenta como disponible ═════════════════════════

def test_entra_en_cuarentena_y_no_suma_al_disponible(app, db_clean):
    """El envase recibido NO es stock usable hasta que Calidad lo libere con el F01."""
    _sembrar(app)
    _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                     json=_lineas(recepcion_id='ZZTOK-5'))
    from database import get_db
    with app.app_context():
        estados = [r[0] for r in get_db().cursor().execute(
            "SELECT UPPER(COALESCE(estado,'')) FROM movimientos_mee WHERE mee_codigo IN (?,?)",
            (COD_A, COD_B)).fetchall()]
    assert estados and all(e == 'CUARENTENA' for e in estados), estados
    assert _disponible_canonico(app, COD_A) == 0, 'cuarentena contó como disponible'


def test_la_PANTALLA_de_envases_no_muestra_la_cuarentena_como_disponible(app, db_clean):
    """EL BUG que destapó esto (M5/M26): `/api/mee/stock` sumaba SIN excluir cuarentena
    mientras el canónico sí la excluye → dos números para lo mismo, y el que se ve es el
    que miente. Con 9 palets entrando, la pantalla los daba por disponibles."""
    _sembrar(app)
    _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                     json=_lineas(recepcion_id='ZZTOK-6'))
    r = _login(app).get('/api/mee/stock')
    assert r.status_code == 200
    item = next((x for x in r.get_json()['items'] if x['codigo'] == COD_A), None)
    assert item is not None, 'el código no aparece en la pantalla de envases'
    assert float(item['stock_actual']) == 0, (
        'la pantalla muestra %s disponible con todo en cuarentena' % item['stock_actual'])
    assert float(item.get('en_cuarentena') or 0) == 4800, (
        'no muestra APARTE lo retenido: el operario no puede saber por qué no subió')


def test_liberar_en_calidad_lo_vuelve_disponible(app, db_clean):
    """El otro lado: una vez liberado, sí cuenta. Un gate que nunca abre no es un gate."""
    _sembrar(app)
    _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                     json=_lineas(recepcion_id='ZZTOK-7'))
    from database import get_db
    with app.app_context():
        conn = get_db()
        mid = conn.cursor().execute(
            "SELECT id FROM movimientos_mee WHERE mee_codigo=?", (COD_A,)).fetchone()[0]
    r = _login(app, 'laura').post('/api/mee/cuarentena/%d/liberar' % mid, headers=_h())
    assert r.status_code == 200, r.data[:300]
    assert _disponible_canonico(app, COD_A) == 4800


def test_aparece_en_la_bandeja_de_calidad_para_el_F01(app, db_clean):
    """Si no le llega a Laura, la recepción administrativa no sirve de nada."""
    _sembrar(app)
    _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                     json=_lineas(recepcion_id='ZZTOK-8'))
    r = _login(app, 'laura').get('/api/calidad/recepcion-pipeline')
    assert r.status_code == 200, r.data[:300]
    mee = [x for x in (r.get_json().get('lotes') or [])
           if x.get('tipo') == 'MEE' and x.get('codigo_mp') == COD_A]
    assert mee, 'el envase recibido no le llegó a Calidad'
    assert mee[0]['lote'] == LOTE_PROV, 'el lote del proveedor no viajó al F01'
    assert mee[0]['proveedor'] == 'Proveedor China SA'


# ══ 4 · idempotencia · el doble-click no duplica 9 palets ═══════════════════════

def test_el_mismo_token_no_duplica_la_recepcion(app, db_clean):
    """M45: para deduplicar una acción repetible el token lo genera el CLIENTE — el
    servidor no puede distinguir un doble-envío de una segunda recepción legítima del
    mismo material. Sin esto, un doble-click mete 9 palets dos veces."""
    _sembrar(app)
    cli = _login(app)
    r1 = cli.post('/api/mee/recepcion-lineas', headers=_h(),
                  json=_lineas(recepcion_id='ZZTOK-9'))
    assert r1.status_code == 201, r1.data[:300]
    r2 = cli.post('/api/mee/recepcion-lineas', headers=_h(),
                  json=_lineas(recepcion_id='ZZTOK-9'))
    assert r2.status_code == 409, r2.data[:300]
    assert r2.get_json().get('codigo') == 'RECEPCION_DUPLICADA'
    from database import get_db
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo=?", (COD_A,)).fetchone()[0]
    assert n == 1, 'se duplicó la recepción (%d movimientos)' % n


def test_token_distinto_SI_recibe_otra_vez(app, db_clean):
    """Dientes del guard: un segundo envío real del mismo material (otro palet, otra
    remisión) tiene otro token y debe entrar."""
    _sembrar(app)
    cli = _login(app)
    cli.post('/api/mee/recepcion-lineas', headers=_h(), json=_lineas(recepcion_id='ZZTOK-10'))
    r = cli.post('/api/mee/recepcion-lineas', headers=_h(), json=_lineas(recepcion_id='ZZTOK-11'))
    assert r.status_code == 201, r.data[:300]


# ══ 5 · llega en CAJAS · un rótulo por caja, numerado ═══════════════════════════

def test_la_cantidad_se_DERIVA_de_las_cajas(app, db_clean):
    """Sebastián: *"llegan 40 cajas de niacinamida, cada una con 200 envases"*. Lo que se
    cuenta en el muelle son CAJAS; las unidades son la multiplicación. Si se teclearan las
    dos, divergen (M71)."""
    _sembrar(app)
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                         json=_lineas(recepcion_id='ZZTOK-13'))
    assert r.status_code == 201, r.data[:400]
    from database import get_db
    with app.app_context():
        cant = get_db().cursor().execute(
            "SELECT cantidad FROM movimientos_mee WHERE mee_codigo=?", (COD_A,)).fetchone()[0]
    assert float(cant) == 24 * 200, cant


def test_ultima_caja_incompleta(app, db_clean):
    """El caso que SIEMPRE pasa: 24 cajas de 200 y la última viene con 150. Si el sistema
    exige que todas sean iguales, el operario 'redondea' y el kardex queda mintiendo."""
    _sembrar(app)
    body = _lineas(recepcion_id='ZZTOK-14', lineas=[
        {'codigo': COD_A, 'n_cajas': 24, 'unidades_por_caja': 200,
         'unidades_ultima_caja': 150, 'lote_proveedor': LOTE_PROV}])
    r = _login(app).post('/api/mee/recepcion-lineas', headers=_h(), json=body)
    assert r.status_code == 201, r.data[:400]
    from database import get_db
    with app.app_context():
        cant = get_db().cursor().execute(
            "SELECT cantidad FROM movimientos_mee WHERE mee_codigo=?", (COD_A,)).fetchone()[0]
    assert float(cant) == 23 * 200 + 150, cant


def test_un_rotulo_por_caja_numerado(app, db_clean):
    """*"que me permita imprimir los rótulos 1 de 30, 2 de 30, etc"*. Un rótulo por caja,
    con SU cantidad y su número, porque el rótulo se pega a una caja física."""
    _sembrar(app)
    cli = _login(app)
    j = cli.post('/api/mee/recepcion-lineas', headers=_h(),
                 json=_lineas(recepcion_id='ZZTOK-15')).get_json()
    mov_a = next(m for m in j['movimientos'] if m['codigo'] == COD_A)
    r = cli.get('/rotulos-recepcion-mee?mov=%d' % mov_a['mov_id'])
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert 'Caja 1 de 24' in body, 'no numeró las cajas'
    assert 'Caja 24 de 24' in body, 'faltan cajas al final'
    assert 'Caja 25 de 24' not in body
    assert body.count('class="sheet"') == 24, 'un rótulo por caja: %d' % body.count('class="sheet"')
    assert LOTE_PROV in body, 'el rótulo no lleva el lote del proveedor'
    assert 'CUARENTENA' in body.upper(), 'el rótulo no dice que está retenido'


def test_los_rotulos_de_TODA_la_recepcion_en_una_pasada(app, db_clean):
    """Con 12 líneas nadie va a abrir 12 pestañas: los rótulos de todas las cajas de la
    recepción salen en un solo imprimible."""
    _sembrar(app)
    cli = _login(app)
    j = cli.post('/api/mee/recepcion-lineas', headers=_h(),
                 json=_lineas(recepcion_id='ZZTOK-16')).get_json()
    movs = ','.join(str(m['mov_id']) for m in j['movimientos'])
    r = cli.get('/rotulos-recepcion-mee?movs=' + movs)
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert COD_A in body and COD_B in body
    # 24 cajas + 42 cajas
    assert body.count('class="sheet"') == 24 + 42, body.count('class="sheet"')


def test_calidad_puede_reimprimir_el_rotulo_de_UNA_caja(app, db_clean):
    """*"cuando calidad haga verificación revisa caja por caja y si es necesario cambia los
    rótulos"*. Para cambiar el de la caja 7 hay que poder imprimir SÓLO la caja 7 — y con
    el mismo número, que sale de lo que se guardó en la recepción, no de un recuento nuevo."""
    _sembrar(app)
    cli = _login(app)
    j = cli.post('/api/mee/recepcion-lineas', headers=_h(),
                 json=_lineas(recepcion_id='ZZTOK-17')).get_json()
    mov_a = next(m for m in j['movimientos'] if m['codigo'] == COD_A)
    r = cli.get('/rotulos-recepcion-mee?mov=%d&caja=7' % mov_a['mov_id'])
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert 'Caja 7 de 24' in body
    assert body.count('class="sheet"') == 1, 'imprimió más de una caja'


def test_las_cajas_quedan_GUARDADAS_no_se_recalculan(app, db_clean):
    """Si el número de cajas no se guarda, el día que Calidad reimprima el rótulo de la
    caja 7 el sistema tiene que adivinar cuántas cajas eran (M115: un dato que se captura
    y se pierde termina inventado por la pantalla)."""
    _sembrar(app)
    _login(app).post('/api/mee/recepcion-lineas', headers=_h(),
                     json=_lineas(recepcion_id='ZZTOK-18'))
    from database import get_db
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT n_cajas, unidades_por_caja FROM movimientos_mee WHERE mee_codigo=?",
            (COD_A,)).fetchone()
    assert row and int(row[0]) == 24 and float(row[1]) == 200, row


# ══ 6 · vive DENTRO de Recepción, como una pestaña ══════════════════════════════

def test_el_panel_vive_en_la_pestana_de_recepcion(app, db_clean):
    """Sebastián: *"no puede quedar todo de manera loca, pueden quedar en recepción pero
    como una pestaña"*. El punto de entrada lo define el TIPO de cosa que llega, no la
    feature que la construyó."""
    r = _login(app).get('/recepcion')
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert 'rt-btn-env' in body, 'no está la pestaña de contenedor sin OC'
    assert 'envRecibir' in body, 'el panel de envases no se inyectó en la página'
    assert '__PANEL_ENVASES__' not in body, 'el placeholder quedó sin reemplazar'


def test_la_pagina_vieja_redirige_a_la_pestana(app, db_clean):
    """La ruta anterior se conserva redirigiendo: borrarla deja un enlace (o un marcador)
    apuntando a la nada, que no falla y simplemente no hace nada (M112)."""
    r = _login(app).get('/planta/recepcion-envases')
    assert r.status_code in (301, 302), r.status_code
    assert '/recepcion' in (r.headers.get('Location') or '')


def test_cada_boton_de_recepcion_tiene_su_funcion(app, db_clean):
    """M112: un botón que llama a lo que no existe no falla, no hace nada, y se despliega.
    Se cruza sobre el documento COMPLETO porque el panel comparte página con el flujo de
    OCs: es ahí donde una función pisada por otra del mismo nombre se nota."""
    import re
    body = _login(app).get('/recepcion').data.decode('utf-8', 'replace')
    llamadas = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\(', body))
    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', body))
    huerfanas = llamadas - definidas - {'alert', 'confirm', 'print'}
    assert not huerfanas, 'botones sin función: %s' % sorted(huerfanas)


def test_el_panel_no_pisa_funciones_de_la_pagina_de_recepcion(app, db_clean):
    """Comparten documento: una segunda `function esc(...)` pisa la de la página y rompe
    la pantalla ajena sin un solo error (M59). Ninguna función puede declararse dos veces."""
    import re
    body = _login(app).get('/recepcion').data.decode('utf-8', 'replace')
    nombres = re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', body)
    dupes = sorted({n for n in nombres if nombres.count(n) > 1})
    assert not dupes, 'funciones declaradas dos veces en la misma página: %s' % dupes
