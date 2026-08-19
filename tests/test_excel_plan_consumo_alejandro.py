# -*- coding: utf-8 -*-
"""El Excel de Alejandro dice el PLAN y lo que se va a gastar · y no miente en el total.

Sebastián 18-ago-2026: *"que diga las producciones de cada producto programadas, cuántos
kilos, cuánto gasta de cada materia prima, cuánto hay, cuánto faltaría con lo que hay, y
el valor total sin contar inventario"*.

Lo que estos guards fijan, y por qué cada uno:

  · que las CUATRO hojas existan con su contenido -- un Excel que abre vacío se ve igual
    que uno que no se generó;
  · que el detalle SUME al agregado: cada gramo de la hoja "Detalle por producción" tiene
    que cuadrar con la hoja "Materia prima". Si no cuadran, el Excel tiene dos verdades
    del mismo hecho y quien lo mira no sabe cuál creer (M161);
  · que el valor use $/kg (M83): `precio_referencia` está en $/kg, así que valorar gramos
    como si fueran kilos infla el total ×1000;
  · y que lo que NO se pudo valorar se DECLARE: un total al que le faltan materiales sin
    avisar se lee como el total real (M124/M155).
"""
import io as _io
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers

COD, PROD = "ZEXC-MP1", "ZEXC PRODUCTO"
COD_SP = "ZEXC-MP2"          # el que NO tiene precio · tiene que salir declarado


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _borrar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cn.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        cn.execute("DELETE FROM movimientos WHERE material_id IN (?,?)", (COD, COD_SP))
        cn.commit()
    finally:
        cn.close()


def _sembrar():
    """Un lote de 20 kg a 40 días · 10% de una MP con precio y 5% de una SIN precio."""
    from datetime import datetime, timedelta
    hoy = datetime.now() - timedelta(hours=5)
    fecha = (hoy + timedelta(days=40)).strftime("%Y-%m-%d")
    _borrar()
    cn = _cn()
    try:
        cn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                   "VALUES (?,?,1)", (COD, "ZEXC INCI UNO"))
        cn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                   "VALUES (?,?,1)", (COD_SP, "ZEXC INCI DOS"))
        # precio_referencia esta en $/kg (M83)
        cn.execute("UPDATE maestro_mps SET precio_referencia=50000 WHERE codigo_mp=?", (COD,))
        cn.execute("UPDATE maestro_mps SET precio_referencia=0 WHERE codigo_mp=?", (COD_SP,))
        cn.execute("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) "
                   "VALUES (?,1,20)", (PROD,))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                   "material_nombre, porcentaje) VALUES (?,?,?,10)",
                   (PROD, COD, "ZEXC INCI UNO"))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                   "material_nombre, porcentaje) VALUES (?,?,?,5)",
                   (PROD, COD_SP, "ZEXC INCI DOS"))
        cn.execute("INSERT INTO produccion_programada (producto, fecha_programada, "
                   "cantidad_kg, lotes, origen, estado) "
                   "VALUES (?,?,20,1,'eos_plan','pendiente')", (PROD, fecha))
        # 500 g en bodega de la MP con precio -> gasta 2000 g, hay 500, faltan 1500
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador) "
                   "VALUES (?,?,'Entrada',500,'ZEXC-L1',?,'VIGENTE','guard')",
                   (COD, "ZEXC INCI UNO", hoy.strftime("%Y-%m-%d")))
        cn.commit()
    finally:
        cn.close()
    return fecha


def _abrir(cli):
    openpyxl = pytest.importorskip("openpyxl")
    r = cli.get("/api/abastecimiento/consumo-bruto-excel?foco=90")
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    assert len(r.data) > 3000, "el Excel salió vacío"
    return openpyxl.load_workbook(_io.BytesIO(r.data), data_only=False)


def _filas(ws, encabezado_fila=4):
    cols = [c.value for c in ws[encabezado_fila]]
    out = []
    for row in ws.iter_rows(min_row=encabezado_fila + 1):
        vals = [c.value for c in row]
        if all(v is None for v in vals):
            continue
        out.append(dict(zip(cols, vals)))
    return out


def test_las_cuatro_hojas_traen_lo_que_Alejandro_pidio(app, db_clean):
    fecha = _sembrar()
    try:
        wb = _abrir(_login(app))
        assert wb.sheetnames == ['Resumen', 'Producciones', 'Materia prima',
                                 'Detalle por producción', 'Envases'], wb.sheetnames

        # 1 · las PRODUCCIONES con sus kilos y su fecha
        prods = [f for f in _filas(wb['Producciones']) if f.get('Producto') == PROD]
        assert prods, "el plan de producción no aparece en el Excel"
        assert float(prods[0]['Kilos']) == 20.0, prods[0]
        assert str(prods[0]['Fecha']) == fecha, prods[0]

        # 2 · lo que GASTA, lo que HAY y lo que FALTA de cada MP
        mps = {f['Código']: f for f in _filas(wb['Materia prima']) if f.get('Código')}
        assert COD in mps, "la materia prima del plan no aparece"
        m = mps[COD]
        assert abs(float(m['Gasta 90d']) - 2.0) < 0.01, ('10% de 20 kg = 2 kg', m)
        assert abs(float(m['Hay (kg)']) - 0.5) < 0.01, m
        assert abs(float(m['Falta 90d']) - 1.5) < 0.01, ('gasta 2, hay 0.5', m)

        # 3 · el VALOR en $/kg, no en $/g (M83)
        assert float(m['Precio $/kg']) == 50000, m
        assert abs(float(m['Valor a consumir']) - 2.0 * 50000) < 1, (
            'el valor no está en $/kg: 2 kg a $50.000 son $100.000', m)
        assert abs(float(m['Valor faltante']) - 1.5 * 50000) < 1, m

        # 4 · el DETALLE explica de dónde sale cada gramo
        det = [f for f in _filas(wb['Detalle por producción'])
               if f.get('Código MP') == COD and f.get('Producto') == PROD]
        assert det, "no se puede rastrear el consumo hasta la producción que lo pide"
        assert abs(float(det[0]['Gasta (kg)']) - 2.0) < 0.01, det[0]
        assert str(det[0]['Fecha']) == fecha, det[0]
    finally:
        _borrar()


def test_el_detalle_SUMA_lo_mismo_que_el_agregado(app, db_clean):
    """Dos hojas del mismo Excel no pueden decir cosas distintas del mismo hecho (M161)."""
    _sembrar()
    try:
        wb = _abrir(_login(app))
        por_mp = {}
        for f in _filas(wb['Detalle por producción']):
            cod = f.get('Código MP')
            if cod:
                por_mp[cod] = por_mp.get(cod, 0.0) + float(f.get('Gasta (kg)') or 0)
        agregado = {f['Código']: float(f.get('Gasta 90d') or 0)
                    for f in _filas(wb['Materia prima']) if f.get('Código')}
        assert por_mp, "la hoja de detalle salió vacía"
        revisados = 0
        for cod, kg_det in por_mp.items():
            if cod not in agregado:
                continue
            assert abs(kg_det - agregado[cod]) < max(0.01, agregado[cod] * 0.01), (
                'el detalle y el agregado no cuadran', cod, kg_det, agregado[cod])
            revisados += 1
        assert revisados > 0, "el guard no comparó nada"
    finally:
        _borrar()


def test_lo_que_no_se_pudo_valorar_se_DECLARA(app, db_clean):
    """Un total al que le faltan materiales sin avisar se lee como el total real."""
    _sembrar()
    try:
        wb = _abrir(_login(app))
        texto = '\n'.join(str(c.value) for row in wb['Resumen'].iter_rows()
                          for c in row if c.value is not None)
        assert 'NO alcanza a valorar' in texto, (
            'el resumen no declara lo que dejó fuera del total', texto[:400])
        assert COD_SP in texto, (
            'la materia prima sin precio no se nombra: su costo falta en el total y '
            'nadie puede saberlo', texto[:600])
    finally:
        _borrar()


def test_el_total_del_resumen_es_el_de_la_tabla(app, db_clean):
    """El número con el que se decide tiene que poder sumarse en la hoja de abajo (M5)."""
    _sembrar()
    try:
        wb = _abrir(_login(app))
        total_resumen = None
        for row in wb['Resumen'].iter_rows():
            for i, c in enumerate(row):
                if isinstance(c.value, str) and 'VALOR TOTAL a consumir' in c.value:
                    total_resumen = row[i + 1].value
        assert total_resumen is not None, 'el resumen no trae el valor total'
        suma = sum(float(f.get('Valor a consumir') or 0)
                   for f in _filas(wb['Materia prima']) if f.get('Código'))
        assert abs(float(total_resumen) - suma) < max(1.0, suma * 0.001), (
            'el total del resumen no coincide con la suma de la tabla',
            total_resumen, suma)
    finally:
        _borrar()


def test_el_desglose_de_lotes_del_resumen_CUADRA(app, db_clean):
    """Los PEDIDOS no son LOTES, y lo proyectado no puede caer en un cajón invisible.

    Al reescribir este Excel perdí el desglose y lo dejé en un renglón que sumaba las
    tres cosas: un desglose que no suma su propio total obliga a desconfiar de los tres
    números (M155). Lo cazó el guard del calendario, que mira el fuente; éste mira el
    Excel que de verdad se descarga.
    """
    _sembrar()
    try:
        wb = _abrir(_login(app))
        celdas = {}
        for row in wb['Resumen'].iter_rows():
            vals = [c.value for c in row]
            if vals and isinstance(vals[0], str):
                celdas[vals[0].strip()] = vals[1] if len(vals) > 1 else None
        etiquetas = ' | '.join(celdas.keys())

        fij = celdas.get('Lotes fijos (los que decidiste)')
        sug = celdas.get('Lotes sugeridos')
        otr = celdas.get('Lotes de otro origen (proyección)')
        tot = celdas.get('= total de lotes')   # las claves vienen con .strip()
        assert None not in (fij, sug, otr, tot), (
            'el resumen no desglosa los lotes por origen', etiquetas)
        assert int(fij) + int(sug) + int(otr) == int(tot), (
            'el desglose no suma su propio total', fij, sug, otr, tot)

        assert any('pedido(s) B2B pendientes' in k for k in celdas), (
            'los pedidos B2B no aparecen · o peor, están sumados dentro de los lotes',
            etiquetas)
    finally:
        _borrar()


def test_la_necesidad_va_por_HORIZONTE_no_solo_por_el_foco(app, db_clean):
    """Sebastián 19-ago: *"que diga necesidades de materias primas para 15 días, 30, 60,
    90, 120, 360"*. Con una sola columna, el Excel contesta una pregunta de las siete.
    """
    _sembrar()
    try:
        wb = _abrir(_login(app))
        cols = [c.value for c in wb['Materia prima'][4]]
        for h in (15, 30, 60, 90, 120, 180, 365):
            assert 'Gasta %sd' % h in cols, ('falta el consumo a %s días' % h, cols)
            assert 'Falta %sd' % h in cols, ('falta el faltante a %s días' % h, cols)
        # y el consumo por horizonte es MONÓTONO en la fila (15d ⊂ 30d ⊂ 60d ...)
        fila = next(f for f in _filas(wb['Materia prima']) if f.get('Código') == COD)
        vals = [float(fila['Gasta %sd' % h] or 0) for h in (15, 30, 60, 90, 120, 180, 365)]
        assert vals == sorted(vals), ('el consumo por horizonte no es acumulativo', vals)

        cols_env = [c.value for c in wb['Envases'][4]]
        for h in (15, 90, 365):
            assert 'Gasta %sd' % h in cols_env, ('los envases no van por horizonte', cols_env)

        # el Resumen trae la necesidad por horizonte, que es lo que se pidió
        txt = '\n'.join(str(c.value) for row in wb['Resumen'].iter_rows()
                        for c in row if c.value is not None)
        assert 'Necesidad de materia prima por horizonte' in txt, txt[:300]
        for h in (15, 30, 60, 90, 120, 180, 365):
            assert '%s días' % h in txt, ('el resumen no llega a %s días' % h)
    finally:
        _borrar()


def test_los_DOS_exceles_se_descargan_como_archivo(app, db_clean):
    """Que el navegador lo baje como archivo, no que lo abra como texto.

    En el CELULAR los botones usaban `window.open(url,'_blank')`: la pestaña nueva recibe
    una descarga y queda EN BLANCO, y el bloqueador de pop-ups la corta seguido -- desde
    afuera se ve como que el botón no hizo nada. La descarga la manda el
    `Content-Disposition: attachment` del servidor, así que ese encabezado es el contrato.
    """
    cli = _login(app)
    for ruta in ('/api/abastecimiento/consumo-bruto-excel',
                 '/api/abastecimiento/export-excel'):
        r = cli.get(ruta)
        assert r.status_code == 200, (ruta, r.get_data(as_text=True)[:200])
        cd = r.headers.get('Content-Disposition', '')
        assert cd.lower().startswith('attachment'), (
            'sin `attachment` el celular abre el archivo en vez de bajarlo', ruta, cd)
        assert '.xlsx' in cd, (ruta, cd)
        assert 'spreadsheetml' in (r.headers.get('Content-Type') or ''), (
            ruta, r.headers.get('Content-Type'))


def test_la_pantalla_no_baja_los_exceles_con_una_pestana_nueva(app, db_clean):
    """El guard del lado del navegador · el otro mide el servidor, éste el disparador."""
    import re as _re
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app), '/inventarios')
    i = js.find('function _abastExportConsumoBruto')
    assert i > 0, 'desapareció el botón del Excel de consumo'
    cuerpo = js[i:i + 400]
    assert "window.open" not in cuerpo, (
        'vuelve a abrir una pestaña para descargar: en el celular queda en blanco',
        cuerpo[:200])
    assert '_abastDescargar' in cuerpo, cuerpo[:200]

    j = js.find('function _abastExportExcel')
    assert j > 0 and 'window.open' not in js[j:j + 400], (
        'el Excel de déficit sigue abriendo pestaña', js[j:j + 200])
