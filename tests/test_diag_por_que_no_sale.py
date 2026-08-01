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


# ══ la familia · "se usa en varias fórmulas, ¿cómo así?" (1-ago) ════════════════
#
# Sebastián, sobre mi respuesta de ayer: el diagnóstico dijo "ninguna fórmula lo usa" y él
# sabía que el ingrediente SÍ se usa. Las dos cosas eran ciertas: ese CÓDIGO no aparece en
# ninguna fórmula, pero las fórmulas nombran a un pariente de la misma familia (lauryl /
# decyl / caprylyl glucoside son parecidos y son moléculas DISTINTAS).
#
# "Nadie lo usa" a secas manda a agregar el ingrediente a una fórmula que quizá ya lo tiene
# con otro nombre. El diagnóstico tiene que poner los candidatos sobre la mesa -- sin
# emparejarlos, porque cuál es cuál lo decide Alejandro (M19).

def _limpiar_familia():
    for cod in ('ZZFAM-LAURYL', 'ZZFAM-DECYL'):
        _sql("DELETE FROM formula_items WHERE material_id=?", (cod,))
        _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
    _sql("DELETE FROM formula_items WHERE producto_nombre='ZZFAM LIMPIADOR'")
    _sql("DELETE FROM formula_headers WHERE producto_nombre='ZZFAM LIMPIADOR'")


def test_avisa_que_un_PARIENTE_es_el_que_usan_las_formulas(app, db_clean):
    _limpiar_familia()
    # el que se busca: existe, nadie lo nombra, y en bodega ENTRÓ y nunca salió
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZFAM-LAURYL', 'Plantaren ZZ', 'ZZLAURYL ZZGLUCOSIDE'))
    # el pariente: misma familia, y ESE sí está en una fórmula activa
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZFAM-DECYL', 'Decyl ZZ', 'ZZDECYL ZZGLUCOSIDE'))
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,10)",
         ('ZZFAM LIMPIADOR',))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,3.5)", ('ZZFAM LIMPIADOR', 'ZZFAM-DECYL', 'Decyl ZZ'))
    try:
        j = _diag(app, 'ZZFAM-LAURYL')
        assert j['formulas_activas_que_lo_usan'] == 0, j
        assert j['parientes_usados_en_formulas'] >= 1, (
            'no avisó que un pariente SÍ se usa · "nadie lo usa" a secas engaña: %r' % j['veredicto'])
        fam = [p for p in j['parientes'] if p['codigo'] == 'ZZFAM-DECYL']
        assert fam, j['parientes']
        assert fam[0]['usos_en_formulas_activas'], fam[0]
        assert 'MISMA FAMILIA' in j['veredicto'], j['veredicto']
        # y el kardex viaja, que es la evidencia que distingue las dos explicaciones
        assert 'kardex' in fam[0] and 'kardex' in j['codigos'][0], j
    finally:
        _limpiar_familia()


def test_si_NO_hay_parientes_sigue_diciendo_que_falta_el_ingrediente(app, db_clean):
    """Dientes del otro lado: si todo se explicara con 'mirá la familia', el aviso sería ruido."""
    _limpiar_familia()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZFAM-LAURYL', 'ZZUNICO ZZRARO', 'ZZUNICO ZZRARO'))
    try:
        j = _diag(app, 'ZZFAM-LAURYL')
        assert j['parientes_usados_en_formulas'] == 0, j['parientes']
        assert 'falta el ingrediente' in j['veredicto'], j['veredicto']
    finally:
        _limpiar_familia()


def test_NO_promete_que_el_kardex_decide(app, db_clean):
    """Corrección de un error MÍO (1-ago).

    La primera versión del aviso decía: *"mirá el kardex: si éste tiene entradas y cero salidas
    mientras el otro sale, es que la fórmula nombra al otro"*. **Falso.** Las salidas del pariente
    las genera la FÓRMULA al producir, no el hecho físico: existirían igual aunque en planta
    estuvieran virtiendo éste. O sea que el patrón se ve idéntico en las dos explicaciones y la
    regla no distingue nada -- manda a concluir con evidencia que no discrimina, que es peor que
    no dar ninguna regla.

    Lo único que separa (a) de (b) es un conteo FÍSICO. El veredicto tiene que decirlo.
    """
    _limpiar_familia()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZFAM-LAURYL', 'Plantaren ZZ', 'ZZLAURYL ZZGLUCOSIDE'))
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZFAM-DECYL', 'Decyl ZZ', 'ZZDECYL ZZGLUCOSIDE'))
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,10)",
         ('ZZFAM LIMPIADOR',))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,3.5)", ('ZZFAM LIMPIADOR', 'ZZFAM-DECYL', 'Decyl ZZ'))
    try:
        v = _diag(app, 'ZZFAM-LAURYL')['veredicto']
        assert 'CONTEO F' in v, ('no dice que lo que decide es el conteo físico: %s' % v)
        assert 'kardex NO alcanza' in v, ('sigue prometiendo que el kardex decide: %s' % v)
    finally:
        _limpiar_familia()


# ══ el punto ciego que me dio una respuesta equivocada (1-ago) ══════════════════
#
# Sebastián: *"hace poco migramos fórmulas... revisá si no están viendo bien"*. Tenía razón.
# Buscando "lauryl", el cruce miraba (a) el código MP00070 y (b) que la fórmula dijera "lauryl".
# Pero ese material se llama comercialmente "Plantaren Lauryl 1200 / Eversoft 1200": una fórmula
# que lo nombre **"Plantaren 1200"** apuntando a otro código NO aparecía, y el veredicto salía
# "ninguna fórmula lo usa" con total tranquilidad.
#
# Un buscador que sólo conoce la palabra que tecleaste no sirve para probar una AUSENCIA.

def _limpiar_marca():
    for cod in ('ZZMARCA-REAL', 'ZZMARCA-OTRO'):
        _sql("DELETE FROM formula_items WHERE material_id=?", (cod,))
        _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
    _sql("DELETE FROM formula_items WHERE producto_nombre='ZZMARCA LIMPIADOR'")
    _sql("DELETE FROM formula_headers WHERE producto_nombre='ZZMARCA LIMPIADOR'")


def test_encuentra_el_uso_cuando_la_formula_lo_nombra_por_la_MARCA(app, db_clean):
    _limpiar_marca()
    # el material que se busca · su nombre comercial trae la marca
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)",
         ('ZZMARCA-REAL', 'Zzplantaren Zzlauryl 1200', 'ZZLAURYL ZZGLUCOSIDE'))
    # la fórmula lo lleva, pero con OTRO código y nombrado sólo por la marca
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZMARCA-OTRO', 'Zzplantaren 1200', 'ZZLAURYL ZZGLUCOSIDE'))
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,120)",
         ('ZZMARCA LIMPIADOR',))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,3.0)", ('ZZMARCA LIMPIADOR', 'ZZMARCA-OTRO', 'Zzplantaren 1200'))
    try:
        j = _diag(app, 'ZZMARCA-REAL')
        assert j['usos_en_formulas'], (
            'NO vio el uso porque la fórmula lo nombra por la marca: %s' % j['veredicto'])
        u = j['usos_en_formulas'][0]
        assert u['producto'] == 'ZZMARCA LIMPIADOR', u
        assert u['coincide_por'].startswith('nombre_comercial'), u
        assert u['mismo_codigo'] is False, u
        assert 'OTRO C' in j['veredicto'], j['veredicto']
    finally:
        _limpiar_marca()


def test_NO_confunde_a_un_pariente_con_un_uso(app, db_clean):
    """Dientes: si el cruce usara el INCI ('glucoside') en vez de la MARCA, cada pariente
    aparecería como un 'uso' de éste y el veredicto diría lo contrario de la verdad."""
    _limpiar_marca()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)",
         ('ZZMARCA-REAL', 'Zzplantaren Zzlauryl 1200', 'ZZLAURYL ZZGLUCOSIDE'))
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
         "VALUES (?,?,?,1)", ('ZZMARCA-OTRO', 'Zzdecyl Zzglucoside', 'ZZDECYL ZZGLUCOSIDE'))
    _sql("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) VALUES (?,1,120)",
         ('ZZMARCA LIMPIADOR',))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,3.0)", ('ZZMARCA LIMPIADOR', 'ZZMARCA-OTRO', 'Zzdecyl Zzglucoside'))
    try:
        j = _diag(app, 'ZZMARCA-REAL')
        assert not j['usos_en_formulas'], (
            'contó a un pariente como uso de éste: %r' % j['usos_en_formulas'])
    finally:
        _limpiar_marca()


def test_si_NO_hay_INCI_lo_DECLARA_en_vez_de_adivinar(app, db_clean):
    """Sin INCI no se puede separar la marca de la química, así que el cruce por nombre comercial
    se APAGA -- y eso hay que decirlo. Un chequeo que no corrió y no se anuncia se lee como
    'no hay nada', que es justo el engaño que este endpoint existe para evitar (M100)."""
    _limpiar_marca()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)",
         ('ZZMARCA-REAL', 'Zzplantaren Zzlauryl 1200'))
    try:
        j = _diag(app, 'ZZMARCA-REAL')
        assert 'ZZMARCA-REAL' in j['sin_cruce_por_marca_porque_no_tienen_INCI'], j
        assert 'no tiene INCI' in (j.get('aviso') or ''), j.get('aviso')
        assert j['cruce_por_marca'] == [], j['cruce_por_marca']
    finally:
        _limpiar_marca()
