"""Operarios/jefe ajustan inventario SIN aprobación de Gerencia (Sebastián 12-jun).
Antes un ajuste >5% por un no-admin daba 403. Ahora lo aplica + queda en el
INFORME (alertas-gerencia → aplicados) con quién lo hizo (trazabilidad, no bloqueo).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_operario_aplica_ajuste_mayor_5pct_sin_aprobacion_y_queda_en_informe(app, db_clean):
    COD, LOTE, EST = 'MP-AJSA', 'L-AJSA', 'E-AJSA'
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,?,?,1)", (COD, 'GLYCERIN', 'Glicerina'))
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estanteria, estado_lote) "
          "VALUES (?,?,?,'Entrada',datetime('now'),?,?,'VIGENTE')", (COD, 'GLYCERIN', 1000, LOTE, EST))

    # 'luis' es operario de planta (PLANTA_USERS), NO admin
    c = _login(app, 'luis')
    r = c.post('/api/conteo/iniciar', json={'estanteria': EST})
    assert r.status_code == 200, r.data
    cid = r.get_json()['conteo_id']

    # físico 400 vs sistema 1000 -> diff -600 = 60% (>5% -> requiere_gerencia)
    item = {'codigo_mp': COD, 'lote': LOTE, 'stock_sistema': 1000, 'stock_fisico': 400,
            'nombre': 'GLYCERIN', 'estanteria': EST, 'precio_ref': 100, 'causa_diferencia': 'merma grande'}
    r = c.post(f'/api/conteo/{cid}/guardar', json={'items': [item]})
    assert r.status_code == 200, r.data
    saved = r.get_json()['items']
    it = next(x for x in saved if x['codigo_mp'] == COD)
    assert it['requiere_gerencia'] is True, "60% debe marcar requiere_gerencia"

    # El operario aplica el ajuste -> ANTES 403, AHORA 200
    r = c.post(f'/api/conteo/{cid}/ajustar', json={'item_id': it['id']})
    assert r.status_code == 200, r.data

    # Se movió el kardex (Salida 600)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    salida = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos "
                          "WHERE material_id=? AND tipo='Salida'", (COD,)).fetchone()[0]
    conn.close()
    assert abs(salida - 600) < 0.5, f"debe descontar 600g · fue {salida}"

    # Queda en el INFORME (no en pendientes) con quién lo aplicó
    r = c.get('/api/conteo/alertas-gerencia')
    assert r.status_code == 200, r.data
    d = r.get_json()
    aplicados = d.get('aplicados', [])
    mio = [a for a in aplicados if a['codigo_mp'] == COD]
    assert mio, "el ajuste grande aplicado debe salir en el informe"
    assert (mio[0].get('aplicado_por') or '') == 'luis', "el informe debe registrar quién lo aplicó"
