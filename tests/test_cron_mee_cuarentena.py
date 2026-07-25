"""El cron que avisa de ENVASES esperando liberación de Calidad (INVIMA · 25-jul).

Sebastián: "los envases sí necesitan revisión, solo que todos los actuales no la tienen".
En producción había 15 lotes en cuarentena de recepciones de días atrás y NADA le avisaba a
nadie: el flujo se usa al recibir, pero la liberación no ocurre porque el pendiente es
invisible. Este cron lo hace visible, y es el paso previo para poder encender el gate de
envasado (hoy apagado a propósito · prenderlo con backlog frenaría la planta).

⚠ Este test existe además porque el job usaba `timezone.utc` y `timezone` NO está importado
a nivel de módulo en auto_plan_jobs.py: habría muerto con NameError dentro del cron, en
silencio. Correr el job de verdad es la única forma de cazar eso.
"""
import os
import sqlite3

MEE = 'ZZMEE-CUAR'


def _sql(*stmts):
    db = sqlite3.connect(os.environ['DB_PATH'], timeout=15)
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _limpiar():
    _sql("DELETE FROM movimientos_mee WHERE mee_codigo='%s'" % MEE,
         "DELETE FROM maestro_mee WHERE codigo='%s'" % MEE)


def test_job_corre_y_cuenta_los_pendientes(app):
    """Corre el job DE VERDAD: es lo único que caza un NameError escondido en el cron."""
    from blueprints.auto_plan_jobs import job_mee_cuarentena_pendiente
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,unidad) "
         "VALUES ('%s','Frasco test cuarentena','Envase','und')" % MEE,
         "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,estado,fecha,responsable) "
         "VALUES ('%s','Entrada',500,'CUARENTENA',date('now','-10 days'),'catalina')" % MEE,
         "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,estado,fecha,responsable) "
         "VALUES ('%s','Entrada',200,'CUARENTENA',date('now'),'catalina')" % MEE)
    try:
        ok, res, _ = job_mee_cuarentena_pendiente(app)
        assert ok is True, res
        assert res['pendientes'] >= 2, res
        assert res['con_mas_de_7d'] >= 1, ('el de hace 10 días debe contar como viejo', res)
    finally:
        _limpiar()


def test_lo_liberado_deja_de_contar(app):
    """Al liberar el lote (CUARENTENA → VIGENTE) el pendiente baja: el aviso no queda pegado."""
    from blueprints.auto_plan_jobs import job_mee_cuarentena_pendiente
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,unidad) "
         "VALUES ('%s','Frasco test cuarentena','Envase','und')" % MEE,
         "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,estado,fecha,responsable) "
         "VALUES ('%s','Entrada',500,'CUARENTENA',date('now'),'catalina')" % MEE)
    try:
        _ok1, antes, _ = job_mee_cuarentena_pendiente(app)
        _sql("UPDATE movimientos_mee SET estado='VIGENTE' WHERE mee_codigo='%s'" % MEE)
        _ok2, despues, _ = job_mee_cuarentena_pendiente(app)
        assert despues['pendientes'] == antes['pendientes'] - 1, (antes, despues)
    finally:
        _limpiar()
