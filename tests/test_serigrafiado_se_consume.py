# -*- coding: utf-8 -*-
"""El frasco que volvió SERIGRAFIADO es el que se consume · el base ya salió.

Catalina (4-ago) lo reportó como *"descuenta doble"*. Cuando un envase se manda a serigrafía, su
Salida YA se registró al enviarlo y vuelve como OTRO código. El cierre de envasado descontaba el
BASE otra vez -- porque `producto_presentaciones` sigue apuntando a él -- así que:

  · el base salía DOS veces del kardex, y
  · el serigrafiado, que es el que de verdad se pone en la línea, no se consumía NUNCA: su stock
    sólo crecía.

La redirección ya estaba escrita y probada... en `_descontar_mee_envasado`, que **no tiene llamador
vivo**. El botón real es `POST /api/brd/ebr/<id>/cerrar-envasado`, y ahí `marcacion_ordenes` no se
leía en ninguna línea. Estaba construido y no corría (M121).

**No adivina:** la orden guarda `produccion_id` + `base_codigo` + `serigrafiado_codigo`, así que
"este base, para ESTA producción, volvió como aquel" es un hecho REGISTRADO (M19). Y sólo cuenta
si está **liberado**: mientras está afuera -- o adentro en cuarentena -- ese envase no está para
usarse y el stock canónico no lo cuenta (M153).
"""
import json
import os
import re

PROD = 'ZZ PRODUCTO SERIG'
BASE = 'MEE-ZZS-BASE'
IMPRESO = 'MEE-ZZS-IMPRESO'
TAPA = 'MEE-ZZS-TAPA'
LOTE = 'ZZS-LOTE-1'


def _sin_comentarios(txt):
    fuera = []
    for ln in txt.splitlines():
        if ln.strip().startswith('#'):
            continue
        fuera.append(re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


def _stock(app, cod):
    from database import get_db
    with app.app_context():
        return get_db().execute(
            "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad "
            "                         WHEN LOWER(tipo)='salida' THEN -cantidad ELSE cantidad END),0) "
            "  FROM movimientos_mee WHERE mee_codigo=? AND COALESCE(anulado,0)=0", (cod,)).fetchone()[0]


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod in (BASE, IMPRESO, TAPA):
            c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM marcacion_ordenes WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_checklist WHERE produccion_id IN "
                  " (SELECT id FROM produccion_programada WHERE producto=?)", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        c.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id IN "
                  " (SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZS-%')")
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZS-%'")
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        conn.commit()


def _sembrar(app, estado_marcacion='liberado', con_orden=True):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((BASE, 'ZZ frasco BASE sin marcar'),
                          (IMPRESO, 'ZZ frasco SERIGRAFIADO'),
                          (TAPA, 'ZZ tapa')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',5000,0,'Activo','2026-08-05')", (cod, desc))
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, estado) "
                      "VALUES (?, 'Entrada', 5000, 'ZZS-SEED', 'VIGENTE')", (cod,))
        # La presentación sigue apuntando al BASE · eso es lo normal y es la razón del bug.
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, tapa_codigo, activo, es_default) "
                  "VALUES (?, 'ZZS30', 'ZZ 30 ml', 30, ?, ?, 1, 1)", (PROD, BASE, TAPA))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?, '2026-08-05', 10, 'pendiente', 'eos_plan')", (PROD,))
        pid = c.lastrowid
        if con_orden:
            c.execute("INSERT INTO marcacion_ordenes (base_codigo, serigrafiado_codigo, "
                      " producto_nombre, metodo, proveedor, cantidad_enviada, cantidad_recibida, "
                      " produccion_id, estado, creado_por, creado_en) "
                      "VALUES (?,?,?, 'serigrafia', 'ZZ Serig', 400, 400, ?, ?, 'zz', '2026-08-01')",
                      (BASE, IMPRESO, PROD, pid, estado_marcacion))
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", (PROD,))
        mbr = c.lastrowid
        c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                  " fase, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, "
                  " produccion_id) VALUES (?,1,?,?, 'envasado', 'en_proceso', 'zz', "
                  " datetime('now','utc'), 10000, ?)", (mbr, LOTE + '-OF', LOTE, pid))
        ebr = c.lastrowid
        c.execute("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, unidades) "
                  "VALUES (?, 'ZZS30', 300)", (ebr,))
        conn.commit()
    return pid, ebr


def _cerrar(admin_client, ebr):
    from .conftest import csrf_headers
    return admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, data=json.dumps({}),
                             headers=csrf_headers(), content_type='application/json')


def test_se_consume_el_SERIGRAFIADO_y_no_el_base(app, admin_client, db_clean):
    """El caso de Catalina: el base ya salió al enviarlo a marcar."""
    pid, ebr = _sembrar(app, estado_marcacion='liberado')
    base0, imp0 = _stock(app, BASE), _stock(app, IMPRESO)
    r = _cerrar(admin_client, ebr)
    assert r.status_code in (200, 201), r.data[:400]
    assert _stock(app, BASE) == base0, 'volvió a descontar el BASE, que ya había salido'
    assert imp0 - _stock(app, IMPRESO) == 300, \
        'el serigrafiado no se consumió · su stock sólo crece'
    _limpiar(app)


def test_mientras_esta_AFUERA_no_se_redirige(app, admin_client, db_clean):
    """Si la orden está 'enviado', ese envase todavía está en serigrafía: no está para usarse, y
    redirigir hacia él descontaría algo que no volvió."""
    pid, ebr = _sembrar(app, estado_marcacion='enviado')
    base0, imp0 = _stock(app, BASE), _stock(app, IMPRESO)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert base0 - _stock(app, BASE) == 300, 'no descontó el envase de la presentación'
    assert _stock(app, IMPRESO) == imp0, 'redirigió a un envase que sigue afuera'
    _limpiar(app)


def test_recibido_pero_SIN_liberar_tampoco_se_redirige(app, admin_client, db_clean):
    """Volvió pero sigue en cuarentena: el stock canónico no lo cuenta (M153)."""
    pid, ebr = _sembrar(app, estado_marcacion='recibido')
    imp0 = _stock(app, IMPRESO)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert _stock(app, IMPRESO) == imp0, 'redirigió a un envase que Calidad no liberó'
    _limpiar(app)


def test_sin_orden_de_marcacion_se_descuenta_lo_de_siempre(app, admin_client, db_clean):
    """El caso mayoritario: un envase que nunca va a serigrafía no cambia en nada."""
    pid, ebr = _sembrar(app, con_orden=False)
    base0 = _stock(app, BASE)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert base0 - _stock(app, BASE) == 300
    _limpiar(app)


def test_la_redireccion_es_de_ESTA_produccion(app, admin_client, db_clean):
    """Una orden de marcación de OTRA producción no puede redirigir esta. Emparejar por código a
    secas convertiría un hecho registrado en una coincidencia de nombres (M19)."""
    from database import get_db
    pid, ebr = _sembrar(app, estado_marcacion='liberado')
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE marcacion_ordenes SET produccion_id=999999 WHERE producto_nombre=?",
                     (PROD,))
        conn.commit()
    base0, imp0 = _stock(app, BASE), _stock(app, IMPRESO)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert base0 - _stock(app, BASE) == 300, 'no descontó nada'
    assert _stock(app, IMPRESO) == imp0, 'redirigió con la orden de OTRA producción'
    _limpiar(app)


def test_la_TAPA_no_se_redirige(app, admin_client, db_clean):
    """A serigrafía va el frasco. Redirigir una tapa porque hay una orden del frasco sería
    adivinar, y en un kardex adivinar es descontar el material equivocado."""
    from database import get_db
    pid, ebr = _sembrar(app, estado_marcacion='liberado')
    with app.app_context():
        # una orden que dice que la TAPA vuelve como el impreso · no debe aplicarse
        get_db().execute("INSERT INTO marcacion_ordenes (base_codigo, serigrafiado_codigo, "
                         " producto_nombre, produccion_id, estado, creado_en) "
                         "VALUES (?,?,?,?, 'liberado', '2026-08-01')",
                         (TAPA, IMPRESO, PROD, pid))
        get_db().commit()
    tapa0 = _stock(app, TAPA)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert tapa0 - _stock(app, TAPA) == 300, 'la tapa se redirigió · sólo el frasco va a marcar'
    _limpiar(app)


def test_la_redireccion_se_DECLARA(app, admin_client, db_clean):
    """Un descuento que cambió de código sin decirlo es indistinguible de un error de carga."""
    from database import get_db
    pid, ebr = _sembrar(app, estado_marcacion='liberado')
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    with app.app_context():
        fila = get_db().execute(
            "SELECT COALESCE(despues,'') FROM audit_log WHERE accion='CERRAR_ENVASADO_DESCONTAR_MEE' "
            " ORDER BY id DESC LIMIT 1").fetchone()
    assert fila and IMPRESO in fila[0] and BASE in fila[0], \
        'el audit no dice que se redirigió · ' + str(fila)[:200]
    _limpiar(app)
