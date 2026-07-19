"""Consumibles/EPP/papelería (Sebastián 19-jul): se reciben en /recepción de forma ADMINISTRATIVA
(comprobar que llegó lo pedido: cantidad, quién recibió) SIN kardex regulado ni cuarentena. Servicios
(pago directo) siguen SIN recepción."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302
    return c


def _seed_oc(numero_oc, categoria, cod, nombre, cant):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria, creado_por) "
              "VALUES (?, date('now'), 'Autorizada', 'Prov X', 0, ?, 'test')", (numero_oc, categoria))
    c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
              "VALUES (?, ?, ?, ?, 0)", (numero_oc, cod, nombre, cant))
    conn.commit(); conn.close()


def _oc_estado(numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)).fetchone()[0]
    finally:
        conn.close()


def test_consumible_recepcion_administrativa_sin_kardex(app, db_clean):
    _seed_oc("OC-CONS-1", "Papeleria/Oficina", "", "Resma de hojas carta", 40)
    c = _login(app)
    # aparece en el seguimiento de recepción (ya no se excluye)
    seg = c.get("/api/recepcion/seguimiento").get_json()
    ocs = [x.get("numero_oc") for x in (seg if isinstance(seg, list) else seg.get("ocs", seg.get("items", [])))]
    assert "OC-CONS-1" in ocs, "el consumible debe aparecer en recepción"
    # el detalle marca es_consumo
    det = c.get("/api/recepcion/detalle/OC-CONS-1").get_json()
    assert det.get("es_consumo") is True
    # recibir administrativamente 40 de 40
    r = c.post("/api/ordenes-compra/OC-CONS-1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tokcons-1",
        "items_recepcion": [{"codigo_mp": "", "cantidad_recibida": 40, "estado": "OK"}]},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    assert _oc_estado("OC-CONS-1") == "Recibida", "completa → Recibida"
    # NO se creó ningún movimiento en el kardex MP ni MEE (no es bodega regulada)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        n_mp = conn.execute("SELECT COUNT(*) FROM movimientos WHERE numero_oc='OC-CONS-1'").fetchone()[0]
        n_rec = conn.execute("SELECT COALESCE(cantidad_recibida_g,0) FROM ordenes_compra_items WHERE numero_oc='OC-CONS-1'").fetchone()[0]
    finally:
        conn.close()
    assert n_mp == 0, "consumible NO entra al kardex MP (recepción administrativa)"
    assert n_rec == 40, "pero SÍ queda el rastro de recibido en la línea de la OC"


def test_servicio_pago_directo_sigue_sin_recepcion(app, db_clean):
    _seed_oc("OC-SVC-1", "Servicio", "", "Mantenimiento aire", 1)
    c = _login(app)
    r = c.post("/api/ordenes-compra/OC-SVC-1/recibir", json={
        "receptor_nombre": "Luz", "items_recepcion": [{"codigo_mp": "", "cantidad_recibida": 1}]},
        headers=csrf_headers())
    assert r.status_code == 409 and r.get_json().get("codigo") == "OC_PAGO_DIRECTO_SIN_RECEPCION"
