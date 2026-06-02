import os,io,sqlite3,base64,openpyxl
from .conftest import TEST_PASSWORD, csrf_headers
def _login(app):
    c=app.test_client(); c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers()); return c
def _xlsx():
    wb=openpyxl.Workbook(); wb.remove(wb.active); ws=wb.create_sheet('P1')
    ws.append(['#','NOMBRE INCI','NOMBRE COMERCIAL','CÓD. BATCH','% FÓRMULA'])
    ws.append(['1','N-ACETYL GLUCOSAMINE','N-acetil glucosamina','MPZZINACT','0.01'])
    b=io.BytesIO(); wb.save(b); return base64.b64encode(b.getvalue()).decode()
def test_reactivar(app, db_clean):
    db=sqlite3.connect(os.environ['DB_PATH']); db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPZZINACT','N-acetil glucosamina',0)"); db.commit(); db.close()
    c=_login(app)
    d=c.post('/api/admin/crear-mps-faltantes-excel?reactivar=1',json={'contenido_b64':_xlsx()},headers=csrf_headers()).get_json()
    print('inactivos',d['total_inactivos'],'reactivados',d['reactivados'])
    assert d['reactivados']>=1
    db=sqlite3.connect(os.environ['DB_PATH']); a=db.execute("SELECT activo FROM maestro_mps WHERE codigo_mp='MPZZINACT'").fetchone()[0]; db.close()
    assert a==1
