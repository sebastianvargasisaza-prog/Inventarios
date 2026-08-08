# -*- coding: utf-8 -*-
"""La cola de decisiones no vuelve a leer lo mismo una vez por pago.

`alertas_pago_influencer` se llama una vez por PAGO pendiente, y la cola evalúa varios pagos del
MISMO creador: su historial y su estado se leían una vez por pago aunque fueran idénticos. Medido
con la sonda local: la misma consulta con los mismos parámetros, tres veces, en 64 consultas
totales. Ahora 52 y ninguna repetida.

⚠ El memo es por REQUEST, nunca de módulo: un pago que se acaba de registrar tiene que contar
como antecedente en la carga siguiente, y un cache de módulo lo dejaría invisible sin dar ningún
error (M9). Es una alerta ANTI DOBLE-PAGO: dejarla mirando un historial viejo es exactamente el
daño que viene a evitar.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _contar(admin_client, ruta):
    import collections
    import sqlite3
    vistas = collections.Counter()
    _orig = sqlite3.connect

    def _conectar(*a, **k):
        con = _orig(*a, **k)
        try:
            con.set_trace_callback(lambda s: vistas.update([' '.join(str(s or '').split())]))
        except Exception:
            pass
        return con

    sqlite3.connect = _conectar
    try:
        r = admin_client.get(ruta)
    finally:
        sqlite3.connect = _orig
    return r, vistas


def test_no_repite_consultas(app, admin_client):
    r, vistas = _contar(admin_client, '/api/centro/decisiones')
    assert r.status_code == 200
    repes = {s: n for s, n in vistas.items() if n > 1 and 'pagos_influencers' in s}
    assert not repes, 'vuelve a leer el historial del mismo creador: %s' % list(repes)[:2]
    repes2 = {s: n for s, n in vistas.items() if n > 1 and 'marketing_influencers' in s}
    assert not repes2, 'vuelve a leer el estado del mismo creador: %s' % list(repes2)[:2]


def test_un_pago_NUEVO_cuenta_como_antecedente_en_la_carga_siguiente(app, admin_client):
    """El guard que impide convertir esto en un cache de módulo. Es una alerta anti doble-pago:
    si el historial quedara viejo, dejaría pasar justo el segundo pago que viene a frenar."""
    from database import get_db
    try:
        from blueprints.marketing import alertas_pago_influencer as alertas
    except ImportError:
        from marketing import alertas_pago_influencer as alertas

    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM pagos_influencers WHERE influencer_nombre='MEMO ALERTA'")
        c.execute("DELETE FROM marketing_influencers WHERE nombre='MEMO ALERTA'")
        c.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('MEMO ALERTA','activo')")
        c.commit()
        iid = c.execute("SELECT id FROM marketing_influencers WHERE nombre='MEMO ALERTA'").fetchone()[0]

    with app.app_context():
        a1 = alertas(get_db(), influencer_id=iid, nombre='MEMO ALERTA', valor=100000,
                     fecha_publicacion='', entregable='')
    assert not a1, 'avisa de un doble pago sin que haya ninguno'

    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
                  "estado) VALUES (?, 'MEMO ALERTA', 100000, date('now','-5 hours'), 'Pagada')",
                  (iid,))
        c.commit()

    with app.app_context():
        a2 = alertas(get_db(), influencer_id=iid, nombre='MEMO ALERTA', valor=100000,
                     fecha_publicacion='', entregable='')
    assert a2, ('el memo sobrevivió al request · la alerta anti doble-pago quedaría mirando un '
                'historial viejo, que es justo el daño que viene a evitar')

    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM pagos_influencers WHERE influencer_nombre='MEMO ALERTA'")
        c.execute("DELETE FROM marketing_influencers WHERE nombre='MEMO ALERTA'")
        c.commit()


def test_sin_contexto_de_flask_sigue_avisando(app):
    """Los crons la llaman sin request · ahí no hay memo y tiene que funcionar igual."""
    from database import db_connect
    try:
        from blueprints.marketing import alertas_pago_influencer as alertas
    except ImportError:
        from marketing import alertas_pago_influencer as alertas
    con = db_connect(timeout=30)
    try:
        assert alertas(con, influencer_id=999999, nombre='NADIE', valor=1,
                       fecha_publicacion='', entregable='') == []
    finally:
        con.close()
