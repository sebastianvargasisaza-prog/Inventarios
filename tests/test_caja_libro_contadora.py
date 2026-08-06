# -*- coding: utf-8 -*-
"""La contadora puede REVISAR la caja: cuánto hay y con qué entró cada peso.

Sebastián (6-ago): *"la caja menor le debe aparecer todo, cuánto hay, con qué ingresó todo, para
ella revisar"*.

Dos huecos medidos antes de construir:

1. **Mayra no podía ver un solo movimiento.** `GET /api/animus/caja` está gateado a
   `ANIMUS_ACCESS` (daniela/alejandro/sebastián) y ella no está ahí; la única pantalla que los
   pinta le devolvía 403. Sin el libro no hay revisión posible.
2. **`origen`, `subtipo`, `empresa` y `comprobante_url` se ESCRIBEN y nunca salían por la API.**
   O sea que "con qué ingresó" estaba en la base y no había forma de verlo en lista -- un dato
   que se captura y no llega al consumidor no existe (M115).

⚠ Casi todo lo que se verifica acá son AGREGADOS sobre un rango (ingresos a la gaveta, egresos,
sin respaldo, por origen), y hay otros 7 archivos que siembran en `animus_caja_menor`. Aislado
pasaba y en el gate no: el endpoint sumaba filas ajenas. Por eso el día de prueba es uno que no
usa nadie mas y se limpia ENTERO antes de sembrar -- un test que mira un agregado tiene que
controlar TODO el universo que el endpoint observa, no solo las filas que el escribe (M102/M103).
"""

DIA = '2027-03-05'      # dia exclusivo de este archivo · ningun otro test siembra caja ahi
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _sembrar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        # el dia ENTERO, no solo lo mio: los agregados del endpoint suman todo lo que caiga
        # en el rango, venga de donde venga
        c.execute("DELETE FROM animus_caja_menor WHERE substr(fecha,1,10)=?", (DIA,))
        filas = [
            (DIA, 'ingreso', 'ZZLIB contraentrega efectivo', 100000, 'efectivo',
             'contraentrega', '', '', 0),
            (DIA, 'ingreso', 'ZZLIB contraentrega nequi', 50000, 'nequi',
             'contraentrega', '', '', 0),
            (DIA, 'egreso', 'ZZLIB gasto con respaldo', 30000, 'efectivo',
             'directo', 'gasto', 'https://x/y.pdf', 0),
            (DIA, 'egreso', 'ZZLIB gasto sin respaldo', 20000, 'efectivo',
             'directo', 'gasto', '', 0),
            (DIA, 'egreso', 'ZZLIB anulado', 99999, 'efectivo', 'directo', 'gasto', '', 1),
        ]
        for i, (f, t, cp, m, me, og, st, cu, an) in enumerate(filas, start=1):
            c.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, metodo, "
                      " referencia, observaciones, registrado_por, recibo_numero, anulado, "
                      " empresa, origen, subtipo, comprobante_url) "
                      "VALUES (?,?,?,?,?,'','', 'zz', ?, ?, 'ANIMUS', ?, ?, ?)",
                      (f, t, cp, m, me, 'RC-ZZLIB-%03d' % i, an, og, st, cu))
        conn.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM animus_caja_menor WHERE substr(fecha,1,10)=?", (DIA,))
        conn.commit()


def _libro(admin_client, **q):
    qs = '&'.join('%s=%s' % (k, v) for k, v in q.items())
    r = admin_client.get('/api/caja/libro' + ('?' + qs if qs else ''))
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_el_libro_DICE_con_que_ingreso_cada_peso(app, admin_client, db_clean):
    """`origen` y `subtipo` existen en la tabla desde la mig 409 y nunca salían por la API."""
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    mios = [m for m in d['movimientos'] if m['concepto'].startswith('ZZLIB')]
    assert len(mios) == 5, len(mios)
    uno = [m for m in mios if 'contraentrega efectivo' in m['concepto']][0]
    for k in ('origen', 'subtipo', 'empresa', 'comprobante_url', 'recibo', 'metodo'):
        assert k in uno, 'falta %s · sin eso no se puede revisar' % k
    assert uno['origen'] == 'contraentrega'
    _limpiar(app)


def test_marca_lo_que_ENTRO_AL_BANCO_y_no_a_la_gaveta(app, admin_client, db_clean):
    """El saldo excluye los ingresos que no son efectivo a propósito (esa plata no está en la
    gaveta). Si no se dijera fila por fila, ella tendría que descubrirlo restando (M124)."""
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    efe = [m for m in d['movimientos'] if 'contraentrega efectivo' in m['concepto']][0]
    nq = [m for m in d['movimientos'] if 'contraentrega nequi' in m['concepto']][0]
    assert efe['cuenta_en_saldo'] is True
    assert nq['cuenta_en_saldo'] is False, 'un Nequi no está en la gaveta'
    assert d['ingresos_a_gaveta'] == 100000
    assert d['ingresos_al_banco'] == 50000, 'no separa lo que entró al banco'
    _limpiar(app)


def test_el_saldo_sale_del_helper_CANONICO_no_del_filtro(app, admin_client, db_clean):
    """Un saldo que cambia según el rango elegido no es un saldo · y tiene que ser el MISMO
    número contra el que se autorizan los pagos (M1/M148)."""
    from database import get_db
    from blueprints.animus import caja_saldo
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    with app.app_context():
        canon = caja_saldo(get_db())
    assert d['saldo_actual'] == canon, 'el libro calcula su propio saldo · va a divergir'
    _limpiar(app)


def test_lo_ANULADO_no_cuenta_pero_se_VE(app, admin_client, db_clean):
    """Un movimiento anulado deja de sumar y sigue a la vista: el rastro es lo que permite
    entender un número de un mes pasado."""
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    anul = [m for m in d['movimientos'] if m['concepto'].endswith('anulado')]
    assert anul, 'el anulado desapareció de la vista'
    assert anul[0]['anulado'] is True
    assert anul[0]['cuenta_en_saldo'] is False
    assert d['egresos'] == 50000, 'el anulado se contó en los egresos · %s' % d['egresos']
    _limpiar(app)


def test_cuenta_los_egresos_SIN_respaldo(app, admin_client, db_clean):
    """Es lo primero que una contadora busca: plata que salió sin soporte."""
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    assert d['egresos_sin_respaldo'] == 1, d['egresos_sin_respaldo']
    _limpiar(app)


def test_agrupa_los_ingresos_POR_ORIGEN(app, admin_client, db_clean):
    """Con qué ingresó todo, en una sola mirada, sin recorrer fila por fila."""
    _sembrar(app)
    d = _libro(admin_client, desde=DIA, hasta=DIA)
    ce = [x for x in d['por_origen'] if x['origen'] == 'contraentrega']
    assert ce, d['por_origen']
    assert ce[0]['total'] == 150000
    assert ce[0]['a_gaveta'] == 100000, 'no separa cuánto de ese origen llegó a la gaveta'
    _limpiar(app)


def test_la_CONTADORA_puede_leerlo(app, db_clean):
    """El hueco original: `GET /api/animus/caja` es ANIMUS_ACCESS y mayra no está ahí."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/animus.py'), encoding='utf-8').read()
    # La ventana se acota al FIN de la función, no a un número de caracteres: con un docstring
    # largo una ventana fija se queda corta y el test falla con el código correcto.
    i = src.find('def caja_libro')
    j = src.find('\n@bp.route', i)
    bloque = src[i:j]
    assert '_caja_auth()' in bloque, 'el libro no usa la puerta que incluye a la contadora'
    from config import CONTADORA_USERS
    assert CONTADORA_USERS, 'no hay contadoras configuradas'


def test_es_de_SOLO_LECTURA(app, db_clean):
    """Un endpoint de revisión que además escriba convierte una consulta en un riesgo."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/animus.py'), encoding='utf-8').read()
    i = src.find('def caja_libro')
    j = src.find('\n@bp.route', i)
    bloque = src[i:j].upper()
    for verbo in ('INSERT ', 'UPDATE ', 'DELETE '):
        assert verbo not in bloque, 'el libro MUTA (%s)' % verbo.strip()
