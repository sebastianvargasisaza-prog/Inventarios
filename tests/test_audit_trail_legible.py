"""El audit trail se puede LEER (15-ago-2026) · acá EOS no copia a MyBatch, lo mejora.

El Audit Trail de MyBatch muestra el JSON crudo de Django:
    {"model": "assurance.observationprocess", "pk": "ecaacab3-...", "fields": {...}}
Es trazabilidad de verdad, pero un auditor no lee eso, y quien revisa un año de cambios
menos. EOS ya guarda el antes y el después completos, así que puede presentar la misma
evidencia en palabras: quién, qué cambió, de qué a qué.

Lo que fija este guard:
  · que el cambio se explique en palabras y con el campo, el valor viejo y el nuevo;
  · que el JSON crudo SIGA viniendo en cada fila -la traducción es para leer, el crudo es
    la prueba, y esconderlo sería empeorar el registro para que se vea lindo;
  · que lo que NO se pudo traducir se declare en vez de quedar a medias (M124/M170);
  · que el TOTAL se cuente aparte del recorte, también en el reporte crudo que ya existía
    y decía "total: 500" con 3.000 cambios en el rango (M155/M207);
  · que el director técnico -quien responde ante INVIMA- pueda abrirlo (M32).
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


def _sembrar(usuario, accion, tabla, registro_id, antes, despues, detalle=""):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(
            "INSERT INTO audit_log (usuario, accion, tabla, registro_id, antes, despues, "
            "detalle, ip, fecha) VALUES (?,?,?,?,?,?,?,'127.0.0.1',datetime('now'))",
            (usuario, accion, tabla, registro_id,
             json.dumps(antes) if antes is not None else None,
             json.dumps(despues) if despues is not None else None, detalle))
        conn.commit()
    finally:
        conn.close()


def _leer(app, user="sebastian", **qs):
    c = _login(app, user)
    url = "/api/aseguramiento/audit-trail-legible"
    if qs:
        url += "?" + "&".join("%s=%s" % (k, v) for k, v in qs.items())
    r = c.get(url)
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_el_cambio_se_explica_en_palabras(app, db_clean):
    """Quién, qué tocó, y de qué a qué. Eso es lo que MyBatch no muestra."""
    _sembrar("laura", "LIBERAR_EBR", "ebr_ejecuciones", "4141",
             {"estado": "completado"}, {"estado": "liberado", "yield_pct": 97.4})
    j = _leer(app, q="4141")
    mios = [i for i in j["items"] if i["registro_id"] == "4141"]
    assert mios, j["items"][:3]
    ev = mios[0]
    assert ev["traducido"] is True, ev
    assert "laura" in ev["titulo"] and "liberó" in ev["titulo"], ev["titulo"]
    assert "legajo" in ev["titulo"], ev["titulo"]
    campos = {c["campo"]: c for c in ev["cambios"]}
    assert "estado" in campos, ev["cambios"]
    assert campos["estado"]["de"] == "completado"
    assert campos["estado"]["a"] == "liberado"
    assert "rendimiento" in campos, "no tradujo el nombre del campo: %s" % list(campos)


def test_el_registro_crudo_sigue_siendo_la_prueba(app, db_clean):
    """La traducción es para leer; el crudo es la evidencia y no se esconde."""
    _sembrar("hernando", "CONFIGURAR_CHECKLIST", "checklist_items", "despeje:dispensacion",
             {"items": [{"texto": "viejo"}]}, {"items": [{"texto": "nuevo"}]})
    j = _leer(app, q="despeje")
    ev = [i for i in j["items"] if i["registro_id"] == "despeje:dispensacion"][0]
    assert ev["antes"] and "viejo" in ev["antes"], ev["antes"]
    assert ev["despues"] and "nuevo" in ev["despues"], ev["despues"]
    assert ev["dominio"] == "procedimientos", ev["dominio"]


def test_lo_que_no_se_pudo_traducir_se_declara(app, db_clean):
    """Un renglón a medio traducir que parece completo es peor que uno crudo: quien
    audita creería que ya lo leyó (M124/M170)."""
    _sembrar("sistema", "ZZZRARO", "tabla_que_nadie_mapeo", "9001", None, {"x": 1})
    j = _leer(app, q="ZZZRARO")
    ev = [i for i in j["items"] if i["accion"] == "ZZZRARO"][0]
    assert ev["traducido"] is False, ev
    assert ev["dominio"] == "otros", ev["dominio"]
    assert j["sin_traducir"] >= 1, j["sin_traducir"]


def test_el_total_no_sale_de_la_ventana(app, db_clean):
    """El número con el que alguien decide si ya revisó todo no puede ser el del recorte.

    Se siembran MÁS filas que el techo de las DOS páginas (la legible corta en 300, la cruda en 500), en un día propio de 2019: sin
    superar el techo, total y mostrados coinciden igual y el guard pasaría verde con el
    bug puesto -que es exactamente lo que pasó al probarle los dientes (M96). El día
    aparte hace que el test controle su universo en vez de depender de lo que otros
    archivos hayan sembrado (M102). `audit_log` es append-only por trigger, así que no
    se limpia: se acota por fecha.
    """
    dia = "2019-03-15"
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        ya = conn.execute("SELECT COUNT(*) FROM audit_log WHERE date(fecha)=?",
                          (dia,)).fetchone()[0]
        faltan = max(0, 520 - int(ya or 0))
        if faltan:
            conn.executemany(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, despues, ip, "
                "fecha) VALUES ('sebastian','LIBERAR_EBR','ebr_ejecuciones',?,?,'127.0.0.1',?)",
                [("ZTOT-%d" % i, '{"estado": "liberado"}', dia + " 08:00:00")
                 for i in range(faltan)])
            conn.commit()
    finally:
        conn.close()

    j = _leer(app, desde=dia, hasta=dia)
    assert j["total"] >= 520, "el universo sembrado no llegó: %s" % j["total"]
    assert j["mostrados"] < j["total"], (
        "la página trae todo, así que este caso no prueba nada: %s" % j)
    assert j["recortado"] == j["total"] - j["mostrados"], j

    # el reporte CRUDO que ya existía tenía el mismo defecto: devolvía total = len(items)
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/reportes/audit-trail?desde=%s&hasta=%s" % (dia, dia))
    assert r.status_code == 200, r.data[:200]
    jc = r.get_json()
    assert jc["total"] >= 520, jc["total"]
    assert jc["mostrados"] < jc["total"], jc
    assert jc["recortado"] == jc["total"] - jc["mostrados"], jc


def test_se_filtra_por_area_del_proceso(app, db_clean):
    """Un auditor pregunta por ÁREA, no por nombre de tabla."""
    _sembrar("mayerlin", "REGISTRAR_ENVASADO", "ebr_envasado_unidades", "ZAUD-ENV",
             None, {"unidades": 1200})
    _sembrar("catalina", "PAGAR_OC", "pagos_oc", "ZAUD-PAGO", None, {"monto": 500000})
    env = _leer(app, dominio="envasado")
    assert all(i["dominio"] == "envasado" for i in env["items"]), (
        "el filtro por área dejó pasar otras: %s" % {i["dominio"] for i in env["items"]})
    assert any(i["registro_id"] == "ZAUD-ENV" for i in env["items"]), env["mostrados"]
    assert not any(i["registro_id"] == "ZAUD-PAGO" for i in env["items"])
    # el total del área tiene que reflejar el filtro, no el universo entero
    todo = _leer(app)
    assert env["total"] <= todo["total"], (env["total"], todo["total"])


def test_el_director_tecnico_puede_abrirlo(app, db_clean):
    """Es quien responde ante INVIMA: si no puede abrir el audit trail, no sirve (M32)."""
    c = _login(app, "hernando")
    r = c.get("/api/aseguramiento/audit-trail-legible")
    assert r.status_code == 200, (r.status_code, r.data[:200])
    assert r.get_json().get("ok") is True


def test_la_pantalla_existe_y_se_alcanza(app, db_clean):
    """Una capacidad a la que nadie puede llegar no existe (M121). Y la pestaña tiene que
    estar en el mapa del conmutador o la pantalla abre EN BLANCO (M155)."""
    c = _login(app, "miguel")
    pg = c.get("/aseguramiento/audit-trail")
    assert pg.status_code == 200, pg.status_code
    html = pg.data.decode("utf-8")
    for que, pieza in (("la carga", "/api/aseguramiento/audit-trail-legible?"),
                       ("el filtro por área", "function atDom("),
                       ("el registro crudo", "Ver el registro crudo")):
        assert pieza in html, "la pantalla no tiene %s (%s)" % (que, pieza)
    aseg = pantalla_servida(c, "/aseguramiento")
    assert "/aseguramiento/audit-trail" in aseg, "no se llega desde Aseguramiento"
    assert "goTab('tab-audit')" in aseg, "falta la pestaña"
    assert "'tab-audit'" in aseg.split("_tabIds")[1][:400], (
        "la pestaña no está en el mapa: abrirla dejaría la pantalla en blanco")
    assert 'id="tab-audit"' in aseg, "falta el panel"
