# -*- coding: utf-8 -*-
"""El cierre suma lo trabajado DESDE EL MÓDULO DE INVENTARIO, no sólo desde el cuadre.

Sebastián 22-ago: *"hice nevera, ingresé nuevos materiales y todo lo modifiqué en inventario,
lo ajusté, entonces para el reporte final necesito que eso se sume ya que no lo hice en el
módulo que creamos"*.

Sin esto la nevera saldría como **"nadie lo revisó"** y el informe mandaría a buscar 40
materiales que ya se contaron. Una lista que manda a buscar lo que está es peor que ninguna:
la próxima ya no se mira (M129).

**La clave es no preguntar QUÉ PANTALLA se usó: el kardex es la verdad.** Si alguien tocó un
lote, hay un movimiento. Lo que viene de una producción NO cuenta -- eso es consumo, no
verificación.
"""
import pytest

CODIGO = 'MPNEVERASUM'
LOTE_INV = 'LOTE-NEV-1'      # trabajado desde el modulo de inventario
LOTE_PROD = 'LOTE-NEV-PROD'  # consumido por una produccion: NO es verificacion
LOTE_QUIETO = 'LOTE-NEV-0'   # nadie lo toco
EST = 'NEVERA-TEST'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


def _hoy_col():
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(hours=5))


@pytest.fixture()
def nevera(app):
    from database import get_db
    _limpiar(app)
    hoy = _hoy_col().strftime('%Y-%m-%d %H:%M:%S')
    viejo = '2026-01-05 09:00:00'
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, 'MP DE NEVERA', 'TEST INCI'))
        # 1 · lote que ya existia y NADIE toco hoy
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote) "
            "VALUES (?,?,'Entrada',?,?,?,?,?,'VIGENTE')",
            (CODIGO, 'MP DE NEVERA', 500.0, LOTE_QUIETO, viejo, 'test', EST))
        # 2 · lote que se ingreso HOY desde el modulo de inventario
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote, observaciones) "
            "VALUES (?,?,'Entrada',?,?,?,?,?,'VIGENTE','ingreso manual')",
            (CODIGO, 'MP DE NEVERA', 800.0, LOTE_INV, hoy, 'sebastian', EST))
        # 3 · lote que existia y HOY lo consumio una PRODUCCION
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote) "
            "VALUES (?,?,'Entrada',?,?,?,?,?,'VIGENTE')",
            (CODIGO, 'MP DE NEVERA', 900.0, LOTE_PROD, viejo, 'test', EST))
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote, produccion_id) "
            "VALUES (?,?,'Salida',?,?,?,?,?,'VIGENTE',?)",
            (CODIGO, 'MP DE NEVERA', 100.0, LOTE_PROD, hoy, 'planta', EST, 12345))
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


def test_lo_ingresado_desde_INVENTARIO_sale_en_el_cierre(admin_client, nevera):
    d = _informe(admin_client)
    f = _en(d.get('trabajado_inventario'), LOTE_INV)
    assert f is not None, (
        'lo que se trabajo desde el modulo de inventario no aparece en el cierre')
    assert f.get('neto_g') == 800.0, 'no dice cuanto entro: %r' % f.get('neto_g')
    assert f.get('por'), 'no dice quien lo hizo'
    assert f.get('estanteria') == EST, 'no dice donde esta'


def test_eso_NO_se_reporta_como_sin_revisar(admin_client, nevera):
    """El punto de todo: si cayera en 'nadie lo reviso', el informe mandaria a buscar lo que
    ya se conto, y esa lista se deja de mirar (M129)."""
    d = _informe(admin_client)
    assert _en(d.get('sin_revisar'), LOTE_INV) is None, (
        'lo trabajado desde inventario quedo como "nadie lo reviso"')
    assert _en(d.get('a_buscar'), LOTE_INV) is None, (
        'manda a buscar un lote que se acaba de ingresar')


def test_lo_que_NADIE_toco_si_queda_pendiente(admin_client, nevera):
    """El guard tiene que distinguir, o dejaria de servir: lo que de verdad nadie miro sigue
    en la lista."""
    d = _informe(admin_client)
    assert _en(d.get('sin_revisar'), LOTE_QUIETO) is not None, (
        'un lote que nadie toco desaparecio de los pendientes')


def test_una_PRODUCCION_no_cuenta_como_verificacion(admin_client, nevera):
    """Consumir un lote no es contarlo. Si contara, cada produccion del dia marcaria como
    revisado un material que nadie fue a mirar."""
    d = _informe(admin_client)
    assert _en(d.get('trabajado_inventario'), LOTE_PROD) is None, (
        'un consumo de produccion se conto como trabajo de inventario')
    assert _en(d.get('sin_revisar'), LOTE_PROD) is not None, (
        'el lote que solo consumio produccion deberia seguir pendiente de revisar')


def test_el_cierre_lo_PINTA(app):
    """Una capacidad sin puerta no existe (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    i = H.find('Se trabaj')
    assert i != -1, 'el cierre no tiene la seccion de lo trabajado desde inventario'
    bloque = H[i:i + 1400]
    assert 'neto_g' in bloque, 'no muestra cuanto se movio'
    assert 'trabajado_inventario' in H, 'la seccion no lee la lista'


def test_el_resumen_lo_CUENTA(admin_client, nevera):
    d = _informe(admin_client)
    assert (d.get('resumen') or {}).get('trabajado_inventario', 0) >= 1, (
        'el resumen no cuenta lo trabajado desde el modulo de inventario')
