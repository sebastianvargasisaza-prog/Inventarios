"""El cron de las 4:50 no puede cancelar la 2ª tanda FIJA del usuario.

`_cerrar_pendientes_ya_producidos` (lo llama `sync_fabricacion_calendario`, 4:50) cierra el
pendiente de un (producto, fecha) que ya tiene un hermano completado. Excluía solo `eos_b2b`,
así que se llevaba puestas las tandas `eos_plan`: programás dos lotes de 20 kg para el mismo
día, la planta produce uno, y de madrugada el otro desaparece. Encima Abastecimiento deja de
contar sus 20 kg de MP (lo cancelado no suma) → sub-compra silenciosa.

Es el gemelo AUTOMÁTICO del bug que ya se cerró en `/api/plan/dedup-mismo-dia`, y el más
peligroso de los dos porque nadie aprieta un botón: pasa solo.
"""
import os
import sqlite3

PROD = 'ZZ CRON FIJO'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _limpiar():
    _sql("DELETE FROM produccion_programada WHERE producto='%s'" % PROD)


def _lote(origen, kg):
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','+4 days'), 1, %s, '%s', 'pendiente')"
         % (PROD, kg, origen))


def _completar(origen):
    """Marca como producida UNA fila del origen dado (la de menor id)."""
    _sql("UPDATE produccion_programada SET estado='completado', fin_real_at=datetime('now') "
         "WHERE id IN (SELECT MIN(id) FROM produccion_programada "
         "WHERE producto='%s' AND origen='%s')" % (PROD, origen))


def _estados():
    db = _db()
    try:
        return [(r[0], r[1]) for r in db.execute(
            "SELECT origen, COALESCE(estado,'') FROM produccion_programada WHERE producto=? ORDER BY id",
            (PROD,)).fetchall()]
    finally:
        db.close()


def _correr_cron(app):
    with app.app_context():
        from database import get_db
        from blueprints.plan import _cerrar_pendientes_ya_producidos
        return _cerrar_pendientes_ya_producidos(get_db())


def test_cron_no_cancela_la_segunda_tanda_fija(app):
    """Dos tandas fijas, se produce una: la otra sigue viva."""
    _limpiar()
    _lote('eos_plan', 20)
    _lote('eos_plan', 20)
    _completar('eos_plan')
    try:
        _correr_cron(app)
        est = _estados()
        assert not [e for _o, e in est if e == 'cancelado'], \
            'el cron canceló una tanda FIJA del usuario · %s' % est
    finally:
        _limpiar()


def test_cron_si_cierra_una_sugerida_redundante(app):
    """Conserva su utilidad: la SUGERIDA pendiente de un día ya producido sí se cierra."""
    _limpiar()
    _lote('eos_plan', 20)
    _lote('eos_canonico', 20)
    _completar('eos_plan')
    try:
        _correr_cron(app)
        est = dict(_estados())
        assert est.get('eos_canonico') == 'cancelado', \
            'la sugerida redundante debía cerrarse · %s' % _estados()
    finally:
        _limpiar()
