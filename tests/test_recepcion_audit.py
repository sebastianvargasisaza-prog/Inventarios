"""Tests del audit de Recepciones (Sebastian 5-may-2026 zero-error).

Cubre los 3 fixes críticos derivados del audit del flujo Recepción:

1. /api/recepcion/lotes-cuarentena · UPPER() para matchear ambos
   'Cuarentena' y 'CUARENTENA' que coexisten en DB. Antes lotes
   recepcionados via /api/ordenes-compra/<oc>/recibir (que escribe
   'CUARENTENA' uppercase) eran INVISIBLES en bandeja QC porque el
   filtro buscaba solo 'Cuarentena' Capitalizado.

2. /api/ordenes-compra/<oc>/recibir · valida sobre-recepción (>5%
   sobre lo pedido) y bloquea con 422 salvo forzar:true. Antes
   permitia recibir cualquier cantidad sin alerta.

3. /api/ordenes-compra/<oc>/recibir · valida que fecha_vencimiento
   no sea pasada · bloquea con 422 salvo forzar:true. Antes
   recepcionaba MP vencida silenciosamente (violación INVIMA).
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


def _seed_oc_autorizada(numero_oc, items, proveedor='Inquimica', categoria='MP'):
    """Inserta una OC en estado Autorizada con items para recibir."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO ordenes_compra
           (numero_oc, fecha, estado, proveedor, valor_total,
            observaciones, creado_por, categoria)
           VALUES (?, date('now'), 'Autorizada', ?, 0,
                   'Test seed', 'test', ?)""",
        (numero_oc, proveedor, categoria),
    )
    for codigo, nombre, cantidad_g in items:
        c.execute(
            """INSERT OR IGNORE INTO maestro_mps
               (codigo_mp, nombre_comercial, activo)
               VALUES (?, ?, 1)""",
            (codigo, nombre),
        )
        c.execute(
            """INSERT INTO ordenes_compra_items
               (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g)
               VALUES (?, ?, ?, ?, 0)""",
            (numero_oc, codigo, nombre, cantidad_g),
        )
    conn.commit(); conn.close()


def _cleanup_oc(numero_oc, codigos):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    c.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    if codigos:
        ph = ','.join(['?'] * len(codigos))
        c.execute(f"DELETE FROM movimientos WHERE material_id IN ({ph})", codigos)
        c.execute(f"DELETE FROM maestro_mps WHERE codigo_mp IN ({ph})", codigos)
    conn.commit(); conn.close()


# ── Bug 1 · UPPER en queries cuarentena ──────────────────────────────


def test_lotes_cuarentena_matchea_ambos_cases(app, db_clean):
    """SELECT debe encontrar lotes en 'Cuarentena' (Cap) y 'CUARENTENA' (UPPER)."""
    cs = _login(app)
    # Sembrar 2 lotes en cuarentena, distintos cases
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT OR IGNORE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo) VALUES ('MP-Q-CAP', 'X', 1)"""
    )
    conn.execute(
        """INSERT OR IGNORE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo) VALUES ('MP-Q-UPP', 'Y', 1)"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, estado_lote, operador)
           VALUES ('MP-Q-CAP', 'X', 1000, 'Entrada', date('now'),
                   'L-Q-CAP', 'Cuarentena', 'test')"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, estado_lote, operador)
           VALUES ('MP-Q-UPP', 'Y', 1000, 'Entrada', date('now'),
                   'L-Q-UPP', 'CUARENTENA', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/recepcion/lotes-cuarentena')
        assert r.status_code == 200
        data = r.get_json()
        lotes = {row['lote'] for row in data}
        assert 'L-Q-CAP' in lotes, "Lote 'Cuarentena' Capitalizado debe aparecer"
        assert 'L-Q-UPP' in lotes, "Lote 'CUARENTENA' UPPERCASE debe aparecer"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE material_id IN ('MP-Q-CAP','MP-Q-UPP')")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp IN ('MP-Q-CAP','MP-Q-UPP')")
        conn.commit(); conn.close()


def test_lotes_cuarentena_incluye_extendida(app, db_clean):
    """CUARENTENA_EXTENDIDA tambien debe aparecer en bandeja QC."""
    cs = _login(app)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        """INSERT OR IGNORE INTO maestro_mps
           (codigo_mp, nombre_comercial, activo) VALUES ('MP-Q-EXT', 'X', 1)"""
    )
    conn.execute(
        """INSERT INTO movimientos
           (material_id, material_nombre, cantidad, tipo, fecha,
            lote, estado_lote, operador)
           VALUES ('MP-Q-EXT', 'X', 1000, 'Entrada', date('now'),
                   'L-EXT', 'CUARENTENA_EXTENDIDA', 'test')"""
    )
    conn.commit(); conn.close()
    try:
        r = cs.get('/api/recepcion/lotes-cuarentena')
        data = r.get_json()
        lotes = {row['lote'] for row in data}
        assert 'L-EXT' in lotes
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-Q-EXT'")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP-Q-EXT'")
        conn.commit(); conn.close()


# ── Bug 2 · Sobre-recepción bloqueada ─────────────────────────────────


def test_recibir_oc_sobrerecepcion_bloqueada_por_default(app, db_clean):
    """Recibir más de 105% de lo pedido debe fallar 422 sin forzar."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-SOBR-001', [('MP-SOB', 'M1', 1000)])
    try:
        r = cs.post('/api/ordenes-compra/OC-SOBR-001/recibir',
                    json={'items_recepcion': [
                        {'codigo_mp': 'MP-SOB', 'cantidad_recibida': 1500,
                         'lote': 'L-SOB-1'}
                    ]},
                    headers=csrf_headers())
        assert r.status_code == 422, r.data
        d = r.get_json()
        assert d['codigo'] == 'RECEPCION_VIOLA_REGLAS'
        assert len(d['sobrerecepciones']) == 1
        assert d['sobrerecepciones'][0]['exceso_g'] == 500
        assert d['sobrerecepciones'][0]['pct_exceso'] == 50.0
        # Verificar que NO se inserto nada
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-SOB'"
        ).fetchone()[0]
        conn.close()
        assert cnt == 0, "No debe haber inserts en sobre-recepcion bloqueada"
    finally:
        _cleanup_oc('OC-SOBR-001', ['MP-SOB'])


def test_recibir_oc_sobrerecepcion_5pct_tolerancia_pasa(app, db_clean):
    """Recibir 4% más debe pasar (dentro del 5% de tolerancia)."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-TOL-001', [('MP-TOL', 'M1', 1000)])
    try:
        r = cs.post('/api/ordenes-compra/OC-TOL-001/recibir',
                    json={'items_recepcion': [
                        {'codigo_mp': 'MP-TOL', 'cantidad_recibida': 1040,
                         'lote': 'L-TOL'}
                    ]},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
    finally:
        _cleanup_oc('OC-TOL-001', ['MP-TOL'])


def test_recibir_oc_sobrerecepcion_admite_forzar(app, db_clean):
    """Con forzar:true, sobre-recepcion permitida (caso legitimo)."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-FRZ-001', [('MP-FRZ', 'M1', 1000)])
    try:
        r = cs.post('/api/ordenes-compra/OC-FRZ-001/recibir',
                    json={'forzar': True,
                          'items_recepcion': [
                            {'codigo_mp': 'MP-FRZ', 'cantidad_recibida': 1500,
                             'lote': 'L-FRZ'}
                          ]},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        # Verificar que sí se inserto
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-FRZ' AND tipo='Entrada'"
        ).fetchone()[0]
        conn.close()
        assert cnt == 1
    finally:
        _cleanup_oc('OC-FRZ-001', ['MP-FRZ'])


# ── Bug 3 · Vencimiento pasado bloqueado ─────────────────────────────


def test_recibir_oc_vencimiento_pasado_bloqueado(app, db_clean):
    """fecha_vencimiento < hoy debe bloquear recepción (422)."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-VEN-001', [('MP-VEN', 'M1', 500)])
    try:
        r = cs.post('/api/ordenes-compra/OC-VEN-001/recibir',
                    json={'items_recepcion': [
                        {'codigo_mp': 'MP-VEN', 'cantidad_recibida': 500,
                         'lote': 'L-VEN', 'fecha_vencimiento': '2024-01-01'}
                    ]},
                    headers=csrf_headers())
        assert r.status_code == 422, r.data
        d = r.get_json()
        assert d['codigo'] == 'RECEPCION_VIOLA_REGLAS'
        assert len(d['vencimientos_pasados']) == 1
        assert d['vencimientos_pasados'][0]['dias_vencido'] > 0
        # NO se insertó
        conn = sqlite3.connect(os.environ["DB_PATH"])
        cnt = conn.execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id='MP-VEN'"
        ).fetchone()[0]
        conn.close()
        assert cnt == 0
    finally:
        _cleanup_oc('OC-VEN-001', ['MP-VEN'])


def test_recibir_oc_vencimiento_futuro_pasa(app, db_clean):
    """fecha_vencimiento >= hoy debe pasar."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-FUT-001', [('MP-FUT', 'M1', 500)])
    try:
        r = cs.post('/api/ordenes-compra/OC-FUT-001/recibir',
                    json={'items_recepcion': [
                        {'codigo_mp': 'MP-FUT', 'cantidad_recibida': 500,
                         'lote': 'L-FUT', 'fecha_vencimiento': '2027-12-31'}
                    ]},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
    finally:
        _cleanup_oc('OC-FUT-001', ['MP-FUT'])


def test_recibir_oc_vencimiento_admite_forzar(app, db_clean):
    """Con forzar:true admin puede recibir MP vencida (caso de emergencia)."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-FZV-001', [('MP-FZV', 'M1', 500)])
    try:
        r = cs.post('/api/ordenes-compra/OC-FZV-001/recibir',
                    json={'forzar': True,
                          'items_recepcion': [
                            {'codigo_mp': 'MP-FZV', 'cantidad_recibida': 500,
                             'lote': 'L-FZV', 'fecha_vencimiento': '2024-01-01'}
                          ]},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
    finally:
        _cleanup_oc('OC-FZV-001', ['MP-FZV'])


def test_recibir_oc_combo_violaciones_listadas(app, db_clean):
    """Si hay sobrerecepción Y vencimiento pasado, listar ambos en error."""
    cs = _login(app, 'sebastian')
    _seed_oc_autorizada('OC-CMB-001', [
        ('MP-CMB-A', 'A', 500),
        ('MP-CMB-B', 'B', 500),
    ])
    try:
        r = cs.post('/api/ordenes-compra/OC-CMB-001/recibir',
                    json={'items_recepcion': [
                        {'codigo_mp': 'MP-CMB-A', 'cantidad_recibida': 800,
                         'lote': 'L-A'},  # sobre-recepción
                        {'codigo_mp': 'MP-CMB-B', 'cantidad_recibida': 500,
                         'lote': 'L-B', 'fecha_vencimiento': '2020-01-01'},  # vencido
                    ]},
                    headers=csrf_headers())
        assert r.status_code == 422
        d = r.get_json()
        assert len(d['sobrerecepciones']) == 1
        assert len(d['vencimientos_pasados']) == 1
    finally:
        _cleanup_oc('OC-CMB-001', ['MP-CMB-A', 'MP-CMB-B'])
