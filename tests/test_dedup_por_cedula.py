"""Fusionar creadores duplicados por CÉDULA, sin perder un solo pago (28-jul).

Sebastián, mirando la ventana de duplicados: sus duplicados reales no eran por nombre sino la
MISMA PERSONA cargada con nombres distintos -- "Valentina Hernandez", "Valentina Peña",
"Valentina Sierra Bernal" y "Val sierra", las cuatro con cédula 1144064620 y 11 pagos entre
todas. La fusión sólo miraba el nombre, así que no las tocaba; y borrarlas a mano habría
perdido esos pagos (el DELETE borra los pagos no-Pagados y deja huérfanos los Pagados).

Dos decisiones que estos tests fijan:

  · la **cédula** SÍ fusiona: es identidad legal, dos fichas con la misma cédula son la misma
    persona;
  · la **cuenta bancaria a secas NO**: dos personas distintas pueden cobrar en la misma cuenta
    (un familiar, un mánager). Fusionarlas juntaría a dos personas reales en una ficha, y eso
    no se deshace con un botón.

Y por encima de todo: la fusión MUEVE, nunca borra. Si al terminar hay menos pagos que al
empezar, la operación se cancela sola.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


CED = '9911144620'
NOMS = ['ZZ Valentina Hernandez', 'ZZ Valentina Pena', 'ZZ Val sierra']


def _sin_indice_unico(app):
    """Simula el estado ANTERIOR a la mig 388, para poder sembrar nombres repetidos.

    Con el índice puesto ya no se pueden crear duplicados por nombre -- que es exactamente
    el punto. Pero la fusión por nombre sigue haciendo falta para los que YA existen en
    producción, así que se prueba contra el estado en que existen. De paso, esto verifica lo
    que más importa: que al terminar la fusión **vuelve a poner el índice**.
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        try:
            cu.execute("DROP INDEX IF EXISTS idx_mktinf_nombre_unq")
            conn.commit()
        except Exception:
            pass


def _hay_indice_unico(app):
    from database import get_db
    with app.app_context():
        cu = get_db().cursor()
        try:
            return cu.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' "
                "AND name='idx_mktinf_nombre_unq'").fetchone()[0] == 1
        except Exception:
            # En PostgreSQL el catálogo es otro.
            return cu.execute(
                "SELECT COUNT(*) FROM pg_indexes WHERE indexname='idx_mktinf_nombre_unq'"
            ).fetchone()[0] == 1


def _limpiar(app, nombres):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for n in nombres:
            for r in cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?", (n,)).fetchall():
                cu.execute("DELETE FROM pagos_influencers WHERE influencer_id=?", (r[0],))
                cu.execute("DELETE FROM marketing_influencers WHERE id=?", (r[0],))
            cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (n,))
        conn.commit()


def _crear(app, nombre, *, cedula='', cuenta='', pagos=0):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado, cedula_nit, cuenta_bancaria) "
                   "VALUES (?,?,?,?)", (nombre, 'Activo', cedula, cuenta))
        # MAX(id), no el primero que aparezca: en estos tests se siembran DOS fichas con el
        # mismo nombre a propósito, así que buscar por nombre devolvería siempre la primera
        # y los pagos de la segunda terminarían colgados de la ficha equivocada.
        iid = cu.execute("SELECT MAX(id) FROM marketing_influencers WHERE nombre=?",
                         (nombre,)).fetchone()[0]
        for k in range(pagos):
            cu.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, "
                       "fecha, estado) VALUES (?,?,?,?,?)",
                       (iid, nombre, 100000 + k, '2026-07-%02d' % (k + 1), 'Pagada'))
        conn.commit()
    return iid


def _pagos_de(app, iid):
    from database import get_db
    with app.app_context():
        return get_db().cursor().execute(
            "SELECT COUNT(*) FROM pagos_influencers WHERE influencer_id=?", (iid,)).fetchone()[0]


def _existe(app, iid):
    from database import get_db
    with app.app_context():
        return get_db().cursor().execute(
            "SELECT COUNT(*) FROM marketing_influencers WHERE id=?", (iid,)).fetchone()[0] == 1


# ═══════════════════════════════════════════════════════════════════════════════

def test_fusiona_por_cedula_y_los_pagos_quedan_todos_en_la_ficha_conservada(app, db_clean):
    """El caso real de Sebastián: cuatro nombres, una cédula, los pagos repartidos."""
    _limpiar(app, NOMS)
    a = _crear(app, NOMS[0], cedula=CED, pagos=4)
    b = _crear(app, NOMS[1], cedula=CED, pagos=0)
    d = _crear(app, NOMS[2], cedula=CED, pagos=6)   # la de más pagos: es la que se conserva
    total = 4 + 0 + 6

    c = _login(app)
    prev = c.post('/api/marketing/influencers/dedup-merge', json={}, headers=_h()).get_json()
    assert prev['ok'] and prev['dry_run']
    mio = [g for g in prev['grupos'] if g['keeper_id'] in (a, b, d)]
    assert mio, 'la vista previa no detectó el grupo por cédula: %s' % prev.get('grupos_por_cedula')
    assert mio[0]['criterio'] == 'cedula'
    assert mio[0]['keeper_id'] == d, 'no eligió la ficha con más pagos'

    r = c.post('/api/marketing/influencers/dedup-merge', json={'apply': True}, headers=_h())
    assert r.status_code == 200, r.data[:300]

    assert _existe(app, d), 'borró la ficha que debía conservar'
    assert not _existe(app, a) and not _existe(app, b)
    assert _pagos_de(app, d) == total, (
        'se perdieron pagos en la fusión: quedaron %d de %d' % (_pagos_de(app, d), total))


def test_la_cuenta_bancaria_compartida_NO_fusiona(app, db_clean):
    """Dos personas distintas pueden cobrar en la misma cuenta (un familiar, un mánager).
    Fusionarlas juntaría a dos personas reales en una sola ficha."""
    NOMS2 = ['ZZ Cuenta Uno', 'ZZ Cuenta Dos']
    _limpiar(app, NOMS2)
    x = _crear(app, NOMS2[0], cedula='9911000001', cuenta='9998887776', pagos=2)
    y = _crear(app, NOMS2[1], cedula='9911000002', cuenta='9998887776', pagos=3)

    c = _login(app)
    prev = c.post('/api/marketing/influencers/dedup-merge', json={}, headers=_h()).get_json()
    tocados = [g for g in prev['grupos'] if x in ([g['keeper_id']] + g['baja_ids'])
               or y in ([g['keeper_id']] + g['baja_ids'])]
    assert not tocados, 'fusionó dos personas distintas por compartir la cuenta: %s' % tocados

    c.post('/api/marketing/influencers/dedup-merge', json={'apply': True}, headers=_h())
    assert _existe(app, x) and _existe(app, y), 'las fusionó igual al aplicar'
    assert _pagos_de(app, x) == 2 and _pagos_de(app, y) == 3


def test_una_cedula_corta_o_vacia_no_agrupa_a_nadie(app, db_clean):
    """Un campo vacío o basura no puede convertir a media agenda en la misma persona."""
    NOMS3 = ['ZZ Sin Cedula A', 'ZZ Sin Cedula B']
    _limpiar(app, NOMS3)
    x = _crear(app, NOMS3[0], cedula='', pagos=1)
    y = _crear(app, NOMS3[1], cedula='12', pagos=1)   # 2 caracteres: por debajo del piso
    c = _login(app)
    prev = c.post('/api/marketing/influencers/dedup-merge', json={}, headers=_h()).get_json()
    tocados = [g for g in prev['grupos'] if x in ([g['keeper_id']] + g['baja_ids'])
               or y in ([g['keeper_id']] + g['baja_ids'])]
    assert not tocados, 'agrupó por una cédula vacía o de dos dígitos: %s' % tocados


def test_sigue_fusionando_por_nombre_repetido(app, db_clean):
    """El criterio viejo no se puede haber roto al agregar el nuevo."""
    NOM = 'ZZ Juanito Repetido'
    _sin_indice_unico(app)
    _limpiar(app, [NOM])
    a = _crear(app, NOM, pagos=1)
    b = _crear(app, NOM, pagos=3)
    c = _login(app)
    prev = c.post('/api/marketing/influencers/dedup-merge', json={}, headers=_h()).get_json()
    mio = [g for g in prev['grupos'] if g['keeper_id'] in (a, b)]
    assert mio and mio[0]['criterio'] == 'nombre'
    assert mio[0]['keeper_id'] == b
    r = c.post('/api/marketing/influencers/dedup-merge', json={'apply': True}, headers=_h())
    assert _pagos_de(app, b) == 4 and not _existe(app, a)
    # Lo que cierra el problema de raíz: al terminar, la protección queda puesta.
    assert r.get_json().get('unique_index') is True
    assert _hay_indice_unico(app), 'la fusión no dejó el índice UNIQUE puesto'


def test_la_vista_previa_no_toca_nada(app, db_clean):
    """Dry-run tiene que ser realmente en seco: es lo que sostiene el confirm."""
    NOM = 'ZZ Previa Intacta'
    _sin_indice_unico(app)
    _limpiar(app, [NOM])
    a = _crear(app, NOM, pagos=2)
    b = _crear(app, NOM, pagos=1)
    c = _login(app)
    c.post('/api/marketing/influencers/dedup-merge', json={}, headers=_h())
    assert _existe(app, a) and _existe(app, b), 'la vista previa borró fichas'
    assert _pagos_de(app, a) == 2 and _pagos_de(app, b) == 1


def test_solo_admin_fusiona(app, db_clean):
    c = _login(app, 'jefferson')
    r = c.post('/api/marketing/influencers/dedup-merge', json={'apply': True}, headers=_h())
    assert r.status_code == 403


def test_la_fusion_queda_auditada_con_el_plan(app, db_clean):
    """Tres meses después la pregunta es "¿qué ficha absorbió a cuál?" · sin el plan en el
    rastro, no hay forma de contestarla."""
    from database import get_db
    NOM = 'ZZ Auditado Merge'
    _sin_indice_unico(app)
    _limpiar(app, [NOM])
    _crear(app, NOM, pagos=1)
    _crear(app, NOM, pagos=2)
    c = _login(app)
    c.post('/api/marketing/influencers/dedup-merge', json={'apply': True}, headers=_h())
    with app.app_context():
        fila = get_db().cursor().execute(
            "SELECT antes, despues FROM audit_log WHERE accion='DEDUP_INFLUENCERS' "
            "ORDER BY id DESC").fetchone()
    assert fila, 'la fusión no dejó rastro'
    assert 'keeper_id' in (fila[0] or ''), 'el rastro no guarda el plan: %s' % (fila[0] or '')[:120]
