"""Sebastián 2-jul: el PATCH de pedido B2B ahora guarda envase_codigo + urgencia
(para que el pedido caiga al calendario con su envase, y la urgencia editable)."""
import os, sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='luz'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_patch_pedido_guarda_envase_y_urgencia(app, db_clean):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO clientes_b2b_maestro (cliente_id,cliente_nombre,activo,tipo) "
                     "VALUES ('CLI-T','Cliente T',1,'MAQUILA')")
        conn.execute("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
                     "creado_por,ml_unidad,estado) VALUES ('CLI-T','Cliente T','PROD',100,'luz',30,'pendiente')")
        conn.commit()
        pid = conn.execute("SELECT id FROM pedidos_b2b WHERE cliente_id='CLI-T'").fetchone()[0]
    finally:
        conn.close()
    c = _login(app, 'luz')
    r = c.patch('/api/pedidos-b2b/%d' % pid, json={'envase_codigo': 'FR-PLA-REDONDO-150', 'urgencia': 'alta'},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        row = conn.execute("SELECT envase_codigo, urgencia FROM pedidos_b2b WHERE id=?", (pid,)).fetchone()
    finally:
        conn.close()
    assert row[0] == 'FR-PLA-REDONDO-150', row
    assert row[1] == 'alta', row
