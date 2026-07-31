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


# ══ que no se pierda una orden sin que nadie lo pida (31-jul) ═══════════════════

def _crear_oc(num, prov, con_items=True):
    _sql("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (num,))
    _sql("DELETE FROM ordenes_compra WHERE numero_oc=?", (num,))
    _sql("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, valor_total, fecha) "
         "VALUES (?,?,'Borrador','Materia Prima',119000,'2026-07-31')", (num, prov))
    if con_items:
        _sql("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, "
             "precio_unitario, subtotal) VALUES (?,?,?,1000,100,100000)",
             (num, 'MP-ZZ', 'ZZ material'))


def test_una_lista_de_items_VACIA_no_borra_los_que_hay(app, db_clean):
    """El otro modo de perder una orden: sigue existiendo pero queda en cero. Este bloque borra
    e re-inserta, así que una lista vacía -- por un error de JS, una carga a medias o un doble
    submit -- la dejaba sin nada. Vaciar una orden nunca es el objetivo de "guardar cambios"."""
    _crear_oc(OC, 'ZZ Proveedor')
    r = _login(app, 'catalina').patch(
        '/api/ordenes-compra/%s/editar' % OC,
        headers={'Content-Type': 'application/json', **csrf_headers()},
        json={'items': []})
    assert r.status_code == 409, ('borró los ítems por una lista vacía: %s' % r.data[:300])
    assert (r.get_json() or {}).get('codigo') == 'ITEMS_VACIOS', r.get_json()
    n = _sql("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=?", (OC,))[0][0]
    assert int(n) == 1, 'los ítems se borraron igual'


def test_editar_con_items_de_verdad_SIGUE_funcionando(app, db_clean):
    """Dientes del otro lado: el guard no puede trabar la edición normal."""
    _crear_oc(OC, 'ZZ Proveedor')
    r = _login(app, 'catalina').patch(
        '/api/ordenes-compra/%s/editar' % OC,
        headers={'Content-Type': 'application/json', **csrf_headers()},
        json={'items': [{'codigo_mp': 'MP-ZZ', 'nombre_mp': 'ZZ material',
                         'cantidad_g': 2000, 'precio_unitario': 50}]})
    assert r.status_code in (200, 201), r.data[:300]
    n = _sql("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=?", (OC,))[0][0]
    assert int(n) == 1


def test_autorizada_de_MERCANCIA_queda_visible_en_RECEPCION(app, db_clean):
    """Lo que le pasó a Catalina con la 0299 (31-jul).

    Al crear una OC el checkbox "Autorizar al crear" viene marcado, así que la orden nace
    **Autorizada**. Y la lista de OCs muestra a propósito sólo las que faltan por autorizar
    (Borrador/Revisada), así que la orden desaparece de la pantalla donde se la acaba de crear.

    Eso está bien SIEMPRE QUE siga visible en algún lado. Para mercancía ese lado NO es Por
    Pagar (que trae Recibida/Parcial): es **Recepción**, esperando que llegue. Si un día alguien
    cambia ese filtro, la orden se vuelve invisible en las tres pantallas y el "se me perdió"
    vuelve -- por eso el test mira el destino real, no el mensaje.
    """
    _crear_oc(OC, 'ZZ Proveedor')
    _sql("UPDATE ordenes_compra SET estado='Autorizada' WHERE numero_oc=?", (OC,))
    cli = _login(app, 'catalina')

    r = cli.get('/api/recepcion/seguimiento')
    assert r.status_code == 200, r.data[:200]
    fila = [o for o in (r.get_json() or []) if o.get('numero_oc') == OC]
    assert fila, 'la OC autorizada de mercancía no aparece en Recepción: quedó invisible'
    assert fila[0].get('en_transito') is True, fila[0]

    # y NO se cuela en Por Pagar antes de llegar (ahí se paga lo que ya se recibió)
    r2 = cli.get('/api/compras/por-pagar')
    assert r2.status_code == 200
    _pp = (r2.get_json() or {})
    _nums = [x.get('numero_oc') for x in (_pp.get('items') or _pp.get('ocs') or [])]
    assert OC not in _nums, 'mercancía sin recibir no debería estar en Por Pagar'


def test_una_CUENTA_DE_COBRO_autorizada_SI_llega_a_por_pagar(app, db_clean):
    """La misma trampa, pero sin salida: una cuenta de cobro no se "recibe" nunca.

    El modal guarda la categoría con el código `CC`, y `CATEGORIAS_PAGO_DIRECTO` enumeraba
    'Cuenta de Cobro' pero no 'CC' -- así que la orden no entraba a Por Pagar y tampoco podía
    pasar a Recibida: quedaba invisible para siempre.
    """
    _crear_oc(OC2, 'ZZ Beneficiario', con_items=False)
    _sql("UPDATE ordenes_compra SET estado='Autorizada', categoria='CC' WHERE numero_oc=?", (OC2,))
    r = _login(app, 'catalina').get('/api/compras/por-pagar')
    assert r.status_code == 200, r.data[:200]
    _pp = r.get_json() or {}
    _items = _pp.get('items') or _pp.get('ocs') or []
    fila = [x for x in _items if x.get('numero_oc') == OC2]
    assert fila, 'la cuenta de cobro autorizada no llegó a Por Pagar (queda sin salida)'
    assert fila[0].get('pago_directo') is True, fila[0]


def test_fusionar_dos_ordenes_PREGUNTA_antes_de_borrar(app, db_clean):
    """Cambiar el proveedor puede FUSIONAR y borrar esta orden (decisión de Sebastián 14-jul).
    Quien pidió "cambiá el proveedor" no pidió "borrá la orden": se confirma antes."""
    _crear_oc(OC, 'ZZ Proveedor A')
    _crear_oc(OC2, 'ZZ Proveedor B')
    cli = _login(app, 'catalina')
    r = cli.post('/api/ordenes-compra/%s/cambiar-proveedor' % OC,
                 headers={'Content-Type': 'application/json', **csrf_headers()},
                 json={'proveedor': 'ZZ Proveedor B'})
    assert r.status_code == 409, ('fusionó sin preguntar: %s' % r.data[:300])
    j = r.get_json()
    assert j.get('requiere_confirmacion') and j.get('fusiona_con') == OC2, j
    assert _sql("SELECT COUNT(*) FROM ordenes_compra WHERE numero_oc=?", (OC,))[0][0] == 1, (
        'borró la orden antes de que nadie confirmara')
    # con la confirmación explícita, sí fusiona
    r2 = cli.post('/api/ordenes-compra/%s/cambiar-proveedor' % OC,
                  headers={'Content-Type': 'application/json', **csrf_headers()},
                  json={'proveedor': 'ZZ Proveedor B', 'confirmar_fusion': True})
    assert r2.status_code == 200, r2.data[:300]
    assert (r2.get_json() or {}).get('merged_into') == OC2, r2.get_json()
    assert _sql("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=?", (OC2,))[0][0] >= 2, (
        'los ítems no llegaron a la orden destino')
