"""Tests de los 4 cron jobs ASG · gap del Día 5 ROADMAP.

Cubre: job_desv_plazos, job_cambios_plazos, job_quejas_plazos, job_recalls_plazos.

Estrategia: cada test crea registros con fechas relativas a 'now' que disparan
las condiciones de alerta, ejecuta el job, y assert que el resultado tiene
las claves esperadas + counts correctos.

Los jobs se ejecutan SIN HTTP (llamada directa a la función) para test rápido.
"""
import os
import sqlite3
import sys
from datetime import date, timedelta

import pytest

# api/ debe estar en sys.path (igual que conftest.py)
_api_dir = os.path.join(os.path.dirname(__file__), '..', 'api')
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)


def _seed_desv_atrasada(db_path, dias_atras):
    """Inserta una desviación con fecha_deteccion N días atrás · estado detectada."""
    conn = sqlite3.connect(db_path)
    fecha = (date.today() - timedelta(days=dias_atras)).isoformat()
    conn.execute("""
        INSERT INTO desviaciones (codigo, fecha_deteccion, detectado_por, tipo,
                                     descripcion, estado)
        VALUES (?, ?, 'sebastian', 'otra', 'Test cron desv atrasada', 'detectada')
    """, (f'DESV-TEST-{dias_atras}', fecha))
    conn.commit(); conn.close()


def _cleanup_desvs(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM desviaciones WHERE codigo LIKE 'DESV-TEST-%'")
    conn.execute("DELETE FROM desviaciones_eventos WHERE comentario LIKE '%Test cron%'")
    conn.commit(); conn.close()


def test_job_desv_plazos_sin_atrasos(app, db_clean):
    """Sin desviaciones atrasadas · job retorna 'Sin desviaciones en plazo vencido'."""
    from blueprints.auto_plan_jobs import job_desv_plazos
    ok, resultado, _ = job_desv_plazos(app)
    assert ok is True
    # No assert sobre el mensaje exacto · BD puede tener desv reales de otros tests
    # Lo importante: el job NO crashea con DB vacía o normal
    assert isinstance(resultado, dict)


def test_job_desv_plazos_detecta_sin_clasificar(app, db_clean):
    """Desviación detectada hace 2d → debe aparecer en sin_clasificar_1d."""
    from blueprints.auto_plan_jobs import job_desv_plazos
    db_path = os.environ['DB_PATH']
    _seed_desv_atrasada(db_path, dias_atras=2)
    try:
        ok, resultado, _ = job_desv_plazos(app)
        assert ok is True
        assert resultado.get('sin_clasificar_1d', 0) >= 1
    finally:
        _cleanup_desvs(db_path)


def test_job_cambios_plazos_sin_atrasos(app, db_clean):
    """Sin cambios atrasados · job retorna sin error."""
    from blueprints.auto_plan_jobs import job_cambios_plazos
    ok, resultado, _ = job_cambios_plazos(app)
    assert ok is True
    assert isinstance(resultado, dict)


def test_job_cambios_plazos_detecta_sin_evaluar(app, db_clean):
    """Cambio solicitado hace 6d → sin_evaluar_5d ≥ 1."""
    from blueprints.auto_plan_jobs import job_cambios_plazos
    db_path = os.environ['DB_PATH']
    conn = sqlite3.connect(db_path)
    fecha = (date.today() - timedelta(days=6)).isoformat()
    conn.execute("""
        INSERT INTO control_cambios (codigo, fecha_solicitud, solicitado_por,
                                        tipo, titulo, descripcion, estado)
        VALUES ('CHG-TEST-6d', ?, 'sebastian', 'otro',
                'Test cron cambio',
                'Cambio para test cron de plazos vencidos · debe disparar alerta',
                'solicitado')
    """, (fecha,))
    conn.commit(); conn.close()
    try:
        ok, resultado, _ = job_cambios_plazos(app)
        assert ok is True
        assert resultado.get('sin_evaluar_5d', 0) >= 1
    finally:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM control_cambios WHERE codigo='CHG-TEST-6d'")
        conn.commit(); conn.close()


def test_job_quejas_plazos_sin_atrasos(app, db_clean):
    """Sin quejas atrasadas · job no crashea."""
    from blueprints.auto_plan_jobs import job_quejas_plazos
    ok, resultado, _ = job_quejas_plazos(app)
    assert ok is True
    assert isinstance(resultado, dict)


def test_job_quejas_plazos_detecta_critica_lenta(app, db_clean):
    """Queja crítica + impacto_salud sin responder hace 3d → criticas_lentas_2d ≥ 1."""
    from blueprints.auto_plan_jobs import job_quejas_plazos
    db_path = os.environ['DB_PATH']
    conn = sqlite3.connect(db_path)
    fecha = (date.today() - timedelta(days=3)).isoformat()
    conn.execute("""
        INSERT INTO quejas_clientes (codigo, fecha_recepcion, recibido_por, canal,
                                         cliente_nombre, tipo_queja, descripcion,
                                         impacto_salud, severidad, estado)
        VALUES ('QC-TEST-3d', ?, 'sebastian', 'email',
                'Cliente Test', 'reaccion_adversa',
                'Queja crítica con impacto en salud para test cron de plazos',
                1, 'critica', 'en_triaje')
    """, (fecha,))
    conn.commit(); conn.close()
    try:
        ok, resultado, _ = job_quejas_plazos(app)
        assert ok is True
        assert resultado.get('criticas_lentas_2d', 0) >= 1
    finally:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM quejas_clientes WHERE codigo='QC-TEST-3d'")
        conn.commit(); conn.close()


def test_job_recalls_plazos_sin_atrasos(app, db_clean):
    """Sin recalls atrasados · job no crashea."""
    from blueprints.auto_plan_jobs import job_recalls_plazos
    ok, resultado, _ = job_recalls_plazos(app)
    assert ok is True
    assert isinstance(resultado, dict)


def test_job_recalls_plazos_detecta_sin_clasificar_12h(app, db_clean):
    """Recall iniciado hace 1 día (=24h) → sin_clasificar_12h ≥ 1."""
    from blueprints.auto_plan_jobs import job_recalls_plazos
    db_path = os.environ['DB_PATH']
    conn = sqlite3.connect(db_path)
    # Crear con datetime('now', '-1 day') · 24h atrás (>12h umbral)
    conn.execute("""
        INSERT INTO recalls (codigo, fecha_inicio, iniciado_por, origen,
                                producto, lotes_afectados, motivo, estado, creado_en)
        VALUES ('RCL-TEST-24h', date('now','-1 day'), 'laura', 'hallazgo_interno',
                'PROD-TEST', 'LOTE-X-001',
                'Recall de prueba para test del cron de plazos vencidos',
                'iniciado', datetime('now','-1 day'))
    """)
    conn.commit(); conn.close()
    try:
        ok, resultado, _ = job_recalls_plazos(app)
        assert ok is True
        assert resultado.get('sin_clasificar_12h', 0) >= 1
    finally:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM recalls WHERE codigo='RCL-TEST-24h'")
        conn.commit(); conn.close()


def test_job_recalls_plazos_clase_I_super_critica(app, db_clean):
    """Recall Clase I clasificado hace 2 días sin notificar INVIMA → super crítica."""
    from blueprints.auto_plan_jobs import job_recalls_plazos
    db_path = os.environ['DB_PATH']
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO recalls (codigo, fecha_inicio, iniciado_por, origen,
                                producto, lotes_afectados, motivo, estado,
                                clase_recall, alcance_geografico,
                                clasificado_por, clasificado_at,
                                justificacion_clasificacion)
        VALUES ('RCL-TEST-CI', date('now','-2 day'), 'laura', 'reaccion_adversa',
                'SAH-30ml', 'LOTE-X-002',
                'Recall Clase I de prueba que requiere INVIMA en <24h',
                'clasificado', 'clase_I', 'nacional',
                'laura', datetime('now','-2 day'),
                'Riesgo grave salud · clase I por norma INVIMA')
    """)
    conn.commit(); conn.close()
    try:
        ok, resultado, _ = job_recalls_plazos(app)
        assert ok is True
        # Clase I sin INVIMA > 24h → debe disparar alerta crítica
        assert resultado.get('clase_I_sin_invima_24h', 0) >= 1
    finally:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM recalls WHERE codigo='RCL-TEST-CI'")
        conn.commit(); conn.close()


def test_job_equipos_vencimientos_no_crashea_db_vacia(app, db_clean):
    """Cron de equipos no debe crashear con DB sin equipos vencidos."""
    from blueprints.auto_plan_jobs import job_equipos_vencimientos
    ok, resultado, _ = job_equipos_vencimientos(app)
    assert ok is True
    assert isinstance(resultado, dict)
    # Tier de urgencia: vencidos, urgentes_7d, proximos_30d (todos pueden ser 0)
    if 'mensaje' not in resultado:
        # Si hay equipos detectados, deben venir las claves nuevas
        for k in ('vencidos', 'urgentes_7d', 'proximos_30d'):
            assert k in resultado
