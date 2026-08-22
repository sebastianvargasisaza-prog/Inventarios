# -*- coding: utf-8 -*-
"""Lo que se dio por NO ENCONTRADO tiene que quedar en el informe con cómo ir a verificarlo.

Sebastián 22-ago: *"los que marquemos como NO EXISTEN también deben aparecer en el resumen
final, para verificar si es real que no existen"* y *"también lo que se baje a cero"*.

El problema de fondo: **lo que se declara no encontrado deja de estar en el inventario** (el
lote queda en cero y desaparece de la hoja), así que del stock actual no se puede reconstruir
nada. El informe se arma del `audit_log`, y ahí estaba la mitad del trabajo hecho: los listaba
pero **sin el nombre del material y sin dónde estaban**, que es justamente lo único que sirve
para ir a buscarlos. Con el código pelado y la columna de ubicación en blanco, la lista no se
puede repartir a nadie.

Un lote a cero también sale del inventario aunque queden gramos de polvo (<= 0,01 g), así que
ésos cuentan igual como *no está*: si no, se irían a la lista de ajustados y nadie los buscaría.
"""
import pytest

CODIGO = 'MPINFORMENC'
LOTE = 'LOTE-INF-1'
LOTE_POLVO = 'LOTE-INF-POLVO'
EST = 'EST-INFORME-NC'
NOMBRE = 'ACIDO DE PRUEBA INFORME'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


@pytest.fixture()
def sembrado(app):
    """Un material cuyo ÚNICO stock son estos dos lotes.

    Es el caso que rompe: al declararlos no encontrados el material se queda sin una sola
    fila con saldo, así que el informe ya no puede sacar su nombre del inventario.
    """
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, NOMBRE, 'TEST INCI'))
        for lote, cant in ((LOTE, 1000.0), (LOTE_POLVO, 500.0)):
            c.execute(
                "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                " fecha, operador, estanteria, posicion, fecha_vencimiento, estado_lote) "
                "VALUES (?,?,'Entrada',?,?,?,?,?,?,?,'VIGENTE')",
                (CODIGO, NOMBRE, cant, lote, '2026-08-01 08:00:00', 'test',
                 EST, 'D4', '2027-06-30'))
        c.commit()
    yield
    _limpiar(app)


def _informe(client):
    r = client.get('/api/inventario/cuadre-informe')
    assert r.status_code == 200, r.data[:200]
    return r.get_json() or {}


def _en(lista, lote):
    for x in lista or []:
        if x.get('codigo_mp', '').upper() == CODIGO and x.get('lote') == lote:
            return x
    return None


def test_lo_declarado_NO_EXISTE_queda_en_el_informe(admin_client, sembrado):
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 0, 'motivo': 'no aparece en el estante',
        'estanteria': EST, 'token': 'inf-nc-1'})
    d = _informe(admin_client)
    f = _en(d.get('no_esta'), LOTE)
    assert f is not None, 'lo declarado no encontrado no aparece en el informe'
    assert _en(d.get('a_buscar'), LOTE) is not None, 'no entró a la lista para ir a buscar'
    assert f.get('sistema') == 1000.0, (
        'el informe no dice cuánto creía tener el sistema: %r' % f.get('sistema'))


def test_dice_QUE_material_es_aunque_ya_no_tenga_stock(admin_client, sembrado):
    """Con el código pelado nadie puede ir a buscarlo: hay que pedirlo por su nombre."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 0, 'motivo': 'no aparece',
        'estanteria': EST, 'token': 'inf-nc-2'})
    f = _en(_informe(admin_client).get('a_buscar'), LOTE)
    assert f is not None
    assert (f.get('nombre') or '').upper() == NOMBRE, (
        'el informe lo nombra %r en vez del material' % f.get('nombre'))


def test_dice_DONDE_deberia_estar_para_poder_verificarlo(admin_client, sembrado):
    """La razón por la que se pide la lista: ir a verificar si de verdad no está."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 0, 'motivo': 'no aparece',
        'estanteria': EST, 'token': 'inf-nc-3'})
    f = _en(_informe(admin_client).get('a_buscar'), LOTE)
    assert f is not None
    assert f.get('estanteria') == EST, (
        'el informe no dice dónde estaba: %r' % f.get('estanteria'))
    assert f.get('posicion') == 'D4', 'perdió la posición: %r' % f.get('posicion')


def test_dice_QUIEN_lo_declaro_y_CUANDO(admin_client, sembrado):
    """Para verificar si es real hay que poder volver a preguntarle a quien lo declaró."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 0, 'motivo': 'no aparece',
        'estanteria': EST, 'token': 'inf-nc-4'})
    f = _en(_informe(admin_client).get('no_esta'), LOTE)
    assert f is not None
    assert f.get('por'), 'no dice quién lo declaró'
    assert f.get('cuando'), 'no dice cuándo'
    assert f.get('motivo') == 'no aparece', 'perdió el motivo que escribió quien contó'


def test_un_lote_BAJADO_A_CERO_cuenta_como_no_encontrado(admin_client, sembrado):
    """Bajarlo a cero es lo mismo que declararlo no encontrado: sale del inventario.

    Aunque queden gramos de polvo (<= 0,01) el lote ya no está en la hoja, así que tiene que
    salir en la lista para buscar y no perderse entre los ajustes.
    """
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE_POLVO, 'fisico': 0.004,
        'motivo': 'quedó vacío el tarro', 'estanteria': EST, 'token': 'inf-nc-5'})
    d = _informe(admin_client)
    assert _en(d.get('a_buscar'), LOTE_POLVO) is not None, (
        'un lote bajado a cero no entró en la lista para buscar')
    assert _en(d.get('ajustados'), LOTE_POLVO) is None, (
        'quedó contado como ajuste: nadie lo va a buscar')


def test_el_que_SI_estaba_no_se_va_a_la_lista_de_buscar(admin_client, sembrado):
    """El guard tiene que distinguir: un ajuste normal NO manda a nadie a buscar nada."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 900.0, 'motivo': 'faltaban 100',
        'estanteria': EST, 'token': 'inf-nc-6'})
    d = _informe(admin_client)
    assert _en(d.get('ajustados'), LOTE) is not None, 'el ajuste no quedó registrado'
    assert _en(d.get('no_esta'), LOTE) is None, 'un ajuste normal se contó como no encontrado'


def test_la_pantalla_del_informe_muestra_donde_estaba_y_quien_lo_dijo(app):
    """La capacidad sin puerta no existe: los datos tienen que estar PINTADOS (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    i = H.find("Para ir a buscar")
    assert i != -1, 'la pantalla no tiene la sección para ir a buscar'
    bloque = H[i:i + 2200]
    assert 'estanteria' in bloque, 'la lista para buscar no pinta dónde estaba'
    assert 'f.por' in bloque or 'por' in bloque, 'no pinta quién lo declaró'


# -----------------------------------------------------------------------------
# Lo contado ES la verdad del estante: tiene que seguir ahi
# -----------------------------------------------------------------------------

def test_lo_declarado_que_SIGUE_igual_no_se_reporta(admin_client, sembrado):
    """El guard tiene que distinguir, o reportaria todo y dejaria de mirarse."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 900.0, 'motivo': 'conteo',
        'estanteria': EST, 'token': 'inf-nc-7'})
    d = _informe(admin_client)
    assert _en(d.get('no_cuadran'), LOTE) is None, (
        'un lote que quedo como se declaro se reporto como descuadrado')


def test_si_lo_declarado_YA_NO_ESTA_el_informe_lo_canta(admin_client, sembrado):
    """La red de seguridad que pidio Sebastian: *"no se puede perder nada de lo que estamos
    haciendo"*. Si un lote contado hoy ya no esta en la cantidad declarada, eso se mira antes
    que nada -- se consumio despues, o la declaracion no aterrizo."""
    from database import get_db
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 900.0, 'motivo': 'conteo',
        'estanteria': EST, 'token': 'inf-nc-8'})
    # Alguien se llevo 300 g despues de contarlo (una produccion, por ejemplo).
    with admin_client.application.app_context():
        c = get_db()
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote) "
            "VALUES (?,?,'Salida',?,?,?,?,?,'VIGENTE')",
            (CODIGO, NOMBRE, 300.0, LOTE, '2026-08-22 18:00:00', 'produccion', EST))
        c.commit()
    f = _en(_informe(admin_client).get('no_cuadran'), LOTE)
    assert f is not None, 'lo contado ya no esta y el informe no lo dice'
    assert f.get('fisico') == 900.0, 'no dice cuanto se conto'
    assert f.get('stock_ahora') == 600.0, 'no dice cuanto hay ahora: %r' % f.get('stock_ahora')
    assert f.get('diferencia') == -300.0, 'no dice la diferencia: %r' % f.get('diferencia')
    assert f.get('posible'), 'no declara que hay dos explicaciones posibles'


def test_la_pantalla_PINTA_lo_que_no_cuadra(app):
    """Una capacidad sin puerta no existe (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    assert 'no_cuadran' in H, 'el informe no pinta la seccion'
    i = H.find('no coincide con el inventario de ahora')
    assert i != -1, 'la seccion no tiene titulo que se entienda'
    bloque = H[i:i + 1600]
    assert 'stock_ahora' in bloque, 'no muestra cuanto hay ahora'
    assert 'diferencia' in bloque, 'no muestra la diferencia'


# -----------------------------------------------------------------------------
# Lo que se CORRIGIO contando tambien es trabajo del inventario
# -----------------------------------------------------------------------------

def test_corregir_una_ubicacion_sale_en_el_cierre(admin_client, sembrado):
    """Se corrige mientras se cuenta, asi que tiene que quedar en el cierre."""
    admin_client.put('/api/lotes/%s/%s/ubicacion' % (CODIGO, LOTE),
                     json={'estanteria': 'EST-NUEVA', 'motivo': 'estaba en otro lado'})
    d = _informe(admin_client)
    f = _en(d.get('correcciones'), LOTE)
    assert f is not None, 'la correccion de ubicacion no aparece en el cierre'
    assert f.get('que') == 'ubicacion' or 'ubicaci' in (f.get('que') or '')
    assert 'EST-NUEVA' in (f.get('despues') or ''), 'no dice como quedo'
    assert f.get('por'), 'no dice quien la hizo'
    assert f.get('motivo') == 'estaba en otro lado', 'perdio el motivo'


def test_corregir_un_vencimiento_sale_en_el_cierre(admin_client, sembrado):
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                     json={'fecha_vencimiento': '2029-01-31', 'motivo': 'mal tecleada'})
    d = _informe(admin_client)
    f = _en(d.get('correcciones'), LOTE)
    assert f is not None, 'la correccion de vencimiento no aparece en el cierre'
    assert '2029-01-31' in (f.get('despues') or ''), 'no dice la fecha nueva'
    assert '2027-06-30' in (f.get('antes') or ''), 'no dice que fecha tenia antes'


def test_el_cierre_NO_inventa_correcciones(admin_client, sembrado):
    """El guard tiene que distinguir, o reportaria siempre y dejaria de mirarse (M129).

    Se mira un lote que NINGUN test corrige: el audit_log es append-only por trigger, asi que
    el rastro de los casos anteriores del archivo sigue ahi y el aislamiento se consigue con un
    DATO propio, no limpiando (M102/M103).
    """
    d = _informe(admin_client)
    assert _en(d.get('correcciones'), LOTE_POLVO) is None, (
        'reporta una correccion que nadie hizo sobre ese lote')


def test_el_cierre_PINTA_las_correcciones(app):
    """Una capacidad sin puerta no existe (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    i = H.find('Se corrigieron')
    assert i != -1, 'el cierre no tiene la seccion de correcciones'
    bloque = H[i:i + 1400]
    assert 'f.antes' in bloque or 'antes' in bloque, 'no muestra que decia'
    assert 'despues' in bloque, 'no muestra como quedo'
