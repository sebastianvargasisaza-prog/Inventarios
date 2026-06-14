"""14-jun · Herramienta de importación de COA (.eml) · Opción B.

Testea la lógica de upsert (DB pura, sin pdfplumber) y el endpoint/serve (auth + seguridad).
El parseo de PDF (pdfplumber) se prueba aparte; acá validamos lo crítico sin esa dependencia.
"""
import os
import sqlite3

from .conftest import csrf_headers


def _conn():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)


def test_upsert_sample_micro_idempotente(app):
    import sys
    sys.path.insert(0, 'api')
    from coa_import import upsert_sample
    sample = {
        'tipo': 'micro', 'ref': 'TEST-COA-1', 'lote': 'L-COA-X',
        'muestra': 'GEL HIDRATANTE', 'fecha': '2026-05-01',
        'analisis': [
            {'analisis': 'Recuento Total de aerobios mesofilos', 'resultado': '< 10 (UFC/g)', 'concepto': 'C'},
            {'analisis': 'Escherichia coli', 'resultado': 'Ausencia', 'concepto': 'C'},
        ],
    }
    conn = _conn()
    try:
        r1 = upsert_sample(conn, sample, '/api/calidad/micro/coa/TEST-COA-1.pdf', usuario='t')
        conn.commit()
        assert r1['nuevos'] == 2 and r1['actualizados'] == 0, r1
        # re-importar el mismo informe NO duplica · actualiza el COA
        r2 = upsert_sample(conn, sample, '/api/calidad/micro/coa/TEST-COA-1.pdf', usuario='t')
        conn.commit()
        assert r2['nuevos'] == 0 and r2['actualizados'] == 2, r2
        n = conn.execute("SELECT COUNT(*), MAX(archivo_coa_url) FROM calidad_micro_resultados WHERE n_referencia='TEST-COA-1'").fetchone()
        assert n[0] == 2 and n[1].endswith('TEST-COA-1.pdf')
    finally:
        conn.execute("DELETE FROM calidad_micro_resultados WHERE n_referencia='TEST-COA-1'"); conn.commit(); conn.close()


def test_upsert_sample_fq(app):
    import sys
    sys.path.insert(0, 'api')
    from coa_import import upsert_sample
    sample = {'tipo': 'fq', 'ref': 'TEST-FQ-1', 'lote': 'L-FQ', 'muestra': 'SUERO X',
              'fecha': '2026-05-02', 'analisis': [{'param': 'pH', 'metodo': 'USP', 'resultado': '5.8'}]}
    conn = _conn()
    try:
        r = upsert_sample(conn, sample, '/api/calidad/micro/coa/TEST-FQ-1.pdf', usuario='t')
        conn.commit()
        assert r['nuevos'] == 1
        row = conn.execute("SELECT parametro, archivo_coa_url FROM calidad_fisicoquimica_resultados WHERE n_referencia='TEST-FQ-1'").fetchone()
        assert row and row[0] == 'pH'
    finally:
        conn.execute("DELETE FROM calidad_fisicoquimica_resultados WHERE n_referencia='TEST-FQ-1'"); conn.commit(); conn.close()


def test_importar_eml_requiere_rol_y_archivo(admin_client, logged_client):
    # sin archivo → 400
    r = admin_client.post('/api/calidad/micro/importar-eml', headers=csrf_headers())
    assert r.status_code == 400, r.data[:200]
    # no-calidad (valentina) → 401/403
    r2 = logged_client.post('/api/calidad/micro/importar-eml', headers=csrf_headers())
    assert r2.status_code in (401, 403)


def test_servir_coa_seguridad(admin_client, logged_client):
    # path traversal / nombre inválido → 400
    r = admin_client.get('/api/calidad/micro/coa/..%2f..%2fsecret')
    assert r.status_code in (400, 404)
    # nombre válido pero inexistente → 404
    r2 = admin_client.get('/api/calidad/micro/coa/NOEXISTE-1.pdf')
    assert r2.status_code == 404
    # no-autorizado → 403
    r3 = logged_client.get('/api/calidad/micro/coa/NOEXISTE-1.pdf')
    assert r3.status_code in (401, 403)
