# -*- coding: utf-8 -*-
"""La tabla de normalización dice cuáles presentaciones FRENAN una producción real.

Sebastián: *"todo lo de MEE para poder ir cerrando el batch record sigue frenado"*. El resumen
contaba todas las filas por igual, así que una lista de decenas de pendientes -- casi todos de
productos que nadie va a fabricar esta semana -- se mezclaba con las pocas que de verdad traban
el cierre. Una lista que no cierra deja de mirarse (M129), y una que no distingue lo urgente
obliga a revisarla entera cada vez.
"""
import pytest

TEST_PASSWORD = "TestPass123"


@pytest.fixture
def planta_client(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "smurillo", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'FRENA %'")
        c.execute("DELETE FROM produccion_programada WHERE producto LIKE 'FRENA %'")
        conn.commit()


def _presentacion(app, producto, completa):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        # Los codigos tienen que EXISTIR en el maestro: una presentacion que apunta a un codigo
        # inexistente esta incompleta de verdad -- es el caso MEE-IMP-001 que tenia frenado el
        # empaque -- asi que sembrar codigos fantasma media otra cosa (M153: si el fixture necesita
        # un estado que produccion marcaria como roto, el fixture es el que esta mal).
        for _cod, _desc, _cat in (('MEE-ENV-001', 'FRASCO DE PRUEBA 30ml', 'Frasco'),
                                  ('MEE-TAP-001', 'TAPA DE PRUEBA', 'Tapa'),
                                  ('MEE-PLG-001', 'PLEGADIZA DE PRUEBA', 'Plegadiza'),
                                  ('MEE-ETQ-001', 'ETIQUETA DE PRUEBA', 'Etiqueta')):
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (_cod,))
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                      "VALUES (?,?,?,0)", (_cod, _desc, _cat))
        c.execute(
            "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
            "volumen_ml, envase_codigo, tapa_codigo, caja_codigo, etiqueta_codigo, "
            "sin_tapa, sin_caja, sin_etiqueta, activo, es_default) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,1,1)",
            (producto, 'V30', '30 ml', 30.0,
             'MEE-ENV-001',
             'MEE-TAP-001' if completa else '',
             'MEE-PLG-001' if completa else '',
             'MEE-ETQ-001' if completa else '',
             0, 0, 0))
        conn.commit()


def _programar(app, producto):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO produccion_programada (producto, fecha_programada, estado, origen, "
            "cantidad_kg) VALUES (?, '2026-09-01', 'pendiente', 'eos_plan', 10)", (producto,))
        conn.commit()


def test_una_incompleta_CON_produccion_frena(app, planta_client):
    """DIENTES · el caso que traba el cierre del batch record tiene que salir marcado."""
    _limpiar(app)
    _presentacion(app, 'FRENA CON PROD', completa=False)
    _programar(app, 'FRENA CON PROD')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in d['filas'] if f['producto'] == 'FRENA CON PROD']
    assert fila, 'la presentación sembrada no salió en la tabla'
    assert fila[0]['incompleta'] is True
    assert fila[0]['bloquea'] is True
    assert d['resumen']['bloquean'] >= 1
    assert d['resumen']['bloquean_medido'] is True


def test_una_incompleta_SIN_produccion_no_frena(app, planta_client):
    """Y el otro borde: sin este test, marcar TODO como bloqueante pasaría igual, y el contador
    no serviría para separar lo urgente de lo que puede esperar."""
    _limpiar(app)
    _presentacion(app, 'FRENA SIN PROD', completa=False)
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in d['filas'] if f['producto'] == 'FRENA SIN PROD']
    assert fila
    assert fila[0]['incompleta'] is True
    assert fila[0]['bloquea'] is False, 'una presentación sin producción programada no frena nada'


def test_una_completa_no_frena_aunque_tenga_produccion(app, planta_client):
    _limpiar(app)
    _presentacion(app, 'FRENA COMPLETA', completa=True)
    _programar(app, 'FRENA COMPLETA')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in d['filas'] if f['producto'] == 'FRENA COMPLETA']
    assert fila
    assert fila[0]['incompleta'] is False
    assert fila[0]['bloquea'] is False


def test_no_usa_cuenta_como_resuelto(app, planta_client):
    """'No usa' y 'todavía no lo cargaron' son cosas distintas: marcar que un producto no lleva
    caja tiene que cerrar la fila, o la lista no llega a cero nunca."""
    _limpiar(app)
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM maestro_mee WHERE codigo='MEE-ENV-001'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('MEE-ENV-001','FRASCO DE PRUEBA 30ml','Frasco',0)")
        c.execute(
            "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
            "volumen_ml, envase_codigo, tapa_codigo, caja_codigo, etiqueta_codigo, "
            "sin_tapa, sin_caja, sin_etiqueta, activo, es_default) "
            "VALUES ('FRENA NOUSA','V30','30 ml',30.0,'MEE-ENV-001','','','',1,1,1,1,1)")
        conn.commit()
    _programar(app, 'FRENA NOUSA')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in d['filas'] if f['producto'] == 'FRENA NOUSA']
    assert fila
    assert fila[0]['incompleta'] is False
    assert fila[0]['bloquea'] is False


def test_la_pantalla_muestra_el_contador_y_el_filtro(planta_client):
    h = planta_client.get('/planta/normalizar-envases').get_data(as_text=True)
    assert 'frenan producci' in h
    assert 'btn-bloquean' in h
    assert 'SOLO_BLOQUEAN' in h


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Una categoría fuera de la lista deja una FAMILIA ENTERA invisible
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _mee(app, codigo, desc, categoria):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM maestro_mee WHERE codigo=?", (codigo,))
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES (?,?,?,0)", (codigo, desc, categoria))
        conn.commit()


def test_los_frascos_IMPRESOS_salen_en_la_columna_envase(app, planta_client):
    """DIENTES · la categoría del maestro es 'Impreso' y la lista decía 'IMPRESION'.

    Ni 'empieza por' ni 'contiene' unen esas dos palabras, así que los ocho frascos serigrafiados
    -- los que de verdad van a la línea -- eran invisibles: la fila del lip serum mostraba
    "MEE-IMP-001 (no está en el maestro)" teniendo 301 unidades en bodega. No da error: da una
    celda vacía que el usuario no puede llenar (M121/M179).
    """
    _mee(app, 'IMPTEST-001', 'LIPS GLOSS GRIS CON SERIGRAFIA', 'Impreso')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    codigos = {x['codigo'] for x in d['catalogo'].get('envase', [])}
    assert 'IMPTEST-001' in codigos, (
        'un envase con categoría "Impreso" no aparece para elegir · la familia entera queda '
        'invisible')


def test_una_categoria_que_nadie_reclama_se_DECLARA(app, planta_client):
    """El guard que evita la tercera vez: en lugar de confiar en que la lista esté completa, la
    pantalla dice qué categorías del maestro quedaron sin columna."""
    _mee(app, 'RARO-001', 'COMPONENTE DE UNA FAMILIA NUEVA', 'CategoriaQueNadieReclama')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    sin = {x['categoria'] for x in d.get('categorias_sin_clasificar', [])}
    assert 'CategoriaQueNadieReclama' in sin, (
        'una categoría fuera de las listas no se declaró: la próxima familia invisible pasaría '
        'igual de desapercibida')


def test_una_categoria_conocida_NO_se_reporta(app, planta_client):
    """Y el caso sano: sin esto, el guard podría reportar todo y volverse ruido."""
    _mee(app, 'FRTEST-001', 'FRASCO DE PRUEBA 30ml', 'Frasco')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    sin = {x['categoria'] for x in d.get('categorias_sin_clasificar', [])}
    assert 'Frasco' not in sin
    assert 'Impreso' not in sin, 'Impreso ya está reclamado por la columna envase'


def test_una_fila_DADA_DE_BAJA_no_frena(app, planta_client):
    """DIENTES · contando las inactivas el numero salia MAYOR que el total de filas.

    En produccion mostro "44 frenan produccion" sobre 42 presentaciones. Un contador imposible
    destruye la confianza en los otros tres que estan al lado y que si eran correctos (M161), y de
    fondo una presentacion dada de baja no frena nada porque no se usa.
    """
    _limpiar(app)
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
            "volumen_ml, envase_codigo, tapa_codigo, caja_codigo, etiqueta_codigo, "
            "sin_tapa, sin_caja, sin_etiqueta, activo, es_default) "
            "VALUES ('FRENA DE BAJA','V30','30 ml',30,'MEE-ENV-001','','','',0,0,0,0,0)")
        conn.commit()
    _programar(app, 'FRENA DE BAJA')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    fila = [f for f in d['filas'] if f['producto'] == 'FRENA DE BAJA']
    assert fila, 'la fila sembrada no salio'
    assert fila[0]['incompleta'] is True
    assert fila[0]['bloquea'] is False, 'una fila dada de baja no puede frenar produccion'


def test_el_contador_nunca_supera_el_total_de_filas(app, planta_client):
    """La invariante que hace imposible el numero absurdo, sin depender de un caso puntual."""
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    r = d['resumen']
    assert r['bloquean'] <= r['filas'], (
        'frenan (%s) > filas (%s): el contador esta midiendo mas de lo que existe'
        % (r['bloquean'], r['filas']))
    activas = sum(1 for f in d['filas'] if f.get('activo'))
    assert r['bloquean'] <= activas, (
        'frenan (%s) > filas activas (%s)' % (r['bloquean'], activas))


def test_una_SUGERENCIA_no_cuenta_como_completa(app, planta_client):
    """DIENTES · una sugerencia no esta en la base: la presentacion tiene la celda VACIA.

    La pantalla la contaba como valor, asi que el KPI decia "38/42 completas" con 13 sugerencias
    sin aceptar -- exageraba -- y encima chocaba con el contador de las que frenan, que mide lo
    guardado: "5 frenan" al lado de una lista de 4. Dos numeros del mismo tablero que se
    contradicen hacen que se deje de creer en los dos (M5/M161).
    """
    _limpiar(app)
    _presentacion(app, 'FRENA SUGERIDA', completa=False)
    _programar(app, 'FRENA SUGERIDA')
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    f = [x for x in d['filas'] if x['producto'] == 'FRENA SUGERIDA'][0]
    # aunque el emparejador le proponga algo, mientras no este guardado la fila esta incompleta
    assert f['incompleta'] is True
    assert f['bloquea'] is True


def test_los_dos_contadores_NO_se_contradicen(app, planta_client):
    """La invariante que hace imposible volver a mostrar "5 frenan" sobre una lista de 4."""
    d = planta_client.get('/api/mee/normalizar-tabla').get_json()
    incompletas_activas = sum(1 for f in d['filas'] if f.get('activo') and f.get('incompleta'))
    assert d['resumen']['bloquean'] <= incompletas_activas, (
        'frenan (%s) > incompletas activas (%s): los dos contadores miden cosas distintas'
        % (d['resumen']['bloquean'], incompletas_activas))
