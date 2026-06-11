"""Factibilidad debe mostrar la REALIDAD, no producciones antiguas (Sebastián 11-jun).

Antes incluía TODA producción pasada pendiente sin tope → lotes de hace meses (zombies)
ensuciaban la vista. Ahora solo atrasadas recientes (default 30d).
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


def test_factibilidad_excluye_producciones_antiguas(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-FACTZZ','Fact ZZ','FACT INCI ZZ',1)")
    for prod in ('ZZ-FACT-RECIENTE', 'ZZ-FACT-ANTIGUO'):
        _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
        _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
              "VALUES (?,'MP-FACTZZ','Fact ZZ',10,0)", (prod,))
    # Atrasada RECIENTE (5 días) pendiente → debe contar · ANTIGUA (90 días) → zombie, fuera
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-FACT-RECIENTE', date('now','-5 hours','-5 days'),1,'pendiente',10,'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-FACT-ANTIGUO', date('now','-5 hours','-90 days'),1,'pendiente',10,'eos_plan')")

    c = _login(app)
    r = c.get("/api/plan/factibilidad?dias=30")
    assert r.status_code == 200, r.data
    txt = r.get_data(as_text=True)
    assert "ZZ-FACT-RECIENTE" in txt, "la atrasada reciente (5d) debe aparecer en factibilidad"
    assert "ZZ-FACT-ANTIGUO" not in txt, "la antigua (90d) NO debe aparecer (zombie)"
