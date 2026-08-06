# -*- coding: utf-8 -*-
"""El KIT del envase se VE en la lista, no sólo dentro del botón.

Sebastián, mirando el inventario MEE: *"yo creo que la mejor forma de organizarlos es aquí, así le
digo a Catalina que los organice... y al hacerlo cómo quedaría? al envase le sale abajo o cómo
organizamos aquí esto"*.

El botón **Kit** ya permitía asociar piezas que ya existen (gotero, tapa, plegadiza) con su
cantidad — eso estaba bien y no se tocó. Lo que faltaba es que el resultado se VIERA: un envase
con kit se veía idéntico a uno sin kit, así que quien organiza no puede saber qué ya hizo sin
abrir cada fila una por una. Una capacidad cuyo resultado no se ve es una capacidad que nadie usa
(M121), y encima obliga a re-abrir 101 filas para saber en qué vas.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

ENV = 'MEE-ZZK-FRASCO'
GOT = 'MEE-ZZK-GOTERO'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
        for cod in (ENV, GOT):
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        conn.commit()


def _sembrar(app, con_kit=True, cantidad=2):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        for cod, desc in ((ENV, 'ZZ frasco con kit'), (GOT, 'ZZ gotero negro')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Envase','und',10,0,'Activo','2026-08-05')", (cod, desc))
        if con_kit:
            c.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                      " creado_at) VALUES (?,?,'',?,'2026-08-05')", (ENV, GOT, cantidad))
        conn.commit()


def _fila(admin_client, cod):
    r = admin_client.get('/api/mee/stock')
    assert r.status_code == 200, r.data[:200]
    for it in (r.get_json().get('items') or []):
        if (it.get('codigo') or '').strip().upper() == cod:
            return it
    return None


def test_la_lista_DEVUELVE_el_kit(app, admin_client, db_clean):
    _sembrar(app, cantidad=2)
    f = _fila(admin_client, ENV)
    assert f is not None, 'el envase no salió en la lista'
    assert f.get('partes'), 'la lista no trae el kit · hay que abrir cada fila para saberlo'
    p = f['partes'][0]
    assert p['codigo'] == GOT
    assert float(p['cantidad']) == 2, 'la cantidad por envase se perdió'
    assert p['descripcion'], 'sin descripción, el código solo no dice qué pieza es'
    _limpiar(app)


def test_un_envase_SIN_kit_devuelve_lista_vacia_no_None(app, admin_client, db_clean):
    """Vacío (va solo) y None (no se pudo leer) son cosas distintas: la pantalla pinta un aviso
    para el segundo y nada para el primero (M100)."""
    _sembrar(app, con_kit=False)
    f = _fila(admin_client, ENV)
    assert f.get('partes') == [], f.get('partes')
    _limpiar(app)


def test_NO_es_una_consulta_por_fila(app, db_clean):
    """101 filas × una consulta cada una es un N+1 disfrazado (M63). El kit se trae en UNA
    consulta para todos."""
    import io
    src = io.open(os.path.join(RAIZ, 'api/blueprints/inventario.py'), encoding='utf-8').read()
    i = src.find('EL KIT DE CADA ENVASE')
    assert i > 0, 'no encontré el bloque del kit'
    # La ventana se acota al FINAL del bloque (el `return jsonify`), no a un número de
    # caracteres: al crecer el bloque una ventana fija deja de cubrirlo y el test falla con el
    # código correcto.
    fin = src.find('return jsonify', i)
    assert fin > i
    bloque = src[i:fin]
    assert 'FROM mee_partes p' in bloque
    # una sola ejecución, fuera del loop de filas
    assert bloque.count('c.execute(') == 1, 'hay más de una consulta · huele a N+1'
    assert 'for _r in rows:' in bloque, 'no reparte el resultado sobre las filas'
    # y el reparto ocurre DESPUÉS de la consulta, no adentro
    assert bloque.find('c.execute(') < bloque.find('for _r in rows:')


def test_la_pantalla_PINTA_el_kit_debajo_del_envase(app, db_clean):
    import templates_py.dashboard_html as D
    H = ((getattr(D, 'DASHBOARD_APP_JS', '') or '')
         + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML)
    js = re.sub(r'//[^\n]*', '', H)
    assert 'function _meeKitLinea' in js, 'no hay nada que pinte el kit en la fila'
    # ⚠ Y se USA en la celda de la descripción (si no, existe y no se ve · M112). Buscar
    # `_meeKitLinea(m)` a secas encuentra la DEFINICIÓN y pasa en verde con la llamada borrada
    # (M154): se exige la forma CONCATENADA, que sólo aparece donde se pinta.
    assert "+_meeKitLinea(m)+" in js, 'el kit se calcula y no se pinta en la fila'
    i = js.find('function _meeKitLinea')
    bloque = js[i:i + 1400]
    assert 'm.partes===null' in bloque, 'no distingue "va solo" de "no pude leer"'


def test_el_boton_Kit_SIGUE_ahi(app, db_clean):
    """Lo que ya funcionaba no se tocó: asociar piezas se sigue haciendo desde ahí."""
    # ⚠ El JS del dashboard se reparte en DOS bundles al importar el módulo · mirar sólo uno da
    # rojo con el código correcto (M158).
    import templates_py.dashboard_html as D
    H = (D.DASHBOARD_HTML + (getattr(D, 'DASHBOARD_APP_JS', '') or '')
         + (getattr(D, 'DASHBOARD_CORE_JS', '') or ''))
    assert 'meeKit(' in H and 'function meeKit(' in H


# ── una pieza COMPARTIDA entre varios envases ────────────────────────────────

ENV2 = 'MEE-ZZK-FRASCO2'


def _sembrar_compartido(app):
    """El mismo gotero como parte de DOS envases distintos."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV2,))
        c.execute("DELETE FROM maestro_mee WHERE codigo=?", (ENV2,))
        for cod, desc in ((ENV, 'ZZ frasco A'), (ENV2, 'ZZ frasco B'), (GOT, 'ZZ gotero negro')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, "
                      " stock_actual, stock_minimo, estado, fecha_creacion) "
                      "VALUES (?,?,'Envase','und',500,0,'Activo','2026-08-05')", (cod, desc))
        for env in (ENV, ENV2):
            c.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                      " creado_at) VALUES (?,?,'',1,'2026-08-05')", (env, GOT))
        conn.commit()


def _limpiar2(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM mee_partes WHERE mee_codigo IN (?,?)", (ENV, ENV2))
        for cod in (ENV, ENV2, GOT):
            c.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        conn.commit()


def test_una_pieza_COMPARTIDA_dice_quien_la_usa(app, admin_client, db_clean):
    """Sebastián: *"un mismo gotero puede ser para varios envases... eso cómo queda? pues
    muestra el total que hay de cada cosa?"*. Sí: la pieza tiene UNA fila y UN stock, porque es
    UN material compartido. Pero mirar 500 goteros no dice nada si no se sabe cuántos envases
    los consumen -- su demanda es la SUMA de todos los que lo llevan (M124)."""
    _sembrar_compartido(app)
    g = _fila(admin_client, GOT)
    assert g is not None
    assert sorted(g.get('usado_en') or []) == sorted([ENV, ENV2]), g.get('usado_en')
    _limpiar2(app)


def test_la_pieza_compartida_tiene_UN_solo_stock(app, admin_client, db_clean):
    """No se duplica por cada envase que la usa: es el mismo material físico en la bodega."""
    _sembrar_compartido(app)
    filas = [x for x in (admin_client.get('/api/mee/stock').get_json().get('items') or [])
             if (x.get('codigo') or '').strip().upper() == GOT]
    assert len(filas) == 1, 'la pieza compartida aparece %d veces en la lista' % len(filas)
    _limpiar2(app)


def test_un_envase_que_no_es_parte_de_nadie_no_dice_nada(app, admin_client, db_clean):
    """Si cada fila mostrara "lo usan 0", la lista se llenaría de ruido."""
    _sembrar(app, con_kit=True)
    f = _fila(admin_client, ENV)
    assert (f.get('usado_en') or []) == [], f.get('usado_en')
    _limpiar(app)


def test_la_pantalla_PINTA_quien_usa_la_pieza(app, db_clean):
    import templates_py.dashboard_html as D
    js = re.sub(r'//[^\n]*', '',
                (getattr(D, 'DASHBOARD_APP_JS', '') or '')
                + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML)
    assert 'function _meeUsadoLinea' in js
    assert '+_meeUsadoLinea(m)+' in js, 'se calcula y no se pinta'
