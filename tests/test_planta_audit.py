"""Tests de audit_log en acciones INVIMA-críticas de planta.

Verifica audit_log para:
- recepcion_aprobar_lote (despachos.py · liberación MP cuarentena)
- prog_iniciar_produccion / prog_terminar_produccion (programacion.py · trazabilidad lote)
- planta_envasado_iniciar / planta_envasado_terminar
- planta_cola_liberacion_disposicion (LIBERACIÓN PT · decisión INVIMA)

INVIMA Resolución 2214/2021 art. 10: liberación de PT documentada.
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


# ─── Recepción · aprobar lote MP ─────────────────────────────────────

def test_aprobar_lote_user_no_calidad_403(app, db_clean):
    """Solo Calidad/Admin puede aprobar lote (no luis · operario)."""
    c = _login(app, "luis")
    r = c.post("/api/recepcion/aprobar-lote",
               json={"mov_id": 1, "estado": "Aprobado"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_aprobar_lote_audita(app, db_clean):
    c = _login(app, "laura")
    # Sembrar movimiento de entrada en cuarentena
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO movimientos (tipo, material_id, material_nombre, cantidad,
                                  lote, estado_lote, proveedor, fecha)
        VALUES ('Entrada', 'MP-T1', 'Test MP', 100, 'LOTE-AUDIT-T1',
                'Cuarentena', 'Prov X', datetime('now'))
    """)
    mov_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post("/api/recepcion/aprobar-lote",
                   json={"mov_id": mov_id, "estado": "Aprobado"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="APROBAR_LOTE")
        assert audit is not None
        assert audit[0] == "laura"
        assert "LOTE-AUDIT-T1" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE id=?", (mov_id,))
        conn.commit(); conn.close()


def test_rechazar_lote_requiere_motivo(app, db_clean):
    """Rechazar lote sin motivo (≥10 chars) devuelve 400."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO movimientos (tipo, material_nombre, cantidad, lote,
                                  estado_lote, fecha)
        VALUES ('Entrada', 'Test', 1, 'LOTE-REJ-T', 'Cuarentena', datetime('now'))
    """)
    mov_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post("/api/recepcion/aprobar-lote",
                   json={"mov_id": mov_id, "estado": "Rechazado"},
                   headers=csrf_headers())
        assert r.status_code == 400
        # Con motivo válido
        r = c.post("/api/recepcion/aprobar-lote",
                   json={"mov_id": mov_id, "estado": "Rechazado",
                         "motivo": "Lote contaminado · evidencia visible"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="RECHAZAR_LOTE")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE id=?", (mov_id,))
        conn.commit(); conn.close()


def test_aprobar_lote_estado_invalido_400(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/recepcion/aprobar-lote",
               json={"mov_id": 1, "estado": "PendienteFoo"},
               headers=csrf_headers())
    assert r.status_code == 400


# ─── Producción iniciar/terminar ─────────────────────────────────────

def test_iniciar_produccion_audita(app, db_clean):
    c = _login(app, "luis")  # operario tiene acceso (compras_user)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado)
        VALUES ('PROD-AUDIT-T1', date('now'), 1, 'pendiente')
    """)
    prod_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/programacion/programar/{prod_id}/iniciar",
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="INICIAR_PRODUCCION")
        assert audit is not None
        assert "PROD-AUDIT-T1" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (prod_id,))
        conn.commit(); conn.close()


def test_terminar_produccion_audita(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO produccion_programada
            (producto, fecha_programada, lotes, estado, inicio_real_at)
        VALUES ('PROD-FIN-T1', date('now'), 1, 'pendiente', datetime('now','-2 hours'))
    """)
    prod_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/programacion/programar/{prod_id}/terminar",
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="TERMINAR_PRODUCCION")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (prod_id,))
        conn.commit(); conn.close()


# ─── Liberación PT (decisión INVIMA crítica) ─────────────────────────

def test_liberacion_disposicion_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")  # luis no es Calidad
    r = c.post("/api/planta/cola-liberacion/1/disposicion",
               json={"disposicion": "aprobado"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_liberar_lote_audita(app, db_clean):
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO cola_liberacion
            (envasado_id, producto_nombre, lote, unidades,
             fecha_envasado, fecha_min_liberacion, estado)
        VALUES (1, 'PT-AUDIT-T1', 'LOTE-LIB-T1', 100,
                date('now'), date('now'), 'listo_revisar')
    """)
    item_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/planta/cola-liberacion/{item_id}/disposicion",
                   json={"disposicion": "aprobado"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="LIBERAR_LOTE_PT")
        assert audit is not None
        assert audit[0] == "laura"
        assert "LOTE-LIB-T1" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM cola_liberacion WHERE id=?", (item_id,))
        conn.commit(); conn.close()


def test_rechazar_lote_pt_requiere_notas(app, db_clean):
    """Rechazar PT sin notas (≥10) → 400."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO cola_liberacion
            (envasado_id, producto_nombre, lote, unidades,
             fecha_envasado, fecha_min_liberacion, estado)
        VALUES (1, 'PT-REJ-T', 'LOTE-REJ-T', 50,
                date('now'), date('now'), 'listo_revisar')
    """)
    item_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        # Sin notas → 400
        r = c.post(f"/api/planta/cola-liberacion/{item_id}/disposicion",
                   json={"disposicion": "rechazado"},
                   headers=csrf_headers())
        assert r.status_code == 400
        # Con notas → 200 + audit
        r = c.post(f"/api/planta/cola-liberacion/{item_id}/disposicion",
                   json={"disposicion": "rechazado",
                         "notas": "Conteo microbiológico fuera spec"},
                   headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="RECHAZAR_LOTE_PT")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM cola_liberacion WHERE id=?", (item_id,))
        conn.commit(); conn.close()


def test_liberacion_disposicion_invalida_400(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/planta/cola-liberacion/1/disposicion",
               json={"disposicion": "FOO"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_liberacion_item_no_encontrado_404(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/planta/cola-liberacion/9999999/disposicion",
               json={"disposicion": "aprobado"},
               headers=csrf_headers())
    assert r.status_code == 404
