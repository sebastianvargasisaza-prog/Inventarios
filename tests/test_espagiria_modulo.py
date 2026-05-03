"""Tests modulo Espagiria · Clientes Maquila 360 + Lab en vivo.

Sebastian 3-may-2026: Luz necesita ver clientes maquila completos +
reportes en tiempo real del laboratorio.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luz"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def test_pagina_espagiria_carga(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/espagiria")
    assert r.status_code == 200


def test_pagina_espagiria_tiene_tabs(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/espagiria")
    body = r.get_data(as_text=True)
    assert 'data-tab="dash"' in body
    assert 'data-tab="lab"' in body
    assert 'data-tab="clientes"' in body
    assert 'esp-tab-dash' in body
    assert 'esp-tab-lab' in body
    assert 'esp-tab-clientes' in body
    assert 'cargarLab' in body
    assert 'cargarClientes' in body
    assert 'verCli360' in body


def test_acceso_solo_espagiria_users(app, db_clean):
    """User sin acceso a espagiria recibe 403."""
    c = app.test_client()
    c.post("/login", data={"username": "mayerlin", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/espagiria")
    # mayerlin (operario planta) no esta en ESPAGIRIA_ACCESS
    assert r.status_code == 403


def test_clientes_maquila_lista_endpoint(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/clientes-maquila")
    assert r.status_code == 200
    d = r.get_json()
    assert "clientes" in d


def test_cliente_maquila_360_endpoint_404_si_no_existe(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/clientes-maquila/9999999/360")
    assert r.status_code == 404


def test_cliente_maquila_360_devuelve_estructura(app, db_clean):
    cs = _login(app, "luz")
    # Crear cliente maquila de prueba
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO clientes_maquila (nombre, nit_cedula, email) VALUES ('TEST-CLI-360', '900111222', 'test@test.com')")
    cid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = cs.get(f"/api/espagiria/clientes-maquila/{cid}/360")
        assert r.status_code == 200
        d = r.get_json()
        for k in ("cliente", "stats", "pedidos_recientes", "pipeline_activo", "top_productos"):
            assert k in d
        assert d["cliente"]["nombre"] == "TEST-CLI-360"
        for k in ("total_pedidos", "valor_total", "ticket_promedio",
                  "ultimo_pedido", "pipeline_activos"):
            assert k in d["stats"]
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes_maquila WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_lab_en_vivo_endpoint(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/lab/en-vivo")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("timestamp", "producciones_en_curso", "producciones_hoy",
              "equipos_estado", "lotes_cuarentena", "oos_abiertos",
              "agua_hoy", "capacitaciones_pendientes",
              "desviaciones_abiertas"):
        assert k in d, f"falta clave {k} en respuesta lab/en-vivo"


def test_lab_en_vivo_requiere_auth(client, db_clean):
    r = client.get("/api/espagiria/lab/en-vivo")
    assert r.status_code in (401, 403)


def test_dashboard_endpoint_funciona(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/dashboard")
    assert r.status_code == 200


# ── Quick Actions ──────────────────────────────────────────────────

def test_quick_actions_endpoint(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/quick-actions")
    assert r.status_code == 200
    d = r.get_json()
    assert "secciones" in d
    assert "total_urgentes" in d
    assert "timestamp" in d


def test_quick_actions_requiere_auth(client, db_clean):
    r = client.get("/api/espagiria/quick-actions")
    assert r.status_code in (401, 403)


# ── Pedido rápido ──────────────────────────────────────────────────

def test_pedido_rapido_crea_correctamente(app, db_clean):
    cs = _login(app, "luz")
    # Cliente de prueba
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO clientes_maquila (nombre, nit_cedula) VALUES ('TEST-PR-CLI', '900PR001')")
    cid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = cs.post("/api/espagiria/pedido-rapido",
                    json={"cliente_id": cid, "producto_nombre": "Prod test PR",
                          "unidades": 100, "precio_unidad": 5000,
                          "fecha_entrega_objetivo": "2026-06-01"},
                    headers=csrf_headers())
        assert r.status_code == 201, r.data
        d = r.get_json()
        assert d["ok"] is True
        assert "numero" in d
        assert d["numero"].startswith("MQ-")
        assert d["valor_total"] == 100 * 5000
        # Verificar audit
        conn = sqlite3.connect(os.environ["DB_PATH"])
        a = conn.execute(
            "SELECT accion FROM audit_log WHERE accion='CREAR_PEDIDO_MAQUILA_RAPIDO' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert a is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maquila_pedidos WHERE cliente_id=?", (cid,))
        conn.execute("DELETE FROM clientes_maquila WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_pedido_rapido_rechaza_cliente_invalido(app, db_clean):
    cs = _login(app, "luz")
    r = cs.post("/api/espagiria/pedido-rapido",
                json={"cliente_id": 9999999, "producto_nombre": "X", "unidades": 1},
                headers=csrf_headers())
    assert r.status_code == 400


def test_pedido_rapido_rechaza_unidades_cero(app, db_clean):
    cs = _login(app, "luz")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO clientes_maquila (nombre) VALUES ('TEST-PR-Z')")
    cid = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = cs.post("/api/espagiria/pedido-rapido",
                    json={"cliente_id": cid, "producto_nombre": "X", "unidades": 0},
                    headers=csrf_headers())
        assert r.status_code == 400
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes_maquila WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_pedido_rapido_rechaza_precio_negativo(app, db_clean):
    cs = _login(app, "luz")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        "INSERT INTO clientes_maquila (nombre) VALUES ('TEST-PR-N')")
    cid = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = cs.post("/api/espagiria/pedido-rapido",
                    json={"cliente_id": cid, "producto_nombre": "X", "unidades": 1,
                          "precio_unidad": -100},
                    headers=csrf_headers())
        assert r.status_code == 400
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes_maquila WHERE id=?", (cid,))
        conn.commit(); conn.close()


# ── Cartera ────────────────────────────────────────────────────────

def test_cartera_endpoint(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/api/espagiria/cartera-maquila")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("kpis", "por_cliente", "pedidos"):
        assert k in d
    for k in ("total_facturado", "total_pagado", "total_saldo",
              "total_vencido_30d", "total_pedidos"):
        assert k in d["kpis"]


# ── UI Tabs nuevos ─────────────────────────────────────────────────

def test_pagina_espagiria_tiene_tabs_nuevos(app, db_clean):
    cs = _login(app, "luz")
    r = cs.get("/espagiria")
    body = r.get_data(as_text=True)
    assert 'data-tab="inicio"' in body
    assert 'data-tab="cartera"' in body
    assert 'esp-tab-inicio' in body
    assert 'esp-tab-cartera' in body
    assert 'cargarQA' in body
    assert 'cargarCartera' in body
    assert 'abrirPedidoRapido' in body
    assert 'guardarPedidoRapido' in body
    assert 'pr-modal' in body
