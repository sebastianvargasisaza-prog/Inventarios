"""14-jun · Biblioteca documental en Calidad (Fase 3).

La pestaña "Documentos" de /calidad consume el SGD existente (solo lectura). Verifica
que la página expone la pestaña y que el endpoint del SGD es accesible para Calidad.
"""


def test_calidad_page_tiene_pestana_documentos(admin_client):
    r = admin_client.get('/calidad')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'tab-doc' in body and 'loadDocumentos' in body, 'falta la pestaña Documentos'


def test_sgd_listado_accesible_para_calidad(admin_client):
    r = admin_client.get('/api/aseguramiento/sgd/listado')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert 'items' in d and 'resumen_por_area' in d
