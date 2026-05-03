"""Tests de los 5 amarillos completados en Direccion Tecnica:
6. Editar desde UI (PATCH ya existia · UI nueva)
7. Fichas con formula_id (POST + PATCH + GET incluye columna)
8. Paginacion + busqueda (frontend, verifica HTML)
9. Versionado en Fichas + INVIMA + SGD (tabla tecnica_versiones)
10. Links cross-modulo en HTML
"""
import json
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="hernando"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_formula(codigo, nombre="Test Formula"):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO formulas_maestras (codigo, nombre, version, tipo, estado) VALUES (?, ?, '1.0', 'COSMETICO', 'Vigente')",
        (codigo, nombre))
    fid = cur.lastrowid
    conn.commit(); conn.close()
    return fid


def _cleanup(table, where, params):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
    conn.commit(); conn.close()


# ════════════════════════════════════════════════════════════════════
#  #10 LINKS CROSS-MODULO
# ════════════════════════════════════════════════════════════════════

def test_pagina_tecnica_tiene_links_cross_modulo(app, db_clean):
    c = _login(app, "hernando")
    r = c.get("/tecnica")
    body = r.get_data(as_text=True)
    for href in ('/aseguramiento', '/calidad', '/compliance', '/espagiria'):
        assert f'href="{href}"' in body, f"falta link a {href}"


# ════════════════════════════════════════════════════════════════════
#  #7 FORMULA_ID en Fichas
# ════════════════════════════════════════════════════════════════════

def test_ficha_post_acepta_formula_id(app, db_clean):
    c = _login(app, "hernando")
    fid = _seed_formula("TEST-FFOR-001")
    try:
        r = c.post("/api/tecnica/fichas",
                   json={"codigo": "TEST-FT-001", "nombre": "Ficha vinculada",
                         "formula_id": fid},
                   headers=csrf_headers())
        assert r.status_code == 200
        ficha_id = r.get_json()["id"]
        # Verificar persistencia
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute("SELECT formula_id FROM fichas_tecnicas WHERE id=?",
                           (ficha_id,)).fetchone()
        conn.close()
        assert row[0] == fid
    finally:
        _cleanup("fichas_tecnicas", "codigo=?", ("TEST-FT-001",))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_ficha_patch_acepta_formula_id(app, db_clean):
    cs = _login(app, "sebastian")
    fid_a = _seed_formula("TEST-FF-A")
    fid_b = _seed_formula("TEST-FF-B")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO fichas_tecnicas (codigo, nombre, formula_id, version, estado) VALUES ('TEST-FT-PATCH', 'Test', ?, '1.0', 'Vigente')",
        (fid_a,))
    fic_id = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = cs.patch(f"/api/tecnica/fichas/{fic_id}",
                     json={"formula_id": fid_b}, headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute("SELECT formula_id FROM fichas_tecnicas WHERE id=?",
                           (fic_id,)).fetchone()
        conn.close()
        assert row[0] == fid_b
    finally:
        _cleanup("fichas_tecnicas", "id=?", (fic_id,))
        _cleanup("formulas_maestras", "id IN (?,?)", (fid_a, fid_b))


def test_pagina_tecnica_tiene_dropdown_formula_en_fichas(app, db_clean):
    c = _login(app, "hernando")
    r = c.get("/tecnica")
    body = r.get_data(as_text=True)
    assert 'id="ft-formula"' in body
    assert "FORMULAS_CACHE" in body


# ════════════════════════════════════════════════════════════════════
#  #9 VERSIONADO en Fichas + INVIMA + SGD
# ════════════════════════════════════════════════════════════════════

def test_versionado_ficha_snapshot_pre_update(app, db_clean):
    cs = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO fichas_tecnicas (codigo, nombre, version, estado) VALUES ('TEST-FT-VER', 'Original', '1.0', 'Vigente')")
    fic_id = cur.lastrowid; conn.commit(); conn.close()
    try:
        # Modificar la ficha 2 veces
        cs.patch(f"/api/tecnica/fichas/{fic_id}",
                 json={"nombre": "Modificado v2", "motivo_cambio": "Cambio nombre"},
                 headers=csrf_headers())
        cs.patch(f"/api/tecnica/fichas/{fic_id}",
                 json={"nombre": "Modificado v3"}, headers=csrf_headers())
        # Listar versiones
        r = cs.get(f"/api/tecnica/fichas/{fic_id}/versiones")
        assert r.status_code == 200
        versiones = r.get_json()
        assert len(versiones) == 2
        # version_num descendente
        assert versiones[0]["version_num"] == 2
        assert versiones[1]["version_num"] == 1
    finally:
        _cleanup("tecnica_versiones", "entidad='ficha' AND registro_id=?", (fic_id,))
        _cleanup("fichas_tecnicas", "id=?", (fic_id,))


def test_versionado_invima_snapshot_pre_update(app, db_clean):
    cs = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO registros_invima (producto, num_registro, estado) VALUES ('Test Prod Versiones', 'NSC-VER-001', 'Vigente')")
    inv_id = cur.lastrowid; conn.commit(); conn.close()
    try:
        cs.patch(f"/api/tecnica/invima/{inv_id}",
                 json={"num_registro": "NSC-VER-001-MOD"}, headers=csrf_headers())
        r = cs.get(f"/api/tecnica/invima/{inv_id}/versiones")
        assert r.status_code == 200
        versiones = r.get_json()
        assert len(versiones) == 1
        assert versiones[0]["version_num"] == 1
        # Detalle
        r2 = cs.get(f"/api/tecnica/invima/{inv_id}/versiones/{versiones[0]['id']}")
        assert r2.status_code == 200
        snap = r2.get_json()
        assert "snapshot" in snap
        assert snap["snapshot"]["num_registro"] == "NSC-VER-001"  # estado original
    finally:
        _cleanup("tecnica_versiones", "entidad='invima' AND registro_id=?", (inv_id,))
        _cleanup("registros_invima", "id=?", (inv_id,))


def test_versionado_sgd_snapshot_pre_update(app, db_clean):
    cs = _login(app, "sebastian")
    # Sembrar en sgd_documentos (rico, unificado) con codigo formato AAA-BBB-NNN
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='ASG-PRO-503'")
    cur = conn.execute(
        """INSERT INTO sgd_documentos
           (codigo, area, tipo_doc, numero, titulo, version_actual, estado, vigente_desde)
           VALUES ('ASG-PRO-503','ASG','PRO',503,'Original','1.0','vigente',date('now'))""")
    sgd_id = cur.lastrowid; conn.commit(); conn.close()
    try:
        cs.patch(f"/api/tecnica/documentos/{sgd_id}",
                 json={"version": "1.1"}, headers=csrf_headers())
        r = cs.get(f"/api/tecnica/documentos/{sgd_id}/versiones")
        assert r.status_code == 200
        versiones = r.get_json()
        assert len(versiones) == 1
    finally:
        _cleanup("tecnica_versiones", "entidad='sgd' AND registro_id=?", (sgd_id,))
        _cleanup("sgd_documentos", "id=?", (sgd_id,))


def test_versionado_entidad_invalida(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/tecnica/foobar/1/versiones")
    assert r.status_code == 400


def test_versionado_version_inexistente_404(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/tecnica/fichas/99999/versiones/99999")
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
#  #6 Editor UI (existencia de funciones JS)
# ════════════════════════════════════════════════════════════════════

def test_pagina_tecnica_tiene_editor_modal(app, db_clean):
    c = _login(app, "hernando")
    r = c.get("/tecnica")
    body = r.get_data(as_text=True)
    assert "EDITOR_CONFIG" in body
    assert "abrirEditor" in body
    assert "editarFormula" in body
    assert "editarFicha" in body
    assert "editarInvima" in body
    assert "editarSgd" in body


# ════════════════════════════════════════════════════════════════════
#  #8 Paginacion + busqueda
# ════════════════════════════════════════════════════════════════════

def test_pagina_tecnica_tiene_paginacion_y_busqueda(app, db_clean):
    c = _login(app, "hernando")
    r = c.get("/tecnica")
    body = r.get_data(as_text=True)
    # Helpers JS
    assert "_paginar" in body
    assert "_filtrar" in body
    assert "TBL_STATE" in body
    assert "buscarEn" in body
    assert "cambiarPagina" in body
    # Caja de busqueda en cada tab
    assert "buscarEn('formulas'" in body
    assert "buscarEn('fichas'" in body
    assert "buscarEn('invima'" in body
    assert "buscarEn('sgd'" in body
    # Divs de paginacion
    for tab in ('pg-formulas','pg-fichas','pg-invima','pg-sgd'):
        assert f'id="{tab}"' in body
