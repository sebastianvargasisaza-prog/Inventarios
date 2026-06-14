"""14-jun · Gobierno GMP de Aseguramiento (5 procesos nuevos) + fix de permiso.

- Miguel (dueño de Aseguramiento, fuera de CALIDAD_USERS tras el split de roles)
  DEBE poder escribir en su módulo. Regresión: _autorizados_escritura() solo
  incluía CALIDAD|ADMIN → 403 para Miguel. Ahora suma ASEGURAMIENTO_USERS.
- Revisión por la dirección: programar + ejecutar (snapshot de KPIs, CAS).
- Calificación de proveedores: upsert reusando el maestro de Compras.
- Validación de equipos IQ/OQ/PQ, FMEA (RPN), acuerdos de calidad.
- Un usuario sin rol de calidad/aseguramiento NO puede escribir (403).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _audit_count(accion):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_log WHERE accion=?", (accion,)).fetchone()[0]
    finally:
        conn.close()


# ── Fix de permiso: Miguel (Aseguramiento) puede escribir ────────────────
def test_miguel_aseguramiento_puede_escribir_fmea(app, db_clean):
    c = _login(app, 'miguel')
    r = c.post('/api/aseguramiento/fmea', json={
        'producto_nombre': 'GEL HIDRATANTE', 'modo_falla': 'pH fuera de rango',
        'severidad': 7, 'ocurrencia': 3, 'deteccion': 4, 'control_actual': 'medición en IPC'},
        headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    assert r.get_json()['rpn'] == 84  # 7*3*4


def test_miguel_aseguramiento_puede_escribir_desviacion(app, db_clean):
    """El split de roles no debe bloquear a Miguel en los flujos AC ya existentes."""
    c = _login(app, 'miguel')
    r = c.post('/api/aseguramiento/desviaciones', json={
        'tipo': 'proceso', 'origen': 'produccion',
        'descripcion': 'desviación de temperatura en marmita durante fabricación'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]


def test_usuario_sin_rol_no_escribe_gobierno(app, db_clean):
    """valentina no es calidad ni aseguramiento → 403 en escritura de gobierno."""
    c = _login(app, 'valentina')
    r = c.post('/api/aseguramiento/fmea', json={
        'producto_nombre': 'X', 'modo_falla': 'y', 'severidad': 1, 'ocurrencia': 1, 'deteccion': 1},
        headers=csrf_headers())
    assert r.status_code == 403, r.data[:300]


# ── Revisión por la Dirección ────────────────────────────────────────────
def test_revision_direccion_programar_y_ejecutar(app, db_clean):
    c = _login(app, 'miguel')
    antes = _audit_count('CREAR_REVISION_DIRECCION')
    r = c.post('/api/aseguramiento/revision-direccion',
               json={'periodo': '2026', 'fecha_planeada': '2026-12-15'}, headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    rid = r.get_json()['id']
    assert _audit_count('CREAR_REVISION_DIRECCION') == antes + 1

    # KPIs vivos vienen en el GET
    g = c.get('/api/aseguramiento/revision-direccion').get_json()
    assert 'kpis_actuales' in g and 'desviaciones_abiertas' in g['kpis_actuales']

    # Ejecutar el acta (toma snapshot, pasa a 'ejecutada')
    e = c.post('/api/aseguramiento/revision-direccion/%d/ejecutar' % rid,
               json={'fortalezas': 'sistema robusto', 'decisiones': 'aprobar plan 2027',
                     'conducido_por': 'miguel'}, headers=csrf_headers())
    assert e.status_code == 200, e.data[:300]

    # CAS: segunda ejecución sobre el mismo id ya no está 'planeada' → 409
    e2 = c.post('/api/aseguramiento/revision-direccion/%d/ejecutar' % rid,
                json={'decisiones': 'otra'}, headers=csrf_headers())
    assert e2.status_code == 409, e2.data[:300]


# ── Calificación de proveedores (reusa maestro de Compras) ───────────────
def test_calificar_proveedor_upsert_idempotente(app, db_clean):
    # crear un proveedor en el maestro de compras (user con permiso de compras)
    adm = _login(app, 'sebastian')
    cr = adm.post('/api/proveedores-compras', json={'nombre': 'PROV-GMP-TEST'}, headers=csrf_headers())
    assert cr.status_code in (200, 201), cr.data[:300]

    c = _login(app, 'miguel')
    r = c.post('/api/aseguramiento/proveedores-calificacion', json={
        'proveedor': 'PROV-GMP-TEST', 'criticidad': 'critico', 'requiere_visita': True,
        'estado': 'aprobado', 'fecha_reevaluacion': '2027-06-14'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]

    # upsert: re-calificar el mismo proveedor no duplica, actualiza
    r2 = c.post('/api/aseguramiento/proveedores-calificacion', json={
        'proveedor': 'PROV-GMP-TEST', 'criticidad': 'no_critico', 'estado': 'aprobado_condicional'},
        headers=csrf_headers())
    assert r2.status_code == 200

    g = c.get('/api/aseguramiento/proveedores-calificacion').get_json()
    fila = [x for x in g['proveedores'] if x['proveedor'] == 'PROV-GMP-TEST']
    assert len(fila) == 1, 'upsert no debe duplicar la calificación'
    assert fila[0]['estado'] == 'aprobado_condicional'
    assert fila[0]['criticidad'] == 'no_critico'


def test_validacion_equipos_y_acuerdos(app, db_clean):
    c = _login(app, 'miguel')
    r = c.post('/api/aseguramiento/validacion-equipos', json={
        'equipo_codigo': 'EQ-MARMITA-01', 'tipo': 'OQ', 'estado': 'aprobado',
        'criterios_aceptacion': 'temperatura ±2°C'}, headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]

    a = c.post('/api/aseguramiento/acuerdos-calidad', json={
        'tercero': 'Maquila Cosmética SAS', 'tipo': 'maquila', 'version': '1',
        'fecha_renovacion': '2027-01-01'}, headers=csrf_headers())
    assert a.status_code == 201, a.data[:300]

    ge = c.get('/api/aseguramiento/validacion-equipos').get_json()
    assert any(x['equipo_codigo'] == 'EQ-MARMITA-01' for x in ge['validaciones'])
    ga = c.get('/api/aseguramiento/acuerdos-calidad').get_json()
    assert any(x['tercero'] == 'Maquila Cosmética SAS' for x in ga['acuerdos'])


def test_tipo_invalido_rechazado(app, db_clean):
    c = _login(app, 'miguel')
    r = c.post('/api/aseguramiento/validacion-equipos', json={
        'equipo_codigo': 'EQ-X', 'tipo': 'BASURA'}, headers=csrf_headers())
    assert r.status_code == 400, r.data[:300]
