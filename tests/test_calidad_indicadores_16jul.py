"""Calidad · Indicadores: dejar solo Liberación + Micro y agregar 3 nuevos (Sebastián 16-jul).

Mig 356: desactiva NC/CAPA/OOS/agua/calibraciones; agrega MP en cuarentena, tiempo de
liberación, liberaciones por día. El endpoint calcula el valor de los 3 nuevos.
"""


def test_indicadores_nuevos_presentes_y_viejos_ocultos(admin_client):
    d = admin_client.get('/api/calidad/indicadores').get_json()
    assert d and 'indicadores' in d, d
    cods = {i['codigo'] for i in d['indicadores']}
    # los 3 nuevos
    for nuevo in ('mp_cuarentena', 'tiempo_liberacion', 'liberacion_dia'):
        assert nuevo in cods, f'falta el KPI nuevo {nuevo} · {sorted(cods)}'
    # los que quedan (Liberación + Micro)
    for keep in ('rft_mp', 'tasa_rechazo_mp', 'liberacion_pt', 'micro_ok'):
        assert keep in cods, f'debe seguir {keep}'
    # los desactivados
    for gone in ('nc_abiertas', 'nc_cierre_dias', 'capa_vencidas', 'capa_a_tiempo',
                 'oos_abiertos', 'agua_conforme', 'calibraciones_vigentes'):
        assert gone not in cods, f'{gone} debe estar oculto (activo=0)'


def test_mp_cuarentena_tiene_valor_numerico(admin_client):
    d = admin_client.get('/api/calidad/indicadores').get_json()
    it = next((i for i in d['indicadores'] if i['codigo'] == 'mp_cuarentena'), None)
    assert it is not None
    # valor = conteo (int) · no None (siempre computable)
    assert isinstance(it['valor'], (int, float)), it
    assert it['unidad'] == 'lotes'
