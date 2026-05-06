"""Tests para la separación de 3 fuentes de SOLs en Compras.

Sebastián 5-may-2026: Catalina recibe solicitudes de 3 frentes:
  · Planta (calendario producción) — categoria 'Materia Prima'/'Empaque'
  · Usuarios (modulo /solicitudes) — Papelería, Servicios, EPP, etc.
  · Influencers (Marketing/Cuenta de Cobro) — flujo de pago directo

Backend cubre:
  · GET /api/solicitudes-compra?fuente=usuarios|planta|influencers
  · GET /api/compras/solicitudes-agrupadas-por-proveedor?fuente=planta
  · PATCH /api/solicitudes-compra/<num>/items con sync global a
    maestro_mps + mp_lead_time_config + precio_referencia
  · POST /api/compras/limpiar-solicitudes-planta (dry_run + ejecutar)
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='catalina'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_sol(numero, categoria, estado='Pendiente', numero_oc='', solicitante='test',
              items=None, urgencia='Normal'):
    """Inserta una SOL + items."""
    conn = sqlite3.connect(os.environ['DB_PATH'])
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO solicitudes_compra
          (numero, fecha, estado, solicitante, urgencia, observaciones,
           area, empresa, categoria, tipo, numero_oc)
        VALUES (?, date('now'), ?, ?, ?, '', 'Test', 'Espagiria', ?, 'Compra', ?)
    """, (numero, estado, solicitante, urgencia, categoria, numero_oc))
    if items:
        for it in items:
            try:
                c.execute("""
                    INSERT INTO solicitudes_compra_items
                      (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                       valor_estimado, proveedor_sugerido, precio_unit_g)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (numero, it.get('codigo_mp', ''), it.get('nombre_mp', ''),
                      it.get('cantidad_g', 0), it.get('unidad', 'g'),
                      it.get('valor_estimado', 0),
                      it.get('proveedor_sugerido', ''),
                      it.get('precio_unit_g', 0)))
            except sqlite3.OperationalError:
                # esquema viejo sin proveedor_sugerido / precio_unit_g
                c.execute("""
                    INSERT INTO solicitudes_compra_items
                      (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                       valor_estimado)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (numero, it.get('codigo_mp', ''), it.get('nombre_mp', ''),
                      it.get('cantidad_g', 0), it.get('unidad', 'g'),
                      it.get('valor_estimado', 0)))
    conn.commit(); conn.close()


def _cleanup_sols(numeros):
    if not numeros:
        return
    conn = sqlite3.connect(os.environ['DB_PATH'])
    ph = ','.join(['?'] * len(numeros))
    conn.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({ph})", numeros)
    conn.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({ph})", numeros)
    conn.commit(); conn.close()


def _cleanup_mps(codigos):
    if not codigos:
        return
    conn = sqlite3.connect(os.environ['DB_PATH'])
    ph = ','.join(['?'] * len(codigos))
    conn.execute(f"DELETE FROM maestro_mps WHERE codigo_mp IN ({ph})", codigos)
    try:
        conn.execute(f"DELETE FROM mp_lead_time_config WHERE material_id IN ({ph})", codigos)
    except sqlite3.OperationalError:
        pass
    conn.commit(); conn.close()


# ── ?fuente= en /api/solicitudes-compra ────────────────────────────


def test_fuente_planta_solo_mp_empaque(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-FNT-MP', 'Materia Prima',
              items=[{'codigo_mp': 'MP1', 'nombre_mp': 'X', 'cantidad_g': 1000}])
    _seed_sol('TEST-FNT-EMP', 'Empaque',
              items=[{'codigo_mp': 'MEE1', 'nombre_mp': 'Y', 'cantidad_g': 100, 'unidad': 'unidades'}])
    _seed_sol('TEST-FNT-PAP', 'Papelería/Oficina',
              items=[{'codigo_mp': '', 'nombre_mp': 'Resma', 'cantidad_g': 1}])
    _seed_sol('TEST-FNT-INF', 'Influencer/Marketing Digital',
              items=[{'codigo_mp': '', 'nombre_mp': 'Pago Mar', 'cantidad_g': 1}])
    try:
        r = cs.get('/api/solicitudes-compra?fuente=planta')
        assert r.status_code == 200
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'TEST-FNT-MP' in nums
        assert 'TEST-FNT-EMP' in nums
        assert 'TEST-FNT-PAP' not in nums
        assert 'TEST-FNT-INF' not in nums
    finally:
        _cleanup_sols(['TEST-FNT-MP', 'TEST-FNT-EMP', 'TEST-FNT-PAP', 'TEST-FNT-INF'])


def test_fuente_usuarios_excluye_planta_e_influencers(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-USR-MP', 'Materia Prima')
    _seed_sol('TEST-USR-PAP', 'Papelería/Oficina')
    _seed_sol('TEST-USR-SVC', 'Servicios')
    _seed_sol('TEST-USR-EPP', 'EPP')
    _seed_sol('TEST-USR-INF', 'Influencer/Marketing Digital')
    _seed_sol('TEST-USR-CC', 'Cuenta de Cobro')
    try:
        r = cs.get('/api/solicitudes-compra?fuente=usuarios')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'TEST-USR-MP' not in nums
        assert 'TEST-USR-INF' not in nums
        assert 'TEST-USR-CC' not in nums
        assert 'TEST-USR-PAP' in nums
        assert 'TEST-USR-SVC' in nums
        assert 'TEST-USR-EPP' in nums
    finally:
        _cleanup_sols(['TEST-USR-MP', 'TEST-USR-PAP', 'TEST-USR-SVC',
                       'TEST-USR-EPP', 'TEST-USR-INF', 'TEST-USR-CC'])


def test_fuente_influencers_solo_marketing_y_cc(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-INF-MK', 'Influencer/Marketing Digital')
    _seed_sol('TEST-INF-CC', 'Cuenta de Cobro')
    _seed_sol('TEST-INF-MP', 'Materia Prima')
    _seed_sol('TEST-INF-PAP', 'Papelería/Oficina')
    try:
        r = cs.get('/api/solicitudes-compra?fuente=influencers')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        assert 'TEST-INF-MK' in nums
        assert 'TEST-INF-CC' in nums
        assert 'TEST-INF-MP' not in nums
        assert 'TEST-INF-PAP' not in nums
    finally:
        _cleanup_sols(['TEST-INF-MK', 'TEST-INF-CC', 'TEST-INF-MP', 'TEST-INF-PAP'])


def test_fuente_sin_param_legacy_compatible(app, db_clean):
    """Sin ?fuente= = comportamiento legacy (todas las categorias)."""
    cs = _login(app, 'catalina')
    _seed_sol('TEST-LEG-MP', 'Materia Prima')
    _seed_sol('TEST-LEG-PAP', 'Papelería/Oficina')
    try:
        r = cs.get('/api/solicitudes-compra')
        nums = {s['numero'] for s in r.get_json()['solicitudes']}
        # Sin filtro = aparecen ambas
        assert 'TEST-LEG-MP' in nums
        assert 'TEST-LEG-PAP' in nums
    finally:
        _cleanup_sols(['TEST-LEG-MP', 'TEST-LEG-PAP'])


# ── /api/compras/solicitudes-agrupadas-por-proveedor?fuente=planta ─


def test_agrupadas_fuente_planta_excluye_otras_categorias(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-AGR-MP', 'Materia Prima',
              items=[{'codigo_mp': 'MP-AGR', 'nombre_mp': 'X', 'cantidad_g': 1000,
                      'proveedor_sugerido': 'ProvAgr', 'valor_estimado': 50000}])
    _seed_sol('TEST-AGR-PAP', 'Papelería/Oficina',
              items=[{'codigo_mp': '', 'nombre_mp': 'Resma', 'cantidad_g': 1,
                      'proveedor_sugerido': 'ProvPap', 'valor_estimado': 10000}])
    try:
        r = cs.get('/api/compras/solicitudes-agrupadas-por-proveedor?fuente=planta')
        assert r.status_code == 200
        d = r.get_json()
        all_sols = []
        for g in (d.get('grupos') or []):
            all_sols.extend([s['numero'] for s in g.get('solicitudes', [])])
        for s in (d.get('sin_proveedor') or []):
            for sub in s.get('solicitudes', []):
                all_sols.append(sub['numero'])
        assert 'TEST-AGR-MP' in all_sols
        assert 'TEST-AGR-PAP' not in all_sols
    finally:
        _cleanup_sols(['TEST-AGR-MP', 'TEST-AGR-PAP'])


# ── PATCH sync global ──────────────────────────────────────────────


def test_patch_sol_item_sincroniza_proveedor_global(app, db_clean):
    """Al editar el proveedor de un item en una SOL, debe propagarse a:
       · maestro_mps.proveedor
       · mp_lead_time_config.proveedor_principal
    """
    cs = _login(app, 'catalina')
    # Seed: maestro_mps con proveedor original
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("""
        INSERT OR REPLACE INTO maestro_mps
          (codigo_mp, nombre_comercial, proveedor, activo, tipo_material)
        VALUES (?, ?, ?, 1, 'MP')
    """, ('MP-PATCH-SYNC', 'X-Sync', 'ProvVIEJO'))
    # Borrar mp_lead_time_config si existe (limpieza)
    try:
        conn.execute("DELETE FROM mp_lead_time_config WHERE material_id=?",
                     ('MP-PATCH-SYNC',))
    except sqlite3.OperationalError:
        pass
    conn.commit(); conn.close()
    _seed_sol('TEST-PATCH-SYNC', 'Materia Prima',
              items=[{'codigo_mp': 'MP-PATCH-SYNC', 'nombre_mp': 'X-Sync',
                      'cantidad_g': 5000, 'proveedor_sugerido': 'ProvVIEJO',
                      'precio_unit_g': 0.05, 'valor_estimado': 250.0}])
    # Obtener el item_id
    conn = sqlite3.connect(os.environ['DB_PATH'])
    item_id = conn.execute(
        "SELECT id FROM solicitudes_compra_items WHERE numero=?",
        ('TEST-PATCH-SYNC',)
    ).fetchone()[0]
    conn.close()
    try:
        r = cs.patch('/api/solicitudes-compra/TEST-PATCH-SYNC/items',
                     json={'items': [{
                         'id': item_id,
                         'cantidad_g': 6000,
                         'proveedor': 'ProvNUEVO',
                         'precio_unit_g': 0.10,
                     }]},
                     headers=csrf_headers())
        assert r.status_code == 200, r.data
        # Verificar sync
        conn = sqlite3.connect(os.environ['DB_PATH'])
        prov_mp = conn.execute(
            "SELECT proveedor FROM maestro_mps WHERE codigo_mp=?",
            ('MP-PATCH-SYNC',)
        ).fetchone()
        assert prov_mp[0] == 'ProvNUEVO', f'maestro_mps no se sincronizó: {prov_mp}'
        try:
            prov_lt = conn.execute(
                "SELECT proveedor_principal FROM mp_lead_time_config WHERE material_id=?",
                ('MP-PATCH-SYNC',)
            ).fetchone()
            assert prov_lt is not None, 'mp_lead_time_config no se creó'
            assert prov_lt[0] == 'ProvNUEVO', f'mp_lead_time_config no se sincronizó: {prov_lt}'
        except sqlite3.OperationalError:
            pass  # tabla puede no existir
        conn.close()
    finally:
        _cleanup_sols(['TEST-PATCH-SYNC'])
        _cleanup_mps(['MP-PATCH-SYNC'])


def test_patch_sol_item_sincroniza_precio_referencia(app, db_clean):
    """precio_unit_g (g) * 1000 = precio por kg → maestro_mps.precio_referencia."""
    cs = _login(app, 'catalina')
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("""
        INSERT OR REPLACE INTO maestro_mps
          (codigo_mp, nombre_comercial, proveedor, activo, tipo_material,
           precio_referencia)
        VALUES (?, ?, ?, 1, 'MP', 0)
    """, ('MP-PATCH-PR', 'X-Pr', 'P'))
    conn.commit(); conn.close()
    _seed_sol('TEST-PATCH-PR', 'Materia Prima',
              items=[{'codigo_mp': 'MP-PATCH-PR', 'nombre_mp': 'X-Pr',
                      'cantidad_g': 1000, 'proveedor_sugerido': 'P',
                      'precio_unit_g': 0, 'valor_estimado': 0}])
    conn = sqlite3.connect(os.environ['DB_PATH'])
    item_id = conn.execute(
        "SELECT id FROM solicitudes_compra_items WHERE numero=?",
        ('TEST-PATCH-PR',)
    ).fetchone()[0]
    conn.close()
    try:
        # 0.025 g * 1000 = $25 / kg
        r = cs.patch('/api/solicitudes-compra/TEST-PATCH-PR/items',
                     json={'items': [{'id': item_id, 'precio_unit_g': 0.025}]},
                     headers=csrf_headers())
        assert r.status_code == 200, r.data
        conn = sqlite3.connect(os.environ['DB_PATH'])
        pr = conn.execute(
            "SELECT precio_referencia FROM maestro_mps WHERE codigo_mp=?",
            ('MP-PATCH-PR',)
        ).fetchone()
        conn.close()
        # 0.025 * 1000 = 25
        assert abs((pr[0] or 0) - 25.0) < 0.01, f'precio_referencia esperado 25, got {pr[0]}'
    finally:
        _cleanup_sols(['TEST-PATCH-PR'])
        _cleanup_mps(['MP-PATCH-PR'])


# ── /api/compras/limpiar-solicitudes-planta ────────────────────────


def test_limpiar_planta_dry_run_no_borra(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-LMP-1', 'Materia Prima', estado='Pendiente', numero_oc='')
    _seed_sol('TEST-LMP-2', 'Empaque', estado='Pendiente', numero_oc='')
    try:
        r = cs.post('/api/compras/limpiar-solicitudes-planta',
                    json={'dry_run': True}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['ok'] is True
        # En dry_run el endpoint devuelve `eliminaria` (condicional)
        assert d['dry_run'] is True
        assert d['eliminaria'] >= 2  # incluye las nuestras (puede haber más)
        # NO se borraron en dry_run
        conn = sqlite3.connect(os.environ['DB_PATH'])
        count = conn.execute(
            "SELECT COUNT(*) FROM solicitudes_compra WHERE numero IN (?, ?)",
            ('TEST-LMP-1', 'TEST-LMP-2')
        ).fetchone()[0]
        conn.close()
        assert count == 2, 'dry_run no debe borrar'
    finally:
        _cleanup_sols(['TEST-LMP-1', 'TEST-LMP-2'])


def test_limpiar_planta_ejecuta_y_borra_solo_pendientes_sin_oc(app, db_clean):
    cs = _login(app, 'catalina')
    _seed_sol('TEST-LMP-DEL', 'Materia Prima', estado='Pendiente', numero_oc='')
    _seed_sol('TEST-LMP-KEEP-OC', 'Materia Prima', estado='Pendiente',
              numero_oc='OC-DUMMY')
    _seed_sol('TEST-LMP-KEEP-EST', 'Materia Prima', estado='Aprobada', numero_oc='')
    _seed_sol('TEST-LMP-KEEP-CAT', 'Papelería/Oficina', estado='Pendiente',
              numero_oc='')
    try:
        r = cs.post('/api/compras/limpiar-solicitudes-planta',
                    json={'dry_run': False, 'confirm': True},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['ok'] is True
        # Verificar
        conn = sqlite3.connect(os.environ['DB_PATH'])
        del_row = conn.execute(
            "SELECT 1 FROM solicitudes_compra WHERE numero=?", ('TEST-LMP-DEL',)
        ).fetchone()
        keep_oc = conn.execute(
            "SELECT 1 FROM solicitudes_compra WHERE numero=?", ('TEST-LMP-KEEP-OC',)
        ).fetchone()
        keep_est = conn.execute(
            "SELECT 1 FROM solicitudes_compra WHERE numero=?", ('TEST-LMP-KEEP-EST',)
        ).fetchone()
        keep_cat = conn.execute(
            "SELECT 1 FROM solicitudes_compra WHERE numero=?", ('TEST-LMP-KEEP-CAT',)
        ).fetchone()
        conn.close()
        assert del_row is None, 'TEST-LMP-DEL debió ser borrada'
        assert keep_oc is not None, 'TEST-LMP-KEEP-OC tiene OC, no debe borrarse'
        assert keep_est is not None, 'TEST-LMP-KEEP-EST está Aprobada, no debe borrarse'
        assert keep_cat is not None, 'TEST-LMP-KEEP-CAT no es planta, no debe borrarse'
    finally:
        _cleanup_sols(['TEST-LMP-DEL', 'TEST-LMP-KEEP-OC',
                       'TEST-LMP-KEEP-EST', 'TEST-LMP-KEEP-CAT'])


def test_limpiar_planta_sin_login_401(client):
    r = client.post('/api/compras/limpiar-solicitudes-planta',
                    json={'dry_run': True}, headers=csrf_headers())
    assert r.status_code == 401


# ── HTML expone tabs ───────────────────────────────────────────────


def test_compras_html_tab_planta_visible(app, db_clean):
    cs = _login(app, 'catalina')
    body = cs.get('/compras').get_data(as_text=True)
    assert 'data-tab="planta"' in body
    assert 'pane-planta' in body
    assert 'loadPlanta' in body
    assert 'limpiarSolsPlantaLegacy' in body
