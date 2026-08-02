"""El agua NUNCA puede bloquear una producción (Sebastián 1-ago).

*"Hay productos que cuando se da fabricar dice que no hay agua"*. El agua se fabrica en el
laboratorio: no se recepciona, así que su kardex está en CERO por diseño. Se marca con
`controla_stock=0` (mig 218) y todos los caminos deben saltearla.

El hueco: `_no_controla` comparaba `codigo_mp=?` CRUDO mientras el resto del sistema usa
UPPER(TRIM). Un código con un espacio pegado o distinto case no encuentra la fila, la MP queda
como `controla_stock=1`, y el agua -- con kardex 0 -- bloquea el arranque. Es M100: una clave
sin normalizar no da error, da silencio.

Y hay CUATRO códigos de agua en EOS (MP00286, MPAGUAL01, MPAGUALI01, MPAGUALI02), así que el
respaldo por NOMBRE importa: si uno perdiera el flag, el simulador diría "alcanza" y el arranque
rechazaría con "no hay agua" -- las dos pantallas tienen que decir lo mismo (M5).
"""
import os
import sqlite3


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    for cod in ('ZZAGUA-ESP', 'ZZAGUA-CASE', 'ZZMP-REAL'):
        _sql("DELETE FROM formula_items WHERE material_id=?", (cod,))
        _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
    _sql("DELETE FROM formula_items WHERE producto_nombre='ZZAGUA PRODUCTO'")
    _sql("DELETE FROM formula_headers WHERE producto_nombre='ZZAGUA PRODUCTO'")
    _sql("DELETE FROM produccion_programada WHERE producto='ZZAGUA PRODUCTO'")


def test_el_agua_no_cuenta_como_faltante_aunque_su_kardex_este_en_cero(app, db_clean):
    _limpiar()
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _validar_stock_para_produccion
        conn = get_db()
        # agua: sin un solo movimiento en el kardex, como en la realidad
        mps = [{'codigo_mp': 'ZZAGUA-ESP', 'codigo_mp_formula': 'ZZAGUA-ESP',
                'nombre': 'Agua desionizada', 'cantidad_g': 90000.0, 'controla_stock': 0}]
        faltan = _validar_stock_para_produccion(conn.cursor(), mps)
        assert faltan == [], 'el agua se reportó como faltante: %r' % faltan


def test_el_lookup_de_controla_stock_NORMALIZA_la_clave(app, db_clean):
    """No pude REPRODUCIR el "no hay agua" -- lo digo tal cual (1-ago).

    El trigger de `formula_items` rechaza un material_id que no esté en el maestro, tanto en
    INSERT como en UPDATE, así que hoy no se puede sembrar un código sucio ni siquiera para
    probarlo. Eso hace poco probable que la causa sea esa.

    Lo que sí era real y quedó blindado: este lookup comparaba `codigo_mp=?` CRUDO mientras el
    resto del sistema usa UPPER(TRIM). Una clave sin normalizar no da error, da silencio (M100),
    y el silencio acá significa `controla_stock=1` para el AGUA -- que no tiene kardex -- o sea
    producción bloqueada. Es endurecimiento, no el arreglo de un bug demostrado.
    """
    import os as _os
    ruta = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         'api', 'blueprints', 'programacion.py')
    src = open(ruta, encoding='utf-8').read()
    i = src.index('def _no_controla')
    bloque = src[i:i + 2600]
    assert 'UPPER(TRIM(codigo_mp))=?' in bloque, (
        'el lookup de controla_stock volvió a comparar la clave sin normalizar')
    assert '_is_unlimited_mp' in bloque, (
        'se perdió el respaldo por NOMBRE · hay 4 códigos de agua y si uno pierde el flag, el '
        'simulador diría "alcanza" y el arranque rechazaría (M5)')


def test_una_MP_de_verdad_SI_sigue_bloqueando(app, db_clean):
    """Dientes: si todo se tratara como infinito, el control desaparece."""
    _limpiar()
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _validar_stock_para_produccion
        conn = get_db()
        mps = [{'codigo_mp': 'ZZMP-REAL', 'codigo_mp_formula': 'ZZMP-REAL',
                'nombre': 'Peptido carisimo ZZ', 'cantidad_g': 500.0, 'controla_stock': 1}]
        faltan = _validar_stock_para_produccion(conn.cursor(), mps)
        assert len(faltan) == 1, 'una MP real sin stock dejó de bloquear: %r' % faltan
