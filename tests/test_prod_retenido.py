import os,sqlite3
from .conftest import TEST_PASSWORD, csrf_headers
def _login(app):
    c=app.test_client(); c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers()); return c
def test_retenido(app, db_clean):
    db=sqlite3.connect(os.environ['DB_PATH'])
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPRET1','Test Ret',1)")
    db.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES ('ZZ RET',1000,1)")
    db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ RET'")
    db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) VALUES ('ZZ RET','MPRET1','Test Ret',10,100)")
    # 5g disponible (VIGENTE) + 600g AGOTADO
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPRET1','Test Ret',5,'Entrada','2026-06-01','L-OK','VIGENTE')")
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPRET1','Test Ret',600,'Entrada','2026-06-01','L-AGOT','AGOTADO')")
    db.commit(); db.close()
    c=_login(app)
    # producir 1kg → necesita 100g, hay 5 → falta, 600 retenido en AGOTADO
    r=c.post('/api/produccion',json={'producto':'ZZ RET','cantidad_kg':1,'operador':'sebastian','presentacion':'x'},headers=csrf_headers())
    d=r.get_json()
    f=next((x for x in d.get('faltantes',[]) if x['material_id']=='MPRET1'),None)
    print('faltante',f)
    assert f and abs(f['retenido_g']-600)<0.5, f
    assert 'AGOTADO' in (f.get('retenido_por_estado') or {}), f
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("DELETE FROM movimientos WHERE material_id='MPRET1'"); db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ RET'"); db.execute("DELETE FROM formula_headers WHERE producto_nombre='ZZ RET'"); db.commit(); db.close()
