"""Sebastián 11-jul · "asegurate que abastecimiento cuente CADA lote que puse en el calendario 2 años, en los
tiempos que son". Verificación EJECUTABLE del motor real (abastecimiento_consumo_horizontes):

  1. Cada lote del calendario aporta gramos = %×cantidad_kg×1000, usando el kg COMPLETO (incl. kg_otro_cliente),
     NO la porción Ánimus (si restara kg_otro compraría de menos).
  2. Cada lote cae en EXACTAMENTE los horizontes cuya ventana cubre su fecha (acumulativo 30⊂120⊂365⊂730).
  3. Un lote del 2º AÑO (día ~400) SOLO se cuenta si se pide horizonte 730 (con el default 365 queda fuera de la
     VENTANA de compra · by-design, pero debe entrar cuando se pide 730 → la pantalla necesita ofrecer 730).
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
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _consumo_map(app, codigo, horizontes):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=" + horizontes)
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return {int(k): float(v or 0) for k, v in (m.get("consumo") or {}).items()}
    return {}


def test_cada_lote_2anios_cuenta_en_su_horizonte_con_kg_completo(app, db_clean):
    prod, mp = "QA CADA LOTE 2Y", "MP-QACL2Y"
    # fórmula: 1 MP al 10%
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
          (mp, mp, mp + " INCI"))
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,?,0)", (prod, mp, mp, 10))

    # 3 lotes Fijos (eos_plan) de un calendario a 2 años · cada uno 70 kg TOTAL con 40 kg para otro cliente.
    # gramos esperados por lote = 10% × 70 kg × 1000 = 7000 g (kg COMPLETO · si restara kg_otro daría 3000).
    for dias in (10, 100, 400):
        _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg,"
              "kg_otro_cliente) VALUES (?, date('now','-5 hours','+' || ? || ' days'), 1, 'pendiente', 'eos_plan', 70, 40)",
              (prod, dias))

    # (A) con horizontes hasta 365: se cuentan el de día 10 y el de día 100; el de día 400 NO (fuera de ventana)
    m = _consumo_map(app, mp, "30,120,365")
    assert abs(m.get(30, 0) - 7000.0) < 1.0, ("h=30 solo el lote de día 10 · kg completo (7000g, no 3000)", m)
    assert abs(m.get(120, 0) - 14000.0) < 1.0, ("h=120 lotes día 10 + día 100 = 14000g", m)
    assert abs(m.get(365, 0) - 14000.0) < 1.0, ("h=365 sigue 14000g · el de día 400 NO entra con default", m)

    # (B) pidiendo horizonte 730 (2 años): entran los TRES → 21000 g. Prueba que el motor SÍ cuenta el 2º año
    # cuando la ventana lo abarca (la pantalla debe ofrecer el horizonte 730 para verlo).
    m2 = _consumo_map(app, mp, "30,120,365,730")
    assert abs(m2.get(730, 0) - 21000.0) < 1.0, ("h=730 los 3 lotes del calendario 2 años = 21000g", m2)
    assert abs(m2.get(365, 0) - 14000.0) < 1.0, ("h=365 sigue sin el de día 400", m2)


def test_kg_editado_por_usuario_manda_no_lote_size(app, db_clean):
    """El consumo usa cantidad_kg EDITADO por el usuario (no el lote_size de la fórmula)."""
    prod, mp = "QA KG EDIT", "MP-QAKGED"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
          (mp, mp, mp + " INCI"))
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))  # lote_size 10
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,?,0)", (prod, mp, mp, 10))
    # lote con cantidad_kg = 25 (editado · distinto del lote_size 10) → 10% × 25 × 1000 = 2500 g
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
          "VALUES (?, date('now','-5 hours','+5 days'), 1, 'pendiente', 'eos_plan', 25)", (prod,))
    m = _consumo_map(app, mp, "15,30")
    assert abs(m.get(15, 0) - 2500.0) < 1.0, ("usa el kg editado (25) no el lote_size (10 → daría 1000)", m)


def test_cadencia_45dias_acumula_por_horizonte_como_espera_sebastian(app, db_clean):
    """Sebastián 11-jul: "el LIMPIADOR BHA se hace cada 45 días → en 30d suma sus MP 1 vez, en 90d 2 veces, en
    120d 3 veces". Se PRUEBA con el motor real: 3 lotes fásicos (día 10, 55, 100 · cada 45d) → el consumo
    acumulativo de cada MP es #lotes_en_la_ventana × (%×kg×1000). 2 MPs para ver que cada una acumula sola."""
    prod = "QA BHA 45D"
    mp5, mp10 = "MP-QABHA5", "MP-QABHA10"   # 5% y 10%
    for mp in (mp5, mp10):
        _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
              (mp, mp, mp + " INCI"))
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,20,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,?,0)", (prod, mp5, mp5, 5))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,?,0)", (prod, mp10, mp10, 10))
    # cada lote 20 kg · MP5 = 5%×20×1000 = 1000 g/lote · MP10 = 10%×20×1000 = 2000 g/lote
    for dias in (10, 55, 100):   # cada 45 días, fásico como el ejemplo del usuario
        _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
              "VALUES (?, date('now','-5 hours','+' || ? || ' days'), 1, 'pendiente', 'eos_plan', 20)", (prod, dias))

    m5 = _consumo_map(app, mp5, "30,45,90,120,180")
    m10 = _consumo_map(app, mp10, "30,45,90,120,180")
    # 30d → solo el lote de día 10 = 1 vez · 90d → día 10+55 = 2 veces · 120d → 10+55+100 = 3 veces
    assert abs(m5.get(30, 0) - 1000.0) < 1.0, ("30d = 1 lote (día 10)", m5)
    assert abs(m5.get(90, 0) - 2000.0) < 1.0, ("90d = 2 lotes (día 10,55)", m5)
    assert abs(m5.get(120, 0) - 3000.0) < 1.0, ("120d = 3 lotes (día 10,55,100)", m5)
    # cada MP acumula por su propio %: MP10 el doble de MP5 en cada horizonte
    assert abs(m10.get(30, 0) - 2000.0) < 1.0, ("MP10 30d = 1 lote × 2000", m10)
    assert abs(m10.get(90, 0) - 4000.0) < 1.0, ("MP10 90d = 2 × 2000", m10)
    assert abs(m10.get(120, 0) - 6000.0) < 1.0, ("MP10 120d = 3 × 2000", m10)
    # 45d → todavía solo el de día 10 (el de día 55 aún no entra) · 180d → los 3 (no hay 4º)
    assert abs(m5.get(45, 0) - 1000.0) < 1.0, ("45d = 1 lote · el de día 55 aún NO entra", m5)
    assert abs(m5.get(180, 0) - 3000.0) < 1.0, ("180d = 3 lotes (no hay más sembrados)", m5)
