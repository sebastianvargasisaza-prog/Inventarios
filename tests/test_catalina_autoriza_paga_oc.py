"""Sebastián 13-jun: Catalina (asistente de compras) debe poder AUTORIZAR y PAGAR
OCs aunque comparta el perfil contable. El gate _require_authorize_oc bloqueaba a
todas las CONTADORA_USERS (incl. Catalina) por segregación de funciones, lo que
contradecía LIMITES_APROBACION_OC (que la documenta autorizando hasta 5M). Fix:
OC_AUTORIZA_USERS la exceptúa.
Sebastián 18-jun: gerencia relaja la SoD · Catalina, Mayra y admins TODOS pueden autorizar
Y pagar (OC_AUTORIZA_USERS={'catalina','mayra'}). El control compensatorio es el audit_log
+ el límite de monto por usuario (5M Catalina/Mayra · admins sin tope).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _seed_oc(oc):
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc,fecha,estado,proveedor,categoria,con_iva,valor_total) "
          "VALUES (?, date('now','-5 hours'),'Borrador','Test Prov','Materia Prima',0,100000)", (oc,))
    _exec("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc,))
    _exec("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) "
          "VALUES (?,?,?,?,?,?)", (oc, 'MP-CAT', 'Test', 1000, 100, 100000))


def test_catalina_puede_autorizar(app, db_clean):
    _seed_oc('OC-CAT-1')
    c = _login(app, 'catalina')
    r = c.patch('/api/ordenes-compra/OC-CAT-1/autorizar', json={}, headers=csrf_headers())
    # No debe ser bloqueo por segregación de funciones
    assert r.status_code != 403 or (r.get_json() or {}).get('codigo') != 'SEGREGATION_OF_DUTIES', \
        f"Catalina NO debe ser bloqueada por SoD · {r.status_code} {r.data[:200]}"
    assert r.status_code in (200, 201), f"Catalina debe poder autorizar (<=5M) · {r.status_code} {r.data[:200]}"


def test_mayra_puede_autorizar(app, db_clean):
    """Sebastián 18-jun · Mayra AHORA está en OC_AUTORIZA_USERS → puede autorizar (SoD relajada)."""
    _seed_oc('OC-CAT-2')
    c = _login(app, 'mayra')
    r = c.patch('/api/ordenes-compra/OC-CAT-2/autorizar', json={}, headers=csrf_headers())
    assert r.status_code != 403 or (r.get_json() or {}).get('codigo') != 'SEGREGATION_OF_DUTIES', \
        f"Mayra NO debe ser bloqueada por SoD (política 18-jun) · {r.status_code} {r.data[:200]}"
    assert r.status_code in (200, 201), f"Mayra debe poder autorizar (<=5M) · {r.status_code} {r.data[:200]}"


def test_mayra_puede_pagar(app, db_clean):
    """Mayra puede registrar el pago de una OC (mismo gate · política 18-jun)."""
    _seed_oc('OC-CAT-4')
    _exec("UPDATE ordenes_compra SET estado='Autorizada' WHERE numero_oc='OC-CAT-4'")
    c = _login(app, 'mayra')
    r = c.post('/api/ordenes-compra/OC-CAT-4/pagar',
               json={'monto': 100000, 'medio': 'Transferencia'}, headers=csrf_headers())
    assert r.status_code != 403 or (r.get_json() or {}).get('codigo') != 'SEGREGATION_OF_DUTIES', \
        f"Mayra NO debe ser bloqueada por SoD al pagar (18-jun) · {r.status_code} {r.data[:200]}"


def test_catalina_puede_pagar(app, db_clean):
    """Catalina puede registrar el pago de una OC (mismo gate _require_authorize_oc)."""
    _seed_oc('OC-CAT-3')
    _exec("UPDATE ordenes_compra SET estado='Autorizada' WHERE numero_oc='OC-CAT-3'")
    c = _login(app, 'catalina')
    r = c.post('/api/ordenes-compra/OC-CAT-3/pagar',
               json={'monto': 100000, 'medio': 'Transferencia'}, headers=csrf_headers())
    assert r.status_code != 403 or (r.get_json() or {}).get('codigo') != 'SEGREGATION_OF_DUTIES', \
        f"Catalina NO debe ser bloqueada por SoD al pagar · {r.status_code} {r.data[:200]}"
