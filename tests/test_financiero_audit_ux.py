"""Tests audit_log + CSRF + paginacion en Financiero.

Sebastian 3-may-2026: financiero maneja $$ y antes tenia audit_log=0.
Ahora todos los movimientos ($$$$) quedan trazados.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _last_audit(accion):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT usuario, accion, tabla, detalle FROM audit_log WHERE accion=? ORDER BY id DESC LIMIT 1",
        (accion,)).fetchone()
    conn.close()
    return row


def _cleanup(table, where, params):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
    conn.commit(); conn.close()


# ── audit_log en mutaciones $ ──────────────────────────────────────────

def test_crear_ingreso_audita(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/ingresos",
                json={"fecha": "2026-05-03", "empresa": "ANIMUS",
                      "concepto": "Test ingreso audit", "categoria": "Ventas",
                      "monto": 1500000, "referencia": "TEST-AUD-001"},
                headers=csrf_headers())
    assert r.status_code == 201, r.data
    audit = _last_audit("CREAR_INGRESO_FIN")
    assert audit is not None
    assert audit[0] == "sebastian"
    _cleanup("flujo_ingresos", "referencia=?", ("TEST-AUD-001",))


def test_crear_egreso_audita(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/egresos",
                json={"fecha": "2026-05-03", "empresa": "ESPAGIRIA",
                      "concepto": "Test egreso audit", "categoria": "MPs",
                      "monto": 800000, "referencia": "TEST-AUD-002"},
                headers=csrf_headers())
    assert r.status_code == 201
    audit = _last_audit("CREAR_EGRESO_FIN")
    assert audit is not None
    _cleanup("flujo_egresos", "referencia=?", ("TEST-AUD-002",))


def test_ingreso_rechaza_monto_negativo(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/ingresos",
                json={"concepto": "Negativo", "monto": -1000},
                headers=csrf_headers())
    assert r.status_code == 400


def test_ingreso_rechaza_monto_invalido(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/ingresos",
                json={"concepto": "Sin monto", "monto": "not-a-number"},
                headers=csrf_headers())
    assert r.status_code == 400


def test_limpiar_flujo_audita(app, db_clean):
    cs = _login(app, "sebastian")
    # Sembrar algo para borrar
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_ingresos WHERE referencia='AUD-LIMP'")
    conn.execute(
        """INSERT INTO flujo_ingresos (fecha, empresa, concepto, categoria, monto, periodo, fuente, referencia)
           VALUES ('2026-05-03','HHA','Para borrar','Test',100,'2026-05','manual','AUD-LIMP')""")
    conn.commit(); conn.close()
    r = cs.post("/api/financiero/limpiar-flujo",
                json={"confirmar": "LIMPIAR_TODO"}, headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit("LIMPIAR_FLUJO")
    assert audit is not None


def test_limpiar_flujo_rechaza_sin_confirmacion(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/limpiar-flujo",
                json={}, headers=csrf_headers())
    assert r.status_code == 400


def test_actualizar_precio_mayorista_audita(app, db_clean):
    cs = _login(app, "sebastian")
    # Sembrar SKU
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sku_precios WHERE sku='AUD-MAY-001'")
    conn.execute(
        "INSERT INTO sku_precios (sku, descripcion, precio_base, precio_mayorista, unidad) VALUES ('AUD-MAY-001','Test',1000,800,'und')")
    conn.commit(); conn.close()
    try:
        r = cs.post("/api/financiero/precios-mayorista/AUD-MAY-001",
                    json={"precio_mayorista": 750}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit("ACTUALIZAR_PRECIO_MAYORISTA")
        assert audit is not None
    finally:
        _cleanup("sku_precios", "sku=?", ("AUD-MAY-001",))


def test_precio_mayorista_rechaza_negativo(app, db_clean):
    cs = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sku_precios WHERE sku='AUD-NEG-001'")
    conn.execute(
        "INSERT INTO sku_precios (sku, descripcion, precio_base, precio_mayorista, unidad) VALUES ('AUD-NEG-001','Test',1000,800,'und')")
    conn.commit(); conn.close()
    try:
        r = cs.post("/api/financiero/precios-mayorista/AUD-NEG-001",
                    json={"precio_mayorista": -100}, headers=csrf_headers())
        assert r.status_code == 400
    finally:
        _cleanup("sku_precios", "sku=?", ("AUD-NEG-001",))


def test_config_actualizar_audita(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/financiero/config",
                json={"test_key_audit": "test_value_001"},
                headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit("ACTUALIZAR_CONFIG_FIN")
    assert audit is not None
    _cleanup("flujo_config", "clave=?", ("test_key_audit",))


# ── CSRF + Paginacion en frontend ─────────────────────────────────────

def test_pagina_financiero_tiene_csrf(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/financiero")
    body = r.get_data(as_text=True)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    assert "method:'POST'" not in body


def test_pagina_financiero_tiene_paginacion(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/financiero")
    body = r.get_data(as_text=True)
    assert "TBL_STATE" in body
    assert "_paginar" in body
    assert "buscarTabla" in body
    for tab in ('pg-ing', 'pg-egr'):
        assert f'id="{tab}"' in body
    for tabla in ('ing', 'egr'):
        assert f"buscarTabla('{tabla}'" in body
