"""Serigrafía (Sebastián 19-jul): un envase base (sin nombre) va a marcar → sale del inventario (Salida
del BASE) → vuelve con OTRO código (el serigrafiado, con el nombre del producto) en CUARENTENA → Calidad
lo libera. La orden ancla base↔serigrafiado↔producto."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302
    return c


def _seed_envases():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    # base (genérico, sin nombre) con stock
    c.execute("INSERT OR REPLACE INTO maestro_mee (codigo, descripcion, categoria, estado, stock_actual) "
              "VALUES ('MEE-BASE1','Frasco 30ml transparente','Envase','Activo',1000)")
    c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, estado) "
              "VALUES ('MEE-BASE1','Entrada',1000,'und','SALDO','VIGENTE')")
    # serigrafiado (con el nombre del producto) · material_referencia = base
    c.execute("INSERT OR REPLACE INTO maestro_mee (codigo, descripcion, categoria, estado, material_referencia) "
              "VALUES ('MEE-SERIG1','Frasco 30ml Serum Vit C (serigrafiado)','Envase','Activo','MEE-BASE1')")
    conn.commit(); conn.close()


def _mee(cod, lote_ref):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT COUNT(*), COALESCE(SUM(cantidad),0), MAX(estado) FROM movimientos_mee "
                            "WHERE mee_codigo=? AND lote_ref=?", (cod, lote_ref)).fetchone()
    finally:
        conn.close()


def test_serigrafia_cambia_codigo_y_ancla(app, db_clean):
    _seed_envases()
    c = _login(app)
    # 1) enviar a marcar 300 del serigrafiado → sale el BASE del inventario
    r = c.post("/api/programacion/marcacion-orden/enviar", json={
        "serigrafiado_codigo": "MEE-SERIG1", "cantidad": 300, "metodo": "serigrafia",
        "proveedor": "SeriPrint", "producto": "Serum Vit C"}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    n_base, sal_base, _ = _mee("MEE-BASE1", "MARCACION")
    assert n_base == 1 and sal_base == 300, "sale una Salida del BASE (300) al enviar a marcar"
    # la orden quedó anclada base↔serigrafiado↔producto
    conn = sqlite3.connect(os.environ["DB_PATH"])
    o = conn.execute("SELECT base_codigo, serigrafiado_codigo, producto_nombre, estado, cantidad_enviada "
                     "FROM marcacion_ordenes ORDER BY id DESC LIMIT 1").fetchone()
    oid = conn.execute("SELECT id FROM marcacion_ordenes ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()
    assert o[0] == "MEE-BASE1" and o[1] == "MEE-SERIG1" and o[2] == "Serum Vit C" and o[3] == "enviado"
    # 2) recibir el retorno → entra el SERIGRAFIADO (código distinto) en CUARENTENA
    r2 = c.post("/api/programacion/marcacion-orden/%d/recibir" % oid, json={"cantidad_recibida": 300},
                headers=csrf_headers())
    assert r2.status_code in (200, 201), r2.data[:300]
    n_ser, ent_ser, est_ser = _mee("MEE-SERIG1", "MARCACION-RET")
    assert n_ser == 1 and ent_ser == 300, "vuelve como SERIGRAFIADO (otro código), 300 uds"
    assert str(est_ser).upper() == "CUARENTENA", "el serigrafiado que vuelve entra en cuarentena (pasa por Calidad)"
    # y la base y el serigrafiado son códigos DISTINTOS (cambió de código)
    assert "MEE-BASE1" != "MEE-SERIG1"
