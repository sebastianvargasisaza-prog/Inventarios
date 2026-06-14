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
from datetime import datetime, timedelta, date, timezone
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


def _hoy_co():
    """Fecha de HOY en Colombia (M24). En Render el server es UTC; de noche en Colombia
    datetime.now() ya es 'mañana' UTC y desfasaba los KPIs (cerradas_30d, vencidos)."""
    return (datetime.now(timezone.utc) - timedelta(hours=5)).date()


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
    """Escritura en Aseguramiento: ASEGURAMIENTO (Miguel · dueño del módulo) + CALIDAD + ADMIN.
    FIX 14-jun: tras dividir los cargos, ASEGURAMIENTO_USERS quedó fuera y Miguel no podía
    operar su propio módulo (clasificar desviaciones, cambios, calificar proveedores, etc.)."""
    try:
        from config import ASEGURAMIENTO_USERS as _AC
    except Exception:
        _AC = set()
    return set(_AC) | set(CALIDAD_USERS) | set(ADMIN_USERS)


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
        return redirect('/login?next=/aseguramiento')
    # Cargo Aseguramiento de la Calidad (AC) · distinto de Control de Calidad. Admin y
    # equipo de calidad también entran (mismo equipo hasta separar membresías).
    u = session.get('compras_user', '')
    try:
        from config import ASEGURAMIENTO_USERS, ADMIN_USERS as _ADM
        permitidos = set(ASEGURAMIENTO_USERS) | set(_ADM)
    except Exception:
        permitidos = set()
    if permitidos and u not in permitidos:
        from auth import sin_acceso_html
        return Response(sin_acceso_html('Aseguramiento de la Calidad'), mimetype='text/html')
    html = ASEGURAMIENTO_HTML
    try:
        from templates_py.ui_help import TOOLTIP_CSS
        html = html.replace('</style>', TOOLTIP_CSS + '\n</style>', 1)
    except Exception:
        pass
    return Response(html, mimetype='text/html; charset=utf-8')


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
    out = {'fecha_hoy': _hoy_co().isoformat()}

    # SGD: docs vigentes / próximos a vencer / obsoletos / conflictos
    # SQLite no soporta COUNT(*) FILTER · usar COUNT(CASE WHEN ...)
    try:
        sgd = c.execute("""
            SELECT
              COUNT(CASE WHEN estado='vigente' THEN 1 END) as vigentes,
              COUNT(CASE WHEN estado='vigente'
                          AND date(proxima_revision) <= date('now', '-5 hours', '+30 days')
                          AND date(proxima_revision) >= date('now', '-5 hours')
                       THEN 1 END) as vencen_30d,
              COUNT(CASE WHEN estado='vigente'
                          AND date(proxima_revision) < date('now', '-5 hours')
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
                          AND date(firmado_at) >= date('now', '-5 hours', '-30 days')
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
            WHERE date(fecha) BETWEEN date('now', '-5 hours') AND date('now', '-5 hours', '+60 days')
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
                          AND date(fecha_cierre) >= date('now', '-5 hours', '-30 days') THEN 1 END) as cerradas_30d
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
                          AND date(fecha_cierre) >= date('now', '-5 hours', '-30 days') THEN 1 END) as cerrados_30d
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
                          AND date(fecha_cierre) >= date('now', '-5 hours', '-30 days') THEN 1 END) as cerradas_30d
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
                          AND date(fecha_cierre) >= date('now', '-5 hours', '-30 days') THEN 1 END) as cerrados_30d
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
              AND date(fecha_deteccion) <= date('now', '-5 hours', '-2 days')
            LIMIT 3
        """).fetchall():
            alertas.append({'tipo': 'desviacion_critica_sin_investigar', 'severidad': 'critica',
                            'codigo': r[0], 'descripcion': (r[1] or '')[:60],
                            'modulo': 'desviaciones'})
        # Quejas con impacto salud sin responder
        for r in c.execute("""
            SELECT codigo, cliente_nombre FROM quejas_clientes
            WHERE impacto_salud=1 AND estado IN ('nueva','en_triaje','en_investigacion')
              AND date(fecha_recepcion) <= date('now', '-5 hours', '-2 days')
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
              AND date(aprobado_at) <= date('now', '-5 hours', '-3 days')
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
                      WHEN estado = 'vigente' AND date(proxima_revision) < date('now', '-5 hours') THEN 'vencido'
                      WHEN estado = 'vigente' AND date(proxima_revision) <= date('now', '-5 hours', '+30 days') THEN 'vence_pronto'
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
            # INVIMA-FIX · 21-may-2026 · proteger campos críticos si versión NO cambió
            # Antes: mismo número de versión podía sobreescribir PDF/aprobador sin
            # archivar la versión previa · ruptura GDP/BPM (auditor INVIMA lo detecta)
            campos_blindados_si_misma_version = (
                'archivo_pdf_url', 'aprobado_por', 'fecha_aprobacion', 'estado',
            )
            if version != ver_anterior:
                c.execute("""
                    INSERT OR IGNORE INTO sgd_versiones
                      (codigo, version, fecha_aprobacion, archivo_url, motivo_cambio, aprobado_por)
                    SELECT codigo, version_actual, fecha_aprobacion, archivo_pdf_url,
                           ?, aprobado_por
                    FROM sgd_documentos WHERE codigo=?
                """, (d.get('motivo_cambio') or 'Versión anterior archivada', codigo))
            else:
                # MISMA versión · ignorar cambios a campos blindados
                # (forzar a quien cambia que haga bump de versión)
                cambios_blindados = [k for k in campos_blindados_si_misma_version if k in d]
                if cambios_blindados:
                    return jsonify({
                        'error': 'Cambios a campos críticos requieren nueva versión',
                        'codigo': 'VERSION_BUMP_REQUERIDO',
                        'campos_bloqueados': cambios_blindados,
                        'version_actual': ver_anterior,
                        'hint': 'Cambiar version y enviar nuevo PDF · versión previa queda archivada',
                    }), 409
            # Validar archivo_pdf_url (http/https only)
            arch_url = d.get('archivo_pdf_url')
            if arch_url and not str(arch_url).startswith(('http://', 'https://')):
                return jsonify({
                    'error': 'archivo_pdf_url debe ser http(s)://',
                    'codigo': 'URL_INVALIDA',
                }), 400
            # UPDATE
            c.execute("""
                UPDATE sgd_documentos SET
                  area=?, tipo_doc=?, numero=?, subtipo=?, padre_codigo=?,
                  titulo=?, descripcion=?, version_actual=?,
                  archivo_pdf_url=?, archivo_origen=?, fecha_creacion=?,
                  fecha_aprobacion=?, vigente_desde=?, proxima_revision=?,
                  estado=?, elaborado_por=?, revisado_por=?, aprobado_por=?,
                  observaciones=?, actualizado_en=datetime('now', '-5 hours')
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
        SET archivo_pdf_url=?, actualizado_en=datetime('now', '-5 hours')
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
    # Audit log INVIMA · importación masiva de SGD (procedimientos regulados)
    try:
        _audit_log(c, usuario=user, accion='SGD_IMPORTAR_MASIVO', tabla='sgd_documentos',
                   despues={'insertados': insertados, 'saltados_ya_existian': saltados,
                            'conflictos_insertados': conflictos_insertados,
                            'conflictos_actualizados': conflictos_saltados,
                            'errores_count': len(errores)},
                   detalle=f'SGD import batch · {insertados} ins · {saltados} saltados · {len(errores)} errores')
        conn.commit()
    except Exception as _ae:
        log.warning('audit sgd_importar fallo: %s', _ae)
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
            resuelto_at=datetime('now', '-5 hours')
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
        SET leido_at=COALESCE(leido_at, datetime('now', '-5 hours')),
            firmado_at=datetime('now', '-5 hours'),
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


def crear_desviacion_auto(c, *, tipo, descripcion, lotes_afectados='',
                          detectado_por='sistema', area_origen='',
                          impacto_producto=1, contencion_inmediata=''):
    """Crea una desviación programáticamente (p.ej. IPC fuera de spec del EBR ·
    reemplazo MyBatch fase 2). Mismo patrón que el endpoint POST (código
    race-safe + evento inicial + audit_log). NO commitea · el caller maneja la
    transacción. Devuelve (codigo, desv_id).
    """
    def _ins():
        cod = _generar_codigo_desviacion(c)
        c.execute("""
            INSERT INTO desviaciones
              (codigo, fecha_deteccion, hora_deteccion, detectado_por, tipo,
               area_origen, descripcion, contencion_inmediata, impacto_producto,
               lotes_afectados, estado)
            VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, 'detectada')
        """, (cod, datetime.now().strftime('%H:%M'), detectado_por, tipo,
              (area_origen or '')[:80], (descripcion or '')[:2000],
              (contencion_inmediata or '')[:1000], 1 if impacto_producto else 0,
              (lotes_afectados or '')[:500]))
        return cod, c.lastrowid
    codigo, desv_id = _intentar_insert_con_retry(_ins)
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_nuevo, usuario, comentario)
        VALUES (?, 'detectada', 'detectada', ?, ?)
    """, (desv_id, detectado_por, 'Desviación creada automáticamente'))
    _audit_log(c, usuario=detectado_por, accion='CREAR_DESVIACION_AUTO',
               tabla='desviaciones', registro_id=codigo,
               despues={'codigo': codigo, 'tipo': tipo,
                        'lotes_afectados': (lotes_afectados or '')[:200]},
               detalle=f"Desviación {codigo} auto · {(descripcion or '')[:120]}")
    return codigo, desv_id


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
                VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, 'detectada')
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
            # P0 audit 26-may · INVIMA · registro primario · audit_log obligatorio
            _audit_log(c, usuario=user, accion='CREAR_DESVIACION',
                       tabla='desviaciones', registro_id=codigo,
                       despues={'codigo': codigo, 'tipo': tipo,
                                'area_origen': (d.get('area_origen') or '')[:80],
                                'impacto_producto': bool(d.get('impacto_producto')),
                                'lotes_afectados': (d.get('lotes_afectados') or '')[:200]},
                       detalle=f"Desviación {codigo} · {tipo} · {descripcion[:120]}")
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
    """, params + [(_hoy_co() - timedelta(days=30)).isoformat()]).fetchone()
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
            clasificado_por=?, clasificado_at=datetime('now', '-5 hours'),
            estado='clasificada', actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND estado IN ('detectada','clasificada')
    """, (clasif, just, user, desv_id))
    if c.rowcount != 1:  # CAS (M27): otro worker cambió el estado en paralelo
        return jsonify({'error': 'El estado cambió en paralelo · recargá', 'codigo': 'RACE_ESTADO'}), 409
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'clasificada', ?, 'clasificada', ?, ?)
    """, (desv_id, estado_ant, user, f'Clasificada como {clasif}: {just[:200]}'))
    # Audit log INVIMA · clasificación crítica/mayor/menor afecta priorización regulatoria
    _audit_log(c, usuario=user, accion='CLASIFICAR_DESVIACION', tabla='desviaciones',
               registro_id=desv_id,
               antes={'estado': estado_ant},
               despues={'clasificacion': clasif, 'justificacion': just[:300],
                        'estado': 'clasificada'})
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
            investigado_por=?, investigacion_at=datetime('now', '-5 hours'),
            estado='en_investigacion', actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND estado IN ('clasificada','en_investigacion')
    """, (metodo, causa, user, desv_id))
    if c.rowcount != 1:  # CAS (M27)
        return jsonify({'error': 'El estado cambió en paralelo · recargá', 'codigo': 'RACE_ESTADO'}), 409
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'investigada', ?, 'en_investigacion', ?, ?)
    """, (desv_id, estado_ant, user, f'Causa raíz ({metodo}): {causa[:200]}'))
    _audit_log(c, usuario=user, accion='INVESTIGAR_DESVIACION', tabla='desviaciones',
               registro_id=desv_id,
               antes={'estado': estado_ant},
               despues={'metodo_investigacion': metodo, 'causa_raiz': causa[:400],
                        'estado': 'en_investigacion'})
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
            estado='capa_propuesto', actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND estado IN ('en_investigacion','capa_propuesto')
    """, (capa, responsable, fecha_limite, desv_id))
    if c.rowcount != 1:  # CAS (M27)
        return jsonify({'error': 'El estado cambió en paralelo · recargá', 'codigo': 'RACE_ESTADO'}), 409
    c.execute("""
        INSERT INTO desviaciones_eventos
          (desviacion_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'capa_propuesto', ?, 'capa_propuesto', ?, ?)
    """, (desv_id, estado_ant, user,
          f'CAPA: {capa[:150]} · resp: {responsable} · límite: {fecha_limite or "sin definir"}'))
    _audit_log(c, usuario=user, accion='DEFINIR_CAPA_DESVIACION', tabla='desviaciones',
               registro_id=desv_id,
               antes={'estado': estado_ant},
               despues={'capa_descripcion': capa[:400], 'capa_responsable': responsable,
                        'capa_fecha_limite': fecha_limite, 'estado': 'capa_propuesto'})
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
        SET estado='cerrada', fecha_cierre=date('now', '-5 hours'), cerrado_por=?,
            verificacion_efectividad=?, verificado_at=datetime('now', '-5 hours'), verificado_por=?,
            efectividad_ok=?, observaciones_cierre=?,
            actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND estado IN ('capa_propuesto','capa_implementado')
    """, (user, verificacion, user, 1 if efectividad_ok else 0,
          obs[:500] or None, desv_id))
    if c.rowcount != 1:  # CAS (M27)
        return jsonify({'error': 'El estado cambió en paralelo · recargá', 'codigo': 'RACE_ESTADO'}), 409
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
                VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado')
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
            # M22 · audit Part 11: la solicitud de cambio es evento regulado.
            _audit_log_global(c, usuario=user, accion='CREAR_CAMBIO', tabla='control_cambios',
                              registro_id=codigo, despues={'titulo': titulo[:120], 'tipo': tipo,
                              'impacto_bpm': bool(d.get('impacto_bpm')),
                              'impacto_regulatorio': bool(d.get('impacto_regulatorio'))})
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
    """, params + [(_hoy_co() - timedelta(days=30)).isoformat()]).fetchone()
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
    # Snapshot antes para audit (incluye requiere_invima previo · cambiar
    # ese flag de True→False desactiva la guard de cambio_implementar)
    row = c.execute(
        "SELECT estado, severidad, requiere_invima, codigo FROM control_cambios WHERE id=?",
        (cid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant, sev_ant, req_inv_ant, codigo_cc = row[0], row[1], row[2], row[3]
    if estado_ant not in ('solicitado', 'en_evaluacion'):
        return jsonify({'error': f'no se puede evaluar en estado {estado_ant}'}), 409
    c.execute("""
        UPDATE control_cambios
        SET severidad=?, evaluacion_descripcion=?, evaluado_por=?,
            evaluado_at=datetime('now', '-5 hours'), requiere_invima=?,
            estado='en_evaluacion', actualizado_en=datetime('now', '-5 hours')
        WHERE id=?
    """, (severidad, eval_desc, user, 1 if requiere_invima else 0, cid))
    c.execute("""
        INSERT INTO control_cambios_eventos
          (cambio_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, 'evaluado', ?, 'en_evaluacion', ?, ?)
    """, (cid, estado_ant, user,
          f'Severidad {severidad}'+(' · Requiere INVIMA' if requiere_invima else '')+f': {eval_desc[:200]}'))
    # Audit log INVIMA · cambiar requiere_invima desactiva guard regulatoria
    _audit_log(c, usuario=user, accion='EVALUAR_CAMBIO_CONTROL', tabla='control_cambios',
               registro_id=codigo_cc or cid,
               antes={'estado': estado_ant, 'severidad': sev_ant,
                      'requiere_invima': bool(req_inv_ant)},
               despues={'severidad': severidad, 'requiere_invima': requiere_invima,
                        'evaluacion_descripcion': eval_desc[:300],
                        'estado': 'en_evaluacion'})
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
        SET aprobado_por=?, aprobado_at=datetime('now', '-5 hours'),
            aprobacion_observaciones=?, plan_implementacion=?,
            fecha_implementacion_propuesta=?, responsable_implementacion=?,
            estado=?, actualizado_en=datetime('now', '-5 hours')
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
    row = c.execute(
        "SELECT estado, requiere_invima, codigo, notificacion_invima_at, notificacion_invima_ref "
        "FROM control_cambios WHERE id=?", (cid,)
    ).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    if not row[1]:
        return jsonify({'error': 'este cambio no requiere INVIMA'}), 400
    # P0 audit 26-may-2026 · zero-error · cronología INVIMA es regulatoria
    # (Resolución 2214/2021). Sobrescribir el timestamp original oculta cuándo
    # se notificó realmente. Rechazar si ya estaba notificado · si Calidad
    # necesita actualizar SOLO la referencia, debe usar endpoint dedicado.
    if row[3]:
        return jsonify({
            'error': 'Ya fue notificado a INVIMA · timestamp inmutable',
            'notificacion_invima_at': row[3],
            'notificacion_invima_ref': row[4] or '',
            'hint': 'Para actualizar la referencia/radicado, usa /api/aseguramiento/cambios/<id>/notificar-invima-ref',
        }), 409
    # CAS: solo actualiza si sigue NULL — defensa contra race entre 2 workers
    c.execute("""
        UPDATE control_cambios
        SET notificacion_invima_at=datetime('now', '-5 hours'),
            notificacion_invima_ref=?, actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND notificacion_invima_at IS NULL
    """, (ref[:200], cid))
    if c.rowcount == 0:
        # Otro worker se adelantó · re-leer y devolver 409
        existing = c.execute(
            "SELECT notificacion_invima_at, notificacion_invima_ref FROM control_cambios WHERE id=?",
            (cid,)).fetchone()
        return jsonify({
            'error': 'Race · ya fue notificado por otro proceso',
            'notificacion_invima_at': existing[0] if existing else None,
            'notificacion_invima_ref': existing[1] if existing else '',
        }), 409
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
        SET implementado_at=datetime('now', '-5 hours'), implementado_por=?,
            estado='implementado', actualizado_en=datetime('now', '-5 hours')
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
        SET verificacion_post=?, verificado_por=?, verificado_at=datetime('now', '-5 hours'),
            verificacion_ok=?, observaciones_cierre=?,
            estado='cerrado', fecha_cierre=date('now', '-5 hours'), cerrado_por=?,
            actualizado_en=datetime('now', '-5 hours')
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
                VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nueva')
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
            # M22 · audit Part 11: la creación de una queja es evento regulado.
            _audit_log_global(c, usuario=user, accion='CREAR_QUEJA', tabla='quejas_clientes',
                              registro_id=codigo, despues={'cliente': cliente_nombre[:100],
                              'tipo': tipo_queja, 'impacto_salud': bool(d.get('impacto_salud')),
                              'lote': (d.get('lote') or '')[:60]})
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
    """, params + [(_hoy_co() - timedelta(days=30)).isoformat()]).fetchone()
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
                VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, 'detectada')
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
            triaje_at=datetime('now', '-5 hours'),
            requiere_desviacion=?, requiere_recall=?,
            desviacion_id=?,
            estado='en_triaje', actualizado_en=datetime('now', '-5 hours')
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
    # Audit log triaje queja · INVIMA (decisión escalar a desviación/recall regulatorio)
    _audit_log(c, usuario=user, accion='TRIAJE_QUEJA', tabla='quejas_clientes',
               registro_id=codigo_q or qid,
               antes={'estado': estado_ant, 'severidad': None},
               despues={'severidad': severidad,
                        'requiere_desviacion': requiere_desv,
                        'requiere_recall': requiere_recall,
                        'desviacion_id': desviacion_id,
                        'desviacion_creada': desviacion_codigo,
                        'estado': 'en_triaje'})
    if desviacion_codigo:
        _audit_log(c, usuario=user, accion='CREAR_DESVIACION_DESDE_QUEJA',
                   tabla='desviaciones', registro_id=desviacion_codigo,
                   despues={'codigo': desviacion_codigo,
                            'queja_origen': codigo_q,
                            'impacto_salud': bool(impacto_salud)},
                   detalle=f'Desv. {desviacion_codigo} auto-creada desde queja {codigo_q}')
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
        SET causa_raiz=?, investigacion_por=?, investigacion_at=datetime('now', '-5 hours'),
            estado='en_investigacion', actualizado_en=datetime('now', '-5 hours')
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
            respondido_por=?, respondido_at=datetime('now', '-5 hours'),
            fecha_compromiso=?, estado='respondida',
            actualizado_en=datetime('now', '-5 hours')
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
            estado='cerrada', fecha_cierre=date('now', '-5 hours'), cerrado_por=?,
            actualizado_en=datetime('now', '-5 hours')
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
                  AND date(fecha_deteccion) <= date('now', '-5 hours')
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
                VALUES (?, date('now', '-5 hours'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'iniciado')
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
    """, params + [(_hoy_co() - timedelta(days=30)).isoformat()]).fetchone()
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
            clasificado_por=?, clasificado_at=datetime('now', '-5 hours'),
            estado='clasificado', actualizado_en=datetime('now', '-5 hours')
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
    row = c.execute(
        "SELECT estado, codigo, notificacion_invima_at, notificacion_invima_ref "
        "FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('clasificado','invima_notificado'):
        return jsonify({'error': f'no se puede notificar INVIMA en estado {estado_ant} · clasificar primero'}), 409
    # P0 audit 26-may · cronología INVIMA inmutable (Resolución 2214/2021 +
    # 24h para recall Clase I). Sobrescribir el timestamp original oculta
    # demora regulatoria — auditoría podría no detectar notificación tardía.
    if row[2]:
        return jsonify({
            'error': 'Ya fue notificado a INVIMA · timestamp inmutable',
            'notificacion_invima_at': row[2],
            'notificacion_invima_ref': row[3] or '',
            'hint': 'Para actualizar SOLO la referencia/radicado usa endpoint dedicado',
        }), 409
    # CAS: defensa cross-worker
    c.execute("""
        UPDATE recalls
        SET notificacion_invima_at=datetime('now', '-5 hours'),
            notificacion_invima_ref=?, notificacion_invima_por=?,
            estado='invima_notificado', actualizado_en=datetime('now', '-5 hours')
        WHERE id=? AND notificacion_invima_at IS NULL
    """, (ref[:200], user, rid))
    if c.rowcount == 0:
        existing = c.execute(
            "SELECT notificacion_invima_at, notificacion_invima_ref FROM recalls WHERE id=?",
            (rid,)).fetchone()
        return jsonify({
            'error': 'Race · ya fue notificado por otro proceso',
            'notificacion_invima_at': existing[0] if existing else None,
            'notificacion_invima_ref': existing[1] if existing else '',
        }), 409
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
        SET notificacion_distribuidores_at=datetime('now', '-5 hours'),
            distribuidores_notificados=?, notificacion_distribuidores_por=?,
            estado=CASE WHEN estado='en_recoleccion' THEN 'en_recoleccion'
                          ELSE 'distribuidores_notificados' END,
            actualizado_en=datetime('now', '-5 hours')
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
    row = c.execute(
        "SELECT estado, codigo, cantidad_distribuida, cantidad_recolectada "
        "FROM recalls WHERE id=?", (rid,)).fetchone()
    if not row: return jsonify({'error': 'no encontrado'}), 404
    estado_ant = row[0]
    if estado_ant not in ('distribuidores_notificados','en_recoleccion'):
        return jsonify({'error': f'no se puede registrar recolección en estado {estado_ant}'}), 409
    # Validar cantidad recolectada <= distribuida (cuando distribuida está
    # definida) · evita marcar recall completado con números inflados
    if row[2] is not None and cantidad > row[2]:
        return jsonify({
            'error': f'cantidad_recolectada ({cantidad}) excede cantidad_distribuida ({row[2]})'
        }), 400
    nuevo_estado = 'completado' if completa else 'en_recoleccion'
    c.execute("""
        UPDATE recalls
        SET cantidad_recolectada=?,
            recoleccion_inicio_at=COALESCE(recoleccion_inicio_at, datetime('now', '-5 hours')),
            recoleccion_completada_at=CASE WHEN ? <> 0 THEN datetime('now', '-5 hours') ELSE recoleccion_completada_at END,
            estado=?, actualizado_en=datetime('now', '-5 hours')
        WHERE id=?
    """, (cantidad, 1 if completa else 0, nuevo_estado, rid))
    c.execute("""
        INSERT INTO recalls_eventos
          (recall_id, evento_tipo, estado_anterior, estado_nuevo, usuario, comentario)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rid, 'recoleccion_completada' if completa else 'recoleccion_actualizada',
          estado_ant, nuevo_estado, user,
          f'Recolectadas {cantidad} unidades' + (' · COMPLETA' if completa else '')))
    # Audit log INVIMA · efectividad recall regulatorio
    _audit_log(c, usuario=user, accion='RECALL_RECOLECCION', tabla='recalls',
               registro_id=row[1] or rid,
               antes={'estado': estado_ant, 'cantidad_recolectada': row[3]},
               despues={'cantidad_recolectada': cantidad, 'completa': completa,
                        'estado': nuevo_estado})
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
            fecha_cierre=date('now', '-5 hours'), cerrado_por=?,
            actualizado_en=datetime('now', '-5 hours')
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


# ════════════════════════════════════════════════════════════════════════
# REPORTES INVIMA · consultas ad-hoc para auditoría regulatoria
# ════════════════════════════════════════════════════════════════════════
# Sebastián 2-may-2026: cuando llegue auditoría INVIMA (Resolución 2214/2021),
# estos endpoints centralizan las consultas más frecuentes en lugar de hacer
# SQL ad-hoc en producción. Solo Calidad+Admin pueden consultarlos.

@bp.route('/api/aseguramiento/reportes/audit-trail', methods=['GET'])
def reporte_audit_trail():
    """Audit log filtrable · evidencia INVIMA de cambios regulatorios.

    Query params:
      - desde · YYYY-MM-DD (default: hace 30 días)
      - hasta · YYYY-MM-DD (default: hoy)
      - accion · filtro exacto (ej. 'CERRAR_RECALL')
      - tabla · filtro exacto (ej. 'recalls')
      - usuario · filtro exacto
    """
    user = session.get('compras_user', '')
    if user not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    accion = (request.args.get('accion') or '').strip()
    tabla = (request.args.get('tabla') or '').strip()
    usuario_filtro = (request.args.get('usuario') or '').strip()
    if not desde:
        desde = (_hoy_co() - timedelta(days=30)).isoformat()
    if not hasta:
        # +1 dia (12-jun): el audit_log canonico guarda fecha en UTC (datetime('now'))
        # y el server corre en hora Colombia (UTC-5). De noche la fecha UTC rueda al
        # dia siguiente y date(fecha) > hoy-local excluia el registro recien escrito
        # (CERRAR_DESVIACION no aparecia en el reporte aunque SI estaba en la tabla).
        hasta = (datetime.now() + timedelta(days=1)).date().isoformat()
    where = ['date(fecha) >= ?', 'date(fecha) <= ?']
    params = [desde, hasta]
    if accion:
        where.append('accion = ?'); params.append(accion)
    if tabla:
        where.append('tabla = ?'); params.append(tabla)
    if usuario_filtro:
        where.append('usuario = ?'); params.append(usuario_filtro)
    sql = f"""
        SELECT id, usuario, accion, tabla, registro_id, antes, despues,
               detalle, ip, fecha
        FROM audit_log
        WHERE {' AND '.join(where)}
        ORDER BY fecha DESC, id DESC
        LIMIT 500
    """
    rows = get_db().execute(sql, params).fetchall()
    items = [{
        'id': r[0], 'usuario': r[1], 'accion': r[2], 'tabla': r[3],
        'registro_id': r[4], 'antes': r[5], 'despues': r[6],
        'detalle': r[7], 'ip': r[8], 'fecha': r[9],
    } for r in rows]
    return jsonify({
        'desde': desde, 'hasta': hasta,
        'filtros': {'accion': accion, 'tabla': tabla, 'usuario': usuario_filtro},
        'total': len(items),
        'items': items,
    })


@bp.route('/api/aseguramiento/reportes/cliente-trazabilidad/<int:cid>', methods=['GET'])
def reporte_cliente_trazabilidad(cid):
    """Dado un cliente, devuelve qué lotes/SKUs recibió.

    Inverso del lote-trazabilidad. Útil para:
    - Recall: notificar al cliente con lista de su pedido afectado.
    - Auditoría: detalle de despachos a un cliente específico.
    """
    user = session.get('compras_user', '')
    if user not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    db = get_db()
    cliente = db.execute("""
        SELECT id, codigo, nombre, empresa, email, telefono, nit
        FROM clientes WHERE id=?
    """, (cid,)).fetchone()
    if not cliente:
        return jsonify({'error': 'cliente no encontrado'}), 404
    # Habeas Data (Ley 1581): email/teléfono/NIT son PII · solo admin los ve en claro;
    # Calidad ve el nombre/empresa (suficiente para el recall) con el contacto enmascarado.
    _es_admin = user in set(ADMIN_USERS)

    def _pii(v):
        return v if _es_admin else ('***' if v else None)
    cli_dict = {
        'id': cliente[0], 'codigo': cliente[1], 'nombre': cliente[2],
        'empresa': cliente[3], 'email': _pii(cliente[4]),
        'telefono': _pii(cliente[5]), 'nit': _pii(cliente[6]),
    }
    # Despachos con lotes (recall-ready)
    despachos = [{
        'numero': r[0], 'fecha': r[1], 'sku': r[2], 'descripcion': r[3],
        'lote_pt': r[4], 'cantidad': r[5],
    } for r in db.execute("""
        SELECT d.numero, d.fecha, di.sku, di.descripcion, di.lote_pt, di.cantidad
        FROM despachos d
          INNER JOIN despachos_items di ON di.numero_despacho=d.numero
        WHERE d.cliente_id=?
        ORDER BY d.fecha DESC LIMIT 500
    """, (cid,)).fetchall()]
    # Pedidos
    pedidos = [{
        'numero': r[0], 'fecha': r[1], 'estado': r[2], 'valor_total': r[3],
    } for r in db.execute("""
        SELECT numero, fecha, estado, valor_total
        FROM pedidos WHERE cliente_id=?
        ORDER BY fecha DESC LIMIT 200
    """, (cid,)).fetchall()]
    # Lotes únicos recibidos (para recall rápido)
    lotes_unicos = list({d['lote_pt'] for d in despachos if d['lote_pt']})
    return jsonify({
        'cliente': cli_dict,
        'consulta_at': datetime.now().isoformat(),
        'consultado_por': user,
        'despachos': despachos,
        'pedidos': pedidos,
        'lotes_unicos': lotes_unicos,
        'resumen': {
            'despachos': len(despachos),
            'pedidos': len(pedidos),
            'lotes_distintos': len(lotes_unicos),
        },
    })


@bp.route('/api/aseguramiento/reportes/audit-trail/csv', methods=['GET'])
def reporte_audit_trail_csv():
    """Export CSV del audit-trail · útil para enviar a INVIMA en físico.

    Mismos query params que /reportes/audit-trail.
    """
    user = session.get('compras_user', '')
    if user not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    accion = (request.args.get('accion') or '').strip()
    tabla = (request.args.get('tabla') or '').strip()
    usuario_filtro = (request.args.get('usuario') or '').strip()
    if not desde:
        desde = (_hoy_co() - timedelta(days=30)).isoformat()
    if not hasta:
        # +1 dia (12-jun): el audit_log canonico guarda fecha en UTC (datetime('now'))
        # y el server corre en hora Colombia (UTC-5). De noche la fecha UTC rueda al
        # dia siguiente y date(fecha) > hoy-local excluia el registro recien escrito
        # (CERRAR_DESVIACION no aparecia en el reporte aunque SI estaba en la tabla).
        hasta = (datetime.now() + timedelta(days=1)).date().isoformat()
    where = ['date(fecha) >= ?', 'date(fecha) <= ?']
    params = [desde, hasta]
    if accion:
        where.append('accion = ?'); params.append(accion)
    if tabla:
        where.append('tabla = ?'); params.append(tabla)
    if usuario_filtro:
        where.append('usuario = ?'); params.append(usuario_filtro)
    sql = f"""
        SELECT id, usuario, accion, tabla, registro_id, antes, despues,
               detalle, ip, fecha
        FROM audit_log
        WHERE {' AND '.join(where)}
        ORDER BY fecha DESC, id DESC
        LIMIT 10000
    """
    rows = get_db().execute(sql, params).fetchall()
    # CSV manual (sin pandas) · headers + filas escapadas
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    writer = _csv.writer(buf, quoting=_csv.QUOTE_MINIMAL)
    writer.writerow(['id','usuario','accion','tabla','registro_id',
                     'antes','despues','detalle','ip','fecha'])
    for r in rows:
        writer.writerow([str(c) if c is not None else '' for c in r])
    fname = f'audit_trail_{desde}_{hasta}.csv'
    from flask import Response as _Response
    return _Response(
        buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{fname}"',
            'Cache-Control': 'no-store',
        }
    )


@bp.route('/api/aseguramiento/reportes/lote-trazabilidad/<path:lote>', methods=['GET'])
def reporte_lote_trazabilidad(lote):
    """Dado un lote, devuelve toda la cadena · recepción → uso → despachos.

    Útil para:
    - Recall: qué clientes recibieron este lote.
    - Auditoría INVIMA: trazabilidad completa de un lote sospechoso.
    """
    user = session.get('compras_user', '')
    if user not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin'}), 403
    if not lote or len(lote) < 2:
        return jsonify({'error': 'lote requerido'}), 400
    import urllib.parse
    lote = urllib.parse.unquote(lote).strip()
    db = get_db()

    # 1. Recepciones (movimientos de entrada)
    try:
        recepciones = [{
            'fecha': r[0], 'material': r[1], 'cantidad': r[2],
            'proveedor': r[3], 'numero_oc': r[4], 'estado_lote': r[5],
            'fecha_vencimiento': r[6],
        } for r in db.execute("""
            SELECT fecha, material_nombre, cantidad, proveedor, numero_oc,
                   estado_lote, fecha_vencimiento
            FROM movimientos
            WHERE tipo='Entrada' AND lote=?
            ORDER BY fecha DESC LIMIT 50
        """, (lote,)).fetchall()]
    except Exception as e:
        log.warning('lote-trazabilidad recepciones fallo: %s', e)
        recepciones = []

    # 2. Producciones que usaron este lote (movimientos de Salida con observación)
    try:
        producciones = [{
            'fecha': r[0], 'material': r[1], 'cantidad': r[2],
            'observaciones': r[3] or '', 'operador': r[4],
        } for r in db.execute("""
            SELECT fecha, material_nombre, cantidad, observaciones, operador
            FROM movimientos
            WHERE tipo='Salida' AND lote=?
            ORDER BY fecha DESC LIMIT 100
        """, (lote,)).fetchall()]
    except Exception:
        producciones = []

    # 3. CoAs del lote
    try:
        coas = [{
            'fecha': r[0], 'parametro': r[1], 'valor': r[2],
            'conforme': bool(r[3]), 'analista': r[4], 'decision': r[5],
        } for r in db.execute("""
            SELECT fecha_analisis, parametro, valor_obtenido, conforme,
                   analista, decision
            FROM coa_resultados
            WHERE lote=?
            ORDER BY fecha_analisis DESC LIMIT 50
        """, (lote,)).fetchall()]
    except Exception:
        coas = []

    # 4. NCs / OOS asociadas
    try:
        ncs = [{
            'id': r[0], 'fecha': r[1], 'tipo': r[2], 'descripcion': r[3],
            'impacto': r[4], 'estado': r[5],
        } for r in db.execute("""
            SELECT id, fecha, tipo, descripcion, impacto, estado
            FROM no_conformidades
            WHERE lote=?
            ORDER BY fecha DESC LIMIT 20
        """, (lote,)).fetchall()]
    except Exception:
        ncs = []

    try:
        oos = [{
            'id': r[0], 'codigo': r[1], 'fecha': r[2], 'parametro': r[3],
            'valor_obtenido': r[4], 'estado': r[5],
        } for r in db.execute("""
            SELECT id, codigo, fecha_deteccion, parametro,
                   valor_obtenido_texto, estado
            FROM calidad_oos
            WHERE lote=?
            ORDER BY fecha_deteccion DESC LIMIT 20
        """, (lote,)).fetchall()]
    except Exception:
        oos = []

    # 5. Despachos a clientes (uso B2B con lote_pt)
    try:
        despachos = [{
            'numero_despacho': r[0], 'fecha': r[1], 'cliente': r[2],
            'sku': r[3], 'cantidad': r[4],
        } for r in db.execute("""
            SELECT di.numero_despacho, d.fecha, cl.nombre, di.sku, di.cantidad
            FROM despachos_items di
              LEFT JOIN despachos d ON d.numero=di.numero_despacho
              LEFT JOIN clientes cl ON cl.id=d.cliente_id
            WHERE di.lote_pt=?
            ORDER BY d.fecha DESC LIMIT 100
        """, (lote,)).fetchall()]
    except Exception:
        despachos = []

    # 6. Desviaciones que mencionan el lote
    try:
        desviaciones = [{
            'codigo': r[0], 'fecha': r[1], 'tipo': r[2], 'estado': r[3],
            'clasificacion': r[4],
        } for r in db.execute("""
            SELECT codigo, fecha_deteccion, tipo, estado, clasificacion
            FROM desviaciones
            WHERE lotes_afectados LIKE ?
            ORDER BY fecha_deteccion DESC LIMIT 20
        """, (f'%{lote}%',)).fetchall()]
    except Exception:
        desviaciones = []

    # 7. Recalls que afectaron el lote
    try:
        recalls = [{
            'codigo': r[0], 'fecha_inicio': r[1], 'producto': r[2],
            'clase_recall': r[3], 'estado': r[4],
        } for r in db.execute("""
            SELECT codigo, fecha_inicio, producto, clase_recall, estado
            FROM recalls
            WHERE lotes_afectados LIKE ?
            ORDER BY fecha_inicio DESC LIMIT 20
        """, (f'%{lote}%',)).fetchall()]
    except Exception:
        recalls = []

    return jsonify({
        'lote': lote,
        'consulta_at': datetime.now().isoformat(),
        'consultado_por': user,
        'cadena': {
            'recepciones': recepciones,
            'producciones_uso': producciones,
            'coas': coas,
            'ncs': ncs,
            'oos': oos,
            'despachos_clientes': despachos,
            'desviaciones': desviaciones,
            'recalls': recalls,
        },
        'resumen': {
            'recepciones': len(recepciones),
            'producciones': len(producciones),
            'coas': len(coas),
            'ncs': len(ncs),
            'oos': len(oos),
            'despachos': len(despachos),
            'desviaciones': len(desviaciones),
            'recalls': len(recalls),
        },
    })


# ════════════════════════════════════════════════════════════════════════
# GOBIERNO GMP (14-jun) · 5 elementos: Revisión por la Dirección, Calificación de
# proveedores (reusa proveedores+scorecard de compras), Validación de equipos (reusa
# equipos_planta), FMEA (ICH Q9), Acuerdos de calidad (maquila/terceros).
# ════════════════════════════════════════════════════════════════════════

# --- (a) REVISIÓN POR LA DIRECCIÓN (APR anual · INVIMA Res.2214 art.8) ---
def _kpis_consolidados(c):
    """Snapshot en vivo de los KPIs del sistema de calidad para la revisión."""
    def n(sql, p=()):
        r = c.execute(sql, p).fetchone()
        return (r[0] or 0) if r else 0
    return {
        'desviaciones_abiertas': n("SELECT COUNT(*) FROM desviaciones WHERE estado NOT IN ('cerrada','rechazada')"),
        'desviaciones_criticas_abiertas': n("SELECT COUNT(*) FROM desviaciones WHERE clasificacion='critica' AND estado NOT IN ('cerrada','rechazada')"),
        'cambios_abiertos': n("SELECT COUNT(*) FROM control_cambios WHERE estado NOT IN ('cerrado','rechazado')"),
        'cambios_invima_pendiente': n("SELECT COUNT(*) FROM control_cambios WHERE requiere_invima=1 AND COALESCE(notificacion_invima_at,'')='' AND estado NOT IN ('cerrado','rechazado')"),
        'quejas_abiertas': n("SELECT COUNT(*) FROM quejas_clientes WHERE estado NOT IN ('cerrada','rechazada')"),
        'recalls_abiertos': n("SELECT COUNT(*) FROM recalls WHERE estado NOT IN ('cerrado','cancelado')"),
        'ncs_abiertas': n("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'"),
        'sgd_vencidos': n("SELECT COUNT(*) FROM sgd_documentos WHERE estado='vigente' AND COALESCE(proxima_revision,'')<>'' AND date(proxima_revision) < date('now','-5 hours')"),
        'capacitaciones_pendientes': n("SELECT COUNT(*) FROM sgd_capacitaciones WHERE estado IN ('asignada','leida')"),
        'proveedores_aprobados': n("SELECT COUNT(*) FROM proveedores_calificacion WHERE estado='aprobado'"),
        'oos_abiertos': n("SELECT COUNT(*) FROM calidad_oos WHERE LOWER(COALESCE(estado,'')) NOT IN ('cerrado','rechazado','descartado')"),
    }


@bp.route('/api/aseguramiento/revision-direccion', methods=['GET', 'POST'])
def revision_direccion():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
        d = request.get_json(silent=True) or {}
        periodo = (d.get('periodo') or '').strip()
        if not periodo:
            return jsonify({'error': 'periodo requerido (ej. 2026 o 2026-S1)'}), 400
        c.execute("INSERT INTO revision_direccion (periodo,fecha_planeada,conducido_por,estado,creado_por) "
                  "VALUES (?,?,?, 'planeada', ?)",
                  (periodo, (d.get('fecha_planeada') or '').strip() or None,
                   (d.get('conducido_por') or '').strip() or None, user))
        rid = c.lastrowid
        _audit_log(c, usuario=user, accion='CREAR_REVISION_DIRECCION', tabla='revision_direccion',
                   registro_id=rid, despues={'periodo': periodo})
        conn.commit()
        return jsonify({'ok': True, 'id': rid}), 201
    rows = c.execute("SELECT id,periodo,fecha_planeada,fecha_ejecutada,conducido_por,estado,creado_en "
                     "FROM revision_direccion ORDER BY id DESC LIMIT 50").fetchall()
    cols = ['id', 'periodo', 'fecha_planeada', 'fecha_ejecutada', 'conducido_por', 'estado', 'creado_en']
    return jsonify({'revisiones': [dict(zip(cols, r)) for r in rows], 'kpis_actuales': _kpis_consolidados(c)})


@bp.route('/api/aseguramiento/revision-direccion/<int:rid>/ejecutar', methods=['POST'])
def revision_direccion_ejecutar(rid):
    if session.get('compras_user', '') not in _autorizados_escritura():
        return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
    user = session.get('compras_user', '')
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT estado FROM revision_direccion WHERE id=?", (rid,)).fetchone()
    if not row:
        return jsonify({'error': 'no encontrada'}), 404
    import json as _json
    kpis = _json.dumps(_kpis_consolidados(c), ensure_ascii=False)
    c.execute("UPDATE revision_direccion SET estado='ejecutada', "
              "fecha_ejecutada=date('now','-5 hours'), kpis_json=?, fortalezas=?, debilidades=?, "
              "decisiones=?, acciones_mejora=?, participantes=?, acta_url=?, conducido_por=COALESCE(?,conducido_por) "
              "WHERE id=? AND estado='planeada'",
              (kpis, (d.get('fortalezas') or '')[:3000], (d.get('debilidades') or '')[:3000],
               (d.get('decisiones') or '')[:3000], (d.get('acciones_mejora') or '')[:3000],
               (d.get('participantes') or '')[:500], (d.get('acta_url') or '').strip() or None,
               (d.get('conducido_por') or '').strip() or None, rid))
    if c.rowcount != 1:
        return jsonify({'error': 'la revisión ya fue ejecutada o cambió de estado'}), 409
    _audit_log(c, usuario=user, accion='EJECUTAR_REVISION_DIRECCION', tabla='revision_direccion',
               registro_id=rid, despues={'kpis': 'snapshot', 'decisiones': (d.get('decisiones') or '')[:200]})
    conn.commit()
    return jsonify({'ok': True})


# --- (b) CALIFICACIÓN DE PROVEEDORES (reusa proveedores + scorecard de compras) ---
@bp.route('/api/aseguramiento/proveedores-calificacion', methods=['GET', 'POST'])
def proveedores_calificacion():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
        d = request.get_json(silent=True) or {}
        prov = (d.get('proveedor') or '').strip()
        if not prov:
            return jsonify({'error': 'proveedor requerido'}), 400
        estado = (d.get('estado') or 'pendiente').strip().lower()
        crit = 'critico' if (d.get('criticidad') == 'critico') else 'no_critico'
        visita = 1 if d.get('requiere_visita') else 0
        c.execute(
            "INSERT INTO proveedores_calificacion "
            "(proveedor,criticidad,requiere_visita,categoria,estado,cuestionario_url,certificaciones,"
            " fecha_aprobacion,fecha_reevaluacion,fecha_ultima_visita,observaciones,evaluado_por,actualizado_en,creado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,date('now','-5 hours'),?) "
            "ON CONFLICT(proveedor) DO UPDATE SET criticidad=excluded.criticidad, "
            "requiere_visita=excluded.requiere_visita, categoria=excluded.categoria, estado=excluded.estado, "
            "cuestionario_url=excluded.cuestionario_url, certificaciones=excluded.certificaciones, "
            "fecha_aprobacion=excluded.fecha_aprobacion, fecha_reevaluacion=excluded.fecha_reevaluacion, "
            "fecha_ultima_visita=excluded.fecha_ultima_visita, observaciones=excluded.observaciones, "
            "evaluado_por=excluded.evaluado_por, actualizado_en=excluded.actualizado_en",
            (prov, crit, visita, (d.get('categoria') or '').strip() or None, estado,
             (d.get('cuestionario_url') or '').strip() or None, (d.get('certificaciones') or '').strip() or None,
             (d.get('fecha_aprobacion') or '').strip() or None, (d.get('fecha_reevaluacion') or '').strip() or None,
             (d.get('fecha_ultima_visita') or '').strip() or None, (d.get('observaciones') or '')[:1000], user, user))
        _audit_log(c, usuario=user, accion='CALIFICAR_PROVEEDOR', tabla='proveedores_calificacion',
                   registro_id=prov, despues={'estado': estado, 'criticidad': crit, 'requiere_visita': bool(visita)})
        conn.commit()
        return jsonify({'ok': True})
    # GET: proveedores (de compras) + su calificación AC (LEFT JOIN · reusa el maestro existente)
    rows = c.execute(
        "SELECT p.nombre, COALESCE(pc.criticidad,'no_critico'), COALESCE(pc.requiere_visita,0), "
        "       COALESCE(pc.estado,'pendiente'), pc.fecha_aprobacion, pc.fecha_reevaluacion, "
        "       pc.fecha_ultima_visita, COALESCE(pc.categoria,'') "
        "FROM proveedores p LEFT JOIN proveedores_calificacion pc ON pc.proveedor = p.nombre "
        "WHERE COALESCE(p.activo,1)=1 "
        "ORDER BY (COALESCE(pc.estado,'pendiente')='pendiente') DESC, p.nombre LIMIT 500"
    ).fetchall()
    cols = ['proveedor', 'criticidad', 'requiere_visita', 'estado', 'fecha_aprobacion',
            'fecha_reevaluacion', 'fecha_ultima_visita', 'categoria']
    items = [dict(zip(cols, r)) for r in rows]
    # Huérfanos: una calificación AC NUNCA debe quedar invisible (proveedor inactivo
    # o calificado a mano sin estar en el maestro) — la sumamos si no salió arriba.
    vistos = {x['proveedor'] for x in items}
    huerf = c.execute(
        "SELECT proveedor, COALESCE(criticidad,'no_critico'), COALESCE(requiere_visita,0), "
        "       COALESCE(estado,'pendiente'), fecha_aprobacion, fecha_reevaluacion, "
        "       fecha_ultima_visita, COALESCE(categoria,'') FROM proveedores_calificacion "
        "ORDER BY proveedor LIMIT 500"
    ).fetchall()
    for r in huerf:
        if r[0] not in vistos:
            items.append(dict(zip(cols, r)))
            vistos.add(r[0])
    hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
    resumen = {
        'total': len(items),
        'aprobados': sum(1 for x in items if x['estado'] == 'aprobado'),
        'pendientes': sum(1 for x in items if x['estado'] == 'pendiente'),
        'criticos': sum(1 for x in items if x['criticidad'] == 'critico'),
        'reevaluacion_vencida': sum(1 for x in items if (x['fecha_reevaluacion'] or '') and x['fecha_reevaluacion'][:10] < hoy),
    }
    return jsonify({'proveedores': items, 'resumen': resumen})


# --- (c) VALIDACIÓN DE EQUIPOS (reusa equipos_planta) ---
@bp.route('/api/aseguramiento/validacion-equipos', methods=['GET', 'POST'])
def validacion_equipos():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
        d = request.get_json(silent=True) or {}
        eq = (d.get('equipo_codigo') or '').strip()
        tipo = (d.get('tipo') or '').strip().upper()
        if not eq or tipo not in ('IQ', 'OQ', 'PQ', 'CSV', 'REVALIDACION'):
            return jsonify({'error': 'equipo_codigo y tipo (IQ/OQ/PQ/CSV/revalidacion) requeridos'}), 400
        c.execute("INSERT INTO validacion_equipos (equipo_codigo,tipo,protocolo_url,criterios_aceptacion,"
                  "resultado,estado,fecha_ejecucion,ejecutado_por,aprobado_por,fecha_revalidacion,observaciones,creado_por) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (eq, ('revalidacion' if tipo == 'REVALIDACION' else tipo),
                   (d.get('protocolo_url') or '').strip() or None, (d.get('criterios_aceptacion') or '')[:2000],
                   (d.get('resultado') or '')[:2000], (d.get('estado') or 'pendiente').strip().lower(),
                   (d.get('fecha_ejecucion') or '').strip() or None, user,
                   (d.get('aprobado_por') or '').strip() or None,
                   (d.get('fecha_revalidacion') or '').strip() or None, (d.get('observaciones') or '')[:1000], user))
        vid = c.lastrowid
        _audit_log(c, usuario=user, accion='VALIDACION_EQUIPO', tabla='validacion_equipos',
                   registro_id=vid, despues={'equipo': eq, 'tipo': tipo})
        conn.commit()
        return jsonify({'ok': True, 'id': vid}), 201
    rows = c.execute(
        "SELECT v.id, v.equipo_codigo, COALESCE(ep.nombre,''), v.tipo, v.estado, v.fecha_ejecucion, "
        "       v.fecha_revalidacion, v.aprobado_por FROM validacion_equipos v "
        "LEFT JOIN equipos_planta ep ON ep.codigo = v.equipo_codigo ORDER BY v.id DESC LIMIT 300"
    ).fetchall()
    cols = ['id', 'equipo_codigo', 'equipo_nombre', 'tipo', 'estado', 'fecha_ejecucion', 'fecha_revalidacion', 'aprobado_por']
    return jsonify({'validaciones': [dict(zip(cols, r)) for r in rows]})


# --- (d) FMEA / riesgo ICH Q9 ---
@bp.route('/api/aseguramiento/fmea', methods=['GET', 'POST'])
def fmea_endpoint():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
        d = request.get_json(silent=True) or {}
        prod = (d.get('producto_nombre') or '').strip()
        modo = (d.get('modo_falla') or '').strip()
        if not prod or not modo:
            return jsonify({'error': 'producto_nombre y modo_falla requeridos'}), 400

        def _i(v):
            try:
                return max(1, min(10, int(v)))
            except (TypeError, ValueError):
                return None
        s, o, det = _i(d.get('severidad')), _i(d.get('ocurrencia')), _i(d.get('deteccion'))
        rpn = (s * o * det) if (s and o and det) else None
        c.execute("INSERT INTO producto_fmea (producto_nombre,modo_falla,efecto,causa,severidad,ocurrencia,"
                  "deteccion,rpn,control_actual,accion_recomendada,responsable,creado_por) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (prod, modo, (d.get('efecto') or '')[:500], (d.get('causa') or '')[:500], s, o, det, rpn,
                   (d.get('control_actual') or '')[:500], (d.get('accion_recomendada') or '')[:500],
                   (d.get('responsable') or '').strip() or None, user))
        fid = c.lastrowid
        _audit_log(c, usuario=user, accion='CREAR_FMEA', tabla='producto_fmea',
                   registro_id=fid, despues={'producto': prod, 'rpn': rpn})
        conn.commit()
        return jsonify({'ok': True, 'id': fid, 'rpn': rpn}), 201
    prod = (request.args.get('producto') or '').strip()
    where, params = [], []
    if prod:
        where.append('producto_nombre=?'); params.append(prod)
    sql = ("SELECT id,producto_nombre,modo_falla,efecto,causa,severidad,ocurrencia,deteccion,rpn,"
           "control_actual,accion_recomendada,estado FROM producto_fmea")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(rpn,0) DESC, id DESC LIMIT 300"
    rows = c.execute(sql, params).fetchall()
    cols = ['id', 'producto_nombre', 'modo_falla', 'efecto', 'causa', 'severidad', 'ocurrencia',
            'deteccion', 'rpn', 'control_actual', 'accion_recomendada', 'estado']
    return jsonify({'fmea': [dict(zip(cols, r)) for r in rows]})


# --- (e) ACUERDOS DE CALIDAD (maquila / terceros) ---
@bp.route('/api/aseguramiento/acuerdos-calidad', methods=['GET', 'POST'])
def acuerdos_calidad():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        if user not in _autorizados_escritura():
            return jsonify({'error': 'Solo Calidad/Aseguramiento o Admin'}), 403
        d = request.get_json(silent=True) or {}
        tercero = (d.get('tercero') or '').strip()
        if not tercero:
            return jsonify({'error': 'tercero requerido'}), 400
        tipo = (d.get('tipo') or 'maquila').strip().lower()
        if tipo not in ('maquila', 'proveedor', 'cliente', 'laboratorio'):
            tipo = 'maquila'
        c.execute("INSERT INTO acuerdos_calidad (tercero,tipo,documento_url,version,fecha_efectiva,"
                  "fecha_renovacion,alcance,estado,ultima_auditoria,responsable,observaciones,creado_por) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tercero, tipo, (d.get('documento_url') or '').strip() or None, (d.get('version') or '1').strip(),
                   (d.get('fecha_efectiva') or '').strip() or None, (d.get('fecha_renovacion') or '').strip() or None,
                   (d.get('alcance') or '')[:1000], (d.get('estado') or 'vigente').strip().lower(),
                   (d.get('ultima_auditoria') or '').strip() or None, (d.get('responsable') or '').strip() or None,
                   (d.get('observaciones') or '')[:1000], user))
        aid = c.lastrowid
        _audit_log(c, usuario=user, accion='CREAR_ACUERDO_CALIDAD', tabla='acuerdos_calidad',
                   registro_id=aid, despues={'tercero': tercero, 'tipo': tipo})
        conn.commit()
        return jsonify({'ok': True, 'id': aid}), 201
    rows = c.execute("SELECT id,tercero,tipo,version,fecha_efectiva,fecha_renovacion,estado,ultima_auditoria "
                     "FROM acuerdos_calidad ORDER BY id DESC LIMIT 200").fetchall()
    cols = ['id', 'tercero', 'tipo', 'version', 'fecha_efectiva', 'fecha_renovacion', 'estado', 'ultima_auditoria']
    return jsonify({'acuerdos': [dict(zip(cols, r)) for r in rows]})
