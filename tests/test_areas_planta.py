"""Áreas de Planta (admin.py · /api/admin/areas-planta + /set).

Cruza areas_planta con equipos_planta (la verdad): nº equipos, capacidad real, flags oficial
/duplicado. Set activo/capacidad para limpiar duplicados (PROD vs FAB) y fijar tanque. Admin.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM areas_planta WHERE codigo IN ('ZFAB','ZPROD')")
    conn.execute("DELETE FROM equipos_planta WHERE codigo='ZTANK'")
    # área buena (con equipo) y su duplicado (sin equipo)
    conn.execute("INSERT INTO areas_planta (codigo, nombre, puede_producir, puede_envasar, tipo, activo, orden, marmita_ml) "
                 "VALUES ('ZFAB','ZZ Fabricación X',1,1,'produccion',1,90,NULL)")
    conn.execute("INSERT INTO areas_planta (codigo, nombre, puede_producir, puede_envasar, tipo, activo, orden, marmita_ml) "
                 "VALUES ('ZPROD','ZZ Fabricación X',1,1,'produccion',1,91,NULL)")
    # equipo (tanque 400L) en el área buena
    conn.execute("INSERT INTO equipos_planta (codigo, nombre, area_codigo, tipo, capacidad_litros) "
                 "VALUES ('ZTANK','Tanque 400L','ZFAB','tanque',400)")
    conn.commit()
    conn.close()


def test_lista_cruza_equipos_y_marca_duplicado(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get("/api/admin/areas-planta")
    assert r.status_code == 200, r.data
    by = {a["codigo"]: a for a in r.get_json()["areas"]}
    assert by["ZFAB"]["n_equipos"] == 1 and by["ZFAB"]["cap_litros"] == 400
    assert by["ZFAB"]["oficial"] is True
    assert by["ZPROD"]["n_equipos"] == 0          # duplicado sin equipos
    assert by["ZFAB"]["duplicado"] is True and by["ZPROD"]["duplicado"] is True


def test_set_capacidad_y_desactivar(app, db_clean):
    _seed()
    c = _login(app)
    by = {a["codigo"]: a for a in c.get("/api/admin/areas-planta").get_json()["areas"]}
    # fijar capacidad de ZFAB = 400 (del tanque) + desactivar el duplicado ZPROD
    r1 = c.post("/api/admin/areas-planta/set", json={"area_id": by["ZFAB"]["id"], "marmita_ml": 400}, headers=_csrf(c))
    r2 = c.post("/api/admin/areas-planta/set", json={"area_id": by["ZPROD"]["id"], "activo": False}, headers=_csrf(c))
    assert r1.status_code == 200 and r2.status_code == 200
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cap = conn.execute("SELECT marmita_ml FROM areas_planta WHERE codigo='ZFAB'").fetchone()[0]
    act = conn.execute("SELECT activo FROM areas_planta WHERE codigo='ZPROD'").fetchone()[0]
    conn.close()
    assert cap == 400 and act == 0


def test_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")
    assert c.get("/api/admin/areas-planta").status_code in (401, 403)
    r = c.post("/api/admin/areas-planta/set", json={"area_id": 1, "activo": True}, headers=_csrf(c))
    assert r.status_code in (401, 403)
