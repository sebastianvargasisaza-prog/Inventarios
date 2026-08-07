# -*- coding: utf-8 -*-
"""El "¿alcanza la MP?" no promete material que el descuento va a rechazar.

`disponibilidad_para_kg` (el modal Programar) delega en `_get_mp_stock`, que excluye por
`estado_lote` y **no mira `fecha_vencimiento`**. El FEFO que descuenta de verdad excluye ADEMÁS
por fecha, con el ancla Colombia (la guarda M25).

⇒ Un lote vencido ayer que el cron `job_marcar_vencidos` (7:50) todavía no marcó **contaba para
la pantalla y el FEFO lo rechaza**: decía "alcanza" y después el descuento no encontraba
material. Ventana de hasta 24 horas, o indefinida si el cron falla.

Es M5 en el sitio donde más cuesta: el número que se MUESTRA para decidir si se programa tiene
que ser el mismo que DECIDE al descontar.

⚠ El arreglo va en la factibilidad y **no** en `_get_mp_stock`: M25 dice que las vistas de bodega
se anclan en `estado_lote` (fuente única que el cron alinea) y que la defensa por fecha va sólo
en los caminos de CONSUMO. Tocar el helper canónico cambiaría decenas de pantallas de golpe.

⚠ Y lo que se excluye se ENUMERA (M124): el gramaje vencido va aparte, para que el operario
entienda por qué bajó el disponible en vez de leerlo como un error.
"""
import uuid

COD = 'MP00050'


def _sembrar(app, vence):
    """Un lote VIGENTE (el cron no lo marcó) con la fecha de vencimiento que se pida."""
    from database import get_db
    lote = 'ZZVEN-' + uuid.uuid4().hex[:6].upper()
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos WHERE lote LIKE 'ZZVEN-%'")
        c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                  " fecha, estado_lote, fecha_vencimiento) "
                  "VALUES (?,?, 'Entrada', ?, ?, '2026-08-01', 'VIGENTE', ?)",
                  (COD, 'ZZ MATERIAL', 900000, lote, vence))
        conn.commit()
    return lote


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM movimientos WHERE lote LIKE 'ZZVEN-%'")
        conn.commit()


def _disp(app, producto, kg):
    from database import get_db
    from blueprints.plan import disponibilidad_para_kg
    with app.app_context():
        return disponibilidad_para_kg(get_db(), producto, kg)


def _item(d, cod=COD):
    for it in (d.get('mp') or {}).get('items') or []:
        if (it.get('codigo') or '').strip().upper() == cod.upper():
            return it
    return None


def _producto_con(app, cod):
    """Un producto cuya fórmula activa use ese material · si no hay, el test no mide nada."""
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT fi.producto_nombre FROM formula_items fi "
            " JOIN formula_headers fh ON UPPER(TRIM(fh.producto_nombre))=UPPER(TRIM(fi.producto_nombre)) "
            "WHERE fi.material_id=? AND COALESCE(fh.activo,1)=1 AND COALESCE(fi.porcentaje,0)>0 "
            "LIMIT 1", (cod,)).fetchone()
    return r[0] if r else None


def test_un_lote_VENCIDO_que_el_cron_no_marco_no_cuenta_como_disponible(app, db_clean):
    prod = _producto_con(app, COD)
    if not prod:
        import pytest
        pytest.skip('ninguna fórmula activa usa %s · el test no mediría nada (M152)' % COD)

    _sembrar(app, '2026-08-01')          # vencio hace dias, sigue VIGENTE en el kardex
    d = _disp(app, prod, 1)
    it = _item(d)
    assert it, 'el material no salió en la factibilidad'
    assert (it.get('vencido_sin_marcar_g') or 0) > 0, (
        'no detectó el lote vencido por fecha · la pantalla sigue prometiendo material que el '
        'FEFO va a rechazar')
    venc = float(it['vencido_sin_marcar_g'])
    _limpiar(app)

    # el MISMO lote, pero vigente de verdad: tiene que contar
    _sembrar(app, '2030-01-01')
    d2 = _disp(app, prod, 1)
    it2 = _item(d2)
    assert (it2.get('vencido_sin_marcar_g') or 0) == 0, 'marcó como vencido uno que no lo está'
    assert float(it2['disponible_g']) - float(it['disponible_g']) >= venc - 1, (
        'el disponible no bajó al descontar lo vencido · %s vs %s'
        % (it2['disponible_g'], it['disponible_g']))
    _limpiar(app)


def test_lo_excluido_se_ENUMERA(app, db_clean):
    """Un total que deja cosas afuera sin nombrarlas se lee como un faltante, y es lo que hace
    que nadie entienda por qué no cuadra (M124)."""
    prod = _producto_con(app, COD)
    if not prod:
        import pytest
        pytest.skip('sin fórmula que use %s' % COD)
    _sembrar(app, '2026-08-01')
    d = _disp(app, prod, 1)
    excluye = (d.get('mp') or {}).get('excluye') or []
    assert any('vencido por fecha' in str(x) for x in excluye), (
        'descontó material sin decir por qué · %s' % excluye)
    assert 'vencido_sin_marcar_g' in (d.get('mp') or {}), 'no informa cuánto se dejó afuera'
    _limpiar(app)


def test_usa_el_MISMO_ancla_de_fecha_que_el_FEFO(app):
    """Si la factibilidad usara el `now()` del servidor (UTC) y el FEFO el ancla Colombia, de
    noche volverían a decir cosas distintas (M24)."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'plan.py'), encoding='utf-8').read()
    i = s.find('venc_por_fecha = {}')
    assert i > 0, 'desapareció la medición'
    bloque = s[i:i + 2200]
    assert "date('now','-5 hours')" in bloque, (
        'no usa el ancla Colombia · de noche la pantalla y el descuento discreparían')


def test_si_NO_se_pudo_medir_se_DECLARA(app):
    """Un cero inventado se lee como "no hay nada vencido" y significa lo contrario, "no se
    miró" (M100)."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'plan.py'), encoding='utf-8').read()
    i = s.find('venc_por_fecha = None')
    assert i > 0, 'el fallo se traga en silencio'
    assert 'no se pudo verificar el vencimiento' in s, 'no lo dice en la respuesta'


def test_NO_se_toco_el_helper_canonico_de_stock(app):
    """Guard de la decisión: la defensa por fecha va en el camino de CONSUMO, no en la vista de
    bodega. Meterla en `_get_mp_stock` cambiaría decenas de pantallas de golpe (M25)."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'programacion.py'), encoding='utf-8').read()
    i = s.find('def _get_mp_stock')
    j = s.find('\ndef ', i + 10)
    cuerpo = re.sub(r'^\s*#[^\n]*$', '', s[i:j], flags=re.M)
    assert 'fecha_vencimiento' not in cuerpo, (
        'el helper canónico de stock empezó a filtrar por fecha · eso cambia TODAS las vistas '
        'de bodega, no sólo la factibilidad')
