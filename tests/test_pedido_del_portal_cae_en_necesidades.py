"""El pedido que hace un cliente en el portal cae en Necesidades por cliente.

Sebastián 14-ago-2026: "ahora que ya hicimos módulo clientes, hacen pedido y cae
aquí?".

Cae, pero faltaba el eslabón de siempre: dar el acceso NO dejaba al cliente en
`clientes_b2b_maestro`, que es de donde salen las secciones de esa pantalla. O sea
que el cliente no aparecía hasta pedir, y si el identificador del portal no era el
mismo del maestro, al pedir salía DOS VECES (su fila en cero y otra sección con los
pedidos). Un alta que alguien tiene que acordarse de completar en otro lado termina
sin completarse (M189).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM pedidos_b2b WHERE cliente_id LIKE 'ZNEC%'",
                "DELETE FROM portal_clientes_credenciales WHERE cliente_id LIKE 'ZNEC%'",
                "DELETE FROM portal_clientes_credenciales WHERE email LIKE '%@znec.test'",
                "DELETE FROM clientes_b2b_maestro WHERE cliente_id LIKE 'ZNEC%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _crear_acceso(adm, cid, nombre, email=None):
    return adm.post('/api/admin/portal/credenciales', json={
        'cliente_id': cid, 'cliente_nombre': nombre,
        'email': email or (cid.lower() + '@znec.test'),
        'password': 'ClavePortal123'}, headers=_h())


def test_dar_el_acceso_deja_al_cliente_en_la_cola(app, db_clean):
    _limpiar()
    adm = _login(app)
    r = _crear_acceso(adm, 'ZNEC1', 'Cliente Necesidades Uno')
    assert r.status_code in (200, 201), r.data
    assert r.get_json().get('ficha_cliente') in ('creada', 'reusada', 'enlazada')
    fila = _q("SELECT cliente_nombre, activo FROM clientes_b2b_maestro WHERE cliente_id='ZNEC1'")
    assert fila, 'el cliente no quedó en el maestro: no aparece en Necesidades hasta que pida'
    assert fila[0][0] == 'Cliente Necesidades Uno' and fila[0][1] == 1


def test_si_ya_hay_ficha_con_ese_nombre_el_acceso_se_engancha_a_ella(app, db_clean):
    """Si no, el mismo cliente sale dos veces: su fila en cero y otra con los pedidos."""
    _limpiar()
    _exec("INSERT INTO clientes_b2b_maestro (cliente_id, cliente_nombre, activo, tipo) "
          "VALUES ('ZNEC-VIEJO','Kelly Guerra Prueba',1,'B2B')")
    adm = _login(app)
    r = _crear_acceso(adm, 'ZNEC-NUEVO', 'kelly  guerra   prueba')
    assert r.status_code in (200, 201), r.data
    d = r.get_json()
    assert d['ficha_cliente'] == 'enlazada', d
    assert d['cliente_id'] == 'ZNEC-VIEJO', 'no adoptó el identificador de la ficha existente'
    # y no se duplicó la ficha
    assert len(_q("SELECT 1 FROM clientes_b2b_maestro WHERE cliente_nombre LIKE 'Kelly Guerra Prueba'")) == 1


def test_con_dos_fichas_del_mismo_nombre_no_adivina(app, db_clean):
    _limpiar()
    for cid in ('ZNEC-A', 'ZNEC-B'):
        _exec("INSERT INTO clientes_b2b_maestro (cliente_id, cliente_nombre, activo, tipo) "
              "VALUES (?,'Cliente Repetido',1,'B2B')", (cid,))
    adm = _login(app)
    r = _crear_acceso(adm, 'ZNEC-C', 'Cliente Repetido')
    assert r.status_code in (200, 201), r.data
    d = r.get_json()
    assert d['cliente_id'] == 'ZNEC-C', 'se enganchó a una de las dos sin poder saber cuál'
    assert d['aviso'], 'no declaró la ambigüedad'


def test_el_pedido_del_portal_aparece_en_necesidades_bajo_su_cliente(app, db_clean):
    """La pregunta de Sebastián, medida de punta a punta."""
    _limpiar()
    prod = 'ZNEC PRODUCTO'
    try:
        _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,10,1)",
              (prod,))
    except Exception:
        pass
    adm = _login(app)
    assert _crear_acceso(adm, 'ZNEC9', 'Cliente Que Pide').status_code in (200, 201)

    cli = app.test_client()
    assert cli.post('/api/portal/login', json={'email': 'znec9@znec.test',
                                               'password': 'ClavePortal123'}).status_code == 200
    r = cli.post('/api/portal/pedidos', json={
        'producto_nombre': prod, 'cantidad_uds': 300, 'ml_unidad': 30,
        'fecha_estimada': '2026-12-01', 'urgencia': 'media', 'notas': 'desde el portal'})
    assert r.status_code in (200, 201), r.data

    # el pedido nace pendiente (entra al plan sólo cuando alguien lo confirma)
    assert _q("SELECT estado FROM pedidos_b2b WHERE cliente_id='ZNEC9'")[0][0] == 'pendiente'

    d = adm.get('/api/plan/necesidades').get_json()
    clientes = d.get('clientes') or []
    mio = [c for c in clientes if c.get('cliente_id') == 'ZNEC9']
    assert mio, 'el pedido del portal no aparece en Necesidades por cliente'
    assert mio[0].get('pedidos'), 'el cliente aparece pero sin su pedido'
    # y NO aparece duplicado (una fila con el pedido y otra vacía)
    assert len(mio) == 1, 'el mismo cliente aparece dos veces'
