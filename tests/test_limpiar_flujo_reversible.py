# -*- coding: utf-8 -*-
"""Vaciar el libro financiero deja de ser irreversible.

`/api/financiero/limpiar-flujo` vacía los DOS libros de un POST. Está bien protegido (admin +
confirmación explícita en el cuerpo + audit) y existe a propósito para tirar datos de prueba o una
importación equivocada. Lo que NO tenía es vuelta atrás: guardaba **cuántas** filas borró, no
**cuáles**.

Un botón irreversible sobre la contabilidad funciona bien mil veces, y el día que alguien se
equivoca no hay cómo deshacerlo. No se le puso más fricción -- eso trabaría un reset legítimo --
sino red: se respalda antes de borrar y se puede restaurar.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _seed(app, n_egr=3, n_ing=2):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM flujo_egresos")
        c.execute("DELETE FROM flujo_ingresos")
        c.execute("DELETE FROM flujo_respaldo")
        for i in range(n_egr):
            c.execute("INSERT INTO flujo_egresos (fecha, empresa, concepto, categoria, monto, "
                      "periodo, fuente, referencia, creado_por) VALUES "
                      "('2026-08-01','HHA',?, 'MPs', ?, '2026-08', 'compras', ?, 'sebastian')",
                      ('Egreso %d' % i, 1000 * (i + 1), 'REF-%d' % i))
        for i in range(n_ing):
            c.execute("INSERT INTO flujo_ingresos (fecha, empresa, concepto, monto, periodo, "
                      "fuente, referencia) VALUES "
                      "('2026-08-01','HHA',?, ?, '2026-08', 'shopify', ?)",
                      ('Ingreso %d' % i, 5000 * (i + 1), 'ING-%d' % i))
        c.commit()


def _cuenta(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        e = c.execute("SELECT COUNT(*) FROM flujo_egresos").fetchone()[0]
        i = c.execute("SELECT COUNT(*) FROM flujo_ingresos").fetchone()[0]
    return e, i


def _limpiar(admin_client):
    return admin_client.post('/api/financiero/limpiar-flujo',
                             json={'confirmar': 'LIMPIAR_TODO'},
                             headers={'Origin': 'http://localhost'})


def test_lo_borrado_se_puede_DESHACER(app, admin_client):
    _seed(app, 3, 2)
    r = _limpiar(admin_client)
    assert r.status_code == 200, r.data[:300]
    lote = r.get_json().get('respaldo_lote')
    assert lote, 'la limpieza no dice en qué lote quedó respaldado · sin eso no se puede deshacer'
    assert _cuenta(app) == (0, 0), 'no borró'

    r2 = admin_client.post('/api/financiero/restaurar-flujo', json={'lote': lote},
                           headers={'Origin': 'http://localhost'})
    assert r2.status_code == 200, r2.data[:300]
    assert r2.get_json()['restauradas'] == 5
    assert _cuenta(app) == (3, 2), 'no volvió todo'


def test_lo_restaurado_CONSERVA_los_valores(app, admin_client):
    """Restaurar cinco filas vacías sería peor que no restaurar: la cuenta cuadraría y la plata no."""
    from database import get_db
    _seed(app, 2, 1)
    lote = _limpiar(admin_client).get_json()['respaldo_lote']
    admin_client.post('/api/financiero/restaurar-flujo', json={'lote': lote},
                      headers={'Origin': 'http://localhost'})
    with app.app_context():
        c = get_db()
        montos = sorted(float(r[0]) for r in c.execute("SELECT monto FROM flujo_egresos").fetchall())
        conc = c.execute("SELECT concepto FROM flujo_ingresos").fetchone()
    assert montos == [1000.0, 2000.0], 'los montos no volvieron: %s' % montos
    assert conc and conc[0] == 'Ingreso 0', 'el concepto no volvió'


def test_si_NO_pudo_respaldar_NO_borra(app, admin_client, monkeypatch):
    """Un respaldo a medias es peor que ninguno: da la sensación de que se puede volver atrás
    (M134 · una corrección a medias es peor que ninguna)."""
    import blueprints.financiero as F
    _seed(app, 2, 1)

    # se simula un respaldo que guarda de menos
    _orig = F.get_db

    class _ConnFalsa:
        def __init__(self, real):
            self._r = real

        def cursor(self):
            return _CurFalso(self._r.cursor())

        def __getattr__(self, k):
            return getattr(self._r, k)

    class _CurFalso:
        def __init__(self, real):
            self._c = real

        def execute(self, sql, params=()):
            if 'INSERT INTO flujo_respaldo' in sql:
                return self._c            # traga el insert: respalda de menos
            return self._c.execute(sql, params)

        def __getattr__(self, k):
            return getattr(self._c, k)

    monkeypatch.setattr(F, 'get_db', lambda: _ConnFalsa(_orig()))
    r = _limpiar(admin_client)
    monkeypatch.undo()
    assert r.status_code == 500, 'borró aunque el respaldo salió incompleto'
    assert _cuenta(app) == (2, 1), 'se llevó las filas pese al respaldo incompleto'


def test_restaurar_DOS_veces_no_duplica(app, admin_client):
    """El respaldo se MARCA al restaurar, no se borra: el rastro queda, pero no se puede aplicar
    dos veces (si no, deshacer dos clics duplicaría la contabilidad)."""
    _seed(app, 2, 1)
    lote = _limpiar(admin_client).get_json()['respaldo_lote']
    admin_client.post('/api/financiero/restaurar-flujo', json={'lote': lote},
                      headers={'Origin': 'http://localhost'})
    r2 = admin_client.post('/api/financiero/restaurar-flujo', json={'lote': lote},
                           headers={'Origin': 'http://localhost'})
    assert r2.status_code == 404, 'dejó restaurar el mismo lote dos veces'
    assert 'restaur' in (r2.get_json().get('error') or '').lower(), \
        'no distingue "ya se restauró" de "no existe" · son cosas distintas (M100)'
    assert _cuenta(app) == (2, 1), 'duplicó la contabilidad'


def test_los_respaldos_se_pueden_VER(app, admin_client):
    """Un respaldo que existe y que nadie sabe que existe no sirve el día que hace falta (M121)."""
    _seed(app, 1, 1)
    lote = _limpiar(admin_client).get_json()['respaldo_lote']
    r = admin_client.get('/api/financiero/respaldos-flujo')
    assert r.status_code == 200
    lotes = r.get_json()['lotes']
    assert any(x['lote'] == lote and x['filas'] == 2 for x in lotes), \
        'el respaldo no aparece en la lista'


def test_restaurar_es_SOLO_admin(app, logged_client):
    r = logged_client.post('/api/financiero/restaurar-flujo', json={'lote': 'X'},
                           headers={'Origin': 'http://localhost'})
    assert r.status_code in (401, 403), 'cualquiera puede reinyectar el libro financiero'
