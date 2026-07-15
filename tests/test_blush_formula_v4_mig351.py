"""Blush Balm · fórmula v4 (Alejandro · Instructivo v4 15-jul) · mig 351.

Etapa 1: la fórmula ACTIVA 'BLUSH BALM' se corrige EN SITIO a la v4:
  - el 7.5% mal codificado como AGUA DESIONIZADA (imposible en un stick anhidro)
    se reemplaza por el PIGMENTO (MPPIGCI01) al 7.179% (Fase B · CI según tono);
  - Phenyl Trimethicone (MP00127) y Dicaprylyl Carbonate (MP00040): 20.271 -> 21.146;
  - PMSS (MP00055): 3.0 -> 2.0; Polyglyceryl-2 Triisostearate (MP00051): 10.0 -> 9.571;
  - suma = 100%; el pigmento queda controla_stock=0 (compra DIFERIDA hasta cargar
    pigmentos por tono · igual que el agua · no infla el faltante).
"""
import os
import sqlite3


def _rows(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _formula():
    return {r[0]: r[1] for r in _rows(
        "SELECT material_id, porcentaje FROM formula_items WHERE producto_nombre='BLUSH BALM'")}


def test_suma_100(app):
    f = _formula()
    assert abs(sum(f.values()) - 100.0) < 0.01, f"suma% = {sum(f.values())}"


def test_agua_fuera_pigmento_dentro(app):
    f = _formula()
    assert 'MPAGUALI01' not in f, "el AGUA DESIONIZADA NO debe seguir en la fórmula (era el bug del 7.5%)"
    assert 'MPPIGCI01' in f, "el pigmento (MPPIGCI01) debe estar en el slot de color"
    assert abs(f['MPPIGCI01'] - 7.179) < 0.001


def test_porcentajes_v4(app):
    f = _formula()
    assert abs(f['MP00127'] - 21.146) < 0.001, "Phenyl Trimethicone v4 = 21.146"
    assert abs(f['MP00040'] - 21.146) < 0.001, "Dicaprylyl Carbonate v4 = 21.146"
    assert abs(f['MP00055'] - 2.0) < 0.001, "PMSS v4 = 2.0"
    assert abs(f['MP00051'] - 9.571) < 0.001, "Polyglyceryl-2 Triisostearate v4 = 9.571"


def test_21_items_y_fases(app):
    f = _formula()
    assert len(f) == 21, f"la v4 tiene 21 ítems, hay {len(f)}"
    # los 3 péptidos de la Fase C, a 0.001 c/u
    for cod in ('MP00190', 'MP00172', 'MP00174'):
        assert abs(f[cod] - 0.001) < 1e-6


def test_pigmento_existe_activo_y_compra_diferida(app):
    # M38: el pigmento debe existir y estar ACTIVO (si no, el trigger de formula_items
    # rechaza el INSERT y en PG el DELETE previo deja la fórmula vacía). Y controla_stock=0
    # (compra DIFERIDA hasta cargar pigmentos por tono).
    r = _rows("SELECT COALESCE(activo,1), COALESCE(controla_stock,1) FROM maestro_mps WHERE codigo_mp='MPPIGCI01'")
    assert r, "MPPIGCI01 debe existir en maestro_mps"
    assert r[0][0] == 1, "MPPIGCI01 debe quedar ACTIVO (trigger formula_items)"
    assert r[0][1] == 0, "MPPIGCI01 debe quedar controla_stock=0 (compra diferida)"


def test_header_activo_y_variante_minuscula_off(app):
    act = {r[0]: r[1] for r in _rows(
        "SELECT producto_nombre, activo FROM formula_headers WHERE UPPER(producto_nombre)='BLUSH BALM'")}
    assert act.get('BLUSH BALM') == 1, "la fórmula v4 (mayúsc) queda ACTIVA"
    assert act.get('Blush Balm', 0) == 0, "la variante minúscula queda descontinuada"
