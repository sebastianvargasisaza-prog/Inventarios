"""Artes/Etiquetas · gate de Direccion Tecnica (Sebastian 19-jul).

Flujo: Catalina (Compras) SOLICITA la revision de una etiqueta/arte al Director
Tecnico -> DT revisa INCI/ingredientes y APRUEBA con e-firma (1a revision, arte) ->
se manda a hacer -> cuando LLEGA, DT da una 2a mirada (fisica) y LIBERA -> recien
ahi la etiqueta queda usable. Gate DURO: sin arte aprobado no se envia a marcacion
ni se reciben etiquetas. La biblioteca de artes vive en un Drive (link por arte +
link maestro de la carpeta), embebido en el panel de DT.
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session, Response, redirect

from database import get_db
from audit_helpers import audit_log
from config import TECNICA_USERS, ADMIN_USERS, COMPRAS_USERS

bp = Blueprint('artes', __name__)

_ESTADOS = ('borrador', 'pendiente_dt', 'aprobado', 'rechazado', 'obsoleto')
_TIPOS = ('etiqueta', 'arte', 'serigrafia', 'plegadiza', 'inserto')


def _hoy_co():
    return (datetime.utcnow() - timedelta(hours=5)).isoformat(timespec='seconds')


def _puede_solicitar(u):
    return u in COMPRAS_USERS or u in TECNICA_USERS or u in ADMIN_USERS


def _es_dt(u):
    return u in TECNICA_USERS or u in ADMIN_USERS


def _norm(s):
    return (s or '').strip().upper()


def _valida_firma(c, signature_id, *, record_id, meaning, signer):
    """Valida e-firma Part 11 sobre un arte (mismo patron que Calidad/EBR)."""
    if not signature_id:
        return False
    try:
        return c.execute(
            "SELECT id FROM e_signatures WHERE id=? AND record_table='artes_etiquetas' "
            "AND record_id=? AND meaning=? AND signer_username=?",
            (int(signature_id), str(record_id), meaning, signer)).fetchone() is not None
    except Exception:
        return False


def arte_aprobado_para(conn, producto_nombre, presentacion_codigo=''):
    """GATE: True si existe un arte con estado 'aprobado' (arte_aprobado=1) para ese
    producto (y presentacion si se especifica). Lo consumen el envio a marcacion y la
    recepcion de etiquetas. Match por nombre normalizado (UPPER/TRIM)."""
    c = conn.cursor()
    prod = _norm(producto_nombre)
    if not prod:
        return False
    pres = (presentacion_codigo or '').strip()
    try:
        if pres:
            row = c.execute(
                "SELECT 1 FROM artes_etiquetas WHERE UPPER(TRIM(producto_nombre))=? "
                "AND arte_aprobado=1 AND estado='aprobado' "
                "AND (TRIM(COALESCE(presentacion_codigo,''))='' OR TRIM(presentacion_codigo)=?) LIMIT 1",
                (prod, pres)).fetchone()
        else:
            row = c.execute(
                "SELECT 1 FROM artes_etiquetas WHERE UPPER(TRIM(producto_nombre))=? "
                "AND arte_aprobado=1 AND estado='aprobado' LIMIT 1", (prod,)).fetchone()
        return row is not None
    except Exception:
        return False


# ─────────────────────────── API ───────────────────────────

@bp.route('/api/artes', methods=['GET'])
def artes_lista():
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'error': 'No autorizado'}), 401
    estado = (request.args.get('estado') or '').strip()
    producto = (request.args.get('producto') or '').strip()
    conn = get_db(); c = conn.cursor()
    sql = ("SELECT id, producto_nombre, presentacion_codigo, mee_codigo, tipo, version, estado, "
           "solicitado_por, solicitado_at, solicitud_notas, arte_aprobado, arte_aprobado_por, "
           "arte_aprobado_at, inci_revisado, drive_url, fisica_aprobada, fisica_aprobada_por, "
           "fisica_aprobada_at, rechazo_motivo, notas, creado_at "
           "FROM artes_etiquetas")
    cl, pr = [], []
    if estado and estado in _ESTADOS:
        cl.append('estado=?'); pr.append(estado)
    if producto:
        cl.append('UPPER(TRIM(producto_nombre)) LIKE ?'); pr.append('%' + _norm(producto) + '%')
    if cl:
        sql += ' WHERE ' + ' AND '.join(cl)
    sql += (" ORDER BY CASE estado WHEN 'pendiente_dt' THEN 0 WHEN 'aprobado' THEN 1 "
            "WHEN 'rechazado' THEN 2 ELSE 3 END, creado_at DESC LIMIT 300")
    cols = ['id', 'producto_nombre', 'presentacion_codigo', 'mee_codigo', 'tipo', 'version', 'estado',
            'solicitado_por', 'solicitado_at', 'solicitud_notas', 'arte_aprobado', 'arte_aprobado_por',
            'arte_aprobado_at', 'inci_revisado', 'drive_url', 'fisica_aprobada', 'fisica_aprobada_por',
            'fisica_aprobada_at', 'rechazo_motivo', 'notas', 'creado_at']
    rows = [dict(zip(cols, r)) for r in c.execute(sql, pr).fetchall()]
    # link maestro de la biblioteca (Drive)
    try:
        bib = c.execute("SELECT valor FROM app_settings WHERE clave='artes_drive_url' LIMIT 1").fetchone()
        biblioteca = bib[0] if bib else ''
    except Exception:
        biblioteca = ''
    resumen = {
        'pendientes': sum(1 for r in rows if r['estado'] == 'pendiente_dt'),
        'aprobados': sum(1 for r in rows if r['estado'] == 'aprobado'),
        'por_recibir': sum(1 for r in rows if r['estado'] == 'aprobado' and not r['fisica_aprobada']),
    }
    return jsonify({'artes': rows, 'biblioteca': biblioteca, 'resumen': resumen,
                    'soy_dt': _es_dt(u), 'puedo_solicitar': _puede_solicitar(u)})


@bp.route('/api/artes/solicitar', methods=['POST'])
def artes_solicitar():
    """Catalina (Compras) solicita a DT revisar una etiqueta/arte."""
    u = session.get('compras_user', '')
    if not _puede_solicitar(u):
        return jsonify({'error': 'Solo Compras/DT'}), 403
    d = request.json or {}
    prod = (d.get('producto_nombre') or '').strip()
    if not prod:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    tipo = (d.get('tipo') or 'etiqueta').strip().lower()
    if tipo not in _TIPOS:
        tipo = 'etiqueta'
    pres = (d.get('presentacion_codigo') or '').strip()
    mee = (d.get('mee_codigo') or '').strip()
    drive = (d.get('drive_url') or '').strip()
    notas = (d.get('solicitud_notas') or d.get('notas') or '').strip()
    conn = get_db(); c = conn.cursor()
    # version siguiente para ese producto+presentacion
    try:
        vr = c.execute("SELECT COALESCE(MAX(version),0)+1 FROM artes_etiquetas "
                       "WHERE UPPER(TRIM(producto_nombre))=? AND TRIM(COALESCE(presentacion_codigo,''))=?",
                       (_norm(prod), pres)).fetchone()
        ver = int(vr[0]) if vr and vr[0] else 1
    except Exception:
        ver = 1
    c.execute("INSERT INTO artes_etiquetas (producto_nombre, presentacion_codigo, mee_codigo, tipo, "
              "version, estado, solicitado_por, solicitado_at, solicitud_notas, drive_url, creado_at) "
              "VALUES (?,?,?,?,?,'pendiente_dt',?,?,?,?,?)",
              (prod, pres, mee, tipo, ver, u, _hoy_co(), notas, drive, _hoy_co()))
    aid = c.lastrowid
    audit_log(c, usuario=u, accion='ARTE_SOLICITAR_REVISION', tabla='artes_etiquetas',
              registro_id=aid, detalle=f'{prod} {pres} v{ver} tipo={tipo}')
    conn.commit()
    return jsonify({'ok': True, 'id': aid, 'version': ver}), 201


@bp.route('/api/artes/<int:aid>/aprobar-arte', methods=['POST'])
def artes_aprobar_arte(aid):
    """DT aprueba el ARTE (1a revision · INCI) con e-firma (meaning='aprueba')."""
    u = session.get('compras_user', '')
    if not _es_dt(u):
        return jsonify({'error': 'Solo Direccion Tecnica'}), 403
    d = request.json or {}
    sig = d.get('signature_id')
    conn = get_db(); c = conn.cursor()
    if not _valida_firma(c, sig, record_id=aid, meaning='aprueba', signer=u):
        return jsonify({'error': 'e-firma requerida (meaning=aprueba, record_table=artes_etiquetas)'}), 400
    inci = 1 if d.get('inci_revisado') else 0
    notas = (d.get('notas') or '').strip()
    # CAS: solo si esta pendiente_dt (o borrador)
    c.execute("UPDATE artes_etiquetas SET estado='aprobado', arte_aprobado=1, arte_aprobado_por=?, "
              "arte_aprobado_at=?, arte_signature_id=?, inci_revisado=?, notas=COALESCE(NULLIF(?,''),notas) "
              "WHERE id=? AND estado IN ('pendiente_dt','borrador')",
              (u, _hoy_co(), int(sig), inci, notas, aid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'El arte no esta pendiente (ya resuelto o inexistente)'}), 409
    audit_log(c, usuario=u, accion='ARTE_APROBAR', tabla='artes_etiquetas', registro_id=aid,
              detalle=f'inci_revisado={inci} sig={sig}')
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/artes/<int:aid>/rechazar', methods=['POST'])
def artes_rechazar(aid):
    """DT rechaza el arte con e-firma (meaning='rechaza')."""
    u = session.get('compras_user', '')
    if not _es_dt(u):
        return jsonify({'error': 'Solo Direccion Tecnica'}), 403
    d = request.json or {}
    sig = d.get('signature_id')
    motivo = (d.get('motivo') or '').strip()
    conn = get_db(); c = conn.cursor()
    if not _valida_firma(c, sig, record_id=aid, meaning='rechaza', signer=u):
        return jsonify({'error': 'e-firma requerida (meaning=rechaza)'}), 400
    if not motivo:
        return jsonify({'error': 'motivo requerido'}), 400
    c.execute("UPDATE artes_etiquetas SET estado='rechazado', rechazo_motivo=?, arte_aprobado=0 "
              "WHERE id=? AND estado IN ('pendiente_dt','borrador','aprobado')", (motivo, aid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'El arte no se puede rechazar en su estado actual'}), 409
    audit_log(c, usuario=u, accion='ARTE_RECHAZAR', tabla='artes_etiquetas', registro_id=aid, detalle=motivo[:200])
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/artes/<int:aid>/aprobar-fisica', methods=['POST'])
def artes_aprobar_fisica(aid):
    """DT da la 2a mirada a la etiqueta FISICA que llego (meaning='libera')."""
    u = session.get('compras_user', '')
    if not _es_dt(u):
        return jsonify({'error': 'Solo Direccion Tecnica'}), 403
    d = request.json or {}
    sig = d.get('signature_id')
    conn = get_db(); c = conn.cursor()
    if not _valida_firma(c, sig, record_id=aid, meaning='libera', signer=u):
        return jsonify({'error': 'e-firma requerida (meaning=libera)'}), 400
    c.execute("UPDATE artes_etiquetas SET fisica_aprobada=1, fisica_aprobada_por=?, fisica_aprobada_at=?, "
              "fisica_signature_id=? WHERE id=? AND estado='aprobado' AND fisica_aprobada=0",
              (u, _hoy_co(), int(sig), aid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'El arte debe estar aprobado y sin liberacion fisica previa'}), 409
    audit_log(c, usuario=u, accion='ARTE_APROBAR_FISICA', tabla='artes_etiquetas', registro_id=aid, detalle=f'sig={sig}')
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/artes/biblioteca', methods=['GET', 'POST'])
def artes_biblioteca():
    """Link maestro de la carpeta de Drive con todos los artes."""
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if not _es_dt(u):
            return jsonify({'error': 'Solo Direccion Tecnica'}), 403
        url = (request.json or {}).get('url', '').strip()
        c.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('artes_drive_url', ?)", (url,))
        audit_log(c, usuario=u, accion='ARTE_BIBLIOTECA_URL', tabla='app_settings', registro_id=0, detalle=url[:200])
        conn.commit()
        return jsonify({'ok': True, 'url': url})
    row = c.execute("SELECT valor FROM app_settings WHERE clave='artes_drive_url' LIMIT 1").fetchone()
    return jsonify({'url': row[0] if row else ''})


@bp.route('/artes')
def artes_page():
    u = session.get('compras_user', '')
    if not u:
        return redirect('/login?next=/artes')
    if not (_es_dt(u) or _puede_solicitar(u)):
        return Response('<h1>Sin acceso</h1>', mimetype='text/html'), 403
    from templates_py.artes_html import ARTES_HTML
    return Response(ARTES_HTML.replace('{usuario}', u), mimetype='text/html')
