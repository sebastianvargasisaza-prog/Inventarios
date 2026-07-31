"""¿Qué pasó con esta orden de compra? (31-jul)

Catalina: *"al hacer órdenes de compra se le perdió"*. Hoy eso se contesta con una teoría: hay
más de 30 acciones distintas que tocan una OC, todas quedan en `audit_log`, y nadie tiene cómo
leerlo. Sin un rastro, un "se perdió" termina en una hipótesis dicha con tono de certeza — que es
justo lo que no se puede hacer con la plata de una compra.

Y una OC puede desaparecer por una razón **legítima**: la fusión por proveedor (Sebastián,
14-jul: *"siempre una orden por proveedor"*) mueve los ítems a otra orden y borra ésta. Desde el
lado de quien la creó, la orden simplemente ya no está.

`GET /api/compras/rastro?q=OC-...` responde en una frase: existe / la fusionaron con cuál / la
borraron quién y cuándo.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

OC = 'OC-ZZRASTRO-1'
OC2 = 'OC-ZZRASTRO-2'


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


def _limpiar():
    for o in (OC, OC2):
        _sql("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (o,))
        _sql("DELETE FROM ordenes_compra WHERE numero_oc=?", (o,))


def _rastro(app, q):
    r = _login(app).get('/api/compras/rastro?q=' + q)
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_si_la_orden_existe_lo_dice_con_sus_items(app, db_clean):
    _limpiar()
    _sql("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total, fecha, creado_por) "
         "VALUES (?,?,'Borrador',119000,'2026-07-31','catalina')", (OC, 'ZZ Proveedor'))
    _sql("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, "
         "precio_unitario, subtotal) VALUES (?,?,?,1000,100,100000)", (OC, 'MP-ZZ', 'ZZ material'))
    j = _rastro(app, OC)
    assert j['existe'] and j['existe']['items'] == 1, j
    assert 'EXISTE' in j['veredicto'], j['veredicto']


def test_una_orden_SIN_items_se_declara(app, db_clean):
    """El otro modo de 'perderse': la orden sigue ahí pero vacía. Guardar una edición con la
    lista de ítems vacía los borra todos, y la orden queda en cero sin que nadie lo note."""
    _limpiar()
    _sql("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total, fecha) "
         "VALUES (?,?,'Borrador',0,'2026-07-31')", (OC, 'ZZ Proveedor'))
    j = _rastro(app, OC)
    assert j['existe']['items'] == 0
    assert 'No tiene ítems' in j['veredicto'], j['veredicto']


def test_si_se_FUSIONO_dice_con_cual(app, db_clean):
    """La causa más probable de 'se me perdió': la orden se juntó con otra del mismo proveedor.
    Los ítems no se perdieron -- se movieron -- y eso hay que poder decirlo, no suponerlo."""
    _oc = 'OC-ZZRASTRO-FUS'
    _sql("INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, fecha) "
         "VALUES ('catalina','FUSIONAR_OC_POR_PROVEEDOR','ordenes_compra',?,?, '2026-07-31 09:12:00')",
         (_oc, 'ítems movidos a ' + OC2))
    j = _rastro(app, _oc)
    assert j['existe'] is None
    assert 'fusion' in j['veredicto'].lower(), j['veredicto']
    assert OC2 in j['veredicto'], ('no dice CON CUÁL se fusionó: %s' % j['veredicto'])
    assert 'NO se perdieron' in j['veredicto'], j['veredicto']


def test_si_la_borraron_dice_quien_y_cuando(app, db_clean):
    _oc = 'OC-ZZRASTRO-DEL'
    _sql("INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, fecha) "
         "VALUES ('catalina','ELIMINAR_OC','ordenes_compra',?,?, '2026-07-30 16:40:00')",
         (_oc, 'Eliminó OC ' + _oc + ' (estado Borrador)'))
    j = _rastro(app, _oc)
    assert 'elimina' in j['veredicto'].lower(), j['veredicto']
    assert 'catalina' in j['veredicto'], j['veredicto']
    assert '2026-07-30' in j['veredicto'], j['veredicto']


def test_un_numero_que_nunca_existio_lo_dice_sin_inventar(app, db_clean):
    j = _rastro(app, 'OC-NO-EXISTE-999')
    assert j['existe'] is None and j['n_eventos'] == 0
    assert 'ni orden ni rastro' in j['veredicto'], j['veredicto']
