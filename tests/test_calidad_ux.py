"""Tests UX de Calidad: CSRF helpers + paginación + búsqueda en frontend.

Sebastian 3-may-2026: aplicar mismo patron zero-error que tecnica y
aseguramiento. 12 fetch refactor + helpers paginacion en NC, Calibraciones,
OOS.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_pagina_calidad_tiene_csrf_helpers(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/calidad")
    body = r.get_data(as_text=True)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    # Pre-fetch del token al cargar
    assert "/api/csrf-token" in body
    # Ningún fetch directo con method:'POST' sin _fetchOpts
    assert "method:'POST'" not in body
    assert "method:'PATCH'" not in body
    assert "method:'DELETE'" not in body


def test_pagina_calidad_tiene_paginacion(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/calidad")
    body = r.get_data(as_text=True)
    assert "TBL_STATE" in body
    assert "_paginar" in body
    assert "_filtrar" in body
    assert "_renderPag" in body
    assert "buscarTabla" in body
    assert "cambiarPag" in body
    # Divs de paginacion en NC, Cal, OOS
    for tab in ('pg-nc', 'pg-cal', 'pg-oos'):
        assert f'id="{tab}"' in body, f'falta id="{tab}"'


def test_pagina_calidad_tiene_cajas_busqueda(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/calidad")
    body = r.get_data(as_text=True)
    for tabla in ('nc', 'cal', 'oos'):
        assert f"buscarTabla('{tabla}'" in body, f"falta buscarTabla({tabla})"


def test_endpoint_dashboard_calidad(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/calidad/dashboard")
    assert r.status_code == 200


def test_endpoint_no_conformidades(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/calidad/no-conformidades")
    assert r.status_code == 200


def test_endpoint_calibraciones(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/calidad/calibraciones")
    assert r.status_code == 200


def test_endpoint_oos(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/calidad/oos")
    assert r.status_code == 200
