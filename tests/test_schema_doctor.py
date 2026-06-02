from .conftest import TEST_PASSWORD, csrf_headers
def test_doctor(app, db_clean):
    c=app.test_client(); c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers())
    r=c.get('/api/admin/schema-doctor'); print('status',r.status_code,'falt',r.get_json().get('total_faltantes'),'backend',r.get_json().get('backend'))
    assert r.status_code==200 and r.get_json().get('ok') is True
    # en SQLite de test el esquema debería estar completo (init_db crea todo)
    assert r.get_json().get('total_faltantes')==0, r.get_json().get('faltantes')
