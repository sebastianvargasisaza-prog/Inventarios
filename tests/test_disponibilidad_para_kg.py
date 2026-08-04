# -*- coding: utf-8 -*-
"""¿Alcanza la MP y los ENVASES para los kilos que estoy por programar? (4-ago)

Sebastián, sobre el modal Programar: *"que diga la materia prima si alcanza para la próxima
producción y los envases"*.

Lo que había contestaba otra pregunta, y con datos inflados:
  · calculaba contra UN lote del tamaño del maestro de fórmulas, no contra los kilos que el
    usuario va a programar;
  · sumaba el stock SIN excluir cuarentena, vencido ni rechazado -- o sea decía "listo para
    producir" con material que la producción no puede consumir;
  · usaba los gramos por lote en vez del porcentaje (la base que ya dio descuentos ~1000x
    cortos · M16/M50/M71);
  · y NO miraba los envases.

Y la trampa de la serigrafía, que es la que más importa acá: cuando un envase se manda a
marcar su Salida YA se registró, así que el stock canónico no lo cuenta. Restarlo otra vez
sería descontarlo dos veces -- el mismo doble descuento que reportó Catalina. Se INFORMA.
"""
PROD = 'ZZDISP PRODUCTO'
MP1, MP2 = 'ZZDISP-MP1', 'ZZDISP-MP2'
FRASCO, TAPA = 'ZZDISP-FR', 'ZZDISP-TP'


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM movimientos WHERE material_id LIKE 'ZZDISP%'")
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZDISP%'")
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'ZZDISP%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZDISP%'")
        c.execute("DELETE FROM marcacion_ordenes WHERE base_codigo LIKE 'ZZDISP%'")
        conn.commit()


def _sembrar(app, stock_mp1=100000, estado_mp1='VIGENTE', stock_frasco=0):
    """Fórmula al 50/50 con lote base de 10 kg, y stock a elección."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) "
                  "VALUES (?,1,10)", (PROD,))
        for cod, nom, pct in ((MP1, 'Activo uno', 50.0), (MP2, 'Activo dos', 50.0)):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo, controla_stock) "
                      "VALUES (?,?,1,1)", (cod, nom))
            c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                      "porcentaje, cantidad_g_por_lote) VALUES (?,?,?,?,0)", (PROD, cod, nom, pct))
        for cod, cant, est in ((MP1, stock_mp1, estado_mp1), (MP2, 900000, 'VIGENTE')):
            c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                      "lote, fecha, estado_lote) VALUES (?,?, 'Entrada', ?, 'L1', "
                      "date('now','-5 hours'), ?)", (cod, 'x', cant, est))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, tapa_codigo, ventas_mes_referencia, "
                  "activo) VALUES (?, 'ZZDISP-P50', '50 ml', 50, ?, ?, 100, 1)",
                  (PROD, FRASCO, TAPA))
        for cod, st in ((FRASCO, stock_frasco), (TAPA, 5000)):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual) "
                      "VALUES (?,?, 'Activo', 0)", (cod, 'Envase ' + cod))
            if st:
                c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                          "lote_ref, responsable) VALUES (?, 'Entrada', ?, 'und','SEED','t')",
                          (cod, st))
        conn.commit()


def _disp(app, kg):
    from database import get_db
    from blueprints.plan import disponibilidad_para_kg
    with app.app_context():
        return disponibilidad_para_kg(get_db(), PROD, kg)


# ── materia prima ────────────────────────────────────────────────────────────

def test_contesta_por_LOS_KILOS_que_voy_a_programar(app, db_clean):
    """El lote de la fórmula es de 10 kg · si programo 60, la cuenta va por 60."""
    _limpiar(app); _sembrar(app)
    r = _disp(app, 60)
    g = {i['codigo']: i['necesario_g'] for i in r['mp']['items']}
    assert g[MP1] == 30000.0, 'al 50 por ciento de 60 kg le tocan 30.000 g, no el lote de la fórmula'
    assert g[MP2] == 30000.0


def test_al_DOBLE_de_kilos_el_doble_de_materia_prima(app, db_clean):
    """Con dientes: si contestara por un lote fijo, este número no se movería."""
    _limpiar(app); _sembrar(app)
    uno = sum(i['necesario_g'] for i in _disp(app, 30)['mp']['items'])
    dos = sum(i['necesario_g'] for i in _disp(app, 60)['mp']['items'])
    assert abs(dos - uno * 2) < 0.5, 'la cuenta no escala con los kilos'


def test_la_materia_prima_en_CUARENTENA_no_cuenta_como_disponible(app, db_clean):
    """El hallazgo grave: el bloque verde sumaba stock que el FEFO no puede consumir, así que
    decía "listo para producir" con material que Calidad todavía no liberó."""
    _limpiar(app); _sembrar(app, stock_mp1=100000, estado_mp1='CUARENTENA')
    r = _disp(app, 10)
    it = next(i for i in r['mp']['items'] if i['codigo'] == MP1)
    assert it['disponible_g'] == 0.0, 'contó como disponible material en cuarentena'
    assert it['estado'] == 'FALTA'
    assert r['mp']['estado'] == 'FALTA'


def test_con_stock_VIGENTE_el_mismo_material_SI_alcanza(app, db_clean):
    """Dientes al revés: si excluyera de más diría que falta todo, y sería igual de inútil."""
    _limpiar(app); _sembrar(app, stock_mp1=100000, estado_mp1='VIGENTE')
    r = _disp(app, 10)
    assert r['mp']['estado'] == 'OK' and r['mp']['n_faltan'] == 0


def test_DECLARA_lo_que_el_calculo_deja_afuera(app, db_clean):
    """Un total que excluye cosas sin nombrarlas se lee como un faltante (M124)."""
    _limpiar(app); _sembrar(app)
    r = _disp(app, 10)
    ex = [e.lower() for e in r['mp']['excluye']]
    for estado in ('cuarentena', 'vencido', 'rechazado', 'bloqueado'):
        assert any(estado in e for e in ex), 'no declara que excluye ' + estado


def test_sin_formula_NO_inventa_un_veredicto(app, db_clean):
    _limpiar(app)
    r = _disp(app, 50)
    assert r['mp']['estado'] == 'SIN_FORMULA' and r['mp']['nota']


# ── envases ──────────────────────────────────────────────────────────────────

def test_dice_cuantos_FRASCOS_y_TAPAS_hacen_falta(app, db_clean):
    """60 kg en frascos de 50 ml son 1.200 unidades · y la tapa cuenta también."""
    _limpiar(app); _sembrar(app, stock_frasco=800)
    e = _disp(app, 60)['envases']
    por_tipo = {i['tipo']: i for i in e['items']}
    assert por_tipo['frasco']['necesarias'] == 1200
    assert por_tipo['tapa']['necesarias'] == 1200
    assert por_tipo['frasco']['hay'] == 800 and por_tipo['frasco']['falta'] == 400
    assert e['estado'] == 'FALTA'


def test_lo_que_esta_en_SERIGRAFIA_se_informa_pero_NO_se_resta(app, db_clean):
    """La trampa: al enviar a marcar la Salida YA se registró, así que el stock no lo cuenta.
    Restarlo otra vez sería el doble descuento que reportó Catalina."""
    from database import get_db
    _limpiar(app); _sembrar(app, stock_frasco=1000)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO marcacion_ordenes (base_codigo, serigrafiado_codigo, "
                  "cantidad_enviada, estado, creado_por) VALUES (?,?,300,'enviado','t')",
                  (FRASCO, FRASCO + '-S'))
        conn.commit()
    fr = next(i for i in _disp(app, 10)['envases']['items'] if i['tipo'] == 'frasco')
    assert fr['hay'] == 1000, 'le restó al saldo lo que está en serigrafía · eso lo cuenta dos veces'
    assert fr['en_marcacion'] == 300, 'no informa lo que está afuera en marcación'


def test_sin_presentacion_configurada_lo_DICE(app, db_clean):
    """Sin volumen y envase no hay forma de saber cuántos frascos hacen falta · decirlo es la
    respuesta correcta; inventar un número, no."""
    from database import get_db
    _limpiar(app); _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        conn.commit()
    e = _disp(app, 60)['envases']
    assert e['estado'] == 'SIN_PRESENTACION' and 'presentaci' in e['nota']
    assert e['items'] == []


def test_el_endpoint_responde_y_cambia_con_los_kg(app, db_clean):
    from .conftest import TEST_PASSWORD, csrf_headers
    _limpiar(app); _sembrar(app)
    c = app.test_client()
    assert c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
                  headers=csrf_headers(), follow_redirects=False).status_code == 302
    a = c.get('/api/plan/disponibilidad-para-kg?producto=' + PROD + '&kg=30').get_json()
    b = c.get('/api/plan/disponibilidad-para-kg?producto=' + PROD + '&kg=60').get_json()
    assert a['ok'] and b['ok']
    ga = sum(i['necesario_g'] for i in a['mp']['items'])
    gb = sum(i['necesario_g'] for i in b['mp']['items'])
    assert abs(gb - ga * 2) < 0.5
