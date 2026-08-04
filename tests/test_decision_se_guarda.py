# -*- coding: utf-8 -*-
"""La decisión "30 kg cada 2 meses" se GUARDA, no se deduce midiendo lotes (4-ago).

Sebastián: *"digo 30 kilos cada 2 meses, guardar · ¿cómo garantizamos que se replique y que
cuando se abra aparezca?"*.

Hasta hoy no se guardaba en ningún lado. El modal la RECONSTRUÍA midiendo los días entre los
dos primeros lotes futuros, así que mentía en cinco escenarios: al mover un lote la cadencia
cambiaba sola; si quedaba uno solo volvía al default de 2 meses; al cancelar lotes igual; una
cadena hecha por el sistema era invisible; y el corrimiento a día hábil ya distorsionaba la
medición ("cada 60 días" se leía 1,9 o 2,1 meses).

Lo raro es que el modal GEMELO del calendario sí la guardaba, en `sku_planeacion_config`. Dos
pantallas que hacen lo mismo con dos comportamientos distintos: el arreglo no fue inventar una
tabla, fue que ésta escriba donde la otra ya escribía.
"""
PROD = 'ZZDEC PRODUCTO'


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (PROD,))
        conn.commit()


def _cli(app):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _leer(app):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT cadencia_dias, kg_objetivo_lote, horizonte_dias, mix_mode, "
            "       mix_congelado_json FROM sku_planeacion_config WHERE producto_nombre=?",
            (PROD,)).fetchone()


def test_guardar_la_decision_la_deja_escrita(app, db_clean):
    from .conftest import csrf_headers
    _limpiar(app)
    c = _cli(app)
    r = c.post('/api/programacion/decision-produccion',
               json={'producto': PROD, 'cadencia_dias': 61,
                     'kg_objetivo_lote': 30.0, 'horizonte_dias': 730},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    fila = _leer(app)
    assert fila is not None, 'la decisión no quedó guardada'
    assert int(fila[0]) == 61 and float(fila[1]) == 30.0 and int(fila[2]) == 730


def test_al_reabrir_MANDA_lo_guardado_sobre_lo_que_se_deduce(app, db_clean):
    """Con dientes: el payload tiene que traer la decisión · si no llega, el modal vuelve a
    deducirla de los lotes y le muestra al usuario una cadencia que él nunca eligió."""
    from .conftest import csrf_headers
    _limpiar(app)
    c = _cli(app)
    c.post('/api/programacion/decision-produccion',
           json={'producto': PROD, 'cadencia_dias': 45, 'kg_objetivo_lote': 12.5,
                 'horizonte_dias': 1095},
           headers=csrf_headers())
    # El lookup usa el MISMO normalizador de nombre que el resto del motor: si no coincidiera,
    # la decisión existiría en la base y no llegaría nunca a la pantalla (M2).
    from database import get_db
    from blueprints.programacion import _norm_prod_fuerte
    with app.app_context():
        fila = get_db().execute(
            "SELECT producto_nombre, cadencia_dias, kg_objetivo_lote FROM sku_planeacion_config "
            " WHERE producto_nombre=?", (PROD,)).fetchone()
    assert fila and int(fila[1]) == 45
    assert _norm_prod_fuerte(fila[0]) == _norm_prod_fuerte(PROD)
    # y que el motor lo exponga por producto (la lista puede venir vacía en una base sin ventas:
    # lo que se verifica es que el campo VIAJA cuando hay productos)
    d = c.get('/api/plan/necesidades').get_json() or {}
    for p in (d.get('necesidades') or [])[:5]:
        assert 'decision_guardada' in p, \
            'el payload no trae la decisión guardada · el modal seguiría deduciéndola'


def test_un_producto_SIN_decision_no_inventa_una(app, db_clean):
    """None significa "todavía no decidiste". Rellenarlo con un default haría ver como decisión
    tomada algo que nadie decidió."""
    _limpiar(app)
    c = _cli(app)
    d = c.get('/api/plan/necesidades').get_json() or {}
    for p in (d.get('necesidades') or []):
        dg = p.get('decision_guardada')
        assert dg is None or isinstance(dg, dict)
        if isinstance(dg, dict):
            assert any(dg.get(k) for k in ('cadencia_dias', 'kg_objetivo_lote', 'horizonte_dias')), \
                'una fila sin ningún valor no debería viajar como decisión'


def test_guardar_la_cadencia_NO_descongela_el_mix_fijo(app, db_clean):
    """M85: el modal manda cadencia y kg, nunca `mix_mode` · si lo mandara con su default,
    borraría un mix puesto en 'fijo' a propósito."""
    from database import get_db
    from .conftest import csrf_headers
    _limpiar(app)
    c = _cli(app)
    c.post('/api/programacion/decision-produccion',
           json={'producto': PROD, 'cadencia_dias': 61, 'mix_mode': 'fijo'},
           headers=csrf_headers())
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE sku_planeacion_config SET mix_congelado_json=? "
                     "WHERE producto_nombre=?", ('{"x":1}', PROD))
        conn.commit()
    # ahora se guarda SÓLO cadencia y kg, como hace el modal
    c.post('/api/programacion/decision-produccion',
           json={'producto': PROD, 'cadencia_dias': 90, 'kg_objetivo_lote': 44.8},
           headers=csrf_headers())
    fila = _leer(app)
    assert int(fila[0]) == 90, 'no guardó la cadencia nueva'
    assert fila[3] == 'fijo', 'cambió el mix sin que nadie se lo pidiera'
    assert fila[4] == '{"x":1}', 'descongeló el mix · eso borra una decisión del dueño'


def test_el_modal_GUARDA_al_crear_la_cadena():
    """Que el frontend haga la llamada · sin esto el backend queda construido y sin efecto."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, 'api/templates_py/dashboard_html.py'),
                  encoding='utf-8').read()
    i = src.find('async function programarCadenaManual')
    assert i > 0, 'no encontré la función que crea la cadena'
    bloque = src[i:i + 6000]
    assert '/api/programacion/decision-produccion' in bloque, \
        'crear la cadena no guarda la decisión'
    # Mirar el PAYLOAD, no el comentario: el comentario nombra `mix_mode` justamente para
    # explicar por qué NO se manda, así que buscar el nombre suelto probaba otra cosa.
    j = bloque[bloque.find('decision-produccion'):]
    j = j[:j.find('}catch')] if '}catch' in j else j[:1200]
    assert 'mix_mode' not in j, 'manda mix_mode en el body y eso descongelaría un mix fijo (M85)'
    assert 'cadencia_dias' in j and 'kg_objetivo_lote' in j
    # y que el modal LEA lo guardado al abrir
    assert 'p.decision_guardada' in src, 'el modal no lee la decisión guardada'
    assert 'Tu decisión guardada' in src, 'no se ve que sea una decisión y no un default'
