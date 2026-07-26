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


# ─── Los datos que faltan se LISTAN, no se cuentan (26-jul · Sebastián) ───────

def test_lista_los_lotes_sin_vencimiento_y_sin_ubicacion(app):
    """Un conteo no se puede accionar; una lista sí. Y con el ESTADO de cada lote se responde
    lo primero que se pregunta: ¿alguno está en cuarentena?"""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    d = c.get("/api/admin/auditoria-lotes?dias=2").get_json()
    for k in ('lotes_sin_vencimiento', 'lotes_sin_ubicacion', 'mps_sin_inci'):
        assert k in d, d.keys()
        assert isinstance(d[k], list), k
        assert '%s_error' % k.replace('lotes_sin_vencimiento', 'lotes_sin_dato') not in d
    assert 'lotes_sin_dato_error' not in d, d.get('lotes_sin_dato_error')
    assert 'mps_sin_inci_error' not in d, d.get('mps_sin_inci_error')
    # cada fila trae lo necesario para ir a completarlo
    for fila in (d['lotes_sin_vencimiento'] + d['lotes_sin_ubicacion']):
        for campo in ('codigo', 'lote', 'stock_g', 'estado', 'en_cuarentena'):
            assert campo in fila, fila
    assert 'lotes_sin_vencimiento_en_cuarentena' in d
    assert d['lotes_sin_vencimiento_count'] == len(d['lotes_sin_vencimiento'])


def test_solo_lista_lotes_CON_stock(app):
    """Un lote agotado sin fecha de vencimiento es historia, no un pendiente."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    d = c.get("/api/admin/auditoria-lotes?dias=2").get_json()
    for fila in d['lotes_sin_vencimiento'] + d['lotes_sin_ubicacion']:
        assert fila['stock_g'] > 0.01, fila


def test_detecta_produccion_en_curso_sin_legajo(app):
    """Ahora que el batch record está vivo, un lote iniciado SIN legajo es un lote fabricándose
    sin registro. Y lo que decide qué hacer con él es si YA descontó la materia prima."""
    from .conftest import TEST_PASSWORD, csrf_headers
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                    "estado, origen, lotes, inicio_real_at, inventario_descontado_at) "
                    "VALUES ('HUERFANA SIN LEGAJO','2026-06-30',20,'en_proceso','eos_plan',1,"
                    "'2026-06-30 10:00:00','2026-06-30 10:05:00')")
        pid = cur.lastrowid
        conn.commit()
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    d = c.get("/api/admin/auditoria-lotes?dias=2").get_json()
    assert 'producciones_en_curso_sin_legajo_error' not in d, d.get('producciones_en_curso_sin_legajo_error')
    mia = [x for x in d['producciones_en_curso_sin_legajo'] if x['produccion_id'] == pid]
    assert mia, 'no detectó la producción en curso sin legajo'
    assert mia[0]['descontó_mp'] is True, 'tiene que decir si la MP ya salió del kardex'
    assert mia[0]['producto'] == 'HUERFANA SIN LEGAJO'
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit()


def test_una_produccion_CON_legajo_no_se_reporta(app):
    """El chequeo no puede gritar sobre lo que sí tiene su registro."""
    from .conftest import TEST_PASSWORD, csrf_headers
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                    "estado, origen, lotes, inicio_real_at) VALUES "
                    "('CON LEGAJO OK','2026-06-30',20,'en_proceso','eos_plan',1,'2026-06-30 10:00:00')")
        pid = cur.lastrowid
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                    "VALUES ('CON LEGAJO OK',1,'aprobado',20000,'test')")
        mbr = cur.lastrowid
        cur.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, "
                    "numero_op, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, fase) "
                    "VALUES (?,1,?,'LOTE-CL-1','OP-CL-1','iniciado','test','2026-06-30 10:00:00',20000,"
                    "'fabricacion')", (mbr, pid))
        conn.commit()
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    d = c.get("/api/admin/auditoria-lotes?dias=2").get_json()
    assert not [x for x in d['producciones_en_curso_sin_legajo'] if x['produccion_id'] == pid]
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM ebr_ejecuciones WHERE produccion_id=?", (pid,))
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.execute("DELETE FROM mbr_templates WHERE producto_nombre='CON LEGAJO OK'")
        conn.commit()
