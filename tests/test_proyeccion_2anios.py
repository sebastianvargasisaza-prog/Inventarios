"""16-jun · Plan rodante a 2 años (_proyectar_horizonte_2y).

Cada producto se proyecta anclado a su venta en Shopify (velocidad + tendencia) y a
su stock EFECTIVO = Shopify disponible + pipeline (lo producido ≤7d que aún no entra
a Shopify). Automático (cron 5:10), idempotente, NO toca lo ejecutado ni lo Fijo.
"""
import os
import sqlite3
import sys
import datetime as _dt


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _seed_producto(producto='PROD PROY 2A', sku='SKU-PROY', vel=10, stock=50,
                   lote_kg=30, factor_g=30, dias_venta=30):
    """Siembra un producto vendible: ventas_diarias (velocidad), mapa SKU, stock
    Shopify, presentación (factor g/u), config de planeación y fórmula (lote_size)."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # Auto-limpieza (db_clean no resetea estas tablas de config) → tests aislados
        conn.execute("CREATE TABLE IF NOT EXISTS ventas_diarias (sku TEXT, fecha TEXT, cantidad REAL)")
        for q, p in [("DELETE FROM ventas_diarias WHERE sku=?", (sku,)),
                     ("DELETE FROM sku_producto_map WHERE sku=?", (sku,)),
                     ("DELETE FROM stock_pt WHERE sku=?", (sku,)),
                     ("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (producto,)),
                     ("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,)),
                     ("DELETE FROM produccion_programada WHERE producto=?", (producto,))]:
            try:
                conn.execute(q, p)
            except Exception:
                pass
        hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
        for i in range(dias_venta):
            f = (hoy - _dt.timedelta(days=i)).isoformat()
            conn.execute("INSERT INTO ventas_diarias (sku,fecha,cantidad) VALUES (?,?,?)", (sku, f, vel))
        conn.execute("INSERT OR REPLACE INTO sku_producto_map (sku,producto_nombre,activo) VALUES (?,?,1)",
                     (sku, producto))
        conn.execute("INSERT INTO stock_pt (sku,descripcion,unidades_disponible,empresa,estado) "
                     "VALUES (?,?,?,?,?)", (sku, producto, stock, 'ANIMUS', 'activo'))
        # factor g/u sale del fallback por categoría ('suero' → 30 g/u),
        # consistente con lote_kg=30 → 1000 u/lote (evita NOT NULLs de presentaciones).
        conn.execute("INSERT INTO sku_planeacion_config (producto_nombre,categoria,cadencia_dias,"
                     "cobertura_target_dias,cobertura_min_dias,cobertura_max_dias,merma_pct,prioridad,activo) "
                     "VALUES (?,?,?,?,?,?,?,?,1)", (producto, 'suero', 30, 60, 20, 90, 5, 1))
        conn.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,?,1)",
                     (producto, lote_kg))
        conn.commit()
    finally:
        conn.close()


def _eos_proyeccion(producto='PROD PROY 2A'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT id, fecha_programada, observaciones FROM produccion_programada "
            "WHERE producto=? AND origen='eos_proyeccion' AND COALESCE(estado,'')<>'cancelado' "
            "ORDER BY fecha_programada", (producto,)).fetchall()
    finally:
        conn.close()


def test_proyeccion_genera_lotes_futuros(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    with app.app_context():
        res = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    assert res['creados'] >= 1, res
    lotes = _eos_proyeccion()
    assert len(lotes) == res['creados']
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date().isoformat()
    assert all(l[1][:10] >= hoy for l in lotes)   # todos futuros


def test_proyeccion_idempotente(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    with app.app_context():
        r1 = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
        r2 = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    # segunda corrida borra la previa y rehace → NO se acumula
    assert r2['creados'] == r1['creados']
    assert len(_eos_proyeccion()) == r1['creados']


def test_proyeccion_incluye_pipeline(app, db_clean):
    """Lo ya producido ≤7d (aún no en Shopify) cuenta como stock efectivo ANTES de
    proponer. Debe reflejarse en el cálculo (obs muestra el pipeline en unidades)."""
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto(stock=50)
    # producción real reciente: 30kg ejecutada hace 2 días → 30000/30 = 1000 u en pipeline
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    f2 = (_dt.datetime.utcnow() - _dt.timedelta(hours=5) - _dt.timedelta(days=2)).date().isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,"
                 "fin_real_at,inicio_real_at) VALUES (?,?,?,?,?,1,?,?)",
                 ('PROD PROY 2A', f2, 'completado', 'eos_retroactivo', 30, f2, f2))
    conn.commit(); conn.close()
    with app.app_context():
        res = _proyectar_horizonte_2y(get_db(), dias=300, usuario='test')
    assert res['creados'] >= 1
    lotes = _eos_proyeccion()
    # el pipeline (30 kg = 30000 g) quedó contado en el stock efectivo (visible en la obs)
    assert any('pipeline 30000' in (l[2] or '') for l in lotes), [l[2] for l in lotes][:3]


def test_proyeccion_sin_ventas_no_planea(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto(producto='PROD SIN VENTA', sku='SKU-SV', vel=0, dias_venta=0, stock=10)
    with app.app_context():
        _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    assert len(_eos_proyeccion('PROD SIN VENTA')) == 0   # sin venta → no inventa demanda


def test_verificar_volumenes_detecta_fuente(app, db_clean):
    """Paso 1: por SKU, el volumen fijado (sku) se distingue del adivinado (fallback)."""
    _api()
    from blueprints.plan import _verificar_volumenes_data
    from database import get_db
    # SKU con volumen fijado (200 ml) → fuente_vol 'sku'
    _seed_producto(producto='CON VOL', sku='SKU-CV', vel=5, lote_kg=30)
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("UPDATE sku_producto_map SET volumen_ml=200 WHERE sku='SKU-CV'")
    conn.commit(); conn.close()
    # SKU sin volumen → fallback por producto (categoría suero → 30), adivinado
    _seed_producto(producto='SIN VOL', sku='SKU-SV2', vel=5, lote_kg=30)
    with app.app_context():
        resumen, prods = _verificar_volumenes_data(get_db())
    by = {p['producto']: p for p in prods}
    cv = by['CON VOL']['skus'][0]
    sv = by['SIN VOL']['skus'][0]
    assert cv['fuente_vol'] == 'sku' and cv['volumen'] == 200
    assert sv['fuente_vol'].startswith('producto:') and sv['volumen'] == 30
    # demanda en gramos = velocidad × volumen (5 × 200 = 1000 g/d ; 5 × 30 = 150 g/d)
    assert by['CON VOL']['demanda_g_dia'] == 1000
    assert by['SIN VOL']['demanda_g_dia'] == 150
    assert resumen['volumen_completo'] >= 1 and resumen['volumen_adivinado'] >= 1


def test_set_volumen_sku_manda(app, db_clean):
    """Fijar el volumen de un SKU manda sobre el fallback (fuente 'sku')."""
    from .conftest import TEST_PASSWORD, csrf_headers
    _api()
    from blueprints.auto_plan import _volumen_sku
    from database import get_db
    _seed_producto(producto='VOL SKU', sku='SKU-VS', vel=5, lote_kg=30)
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.post('/api/plan/set-volumen', json={'sku': 'SKU-VS', 'volumen_ml': 200}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    with app.app_context():
        vol, fuente = _volumen_sku(get_db().cursor(), 'SKU-VS', 'VOL SKU')
        assert vol == 200 and fuente == 'sku'


def test_set_volumenes_bulk(app, db_clean):
    """Guardar TODOS los volúmenes de una (botón 'Guardar todos')."""
    from .conftest import TEST_PASSWORD, csrf_headers
    _api()
    from blueprints.auto_plan import _volumen_sku
    from database import get_db
    _seed_producto(producto='BULK A', sku='SKU-BA', vel=5, lote_kg=30)
    _seed_producto(producto='BULK B', sku='SKU-BB', vel=5, lote_kg=30)
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.post('/api/plan/set-volumenes-bulk', json={'items': [
        {'sku': 'SKU-BA', 'volumen_ml': 30}, {'sku': 'SKU-BB', 'volumen_ml': 10},
        {'sku': 'SKU-NOPE', 'volumen_ml': 5}]}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    assert j['guardados'] == 2 and 'SKU-NOPE' in j['no_encontrados']
    with app.app_context():
        assert _volumen_sku(get_db().cursor(), 'SKU-BA', 'BULK A') == (30, 'sku')
        assert _volumen_sku(get_db().cursor(), 'SKU-BB', 'BULK B') == (10, 'sku')


def test_sugerencia_adelanto_y_aceptar(app, db_clean):
    """La venta sube → cobertura corta vs un lote lejano → sugiere adelantar; al
    aceptar, mueve el lote (Fijo) y recalcula."""
    from .conftest import TEST_PASSWORD, csrf_headers
    _api()
    from blueprints.plan import _sugerencias_adelanto
    from database import get_db
    _seed_producto(producto='ADEL', sku='SKU-AD', vel=20, lote_kg=30, stock=50)
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("UPDATE sku_producto_map SET volumen_ml=30 WHERE sku='SKU-AD'")
    # próximo lote MUY lejano (90d) → queda tarde porque la venta es alta
    far = ((_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date() + _dt.timedelta(days=90)).isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                 "VALUES (?,?,?,?,?,1)", ('ADEL', far, 'pendiente', 'eos_proyeccion', 30))
    lote_id = conn.execute("SELECT id FROM produccion_programada WHERE producto='ADEL'").fetchone()[0]
    conn.commit(); conn.close()
    with app.app_context():
        sug = _sugerencias_adelanto(get_db())
    mine = [s for s in sug if s['producto'] == 'ADEL']
    assert mine, sug
    assert mine[0]['fecha_sugerida'] < far and mine[0]['dias_adelanto'] > 5
    assert mine[0]['mp_ok'] is None  # sin fórmula → MP desconocido

    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.post('/api/plan/aceptar-adelanto', json={'producto': 'ADEL'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        row = conn.execute("SELECT fecha_programada, origen FROM produccion_programada WHERE id=?", (lote_id,)).fetchone()
        assert row[0][:10] < far          # se movió antes
        assert row[1] == 'eos_plan'        # quedó Fijo (decisión aceptada)
    finally:
        conn.close()


def test_mp_alcanza_para_lote_con_faltante(app, db_clean):
    """Chequeo de MP: con fórmula y stock insuficiente → mp_ok False + faltante."""
    _api()
    from blueprints.plan import _mp_alcanza_para_lote
    from database import get_db
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=30)
    # maestro_mps PRIMERO (formula_items tiene trigger FK que exige material activo)
    conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPX-CHK','Mat X',1)")
    conn.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('MPCHK',10,1)")
    conn.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,cantidad_g_por_lote) "
                 "VALUES ('MPCHK','MPX-CHK','Mat X',5000)")
    # solo 1000 g en stock VIGENTE → falta para 5000
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                 "VALUES ('MPX-CHK','Mat X',1000,'Entrada','2026-06-10','L-CHK','VIGENTE')")
    conn.commit(); conn.close()
    with app.app_context():
        ok, faltantes = _mp_alcanza_para_lote(get_db(), 'MPCHK')
    assert ok is False and faltantes


def test_revisar_plan_detecta_vende_sin_plan(app, db_clean):
    """La revisión cruza producido + necesidad Shopify + plan; marca 'vende sin plan'
    y queda OK cuando hay lotes proyectados."""
    from .conftest import TEST_PASSWORD, csrf_headers
    _api()
    from blueprints.plan import _revisar_plan_data, _proyectar_horizonte_2y
    from database import get_db
    _seed_producto(producto='REV SINPLAN', sku='SKU-RSP', vel=10, lote_kg=30, stock=10)
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=30)
    conn.execute("UPDATE sku_producto_map SET volumen_ml=30 WHERE sku='SKU-RSP'")
    conn.commit(); conn.close()
    with app.app_context():
        # sin proyectar todavía → se vende pero no hay plan
        _, prods = _revisar_plan_data(get_db())
        row = [p for p in prods if p['producto'] == 'REV SINPLAN'][0]
        assert 'se vende pero SIN producción planeada' in row['razones']
        # proyectar SOLO ese producto → ahora tiene plan → ok
        _proyectar_horizonte_2y(get_db(), dias=200, usuario='test', solo_producto='REV SINPLAN')
        _, prods2 = _revisar_plan_data(get_db())
        row2 = [p for p in prods2 if p['producto'] == 'REV SINPLAN'][0]
        assert row2['n_proyectados'] >= 1
        assert 'se vende pero SIN producción planeada' not in row2['razones']

    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.get('/admin/revisar-plan')
    assert r.status_code == 200 and b'Revisar plan' in r.data


def test_set_volumen_sku_inexistente_404(app, db_clean):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.post('/api/plan/set-volumen', json={'sku': 'SKU-NOEXISTE-XYZ', 'volumen_ml': 50}, headers=csrf_headers())
    assert r.status_code == 404, r.data[:200]


def test_verificar_volumenes_page_render(app, db_clean):
    from .conftest import TEST_PASSWORD, csrf_headers
    _seed_producto(producto='PROD PAGINA', sku='SKU-PG', vel=5, lote_kg=30)
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    r = c.get('/admin/verificar-volumenes')
    assert r.status_code == 200
    assert b'Verificar vol' in r.data
    assert 'PROD PAGINA'.encode() in r.data


def test_proyeccion_no_toca_fijo_ni_ejecutado(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    fut = ((_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date() + _dt.timedelta(days=15)).isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                 "VALUES (?,?,?,?,?,1)", ('PROD PROY 2A', fut, 'pendiente', 'eos_plan', 30))
    fijo = conn.execute("SELECT id FROM produccion_programada WHERE origen='eos_plan' AND producto='PROD PROY 2A'").fetchone()[0]
    ej = ((_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date() - _dt.timedelta(days=3)).isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
                 "VALUES (?,?,?,?,?,1,?)", ('PROD PROY 2A', ej, 'en_proceso', 'eos_proyeccion', 30, ej))
    ejec = conn.execute("SELECT id FROM produccion_programada WHERE origen='eos_proyeccion' AND inicio_real_at IS NOT NULL").fetchone()[0]
    conn.commit(); conn.close()
    with app.app_context():
        _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # Fijo intacto
        assert conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (fijo,)).fetchone()[0] == 'pendiente'
        # eos_proyeccion ejecutado NO se borra (idempotencia solo borra NO ejecutado)
        assert conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (ejec,)).fetchone()[0] == 'en_proceso'
    finally:
        conn.close()
