"""Recepción por naturaleza (18-jul, actualizado 19-jul · Sebastián): el monitoreo de recepción
muestra MP/MEE (bodega, con cuarentena) Y consumibles/EPP/papelería (recepción ADMINISTRATIVA, sin
cuarentena · comprobar que llegó lo pedido). Solo el PAGO DIRECTO (servicios/CC/influencer) NO aparece
(pago puro sin material físico)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _oc(numero, categoria):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, valor_total, fecha) "
                     "VALUES (?, 'Prov Recep', 'Autorizada', ?, 100000, date('now','-5 hours'))", (numero, categoria))
        conn.commit()
    finally:
        conn.close()


def test_recepcion_mp_mee_y_consumibles_no_servicios(app, db_clean):
    _oc("OC-REC-MP", "MP")
    _oc("OC-REC-MEE", "MEE")
    _oc("OC-REC-EPP", "EPP")          # consumo → SÍ aparece (recepción administrativa)
    _oc("OC-REC-PAP", "Papeleria/Oficina")  # consumo → SÍ
    _oc("OC-REC-SVC", "SVC")          # pago directo → NO
    _oc("OC-REC-CC", "Cuenta de Cobro")  # pago directo → NO
    c = _login(app)
    d = c.get("/api/recepcion/seguimiento").get_json()
    nums = {x.get("numero_oc") for x in (d if isinstance(d, list) else d.get("items", []))}
    assert "OC-REC-MP" in nums and "OC-REC-MEE" in nums, "MP/MEE deben aparecer"
    assert "OC-REC-EPP" in nums and "OC-REC-PAP" in nums, "consumibles ahora SÍ aparecen (recepción administrativa)"
    for n in ("OC-REC-SVC", "OC-REC-CC"):
        assert n not in nums, f"{n} (pago directo) NO debe aparecer en recepción"
