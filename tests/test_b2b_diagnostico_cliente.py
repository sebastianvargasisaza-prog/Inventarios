"""Read-only · /api/pedidos-b2b/diagnostico-cliente · cobertura + duplicados B2B."""
import os
import sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def test_diagnostico_cliente_b2b(app, db_clean):
    PROD = "PROD-KELLY-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM pedidos_b2b WHERE cliente_nombre LIKE 'Kelly%'")
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    # Pedido B2B de Kelly
    cur = db.execute(
        """INSERT INTO pedidos_b2b
           (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
            ml_unidad, estado, creado_por)
           VALUES ('CLI-KELLY','Kelly Guerra', ?, 150, 30, 'confirmado', 'sebastian')""",
        (PROD,),
    )
    pid = cur.lastrowid
    # Lote futuro activo del producto + vinculación
    cur2 = db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes,
            observaciones)
           VALUES (?, date('now','+12 days'), 10, 'programado', 'eos_plan', 1,
                   '+4.5kg B2B Kelly Guerra (pedido #' || ? || ')')""",
        (PROD, pid),
    )
    lote_id = cur2.lastrowid
    db.execute(
        """INSERT INTO pedidos_b2b_lote
           (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte,
            ml_unidad, envase_codigo, modo, cliente_nombre)
           VALUES (?, ?, 4.5, 150, 30, '', 'sumado_a_lote_canonico', 'Kelly Guerra')""",
        (pid, lote_id),
    )
    db.commit()
    db.close()

    r = c.get("/api/pedidos-b2b/diagnostico-cliente?cliente=Kelly")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True
    assert d["n_pedidos"] >= 1, d
    fila = next((p for p in d["pedidos"] if p["producto"] == PROD), None)
    assert fila is not None, d
    assert fila["vinculado"] is True, fila
    assert fila["hay_lote_calendario"] >= 1, fila
    assert len(fila["lotes_vinculados"]) == 1, fila
    assert fila["lotes_vinculados"][0]["lote_id"] == lote_id, fila


def test_diagnostico_cliente_requiere_param(app, db_clean):
    c = _login_as(app, "sebastian")
    r = c.get("/api/pedidos-b2b/diagnostico-cliente")
    assert r.status_code == 400
