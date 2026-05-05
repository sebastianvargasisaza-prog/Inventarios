"""Tests del feature 'Revisar mínimos' en Bodega MP (Sebastian 5-may-2026).

El equipo de planta necesita verificar si los stock_minimo configurados
en maestro_mps son reales antes de fiarse de las alertas. Antes solo
admin podia ver la auditoria desde /admin · ahora boton dentro de
Bodega MP que abre modal con audit + apply (admin only).

Cubre:
  - /api/planta/auditar-minimos accesible para todos los users autenticados
  - 401 sin login
  - Estructura del response (stats + auditoria + metodologia)
  - HTML expone botón + modal + funciones JS
  - Refactor: _compute_audit_minimos() helper compartido funciona desde
    ambos endpoints (admin y planta) con misma logica
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luis"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_planta_auditar_minimos_accesible_a_operario(app, db_clean):
    """Endpoint /api/planta/auditar-minimos accesible para Luis (operario)."""
    cs = _login(app, 'luis')
    r = cs.get('/api/planta/auditar-minimos')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert 'stats' in d
    assert 'auditoria' in d
    assert 'metodologia' in d


def test_planta_auditar_minimos_sin_login_401(app, db_clean):
    client = app.test_client()
    r = client.get('/api/planta/auditar-minimos')
    assert r.status_code == 401


def test_planta_auditar_minimos_horizonte_clamp(app, db_clean):
    """proyeccion_dias debe clampear entre 30-180."""
    cs = _login(app, 'luis')
    r = cs.get('/api/planta/auditar-minimos?proyeccion_dias=500')
    d = r.get_json()
    assert d['horizonte_proyeccion_dias'] == 180  # clamped to max
    r2 = cs.get('/api/planta/auditar-minimos?proyeccion_dias=10')
    d2 = r2.get_json()
    assert d2['horizonte_proyeccion_dias'] == 30  # clamped to min


def test_planta_auditar_minimos_stats_estructura_correcta(app, db_clean):
    cs = _login(app, 'luis')
    r = cs.get('/api/planta/auditar-minimos?proyeccion_dias=90')
    d = r.get_json()
    stats = d['stats']
    for k in ('total', 'ok', 'sub_protegido', 'sobre_protegido',
              'sin_minimo', 'sin_uso'):
        assert k in stats
    metodologia = d['metodologia']
    assert 'formula' in metodologia
    assert 'lead_times' in metodologia


def test_admin_auditar_minimos_misma_logica_que_planta(app, db_clean):
    """Refactor verificación: ambos endpoints retornan misma estructura."""
    cs_admin = _login(app, 'sebastian')
    cs_op = _login(app, 'luis')
    r_admin = cs_admin.get('/api/admin/auditar-minimos?proyeccion_dias=60')
    r_op = cs_op.get('/api/planta/auditar-minimos?proyeccion_dias=60')
    assert r_admin.status_code == 200
    assert r_op.status_code == 200
    a = r_admin.get_json()
    o = r_op.get_json()
    # Mismo horizonte → mismos stats (data idéntica)
    assert a['stats'] == o['stats']
    assert len(a['auditoria']) == len(o['auditoria'])


def test_dashboard_html_expone_boton_revisar_minimos(app, db_clean):
    cs = _login(app, 'luis')
    body = cs.get('/inventarios').get_data(as_text=True)
    # Botón en barra
    assert 'abrirRevisarMinimos' in body
    assert 'Revisar m' in body  # 'minimos' (sin acento o con HTML entity)
    # Modal
    assert 'modal-revisar-minimos' in body
    # Funciones JS
    assert 'cargarRevisarMinimos' in body
    assert 'aplicarRevisarMinimos' in body
    # Stats elementos
    assert 'rmin-stats' in body
    assert 'rmin-aplicar-box' in body


def test_aplicar_minimos_solo_admin(app, db_clean):
    """Luis (no admin) NO puede aplicar · debe recibir 403."""
    cs = _login(app, 'luis')
    r = cs.post('/api/admin/aplicar-minimos',
                json={'token': 'APLICAR_MINIMOS_RECALCULADOS_2026',
                      'proyeccion_dias': 90},
                headers=csrf_headers())
    assert r.status_code == 403


def test_aplicar_minimos_token_incorrecto_403(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.post('/api/admin/aplicar-minimos',
                json={'token': 'TOKEN_MAL', 'proyeccion_dias': 90},
                headers=csrf_headers())
    assert r.status_code == 403
