"""17-jun · E2E de la CADENA CRÍTICA de MP (Sebastián va a cargar MPs reales):
ingreso (stock en kardex) → mapeo con la fórmula maestra → PRODUCIR → descuento exacto.

"Sería una catástrofe que no funcione." Este test prueba el flujo completo de punta
a punta: una MP con stock, una fórmula maestra que la usa, y al producir el descuento
sale por FEFO con la cantidad EXACTA de la fórmula (% × kg). Cubre además el caso de
MAPEO por INCI (la fórmula referencia un código y el stock está en otro del mismo INCI).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _stock(material_id):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    v = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +','Ajuste') THEN cantidad "
        "WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad ELSE 0 END),0) "
        "FROM movimientos WHERE material_id=?", (material_id,)).fetchone()[0]
    conn.close()
    return float(v or 0)


def test_e2e_mp_ingreso_mapeo_descuento(app, db_clean):
    """Cadena feliz: MP código exacto en la fórmula · 5% de un lote de 10kg = 500 g."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM formula_items WHERE producto_nombre='E2E PROD DIRECTO'")
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre='E2E PROD DIRECTO'")
        conn.execute("DELETE FROM movimientos WHERE material_id='MPE2E1'")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MPE2E1'")
        # 1) Maestro de MP (lo que define el catálogo)
        conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
                     "VALUES ('MPE2E1','GLYCERIN E2E','Glicerina E2E','MP',1)")
        # 2) Fórmula maestra que USA esa MP (5% del lote)
        conn.execute("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
                     "VALUES ('E2E PROD DIRECTO',10000,10,1,datetime('now'))")
        conn.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
                     "VALUES ('E2E PROD DIRECTO','MPE2E1','GLYCERIN E2E',5.0,0)")
        # 3) INGRESO: la MP entra al kardex (lo que hace recepción/carga) · 2000 g VIGENTE
        conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento,operador) "
                     "VALUES ('MPE2E1','GLYCERIN E2E',2000,'Entrada',date('now'),'L-E2E-1','VIGENTE','2027-12-31','test')")
        conn.commit()
    finally:
        conn.close()
    assert _stock('MPE2E1') == 2000.0

    c = _login(app)
    # 4) PRODUCIR 10 kg (= 1 lote) → debe descontar 5% × 10kg = 500 g de MPE2E1
    r = c.post('/api/produccion', json={'producto': 'E2E PROD DIRECTO', 'cantidad_kg': 10, 'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    try:
        assert r.status_code in (200, 201), r.data[:400]
        # 5) DESCUENTO exacto: stock 2000 - 500 = 1500
        assert abs(_stock('MPE2E1') - 1500.0) < 1.0, \
            f'el descuento NO fue exacto · stock quedó {_stock("MPE2E1")} (esperado 1500)'
        # FEFO consumió el lote real (Salida sobre L-E2E-1)
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        sal = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos "
                           "WHERE material_id='MPE2E1' AND tipo='Salida' AND lote='L-E2E-1'").fetchone()[0]
        conn.close()
        assert abs(float(sal) - 500.0) < 1.0, f'la Salida FEFO debe ser 500 g sobre el lote real · {sal}'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        conn.execute("DELETE FROM movimientos WHERE material_id='MPE2E1'")
        conn.execute("DELETE FROM formula_items WHERE producto_nombre='E2E PROD DIRECTO'")
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre='E2E PROD DIRECTO'")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MPE2E1'")
        conn.commit(); conn.close()


def test_e2e_mp_mapeo_por_inci_descuenta(app, db_clean):
    """Caso real al cargar: la fórmula referencia un código y el stock entró en OTRO
    código del MISMO INCI → el resolver mapea por INCI y el descuento igual sale."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        for q in ["DELETE FROM formula_items WHERE producto_nombre='E2E PROD INCI'",
                  "DELETE FROM formula_headers WHERE producto_nombre='E2E PROD INCI'",
                  "DELETE FROM movimientos WHERE material_id IN ('MPE2E-FORM','MPE2E-STOCK')",
                  "DELETE FROM maestro_mps WHERE codigo_mp IN ('MPE2E-FORM','MPE2E-STOCK')"]:
            conn.execute(q)
        # Dos códigos, MISMO INCI: el de la fórmula SIN stock, el de bodega CON stock
        conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MPE2E-FORM','PANTHENOL E2E','MP',1)")
        conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MPE2E-STOCK','PANTHENOL E2E','MP',1)")
        conn.execute("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
                     "VALUES ('E2E PROD INCI',10000,10,1,datetime('now'))")
        conn.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
                     "VALUES ('E2E PROD INCI','MPE2E-FORM','PANTHENOL E2E',2.0,0)")
        # stock SOLO en el código de bodega (mismo INCI)
        conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento,operador) "
                     "VALUES ('MPE2E-STOCK','PANTHENOL E2E',1000,'Entrada',date('now'),'L-INCI-1','VIGENTE','2027-12-31','test')")
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'E2E PROD INCI', 'cantidad_kg': 10, 'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    try:
        assert r.status_code in (200, 201), r.data[:400]
        # 2% × 10kg = 200 g · debe salir del stock del código de bodega (mapeo por INCI)
        assert abs(_stock('MPE2E-STOCK') - 800.0) < 1.0, \
            f'el descuento por mapeo-INCI falló · stock bodega quedó {_stock("MPE2E-STOCK")} (esperado 800)'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        for q in ["DELETE FROM movimientos WHERE material_id IN ('MPE2E-FORM','MPE2E-STOCK')",
                  "DELETE FROM formula_items WHERE producto_nombre='E2E PROD INCI'",
                  "DELETE FROM formula_headers WHERE producto_nombre='E2E PROD INCI'",
                  "DELETE FROM maestro_mps WHERE codigo_mp IN ('MPE2E-FORM','MPE2E-STOCK')"]:
            conn.execute(q)
        conn.commit(); conn.close()
