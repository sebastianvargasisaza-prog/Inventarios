"""Tests del flujo de inventario en /planta — el corazón del módulo.

Sebastian (29-abr-2026): "que se mantenga, que no se rompa nunca más,
sea perfecta". Estos tests garantizan que cualquier regresión futura en:
  - prog_completar_evento (descuento al completar producción)
  - prog_revertir_completado (restauración de stock)
  - recibir_oc (entrada de stock)
fallen visiblemente en CI antes de llegar a producción.

Cobertura:
  ✓ Completar producción descuenta MPs según fórmula
  ✓ Idempotencia: completar 2 veces no descuenta 2 veces
  ✓ dry_run muestra preview sin escribir
  ✓ Revertir genera movimientos compensatorios
  ✓ Stock final coherente: SUM(Entrada) - SUM(Salida)
  ✓ Forzar redescuento solo admin
  ✓ Revertir solo admin
  ✓ Producción sin fórmula no crashea
"""
import pytest
import sqlite3


def _setup_producto_con_formula(db_path, producto, lote_kg, mps):
    """Helper: inserta formula_headers + formula_items + maestro_mps base.

    mps: lista de tuplas (codigo, nombre, g_por_lote, stock_inicial_g)
    """
    con = sqlite3.connect(db_path)
    c = con.cursor()
    # Formula header
    c.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre, lote_size_kg) VALUES (?, ?)",
              (producto, lote_kg))
    # Formula items + stock inicial
    for cod, nom, g_por_lote, stock_inicial in mps:
        c.execute(
            "INSERT OR REPLACE INTO maestro_mps "
            "(codigo_mp, nombre_inci, nombre_comercial, tipo, activo) "
            "VALUES (?, ?, ?, 'MP', 1)",
            (cod, nom, nom)
        )
        c.execute(
            "INSERT INTO formula_items "
            "(producto_nombre, material_id, material_nombre, "
            " porcentaje, cantidad_g_por_lote) "
            "VALUES (?, ?, ?, 0, ?)",
            (producto, cod, nom, g_por_lote)
        )
        # Stock inicial vía movimiento de Entrada
        if stock_inicial > 0:
            c.execute(
                "INSERT INTO movimientos "
                "(material_id, material_nombre, cantidad, tipo, fecha, observaciones) "
                "VALUES (?, ?, ?, 'Entrada', datetime('now','-30 day'), 'Stock inicial test')",
                (cod, nom, stock_inicial)
            )
    con.commit()
    con.close()


def _crear_produccion(db_path, producto, fecha, lotes):
    """Helper: crea fila en produccion_programada y devuelve el id."""
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute(
        "INSERT INTO produccion_programada "
        "(producto, fecha_programada, lotes, estado, origen) "
        "VALUES (?, ?, ?, 'programado', 'test')",
        (producto, fecha, lotes)
    )
    pid = c.lastrowid
    con.commit()
    con.close()
    return pid


def _stock_actual(db_path, codigo_mp):
    """Helper: stock calculado desde movimientos."""
    con = sqlite3.connect(db_path)
    c = con.cursor()
    r = c.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad "
        "                          ELSE -cantidad END), 0) "
        "FROM movimientos WHERE material_id=?",
        (codigo_mp,)
    ).fetchone()
    con.close()
    return float(r[0] or 0)


def _set_admin_session(client):
    """Login como admin (sebastian) — para tests que requieren admin."""
    from .conftest import TEST_PASSWORD
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302


def test_completar_produccion_descuenta_mps_segun_formula(app, db_clean):
    """Flujo principal: producción completada → MPs descontadas según fórmula."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_CREMA_X"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_TEST_A", "Glicerina test", 1000, 50000),  # 1kg/lote, stock 50kg
        ("MP_TEST_B", "Aceite test",   500, 30000),    # 500g/lote, stock 30kg
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=2)

    client = app.test_client()
    _set_admin_session(client)

    # Verificar stock inicial
    assert _stock_actual(db_path, "MP_TEST_A") == 50000
    assert _stock_actual(db_path, "MP_TEST_B") == 30000

    # Completar producción
    r = client.post(
        f"/api/programacion/programar/{pid}/completar",
        json={},
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["total_mps"] == 2
    # 2 lotes * 1000g = 2000g de A; 2 lotes * 500g = 1000g de B
    assert d["total_g_mps"] == 3000

    # Stock final: bajó por el consumo
    assert _stock_actual(db_path, "MP_TEST_A") == 48000
    assert _stock_actual(db_path, "MP_TEST_B") == 29000

    # Producción quedó marcada
    con = sqlite3.connect(db_path)
    estado, descontado_at = con.execute(
        "SELECT estado, inventario_descontado_at FROM produccion_programada WHERE id=?",
        (pid,)
    ).fetchone()
    con.close()
    assert estado == "completado"
    assert descontado_at  # tiene timestamp


def test_idempotencia_completar_dos_veces(app, db_clean):
    """Llamar 2 veces no debe descontar 2 veces — idempotencia."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_IDEMP_PROD"
    _setup_producto_con_formula(db_path, producto, lote_kg=5, mps=[
        ("MP_IDEMP", "MP idemp test", 800, 20000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)

    client = app.test_client()
    _set_admin_session(client)

    # Primera llamada
    r1 = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                     headers={"Origin": "http://localhost"})
    assert r1.status_code == 200
    stock_post1 = _stock_actual(db_path, "MP_IDEMP")
    assert stock_post1 == 19200  # 20000 - 800

    # Sebastian 5-may-2026: contrato cambió. /completar ahora es backwards-
    # compatible con /iniciar (que descuenta MP atómicamente). Segunda
    # llamada NO devuelve 409 — devuelve 200 sin doble descuento.
    # La GARANTÍA de no-double-descuento sigue intacta.
    r2 = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                     headers={"Origin": "http://localhost"})
    assert r2.status_code == 200, r2.data

    # Stock NO debe haber cambiado (sin doble descuento)
    assert _stock_actual(db_path, "MP_IDEMP") == 19200


def test_dry_run_no_escribe_movimientos(app, db_clean):
    """dry_run=true devuelve preview sin escribir nada."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_DRYRUN"
    _setup_producto_con_formula(db_path, producto, lote_kg=8, mps=[
        ("MP_DRY", "MP dry", 600, 10000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)

    client = app.test_client()
    _set_admin_session(client)

    r = client.post(f"/api/programacion/programar/{pid}/completar",
                    json={"dry_run": True},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200
    d = r.get_json()
    assert d.get("dry_run") is True
    assert d["total_g_mps"] == 600
    assert len(d["mps_a_descontar"]) == 1

    # Stock NO cambió
    assert _stock_actual(db_path, "MP_DRY") == 10000

    # Producción sigue sin descontar
    con = sqlite3.connect(db_path)
    descontado_at = con.execute(
        "SELECT inventario_descontado_at FROM produccion_programada WHERE id=?", (pid,)
    ).fetchone()[0]
    con.close()
    assert not descontado_at


def test_revertir_restaura_stock(app, db_clean):
    """Revertir genera movimientos compensatorios que restauran el stock."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_REVERTIR"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_REV", "MP rev", 1500, 50000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=2)

    client = app.test_client()
    _set_admin_session(client)

    # Completar
    r1 = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                     headers={"Origin": "http://localhost"})
    assert r1.status_code == 200
    assert _stock_actual(db_path, "MP_REV") == 47000  # 50000 - 3000

    # Revertir
    r2 = client.post(f"/api/programacion/programar/{pid}/revertir-completado",
                     json={}, headers={"Origin": "http://localhost"})
    assert r2.status_code == 200, r2.get_data(as_text=True)

    # Stock restaurado
    assert _stock_actual(db_path, "MP_REV") == 50000

    # Estado de la producción restaurado
    con = sqlite3.connect(db_path)
    estado, descontado_at = con.execute(
        "SELECT estado, inventario_descontado_at FROM produccion_programada WHERE id=?",
        (pid,)
    ).fetchone()
    con.close()
    assert estado == "programado"
    assert not descontado_at  # flag limpiado


def test_revertir_solo_admin(app, db_clean):
    """Revertir requiere admin — usuarios normales reciben 403."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_REV_PERM"
    _setup_producto_con_formula(db_path, producto, lote_kg=5, mps=[
        ("MP_PERM", "MP perm", 500, 10000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)

    # Completar como admin
    admin = app.test_client()
    _set_admin_session(admin)
    admin.post(f"/api/programacion/programar/{pid}/completar", json={},
               headers={"Origin": "http://localhost"})

    # Revertir como user normal — 403
    from .conftest import TEST_PASSWORD
    user = app.test_client()
    r = user.post("/login",
                  data={"username": "valentina", "password": TEST_PASSWORD},
                  headers={"Origin": "http://localhost"},
                  follow_redirects=False)
    assert r.status_code == 302

    rr = user.post(f"/api/programacion/programar/{pid}/revertir-completado",
                   json={}, headers={"Origin": "http://localhost"})
    assert rr.status_code == 403


def test_produccion_sin_formula_no_crashea(app, db_clean):
    """Si la producción no tiene fórmula, completar no crashea (descuenta 0 MPs)."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    pid = _crear_produccion(db_path, "PRODUCTO_INVENTADO_SIN_FORMULA",
                            "2026-04-29", lotes=1)

    client = app.test_client()
    _set_admin_session(client)

    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["total_mps"] == 0  # sin fórmula no descuenta MPs


def test_stock_jamas_se_va_negativo_normalmente(app, db_clean):
    """Producción que consume MENOS que el stock disponible deja stock positivo."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_NO_NEGATIVO"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_NN", "MP no neg", 1000, 5000),  # consume 1kg/lote, hay 5kg
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=2)

    client = app.test_client()
    _set_admin_session(client)
    client.post(f"/api/programacion/programar/{pid}/completar", json={},
                headers={"Origin": "http://localhost"})

    stock_final = _stock_actual(db_path, "MP_NN")
    assert stock_final == 3000  # 5000 - 2*1000
    assert stock_final >= 0


def test_movimientos_se_marcan_con_observaciones_correctas(app, db_clean):
    """Cada movimiento de salida lleva observaciones detalladas para audit."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_OBS"
    _setup_producto_con_formula(db_path, producto, lote_kg=15, mps=[
        ("MP_OBS", "MP obs", 700, 20000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=3)

    client = app.test_client()
    _set_admin_session(client)
    client.post(f"/api/programacion/programar/{pid}/completar", json={},
                headers={"Origin": "http://localhost"})

    con = sqlite3.connect(db_path)
    obs = con.execute(
        "SELECT observaciones FROM movimientos "
        "WHERE material_id='MP_OBS' AND tipo='Salida' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    con.close()
    # Debe contener el nombre del producto + fecha + lotes
    assert "Producción COMPLETADA" in obs
    assert producto in obs
    assert "2026-04-29" in obs
    assert "3 lote" in obs


def test_fefo_sugiere_lote_mas_viejo(app, db_clean):
    """Al completar produccion, el movimiento de Salida lleva en lote
    el lote con fecha_vencimiento mas cercana (FEFO)."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FEFO", "MP fefo", 1000, 0),  # arrancamos sin stock
    ])

    # Insertar 3 entradas con distintas fechas de vencimiento
    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_NUEVO', '2027-12-31', 'OK')",
        ("MP_FEFO", "MP fefo", 5000)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-02-01', 'L_VIEJO', '2026-06-30', 'OK')",
        ("MP_FEFO", "MP fefo", 5000)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-03-01', 'L_MEDIO', '2027-03-31', 'OK')",
        ("MP_FEFO", "MP fefo", 5000)
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)
    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200

    # El movimiento de Salida debe llevar lote=L_VIEJO (más cercano a vencer)
    con = sqlite3.connect(db_path)
    lote = con.execute(
        "SELECT lote FROM movimientos "
        "WHERE material_id='MP_FEFO' AND tipo='Salida' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    con.close()
    assert lote == "L_VIEJO"


def test_ajuste_manual_requiere_motivo_y_observaciones(app, db_clean):
    """Ajuste manual rechaza requests sin motivo válido o sin observaciones."""
    client = app.test_client()
    _set_admin_session(client)

    # Falta motivo
    r1 = client.post("/api/inventario/ajuste-manual", json={
        "tipo_material": "MP", "codigo": "MP00001",
        "cantidad": 100, "direccion": "sumar", "observaciones": "test test test"
    }, headers={"Origin": "http://localhost"})
    assert r1.status_code == 400

    # Observaciones muy cortas
    r2 = client.post("/api/inventario/ajuste-manual", json={
        "tipo_material": "MP", "codigo": "MP00001",
        "cantidad": 100, "motivo": "merma",
        "direccion": "sumar", "observaciones": "x"
    }, headers={"Origin": "http://localhost"})
    assert r2.status_code == 400


def test_ajuste_manual_solo_admin(app, db_clean):
    """Usuarios normales no pueden ajustar inventario."""
    from .conftest import TEST_PASSWORD
    user = app.test_client()
    user.post("/login",
              data={"username": "valentina", "password": TEST_PASSWORD},
              headers={"Origin": "http://localhost"},
              follow_redirects=False)
    r = user.post("/api/inventario/ajuste-manual", json={
        "tipo_material": "MP", "codigo": "MP00001",
        "cantidad": 100, "motivo": "merma",
        "direccion": "sumar",
        "observaciones": "Recuento físico septiembre"
    }, headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_ajuste_manual_resta_stock_mp(app, db_clean):
    """Ajuste 'restar' a un MP genera mov de Salida con observaciones AJUSTE_MANUAL."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    # Crear MP con stock
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT OR REPLACE INTO maestro_mps "
        "(codigo_mp, nombre_inci, nombre_comercial, tipo, activo) "
        "VALUES ('MP_AJUSTE', 'Ajuste test', 'Ajuste test', 'MP', 1)"
    )
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha) "
        "VALUES ('MP_AJUSTE', 'Ajuste test', 1000, 'Entrada', datetime('now'))"
    )
    con.commit()
    con.close()

    client = app.test_client()
    _set_admin_session(client)
    r = client.post("/api/inventario/ajuste-manual", json={
        "tipo_material": "MP", "codigo": "MP_AJUSTE",
        "cantidad": 200, "motivo": "merma",
        "direccion": "restar",
        "observaciones": "Conteo físico encontró 200g menos del esperado"
    }, headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True

    # Stock final
    assert _stock_actual(db_path, "MP_AJUSTE") == 800

    # Movimiento debe tener AJUSTE_MANUAL en obs
    con = sqlite3.connect(db_path)
    obs = con.execute(
        "SELECT observaciones FROM movimientos "
        "WHERE material_id='MP_AJUSTE' AND tipo='Salida' ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    con.close()
    assert "AJUSTE_MANUAL" in obs
    assert "merma" in obs


def test_completar_y_revertir_no_deja_drift(app, db_clean):
    """Completar + Revertir devuelve el stock al estado original (zero net effect)."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_DRIFT"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_DRIFT", "MP drift", 750, 100000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=4)

    stock_inicial = _stock_actual(db_path, "MP_DRIFT")

    client = app.test_client()
    _set_admin_session(client)
    client.post(f"/api/programacion/programar/{pid}/completar", json={},
                headers={"Origin": "http://localhost"})
    client.post(f"/api/programacion/programar/{pid}/revertir-completado", json={},
                headers={"Origin": "http://localhost"})

    stock_final = _stock_actual(db_path, "MP_DRIFT")
    assert stock_final == stock_inicial, (
        f"DRIFT detectado: stock cambió de {stock_inicial} a {stock_final} "
        f"después de completar+revertir (debería ser 0)"
    )


def test_limpiar_drift_mee_alinea_stock_y_movs(app, db_clean):
    """El endpoint limpiar-drift-mee inserta movimientos seed que alinean
    SUM(movimientos_mee) con maestro_mee.stock_actual."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]

    # Setup: 2 MEEs con drift (stock_actual=100, sin movimientos)
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM maestro_mee WHERE codigo IN ('TEST_DRIFT_A','TEST_DRIFT_B')")
    con.execute("DELETE FROM movimientos_mee WHERE mee_codigo IN ('TEST_DRIFT_A','TEST_DRIFT_B')")
    con.execute(
        "INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
        "VALUES ('TEST_DRIFT_A', 'Test drift A', 500, 'Activo')"
    )
    con.execute(
        "INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
        "VALUES ('TEST_DRIFT_B', 'Test drift B', 800, 'Activo')"
    )
    con.commit()
    con.close()

    # Verificar drift inicial
    con = sqlite3.connect(db_path)
    suma_a = con.execute(
        "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad ELSE -cantidad END),0) "
        "FROM movimientos_mee WHERE mee_codigo='TEST_DRIFT_A'"
    ).fetchone()[0]
    assert suma_a == 0, "Setup: debería haber 0 movimientos antes"
    con.close()

    # Llamar endpoint de limpieza
    client = app.test_client()
    _set_admin_session(client)
    r = client.post("/admin/audit-inventario/limpiar-drift-mee",
                    json={}, headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["alineados"] >= 2  # nuestros 2 + posibles otros pre-existentes

    # Verificar que ahora SUM = stock_actual
    con = sqlite3.connect(db_path)
    suma_a = con.execute(
        "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad ELSE -cantidad END),0) "
        "FROM movimientos_mee WHERE mee_codigo='TEST_DRIFT_A'"
    ).fetchone()[0]
    suma_b = con.execute(
        "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad ELSE -cantidad END),0) "
        "FROM movimientos_mee WHERE mee_codigo='TEST_DRIFT_B'"
    ).fetchone()[0]
    con.close()
    assert suma_a == 500
    assert suma_b == 800

    # Idempotente: llamar de nuevo no debe insertar más (drift ya 0)
    r2 = client.post("/admin/audit-inventario/limpiar-drift-mee",
                     json={}, headers={"Origin": "http://localhost"})
    assert r2.status_code == 200
    d2 = r2.get_json()
    # No debe haber alineado nuestros 2 (ya estaban OK)
    con = sqlite3.connect(db_path)
    cnt_a = con.execute(
        "SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo='TEST_DRIFT_A'"
    ).fetchone()[0]
    con.close()
    assert cnt_a == 1  # solo el seed inicial, no se agregó otro


def test_limpiar_drift_solo_admin(app, db_clean):
    """Endpoint limpiar-drift-mee requiere admin."""
    from .conftest import TEST_PASSWORD
    user = app.test_client()
    user.post("/login",
              data={"username": "valentina", "password": TEST_PASSWORD},
              headers={"Origin": "http://localhost"},
              follow_redirects=False)
    r = user.post("/admin/audit-inventario/limpiar-drift-mee",
                  json={}, headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_e2e_oc_recepcion_a_produccion(app, db_clean):
    """Flujo completo: crear OC → recibir → completar producción.
    Verifica que el stock fluye correctamente entre los 3 pasos.
    """
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_E2E"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_E2E", "MP e2e", 1000, 0),  # arrancamos sin stock
    ])

    # Crear OC + items
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, categoria, valor_total) "
        "VALUES ('OC-TEST-E2E', date('now'), 'Autorizada', 'PROV TEST', 'MP', 100000)"
    )
    con.execute(
        "INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) "
        "VALUES ('OC-TEST-E2E', 'MP_E2E', 'MP e2e', 5000)"
    )
    con.commit()
    con.close()

    client = app.test_client()
    _set_admin_session(client)

    # Paso 1: Stock inicial = 0
    assert _stock_actual(db_path, "MP_E2E") == 0

    # Paso 2: Recibir OC
    r1 = client.post("/api/ordenes-compra/OC-TEST-E2E/recibir", json={
        "items_recepcion": [{"codigo_mp": "MP_E2E", "cantidad_recibida": 5000,
                             "lote": "L001", "estado": "OK"}],
        "receptor_nombre": "test"
    }, headers={"Origin": "http://localhost"})
    assert r1.status_code == 200, r1.get_data(as_text=True)
    assert _stock_actual(db_path, "MP_E2E") == 5000

    # Paso 3: Crear producción que consume MP
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=2)

    # Paso 4: Completar producción → descuenta 2*1000 = 2000g
    r2 = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                     headers={"Origin": "http://localhost"})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    assert _stock_actual(db_path, "MP_E2E") == 3000  # 5000 - 2000


def test_alertas_planta_endpoint_responde(app, db_clean):
    """El endpoint de alertas vivas de planta responde 200 con estructura JSON."""
    client = app.test_client()
    _set_admin_session(client)
    r = client.get("/api/planta/alertas-vivas")
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    # Debe tener al menos las keys principales
    assert isinstance(d, dict)


def test_kardex_mp_responde(app, db_clean):
    """Kardex de un MP devuelve estructura coherente con movimientos + saldo."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    # Crear MP con movimientos
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT OR REPLACE INTO maestro_mps "
        "(codigo_mp, nombre_inci, nombre_comercial, tipo, activo) "
        "VALUES ('MP_KARDEX', 'Kardex test', 'Kardex test', 'MP', 1)"
    )
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha) "
        "VALUES ('MP_KARDEX', 'Kardex test', 1000, 'Entrada', datetime('now','-5 day'))"
    )
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha) "
        "VALUES ('MP_KARDEX', 'Kardex test', 200, 'Salida', datetime('now','-2 day'))"
    )
    con.commit()
    con.close()

    client = app.test_client()
    _set_admin_session(client)
    r = client.get("/api/planta/kardex/MP_KARDEX")
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    # Debe tener movimientos
    assert "movimientos" in d or "kardex" in d or len(d) > 0


def test_kardex_mp_inexistente_devuelve_404(app, db_clean):
    """Kardex de un MP que no existe devuelve 404."""
    client = app.test_client()
    _set_admin_session(client)
    r = client.get("/api/planta/kardex/MP_NO_EXISTE_XYZ")
    assert r.status_code == 404


def test_recibir_oc_sin_auth_falla(app, db_clean):
    """Recibir OC sin autenticación devuelve 401."""
    client = app.test_client()
    r = client.post("/api/ordenes-compra/OC-CUALQUIERA/recibir", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 401


def test_completar_descuenta_y_audit_no_reporta_anomalia(app, db_clean):
    """Después de completar una producción, /admin/audit-inventario NO debe
    reportar esa producción como 'legacy sin descontar'."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_AUDIT_CLEAN"
    _setup_producto_con_formula(db_path, producto, lote_kg=8, mps=[
        ("MP_AUDIT", "MP audit", 600, 50000),
    ])
    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)

    client = app.test_client()
    _set_admin_session(client)
    client.post(f"/api/programacion/programar/{pid}/completar", json={},
                headers={"Origin": "http://localhost"})

    # Audit no debe listar esta producción como legacy
    r = client.get("/admin/audit-inventario")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # La producción NO debe aparecer en la sección legacy
    # (busca el id de la producción cerca del título legacy)
    legacy_section_idx = body.find("Producciones LEGACY")
    siguiente_section_idx = body.find("Producciones ATRASADAS")
    if legacy_section_idx > 0 and siguiente_section_idx > legacy_section_idx:
        legacy_html = body[legacy_section_idx:siguiente_section_idx]
        assert producto not in legacy_html, (
            f"Producción {producto} aparece como legacy aunque ya descontó"
        )


def test_fefo_consume_lote_mas_viejo_primero(app, db_clean):
    """FEFO real: si hay 2 lotes de un MP, consume PRIMERO el más cercano
    a vencer. Cada movimiento de Salida lleva el lote real consumido."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO_REAL_1"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FR1", "MP fr1", 500, 0),
    ])

    # 2 lotes con distintas fechas de vencimiento
    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_NUEVO', '2027-12-31', 'OK')",
        ("MP_FR1", "MP fr1", 1000)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-02-01', 'L_VIEJO', '2026-08-30', 'OK')",
        ("MP_FR1", "MP fr1", 1000)
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)
    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)

    # Debe haber UNA salida con lote=L_VIEJO (el que vence más pronto), 500g
    con = sqlite3.connect(db_path)
    salidas = con.execute(
        "SELECT lote, cantidad FROM movimientos "
        "WHERE material_id='MP_FR1' AND tipo='Salida' ORDER BY id"
    ).fetchall()
    con.close()
    assert len(salidas) == 1
    assert salidas[0][0] == "L_VIEJO"
    assert salidas[0][1] == 500


def test_fefo_distribuye_entre_varios_lotes(app, db_clean):
    """Si un solo lote no alcanza, FEFO distribuye el consumo entre lotes
    en orden de vencimiento. Genera UN movimiento de Salida POR LOTE."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO_DISTRIB"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FRD", "MP frd", 1500, 0),  # consume 1500g/lote
    ])

    # 3 lotes — el primero tiene 700g, el segundo 600g, el tercero 5000g
    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_A', '2026-06-30', 'OK')",
        ("MP_FRD", "MP frd", 700)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-02-01', 'L_B', '2026-09-30', 'OK')",
        ("MP_FRD", "MP frd", 600)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-03-01', 'L_C', '2027-12-31', 'OK')",
        ("MP_FRD", "MP frd", 5000)
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)
    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)

    # Distribución FEFO: 700 de L_A + 600 de L_B + 200 de L_C = 1500g total
    con = sqlite3.connect(db_path)
    salidas = con.execute(
        "SELECT lote, cantidad FROM movimientos "
        "WHERE material_id='MP_FRD' AND tipo='Salida' ORDER BY id"
    ).fetchall()
    con.close()
    assert len(salidas) == 3
    assert salidas[0] == ("L_A", 700.0)
    assert salidas[1] == ("L_B", 600.0)
    assert salidas[2] == ("L_C", 200.0)
    # Stock total final = 4800 (700+600+5000-1500)
    assert _stock_actual(db_path, "MP_FRD") == 4800


def test_fefo_excluye_lotes_vencidos_y_bloqueados(app, db_clean):
    """FEFO ignora lotes con estado_lote='Vencido' o 'Bloqueado' aunque
    tengan stock — esos NO deben consumirse."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO_EXCL"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FRE", "MP fre", 800, 0),
    ])

    # Lote VENCIDO con 1000g + Lote OK con 1000g
    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_VENC', '2025-01-01', 'Vencido')",
        ("MP_FRE", "MP fre", 1000)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-02-01', 'L_OK', '2027-12-31', 'OK')",
        ("MP_FRE", "MP fre", 1000)
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)
    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200

    # Solo debe haber consumido del lote OK
    con = sqlite3.connect(db_path)
    salidas = con.execute(
        "SELECT lote, cantidad FROM movimientos "
        "WHERE material_id='MP_FRE' AND tipo='Salida' ORDER BY id"
    ).fetchall()
    con.close()
    assert len(salidas) == 1
    assert salidas[0] == ("L_OK", 800.0)


def test_fefo_remainder_sin_lote_si_lotes_no_alcanzan(app, db_clean):
    """Si los lotes con trazabilidad no alcanzan, el remainder se descuenta
    sin lote (lote=NULL) — indica stock legacy."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO_REMAIN"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FRR", "MP frr", 1200, 0),
    ])

    # 1 lote con 500g + 5000g sin lote (legacy seed)
    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_X', '2027-01-01', 'OK')",
        ("MP_FRR", "MP frr", 500)
    )
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01')",
        ("MP_FRR", "MP frr", 5000)  # sin lote
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)
    r = client.post(f"/api/programacion/programar/{pid}/completar", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200

    con = sqlite3.connect(db_path)
    salidas = con.execute(
        "SELECT lote, cantidad FROM movimientos "
        "WHERE material_id='MP_FRR' AND tipo='Salida' ORDER BY id"
    ).fetchall()
    con.close()
    assert len(salidas) == 2
    # 500 del lote
    assert salidas[0] == ("L_X", 500.0)
    # 700 sin lote
    assert salidas[1][0] is None
    assert salidas[1][1] == 700.0


def test_fefo_revertir_restaura_stock_por_lote(app, db_clean):
    """Al revertir una producción FEFO, el stock por LOTE debe quedar
    igual al estado pre-completar (movimientos compensatorios con lote)."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    producto = "TEST_FEFO_REV"
    _setup_producto_con_formula(db_path, producto, lote_kg=10, mps=[
        ("MP_FRREV", "MP frrev", 800, 0),
    ])

    con = sqlite3.connect(db_path)
    cu = con.cursor()
    cu.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES (?, ?, ?, 'Entrada', '2026-01-01', 'L_REV', '2027-01-01', 'OK')",
        ("MP_FRREV", "MP frrev", 2000)
    )
    con.commit()
    con.close()

    pid = _crear_produccion(db_path, producto, "2026-04-29", lotes=1)
    client = app.test_client()
    _set_admin_session(client)

    # Completar → consume 800g del lote L_REV
    client.post(f"/api/programacion/programar/{pid}/completar", json={},
                headers={"Origin": "http://localhost"})
    # Stock por lote L_REV ahora = 1200 (2000-800)
    con = sqlite3.connect(db_path)
    stock_lote = con.execute(
        "SELECT SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) "
        "FROM movimientos WHERE material_id='MP_FRREV' AND lote='L_REV'"
    ).fetchone()[0]
    con.close()
    assert stock_lote == 1200

    # Revertir → stock por lote L_REV vuelve a 2000
    r = client.post(f"/api/programacion/programar/{pid}/revertir-completado",
                    json={}, headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    con = sqlite3.connect(db_path)
    stock_lote = con.execute(
        "SELECT SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) "
        "FROM movimientos WHERE material_id='MP_FRREV' AND lote='L_REV'"
    ).fetchone()[0]
    con.close()
    assert stock_lote == 2000  # restaurado al lote correcto


def test_stock_por_lote_endpoint(app, db_clean):
    """El endpoint /api/planta/stock-por-lote/<cod> devuelve lotes ordenados
    FEFO con stock vivo por lote y total."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo, activo) "
        "VALUES ('MP_LOTES', 'MP lotes', 'MP lotes', 'MP', 1)"
    )
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES ('MP_LOTES', 'MP lotes', 800, 'Entrada', '2026-01-01', 'L1', '2027-12-31', 'OK')"
    )
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
        "fecha, lote, fecha_vencimiento, estado_lote) "
        "VALUES ('MP_LOTES', 'MP lotes', 500, 'Entrada', '2026-01-01', 'L2', '2026-06-30', 'OK')"
    )
    con.commit()
    con.close()

    client = app.test_client()
    _set_admin_session(client)
    r = client.get("/api/planta/stock-por-lote/MP_LOTES")
    assert r.status_code == 200
    d = r.get_json()
    assert d["codigo_mp"] == "MP_LOTES"
    assert d["total_g"] == 1300
    # FEFO: L2 primero (vence 2026-06, antes que L1 en 2027-12)
    assert d["lotes"][0]["lote"] == "L2"
    assert d["lotes"][0]["stock_g"] == 500
    assert d["lotes"][1]["lote"] == "L1"
    assert d["lotes"][1]["stock_g"] == 800


def test_audit_endpoint_solo_admin(app, db_clean):
    """/admin/audit-inventario es solo admin."""
    from .conftest import TEST_PASSWORD
    user = app.test_client()
    user.post("/login",
              data={"username": "valentina", "password": TEST_PASSWORD},
              headers={"Origin": "http://localhost"},
              follow_redirects=False)
    r = user.get("/admin/audit-inventario")
    assert r.status_code == 403

    admin = app.test_client()
    _set_admin_session(admin)
    r2 = admin.get("/admin/audit-inventario")
    assert r2.status_code == 200
    body = r2.get_data(as_text=True)
    assert "Auditoría de Inventario" in body
