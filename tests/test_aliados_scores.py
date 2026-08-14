"""El scoring de aliados NUNCA corrió: alias `p.` sin declarar en el FROM.

`BASE = "p.estado NOT IN (...) AND p.cliente_id=?"` sobre `SELECT ... FROM pedidos`
(sin alias) es sintaxis inválida en los dos motores, así que el endpoint daba 500
apenas hubiera UN cliente cargado. Sin clientes la lista sale vacía y el bucle ni
entra, y por eso pasó desapercibido: el barrido de rutas sólo lo destapó cuando otro
test dejó clientes sembrados (M96).

Este test lo ejercita CON datos, que es la única forma de que el guard sirva.
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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_el_scoring_de_aliados_corre_con_clientes_cargados(app, db_clean):
    for sql in ("DELETE FROM pedidos WHERE numero LIKE 'ZAL-%'",
                "DELETE FROM clientes WHERE codigo = 'ZALIADO'"):
        try:
            _exec(sql)
        except Exception:
            pass
    cid = _exec("INSERT INTO clientes (codigo, nombre, empresa, activo) "
                "VALUES ('ZALIADO','Aliado De Prueba','ANIMUS',1)")
    _exec("INSERT INTO pedidos (numero, cliente_id, fecha, estado, empresa, valor_total) "
          "VALUES ('ZAL-1', ?, '2026-05-10', 'Confirmado', 'ANIMUS', 1000000)", (cid,))
    _exec("INSERT INTO pedidos (numero, cliente_id, fecha, estado, empresa, valor_total) "
          "VALUES ('ZAL-2', ?, '2026-07-10', 'Confirmado', 'ANIMUS', 2000000)", (cid,))

    r = _login(app).get('/api/aliados/scores')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    filas = d.get('aliados') or d.get('items') or d.get('scores') or []
    assert any('Aliado De Prueba' in str(f) for f in filas), \
        'el cliente sembrado no aparece en el scoring: %s' % str(d)[:300]
