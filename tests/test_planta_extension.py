"""Tests Sprints 2, 3, 4: tipo_material, alertas vivas, kardex FIFO."""
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luis"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


# ═══ Sprint 2: tipo_material ════════════════════════════════════════════════


def test_maestro_mps_supports_tipo_material(app, db_clean):
    """POST /api/maestro-mps acepta tipo_material y lo guarda."""
    c = _login(app, "luis")  # planta puede crear MPs
    r = c.post("/api/maestro-mps",
               json={"codigo_mp": "ENV001", "nombre_inci": "frasco vidrio",
                     "nombre_comercial": "Frasco 30ml",
                     "tipo_material": "Envase Primario",
                     "stock_minimo": 100},
               headers=csrf_headers())
    assert r.status_code == 201
    assert r.get_json().get("tipo_material") == "Envase Primario"


def test_maestro_mps_filter_by_tipo_material(app, db_clean):
    """GET con ?tipo_material=Empaque filtra correctamente."""
    c = _login(app, "luis")
    # Crear 2 MPs de distinto tipo
    c.post("/api/maestro-mps",
           json={"codigo_mp": "MP_T1", "tipo_material": "MP",
                 "nombre_comercial": "MP test"},
           headers=csrf_headers())
    c.post("/api/maestro-mps",
           json={"codigo_mp": "EMP_T1", "tipo_material": "Empaque",
                 "nombre_comercial": "Caja test"},
           headers=csrf_headers())

    # Filter Empaque
    r = c.get("/api/maestro-mps?tipo_material=Empaque")
    assert r.status_code == 200
    items = r.get_json()["mps"]
    codigos = [m["codigo_mp"] for m in items]
    assert "EMP_T1" in codigos
    assert "MP_T1" not in codigos


def test_maestro_mps_invalid_tipo_defaults_to_mp(app, db_clean):
    """Tipo inválido se reemplaza por 'MP' (no rompe)."""
    c = _login(app, "luis")
    r = c.post("/api/maestro-mps",
               json={"codigo_mp": "MP_INVALID_TIPO",
                     "tipo_material": "TIPO_INEXISTENTE",
                     "nombre_comercial": "Test"},
               headers=csrf_headers())
    assert r.status_code == 201
    assert r.get_json().get("tipo_material") == "MP"


def test_conteo_estanterias_filter_by_tipo(admin_client, db_clean):
    """Endpoint de estanterías acepta filtro tipo_material."""
    r = admin_client.get("/api/conteo/estanterias?tipo_material=Empaque")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_conteo_materiales_returns_tipo_material(admin_client, db_clean):
    """Endpoint conteo/materiales incluye tipo_material en cada item."""
    r = admin_client.get("/api/conteo/materiales")
    assert r.status_code == 200
    items = r.get_json()
    if items:  # Si hay datos
        assert "tipo_material" in items[0]


# ═══ Sprint 3: alertas vivas ════════════════════════════════════════════════


def test_alertas_vivas_endpoint_works(admin_client, db_clean):
    """El endpoint responde y tiene estructura esperada."""
    r = admin_client.get("/api/planta/alertas-vivas")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("vencimientos", "stock_bajo", "discrepancias",
                "cuarentena_extendida", "total", "severidad_max"):
        assert key in data, f"Falta key '{key}'"
    assert data["severidad_max"] in ("ok", "medio", "alto", "critico")


def test_alertas_vivas_requires_auth(client, db_clean):
    r = client.get("/api/planta/alertas-vivas")
    assert r.status_code == 401


def test_alertas_vivas_open_to_any_authenticated(app, db_clean):
    """Lectura abierta a cualquier user logueado."""
    c = _login(app, "felipe")  # marketing
    r = c.get("/api/planta/alertas-vivas")
    assert r.status_code == 200


def test_alertas_vivas_detects_low_stock(app, db_clean):
    """Si hay MP con stock < min_stock, aparece en stock_bajo."""
    import os
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # MP con stock_minimo 1000g
    conn.execute("""INSERT OR REPLACE INTO maestro_mps
                    (codigo_mp, nombre_comercial, stock_minimo, activo, tipo_material)
                    VALUES ('TEST_LOW_STOCK', 'Test MP', 1000, 1, 'MP')""")
    # Movimiento: solo entró 100g → stock = 100, < 1000
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha, estado_lote)
                    VALUES ('TEST_LOW_STOCK', 'Test MP', 100, 'Entrada',
                            datetime('now'), 'VIGENTE')""")
    conn.commit()
    conn.close()

    c = _login(app, "luis")
    r = c.get("/api/planta/alertas-vivas")
    data = r.get_json()
    codigos = [s["codigo_mp"] for s in data["stock_bajo"]]
    assert "TEST_LOW_STOCK" in codigos


def test_alertas_vivas_detects_expiring(app, db_clean):
    """MPs con fecha_vencimiento próxima aparecen en vencimientos."""
    import os
    in_15 = (date.today() + timedelta(days=15)).isoformat()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha,
                     lote, fecha_vencimiento, estado_lote)
                    VALUES ('TEST_VENC', 'Test Vencimiento', 500, 'Entrada',
                            datetime('now'), 'LOTE_VENC', ?, 'VIGENTE')""",
                 (in_15,))
    conn.commit()
    conn.close()

    c = _login(app, "luis")
    r = c.get("/api/planta/alertas-vivas")
    data = r.get_json()
    lotes = [v["lote"] for v in data["vencimientos"]]
    assert "LOTE_VENC" in lotes


# ═══ Sprint 4: Kardex + valoración FIFO ═════════════════════════════════════


def test_kardex_unknown_mp(admin_client, db_clean):
    r = admin_client.get("/api/planta/kardex/NO_EXISTE_999")
    assert r.status_code == 404


def test_kardex_fifo_calculation(app, db_clean):
    """Kardex calcula correctamente con 2 entradas a precios distintos
    y una salida que consume FIFO."""
    import os
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR REPLACE INTO maestro_mps
                    (codigo_mp, nombre_comercial, activo, tipo_material)
                    VALUES ('FIFO_MP', 'Test FIFO', 1, 'MP')""")
    # Entrada 1: 10 kg @ $100/kg = $1000
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha,
                     lote, precio_kg, estado_lote)
                    VALUES ('FIFO_MP', 'Test FIFO', 10000, 'Entrada',
                            '2025-01-01T10:00:00', 'L1', 100, 'VIGENTE')""")
    # Entrada 2: 5 kg @ $200/kg = $1000
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha,
                     lote, precio_kg, estado_lote)
                    VALUES ('FIFO_MP', 'Test FIFO', 5000, 'Entrada',
                            '2025-02-01T10:00:00', 'L2', 200, 'VIGENTE')""")
    # Salida: 12 kg → consume L1 (10kg @100=1000) + L2 (2kg @200=400)
    #   costo total salida = 1400, costo unitario = 1400/12 = 116.67
    #   stock restante: 0 de L1, 3kg de L2 = $600
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha,
                     lote, estado_lote)
                    VALUES ('FIFO_MP', 'Test FIFO', 12000, 'Salida',
                            '2025-03-01T10:00:00', 'PROD-L1', 'VIGENTE')""")
    conn.commit()
    conn.close()

    c = _login(app, "luis")
    r = c.get("/api/planta/kardex/FIFO_MP?desde=2025-01-01&hasta=2025-12-31")
    assert r.status_code == 200
    data = r.get_json()

    assert data["totales"]["entradas_kg"] == 15.0
    assert data["totales"]["salidas_kg"] == 12.0
    assert data["totales"]["saldo_actual_g"] == 3000.0
    assert data["totales"]["valor_actual_fifo"] == 600.0

    # Movimiento de salida debe tener costo_total = 1400
    salida = next(m for m in data["movimientos"] if m["tipo"] == "Salida")
    assert salida["costo_total"] == 1400.0
    # Stock restante: 1 capa de L2 con 3kg
    assert len(data["stock_actual_capas"]) == 1
    assert data["stock_actual_capas"][0]["lote"] == "L2"
    assert data["stock_actual_capas"][0]["cantidad_kg"] == 3.0


def test_valoracion_inventario_endpoint(admin_client, db_clean):
    r = admin_client.get("/api/planta/valoracion-inventario")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("items", "valor_total_fifo", "count", "por_tipo_material"):
        assert key in data


def test_valoracion_inventario_filter(admin_client, db_clean):
    r = admin_client.get("/api/planta/valoracion-inventario?tipo_material=Empaque")
    assert r.status_code == 200
    data = r.get_json()
    # Todos los items devueltos deben ser de Empaque
    for item in data["items"]:
        assert item["tipo_material"] == "Empaque"


# ═══ Sprint solicitud + eliminar lote desde Stock por Lote ═══════════════════
# Política CEO 2026-04-27: jefe de producción puede solicitar MP desde la vista
# de Stock por Lote (modal a nivel MP) y eliminar lotes con motivo obligatorio
# para corregir incoherencias de carga (recepción duplicada, código equivocado).


def test_eliminar_lote_requiere_motivo(app, db_clean):
    """DELETE /api/lotes/<mid>/<lote> sin motivo o con < 10 chars debe ser 400."""
    c = _login(app, "luis")
    r = c.delete("/api/lotes/MPTEST/LOTE-A",
                 json={}, headers=csrf_headers())
    assert r.status_code == 400
    body = r.get_json()
    assert "motivo" in (body.get("error") or "").lower()

    r = c.delete("/api/lotes/MPTEST/LOTE-A",
                 json={"motivo": "corto"}, headers=csrf_headers())
    assert r.status_code == 400


def test_eliminar_lote_lote_inexistente(app, db_clean):
    """Si el lote no tiene movimientos, 404."""
    c = _login(app, "luis")
    r = c.delete("/api/lotes/MP_NO_EXISTE/LOTE_X",
                 json={"motivo": "limpieza de prueba"},
                 headers=csrf_headers())
    assert r.status_code == 404


def test_eliminar_lote_borra_movimientos_y_audit(app, db_clean):
    """Lote con varios movimientos: borra todos + escribe audit_log."""
    import os
    c = _login(app, "luis")

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("""INSERT OR IGNORE INTO maestro_mps
                   (codigo_mp, nombre_inci, nombre_comercial, tipo,
                    proveedor, stock_minimo, activo)
                   VALUES ('MP_DEL_TEST','TEST INCI','Test MP','Activo',
                           'Prov X', 0, 1)""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, proveedor, fecha_vencimiento, operador)
                   VALUES ('MP_DEL_TEST','Test MP','LOTE-DEL-1',1000,
                           'Entrada','2026-04-20','Prov X','2027-01-01','luis')""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, operador)
                   VALUES ('MP_DEL_TEST','Test MP','LOTE-DEL-1',300,
                           'Salida','2026-04-22','luis')""")
    conn.commit()
    conn.close()

    r = c.delete("/api/lotes/MP_DEL_TEST/LOTE-DEL-1",
                 json={"motivo": "Recepcion duplicada de prueba"},
                 headers=csrf_headers())
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert j["deleted_count"] == 2
    assert j["snapshot"]["saldo_neto_g_al_eliminar"] == 700.0
    assert j["snapshot"]["motivo"] == "Recepcion duplicada de prueba"

    # Verificar que los movimientos ya no existen
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT COUNT(*) FROM movimientos WHERE material_id='MP_DEL_TEST' "
        "AND lote='LOTE-DEL-1'"
    ).fetchone()
    assert rows[0] == 0

    # Verificar que quedó audit_log
    audit = cur.execute(
        "SELECT usuario, accion, registro_id FROM audit_log "
        "WHERE accion='ELIMINAR_LOTE' AND registro_id='MP_DEL_TEST/LOTE-DEL-1' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None, "audit_log no registró el ELIMINAR_LOTE"
    assert audit[0] == "luis"
    cur.execute("DELETE FROM movimientos WHERE material_id='MP_DEL_TEST'")
    cur.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP_DEL_TEST'")
    conn.commit()
    conn.close()


def test_eliminar_lote_sin_lote_placeholder(app, db_clean):
    """Lote vacío (NULL/'') usa placeholder _SIN_LOTE_ del frontend."""
    import os
    c = _login(app, "luis")

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, operador)
                   VALUES ('MP_NOLOTE','Test MP NoLote', NULL, 500,
                           'Entrada','2026-04-20','luis')""")
    conn.commit()
    conn.close()

    r = c.delete("/api/lotes/MP_NOLOTE/_SIN_LOTE_",
                 json={"motivo": "Movimiento sin lote — limpieza"},
                 headers=csrf_headers())
    assert r.status_code == 200
    j = r.get_json()
    assert j["deleted_count"] == 1


def test_solicitar_desde_lote_crea_solicitud_compra(app, db_clean):
    """El payload del modal Solicitar (POST /api/solicitudes-compra) crea
    una solicitud Pendiente con el item de la MP."""
    c = _login(app, "luis")

    payload = {
        "solicitante": "luis",
        "urgencia": "Alta",
        "observaciones": "Stock bajo mínimo, requiero para producción",
        "empresa": "Espagiria",
        "categoria": "Materia Prima",
        "tipo": "Compra",
        "area": "Produccion",
        "items": [{
            "codigo_mp": "MP00245",
            "nombre_mp": "1,2-Hexanediol",
            "cantidad_g": 5000,
            "unidad": "g",
            "justificacion": "Producción GEL HID",
            "valor_estimado": 0,
        }],
    }
    r = c.post("/api/solicitudes-compra",
               json=payload, headers=csrf_headers())
    assert r.status_code == 201
    j = r.get_json()
    assert j["numero"].startswith("SOL-")

    # Verificar estado en DB
    import os
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    sol = cur.execute(
        "SELECT estado, urgencia, area, categoria FROM solicitudes_compra "
        "WHERE numero=?", (j["numero"],)
    ).fetchone()
    assert sol is not None
    assert sol[0] == "Pendiente"
    assert sol[1] == "Alta"
    items = cur.execute(
        "SELECT codigo_mp, cantidad_g FROM solicitudes_compra_items "
        "WHERE numero=?", (j["numero"],)
    ).fetchall()
    assert len(items) == 1
    assert items[0][0] == "MP00245"
    assert items[0][1] == 5000

    cur.execute("DELETE FROM solicitudes_compra_items WHERE numero=?",
                (j["numero"],))
    cur.execute("DELETE FROM solicitudes_compra WHERE numero=?",
                (j["numero"],))
    conn.commit()
    conn.close()


# ═══ Editar proveedor de lote (afecta movimientos + maestro_mps) ═══════════


def test_proveedores_unicos_lista(app, db_clean):
    """GET /api/proveedores-unicos devuelve lista deduplicada de proveedores."""
    import os
    c = _login(app, "luis")

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("""INSERT OR IGNORE INTO maestro_mps
                   (codigo_mp, nombre_inci, nombre_comercial, proveedor, activo)
                   VALUES ('MP_PRV_T1','t1','T1','Lyphar', 1)""")
    cur.execute("""INSERT OR IGNORE INTO maestro_mps
                   (codigo_mp, nombre_inci, nombre_comercial, proveedor, activo)
                   VALUES ('MP_PRV_T2','t2','T2','Inchemical', 1)""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, proveedor, operador)
                   VALUES ('MP_PRV_T1','T1','L-A',100,'Entrada',
                           '2026-04-20','Lyphar','luis')""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, proveedor, operador)
                   VALUES ('MP_PRV_T2','T2','L-B',100,'Entrada',
                           '2026-04-21','Agenquimicos','luis')""")
    conn.commit()
    conn.close()

    r = c.get("/api/proveedores-unicos")
    assert r.status_code == 200
    provs = r.get_json()["proveedores"]
    # Lyphar e Inchemical desde catalogo, Agenquimicos desde movimientos
    for esperado in ("Lyphar", "Inchemical", "Agenquimicos"):
        assert esperado in provs, f'{esperado} debería estar en {provs}'

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("DELETE FROM movimientos WHERE material_id IN ('MP_PRV_T1','MP_PRV_T2')")
    cur.execute("DELETE FROM maestro_mps WHERE codigo_mp IN ('MP_PRV_T1','MP_PRV_T2')")
    conn.commit(); conn.close()


def test_editar_proveedor_lote_validacion(app, db_clean):
    """PUT con proveedor vacío o muy corto → 400."""
    c = _login(app, "luis")
    r = c.put("/api/lotes/MP_X/LOTE-X/proveedor",
              json={}, headers=csrf_headers())
    assert r.status_code == 400
    r = c.put("/api/lotes/MP_X/LOTE-X/proveedor",
              json={"proveedor": "A"}, headers=csrf_headers())
    assert r.status_code == 400
    r = c.put("/api/lotes/MP_X/LOTE-X/proveedor",
              json={"proveedor": "   "}, headers=csrf_headers())
    assert r.status_code == 400


def test_editar_proveedor_lote_mp_inexistente(app, db_clean):
    """PUT sobre MP que no existe en catalogo → 404."""
    c = _login(app, "luis")
    r = c.put("/api/lotes/MP_NO_HAY/LOTE-X/proveedor",
              json={"proveedor": "Lyphar"}, headers=csrf_headers())
    assert r.status_code == 404


def test_editar_proveedor_lote_actualiza_movs_y_catalogo(app, db_clean):
    """PUT correcto: movimientos del lote y maestro_mps quedan en sync."""
    import os
    c = _login(app, "luis")

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("""INSERT INTO maestro_mps
                   (codigo_mp, nombre_inci, nombre_comercial, proveedor, activo)
                   VALUES ('MP_EDIT_PRV','test inci','Test Edit',
                           'Inchemical', 1)""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, proveedor, operador)
                   VALUES ('MP_EDIT_PRV','Test Edit','LOTE-EP-1', 1000,
                           'Entrada','2026-04-20','Inchemical','luis')""")
    cur.execute("""INSERT INTO movimientos
                   (material_id, material_nombre, lote, cantidad, tipo,
                    fecha, proveedor, operador)
                   VALUES ('MP_EDIT_PRV','Test Edit','LOTE-EP-1', 200,
                           'Salida','2026-04-22','Inchemical','luis')""")
    conn.commit()
    conn.close()

    r = c.put("/api/lotes/MP_EDIT_PRV/LOTE-EP-1/proveedor",
              json={"proveedor": "Lyphar Corregido"},
              headers=csrf_headers())
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert j["movimientos_actualizados"] == 2
    assert j["proveedor_anterior_lote"] == "Inchemical"
    assert j["proveedor_anterior_catalogo"] == "Inchemical"
    assert j["proveedor_nuevo"] == "Lyphar Corregido"

    # Verificar DB
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT proveedor FROM movimientos WHERE material_id='MP_EDIT_PRV' "
        "AND lote='LOTE-EP-1'"
    ).fetchall()
    assert all(r[0] == "Lyphar Corregido" for r in rows), (
        f"movimientos no actualizados: {rows}"
    )
    cat = cur.execute(
        "SELECT proveedor FROM maestro_mps WHERE codigo_mp='MP_EDIT_PRV'"
    ).fetchone()
    assert cat[0] == "Lyphar Corregido", (
        f"catalogo no actualizado: {cat[0]}"
    )

    # Audit log
    audit = cur.execute(
        "SELECT usuario, accion FROM audit_log "
        "WHERE accion='EDITAR_PROVEEDOR_LOTE' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None and audit[0] == "luis"

    cur.execute("DELETE FROM movimientos WHERE material_id='MP_EDIT_PRV'")
    cur.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP_EDIT_PRV'")
    conn.commit(); conn.close()
