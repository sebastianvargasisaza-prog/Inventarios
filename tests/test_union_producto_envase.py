# -*- coding: utf-8 -*-
"""¿El inventario de envases JUNTA con cada producto?

Sebastián (5-ago): *"debemos ir a revisar lo que hay, si ya junta con cada producto y demás"*.

El diagnóstico que existía contestaba media pregunta: *"¿el producto tiene frasco?"*. Pero el
motor de compra también lee la TAPA, la CAJA y las PIEZAS del frasco (gotero, plegadiza), así que
un producto con frasco y sin tapa salía en VERDE mientras su tapa no se pedía nunca. Medido en el
snapshot local: las 13 presentaciones activas tienen frasco y **ninguna** tiene tapa ni caja -- la
capacidad de comprarlas está construida desde el 18-jun y sin un solo dato, que es igual a no
existir (M121).

La regla que ordena esto: **cuando un cálculo excluye cosas, el resultado enumera lo excluido y
por qué** (M124). Un sí/no que esconde tres huecos se lee como "está todo bien".
"""
import json
import os
import re

PROD = 'ZZ PRODUCTO UNION'
FRASCO = 'MEE-ZZU-FRASCO'
TAPA = 'MEE-ZZU-TAPA'
GOTERO = 'MEE-ZZU-GOTERO'
IMPRESO = 'MEE-ZZU-IMPRESO'
FANTASMA = 'MEE-ZZU-NOEXISTE'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        for cod in (FRASCO, TAPA, GOTERO, IMPRESO):
            c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        conn.commit()


def _sembrar(app, tapa=TAPA, caja='', pieza=GOTERO, serigrafiado=IMPRESO):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((FRASCO, 'ZZ frasco'), (TAPA, 'ZZ tapa'),
                          (GOTERO, 'ZZ gotero'), (IMPRESO, 'ZZ frasco impreso')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',0,0,'Activo','2026-08-05')", (cod, desc))
        if serigrafiado:
            c.execute("UPDATE maestro_mee SET material_referencia=? WHERE codigo=?",
                      (serigrafiado, FRASCO))
        if pieza:
            c.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                      " creado_at) VALUES (?,?,'',1,'2026-08-05')", (FRASCO, pieza))
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                  "VALUES (?, 10, 1)", (PROD,))
        # `presentacion_codigo` y `etiqueta` son NOT NULL · el fixture se arma contra el
        # CREATE TABLE real, no contra las columnas que uno recuerda.
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, activo) "
                  "VALUES (?,'ZZU30','ZZ 30 ml',?,?,?,?,1)",
                  (PROD, 30.0, FRASCO, tapa, caja))
        conn.commit()


def _union(admin_client):
    r = admin_client.get('/api/abastecimiento/envases-cobertura')
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j.get('union') is not None, 'la unión no se pudo calcular · ' + str(j.get('aviso'))
    return {x['producto']: x for x in j['union']}, j


def test_la_TAPA_que_falta_se_NOMBRA(app, admin_client, db_clean):
    """El caso medido: frasco puesto, tapa vacía. Antes esto salía en verde."""
    _sembrar(app, tapa='', caja='')
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is False, 'una presentación sin tapa se declaró completa'
    assert 'tapa' in fila['falta'], fila['falta']
    assert 'caja' in fila['falta'], fila['falta']
    _limpiar(app)


def test_una_presentacion_COMPLETA_no_grita(app, admin_client, db_clean):
    """Sin este caso, un diagnóstico que siempre marca algo se vuelve ruido y deja de mirarse."""
    _sembrar(app, tapa=TAPA, caja=GOTERO)
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is True, fila['falta']
    assert fila['falta'] == []
    _limpiar(app)


def test_un_codigo_que_NO_existe_en_el_maestro_se_declara(app, admin_client, db_clean):
    """Una presentación puede apuntar a un código muerto: el campo está lleno pero el motor no
    encuentra nada que comprar. "Tiene tapa" y "tiene una tapa que existe" no son lo mismo."""
    _sembrar(app, tapa=FANTASMA, caja=GOTERO)
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is False
    assert any(FANTASMA in f for f in fila['falta']), fila['falta']
    _limpiar(app)


def test_la_PIEZA_muerta_del_frasco_tambien_se_declara(app, admin_client, db_clean):
    """El gotero vive en `mee_partes`, no en la presentación · si apunta a un código que no
    existe, la recepción no lo puede ingresar y el envasado no lo puede descontar."""
    _sembrar(app, tapa=TAPA, caja=GOTERO, pieza=FANTASMA)
    fila = _union(admin_client)[0][PROD]
    assert any(FANTASMA in f for f in fila['falta']), fila['falta']
    assert any(p['codigo'] == FANTASMA and p['en_maestro'] is False for p in fila['piezas'])
    _limpiar(app)


def test_el_puente_base_a_SERIGRAFIADO_se_reporta(app, admin_client, db_clean):
    """`material_referencia` vacío = lo que vuelve de serigrafía no queda atado a este producto.
    Medido en el snapshot local: está vacío en los 129 envases, o sea que el flujo de marcación
    está desconectado de la compra. Un hueco que no se mide no se cierra."""
    _sembrar(app, serigrafiado=IMPRESO)
    fila = _union(admin_client)[0][PROD]
    assert fila['serigrafiado'] == IMPRESO, fila

    _sembrar(app, serigrafiado='')
    fila = _union(admin_client)[0][PROD]
    assert fila['serigrafiado'] == '', fila
    _limpiar(app)


def test_los_CONTADORES_cuadran_con_el_detalle(app, admin_client, db_clean):
    """El número del encabezado y la lista de abajo salen del MISMO recorrido: si se cuentan
    aparte, un día dicen cosas distintas y no se puede creer en ninguno (M5/M161)."""
    _sembrar(app, tapa='', caja='')
    filas, j = _union(admin_client)
    un = j['union']
    assert j['n_presentaciones'] == len(un)
    assert j['n_completas'] == sum(1 for x in un if x['completo'])
    assert j['n_sin_tapa'] == sum(1 for x in un if not x['tapa'])
    assert j['n_sin_caja'] == sum(1 for x in un if not x['caja'])
    assert j['n_sin_serigrafiado'] == sum(1 for x in un if not x['serigrafiado'])
    _limpiar(app)


def test_lo_que_ya_leia_la_pantalla_NO_cambio(app, admin_client, db_clean):
    """El cambio es ADITIVO (M117): la pantalla de Reparto ya consume `sin_envase`/`no_aplica`
    y no puede romperse porque se agregó el detalle."""
    _sembrar(app)
    j = _union(admin_client)[1]
    for k in ('n_activos', 'n_con_envase', 'n_sin_envase', 'no_aplica', 'sin_envase',
              'con_envase', 'donde_configurar'):
        assert k in j, 'desapareció la llave %s que la pantalla ya usaba' % k
    _limpiar(app)


def test_la_pantalla_PINTA_la_union(app, db_clean):
    """Un endpoint que nadie abre no existe (M121). Y el escáner quita los comentarios antes de
    buscar, o encuentra la prosa del propio autor (M154)."""
    # ⚠ El JS del dashboard se EXTRAE a `DASHBOARD_APP_JS` al importar el módulo (bundle
    # cacheable servido como /planta-app.js). Buscarlo en `DASHBOARD_HTML` da CERO y el test
    # falla con el código correcto: hay que leer el valor FINAL, no el que uno cree que es
    # (M158 · un guard que lee el literal no ve lo que el módulo hace después).
    import templates_py.dashboard_html as D
    H = ((getattr(D, 'DASHBOARD_APP_JS', '') or '')
         + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML)
    js = re.sub(r'//[^\n]*', '', H)
    i = js.find('async function cargarReparto')
    assert i > 0
    bloque = js[i:i + 9000]
    assert 'cov.union' in bloque, 'la pantalla no lee la unión'
    assert 'Serigrafiado' in bloque, 'no muestra el puente base → impreso'
    assert 'cov.aviso' in bloque, 'si la unión no se pudo calcular, la pantalla no lo dice'


# ── ¿este frasco está EN BLANCO? ─────────────────────────────────────────────

def test_un_frasco_de_COLOR_blanco_NO_se_marca_para_serigrafiar(app, admin_client, db_clean):
    """⚠ El test que evita la alerta inútil. Medido en el maestro real: `FRASCO BLANCO CUADRADO`,
    `FRASCO BLANCO PUFF` y `ENVASE REDONDO BLANCO` son frascos de COLOR blanco, no frascos sin
    marcar. Detectarlos por la palabra "blanco" haría gritar la alerta por medio inventario, y una
    alerta que suena siempre deja de mirarse justo el día que importa (M129/M144)."""
    from database import get_db
    _sembrar(app, serigrafiado='')
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE maestro_mee SET descripcion='ZZ FRASCO BLANCO CUADRADO 30ml' "
                     " WHERE codigo=?", (FRASCO,))
        conn.commit()
    fila = _union(admin_client)[0][PROD]
    assert fila['en_blanco'] is False, \
        'marcó un frasco de color blanco como "sin serigrafía" · señal: %s' % fila['senal_blanco']
    assert fila['hay_que_serigrafiar'] is False
    _limpiar(app)


def test_un_frasco_SIN_SERIGRAFIA_si_se_marca(app, admin_client, db_clean):
    """La señal real: `NO PRINT` / `SIN SERIG`, no el color."""
    from database import get_db
    _sembrar(app, serigrafiado='')
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE maestro_mee SET descripcion='ZZ PLASTIC BOTTLE NO PRINT 30ml' "
                     " WHERE codigo=?", (FRASCO,))
        conn.commit()
    fila = _union(admin_client)[0][PROD]
    assert fila['en_blanco'] is True, fila
    assert fila['senal_blanco'], 'no dice QUÉ señal coincidió · sin eso no se puede ajustar'
    assert fila['hay_que_serigrafiar'] is True, 'está en blanco y sin impreso: hay que marcarlo'
    _limpiar(app)


def test_en_blanco_PERO_ya_tiene_su_impreso_no_alerta(app, admin_client, db_clean):
    """Los dos hechos juntos son la alerta. Un frasco en blanco que YA tiene su serigrafiado
    asignado está resuelto; seguir gritando por él es ruido."""
    from database import get_db
    _sembrar(app, serigrafiado=IMPRESO)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE maestro_mee SET descripcion='ZZ FRASCO SIN SERIG 30ml' "
                     " WHERE codigo=?", (FRASCO,))
        conn.commit()
    fila = _union(admin_client)[0][PROD]
    assert fila['en_blanco'] is True
    assert fila['hay_que_serigrafiar'] is False, 'alerta por algo que ya está resuelto'
    _limpiar(app)


def test_el_patron_se_puede_ajustar_SIN_desplegar(app, admin_client, db_clean):
    """Va a aparecer una forma nueva de escribirlo. Una lista escrita a mano en el código se
    pudre y hay que esperar un deploy para arreglarla (M108/M122)."""
    from database import get_db
    _sembrar(app, serigrafiado='')
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE maestro_mee SET descripcion='ZZ FRASCO CRUDO 30ml' WHERE codigo=?",
                     (FRASCO,))
        conn.execute("INSERT INTO app_settings (clave, valor) VALUES ('envase_blanco_patron', ?) "
                     "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", ('CRUDO|NO PRINT',))
        conn.commit()
    try:
        fila = _union(admin_client)[0][PROD]
        assert fila['en_blanco'] is True, 'no tomó el patrón de app_settings'
        assert fila['senal_blanco'] == 'CRUDO'
    finally:
        with app.app_context():
            conn = get_db()
            conn.execute("DELETE FROM app_settings WHERE clave='envase_blanco_patron'")
            conn.commit()
    _limpiar(app)


def test_la_pantalla_AVISA_lo_que_hay_que_serigrafiar(app, db_clean):
    import templates_py.dashboard_html as D
    H = ((getattr(D, 'DASHBOARD_APP_JS', '') or '')
         + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML)
    js = re.sub(r'//[^\n]*', '', H)
    i = js.find('async function cargarReparto')
    bloque = js[i:i + 12000]
    assert 'n_hay_que_serigrafiar' in bloque, 'la pantalla no avisa qué mandar a serigrafiar'
    assert 'senales_envase_blanco' in bloque, 'no dice por qué señal lo detectó'


# ── las VENTAS son la evidencia de que la presentación existe ─────────────────

def _pres_id(app, vol=30.0):
    from database import get_db
    with app.app_context():
        return get_db().execute("SELECT id FROM producto_presentaciones "
                                " WHERE producto_nombre=? AND volumen_ml=?", (PROD, vol)).fetchone()[0]


def _patch(admin_client, pid, **campos):
    import json
    from .conftest import csrf_headers
    campos['id'] = pid
    return admin_client.post('/api/programacion/presentacion-empaque', data=json.dumps(campos),
                             headers=csrf_headers(), content_type='application/json')


def test_la_presentacion_dice_si_VENDE(app, admin_client, db_clean):
    """Sebastián, viendo el modal con datos reales: *"deberías ver cuál de esos realmente tiene
    ventas en Shopify... es parte fundamental"*. En su pantalla, RENOVA C10 mostraba DOS filas de
    15 ml con el MISMO frasco: una dobla la demanda del envase. Cuál sobra no se adivina por el
    nombre, se mira cuál vende."""
    from database import get_db
    _sembrar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM sku_producto_map WHERE sku='ZZ-SKU-30'")
        c.execute("DELETE FROM ventas_diarias WHERE sku='ZZ-SKU-30'")
        c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) "
                  "VALUES ('ZZ-SKU-30', ?, 30, 1)", (PROD,))
        c.execute("INSERT INTO ventas_diarias (sku, fecha, cantidad) "
                  "VALUES ('ZZ-SKU-30', date('now','-10 days'), 44)")
        conn.commit()
    try:
        fila = _union(admin_client)[0][PROD]
        assert fila['ventas_180d'] == 44, fila
        assert 'ZZ-SKU-30' in (fila.get('skus') or []), 'no dice POR QUÉ SKU vendió'
    finally:
        with app.app_context():
            conn = get_db()
            conn.execute("DELETE FROM sku_producto_map WHERE sku='ZZ-SKU-30'")
            conn.execute("DELETE FROM ventas_diarias WHERE sku='ZZ-SKU-30'")
            conn.commit()
    _limpiar(app)


def test_sin_ventas_devuelve_CERO_no_None(app, admin_client, db_clean):
    """Cero y "no se pudo medir" son cosas distintas: un cero inventado se lee como "esta
    presentación no se usa", que es justo la decisión que se está tomando acá (M100)."""
    _sembrar(app)
    fila = _union(admin_client)[0][PROD]
    assert fila['ventas_180d'] == 0, fila
    assert fila['ventas_180d'] is not None
    _limpiar(app)


# ── elegir cuál se usa, y arreglarlo ahí mismo ───────────────────────────────

def test_APAGAR_una_presentacion_la_saca_del_conteo(app, admin_client, db_clean):
    """*"debería poder allí escoger cuál de esas presentaciones sí se usarán para que aparezcan
    en calendario"*. Apagada deja de contar para el calendario y para la compra de envases."""
    from database import get_db
    _sembrar(app, tapa='', caja='')
    pid = _pres_id(app)
    r = _patch(admin_client, pid, activo=False)
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        act = get_db().execute("SELECT COALESCE(activo,1) FROM producto_presentaciones "
                               " WHERE id=?", (pid,)).fetchone()[0]
    assert int(act) == 0, 'no se apagó'
    fila = _union(admin_client)[0][PROD]
    assert fila['activo'] is False
    assert fila['falta'] == [], 'una presentación apagada no puede reportar huecos: es ruido'
    _limpiar(app)


def test_la_apagada_SIGUE_VISIBLE_para_poder_encenderla(app, admin_client, db_clean):
    """Para elegir "cuál se usa" hay que VER las que no se usan. Si se filtraran, apagar una
    sería una operación de un solo sentido."""
    _sembrar(app)
    pid = _pres_id(app)
    _patch(admin_client, pid, activo=False)
    assert PROD in _union(admin_client)[0], 'la presentación apagada desapareció de la vista'
    _patch(admin_client, pid, activo=True)
    assert _union(admin_client)[0][PROD]['activo'] is True, 'no se pudo volver a encender'
    _limpiar(app)


def test_APAGAR_no_BORRA(app, admin_client, db_clean):
    """La presentación puede tener histórico colgando y un DELETE no se deshace."""
    from database import get_db
    _sembrar(app)
    pid = _pres_id(app)
    _patch(admin_client, pid, activo=False)
    with app.app_context():
        n = get_db().execute("SELECT COUNT(*) FROM producto_presentaciones WHERE id=?",
                             (pid,)).fetchone()[0]
    assert n == 1, 'la fila se borró en vez de apagarse'
    _limpiar(app)


def test_asignar_TAPA_desde_el_modal(app, admin_client, db_clean):
    """*"además de una vez ponerle el envase, así ya queda redondo"*."""
    _sembrar(app, tapa='', caja='')
    pid = _pres_id(app)
    r = _patch(admin_client, pid, tapa=TAPA)
    assert r.status_code == 200, r.data[:300]
    fila = _union(admin_client)[0][PROD]
    assert fila['tapa'] == TAPA
    assert 'tapa' not in fila['falta'], fila['falta']
    _limpiar(app)


def test_no_deja_asignar_un_codigo_que_NO_EXISTE(app, admin_client, db_clean):
    """Dejarlo entrar convierte un hueco visible en uno invisible: el campo se ve lleno y el
    motor no encuentra nada que comprar (M100)."""
    _sembrar(app, tapa='')
    pid = _pres_id(app)
    r = _patch(admin_client, pid, tapa=FANTASMA)
    assert r.status_code == 400, r.data[:200]
    assert 'MEE_INEXISTENTE' in r.get_data(as_text=True)
    fila = _union(admin_client)[0][PROD]
    assert fila['tapa'] == '', 'guardó un código inexistente'
    _limpiar(app)


def test_el_PATCH_es_parcial(app, admin_client, db_clean):
    """Mandar el objeto entero desde una pantalla que no muestra todos los campos los pisaría
    con vacío: el default del control ganándole al dato guardado (M85)."""
    _sembrar(app, tapa=TAPA, caja=GOTERO)
    pid = _pres_id(app)
    _patch(admin_client, pid, activo=False)      # sólo el interruptor
    fila = _union(admin_client)[0][PROD]
    assert fila['tapa'] == TAPA, 'el PATCH pisó la tapa'
    assert fila['caja'] == GOTERO, 'el PATCH pisó la caja'
    _limpiar(app)


def test_el_cambio_queda_AUDITADO_con_el_valor_previo(app, admin_client, db_clean):
    """Sin el `antes` no se puede revertir (regla 5 del cerebro)."""
    from database import get_db
    _sembrar(app, tapa='')
    pid = _pres_id(app)
    _patch(admin_client, pid, tapa=TAPA)
    with app.app_context():
        fila = get_db().execute(
            "SELECT COALESCE(antes,''), COALESCE(despues,'') FROM audit_log "
            " WHERE accion='EDITAR_PRESENTACION_EMPAQUE' AND registro_id=? "
            " ORDER BY id DESC LIMIT 1", (str(pid),)).fetchone()
    assert fila, 'no auditó'
    assert TAPA in fila[1], 'el audit no dice qué quedó'
    assert 'tapa' in fila[0], 'el audit no guarda el valor previo · sin eso no se puede revertir'
    _limpiar(app)


# ── "NO LLEVA" es una respuesta, no un hueco ─────────────────────────────────

def test_NO_LLEVA_tapa_deja_de_reportarse_como_hueco(app, admin_client, db_clean):
    """Sebastián, viendo un envase redondo de 150 ml en rojo por tapa y caja: *"digamos este no
    tiene ni tapa ni caja, cómo hacemos con esos"*. El diagnóstico trataba VACÍO como FALTA, y
    así un envase que de verdad no lleva caja se queda en rojo para siempre -- un tablero que
    grita siempre deja de mirarse justo el día que importa (M129/M144)."""
    _sembrar(app, tapa='', caja='')
    pid = _pres_id(app)
    r = _patch(admin_client, pid, sin_tapa=True, sin_caja=True)
    assert r.status_code == 200, r.data[:300]
    fila = _union(admin_client)[0][PROD]
    assert fila['sin_tapa'] is True and fila['sin_caja'] is True
    assert fila['falta'] == [], 'sigue reportando como hueco algo que se declaró que no lleva'
    assert fila['completo'] is True
    _limpiar(app)


def test_VACIO_sigue_siendo_un_hueco(app, admin_client, db_clean):
    """El otro lado: si no se declaró nada, sigue faltando. Sin esto, la bandera sería una
    forma de silenciar el tablero en vez de una respuesta."""
    _sembrar(app, tapa='', caja='')
    fila = _union(admin_client)[0][PROD]
    assert 'tapa' in fila['falta'] and 'caja' in fila['falta'], fila['falta']
    _limpiar(app)


def test_poner_un_CODIGO_apaga_el_no_lleva(app, admin_client, db_clean):
    """Son opuestos: si quedaran los dos, el diagnóstico tendría que elegir a cuál creerle."""
    _sembrar(app, tapa='')
    pid = _pres_id(app)
    _patch(admin_client, pid, sin_tapa=True)
    _patch(admin_client, pid, tapa=TAPA)
    fila = _union(admin_client)[0][PROD]
    assert fila['tapa'] == TAPA
    assert fila['sin_tapa'] is False, 'quedó "no lleva" con un código cargado'
    _limpiar(app)


def test_decir_NO_LLEVA_borra_el_codigo_que_hubiera(app, admin_client, db_clean):
    """Al revés: dejar el código con la bandera puesta deja al motor comprando algo que la
    pantalla dice que no existe (M5)."""
    from database import get_db
    _sembrar(app, tapa=TAPA)
    pid = _pres_id(app)
    _patch(admin_client, pid, sin_tapa=True)
    with app.app_context():
        cod = get_db().execute("SELECT COALESCE(tapa_codigo,'') FROM producto_presentaciones "
                               " WHERE id=?", (pid,)).fetchone()[0]
    assert cod == '', 'quedó el código de tapa con "no lleva" puesto'
    _limpiar(app)


def test_el_contador_no_cuenta_lo_que_NO_LLEVA(app, admin_client, db_clean):
    """Si el KPI siguiera contándolo, el número nunca llegaría a cero y dejaría de usarse."""
    _sembrar(app, tapa='', caja='')
    pid = _pres_id(app)
    antes = _union(admin_client)[1]['n_sin_tapa']
    _patch(admin_client, pid, sin_tapa=True)
    despues = _union(admin_client)[1]['n_sin_tapa']
    assert despues == antes - 1, 'el contador de "sin tapa" no bajó · %s -> %s' % (antes, despues)
    _limpiar(app)


def test_el_centinela_NO_se_guarda_como_codigo(app, db_clean):
    """La pantalla manda `__NO__` para decir "no lleva". Si viajara al campo del código quedaría
    guardado como un material a comprar que no existe (M100)."""
    import templates_py.dashboard_html as D
    js = re.sub(r'//[^\n]*', '',
                (getattr(D, 'DASHBOARD_APP_JS', '') or '') + D.DASHBOARD_HTML)
    i = js.find('async function empqSet')
    bloque = js[i:i + 700]
    assert "__NO__" in bloque, 'la pantalla no distingue "no lleva"'
    assert "body['sin_'+campo]=true" in bloque.replace(' ', '').replace("body['sin_'+campo]=true", "body['sin_'+campo]=true"), \
        'el centinela no se traduce a la bandera'


def test_la_columna_de_la_bandera_existe(app, db_clean):
    """mig 419 · sin la columna, la bandera sería un `except` mudo que deja el rojo puesto."""
    from database import get_db
    with app.app_context():
        get_db().execute("SELECT sin_tapa, sin_caja FROM producto_presentaciones LIMIT 0")


def test_mandar_la_tapa_Y_el_sin_tapa_juntos_no_rompe_el_UPDATE(app, admin_client, db_clean):
    """El error que Catalina vio en producción: *"No se pudo guardar: multiple assignments to
    same column 'sin_tapa'"*.

    El endpoint armaba el SET como una LISTA: la primera vuelta escribía `sin_tapa` y la
    segunda, al ver un código de tapa, lo volvía a escribir para apagarlo. Dos asignaciones a
    la misma columna en un solo UPDATE: **SQLite lo tolera y PostgreSQL lo rechaza**, así que
    fallaba en producción y pasaba en los tests -- el drift de siempre.

    Ahora las asignaciones van en un dict por columna: la última decisión gana, que es la
    semántica buscada (poner un código apaga el "no lleva").
    """
    from database import get_db
    from .conftest import csrf_headers
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre='ZZ DOBLE ASIGN'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual) "
                  "VALUES (?,?,?,?) ON CONFLICT (codigo) DO NOTHING",
                  ('ZZTAP-9', 'ZZ tapa', 'Activo', 0))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, activo, sin_tapa) VALUES (?,?,?,?,?,?)",
                  ('ZZ DOBLE ASIGN', 'ZZD1', 'ZZ 30 ml', 30, 1, 1))
        pid = c.lastrowid
        conn.commit()

    # el modal manda las dos cosas en el mismo guardado
    r = admin_client.post('/api/programacion/presentacion-empaque',
                          json={'id': pid, 'tapa': 'ZZTAP-9', 'sin_tapa': True},
                          headers=csrf_headers())
    assert r.status_code == 200, 'el guardado falló: %s' % r.data[:250]

    with app.app_context():
        fila = get_db().execute(
            "SELECT COALESCE(tapa_codigo,''), COALESCE(sin_tapa,0) "
            "  FROM producto_presentaciones WHERE id=?", (pid,)).fetchone()
    # poner un código APAGA el "no lleva": no pueden convivir, o el motor compra algo que la
    # pantalla dice que no existe (M5)
    assert fila[0] == 'ZZTAP-9', fila
    assert int(fila[1] or 0) == 0, 'quedó "sin tapa" con una tapa cargada · se contradicen'

    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre='ZZ DOBLE ASIGN'")
        conn.execute("DELETE FROM maestro_mee WHERE codigo='ZZTAP-9'")
        conn.commit()


def test_ninguna_columna_se_asigna_DOS_veces(app):
    """Guard estructural: el SET se arma por columna, no acumulando en una lista. Con una lista
    el bug vuelve en cuanto alguien agregue otra regla cruzada."""
    import io as _io
    import os as _os
    import re as _re
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    s = _io.open(_os.path.join(raiz, 'api', 'blueprints', 'programacion.py'), encoding='utf-8').read()
    i = s.find("def presentacion_empaque")
    if i < 0:
        i = s.find("'/api/programacion/presentacion-empaque'")
    j = s.find('\n@bp.route', i + 10)
    bloque = _re.sub(r'^\s*#[^\n]*$', '', s[i:j], flags=_re.M)
    assert 'asign[' in bloque, 'volvió a acumular el SET en una lista'
    assert "sets.append" not in bloque, (
        'quedó un `sets.append` · esa es la forma que permite asignar dos veces la misma columna')
