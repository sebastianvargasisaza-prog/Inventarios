"""Lotes consumidos a residuo (<=0.01g) desaparecen del inventario (Sebastián
12-jun). Un lote ya gastado deja polvo flotante (0.004g) que se mostraba como
"0" y no salía ni de la vista ni de FEFO. Ahora umbral 0.01g.
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


def test_lote_residuo_desaparece_real_se_mantiene(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo_material, activo) "
          "VALUES ('MP-DUST','GLYCERIN','Glicerina','MP',1)")
    # Lote DUST: 1000 - 999.996 = 0.004 g (residuo · ya gastado)
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
          "VALUES ('MP-DUST','GLYCERIN',1000,'Entrada',datetime('now'),'L-DUST','VIGENTE')")
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
          "VALUES ('MP-DUST','GLYCERIN',999.996,'Salida',datetime('now'),'L-DUST','VIGENTE')")
    # Lote REAL: 500 g
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
          "VALUES ('MP-DUST','GLYCERIN',500,'Entrada',datetime('now'),'L-REAL','VIGENTE')")

    c = _login(app)
    r = c.get('/api/lotes')
    assert r.status_code == 200, r.data
    lotes = r.get_json()['lotes']
    de_dust = [x for x in lotes if x['material_id'] == 'MP-DUST']
    nombres_lote = {x['lote'] for x in de_dust}
    assert 'L-REAL' in nombres_lote, "el lote con stock real debe aparecer"
    assert 'L-DUST' not in nombres_lote, "el lote en residuo (0.004g) debe desaparecer del inventario"
