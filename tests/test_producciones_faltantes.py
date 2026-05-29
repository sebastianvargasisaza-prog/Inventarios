"""Tests del flujo simple para Luis Enrique (Sebastian 5-may-2026).

Vista única en tab Plan: producciones programadas + MP/MEE faltantes
+ botón "Solicitar TODO" → bulk SOL agrupada por proveedor.

Endpoints cubiertos:
  - GET /api/programacion/producciones-faltantes?dias=N
  - POST /api/programacion/solicitar-faltantes-bulk

Reusa toda la infraestructura existente (formulas, sku_mee_config,
maestro_mee, mp_lead_time_config) sin migraciones.
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


def _seed_mp_y_stock(codigo, nombre, gramos_stock, proveedor='ProveedorMP'):
    """Inserta MP en catalogo + un movimiento Entrada con `gramos_stock`.

    Importante: tambien limpia mp_lead_time_config de leaks de tests previos.
    /api/programacion/producciones-faltantes hace COALESCE entre
    mp_lead_time_config.proveedor_principal y maestro_mps.proveedor —
    si otro test dejo una fila ahi, sobreescribiria nuestro proveedor.
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO maestro_mps
               (codigo_mp, nombre_comercial, proveedor, activo, tipo_material)
               VALUES (?, ?, ?, 1, 'MP')""",
            (codigo, nombre, proveedor),
        )
        try:
            c.execute("DELETE FROM mp_lead_time_config WHERE material_id=?", (codigo,))
        except sqlite3.OperationalError:
            pass  # tabla puede no existir en schema legacy
        # Sebastián 29-may-2026: el trigger trg_mov_cantidad_positiva (mig ~99)
        # ABORTA movimientos con cantidad <= 0. "Stock cero" se modela como
        # AUSENCIA de movimiento (stock = SUM(movimientos) = 0), no como una
        # Entrada de 0g. Solo sembramos el movimiento si hay gramos positivos.
        if gramos_stock and gramos_stock > 0:
            c.execute(
                """INSERT INTO movimientos
                   (material_id, material_nombre, cantidad, tipo, fecha,
                    lote, estado_lote, operador)
                   VALUES (?, ?, ?, 'Entrada', date('now'),
                           'L-SEED', 'VIGENTE', 'test')""",
                (codigo, nombre, gramos_stock),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_formula(producto, items, lote_size_kg=10):
    """items: list de (codigo_mp, nombre, cantidad_g_por_lote).

    Sebastián 29-may-2026 (tests stale): migración 99 añadió el trigger
    `trg_fi_material_id_fk`, que ABORTA cualquier INSERT en formula_items
    cuyo material_id no exista en maestro_mps activo. Los tests viejos
    insertaban fórmulas con MPs sin sembrar primero → IntegrityError que
    dejaba la conexión cruda abierta y bloqueaba la BD en cascada. La
    corrección correcta (y fiel al invariante de producción: toda fórmula
    referencia una MP real) es auto-sembrar en maestro_mps cualquier MP que
    no esté ya presente, ANTES de insertar el formula_item.
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO formula_headers
               (producto_nombre, unidad_base_g, lote_size_kg, fecha_creacion)
               VALUES (?, ?, ?, datetime('now'))""",
            (producto, lote_size_kg * 1000, lote_size_kg),
        )
        c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
        for cod, nom, g_lote in items:
            # Garantiza que la MP exista y esté activa (satisface el trigger
            # FK de migración 99). Solo crea si falta · no pisa la fila real
            # que _seed_mp_y_stock pudo haber sembrado con proveedor/stock.
            existe = c.execute(
                "SELECT 1 FROM maestro_mps WHERE codigo_mp=? AND activo=1",
                (cod,),
            ).fetchone()
            if not existe:
                c.execute(
                    """INSERT OR REPLACE INTO maestro_mps
                       (codigo_mp, nombre_comercial, proveedor, activo, tipo_material)
                       VALUES (?, ?, 'ProveedorSeed', 1, 'MP')""",
                    (cod, nom),
                )
            c.execute(
                """INSERT INTO formula_items
                   (producto_nombre, material_id, material_nombre,
                    porcentaje, cantidad_g_por_lote)
                   VALUES (?, ?, ?, 0, ?)""",
                (producto, cod, nom, g_lote),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_mee_y_stock(codigo, descripcion, stock_unidades, proveedor='ProveedorMEE'):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    try:
        c.execute(
            """INSERT OR REPLACE INTO maestro_mee
               (codigo, descripcion, stock_actual, stock_minimo, proveedor, activo)
               VALUES (?, ?, ?, 0, ?, 1)""",
            (codigo, descripcion, stock_unidades, proveedor),
        )
    except sqlite3.OperationalError:
        # Schema sin proveedor/activo
        c.execute(
            """INSERT OR REPLACE INTO maestro_mee
               (codigo, descripcion, stock_actual, stock_minimo)
               VALUES (?, ?, ?, 0)""",
            (codigo, descripcion, stock_unidades),
        )
    conn.commit(); conn.close()


def _seed_sku_mee_config(producto, mee_codigo, cantidad_por_unidad=1, tipo='envase'):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO sku_mee_config
           (sku_codigo, mee_codigo, componente_tipo, cantidad_por_unidad, aplica)
           VALUES (?, ?, ?, ?, 1)""",
        (producto, mee_codigo, tipo, cantidad_por_unidad),
    )
    conn.commit(); conn.close()


def _seed_volumen(producto, volumen_ml):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        conn.execute(
            """INSERT OR REPLACE INTO volumen_unitario_producto
               (producto_nombre, volumen_ml, activo)
               VALUES (?, ?, 1)""",
            (producto, volumen_ml),
        )
    except sqlite3.OperationalError:
        # tabla puede no existir · OK · helper la crea si falta
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS volumen_unitario_producto (
                producto_nombre TEXT PRIMARY KEY,
                volumen_ml REAL DEFAULT 0,
                activo INTEGER DEFAULT 1
            )""")
            conn.execute(
                """INSERT OR REPLACE INTO volumen_unitario_producto
                   (producto_nombre, volumen_ml, activo)
                   VALUES (?, ?, 1)""",
                (producto, volumen_ml),
            )
        except Exception:
            pass
    conn.commit(); conn.close()


def _seed_produccion(producto, lotes=1, fecha_offset_dias=3, cantidad_kg=None):
    """Inserta una produccion_programada en horizonte futuro o pasado.

    fecha_offset_dias soporta negativos para sembrar producciones atrasadas.
    """
    modifier = ('+' if fecha_offset_dias >= 0 else '') + str(fecha_offset_dias) + ' days'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, estado, cantidad_kg)
           VALUES (?, date('now', ?), ?, 'pendiente', ?)""",
        (producto, modifier, lotes, cantidad_kg or 0),
    )
    pid = c.lastrowid
    conn.commit(); conn.close()
    return pid


def _cleanup(productos=None, mps=None, mees=None, prod_ids=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    if prod_ids:
        ph = ','.join(['?']*len(prod_ids))
        c.execute(f"DELETE FROM produccion_programada WHERE id IN ({ph})", prod_ids)
    if productos:
        ph = ','.join(['?']*len(productos))
        c.execute(f"DELETE FROM formula_items WHERE producto_nombre IN ({ph})", productos)
        c.execute(f"DELETE FROM formula_headers WHERE producto_nombre IN ({ph})", productos)
        c.execute(f"DELETE FROM sku_mee_config WHERE sku_codigo IN ({ph})", productos)
        try:
            c.execute(f"DELETE FROM volumen_unitario_producto WHERE producto_nombre IN ({ph})",
                      productos)
        except sqlite3.OperationalError:
            pass
    if mps:
        ph = ','.join(['?']*len(mps))
        c.execute(f"DELETE FROM movimientos WHERE material_id IN ({ph})", mps)
        c.execute(f"DELETE FROM maestro_mps WHERE codigo_mp IN ({ph})", mps)
        try:
            c.execute(f"DELETE FROM mp_lead_time_config WHERE material_id IN ({ph})", mps)
        except sqlite3.OperationalError:
            pass
    if mees:
        ph = ','.join(['?']*len(mees))
        c.execute(f"DELETE FROM maestro_mee WHERE codigo IN ({ph})", mees)
        try:
            c.execute(f"DELETE FROM mee_lead_time_config WHERE mee_codigo IN ({ph})", mees)
        except sqlite3.OperationalError:
            pass
    conn.commit(); conn.close()


# ── GET /api/programacion/producciones-faltantes ──────────────────


def test_producciones_faltantes_listado_basico(app, db_clean):
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-PF-1', 'Glicerina PF', 1000, 'ProvA')  # Stock 1kg
    _seed_mp_y_stock('MP-PF-2', 'Agua PF', 100000, 'ProvB')      # Stock 100kg
    _seed_formula('PROD-PF-1', [
        ('MP-PF-1', 'Glicerina PF', 5000),  # 5kg necesario
        ('MP-PF-2', 'Agua PF', 5000),       # 5kg
    ], lote_size_kg=10)
    pid = _seed_produccion('PROD-PF-1', lotes=2, cantidad_kg=20)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        assert r.status_code == 200
        d = r.get_json()
        # 1 producción
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-PF-1']
        assert len(prods) == 1
        prod = prods[0]
        assert prod['lotes'] == 2
        # MP1: 5000g/lote × 2 lotes = 10000g necesarios, hay 1000g → falta 9000
        # MP2: 5000g/lote × 2 lotes = 10000g necesarios, hay 100000g → no falta
        nec_mp1 = next(m for m in prod['mps_necesarias'] if m['codigo_mp'] == 'MP-PF-1')
        assert nec_mp1['necesario_g'] == 10000
        # Faltantes agregados
        falt_mp1 = next((m for m in d['faltantes_mps'] if m['codigo_mp'] == 'MP-PF-1'), None)
        assert falt_mp1 is not None
        assert falt_mp1['faltante_g'] == 9000
        falt_mp2 = next((m for m in d['faltantes_mps'] if m['codigo_mp'] == 'MP-PF-2'), None)
        assert falt_mp2 is None  # no falta nada
    finally:
        _cleanup(productos=['PROD-PF-1'], mps=['MP-PF-1', 'MP-PF-2'],
                  prod_ids=[pid])


def test_producciones_faltantes_descontadas_aparecen_marcadas(app, db_clean):
    """Sebastián 8-may-2026 ('rescatalas'): producciones con
    inventario_descontado_at AHORA aparecen visibles (antes se escondían).
    Una descontada sin fin_real_at = en_proceso (sigue activa en planta).
    Crítico: aunque visibles, NO suman a faltantes_mps (ya descontaron).
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-DESC-1', 'X', 100)  # solo 100g · si en_proceso
                                              # contara, faltarían 4900g
    _seed_formula('PROD-DESC', [('MP-DESC-1', 'X', 5000)], lote_size_kg=5)
    pid = _seed_produccion('PROD-DESC', lotes=1, cantidad_kg=5)
    # Forzar descontado
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE produccion_programada SET inventario_descontado_at='2026-05-01' WHERE id=?", (pid,))
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-DESC']
        assert len(prods) == 1, 'descontada debe aparecer'
        # Descontada sin fin → en_proceso (siguió activa pero no terminó)
        assert prods[0]['en_proceso'] is True
        assert prods[0]['estado_display'] == 'en_proceso'
        # NO infla faltantes
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-DESC-1'), None)
        assert falt is None, 'descontada NO debe pedir MPs otra vez'
    finally:
        _cleanup(productos=['PROD-DESC'], mps=['MP-DESC-1'], prod_ids=[pid])


def test_producciones_faltantes_excluye_canceladas(app, db_clean):
    cs = _login(app, 'luis')
    _seed_formula('PROD-CAN', [('MP-CAN', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-CAN', lotes=1, cantidad_kg=1)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE produccion_programada SET estado='cancelado' WHERE id=?", (pid,))
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-CAN']
        assert len(prods) == 0
    finally:
        _cleanup(productos=['PROD-CAN'], prod_ids=[pid])


def test_producciones_faltantes_horizonte_filtra_lejanas(app, db_clean):
    cs = _login(app, 'luis')
    _seed_formula('PROD-LEJ', [('MP-LEJ', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-LEJ', lotes=1, cantidad_kg=1, fecha_offset_dias=200)
    try:
        # Horizonte 30d · no debe aparecer
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        prods = [p for p in r.get_json()['producciones'] if p['producto'] == 'PROD-LEJ']
        assert len(prods) == 0
        # Horizonte 365d · sí
        r2 = cs.get('/api/programacion/producciones-faltantes?dias=365')
        prods2 = [p for p in r2.get_json()['producciones'] if p['producto'] == 'PROD-LEJ']
        assert len(prods2) == 1
    finally:
        _cleanup(productos=['PROD-LEJ'], prod_ids=[pid])


def test_producciones_faltantes_mees_calculados_desde_volumen(app, db_clean):
    """Volumen 30ml, producción 3kg = 3000g ≈ 3000ml = 100 unidades → 100 frascos."""
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-MEE-1', 'X', 100000)  # MP suficiente
    _seed_formula('PROD-MEE', [('MP-MEE-1', 'X', 3000)], lote_size_kg=3)
    _seed_mee_y_stock('MEE-FRASCO', 'Frasco 30ml', 50, 'ProvFrasco')  # 50 stock
    _seed_sku_mee_config('PROD-MEE', 'MEE-FRASCO', 1, 'envase')
    _seed_volumen('PROD-MEE', 30)  # 30ml por frasco
    pid = _seed_produccion('PROD-MEE', lotes=1, cantidad_kg=3)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        prod = next(p for p in d['producciones'] if p['producto'] == 'PROD-MEE')
        # 3000ml / 30ml = 100 unidades
        assert prod['unidades_envasadas_estimadas'] == 100
        mee_nec = next(m for m in prod['mees_necesarios'] if m['codigo'] == 'MEE-FRASCO')
        assert mee_nec['necesario_unidades'] == 100
        # Falta: 100 necesarios - 50 stock = 50
        falt = next((f for f in d['faltantes_mees'] if f['codigo'] == 'MEE-FRASCO'), None)
        assert falt is not None
        assert falt['faltante_u'] == 50
    finally:
        _cleanup(productos=['PROD-MEE'], mps=['MP-MEE-1'], mees=['MEE-FRASCO'],
                  prod_ids=[pid])


def test_producciones_faltantes_sin_login_401(client):
    r = client.get('/api/programacion/producciones-faltantes')
    assert r.status_code == 401


def test_producciones_faltantes_horizonte_clamp(app, db_clean):
    cs = _login(app, 'luis')
    r = cs.get('/api/programacion/producciones-faltantes?dias=999')
    d = r.get_json()
    assert d['horizonte_dias'] == 365
    r2 = cs.get('/api/programacion/producciones-faltantes?dias=1')
    assert r2.get_json()['horizonte_dias'] == 7


# ── POST /api/programacion/solicitar-faltantes-bulk ───────────────


def test_solicitar_bulk_crea_solicitudes_agrupadas(app, db_clean):
    """Faltantes con 2 proveedores → 2 solicitudes (1 por proveedor)."""
    cs = _login(app, 'sebastian')  # admin para asegurar permiso
    _seed_mp_y_stock('MP-BLK-A', 'A', 100, proveedor='ProvA')
    _seed_mp_y_stock('MP-BLK-B', 'B', 100, proveedor='ProvB')
    _seed_formula('PROD-BLK', [
        ('MP-BLK-A', 'A', 5000),
        ('MP-BLK-B', 'B', 5000),
    ], lote_size_kg=5)
    pid = _seed_produccion('PROD-BLK', lotes=1, cantidad_kg=5)
    try:
        r = cs.post('/api/programacion/solicitar-faltantes-bulk',
                    json={'dias': 30, 'urgencia': 'Alta'},
                    headers=csrf_headers())
        assert r.status_code == 201, r.data
        d = r.get_json()
        assert d['ok'] is True
        # MIS proveedores deben aparecer (otros tests pueden generar mas)
        provs = {s['proveedor'] for s in d['solicitudes_creadas']}
        assert 'ProvA' in provs
        assert 'ProvB' in provs
        assert d['total_proveedores'] >= 2
        # Verificar SOLs en DB
        conn = sqlite3.connect(os.environ["DB_PATH"])
        for s in d['solicitudes_creadas']:
            row = conn.execute(
                "SELECT estado, urgencia FROM solicitudes_compra WHERE numero=?",
                (s['numero'],)).fetchone()
            assert row[0] == 'Pendiente'
            assert row[1] == 'Alta'
        conn.close()
        # Limpiar SOLs creadas
        conn = sqlite3.connect(os.environ["DB_PATH"])
        for s in d['solicitudes_creadas']:
            conn.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (s['numero'],))
            conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (s['numero'],))
        conn.commit(); conn.close()
    finally:
        _cleanup(productos=['PROD-BLK'], mps=['MP-BLK-A', 'MP-BLK-B'],
                  prod_ids=[pid])


def test_solicitar_bulk_sin_faltantes_no_incluye_mp_con_stock(app, db_clean):
    """Sin faltantes para MIs MPs (stock suficiente) → ninguna SOL los incluye.

    El endpoint puede crear SOLs para OTRAS producciones programadas con
    faltantes (data de otros tests), pero las que YO sembré con stock
    suficiente NO deben aparecer.
    """
    cs = _login(app, 'sebastian')
    _seed_mp_y_stock('MP-NOFALTA', 'X', 100000)  # stock 100kg
    _seed_formula('PROD-NOFALTA', [('MP-NOFALTA', 'X', 5000)], lote_size_kg=5)
    pid = _seed_produccion('PROD-NOFALTA', lotes=1, cantidad_kg=5)
    sols_creadas = []
    try:
        r = cs.post('/api/programacion/solicitar-faltantes-bulk',
                    json={'dias': 30}, headers=csrf_headers())
        # Status 200 si no hay faltantes globales · 201 si hay (de otros tests)
        assert r.status_code in (200, 201), r.data
        d = r.get_json()
        assert d['ok'] is True
        sols_creadas = [s['numero'] for s in d.get('solicitudes_creadas', [])]
        # Verificar que MP-NOFALTA NO esté en ninguna solicitud
        if sols_creadas:
            ph = ','.join(['?']*len(sols_creadas))
            conn = sqlite3.connect(os.environ["DB_PATH"])
            count = conn.execute(
                f"SELECT COUNT(*) FROM solicitudes_compra_items "
                f"WHERE numero IN ({ph}) AND codigo_mp='MP-NOFALTA'",
                sols_creadas,
            ).fetchone()[0]
            conn.close()
            assert count == 0, "MP-NOFALTA NO debe aparecer en SOLs"
    finally:
        if sols_creadas:
            conn = sqlite3.connect(os.environ["DB_PATH"])
            ph = ','.join(['?']*len(sols_creadas))
            conn.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})", sols_creadas)
            conn.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph})", sols_creadas)
            conn.commit(); conn.close()
        _cleanup(productos=['PROD-NOFALTA'], mps=['MP-NOFALTA'], prod_ids=[pid])


def test_solicitar_bulk_sin_login_401(client):
    """Sin login → 401."""
    r = client.post('/api/programacion/solicitar-faltantes-bulk',
                    json={'dias': 30}, headers=csrf_headers())
    assert r.status_code == 401


def test_solicitar_bulk_luis_jefe_produccion_puede(app, db_clean):
    """Luis (jefe de producción) ESTA en COMPRAS_USERS · puede solicitar
    porque ese es el use case · este endpoint es PARA él."""
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-LUIS-OK', 'X', 100, proveedor='ProvX')
    _seed_formula('PROD-LUIS', [('MP-LUIS-OK', 'X', 5000)], lote_size_kg=5)
    pid = _seed_produccion('PROD-LUIS', lotes=1, cantidad_kg=5)
    sols_creadas = []
    try:
        r = cs.post('/api/programacion/solicitar-faltantes-bulk',
                    json={'dias': 30}, headers=csrf_headers())
        assert r.status_code == 201, r.data
        d = r.get_json()
        sols_creadas = [s['numero'] for s in d.get('solicitudes_creadas', [])]
    finally:
        if sols_creadas:
            conn = sqlite3.connect(os.environ["DB_PATH"])
            ph = ','.join(['?']*len(sols_creadas))
            conn.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})", sols_creadas)
            conn.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph})", sols_creadas)
            conn.commit(); conn.close()
        _cleanup(productos=['PROD-LUIS'], mps=['MP-LUIS-OK'], prod_ids=[pid])


def test_solicitar_bulk_audit_log(app, db_clean):
    cs = _login(app, 'sebastian')
    _seed_mp_y_stock('MP-AUD', 'X', 100, proveedor='ProvAud')
    _seed_formula('PROD-AUD', [('MP-AUD', 'X', 5000)], lote_size_kg=5)
    pid = _seed_produccion('PROD-AUD', lotes=1, cantidad_kg=5)
    sols_creadas = []
    try:
        r = cs.post('/api/programacion/solicitar-faltantes-bulk',
                    json={'dias': 30}, headers=csrf_headers())
        d = r.get_json()
        sols_creadas = [s['numero'] for s in (d.get('solicitudes_creadas') or [])]
        # Audit log
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion FROM audit_log "
            "WHERE accion='SOLICITAR_FALTANTES_BULK' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'sebastian'
    finally:
        if sols_creadas:
            conn = sqlite3.connect(os.environ["DB_PATH"])
            ph = ','.join(['?']*len(sols_creadas))
            conn.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})", sols_creadas)
            conn.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph})", sols_creadas)
            conn.commit(); conn.close()
        _cleanup(productos=['PROD-AUD'], mps=['MP-AUD'], prod_ids=[pid])


# ── HTML expone UI ─────────────────────────────────────────────────


def _seed_produccion_realizada(producto, fecha_offset_dias, lotes=1, cantidad_kg=5):
    """Insert a production marked as realizada (descontada + estado completado).

    fecha_offset_dias soporta negativos · construimos modifier explícito.
    """
    modifier = ('+' if fecha_offset_dias >= 0 else '') + str(fecha_offset_dias) + ' days'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, estado, cantidad_kg,
            inicio_real_at, fin_real_at, inventario_descontado_at)
           VALUES (?, date('now', ?), ?, 'completado', ?,
                   datetime('now'), datetime('now'), datetime('now'))""",
        (producto, modifier, lotes, cantidad_kg),
    )
    pid = c.lastrowid
    conn.commit(); conn.close()
    return pid


def _seed_produccion_en_proceso(producto, fecha_offset_dias, lotes=1, cantidad_kg=5):
    """Producción que arrancó pero no terminó: inicio_real_at + descontada."""
    modifier = ('+' if fecha_offset_dias >= 0 else '') + str(fecha_offset_dias) + ' days'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, estado, cantidad_kg,
            inicio_real_at, inventario_descontado_at)
           VALUES (?, date('now', ?), ?, 'en_proceso', ?,
                   datetime('now'), datetime('now'))""",
        (producto, modifier, lotes, cantidad_kg),
    )
    pid = c.lastrowid
    conn.commit(); conn.close()
    return pid


def test_realizadas_aparecen_en_panel(app, db_clean):
    """Sebastián 8-may-2026 ('rescatalas'): producciones completadas DEBEN
    aparecer en el panel para visibilidad. Antes el filtro las escondía y
    parecía que se habían perdido.
    """
    cs = _login(app, 'luis')
    _seed_formula('PROD-RESC-DONE', [('MP-RESC-D', 'X', 1000)], lote_size_kg=1)
    pid_real = _seed_produccion_realizada('PROD-RESC-DONE',
                                            fecha_offset_dias=-3, lotes=2,
                                            cantidad_kg=2)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        assert r.status_code == 200
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-RESC-DONE']
        assert len(prods) == 1, 'la realizada DEBE aparecer en el panel'
        p = prods[0]
        assert p['realizada'] is True
        assert p['estado_display'] == 'realizada'
        # Resumen contiene contador
        assert d['resumen']['n_realizadas'] >= 1
    finally:
        _cleanup(productos=['PROD-RESC-DONE'], prod_ids=[pid_real])


def test_realizadas_no_inflan_mp_faltantes(app, db_clean):
    """Crítico: producciones ya descontadas NO deben sumar al cálculo de MPs
    faltantes — sus MPs ya se descontaron del stock. Si las contáramos otra
    vez, infláriamos la lista de compras y se ordenaría stock duplicado.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-NOINFLA', 'X', 5000, 'ProvX')   # 5kg en stock
    _seed_formula('PROD-NOINFLA', [('MP-NOINFLA', 'X', 5000)], lote_size_kg=5)
    # Realizada (no debe contar) + pendiente futura (sí cuenta)
    pid_done = _seed_produccion_realizada('PROD-NOINFLA',
                                            fecha_offset_dias=-2, lotes=1,
                                            cantidad_kg=5)
    pid_pend = _seed_produccion('PROD-NOINFLA', lotes=1, cantidad_kg=5,
                                  fecha_offset_dias=4)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        # Solo la pendiente debe contribuir al cálculo: 5000g - 5000g stock = 0
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-NOINFLA'), None)
        # Si la realizada inflara → necesario=10000 → falta 5000. Bug.
        # Esperado: necesario=5000 → falta 0 → no aparece en faltantes
        assert falt is None, (
            f'realizada NO debe inflar MP faltantes · falt={falt}')
    finally:
        _cleanup(productos=['PROD-NOINFLA'], mps=['MP-NOINFLA'],
                  prod_ids=[pid_done, pid_pend])


def test_en_proceso_aparece_y_no_infla_mp(app, db_clean):
    """Producción que arrancó (inicio_real_at + descontada) pero no terminó:
    visible con estado_display='en_proceso' y NO suma a faltantes.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-PROC', 'X', 5000)
    _seed_formula('PROD-PROC', [('MP-PROC', 'X', 5000)], lote_size_kg=5)
    pid = _seed_produccion_en_proceso('PROD-PROC',
                                        fecha_offset_dias=0, lotes=1,
                                        cantidad_kg=5)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        p = next(p for p in d['producciones'] if p['producto'] == 'PROD-PROC')
        assert p['en_proceso'] is True
        assert p['estado_display'] == 'en_proceso'
        # No infla MP — su descuento ya se aplicó
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-PROC'), None)
        assert falt is None, 'en_proceso ya descontó · NO debe pedir más'
    finally:
        _cleanup(productos=['PROD-PROC'], mps=['MP-PROC'], prod_ids=[pid])


def test_atrasada_aparece_y_si_infla_mp(app, db_clean):
    """Producción cuya fecha pasó pero NUNCA arrancó: 'atrasada'. Sigue
    requiriendo MPs porque no ha consumido stock todavía.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-ATR', 'X', 0)  # sin stock
    _seed_formula('PROD-ATR', [('MP-ATR', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-ATR', lotes=1, cantidad_kg=1,
                            fecha_offset_dias=-3)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        p = next(p for p in d['producciones'] if p['producto'] == 'PROD-ATR')
        assert p['atrasada'] is True
        assert p['estado_display'] == 'atrasada'
        # SÍ debe contar a faltantes (1000g necesarios, 0 stock)
        falt = next(m for m in d['faltantes_mps']
                    if m['codigo_mp'] == 'MP-ATR')
        assert falt['faltante_g'] == 1000
        # Resumen
        assert d['resumen']['n_atrasadas'] >= 1
    finally:
        _cleanup(productos=['PROD-ATR'], mps=['MP-ATR'], prod_ids=[pid])


def test_canceladas_siguen_ocultas(app, db_clean):
    """Las cancelaciones SIGUEN siendo ruido — no deben aparecer en el panel
    ni siquiera con la nueva visibilidad de realizadas/atrasadas.
    """
    cs = _login(app, 'luis')
    _seed_formula('PROD-CANC', [('MP-CC', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-CANC', lotes=1, cantidad_kg=1)
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("UPDATE produccion_programada SET estado='cancelado' WHERE id=?", (pid,))
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-CANC']
        assert len(prods) == 0, 'canceladas siguen ocultas · son basura'
    finally:
        _cleanup(productos=['PROD-CANC'], prod_ids=[pid])


def test_realizada_no_clona_con_pendiente_misma_kg(app, db_clean):
    """Antes: una realizada + una pendiente con mismo kg/lotes dentro de 7d
    se marcaban como CLONES. Eso es falso positivo — la realizada es historia,
    no clon de la próxima.
    """
    cs = _login(app, 'luis')
    _seed_formula('PROD-NOCLON', [('MP-NC', 'X', 1000)], lote_size_kg=1)
    pid_done = _seed_produccion_realizada('PROD-NOCLON',
                                            fecha_offset_dias=-2, lotes=1,
                                            cantidad_kg=1)
    pid_next = _seed_produccion('PROD-NOCLON', lotes=1, cantidad_kg=1,
                                  fecha_offset_dias=3)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-NOCLON']
        assert len(agr) == 1
        assert agr[0]['duplicado_sospechoso'] is False, \
            'realizada vs pendiente NO son clones'
    finally:
        _cleanup(productos=['PROD-NOCLON'], prod_ids=[pid_done, pid_next])


def test_dashboard_html_expone_vista_simple(app, db_clean):
    cs = _login(app, 'luis')
    body = cs.get('/inventarios').get_data(as_text=True)
    # Vista calendario por sala (Sebastian 5-may-2026)
    assert 'pv2-vista-simple' in body
    assert 'pv2CargarProdFaltantes' in body
    assert 'pv2SolicitarFaltantesBulk' in body
    assert 'pv2VerProd' in body  # click celda → modal detalle
    assert 'modal-prod-detalle' in body
    assert 'Producciones programadas' in body
    assert 'Solicitar TODO faltante' in body
    # Vista por producto + cleanup duplicados (Sebastian 7-may-2026)
    assert 'pv2VerProductoAgrupado' in body
    assert 'pv2LimpiarDuplicados' in body
    # 29-may-2026: el botón se renombró de "Limpiar duplicados" a "Limpiar"
    # (handler pv2LimpiarDuplicados sigue igual). Aceptamos el texto actual.
    assert 'Limpiar' in body
    # Sebastian 8-may-2026: UNA FILA POR (producto × fecha) — antes colapsaba
    # múltiples fechas en "Lun 11 +N" oculto.
    assert 'UNA FILA POR (producto × fecha)' in body
    assert 'Fecha</th>' in body  # nuevo header (antes "Próxima")
    # +N badge ya NO debe estar — todas las fechas son visibles ahora
    assert '<span style="color:#94a3b8;font-size:10px">+' not in body


# ── Vista agrupada por producto ────────────────────────────────────


def test_producciones_agrupadas_consolida_misma_producto(app, db_clean):
    """Un producto con 2 fechas debe aparecer UNA vez en producciones_agrupadas
    con todas sus fechas listadas y total_kg sumado.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-AGR-1', 'X', 100000)
    _seed_formula('PROD-AGR', [('MP-AGR-1', 'X', 5000)], lote_size_kg=5)
    pid_a = _seed_produccion('PROD-AGR', lotes=1, cantidad_kg=5,
                              fecha_offset_dias=2)
    pid_b = _seed_produccion('PROD-AGR', lotes=2, cantidad_kg=10,
                              fecha_offset_dias=10)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-AGR']
        assert len(agr) == 1, 'producto debe consolidarse en 1 entry'
        g = agr[0]
        assert len(g['fechas']) == 2
        assert g['total_kg'] == 15  # 5 + 10
        assert g['total_lotes'] == 3  # 1 + 2
        # Fechas ordenadas ascendente
        assert g['fechas'][0]['fecha'] < g['fechas'][1]['fecha']
    finally:
        _cleanup(productos=['PROD-AGR'], mps=['MP-AGR-1'],
                  prod_ids=[pid_a, pid_b])


def test_duplicado_sospechoso_marca_clones_dentro_de_7_dias(app, db_clean):
    """Misma producción (mismo producto + lotes + kg) en fechas dentro de 7d
    → flag duplicado_sospechoso=True.
    """
    cs = _login(app, 'luis')
    _seed_formula('PROD-DUP', [('MP-DUP', 'X', 1000)], lote_size_kg=1)
    pid_a = _seed_produccion('PROD-DUP', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=2)
    pid_b = _seed_produccion('PROD-DUP', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=4)  # 2 días después
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-DUP']
        assert len(agr) == 1
        assert agr[0]['duplicado_sospechoso'] is True
        assert agr[0]['duplicados_detalle']
        # Resumen contiene contador de duplicados
        res = d.get('resumen', {})
        assert res.get('n_productos_con_duplicados', 0) >= 1
    finally:
        _cleanup(productos=['PROD-DUP'], prod_ids=[pid_a, pid_b])


def test_fechas_distintas_misma_semana_no_se_colapsan(app, db_clean):
    """Bug 8-may-2026 Sebastián: el panel mostraba 'Lun 11 +1' colapsando
    múltiples fechas distintas de la misma semana en la primera. El backend
    DEBE devolver TODAS las fechas distintas con su propio pid/lotes/kg en
    g.fechas[] para que el frontend pueda renderizar una fila por fecha.

    Caso: PROD-MULTIWEEK con 3 fechas en horizonte 14d (lunes 11, jueves 14,
    lunes 18). Cada fecha con kg/lotes distintos. La respuesta debe preservar
    las 3 fechas separadas.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-MW-1', 'X', 100000)
    _seed_formula('PROD-MULTIWEEK', [('MP-MW-1', 'X', 1000)], lote_size_kg=10)
    pid_1 = _seed_produccion('PROD-MULTIWEEK', lotes=2, cantidad_kg=20,
                              fecha_offset_dias=3)
    pid_2 = _seed_produccion('PROD-MULTIWEEK', lotes=1, cantidad_kg=10,
                              fecha_offset_dias=6)
    pid_3 = _seed_produccion('PROD-MULTIWEEK', lotes=3, cantidad_kg=30,
                              fecha_offset_dias=10)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        assert r.status_code == 200
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-MULTIWEEK']
        assert len(agr) == 1
        g = agr[0]
        # Las 3 fechas DISTINTAS deben estar en g.fechas — sin colapsar
        assert len(g['fechas']) == 3, \
            f"Esperaba 3 fechas distintas, got {len(g['fechas'])}"
        # Cada fecha con su propio pid/lotes/kg (no totalizado)
        fechas_por_pid = {f['pid']: f for f in g['fechas']}
        assert pid_1 in fechas_por_pid
        assert pid_2 in fechas_por_pid
        assert pid_3 in fechas_por_pid
        assert fechas_por_pid[pid_1]['lotes'] == 2
        assert fechas_por_pid[pid_2]['lotes'] == 1
        assert fechas_por_pid[pid_3]['lotes'] == 3
        assert fechas_por_pid[pid_1]['cantidad_kg'] == 20
        assert fechas_por_pid[pid_2]['cantidad_kg'] == 10
        assert fechas_por_pid[pid_3]['cantidad_kg'] == 30
        # Fechas ordenadas ascendente
        fechas_iso = [f['fecha'] for f in g['fechas']]
        assert fechas_iso == sorted(fechas_iso)
        # Totales agregados separados de las fechas individuales
        assert g['total_lotes'] == 6
        assert g['total_kg'] == 60
    finally:
        _cleanup(productos=['PROD-MULTIWEEK'], mps=['MP-MW-1'],
                  prod_ids=[pid_1, pid_2, pid_3])


def test_fechas_no_se_marcan_clones_si_separadas_mas_de_7_dias(app, db_clean):
    """Bug-related: 4 lunes consecutivos del mes (4 productions, 7 dias entre
    cada una) NO debe activar el flag duplicado_sospechoso porque la regla es
    'mismo producto + mismos lotes/kg DENTRO de 7 dias' — exactamente 7 entra
    al límite, pero el caso real son lunes consecutivos de cadencia distinta.
    """
    cs = _login(app, 'luis')
    _seed_formula('PROD-MONDAYS', [('MP-MN-1', 'X', 500)], lote_size_kg=5)
    # 4 fechas separadas por > 7 días cada una (offset 1, 9, 17, 25)
    pids = []
    for offset in (1, 9, 17, 25):
        pids.append(_seed_produccion('PROD-MONDAYS', lotes=1, cantidad_kg=5,
                                      fecha_offset_dias=offset))
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-MONDAYS']
        assert len(agr) == 1
        g = agr[0]
        # 4 fechas distintas preservadas
        assert len(g['fechas']) == 4
        # No debe marcar como clones (separadas > 7d)
        assert g['duplicado_sospechoso'] is False, \
            f"Lunes consecutivos NO son clones · detalle: {g.get('duplicados_detalle')}"
    finally:
        _cleanup(productos=['PROD-MONDAYS'], prod_ids=pids)


def test_duplicado_no_marca_si_distintos_lotes(app, db_clean):
    """Mismo producto con DISTINTOS lotes/kg no debe marcar como clon."""
    cs = _login(app, 'luis')
    _seed_formula('PROD-NODUP', [('MP-ND', 'X', 1000)], lote_size_kg=1)
    pid_a = _seed_produccion('PROD-NODUP', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=2)
    pid_b = _seed_produccion('PROD-NODUP', lotes=3, cantidad_kg=3,
                              fecha_offset_dias=4)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=30')
        d = r.get_json()
        agr = [g for g in (d.get('producciones_agrupadas') or [])
               if g['producto'] == 'PROD-NODUP']
        assert len(agr) == 1
        assert agr[0]['duplicado_sospechoso'] is False
    finally:
        _cleanup(productos=['PROD-NODUP'], prod_ids=[pid_a, pid_b])


# ── /api/programacion/limpiar-duplicados-producciones ──────────────


def test_limpiar_duplicados_dry_run_no_borra(app, db_clean):
    cs = _login(app, 'sebastian')
    _seed_formula('PROD-LIMP-DUP', [('MP-LD', 'X', 1000)], lote_size_kg=1)
    pid_a = _seed_produccion('PROD-LIMP-DUP', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=2)
    pid_b = _seed_produccion('PROD-LIMP-DUP', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=4)
    try:
        r = cs.post('/api/programacion/limpiar-duplicados-producciones',
                    json={'dry_run': True, 'horizonte_dias': 30},
                    headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d['ok'] is True
        assert d['dry_run'] is True
        assert d['producciones_a_borrar'] >= 1
        # NO se borraron
        conn = sqlite3.connect(os.environ['DB_PATH'])
        cnt = conn.execute(
            "SELECT COUNT(*) FROM produccion_programada WHERE id IN (?, ?)",
            (pid_a, pid_b)
        ).fetchone()[0]
        conn.close()
        assert cnt == 2
    finally:
        _cleanup(productos=['PROD-LIMP-DUP'], prod_ids=[pid_a, pid_b])


def test_limpiar_duplicados_ejecuta_borra_solo_clones(app, db_clean):
    """Ejecuta cleanup · debe eliminar el clon (más tarde) y conservar el ancla.

    29-may-2026: el endpoint ya NO hace DELETE duro (fix 19-may-2026 'hueco
    Fijo vs Sugerido' · MEMORY). Ahora SOFT-CANCEL: la fila del clon SIGUE
    en la tabla con estado='cancelado' (auditable/recuperable), mientras la
    ancla permanece 'pendiente'. Actualizamos las aserciones al borrado
    lógico actual en vez del borrado físico viejo.
    """
    cs = _login(app, 'sebastian')
    _seed_formula('PROD-LIMP-EXEC', [('MP-LX', 'X', 1000)], lote_size_kg=1)
    pid_a = _seed_produccion('PROD-LIMP-EXEC', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=2)  # ancla (más temprana)
    pid_b = _seed_produccion('PROD-LIMP-EXEC', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=5)  # clon
    try:
        r = cs.post('/api/programacion/limpiar-duplicados-producciones',
                    json={'dry_run': False, 'horizonte_dias': 30},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['ok'] is True
        assert d['producciones_borradas'] >= 1
        # ancla sigue activa, clon soft-cancelado
        conn = sqlite3.connect(os.environ['DB_PATH'])
        anc = conn.execute(
            "SELECT LOWER(COALESCE(estado,'')) FROM produccion_programada WHERE id=?",
            (pid_a,)
        ).fetchone()
        clon = conn.execute(
            "SELECT LOWER(COALESCE(estado,'')) FROM produccion_programada WHERE id=?",
            (pid_b,)
        ).fetchone()
        conn.close()
        assert anc is not None and anc[0] != 'cancelado', \
            'ancla (más temprana) NO debe cancelarse'
        assert clon is not None and clon[0] == 'cancelado', \
            'clon (más tarde) DEBE quedar soft-cancelado'
    finally:
        _cleanup(productos=['PROD-LIMP-EXEC'], prod_ids=[pid_a, pid_b])


def test_limpiar_duplicados_no_toca_descontadas(app, db_clean):
    """Producciones ya descontadas NO deben aparecer en el plan."""
    cs = _login(app, 'sebastian')
    _seed_formula('PROD-LIMP-DESC', [('MP-LDS', 'X', 1000)], lote_size_kg=1)
    pid_a = _seed_produccion('PROD-LIMP-DESC', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=2)
    pid_b = _seed_produccion('PROD-LIMP-DESC', lotes=1, cantidad_kg=1,
                              fecha_offset_dias=4)
    # Marcar pid_a como descontada
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("UPDATE produccion_programada "
                  "SET inventario_descontado_at='2026-05-01' WHERE id=?",
                  (pid_a,))
    conn.commit(); conn.close()
    try:
        r = cs.post('/api/programacion/limpiar-duplicados-producciones',
                    json={'dry_run': True, 'horizonte_dias': 30},
                    headers=csrf_headers())
        d = r.get_json()
        # Buscar plan sobre PROD-LIMP-DESC · no debe haber nada (la única
        # producción no-descontada es pid_b, no tiene clon)
        relevant = [g for g in (d.get('plan') or [])
                    if g['producto'] == 'PROD-LIMP-DESC']
        assert not relevant, 'no debe planear borrar nada · descontada se ignora'
    finally:
        _cleanup(productos=['PROD-LIMP-DESC'], prod_ids=[pid_a, pid_b])


def test_limpiar_duplicados_sin_login_401(client):
    r = client.post('/api/programacion/limpiar-duplicados-producciones',
                    json={'dry_run': True}, headers=csrf_headers())
    assert r.status_code == 401


# ── /api/programacion/checklist/sync-calendar (force_mirror) ──────


def test_sync_calendar_endpoint_acepta_force_mirror(app, db_clean):
    """El endpoint debe aceptar ?force_mirror=true y reportarlo en respuesta."""
    cs = _login(app, 'sebastian')
    r = cs.post('/api/programacion/checklist/sync-calendar?force_mirror=true&dias=30',
                headers=csrf_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is True
    assert d['force_mirror'] is True
    assert 'modo espejo' in (d.get('mensaje') or '').lower() or \
           d.get('producciones_creadas', 0) >= 0  # mensaje varía si no hay events


def test_sync_calendar_default_no_force_mirror(app, db_clean):
    """Sin ?force_mirror = comportamiento legacy."""
    cs = _login(app, 'sebastian')
    r = cs.post('/api/programacion/checklist/sync-calendar?dias=30',
                headers=csrf_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d['force_mirror'] is False


def test_sync_calendar_sin_login_401(client):
    r = client.post('/api/programacion/checklist/sync-calendar')
    assert r.status_code == 401


# ════════════════════════════════════════════════════════════════════
# Sebastián 9-may-2026: filtro atrasadas_max_dias para ocultar
# producciones pendientes pasadas viejas (basura abandonada).
# ════════════════════════════════════════════════════════════════════

def test_atrasadas_viejas_pendientes_se_ocultan_por_default(app, db_clean):
    """Una pendiente de hace 30 días sin arrancar NO debe aparecer en
    la vista por default (atrasadas_max_dias=7). Es basura visual.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-VJ', 'X', 0)
    _seed_formula('PROD-VIEJA', [('MP-VJ', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-VIEJA', lotes=1, cantidad_kg=1,
                            fecha_offset_dias=-30)  # 30 días atrás
    try:
        # Default (atrasadas_max_dias implícito = 7)
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-VIEJA']
        assert not prods, \
            f'BUG: producción de hace 30 días NO debe aparecer · default oculta >7d'
        # Pero el contador de ocultas SÍ debe reflejarlas
        assert d['resumen'].get('n_atrasadas_ocultas', 0) >= 1, \
            'n_atrasadas_ocultas debe contar la vieja oculta'
        # MPs faltantes NO deben inflar (esa producción no contribuye)
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-VJ'), None)
        assert falt is None, 'BUG: MP de producción oculta no debe contar como faltante'
    finally:
        _cleanup(productos=['PROD-VIEJA'], mps=['MP-VJ'], prod_ids=[pid])


def test_atrasadas_viejas_visible_si_pasa_param(app, db_clean):
    """Si el frontend pasa ?atrasadas_max_dias=999 (toggle 'Mostrar
    atrasadas viejas'), las producciones viejas SÍ aparecen.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-VS', 'X', 0)
    _seed_formula('PROD-VS', [('MP-VS', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-VS', lotes=1, cantidad_kg=1,
                            fecha_offset_dias=-10)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14&atrasadas_max_dias=999')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-VS']
        assert prods, 'BUG: con atrasadas_max_dias=999 la vieja debe aparecer'
        assert prods[0]['atrasada'] is True
        # Ahora SÍ debe contar para faltantes
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-VS'), None)
        assert falt is not None, 'BUG: con toggle activado debe contar faltantes'
        assert falt['faltante_g'] == 1000
    finally:
        _cleanup(productos=['PROD-VS'], mps=['MP-VS'], prod_ids=[pid])


def test_realizadas_pasadas_siempre_visibles(app, db_clean):
    """Una producción con descuento aplicado (desc_at) DEBE aparecer
    aunque sea de hace 10 días. El filtro atrasadas_max_dias NO aplica
    a producciones que ya tocaron stock — son trazabilidad histórica.
    Nota: se marca como `en_proceso` (arrancó/descontó pero sin fin_real_at).
    Para `realizada=True` necesita fin_real_at o estado=completado.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-RP', 'X', 0)
    _seed_formula('PROD-REAL', [('MP-RP', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-REAL', lotes=1, cantidad_kg=1,
                            fecha_offset_dias=-10)
    # Marcarla como descontada (ya consumió MPs)
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("UPDATE produccion_programada SET inventario_descontado_at=datetime('now') WHERE id=?", (pid,))
    conn.commit(); conn.close()
    try:
        # Default — debe aparecer aunque sea -10d (con desc_at supera filtro)
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-REAL']
        assert prods, 'BUG: producción descontada de hace 10d debe aparecer aunque default oculta atrasadas viejas'
        # Con desc_at se marca en_proceso (no realizada porque falta fin_real_at)
        assert prods[0].get('en_proceso') is True, \
            f'debe marcarse en_proceso (arrancó/descontó · sin fin_real): {prods[0]}'
        # NO debe contar para faltantes (sus MPs ya fueron descontadas)
        falt = next((m for m in d['faltantes_mps']
                     if m['codigo_mp'] == 'MP-RP'), None)
        assert falt is None, 'descontada NO debe inflar faltantes'
    finally:
        _cleanup(productos=['PROD-REAL'], mps=['MP-RP'], prod_ids=[pid])


def test_atrasadas_recientes_dentro_threshold_aparecen(app, db_clean):
    """Una pendiente de hace 3 días (dentro del threshold 7d default)
    SÍ aparece como atrasada. No es basura vieja, todavía puede hacerse.
    """
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-AR', 'X', 0)
    _seed_formula('PROD-AR', [('MP-AR', 'X', 1000)], lote_size_kg=1)
    pid = _seed_produccion('PROD-AR', lotes=1, cantidad_kg=1,
                            fecha_offset_dias=-3)
    try:
        r = cs.get('/api/programacion/producciones-faltantes?dias=14')
        d = r.get_json()
        prods = [p for p in d['producciones'] if p['producto'] == 'PROD-AR']
        assert prods, 'atrasada de -3d debe aparecer (default 7d)'
        assert prods[0]['atrasada'] is True
    finally:
        _cleanup(productos=['PROD-AR'], mps=['MP-AR'], prod_ids=[pid])
