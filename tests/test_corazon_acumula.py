"""PROPIEDAD 1 · consumo ACUMULATIVO + suma de TODAS las producciones que
comparten una MP.

Verifica /api/abastecimiento/consumo-horizontes con datos CONTROLADOS:
  - 2 productos DISTINTOS que usan la MISMA materia prima.
  - Programados a +2 días y +40 días.
  - consumo[15] = solo el de +2d.
  - consumo[60] = ambos sumados.
  - crece de forma monótona: 15 <= 30 <= 60 <= 90.

Prefijos únicos 'QAacumula-' / 'QAACUM ...' para aislamiento total.
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


def _consumo_mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def test_corazon_acumula_suma_producciones_compartiendo_mp(app, db_clean):
    # --- MP compartida por DOS productos distintos ---
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('MP-QAACUMULA','Acumula QA','ACUMULA INCI QA',1)")

    # Producto A: usa la MP al 10%.  Producto B: al 20%.
    for prod, pct in [('QAACUM PRODA', 10), ('QAACUM PRODB', 20)]:
        _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)", (prod,))
        _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
              "VALUES (?, 'MP-QAACUMULA', 'Acumula QA', ?, 0)", (prod, pct))

    # Programar (Fijo / eos_plan):
    #   A en +2 días con 10 kg  -> 10% de 10kg = 1000 g
    #   B en +40 días con 5 kg  -> 20% de  5kg = 1000 g
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAACUM PRODA', date('now','-5 hours','+2 days'), 1, 'pendiente', 10, 'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAACUM PRODB', date('now','-5 hours','+40 days'), 1, 'pendiente', 5, 'eos_plan')")

    mp = _consumo_mp(app, "MP-QAACUMULA")
    assert mp is not None, "la MP compartida debe aparecer (el match producción↔fórmula funciona)"
    cons = mp["consumo"]

    a_g = 1000.0  # A: 10% × 10kg × 1000
    b_g = 1000.0  # B: 20% ×  5kg × 1000

    # +2d entra en todos los horizontes; +40d entra solo desde 60d.
    # 15 y 30 = solo A
    assert abs(cons["15"] - a_g) < 1, f"consumo[15] debe ser SOLO A (1000g · +2d) · {cons}"
    assert abs(cons["30"] - a_g) < 1, f"consumo[30] sigue SOLO A (+40d aún no entra) · {cons}"
    # 60 y 90 = A + B acumulados
    assert abs(cons["60"] - (a_g + b_g)) < 1, f"consumo[60] debe ACUMULAR A+B (2000g) · {cons}"
    assert abs(cons["90"] - (a_g + b_g)) < 1, f"consumo[90] debe seguir A+B (2000g) · {cons}"

    # Monotonía: 15 <= 30 <= 60 <= 90 (acumulativo nunca decrece).
    assert cons["15"] <= cons["30"] <= cons["60"] <= cons["90"], f"debe ser monótono creciente · {cons}"
