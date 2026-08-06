# -*- coding: utf-8 -*-
"""Toda plata que se mueve en la caja llega al libro central de Tesorería.

Sebastián (6-ago): *"allí debe llegar cualquier movimiento, todo lo que sea plata se debe ver
reflejado allí"*.

`_tesoreria_espejo` existía y lo llamaban tres caminos (pagar una solicitud, consignar a la
cuenta, cobrar un contraentrega que no fue en efectivo). Faltaban tres, y son justo los que un
mes cierra mal sin que nadie sepa por qué:

1. **El movimiento MANUAL de caja** (`POST /api/animus/caja`) -- el camino más usado del día a
   día -- no llegaba a ningún lado. Es M45 otra vez: el patrón estaba escrito y a este hermano
   no se lo aplicaron.
2. **El ajuste por arqueo.** Un faltante es plata que salió de la empresa aunque nadie sepa en
   qué; si no llega al libro, el gasto del mes queda corto y la diferencia se descubre cuadrando
   a mano.
3. **El sobrante de un pago.** Acá la trampa es la contraria: espejarlo como INGRESO inflaría
   los ingresos del mes con algo que nunca fue una venta. El pago ya entró al libro por su monto
   completo, así que lo correcto es BAJAR ese gasto -- va como egreso NEGATIVO, que es
   literalmente lo que pasó: se gastó menos.

Los tres son idempotentes por el número de recibo (UNIQUE), así que reintentar no duplica plata.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZLIBRO'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD es compartida y en PG persiste entre corridas.

    ⚠ Borra TODOS los espejos de caja, no sólo los míos, y la razón vale más que el borrado:
    los archivos vecinos borran sus movimientos de `animus_caja_menor` sin borrar los espejos
    que dejaron en el libro. Como el correlativo del recibo se calcula leyendo el máximo de esa
    tabla, al vaciarla **el número se reinicia** y mi movimiento nuevo recibe un `RC-2026-0002`
    que ya tiene un espejo viejo -- el guard de idempotencia lo encuentra y NO espeja el mío.
    Aislado pasaba y en el gate no (M102: un test que mira agregados tiene que controlar todo
    el universo que el endpoint observa).

    En producción no puede pasar: anular CONSERVA la fila (M106), así que el correlativo nunca
    retrocede. Es decir que la llave de idempotencia (el recibo) es segura mientras nadie borre
    un movimiento de caja de verdad -- si algún día se agrega un borrado duro, hay que cambiar
    la llave por el id del movimiento, que no se reusa.
    """
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?", (MARCA + '%',))
        for t in ('flujo_ingresos', 'flujo_egresos'):
            conn.execute("DELETE FROM " + t + " WHERE fuente='caja_menor'")
        conn.commit()


def _fila_libro(app, tabla, recibo):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT monto, categoria, periodo, fecha FROM " + tabla +
            " WHERE fuente='caja_menor' AND referencia=?", (recibo,)).fetchall()


def test_un_ingreso_MANUAL_de_caja_llega_al_libro(app, db_clean):
    """Era el camino más usado y el único de alta que no espejaba."""
    _limpiar(app)
    c = _admin(app)
    r = c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "ingreso", "concepto": MARCA + " venta de mostrador",
        "monto": 250000, "fecha": "2026-08-04"})
    assert r.status_code == 200, r.data[:300]
    recibo = r.get_json()['recibo_numero']
    filas = _fila_libro(app, 'flujo_ingresos', recibo)
    assert len(filas) == 1, 'el ingreso manual no llegó a Tesorería'
    assert float(filas[0][0]) == 250000
    # el PERÍODO sale de la fecha del hecho, no del reloj (M106)
    assert filas[0][2] == '2026-08', filas[0][2]
    _limpiar(app)


def test_un_egreso_MANUAL_de_caja_llega_al_libro(app, db_clean):
    _limpiar(app)
    c = _admin(app)
    r = c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "egreso", "concepto": MARCA + " taxi de domicilios",
        "monto": 18000, "fecha": "2026-08-04"})
    assert r.status_code == 200, r.data[:300]
    recibo = r.get_json()['recibo_numero']
    filas = _fila_libro(app, 'flujo_egresos', recibo)
    assert len(filas) == 1, 'el egreso manual no llegó a Tesorería'
    assert float(filas[0][0]) == 18000
    assert not _fila_libro(app, 'flujo_ingresos', recibo), 'un egreso no puede ser un ingreso'
    _limpiar(app)


def test_el_espejo_NO_duplica_la_plata(app, db_clean):
    """Dos movimientos distintos son dos recibos distintos; el mismo recibo NUNCA se espeja dos
    veces. Un espejo que duplica es peor que uno que falta: nadie sospecha de un número de más."""
    _limpiar(app)
    c = _admin(app)
    recibos = []
    for i in range(2):
        r = c.post("/api/animus/caja", headers=csrf_headers(), json={
            "tipo": "ingreso", "concepto": MARCA + " cobro %d" % i,
            "monto": 5000, "fecha": "2026-08-04"})
        recibos.append(r.get_json()['recibo_numero'])
    assert recibos[0] != recibos[1], 'dos movimientos comparten recibo'
    for rec in recibos:
        assert len(_fila_libro(app, 'flujo_ingresos', rec)) == 1
    # y re-espejar el mismo recibo a mano no agrega una segunda fila
    from database import get_db
    from blueprints.animus import _tesoreria_espejo
    with app.app_context():
        conn = get_db()
        _tesoreria_espejo(conn.cursor(), tipo='ingreso', fecha='2026-08-04',
                          concepto=MARCA + ' reintento', monto=5000, empresa='ANIMUS',
                          referencia=recibos[0], usuario='zz', categoria='Caja menor')
        conn.commit()
    assert len(_fila_libro(app, 'flujo_ingresos', recibos[0])) == 1, 'se duplicó la plata'
    _limpiar(app)


def test_el_FALTANTE_de_un_arqueo_llega_como_egreso(app, db_clean):
    """Un faltante es plata que salió aunque nadie sepa en qué. Con categoría propia, para que
    no se lea como un gasto operativo del mes."""
    _limpiar(app)
    from database import get_db
    from blueprints.animus import caja_saldo
    c = _admin(app)
    # Hay que sembrar efectivo primero: con la gaveta en 0 no se puede contar de MENOS, el
    # arqueo sale "Cuadrada" y el test pasaría sin ejercitar nada (M152: un test que pasa por
    # la razón equivocada es peor que no tenerlo).
    c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "ingreso", "concepto": MARCA + " base para arquear",
        "monto": 100000, "fecha": "2026-08-04"})
    with app.app_context():
        sistema = caja_saldo(get_db())
    assert sistema >= 100000, 'la siembra no entró a la gaveta · %s' % sistema
    r = c.post("/api/caja/arqueos", headers=csrf_headers(), json={
        "conteo_fisico": sistema - 30000, "fecha": "2026-08-04",
        "motivo": MARCA + " faltante de prueba"})
    assert r.status_code == 201, r.data[:300]
    d = r.get_json()
    assert d['diferencia'] < 0, d
    from database import get_db as _g
    with app.app_context():
        filas = _g().execute(
            "SELECT monto, categoria FROM flujo_egresos WHERE fuente='caja_menor' "
            "AND concepto LIKE ?", ('%' + d['numero'] + '%',)).fetchall()
    assert len(filas) == 1, 'el faltante del arqueo no llegó al libro'
    assert filas[0][1] == 'Ajuste de caja', 'sin categoría propia se lee como gasto operativo'
    _limpiar(app)


def test_el_SOBRANTE_baja_el_gasto_y_NO_inventa_un_ingreso(app, db_clean):
    """Lo que sobró de un pago nunca fue una venta. Si entrara como ingreso, los ingresos del
    mes subirían por plata que sólo volvió al cajón (M124: lo que un número incluye importa
    tanto como su valor)."""
    # ⚠ La 1ª versión llamaba a `_tesoreria_espejo` directo y pasaba VERDE aunque yo pusiera el
    # sobrante como INGRESO en el endpoint: estaba midiendo el helper, no el camino que corre
    # (M152). Ahora recorre solicitar → autorizar → pagar → devolver el sobrante por los
    # endpoints reales, que es lo único que prueba que el botón hace lo que dice.
    _limpiar(app)
    c = _admin(app)
    c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "ingreso", "concepto": MARCA + " fondeo", "monto": 900000,
        "fecha": "2026-08-04"})
    r = c.post('/api/caja/solicitudes', headers=csrf_headers(),
               json={'concepto': MARCA + ' compra de ferretería', 'monto': 200000,
                     'empresa': 'ANIMUS'})
    assert r.status_code == 201, r.data[:300]
    sid = r.get_json()['id']
    c.post('/api/caja/solicitudes/%d/autorizar' % sid, json={}, headers=csrf_headers())
    rp = c.post('/api/caja/solicitudes/%d/pagar' % sid, json={}, headers=csrf_headers())
    assert rp.status_code == 200, rp.data[:300]
    rs = c.post('/api/caja/solicitudes/%d/sobrante' % sid, headers=csrf_headers(),
                json={'monto': 7000, 'fecha': '2026-08-04'})
    assert rs.status_code == 200, rs.data[:300]
    recibo = rs.get_json()['recibo_numero']
    egr = _fila_libro(app, 'flujo_egresos', recibo)
    assert len(egr) == 1, 'el sobrante no ajustó el gasto'
    assert float(egr[0][0]) == -7000, 'tiene que BAJAR el gasto, no sumarlo'
    assert not _fila_libro(app, 'flujo_ingresos', recibo), (
        'el sobrante entró como INGRESO · eso infla los ingresos del mes con algo que nunca '
        'fue una venta')
    _limpiar(app)


def test_los_TRES_caminos_que_faltaban_llaman_al_espejo(app):
    """Guard estructural: si alguien agrega un cuarto camino de alta y se olvida del espejo, el
    hueco vuelve. Se mide sobre el FUENTE porque es la única forma de ver la ausencia."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'animus.py'), encoding='utf-8').read()
    # comentarios fuera: si no, este test encuentra la prosa que explica el espejo (M154)
    limpio = re.sub(r'^\s*#[^\n]*$', '', s, flags=re.M)
    n_altas = limpio.count('registrar_movimiento_caja(')
    n_espejos = limpio.count('_tesoreria_espejo(')
    # una definición + una por camino · las altas incluyen la definición del helper
    assert n_espejos >= 6, (
        'hay %d altas de caja y sólo %d espejos · algún camino da de alta plata que no llega al '
        'libro central' % (n_altas, n_espejos))
