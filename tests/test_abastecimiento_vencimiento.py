"""El stock que se VENCE antes de usarse no cubre el consumo (Sebastián 25-jul).

"Abastecimiento es la fuente de la solicitud para no quedarnos sin materias primas."

El motor tomaba el stock como un número plano: una MP que vence en 30 días contaba igual para
cubrir un consumo del día 90, así que el déficit salía CORTO y no se compraba. Medido contra
producción: 53 MPs con ese problema (5 dentro del horizonte de 90d, ~4.7 kg; el caso extremo,
202 kg de Probetaína de los que sólo 9.9 seguían vigentes al día 365).

Modelo correcto: un lote que vence el día D sólo cubre el consumo ANTERIOR a D, así que lo que
sobra en D (`stock_que_vence_hasta_D − consumo_hasta_D`) se pierde, y el desperdicio al horizonte
h es el PEOR de esos excedentes hasta h.
"""


def _f(lotes, consumo, horizontes=(15, 30, 60, 90)):
    from blueprints.programacion import _desperdicio_por_vencimiento
    return _desperdicio_por_vencimiento(lotes, consumo, list(horizontes))


def test_sin_fechas_de_vencimiento_no_desperdicia_nada(app):
    """Un lote sin fecha se trata como que NO vence · nunca infla la compra (conservador)."""
    r = _f([(None, 5000.0)], {15: 100, 30: 200, 60: 400, 90: 600})
    assert all(v == 0 for v in r.values()), r


def test_el_caso_del_comentario(app):
    """100 g que vencen el día 50 · consumo 30 g a 50d y 60 g a 90d → se pierden 70 g."""
    r = _f([(50, 100.0)], {15: 9, 30: 18, 60: 36, 90: 60})
    # consumo interpolado al día 50 = 18 + (36-18)*(20/30) = 30
    assert r[90] == 70.0, r
    assert r[15] == 0.0, 'antes de que venza no hay desperdicio'


def test_si_alcanzo_a_consumirlo_no_hay_desperdicio(app):
    """Mismo lote, pero el consumo previo lo supera → no se pierde nada."""
    r = _f([(50, 100.0)], {15: 40, 30: 80, 60: 160, 90: 240})
    assert all(v == 0 for v in r.values()), r


def test_el_desperdicio_es_monotono(app):
    """Lo que ya se perdió no se recupera en un horizonte más largo."""
    r = _f([(20, 500.0), (70, 300.0)], {15: 10, 30: 20, 60: 40, 90: 60})
    vals = [r[h] for h in (15, 30, 60, 90)]
    assert vals == sorted(vals), vals
    assert vals[-1] > 0


def test_varios_lotes_se_evaluan_del_que_vence_primero(app):
    """FEFO: el excedente se mide acumulando por fecha de vencimiento, no lote a lote."""
    # 100 g vencen a 30d, otros 100 a 60d · consumo total 90d = 150
    r = _f([(30, 100.0), (60, 100.0)], {15: 25, 30: 50, 60: 100, 90: 150})
    # al día 30: acumulado 100, consumo 50 → sobran 50
    # al día 60: acumulado 200, consumo 100 → sobran 100 (peor)
    assert r[90] == 100.0, r


def test_endpoint_expone_el_dato_y_el_deficit_lo_respeta(app):
    """El motor real: `vence_sin_usar_g` viaja en la respuesta y el déficit lo descuenta."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    resp = c.get('/api/abastecimiento/consumo-horizontes?dias=365&foco=90')
    assert resp.status_code == 200, resp.data[:300]
    d = resp.get_json()
    hs = d['horizontes']
    for m in (d.get('mps') or []):
        assert 'vence_sin_usar_g' in m, m.get('codigo')
        for h in hs:
            venc = float(m['vence_sin_usar_g'][str(h)])
            assert venc >= 0, m
            cons = float(m['consumo'][str(h)])
            disp = float(m['stock_actual_g']) + float(m['cuarentena_g']) - venc
            esperado = round(max(cons - disp, 0), 1)
            real = float(m['deficit'][str(h)])
            assert abs(esperado - real) < 0.5, (m['codigo'], h, esperado, real)
