"""Mover un lote: ¿arrastra la cadena o no? Lo decide el MOTIVO, no el sistema (25-jul).

Sebastián: "si muevo el lote porque no llegó la materia prima, el lote ya va tarde; si el próximo
se mueve pues llegará tarde. Diferente a que lo mueva porque quiero adelantar algo y no altera los
tiempos de producción. Entonces depende."

Por eso:
  · default = mueve SOLO ese lote (lo no destructivo)
  · `reprogramar_cadena: true` = corre también los siguientes a nueva_fecha + k×cadencia
  · la respuesta informa `siguientes_en_cadena` para que la UI pueda ofrecerlo sólo si aplica

⚠ Además: la cadencia NO se guardaba en los lotes creados por el modal de horizonte (sólo la
escribía el generador automático), así que en las cadenas hechas a mano el re-espaciado nunca
podía dispararse. Y el bloque vivía dentro de un `except: pass`, moviendo N lotes sin auditoría.
"""
import datetime as _dt
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ CADENA MOVER'


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _limpiar():
    db = _db()
    try:
        db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        db.commit()
    finally:
        db.close()


def _habil(d):
    from blueprints.plan import es_festivo_colombia
    while d.weekday() >= 5 or es_festivo_colombia(d):
        d += _dt.timedelta(days=1)
    return d


def _sembrar_cadena(cad=30, n=4):
    """Cadena de n lotes cada `cad` días, con la cadencia GUARDADA en cada lote."""
    _limpiar()
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
    base = _habil(hoy + _dt.timedelta(days=30))
    ids, fechas = [], []
    db = _db()
    try:
        for k in range(n):
            f = _habil(base + _dt.timedelta(days=cad * k))
            db.execute(
                "INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,"
                "cantidad_kg,cadencia_dias) VALUES (?,?,1,'pendiente','eos_plan',20,?)",
                (PROD, f.isoformat(), cad))
            ids.append(db.execute("SELECT id FROM produccion_programada WHERE producto=? "
                                  "ORDER BY id DESC LIMIT 1", (PROD,)).fetchone()[0])
            fechas.append(f.isoformat())
        db.commit()
    finally:
        db.close()
    return ids, fechas


def _fecha(pid):
    db = _db()
    try:
        r = db.execute("SELECT substr(fecha_programada,1,10) FROM produccion_programada WHERE id=?",
                       (pid,)).fetchone()
        return r[0] if r else None
    finally:
        db.close()


def test_por_defecto_mueve_SOLO_ese_lote(app):
    """Adelanto puntual: no puede desarmarme el plan de 2 años."""
    c = _login(app)
    ids, fechas = _sembrar_cadena()
    try:
        nueva = _habil(_dt.date.fromisoformat(fechas[0]) + _dt.timedelta(days=5)).isoformat()
        r = c.post('/api/plan/proximas/%d/reprogramar' % ids[0], json={'nueva_fecha': nueva})
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        d = r.get_json()
        assert d['cadena_recolocados'] == 0, d
        assert _fecha(ids[0]) == nueva
        for pid, f0 in zip(ids[1:], fechas[1:]):
            assert _fecha(pid) == f0, 'los siguientes NO se debían mover'
    finally:
        _limpiar()


def test_informa_cuantos_siguen_para_poder_ofrecerlo(app):
    """La respuesta trae `siguientes_en_cadena` · la UI pregunta sólo cuando aplica."""
    c = _login(app)
    ids, fechas = _sembrar_cadena(n=4)
    try:
        nueva = _habil(_dt.date.fromisoformat(fechas[0]) + _dt.timedelta(days=5)).isoformat()
        d = c.post('/api/plan/proximas/%d/reprogramar' % ids[0],
                   json={'nueva_fecha': nueva}).get_json()
        assert d['siguientes_en_cadena'] == 3, d
        assert d['cadencia_dias'] == 30, d
    finally:
        _limpiar()


def test_con_la_bandera_corre_toda_la_cadena(app):
    """Atraso por falta de MP: los siguientes se corren a nueva_fecha + k×cadencia."""
    c = _login(app)
    ids, fechas = _sembrar_cadena(cad=30, n=4)
    try:
        nueva = _habil(_dt.date.fromisoformat(fechas[0]) + _dt.timedelta(days=14)).isoformat()
        r = c.post('/api/plan/proximas/%d/reprogramar' % ids[0],
                   json={'nueva_fecha': nueva, 'reprogramar_cadena': True, 'razon': 'falta_mp'})
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        d = r.get_json()
        assert d['cadena_recolocados'] == 3, d
        base = _dt.date.fromisoformat(nueva)
        for k, pid in enumerate(ids[1:], start=1):
            esperado = _habil(base + _dt.timedelta(days=30 * k)).isoformat()
            assert _fecha(pid) == esperado, (pid, _fecha(pid), esperado)
    finally:
        _limpiar()


def test_la_cadena_recolocada_NUNCA_cae_en_finde_ni_festivo(app):
    """El re-espaciado usa el helper canónico de día de producción (L-V no festivo)."""
    from blueprints.plan import es_festivo_colombia
    c = _login(app)
    ids, fechas = _sembrar_cadena(cad=7, n=6)   # cadencia semanal → cae seguido en finde
    try:
        nueva = _habil(_dt.date.fromisoformat(fechas[0]) + _dt.timedelta(days=3)).isoformat()
        c.post('/api/plan/proximas/%d/reprogramar' % ids[0],
               json={'nueva_fecha': nueva, 'reprogramar_cadena': True})
        for pid in ids[1:]:
            f = _dt.date.fromisoformat(_fecha(pid))
            assert f.weekday() < 5, '%s cayó %s' % (f, f.strftime('%A'))
            assert not es_festivo_colombia(f), '%s es festivo' % f
    finally:
        _limpiar()


def test_mover_la_cadena_deja_rastro_en_auditoria(app):
    """Mover producción sin auditar es lo que hizo desaparecer un plan entero el 19-may.

    El bloque vivía dentro de un `except: pass`: movía N lotes en silencio, sin audit_log.
    """
    c = _login(app)
    ids, fechas = _sembrar_cadena(n=3)
    try:
        nueva = _habil(_dt.date.fromisoformat(fechas[0]) + _dt.timedelta(days=10)).isoformat()
        c.post('/api/plan/proximas/%d/reprogramar' % ids[0],
               json={'nueva_fecha': nueva, 'reprogramar_cadena': True, 'razon': 'falta_mp'})
        db = _db()
        try:
            # ⚠ `audit_log.registro_id` es TEXT (el helper hace str(...)). Comparar contra un
            # entero pasa en SQLite pero en PostgreSQL revienta con
            # "operator does not exist: text = smallint" → siempre comparar como texto.
            n = db.execute("SELECT COUNT(*) FROM audit_log WHERE accion='REPROGRAMAR_CADENA' "
                           "AND registro_id=?", (str(ids[0]),)).fetchone()[0]
        finally:
            db.close()
        assert n >= 1, 'correr la cadena DEBE dejar rastro'
    finally:
        _limpiar()


def test_el_modal_de_horizonte_guarda_la_cadencia_en_cada_lote(app):
    """Sin esto, "correr los siguientes" es imposible en una cadena hecha a mano.

    Sólo el generador automático (que Sebastián no usa) escribía `cadencia_dias`, así que en sus
    324 lotes la columna venía vacía y el re-espaciado nunca podía dispararse.
    """
    c = _login(app)
    _limpiar()
    try:
        r = c.post('/api/plan/programar-cadencia-producto',
                   json={'producto': PROD, 'kg_por_lote': 20.0, 'interval_dias': 45,
                         'dias_hasta_primera': 30, 'anios': 1})
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        db = _db()
        try:
            filas = db.execute("SELECT COALESCE(cadencia_dias,0) FROM produccion_programada "
                               "WHERE producto=? AND COALESCE(estado,'')<>'cancelado'",
                               (PROD,)).fetchall()
        finally:
            db.close()
        assert filas, 'la cadena debe existir'
        assert all(int(f[0]) == 45 for f in filas), \
            'cada lote debe llevar la cadencia que definió el usuario · %s' % filas
    finally:
        _limpiar()
