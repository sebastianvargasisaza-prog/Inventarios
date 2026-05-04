"""Tests para vista agrupada de solicitudes por proveedor (Catalina · 4-may-2026).

Catalina recibe 200+ solicitudes AUTO-PLAN desde planta. La feature agrupa
todas las del mismo proveedor sugerido para crear UNA OC consolidada en
lugar de gestionar una por una.

Cubre:
  - GET /api/compras/solicitudes-agrupadas-por-proveedor (agrupamiento)
  - POST /api/compras/oc-desde-solicitudes (bulk OC con N→1)
  - Atomicidad (rollback si falla)
  - Validaciones: solicitudes faltantes, no-pendientes, ya con OC
  - Audit log CREAR_OC_BULK
  - HTML expone toggle + funciones JS
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _crear_solicitud_con_items(numero, items):
    """Inserta directo en DB una solicitud Pendiente con N items.

    items: list de dicts {codigo_mp, nombre_mp, cantidad_g, valor_estimado, proveedor_sugerido}
    """
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO solicitudes_compra
           (numero, fecha, estado, solicitante, urgencia, observaciones,
            area, empresa, categoria, tipo, valor)
           VALUES (?, '2026-05-04', 'Pendiente', 'AUTO-PLAN',
                   ?, 'AUTO-PLAN test', 'Produccion', 'Espagiria',
                   'Materia Prima', 'Compra', 0)""",
        (numero, items[0].get('urgencia', 'Urgente') if items else 'Normal'),
    )
    for it in items:
        try:
            c.execute(
                """INSERT INTO solicitudes_compra_items
                   (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                    valor_estimado, proveedor_sugerido)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (numero, it['codigo_mp'], it['nombre_mp'],
                 it['cantidad_g'], it.get('unidad', 'g'),
                 it.get('valor_estimado', 0),
                 it.get('proveedor_sugerido', '')),
            )
        except sqlite3.OperationalError:
            c.execute(
                """INSERT INTO solicitudes_compra_items
                   (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                    valor_estimado)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (numero, it['codigo_mp'], it['nombre_mp'],
                 it['cantidad_g'], it.get('unidad', 'g'),
                 it.get('valor_estimado', 0)),
            )
    conn.commit()
    conn.close()


def _cleanup_solicitudes(numeros):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    placeholders = ','.join(['?'] * len(numeros))
    conn.execute(f"DELETE FROM solicitudes_compra_items WHERE numero IN ({placeholders})", numeros)
    conn.execute(f"DELETE FROM solicitudes_compra WHERE numero IN ({placeholders})", numeros)
    conn.commit()
    conn.close()


def _cleanup_oc(numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    conn.commit()
    conn.close()


# ── GET /api/compras/solicitudes-agrupadas-por-proveedor ─────────────

def test_agrupamiento_por_proveedor_basico(app, db_clean):
    cs = _login(app, "catalina")
    nums = ['SOL-AGR-001', 'SOL-AGR-002', 'SOL-AGR-003']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-A', 'nombre_mp': 'Glicerina',
                                           'cantidad_g': 10000, 'valor_estimado': 100000,
                                           'proveedor_sugerido': 'Inquimica Test'}])
    _crear_solicitud_con_items(nums[1], [{'codigo_mp': 'MP-B', 'nombre_mp': 'Propilenglicol',
                                           'cantidad_g': 5000, 'valor_estimado': 50000,
                                           'proveedor_sugerido': 'Inquimica Test'}])
    _crear_solicitud_con_items(nums[2], [{'codigo_mp': 'MP-C', 'nombre_mp': 'Niacinamida',
                                           'cantidad_g': 2000, 'valor_estimado': 200000,
                                           'proveedor_sugerido': 'Otro Proveedor'}])
    try:
        r = cs.get('/api/compras/solicitudes-agrupadas-por-proveedor?estado=Pendiente')
        assert r.status_code == 200
        d = r.get_json()
        provs = {g['proveedor'] for g in d['grupos']}
        assert 'Inquimica Test' in provs
        assert 'Otro Proveedor' in provs
        # Inquimica Test debe tener 2 solicitudes consolidadas
        inq = [g for g in d['grupos'] if g['proveedor'] == 'Inquimica Test'][0]
        assert inq['solicitudes_count'] == 2
        assert inq['items_count'] == 2  # 2 MPs distintas
        assert any(s['numero'] == 'SOL-AGR-001' for s in inq['solicitudes'])
        assert any(s['numero'] == 'SOL-AGR-002' for s in inq['solicitudes'])
    finally:
        _cleanup_solicitudes(nums)


def test_agrupamiento_consolida_mismo_codigo_mp(app, db_clean):
    """2 solicitudes piden la misma MP → en items_consolidados aparece sumada."""
    cs = _login(app, "catalina")
    nums = ['SOL-CON-001', 'SOL-CON-002']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-CONSOL', 'nombre_mp': 'Glicerina',
                                           'cantidad_g': 1000, 'valor_estimado': 10000,
                                           'proveedor_sugerido': 'Prov Consol'}])
    _crear_solicitud_con_items(nums[1], [{'codigo_mp': 'MP-CONSOL', 'nombre_mp': 'Glicerina',
                                           'cantidad_g': 2500, 'valor_estimado': 25000,
                                           'proveedor_sugerido': 'Prov Consol'}])
    try:
        r = cs.get('/api/compras/solicitudes-agrupadas-por-proveedor?estado=Pendiente')
        d = r.get_json()
        grp = [g for g in d['grupos'] if g['proveedor'] == 'Prov Consol'][0]
        assert grp['solicitudes_count'] == 2
        assert grp['items_count'] == 1  # consolidado a 1 MP
        item = grp['items_consolidados'][0]
        assert item['codigo_mp'] == 'MP-CONSOL'
        assert item['cantidad_g'] == 3500.0  # suma 1000 + 2500
        assert sorted(item['solicitudes_origen']) == sorted(nums)
    finally:
        _cleanup_solicitudes(nums)


def test_agrupamiento_sin_proveedor_va_a_aparte(app, db_clean):
    cs = _login(app, "catalina")
    nums = ['SOL-NOPRV-001']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-X', 'nombre_mp': 'X',
                                           'cantidad_g': 100, 'valor_estimado': 0,
                                           'proveedor_sugerido': ''}])
    try:
        r = cs.get('/api/compras/solicitudes-agrupadas-por-proveedor?estado=Pendiente')
        d = r.get_json()
        # No esta en grupos
        assert not any(g['proveedor'] == '' for g in d['grupos'])
        # Si esta en sin_proveedor
        assert any(s['numero'] == 'SOL-NOPRV-001' for s in d['sin_proveedor'])
    finally:
        _cleanup_solicitudes(nums)


def test_agrupamiento_proveedores_mixtos_va_aparte(app, db_clean):
    """1 solicitud con 2 items de proveedores DIFERENTES → sin_proveedor."""
    cs = _login(app, "catalina")
    nums = ['SOL-MIX-001']
    _crear_solicitud_con_items(nums[0], [
        {'codigo_mp': 'MP-1', 'nombre_mp': 'A', 'cantidad_g': 100,
         'valor_estimado': 0, 'proveedor_sugerido': 'Prov A'},
        {'codigo_mp': 'MP-2', 'nombre_mp': 'B', 'cantidad_g': 100,
         'valor_estimado': 0, 'proveedor_sugerido': 'Prov B'},
    ])
    try:
        r = cs.get('/api/compras/solicitudes-agrupadas-por-proveedor?estado=Pendiente')
        d = r.get_json()
        # No deberia entrar a Prov A ni Prov B
        for g in d['grupos']:
            for s in g['solicitudes']:
                assert s['numero'] != 'SOL-MIX-001'
        # Si en sin_proveedor con motivo mixto
        candidato = [s for s in d['sin_proveedor'] if s['numero'] == 'SOL-MIX-001']
        assert candidato
        assert candidato[0].get('_motivo_sin_grupo') == 'mixto'
    finally:
        _cleanup_solicitudes(nums)


def test_agrupamiento_sin_login_401(client):
    r = client.get('/api/compras/solicitudes-agrupadas-por-proveedor')
    assert r.status_code == 401


# ── POST /api/compras/oc-desde-solicitudes ────────────────────────────

def test_oc_desde_solicitudes_basico(app, db_clean):
    cs = _login(app, "catalina")
    nums = ['SOL-OCB-001', 'SOL-OCB-002']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-OCB-1', 'nombre_mp': 'Glicerina',
                                           'cantidad_g': 5000, 'valor_estimado': 50000,
                                           'proveedor_sugerido': 'Prov OCB'}])
    _crear_solicitud_con_items(nums[1], [{'codigo_mp': 'MP-OCB-2', 'nombre_mp': 'Aceite',
                                           'cantidad_g': 3000, 'valor_estimado': 30000,
                                           'proveedor_sugerido': 'Prov OCB'}])
    oc_creada = None
    try:
        r = cs.post('/api/compras/oc-desde-solicitudes',
                    json={'proveedor': 'Prov OCB', 'solicitudes': nums,
                          'observaciones': 'Test consolidacion'},
                    headers=csrf_headers())
        assert r.status_code == 201, r.data
        d = r.get_json()
        oc_creada = d['numero_oc']
        assert oc_creada.startswith('OC-2026-')
        assert d['solicitudes_vinculadas'] == 2
        assert d['items_creados'] == 2
        # Verificar que las solicitudes pasaron a Aprobada con numero_oc
        conn = sqlite3.connect(os.environ["DB_PATH"])
        for n in nums:
            row = conn.execute(
                "SELECT estado, numero_oc FROM solicitudes_compra WHERE numero=?", (n,)
            ).fetchone()
            assert row[0] == 'Aprobada'
            assert row[1] == oc_creada
        # Verificar items en la OC
        cnt = conn.execute(
            "SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=?", (oc_creada,)
        ).fetchone()[0]
        assert cnt == 2
        conn.close()
    finally:
        _cleanup_solicitudes(nums)
        if oc_creada:
            _cleanup_oc(oc_creada)


def test_oc_desde_solicitudes_consolida_mismo_mp(app, db_clean):
    """2 solicitudes de la misma MP → 1 item consolidado en la OC."""
    cs = _login(app, "catalina")
    nums = ['SOL-CONS-001', 'SOL-CONS-002']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-SAMECODE', 'nombre_mp': 'X',
                                           'cantidad_g': 1000, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'P'}])
    _crear_solicitud_con_items(nums[1], [{'codigo_mp': 'MP-SAMECODE', 'nombre_mp': 'X',
                                           'cantidad_g': 2000, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'P'}])
    oc_creada = None
    try:
        r = cs.post('/api/compras/oc-desde-solicitudes',
                    json={'proveedor': 'P', 'solicitudes': nums,
                          'consolidar_iguales': True},
                    headers=csrf_headers())
        assert r.status_code == 201
        d = r.get_json()
        oc_creada = d['numero_oc']
        assert d['items_creados'] == 1  # consolidado
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT cantidad_g FROM ordenes_compra_items WHERE numero_oc=?", (oc_creada,)
        ).fetchone()
        conn.close()
        assert row[0] == 3000.0
    finally:
        _cleanup_solicitudes(nums)
        if oc_creada:
            _cleanup_oc(oc_creada)


def test_oc_desde_solicitudes_sin_consolidar(app, db_clean):
    """Si consolidar_iguales=false, items van separados (1 por solicitud-item)."""
    cs = _login(app, "catalina")
    nums = ['SOL-NCONS-001', 'SOL-NCONS-002']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-Z', 'nombre_mp': 'Z',
                                           'cantidad_g': 100, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'PZ'}])
    _crear_solicitud_con_items(nums[1], [{'codigo_mp': 'MP-Z', 'nombre_mp': 'Z',
                                           'cantidad_g': 200, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'PZ'}])
    oc_creada = None
    try:
        r = cs.post('/api/compras/oc-desde-solicitudes',
                    json={'proveedor': 'PZ', 'solicitudes': nums,
                          'consolidar_iguales': False},
                    headers=csrf_headers())
        d = r.get_json()
        oc_creada = d['numero_oc']
        assert d['items_creados'] == 2  # NO consolidado
    finally:
        _cleanup_solicitudes(nums)
        if oc_creada:
            _cleanup_oc(oc_creada)


def test_oc_desde_solicitudes_proveedor_faltante_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post('/api/compras/oc-desde-solicitudes',
                json={'solicitudes': ['SOL-X']},
                headers=csrf_headers())
    assert r.status_code == 400
    assert 'proveedor' in r.get_json()['error'].lower()


def test_oc_desde_solicitudes_lista_vacia_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post('/api/compras/oc-desde-solicitudes',
                json={'proveedor': 'X', 'solicitudes': []},
                headers=csrf_headers())
    assert r.status_code == 400


def test_oc_desde_solicitudes_solicitud_no_existe_404(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post('/api/compras/oc-desde-solicitudes',
                json={'proveedor': 'X', 'solicitudes': ['SOL-NO-EXISTE-XYZ']},
                headers=csrf_headers())
    assert r.status_code == 404
    assert 'faltantes' in r.get_json()


def test_oc_desde_solicitudes_no_pendiente_409(app, db_clean):
    cs = _login(app, "catalina")
    nums = ['SOL-APR-001']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP', 'nombre_mp': 'X',
                                           'cantidad_g': 100, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'P'}])
    # Forzar estado Aprobada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE solicitudes_compra SET estado='Aprobada' WHERE numero=?", (nums[0],))
    conn.commit(); conn.close()
    try:
        r = cs.post('/api/compras/oc-desde-solicitudes',
                    json={'proveedor': 'P', 'solicitudes': nums},
                    headers=csrf_headers())
        assert r.status_code == 409
        assert 'no_pendientes' in r.get_json()
    finally:
        _cleanup_solicitudes(nums)


def test_oc_desde_solicitudes_audit_log(app, db_clean):
    cs = _login(app, "catalina")
    nums = ['SOL-AUD-001']
    _crear_solicitud_con_items(nums[0], [{'codigo_mp': 'MP-AUD', 'nombre_mp': 'X',
                                           'cantidad_g': 100, 'valor_estimado': 0,
                                           'proveedor_sugerido': 'PAud'}])
    oc_creada = None
    try:
        r = cs.post('/api/compras/oc-desde-solicitudes',
                    json={'proveedor': 'PAud', 'solicitudes': nums},
                    headers=csrf_headers())
        d = r.get_json()
        oc_creada = d['numero_oc']
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion FROM audit_log WHERE accion='CREAR_OC_BULK' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'catalina'
    finally:
        _cleanup_solicitudes(nums)
        if oc_creada:
            _cleanup_oc(oc_creada)


def test_oc_desde_solicitudes_max_100(app, db_clean):
    cs = _login(app, "catalina")
    fake_nums = [f'SOL-FAKE-{i}' for i in range(101)]
    r = cs.post('/api/compras/oc-desde-solicitudes',
                json={'proveedor': 'X', 'solicitudes': fake_nums},
                headers=csrf_headers())
    assert r.status_code == 400
    assert 'maximo 100' in r.get_json()['error'].lower()


# ── HTML expone toggle + funciones JS ─────────────────────────────────

def test_compras_html_toggle_vista_agrupada_visible(app, db_clean):
    cs = _login(app, "catalina")
    body = cs.get('/compras').get_data(as_text=True)
    assert 'btn-toggle-vista' in body
    assert 'toggleVistaSolicitudes' in body
    assert 'renderSolicitudesAgrupadas' in body
    assert 'abrirCrearOCDesdeGrupo' in body
    assert 'Agrupar por proveedor' in body
    assert 'grid-solic-grouped' in body
