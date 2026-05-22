"""Portal de Clientes B2B · Fase 1 · Sebastián 20-may-2026.

Portal MINIMALISTA · 2 módulos: Solicitar (Fase 1) + PQR (Fase 2 · pendiente).
Para Fernando Mesa y mayoristas que hoy mandan pedidos por WhatsApp/email.

Aislamiento:
- Sesión separada del backoffice: usa `session['portal_cliente_id']` en lugar
  de `compras_user`. El cliente NUNCA toca inventario, fórmulas, otros clientes.
- Rutas únicas: `/portal/*` (HTML) y `/api/portal/*` (JSON).
- Sebastián crea las credenciales manualmente (no hay self-signup) ·
  ver /api/admin/portal/credenciales (admin).

Endpoints:
    GET  /portal/login                      · form de login
    POST /api/portal/login                  · valida email + password
    GET  /portal/logout                     · cierra sesión + redirect
    GET  /portal                            · página app (solicitar)
    GET  /api/portal/productos              · catálogo público para pedir
    POST /api/portal/pedidos                · crea pedido B2B
                                             (reusa _integrar_pedido_b2b_al_plan)
    GET  /api/portal/mis-pedidos            · pedidos del cliente logueado
"""
import logging
import time
from flask import Blueprint, jsonify, request, session, redirect, Response

from database import get_db
from audit_helpers import audit_log
from config import ADMIN_USERS

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    # Fallback PBKDF2 si werkzeug no disponible (no debería pasar en EOS)
    import hashlib
    def generate_password_hash(pw):
        salt = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100_000)
        return f'pbkdf2:sha256:100000${salt}${h.hex()}'
    def check_password_hash(stored, pw):
        try:
            _, sch, rest = stored.split(':', 2)
            iters = int(sch.split('sha256:')[1]) if 'sha256:' in sch else 100_000
            salt, h_hex = rest.split('$', 1)[1].split('$')
            h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), iters)
            return h.hex() == h_hex
        except Exception:
            return False

bp = Blueprint('portal', __name__)
log = logging.getLogger('portal')


# ────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ────────────────────────────────────────────────────────────────────

def _require_portal_login():
    """Devuelve (cliente_id, cliente_nombre, email) o None si no logueado."""
    cid = session.get('portal_cliente_id')
    if not cid:
        return None
    return (
        cid,
        session.get('portal_cliente_nombre', ''),
        session.get('portal_email', ''),
    )


# ────────────────────────────────────────────────────────────────────
# LOGIN / LOGOUT
# ────────────────────────────────────────────────────────────────────

_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portal Clientes · Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f766e,#0891b2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#1e293b}
.card{background:#fff;border-radius:16px;padding:32px;max-width:380px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.3)}
h1{color:#0f766e;font-size:22px;margin-bottom:6px}
.sub{color:#64748b;font-size:13px;margin-bottom:22px}
label{display:block;font-size:12px;color:#475569;font-weight:600;margin:14px 0 6px}
input{width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;outline:none}
input:focus{border-color:#0f766e}
button{width:100%;background:#0f766e;color:#fff;border:none;padding:13px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;margin-top:18px}
button:hover{background:#0d635c}
.err{background:#fee2e2;color:#991b1b;padding:10px 12px;border-radius:8px;font-size:12px;margin-top:12px;display:none}
.foot{text-align:center;color:#94a3b8;font-size:11px;margin-top:18px}
</style></head><body>
<div class="card">
  <h1>🌿 Portal Clientes</h1>
  <div class="sub">Espagiria & ÁNIMUS Lab · acceso B2B</div>
  <form id="form-login">
    <label>Email</label>
    <input type="email" id="email" required autocomplete="username">
    <label>Contraseña</label>
    <input type="password" id="password" required autocomplete="current-password">
    <button type="submit">Entrar</button>
    <div class="err" id="err"></div>
  </form>
  <div class="foot">¿No tienes credenciales? Contacta a Sebastián.</div>
</div>
<script>
document.getElementById('form-login').addEventListener('submit', async function(e){
  e.preventDefault();
  var email = document.getElementById('email').value.trim().toLowerCase();
  var pw = document.getElementById('password').value;
  var err = document.getElementById('err');
  err.style.display = 'none';
  try {
    var r = await fetch('/api/portal/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: email, password: pw}),
      credentials: 'same-origin',
    });
    var d = await r.json();
    if (!r.ok) {
      err.textContent = d.error || 'Login fallido';
      err.style.display = 'block';
      return;
    }
    window.location.href = '/portal';
  } catch(ex){
    err.textContent = 'Error de red: ' + ex.message;
    err.style.display = 'block';
  }
});
</script></body></html>
"""


@bp.route('/portal/login', methods=['GET'])
def portal_login_page():
    if session.get('portal_cliente_id'):
        return redirect('/portal')
    return Response(_LOGIN_HTML, mimetype='text/html')


@bp.route('/api/portal/login', methods=['POST'])
def portal_login_api():
    # SEC-FIX · 21-may-2026 · rate-limit + lockout (CVSS 7.5 · brute-force público)
    # Antes: endpoint público B2B sin throttle · enumeración + crack ilimitado.
    # Ahora: usa _is_locked/_record_failure del módulo auth (5 fallos/15min).
    body = request.get_json(silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    pw = body.get('password') or ''
    ip_req = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()
    try:
        from auth import _is_locked, _record_failure, _reset_failures
        if _is_locked(ip_req, email):
            return jsonify({'error': 'Demasiados intentos · esperá 15 min',
                            'codigo': 'RATE_LIMITED'}), 429
    except Exception:
        _is_locked = None
    if not email or not pw:
        return jsonify({'error': 'email y password requeridos'}), 400
    conn = get_db()
    row = conn.execute(
        """SELECT id, cliente_id, cliente_nombre, email, password_hash, activo
           FROM portal_clientes_credenciales
           WHERE LOWER(email) = ? LIMIT 1""",
        (email,),
    ).fetchone()
    if not row:
        # Mensaje genérico anti-enumeración + record failure
        log.info('portal login fallo · email no existe · %s', email)
        try:
            if _is_locked:
                from auth import _record_failure as _rf
                _rf(ip_req, email)
        except Exception: pass
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    cred_id, cid, cnom, _email, pw_hash, activo = row
    if not activo:
        return jsonify({'error': 'Cuenta desactivada · contactá a Sebastián'}), 403
    try:
        ok = check_password_hash(pw_hash, pw)
    except Exception:
        ok = False
    if not ok:
        log.info('portal login fallo · password incorrecto · %s', email)
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    # Sesión nueva para evitar fixation
    session.clear()
    session.permanent = True
    session['portal_cliente_id'] = cid
    session['portal_cliente_nombre'] = cnom
    session['portal_email'] = email
    session['portal_login_time'] = time.time()
    # Track last login
    ip = (request.headers.get('X-Forwarded-For', request.remote_addr or '')
          .split(',')[0].strip())
    try:
        conn.execute(
            """UPDATE portal_clientes_credenciales
               SET ultimo_login_at_utc = datetime('now','utc'),
                   ultimo_login_ip = ?
               WHERE id = ?""",
            (ip, cred_id),
        )
        conn.commit()
    except Exception:
        pass
    return jsonify({'ok': True, 'cliente_nombre': cnom})


@bp.route('/portal/logout', methods=['GET', 'POST'])
def portal_logout():
    session.pop('portal_cliente_id', None)
    session.pop('portal_cliente_nombre', None)
    session.pop('portal_email', None)
    session.pop('portal_login_time', None)
    return redirect('/portal/login')


# ────────────────────────────────────────────────────────────────────
# PÁGINA DEL PORTAL
# ────────────────────────────────────────────────────────────────────

_PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portal Clientes · Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;min-height:100vh;font-size:14px}
header{background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:16px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
header h1{font-size:18px;font-weight:800}
header .meta{font-size:11px;opacity:.9}
header a{color:#fff;text-decoration:none;font-size:12px;background:rgba(255,255,255,.15);padding:6px 10px;border-radius:6px}
.wrap{max-width:780px;margin:0 auto;padding:20px}
.tabs{display:flex;gap:8px;margin-bottom:16px}
.tab{flex:1;padding:11px;background:#fff;border:1px solid #cbd5e1;border-radius:10px 10px 0 0;font-size:14px;font-weight:700;cursor:pointer;color:#475569}
.tab.active{background:#0f766e;color:#fff;border-color:#0f766e}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px;margin-bottom:14px}
.card h2{font-size:15px;color:#0f766e;margin-bottom:10px}
label{display:block;font-size:12px;color:#475569;font-weight:600;margin:10px 0 4px}
input,select,textarea{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:14px;outline:none;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:#0f766e}
button.primary{background:#0f766e;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;margin-top:14px}
button.primary:hover{background:#0d635c}
button.primary:disabled{opacity:.6;cursor:not-allowed}
.lista{display:flex;flex-direction:column;gap:8px}
.pedido{background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:6px;padding:10px 14px}
.pedido.pendiente{border-left-color:#94a3b8}
.pedido.confirmado{border-left-color:#0891b2}
.pedido.en_produccion{border-left-color:#ca8a04}
.pedido.despachado{border-left-color:#16a34a}
.pedido.cancelado{border-left-color:#dc2626;opacity:.7}
.pedido-prod{font-weight:700;font-size:14px}
.pedido-meta{font-size:11px;color:#64748b;margin-top:3px}
.pedido-estado{display:inline-block;background:#e2e8f0;color:#475569;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;margin-top:4px}
.empty{text-align:center;color:#94a3b8;font-style:italic;padding:30px;font-size:13px}
.chip{display:inline-block;background:#e2e8f0;color:#475569;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700}
.chip.libre{background:#d1fae5;color:#065f46}
.chip.ocupada{background:#fef3c7;color:#854d0e}
.chip.sucia{background:#fee2e2;color:#991b1b}
.chip.area{background:#dbeafe;color:#1e40af}
/* Timeline visual del pedido · Sprint D Portal */
.tl{margin-top:14px;padding-top:12px;border-top:1px dashed #cbd5e1;display:flex;flex-direction:column;gap:8px}
.tl-step{display:flex;gap:10px;align-items:flex-start;padding:6px 8px;border-radius:6px;background:#fafafa;border-left:3px solid #cbd5e1;opacity:.55}
.tl-step.completado{opacity:1;background:#ecfdf5;border-left-color:#16a34a}
.tl-step.en_curso{opacity:1;background:#fef3c7;border-left-color:#ca8a04}
.tl-step.rechazado{opacity:1;background:#fee2e2;border-left-color:#dc2626}
.tl-step.pendiente{opacity:.5}
.tl-ico{font-size:18px;line-height:1.2;flex-shrink:0;width:24px;text-align:center}
.tl-body{flex:1;min-width:0}
.tl-lbl{font-size:13px;font-weight:700;color:#1e293b}
.tl-step.pendiente .tl-lbl{color:#94a3b8}
.tl-fecha{font-size:10px;color:#64748b;margin-top:1px}
.tl-det{font-size:11px;color:#475569;margin-top:2px}
.msg{padding:10px 12px;border-radius:8px;font-size:12px;margin-top:10px;display:none}
.msg.ok{background:#d1fae5;color:#065f46}
.msg.err{background:#fee2e2;color:#991b1b}
@media (min-width:680px){
  .row{display:flex;gap:10px}
  .row > div{flex:1}
}
</style></head><body>
<header>
  <div>
    <h1>🌿 Portal Clientes</h1>
    <div class="meta" id="hdr-cliente">Cargando...</div>
  </div>
  <a href="/portal/logout">Cerrar sesión</a>
</header>
<div class="wrap">
  <div class="tabs">
    <button class="tab active" data-tab="solicitar" onclick="setTab('solicitar')">📦 Solicitar</button>
    <button class="tab" data-tab="mis" onclick="setTab('mis')">📋 Mis pedidos</button>
    <button class="tab" data-tab="pqr" onclick="setTab('pqr')">💬 PQR</button>
    <button class="tab" data-tab="mis-pqr" onclick="setTab('mis-pqr')">📜 Mis PQR</button>
  </div>

  <div id="panel-solicitar">
    <div class="card">
      <h2>Solicitar producto</h2>
      <p style="font-size:12px;color:#64748b;margin-bottom:8px">Elegí producto, cantidad y fecha estimada · te confirmamos por correo.</p>
      <label>Producto</label>
      <select id="sol-producto">
        <option value="">— Cargando productos —</option>
      </select>
      <div class="row">
        <div>
          <label>Cantidad (unidades)</label>
          <input id="sol-cant" type="number" min="1" step="1" placeholder="Ej. 100">
        </div>
        <div>
          <label>ml por unidad</label>
          <input id="sol-ml" type="number" min="1" step="1" value="30">
        </div>
      </div>
      <label>Fecha estimada de entrega</label>
      <input id="sol-fecha" type="date">
      <label>Notas (opcional)</label>
      <textarea id="sol-notas" rows="3" placeholder="Detalles, urgencia, etc."></textarea>
      <button class="primary" id="btn-enviar" onclick="enviarPedido()">📨 Enviar solicitud</button>
      <div class="msg" id="sol-msg"></div>
    </div>
  </div>

  <div id="panel-mis" style="display:none">
    <div class="card">
      <h2>Mis pedidos</h2>
      <div id="mis-lista" class="lista"><div class="empty">Cargando...</div></div>
    </div>
  </div>

  <div id="panel-pqr" style="display:none">
    <div class="card">
      <h2>💬 PQR · Petición · Queja · Reclamo · Sugerencia</h2>
      <p style="font-size:12px;color:#64748b;margin-bottom:8px">Contanos qué pasa · revisamos en máximo 5 días hábiles.</p>
      <label>Tipo</label>
      <select id="pqr-tipo">
        <option value="peticion">📨 Petición</option>
        <option value="queja">⚠️ Queja</option>
        <option value="reclamo">🚨 Reclamo</option>
        <option value="sugerencia">💡 Sugerencia</option>
      </select>
      <label>Título corto</label>
      <input id="pqr-titulo" type="text" maxlength="200" placeholder="Ej. Lote llegó con tapa rota">
      <label>Descripción detallada</label>
      <textarea id="pqr-desc" rows="5" maxlength="5000" placeholder="Contanos qué pasó, cuándo, qué esperás de solución..."></textarea>
      <button class="primary" id="btn-pqr" onclick="enviarPqr()">📨 Enviar PQR</button>
      <div class="msg" id="pqr-msg"></div>
    </div>
  </div>

  <div id="panel-mis-pqr" style="display:none">
    <div class="card">
      <h2>📜 Mis PQR</h2>
      <div id="mis-pqr-lista" class="lista"><div class="empty">Cargando...</div></div>
    </div>
  </div>
</div>

<script>
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function setTab(t){
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active', b.dataset.tab===t));
  document.getElementById('panel-solicitar').style.display = (t==='solicitar')?'block':'none';
  document.getElementById('panel-mis').style.display = (t==='mis')?'block':'none';
  document.getElementById('panel-pqr').style.display = (t==='pqr')?'block':'none';
  document.getElementById('panel-mis-pqr').style.display = (t==='mis-pqr')?'block':'none';
  if(t==='mis') cargarMisPedidos();
  if(t==='mis-pqr') cargarMisPqr();
}

async function enviarPqr(){
  var btn = document.getElementById('btn-pqr');
  var msg = document.getElementById('pqr-msg');
  msg.style.display = 'none';
  var tipo = document.getElementById('pqr-tipo').value;
  var titulo = document.getElementById('pqr-titulo').value.trim();
  var desc = document.getElementById('pqr-desc').value.trim();
  if(!titulo){
    msg.className='msg err'; msg.textContent='Falta título'; msg.style.display='block'; return;
  }
  if(desc.length < 10){
    msg.className='msg err'; msg.textContent='Descripción muy corta (≥10 chars)'; msg.style.display='block'; return;
  }
  btn.disabled=true; btn.textContent='Enviando...';
  try{
    var r = await fetch('/api/portal/pqr', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body: JSON.stringify({tipo: tipo, titulo: titulo, descripcion: desc}),
    });
    var d = await r.json();
    if(!r.ok){
      msg.className='msg err'; msg.textContent='Error: '+(d.error||r.status);
      msg.style.display='block';
      btn.disabled=false; btn.textContent='📨 Enviar PQR'; return;
    }
    msg.className='msg ok'; msg.textContent='✓ PQR #'+d.id+' registrado · te respondemos pronto';
    msg.style.display='block';
    document.getElementById('pqr-titulo').value='';
    document.getElementById('pqr-desc').value='';
    btn.disabled=false; btn.textContent='📨 Enviar PQR';
  }catch(e){
    msg.className='msg err'; msg.textContent='Error red: '+e.message;
    msg.style.display='block';
    btn.disabled=false; btn.textContent='📨 Enviar PQR';
  }
}

async function cargarMisPqr(){
  var box = document.getElementById('mis-pqr-lista');
  box.innerHTML = '<div class="empty">Cargando...</div>';
  try{
    var r = await fetch('/api/portal/mis-pqr', {credentials:'same-origin'});
    if(r.status===401){ window.location.href='/portal/login'; return; }
    var d = await r.json();
    var items = d.pqrs || [];
    if(!items.length){
      box.innerHTML = '<div class="empty">Sin PQRs · usá la pestaña PQR para crear uno</div>';
      return;
    }
    var EMOJI = {peticion:'📨', queja:'⚠️', reclamo:'🚨', sugerencia:'💡'};
    box.innerHTML = items.map(p =>
      '<div class="pedido '+esc(p.estado)+'">'
      + '<div class="pedido-prod">'+(EMOJI[p.tipo]||'📨')+' '+esc(p.titulo)+'</div>'
      + '<div class="pedido-meta">'+esc(p.tipo)+' · creado '+esc((p.creado_at_utc||'').slice(0,10))+'</div>'
      + '<span class="pedido-estado">'+esc(p.estado)+'</span>'
      + '<div style="font-size:11px;color:#475569;margin-top:6px;white-space:pre-wrap">'+esc(p.descripcion)+'</div>'
      + (p.respuesta_admin
          ? '<div style="margin-top:8px;padding:8px;background:#dbeafe;border-radius:6px;font-size:11px"><b>Respuesta de '+esc(p.respondido_por||'Espagiria')+':</b><br>'+esc(p.respuesta_admin)+'</div>'
          : '')
      + '</div>'
    ).join('');
  }catch(e){ box.innerHTML='<div class="empty">Error: '+esc(e.message)+'</div>'; }
}

async function cargarSesionYProductos(){
  try{
    var rp = await fetch('/api/portal/productos', {credentials:'same-origin'});
    if(rp.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await rp.json();
    document.getElementById('hdr-cliente').textContent = d.cliente_nombre ? ('Hola, ' + d.cliente_nombre) : '';
    var sel = document.getElementById('sol-producto');
    sel.innerHTML = '<option value="">— Elegí un producto —</option>' +
      (d.productos||[]).map(p=>'<option value="'+esc(p.nombre)+'">'+esc(p.nombre)+'</option>').join('');
  } catch(e){
    document.getElementById('hdr-cliente').textContent = 'Error: ' + e.message;
  }
}

async function enviarPedido(){
  var btn = document.getElementById('btn-enviar');
  var msg = document.getElementById('sol-msg');
  msg.style.display = 'none';
  var producto = document.getElementById('sol-producto').value;
  var cant = parseInt(document.getElementById('sol-cant').value);
  var ml = parseFloat(document.getElementById('sol-ml').value || '30');
  var fecha = document.getElementById('sol-fecha').value;
  var notas = document.getElementById('sol-notas').value.trim();
  if(!producto || !cant || cant<=0){
    msg.className = 'msg err';
    msg.textContent = 'Falta producto o cantidad';
    msg.style.display = 'block';
    return;
  }
  btn.disabled = true; btn.textContent = 'Enviando...';
  try{
    var r = await fetch('/api/portal/pedidos', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body: JSON.stringify({
        producto_nombre: producto,
        cantidad_uds: cant,
        ml_unidad: ml,
        fecha_estimada: fecha,
        notas: notas,
      }),
    });
    var d = await r.json();
    if(!r.ok){
      msg.className = 'msg err';
      msg.textContent = 'Error: ' + (d.error || r.status);
      msg.style.display = 'block';
      btn.disabled = false; btn.textContent = '📨 Enviar solicitud';
      return;
    }
    msg.className = 'msg ok';
    msg.textContent = '✓ Pedido enviado · #' + d.id + ' · ' + (d.kg_b2b||0) + ' kg · te avisamos pronto';
    msg.style.display = 'block';
    // limpiar form
    document.getElementById('sol-cant').value = '';
    document.getElementById('sol-fecha').value = '';
    document.getElementById('sol-notas').value = '';
    btn.disabled = false; btn.textContent = '📨 Enviar solicitud';
  } catch(e){
    msg.className = 'msg err';
    msg.textContent = 'Error de red: ' + e.message;
    msg.style.display = 'block';
    btn.disabled = false; btn.textContent = '📨 Enviar solicitud';
  }
}

async function cargarMisPedidos(){
  var box = document.getElementById('mis-lista');
  box.innerHTML = '<div class="empty">Cargando...</div>';
  try{
    var r = await fetch('/api/portal/mis-pedidos', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    var items = d.pedidos || [];
    if(!items.length){
      box.innerHTML = '<div class="empty">No tenés pedidos todavía · andá a Solicitar</div>';
      return;
    }
    box.innerHTML = items.map(p => {
      var tlHtml = '';
      if (p.timeline && p.timeline.length) {
        tlHtml = '<div class="tl">' + p.timeline.map(function(s){
          var clsState = 'tl-step ' + (s.estado || 'pendiente');
          return '<div class="' + clsState + '">'
               + '<div class="tl-ico">' + esc(s.icon || '·') + '</div>'
               + '<div class="tl-body">'
               +   '<div class="tl-lbl">' + esc(s.label || '') + '</div>'
               +   (s.fecha ? '<div class="tl-fecha">' + esc(s.fecha) + '</div>' : '')
               +   (s.detalle ? '<div class="tl-det">' + esc(s.detalle) + '</div>' : '')
               + '</div></div>';
        }).join('') + '</div>';
      }
      var estLbl = p.estado_visible || p.estado || 'pendiente';
      var estKind = p.estado_visible_kind || 'pendiente';
      var estChipCls = {
        completado: 'libre', en_curso: 'ocupada',
        rechazado: 'sucia', pendiente: 'area',
      }[estKind] || 'area';
      return '<div class="pedido '+esc(p.estado)+'">'
        + '<div class="pedido-prod">'+esc(p.producto_nombre)+'</div>'
        + '<div class="pedido-meta">'+p.cantidad_uds+' uds × '+p.ml_unidad+' ml · '+(p.kg_equivalente||0)+' kg' + (p.fecha_estimada?(' · entrega ~'+esc(p.fecha_estimada)):'')+'</div>'
        + '<span class="chip '+estChipCls+'" style="margin-top:4px;display:inline-block">'+esc(estLbl)+'</span>'
        + (p.notas?'<div style="font-size:11px;color:#64748b;margin-top:6px">📝 '+esc(p.notas)+'</div>':'')
        + tlHtml
        + '</div>';
    }).join('');
  } catch(e){
    box.innerHTML = '<div class="empty">Error: '+esc(e.message)+'</div>';
  }
}

cargarSesionYProductos();
</script></body></html>
"""


@bp.route('/portal', methods=['GET'])
def portal_app_page():
    if not session.get('portal_cliente_id'):
        return redirect('/portal/login')
    return Response(_PORTAL_HTML, mimetype='text/html')


# ────────────────────────────────────────────────────────────────────
# API: productos disponibles para pedir
# ────────────────────────────────────────────────────────────────────

@bp.route('/api/portal/productos', methods=['GET'])
def portal_productos():
    """Catálogo público del portal · solo productos activos con fórmula.

    Sebastián 20-may-2026: el cliente externo NO ve precios ni stock ni
    fórmulas · solo el nombre del producto que puede solicitar.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT producto_nombre
           FROM formula_headers
           WHERE COALESCE(activo, 1) = 1
             AND producto_nombre IS NOT NULL
             AND TRIM(producto_nombre) != ''
           ORDER BY producto_nombre ASC""",
    ).fetchall()
    productos = [{'nombre': r[0]} for r in rows if r[0]]
    return jsonify({
        'productos': productos,
        'total': len(productos),
        'cliente_id': cid,
        'cliente_nombre': cnom,
    })


# ────────────────────────────────────────────────────────────────────
# API: crear pedido
# ────────────────────────────────────────────────────────────────────

@bp.route('/api/portal/pedidos', methods=['POST'])
def portal_crear_pedido():
    """El cliente externo envía un pedido · se inserta en `pedidos_b2b` con
    cliente_id de su credencial · luego invocamos `_integrar_pedido_b2b_al_plan`
    para que se agende automáticamente (misma lógica que el backoffice).
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    body = request.get_json(silent=True) or {}
    producto = (body.get('producto_nombre') or '').strip()
    try:
        cantidad = int(body.get('cantidad_uds') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'cantidad_uds inválida'}), 400
    try:
        ml = float(body.get('ml_unidad') or 30)
    except (TypeError, ValueError):
        return jsonify({'error': 'ml_unidad inválida'}), 400
    fecha = (body.get('fecha_estimada') or '').strip() or None
    notas = (body.get('notas') or '').strip()[:500]

    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if cantidad <= 0:
        return jsonify({'error': 'cantidad_uds debe ser > 0'}), 400
    if ml <= 0:
        return jsonify({'error': 'ml_unidad debe ser > 0'}), 400

    conn = get_db()
    cur = conn.cursor()
    # Validar que el producto exista
    prod_row = cur.execute(
        "SELECT producto_nombre FROM formula_headers WHERE producto_nombre = ?",
        (producto,),
    ).fetchone()
    if not prod_row:
        return jsonify({'error': f"producto '{producto}' no disponible"}), 404

    cur.execute(
        """INSERT INTO pedidos_b2b
             (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
              ml_unidad, fecha_estimada, notas, creado_por)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (cid, cnom, producto, cantidad, ml, fecha,
         notas + (' [via portal]' if notas else 'via portal'),
         f'portal:{email}'),
    )
    pid = cur.lastrowid
    audit_log(cur, usuario=f'portal:{email}', accion='PORTAL_CREAR_PEDIDO',
              tabla='pedidos_b2b', registro_id=pid,
              despues={'cliente_id': cid, 'producto': producto,
                       'cantidad_uds': cantidad, 'ml': ml, 'fecha': fecha})
    conn.commit()

    kg_b2b = round(cantidad * ml / 1000.0, 2)
    integracion = None
    try:
        from blueprints.plan import _integrar_pedido_b2b_al_plan
        integracion = _integrar_pedido_b2b_al_plan(
            cur, pid, producto, kg_b2b, fecha, cnom, f'portal:{email}')
        conn.commit()
    except Exception as _e:
        try: conn.rollback()
        except Exception: pass
        log.warning('integracion B2B portal fallo pid=%s: %s', pid, _e)
        integracion = {'error': str(_e)[:200]}

    # Notif in-app a Sebastián+Catalina (no email · CLAUDE.md memoria)
    try:
        from blueprints.notif import push_notif as _push_notif
        for dest in ('sebastian', 'catalina'):
            _push_notif(
                destinatario=dest,
                tipo='portal_pedido_nuevo',
                titulo=f'📦 Nuevo pedido portal · {cnom}',
                body=f'{producto} · {cantidad} uds × {ml} ml · {kg_b2b} kg' +
                      (f' para {fecha}' if fecha else ''),
                link='/dashboard#programacion',
                remitente=f'portal:{email}',
                importante=False,
            )
    except Exception:
        pass

    return jsonify({
        'ok': True, 'id': pid, 'kg_b2b': kg_b2b,
        'integracion_plan': integracion,
    }), 201


# ────────────────────────────────────────────────────────────────────
# API: mis pedidos
# ────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────
# ADMIN · CRUD de credenciales (sólo admin backoffice)
# ────────────────────────────────────────────────────────────────────

def _require_admin_backoffice():
    """Valida que el caller sea admin del backoffice (no portal)."""
    u = session.get('compras_user', '')
    if not u:
        return None, (jsonify({'error': 'No autenticado'}), 401)
    if u not in ADMIN_USERS:
        return None, (jsonify({'error': 'Solo admin'}), 403)
    return u, None


@bp.route('/api/admin/portal/credenciales', methods=['GET', 'POST'])
def admin_portal_credenciales():
    """GET · lista credenciales del portal (sin password_hash).
       POST · crea credencial nueva · body: {cliente_id, cliente_nombre,
              email, password}.
    """
    u, err = _require_admin_backoffice()
    if err:
        return err
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        rows = c.execute(
            """SELECT id, cliente_id, cliente_nombre, email, activo,
                      creado_por, creado_at_utc, ultimo_login_at_utc,
                      ultimo_login_ip
               FROM portal_clientes_credenciales
               ORDER BY creado_at_utc DESC, id DESC""",
        ).fetchall()
        items = [{
            'id': r[0], 'cliente_id': r[1], 'cliente_nombre': r[2],
            'email': r[3], 'activo': bool(r[4]),
            'creado_por': r[5], 'creado_at_utc': r[6],
            'ultimo_login_at_utc': r[7], 'ultimo_login_ip': r[8],
        } for r in rows]
        return jsonify({'items': items, 'total': len(items)})

    body = request.get_json(silent=True) or {}
    cid = (body.get('cliente_id') or '').strip()
    cnom = (body.get('cliente_nombre') or '').strip()
    email = (body.get('email') or '').strip().lower()
    pw = body.get('password') or ''
    if not (cid and cnom and email and pw):
        return jsonify({'error': 'cliente_id, cliente_nombre, email y password requeridos'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'error': 'email inválido'}), 400
    if len(pw) < 8:
        return jsonify({'error': 'password debe ser >= 8 chars'}), 400
    # Check email único
    existe = c.execute(
        "SELECT id FROM portal_clientes_credenciales WHERE LOWER(email) = ?",
        (email,),
    ).fetchone()
    if existe:
        return jsonify({'error': f'email ya registrado (id={existe[0]})'}), 409
    pw_hash = generate_password_hash(pw)
    c.execute(
        """INSERT INTO portal_clientes_credenciales
             (cliente_id, cliente_nombre, email, password_hash,
              activo, creado_por)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (cid, cnom, email, pw_hash, u),
    )
    new_id = c.lastrowid
    audit_log(c, usuario=u, accion='PORTAL_CREAR_CREDENCIAL',
              tabla='portal_clientes_credenciales', registro_id=new_id,
              despues={'cliente_id': cid, 'email': email,
                       'cliente_nombre': cnom})
    conn.commit()
    return jsonify({
        'ok': True, 'id': new_id,
        'mensaje': f'Credencial creada para {cnom} ({email})',
    }), 201


@bp.route('/api/admin/portal/credenciales/<int:cred_id>', methods=['PATCH', 'DELETE'])
def admin_portal_credencial_uno(cred_id):
    """PATCH · cambia activo / reset password · body: {activo?: bool,
              password?: str}.
       DELETE · soft delete (activo=0).
    """
    u, err = _require_admin_backoffice()
    if err:
        return err
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT id, cliente_id, email, activo FROM portal_clientes_credenciales WHERE id = ?",
        (cred_id,),
    ).fetchone()
    if not row:
        return jsonify({'error': 'credencial no existe'}), 404

    if request.method == 'DELETE':
        c.execute(
            "UPDATE portal_clientes_credenciales SET activo = 0 WHERE id = ?",
            (cred_id,),
        )
        audit_log(c, usuario=u, accion='PORTAL_DESACTIVAR_CREDENCIAL',
                  tabla='portal_clientes_credenciales', registro_id=cred_id,
                  antes={'activo': bool(row[3])}, despues={'activo': False})
        conn.commit()
        return jsonify({'ok': True, 'desactivada': True})

    body = request.get_json(silent=True) or {}
    cambios = []
    sets = []
    params = []
    if 'activo' in body:
        nuevo_activo = 1 if bool(body['activo']) else 0
        sets.append("activo = ?")
        params.append(nuevo_activo)
        cambios.append(f'activo→{bool(nuevo_activo)}')
    if 'password' in body and body['password']:
        pw = body['password']
        if len(pw) < 8:
            return jsonify({'error': 'password debe ser >= 8 chars'}), 400
        sets.append("password_hash = ?")
        params.append(generate_password_hash(pw))
        cambios.append('password reset')
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(cred_id)
    c.execute(
        f"UPDATE portal_clientes_credenciales SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    audit_log(c, usuario=u, accion='PORTAL_ACTUALIZAR_CREDENCIAL',
              tabla='portal_clientes_credenciales', registro_id=cred_id,
              despues={'cambios': cambios})
    conn.commit()
    return jsonify({'ok': True, 'cambios': cambios})


# ────────────────────────────────────────────────────────────────────
# API: mis pedidos
# ────────────────────────────────────────────────────────────────────

def _construir_timeline_pedido(conn, pedido_id, pedido_creado_at, pedido_estado):
    """Sprint D Portal · 20-may-2026 · construye 8 steps del ciclo de
    vida del pedido B2B, derivados de:

      - pedidos_b2b.estado / creado_at (recibido)
      - produccion_programada match por observaciones (#N)
        + sus etapas (mig 139: etapa_disp/elab/env/acond _inicio_at/_fin_at)
      - ebr_ejecuciones.estado (liberado/rechazado)

    Devuelve lista de dicts:
      {key, label, icon, estado: 'completado'|'en_curso'|'pendiente',
       fecha: 'YYYY-MM-DD' | None, detalle: str | None}

    NO se inventa información · si no hay dato, estado='pendiente'.
    """
    timeline = []
    # 1) Recibido (siempre completado si el pedido existe)
    timeline.append({
        'key': 'recibido', 'label': 'Recibido', 'icon': '📨',
        'estado': 'completado',
        'fecha': (pedido_creado_at or '')[:10],
        'detalle': 'Solicitud entró al sistema',
    })

    # 2) Buscar lote vinculado por observaciones LIKE '%(pedido #N)%'
    # o lote dedicado eos_b2b con '· #N · entrega'.
    lote = conn.execute(
        """SELECT id, COALESCE(estado,''), COALESCE(inicio_real_at,''),
                  COALESCE(fin_real_at,''), COALESCE(area_id, 0),
                  COALESCE(fecha_programada,''),
                  COALESCE(etapa_disp_inicio_at,''), COALESCE(etapa_disp_fin_at,''),
                  COALESCE(etapa_elab_inicio_at,''), COALESCE(etapa_elab_fin_at,''),
                  COALESCE(etapa_env_inicio_at,''),  COALESCE(etapa_env_fin_at,''),
                  COALESCE(etapa_acond_inicio_at,''), COALESCE(etapa_acond_fin_at,'')
           FROM produccion_programada
           WHERE (observaciones LIKE ? OR observaciones LIKE ?)
             AND LOWER(COALESCE(estado,'')) != 'cancelado'
           ORDER BY id DESC LIMIT 1""",
        (f'%(pedido #{pedido_id})%', f'%· #{pedido_id} ·%'),
    ).fetchone()

    if lote:
        (lid, lest, l_ini, l_fin, l_area, l_fecha,
         d_ini, d_fin, e_ini, e_fin, n_ini, n_fin, a_ini, a_fin) = lote
        # 2) Confirmado · sabemos que el pedido está integrado al plan
        timeline.append({
            'key': 'confirmado', 'label': 'Confirmado en plan', 'icon': '✅',
            'estado': 'completado',
            'fecha': (l_fecha or '')[:10],
            'detalle': f'Lote #{lid} programado para {(l_fecha or "")[:10]}',
        })
        # 3) En producción · dispensación/elaboración
        if d_fin or e_ini or l_ini:
            est_prod = 'completado' if (e_fin and d_fin) else 'en_curso'
            fechas_prod = [d_ini, d_fin, e_ini, e_fin, l_ini]
            f_ref = next((x for x in fechas_prod if x), '')
            timeline.append({
                'key': 'produciendo', 'label': 'En producción', 'icon': '🏭',
                'estado': est_prod,
                'fecha': (f_ref or '')[:10],
                'detalle': (
                    'Mezclando / elaborando · etapa dispensación + elaboración'
                    if est_prod == 'en_curso'
                    else 'Elaboración terminada'
                ),
            })
        else:
            timeline.append({
                'key': 'produciendo', 'label': 'En producción', 'icon': '🏭',
                'estado': 'pendiente', 'fecha': None, 'detalle': None,
            })

        # 4) Envasado
        if n_ini or n_fin:
            timeline.append({
                'key': 'envasado', 'label': 'Envasado', 'icon': '🍶',
                'estado': 'completado' if n_fin else 'en_curso',
                'fecha': (n_fin or n_ini)[:10] if (n_fin or n_ini) else None,
                'detalle': 'Embotellado / llenado',
            })
        else:
            timeline.append({
                'key': 'envasado', 'label': 'Envasado', 'icon': '🍶',
                'estado': 'pendiente', 'fecha': None, 'detalle': None,
            })

        # 5) Micro QC · derivado del EBR (IPCs micro) · si no hay EBR,
        # heurística: si envasado terminó y acond NO empezó, asumimos en QC.
        ebr_row = conn.execute(
            """SELECT id, COALESCE(estado,''), iniciado_at_utc, completado_at_utc
               FROM ebr_ejecuciones
               WHERE produccion_id = ?
               ORDER BY id DESC LIMIT 1""",
            (lid,),
        ).fetchone()
        micro_estado = 'pendiente'
        micro_fecha = None
        micro_detalle = None
        if n_fin and not a_ini:
            # Envasado terminó, acond no empezó · está en QC/micro
            micro_estado = 'en_curso'
            micro_fecha = (n_fin or '')[:10]
            micro_detalle = 'Esperando resultados de microbiología'
        elif a_ini:
            # Si acond ya empezó, micro pasó OK
            micro_estado = 'completado'
            micro_fecha = (n_fin or a_ini or '')[:10]
            micro_detalle = 'Microbiología conforme'
        timeline.append({
            'key': 'micro_qc', 'label': 'Microbiología', 'icon': '🔬',
            'estado': micro_estado, 'fecha': micro_fecha,
            'detalle': micro_detalle,
        })

        # 6) Acondicionamiento
        if a_ini or a_fin:
            timeline.append({
                'key': 'acondicionamiento', 'label': 'Acondicionamiento',
                'icon': '📦',
                'estado': 'completado' if a_fin else 'en_curso',
                'fecha': (a_fin or a_ini)[:10] if (a_fin or a_ini) else None,
                'detalle': 'Etiquetado / empaque',
            })
        else:
            timeline.append({
                'key': 'acondicionamiento', 'label': 'Acondicionamiento',
                'icon': '📦',
                'estado': 'pendiente', 'fecha': None, 'detalle': None,
            })

        # 7) Liberado QC
        lib_estado = 'pendiente'
        lib_fecha = None
        lib_detalle = None
        if ebr_row:
            ebr_estado = (ebr_row[1] or '').lower()
            if ebr_estado == 'liberado':
                lib_estado = 'completado'
                lib_fecha = (ebr_row[3] or '')[:10] if ebr_row[3] else None
                lib_detalle = 'QC aprobó el lote'
            elif ebr_estado == 'rechazado':
                lib_estado = 'rechazado'
                lib_detalle = 'QC rechazó · contactá soporte'
            elif a_fin:
                lib_estado = 'en_curso'
                lib_detalle = 'En revisión final de QC'
        elif a_fin:
            lib_estado = 'en_curso'
            lib_detalle = 'Pendiente firma de QC'
        timeline.append({
            'key': 'liberado', 'label': 'Liberado QC', 'icon': '✔️',
            'estado': lib_estado, 'fecha': lib_fecha, 'detalle': lib_detalle,
        })
    else:
        # Sin lote vinculado · pedido aún sin programar
        for k, lbl, ico in (
            ('confirmado', 'Confirmado en plan', '✅'),
            ('produciendo', 'En producción', '🏭'),
            ('envasado', 'Envasado', '🍶'),
            ('micro_qc', 'Microbiología', '🔬'),
            ('acondicionamiento', 'Acondicionamiento', '📦'),
            ('liberado', 'Liberado QC', '✔️'),
        ):
            timeline.append({'key': k, 'label': lbl, 'icon': ico,
                             'estado': 'pendiente', 'fecha': None,
                             'detalle': None})

    # 8) Enviado · pedidos_b2b.estado='despachado'
    estado_pedido = (pedido_estado or '').lower()
    if estado_pedido == 'despachado':
        timeline.append({
            'key': 'enviado', 'label': 'Enviado', 'icon': '🚚',
            'estado': 'completado', 'fecha': None,
            'detalle': 'Despachado al cliente',
        })
    else:
        timeline.append({
            'key': 'enviado', 'label': 'Enviado', 'icon': '🚚',
            'estado': 'pendiente', 'fecha': None, 'detalle': None,
        })
    return timeline


@bp.route('/api/portal/mis-pedidos', methods=['GET'])
def portal_mis_pedidos():
    """Pedidos del cliente logueado · solo los SUYOS, nunca de otros.

    Sprint D Portal · 20-may-2026: cada pedido trae `timeline` con 8 steps
    del ciclo de vida (Recibido → Confirmado → En producción → Envasado →
    Micro QC → Acondicionamiento → Liberado QC → Enviado).
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, _ = auth
    conn = get_db()
    rows = conn.execute(
        """SELECT id, producto_nombre, cantidad_uds, ml_unidad, fecha_estimada,
                  estado, notas, creado_at_utc
           FROM pedidos_b2b
           WHERE cliente_id = ?
           ORDER BY creado_at_utc DESC, id DESC
           LIMIT 100""",
        (cid,),
    ).fetchall()
    out = []
    for r in rows:
        uds = int(r[2] or 0); ml = float(r[3] or 0)
        pid = r[0]
        estado = r[5] or 'pendiente'
        creado = r[7] or ''
        try:
            tl = _construir_timeline_pedido(conn, pid, creado, estado)
        except Exception as _e:
            log.warning('timeline pedido %s falló: %s', pid, _e)
            tl = []
        # estado_visible: el último step con 'completado' o 'en_curso'
        estado_visible_lbl = 'Recibido'
        estado_visible_est = 'completado'
        for step in tl:
            if step['estado'] in ('completado', 'en_curso', 'rechazado'):
                estado_visible_lbl = step['label']
                estado_visible_est = step['estado']
        out.append({
            'id': pid,
            'producto_nombre': r[1] or '',
            'cantidad_uds': uds,
            'ml_unidad': ml,
            'kg_equivalente': round(uds * ml / 1000.0, 2),
            'fecha_estimada': r[4] or '',
            'estado': estado,
            'notas': r[6] or '',
            'creado_at': creado,
            'timeline': tl,
            'estado_visible': estado_visible_lbl,
            'estado_visible_kind': estado_visible_est,
        })
    return jsonify({'pedidos': out, 'total': len(out)})


# ────────────────────────────────────────────────────────────────────
# FASE 2 · PQR (Peticiones, Quejas, Reclamos, Sugerencias)
# ────────────────────────────────────────────────────────────────────

_PQR_TIPOS = {'peticion', 'queja', 'reclamo', 'sugerencia'}


@bp.route('/api/portal/pqr', methods=['POST'])
def portal_crear_pqr():
    """Cliente crea un PQR · tipo ∈ {peticion, queja, reclamo, sugerencia}.

    Sebastián 20-may-2026 · Fase 2 del Portal · cierra el módulo PQR.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    body = request.get_json(silent=True) or {}
    tipo = (body.get('tipo') or '').strip().lower()
    titulo = (body.get('titulo') or '').strip()[:200]
    descripcion = (body.get('descripcion') or '').strip()[:5000]
    if tipo not in _PQR_TIPOS:
        return jsonify({
            'error': f'tipo inválido · usar {sorted(_PQR_TIPOS)}',
        }), 400
    if not titulo:
        return jsonify({'error': 'titulo requerido'}), 400
    if len(descripcion) < 10:
        return jsonify({'error': 'descripcion requerida (>= 10 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute(
        """INSERT INTO portal_pqr
             (cliente_id, cliente_nombre, email_cliente, tipo, titulo,
              descripcion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (cid, cnom, email, tipo, titulo, descripcion),
    )
    pqr_id = c.lastrowid
    audit_log(c, usuario=f'portal:{email}', accion='PORTAL_CREAR_PQR',
              tabla='portal_pqr', registro_id=pqr_id,
              despues={'cliente_id': cid, 'tipo': tipo, 'titulo': titulo})
    conn.commit()

    # Notif a Calidad + Sebastián (las quejas/reclamos a Calidad por gobierno
    # INVIMA · peticiones/sugerencias también porque suelen ser de producto).
    try:
        from blueprints.notif import push_notif as _push_notif
        destinatarios = ['sebastian']
        try:
            from config import CALIDAD_USERS
            destinatarios.extend(sorted(CALIDAD_USERS))
        except Exception:
            pass
        emoji = {'peticion': '📨', 'queja': '⚠️',
                 'reclamo': '🚨', 'sugerencia': '💡'}.get(tipo, '📨')
        # Quejas y reclamos como importantes
        es_importante = tipo in ('queja', 'reclamo')
        for dest in set(destinatarios):
            _push_notif(
                destinatario=dest,
                tipo=f'portal_pqr_{tipo}',
                titulo=f'{emoji} PQR · {tipo} · {cnom}',
                body=f'{titulo[:80]} · click para ver',
                link='/admin?tab=portal_pqr',
                remitente=f'portal:{email}',
                importante=es_importante,
            )
    except Exception:
        pass

    return jsonify({
        'ok': True, 'id': pqr_id, 'tipo': tipo,
        'mensaje': 'PQR registrado · te respondemos a la brevedad',
    }), 201


@bp.route('/api/portal/mis-pqr', methods=['GET'])
def portal_mis_pqr():
    """PQRs del cliente logueado · solo los SUYOS."""
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, _ = auth
    conn = get_db()
    rows = conn.execute(
        """SELECT id, tipo, titulo, descripcion, estado,
                  respuesta_admin, respondido_por, respondido_at_utc,
                  creado_at_utc
           FROM portal_pqr
           WHERE cliente_id = ?
           ORDER BY creado_at_utc DESC, id DESC
           LIMIT 100""",
        (cid,),
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            'id': r[0], 'tipo': r[1], 'titulo': r[2] or '',
            'descripcion': r[3] or '', 'estado': r[4] or 'abierto',
            'respuesta_admin': r[5] or '',
            'respondido_por': r[6] or '',
            'respondido_at_utc': r[7] or '',
            'creado_at_utc': r[8] or '',
        })
    return jsonify({'pqrs': out, 'total': len(out)})


# ─── ADMIN PQR ──────────────────────────────────────────────────────

@bp.route('/api/admin/portal/pqr', methods=['GET'])
def admin_portal_pqr_lista():
    """Lista TODOS los PQRs (admin/calidad ven todos · clientes solo los suyos).

    Filtros opcionales:
      ?estado=abierto|en_revision|respondido|cerrado
      ?tipo=peticion|queja|reclamo|sugerencia
      ?cliente_id=XXX
    """
    u, err = _require_admin_backoffice()
    if err:
        return err
    estado = (request.args.get('estado') or '').strip().lower()
    tipo = (request.args.get('tipo') or '').strip().lower()
    cli = (request.args.get('cliente_id') or '').strip()
    where = ['1=1']
    params = []
    if estado in ('abierto', 'en_revision', 'respondido', 'cerrado'):
        where.append('estado = ?'); params.append(estado)
    if tipo in _PQR_TIPOS:
        where.append('tipo = ?'); params.append(tipo)
    if cli:
        where.append('cliente_id = ?'); params.append(cli)
    sql = (
        "SELECT id, cliente_id, cliente_nombre, email_cliente, tipo, "
        "titulo, descripcion, estado, respuesta_admin, respondido_por, "
        "respondido_at_utc, creado_at_utc, actualizado_at_utc "
        "FROM portal_pqr "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY (estado='abierto') DESC, creado_at_utc DESC, id DESC "
        "LIMIT 500"
    )
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    items = [{
        'id': r[0], 'cliente_id': r[1], 'cliente_nombre': r[2],
        'email_cliente': r[3], 'tipo': r[4], 'titulo': r[5],
        'descripcion': r[6], 'estado': r[7],
        'respuesta_admin': r[8] or '',
        'respondido_por': r[9] or '',
        'respondido_at_utc': r[10] or '',
        'creado_at_utc': r[11] or '',
        'actualizado_at_utc': r[12] or '',
    } for r in rows]
    return jsonify({'items': items, 'total': len(items)})


@bp.route('/api/admin/portal/pqr/<int:pqr_id>', methods=['PATCH'])
def admin_portal_pqr_responder(pqr_id):
    """Admin/calidad responde un PQR o cambia su estado.

    Body: {estado?, respuesta?}
    """
    u, err = _require_admin_backoffice()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT id, estado, respuesta_admin FROM portal_pqr WHERE id = ?",
        (pqr_id,),
    ).fetchone()
    if not row:
        return jsonify({'error': 'PQR no existe'}), 404

    sets = []
    params = []
    cambios = {}
    nuevo_estado = body.get('estado')
    if nuevo_estado:
        nuevo_estado = nuevo_estado.strip().lower()
        if nuevo_estado not in ('abierto', 'en_revision', 'respondido', 'cerrado'):
            return jsonify({'error': 'estado inválido'}), 400
        sets.append('estado = ?'); params.append(nuevo_estado)
        cambios['estado'] = nuevo_estado
    respuesta = body.get('respuesta')
    if respuesta is not None:
        respuesta = str(respuesta).strip()[:5000]
        sets.append('respuesta_admin = ?'); params.append(respuesta)
        sets.append('respondido_por = ?'); params.append(u)
        sets.append("respondido_at_utc = datetime('now','utc')")
        cambios['respuesta_len'] = len(respuesta)
        cambios['respondido_por'] = u
        # Si responde y no cambió estado, marcar como respondido
        if 'estado' not in cambios:
            sets.append("estado = 'respondido'")
            cambios['estado'] = 'respondido'
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    sets.append("actualizado_at_utc = datetime('now','utc')")
    params.append(pqr_id)
    c.execute(
        f"UPDATE portal_pqr SET {', '.join(sets)} WHERE id = ?", params,
    )
    audit_log(c, usuario=u, accion='PORTAL_RESPONDER_PQR',
              tabla='portal_pqr', registro_id=pqr_id,
              antes={'estado_prev': row[1]}, despues=cambios)

    # Notif al cliente vía push_notif si tiene usuario interno mapeado
    # (no en este flujo · el cliente externo NO tiene compras_user)
    # · simplemente actualizamos y el cliente lo ve al refrescar /portal.

    conn.commit()
    return jsonify({'ok': True, 'cambios': cambios})

