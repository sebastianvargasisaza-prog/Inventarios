"""El desempeño del proveedor sale de la recepción, no de un formulario (27-jul).

Sebastián, sobre la pantalla de Calidad: *"todo esto debe sumarse a la calificación del
proveedor"*.

`proveedores_calificacion` es la parte de GOBIERNO (criticidad, certificaciones, visitas) y se
llena a mano. Lo que faltaba es el DESEMPEÑO, y ese no se teclea: EOS ya registra los hechos en
cada recepción. Un indicador que alguien tiene que recordar actualizar termina viejo y deja de
mirarse; uno derivado siempre dice la verdad de hoy.

Cinco dimensiones, todas de datos que ya existen: cantidad (pedido vs recibido), puntualidad
(fecha prometida vs real), documentación (los 6 criterios del F01), calidad (F01 conforme) y
trazabilidad (¿mandó el lote real, o quedó el provisional que pone EOS?).

La regla que más importa acá: **el puntaje promedia sólo las dimensiones que TIENEN dato**. Un
proveedor sin F01 todavía no tiene nota de documentación, y ponerle 0 lo castigaría por algo que
no hizo mal (M33: un KPI sin denominador va en gris, no en rojo).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida

PROV_BUENO = 'ZZ PROV IMPECABLE'
PROV_MALO = 'ZZ PROV PROBLEMA'


def _login(app, usuario='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for p in (PROV_BUENO, PROV_MALO):
            cur.execute("DELETE FROM recepcion_tecnica_doc WHERE proveedor=?", (p,))
            for oc in cur.execute("SELECT numero_oc FROM ordenes_compra WHERE proveedor=?",
                                  (p,)).fetchall():
                cur.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc[0],))
            cur.execute("DELETE FROM ordenes_compra WHERE proveedor=?", (p,))
        conn.commit()


def _sembrar_oc(app, proveedor, numero, *, pedido, recibido, f_est, f_rec):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                    "fecha_entrega_est, fecha_recepcion, valor_total, creado_por) "
                    "VALUES (?,?,'Recibida','MP',?,?,?,1000,'test')",
                    (numero, proveedor, '2026-07-01', f_est, f_rec))
        cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                    "cantidad_g, cantidad_recibida_g) VALUES (?,?,?,?,?)",
                    (numero, 'MP00050', 'X', pedido, recibido))
        conn.commit()


def _sembrar_f01(app, proveedor, numero, *, lote_prov, resultado, criterios_ok):
    """`criterios_ok` = cuántos de los 6 criterios del F01 cumplió."""
    from database import get_db
    crit = ['si'] * criterios_ok + ['no'] * (6 - criterios_ok)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO recepcion_tecnica_doc (mov_id, numero_oc, lote, codigo_insumo, "
            "nombre_insumo, lote_proveedor, cantidad_recibida, proveedor, fecha_recepcion, "
            "resultado, crit_rotulado, crit_empaque, crit_hoja_seguridad, crit_ficha_tecnica, "
            "crit_coa, crit_doc_coincide, origen, creado_por, creado_en) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MP','test',?)",
            (0, numero, lote_prov, 'MP00050', 'X', lote_prov, '1000', proveedor,
             '2026-07-10', resultado, crit[0], crit[1], crit[2], crit[3], crit[4], crit[5],
             '2026-07-10'))
        conn.commit()


def _traer(c, prov):
    d = c.get('/api/aseguramiento/proveedores-desempeno?desde=2026-01-01&hasta=2026-12-31').get_json()
    assert d and d.get('ok'), d
    fila = [p for p in d['proveedores'] if p['proveedor'] == prov]
    return (fila[0] if fila else None), d


def test_un_proveedor_impecable_saca_verde(app, db_clean):
    _limpiar(app)
    _sembrar_oc(app, PROV_BUENO, 'OC-ZZDES-1', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-09')
    _sembrar_f01(app, PROV_BUENO, 'OC-ZZDES-1', lote_prov='L-REAL-1',
                 resultado='conforme', criterios_ok=6)
    p, _ = _traer(_login(app), PROV_BUENO)
    assert p, 'el proveedor no salió en el desempeño'
    assert p['dimensiones']['cantidad'] == 100.0
    assert p['dimensiones']['puntualidad'] == 100.0
    assert p['dimensiones']['documentacion'] == 100.0
    assert p['dimensiones']['calidad'] == 100.0
    assert p['dimensiones']['trazabilidad'] == 100.0
    assert p['puntaje'] == 100.0 and p['semaforo'] == 'verde', p


def test_lo_que_llego_de_menos_y_tarde_baja_la_nota(app, db_clean):
    """Los dos reclamos clásicos: mandó menos y llegó tarde."""
    _limpiar(app)
    _sembrar_oc(app, PROV_MALO, 'OC-ZZDES-2', pedido=1000, recibido=600,
                f_est='2026-07-05', f_rec='2026-07-20')      # 400 g de menos, 15 días tarde
    p, _ = _traer(_login(app), PROV_MALO)
    assert p['dimensiones']['cantidad'] == 0.0, p['dimensiones']
    assert p['dimensiones']['puntualidad'] == 0.0, p['dimensiones']
    assert p['atraso_promedio_dias'] == 15, p['atraso_promedio_dias']
    assert p['semaforo'] == 'rojo', p


def test_el_lote_provisional_cuenta_contra_la_trazabilidad(app, db_clean):
    """Si el proveedor no manda el lote, EOS pone uno provisional 'OC-...'. Eso NO es un problema
    de EOS, es un dato del proveedor: rompe el cruce con su propio CoA."""
    _limpiar(app)
    _sembrar_oc(app, PROV_MALO, 'OC-ZZDES-3', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-10')
    _sembrar_f01(app, PROV_MALO, 'OC-ZZDES-3', lote_prov='OC-OC-2026-0281-5',
                 resultado='conforme', criterios_ok=6)
    p, _ = _traer(_login(app), PROV_MALO)
    assert p['dimensiones']['trazabilidad'] == 0.0, p['dimensiones']
    assert p['lote_provisional'] == 1 and p['lote_real'] == 0, p


def test_la_documentacion_sale_de_los_seis_criterios_del_f01(app, db_clean):
    """4 de 6 criterios = 66,7%. Es el dato que Calidad ya marca en el F01."""
    _limpiar(app)
    _sembrar_oc(app, PROV_MALO, 'OC-ZZDES-4', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-10')
    _sembrar_f01(app, PROV_MALO, 'OC-ZZDES-4', lote_prov='L-REAL-4',
                 resultado='conforme', criterios_ok=4)
    p, _ = _traer(_login(app), PROV_MALO)
    assert p['dimensiones']['documentacion'] == 66.7, p['dimensiones']


def test_una_dimension_sin_dato_no_cuenta_como_cero(app, db_clean):
    """LA regla que evita calificaciones injustas: un proveedor con OC recibida pero sin F01
    todavía no tiene nota de documentación ni de calidad. Si esas contaran 0, saldría rojo por
    algo que no hizo mal."""
    _limpiar(app)
    _sembrar_oc(app, PROV_BUENO, 'OC-ZZDES-5', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-09')
    p, _ = _traer(_login(app), PROV_BUENO)
    assert p['dimensiones']['documentacion'] is None, p['dimensiones']
    assert p['dimensiones']['calidad'] is None, p['dimensiones']
    assert p['dims_con_dato'] == 2, p['dims_con_dato']
    assert p['puntaje'] == 100.0, ('promedió las dimensiones vacías como 0: %s' % p['puntaje'])
    assert p['semaforo'] == 'verde', p


def test_sin_fecha_prometida_no_hay_incumplimiento(app, db_clean):
    """Si la OC nunca prometió fecha, no se le puede cobrar la demora."""
    _limpiar(app)
    _sembrar_oc(app, PROV_BUENO, 'OC-ZZDES-6', pedido=1000, recibido=1000,
                f_est='', f_rec='2026-07-30')
    p, _ = _traer(_login(app), PROV_BUENO)
    assert p['dimensiones']['puntualidad'] is None, p['dimensiones']


def test_los_peores_salen_primero(app, db_clean):
    """La lista es para saber con quién hay que hablar, así que se ordena por el peor."""
    _limpiar(app)
    _sembrar_oc(app, PROV_BUENO, 'OC-ZZDES-7', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-09')
    _sembrar_oc(app, PROV_MALO, 'OC-ZZDES-8', pedido=1000, recibido=200,
                f_est='2026-07-05', f_rec='2026-07-25')
    _, d = _traer(_login(app), PROV_MALO)
    nombres = [p['proveedor'] for p in d['proveedores']
               if p['proveedor'] in (PROV_BUENO, PROV_MALO)]
    assert nombres and nombres[0] == PROV_MALO, nombres


def test_muestra_el_estado_de_calificacion_junto_a_la_nota(app, db_clean):
    """La nota sin el estado de gobierno no decide nada: un 95% de un proveedor no calificado
    sigue siendo un proveedor no calificado."""
    _limpiar(app)
    _sembrar_oc(app, PROV_BUENO, 'OC-ZZDES-9', pedido=1000, recibido=1000,
                f_est='2026-07-10', f_rec='2026-07-09')
    p, d = _traer(_login(app), PROV_BUENO)
    assert 'estado_calificacion' in p, p
    assert p['estado_calificacion'] == 'sin_calificar', p['estado_calificacion']
    assert 'sin_calificar' in d['resumen'], d['resumen']


def test_solo_lo_ve_quien_debe(app, db_clean):
    """Desempeño de proveedores es información sensible de la relación comercial."""
    c = app.test_client()
    r = c.get('/api/aseguramiento/proveedores-desempeno')
    assert r.status_code in (401, 403), r.status_code


def test_la_pantalla_de_aseguramiento_muestra_el_desempeno(app, db_clean):
    """El texto del panel YA prometía "el scorecard viene del desempeño real registrado en
    Compras/Recepción" y no existía ninguno: una promesa que la UI hacía y el código no cumplía.
    Si alguien quita el panel, esto lo caza."""
    c = _login(app)
    r = c.get('/aseguramiento')
    assert r.status_code == 200, r.status_code
    html = pantalla_servida(c, '/aseguramiento')
    assert 'gob-des-list' in html, 'desapareció el panel de desempeño'
    assert 'gobLoadDesempeno' in html, 'el panel quedó sin su carga'
    assert 'gobLoadDesempeno();' in html, 'no se carga junto con la calificación · abriría vacío'
