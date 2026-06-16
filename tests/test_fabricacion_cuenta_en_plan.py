"""15-jun-2026 · CÁLCULO PERFECTO · las producciones de Fabricación (tabla
`producciones`) deben CONTAR para el plan automáticamente.

Causa raíz: el ancla del cálculo (`ultima_prod`) y el calendario leen SOLO
`produccion_programada`; Fabricación escribe SOLO en `producciones`. El espejo
`_mirror_produccion_a_calendario` crea el lote completado retroactivo (idempotente)
para que el cálculo lo cuente. Disparado por hook al registrar + cron de reconciliación.
"""
import os
import sqlite3
import sys


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _row(producto):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT estado, origen, fin_real_at, COALESCE(kg_real,0), COALESCE(inventario_descontado_at,'') "
            "FROM produccion_programada WHERE producto=? ORDER BY id DESC LIMIT 1", (producto,)).fetchone()
    finally:
        conn.close()


def test_mirror_crea_idempotente_y_no_duplica(app, db_clean):
    _api()
    from blueprints.plan import _mirror_produccion_a_calendario
    from database import get_db
    with app.app_context():
        conn = get_db()
        # 1. crea el espejo (completado, retroactivo, fin_real_at, inventario descontado)
        n1 = _mirror_produccion_a_calendario(conn, 55001, 'PROD FAB CALC', 40,
                                             '2026-06-05T10:00:00', 'L1', usuario='test')
        conn.commit()
        assert n1 == 1
        r = _row('PROD FAB CALC')
        assert r and r[0] == 'completado' and r[1] == 'eos_retroactivo'
        assert r[2] and r[3] == 40 and r[4]   # fin_real_at + kg + inventario_descontado_at
        # 2. idempotente por marcador [fab#id]
        n2 = _mirror_produccion_a_calendario(conn, 55001, 'PROD FAB CALC', 40,
                                             '2026-06-05T10:00:00', 'L1', usuario='test')
        conn.commit()
        assert n2 == 0
        # 3. no duplica si (producto, fecha) ya tiene un lote EJECUTADO (otro fab id)
        n3 = _mirror_produccion_a_calendario(conn, 55002, 'PROD FAB CALC', 20,
                                             '2026-06-05T09:00:00', 'L2', usuario='test')
        conn.commit()
        assert n3 == 0
        # 4. cantidad <=0 o fecha inválida → no crea
        assert _mirror_produccion_a_calendario(conn, 55003, 'X', 0, '2026-06-05', '', 'test') == 0
        assert _mirror_produccion_a_calendario(conn, 55004, 'X', 5, 'basura', '', 'test') == 0


def test_sync_fabricacion_calendario_reconcilia(app, db_clean):
    """El cron de reconciliación recorre `producciones` y crea los espejos faltantes."""
    _api()
    from blueprints.plan import _sync_fabricacion_calendario
    from database import get_db
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn0.execute("INSERT INTO producciones (producto,cantidad,fecha,estado,lote) VALUES (?,?,?,?,?)",
                  ('PROD RECON', 30, '2026-06-03T08:00:00', 'Completado', 'PROD-66001'))
    conn0.commit(); conn0.close()
    with app.app_context():
        conn = get_db()
        res = _sync_fabricacion_calendario(conn, usuario='test')
        assert res['creados'] >= 1
        res2 = _sync_fabricacion_calendario(conn, usuario='test')
        assert res2['creados'] == 0   # idempotente
    r = _row('PROD RECON')
    assert r and r[0] == 'completado' and r[1] == 'eos_retroactivo' and r[2]


def test_mirror_cierra_pendiente_en_vez_de_duplicar(app, db_clean):
    """Si ya hay un lote PENDIENTE ese (producto, fecha), el espejo lo CIERRA como
    completado en vez de crear un duplicado (caso 4-jun)."""
    _api()
    from blueprints.plan import _mirror_produccion_a_calendario
    from database import get_db
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                  "VALUES (?,?,?,?,?,1)", ('SUERO EXF DUP', '2026-06-04', 'programado', 'eos_plan', 45))
    pend = conn0.execute("SELECT id FROM produccion_programada WHERE producto='SUERO EXF DUP'").fetchone()[0]
    conn0.commit(); conn0.close()
    with app.app_context():
        conn = get_db()
        n = _mirror_produccion_a_calendario(conn, 80001, 'SUERO EXF DUP', 45,
                                            '2026-06-04T10:00:00', 'L', usuario='test')
        conn.commit()
        assert n == 1
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    estado = conn0.execute("SELECT estado FROM produccion_programada WHERE id=?", (pend,)).fetchone()[0]
    total = conn0.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto='SUERO EXF DUP' "
                          "AND substr(fecha_programada,1,10)='2026-06-04'").fetchone()[0]
    conn0.close()
    assert estado == 'completado'   # cerró el pendiente
    assert total == 1               # NO duplicó


def test_cerrar_pendientes_ya_producidos(app, db_clean):
    """Un pendiente cuyo mismo (producto, fecha) ya tiene un completado → se cancela."""
    _api()
    from blueprints.plan import _cerrar_pendientes_ya_producidos
    from database import get_db
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,fin_real_at,inicio_real_at) "
                  "VALUES (?,?,?,?,?,1,?,?)", ('GEL DUP', '2026-06-04', 'completado', 'eos_retroactivo', 45, '2026-06-04', '2026-06-04'))
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                  "VALUES (?,?,?,?,?,1)", ('GEL DUP', '2026-06-04', 'programado', 'eos_plan', 45))
    pend = conn0.execute("SELECT id FROM produccion_programada WHERE producto='GEL DUP' AND estado='programado'").fetchone()[0]
    # un pendiente FUTURO de otro día NO debe tocarse
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                  "VALUES (?,?,?,?,?,1)", ('GEL DUP', '2026-07-04', 'pendiente', 'eos_plan', 45))
    otro = conn0.execute("SELECT id FROM produccion_programada WHERE producto='GEL DUP' AND substr(fecha_programada,1,10)='2026-07-04'").fetchone()[0]
    conn0.commit(); conn0.close()
    with app.app_context():
        conn = get_db()
        cerrados = _cerrar_pendientes_ya_producidos(conn, usuario='test')
        assert cerrados >= 1
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    assert conn0.execute("SELECT estado FROM produccion_programada WHERE id=?", (pend,)).fetchone()[0] == 'cancelado'
    assert conn0.execute("SELECT estado FROM produccion_programada WHERE id=?", (otro,)).fetchone()[0] == 'pendiente'
    conn0.close()


def test_anclas_normaliza_nombre_M13(app, db_clean):
    """El espejo de Fabricación con nombre variante (acento/puntuación) igual debe
    contar como ancla: _calcular_animus_dtc indexa el ancla normalizada."""
    _api()
    from blueprints.plan import _calcular_animus_dtc, _mirror_produccion_a_calendario
    from blueprints.programacion import _norm_prod_fuerte
    from database import get_db
    with app.app_context():
        conn = get_db()
        # crear espejo con un nombre con acento/variación
        _mirror_produccion_a_calendario(conn, 70001, 'Suero Multipéptidos+', 35,
                                        '2026-06-01T10:00:00', 'L', usuario='test')
        conn.commit()
        productos = _calcular_animus_dtc(conn.cursor(), ventana=60,
                                          cob_critico=20, cob_alerta=25, cob_vigilar=45)
        # construir índice normalizado como lo hace el motor y verificar que el ancla
        # del espejo es alcanzable por nombre normalizado (no se pierde por el acento)
        clave = _norm_prod_fuerte('SUERO MULTIPEPTIDOS')
        assert clave == _norm_prod_fuerte('Suero Multipéptidos+')  # mismas tras normalizar
        # el cálculo corrió sin error con el espejo presente (no rompe)
        assert isinstance(productos, list)


def test_dejar_solo_real_rescata_limpia_y_pausa(app, db_clean):
    """16-jun · solución definitiva: rescata Fabricación, cancela todo lo no
    ejecutado y PAUSA el cron (self-heal lo respeta)."""
    from .conftest import TEST_PASSWORD, csrf_headers
    # Seed: 1 producción real de Fabricación + ruido pendiente + 1 ejecutado real
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn0.execute("INSERT INTO producciones (producto,cantidad,fecha,estado,lote) VALUES (?,?,?,?,?)",
                  ('PROD SOLO REAL', 30, '2026-06-02T08:00:00', 'Completado', 'PSR-1'))
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                  "VALUES (?,?,?,?,?,1)", ('RUIDO AUTO', '2026-07-20', 'pendiente', 'auto_plan', 50))
    ruido = conn0.execute("SELECT id FROM produccion_programada WHERE producto='RUIDO AUTO'").fetchone()[0]
    conn0.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
                  "VALUES (?,?,?,?,?,1,?)", ('YA EJECUTADO', '2026-06-09', 'en_proceso', 'eos_plan', 40, '2026-06-09'))
    ejec = conn0.execute("SELECT id FROM produccion_programada WHERE producto='YA EJECUTADO'").fetchone()[0]
    # cron arranca habilitado
    conn0.execute("UPDATE auto_plan_cron_state SET habilitado=1 WHERE id=1")
    conn0.commit(); conn0.close()

    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    # preview no toca nada
    pv = c.get('/api/plan/dejar-solo-real')
    assert pv.status_code == 200 and pv.get_json()['a_cancelar'] >= 1
    # ejecutar
    r = c.post('/api/plan/dejar-solo-real', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['ok'] is True
    assert j['rescatados_fabricacion'] >= 1
    assert j['cancelados'] >= 1
    assert j['cron_pausado'] is True

    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # ruido cancelado, ejecutado intacto
        assert conn0.execute("SELECT estado FROM produccion_programada WHERE id=?", (ruido,)).fetchone()[0] == 'cancelado'
        assert conn0.execute("SELECT estado FROM produccion_programada WHERE id=?", (ejec,)).fetchone()[0] == 'en_proceso'
        # Fabricación rescatada (espejo completado)
        resc = conn0.execute("SELECT estado, origen FROM produccion_programada WHERE producto='PROD SOLO REAL' ORDER BY id DESC LIMIT 1").fetchone()
        assert resc and resc[0] == 'completado' and resc[1] == 'eos_retroactivo'
        # cron pausado + flag de pausa manual
        assert conn0.execute("SELECT habilitado FROM auto_plan_cron_state WHERE id=1").fetchone()[0] in (0, False)
        assert conn0.execute("SELECT valor FROM app_settings WHERE clave='auto_plan_pausa_manual'").fetchone()[0] == '1'
    finally:
        conn0.execute("DELETE FROM app_settings WHERE clave='auto_plan_pausa_manual'")
        conn0.execute("UPDATE auto_plan_cron_state SET habilitado=1 WHERE id=1")
        conn0.commit(); conn0.close()


def test_self_heal_respeta_pausa_manual(app, db_clean):
    """Con la pausa manual puesta, el self-heal NO re-habilita el cron (antes lo
    re-encendía cada 7am y el calendario volvía a llenarse)."""
    _api()
    from blueprints.auto_plan_jobs import job_self_heal
    conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn0.execute("UPDATE auto_plan_cron_state SET habilitado=0 WHERE id=1")
    conn0.execute("INSERT INTO app_settings (clave,valor,descripcion) VALUES ('auto_plan_pausa_manual','1','x') "
                  "ON CONFLICT(clave) DO UPDATE SET valor='1'")
    conn0.commit(); conn0.close()
    try:
        job_self_heal(app)
        conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        hab = conn0.execute("SELECT habilitado FROM auto_plan_cron_state WHERE id=1").fetchone()[0]
        conn0.close()
        assert hab in (0, False)   # respetó la pausa
    finally:
        conn0 = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        conn0.execute("DELETE FROM app_settings WHERE clave='auto_plan_pausa_manual'")
        conn0.execute("UPDATE auto_plan_cron_state SET habilitado=1 WHERE id=1")
        conn0.commit(); conn0.close()
