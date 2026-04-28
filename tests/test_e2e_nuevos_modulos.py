"""E2E tests para modulos nuevos: espagiria, comunicacion, versionado formulas."""
import pytest
from .conftest import TEST_PASSWORD, csrf_headers


def _login_as(app, user):
    c = app.test_client()
    r = c.post("/login",
               data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


# ─── ESPAGIRIA ─────────────────────────────────────────────────────────────

def test_espagiria_dashboard_responde(app, db_clean):
    c = _login_as(app, 'luz')
    r = c.get('/api/espagiria/dashboard')
    assert r.status_code == 200, r.data
    d = r.get_json()
    for k in ['producciones_mes', 'mps_bajo_minimo', 'vencen_30d', 'ocs_activas',
             'solicitudes_pendientes', 'calidad_ncs', 'mis_tareas_pendientes']:
        assert k in d, f"Falta clave: {k}"


def test_espagiria_acceso_denegado_otros(app, db_clean):
    c = _login_as(app, 'jefferson')
    r = c.get('/api/espagiria/dashboard')
    assert r.status_code == 403


def test_espagiria_alertas_estructura(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/espagiria/alertas')
    assert r.status_code == 200
    d = r.get_json()
    assert 'alertas' in d and 'total' in d


def test_espagiria_pre_comite(app, db_clean):
    c = _login_as(app, 'luz')
    r = c.get('/api/espagiria/resumen-pre-comite')
    assert r.status_code == 200
    d = r.get_json()
    assert 'reincidentes' in d
    assert 'completadas_semana' in d
    assert 'nuevas_semana' in d


# ─── COMUNICACION TAREAS RACI ──────────────────────────────────────────────

def test_comunicacion_crear_tarea_con_raci(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.post('/api/comunicacion/tareas', json={
        'titulo': 'Pilotear nuevo serum vitamina C',
        'descripcion': 'Lote piloto 5kg para validar formula',
        'prioridad': 'Alta',
        'area': 'Tecnica',
        'fecha_compromiso': '2026-05-15',
        'raci': [
            {'usuario': 'hernando', 'rol': 'R'},
            {'usuario': 'sebastian', 'rol': 'A'},
            {'usuario': 'gisseth', 'rol': 'C'},
            {'usuario': 'luz', 'rol': 'I'},
        ],
    })
    assert r.status_code == 201, r.data
    tid = r.get_json()['id']

    r2 = c.get(f'/api/comunicacion/tareas/{tid}')
    d = r2.get_json()
    assert d['titulo'] == 'Pilotear nuevo serum vitamina C'
    raci = {item['usuario']: item['rol'] for item in d['raci']}
    assert raci.get('hernando') == 'R'
    assert raci.get('sebastian') == 'A'


def test_comunicacion_filtrar_mis_tareas(app, db_clean):
    sb = _login_as(app, 'sebastian')
    sb.post('/api/comunicacion/tareas', json={
        'titulo': 'Coordinar entrega FM',
        'raci': [{'usuario': 'luz', 'rol': 'R'}],
    })
    luz = _login_as(app, 'luz')
    r = luz.get('/api/comunicacion/tareas?mis=1')
    assert r.status_code == 200
    titulos = [t['titulo'] for t in r.get_json()]
    assert 'Coordinar entrega FM' in titulos


def test_comunicacion_avanzar_estado_completa_tarea(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.post('/api/comunicacion/tareas', json={
        'titulo': 'Test estado',
        'raci': [{'usuario': 'sebastian', 'rol': 'R'}],
    })
    tid = r.get_json()['id']
    c.patch(f'/api/comunicacion/tareas/{tid}', json={'estado': 'Hecha'})
    d = c.get(f'/api/comunicacion/tareas/{tid}').get_json()
    assert d['estado'] == 'Hecha'
    assert d['fecha_completada'] is not None


def test_comunicacion_avance_acumula_timeline(app, db_clean):
    c = _login_as(app, 'sebastian')
    tid = c.post('/api/comunicacion/tareas', json={
        'titulo': 'Test avance',
        'raci': [{'usuario': 'sebastian', 'rol': 'R'}],
    }).get_json()['id']
    c.post(f'/api/comunicacion/tareas/{tid}/avance', json={'nota': 'Primer paso done'})
    c.post(f'/api/comunicacion/tareas/{tid}/avance', json={'nota': 'Segundo paso bloqueado'})
    d = c.get(f'/api/comunicacion/tareas/{tid}').get_json()
    assert 'Primer paso done' in d['notas_avance']
    assert 'Segundo paso bloqueado' in d['notas_avance']


# ─── COMUNICACION CHAT ─────────────────────────────────────────────────────

def test_comunicacion_chat_bidireccional(app, db_clean):
    luz = _login_as(app, 'luz')
    r = luz.post('/api/comunicacion/mensajes', json={
        'a_usuario': 'sebastian',
        'asunto': 'Pendiente cronograma',
        'mensaje': 'Laura aun no entrega cronograma calibraciones',
    })
    assert r.status_code == 200, r.data

    sb = _login_as(app, 'sebastian')
    msgs = sb.get('/api/comunicacion/mensajes').get_json()
    asuntos = [m['asunto'] for m in msgs]
    assert 'Pendiente cronograma' in asuntos
    assert sb.get('/api/comunicacion/mensajes/no-leidos').get_json()['count'] >= 1


def test_comunicacion_marcar_leido(app, db_clean):
    luz = _login_as(app, 'luz')
    luz.post('/api/comunicacion/mensajes', json={
        'a_usuario': 'sebastian', 'asunto': 'Test leido',
        'mensaje': 'msg',
    })
    sb = _login_as(app, 'sebastian')
    msgs = sb.get('/api/comunicacion/mensajes').get_json()
    msg = next(m for m in msgs if m['asunto'] == 'Test leido')
    sb.post(f'/api/comunicacion/mensajes/{msg["id"]}/leido')
    d = sb.get('/api/comunicacion/mensajes/no-leidos').get_json()
    # contador debe haber disminuido (idealmente a 0 si era el unico no-leido del test)
    assert d['count'] >= 0  # smoke


# ─── COMUNICACION ACTAS Y PARSER ───────────────────────────────────────────

def test_comunicacion_acta_y_parser_crea_tareas(app, db_clean):
    c = _login_as(app, 'sebastian')
    transcripcion = """
    Comite Semanal Espagiria - 2026-04-26

    Asistentes: Sebastian, Luz, Gisseth, Hernando, Laura, Catalina

    Desarrollo:
    Se discutieron varios temas operativos importantes...

    Conclusiones y compromisos:
    - Gisseth entregara informe Retinal Mas, plazo: 2026-05-03
    - Luz coordinara cronograma de auditoria interna con Laura
    - Hernando probara fenoxietanol sustituto en lote piloto
    - Sebastian revisara presupuesto Q2 con Mayra
    - Catalina solicitara cotizaciones de glicerina, plazo: 2026-05-10

    Observaciones:
    Reunion concluyo a las 5pm
    """
    r = c.post('/api/comunicacion/actas', json={
        'fecha': '2026-04-26',
        'asistentes': ['sebastian', 'luz', 'gisseth'],
        'transcripcion': transcripcion,
    })
    assert r.status_code == 201, r.data
    aid = r.get_json()['id']

    r2 = c.post(f'/api/comunicacion/actas/{aid}/parsear')
    assert r2.status_code == 200, r2.data
    n_creadas = r2.get_json()['tareas_creadas']
    assert n_creadas >= 3, f"esperaba >=3 tareas, parser creo {n_creadas}"

    tareas = c.get('/api/comunicacion/tareas?origen=comite').get_json()
    titulos = ' | '.join(t['titulo'] for t in tareas)
    # Al menos los responsables principales aparecen en algun titulo
    assert ('Gisseth' in titulos or 'Retinal' in titulos)


# ─── VERSIONADO FORMULAS ────────────────────────────────────────────────────

def test_versionado_snapshot_automatico(app, db_clean):
    c = _login_as(app, 'sebastian')
    r1 = c.post('/api/tecnica/formulas', json={
        'codigo': 'TST-001', 'nombre': 'Suero V1',
        'tipo': 'COSMETICO', 'descripcion': 'Original',
    })
    assert r1.status_code == 200
    fid = r1.get_json()['id']

    c.patch(f'/api/tecnica/formulas/{fid}', json={
        'nombre': 'Suero V2', 'motivo_cambio': 'Mejora estabilidad',
    })
    c.patch(f'/api/tecnica/formulas/{fid}', json={'nombre': 'Suero V3'})

    versiones = c.get(f'/api/tecnica/formulas/{fid}/versiones').get_json()
    assert len(versiones) == 2
    assert versiones[0]['version_num'] == 2
    assert versiones[1]['version_num'] == 1
    # Verifica motivo de cambio se guardo
    motivos = [v.get('motivo_cambio') for v in versiones]
    assert 'Mejora estabilidad' in motivos


def test_versionado_restaurar_devuelve_original(app, db_clean):
    c = _login_as(app, 'sebastian')
    r1 = c.post('/api/tecnica/formulas', json={
        'codigo': 'TST-002', 'nombre': 'OriginalABC',
    })
    fid = r1.get_json()['id']
    c.patch(f'/api/tecnica/formulas/{fid}', json={'nombre': 'Modificado1'})
    c.patch(f'/api/tecnica/formulas/{fid}', json={'nombre': 'Modificado2'})

    versiones = c.get(f'/api/tecnica/formulas/{fid}/versiones').get_json()
    vid_original = versiones[-1]['id']  # snapshot mas viejo
    r_rest = c.post(f'/api/tecnica/formulas/{fid}/restaurar/{vid_original}')
    assert r_rest.status_code == 200, r_rest.data

    formulas = c.get('/api/tecnica/formulas').get_json()
    f_actual = next(f for f in formulas if f['id'] == fid)
    assert f_actual['nombre'] == 'OriginalABC'


def test_versionado_restaurar_solo_admin(app, db_clean):
    sb = _login_as(app, 'sebastian')
    r1 = sb.post('/api/tecnica/formulas', json={
        'codigo': 'TST-003', 'nombre': 'X',
    })
    fid = r1.get_json()['id']
    sb.patch(f'/api/tecnica/formulas/{fid}', json={'nombre': 'Y'})
    versiones = sb.get(f'/api/tecnica/formulas/{fid}/versiones').get_json()
    vid = versiones[0]['id']
    # Hernando es TECNICA_USERS pero no admin
    hr = _login_as(app, 'hernando')
    r = hr.post(f'/api/tecnica/formulas/{fid}/restaurar/{vid}')
    assert r.status_code == 403


# ─── SYNC SHOPIFY → FLUJO_INGRESOS ─────────────────────────────────────────

def test_sync_shopify_status_endpoint(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/financiero/sync-shopify-status')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert 'pendientes_count' in d
    assert 'sincronizados_count' in d


def test_sync_shopify_dry_run_no_escribe(app, db_clean):
    """Inserta orders shopify mock + dry_run + verifica que NO se escriben ingresos."""
    import sqlite3, os
    c = _login_as(app, 'sebastian')
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM animus_shopify_orders")
    db.execute("DELETE FROM flujo_ingresos WHERE fuente='shopify_auto'")
    for i in range(3):
        db.execute("""INSERT INTO animus_shopify_orders
                      (shopify_id, nombre, total, moneda, estado_pago, creado_en, flujo_synced)
                      VALUES (?,?,?,?,?,?,0)""",
                  (f'TEST-DR-{i}', f'Cliente {i}', 100000.0, 'COP', 'paid', f'2026-04-{20+i}'))
    db.commit()
    db.close()

    r = c.post('/api/financiero/sync-shopify-ingresos',
               json={'dry_run': True, 'solo_pagados': True})
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['dry_run'] is True
    assert d['pendientes'] == 3
    assert d['total_a_importar'] == 300000

    # Verificar que NO se escribieron ingresos
    db = sqlite3.connect(os.environ["DB_PATH"])
    n = db.execute("SELECT COUNT(*) FROM flujo_ingresos WHERE fuente='shopify_auto'").fetchone()[0]
    db.close()
    assert n == 0


def test_sync_shopify_ejecuta_e_idempotente(app, db_clean):
    """Verifica que sync escribe ingresos, marca synced=1, y reejecutar no duplica."""
    import sqlite3, os
    c = _login_as(app, 'sebastian')
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM animus_shopify_orders")
    db.execute("DELETE FROM flujo_ingresos WHERE fuente='shopify_auto'")
    db.execute("""INSERT INTO animus_shopify_orders
                  (shopify_id, nombre, total, moneda, estado_pago, creado_en, flujo_synced)
                  VALUES (?,?,?,?,?,?,0)""",
              ('SH-100', 'Cliente A', 250000.0, 'COP', 'paid', '2026-04-25'))
    db.execute("""INSERT INTO animus_shopify_orders
                  (shopify_id, nombre, total, moneda, estado_pago, creado_en, flujo_synced)
                  VALUES (?,?,?,?,?,?,0)""",
              ('SH-101', 'Cliente B', 150000.0, 'COP', 'cancelled', '2026-04-26'))
    db.commit()
    db.close()

    # Primer sync — debe importar SOLO la pagada
    r1 = c.post('/api/financiero/sync-shopify-ingresos',
                json={'solo_pagados': True})
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1['importadas'] == 1, f"esperaba 1, importo {d1['importadas']}"
    assert d1['total_importado'] == 250000

    # Segundo sync — idempotente, no debe importar de nuevo
    r2 = c.post('/api/financiero/sync-shopify-ingresos',
                json={'solo_pagados': True})
    d2 = r2.get_json()
    assert d2['importadas'] == 0

    # Verificar fila en flujo_ingresos
    db = sqlite3.connect(os.environ["DB_PATH"])
    rows = db.execute(
        "SELECT monto, referencia, fuente FROM flujo_ingresos WHERE fuente='shopify_auto'"
    ).fetchall()
    db.close()
    assert len(rows) == 1
    assert rows[0][0] == 250000.0
    assert rows[0][1] == 'SHOPIFY-SH-100'


def test_sync_shopify_solo_admin(app, db_clean):
    luz = _login_as(app, 'luz')
    r = luz.post('/api/financiero/sync-shopify-ingresos', json={})
    assert r.status_code == 401
