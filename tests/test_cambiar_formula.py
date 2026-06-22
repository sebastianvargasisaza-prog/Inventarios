"""Cambio de fórmula (admin.py · /api/admin/cambiar-formula).

Archiva la receta vigente (header '[ARCHIVADA <fecha>]' activo=0 con SUS ítems) y carga
una nueva bajo el nombre canónico, conservando el header (Shopify/SKU). NUNCA DELETE de
header (GMP). Valida los códigos nuevos contra el maestro vivo ANTES de escribir (M19/M38).
Reversible: la receta vieja queda consultable.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ LIMPIADOR TEST KOJICO"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed(mps, lote_kg=90, shopify="SHOP-123"):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # limpiar el set conocido ANTES (db_clean no resetea maestro_mps entre tests →
    # un código sembrado por otro test no debe sobrevivir y falsear el preflight)
    for cod in ("MPOLD01", "MPOLD02", "MPNEW01", "MPNEW02"):
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
    for cod, comercial, inci in mps:
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, proveedor, activo) "
                     "VALUES (?,?,?,?,1)", (cod, comercial, inci, "Test"))
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre LIKE ?", (PROD + "%",))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre LIKE ?", (PROD + "%",))
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, unidad_base_g, activo, "
                 "shopify_id, sku_principal, producto_canonico) VALUES (?,?,?,1,?,?,?)",
                 (PROD, lote_kg, lote_kg * 1000, shopify, "SKU-1", PROD))
    # receta vieja: 2 ítems (uno con un MP que luego "desactivamos" para probar archivado seguro)
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?,?,?,?,?)", (PROD, "MPOLD01", "Viejo A", 80, 72000))
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?,?,?,?,?)", (PROD, "MPOLD02", "Viejo B", 20, 18000))
    conn.commit()
    conn.close()


def _new_items():
    return [
        {"codigo": "MPNEW01", "pct": 60},
        {"codigo": "MPNEW02", "pct": 40},
    ]


def test_dry_run_no_escribe_y_halla_nombre_real(app, db_clean):
    _seed([("MPOLD01", "Viejo A", "OLDA"), ("MPOLD02", "Viejo B", "OLDB"),
           ("MPNEW01", "Glicerina", "GLYCERIN"), ("MPNEW02", "Acido kojico", "KOJIC ACID")])
    c = _login(app)
    # match por nombre normalizado (sin acentos / minúsculas)
    r = c.post("/api/admin/cambiar-formula", json={
        "producto": "zz limpiador test kojico", "lote_kg": 10,
        "items": _new_items(), "dry_run": 1}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    j = r.get_json()
    assert j["dry_run"] is True
    assert j["nombre_real"] == PROD
    assert j["items_actuales"] == 2 and j["items_nuevos"] == 2
    # no escribió: sigue con la receta vieja
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    arch = conn.execute("SELECT COUNT(*) FROM formula_headers WHERE producto_nombre LIKE ?",
                        (PROD + " [ARCHIVADA%",)).fetchone()[0]
    conn.close()
    assert n == 2 and arch == 0


def test_aplicar_archiva_y_carga(app, db_clean):
    _seed([("MPOLD01", "Viejo A", "OLDA"), ("MPOLD02", "Viejo B", "OLDB"),
           ("MPNEW01", "Glicerina", "GLYCERIN"), ("MPNEW02", "Acido kojico", "KOJIC ACID")])
    c = _login(app)
    r = c.post("/api/admin/cambiar-formula", json={
        "producto": PROD, "lote_kg": 10, "items": _new_items(), "dry_run": 0}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    j = r.get_json()
    assert j["aplicado"] is True and j["items_cargados"] == 2
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # canónico ahora tiene la receta NUEVA (2 ítems nuevos)
    nuevos = conn.execute("SELECT material_id FROM formula_items WHERE producto_nombre=? ORDER BY material_id",
                          (PROD,)).fetchall()
    assert [x[0] for x in nuevos] == ["MPNEW01", "MPNEW02"]
    # lote default actualizado + header canónico sigue activo con su Shopify
    h = conn.execute("SELECT lote_size_kg, activo, shopify_id, sku_principal FROM formula_headers "
                     "WHERE producto_nombre=?", (PROD,)).fetchone()
    assert h[0] == 10 and h[1] == 1 and h[2] == "SHOP-123" and h[3] == "SKU-1"
    # la receta vieja quedó conservada en el [ARCHIVADA] activo=0 (consultable)
    arch = conn.execute("SELECT producto_nombre, activo FROM formula_headers WHERE producto_nombre LIKE ?",
                        (PROD + " [ARCHIVADA%",)).fetchone()
    assert arch is not None and arch[1] == 0
    viejos = conn.execute("SELECT material_id FROM formula_items WHERE producto_nombre=? ORDER BY material_id",
                          (arch[0],)).fetchall()
    assert [x[0] for x in viejos] == ["MPOLD01", "MPOLD02"]
    # el archivado NO se queda con el enlace Shopify (no duplica)
    arch_shop = conn.execute("SELECT COALESCE(shopify_id,'') FROM formula_headers WHERE producto_nombre=?",
                             (arch[0],)).fetchone()[0]
    assert arch_shop == ""
    conn.close()


def test_aborta_si_codigo_nuevo_no_existe(app, db_clean):
    _seed([("MPOLD01", "Viejo A", "OLDA"), ("MPOLD02", "Viejo B", "OLDB"),
           ("MPNEW01", "Glicerina", "GLYCERIN")])  # MPNEW02 NO existe
    c = _login(app)
    r = c.post("/api/admin/cambiar-formula", json={
        "producto": PROD, "lote_kg": 10, "items": _new_items(), "dry_run": 0}, headers=_csrf(c))
    assert r.status_code == 400, r.data
    j = r.get_json()
    assert "MPNEW02" in j.get("faltan", [])
    # NO tocó nada: la receta vieja sigue intacta
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    conn.close()
    assert n == 2


def test_aborta_si_no_suma_100(app, db_clean):
    _seed([("MPOLD01", "Viejo A", "OLDA"), ("MPOLD02", "Viejo B", "OLDB"),
           ("MPNEW01", "Glicerina", "GLYCERIN"), ("MPNEW02", "Acido kojico", "KOJIC ACID")])
    c = _login(app)
    r = c.post("/api/admin/cambiar-formula", json={
        "producto": PROD, "lote_kg": 10,
        "items": [{"codigo": "MPNEW01", "pct": 60}, {"codigo": "MPNEW02", "pct": 30}],  # 90
        "dry_run": 0}, headers=_csrf(c))
    assert r.status_code == 400, r.data
    assert r.get_json().get("suma_100") is False


def test_requiere_admin(app, db_clean):
    c = app.test_client()
    r = c.post("/api/admin/cambiar-formula", json={"producto": "x", "lote_kg": 1, "items": []},
               headers=csrf_headers())
    assert r.status_code in (401, 403)
