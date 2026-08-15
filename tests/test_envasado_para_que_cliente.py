"""La lista de Envasado dice PARA QUIÉN es el lote (Sebastián 15-ago-2026).

*"que aparezca foto con cantidades que son para cada cliente en el envasado"*.

El dato existía y se mostraba **dentro** del legajo, pero para verlo había que abrir
orden por orden; en el piso lo que se mira es la LISTA, y ahí un lote con unidades
de un cliente se veía idéntico a uno de ÁNIMUS.

Dos cosas que este guard fija:

1. La orden trae sus clientes con unidades y con el frasco que le corresponde a cada
   uno (con foto: un código `MEE-ENV-012` no le dice nada al operario, la foto sí).
2. Se calcula con consultas AGREGADAS para toda la lista. Pedir el detalle por fila
   desde el navegador es exactamente lo que satura los tres workers y deja la
   pantalla en "Cargando" (M43): el guard cuenta las consultas.
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-CLIENTE-OF"


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _lote_con_cliente(app):
    """Un legajo de envasado cuyo lote lleva unidades de un cliente con su frasco."""
    for sql in ("DELETE FROM pedidos_b2b_lote WHERE cliente_nombre LIKE 'ZCLI%'",
                "DELETE FROM pedidos_b2b WHERE cliente_id LIKE 'ZCLI%'",
                "DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-CLIENTE%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-CLIENTE%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-CLIENTE%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-CLIENTE%'",
                "DELETE FROM maestro_mee WHERE codigo='ZCLI-ENV-30'"):
        try:
            _exec(sql)
        except Exception:
            pass
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-CLI','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-CLI','Agua',100,1000)", (PRODUCTO,))
    _exec("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado, imagen_url) "
          "VALUES ('ZCLI-ENV-30','Frasco del cliente 30 ml',0,'Activo','/static/frasco.png')")
    pp = _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, "
               "cantidad_kg, estado, origen) VALUES (?, date('now'), 1, 30, 'pendiente', 'eos_plan')",
               (PRODUCTO,))
    # El aporte cuelga de un pedido real (la tabla lo exige, y así debe ser: un aporte
    # sin pedido sería una unidad comprometida con nadie).
    ped = _exec("INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, "
                "cantidad_uds, ml_unidad, fecha_estimada, estado, urgencia, envase_codigo, "
                "creado_at_utc, creado_por) VALUES ('ZCLI1','ZCLIENTE PRUEBA',?,700,30,"
                "'2026-12-01','confirmado','media','ZCLI-ENV-30','2026-08-15T09:00:00Z','test')",
                (PRODUCTO,))
    _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, cliente_nombre, "
          "unidades_aporte, ml_unidad, envase_codigo, modo) VALUES (?,?,?,?,?,?,?)",
          (ped, pp, "ZCLIENTE PRUEBA", 700, 30, "ZCLI-ENV-30", "lote_dedicado"))

    c = _login(app)
    c.post("/api/brd/mbr/generar-desde-formula",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    c.post("/api/brd/mbr/cargar-instructivo",
           json={"producto": PRODUCTO, "fase": "envasado",
                 "pasos": ["Paso 1. Llenar.", "Paso 2. Sellar."]}, headers=_h())
    c.post("/api/brd/mbr/preparar-aprobado",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": "LOTE-CLI-1", "fase": "envasado",
                     "produccion_id": pp}, headers=_h())
    assert r.status_code in (200, 201), r.data
    ebr_id = (r.get_json().get("id") or r.get_json().get("ebr_id"))
    # el legajo tiene que quedar colgado de esa producción · si no, no hay de dónde
    # sacar los clientes (y el test estaría midiendo otra cosa)
    _exec("UPDATE ebr_ejecuciones SET produccion_id=? WHERE id=?", (pp, ebr_id))
    return c, ebr_id


def test_la_lista_de_envasado_dice_para_que_cliente_es(app, db_clean):
    c, ebr_id = _lote_con_cliente(app)
    d = c.get("/api/brd/ordenes-unificadas?fase=envasado").get_json()
    mia = [o for o in d["ordenes"] if o.get("ebr_id") == ebr_id]
    assert mia, "la orden no aparece en la lista de envasado"
    cli = mia[0].get("clientes") or []
    assert cli, "la orden no dice para qué cliente es: %s" % mia[0]
    assert cli[0]["cliente"] == "ZCLIENTE PRUEBA"
    assert cli[0]["unidades"] == 700
    assert cli[0]["envase_codigo"] == "ZCLI-ENV-30", cli[0]
    assert cli[0]["envase_foto"], "sin la foto, el operario tiene que adivinar el frasco"
    assert mia[0]["unidades_clientes"] == 700


def test_no_hace_una_consulta_por_orden():
    """Pedir el detalle fila por fila es lo que tumba la pantalla (M43).

    Es estructural: no necesita sembrar nada, y así no compite por el lote con el
    test de arriba (dos legajos de la misma fase no pueden llevar el mismo lote)."""
    fuente = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "api", "blueprints", "brd.py"), encoding="utf-8").read()
    i = fuente.find("def ordenes_unificadas")
    j = fuente.find("\n@bp.route", i + 10)
    cuerpo = fuente[i:j if j > 0 else len(fuente)]
    # el bloque de clientes tiene que estar FUERA del `for it in items`
    k = cuerpo.find("clientes del lote fallo")
    m = cuerpo.find("for it in items:")
    assert k > 0 and m > 0, "no se encontró el bloque de clientes o el loop"
    assert k < m, ("la consulta de clientes quedó dentro del loop por orden: "
                   "eso es una consulta por fila")


def test_la_tarjeta_pinta_el_cliente_con_su_foto(app, db_clean):
    """Un dato que el backend manda y la pantalla no pinta no existe (M115)."""
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    pub = app.test_client()
    for src in re.findall(r'<script[^>]+src="(/[^"?]+)', html):
        rj = pub.get(src)
        if rj.status_code == 200:
            html += rj.data.decode("utf-8", "replace")
    assert "o.clientes&&o.clientes.length" in html, "la tarjeta no mira los clientes"
    assert "envase_foto" in html, "la tarjeta no usa la foto del frasco del cliente"
    assert "frasco de ÁNIMUS" in html, (
        "un cliente sin frasco propio lleva el de ÁNIMUS y la tarjeta debería decirlo")
