# -*- coding: utf-8 -*-
"""Mismo INCI + otro GRADO no es el mismo material, y no se sustituye.

Sebastián 22-ago, mirando los hialurónicos: *"los cuenta juntos pero son de pesos diferentes,
esto resuélvelo, debe estar diferente"*.

El nivel 2b del resolver busca otros códigos activos con el mismo INCI y redirige al de más
stock. Comparaba con `_norm_mp_name`, que **borra el paréntesis** -- justo donde vive el grado:
`HYALURONIC ACID (300 kD)` y `(50 kD)` caían en la misma clave.

Medido sobre los 169 materiales activos con INCI:

  · **CENTELLA ASIATICA EXTRACT** -- `(triterpenos 80%)` y el extracto plano -- son **DOS**
    códigos, y el guard de ambigüedad exige MÁS DE DOS para bloquear: **hoy se intercambian**.
    El % de fórmula cambia con el grado, así que mezclarlos es potencia equivocada (M19).
  · **HYALURONIC ACID** son TRES (1500/300/50 kD), así que el guard sí dispara: estaban
    protegidos por casualidad, no por diseño.

Este archivo fija lo que importa: **el grado decide, no cuántos códigos haya.**
"""
import pytest

BASE = 'ACIDO DE PRUEBA GRADO'
COD_A = 'MPGRADOA'      # (grado alto)  · SIN stock
COD_B = 'MPGRADOB'      # (grado bajo)  · CON stock
COD_DUP1 = 'MPDUPINCI1'  # INCI identico · SIN stock
COD_DUP2 = 'MPDUPINCI2'  # INCI identico · CON stock


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        for cod in (COD_A, COD_B, COD_DUP1, COD_DUP2):
            c.execute("DELETE FROM movimientos WHERE material_id=?", (cod,))
            c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        c.commit()


@pytest.fixture()
def dos_grados(app):
    """El caso de la Centella: DOS códigos, mismo INCI base, grado distinto.

    Sólo el de grado bajo tiene stock. Sin el arreglo, pedir el de grado alto redirigía al
    otro -- que es fabricar con otra potencia.
    """
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                  "VALUES (?,?,?,1)", (COD_A, BASE + ' (triterpenos 80%)', BASE + ' 80'))
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                  "VALUES (?,?,?,1)", (COD_B, BASE, BASE + ' plano'))
        # sólo el B tiene material en bodega
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote) "
            "VALUES (?,?,'Entrada',5000.0,'L-GRADO-B',?,?,?,'VIGENTE')",
            (COD_B, BASE, '2026-08-01 08:00:00', 'test', 'EST-GRADO'))
        c.commit()
    yield
    _limpiar(app)


@pytest.fixture()
def duplicado_legitimo(app):
    """El otro lado: MISMO material bajo dos códigos, INCI IDÉNTICO.

    Ahí redirigir es lo correcto y tiene que seguir funcionando, o el arreglo rompería los
    duplicados legítimos (tipo PANTHENOL).
    """
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                  "VALUES (?,?,?,1)", (COD_DUP1, BASE + ' UNICO', BASE + ' viejo'))
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                  "VALUES (?,?,?,1)", (COD_DUP2, BASE + ' unico', BASE + ' nuevo'))
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, estado_lote) "
            "VALUES (?,?,'Entrada',5000.0,'L-DUP',?,?,?,'VIGENTE')",
            (COD_DUP2, BASE, '2026-08-01 08:00:00', 'test', 'EST-GRADO'))
        c.commit()
    yield
    _limpiar(app)


def _resolver(app, cod, nombre=''):
    from database import get_db
    from blueprints.programacion import _resolver_material_bodega
    with app.app_context():
        return _resolver_material_bodega(get_db().cursor(), cod, nombre)


# ─────────────────────────────────────────────────────────────────────────────
# el grado NO se sustituye, y no depende de cuantos codigos haya
# ─────────────────────────────────────────────────────────────────────────────

def test_un_grado_NO_se_reemplaza_por_otro(app, dos_grados):
    """El corazón: pedir el de triterpenos 80% no puede devolver el extracto plano."""
    r = _resolver(app, COD_A, BASE)
    assert r != COD_B, (
        'el resolver cambio un grado por otro: pidieron %s y devolvio %s · misma dosis, '
        'otra potencia (M19)' % (COD_A, COD_B))


def test_el_comparador_conserva_el_GRADO(app):
    from blueprints.programacion import _inci_con_grado as g
    assert g('HYALURONIC ACID (300 kD)') != g('HYALURONIC ACID (50 kD)'), (
        'dos pesos moleculares distintos caen en la misma clave')
    assert g('CENTELLA ASIATICA EXTRACT (triterpenos 80%)') != g('CENTELLA ASIATICA EXTRACT'), (
        'el extracto con grado y el plano caen en la misma clave')
    # Y lo que SI tiene que colapsar: mayusculas y espacios.
    assert g('PANTHENOL') == g('  panthenol '), 'no colapsa mayusculas y espacios'
    assert g('HYALURONIC ACID (300 kD)') == g('Hyaluronic Acid (300 kd)')


def test_el_normalizador_CANONICO_no_se_toco(app):
    """`_norm_mp_name` lo usa medio sistema para matchear por nombre: cambiarlo moveria todos
    los matches a la vez (M45). El grado sólo importa donde se decide un REEMPLAZO."""
    from blueprints.programacion import _norm_mp_name as n
    assert n('HYALURONIC ACID (300 kD)') == n('HYALURONIC ACID (50 kD)'), (
        'se cambio el normalizador canonico: eso tiene un radio mucho mayor que este arreglo')


# ─────────────────────────────────────────────────────────────────────────────
# el borde: el duplicado LEGITIMO tiene que seguir resolviendo
# ─────────────────────────────────────────────────────────────────────────────

def test_el_duplicado_con_INCI_IDENTICO_sigue_resolviendo(app, duplicado_legitimo):
    """Si el arreglo rompiera esto, un material con dos códigos dejaría de encontrar su stock
    y produccion diria 'no hay' con el material en el estante."""
    r = _resolver(app, COD_DUP1, BASE)
    assert r == COD_DUP2, (
        'el duplicado legitimo dejo de resolver: pidieron %s, hay stock en %s, devolvio %s'
        % (COD_DUP1, COD_DUP2, r))
