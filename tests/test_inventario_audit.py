"""Tests de audit_log en mutaciones críticas de inventario.

Cubre: archivar_mp, actualizar_precio_mp, liberacion_update,
acondicionamiento_update, mee_anular_movimiento, mee_ajustar_stock.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


def _last_audit(accion=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    params = []
    if accion:
        sql += " WHERE accion=?"; params.append(accion)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ─── archivar_mp ─────────────────────────────────────────────────────

def test_archivar_mp_requiere_auth(client, db_clean):
    r = client.put("/api/maestro-mps/MP-X/archivar", headers=csrf_headers())
    assert r.status_code == 401


def test_archivar_mp_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")  # luis no es Calidad/Admin
    r = c.put("/api/maestro-mps/MP-X/archivar", headers=csrf_headers())
    assert r.status_code == 403


def test_archivar_mp_audita(app, db_clean):
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
                    (codigo_mp, nombre_inci, nombre_comercial, tipo, activo)
                    VALUES ('MP-AUDIT-T1', 'INCI', 'MP audit test', 'MP', 1)""")
    conn.commit(); conn.close()
    try:
        r = c.put("/api/maestro-mps/MP-AUDIT-T1/archivar", headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ARCHIVAR_MP")
        assert audit is not None
        assert audit[0] == "laura"
        assert audit[3] == "MP-AUDIT-T1"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP-AUDIT-T1'")
        conn.commit(); conn.close()


def test_archivar_mp_inexistente_404(app, db_clean):
    c = _login(app, "laura")
    r = c.put("/api/maestro-mps/MP-NO-EXISTE-XYZ/archivar", headers=csrf_headers())
    assert r.status_code == 404


# ─── actualizar_precio_mp ────────────────────────────────────────────

def test_actualizar_precio_mp_requiere_auth(client, db_clean):
    r = client.post("/api/maestro-mp/MP-X/precio",
                    json={"precio_kg": 100}, headers=csrf_headers())
    assert r.status_code == 401


def test_actualizar_precio_mp_audita(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
                    (codigo_mp, nombre_inci, nombre_comercial, activo, precio_referencia)
                    VALUES ('MP-PREC-T1', 'INCI', 'MP precio test', 1, 100.0)""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/maestro-mp/MP-PREC-T1/precio",
                   json={"precio_kg": 250.50, "origen": "factura proveedor"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_PRECIO_MP")
        assert audit is not None
        assert "100" in (audit[4] or "") and "250" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP-PREC-T1'")
        conn.execute("DELETE FROM precios_mp_historico WHERE codigo_mp='MP-PREC-T1'")
        conn.commit(); conn.close()


def test_actualizar_precio_mp_negativo_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/maestro-mp/MP-X/precio",
               json={"precio_kg": -50}, headers=csrf_headers())
    assert r.status_code == 400


def test_actualizar_precio_mp_nan_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/maestro-mp/MP-X/precio",
               json={"precio_kg": float('nan')}, headers=csrf_headers())
    # nan se serializa como NaN literal; el endpoint debe rechazar
    assert r.status_code == 400


# ─── liberacion_update (PT release · INVIMA art. 10) ────────────────

def test_liberacion_update_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.patch("/api/liberacion/1",
                json={"estado": "Liberado"}, headers=csrf_headers())
    assert r.status_code == 403


def test_liberacion_rechazo_requiere_observaciones(app, db_clean):
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO liberaciones
        (acondicionamiento_id, lote, producto, unidades, estado)
        VALUES (1, 'LOTE-LIB-AUDIT', 'PROD test', 100, 'Pendiente')""")
    lid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.patch(f"/api/liberacion/{lid}",
                    json={"estado": "Rechazado"}, headers=csrf_headers())
        assert r.status_code == 400
        r = c.patch(f"/api/liberacion/{lid}",
                    json={"estado": "Rechazado",
                          "observaciones": "Lote contaminado · evidencia"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="RECHAZAR_PT")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM liberaciones WHERE id=?", (lid,))
        conn.commit(); conn.close()


def test_liberacion_aprobado_audita(app, db_clean):
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO liberaciones
        (acondicionamiento_id, lote, producto, unidades, estado, sku)
        VALUES (1, 'LOTE-OK-AUDIT', 'PROD ok', 50, 'Pendiente', 'SKU-T')""")
    lid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.patch(f"/api/liberacion/{lid}",
                    json={"estado": "Liberado", "cliente": "Cliente Test"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="LIBERAR_PT")
        assert audit is not None
        assert audit[0] == "laura"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM liberaciones WHERE id=?", (lid,))
        conn.execute("DELETE FROM stock_pt WHERE lote_produccion='LOTE-OK-AUDIT'")
        conn.commit(); conn.close()


# ─── mee_anular_movimiento ──────────────────────────────────────────

def test_mee_anular_audita(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Crear MEE + movimiento
    conn.execute("""INSERT OR IGNORE INTO maestro_mee
        (codigo, descripcion, stock_actual) VALUES ('MEE-T1', 'MEE test', 100)""")
    cur = conn.execute("""INSERT INTO movimientos_mee
        (mee_codigo, tipo, cantidad, responsable, observaciones, anulado)
        VALUES ('MEE-T1', 'Entrada', 50, 'luis', 'test', 0)""")
    mov_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/mee/anular/{mov_id}",
                   json={"motivo": "Error registro"}, headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ANULAR_MOV_MEE")
        assert audit is not None
        assert audit[0] == "luis"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos_mee WHERE id=?", (mov_id,))
        conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-T1'")
        conn.commit(); conn.close()


# ─── mee_ajustar_stock ──────────────────────────────────────────────

def test_mee_ajustar_audita(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mee
        (codigo, descripcion, stock_actual) VALUES ('MEE-AJ-T1', 'MEE ajustar', 50)""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/mee/MEE-AJ-T1/ajustar",
                   json={"cantidad_nueva": 75, "motivo": "Conteo físico"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="AJUSTAR_STOCK_MEE")
        assert audit is not None
        assert "50" in (audit[4] or "") and "75" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-AJ-T1'")
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-AJ-T1'")
        conn.commit(); conn.close()


# ─── acondicionamiento_update ───────────────────────────────────────

def test_acondicionamiento_update_audita(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO acondicionamiento
        (lote, producto, estado, unidades_producidas)
        VALUES ('LOTE-AC-T1', 'PROD ac', 'En proceso', 0)""")
    aid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.patch(f"/api/acondicionamiento/{aid}",
                    json={"estado": "Completado", "unidades_producidas": 200},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_ACONDICIONAMIENTO")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM acondicionamiento WHERE id=?", (aid,))
        conn.commit(); conn.close()
