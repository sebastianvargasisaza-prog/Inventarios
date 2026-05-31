"""Necesidades reporta el estado del sync de ventas (para el banner de atraso).

Si el sync de Shopify lleva mucho sin correr, el plan queda ciego. El endpoint
expone sync_ventas.{ultimo, horas_desde} y el frontend pinta un banner si >36h.
"""
import os
import sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def test_necesidades_reporta_sync_atrasado(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM animus_shopify_orders")
    db.execute(
        """INSERT INTO animus_shopify_orders
           (shopify_id, nombre, total, moneda, estado, estado_pago,
            sku_items, unidades_total, creado_en, synced_at)
           VALUES ('SB-OLD','Cli',100,'COP','','paid','[]',0,
                   '2026-05-28','2020-01-01 00:00:00')""")
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert "sync_ventas" in d, d.keys()
    sv = d["sync_ventas"]
    assert sv["ultimo"] is not None
    # synced_at en 2020 → muchísimas horas de atraso
    assert sv["horas_desde"] is not None and sv["horas_desde"] > 1000, sv
