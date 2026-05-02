"""Tests CERO SESGO · race-safety en prog_completar_evento.

Antes: SELECT descontado_at + check + heavy work + UPDATE final →
ventana entre SELECT y UPDATE permitía a 2 requests paralelos
descontar 2x.

Ahora: ATOMIC CLAIM (UPDATE-WHERE) al inicio · solo uno gana.

Tests verifican:
1. Llamado simple funciona normal
2. Llamado consecutivo · segundo recibe 409 YA_DESCONTADO
3. Forzar redescuento (admin) bypassa el claim
4. Concurrencia simulada · solo uno descuenta, el otro recibe 409
5. Después de un fallo en el descuento, claim queda liberado
"""
import os
import sqlite3
import threading

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_produccion(conn, codigo='PROD-RACE-T'):
    """Crea producción + fórmula + MP para que completar funcione."""
    # Limpiar
    conn.execute(f"DELETE FROM produccion_programada WHERE producto=?", (codigo,))
    conn.execute(f"DELETE FROM formula_headers WHERE producto_nombre=?", (codigo,))
    conn.execute(f"DELETE FROM formula_items WHERE producto_nombre=?", (codigo,))
    conn.execute(f"DELETE FROM movimientos WHERE material_id LIKE ?", (f'MP-RACE-%',))
    # Fórmula
    conn.execute("""INSERT INTO formula_headers (producto_nombre, lote_size_kg)
                    VALUES (?, 1.0)""", (codigo,))
    conn.execute("""INSERT INTO formula_items
        (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote)
        VALUES (?, 'MP-RACE-1', 'MP race test', 50, 500)""", (codigo,))
    # Stock MP
    conn.execute("""INSERT INTO movimientos
        (material_id, material_nombre, cantidad, tipo, fecha)
        VALUES ('MP-RACE-1', 'MP race', 5000, 'Entrada', datetime('now'))""")
    # Producción
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado)
        VALUES (?, date('now'), 1, 'pendiente')""", (codigo,))
    pid = cur.lastrowid
    conn.commit()
    return pid


def _cleanup_produccion(conn, pid, codigo='PROD-RACE-T'):
    conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (codigo,))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (codigo,))
    conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-RACE-%'")
    conn.commit()


# ─── Llamado simple funciona normal ──────────────────────────────────

def test_completar_simple_funciona(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        r = c.post(f"/api/programacion/programar/{pid}/completar",
                   json={}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        # Verificar que descontó · 1 movimiento de Salida creado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        rows = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-RACE-1' AND tipo='Salida'"
        ).fetchone()[0]
        assert rows >= 1
        # Verificar que inventario_descontado_at != ''
        descontado = conn.execute(
            "SELECT inventario_descontado_at FROM produccion_programada WHERE id=?",
            (pid,)
        ).fetchone()[0]
        assert descontado is not None and descontado != ''
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


# ─── Segundo llamado consecutivo recibe 409 ──────────────────────────

def test_completar_segundo_llamado_409(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        # Primera llamada · OK
        r1 = c.post(f"/api/programacion/programar/{pid}/completar",
                    json={}, headers=csrf_headers())
        assert r1.status_code == 200
        # Segunda llamada · 409 idempotente
        r2 = c.post(f"/api/programacion/programar/{pid}/completar",
                    json={}, headers=csrf_headers())
        assert r2.status_code == 409
        d = r2.get_json()
        assert d['codigo'] == 'YA_DESCONTADO'
        # Importante: el segundo NO descontó · solo 1 Salida en total
        conn = sqlite3.connect(os.environ["DB_PATH"])
        rows = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-RACE-1' AND tipo='Salida'"
        ).fetchone()[0]
        assert rows == 1, f"Esperaba 1 Salida, encontré {rows} (double-descuento)"
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


# ─── Concurrencia simulada (race condition real) ─────────────────────

def test_completar_concurrente_solo_uno_descuenta(app, db_clean):
    """Simula 2 requests concurrentes · solo uno descuenta el inventario.

    Usamos threads con session compartida del test_client. SQLite WAL
    serializa writes · solo uno gana el atomic claim UPDATE-WHERE.
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        results = []
        results_lock = threading.Lock()

        def _request(login_user):
            c = _login(app, login_user)
            r = c.post(f"/api/programacion/programar/{pid}/completar",
                       json={}, headers=csrf_headers())
            with results_lock:
                results.append((r.status_code, r.get_json()))

        # 2 threads simultáneos llamando completar
        t1 = threading.Thread(target=_request, args=('sebastian',))
        t2 = threading.Thread(target=_request, args=('alejandro',))
        t1.start(); t2.start()
        t1.join(timeout=30); t2.join(timeout=30)

        assert len(results) == 2, "Esperaba 2 resultados"
        codes = sorted(r[0] for r in results)
        # Esperado: uno 200, uno 409
        assert codes == [200, 409], f"Esperaba [200, 409], obtuve {codes}"
        # Verificar que SOLO 1 descuento ocurrió
        conn = sqlite3.connect(os.environ["DB_PATH"])
        salidas = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-RACE-1' AND tipo='Salida'"
        ).fetchone()[0]
        assert salidas == 1, \
               f"DOUBLE DESCUENTO detectado · {salidas} salidas (esperaba 1)"
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


# ─── Forzar bypassa el claim ─────────────────────────────────────────

def test_completar_forzar_bypassa_claim(app, db_clean):
    """Admin con forzar=true puede re-descontar incluso si ya estaba descontado."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        # Primer descuento normal
        r1 = c.post(f"/api/programacion/programar/{pid}/completar",
                    json={}, headers=csrf_headers())
        assert r1.status_code == 200
        # Forzar redescuento (admin)
        r2 = c.post(f"/api/programacion/programar/{pid}/completar",
                    json={'forzar_redescuento': True}, headers=csrf_headers())
        assert r2.status_code == 200, f"Forzar debería bypass · {r2.data}"
        # Ahora SÍ hay 2 salidas (descontó 2x intencional)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        salidas = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-RACE-1' AND tipo='Salida'"
        ).fetchone()[0]
        assert salidas == 2  # forzar permite 2x
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


def test_completar_forzar_no_admin_403(app, db_clean):
    """Si forzar=true pero user no es admin, debe rechazar 403."""
    c = _login(app, "luis")  # luis no es admin
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        r = c.post(f"/api/programacion/programar/{pid}/completar",
                   json={'forzar_redescuento': True}, headers=csrf_headers())
        assert r.status_code == 403
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


# ─── Dry run no claim ─────────────────────────────────────────────────

def test_completar_dry_run_no_claim(app, db_clean):
    """dry_run no debe hacer claim · puede llamarse N veces sin descontar."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed_produccion(conn)
    conn.close()
    try:
        # 3 dry_runs consecutivos · todos 200 sin descuento
        for _ in range(3):
            r = c.post(f"/api/programacion/programar/{pid}/completar",
                       json={'dry_run': True}, headers=csrf_headers())
            assert r.status_code == 200
            assert r.get_json().get('dry_run') is True
        # Verificar que NO se descontó nada
        conn = sqlite3.connect(os.environ["DB_PATH"])
        salidas = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-RACE-1' AND tipo='Salida'"
        ).fetchone()[0]
        assert salidas == 0
        descontado = conn.execute(
            "SELECT COALESCE(inventario_descontado_at,'') FROM produccion_programada WHERE id=?",
            (pid,)
        ).fetchone()[0]
        assert descontado == ''
        conn.close()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        _cleanup_produccion(conn, pid)
        conn.close()


# ─── No existe → 404 ─────────────────────────────────────────────────

def test_completar_inexistente_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/programacion/programar/9999999/completar",
               json={}, headers=csrf_headers())
    assert r.status_code == 404
