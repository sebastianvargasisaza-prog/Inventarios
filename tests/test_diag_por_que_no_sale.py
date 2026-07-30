"""¿Por qué una MP no sale en Abastecimiento? (30-jul)

Alejandro: *"lauryl glucoside no sale en abastecimiento"*. La tabla de Abastecimiento **no es un
catálogo**: lista lo que las producciones PROGRAMADAS van a consumir. Que una MP no aparezca
puede significar cuatro cosas muy distintas -- que no exista, que ninguna fórmula la use, que su
producto no esté programado, o que aporte 0 g -- y hasta ahora había que adivinar cuál.

Una ausencia sin explicación se lee como un error del sistema aunque sea el comportamiento
correcto; y cuando de verdad ES un error, se lee como si fuera normal. Es la misma lección que el
aviso de lotes (M124), aplicada al lado de la demanda.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ PRODUCTO DIAG'
COD = 'MP-ZZDIAG'
NOMBRE = 'Lauryl glucoside ZZTEST'


def _login(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _limpiar():
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))


def _diag(app, q=NOMBRE):
    r = _login(app).get('/api/programacion/diag-por-que-no-sale?q=' + q.replace(' ', '%20'))
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_no_existe_en_ningun_lado_lo_dice(app, db_clean):
    """El caso más simple y el más confuso: nadie la dio de alta."""
    _limpiar()
    j = _diag(app)
    assert j['existe_en_maestro'] is False
    assert 'no sabe que existe' in j['veredicto'] or 'No existe' in j['veredicto'], j['veredicto']


def test_existe_pero_ninguna_formula_la_usa(app, db_clean):
    """A la fórmula le falta el ingrediente · es un problema de datos, no del motor."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
         (COD, NOMBRE, 'LAURYL GLUCOSIDE'))
    j = _diag(app)
    assert j['existe_en_maestro'] is True
    assert j['formulas_activas_que_lo_usan'] == 0
    assert 'NINGUNA f' in j['veredicto'] or 'falta el ingrediente' in j['veredicto'], j['veredicto']


def test_esta_en_la_formula_pero_el_producto_no_esta_programado(app, db_clean):
    """El caso más frecuente y el que más parece un bug sin serlo: no hay nada que consumir."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (COD, NOMBRE))
    _sql("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) "
         "VALUES (?,1000,1,1)", (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
         "VALUES (?,?,?,3.0)", (PROD, COD, NOMBRE))
    j = _diag(app)
    assert j['formulas_activas_que_lo_usan'] == 1
    assert j['con_produccion_programada'] == 0
    assert 'producción programada' in j['veredicto'], j['veredicto']


def test_con_produccion_programada_dice_que_DEBERIA_salir(app, db_clean):
    """Dientes del otro lado: si están las dos cosas, el diagnóstico no puede echarle la culpa
    a los datos -- ahí sí habría que mirar el motor."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (COD, NOMBRE))
    _sql("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) "
         "VALUES (?,1000,1,1)", (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
         "VALUES (?,?,?,3.0)", (PROD, COD, NOMBRE))
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,cantidad_kg,estado,origen) "
         "VALUES (?,?,50,'pendiente','eos_plan')", (PROD, '2027-06-15'))
    j = _diag(app)
    assert j['con_produccion_programada'] == 1, j
    assert 'DEBER' in j['veredicto'].upper(), j['veredicto']


def test_lo_encuentra_por_el_NOMBRE_escrito_en_la_formula(app, db_clean):
    """El material puede estar en la fórmula bajo un código cuyo nombre en el maestro es OTRO
    (renombres, códigos heredados). Buscar sólo por código lo escondería justo en el caso que
    hay que ver: la fórmula dice 'Lauryl glucoside' y el maestro dice otra cosa.

    ⚠ Un código REALMENTE inexistente ya no se puede insertar: `formula_items` tiene trigger
    contra `maestro_mps` activo (M38). Los códigos fantasma que hay en producción son legado
    anterior a ese trigger — por eso la búsqueda mira el material_nombre además del código.
    """
    _limpiar()
    _sql("DELETE FROM formula_items WHERE material_id='MP-ZZOTRO'")
    _sql("DELETE FROM maestro_mps WHERE codigo_mp='MP-ZZOTRO'")
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo) "
         "VALUES ('MP-ZZOTRO','Material con otro nombre ZZTEST',1)")
    _sql("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) "
         "VALUES (?,1000,1,1)", (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
         "VALUES (?,'MP-ZZOTRO',?,2.0)", (PROD, NOMBRE))
    j = _diag(app)
    assert j['usos_en_formulas'], 'no lo encontró por el nombre escrito en la fórmula'
    u = j['usos_en_formulas'][0]
    assert u['material_id'] == 'MP-ZZOTRO' and u['material_nombre'] == NOMBRE
    assert j['existe_en_maestro'] is False, (
        'el nombre no está en el maestro (está sólo en la fórmula) y el diagnóstico debería decirlo')
