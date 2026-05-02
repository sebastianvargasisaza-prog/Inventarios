"""Tests CERO SESGO · helpers MEE + fixes en mee_ajustar / mee_anular.

Sebastián 2-may-2026: planta "tener cero sesgo" en MP y MEE.

Bug encontrado: mee_ajustar_stock perdía el signo del ajuste (siempre
tipo='Ajuste' cantidad=abs(delta)). Resultado: drift permanente entre
maestro_mee.stock_actual (correcto) y SUM(movimientos_mee) (siempre
sumaba cantidad, nunca restaba).

Tests garantizan:
1. Helpers stock_mee_persisted/calculated/drift retornan valores correctos
2. mee_ajustar_stock crea Entrada/Salida según signo del delta
3. drift = 0 después de un ajuste (cero sesgo)
4. mee_anular_movimiento maneja cada tipo correctamente
5. Anular un Ajuste legacy se rechaza con 422 (no puede revertir)
6. aplicar_movimiento_mee es atómico y consistente
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


def _seed_mee(conn, codigo, stock_inicial):
    """Crea un MEE con stock conocido en maestro_mee + un movimiento Entrada
    que justifica ese stock (drift inicial = 0)."""
    conn.execute("DELETE FROM maestro_mee WHERE codigo=?", (codigo,))
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (codigo,))
    conn.execute("""INSERT INTO maestro_mee
        (codigo, descripcion, categoria, stock_actual, unidad)
        VALUES (?, ?, 'Test', ?, 'und')""",
        (codigo, f'Test {codigo}', stock_inicial))
    if stock_inicial > 0:
        conn.execute("""INSERT INTO movimientos_mee
            (mee_codigo, tipo, cantidad, observaciones, responsable, fecha)
            VALUES (?, 'Entrada', ?, 'seed', 'test', datetime('now'))""",
            (codigo, stock_inicial))
    conn.commit()


def _cleanup_mee(conn, codigo):
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (codigo,))
    conn.execute("DELETE FROM maestro_mee WHERE codigo=?", (codigo,))
    conn.commit()


# ─── Helpers stock_mee_* ─────────────────────────────────────────────

def test_stock_mee_persisted_lee_maestro(app, db_clean):
    from inventario_helpers import stock_mee_persisted
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-PERS-T', 1500)
    try:
        assert stock_mee_persisted(conn, 'MEE-PERS-T') == 1500.0
    finally:
        _cleanup_mee(conn, 'MEE-PERS-T'); conn.close()


def test_stock_mee_persisted_inexistente_devuelve_0(app, db_clean):
    from inventario_helpers import stock_mee_persisted
    conn = sqlite3.connect(os.environ["DB_PATH"])
    assert stock_mee_persisted(conn, 'MEE-NO-EXISTE') == 0.0
    conn.close()


def test_stock_mee_calculated_suma_entradas_resta_salidas(app, db_clean):
    from inventario_helpers import stock_mee_calculated
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-CALC-T', 0)
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-CALC-T','Entrada',1000,datetime('now'))")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-CALC-T','Entrada',500,datetime('now'))")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-CALC-T','Salida',200,datetime('now'))")
    conn.commit()
    try:
        # 1000 + 500 - 200 = 1300
        assert stock_mee_calculated(conn, 'MEE-CALC-T') == 1300.0
    finally:
        _cleanup_mee(conn, 'MEE-CALC-T'); conn.close()


def test_stock_mee_calculated_excluye_anulados(app, db_clean):
    """Movimientos con anulado=1 no cuentan."""
    from inventario_helpers import stock_mee_calculated
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-ANUL-T', 0)
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha,anulado) VALUES ('MEE-ANUL-T','Entrada',500,datetime('now'),0)")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha,anulado) VALUES ('MEE-ANUL-T','Entrada',300,datetime('now'),1)")
    conn.commit()
    try:
        assert stock_mee_calculated(conn, 'MEE-ANUL-T') == 500.0
    finally:
        _cleanup_mee(conn, 'MEE-ANUL-T'); conn.close()


def test_stock_mee_drift_detecta_inconsistencia(app, db_clean):
    """Si stock_actual no matchea SUM(movimientos), drift != 0."""
    from inventario_helpers import stock_mee_drift
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Stock_actual=1000 pero solo movimientos de 600 → drift +400
    conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-DRIFT-T'")
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-DRIFT-T'")
    conn.execute("INSERT INTO maestro_mee (codigo,descripcion,stock_actual) VALUES ('MEE-DRIFT-T','Test',1000)")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-DRIFT-T','Entrada',600,datetime('now'))")
    conn.commit()
    try:
        assert stock_mee_drift(conn, 'MEE-DRIFT-T') == 400.0
    finally:
        _cleanup_mee(conn, 'MEE-DRIFT-T'); conn.close()


# ─── aplicar_movimiento_mee · helper canónico ────────────────────────

def test_aplicar_movimiento_mee_atomico_entrada(app, db_clean):
    from inventario_helpers import aplicar_movimiento_mee, stock_mee_drift
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-APL-T1', 100)
    try:
        result = aplicar_movimiento_mee(conn, 'MEE-APL-T1', 'Entrada', 50,
                                         observaciones='test entrada', responsable='test')
        conn.commit()
        assert result['stock_anterior'] == 100
        assert result['stock_nuevo'] == 150
        assert stock_mee_drift(conn, 'MEE-APL-T1') == 0  # ATÓMICO · drift = 0
    finally:
        _cleanup_mee(conn, 'MEE-APL-T1'); conn.close()


def test_aplicar_movimiento_mee_atomico_salida(app, db_clean):
    from inventario_helpers import aplicar_movimiento_mee, stock_mee_drift
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-APL-T2', 200)
    try:
        result = aplicar_movimiento_mee(conn, 'MEE-APL-T2', 'Salida', 80,
                                         observaciones='test salida', responsable='test')
        conn.commit()
        assert result['stock_anterior'] == 200
        assert result['stock_nuevo'] == 120
        assert stock_mee_drift(conn, 'MEE-APL-T2') == 0
    finally:
        _cleanup_mee(conn, 'MEE-APL-T2'); conn.close()


def test_aplicar_movimiento_mee_clamp_no_negativo(app, db_clean):
    """Salida que excede stock se clampa a 0 (no permite negativo)."""
    from inventario_helpers import aplicar_movimiento_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-APL-T3', 50)
    try:
        result = aplicar_movimiento_mee(conn, 'MEE-APL-T3', 'Salida', 100,
                                         observaciones='oversold', responsable='test')
        assert result['stock_nuevo'] == 0  # clamped, no -50
    finally:
        _cleanup_mee(conn, 'MEE-APL-T3'); conn.close()


def test_aplicar_movimiento_mee_rechaza_tipo_invalido(app, db_clean):
    from inventario_helpers import aplicar_movimiento_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-APL-T4', 100)
    try:
        with pytest.raises(ValueError, match="tipo debe ser"):
            aplicar_movimiento_mee(conn, 'MEE-APL-T4', 'Ajuste', 50)
        with pytest.raises(ValueError, match="tipo debe ser"):
            aplicar_movimiento_mee(conn, 'MEE-APL-T4', 'Foo', 50)
    finally:
        _cleanup_mee(conn, 'MEE-APL-T4'); conn.close()


def test_aplicar_movimiento_mee_rechaza_cantidad_no_positiva(app, db_clean):
    from inventario_helpers import aplicar_movimiento_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-APL-T5', 100)
    try:
        with pytest.raises(ValueError, match="cantidad debe ser > 0"):
            aplicar_movimiento_mee(conn, 'MEE-APL-T5', 'Entrada', 0)
        with pytest.raises(ValueError, match="cantidad debe ser > 0"):
            aplicar_movimiento_mee(conn, 'MEE-APL-T5', 'Entrada', -10)
    finally:
        _cleanup_mee(conn, 'MEE-APL-T5'); conn.close()


def test_aplicar_movimiento_mee_rechaza_codigo_no_existe(app, db_clean):
    from inventario_helpers import aplicar_movimiento_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    with pytest.raises(ValueError, match="no existe en maestro_mee"):
        aplicar_movimiento_mee(conn, 'MEE-NO-EXISTE-XYZ', 'Entrada', 50)
    conn.close()


# ─── mee_ajustar_stock · fix preserva signo ──────────────────────────

def test_mee_ajustar_positivo_inserta_entrada(app, db_clean):
    """Subir stock 100 → 150 debe insertar Entrada (no Ajuste)."""
    from inventario_helpers import stock_mee_drift, stock_mee_calculated
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AJU-T1', 100)
    conn.close()
    try:
        r = c.post("/api/mee/MEE-AJU-T1/ajustar",
                   json={"cantidad_nueva": 150, "motivo": "Conteo físico encontró +50"},
                   headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        # Verificar tipo del último movimiento
        tipo = conn.execute(
            "SELECT tipo FROM movimientos_mee WHERE mee_codigo='MEE-AJU-T1' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        assert tipo == 'Entrada'  # NO 'Ajuste'
        # Drift = 0 porque calc ahora suma correctamente la Entrada
        assert stock_mee_drift(conn, 'MEE-AJU-T1') == 0
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AJU-T1'); conn.close()


def test_mee_ajustar_negativo_inserta_salida(app, db_clean):
    """Bajar stock 200 → 150 debe insertar Salida."""
    from inventario_helpers import stock_mee_drift
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AJU-T2', 200)
    conn.close()
    try:
        r = c.post("/api/mee/MEE-AJU-T2/ajustar",
                   json={"cantidad_nueva": 150, "motivo": "Merma encontrada en conteo"},
                   headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        tipo, cantidad = conn.execute(
            "SELECT tipo, cantidad FROM movimientos_mee WHERE mee_codigo='MEE-AJU-T2' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert tipo == 'Salida'
        assert cantidad == 50  # abs(150 - 200)
        assert stock_mee_drift(conn, 'MEE-AJU-T2') == 0
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AJU-T2'); conn.close()


def test_mee_ajustar_sin_cambio_no_inserta_movimiento(app, db_clean):
    """Si delta=0, no insertar movimiento (idempotente)."""
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AJU-T3', 100)
    conn.close()
    try:
        r = c.post("/api/mee/MEE-AJU-T3/ajustar",
                   json={"cantidad_nueva": 100, "motivo": "Confirmando conteo"},
                   headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        # Debe haber solo el movimiento seed (1), no un nuevo movimiento
        n = conn.execute(
            "SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo='MEE-AJU-T3'"
        ).fetchone()[0]
        assert n == 1  # solo el seed Entrada inicial
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AJU-T3'); conn.close()


def test_mee_ajustar_obs_marca_ajuste_manual(app, db_clean):
    """Las observaciones del movimiento deben marcar 'AJUSTE MANUAL' para
    que reportes lo distingan de movimientos operativos."""
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AJU-T4', 100)
    conn.close()
    try:
        r = c.post("/api/mee/MEE-AJU-T4/ajustar",
                   json={"cantidad_nueva": 120, "motivo": "Test motivo"},
                   headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        obs = conn.execute(
            "SELECT observaciones FROM movimientos_mee WHERE mee_codigo='MEE-AJU-T4' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        assert 'AJUSTE MANUAL' in obs
        assert 'Test motivo' in obs
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AJU-T4'); conn.close()


# ─── mee_anular_movimiento · guard contra Ajuste legacy ──────────────

def test_anular_entrada_revierte_stock(app, db_clean):
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AN-T1', 0)
    cur = conn.execute("""INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha)
                          VALUES ('MEE-AN-T1','Entrada',500,datetime('now'))""")
    mov_id = cur.lastrowid
    conn.execute("UPDATE maestro_mee SET stock_actual=500 WHERE codigo='MEE-AN-T1'")
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/mee/anular/{mov_id}",
                   json={"motivo": "Error de captura"}, headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        stock = conn.execute("SELECT stock_actual FROM maestro_mee WHERE codigo='MEE-AN-T1'").fetchone()[0]
        assert stock == 0  # Entrada de 500 revertida → 500 - 500 = 0
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AN-T1'); conn.close()


def test_anular_ajuste_legacy_rechazado_422(app, db_clean):
    """No se puede anular un tipo='Ajuste' legacy porque el signo no se
    preservaba. Debe rechazar con 422 y mensaje claro."""
    c = _login(app, "luis")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    _seed_mee(conn, 'MEE-AN-T2', 100)
    cur = conn.execute("""INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha)
                          VALUES ('MEE-AN-T2','Ajuste',50,datetime('now'))""")
    mov_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/mee/anular/{mov_id}",
                   json={"motivo": "Intento anular ajuste"}, headers=csrf_headers())
        assert r.status_code == 422
        d = r.get_json()
        assert d.get('codigo') == 'AJUSTE_LEGACY_NO_ANULABLE'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_mee(conn, 'MEE-AN-T2'); conn.close()
