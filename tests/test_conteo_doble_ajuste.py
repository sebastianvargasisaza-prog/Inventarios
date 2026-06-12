"""Conteo cíclico · un ítem ya ajustado NO se re-ajusta al re-guardar (Sebastián
12-jun). Antes, guardar usaba INSERT OR REPLACE que reseteaba ajuste_aplicado ->
al cerrar/ajustar de nuevo el kardex se movía 2 veces (doble entrada/salida).
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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def test_conteo_item_ajustado_no_se_reajusta_al_reguardar(app, db_clean):
    COD, LOTE, EST = 'MP-CONT-DA', 'L-CONT-DA', 'E-CONT-DA'
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,?,?,1)", (COD, 'GLYCERIN', 'Glicerina'))
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estanteria, estado_lote) "
          "VALUES (?,?,?,'Entrada',datetime('now'),?,?,'VIGENTE')",
          (COD, 'GLYCERIN', 1000, LOTE, EST))

    c = _login(app)
    # iniciar conteo en la estantería
    r = c.post('/api/conteo/iniciar', json={'estanteria': EST})
    assert r.status_code == 200, r.data
    cid = r.get_json()['conteo_id']

    item = {'codigo_mp': COD, 'lote': LOTE, 'stock_sistema': 1000, 'stock_fisico': 970,
            'nombre': 'GLYCERIN', 'estanteria': EST, 'precio_ref': 0, 'causa_diferencia': 'merma'}
    # guardar (diff -30 = 3% < 5% -> no requiere gerencia)
    r = c.post(f'/api/conteo/{cid}/guardar', json={'items': [item]})
    assert r.status_code == 200, r.data
    saved = r.get_json()['items']
    it_id = next(x['id'] for x in saved if x['codigo_mp'] == COD)

    # aplicar ajuste manual -> Salida 30, ajuste_aplicado=1
    r = c.post(f'/api/conteo/{cid}/ajustar', json={'item_id': it_id})
    assert r.status_code == 200, r.data

    # RE-GUARDAR el mismo item (el bug reseteaba el flag) ...
    r = c.post(f'/api/conteo/{cid}/guardar', json={'items': [item]})
    assert r.status_code == 200, r.data
    # ... y CERRAR (auto-ajustaría de nuevo si el flag se reseteó)
    r = c.post(f'/api/conteo/{cid}/cerrar', json={})
    assert r.status_code == 200, r.data

    # CLAVE: debe haber UN SOLO movimiento de ajuste (no doble)
    n_ajustes = _q1("SELECT COUNT(*) FROM movimientos WHERE material_id=? "
                    "AND observaciones LIKE '%juste%ciclico%'", (COD,))
    assert n_ajustes == 1, f"doble ajuste: {n_ajustes} movimientos de ajuste (esperado 1)"

    # el item quedó marcado como aplicado (no reseteado)
    aplicado = _q1("SELECT COALESCE(ajuste_aplicado,0) FROM conteo_items "
                   "WHERE conteo_id=? AND codigo_mp=? AND COALESCE(lote,'')=?", (cid, COD, LOTE))
    assert aplicado == 1

    # stock final = 1000 - 30 = 970 (un solo ajuste)
    stock = _q1("SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad WHEN tipo='Salida' "
                "THEN -cantidad ELSE 0 END),0) FROM movimientos WHERE material_id=? AND lote=?", (COD, LOTE))
    assert abs(stock - 970) < 0.01, f"stock {stock} != 970 (doble ajuste lo dejaría en 940)"
