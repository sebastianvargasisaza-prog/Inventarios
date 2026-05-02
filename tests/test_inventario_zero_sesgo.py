"""Tests CERO SESGO · helpers canónicos de inventario MP.

Sebastián 2-may-2026: "planta debe funcionar perfecto · cero sesgo".

Audit zero-error encontró 6+ implementaciones inconsistentes del cálculo
de stock que usaban tipos inexistentes ('Ingreso','Consumo') y devolvían
valores negativos siempre · semáforo dashboard, gate producción, IA de
compras, conteo cíclico — todos rotos.

Estos tests garantizan que:
1. stock_mp_total y stock_mp_disponible cuentan correctamente
2. Cuarentena se excluye de "disponible" pero suma en "total"
3. Vencido/Rechazado se excluyen de "disponible"
4. Tipos legacy ('Ajuste +'/'Ajuste -') funcionan
5. La regresión a 'Ingreso'/'Consumo' nunca vuelve
6. prog_cancelar_evento no permite cancelar producciones completadas
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


# ─── Helpers stock_mp_total / stock_mp_disponible ────────────────────

def _seed_mp(conn, codigo, movs):
    """Helper: limpia movs del MP y siembra los pasados.

    movs: lista de tuplas (tipo, cantidad, estado_lote).
    """
    conn.execute("DELETE FROM movimientos WHERE material_id=?", (codigo,))
    for tipo, cant, estado in movs:
        conn.execute("""
            INSERT INTO movimientos
              (material_id, material_nombre, cantidad, tipo, fecha, estado_lote)
            VALUES (?, ?, ?, ?, datetime('now'), ?)
        """, (codigo, f'Test {codigo}', cant, tipo, estado))
    conn.commit()


def test_stock_total_suma_entradas_resta_salidas(app, db_clean):
    from inventario_helpers import stock_mp_total
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mp(conn, 'MP-CERO-T1', [
        ('Entrada', 1000, 'Aprobado'),
        ('Entrada', 500, 'Aprobado'),
        ('Salida', 200, 'Aprobado'),
    ])
    try:
        assert stock_mp_total(conn, 'MP-CERO-T1') == 1300.0  # 1000 + 500 - 200
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T1'")
        conn.commit(); conn.close()


def test_stock_total_incluye_cuarentena(app, db_clean):
    """stock_mp_total debe incluir lotes en cuarentena (visión completa)."""
    from inventario_helpers import stock_mp_total
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mp(conn, 'MP-CERO-T2', [
        ('Entrada', 800, 'Aprobado'),
        ('Entrada', 200, 'CUARENTENA'),
    ])
    try:
        assert stock_mp_total(conn, 'MP-CERO-T2') == 1000.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T2'")
        conn.commit(); conn.close()


def test_stock_disponible_excluye_cuarentena(app, db_clean):
    """stock_mp_disponible NO debe contar cuarentena."""
    from inventario_helpers import stock_mp_disponible
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mp(conn, 'MP-CERO-T3', [
        ('Entrada', 800, 'Aprobado'),
        ('Entrada', 200, 'CUARENTENA'),
        ('Salida', 100, 'Aprobado'),
    ])
    try:
        # Disponible = 800 (Aprobado) - 100 (Salida) = 700
        # NO 1000 - 100 = 900 (cuarentena no cuenta)
        assert stock_mp_disponible(conn, 'MP-CERO-T3') == 700.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T3'")
        conn.commit(); conn.close()


def test_stock_disponible_excluye_vencido_rechazado(app, db_clean):
    from inventario_helpers import stock_mp_disponible
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mp(conn, 'MP-CERO-T4', [
        ('Entrada', 1000, 'Aprobado'),
        ('Entrada', 300, 'VENCIDO'),
        ('Entrada', 200, 'RECHAZADO'),
    ])
    try:
        assert stock_mp_disponible(conn, 'MP-CERO-T4') == 1000.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T4'")
        conn.commit(); conn.close()


def test_stock_estado_lote_vacio_o_null_se_considera_aprobado(app, db_clean):
    """Lotes legacy sin estado_lote NULL/'' se consideran disponibles."""
    from inventario_helpers import stock_mp_disponible
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T5'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,estado_lote) VALUES ('MP-CERO-T5','Test',500,'Entrada',datetime('now'),NULL)")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,estado_lote) VALUES ('MP-CERO-T5','Test',300,'Entrada',datetime('now'),'')")
    conn.commit()
    try:
        assert stock_mp_disponible(conn, 'MP-CERO-T5') == 800.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T5'")
        conn.commit(); conn.close()


def test_stock_legacy_ajuste_signed_funciona(app, db_clean):
    """Tipos legacy 'Ajuste +'/'Ajuste -' (animus) deben funcionar."""
    from inventario_helpers import stock_mp_total
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mp(conn, 'MP-CERO-T6', [
        ('Entrada', 1000, 'Aprobado'),
        ('Ajuste +', 100, 'Aprobado'),
        ('Ajuste -', 50, 'Aprobado'),
        ('Ajuste', 200, 'Aprobado'),  # legacy sin signo, contado como entrada
    ])
    try:
        # 1000 + 100 - 50 + 200 = 1250
        assert stock_mp_total(conn, 'MP-CERO-T6') == 1250.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CERO-T6'")
        conn.commit(); conn.close()


def test_regresion_no_volver_a_ingreso_consumo():
    """Test de regresión: ningún archivo del backend debe usar
    'Ingreso'/'Consumo' como tipo de movimiento (no existen en BD).
    """
    import pathlib
    # Buscar en blueprints + helpers
    api_root = pathlib.Path(__file__).parent.parent / 'api'
    offending = []
    for py in api_root.rglob('*.py'):
        if py.name in ('inventario_helpers.py', 'test_inventario_zero_sesgo.py'):
            continue  # los helpers documentan los tipos legacy y este test verifica
        text = py.read_text(encoding='utf-8', errors='ignore')
        # Si tiene SQL CASE WHEN tipo IN ('Ingreso',...) → bug
        if "tipo IN ('Ingreso'" in text or "tipo IN ( 'Ingreso'" in text:
            offending.append(str(py.relative_to(api_root)))
    assert not offending, (
        f"Archivos con SQL roto (usan 'Ingreso' que NO existe en data): {offending}. "
        f"Usar inventario_helpers.stock_mp_total/disponible en su lugar."
    )


# ─── prog_cancelar_evento guard ──────────────────────────────────────

def test_cancelar_pendiente_funciona(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado)
        VALUES ('PROD-CANCEL-T1', date('now'), 1, 'pendiente')""")
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.delete(f"/api/programacion/programar/{pid}",
                     headers=csrf_headers())
        assert r.status_code == 200
        # Verificar estado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute("SELECT estado FROM produccion_programada WHERE id=?",
                              (pid,)).fetchone()[0]
        conn.close()
        assert estado == 'cancelado'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_cancelar_completada_devuelve_409(app, db_clean):
    """No se puede cancelar una producción que ya descontó inventario."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Verificar que la columna inventario_descontado_at exista
    cols = [r[1] for r in conn.execute("PRAGMA table_info(produccion_programada)").fetchall()]
    if 'inventario_descontado_at' not in cols:
        pytest.skip("Schema sin inventario_descontado_at (migración pendiente)")
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado, inventario_descontado_at)
        VALUES ('PROD-COMPLETA-T', date('now'), 1, 'completado', datetime('now'))""")
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.delete(f"/api/programacion/programar/{pid}",
                     headers=csrf_headers())
        assert r.status_code == 409
        data = r.get_json()
        assert data.get('codigo') == 'YA_COMPLETADA'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_cancelar_inexistente_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.delete("/api/programacion/programar/9999999",
                 headers=csrf_headers())
    assert r.status_code == 404


def test_cancelar_idempotente(app, db_clean):
    """Cancelar 2 veces no debe romper · segunda devuelve ya_cancelado=True."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado)
        VALUES ('PROD-IDEMP-T', date('now'), 1, 'cancelado')""")
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.delete(f"/api/programacion/programar/{pid}",
                     headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d.get('ya_cancelado') is True
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


# ─── End-to-end · listo-producir refleja stock real ──────────────────

def test_listo_producir_refleja_stock_real(app, db_clean):
    """El semáforo /api/planta/listo-producir debe devolver disponible_g real,
    no el -200 fantasma del bug anterior."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Sembrar fórmula + MP con stock conocido
    conn.execute("""INSERT OR IGNORE INTO formula_headers
        (producto_nombre, lote_size_kg) VALUES ('PROD-LISTO-T', 1.0)""")
    conn.execute("DELETE FROM formula_items WHERE producto_nombre='PROD-LISTO-T'")
    conn.execute("""INSERT INTO formula_items
        (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote)
        VALUES ('PROD-LISTO-T', 'MP-LISTO-T', 'MP listo test', 50, 500)""")
    # Stock: 1000g aprobado + 200g cuarentena · disponible = 1000
    _seed_mp(conn, 'MP-LISTO-T', [
        ('Entrada', 1000, 'Aprobado'),
        ('Entrada', 200, 'CUARENTENA'),
    ])
    try:
        r = c.get("/api/planta/listo-producir/PROD-LISTO-T?lotes=1")
        assert r.status_code == 200
        d = r.get_json()
        items = d.get('items', [])
        mp = next((i for i in items if i['codigo_mp'] == 'MP-LISTO-T'), None)
        assert mp is not None
        assert mp['disponible_g'] == 1000  # NO 1200 (cuarentena excluida) ni -200 (bug viejo)
        assert mp['requerido_g'] == 500
        assert mp['status'] == 'ok'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM formula_items WHERE producto_nombre='PROD-LISTO-T'")
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre='PROD-LISTO-T'")
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-LISTO-T'")
        conn.commit(); conn.close()


def test_listo_producir_deficit_real(app, db_clean):
    """Si el stock disponible es < requerido, status='deficit'."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO formula_headers
        (producto_nombre, lote_size_kg) VALUES ('PROD-DEF-T', 2.0)""")
    conn.execute("DELETE FROM formula_items WHERE producto_nombre='PROD-DEF-T'")
    conn.execute("""INSERT INTO formula_items
        (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote)
        VALUES ('PROD-DEF-T', 'MP-DEF-T', 'MP def test', 50, 1000)""")
    # Solo 100g aprobado · necesita 1000 → deficit
    _seed_mp(conn, 'MP-DEF-T', [
        ('Entrada', 100, 'Aprobado'),
    ])
    try:
        r = c.get("/api/planta/listo-producir/PROD-DEF-T?lotes=1")
        d = r.get_json()
        mp = next(i for i in d['items'] if i['codigo_mp'] == 'MP-DEF-T')
        assert mp['disponible_g'] == 100
        assert mp['status'] == 'deficit'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM formula_items WHERE producto_nombre='PROD-DEF-T'")
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre='PROD-DEF-T'")
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-DEF-T'")
        conn.commit(); conn.close()
