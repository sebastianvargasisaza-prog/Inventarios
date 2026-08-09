# -*- coding: utf-8 -*-
"""Las tres decisiones del maestro de envases que cambian lo que se compra dejan quién.

M139 lo dejó escrito con un caso concreto: *"toda acción que cambia un PUENTE de material se
audita con el destino previo -- sin él no se puede revertir, y el puente 184 existía desde junio
sin que nadie supiera porque se creó sin rastro"*. La regla estaba y el endpoint que escribe el
puente seguía mudo.

Las tres tienen la misma forma: no dan error, cambian lo que se compra o lo que se descuenta, y
sin el valor ANTERIOR no se pueden deshacer.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

COD = 'RM-SERIG-01'


def _sembrar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM maestro_mee WHERE codigo IN (?,?,?)",
                  (COD, 'RM-BASE-A', 'RM-BASE-B'))
        for cod, desc in ((COD, 'FRASCO SERIGRAFIADO NOVA'), ('RM-BASE-A', 'FRASCO BASE A'),
                          ('RM-BASE-B', 'FRASCO BASE B')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, "
                      "stock_minimo) VALUES (?,?,'Frasco',0,0)", (cod, desc))
        c.commit()


def _rastro(app, accion):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT usuario, COALESCE(antes,''), COALESCE(despues,'') FROM audit_log "
            " WHERE accion=? AND registro_id=? ORDER BY id DESC", (accion, COD)).fetchall()


def test_el_PUENTE_base_serigrafiado_guarda_de_donde_venia(app, admin_client):
    """Cambiar el puente cambia qué envase se descuenta y cuál se compra. Si el rastro no guarda
    el destino ANTERIOR no se puede revertir: es exactamente el caso del puente 184 (M139)."""
    _sembrar(app)
    r1 = admin_client.post('/api/admin/mee-base', json={'codigo': COD, 'base': 'RM-BASE-A'},
                           headers={'Origin': 'http://localhost'})
    assert r1.status_code == 200, r1.data[:200]
    r2 = admin_client.post('/api/admin/mee-base', json={'codigo': COD, 'base': 'RM-BASE-B'},
                           headers={'Origin': 'http://localhost'})
    assert r2.status_code == 200, r2.data[:200]
    filas = _rastro(app, 'MEE_PUENTE_BASE')
    assert filas, 'cambiar el puente base<->serigrafiado no dejó rastro'
    assert filas[0][0], 'el rastro no dice QUIÉN'
    assert 'RM-BASE-A' in filas[0][1], \
        'el rastro no guarda el puente ANTERIOR (no se puede revertir): %s' % filas[0][1][:200]
    assert 'RM-BASE-B' in filas[0][2]
    assert r2.get_json().get('base_anterior') == 'RM-BASE-A', \
        'la respuesta no informa desde qué base venía'


def test_el_METODO_de_marcacion_deja_rastro(app, admin_client):
    """Decide si el envase sale a serigrafía y a qué proveedor se le paga."""
    _sembrar(app)
    r = admin_client.post('/api/admin/marcacion-envase',
                          json={'codigo': COD, 'marcacion_tipo': 'serigrafia',
                                'marcacion_proveedor': 'PROVEEDOR X'},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.data[:200]
    filas = _rastro(app, 'MEE_MARCACION')
    assert filas and filas[0][0], 'el método de marcación no deja quién'
    assert 'serigrafia' in filas[0][2]


def test_el_MINIMO_del_envase_deja_rastro_y_el_valor_previo(app, admin_client):
    """El mínimo es lo que dispara la sugerencia de comprar: subirlo de más compra de más."""
    _sembrar(app)
    admin_client.put('/api/maestro-mps/%s/mee-stock-minimo' % COD, json={'stock_minimo': 500},
                     headers={'Origin': 'http://localhost'})
    r = admin_client.put('/api/maestro-mps/%s/mee-stock-minimo' % COD,
                         json={'stock_minimo': 900}, headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.data[:200]
    filas = _rastro(app, 'MEE_STOCK_MINIMO')
    assert filas and filas[0][0], 'el mínimo no deja quién'
    assert '500' in filas[0][1], 'no guarda el mínimo anterior: %s' % filas[0][1][:150]
    assert '900' in filas[0][2]
