"""14-jun · Cuadro de mando de indicadores de calidad (Fase 1).

GET /api/calidad/indicadores devuelve el set estándar con meta + valor + semáforo
+ serie 6m; PATCH la meta lo edita (solo Calidad/Admin · valentina no es Calidad).
"""
from .conftest import csrf_headers

# Mig 356 (16-jul): el tablero quedó en Liberación + Micro + 3 nuevos. Los de
# NC/CAPA/OOS/agua/calibraciones se desactivaron (activo=0) → ya no salen.
_ESPERADOS = {
    'rft_mp', 'tasa_rechazo_mp', 'liberacion_pt', 'micro_ok',
    'mp_cuarentena', 'tiempo_liberacion', 'liberacion_dia',
}
_DESACTIVADOS = {
    'nc_abiertas', 'nc_cierre_dias', 'capa_vencidas', 'capa_a_tiempo',
    'oos_abiertos', 'agua_conforme', 'calibraciones_vigentes',
}


def test_indicadores_set_completo(admin_client):
    r = admin_client.get('/api/calidad/indicadores')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    cods = {i['codigo'] for i in d['indicadores']}
    assert _ESPERADOS <= cods, f'faltan indicadores: {_ESPERADOS - cods}'
    assert not (_DESACTIVADOS & cods), f'no deben salir los desactivados: {_DESACTIVADOS & cods}'
    # cada indicador trae semáforo válido
    for i in d['indicadores']:
        assert i['semaforo'] in ('verde', 'amarillo', 'rojo', 'gris'), i
    # los de tasa traen serie de 6 meses
    rft = next(i for i in d['indicadores'] if i['codigo'] == 'rft_mp')
    assert len(rft['serie']) == 6, rft['serie']
    assert 'resumen' in d and 'mes_actual' in d


def test_editar_meta_kpi(admin_client):
    r = admin_client.patch('/api/calidad/indicadores/metas/rft_mp',
                           json={'meta': 97, 'umbral_amarillo': 92}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    d = admin_client.get('/api/calidad/indicadores').get_json()
    rft = next(i for i in d['indicadores'] if i['codigo'] == 'rft_mp')
    assert rft['meta'] == 97 and rft['umbral_amarillo'] == 92


def test_editar_meta_inexistente_404(admin_client):
    r = admin_client.patch('/api/calidad/indicadores/metas/no_existe',
                           json={'meta': 1}, headers=csrf_headers())
    assert r.status_code == 404


def test_editar_meta_requiere_rol_calidad(logged_client):
    # valentina NO está en CALIDAD_USERS → no puede mutar metas
    r = logged_client.patch('/api/calidad/indicadores/metas/rft_mp',
                            json={'meta': 50}, headers=csrf_headers())
    assert r.status_code in (401, 403), r.data[:200]
