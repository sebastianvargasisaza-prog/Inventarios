"""Envases MEE · MEDIDA por código (Catalina 15-jul).

Catalina no sabía qué gotero pedir en la OC porque los 6 decían todos 'GOTERO' sin la
medida. Ahora `maestro_mee.medida` (30ml, 89mm para goteros) se muestra en el inventario
(/api/mee/stock), en el dropdown de la OC (/api/mee) y se edita desde el modal Ajustar.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _seed(cod, medida=''):
    _exec("INSERT OR REPLACE INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,stock_actual,stock_minimo,unidad,medida) "
          "VALUES (?,?, 'Gotero','China','Activo',100,0,'und',?)", (cod, 'GOTERO', medida))


def _medida_db(cod):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute("SELECT medida FROM maestro_mee WHERE codigo=?", (cod,)).fetchone()
        return (r[0] if r else None)
    finally:
        conn.close()


def test_medida_sale_en_stock_y_en_lookup_oc(app, db_clean):
    _seed('MEE-GOT-TEST1', '89mm')
    _seed('MEE-GOT-TEST2', '65mm')
    c = _login(app)
    # inventario
    st = c.get('/api/mee/stock').get_json()['items']
    g1 = next(x for x in st if x['codigo'] == 'MEE-GOT-TEST1')
    assert g1.get('medida') == '89mm', g1
    # dropdown de la OC (/api/mee)
    lk = c.get('/api/mee?limit=1000').get_json()['items']
    l1 = next(x for x in lk if x['codigo'] == 'MEE-GOT-TEST1')
    l2 = next(x for x in lk if x['codigo'] == 'MEE-GOT-TEST2')
    assert l1.get('medida') == '89mm' and l2.get('medida') == '65mm', (l1, l2)


def test_editar_medida_desde_ajustar(app, db_clean):
    _seed('MEE-GOT-TEST3', '')
    c = _login(app)
    r = c.post('/api/mee/MEE-GOT-TEST3/ajustar',
               json={'medida': '72mm'}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _medida_db('MEE-GOT-TEST3') == '72mm'


def test_editar_medida_via_put(app, db_clean):
    _seed('MEE-GOT-TEST4', '10mm')
    c = _login(app)
    r = c.put('/api/mee/MEE-GOT-TEST4', json={'medida': '55mm'}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _medida_db('MEE-GOT-TEST4') == '55mm'


def test_migracion_agrega_columna(app, db_clean):
    """La mig 354 debe haber agregado la columna medida (si no, el SELECT falla)."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(maestro_mee)").fetchall()]
        assert 'medida' in cols, cols
    finally:
        conn.close()
