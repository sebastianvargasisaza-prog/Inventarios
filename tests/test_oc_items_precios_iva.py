"""Audit compras 13-jun · BUG dinero (M12(f)): el endpoint items-precios (el que usa
Catalina para guardar precios) recalculaba valor_total como SUMA de subtotales SIN IVA,
mientras editar_oc/agregar/modificar sí aplican ×1.19. Tras pasar por items-precios el
valor_total perdía el 16% → pagar_oc/espejo financiero pagaban de menos.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone(); return r[0] if r else None
    finally:
        conn.close()


def _seed_oc(oc, con_iva):
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc,fecha,estado,proveedor,categoria,con_iva,valor_total) "
          "VALUES (?, date('now','-5 hours'),'Borrador','Test Prov','Materia Prima',?,0)", (oc, con_iva))
    _exec("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc,))
    _exec("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) "
          "VALUES (?,?,?,?,?,?)", (oc, 'MP-IVA', 'Test MP-IVA', 1000, 0, 0))


def test_items_precios_respeta_iva(app, db_clean):
    """OC con con_iva=1: tras items-precios, valor_total debe incluir el IVA (×1.19)."""
    _seed_oc('OC-IVA-1', con_iva=1)
    c = _login(app)
    r = c.patch('/api/ordenes-compra/OC-IVA-1/items-precios',
                json={'items': [{'codigo_mp': 'MP-IVA', 'precio_unitario': 10, 'cantidad_g': 1000}]},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    vt = _q1("SELECT valor_total FROM ordenes_compra WHERE numero_oc='OC-IVA-1'")
    vsi = _q1("SELECT valor_sin_iva FROM ordenes_compra WHERE numero_oc='OC-IVA-1'")
    # subtotal = 1000*10 = 10000 ; con IVA = 11900
    assert abs(float(vt) - 11900) < 0.5, f"valor_total debe incluir IVA (11900) · fue {vt}"
    assert abs(float(vsi or 0) - 10000) < 0.5, f"valor_sin_iva debe ser 10000 · fue {vsi}"


def test_items_precios_sin_iva_no_infla(app, db_clean):
    """OC con con_iva=0: valor_total = subtotal puro (no agrega IVA)."""
    _seed_oc('OC-IVA-0', con_iva=0)
    c = _login(app)
    r = c.patch('/api/ordenes-compra/OC-IVA-0/items-precios',
                json={'items': [{'codigo_mp': 'MP-IVA', 'precio_unitario': 10, 'cantidad_g': 1000}]},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    vt = _q1("SELECT valor_total FROM ordenes_compra WHERE numero_oc='OC-IVA-0'")
    assert abs(float(vt) - 10000) < 0.5, f"sin IVA valor_total debe ser 10000 · fue {vt}"
