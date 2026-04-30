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


@bp.route('/api/chat/widget.js')
def chat_widget_js():
    """JS del widget flotante 💬 que se inyecta en TODAS las paginas
    (excepto /chat /login /logout). Sebastian (29-abr-2026): "vista
    lateral persistente tipo WhatsApp Web — boton flotante en cualquier
    pagina"."""
    if 'compras_user' not in session:
        return Response("// no auth", mimetype="application/javascript")
    js = """
(function(){
  // No inyectar en /chat (seria recursivo) ni en /login
  var p = window.location.pathname;
  if (p === '/chat' || p === '/login' || p === '/logout') return;
  // Idempotente: si ya esta cargado, no re-cargar
  if (window.__chatWidgetLoaded) return;
  window.__chatWidgetLoaded = true;

  // Crear estilos
  var s = document.createElement('style');
  s.textContent = '\\
    #cw-fab{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#7c3aed;color:#fff;border:none;cursor:pointer;font-size:24px;box-shadow:0 4px 16px rgba(124,58,237,.4);z-index:9998;display:flex;align-items:center;justify-content:center;transition:transform .15s}\\
    #cw-fab:hover{transform:scale(1.08)}\\
    #cw-badge{position:absolute;top:-4px;right:-4px;background:#dc2626;color:#fff;border-radius:50%;min-width:22px;height:22px;font-size:12px;font-weight:800;display:flex;align-items:center;justify-content:center;padding:0 4px;border:2px solid #fff}\\
    #cw-toast{position:fixed;bottom:90px;right:20px;background:#1e293b;color:#fff;padding:12px 16px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.3);z-index:9999;max-width:320px;font-size:13px;cursor:pointer;animation:cwSlide .3s ease-out;border-left:4px solid #7c3aed}\\
    @keyframes cwSlide{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}\\
    #cw-panel{position:fixed;bottom:90px;right:20px;width:380px;max-width:calc(100vw - 40px);height:560px;max-height:calc(100vh - 130px);background:#fff;border:1px solid #e7e5e4;border-radius:14px;box-shadow:0 12px 36px rgba(0,0,0,.25);z-index:9997;display:none;flex-direction:column;overflow:hidden}\\
    #cw-panel.open{display:flex}\\
    #cw-panel iframe{flex:1;border:none;background:#fafaf9}\\
    #cw-panel-hdr{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#7c3aed;color:#fff;font-size:13px;font-weight:700}\\
    #cw-panel-close{background:transparent;border:none;color:#fff;font-size:18px;cursor:pointer;padding:0;line-height:1}\\
  ';
  document.head.appendChild(s);

  // Crear FAB
  var fab = document.createElement('button');
  fab.id = 'cw-fab';
  fab.title = 'EOS Chat — clic para abrir / Esc para cerrar';
  fab.innerHTML = '\\u{1F4AC}<span id="cw-badge" style="display:none">0</span>';
  fab.onclick = function(){ togglePanel(); };
  document.body.appendChild(fab);

  // Crear panel embebido
  var panel = document.createElement('div');
  panel.id = 'cw-panel';
  panel.innerHTML = '<div id="cw-panel-hdr">\\u{1F4AC} EOS Chat <button id="cw-panel-close">\\u00D7</button></div><iframe id="cw-iframe" src="" allow="autoplay"></iframe>';
  document.body.appendChild(panel);
  document.getElementById('cw-panel-close').onclick = function(){ togglePanel(false); };
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && panel.classList.contains('open')) togglePanel(false);
  });

  function togglePanel(force){
    var open = (typeof force === 'boolean') ? force : !panel.classList.contains('open');
    if (open) {
      var iframe = document.getElementById('cw-iframe');
      if (!iframe.src || iframe.src === window.location.origin + '/') iframe.src = '/chat';
      panel.classList.add('open');
      // Limpiar badge cuando abre el panel
      var b = document.getElementById('cw-badge');
      if (b) { b.style.display = 'none'; b.textContent = '0'; }
    } else {
      panel.classList.remove('open');
    }
  }

  // Polling cada 15s para detectar mensajes nuevos
  var lastTotal = 0;
  var soundOn = true;
  function checkUnread(){
    fetch('/api/chat/unread-summary').then(function(r){return r.json();}).then(function(d){
      var total = d.total || 0;
      var b = document.getElementById('cw-badge');
      if (b) {
        if (total > 0) {
          b.textContent = total > 99 ? '99+' : total;
          b.style.display = 'flex';
        } else {
          b.style.display = 'none';
        }
      }
      // Toast solo si subio el contador y el panel esta cerrado
      if (total > lastTotal && !panel.classList.contains('open') && lastTotal > 0) {
        var nuevo = total - lastTotal;
        showToast('\\u{1F4AC} ' + nuevo + ' mensaje' + (nuevo>1?'s':'') + ' nuevo' + (nuevo>1?'s':''),
                  'Click para abrir el chat');
        if (soundOn) playPing();
      }
      lastTotal = total;
    }).catch(function(){});
  }

  function showToast(titulo, sub){
    // Quitar toast anterior si existe
    var prev = document.getElementById('cw-toast');
    if (prev) prev.remove();
    var t = document.createElement('div');
    t.id = 'cw-toast';
    t.innerHTML = '<div style="font-weight:700;margin-bottom:2px">'+titulo+'</div><div style="font-size:11px;color:#cbd5e1">'+sub+'</div>';
    t.onclick = function(){ togglePanel(true); t.remove(); };
    document.body.appendChild(t);
    setTimeout(function(){ if (t.parentNode) t.remove(); }, 6000);
  }

  function playPing(){
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
      osc.start(); osc.stop(ctx.currentTime + 0.2);
    } catch(e){}
  }

  // Primer check inmediato + polling 15s
  checkUnread();
  setInterval(checkUnread, 15000);
})();
"""
    return Response(js, mimetype="application/javascript")


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
    # Enriquecer con reacciones (Fase 3) — agrega un dict {emoji: [users]} por msg
    if messages:
        msg_ids = [m['id'] for m in messages]
        placeholders = ','.join('?' * len(msg_ids))
        try:
            r_rows = c.execute(
                f"SELECT message_id, emoji, username FROM chat_reactions "
                f"WHERE message_id IN ({placeholders})",
                msg_ids
            ).fetchall()
            by_msg = {}
            for mid, em, uname in r_rows:
                by_msg.setdefault(mid, {}).setdefault(em, []).append(uname)
            for m in messages:
                m['reactions'] = by_msg.get(m['id'], {})
        except Exception:
            for m in messages:
                m['reactions'] = {}
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


@bp.route('/api/chat/threads/<int:thread_id>/asignar-tarea', methods=['POST'])
def chat_asignar_tarea(thread_id):
    """Crear tarea_operativa desde el chat + insertar mensaje tipo 'tarea'
    linkeado a la tarea + notificar por email a los asignados.

    Sebastian (29-abr-2026): Fase 2 del chat — asignacion de tareas inline.

    Body: {titulo, descripcion, asignado_a (csv), fecha_objetivo (YYYY-MM-DD)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    # Verificar membresia
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (thread_id, user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403

    d = request.json or {}
    titulo = (d.get('titulo') or '').strip()
    descripcion = (d.get('descripcion') or '').strip()
    asignado_a = (d.get('asignado_a') or '').strip()
    fecha_obj = (d.get('fecha_objetivo') or '').strip()

    if not titulo:
        return jsonify({'error': 'titulo requerido'}), 400
    if not asignado_a:
        return jsonify({'error': 'asignado_a requerido (csv: usuario1,usuario2)'}), 400

    # 1. Crear la tarea operativa
    try:
        cur = c.execute("""
            INSERT INTO tareas_operativas
              (titulo, descripcion, tipo, asignado_a, fecha_objetivo, estado,
               origen_tipo, origen_id, creado_por)
            VALUES (?, ?, 'chat_asignacion', ?, ?, 'pendiente',
                    'chat', ?, ?)
        """, (titulo, descripcion or titulo, asignado_a, fecha_obj or '',
              thread_id, user))
        tarea_id = cur.lastrowid
    except Exception as e:
        return jsonify({'error': f'Error creando tarea: {e}'}), 500

    # 2. Insertar mensaje en el chat tipo='tarea' linkeado a la tarea
    contenido = f"📋 {titulo}"
    if fecha_obj:
        contenido += f"  ·  ⏰ {fecha_obj}"
    contenido += f"  ·  → {asignado_a}"
    cur2 = c.execute("""
        INSERT INTO chat_messages
          (thread_id, sender, contenido, tipo_mensaje, tarea_operativa_id)
        VALUES (?, ?, ?, 'tarea', ?)
    """, (thread_id, user, contenido, tarea_id))
    msg_id = cur2.lastrowid

    # 3. Update thread metadata (igual que en POST messages normal)
    preview = f"[tarea] {titulo[:100]}"
    c.execute("""
        UPDATE chat_threads SET
          ultimo_mensaje_id=?, ultimo_mensaje_en=datetime('now'),
          ultimo_mensaje_preview=?
        WHERE id=?
    """, (msg_id, preview, thread_id))
    c.execute("""
        UPDATE chat_thread_members SET ultimo_leido_id=?
        WHERE thread_id=? AND username=?
    """, (msg_id, thread_id, user))
    conn.commit()

    # 4. Notificar por email a los asignados (no-bloqueante)
    try:
        import sys, os, threading
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        from config import USER_EMAILS
        destinos = []
        for asig in asignado_a.split(','):
            asig_clean = asig.strip().lower()
            email = USER_EMAILS.get(asig_clean, '')
            if email:
                destinos.append(email)
        if destinos:
            asunto = f"📋 Nueva tarea asignada: {titulo[:80]}"
            body = (
                f"<h2>Nueva tarea desde el chat EOS</h2>"
                f"<p><b>{user}</b> te asignó:</p>"
                f"<div style='background:#f5f5f4;padding:14px;border-radius:8px;border-left:4px solid #7c3aed'>"
                f"<b>{titulo}</b>"
                + (f"<br><i>{descripcion}</i>" if descripcion and descripcion != titulo else "")
                + (f"<br>⏰ <b>Fecha objetivo:</b> {fecha_obj}" if fecha_obj else "")
                + f"<br>👥 <b>Asignados:</b> {asignado_a}"
                + f"</div>"
                + f"<p>Revisa la tarea en <a href='/chat'>el chat</a> o en /planta → Tareas Operativas.</p>"
                + f"<p style='color:#94a3b8;font-size:11px'>Mensaje automatico HHA Group · EOS</p>"
            )
            notif = SistemaNotificaciones()
            threading.Thread(
                target=notif._enviar_email,
                args=(asunto, body, destinos),
                daemon=True
            ).start()
    except Exception as _e:
        # Falla silenciosa — el chat no debe bloquearse por email
        import logging
        logging.getLogger('chat').warning("Email asignacion tarea fallo: %s", _e)

    return jsonify({
        'ok': True,
        'tarea_id': tarea_id,
        'message_id': msg_id,
        'mensaje': f'Tarea creada y asignada a {asignado_a}'
    })


# ─── Fase 3: Reacciones a mensajes ──────────────────────────────────────
@bp.route('/api/chat/messages/<int:message_id>/react', methods=['POST', 'DELETE'])
def chat_message_reaccion(message_id):
    """Toggle de una reaccion (emoji) a un mensaje.
    POST con body {emoji} agrega; DELETE quita. Idempotente."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    msg = c.execute(
        "SELECT thread_id FROM chat_messages WHERE id=?", (message_id,)
    ).fetchone()
    if not msg:
        return jsonify({'error': 'Mensaje no existe'}), 404
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (msg[0], user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403
    d = request.json or {}
    emoji = (d.get('emoji') or '').strip()
    EMOJIS_OK = ('👍', '❤️', '😂', '🔥', '👀', '✅', '❌', '🙏')
    if emoji not in EMOJIS_OK:
        return jsonify({'error': f'emoji invalido (usar uno de {EMOJIS_OK})'}), 400
    if request.method == 'DELETE':
        c.execute(
            "DELETE FROM chat_reactions WHERE message_id=? AND username=? AND emoji=?",
            (message_id, user, emoji)
        )
    else:
        # Toggle: si ya existe, borrar. Si no, agregar.
        existing = c.execute(
            "SELECT id FROM chat_reactions WHERE message_id=? AND username=? AND emoji=?",
            (message_id, user, emoji)
        ).fetchone()
        if existing:
            c.execute("DELETE FROM chat_reactions WHERE id=?", (existing[0],))
        else:
            c.execute(
                "INSERT INTO chat_reactions (message_id, username, emoji) VALUES (?, ?, ?)",
                (message_id, user, emoji)
            )
    conn.commit()
    # Devolver counts actualizados de ese mensaje
    rows = c.execute(
        "SELECT emoji, COUNT(*) FROM chat_reactions WHERE message_id=? GROUP BY emoji",
        (message_id,)
    ).fetchall()
    return jsonify({
        'ok': True,
        'reactions': [{'emoji': r[0], 'count': r[1]} for r in rows]
    })


# ─── Fase 3: Busqueda global en mensajes ──────────────────────────────
@bp.route('/api/chat/search', methods=['GET'])
def chat_search():
    """Busca en chat_messages por contenido — solo en threads donde el user
    es miembro. Devuelve top 30 matches con contexto."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify({'results': [], 'q': q, 'mensaje': 'Escribe al menos 2 letras'})
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT m.id, m.thread_id, m.sender, m.contenido, m.tipo_mensaje,
               m.creado_en, t.tipo as thread_tipo, t.nombre as thread_nombre
        FROM chat_messages m
        JOIN chat_threads t ON t.id = m.thread_id
        WHERE m.eliminado=0
          AND m.thread_id IN (
            SELECT thread_id FROM chat_thread_members WHERE username=?
          )
          AND LOWER(m.contenido) LIKE LOWER(?)
        ORDER BY m.creado_en DESC
        LIMIT 30
    """, (user, f"%{q}%")).fetchall()
    cols = [d[0] for d in c.description]
    results = [dict(zip(cols, r)) for r in rows]
    return jsonify({'results': results, 'q': q, 'count': len(results)})


# ─── Fase 3: Resumen global de mensajes no leidos (badge widget) ─────
@bp.route('/api/chat/unread-summary', methods=['GET'])
def chat_unread_summary():
    """Devuelve total de mensajes no leidos del usuario para el badge
    del widget flotante. Liviano — usado por polling cada 10-15s."""
    if 'compras_user' not in session:
        return jsonify({'total': 0, 'threads': []}), 200  # 200 silencioso
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT t.id, t.tipo, t.nombre, t.ultimo_mensaje_preview,
                   t.ultimo_mensaje_en, m.username as me_user,
                   m.ultimo_leido_id,
                   (SELECT COUNT(*) FROM chat_messages msg
                    WHERE msg.thread_id=t.id
                      AND msg.eliminado=0
                      AND msg.sender != ?
                      AND (m.ultimo_leido_id IS NULL OR msg.id > m.ultimo_leido_id)
                   ) as unread
            FROM chat_threads t
            JOIN chat_thread_members m ON m.thread_id=t.id
            WHERE m.username=?
        """, (user, user)).fetchall()
        cols = [d[0] for d in c.description]
        threads_unread = [dict(zip(cols, r)) for r in rows if (r[-1] or 0) > 0]
        total = sum(t['unread'] for t in threads_unread)
        return jsonify({'total': total, 'threads': threads_unread})
    except Exception as e:
        return jsonify({'total': 0, 'threads': [], '_err': str(e)}), 200
