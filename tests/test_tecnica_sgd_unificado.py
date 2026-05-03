"""Tests de unificacion SGD: /api/tecnica/documentos delega a sgd_documentos.

Sebastian 3-may-2026: ANTES habian dos tablas (documentos_sgd legacy
en tecnica + sgd_documentos rico en aseguramiento). AHORA /tecnica
escribe en sgd_documentos · ambos modulos comparten fuente.
"""
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="hernando"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(table, where, params):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
    conn.commit(); conn.close()


def test_post_tecnica_aparece_en_aseguramiento(app, db_clean):
    """Crear via /api/tecnica/documentos debe aparecer en /api/aseguramiento/sgd."""
    c = _login(app, "hernando")
    payload = {
        "tipo": "SOP",
        "codigo": "ASG-PRO-700",
        "nombre": "SOP unificacion test",
        "fecha_emision": "2026-04-01",
        "frecuencia_revision_meses": 12,
        "responsable": "hernando",
    }
    r = c.post("/api/tecnica/documentos", json=payload, headers=csrf_headers())
    assert r.status_code == 200
    did = r.get_json()["id"]
    try:
        # Ahora consultar desde aseguramiento
        r2 = c.get("/api/aseguramiento/sgd/listado")
        assert r2.status_code == 200
        items = r2.get_json().get("items", [])
        codigos = [it["codigo"] for it in items]
        assert "ASG-PRO-700" in codigos
        # Verificar campos en la tabla rica
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            """SELECT codigo, area, tipo_doc, numero, titulo, version_actual,
                      estado, elaborado_por
                 FROM sgd_documentos WHERE id=?""", (did,)).fetchone()
        conn.close()
        assert row[0] == "ASG-PRO-700"
        assert row[1] == "ASG"
        assert row[2] == "PRO"
        assert row[3] == 700
        assert row[4] == "SOP unificacion test"
        assert row[6] == "vigente"  # estado mapeado
        assert row[7] == "hernando"
    finally:
        _cleanup("sgd_documentos", "id=?", (did,))


def test_post_tecnica_rechaza_codigo_invalido(app, db_clean):
    """Codigo sin formato AAA-BBB-NNN debe rechazarse."""
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/documentos",
               json={"codigo": "TEST-SOP-001", "nombre": "test"},
               headers=csrf_headers())
    assert r.status_code == 400
    assert "codigo" in r.get_json()["error"].lower()


def test_post_tecnica_rechaza_codigo_duplicado(app, db_clean):
    c = _login(app, "hernando")
    payload = {"codigo": "ASG-PRO-701", "nombre": "Original"}
    r = c.post("/api/tecnica/documentos", json=payload, headers=csrf_headers())
    assert r.status_code == 200
    did = r.get_json()["id"]
    try:
        r2 = c.post("/api/tecnica/documentos",
                    json={"codigo": "ASG-PRO-701", "nombre": "Duplicado"},
                    headers=csrf_headers())
        assert r2.status_code == 409
    finally:
        _cleanup("sgd_documentos", "id=?", (did,))


def test_get_tecnica_lee_de_sgd_documentos(app, db_clean):
    """GET /api/tecnica/documentos lee de sgd_documentos (no de documentos_sgd)."""
    c = _login(app, "hernando")
    # Sembrar directo en sgd_documentos (la tabla rica)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-NOR-702'")
    cur = conn.execute(
        """INSERT INTO sgd_documentos
           (codigo, area, tipo_doc, numero, titulo, version_actual, estado, vigente_desde)
           VALUES ('COC-NOR-702','COC','NOR',702,'Norma de prueba','2.0','vigente',date('now'))""")
    sid = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/documentos")
        assert r.status_code == 200
        items = r.get_json()
        item = next((x for x in items if x["codigo"] == "COC-NOR-702"), None)
        assert item is not None
        assert item["nombre"] == "Norma de prueba"
        assert item["version"] == "2.0"
        # tipo_doc 'NOR' debe mapear a 'BPM' en schema simple
        assert item["tipo"] == "BPM"
        assert item["estado"] == "Vigente"
    finally:
        _cleanup("sgd_documentos", "id=?", (sid,))


def test_patch_tecnica_actualiza_sgd_documentos(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/tecnica/documentos",
                json={"codigo": "ASG-PRO-703", "nombre": "Original",
                      "responsable": "hernando"},
                headers=csrf_headers())
    did = r.get_json()["id"]
    try:
        r2 = cs.patch(f"/api/tecnica/documentos/{did}",
                      json={"nombre": "Modificado", "version": "2.0"},
                      headers=csrf_headers())
        assert r2.status_code == 200
        # Verificar en sgd_documentos
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT titulo, version_actual FROM sgd_documentos WHERE id=?",
            (did,)).fetchone()
        conn.close()
        assert row[0] == "Modificado"
        assert row[1] == "2.0"
    finally:
        _cleanup("tecnica_versiones", "entidad='sgd' AND registro_id=?", (did,))
        _cleanup("sgd_documentos", "id=?", (did,))


def test_delete_tecnica_es_soft_delete(app, db_clean):
    """DELETE /api/tecnica/documentos/<id> marca como retirado (no DROP fila)."""
    cs = _login(app, "sebastian")
    r = cs.post("/api/tecnica/documentos",
                json={"codigo": "ASG-PRO-704", "nombre": "Para borrar"},
                headers=csrf_headers())
    did = r.get_json()["id"]
    try:
        r2 = cs.delete(f"/api/tecnica/documentos/{did}", headers=csrf_headers())
        assert r2.status_code == 200
        # La fila sigue existiendo con estado=retirado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT estado FROM sgd_documentos WHERE id=?", (did,)).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "retirado"
    finally:
        _cleanup("sgd_documentos", "id=?", (did,))


def test_marcar_revisado_actualiza_proxima_revision(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/tecnica/documentos",
                json={"codigo": "ASG-PRO-705", "nombre": "Para revisar",
                      "fecha_emision": "2025-01-01",
                      "frecuencia_revision_meses": 6},
                headers=csrf_headers())
    did = r.get_json()["id"]
    try:
        r2 = cs.post(f"/api/tecnica/documentos/{did}/marcar-revisado",
                     headers=csrf_headers())
        assert r2.status_code == 200
        d2 = r2.get_json()
        # fecha_revision = hoy
        assert d2["fecha_revision"] == date.today().isoformat()
        # fecha_proxima_revision = hoy + ~6 meses
        prox = date.fromisoformat(d2["fecha_proxima_revision"])
        dias = (prox - date.today()).days
        assert 170 <= dias <= 190  # 6 meses ≈ 180d
    finally:
        _cleanup("sgd_documentos", "id=?", (did,))


def test_proximos_vencimientos_lee_sgd_documentos(app, db_clean):
    c = _login(app, "hernando")
    # Sembrar en sgd_documentos un doc que vence en 20d
    proxima = (date.today() + timedelta(days=20)).isoformat()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='ASG-PRO-706'")
    cur = conn.execute(
        """INSERT INTO sgd_documentos
           (codigo, area, tipo_doc, numero, titulo, version_actual,
            estado, vigente_desde, proxima_revision)
           VALUES ('ASG-PRO-706','ASG','PRO',706,'Vence en 20d','1.0',
                   'vigente', date('now','-300 day'), ?)""",
        (proxima,))
    sid = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/documentos/proximos-vencimientos")
        assert r.status_code == 200
        docs = r.get_json()["documentos"]
        item = next((x for x in docs if x["codigo"] == "ASG-PRO-706"), None)
        assert item is not None
        assert item["nombre"] == "Vence en 20d"
        # Schema simple: tipo PRO → SOP
        assert item["tipo"] == "SOP"
    finally:
        _cleanup("sgd_documentos", "id=?", (sid,))
