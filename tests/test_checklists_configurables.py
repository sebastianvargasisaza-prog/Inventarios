"""El director técnico configura las verificaciones, igual que en MyBatch (15-ago-2026).

En MyBatch los ítems del despeje de línea y los controles de atributos son pantallas de
configuración del DT. En EOS eran constantes del código: cambiar un ítem exigía un
despliegue y el DT dependía de que alguien lo hiciera por él.

Se hace configurable SIN perder lo que el código daba gratis, y eso es lo que fija este
guard:
  · sin configurar, todo sigue EXACTAMENTE igual que antes (la tabla nace vacía · M117);
  · el texto de lo YA FIRMADO no cambia nunca, aunque el procedimiento se edite después
    (M105 · cambiarle el texto a un registro firmado es falsificarlo);
  · un ítem retirado del procedimiento sigue apareciendo en los lotes donde se registró;
  · una clave ya firmada NUNCA se recicla para un ítem nuevo;
  · quien EJECUTA el procedimiento no lo DEFINE: un operario recibe 403;
  · una lista vacía se rechaza: eso no es relajar un control, es borrarlo (M124/M126).
"""
import json
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, (user, r.data[:200])
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM checklist_items",
                "DELETE FROM ebr_despeje_items WHERE ebr_id IN "
                "(SELECT id FROM ebr_ejecuciones WHERE lote LIKE 'ZCHK%')",
                "DELETE FROM ebr_ejecuciones WHERE lote LIKE 'ZCHK%'",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZCHK%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _post(c, url, payload):
    return c.post(url, data=json.dumps(payload), content_type="application/json",
                  headers=csrf_headers())


def _guardar(c, tipo, ambito, items, motivo="prueba"):
    return _post(c, "/api/brd/checklists",
                 {"tipo": tipo, "ambito": ambito, "items": items, "motivo": motivo})


def _ver(c, tipo, ambito):
    r = c.get("/api/brd/checklists?tipo=%s&ambito=%s" % (tipo, ambito))
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_sin_configurar_manda_la_lista_de_fabrica(app, db_clean):
    """La tabla nace vacía a propósito: todo funciona igual que antes (M117)."""
    _limpiar()
    c = _login(app, "sebastian")
    j = _ver(c, "despeje", "dispensacion")
    assert j["origen"] == "fabrica", j["origen"]
    assert len(j["items"]) == 12, len(j["items"])
    assert j["items"][0]["texto"].startswith("El área está libre"), j["items"][0]
    ipc = _ver(c, "ipc", "acondicionamiento")
    assert ipc["origen"] == "fabrica"
    assert len(ipc["items"]) == 14, len(ipc["items"])


def test_el_dt_configura_y_el_legajo_lo_ve(app, db_clean):
    """Lo que el DT guarda es lo que el piso ejecuta: un solo lugar decide (M3)."""
    _limpiar()
    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base]
    items[0]["texto"] = "ZCHK El área quedó libre del producto anterior"
    items.append({"texto": "ZCHK Verificar el sello de la tolva"})
    r = _guardar(c, "despeje", "dispensacion", items)
    assert r.status_code == 200, r.data[:300]
    j = _ver(c, "despeje", "dispensacion")
    assert j["origen"] == "configurado", j
    assert j["ultimo_por"] == "hernando", j["ultimo_por"]
    textos = [i["texto"] for i in j["items"]]
    assert textos[0] == "ZCHK El área quedó libre del producto anterior"
    assert "ZCHK Verificar el sello de la tolva" in textos
    assert len(j["items"]) == 13


def test_el_texto_de_lo_ya_firmado_no_cambia(app, db_clean):
    """Cambiarle el texto a un registro firmado es falsificarlo (M105).

    El operario firmó el ítem 0 con SU texto; el DT lo reescribe después. En el legajo
    tiene que seguir viéndose lo que la persona tenía delante cuando firmó.
    """
    _limpiar()
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES ('ZCHK PRODUCTO',1,'aprobado',1000,'sebastian')")
    ebr = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,'ZCHK-L1','ZCHK-L1','en_proceso','fabricacion','sebastian',"
                "'2026-08-01 10:00:00',1000)", (mbr,))
    firmado = "El área está libre del producto anterior, TAL COMO SE FIRMÓ"
    _exec("INSERT INTO ebr_despeje_items (ebr_id, item_idx, item_texto, cumple, "
          "registrado_por, registrado_at_utc, etapa) "
          "VALUES (?,0,?,1,'mayerlin','2026-08-01 11:00:00','dispensacion')", (ebr, firmado))

    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base]
    items[0]["texto"] = "ZCHK TEXTO NUEVO QUE NADIE FIRMÓ"
    assert _guardar(c, "despeje", "dispensacion", items).status_code == 200

    from api.blueprints.brd import despeje_checklist
    from api.database import get_db
    with app.app_context():
        filas = despeje_checklist(get_db(), ebr, "dispensacion")
    fila0 = [f for f in filas if f["idx"] == 0][0]
    assert fila0["texto"] == firmado, (
        "le cambió el texto a un registro ya firmado: %r" % fila0["texto"])
    # y el ítem que nadie tocó sí muestra el texto nuevo del procedimiento vigente
    assert any(f["texto"] == "ZCHK TEXTO NUEVO QUE NADIE FIRMÓ" for f in filas) is False, filas
    # (el 0 está firmado, así que el texto nuevo no se ve en ESE ítem · es lo correcto)


def test_un_item_retirado_sigue_en_el_lote_donde_se_registro(app, db_clean):
    """Un registro regulado no se borra porque el procedimiento cambie después."""
    _limpiar()
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES ('ZCHK RETIRO',1,'aprobado',1000,'sebastian')")
    ebr = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,'ZCHK-L2','ZCHK-L2','en_proceso','fabricacion','sebastian',"
                "'2026-08-01 10:00:00',1000)", (mbr,))
    _exec("INSERT INTO ebr_despeje_items (ebr_id, item_idx, item_texto, cumple, "
          "registrado_por, registrado_at_utc, etapa) "
          "VALUES (?,11,'¿Cuenta con los EPP requeridos?',1,'mayerlin',"
          "'2026-08-01 11:00:00','dispensacion')", (ebr,))

    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    # el DT retira el último ítem del procedimiento
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base[:-1]]
    r = _guardar(c, "despeje", "dispensacion", items)
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()["retirados"] == 1, r.get_json()

    from api.blueprints.brd import despeje_checklist
    from api.database import get_db
    with app.app_context():
        filas = despeje_checklist(get_db(), ebr, "dispensacion")
    hist = [f for f in filas if f["idx"] == 11]
    assert hist, "el ítem retirado desapareció del lote donde se registró"
    assert hist[0]["historico"] is True, hist[0]
    assert hist[0]["cumple"] == 1
    assert "EPP" in hist[0]["texto"]


def test_una_clave_ya_firmada_nunca_se_recicla(app, db_clean):
    """Reciclar un `item_idx` le cambiaría el significado a lo que se firmó con él."""
    _limpiar()
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES ('ZCHK CLAVE',1,'aprobado',1000,'sebastian')")
    ebr = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,'ZCHK-L3','ZCHK-L3','en_proceso','fabricacion','sebastian',"
                "'2026-08-01 10:00:00',1000)", (mbr,))
    # un lote viejo firmó un ítem 20 que ya no está en el procedimiento
    _exec("INSERT INTO ebr_despeje_items (ebr_id, item_idx, item_texto, cumple, "
          "registrado_por, registrado_at_utc, etapa) "
          "VALUES (?,20,'Item viejo firmado',1,'mayerlin','2026-08-01 11:00:00','dispensacion')",
          (ebr,))
    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base]
    items.append({"texto": "ZCHK item nuevo del DT"})
    assert _guardar(c, "despeje", "dispensacion", items).status_code == 200
    j = _ver(c, "despeje", "dispensacion")
    nuevo = [i for i in j["items"] if i["texto"] == "ZCHK item nuevo del DT"][0]
    assert nuevo["clave"] != "20", "recicló la clave de un ítem ya firmado"
    assert int(nuevo["clave"]) > 20, nuevo["clave"]


def test_quien_ejecuta_el_procedimiento_no_lo_define(app, db_clean):
    """Segregación de funciones: el operario ejecuta, el DT define (403 al operario)."""
    _limpiar()
    c = _login(app, "mayerlin")
    r = _guardar(c, "despeje", "dispensacion", [{"texto": "cambio del operario"}])
    assert r.status_code == 403, r.status_code
    assert r.get_json().get("codigo") == "SIN_PERMISO_CHECKLIST", r.get_json()
    # y la pantalla se lo dice en vez de dejarlo apretar un botón que da 403
    assert _ver(c, "despeje", "dispensacion")["puede_configurar"] is False


def test_no_se_puede_dejar_un_legajo_sin_verificaciones(app, db_clean):
    """Una lista vacía no es relajar un control: es borrarlo (M124/M126)."""
    _limpiar()
    c = _login(app, "hernando")
    r = _guardar(c, "despeje", "dispensacion", [])
    assert r.status_code == 400, r.status_code
    assert r.get_json().get("codigo") == "CHECKLIST_VACIO", r.get_json()
    assert _ver(c, "despeje", "dispensacion")["origen"] == "fabrica"


def test_restaurar_vuelve_a_fabrica(app, db_clean):
    """Volver atrás también es una decisión, y también se audita."""
    _limpiar()
    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base]
    items[0]["texto"] = "ZCHK cambio a revertir"
    assert _guardar(c, "despeje", "dispensacion", items).status_code == 200
    assert _ver(c, "despeje", "dispensacion")["origen"] == "configurado"
    r = _post(c, "/api/brd/checklists/restaurar", {"tipo": "despeje", "ambito": "dispensacion"})
    assert r.status_code == 200, r.data[:200]
    j = _ver(c, "despeje", "dispensacion")
    assert j["origen"] == "fabrica", j["origen"]
    assert j["items"][0]["texto"].startswith("El área está libre")


def test_los_controles_configurados_llegan_al_legajo_y_a_la_cola_de_calidad(app, db_clean):
    """Dos pantallas que piden controles distintos del mismo lote se contradicen (M161)."""
    _limpiar()
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES ('ZCHK IPC',1,'aprobado',1000,'sebastian')")
    ebr = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,'ZCHK-OA','ZCHK-OA','en_proceso','acondicionamiento','sebastian',"
                "'1990-01-01 00:00:00',1000)", (mbr,))
    c = _login(app, "hernando")
    base = _ver(c, "ipc", "acondicionamiento")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"], "unidad": i["unidad"]} for i in base]
    items.append({"texto": "ZCHK Torque de la tapa", "unidad": "N·m"})
    assert _guardar(c, "ipc", "acondicionamiento", items).status_code == 200

    # el legajo lo pide
    from api.blueprints.brd import _ipc_estandar_ebr
    from api.database import get_db
    with app.app_context():
        cat = _ipc_estandar_ebr(get_db(), ebr)
    assert any(t == "ZCHK Torque de la tapa" for _c, t, _u in cat), cat

    # y la cola de Calidad pide EXACTAMENTE lo mismo
    r = c.get("/api/calidad/bandeja")
    assert r.status_code == 200, r.data[:200]
    cola = (r.get_json().get("secciones") or {}).get("controles_pendientes") or {}
    mios = [i["control"] for i in cola.get("items", []) if i["ebr_id"] == ebr]
    assert "ZCHK Torque de la tapa" in mios, (
        "la cola de Calidad no ve el control que el director técnico agregó: %s" % mios)


def test_cada_cambio_de_procedimiento_deja_rastro(app, db_clean):
    """Part 11 §11.10(e): quién cambió qué, con el antes y el después."""
    _limpiar()
    c = _login(app, "hernando")
    base = _ver(c, "despeje", "dispensacion")["items"]
    items = [{"clave": i["clave"], "texto": i["texto"]} for i in base]
    items[0]["texto"] = "ZCHK auditado"
    assert _guardar(c, "despeje", "dispensacion", items,
                    motivo="ajuste pedido por INVIMA").status_code == 200
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        # `antes`/`despues` son columnas propias del audit (mig 91), no `detalle`.
        row = conn.execute(
            "SELECT usuario, COALESCE(antes,''), COALESCE(despues,'') FROM audit_log "
            "WHERE accion='CONFIGURAR_CHECKLIST' ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row, "no quedó rastro del cambio de procedimiento"
    assert row[0] == "hernando", row[0]
    assert "ajuste pedido por INVIMA" in row[2], row[2]
    assert "ZCHK auditado" in row[2], row[2]
    # El ANTES tiene que estar completo, o el rastro no permite deshacer: ante un
    # procedimiento cambiado por error la pregunta es "¿qué decía antes?", no "¿qué dice
    # ahora?" (M175). Se busca sin acentos porque json.dumps los escapa (á).
    import json as _j
    antes = _j.loads(row[1])["items"]
    assert len(antes) == 12, antes
    assert antes[0]["texto"].startswith("El área está libre"), antes[0]


def test_el_dt_tiene_pantalla_y_se_puede_llegar(app, db_clean):
    """Una capacidad a la que nadie puede llegar no existe (M121/M197).

    Además la pestaña tiene que estar EN EL MAPA del conmutador: `goTab` apaga todos los
    paneles antes de encender el destino, así que una pestaña sin entrada en `_tabIds`
    deja la pantalla EN BLANCO (M155).
    """
    c = _login(app, "hernando")
    pg = c.get("/aseguramiento/checklists")
    assert pg.status_code == 200, pg.status_code
    html = pg.data.decode("utf-8")
    for que, pieza in (("la carga del procedimiento", "/api/brd/checklists?tipo="),
                       ("el botón de guardar", "ckGuardar()"),
                       ("el de agregar", "ckAgregar()"),
                       ("el de volver a fábrica", "ckRestaurar()"),
                       ("el aviso de solo lectura", 'id="ro"')):
        assert pieza in html, "la pantalla del DT no tiene %s (%s)" % (que, pieza)

    aseg = pantalla_servida(c, "/aseguramiento")
    assert "/aseguramiento/checklists" in aseg, "no se llega desde Aseguramiento"
    assert "goTab('tab-checklists')" in aseg, "falta la pestaña"
    assert "'tab-checklists'" in aseg.split("_tabIds")[1][:400], (
        "la pestaña no está en el mapa del conmutador: abrirla deja la pantalla en blanco")
    assert 'id="tab-checklists"' in aseg, "falta el panel de la pestaña"
