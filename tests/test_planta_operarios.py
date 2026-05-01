"""Tests de la lógica de asignación de operarios (zero-error audit 1-may-2026).

Regla dura del CEO: operarios con `fija_en_dispensacion=1` SOLO pueden ir a
rol 'dispensacion'. Mayerlin Rivera tiene este flag en el seed.

Antes del fix, las funciones `_operarios_para` y `_auto_asignar_operarios`
ignoraban el flag y se basaban sólo en pesos AFINIDAD probabilísticos —
Mayerlin podía caer en elaboración/envasado/acondicionamiento por hash.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luis"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _ids_operarios(conn):
    """Retorna {nombre_lower: id} para los operarios activos."""
    out = {}
    for row in conn.execute("""
        SELECT id, LOWER(nombre || ' ' || COALESCE(apellido,''))
        FROM operarios_planta
        WHERE COALESCE(activo,1)=1
    """).fetchall():
        out[row[1].strip()] = row[0]
    return out


def test_mayerlin_tiene_flag_fija_en_dispensacion(app, db_clean):
    """El seed de operarios marca a Mayerlin como fija (regla dura)."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute("""
        SELECT COALESCE(fija_en_dispensacion,0)
        FROM operarios_planta
        WHERE LOWER(nombre)='mayerlin'
    """).fetchone()
    conn.close()
    assert row is not None, "Mayerlin no está en el seed de operarios_planta"
    assert row[0] == 1, "Mayerlin DEBE tener fija_en_dispensacion=1 (regla dura CEO)"


def test_auto_asignar_excluye_mayerlin_de_roles_no_dispensacion(app, db_clean):
    """`_auto_asignar_operarios` NO debe poner a Mayerlin en elaboracion,
    envasado ni acondicionamiento — sólo en dispensacion.
    """
    from blueprints.programacion import _auto_asignar_operarios
    from database import get_db

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    ops = _ids_operarios(conn)
    mayerlin_id = next((v for k, v in ops.items() if k.startswith("mayerlin")), None)
    assert mayerlin_id, f"Mayerlin no encontrada en operarios: {list(ops.keys())}"

    # Crear una producción de prueba
    cur.execute("""
        INSERT INTO produccion_programada
            (producto, fecha_programada, lotes, cantidad_kg, estado)
        VALUES ('TEST_MAYERLIN_RULE', '2026-06-01', 1, 50, 'programado')
    """)
    pid = cur.lastrowid
    conn.commit()

    # Forzar 50 asignaciones distintas (con productos+fechas hash distintos)
    # para cubrir todo el espacio de hash. Si Mayerlin cae en cualquier rol
    # ≠ dispensacion EN CUALQUIERA DE LAS 50, el test falla.
    fallos = []
    for i in range(50):
        cur.execute("""
            UPDATE produccion_programada SET
              producto = ?, fecha_programada = ?,
              operario_dispensacion_id = NULL,
              operario_elaboracion_id = NULL,
              operario_envasado_id = NULL,
              operario_acondicionamiento_id = NULL
            WHERE id = ?
        """, (f'TEST_MAY_{i}', f'2026-06-{(i % 28) + 1:02d}', pid))
        _auto_asignar_operarios(cur, pid, f'2026-06-{(i % 28) + 1:02d}', user='test')
        row = cur.execute("""
            SELECT operario_dispensacion_id, operario_elaboracion_id,
                   operario_envasado_id, operario_acondicionamiento_id
            FROM produccion_programada WHERE id=?
        """, (pid,)).fetchone()
        if row[1] == mayerlin_id:
            fallos.append(f'iter {i}: Mayerlin en op_elaboracion')
        if row[2] == mayerlin_id:
            fallos.append(f'iter {i}: Mayerlin en op_envasado')
        if row[3] == mayerlin_id:
            fallos.append(f'iter {i}: Mayerlin en op_acondicionamiento')

    cur.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
    cur.execute("DELETE FROM rotacion_operarios_state WHERE actualizado_por='test'")
    conn.commit()
    conn.close()

    assert not fallos, (
        f"Mayerlin asignada a roles ≠ dispensacion en {len(fallos)}/50 iteraciones: "
        + '; '.join(fallos[:5])
    )


def test_auto_asignar_pone_mayerlin_en_dispensacion(app, db_clean):
    """Cuando hay operarios con `fija_en_dispensacion=1`, el rol dispensación
    debe llenarse OBLIGATORIAMENTE con uno de ellos (no puede quedar NULL si
    el flag está activo y el operario está activo).
    """
    from blueprints.programacion import _auto_asignar_operarios

    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    ops = _ids_operarios(conn)
    mayerlin_id = next((v for k, v in ops.items() if k.startswith("mayerlin")), None)
    assert mayerlin_id

    cur.execute("""
        INSERT INTO produccion_programada
            (producto, fecha_programada, lotes, cantidad_kg, estado)
        VALUES ('TEST_DISP_FORZADO', '2026-07-15', 1, 30, 'programado')
    """)
    pid = cur.lastrowid
    conn.commit()

    _auto_asignar_operarios(cur, pid, '2026-07-15', user='test')
    row = cur.execute(
        "SELECT operario_dispensacion_id FROM produccion_programada WHERE id=?",
        (pid,)
    ).fetchone()

    cur.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
    cur.execute("DELETE FROM rotacion_operarios_state WHERE actualizado_por='test'")
    conn.commit()
    conn.close()

    assert row[0] == mayerlin_id, (
        f"op_dispensacion_id debería ser Mayerlin ({mayerlin_id}), got {row[0]}"
    )


def test_pipeline_constante_es_7_dias(app, db_clean):
    """Regla CEO: pipeline = lotes producidos en últimos 7d (no 14d).

    Verifica el código fuente — no hay forma directa de probar el cálculo
    sin mockear Calendar, así que valida la constante.
    """
    src = open(
        os.path.join(os.path.dirname(__file__), '..', 'api',
                     'blueprints', 'auto_plan.py'),
        encoding='utf-8',
    ).read()
    # La constante PIPELINE_DIAS debe ser 7 (no 14 ni otro valor)
    assert 'PIPELINE_DIAS = 7' in src, (
        "PIPELINE_DIAS debe ser 7 (regla: lote tarda 7d en aparecer en Shopify)"
    )
    # No debe quedar el legacy `timedelta(days=14)` para fecha_pipeline_inicio
    assert 'fecha_pipeline_inicio = fecha_hoy - timedelta(days=14)' not in src, (
        "Quedó el código legacy de 14d — limpiar"
    )


# ─── Tests de cron_locks (audit zero-error 1-may-2026) ─────────────────────

def test_cron_lock_adquirir_y_liberar(app, db_clean):
    """_adquirir_lock_cron debe ser atómico: solo el primer caller lo gana."""
    from blueprints.auto_plan_jobs import (
        _adquirir_lock_cron, _liberar_lock_cron
    )
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        # Primer adquirir → True
        assert _adquirir_lock_cron(conn, 'test_job_x') is True
        # Segundo (sin liberar) → False (otro tiene el lock)
        assert _adquirir_lock_cron(conn, 'test_job_x') is False
        # Liberar
        _liberar_lock_cron(conn, 'test_job_x')
        # Después de liberar → otro puede adquirir
        assert _adquirir_lock_cron(conn, 'test_job_x') is True
        _liberar_lock_cron(conn, 'test_job_x')
    finally:
        conn.execute("DELETE FROM cron_locks WHERE job_name='test_job_x'")
        conn.commit()
        conn.close()


def test_cron_lock_ttl_expira(app, db_clean):
    """Si un worker crashea sin liberar, el lock vencido (>TTL) se libera."""
    from blueprints.auto_plan_jobs import _adquirir_lock_cron
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        # Insertar un lock viejo (3 horas atrás · TTL es 2h)
        conn.execute("""
            INSERT OR REPLACE INTO cron_locks (job_name, locked_at, locked_by)
            VALUES ('test_job_old', datetime('now', '-3 hours'), 'crashed_worker')
        """)
        conn.commit()
        # Adquirir debe limpiar el viejo y reclamar
        assert _adquirir_lock_cron(conn, 'test_job_old', ttl_horas=2) is True
    finally:
        conn.execute("DELETE FROM cron_locks WHERE job_name='test_job_old'")
        conn.commit()
        conn.close()


# ─── Tests de _cargar_afinidad ──────────────────────────────────────────────

def test_cargar_afinidad_devuelve_estructura_completa(app, db_clean):
    """La matriz AFINIDAD debe tener los 4 roles destino con ≥4 entries cada uno."""
    from blueprints.auto_plan import _cargar_afinidad
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        afin = _cargar_afinidad(conn)
        assert set(afin.keys()) >= {'dispensacion', 'elaboracion',
                                      'envasado', 'acondicionamiento'}
        # Mismo rol_destino → rol_predeterminado debe pesar 4 (preferido fuerte)
        assert afin['dispensacion']['dispensacion'] == 4
        assert afin['elaboracion']['elaboracion'] == 4
        assert afin['envasado']['envasado'] == 4
        assert afin['acondicionamiento']['acondicionamiento'] == 4
        # Sebastián 1-may-2026: peso 3 (legacy buggy) ya NO existe en seed
        for rol_d, pesos in afin.items():
            assert 3 not in pesos.values(), (
                f"Rol {rol_d} tiene peso 3 (legacy bug Mayerlin elaboración)"
            )
    finally:
        conn.close()


def test_cargar_afinidad_fallback_si_tabla_vacia(app, db_clean):
    """Si rol_afinidad_config se vacía, debe caer a default hardcoded."""
    from blueprints.auto_plan import _cargar_afinidad, _AFINIDAD_DEFAULT
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        # Backup
        rows = conn.execute(
            "SELECT rol_destino, rol_predeterminado, peso FROM rol_afinidad_config"
        ).fetchall()
        conn.execute("DELETE FROM rol_afinidad_config")
        conn.commit()
        afin = _cargar_afinidad(conn)
        # Debe coincidir con _AFINIDAD_DEFAULT
        assert afin == _AFINIDAD_DEFAULT
        # Restaurar
        for r in rows:
            conn.execute(
                "INSERT OR IGNORE INTO rol_afinidad_config "
                "(rol_destino, rol_predeterminado, peso) VALUES (?,?,?)",
                r
            )
        conn.commit()
    finally:
        conn.close()


# ─── Test del endpoint validar-hermanos-skus ───────────────────────────────

def test_validar_hermanos_skus_endpoint(app, db_clean):
    """Endpoint detecta SKUs con mismo prefix pero producto distinto."""
    c = _login(app, "luis")
    r = c.get("/api/planta/validar-hermanos-skus")
    assert r.status_code == 200
    data = r.get_json()
    assert 'total_grupos_sospechosos' in data
    assert 'grupos' in data
    assert isinstance(data['grupos'], list)


def test_validar_hermanos_skus_requiere_auth(client, db_clean):
    r = client.get("/api/planta/validar-hermanos-skus")
    assert r.status_code == 401


# ─── Test validación MP China lead time ────────────────────────────────────

def test_configs_mp_warn_china_lead_corto(app, db_clean):
    """POST a /api/auto-plan/configs/mp con origen=China y lead<60d retorna warning."""
    c = _login(app, "luis")
    r = c.post("/api/auto-plan/configs/mp",
               json={"material_id": "TEST_CHINA",
                     "material_nombre": "Test China MP",
                     "origen": "China",
                     "lead_time_dias": 30,
                     "buffer_dias": 30,
                     "cobertura_min_dias": 30,
                     "cobertura_ideal_dias": 60},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert any('China' in w for w in data.get('warnings', [])), (
        f"Esperaba warning de China pero recibí: {data.get('warnings')}"
    )

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM mp_lead_time_config WHERE material_id='TEST_CHINA'")
    conn.commit(); conn.close()


def test_configs_mp_rechaza_lead_negativo(app, db_clean):
    """POST con lead_time_dias=0 debe ser 400."""
    c = _login(app, "luis")
    r = c.post("/api/auto-plan/configs/mp",
               json={"material_id": "TEST_INVALID",
                     "material_nombre": "Test",
                     "lead_time_dias": 0},
               headers=csrf_headers())
    assert r.status_code == 400


def test_configs_mp_rechaza_cobertura_inversa(app, db_clean):
    """cobertura_ideal < cobertura_min debe ser 400 (incoherente)."""
    c = _login(app, "luis")
    r = c.post("/api/auto-plan/configs/mp",
               json={"material_id": "TEST_INC",
                     "material_nombre": "Test",
                     "lead_time_dias": 30,
                     "cobertura_min_dias": 60,
                     "cobertura_ideal_dias": 30},
               headers=csrf_headers())
    assert r.status_code == 400


# ─── Tests Round 2 audit (1-may-2026) ──────────────────────────────────────

def test_trigger_bd_bloquea_mayerlin_en_elaboracion(app, db_clean):
    """El trigger SQL impide UPDATE de operario_elaboracion_id con un fijo.

    Defense-in-depth: si alguien hace UPDATE directo en BD (bypass del código
    Python), el trigger BD lo bloquea con RAISE(ABORT).
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    # Crear producción de prueba
    cur.execute("""
        INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado)
        VALUES ('TEST_TRIGGER', '2026-08-01', 1, 'programado')
    """)
    pid = cur.lastrowid
    # Mayerlin id
    mayerlin_id = cur.execute(
        "SELECT id FROM operarios_planta WHERE LOWER(nombre)='mayerlin'"
    ).fetchone()[0]
    # Intentar UPDATE directo → debe fallar con IntegrityError
    intentado = False
    try:
        cur.execute(
            "UPDATE produccion_programada SET operario_elaboracion_id = ? WHERE id = ?",
            (mayerlin_id, pid)
        )
        conn.commit()
        intentado = True
    except sqlite3.IntegrityError as e:
        assert 'fija_en_dispensacion' in str(e), f"mensaje inesperado: {e}"
    finally:
        cur.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit()
        conn.close()
    assert not intentado, "trigger BD NO bloqueó el UPDATE (defensa rota)"


def test_trigger_bd_permite_mayerlin_en_dispensacion(app, db_clean):
    """El trigger NO debe bloquear UPDATE a operario_dispensacion_id."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado)
        VALUES ('TEST_TRIGGER_OK', '2026-08-02', 1, 'programado')
    """)
    pid = cur.lastrowid
    mayerlin_id = cur.execute(
        "SELECT id FROM operarios_planta WHERE LOWER(nombre)='mayerlin'"
    ).fetchone()[0]
    cur.execute(
        "UPDATE produccion_programada SET operario_dispensacion_id = ? WHERE id = ?",
        (mayerlin_id, pid)
    )
    conn.commit()
    row = cur.execute(
        "SELECT operario_dispensacion_id FROM produccion_programada WHERE id=?",
        (pid,)
    ).fetchone()
    cur.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    assert row[0] == mayerlin_id


def test_validar_acceso_cron_legacy(app, db_clean):
    """Helper _validar_acceso_cron en modo legacy (env AUTO_PLAN_CRON_KEY)."""
    from blueprints.auto_plan import _validar_acceso_cron
    from unittest.mock import patch, MagicMock

    secret_old = os.environ.get('AUTO_PLAN_CRON_KEY', '')
    os.environ['AUTO_PLAN_CRON_KEY'] = 'test-secret-cron-123'
    os.environ.pop('HMAC_CRON_REQUIRED', None)
    try:
        # Mock request con clave correcta
        req = MagicMock()
        req.args.get.return_value = 'test-secret-cron-123'
        req.json = None
        es_cron, err = _validar_acceso_cron(req)
        assert es_cron is True and err is None

        # Clave incorrecta
        req.args.get.return_value = 'wrong-key'
        es_cron, err = _validar_acceso_cron(req)
        assert es_cron is False
    finally:
        if secret_old:
            os.environ['AUTO_PLAN_CRON_KEY'] = secret_old
        else:
            os.environ.pop('AUTO_PLAN_CRON_KEY', None)


def test_validar_acceso_cron_hmac_required(app, db_clean):
    """En modo HMAC_CRON_REQUIRED=1, falla sin firma válida."""
    from blueprints.auto_plan import _validar_acceso_cron
    from unittest.mock import MagicMock
    import hmac, hashlib, time

    secret_old = os.environ.get('AUTO_PLAN_CRON_KEY', '')
    hmac_old = os.environ.get('HMAC_CRON_REQUIRED', '')
    os.environ['AUTO_PLAN_CRON_KEY'] = 'test-secret-hmac'
    os.environ['HMAC_CRON_REQUIRED'] = '1'
    try:
        req = MagicMock()
        req.headers.get.return_value = ''
        req.args.get.return_value = ''
        req.json = None
        es_cron, err = _validar_acceso_cron(req)
        assert es_cron is False
        assert err and 'HMAC_REQUIRED' in err

        # Firma válida con timestamp actual
        ts = str(int(time.time()))
        body = ''
        msg = ts.encode('utf-8') + b'\n' + body.encode('utf-8')
        sig = hmac.new(b'test-secret-hmac', msg, hashlib.sha256).hexdigest()
        req2 = MagicMock()
        headers_map = {'X-Cron-Signature': sig, 'X-Cron-Timestamp': ts}
        req2.headers.get.side_effect = lambda k, default='': headers_map.get(k, default)
        es_cron2, err2 = _validar_acceso_cron(req2, body=body)
        assert es_cron2 is True, f"HMAC válido rechazado: {err2}"
    finally:
        if secret_old:
            os.environ['AUTO_PLAN_CRON_KEY'] = secret_old
        else:
            os.environ.pop('AUTO_PLAN_CRON_KEY', None)
        if hmac_old:
            os.environ['HMAC_CRON_REQUIRED'] = hmac_old
        else:
            os.environ.pop('HMAC_CRON_REQUIRED', None)


def test_unificar_hermanos_skus_endpoint(app, db_clean):
    """POST /api/planta/unificar-hermanos-skus actualiza sku_producto_map."""
    c = _login(app, "luis")

    # Setup: 2 SKUs con productos distintos pero deben compartir bulk
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo)
                    VALUES ('TESTAH', 'PRODUCTO TEST AH', 1)""")
    conn.execute("""INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo)
                    VALUES ('TESTAH10', 'PRODUCTO TEST AH 10ML', 1)""")
    # formula_headers debe tener el canónico para que el endpoint lo acepte
    conn.execute("""INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg)
                    VALUES ('SUERO HIDRATANTE AH 1.5%', 30)""")
    conn.commit()
    conn.close()

    r = c.post("/api/planta/unificar-hermanos-skus",
               json={"producto_canonico": "SUERO HIDRATANTE AH 1.5%",
                     "skus": ["TESTAH", "TESTAH10"]},
               headers=csrf_headers())
    assert r.status_code == 200, f"got {r.status_code}: {r.data[:200]!r}"
    data = r.get_json()
    assert data['ok'] is True
    assert data['skus_actualizados'] == 2

    # Verificar BD
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute(
        "SELECT producto_nombre FROM sku_producto_map WHERE sku IN ('TESTAH','TESTAH10')"
    ).fetchall()
    assert all(r[0] == 'SUERO HIDRATANTE AH 1.5%' for r in rows)
    conn.execute("DELETE FROM sku_producto_map WHERE sku IN ('TESTAH','TESTAH10')")
    conn.commit()
    conn.close()


def test_unificar_hermanos_skus_rechaza_canonico_inexistente(app, db_clean):
    """Si producto_canonico no existe en formula_headers, rechazar."""
    c = _login(app, "luis")
    r = c.post("/api/planta/unificar-hermanos-skus",
               json={"producto_canonico": "PRODUCTO_INEXISTENTE_XYZ_999",
                     "skus": ["AAA", "BBB"]},
               headers=csrf_headers())
    assert r.status_code == 400


def test_unificar_hermanos_skus_rechaza_skus_insuficientes(app, db_clean):
    """skus debe ser lista con ≥2 elementos."""
    c = _login(app, "luis")
    r = c.post("/api/planta/unificar-hermanos-skus",
               json={"producto_canonico": "X", "skus": ["AAA"]},
               headers=csrf_headers())
    assert r.status_code == 400


def test_endpoint_programar_post_requiere_auth(app, db_clean):
    """POST /api/programacion/programar sin login → 401 (antes era 200/400)."""
    c = app.test_client()  # sin login
    r = c.post("/api/programacion/programar",
               json={"producto": "X", "fecha": "2026-08-01"},
               headers=csrf_headers())
    assert r.status_code == 401


def test_endpoint_mp_bridge_post_requiere_auth(app, db_clean):
    """POST /api/programacion/mp-bridge sin login → 401."""
    c = app.test_client()
    r = c.post("/api/programacion/mp-bridge",
               json={"formula_material_id": "X", "bodega_material_id": "Y"},
               headers=csrf_headers())
    assert r.status_code == 401


def test_margen_dias_activo_default_25(app, db_clean):
    """Default debe ser MARGEN_IDEAL_DIAS=25 (regla CEO 25d ideal)."""
    # Borrar override env si existe
    saved = os.environ.pop('MARGEN_PLANEACION_DIAS', None)
    try:
        # Re-importar módulo para que tome el default
        import importlib
        from blueprints import auto_plan
        importlib.reload(auto_plan)
        assert auto_plan.MARGEN_IDEAL_DIAS == 25
        assert auto_plan.MARGEN_MIN_DIAS == 20
        # MARGEN_DIAS_ACTIVO debe ser el ideal por default
        assert auto_plan.MARGEN_DIAS_ACTIVO == 25
    finally:
        if saved:
            os.environ['MARGEN_PLANEACION_DIAS'] = saved
        # Re-reload para no contaminar otros tests
        import importlib
        from blueprints import auto_plan
        importlib.reload(auto_plan)


# ─── Tests Round 3: blueprints fuera de planta (compras, inventario, calidad) ──

def test_movimiento_salida_rechaza_si_stock_insuficiente(app, db_clean):
    """POST /api/movimientos tipo='Salida' DEBE rechazar si va a dejar saldo
    negativo. Antes podía dejar inventario negativo silenciosamente."""
    c = _login(app, "luis")
    # Setup: MP con stock 100g (1 entrada de 100)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
                    (codigo_mp, nombre_inci, nombre_comercial, activo)
                    VALUES ('MP_NEG_TEST', 'test', 'Test Stock Neg', 1)""")
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, cantidad, tipo, fecha)
                    VALUES ('MP_NEG_TEST', 'Test Stock Neg', 100, 'Entrada',
                            datetime('now'))""")
    conn.commit()
    conn.close()

    # Intentar Salida de 200g (> stock 100g) → 422
    r = c.post("/api/movimientos",
               json={"material_id": "MP_NEG_TEST",
                     "material_nombre": "Test Stock Neg",
                     "cantidad": 200, "tipo": "Salida"},
               headers=csrf_headers())
    assert r.status_code == 422, f"esperaba 422, got {r.status_code}: {r.data[:200]!r}"
    body = r.get_json()
    assert 'stock insuficiente' in (body.get('error') or '').lower()

    # Salida válida (50g) → 201
    r2 = c.post("/api/movimientos",
                json={"material_id": "MP_NEG_TEST",
                      "material_nombre": "Test Stock Neg",
                      "cantidad": 50, "tipo": "Salida"},
                headers=csrf_headers())
    assert r2.status_code == 201

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP_NEG_TEST'")
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP_NEG_TEST'")
    conn.commit(); conn.close()


def test_movimiento_rechaza_cantidad_negativa(app, db_clean):
    """cantidad <= 0 debe ser 400."""
    c = _login(app, "luis")
    r = c.post("/api/movimientos",
               json={"material_id": "X", "material_nombre": "Test",
                     "cantidad": -10, "tipo": "Entrada"},
               headers=csrf_headers())
    assert r.status_code == 400
    r2 = c.post("/api/movimientos",
                json={"material_id": "X", "material_nombre": "Test",
                      "cantidad": 0, "tipo": "Entrada"},
                headers=csrf_headers())
    assert r2.status_code == 400


def test_oc_item_rechaza_cantidad_negativa(app, db_clean):
    """POST item OC con cantidad_g<=0 debe ser 400."""
    c = _login(app, "luis")
    # Setup OC mínima
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR REPLACE INTO ordenes_compra
                    (numero_oc, proveedor, estado, valor_total, con_iva)
                    VALUES ('OC-TEST-001', 'Prov X', 'Borrador', 0, 0)""")
    conn.commit(); conn.close()

    r = c.post("/api/ordenes-compra/OC-TEST-001/items",
               json={"nombre_mp": "MP X", "cantidad_g": -100, "precio_unitario": 50},
               headers=csrf_headers())
    assert r.status_code == 400

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-TEST-001'")
    conn.commit(); conn.close()


def test_cerrar_nc_rechaza_sin_motivo(app, db_clean):
    """POST cerrar_nc sin motivo_cierre o motivo<10 chars → 400."""
    c = _login(app, "laura")  # calidad
    r = c.post("/api/calidad/no-conformidades/999/cerrar",
               json={},
               headers=csrf_headers())
    assert r.status_code == 400
    r2 = c.post("/api/calidad/no-conformidades/999/cerrar",
                json={"motivo_cierre": "corto"},
                headers=csrf_headers())
    assert r2.status_code == 400


def test_cerrar_nc_rbac_solo_calidad(app, db_clean):
    """POST cerrar_nc rechaza usuarios no-calidad/no-admin."""
    c = _login(app, "luis")  # planta, no calidad
    r = c.post("/api/calidad/no-conformidades/999/cerrar",
               json={"motivo_cierre": "Motivo de prueba completo INVIMA",
                     "accion_correctiva": "Acción correctiva test"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_unique_constraint_oc_numero(app, db_clean):
    """UNIQUE INDEX en ordenes_compra(numero_oc) previene duplicados."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        conn.execute("""INSERT OR REPLACE INTO ordenes_compra
                        (numero_oc, proveedor, estado, valor_total)
                        VALUES ('OC-UNIQ-TEST', 'Prov A', 'Borrador', 100)""")
        conn.commit()
        # Intentar insertar duplicado → IntegrityError
        rejected = False
        try:
            conn.execute("""INSERT INTO ordenes_compra
                            (numero_oc, proveedor, estado, valor_total)
                            VALUES ('OC-UNIQ-TEST', 'Prov B', 'Borrador', 200)""")
            conn.commit()
        except sqlite3.IntegrityError:
            rejected = True
        assert rejected, "UNIQUE constraint NO bloqueó duplicado"
    finally:
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-UNIQ-TEST'")
        conn.commit()
        conn.close()
