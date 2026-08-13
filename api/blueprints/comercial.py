"""Blueprint Comercial — Pipeline Maquila B2B + EOS Leads.

Sebastian (30-abr-2026):
  - Maquila: JGB SA pidio Full Service 29 abr, NDA firmado mismo dia.
    Fernando Mesa unico activo, ERLENMEYER cliente. Pipeline para no
    perder otro JGB.
  - EOS Leads: webhook web3forms desde landing eossuite.com → tabla
    eos_leads → notif al owner.
"""
from flask import Blueprint, jsonify, request, session, Response, redirect
import json
import os
import hmac
import hashlib
import logging
import time
from datetime import date
from database import get_db
from config import ADMIN_USERS, ESPAGIRIA_ACCESS

logger = logging.getLogger(__name__)
log = logger
bp = Blueprint('comercial', __name__)


# ─── Rate limiter en memoria por IP ────────────────────────────────────────
# Audit zero-error 2-may-2026: webhook público sin rate limit permitía
# inundar la BD con leads falsos. 5 req/min/IP es suficiente para web3forms
# (1 lead esperado por sumisión humana) y bloquea bots.
_RATE_BUCKETS = {}  # ip → [timestamps]


def _rate_limit_check_mem(ip: str, max_req: int = 5, window: int = 60) -> bool:
    """Limiter en memoria (fallback). True si la IP excedió el límite."""
    now = time.time()
    bucket = _RATE_BUCKETS.setdefault(ip, [])
    # Limpiar entradas viejas
    bucket[:] = [t for t in bucket if (now - t) < window]
    if len(bucket) >= max_req:
        return True
    bucket.append(now)
    return False


def _rate_limit_check(ip: str, max_req: int = 5, window: int = 60) -> bool:
    """Retorna True si la IP excedió el límite (debe rechazarse).

    Audit ronda2 29-may-2026: con 3 workers gunicorn el dict en memoria daba
    3× el límite real. Usa la tabla rate_limit_hits (mig 202) para contar por
    ventana deslizante compartida entre workers. Deploy-safe: si la tabla aún
    no existe en PG (mig sin aplicar) o falla, cae al limiter en memoria.
    """
    try:
        now = time.time()
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM rate_limit_hits WHERE ts < ?", (now - window,))
        n = c.execute("SELECT COUNT(*) FROM rate_limit_hits WHERE clave=?", (ip,)).fetchone()[0]
        if n >= max_req:
            conn.commit()
            return True
        c.execute("INSERT INTO rate_limit_hits (clave, ts) VALUES (?, ?)", (ip, now))
        conn.commit()
        return False
    except Exception:
        return _rate_limit_check_mem(ip, max_req, window)


def _scrub_webhook_payload(d: dict) -> dict:
    """Elimina headers/cookies/IP del payload del webhook antes de persistir.

    Audit zero-error 2-may-2026: el INSERT de payload_raw guardaba el dict
    completo incluyendo posibles headers, cookies, IPs si llegaban en el body.
    """
    if not isinstance(d, dict):
        return {}
    # Whitelist de claves permitidas (resto se ignora)
    permitidas = {
        'Nombre','nombre','name','Email','email','Telefono','telefono','phone',
        'Empresa','empresa','company','Mensaje','mensaje','message','source',
        'fuente','asunto','subject','origen','referer_landing',
    }
    return {k: str(v)[:500] for k, v in d.items()
            if k in permitidas and v is not None}


# ─── Pagina /comercial ────────────────────────────────────────────────────
def _hoy_col():
    """Hoy en Colombia. El servidor corre en UTC: de noche `date.today()` ya es manana aca y
    desfasa contra todo lo que se lee anclado a -5h (M24)."""
    from datetime import datetime as _dt, timedelta as _td
    return (_dt.utcnow() - _td(hours=5)).date().isoformat()


def _pipeline_puede(user):
    """Quien ve el pipeline de maquila.

    Sebastián (13-ago): *"que en el módulo de Espagiria Luz pueda crearlos, además de que tenemos
    que montar el pipeline de clientes para no perdernos"*. Luz es quien atiende a los clientes de
    maquila, así que sin esto el pipeline existía y la única persona que lo iba a usar no lo veía
    -- una capacidad que nadie puede alcanzar no existe (M121).

    Sigue siendo cerrado a propósito (SEC-FIX 21-may: el pipeline B2B es confidencial y Catalina o
    Mayerlin no lo ven). `ESPAGIRIA_ACCESS` son tres personas, así que esto suma exactamente a Luz.
    """
    u = (user or '').lower()
    return u in {x.lower() for x in ADMIN_USERS} or u in {x.lower() for x in ESPAGIRIA_ACCESS}


@bp.route('/comercial')
def comercial_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/comercial')
    # ⚠ La PAGINA no gateaba nada: se abria para cualquiera que tuviera login y quedaba vacia
    # porque la API devolvia 403. Una pantalla que abre en blanco se lee como rota, no como
    # prohibida, y ademas confunde "no tiene gate" con "el gate esta en otro lado" (M170).
    if not _pipeline_puede(session.get('compras_user', '')):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    from templates_py.comercial_html import HTML
    user = session.get('compras_user', '')
    html = HTML.replace('{usuario}', user.capitalize())
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── MAQUILA PIPELINE ─────────────────────────────────────────────────────
@bp.route('/api/comercial/maquila', methods=['GET', 'POST'])
def maquila_handler():
    # SEC-FIX · 21-may-2026 · solo admin (pipeline B2B confidencial)
    # Antes: cualquier compras_user (Mayerlin, Catalina) veía pipeline
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _pipeline_puede(user):
        return jsonify({
            'error': 'Pipeline comercial · sin acceso',
            'codigo': 'PIPELINE_PRIVADO',
        }), 403
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(force=True, silent=True) or {}
        empresa = (d.get('empresa') or '').strip()
        if not empresa:
            return jsonify({'error': 'empresa requerida'}), 400
        # Validar valor_estimado · audit zero-error
        from http_helpers import validate_money as _vm
        valor_est, err = _vm(d.get('valor_estimado_cop', 0), allow_zero=True,
                              field_name='valor_estimado_cop')
        if err:
            return jsonify(err), 400
        try:
            volumen = int(d.get('volumen_estimado_unds') or 0)
            if volumen < 0:
                return jsonify({'error': 'volumen_estimado_unds no puede ser negativo'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'volumen_estimado_unds inválido'}), 400
        # P0 audit 26-may · stage POST debe usar misma whitelist que PATCH
        # (línea 189) · sin esto un cliente malicioso puede romper kanban con
        # estados inválidos o inyectar HTML/scripts.
        stage_raw = (d.get('stage') or 'consulta').strip()
        _STAGES_OK = {'consulta','nda','brief','cotizacion','contrato',
                      'produccion','ganado','perdido'}
        if stage_raw not in _STAGES_OK:
            return jsonify({'error': f'stage inválido · válidos: {sorted(_STAGES_OK)}'}), 400
        c.execute("""INSERT INTO maquila_pipeline
            (empresa, contacto_nombre, contacto_email, contacto_telefono,
             origen, stage, valor_estimado_cop, volumen_estimado_unds,
             producto_descripcion, owner, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa,
             (d.get('contacto_nombre') or '').strip() or None,
             (d.get('contacto_email') or '').strip() or None,
             (d.get('contacto_telefono') or '').strip() or None,
             (d.get('origen') or '').strip() or None,
             stage_raw,
             valor_est, volumen,
             (d.get('producto_descripcion') or '').strip() or None,
             (d.get('owner') or user),
             (d.get('notas') or '').strip() or None))
        mid = c.lastrowid
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=user, accion='CREAR_MAQUILA_PIPELINE',
                tabla='maquila_pipeline', registro_id=mid,
                despues={'empresa': empresa[:120], 'stage': d.get('stage','consulta'),
                          'valor_estimado_cop': valor_est, 'owner': d.get('owner') or user},
                detalle=f"Pipeline maquila · {empresa} · ${valor_est/1_000_000:.1f}M")
        except Exception:
            pass
        conn.commit()
        return jsonify({'ok': True, 'id': mid}), 201

    # GET
    stage = request.args.get('stage', '').strip()
    sql = """SELECT id, empresa, contacto_nombre, contacto_email, contacto_telefono,
                    origen, stage, valor_estimado_cop, volumen_estimado_unds,
                    producto_descripcion, nda_firmado_at, brief_recibido_at,
                    cotizacion_enviada_at, contrato_firmado_at, fecha_cierre_estimada,
                    owner, notas, motivo_perdida, creado_en, actualizado_en
             FROM maquila_pipeline"""
    params = []
    if stage:
        sql += " WHERE stage=?"; params.append(stage)
    sql += " ORDER BY CASE stage "
    sql += "  WHEN 'produccion' THEN 1 WHEN 'contrato' THEN 2 "
    sql += "  WHEN 'cotizacion' THEN 3 WHEN 'brief' THEN 4 "
    sql += "  WHEN 'nda' THEN 5 WHEN 'consulta' THEN 6 "
    sql += "  WHEN 'ganado' THEN 7 WHEN 'perdido' THEN 8 ELSE 9 END, "
    sql += " creado_en DESC LIMIT 100"
    rows = c.execute(sql, params).fetchall()
    cols = ['id','empresa','contacto_nombre','contacto_email','contacto_telefono',
            'origen','stage','valor_estimado_cop','volumen_estimado_unds',
            'producto_descripcion','nda_firmado_at','brief_recibido_at',
            'cotizacion_enviada_at','contrato_firmado_at','fecha_cierre_estimada',
            'owner','notas','motivo_perdida','creado_en','actualizado_en']
    out = [dict(zip(cols, r)) for r in rows]

    # Agrupar por stage
    grupos = {}
    valor_total = 0
    for d in out:
        grupos.setdefault(d['stage'], []).append(d)
        if d['stage'] not in ('perdido','ganado'):
            valor_total += d.get('valor_estimado_cop') or 0

    return jsonify({
        'maquila': out,
        'grupos': grupos,
        'valor_pipeline_cop': valor_total,
        'total': len(out),
    })


@bp.route('/api/comercial/maquila/<int:mid>', methods=['PATCH'])
def maquila_actualizar(mid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    # ⚠ Este PATCH NO gateaba nada: el GET era solo admin y el que MODIFICA estaba abierto a
    # cualquiera con login -- se podia mover de etapa, cambiar el valor estimado o marcar perdido
    # un cliente sin ser del pipeline. La asimetria entre leer y escribir es la firma del hueco
    # (M45): al cerrar un gate hay que mirar TODOS los verbos del mismo recurso.
    if not _pipeline_puede(user):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    d = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()
    sets = []; params = []
    for col in ('empresa','contacto_nombre','contacto_email','contacto_telefono',
                'origen','valor_estimado_cop','volumen_estimado_unds',
                'producto_descripcion','owner','notas','motivo_perdida',
                'fecha_cierre_estimada'):
        if col in d:
            sets.append(f'{col}=?'); params.append(d[col])
    if 'stage' in d:
        nuevo = d['stage']
        if nuevo not in ('consulta','nda','brief','cotizacion','contrato','produccion','ganado','perdido'):
            return jsonify({'error': 'stage invalido'}), 400
        sets.append('stage=?'); params.append(nuevo)
        # Auto-stamp el campo de fecha del stage
        stage_field = {
            'nda': 'nda_firmado_at',
            'brief': 'brief_recibido_at',
            'cotizacion': 'cotizacion_enviada_at',
            'contrato': 'contrato_firmado_at',
        }.get(nuevo)
        if stage_field:
            sets.append(f'{stage_field}=COALESCE({stage_field}, ?)')
            params.append(date.today().isoformat())
    sets.append("actualizado_en=datetime('now', '-5 hours')")
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(mid)
    # Capturar antes para audit
    antes_row = c.execute(
        "SELECT empresa, stage, valor_estimado_cop FROM maquila_pipeline WHERE id=?",
        (mid,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Pipeline item no encontrado'}), 404
    antes = dict(antes_row)
    cur = c.execute(f"UPDATE maquila_pipeline SET {', '.join(sets)} WHERE id=?", params)
    try:
        from audit_helpers import audit_log as _al
        accion = 'CAMBIO_STAGE_MAQUILA' if 'stage' in d else 'ACTUALIZAR_MAQUILA_PIPELINE'
        _al(c, usuario=user, accion=accion, tabla='maquila_pipeline',
            registro_id=mid, antes=antes,
            despues={k: d.get(k) for k in d
                      if k in ('empresa', 'stage', 'valor_estimado_cop',
                               'owner', 'motivo_perdida')},
            detalle=f"Pipeline {antes.get('empresa','')[:60]} · "
                    + (f"{antes.get('stage','')}→{d.get('stage','')}" if 'stage' in d else 'editado'))
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'actualizado': cur.rowcount > 0})


# ─── EOS LEADS ────────────────────────────────────────────────────────────
# ─── LEADS QUE LLEGAN AL CORREO DE DIRECCION ───────────────────────────────
#
# Sebastián (13-ago): *"los leads llegan a mi correo direccion@animuslb.com y allí sólo llegan de
# maquila (...) la mayoría son formularios de la página web · si querés le das una revisada al
# correo para ver qué llega"*.
#
# No puedo mirarle el correo desde acá, así que esto es lo que lo reemplaza: una vista de sólo
# lectura de QUE esta llegando, con el crudo guardado. Con eso el parseo se define contra lo que
# llega de verdad y no contra lo que suponemos (M132: para afirmar que algo esta bien hace falta
# una fuente externa, y acá la fuente es su bandeja).

@bp.route('/api/comercial/leads-correo', methods=['GET'])
def leads_correo_lista():
    """Lo que llego al buzon de direccion, sin tocar nada."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    if not _pipeline_puede(session.get('compras_user', '')):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    c = get_db().cursor()
    try:
        rows = c.execute(
            "SELECT id, remitente, asunto, fecha_correo, empresa, contacto, telefono, "
            "       email_contacto, producto, empresa_inferida, pipeline_id, descartado, "
            "       SUBSTR(COALESCE(cuerpo,''),1,600) "
            "  FROM leads_correo ORDER BY fecha_correo DESC, id DESC LIMIT 200").fetchall()
    except Exception as e:
        log.warning('leads-correo: %s', e)
        return jsonify({'ok': True, 'leads': [], 'aviso': 'la tabla todavia no existe'}), 200
    campos = ('id', 'remitente', 'asunto', 'fecha_correo', 'empresa', 'contacto', 'telefono',
              'email_contacto', 'producto', 'empresa_inferida', 'pipeline_id', 'descartado',
              'cuerpo')
    leads = [dict(zip(campos, r)) for r in rows]
    try:
        from leads_correo import configurado as _cfg
        listo = _cfg()
    except Exception:
        listo = False
    sin_tarjeta = len([x for x in leads if not x['pipeline_id'] and not x['descartado']])
    return jsonify({
        'ok': True, 'leads': leads,
        'buzon_configurado': listo,
        'resumen': {'total': len(leads), 'sin_tarjeta': sin_tarjeta},
        # Un cero que nadie pudo medir se lee como "no hay nada que hacer" y significa lo
        # contrario: "no se miro" (M154).
        'aviso': (None if listo else
                  'El buzon no esta configurado en Render (IMAP_LEADS_HOST / IMAP_LEADS_USER / '
                  'IMAP_LEADS_PASSWORD), asi que esta lista esta vacia porque no se leyo nada, '
                  'no porque no hayan llegado correos.'),
    })


@bp.route('/api/comercial/leads-correo/leer', methods=['POST'])
def leads_correo_leer():
    """Trae lo nuevo del buzon AHORA. Idempotente por Message-ID."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    if not _pipeline_puede(session.get('compras_user', '')):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    from flask import current_app
    try:
        from leads_correo import leer as _leer, configurado as _cfg
    except Exception as e:
        return jsonify({'error': 'no pude cargar el lector: %s' % e}), 500
    if not _cfg():
        return jsonify({'error': 'el buzon no esta configurado',
                        'codigo': 'SIN_BUZON',
                        'como': ('cargá IMAP_LEADS_HOST, IMAP_LEADS_USER e IMAP_LEADS_PASSWORD '
                                 'en Render · las credenciales las ponés vos ahi, no viven en '
                                 'el codigo')}), 503
    ok, detalle, n = _leer(current_app._get_current_object(), limite=40, presupuesto_seg=45)
    if not ok:
        return jsonify({'ok': False, 'error': detalle.get('error', 'fallo la lectura')}), 502
    return jsonify({'ok': True, 'nuevos': n, 'detalle': detalle})


@bp.route('/api/comercial/leads-correo/<int:lid>/al-pipeline', methods=['POST'])
def lead_correo_al_pipeline(lid):
    """Convierte un correo en tarjeta del pipeline · o lo descarta con motivo.

    ⚠ El descarte NO borra: queda con su motivo y se puede recuperar. Un filtro que bota sin
    dejar rastro es un filtro en el que no se puede confiar (M138).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _pipeline_puede(user):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    r = c.execute("SELECT id, empresa, contacto, telefono, email_contacto, producto, asunto, "
                  "       pipeline_id, descartado FROM leads_correo WHERE id=?", (lid,)).fetchone()
    if not r:
        return jsonify({'error': 'ese correo no existe'}), 404
    if r[7]:
        return jsonify({'ok': True, 'pipeline_id': r[7], 'ya_estaba': True})

    if d.get('descartar'):
        motivo = (d.get('motivo') or '').strip() or 'no es un prospecto'
        c.execute("UPDATE leads_correo SET descartado=1, motivo_descarte=? WHERE id=? "
                  "  AND COALESCE(descartado,0)=0", (motivo, lid))
        if not c.rowcount:
            return jsonify({'error': 'ya estaba descartado'}), 409
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=user, accion='DESCARTAR_LEAD_CORREO', tabla='leads_correo',
                registro_id=str(lid), antes={'descartado': 0},
                despues={'descartado': 1, 'motivo': motivo}, detalle=motivo)
        except Exception as e:
            log.warning('descartar lead: no pude auditar: %s', e)
        conn.commit()
        return jsonify({'ok': True, 'descartado': True, 'motivo': motivo})

    empresa = (d.get('empresa') or r[1] or '').strip()
    if not empresa:
        return jsonify({'error': 'sin empresa no se puede abrir la tarjeta'}), 400
    # Si esa empresa ya tiene tarjeta viva, este correo se CUELGA de ella. Dos tarjetas del mismo
    # cliente son dos personas persiguiendolo sin saberlo.
    ya = c.execute("SELECT id FROM maquila_pipeline "
                   " WHERE UPPER(TRIM(empresa))=UPPER(TRIM(?)) "
                   "   AND stage NOT IN ('ganado','perdido') ORDER BY id LIMIT 1",
                   (empresa,)).fetchone()
    if ya:
        pid, nuevo = ya[0], False
    else:
        c.execute("""INSERT INTO maquila_pipeline
                       (empresa, contacto_nombre, contacto_email, contacto_telefono, origen,
                        stage, producto_descripcion, owner, notas, actualizado_en)
                     VALUES (?,?,?,?,?, 'consulta', ?,?,?,?)""",
                  (empresa, r[2] or None, r[4] or None, r[3] or None,
                   'correo direccion', r[5] or None, user, r[6] or None, _hoy_col()))
        pid, nuevo = c.lastrowid, True
        try:
            from audit_helpers import audit_log as _al
            _al(c, usuario=user, accion='ABRIR_PIPELINE_MAQUILA', tabla='maquila_pipeline',
                registro_id=str(pid), antes={}, despues={'empresa': empresa, 'stage': 'consulta'},
                detalle='abierto desde un correo que llego a direccion')
        except Exception as e:
            log.warning('lead al pipeline: no pude auditar: %s', e)
    c.execute("UPDATE leads_correo SET pipeline_id=? WHERE id=?", (pid, lid))
    conn.commit()
    return jsonify({'ok': True, 'pipeline_id': pid, 'nueva_tarjeta': nuevo, 'empresa': empresa})


# ─── PROGRESION DEL CLIENTE ────────────────────────────────────────────────
#
# Sebastián (13-ago): *"revisar bien la progresión de cada cliente, qué pasos deben llegar hasta
# ser cliente oficial y tener usuario"*.
#
# La regla de fondo: **cada etapa exige el HECHO que la justifica, no la intención de alguien**.
# Un pipeline donde se puede arrastrar la tarjeta a "contrato" sin que exista un contrato firmado
# no es un seguimiento: es una lista de deseos que se lee como un compromiso, y el que decide
# mirando eso decide mal (M19: el estado se DERIVA de un hecho registrado).
#
# Las columnas de cada hito YA EXISTEN en `maquila_pipeline` desde que se creó la tabla y nadie
# las estaba llenando. Acá se vuelven la condición para avanzar, así que el pipeline pasa de
# decorativo a auditable sin migrar nada.
PROGRESION = [
    # (etapa, hito que la habilita, qué significa en una línea)
    ('consulta',   None,
     'llego por algun lado y todavia no sabemos que quiere'),
    ('nda',        'nda_firmado_at',
     'firmo confidencialidad · sin esto no se le muestra una formula'),
    ('brief',      'brief_recibido_at',
     'dijo que quiere: producto, volumen y mercado'),
    ('cotizacion', 'cotizacion_enviada_at',
     'se le paso precio'),
    ('contrato',   'contrato_firmado_at',
     'acepto · desde aca es cliente oficial y puede tener usuario del portal'),
    ('produccion', None,
     'tiene al menos una orden en marcha'),
    ('ganado',     None,
     'cliente recurrente'),
]
_ORDEN = [x[0] for x in PROGRESION]
# Desde aca el cliente es OFICIAL. El usuario del portal no se crea antes, porque el portal sirve
# para PEDIR: darle acceso a quien no firmo es dejar entrar pedidos sin respaldo.
ETAPA_OFICIAL = 'contrato'


def _progresion_de(row):
    """Dónde está, qué sigue, y qué falta para poder avanzar.

    `row` = dict con al menos stage + las columnas de hito.
    """
    stage = (row.get('stage') or 'consulta').strip().lower()
    if stage == 'perdido':
        return {'stage': stage, 'siguiente': None, 'falta': None, 'oficial': False,
                'cerrado': True, 'que_significa': 'se cayo'}
    try:
        i = _ORDEN.index(stage)
    except ValueError:
        i = 0
    oficial = i >= _ORDEN.index(ETAPA_OFICIAL)
    sig = _ORDEN[i + 1] if i + 1 < len(_ORDEN) else None
    falta = None
    if sig:
        hito = dict((e, h) for e, h, _ in PROGRESION)[sig]
        if hito and not (row.get(hito) or '').strip():
            falta = {'campo': hito,
                     'que_hace_falta': dict((e, d) for e, _, d in PROGRESION)[sig]}
    return {'stage': stage, 'siguiente': sig, 'falta': falta, 'oficial': oficial,
            'cerrado': stage == 'ganado',
            'que_significa': dict((e, d) for e, _, d in PROGRESION)[stage],
            'puede_tener_usuario': oficial}


@bp.route('/api/comercial/maquila/progresion', methods=['GET'])
def maquila_progresion():
    """Cada cliente del pipeline con lo que le falta para el siguiente paso.

    Esto es lo que evita que se pierdan: la pregunta *"¿de quién estoy esperando qué?"* se
    contesta mirando, no acordándose.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    if not _pipeline_puede(session.get('compras_user', '')):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    c = get_db().cursor()
    cols = ('id, empresa, contacto_nombre, contacto_email, stage, owner, origen, '
            'nda_firmado_at, brief_recibido_at, cotizacion_enviada_at, contrato_firmado_at, '
            'valor_estimado_cop, creado_en, actualizado_en')
    out, oficiales, trabados = [], 0, 0
    for r in c.execute('SELECT ' + cols + ' FROM maquila_pipeline ORDER BY id').fetchall():
        d = dict(zip([x.strip() for x in cols.split(',')], r))
        p = _progresion_de(d)
        d['progresion'] = p
        if p['oficial']:
            oficiales += 1
        if p.get('falta'):
            trabados += 1
        out.append(d)
    return jsonify({
        'ok': True, 'clientes': out, 'etapas': [
            {'etapa': e, 'hito': h, 'que_significa': q} for e, h, q in PROGRESION],
        'etapa_oficial': ETAPA_OFICIAL,
        'resumen': {'total': len(out), 'oficiales': oficiales,
                    'esperando_algo': trabados},
    })


@bp.route('/api/comercial/maquila/<int:mid>/avanzar', methods=['POST'])
def maquila_avanzar(mid):
    """Avanza al cliente UNA etapa, y sólo si el hecho que la justifica está registrado.

    Body opcional: {fecha: 'YYYY-MM-DD'} para registrar el hito en el mismo acto.

    ⚠ No se puede saltar etapas: un cliente que aparece en "contrato" sin haber pasado por el
    brief deja un hueco que nadie puede reconstruir después. Si de verdad hay que corregir el
    estado a mano, para eso está el PATCH -- pero queda auditado como lo que es.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _pipeline_puede(user):
        return jsonify({'error': 'Pipeline comercial · sin acceso',
                        'codigo': 'PIPELINE_PRIVADO'}), 403
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    cols = ('id, empresa, stage, nda_firmado_at, brief_recibido_at, cotizacion_enviada_at, '
            'contrato_firmado_at')
    r = c.execute('SELECT ' + cols + ' FROM maquila_pipeline WHERE id=?', (mid,)).fetchone()
    if not r:
        return jsonify({'error': 'no existe ese cliente en el pipeline'}), 404
    row = dict(zip([x.strip() for x in cols.split(',')], r))
    p = _progresion_de(row)
    if not p['siguiente']:
        return jsonify({'error': 'ya esta en la ultima etapa', 'stage': p['stage']}), 409
    sig = p['siguiente']
    hito = dict((e, h) for e, h, _ in PROGRESION)[sig]

    sets, params = ['stage=?'], [sig]
    fecha = (d.get('fecha') or '').strip() or _hoy_col()
    if hito and not (row.get(hito) or '').strip():
        # El hecho se registra al avanzar. Si no viene y no estaba, no se inventa: se rechaza
        # diciendo QUE falta -- un "no se pudo" sin motivo obliga a adivinar (M127).
        if not d.get('registrar_hito'):
            return jsonify({
                'error': 'falta el hecho que justifica ese paso',
                'codigo': 'FALTA_HITO', 'siguiente': sig, 'campo': hito,
                'que_hace_falta': dict((e, q) for e, _, q in PROGRESION)[sig],
                'como': ('mandá {"registrar_hito": true, "fecha": "YYYY-MM-DD"} para dejarlo '
                         'registrado en el mismo acto'),
            }), 422
        sets.append(hito + '=?'); params.append(fecha)
    sets.append('actualizado_en=?'); params.append(_hoy_col())
    params.append(mid); params.append(row['stage'])
    # CAS: dos personas avanzando la misma tarjeta a la vez la saltearian dos etapas (M27).
    cur = c.execute('UPDATE maquila_pipeline SET ' + ', '.join(sets) +
                    ' WHERE id=? AND stage=?', tuple(params))
    if not cur.rowcount:
        conn.rollback()
        return jsonify({'error': 'la etapa cambio mientras tanto',
                        'codigo': 'ESTADO_CAMBIO'}), 409
    try:
        from audit_helpers import audit_log as _al
        _al(c, usuario=user, accion='AVANZAR_PIPELINE_MAQUILA',
            tabla='maquila_pipeline', registro_id=str(mid),
            antes={'stage': row['stage']}, despues={'stage': sig},
            detalle='%s -> %s%s' % (row['stage'], sig,
                                    (' · %s=%s' % (hito, fecha)) if hito else ''))
    except Exception as e:
        log.warning('avanzar pipeline: no pude auditar: %s', e)
    conn.commit()
    nuevo = _progresion_de(dict(row, stage=sig, **({hito: fecha} if hito else {})))
    return jsonify({
        'ok': True, 'empresa': row['empresa'], 'stage': sig, 'progresion': nuevo,
        'aviso': ('Ya es cliente OFICIAL: desde aca se le puede crear el usuario del portal para '
                  'que pida solo.' if nuevo['oficial'] and not p['oficial'] else
                  ('Sigue: %s · %s' % (nuevo['siguiente'], (nuevo.get('falta') or {}).get(
                      'que_hace_falta', 'sin requisito')) if nuevo['siguiente'] else 'Cerrado.')),
    })


@bp.route('/api/eos/leads', methods=['GET'])
def eos_leads_listar():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    estado = request.args.get('estado', '').strip()
    conn = get_db()
    sql = """SELECT id, nombre, email, telefono, empresa, mensaje, fuente,
                    estado, owner, notas, creado_en
             FROM eos_leads"""
    params = []
    if estado:
        sql += " WHERE estado=?"; params.append(estado)
    sql += " ORDER BY estado='nuevo' DESC, creado_en DESC LIMIT 200"
    rows = conn.execute(sql, params).fetchall()
    cols = ['id','nombre','email','telefono','empresa','mensaje','fuente',
            'estado','owner','notas','creado_en']
    return jsonify({'leads': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/eos/leads/<int:lid>', methods=['PATCH'])
def eos_lead_actualizar(lid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()
    sets = []; params = []
    for col in ('estado','owner','notas','empresa','telefono'):
        if col in d:
            sets.append(f'{col}=?'); params.append(d[col])
    if not sets: return jsonify({'error':'nada'}), 400
    # Capturar antes para audit
    antes_row = c.execute(
        "SELECT estado, owner FROM eos_leads WHERE id=?", (lid,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Lead no encontrado'}), 404
    params.append(lid)
    c.execute(f"UPDATE eos_leads SET {', '.join(sets)} WHERE id=?", params)
    try:
        from audit_helpers import audit_log as _al
        _al(c, usuario=user, accion='ACTUALIZAR_EOS_LEAD',
            tabla='eos_leads', registro_id=lid,
            antes={'estado': antes_row[0], 'owner': antes_row[1]},
            despues={k: d.get(k) for k in d if k in ('estado','owner','notas')},
            detalle=f"Lead EOS id={lid}")
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/eos/leads/webhook', methods=['POST'])
def eos_lead_webhook():
    """Webhook publico (sin auth de sesión) para recibir submissions de web3forms.

    Audit zero-error 2-may-2026: ahora requiere HMAC opcional + rate limit
    + sanitización del payload. Si la env var EOS_WEBHOOK_SECRET está
    configurada, el header X-EOS-Signature debe coincidir con
    HMAC-SHA256(body, EOS_WEBHOOK_SECRET).

    Web3Forms envia POST con form fields en el body. Tambien podemos
    recibir desde otros forms.

    Acepta application/json o application/x-www-form-urlencoded.
    """
    # ── Rate limit: 5 req/min/IP ──────────────────────────────────────────
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    ip = (ip or 'unknown').split(',')[0].strip()[:45]
    if _rate_limit_check(ip):
        log.warning('eos_lead_webhook rate-limited · ip=%s', ip)
        return jsonify({'error': 'rate limit excedido', 'codigo': 'RATE_LIMIT'}), 429

    # ── HMAC signature (fail-close en producción · SEC-FIX 21-may-2026) ──
    # Antes: si EOS_WEBHOOK_SECRET no estaba en env, aceptaba cualquier payload
    # Ahora: en prod (env ENV=production) FAIL-CLOSE · 503 sin secret configurado
    secret = os.environ.get('EOS_WEBHOOK_SECRET', '').strip()
    is_prod = (os.environ.get('ENV') or os.environ.get('FLASK_ENV') or '').lower() == 'production'
    if not secret and is_prod:
        log.critical('eos_lead_webhook · EOS_WEBHOOK_SECRET no configurado en producción · DENY')
        return jsonify({
            'error': 'Webhook no configurado · contactar admin',
            'codigo': 'WEBHOOK_NO_CONFIG',
        }), 503
    if secret:
        body_bytes = request.get_data(cache=True) or b''
        signature = (request.headers.get('X-EOS-Signature') or '').strip()
        expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            log.warning('eos_lead_webhook HMAC fail · ip=%s', ip)
            return jsonify({'error': 'firma inválida', 'codigo': 'BAD_SIGNATURE'}), 403

    try:
        if request.is_json:
            d = request.get_json(force=True, silent=True) or {}
        else:
            d = request.form.to_dict() if request.form else {}
            if not d:
                d = request.get_json(force=True, silent=True) or {}
    except Exception:
        d = {}
    nombre = (d.get('Nombre') or d.get('nombre') or d.get('name') or '').strip()
    email = (d.get('Email') or d.get('email') or '').strip()
    if not nombre and not email:
        return jsonify({'error': 'falta nombre o email'}), 400
    telefono = (d.get('Telefono') or d.get('telefono') or d.get('phone') or '').strip()
    empresa = (d.get('Empresa') or d.get('empresa') or d.get('company') or '').strip()
    mensaje = (d.get('Mensaje') or d.get('mensaje') or d.get('message') or '').strip()
    fuente = d.get('source') or 'web3forms'
    # Audit zero-error: sanitizar payload antes de persistir (no headers/cookies/IP)
    payload_limpio = _scrub_webhook_payload(d)
    raw = json.dumps(payload_limpio, ensure_ascii=False, default=str)[:4000]
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO eos_leads
        (nombre, email, telefono, empresa, mensaje, fuente, payload_raw, owner)
        VALUES (?,?,?,?,?,?,?,?)""",
        (nombre[:200] or None, email[:200] or None, telefono[:50] or None,
         empresa[:200] or None, mensaje[:2000] or None, fuente[:100], raw, 'sebastian'))
    new_id = c.lastrowid
    conn.commit()
    # Notif in-app a sebastian
    try:
        from blueprints.notif import push_notif
        push_notif('sebastian', 'generico',
                   f'🆕 Lead EOS: {(nombre or email)[:60]}',
                   body=(empresa[:60] if empresa else '') + ' · ' + (mensaje or '')[:80],
                   link='/comercial', remitente=fuente, importante=True)
    except Exception: pass
    return jsonify({'ok': True, 'id': new_id})
