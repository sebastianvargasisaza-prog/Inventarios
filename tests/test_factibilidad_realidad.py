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


def test_factibilidad_forward_only_desde_hoy(app, db_clean):
    """Por defecto factibilidad muestra desde HOY hacia adelante · NO arrastra el pasado
    (lotes viejos del mes anterior = zombies)."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-FACTZZ','Fact ZZ','FACT INCI ZZ',1)")
    for prod in ('ZZ-FACT-FUTURA', 'ZZ-FACT-PASADA'):
        _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
        _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
              "VALUES (?,'MP-FACTZZ','Fact ZZ',10,0)", (prod,))
    # Futura (+5 días) → debe aparecer · Pasada (-25 días, mes anterior) → fuera por defecto
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-FACT-FUTURA', date('now','-5 hours','+5 days'),1,'pendiente',10,'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-FACT-PASADA', date('now','-5 hours','-25 days'),1,'pendiente',10,'eos_plan')")

    c = _login(app)
    r = c.get("/api/plan/factibilidad?dias=30")
    assert r.status_code == 200, r.data
    txt = r.get_data(as_text=True)
    assert "ZZ-FACT-FUTURA" in txt, "la producción futura (desde hoy) debe aparecer"
    assert "ZZ-FACT-PASADA" not in txt, "una producción del mes anterior NO debe aparecer (forward-only)"

    # Con ?incluir_atrasadas=1 sí entra el backlog reciente (acotado), pero no el viejo
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-FACT-AYER', date('now','-5 hours','-2 days'),1,'pendiente',10,'eos_plan')")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('ZZ-FACT-AYER',1,1)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES ('ZZ-FACT-AYER','MP-FACTZZ','Fact ZZ',10,0)")
    r2 = c.get("/api/plan/factibilidad?dias=30&incluir_atrasadas=1")
    t2 = r2.get_data(as_text=True)
    assert "ZZ-FACT-AYER" in t2, "con incluir_atrasadas=1, el backlog reciente (2d) debe aparecer"
    assert "ZZ-FACT-PASADA" not in t2, "aun con atrasadas, el de 25d (>7d tope) no debe aparecer"


def test_factibilidad_horizonte_acumulativo_bloquea_el_segundo(app, db_clean):
    """Lógica de horizonte: si 2 producciones comparten una MP y el stock alcanza para
    UNA sola, la primera sale factible y la SEGUNDA bloqueada (consumo acumulado)."""
    # MP con stock para UN solo lote (1000 g)
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-LIMZZ','Limitada ZZ','LIM INCI ZZ',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) "
          "VALUES ('MP-LIMZZ','Limitada ZZ','Entrada',1000,'LT-LIMZZ', date('now','-5 hours'))")
    # Producto cuya fórmula pide 10% → 1 lote de 10 kg = 1000 g de MP-LIMZZ
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('ZZ-LIM',10,1)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES ('ZZ-LIM','MP-LIMZZ','Limitada ZZ',10,0)")
    # 2 producciones futuras de 10 kg c/u (necesitan 1000 g c/u · total 2000 > 1000 stock)
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-LIM', date('now','-5 hours','+2 days'),1,'pendiente',10,'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES ('ZZ-LIM', date('now','-5 hours','+4 days'),1,'pendiente',10,'eos_plan')")

    c = _login(app)
    d = c.get("/api/plan/factibilidad?dias=30").get_json()
    lim = [p for p in d.get("producciones", []) if p.get("producto") == "ZZ-LIM"]
    assert len(lim) == 2, lim
    factibles = [p for p in lim if p["factible"] is True]
    bloqueadas = [p for p in lim if p["factible"] is False]
    assert len(factibles) == 1 and len(bloqueadas) == 1, f"1 factible + 1 bloqueada · {lim}"
    # La bloqueada es la segunda (más tarde) y le falta ~1000 g
    assert bloqueadas[0]["mps_faltantes"], "la bloqueada debe reportar la MP faltante"
    assert abs(bloqueadas[0]["mps_faltantes"][0]["faltante_g"] - 1000) < 1, bloqueadas[0]["mps_faltantes"]
