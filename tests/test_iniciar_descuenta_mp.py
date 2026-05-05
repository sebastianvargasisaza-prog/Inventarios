"""Tests del descuento MP en /api/programacion/programar/<id>/iniciar.

Sebastian 5-may-2026 (Luis Enrique): "no estan terminando las producciones,
se quedan en envasado, pero dejemos que cuando carguen produccion de
materia prima de una descuente". Antes el descuento estaba en /completar
(paso final) que los operarios no ejecutaban → MPs nunca salian del
inventario. Ahora /iniciar descuenta atomicamente.

Cubre:
  - iniciar descuenta MP via FEFO al arrancar
  - iniciar bloquea con 422 SIN_STOCK si falta stock
  - iniciar es idempotente (segundo POST devuelve ya_iniciada)
  - iniciar marca inventario_descontado_at + inicio_real_at
  - sin formula → iniciar OK pero sin descuento (warning)
  - completar tras iniciar: skip MP, sigue procesando MEE + estado
  - audit_log registra MPs descontadas con detalle
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


def _seed_mp_con_stock(codigo, nombre, gramos, lote='LT-2026-001', vence='2027-12-31'):
    """Inserta una entrada de stock para un MP."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo)
           VALUES (?, ?, 1)""",
        (codigo, nombre),
    )
    c.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, fecha_vencimiento, operador, estado_lote)
           VALUES (?, ?, ?, 'Entrada', date('now'), 'Test seed', ?, ?, 'test', 'Aprobado')""",
        (codigo, nombre, gramos, lote, vence),
    )
    conn.commit()
    conn.close()


def _seed_formula(producto, items, lote_size_kg=10):
    """Crea formula_headers + formula_items.

    items: lista de tuples (codigo_mp, nombre, porcentaje, cantidad_g_por_lote).
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO formula_headers
           (producto_nombre, unidad_base_g, lote_size_kg, fecha_creacion)
           VALUES (?, ?, ?, datetime('now'))""",
        (producto, lote_size_kg * 1000, lote_size_kg),
    )
    c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
    for cod, nom, pct, g_lote in items:
        c.execute(
            """INSERT INTO formula_items
               (producto_nombre, material_id, material_nombre,
                porcentaje, cantidad_g_por_lote)
               VALUES (?, ?, ?, ?, ?)""",
            (producto, cod, nom, pct, g_lote),
        )
    conn.commit()
    conn.close()


def _seed_produccion(producto, lotes=1, cantidad_kg=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, lotes, estado, cantidad_kg)
           VALUES (?, date('now'), ?, 'pendiente', ?)""",
        (producto, lotes, cantidad_kg or 0),
    )
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def _cleanup(producto=None, codigos_mp=None, prod_id=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    if prod_id:
        c.execute("DELETE FROM produccion_programada WHERE id=?", (prod_id,))
    if producto:
        c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
    if codigos_mp:
        ph = ','.join(['?'] * len(codigos_mp))
        c.execute(f"DELETE FROM movimientos WHERE material_id IN ({ph})", codigos_mp)
        c.execute(f"DELETE FROM maestro_mps WHERE codigo_mp IN ({ph})", codigos_mp)
    conn.commit()
    conn.close()


def _stock_disponible(codigo_mp):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    r = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), 0) "
        "FROM movimientos WHERE material_id=?",
        (codigo_mp,)
    ).fetchone()[0]
    conn.close()
    return float(r or 0)


# ── Iniciar descuenta MP ────────────────────────────────────────────


def test_iniciar_descuenta_mp_de_inventario(app, db_clean):
    """Al iniciar, las MPs de la formula deben descontarse del inventario."""
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-INI-A', 'Glicerina test', 50000)
    _seed_mp_con_stock('MP-INI-B', 'Agua test', 100000)
    _seed_formula('PROD-INI-1', [
        ('MP-INI-A', 'Glicerina test', 30.0, 3000),  # 30% · 3kg/lote
        ('MP-INI-B', 'Agua test', 70.0, 7000),       # 70% · 7kg/lote
    ], lote_size_kg=10)
    pid = _seed_produccion('PROD-INI-1', lotes=2)
    try:
        # Stock antes
        assert _stock_disponible('MP-INI-A') == 50000
        assert _stock_disponible('MP-INI-B') == 100000

        r = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['ok'] is True
        assert d['inventario_descontado_at']
        assert len(d['mps_descontadas']) == 2
        assert d['total_g_descontado'] == 20000  # (3+7) * 2 lotes = 20kg

        # Stock después: 50k - 6k = 44k, 100k - 14k = 86k
        assert _stock_disponible('MP-INI-A') == 44000
        assert _stock_disponible('MP-INI-B') == 86000

        # Verificar movimientos de Salida
        conn = sqlite3.connect(os.environ["DB_PATH"])
        salidas = conn.execute(
            "SELECT material_id, cantidad, tipo FROM movimientos "
            "WHERE material_id IN ('MP-INI-A','MP-INI-B') AND tipo='Salida'"
        ).fetchall()
        conn.close()
        assert len(salidas) == 2  # 1 por MP (FEFO consume del unico lote)
        cantidades = {r[0]: r[1] for r in salidas}
        assert cantidades['MP-INI-A'] == 6000
        assert cantidades['MP-INI-B'] == 14000
    finally:
        _cleanup('PROD-INI-1', ['MP-INI-A', 'MP-INI-B'], pid)


def test_iniciar_bloquea_si_stock_insuficiente(app, db_clean):
    """Si falta stock para alguna MP, iniciar devuelve 422 sin tocar nada."""
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-LOW-A', 'MP escasa', 100)  # solo 100g
    _seed_formula('PROD-INI-2', [
        ('MP-LOW-A', 'MP escasa', 100.0, 5000),  # necesita 5kg
    ], lote_size_kg=5)
    pid = _seed_produccion('PROD-INI-2', lotes=1)
    try:
        r = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                    headers=csrf_headers())
        assert r.status_code == 422
        d = r.get_json()
        assert d['codigo'] == 'SIN_STOCK'
        assert 'faltantes' in d
        assert d['faltantes'][0]['codigo_mp'] == 'MP-LOW-A'
        # Stock no debe cambiar
        assert _stock_disponible('MP-LOW-A') == 100
        # inicio_real_at NO seteado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT inicio_real_at, inventario_descontado_at "
            "FROM produccion_programada WHERE id=?",
            (pid,)
        ).fetchone()
        conn.close()
        assert row[0] is None  # NO iniciada
        assert not row[1]      # NO descontada
    finally:
        _cleanup('PROD-INI-2', ['MP-LOW-A'], pid)


def test_iniciar_idempotente_segundo_post_no_descuenta_doble(app, db_clean):
    """Segundo POST /iniciar devuelve ya_iniciada sin descontar otra vez."""
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-IDM-1', 'Material', 100000)
    _seed_formula('PROD-IDM', [
        ('MP-IDM-1', 'Material', 100.0, 5000),
    ], lote_size_kg=5)
    pid = _seed_produccion('PROD-IDM', lotes=1)
    try:
        r1 = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                     headers=csrf_headers())
        assert r1.status_code == 200
        stock_post1 = _stock_disponible('MP-IDM-1')
        assert stock_post1 == 95000  # 100k - 5k

        r2 = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                     headers=csrf_headers())
        assert r2.status_code == 200
        d2 = r2.get_json()
        assert d2.get('ya_iniciada') is True

        # Stock NO cambia
        assert _stock_disponible('MP-IDM-1') == 95000
    finally:
        _cleanup('PROD-IDM', ['MP-IDM-1'], pid)


def test_iniciar_sin_formula_permite_pero_warning(app, db_clean):
    """Producto sin formula → iniciar OK pero sin_formula=true sin descontar."""
    cs = _login(app, 'luis')
    pid = _seed_produccion('PROD-SIN-FORMULA', lotes=1)
    try:
        r = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['ok'] is True
        assert d['sin_formula'] is True
        assert d['warning']
        assert d['total_g_descontado'] == 0
        # inventario_descontado_at NO seteado (permite re-intento)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        descontado = conn.execute(
            "SELECT inventario_descontado_at FROM produccion_programada WHERE id=?",
            (pid,)
        ).fetchone()[0]
        # inicio_real_at SI seteado
        inicio = conn.execute(
            "SELECT inicio_real_at FROM produccion_programada WHERE id=?",
            (pid,)
        ).fetchone()[0]
        conn.close()
        assert not descontado
        assert inicio is not None
    finally:
        _cleanup(producto='PROD-SIN-FORMULA', prod_id=pid)


def test_completar_tras_iniciar_skip_mp_y_solo_cierra(app, db_clean):
    """Si iniciar ya descontó, completar NO debe descontar otra vez."""
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-CMP-1', 'M1', 50000)
    _seed_formula('PROD-CMP', [
        ('MP-CMP-1', 'M1', 100.0, 2000),
    ], lote_size_kg=2)
    pid = _seed_produccion('PROD-CMP', lotes=1)
    try:
        r1 = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                     headers=csrf_headers())
        assert r1.status_code == 200
        stock_post_iniciar = _stock_disponible('MP-CMP-1')
        assert stock_post_iniciar == 48000  # 50k - 2k

        r2 = cs.post(f'/api/programacion/programar/{pid}/completar',
                     json={}, headers=csrf_headers())
        # Completar debe procesar SIN error (skip MP, hace estado=completado)
        assert r2.status_code == 200, r2.data
        # Stock NO cambia (no doble descuento)
        assert _stock_disponible('MP-CMP-1') == 48000

        # Estado sí debe ser completado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute(
            "SELECT estado FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()[0]
        conn.close()
        assert estado == 'completado'
    finally:
        _cleanup('PROD-CMP', ['MP-CMP-1'], pid)


def test_iniciar_audit_log_registra_descuento(app, db_clean):
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-AUD-1', 'Auditest', 50000)
    _seed_formula('PROD-AUD', [
        ('MP-AUD-1', 'Auditest', 100.0, 3000),
    ], lote_size_kg=3)
    pid = _seed_produccion('PROD-AUD', lotes=1)
    try:
        cs.post(f'/api/programacion/programar/{pid}/iniciar',
                headers=csrf_headers())
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion, detalle FROM audit_log "
            "WHERE accion='INICIAR_PRODUCCION' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'luis'
        assert 'descontó' in row[2] or 'MPs' in row[2]
    finally:
        _cleanup('PROD-AUD', ['MP-AUD-1'], pid)


def test_iniciar_terminada_devuelve_idempotente(app, db_clean):
    """Si producción ya iniciada+terminada, iniciar es idempotente
    (devuelve 200 ya_iniciada, no toca nada)."""
    cs = _login(app, 'luis')
    pid = _seed_produccion('PROD-TERM-1', lotes=1)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        "UPDATE produccion_programada SET inicio_real_at=datetime('now','-1 hour'), "
        "fin_real_at=datetime('now') WHERE id=?", (pid,)
    )
    conn.commit(); conn.close()
    try:
        r = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                    headers=csrf_headers())
        # ya_iniciada → 200 idempotente
        assert r.status_code == 200
        d = r.get_json()
        assert d.get('ya_iniciada') is True
    finally:
        _cleanup(producto='PROD-TERM-1', prod_id=pid)


def test_dashboard_html_popup_stock_insuficiente_visible(app, db_clean):
    """UI tiene la funcion popup + el handler de errores con detalle."""
    cs = _login(app)
    body = cs.get('/inventarios').get_data(as_text=True)
    assert '_showStockInsuficientePopup' in body
    assert 'No se puede fabricar' in body
    assert 'popup-stock-insuf' in body
    # El handler debe usar el popup cuando hay faltantes
    assert 'd.faltantes && d.faltantes.length' in body


def test_api_produccion_devuelve_faltantes_si_sin_stock(app, db_clean):
    """Endpoint /api/produccion devuelve detalle de faltantes en 422
    para que el popup pueda renderizarse."""
    cs = _login(app, 'luis')
    _seed_mp_con_stock('MP-FALT-1', 'M1', 100)  # solo 100g
    _seed_formula('PROD-FALT', [
        ('MP-FALT-1', 'M1', 100.0, 5000),  # necesita 5000g
    ], lote_size_kg=5)
    try:
        r = cs.post('/api/produccion',
                    json={'producto': 'PROD-FALT', 'cantidad_kg': 5,
                          'operador': 'test'},
                    headers=csrf_headers())
        assert r.status_code == 422
        d = r.get_json()
        assert d['error'].lower().startswith('stock insuficiente')
        assert 'faltantes' in d
        assert len(d['faltantes']) >= 1
        f = d['faltantes'][0]
        # Cada faltante tiene los campos que el popup usa
        assert f['material'] == 'M1'
        assert f['requerido_g'] == 5000
        assert f['disponible_g'] == 100
        assert f['falta_g'] == 4900
    finally:
        _cleanup('PROD-FALT', ['MP-FALT-1'])


def test_iniciar_fefo_distribuye_entre_lotes_por_vencimiento(app, db_clean):
    """Con 2 lotes: el más cercano a vencer se consume primero."""
    cs = _login(app, 'luis')
    # Lote viejo (vence pronto): 1000g
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT OR REPLACE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo)
           VALUES ('MP-FEFO', 'FEFO test', 1)"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, fecha_vencimiento, operador, estado_lote)
           VALUES ('MP-FEFO', 'FEFO test', 1000, 'Entrada', date('now'),
                   'Lote viejo', 'LV-001', '2026-06-01', 'test', 'Aprobado')"""
    )
    # Lote nuevo (vence tarde): 5000g
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, fecha_vencimiento, operador, estado_lote)
           VALUES ('MP-FEFO', 'FEFO test', 5000, 'Entrada', date('now'),
                   'Lote nuevo', 'LN-001', '2028-12-31', 'test', 'Aprobado')"""
    )
    conn.commit(); conn.close()
    _seed_formula('PROD-FEFO', [
        ('MP-FEFO', 'FEFO test', 100.0, 1500),  # necesita 1500g
    ], lote_size_kg=1.5)
    pid = _seed_produccion('PROD-FEFO', lotes=1)
    try:
        r = cs.post(f'/api/programacion/programar/{pid}/iniciar',
                    headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        # Debe consumir 1000g del lote viejo + 500g del nuevo
        distrib = d['mps_descontadas'][0]['distribucion_fefo']
        # 2 entradas (1 por lote)
        assert len(distrib) == 2
        # Primera entrada: lote viejo
        assert distrib[0]['lote'] == 'LV-001'
        assert distrib[0]['cantidad_g'] == 1000
        # Segunda entrada: lote nuevo
        assert distrib[1]['lote'] == 'LN-001'
        assert distrib[1]['cantidad_g'] == 500
    finally:
        _cleanup('PROD-FEFO', ['MP-FEFO'], pid)
