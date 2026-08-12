# -*- coding: utf-8 -*-
"""Exportación anual del expediente · tarea B-08 del ASG-PRO-014.

Lo que se protege: que el expediente se pueda LEER dentro de diez años, con un navegador y nada
más. El archivo inmutable ya conserva los documentos, pero saber cuáles componen el expediente de
un lote sale de la base de datos: sin índice, perder el sistema deja miles de archivos sin forma
de saber cuál es de quién ni si están todos.

Y el índice tiene que enumerar lo que FALTA. Uno que sólo liste lo que salió bien haría creer que
el expediente está completo justo cuando le falta lo que no se pudo archivar (M100).
"""
import pytest

TEST_PASSWORD = "TestPass123"


def _sembrar(app, anio, lote, con_archivo=True, n=1):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM documentos_regulados WHERE lote=?", (lote,))
        for i in range(n):
            c.execute(
                "INSERT INTO documentos_regulados (entidad, codigo, producto_nombre, lote, "
                "tipo_doc, formato, titulo, url, generado_por, generado_at, r2_key, anulado) "
                "VALUES ('PT','','CREMA EXPORT',?,?,?,?,'/x','laura',?,?,0)",
                (lote, 'F01', 'COC-PRO-002-F01', 'Recepcion tecnica %d' % i,
                 '%d-03-15T10:0%d:00Z' % (anio, i),
                 ('expediente/PT/%s/F01/%d-abc.html' % (lote, i)) if con_archivo else ''))
        conn.commit()


def test_el_indice_lista_los_documentos_del_ano(app):
    from exportar_expediente import construir
    _sembrar(app, 2026, 'LOTE-EXP-A', n=2)
    with app.app_context():
        from database import get_db
        doc, csvtxt, resumen = construir(get_db(), 2026)
    assert 'LOTE-EXP-A' in doc
    assert 'Recepcion tecnica 0' in doc
    assert resumen['documentos'] >= 2
    assert 'LOTE-EXP-A' in csvtxt


def test_el_indice_DECLARA_lo_que_nunca_se_archivo(app):
    """DIENTES · un documento sin copia en el archivo tiene que salir marcado, no omitido.

    Omitirlo produciría un índice que se lee como completo justo cuando le falta lo único que
    importaba señalar.
    """
    from exportar_expediente import construir
    _sembrar(app, 2026, 'LOTE-EXP-SIN', con_archivo=False, n=1)
    with app.app_context():
        from database import get_db
        doc, csvtxt, resumen = construir(get_db(), 2026)
    assert resumen['sin_archivar'] >= 1
    assert 'NO ARCHIVADO' in doc
    assert 'NO ARCHIVADO' in csvtxt
    assert 'falta' in doc, 'la fila tiene que quedar resaltada, no perdida entre las demás'


def test_el_indice_se_abre_sin_el_sistema(app):
    """No puede depender de EOS: ni hojas de estilo externas, ni llamadas al servidor.

    Un expediente que sólo se ve con la aplicación corriendo no cumple una conservación que se
    cuenta en años y supera la vida de cualquier programa.
    """
    from exportar_expediente import construir
    _sembrar(app, 2026, 'LOTE-EXP-B')
    with app.app_context():
        from database import get_db
        doc, _c, _r = construir(get_db(), 2026)
    assert '<style>' in doc, 'los estilos van embebidos'
    assert 'cortex.css' not in doc
    assert '<link' not in doc, 'no puede pedirle nada a un servidor'
    assert '<script' not in doc, 'no puede depender de que corra JavaScript'
    assert doc.strip().startswith('<!doctype html>')


def test_el_indice_trae_la_ruta_exacta_del_archivo(app):
    """Sin la ruta, el índice dice que el documento existe pero no dónde · y eso no sirve."""
    from exportar_expediente import construir
    _sembrar(app, 2026, 'LOTE-EXP-C')
    with app.app_context():
        from database import get_db
        doc, csvtxt, _r = construir(get_db(), 2026)
    assert 'expediente/PT/LOTE-EXP-C/F01/0-abc.html' in doc
    assert 'expediente/PT/LOTE-EXP-C/F01/0-abc.html' in csvtxt


def test_no_mezcla_anos(app):
    from exportar_expediente import construir
    _sembrar(app, 2025, 'LOTE-EXP-2025')
    _sembrar(app, 2026, 'LOTE-EXP-2026')
    with app.app_context():
        from database import get_db
        doc26, _c, _r = construir(get_db(), 2026)
    assert 'LOTE-EXP-2026' in doc26
    assert 'LOTE-EXP-2025' not in doc26


def test_los_anulados_no_entran(app):
    """Un documento anulado se conserva en la base, pero no compone el expediente vigente."""
    from exportar_expediente import construir
    _sembrar(app, 2026, 'LOTE-EXP-ANU')
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("UPDATE documentos_regulados SET anulado=1 WHERE lote=?",
                              ('LOTE-EXP-ANU',))
        conn.commit()
        doc, _c, _r = construir(conn, 2026)
    assert 'LOTE-EXP-ANU' not in doc


def test_previsualizar_no_escribe_nada(app, admin_client, monkeypatch):
    """El GET es una lectura · se puede mirar antes de archivar (M113: un GET no muta)."""
    import r2_storage
    escrituras = []
    monkeypatch.setattr(r2_storage, 'r2_put',
                        lambda k, d, content_type=None: escrituras.append(k) or True)
    _sembrar(app, 2026, 'LOTE-EXP-PREV')
    r = admin_client.get('/api/admin/exportar-expediente?anio=2026')
    assert r.status_code == 200
    assert r.get_json()['documentos'] >= 1
    assert escrituras == [], 'la previsualización escribió en el archivo'


def test_el_endpoint_es_solo_de_admin(logged_client):
    assert logged_client.get('/api/admin/exportar-expediente').status_code in (401, 403)
    assert logged_client.post('/api/admin/exportar-expediente', json={}).status_code in (401, 403)


def test_ano_invalido_se_rechaza(admin_client):
    r = admin_client.post('/api/admin/exportar-expediente', json={'anio': 'el año pasado'})
    assert r.status_code == 400


def test_el_cron_anual_existe_y_apunta_a_algo_real(app):
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    import blueprints.auto_plan_jobs as J
    fila = [j for j in JOBS_SCHEDULE if j[0] == 'exportar_expediente']
    assert fila, 'el índice del expediente no está en el cron'
    assert hasattr(J, fila[0][5]), 'el cron apunta a una función que no existe'
