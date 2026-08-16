"""Tests UX de Calidad: CSRF helpers + paginación + búsqueda en frontend.

Sebastian 3-may-2026: aplicar mismo patron zero-error que tecnica y
aseguramiento. 12 fetch refactor + helpers paginacion en NC, Calibraciones,
OOS.
"""
import re as _re

from .conftest import TEST_PASSWORD, csrf_headers, contenido_pantalla


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cuerpo(c=None):
    """El HTML de /calidad MÁS el JS propio que la pantalla extrajo a su bundle.

    El JS de esta pantalla dejó de viajar inline el 16-ago (139 KB que ahora se sirven como
    `/calidad-app.js` cacheable). Lo que estos tests garantizan -- que la pantalla tenga sus
    helpers de CSRF y su paginación -- no cambió; lo que cambió es en qué archivo viven, o sea
    la implementación. Se re-apuntan al helper único en vez de parchear archivo por archivo
    (M143/M173).

    ⚠ Va por el módulo y NO descargando cada `<script src>` de la página servida: eso sumaría
    los widgets de chat y campana, que se inyectan en TODAS las pantallas y traen sus propios
    `fetch`. El test cuenta POST crudos para exigir que usen el wrapper con CSRF, así que
    contarle código ajeno lo vuelve un rojo que no habla de Calidad (y, peor, uno que se
    "arregla" aflojando el umbral).
    """
    return contenido_pantalla("calidad_html", "CALIDAD_HTML")


def test_pagina_calidad_tiene_csrf_helpers(app, db_clean):
    c = _login(app, "laura")
    body = _cuerpo(c)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    # Pre-fetch del token al cargar
    assert "/api/csrf-token" in body
    # Los fetch que MUTAN usan _fetchOpts (agrega CSRF). Los que no pueden usar el wrapper -- un
    # FormData de subida de archivo, o un POST que ya pidió su token -- van crudos, y entonces
    # DEBEN poner el encabezado a mano o el servidor los rechaza (M15).
    #
    # Antes esto se medía contando ("a lo sumo UN POST crudo"), y un umbral así se rompe el día
    # que aparece un segundo POST legítimo -- y se "arregla" subiendo el número, que es aflojar
    # el control sin mirarlo. Ahora se exige lo que de verdad importa: que CADA POST crudo lleve
    # el token en su propia llamada.
    crudos = [m.start() for m in _re.finditer(r"method:'POST'", body)]
    assert crudos, 'no se encontró ningún POST · el chequeo estaría pasando sin medir nada'
    sin_token = []
    for pos in crudos:
        ventana = body[max(0, pos - 400):pos + 400]
        if 'X-CSRF-Token' not in ventana:
            sin_token.append(body[max(0, pos - 120):pos + 80].replace('\n', ' '))
    assert not sin_token, (
        'POST que muta sin token CSRF (usá _fetchOpts o agregá el encabezado): %s'
        % sin_token[:2])
    assert "method:'PATCH'" not in body
    assert "method:'DELETE'" not in body


def test_pagina_calidad_tiene_paginacion(app, db_clean):
    c = _login(app, "laura")
    body = _cuerpo(c)
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
    body = _cuerpo(c)
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
