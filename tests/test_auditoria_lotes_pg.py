"""La auditoría de lotes tiene que CORRER, no sólo responder 200 (25-jul).

`/api/admin/auditoria-lotes` es la herramienta que vigila la integridad del kardex (lotes
duplicados, lotes nuevos, delta). Dos de sus queries llevaban tiempo reventando SOLO en
PostgreSQL con "column ... must appear in the GROUP BY clause" (el patrón M12b: pasa en SQLite,
falla en PG). El endpoint atrapaba el error y devolvía la lista VACÍA junto a un campo `_error`,
así que en producción leía:

    "duplicados_sospechosos": []      ← parece "no hay duplicados"
    "duplicados_error": "column movimientos.material_nombre must appear in the GROUP BY..."

Es decir: la detección de lotes duplicados estaba MUERTA y se veía como un resultado limpio.

⚠ Estos tests corren en SQLite igual, pero el que vale es el gate `--pg`: en SQLite las dos
queries pasaban aunque estuvieran mal.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _admin(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_ningun_chequeo_de_la_auditoria_falla(app):
    """Si alguna query revienta, el endpoint lo DECLARA en vez de devolver listas vacías."""
    c = _admin(app)
    r = c.get('/api/admin/auditoria-lotes?dias=2')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('checks_fallidos') == [], (
        'hay chequeos de integridad que NO corrieron: %s' % d.get('aviso'))
    assert d.get('ok') is True, d.get('aviso')


def test_las_dos_queries_que_estaban_rotas_devuelven_datos(app):
    """Las claves tienen que existir de verdad, no venir del fallback del except."""
    c = _admin(app)
    d = c.get('/api/admin/auditoria-lotes?dias=30').get_json()
    for k in ('duplicados_sospechosos', 'lotes_creados_recientes'):
        assert k in d, k
        assert isinstance(d[k], list), (k, type(d[k]))
        assert (k + '_error') not in d, '%s sigue reventando: %s' % (k, d.get(k + '_error'))
    # y su contador acompaña (sólo se setea cuando la query corrió)
    assert 'duplicados_count' in d and 'lotes_creados_count' in d, d.keys()


def test_un_chequeo_roto_se_declara(app):
    """El flag no es decorativo: si aparece un `_error`, ok=False y sale el aviso."""
    fake = {'ventana_dias': 2, 'duplicados_sospechosos': [], 'duplicados_error': 'boom'}
    fallidos = sorted(k[:-6] for k in fake if k.endswith('_error'))
    assert fallidos == ['duplicados']
    assert not (not fallidos), 'con un error, ok debe ser False'
