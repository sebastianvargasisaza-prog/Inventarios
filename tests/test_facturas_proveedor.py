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


def test_pdf_va_a_tabla_1a1(app, db_clean):
    """mig 207: el PDF se guarda en facturas_proveedor_pdf, NO en la tabla padre."""
    import base64, json
    c = _login(app)
    data_url = "data:application/pdf;base64," + base64.b64encode(b"%PDF-1.4 test").decode()
    r = c.post("/api/compras/facturas-proveedor",
               data=json.dumps({"numero_factura": "FAC-PDF-1", "proveedor": "ProvPDF",
                                "subtotal": 100, "pdf_adjunto": data_url}), headers=_h())
    assert r.status_code == 200, r.data
    fid = r.get_json()["id"]
    # la tabla padre NO debe tener el blob; la hija SÍ
    with app.app_context():
        from database import get_db
        cu = get_db().cursor()
        padre = cu.execute("SELECT COALESCE(pdf_adjunto,'') FROM facturas_proveedor WHERE id=?", (fid,)).fetchone()[0]
        hija = cu.execute("SELECT pdf_adjunto FROM facturas_proveedor_pdf WHERE factura_id=?", (fid,)).fetchone()
    assert padre == "", "el blob NO debe vivir en la tabla transaccional"
    assert hija and hija[0] == data_url, "el blob debe vivir en la tabla 1:1"
    # el listado marca tiene_pdf sin traer el blob
    lst = c.get("/api/compras/facturas-proveedor").get_json()
    fila = next(x for x in lst["items"] if x["id"] == fid)
    assert fila["tiene_pdf"] is True
    assert "pdf_adjunto" not in fila, "el listado NO debe incluir el blob"
    # fp_pdf lo sirve desde la tabla 1:1
    pr = c.get(f"/api/compras/facturas-proveedor/{fid}/pdf")
    assert pr.status_code == 200, pr.data
    assert pr.data == b"%PDF-1.4 test"


def test_pago_factura_recalcula_estado_oc_y_warning(app, db_clean):
    """fp_pagar refleja el estado en la OC ligada; fp_crear avisa si la OC no existe."""
    import json
    c = _login(app)
    with app.app_context():
        from database import get_db
        cu = get_db().cursor()
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-FP-T'")
        cu.execute("DELETE FROM facturas_proveedor WHERE numero_factura IN ('FAC-OC-1','FAC-NOOC-1')")
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total) VALUES ('OC-FP-T','ProvOC','Autorizada',1000)")
        get_db().commit()
    # factura ligada a OC existente
    r = c.post("/api/compras/facturas-proveedor",
               data=json.dumps({"numero_factura":"FAC-OC-1","proveedor":"ProvOC","numero_oc":"OC-FP-T","total":1000}), headers=_h())
    assert r.status_code == 200, r.data
    assert r.get_json().get("warning") in (None, ""), "OC existe → sin warning"
    fid = r.get_json()["id"]
    # pago parcial → OC Parcial
    rp = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                data=json.dumps({"monto":400,"medio":"Transferencia"}), headers=_h())
    assert rp.get_json().get("oc_estado") == "Parcial", rp.data
    # pago final → OC Pagada
    rp2 = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                 data=json.dumps({"monto":600,"medio":"Transferencia"}), headers=_h())
    assert rp2.get_json().get("oc_estado") == "Pagada", rp2.data
    with app.app_context():
        from database import get_db
        est = get_db().execute("SELECT estado FROM ordenes_compra WHERE numero_oc='OC-FP-T'").fetchone()[0]
    assert est == "Pagada"
    # factura con OC inexistente → warning no bloqueante
    r2 = c.post("/api/compras/facturas-proveedor",
                data=json.dumps({"numero_factura":"FAC-NOOC-1","proveedor":"ProvX","numero_oc":"OC-NO-EXISTE","total":50}), headers=_h())
    assert r2.status_code == 200, r2.data
    assert r2.get_json().get("warning"), "OC inexistente → debe avisar"


def test_fp_pagar_bloquea_factura_ya_pagada_directo(app, db_clean):
    """Anti-doble-pago: si el nº ya se pagó por el camino directo (pagos_oc), fp_pagar rechaza."""
    import json
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM facturas_proveedor WHERE numero_factura='FAC-DIR-X'")
        cu.execute("DELETE FROM pagos_oc WHERE numero_factura_proveedor='FAC-DIR-X'")
        # pago previo por el camino directo (pagar_oc) con ese nº de factura
        cu.execute("INSERT INTO pagos_oc (numero_oc, monto, medio, registrado_por, numero_factura_proveedor) VALUES ('OC-X',100,'Transferencia','t','FAC-DIR-X')")
        conn.commit()
    # crear la misma factura en el libro y tratar de pagarla
    r = c.post("/api/compras/facturas-proveedor",
               data=json.dumps({"numero_factura":"FAC-DIR-X","proveedor":"ProvDir","total":100}), headers=_h())
    fid = r.get_json()["id"]
    rp = c.post(f"/api/compras/facturas-proveedor/{fid}/pagar",
                data=json.dumps({"monto":100,"medio":"Transferencia"}), headers=_h())
    assert rp.status_code == 409, rp.data
    assert rp.get_json().get("codigo") == "YA_PAGADA_DIRECTO"


def test_conteo_cerrar_requiere_auth(app, db_clean):
    """conteo_cerrar ya NO es accesible sin autenticación (P1 seguridad)."""
    anon = app.test_client()  # sin login
    r = anon.post("/api/conteo/999999/cerrar")
    assert r.status_code in (401, 403), f"debe rechazar sin auth, got {r.status_code}"
