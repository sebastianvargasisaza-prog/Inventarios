"""Tests UX de Compliance: CSRF helpers + paginacion + busqueda en CAPA/Hallazgos."""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_pagina_compliance_tiene_csrf_helpers(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/compliance")
    body = r.get_data(as_text=True)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    assert "/api/csrf-token" in body
    # Sin patrones antiguos
    assert "method:'POST'" not in body
    assert "method:'PATCH'" not in body
    assert "method:'DELETE'" not in body


def test_pagina_compliance_tiene_paginacion(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/compliance")
    body = r.get_data(as_text=True)
    assert "TBL_STATE" in body
    assert "_paginar" in body
    assert "_filtrar" in body
    assert "buscarTabla" in body
    # Divs de paginacion
    for tab in ('pg-capa', 'pg-hall'):
        assert f'id="{tab}"' in body, f'falta id="{tab}"'
    # Cajas de busqueda
    for tabla in ('capa', 'hall'):
        assert f"buscarTabla('{tabla}'" in body


def test_endpoint_kpis_compliance(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/compliance/kpis")
    assert r.status_code == 200


def test_endpoint_cronogramas(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/compliance/cronogramas")
    assert r.status_code == 200


def test_endpoint_capa(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/compliance/capa")
    assert r.status_code == 200


def test_endpoint_hallazgos(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/compliance/hallazgos")
    assert r.status_code == 200
