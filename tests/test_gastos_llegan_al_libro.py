# -*- coding: utf-8 -*-
"""Dos gastos que se repiten todos los meses y no llegaban al libro central.

Sebastián (6-ago): *"todo lo que sea plata se debe ver reflejado allí"*.

1. **Marcación de envases** (serigrafía/tampografía · `ordenes_servicio.costo_real_cop`): se
   guardaba el costo real al entregar la orden y ahí moría. El gasto del mes salía corto justo
   en un rubro recurrente.
2. **Publicidad** (`marketing_ads_campaigns.spend_total`): plata que Meta cobra y que no
   aparecía en una sola línea de Tesorería.

Los dos se espejan con el MISMO patrón, y la diferencia con un pago normal importa: ninguno de
los dos es un evento de pago único, así que la fila del libro se **actualiza** (referencia = la
orden / la campaña) en vez de insertar una nueva cada vez que el dato se refresca. Si se
insertara, cada sync de Meta sumaría el acumulado otra vez -- y un gasto inflado no da ningún
síntoma: nadie sospecha de un número de más (M148).
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fuente(mod):
    return io.open(os.path.join(RAIZ, 'api', 'blueprints', mod), encoding='utf-8').read()


def _sin_comentarios(s):
    """Si no, estos tests encuentran la prosa que explica el espejo, no el espejo (M154)."""
    return re.sub(r'^\s*#[^\n]*$', '', s, flags=re.M)


def test_el_costo_de_marcacion_llega_al_libro(app, db_clean):
    """De punta a punta: entregar una OS con costo real deja su egreso en Tesorería."""
    from database import get_db
    from .conftest import TEST_PASSWORD, csrf_headers
    cli = app.test_client()
    r = cli.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
                 headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302

    numero = 'OS-ZZLIB-001'
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM ordenes_servicio WHERE numero_os=?", (numero,))
        c.execute("DELETE FROM flujo_egresos WHERE referencia=?", ('OS-%s' % numero,))
        c.execute("INSERT INTO ordenes_servicio (numero_os, proveedor, tipo_servicio, estado, "
                  " cantidad_unidades, creado_por, fecha_solicitud) VALUES (?,?,?,?,?,?,?)",
                  (numero, 'Serigrafias del Valle', 'Serigrafia', 'En proceso', 0, 'zz',
                   '2026-08-04'))
        conn.commit()

    r = cli.patch('/api/compras/ordenes-servicio/%s/estado' % numero, headers=csrf_headers(),
                  json={'estado_nuevo': 'Entregada', 'costo_real_cop': 480000})
    assert r.status_code in (200, 201), r.data[:300]

    with app.app_context():
        filas = get_db().execute(
            "SELECT monto, categoria FROM flujo_egresos WHERE fuente='marcacion' AND referencia=?",
            ('OS-%s' % numero,)).fetchall()
    assert len(filas) == 1, 'el costo de la marcación no llegó al libro (%s filas)' % len(filas)
    assert float(filas[0][0]) == 480000

    # Un segundo intento NO puede duplicar el gasto. Acá lo frena la máquina de estados
    # (`Entregada → Entregada` no está permitida), así que el `UPDATE` del espejo es defensa en
    # profundidad y no el camino normal -- lo digo explícito para que nadie lea este test como
    # prueba de que la actualización se ejercita.
    r2 = cli.patch('/api/compras/ordenes-servicio/%s/estado' % numero, headers=csrf_headers(),
                   json={'estado_nuevo': 'Entregada', 'costo_real_cop': 500000})
    assert r2.status_code == 409, 'la máquina de estados dejó re-entregar · %s' % r2.data[:200]
    with app.app_context():
        filas = get_db().execute(
            "SELECT monto FROM flujo_egresos WHERE fuente='marcacion' AND referencia=?",
            ('OS-%s' % numero,)).fetchall()
        get_db().execute("DELETE FROM ordenes_servicio WHERE numero_os=?", (numero,))
        get_db().execute("DELETE FROM flujo_egresos WHERE referencia=?", ('OS-%s' % numero,))
        get_db().commit()
    assert len(filas) == 1, 'el costo se duplicó al re-guardarlo'


def test_el_gasto_de_publicidad_se_ACTUALIZA_y_no_se_acumula(app):
    """`spend_total` es el acumulado de la campaña, no un pago. Si el espejo insertara en cada
    sync, el gasto crecería solo hasta el infinito."""
    s = _sin_comentarios(_fuente('marketing.py'))
    i = s.find("'ADS-meta-%s' % cid")
    assert i > 0, 'no existe el espejo del gasto publicitario'
    bloque = s[i:i + 1400]
    assert 'UPDATE flujo_egresos' in bloque, (
        'el espejo de ads sólo INSERTA · cada sync volvería a sumar el acumulado')
    assert "fuente='ads'" in bloque, 'sin fuente propia no se puede distinguir ni reconciliar'


def test_los_dos_espejos_NUNCA_tumban_la_operacion(app):
    """Un espejo que falla no puede impedir entregar una orden ni sincronizar campañas -- pero
    tampoco puede fallar en silencio, que es como se pierde plata sin enterarse (M4)."""
    for mod, marca in (('compras.py', 'OS-%s'), ('marketing.py', "'ADS-meta-%s' % cid")):
        s = _sin_comentarios(_fuente(mod))
        i = s.find(marca if mod == 'marketing.py' else "_ref_os = 'OS-%s' % numero_os")
        assert i > 0, 'no encuentro el espejo en %s' % mod
        bloque = s[i:i + 2200]
        assert 'log.warning' in bloque, (
            '%s: el espejo falla en silencio · un except mudo convierte plata perdida en '
            '"no hay datos"' % mod)
