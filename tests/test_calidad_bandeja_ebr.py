"""14-jun · Fase 4 · consolidar liberación de PT (EBR) en la bandeja de Calidad.

La bandeja QC ahora trae la sección ebr_por_liberar: legajos EBR completados / en
revisión QC esperando decisión, con enlace al legajo. Antes vivía sólo en /brd.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_bandeja_surface_ebr_por_liberar(admin_client):
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('PROD-BANDEJA-T1', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, iniciado_por, iniciado_at_utc, completado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'LOTE-BANDEJA-T1', 'completado', 'sebastian', datetime('now','utc'), datetime('now','utc'), 1000)", (mbr_id,))
    try:
        r = admin_client.get('/api/calidad/bandeja')
        assert r.status_code == 200, r.data[:200]
        d = r.get_json()
        sec = d['secciones'].get('ebr_por_liberar')
        assert sec is not None, 'falta la sección ebr_por_liberar'
        mine = next((x for x in sec['items'] if x['ebr_id'] == ebr_id), None)
        assert mine, 'el EBR completado debe aparecer en ebr_por_liberar'
        assert mine['producto'] == 'PROD-BANDEJA-T1'
        assert mine['lote'] == 'LOTE-BANDEJA-T1'
        assert mine['link'] == f'/brd/timeline/{ebr_id}'
        assert d['kpis'].get('ebr_por_liberar', 0) >= 1
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
        conn.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (ebr_id,))
        conn.execute("DELETE FROM mbr_templates WHERE id=?", (mbr_id,))
        conn.commit(); conn.close()
