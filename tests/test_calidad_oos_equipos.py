"""14-jun · OOS: doble aprobación (rechazo/destrucción) + e-firma Part 11 + auto-CAPA +
sección equipos en bandeja."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client(); c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers()); return c


def _firmar(c, oos_id, meaning='aprueba'):
    rc = c.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=csrf_headers())
    assert rc.status_code == 200, rc.data[:200]
    tok = rc.get_json()['token']
    rs = c.post('/api/sign', json={'record_table': 'calidad_oos', 'record_id': str(oos_id),
                                    'meaning': meaning, 'challenge_token': tok}, headers=csrf_headers())
    assert rs.status_code == 201, rs.data[:200]
    return rs.get_json()['signature_id']


def _nuevo_oos(producto='PROD X', lote='L-OOS'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    cur = conn.execute("INSERT INTO calidad_oos (codigo,origen,lote,producto,parametro,estado,fecha_deteccion) "
                       "VALUES (?,'micro',?,?,'Mesófilos','abierto','2026-05-01')", ('OOS-T-'+lote, lote, producto))
    oid = cur.lastrowid; conn.commit(); conn.close()
    return oid


def test_oos_cierre_requiere_firma(app, db_clean):
    oid = _nuevo_oos()
    c = _login(app, 'sebastian')
    base = {'causa_raiz': 'desviacion de proceso confirmada en envasado y corregida', 'disposicion': 'liberado', 'estado': 'cerrado'}
    # sin firma → 400 FIRMA_REQUERIDA
    r = c.patch(f'/api/calidad/oos/{oid}', json=base, headers=csrf_headers())
    assert r.status_code == 400 and (r.get_json() or {}).get('codigo') == 'FIRMA_REQUERIDA', r.data[:200]
    # con firma → cierra + auto-CAPA
    sig = _firmar(c, oid)
    r2 = c.patch(f'/api/calidad/oos/{oid}', json={**base, 'signature_id': sig}, headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:200]
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    # auto-CAPA: NC con el código del OOS en la descripción + CAPA correctiva colgando
    nc = conn.execute("SELECT id FROM no_conformidades WHERE descripcion LIKE 'OOS OOS-T-L-OOS:%'").fetchone()
    assert nc, 'cerrar un OOS debe auto-crear la NC'
    cap = conn.execute("SELECT id FROM capa_acciones WHERE nc_id=? AND tipo='correctiva'", (nc[0],)).fetchone()
    assert cap, 'la NC del OOS debe tener una CAPA correctiva'
    conn.close()


def test_oos_rechazo_requiere_gerencia_y_firma(app, db_clean):
    oid = _nuevo_oos(lote='L-RCH')
    c = _login(app, 'sebastian')
    base = {'causa_raiz': 'contaminacion cruzada confirmada, lote no recuperable', 'disposicion': 'rechazado', 'estado': 'cerrado'}
    # sin gerencia → 422 (antes de la firma)
    r = c.patch(f'/api/calidad/oos/{oid}', json=base, headers=csrf_headers())
    assert r.status_code == 422 and (r.get_json() or {}).get('codigo') == 'REQUIERE_APROBACION_GERENCIA', r.data[:200]
    # gerencia == quien cierra → SoD
    r2 = c.patch(f'/api/calidad/oos/{oid}', json={**base, 'aprobado_gerencia': 'sebastian'}, headers=csrf_headers())
    assert r2.status_code == 422 and (r2.get_json() or {}).get('codigo') == 'DOBLE_APROBACION_MISMO_USUARIO', r2.data[:200]
    # gerencia distinta + firma → cierra
    sig = _firmar(c, oid)
    r3 = c.patch(f'/api/calidad/oos/{oid}', json={**base, 'aprobado_gerencia': 'alejandro', 'signature_id': sig}, headers=csrf_headers())
    assert r3.status_code == 200, r3.data[:200]


def test_bandeja_tiene_seccion_equipos(admin_client):
    d = admin_client.get('/api/calidad/bandeja').get_json()
    assert 'equipos_calibracion' in d['secciones']
    assert 'oos_sla_vencidos' in d['kpis']
