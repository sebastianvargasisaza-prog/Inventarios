# -*- coding: utf-8 -*-
"""El envase sale UNA vez del kardex, no dos.

Medido con el código en la mano (5-ago): hay DOS cierres que descuentan el mismo empaque desde
la misma fuente, cada uno con su propio candado, y ninguno mira el del otro:

  · `cerrar-envasado` (brd.py) lee `producto_presentaciones` y marca `envases_descontados_at`.
  · el cierre de acondicionamiento del Kanban (auto_plan.py) lee `produccion_checklist` y marca
    `consumido_at`.
  · y el checklist SE PRE-LLENA desde `producto_presentaciones` (programacion.py:21371), o sea
    exactamente los mismos códigos.

En el flujo normal el mismo lote físico pasa por los dos (envasar → acondicionar), así que el
frasco, la tapa y la caja salían DOS VECES. El kardex mostraba menos envases de los que hay en el
estante, y abastecimiento los volvía a pedir.

El arreglo no es un tercer candado: es que los dos caminos usen el MISMO libro mayor
(`produccion_checklist.consumido_at`), que ya existía. Un hecho con dos registros diverge siempre
(M99); un candado por camino no es un candado (M119).
"""
import json
import os
import re

PROD = 'ZZ PRODUCTO DOBLE'
FRASCO = 'MEE-ZZD-FRASCO'
TAPA = 'MEE-ZZD-TAPA'
LOTE = 'ZZD-LOTE-1'


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
        for cod in (FRASCO, TAPA):
            c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_checklist WHERE produccion_id IN "
                  " (SELECT id FROM produccion_programada WHERE producto=?)", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        c.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id IN "
                  " (SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZD-%')")
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZD-%'")
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        conn.commit()


def _sembrar(app):
    """Deja el lote listo para CERRAR el envasado, con su checklist ya pre-llenado."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((FRASCO, 'ZZ frasco'), (TAPA, 'ZZ tapa')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',5000,0,'Activo','2026-08-05')", (cod, desc))
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, estado) "
                      "VALUES (?, 'Entrada', 5000, 'ZZD-SEED', 'VIGENTE')", (cod,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, tapa_codigo, activo, es_default) "
                  "VALUES (?, 'ZZD30', 'ZZ 30 ml', 30, ?, ?, 1, 1)", (PROD, FRASCO, TAPA))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?, '2026-08-05', 10, 'pendiente', 'eos_plan')", (PROD,))
        pid = c.lastrowid
        # El checklist tal como lo deja el generador: mismo envase y misma tapa que la
        # presentación, todavía SIN consumir.
        for tipo, cod in (('envase_primario', FRASCO), ('tapa', TAPA)):
            # `producto_nombre` y `fecha_planeada` son NOT NULL · el fixture se arma contra el
            # CREATE TABLE real, no contra las columnas que uno recuerda.
            c.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, "
                      " fecha_planeada, item_tipo, descripcion, mee_codigo_asignado, "
                      " cantidad_unidades, estado, consumido_at) "
                      "VALUES (?,?, '2026-08-05', ?,?,?,?, 'verificado_ok','')",
                      (pid, PROD, tipo, 'ZZ ' + tipo, cod, 300))
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", (PROD,))
        mbr = c.lastrowid
        # ⚠ El legajo de ENVASADO lleva sufijo de fase en `lote` (UNIQUE) y el lote FÍSICO en
        # `lote_codigo` · M10. Sembrar los dos iguales rompería la convención que el resto lee.
        c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                  " fase, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, "
                  " produccion_id) VALUES (?,1,?,?, 'envasado', 'en_proceso', 'zz', "
                  " datetime('now','utc'), 10000, ?)",
                  (mbr, LOTE + '-OF', LOTE, pid))
        ebr = c.lastrowid
        c.execute("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, unidades) "
                  "VALUES (?, 'ZZD30', 300)", (ebr,))
        conn.commit()
    return pid, ebr


def test_cerrar_envasado_RECLAMA_el_checklist(app, admin_client, db_clean):
    """Sin el reclamo, el cierre de acondicionamiento vuelve a descontar lo mismo después."""
    from database import get_db
    from .conftest import csrf_headers
    pid, ebr = _sembrar(app)
    r = admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebr,
                          data=json.dumps({}), headers=csrf_headers(),
                          content_type='application/json')
    assert r.status_code in (200, 201), r.data[:400]
    with app.app_context():
        filas = get_db().execute(
            "SELECT mee_codigo_asignado, COALESCE(consumido_at,''), COALESCE(consumido_contexto,'') "
            "  FROM produccion_checklist WHERE produccion_id=?", (pid,)).fetchall()
    for cod, cons, ctx in filas:
        assert cons.strip(), 'el cierre de envasado no reclamó %s · el Kanban lo va a descontar otra vez' % cod
        assert ctx == 'envasado_ebr', ctx
    _limpiar(app)


def test_el_envase_sale_UNA_sola_vez(app, admin_client, db_clean):
    """La prueba que importa: correr LOS DOS cierres y contar el kardex."""
    from database import get_db
    from .conftest import csrf_headers
    pid, ebr = _sembrar(app)
    antes = _stock(app, FRASCO)
    r = admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, data=json.dumps({}),
                          headers=csrf_headers(), content_type='application/json')
    assert r.status_code in (200, 201), r.data[:300]
    tras_of = _stock(app, FRASCO)
    assert antes - tras_of == 300, 'el envasado descontó %s (esperaba 300)' % (antes - tras_of)

    # Ahora el cierre de acondicionamiento del Kanban, que lee el checklist.
    from inventario_helpers import aplicar_movimiento_mee as _ap
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        pendientes = c.execute(
            "SELECT id, mee_codigo_asignado, cantidad_unidades FROM produccion_checklist "
            " WHERE produccion_id=? AND COALESCE(consumido_at,'')='' "
            "   AND COALESCE(mee_codigo_asignado,'')!=''", (pid,)).fetchall()
        for _mid, _mcod, _mcant in pendientes:
            _ap(conn, _mcod, 'Salida', int(_mcant or 0),
                observaciones='Cierre Kanban acondicionamiento · test', responsable='zz',
                lote_ref=str(pid))
        conn.commit()
    tras_oa = _stock(app, FRASCO)
    assert tras_oa == tras_of, \
        'el frasco salió DOS veces: %s tras envasar y %s tras acondicionar' % (tras_of, tras_oa)
    _limpiar(app)


def test_lo_que_YA_bajo_no_se_vuelve_a_descontar(app, admin_client, db_clean):
    """El caso inverso: si acondicionamiento corrió primero, el envasado no puede repetirlo."""
    from database import get_db
    from .conftest import csrf_headers
    pid, ebr = _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE produccion_checklist SET consumido_at=datetime('now','-5 hours'), "
                     " consumido_contexto='kanban_acond' WHERE produccion_id=?", (pid,))
        conn.commit()
    antes = _stock(app, FRASCO)
    r = admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, data=json.dumps({}),
                          headers=csrf_headers(), content_type='application/json')
    assert r.status_code in (200, 201), r.data[:300]
    assert _stock(app, FRASCO) == antes, 'volvió a descontar un envase que ya había salido'
    _limpiar(app)


def test_sin_libro_mayor_se_DECLARA(app, db_clean):
    """Un legajo sin `produccion_id` no tiene checklist que consultar: descuenta como siempre,
    pero lo dice. Un descuento que no se pudo coordinar no se puede presentar como coordinado."""
    src = _sin_comentarios(open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'api/blueprints/brd.py'), encoding='utf-8').read())
    i = src.find('def cerrar_envasado_ebr')
    bloque = src[i:i + 12000]
    assert '_sin_libro' in bloque, 'no distingue "coordinado" de "no se pudo coordinar"'
    assert 'sin_libro_mayor' in bloque, 'no lo deja en el audit'


def test_el_reclamo_va_con_CAS(app, db_clean):
    """Con 3 workers, leer-y-después-marcar deja pasar los dos. El reclamo tiene que llevar la
    condición en el WHERE y mirar el rowcount (M27/M73)."""
    src = _sin_comentarios(open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'api/blueprints/brd.py'), encoding='utf-8').read())
    i = src.find("consumido_contexto='envasado_ebr'")
    assert i > 0, 'no encontré el reclamo del checklist'
    bloque = src[i:i + 400]
    assert "COALESCE(consumido_at,'')=''" in bloque, 'el reclamo no lleva el CAS en el WHERE'
    assert 'rowcount == 0' in bloque, 'no verifica el rowcount'
