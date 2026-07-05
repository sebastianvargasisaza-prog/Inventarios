"""Sebastián 4-jul · PERF · cache COMPARTIDA en BD de los mapas de ventas (mig 337).

El parseo de 90d de órdenes es el hotspot de /necesidades y el cache de módulo es POR-WORKER (en PG
multi-worker cada worker frío re-parsea). La tabla plan_vmaps_cache lo comparte: se computa 1 vez y todos
LEEN. Test con dientes: tras poblar la cache, se BORRAN las órdenes → si la 2ª llamada re-parseara daría
vacío; como lee el cache compartido, devuelve la misma data.
"""
import json
import os
import sqlite3
from datetime import date, timedelta


def test_vmaps_cache_compartida_bd(app, db_clean, monkeypatch):
    # bajo pytest el cache está desactivado · lo habilitamos para ejercitar la capa compartida
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from blueprints.plan import _ventas_maps_shopify, _VMAPS_CACHE
    _VMAPS_CACHE.clear()

    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM plan_vmaps_cache")
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'VMAP-%'")
    today = date.today()
    for i in range(20):
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"VMAP-{i}", f"c{i}", 1000.0, "COP", "", "paid",
             json.dumps([{"sku": "VMAPSKU", "qty": 3}]), 3,
             (today - timedelta(days=i)).isoformat() + "T00:00:00"))
    db.commit()

    vd_iso = (today - timedelta(days=60)).strftime("%Y-%m-%d") + "T00:00:00"
    cut30 = (today - timedelta(days=30)).strftime("%Y-%m-%d") + "T00:00:00"
    cut90 = (today - timedelta(days=90)).strftime("%Y-%m-%d") + "T00:00:00"
    vd_base = min(vd_iso, cut90)
    c = db.cursor()

    r1 = _ventas_maps_shopify(c, vd_base, vd_iso, cut30, cut90, "", [], set())
    assert r1[2].get("VMAPSKU", 0) > 0, ("control: VMAPSKU debe tener ventas en v90", r1[2])
    # la cache compartida en BD se pobló
    n = c.execute("SELECT COUNT(*) FROM plan_vmaps_cache").fetchone()[0]
    assert n >= 1, "el cache compartido en BD debe poblarse tras el primer cómputo"

    # vaciar el cache de MÓDULO + BORRAR las órdenes → la 2ª llamada solo puede dar data si LEE el cache BD
    _VMAPS_CACHE.clear()
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'VMAP-%'")
    db.commit()

    r2 = _ventas_maps_shopify(c, vd_base, vd_iso, cut30, cut90, "", [], set())
    assert r2 == r1, "la 2ª llamada debe leer el cache compartido (misma data), no re-parsear"
    assert r2[2].get("VMAPSKU", 0) == r1[2].get("VMAPSKU", 0) > 0, (
        "sin cache daría vacío (órdenes borradas) · con cache da lo mismo que r1", r2[2])
    db.close()
