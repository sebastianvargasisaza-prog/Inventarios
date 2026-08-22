# -*- coding: utf-8 -*-
"""Antes de cerrar: que nada haya quedado duplicado ni en el lugar equivocado.

Sebastián, sobre la nevera: *"confirma lo que había, ya lo hice, lo puse, le cambié y agregué
nuevos ... revisá bien que nada quede duplicado o donde no es, porque sería perder tiempo"*.

Los tres accidentes que de verdad pasan cuando se ingresa material mientras se cuenta:

  1. **El mismo lote ingresado DOS veces** · el kardex suma las dos, el stock queda inflado y
     no da ningún síntoma: se descubre al producir (M172).
  2. **El mismo lote en DOS ubicaciones** · ir a buscarlo manda al estante equivocado.
  3. **El mismo material bajo DOS códigos** · la demanda se parte entre los dos y el FEFO
     nunca ve el total (M1/M17). Es el más caro y el más fácil de provocar dando de alta algo
     que ya existía.

⚠ El caso 3 compara el INCI **con el grado**: sin eso los tres pesos del hialurónico y los dos
grados de la Centella saldrían como duplicados y el informe gritaría sobre material que está
bien (M276). Un detector que grita se deja de mirar (M170).
"""
import pytest

COD = 'MPDUPCIERRE'
EST = 'DUP-EST-5'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id LIKE ?", (COD + '%',))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE ?", (COD + '%',))
        c.commit()


def _hoy():
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')


def _mp(c, cod, inci, com=''):
    c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
              "VALUES (?,?,?,1)", (cod, com or cod, inci))


def _mov(c, cod, lote, cant, est, fecha=None, nombre='MP DUP'):
    c.execute(
        "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
        " fecha, operador, estanteria, estado_lote) "
        "VALUES (?,?,'Entrada',?,?,?,?,?,'VIGENTE')",
        (cod, nombre, cant, lote, fecha or _hoy(), 'sebastian', est))


def _informe(client):
    r = client.get('/api/inventario/cuadre-informe')
    assert r.status_code == 200, r.data[:200]
    return r.get_json() or {}


def _hallazgos(d, cod=None):
    return [x for x in d.get('posibles_duplicados') or []
            if cod is None or x.get('codigo_mp', '').upper() == cod]


# ─────────────────────────────────────────────────────────────────────────────
# 1 · el mismo lote ingresado dos veces
# ─────────────────────────────────────────────────────────────────────────────

def test_el_mismo_lote_ingresado_DOS_veces_se_reporta(admin_client, app):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'INCI DUP UNO')
        _mov(c, COD, 'L-DOBLE', 500.0, EST)
        _mov(c, COD, 'L-DOBLE', 500.0, EST)   # el mismo, otra vez
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client), COD)
        assert any('entradas' in x['que'] for x in h), (
            'no reporta el lote ingresado dos veces: %s' % h)
    finally:
        _limpiar(app)


def test_un_lote_ingresado_UNA_vez_no_se_reporta(admin_client, app):
    """El guard tiene que distinguir, o reportaria todo y se dejaria de mirar (M170)."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'INCI DUP UNO')
        _mov(c, COD, 'L-SOLO', 500.0, EST)
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client), COD)
        assert not h, 'reporta como duplicado un lote que se ingreso una sola vez: %s' % h
    finally:
        _limpiar(app)


# ─────────────────────────────────────────────────────────────────────────────
# 2 · el mismo lote en dos ubicaciones
# ─────────────────────────────────────────────────────────────────────────────

def test_el_mismo_lote_en_DOS_ubicaciones_se_reporta(admin_client, app):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'INCI DUP DOS')
        _mov(c, COD, 'L-DOSLADOS', 300.0, EST)
        _mov(c, COD, 'L-DOSLADOS', 200.0, 'DUP-EST-9')
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client), COD)
        assert any('ubicaciones' in x['que'] for x in h), (
            'no reporta el lote que figura en dos estantes: %s' % h)
        txt = ' '.join(x['detalle'] for x in h)
        assert EST in txt and 'DUP-EST-9' in txt, 'no dice en cuales dos esta'
    finally:
        _limpiar(app)


# ─────────────────────────────────────────────────────────────────────────────
# 3 · el mismo material bajo dos codigos
# ─────────────────────────────────────────────────────────────────────────────

def test_el_mismo_material_bajo_DOS_codigos_se_reporta(admin_client, app):
    """El mas caro: la demanda se parte entre los dos y el FEFO nunca ve el total."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'GLICERINA VEGETAL DUP')
        _mp(c, COD + 'B', 'glicerina vegetal dup')   # el mismo INCI, otro codigo
        _mov(c, COD, 'L-A', 400.0, EST)
        _mov(c, COD + 'B', 'L-B', 600.0, EST)
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client))
        assert any('codigos' in x['que'] for x in h), (
            'no reporta el material duplicado en dos codigos: %s' % h)
    finally:
        _limpiar(app)


def test_dos_GRADOS_del_mismo_INCI_no_son_un_duplicado(admin_client, app):
    """Un detector que grita se deja de mirar: los hialuronicos y la Centella comparten INCI
    base y NO son el mismo material (M276)."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'ACIDO DUP (300 kD)')
        _mp(c, COD + 'B', 'ACIDO DUP (50 kD)')
        _mov(c, COD, 'L-300', 400.0, EST)
        _mov(c, COD + 'B', 'L-50', 600.0, EST)
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client))
        assert not any('codigos' in x['que'] for x in h), (
            'reporta como duplicado dos GRADOS distintos: %s' % h)
    finally:
        _limpiar(app)


def test_un_codigo_viejo_EN_CERO_no_cuenta_como_duplicado(admin_client, app):
    """Dos codigos donde uno esta en cero es un codigo viejo, no un duplicado activo."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        _mp(c, COD, 'ACEITE DUP CERO')
        _mp(c, COD + 'B', 'ACEITE DUP CERO')
        _mov(c, COD, 'L-VIVO', 400.0, EST)
        # el otro codigo existe pero no tiene material
        c.commit()
    try:
        h = _hallazgos(_informe(admin_client))
        assert not any('codigos' in x['que'] for x in h), (
            'reporta como duplicado un codigo que esta en cero: %s' % h)
    finally:
        _limpiar(app)


# ─────────────────────────────────────────────────────────────────────────────
# y la puerta
# ─────────────────────────────────────────────────────────────────────────────

def test_la_pantalla_lo_PINTA(app):
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    assert 'posibles_duplicados' in H, 'la pantalla no lee los posibles duplicados'
    i = H.find('Revisar antes de cerrar')
    assert i != -1, 'no hay seccion de duplicados'
    bloque = H[i:i + 1200]
    assert 'f.detalle' in bloque or 'detalle' in bloque, 'no muestra el detalle del hallazgo'
