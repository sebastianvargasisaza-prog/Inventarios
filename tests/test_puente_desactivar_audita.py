"""Desactivar un puente de MP cambia de QUÉ código sale el material · tiene que auditarse (2-ago).

Un puente (`mp_formula_bridge`) decide a qué código de bodega se resuelve un ingrediente, así que
quitarlo cambia el DESCUENTO DEL INVENTARIO. Hasta hoy se hacía con un UPDATE sin rastro.

Lo vi al desactivar el puente 184 (`MP00181 → MP00176`), que a su vez alguien había creado en
junio sin que quedara constancia -- por eso nadie sabía que existía y la centella se descontaba
del frasco equivocado.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

A, B = 'MPQAPUENTE1', 'MPQAPUENTE2'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sembrar():
    db = _db()
    try:
        db.execute("DELETE FROM mp_formula_bridge WHERE formula_material_id=?", (A,))
        db.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
                   "VALUES (?,?,1)", (A, B))
        db.commit()
        return db.execute("SELECT id FROM mp_formula_bridge WHERE formula_material_id=?",
                          (A,)).fetchone()[0]
    finally:
        db.close()


def _cli(app):
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    return c


def _h(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    return h


def test_desactivar_un_puente_queda_en_audit_log(app):
    bid = _sembrar()
    c = _cli(app)
    r = c.delete('/api/programacion/mp-bridge/%d' % bid, headers=_h(c))
    assert r.status_code == 200, r.data[:200]
    db = _db()
    try:
        assert db.execute("SELECT activo FROM mp_formula_bridge WHERE id=?", (bid,)).fetchone()[0] == 0
        n = db.execute("SELECT COUNT(*) FROM audit_log WHERE accion='DESACTIVAR_PUENTE_MP' "
                       "AND registro_id=?", (str(bid),)).fetchone()[0]
        assert n >= 1, 'sin rastro no se puede saber quién quitó el puente ni revertirlo'
    finally:
        db.close()


def test_el_audit_guarda_a_donde_apuntaba(app):
    """Sin el destino previo no se puede revertir: el puente se recrea a ciegas."""
    bid = _sembrar()
    c = _cli(app)
    c.delete('/api/programacion/mp-bridge/%d' % bid, headers=_h(c))
    db = _db()
    try:
        antes = db.execute("SELECT antes FROM audit_log WHERE accion='DESACTIVAR_PUENTE_MP' "
                           "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(bid),)).fetchone()[0]
        assert A in (antes or '') and B in (antes or ''), antes
    finally:
        db.close()


def test_un_puente_inexistente_da_404(app):
    c = _cli(app)
    assert c.delete('/api/programacion/mp-bridge/99999999', headers=_h(c)).status_code == 404
