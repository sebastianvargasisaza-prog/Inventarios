"""M-1 (Sebastián 12-jun · auditoría dashboard): "Verificar Stock" (simular) debe
reportar la MISMA disponibilidad que alcanza el descuento FEFO. Antes sumaba plano
(S/L + polvo + estados retenidos) -> decía factible y el POST real fallaba 422.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_simular_no_cuenta_stock_sin_lote(app, db_clean):
    db = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPSIM1','Test Sim',1)")
        db.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES ('ZZ SIM',1000,1)")
        db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ SIM'")
        db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
                   "VALUES ('ZZ SIM','MPSIM1','Test Sim',10,100)")
        # 300g pero SIN lote real (S/L) -> FEFO NO lo puede usar -> simular tampoco
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                   "VALUES ('MPSIM1','Test Sim',300,'Entrada','2026-06-01','S/L','VIGENTE')")
        db.commit()
    finally:
        db.close()

    c = _login(app)
    r = c.post('/api/produccion/simular', json={'producto': 'ZZ SIM', 'cantidad_kg': 1},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = r.get_json()
    items = d.get('ingredientes') or d.get('materiales') or d.get('resultado') or []
    m = next((x for x in items if x.get('material_id') == 'MPSIM1'), None)
    assert m is not None, f"MPSIM1 debe aparecer en simular · {d}"
    # Stock S/L NO cuenta como disponible (FEFO no lo alcanza)
    assert (m.get('g_disponible') or 0) < 1, f"S/L no debe contar como disponible · {m}"
    assert m.get('suficiente') in (False, 0), f"debe salir insuficiente · {m}"
