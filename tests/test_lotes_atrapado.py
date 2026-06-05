import os,sqlite3
from .conftest import TEST_PASSWORD, csrf_headers
def _login(app):
    c=app.test_client(); c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers()); return c
def test_atrapado(app, db_clean):
    db=sqlite3.connect(os.environ['DB_PATH'])
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPATR1','Glucosa Test',1)")
    db.execute("DELETE FROM movimientos WHERE material_id='MPATR1'")
    # entrada 2495 AGOTADO (venc futuro) + salidas sin estado 1895 -> neto 600 atrapado
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) VALUES ('MPATR1','Glucosa Test',2495,'Entrada','2026-04-15','LATR','AGOTADO','2027-12-07')")
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPATR1','Glucosa Test',1895,'Salida','2026-05-01','LATR','')")
    db.commit(); db.close()
    c=_login(app)
    d=c.get('/api/admin/lotes-stock-atrapado').get_json()
    lote=next((x for x in d['lotes'] if x['material_id']=='MPATR1'),None)
    print('atrapado_g',lote and lote['atrapado_g'],'disp',lote and lote['disponible_g'])
    assert lote and abs(lote['atrapado_g']-600)<1, lote
    # aplicar
    d2=c.post('/api/admin/lotes-stock-atrapado',json={'token':'CORREGIR_LOTES_2026'},headers=csrf_headers()).get_json()
    assert d2['corregidos']>=1
    db=sqlite3.connect(os.environ['DB_PATH']); est=db.execute("SELECT estado_lote FROM movimientos WHERE material_id='MPATR1' AND tipo='Entrada'").fetchone()[0]; db.close()
    assert est=='VIGENTE', est
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("DELETE FROM movimientos WHERE material_id='MPATR1'"); db.commit(); db.close()


def test_atrapado_sin_lote(app, db_clean):
    """4-jun · stock AGOTADO SIN lote (caso Niacinamida MP00148, reset 27-abr):
    antes el recuperador filtraba WHERE lote!='' y NO lo veía ('ningún lote
    atrapado') aunque el cruce sí lo contaba. Ahora también lo recupera."""
    db=sqlite3.connect(os.environ['DB_PATH'])
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPATRNL','Niacina Test',1)")
    db.execute("DELETE FROM movimientos WHERE material_id='MPATRNL'")
    # entrada 3620 AGOTADO SIN lote + salida 520 sin lote -> neto 3100 atrapado
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) VALUES ('MPATRNL','Niacina Test',3620,'Entrada','2026-04-15','','AGOTADO','2027-12-07')")
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPATRNL','Niacina Test',520,'Salida','2026-05-01','','')")
    db.commit(); db.close()
    c=_login(app)
    d=c.get('/api/admin/lotes-stock-atrapado').get_json()
    lote=next((x for x in d['lotes'] if x['material_id']=='MPATRNL'),None)
    assert lote and lote['atrapado_g']>3000, f"debe ver stock atrapado sin lote · {lote}"
    d2=c.post('/api/admin/lotes-stock-atrapado',json={'token':'CORREGIR_LOTES_2026'},headers=csrf_headers()).get_json()
    assert d2['corregidos']>=1
    db=sqlite3.connect(os.environ['DB_PATH']); est=db.execute("SELECT estado_lote FROM movimientos WHERE material_id='MPATRNL' AND tipo='Entrada'").fetchone()[0]; db.close()
    assert est=='VIGENTE', est
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("DELETE FROM movimientos WHERE material_id='MPATRNL'"); db.commit(); db.close()
