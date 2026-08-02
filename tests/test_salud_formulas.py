"""¿Están las fórmulas PERFECTAS? · las cuatro cosas, por separado (2-ago).

Sebastián: *"necesito que me digas: fórmulas perfectas, hacen match con materias primas,
descuentan y marca en abastecimiento"*. Son cuatro condiciones que se fallan por separado, así
que se chequean por separado -- un "sí" global que junta las cuatro no sirve para arreglar nada.

Y la cuarta no es un defecto de la fórmula: Abastecimiento muestra lo que las producciones
FUTURAS van a consumir. Una fórmula perfecta sin lote en el calendario no aparece, y eso es
correcto (M124: cuando un cálculo excluye algo, hay que decir por qué).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZSALUD PRODUCTO'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    for cod in ('ZZSAL-A', 'ZZSAL-B'):
        _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))


def _mp(cod, activo=1):
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES (?,?,?,?,1)", (cod, 'ZZ ' + cod, 'ZZ ' + cod, activo))


def _formula(items, activo=1):
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,?)", (PROD, activo))
    for cod, pct in items:
        _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
             "porcentaje) VALUES (?,?,?,?)", (PROD, cod, 'ZZ ' + cod, pct))


def _mia(app):
    r = _login(app).get('/api/programacion/salud-formulas')
    assert r.status_code == 200, r.data[:300]
    return next((x for x in r.get_json()['formulas'] if x['producto'] == PROD), None)


def test_una_formula_sana_sale_PERFECTA(app, db_clean):
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 30.0)])
    try:
        f = _mia(app)
        assert f and f['perfecta'] is True, f
        assert f['suma_ok'] and f['match_ok'] and f['descuenta_ok'], f
    finally:
        _limpiar()


def test_detecta_la_suma_que_NO_da_100(app, db_clean):
    """Si no suma 100, el gramaje de CADA ingrediente del lote queda mal."""
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 20.0)])
    try:
        f = _mia(app)
        assert f['suma_ok'] is False and f['perfecta'] is False, f
        assert any('suma' in p for p in f['problemas']), f['problemas']
    finally:
        _limpiar()


def test_detecta_un_codigo_que_NO_existe_en_el_maestro(app, db_clean):
    """Un código que no existe no se puede descontar: la producción sale sin tocar ese material.

    ⓘ El trigger de `formula_items` (M38) impide CREAR una fórmula con un código fantasma, tanto
    en INSERT como en UPDATE. O sea que hoy no se pueden fabricar nuevos. Los que hay en
    producción llegaron por otro lado -- son anteriores al trigger, o el material se dio de baja
    del maestro después. Acá se reproduce esa segunda vía, que es la que sigue viva.
    """
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 30.0)])
    _sql("DELETE FROM maestro_mps WHERE codigo_mp='ZZSAL-B'")
    try:
        f = _mia(app)
        assert f['match_ok'] is False and f['perfecta'] is False, f
        assert any(x['codigo'] == 'ZZSAL-B' for x in f['codigos_sin_maestro']), f
    finally:
        _limpiar()


def test_detecta_un_material_INACTIVO(app, db_clean):
    """Descontinuar un material es `activo=0`, nunca DELETE (GMP conserva registros). Pero una
    fórmula ACTIVA que apunte a un material dado de baja tampoco puede descontar."""
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 30.0)])
    _sql("UPDATE maestro_mps SET activo=0 WHERE codigo_mp='ZZSAL-B'")
    try:
        f = _mia(app)
        assert f['match_ok'] is False, f
        assert any(x['codigo'] == 'ZZSAL-B' for x in f['materiales_inactivos']), f
    finally:
        _limpiar()


def test_detecta_un_ingrediente_al_CERO_por_ciento(app, db_clean):
    """Un ingrediente al 0% está en la receta y no descuenta nada: es igual a no estar (M71)."""
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 100.0), ('ZZSAL-B', 0.0)])
    try:
        f = _mia(app)
        assert f['descuenta_ok'] is False and f['perfecta'] is False, f
        assert any(x['codigo'] == 'ZZSAL-B' for x in f['ingredientes_en_cero']), f
    finally:
        _limpiar()


def test_sin_produccion_programada_NO_es_un_defecto_de_la_formula(app, db_clean):
    """Abastecimiento muestra lo que se va a CONSUMIR. Sin lote en el calendario no hay demanda,
    y marcar eso como 'fórmula rota' mandaría a arreglar lo que está bien."""
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 30.0)])
    try:
        f = _mia(app)
        assert f['perfecta'] is True, f
        assert f['sale_en_abastecimiento'] is False, f
        assert f['problemas'] == [], f
    finally:
        _limpiar()


def test_con_produccion_programada_SI_sale_en_abastecimiento(app, db_clean):
    _limpiar(); _mp('ZZSAL-A'); _mp('ZZSAL-B')
    _formula([('ZZSAL-A', 70.0), ('ZZSAL-B', 30.0)])
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, "
         "estado, origen) VALUES (?, date('now','+10 days'), 10, 1, 'programado', 'eos_plan')",
         (PROD,))
    try:
        f = _mia(app)
        assert f['sale_en_abastecimiento'] is True and f['producciones_programadas'] >= 1, f
    finally:
        _limpiar()
