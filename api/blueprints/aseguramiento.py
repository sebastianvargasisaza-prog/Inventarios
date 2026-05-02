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

    Body: {
        items: [{codigo, area, tipo_doc, numero, subtipo, titulo,
                  version, archivo_origen, padre_codigo, ...}],
        conflictos: [{codigo, archivos, temas}]   # opcional
    }
    Idempotente · usa INSERT OR IGNORE en docs Y en conflictos (por código).
    """
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin puede importar SGD masivo'}), 403
    d = request.get_json(silent=True) or {}
    items = d.get('items') or []
    conflictos = d.get('conflictos') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'items debe ser lista no vacía'}), 400

    conn = get_db(); c = conn.cursor()
    insertados = 0
    saltados = 0
    conflictos_insertados = 0
    conflictos_saltados = 0
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

    # Persistir conflictos detectados (si vienen en el payload).
    # Idempotente: si ya hay un conflicto pendiente para ese código, no
    # duplicar. Se actualiza temas/archivos por si el set cambió.
    for cf in (conflictos or [])[:200]:
        try:
            cod = (cf.get('codigo') or '').strip().upper()
            if not cod:
                continue
            archivos = (cf.get('archivos') or '')[:1000]
            temas = (cf.get('temas') or '')[:1000]
            existing = c.execute(
                "SELECT id FROM sgd_conflictos WHERE codigo=? AND estado='pendiente' LIMIT 1",
                (cod,)
            ).fetchone()
            if existing:
                c.execute("""
                    UPDATE sgd_conflictos
                    SET archivos_detectados=?, temas_detectados=?
                    WHERE id=?
                """, (archivos, temas, existing[0]))
                conflictos_saltados += 1
            else:
                c.execute("""
                    INSERT INTO sgd_conflictos
                      (codigo, archivos_detectados, temas_detectados, estado)
                    VALUES (?, ?, ?, 'pendiente')
                """, (cod, archivos, temas))
                conflictos_insertados += 1
        except Exception as e:
            errores.append(f'conflicto {cf.get("codigo","?")}: {str(e)[:80]}')

    conn.commit()
    return jsonify({
        'ok': True,
        'insertados': insertados,
        'saltados_ya_existian': saltados,
        'conflictos_insertados': conflictos_insertados,
        'conflictos_actualizados': conflictos_saltados,
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


# ════════════════════════════════════════════════════════════════════════
# DESVIACIONES · ASG-PRO-001
# Workflow: detectada → clasificada (24h) → en_investigación (5d) →
# capa_propuesto (10-15d) → cerrada (con verificación efectividad)
# ════════════════════════════════════════════════════════════════════════

def _generar_codigo_desviacion(c):
    """Genera código DESV-AAAA-NNNN secuencial por año."""
    anio = datetime.now().year
    row = c.execute("""
        SELECT codigo FROM desviaciones
        WHERE codigo LIKE ?
        ORDER BY id DESC LIMIT 1
    """, (f'DESV-{anio}-%',)).fetchone()
    if row and row[0]:
        try:
            ult = int(row[0].split('-')[-1])
            return f'DESV-{anio}-{ult+1:04d}'
        except (ValueError, IndexError):
            pass
    return f'DESV-{anio}-0001'


@bp.route('/api/aseguramiento/desviaciones', methods=['GET', 'POST'])
def desviaciones_endpoint():
    """GET: lista filtrable. POST: crea nueva desviación (cualquier user)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        descripcion = (d.get('descripcion') or '').strip()
        if len(descripcion) < 10:
            return jsonify({'error': 'descripcion requerida (≥10 chars)'}), 400
        tipo = (d.get('tipo') or 'otra').strip()
        valid_tipos = ('proceso','equipo','instalacion','sistema_agua','ambiental',
                        'documental','personal','materia_prima','envase','otra')
        if tipo not in valid_tipos:
            return jsonify({'error': f'tipo inválido. Uno de: {", ".join(valid_tipos)}'}), 400

        codigo = _generar_codigo_desviacion(c)
        try:
            c.execute("""
                INSERT INTO desviaciones
                  (codigo, fecha_deteccion, hora_deteccion, detectado_por,
                   tipo, area_origen, descripcion, contencion_inmediata,
                   impacto_producto, lotes_afectados, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'detectada')
            """, (codigo,
                  (d.get('hora_deteccion') or datetime.now().strftime('%H:%M')),
                  user, tipo,
                  (d.get('area_origen') or '').strip()[:80],
                  descripcion[:2000],
                  (d.get('contencion_inmediata') or '')[:1000],
                  1 if d.get('impacto_producto') else 0,
                  (d.get('lotes_afectados') or '')[:500]))
            desv_id = c.lastrowid
            # Evento inicial
            c.execute("""
                INSERT INTO desviaciones_eventos
                  (desviacion_id, evento_tipo, estado_nuevo, usuario, comentario)
                VALUES (?, 'detectada', 'detectada', ?, ?)
            """, (desv_id, user, 'Desviación reportada'))
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            log.exception('crear desviacion fallo: %s', e)
            return jsonify({'error': str(e)[:200]}), 500

        # Notificar a Calidad si parece crítica (impacto_producto o tipo crítico)
        if d.get('impacto_producto') or tipo in ('sistema_agua', 'materia_prima'):
            try:
                from blueprints.notif import push_notif_multi
                push_notif_multi(
                    ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                    'capa', f'⚠ Desviación {codigo} reportada · revisar y clasificar',
                    body=f'{tipo} · {(d.get("area_origen") or "")} · {descripcion[:140]}',
                    link='/aseguramiento', remitente=user, importante=True,
                )
            except Exception as _e:
                log.warning('notif desviacion fallo: %s', _e)

        return jsonify({'ok': True, 'id': desv_id, 'codigo': codigo}), 201

    # GET · lista con filtros
    estado = (request.args.get('estado') or '').strip()
    clasif = (request.args.get('clasificacion') or '').strip()
    area = (request.args.get('area') or '').strip()
    where = []; params = []
    if estado: where.append('estado=?'); params.append(estado)
    if clasif: where.append('clasificacion=?'); params.append(clasif)
    if area: where.append('area_origen=?'); params.append(area)
    sql = """SELECT id, codigo, fecha_deteccion, hora_deteccion, detectado_por,
                    tipo, area_origen, descripcion, clasificacion, estado,
                    impacto_producto, capa_responsable, capa_fecha_limite,
                    fecha_cierre,
                    CAST((julianday('now') - julianday(fecha_deteccion)) AS INTEGER) as dias_abierta
             FROM desviaciones"""
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_deteccion DESC, id DESC LIMIT 500'
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','fecha_deteccion','hora_deteccion','detectado_por',
            'tipo','area_origen','descripcion','clasificacion','estado',
            'impacto_producto','capa_responsable','capa_fecha_limite',
            'fecha_cierre','dias_abierta']
    items = [dict(zip(cols, r)) for r in rows]
    # KPIs rápidos
    kpis = {
        'total': len(items),
        'criticas_abiertas': sum(1 for it in items
                                  if it['clasificacion']=='critica' and it['estado']!='cerrada'),
        'sin_clasificar': sum(1 for it in items if not it['clasificacion']
                                                    and it['estado']!='rechazada'),
        'investigando': sum(1 for it in items if it['estado']=='en_investigacion'),
        'cerradas_30d': sum(1 for it in items
                             if it['estado']=='cerrada' and it.get('fecha_cierre')
                             and (it['fecha_cierre'] >= (datetime.now().date() - timedelta(days=30)).isoformat())),
    }
    return jsonify({'items': items, 'kpis': kpis})


@bp.route('/api/aseguramiento/desviaciones/<int:desv_id>', methods=['GET'])
def desviacion_detalle(desv_id):
    """Detalle completo + timeline de eventos."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT id, codigo, fecha_deteccion, hora_deteccion, detectado_por,
               tipo, area_origen, descripcion, contencion_inmediata,
               impacto_producto, lotes_afectados, clasificacion, clasificado_por,
               clasificado_at, justificacion_clasificacion,
               metodo_investigacion, causa_raiz_descripcion, investigado_por,
               investigacion_at, capa_descripcion, capa_responsable,
               capa_fecha_limite, capa_implementado_at, verificacion_efectividad,
               verificado_at, verificado_por, efectividad_ok,
               estado, fecha_cierre, cerrado_por, observaciones_cierre,
               creado_en, actualizado_en
        FROM desviaciones WHERE id=?
    """, (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'desviacion no encontrada'}), 404
    cols = ['id','codigo','fecha_deteccion','hora_deteccion','detectado_por',
            'tipo','area_origen','descripcion','contencion_inmediata',
            'impacto_producto','lotes_afectados','clasificacion','clasificado_por',
            'clasificado_at','justificacion_clasificacion',
            'metodo_investigacion','causa_raiz_descripcion','investigado_por',
            'investigacion_at','capa_descripcion','capa_responsable',
            'capa_fecha_limite','capa_implementado_at','verificacion_efectividad',
            'verificado_at','verificado_por','efectividad_ok',
            'estado','fecha_cierre','cerrado_por','observaciones_cierre',
            'creado_en','actualizado_en']
    detalle = dict(zip(cols, row))

    eventos = c.execute("""
        SELECT evento_tipo, estado_anterior, estado_nuevo, usuario, comentario, creado_en
        FROM desviaciones_eventos WHERE desviacion_id=?
        ORDER BY id ASC
    """, (desv_id,)).fetchall()
    detalle['timeline'] = [{
        'evento_tipo': r[0], 'estado_anterior': r[1], 'estado_nuevo': r[2],
        'usuario': r[3], 'comentario': r[4], 'creado_en': r[5],
    } for r in eventos]
    return jsonify(detalle)


@bp.route('/api/aseguramiento/desviaciones/<int:desv_id>/clasificar', methods=['POST'])
def desviacion_clasificar(desv_id):
    """Clasifica (crítica/mayor/menor/informativa). RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    clasif = (d.get('clasificacion') or '').strip()
    if clasif not in ('critica','mayor','menor','informativa'):
        return jsonify({'error': 'clasificacion inválida'}), 400
    just = (d.get('justificacion') or '').strip()
    if len(just) < 10:
        return jsonify({'error': 'justificacion requerida (≥10 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM desviaciones WHERE id=?", (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant not in ('detectada', 'clasificada'):  # idempotente reclasificar mientras no esté investigando
        return jsonify({'error': f'no se puede clasificar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE desviaciones
        SET clasificacion=?, justificacion_clasificacion=?,
            clasificado_por=?, clasificado_at=datetime('now'),
            estado='clasificada', actualizado_en=datetime('now')
        WHERE id=?
    """, (clasif, just, user, desv_id))
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'clasificada', ?, 'clasificada', ?, ?)
    """, (desv_id, estado_ant, user, f'Clasificada como {clasif}: {just[:200]}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/desviaciones/<int:desv_id>/investigar', methods=['POST'])
def desviacion_investigar(desv_id):
    """Registra causa raíz + método investigación. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    metodo = (d.get('metodo_investigacion') or '').strip()
    if metodo not in ('5_porques','ishikawa','arbol_decision','otro'):
        return jsonify({'error': 'metodo_investigacion inválido'}), 400
    causa = (d.get('causa_raiz') or '').strip()
    if len(causa) < 20:
        return jsonify({'error': 'causa_raiz requerida (≥20 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM desviaciones WHERE id=?", (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant not in ('clasificada', 'en_investigacion'):
        return jsonify({'error': f'no se puede investigar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE desviaciones
        SET metodo_investigacion=?, causa_raiz_descripcion=?,
            investigado_por=?, investigacion_at=datetime('now'),
            estado='en_investigacion', actualizado_en=datetime('now')
        WHERE id=?
    """, (metodo, causa, user, desv_id))
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'investigada', ?, 'en_investigacion', ?, ?)
    """, (desv_id, estado_ant, user, f'Causa raíz ({metodo}): {causa[:200]}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/desviaciones/<int:desv_id>/capa', methods=['POST'])
def desviacion_capa(desv_id):
    """Define plan CAPA (acciones correctivas/preventivas). RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    capa = (d.get('capa_descripcion') or '').strip()
    if len(capa) < 20:
        return jsonify({'error': 'capa_descripcion requerida (≥20 chars)'}), 400
    responsable = (d.get('capa_responsable') or '').strip()
    if not responsable:
        return jsonify({'error': 'capa_responsable requerido'}), 400
    fecha_limite = (d.get('capa_fecha_limite') or '').strip() or None
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM desviaciones WHERE id=?", (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant not in ('en_investigacion', 'capa_propuesto'):
        return jsonify({'error': f'no se puede definir CAPA en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE desviaciones
        SET capa_descripcion=?, capa_responsable=?, capa_fecha_limite=?,
            estado='capa_propuesto', actualizado_en=datetime('now')
        WHERE id=?
    """, (capa, responsable, fecha_limite, desv_id))
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'capa_propuesto', ?, 'capa_propuesto', ?, ?)
    """, (desv_id, estado_ant, user,
          f'CAPA: {capa[:150]} · resp: {responsable} · límite: {fecha_limite or "sin definir"}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/desviaciones/<int:desv_id>/cerrar', methods=['POST'])
def desviacion_cerrar(desv_id):
    """Cierra la desviación con verificación de efectividad. RBAC Director Técnico/Admin.

    Requiere: efectividad_ok (bool), verificacion_efectividad (texto >=20),
    observaciones_cierre. Audit log obligatorio.
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin pueden cerrar (regulación INVIMA)'}), 403
    d = request.get_json(silent=True) or {}
    if d.get('efectividad_ok') is None:
        return jsonify({'error': 'efectividad_ok (true/false) requerido'}), 400
    verificacion = (d.get('verificacion_efectividad') or '').strip()
    if len(verificacion) < 20:
        return jsonify({'error': 'verificacion_efectividad requerida (≥20 chars)'}), 400
    obs = (d.get('observaciones_cierre') or '').strip()

    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM desviaciones WHERE id=?", (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant == 'cerrada':
        return jsonify({'error': 'ya está cerrada'}), 409
    if estado_ant not in ('capa_propuesto', 'capa_implementado'):
        return jsonify({'error': f'no se puede cerrar en estado {estado_ant} · primero CAPA'}), 409

    c.execute("""
        UPDATE desviaciones
        SET estado='cerrada', fecha_cierre=date('now'), cerrado_por=?,
            verificacion_efectividad=?, verificado_at=datetime('now'), verificado_por=?,
            efectividad_ok=?, observaciones_cierre=?,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (user, verificacion, user, 1 if d.get('efectividad_ok') else 0,
          obs[:500] or None, desv_id))
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'cerrada', ?, 'cerrada', ?, ?)
    """, (desv_id, estado_ant, user,
          f'Cerrada · efectividad {"OK" if d.get("efectividad_ok") else "NO_OK"}: {verificacion[:200]}'))
    # Audit log INVIMA
    try:
        import json as _json
        c.execute("""
            INSERT INTO audit_log (usuario, accion, registro_id, antes, despues)
            VALUES (?, 'CERRAR_DESVIACION', ?, ?, ?)
        """, (user, row[1] or str(desv_id),
              _json.dumps({'estado_anterior': estado_ant}),
              _json.dumps({'efectividad_ok': bool(d.get('efectividad_ok')),
                            'verificacion': verificacion[:500],
                            'observaciones': obs[:500]})))
    except Exception as _e:
        log.debug('audit cerrar desviacion fallo: %s', _e)
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════
# CONTROL DE CAMBIOS · ASG-PRO-007
# Workflow: solicitado → en_evaluacion (5d) → aprobado/rechazado →
# en_implementacion → implementado → cerrado (con verificación post)
# Si toca BPM → notificación INVIMA obligatoria.
# ════════════════════════════════════════════════════════════════════════

def _generar_codigo_cambio(c):
    """Genera código CHG-AAAA-NNNN secuencial por año."""
    anio = datetime.now().year
    row = c.execute("""
        SELECT codigo FROM control_cambios
        WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1
    """, (f'CHG-{anio}-%',)).fetchone()
    if row and row[0]:
        try:
            return f'CHG-{anio}-{int(row[0].split("-")[-1])+1:04d}'
        except (ValueError, IndexError):
            pass
    return f'CHG-{anio}-0001'


@bp.route('/api/aseguramiento/cambios', methods=['GET', 'POST'])
def cambios_endpoint():
    """GET: lista filtrable. POST: nueva solicitud (cualquier user)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        titulo = (d.get('titulo') or '').strip()
        descripcion = (d.get('descripcion') or '').strip()
        if len(titulo) < 5:
            return jsonify({'error': 'titulo requerido (≥5 chars)'}), 400
        if len(descripcion) < 20:
            return jsonify({'error': 'descripcion requerida (≥20 chars)'}), 400
        tipo = (d.get('tipo') or 'otro').strip()
        valid_tipos = ('formulacion','proceso','equipo','instalacion',
                        'proveedor','documental','sistema','envase','otro')
        if tipo not in valid_tipos:
            return jsonify({'error': f'tipo inválido. Uno de: {", ".join(valid_tipos)}'}), 400

        codigo = _generar_codigo_cambio(c)
        try:
            c.execute("""
                INSERT INTO control_cambios
                  (codigo, fecha_solicitud, solicitado_por, tipo, titulo,
                   descripcion, justificacion, areas_afectadas,
                   impacto_bpm, impacto_regulatorio, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado')
            """, (codigo, user, tipo, titulo[:200], descripcion[:3000],
                  (d.get('justificacion') or '')[:1000],
                  (d.get('areas_afectadas') or '')[:300],
                  1 if d.get('impacto_bpm') else 0,
                  1 if d.get('impacto_regulatorio') else 0))
            cid = c.lastrowid
            c.execute("""
                INSERT INTO control_cambios_eventos
                  (cambio_id, evento_tipo, estado_nuevo, usuario, comentario)
                VALUES (?, 'solicitado', 'solicitado', ?, ?)
            """, (cid, user, f'Solicitud de cambio: {titulo[:200]}'))
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            log.exception('crear cambio fallo: %s', e)
            return jsonify({'error': str(e)[:200]}), 500

        # Notificar a Calidad si declara impacto BPM/regulatorio
        if d.get('impacto_bpm') or d.get('impacto_regulatorio') or tipo == 'formulacion':
            try:
                from blueprints.notif import push_notif_multi
                push_notif_multi(
                    ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                    'capa', f'🔄 Cambio {codigo} pendiente de evaluar',
                    body=f'{tipo} · {titulo[:140]}',
                    link='/aseguramiento', remitente=user,
                    importante=bool(d.get('impacto_bpm')),
                )
            except Exception as _e:
                log.warning('notif cambio fallo: %s', _e)

        return jsonify({'ok': True, 'id': cid, 'codigo': codigo}), 201

    # GET · lista
    estado = (request.args.get('estado') or '').strip()
    severidad = (request.args.get('severidad') or '').strip()
    where = []; params = []
    if estado: where.append('estado=?'); params.append(estado)
    if severidad: where.append('severidad=?'); params.append(severidad)
    sql = """SELECT id, codigo, fecha_solicitud, solicitado_por, tipo, titulo,
                    severidad, estado, impacto_bpm, requiere_invima,
                    aprobado_por, fecha_implementacion_propuesta, fecha_cierre,
                    CAST((julianday('now') - julianday(fecha_solicitud)) AS INTEGER) as dias_abierto
             FROM control_cambios"""
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_solicitud DESC, id DESC LIMIT 500'
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','fecha_solicitud','solicitado_por','tipo','titulo',
            'severidad','estado','impacto_bpm','requiere_invima',
            'aprobado_por','fecha_implementacion_propuesta','fecha_cierre','dias_abierto']
    items = [dict(zip(cols, r)) for r in rows]
    kpis = {
        'total': len(items),
        'sin_evaluar': sum(1 for it in items if it['estado'] == 'solicitado'),
        'en_evaluacion': sum(1 for it in items if it['estado'] == 'en_evaluacion'),
        'aprobados_pendientes': sum(1 for it in items if it['estado'] in ('aprobado','en_implementacion')),
        'requieren_invima': sum(1 for it in items
                                  if it['requiere_invima'] and it['estado'] not in ('cerrado','rechazado')),
        'cerrados_30d': sum(1 for it in items
                              if it['estado']=='cerrado' and it.get('fecha_cierre')
                              and it['fecha_cierre'] >= (datetime.now().date() - timedelta(days=30)).isoformat()),
    }
    return jsonify({'items': items, 'kpis': kpis})


@bp.route('/api/aseguramiento/cambios/<int:cid>', methods=['GET'])
def cambio_detalle(cid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT * FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row:
        return jsonify({'error': 'cambio no encontrado'}), 404
    cols = [d[0] for d in c.description]
    detalle = dict(zip(cols, row))
    eventos = c.execute("""
        SELECT evento_tipo, estado_anterior, estado_nuevo, usuario, comentario, creado_en
        FROM control_cambios_eventos WHERE cambio_id=? ORDER BY id ASC
    """, (cid,)).fetchall()
    detalle['timeline'] = [{
        'evento_tipo': r[0], 'estado_anterior': r[1], 'estado_nuevo': r[2],
        'usuario': r[3], 'comentario': r[4], 'creado_en': r[5],
    } for r in eventos]
    return jsonify(detalle)


@bp.route('/api/aseguramiento/cambios/<int:cid>/evaluar', methods=['POST'])
def cambio_evaluar(cid):
    """Evalúa impacto del cambio. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    severidad = (d.get('severidad') or '').strip()
    if severidad not in ('mayor','menor'):
        return jsonify({'error': 'severidad debe ser mayor/menor'}), 400
    eval_desc = (d.get('evaluacion_descripcion') or '').strip()
    if len(eval_desc) < 20:
        return jsonify({'error': 'evaluacion_descripcion requerida (≥20 chars)'}), 400
    requiere_invima = bool(d.get('requiere_invima'))
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('solicitado', 'en_evaluacion'):
        return jsonify({'error': f'no se puede evaluar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE control_cambios
        SET severidad=?, evaluacion_descripcion=?, evaluado_por=?,
            evaluado_at=datetime('now'), requiere_invima=?,
            estado='en_evaluacion', actualizado_en=datetime('now')
        WHERE id=?
    """, (severidad, eval_desc, user, 1 if requiere_invima else 0, cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'evaluado', ?, 'en_evaluacion', ?, ?)
    """, (cid, estado_ant, user,
          f'Severidad {severidad}'+(' · Requiere INVIMA' if requiere_invima else '')+f': {eval_desc[:200]}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/cambios/<int:cid>/aprobar', methods=['POST'])
def cambio_aprobar(cid):
    """Aprueba o rechaza el cambio. RBAC Admin/Director Técnico."""
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({'error': 'Solo Admin o Calidad pueden aprobar/rechazar'}), 403
    d = request.get_json(silent=True) or {}
    decision = (d.get('decision') or '').strip()
    if decision not in ('aprobar', 'rechazar'):
        return jsonify({'error': 'decision debe ser aprobar/rechazar'}), 400
    obs = (d.get('observaciones') or '').strip()
    if len(obs) < 10:
        return jsonify({'error': 'observaciones requeridas (≥10 chars)'}), 400
    plan = (d.get('plan_implementacion') or '').strip() if decision == 'aprobar' else None
    fecha_imp = (d.get('fecha_implementacion_propuesta') or '').strip() or None
    responsable = (d.get('responsable_implementacion') or '').strip() or None

    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, requiere_invima, codigo FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant != 'en_evaluacion':
        return jsonify({'error': f'no se puede aprobar/rechazar en estado {estado_ant} · debe estar en_evaluacion'}), 409

    nuevo_estado = 'aprobado' if decision == 'aprobar' else 'rechazado'
    if decision == 'aprobar' and (not plan or len(plan) < 20):
        return jsonify({'error': 'plan_implementacion requerido (≥20 chars) si aprueba'}), 400

    c.execute("""
        UPDATE control_cambios
        SET aprobado_por=?, aprobado_at=datetime('now'),
            aprobacion_observaciones=?, plan_implementacion=?,
            fecha_implementacion_propuesta=?, responsable_implementacion=?,
            estado=?, actualizado_en=datetime('now')
        WHERE id=?
    """, (user, obs, plan, fecha_imp, responsable, nuevo_estado, cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cid, decision, estado_ant, nuevo_estado, user, obs[:200]))
    # Audit
    try:
        import json as _json
        c.execute("""
            INSERT INTO audit_log (usuario, accion, registro_id, despues)
            VALUES (?, 'CAMBIO_APROBACION', ?, ?)
        """, (user, row[2] or str(cid),
              _json.dumps({'decision': decision, 'observaciones': obs[:300]})))
    except Exception:
        pass
    conn.commit()

    # Si requiere INVIMA → recordatorio
    if decision == 'aprobar' and row[1]:
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['aseguramiento.espagiria','sebastian'],
                'capa', f'⚠ Cambio {row[2]} aprobado · REQUIERE NOTIFICACIÓN INVIMA',
                body='Notificar a INVIMA antes de implementar (Resolución 2214/2021).',
                link='/aseguramiento', remitente=user, importante=True,
            )
        except Exception as _e:
            log.warning('notif INVIMA cambio fallo: %s', _e)

    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/cambios/<int:cid>/notificar-invima', methods=['POST'])
def cambio_notificar_invima(cid):
    """Marca que se notificó a INVIMA (con referencia)."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    ref = (d.get('referencia') or '').strip()
    if not ref:
        return jsonify({'error': 'referencia (radicado/oficio) requerido'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, requiere_invima FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    if not row[1]:
        return jsonify({'error': 'este cambio no requiere INVIMA'}), 400
    c.execute("""
        UPDATE control_cambios
        SET notificacion_invima_at=datetime('now'),
            notificacion_invima_ref=?, actualizado_en=datetime('now')
        WHERE id=?
    """, (ref[:200], cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, usuario, comentario)
        VALUES (?, 'notificado_invima', ?, ?)
    """, (cid, user, f'Notificado INVIMA · ref: {ref[:100]}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/cambios/<int:cid>/implementar', methods=['POST'])
def cambio_implementar(cid):
    """Marca cambio como implementado. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    obs = (d.get('observaciones') or '').strip()
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('aprobado', 'en_implementacion'):
        return jsonify({'error': f'no se puede implementar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE control_cambios
        SET implementado_at=datetime('now'), implementado_por=?,
            estado='implementado', actualizado_en=datetime('now')
        WHERE id=?
    """, (user, cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'implementado', ?, 'implementado', ?, ?)
    """, (cid, estado_ant, user, obs[:200] or 'Implementación completada'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/cambios/<int:cid>/cerrar', methods=['POST'])
def cambio_cerrar(cid):
    """Cierra el cambio con verificación post. Audit log INVIMA."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    if d.get('verificacion_ok') is None:
        return jsonify({'error': 'verificacion_ok (true/false) requerido'}), 400
    verif = (d.get('verificacion_post') or '').strip()
    if len(verif) < 20:
        return jsonify({'error': 'verificacion_post requerida (≥20 chars)'}), 400
    obs = (d.get('observaciones_cierre') or '').strip()
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM control_cambios WHERE id=?", (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant == 'cerrado':
        return jsonify({'error': 'ya está cerrado'}), 409
    if estado_ant != 'implementado':
        return jsonify({'error': f'debe estar implementado primero · actualmente {estado_ant}'}), 409

    c.execute("""
        UPDATE control_cambios
        SET verificacion_post=?, verificado_por=?, verificado_at=datetime('now'),
            verificacion_ok=?, observaciones_cierre=?,
            estado='cerrado', fecha_cierre=date('now'), cerrado_por=?,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (verif, user, 1 if d.get('verificacion_ok') else 0,
          obs[:500] or None, user, cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'cerrado', ?, 'cerrado', ?, ?)
    """, (cid, estado_ant, user,
          f'Cerrado · verif {"OK" if d.get("verificacion_ok") else "NO_OK"}: {verif[:200]}'))
    try:
        import json as _json
        c.execute("""
            INSERT INTO audit_log (usuario, accion, registro_id, despues)
            VALUES (?, 'CERRAR_CAMBIO', ?, ?)
        """, (user, row[1] or str(cid),
              _json.dumps({'verificacion_ok': bool(d.get('verificacion_ok')),
                            'verificacion': verif[:500]})))
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True})


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
