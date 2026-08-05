# -*- coding: utf-8 -*-
"""Las PIEZAS entran al inventario con el envase, y quien recibe lo CONFIRMA.

Sebastián (5-ago), con la pantalla de recepción delante: *"aquí debería existir la lógica de ese
envase tiene parte? viene con gotero? y si lo compramos con plegadiza y llega con plegadiza desde
China, ALLÍ es donde debe vivir todo porque allí se da la recepción... aquí debe vivir todo para
que garantice que se recepcionó perfecto"*.

Hasta hoy la recepción NO tocaba `mee_partes` en ninguna de sus dos puertas: el modelo asumía que
gotero, tapa y plegadiza se compran SUELTOS y que el frasco sólo arrastra la necesidad. Cuando el
frasco llega armado de China, eso hace comprar goteros que ya están en la caja.

La distinción que hace que funcione: `mee_partes` dice que el frasco LLEVA gotero -- receta del
envase, no cambia. Que ESTE embarque VINO con el gotero adentro es un hecho del EMBARQUE. El
mismo frasco puede venir armado de China y suelto de un proveedor local; por eso se declara al
recibir y no en el maestro.

⚠ Los tests limpian ANTES de sembrar (M103): la base de tests es compartida y en PG persiste
entre corridas, así que limpiar en un `finally` no alcanza (un assert que falla se lo saltea).
"""
import io
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRASCO = 'MEE-ZZTEST-FRASCO'
GOTERO = 'MEE-ZZTEST-GOTERO'
PLEGA = 'MEE-ZZTEST-PLEGA'
FANTASMA = 'MEE-ZZTEST-NOEXISTE'


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios_js(txt):
    """Un escáner que no quita comentarios encuentra la prosa del propio autor (M154)."""
    return re.sub(r'//[^\n]*', '', txt)


def _sembrar(app, con_partes=True):
    """Deja el maestro con frasco + gotero + plegadiza y la receta del envase."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod in (FRASCO, GOTERO, PLEGA):
            c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (FRASCO,))
        for cod, desc in ((FRASCO, 'ZZ frasco vidrio 30 ml'),
                          (GOTERO, 'ZZ gotero negro'),
                          (PLEGA, 'ZZ plegadiza')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',0,0,'Activo','2026-08-05')", (cod, desc))
        if con_partes:
            for parte, cant in ((GOTERO, 1), (PLEGA, 2)):
                c.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, "
                          " cantidad, creado_at) VALUES (?,?,'',?,'2026-08-05')",
                          (FRASCO, parte, cant))
        conn.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod in (FRASCO, GOTERO, PLEGA):
            c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (FRASCO,))
        conn.commit()


def _recibir(admin_client, partes, cajas=(100.0, 100.0), token='zz'):
    """⚠ `token` DISTINTO por test a propósito: el `recepcion_id` es la llave de idempotencia
    del cliente (M45) y dos tests que mandan el mismo token hacen que el segundo se rechace
    como duplicado -- el test falla y el código está sano. Que eso pasara es, de hecho, la
    prueba de que el guard anti-doble-recepción funciona."""
    from .conftest import csrf_headers
    cuerpo = {
        'proveedor': 'ZZ Proveedor China', 'factura_numero': 'ZZ-IMP-001',
        'zona': 'A / 1 / 1', 'recepcion_id': 'zz-tok-%s' % token,
        'lineas': [{'codigo': FRASCO, 'lote_proveedor': 'ZZLOTE-1',
                    'cajas_detalle': list(cajas), 'partes': partes}],
    }
    return admin_client.post('/api/mee/recepcion-lineas', data=json.dumps(cuerpo),
                             headers=csrf_headers(), content_type='application/json')


def _stock(app, cod):
    """Stock CANÓNICO del kardex (M26) · nunca el cache `maestro_mee.stock_actual`."""
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad "
            "                         WHEN LOWER(tipo)='salida' THEN -cantidad "
            "                         ELSE cantidad END),0) "
            "  FROM movimientos_mee WHERE mee_codigo=? AND COALESCE(anulado,0)=0",
            (cod,)).fetchone()[0]


# ── 1 · lo que vino adentro ENTRA al inventario ──────────────────────────────

def test_la_pieza_incluida_ENTRA_al_kardex_con_su_cantidad(app, admin_client, db_clean):
    """200 frascos con 1 gotero y 2 plegadizas cada uno = 200 goteros y 400 plegadizas.

    La cantidad se MULTIPLICA, no se teclea: si se tecleara, el día que cambien las unidades
    del bulto los dos números divergen y nadie sabría cuál manda (M71/M99).
    """
    _sembrar(app)
    r = _recibir(admin_client, [{'codigo': GOTERO, 'cantidad_por_envase': 1},
                                {'codigo': PLEGA, 'cantidad_por_envase': 2}], token='entra')
    assert r.status_code == 201, r.data[:400]
    j = r.get_json()

    assert _stock(app, FRASCO) == 200, 'el frasco no entró completo'
    assert _stock(app, GOTERO) == 200, 'el gotero NO entró al inventario con el frasco'
    assert _stock(app, PLEGA) == 400, 'la plegadiza no multiplicó por 2 piezas por envase'

    # La respuesta las NOMBRA: si sólo se sumaran al total, quien recibe no podría verificar
    # que el gotero quedó registrado.
    cods = {x['codigo'] for x in (j.get('partes_ingresadas') or [])}
    assert cods == {GOTERO, PLEGA}, j.get('partes_ingresadas')
    _limpiar(app)


def test_la_pieza_que_se_compra_APARTE_no_entra(app, admin_client, db_clean):
    """El caso que hace que esto sea una CONFIRMACIÓN y no un automatismo: el mismo frasco
    puede venir armado de China y suelto del proveedor local. Si entrara siempre, un embarque
    sin goteros crearía stock de goteros que no existen."""
    _sembrar(app)
    r = _recibir(admin_client, [], token='pelado')   # llegó pelado
    assert r.status_code == 201, r.data[:300]
    assert _stock(app, FRASCO) == 200
    assert _stock(app, GOTERO) == 0, 'entró un gotero que nadie declaró'
    assert _stock(app, PLEGA) == 0
    assert not (r.get_json().get('partes_ingresadas') or [])
    _limpiar(app)


def test_la_pieza_queda_AMARRADA_al_movimiento_del_frasco(app, admin_client, db_clean):
    """Sin la marca `[recep #N]` no se puede deshacer una recepción mal hecha: habría que
    adivinar cuál de las entradas de gotero vino con cuál frasco."""
    from database import get_db
    _sembrar(app)
    r = _recibir(admin_client, [{'codigo': GOTERO, 'cantidad_por_envase': 1}], token='amarre')
    mov_frasco = r.get_json()['movimientos'][0]['mov_id']
    with app.app_context():
        obs = get_db().execute(
            "SELECT COALESCE(observaciones,'') FROM movimientos_mee "
            " WHERE mee_codigo=? ORDER BY id DESC LIMIT 1", (GOTERO,)).fetchone()[0]
    assert '[recep #%d]' % mov_frasco in obs, obs
    assert FRASCO in obs, 'la observación no dice de qué envase vino'
    _limpiar(app)


def test_la_pieza_hereda_LOTE_y_VENCIMIENTO_del_bulto(app, admin_client, db_clean):
    """Un gotero que entra sin vencimiento es un gotero que el cron de vencidos deja de ver y
    el FEFO trata como eterno (M118). Vino en la misma caja: es el mismo lote."""
    from database import get_db
    from .conftest import csrf_headers
    _sembrar(app)
    cuerpo = {'proveedor': 'ZZ', 'recepcion_id': 'zz-venc',
              'lineas': [{'codigo': FRASCO, 'lote_proveedor': 'ZZLOTE-9',
                          'cajas_detalle': [50.0], 'fecha_vencimiento': '2027-12-31',
                          'partes': [{'codigo': GOTERO, 'cantidad_por_envase': 1}]}]}
    r = admin_client.post('/api/mee/recepcion-lineas', data=json.dumps(cuerpo),
                          headers=csrf_headers(), content_type='application/json')
    assert r.status_code == 201, r.data[:300]
    with app.app_context():
        lote, venc = get_db().execute(
            "SELECT COALESCE(lote_ref,''), COALESCE(fecha_vencimiento,'') FROM movimientos_mee "
            " WHERE mee_codigo=? ORDER BY id DESC LIMIT 1", (GOTERO,)).fetchone()
    assert lote == 'ZZLOTE-9', 'la pieza perdió el lote del bulto'
    assert venc == '2027-12-31', 'la pieza entró SIN vencimiento'
    _limpiar(app)


# ── 2 · lo que NO se puede ingresar se DECLARA ───────────────────────────────

def test_una_pieza_que_no_existe_en_el_maestro_se_DECLARA_y_no_entra(app, admin_client, db_clean):
    """Un código mal tecleado que entra igual crea stock fantasma que nadie puede reponer
    (M100). Y un rechazo silencioso es peor: el frasco queda 'perfecto' sin su gotero."""
    _sembrar(app)
    r = _recibir(admin_client, [{'codigo': FANTASMA, 'cantidad_por_envase': 1}], token='fantasma')
    assert r.status_code == 201, r.data[:300]
    j = r.get_json()
    assert not (j.get('partes_ingresadas') or []), 'ingresó una pieza que no está en el maestro'
    avisos = ' '.join(j.get('avisos') or [])
    assert FANTASMA in avisos, 'la pieza rechazada no se declaró · ' + repr(j.get('avisos'))
    _limpiar(app)


def test_la_pieza_se_RECUERDA_para_la_proxima_recepcion(app, admin_client, db_clean):
    """`incluido_default` es MEMORIA, no regla: premarca la casilla. Sin esto, quien recibe
    tiene que acordarse cada vez de que ese frasco viene armado -- y un dato que alguien tiene
    que recordar termina viejo (M109)."""
    from database import get_db
    _sembrar(app)
    with app.app_context():
        antes = get_db().execute(
            "SELECT COALESCE(incluido_default,0) FROM mee_partes "
            " WHERE mee_codigo=? AND parte_codigo=?", (FRASCO, GOTERO)).fetchone()[0]
    assert int(antes) == 0, 'nace SIN memoria · el default no puede ser "viene incluida"'

    _recibir(admin_client, [{'codigo': GOTERO, 'cantidad_por_envase': 1}], token='memoria')
    with app.app_context():
        despues = get_db().execute(
            "SELECT COALESCE(incluido_default,0) FROM mee_partes "
            " WHERE mee_codigo=? AND parte_codigo=?", (FRASCO, GOTERO)).fetchone()[0]
    assert int(despues) == 1, 'no recordó que el gotero vino adentro'

    # Y el endpoint que alimenta la pantalla lo DEVUELVE (si no, la memoria existe y no premarca
    # nada · M121: una capacidad que no llega a la puerta no existe).
    rp = admin_client.get('/api/mee/partes?codigo=' + FRASCO)
    assert rp.status_code == 200
    got = [x for x in rp.get_json()['partes'] if x['codigo'] == GOTERO]
    assert got and got[0].get('incluido_default') == 1, rp.get_json()
    _limpiar(app)


def test_el_endpoint_de_partes_avisa_si_la_pieza_NO_esta_en_el_maestro(app, admin_client, db_clean):
    """La pantalla tiene que poder decir "esta pieza no puede entrar" ANTES de recibir, no
    después. Un `en_maestro` que no viaja obliga a descubrirlo en el aviso final."""
    from database import get_db
    _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                     " creado_at) VALUES (?,?,'',1,'2026-08-05')", (FRASCO, FANTASMA))
        conn.commit()
    j = admin_client.get('/api/mee/partes?codigo=' + FRASCO).get_json()
    por_cod = {x['codigo']: x for x in j['partes']}
    assert por_cod[GOTERO]['en_maestro'] is True
    assert por_cod[FANTASMA]['en_maestro'] is False, 'no avisa que la pieza no existe'
    _limpiar(app)


# ── 3 · la pantalla ──────────────────────────────────────────────────────────

def test_la_pantalla_PREGUNTA_que_trae_el_bulto(app, db_clean):
    from templates_py.recepcion_envases_panel import PANEL_ENVASES_HTML as H
    assert 'id="env-partes-card"' in H, 'no está el paso "¿Qué trae el bulto?"'
    assert 'Qu&eacute; trae el bulto' in H
    js = _sin_comentarios_js(H)
    assert 'function envPartesPayload' in js, 'no arma el payload de piezas'
    assert 'function envCargarPartes' in js
    # y el payload VIAJA en el envío · sin esto la pantalla pregunta y el backend nunca se entera
    i = js.find('async function envRecibir')
    assert i > 0
    assert 'partes:_pz' in js[i:i + 3000], 'las piezas no viajan en la recepción'


def test_la_pantalla_no_promete_CUARENTENA_cuando_entra_disponible(app, db_clean):
    """El encabezado dice "entra disponible" y el confirm decía "en CUARENTENA": dos pantallas
    que describen el mismo hecho de forma distinta hacen que no se crea en ninguna (M161)."""
    from templates_py.recepcion_envases_panel import PANEL_ENVASES_HTML as H
    js = _sin_comentarios_js(H)
    i = js.find('async function envRecibir')
    bloque = js[i:i + 2000]
    assert 'CUARENTENA' not in bloque, 'el confirm sigue prometiendo cuarentena'
    assert 'DISPONIBLE' in bloque


def test_la_referencia_nueva_puede_declarar_sus_piezas(app, db_clean):
    """Si la referencia nace sin piezas, la recepción no tiene nada que preguntar y el envase
    entra solo para siempre: el gotero se sigue comprando aparte sin que nadie lo note."""
    from templates_py.recepcion_envases_panel import PANEL_ENVASES_HTML as H
    js = _sin_comentarios_js(H)
    assert 'id="env-n-pieza"' in H, 'el formulario de crear referencia no pide piezas'
    assert 'function envPiezaAgregar' in js
    i = js.find('async function envCrearRef')
    assert 'partes:ENV_NPIEZAS' in js[i:i + 2500], 'las piezas declaradas no se envían al crear'


def test_la_columna_de_memoria_existe(app, db_clean):
    """mig 418 · sin la columna, `incluido_default` sería un `except` mudo que deja la casilla
    siempre desmarcada (M96: una columna fantasma dentro de un try es una feature muerta)."""
    from database import get_db
    with app.app_context():
        get_db().execute("SELECT incluido_default FROM mee_partes LIMIT 0")
