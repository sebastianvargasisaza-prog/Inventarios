"""El legajo de envasado es UNA vista continua (29-jul).

Sebastián: el legajo estaba partido en dos pantallas y el operario -con guantes, en piso-
tenía que apretar un botón intermedio para llegar al despeje y a los controles. En MyBatch
son las 7 secciones seguidas en una sola página.

Unir dos pantallas NO es pegar sus HTML: comparten 18 clases CSS y **6 están definidas
distinto** (`.grid` es 4 columnas en una y 5 en la otra, `.bt` tiene otro padding), así que
pegarlas rompería las dos. El CSS de la parte embebida va encapsulado bajo `.ie-emb` y las
5 funciones que chocaban van con prefijo `ie_` -- RENOMBRADAS, no borradas, porque no son
idénticas (su `estCol` trata 'completado' distinto).

Estos tests fijan las tres cosas que se romperían en silencio si alguien vuelve a tocarlo:
la sección que falta, la función que se pisa, y el botón que quedó apuntando a la nada.
"""
import re

import pytest


@pytest.fixture(scope="module")
def legajo(app):
    """Depende de `app` a propósito: importar el template arrastra `config`, y si corre
    antes que la fixture `app` deja `config` cacheado sin las claves de los usuarios y
    revienta el login de los tests siguientes (M112)."""
    from api.blueprints import brd
    return brd._ENVASADO_LEGAJO_HTML.replace('__EBR_ID__', '1')


def _scripts(t):
    return ' '.join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', t, re.S))


SECCIONES = [
    ('1. Precauciones', 'Precaucion'),
    ('2. Despeje de línea', 'Despeje'),
    ('3. Recepción de material de envase', 'Materiales de Envase'),
    ('4. Envasado · unidades por presentación', 'Presentaci'),
    ('5. Controles en proceso', 'Control'),
    ('6. Observaciones del proceso', 'Observaci'),
    ('7. Registros físicos', 'Registros'),
    ('Conciliación del granel', 'Conciliaci'),
    ('Aprobación de la orden', 'bandaAprobacion'),
]


@pytest.mark.parametrize('nombre,patron', SECCIONES, ids=[s[0] for s in SECCIONES])
def test_las_siete_secciones_estan_en_la_MISMA_pagina(legajo, nombre, patron):
    """Antes, cuatro de estas vivían detrás de un botón. El operario las lee de arriba
    abajo, como en MyBatch."""
    assert patron in legajo, 'la sección %r no está en el legajo' % nombre


def test_el_boton_ya_no_saca_al_operario_de_la_pagina(legajo):
    assert 'href="#seccion-instrucciones"' in legajo, (
        'el botón volvió a navegar a otra pantalla')
    assert 'id="seccion-instrucciones"' in legajo, 'el ancla de destino no existe'


def test_ninguna_funcion_global_se_declara_dos_veces(legajo):
    """Una redeclaración pisa a la otra SIN error: la pantalla queda usando la versión
    equivocada y no hay forma de notarlo mirando el diff.

    Se miran sólo las de nivel superior -- las anidadas (`n`, `v` dentro de un modal)
    tienen scope propio y repetirse es legítimo.
    """
    top = re.findall(r'^(?:async\s+)?function\s+(\w+)\s*\(', _scripts(legajo), re.M)
    dup = sorted({f for f in top if top.count(f) > 1})
    assert not dup, 'funciones globales duplicadas (una pisa a la otra): %s' % dup


def test_las_funciones_que_chocaban_quedaron_con_prefijo(legajo):
    """Se renombraron, no se borraron: `estCol` de las instrucciones trata 'completado'
    distinto que la del legajo, así que dejar una sola cambiaría un color de estado."""
    js = _scripts(legajo)
    for f in ('ie_esc', 'ie_estCol', 'ie_fld', 'ie_load', 'ie_prox'):
        assert ('function %s' % f) in js, 'falta %s' % f
    assert 'ie_load();' in js, 'la parte embebida nunca se carga'


def test_el_css_embebido_no_pisa_al_legajo(legajo):
    """Las 6 clases definidas distinto en las dos pantallas conservan la regla PROPIA del
    legajo; la versión embebida vive encapsulada bajo `.ie-emb`."""
    st = re.search(r'<style>(.*?)</style>', legajo, re.S).group(1)
    for c in ('grid', 'bt', 'val', 'prod', 'ab', 'act'):
        assert re.search(r'(?:^|[,}\n])\s*\.' + c + r'\s*[,{]', st, re.M), (
            'se perdió la regla propia de .%s' % c)
    assert '.ie-emb' in st, 'el CSS embebido no quedó encapsulado'


def test_cada_boton_tiene_su_funcion_y_cada_id_existe(legajo):
    """M112: el hueco vive entre el botón y su destino, y ni el golden ni el node-check
    lo ven (borrar un div no rompe la sintaxis)."""
    sin_fn = [f for f in set(re.findall(r'onclick="(\w+)\(', legajo))
              if ('function %s' % f) not in legajo and ('async function %s' % f) not in legajo]
    assert not sin_fn, 'botones que llaman a funciones inexistentes: %s' % sin_fn
    ids = set(re.findall(r'id="([\w-]+)"', legajo))
    creados = set(re.findall(r"\.id\s*=\s*'([\w-]+)'", legajo))
    faltan = [i for i in set(re.findall(r"getElementById\('([\w-]+)'\)", legajo))
              if i not in ids | creados]
    assert not faltan, 'getElementById sobre ids que no existen: %s' % faltan


def test_la_pagina_suelta_de_instrucciones_sigue_existiendo(app):
    """Se conserva: se imprime y se enlaza desde otros lados. Unificar la vista no puede
    romper una ruta que ya estaba en uso."""
    from api.blueprints import brd
    assert hasattr(brd, '_INSTRUCCIONES_ENVASADO_HTML')
    rutas = {r.rule for r in app.url_map.iter_rules()}
    assert '/planta/instrucciones-envasado/<int:ebr_id>' in rutas


def test_el_legajo_carga_de_verdad(app, db_clean):
    """Que el template tenga las secciones no prueba que la página responda."""
    from .conftest import TEST_PASSWORD, csrf_headers
    from database import get_db
    LOTE = 'ZZ-EBR-CONTINUA'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if f:
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE, LOTE, 'en_proceso', 'envasado', 'sebastian', '2026-07-29T10:00:00', 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get('/planta/legajo-envasado/%d' % eid)
    assert r.status_code == 200, r.data[:300]
    assert b'seccion-instrucciones' in r.data, 'la parte embebida no llegó al HTML servido'
