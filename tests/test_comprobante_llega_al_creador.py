# -*- coding: utf-8 -*-
"""Al pagarle a un creador, el comprobante SALE · y si no sale, se dice.

Sebastián: *"aquí ya viene correo, la idea es que le doy pagar y le llega al influencer a su
correo la cuenta paga · ¿eso existe? sí, sí, revisemos qué sale, qué les llega a ellos"*.

**Existe y está bien construido**: al pagar se genera un comprobante de egreso (PDF con subtotal,
IVA, retefuente, reteica y total) y se le envía al creador. Pero tiene DOS condiciones -- que el
creador tenga correo guardado y que haya SMTP configurado -- y hasta hoy, cuando fallaban, fallaba
**callado**: el endpoint devolvía `email_pendiente` con el motivo y la pantalla lo tiraba a la
basura. Se pagaba creyendo que el comprobante había salido.

⚠ Medido en el snapshot local: **0 de 17 creadores tienen correo**. O sea que el comprobante no le
llegaba a nadie -- una capacidad que no alcanza a nadie no existe (M121). Verificar el número real
en producción; la forma del hueco es la misma.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _js():
    import templates_py.centro_operaciones_html as C
    return re.sub(r'//[^\n]*', '', getattr(C, 'HTML', ''))


def test_avisa_ANTES_si_el_creador_no_tiene_correo(app, db_clean):
    """Es el único momento en que todavía se puede cargar el correo y que el comprobante salga."""
    js = _js()
    i = js.find('async function pagarDesdeBandeja')
    assert i > 0
    bloque = js[i:i + 1800]
    j = bloque.find('confirm(txt)')
    assert j > 0
    antes = bloque[:j]
    assert 'p.email' in antes, 'no mira si el creador tiene correo antes de pagar'
    assert 'comprobante' in antes.lower(), 'no dice QUÉ es lo que no va a salir'


def test_dice_DESPUES_si_el_comprobante_salio(app, db_clean):
    """Un pago sin comprobante se veía idéntico a uno con comprobante (M100)."""
    js = _js()
    i = js.find('async function pagarDesdeBandeja')
    bloque = js[i:i + 2600]
    assert 'js.comprobante' in bloque, 'la pantalla ignora lo que el endpoint responde'
    assert 'email_enviado_a' in bloque, 'no confirma cuando SÍ salió'
    assert 'email_pendiente' in bloque, 'no avisa cuando NO salió'


def test_la_bandeja_TRAE_el_correo(app, db_clean):
    """Sin el dato en la bandeja, el aviso previo sería imposible."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/hub.py'), encoding='utf-8').read()
    i = src.find('def _pagos_influencer_pendientes')
    bloque = src[i:i + 3000]
    assert "mi.email" in bloque, 'la bandeja no trae el correo del creador'


def test_el_endpoint_DECLARA_por_que_no_envio(app, db_clean):
    """El motivo tiene que ser accionable: decir 'no se envió' sin decir por qué no sirve."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'), encoding='utf-8').read()
    i = src.find('def pagar_oc')
    j = src.find('\n@bp.route', i)
    c = src[i:j]
    assert 'email_pendiente' in c, 'el endpoint no declara cuando no envía'
    assert 'sin email' in c, 'no dice que falta el correo del beneficiario'
    assert 'SMTP no configurado' in c, 'no distingue el caso de SMTP sin configurar'
    # ⚠ Decía `email_enviado_a` y se renombró a `email_encolado_a` A PROPÓSITO (7-ago):
    # `enviar_en_background` vuelve enseguida, así que en ese punto el correo está ENCOLADO,
    # no entregado -- el SMTP puede fallar después (dirección mal escrita, Gmail rechazando).
    # Afirmar "enviado" ahí hace que nadie revise un comprobante que nunca salió (M100/M115).
    # La invariante que este test protege sigue viva: el endpoint dice A QUIÉN va.
    assert 'email_encolado_a' in c, 'no dice a quién va el comprobante'
    assert 'email_estado' in c, 'no distingue "va en camino" de "llegó"'


def test_el_comprobante_se_manda_SOLO_con_correo_valido(app, db_clean):
    """Mandar a una cadena sin `@` es un rebote silencioso que nadie ve."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'), encoding='utf-8').read()
    i = src.find('email_dest = ')
    bloque = src[i:i + 260]
    assert "'@' in email_dest" in bloque, 'no valida que el correo tenga arroba'


def test_el_correo_lleva_el_PDF_y_el_desglose(app, db_clean):
    """Lo que el creador necesita es el soporte formal, no un aviso de que le pagaron."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'notificaciones.py'), encoding='utf-8').read()
    i = src.find('def enviar_comprobante_egreso')
    assert i > 0, 'no existe el envío del comprobante'
    bloque = src[i:i + 3000]
    assert 'pdf_bytes' in bloque, 'no adjunta el PDF'
    assert 'Comprobante de pago' in bloque, 'el asunto no dice qué es'
    assert 'retenciones' in bloque.lower(), 'no menciona el desglose de retenciones'
