# -*- coding: utf-8 -*-
"""El ciclo del despacho: cuándo salió, con qué guía y si LLEGÓ.

Gerencia (17-ago): *"hoy cerramos el ciclo cuando el pedido SALE, no cuando LLEGA. Sin eso no
sabemos cuántos pedidos llegaron de verdad."*

`animus_shopify_orders` tenía 24 columnas y **ninguna** decía nada de esto, aunque Shopify lo
manda todo en `fulfillments[]` y el sync lo tiraba (PASO 0, medido el 18-ago).

Lo que estos guards fijan, y es lo delicado del indicador: **lo que la transportadora no reporta
NO se cuenta como incumplido**. Se declara aparte. Un pedido sin noticia de entrega y uno que no
llegó son cosas distintas, y confundirlos convierte el indicador en una opinión (M100/M124).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _sembrar(filas):
    """Se limpia ANTES: este test mide CONTEOS sobre toda la tabla, así que lo que dejó otro
    archivo lo haría medir cualquier cosa (M103/M165)."""
    cn = _cn()
    try:
        cn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZIND-%'")
        for f in filas:
            cn.execute(
                "INSERT INTO animus_shopify_orders "
                "(shopify_id, nombre, total, estado, estado_pago, creado_en, "
                " despachado_at, guia, transportadora, entregado_at, estado_envio) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)", f)
        cn.commit()
    finally:
        cn.close()


def _ind(cli, dias=30):
    r = cli.get("/api/indicadores/despachos?dias=%d" % dias)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    return r.get_json() or {}


def test_el_ciclo_del_despacho_se_extrae_de_shopify(app):
    """La extracción es lo único que puede equivocarse acá, y se puede medir sin red.

    ⚠ Depende de la fixture `app` sólo para que `api/` esté en el path: un `sys.path.insert` a
    nivel de módulo corre en la COLECCIÓN, antes de que ninguna fixture prepare el entorno, y
    rompe el login de los archivos siguientes (M165/M184).
    """
    from shopify_client import ciclo_despacho

    # sin fulfillments: todo vacío · no se inventa nada
    assert ciclo_despacho({"fulfillments": []}) == ('', '', '', '', '')
    assert ciclo_despacho({}) == ('', '', '', '', '')

    # despachado pero SIN noticia de entrega: hay guía, no hay entregado_at
    # ⚠ lleva `updated_at` A PROPÓSITO: sin él, "inventar la entrega" no produciría ningún
    # valor y el guard pasaría verde con el bug puesto (M96).
    d, g, t, e, se = ciclo_despacho({"fulfillments": [
        {"created_at": "2026-08-10T10:00:00-05:00", "updated_at": "2026-08-12T09:00:00-05:00",
         "tracking_number": "ABC123", "tracking_company": "Servientrega",
         "shipment_status": None}]})
    assert g == "ABC123" and t == "Servientrega"
    assert d, "no capturó la fecha de despacho"
    assert e == '', "inventó una entrega que la transportadora no reportó"

    # entregado: la transportadora lo reporta
    d, g, t, e, se = ciclo_despacho({"fulfillments": [
        {"created_at": "2026-08-10T10:00:00-05:00", "updated_at": "2026-08-13T16:00:00-05:00",
         "tracking_number": "X1", "shipment_status": "delivered"}]})
    assert e, "no registró la entrega que la transportadora SÍ reportó"
    assert se == "delivered"

    # un fulfillment CANCELADO no cuenta
    assert ciclo_despacho({"fulfillments": [
        {"created_at": "2026-08-10T10:00:00-05:00", "status": "cancelled",
         "tracking_number": "NO"}]}) == ('', '', '', '', '')

    # tracking_numbers (plural) es el otro nombre que manda Shopify
    _, g, _, _, _ = ciclo_despacho({"fulfillments": [
        {"created_at": "2026-08-10T10:00:00-05:00", "tracking_numbers": ["P9"]}]})
    assert g == "P9", "perdió la guía cuando viene en plural"


def test_lo_que_nadie_reporto_no_se_cuenta_como_incumplido(app, db_clean):
    cli = _login(app)
    hoy = "date('now','-5 hours')"
    cn = _cn()
    try:
        base = cn.execute("SELECT date('now','-5 hours','-3 day')").fetchone()[0]
        ent = cn.execute("SELECT date('now','-5 hours','-1 day')").fetchone()[0]
    finally:
        cn.close()
    _sembrar([])
    base_fuera = _ind(cli)["indicadores"]["promesa_fuera"]
    _sembrar([
        # 1 entregado con noticia · 2 despachados sin noticia · 1 sin despachar
        ('ZIND-1', 'a', 100, '', 'paid', base, base, 'G1', 'Serv', ent, 'delivered'),
        ('ZIND-2', 'b', 100, '', 'paid', base, base, 'G2', 'Serv', '', ''),
        ('ZIND-3', 'c', 100, '', 'paid', base, base, 'G3', 'Serv', '', 'in_transit'),
        ('ZIND-4', 'd', 100, '', 'paid', base, '', '', '', '', ''),
    ])
    j = _ind(cli)
    ind, cob = j["indicadores"], j["cobertura_entrega"]

    assert ind["despachados"] >= 3, ind
    assert ind["entregados_confirmados"] >= 1, ind
    assert ind["despachados_sin_confirmacion"] >= 2, ind

    # LA regla: los sin noticia se DECLARAN, no engordan el incumplimiento
    assert cob["sin_dato"] >= 2, ("los pedidos sin noticia de entrega no se están declarando", cob)
    # También en relativo: otro archivo puede tener un pedido entregado tarde, y eso no es
    # asunto de este test (M227).
    assert ind["promesa_fuera"] == base_fuera, (
        "está contando como incumplido un pedido del que nadie reportó la entrega",
        base_fuera, ind)
    assert ind["promesa_cumple"] >= 1, ind
    # La invariante que de verdad protege el indicador: la promesa se mide SOBRE LOS
    # ENTREGADOS y sobre nadie más. Si alguna vez empieza a contar los que no tienen noticia,
    # la suma se despega del universo medible y el número pasa a ser una opinión.
    assert ind["promesa_cumple"] + ind["promesa_fuera"] == ind["entregados_confirmados"], (
        "la promesa se está midiendo sobre pedidos sin noticia de entrega", ind)


def test_el_pendiente_dice_cuantos_dias_lleva(app, db_clean):
    """"3 pendientes" se lee igual el día 1 que el día 47 · sin la edad, la alerta se ignora
    (M129)."""
    cli = _login(app)
    cn = _cn()
    try:
        viejo = cn.execute("SELECT date('now','-5 hours','-12 day')").fetchone()[0]
    finally:
        cn.close()
    _sembrar([('ZIND-9', 'z', 100, '', 'paid', viejo, '', '', '', '', '')])
    ind = _ind(cli)["indicadores"]
    assert ind["pendientes_despacho"] >= 1, ind
    assert (ind["pendiente_mas_viejo_dias"] or 0) >= 11, (
        "no dice hace cuántos días espera el pendiente más viejo", ind)


def test_las_canceladas_no_cuentan(app, db_clean):
    """Shopify NO escribe 'cancelled' en fulfillment_status · el sync lo traduce (M108).

    ⚠ Se mide en RELATIVO (antes vs después), nunca con un conteo absoluto: `recibidos` cuenta
    TODA la tabla y hay varios archivos de test que siembran pedidos ahí, así que un
    `== 0` pasa aislado y falla en el gate según con quién comparta worker (M227/M103).
    """
    cli = _login(app)
    cn = _cn()
    try:
        hoy = cn.execute("SELECT date('now','-5 hours')").fetchone()[0]
    finally:
        cn.close()
    # La línea base se toma DESPUÉS de limpiar lo de este archivo: si no, cuenta las filas que
    # dejó el test anterior y el delta mide la limpieza en vez de la cancelada.
    _sembrar([])
    antes = _ind(cli)["indicadores"]["recibidos"]
    _sembrar([('ZIND-C', 'x', 100, 'cancelled', 'paid', hoy, '', '', '', '', '')])
    despues = _ind(cli)["indicadores"]["recibidos"]
    assert despues == antes, (
        "una orden cancelada se está contando como pedido", antes, despues)


def test_un_pedido_despachado_sin_fecha_NO_es_un_pendiente(app, db_clean):
    """El día del deploy la pantalla decía "4.652 pendientes de despacho" en producción.

    No estaban pendientes: `despachado_at` es de la mig 440 y sólo se llena cuando el sync
    vuelve a pasar por el pedido, así que todo lo anterior lo tenía vacío. Contar por ese campo
    convertía la falta de dato en una crisis (M5/M100).

    El discriminador que existe desde siempre es `estado` (el `fulfillment_status` de Shopify).
    Lo que falte de FECHA se declara en `cobertura_despacho`, no se disfraza de pendiente (M124).
    """
    cli = _login(app)
    cn = _cn()
    try:
        hoy = cn.execute("SELECT date('now','-5 hours')").fetchone()[0]
    finally:
        cn.close()
    _sembrar([])
    base = _ind(cli)["indicadores"]

    _sembrar([
        # despachado según Shopify, pero SIN la fecha nueva (el caso de todo lo viejo)
        ('ZIND-V1', 'v1', 100, 'fulfilled', 'paid', hoy, '', '', '', '', ''),
        # pendiente de verdad: Shopify tampoco lo dio por despachado
        ('ZIND-V2', 'v2', 100, '', 'paid', hoy, '', '', '', '', ''),
    ])
    ind = _ind(cli)["indicadores"]
    cob = _ind(cli)["cobertura_despacho"]

    assert ind["despachados"] == base["despachados"] + 1, (
        "un pedido que Shopify da por despachado no se está contando como despachado", ind)
    assert ind["pendientes_despacho"] == base["pendientes_despacho"] + 1, (
        "está contando como PENDIENTE un pedido despachado al que sólo le falta la fecha", ind)
    assert cob["sin_fecha"] >= 1, (
        "no declara cuántos despachados están sin fecha · sin eso, el hueco de datos se lee "
        "como un dato", cob)
