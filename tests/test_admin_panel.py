"""Tests del panel admin extendido: users, reset password, eventos, config."""
from .conftest import TEST_PASSWORD, csrf_headers


# ── /api/admin/users ─────────────────────────────────────────────────────────


def test_users_list_requires_admin(client, db_clean):
    r = client.get("/api/admin/users")
    assert r.status_code == 401


def test_users_list_blocked_for_non_admin(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "valentina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/admin/users")
    assert r.status_code == 403


def test_users_list_admin_returns_19_users(admin_client, db_clean):
    r = admin_client.get("/api/admin/users")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 19
    assert len(data["users"]) == 19


def test_users_list_includes_groups_and_password_source(admin_client, db_clean):
    r = admin_client.get("/api/admin/users")
    data = r.get_json()
    sebastian = next(u for u in data["users"] if u["username"] == "sebastian")
    assert sebastian["is_admin"] is True
    assert "Admin" in sebastian["groups"]
    assert sebastian["password_source"] in ("env", "db")
    # No expone hashes ni passwords
    assert "password_hash" not in sebastian
    assert "password" not in sebastian


def test_users_list_no_hashes_exposed(admin_client, db_clean):
    """CRITICAL: el endpoint NO debe devolver hashes ni passwords plaintext."""
    r = admin_client.get("/api/admin/users")
    body = r.get_data(as_text=True)
    # Ningun PBKDF2 hash ni la TEST_PASSWORD plana en el response
    assert "pbkdf2:" not in body
    assert TEST_PASSWORD not in body


# ── /api/admin/reset-password ────────────────────────────────────────────────


def test_reset_password_requires_admin(client, db_clean):
    r = client.post("/api/admin/reset-password",
                    json={"username": "valentina"},
                    headers=csrf_headers())
    assert r.status_code == 401


def test_reset_password_blocked_for_non_admin(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "felipe", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/admin/reset-password",
               json={"username": "felipe"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_reset_password_unknown_user(admin_client, db_clean):
    r = admin_client.post("/api/admin/reset-password",
                          json={"username": "fantasma"},
                          headers=csrf_headers())
    assert r.status_code == 404


def test_reset_password_missing_username(admin_client, db_clean):
    r = admin_client.post("/api/admin/reset-password",
                          json={},
                          headers=csrf_headers())
    assert r.status_code == 400


def test_reset_password_works_end_to_end(app, db_clean):
    """Admin resetea, user puede loguear con nueva password."""
    admin = app.test_client()
    admin.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    r = admin.post("/api/admin/reset-password",
                   json={"username": "valentina"},
                   headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    new_pwd = data["new_password"]
    assert len(new_pwd) >= 8

    # Valentina puede loguear con la nueva
    user_c = app.test_client()
    r = user_c.post("/login",
                    data={"username": "valentina", "password": new_pwd},
                    headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302  # redirect


def test_reset_password_disables_old_password(app, db_clean):
    """Después del reset, la password vieja (env var) ya no funciona."""
    admin = app.test_client()
    admin.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    admin.post("/api/admin/reset-password",
               json={"username": "yuliel"},
               headers=csrf_headers())
    # Ya no entra con la vieja TEST_PASSWORD
    user_c = app.test_client()
    r = user_c.post("/login",
                    data={"username": "yuliel", "password": TEST_PASSWORD},
                    headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 200  # fallo


# ── /api/admin/security-events ───────────────────────────────────────────────


def test_security_events_requires_admin(client, db_clean):
    r = client.get("/api/admin/security-events")
    assert r.status_code == 401


def test_security_events_returns_list(admin_client, db_clean):
    """Tras el login del admin (que generó login_success), debe haber al menos 1."""
    r = admin_client.get("/api/admin/security-events")
    assert r.status_code == 200
    data = r.get_json()
    assert "events" in data
    assert "stats_24h" in data
    assert isinstance(data["events"], list)


def test_security_events_filter_by_event_type(app, db_clean):
    """Filtro ?event=login_success funciona."""
    c = app.test_client()
    # Logear admin para generar 1 login_success
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/admin/security-events?event=login_success&limit=5")
    assert r.status_code == 200
    events = r.get_json()["events"]
    for e in events:
        assert e["event"] == "login_success"


def test_security_events_limit_capped(admin_client, db_clean):
    """Limit > 500 se capea a 500 (anti-abuso)."""
    r = admin_client.get("/api/admin/security-events?limit=99999")
    assert r.status_code == 200
    # No debe crashear ni devolver más de 500
    assert len(r.get_json()["events"]) <= 500


# ── /api/admin/config-status ─────────────────────────────────────────────────


def test_config_status_requires_admin(client, db_clean):
    r = client.get("/api/admin/config-status")
    assert r.status_code == 401


def test_config_status_returns_structure(admin_client, db_clean):
    r = admin_client.get("/api/admin/config-status")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("issues", "critical", "user_passwords", "optional"):
        assert key in data, f"Falta {key}"


def test_config_status_no_values_exposed(admin_client, db_clean):
    """CRITICAL: solo 'set' bool y 'length', NO el valor."""
    r = admin_client.get("/api/admin/config-status")
    body = r.get_data(as_text=True)
    # NO debe aparecer la SECRET_KEY de tests ni el TEST_PASSWORD
    assert "test-secret-key-only-for-pytest" not in body
    assert TEST_PASSWORD not in body
    # Cada item debe tener 'set' y 'length' pero NO 'value'
    data = r.get_json()
    for v in data["critical"] + data["user_passwords"] + data["optional"]:
        assert "set" in v
        assert "length" in v
        assert "value" not in v


def test_config_status_lists_all_user_passwords(admin_client, db_clean):
    """Las 19 PASS_<USER> aparecen."""
    r = admin_client.get("/api/admin/config-status")
    data = r.get_json()
    user_pass_names = {v["name"] for v in data["user_passwords"]}
    assert len(user_pass_names) == 19
    assert "PASS_SEBASTIAN" in user_pass_names


# ═══ Auditoria inventario vs Excel dia cero ═════════════════════════════════


def test_audit_inventario_vs_excel_solo_admin(app, db_clean):
    """POST /api/admin/audit-inventario-vs-excel → 403 para no-admin."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "luis", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    r = c.post("/api/admin/audit-inventario-vs-excel",
               data={}, headers=csrf_headers())
    assert r.status_code == 403


def test_audit_inventario_vs_excel_filtra_solo_verde(admin_client, db_clean):
    """El endpoint solo cuenta filas en color VERDE (FF92D050).

    Construye un Excel sintetico con 3 filas: 1 verde, 1 roja, 1 sin marcar.
    Verifica que solo la verde llega al reporte.
    """
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    import io

    wb = Workbook()
    ws = wb.active
    ws.title = "INVENTARIO"
    ws.cell(row=1, column=1, value="INVENTARIO DE MATERIAS PRIMAS")
    ws.cell(row=5, column=1, value="CÓDIGO MP")
    ws.cell(row=5, column=2, value="NOMBRE INCI")
    ws.cell(row=5, column=3, value="NOMBRE COMERCIAL")
    ws.cell(row=5, column=4, value="TIPO")
    ws.cell(row=5, column=5, value="PROVEEDOR")
    ws.cell(row=5, column=6, value="STOCK MIN")
    ws.cell(row=5, column=7, value="N° LOTE")
    ws.cell(row=5, column=8, value="CANT. CONTEO(g)")
    ws.cell(row=5, column=9, value="CANT. ACTUAL")
    ws.cell(row=5, column=10, value="ESTANTERIA")
    ws.cell(row=5, column=11, value="POS.")
    ws.cell(row=5, column=12, value="FECHA VENC.")

    verde = PatternFill(start_color="FF92D050", end_color="FF92D050", fill_type="solid")
    rojo = PatternFill(start_color="FFFF0000", end_color="FFFF0000", fill_type="solid")
    blanco = PatternFill(start_color="FFFFFFFF", end_color="FFFFFFFF", fill_type="solid")

    # Fila verde — debe contar
    for col in range(1, 13):
        ws.cell(row=6, column=col).fill = verde
    ws.cell(row=6, column=1, value="MP_VERDE_T")
    ws.cell(row=6, column=3, value="Material verde test")
    ws.cell(row=6, column=5, value="Lyphar")
    ws.cell(row=6, column=7, value="LOTE-V-1")
    ws.cell(row=6, column=8, value=1000)

    # Fila roja — debe excluir
    for col in range(1, 13):
        ws.cell(row=7, column=col).fill = rojo
    ws.cell(row=7, column=1, value="MP_ROJO_T")
    ws.cell(row=7, column=3, value="Material rojo test")
    ws.cell(row=7, column=7, value="LOTE-R-1")
    ws.cell(row=7, column=8, value=999999)

    # Fila blanca — debe excluir
    for col in range(1, 13):
        ws.cell(row=8, column=col).fill = blanco
    ws.cell(row=8, column=1, value="MP_BLANCO_T")
    ws.cell(row=8, column=7, value="LOTE-B-1")
    ws.cell(row=8, column=8, value=888888)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = admin_client.post(
        "/api/admin/audit-inventario-vs-excel",
        data={"file": (buf, "test.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, f"body: {r.data[:300]!r}"
    j = r.get_json()
    s = j["resumen"]
    assert s["lotes_verde_excel"] == 1, f"solo 1 verde, recibido: {s}"
    assert s["lotes_excluidos_no_verde"] == 2, (
        f"2 no-verde (rojo+blanco), recibido: {s}"
    )
    assert s["stock_total_excel_g"] == 1000.0
    # MP_VERDE_T no esta en DB → debe aparecer en faltantes
    faltantes_codigos = [x["codigo_mp"] for x in j["faltantes_en_db"]]
    assert "MP_VERDE_T" in faltantes_codigos
    # MP_ROJO_T y MP_BLANCO_T NO deben estar en ningun bucket
    todos = (j["en_db_match_sample"] + j["en_db_con_delta"]
             + j["faltantes_en_db"] + j["solo_db_no_excel"])
    codigos_total = [x.get("codigo_mp") for x in todos]
    assert "MP_ROJO_T" not in codigos_total
    assert "MP_BLANCO_T" not in codigos_total


def test_audit_inventario_vs_excel_excel_invalido(admin_client, db_clean):
    """Sin archivo o no-xlsx → 400."""
    r = admin_client.post("/api/admin/audit-inventario-vs-excel", data={})
    assert r.status_code == 400
    import io
    r = admin_client.post(
        "/api/admin/audit-inventario-vs-excel",
        data={"file": (io.BytesIO(b"not an excel"), "test.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400


def test_inventario_diagnostico_solo_admin(app, db_clean):
    """GET /api/admin/inventario-diagnostico-entradas → 403 para no-admin."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "luis", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    r = c.get("/api/admin/inventario-diagnostico-entradas")
    assert r.status_code == 403


def test_inventario_diagnostico_detecta_doble_carga(admin_client, db_clean):
    """Si un lote tiene 2 Entradas → debe aparecer en multi_entradas."""
    import sqlite3
    import os

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    # Lote con UNA entrada (legitimo)
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo, fecha,
                    operador)
                   VALUES ('MP_DIAG_OK','OK','LOTE-OK',1000,'Entrada',
                           '2026-04-20','sistema')""")
    # Lote con DOS entradas (doble carga)
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo, fecha,
                    operador)
                   VALUES ('MP_DIAG_DUP','DUP','LOTE-DUP',500,'Entrada',
                           '2026-04-20','sistema')""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo, fecha,
                    operador)
                   VALUES ('MP_DIAG_DUP','DUP','LOTE-DUP',500,'Entrada',
                           '2026-04-21','luis')""")
    conn.commit()
    conn.close()

    r = admin_client.get("/api/admin/inventario-diagnostico-entradas")
    assert r.status_code == 200
    j = r.get_json()
    duplicados = [m for m in j["multi_entradas"] if m["codigo_mp"] == "MP_DIAG_DUP"]
    assert len(duplicados) == 1, f"Doble carga no detectada: {j['multi_entradas']}"
    assert duplicados[0]["n_entradas"] == 2
    assert duplicados[0]["total_g"] == 1000.0

    # MP_DIAG_OK NO debe aparecer (solo 1 entrada)
    legits = [m for m in j["multi_entradas"] if m["codigo_mp"] == "MP_DIAG_OK"]
    assert len(legits) == 0

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("DELETE FROM movimientos WHERE material_id IN ('MP_DIAG_OK','MP_DIAG_DUP')")
    conn.commit(); conn.close()
