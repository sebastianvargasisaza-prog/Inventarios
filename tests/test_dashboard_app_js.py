"""PERF 26-jun (Increment 1) · el 2º bloque JS grande del dashboard se extrae a /planta-app.js
(archivo externo cacheable). Estos tests fijan el contrato: la ruta sirve el JS y la HTML del
dashboard lo referencia. Si la extracción se rompiera (fallback inline), el primero falla y avisa."""


def test_planta_app_js_se_sirve(client):
    r = client.get('/planta-app.js')
    assert r.status_code == 200, 'la ruta debe servir el JS (extracción OK)'
    assert 'javascript' in r.headers.get('Content-Type', '').lower()
    assert 'immutable' in r.headers.get('Cache-Control', ''), 'debe ser cacheable immutable'
    assert len(r.data) > 100000, 'debe ser el bloque grande (~12k líneas)'
    assert b'Programar' in r.data, 'contenido esperado del bloque (Programar Producción Modal)'


def test_dashboard_referencia_app_js(logged_client):
    r = logged_client.get('/planta')
    assert r.status_code == 200
    assert b'/planta-app.js?v=' in r.data, 'la HTML servida debe referenciar el archivo externo'
    # el 2º bloque ya NO debe estar inline en la HTML servida
    assert b'// Cache global de areas + operarios (cargado al abrir modal' not in r.data
