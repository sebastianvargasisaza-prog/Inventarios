"""Sebastián 1-jul: Catalina debe poder ELIMINAR una OC que autorizó por error,
siempre que la OC todavía NO tenga pago ni recepción. Si ya movió plata o entró
stock, se bloquea (primero se anula el pago/recepción). Borrador/Rechazada siguen
borrándose sin más; Recibida/Pagada nunca."""
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


def _one(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def _seed_oc(oc, estado='Autorizada', recibido_g=0):
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc,fecha,estado,proveedor,categoria,con_iva,valor_total) "
          "VALUES (?, date('now','-5 hours'),?,'Test Prov','Materia Prima',0,100000)", (oc, estado))
    _exec("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc,))
    _exec("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,cantidad_recibida_g,precio_unitario,subtotal) "
          "VALUES (?,?,?,?,?,?,?)", (oc, 'MP-CAT', 'Test', 1000, recibido_g, 100, 100000))


def test_catalina_elimina_oc_autorizada_sin_pago(app, db_clean):
    _seed_oc('OC-DEL-AUT', estado='Autorizada', recibido_g=0)
    c = _login(app, 'catalina')
    r = c.delete('/api/ordenes-compra/OC-DEL-AUT', headers=csrf_headers())
    assert r.status_code == 200, f"debe poder borrar Autorizada sin pago/recepción · {r.status_code} {r.data[:200]}"
    assert _one("SELECT 1 FROM ordenes_compra WHERE numero_oc='OC-DEL-AUT'") is None, "la OC debe quedar eliminada"


def test_no_elimina_oc_autorizada_con_recepcion(app, db_clean):
    _seed_oc('OC-DEL-REC', estado='Autorizada', recibido_g=500)  # ya entró stock
    c = _login(app, 'catalina')
    r = c.delete('/api/ordenes-compra/OC-DEL-REC', headers=csrf_headers())
    assert r.status_code == 400, f"NO debe borrar Autorizada con recepción · {r.status_code} {r.data[:200]}"
    assert (r.get_json() or {}).get('codigo') == 'OC_CON_PAGO_O_RECEPCION'
    assert _one("SELECT 1 FROM ordenes_compra WHERE numero_oc='OC-DEL-REC'") is not None, "la OC NO debe borrarse"


def test_no_elimina_oc_recibida(app, db_clean):
    _seed_oc('OC-DEL-RCB', estado='Recibida', recibido_g=1000)
    c = _login(app, 'catalina')
    r = c.delete('/api/ordenes-compra/OC-DEL-RCB', headers=csrf_headers())
    assert r.status_code == 400, f"Recibida nunca se borra · {r.status_code} {r.data[:200]}"
    assert _one("SELECT 1 FROM ordenes_compra WHERE numero_oc='OC-DEL-RCB'") is not None
