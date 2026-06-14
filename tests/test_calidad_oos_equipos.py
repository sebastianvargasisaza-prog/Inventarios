"""14-jun · OOS doble aprobación (rechazo/destrucción) + sección equipos en bandeja."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client(); c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers()); return c


def test_oos_rechazo_requiere_gerencia(app, db_clean):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    cur = conn.execute("INSERT INTO calidad_oos (codigo,origen,lote,producto,parametro,estado,fecha_deteccion) "
                       "VALUES ('OOS-T1','micro','L-OOS','PROD X','Mesófilos','abierto','2026-05-01')")
    oos_id = cur.lastrowid; conn.commit(); conn.close()
    c = _login(app, 'sebastian')
    base = {'causa_raiz': 'contaminacion cruzada confirmada en el area de envasado', 'disposicion': 'rechazado', 'estado': 'cerrado'}
    # sin aprobado_gerencia → 422
    r = c.patch(f'/api/calidad/oos/{oos_id}', json=base, headers=csrf_headers())
    assert r.status_code == 422 and (r.get_json() or {}).get('codigo') == 'REQUIERE_APROBACION_GERENCIA', r.data[:200]
    # gerencia == quien cierra (sebastian es admin) → rechazado por SoD
    r2 = c.patch(f'/api/calidad/oos/{oos_id}', json={**base, 'aprobado_gerencia': 'sebastian'}, headers=csrf_headers())
    assert r2.status_code == 422 and (r2.get_json() or {}).get('codigo') == 'DOBLE_APROBACION_MISMO_USUARIO', r2.data[:200]
    # gerencia distinta (alejandro, admin) → cierra
    r3 = c.patch(f'/api/calidad/oos/{oos_id}', json={**base, 'aprobado_gerencia': 'alejandro'}, headers=csrf_headers())
    assert r3.status_code == 200, r3.data[:200]


def test_bandeja_tiene_seccion_equipos(admin_client):
    d = admin_client.get('/api/calidad/bandeja').get_json()
    assert 'equipos_calibracion' in d['secciones']
    assert 'oos_sla_vencidos' in d['kpis']
