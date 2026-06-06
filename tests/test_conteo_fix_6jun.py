"""Incidente 6-jun-2026 · conteo cíclico "lo de ayer no sale hoy".

Causa raíz: /api/conteo/<id>/items devolvía un array plano pero el frontend al
RETOMAR un conteo leía d2.items (undefined) → las casillas de stock físico salían
en blanco (datos intactos en BD). Fix: el endpoint devuelve {items:[...]} y el
frontend tolera ambas formas.

Riesgo secundario: conteo_items sin UNIQUE + INSERT OR REPLACE → en PG duplicaba
filas (doble ajuste al cerrar). Fix: mig 221 UNIQUE(conteo_id,codigo_mp,lote).
"""
import os
import sqlite3


def _conn():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)


def test_items_endpoint_devuelve_objeto_items(admin_client):
    """El contrato es {items:[...]} (lo que espera el frontend al retomar)."""
    c = _conn()
    c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) "
              "VALUES ('CF-CONTRATO',datetime('now','-5 hours'),'Abierto','luis','EST-C','Ciclico')")
    cid = c.execute("SELECT id FROM conteos_fisicos WHERE numero='CF-CONTRATO'").fetchone()[0]
    c.execute("INSERT INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,lote) "
              "VALUES (?,'MP-CT','Mat',100,80,-20,'L1')", (cid,))
    c.commit(); c.close()
    r = admin_client.get(f'/api/conteo/{cid}/items')
    assert r.status_code == 200
    j = r.get_json()
    assert isinstance(j, dict) and 'items' in j, f'debe ser {{items:[...]}} · {type(j)}'
    assert any(it['codigo_mp'] == 'MP-CT' and it['stock_fisico'] == 80 for it in j['items'])


def test_conteo_items_unique_no_duplica(admin_client):
    """mig 221: UNIQUE(conteo_id,codigo_mp,lote) → INSERT OR REPLACE reemplaza,
    no duplica (evita doble ajuste al kardex al cerrar)."""
    c = _conn()
    idx = c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uq_conteo_items'").fetchone()
    assert idx, 'mig 221 debe crear uq_conteo_items'
    c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria) "
              "VALUES ('CF-UQ2',datetime('now'),'Abierto','luis','E')")
    cid = c.execute("SELECT id FROM conteos_fisicos WHERE numero='CF-UQ2'").fetchone()[0]
    for sf in (40, 42, 45):
        c.execute("INSERT OR REPLACE INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,lote) "
                  "VALUES (?,'MP-Q','Q',50,?,?-50,'LQ')", (cid, sf, sf))
    c.commit()
    n = c.execute("SELECT COUNT(*) FROM conteo_items WHERE conteo_id=? AND codigo_mp='MP-Q' AND lote='LQ'", (cid,)).fetchone()[0]
    val = c.execute("SELECT stock_fisico FROM conteo_items WHERE conteo_id=? AND codigo_mp='MP-Q'", (cid,)).fetchone()[0]
    c.close()
    assert n == 1, f'UNIQUE debe evitar duplicados · {n} filas'
    assert val == 45, 'el último guardado debe ganar'


def test_rescate_page_muestra_conteos(admin_client):
    """La herramienta de rescate muestra conteos+items recientes sin filtro."""
    c = _conn()
    c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) "
              "VALUES ('CF-RESC',datetime('now','-5 hours'),'Abierto','luis','EST-R','Ciclico')")
    cid = c.execute("SELECT id FROM conteos_fisicos WHERE numero='CF-RESC'").fetchone()[0]
    c.execute("INSERT INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,lote) "
              "VALUES (?,'MP-RR','Material RR',100,90,-10,'L1')", (cid,))
    c.commit(); c.close()
    r = admin_client.get('/admin/conteo-rescate?dias=3')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'CF-RESC' in body and 'MP-RR' in body and 'Material RR' in body
