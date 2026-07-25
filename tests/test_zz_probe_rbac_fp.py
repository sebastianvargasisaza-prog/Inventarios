import json
import pytest
TEST_PASSWORD = "TestPass123"


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def _h():
    return {"Content-Type": "application/json", "Origin": "http://localhost"}


def test_probe_fp_pagar_sin_rol(app, db_clean):
    c = _login(app, "mayerlin")
    # camino canonico: pagar OC
    r_canon = c.patch("/api/ordenes-compra/OC-NOEXISTE/pagar",
                      data=json.dumps({"monto": 1000}), headers=_h())
    print("CANONICO pagar_oc ->", r_canon.status_code, r_canon.get_data(as_text=True)[:200])

    # crear factura
    r = c.post("/api/compras/facturas-proveedor",
               data=json.dumps({"numero_factura": "ZZPROBE-RBAC-1",
                                "proveedor": "PROV ZZ PROBE", "total": 1000000}),
               headers=_h())
    print("CREAR factura ->", r.status_code, r.get_data(as_text=True)[:250])
    if r.status_code != 200:
        pytest.skip("no creo factura")
    fid = r.get_json().get("id")

    rp = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                data=json.dumps({"monto": 1000000, "medio": "Transferencia"}),
                headers=_h())
    print("PAGAR factura ->", rp.status_code, rp.get_data(as_text=True)[:250])

    from database import get_db
    with app.app_context():
        cu = get_db().cursor()
        row = cu.execute("SELECT id, monto, registrado_por, factura_proveedor_id FROM pagos_oc "
                         "WHERE factura_proveedor_id=?", (fid,)).fetchall()
        print("FILAS pagos_oc ->", row)
        est = cu.execute("SELECT estado FROM facturas_proveedor WHERE id=?", (fid,)).fetchone()
        print("ESTADO factura ->", est)
