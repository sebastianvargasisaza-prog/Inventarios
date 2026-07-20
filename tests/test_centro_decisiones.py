"""Centro de Mando - cola de decisiones (Sebastian 19-jul): agrega compras por autorizar,
discrepancias de precio/consumo, inventario critico, calidad pendiente y equipo en UNA cola
priorizada que el gerente ataca de una. Solo admins."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_decisiones_solo_admin(app, db_clean):
    # catalina NO es admin -> 403
    c = _login(app, "catalina")
    r = c.get("/api/centro/decisiones")
    assert r.status_code == 403, "solo admins ven el centro de mando"


def test_decisiones_estructura_y_prioridad(app, db_clean):
    # OC revisada sin autorizar -> debe aparecer en la cola (grupo compras)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, valor_total, fecha) "
                     "VALUES ('OC-DEC-1','Prov Dec','Revisada','MP', 500000, date('now','-5 hours','-4 day'))")
        conn.commit()
    finally:
        conn.close()
    c = _login(app, "sebastian")
    d = c.get("/api/centro/decisiones").get_json()
    assert "decisiones" in d and "resumen" in d
    assert isinstance(d["decisiones"], list)
    # la OC revisada de hace 4 dias debe salir como critica
    oc = [x for x in d["decisiones"] if x.get("grupo") == "compras" and "OC-DEC-1" in (x.get("detalle") or "")]
    assert oc, "la OC revisada sin autorizar debe aparecer en la cola"
    assert oc[0]["nivel"] == "critico", "4d sin autorizar = critico"
    # criticas primero
    niveles = [x["nivel"] for x in d["decisiones"]]
    if "critico" in niveles and "atencion" in niveles:
        assert niveles.index("critico") < niveles.index("atencion"), "criticas van primero"
    # resumen coherente
    assert d["resumen"]["critico"] == sum(1 for x in d["decisiones"] if x["nivel"] == "critico")


def test_decisiones_factura_proveedor_con_saldo(app, db_clean):
    # Fix cero-error (ultracode): la decision 'Facturas de proveedor con saldo' debe salir de
    # facturas_proveedor (AP), NO de facturas (AR cliente, sin columna numero_factura). Guard de regresion.
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO facturas_proveedor (numero_factura, proveedor, total, estado, fecha_emision) "
                     "VALUES ('FP-DEC-9', 'Prov Saldo', 700000, 'pendiente', date('now','-5 hours'))")
        conn.commit()
    finally:
        conn.close()
    c = _login(app, "sebastian")
    d = c.get("/api/centro/decisiones").get_json()
    fp = [x for x in d.get("decisiones", []) if "Facturas de proveedor" in (x.get("titulo") or "")]
    assert fp, "la factura de proveedor con saldo debe aparecer como decision"
    assert "700,000" in (fp[0].get("detalle") or "") or "1 factura" in (fp[0].get("detalle") or "")


def test_hub_alertas_sin_emdash(app, db_clean):
    # regla M86: cero em-dash en la UI/datos
    c = _login(app, "sebastian")
    d = c.get("/api/hub/alertas").get_json()
    for a in d.get("alertas", []):
        assert "—" not in (a.get("detalle") or ""), "sin em-dash en alertas (rastro IA)"
