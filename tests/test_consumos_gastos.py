"""Consumos / Gastos Generales (compras.py).

- La recepción de una OC de categoría de consumo (EPP, papelería, aseo...) NO entra al kardex MP
  (gate en recibir_oc → 409 OC_CONSUMO_SIN_RECEPCION).
- /api/compras/consumos/tendencia: gasto por categoría/mes + alerta cuando el último mes sube
  >umbral sobre el promedio previo.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def test_recepcion_consumo_no_entra_a_mp(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-EPP-TEST'")
    conn.execute("DELETE FROM movimientos WHERE numero_oc='OC-EPP-TEST'")
    conn.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria) "
                 "VALUES ('OC-EPP-TEST','2026-06-01','Autorizada','COMPETRI',100000,'EPP')")
    conn.commit(); conn.close()
    c = _login(app)
    r = c.post("/api/ordenes-compra/OC-EPP-TEST/recibir", json={"items": []}, headers=_csrf(c))
    assert r.status_code == 409, r.data
    assert r.get_json().get("codigo") == "OC_CONSUMO_SIN_RECEPCION"
    # y NO se creó ningún movimiento de MP para esa OC
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM movimientos WHERE numero_oc='OC-EPP-TEST'").fetchone()[0]
    conn.close()
    assert n == 0


def test_tendencia_detecta_subida(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE 'OC-CONS-%'")
    # Papelería: estable ~50k tres meses, salta a 200k el último → alerta
    datos = [("OC-CONS-1", "2026-03-10", 50000, "Papeleria/Oficina"),
             ("OC-CONS-2", "2026-04-10", 50000, "Papeleria/Oficina"),
             ("OC-CONS-3", "2026-05-10", 50000, "Papeleria/Oficina"),
             ("OC-CONS-4", "2026-06-10", 200000, "Papeleria/Oficina"),
             ("OC-CONS-5", "2026-06-12", 80000, "EPP")]
    for num, fecha, val, cat in datos:
        conn.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria) "
                     "VALUES (?,?,?,?,?,?)", (num, fecha, "Pagada", "PROV", val, cat))
    conn.commit(); conn.close()
    c = _login(app)
    j = c.get("/api/compras/consumos/tendencia?meses=8").get_json()
    assert j["ok"]
    by = {x["categoria"]: x for x in j["categorias"]}
    assert "Papeleria/Oficina" in by
    pap = by["Papeleria/Oficina"]
    assert pap["ultimo"] == 200000 and pap["promedio_previo"] == 50000
    assert pap["variacion_pct"] == 300.0 and pap["alerta"] is True
    # aparece en alertas
    assert any(a["categoria"] == "Papeleria/Oficina" for a in j["alertas"])
    # MP NO debe aparecer (no es categoría de consumo)
    assert "MP" not in by and "Materia Prima" not in by


def test_pagina_render(app, db_clean):
    c = _login(app)
    r = c.get("/compras/consumos")
    assert r.status_code == 200
    assert "Consumos / Gastos Generales" in r.get_data(as_text=True)


def test_catalogo_consumibles_crear_listar_solicitar(app, db_clean):
    c = _login(app)
    # crear consumible
    r = c.post("/api/compras/consumibles",
               json={"nombre": "Guantes nitrilo M", "categoria": "EPP", "proveedor": "COMPETRI",
                     "precio_referencia": 1200, "unidad": "caja"}, headers=_csrf(c))
    assert r.status_code == 201, r.data
    cid = r.get_json()["id"]
    # listar
    j = c.get("/api/compras/consumibles").get_json()
    by = {x["nombre"]: x for x in j["consumibles"]}
    assert "Guantes nitrilo M" in by and by["Guantes nitrilo M"]["categoria"] == "EPP"
    # solicitar (vía el endpoint real de SOL, como hace la página) → SOL con categoría EPP
    r2 = c.post("/api/solicitudes-compra",
                json={"categoria": "EPP", "urgencia": "Normal", "observaciones": "Consumible",
                      "items": [{"codigo_mp": "", "nombre_mp": "Guantes nitrilo M", "cantidad_g": 3,
                                 "unidad": "caja", "valor_estimado": 3600, "proveedor_sugerido": "COMPETRI"}]},
                headers=_csrf(c))
    assert r2.status_code in (200, 201), r2.data
    # la SOL quedó con categoría EPP (de consumo)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cat = conn.execute("SELECT categoria FROM solicitudes_compra WHERE categoria='EPP' ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert cat and cat[0] == "EPP"
    # desactivar
    assert c.delete(f"/api/compras/consumibles/{cid}", headers=_csrf(c)).status_code == 200
    j2 = c.get("/api/compras/consumibles").get_json()
    assert "Guantes nitrilo M" not in {x["nombre"] for x in j2["consumibles"]}
