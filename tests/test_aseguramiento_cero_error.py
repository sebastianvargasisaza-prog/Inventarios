"""14-jun · Audit cero-error de Aseguramiento (4 bugs reales):
- audit_log al crear queja y cambio (Part 11 / M22)
- PII de cliente enmascarada para no-admin en cliente-trazabilidad (Habeas Data)
- CAS en transiciones de desviación (M27) · el flujo normal sigue funcionando
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client(); c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers()); return c


def _audit_count(accion):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_log WHERE accion=?", (accion,)).fetchone()[0]
    finally:
        conn.close()


def test_crear_queja_audita(app, db_clean):
    c = _login(app)
    antes = _audit_count('CREAR_QUEJA')
    r = c.post('/api/aseguramiento/quejas', json={
        'cliente_nombre': 'Cliente Test', 'descripcion': 'producto con olor raro reportado',
        'canal': 'email', 'tipo_queja': 'calidad_producto'}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    assert _audit_count('CREAR_QUEJA') == antes + 1, 'crear queja debe auditar (Part 11)'


def test_crear_cambio_audita(app, db_clean):
    c = _login(app)
    antes = _audit_count('CREAR_CAMBIO')
    r = c.post('/api/aseguramiento/cambios', json={
        'titulo': 'Cambio de proveedor de envase', 'tipo': 'proveedor',
        'descripcion': 'cambiar proveedor del frasco de 30ml por desabasto del actual'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    assert _audit_count('CREAR_CAMBIO') == antes + 1, 'crear cambio debe auditar (Part 11)'


def test_cliente_trazabilidad_pii_enmascarada(app, db_clean):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    cur = conn.execute("INSERT INTO clientes (codigo,nombre,empresa,email,telefono,nit) "
                       "VALUES ('CL-PII','Cliente PII','Empresa X','correo@x.com','3001234567','900123')")
    cid = cur.lastrowid; conn.commit(); conn.close()
    # admin ve PII en claro
    adm = _login(app, 'sebastian')
    da = adm.get(f'/api/aseguramiento/reportes/cliente-trazabilidad/{cid}').get_json()['cliente']
    assert da['email'] == 'correo@x.com' and da['nit'] == '900123', 'admin ve PII'
    # calidad (laura) la ve enmascarada
    lau = _login(app, 'laura')
    dl = lau.get(f'/api/aseguramiento/reportes/cliente-trazabilidad/{cid}').get_json()['cliente']
    assert dl['email'] == '***' and dl['nit'] == '***', 'no-admin no debe ver PII en claro'
    assert dl['nombre'] == 'Cliente PII', 'pero sí el nombre (recall)'


def test_desviacion_flujo_con_cas(app, db_clean):
    c = _login(app)
    r = c.post('/api/aseguramiento/desviaciones', json={
        'tipo': 'proceso', 'area_origen': 'envasado',
        'descripcion': 'temperatura fuera de rango en marmita durante fabricacion'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    did = r.get_json().get('id') or r.get_json().get('desviacion_id')
    assert did
    # flujo normal: clasificar → investigar → capa (el CAS no debe romperlo)
    r1 = c.post(f'/api/aseguramiento/desviaciones/{did}/clasificar',
                json={'clasificacion': 'menor', 'justificacion': 'desviacion menor sin impacto en producto'}, headers=csrf_headers())
    assert r1.status_code == 200, r1.data[:200]
    r2 = c.post(f'/api/aseguramiento/desviaciones/{did}/investigar',
                json={'metodo_investigacion': '5_porques', 'causa_raiz': 'sensor de temperatura descalibrado por el uso continuo'}, headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:200]
    # reclasificar tras investigar → bloqueado (gate/CAS)
    r3 = c.post(f'/api/aseguramiento/desviaciones/{did}/clasificar',
                json={'clasificacion': 'mayor', 'justificacion': 'intento reclasificar fuera de estado'}, headers=csrf_headers())
    assert r3.status_code == 409, r3.data[:200]
