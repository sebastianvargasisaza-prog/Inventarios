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


def test_guardian_salud_cruce_detecta_y_alerta(app, db_clean):
    """4-jun · GUARDIÁN diario: detecta stock en bodega que NO cruza (atrapado/
    duplicado) y avisa por campana. Separa el bug de cruce de la compra real."""
    db=sqlite3.connect(os.environ['DB_PATH'])
    # ATRAPADO: código de fórmula con stock pero en AGOTADO (recuperable)
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES ('MPGUARD1','Guardinol','GUARDINOLX',1)")
    db.execute("DELETE FROM movimientos WHERE material_id='MPGUARD1'")
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) VALUES ('MPGUARD1','Guardinol',5000,'Entrada','2026-04-15','LG','AGOTADO','2027-12-07')")
    db.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD GUARD TEST',1,1)")
    db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD GUARD TEST','MPGUARD1','Guardinol',10)")
    db.commit(); db.close()
    # helper directo
    from blueprints.admin import diagnosticar_cruce_global
    with app.app_context():
        d = diagnosticar_cruce_global()
    prod = next((p for p in d['productos'] if p['producto']=='PROD GUARD TEST'), None)
    assert prod, 'el producto debe figurar bloqueado'
    blo = next((b for b in prod['bloqueos'] if b['material_id']=='MPGUARD1'), None)
    assert blo and blo['categoria']=='ATRAPADO', f"stock AGOTADO recuperable = ATRAPADO · {blo}"
    # job guardián: debe detectar n_cruce>=1
    from blueprints.auto_plan_jobs import job_salud_cruce_inventario
    ok, detalle, count = job_salud_cruce_inventario(app)
    assert ok and count >= 1, f"guardián debe detectar cruce · {detalle}"
    assert 'PROD GUARD TEST' in (detalle.get('ejemplos') or []), detalle
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("DELETE FROM movimientos WHERE material_id='MPGUARD1'"); db.execute("DELETE FROM formula_items WHERE producto_nombre='PROD GUARD TEST'"); db.commit(); db.close()


def test_diag_global_no_reporta_agotado_ya_consumido(app, db_clean):
    """4-jun · el diagnóstico global NETEA por lote: stock AGOTADO que ya se
    consumió (entrada 3620 + salida 3620 en el MISMO lote = neto 0) NO debe
    figurar como 'recuperable/ATRAPADO' (era el espejismo de Niacinamida).
    Debe caer a SIN_STOCK_REAL (comprar), coherente con el recuperador."""
    db=sqlite3.connect(os.environ['DB_PATH'])
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES ('MPCONS1','Niacina Cons','NIACINAMIDE',1)")
    db.execute("DELETE FROM movimientos WHERE material_id='MPCONS1'")
    db.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD CONS TEST',1,1)")
    db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD CONS TEST','MPCONS1','Niacina Cons',10)")
    # entró 3620 AGOTADO y salió 3620 en el MISMO lote → neto 0, NO recuperable
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) VALUES ('MPCONS1','Niacina Cons',3620,'Entrada','2026-04-15','LC','AGOTADO','2027-12-07')")
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPCONS1','Niacina Cons',3620,'Salida','2026-05-01','LC','AGOTADO')")
    db.commit(); db.close()
    c=_login(app)
    d=c.get('/api/admin/diagnostico-produccion-global').get_json()
    prod=next((p for p in d['productos'] if p['producto']=='PROD CONS TEST'),None)
    assert prod, 'producto debe figurar bloqueado'
    blo=next((b for b in prod['bloqueos'] if b['material_id']=='MPCONS1'),None)
    assert blo and blo['categoria']=='SIN_STOCK_REAL', f"AGOTADO ya consumido NO es recuperable · {blo}"
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("DELETE FROM movimientos WHERE material_id='MPCONS1'"); db.execute("DELETE FROM formula_items WHERE producto_nombre='PROD CONS TEST'"); db.commit(); db.close()
