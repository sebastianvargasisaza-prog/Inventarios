# -*- coding: utf-8 -*-
"""¿El inventario de envases JUNTA con cada producto?

Sebastián (5-ago): *"debemos ir a revisar lo que hay, si ya junta con cada producto y demás"*.

El diagnóstico que existía contestaba media pregunta: *"¿el producto tiene frasco?"*. Pero el
motor de compra también lee la TAPA, la CAJA y las PIEZAS del frasco (gotero, plegadiza), así que
un producto con frasco y sin tapa salía en VERDE mientras su tapa no se pedía nunca. Medido en el
snapshot local: las 13 presentaciones activas tienen frasco y **ninguna** tiene tapa ni caja -- la
capacidad de comprarlas está construida desde el 18-jun y sin un solo dato, que es igual a no
existir (M121).

La regla que ordena esto: **cuando un cálculo excluye cosas, el resultado enumera lo excluido y
por qué** (M124). Un sí/no que esconde tres huecos se lee como "está todo bien".
"""
import json
import os
import re

PROD = 'ZZ PRODUCTO UNION'
FRASCO = 'MEE-ZZU-FRASCO'
TAPA = 'MEE-ZZU-TAPA'
GOTERO = 'MEE-ZZU-GOTERO'
IMPRESO = 'MEE-ZZU-IMPRESO'
FANTASMA = 'MEE-ZZU-NOEXISTE'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        for cod in (FRASCO, TAPA, GOTERO, IMPRESO):
            c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (cod,))
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        conn.commit()


def _sembrar(app, tapa=TAPA, caja='', pieza=GOTERO, serigrafiado=IMPRESO):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((FRASCO, 'ZZ frasco'), (TAPA, 'ZZ tapa'),
                          (GOTERO, 'ZZ gotero'), (IMPRESO, 'ZZ frasco impreso')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Frasco','und',0,0,'Activo','2026-08-05')", (cod, desc))
        if serigrafiado:
            c.execute("UPDATE maestro_mee SET material_referencia=? WHERE codigo=?",
                      (serigrafiado, FRASCO))
        if pieza:
            c.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                      " creado_at) VALUES (?,?,'',1,'2026-08-05')", (FRASCO, pieza))
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                  "VALUES (?, 10, 1)", (PROD,))
        # `presentacion_codigo` y `etiqueta` son NOT NULL · el fixture se arma contra el
        # CREATE TABLE real, no contra las columnas que uno recuerda.
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, activo) "
                  "VALUES (?,'ZZU30','ZZ 30 ml',?,?,?,?,1)",
                  (PROD, 30.0, FRASCO, tapa, caja))
        conn.commit()


def _union(admin_client):
    r = admin_client.get('/api/abastecimiento/envases-cobertura')
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j.get('union') is not None, 'la unión no se pudo calcular · ' + str(j.get('aviso'))
    return {x['producto']: x for x in j['union']}, j


def test_la_TAPA_que_falta_se_NOMBRA(app, admin_client, db_clean):
    """El caso medido: frasco puesto, tapa vacía. Antes esto salía en verde."""
    _sembrar(app, tapa='', caja='')
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is False, 'una presentación sin tapa se declaró completa'
    assert 'tapa' in fila['falta'], fila['falta']
    assert 'caja' in fila['falta'], fila['falta']
    _limpiar(app)


def test_una_presentacion_COMPLETA_no_grita(app, admin_client, db_clean):
    """Sin este caso, un diagnóstico que siempre marca algo se vuelve ruido y deja de mirarse."""
    _sembrar(app, tapa=TAPA, caja=GOTERO)
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is True, fila['falta']
    assert fila['falta'] == []
    _limpiar(app)


def test_un_codigo_que_NO_existe_en_el_maestro_se_declara(app, admin_client, db_clean):
    """Una presentación puede apuntar a un código muerto: el campo está lleno pero el motor no
    encuentra nada que comprar. "Tiene tapa" y "tiene una tapa que existe" no son lo mismo."""
    _sembrar(app, tapa=FANTASMA, caja=GOTERO)
    fila = _union(admin_client)[0][PROD]
    assert fila['completo'] is False
    assert any(FANTASMA in f for f in fila['falta']), fila['falta']
    _limpiar(app)


def test_la_PIEZA_muerta_del_frasco_tambien_se_declara(app, admin_client, db_clean):
    """El gotero vive en `mee_partes`, no en la presentación · si apunta a un código que no
    existe, la recepción no lo puede ingresar y el envasado no lo puede descontar."""
    _sembrar(app, tapa=TAPA, caja=GOTERO, pieza=FANTASMA)
    fila = _union(admin_client)[0][PROD]
    assert any(FANTASMA in f for f in fila['falta']), fila['falta']
    assert any(p['codigo'] == FANTASMA and p['en_maestro'] is False for p in fila['piezas'])
    _limpiar(app)


def test_el_puente_base_a_SERIGRAFIADO_se_reporta(app, admin_client, db_clean):
    """`material_referencia` vacío = lo que vuelve de serigrafía no queda atado a este producto.
    Medido en el snapshot local: está vacío en los 129 envases, o sea que el flujo de marcación
    está desconectado de la compra. Un hueco que no se mide no se cierra."""
    _sembrar(app, serigrafiado=IMPRESO)
    fila = _union(admin_client)[0][PROD]
    assert fila['serigrafiado'] == IMPRESO, fila

    _sembrar(app, serigrafiado='')
    fila = _union(admin_client)[0][PROD]
    assert fila['serigrafiado'] == '', fila
    _limpiar(app)


def test_los_CONTADORES_cuadran_con_el_detalle(app, admin_client, db_clean):
    """El número del encabezado y la lista de abajo salen del MISMO recorrido: si se cuentan
    aparte, un día dicen cosas distintas y no se puede creer en ninguno (M5/M161)."""
    _sembrar(app, tapa='', caja='')
    filas, j = _union(admin_client)
    un = j['union']
    assert j['n_presentaciones'] == len(un)
    assert j['n_completas'] == sum(1 for x in un if x['completo'])
    assert j['n_sin_tapa'] == sum(1 for x in un if not x['tapa'])
    assert j['n_sin_caja'] == sum(1 for x in un if not x['caja'])
    assert j['n_sin_serigrafiado'] == sum(1 for x in un if not x['serigrafiado'])
    _limpiar(app)


def test_lo_que_ya_leia_la_pantalla_NO_cambio(app, admin_client, db_clean):
    """El cambio es ADITIVO (M117): la pantalla de Reparto ya consume `sin_envase`/`no_aplica`
    y no puede romperse porque se agregó el detalle."""
    _sembrar(app)
    j = _union(admin_client)[1]
    for k in ('n_activos', 'n_con_envase', 'n_sin_envase', 'no_aplica', 'sin_envase',
              'con_envase', 'donde_configurar'):
        assert k in j, 'desapareció la llave %s que la pantalla ya usaba' % k
    _limpiar(app)


def test_la_pantalla_PINTA_la_union(app, db_clean):
    """Un endpoint que nadie abre no existe (M121). Y el escáner quita los comentarios antes de
    buscar, o encuentra la prosa del propio autor (M154)."""
    # ⚠ El JS del dashboard se EXTRAE a `DASHBOARD_APP_JS` al importar el módulo (bundle
    # cacheable servido como /planta-app.js). Buscarlo en `DASHBOARD_HTML` da CERO y el test
    # falla con el código correcto: hay que leer el valor FINAL, no el que uno cree que es
    # (M158 · un guard que lee el literal no ve lo que el módulo hace después).
    import templates_py.dashboard_html as D
    H = ((getattr(D, 'DASHBOARD_APP_JS', '') or '')
         + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML)
    js = re.sub(r'//[^\n]*', '', H)
    i = js.find('async function cargarReparto')
    assert i > 0
    bloque = js[i:i + 9000]
    assert 'cov.union' in bloque, 'la pantalla no lee la unión'
    assert 'Serigrafiado' in bloque, 'no muestra el puente base → impreso'
    assert 'cov.aviso' in bloque, 'si la unión no se pudo calcular, la pantalla no lo dice'
