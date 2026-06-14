"""14-jun · Carga histórica de Microlab Cali (mig 246).

Verifica que el seed quedó cargado, etiquetado por categoría, con N° de referencia, y
que el heatmap de producto NO incluye las muestras ambientales.
"""


def test_seed_microlab_cargado(admin_client):
    r = admin_client.get('/api/calidad/micro/resultados')
    assert r.status_code == 200, r.data[:200]
    res = r.get_json()['resultados']
    micro = [x for x in res if x.get('laboratorio') == 'Microlab Cali']
    assert len(micro) >= 100, f'deben cargarse los resultados de Microlab · {len(micro)}'
    # traen N° de referencia y categoría
    assert any(x.get('n_referencia') for x in micro), 'falta n_referencia'
    assert {x.get('categoria') for x in micro} >= {'producto', 'ambiente'}, 'faltan categorías'


def test_filtro_categoria_ambiente(admin_client):
    r = admin_client.get('/api/calidad/micro/resultados?categoria=ambiente')
    assert r.status_code == 200
    res = r.get_json()['resultados']
    assert res, 'debe haber muestras ambientales'
    assert all(x['categoria'] == 'ambiente' for x in res), 'el filtro debe traer solo ambiente'
    # los No Conformes históricos son ambientales
    assert any(x['estado'] == 'fuera_industria' for x in res), 'los NC ambientales deben estar'


def test_heatmap_excluye_ambiente(admin_client):
    r = admin_client.get('/api/calidad/micro/heatmap?meses=24')
    assert r.status_code == 200
    prods = r.get_json().get('productos', [])
    # ninguna muestra ambiental (superficie/uniforme/bidón) debe aparecer como "producto"
    for p in prods:
        u = (p or '').upper()
        assert not any(k in u for k in ('SUPERFICIE', 'UNIFORME', 'BIDON', 'AMBIENTE', 'MANIPULAD')), \
            f'el heatmap de producto no debe incluir ambiente · {p}'
