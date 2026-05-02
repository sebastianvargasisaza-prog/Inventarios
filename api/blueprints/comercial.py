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
from config import ADMIN_USERS

logger = logging.getLogger(__name__)
log = logger
bp = Blueprint('comercial', __name__)


# ─── Rate limiter en memoria por IP ────────────────────────────────────────
# Audit zero-error 2-may-2026: webhook público sin rate limit permitía
# inundar la BD con leads falsos. 5 req/min/IP es suficiente para web3forms
# (1 lead esperado por sumisión humana) y bloquea bots.
_RATE_BUCKETS = {}  # ip → [timestamps]


def _rate_limit_check(ip: str, max_req: int = 5, window: int = 60) -> bool:
    """Retorna True si la IP excedió el límite (debe rechazarse)."""
    now = time.time()
    bucket = _RATE_BUCKETS.setdefault(ip, [])
    # Limpiar entradas viejas
    bucket[:] = [t for t in bucket if (now - t) < window]
    if len(bucket) >= max_req:
        return True
    bucket.append(now)
    return False


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
@bp.route('/comercial')
def comercial_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/comercial')
    from templates_py.comercial_html import HTML
    user = session.get('compras_user', '')
    html = HTML.replace('{usuario}', user.capitalize())
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── MAQUILA PIPELINE ─────────────────────────────────────────────────────
@bp.route('/api/comercial/maquila', methods=['GET', 'POST'])
def maquila_handler():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
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
        except (TypeError, ValueError):
            return jsonify({'error': 'volumen_estimado_unds inválido'}), 400
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
             (d.get('stage') or 'consulta'),
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
    sets.append("actualizado_en=datetime('now')")
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

    # ── HMAC signature (opcional, recomendado en prod) ────────────────────
    secret = os.environ.get('EOS_WEBHOOK_SECRET', '').strip()
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
