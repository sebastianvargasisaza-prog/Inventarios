# -*- coding: utf-8 -*-
"""El tamaño es la IDENTIDAD de una presentación: no se clona de otra.

Sebastián (12-ago), mirando el modal de Niacinamida y de AZ HIBRID: *"ya vi lo que pasa, está
clonando la de 30 como si fuera de 15 ml en varios productos"*. Tenía razón y la causa era una
sola línea: la expansión por tono elegía UNA presentación modelo por producto y le copiaba su
volumen y su frasco a **todos** los SKU, incluidos los de otro tamaño.

El daño no es cosmético. Esa fila le pide a Compras el frasco equivocado, y además la venta del
tamaño de 30 se cuenta DOS VECES: una por la fila genérica de 30 ml (que quedó activa sin SKU, así
que su grupo se reparte por volumen) y otra por la fila clonada que sí declara el SKU.

Acá se prueban las dos mitades: que la expansión ya no pueda volver a hacerlo, y que lo que quedó
mal se pueda reparar sin adivinar.
"""
import pytest

TEST_PASSWORD = "TestPass123"
PROD = "VOLCLON TEST SUERO"


@pytest.fixture
def planta_client(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "smurillo", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Se limpia ANTES de sembrar: un `finally` no corre si el proceso muere (M103)."""
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre LIKE 'VOLCLON TEST%'")
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'VOLCLON TEST%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'VC-%'")
        conn.commit()


def _envase(app, cod, desc):
    with app.app_context():
        from database import get_db
        conn = get_db()
        # ⚠ `stock_actual` explícito en 0: el CREATE TABLE tiene DEFAULT 2000 y un alta descuidada
        # inventa 2000 unidades (M100).
        conn.cursor().execute(
            "INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, estado) "
            "VALUES (?,?,'Envase',0,'Activo')", (cod, desc))
        conn.commit()


def _sku(app, sku, tono, vol):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO sku_producto_map (sku, producto_nombre, tono_label, volumen_ml, es_regalo) "
            "VALUES (?,?,?,?,0)", (sku, PROD, tono, vol))
        conn.commit()


def _pres(app, cod, etiqueta, vol, envase, sku=None):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, sku_shopify, activo) VALUES (?,?,?,?,?,?,1)",
                  (PROD, cod, etiqueta, vol, envase, sku))
        conn.commit()
        return c.lastrowid


def _fila(app, sku):
    with app.app_context():
        from database import get_db
        return get_db().cursor().execute(
            "SELECT COALESCE(volumen_ml,0), COALESCE(envase_codigo,''), COALESCE(activo,1) "
            "  FROM producto_presentaciones "
            " WHERE producto_nombre=? AND UPPER(TRIM(COALESCE(sku_shopify,'')))=?",
            (PROD, sku.upper())).fetchone()


# ---------------------------------------------------------------- la expansión

def test_NO_le_clona_a_un_SKU_de_30_el_frasco_de_15(app, planta_client):
    """El caso exacto de AZ HIBRID: el SKU de 30 ml no puede nacer con el frasco de 15.

    Sin presentación de 30 ml de la que copiar, la fila NO se crea: se declara por qué. Copiar el
    frasco del otro tamaño es precisamente el defecto (M100: lo que no se puede resolver se dice,
    no se adivina).
    """
    _limpiar(app)
    _envase(app, 'VC-E15', 'Frasco 15 ml')
    _sku(app, 'VCT15', 'Quince', 15)
    _sku(app, 'VCT30', 'Treinta', 30)
    _pres(app, 'V15', '15ml', 15, 'VC-E15', 'VCT15')
    _pres(app, 'V15B', '15ml b', 15, 'VC-E15')     # 2ª fila para que haya algo que expandir

    r = planta_client.get('/api/mee/expandir-tonos')
    assert r.status_code == 200
    d = r.get_json()
    creables = [t['sku'] for p in d['propuestas'] if p['producto'] == PROD for t in p['tonos']]
    assert 'VCT30' not in creables, \
        'le abrió una fila al SKU de 30 ml copiando el frasco de 15: %s' % creables
    # Y DICE por qué, en su lista propia: el tono se conoce, lo que falta es la presentación de
    # 30 ml. Reportarlo como "sin tono" lo mandaría a cargar un tono que ya está y dejaría el
    # hueco real sin nombrar -- un "no se pudo" sin motivo obliga a adivinar (M127).
    motivos = [x['motivo'] for g in d.get('sin_modelo', []) for x in g['skus']
               if x['sku'] == 'VCT30']
    assert motivos and '30' in motivos[0], \
        'no dijo POR QUÉ no pudo con el de 30 ml: %s' % d.get('sin_modelo')
    assert 'VCT30' not in str(d.get('sin_tono')), \
        'lo reportó como "sin tono" cuando el tono se conoce: manda a arreglar lo que no es'


def test_cuando_SI_existe_la_de_30_copia_de_ESA_y_no_de_la_de_15(app, planta_client):
    """El modelo se elige por VOLUMEN. Con las dos presentaciones cargadas, el tono de 30 nace
    con el frasco de 30."""
    _limpiar(app)
    _envase(app, 'VC-E15', 'Frasco 15 ml')
    _envase(app, 'VC-E30', 'Frasco 30 ml')
    _sku(app, 'VCT15', 'Quince', 15)
    _sku(app, 'VCT30', 'Treinta', 30)
    _pres(app, 'V15', '15ml', 15, 'VC-E15')
    _pres(app, 'V30', '30ml', 30, 'VC-E30')

    prop = [p for p in planta_client.get('/api/mee/expandir-tonos').get_json()['propuestas']
            if p['producto'] == PROD]
    assert prop, 'no propuso nada teniendo los dos tamaños cargados'
    de30 = [t for p in prop for t in p['tonos'] if t['sku'] == 'VCT30']
    assert de30, 'no propuso el tono de 30 ml'
    assert de30[0]['modelo']['envase'] == 'VC-E30', \
        'copió el frasco de 15 para el tono de 30: %s' % de30[0]['modelo']

    r = planta_client.post('/api/mee/expandir-tonos-aplicar', json={'productos': [PROD]},
                           headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    f30 = _fila(app, 'VCT30')
    assert f30 and abs(f30[0] - 30) < 0.01 and f30[1] == 'VC-E30', \
        'la fila de 30 ml quedó con otro volumen o con otro frasco: %s' % (f30,)
    f15 = _fila(app, 'VCT15')
    assert f15 and abs(f15[0] - 15) < 0.01 and f15[1] == 'VC-E15', \
        'la de 15 ml salió mal: %s' % (f15,)


# ------------------------------------------------------------- la reparación

def test_repara_la_fila_clonada_y_retira_la_generica_que_doble_contaba(app, planta_client):
    """Reproduce el estado REAL de AZ HIBRID: la fila del SKU de 30 quedó en 15 ml con el frasco
    de 15, y la genérica de 30 ml sigue activa sin SKU. Las dos cosas juntas hacen que la venta de
    30 ml se cuente dos veces."""
    _limpiar(app)
    _envase(app, 'VC-E15', 'Frasco 15 ml')
    _envase(app, 'VC-E30', 'Frasco 30 ml')
    _sku(app, 'VCT15', 'Quince', 15)
    _sku(app, 'VCT30', 'Treinta', 30)
    _pres(app, 'V15', '15 ml', 15, 'VC-E15', 'VCT15')
    gen30 = _pres(app, 'V30', '30ml', 30, 'VC-E30')            # genérica, sin SKU
    mala = _pres(app, 'T-VCT30', '30 ML', 15, 'VC-E15', 'VCT30')  # clonada del tamaño equivocado

    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    ids = [x['id'] for x in d['volumen_mal']]
    assert mala in ids, 'no detectó la fila clonada: %s' % d['resumen']
    _f = [x for x in d['volumen_mal'] if x['id'] == mala][0]
    assert _f['envase_correcto'] == 'VC-E30' and abs(_f['volumen_real'] - 30) < 0.01
    assert _f['dar_de_baja'] and _f['dar_de_baja']['id'] == gen30, \
        'no vio que la genérica de 30 ml queda doble-contando'

    r = planta_client.post('/api/mee/presentaciones-volumen-aplicar', json={'ids': [mala]},
                           headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    f30 = _fila(app, 'VCT30')
    assert f30 and abs(f30[0] - 30) < 0.01 and f30[1] == 'VC-E30' and f30[2] == 1, \
        'la fila no quedó en sus 30 ml con su frasco: %s' % (f30,)
    with app.app_context():
        from database import get_db
        act = get_db().cursor().execute(
            "SELECT COALESCE(activo,1) FROM producto_presentaciones WHERE id=?", (gen30,)).fetchone()
    assert act and act[0] == 0, 'la genérica de 30 ml quedó activa y sigue doble-contando'


def test_sin_presentacion_del_tamano_correcto_NO_se_toca(app, planta_client):
    """El caso del LIP SERUM: el SKU dice 30 ml y el producto no tiene ninguna presentación de 30.

    Corregirle el volumen dejándole el frasco de 10 sería peor que no hacer nada: quedaría una
    fila de 30 ml pidiendo el envase de 10. Se declara y se deja quieta.
    """
    _limpiar(app)
    _envase(app, 'VC-E10', 'Frasco 10 ml')
    _sku(app, 'VCT10', 'Diez', 10)
    _sku(app, 'VCT30', 'Treinta', 30)
    _pres(app, 'V10', '10 ml', 10, 'VC-E10', 'VCT10')
    huerf = _pres(app, 'T-VCT30', '30 mL', 10, 'VC-E10', 'VCT30')

    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    assert huerf not in [x['id'] for x in d['volumen_mal']], \
        'la ofreció como corregible sin tener de dónde copiar el frasco'
    sd = [x for x in d['sin_destino'] if x['id'] == huerf]
    assert sd, 'no la declaró como sin destino: %s' % d['resumen']
    # ⚠ El motivo tiene que ofrecer las DOS lecturas, porque llevan a arreglos OPUESTOS y el
    # sistema no puede elegir. Sebastián, sobre el lip serum: *"es solo de 10 ml, no es de 30"* --
    # ahí la respuesta era corregir el SKU, y un motivo que sólo dice "falta cargar esa
    # presentación" manda a crear una que no debería existir (M100/M130).
    _mot = sd[0]['motivo']
    assert 'falta cargarla' in _mot and 'volumen del SKU' in _mot, \
        'el motivo ofrece una sola salida y puede ser la equivocada: %r' % _mot
    assert sorted(sd[0].get('tamanos_del_producto') or []) == [10.0], \
        'no dice qué tamaños SÍ tiene el producto: %s' % sd[0].get('tamanos_del_producto')

    # y el apply la ignora aunque se la manden a la fuerza
    planta_client.post('/api/mee/presentaciones-volumen-aplicar', json={'ids': [huerf]},
                       headers={'Origin': 'http://localhost'})
    f = _fila(app, 'VCT30')
    assert f and abs(f[0] - 10) < 0.01 and f[1] == 'VC-E10', \
        'tocó una fila que no sabía cómo arreglar: %s' % (f,)


def test_lista_las_genericas_que_conviven_con_filas_por_SKU(app, planta_client):
    """El caso del LIP SERUM en el modal: siete tarjetas con el mismo número.

    Una fila activa SIN SKU en un tamaño que ya tiene filas CON SKU deja el grupo incompleto, así
    que ese tamaño vuelve a repartirse por volumen -- o sea, la misma cantidad de cada etiqueta.
    Se LISTA y no se da de baja sola: varias son tonos reales a los que sólo les falta el SKU, y
    retirarlas perdería su frasco (M19).
    """
    _limpiar(app)
    _envase(app, 'VC-E10', 'Frasco 10 ml')
    _envase(app, 'VC-E10B', 'Frasco 10 ml cafe')
    _sku(app, 'VCT10', 'Diez', 10)
    _pres(app, 'V10', '10 ml', 10, 'VC-E10', 'VCT10')
    suelta = _pres(app, 'V10CAFE', 'Cafe claro', 10, 'VC-E10B')

    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    g = [x for x in d['genericas_conviviendo'] if x['id'] == suelta]
    assert g, 'no listó la fila sin SKU que rompe el reparto: %s' % d['resumen']
    assert 'VCT10' in g[0]['convive_con']
    with app.app_context():
        from database import get_db
        act = get_db().cursor().execute(
            "SELECT COALESCE(activo,1) FROM producto_presentaciones WHERE id=?",
            (suelta,)).fetchone()
    assert act and act[0] == 1, 'la dio de baja sola: eso pierde el frasco de ese tono'


# ------------------------------------------------------- el texto de la etiqueta

def test_la_etiqueta_no_puede_decir_un_volumen_y_la_fila_otro(app, planta_client):
    """Sebastián, sobre la tarjeta YA corregida: arriba decía "de 30 ml" y la etiqueta
    "30ML 10 ml".

    El generador horneaba el volumen dentro del texto, así que al corregir la columna el texto
    quedó viejo y la misma tarjeta mostró dos volúmenes del mismo hecho. Se alinea el volumen
    FINAL -- lo único que escribió el generador -- y el nombre de adelante se conserva.
    """
    _limpiar(app)
    _envase(app, 'VC-E30', 'Frasco 30 ml')
    _sku(app, 'VCT30', 'Treinta', 30)
    fid = _pres(app, 'T-VCT30', '30ML 10 ml', 30, 'VC-E30', 'VCT30')

    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    e = [x for x in d.get('etiqueta_desalineada', []) if x['id'] == fid]
    assert e, 'no vio que la etiqueta dice 10 ml y la fila es de 30: %s' % d['resumen']
    assert e[0]['etiqueta_nueva'] == '30ML', \
        'se comió el nombre en vez de sólo el volumen viejo: %r' % e[0]['etiqueta_nueva']

    planta_client.post('/api/mee/presentaciones-volumen-aplicar', json={'ids': [fid]},
                       headers={'Origin': 'http://localhost'})
    with app.app_context():
        from database import get_db
        etq = get_db().cursor().execute(
            "SELECT etiqueta FROM producto_presentaciones WHERE id=?", (fid,)).fetchone()
    assert etq and etq[0] == '30ML', 'la etiqueta no quedó alineada: %s' % (etq,)


def test_una_etiqueta_que_YA_coincide_no_se_toca(app, planta_client):
    """Un texto redundante pero consistente ("10ML 10 ml" en una fila de 10 ml) no es un defecto.

    Tocar datos que una persona ve, sin que estén mal, es cambiarle la pantalla por gusto propio.
    """
    _limpiar(app)
    _envase(app, 'VC-E10', 'Frasco 10 ml')
    _sku(app, 'VCT10', 'Diez', 10)
    fid = _pres(app, 'T-VCT10', '10ML 10 ml', 10, 'VC-E10', 'VCT10')
    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    assert fid not in [x['id'] for x in d.get('etiqueta_desalineada', [])], \
        'ofreció cambiar una etiqueta que no contradice nada'


def test_un_nombre_sin_volumen_al_final_nunca_se_toca(app, planta_client):
    """"Café claro" no menciona ningún volumen: no hay nada que alinear y no se inventa."""
    _limpiar(app)
    _envase(app, 'VC-E10', 'Frasco 10 ml')
    _sku(app, 'VCT10', 'Diez', 10)
    fid = _pres(app, 'T-VCT10', 'Cafe claro', 10, 'VC-E10', 'VCT10')
    d = planta_client.get('/api/mee/presentaciones-volumen').get_json()
    assert fid not in [x['id'] for x in d.get('etiqueta_desalineada', [])], \
        'quiso tocar un nombre escrito a mano'
