import os,io,sqlite3,base64,openpyxl
from .conftest import TEST_PASSWORD, csrf_headers
def _login(app):
    c=app.test_client(); r=c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers(),follow_redirects=False); assert r.status_code==302; return c
def _xlsx():
    wb=openpyxl.Workbook(); wb.remove(wb.active); ws=wb.create_sheet('P1')
    ws.append(['#','NOMBRE INCI','NOMBRE COMERCIAL','CÓD. BATCH','% FÓRMULA'])
    ws.append(['1','N-ACETYL GLUCOSAMINE','N-acetil glucosamina','MPZZNEW1','0.01'])
    ws.append(['2','GLYCERIN','Glicerina','MPZZEXIST','0.03'])
    b=io.BytesIO(); wb.save(b); return base64.b64encode(b.getvalue()).decode()
def test_crear_faltantes(app, db_clean):
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPZZEXIST','Glicerina',1)"); db.execute("DELETE FROM maestro_mps WHERE codigo_mp='MPZZNEW1'"); db.commit(); db.close()
    c=_login(app)
    d=c.post('/api/admin/crear-mps-faltantes-excel?aplicar=1',json={'contenido_b64':_xlsx()},headers=csrf_headers()).get_json()
    print('faltantes',d['total_faltantes'],'creados',d['creados'])
    assert any(f['codigo']=='MPZZNEW1' for f in d['faltantes'])
    db=sqlite3.connect(os.environ['DB_PATH']); row=db.execute("SELECT nombre_inci,nombre_comercial,activo FROM maestro_mps WHERE codigo_mp='MPZZNEW1'").fetchone(); db.close()
    assert row and row[2]==1, row
    assert 'GLUCOSAMINE' in (row[0] or '').upper()
