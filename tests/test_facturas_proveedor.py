"""Libro de facturas de proveedor (mig 206 + endpoints) · Sebastián 31-may."""
import json


def _login(app, user="sebastian"):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def test_mig206_tabla(app, db_clean):
    with app.app_context():
        from database import get_db
        c = get_db()
        cols = [r[1] for r in c.execute("PRAGMA table_info(facturas_proveedor)").fetchall()]
        for must in ("numero_factura", "proveedor", "numero_oc", "fecha_vencimiento",
                     "subtotal", "iva", "retefuente", "retica", "total", "estado", "pdf_adjunto"):
            assert must in cols, f"falta {must}: {cols}"
        pcols = [r[1] for r in c.execute("PRAGMA table_info(pagos_oc)").fetchall()]
        assert "factura_proveedor_id" in pcols


def test_crear_listar_pagar_anular(app, db_clean):
    c = _login(app)
    # crear (total auto = subtotal+iva-retefuente-retica = 1000+190-25-10 = 1155)
    body = {"numero_factura": "FAC-T-1", "proveedor": "ProvTest", "numero_oc": "",
            "fecha_vencimiento": "2020-01-01",  # vencida
            "subtotal": 1000, "iva": 190, "retefuente": 25, "retica": 10}
    r = c.post("/api/compras/facturas-proveedor", data=json.dumps(body), headers=_h())
    assert r.status_code == 200, r.data
    fid = r.get_json()["id"]
    assert abs(r.get_json()["total"] - 1155) < 0.01

    # duplicado
    r2 = c.post("/api/compras/facturas-proveedor", data=json.dumps(body), headers=_h())
    assert r2.status_code == 409, r2.data

    # listar · saldo=1155, vencida
    r3 = c.get("/api/compras/facturas-proveedor")
    d = r3.get_json()
    fila = next(x for x in d["items"] if x["id"] == fid)
    assert fila["saldo"] == 1155
    assert fila["vencida"] is True
    assert fila["estado_efectivo"] == "vencida"
    assert d["total_vencido"] >= 1155

    # pago parcial
    rp = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                data=json.dumps({"monto": 155, "medio": "Transferencia"}), headers=_h())
    assert rp.status_code == 200, rp.data
    assert rp.get_json()["estado"] == "parcial"

    # sobre-pago rechazado
    rbad = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                  data=json.dumps({"monto": 5000, "medio": "Nequi"}), headers=_h())
    assert rbad.status_code == 400

    # pago final → pagada
    rp2 = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                 data=json.dumps({"monto": 1000, "medio": "Transferencia"}), headers=_h())
    assert rp2.get_json()["estado"] == "pagada"

    # detalle: 2 pagos, saldo 0
    rd = c.get(f"/api/compras/facturas-proveedor/{fid}")
    fac = rd.get_json()["factura"]
    assert len(fac["pagos"]) == 2
    assert fac["saldo"] == 0

    # anular
    ra = c.patch(f"/api/compras/facturas-proveedor/{fid}",
                 data=json.dumps({"anular": True, "motivo": "test"}), headers=_h())
    assert ra.get_json()["estado"] == "anulada"
