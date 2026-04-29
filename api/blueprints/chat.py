# -*- coding: utf-8 -*-
"""
Chat interno EOS — Fase 1 WhatsApp-style.

Sebastian (29-abr-2026): reemplaza Compromisos+Chat con un sistema
moderno de comunicación interna. Lateral con conversaciones, header
con presencia, mensajes 1-a-1 / grupo / broadcast, asignación de
tareas inline.

Endpoints:
  GET  /chat                              - UI (HTML)
  GET  /api/chat/users                    - usuarios + estado online
  POST /api/chat/heartbeat                - actualiza presence
  GET  /api/chat/threads                  - mis conversaciones
  POST /api/chat/threads                  - crear nueva (directo/grupo/broadcast)
  GET  /api/chat/threads/<id>/messages    - mensajes (paginado)
  POST /api/chat/threads/<id>/messages    - enviar mensaje
  POST /api/chat/threads/<id>/leer        - marcar leído
  POST /api/chat/messages/<id>            - editar/eliminar
  POST /api/chat/threads/<id>/miembros    - agregar miembros (grupos)
"""
from flask import Blueprint, jsonify, request, session, Response
from database import get_db
from config import COMPRAS_USERS

bp = Blueprint('chat', __name__)


@bp.route('/chat')
def chat_ui():
    if 'compras_user' not in session:
        from flask import redirect
        return redirect('/login?next=/chat')
    from templates_py.chat_html import CHAT_HTML
    user = session.get('compras_user', '')
    html = CHAT_HTML.replace('{usuario}', user)
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── PRESENCIA ───────────────────────────────────────────────────────
@bp.route('/api/chat/heartbeat', methods=['POST'])
def chat_heartbeat():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    c.execute("""
        INSERT INTO chat_user_presence (username, last_heartbeat, estado, display_name)
        VALUES (?, datetime('now'), 'conectado', ?)
        ON CONFLICT(username) DO UPDATE SET
          last_heartbeat = datetime('now'),
          estado = 'conectado'
    """, (user, user.capitalize()))
    conn.commit()
    return jsonify({'ok': True, 'username': user})


@bp.route('/api/chat/users', methods=['GET'])
def chat_users():
    """Lista todos los usuarios del sistema con su estado de presencia."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    me = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    # Leer presence (auto-degradar a 'desconectado' si > 90s sin heartbeat)
    rows = c.execute("""
        SELECT username,
               COALESCE(display_name, username) as display_name,
               CASE
                 WHEN last_heartbeat IS NULL THEN 'desconectado'
                 WHEN (julianday('now') - julianday(last_heartbeat)) * 86400 > 90 THEN 'desconectado'
                 ELSE 'conectado'
               END as estado_real,
               last_heartbeat
        FROM chat_user_presence
    """).fetchall()
    presence = {r[0]: {'display_name': r[1], 'estado': r[2], 'last_heartbeat': r[3]} for r in rows}
    # Fusionar con la lista total de usuarios del sistema
    users = []
    for u in (COMPRAS_USERS or []):
        if u == me:
            continue  # no me listo a mí mismo
        p = presence.get(u, {})
        users.append({
            'username': u,
            'display_name': p.get('display_name') or u.capitalize(),
            'estado': p.get('estado') or 'desconectado',
            'last_heartbeat': p.get('last_heartbeat'),
        })
    # Ordenar: conectados primero, luego alfabético
    users.sort(key=lambda x: (0 if x['estado'] == 'conectado' else 1, x['username']))
    return jsonify({'users': users, 'me': me})


# ─── THREADS ──────────────────────────────────────────────────────────
@bp.route('/api/chat/threads', methods=['GET', 'POST'])
def chat_threads():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.json or {}
        tipo = (d.get('tipo') or 'directo').strip()
        if tipo not in ('directo', 'grupo', 'broadcast'):
            return jsonify({'error': 'tipo invalido'}), 400
        miembros = [u.strip() for u in (d.get('miembros') or []) if u.strip()]
        nombre = (d.get('nombre') or '').strip()

        # Para 1-a-1: si ya existe thread con esos 2 miembros, devolverlo
        if tipo == 'directo' and len(miembros) == 1:
            otro = miembros[0]
            existing = c.execute("""
                SELECT t.id FROM chat_threads t
                WHERE t.tipo='directo' AND t.activo=1
                  AND EXISTS (SELECT 1 FROM chat_thread_members WHERE thread_id=t.id AND username=?)
                  AND EXISTS (SELECT 1 FROM chat_thread_members WHERE thread_id=t.id AND username=?)
                  AND (SELECT COUNT(*) FROM chat_thread_members WHERE thread_id=t.id) = 2
                LIMIT 1
            """, (user, otro)).fetchone()
            if existing:
                return jsonify({'ok': True, 'thread_id': existing[0], 'ya_existia': True})

        # Broadcast: solo creador, al "Todos · HHA Group" único
        if tipo == 'broadcast':
            existing = c.execute("SELECT id FROM chat_threads WHERE tipo='broadcast' LIMIT 1").fetchone()
            if existing:
                return jsonify({'ok': True, 'thread_id': existing[0], 'ya_existia': True})
            nombre = nombre or 'Todos · HHA Group'

        cur = c.execute("""
            INSERT INTO chat_threads (tipo, nombre, creado_por)
            VALUES (?, ?, ?)
        """, (tipo, nombre, user))
        thread_id = cur.lastrowid

        # Yo siempre soy miembro
        c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username, rol)
                     VALUES (?, ?, 'creador')""", (thread_id, user))
        # Agregar miembros adicionales
        for m in miembros:
            if m == user:
                continue
            c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username)
                         VALUES (?, ?)""", (thread_id, m))
        # Para broadcast, agregar TODOS los usuarios
        if tipo == 'broadcast':
            for u in (COMPRAS_USERS or []):
                if u == user:
                    continue
                c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username)
                             VALUES (?, ?)""", (thread_id, u))
        conn.commit()
        return jsonify({'ok': True, 'thread_id': thread_id})

    # GET — mis threads con preview del último mensaje + unread count
    rows = c.execute("""
        SELECT t.id, t.tipo, t.nombre, t.ultimo_mensaje_preview, t.ultimo_mensaje_en,
               t.creado_por,
               m.ultimo_leido_id,
               t.ultimo_mensaje_id,
               (SELECT COUNT(*) FROM chat_messages WHERE thread_id=t.id
                  AND id > COALESCE(m.ultimo_leido_id, 0)
                  AND sender != ? AND eliminado=0) as no_leidos,
               (SELECT GROUP_CONCAT(username, ',') FROM chat_thread_members
                  WHERE thread_id=t.id AND username != ?) as otros_miembros
        FROM chat_threads t
        JOIN chat_thread_members m ON m.thread_id = t.id AND m.username = ?
        WHERE t.activo = 1
        ORDER BY t.ultimo_mensaje_en DESC NULLS LAST, t.creado_en DESC
        LIMIT 100
    """, (user, user, user)).fetchall()
    threads = []
    for r in rows:
        threads.append({
            'id': r[0], 'tipo': r[1], 'nombre': r[2],
            'ultimo_mensaje_preview': r[3], 'ultimo_mensaje_en': r[4],
            'creado_por': r[5],
            'no_leidos': r[8] or 0,
            'otros_miembros': (r[9] or '').split(',') if r[9] else [],
        })
    return jsonify({'threads': threads})


@bp.route('/api/chat/threads/<int:thread_id>/messages', methods=['GET', 'POST'])
def chat_messages(thread_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    # Verificar que soy miembro
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (thread_id, user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403

    if request.method == 'POST':
        d = request.json or {}
        contenido = (d.get('contenido') or '').strip()
        if not contenido:
            return jsonify({'error': 'contenido requerido'}), 400
        tipo = (d.get('tipo_mensaje') or 'texto').strip()
        if tipo not in ('texto', 'tarea', 'compromiso', 'archivo', 'imagen', 'sistema', 'llamado_atencion'):
            tipo = 'texto'
        import json as _json
        meta = _json.dumps(d.get('metadata') or {})
        cur = c.execute("""
            INSERT INTO chat_messages
              (thread_id, sender, contenido, tipo_mensaje, metadata_json,
               tarea_operativa_id, compromiso_id, reply_to_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (thread_id, user, contenido, tipo, meta,
              d.get('tarea_operativa_id'), d.get('compromiso_id'),
              d.get('reply_to_id')))
        msg_id = cur.lastrowid
        # Update thread metadata
        preview = contenido[:120] if tipo == 'texto' else f'[{tipo}] {contenido[:100]}'
        c.execute("""
            UPDATE chat_threads SET
              ultimo_mensaje_id=?, ultimo_mensaje_en=datetime('now'),
              ultimo_mensaje_preview=?
            WHERE id=?
        """, (msg_id, preview, thread_id))
        # Marcar como leído para mí (el sender)
        c.execute("""
            UPDATE chat_thread_members SET ultimo_leido_id=?
            WHERE thread_id=? AND username=?
        """, (msg_id, thread_id, user))
        conn.commit()
        return jsonify({'ok': True, 'message_id': msg_id})

    # GET — paginated (default últimos 50)
    limit = min(int(request.args.get('limit', 50)), 200)
    before_id = request.args.get('before_id')
    where_extra = "AND id < ?" if before_id else ""
    params = [thread_id]
    if before_id:
        params.append(int(before_id))
    params.append(limit)
    rows = c.execute(f"""
        SELECT id, sender, contenido, tipo_mensaje, metadata_json,
               tarea_operativa_id, compromiso_id, reply_to_id,
               creado_en, editado_en, eliminado
        FROM chat_messages
        WHERE thread_id=? AND eliminado=0 {where_extra}
        ORDER BY id DESC
        LIMIT ?
    """, params).fetchall()
    cols = [d[0] for d in c.description]
    messages = [dict(zip(cols, r)) for r in rows]
    messages.reverse()  # cronológico ascendente
    return jsonify({'messages': messages})


@bp.route('/api/chat/threads/<int:thread_id>/leer', methods=['POST'])
def chat_marcar_leido(thread_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    last_msg = c.execute(
        "SELECT MAX(id) FROM chat_messages WHERE thread_id=?",
        (thread_id,)
    ).fetchone()
    last_id = last_msg[0] if last_msg else 0
    c.execute("""
        UPDATE chat_thread_members SET ultimo_leido_id=?
        WHERE thread_id=? AND username=?
    """, (last_id or 0, thread_id, user))
    conn.commit()
    return jsonify({'ok': True, 'ultimo_leido_id': last_id})


@bp.route('/api/chat/messages/<int:message_id>', methods=['DELETE', 'PATCH'])
def chat_mensaje_modificar(message_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    msg = c.execute("SELECT sender FROM chat_messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404
    if msg[0] != user:
        return jsonify({'error': 'Solo el autor puede modificar'}), 403
    if request.method == 'DELETE':
        c.execute("UPDATE chat_messages SET eliminado=1 WHERE id=?", (message_id,))
    else:
        d = request.json or {}
        nuevo = (d.get('contenido') or '').strip()
        if not nuevo:
            return jsonify({'error': 'contenido vacío'}), 400
        c.execute("""
            UPDATE chat_messages SET contenido=?, editado_en=datetime('now')
            WHERE id=?
        """, (nuevo, message_id))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/chat/threads/<int:thread_id>/miembros', methods=['POST'])
def chat_agregar_miembros(thread_id):
    """Agregar miembros a un grupo. Solo el creador."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    th = c.execute("SELECT creado_por, tipo FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
    if not th:
        return jsonify({'error': 'Thread no existe'}), 404
    if th[0] != user:
        return jsonify({'error': 'Solo el creador puede agregar miembros'}), 403
    if th[1] == 'directo':
        return jsonify({'error': 'No se pueden agregar miembros a un chat directo'}), 400
    d = request.json or {}
    miembros = [u.strip() for u in (d.get('miembros') or []) if u.strip()]
    added = 0
    for m in miembros:
        cur = c.execute(
            "INSERT OR IGNORE INTO chat_thread_members (thread_id, username) VALUES (?, ?)",
            (thread_id, m)
        )
        if cur.rowcount > 0:
            added += 1
    conn.commit()
    return jsonify({'ok': True, 'agregados': added})
