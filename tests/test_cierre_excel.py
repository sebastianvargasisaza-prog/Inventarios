# -*- coding: utf-8 -*-
"""El Excel del cierre: separado por QUIÉN lo resuelve, y diciendo qué hacer.

Sebastián: *"todo lo que hicimos ya está ... qué queda por fuera: las que pusimos NO EXISTE
-- en esa estantería ni había más nada -- y las que faltan por UBICAR. Ésas son las que
necesito que me revisen los jefes y digan 'ésta no está'"*.

Eso parte la lista en tres cosas que **no las resuelve la misma persona**, y mezclarlas es lo
que hace que no se resuelva ninguna:

  · **Revisar con los jefes** · no encontrado + sin ubicación
  · **Falta contar** · lo que nadie revisó (Sebastián ya sabe cuál es)
  · **Otros datos faltantes** · vencimiento, INCI, lote

Y cada fila dice **qué pasó** y **qué hacer**: un listado que no dice qué hacer se lo devuelven
a uno.
"""
import io

import pytest

COD = 'MPXLSCIERRE'
EST = 'XLS-EST-3'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id LIKE ?", (COD + '%',))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE ?", (COD + '%',))
        c.commit()


@pytest.fixture()
def pendientes(app):
    """Uno de cada clase: sin revisar, sin ubicación y sin vencimiento."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        for suf in ('', 'U', 'V'):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, "
                      " activo) VALUES (?,?,?,1)",
                      (COD + suf, 'MP XLS' + suf, 'INCI XLS' + suf))
        def _m(cod, lote, est, venc):
            c.execute(
                "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                " fecha, operador, estanteria, posicion, fecha_vencimiento, estado_lote) "
                "VALUES (?,?,'Entrada',400.0,?,?,?,?,'Z9',?,'VIGENTE')",
                (cod, 'MP XLS', lote, '2026-08-01 08:00:00', 'test', est, venc))
        _m(COD, 'L-XLS-CONTAR', EST, '2027-05-05')     # nadie lo reviso
        _m(COD + 'U', 'L-XLS-SINUBI', '', '2027-05-05')  # sin ubicacion
        _m(COD + 'V', 'L-XLS-SINVENC', EST, '')          # sin vencimiento
        c.commit()
    yield
    _limpiar(app)


def _libro(client):
    openpyxl = pytest.importorskip('openpyxl')
    r = client.get('/api/inventario/cuadre-informe/xlsx')
    assert r.status_code == 200, r.data[:200]
    assert 'spreadsheetml' in r.headers.get('Content-Type', ''), (
        'no salio como Excel: %s' % r.headers.get('Content-Type'))
    return openpyxl.load_workbook(io.BytesIO(r.data))


def _filas(ws):
    out = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and any(x not in (None, '') for x in row):
            out.append(list(row))
    return out


def test_el_excel_trae_las_TRES_hojas(admin_client, pendientes):
    wb = _libro(admin_client)
    assert wb.sheetnames == ['Revisar con los jefes', 'Falta contar', 'Otros datos faltantes'], (
        'las hojas no estan separadas por quien lo resuelve: %s' % wb.sheetnames)


def test_lo_que_NO_TIENE_UBICACION_va_a_la_hoja_de_los_jefes(admin_client, pendientes):
    """*"las que faltan por ubicar ... que me revisen los jefes"*."""
    wb = _libro(admin_client)
    filas = _filas(wb['Revisar con los jefes'])
    mio = [f for f in filas if f[4] == 'L-XLS-SINUBI']
    assert mio, 'lo que no tiene ubicacion no llego a la hoja de los jefes'
    assert 'ubicaci' in str(mio[0][5]).lower(), 'no dice que paso: %r' % mio[0][5]
    assert 'estanter' in str(mio[0][6]).lower(), 'no dice que hacer: %r' % mio[0][6]


def test_lo_que_NADIE_REVISO_va_a_su_propia_hoja(admin_client, pendientes):
    """No es una duda para un jefe: es trabajo pendiente de contar."""
    wb = _libro(admin_client)
    contar = [f[4] for f in _filas(wb['Falta contar'])]
    jefes = [f[4] for f in _filas(wb['Revisar con los jefes'])]
    assert 'L-XLS-CONTAR' in contar, 'lo que nadie reviso no quedo en su hoja'
    assert 'L-XLS-CONTAR' not in jefes, (
        'lo que falta contar se mezclo con lo que necesita el ojo de un jefe')


def test_el_dato_que_se_completa_solo_NO_va_con_los_jefes(admin_client, pendientes):
    wb = _libro(admin_client)
    otros = [f[4] for f in _filas(wb['Otros datos faltantes'])]
    jefes = [f[4] for f in _filas(wb['Revisar con los jefes'])]
    assert 'L-XLS-SINVENC' in otros, 'el lote sin vencimiento no quedo en su hoja'
    assert 'L-XLS-SINVENC' not in jefes, 'un dato que se completa en pantalla fue a los jefes'


def test_cada_fila_dice_QUE_HACER(admin_client, pendientes):
    """Un listado que no dice que hacer se lo devuelven a uno."""
    wb = _libro(admin_client)
    n = 0
    for hoja in wb.sheetnames:
        for f in _filas(wb[hoja]):
            if f[0] == 'Nada pendiente en esta lista.':
                continue
            n += 1
            assert str(f[5] or '').strip(), 'una fila no dice que paso: %r' % f
            assert str(f[6] or '').strip(), 'una fila no dice que hacer: %r' % f
    assert n >= 3, 'la sonda solo midio %d filas' % n


def test_dice_DONDE_ir_a_buscar(admin_client, pendientes):
    """Sin estanteria y posicion la lista no se puede repartir."""
    wb = _libro(admin_client)
    cab = [c.value for c in wb['Revisar con los jefes'][1]]
    for t in ('Estantería', 'Posición', 'Material', 'Lote'):
        assert t in cab, 'al Excel le falta la columna %r: %s' % (t, cab)


def test_una_hoja_VACIA_lo_dice_con_palabras(admin_client):
    """Una hoja en blanco se lee como *"no se pudo"*, que es lo contrario de *"no hay nada"*
    (M100)."""
    wb = _libro(admin_client)
    for hoja in wb.sheetnames:
        filas = _filas(wb[hoja])
        if not filas:
            pytest.fail('la hoja %r salio vacia sin decirlo' % hoja)


def test_la_pantalla_OFRECE_bajarlo(app):
    """Una capacidad sin puerta no existe (M121)."""
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    assert 'bajarExcel' in H, 'no hay boton para bajar el Excel'
    assert 'cuadre-informe/xlsx' in H, 'el boton no apunta al endpoint'
