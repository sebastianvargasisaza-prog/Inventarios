"""PERF 26-jun · el dashboard monolítico se parte en 2 archivos JS externos cacheables:
  /planta-core.js (1er bloque · Increment 2) y /planta-app.js (2º bloque · Increment 1).
Estos tests fijan el contrato: ambas rutas sirven su JS, la HTML los referencia en ORDEN correcto
(globals inline → core → app) y las interpolaciones {usuario}/{es_admin} NO viajan en los archivos
cacheados (van en un <script> inline). Si una extracción se rompe (fallback inline), su test falla y avisa."""


def test_planta_app_js_se_sirve(client):
    r = client.get('/planta-app.js')
    assert r.status_code == 200, 'la ruta debe servir el JS (extracción OK)'
    assert 'javascript' in r.headers.get('Content-Type', '').lower()
    assert 'immutable' in r.headers.get('Cache-Control', ''), 'debe ser cacheable immutable'
    assert len(r.data) > 100000, 'debe ser el bloque grande'
    assert b'Programar' in r.data


def test_planta_core_js_se_sirve(client):
    r = client.get('/planta-core.js')
    assert r.status_code == 200, 'la ruta debe servir el 1er bloque (extracción OK)'
    assert 'javascript' in r.headers.get('Content-Type', '').lower()
    assert 'immutable' in r.headers.get('Cache-Control', '')
    assert len(r.data) > 100000
    # el 1er bloque arranca con las globales fData/OPER_ACTUAL
    assert b'OPER_ACTUAL' in r.data
    # NO debe traer interpolaciones (van en el <script> inline, no en el archivo cacheado)
    assert b'{usuario}' not in r.data and b'{es_admin}' not in r.data


def test_dashboard_referencia_y_orden(logged_client):
    r = logged_client.get('/planta')
    assert r.status_code == 200
    html = r.data.decode('utf-8', 'replace')
    assert '/planta-core.js?v=' in html and '/planta-app.js?v=' in html, 'debe referenciar ambos archivos'
    # ORDEN de carga: globals inline (con el usuario real) → core.js → app.js
    assert '__DASH_USR' in html, 'falta el <script> inline de globals'
    assert html.index('__DASH_USR') < html.index('/planta-core.js') < html.index('/planta-app.js')
    # los bloques grandes ya NO están inline en la HTML servida
    assert '// Cache global de areas + operarios (cargado al abrir modal' not in html
    # el usuario real quedó inyectado en el inline (no el placeholder)
    assert '{usuario}' not in html
