"""Audit 3-jun · cadena bodega→fórmula→descuento perfecta tras unificar códigos.

- _get_mp_stock excluye BLOQUEADO (igual que validar/FEFO) → "lo que veo = lo que descuenta".
- _distribuir_fefo legacy (lote='') no consume stock en estado no-producible.
- _resolver_material_bodega: nombre ambiguo (>1 código) NO cruza (devuelve el propio fmid).
- unify repunta mp_formula_bridge (antes referenciaba columna inexistente).
"""
import os
import sqlite3


def _conn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def test_get_mp_stock_excluye_bloqueado(app, db_clean):
    import blueprints.programacion as prog
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-BLK','X','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,estado_lote,fecha) VALUES ('MP-BLK','X','Entrada',900,'LB','BLOQUEADO',date('now'))")
    c.commit()
    with app.app_context():
        from database import get_db
        st = prog._get_mp_stock(get_db())
    c.close()
    # el lote BLOQUEADO NO debe contar como disponible
    assert st.get('MP-BLK', 0) == 0, f"BLOQUEADO no debe sumar como stock · {st.get('MP-BLK')}"


def test_resolver_nombre_varios_codigos_elige_mas_stock(app, db_clean):
    """Mismo material en 2 códigos (mismo INCI) → el resolver elige el de MÁS stock
    (mismo material consigo mismo, seguro) para que producción jale el inventario."""
    import blueprints.programacion as prog
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-AMB-1','GLYCERIN','MP',1)")
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-AMB-2','GLYCERIN','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-AMB-1','GLYCERIN','Entrada',100,'L1',date('now'))")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-AMB-2','GLYCERIN','Entrada',900,'L2',date('now'))")
    c.commit()
    # fmid sin movimientos, nombre que matchea AMBOS → elige el de más stock (MP-AMB-2 = 900)
    res = prog._resolver_material_bodega(c, 'MP-FMID-SINMOV', 'GLYCERIN')
    c.close()
    assert res == 'MP-AMB-2', f"debe elegir el de más stock · {res}"


def test_resolver_nombre_unico_si_resuelve(app, db_clean):
    """Match ÚNICO por nombre se mantiene (rescate sin regresión)."""
    import blueprints.programacion as prog
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-UNI-1','UNOBTANIUM','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-UNI-1','UNOBTANIUM','Entrada',50,'L1',date('now'))")
    c.commit()
    res = prog._resolver_material_bodega(c, 'MP-FMID-X', 'UNOBTANIUM')
    c.close()
    assert res == 'MP-UNI-1', f"match único debe resolver · {res}"


def test_resolver_tier1_neto_cero_cae_a_inci_con_stock(app, db_clean):
    """Si el código de fórmula tiene movimientos pero NETO 0, el resolver NO se
    queda ahí: busca por INCI y elige el código (mismo material) con stock."""
    import blueprints.programacion as prog
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-F-INCI','TESTINOLX','MP',1)")
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-G-INCI','TESTINOLX','MP',1)")
    # F: tiene movimientos pero neto 0 (entrada+salida)
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-F-INCI','x','Entrada',50,'L0',date('now'))")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-F-INCI','x','Salida',50,'L0',date('now'))")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-G-INCI','x','Entrada',700,'L1',date('now'))")
    c.commit()
    res = prog._resolver_material_bodega(c, 'MP-F-INCI', 'nombre que no matchea nada')
    c.close()
    assert res == 'MP-G-INCI', f"tier-1 neto 0 debe caer al código del mismo INCI con stock · {res}"


def test_resolver_rescata_stock_en_codigo_inactivo(app, db_clean):
    """Caso PANTENOL real (4-jun): el código de fórmula Y su duplicado están AMBOS
    inactivos, con el stock atrapado en el inactivo. El resolver debe rescatarlo
    igual (inventario físico real) en vez de devolver 0g y abortar producción."""
    import blueprints.programacion as prog
    c = _conn()
    # ambos INACTIVOS · INCI único (no choca con seed) · stock en el duplicado inactivo
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-PAN-F','RESCATINOLZZ','MP',0)")
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-PAN-G','RESCATINOLZZ','MP',0)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-PAN-G','Rescatinol atrapado','Entrada',1118,'L1',date('now'))")
    c.commit()
    res = prog._resolver_material_bodega(c, 'MP-PAN-F', 'nombre que no matchea seed')
    c.close()
    assert res == 'MP-PAN-G', f"debe rescatar stock atrapado en código inactivo · {res}"


def test_agua_no_controla_stock_no_bloquea_produccion(app, db_clean):
    """AGUA del lab (controla_stock=0): infinita, fabricada en casa → producción NO
    la exige (sin faltante) ni la descuenta del kardex, aunque su stock sea 0/negativo."""
    import blueprints.programacion as prog
    c = _conn()
    # agua marcada como no-controlada, con stock NEGATIVO (caso real -330k)
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo,controla_stock) VALUES ('MP-AGUA','AQUA','MP',1,0)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-AGUA','Agua','Salida',5000,'L0',date('now'))")
    c.commit()
    # validar: agua marcada no-controla → NO debe aparecer como faltante
    mps = [{'codigo_mp': 'MP-AGUA', 'nombre': 'Agua', 'cantidad_g': 800, 'controla_stock': 0}]
    falt = prog._validar_stock_para_produccion(c, mps)
    c.close()
    assert falt == [], f"agua infinita no debe bloquear producción · {falt}"


def test_calcular_consumo_marca_agua_no_controla(app, db_clean):
    """_calcular_mp_consumo_produccion debe marcar controla_stock=0 para el agua
    (lee maestro_mps.controla_stock del código resuelto o el de fórmula)."""
    import blueprints.programacion as prog
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo,controla_stock) VALUES ('MP-AGUA2','AQUA','MP',1,0)")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD AGUA',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD AGUA','MP-AGUA2','Agua',70)")
    c.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,estado,origen) VALUES ('PROD AGUA',date('now'),1,1,'programado','manual')")
    pid = c.execute("SELECT id FROM produccion_programada WHERE producto='PROD AGUA'").fetchone()[0]
    c.commit()
    mps, _meta = prog._calcular_mp_consumo_produccion(c, pid)
    c.close()
    agua = [m for m in mps if m['codigo_mp'] == 'MP-AGUA2']
    assert agua and agua[0]['controla_stock'] == 0, f"agua debe marcarse controla_stock=0 · {mps}"


def test_simular_usa_resolver_y_jala_stock(app, db_clean):
    """Verificar Stock (simular) ahora resuelve el código de fórmula → reporta el
    stock que está bajo el código duplicado (antes mostraba 0g)."""
    from .conftest import TEST_PASSWORD, csrf_headers
    cl = app.test_client()
    cl.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
            headers=csrf_headers(), follow_redirects=False)
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-SF','SIMINOL','MP',1)")
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-SG','SIMINOL','MP',1)")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD SIM T1',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD SIM T1','MP-SF','Siminol',10)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-SG','Siminol','Entrada',5000,'L1',date('now'))")
    c.commit(); c.close()
    r = cl.post('/api/produccion/simular',
                json={'producto': 'PROD SIM T1', 'cantidad_kg': 1}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    row = [i for i in r.get_json()['ingredientes'] if i['material_id'] == 'MP-SF'][0]
    assert row['g_disponible'] > 0, f"simular debe resolver al código con stock · {row}"


def test_unify_repunta_bridge(app, db_clean):
    """maestro_mps_unificar ahora repunta mp_formula_bridge (bodega_material_id)."""
    from .conftest import csrf_headers, TEST_PASSWORD
    cl = app.test_client()
    r = cl.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
                headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-CANON-B','X','MP',1)")
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,tipo_material,activo) VALUES ('MP-VIEJO-B','X','MP',1)")
    c.execute("INSERT INTO mp_formula_bridge (formula_material_id,bodega_material_id,activo) VALUES ('MP-FORM-B','MP-VIEJO-B',1)")
    c.commit(); c.close()
    r = cl.post("/api/maestro-mps/unificar",
                json={"canonico": "MP-CANON-B", "codigos_a_unir": ["MP-VIEJO-B"],
                      "dry_run": False, "token": "UNIFICAR_MP_2026"},
                headers=csrf_headers())
    assert r.status_code == 200, r.data
    c = _conn()
    row = c.execute("SELECT bodega_material_id FROM mp_formula_bridge WHERE formula_material_id='MP-FORM-B'").fetchone()
    c.close()
    assert row and row[0] == "MP-CANON-B", f"el bridge debe repuntar al canónico · {row}"
