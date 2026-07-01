"""M67 · cantidad_objetivo_g del EBR sale de la cantidad REAL a producir (produccion_programada.cantidad_kg),
NO del default genérico lote_size_g del MBR. Protege la clase del bug de la TEÓRICA (30-jun-2026):
un EBR de 12 kg mostraba 100 g porque heredaba el default del MBR cuando el caller no pasaba la cantidad.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_crear_ebr_desde_mbr_deriva_objetivo_de_cantidad_kg(app, db_clean):
    """El helper canónico crear_ebr_desde_mbr, si el caller NO pasa cantidad_objetivo_g pero sí
    produccion_id, deriva el objetivo de produccion_programada.cantidad_kg × 1000 (fuente de verdad),
    no del lote_size_g del MBR (default genérico). Blinda los hooks de envasado/acondicionamiento."""
    from blueprints.brd import crear_ebr_desde_mbr
    # MBR con default genérico de 100 g (el que causaba la TEÓRICA falsa)
    _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
          "VALUES ('ZZ-M67', 1, 'aprobado', 100, 'sebastian')")
    # producción real de 12 kg
    pid = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen) "
                "VALUES ('ZZ-M67', '2026-06-30', 12, 'en_proceso', 'eos_plan')")
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.cursor()
        r = crear_ebr_desde_mbr(cur, producto_nombre='ZZ-M67', lote='M67L1',
                                produccion_id=pid, usuario='sebastian')
        conn.commit()
    finally:
        conn.close()
    assert r.get('ok'), r
    obj = _q1("SELECT cantidad_objetivo_g FROM ebr_ejecuciones WHERE id=?", (r['id'],))[0]
    # 12 kg × 1000 = 12000 g · NO el default 100 g del MBR
    assert abs(float(obj) - 12000.0) < 0.5, f"esperaba 12000 g (12 kg real), fue {obj}"


def test_crear_ebr_desde_mbr_sin_produccion_usa_default_mbr(app, db_clean):
    """Sin produccion_id ni cantidad_objetivo_g, el fallback ordenado sí usa el lote_size_g del MBR."""
    from blueprints.brd import crear_ebr_desde_mbr
    _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
          "VALUES ('ZZ-M67B', 1, 'aprobado', 777, 'sebastian')")
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.cursor()
        r = crear_ebr_desde_mbr(cur, producto_nombre='ZZ-M67B', lote='M67BL1', usuario='sebastian')
        conn.commit()
    finally:
        conn.close()
    assert r.get('ok'), r
    obj = _q1("SELECT cantidad_objetivo_g FROM ebr_ejecuciones WHERE id=?", (r['id'],))[0]
    assert abs(float(obj) - 777.0) < 0.5, f"esperaba fallback 777 g del MBR, fue {obj}"


def test_corregir_cantidad_resincroniza_objetivo_ebr(app, db_clean):
    """Corregir la cantidad_kg de una producción re-sincroniza el cantidad_objetivo_g del EBR de
    fabricación NO liberado ligado (el batch record no debe quedar con el objetivo/rendimiento viejo)."""
    c = _login(app, "sebastian")
    _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
          "VALUES ('ZZ-M67C', 1, 'aprobado', 100, 'sebastian')")
    pid = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, "
                "inventario_descontado_at) VALUES ('ZZ-M67C', '2026-06-30', 10, 'en_proceso', 'eos_plan', '')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, lote_codigo, "
                   "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES ((SELECT id FROM mbr_templates WHERE producto_nombre='ZZ-M67C'), 1, ?, 'M67CL1', "
                   "'M67CL1', 'iniciado', 'fabricacion', 'sebastian', datetime('now','utc'), 10000)", (pid,))
    # corregir a 25 kg
    r = c.post(f"/api/programacion/programar/{pid}/corregir-cantidad",
               json={"cantidad_kg": 25}, headers=_h())
    assert r.status_code == 200, r.data
    obj = _q1("SELECT cantidad_objetivo_g FROM ebr_ejecuciones WHERE id=?", (ebr_id,))[0]
    assert abs(float(obj) - 25000.0) < 0.5, f"el EBR debía re-sincronizar a 25000 g, quedó {obj}"


def test_corregir_cantidad_no_toca_ebr_liberado(app, db_clean):
    """Un EBR ya liberado es INMUTABLE (mig 111): corregir la cantidad NO cambia su objetivo congelado."""
    c = _login(app, "sebastian")
    _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
          "VALUES ('ZZ-M67D', 1, 'aprobado', 100, 'sebastian')")
    pid = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, "
                "inventario_descontado_at) VALUES ('ZZ-M67D', '2026-06-30', 10, 'en_proceso', 'eos_plan', '')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, lote_codigo, "
                   "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, liberado_at_utc, liberado_por) "
                   "VALUES ((SELECT id FROM mbr_templates WHERE producto_nombre='ZZ-M67D'), 1, ?, 'M67DL1', "
                   "'M67DL1', 'liberado', 'fabricacion', 'sebastian', datetime('now','utc'), 10000, "
                   "datetime('now','utc'), 'sebastian')", (pid,))
    r = c.post(f"/api/programacion/programar/{pid}/corregir-cantidad",
               json={"cantidad_kg": 25}, headers=_h())
    assert r.status_code == 200, r.data
    obj = _q1("SELECT cantidad_objetivo_g FROM ebr_ejecuciones WHERE id=?", (ebr_id,))[0]
    assert abs(float(obj) - 10000.0) < 0.5, f"EBR liberado inmutable: objetivo debía seguir 10000, fue {obj}"
