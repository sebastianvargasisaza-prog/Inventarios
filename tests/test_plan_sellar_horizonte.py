"""15-jun · Sellar plan: limpieza global del horizonte futuro protegiendo lo
pasado, la semana en curso, lo iniciado y los B2B.

Regla (Sebastián): cancela solo los lotes FUTUROS pendientes (> domingo de la
semana en curso), no toca pasado / esta semana / iniciados / completados / B2B.
"""
import os
import sqlite3
import datetime as _dt
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _hoy_co():
    return (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()


def _seed(prod, fecha, origen='eos_plan', estado='pendiente', inicio=None):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
            "VALUES (?,?,?,?,?,1,?)", (prod, fecha, estado, origen, 30, inicio))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto=? AND fecha_programada=? ORDER BY id DESC LIMIT 1",
                            (prod, fecha)).fetchone()[0]
    finally:
        conn.close()


def _estado(lote_id):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        r = conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (lote_id,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def test_sellar_protege_pasado_semana_y_b2b(app, db_clean):
    hoy = _hoy_co()
    fin_sem = hoy + _dt.timedelta(days=(6 - hoy.weekday()))
    prod = 'PROD SELLAR TEST'
    id_pasado = _seed(prod, (hoy - _dt.timedelta(days=10)).isoformat())
    id_semana = _seed(prod, hoy.isoformat())                       # esta semana (Alejandro)
    id_futuro = _seed(prod, (fin_sem + _dt.timedelta(days=20)).isoformat())
    id_inic = _seed(prod, (fin_sem + _dt.timedelta(days=25)).isoformat(), inicio=(hoy.isoformat()))  # ya iniciado
    id_b2b = _seed(prod, (fin_sem + _dt.timedelta(days=30)).isoformat(), origen='eos_b2b')

    c = _login(app)
    # preview (dry_run) no cambia nada
    pv = c.post('/api/plan/sellar-horizonte', json={'dry_run': True}, headers=csrf_headers())
    assert pv.status_code == 200, pv.data[:300]
    assert pv.get_json()['n_a_cancelar'] >= 1
    assert _estado(id_futuro) == 'pendiente'  # dry_run no toca

    # ejecutar
    r = c.post('/api/plan/sellar-horizonte', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    # solo el futuro normal se cancela
    assert _estado(id_futuro) == 'cancelado'
    # protegidos
    assert _estado(id_pasado) == 'pendiente'
    assert _estado(id_semana) == 'pendiente'
    assert _estado(id_inic) == 'pendiente'
    assert _estado(id_b2b) == 'pendiente'


def test_reemplazar_no_hace_vanish(app, db_clean):
    """BUG 15-jun: 'Aplicar y recalcular' (reemplazar) cancelaba el lote y, si el
    planner no recreaba (sin velocidad/sin ancla), el producto desaparecía del
    calendario. Ahora si no se recrea nada, RESTAURA lo cancelado (anti-vanish)."""
    hoy = _hoy_co()
    prod = 'PROD VANISH TEST'
    fut = (hoy + _dt.timedelta(days=40)).isoformat()
    lote_id = _seed(prod, fut)  # único lote futuro, producto sin velocidad en test
    c = _login(app)
    r = c.post('/api/plan/auto-programar-sugeridas',
               json={'producto': prod, 'reemplazar': True, 'dias_horizonte': 365},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    # sin velocidad → no recrea → restaura → el lote NO desaparece
    assert j.get('n_creados', 0) == 0
    assert j.get('restaurados', 0) >= 1
    assert _estado(lote_id) == 'pendiente'  # restaurado, no cancelado


def test_recuperar_cancelados_bug(app, db_clean):
    """RESCATE 15-jun: lote cancelado por el bug (audit CANCELAR_LOTE_REEMPLAZO /
    SELLAR_CANCELAR_LOTE) y sin recrear → 'Recuperar lotes perdidos' lo restaura."""
    hoy = _hoy_co()
    prod = 'PROD RESCATE BUG'
    fut = (hoy + _dt.timedelta(days=40)).isoformat()
    lote_id = _seed(prod, fut)
    # simular el bug: cancelar + dejar rastro de la acción culpable
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("UPDATE produccion_programada SET estado='cancelado' WHERE id=?", (lote_id,))
    conn.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
                 "VALUES ('sebastian','CANCELAR_LOTE_REEMPLAZO','produccion_programada',?,datetime('now'))",
                 (str(lote_id),))
    conn.commit(); conn.close()

    c = _login(app)
    # diagnóstico
    dg = c.get('/api/plan/recuperar-cancelados-bug')
    assert dg.status_code == 200, dg.data[:300]
    jd = dg.get_json()
    assert jd['recuperables_total'] >= 1 and jd['a_restaurar'] >= 1
    assert any(p['clasificacion'] == 'VANISH' for p in jd['productos'])
    assert _estado(lote_id) == 'cancelado'  # diag no toca
    # ejecutar
    r = c.post('/api/plan/recuperar-cancelados-bug', json={'dry_run': False, 'modo': 'vanish'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['restaurados'] >= 1
    assert _estado(lote_id) == 'pendiente'  # recuperado


def test_backfill_fabricacion(app, db_clean):
    """CAUSA RAÍZ 15-jun: las producciones de Fabricación (tabla producciones) no
    llegan al calendario ni al ancla → backfill las trae como completados
    retroactivos (con fin_real_at) e idempotente."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("INSERT INTO producciones (producto,cantidad,fecha,estado,lote) VALUES (?,?,?,?,?)",
                 ('PROD FAB TEST', 40, '2026-06-03T08:00:00', 'Completado', 'PROD-77001'))
    conn.commit(); conn.close()
    c = _login(app)
    dg = c.post('/api/plan/backfill-fabricacion', json={'dry_run': True}, headers=csrf_headers())
    assert dg.status_code == 200, dg.data[:300]
    assert dg.get_json()['a_crear'] >= 1
    r = c.post('/api/plan/backfill-fabricacion', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()['creados'] >= 1
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    row = conn.execute("SELECT estado, origen, fin_real_at, COALESCE(kg_real,0) FROM produccion_programada "
                       "WHERE producto='PROD FAB TEST'").fetchone()
    conn.close()
    assert row and row[0] == 'completado' and row[1] == 'eos_retroactivo'
    assert row[2] is not None and row[3] == 40  # fin_real_at puesto (lo ve el ancla) + kg
    # idempotente
    r2 = c.post('/api/plan/backfill-fabricacion', json={'dry_run': False}, headers=csrf_headers())
    assert r2.get_json()['creados'] == 0


def test_dedup_mismo_dia(app, db_clean):
    """15-jun: lotes duplicados del mismo producto el mismo día → mantiene el de
    mayor kg, cancela el resto; no toca productos sin duplicado."""
    hoy = _hoy_co()
    f = (hoy + _dt.timedelta(days=2)).isoformat()
    ids = [_seed('DEDUP TEST', f) for _ in range(3)]   # 3 iguales (30kg)
    solo = _seed('SOLO TEST', f)                         # sin duplicado
    c = _login(app)
    dg = c.post('/api/plan/dedup-mismo-dia', json={'dry_run': True}, headers=csrf_headers())
    assert dg.status_code == 200
    j = dg.get_json()
    assert j['grupos_con_duplicado'] == 1 and j['lotes_a_cancelar'] == 2
    r = c.post('/api/plan/dedup-mismo-dia', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200 and r.get_json()['cancelados'] == 2
    activos = [i for i in ids if _estado(i) != 'cancelado']
    assert len(activos) == 1                              # queda uno
    assert _estado(solo) == 'pendiente'                  # el sin-dup intacto


def test_repartir_sobrecargados(app, db_clean):
    """15-jun: día con muchos lotes (apilón del rescate) → se reparten a próximos
    días hábiles con cupo (máx 2/día); lo ejecutado NO se mueve."""
    hoy = _hoy_co()
    # próximo lunes (día hábil estable)
    base = hoy + _dt.timedelta(days=((7 - hoy.weekday()) % 7) or 7)
    f = base.isoformat()
    ids = [_seed('REPARTO %d' % i, f) for i in range(9)]   # 9 productos distintos mismo día
    ejec = _seed('YA INICIADO', f, inicio=hoy.isoformat())  # ejecutado → no se mueve
    c = _login(app)
    dg = c.post('/api/plan/repartir-sobrecargados', json={'dry_run': True}, headers=csrf_headers())
    assert dg.status_code == 200, dg.data[:300]
    assert dg.get_json()['a_mover'] >= 1
    r = c.post('/api/plan/repartir-sobrecargados', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200 and r.get_json()['movidos'] >= 1
    # ningún día con >2 lotes activos
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    sobre = conn.execute(
        "SELECT substr(fecha_programada,1,10), COUNT(*) FROM produccion_programada "
        "WHERE COALESCE(estado,'') NOT IN ('cancelado','completado') "
        "AND substr(fecha_programada,1,10) >= ? GROUP BY 1 HAVING COUNT(*) > 2", (hoy.isoformat(),)).fetchall()
    fej = conn.execute("SELECT fecha_programada FROM produccion_programada WHERE id=?", (ejec,)).fetchone()[0]
    conn.close()
    assert not sobre, f"quedaron días sobrecargados: {sobre}"
    assert str(fej)[:10] == f          # ejecutado no se movió


def test_revertir_hoy(app, db_clean):
    """15-jun: 'deshacer cambios de hoy' → suprime lo creado hoy, restaura lo que la
    cirugía canceló hoy (Alejandro), conserva lo retroactivo de Fabricación."""
    hoy = _hoy_co()
    fut = (hoy + _dt.timedelta(days=30)).isoformat()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    ahora = _dt.datetime.utcnow().isoformat()
    ayer = (hoy - _dt.timedelta(days=2)).isoformat()
    # A) creado HOY (suprimir)
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en) "
                 "VALUES (?,?,?,?,?,1,?)", ('REV NUEVO', fut, 'pendiente', 'eos_canonico', 30, ahora))
    idA = conn.execute("SELECT id FROM produccion_programada WHERE producto='REV NUEVO'").fetchone()[0]
    # B) de ayer, CANCELADO hoy por la cirugía (restaurar)
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en) "
                 "VALUES (?,?,?,?,?,1,?)", ('REV ALEJANDRO', fut, 'cancelado', 'eos_plan', 50, ayer))
    idB = conn.execute("SELECT id FROM produccion_programada WHERE producto='REV ALEJANDRO'").fetchone()[0]
    conn.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
                 "VALUES ('sebastian','SELLAR_CANCELAR_LOTE','produccion_programada',?,datetime('now'))", (str(idB),))
    # C) retroactivo Fabricación creado hoy (conservar · historial real producido)
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en,fin_real_at,inicio_real_at) "
                 "VALUES (?,?,?,?,?,1,?,?,?)", ('REV FAB', '2026-06-04', 'completado', 'eos_retroactivo', 20, ahora, '2026-06-04', '2026-06-04'))
    idC = conn.execute("SELECT id FROM produccion_programada WHERE producto='REV FAB'").fetchone()[0]
    # D) restaurado HOY por el rescate (el apilón · antes estaba cancelado) → re-cancelar
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en) "
                 "VALUES (?,?,?,?,?,1,?)", ('REV APILON', fut, 'pendiente', 'eos_plan', 35, ayer))
    idD = conn.execute("SELECT id FROM produccion_programada WHERE producto='REV APILON'").fetchone()[0]
    conn.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
                 "VALUES ('sebastian','RESTAURAR_BUG_VANISH','produccion_programada',?,datetime('now'))", (str(idD),))
    conn.commit(); conn.close()

    c = _login(app)
    dg = c.post('/api/plan/revertir-hoy', json={'dry_run': True}, headers=csrf_headers())
    assert dg.status_code == 200, dg.data[:300]
    j = dg.get_json()
    assert j['a_suprimir_creadas_hoy'] >= 1 and j['a_restaurar_canceladas'] >= 1 and j['a_recancelar_rescate'] >= 1
    r = c.post('/api/plan/revertir-hoy', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200
    assert _estado(idA) == 'cancelado'    # creado hoy → suprimido
    assert _estado(idB) == 'pendiente'    # cancelado hoy → restaurado
    assert _estado(idC) == 'completado'   # retroactivo Fabricación → conservado
    assert _estado(idD) == 'cancelado'    # rescate de hoy → re-cancelado (limpia el apilón)


def test_restaurar_a_hora(app, db_clean):
    """Restauración punto-en-el-tiempo: reconstruye el estado de hoy a las 11am
    reversando lo posterior · lo creado/restaurado después se quita, lo cancelado
    después se restaura."""
    hoy = _hoy_co()
    after = "%s 17:30:00" % hoy.isoformat()      # > T (11am CO = 16:00 UTC)
    fut = (hoy + _dt.timedelta(days=20)).isoformat()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)

    def _ins(prod, estado, origen, creado):
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en) "
                     "VALUES (?,?,?,?,?,1,?)", (prod, fut, estado, origen, 30, creado))
        return conn.execute("SELECT id FROM produccion_programada WHERE producto=?", (prod,)).fetchone()[0]

    idA = _ins('RAH EXISTIA', 'cancelado', 'eos_plan', (hoy - _dt.timedelta(days=1)).isoformat())
    conn.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
                 "VALUES ('s','SELLAR_CANCELAR_LOTE','produccion_programada',?,?)", (str(idA), after))
    idB = _ins('RAH NUEVO', 'pendiente', 'eos_canonico', "%s 18:00:00" % hoy.isoformat())  # creado después
    idC = _ins('RAH RESCATE', 'pendiente', 'eos_plan', (hoy - _dt.timedelta(days=3)).isoformat())
    conn.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
                 "VALUES ('s','RESTAURAR_BUG_VANISH','produccion_programada',?,?)", (str(idC), after))
    conn.commit(); conn.close()

    c = _login(app)
    dg = c.post('/api/plan/restaurar-a-hora', json={'dry_run': True, 'hora': 11}, headers=csrf_headers())
    assert dg.status_code == 200, dg.data[:300]
    r = c.post('/api/plan/restaurar-a-hora', json={'dry_run': False, 'hora': 11}, headers=csrf_headers())
    assert r.status_code == 200
    assert _estado(idA) == 'pendiente'    # cancelado después → restaurado a las 11am
    assert _estado(idB) == 'cancelado'    # creado después de las 11am → quitado
    assert _estado(idC) == 'cancelado'    # rescate después → a las 11am estaba cancelado


def test_reconstruir_plan(app, db_clean):
    """Recuperación TOTAL: re-activa historial ya producido (eos_retroactivo
    cancelado→completado + sync de producciones), restaura plan Fijo UNO por
    (producto,fecha) sin duplicados, y quita el canónico-ruido reciente."""
    hoy = _hoy_co()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    # historial ya producido pero CANCELADO → debe reactivarse
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,fin_real_at,inicio_real_at,observaciones) "
                 "VALUES ('REC HIST','2026-06-10','cancelado','eos_retroactivo',14,1,'2026-06-10','2026-06-10','[fab#9991]')")
    hid = conn.execute("SELECT id FROM produccion_programada WHERE producto='REC HIST'").fetchone()[0]
    # produccion en Fabricación sin espejo → debe sincronizarse
    conn.execute("INSERT INTO producciones (producto,cantidad,fecha,estado,lote) VALUES ('REC FAB SYNC',60,'2026-06-11T10:00:00','Completado','PR-1')")
    # plan Fijo CANCELADO con 3 duplicados mismo día → vuelve UNO
    f = hoy.isoformat()
    for _ in range(3):
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                     "VALUES ('REC UREA',?,'cancelado','eos_plan',80,1)", (f,))
    # canónico ruido creado hoy → quitar
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,creado_en) "
                 "VALUES ('REC RUIDO','2026-07-01','pendiente','eos_canonico',30,1,?)", (_dt.datetime.utcnow().isoformat(),))
    rid = conn.execute("SELECT id FROM produccion_programada WHERE producto='REC RUIDO'").fetchone()[0]
    conn.commit(); conn.close()

    c = _login(app)
    r = c.post('/api/plan/reconstruir-plan', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _estado(hid) == 'completado'    # historial reactivado
    assert _estado(rid) == 'cancelado'     # ruido quitado
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    syncd = conn.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto='REC FAB SYNC' AND estado='completado'").fetchone()[0]
    urea = conn.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto='REC UREA' AND COALESCE(estado,'')<>'cancelado'").fetchone()[0]
    conn.close()
    assert syncd == 1                      # Fabricación sincronizada
    assert urea == 1                       # plan restaurado UNO (sin dups)


def test_sellar_requiere_rol(app, db_clean):
    c = _login(app, 'valentina')  # sin admin/compras
    r = c.post('/api/plan/sellar-horizonte', json={'dry_run': True}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]
