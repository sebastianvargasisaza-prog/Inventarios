"""Renombrar producto (admin.py · /api/admin/renombrar-producto).

Cambia producto_nombre/producto de forma consistente en las tablas vivas (formula_headers,
formula_items, producto_presentaciones, produccion_programada, producciones). Los SKU de
Shopify NO cambian → el enlace a Necesidades sobrevive. dry-run no escribe. M1/M2.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

VIEJO = "ZZ RENAME TEST ACIDO KOJICO"
NUEVO = "ZZ RENAME TEST"


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    for nom in (VIEJO, NUEVO):
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (nom,))
        conn.execute("DELETE FROM producciones WHERE producto=?", (nom,))
        conn.execute("DELETE FROM produccion_checklist WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM produccion_envasado WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (nom,))
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", ("MPRN01",))
    conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, proveedor, activo) "
                 "VALUES ('MPRN01','Glicerina','GLYCERIN','Test',1)")
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, producto_canonico, sku_principal) "
                 "VALUES (?,?,1,?,?)", (VIEJO, 10, VIEJO, "SKU-RN"))
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?,?,?,?,?)", (VIEJO, "MPRN01", "Glicerina", 100, 10000))
    conn.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, sku_shopify, volumen_ml, activo) "
                 "VALUES (?,?,?,?,?,1)", (VIEJO, "P150", "150 ml", "LIMILUM150", 150))
    conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                 "VALUES (?, date('now','-5 hours','+5 days'), 10, 1, 'programado', 'eos_plan')", (VIEJO,))
    conn.execute("INSERT INTO producciones (producto, fecha) VALUES (?, date('now','-5 hours'))", (VIEJO,))
    # tablas de producción/EBR que el rename ahora también cubre
    conn.execute("INSERT INTO produccion_checklist (producto_nombre, fecha_planeada, item_tipo, descripcion, estado) "
                 "VALUES (?, '2026-06-20', 'envase', 'check', 'pendiente')", (VIEJO,))
    conn.execute("INSERT INTO produccion_envasado (produccion_id, producto_nombre, lote, iniciado_at, estado) "
                 "VALUES (1, ?, 'L-RN', '2026-06-20 08:00:00', 'en_proceso')", (VIEJO,))
    # MBR aprobado (inmutable) · NO se renombra · solo se reporta
    conn.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                 "VALUES (?, 1, 'aprobado', 10000, 'sebastian')", (VIEJO,))
    conn.commit()
    conn.close()


def test_dry_run_reporta_y_no_escribe(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/admin/renombrar-producto", json={
        "viejo": "zz rename test acido kojico", "nuevo": NUEVO, "dry_run": 1}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    j = r.get_json()
    assert j["nombre_real"] == VIEJO
    assert j["ocurrencias"]["formula_items"] == 1
    assert j["ocurrencias"]["produccion_programada"] == 1
    assert j["ocurrencias"]["produccion_checklist"] == 1
    assert j["ocurrencias"]["produccion_envasado"] == 1
    assert j["mbr"]["total"] == 1 and j["mbr"]["aprobados_inmutables"] == 1
    assert j["shopify_mapeado"] is True
    assert any(s["sku_shopify"] == "LIMILUM150" for s in j["shopify_skus"])
    # no escribió: el viejo sigue
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM formula_headers WHERE producto_nombre=?", (VIEJO,)).fetchone()[0]
    conn.close()
    assert n == 1


def test_aplica_rename_consistente_y_conserva_sku(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/admin/renombrar-producto", json={
        "viejo": VIEJO, "nuevo": NUEVO, "dry_run": 0}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    assert r.get_json()["aplicado"] is True
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # el viejo ya no está en ninguna tabla viva
    assert conn.execute("SELECT COUNT(*) FROM formula_headers WHERE producto_nombre=?", (VIEJO,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (VIEJO,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto=?", (VIEJO,)).fetchone()[0] == 0
    # el nuevo tiene todo, incluido producto_canonico actualizado
    h = conn.execute("SELECT producto_canonico, sku_principal FROM formula_headers WHERE producto_nombre=?", (NUEVO,)).fetchone()
    assert h[0] == NUEVO and h[1] == "SKU-RN"
    assert conn.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (NUEVO,)).fetchone()[0] == 1
    # el SKU de Shopify se conservó bajo el nuevo nombre (Necesidades lo verá)
    sku = conn.execute("SELECT sku_shopify FROM producto_presentaciones WHERE producto_nombre=?", (NUEVO,)).fetchone()
    assert sku and sku[0] == "LIMILUM150"
    assert conn.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto=?", (NUEVO,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM producciones WHERE producto=?", (NUEVO,)).fetchone()[0] == 1
    # producción/EBR vivas también renombradas
    assert conn.execute("SELECT COUNT(*) FROM produccion_checklist WHERE producto_nombre=?", (NUEVO,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM produccion_envasado WHERE producto_nombre=?", (NUEVO,)).fetchone()[0] == 1
    # MBR aprobado NO se renombra (inmutable · GMP) → conserva el nombre viejo
    assert conn.execute("SELECT COUNT(*) FROM mbr_templates WHERE producto_nombre=?", (VIEJO,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM mbr_templates WHERE producto_nombre=?", (NUEVO,)).fetchone()[0] == 0
    conn.close()


def test_aborta_si_nuevo_ya_existe(app, db_clean):
    _seed()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,?,1)", (NUEVO, 5))
    conn.commit()
    conn.close()
    c = _login(app)
    r = c.post("/api/admin/renombrar-producto", json={
        "viejo": VIEJO, "nuevo": NUEVO, "dry_run": 0}, headers=_csrf(c))
    assert r.status_code == 409, r.data


def test_requiere_admin(app, db_clean):
    c = app.test_client()
    r = c.post("/api/admin/renombrar-producto", json={"viejo": "x", "nuevo": "y"}, headers=csrf_headers())
    assert r.status_code in (401, 403)
