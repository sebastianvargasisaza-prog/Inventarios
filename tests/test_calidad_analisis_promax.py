"""14-jun · Análisis micro pro-max (workflow ultracode): gráficas, alertas, picker de
lote de planta, tooltips 'para qué sirve', y limpieza de nombres (mig 247/248)."""


def test_analisis_micro_paneles(admin_client):
    r = admin_client.get('/api/calidad/micro/analisis?meses=24')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    for k in ('tendencia', 'top_microorganismos', 'conformidad', 'hallazgos', 'ambiental'):
        assert k in d, f'falta panel {k}'
    # con los 432 seed debe haber tendencia y top micro
    assert len(d['top_microorganismos']) > 0
    assert len(d['tendencia']) > 0


def test_micro_alertas_endpoint(admin_client):
    r = admin_client.get('/api/calidad/micro/alertas')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert 'alertas' in d and 'total' in d and 'criticas' in d


def test_lotes_planta_picker(admin_client):
    r = admin_client.get('/api/calidad/lotes-planta?dias=120')
    assert r.status_code == 200, r.data[:200]
    assert 'lotes' in r.get_json()


def test_nombres_limpios_sin_mojibake_ni_sufijo(admin_client):
    # mig 247: no deben quedar nombres con mojibake ni '(PRODUCTO TERMINADO)'
    res = admin_client.get('/api/calidad/micro/resultados').get_json()['resultados']
    micro = [x for x in res if x.get('laboratorio') == 'Microlab Cali']
    assert micro, 'debe haber resultados Microlab'
    for x in micro:
        nom = x.get('producto_nombre') or ''
        assert '�' not in nom, f'mojibake en {nom!r}'
        assert 'PRODUCTO TERMINADO' not in nom.upper(), f'sufijo sin limpiar en {nom!r}'
        # mig 248: la fecha no debe estar vacía
        assert (x.get('fecha_analisis') or ''), f'fecha vacía en {nom!r} ref {x.get("n_referencia")}'


def test_pagina_calidad_tiene_tooltips_y_analisis(admin_client):
    body = admin_client.get('/calidad').get_data(as_text=True)
    assert 'data-tip=' in body, 'faltan tooltips para-qué-sirve'
    assert '[data-tip]' in body, 'falta el CSS de tooltips (ui_help)'
    assert 'tab-analisis' in body and 'loadMicroAnalisis' in body, 'falta la pestaña Análisis'


def test_fisicoquimica_seed_y_post(admin_client):
    from .conftest import csrf_headers
    # seed mig 249 presente
    r = admin_client.get('/api/calidad/fisicoquimica/resultados')
    assert r.status_code == 200, r.data[:200]
    res = r.get_json()['resultados']
    assert any('FÓSFORO' in (x['parametro'] or '').upper() or 'FOSFORO' in (x['parametro'] or '').upper() for x in res), 'falta el seed FQ'
    # POST nuevo
    r2 = admin_client.post('/api/calidad/fisicoquimica/resultados',
                           json={'producto_nombre': 'GEL HIDRATANTE', 'parametro': 'pH', 'resultado': '5.8', 'unidad': '—'},
                           headers=csrf_headers())
    assert r2.status_code in (200, 201), r2.data[:200]
