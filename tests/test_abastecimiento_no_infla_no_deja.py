"""Re-revisión de abastecimiento (Sebastián 18-jun): que NO infle ni deje nada.

Escenario controlado con cantidades conocidas → prueba exacta de:
  - prefer-Fijo: 3 capas solapadas (eos_plan + auto_plan + eos_proyeccion) del MISMO
    producto NO se suman → demanda = SOLO el Fijo (no 3×) · NO INFLA.
  - completitud: TODOS los MP de la fórmula aparecen + el envase de presentaciones · NO DEJA NADA.
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


def test_abastecimiento_no_infla_ni_deja_nada(app, db_clean):
    prod = "ZZ NIDN PROD"
    mpA, mpB = "MP-NIDN-A", "MP-NIDN-B"
    envase = "ENV-NIDN-30ML"
    # Fórmula: 2 MP (A 10%, B 5%)
    for cod, pct in ((mpA, 10), (mpB, 5)):
        _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
              "VALUES (?,?,?,1)", (cod, "Mat " + cod, "INCI " + cod.replace("-", "")))
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo,volumen_unitario_ml) VALUES (?,1,1,30)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) VALUES (?,?,?,10,0)", (prod, mpA, "Mat A"))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) VALUES (?,?,?,5,0)", (prod, mpB, "Mat B"))
    # Envase (presentaciones · fuente unificada)
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) VALUES (?,?,?,0,0)", (envase, "Frasco NIDN", "Envase"))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,es_default,ventas_mes_referencia,activo) "
          "VALUES (?,'NIDN-30','30 ml',30,?,1,100,1)", (prod, envase))
    # 3 CAPAS SOLAPADAS del MISMO producto · 2 kg c/u · prefer-Fijo debe contar SOLO la Fija.
    for org, off in (("eos_plan", 5), ("auto_plan", 6), ("eos_proyeccion", 7)):
        _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
              "VALUES (?, date('now','-5 hours','+' || ? || ' days'),1,'pendiente',2,?)", (prod, off, org))
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee").get_json()
    hmax = str(max(j["horizontes"]))
    mps = {(m.get("codigo") or "").upper(): m for m in (j.get("mps") or [])}
    mees = {(m.get("codigo") or "").upper(): m for m in (j.get("mees") or [])}

    # NO INFLA · MP-A = 10% × 2kg × 1000 = 200g (SOLO la Fija · no 3×600)
    itA = mps.get(mpA.upper())
    assert itA is not None, "MP-A debe aparecer (no dejar nada por fuera)"
    consA = float(itA["consumo"][hmax])
    assert 195 <= consA <= 205, f"MP-A debe ser ~200g (solo la capa Fija · prefer-Fijo) · got {consA} (inflado si ~600)"
    # NO DEJA NADA · MP-B presente (~100g) + envase presente
    itB = mps.get(mpB.upper())
    assert itB is not None and 95 <= float(itB["consumo"][hmax]) <= 105, f"MP-B ~100g · got {itB}"
    itE = mees.get(envase.upper())
    assert itE is not None, "el envase debe aparecer (no dejar envases por fuera)"
    # envase: 2kg×1000/30ml ≈ 67 unidades (1 lote Fijo)
    consE = float(itE["consumo"][hmax])
    assert 60 <= consE <= 75, f"envase ~67 u (1 lote de 2kg/30ml) · got {consE}"
