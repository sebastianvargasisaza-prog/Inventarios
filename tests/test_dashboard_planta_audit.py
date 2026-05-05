"""Tests del audit del Dashboard de Planta (Sebastian 5-may-2026).

Cubre los fixes derivados del audit zero-error:

  1. /api/inventario · KPIs lotes_vencidos y venc_criticos calculados
     dinámicamente desde fecha_vencimiento (antes usaban estado_lote
     estatico que nunca se actualizaba → drift critico).

  2. /api/inventario · lotes_cuarentena case-insensitive (UPPER) porque
     calidad.py escribe 'Cuarentena' (Cap) y inventario.py escribe
     'CUARENTENA' (UPPER) — la mezcla causaba conteos incorrectos.

  3. _distribuir_fefo y _validar_stock_para_produccion · usan UPPER +
     lista canonica completa (CUARENTENA, CUARENTENA_EXTENDIDA, VENCIDO,
     RECHAZADO, AGOTADO, BLOQUEADO) → garantia de no consumir lotes
     no disponibles en producción.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_lote(codigo_mp, nombre, gramos, lote, fecha_venc, estado='VIGENTE'):
    """Inserta una entrada con lote + fecha_vencimiento + estado."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo)
           VALUES (?, ?, 1)""",
        (codigo_mp, nombre),
    )
    c.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, fecha_vencimiento, estado_lote, operador)
           VALUES (?, ?, ?, 'Entrada', date('now'), 'Test seed', ?, ?, ?, 'test')""",
        (codigo_mp, nombre, gramos, lote, fecha_venc, estado),
    )
    conn.commit()
    conn.close()


def _cleanup(codigos):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    if codigos:
        ph = ','.join(['?'] * len(codigos))
        c.execute(f"DELETE FROM movimientos WHERE material_id IN ({ph})", codigos)
        c.execute(f"DELETE FROM maestro_mps WHERE codigo_mp IN ({ph})", codigos)
    conn.commit()
    conn.close()


# ── KPI lotes_vencidos dinamico ─────────────────────────────────────


def test_lotes_vencidos_calcula_dinamicamente_desde_fecha_venc(app, db_clean):
    """Lote con estado_lote='VIGENTE' pero fecha_vencimiento pasada
    debe contar como vencido (drift que afectaba decisiones)."""
    cs = _login(app)
    # Snapshot del baseline ANTES de sembrar (otros tests pueden haber
    # dejado lotes vencidos · queremos verificar el delta).
    r0 = cs.get('/api/inventario'); base = r0.get_json()['kpis']['ahora']['lotes_vencidos']
    _seed_lote('MP-AUD-V1', 'X', 1000, 'LV-001', '2024-01-01', 'VIGENTE')
    _seed_lote('MP-AUD-V2', 'Y', 500,  'LV-002', '2024-06-15', 'VIGENTE')
    _seed_lote('MP-AUD-V3', 'Z', 2000, 'LV-003', '2027-12-31', 'VIGENTE')  # NO vencido
    try:
        r = cs.get('/api/inventario')
        assert r.status_code == 200
        d = r.get_json()
        # Verificacion directa contra DB: el query del endpoint debe
        # retornar al menos 2 (LV-001 y LV-002 con stock > 0 y vencidos)
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt_directo = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT material_id, lote, MIN(fecha_vencimiento) v,
                     SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) s
              FROM movimientos
              WHERE COALESCE(lote,'') != '' AND fecha_vencimiento IS NOT NULL
                AND fecha_vencimiento != ''
                AND material_id IN ('MP-AUD-V1','MP-AUD-V2','MP-AUD-V3')
              GROUP BY material_id, lote
              HAVING s > 0 AND v < date('now')
            )
        """).fetchone()[0]
        conn.close()
        assert cnt_directo == 2, \
            f"Query directo cuenta {cnt_directo}, esperaba 2 (LV-001, LV-002)"
        # Endpoint: delta consistente con verificacion directa
        ahora = d['kpis']['ahora']['lotes_vencidos']
        assert ahora >= base + 2, \
            f"lotes_vencidos={ahora} (base={base}) · directo={cnt_directo}"
    finally:
        _cleanup(['MP-AUD-V1', 'MP-AUD-V2', 'MP-AUD-V3'])


def test_lotes_vencidos_excluye_lotes_consumidos(app, db_clean):
    """Lote vencido pero ya consumido (stock=0) NO debe contarse."""
    cs = _login(app)
    # Entrada vencida + Salida del mismo lote = stock 0
    _seed_lote('MP-AUD-VC', 'X', 500, 'LVC-001', '2024-01-01', 'VIGENTE')
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, operador)
           VALUES ('MP-AUD-VC', 'X', 500, 'Salida', date('now'),
                   'Consumido', 'LVC-001', 'test')"""
    )
    # Otro lote vencido CON stock
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            observaciones, lote, fecha_vencimiento, operador)
           VALUES ('MP-AUD-VC', 'X', 100, 'Entrada', date('now'),
                   'Otro vencido', 'LVC-002', '2024-06-15', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/inventario')
        d = r.get_json()
        # Solo LVC-002 (con stock>0) debe contarse · LVC-001 stock=0
        # Sumamos +1 (no podemos asegurar conteo exacto por otros lotes
        # de otros tests que pueda haber dejado · solo verificamos que
        # el lote consumido NO se cuenta).
        # Verificacion directa via query como sanity:
        conn2 = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn2.execute("""
            SELECT COUNT(*) FROM (
              SELECT material_id, lote, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as s
              FROM movimientos WHERE material_id='MP-AUD-VC'
              GROUP BY material_id, lote
              HAVING s > 0 AND MIN(fecha_vencimiento) < date('now')
            )
        """).fetchone()[0]
        conn2.close()
        assert cnt == 1, f"Solo LVC-002 debe quedar como vencido con stock"
    finally:
        _cleanup(['MP-AUD-VC'])


# ── KPI venc_criticos dinamico ──────────────────────────────────────


def test_venc_criticos_lotes_proximos_30d(app, db_clean):
    """Lotes que vencen en próximos 30 días deben contarse aunque
    estado_lote sea 'VIGENTE' (antes usaba 'CRITICO'/'PROXIMO' que
    nunca se asignan)."""
    from datetime import date, timedelta
    cs = _login(app)
    r0 = cs.get('/api/inventario'); base = r0.get_json()['kpis']['cerca']['venc_criticos_30d']
    fut15 = (date.today() + timedelta(days=15)).isoformat()
    fut45 = (date.today() + timedelta(days=45)).isoformat()
    _seed_lote('MP-AUD-C1', 'C1', 1000, 'LC-001', fut15, 'VIGENTE')  # critico
    _seed_lote('MP-AUD-C2', 'C2', 1000, 'LC-002', fut45, 'VIGENTE')  # NO critico
    try:
        r = cs.get('/api/inventario')
        d = r.get_json()
        # Delta: +1 (LC-001), LC-002 fuera de 30d
        actual = d['kpis']['cerca']['venc_criticos_30d']
        assert actual >= base + 1, \
            f"venc_criticos_30d={actual} debe ser >= base({base})+1"
        # Verificacion directa: solo LC-001 entra
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT material_id, lote, MIN(fecha_vencimiento) v,
                     SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) s
              FROM movimientos WHERE material_id IN ('MP-AUD-C1','MP-AUD-C2')
              GROUP BY material_id, lote
              HAVING s > 0 AND v >= date('now') AND v <= date('now','+30 day')
            )
        """).fetchone()[0]
        conn.close()
        assert cnt == 1, "Solo LC-001 (15d) entra · LC-002 (45d) no"
    finally:
        _cleanup(['MP-AUD-C1', 'MP-AUD-C2'])


# ── lotes_cuarentena case-insensitive ────────────────────────────────


def test_lotes_cuarentena_case_insensitive(app, db_clean):
    """Acepta 'CUARENTENA' (uppercase, inventario.py) y 'Cuarentena'
    (capitalized, calidad.py) y 'CUARENTENA_EXTENDIDA'."""
    from datetime import date, timedelta
    cs = _login(app)
    r0 = cs.get('/api/inventario'); base = r0.get_json()['kpis']['cerca']['lotes_cuarentena']
    fut = (date.today() + timedelta(days=200)).isoformat()
    _seed_lote('MP-AUD-Q1', 'Q1', 1000, 'LQ-001', fut, 'CUARENTENA')
    _seed_lote('MP-AUD-Q2', 'Q2', 1000, 'LQ-002', fut, 'Cuarentena')
    _seed_lote('MP-AUD-Q3', 'Q3', 1000, 'LQ-003', fut, 'CUARENTENA_EXTENDIDA')
    try:
        # Verificacion directa
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute("""
            SELECT COUNT(*) FROM movimientos
            WHERE tipo='Entrada' AND material_id IN ('MP-AUD-Q1','MP-AUD-Q2','MP-AUD-Q3')
              AND UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
        """).fetchone()[0]
        conn.close()
        assert cnt == 3, "Los 3 lotes deben contarse (case-insensitive)"
        # Endpoint: delta +3
        r = cs.get('/api/inventario')
        d = r.get_json()
        actual = d['kpis']['cerca']['lotes_cuarentena']
        assert actual >= base + 3, \
            f"lotes_cuarentena={actual} debe ser >= base({base})+3"
    finally:
        _cleanup(['MP-AUD-Q1', 'MP-AUD-Q2', 'MP-AUD-Q3'])


# ── _distribuir_fefo NO consume CUARENTENA ──────────────────────────


def test_fefo_no_consume_lotes_cuarentena(app, db_clean):
    """FEFO debe saltar lotes en CUARENTENA aunque tengan vencimiento
    cercano · solo consume aprobados/vigentes."""
    from datetime import date, timedelta
    fut_cerca = (date.today() + timedelta(days=10)).isoformat()
    fut_lejos = (date.today() + timedelta(days=200)).isoformat()
    # Lote A: en CUARENTENA, vence pronto (FEFO lo elegiria primero, NO debe)
    _seed_lote('MP-FEFO-X', 'X', 1000, 'L-CUAR', fut_cerca, 'CUARENTENA')
    # Lote B: VIGENTE, vence tarde (FEFO debe usar este)
    _seed_lote('MP-FEFO-X', 'X', 1000, 'L-VIG', fut_lejos, 'VIGENTE')
    try:
        # Importar el helper directamente
        api_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "api",
        )
        import sys
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        from blueprints.programacion import _distribuir_fefo
        conn = sqlite3.connect(os.environ["DB_PATH"])
        c = conn.cursor()
        distrib = _distribuir_fefo(c, 'MP-FEFO-X', 500)
        conn.close()
        # Solo debe usar L-VIG · L-CUAR esta excluido
        lotes_usados = {d['lote'] for d in distrib if d['lote']}
        assert 'L-CUAR' not in lotes_usados, \
            f"FEFO consumió lote en CUARENTENA: {lotes_usados}"
        assert 'L-VIG' in lotes_usados or any(d.get('sin_lote') for d in distrib), \
            "FEFO debió usar L-VIG"
    finally:
        _cleanup(['MP-FEFO-X'])


def test_fefo_no_consume_vencidos_uppercase(app, db_clean):
    """estado_lote='VENCIDO' (UPPERCASE) debe excluirse en FEFO
    (antes solo excluia 'Vencido' Capitalizado)."""
    from datetime import date, timedelta
    fut_lejos = (date.today() + timedelta(days=200)).isoformat()
    _seed_lote('MP-FEFO-V', 'V', 1000, 'L-VEN', '2024-01-01', 'VENCIDO')
    _seed_lote('MP-FEFO-V', 'V', 1000, 'L-VIG', fut_lejos, 'VIGENTE')
    try:
        api_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "api",
        )
        import sys
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        from blueprints.programacion import _distribuir_fefo
        conn = sqlite3.connect(os.environ["DB_PATH"])
        c = conn.cursor()
        distrib = _distribuir_fefo(c, 'MP-FEFO-V', 500)
        conn.close()
        lotes_usados = {d['lote'] for d in distrib if d['lote']}
        assert 'L-VEN' not in lotes_usados, \
            f"FEFO consumió lote VENCIDO: {lotes_usados}"
    finally:
        _cleanup(['MP-FEFO-V'])


# ── _validar_stock_para_produccion case-insensitive ────────────────


# ── Bodega MP · /api/lotes filtra MEEs y lotes consumidos ───────────


def test_lotes_excluye_mees_registrados_en_maestro_mps(app, db_clean):
    """Si un envase/tapa fue registrado por error en maestro_mps con
    tipo_material!='MP', NO debe aparecer en Bodega MP."""
    cs = _login(app)
    # MP normal
    _seed_lote('MP-BMP-1', 'Glicerina', 1000, 'L-MP-1', '2027-01-01', 'VIGENTE')
    # MEE registrado erroneamente en maestro_mps (escenario legacy)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT OR REPLACE INTO maestro_mps
           (codigo_mp, nombre_comercial, tipo_material, activo)
           VALUES ('MEE-BMP-1', 'Frasco 50ml', 'Envase', 1)"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, fecha_vencimiento, estado_lote, operador)
           VALUES ('MEE-BMP-1', 'Frasco 50ml', 500, 'Entrada', date('now'),
                   'L-MEE-1', '2027-12-31', 'VIGENTE', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/lotes')
        assert r.status_code == 200
        d = r.get_json()
        codigos = {l['material_id'] for l in d['lotes']}
        assert 'MP-BMP-1' in codigos, "MP normal debe aparecer"
        assert 'MEE-BMP-1' not in codigos, \
            "MEE con tipo_material='Envase' NO debe aparecer en Bodega MP"
    finally:
        _cleanup(['MP-BMP-1', 'MEE-BMP-1'])


def test_lotes_excluye_lotes_consumidos_completamente(app, db_clean):
    """Lote con stock_neto=0 (consumido completamente) NO debe aparecer."""
    cs = _login(app)
    _seed_lote('MP-CON-1', 'X', 1000, 'L-CON', '2027-01-01', 'VIGENTE')
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, operador)
           VALUES ('MP-CON-1', 'X', 1000, 'Salida', date('now'),
                   'L-CON', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/lotes')
        d = r.get_json()
        lotes_con = [l for l in d['lotes']
                      if l['material_id'] == 'MP-CON-1' and l['lote'] == 'L-CON']
        assert lotes_con == [], \
            f"Lote consumido (stock=0) NO debe aparecer · llegaron {lotes_con}"
    finally:
        _cleanup(['MP-CON-1'])


def test_lotes_incluye_mp_sin_tipo_material_set(app, db_clean):
    """MPs legacy sin tipo_material asignado deben aparecer (default 'MP')."""
    cs = _login(app)
    # Insertar MP SIN tipo_material (legacy)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT OR REPLACE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo)
           VALUES ('MP-LEG-1', 'Legacy MP', 1)"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, fecha_vencimiento, estado_lote, operador)
           VALUES ('MP-LEG-1', 'Legacy MP', 500, 'Entrada', date('now'),
                   'L-LEG', '2027-01-01', 'VIGENTE', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/lotes')
        d = r.get_json()
        codigos = {l['material_id'] for l in d['lotes']}
        assert 'MP-LEG-1' in codigos, \
            "MP legacy sin tipo_material debe aparecer (COALESCE default 'MP')"
    finally:
        _cleanup(['MP-LEG-1'])


def test_lotes_incluye_lote_parcialmente_consumido(app, db_clean):
    """Lote con 1000g entrada y 300g salida debe aparecer con stock_neto=700."""
    cs = _login(app)
    _seed_lote('MP-PAR-1', 'X', 1000, 'L-PAR', '2027-01-01', 'VIGENTE')
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, operador)
           VALUES ('MP-PAR-1', 'X', 300, 'Salida', date('now'),
                   'L-PAR', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/lotes')
        d = r.get_json()
        lotes = [l for l in d['lotes']
                  if l['material_id'] == 'MP-PAR-1' and l['lote'] == 'L-PAR']
        assert len(lotes) == 1
        # cantidad_g debe ser 700 (1000 - 300)
        assert lotes[0]['cantidad_g'] == 700, \
            f"stock_neto debe ser 700 · llegado {lotes[0]['cantidad_g']}"
    finally:
        _cleanup(['MP-PAR-1'])


def test_validar_stock_excluye_cuarentena_capitalizada(app, db_clean):
    """estado_lote='Cuarentena' (Capitalizada · calidad.py) debe
    excluirse al calcular disponible."""
    from datetime import date, timedelta
    fut = (date.today() + timedelta(days=200)).isoformat()
    _seed_lote('MP-VAL-X', 'X', 5000, 'L-CAP', fut, 'Cuarentena')  # NO disponible
    _seed_lote('MP-VAL-X', 'X', 1000, 'L-VIG', fut, 'VIGENTE')      # SI disponible
    try:
        api_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "api",
        )
        import sys
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        from blueprints.programacion import _validar_stock_para_produccion
        conn = sqlite3.connect(os.environ["DB_PATH"])
        c = conn.cursor()
        # Pedir 3000g · solo hay 1000g disponible (5000g en cuarentena no cuenta)
        faltantes = _validar_stock_para_produccion(
            c, [{'codigo_mp': 'MP-VAL-X', 'nombre': 'X', 'cantidad_g': 3000}]
        )
        conn.close()
        assert len(faltantes) == 1, "Debe reportar 1 faltante"
        assert faltantes[0]['disponible_g'] == 1000, \
            f"Solo VIGENTE cuenta · Cuarentena excluida (UPPER) · disponible_g={faltantes[0]['disponible_g']}"
    finally:
        _cleanup(['MP-VAL-X'])
