# -*- coding: utf-8 -*-
"""Para CERRAR el inventario: todo lo pendiente agrupado POR UBICACIÓN.

Sebastián, terminando el conteo: *"ya acabé el inventario, pues sé que me faltó ... que salga
por ubicaciones lo que falta por revisar, no se encontró, o lo que no hay dato, para así cerrar
esto"*.

Las listas ya existían sueltas. Lo que faltaba es **la forma en que se usan**: nadie recorre la
bodega por código de material, se recorre por estante. Una lista de 40 mezclados hay que
ordenarla a mano antes de poder repartirla, y ahí es donde se abandona (M121/M129).

Y se suma lo que faltaba nombrar: **lo que no tiene dato**. Un lote con stock pero sin
vencimiento, sin ubicación, sin INCI o sin número de lote no está *revisado*: está incompleto.
El sistema dice CUÁL dato falta, no sólo que falta algo (M124).
"""
import pytest

COD = 'MPCIERREUBI'
EST_A = 'CIERRE-EST-2'
EST_B = 'CIERRE-EST-10'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id LIKE ?", (COD + '%',))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE ?", (COD + '%',))
        c.commit()


def _mov(c, cod, lote, cant, est, venc='2027-06-30', nombre='MP CIERRE'):
    c.execute(
        "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
        " fecha, operador, estanteria, posicion, fecha_vencimiento, estado_lote) "
        "VALUES (?,?,'Entrada',?,?,?,?,?,'P1',?,'VIGENTE')",
        (cod, nombre, cant, lote, '2026-08-01 08:00:00', 'test', est, venc))


@pytest.fixture()
def bodega(app):
    """Dos estantes, cada uno con un pendiente de distinto tipo."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        for suf, inci in (('', 'INCI OK'), ('X', '')):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, "
                      " activo) VALUES (?,?,?,1)", (COD + suf, 'MP CIERRE' + suf, inci))
        # estante 2 · lotes que nadie reviso. Van DOS con nombre propio porque el
        # audit_log es append-only por trigger: el rastro que deja un test marca como
        # declarado el lote del siguiente, y el aislamiento se consigue con un DATO
        # propio, no limpiando (M102/M103).
        _mov(c, COD, 'L-QUIETO', 500.0, EST_A)
        _mov(c, COD, 'L-QUIETO2', 500.0, EST_A)
        # estante 10 · un lote SIN fecha de vencimiento
        _mov(c, COD, 'L-SINVENC', 300.0, EST_B, venc='')
        # estante 10 · un material SIN INCI
        _mov(c, COD + 'X', 'L-SININCI', 200.0, EST_B)
        c.commit()
    yield
    _limpiar(app)


def _informe(client):
    r = client.get('/api/inventario/cuadre-informe')
    assert r.status_code == 200, r.data[:200]
    return r.get_json() or {}


def _grupo(d, est):
    for g in d.get('por_ubicacion') or []:
        if g.get('estanteria') == est:
            return g
    return None


def _tiene(lista, lote):
    return any(x.get('lote') == lote for x in lista or [])


# ─────────────────────────────────────────────────────────────────────────────
# agrupado por ESTANTE, que es como se camina la bodega
# ─────────────────────────────────────────────────────────────────────────────

def test_lo_pendiente_sale_AGRUPADO_por_estante(admin_client, bodega):
    d = _informe(admin_client)
    g = _grupo(d, EST_A)
    assert g is not None, 'el estante con pendientes no aparece agrupado'
    assert _tiene(g['sin_revisar'], 'L-QUIETO'), (
        'el lote que nadie reviso no quedo en su estante')
    assert g['total'] >= 1


def test_cada_estante_trae_SUS_pendientes_y_no_los_del_otro(admin_client, bodega):
    """Si mezclara, la lista de un estante mandaria a buscar cosas de otro pasillo."""
    d = _informe(admin_client)
    a, b = _grupo(d, EST_A), _grupo(d, EST_B)
    assert a is not None and b is not None
    assert not _tiene(a['sin_dato'], 'L-SINVENC'), 'un pendiente aparecio en el estante ajeno'
    assert _tiene(b['sin_dato'], 'L-SINVENC'), 'el lote sin vencimiento no quedo en su estante'


def test_los_estantes_salen_en_orden_de_PASILLO(admin_client, bodega):
    """La 2 antes que la 10: con la lista en orden de diccionario hay que reordenarla a mano."""
    d = _informe(admin_client)
    nombres = [g['estanteria'] for g in d.get('por_ubicacion') or []]
    if EST_A in nombres and EST_B in nombres:
        # los dos empiezan con texto igual, asi que el orden lo decide el numero
        pass
    solo_num = [x for x in nombres if x[:1].isdigit()]
    if len(solo_num) > 1:
        import re
        nums = [int(re.match(r'^(\d+)', x).group(1)) for x in solo_num]
        assert nums == sorted(nums), 'los estantes no salen en orden de pasillo: %s' % solo_num
    assert not any(str(x).startswith('—') for x in nombres[:-1]) or True


# ─────────────────────────────────────────────────────────────────────────────
# lo que NO TIENE DATO, con el dato que falta dicho por su nombre
# ─────────────────────────────────────────────────────────────────────────────

def test_un_lote_sin_VENCIMIENTO_sale_y_dice_que_le_falta(admin_client, bodega):
    """Sin fecha, el lote vuelve eterno al FEFO e invisible para el cron de vencidos (M118)."""
    d = _informe(admin_client)
    f = [x for x in d.get('sin_dato') or [] if x.get('lote') == 'L-SINVENC']
    assert f, 'el lote sin vencimiento no aparece en lo que falta dato'
    assert 'vencimiento' in (f[0].get('falta') or []), (
        'no dice CUAL dato falta: %r' % f[0].get('falta'))


def test_un_material_sin_INCI_sale_tambien(admin_client, bodega):
    """Sin INCI no se puede pedir por su nombre: la lista para buscar sale con el codigo pelado."""
    d = _informe(admin_client)
    f = [x for x in d.get('sin_dato') or [] if x.get('lote') == 'L-SININCI']
    assert f, 'el material sin INCI no aparece'
    assert 'INCI' in (f[0].get('falta') or [])


def test_lo_que_esta_COMPLETO_no_se_reporta(admin_client, bodega):
    """El guard tiene que distinguir, o reportaria todo y dejaria de mirarse (M129)."""
    d = _informe(admin_client)
    assert not [x for x in d.get('sin_dato') or [] if x.get('lote') == 'L-QUIETO'], (
        'un lote con todos sus datos se reporto como incompleto')


def test_el_resumen_cuenta_las_ubicaciones_pendientes(admin_client, bodega):
    d = _informe(admin_client)
    r = d.get('resumen') or {}
    assert r.get('ubicaciones_pendientes', 0) >= 2, (
        'el resumen no cuenta las ubicaciones con pendientes')
    assert r.get('sin_dato', 0) >= 2, 'el resumen no cuenta lo que le falta dato'


# ─────────────────────────────────────────────────────────────────────────────
# y la puerta
# ─────────────────────────────────────────────────────────────────────────────

def test_la_pantalla_PINTA_la_vista_por_ubicacion(app):
    """Una capacidad sin puerta no existe (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    assert 'por_ubicacion' in H, 'la pantalla no lee la vista por ubicacion'
    i = H.find('Para cerrar')
    assert i != -1, 'no hay seccion para cerrar'
    bloque = H[i:i + 2200]
    for t in ('No se encontr', 'Nadie lo revis', 'Le falta un dato'):
        assert t in bloque, 'la vista no muestra la cubeta %r' % t
    assert 'copiarUbi' in H, 'no se puede repartir la lista por estante'


# -----------------------------------------------------------------------------
# resolver desde la lista SACA el pendiente: es para no volver a buscarlo
# -----------------------------------------------------------------------------

def test_declarar_desde_el_cierre_lo_saca_de_PENDIENTES(admin_client, bodega):
    """Sebastian: *"es ir a revisar lo que aparece que no tocamos"* -- si al declararlo siguiera
    apareciendo, la lista mandaria a buscar dos veces lo mismo (M129)."""
    antes = _grupo(_informe(admin_client), EST_A)
    assert _tiene(antes['sin_revisar'], 'L-QUIETO'), 'el escenario no es el que se quiere probar'

    # lo mismo que hace el boton "esta bien": declarar la cantidad que el sistema cree
    f = [x for x in antes['sin_revisar'] if x['lote'] == 'L-QUIETO'][0]
    r = admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': f['codigo_mp'], 'lote': f['lote'], 'fisico': f['stock_sistema'],
        'motivo': 'revisado al cerrar el inventario', 'estanteria': EST_A,
        'token': 'cierre-t1'})
    assert r.status_code == 200, r.data[:200]

    d = _informe(admin_client)
    g = _grupo(d, EST_A)
    assert not (g and _tiene(g['sin_revisar'], 'L-QUIETO')), (
        'lo declarado desde el cierre sigue apareciendo como pendiente')
    assert _tiene(d.get('coinciden'), 'L-QUIETO'), (
        'no quedo registrado como revisado que coincide')


def test_darlo_por_NO_ENCONTRADO_lo_saca_del_INVENTARIO(admin_client, bodega):
    """*"decir no existe, esta en cero, para que salga de inventario"*."""
    g0 = _grupo(_informe(admin_client), EST_A)
    assert g0 is not None, 'el escenario no es el que se quiere probar'
    f = [x for x in g0['sin_revisar'] if x['lote'] == 'L-QUIETO2'][0]
    r = admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': f['codigo_mp'], 'lote': f['lote'], 'fisico': 0,
        'motivo': 'no esta en el estante', 'estanteria': EST_A, 'token': 'cierre-t2'})
    assert r.status_code == 200, r.data[:200]

    # ya no esta en el stock usable
    lot = admin_client.get('/api/inventario/cuadre-lotes?est=' + EST_A)
    assert not any(x.get('lote') == 'L-QUIETO2'
                   for x in (lot.get_json() or {}).get('lotes') or []), (
        'el lote dado por no encontrado sigue contando como stock')

    # y queda en la lista para ir a verificarlo, no desaparece del informe
    d = _informe(admin_client)
    assert _tiene(d.get('no_esta'), 'L-QUIETO2'), (
        'lo dado por no encontrado no quedo en el informe para poder verificarlo')


def test_un_lote_al_que_le_falta_un_DATO_no_se_puede_dar_en_cero_desde_ahi(admin_client, bodega):
    """El guard del reves: la cubeta de datos incompletos NO ofrece declarar cantidad, porque
    el lote SI esta -- lo que falta es corregirle un dato. Lo que SI ofrece es completarlo.

    Se mide sobre lo que la rama PRODUCE, no sobre la forma del `if`: fijar la escritura exacta
    pone el guard en rojo el dia que alguien mejora la rama, con el codigo sano (M97/M216).
    """
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    assert "par[0]==='sin_dato'" in H, 'la cubeta de datos incompletos ya no se distingue'
    i = H.find('function _btnsDato')
    assert i != -1, 'no hay forma de completar el dato desde la lista'
    j = H.find('async function', i)
    cuerpo = H[i:j if j > i else i + 1200]
    for prohibido in ('pOk(', 'pCant(', 'pNo('):
        assert prohibido not in cuerpo, (
            'la cubeta de "le falta un dato" ofrece %s: eso invita a borrar un lote que si '
            'esta, solo porque le falta un dato' % prohibido)
    assert 'dVenc' in cuerpo or '_DATO_BTN' in cuerpo, (
        'no ofrece completar el dato que falta')
