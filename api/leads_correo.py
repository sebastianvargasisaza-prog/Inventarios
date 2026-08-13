# -*- coding: utf-8 -*-
"""Los prospectos de maquila que llegan al correo de dirección.

Sebastián (13-ago): *"los leads llegan a mi correo direccion@animuslb.com y allí sólo llegan de
maquila porque los de Ánimus llegan a otro (...) la mayoría son formularios de la página web"*.

Eso resuelve la parte difícil sin una sola heurística: **el BUZÓN es el filtro**. No hay que
adivinar por el asunto ni por si el mensaje trae empresa -- meter la regla en el contenido es lo
que habría llenado de ruido el único lugar donde se mira quién falta, y un registro con ruido no
queda incompleto, queda FALSO (M144).

Cuatro decisiones que sostienen esto:

  · **No se le toca el correo.** Se lee con `BODY.PEEK[]`, así que nada queda marcado como leído
    ni se borra. Leer la bandeja de alguien no puede cambiársela.
  · **La llave de dedup es el `Message-ID`**, no el remitente ni el asunto. La misma persona
    escribe dos veces legítimamente y los formularios web repiten el asunto: deduplicar por eso
    pierde el segundo cliente en silencio (M127 lo pagó con los PQR, dedupeando por contacto).
  · **Lo que no se puede leer NO se inventa.** Si el formulario viene en un formato que no
    parseamos, la tarjeta se abre igual con remitente, asunto y fecha, y el crudo queda guardado
    -- perder el cliente es peor que tener la ficha incompleta, y con el crudo la pregunta "¿qué
    campo hay que mapear?" se LEE en vez de adivinarse.
  · **Presupuesto de reloj y corta-circuitos.** Es I/O de red dentro del hilo único del multi-cron:
    sin tope, un servidor lento congela todos los crons siguientes (M90/M92).
"""
import email as _email
import email.utils as _eutils
import imaplib
import logging
import os
import re
import time
from datetime import datetime, timedelta

log = logging.getLogger('leads_correo')

# El buzón de dirección es DISTINTO del de facturas (`IMAP_*`), así que lleva sus propias
# credenciales. Se cargan en Render: nunca viven en el código.
ENV_HOST = 'IMAP_LEADS_HOST'
ENV_USER = 'IMAP_LEADS_USER'
ENV_PASS = 'IMAP_LEADS_PASSWORD'
ENV_CARPETA = 'IMAP_LEADS_CARPETA'


def configurado():
    return all(os.environ.get(k, '').strip() for k in (ENV_HOST, ENV_USER, ENV_PASS))


def _hoy_col():
    return (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')


def _texto(msg):
    """El cuerpo en texto plano. Un HTML sin parte de texto se devuelve destildado a lo bruto:
    sirve para LEER qué llegó, que es para lo que se guarda."""
    cuerpo = ''
    try:
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                cuerpo = (part.get_payload(decode=True) or b'').decode('utf-8', 'replace')
                break
        if not cuerpo:
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    crudo = (part.get_payload(decode=True) or b'').decode('utf-8', 'replace')
                    cuerpo = re.sub(r'<[^>]+>', ' ', crudo)
                    break
    except Exception as e:
        log.warning('leads: no pude leer el cuerpo: %s', e)
    return re.sub(r'[ \t]+', ' ', cuerpo).strip()[:8000]


def _asunto(msg):
    try:
        from email.header import decode_header, make_header
        return str(make_header(decode_header(msg.get('Subject', '') or '')))[:300]
    except Exception:
        return (msg.get('Subject', '') or '')[:300]


# Los campos que mandan los formularios de la web. Se buscan por ETIQUETA, y lo que no aparece
# queda vacío -- rellenar adivinando le pone a un cliente el dato de otro (M19).
_CAMPOS = (
    ('empresa', r'(?:empresa|compa[nñ][ií]a|marca|negocio)\s*[:\-]\s*(.+)'),
    ('contacto', r'(?:nombre|contacto|nombre completo)\s*[:\-]\s*(.+)'),
    ('telefono', r'(?:tel[eé]fono|celular|whatsapp|phone)\s*[:\-]\s*(.+)'),
    ('email_form', r'(?:correo|e-?mail)\s*[:\-]\s*(.+)'),
    ('producto', r'(?:producto|categor[ií]a|qu[eé] necesita|servicio)\s*[:\-]\s*(.+)'),
    ('unidades', r'(?:unidades|cantidad|volumen)\s*[:\-]\s*(.+)'),
    ('mensaje', r'(?:mensaje|comentario|detalle|notas?)\s*[:\-]\s*(.+)'),
)

# ⚠ Lo que la gente escribe cuando TODAVIA NO SABE. El formulario real de la web trae
# `Empresa: Por definir` y `Unidades: no-se`, y eso NO es un dato: es la ausencia de uno.
#
# Tomarlo como razón social tiene una consecuencia que no se ve venir: las tarjetas del pipeline
# se funden por NOMBRE DE EMPRESA, así que **todos los formularios que digan "Por definir"
# colapsarían en una sola tarjeta** -- prospectos distintos mezclados en uno, en silencio, que es
# justo la forma de perderlos que este circuito viene a evitar.
_SIN_DATO = {
    'por definir', 'pordefinir', 'sin definir', 'a definir', 'por confirmar', 'por asignar',
    'no se', 'no-se', 'nose', 'no sé', 'no lo se', 'aun no', 'aún no', 'todavia no', 'todavía no',
    'n/a', 'na', 'no aplica', 'ninguna', 'ninguno', 'nada', 'pendiente', 'sin nombre',
    '-', '--', '---', '.', '..', 'x', 'xx', 'xxx', '?', '??', 'test',
}


def _es_vacio(v):
    """Un valor que dice "todavía no sé" cuenta como vacío, no como dato."""
    t = re.sub(r'[\s.]+$', '', str(v or '').strip().lower())
    return (not t) or t in _SIN_DATO


def parsear(asunto, cuerpo, remitente):
    """Lo que se pueda sacar del formulario. Lo que no, vacío y declarado."""
    out = {k: '' for k, _ in _CAMPOS}
    out['sin_definir'] = []
    texto = (asunto or '') + '\n' + (cuerpo or '')
    for clave, patron in _CAMPOS:
        m = re.search(patron, texto, re.I)
        if not m:
            continue
        val = m.group(1).strip()[:200]
        if _es_vacio(val):
            # Se DECLARA que el formulario lo trajo en blanco. No es lo mismo que no haberlo
            # preguntado, y quien mire la ficha tiene que poder distinguirlo (M124).
            out['sin_definir'].append(clave)
            continue
        out[clave] = val
    if not out['empresa']:
        # Sin empresa declarada, el nombre del contacto es lo único que identifica la tarjeta.
        # Se usa como rótulo, y se DICE que salió de ahí para que nadie lo lea como razón social.
        out['empresa'] = (out['contacto'] or _eutils.parseaddr(remitente or '')[0]
                          or _eutils.parseaddr(remitente or '')[1] or 'sin identificar')[:160]
        out['empresa_inferida'] = True
    else:
        out['empresa_inferida'] = False
    return out


def leer(app, limite=40, presupuesto_seg=45, dias=30):
    """Trae los correos nuevos del buzón y abre su tarjeta en el pipeline.

    Devuelve (ok, detalle, n). Idempotente por `Message-ID`.
    """
    if not configurado():
        return True, {'skipped': True,
                      'razon': 'faltan %s / %s / %s en Render' % (ENV_HOST, ENV_USER, ENV_PASS)}, 0
    host = os.environ[ENV_HOST].strip()
    usuario = os.environ[ENV_USER].strip()
    clave = os.environ[ENV_PASS].strip()
    carpeta = os.environ.get(ENV_CARPETA, 'INBOX').strip() or 'INBOX'
    t0 = time.monotonic()
    nuevos, vistos, fallos, ignorados = [], 0, 0, 0
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        # Los remitentes que ya se barrieron. El correo interno (Aseguramiento, RRHH, un
        # proveedor) vuelve a llegar todos los dias: sin esto el barrido hay que rehacerlo, y un
        # trabajo que se rehace a diario se deja de hacer -- y ahi el prospecto real queda
        # enterrado entre veinte correos internos, que es justo lo que esto viene a impedir.
        #
        # NO se saltean: se guardan igual, ya descartados y con motivo. Un filtro que bota sin
        # dejar rastro no se puede auditar ni revertir, y lo que bota podria ser un cliente.
        _ignorar = set()
        try:
            for (_co,) in c.execute(
                    "SELECT LOWER(TRIM(correo)) FROM leads_remitentes_ignorados").fetchall():
                if _co:
                    _ignorar.add(_co)
        except Exception as e:
            log.warning('leads: no pude leer la lista de ignorados: %s', e)
        try:
            imap = imaplib.IMAP4_SSL(host, timeout=25)
            imap.login(usuario, clave)
            imap.select(carpeta, readonly=True)   # readonly: la bandeja no se altera
            desde = (datetime.utcnow() - timedelta(days=int(dias))).strftime('%d-%b-%Y')
            _, data = imap.search(None, '(SINCE "%s")' % desde)
            ids = (data[0].split() if data and data[0] else [])[-int(limite):]
            for mid in reversed(ids):
                if time.monotonic() - t0 > presupuesto_seg:
                    log.info('leads: corto por presupuesto (%ss)', presupuesto_seg)
                    break
                if fallos >= 4:
                    log.warning('leads: corto por fallos seguidos del servidor')
                    break
                try:
                    # PEEK: no marca el mensaje como leido en la bandeja de Sebastian.
                    _, md = imap.fetch(mid, '(BODY.PEEK[])')
                except Exception as e:
                    fallos += 1
                    log.warning('leads: fallo al traer un mensaje: %s', e)
                    continue
                fallos = 0
                if not md or not md[0]:
                    continue
                msg = _email.message_from_bytes(md[0][1])
                msg_id = (msg.get('Message-ID') or '').strip()[:250]
                if not msg_id:
                    # Sin Message-ID no hay forma de deduplicar; se arma uno estable con lo que
                    # identifica al mensaje, en vez de descartarlo o de duplicarlo en cada corrida.
                    msg_id = 'sin-id:%s|%s' % ((msg.get('Date') or '')[:60], _asunto(msg)[:80])
                vistos += 1
                if c.execute("SELECT 1 FROM leads_correo WHERE message_id=?", (msg_id,)).fetchone():
                    continue
                remitente = (msg.get('From') or '')[:250]
                asunto = _asunto(msg)
                try:
                    fecha = _eutils.parsedate_to_datetime(msg.get('Date') or '')
                    fecha = fecha.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    fecha = _hoy_col()
                cuerpo = _texto(msg)
                datos = parsear(asunto, cuerpo, remitente)
                _ign = any(x in remitente.lower() for x in _ignorar)
                if _ign:
                    ignorados += 1
                c.execute(
                    """INSERT INTO leads_correo
                         (message_id, remitente, asunto, fecha_correo, cuerpo, empresa,
                          contacto, telefono, email_contacto, producto, empresa_inferida,
                          descartado, motivo_descarte, creado_en)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (msg_id, remitente, asunto, fecha, cuerpo, datos['empresa'],
                     datos['contacto'], datos['telefono'],
                     datos['email_form'] or _eutils.parseaddr(remitente)[1],
                     datos['producto'], 1 if datos['empresa_inferida'] else 0,
                     1 if _ign else 0,
                     'remitente en la lista de ignorados' if _ign else '',
                     _hoy_col()))
                lid = c.lastrowid
                if not _ign:
                    nuevos.append({'id': lid, 'empresa': datos['empresa'], 'asunto': asunto,
                                   'fecha': fecha, 'inferida': datos['empresa_inferida']})
            try:
                imap.close()
            except Exception:
                pass
            imap.logout()
        except Exception as e:
            conn.rollback()
            log.warning('leads: no pude leer el buzon: %s', e)
            return False, {'error': str(e)[:200]}, 0
        conn.commit()
    return True, {'vistos': vistos, 'nuevos': nuevos, 'ignorados': ignorados, 'segundos': round(time.monotonic() - t0, 1)}, \
        len(nuevos)
