"""Tests de consolidacion AUTO-XXXX por proveedor (Catalina · 4-may-2026).

Antes: aplicar_plan() iteraba plan['compras_propuestas'] y creaba 1
solicitud AUTO-XXXX por cada MP en deficit. Catalina recibia 200+
cards.

Ahora: agrupa por (proveedor, categoria) y crea 1 AUTO-XXXX por grupo
con N items dentro. Misma data, ~10x menos cards en compras.
"""
import os
import sqlite3
import sys

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _make_plan(compras_propuestas, fecha_hoy='2026-05-04'):
    """Construye un plan minimo (solo lo que necesita aplicar_plan)."""
    return {
        'producciones_propuestas': [],
        'compras_propuestas': compras_propuestas,
        'conteos_propuestos': [],
        'alertas': [],
        'log': [],
        'duracion_ms': 1,
        'horizonte_dias': 60,
        'fecha_hoy': fecha_hoy,
        'fecha_fin': '2026-07-04',
    }


def _cleanup_auto_solicitudes():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        "DELETE FROM solicitudes_compra_items WHERE numero IN "
        "(SELECT numero FROM solicitudes_compra WHERE numero LIKE 'AUTO-%')"
    )
    conn.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'AUTO-%'")
    conn.commit()
    conn.close()


def _ensure_api_path():
    api_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "api",
    )
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


# ── Consolidacion AUTO-XXXX por (proveedor, categoria) ───────────────


def test_aplicar_plan_consolida_5_mps_de_2_proveedores_en_2_solicitudes(app, db_clean):
    """5 MPs en deficit, 3 de proveedor A + 2 de proveedor B → 2 AUTO-XXXX."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    compras = [
        {'material_id': 'MP1', 'material_nombre': 'Glicerina',
         'requerido_g': 10000, 'stock_actual_g': 1000, 'deficit_g': 9000,
         'cantidad_a_pedir_g': 12000, 'lead_time_dias': 14, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'Inquimica', 'urgencia': 'alta'},
        {'material_id': 'MP2', 'material_nombre': 'Propilenglicol',
         'requerido_g': 5000, 'stock_actual_g': 500, 'deficit_g': 4500,
         'cantidad_a_pedir_g': 6000, 'lead_time_dias': 14, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'Inquimica', 'urgencia': 'normal'},
        {'material_id': 'MP3', 'material_nombre': 'Niacinamida',
         'requerido_g': 2000, 'stock_actual_g': 100, 'deficit_g': 1900,
         'cantidad_a_pedir_g': 2500, 'lead_time_dias': 90, 'origen': 'china',
         'es_envase': False, 'proveedor_principal': 'Inquimica', 'urgencia': 'critica'},
        {'material_id': 'MP4', 'material_nombre': 'Aerosil',
         'requerido_g': 800, 'stock_actual_g': 0, 'deficit_g': 800,
         'cantidad_a_pedir_g': 1000, 'lead_time_dias': 30, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'Quimicos SA', 'urgencia': 'critica'},
        {'material_id': 'MP5', 'material_nombre': 'Acido tranexamico',
         'requerido_g': 500, 'stock_actual_g': 50, 'deficit_g': 450,
         'cantidad_a_pedir_g': 600, 'lead_time_dias': 30, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'Quimicos SA', 'urgencia': 'normal'},
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        assert len(res['compras_creadas']) == 2, \
            f"Esperaba 2 solicitudes consolidadas, llegaron {len(res['compras_creadas'])}"
        # Cada uno debe tener su proveedor
        provs = sorted([c['proveedor'] for c in res['compras_creadas']])
        assert provs == ['Inquimica', 'Quimicos SA']
        # Inquimica tiene 3 items, Quimicos 2
        inq = [c for c in res['compras_creadas'] if c['proveedor'] == 'Inquimica'][0]
        qmc = [c for c in res['compras_creadas'] if c['proveedor'] == 'Quimicos SA'][0]
        assert inq['items_count'] == 3
        assert qmc['items_count'] == 2

        # Verificar en DB
        conn = sqlite3.connect(os.environ["DB_PATH"])
        rows_inq = conn.execute(
            "SELECT codigo_mp, cantidad_g, proveedor_sugerido FROM solicitudes_compra_items "
            "WHERE numero=?", (inq['numero'],)
        ).fetchall()
        conn.close()
        assert len(rows_inq) == 3
        assert all(r[2] == 'Inquimica' for r in rows_inq)
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_urgencia_max_por_grupo(app, db_clean):
    """En un grupo con MP critica + alta + normal, urgencia_solicitud = Urgente."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    compras = [
        {'material_id': 'A', 'material_nombre': 'A', 'requerido_g': 100,
         'stock_actual_g': 0, 'deficit_g': 100, 'cantidad_a_pedir_g': 200,
         'lead_time_dias': 10, 'origen': 'local', 'es_envase': False,
         'proveedor_principal': 'PX', 'urgencia': 'normal'},
        {'material_id': 'B', 'material_nombre': 'B', 'requerido_g': 100,
         'stock_actual_g': 0, 'deficit_g': 100, 'cantidad_a_pedir_g': 200,
         'lead_time_dias': 10, 'origen': 'china', 'es_envase': False,
         'proveedor_principal': 'PX', 'urgencia': 'critica'},
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        assert len(res['compras_creadas']) == 1
        numero = res['compras_creadas'][0]['numero']
        conn = sqlite3.connect(os.environ["DB_PATH"])
        urg = conn.execute(
            "SELECT urgencia FROM solicitudes_compra WHERE numero=?", (numero,)
        ).fetchone()[0]
        conn.close()
        assert urg == 'Urgente', f"Esperaba Urgente (critica gana), llegado {urg}"
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_separa_mp_y_empaque_aunque_mismo_proveedor(app, db_clean):
    """MP + Empaque del mismo proveedor → 2 solicitudes (categoria distinta)."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    compras = [
        {'material_id': 'MP-A', 'material_nombre': 'Glicerina',
         'requerido_g': 1000, 'stock_actual_g': 0, 'deficit_g': 1000,
         'cantidad_a_pedir_g': 1500, 'lead_time_dias': 14, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'Mismo Prov', 'urgencia': 'normal'},
        {'material_id': 'MEE-1', 'material_nombre': 'Frasco 50ml',
         'requerido_g': 500, 'stock_actual_g': 0, 'deficit_g': 500,
         'cantidad_a_pedir_g': 600, 'lead_time_dias': 30, 'origen': 'local',
         'es_envase': True, 'proveedor_principal': 'Mismo Prov', 'urgencia': 'normal'},
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        assert len(res['compras_creadas']) == 2
        # Ambas son 'Mismo Prov' pero categorias diferentes
        conn = sqlite3.connect(os.environ["DB_PATH"])
        nums = [c['numero'] for c in res['compras_creadas']]
        cats = sorted([
            conn.execute("SELECT categoria FROM solicitudes_compra WHERE numero=?", (n,)).fetchone()[0]
            for n in nums
        ])
        conn.close()
        # alpha sort: 'Materia Prima' < 'Material de Empaque' (a<l en pos 7)
        assert sorted(cats) == sorted(['Materia Prima', 'Material de Empaque'])
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_sin_proveedor_principal_va_a_grupo_vacio(app, db_clean):
    """MPs sin proveedor_principal → 1 solicitud con proveedor=''."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    compras = [
        {'material_id': 'X', 'material_nombre': 'X', 'requerido_g': 100,
         'stock_actual_g': 0, 'deficit_g': 100, 'cantidad_a_pedir_g': 100,
         'lead_time_dias': 10, 'origen': 'local', 'es_envase': False,
         'proveedor_principal': None, 'urgencia': 'normal'},
        {'material_id': 'Y', 'material_nombre': 'Y', 'requerido_g': 100,
         'stock_actual_g': 0, 'deficit_g': 100, 'cantidad_a_pedir_g': 100,
         'lead_time_dias': 10, 'origen': 'local', 'es_envase': False,
         'proveedor_principal': '', 'urgencia': 'normal'},
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        # Ambos sin proveedor → 1 solicitud
        assert len(res['compras_creadas']) == 1
        assert res['compras_creadas'][0]['items_count'] == 2
        # observaciones debe decir "(Sin proveedor sugerido)"
        conn = sqlite3.connect(os.environ["DB_PATH"])
        obs = conn.execute(
            "SELECT observaciones FROM solicitudes_compra WHERE numero=?",
            (res['compras_creadas'][0]['numero'],)
        ).fetchone()[0]
        conn.close()
        assert 'Sin proveedor sugerido' in obs
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_observacion_resumen_top3(app, db_clean):
    """Observacion debe tener resumen top-3 por deficit."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    # 5 MPs ordenadas por deficit DESC: A(9000), B(5000), C(2000), D(800), E(450)
    compras = [
        {'material_id': f'M{i}', 'material_nombre': f'Mat{i}',
         'requerido_g': 100, 'stock_actual_g': 0, 'deficit_g': d,
         'cantidad_a_pedir_g': d * 1.2, 'lead_time_dias': 10, 'origen': 'local',
         'es_envase': False, 'proveedor_principal': 'P1', 'urgencia': 'normal'}
        for i, d in enumerate([9000, 5000, 2000, 800, 450])
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        assert len(res['compras_creadas']) == 1
        conn = sqlite3.connect(os.environ["DB_PATH"])
        obs = conn.execute(
            "SELECT observaciones FROM solicitudes_compra WHERE numero=?",
            (res['compras_creadas'][0]['numero'],)
        ).fetchone()[0]
        conn.close()
        # Mat0 (9000) debe estar primero, Mat4 NO debe estar (top 3)
        assert 'Mat0' in obs and 'Mat1' in obs and 'Mat2' in obs
        # +2 mas
        assert '+2 mas' in obs
        # Total proveedor + cantidad
        assert 'P1' in obs and 'MPs' in obs
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_items_persisten_proveedor_sugerido(app, db_clean):
    """Cada item creado bajo la consolidacion debe llevar proveedor_sugerido
    igual al proveedor del grupo (asi `solicitudes-agrupadas-por-proveedor`
    sigue funcionando)."""
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    compras = [
        {'material_id': 'CMP-1', 'material_nombre': 'Mat1', 'requerido_g': 100,
         'stock_actual_g': 0, 'deficit_g': 100, 'cantidad_a_pedir_g': 100,
         'lead_time_dias': 14, 'origen': 'local', 'es_envase': False,
         'proveedor_principal': 'ProvX', 'urgencia': 'normal'},
        {'material_id': 'CMP-2', 'material_nombre': 'Mat2', 'requerido_g': 200,
         'stock_actual_g': 0, 'deficit_g': 200, 'cantidad_a_pedir_g': 200,
         'lead_time_dias': 14, 'origen': 'local', 'es_envase': False,
         'proveedor_principal': 'ProvX', 'urgencia': 'normal'},
    ]
    try:
        with app.app_context():
            res = aplicar_plan(_make_plan(compras), usuario='test')
        numero = res['compras_creadas'][0]['numero']
        conn = sqlite3.connect(os.environ["DB_PATH"])
        provs = [
            r[0] for r in conn.execute(
                "SELECT COALESCE(proveedor_sugerido,'') FROM solicitudes_compra_items "
                "WHERE numero=?", (numero,)
            ).fetchall()
        ]
        conn.close()
        assert provs == ['ProvX', 'ProvX']
    finally:
        _cleanup_auto_solicitudes()


def test_aplicar_plan_sin_compras_propuestas_no_crea_solicitudes(app, db_clean):
    _ensure_api_path()
    from blueprints.auto_plan import aplicar_plan

    try:
        with app.app_context():
            res = aplicar_plan(_make_plan([]), usuario='test')
        assert len(res['compras_creadas']) == 0
    finally:
        _cleanup_auto_solicitudes()


# ── /api/compras/consolidar-auto-pendientes (limpieza legacy) ────────


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _crear_auto_xxxx_legacy(numero, codigo_mp, nombre_mp, cantidad_g,
                              proveedor_sugerido, urgencia='Normal',
                              categoria='Materia Prima'):
    """Inserta una AUTO-XXXX pendiente con UN solo item (legacy 1-MP-cada-una)."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO solicitudes_compra
           (numero, fecha, estado, solicitante, urgencia, observaciones,
            area, empresa, categoria, tipo, valor)
           VALUES (?, '2026-05-04', 'Pendiente', 'AUTO-PLAN', ?, ?,
                   'Producción', 'Espagiria', ?, 'Compra', 0)""",
        (numero, urgencia, f'AUTO-PLAN: {nombre_mp} test', categoria),
    )
    try:
        c.execute(
            """INSERT INTO solicitudes_compra_items
               (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                valor_estimado, proveedor_sugerido)
               VALUES (?, ?, ?, ?, 'g', 0, ?)""",
            (numero, codigo_mp, nombre_mp, cantidad_g, proveedor_sugerido),
        )
    except sqlite3.OperationalError:
        c.execute(
            """INSERT INTO solicitudes_compra_items
               (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                valor_estimado)
               VALUES (?, ?, ?, ?, 'g', 0)""",
            (numero, codigo_mp, nombre_mp, cantidad_g),
        )
    conn.commit()
    conn.close()


def test_consolidar_dry_run_no_modifica_db(app, db_clean):
    cs = _login(app)
    _crear_auto_xxxx_legacy('AUTO-9001', 'MP1', 'Glicerina', 1000, 'P1')
    _crear_auto_xxxx_legacy('AUTO-9002', 'MP2', 'Propilenglicol', 2000, 'P1')
    try:
        r = cs.post('/api/compras/consolidar-auto-pendientes',
                    json={'dry_run': True}, headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d['dry_run'] is True
        assert d['antes'] == 2
        assert d['despues'] == 1  # 2 SOLs P1 → 1 SOL consolidado
        assert d['eliminadas'] == 0  # dry-run no modifica
        assert d['creadas'] == 0
        # Verificar que NADA se modifico en DB
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute(
            "SELECT COUNT(*) FROM solicitudes_compra WHERE numero IN ('AUTO-9001','AUTO-9002')"
        ).fetchone()[0]
        conn.close()
        assert cnt == 2  # ambas siguen existiendo
    finally:
        _cleanup_auto_solicitudes()


def test_consolidar_ejecuta_borra_legacy_y_crea_consolidadas(app, db_clean):
    cs = _login(app)
    _crear_auto_xxxx_legacy('AUTO-9011', 'MP-A', 'Glicerina', 1000, 'Inq')
    _crear_auto_xxxx_legacy('AUTO-9012', 'MP-B', 'Propilenglicol', 2000, 'Inq')
    _crear_auto_xxxx_legacy('AUTO-9013', 'MP-C', 'Aerosil', 500, 'Otro')
    try:
        r = cs.post('/api/compras/consolidar-auto-pendientes',
                    json={'dry_run': False}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d['antes'] == 3
        assert d['eliminadas'] == 3
        assert d['creadas'] == 2  # Inq tenía 2, Otro tenía 1
        # Verificar DB
        conn = sqlite3.connect(os.environ["DB_PATH"])
        # Las legacy AUTO-9011..9013 ya no existen
        cnt_legacy = conn.execute(
            "SELECT COUNT(*) FROM solicitudes_compra "
            "WHERE numero IN ('AUTO-9011','AUTO-9012','AUTO-9013')"
        ).fetchone()[0]
        assert cnt_legacy == 0
        # Las consolidadas si
        for new_num in d['creadas_nums']:
            row = conn.execute(
                "SELECT estado, categoria FROM solicitudes_compra WHERE numero=?",
                (new_num,)
            ).fetchone()
            assert row[0] == 'Pendiente'
        conn.close()
    finally:
        _cleanup_auto_solicitudes()


def test_consolidar_respeta_min_para_consolidar(app, db_clean):
    """Si min_para_consolidar=3, un grupo de 2 NO debe consolidarse."""
    cs = _login(app)
    _crear_auto_xxxx_legacy('AUTO-9021', 'MP-X', 'X', 100, 'P-poco')
    _crear_auto_xxxx_legacy('AUTO-9022', 'MP-Y', 'Y', 100, 'P-poco')
    _crear_auto_xxxx_legacy('AUTO-9023', 'MP-Z', 'Z', 100, 'P-mucho')
    _crear_auto_xxxx_legacy('AUTO-9024', 'MP-W', 'W', 100, 'P-mucho')
    _crear_auto_xxxx_legacy('AUTO-9025', 'MP-V', 'V', 100, 'P-mucho')
    try:
        r = cs.post('/api/compras/consolidar-auto-pendientes',
                    json={'dry_run': False, 'min_para_consolidar': 3},
                    headers=csrf_headers())
        d = r.get_json()
        # Solo P-mucho (3 SOLs) se consolida, P-poco (2 SOLs) queda intacto
        assert d['eliminadas'] == 3
        assert d['creadas'] == 1
        conn = sqlite3.connect(os.environ["DB_PATH"])
        # P-poco SOLs siguen existiendo
        cnt = conn.execute(
            "SELECT COUNT(*) FROM solicitudes_compra WHERE numero IN ('AUTO-9021','AUTO-9022')"
        ).fetchone()[0]
        conn.close()
        assert cnt == 2
    finally:
        _cleanup_auto_solicitudes()


def test_consolidar_preserva_auto_ya_consolidadas(app, db_clean):
    """AUTO-XXXX con N>=2 items NO se toca (ya esta consolidada)."""
    cs = _login(app)
    # Crear una con 2 items (ya consolidada)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT INTO solicitudes_compra
           (numero, fecha, estado, solicitante, urgencia, observaciones,
            area, empresa, categoria, tipo, valor)
           VALUES ('AUTO-9031', '2026-05-04', 'Pendiente', 'AUTO-PLAN',
                   'Normal', 'consolidada', 'Producción', 'Espagiria',
                   'Materia Prima', 'Compra', 0)"""
    )
    for cod, n, q in [('MP-K1', 'K1', 100), ('MP-K2', 'K2', 200)]:
        try:
            c.execute(
                """INSERT INTO solicitudes_compra_items
                   (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                    valor_estimado, proveedor_sugerido)
                   VALUES ('AUTO-9031', ?, ?, ?, 'g', 0, 'P-K')""",
                (cod, n, q),
            )
        except sqlite3.OperationalError:
            c.execute(
                """INSERT INTO solicitudes_compra_items
                   (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                    valor_estimado)
                   VALUES ('AUTO-9031', ?, ?, ?, 'g', 0)""",
                (cod, n, q),
            )
    conn.commit(); conn.close()
    try:
        r = cs.post('/api/compras/consolidar-auto-pendientes',
                    json={'dry_run': False}, headers=csrf_headers())
        d = r.get_json()
        assert d['intactas'] == 1
        assert d['eliminadas'] == 0
        # AUTO-9031 sigue existiendo
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT COUNT(*) FROM solicitudes_compra WHERE numero='AUTO-9031'"
        ).fetchone()
        conn.close()
        assert row[0] == 1
    finally:
        _cleanup_auto_solicitudes()


def test_consolidar_sin_pendientes_devuelve_ok(app, db_clean):
    cs = _login(app)
    r = cs.post('/api/compras/consolidar-auto-pendientes',
                json={}, headers=csrf_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d['antes'] == 0
    assert 'Sin AUTO-XXXX pendientes' in d['mensaje']


def test_consolidar_audit_log(app, db_clean):
    cs = _login(app)
    _crear_auto_xxxx_legacy('AUTO-9041', 'MP-A1', 'A1', 100, 'PA')
    _crear_auto_xxxx_legacy('AUTO-9042', 'MP-A2', 'A2', 200, 'PA')
    try:
        r = cs.post('/api/compras/consolidar-auto-pendientes',
                    json={}, headers=csrf_headers())
        assert r.status_code == 200
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion FROM audit_log "
            "WHERE accion='CONSOLIDAR_AUTO_PENDIENTES' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'catalina'
    finally:
        _cleanup_auto_solicitudes()


def test_compras_html_boton_consolidar_visible(app, db_clean):
    cs = _login(app)
    body = cs.get('/compras').get_data(as_text=True)
    assert 'btn-consolidar-auto' in body
    assert 'consolidarAutoPendientes' in body
    assert 'Consolidar AUTO' in body
