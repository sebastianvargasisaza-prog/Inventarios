"""Blueprint Notificaciones in-app — sistema unificado de alertas.

Sebastian (30-abr-2026): "asignacion de tareas con alerta al usuario en la
app". Centralizado: cualquier blueprint puede llamar push_notif() para
dejar aviso a un usuario. El widget global (campana 🔔) se inyecta en
todas las páginas y muestra badge con count + dropdown con últimas.

Tipos típicos:
  chat_msg              mensaje nuevo en hilo
  chat_mencion          @mención en chat
  tarea_asignada        nueva tarea operativa para el usuario
  capacitacion          capacitación nueva asignada
  notif_resuelta        notif de bienestar aprobada/rechazada
  oc_estado             OC pasó a otro estado
  produccion            producción asignada / iniciada
  cronograma            cronograma en riesgo
  capa                  desviación abierta / 5 días
  hallazgo              hallazgo nuevo / cierre vencido
  generico              otros
"""
from flask import Blueprint, jsonify, request, session, Response
import logging
from database import get_db

logger = logging.getLogger(__name__)
bp = Blueprint('notif', __name__)


# ─── Helper público (usado desde otros blueprints) ────────────────────────
def push_notif(destinatario, tipo, titulo, body=None, link=None,
               remitente=None, importante=False):
    """Crea una notificacion in-app para un usuario. No-bloqueante: cualquier
    excepción se logea pero no propaga (no debe romper el flujo principal).

    Args:
        destinatario: username del receptor.
        tipo: string corto identificando el tipo (ver doc del módulo).
        titulo: línea principal (max ~80 chars recomendado).
        body: detalle opcional.
        link: URL relativa para click ("/comunicacion?tarea=123").
        remitente: quien generó (opcional, para mostrar quién avisa).
        importante: si True, badge en rojo + sonido al llegar.

    Returns:
        id del row creado, o None si falló.
    """
    if not destinatario or not tipo or not titulo:
        return None
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("""INSERT INTO notificaciones_app
            (destinatario, tipo, titulo, body, link, remitente, importante)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (destinatario, tipo, titulo, body, link, remitente,
             1 if importante else 0))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        logger.warning('push_notif fallo (%s → %s): %s', tipo, destinatario, e)
        return None


def push_notif_multi(destinatarios, tipo, titulo, body=None, link=None,
                     remitente=None, importante=False):
    """Pushea la misma notificación a varios destinatarios (lista de usernames).
    Útil para tareas asignadas a un grupo, alertas a admins, etc."""
    ids = []
    for d in (destinatarios or []):
        d = (d or '').strip().lower()
        if not d:
            continue
        nid = push_notif(d, tipo, titulo, body, link, remitente, importante)
        if nid:
            ids.append(nid)
    return ids


# ─── Endpoints ──────────────────────────────────────────────────────────
@bp.route('/api/notif/list', methods=['GET'])
def notif_list():
    """Últimas 50 notificaciones del usuario actual."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    solo_no_leidas = request.args.get('solo_no_leidas') == '1'
    conn = get_db()
    sql = """SELECT id, tipo, titulo, body, link, remitente, importante,
                    leido_at, creado_en
             FROM notificaciones_app
             WHERE destinatario=?"""
    params = [user]
    if solo_no_leidas:
        sql += " AND leido_at IS NULL"
    sql += " ORDER BY creado_en DESC LIMIT 50"
    rows = conn.execute(sql, params).fetchall()
    out = [{
        'id': r[0], 'tipo': r[1], 'titulo': r[2], 'body': r[3],
        'link': r[4], 'remitente': r[5], 'importante': bool(r[6]),
        'leido': bool(r[7]),
        'creado_en': r[8],
    } for r in rows]
    no_leidas = sum(1 for x in out if not x['leido'])
    return jsonify({'notificaciones': out, 'no_leidas': no_leidas})


@bp.route('/api/notif/unread-count', methods=['GET'])
def notif_unread_count():
    """Solo el conteo — endpoint liviano para polling cada N segundos."""
    if 'compras_user' not in session:
        return jsonify({'count': 0}), 200
    user = session.get('compras_user', '')
    conn = get_db()
    n = conn.execute(
        "SELECT COUNT(*) FROM notificaciones_app WHERE destinatario=? AND leido_at IS NULL",
        (user,)
    ).fetchone()[0]
    importante = conn.execute(
        "SELECT COUNT(*) FROM notificaciones_app WHERE destinatario=? AND leido_at IS NULL AND importante=1",
        (user,)
    ).fetchone()[0]
    return jsonify({'count': n, 'importantes': importante})


@bp.route('/api/notif/<int:nid>/leer', methods=['POST'])
def notif_marcar_leida(nid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    cur = c.execute(
        "UPDATE notificaciones_app SET leido_at=datetime('now') "
        "WHERE id=? AND destinatario=? AND leido_at IS NULL",
        (nid, user)
    )
    conn.commit()
    return jsonify({'ok': True, 'actualizado': cur.rowcount > 0})


@bp.route('/api/notif/marcar-todas', methods=['POST'])
def notif_marcar_todas():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    cur = c.execute(
        "UPDATE notificaciones_app SET leido_at=datetime('now') "
        "WHERE destinatario=? AND leido_at IS NULL",
        (user,)
    )
    conn.commit()
    return jsonify({'ok': True, 'actualizadas': cur.rowcount})


@bp.route('/api/notif/widget.js')
def notif_widget_js():
    """Widget global — campana flotante con badge + dropdown.
    Se inyecta en TODAS las páginas (excepto /chat /login etc) por after_request.
    """
    if 'compras_user' not in session:
        return Response("// no auth", mimetype="application/javascript")
    js = r"""
(function(){
  var p = window.location.pathname;
  if (p === '/login' || p === '/logout') return;
  if (window.__notifWidgetLoaded) return;
  window.__notifWidgetLoaded = true;

  // Estilos
  var s = document.createElement('style');
  s.textContent = ''+
    '#nw-fab{position:fixed;bottom:20px;right:90px;width:48px;height:48px;border-radius:50%;background:#0f766e;color:#fff;border:none;cursor:pointer;font-size:20px;box-shadow:0 4px 16px rgba(15,118,110,.4);z-index:9997;display:flex;align-items:center;justify-content:center;transition:transform .15s}'+
    '#nw-fab:hover{transform:scale(1.08);background:#115e59}'+
    '#nw-badge{position:absolute;top:-4px;right:-4px;background:#dc2626;color:#fff;border-radius:50%;min-width:20px;height:20px;font-size:11px;font-weight:800;display:none;align-items:center;justify-content:center;padding:0 4px;border:2px solid #fff}'+
    '#nw-panel{position:fixed;bottom:78px;right:20px;width:360px;max-width:92vw;max-height:60vh;background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.18);z-index:9998;display:none;overflow:hidden;border:1px solid #e2e8f0}'+
    '#nw-panel-header{background:#0f766e;color:#fff;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;font-weight:700;font-size:14px}'+
    '#nw-panel-list{overflow-y:auto;max-height:calc(60vh - 90px)}'+
    '.nw-item{padding:10px 14px;border-bottom:1px solid #f1f5f9;cursor:pointer;display:block;text-decoration:none;color:#0f172a;transition:background .15s}'+
    '.nw-item:hover{background:#f8fafc}'+
    '.nw-item.unread{background:#f0fdfa;border-left:3px solid #0f766e}'+
    '.nw-item .t{font-size:13px;font-weight:600;color:#0f172a;margin-bottom:2px}'+
    '.nw-item .b{font-size:11px;color:#64748b;line-height:1.4}'+
    '.nw-item .m{font-size:10px;color:#94a3b8;margin-top:3px}'+
    '#nw-panel-footer{padding:8px 14px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;font-size:12px}'+
    '#nw-panel-footer button{background:none;border:none;color:#0f766e;font-weight:600;cursor:pointer;font-size:12px;padding:0}'+
    '.nw-empty{text-align:center;color:#94a3b8;padding:30px 14px;font-size:13px}';
  document.head.appendChild(s);

  // FAB
  var fab = document.createElement('button');
  fab.id = 'nw-fab';
  fab.title = 'Notificaciones';
  fab.innerHTML = '\u{1F514}<span id="nw-badge">0</span>';
  document.body.appendChild(fab);

  // Panel
  var panel = document.createElement('div');
  panel.id = 'nw-panel';
  panel.innerHTML = ''+
    '<div id="nw-panel-header"><span>\u{1F514} Notificaciones</span><span id="nw-mark-all" style="font-size:11px;cursor:pointer;text-decoration:underline;font-weight:400">Marcar todas leídas</span></div>'+
    '<div id="nw-panel-list"></div>'+
    '<div id="nw-panel-footer"><button onclick="window.__notifClose()">Cerrar</button></div>';
  document.body.appendChild(panel);

  fab.onclick = function(e){
    e.stopPropagation();
    if (panel.style.display === 'block') {
      panel.style.display = 'none';
    } else {
      panel.style.display = 'block';
      cargarLista();
    }
  };
  document.addEventListener('click', function(e){
    if (panel.style.display === 'block' && !panel.contains(e.target) && e.target !== fab) {
      panel.style.display = 'none';
    }
  });
  window.__notifClose = function(){ panel.style.display = 'none'; };

  document.getElementById('nw-mark-all').onclick = async function(e){
    e.stopPropagation();
    try {
      await fetch('/api/notif/marcar-todas', {method:'POST'});
      cargarLista();
      checkUnread();
    } catch(e){}
  };

  function _esc(s){ return (s==null?'':String(s)).replace(/[<>&"']/g, function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]; }); }

  function _tiempoRel(iso){
    if(!iso) return '';
    var d = new Date(iso.replace(' ','T')+'Z');
    var diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'ahora';
    if (diff < 3600) return Math.floor(diff/60) + 'min';
    if (diff < 86400) return Math.floor(diff/3600) + 'h';
    return Math.floor(diff/86400) + 'd';
  }

  function _icono(tipo){
    var map = {chat_msg:'\u{1F4AC}', chat_mencion:'@', tarea_asignada:'✅',
               capacitacion:'\u{1F393}', notif_resuelta:'\u{1F4AC}',
               oc_estado:'\u{1F6D2}', produccion:'\u{1F3ED}',
               cronograma:'\u{1F4C5}', capa:'⚠', hallazgo:'\u{1F50D}'};
    return map[tipo] || '\u{1F514}';
  }

  async function cargarLista(){
    var box = document.getElementById('nw-panel-list');
    box.innerHTML = '<div class="nw-empty">Cargando...</div>';
    try {
      var r = await fetch('/api/notif/list');
      var d = await r.json();
      var items = d.notificaciones || [];
      if (!items.length) {
        box.innerHTML = '<div class="nw-empty">Sin notificaciones ✨</div>';
        return;
      }
      box.innerHTML = items.map(function(n){
        var html = '';
        var icon = _icono(n.tipo);
        var clase = n.leido ? 'nw-item' : 'nw-item unread';
        var elem = n.link ? 'a href="'+_esc(n.link)+'"' : 'div';
        html += '<'+elem+' class="'+clase+'" data-id="'+n.id+'" onclick="window.__notifClick('+n.id+',\''+_esc(n.link||'').replace(/'/g, "\\'")+'\')">';
        html += '<div class="t">'+icon+' '+_esc(n.titulo);
        if (n.importante && !n.leido) html += ' <span style="background:#dc2626;color:#fff;padding:1px 5px;border-radius:4px;font-size:9px">!</span>';
        html += '</div>';
        if (n.body) html += '<div class="b">'+_esc(n.body)+'</div>';
        html += '<div class="m">'+(n.remitente?_esc(n.remitente)+' · ':'')+_tiempoRel(n.creado_en)+'</div>';
        html += '</'+(n.link?'a':'div')+'>';
        return html;
      }).join('');
    } catch(e){
      box.innerHTML = '<div class="nw-empty">Error al cargar.</div>';
    }
  }

  window.__notifClick = function(id, link){
    fetch('/api/notif/'+id+'/leer', {method:'POST'}).catch(function(){});
    if (link) {
      window.location.href = link;
    }
  };

  // Polling de unread count cada 25s
  var lastCount = 0;
  function checkUnread(){
    fetch('/api/notif/unread-count').then(function(r){return r.json();}).then(function(d){
      var n = d.count || 0;
      var b = document.getElementById('nw-badge');
      if (b) {
        if (n > 0) {
          b.textContent = n > 99 ? '99+' : n;
          b.style.display = 'flex';
        } else {
          b.style.display = 'none';
        }
        if (d.importantes > 0) b.style.background = '#dc2626';
        else b.style.background = '#7c3aed';
      }
      // Sonido si hay nuevas
      if (n > lastCount && lastCount > 0) {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.connect(gain); gain.connect(ctx.destination);
          osc.frequency.setValueAtTime(660, ctx.currentTime);
          osc.frequency.exponentialRampToValueAtTime(330, ctx.currentTime + 0.12);
          gain.gain.setValueAtTime(0.12, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
          osc.start(); osc.stop(ctx.currentTime + 0.16);
        } catch(e){}
      }
      lastCount = n;
    }).catch(function(){});
  }
  checkUnread();
  setInterval(checkUnread, 25000);
})();
"""
    resp = Response(js, mimetype="application/javascript")
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    return resp
