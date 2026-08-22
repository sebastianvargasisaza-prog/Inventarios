# -*- coding: utf-8 -*-
"""El peso que la hoja MUESTRA tiene que ser el mismo que DECIDE el ajuste.

Sebastián 22-ago: *"súper verificá que las posiciones, pesos, o sea todo, es perfecto"*.

El caso que lo rompe existe en la operación real: una recepción que Calidad parte en
**aprobado y rechazado** deja el MISMO número de lote con filas en dos estados. Ahí:

  · la hoja SUMA sólo lo usable (excluye los 6 estados que no son stock),
  · y el cálculo del ajuste sumaba TODAS las filas, sin mirar el estado.

Entonces quien cuenta ve 800 g, cuenta 800 g, declara 800 g... y el sistema cree que tenía
1.000, así que escribe una **Salida de 200 g que nadie contó** y la hoja pasa a decir 600.
Declarar *"está bien"* terminaba sacando material. Es M5 en el peor lugar posible: el número
mostrado y el que decide no eran el mismo.
"""
import pytest

CODIGO = 'MPCUADRPESO'
LOTE = 'LOTE-MIXTO-1'
EST = 'EST-PESOS-MIXTOS'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


def _mov(c, cant, estado, tipo='Entrada', lote=LOTE):
    c.execute(
        "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
        " fecha, operador, estanteria, posicion, estado_lote) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (CODIGO, 'MP PESOS MIXTOS', tipo, cant, lote, '2026-08-01 08:00:00', 'test',
         EST, 'C3', estado))


@pytest.fixture()
def lote_partido(app):
    """Una recepción partida por Calidad: 800 g aprobados y 200 g rechazados, MISMO lote."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, 'MP PESOS MIXTOS', 'TEST INCI'))
        _mov(c, 800.0, 'VIGENTE')
        _mov(c, 200.0, 'RECHAZADO')
        c.commit()
    yield
    _limpiar(app)


def _fila(client):
    r = client.get('/api/inventario/cuadre-lotes?est=' + EST)
    assert r.status_code == 200, r.data[:200]
    for l in (r.get_json() or {}).get('lotes') or []:
        if l.get('codigo_mp') == CODIGO and l.get('lote') == LOTE:
            return l
    return None


def test_la_hoja_muestra_SOLO_lo_usable(admin_client, lote_partido):
    """Lo rechazado no es stock: si la hoja lo sumara, mandaría a contar material retenido."""
    f = _fila(admin_client)
    assert f is not None, 'el lote no aparece en la hoja'
    assert f['stock_sistema'] == 800.0, (
        'la hoja dice %s: debería mostrar sólo los 800 g usables' % f['stock_sistema'])


def test_declarar_lo_MISMO_que_muestra_la_hoja_no_mueve_nada(admin_client, lote_partido):
    """El corazón del asunto: contar y encontrar lo que dice la pantalla es un no-evento.

    Con el bug, declarar 800 escribía una Salida de 200 g que nadie contó.
    """
    f = _fila(admin_client)
    r = admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': f['stock_sistema'],
        'estanteria': EST, 'token': 'cuadre-pesos-1'})
    assert r.status_code == 200, r.data[:200]
    d = r.get_json() or {}
    assert d.get('sin_cambio') is True, (
        'declarar lo mismo que muestra la hoja generó un ajuste de %s' % d.get('ajuste'))

    despues = _fila(admin_client)
    assert despues['stock_sistema'] == 800.0, (
        'confirmar que coincide cambió el stock: %s' % despues['stock_sistema'])


def test_lo_RECHAZADO_sigue_intacto_despues_del_cuadre(admin_client, lote_partido):
    """El cuadre corrige lo usable; lo que Calidad retuvo no se toca por la puerta de atrás."""
    from database import get_db
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 750.0, 'motivo': 'faltaban 50',
        'estanteria': EST, 'token': 'cuadre-pesos-2'})
    with admin_client.application.app_context():
        r = get_db().execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos "
            "  WHERE material_id=? AND lote=? AND UPPER(COALESCE(estado_lote,''))='RECHAZADO'",
            (CODIGO, LOTE)).fetchone()
    assert float(r[0]) == 200.0, 'el cuadre tocó lo rechazado: %s' % r[0]


def test_un_faltante_real_se_descuenta_EXACTO(admin_client, lote_partido):
    """Y el ajuste tiene que ser exactamente lo que falta contra lo que se mostraba."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 750.0, 'motivo': 'faltaban 50',
        'estanteria': EST, 'token': 'cuadre-pesos-3'})
    f = _fila(admin_client)
    assert f is not None and f['stock_sistema'] == 750.0, (
        'quedó en %s y se declararon 750' % (f and f['stock_sistema']))


def test_el_ajuste_conserva_la_POSICION_del_lote(admin_client, lote_partido):
    """La posición es dónde ir a buscarlo: un ajuste que la pierde deja el lote sin dirección."""
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 700.0, 'motivo': 'conteo',
        'estanteria': EST, 'token': 'cuadre-pesos-4'})
    f = _fila(admin_client)
    assert f is not None
    assert f.get('posicion') == 'C3', 'el ajuste perdió la posición: %r' % f.get('posicion')
    assert f.get('estanteria') == EST


def test_el_ajuste_no_hereda_el_estado_RECHAZADO(admin_client, lote_partido):
    """Si el movimiento del ajuste naciera RECHAZADO, el material corregido saldría del stock
    usable de una: el ajuste se aplica sobre lo usable y con el estado de lo usable."""
    from database import get_db
    admin_client.post('/api/inventario/cuadre', json={
        'codigo_mp': CODIGO, 'lote': LOTE, 'fisico': 700.0, 'motivo': 'conteo',
        'estanteria': EST, 'token': 'cuadre-pesos-5'})
    with admin_client.application.app_context():
        filas = get_db().execute(
            "SELECT UPPER(COALESCE(estado_lote,'')), tipo, cantidad FROM movimientos "
            "  WHERE material_id=? AND lote=? AND observaciones LIKE '[cuadre]%'",
            (CODIGO, LOTE)).fetchall()
    assert filas, 'el ajuste no escribió ningún movimiento'
    for estado, tipo, cant in filas:
        assert estado not in ('RECHAZADO', 'CUARENTENA', 'VENCIDO', 'BLOQUEADO'), (
            'el ajuste nació en %s: ese material no cuenta como stock' % estado)


def test_la_hoja_de_PRODUCCION_no_promete_lo_rechazado(app, lote_partido):
    """El mismo lote partido, visto desde la pantalla con la que produccion decide.

    El FEFO y la validacion de stock excluyen los estados no producibles FILA POR FILA, asi
    que de este lote toman 800. La hoja agrupaba primero y decidia por el estado maximo, o sea
    mostraba 1.000 g usables: prometia material que el descuento no toma (M5/M150).
    """
    import sys
    sys.path.insert(0, 'api')
    from database import get_db
    from blueprints.programacion import _lotes_de_material
    with app.app_context():
        d = _lotes_de_material(get_db().cursor(), CODIGO)
    usables = {x['lote']: x['g'] for x in d.get('usables') or []}
    retenidos = {x['lote']: x['g'] for x in d.get('retenidos') or []}
    assert usables.get(LOTE) == 800.0, (
        'la hoja ofrece %s g usables y solo 800 son aprobados' % usables.get(LOTE))
    assert retenidos.get(LOTE) == 200.0, (
        'no declara los 200 g retenidos: desaparecen sin que nadie sepa por que')


def test_lo_usable_de_la_hoja_es_lo_MISMO_que_el_motor_descuenta(app, lote_partido):
    """La invariante que de verdad importa: lo que la pantalla ofrece y lo que el descuento
    puede tomar tienen que ser el MISMO numero."""
    import sys
    sys.path.insert(0, 'api')
    from database import get_db
    from blueprints.programacion import _lotes_de_material, _lotes_disponibles_fefo
    with app.app_context():
        c = get_db().cursor()
        hoja = sum(x['g'] for x in (_lotes_de_material(c, CODIGO).get('usables') or [])
                   if x['lote'] == LOTE)
        # (lote, fecha_vencimiento, stock_lote): la cantidad es la TERCERA columna.
        # Se lee del contrato del helper, no se supone (M220).
        motor = sum(float(x[2]) for x in (_lotes_disponibles_fefo(c, CODIGO) or [])
                    if str(x[0]) == LOTE)
    assert round(hoja, 2) == round(motor, 2), (
        'la hoja ofrece %s g y el motor puede tomar %s g' % (hoja, motor))
