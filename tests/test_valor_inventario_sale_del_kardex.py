# -*- coding: utf-8 -*-
"""El valor del inventario se calculaba DESPUES de una consulta imposible · 19-ago.

Dos rutas de plata -el tablero del CEO y el capital de trabajo de Financiero- empezaban
consultando la tabla `lotes`, que NO EXISTE en este esquema (el kardex canonico es
`movimientos`). La consulta fallaba siempre, el `except` dejaba el valor en 0, y recien
entonces corria el camino canonico que el arreglo del 25-jul habia puesto debajo.

O sea que el numero que se mostraba YA era el correcto. Lo que sobraba era pagar una
consulta que no puede funcionar en cada carga -- y en PostgreSQL, el rollback de su
savepoint. Se retira la consulta muerta y el camino canonico pasa a ser el unico.

Este guard mide lo que importa: que el valor siga siendo el mismo y que salga del
kardex. Un cambio de rendimiento no puede cambiar la respuesta (M128).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'ZVAL01'


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
        cn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))
        cn.commit()
    finally:
        cn.close()


def _sembrar(gramos=10000.0, precio_kg=50000.0):
    """10 kg a $50.000/kg = $500.000 de valor."""
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo, precio_referencia) "
                   "VALUES (?,?,1,?)", (COD, 'ZVAL INCI', precio_kg))
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador) VALUES (?,?,'Entrada',?,'ZVAL-L1',"
                   "date('now','-5 hours'),'VIGENTE','guard')", (COD, 'ZVAL INCI', gramos))
        cn.commit()
    finally:
        cn.close()


def test_el_valor_del_inventario_cuenta_el_stock_del_kardex(app, db_clean):
    cli = _cli(app)
    # ⚠ la llave vive en `/api/gerencia/dashboard-extra`, no en `/kpis` · leer la
    # equivocada haria que el guard se saltee justo lo que revisa (M220/M241)
    antes = float((cli.get('/api/gerencia/dashboard-extra').get_json() or {})
                  .get('inventory_cop') or 0)
    _sembrar()
    try:
        ahora = float((cli.get('/api/gerencia/dashboard-extra').get_json() or {})
                      .get('inventory_cop') or 0)
        assert ahora > antes, (
            "sembrar 10 kg de MP no movio el valor del inventario · el KPI no esta "
            "leyendo el kardex", antes, ahora)
        # 10.000 g x ($50.000/kg / 1000) = $500.000
        assert abs((ahora - antes) - 500000.0) < 1.0, (
            "el valor no cuadra con gramos x precio en $/g · ojo con el factor 1000 (M83)",
            antes, ahora)
    finally:
        _limpiar()


def test_lo_que_esta_en_CUARENTENA_no_se_valora_como_disponible(app, db_clean):
    """El borde: el canonico excluye los 6 estados no disponibles (regla #4)."""
    cli = _cli(app)
    antes = float((cli.get('/api/gerencia/dashboard-extra').get_json() or {})
                  .get('inventory_cop') or 0)
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo, precio_referencia) "
                   "VALUES (?,?,1,50000)", (COD, 'ZVAL INCI'))
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador) VALUES (?,?,'Entrada',10000,'ZVAL-L2',"
                   "date('now','-5 hours'),'CUARENTENA','guard')", (COD, 'ZVAL INCI'))
        cn.commit()
    finally:
        cn.close()
    try:
        ahora = float((cli.get('/api/gerencia/dashboard-extra').get_json() or {})
                      .get('inventory_cop') or 0)
        assert abs(ahora - antes) < 1.0, (
            "se esta valorando como inventario disponible algo que esta en cuarentena",
            antes, ahora)
    finally:
        _limpiar()


def test_ninguna_ruta_lee_la_tabla_INEXISTENTE(app, db_clean):
    """La invariante vive en el CODIGO: una tabla que no existe no da error visible.

    La consulta fallaba y el `except` la convertia en 0, que es indistinguible de
    "no hay inventario" (M4/M94).
    """
    import io
    import os as _os
    import re
    base = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         "api", "blueprints")
    culpables = []
    for nombre in sorted(_os.listdir(base)):
        if not nombre.endswith(".py"):
            continue
        src = io.open(_os.path.join(base, nombre), encoding="utf-8").read()
        sin_com = "\n".join(l for l in src.splitlines()
                            if not l.strip().startswith("#"))
        if re.search(r"FROM\s+lotes\s+(?:l\b|WHERE)", sin_com, re.I):
            culpables.append(nombre)
    assert not culpables, (
        "hay codigo leyendo la tabla `lotes`, que no existe · su fallo se convierte en "
        "un cero indistinguible de 'no hay inventario': %s" % culpables)
