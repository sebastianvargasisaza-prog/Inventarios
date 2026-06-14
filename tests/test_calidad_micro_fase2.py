"""14-jun · Micro brutal (Fase 2).

- POST /api/calidad/micro/resultados acepta archivo_coa_url + ebr_id y los devuelve en GET.
- COA debe ser URL http(s) (400 si no).
- GATE DURO: no se libera un EBR cuyo lote tiene un resultado micro fuera_industria sin
  OOS resuelto (codigo MICRO_OOS). Al resolverlo, ese gate ya no bloquea.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_micro_post_guarda_coa_y_ebr(admin_client):
    r = admin_client.post('/api/calidad/micro/resultados', json={
        'producto_nombre': 'PROD-COA', 'lote': 'L-COA-1', 'microorganismo': 'Mohos y levaduras',
        'valor': 5, 'fecha_analisis': '2026-06-14',
        'laboratorio': 'BioLab', 'archivo_coa_url': 'https://example.com/coa-1.pdf', 'ebr_id': 777,
    }, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    g = admin_client.get('/api/calidad/micro/resultados?lote=L-COA-1').get_json()
    row = next((x for x in g['resultados'] if x['lote'] == 'L-COA-1'), None)
    assert row, 'el resultado debe listarse'
    assert row['archivo_coa_url'] == 'https://example.com/coa-1.pdf'
    assert row['ebr_id'] == 777
    assert row['laboratorio'] == 'BioLab'


def test_micro_coa_url_invalida_400(admin_client):
    r = admin_client.post('/api/calidad/micro/resultados', json={
        'producto_nombre': 'PROD-COA', 'lote': 'L-COA-2', 'microorganismo': 'E. coli',
        'valor_texto': 'ausencia', 'archivo_coa_url': 'ftp://malo/coa.pdf',
    }, headers=csrf_headers())
    assert r.status_code == 400, r.data[:200]


def test_micro_gate_bloquea_liberacion(app, db_clean):
    cs = _login(app, 'sebastian')
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('PROD-MICRO-T1', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'LOTE-MICRO-T1', 'completado', 'sebastian', datetime('now','utc'), 1000)", (mbr_id,))
    # micro fuera de spec de industria, sin OOS resuelto (oos_id NULL)
    _exec("INSERT INTO calidad_micro_resultados (lote, producto_nombre, fecha_analisis, microorganismo, "
          "valor, unidad, estado, creado_por) VALUES ('LOTE-MICRO-T1','PROD-MICRO-T1','2026-06-14',"
          "'Mesófilos aerobios totales', 5000, 'UFC/g', 'fuera_industria', 'sebastian')")
    try:
        r = cs.post(f'/api/brd/ebr/{ebr_id}/liberar', json={'signature_id': 999999}, headers=csrf_headers())
        assert r.status_code == 409, r.data[:200]
        assert r.get_json().get('codigo') == 'MICRO_OOS', r.data[:200]
        # resolver el micro (estado ok) → el gate micro ya no debe bloquear
        _exec("UPDATE calidad_micro_resultados SET estado='ok' WHERE lote='LOTE-MICRO-T1'")
        r2 = cs.post(f'/api/brd/ebr/{ebr_id}/liberar', json={'signature_id': 999999}, headers=csrf_headers())
        assert not (r2.status_code == 409 and (r2.get_json() or {}).get('codigo') == 'MICRO_OOS'), \
            f'resuelto el micro, MICRO_OOS no debe bloquear · {r2.data[:200]}'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
        conn.execute("DELETE FROM calidad_micro_resultados WHERE lote='LOTE-MICRO-T1'")
        conn.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (ebr_id,))
        conn.execute("DELETE FROM mbr_templates WHERE id=?", (mbr_id,))
        conn.commit(); conn.close()
