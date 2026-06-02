"""Integración MyBatch · paso 1: el editor de Fórmulas guarda procedimiento + IPC
como MBR draft, y se puede releer."""
import os, sqlite3
from .conftest import TEST_PASSWORD, csrf_headers
def _login(app):
    c=app.test_client(); r=c.post('/login',data={'username':'sebastian','password':TEST_PASSWORD},headers=csrf_headers(),follow_redirects=False); assert r.status_code==302; return c
def _h():
    h={'Content-Type':'application/json'}; h.update(csrf_headers()); return h
def test_sync_y_releer(app, db_clean):
    db=sqlite3.connect(os.environ['DB_PATH'])
    db.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) VALUES ('ZZ MBR PROD',1000,10,1)")
    db.commit(); db.close()
    c=_login(app)
    body={'producto_nombre':'ZZ MBR PROD',
          'pasos':[{'descripcion':'Premezcla 1: 90% agua + niacinamida a 65C','fase':'Fabricación','resultado_label':'temperatura'},
                   {'descripcion':'Agitar 1500 RPM hasta disolución','resultado_label':'RPM'}],
          'ipc':[{'parametro':'pH','unidad':'','valor_min':5.0,'valor_max':6.0},
                 {'parametro':'Apariencia','especificacion':'Líquido viscoso blanco hueso'}]}
    r=c.post('/api/brd/mbr/sync-procedimiento',data=__import__('json').dumps(body),headers=_h())
    assert r.status_code==200, r.data
    d=r.get_json(); print('sync',d)
    assert d['ok'] and d['n_pasos']==2 and d['n_ipc']==2
    # releer
    r2=c.get('/api/brd/mbr/por-producto?producto=ZZ%20MBR%20PROD')
    d2=r2.get_json(); print('releer',d2.get('existe'),len(d2.get('pasos',[])),len(d2.get('ipc',[])))
    assert d2['existe'] and len(d2['pasos'])==2 and len(d2['ipc'])==2
    assert d2['pasos'][0]['descripcion'].startswith('Premezcla 1')
    assert any(i['parametro']=='pH' for i in d2['ipc'])
