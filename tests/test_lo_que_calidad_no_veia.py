# -*- coding: utf-8 -*-
"""Tres secciones de Calidad/Aseguramiento que devolvían VACÍO por un error de columna.

Las tres se veían igual que "no hay nada que hacer", que es la peor forma de fallar en un
módulo regulado: nadie reporta una bandeja vacía (M96/M154/M100).

  1. Auditorías próximas   -> consultaba `area`, `descripcion` y `responsable`, que NO existen
                              en `auditorias` (son `ente_auditado`, `alcance`, `auditor`).
  2. Muestreo microbiológico -> la tabla del cronograma NO está construida todavía, y el cero se
                              leía como "no hay muestreos pendientes". Ahora lo DECLARA.
  3. OCs de calibración    -> consultaba `fecha_creacion`; la columna de `ordenes_compra` es
                              `fecha`. Sin esas OCs no se puede anclar la calibración a su compra.

Cada test prueba sus DIENTES: siembra el dato y exige verlo. Si alguien vuelve a poner una
columna que no existe, el `except` devolverá la lista vacía y el test cae.
"""
import pytest


_H = {"Origin": "http://localhost"}


def _login(client, usuario):
    r = client.post("/login", data={"username": usuario, "password": "TestPass123"},
                    headers=_H, follow_redirects=False)
    assert r.status_code == 302, "no entro %s" % usuario
    return client


def test_auditoria_programada_aparece_en_la_bandeja(client, app):
    """Una auditoría programada tiene que verse. Antes NUNCA se veía ninguna."""
    import database
    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        # ⚠ el CHECK exige 'Interna' capitalizado -- ese CHECK es la invariante, no un estorbo
        cur.execute("DELETE FROM auditorias WHERE ente_auditado='ZZ-GUARD-AUD'")
        cur.execute(
            "INSERT INTO auditorias (tipo, ente_auditado, fecha_planeada, auditor, alcance, estado) "
            "VALUES ('Interna','ZZ-GUARD-AUD',date('now','+10 days'),'Miguel','BPM','programada')")
        c.commit()

    j = _login(client, "laura").get("/api/calidad/bandeja").get_json() or {}
    sec = (j.get("secciones") or {}).get("auditorias_proximas") or {}
    items = sec.get("items") or []
    mia = [x for x in items if x.get("area") == "ZZ-GUARD-AUD"]
    assert mia, "la auditoría programada NO aparece (columnas equivocadas otra vez): %s" % items

    fila = mia[0]
    # el nombre de pantalla sale de columnas REALES, no inventadas
    assert fila.get("responsable") == "Miguel"      # auditor
    assert fila.get("descripcion") == "BPM"         # alcance
    assert fila.get("tipo") == "Interna"
    assert (fila.get("fecha") or "")[:2] == "20"


def test_muestreo_micro_declara_que_no_esta_construido(client):
    """Un cero que nadie calculó NO se puede leer como 'no hay muestreos'."""
    j = _login(client, "laura").get("/api/calidad/bandeja").get_json() or {}
    m = (j.get("secciones") or {}).get("muestreo_micro_semana") or {}

    assert m.get("total") == 0
    assert m.get("no_configurado") is True, (
        "la sección tiene que DECLARAR que el cronograma no existe · un 0 mudo miente")
    motivo = (m.get("motivo") or "").lower()
    assert "no" in motivo and ("construido" in motivo or "configurado" in motivo), motivo


def test_oc_de_calibracion_se_puede_anclar_a_su_compra(client, app):
    """Sin esta lista, registrar una calibración nunca encuentra la OC con que se pagó."""
    import database
    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        cur.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-ZZ-CAL'")
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, fecha, estado, observaciones) "
                    "VALUES ('OC-ZZ-CAL','Balanzas ZZ',date('now'),'Pagada','CALIBRACION balanza')")
        c.commit()

    r = _login(client, "sebastian").get("/api/aseguramiento/calibracion/ocs-sugeridas")
    assert r.status_code == 200
    j = r.get_json() or {}
    assert not j.get("error_lectura"), "la consulta reventó: %s" % j.get("motivo")

    mia = [x for x in (j.get("items") or []) if x.get("numero_oc") == "OC-ZZ-CAL"]
    assert mia, "la OC de calibración NO se lista (columna fecha_creacion otra vez?): %s" % j
    assert mia[0].get("proveedor") == "Balanzas ZZ"
    assert (mia[0].get("fecha") or "")[:2] == "20", "la fecha viene vacía · columna equivocada"


def test_completar_limpieza_deja_rastro(client, app):
    """Liberar un equipo tras limpiarlo es una acción GMP: sin audit_log no se sabe quién fue."""
    import database
    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        cur.execute("DELETE FROM equipo_limpieza_log WHERE equipo_codigo='ZZ-EQ-LIMP'")
        cur.execute(
            "INSERT INTO equipo_limpieza_log (equipo_codigo, lote_anterior, tipo_limpieza, "
            "operario_username, iniciado_at_utc) "
            "VALUES ('ZZ-EQ-LIMP','ZZ-LOTE-1','rutinaria','mayerlin',datetime('now','utc'))")
        c.commit()
        cid = cur.execute("SELECT id FROM equipo_limpieza_log WHERE equipo_codigo='ZZ-EQ-LIMP' "
                          "ORDER BY id DESC LIMIT 1").fetchone()[0]
        antes = cur.execute("SELECT COUNT(*) FROM audit_log "
                            "WHERE accion='COMPLETAR_LIMPIEZA_EQUIPO'").fetchone()[0]

    r = _login(client, "sebastian").post(
        "/api/brd/cleaning/%d/completar" % cid,
        json={"resultado": "conforme", "observaciones": "guard"},
        headers={"Content-Type": "application/json", **_H})
    assert r.status_code in (200, 201), r.get_json()

    with app.app_context():
        c = database.get_db()
        despues = c.execute("SELECT COUNT(*) FROM audit_log "
                            "WHERE accion='COMPLETAR_LIMPIEZA_EQUIPO'").fetchone()[0]
    assert despues == antes + 1, (
        "completar la limpieza no dejó rastro en audit_log · quién liberó el equipo se pierde")
