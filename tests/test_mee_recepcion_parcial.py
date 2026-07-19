"""Envases (MEE) por partes (Sebastián 19-jul): la recepción soporta entregas PARCIALES ancladas a la
OC → cada parte crea una Entrada en movimientos_mee (cuarentena) ligada a la OC, la línea acumula
lo recibido y la OC queda 'Parcial' hasta completar. Empaque (MEMP) usa el mismo camino."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302
    return c


def _seed_oc_mee(numero_oc, cod, nombre, unidades):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO maestro_mee (codigo, descripcion, categoria, estado) VALUES (?,?, 'Envase','Activo')",
              (cod, nombre))
    c.execute("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria, creado_por) "
              "VALUES (?, date('now'), 'Autorizada', 'Prov MEE', 0, 'MEE', 'test')", (numero_oc,))
    c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
              "VALUES (?, ?, ?, ?, 0)", (numero_oc, cod, nombre, unidades))
    conn.commit(); conn.close()


def _oc_estado(numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)).fetchone()[0]
    finally:
        conn.close()


def _oci_recibido(numero_oc, cod):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT COALESCE(cantidad_recibida_g,0) FROM ordenes_compra_items WHERE numero_oc=? AND codigo_mp=?",
                            (numero_oc, cod)).fetchone()[0]
    finally:
        conn.close()


def _mee_entradas(cod, numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos_mee "
                            "WHERE mee_codigo=? AND tipo='Entrada' AND lote_ref=? AND UPPER(COALESCE(estado,''))='CUARENTENA'",
                            (cod, numero_oc)).fetchone()
    finally:
        conn.close()


def test_mee_recepcion_por_partes_ancladas(app, db_clean):
    _seed_oc_mee("OC-MEE-P1", "MEE-PARC", "Frasco 30ml", 1000)
    c = _login(app)
    # 1ra parte: 600 de 1000
    r1 = c.post("/api/ordenes-compra/OC-MEE-P1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tok-1",
        "items_recepcion": [{"codigo_mp": "MEE-PARC", "cantidad_recibida": 600, "estado": "OK"}]},
        headers=csrf_headers())
    assert r1.status_code in (200, 201), r1.data[:300]
    assert _oci_recibido("OC-MEE-P1", "MEE-PARC") == 600, "la línea debe acumular 600"
    assert _oc_estado("OC-MEE-P1") == "Parcial", "con faltante la OC queda Parcial"
    n, tot = _mee_entradas("MEE-PARC", "OC-MEE-P1")
    assert n == 1 and tot == 600, "1 Entrada MEE en cuarentena anclada a la OC"
    # 2da parte: los 400 restantes
    r2 = c.post("/api/ordenes-compra/OC-MEE-P1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tok-2",
        "items_recepcion": [{"codigo_mp": "MEE-PARC", "cantidad_recibida": 400, "estado": "OK"}]},
        headers=csrf_headers())
    assert r2.status_code in (200, 201), r2.data[:300]
    assert _oci_recibido("OC-MEE-P1", "MEE-PARC") == 1000, "acumula el total"
    assert _oc_estado("OC-MEE-P1") == "Recibida", "completa → Recibida"
    n2, tot2 = _mee_entradas("MEE-PARC", "OC-MEE-P1")
    assert n2 == 2 and tot2 == 1000, "2 Entradas ancladas, total 1000, ambas en cuarentena"
