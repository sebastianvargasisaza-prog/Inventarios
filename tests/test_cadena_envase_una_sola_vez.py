# -*- coding: utf-8 -*-
"""La secuencia REAL: envasar y después acondicionar el mismo lote. El frasco sale UNA vez.

Había tests de cada cierre contra el libro mayor por separado, y ninguno que recorriera la
secuencia que ocurre en el piso: primero se envasa, después se acondiciona el mismo lote físico.
Y ahí es exactamente donde vivía el doble descuento -- cada cierre miraba su propia marca y
ninguno sabía del otro (M162).

Un test de un endpoint verifica que ese endpoint hace lo suyo. La COSTURA entre dos endpoints no
la cubre nadie, y es donde se pierde el material: el frasco salía dos veces del kardex y no daba
ningún síntoma, porque un kardex con un descuento de más se ve idéntico a uno sano. Se descubre
contando físico, semanas después.

Lo que se mide acá es el hecho, no la implementación: **después de los dos cierres, el frasco
salió exactamente 300 unidades, ni 0 ni 600.**
"""
import json
import uuid

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ CADENA PRODUCTO'
FRASCO = 'ZZCAD-FRASCO'
TAPA = 'ZZCAD-TAPA'
CAJA = 'ZZCAD-CAJA'
UNIDADES = 300


def _limpiar(app):
    """Hijas → quien las apunta → madre: borrar un maestro con movimientos vivos revienta la FK
    (M119), y entre tests de este archivo los hay."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod in (FRASCO, TAPA, CAJA):
            c.execute("DELETE FROM movimientos_mee WHERE UPPER(TRIM(mee_codigo))=?", (cod,))
        c.execute("DELETE FROM produccion_checklist WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id IN "
                  " (SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZCAD-%')")
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZCAD-%'")
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        for cod in (FRASCO, TAPA, CAJA):
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        conn.commit()


def _sembrar(app):
    """Un lote con su presentación, su checklist y los DOS legajos: envasado y acondicionamiento.

    Los dos cuelgan de la MISMA `produccion_id`, que es lo que los hace hablar entre sí -- y es
    también la condición real: un lote físico se envasa y después se acondiciona.
    """
    from database import get_db
    _limpiar(app)
    lote = 'ZZCAD-' + uuid.uuid4().hex[:6].upper()
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((FRASCO, 'ZZ frasco'), (TAPA, 'ZZ tapa'), (CAJA, 'ZZ caja')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',5000,0,'Activo','2026-08-06')", (cod, desc))
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, estado) "
                      "VALUES (?, 'Entrada', 5000, 'ZZCAD-SEED', 'VIGENTE')", (cod,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, tapa_codigo, activo, es_default) "
                  "VALUES (?, 'ZZCAD30', 'ZZ 30 ml', 30, ?, ?, 1, 1)", (PROD, FRASCO, TAPA))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?, '2026-08-06', 10, 'pendiente', 'eos_plan')", (PROD,))
        pid = c.lastrowid
        for tipo, cod in (('envase_primario', FRASCO), ('tapa', TAPA)):
            c.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, "
                      " fecha_planeada, item_tipo, descripcion, mee_codigo_asignado, "
                      " cantidad_unidades, estado, consumido_at) "
                      "VALUES (?,?, '2026-08-06', ?,?,?,?, 'verificado_ok','')",
                      (pid, PROD, tipo, 'ZZ ' + tipo, cod, UNIDADES))
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", (PROD,))
        mbr = c.lastrowid
        # M10: la llave `lote` lleva sufijo de FASE (es UNIQUE) y el lote físico va en
        # `lote_codigo`. Los dos legajos comparten el lote físico y la producción.
        ebrs = {}
        for fase, sufijo in (('envasado', '-OF'), ('acondicionamiento', '-OA')):
            c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, "
                      " lote_codigo, fase, estado, iniciado_por, iniciado_at_utc, "
                      " cantidad_objetivo_g, produccion_id) "
                      "VALUES (?,1,?,?,?, 'en_proceso', 'zz', datetime('now','utc'), 10000, ?)",
                      (mbr, lote + sufijo, lote, fase, pid))
            ebrs[fase] = c.lastrowid
        c.execute("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, unidades) "
                  "VALUES (?, 'ZZCAD30', ?)", (ebrs['envasado'], UNIDADES))
        conn.commit()
    return pid, ebrs


def _salidas(app, cod):
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos_mee "
            " WHERE UPPER(TRIM(mee_codigo))=? AND LOWER(tipo)='salida'", (cod,)).fetchone()
        return float(r[0] or 0)


def test_envasar_y_despues_acondicionar_saca_el_frasco_UNA_sola_vez(app, admin_client, db_clean):
    """El caso del piso, de punta a punta."""
    pid, ebrs = _sembrar(app)

    r1 = admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebrs['envasado'],
                           data=json.dumps({}), content_type='application/json',
                           headers=csrf_headers())
    assert r1.status_code == 200, r1.data[:300]
    assert _salidas(app, FRASCO) == UNIDADES, 'el envasado no descontó el frasco'

    # El operario acondiciona y lista lo que usó · escribe el MISMO frasco que ya salió.
    r2 = admin_client.post('/api/brd/ebr/%d/cerrar-acondicionamiento' % ebrs['acondicionamiento'],
                           data=json.dumps({'materiales': [{'codigo': FRASCO,
                                                            'cantidad': UNIDADES}]}),
                           content_type='application/json', headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]

    assert _salidas(app, FRASCO) == UNIDADES, (
        'el frasco salió DOS veces del kardex · %s' % _salidas(app, FRASCO))
    motivos = [s.get('motivo', '') for s in (r2.get_json().get('saltados') or [])]
    assert any('ya consumido' in m for m in motivos), (
        'lo saltó sin decir por qué · un descuento que no ocurre y no se declara se ve igual '
        'que uno que sí (M124) · %s' % r2.get_json())
    _limpiar(app)


def test_lo_que_el_envasado_NO_toca_si_se_descuenta_al_acondicionar(app, admin_client, db_clean):
    """El borde en la otra dirección, que es el que evita que el guard se vuelva un muro: la
    CAJA no está en la presentación, así que el envasado no la consume -- y el acondicionamiento
    tiene que descontarla igual que siempre."""
    pid, ebrs = _sembrar(app)
    admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebrs['envasado'],
                      data=json.dumps({}), content_type='application/json',
                      headers=csrf_headers())
    antes = _salidas(app, CAJA)
    r = admin_client.post('/api/brd/ebr/%d/cerrar-acondicionamiento' % ebrs['acondicionamiento'],
                          data=json.dumps({'materiales': [{'codigo': CAJA, 'cantidad': 300}]}),
                          content_type='application/json', headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _salidas(app, CAJA) == antes + 300, (
        'dejó de descontar la caja, que nadie había consumido antes')
    _limpiar(app)


def test_el_stock_del_frasco_baja_EXACTAMENTE_lo_envasado(app, admin_client, db_clean):
    """El número que decide: lo que queda en bodega después de la cadena completa. Se mide
    contra el kardex, que es el stock canónico -- nunca contra el cache (M26)."""
    from database import get_db
    from blueprints.programacion import _get_mee_stock
    pid, ebrs = _sembrar(app)
    with app.app_context():
        antes = float((_get_mee_stock(get_db()) or {}).get(FRASCO.upper(), 0) or 0)
    admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebrs['envasado'],
                      data=json.dumps({}), content_type='application/json',
                      headers=csrf_headers())
    admin_client.post('/api/brd/ebr/%d/cerrar-acondicionamiento' % ebrs['acondicionamiento'],
                      data=json.dumps({'materiales': [{'codigo': FRASCO, 'cantidad': UNIDADES}]}),
                      content_type='application/json', headers=csrf_headers())
    with app.app_context():
        despues = float((_get_mee_stock(get_db()) or {}).get(FRASCO.upper(), 0) or 0)
    assert antes - despues == UNIDADES, (
        'la bodega bajó %s cuando se envasaron %s unidades' % (antes - despues, UNIDADES))
    _limpiar(app)
