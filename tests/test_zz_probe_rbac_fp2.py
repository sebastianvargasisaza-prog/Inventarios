import json

TEST_PASSWORD = "TestPass123"


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    return {"Content-Type": "application/json", "Origin": "http://localhost"}


def test_probe_oc_flip_pagada(app, db_clean):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-ZZPROBE-9'")
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total) "
                   "VALUES (?,?,?,?)", ("OC-ZZPROBE-9", "PROV ZZ PROBE", "Autorizada", 1000000))
        conn.commit()

    c = _login(app, "mayerlin")
    r = c.post("/api/compras/facturas-proveedor",
               data=json.dumps({"numero_factura": "ZZPROBE-OC-9", "proveedor": "PROV ZZ PROBE",
                                "numero_oc": "OC-ZZPROBE-9", "total": 1000000}),
               headers=_h())
    print("CREAR ->", r.status_code, r.get_data(as_text=True)[:200])
    fid = r.get_json()["id"]
    rp = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                data=json.dumps({"monto": 1000000, "medio": "Transferencia"}), headers=_h())
    print("PAGAR ->", rp.status_code, rp.get_data(as_text=True)[:250])

    with app.app_context():
        cu = get_db().cursor()
        est = cu.execute("SELECT estado FROM ordenes_compra WHERE numero_oc='OC-ZZPROBE-9'").fetchone()
        print("OC ESTADO FINAL ->", est[0])
        eg = cu.execute("SELECT COUNT(*) FROM flujo_egresos WHERE numero_oc='OC-ZZPROBE-9'").fetchone()
        print("flujo_egresos filas ->", eg[0])
