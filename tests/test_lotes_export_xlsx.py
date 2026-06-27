"""Stock por Lote · export .xlsx NATIVO (27-jun) · un .xlsx real (zip → 'PK'), no el truco HTML-como-Excel."""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def test_lotes_export_xlsx(app, db_clean):
    c = _login(app)
    r = c.get("/api/lotes/export-xlsx")
    assert r.status_code == 200, r.data[:200]
    assert 'spreadsheetml' in r.headers.get('Content-Type', ''), r.headers.get('Content-Type')
    assert r.headers.get('Content-Disposition', '').endswith('.xlsx"'), r.headers.get('Content-Disposition')
    assert r.data[:2] == b'PK', r.data[:20]  # .xlsx = zip → empieza con PK (no HTML)
