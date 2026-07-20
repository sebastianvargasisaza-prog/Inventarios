"""Inteligencia de discrepancias de compra (Sebastián 19-jul): por ítem, descompone la subida del gasto
en efecto PRECIO vs CANTIDAD ('20 hojas → 40 hojas: cantidad +100%')."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302
    return c


def _oc_item(numero, fecha, cat, nombre, cant, precio):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria, creado_por) "
              "VALUES (?, ?, 'Pagada', 'Prov', ?, ?, 'test')", (numero, fecha, cant * precio, cat))
    c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal) "
              "VALUES (?, '', ?, ?, ?, ?)", (numero, nombre, cant, precio, cant * precio))
    conn.commit(); conn.close()


def test_discrepancia_por_cantidad(app, db_clean):
    # mismo item, precio igual, cantidad se duplica → subida por CANTIDAD
    _oc_item("OC-D1", "2026-05-15", "Papeleria/Oficina", "HOJAS-DISCREP", 20, 10)
    _oc_item("OC-D2", "2026-06-15", "Papeleria/Oficina", "HOJAS-DISCREP", 40, 10)
    c = _login(app)
    d = c.get("/api/compras/discrepancias?meses=6&umbral=25&grupo=consumo").get_json()
    it = next((x for x in d["items"] if x["item"] == "HOJAS-DISCREP"), None)
    assert it is not None, "el ítem debe salir"
    assert it["alerta"] is True
    assert it["var_cantidad_pct"] == 100.0, "cantidad se duplicó"
    assert (it["var_precio_pct"] or 0) == 0.0, "el precio no cambió"
    assert it["efecto_cantidad"] > it["efecto_precio"], "la subida la explica la CANTIDAD"
    assert "cantidad" in it["razon"]


def test_discrepancia_por_precio(app, db_clean):
    # misma cantidad, precio sube → subida por PRECIO
    _oc_item("OC-D3", "2026-05-15", "MP", "MPX-DISCREP", 100, 50)
    _oc_item("OC-D4", "2026-06-15", "MP", "MPX-DISCREP", 100, 80)
    c = _login(app)
    d = c.get("/api/compras/discrepancias?meses=6&umbral=25&grupo=mp").get_json()
    it = next((x for x in d["items"] if x["item"] == "MPX-DISCREP"), None)
    assert it is not None
    assert it["alerta"] is True
    assert it["var_precio_pct"] == 60.0, "precio subió 60%"
    assert (it["var_cantidad_pct"] or 0) == 0.0
    assert it["efecto_precio"] > it["efecto_cantidad"], "la subida la explica el PRECIO"
    assert "precio" in it["razon"]


def test_pagina_discrepancias_render(app, db_clean):
    c = _login(app)
    r = c.get("/compras/discrepancias")
    assert r.status_code == 200
    assert "Discrepancias de compra" in r.get_data(as_text=True)


def _seed_sol(numero, fecha, solicitante, nombre, cant, oc=""):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO solicitudes_compra (numero, fecha, estado, solicitante, numero_oc) "
              "VALUES (?, ?, 'Aprobada', ?, ?)", (numero, fecha, solicitante, oc))
    c.execute("INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, cantidad_g, unidad) "
              "VALUES (?, '', ?, ?, 'uds')", (numero, nombre, cant))
    conn.commit(); conn.close()


def test_trazabilidad_item_timeline(app, db_clean):
    # Alejandro pide → OC de Catalina → llega y recibe Luz
    _seed_sol("SOL-TZ1", "2026-06-01", "Alejandro", "TAPA-NEGRA-TZ", 500, "OC-TZ1")
    _oc_item("OC-TZ1", "2026-06-05", "MEE", "TAPA-NEGRA-TZ", 500, 3)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion='2026-06-10', recibido_por='Luz' WHERE numero_oc='OC-TZ1'")
    conn.execute("UPDATE ordenes_compra_items SET cantidad_recibida_g=500 WHERE numero_oc='OC-TZ1'")
    conn.commit(); conn.close()
    c = _login(app)
    d = c.get("/api/compras/trazabilidad-item?item=TAPA-NEGRA-TZ").get_json()
    assert d["ok"] is True
    R = d["resumen"]
    assert R["n_sol"] == 1 and R["n_oc"] == 1
    assert R["total_pedido"] == 500 and R["total_recibido"] == 500 and R["pendiente"] == 0
    tipos = [e["tipo"] for e in d["eventos"]]
    assert "solicitado" in tipos and "ordenado" in tipos and "recibido" in tipos, "la historia completa"
    sol = next(e for e in d["eventos"] if e["tipo"] == "solicitado")
    assert sol["quien"] == "Alejandro", "quién lo pidió"
    rec = next(e for e in d["eventos"] if e["tipo"] == "recibido")
    assert rec["quien"] == "Luz", "quién recibió"
