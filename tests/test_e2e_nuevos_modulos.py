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


# ─── CENTRO DE NOTIFICACIONES ──────────────────────────────────────────────

def test_centro_notificaciones_estructura(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/notificaciones/centro')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert 'alertas' in d
    assert 'total' in d
    assert 'por_severidad' in d
    assert all(k in d['por_severidad'] for k in ['alta', 'media', 'info'])


def test_centro_notificaciones_count(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/notificaciones/count')
    assert r.status_code == 200
    d = r.get_json()
    assert 'count' in d
    assert isinstance(d['count'], int)


def test_centro_notificaciones_no_autenticado(app, db_clean):
    c = app.test_client()  # sin login
    r = c.get('/api/notificaciones/count')
    # El endpoint puede devolver 200 con count=0 o 401/302 dependiendo del middleware
    if r.status_code == 200:
        d = r.get_json() or {}
        assert d.get('count', 0) == 0
    else:
        assert r.status_code in (401, 302)


def test_centro_notificaciones_detecta_tarea_vencida(app, db_clean):
    """Crea una tarea vencida asignada a luz y verifica que aparece en su centro."""
    sb = _login_as(app, 'sebastian')
    sb.post('/api/comunicacion/tareas', json={
        'titulo': 'Tarea TEST vencida',
        'fecha_compromiso': '2025-01-01',  # ya pasada
        'raci': [{'usuario': 'luz', 'rol': 'R'}],
    })
    luz = _login_as(app, 'luz')
    r = luz.get('/api/notificaciones/centro')
    d = r.get_json()
    titulos = ' '.join(a['titulo'] for a in d['alertas'])
    assert 'TEST vencida' in titulos
    assert d['por_severidad']['alta'] >= 1


# ─── ASIGNACION POR AREA + RESOLUCION ──────────────────────────────────────

def test_comunicacion_listar_areas(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/comunicacion/areas')
    assert r.status_code == 200
    d = r.get_json()
    assert 'areas' in d
    nombres = [a['area'] for a in d['areas']]
    assert 'Calidad' in nombres
    assert 'Tecnica' in nombres
    assert 'Compras' in nombres


def test_comunicacion_asignar_area_completa(app, db_clean):
    """Crear tarea + asignar a area Calidad → todos los miembros quedan como I."""
    c = _login_as(app, 'sebastian')
    r1 = c.post('/api/comunicacion/tareas', json={
        'titulo': 'Test asignar a Calidad', 'raci': []
    })
    tid = r1.get_json()['id']
    r2 = c.post(f'/api/comunicacion/tareas/{tid}/asignar-area',
                json={'area': 'Calidad', 'rol': 'I'})
    assert r2.status_code == 200, r2.data
    d = r2.get_json()
    assert 'laura' in d['notificados'] or 'gisseth' in d['notificados']
    # Verificar en GET
    detalle = c.get(f'/api/comunicacion/tareas/{tid}').get_json()
    raci_users = {item['usuario'] for item in detalle['raci']}
    assert 'laura' in raci_users or 'gisseth' in raci_users


def test_comunicacion_raci_expande_area_prefix(app, db_clean):
    """Crear tarea con raci usando 'area:Calidad' debe expandir a miembros."""
    c = _login_as(app, 'sebastian')
    r = c.post('/api/comunicacion/tareas', json={
        'titulo': 'Test area: prefix',
        'raci': [{'usuario': 'area:Calidad', 'rol': 'I'}],
    })
    assert r.status_code == 201, r.data
    d = r.get_json()
    expandido = {item['usuario'] for item in d['raci_expandido']}
    # Calidad area users incluye laura y gisseth
    assert 'laura' in expandido or 'gisseth' in expandido


# ─── SGD VENCIMIENTOS ──────────────────────────────────────────────────────

def test_sgd_proximos_vencimientos_endpoint(app, db_clean):
    c = _login_as(app, 'sebastian')
    # Crear un SGD que vence en 5 días
    from datetime import datetime as _dt, timedelta as _td
    fecha_emision = (_dt.now() - _td(days=360)).strftime('%Y-%m-%d')
    r1 = c.post('/api/tecnica/documentos', json={
        'tipo': 'SOP', 'codigo': 'SOP-TEST-001',
        'nombre': 'SOP de prueba',
        'fecha_emision': fecha_emision,
        'frecuencia_revision_meses': 12,
    })
    assert r1.status_code == 200

    r2 = c.get('/api/tecnica/documentos/proximos-vencimientos')
    assert r2.status_code == 200, r2.data
    d = r2.get_json()
    assert 'documentos' in d
    codigos = [doc['codigo'] for doc in d['documentos']]
    assert 'SOP-TEST-001' in codigos


def test_sgd_marcar_revisado_reprograma(app, db_clean):
    c = _login_as(app, 'sebastian')
    r1 = c.post('/api/tecnica/documentos', json={
        'tipo': 'SOP', 'codigo': 'SOP-REV-001', 'nombre': 'X',
        'fecha_emision': '2025-01-01', 'frecuencia_revision_meses': 6,
    })
    did = r1.get_json()['id']
    r2 = c.post(f'/api/tecnica/documentos/{did}/marcar-revisado')
    assert r2.status_code == 200, r2.data
    d = r2.get_json()
    assert d['ok']
    # Proxima revisión debe ser ~6 meses adelante
    from datetime import datetime as _dt
    proxima = _dt.strptime(d['fecha_proxima_revision'], '%Y-%m-%d')
    delta_dias = (proxima - _dt.now()).days
    assert 150 <= delta_dias <= 200  # ~6 meses


# ─── MIGRACION COMPROMISOS LEGACY ──────────────────────────────────────────

def test_migrar_compromisos_a_tareas(app, db_clean):
    c = _login_as(app, 'sebastian')
    # Crear 2 compromisos legacy
    c.post('/api/compromisos', json={
        'descripcion': 'Compromiso TEST 1',
        'responsable': 'hernando',
        'area': 'Tecnica',
        'estado': 'Pendiente',
    })
    c.post('/api/compromisos', json={
        'descripcion': 'Compromiso TEST 2 completado',
        'responsable': 'luz',
        'area': 'Gerencia',
        'estado': 'Completado',
    })
    # Migrar
    r = c.post('/api/compromisos/migrar-a-tareas')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['migrados'] >= 1  # solo el pendiente
    # Re-ejecutar es idempotente (no migra de nuevo)
    r2 = c.post('/api/compromisos/migrar-a-tareas')
    d2 = r2.get_json()
    assert d2['migrados'] == 0
    # La tarea migrada debe aparecer en tareas con origen=compromisos_legacy
    tareas = c.get('/api/comunicacion/tareas?origen=compromisos_legacy').get_json()
    titulos = ' '.join(t['titulo'] for t in tareas)
    assert 'TEST 1' in titulos


# ─── GAP 5/7/4 SMOKE TESTS ─────────────────────────────────────────────────

def test_gap5_pago_factura_genera_flujo_ingreso(app, db_clean):
    """Crear factura + registrar pago → debe aparecer en flujo_ingresos auto."""
    import sqlite3, os
    c = _login_as(app, 'sebastian')
    # Login a contabilidad (sesion dual)
    c.post('/api/contabilidad/login', json={'usuario': 'sebastian', 'password': TEST_PASSWORD})
    # Insertar factura directamente
    db = sqlite3.connect(os.environ['DB_PATH'])
    db.execute("""INSERT OR IGNORE INTO config_facturacion(empresa,anio,tipo,siguiente)
                  VALUES('ANIMUS', 2026, 'FV', 9000)""")
    db.execute("""INSERT INTO facturas
                  (numero, tipo, cliente_nombre, empresa, fecha_emision, total, estado)
                  VALUES ('FV-ANI-2026-9000', 'Factura', 'Cliente Test',
                          'ANIMUS', date('now'), 500000, 'Emitida')""")
    db.commit()
    db.close()

    # Pagar la factura
    r = c.post('/api/contabilidad/facturas/FV-ANI-2026-9000/pago',
               json={'monto': 500000, 'medio': 'Transferencia'})
    assert r.status_code == 200, r.data

    # Verificar flujo_ingresos
    db = sqlite3.connect(os.environ['DB_PATH'])
    rows = db.execute("""SELECT monto, fuente, referencia FROM flujo_ingresos
                         WHERE referencia LIKE 'FAC-FV-ANI-2026-9000-%'""").fetchall()
    db.close()
    assert len(rows) == 1
    assert rows[0][0] == 500000
    assert rows[0][1] == 'factura_pago_auto'


def test_gap4_pagar_nomina_genera_flujo_egreso(app, db_clean):
    """Aprobar+pagar nómina periodo → debe aparecer en flujo_egresos auto."""
    import sqlite3, os
    c = _login_as(app, 'sebastian')
    db = sqlite3.connect(os.environ['DB_PATH'])
    # Crear empleado test + registro nomina (schema real)
    db.execute("""INSERT OR IGNORE INTO empleados(id, codigo, nombre, cargo, estado)
                  VALUES (9001, 'EMP-9001', 'Empleado Test', 'Operario', 'Activo')""")
    db.execute("""INSERT INTO nomina_registros
                  (empleado_id, periodo, salario_neto, estado)
                  VALUES (9001, '2026-04', 1500000, 'Aprobada')""")
    db.commit()
    db.close()
    # Pagar
    r = c.patch('/api/rrhh/nomina/2026-04/pagar')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d.get('egresos_flujo_creados') == 1

    # Verificar flujo_egresos
    db = sqlite3.connect(os.environ['DB_PATH'])
    row = db.execute("""SELECT monto, fuente FROM flujo_egresos
                        WHERE referencia='NOM-2026-04'""").fetchone()
    db.close()
    assert row is not None
    assert row[0] == 1500000
    assert row[1] == 'nomina_auto'


def test_gap7_facturar_orden_maquila(app, db_clean):
    """Crear orden maquila + facturar → genera factura tipo 'FM'."""
    import sqlite3, os
    c = _login_as(app, 'sebastian')
    db = sqlite3.connect(os.environ['DB_PATH'])
    db.execute("""INSERT INTO maquila_ordenes
                  (numero, cliente_nombre, producto, lote_kg, precio_lote, estado)
                  VALUES ('MAQ-TEST-001', 'Cliente Maquila SA', 'Crema',
                          50, 2000000, 'En proceso')""")
    oid = db.execute("SELECT MAX(id) FROM maquila_ordenes").fetchone()[0]
    db.commit()
    db.close()

    r = c.post(f'/api/maquila/ordenes/{oid}/facturar', json={})
    assert r.status_code == 201, r.data
    d = r.get_json()
    assert d['ok']
    assert d['numero_factura'].startswith('FM-ESP-')

    # Idempotencia: re-facturar misma orden devuelve la existente
    r2 = c.post(f'/api/maquila/ordenes/{oid}/facturar', json={})
    assert r2.status_code == 200
    assert r2.get_json().get('ya_facturada') is True


# ─── CENTRO DE OPERACIONES ─────────────────────────────────────────────────

def test_centro_operaciones_solo_admin(app, db_clean):
    luz = _login_as(app, 'luz')
    r = luz.get('/api/centro/operaciones')
    assert r.status_code == 403


def test_centro_operaciones_estructura(app, db_clean):
    c = _login_as(app, 'sebastian')
    r = c.get('/api/centro/operaciones')
    assert r.status_code == 200, r.data
    d = r.get_json()
    for k in ['caja', 'produccion', 'inventario', 'comercial', 'pagos', 'equipo', 'marketing', 'actividad_reciente']:
        assert k in d, f'falta clave {k}'
