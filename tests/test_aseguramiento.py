"""Tests del módulo Aseguramiento (ASG · /aseguramiento).

SGD electrónico + capacitaciones + conflictos. Complementario a /calidad.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


# ─── Página y dashboard ─────────────────────────────────────────────────

def test_aseguramiento_pagina_redirect_sin_login(client, db_clean):
    """GET /aseguramiento sin login redirige a /login."""
    r = client.get("/aseguramiento", follow_redirects=False)
    assert r.status_code == 302


def test_aseguramiento_pagina_con_login(app, db_clean):
    """GET /aseguramiento con login retorna HTML."""
    c = _login(app, "laura")
    r = c.get("/aseguramiento")
    assert r.status_code == 200
    assert b"ASEGURAMIENTO" in r.data


def test_dashboard_estructura(app, db_clean):
    """GET /api/aseguramiento/dashboard retorna estructura completa."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/dashboard")
    assert r.status_code == 200
    data = r.get_json()
    assert "fecha_hoy" in data
    assert "sgd" in data
    assert "capacitaciones" in data
    assert "ncs_abiertas" in data
    assert "auditorias_60d" in data


def test_dashboard_requiere_auth(client, db_clean):
    r = client.get("/api/aseguramiento/dashboard")
    assert r.status_code == 401


# ─── SGD electrónico ─────────────────────────────────────────────────────

def test_sgd_listado_vacio(app, db_clean):
    """Sin documentos importados, retorna lista vacía pero estructura OK."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos")
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/listado")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 0
    assert data["items"] == []
    assert "areas" in data
    assert "tipos_doc" in data


def test_sgd_crear_documento(app, db_clean):
    """POST /api/aseguramiento/sgd con código válido crea documento."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "COC-PRO-099",
                     "titulo": "Test Procedure",
                     "version": "1",
                     "estado": "vigente",
                     "elaborado_por": "Laura"},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["accion"] == "creado"

    # Verificar que aparece en listado
    r2 = c.get("/api/aseguramiento/sgd/listado?area=COC")
    items = r2.get_json()["items"]
    codigos = [it["codigo"] for it in items]
    assert "COC-PRO-099" in codigos

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-PRO-099'")
    conn.commit(); conn.close()


def test_sgd_codigo_invalido(app, db_clean):
    """Código fuera del formato AAA-BBB-NNN → 400."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "FOO-BAR-X", "titulo": "Test"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_sgd_area_no_reconocida(app, db_clean):
    """Área fuera de las 8 oficiales → 400."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "XYZ-PRO-001", "titulo": "Test"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_sgd_actualizar_archiva_version_anterior(app, db_clean):
    """Cambiar versión actual archiva la anterior en sgd_versiones."""
    c = _login(app, "laura")
    # Crear v1
    c.post("/api/aseguramiento/sgd",
           json={"codigo": "ASG-PRO-099", "titulo": "Test ASG",
                 "version": "1", "fecha_aprobacion": "2026-01-01"},
           headers=csrf_headers())
    # Cambiar a v2
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "ASG-PRO-099", "titulo": "Test ASG",
                     "version": "2", "fecha_aprobacion": "2026-05-01",
                     "motivo_cambio": "Actualización por hallazgo"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar que la v1 quedó en histórico
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute(
        "SELECT version, motivo_cambio FROM sgd_versiones WHERE codigo='ASG-PRO-099'"
    ).fetchall()
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='ASG-PRO-099'")
    conn.execute("DELETE FROM sgd_versiones WHERE codigo='ASG-PRO-099'")
    conn.commit(); conn.close()

    versiones = [r[0] for r in rows]
    assert "1" in versiones, f"versión 1 debería estar archivada · histórico: {versiones}"


def test_sgd_detalle_no_existe(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/COC-PRO-999999")
    assert r.status_code == 404


def test_sgd_solo_calidad_admin_pueden_escribir(app, db_clean):
    """Usuario sin rol de Calidad/Admin → 403."""
    c = _login(app, "luis")  # planta operativa
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "COC-PRO-088", "titulo": "X"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_sgd_importar_admin_only(app, db_clean):
    """Solo admin puede importar masivamente."""
    c = _login(app, "laura")  # calidad pero no admin
    r = c.post("/api/aseguramiento/sgd/importar",
               json={"items": [{"codigo": "COC-PRO-077", "titulo": "X"}]},
               headers=csrf_headers())
    assert r.status_code == 403

    c_admin = _login(app, "sebastian")
    r2 = c_admin.post("/api/aseguramiento/sgd/importar",
                      json={"items": [
                          {"codigo": "COC-PRO-077", "titulo": "Test importado"},
                          {"codigo": "ASG-PRO-077", "titulo": "Test ASG importado"},
                      ]},
                      headers=csrf_headers())
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["insertados"] == 2

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo IN ('COC-PRO-077','ASG-PRO-077')")
    conn.commit(); conn.close()


# ─── Capacitaciones ──────────────────────────────────────────────────────

def test_capacitaciones_asignar_y_firmar(app, db_clean):
    """Asignar a una persona y luego firmar como esa persona."""
    c_admin = _login(app, "laura")
    # Crear documento
    c_admin.post("/api/aseguramiento/sgd",
                 json={"codigo": "RRH-PRO-099", "titulo": "Test RRHH",
                       "version": "1"},
                 headers=csrf_headers())
    # Asignar a smurillo
    r = c_admin.post("/api/aseguramiento/capacitaciones/asignar",
                     json={"sgd_codigo": "RRH-PRO-099",
                           "sgd_version": "1",
                           "personas": ["smurillo"]},
                     headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()["asignados"] == 1

    # Login como smurillo y firmar
    c_user = _login(app, "smurillo")
    r2 = c_user.get("/api/aseguramiento/capacitaciones/mias")
    items = r2.get_json()["items"]
    assert any(it["sgd_codigo"] == "RRH-PRO-099" for it in items)

    r3 = c_user.post("/api/aseguramiento/capacitaciones/firmar",
                     json={"sgd_codigo": "RRH-PRO-099", "sgd_version": "1"},
                     headers=csrf_headers())
    assert r3.status_code == 200
    assert "firma_hash" in r3.get_json()

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_capacitaciones WHERE sgd_codigo='RRH-PRO-099'")
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='RRH-PRO-099'")
    conn.commit(); conn.close()


def test_capacitaciones_firmar_sin_asignacion(app, db_clean):
    """Si no tiene la capacitación asignada → 404."""
    c = _login(app, "smurillo")
    r = c.post("/api/aseguramiento/capacitaciones/firmar",
               json={"sgd_codigo": "FAKE-PRO-001", "sgd_version": "1"},
               headers=csrf_headers())
    assert r.status_code == 404


def test_capacitaciones_doc_no_existe(app, db_clean):
    """Asignar capacitación de doc inexistente → 404."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/capacitaciones/asignar",
               json={"sgd_codigo": "FAKE-DOC-001", "sgd_version": "1",
                     "personas": ["luis"]},
               headers=csrf_headers())
    assert r.status_code == 404


# ─── Conflictos ──────────────────────────────────────────────────────────

def test_conflictos_listar(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/conflictos")
    assert r.status_code == 200
    assert "items" in r.get_json()


def test_conflictos_resolver_requiere_resolucion_larga(app, db_clean):
    """Resolución <10 chars → 400."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO sgd_conflictos (codigo, archivos_detectados, temas_detectados)
                    VALUES ('TEST-CONF-001', 'a;b', 'tema1;tema2')""")
    cid = conn.execute("SELECT id FROM sgd_conflictos WHERE codigo='TEST-CONF-001'").fetchone()[0]
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.post(f"/api/aseguramiento/sgd/conflictos/{cid}/resolver",
               json={"resolucion": "corta"},
               headers=csrf_headers())
    assert r.status_code == 400

    r2 = c.post(f"/api/aseguramiento/sgd/conflictos/{cid}/resolver",
                json={"resolucion": "Resolución detallada con más de 10 caracteres"},
                headers=csrf_headers())
    assert r2.status_code == 200

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_conflictos WHERE codigo='TEST-CONF-001'")
    conn.commit(); conn.close()
