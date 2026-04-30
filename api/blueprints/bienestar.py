"""Blueprint Bienestar — notificaciones de empleados + capacitaciones.

Sebastian (30-abr-2026): "falta modulo de notificaciones donde los empleados
notifiquen estado de salud, soliciten permisos, citas, enfermedades... y modulo
de educacion: jefe asigna videos, operario ve, hace autoexamen Claude, da
nota, suma a historial reinducciones".

Dos sub-modulos en un solo blueprint:
  /bienestar  — UI con tabs: Mis notif / Mis capacitaciones / (admin: todas)
  /api/bienestar/notificaciones    — CRUD notif empleados
  /api/bienestar/capacitaciones    — CRUD capacitacion + autoexamen Claude

Acceso:
  - Cualquier autenticado puede crear notificaciones para si mismo y ver/
    intentar sus capacitaciones.
  - Admins (sebastian/alejandro) y jefes de area ven TODAS las notif y
    pueden asignar capacitaciones.
"""
from flask import Blueprint, jsonify, request, session, Response, redirect
import json, logging
from datetime import datetime
from database import get_db
from config import ADMIN_USERS

logger = logging.getLogger(__name__)
bp = Blueprint('bienestar', __name__)

# Jefes de area (pueden ver notificaciones del equipo y asignar capacitaciones)
# Por ahora solo Luis Enrique (jefe planta) + admins. RH (mayra) podria sumarse.
JEFES_AREA = {'sebastian', 'alejandro', 'luis_enrique', 'luisenrique', 'mayra'}

def _is_jefe(user):
    return (user or '').lower() in JEFES_AREA or (user or '').lower() in {u.lower() for u in ADMIN_USERS}


# ─── Pagina principal /bienestar ────────────────────────────────────────────
@bp.route('/bienestar')
def bienestar_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/bienestar')
    from templates_py.bienestar_html import HTML
    user = session.get('compras_user', '')
    es_jefe = 'true' if _is_jefe(user) else 'false'
    html = HTML.replace('{usuario}', user.capitalize()).replace('{es_jefe}', es_jefe)
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── NOTIFICACIONES EMPLEADOS ───────────────────────────────────────────────
@bp.route('/api/bienestar/notificaciones', methods=['GET', 'POST'])
def notificaciones_handler():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(force=True, silent=True) or {}
        tipo = (d.get('tipo') or '').strip().lower()
        if tipo not in ('salud', 'permiso', 'cita_medica', 'enfermedad', 'licencia', 'otro'):
            return jsonify({'error': 'tipo invalido'}), 400
        asunto = (d.get('asunto') or '').strip()
        if not asunto:
            return jsonify({'error': 'asunto requerido'}), 400
        # Default notificar a jefes + admins
        notificado = (d.get('notificado_a') or '').strip() or 'sebastian,luis_enrique'
        c.execute("""INSERT INTO notificaciones_empleados
            (empleado_username, empleado_nombre, tipo, asunto, descripcion,
             fecha_inicio, fecha_fin, adjunto_url, notificado_a)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (user, user.capitalize(), tipo, asunto,
             (d.get('descripcion') or '').strip() or None,
             (d.get('fecha_inicio') or '').strip() or None,
             (d.get('fecha_fin') or '').strip() or None,
             (d.get('adjunto_url') or '').strip() or None,
             notificado))
        conn.commit()
        return jsonify({'ok': True, 'id': c.lastrowid}), 201

    # GET — filtros opcionales:
    #   ?solo_mias=1  → solo las creadas por el usuario actual
    #   ?estado=pendiente → filtra por estado
    #   ?tipo=cita_medica → filtra por tipo
    solo_mias = request.args.get('solo_mias') == '1'
    estado = (request.args.get('estado') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()
    where = []
    params = []
    if solo_mias or not _is_jefe(user):
        where.append('empleado_username=?'); params.append(user)
    if estado:
        where.append('estado=?'); params.append(estado)
    if tipo:
        where.append('tipo=?'); params.append(tipo)
    sql = "SELECT id, empleado_username, empleado_nombre, tipo, asunto, descripcion, " \
          "fecha_inicio, fecha_fin, adjunto_url, estado, notificado_a, " \
          "comentario_jefe, resuelto_por, resuelto_en, creado_en " \
          "FROM notificaciones_empleados"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY creado_en DESC LIMIT 200"
    rows = c.execute(sql, params).fetchall()
    cols = ['id', 'empleado_username', 'empleado_nombre', 'tipo', 'asunto',
            'descripcion', 'fecha_inicio', 'fecha_fin', 'adjunto_url',
            'estado', 'notificado_a', 'comentario_jefe', 'resuelto_por',
            'resuelto_en', 'creado_en']
    return jsonify({
        'notificaciones': [dict(zip(cols, r)) for r in rows],
        'total': len(rows),
        'es_jefe': _is_jefe(user),
    })


@bp.route('/api/bienestar/notificaciones/<int:nid>/resolver', methods=['POST'])
def notificacion_resolver(nid):
    """Jefe aprueba / rechaza una notificacion."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _is_jefe(user):
        return jsonify({'error': 'Solo jefes pueden resolver'}), 403
    d = request.get_json(force=True, silent=True) or {}
    nuevo = (d.get('estado') or '').strip().lower()
    if nuevo not in ('aprobada', 'rechazada', 'vista'):
        return jsonify({'error': 'estado invalido'}), 400
    coment = (d.get('comentario_jefe') or '').strip() or None
    conn = get_db(); c = conn.cursor()
    # Buscar empleado para notificarle el resultado
    fila = c.execute("""SELECT empleado_username, asunto FROM notificaciones_empleados
                        WHERE id=?""", (nid,)).fetchone()
    cur = c.execute("""UPDATE notificaciones_empleados
        SET estado=?, comentario_jefe=COALESCE(?, comentario_jefe),
            resuelto_por=?, resuelto_en=datetime('now')
        WHERE id=?""", (nuevo, coment, user, nid))
    conn.commit()
    if cur.rowcount == 0:
        return jsonify({'error': 'no encontrada'}), 404
    # Push notif in-app al empleado
    if fila:
        try:
            from blueprints.notif import push_notif
            emp_user, asunto = fila
            label = {'aprobada':'✅ aprobada','rechazada':'❌ rechazada','vista':'👁 vista'}.get(nuevo, nuevo)
            push_notif(
                emp_user, 'notif_resuelta',
                f'Tu solicitud "{asunto}" fue {label}',
                body=(coment[:120] if coment else None),
                link='/bienestar', remitente=user
            )
        except Exception:
            pass
    return jsonify({'ok': True, 'id': nid, 'estado': nuevo})


# ─── CAPACITACIONES ──────────────────────────────────────────────────────────
@bp.route('/api/bienestar/capacitaciones', methods=['GET', 'POST'])
def capacitaciones_handler():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # Solo jefes pueden asignar capacitaciones
        if not _is_jefe(user):
            return jsonify({'error': 'Solo jefes asignan capacitaciones'}), 403
        d = request.get_json(force=True, silent=True) or {}
        titulo = (d.get('titulo') or '').strip()
        asignado_a = (d.get('asignado_a') or '').strip().lower()
        if not titulo or not asignado_a:
            return jsonify({'error': 'titulo y asignado_a requeridos'}), 400
        material_tipo = (d.get('material_tipo') or 'video').strip().lower()
        if material_tipo not in ('video', 'pdf', 'notebooklm', 'articulo', 'otro'):
            material_tipo = 'otro'
        c.execute("""INSERT INTO bienestar_capacitaciones
            (titulo, descripcion, material_tipo, material_url, material_notas,
             asignado_a, asignado_por, fecha_limite, nota_minima)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (titulo,
             (d.get('descripcion') or '').strip() or None,
             material_tipo,
             (d.get('material_url') or '').strip() or None,
             (d.get('material_notas') or '').strip() or None,
             asignado_a, user,
             (d.get('fecha_limite') or '').strip() or None,
             int(d.get('nota_minima') or 70)))
        new_id = c.lastrowid
        conn.commit()
        # Notif in-app al operario asignado
        try:
            from blueprints.notif import push_notif
            cuerpo = f'Material: {material_tipo}'
            if d.get('fecha_limite'):
                cuerpo += f' · 📅 hasta {d.get("fecha_limite")}'
            push_notif(
                asignado_a, 'capacitacion',
                f'Capacitación asignada: {titulo}',
                body=cuerpo,
                link='/bienestar',
                remitente=user, importante=True
            )
        except Exception:
            pass
        return jsonify({'ok': True, 'id': new_id}), 201

    # GET — segun rol: empleado solo ve las suyas, jefe ve todas
    where = []; params = []
    if not _is_jefe(user):
        where.append('asignado_a=?'); params.append(user)
    else:
        # filtros opcionales para jefes
        u = (request.args.get('usuario') or '').strip().lower()
        if u: where.append('asignado_a=?'); params.append(u)
    estado = (request.args.get('estado') or '').strip()
    if estado: where.append('estado=?'); params.append(estado)
    sql = "SELECT id, titulo, descripcion, material_tipo, material_url, material_notas, " \
          "asignado_a, asignado_por, fecha_asignacion, fecha_limite, estado, " \
          "nota_minima, nota_obtenida, intentos, completada_en, creado_en " \
          "FROM bienestar_capacitaciones"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY estado='pendiente' DESC, fecha_limite ASC NULLS LAST, creado_en DESC LIMIT 100"
    rows = c.execute(sql, params).fetchall()
    cols = ['id', 'titulo', 'descripcion', 'material_tipo', 'material_url',
            'material_notas', 'asignado_a', 'asignado_por',
            'fecha_asignacion', 'fecha_limite', 'estado', 'nota_minima',
            'nota_obtenida', 'intentos', 'completada_en', 'creado_en']
    return jsonify({
        'capacitaciones': [dict(zip(cols, r)) for r in rows],
        'es_jefe': _is_jefe(user),
        'mi_username': user,
    })


@bp.route('/api/bienestar/capacitaciones/<int:cid>/iniciar-examen', methods=['POST'])
def capacitacion_iniciar_examen(cid):
    """Genera 5 preguntas de autoevaluacion via Claude API basado en titulo +
    descripcion + material_notas. Crea un row en capacitaciones_intentos.

    Si CLAUDE_API_KEY no esta configurado, usa preguntas placeholder
    basadas en el titulo (modo offline para que el flujo funcione igual).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    cap = c.execute("""SELECT id, titulo, descripcion, material_tipo,
                              material_url, material_notas, asignado_a,
                              estado, nota_minima
                       FROM bienestar_capacitaciones WHERE id=?""", (cid,)).fetchone()
    if not cap:
        return jsonify({'error': 'capacitacion no existe'}), 404
    if cap[6] != user and not _is_jefe(user):
        return jsonify({'error': 'No es tu capacitacion'}), 403

    titulo, descr, mat_tipo, mat_url, mat_notas = cap[1], cap[2], cap[3], cap[4], cap[5]

    # Generar preguntas — Claude API si esta disponible
    preguntas = _generar_preguntas_claude(titulo, descr, mat_tipo, mat_url, mat_notas)

    # Crear intento
    c.execute("""INSERT INTO bienestar_capacitaciones_intentos
        (capacitacion_id, empleado_username, preguntas_json)
        VALUES (?,?,?)""", (cid, user, json.dumps(preguntas, ensure_ascii=False)))
    intento_id = c.lastrowid
    # Marcar capacitacion en_curso si estaba pendiente
    c.execute("""UPDATE bienestar_capacitaciones
                 SET estado='en_curso', intentos=intentos+1
                 WHERE id=? AND estado IN ('pendiente','reprobada')""", (cid,))
    conn.commit()
    return jsonify({'ok': True, 'intento_id': intento_id, 'preguntas': preguntas})


@bp.route('/api/bienestar/intentos/<int:int_id>/calificar', methods=['POST'])
def calificar_intento(int_id):
    """Recibe respuestas, llama a Claude para calificar, guarda nota y
    actualiza la capacitacion. Si nota >= nota_minima → completada."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json(force=True, silent=True) or {}
    respuestas = d.get('respuestas') or []
    if not isinstance(respuestas, list) or not respuestas:
        return jsonify({'error': 'respuestas vacias'}), 400
    conn = get_db(); c = conn.cursor()
    intento = c.execute("""SELECT id, capacitacion_id, empleado_username,
                                  preguntas_json
                           FROM bienestar_capacitaciones_intentos WHERE id=?""", (int_id,)).fetchone()
    if not intento:
        return jsonify({'error': 'intento no existe'}), 404
    if intento[2] != user:
        return jsonify({'error': 'no es tu intento'}), 403
    cap_id = intento[1]
    cap = c.execute("""SELECT titulo, descripcion, material_notas, nota_minima
                       FROM bienestar_capacitaciones WHERE id=?""", (cap_id,)).fetchone()
    titulo, descr, mat_notas, nota_minima = cap
    preguntas = json.loads(intento[3])

    # Calificar con Claude (o fallback offline)
    evaluacion, nota = _calificar_respuestas_claude(
        titulo, descr, mat_notas, preguntas, respuestas
    )
    aprobado = nota >= (nota_minima or 70)

    c.execute("""UPDATE bienestar_capacitaciones_intentos
        SET respuestas_json=?, evaluacion_json=?, nota=?, terminado_en=datetime('now')
        WHERE id=?""", (
        json.dumps(respuestas, ensure_ascii=False),
        json.dumps(evaluacion, ensure_ascii=False),
        nota, int_id))

    nuevo_estado = 'completada' if aprobado else 'reprobada'
    c.execute("""UPDATE bienestar_capacitaciones
                 SET estado=?, nota_obtenida=?,
                     completada_en = CASE WHEN ?='completada' THEN datetime('now') ELSE completada_en END
                 WHERE id=?""", (nuevo_estado, nota, nuevo_estado, cap_id))
    conn.commit()
    return jsonify({
        'ok': True, 'nota': nota, 'aprobado': aprobado,
        'nota_minima': nota_minima or 70,
        'evaluacion': evaluacion,
        'estado': nuevo_estado,
    })


@bp.route('/api/bienestar/historial/<usuario>', methods=['GET'])
def historial_capacitaciones(usuario):
    """Historial completo de capacitaciones de un usuario. Visible por el
    propio empleado o por un jefe. Sirve para reinducciones RH."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user != usuario and not _is_jefe(user):
        return jsonify({'error': 'No autorizado'}), 403
    conn = get_db()
    rows = conn.execute("""
        SELECT c.id, c.titulo, c.material_tipo, c.estado,
               c.nota_obtenida, c.nota_minima, c.fecha_asignacion,
               c.completada_en, c.intentos, c.asignado_por
        FROM bienestar_capacitaciones c
        WHERE c.asignado_a=?
        ORDER BY c.fecha_asignacion DESC
    """, (usuario,)).fetchall()
    cols = ['id','titulo','material_tipo','estado','nota_obtenida','nota_minima',
            'fecha_asignacion','completada_en','intentos','asignado_por']
    out = [dict(zip(cols, r)) for r in rows]
    aprobadas = [x for x in out if x['estado'] == 'completada']
    promedio = round(sum(x['nota_obtenida'] or 0 for x in aprobadas) / len(aprobadas)) if aprobadas else None
    return jsonify({
        'usuario': usuario,
        'capacitaciones': out,
        'total': len(out),
        'aprobadas': len(aprobadas),
        'promedio_notas': promedio,
    })


# ─── Helpers Claude API (auto-examen) ──────────────────────────────────────

def _generar_preguntas_claude(titulo, descripcion, material_tipo, material_url, material_notas):
    """Genera 5 preguntas de evaluacion via Claude API. Fallback offline si
    falla o no hay API key. Retorna list[{pregunta, contexto}]."""
    import os
    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
    if not api_key:
        return _preguntas_fallback(titulo, descripcion)
    try:
        import urllib.request, urllib.error
        prompt = f"""Eres un evaluador BPM/calidad para un laboratorio cosmético colombiano (HHA Group / Espagiria, certificación INVIMA).

El jefe de área asignó al operario la siguiente capacitación:

Título: {titulo}
Descripción: {descripcion or '(sin descripción adicional)'}
Material tipo: {material_tipo}
Material URL: {material_url or '(sin url)'}
Notas del jefe sobre el material: {material_notas or '(sin notas adicionales)'}

Genera EXACTAMENTE 5 preguntas de comprensión sobre el tema del título. Las preguntas deben ser:
- Cortas, claras, pertinentes a un operario de planta de cosmética/farmacéutica.
- De respuesta abierta (no opción múltiple).
- Apuntar a comprensión real, no memorística.

Devuelve SOLO un JSON array, sin texto extra, así:
[{{"pregunta": "...", "contexto": "razón de la pregunta"}}, ...]
"""
        body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 1500,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=body, method='POST',
            headers={
                'content-type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = (data.get('content') or [{}])[0].get('text', '').strip()
        # Limpiar fences si Claude las puso
        if text.startswith('```'):
            text = text.split('```', 2)[1]
            if text.lstrip().startswith('json'):
                text = text.lstrip()[4:]
        text = text.strip().strip('`').strip()
        preguntas = json.loads(text)
        if isinstance(preguntas, list) and preguntas:
            return preguntas[:5]
    except Exception as e:
        logger.warning('Claude generar_preguntas fallo, usando fallback: %s', e)
    return _preguntas_fallback(titulo, descripcion)


def _calificar_respuestas_claude(titulo, descripcion, material_notas, preguntas, respuestas):
    """Pide a Claude que califique las respuestas y devuelva nota 0-100 +
    feedback por pregunta. Fallback offline: nota=70 si las respuestas
    son no-vacias, 0 si vacias."""
    import os
    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
    if not api_key:
        return _calificar_fallback(preguntas, respuestas)
    try:
        import urllib.request
        items = []
        for i, p in enumerate(preguntas):
            r = respuestas[i] if i < len(respuestas) else ''
            items.append({
                'pregunta': p.get('pregunta', ''),
                'respuesta': r,
            })
        prompt = f"""Eres un evaluador BPM/calidad. Califica las respuestas del operario a su autoevaluacion.

Capacitación: {titulo}
Descripción: {descripcion or ''}
Notas del jefe: {material_notas or ''}

Preguntas y respuestas:
{json.dumps(items, ensure_ascii=False, indent=2)}

Para CADA pregunta, evalúa la respuesta del operario en una escala 0-20. Considera:
- Comprensión del concepto (no memorización literal)
- Aplicación práctica al contexto de planta cosmética
- Si la respuesta está vacía o irrelevante: 0

Devuelve SOLO un JSON con esta forma:
{{
  "nota_global": <int 0-100>,
  "feedback": [
    {{"pregunta_idx": 0, "puntaje": <0-20>, "feedback": "comentario corto y constructivo"}},
    ...
  ],
  "resumen": "resumen general en 1-2 frases sobre desempeño"
}}
"""
        body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 2000,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=body, method='POST',
            headers={
                'content-type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = (data.get('content') or [{}])[0].get('text', '').strip()
        if text.startswith('```'):
            text = text.split('```', 2)[1]
            if text.lstrip().startswith('json'):
                text = text.lstrip()[4:]
        text = text.strip().strip('`').strip()
        evaluacion = json.loads(text)
        nota = int(evaluacion.get('nota_global', 0))
        nota = max(0, min(100, nota))
        return evaluacion, nota
    except Exception as e:
        logger.warning('Claude calificar fallo, usando fallback: %s', e)
    return _calificar_fallback(preguntas, respuestas)


def _preguntas_fallback(titulo, descripcion):
    """Preguntas genericas cuando Claude API no responde — no dejar al
    operario sin examen. Son razonables para cualquier capacitacion BPM."""
    return [
        {'pregunta': f'Explica con tus palabras: ¿de qué trata "{titulo}"?',
         'contexto': 'Comprensión general del tema'},
        {'pregunta': '¿Por qué es importante esto en una planta de cosméticos / fármacos? Da un ejemplo concreto.',
         'contexto': 'Aplicación práctica'},
        {'pregunta': 'Menciona dos riesgos o errores comunes que esta capacitación busca prevenir.',
         'contexto': 'Identificación de riesgos'},
        {'pregunta': '¿Qué harías si encontraras una situación que viola lo que te enseñaron en esta capacitación?',
         'contexto': 'Toma de decisión y reporte'},
        {'pregunta': 'En tu rol del día a día, ¿en qué momento aplicarías lo aprendido?',
         'contexto': 'Integración con el rol'},
    ]


def _calificar_fallback(preguntas, respuestas):
    """Sin Claude: nota basada en si respondio o no, ~14/20 por respuesta no
    vacia. Devuelve resultado con feedback generico."""
    feedback = []
    total = 0
    for i, p in enumerate(preguntas):
        r = (respuestas[i] if i < len(respuestas) else '').strip()
        if not r or len(r) < 10:
            puntaje = 0; comentario = 'Respuesta vacía o muy corta.'
        else:
            puntaje = 14
            comentario = 'Respuesta registrada (calificación automática sin IA).'
        feedback.append({'pregunta_idx': i, 'puntaje': puntaje, 'feedback': comentario})
        total += puntaje
    nota_global = int(total / max(1, len(preguntas)) * 5)  # 20*5 = 100 max
    return {
        'nota_global': nota_global,
        'feedback': feedback,
        'resumen': 'Calificación offline (Claude no disponible). Revisión manual recomendada.',
    }, nota_global
