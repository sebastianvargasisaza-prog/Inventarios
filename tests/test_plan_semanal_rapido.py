# -*- coding: utf-8 -*-
"""El plan semanal: mismo resultado, ~1.200 consultas menos (5-ago).

Sebastián: *"revisa velocidad de la app"*. Éste era el peor caso, y no es "una pantalla lenta":
con 3 workers Gunicorn, **dos personas abriéndolo a la vez dejan la app entera sin atender**, y
el resto de las pantallas empieza a devolver "Unexpected token '<'" — que es el 502 servido como
HTML (M43/M59).

Hacía, por cada producción de la ventana (~30) y por cada MP de su fórmula (~20), **dos**
consultas: el nombre del material y su stock. Ahora las dos se precargan en una consulta cada
una, fuera del loop.

⚠ La regla que gobierna el arreglo, y lo que estos tests protegen de verdad: **un atajo puede
acelerar la respuesta, NO cambiarla** (M128). El bug que M128 documenta nació exactamente así —
un fast-path todo-o-nada que devolvía "no hay" cuando el camino lento decía "hay". Por eso acá
se compara el resultado CON y SIN precarga sobre los mismos datos.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sembrar(app):
    """Un producto con fórmula y stock, programado dentro de la ventana."""
    from database import get_db
    from datetime import date, timedelta
    f = (date.today() + timedelta(days=2)).isoformat()
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for sql in ("DELETE FROM produccion_programada WHERE producto='ZZ PLANSEM'",
                    "DELETE FROM formula_items WHERE producto_nombre='ZZ PLANSEM'",
                    "DELETE FROM formula_headers WHERE producto_nombre='ZZ PLANSEM'",
                    "DELETE FROM movimientos WHERE material_id LIKE 'ZZMP-PS%'",
                    "DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZMP-PS%'"):
            c.execute(sql)
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                  "VALUES ('ZZ PLANSEM', 10, 1)")
        for i, pct in ((1, 60.0), (2, 40.0)):
            cod = 'ZZMP-PS%d' % i
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, activo, stock_minimo) "
                      "VALUES (?,?,1,0)", (cod, 'ZZ Material %d' % i))
            c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                      "                           porcentaje, cantidad_g_por_lote) "
                      "VALUES ('ZZ PLANSEM', ?, ?, ?, ?)",
                      (cod, 'ZZ Material %d' % i, pct, pct * 100))
            c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
                      "                          lote, fecha, estado_lote) "
                      "VALUES (?,?,?, 'Entrada', 'ZZL1', date('now'), 'VIGENTE')",
                      (cod, 'ZZ Material %d' % i, 50000))
            # ⚠ Un lote EN CUARENTENA, a propósito: el plan semanal lo cuenta (mira consumo
            # FUTURO, y si sale de QC a tiempo va a contar). Sin este lote la comparación contra
            # el helper sería ciega a la diferencia que importa — que es exactamente lo que pasó
            # la primera vez que probé los dientes de este test.
            c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, "
                      "                          lote, fecha, estado_lote) "
                      "VALUES (?,?,?, 'Entrada', 'ZZL2', date('now'), 'CUARENTENA')",
                      (cod, 'ZZ Material %d' % i, 7000))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, "
                  "                                   origen, cantidad_kg) "
                  "VALUES ('ZZ PLANSEM', ?, 1, 'programado', 'eos_plan', 10)", (f,))
        conn.commit()
    return f


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        for sql in ("DELETE FROM produccion_programada WHERE producto='ZZ PLANSEM'",
                    "DELETE FROM formula_items WHERE producto_nombre='ZZ PLANSEM'",
                    "DELETE FROM formula_headers WHERE producto_nombre='ZZ PLANSEM'",
                    "DELETE FROM movimientos WHERE material_id LIKE 'ZZMP-PS%'",
                    "DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZMP-PS%'"):
            conn.execute(sql)
        conn.commit()


def _plan(admin_client, desde, hasta):
    r = admin_client.get('/api/planta/plan-semanal?desde=%s&hasta=%s' % (desde, hasta))
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def _fila(d, producto='ZZ PLANSEM'):
    for it in (d.get('items') or d.get('producciones') or []):
        if (it.get('producto') or '') == producto:
            return it
    return None


# ── lo que de verdad importa: el atajo no cambia la respuesta ────────────────

def test_la_PRECARGA_da_el_MISMO_stock_que_el_HELPER_que_reemplaza(app, admin_client, db_clean):
    """M128 en su forma más directa: el atajo tiene que ser indistinguible del camino lento.

    ⚠ La primera versión de este test era VACUA: reemplazaba `_stock_mp` por un contador y
    comparaba las dos corridas — pero como la precarga funciona, el contador nunca se llamaba y
    el test comparaba el camino rápido consigo mismo. Un test que pasa por la razón equivocada
    es peor que no tenerlo (M152). Lo que vale es comparar contra el helper que la precarga
    reemplazó, calculándolo acá."""
    from datetime import date, timedelta
    from database import get_db
    _sembrar(app)
    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=10)).isoformat()

    fila = _fila(_plan(admin_client, desde, hasta))
    assert fila is not None, 'el plan semanal no ve la producción sembrada'
    mps = fila.get('mp_status') or []
    assert mps, 'la producción salió sin materias primas'

    from inventario_helpers import stock_mp_total
    with app.app_context():
        conn = get_db()
        for m in mps:
            esperado = round(stock_mp_total(conn, m['material_id']))
            assert m['stock_total_g'] == esperado, \
                'el atajo cambia el stock de %s: %s vs %s (helper)' % (
                    m['material_id'], m['stock_total_g'], esperado)
    # y el material sembrado tiene stock de verdad · si diera 0 la comparación sería vacua
    assert any(m['stock_total_g'] > 0 for m in mps), \
        'ningún material tiene stock · la comparación no probaría nada'
    _limpiar(app)


def test_el_stock_precargado_INCLUYE_cuarentena_igual_que_antes(app, admin_client, db_clean):
    """El plan mira consumo FUTURO: incluye cuarentena a propósito, porque si esos lotes salen de
    QC a tiempo van a contar. Si la precarga usara el stock canónico (que la excluye) el número
    bajaría y aparecerían déficits que no existen."""
    prog = _src('api/blueprints/programacion.py')
    i = prog.find('_stock_mat = {}')
    assert i > 0, 'no encontré la precarga de stock'
    bloque = prog[i:i + 900]
    # el MISMO CASE que `stock_mp_total`, sin exclusión de estado_lote
    assert "WHEN tipo IN ('Entrada','Ajuste +','Ajuste') THEN cantidad" in bloque
    assert 'estado_lote' not in bloque, \
        'la precarga excluye estados · eso cambia el número respecto del helper que reemplaza'


def test_si_la_precarga_FALLA_la_pantalla_sigue_saliendo(app, db_clean):
    """Un stock en cero sería un déficit inventado. Cuando la precarga no se puede hacer, el
    endpoint va por el camino lento — más lento, pero correcto."""
    prog = _src('api/blueprints/programacion.py')
    i = prog.find('def _stock_precargado')
    assert i > 0, 'no existe el fallback'
    assert 'return _stock_mp(mid, c)' in prog[i:i + 400], \
        'lo que falte en el precalculado no cae al helper · asumiría cero'


def test_YA_NO_hay_una_consulta_por_MP_dentro_del_loop(app, db_clean):
    """Las dos que hacían el N+1: el nombre del material y su stock."""
    prog = _src('api/blueprints/programacion.py')
    i = prog.find("mp_req = _calcular_mp_requerido(producto, lotes, c)")
    assert i > 0
    loop = prog[i:i + 3000]
    assert 'SELECT material_nombre FROM formula_items WHERE material_id=?' not in loop, \
        'volvió la consulta del nombre por MP'
    assert '_stock_mp(mat_id, c)' not in loop, 'volvió el SUM por MP'
    assert '_nombre_mat.get' in loop and '_stock_precargado(' in loop


def test_la_columna_de_DIAS_DE_INVENTARIO_dejo_de_estar_muerta(app, db_clean):
    """La consulta de velocidad estaba apagada con `if False` porque apunta a
    `ordenes_shopify_items`, que no existe · nadie la reemplazó, así que `velocidad_dia` valía 0
    SIEMPRE y la columna salía en gris en todas las filas, desde que se escribió."""
    prog = _src('api/blueprints/programacion.py')
    assert 'FROM ordenes_shopify_items' not in prog, 'sigue apuntando a una tabla que no existe'
    assert 'if False else None  # legacy' not in prog, 'sigue la consulta apagada'
    assert '_vel_sku' in prog and 'FROM ventas_diarias' in prog, \
        'no se conectó a la tabla precalculada que el resto del sistema usa'


def test_el_endpoint_RESPONDE(app, admin_client, db_clean):
    from datetime import date, timedelta
    _sembrar(app)
    d = _plan(admin_client, (date.today() - timedelta(days=1)).isoformat(),
              (date.today() + timedelta(days=10)).isoformat())
    assert isinstance(d, dict)
    _limpiar(app)
