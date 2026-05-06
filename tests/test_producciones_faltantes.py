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
    c.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, estado_lote, operador)
           VALUES (?, ?, ?, 'Entrada', date('now'),
                   'L-SEED', 'VIGENTE', 'test')""",
        (codigo, nombre, gramos_stock),
    )
    conn.commit(); conn.close()


def _seed_formula(producto, items, lote_size_kg=10):
    """items: list de (codigo_mp, nombre, cantidad_g_por_lote)."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO formula_headers
           (producto_nombre, unidad_base_g, lote_size_kg, fecha_creacion)
           VALUES (?, ?, ?, datetime('now'))""",
        (producto, lote_size_kg * 1000, lote_size_kg),
    )
    c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
    for cod, nom, g_lote in items:
        c.execute(
            """INSERT INTO formula_items
               (producto_nombre, material_id, material_nombre,
                porcentaje, cantidad_g_por_lote)
               VALUES (?, ?, ?, 0, ?)""",
            (producto, cod, nom, g_lote),
        )
    conn.commit(); conn.close()


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
    """Inserta una produccion_programada en horizonte futuro."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, estado, cantidad_kg)
           VALUES (?, date('now', '+' || ? || ' days'), ?, 'pendiente', ?)""",
        (producto, fecha_offset_dias, lotes, cantidad_kg or 0),
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


def test_producciones_faltantes_excluye_descontadas(app, db_clean):
    """Producciones con inventario_descontado_at NO deben aparecer."""
    cs = _login(app, 'luis')
    _seed_mp_y_stock('MP-DESC-1', 'X', 100)
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
        assert len(prods) == 0  # excluida
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
