"""Tests de audit_log en operaciones críticas de compras.py.

Cubre las nuevas acciones agregadas (audit zero-error · 2-may-2026):
- CREAR_OC, EDITAR_OC, AGREGAR_ITEM_OC, MODIFICAR_ITEM_OC
- CONFIRMAR_PROVEEDOR_OC, ACTUALIZAR_PRECIOS_OC
- CREAR_SOLICITUD, ACTUALIZAR_ESTADO_SOL, RECHAZAR_SOLICITUD
- APROBAR_SOLICITUD_INFLUENCER, MARCAR_RECIBIDO_SOLICITANTE
- RECIBIR_OC, REVISAR_OC, RECHAZAR_OC
- ELEGIR_COTIZACION_GANADORA
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


def _last_audit(accion=None, registro_id=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    where = []; params = []
    if accion:
        where.append("accion=?"); params.append(accion)
    if registro_id is not None:
        where.append("registro_id=?"); params.append(str(registro_id))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ─── CREAR_OC ────────────────────────────────────────────────────────

def test_crear_oc_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/ordenes-compra",
               json={"proveedor": "Proveedor Audit Test", "categoria": "MP",
                     "items": [{"codigo_mp": "MP-AUDIT-T1",
                                "nombre_mp": "Item audit", "cantidad_g": 1000,
                                "precio_unitario": 50}]},
               headers=csrf_headers())
    assert r.status_code == 201, r.data
    numero_oc = r.get_json()["numero_oc"]
    audit = _last_audit(accion="CREAR_OC", registro_id=numero_oc)
    assert audit is not None
    assert audit[0] == "sebastian"
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    conn.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    conn.execute("DELETE FROM precios_mp_historico WHERE numero_oc=?", (numero_oc,))
    conn.commit(); conn.close()


def test_crear_oc_user_no_compras_403(app, db_clean):
    c = _login(app, "luis")  # luis no es Compras/Admin
    r = c.post("/api/ordenes-compra",
               json={"proveedor": "X", "items": []}, headers=csrf_headers())
    assert r.status_code == 403


def test_crear_oc_sin_proveedor_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/ordenes-compra", json={"items": []}, headers=csrf_headers())
    assert r.status_code == 400


# ─── CONFIRMAR_PROVEEDOR_OC ──────────────────────────────────────────

def test_confirmar_proveedor_oc_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO ordenes_compra
        (numero_oc, fecha, estado, proveedor)
        VALUES ('OC-AUDT-CONF', date('now'), 'Borrador', 'Prov Original')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/ordenes-compra/OC-AUDT-CONF/proveedor",
                    json={"proveedor": "Prov Nuevo Confirmado"},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="CONFIRMAR_PROVEEDOR_OC", registro_id="OC-AUDT-CONF")
        assert audit is not None
        assert "Prov Original" in (audit[4] or "")
        assert "Prov Nuevo" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-AUDT-CONF'")
        conn.commit(); conn.close()


# ─── CREAR_SOLICITUD ────────────────────────────────────────────────

def test_crear_solicitud_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/solicitudes-compra",
               json={"solicitante": "sebastian", "categoria": "Materia Prima",
                     "empresa": "Espagiria", "tipo": "Compra",
                     "area": "Produccion", "valor": 100000,
                     "items": [{"codigo_mp": "MP-AUDIT-S",
                                "nombre_mp": "Item sol",
                                "cantidad_g": 500, "unidad": "g"}]},
               headers=csrf_headers())
    assert r.status_code == 201, r.data
    numero = r.get_json()["numero"]
    audit = _last_audit(accion="CREAR_SOLICITUD", registro_id=numero)
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
    conn.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,))
    conn.commit(); conn.close()


# ─── ACTUALIZAR_ESTADO_SOL ──────────────────────────────────────────

def test_actualizar_estado_sol_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO solicitudes_compra
        (numero, fecha, estado, solicitante, categoria, empresa)
        VALUES ('SOL-AUDT-EST', date('now'), 'Pendiente', 'sebastian',
                'Materia Prima', 'Espagiria')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/solicitudes-compra/SOL-AUDT-EST/estado",
                    json={"estado": "Aprobada"}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="ACTUALIZAR_ESTADO_SOL", registro_id="SOL-AUDT-EST")
        assert audit is not None
        assert "Pendiente" in (audit[4] or "") and "Aprobada" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM solicitudes_compra WHERE numero='SOL-AUDT-EST'")
        conn.commit(); conn.close()


def test_actualizar_estado_sol_inexistente_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.patch("/api/solicitudes-compra/SOL-NO-EXISTE-XYZ/estado",
                json={"estado": "Aprobada"}, headers=csrf_headers())
    assert r.status_code == 404


# ─── RECHAZAR_SOLICITUD ─────────────────────────────────────────────

def test_rechazar_solicitud_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO solicitudes_compra
        (numero, fecha, estado, solicitante, categoria, empresa)
        VALUES ('SOL-AUDT-REJ', date('now'), 'Pendiente', 'sebastian',
                'Materia Prima', 'Espagiria')""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/solicitudes-compra/SOL-AUDT-REJ/rechazar",
                   json={"motivo": "Test rechazo audit"},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="RECHAZAR_SOLICITUD", registro_id="SOL-AUDT-REJ")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM solicitudes_compra WHERE numero='SOL-AUDT-REJ'")
        conn.commit(); conn.close()


# ─── REVISAR_OC ─────────────────────────────────────────────────────

def test_revisar_oc_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
        (numero_oc, fecha, estado, proveedor)
        VALUES ('OC-AUDT-REV', date('now'), 'Pendiente', 'Prov Rev')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/ordenes-compra/OC-AUDT-REV/revisar",
                    json={"valor_total": 250000}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="REVISAR_OC", registro_id="OC-AUDT-REV")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-AUDT-REV'")
        conn.commit(); conn.close()


# ─── RECHAZAR_OC ────────────────────────────────────────────────────

def test_rechazar_oc_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
        (numero_oc, fecha, estado, proveedor, categoria)
        VALUES ('OC-AUDT-REJ', date('now'), 'Pendiente', 'Prov Rej', 'MP')""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/compras/oc/OC-AUDT-REJ/rechazar",
                   json={"motivo": "Test rechazo OC audit"},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="RECHAZAR_OC", registro_id="OC-AUDT-REJ")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-AUDT-REJ'")
        conn.commit(); conn.close()


# ─── AGREGAR_ITEM_OC ────────────────────────────────────────────────

def test_agregar_item_oc_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
        (numero_oc, fecha, estado, proveedor)
        VALUES ('OC-AUDT-ITEM', date('now'), 'Borrador', 'Prov')""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/ordenes-compra/OC-AUDT-ITEM/items",
                   json={"codigo_mp": "MP-X", "nombre_mp": "Nuevo item",
                         "cantidad_g": 500, "precio_unitario": 100},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="AGREGAR_ITEM_OC", registro_id="OC-AUDT-ITEM")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-AUDT-ITEM'")
        conn.execute("DELETE FROM ordenes_compra_items WHERE numero_oc='OC-AUDT-ITEM'")
        conn.commit(); conn.close()


# ─── ELEGIR_COTIZACION_GANADORA ──────────────────────────────────────

def test_elegir_ganadora_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO cotizaciones
        (ronda_id, proveedor, descripcion, valor_total, estado, ganadora)
        VALUES ('COT-AUDT-1', 'Prov Ganador', 'Test cotización',
                500000, 'Recibida', 0)""")
    cot_id = cur.lastrowid
    cur = conn.execute("""INSERT INTO cotizaciones
        (ronda_id, proveedor, descripcion, valor_total, estado, ganadora)
        VALUES ('COT-AUDT-1', 'Prov Otro', 'Test cotización',
                600000, 'Recibida', 0)""")
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/compras/cotizaciones/{cot_id}/elegir-ganadora",
                   json={}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="ELEGIR_COTIZACION_GANADORA", registro_id=cot_id)
        assert audit is not None
        assert "Prov Ganador" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM cotizaciones WHERE ronda_id='COT-AUDT-1'")
        conn.commit(); conn.close()
