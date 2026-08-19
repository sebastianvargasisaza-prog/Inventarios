"""El stock que se VENCE antes de usarse no cubre el consumo (Sebastián 25-jul).

"Abastecimiento es la fuente de la solicitud para no quedarnos sin materias primas."

El motor tomaba el stock como un número plano: una MP que vence en 30 días contaba igual para
cubrir un consumo del día 90, así que el déficit salía CORTO y no se compraba. Medido contra
producción: 53 MPs con ese problema (5 dentro del horizonte de 90d, ~4.7 kg; el caso extremo,
202 kg de Probetaína de los que sólo 9.9 seguían vigentes al día 365).

Modelo correcto: un lote que vence el día D sólo cubre el consumo ANTERIOR a D, así que lo que
sobra en D (`stock_que_vence_hasta_D − consumo_hasta_D`) se pierde, y el desperdicio al horizonte
h es el PEOR de esos excedentes hasta h.
"""


def _f(lotes, consumo, horizontes=(15, 30, 60, 90)):
    from blueprints.programacion import _desperdicio_por_vencimiento
    return _desperdicio_por_vencimiento(lotes, consumo, list(horizontes))


def test_sin_fechas_de_vencimiento_no_desperdicia_nada(app):
    """Un lote sin fecha se trata como que NO vence · nunca infla la compra (conservador)."""
    r = _f([(None, 5000.0)], {15: 100, 30: 200, 60: 400, 90: 600})
    assert all(v == 0 for v in r.values()), r


def test_el_caso_del_comentario(app):
    """100 g que vencen el día 50 · consumo 30 g a 50d y 60 g a 90d → se pierden 70 g."""
    r = _f([(50, 100.0)], {15: 9, 30: 18, 60: 36, 90: 60})
    # consumo interpolado al día 50 = 18 + (36-18)*(20/30) = 30
    assert r[90] == 70.0, r
    assert r[15] == 0.0, 'antes de que venza no hay desperdicio'


def test_si_alcanzo_a_consumirlo_no_hay_desperdicio(app):
    """Mismo lote, pero el consumo previo lo supera → no se pierde nada."""
    r = _f([(50, 100.0)], {15: 40, 30: 80, 60: 160, 90: 240})
    assert all(v == 0 for v in r.values()), r


def test_el_desperdicio_es_monotono(app):
    """Lo que ya se perdió no se recupera en un horizonte más largo."""
    r = _f([(20, 500.0), (70, 300.0)], {15: 10, 30: 20, 60: 40, 90: 60})
    vals = [r[h] for h in (15, 30, 60, 90)]
    assert vals == sorted(vals), vals
    assert vals[-1] > 0


def test_varios_lotes_se_evaluan_del_que_vence_primero(app):
    """FEFO: el excedente se mide acumulando por fecha de vencimiento, no lote a lote."""
    # 100 g vencen a 30d, otros 100 a 60d · consumo total 90d = 150
    r = _f([(30, 100.0), (60, 100.0)], {15: 25, 30: 50, 60: 100, 90: 150})
    # al día 30: acumulado 100, consumo 50 → sobran 50
    # al día 60: acumulado 200, consumo 100 → sobran 100 (peor)
    assert r[90] == 100.0, r


def test_endpoint_expone_el_dato_y_el_deficit_lo_respeta(app):
    """El motor real: `vence_sin_usar_g` viaja en la respuesta y el déficit lo descuenta."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    resp = c.get('/api/abastecimiento/consumo-horizontes?dias=365&foco=90')
    assert resp.status_code == 200, resp.data[:300]
    d = resp.get_json()
    hs = d['horizontes']
    for m in (d.get('mps') or []):
        assert 'vence_sin_usar_g' in m, m.get('codigo')
        for h in hs:
            venc = float(m['vence_sin_usar_g'][str(h)])
            assert venc >= 0, m
            cons = float(m['consumo'][str(h)])
            disp = float(m['stock_actual_g']) + float(m['cuarentena_g']) - venc
            esperado = round(max(cons - disp, 0), 1)
            real = float(m['deficit'][str(h)])
            assert abs(esperado - real) < 0.5, (m['codigo'], h, esperado, real)


# ── Y los TRES hermanos que deciden la COMPRA ────────────────────────────────────
#
# 18-ago · medido contra los datos REALES de producción (194 items × 7 horizontes):
# el déficit descontaba el stock que se vence antes de usarse y `neto_a_pedir`,
# `comprar_ahora_g` y la cobertura NO. Resultado: cuatro materias primas decían
# "te falta" y "no compres" al mismo tiempo, sin nada en camino. La peor:
#
#   MP00214 Betaglucano · stock 3.002 g, de los cuales 2.409 se vencen antes de
#   usarse · consumo 90d 731,9 g · déficit 139,1 g · comprar ahora: 0
#
# Es M45 en su forma cara -- el arreglo del 25-jul se aplicó a UNO de cuatro -- y
# M5: el número que se muestra no era el que decide.

def _cli(app):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


_ZCOD, _ZPROD = 'ZVENC01', 'ZVENC PRODUCTO'


def _borrar_caso_vencimiento():
    import os
    import sqlite3
    cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (_ZCOD,))
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (_ZPROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (_ZPROD,))
        cn.execute("DELETE FROM produccion_programada WHERE producto=?", (_ZPROD,))
        cn.commit()
    finally:
        cn.close()


def _sembrar_caso_vencimiento(dias_produccion=35, dias_vence=12):
    """Una MP con stock que NO llega vivo a la fecha en que se va a usar.

    Se limpia ANTES (M103): una corrida anterior dejaria el lote puesto y el caso
    mediria otra cosa.
    """
    import os
    import sqlite3
    from datetime import datetime, timedelta
    _borrar_caso_vencimiento()
    hoy = datetime.now() - timedelta(hours=5)
    cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                   "VALUES (?,?,1)", (_ZCOD, 'ZVENC INCI'))
        cn.execute("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) "
                   "VALUES (?,1,10)", (_ZPROD,))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                   "material_nombre, porcentaje) VALUES (?,?,?,10)",
                   (_ZPROD, _ZCOD, 'ZVENC INCI'))
        cn.execute("INSERT INTO produccion_programada (producto, fecha_programada, "
                   "cantidad_kg, lotes, origen, estado) "
                   "VALUES (?,?,10,1,'eos_plan','pendiente')",
                   (_ZPROD, (hoy + timedelta(days=dias_produccion)).strftime('%Y-%m-%d')))
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador, fecha_vencimiento) "
                   "VALUES (?,?,'Entrada',5000,'ZVENC-L1',?,'VIGENTE','guard',?)",
                   (_ZCOD, 'ZVENC INCI', hoy.strftime('%Y-%m-%d'),
                    (hoy + timedelta(days=dias_vence)).strftime('%Y-%m-%d')))
        cn.commit()
    finally:
        cn.close()


def test_el_neto_a_pedir_se_DERIVA_del_deficit(app, db_clean):
    """La invariante que impide que vuelvan a divergir: neto == deficit - lo que ya viene.

    Escritos como dos cuentas separadas, cualquier regla que se agregue a una (el
    vencimiento fue la primera) deja a la otra atrás sin que nadie se entere.
    """
    _sembrar_caso_vencimiento()          # sin datos el guard no mide nada, y eso no es verde
    try:
        d = _cli(app).get('/api/abastecimiento/consumo-horizontes').get_json()
    finally:
        _borrar_caso_vencimiento()
    hs = [str(h) for h in d['horizontes']]
    revisados = 0
    for it in (d.get('mps') or []):
        pend = float(it.get('pendiente_compras_g') or 0)
        for h in hs:
            esperado = round(max(float(it['deficit'][h]) - pend, 0), 1)
            real = float(it['neto_a_pedir'][h])
            assert abs(esperado - real) < 0.6, (
                'el neto no es el déficit menos lo que ya viene', it['codigo'], h,
                esperado, real)
            revisados += 1
    for it in (d.get('mees') or []):
        pend = float(it.get('pendiente_compras_u') or 0)
        for h in hs:
            esperado = round(max(float(it['deficit'][h]) - pend, 0), 1)
            real = float(it['neto_a_pedir'][h])
            assert abs(esperado - real) < 0.6, (it['codigo'], h, esperado, real)
            revisados += 1
    assert revisados > 0, 'el guard no midió nada'


def test_un_stock_que_se_VENCE_manda_a_comprar(app, db_clean):
    """El caso real: el stock existe, no llega vivo a la fecha, y hay que comprar.

    Antes decía déficit > 0 y comprar_ahora = 0 · o sea que la pantalla avisaba y la
    columna con la que se compra decía que no hiciera nada.
    """
    import os
    import sqlite3
    from datetime import datetime, timedelta

    hoy = datetime.now() - timedelta(hours=5)
    vence = (hoy + timedelta(days=12)).strftime('%Y-%m-%d')     # se vence YA
    produce = (hoy + timedelta(days=35)).strftime('%Y-%m-%d')   # dentro del reorden (lead+buffer)
    COD, PROD = 'ZVENC01', 'ZVENC PRODUCTO'

    cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cn.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        cn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                   "VALUES (?,?,1)", (COD, 'ZVENC INCI'))
        cn.execute("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) "
                   "VALUES (?,1,10)", (PROD,))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                   "material_nombre, porcentaje) VALUES (?,?,?,10)",
                   (PROD, COD, 'ZVENC INCI'))
        cn.execute("INSERT INTO produccion_programada (producto, fecha_programada, "
                   "cantidad_kg, lotes, origen, estado) VALUES (?,?,10,1,'eos_plan','pendiente')",
                   (PROD, produce))
        # 5 kg en bodega... que se vencen antes de que se produzca
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador, fecha_vencimiento) "
                   "VALUES (?,?,'Entrada',5000,'ZVENC-L1',?, 'VIGENTE','guard',?)",
                   (COD, 'ZVENC INCI', hoy.strftime('%Y-%m-%d'), vence))
        cn.commit()
    finally:
        cn.close()

    try:
        d = _cli(app).get('/api/abastecimiento/consumo-horizontes?tipo=mp').get_json()
        it = next((x for x in (d.get('mps') or []) if x['codigo'] == COD), None)
        assert it, 'la MP sembrada no aparece en abastecimiento'

        venc = float(it['vence_sin_usar_g']['90'])
        cons = float(it['consumo']['90'])
        assert cons > 0, ('el lote sembrado no generó consumo', it)
        assert venc > 0, ('no detectó que el stock se vence antes de usarse', it)

        assert float(it['deficit']['90']) > 0, ('el déficit ignoró el vencimiento', it)
        assert float(it['neto_a_pedir']['90']) > 0, (
            'dice que FALTA y manda a pedir CERO: el stock que se vence se está '
            'contando como disponible justo donde se decide la compra', it)
        assert float(it['comprar_ahora_g']) > 0, (
            'la columna con la que se compra dice que no hay nada que comprar', it)
    finally:
        cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
        try:
            cn.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
            cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
            cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
            cn.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
            cn.commit()
        finally:
            cn.close()
