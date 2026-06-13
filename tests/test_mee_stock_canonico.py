"""Bodega MEE (envases) · stock CANÓNICO = SUM(movimientos_mee), no el cache
maestro_mee.stock_actual (que driftea · hay backfill de drift en admin).
12-jun · paridad con el principio de MP (stock = SUM(movimientos)).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _seed_mee(cod, stock_cache, stock_min=0):
    _exec("INSERT OR REPLACE INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,stock_actual,stock_minimo,unidad) "
          "VALUES (?,?, 'Tapa','China','Activo',?,?,'und')", (cod, 'Env ' + cod, stock_cache, stock_min))


def _mov(cod, tipo, cant, anulado=0):
    _exec("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha,anulado) "
          "VALUES (?,?,?,datetime('now'),?)", (cod, tipo, cant, anulado))


def test_mee_stock_es_canonico_no_cache(app, db_clean):
    """stock_actual cache=5000 pero movimientos suman 1200 → la vista muestra 1200."""
    _seed_mee('ENV-DRIFT', 5000, stock_min=0)
    _mov('ENV-DRIFT', 'Entrada', 1000)
    _mov('ENV-DRIFT', 'Entrada', 500)
    _mov('ENV-DRIFT', 'Salida', 300)   # neto = 1200

    c = _login(app)
    data = c.get('/api/mee/stock').get_json()
    items = data['items'] if isinstance(data, dict) and 'items' in data else data
    it = next((x for x in items if x['codigo'] == 'ENV-DRIFT'), None)
    assert it is not None, f"ENV-DRIFT debe salir · {data}"
    assert abs(it['stock_actual'] - 1200) < 0.5, \
        f"debe mostrar el canónico SUM=1200, no el cache 5000 · fue {it['stock_actual']}"


def test_mee_stock_cuenta_ajuste(app, db_clean):
    """El Ajuste suma (igual que _mee_stock_real)."""
    _seed_mee('ENV-AJ', 0)
    _mov('ENV-AJ', 'Entrada', 1000)
    _mov('ENV-AJ', 'Ajuste', 200)      # neto = 1200
    c = _login(app)
    items = c.get('/api/mee/stock').get_json()
    items = items['items'] if isinstance(items, dict) and 'items' in items else items
    it = next((x for x in items if x['codigo'] == 'ENV-AJ'), None)
    assert abs(it['stock_actual'] - 1200) < 0.5, f"Ajuste debe sumar · {it}"


def test_mee_stock_ignora_anulado(app, db_clean):
    _seed_mee('ENV-AN', 0)
    _mov('ENV-AN', 'Entrada', 1000)
    _mov('ENV-AN', 'Entrada', 9999, anulado=1)   # anulado no cuenta
    c = _login(app)
    items = c.get('/api/mee/stock').get_json()
    items = items['items'] if isinstance(items, dict) and 'items' in items else items
    it = next((x for x in items if x['codigo'] == 'ENV-AN'), None)
    assert abs(it['stock_actual'] - 1000) < 0.5, f"movimiento anulado no debe contar · {it}"


def test_mee_alerta_bajo_minimo_usa_canonico(app, db_clean):
    """La alerta de quiebre usa el stock canónico, no el cache (M5)."""
    # cache dice 5000 (ok), pero el real (movimientos) es 100 < min 1000 → debe alertar
    _seed_mee('ENV-LOW', 5000, stock_min=1000)
    _mov('ENV-LOW', 'Entrada', 100)
    c = _login(app)
    data = c.get('/api/mee/stock').get_json()
    items = data['items'] if isinstance(data, dict) and 'items' in data else data
    it = next((x for x in items if x['codigo'] == 'ENV-LOW'), None)
    assert abs(it['stock_actual'] - 100) < 0.5, f"stock real = 100 · {it}"
    assert it['alerta'] in ('critico', 'bajo'), \
        f"con 100 < min 1000 debe alertar bajo/crítico, no 'ok' · {it}"


def test_abc_mee_consumo_no_revienta(app, db_clean):
    """ABC de MEE en modo consumo usaba columna 'codigo_mee' inexistente → 500.
    La columna real es mee_codigo."""
    _seed_mee('ENV-ABC', 0)
    _mov('ENV-ABC', 'Entrada', 1000)
    _mov('ENV-ABC', 'Salida', 200)
    c = _login(app)
    r = c.get('/api/analisis-abc?tipo_material=MEE&modo=consumo_90d')
    assert r.status_code == 200, f"ABC MEE consumo no debe dar 500 · {r.status_code} {r.data[:200]}"
