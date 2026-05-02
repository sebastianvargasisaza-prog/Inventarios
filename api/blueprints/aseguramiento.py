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
from audit_helpers import (
    audit_log as _audit_log_global,
    intentar_insert_con_retry as _retry_global,
    siguiente_codigo_secuencial as _siguiente_codigo_global,
)
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


# Helpers locales son ahora wrappers thin del módulo global api/audit_helpers.py
# (extraído 2-may-2026 para uso compartido en compras, contabilidad, planta, calidad,
# compliance). Mantienen compatibilidad con call-sites existentes en este blueprint.
def _siguiente_codigo_secuencial(c, prefijo, tabla, anio=None):
    return _siguiente_codigo_global(c, prefijo, tabla, anio=anio)


def _intentar_insert_con_retry(insert_fn, *, max_intentos=5):
    return _retry_global(insert_fn, max_intentos=max_intentos)


def _audit_log(c, *, usuario, accion, registro_id, tabla=None,
                antes=None, despues=None, detalle=None):
    return _audit_log_global(c, usuario=usuario, accion=accion,
                              registro_id=registro_id, tabla=tabla,
                              antes=antes, despues=despues, detalle=detalle)


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

    # Desviaciones (ASG-PRO-001)
    try:
        dv = c.execute("""
            SELECT
              COUNT(*) as total,
              COUNT(CASE WHEN estado='detectada' THEN 1 END) as sin_clasificar,
              COUNT(CASE WHEN clasificacion='critica'
                          AND estado NOT IN ('cerrada','rechazada') THEN 1 END) as criticas_abiertas,
              COUNT(CASE WHEN estado IN ('en_investigacion','clasificada') THEN 1 END) as investigando,
              COUNT(CASE WHEN estado='cerrada'
                          AND date(fecha_cierre) >= date('now','-30 days') THEN 1 END) as cerradas_30d
            FROM desviaciones
        """).fetchone()
        out['desviaciones'] = {
            'total': dv[0] or 0, 'sin_clasificar': dv[1] or 0,
            'criticas_abiertas': dv[2] or 0, 'investigando': dv[3] or 0,
            'cerradas_30d': dv[4] or 0,
        }
    except Exception:
        out['desviaciones'] = {}

    # Control de cambios (ASG-PRO-007)
    try:
        cm = c.execute("""
            SELECT
              COUNT(*) as total,
              COUNT(CASE WHEN estado='solicitado' THEN 1 END) as sin_evaluar,
              COUNT(CASE WHEN estado IN ('aprobado','en_implementacion') THEN 1 END) as aprobados_pendientes,
              COUNT(CASE WHEN requiere_invima=1
                          AND estado NOT IN ('cerrado','rechazado')
                          AND notificacion_invima_at IS NULL THEN 1 END) as invima_pendiente,
              COUNT(CASE WHEN estado='cerrado'
                          AND date(fecha_cierre) >= date('now','-30 days') THEN 1 END) as cerrados_30d
            FROM control_cambios
        """).fetchone()
        out['cambios'] = {
            'total': cm[0] or 0, 'sin_evaluar': cm[1] or 0,
            'aprobados_pendientes': cm[2] or 0, 'invima_pendiente': cm[3] or 0,
            'cerrados_30d': cm[4] or 0,
        }
    except Exception:
        out['cambios'] = {}

    # Quejas de cliente (ASG-PRO-013)
    try:
        qc = c.execute("""
            SELECT
              COUNT(*) as total,
              COUNT(CASE WHEN estado='nueva' THEN 1 END) as nuevas,
              COUNT(CASE WHEN estado='respondida' THEN 1 END) as pendientes_cierre,
              COUNT(CASE WHEN (severidad='critica' OR impacto_salud=1)
                          AND estado NOT IN ('cerrada','rechazada') THEN 1 END) as criticas_abiertas,
              COUNT(CASE WHEN estado='cerrada'
                          AND date(fecha_cierre) >= date('now','-30 days') THEN 1 END) as cerradas_30d
            FROM quejas_clientes
        """).fetchone()
        out['quejas'] = {
            'total': qc[0] or 0, 'nuevas': qc[1] or 0,
            'pendientes_cierre': qc[2] or 0, 'criticas_abiertas': qc[3] or 0,
            'cerradas_30d': qc[4] or 0,
        }
    except Exception:
        out['quejas'] = {}

    # Recalls (ASG-PRO-004)
    try:
        rcl = c.execute("""
            SELECT
              COUNT(*) as total,
              COUNT(CASE WHEN estado='iniciado' THEN 1 END) as sin_clasificar,
              COUNT(CASE WHEN clase_recall='clase_I'
                          AND estado NOT IN ('cerrado','cancelado') THEN 1 END) as clase_I_abiertos,
              COUNT(CASE WHEN estado IN ('iniciado','clasificado')
                          AND notificacion_invima_at IS NULL THEN 1 END) as invima_pendiente,
              COUNT(CASE WHEN estado='en_recoleccion' THEN 1 END) as en_recoleccion,
              COUNT(CASE WHEN estado='cerrado'
                          AND date(fecha_cierre) >= date('now','-30 days') THEN 1 END) as cerrados_30d
            FROM recalls
        """).fetchone()
        out['recalls'] = {
            'total': rcl[0] or 0, 'sin_clasificar': rcl[1] or 0,
            'clase_I_abiertos': rcl[2] or 0, 'invima_pendiente': rcl[3] or 0,
            'en_recoleccion': rcl[4] or 0, 'cerrados_30d': rcl[5] or 0,
        }
    except Exception:
        out['recalls'] = {}

    # Alertas críticas consolidadas (top 5 más urgentes)
    alertas = []
    try:
        # Recalls Clase I sin INVIMA → super crítica
        for r in c.execute("""
            SELECT codigo, producto FROM recalls
            WHERE clase_recall='clase_I' AND notificacion_invima_at IS NULL
              AND estado NOT IN ('cerrado','cancelado')
            LIMIT 3
        """).fetchall():
            alertas.append({'tipo': 'recall_clase_I_sin_invima', 'severidad': 'super_critica',
                            'codigo': r[0], 'descripcion': f'Clase I sin INVIMA: {(r[1] or "")[:60]}',
                            'modulo': 'recalls'})
        # Desviaciones críticas sin investigar
        for r in c.execute("""
            SELECT codigo, descripcion FROM desviaciones
            WHERE clasificacion='critica' AND estado IN ('clasificada','detectada')
              AND date(fecha_deteccion) <= date('now','-2 days')
            LIMIT 3
        """).fetchall():
            alertas.append({'tipo': 'desviacion_critica_sin_investigar', 'severidad': 'critica',
                            'codigo': r[0], 'descripcion': (r[1] or '')[:60],
                            'modulo': 'desviaciones'})
        # Quejas con impacto salud sin responder
        for r in c.execute("""
            SELECT codigo, cliente_nombre FROM quejas_clientes
            WHERE impacto_salud=1 AND estado IN ('nueva','en_triaje','en_investigacion')
              AND date(fecha_recepcion) <= date('now','-2 days')
            LIMIT 3
        """).fetchall():
            alertas.append({'tipo': 'queja_salud_sin_responder', 'severidad': 'critica',
                            'codigo': r[0], 'descripcion': f'Cliente: {(r[1] or "")[:60]}',
                            'modulo': 'quejas'})
        # Cambios aprobados con INVIMA pendiente
        for r in c.execute("""
            SELECT codigo, titulo FROM control_cambios
            WHERE requiere_invima=1 AND notificacion_invima_at IS NULL
              AND estado IN ('aprobado','en_implementacion')
              AND date(aprobado_at) <= date('now','-3 days')
            LIMIT 3
        """).fetchall():
            alertas.append({'tipo': 'cambio_invima_pendiente', 'severidad': 'critica',
                            'codigo': r[0], 'descripcion': (r[1] or '')[:60],
                            'modulo': 'cambios'})
    except Exception as e:
        log.warning('dashboard alertas fallo: %s', e)
    out['alertas_criticas'] = alertas[:10]

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

        # Audit log regulatorio
        _audit_log(c, usuario=user, accion='SGD_GUARDAR', tabla='sgd_documentos',
                   registro_id=codigo,
                   despues={'version': version, 'estado': estado, 'titulo': titulo[:200]})
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        log.exception('sgd_crear_o_actualizar fallo: %s', e)
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'codigo': codigo, 'accion': accion})


@bp.route('/api/aseguramiento/sgd/<path:codigo>/pdf', methods=['POST'])
def sgd_actualizar_pdf(codigo):
    """Actualiza solo el archivo_pdf_url de un documento SGD existente.

    Endpoint dedicado para editar PDFs sin requerir todos los demás campos.
    Body: { archivo_pdf_url } · puede ser '' para limpiar el PDF.
    Requiere Calidad/Admin (igual que POST general /sgd).
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    codigo = (codigo or '').strip().upper()
    if not codigo or not re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{1,3}(?:-[A-Z]\d{1,2})?$', codigo):
        return jsonify({'error': 'codigo inválido'}), 400
    d = request.get_json(silent=True) or {}
    url = (d.get('archivo_pdf_url') or '').strip()
    if url and not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({'error': 'archivo_pdf_url debe ser http(s):// válido'}), 400
    if len(url) > 500:
        return jsonify({'error': 'URL demasiado larga (máx 500 chars)'}), 400

    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT codigo FROM sgd_documentos WHERE codigo=?", (codigo,)).fetchone()
    if not row:
        return jsonify({'error': 'documento no encontrado'}), 404
    c.execute("""
        UPDATE sgd_documentos
        SET archivo_pdf_url=?, actualizado_en=datetime('now')
        WHERE codigo=?
    """, (url or None, codigo))
    _audit_log(c, usuario=user, accion='SGD_PDF', tabla='sgd_documentos',
               registro_id=codigo, despues={'archivo_pdf_url': url[:200]})
    conn.commit()
    return jsonify({'ok': True, 'archivo_pdf_url': url or None})


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
    secret_env = os.environ.get('SECRET_KEY', '')
    if not secret_env:
        # Sin SECRET_KEY no podemos garantizar integridad de la firma INVIMA.
        # NO usar fallback determinístico (audit hallazgo crítico).
        log.error('capacitaciones_firmar: SECRET_KEY no configurado · firma rechazada')
        return jsonify({'error': 'Sistema mal configurado · contactar admin'}), 503
    secret = secret_env.encode()
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
    # Audit log INVIMA · firma de SOP es evidencia regulatoria primaria
    _audit_log(c, usuario=user, accion='SGD_FIRMAR_CAP', tabla='sgd_capacitaciones',
               registro_id=f'{sgd_codigo}#v{sgd_version}',
               despues={'sgd_codigo': sgd_codigo, 'sgd_version': sgd_version,
                         'firma_hash': firma_hash})
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

        # Race-safe: reintenta si UNIQUE(codigo) por concurrencia
        def _insertar_desv():
            cod = _generar_codigo_desviacion(c)
            c.execute("""
                INSERT INTO desviaciones
                  (codigo, fecha_deteccion, hora_deteccion, detectado_por,
                   tipo, area_origen, descripcion, contencion_inmediata,
                   impacto_producto, lotes_afectados, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'detectada')
            """, (cod,
                  (d.get('hora_deteccion') or datetime.now().strftime('%H:%M')),
                  user, tipo,
                  (d.get('area_origen') or '').strip()[:80],
                  descripcion[:2000],
                  (d.get('contencion_inmediata') or '')[:1000],
                  1 if d.get('impacto_producto') else 0,
                  (d.get('lotes_afectados') or '')[:500]))
            return cod, c.lastrowid
        try:
            codigo, desv_id = _intentar_insert_con_retry(_insertar_desv)
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
    # KPIs reales: queries dedicadas (no limitadas por LIMIT 500 de la página)
    kpi_where = ('WHERE ' + ' AND '.join(where)) if where else ''
    kpi_row = c.execute(f"""
        SELECT
          COUNT(*) as total,
          COUNT(CASE WHEN clasificacion='critica' AND estado NOT IN ('cerrada','rechazada') THEN 1 END) as criticas_abiertas,
          COUNT(CASE WHEN clasificacion IS NULL AND estado!='rechazada' THEN 1 END) as sin_clasificar,
          COUNT(CASE WHEN estado='en_investigacion' THEN 1 END) as investigando,
          COUNT(CASE WHEN estado='cerrada' AND fecha_cierre >= ? THEN 1 END) as cerradas_30d
        FROM desviaciones {kpi_where}
    """, params + [(datetime.now().date() - timedelta(days=30)).isoformat()]).fetchone()
    kpis = {
        'total': kpi_row[0] or 0, 'criticas_abiertas': kpi_row[1] or 0,
        'sin_clasificar': kpi_row[2] or 0, 'investigando': kpi_row[3] or 0,
        'cerradas_30d': kpi_row[4] or 0,
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
    row = c.execute("""
        SELECT estado, codigo, clasificacion, lotes_afectados, descripcion
        FROM desviaciones WHERE id=?
    """, (desv_id,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    estado_ant, codigo_d, clasif, lotes, desc_d = row[0], row[1], row[2], row[3], row[4]
    if estado_ant == 'cerrada':
        return jsonify({'error': 'ya está cerrada'}), 409
    if estado_ant not in ('capa_propuesto', 'capa_implementado'):
        return jsonify({'error': f'no se puede cerrar en estado {estado_ant} · primero CAPA'}), 409

    efectividad_ok = bool(d.get('efectividad_ok'))
    c.execute("""
        UPDATE desviaciones
        SET estado='cerrada', fecha_cierre=date('now'), cerrado_por=?,
            verificacion_efectividad=?, verificado_at=datetime('now'), verificado_por=?,
            efectividad_ok=?, observaciones_cierre=?,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (user, verificacion, user, 1 if efectividad_ok else 0,
          obs[:500] or None, desv_id))
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'cerrada', ?, 'cerrada', ?, ?)
    """, (desv_id, estado_ant, user,
          f'Cerrada · efectividad {"OK" if efectividad_ok else "NO_OK"}: {verificacion[:200]}'))
    # Audit log INVIMA · regulatorio
    _audit_log(c, usuario=user, accion='CERRAR_DESVIACION', tabla='desviaciones',
               registro_id=codigo_d or desv_id,
               antes={'estado': estado_ant, 'efectividad_ok': None},
               despues={'efectividad_ok': efectividad_ok,
                         'verificacion': verificacion[:500],
                         'observaciones': obs[:500]})
    conn.commit()

    # Sugerir recall si crítica + efectividad NO OK + lotes en mercado
    sugiere_recall = (clasif == 'critica' and not efectividad_ok)
    resp = {'ok': True, 'sugiere_recall': sugiere_recall}
    if sugiere_recall:
        # Pre-rellenar contexto para que el frontend pueda iniciar recall
        # con un click. El producto se infiere de los lotes (si hay).
        resp['recall_prefill'] = {
            'origen': 'desviacion',
            'origen_referencia': codigo_d,
            'desviacion_id': desv_id,
            'lotes_afectados': lotes or '',
            'motivo': (
                f'Desviación crítica {codigo_d} cerrada con CAPA '
                f'NO efectivo. {(desc_d or "")[:500]}'
            )[:1500],
        }
        # Notificar Calidad+Sebastián de que se sugiere recall
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                'capa', f'⚠ Desv {codigo_d} cerrada · CAPA NO efectivo · evaluar recall',
                body=f'Desviación crítica con efectividad NO OK. Lotes afectados: {(lotes or "?")[:200]}',
                link='/aseguramiento', remitente=user, importante=True,
            )
        except Exception as _e:
            log.warning('notif sugerir recall fallo: %s', _e)
    return jsonify(resp)


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

        def _insertar_cambio():
            cod = _generar_codigo_cambio(c)
            c.execute("""
                INSERT INTO control_cambios
                  (codigo, fecha_solicitud, solicitado_por, tipo, titulo,
                   descripcion, justificacion, areas_afectadas,
                   impacto_bpm, impacto_regulatorio, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado')
            """, (cod, user, tipo, titulo[:200], descripcion[:3000],
                  (d.get('justificacion') or '')[:1000],
                  (d.get('areas_afectadas') or '')[:300],
                  1 if d.get('impacto_bpm') else 0,
                  1 if d.get('impacto_regulatorio') else 0))
            return cod, c.lastrowid
        try:
            codigo, cid = _intentar_insert_con_retry(_insertar_cambio)
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
    kpi_where = ('WHERE ' + ' AND '.join(where)) if where else ''
    kpi_row = c.execute(f"""
        SELECT
          COUNT(*) as total,
          COUNT(CASE WHEN estado='solicitado' THEN 1 END) as sin_evaluar,
          COUNT(CASE WHEN estado='en_evaluacion' THEN 1 END) as en_evaluacion,
          COUNT(CASE WHEN estado IN ('aprobado','en_implementacion') THEN 1 END) as aprobados_pendientes,
          COUNT(CASE WHEN requiere_invima=1 AND estado NOT IN ('cerrado','rechazado') THEN 1 END) as requieren_invima,
          COUNT(CASE WHEN estado='cerrado' AND fecha_cierre >= ? THEN 1 END) as cerrados_30d
        FROM control_cambios {kpi_where}
    """, params + [(datetime.now().date() - timedelta(days=30)).isoformat()]).fetchone()
    kpis = {
        'total': kpi_row[0] or 0, 'sin_evaluar': kpi_row[1] or 0,
        'en_evaluacion': kpi_row[2] or 0, 'aprobados_pendientes': kpi_row[3] or 0,
        'requieren_invima': kpi_row[4] or 0, 'cerrados_30d': kpi_row[5] or 0,
    }
    return jsonify({'items': items, 'kpis': kpis})


@bp.route('/api/aseguramiento/cambios/<int:cid>', methods=['GET'])
def cambio_detalle(cid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    cols = ['id','codigo','fecha_solicitud','solicitado_por','tipo','titulo',
            'descripcion','justificacion','impacto_bpm','impacto_regulatorio',
            'areas_afectadas','severidad','evaluado_por','evaluado_at',
            'evaluacion_descripcion','aprobado_por','aprobado_at',
            'aprobacion_observaciones','requiere_invima','notificacion_invima_at',
            'notificacion_invima_ref','plan_implementacion',
            'fecha_implementacion_propuesta','responsable_implementacion',
            'implementado_at','implementado_por','verificacion_post',
            'verificado_por','verificado_at','verificacion_ok','estado',
            'fecha_cierre','cerrado_por','observaciones_cierre','creado_en',
            'actualizado_en']
    row = c.execute(
        f"SELECT {', '.join(cols)} FROM control_cambios WHERE id=?", (cid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'cambio no encontrado'}), 404
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
    # Audit INVIMA · decisión regulatoria
    _audit_log(c, usuario=user, accion='CAMBIO_APROBACION', tabla='control_cambios',
               registro_id=row[2] or cid,
               antes={'estado': estado_ant},
               despues={'decision': decision, 'observaciones': obs[:300],
                         'plan_implementacion': (plan or '')[:300] if plan else None,
                         'requiere_invima': bool(row[1])})
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
    row = c.execute("SELECT estado, requiere_invima, codigo FROM control_cambios WHERE id=?", (cid,)).fetchone()
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
    # Audit log INVIMA · regulatorio (Resolución 2214/2021)
    _audit_log(c, usuario=user, accion='CAMBIO_NOTIFICAR_INVIMA', tabla='control_cambios',
               registro_id=row[2] or cid,
               despues={'referencia': ref[:200]})
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/cambios/<int:cid>/implementar', methods=['POST'])
def cambio_implementar(cid):
    """Marca cambio como implementado. RBAC Calidad/Admin.

    BLOQUEA si requiere_invima=1 y aún no se notificó (Resolución 2214/2021
    exige notificación previa a la implementación).
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    obs = (d.get('observaciones') or '').strip()
    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT estado, requiere_invima, notificacion_invima_at, codigo
        FROM control_cambios WHERE id=?
    """, (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    # Bloquear implementación si requiere INVIMA pero no se ha notificado
    if row[1] and not row[2]:
        return jsonify({'error': 'No se puede implementar: requiere INVIMA y no se ha notificado · '
                                  'Notifique INVIMA primero (Resolución 2214/2021)'}), 409
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
    _audit_log(c, usuario=user, accion='CAMBIO_IMPLEMENTAR', tabla='control_cambios',
               registro_id=row[3] or cid,
               antes={'estado': estado_ant},
               despues={'observaciones': obs[:200]})
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
    _audit_log(c, usuario=user, accion='CERRAR_CAMBIO', tabla='control_cambios',
               registro_id=row[1] or cid,
               antes={'estado': estado_ant},
               despues={'verificacion_ok': bool(d.get('verificacion_ok')),
                         'verificacion': verif[:500]})
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════
# QUEJAS DE CLIENTES · ASG-PRO-013
# ════════════════════════════════════════════════════════════════════

def _generar_codigo_queja(c) -> str:
    """Genera código QC-AAAA-NNNN secuencial por año."""
    anio = datetime.now().year
    row = c.execute("""
        SELECT codigo FROM quejas_clientes
        WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1
    """, (f'QC-{anio}-%',)).fetchone()
    if row and row[0]:
        try:
            return f'QC-{anio}-{int(row[0].split("-")[-1])+1:04d}'
        except (ValueError, IndexError):
            pass
    return f'QC-{anio}-0001'


@bp.route('/api/aseguramiento/quejas', methods=['GET', 'POST'])
def quejas_endpoint():
    """GET: lista filtrable. POST: nueva queja (cualquier usuario autenticado)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        cliente_nombre = (d.get('cliente_nombre') or '').strip()
        descripcion = (d.get('descripcion') or '').strip()
        if len(cliente_nombre) < 2:
            return jsonify({'error': 'cliente_nombre requerido'}), 400
        if len(descripcion) < 10:
            return jsonify({'error': 'descripcion requerida (≥10 chars)'}), 400
        canal = (d.get('canal') or 'otro').strip()
        valid_canales = ('email','telefono','whatsapp','redes_sociales',
                          'presencial','distribuidor','formulario_web','otro')
        if canal not in valid_canales:
            return jsonify({'error': f'canal inválido. Uno de: {", ".join(valid_canales)}'}), 400
        tipo_queja = (d.get('tipo_queja') or 'otro').strip()
        valid_tipos = ('reaccion_adversa','calidad_producto','envase_empaque',
                        'cantidad_volumen','fecha_vencimiento','sabor_olor_textura',
                        'eficacia','documentacion','servicio','otro')
        if tipo_queja not in valid_tipos:
            return jsonify({'error': f'tipo_queja inválido. Uno de: {", ".join(valid_tipos)}'}), 400
        cliente_tipo = (d.get('cliente_tipo') or '').strip() or None
        if cliente_tipo and cliente_tipo not in ('consumidor_final','distribuidor','retail','medico','otro'):
            return jsonify({'error': 'cliente_tipo inválido'}), 400

        def _insertar_queja():
            cod = _generar_codigo_queja(c)
            c.execute("""
                INSERT INTO quejas_clientes
                  (codigo, fecha_recepcion, recibido_por, canal,
                   cliente_nombre, cliente_contacto, cliente_tipo,
                   producto, lote, fecha_compra, establecimiento_compra,
                   tipo_queja, descripcion, impacto_salud, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nueva')
            """, (cod, user, canal,
                  cliente_nombre[:200],
                  (d.get('cliente_contacto') or '')[:200],
                  cliente_tipo,
                  (d.get('producto') or '')[:200],
                  (d.get('lote') or '')[:100],
                  (d.get('fecha_compra') or '').strip() or None,
                  (d.get('establecimiento_compra') or '')[:200],
                  tipo_queja,
                  descripcion[:3000],
                  1 if d.get('impacto_salud') else 0))
            return cod, c.lastrowid
        try:
            codigo, qid = _intentar_insert_con_retry(_insertar_queja)
            c.execute("""
                INSERT INTO quejas_clientes_eventos
                  (queja_id, evento_tipo, estado_nuevo, usuario, comentario)
                VALUES (?, 'recibida', 'nueva', ?, ?)
            """, (qid, user, f'Queja recibida vía {canal} de {cliente_nombre[:100]}'))
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            log.exception('crear queja fallo: %s', e)
            return jsonify({'error': str(e)[:200]}), 500

        # Si declaran impacto en salud → notificación inmediata Calidad+Sebastián
        if d.get('impacto_salud') or tipo_queja == 'reaccion_adversa':
            try:
                from blueprints.notif import push_notif_multi
                push_notif_multi(
                    ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                    'capa', f'🚨 Queja {codigo} con IMPACTO EN SALUD',
                    body=f'{tipo_queja} · {cliente_nombre[:100]} · {descripcion[:140]}',
                    link='/aseguramiento', remitente=user, importante=True,
                )
            except Exception as _e:
                log.warning('notif queja salud fallo: %s', _e)
        return jsonify({'ok': True, 'id': qid, 'codigo': codigo}), 201

    # GET · lista
    estado = (request.args.get('estado') or '').strip()
    severidad = (request.args.get('severidad') or '').strip()
    where = []; params = []
    if estado: where.append('estado=?'); params.append(estado)
    if severidad: where.append('severidad=?'); params.append(severidad)
    sql = """SELECT id, codigo, fecha_recepcion, canal, cliente_nombre,
                    producto, lote, tipo_queja, severidad, estado,
                    impacto_salud, requiere_recall, fecha_compromiso, fecha_cierre,
                    CAST((julianday('now') - julianday(fecha_recepcion)) AS INTEGER) as dias_abierta
             FROM quejas_clientes"""
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_recepcion DESC, id DESC LIMIT 500'
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','fecha_recepcion','canal','cliente_nombre',
            'producto','lote','tipo_queja','severidad','estado',
            'impacto_salud','requiere_recall','fecha_compromiso','fecha_cierre','dias_abierta']
    items = [dict(zip(cols, r)) for r in rows]
    kpi_where = ('WHERE ' + ' AND '.join(where)) if where else ''
    kpi_row = c.execute(f"""
        SELECT
          COUNT(*) as total,
          COUNT(CASE WHEN estado='nueva' THEN 1 END) as nuevas,
          COUNT(CASE WHEN estado='en_investigacion' THEN 1 END) as en_investigacion,
          COUNT(CASE WHEN estado='respondida' THEN 1 END) as pendientes_cierre,
          COUNT(CASE WHEN (severidad='critica' OR impacto_salud=1)
                       AND estado NOT IN ('cerrada','rechazada') THEN 1 END) as criticas_abiertas,
          COUNT(CASE WHEN estado='cerrada' AND fecha_cierre >= ? THEN 1 END) as cerradas_30d
        FROM quejas_clientes {kpi_where}
    """, params + [(datetime.now().date() - timedelta(days=30)).isoformat()]).fetchone()
    kpis = {
        'total': kpi_row[0] or 0, 'nuevas': kpi_row[1] or 0,
        'en_investigacion': kpi_row[2] or 0, 'pendientes_cierre': kpi_row[3] or 0,
        'criticas_abiertas': kpi_row[4] or 0, 'cerradas_30d': kpi_row[5] or 0,
    }
    return jsonify({'items': items, 'kpis': kpis})


@bp.route('/api/aseguramiento/quejas/<int:qid>', methods=['GET'])
def queja_detalle(qid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    cols = ['id','codigo','fecha_recepcion','recibido_por','canal',
            'cliente_nombre','cliente_contacto','cliente_tipo','producto',
            'lote','fecha_compra','establecimiento_compra','tipo_queja',
            'descripcion','impacto_salud','severidad','triaje_descripcion',
            'triaje_por','triaje_at','requiere_desviacion','desviacion_id',
            'requiere_recall','causa_raiz','investigacion_por','investigacion_at',
            'respuesta_descripcion','respuesta_canal','respondido_por',
            'respondido_at','fecha_compromiso','cliente_satisfecho',
            'accion_correctiva','cerrado_por','fecha_cierre',
            'observaciones_cierre','estado','creado_en','actualizado_en']
    row = c.execute(
        f"SELECT {', '.join(cols)} FROM quejas_clientes WHERE id=?", (qid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'queja no encontrada'}), 404
    detalle = dict(zip(cols, row))
    eventos = c.execute("""
        SELECT evento_tipo, estado_anterior, estado_nuevo, usuario, comentario, creado_en
        FROM quejas_clientes_eventos WHERE queja_id=? ORDER BY id ASC
    """, (qid,)).fetchall()
    detalle['timeline'] = [{
        'evento_tipo': r[0], 'estado_anterior': r[1], 'estado_nuevo': r[2],
        'usuario': r[3], 'comentario': r[4], 'creado_en': r[5],
    } for r in eventos]
    return jsonify(detalle)


def _tipo_desv_desde_queja(tipo_queja: str) -> str:
    """Mapea el tipo de queja al tipo de desviación más cercano."""
    return {
        'reaccion_adversa': 'materia_prima',
        'calidad_producto': 'proceso',
        'envase_empaque': 'envase',
        'cantidad_volumen': 'proceso',
        'fecha_vencimiento': 'documental',
        'sabor_olor_textura': 'materia_prima',
        'eficacia': 'proceso',
        'documentacion': 'documental',
        'servicio': 'otra',
    }.get(tipo_queja or '', 'otra')


@bp.route('/api/aseguramiento/quejas/<int:qid>/triaje', methods=['POST'])
def queja_triaje(qid):
    """Triaje · RBAC Calidad/Admin · severidad + ¿requiere desviación/recall?

    Si requiere_desviacion=True, crea una desviación enlazada
    automáticamente y devuelve `desviacion_id` + `desviacion_codigo`.
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    d = request.get_json(silent=True) or {}
    severidad = (d.get('severidad') or '').strip()
    if severidad not in ('critica','mayor','menor','informativa'):
        return jsonify({'error': 'severidad: critica/mayor/menor/informativa'}), 400
    triaje_desc = (d.get('triaje_descripcion') or '').strip()
    if len(triaje_desc) < 10:
        return jsonify({'error': 'triaje_descripcion requerida (≥10 chars)'}), 400
    requiere_desv = bool(d.get('requiere_desviacion'))
    requiere_recall = bool(d.get('requiere_recall'))
    conn = get_db(); c = conn.cursor()
    # Cargar queja completa para tener datos al crear desviación
    row = c.execute("""
        SELECT estado, codigo, impacto_salud, tipo_queja, descripcion,
               producto, lote, desviacion_id
        FROM quejas_clientes WHERE id=?
    """, (qid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrada'}), 404
    estado_ant, codigo_q, impacto_salud, tipo_queja = row[0], row[1], row[2], row[3]
    desc_q, prod_q, lote_q, desv_existente = row[4], row[5], row[6], row[7]
    if estado_ant not in ('nueva','en_triaje'):
        return jsonify({'error': f'no se puede triar en estado {estado_ant}'}), 409

    desviacion_id = desv_existente  # Mantener si ya estaba enlazada
    desviacion_codigo = None

    # Crear desviación AUTOMÁTICA si triaje pide y no había una ya
    # Si falla, abortar todo el triaje (atomicidad regulatoria).
    if requiere_desv and not desv_existente:
        tipo_desv = _tipo_desv_desde_queja(tipo_queja)
        desv_descripcion = (
            f'[Origen: Queja {codigo_q}] {(desc_q or "")[:1500]}\n\n'
            f'Triaje: {triaje_desc[:500]}'
        )[:3000]
        def _insertar_desv_desde_queja():
            cod_desv = _generar_codigo_desviacion(c)
            c.execute("""
                INSERT INTO desviaciones
                  (codigo, fecha_deteccion, detectado_por, tipo, area_origen,
                   descripcion, impacto_producto, lotes_afectados, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, 'detectada')
            """, (cod_desv, user, tipo_desv, 'Quejas',
                  desv_descripcion,
                  1 if impacto_salud else 0,
                  (lote_q or '')[:300] or None))
            return cod_desv, c.lastrowid
        try:
            desviacion_codigo, desviacion_id = _intentar_insert_con_retry(_insertar_desv_desde_queja)
            c.execute("""
                INSERT INTO desviaciones_eventos
                  (desviacion_id, evento_tipo, estado_nuevo, usuario, comentario)
                VALUES (?, 'detectada_desde_queja', 'detectada', ?, ?)
            """, (desviacion_id, user,
                  f'Desviación creada automáticamente desde queja {codigo_q}'))
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            log.exception('crear desv desde queja fallo: %s', e)
            return jsonify({
                'error': 'Error creando desviación enlazada · triaje no aplicado'
            }), 500

    c.execute("""
        UPDATE quejas_clientes
        SET severidad=?, triaje_descripcion=?, triaje_por=?,
            triaje_at=datetime('now'),
            requiere_desviacion=?, requiere_recall=?,
            desviacion_id=?,
            estado='en_triaje', actualizado_en=datetime('now')
        WHERE id=?
    """, (severidad, triaje_desc, user,
          1 if requiere_desv else 0, 1 if requiere_recall else 0,
          desviacion_id, qid))
    extra = ''
    if desviacion_codigo:
        extra = f' · desviación auto-creada {desviacion_codigo}'
    elif requiere_desv and desv_existente:
        extra = ' · ya enlazada a desviación previa'
    c.execute("""
        INSERT INTO quejas_clientes_eventos
          (queja_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'triaje', ?, 'en_triaje', ?, ?)
    """, (qid, estado_ant, user,
          f'Severidad {severidad}'+
          (' · requiere desviación' if requiere_desv else '')+
          (' · requiere recall' if requiere_recall else '')+
          f': {triaje_desc[:200]}'+extra))
    conn.commit()
    # Notificar si crítica + impacto salud + requiere recall
    if severidad == 'critica' or requiere_recall:
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                'capa', f'⚠ Queja {codigo_q} · severidad {severidad}'+
                          (' · RECALL POTENCIAL' if requiere_recall else ''),
                body=triaje_desc[:200]+extra,
                link='/aseguramiento', remitente=user, importante=True,
            )
        except Exception as _e:
            log.warning('notif triaje fallo: %s', _e)
    return jsonify({
        'ok': True,
        'desviacion_id': desviacion_id,
        'desviacion_codigo': desviacion_codigo,
    })


@bp.route('/api/aseguramiento/quejas/<int:qid>/investigar', methods=['POST'])
def queja_investigar(qid):
    """Registrar causa raíz. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    causa = (d.get('causa_raiz') or '').strip()
    if len(causa) < 20:
        return jsonify({'error': 'causa_raiz requerida (≥20 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM quejas_clientes WHERE id=?", (qid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant not in ('en_triaje','en_investigacion'):
        return jsonify({'error': f'no se puede investigar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE quejas_clientes
        SET causa_raiz=?, investigacion_por=?, investigacion_at=datetime('now'),
            estado='en_investigacion', actualizado_en=datetime('now')
        WHERE id=?
    """, (causa[:2000], user, qid))
    c.execute("""
        INSERT INTO quejas_clientes_eventos
          (queja_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'investigada', ?, 'en_investigacion', ?, ?)
    """, (qid, estado_ant, user, causa[:200]))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/quejas/<int:qid>/responder', methods=['POST'])
def queja_responder(qid):
    """Registrar respuesta al cliente. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    resp_desc = (d.get('respuesta_descripcion') or '').strip()
    if len(resp_desc) < 20:
        return jsonify({'error': 'respuesta_descripcion requerida (≥20 chars)'}), 400
    canal_resp = (d.get('respuesta_canal') or '').strip()
    valid = ('email','telefono','whatsapp','presencial','carta','formulario_web','otro')
    if canal_resp not in valid:
        return jsonify({'error': f'respuesta_canal: {", ".join(valid)}'}), 400
    fecha_comp = (d.get('fecha_compromiso') or '').strip() or None
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM quejas_clientes WHERE id=?", (qid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant not in ('en_investigacion','en_triaje'):
        return jsonify({'error': f'no se puede responder en estado {estado_ant} · investigar primero'}), 409
    c.execute("""
        UPDATE quejas_clientes
        SET respuesta_descripcion=?, respuesta_canal=?,
            respondido_por=?, respondido_at=datetime('now'),
            fecha_compromiso=?, estado='respondida',
            actualizado_en=datetime('now')
        WHERE id=?
    """, (resp_desc[:2000], canal_resp, user, fecha_comp, qid))
    c.execute("""
        INSERT INTO quejas_clientes_eventos
          (queja_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'respondida', ?, 'respondida', ?, ?)
    """, (qid, estado_ant, user, f'Respondida vía {canal_resp}: {resp_desc[:200]}'))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/quejas/<int:qid>/cerrar', methods=['POST'])
def queja_cerrar(qid):
    """Cierra la queja con análisis efectividad. Audit log."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    if d.get('cliente_satisfecho') is None:
        return jsonify({'error': 'cliente_satisfecho (true/false) requerido'}), 400
    accion = (d.get('accion_correctiva') or '').strip()
    if len(accion) < 20:
        return jsonify({'error': 'accion_correctiva requerida (≥20 chars)'}), 400
    obs = (d.get('observaciones_cierre') or '').strip()
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM quejas_clientes WHERE id=?", (qid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrada'}), 404
    estado_ant = row[0]
    if estado_ant == 'cerrada':
        return jsonify({'error': 'ya está cerrada'}), 409
    if estado_ant != 'respondida':
        return jsonify({'error': f'debe estar respondida primero · actualmente {estado_ant}'}), 409

    c.execute("""
        UPDATE quejas_clientes
        SET cliente_satisfecho=?, accion_correctiva=?, observaciones_cierre=?,
            estado='cerrada', fecha_cierre=date('now'), cerrado_por=?,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (1 if d.get('cliente_satisfecho') else 0, accion[:2000],
          obs[:500] or None, user, qid))
    c.execute("""
        INSERT INTO quejas_clientes_eventos
          (queja_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'cerrada', ?, 'cerrada', ?, ?)
    """, (qid, estado_ant, user,
          f'Cerrada · cliente {"satisfecho" if d.get("cliente_satisfecho") else "NO satisfecho"}: {accion[:200]}'))
    _audit_log(c, usuario=user, accion='CERRAR_QUEJA', tabla='quejas_clientes',
               registro_id=row[1] or qid,
               antes={'estado': estado_ant},
               despues={'cliente_satisfecho': bool(d.get('cliente_satisfecho')),
                         'accion': accion[:500]})
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/mis-tareas', methods=['GET'])
def mis_tareas():
    """Vista consolidada de tareas pendientes del usuario actual.

    Devuelve por sección:
    - capacitaciones: SOPs asignados sin firmar (cualquier user)
    - mis_creados: items que el user creó y siguen abiertos
        (desviaciones, cambios, quejas, recalls)
    - calidad_queue: ítems pendientes de acción de Calidad
        (solo si user en CALIDAD_USERS o ADMIN_USERS) - cola universal
    - urgentes: items críticos que requieren acción inmediata

    Cada item lleva: codigo, modulo, titulo, dias_abierto, accion_sugerida.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    es_calidad = user in (set(CALIDAD_USERS) | set(ADMIN_USERS))
    conn = get_db(); c = conn.cursor()

    out = {
        'usuario': user, 'es_calidad': es_calidad,
        'capacitaciones': [], 'mis_creados': [],
        'calidad_queue': [], 'urgentes': [],
    }

    # ── Capacitaciones pendientes del usuario ──
    try:
        rows = c.execute("""
            SELECT cap.sgd_codigo, cap.sgd_version, doc.titulo, doc.archivo_pdf_url,
                   cap.asignado_at, cap.fecha_limite, cap.estado,
                   CAST(julianday('now') - julianday(cap.asignado_at) AS INTEGER) as dias
            FROM sgd_capacitaciones cap
            LEFT JOIN sgd_documentos doc ON doc.codigo=cap.sgd_codigo
            WHERE cap.persona_username=? AND cap.estado IN ('asignada','leida')
            ORDER BY cap.fecha_limite IS NULL, cap.fecha_limite ASC, cap.asignado_at ASC
            LIMIT 50
        """, (user,)).fetchall()
        out['capacitaciones'] = [{
            'sgd_codigo': r[0], 'sgd_version': r[1], 'titulo': r[2],
            'archivo_pdf_url': r[3], 'asignado_at': r[4],
            'fecha_limite': r[5], 'estado': r[6], 'dias': r[7],
        } for r in rows]
    except Exception as e:
        log.warning('mis_tareas capacitaciones: %s', e)

    # ── Items que el usuario creó y siguen abiertos ──
    try:
        # Desviaciones que detectó
        for r in c.execute("""
            SELECT codigo, descripcion, estado, fecha_deteccion,
                   CAST(julianday('now') - julianday(fecha_deteccion) AS INTEGER) as dias
            FROM desviaciones
            WHERE detectado_por=? AND estado NOT IN ('cerrada','rechazada')
            ORDER BY fecha_deteccion DESC LIMIT 20
        """, (user,)).fetchall():
            out['mis_creados'].append({
                'modulo': 'desviaciones', 'codigo': r[0],
                'titulo': (r[1] or '')[:80], 'estado': r[2],
                'fecha': r[3], 'dias': r[4],
                'accion': _accion_desv_por_estado(r[2]),
            })
        # Cambios solicitados o donde es responsable de implementación
        for r in c.execute("""
            SELECT codigo, titulo, estado, fecha_solicitud, solicitado_por,
                   responsable_implementacion,
                   CAST(julianday('now') - julianday(fecha_solicitud) AS INTEGER) as dias
            FROM control_cambios
            WHERE (solicitado_por=? OR responsable_implementacion=?)
              AND estado NOT IN ('cerrado','rechazado')
            ORDER BY fecha_solicitud DESC LIMIT 20
        """, (user, user)).fetchall():
            es_resp = r[5] == user and r[2] in ('aprobado','en_implementacion')
            out['mis_creados'].append({
                'modulo': 'cambios', 'codigo': r[0],
                'titulo': (r[1] or '')[:80], 'estado': r[2],
                'fecha': r[3], 'dias': r[6],
                'accion': 'Implementar' if es_resp else _accion_cambio_por_estado(r[2]),
            })
        # Quejas recibidas
        for r in c.execute("""
            SELECT codigo, cliente_nombre, estado, fecha_recepcion,
                   CAST(julianday('now') - julianday(fecha_recepcion) AS INTEGER) as dias
            FROM quejas_clientes
            WHERE recibido_por=? AND estado NOT IN ('cerrada','rechazada')
            ORDER BY fecha_recepcion DESC LIMIT 20
        """, (user,)).fetchall():
            out['mis_creados'].append({
                'modulo': 'quejas', 'codigo': r[0],
                'titulo': f'Cliente: {(r[1] or "")[:60]}', 'estado': r[2],
                'fecha': r[3], 'dias': r[4],
                'accion': _accion_queja_por_estado(r[2]),
            })
        # Recalls iniciados (siempre Calidad/Admin pero por completar el patrón)
        for r in c.execute("""
            SELECT codigo, producto, estado, fecha_inicio,
                   CAST(julianday('now') - julianday(fecha_inicio) AS INTEGER) as dias
            FROM recalls
            WHERE iniciado_por=? AND estado NOT IN ('cerrado','cancelado')
            ORDER BY fecha_inicio DESC LIMIT 20
        """, (user,)).fetchall():
            out['mis_creados'].append({
                'modulo': 'recalls', 'codigo': r[0],
                'titulo': (r[1] or '')[:80], 'estado': r[2],
                'fecha': r[3], 'dias': r[4],
                'accion': _accion_recall_por_estado(r[2]),
            })
    except Exception as e:
        log.warning('mis_tareas creados: %s', e)

    # ── Cola Calidad: solo para Calidad/Admin ──
    if es_calidad:
        try:
            # Desviaciones sin clasificar (≥1d) — todas
            for r in c.execute("""
                SELECT codigo, descripcion, fecha_deteccion,
                       CAST(julianday('now') - julianday(fecha_deteccion) AS INTEGER) as dias
                FROM desviaciones
                WHERE estado='detectada'
                  AND date(fecha_deteccion) <= date('now')
                ORDER BY fecha_deteccion ASC LIMIT 20
            """).fetchall():
                out['calidad_queue'].append({
                    'modulo': 'desviaciones', 'codigo': r[0],
                    'titulo': (r[1] or '')[:80], 'fecha': r[2], 'dias': r[3],
                    'accion': 'Clasificar', 'urgencia': 'alta' if (r[3] or 0) >= 1 else 'media',
                })
            # Cambios sin evaluar
            for r in c.execute("""
                SELECT codigo, titulo, fecha_solicitud,
                       CAST(julianday('now') - julianday(fecha_solicitud) AS INTEGER) as dias
                FROM control_cambios
                WHERE estado='solicitado'
                ORDER BY fecha_solicitud ASC LIMIT 20
            """).fetchall():
                out['calidad_queue'].append({
                    'modulo': 'cambios', 'codigo': r[0],
                    'titulo': (r[1] or '')[:80], 'fecha': r[2], 'dias': r[3],
                    'accion': 'Evaluar', 'urgencia': 'alta' if (r[3] or 0) >= 5 else 'media',
                })
            # Quejas nuevas
            for r in c.execute("""
                SELECT codigo, cliente_nombre, fecha_recepcion, impacto_salud,
                       CAST(julianday('now') - julianday(fecha_recepcion) AS INTEGER) as dias
                FROM quejas_clientes
                WHERE estado='nueva'
                ORDER BY impacto_salud DESC, fecha_recepcion ASC LIMIT 20
            """).fetchall():
                urg = 'super_alta' if r[3] else ('alta' if (r[4] or 0) >= 1 else 'media')
                out['calidad_queue'].append({
                    'modulo': 'quejas', 'codigo': r[0],
                    'titulo': f'Cliente: {(r[1] or "")[:60]}',
                    'fecha': r[2], 'dias': r[4],
                    'accion': 'Triaje', 'urgencia': urg,
                })
            # Recalls sin clasificar
            for r in c.execute("""
                SELECT codigo, producto, fecha_inicio,
                       CAST(julianday('now') - julianday(fecha_inicio) AS INTEGER) as dias
                FROM recalls
                WHERE estado='iniciado'
                ORDER BY fecha_inicio ASC LIMIT 20
            """).fetchall():
                out['calidad_queue'].append({
                    'modulo': 'recalls', 'codigo': r[0],
                    'titulo': (r[1] or '')[:80], 'fecha': r[2], 'dias': r[3],
                    'accion': 'Clasificar URGENTE', 'urgencia': 'super_alta',
                })
        except Exception as e:
            log.warning('mis_tareas calidad_queue: %s', e)

    # ── Urgentes: subset de calidad_queue + mis_creados marcadas como super_alta ──
    out['urgentes'] = [it for it in out['calidad_queue']
                          if it.get('urgencia') == 'super_alta']

    # Resumen
    out['resumen'] = {
        'capacitaciones_pendientes': len(out['capacitaciones']),
        'mis_creados_abiertos': len(out['mis_creados']),
        'calidad_queue': len(out['calidad_queue']) if es_calidad else 0,
        'urgentes': len(out['urgentes']),
    }
    return jsonify(out)


def _accion_desv_por_estado(estado):
    return {
        'detectada': 'Esperando clasificación de Calidad',
        'clasificada': 'Esperando investigación',
        'en_investigacion': 'Investigación en curso',
        'capa_propuesto': 'CAPA propuesto · esperando implementación',
        'capa_implementado': 'CAPA implementado · esperando cierre',
    }.get(estado, 'En proceso')


def _accion_cambio_por_estado(estado):
    return {
        'solicitado': 'Esperando evaluación',
        'en_evaluacion': 'Esperando aprobación',
        'aprobado': 'Aprobado · esperando implementación',
        'en_implementacion': 'Implementación en curso',
        'implementado': 'Esperando cierre',
    }.get(estado, 'En proceso')


def _accion_queja_por_estado(estado):
    return {
        'nueva': 'Esperando triaje de Calidad',
        'en_triaje': 'Esperando investigación',
        'en_investigacion': 'Investigación en curso',
        'respondida': 'Respondida · esperando cierre',
    }.get(estado, 'En proceso')


def _accion_recall_por_estado(estado):
    return {
        'iniciado': 'Esperando clasificación URGENTE',
        'clasificado': 'Esperando notificación INVIMA',
        'invima_notificado': 'INVIMA OK · notificar distribuidores',
        'distribuidores_notificados': 'Distribuidores OK · iniciar recolección',
        'en_recoleccion': 'Recolección en curso',
        'completado': 'Esperando cierre con efectividad',
    }.get(estado, 'En proceso')


# ════════════════════════════════════════════════════════════════════
# RECALL · ASG-PRO-004 · Retiro de producto del mercado
# ════════════════════════════════════════════════════════════════════
# Cumplimiento Resolución 2214/2021 INVIMA: Clase I requiere notificación
# a INVIMA en <24h. Clase II y III en plazos estándar definidos por
# severidad del riesgo. Acción de RECALL = uno de los procedimientos
# críticos para liberación regulatoria de cualquier farmacéutico.

def _generar_codigo_recall(c) -> str:
    """Genera código RCL-AAAA-NNNN secuencial por año."""
    anio = datetime.now().year
    row = c.execute("""
        SELECT codigo FROM recalls
        WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1
    """, (f'RCL-{anio}-%',)).fetchone()
    if row and row[0]:
        try:
            return f'RCL-{anio}-{int(row[0].split("-")[-1])+1:04d}'
        except (ValueError, IndexError):
            pass
    return f'RCL-{anio}-0001'


@bp.route('/api/aseguramiento/recalls', methods=['GET', 'POST'])
def recalls_endpoint():
    """GET: lista filtrable. POST: iniciar recall (solo Calidad/Admin)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # Iniciar recall = solo Calidad/Admin (es decisión grave)
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin pueden iniciar recall'}), 403
        d = request.get_json(silent=True) or {}
        producto = (d.get('producto') or '').strip()
        lotes = (d.get('lotes_afectados') or '').strip()
        motivo = (d.get('motivo') or '').strip()
        if len(producto) < 2:
            return jsonify({'error': 'producto requerido'}), 400
        if len(lotes) < 2:
            return jsonify({'error': 'lotes_afectados requerido (puede ser uno o varios)'}), 400
        if len(motivo) < 20:
            return jsonify({'error': 'motivo requerido (≥20 chars)'}), 400
        origen = (d.get('origen') or 'otro').strip()
        valid_origenes = ('desviacion','queja_cliente','hallazgo_interno',
                            'auditoria','reaccion_adversa','invima','otro')
        if origen not in valid_origenes:
            return jsonify({'error': f'origen inválido. Uno de: {", ".join(valid_origenes)}'}), 400

        def _insertar_recall():
            cod = _generar_codigo_recall(c)
            c.execute("""
                INSERT INTO recalls
                  (codigo, fecha_inicio, iniciado_por, origen, origen_referencia,
                   desviacion_id, queja_id, producto, lotes_afectados,
                   cantidad_fabricada, cantidad_distribuida,
                   motivo, riesgo_descripcion, estado)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'iniciado')
            """, (cod, user, origen,
                  (d.get('origen_referencia') or '')[:200],
                  d.get('desviacion_id'),
                  d.get('queja_id'),
                  producto[:200],
                  lotes[:500],
                  d.get('cantidad_fabricada'),
                  d.get('cantidad_distribuida'),
                  motivo[:3000],
                  (d.get('riesgo_descripcion') or '')[:2000]))
            return cod, c.lastrowid
        try:
            codigo, rid = _intentar_insert_con_retry(_insertar_recall)
            c.execute("""
                INSERT INTO recalls_eventos
                  (recall_id, evento_tipo, estado_nuevo, usuario, comentario)
                VALUES (?, 'iniciado', 'iniciado', ?, ?)
            """, (rid, user, f'Recall iniciado · origen {origen} · {producto[:80]}'))
            # Audit log INVIMA · regulatorio crítico para recalls
            _audit_log(c, usuario=user, accion='INICIAR_RECALL', tabla='recalls',
                       registro_id=codigo,
                       despues={'producto': producto[:200], 'lotes': lotes[:500],
                                 'origen': origen, 'motivo': motivo[:500]})
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            log.exception('crear recall fallo: %s', e)
            return jsonify({'error': str(e)[:200]}), 500

        # Recall = SIEMPRE notificación crítica
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                'capa', f'🚨🚨 RECALL INICIADO {codigo} · {producto[:60]}',
                body=f'Lotes: {lotes[:200]}\nMotivo: {motivo[:200]}\nClasificar URGENTE para INVIMA.',
                link='/aseguramiento', remitente=user, importante=True,
            )
        except Exception as _e:
            log.warning('notif recall iniciar fallo: %s', _e)
        return jsonify({'ok': True, 'id': rid, 'codigo': codigo}), 201

    # GET · lista
    estado = (request.args.get('estado') or '').strip()
    clase = (request.args.get('clase') or '').strip()
    where = []; params = []
    if estado: where.append('estado=?'); params.append(estado)
    if clase: where.append('clase_recall=?'); params.append(clase)
    sql = """SELECT id, codigo, fecha_inicio, producto, lotes_afectados,
                    clase_recall, alcance_geografico, estado, origen,
                    notificacion_invima_at, cantidad_distribuida, cantidad_recolectada,
                    fecha_cierre,
                    CAST((julianday('now') - julianday(fecha_inicio)) AS INTEGER) as dias_abierto
             FROM recalls"""
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_inicio DESC, id DESC LIMIT 500'
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','fecha_inicio','producto','lotes_afectados',
            'clase_recall','alcance_geografico','estado','origen',
            'notificacion_invima_at','cantidad_distribuida','cantidad_recolectada',
            'fecha_cierre','dias_abierto']
    items = [dict(zip(cols, r)) for r in rows]
    kpi_where = ('WHERE ' + ' AND '.join(where)) if where else ''
    kpi_row = c.execute(f"""
        SELECT
          COUNT(*) as total,
          COUNT(CASE WHEN estado='iniciado' THEN 1 END) as sin_clasificar,
          COUNT(CASE WHEN clase_recall='clase_I'
                       AND estado NOT IN ('cerrado','cancelado') THEN 1 END) as clase_I_abiertos,
          COUNT(CASE WHEN estado IN ('iniciado','clasificado')
                       AND notificacion_invima_at IS NULL THEN 1 END) as invima_pendiente,
          COUNT(CASE WHEN estado='en_recoleccion' THEN 1 END) as en_recoleccion,
          COUNT(CASE WHEN estado='cerrado' AND fecha_cierre >= ? THEN 1 END) as cerrados_30d
        FROM recalls {kpi_where}
    """, params + [(datetime.now().date() - timedelta(days=30)).isoformat()]).fetchone()
    kpis = {
        'total': kpi_row[0] or 0, 'sin_clasificar': kpi_row[1] or 0,
        'clase_I_abiertos': kpi_row[2] or 0, 'invima_pendiente': kpi_row[3] or 0,
        'en_recoleccion': kpi_row[4] or 0, 'cerrados_30d': kpi_row[5] or 0,
    }
    return jsonify({'items': items, 'kpis': kpis})


@bp.route('/api/aseguramiento/recalls/<int:rid>', methods=['GET'])
def recall_detalle(rid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    cols = ['id','codigo','fecha_inicio','iniciado_por','origen',
            'origen_referencia','desviacion_id','queja_id','producto',
            'lotes_afectados','cantidad_fabricada','cantidad_distribuida',
            'motivo','riesgo_descripcion','clase_recall','alcance_geografico',
            'clasificado_por','clasificado_at','justificacion_clasificacion',
            'notificacion_invima_at','notificacion_invima_ref',
            'notificacion_invima_por','notificacion_distribuidores_at',
            'distribuidores_notificados','notificacion_distribuidores_por',
            'recoleccion_inicio_at','recoleccion_completada_at',
            'cantidad_recolectada','disposicion_final','disposicion_descripcion',
            'efectividad_porcentaje','efectividad_descripcion','estado',
            'fecha_cierre','cerrado_por','observaciones_cierre','creado_en',
            'actualizado_en']
    row = c.execute(
        f"SELECT {', '.join(cols)} FROM recalls WHERE id=?", (rid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'recall no encontrado'}), 404
    detalle = dict(zip(cols, row))
    eventos = c.execute("""
        SELECT evento_tipo, estado_anterior, estado_nuevo, usuario, comentario, creado_en
        FROM recalls_eventos WHERE recall_id=? ORDER BY id ASC
    """, (rid,)).fetchall()
    detalle['timeline'] = [{
        'evento_tipo': r[0], 'estado_anterior': r[1], 'estado_nuevo': r[2],
        'usuario': r[3], 'comentario': r[4], 'creado_en': r[5],
    } for r in eventos]
    return jsonify(detalle)


@bp.route('/api/aseguramiento/recalls/<int:rid>/clasificar', methods=['POST'])
def recall_clasificar(rid):
    """Clase I (riesgo grave salud) → INVIMA <24h. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    clase = (d.get('clase_recall') or '').strip()
    if clase not in ('clase_I','clase_II','clase_III'):
        return jsonify({'error': 'clase_recall: clase_I/clase_II/clase_III'}), 400
    alcance = (d.get('alcance_geografico') or '').strip()
    if alcance not in ('local','regional','nacional','internacional'):
        return jsonify({'error': 'alcance_geografico: local/regional/nacional/internacional'}), 400
    just = (d.get('justificacion_clasificacion') or '').strip()
    if len(just) < 20:
        return jsonify({'error': 'justificacion_clasificacion requerida (≥20 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('iniciado','clasificado'):
        return jsonify({'error': f'no se puede clasificar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE recalls
        SET clase_recall=?, alcance_geografico=?, justificacion_clasificacion=?,
            clasificado_por=?, clasificado_at=datetime('now'),
            estado='clasificado', actualizado_en=datetime('now')
        WHERE id=?
    """, (clase, alcance, just, user, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'clasificado', ?, 'clasificado', ?, ?)
    """, (rid, estado_ant, user, f'{clase} · alcance {alcance}: {just[:200]}'))
    # Audit log INVIMA · clasificación regulatoria
    _audit_log(c, usuario=user, accion='RECALL_CLASIFICAR', tabla='recalls',
               registro_id=row[1] or rid,
               antes={'estado': estado_ant, 'clase_recall': None},
               despues={'clase_recall': clase, 'alcance_geografico': alcance,
                         'justificacion': just[:500]})
    conn.commit()
    # Si Clase I → notificar INVIMA es URGENTE (24h)
    if clase == 'clase_I':
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['aseguramiento.espagiria','sebastian'],
                'capa', f'🚨 {row[1]} · CLASE I · NOTIFICAR INVIMA <24H',
                body=f'Recall Clase I requiere notificación INVIMA inmediata (Resolución 2214/2021).',
                link='/aseguramiento', remitente=user, importante=True,
            )
        except Exception as _e:
            log.warning('notif clase_I fallo: %s', _e)
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/recalls/<int:rid>/notificar-invima', methods=['POST'])
def recall_notificar_invima(rid):
    """Registra notificación a INVIMA (radicado/oficio)."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    ref = (d.get('referencia') or '').strip()
    if not ref:
        return jsonify({'error': 'referencia (radicado/oficio) requerido'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('clasificado','invima_notificado'):
        return jsonify({'error': f'no se puede notificar INVIMA en estado {estado_ant} · clasificar primero'}), 409
    c.execute("""
        UPDATE recalls
        SET notificacion_invima_at=datetime('now'),
            notificacion_invima_ref=?, notificacion_invima_por=?,
            estado='invima_notificado', actualizado_en=datetime('now')
        WHERE id=?
    """, (ref[:200], user, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'invima_notificado', ?, 'invima_notificado', ?, ?)
    """, (rid, estado_ant, user, f'INVIMA notificado · ref: {ref[:100]}'))
    # Audit log INVIMA · regulatorio crítico (Resolución 2214/2021)
    _audit_log(c, usuario=user, accion='RECALL_NOTIFICAR_INVIMA', tabla='recalls',
               registro_id=row[1] or rid,
               despues={'referencia': ref[:200]})
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/recalls/<int:rid>/notificar-distribuidores', methods=['POST'])
def recall_notificar_distribuidores(rid):
    """Notifica a distribuidores y retail. RBAC Calidad/Admin."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    distribuidores = (d.get('distribuidores_notificados') or '').strip()
    if len(distribuidores) < 5:
        return jsonify({'error': 'distribuidores_notificados requerido (lista o descripción)'}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('invima_notificado','distribuidores_notificados','en_recoleccion'):
        return jsonify({'error': f'INVIMA debe estar notificado primero · estado {estado_ant}'}), 409
    c.execute("""
        UPDATE recalls
        SET notificacion_distribuidores_at=datetime('now'),
            distribuidores_notificados=?, notificacion_distribuidores_por=?,
            estado=CASE WHEN estado='en_recoleccion' THEN 'en_recoleccion'
                          ELSE 'distribuidores_notificados' END,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (distribuidores[:2000], user, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'distribuidores_notificados', ?, 'distribuidores_notificados', ?, ?)
    """, (rid, estado_ant, user, distribuidores[:200]))
    _audit_log(c, usuario=user, accion='RECALL_NOTIFICAR_DIST', tabla='recalls',
               registro_id=row[1] or rid,
               despues={'distribuidores': distribuidores[:500]})
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/recalls/<int:rid>/recoleccion', methods=['POST'])
def recall_recoleccion(rid):
    """Inicia/actualiza recolección · cantidad recolectada."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    cantidad = d.get('cantidad_recolectada')
    if cantidad is None:
        return jsonify({'error': 'cantidad_recolectada requerida (entero)'}), 400
    try:
        cantidad = int(cantidad)
        if cantidad < 0: raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'cantidad_recolectada debe ser entero ≥ 0'}), 400
    completa = bool(d.get('completa'))
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('distribuidores_notificados','en_recoleccion'):
        return jsonify({'error': f'no se puede registrar recolección en estado {estado_ant}'}), 409
    nuevo_estado = 'completado' if completa else 'en_recoleccion'
    c.execute("""
        UPDATE recalls
        SET cantidad_recolectada=?,
            recoleccion_inicio_at=COALESCE(recoleccion_inicio_at, datetime('now')),
            recoleccion_completada_at=CASE WHEN ? THEN datetime('now') ELSE recoleccion_completada_at END,
            estado=?, actualizado_en=datetime('now')
        WHERE id=?
    """, (cantidad, 1 if completa else 0, nuevo_estado, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rid, 'recoleccion_completada' if completa else 'recoleccion_actualizada',
          estado_ant, nuevo_estado, user,
          f'Recolectadas {cantidad} unidades' + (' · COMPLETA' if completa else '')))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/aseguramiento/recalls/<int:rid>/cerrar', methods=['POST'])
def recall_cerrar(rid):
    """Cierra el recall con efectividad + disposición final. Audit log."""
    user = session.get('compras_user', '')
    if user not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    d = request.get_json(silent=True) or {}
    disposicion = (d.get('disposicion_final') or '').strip()
    if disposicion not in ('destruccion','reproceso','devolver_proveedor','cuarentena'):
        return jsonify({'error': 'disposicion_final: destruccion/reproceso/devolver_proveedor/cuarentena'}), 400
    disp_desc = (d.get('disposicion_descripcion') or '').strip()
    if len(disp_desc) < 20:
        return jsonify({'error': 'disposicion_descripcion requerida (≥20 chars)'}), 400
    efectividad = d.get('efectividad_porcentaje')
    try:
        efectividad = int(efectividad) if efectividad is not None else None
        if efectividad is not None and not (0 <= efectividad <= 100):
            return jsonify({'error': 'efectividad_porcentaje debe ser 0-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'efectividad_porcentaje inválido'}), 400
    ef_desc = (d.get('efectividad_descripcion') or '').strip()
    obs = (d.get('observaciones_cierre') or '').strip()
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado, codigo FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant == 'cerrado':
        return jsonify({'error': 'ya está cerrado'}), 409
    if estado_ant != 'completado':
        return jsonify({'error': f'debe estar completado primero · actualmente {estado_ant}'}), 409

    c.execute("""
        UPDATE recalls
        SET disposicion_final=?, disposicion_descripcion=?,
            efectividad_porcentaje=?, efectividad_descripcion=?,
            observaciones_cierre=?, estado='cerrado',
            fecha_cierre=date('now'), cerrado_por=?,
            actualizado_en=datetime('now')
        WHERE id=?
    """, (disposicion, disp_desc[:1000],
          efectividad, ef_desc[:1000] or None,
          obs[:500] or None, user, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'cerrado', ?, 'cerrado', ?, ?)
    """, (rid, estado_ant, user,
          f'Cerrado · {disposicion}' + (f' · efectividad {efectividad}%' if efectividad is not None else '')))
    _audit_log(c, usuario=user, accion='CERRAR_RECALL', tabla='recalls',
               registro_id=row[1] or rid,
               antes={'estado': estado_ant},
               despues={'disposicion': disposicion,
                         'efectividad_porcentaje': efectividad,
                         'descripcion': disp_desc[:500]})
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
