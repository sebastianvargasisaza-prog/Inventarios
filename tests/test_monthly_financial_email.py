"""Tests del cron job_monthly_financial_summary + helpers P&L/MoM/tops.

Verifica:
- _calcular_pnl_mensual: ingresos/egresos/margen/MoM/categorías
- _calcular_tops_mes: top clientes y proveedores
- _calcular_operativos_mes: producciones/lotes/facturas
- _build_monthly_financial_html: HTML válido con todas las secciones
- job_monthly_financial_summary: ejecuta y manda email
- Está registrado en JOBS_SCHEDULE como día 1 8am
"""
import os
import sqlite3


def test_pnl_mensual_estructura(app, db_clean):
    from blueprints.auto_plan_jobs import _calcular_pnl_mensual
    from database import get_db
    with app.app_context():
        conn = get_db()
        pnl = _calcular_pnl_mensual(conn, '2026-04')
    assert isinstance(pnl, dict)
    for k in ('periodo', 'ingresos_total', 'egresos_total', 'margen',
                'margen_pct', 'egresos_por_categoria', 'mes_anterior',
                'mes_anterior_ingresos', 'mom_pct'):
        assert k in pnl, f"falta key {k}"


def test_pnl_calcula_correcto(app, db_clean):
    """Sembrar flujo + verificar cálculos."""
    from blueprints.auto_plan_jobs import _calcular_pnl_mensual
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Limpiar período de prueba
    conn.execute("DELETE FROM flujo_ingresos WHERE periodo='2026-99'")
    conn.execute("DELETE FROM flujo_egresos WHERE periodo='2026-99'")
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto)
                    VALUES (date('now'), '2026-99', 10000000, 'Test ingreso')""")
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), '2026-99', 6000000, 'Test egreso 1', 'MPs')""")
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), '2026-99', 2000000, 'Test egreso 2', 'Nomina')""")
    conn.commit(); conn.close()
    try:
        from database import get_db
        with app.app_context():
            conn = get_db()
            pnl = _calcular_pnl_mensual(conn, '2026-99')
        assert pnl['ingresos_total'] == 10000000
        assert pnl['egresos_total'] == 8000000
        assert pnl['margen'] == 2000000
        assert pnl['margen_pct'] == 20.0
        # Categorías
        cats = {c['categoria']: c['monto'] for c in pnl['egresos_por_categoria']}
        assert cats.get('MPs') == 6000000
        assert cats.get('Nomina') == 2000000
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_ingresos WHERE periodo='2026-99'")
        conn.execute("DELETE FROM flujo_egresos WHERE periodo='2026-99'")
        conn.commit(); conn.close()


def test_tops_mes_estructura(app, db_clean):
    from blueprints.auto_plan_jobs import _calcular_tops_mes
    from database import get_db
    with app.app_context():
        conn = get_db()
        tops = _calcular_tops_mes(conn, '2026-04')
    assert 'clientes' in tops
    assert 'proveedores' in tops
    assert isinstance(tops['clientes'], list)
    assert isinstance(tops['proveedores'], list)


def test_operativos_mes_estructura(app, db_clean):
    from blueprints.auto_plan_jobs import _calcular_operativos_mes
    from database import get_db
    with app.app_context():
        conn = get_db()
        op = _calcular_operativos_mes(conn, '2026-04')
    for k in ('producciones_completadas', 'lotes_liberados',
              'lotes_rechazados', 'facturas_emitidas'):
        assert k in op
        assert isinstance(op[k], int)


def test_html_monthly_genera(app, db_clean):
    from blueprints.auto_plan_jobs import (
        _build_monthly_financial_html, _calcular_pnl_mensual,
        _calcular_tops_mes, _calcular_operativos_mes,
    )
    from database import get_db
    with app.app_context():
        conn = get_db()
        pnl = _calcular_pnl_mensual(conn, '2026-04')
        tops = _calcular_tops_mes(conn, '2026-04')
        op = _calcular_operativos_mes(conn, '2026-04')
    html = _build_monthly_financial_html(pnl, tops, op, caja_actual=10000000)
    assert '<html>' in html.lower()
    assert 'Reporte Mensual' in html
    # Las 5 secciones esperadas
    for s in ('Egresos por categoría', 'Top 5 clientes',
              'Top 5 proveedores', 'Operativos del mes',
              'app.eossuite.com/financiero'):
        assert s in html, f'falta sección "{s}"'
    # Mes en español
    assert 'abril' in html
    # Caja debe aparecer si > 0
    assert '10.0M' in html


def test_monthly_financial_registrado_en_schedule():
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    job_names = [j[0] for j in JOBS_SCHEDULE]
    assert 'monthly_financial' in job_names
    monthly = [j for j in JOBS_SCHEDULE if j[0] == 'monthly_financial'][0]
    name, hora, minuto, dias_sem, dias_mes, callable_name = monthly
    assert hora == 8 and minuto == 0
    assert dias_sem is None
    assert dias_mes == [1]  # solo día 1
    assert callable_name == 'job_monthly_financial_summary'


def test_job_monthly_returns_ok(app, db_clean, monkeypatch):
    """Ejecutar el cron debe retornar (True, {...}) sin enviar email real."""
    from blueprints.auto_plan_jobs import job_monthly_financial_summary
    sent_emails = []

    def fake_send_async(asunto, html, destinos):
        sent_emails.append({'asunto': asunto, 'destinos': destinos, 'html_len': len(html)})
        return True

    monkeypatch.setattr('blueprints.auto_plan_jobs._enviar_email_async', fake_send_async)
    ok, data, _ = job_monthly_financial_summary(app)
    assert ok is True, f"job retornó error: {data}"
    assert 'destino' in data
    assert 'periodo' in data
    assert 'ingresos' in data
    assert 'egresos' in data
    assert 'margen' in data
    assert len(sent_emails) == 1
    em = sent_emails[0]
    assert 'sebastianvargasisaza@gmail.com' in em['destinos']
    assert 'Reporte Mensual HHA' in em['asunto']
    assert em['html_len'] > 1000


def test_monthly_periodo_es_mes_anterior(app, db_clean, monkeypatch):
    """El cron debe procesar el mes ANTERIOR, no el actual."""
    from blueprints.auto_plan_jobs import job_monthly_financial_summary
    captured = {}

    def fake_send_async(asunto, html, destinos):
        captured['asunto'] = asunto
        return True

    monkeypatch.setattr('blueprints.auto_plan_jobs._enviar_email_async', fake_send_async)
    ok, data, _ = job_monthly_financial_summary(app)
    assert ok is True
    # Como hoy es mayo 2026, debe procesar abril (2026-04)
    from datetime import datetime
    hoy = datetime.now()
    mes_esperado = hoy.month - 1
    anio_esperado = hoy.year
    if mes_esperado == 0:
        mes_esperado = 12; anio_esperado -= 1
    periodo_esperado = f"{anio_esperado:04d}-{mes_esperado:02d}"
    assert data['periodo'] == periodo_esperado
