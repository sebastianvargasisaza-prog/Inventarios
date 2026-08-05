# -*- coding: utf-8 -*-
"""Las DOS puertas por las que entra un envase tienen que recibir IGUAL.

Sebastián describió la cadena así: *"el envase se pide, puede estar como orden de compra y
aparecer en recepción para ser aceptado, o llega como importación y se recepciona directamente"*.
Son dos puertas para el mismo hecho físico -- llegó un bulto de frascos -- y hasta hoy se
comportaban distinto:

  · por CONTENEDOR (manual)  → entraba DISPONIBLE, con proveedor, lote, vencimiento y sus cajas.
  · por ORDEN DE COMPRA      → entraba RETENIDO, con el número de OC guardado en el campo del
                               LOTE, sin proveedor, sin vencimiento y sin una sola caja.

O sea que el mismo frasco se podía usar o no según por dónde hubiera entrado, y el prefill del
F01 llegaba vacío justo cuando venía con orden de compra (que es el caso normal). Dos pantallas
que describen el mismo hecho de forma distinta hacen que no se crea en ninguna (M161).

⚠ Esto NO toca la materia prima: la MP sigue entrando en CUARENTENA (INVIMA).
"""
import io
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OC = 'OC-ZZTEST-9001'
# ⚠ SIN prefijo `MEE-`/`ENV-` a propósito: de los 129 códigos de envase reales, 109 se llaman
# `PLEG-`, `ETIQ-`, `SERIG-`, `TA-`, `GO-`, `FR-`… Un test con código `MEE-` pasa por la regla
# de RESPALDO (prefijo) y nunca ejercita la que de verdad decide (está en maestro_mee y no en
# maestro_mps) -- pasaría verde con esa regla rota, que es un test sin dientes (M152).
ENV = 'PLEG-ZZOC-001'
PROV = 'ZZ Importadora China'


def _sin_comentarios(txt):
    fuera = []
    for ln in txt.splitlines():
        if ln.strip().startswith('#'):
            continue
        fuera.append(re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM mee_cajas_disposicion WHERE mov_id IN "
                  " (SELECT id FROM movimientos_mee WHERE mee_codigo=?)", (ENV,))
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (ENV,))
        c.execute("DELETE FROM maestro_mee WHERE codigo=?", (ENV,))
        c.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (OC,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        c.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc=?", (OC,))
        conn.commit()


def _sembrar_oc(app, cantidad=1200.0):
    """OC con categoría 'MP' A PROPÓSITO: es el caso real (el front la crea siempre así) y es
    lo que obliga a decidir MP vs envase por ÍTEM y no por la categoría de la OC."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, stock_actual, "
                  " stock_minimo, estado, fecha_creacion) "
                  "VALUES (?, 'ZZ frasco importado 30 ml', 'Frasco', 'und', 0, 0, 'Activo', '2026-08-05')",
                  (ENV,))
        c.execute("INSERT INTO ordenes_compra (numero_oc, fecha, proveedor, estado, categoria, "
                  " valor_total) VALUES (?, '2026-08-05', ?, 'Autorizada', 'MP', 1000)", (OC, PROV))
        c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) "
                  "VALUES (?,?,?,?)", (OC, ENV, 'ZZ frasco importado 30 ml', cantidad))
        conn.commit()


def _recibir(admin_client, **extra):
    from .conftest import csrf_headers
    item = {'codigo_mp': ENV, 'cantidad_recibida': 1200.0}
    item.update({k: v for k, v in extra.items() if not k.startswith('_')})
    # ⚠ la clave es `items_recepcion`: mandar `items` deja al endpoint sin nada que imputar y
    # devuelve 200 con `ingresos: 0` -- verde por fuera, kardex vacío por dentro (M100).
    cuerpo = {'recepcion_id': 'zz-oc-%s' % (extra.get('lote') or extra.get('_tok') or 'base'),
              'items_recepcion': [item]}
    return admin_client.post('/api/ordenes-compra/%s/recibir' % OC, data=json.dumps(cuerpo),
                             headers=csrf_headers(), content_type='application/json')


def _mov(app):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT id, estado, COALESCE(lote_ref,''), COALESCE(proveedor,''), "
            "       COALESCE(oc_numero,''), COALESCE(fecha_vencimiento,''), cantidad "
            "  FROM movimientos_mee WHERE mee_codigo=? ORDER BY id DESC LIMIT 1", (ENV,)).fetchone()


# ── el envase entra al kardex CORRECTO ───────────────────────────────────────

def test_el_envase_de_una_OC_no_cae_al_kardex_de_MATERIA_PRIMA(app, admin_client, db_clean):
    """La OC dice 'MP' (el front la crea siempre así) y el ítem es un envase. Si se decide por
    la categoría de la OC, el frasco entra a `movimientos` y su stock de envase queda en 0 --
    con lo cual abastecimiento lo vuelve a pedir teniéndolo en bodega."""
    from database import get_db
    _sembrar_oc(app)
    r = _recibir(admin_client, lote='ZZL-1')
    assert r.status_code in (200, 201), r.data[:400]
    with app.app_context():
        en_mp = get_db().execute("SELECT COUNT(*) FROM movimientos WHERE material_id=?",
                                 (ENV,)).fetchone()[0]
    assert en_mp == 0, 'el envase entró al kardex de MATERIA PRIMA'
    assert _mov(app) is not None, 'el envase no entró al kardex de envases'
    _limpiar(app)


def test_entra_DISPONIBLE_igual_que_por_la_puerta_manual(app, admin_client, db_clean):
    """La decisión del 30-jul se había aplicado a UNA sola de las dos puertas."""
    _sembrar_oc(app)
    _recibir(admin_client, lote='ZZL-2')
    m = _mov(app)
    assert m[1] == 'VIGENTE', 'entró retenido: %s' % m[1]
    _limpiar(app)


def test_el_stock_del_envase_QUEDA_disponible(app, admin_client, db_clean):
    """Stock canónico (M26), no el cache: es el número contra el que se decide si hay que
    comprar y si se puede envasar."""
    from database import get_db
    _sembrar_oc(app)
    _recibir(admin_client, lote='ZZL-3')
    with app.app_context():
        stock = get_db().execute(
            "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad "
            "                         WHEN LOWER(tipo)='salida' THEN -cantidad ELSE cantidad END),0) "
            "  FROM movimientos_mee WHERE mee_codigo=? AND COALESCE(anulado,0)=0 "
            "   AND UPPER(COALESCE(estado,'')) NOT IN ('CUARENTENA','RECHAZADO')",
            (ENV,)).fetchone()[0]
    assert stock == 1200, 'el envase recibido por OC no quedó disponible · %s' % stock
    _limpiar(app)


# ── el kardex queda COMPLETO ─────────────────────────────────────────────────

def test_el_lote_es_el_del_PROVEEDOR_no_el_numero_de_OC(app, admin_client, db_clean):
    """Guardar el número de OC en el campo del lote no es un detalle cosmético: es el dato que
    se imprime en el rótulo y el que Calidad busca en el F01. Un lote que en realidad es el
    número de la orden no identifica el material que llegó."""
    _sembrar_oc(app)
    _recibir(admin_client, lote='ZZL-REAL-7788')
    m = _mov(app)
    assert m[2] == 'ZZL-REAL-7788', 'el lote quedó como "%s"' % m[2]
    assert m[2] != OC
    assert m[4] == OC, 'la OC se perdió · va en su columna, no en la del lote'
    _limpiar(app)


def test_sin_lote_del_proveedor_se_asigna_uno_INTERNO(app, admin_client, db_clean):
    """Sin lote no hay trazabilidad, y un lote vacío rompe el rótulo y el escaneo. El prefijo
    INT- lo distingue a simple vista de un lote del proveedor (M115)."""
    _sembrar_oc(app)
    _recibir(admin_client, _tok='sinlote')
    m = _mov(app)
    assert m[2].startswith('INT-'), 'quedó sin lote o con uno inventado: "%s"' % m[2]
    _limpiar(app)


def test_el_kardex_guarda_PROVEEDOR_y_VENCIMIENTO(app, admin_client, db_clean):
    """Son los dos datos que el F01 pre-llena y que el rótulo imprime. Sin ellos, Calidad
    tiene que volver a teclear lo que el sistema ya sabía."""
    _sembrar_oc(app)
    _recibir(admin_client, lote='ZZL-4', fecha_vencimiento='2028-01-31')
    m = _mov(app)
    assert m[3] == PROV, 'el kardex no guardó el proveedor · "%s"' % m[3]
    assert m[5] == '2028-01-31', 'el kardex no guardó el vencimiento · "%s"' % m[5]
    _limpiar(app)


def test_las_CAJAS_quedan_abiertas_para_que_Calidad_revise(app, admin_client, db_clean):
    """La revisión de Calidad es caja por caja escaneando el rótulo. Sin filas de caja no hay
    nada que revisar: quitar el candado de la cuarentena exige que lo que lo reemplaza exista
    de verdad (M126)."""
    from database import get_db
    _sembrar_oc(app)
    _recibir(admin_client, lote='ZZL-5', recipientes=4)
    m = _mov(app)
    with app.app_context():
        filas = get_db().execute(
            "SELECT caja, estado, cantidad FROM mee_cajas_disposicion "
            " WHERE mov_id=? ORDER BY caja", (m[0],)).fetchall()
    assert len(filas) == 4, 'se abrieron %d cajas de 4' % len(filas)
    assert {f[1] for f in filas} == {'PENDIENTE'}, [f[1] for f in filas]
    assert round(sum(float(f[2]) for f in filas), 2) == 1200.0, \
        'las cajas no suman lo recibido · %s' % [f[2] for f in filas]
    _limpiar(app)


# ── lo que NO cambia ─────────────────────────────────────────────────────────

def test_la_MATERIA_PRIMA_sigue_entrando_en_cuarentena(app, db_clean):
    """El cambio de estado es SÓLO para envases. Aflojar la cuarentena de MP sería quitar un
    control INVIMA que nadie pidió quitar."""
    src = _sin_comentarios(io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'),
                                   encoding='utf-8').read())
    i = src.find('recepcion_auto_vigente')
    assert i > 0, 'desapareció el interruptor de cuarentena de la recepción de MP'
    # y el estado fijo VIGENTE vive DENTRO de la rama de envases, no en la de MP
    j = src.find("_estado_mee = 'VIGENTE'")
    k = src.find('lotes_sinteticos_advertencia.append')
    assert 0 < j < k, 'el estado fijo de envase se salió de su rama'


def test_el_lote_interno_es_UN_solo_helper(app, db_clean):
    """Dos puertas con su propio correlativo producen dos series que se pisan, y dos materiales
    distintos bajo el mismo lote es lo peor que le puede pasar a la trazabilidad (M1/M99)."""
    from audit_helpers import lote_interno_mee
    inv = _sin_comentarios(io.open(os.path.join(RAIZ, 'api/blueprints/inventario.py'),
                                   encoding='utf-8').read())
    com = _sin_comentarios(io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'),
                                   encoding='utf-8').read())
    assert 'lote_interno_mee' in inv and 'lote_interno_mee' in com, \
        'alguna puerta se armó su propio lote interno'
    assert callable(lote_interno_mee)


def test_el_lote_interno_no_repite_dentro_del_mismo_dia(app, db_clean):
    """El correlativo se calcula mirando lo que YA está en el kardex · si dos recepciones del
    mismo día comparten lote, el reclamo no apunta a ninguna."""
    from database import get_db
    from audit_helpers import lote_interno_mee
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, stock_actual, "
                  " stock_minimo, estado, fecha_creacion) VALUES (?, 'ZZ', 'Frasco', 'und', 0, 0, "
                  " 'Activo', '2026-08-05')", (ENV,))
        primero = lote_interno_mee(c)
        c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, estado) "
                  "VALUES (?, 'Entrada', 1, ?, 'VIGENTE')", (ENV, primero))
        conn.commit()
        segundo = lote_interno_mee(c)
    assert primero != segundo, 'el lote interno se repitió: %s' % primero
    assert segundo.startswith('INT-')
    _limpiar(app)
