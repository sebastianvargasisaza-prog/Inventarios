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
