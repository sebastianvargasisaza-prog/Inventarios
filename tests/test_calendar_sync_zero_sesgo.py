"""Tests CERO SESGO · sync calendar no debe cancelar producciones en curso.

Sebastián 2-may-2026: si Sebastián borra un evento del Google Calendar
mientras una producción está EN CURSO (ya inició o ya descontó MPs),
el sync bidireccional NO debe marcarla como 'cancelado' · eso
corromperia el estado y dejaría inventario en limbo.

Tests verifican que:
1. Sync NO cancela producciones con inicio_real_at != NULL
2. Sync NO cancela producciones con inventario_descontado_at != NULL
3. Sync SÍ cancela producciones huérfanas que NO han iniciado
4. Audit_log SYNC_CALENDAR_SKIP_EN_CURSO se crea cuando se salta
5. Audit_log AUTO_CANCELAR_PRODUCCION se crea cuando sí cancela
"""
import os
import sqlite3

import pytest


def test_sync_no_cancela_si_ya_inicio(app, db_clean):
    """Producción con inicio_real_at != NULL no debe cancelarse aunque
    haya sido removida del calendar."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Limpiar
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T1'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen, inicio_real_at)
        VALUES ('PROD-CALSYNC-T1', date('now','+5 days'), 1, 'pendiente',
                'calendar', datetime('now'))
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        # Mock _fetch_calendar_events para que devuelva 0 eventos (simula que
        # el evento se borró del Calendar)
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        # Verificar que NO fue cancelada
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute(
            "SELECT estado FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()[0]
        assert estado != 'cancelado', \
               f"Producción con inicio_real_at fue cancelada incorrectamente"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_sync_no_cancela_si_ya_descontó_inventario(app, db_clean):
    """Producción con inventario_descontado_at != NULL no debe cancelarse."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cols = [r[1] for r in conn.execute("PRAGMA table_info(produccion_programada)").fetchall()]
    if 'inventario_descontado_at' not in cols:
        pytest.skip("Schema sin inventario_descontado_at")
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T2'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen,
           inventario_descontado_at)
        VALUES ('PROD-CALSYNC-T2', date('now','+5 days'), 1, 'completado',
                'calendar', datetime('now'))
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute(
            "SELECT estado FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()[0]
        assert estado == 'completado'  # NO cambió
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_sync_si_cancela_huerfana_que_no_inicio(app, db_clean):
    """Producción origen='calendar' sin inicio + ya no en calendar SÍ debe cancelarse."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T3'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen)
        VALUES ('PROD-CALSYNC-T3', date('now','+5 days'), 1, 'pendiente',
                'calendar')
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute(
            "SELECT estado FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()[0]
        # SÍ debió cancelarse porque no había iniciado
        assert estado == 'cancelado'
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_sync_no_toca_origen_manual(app, db_clean):
    """Producciones con origen != 'calendar' NUNCA deben tocarse."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T4'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen)
        VALUES ('PROD-CALSYNC-T4', date('now','+5 days'), 1, 'pendiente',
                'manual')
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        conn = sqlite3.connect(os.environ["DB_PATH"])
        estado = conn.execute(
            "SELECT estado FROM produccion_programada WHERE id=?", (pid,)
        ).fetchone()[0]
        assert estado == 'pendiente'  # No tocó origen=manual
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_sync_skip_en_curso_genera_audit_log(app, db_clean):
    """Cuando se salta cancelar una producción en curso, audit_log debe registrarlo."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T5'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen, inicio_real_at)
        VALUES ('PROD-CALSYNC-T5', date('now','+5 days'), 1, 'pendiente',
                'calendar', datetime('now'))
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        # Verificar audit_log
        conn = sqlite3.connect(os.environ["DB_PATH"])
        audit = conn.execute("""
            SELECT accion FROM audit_log
            WHERE accion='SYNC_CALENDAR_SKIP_EN_CURSO' AND registro_id=?
            ORDER BY id DESC LIMIT 1
        """, (str(pid),)).fetchone()
        assert audit is not None, "audit_log SYNC_CALENDAR_SKIP_EN_CURSO no se creó"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_sync_cancela_genera_audit_log(app, db_clean):
    """Cuando sí cancela una huérfana, audit_log AUTO_CANCELAR_PRODUCCION."""
    from blueprints.programacion import _sync_calendar_a_produccion_programada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-CALSYNC-T6'")
    cur = conn.execute("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, origen)
        VALUES ('PROD-CALSYNC-T6', date('now','+5 days'), 1, 'pendiente',
                'calendar')
    """)
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        from blueprints import programacion as prog
        orig_fetch = prog._fetch_calendar_events
        # Mock con UN evento distinto · así el sync corre el cleanup pero
        # no encuentra el (producto, fecha) de la prod test → la marca huérfana
        prog._fetch_calendar_events = lambda **kw: {
            'events': [{'titulo': 'OTROPROD ~5kg', 'fecha': '2099-12-31', 'id': 'fake'}],
            'error': None, 'source': 'mock'
        }
        try:
            with app.app_context():
                from database import get_db
                conn2 = get_db()
                _sync_calendar_a_produccion_programada(conn2, days_ahead=30)
        finally:
            prog._fetch_calendar_events = orig_fetch
        conn = sqlite3.connect(os.environ["DB_PATH"])
        audit = conn.execute("""
            SELECT accion FROM audit_log
            WHERE accion='AUTO_CANCELAR_PRODUCCION' AND registro_id=?
            ORDER BY id DESC LIMIT 1
        """, (str(pid),)).fetchone()
        assert audit is not None, "audit_log AUTO_CANCELAR_PRODUCCION no se creó"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()
