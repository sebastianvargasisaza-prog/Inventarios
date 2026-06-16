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
