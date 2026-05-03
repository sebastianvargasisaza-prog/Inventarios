"""Tests UX de Aseguramiento: CSRF helpers + paginación + búsqueda en frontend.

Sebastian 3-may-2026: Aseguramiento es módulo más grande (39 endpoints,
11 tabs). Antes: 33 fetch directos sin CSRF token + sin paginación. Ahora
usa _fetchOpts() y TBL_STATE.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_pagina_aseguramiento_carga(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/aseguramiento")
    assert r.status_code == 200


def test_pagina_aseguramiento_tiene_csrf_helpers(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/aseguramiento")
    body = r.get_data(as_text=True)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    # Pre-fetch del token al cargar
    assert "/api/csrf-token" in body
    # Ningún fetch directo con method:'POST' sin _fetchOpts
    # (verificar que el patrón antiguo NO existe)
    assert "method:'POST'" not in body
    assert "method:'PATCH'" not in body
    assert "method:'DELETE'" not in body


def test_pagina_aseguramiento_tiene_paginacion(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/aseguramiento")
    body = r.get_data(as_text=True)
    # Helpers JS de paginación
    assert "TBL_STATE" in body
    assert "_paginar" in body
    assert "_filtrar" in body
    assert "_renderPag" in body
    assert "buscarTabla" in body
    assert "cambiarPag" in body
    # Divs de paginación por tabla
    for tab in ('pg-sgd', 'pg-desv', 'pg-cambios', 'pg-quejas',
                'pg-recalls', 'pg-conf', 'pg-audittrail'):
        assert f'id="{tab}"' in body, f'falta id="{tab}"'


def test_pagina_aseguramiento_tiene_cajas_busqueda(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/aseguramiento")
    body = r.get_data(as_text=True)
    # Cajas de búsqueda en cada tab (excluyendo SGD que ya tiene server-side q)
    for tabla in ('desv', 'cambios', 'quejas', 'recalls', 'conf', 'audittrail'):
        assert f"buscarTabla('{tabla}'" in body, f"falta buscarTabla({tabla})"


def test_dashboard_endpoint_funciona(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/dashboard")
    assert r.status_code == 200
    d = r.get_json()
    assert "fecha_hoy" in d
    assert "sgd" in d
    assert "capacitaciones" in d


def test_endpoint_desviaciones_get(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/desviaciones")
    assert r.status_code == 200
    d = r.get_json()
    assert "items" in d
    assert "kpis" in d


def test_endpoint_cambios_get(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/cambios")
    assert r.status_code == 200


def test_endpoint_quejas_get(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/quejas")
    assert r.status_code == 200


def test_endpoint_recalls_get(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/recalls")
    assert r.status_code == 200


def test_endpoint_sgd_listado_get(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/aseguramiento/sgd/listado")
    assert r.status_code == 200
