# -*- coding: utf-8 -*-
"""Las reglas de programación que dictó Sebastián, escritas donde se aplican (4-ago).

Sus palabras: *"el sistema automático coloca las producciones 20 días antes de que se agote,
esa es la regla primordial · no programa sábados, domingos ni festivos · intenta un lote por
día, si es necesario dos · no pone más de 200 kilos por día"*, y después: *"no es tope duro, se
puede pasar · incluso siempre prefiere producir lunes, miércoles y viernes para que tengan
martes y jueves de otras actividades"*.

Lo que la auditoría encontró antes de tocar nada:
  · el tope de 200 kg **no existía**: sólo había "máximo 2 lotes por día" y "un lote de 100 kg
    va solo", así que dos de 150 dejaban 300 kg en una jornada;
  · la preferencia lun/mié/vie estaba construida en el helper (`prefer_mwf`) y la cadena **no la
    usaba**: llamaba sin ella, o sea lunes a viernes parejo;
  · y "recalcular horizonte desde este lote" **no aplicaba la regla de los 20 días**: ponía el
    primer lote a una cadencia exacta del ancla, sin mirar cuándo se agota lo hecho.
"""
from datetime import date, timedelta

PROD = 'ZZREG PRODUCTO'


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM produccion_programada WHERE producto LIKE 'ZZREG%'")
        conn.commit()


def _sembrar_dia(app, fecha, kg, producto=PROD):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, "
                     "estado, origen, cantidad_kg) VALUES (?,?,1,'pendiente','eos_plan',?)",
                     (producto, fecha.isoformat(), kg))
        conn.commit()


def _buscar(app, fecha, kg):
    from database import get_db
    from blueprints.plan import _proxima_fecha_habil
    with app.app_context():
        return _proxima_fecha_habil(get_db().cursor(), fecha, prefer_mwf=True,
                                    lote_kg=kg, producto_nombre=PROD)


def _lunes(desde=None):
    d = desde or date(2026, 9, 7)      # 7-sep-2026 es lunes
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


# ── el tope de 200 kg por día ────────────────────────────────────────────────

def _slots_generador(kgs, max_kg=None, lotes_max=2):
    """Reproduce el contador de cupo de los GENERADORES (el que no pasa por
    `_proxima_fecha_habil`), que es donde estaba el hueco de verdad."""
    from blueprints.plan import MAX_KG_POR_DIA_PREFERIDO
    tope = MAX_KG_POR_DIA_PREFERIDO if max_kg is None else max_kg
    slots, slots_kg, out = {}, {}, []
    d = _lunes()
    for kg in kgs:
        fd = d
        for _ in range(60):
            iso = fd.isoformat()
            cabe = (slots_kg.get(iso, 0.0) + kg) <= tope or kg > tope
            if slots.get(iso, 0) < lotes_max and cabe:
                slots[iso] = slots.get(iso, 0) + 1
                slots_kg[iso] = slots_kg.get(iso, 0.0) + kg
                out.append(fd)
                break
            fd += timedelta(days=1)
    return out, slots_kg


def test_los_generadores_no_apilan_mas_de_200_kg_en_un_dia(app, db_clean):
    """ACÁ estaba el hueco real. `_proxima_fecha_habil` ya lo cuidaba de rebote (máximo 2 lotes
    y el de 100 kg va solo, así que dos normales nunca llegan a 200), pero los generadores
    tienen su PROPIO contador y sólo miraban cantidad de lotes: dos de 150 kg dejaban 300 kg en
    una jornada."""
    _, kg_por_dia = _slots_generador([150, 150])
    assert max(kg_por_dia.values()) <= 200, 'apiló %s kg en un día' % max(kg_por_dia.values())


def test_el_tope_de_kilos_MUERDE(app, db_clean):
    """Prueba de dientes explícita: sin el tope, los dos lotes de 150 caen el mismo día. Si esto
    no cambiara, el guard sería decorativo (que es como pasaron la primera versión de estos
    tests: verdes por la razón equivocada)."""
    fechas_con, _ = _slots_generador([150, 150])
    fechas_sin, _ = _slots_generador([150, 150], max_kg=99999)
    assert fechas_sin[0] == fechas_sin[1], 'sin tope deberían caer juntos'
    assert fechas_con[0] != fechas_con[1], 'con tope NO deberían caer juntos'


def test_pero_NO_es_un_muro(app, db_clean):
    """Sebastián: *"no es tope duro, se puede pasar"* · un lote que por sí solo pasa el tope se
    coloca igual. Frenar una producción por una preferencia de carga sería peor que el
    problema."""
    fechas, kg_por_dia = _slots_generador([400])
    assert len(fechas) == 1, 'dejó un lote grande sin fecha por el tope de kilos'
    assert max(kg_por_dia.values()) == 400


def test_dos_lotes_chicos_SI_caben_juntos(app, db_clean):
    """Con dientes al revés: si el tope frenara de más, la planta perdería el segundo turno."""
    fechas, _ = _slots_generador([40, 40])
    assert fechas[0] == fechas[1], 'no dejó dos lotes chicos el mismo día (80 kg está lejos del tope)'


def test_los_DOS_generadores_cuentan_kilos(app, db_clean):
    """Son dos funciones hermanas con contador propio · arreglar una y dejar la otra es el
    patrón que más se repite (M45)."""
    import io as _io
    import os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api/blueprints/plan.py'), encoding='utf-8').read()
    assert src.count('def _tomar_slot(desde, kg=0.0)') == 1
    assert src.count('def _slot(desde, kg=0.0)') == 1
    assert src.count('MAX_KG_POR_DIA_PREFERIDO') >= 4, 'el tope no se aplica en todos los caminos'


# ── lunes, miércoles y viernes ───────────────────────────────────────────────

def test_prefiere_lunes_miercoles_viernes(app, db_clean):
    """*"para que tengan martes y jueves de otras actividades"*."""
    _limpiar(app)
    martes = _lunes() + timedelta(days=1)
    f = _buscar(app, martes, 30)
    assert f is not None and f.weekday() in (0, 2, 4), \
        'cayó en %s · debería preferir lunes/miércoles/viernes' % f.strftime('%A')


def test_la_CADENA_usa_la_preferencia(app, db_clean):
    """El helper tenía la preferencia construida desde hace tiempo y la cadena llamaba SIN ella:
    una capacidad que nadie activa es una capacidad que no existe (M121). Se verifica en los DOS
    gemelos, no en uno: la primera versión de este test miraba el helper y por eso pasaba verde
    aunque la cadena no lo usara."""
    import io as _io
    import os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api/blueprints/plan.py'), encoding='utf-8').read()
    n = src.count('_proxima_fecha_habil(c, _target, prefer_mwf=True')
    assert n == 2, 'los dos caminos que crean la cadena deben preferir lun/mié/vie · hay %d' % n


def test_acepta_martes_si_los_preferidos_estan_llenos(app, db_clean):
    """Es preferencia, no regla: si lunes/miércoles/viernes no dan, se usa martes o jueves antes
    que dejar el producto sin programar."""
    _limpiar(app)
    l = _lunes()
    # saturo lunes, miércoles y viernes de esa semana y de la siguiente
    for semana in (0, 1):
        for delta in (0, 2, 4):
            d = l + timedelta(days=semana * 7 + delta)
            _sembrar_dia(app, d, 120)
            _sembrar_dia(app, d, 120)
    f = _buscar(app, l, 30)
    assert f is not None, 'no encontró fecha con los preferidos saturados'


def test_nunca_cae_en_sabado_domingo_ni_festivo(app, db_clean):
    """Esto no es preferencia: la planta no abre."""
    from blueprints.plan import es_festivo_colombia
    _limpiar(app)
    d = date(2026, 9, 1)
    for _ in range(40):
        f = _buscar(app, d, 30)
        assert f is not None
        assert f.weekday() < 5, 'programó en fin de semana: %s' % f
        assert not es_festivo_colombia(f), 'programó en festivo: %s' % f
        d += timedelta(days=3)


# ── la regla de los 20 días ──────────────────────────────────────────────────

def test_recalcular_horizonte_aplica_los_20_dias(app, db_clean):
    """Este camino ponía el primer lote a una cadencia EXACTA del ancla, sin mirar cuándo se
    agota lo ya hecho · o sea la regla primordial no aplicaba por ahí."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, 'api/blueprints/plan.py'), encoding='utf-8').read()
    i = src.find('def plan_programar_cadencia_desde_lote')
    if i < 0:
        i = src.find('first_offset_dias = int(round(float(body.get("first_offset_dias")')
    assert i > 0, 'no encontré el endpoint de recalcular horizonte'
    bloque = src[i:i + 4000]
    assert 'interval_dias - BUFFER_REORDEN_DIAS' in bloque, \
        'el primer lote no aplica los 20 días de reorden'
    assert 'first_offset_dias = interval_dias\n' not in bloque, \
        'volvió el default de una cadencia exacta, sin buffer'


def test_el_buffer_sale_de_UNA_constante(app, db_clean):
    """La misma regla escrita en dos lados se separa sola (M99): ya pasó con los 20 y los 25."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, 'api/blueprints/plan.py'), encoding='utf-8').read()
    assert 'BUFFER_REORDEN_DIAS = 20' in src
    # el endpoint de salud de cadenas y el helper de simulación usan la constante, no un literal
    from blueprints.plan import BUFFER_REORDEN_DIAS, salud_cadena
    assert BUFFER_REORDEN_DIAS == 20
    r = salud_cadena([{'id': 1, 'fecha': (date(2026, 8, 4) + timedelta(days=27)).isoformat(),
                       'kg': 20, 'estado': 'pendiente'}],
                     velocidad_uds_dia=14.7, ml_unidad=50, stock_uds=400, hoy=date(2026, 8, 4))
    assert r['medible'] and r['lotes'][1]['estado'] in ('sano', 'justo', 'sobra', 'tarde')


# ── la referencia de kilos, alineada en las dos pantallas ────────────────────

def test_las_dos_pantallas_usan_la_MISMA_referencia_de_kilos(app, db_clean):
    """El modal propone `velocidad × cadencia` y el tablero de salud comparaba contra
    `velocidad × (cadencia + 20)`: cambiar uno solo dejaba las cadenas nuevas leídas como
    CORTAS, gritando al revés."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plan = io.open(os.path.join(raiz, 'api/blueprints/plan.py'), encoding='utf-8').read()
    dash = io.open(os.path.join(raiz, 'api/templates_py/dashboard_html.py'),
                   encoding='utf-8').read()
    assert 'kg_req = round(vel * cad * ml / 1000.0, 2)' in plan, \
        'el tablero de salud sigue comparando contra cadencia + 20'
    assert '_velDiaM * _intM * 10' in dash, \
        'el modal sigue proponiendo cadencia + 20 en el kg por lote'
    # y el veredicto de las dos sale del MISMO cálculo
    assert 'salud_cadena(' in plan
    assert "_sal.get('sobreproduce')" in plan, \
        'el tablero clasifica con sus propios umbrales en vez de la simulación'
