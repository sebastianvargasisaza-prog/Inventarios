"""Tests inventario fisico Animus · Fase 1.

Sebastian 3-may-2026: la asistente Daniela cuenta inventario fisico
y nunca cuadra con Shopify. Solucion: ecuacion contable.
  stock_esperado = baseline + Σ(entradas) − Σ(ventas_shopify) − Σ(salidas)
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


def _cleanup(sku):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_inventario_baseline WHERE sku=?", (sku,))
    conn.execute("DELETE FROM animus_inventario_movimientos WHERE sku=?", (sku,))
    conn.commit(); conn.close()


# ── BASELINE ──────────────────────────────────────────────────────

def test_baseline_crear(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/baseline",
                json={"sku": "TEST-INV-001", "unidades_baseline": 120,
                      "fecha_baseline": "2026-05-03",
                      "descripcion": "Hydra Balance Test"},
                headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["unidades_baseline"] == 120
    _cleanup("TEST-INV-001")


def test_baseline_actualizar_es_idempotente(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-INV-002", "unidades_baseline": 50},
            headers=csrf_headers())
    r2 = cs.post("/api/animus/inv-fisico/baseline",
                 json={"sku": "TEST-INV-002", "unidades_baseline": 60},
                 headers=csrf_headers())
    assert r2.status_code == 200
    # Verificar que solo hay una fila
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute(
        "SELECT COUNT(*) FROM animus_inventario_baseline WHERE sku='TEST-INV-002'"
    ).fetchone()[0]
    conn.close()
    assert n == 1
    _cleanup("TEST-INV-002")


def test_baseline_rechaza_negativo(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/baseline",
                json={"sku": "TEST-NEG", "unidades_baseline": -5},
                headers=csrf_headers())
    assert r.status_code == 400


def test_baseline_rechaza_sku_vacio(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/baseline",
                json={"unidades_baseline": 10}, headers=csrf_headers())
    assert r.status_code == 400


# ── ENTRADAS / SALIDAS ────────────────────────────────────────────

def test_entrada_basica(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-ENT-001", "unidades_baseline": 0},
            headers=csrf_headers())
    r = cs.post("/api/animus/inv-fisico/entrada",
                json={"sku": "TEST-ENT-001", "cantidad": 50,
                      "origen": "produccion", "referencia": "LOTE-001"},
                headers=csrf_headers())
    assert r.status_code == 200
    _cleanup("TEST-ENT-001")


def test_entrada_rechaza_cantidad_cero(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/entrada",
                json={"sku": "X", "cantidad": 0}, headers=csrf_headers())
    assert r.status_code == 400


def test_entrada_rechaza_cantidad_negativa(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/entrada",
                json={"sku": "X", "cantidad": -5}, headers=csrf_headers())
    assert r.status_code == 400


def test_entrada_rechaza_origen_invalido(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/entrada",
                json={"sku": "X", "cantidad": 5, "origen": "robo"},
                headers=csrf_headers())
    assert r.status_code == 400


def test_salida_basica(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/salida",
                json={"sku": "TEST-SAL-001", "cantidad": 3,
                      "origen": "regalo", "motivo": "Influencer Maria"},
                headers=csrf_headers())
    assert r.status_code == 200


def test_salida_rechaza_origen_invalido(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/salida",
                json={"sku": "X", "cantidad": 1, "origen": "exportacion"},
                headers=csrf_headers())
    assert r.status_code == 400


# ── ECUACION CONTABLE ──────────────────────────────────────────────

def test_esperado_sin_baseline_404(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/animus/inv-fisico/esperado/SKU-NO-EXISTE")
    assert r.status_code == 404


def test_esperado_solo_baseline(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-ESP-001", "unidades_baseline": 100,
                  "fecha_baseline": "2026-05-01"},
            headers=csrf_headers())
    r = cs.get("/api/animus/inv-fisico/esperado/TEST-ESP-001")
    assert r.status_code == 200
    d = r.get_json()
    assert d["esperado"] == 100
    assert d["entradas"] == 0
    assert d["salidas"] == 0
    assert d["shopify"] == 0
    _cleanup("TEST-ESP-001")


def test_esperado_baseline_mas_entradas(app, db_clean):
    """baseline=100 + entrada=50 → esperado=150."""
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-ESP-002", "unidades_baseline": 100,
                  "fecha_baseline": "2026-05-01"},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/entrada",
            json={"sku": "TEST-ESP-002", "cantidad": 50,
                  "origen": "produccion", "fecha": "2026-05-02"},
            headers=csrf_headers())
    r = cs.get("/api/animus/inv-fisico/esperado/TEST-ESP-002")
    d = r.get_json()
    assert d["entradas"] == 50
    assert d["esperado"] == 150
    _cleanup("TEST-ESP-002")


def test_esperado_completo_ecuacion(app, db_clean):
    """baseline + entradas - salidas - shopify."""
    cs = _login(app, "sebastian")
    sku = "TEST-ESP-003"
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": sku, "unidades_baseline": 200,
                  "fecha_baseline": "2026-05-01"},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/entrada",
            json={"sku": sku, "cantidad": 100, "origen": "produccion",
                  "fecha": "2026-05-02"}, headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/salida",
            json={"sku": sku, "cantidad": 5, "origen": "regalo",
                  "fecha": "2026-05-03"}, headers=csrf_headers())
    # Sembrar venta Shopify directamente en movimientos
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT INTO animus_inventario_movimientos
           (sku, tipo, cantidad, fecha, origen, usuario)
           VALUES (?, 'SHOPIFY_VENTA', 30, '2026-05-04', 'shopify-sync', 'sistema')""",
        (sku,))
    conn.commit(); conn.close()
    r = cs.get(f"/api/animus/inv-fisico/esperado/{sku}")
    d = r.get_json()
    # 200 baseline + 100 entradas - 5 salidas - 30 shopify = 265
    assert d["baseline"] == 200
    assert d["entradas"] == 100
    assert d["salidas"] == 5
    assert d["shopify"] == 30
    assert d["esperado"] == 265
    _cleanup(sku)


def test_esperado_lista_todos(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-LIST-A", "unidades_baseline": 10},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-LIST-B", "unidades_baseline": 20},
            headers=csrf_headers())
    r = cs.get("/api/animus/inv-fisico/esperado")
    assert r.status_code == 200
    d = r.get_json()
    skus = {x["sku"] for x in d["items"]}
    assert "TEST-LIST-A" in skus
    assert "TEST-LIST-B" in skus
    _cleanup("TEST-LIST-A")
    _cleanup("TEST-LIST-B")


def test_movimientos_filtra_por_sku(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-MOV-001", "unidades_baseline": 0},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/entrada",
            json={"sku": "TEST-MOV-001", "cantidad": 5, "origen": "produccion"},
            headers=csrf_headers())
    r = cs.get("/api/animus/inv-fisico/movimientos?sku=TEST-MOV-001")
    assert r.status_code == 200
    movs = r.get_json()["movimientos"]
    assert len(movs) >= 1
    assert all(m["sku"] == "TEST-MOV-001" for m in movs)
    _cleanup("TEST-MOV-001")


# ── audit_log ─────────────────────────────────────────────────────

def test_baseline_audita(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-AUD-001", "unidades_baseline": 50},
            headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT accion FROM audit_log WHERE accion='ANIMUS_BASELINE_CREATE' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row is not None
    _cleanup("TEST-AUD-001")


# ── Fase 2: Conteo ciclico ────────────────────────────────────────

def test_asignar_hoy_sin_baseline_returns_empty(app, db_clean):
    """Si no hay SKUs con baseline, no hay nada que asignar."""
    cs = _login(app, "sebastian")
    # Limpiar baseline de la DB de tests
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_inventario_baseline")
    conn.execute("DELETE FROM animus_conteos_asignados WHERE fecha_asignado=date('now')")
    conn.commit(); conn.close()
    r = cs.post("/api/animus/inv-fisico/conteo/asignar-hoy",
                json={"n": 5}, headers=csrf_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert len(d.get("asignados", [])) == 0


def test_asignar_hoy_con_baselines(app, db_clean):
    cs = _login(app, "sebastian")
    # Limpiar previa
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_conteos_asignados WHERE fecha_asignado=date('now')")
    conn.commit(); conn.close()
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-CON-A", "unidades_baseline": 10},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-CON-B", "unidades_baseline": 20},
            headers=csrf_headers())
    try:
        r = cs.post("/api/animus/inv-fisico/conteo/asignar-hoy",
                    json={"n": 2}, headers=csrf_headers())
        d = r.get_json()
        assert len(d["asignados"]) >= 1
    finally:
        _cleanup("TEST-CON-A")
        _cleanup("TEST-CON-B")


def test_asignar_hoy_es_idempotente(app, db_clean):
    """Si ya hay pendientes hoy, no se duplican."""
    cs = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_conteos_asignados WHERE fecha_asignado=date('now')")
    conn.commit(); conn.close()
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-IDM-001", "unidades_baseline": 10},
            headers=csrf_headers())
    try:
        cs.post("/api/animus/inv-fisico/conteo/asignar-hoy",
                json={"n": 1}, headers=csrf_headers())
        r2 = cs.post("/api/animus/inv-fisico/conteo/asignar-hoy",
                     json={"n": 5}, headers=csrf_headers())
        d2 = r2.get_json()
        # Segunda llamada debe retornar ya_asignados_hoy
        assert d2.get("ya_asignados_hoy", 0) >= 1 or len(d2.get("asignados", [])) == 0
    finally:
        _cleanup("TEST-IDM-001")
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_conteos_asignados WHERE fecha_asignado=date('now')")
        conn.commit(); conn.close()


def test_registrar_conteo_cuadra(app, db_clean):
    """Conteo fisico = esperado · sin diferencia."""
    cs = _login(app, "sebastian")
    sku = "TEST-CUADRA"
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": sku, "unidades_baseline": 50},
            headers=csrf_headers())
    try:
        # Asignar manualmente
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cur = conn.execute(
            "INSERT INTO animus_conteos_asignados (sku, asignado_a, estado) VALUES (?, 'test', 'pendiente')",
            (sku,))
        asig_id = cur.lastrowid
        conn.commit(); conn.close()
        # Contar exacto
        r = cs.post(f"/api/animus/inv-fisico/conteo/{asig_id}/registrar",
                    json={"cantidad_fisica": 50}, headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d["diferencia"] == 0
        assert d["esperado"] == 50
        assert d["fisica"] == 50
    finally:
        _cleanup(sku)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_conteos_asignados WHERE sku=?", (sku,))
        conn.commit(); conn.close()


def test_registrar_conteo_diferencia_grande_requiere_motivo(app, db_clean):
    cs = _login(app, "sebastian")
    sku = "TEST-DIFF"
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": sku, "unidades_baseline": 50},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cur = conn.execute(
            "INSERT INTO animus_conteos_asignados (sku, asignado_a, estado) VALUES (?, 'test', 'pendiente')",
            (sku,))
        asig_id = cur.lastrowid
        conn.commit(); conn.close()
        # Diferencia grande sin motivo → 400
        r = cs.post(f"/api/animus/inv-fisico/conteo/{asig_id}/registrar",
                    json={"cantidad_fisica": 30}, headers=csrf_headers())
        assert r.status_code == 400
        # Con motivo → 200
        r2 = cs.post(f"/api/animus/inv-fisico/conteo/{asig_id}/registrar",
                     json={"cantidad_fisica": 30, "motivo_diferencia": "Daño en bodega"},
                     headers=csrf_headers())
        assert r2.status_code == 200
        d = r2.get_json()
        assert d["diferencia"] == -20
    finally:
        _cleanup(sku)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_conteos_asignados WHERE sku=?", (sku,))
        conn.commit(); conn.close()


def test_registrar_conteo_con_aplicar_ajuste(app, db_clean):
    cs = _login(app, "sebastian")
    sku = "TEST-AJUST"
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": sku, "unidades_baseline": 100},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cur = conn.execute(
            "INSERT INTO animus_conteos_asignados (sku, asignado_a, estado) VALUES (?, 'test', 'pendiente')",
            (sku,))
        asig_id = cur.lastrowid
        conn.commit(); conn.close()
        r = cs.post(f"/api/animus/inv-fisico/conteo/{asig_id}/registrar",
                    json={"cantidad_fisica": 95, "motivo_diferencia": "regalo no anotado",
                          "aplicar_ajuste": True}, headers=csrf_headers())
        assert r.status_code == 200
        # Verificar que ahora esperado matchea
        r2 = cs.get(f"/api/animus/inv-fisico/esperado/{sku}")
        d2 = r2.get_json()
        assert d2["esperado"] == 95
    finally:
        _cleanup(sku)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_conteos_asignados WHERE sku=?", (sku,))
        conn.commit(); conn.close()


def test_pendientes_conteo_endpoint(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/animus/inv-fisico/conteo/pendientes")
    assert r.status_code == 200
    assert "pendientes" in r.get_json()


def test_historial_conteo_endpoint(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/animus/inv-fisico/conteo/historial")
    assert r.status_code == 200
    d = r.get_json()
    assert "historial" in d
    assert "kpis_30d" in d


def test_sync_shopify_inv_endpoint(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/animus/inv-fisico/sync-shopify",
                json={}, headers=csrf_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert "ventas_creadas" in d


def test_sembrar_desde_shopify_endpoint(app, db_clean):
    """Endpoint sembrar baseline=0 desde SKUs Shopify."""
    cs = _login(app, "sebastian")
    # Sembrar pedido shopify de prueba
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id='TEST-SEMB-001'")
    conn.execute("DELETE FROM animus_inventario_baseline WHERE sku='TEST-SEMB-SKU'")
    conn.execute("""INSERT INTO animus_shopify_orders
        (shopify_id, nombre, total, sku_items, unidades_total, creado_en)
        VALUES ('TEST-SEMB-001', 'Test', 0, ?, 1, date('now'))""",
        ('[{"sku":"TEST-SEMB-SKU","qty":1}]',))
    conn.commit(); conn.close()
    try:
        r = cs.post("/api/animus/inv-fisico/baseline/sembrar-desde-shopify",
                    json={"dias": 30}, headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        # Debe haber creado el baseline
        assert "TEST-SEMB-SKU" in d.get("skus_creados", [])
        # Verificar que existe en DB
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT unidades_baseline FROM animus_inventario_baseline WHERE sku='TEST-SEMB-SKU'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 0
    finally:
        _cleanup("TEST-SEMB-SKU")
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id='TEST-SEMB-001'")
        conn.commit(); conn.close()


def test_sembrar_es_idempotente(app, db_clean):
    """Si SKU ya tiene baseline, no se sobreescribe."""
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-IDEM-SKU", "unidades_baseline": 50},
            headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id='TEST-IDEM-001'")
    conn.execute("""INSERT INTO animus_shopify_orders
        (shopify_id, nombre, total, sku_items, unidades_total, creado_en)
        VALUES ('TEST-IDEM-001', 'Test', 0, ?, 1, date('now'))""",
        ('[{"sku":"TEST-IDEM-SKU","qty":1}]',))
    conn.commit(); conn.close()
    try:
        r = cs.post("/api/animus/inv-fisico/baseline/sembrar-desde-shopify",
                    json={"dias": 30}, headers=csrf_headers())
        d = r.get_json()
        assert "TEST-IDEM-SKU" not in d.get("skus_creados", [])
        # Baseline original NO se tocó
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT unidades_baseline FROM animus_inventario_baseline WHERE sku='TEST-IDEM-SKU'"
        ).fetchone()
        conn.close()
        assert row[0] == 50
    finally:
        _cleanup("TEST-IDEM-SKU")
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id='TEST-IDEM-001'")
        conn.commit(); conn.close()


def test_diagnostico_endpoint(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/animus/inv-fisico/diagnostico")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("kpis", "top_problematicos", "patrones_detectados", "sin_baseline"):
        assert k in d


def test_pagina_animus_tiene_tab_inv_fisico(app, db_clean):
    """La UI debe exponer el tab nuevo + modales."""
    cs = _login(app, "sebastian")
    r = cs.get("/animus")
    body = r.get_data(as_text=True)
    assert 'data-tab="invfis"' in body
    assert 'id="tab-invfis"' in body
    assert 'id="modal-baseline"' in body
    assert 'id="modal-entrada"' in body
    assert 'id="modal-salida"' in body
    assert 'cargarInvFisico' in body
    assert 'guardarBaseline' in body
    assert 'guardarEntrada' in body
    assert 'guardarSalida' in body


def test_entrada_audita(app, db_clean):
    cs = _login(app, "sebastian")
    cs.post("/api/animus/inv-fisico/baseline",
            json={"sku": "TEST-AUD-ENT", "unidades_baseline": 0},
            headers=csrf_headers())
    cs.post("/api/animus/inv-fisico/entrada",
            json={"sku": "TEST-AUD-ENT", "cantidad": 10, "origen": "produccion"},
            headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT accion FROM audit_log WHERE accion='ANIMUS_INV_ENTRADA' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row is not None
    _cleanup("TEST-AUD-ENT")
