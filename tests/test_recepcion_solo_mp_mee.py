"""Recepción divide por naturaleza (18-jul · Sebastián): el monitoreo/cola de recepción
muestra SOLO lo que entra a bodega (MP/MEE). Consumibles/gastos (EPP, papelería, servicios)
NO aparecen (recibir_oc los rechaza · se trazan en Consumos)."""
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


def test_recepcion_solo_mp_mee(app, db_clean):
    _oc("OC-REC-MP", "MP")
    _oc("OC-REC-MEE", "MEE")
    _oc("OC-REC-EPP", "EPP")          # consumo → NO debe aparecer
    _oc("OC-REC-PAP", "Papeleria/Oficina")  # consumo → NO
    _oc("OC-REC-SVC", "SVC")          # servicio → NO
    c = _login(app)
    d = c.get("/api/recepcion/seguimiento").get_json()
    nums = {x.get("numero_oc") for x in (d if isinstance(d, list) else d.get("items", []))}
    assert "OC-REC-MP" in nums and "OC-REC-MEE" in nums, "MP/MEE deben aparecer en recepción"
    for n in ("OC-REC-EPP", "OC-REC-PAP", "OC-REC-SVC"):
        assert n not in nums, f"{n} (consumo/servicio) NO debe aparecer en recepción"
