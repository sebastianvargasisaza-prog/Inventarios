"""Consumos elevados · #2 tarjeta dashboard Catalina + #3 alerta a la campana (CEO)."""
import os, sqlite3
from .conftest import TEST_PASSWORD, csrf_headers

def _login(app, user="sebastian"):
    c=app.test_client()
    r=c.post("/login",data={"username":user,"password":TEST_PASSWORD},headers=csrf_headers(),follow_redirects=False)
    assert r.status_code==302; return c

def _seed_spike():
    conn=sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE 'OC-CEL-%'")
    for num,fecha,val in [("OC-CEL-1","2026-03-10",50000),("OC-CEL-2","2026-04-10",50000),
                          ("OC-CEL-3","2026-05-10",50000),("OC-CEL-4","2026-06-10",200000)]:
        conn.execute("INSERT INTO ordenes_compra (numero_oc,fecha,estado,proveedor,valor_total,categoria) "
                     "VALUES (?,?,?,?,?,?)",(num,fecha,"Pagada","P",val,"Papeleria/Oficina"))
    conn.commit(); conn.close()

def test_dashboard_card_render(app, db_clean):
    c=_login(app,"catalina")
    b=c.get("/compras").get_data(as_text=True)
    assert 'id="dash-consumos-elev"' in b and 'function cargarConsumosElevados' in b

def test_campana_alerta_consumo_elevado(app, db_clean):
    _seed_spike()
    c=_login(app,"sebastian")
    j=c.get("/api/notificaciones/centro").get_json()
    al=j.get("alertas") if isinstance(j,dict) else None
    assert al is not None, j
    hit=[a for a in al if a.get("tipo")=="consumo_elevado" or ("Papeleria" in str(a.get("titulo","")))]
    assert hit, "no salió la alerta de consumo elevado en la campana"
    assert "Papeleria" in hit[0]["titulo"] and "+" in hit[0]["titulo"]
