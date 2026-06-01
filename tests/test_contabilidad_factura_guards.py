"""Guards de cont_facturas_generar (audit dinero 1-jun): items/descuento + idempotencia."""
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


def test_item_negativo_rechazado(app, db_clean):
    c = _login(app)
    r = c.post("/api/contabilidad/facturas/generar",
               data=json.dumps({"empresa":"ANIMUS","items":[{"cantidad":-2,"precio_unitario":100}]}), headers=_h())
    assert r.status_code == 400, r.data
    assert r.get_json().get("codigo") == "ITEM_INVALIDO"


def test_descuento_negativo_o_mayor_subtotal_rechazado(app, db_clean):
    c = _login(app)
    base = {"empresa":"ANIMUS","items":[{"cantidad":1,"precio_unitario":100,"subtotal":100}]}
    r1 = c.post("/api/contabilidad/facturas/generar", data=json.dumps({**base,"descuento":-50}), headers=_h())
    assert r1.status_code == 400 and r1.get_json().get("codigo")=="DESCUENTO_INVALIDO", r1.data
    r2 = c.post("/api/contabilidad/facturas/generar", data=json.dumps({**base,"descuento":500}), headers=_h())
    assert r2.status_code == 400 and r2.get_json().get("codigo")=="DESCUENTO_INVALIDO", r2.data


def test_factura_valida_pasa(app, db_clean):
    c = _login(app)
    r = c.post("/api/contabilidad/facturas/generar",
               data=json.dumps({"empresa":"ANIMUS","items":[{"cantidad":2,"precio_unitario":100,"subtotal":200}],"iva_pct":19}), headers=_h())
    assert r.status_code == 200, r.data
