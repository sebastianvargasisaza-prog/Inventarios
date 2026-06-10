"""Auditoría exhaustiva de Bodega MP · concordancia de INCI · 10-jun-2026.

Consolida en una pasada: INCI prestado de otro material (caso glucosamina/péptido),
INCI compartido, nombre comercial duplicado, INCI vacío, abreviatura en INCI.
Read-only · solo Admin.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_auditoria_bodega_mp_detecta_incis_mal(app, db_clean):
    c = _login(app, "sebastian")
    # Péptido real + glucosamina con el INCI PRESTADO del péptido (tu bug).
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, controla_stock) "
          "VALUES ('ZZP-PEP','Acetyl Tetrapeptide-5','Acetyl Tetrapeptide-5',1,1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, controla_stock) "
          "VALUES ('ZZP-GLU1','N-Acetyl Glucosamina','Acetyl Tetrapeptide-5',1,1)")
    # Dos 'Glucosamina' (mismo comercial) → comercial duplicado.
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, controla_stock) "
          "VALUES ('ZZP-GLU2','Glucosamina ZZ','Glucosamine',1,1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, controla_stock) "
          "VALUES ('ZZP-GLU3','Glucosamina ZZ','Glucosamine HCl',1,1)")
    # INCI vacío en un material que controla stock.
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, controla_stock) "
          "VALUES ('ZZP-VAC','Material Raro ZZ','',1,1)")

    r = c.get("/api/admin/auditoria-bodega-mp")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"]
    by_code = {}
    for h in d["hallazgos"]:
        by_code.setdefault(h["codigo_mp"], set()).add(h["categoria"])
    # El glucosamina con INCI de péptido → inci_es_otro_material.
    assert "inci_es_otro_material" in by_code.get("ZZP-GLU1", set()), by_code.get("ZZP-GLU1")
    # Los dos 'Glucosamina ZZ' → comercial_duplicado (ambos).
    assert "comercial_duplicado" in by_code.get("ZZP-GLU2", set()), by_code.get("ZZP-GLU2")
    assert "comercial_duplicado" in by_code.get("ZZP-GLU3", set()), by_code.get("ZZP-GLU3")
    # El material sin INCI → inci_vacio.
    assert "inci_vacio" in by_code.get("ZZP-VAC", set()), by_code.get("ZZP-VAC")
    # La página HTML carga.
    p = c.get("/admin/auditoria-bodega-mp")
    assert p.status_code == 200 and b"Auditor" in p.data
