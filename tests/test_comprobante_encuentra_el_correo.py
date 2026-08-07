# -*- coding: utf-8 -*-
"""El comprobante encuentra el correo del creador por la MISMA fuente que la pantalla.

Sebastián (7-ago), con la tarjeta a la vista: *"marketing pone correos, todos los que me llegan
ya tienen, mira que esté usando ese"*. Y tenía razón: el creador **tiene** correo -- la bandeja
lo muestra -- y el comprobante igual no salía. Yo venía repitiendo que el problema eran los
creadores sin correo; era falso, y la memoria estaba desactualizada.

Son **dos caminos distintos para el mismo hecho** (M1, otra vez):

| quién | de dónde saca el correo |
|---|---|
| la BANDEJA del Centro de Mando | `pagos_influencers.influencer_id` → por eso se ve en la tarjeta |
| el PAGO (`pagar_oc`) | `solicitudes_compra.influencer_id` |

Si la SOL no quedó ligada al creador, el correo se pierde **aunque la pantalla lo esté
mostrando** (M115: el dato existe y se pierde a mitad de camino). Y encima todo el bloque estaba
gateado por la CATEGORÍA de la OC ('influencer'/'marketing'): con otra categoría ni siquiera
miraba.

El arreglo es el de siempre: preguntarle a la misma fuente que ve el usuario. Si hay una fila en
`pagos_influencers` para esa OC, eso YA dice que es un pago a creador -- no hace falta adivinarlo
por el texto de una categoría.
"""
import io
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OC = 'OC-ZZMAIL-1'
MAIL = 'zzcreador@ejemplo.com'


def _cli(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app):
    """Una OC de creador CON correo en su ficha y SIN el vínculo por solicitud.

    Ese es exactamente el caso que se rompía: la tarjeta muestra el correo (lo saca de
    `pagos_influencers`) y el pago no lo encontraba.
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM pagos_influencers WHERE numero_oc=?", (OC,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        c.execute("DELETE FROM marketing_influencers WHERE nombre='ZZ CREADOR MAIL'")
        c.execute("INSERT INTO marketing_influencers (nombre, email, estado) "
                  "VALUES (?,?,?)", ('ZZ CREADOR MAIL', MAIL, 'Activo'))
        iid = c.lastrowid
        c.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                  " valor_total, creado_por) VALUES (?,?,?,?,?,?,?)",
                  (OC, 'ZZ CREADOR MAIL', 'Autorizada', 'Servicios', '2026-08-07', 250000, 'zz'))
        c.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, "
                  " fecha, estado, numero_oc) VALUES (?,?,?,?,?,?)",
                  (iid, 'ZZ CREADOR MAIL', 250000, '2026-08-07', 'Pendiente', OC))
        conn.commit()
    return iid


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM pagos_influencers WHERE numero_oc=?", (OC,))
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        conn.execute("DELETE FROM marketing_influencers WHERE nombre='ZZ CREADOR MAIL'")
        conn.commit()


def test_encuentra_el_correo_aunque_la_SOL_no_lo_tenga(app, db_clean):
    """El caso real de la captura: el creador tiene correo, la tarjeta lo muestra, y el
    comprobante salía sin destinatario."""
    _sembrar(app)
    r = _cli(app).patch('/api/ordenes-compra/%s/pagar' % OC, headers=csrf_headers(),
                        json={'monto': 250000, 'medio': 'Transferencia',
                              'numero_transaccion': 'ZZ-REF-1'})
    assert r.status_code == 200, r.data[:400]
    cp = (r.get_json() or {}).get('comprobante') or {}
    destino = cp.get('email_encolado_a') or cp.get('email_enviado_a') or ''
    pend = str(cp.get('email_pendiente') or '')
    # ⚠ En el entorno de pruebas NO hay SMTP, así que el envío no se encola igual. Lo que este
    # test mide es que el correo se HAYA RESUELTO: si el motivo pendiente dice "sin email", el
    # beneficiario quedó sin destinatario -- que es el bug. Si dice "SMTP", el correo se
    # encontró y sólo falta la configuración (que en producción SÍ está · verificado en
    # `/api/email-status` el 7-ago).
    assert 'sin email' not in pend.lower(), (
        'el comprobante NO encontró el correo del creador aunque su ficha lo tiene · %s' % cp)
    assert destino == MAIL or 'SMTP' in pend, (
        'ni encoló el envío ni explicó por qué · %s' % cp)
    _limpiar(app)


def test_la_categoria_de_la_OC_ya_no_decide(app, db_clean):
    """La OC sembrada tiene categoría 'Servicios', no 'Influencer'. Antes eso bastaba para que
    ni siquiera buscara el creador -- un texto libre decidiendo si sale un comprobante."""
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    # ⚠ Anclado al comentario ÚNICO del bloque: `FROM pagos_influencers pi` aparece ANTES en
    # el archivo, en otra consulta, y el test terminaba midiendo código ajeno (M151).
    i = s.find('# ── El MISMO camino que usa la pantalla')
    assert i > 0, 'no existe la búsqueda de respaldo por pagos_influencers'
    # el respaldo va FUERA del if de la categoría · si quedara adentro, una OC con otra
    # categoría seguiría sin buscar al creador
    bloque = s[i:i + 1800]
    assert 'if not (beneficiario.get(' in bloque, (
        'la búsqueda por pagos_influencers no es un respaldo del camino anterior')
    assert "if not ('influencer' in cat_lower or 'marketing' in cat_lower):" in s, (
        'la rama de proveedor regular dejó de ser el complemento del gate de categoría')


def test_NO_pisa_un_correo_que_ya_se_habia_resuelto(app, db_clean):
    """El respaldo sólo entra si el camino de siempre no encontró correo · si pisara, un cambio
    en la ficha del creador cambiaría el destinatario de un pago ya resuelto."""
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    i = s.find('# ── El MISMO camino que usa la pantalla')
    assert i > 0, 'desapareció el respaldo'
    bloque = s[i:i + 1800]
    assert re.search(r"if not \(beneficiario\.get\('email'\) or ''\)\.strip\(\)", bloque), (
        'el respaldo corre siempre · debería entrar sólo cuando falta el correo')


def test_el_fallo_del_respaldo_NO_es_mudo(app, db_clean):
    """Sin aviso, el comprobante sale sin destinatario y nadie se entera de por qué (M4)."""
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    i = s.find('no pude resolver el creador de')
    assert i > 0, 'el fallo del respaldo se traga en silencio'
