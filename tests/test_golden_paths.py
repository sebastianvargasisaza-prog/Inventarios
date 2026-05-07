"""GOLDEN PATHS · Sebastian 7-may-2026

Tests E2E de los flujos críticos de EOS · cada test ejercita un journey
completo (no unidad aislada) y verifica la condición de éxito desde el
punto de vista del USUARIO real (Catalina, Mayerlin, Luis Enrique,
Alejandro).

Si CUALQUIER test acá rompe → no se debe deployar. El Guardian agent
los corre antes de cada push.

Estos 5 tests fueron escogidos porque cubren los bugs que aparecieron
durante el sprint del 6-7-may-2026:

  1. Conteo cíclico → ajuste se aplica al LOTE REAL (no sintético) ·
     Bodega lo refleja. (Bug: ajuste-XX no afectaba lote 115013113)

  2. Sync Calendar modo espejo borra orfanos manuales ·
     produccion_programada == Calendar. (Bug: AZHC Lun 11 fantasma
     persistía aunque Calendar dijera Jue 14)

  3. PATCH SOL items sincroniza global · maestro_mps + mp_lead_time_config
     + precio_referencia. (Bug: cambiar proveedor en SOL no se reflejaba
     en próximo cron de auto_plan)

  4. Limpiar duplicados respeta guard inicio_real_at /
     inventario_descontado_at. (Bug potencial: borrar producción en curso)

  5. 3 fuentes de SOL filtran correcto · planta / usuarios / influencers
     no se mezclan. (Bug: Catalina veía planta en tab Solicitudes)

Cada test:
  · seed estado inicial
  · ejecuta acción de usuario (POST/PATCH/DELETE)
  · verifica que el efecto downstream sea correcto
  · cleanup completo en finally
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f'login fallo: {r.status_code}'
    return c


def _exec(sql, params=()):
    """Helper para queries DB directas en setup/cleanup."""
    conn = sqlite3.connect(os.environ['DB_PATH'])
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _query(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'])
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════
# GOLDEN PATH 1 · Conteo cíclico aplica ajuste al LOTE REAL
# ═══════════════════════════════════════════════════════════════════
# Bug que cazaría: el endpoint /ajustar usaba lote sintético 'AJUSTE-XX'
# en vez del lote real, así Bodega Materias Primas no reflejaba el cambio
# aunque el total agregado por material_id sí.

def test_golden_conteo_ciclico_ajuste_afecta_lote_real(app, db_clean):
    cs = _login(app, 'sebastian')

    codigo_mp = 'GP1-MP-AEROSIL'
    lote = 'GP1-LOTE-12345'
    nombre = 'Aerosil Test'

    # Setup: MP + lote con stock alto en kardex
    _exec("""INSERT OR REPLACE INTO maestro_mps
              (codigo_mp, nombre_comercial, proveedor, activo, tipo_material,
               precio_referencia)
              VALUES (?, ?, 'TestProv', 1, 'MP', 100)""",
          (codigo_mp, nombre))
    _exec("""INSERT INTO movimientos
              (material_id, material_nombre, cantidad, tipo, fecha,
               lote, estado_lote, operador)
              VALUES (?, ?, 1440000, 'Entrada', date('now'),
                      ?, 'VIGENTE', 'seed')""",
          (codigo_mp, nombre, lote))

    # Helper: stock del lote
    def _stock_lote():
        rows = _query("""
            SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad
                                     ELSE -cantidad END), 0)
            FROM movimientos WHERE material_id=? AND lote=?
        """, (codigo_mp, lote))
        return float(rows[0][0]) if rows else 0

    assert _stock_lote() == 1440000, 'precondición: stock inicial 1.440.000g'

    # Acción usuario:
    # 1. Iniciar conteo (estanteria='12')
    r = cs.post('/api/conteo/iniciar', json={'estanteria': '12', 'tipo_material': 'TODOS'},
                headers=csrf_headers())
    assert r.status_code == 200, f'iniciar fallo: {r.data}'
    conteo_id = r.get_json().get('conteo_id') or r.get_json().get('id')
    if not conteo_id:
        # Algunos endpoints devuelven {conteo:{id:N}}
        conteo_id = r.get_json().get('conteo', {}).get('id')
    assert conteo_id, f'conteo_id no encontrado en respuesta: {r.get_json()}'

    # 2. Guardar conteo con stock_físico=10000 (diferencia -1.430.000g, 99.3%)
    r = cs.post(f'/api/conteo/{conteo_id}/guardar',
                json={'items': [{
                    'codigo_mp': codigo_mp, 'nombre': nombre, 'lote': lote,
                    'stock_sistema': 1440000, 'stock_fisico': 10000,
                    'precio_ref': 100, 'estanteria': '12',
                    'causa_diferencia': 'Error de conteo',
                }]},
                headers=csrf_headers())
    assert r.status_code == 200, f'guardar fallo: {r.data}'
    items = r.get_json().get('items', [])
    assert items, 'guardar debe devolver items con sus IDs DB'
    item_id = items[0]['id']
    assert items[0]['requiere_gerencia'], 'diff 99.3% debe marcar requiere_gerencia'

    # 3. Aplicar ajuste como admin (auto-aprueba gerencia)
    r = cs.post(f'/api/conteo/{conteo_id}/ajustar',
                json={'item_id': item_id},
                headers=csrf_headers())
    assert r.status_code == 200, f'ajustar fallo: {r.data}'
    res = r.get_json()
    assert res.get('lote_ajustado') == lote, \
        f'ajuste debe aplicarse al lote REAL ({lote}), no sintético · got {res.get("lote_ajustado")}'

    # 4. Verificación CRÍTICA: el lote real debe reflejar el ajuste
    stock_post = _stock_lote()
    assert stock_post == 10000, \
        f'BUG: lote {lote} debería tener 10000g post-ajuste, tiene {stock_post}g · ' \
        f'esto significa que el ajuste no se aplicó al lote correcto y Bodega no lo refleja'

    # Cleanup
    _exec("DELETE FROM movimientos WHERE material_id=?", (codigo_mp,))
    _exec("DELETE FROM conteo_items WHERE conteo_id=?", (conteo_id,))
    _exec("DELETE FROM conteos_fisicos WHERE id=?", (conteo_id,))
    _exec("DELETE FROM maestro_mps WHERE codigo_mp=?", (codigo_mp,))


# ═══════════════════════════════════════════════════════════════════
# GOLDEN PATH 2 · Sync Calendar modo espejo borra orfanos manuales
# ═══════════════════════════════════════════════════════════════════
# Bug que cazaría: el sync solo cancelaba origen='calendar'. Las entries
# manuales viejas sobrevivían como fantasmas. AZHC Lun 11 manual seguía
# aunque Calendar lo había movido a Jue 14.

def test_golden_sync_calendar_espejo_borra_orfan_manual(app, db_clean, monkeypatch):
    cs = _login(app, 'sebastian')

    # Mock Calendar fetch · simulamos que Calendar respondió con 0 eventos
    # legítimamente (no es error de API, simplemente está vacío). Esto
    # debe disparar el modo espejo y borrar todo orfan no protegido.
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
    from blueprints import programacion as _prog
    monkeypatch.setattr(_prog, '_fetch_calendar_events',
                        lambda days_ahead=90: {'events': [], 'error': None, 'source': 'mock'})

    # Setup: producción manual fantasma (no está en Calendar)
    pid_fantasma = _exec("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, cantidad_kg, origen)
        VALUES ('GP2-FANTASMA-PROD', date('now', '+5 days'), 1, 'pendiente', 10, 'manual')
    """)
    # Otra con guard activo (NO debe borrarse)
    pid_iniciada = _exec("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, cantidad_kg, origen,
           inicio_real_at)
        VALUES ('GP2-INICIADA-PROD', date('now', '+5 days'), 1, 'pendiente', 10, 'manual',
                datetime('now'))
    """)

    try:
        # Acción usuario: forzar sync espejo
        r = cs.post('/api/programacion/checklist/sync-calendar?force_mirror=true&dias=30',
                    headers=csrf_headers())
        assert r.status_code == 200, f'sync fallo: {r.data}'
        d = r.get_json()
        assert d['force_mirror'] is True

        # Verificación: el fantasma debe haber sido borrado (HARD DELETE)
        rows = _query("SELECT COUNT(*) FROM produccion_programada WHERE id=?",
                      (pid_fantasma,))
        assert rows[0][0] == 0, \
            f'BUG: producción manual fantasma id={pid_fantasma} sobrevivió al espejo · ' \
            'el sync debe borrarla porque no está en Calendar'

        # La iniciada NO debe haberse tocado (guard inicio_real_at)
        rows = _query("SELECT COUNT(*) FROM produccion_programada WHERE id=?",
                      (pid_iniciada,))
        assert rows[0][0] == 1, \
            f'CRÍTICO: el espejo borró una producción ya INICIADA (id={pid_iniciada}) · ' \
            'esto corrompe inventario en curso'
    finally:
        _exec("DELETE FROM produccion_programada WHERE id IN (?, ?)",
              (pid_fantasma, pid_iniciada))


# ═══════════════════════════════════════════════════════════════════
# GOLDEN PATH 3 · PATCH SOL sincroniza proveedor + precio GLOBAL
# ═══════════════════════════════════════════════════════════════════
# Bug que cazaría: cambiar el proveedor en una SOL no se reflejaba en
# auto_plan (que lee mp_lead_time_config con COALESCE) ni en
# precio_referencia.

def test_golden_patch_sol_sincroniza_global(app, db_clean):
    cs = _login(app, 'catalina')

    codigo_mp = 'GP3-MP-SYNC'
    sol_num = 'GP3-SOL-001'

    # Seed
    _exec("""INSERT OR REPLACE INTO maestro_mps
              (codigo_mp, nombre_comercial, proveedor, activo, tipo_material,
               precio_referencia)
              VALUES (?, 'X', 'ProvOLD', 1, 'MP', 0)""", (codigo_mp,))
    _exec("DELETE FROM mp_lead_time_config WHERE material_id=?", (codigo_mp,))
    _exec("""INSERT OR REPLACE INTO solicitudes_compra
              (numero, fecha, estado, solicitante, urgencia, observaciones,
               area, empresa, categoria, tipo)
              VALUES (?, date('now'), 'Pendiente', 'test', 'Normal', '',
                      'Test', 'Espagiria', 'Materia Prima', 'Compra')""", (sol_num,))
    item_id = _exec("""INSERT INTO solicitudes_compra_items
                        (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                         valor_estimado, proveedor_sugerido, precio_unit_g)
                        VALUES (?, ?, 'X', 5000, 'g', 0, 'ProvOLD', 0)""",
                    (sol_num, codigo_mp))

    try:
        # Acción usuario: PATCH cambia proveedor + precio
        r = cs.patch(f'/api/solicitudes-compra/{sol_num}/items',
                     json={'items': [{
                         'id': item_id,
                         'proveedor': 'ProvNEW',
                         'precio_unit_g': 0.05,  # 0.05 g/g = $50/kg
                     }]},
                     headers=csrf_headers())
        assert r.status_code == 200, f'PATCH fallo: {r.data}'

        # Verificación 1: maestro_mps.proveedor sincronizado
        rows = _query("SELECT proveedor, precio_referencia FROM maestro_mps WHERE codigo_mp=?",
                      (codigo_mp,))
        assert rows[0][0] == 'ProvNEW', \
            f'BUG: maestro_mps.proveedor no sincronizó · got {rows[0][0]}'
        assert abs(rows[0][1] - 50.0) < 0.01, \
            f'BUG: precio_referencia debe ser 50 (0.05*1000), got {rows[0][1]}'

        # Verificación 2: mp_lead_time_config creado/sincronizado
        rows = _query("""SELECT proveedor_principal FROM mp_lead_time_config
                         WHERE material_id=?""", (codigo_mp,))
        assert rows, 'BUG: mp_lead_time_config row no se creó (sync falló)'
        assert rows[0][0] == 'ProvNEW', \
            f'BUG: mp_lead_time_config.proveedor_principal no sincronizó · got {rows[0][0]}'
    finally:
        _exec("DELETE FROM solicitudes_compra_items WHERE numero=?", (sol_num,))
        _exec("DELETE FROM solicitudes_compra WHERE numero=?", (sol_num,))
        _exec("DELETE FROM maestro_mps WHERE codigo_mp=?", (codigo_mp,))
        try:
            _exec("DELETE FROM mp_lead_time_config WHERE material_id=?", (codigo_mp,))
        except sqlite3.OperationalError:
            pass


# ═══════════════════════════════════════════════════════════════════
# GOLDEN PATH 4 · Limpiar duplicados RESPETA guard inicio/descontado
# ═══════════════════════════════════════════════════════════════════
# Bug que cazaría: si el endpoint borra una producción ya iniciada o
# descontada, corrompe inventario. El guard debe protegerla.

def test_golden_limpiar_duplicados_respeta_guard(app, db_clean):
    cs = _login(app, 'sebastian')

    producto = 'GP4-PROD-DUP'
    # 2 producciones duplicadas (mismo producto + mismas lotes)
    pid_keep = _exec("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, cantidad_kg, origen)
        VALUES (?, date('now', '+3 days'), 2, 'pendiente', 20, 'manual')
    """, (producto,))
    pid_clone = _exec("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, cantidad_kg, origen)
        VALUES (?, date('now', '+5 days'), 2, 'pendiente', 20, 'manual')
    """, (producto,))
    # 3a producción duplicada YA INICIADA (debe protegerse)
    pid_iniciada = _exec("""
        INSERT INTO produccion_programada
          (producto, fecha_programada, lotes, estado, cantidad_kg, origen,
           inicio_real_at)
        VALUES (?, date('now', '+4 days'), 2, 'pendiente', 20, 'manual',
                datetime('now'))
    """, (producto,))

    try:
        # Acción usuario: limpiar duplicados
        r = cs.post('/api/programacion/limpiar-duplicados-producciones',
                    json={'dry_run': False, 'horizonte_dias': 30},
                    headers=csrf_headers())
        assert r.status_code == 200, f'limpiar fallo: {r.data}'

        # Verificación CRÍTICA: la iniciada NO debe haberse borrado
        rows = _query("SELECT COUNT(*) FROM produccion_programada WHERE id=?",
                      (pid_iniciada,))
        assert rows[0][0] == 1, \
            f'CRÍTICO: limpiar-duplicados borró producción ya INICIADA (id={pid_iniciada}) · ' \
            'esto corrompe inventario en curso'

        # Al menos una de las pendientes debe sobrevivir (la más temprana)
        rows = _query("""SELECT COUNT(*) FROM produccion_programada
                         WHERE producto=? AND COALESCE(inicio_real_at,'')=''""",
                      (producto,))
        assert rows[0][0] >= 1, \
            'limpiar-duplicados borró TODAS las pendientes · debe conservar al menos una'
    finally:
        _exec("DELETE FROM produccion_programada WHERE producto=?", (producto,))


# ═══════════════════════════════════════════════════════════════════
# GOLDEN PATH 5 · 3 fuentes SOL filtran correctamente
# ═══════════════════════════════════════════════════════════════════
# Bug que cazaría: Catalina veía SOLs de planta mezcladas en tab
# "Solicitudes" cuando solo deberían aparecer en tab "Planta".

def test_golden_3_fuentes_solicitudes_no_se_mezclan(app, db_clean):
    cs = _login(app, 'catalina')

    sols = [
        ('GP5-PLANTA-MP', 'Materia Prima'),
        ('GP5-PLANTA-EMP', 'Empaque'),
        ('GP5-USUARIO-PAP', 'Papelería/Oficina'),
        ('GP5-USUARIO-EPP', 'EPP'),
        ('GP5-INFLUENCER', 'Influencer/Marketing Digital'),
        ('GP5-CC', 'Cuenta de Cobro'),
    ]
    for num, cat in sols:
        _exec("""INSERT OR REPLACE INTO solicitudes_compra
                  (numero, fecha, estado, solicitante, urgencia, observaciones,
                   area, empresa, categoria, tipo)
                  VALUES (?, date('now'), 'Pendiente', 'test', 'Normal', '',
                          'Test', 'Espagiria', ?, 'Compra')""", (num, cat))

    try:
        # Tab "Planta" → solo MP + Empaque
        r = cs.get('/api/solicitudes-compra?fuente=planta')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'GP5-PLANTA-MP' in nums and 'GP5-PLANTA-EMP' in nums, \
            'Tab Planta debe incluir MP y Empaque'
        assert 'GP5-USUARIO-PAP' not in nums, \
            'BUG: Papelería NO debe aparecer en tab Planta (Catalina se confunde)'
        assert 'GP5-INFLUENCER' not in nums, \
            'BUG: Influencer NO debe aparecer en tab Planta'
        assert 'GP5-CC' not in nums, \
            'BUG: CC NO debe aparecer en tab Planta'

        # Tab "Solicitudes" (usuarios) → ni planta ni influencers
        r = cs.get('/api/solicitudes-compra?fuente=usuarios')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'GP5-USUARIO-PAP' in nums and 'GP5-USUARIO-EPP' in nums
        assert 'GP5-PLANTA-MP' not in nums, \
            'BUG: planta NO debe aparecer en tab Solicitudes (este era el bug original)'
        assert 'GP5-INFLUENCER' not in nums, \
            'BUG: influencer NO debe aparecer en tab Solicitudes'

        # Tab "Influencers" → solo Marketing + CC
        r = cs.get('/api/solicitudes-compra?fuente=influencers')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'GP5-INFLUENCER' in nums and 'GP5-CC' in nums
        assert 'GP5-PLANTA-MP' not in nums, \
            'BUG: planta NO debe aparecer en tab Influencers'
        assert 'GP5-USUARIO-PAP' not in nums, \
            'BUG: usuario NO debe aparecer en tab Influencers'
    finally:
        for num, _ in sols:
            _exec("DELETE FROM solicitudes_compra_items WHERE numero=?", (num,))
            _exec("DELETE FROM solicitudes_compra WHERE numero=?", (num,))
