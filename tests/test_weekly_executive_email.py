"""Tests del cron job_weekly_executive_email + helpers HTML/KPIs.

Verifica:
- _calcular_kpis_semanales devuelve dict con KPIs esperadas
- _capturar_health_snapshot consume el endpoint y retorna estructura válida
- _build_weekly_executive_html genera HTML válido con secciones
- job_weekly_executive_email retorna ok=True con destino correcto
- Está registrado en JOBS_SCHEDULE
"""
import os
import sqlite3


def test_kpis_semanales_estructura(app, db_clean):
    from blueprints.auto_plan_jobs import _calcular_kpis_semanales
    from database import get_db
    with app.app_context():
        conn = get_db()
        kpis = _calcular_kpis_semanales(conn)
    assert isinstance(kpis, dict)
    for key in ('Pedidos 7d', 'Ventas 7d', 'OCs 7d', 'Prod 7d', 'Audit 7d'):
        assert key in kpis, f"falta KPI {key}"


def test_health_snapshot_capturable(app, db_clean):
    from blueprints.auto_plan_jobs import _capturar_health_snapshot
    snap = _capturar_health_snapshot(app)
    assert isinstance(snap, dict)
    assert 'overall' in snap
    assert 'sections' in snap
    # Debe traer las secciones operacionales nuevas
    sections = snap.get('sections', {})
    for k in ('invima', 'recalls', 'caja', 'salas', 'mfa_admins'):
        assert k in sections, f"snapshot no trae sección {k}"


def test_html_executive_genera(app, db_clean):
    from blueprints.auto_plan_jobs import (
        _build_weekly_executive_html,
        _capturar_health_snapshot,
        _calcular_kpis_semanales,
    )
    from database import get_db
    with app.app_context():
        snapshot = _capturar_health_snapshot(app)
        conn = get_db()
        kpis = _calcular_kpis_semanales(conn)
    html = _build_weekly_executive_html(snapshot, kpis)
    assert '<html>' in html.lower()
    assert 'Executive Brief' in html
    assert 'app.eossuite.com/admin/system-health' in html
    # Debe incluir KPIs como texto
    for k in ('Pedidos 7d', 'Ventas 7d'):
        assert k in html


def test_weekly_executive_registrado_en_schedule():
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    job_names = [j[0] for j in JOBS_SCHEDULE]
    assert 'weekly_executive' in job_names
    # Debe ser lunes (dia=0) a las 7:30
    weekly = [j for j in JOBS_SCHEDULE if j[0] == 'weekly_executive'][0]
    name, hora, minuto, dias_sem, dias_mes, callable_name = weekly
    assert hora == 7 and minuto == 30
    assert dias_sem == [0]  # solo lunes
    assert callable_name == 'job_weekly_executive_email'


def test_job_weekly_executive_returns_ok(app, db_clean, monkeypatch):
    """Ejecutar el cron debe retornar (True, {...}, 0) sin enviar email real."""
    from blueprints.auto_plan_jobs import job_weekly_executive_email
    sent_emails = []

    def fake_send_async(asunto, html, destinos):
        sent_emails.append({'asunto': asunto, 'destinos': destinos, 'html_len': len(html)})
        return True

    monkeypatch.setattr('blueprints.auto_plan_jobs._enviar_email_async', fake_send_async)
    ok, data, sleep_s = job_weekly_executive_email(app)
    assert ok is True, f"job retornó error: {data}"
    assert isinstance(data, dict)
    assert 'destino' in data
    assert 'overall' in data
    assert 'kpis' in data
    # El email debe haberse intentado enviar
    assert len(sent_emails) == 1
    em = sent_emails[0]
    assert 'sebastianvargasisaza@gmail.com' in em['destinos']
    assert 'Executive Brief' in em['asunto']
    assert em['html_len'] > 500  # HTML no vacío


def test_job_sin_email_configurado(app, db_clean, monkeypatch):
    """Si EMAIL_SEBASTIAN no está configurado, retorna False con error claro."""
    from blueprints.auto_plan_jobs import job_weekly_executive_email
    # Forzar USER_EMAILS sin sebastian
    monkeypatch.setattr('config.USER_EMAILS', {'sebastian': ''})
    ok, data, _ = job_weekly_executive_email(app)
    assert ok is False
    assert 'error' in data
