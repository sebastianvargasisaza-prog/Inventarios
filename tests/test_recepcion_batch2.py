"""Recepciones · batch 2 (Sebastián 12-jun · auditoría):
H2-F4: KPI Calidad cuenta aprobados/rechazados desde audit_log (no estado_lote).
H4-F4: seguimiento NO duplica la OC si >1 SOL apunta al mismo numero_oc.
H1-F4: color de estado en trazabilidad normaliza a mayúsculas.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_kpi_calidad_cuenta_desde_audit(app, db_clean):
    # Decisiones QC de hoy desde ambas rutas (panel + cc-review)
    for acc in ('APROBAR_LOTE', 'CC_REVIEW_APROBADO', 'RECHAZAR_LOTE'):
        _exec("INSERT INTO audit_log (usuario,accion,tabla,registro_id,fecha) "
              "VALUES ('sebastian',?,'movimientos','1', date('now','-5 hours'))", (acc,))
    c = _login(app)
    r = c.get('/api/calidad/dashboard')
    assert r.status_code == 200, r.data
    d = r.get_json()
    # aprobados cuenta APROBAR_LOTE + CC_REVIEW_APROBADO (>=2), rechazados >=1
    assert d.get('aprobados', 0) >= 2, f"KPI aprobados debe contar ambas rutas · {d.get('aprobados')}"
    assert d.get('rechazados', 0) >= 1, f"KPI rechazados · {d.get('rechazados')}"


def test_seguimiento_no_duplica_oc(app, db_clean):
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc,fecha,estado,proveedor,categoria,valor_total) "
          "VALUES ('OC-DUP-SEG', date('now'), 'Autorizada', 'ProvX', 'MP', 0)")
    # 2 SOLs apuntan a la MISMA OC (consolidacion) · numero_oc no es UNIQUE
    _exec("INSERT INTO solicitudes_compra (numero,numero_oc,estado) VALUES ('SOL-A','OC-DUP-SEG','Aprobada')")
    _exec("INSERT INTO solicitudes_compra (numero,numero_oc,estado) VALUES ('SOL-B','OC-DUP-SEG','Aprobada')")
    c = _login(app)
    r = c.get('/api/recepcion/seguimiento')
    assert r.status_code == 200, r.data
    filas = r.get_json()
    n = sum(1 for x in filas if x.get('numero_oc') == 'OC-DUP-SEG')
    assert n == 1, f"la OC debe aparecer UNA sola vez (no fanout por 2 SOLs) · aparecio {n}"


def test_trazabilidad_color_normaliza_case(app, db_clean):
    c = _login(app)
    r = c.get('/recepcion')
    assert r.status_code == 200
    body = r.data.decode('utf-8', 'replace')
    assert '.toUpperCase()' in body and "_est === 'RECHAZADO'" in body, \
        "el color de estado en trazabilidad debe comparar en mayúsculas"
