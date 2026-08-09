# -*- coding: utf-8 -*-
"""Dos códigos para la misma tapa: uno lleva el tamaño y el otro no.

Sebastián (9-ago), mirando el desplegable: *"veo que existen dos tapas para envase cuadrado, creo
que debemos normalizar a solo una"*. Eran `MEE-TAP-003 · TAPA ENVASE CUADRADO` y
`TAP-TAPA-ENVASE-CUADRADO-30ML15ML · TAPA ENVASE CUADRADO 30ml/15ml`.

El agrupador de duplicados compara el nombre normalizado COMPLETO, así que nunca los vio juntos y
los dos siguen vivos en la lista. El daño no es cosmético: si un producto se carga con uno y otro
con el otro, **el stock de esa tapa queda partido en dos** y ninguna muestra la necesidad real
(M57/M100).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _sembrar(app, filas):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'DUPT-%'")
        for cod, desc, cat in filas:
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, "
                      "estado) VALUES (?,?,?,0,'Activo')", (cod, desc, cat))
        c.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'DUPT-%'")
        c.commit()


def _grupos(admin_client, prefijo='DUPT-'):
    r = admin_client.get('/api/admin/maestro-envases-diff')
    assert r.status_code == 200, r.data[:200]
    return [g for g in (r.get_json().get('posibles_duplicados') or [])
            if any(str(x['codigo']).startswith(prefijo) for x in g['codigos'])]


def test_encuentra_el_par_donde_uno_NO_lleva_tamano(app, admin_client):
    _sembrar(app, [('DUPT-A', 'TAPA ENVASE CUADRADO', 'Tapa'),
                   ('DUPT-B', 'TAPA ENVASE CUADRADO 30ml/15ml', 'Tapa')])
    g = _grupos(admin_client)
    assert g, 'no vio el par que Sebastián encontró a ojo'
    assert {x['codigo'] for x in g[0]['codigos']} == {'DUPT-A', 'DUPT-B'}
    assert g[0]['canonico_sugerido'], 'no sugiere cuál dejar'
    _limpiar(app)


def test_NO_marca_dos_TAMANOS_distintos(app, admin_client):
    """`FR-BLANCOCUAD-30` y `FR-BLANCOCUAD-15` son dos frascos, no el mismo mal cargado.

    Sin esta regla el detector marcaba 3 de 4 mal (medido), y un detector que grita sobre lo
    legítimo deja de mirarse justo donde tiene que dar confianza (M122).
    """
    _sembrar(app, [('DUPT-30', 'FRASCO BLANCO CUADRADO 30ml', 'Frasco'),
                   ('DUPT-15', 'FRASCO BLANCO CUADRADO 15ml', 'Frasco')])
    assert not _grupos(admin_client), 'marcó como duplicados dos tamaños distintos'
    _limpiar(app)


def test_si_el_SIN_TAMANO_tiene_VARIOS_enfrente_no_elige(app, admin_client):
    """Con un `TAPA X` y dos tamaños distintos no hay forma de saber a cuál corresponde: se
    muestra el grupo y no se propone canónico (M19)."""
    _sembrar(app, [('DUPT-N', 'TAPA PATO BLANCA', 'Tapa'),
                   ('DUPT-1', 'TAPA PATO BLANCA 120ml', 'Tapa'),
                   ('DUPT-2', 'TAPA PATO BLANCA 60ml', 'Tapa')])
    g = _grupos(admin_client)
    assert g, 'no mostró el grupo'
    assert g[0]['ambiguo'] is True, 'no marcó la ambigüedad'
    assert not g[0]['canonico_sugerido'], 'eligió uno con dos tamaños enfrente'
    _limpiar(app)
