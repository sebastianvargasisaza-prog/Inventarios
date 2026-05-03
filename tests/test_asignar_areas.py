"""Tests del endpoint /api/planta/asignar-areas + página + parser [CODIGO]."""
import json
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_produccion(producto, fecha, area_id=None, lotes=1, estado="programado"):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, cantidad_kg, estado, area_id, origen)
           VALUES (?, ?, ?, ?, ?, ?, 'manual')""",
        (producto, fecha, lotes, 5.0, estado, area_id))
    pid = cur.lastrowid
    conn.commit(); conn.close()
    return pid


def _cleanup_pid(pid):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
    conn.commit(); conn.close()


# ── AUTH ──────────────────────────────────────────────────────────────

def test_asignar_areas_requires_auth(client, db_clean):
    r = client.get("/api/planta/asignar-areas")
    assert r.status_code == 401
    r = client.post("/api/planta/asignar-areas", json={"asignaciones": []},
                    headers=csrf_headers())
    assert r.status_code == 401


# ── GET listado ───────────────────────────────────────────────────────

def test_get_listado_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/planta/asignar-areas?dias=30")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("horizonte_dias", "total", "sin_area",
              "areas_disponibles", "producciones"):
        assert k in d
    assert d["horizonte_dias"] == 30
    # Áreas disponibles deben incluir las del seed canónico (al menos PROD1/PROD2/ENV1)
    codigos = [a["codigo"] for a in d["areas_disponibles"]]
    for cod in ("PROD1", "PROD2", "ENV1"):
        assert cod in codigos


def test_get_listado_horizonte_clamp(app, db_clean):
    """dias se limita a [1, 180]"""
    c = _login(app, "sebastian")
    r = c.get("/api/planta/asignar-areas?dias=999")
    assert r.status_code == 200
    assert r.get_json()["horizonte_dias"] == 180
    r = c.get("/api/planta/asignar-areas?dias=0")
    assert r.get_json()["horizonte_dias"] == 1


def test_get_solo_sin_area(app, db_clean):
    """solo_sin_area filtra producciones que ya tienen área"""
    c = _login(app, "sebastian")
    # Sembrar 2 producciones: una sin area, otra con area
    pid_sin = _seed_produccion("PROD-TEST-SIN-AREA", "2026-05-15", area_id=None)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    conn.close()
    pid_con = _seed_produccion("PROD-TEST-CON-AREA", "2026-05-16", area_id=pr1[0])
    try:
        r = c.get("/api/planta/asignar-areas?dias=180&solo_sin_area=1")
        d = r.get_json()
        ids = [p["id"] for p in d["producciones"]]
        assert pid_sin in ids
        assert pid_con not in ids
    finally:
        _cleanup_pid(pid_sin); _cleanup_pid(pid_con)


def test_get_incluye_sugerencia(app, db_clean):
    """Cada producción tiene area_sugerida_id (puede ser null si no se pudo)."""
    c = _login(app, "sebastian")
    pid = _seed_produccion("PROD-TEST-SUGERENCIA", "2026-05-20")
    try:
        r = c.get("/api/planta/asignar-areas?dias=180")
        d = r.get_json()
        item = next((p for p in d["producciones"] if p["id"] == pid), None)
        assert item is not None
        assert "area_sugerida_id" in item
        assert "area_sugerida_codigo" in item
    finally:
        _cleanup_pid(pid)


# ── POST bulk asignar ─────────────────────────────────────────────────

def test_post_asigna_y_audita(app, db_clean):
    c = _login(app, "sebastian")
    pid = _seed_produccion("PROD-TEST-ASIGNAR", "2026-05-22")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr3 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD3'").fetchone()
    pr3_id = pr3[0]
    conn.close()
    try:
        r = c.post("/api/planta/asignar-areas",
                   json={"asignaciones": [{"id": pid, "area_id": pr3_id}]},
                   headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d["asignados"] == 1
        assert pid in d["ids_ok"]
        # Verificar persistencia
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT area_id FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()
        conn.close()
        assert row[0] == pr3_id
    finally:
        _cleanup_pid(pid)


def test_post_desasigna_con_null(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0]
    conn.close()
    pid = _seed_produccion("PROD-TEST-DESASIG", "2026-05-23", area_id=pr1_id)
    try:
        r = c.post("/api/planta/asignar-areas",
                   json={"asignaciones": [{"id": pid, "area_id": None}]},
                   headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT area_id FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()
        conn.close()
        assert row[0] is None
    finally:
        _cleanup_pid(pid)


def test_post_no_reasigna_completado(app, db_clean):
    c = _login(app, "sebastian")
    pid = _seed_produccion("PROD-TEST-COMPLETADO", "2026-05-25",
                           estado="completado")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0]
    conn.close()
    try:
        r = c.post("/api/planta/asignar-areas",
                   json={"asignaciones": [{"id": pid, "area_id": pr1_id}]},
                   headers=csrf_headers())
        d = r.get_json()
        assert d["asignados"] == 0
        assert len(d["errores"]) == 1
        assert d["errores"][0]["id"] == pid
    finally:
        _cleanup_pid(pid)


def test_post_reporta_conflicto_sala_misma_fecha(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr2 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD2'").fetchone()
    pr2_id = pr2[0]
    conn.close()
    # Producción A en PROD2 mañana
    pid_a = _seed_produccion("PROD-TEST-CONFLIC-A", "2026-05-28", area_id=pr2_id)
    # Producción B sin área (la queremos meter en PROD2 mismo día → choca con A)
    pid_b = _seed_produccion("PROD-TEST-CONFLIC-B", "2026-05-28", area_id=None)
    try:
        r = c.post("/api/planta/asignar-areas",
                   json={"asignaciones": [{"id": pid_b, "area_id": pr2_id}]},
                   headers=csrf_headers())
        d = r.get_json()
        # Asigna pero reporta warning
        assert d["asignados"] == 1
        assert len(d["warnings"]) == 1
        assert d["warnings"][0]["id"] == pid_b
        assert any(x["id"] == pid_a for x in d["warnings"][0]["choca_con"])
    finally:
        _cleanup_pid(pid_a); _cleanup_pid(pid_b)


def test_post_rechaza_lista_vacia(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/planta/asignar-areas",
               json={"asignaciones": []}, headers=csrf_headers())
    assert r.status_code == 400


def test_post_rechaza_demasiadas(app, db_clean):
    c = _login(app, "sebastian")
    asignaciones = [{"id": i, "area_id": None} for i in range(201)]
    r = c.post("/api/planta/asignar-areas",
               json={"asignaciones": asignaciones}, headers=csrf_headers())
    assert r.status_code == 400


def test_post_id_inexistente_reporta_error(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/planta/asignar-areas",
               json={"asignaciones": [{"id": 99999999, "area_id": None}]},
               headers=csrf_headers())
    d = r.get_json()
    assert d["asignados"] == 0
    assert len(d["errores"]) == 1


def test_post_area_inexistente_reporta_error(app, db_clean):
    c = _login(app, "sebastian")
    pid = _seed_produccion("PROD-TEST-AREA-INV", "2026-05-30")
    try:
        r = c.post("/api/planta/asignar-areas",
                   json={"asignaciones": [{"id": pid, "area_id": 99999}]},
                   headers=csrf_headers())
        d = r.get_json()
        assert d["asignados"] == 0
        assert len(d["errores"]) == 1
        assert "área no existe" in d["errores"][0]["error"].lower() \
            or "no existe" in d["errores"][0]["error"].lower()
    finally:
        _cleanup_pid(pid)


# ── PARSER [CODIGO] en sync ──────────────────────────────────────────

def test_parser_codigo_corto():
    """Verifica que el parser extrae [FAB1], [FYE2] etc del título."""
    import re
    AREA_ALIAS = {
        'FAB1': 'PROD1', 'FYE2': 'PROD2', 'FYE3': 'PROD3', 'ENV2': 'PROD4',
        'ENV1': 'ENV1',
        'PROD1': 'PROD1', 'PROD2': 'PROD2', 'PROD3': 'PROD3', 'PROD4': 'PROD4',
    }
    casos = [
        ('[FAB1] Gel Hidratante 50ml ~5kg', 'PROD1'),
        ('[FYE2] Blush Balm ~3kg', 'PROD2'),
        ('[FYE3] Booster Tensor ~2kg', 'PROD3'),
        ('[ENV2] Suero envasado', 'PROD4'),
        ('[ENV1] Algo en envasado', 'ENV1'),
        ('  [PROD1] espacios delante', 'PROD1'),
        ('Sin código al inicio', None),
        ('[XXX] codigo invalido', None),
    ]
    for titulo, esperado in casos:
        m = re.match(r'\s*\[([A-Z0-9]{3,5})\]', titulo)
        if not m:
            assert esperado is None, f"caso '{titulo}' debió matchear"
            continue
        codigo_corto = m.group(1).upper()
        codigo_real = AREA_ALIAS.get(codigo_corto)
        assert codigo_real == esperado, f"caso '{titulo}' → {codigo_real} != {esperado}"


# ── Página renderiza ─────────────────────────────────────────────────

def test_pagina_asignar_areas_renderiza(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/asignar-areas")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Asignar áreas" in body
    assert "/api/planta/asignar-areas" in body
    assert "Aplicar sugerencias" in body
    assert "Confirmar cambios" in body


def test_pagina_asignar_areas_redirect_sin_login(client, db_clean):
    r = client.get("/asignar-areas", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.location
