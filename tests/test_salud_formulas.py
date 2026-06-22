"""Salud de Fórmulas Maestras (admin.py · /api/admin/salud-formulas).

READ-ONLY: por fórmula activa reporta nº ítems, suma %, e ingredientes que NO resuelven a
un MP activo (mismo resolver del descuento). Banderas SUMA / ROTOS / SIN_ITEMS / DUPLICADO.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

SANA, SUMA, ROTO, CONAGUA = "ZZ SALUD SANA", "ZZ SALUD SUMA", "ZZ SALUD ROTO", "ZZ SALUD CONAGUA"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _it(conn, prod, mid, mnom, pct):
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?,?,?,?,?)", (prod, mid, mnom, pct, pct * 100))


def _seed():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    for nom in (SANA, SUMA, ROTO, CONAGUA):
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (nom,))
        conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (nom,))
    # ACTIVOS al insertar (el trigger SQLite/PG exige material activo en formula_items)
    for cod in ("MPSFOK", "MPSFLATER"):
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) VALUES (?,?,?,1)",
                     (cod, "ZZSALUD " + cod, "T"))
    # MP agua: controla_stock=0 (infinita)
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MPSFAGUA'")
    conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo, controla_stock) "
                 "VALUES ('MPSFAGUA','AGUA DESIONIZADA TEST','T',1,0)")
    for nom in (SANA, SUMA, ROTO, CONAGUA):
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,10,1)", (nom,))
    _it(conn, SANA, "MPSFOK", "ZZSALUDOKMAT", 100)          # ok
    _it(conn, SUMA, "MPSFOK", "ZZSALUDOKMAT", 90)           # suma 90 · SIN agua → falta agua
    _it(conn, ROTO, "MPSFOK", "ZZSALUDOKMAT", 50)           # ok
    _it(conn, ROTO, "MPSFLATER", "ZZSALUDLATERMAT", 50)     # válido al insertar
    _it(conn, CONAGUA, "MPSFAGUA", "Agua desionizada", 80)  # suma 80 · CON agua → falta activo
    conn.commit()
    # MPSFLATER se DESCONTINÚA después → ROTO queda con 1 código inactivo (caso real)
    conn.execute("UPDATE maestro_mps SET activo=0 WHERE codigo_mp='MPSFLATER'")
    conn.commit()
    conn.close()


def test_salud_formulas(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get("/api/admin/salud-formulas")
    assert r.status_code == 200, r.data
    j = r.get_json()
    by = {f["producto"]: f for f in j["formulas"]}
    assert by[SANA]["ok"] is True and by[SANA]["suma"] == 100
    assert "SUMA" in by[SUMA]["flags"] and by[SUMA]["suma"] == 90
    # incompleta SIN agua → diag apunta a falta de AGUA
    assert by[SUMA]["falta"] == 10 and by[SUMA]["tiene_agua"] is False
    assert "AGUA" in by[SUMA]["diag"]
    # incompleta CON agua → diag apunta a falta de un ACTIVO
    assert by[CONAGUA]["tiene_agua"] is True and "ACTIVO" in by[CONAGUA]["diag"]
    assert "ROTOS" in by[ROTO]["flags"]
    assert len(by[ROTO]["rotos"]) == 1     # MPSFLATER (desactivado después)
    assert by[ROTO]["rotos"][0]["codigo"] == "MPSFLATER"
    # resumen coherente
    assert j["resumen"]["total"] >= 3
    assert j["resumen"]["con_rotos"] >= 1 and j["resumen"]["suma_mala"] >= 1


def test_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")
    r = c.get("/api/admin/salud-formulas")
    assert r.status_code in (401, 403)
