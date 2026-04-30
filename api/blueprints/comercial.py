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
import logging
from datetime import date
from database import get_db
from config import ADMIN_USERS

logger = logging.getLogger(__name__)
bp = Blueprint('comercial', __name__)


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
             float(d.get('valor_estimado_cop') or 0),
             int(d.get('volumen_estimado_unds') or 0),
             (d.get('producto_descripcion') or '').strip() or None,
             (d.get('owner') or user),
             (d.get('notas') or '').strip() or None))
        conn.commit()
        return jsonify({'ok': True, 'id': c.lastrowid}), 201

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
    cur = c.execute(f"UPDATE maquila_pipeline SET {', '.join(sets)} WHERE id=?", params)
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
    params.append(lid)
    c.execute(f"UPDATE eos_leads SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/eos/leads/webhook', methods=['POST'])
def eos_lead_webhook():
    """Webhook publico (sin auth) para recibir submissions de web3forms.

    Web3Forms envia POST con form fields en el body. Tambien podemos
    recibir desde otros forms.

    Sebastian (30-abr-2026): correo "EOS — nueva solicitud de demo" 30 abr
    llego como email — webhook lo capturaria directo a BD.

    Acepta application/json o application/x-www-form-urlencoded.
    """
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
    raw = json.dumps(d, ensure_ascii=False, default=str)[:4000]
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO eos_leads
        (nombre, email, telefono, empresa, mensaje, fuente, payload_raw, owner)
        VALUES (?,?,?,?,?,?,?,?)""",
        (nombre or None, email or None, telefono or None,
         empresa or None, mensaje or None, fuente, raw, 'sebastian'))
    new_id = c.lastrowid
    conn.commit()
    # Notif in-app a sebastian
    try:
        from blueprints.notif import push_notif
        push_notif('sebastian', 'generico',
                   f'🆕 Lead EOS: {nombre or email}',
                   body=(empresa or '') + ' · ' + (mensaje or '')[:80],
                   link='/comercial', remitente=fuente, importante=True)
    except Exception: pass
    return jsonify({'ok': True, 'id': new_id})
