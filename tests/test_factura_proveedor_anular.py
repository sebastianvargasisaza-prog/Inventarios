"""No se puede anular una factura de proveedor que YA se pagó (28-jul · auditoría de Compras).

El endpoint leía el estado de la factura y **no lo usaba para nada**: `SELECT estado` y después
`UPDATE ... SET estado='anulada' WHERE id=?`, sin mirar nada. Se podía anular una factura ya
pagada, y los pagos de `pagos_oc` quedaban colgando de un registro anulado: el libro de cuentas
por pagar decía "anulada" mientras la plata ya había salido.

Es la firma del patrón M45: su hermano `fp_pagar` SÍ rechaza pagar una factura anulada desde el
31-may. Cuando se endurece un guard de dinero, uno de los hermanos queda sin endurecer.
"""
from datetime import date

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


OC = 'OC-ZZ-FACT'


def _factura(app, *, pagada=0):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM pagos_oc WHERE numero_oc=?", (OC,))
        cu.execute("DELETE FROM facturas_proveedor WHERE numero_oc=?", (OC,))
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        hoy = date.today().isoformat()
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, fecha, valor_total) "
                   "VALUES (?,?,?,?,?)", (OC, 'ZZ Proveedor', 'Autorizada', hoy, 500000))
        cu.execute("INSERT INTO facturas_proveedor (numero_factura, proveedor, numero_oc, "
                   "fecha_emision, total, estado) VALUES (?,?,?,?,?,?)",
                   ('FZZ-001', 'ZZ Proveedor', OC, hoy, 500000, 'pendiente'))
        fid = cu.execute("SELECT id FROM facturas_proveedor WHERE numero_factura=?",
                         ('FZZ-001',)).fetchone()[0]
        if pagada:
            # La columna es `fecha_pago`, no `fecha` (verificado contra el CREATE TABLE ·
            # el auto-check del cerebro: confirmar el nombre real antes de escribir SQL).
            cu.execute("INSERT INTO pagos_oc (numero_oc, monto, fecha_pago, medio, "
                       "factura_proveedor_id) VALUES (?,?,?,?,?)",
                       (OC, pagada, hoy, 'Transferencia', fid))
            cu.execute("UPDATE facturas_proveedor SET estado='pagada' WHERE id=?", (fid,))
        conn.commit()
    return fid


def _estado(app, fid):
    from database import get_db
    with app.app_context():
        return get_db().cursor().execute(
            "SELECT estado FROM facturas_proveedor WHERE id=?", (fid,)).fetchone()[0]


# ═══════════════════════════════════════════════════════════════════════════════

def test_no_se_puede_anular_una_factura_ya_pagada(app, db_clean):
    """Si se anulara, los pagos quedan colgando de un registro anulado y el libro miente."""
    fid = _factura(app, pagada=500000)
    c = _login(app)
    r = c.patch(f'/api/compras/facturas-proveedor/{fid}',
                json={'anular': True, 'motivo': 'me equivoqué'}, headers=_h())
    assert r.status_code == 409, r.data[:300]
    assert r.get_json().get('codigo') == 'FACTURA_CON_PAGOS'
    assert _estado(app, fid) == 'pagada', 'la anuló igual'


def test_una_factura_con_pago_PARCIAL_tampoco_se_anula(app, db_clean):
    """Medio pagada es igual de peligroso: esa mitad ya salió del banco."""
    fid = _factura(app, pagada=200000)
    c = _login(app)
    r = c.patch(f'/api/compras/facturas-proveedor/{fid}',
                json={'anular': True, 'motivo': 'ajuste'}, headers=_h())
    assert r.status_code == 409
    assert 'revertí el pago' in (r.get_json().get('error') or '')


def test_una_factura_sin_pagos_SI_se_anula(app, db_clean):
    """El arreglo no puede matar el caso legítimo: una factura mal cargada se anula."""
    fid = _factura(app)
    c = _login(app)
    r = c.patch(f'/api/compras/facturas-proveedor/{fid}',
                json={'anular': True, 'motivo': 'cargada dos veces'}, headers=_h())
    assert r.status_code == 200, r.data[:300]
    assert _estado(app, fid) == 'anulada'


def test_anular_dos_veces_no_pasa_dos_veces(app, db_clean):
    """CAS (M27): con 3 workers, dos anulaciones concurrentes no pueden pasar las dos."""
    fid = _factura(app)
    c = _login(app)
    assert c.patch(f'/api/compras/facturas-proveedor/{fid}',
                   json={'anular': True, 'motivo': 'la primera'}, headers=_h()).status_code == 200
    r2 = c.patch(f'/api/compras/facturas-proveedor/{fid}',
                 json={'anular': True, 'motivo': 'la segunda'}, headers=_h())
    assert r2.status_code == 409
    assert r2.get_json().get('codigo') == 'YA_ANULADA'


def test_la_anulacion_queda_auditada_con_el_estado_anterior(app, db_clean):
    """Part 11: tiene que quedar de qué estado se anuló, no sólo que se anuló."""
    from database import get_db
    fid = _factura(app)
    c = _login(app)
    c.patch(f'/api/compras/facturas-proveedor/{fid}',
            json={'anular': True, 'motivo': 'duplicada'}, headers=_h())
    with app.app_context():
        fila = get_db().cursor().execute(
            "SELECT antes, despues FROM audit_log WHERE accion='ANULAR_FACTURA_PROVEEDOR' "
            "AND registro_id=? ORDER BY id DESC", (str(fid),)).fetchone()
    assert fila, 'la anulación no dejó rastro'
    assert 'pendiente' in (fila[0] or ''), 'no guardó de qué estado venía: %s' % (fila[0],)
    assert 'duplicada' in (fila[1] or '')


def test_el_hermano_sigue_rechazando_pagar_una_anulada(app, db_clean):
    """La simetría que faltaba, ahora en los dos sentidos."""
    fid = _factura(app)
    c = _login(app)
    c.patch(f'/api/compras/facturas-proveedor/{fid}',
            json={'anular': True, 'motivo': 'no va'}, headers=_h())
    r = c.post(f'/api/compras/facturas-proveedor/{fid}/pagar',
               json={'monto': 100000, 'medio': 'Transferencia'}, headers=_h())
    assert r.status_code in (400, 409), r.data[:200]
