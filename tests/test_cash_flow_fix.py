"""Dashboard Compras · fixes 23-jun: Cash Flow por fecha de pago esperada + Real pagado.

- Bug 1: la proyección 30/60/90 agrupaba por fecha de CREACIÓN → todos los buckets idénticos.
  Ahora agrupa por fecha_entrega_est → una OC con entrega en 60d NO entra en el bucket de 30d.
- Bug 2 (M12 columna fantasma): pagado_30d leía date(fecha) pero pagos_oc tiene fecha_pago →
  siempre $0. Ahora lee fecha_pago.
"""
import os
import sqlite3
from datetime import datetime, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_cash_flow_bucketea_por_entrega(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE 'OC-CF-%'")
    hoy = datetime.now().date()
    entrega_45 = (hoy + timedelta(days=45)).isoformat()
    # OC con entrega en 45 días → debe salir en 60/90 pero NO en 30
    conn.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, fecha_entrega_est) "
                 "VALUES ('OC-CF-1', ?, 'Autorizada', 'P', 500000, ?)", (hoy.isoformat(), entrega_45))
    conn.commit(); conn.close()
    c = _login(app)
    j = c.get("/api/compras/cash-flow").get_json()
    por = {p["dias"]: p["ocs_por_pagar"]["monto"] for p in j["proyecciones"]}
    assert por[30] == 0, "OC con entrega a 45d NO debe estar en el bucket de 30d"
    assert por[60] == 500000 and por[90] == 500000, "sí debe estar en 60d y 90d"


def test_real_pagado_lee_fecha_pago(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM pagos_oc WHERE numero_oc='OC-PAGO-TEST'")
    hoy = datetime.now().date().isoformat()
    conn.execute("INSERT INTO pagos_oc (numero_oc, monto, medio, fecha_pago, registrado_por) "
                 "VALUES ('OC-PAGO-TEST', 333000, 'transferencia', ?, 'catalina')", (hoy,))
    conn.commit(); conn.close()
    c = _login(app)
    j = c.get("/api/compras/cash-flow").get_json()
    pag = j.get("pagado_30d", {})
    assert pag.get("monto", 0) >= 333000, f"real pagado debe leer fecha_pago, got {pag}"
    assert pag.get("count", 0) >= 1
