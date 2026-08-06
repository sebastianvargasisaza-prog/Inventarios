# -*- coding: utf-8 -*-
"""Imprimir los rótulos de varias materias primas de una sola vez (Alejandro, 6-ago).

Sebastián: *"que no les tarde mucho ese rótulo: seleccionan las materias primas que quieran, le
dan imprimir, salen en cuarentena y los pegan"*. Y después: *"adicional al final puede ser
impresión masiva de los lotes, también para que puedan hacerlo por allí"*.

Es **EL MISMO rótulo**, no uno nuevo: se arma con `_rotulo_mp_hojas`, que se extrajo del rótulo
individual **cortando el cuerpo por líneas, sin tocar la maqueta**. Es un documento REGULADO
(COC-PRO-002-F07) y dos renderizadores divergen -- terminan imprimiendo distinto según por dónde
se pida (M1/M93).

Lo que cambia es lo que Alejandro necesita: los campos que llenan el F01/F02 salen **en blanco**
porque todavía no se hicieron (un dato inventado miente con formato de verdad · M115), y el
**ESTADO va en grande** para reemplazar el sticker que hoy pegan a mano.

⚠ El estado sale del **KARDEX**, nunca de la URL: un rótulo que diga APROBADO pegado a un bidón
que sigue en cuarentena es peor que no tener rótulo.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'MP00050'
LOTE_A = 'ZZROT-A'
LOTE_B = 'ZZROT-B'


def _cli(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app):
    """Dos entradas del mismo material: una en CUARENTENA y otra ya liberada (VIGENTE)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos WHERE lote IN (?,?)", (LOTE_A, LOTE_B))
        ids = {}
        for lote, estado in ((LOTE_A, 'CUARENTENA'), (LOTE_B, 'VIGENTE')):
            c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                      " lote, fecha, estado_lote, proveedor) "
                      "VALUES (?,?, 'Entrada', ?,?, '2026-08-06', ?, 'PROVEEDOR ZZ')",
                      (COD, 'ZZ MATERIAL', 4000, lote, estado))
            ids[lote] = c.lastrowid
        conn.commit()
    return ids


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM movimientos WHERE lote IN (?,?)", (LOTE_A, LOTE_B))
        conn.commit()


def test_salen_los_DOS_rotulos_en_un_solo_documento(app, db_clean):
    ids = _sembrar(app)
    r = _cli(app).get('/rotulos-recepcion?movs=%d,%d' % (ids[LOTE_A], ids[LOTE_B]))
    assert r.status_code == 200, r.data[:300]
    h = r.data.decode('utf-8', 'replace')
    assert h.count('class="sheet"') == 2, 'no salieron las dos hojas'
    assert LOTE_A in h and LOTE_B in h, 'falta alguno de los lotes'
    _limpiar(app)


def test_el_ESTADO_sale_del_kardex_no_de_la_URL(app, db_clean):
    """El lote en cuarentena dice CUARENTENA y el liberado dice APROBADO, aunque se pidan juntos.
    Y no se puede forzar por query string: ahí es donde un rótulo empieza a mentir."""
    ids = _sembrar(app)
    c = _cli(app)
    h = c.get('/rotulos-recepcion?movs=%d,%d' % (ids[LOTE_A], ids[LOTE_B])).data.decode(
        'utf-8', 'replace')
    assert 'CUARENTENA' in h, 'el lote en cuarentena no salió marcado'
    assert 'APROBADO' in h, 'el lote liberado no salió aprobado'
    # forzar por URL no cambia nada: el estado lo decide el kardex
    h2 = c.get('/rotulos-recepcion?movs=%d&estado=APROBADO' % ids[LOTE_A]).data.decode(
        'utf-8', 'replace')
    assert 'CUARENTENA' in h2 and 'APROBADO' not in h2.split('estadobig')[1][:80], (
        'se pudo forzar APROBADO por la URL sobre un lote en cuarentena')
    _limpiar(app)


def test_el_rotulo_individual_sigue_saliendo_IGUAL(app, db_clean):
    """La extracción no puede cambiar lo que ya se imprimía: es un formato regulado. Se comparan
    las marcas que definen la maqueta."""
    ids = _sembrar(app)
    h = _cli(app).get('/rotulo-recepcion/%s/%s/4000' % (COD, LOTE_A)).data.decode(
        'utf-8', 'replace')
    for marca in ('COC-PRO-002-F07', 'class="sheet"', 'Numero de lote', 'Fecha recepcion',
                  'Vencimiento', 'Ubicacion', 'Realizado por', 'Revisado por'):
        assert marca in h, 'la extracción se comió: %s' % marca
    _limpiar(app)


def test_lo_que_NO_se_pudo_rotular_se_DICE(app, db_clean):
    """Imprimir 3 de 5 sin avisar es peor que fallar: el que pega los rótulos no tiene forma de
    saber cuál falta (M124)."""
    r = _cli(app).get('/rotulos-recepcion?movs=999999999')
    assert r.status_code == 404, r.status_code


def test_sin_seleccion_no_abre_un_documento_vacio(app, db_clean):
    r = _cli(app).get('/rotulos-recepcion')
    assert r.status_code == 400
    assert 'Eleg' in r.data.decode('utf-8', 'replace'), 'no explica qué hacer'


def test_recepcion_resuelve_los_lotes_y_declara_los_que_faltan(app, db_clean):
    """El bloque de impresión masiva de /recepcion: se pegan números de lote y se resuelven
    contra el kardex."""
    ids = _sembrar(app)
    r = _cli(app).get('/api/lotes/por-numero?lotes=%s,%s,NO-EXISTE-ZZ' % (LOTE_A, LOTE_B))
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert sorted(d['movs']) == sorted([ids[LOTE_A], ids[LOTE_B]]), d
    assert d['no_encontrados'] == ['NO-EXISTE-ZZ'], (
        'no declaró el lote que no encontró · imprimir de menos sin avisar es lo peor')
    _limpiar(app)


def test_las_dos_pantallas_tienen_por_donde_pedirlo(app):
    """Una capacidad que nadie puede alcanzar no existe (M121): botón en Calidad y bloque en
    Recepción, cada uno con su función definida."""
    from templates_py.calidad_html import CALIDAD_HTML as CAL
    from templates_py.recepcion_html import RECEPCION_HTML as REC
    assert 'rotImprimir()' in CAL and 'function rotImprimir(' in CAL
    assert 'class="rot-chk"' in CAL, 'no hay casilla por fila'
    assert 'rotTodas(' in CAL and 'function rotTodas(' in CAL
    assert 'rotmImprimir()' in REC and 'function rotmImprimir(' in REC
    assert '/rotulos-recepcion?movs=' in CAL and '/rotulos-recepcion?movs=' in REC
