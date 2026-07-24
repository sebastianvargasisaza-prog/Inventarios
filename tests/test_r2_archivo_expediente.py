"""Fase 2b · archivo inmutable del expediente en R2 (Sebastián 24-jul · INVIMA zero-paper).

Cubre lo verificable sin credenciales R2: la migración 372, el render interno de un documento vía
test_client con sesión de servicio, el estado archivados/pendientes, el no-op cuando R2 no está
configurado, y la key inmutable determinista por id. El PUT real a R2 se prueba en prod (self-test)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))


def _cols(conn, tabla):
    try:
        return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % tabla).fetchall()}
    except Exception:
        return set()


def test_mig372_columnas_r2(app):
    """mig 372 agregó r2_key/r2_at/r2_sha256/r2_bytes a documentos_regulados."""
    with app.app_context():
        from database import get_db
        cols = _cols(get_db(), 'documentos_regulados')
    for c in ('r2_key', 'r2_at', 'r2_sha256', 'r2_bytes'):
        assert c in cols, 'falta columna %s (mig 372)' % c


def test_key_inmutable_por_id():
    import r2_storage as r
    d1 = {'id': 10, 'entidad': 'MP', 'codigo': 'MP00123', 'lote': 'LOT-1', 'tipo_doc': 'F02'}
    d2 = dict(d1, id=11)  # re-registro → id nuevo
    k1 = r._r2_key_documento(d1, 'abc123def456', 'html')
    k2 = r._r2_key_documento(d2, 'abc123def456', 'html')
    assert k1 != k2, 'cada versión (id distinto) debe tener su propia key (WORM)'
    assert k1.startswith('expediente/MP/LOT-1/F02/10-'), k1
    # determinista: misma entrada → misma key
    assert k1 == r._r2_key_documento(d1, 'abc123def456', 'html')


def test_estado_y_noop_sin_r2(app, monkeypatch):
    """r2_stats_expediente cuenta; archivar_pendientes_r2 es no-op limpio sin credenciales."""
    import r2_storage as r
    monkeypatch.delenv('R2_ENDPOINT', raising=False)
    monkeypatch.delenv('R2_BUCKET', raising=False)
    monkeypatch.delenv('R2_ACCESS_KEY', raising=False)
    monkeypatch.delenv('R2_SECRET_KEY', raising=False)
    assert r.r2_configurado() is False
    res = r.archivar_pendientes_r2(app, limite=5)
    assert res.get('ok') is False and 'no configurado' in (res.get('error') or '').lower()
    with app.app_context():
        from database import get_db
        st = r.r2_stats_expediente(get_db())
    assert 'archivados' in st and 'pendientes' in st and st['configurado'] is False


def test_render_doc_via_test_client(app):
    """El archivador renderiza un imprimible interno con sesión de servicio (auth OK, 200, bytes)."""
    import r2_storage as r
    # el F01 imprimible responde 200 (con HTML de 'no hay F01') aun sin fila → prueba auth+render
    data, ct = r._render_doc_bytes(app, '/api/calidad/recepcion-tecnica/imprimible?mov_id=999999&origen=MP')
    assert data is not None, 'no renderizó (motivo: %s)' % ct
    assert b'<' in data  # HTML
    assert 'html' in (ct or '').lower()


def test_disco_preflight(admin_client):
    """El preflight de quitar-disco responde el checklist go/no-go sin tocar nada (read-only)."""
    r = admin_client.get('/admin/disco-preflight')
    assert r.status_code == 200 and b'cortex.css' in r.data
    j = admin_client.get('/api/admin/disco-preflight')
    assert j.status_code == 200
    d = j.get_json()
    for k in ('backend_es_postgres', 'r2_conectado', 'coa_todos_en_r2', 'backups_offsite'):
        assert k in d['checklist']
    assert 'listo_para_quitar_disco' in d and 'disco' in d


def test_endpoint_estado_get(logged_client):
    """GET /api/calidad/archivar-r2 devuelve estado sin requerir R2 (para pintar la página)."""
    r = logged_client.get('/api/calidad/archivar-r2')
    # calidad gate: valentina puede no ser calidad → 403 aceptable; si pasa, trae estado
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        j = r.get_json()
        assert j.get('ok') and 'estado' in j
