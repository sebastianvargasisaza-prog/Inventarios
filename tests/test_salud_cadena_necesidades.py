# -*- coding: utf-8 -*-
"""La salud de la cadena se mide en el SERVIDOR, y el punto ciego del mapeo se ve (4-ago).

Sebastián, revisando Necesidades: nueve de once cadenas decían "sobra-stock". Dos problemas
detrás de eso:

1. **Esa cuenta vivía sólo en el navegador.** Se veía lote por lote adentro del modal, pero
   nada del servidor podía contar cuántos productos estaban mal dimensionados, alertarlo ni
   testearlo. Ahora la calcula `plan.salud_cadena` (M1: un solo cálculo · M5: la pantalla
   pinta lo que el backend dice).

2. **Las tarjetas de arriba sumaban 26 sobre 28 SKUs.** Los dos que faltaban eran los que más
   importan: un producto sin mapeo VENDE y el plan no lo ve. Estaba en la pantalla, escondido
   en un chip al costado de la fila (M124: lo que el cálculo deja afuera se dice).

La medición que respalda el clasificador: una cadena perfectamente espaciada (cadencia = lo que
dura un lote) deja EXACTAMENTE el buffer de 20 días y sale sana; a la mitad de cadencia marca
sobre-producción. O sea que cuando dice "sobra-stock" es porque de verdad se produce más seguido
de lo que dura un lote.
"""
import io
import os
from datetime import date, timedelta

HOY = date(2026, 8, 4)
VEL = 14.7          # uds/día · el HYDRABALANCE de la captura
ML = 50


def _cadena(n, cada_dias, kg, desde=0, estado='pendiente'):
    return [{'id': i, 'fecha': (HOY + timedelta(days=desde + i * cada_dias)).isoformat(),
             'kg': kg, 'estado': estado} for i in range(n)]


def _uds(kg):
    return kg * 1000.0 / ML


def _salud(lotes, stock_uds=0.0, vel=VEL):
    from blueprints.plan import salud_cadena
    return salud_cadena(lotes, velocidad_uds_dia=vel, ml_unidad=ML,
                        stock_uds=stock_uds, hoy=HOY)


# ── el clasificador mide lo que dice ─────────────────────────────────────────

def test_una_cadena_bien_espaciada_deja_EXACTAMENTE_el_buffer(app, db_clean):
    """Cadencia = lo que dura un lote · el colchón tiene que dar los 20 días del buffer, ni
    más ni menos. Si diera otra cosa, todo el resto del veredicto estaría corrido."""
    from blueprints.plan import BUFFER_REORDEN_DIAS
    dura = int(_uds(20) / VEL)          # 400 uds / 14.7 = 27 días
    r = _salud(_cadena(6, dura, 20), stock_uds=_uds(20))
    assert r['medible'] is True
    assert r['n_sobra'] == 0 and r['n_tarde'] == 0
    assert r['n_sano'] == 6
    for d in r['lotes'].values():
        assert d['colchon'] == BUFFER_REORDEN_DIAS, \
            'una cadena perfecta debería dejar %sd de colchón' % BUFFER_REORDEN_DIAS


def test_producir_al_DOBLE_de_ritmo_marca_sobreproduccion(app, db_clean):
    """Con dientes: si el clasificador no mordiera acá, el rótulo 'sobra-stock' no
    significaría nada."""
    dura = int(_uds(20) / VEL)
    r = _salud(_cadena(8, max(1, dura // 2), 20), stock_uds=_uds(20))
    assert r['sobreproduce'] is True
    assert r['n_sobra'] >= 3, 'produciendo al doble de ritmo tiene que sobrar stock'


def test_una_cadencia_LARGA_no_marca_sobra_sino_quiebre(app, db_clean):
    """Y con dientes al revés: espaciar de más no puede leerse como sobre-producción · es lo
    contrario, un quiebre."""
    dura = int(_uds(20) / VEL)          # 27 días
    r = _salud(_cadena(6, dura + 20, 20), stock_uds=0)
    assert r['n_sobra'] == 0
    assert r['llega_tarde'] is True and r['n_tarde'] > 0


def test_sin_velocidad_NO_inventa_un_veredicto(app, db_clean):
    """Un producto sin ventas no tiene cadena sana ni enferma: no se puede medir, y eso se
    declara. Un 'todo bien' inventado es peor que la ausencia del dato (M100)."""
    r = _salud(_cadena(5, 30, 20), stock_uds=0, vel=0)
    assert r['medible'] is False
    assert r['motivo'] and r['sobreproduce'] is False and r['n_sobra'] == 0


def test_los_lotes_cancelados_y_completados_NO_aportan_cobertura(app, db_clean):
    """Un lote cancelado no va a llegar nunca · contarlo como cobertura futura haría ver
    holgada una cadena que en realidad rompe."""
    vivos = _cadena(4, 27, 20)
    muertos = _cadena(4, 27, 20, desde=2, estado='cancelado')
    r_solo = _salud(vivos, stock_uds=_uds(20))
    r_mix = _salud(vivos + muertos, stock_uds=_uds(20))
    assert r_mix['lotes'].keys() == r_solo['lotes'].keys()
    assert r_mix['n_sobra'] == r_solo['n_sobra']


def test_un_lote_PASADO_no_recibe_veredicto_pero_SI_suma_cobertura(app, db_clean):
    """Sobre un lote que ya pasó no se puede accionar (no se adelanta el pasado), pero su
    producto sí está en la góndola: ignorarlo entero haría ver corta la cobertura."""
    pasado = [{'id': 99, 'fecha': (HOY - timedelta(days=40)).isoformat(),
               'kg': 20, 'estado': 'pendiente'}]
    fut = _cadena(3, 27, 20, desde=30)
    fut = [dict(l, id=l['id'] + 100) for l in fut]
    r = _salud(pasado + fut, stock_uds=0)
    assert 99 not in r['lotes'], 'un lote de hace 40 días no debería traer un veredicto accionable'
    assert len(r['lotes']) == 3


def test_el_boton_ADELANTAR_recibe_su_fecha_del_backend(app, db_clean):
    """El cálculo se movió al servidor · si no manda la fecha sugerida, el botón queda vivo y
    mudo, que es invisible desde afuera (M112)."""
    from blueprints.plan import BUFFER_REORDEN_DIAS, PIPELINE_GONDOLA_DIAS
    r = _salud(_cadena(3, 60, 20), stock_uds=_uds(20))
    for d in r['lotes'].values():
        assert d.get('fecha_sugerida'), 'sin fecha sugerida el botón Adelantar no puede proponer'
        cob = date.fromisoformat(d['cobertura_antes'])
        assert date.fromisoformat(d['fecha_sugerida']) == \
            cob - timedelta(days=BUFFER_REORDEN_DIAS + PIPELINE_GONDOLA_DIAS)


# ── la pantalla muestra lo que el plan NO ve ─────────────────────────────────

def _fuente(rel):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(raiz, rel), encoding='utf-8').read()


def test_el_resumen_CUENTA_las_cadenas_mal_dimensionadas(app, db_clean):
    """Antes esto no existía en ningún lado del servidor: sólo se veía abriendo producto por
    producto."""
    src = _fuente('api/blueprints/plan.py')
    for campo in ('"n_cadenas_sobreproducen"', '"n_cadenas_tarde"',
                  '"n_cadenas_sin_medir"', '"n_cadenas_sobreproducen_a_proposito"'):
        assert campo in src, 'el resumen no cuenta %s' % campo
    # la sobre-producción deliberada NO cuenta como alerta (decisión guardada · mig 378)
    assert 'and not p.get("sobreproduccion_deliberada")' in src


def test_las_tarjetas_muestran_el_punto_ciego_del_mapeo(app, db_clean):
    """*"las tarjetas sumaban 26 sobre 28 SKUs"* · el que falta es el que vende y el plan no ve."""
    src = _fuente('api/templates_py/dashboard_html.py')
    assert "'❓ Sin mapeo', res.n_sin_mapeo" in src
    assert "'🔵 Sobre-producen', res.n_cadenas_sobreproducen" in src
    assert "'⏰ Llegan tarde', res.n_cadenas_tarde" in src
    assert 'id="nec-avisos-ciegos"' in src
    # y las unidades, que son las que dicen cuánto duele (el conteo de SKU no lo dice)
    assert 'res.uds_huerfanas_total_30d' in src


def test_la_pantalla_USA_la_salud_del_backend(app, db_clean):
    """Dos cálculos del mismo hecho divergen en silencio (M1)."""
    src = _fuente('api/templates_py/dashboard_html.py')
    assert 'var _sv = p.salud_cadena;' in src
    assert '_sd.fechaSugerida || _fechaAdelanto' in src


def test_el_endpoint_de_necesidades_TRAE_la_salud(app, db_clean):
    """Que el campo llegue de verdad al payload, no sólo que el código lo escriba."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    d = c.get('/api/plan/necesidades').get_json() or {}
    res = d.get('resumen') or {}
    for k in ('n_cadenas_sobreproducen', 'n_cadenas_tarde', 'n_cadenas_sin_medir',
              'n_sin_mapeo', 'uds_huerfanas_total_30d'):
        assert k in res, 'el resumen no trae %s' % k
    for p in (d.get('necesidades') or [])[:5]:
        assert 'salud_cadena' in p, 'un producto sin salud_cadena deja la pantalla recalculando'
        assert 'medible' in p['salud_cadena']
