"""El botón "Dedup mismo día" NO puede cancelar lo que el usuario fijó.

Regla dura del cerebro (#3) y de CLAUDE.md: ningún UPDATE/DELETE masivo puede tocar
`produccion_programada.origen IN ('eos_plan','eos_b2b','eos_retroactivo')`.

Auditoría 25-jul: la PRIMERA pasada de `/api/plan/dedup-mismo-dia` excluía `eos_b2b` y
`eos_retroactivo` pero NO `eos_plan`, así que cancelaba tandas fijas. La segunda pasada de
la misma función sí lo protege, y su propio comentario dice por qué: "un Fijo (eos_plan)
puede ser una 2ª tanda deliberada del mismo producto el mismo día → NUNCA se toca".

Es justo el caso que Abastecimiento acaba de aprender a contar: dos tandas de 20 kg el
mismo día son dos lotes reales.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ DEDUP DIA'


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


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    _sql("DELETE FROM produccion_programada WHERE producto LIKE '%s%%'" % PROD)


def _lote(origen, kg, prod=PROD, dias=6):
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','+%d days'), 1, %s, '%s', 'pendiente')"
         % (prod, dias, kg, origen))


def _estados(prod=PROD):
    db = _db()
    try:
        return [(r[0], r[1]) for r in db.execute(
            "SELECT origen, COALESCE(estado,'') FROM produccion_programada WHERE producto=? ORDER BY id",
            (prod,)).fetchall()]
    finally:
        db.close()


def test_no_cancela_dos_tandas_fijas_del_mismo_dia(app):
    """Dos eos_plan el mismo día son dos lotes deliberados: el botón no puede tocarlos."""
    _limpiar()
    _lote('eos_plan', 20)
    _lote('eos_plan', 20)
    c = _login(app)
    try:
        r = c.post('/api/plan/dedup-mismo-dia', json={'dry_run': False}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        est = _estados()
        assert len(est) == 2, est
        assert all(e != 'cancelado' for _o, e in est), \
            'canceló una tanda FIJA del usuario · %s' % est
    finally:
        _limpiar()


def test_dry_run_tampoco_las_lista(app):
    """Ni siquiera las propone: el preview no debe ofrecer cancelar lo fijo."""
    _limpiar()
    _lote('eos_plan', 20)
    _lote('eos_plan', 20)
    c = _login(app)
    try:
        r = c.get('/api/plan/dedup-mismo-dia')
        assert r.status_code == 200, r.data[:300]
        d = r.get_json() or {}
        _txt = str(d)
        assert PROD not in _txt or (d.get('a_cancelar') in (0, None)) or not d.get('detalle'), \
            'el preview propone cancelar lo fijo · %s' % _txt[:400]
    finally:
        _limpiar()


def test_sigue_deduplicando_las_sugeridas(app):
    """El botón conserva su utilidad: las sugerencias duplicadas del mismo día sí se limpian."""
    _limpiar()
    _lote('eos_canonico', 20, prod=PROD + ' SUG')
    _lote('sugerido', 15, prod=PROD + ' SUG')
    c = _login(app)
    try:
        r = c.post('/api/plan/dedup-mismo-dia', json={'dry_run': False}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        est = _estados(PROD + ' SUG')
        assert sum(1 for _o, e in est if e == 'cancelado') == 1, \
            'debía cancelar exactamente una sugerida duplicada · %s' % est
    finally:
        _limpiar()
