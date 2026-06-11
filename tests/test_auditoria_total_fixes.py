"""Regresión de la auditoría total (ultracode · 10-jun-2026).

Cubre los fixes testeables en SQLite:
  · /api/financiero/ar-aging ya no da 500 (columnas fantasma numero_pedido/cliente).
  · Datos bancarios de proveedores enmascarados para no-admin (Habeas Data Ley 1581).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_ar_aging_no_da_500(app, db_clean):
    """Antes consultaba numero_pedido/cliente (no existen en `pedidos`) → 500 siempre."""
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/ar-aging")
    assert r.status_code == 200, r.data
    assert "buckets" in r.get_json()


def test_datos_bancarios_proveedor_enmascarados_no_admin(app, db_clean):
    """num_cuenta/banco/nit visibles solo para admin+contadora · enmascarados al resto."""
    _exec("INSERT INTO proveedores (nombre, num_cuenta, tipo_cuenta, banco, nit, activo) "
          "VALUES ('PROV-ZZTEST', '1234567890', 'Ahorros', 'Bancolombia', '900123', 1)")

    # Operario de planta (no admin/contadora) → enmascarado
    cp = _login(app, "luis")
    rp = cp.get("/api/proveedores-compras")
    assert rp.status_code == 200, rp.data
    prov_p = next((p for p in rp.get_json().get("proveedores", []) if p.get("nombre") == "PROV-ZZTEST"), None)
    assert prov_p is not None, "el proveedor debe listarse"
    assert prov_p.get("num_cuenta") == "***", prov_p
    assert prov_p.get("banco") == "***", prov_p

    # Admin → ve los datos reales
    ca = _login(app, "sebastian")
    ra = ca.get("/api/proveedores-compras")
    prov_a = next((p for p in ra.get_json().get("proveedores", []) if p.get("nombre") == "PROV-ZZTEST"), None)
    assert prov_a and prov_a.get("num_cuenta") == "1234567890", prov_a
