"""Quién fabricó cada lote es dato regulado: la asignación automática tiene que dejar rastro.

Último pendiente vivo del roadmap zero-error de mayo (los otros 5 ya estaban cerrados · verificado
uno por uno el 26-jul). `_auto_asignar_operarios` decide QUIÉN dispensa, elabora, envasa y
acondiciona cada lote, y escribía en `produccion_programada` sin `audit_log` — justo la tabla
donde una mutación sin auditar hizo desaparecer la programación del 19-may sin dejar rastro.
"""


def test_la_asignacion_automatica_queda_auditada(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  "estado, origen) VALUES ('PRUEBA AUDIT OPERARIOS','2026-07-27',10,"
                  "'programado','eos_plan')")
        pid = c.lastrowid
        conn.commit()
        from blueprints.programacion import _auto_asignar_operarios
        res = _auto_asignar_operarios(c, pid, '2026-07-27', user='sebastian')
        conn.commit()
        fila = conn.execute(
            "SELECT usuario, despues FROM audit_log WHERE accion='AUTO_ASIGNAR_OPERARIOS' "
            "AND registro_id=?", (str(pid),)).fetchone()
    if res is None:
        # Sin pool de operarios la función aborta a propósito y NO toca la BD:
        # entonces tampoco debe auditar (auditar un no-cambio ensucia la evidencia).
        assert fila is None, 'abortó sin tocar nada pero igual auditó'
        return
    assert fila is not None, 'asignó operarios y no dejó rastro'
    assert fila[0] == 'sebastian'
    assert 'dispensacion' in str(fila[1])


def test_el_audit_guarda_el_estado_previo(app):
    """Sin el 'antes' el rastro no sirve para revertir."""
    import inspect

    from blueprints.programacion import _auto_asignar_operarios
    src = inspect.getsource(_auto_asignar_operarios)
    assert 'previos' in src and 'antes=' in src
    assert src.index('previos = {}') < src.index('UPDATE produccion_programada SET'), (
        'el estado previo hay que leerlo ANTES del UPDATE, o se lee el nuevo')
