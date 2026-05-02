"""Blueprint: Aseguramiento de Calidad (ASG)

Gobierno documental + eventos no-rutinarios + auditorías. Complementario a
/calidad (que es operativo del laboratorio · COC).

Procedimientos cubiertos:
- ASG-NOR-001 Norma Documental → SGD electrónico
- ASG-LMA-001 Listado Maestro → generación automática
- ASG-PRO-001 Manejo de Desviaciones
- ASG-PRO-007 Control de Cambios
- ASG-PRO-004 Recall / Simulacro Retiro
- COC-EVA-002 Examen Envase Empaque → capacitaciones online
- Quejas de clientes
- Actas de reunión (ASG-PGM-003)

Este blueprint NO toca tablas existentes (no_conformidades, capa_acciones,
auditorias). Esas se mantienen en /api/calidad/* por backward compat;
los tabs UI sí se mueven a /aseguramiento.

Sebastián 1-may-2026.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, date
from flask import Blueprint, jsonify, request, session, Response

from database import get_db
from config import ADMIN_USERS, CALIDAD_USERS, COMPRAS_USERS
from templates_py.aseguramiento_html import ASEGURAMIENTO_HTML

bp = Blueprint('aseguramiento', __name__)
log = logging.getLogger('aseguramiento')


# Áreas oficiales SGD según ASG-NOR-001
AREAS_SGD = {
    'COC': 'Control de Calidad',
    'ASG': 'Aseguramiento',
    'ADM': 'Administración',
    'BDG': 'Bodega',
    'GER': 'Gerencia',
    'PRD': 'Producción',
    'RRH': 'Recursos Humanos',
    'SST': 'Seguridad y Salud',
}

TIPOS_DOC = {
    'PRO': 'Procedimiento',
    'NOR': 'Norma',
    'MAN': 'Manual',
    'INS': 'Instructivo',
    'POL': 'Política',
    'FOR': 'Formato',
    'EVA': 'Evaluación',
    'ACT': 'Acta',
    'REG': 'Registro',
    'DES': 'Descripción',
    'LMA': 'Listado Maestro',
    'PGM': 'Programa',
    'CRO': 'Cronograma',
}


def _autorizados_lectura():
    """Lectura del SGD: cualquier compras_user (es info de gobierno)."""
    return set(COMPRAS_USERS) if COMPRAS_USERS else set()


def _autorizados_escritura():
    """Escritura del SGD: solo CALIDAD + ADMIN (Aseguramiento gestiona docs)."""
    return set(CALIDAD_USERS) | set(ADMIN_USERS)


# ════════════════════════════════════════════════════════════════════════
# Página HTML del módulo
# ════════════════════════════════════════════════════════════════════════
@bp.route('/aseguramiento')
def aseguramiento_page():
    if 'compras_user' not in session:
        from flask import redirect
        return redirect('/login')
    return Response(ASEGURAMIENTO_HTML, mimetype='text/html; charset=utf-8')


# ════════════════════════════════════════════════════════════════════════
# Dashboard ASG · KPIs principales
# ════════════════════════════════════════════════════════════════════════
@bp.route('/api/aseguramiento/dashboard', methods=['GET'])
def aseguramiento_dashboard():
    """Resumen de aseguramiento: SGD, capacitaciones pendientes, NCs, auditorías,
    desviaciones, control de cambios, recall.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    out = {'fecha_hoy': datetime.now().date().isoformat()}

    # SGD: docs vigentes / próximos a vencer / obsoletos / conflictos
    # SQLite no soporta COUNT(*) FILTER · usar COUNT(CASE WHEN ...)
    try:
        sgd = c.execute("""
            SELECT
              COUNT(CASE WHEN estado='vigente' THEN 1 END) as vigentes,
              COUNT(CASE WHEN estado='vigente'
                          AND date(proxima_revision) <= date('now','+30 days')
                          AND date(proxima_revision) >= date('now')
                       THEN 1 END) as vencen_30d,
              COUNT(CASE WHEN estado='vigente'
                          AND date(proxima_revision) < date('now')
                       THEN 1 END) as vencidos,
              COUNT(CASE WHEN estado='obsoleto' THEN 1 END) as obsoletos,
              COUNT(CASE WHEN estado='conflicto' THEN 1 END) as conflictos,
              COUNT(CASE WHEN estado='borrador' THEN 1 END) as borradores,
              COUNT(*) as total
            FROM sgd_documentos
        """).fetchone()
        out['sgd'] = {
            'vigentes': sgd[0] or 0, 'vencen_30d': sgd[1] or 0,
            'vencidos': sgd[2] or 0, 'obsoletos': sgd[3] or 0,
            'conflictos': sgd[4] or 0, 'borradores': sgd[5] or 0,
            'total': sgd[6] or 0,
        }
    except Exception as e:
        log.warning('dashboard sgd fallo: %s', e)
        out['sgd'] = {}

    # Capacitaciones pendientes
    try:
        cap = c.execute("""
            SELECT
              COUNT(CASE WHEN estado IN ('asignada','leida') THEN 1 END) as pendientes,
              COUNT(CASE WHEN estado='vencida' THEN 1 END) as vencidas,
              COUNT(CASE WHEN estado IN ('firmada','aprobada')
                          AND date(firmado_at) >= date('now','-30 days')
                       THEN 1 END) as firmadas_30d
            FROM sgd_capacitaciones
        """).fetchone()
        out['capacitaciones'] = {
            'pendientes': cap[0] or 0, 'vencidas': cap[1] or 0,
            'firmadas_30d': cap[2] or 0,
        }
    except Exception as e:
        log.info('dashboard capacitaciones: %s', e)
        out['capacitaciones'] = {}

    # NCs abiertas (tabla en /calidad pero KPI aquí)
    try:
        nc = c.execute("""
            SELECT COUNT(*) FROM no_conformidades WHERE estado = 'Abierta'
        """).fetchone()
        out['ncs_abiertas'] = nc[0] or 0
    except Exception:
        out['ncs_abiertas'] = 0

    # Auditorías próximas 60d
    try:
        a = c.execute("""
            SELECT COUNT(*) FROM auditorias
            WHERE date(fecha) BETWEEN date('now') AND date('now','+60 days')
              AND COALESCE(estado,'programada') NOT IN ('completada','cancelada')
        """).fetchone()
        out['auditorias_60d'] = a[0] or 0
    except Exception:
        out['auditorias_60d'] = 0

    return jsonify(out)


# ════════════════════════════════════════════════════════════════════════
# SGD ELECTRÓNICO · ASG-NOR-001 + ASG-LMA-001
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/aseguramiento/sgd/listado', methods=['GET'])
def sgd_listado():
    """Listado maestro de documentos. Filtros: area, tipo_doc, estado, q (búsqueda).

    Reemplaza ASG-LMA-001 manual (xlsx). Generado automáticamente.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    area = (request.args.get('area') or '').strip().upper()
    tipo = (request.args.get('tipo_doc') or '').strip().upper()
    estado = (request.args.get('estado') or '').strip().lower()
    q = (request.args.get('q') or '').strip()
    incluir_hijos = request.args.get('incluir_hijos', '1') == '1'

    where = []; params = []
    if area: where.append('area = ?'); params.append(area)
    if tipo: where.append('tipo_doc = ?'); params.append(tipo)
    if estado: where.append('estado = ?'); params.append(estado)
    if not incluir_hijos: where.append('padre_codigo IS NULL')
    if q:
        where.append('(codigo LIKE ? OR titulo LIKE ?)')
        like = f'%{q}%'
        params.extend([like, like])

    sql = """SELECT codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                    titulo, version_actual, estado, vigente_desde,
                    proxima_revision, archivo_pdf_url,
                    elaborado_por, revisado_por, aprobado_por,
                    CASE
                      WHEN estado = 'vigente' AND date(proxima_revision) < date('now') THEN 'vencido'
                      WHEN estado = 'vigente' AND date(proxima_revision) <= date('now','+30 days') THEN 'vence_pronto'
                      ELSE estado
                    END as estado_efectivo
             FROM sgd_documentos"""
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY area, tipo_doc, numero, COALESCE(subtipo, "") LIMIT 2000'
    rows = get_db().execute(sql, params).fetchall()
    cols = ['codigo','area','tipo_doc','numero','subtipo','padre_codigo',
            'titulo','version_actual','estado','vigente_desde',
            'proxima_revision','archivo_pdf_url',
            'elaborado_por','revisado_por','aprobado_por','estado_efectivo']
    items = [dict(zip(cols, r)) for r in rows]
    # Resumen por área
    resumen_area = {}
    for it in items:
        resumen_area.setdefault(it['area'], 0)
        resumen_area[it['area']] += 1
    return jsonify({
        'total': len(items),
        'items': items,
        'resumen_por_area': resumen_area,
        'areas': AREAS_SGD,
        'tipos_doc': TIPOS_DOC,
    })


@bp.route('/api/aseguramiento/sgd/<path:codigo>', methods=['GET'])
def sgd_detalle(codigo):
    """Detalle del documento + histórico de versiones + capacitaciones."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    doc = c.execute("""
        SELECT codigo, area, tipo_doc, numero, subtipo, padre_codigo,
               titulo, descripcion, version_actual, archivo_pdf_url,
               archivo_origen, fecha_creacion, fecha_aprobacion,
               vigente_desde, proxima_revision, estado,
               elaborado_por, revisado_por, aprobado_por, observaciones,
               creado_por, creado_en, actualizado_en
        FROM sgd_documentos WHERE codigo = ?
    """, (codigo,)).fetchone()
    if not doc:
        return jsonify({'error': f'Documento {codigo} no encontrado'}), 404
    cols = ['codigo','area','tipo_doc','numero','subtipo','padre_codigo',
            'titulo','descripcion','version_actual','archivo_pdf_url',
            'archivo_origen','fecha_creacion','fecha_aprobacion',
            'vigente_desde','proxima_revision','estado',
            'elaborado_por','revisado_por','aprobado_por','observaciones',
            'creado_por','creado_en','actualizado_en']
    detalle = dict(zip(cols, doc))

    # Hijos (formatos -F##, anexos -A##)
    hijos = c.execute("""
        SELECT codigo, subtipo, titulo, version_actual, estado
        FROM sgd_documentos WHERE padre_codigo = ?
        ORDER BY subtipo
    """, (codigo,)).fetchall()
    detalle['hijos'] = [{'codigo': r[0], 'subtipo': r[1], 'titulo': r[2],
                          'version': r[3], 'estado': r[4]} for r in hijos]

    # Versiones históricas
    versiones = c.execute("""
        SELECT version, fecha_aprobacion, archivo_url, motivo_cambio,
               aprobado_por, creado_en
        FROM sgd_versiones WHERE codigo = ?
        ORDER BY fecha_aprobacion DESC, id DESC LIMIT 50
    """, (codigo,)).fetchall()
    detalle['versiones'] = [{
        'version': r[0], 'fecha_aprobacion': r[1], 'archivo_url': r[2],
        'motivo_cambio': r[3], 'aprobado_por': r[4], 'creado_en': r[5],
    } for r in versiones]

    # Capacitaciones de la versión actual
    caps = c.execute("""
        SELECT persona_username, asignado_at, leido_at, firmado_at,
               estado, fecha_limite
        FROM sgd_capacitaciones
        WHERE sgd_codigo = ? AND sgd_version = ?
        ORDER BY estado DESC, persona_username
    """, (codigo, detalle['version_actual'])).fetchall()
    detalle['capacitaciones'] = [{
        'persona': r[0], 'asignado_at': r[1], 'leido_at': r[2],
        'firmado_at': r[3], 'estado': r[4], 'fecha_limite': r[5],
    } for r in caps]

    return jsonify(detalle)


@bp.route('/api/aseguramiento/sgd', methods=['POST'])
def sgd_crear_o_actualizar():
    """Crea un documento nuevo o sube nueva versión.

    Body: {
      codigo, area, tipo_doc, numero, subtipo (opt), padre_codigo (opt),
      titulo, descripcion (opt), version (default '1'), archivo_pdf_url (opt),
      archivo_origen (opt), fecha_aprobacion (opt), vigente_desde (opt),
      proxima_revision (opt), estado (default 'vigente'),
      elaborado_por, revisado_por, aprobado_por, observaciones,
      motivo_cambio (si es nueva versión)
    }
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin pueden gestionar SGD'}), 403

    d = request.get_json(silent=True) or {}
    codigo = (d.get('codigo') or '').strip().upper()
    if not codigo or not re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{1,3}(?:-[A-Z]\d{1,2})?$', codigo):
        return jsonify({'error': 'codigo inválido (formato AAA-BBB-NNN[-FNN])'}), 400

    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'titulo requerido'}), 400

    # Parsear codigo
    parts = codigo.split('-')
    area, tipo_doc = parts[0], parts[1]
    if area not in AREAS_SGD:
        return jsonify({'error': f'área {area} no reconocida (válidas: {", ".join(AREAS_SGD)})'}), 400
    if tipo_doc not in TIPOS_DOC:
        return jsonify({'error': f'tipo_doc {tipo_doc} no reconocido'}), 400
    try:
        numero = int(parts[2])
    except (ValueError, IndexError):
        return jsonify({'error': 'numero inválido en código'}), 400
    subtipo = parts[3] if len(parts) > 3 else None
    padre_codigo = '-'.join(parts[:3]) if subtipo else None

    version = (d.get('version') or '1').strip()
    estado = (d.get('estado') or 'vigente').strip().lower()
    if estado not in ('borrador','revision','vigente','obsoleto','retirado','conflicto'):
        return jsonify({'error': 'estado inválido'}), 400

    conn = get_db(); c = conn.cursor()
    # ¿Existe?
    existe = c.execute("SELECT codigo, version_actual FROM sgd_documentos WHERE codigo=?",
                       (codigo,)).fetchone()
    try:
        if existe:
            # Si la versión cambió, archivar la anterior
            ver_anterior = existe[1]
            if version != ver_anterior:
                c.execute("""
                    INSERT OR IGNORE INTO sgd_versiones
                      (codigo, version, fecha_aprobacion, archivo_url, motivo_cambio, aprobado_por)
                    SELECT codigo, version_actual, fecha_aprobacion, archivo_pdf_url,
                           ?, aprobado_por
                    FROM sgd_documentos WHERE codigo=?
                """, (d.get('motivo_cambio') or 'Versión anterior archivada', codigo))
            # UPDATE
            c.execute("""
                UPDATE sgd_documentos SET
                  area=?, tipo_doc=?, numero=?, subtipo=?, padre_codigo=?,
                  titulo=?, descripcion=?, version_actual=?,
                  archivo_pdf_url=?, archivo_origen=?, fecha_creacion=?,
                  fecha_aprobacion=?, vigente_desde=?, proxima_revision=?,
                  estado=?, elaborado_por=?, revisado_por=?, aprobado_por=?,
                  observaciones=?, actualizado_en=datetime('now')
                WHERE codigo=?
            """, (area, tipo_doc, numero, subtipo, padre_codigo,
                  titulo, d.get('descripcion'), version,
                  d.get('archivo_pdf_url'), d.get('archivo_origen'),
                  d.get('fecha_creacion'), d.get('fecha_aprobacion'),
                  d.get('vigente_desde'), d.get('proxima_revision'),
                  estado, d.get('elaborado_por'), d.get('revisado_por'),
                  d.get('aprobado_por'), d.get('observaciones'), codigo))
            accion = 'actualizado'
        else:
            c.execute("""
                INSERT INTO sgd_documentos
                  (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                   titulo, descripcion, version_actual,
                   archivo_pdf_url, archivo_origen, fecha_creacion,
                   fecha_aprobacion, vigente_desde, proxima_revision,
                   estado, elaborado_por, revisado_por, aprobado_por,
                   observaciones, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                  titulo, d.get('descripcion'), version,
                  d.get('archivo_pdf_url'), d.get('archivo_origen'),
                  d.get('fecha_creacion'), d.get('fecha_aprobacion'),
                  d.get('vigente_desde'), d.get('proxima_revision'),
                  estado, d.get('elaborado_por'), d.get('revisado_por'),
                  d.get('aprobado_por'), d.get('observaciones'), user))
            accion = 'creado'

        # Audit log
        try:
            import json as _json
            c.execute("""
                INSERT INTO audit_log (usuario, accion, registro_id, despues)
                VALUES (?, 'SGD_GUARDAR', ?, ?)
            """, (user, codigo, _json.dumps({'version': version, 'estado': estado, 'titulo': titulo})))
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        log.exception('sgd_crear_o_actualizar fallo: %s', e)
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'codigo': codigo, 'accion': accion})


@bp.route('/api/aseguramiento/sgd/conflictos', methods=['GET'])
def sgd_conflictos_listar():
    """Lista los conflictos detectados (códigos repetidos con temas distintos)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    rows = get_db().execute("""
        SELECT id, codigo, archivos_detectados, temas_detectados,
               estado, resolucion, resuelto_por, resuelto_at, creado_en
        FROM sgd_conflictos
        ORDER BY estado, codigo
        LIMIT 100
    """).fetchall()
    return jsonify({'items': [{
        'id': r[0], 'codigo': r[1], 'archivos': r[2], 'temas': r[3],
        'estado': r[4], 'resolucion': r[5], 'resuelto_por': r[6],
        'resuelto_at': r[7], 'creado_en': r[8],
    } for r in rows]})


@bp.route('/api/aseguramiento/sgd/importar', methods=['POST'])
def sgd_importar():
    """Importa documentos masivos del SGD (1-shot del directorio Downloads).

    Body: { items: [{codigo, area, tipo_doc, numero, subtipo, titulo,
                       version, archivo_origen, padre_codigo, ...}] }
    Idempotente · usa INSERT OR IGNORE.
    """
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin puede importar SGD masivo'}), 403
    d = request.get_json(silent=True) or {}
    items = d.get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'items debe ser lista no vacía'}), 400

    conn = get_db(); c = conn.cursor()
    insertados = 0
    saltados = 0
    errores = []
    for it in items[:5000]:
        try:
            codigo = (it.get('codigo') or '').strip().upper()
            if not codigo:
                errores.append(f'sin codigo: {it}')
                continue
            parts = codigo.split('-')
            if len(parts) < 3:
                errores.append(f'codigo invalido: {codigo}')
                continue
            area = parts[0]; tipo_doc = parts[1]
            try:
                numero = int(parts[2])
            except (ValueError, IndexError):
                errores.append(f'numero invalido en {codigo}')
                continue
            subtipo = parts[3] if len(parts) > 3 else None
            padre_codigo = '-'.join(parts[:3]) if subtipo else None
            titulo = (it.get('titulo') or codigo).strip()[:300]
            r = c.execute("""
                INSERT OR IGNORE INTO sgd_documentos
                  (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                   titulo, version_actual, archivo_origen, estado, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                  titulo, (it.get('version') or '1'),
                  (it.get('archivo_origen') or '')[:300],
                  (it.get('estado') or 'vigente'), user))
            if r.rowcount > 0:
                insertados += 1
            else:
                saltados += 1
        except Exception as e:
            errores.append(f'{it.get("codigo","?")}: {str(e)[:80]}')
    conn.commit()
    return jsonify({
        'ok': True,
        'insertados': insertados,
        'saltados_ya_existian': saltados,
        'errores': errores[:30],
    })


@bp.route('/api/aseguramiento/sgd/conflictos/<int:conflicto_id>/resolver', methods=['POST'])
def sgd_conflicto_resolver(conflicto_id):
    """Marca un conflicto como resuelto."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    resolucion = (d.get('resolucion') or '').strip()
    if len(resolucion) < 10:
        return jsonify({'error': 'resolucion requerida (>=10 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    r = c.execute("""
        UPDATE sgd_conflictos
        SET estado='resuelto', resolucion=?, resuelto_por=?,
            resuelto_at=datetime('now')
        WHERE id=?
    """, (resolucion, user, conflicto_id))
    if r.rowcount == 0:
        return jsonify({'error': 'conflicto no encontrado'}), 404
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════
# CAPACITACIONES SOPs · evidencia INVIMA
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/aseguramiento/capacitaciones/asignar', methods=['POST'])
def capacitaciones_asignar():
    """Asigna lectura/firma de un SOP a personas o área completa.

    Body: {
      sgd_codigo (req), sgd_version (req),
      personas: [usernames] o area: 'COC' (mutually exclusive),
      fecha_limite (opt),
    }
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    sgd_codigo = (d.get('sgd_codigo') or '').strip().upper()
    sgd_version = (d.get('sgd_version') or '').strip()
    personas = d.get('personas') or []
    fecha_limite = (d.get('fecha_limite') or '').strip() or None
    if not sgd_codigo or not sgd_version:
        return jsonify({'error': 'sgd_codigo y sgd_version requeridos'}), 400
    if not isinstance(personas, list) or not personas:
        return jsonify({'error': 'personas debe ser lista no vacía'}), 400

    conn = get_db(); c = conn.cursor()
    # Verificar que el doc existe
    if not c.execute("SELECT 1 FROM sgd_documentos WHERE codigo=?", (sgd_codigo,)).fetchone():
        return jsonify({'error': f'documento {sgd_codigo} no existe'}), 404

    asignados = 0
    saltados = 0
    for p in personas:
        p = (p or '').strip().lower()
        if not p: continue
        r = c.execute("""
            INSERT OR IGNORE INTO sgd_capacitaciones
              (sgd_codigo, sgd_version, persona_username, fecha_limite, asignado_por, estado)
            VALUES (?, ?, ?, ?, ?, 'asignada')
        """, (sgd_codigo, sgd_version, p, fecha_limite, user))
        if r.rowcount > 0:
            asignados += 1
        else:
            saltados += 1
    conn.commit()
    return jsonify({
        'ok': True, 'asignados': asignados,
        'saltados_ya_existian': saltados,
    })


@bp.route('/api/aseguramiento/capacitaciones/firmar', methods=['POST'])
def capacitaciones_firmar():
    """La persona firma haber leído/comprendido el SOP.

    Body: { sgd_codigo, sgd_version }
    El usuario firma con su propia sesión (no admin firma por otro).
    """
    user = session.get('compras_user', '')
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json(silent=True) or {}
    sgd_codigo = (d.get('sgd_codigo') or '').strip().upper()
    sgd_version = (d.get('sgd_version') or '').strip()
    if not sgd_codigo or not sgd_version:
        return jsonify({'error': 'sgd_codigo y sgd_version requeridos'}), 400

    import hmac as _hmac
    import hashlib
    secret = (os.environ.get('SECRET_KEY','') or 'fallback').encode()
    msg = f'{sgd_codigo}|{sgd_version}|{user}|{datetime.now().isoformat()}'.encode()
    firma_hash = _hmac.new(secret, msg, hashlib.sha256).hexdigest()[:32]

    conn = get_db(); c = conn.cursor()
    r = c.execute("""
        UPDATE sgd_capacitaciones
        SET leido_at=COALESCE(leido_at, datetime('now')),
            firmado_at=datetime('now'),
            firma_hash=?,
            estado='firmada'
        WHERE sgd_codigo=? AND sgd_version=? AND persona_username=?
    """, (firma_hash, sgd_codigo, sgd_version, user))
    if r.rowcount == 0:
        return jsonify({'error': 'no tienes esta capacitación asignada'}), 404
    conn.commit()
    return jsonify({'ok': True, 'firma_hash': firma_hash})


@bp.route('/api/aseguramiento/capacitaciones/mias', methods=['GET'])
def capacitaciones_mias():
    """Capacitaciones del usuario actual."""
    user = session.get('compras_user', '')
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    rows = get_db().execute("""
        SELECT cap.id, cap.sgd_codigo, cap.sgd_version,
               doc.titulo, doc.archivo_pdf_url,
               cap.asignado_at, cap.leido_at, cap.firmado_at,
               cap.estado, cap.fecha_limite
        FROM sgd_capacitaciones cap
        LEFT JOIN sgd_documentos doc ON doc.codigo = cap.sgd_codigo
        WHERE cap.persona_username = ?
        ORDER BY CASE cap.estado
                   WHEN 'asignada' THEN 0 WHEN 'leida' THEN 1
                   WHEN 'vencida' THEN 2 ELSE 3 END,
                 cap.asignado_at DESC
        LIMIT 200
    """, (user,)).fetchall()
    return jsonify({'items': [{
        'id': r[0], 'sgd_codigo': r[1], 'sgd_version': r[2],
        'titulo': r[3], 'archivo_pdf_url': r[4],
        'asignado_at': r[5], 'leido_at': r[6], 'firmado_at': r[7],
        'estado': r[8], 'fecha_limite': r[9],
    } for r in rows]})
