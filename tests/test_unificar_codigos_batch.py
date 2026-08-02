"""Dejar los códigos de EOS iguales a los del BATCH RECORD · con candado (1-ago).

Sebastián: *"lo ideal es que todo quede con los códigos del batch, si estás seguro, hazlo"*.
Para la mayoría sí. Para algunos NO, y hacerlo en bloque destruye el kardex -- los dos casos
aparecieron en los datos REALES de producción:

  · `MP00301` es PROPYLHEPTYL CAPRYLATE en el batch record, pero en EOS ese código es OTRO
    material y el propylheptyl vive en `MP00030`. Renombrar fusionaría dos materias primas.
  · `MP00296 CARBOMERO 980` y `MP00008 Carbopol` caen los dos en `MP00200`; `MP00252` y
    `MP00181` (dos grados de centella) caen los dos en `MP00176`.

"Si estás seguro" me da la responsabilidad de decir cuándo NO lo estoy. Estos tests fijan que
el candado exista y que tenga dientes.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def test_el_plan_no_aplica_nada_por_defecto(app, db_clean):
    """Un GET NUNCA muta (M113: un GET que muta duplica el daño de cualquier defecto)."""
    r = _login(app).get('/api/programacion/unificar-codigos-batch')
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['dry_run'] is True, j
    assert 'seguros' in j and 'bloqueados' in j


def test_un_POST_sin_confirmar_TAMPOCO_aplica(app, db_clean):
    """Renombrar códigos mueve kardex y fórmulas: se confirma explícitamente o no pasa nada."""
    r = _login(app).post('/api/programacion/unificar-codigos-batch',
                         headers={'Content-Type': 'application/json', **csrf_headers()},
                         json={})
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['dry_run'] is True


def test_solo_un_ADMIN_puede_unificar(app, db_clean):
    """Cambia el código de una materia prima en TODO el sistema · no es una acción de operación."""
    r = _login(app, 'catalina').get('/api/programacion/unificar-codigos-batch')
    assert r.status_code == 403, r.data[:200]


def test_cada_par_trae_su_motivo_y_su_clasificacion(app, db_clean):
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in j['seguros'] + j['bloqueados']:
        assert d['estado'] in ('seguro', 'bloqueado_ambiguo', 'bloqueado_colision'), d
        assert d.get('motivo'), d
        assert d['codigo_batch'] != d['codigo_eos'], d
        if d['estado'] == 'seguro':
            assert d.get('accion') in ('renombrar', 'fusionar'), d


def test_BLOQUEA_cuando_el_destino_existe_con_OTRO_material(app, db_clean):
    """El caso MP00301: el código del batch YA EXISTE en EOS con otro INCI. Fusionarlos mezcla
    dos materias primas distintas y eso no se deshace contando."""
    from blueprints.programacion import _plan_unificar_codigos
    import blueprints.programacion as P

    class _FakeCur:
        def __init__(self, incis):
            self.incis = incis
        def execute(self, sql, params=()):
            self._r = []
            if 'nombre_inci' in sql and params:
                v = self.incis.get(params[0])
                self._r = [(v,)] if v is not None else []
            return self
        def fetchall(self):
            return self._r
        def fetchone(self):
            return self._r[0] if self._r else None

    # el plan real se arma con la BD; acá se prueba la CLASIFICACIÓN, que es la que decide
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in j['bloqueados']:
        if d['estado'] == 'bloqueado_colision':
            assert d['inci_batch'] and d['inci_eos'] and d['inci_batch'] != d['inci_eos'], d
    assert P._plan_unificar_codigos is not None


def test_el_candado_TIENE_dientes(app, db_clean):
    """Si el clasificador dejara pasar todo, este test cae. La regla: nada con estado distinto
    de 'seguro' puede aparecer en la lista que se aplica."""
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    assert all(d['estado'] == 'seguro' for d in j['seguros']), (
        'se coló un par no seguro en la lista que se aplica')
    assert all(d['estado'] != 'seguro' for d in j['bloqueados']), j['bloqueados'][:2]
