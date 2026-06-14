"""Audit recepción 13-jun (revisores adversariales):
- anular_recepcion dejaba el stock NEGATIVO (Salida 'ANULADO' restaba en el canónico
  pero la Entrada CUARENTENA no sumaba) y fantasma en auditar-minimos. Fix: la Salida
  de anulación ESPEJA el estado original (net-zero exacto) + guard de stock disponible.
- cc_review escribía 'APROBADO' en movimientos.estado_lote (no canónico) → cron de
  vencidos/KPIs lo saltaban. Fix: el kardex usa 'VIGENTE'.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone(); return r[0] if r else None
    finally:
        conn.close()


def _seed_entrada(cod, lote, cant, estado):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (cod, 'Test ' + cod))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES (?,?,?,'Entrada','2026-06-01',?,?)", (cod, 'Test ' + cod, cant, lote, estado))
    return _q1("SELECT MAX(id) FROM movimientos WHERE material_id=? AND lote=?", (cod, lote))


# stock canónico (excluye cuarentena/rechazado/etc · como _get_mp_stock)
_CANON = ("SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
          "WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END),0) FROM movimientos "
          "WHERE material_id=? AND UPPER(COALESCE(estado_lote,'')) NOT IN "
          "('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO')")


def test_anular_cuarentena_no_deja_negativo(app, db_clean):
    mid = _seed_entrada('MP-ANC', 'L-ANC', 1000, 'CUARENTENA')
    c = _login(app)
    r = c.post(f'/api/recepcion/{mid}/anular', json={'motivo': 'recepción duplicada por error'}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    canon = float(_q1(_CANON, ('MP-ANC',)))
    assert canon == 0, f"anular un lote en cuarentena NO debe dejar stock canónico negativo · fue {canon}"
    # la Salida de anulación espeja el estado original (CUARENTENA), no 'ANULADO'
    estado_salida = _q1("SELECT estado_lote FROM movimientos WHERE material_id='MP-ANC' AND tipo='Salida' ORDER BY id DESC LIMIT 1")
    assert estado_salida == 'CUARENTENA', f"la Salida debe espejar el estado original · fue {estado_salida}"


def test_anular_vigente_neto_cero(app, db_clean):
    mid = _seed_entrada('MP-ANV', 'L-ANV', 1000, 'VIGENTE')
    canon_antes = float(_q1(_CANON, ('MP-ANV',)))
    assert abs(canon_antes - 1000) < 0.5
    c = _login(app)
    r = c.post(f'/api/recepcion/{mid}/anular', json={'motivo': 'ingreso equivocado de prueba'}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    canon = float(_q1(_CANON, ('MP-ANV',)))
    assert canon == 0, f"anular un VIGENTE debe dar neto 0 · fue {canon}"


def test_anular_lote_consumido_bloqueado(app, db_clean):
    mid = _seed_entrada('MP-ANX', 'L-ANX', 1000, 'VIGENTE')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-ANX','Test MP-ANX',1000,'Salida','2026-06-02','L-ANX','VIGENTE')")  # consumido
    c = _login(app)
    r = c.post(f'/api/recepcion/{mid}/anular', json={'motivo': 'intento anular ya consumido'}, headers=csrf_headers())
    assert r.status_code == 409 and (r.get_json() or {}).get('codigo') == 'LOTE_YA_MOVIDO', \
        f"no debe anular un lote ya consumido · {r.status_code} {r.data[:200]}"
    canon = float(_q1(_CANON, ('MP-ANX',)))
    assert canon == 0, f"no debe quedar negativo · fue {canon}"


def test_doble_anulacion_bloqueada(app, db_clean):
    mid = _seed_entrada('MP-AND', 'L-AND', 1000, 'VIGENTE')
    c = _login(app)
    r1 = c.post(f'/api/recepcion/{mid}/anular', json={'motivo': 'primera anulación válida'}, headers=csrf_headers())
    assert r1.status_code in (200, 201), r1.data[:200]
    r2 = c.post(f'/api/recepcion/{mid}/anular', json={'motivo': 'segunda anulación no debe pasar'}, headers=csrf_headers())
    assert r2.status_code == 409, f"la 2ª anulación debe bloquearse · {r2.status_code} {r2.data[:200]}"
    canon = float(_q1(_CANON, ('MP-AND',)))
    assert canon == 0, f"no debe quedar negativo tras intento de doble anulación · fue {canon}"
