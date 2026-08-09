# -*- coding: utf-8 -*-
"""La tabla para normalizar el empaque: arrastra por nombre, deja vacío lo que no es, y deja
poner "no usa".

Sebastián (8-ago): *"ese módulo así no me sirve, quiero que sea producto, envase, tapa, etiqueta
etc, que arrastre todo por nombre, me deje vacío lo que no es, y me deje poner NO USA, porque no
he sido capaz, así me tengas que abrir en otra ventana"*.

Lo anterior era una lista de PENDIENTES; esto es una tabla donde se carga. La diferencia no es
cosmética: una lista dice qué falta, una tabla deja avanzar.

Las tres reglas se prueban una por una, y la segunda es la que más importa: **rellenar con "lo más
parecido" es como se le pone al producto el envase de otro**, y eso no da error -- da una compra
equivocada (M19/M137).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PROD = 'NORMTAB SUERO ZANAHORIA'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'NORMTAB%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'MEE-QQ-%'")
        c.commit()


def _mee(app, cod, desc, cat):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES (?,?,?,0)", (cod, desc, cat))
        c.commit()


def _pres(app, producto=PROD, frasco='MEE-QQ-FR', **kw):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, etiqueta_codigo, "
                  "activo) VALUES (?,'V30','30 ml',30,?,?,?,?,1)",
                  (producto, frasco, kw.get('tapa', ''), kw.get('caja', ''),
                   kw.get('etq', '')))
        c.commit()
        return c.execute("SELECT id FROM producto_presentaciones WHERE producto_nombre=?",
                         (producto,)).fetchone()[0]


def _fila(admin_client, pid):
    r = admin_client.get('/api/mee/normalizar-tabla')
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    f = [x for x in j['filas'] if x['id'] == pid]
    return (f[0] if f else None), j


def test_ARRASTRA_por_nombre(app, admin_client):
    """El caso real: 'SUERO ZANAHORIA' y 'ETIQUETA ZANAHORIA 30' comparten la palabra que los
    identifica, así que el vínculo se deduce."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA ZANAHORIA 30', 'Etiqueta')
    pid = _pres(app)
    f, _ = _fila(admin_client, pid)
    assert f and f['sugerido'].get('etiqueta') == 'MEE-QQ-ETQ', \
        'no arrastró la etiqueta por el nombre: %s' % (f or {}).get('sugerido')
    _limpiar(app)


def test_DEJA_VACIO_lo_que_no_coincide(app, admin_client):
    """La regla que evita el daño: rellenar con "lo más parecido" le pone al producto el envase de
    otro, y eso no da error -- da una compra equivocada."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA MANZANILLA 30', 'Etiqueta')     # nada que ver
    pid = _pres(app)
    f, _ = _fila(admin_client, pid)
    assert not f['sugerido'].get('etiqueta'), \
        'propuso una etiqueta que no tiene nada que ver: %s' % f['sugerido']
    _limpiar(app)


def test_si_DOS_empatan_deja_VACIO_y_lo_DICE(app, admin_client):
    """Dos candidatas no son una respuesta: se deja vacío y se muestra el empate, para que decida
    una persona (M19)."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ1', 'ETIQUETA ZANAHORIA FRENTE', 'Etiqueta')
    _mee(app, 'MEE-QQ-ETQ2', 'ETIQUETA ZANAHORIA DORSO', 'Etiqueta')
    pid = _pres(app)
    f, _ = _fila(admin_client, pid)
    assert not f['sugerido'].get('etiqueta'), 'eligió una de dos empatadas'
    assert f['ambiguo'].get('etiqueta'), 'no dice que empataron · se resolvería solo'
    _limpiar(app)


def test_NO_propone_encima_de_lo_que_YA_esta(app, admin_client):
    """Lo cargado a mano vale más que lo deducido: si la propuesta pisara el dato guardado, un
    guardado en bloque cambiaría cosas que nadie decidió."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA ZANAHORIA 30', 'Etiqueta')
    _mee(app, 'MEE-QQ-OTRA', 'ETIQUETA VIEJA', 'Etiqueta')
    pid = _pres(app, etq='MEE-QQ-OTRA')
    f, _ = _fila(admin_client, pid)
    assert f['actual']['etiqueta'] == 'MEE-QQ-OTRA'
    assert 'etiqueta' not in f['sugerido'], 'propone encima de un dato ya cargado'
    _limpiar(app)


def test_NO_USA_se_guarda_como_MARCA_no_como_vacio(app, admin_client):
    """*"que me deje poner NO USA"* · y "no usa" y "todavía no lo cargaron" son cosas DISTINTAS:
    si se guardara como código vacío, la pantalla no podría distinguirlas y el producto contaría
    como pendiente para siempre (M100/M129)."""
    from database import get_db
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    pid = _pres(app)
    r = admin_client.post('/api/mee/normalizar-guardar',
                          json={'filas': [{'id': pid, 'etiqueta': '__NO_USA__'}]},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['guardadas'] == 1, r.data[:200]
    with app.app_context():
        v = get_db().execute("SELECT sin_etiqueta, COALESCE(etiqueta_codigo,'') "
                             "  FROM producto_presentaciones WHERE id=?", (pid,)).fetchone()
    assert v[0] == 1 and not v[1], 'no lo guardó como marca: %s' % (tuple(v),)
    f, _ = _fila(admin_client, pid)
    assert f['no_usa']['etiqueta'] == 1
    assert not f['sugerido'].get('etiqueta'), 'sigue proponiendo algo que se dijo que no usa'
    _limpiar(app)


def test_el_ENVASE_no_puede_ser_no_usa(app, admin_client):
    """Sin frasco no hay nada que envasar · aceptarlo dejaría un producto que nunca compra envase
    y que además se ve como resuelto."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    pid = _pres(app)
    r = admin_client.post('/api/mee/normalizar-guardar',
                          json={'filas': [{'id': pid, 'envase': '__NO_USA__'}]},
                          headers={'Origin': 'http://localhost'})
    j = r.get_json()
    assert any(e['campo'] == 'envase' for e in (j.get('errores') or [])), \
        'aceptó dejar un producto sin frasco'
    _limpiar(app)


def test_NO_acepta_un_codigo_que_no_existe(app, admin_client):
    """Un empaque fantasma es uno que la compra no resuelve: no se compra nunca y nadie se entera
    (M100 · un hueco visible convertido en invisible)."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    pid = _pres(app)
    r = admin_client.post('/api/mee/normalizar-guardar',
                          json={'filas': [{'id': pid, 'tapa': 'NO-EXISTE-999'}]},
                          headers={'Origin': 'http://localhost'})
    j = r.get_json()
    assert any(e.get('codigo') == 'NO-EXISTE-999' for e in (j.get('errores') or [])), \
        'aceptó un código fantasma'
    _limpiar(app)


def test_lo_que_NO_se_pudo_guardar_se_DICE(app, admin_client):
    """Un "listo" que dejó cosas afuera es peor que un error: nadie vuelve a mirarlas."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-TAP', 'TAPA NEGRA 30', 'Tapa')
    pid = _pres(app)
    r = admin_client.post('/api/mee/normalizar-guardar',
                          json={'filas': [{'id': pid, 'tapa': 'MEE-QQ-TAP', 'caja': 'FANTASMA'}]},
                          headers={'Origin': 'http://localhost'})
    j = r.get_json()
    assert j['guardadas'] == 1, 'no guardó lo que sí era válido'
    assert j['errores'] and j['errores'][0]['motivo'], 'no dice qué rechazó ni por qué'
    _limpiar(app)


def test_cada_columna_ofrece_SU_categoria(app, admin_client):
    """Una tapa no puede aparecer en la columna de la caja: el desplegable existe para que no haya
    que acordarse de qué código es de qué."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-TAP', 'TAPA NEGRA 30', 'Tapa')
    _pres(app)
    _, j = _fila(admin_client, 0)
    tapas = {x['codigo'] for x in j['catalogo']['tapa']}
    cajas = {x['codigo'] for x in j['catalogo']['caja']}
    assert 'MEE-QQ-TAP' in tapas, 'la tapa no aparece en su columna'
    assert 'MEE-QQ-TAP' not in cajas, 'la tapa aparece en la columna de la caja'
    _limpiar(app)


def test_la_PAGINA_existe_y_es_su_propia_ventana(app, admin_client, client):
    """*"así me tengas que abrir en otra ventana"* · y va en archivo propio: un error de sintaxis
    dentro del bundle gigante deja pantallas en blanco, y eso ya pasó dos veces hoy."""
    r = admin_client.get('/planta/normalizar-envases')
    assert r.status_code == 200
    assert b'normalizar-tabla' in r.data, 'la página no consulta la tabla'
    assert b'no usa' in r.data, 'la página no ofrece "no usa"'
    assert os.path.exists(os.path.join(RAIZ, 'api', 'templates_py',
                                       'normalizar_envases_html.py')), \
        'la pantalla no vive en su propio archivo'
    r2 = client.get('/planta/normalizar-envases')      # sin sesión
    assert r2.status_code in (302, 401, 403), 'la página está abierta'


def test_a_las_pantallas_NUEVAS_se_LLEGA_desde_la_app(app, admin_client):
    """Una capacidad a la que no se llega no existe (M121).

    Sebastián tuvo que escribir la URL a mano para abrir la tabla de normalización, y la matriz de
    permisos llevaba horas sin un solo enlace. Construir la pantalla es la mitad del trabajo: la
    otra mitad es que alguien pueda encontrarla sin que se la digan.

    Se enumeran las que importan, con la pantalla desde la que se llega. Si mañana se agrega otra,
    se suma acá y el guard exige su enlace.
    """
    destinos = [
        ('/planta/normalizar-envases', '/inventarios'),
        ('/admin/permisos', '/admin'),
    ]
    sin_enlace = []
    for destino, desde in destinos:
        r = admin_client.get(desde)
        assert r.status_code == 200, 'no pude abrir %s' % desde
        if destino.encode() not in r.data:
            sin_enlace.append('%s no se enlaza desde %s' % (destino, desde))
    assert not sin_enlace, sin_enlace


def test_NO_propone_por_una_palabra_de_FAMILIA(app, admin_client):
    """El caso real que reportó Sebastián el 9-ago: a **CONTORNO DE CAFEÍNA** se le proponía la
    etiqueta *"Contorno de retinaldehído 0.05%"*, o sea la de OTRO producto, porque compartían la
    palabra `CONTORNO`.

    `CONTORNO` no identifica un producto: identifica una FAMILIA (hay contorno de cafeína, de
    ojos, de retinaldehído). Una propuesta sostenida sólo por una palabra de familia es
    exactamente "ponerle a este producto el empaque de otro", y con el botón de aceptar en bloque
    al lado eso se guarda de a decenas (M19/M137).
    """
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 10', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'CONTORNO DE RETINALDEHIDO 0.05% ETIQUETA BLANCA', 'Etiqueta')
    from database import get_db
    with app.app_context():
        c = get_db()
        # otro producto de la MISMA familia: eso es lo que vuelve genérica la palabra
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo) VALUES "
                  "('NORMTAB CONTORNO DE RETINALDEHIDO','V10','10 ml',10,1)")
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, activo) VALUES "
                  "('NORMTAB CONTORNO DE CAFEINA','V10','10 ml',10,'MEE-QQ-FR',1)")
        c.commit()
        pid = c.execute("SELECT id FROM producto_presentaciones "
                        " WHERE producto_nombre='NORMTAB CONTORNO DE CAFEINA'").fetchone()[0]
    f, _ = _fila(admin_client, pid)
    # Lo que NO puede pasar es que le ponga la etiqueta del OTRO contorno. Si encuentra la suya
    # propia, mejor: la regla no es "no propongas", es "no adivines".
    assert f and f['sugerido'].get('etiqueta') != 'MEE-QQ-ETQ', \
        'le puso a la cafeína la etiqueta del retinaldehído: %s' % f['sugerido']
    # Y si quedó vacía, tiene que decir por qué: una celda vacía sin explicación se lee como "el
    # sistema no sabe", y lo que pasa es que sabe y decidió no adivinar. Son dos razones distintas
    # y llevan a acciones distintas ("elegila vos" vs "ojo, ese es de otro producto").
    if not f['sugerido'].get('etiqueta') and not f['ambiguo'].get('etiqueta'):
        _m = (f.get('motivo', {}) or {}).get('etiqueta', '')
        assert 'otro producto' in _m or 'familia' in _m, \
            'quedó vacía y no dice por qué: %s' % f.get('motivo')
    _limpiar(app)


def test_una_etiqueta_que_nombra_a_OTRO_producto_queda_descalificada(app, admin_client):
    """El descalificador que de verdad decide, aislado del resto.

    A CONTORNO DE CAFEÍNA se le proponía *"Contorno de retinaldehído 0.05%"*. Lo que delata a ese
    candidato no es que comparta `CONTORNO`: es que lleva escrito **RETINALDEHIDO**, una palabra
    que identifica a otro producto. Un descalificador duro le gana al parecido (M135).
    """
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 10', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA ZANAHORIA CON RETINALDEHIDO NORMTAB', 'Etiqueta')
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo) VALUES "
                  "('NORMTAB RETINALDEHIDO','V10','10 ml',10,1)")
        c.commit()
    pid = _pres(app)                      # producto: NORMTAB SUERO ZANAHORIA
    f, _ = _fila(admin_client, pid)
    assert f['sugerido'].get('etiqueta') != 'MEE-QQ-ETQ', \
        'propuso una etiqueta que nombra a otro producto: %s · %s' % (f['sugerido'], f.get('motivo'))
    _limpiar(app)


def test_la_TAPA_se_propone_por_TAMANO(app, admin_client):
    """Sebastián (9-ago): *"este usa gotero, la tapa sería gotero, el de menos ml que tenemos;
    tenemos varios para 10, 15, 30 y 50 ml"*.

    La tapa es el caso donde emparejar por nombre NO puede funcionar: un gotero no dice de qué
    producto es, dice de qué TAMAÑO es. Para la tapa, el tamaño es la identidad.
    """
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 10', 'Frasco')
    _mee(app, 'MEE-QQ-GOT10', 'GOTERO 10ML NEGRO', 'Tapa')
    _mee(app, 'MEE-QQ-GOT30', 'GOTERO 30ML NEGRO', 'Tapa')
    pid = _pres(app)                                   # esta presentación es de 30 ml
    f, _ = _fila(admin_client, pid)
    assert f['sugerido'].get('tapa') == 'MEE-QQ-GOT30', \
        'no eligió el gotero de SU tamaño: %s · %s' % (f['sugerido'], f.get('motivo'))
    assert 'tama' in (f.get('motivo', {}) or {}).get('tapa', ''), 'no dice por qué la eligió'
    _limpiar(app)


def test_si_hay_DOS_tapas_del_mismo_tamano_no_elige(app, admin_client):
    """Dos goteros de 30 ml no son una respuesta: los muestra y espera a una persona."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 10', 'Frasco')
    _mee(app, 'MEE-QQ-GOTA', 'GOTERO 30ML NEGRO', 'Tapa')
    _mee(app, 'MEE-QQ-GOTB', 'GOTERO 30ML BLANCO', 'Tapa')
    pid = _pres(app)
    f, _ = _fila(admin_client, pid)
    assert not f['sugerido'].get('tapa'), 'eligió una de dos tapas del mismo tamaño'
    assert f['ambiguo'].get('tapa'), 'no muestra el empate'
    _limpiar(app)


def test_un_envase_de_OTRO_tamano_no_se_propone(app, admin_client):
    """Un "Envase 30ml" no envasa una presentación de 10 ml, por más que el nombre pegue."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-E30', 'ENVASE ZANAHORIA 30ML', 'Frasco')
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo) VALUES (?,'V10','10 ml',10,1)", (PROD,))
        c.commit()
        pid = c.execute("SELECT id FROM producto_presentaciones WHERE producto_nombre=?",
                        (PROD,)).fetchone()[0]
    f, _ = _fila(admin_client, pid)
    assert not f['sugerido'].get('envase'), \
        'propuso un envase de 30 ml para una presentación de 10: %s' % f['sugerido']
    _limpiar(app)


def test_marca_lo_YA_GUARDADO_que_nombra_a_otro_producto(app, admin_client):
    """Arreglar la regla no arregla el dato que ya se guardó con la regla vieja.

    Hasta el 9-ago el emparejador proponía por palabra de familia, así que un "aceptar todas las
    sugeridas" pudo dejar la etiqueta del retinaldehído puesta en la cafeína. Esa fila se ve
    RESUELTA, que es la peor forma de estar mal (M100). Se marca para poder revisarla.
    """
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA CON RETINALDEHIDO', 'Etiqueta')
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo) VALUES ('NORMTAB RETINALDEHIDO','V30','30 ml',30,1)")
        c.commit()
    pid = _pres(app, etq='MEE-QQ-ETQ')          # ya GUARDADA, como si se hubiera aceptado en bloque
    f, _ = _fila(admin_client, pid)
    assert f['actual']['etiqueta'] == 'MEE-QQ-ETQ'
    assert 'etiqueta' in (f.get('sospechoso') or {}), \
        'no marcó una etiqueta guardada que nombra a otro producto: %s' % f.get('sospechoso')
    _limpiar(app)


def test_lo_guardado_CORRECTO_no_se_marca(app, admin_client):
    """Un detector que grita de más deja de mirarse (M122): la etiqueta propia no se marca."""
    _limpiar(app)
    _mee(app, 'MEE-QQ-FR', 'FRASCO VIDRIO 30', 'Frasco')
    _mee(app, 'MEE-QQ-ETQ', 'ETIQUETA ZANAHORIA 30', 'Etiqueta')
    pid = _pres(app, etq='MEE-QQ-ETQ')
    f, _ = _fila(admin_client, pid)
    assert not (f.get('sospechoso') or {}).get('etiqueta'), \
        'marcó como sospechosa la etiqueta correcta: %s' % f.get('sospechoso')
    _limpiar(app)
