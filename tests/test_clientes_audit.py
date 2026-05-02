"""Tests CERO SESGO · clientes · audit_log + guards en mutations.

Cubre:
- handle_clientes POST · audit + validar descuento_pct rango
- handle_cliente_detalle PUT · audit + validar descuento_pct
- handle_pedidos POST · audit + validar cliente_id existe
- handle_pedido_detalle PATCH · audit + validate_money en monto_pagado
- handle_pedido_detalle DELETE · guard pedidos despachados/con-despachos
- handle_stock_pt POST · validar precio + idempotency duplicado
- handle_despachos POST · validar cliente_id + numero_pedido + audit
- patch_aliado · audit
"""
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _last_audit(accion=None, registro_id=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    where, params = [], []
    if accion: where.append("accion=?"); params.append(accion)
    if registro_id is not None: where.append("registro_id=?"); params.append(str(registro_id))
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ─── Clientes ────────────────────────────────────────────────────────

def test_crear_cliente_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/clientes",
               json={"nombre": "Cliente Audit Test", "tipo": "Distribuidor",
                     "empresa": "ANIMUS"},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    cid = data['id']
    audit = _last_audit(accion="CREAR_CLIENTE", registro_id=cid)
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM clientes WHERE id=?", (cid,))
    conn.commit(); conn.close()


def test_crear_cliente_descuento_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/clientes",
               json={"nombre": "Test", "descuento_pct": 150},
               headers=csrf_headers())
    assert r.status_code == 400
    r = c.post("/api/clientes",
               json={"nombre": "Test", "descuento_pct": -10},
               headers=csrf_headers())
    assert r.status_code == 400


def test_actualizar_cliente_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/clientes",
               json={"nombre": "CLI-UPD-T"}, headers=csrf_headers())
    cid = r.get_json()['id']
    try:
        r = c.put(f"/api/clientes/{cid}",
                  json={"nombre": "CLI-UPD-T modificado", "descuento_pct": 5},
                  headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_CLIENTE", registro_id=cid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=?", (cid,))
        conn.commit(); conn.close()


# ─── Pedidos ─────────────────────────────────────────────────────────

def test_crear_pedido_cliente_inexistente_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/pedidos",
               json={"cliente_id": 999999, "items": []},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_pedido_audita(app, db_clean):
    c = _login(app, "sebastian")
    # Setup cliente
    r = c.post("/api/clientes", json={"nombre": "CLI-PED-T"}, headers=csrf_headers())
    cid = r.get_json()['id']
    try:
        r = c.post("/api/pedidos",
                   json={"cliente_id": cid,
                         "items": [{"sku": "TEST-1", "cantidad": 5,
                                    "precio_unitario": 100000, "subtotal": 500000}]},
                   headers=csrf_headers())
        assert r.status_code == 201
        numero = r.get_json()['numero']
        audit = _last_audit(accion="CREAR_PEDIDO", registro_id=numero)
        assert audit is not None
        # cleanup pedido
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM pedidos WHERE numero=?", (numero,))
        conn.execute("DELETE FROM pedidos_items WHERE numero_pedido=?", (numero,))
        conn.commit(); conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_eliminar_pedido_despachado_409(app, db_clean):
    """No se puede eliminar pedido en estado Despachado (trazabilidad)."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9001, 'CLI-DEL', 'Del Test', 1)")
    conn.execute("""INSERT INTO pedidos (numero, cliente_id, fecha, estado, valor_total)
                    VALUES ('PED-DEL-T', 9001, datetime('now'), 'Despachado', 100000)""")
    conn.commit(); conn.close()
    try:
        r = c.delete("/api/pedidos/PED-DEL-T", headers=csrf_headers())
        assert r.status_code == 409
        d = r.get_json()
        assert d.get('codigo') == 'PEDIDO_DESPACHADO_NO_ELIMINABLE'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM pedidos WHERE numero='PED-DEL-T'")
        conn.execute("DELETE FROM clientes WHERE id=9001")
        conn.commit(); conn.close()


def test_eliminar_pedido_con_despachos_409(app, db_clean):
    """Pedido con despachos asociados no se puede eliminar."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9002, 'CLI-DSP', 'Dsp Test', 1)")
    conn.execute("""INSERT INTO pedidos (numero, cliente_id, fecha, estado, valor_total)
                    VALUES ('PED-DSP-T', 9002, datetime('now'), 'Confirmado', 50000)""")
    conn.execute("""INSERT INTO despachos (numero, numero_pedido, cliente_id, fecha, estado)
                    VALUES ('DSP-T1', 'PED-DSP-T', 9002, datetime('now'), 'Completado')""")
    conn.commit(); conn.close()
    try:
        r = c.delete("/api/pedidos/PED-DSP-T", headers=csrf_headers())
        assert r.status_code == 409
        d = r.get_json()
        assert d.get('codigo') == 'PEDIDO_CON_DESPACHOS'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM despachos WHERE numero='DSP-T1'")
        conn.execute("DELETE FROM pedidos WHERE numero='PED-DSP-T'")
        conn.execute("DELETE FROM clientes WHERE id=9002")
        conn.commit(); conn.close()


def test_actualizar_pedido_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9003, 'CLI-UPD-P', 'Upd Test', 1)")
    conn.execute("""INSERT INTO pedidos (numero, cliente_id, fecha, estado, valor_total)
                    VALUES ('PED-UPD-T', 9003, datetime('now'), 'Confirmado', 100000)""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/pedidos/PED-UPD-T",
                    json={"monto_pagado": 50000, "estado_pago": "Parcial"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_PEDIDO", registro_id="PED-UPD-T")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM pedidos WHERE numero='PED-UPD-T'")
        conn.execute("DELETE FROM clientes WHERE id=9003")
        conn.commit(); conn.close()


def test_actualizar_pedido_monto_pagado_negativo_400(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9004, 'CLI', 'X', 1)")
    conn.execute("""INSERT INTO pedidos (numero, cliente_id, fecha, estado, valor_total)
                    VALUES ('PED-NEG-T', 9004, datetime('now'), 'Confirmado', 100000)""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/pedidos/PED-NEG-T",
                    json={"monto_pagado": -1000}, headers=csrf_headers())
        assert r.status_code == 400
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM pedidos WHERE numero='PED-NEG-T'")
        conn.execute("DELETE FROM clientes WHERE id=9004")
        conn.commit(); conn.close()


# ─── Stock PT ───────────────────────────────────────────────────────

def test_crear_stock_pt_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/stock-pt",
               json={"sku": "SKU-PT-T1", "lote_produccion": "LOTE-PT-T1",
                     "unidades_inicial": 100, "precio_base": 50000},
               headers=csrf_headers())
    assert r.status_code == 201, r.data
    spt_id = r.get_json()['id']
    audit = _last_audit(accion="CREAR_STOCK_PT")
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM stock_pt WHERE id=?", (spt_id,))
    conn.commit(); conn.close()


def test_stock_pt_duplicado_409(app, db_clean):
    """Mismo SKU + lote_produccion no debe duplicarse."""
    c = _login(app, "sebastian")
    r1 = c.post("/api/stock-pt",
                json={"sku": "SKU-DUP", "lote_produccion": "L-DUP",
                      "unidades_inicial": 50, "precio_base": 1000},
                headers=csrf_headers())
    assert r1.status_code == 201
    spt_id = r1.get_json()['id']
    try:
        r2 = c.post("/api/stock-pt",
                    json={"sku": "SKU-DUP", "lote_produccion": "L-DUP",
                          "unidades_inicial": 50, "precio_base": 1000},
                    headers=csrf_headers())
        assert r2.status_code == 409
        d = r2.get_json()
        assert d.get('codigo') == 'STOCK_PT_DUPLICADO'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM stock_pt WHERE sku='SKU-DUP'")
        conn.commit(); conn.close()


def test_stock_pt_unidades_invalidas_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/stock-pt",
               json={"sku": "SKU-X", "unidades_inicial": 0},
               headers=csrf_headers())
    assert r.status_code == 400


# ─── Despachos ──────────────────────────────────────────────────────

def test_crear_despacho_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9005, 'CLI-DSP', 'Dsp', 1)")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/despachos",
                   json={"cliente_id": 9005,
                         "items": [{"sku": "X", "cantidad": 1, "precio_unitario": 1000}]},
                   headers=csrf_headers())
        assert r.status_code == 201
        numero = r.get_json()['numero']
        audit = _last_audit(accion="CREAR_DESPACHO", registro_id=numero)
        assert audit is not None
        # cleanup
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM despachos_items WHERE numero_despacho=?", (numero,))
        conn.execute("DELETE FROM despachos WHERE numero=?", (numero,))
        conn.commit(); conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=9005")
        conn.commit(); conn.close()


def test_despacho_cliente_inexistente_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/despachos",
               json={"cliente_id": 999999, "items": []},
               headers=csrf_headers())
    assert r.status_code == 400


def test_despacho_pedido_inexistente_400(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO clientes (id, codigo, nombre, activo) VALUES (9006, 'CLI', 'X', 1)")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/despachos",
                   json={"cliente_id": 9006, "numero_pedido": "PED-NO-EXISTE",
                         "items": []},
                   headers=csrf_headers())
        assert r.status_code == 400
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=9006")
        conn.commit(); conn.close()


# ─── Aliados ────────────────────────────────────────────────────────

def test_patch_aliado_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/clientes", json={"nombre": "ALI-T"}, headers=csrf_headers())
    cid = r.get_json()['id']
    try:
        r = c.patch(f"/api/aliados/{cid}",
                    json={"semaforo": "amarillo", "nivel_aliado": "Estratégico"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_ALIADO", registro_id=cid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=?", (cid,))
        conn.commit(); conn.close()
