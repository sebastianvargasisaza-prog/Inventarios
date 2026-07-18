"""Cash-flow 'Por Pagar' (18-jul): el KPI de proyección 30/60/90 debe restar lo ya abonado
(pagos_oc) del valor_total de las OC Parciales, no sumar el total completo (sobre-proyectaba)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='catalina'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_oc_parcial(numero, valor_total, pagado):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total, fecha, fecha_entrega_est) "
            "VALUES (?, 'Prov Cash', 'Parcial', ?, date('now','-5 hours'), date('now','-5 hours'))",
            (numero, valor_total))
        if pagado > 0:
            conn.execute("INSERT INTO pagos_oc (numero_oc, monto, medio, registrado_por) "
                         "VALUES (?, ?, 'Transferencia', 'test')", (numero, pagado))
        conn.commit()
    finally:
        conn.close()


def _monto_30d(client):
    d = client.get('/api/compras/cash-flow').get_json()
    for p in (d.get('proyecciones') or []):
        if p.get('dias') == 30:
            return p['ocs_por_pagar']['monto']
    return None


def test_cash_flow_resta_abonos_parciales(app, db_clean):
    # OC de 1.000.000 con 600.000 ya abonado → el "por pagar" debe reflejar 400.000, no 1.000.000
    _seed_oc_parcial('OC-CASH-001', 1_000_000, 600_000)
    c = _login(app)
    monto = _monto_30d(c)
    assert monto is not None
    assert abs(monto - 400_000) < 1.0, f"debe restar lo abonado (saldo 400k), no sumar el total: {monto}"


def test_cash_flow_no_negativo_por_sobrepago(app, db_clean):
    # sobrepago (abonado > total) no debe restar de más ni volverse negativo → aporta 0
    _seed_oc_parcial('OC-CASH-002', 500_000, 700_000)
    c = _login(app)
    monto = _monto_30d(c)
    assert monto is not None and monto >= 0, f"no debe ser negativo: {monto}"
    assert monto < 1.0, f"una OC sobre-pagada aporta 0 al por pagar: {monto}"
