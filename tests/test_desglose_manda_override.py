"""Sebastián 2-jul · "el Desglose editable manda": al guardar los kg de un lote con
desglose_uds:{sku:uds}, el backend persiste las uds por presentación en
produccion_programada.fija_override_json (mapeando SKU→presentacion_codigo). Así la
Composición de envases / Abastecimiento usan EXACTAMENTE lo que se decide producir.
"""
import os
import sqlite3
import json

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_desglose_uds_escribe_fija_override_json(app, db_clean):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,lote_size_kg,activo) "
                     "VALUES ('PROD DESG',30,1)")
        conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre='PROD DESG'")
        # 2 presentaciones con su SKU real + presentacion_codigo
        conn.execute("INSERT INTO producto_presentaciones (producto_nombre,categoria,presentacion_codigo,"
                     "etiqueta,volumen_ml,envase_codigo,sku_shopify,es_default,activo) "
                     "VALUES ('PROD DESG','','P30','30ml',30,'FR-30','SKU-30',1,1)")
        conn.execute("INSERT INTO producto_presentaciones (producto_nombre,categoria,presentacion_codigo,"
                     "etiqueta,volumen_ml,envase_codigo,sku_shopify,es_default,activo) "
                     "VALUES ('PROD DESG','','P15','15ml',15,'FR-15','SKU-15',0,1)")
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                     "VALUES ('PROD DESG','2026-08-15','pendiente','eos_plan',20,1)")
        conn.commit()
        pid = conn.execute("SELECT id FROM produccion_programada WHERE producto='PROD DESG'").fetchone()[0]
    finally:
        conn.close()

    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid,
               json={'cantidad_kg': 28, 'desglose_uds': {'SKU-30': 931, 'SKU-15': 4}},
               headers=csrf_headers())
    assert r.status_code == 200, f"{r.status_code} {r.data[:300]}"
    assert (r.get_json() or {}).get('override_presentaciones') == 2

    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        raw = conn.execute("SELECT fija_override_json FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
    finally:
        conn.close()
    ovr = json.loads(raw)
    # keyed by presentacion_codigo (lo que lee _composicion_envases_lote), no por SKU
    assert ovr.get('P30') == 931, ovr
    assert ovr.get('P15') == 4, ovr


def test_meses_cobertura_persiste(app, db_clean):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD MC',30,1)")
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                     "VALUES ('PROD MC','2026-08-15','pendiente','eos_plan',20,1)")
        conn.commit()
        pid = conn.execute("SELECT id FROM produccion_programada WHERE producto='PROD MC'").fetchone()[0]
    finally:
        conn.close()
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'cantidad_kg': 25, 'meses_cobertura': 3},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        mc = conn.execute("SELECT meses_cobertura FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
    finally:
        conn.close()
    assert mc == 3, mc
