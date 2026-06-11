"""Verificación a fondo de Abastecimiento (Sebastián 10-jun-2026 · "¿acumula? ¿usa las
fórmulas reales? ¿hace match con producciones?").

Prueba con datos concretos que /api/abastecimiento/consumo-horizontes:
  · hace MATCH producción↔fórmula,
  · usa las cantidades REALES de la fórmula (% × kg),
  · ACUMULA el consumo entre producciones por horizonte (15 ⊂ 30 ⊂ 60 ⊂ 90).
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


def _consumo_mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def test_abastecimiento_acumula_y_usa_formulas(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('MP-SHAREZZ','Compartida ZZ','SHARED INCI ZZ',1)")
    # 2 productos con fórmula por % que usan la MISMA materia prima
    for prod, pct in [('ZZ-PRODA', 10), ('ZZ-PRODB', 20)]:
        _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)", (prod,))
        _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
              "VALUES (?, 'MP-SHAREZZ', 'Compartida ZZ', ?, 0)", (prod, pct))
    # Programar (Fijo): A en +2 días con 10 kg · B en +40 días con 5 kg
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('ZZ-PRODA', date('now','-5 hours','+2 days'), 1, 'pendiente', 10, 'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('ZZ-PRODB', date('now','-5 hours','+40 days'), 1, 'pendiente', 5, 'eos_plan')")

    mp = _consumo_mp(app, "MP-SHAREZZ")
    assert mp is not None, "la MP compartida debe aparecer → el match producción↔fórmula funciona"
    cons = mp["consumo"]
    # Cantidades REALES de la fórmula: A=10% de 10kg=1000g · B=20% de 5kg=1000g
    # A entra en TODOS los horizontes (día 2). B solo desde 60d (día 40 > 30).
    assert abs(cons["15"] - 1000) < 1, f"15d debe ser solo A (1000g) · {cons}"
    assert abs(cons["30"] - 1000) < 1, f"30d debe ser solo A (1000g) · {cons}"
    assert abs(cons["60"] - 2000) < 1, f"60d debe ACUMULAR A+B (2000g) · {cons}"
    assert abs(cons["90"] - 2000) < 1, f"90d debe ACUMULAR A+B (2000g) · {cons}"


def test_abastecimiento_match_tolera_acento_y_signo(app, db_clean):
    """FIX 10-jun: el match producción↔fórmula ahora tolera acentos/'+'/puntuación
    (antes 'ZZ ÁCIDO + NAD' no casaba con 'ZZ ACIDO NAD' → consumo 0 silencioso)."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('MP-ACENTOZZ','Acento ZZ','ACENTO INCI ZZ',1)")
    # Fórmula registrada SIN acento ni signo
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('ZZ ACIDO NAD', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('ZZ ACIDO NAD', 'MP-ACENTOZZ', 'Acento ZZ', 50, 0)")
    # Programado CON acento y '+': difiere en texto pero es el MISMO producto
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('ZZ ÁCIDO + NAD', date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')")
    mp = _consumo_mp(app, "MP-ACENTOZZ")
    assert mp is not None, "tras el fix, acento/'+' ya no debe romper el match"
    # 50% de 10kg = 5000g · entra en todos los horizontes (día 5)
    assert abs(mp["consumo"]["15"] - 5000) < 1, mp["consumo"]
