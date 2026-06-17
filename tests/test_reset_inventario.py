"""16-jun · Reset de inventario a CERO (app en prueba) · conserva catálogo, borra stock.

POST /api/inventario/reset-inventario-cero {confirmar:'CERO'} (ADMIN): borra movimientos
(MP) + movimientos_mee + maestro_mee.stock_actual=0 + conteos, con respaldo *_bak_<ts>.
NO toca maestro_mps (códigos/INCI/nombres) ni stock_pt.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _seed_inv():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        for q in ["DELETE FROM maestro_mps WHERE codigo_mp='MPRST1'",
                  "DELETE FROM maestro_mee WHERE codigo='MEERST'"]:
            try:
                conn.execute(q)
            except Exception:
                pass
        conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) "
                     "VALUES ('MPRST1','Test INCI Reset','Comercial Reset',1)")
        conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                     "VALUES ('MPRST1','Test INCI Reset',5000,'Entrada','2026-06-10','LRST','VIGENTE')")
        try:
            conn.execute("INSERT INTO maestro_mee (codigo,descripcion,stock_actual,estado) VALUES ('MEERST','Envase Reset',300,'activo')")
            conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha,anulado) VALUES ('MEERST','Entrada',300,'2026-06-10',0)")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def test_reset_requiere_admin(app, db_clean):
    c = _login(app, 'valentina')  # no admin
    r = c.post('/api/inventario/reset-inventario-cero', json={'confirmar': 'CERO'}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]


def test_reset_sin_confirmar_no_borra(app, db_clean):
    _seed_inv()
    c = _login(app, 'sebastian')
    # GET = preview, no borra
    g = c.get('/api/inventario/reset-inventario-cero')
    assert g.status_code == 200 and g.get_json()['dry_run'] is True
    # POST sin confirmar correcto → 400
    r = c.post('/api/inventario/reset-inventario-cero', json={'confirmar': 'si'}, headers=csrf_headers())
    assert r.status_code == 400
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        assert conn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id='MPRST1'").fetchone()[0] >= 1
    finally:
        conn.close()


def test_reset_pone_cero_conserva_catalogo(app, db_clean):
    _seed_inv()
    c = _login(app, 'sebastian')
    r = c.post('/api/inventario/reset-inventario-cero',
               json={'confirmar': 'CERO', 'incluir_mee': True, 'limpiar_conteos': True}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['ok'] is True and j['mp_borrados'] >= 1
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # stock MP en cero (sin movimientos)
        assert conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0] == 0
        # catálogo INTACTO (código/INCI/nombre se conservan)
        row = conn.execute("SELECT nombre_inci, nombre_comercial FROM maestro_mps WHERE codigo_mp='MPRST1'").fetchone()
        assert row and row[0] == 'Test INCI Reset' and row[1] == 'Comercial Reset'
        # envases en cero
        assert conn.execute("SELECT COUNT(*) FROM movimientos_mee").fetchone()[0] == 0
        mee = conn.execute("SELECT stock_actual FROM maestro_mee WHERE codigo='MEERST'").fetchone()
        if mee:
            assert (mee[0] or 0) == 0
        # respaldo creado
        assert j['backups'] and any('movimientos_bak_' in b for b in j['backups'])
        bak = [b for b in j['backups'] if b.startswith('movimientos_bak_')][0]
        assert conn.execute(f"SELECT COUNT(*) FROM {bak}").fetchone()[0] >= 1  # respaldo tiene los datos
    finally:
        conn.close()
