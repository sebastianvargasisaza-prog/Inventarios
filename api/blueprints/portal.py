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
import secrets
import time
from flask import Blueprint, jsonify, request, session, redirect, Response

from database import get_db
from audit_helpers import audit_log
from config import ADMIN_USERS, COMPRAS_USERS

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
    """Devuelve (cliente_id, cliente_nombre, email) o None si no logueado.

    SEC-FIX · 22-may-2026 · Bug #3 audit Portal · revalida activo=1
    contra portal_clientes_credenciales · cliente desactivado por mora/fraude
    no sigue operando 60 días. Cache 60s para evitar query por request.
    """
    import time as _t
    cid = session.get('portal_cliente_id')
    if not cid:
        return None
    last_check = session.get('portal_activo_check_ts', 0)
    now_ts = _t.time()
    if now_ts - last_check > 60:  # revalidar cada 60s
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT activo FROM portal_clientes_credenciales WHERE cliente_id=? LIMIT 1",
                (cid,),
            ).fetchone()
            if not row or not row[0]:
                session.clear()
                return None
            session['portal_activo_check_ts'] = now_ts
        except Exception:
            pass  # graceful · si falla DB no expulsamos al cliente
    return (
        cid,
        session.get('portal_cliente_nombre', ''),
        session.get('portal_email', ''),
    )


# ────────────────────────────────────────────────────────────────────
# LOGIN / LOGOUT
# ────────────────────────────────────────────────────────────────────

_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Portal Clientes</title>
<meta name="application-name" content="EOS · Portal">
<meta name="apple-mobile-web-app-title" content="EOS Portal">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="description" content="EOS · Portal Clientes B2B · Espagiria & ÁNIMUS Lab">
<meta name="author" content="HHA Group">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=eos11">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=eos11">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png?v=eos11">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:radial-gradient(ellipse at top,#1e1b4b 0%,#0f172a 50%,#0a0a0f 100%);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;color:#e2e8f0;}
.card{background:rgba(30,41,59,0.7);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid rgba(167,139,250,0.2);border-radius:20px;padding:48px 40px;width:100%;max-width:440px;box-shadow:0 20px 60px rgba(109,40,217,0.15);}
.logo{text-align:center;margin-bottom:36px;}
.brand-mark{display:inline-flex;align-items:center;justify-content:center;width:80px;height:80px;border-radius:18px;margin-bottom:18px;box-shadow:0 12px 36px rgba(109,40,217,0.45);}
.brand-name{font-size:30px;font-weight:800;letter-spacing:-0.8px;background:linear-gradient(135deg,#c4b5fd,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px;}
.brand-tag{color:#a78bfa;font-size:12px;font-style:italic;margin-bottom:8px;}
.brand-sub{color:#cbd5e1;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:14px;}
.brand-by{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;}
.brand-by strong{color:#cbd5e1;}
label{display:block;color:#94a3b8;font-size:0.8em;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;}
.fg{margin-bottom:20px;}
input[type=email],input[type=password]{width:100%;background:rgba(15,23,42,0.6);border:1px solid #334155;border-radius:10px;padding:14px 16px;color:white;font-size:1em;outline:none;transition:.2s;}
input[type=email]:focus,input[type=password]:focus{border-color:#a78bfa;background:rgba(15,23,42,0.9);box-shadow:0 0 0 3px rgba(167,139,250,0.15);}
.btn{width:100%;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;border:none;border-radius:10px;padding:14px;font-size:1em;font-weight:700;cursor:pointer;margin-top:8px;transition:.2s;letter-spacing:0.3px;}
.btn:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(109,40,217,0.4);}
.err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#f87171;padding:12px 16px;border-radius:8px;font-size:0.88em;margin-bottom:20px;text-align:center;display:none;}
.help{text-align:center;color:#475569;font-size:0.78em;margin-top:14px;}
.help a{color:#a78bfa;text-decoration:none;}
.app-footer{margin-top:32px;text-align:center;font-size:10px;color:#475569;letter-spacing:0.5px;line-height:1.6;}
.app-footer strong{color:#94a3b8;}
@media(max-width:480px){
  .card{padding:36px 24px;}
  .brand-name{font-size:26px;}
}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <span class="brand-mark" style="color:#6d28d9;" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="64" height="64" fill="none" stroke="#a78bfa" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#a78bfa"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>
      </svg>
    </span>
    <div class="brand-name">EOS</div>
    <div class="brand-tag">Todo el holding, al frente</div>
    <div class="brand-sub">Portal Clientes B2B</div>
    <div class="brand-by">by <strong>HHA Group</strong></div>
  </div>
  <div class="err" id="err"></div>
  <form id="form-login">
    <div class="fg"><label>Email</label><input type="email" id="email" placeholder="cliente@empresa.com" required autocomplete="username" autofocus></div>
    <div class="fg"><label>Contraseña</label><input type="password" id="password" placeholder="••••••••" required autocomplete="current-password"></div>
    <button type="submit" class="btn">Ingresar →</button>
  </form>
  <div class="help">¿No tenés credenciales? Contactá a tu ejecutivo.</div>
</div>
<footer class="app-footer">
  <div><strong>EOS v1.0</strong> &middot; Edición Espagiria</div>
  <div style="margin-top:4px;">Desarrollado por <strong>HHA Group</strong></div>
  <div style="margin-top:6px;color:#334155;">&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>
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
    # P0 audit 26-may-2026 · NEVER fail-open en endpoint público externo.
    # Bug histórico: `from auth import ..., _reset_failures` levantaba
    # ImportError (símbolo no existía) · except silenciaba todo · rate-limit
    # quedaba inactivo y brute-force ilimitado. Importamos arriba sin try;
    # si falla, queremos 500 para que el deploy lo detecte de inmediato.
    from auth import _is_locked, _record_failure, _clear_attempts
    if _is_locked(ip_req, email):
        # Logging anti-enumeración: NO mostrar email en log público
        try:
            import hashlib as _h
            _eh = _h.sha256((email or '').encode()).hexdigest()[:10]
            log.info('portal login rate-limited · ip=%s email_hash=%s', ip_req, _eh)
        except Exception:
            pass
        return jsonify({'error': 'Demasiados intentos · esperá 15 min',
                        'codigo': 'RATE_LIMITED'}), 429
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
        # Logging hashed · no plaintext email (Habeas Data L1581 + anti-enum)
        try:
            import hashlib as _h
            _eh = _h.sha256((email or '').encode()).hexdigest()[:10]
            log.info('portal login fallo · email_hash=%s · email_unknown', _eh)
        except Exception: pass
        try:
            _record_failure(ip_req, email)
        except Exception as _rf_e:
            log.warning('record_failure fallo: %s', _rf_e)
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    cred_id, cid, cnom, _email, pw_hash, activo = row
    if not activo:
        return jsonify({'error': 'Cuenta desactivada · contactá a Sebastián'}), 403
    try:
        ok = check_password_hash(pw_hash, pw)
    except Exception:
        ok = False
    if not ok:
        try:
            import hashlib as _h
            _eh = _h.sha256((email or '').encode()).hexdigest()[:10]
            log.info('portal login fallo · email_hash=%s · bad_password', _eh)
        except Exception: pass
        try:
            _record_failure(ip_req, email)
        except Exception as _rf_e:
            log.warning('record_failure fallo: %s', _rf_e)
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    # Sesión nueva para evitar fixation
    # Reset failures tras login exitoso · usa _clear_attempts (alias _reset_failures)
    try:
        _clear_attempts(ip_req, email)
    except Exception as _cl_e:
        log.warning('clear_attempts fallo: %s', _cl_e)
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
<html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EOS · Portal Clientes</title>
<meta name="theme-color" content="#6d28d9">
<meta name="application-name" content="EOS · Portal">
<meta name="apple-mobile-web-app-title" content="EOS Portal">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="author" content="HHA Group">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=eos11">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=eos11">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png?v=eos11">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:radial-gradient(ellipse at top,#1e1b4b 0%,#0f172a 50%,#0a0a0f 100%);
     color:#e2e8f0;min-height:100vh;font-size:14px}
header{background:rgba(30,41,59,0.7);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
       border-bottom:1px solid rgba(167,139,250,0.2);
       color:#fff;padding:14px 22px;display:flex;justify-content:space-between;align-items:center;
       flex-wrap:wrap;gap:10px;position:sticky;top:0;z-index:10}
header .brand{display:flex;align-items:center;gap:12px}
header .brand-mark{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;
                   border-radius:10px;background:rgba(109,40,217,.18);box-shadow:0 4px 12px rgba(109,40,217,0.25)}
header h1{font-size:18px;font-weight:800;letter-spacing:-0.4px;
          background:linear-gradient(135deg,#c4b5fd,#a78bfa);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
header .sub{font-size:10px;color:#a78bfa;font-style:italic;font-weight:500}
header .meta{font-size:11px;color:#cbd5e1;margin-top:2px}
header a.logout{color:#cbd5e1;text-decoration:none;font-size:12px;font-weight:600;
                background:rgba(167,139,250,.12);padding:7px 14px;border-radius:8px;
                border:1px solid rgba(167,139,250,.25);transition:.15s}
header a.logout:hover{background:rgba(167,139,250,.22);color:#fff}
.wrap{max-width:820px;margin:0 auto;padding:24px 18px 60px}
.tabs{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}
.tab{flex:1;min-width:120px;padding:11px 12px;background:rgba(30,41,59,0.5);
     border:1px solid rgba(167,139,250,.15);border-radius:10px;font-size:13px;
     font-weight:700;cursor:pointer;color:#94a3b8;transition:.15s;font-family:inherit}
.tab:hover{background:rgba(30,41,59,0.7);color:#e2e8f0;border-color:rgba(167,139,250,.3)}
.tab.active{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;
            border-color:transparent;box-shadow:0 6px 18px rgba(109,40,217,.35)}
.card{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
      border:1px solid rgba(167,139,250,.15);border-radius:14px;padding:22px;margin-bottom:14px;
      box-shadow:0 8px 24px rgba(0,0,0,.18)}
.card h2{font-size:16px;font-weight:800;margin-bottom:6px;
         background:linear-gradient(135deg,#c4b5fd,#a78bfa);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.card > p{color:#94a3b8;font-size:12px;margin-bottom:12px}
label{display:block;font-size:11px;color:#94a3b8;font-weight:700;
      margin:14px 0 6px;text-transform:uppercase;letter-spacing:.5px}
input,select,textarea{width:100%;padding:12px 14px;
                       background:rgba(15,23,42,0.7);border:1px solid #334155;
                       border-radius:10px;font-size:14px;outline:none;font-family:inherit;
                       color:#e2e8f0;transition:.2s}
input::placeholder,textarea::placeholder{color:#64748b}
input:focus,select:focus,textarea:focus{border-color:#a78bfa;background:rgba(15,23,42,0.9);
                                          box-shadow:0 0 0 3px rgba(167,139,250,.12)}
select option{background:#1e1b4b;color:#e2e8f0}
button.primary{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border:none;
                padding:13px 24px;border-radius:10px;font-size:14px;font-weight:700;
                cursor:pointer;margin-top:16px;letter-spacing:.3px;transition:.15s;font-family:inherit}
button.primary:hover{transform:translateY(-1px);box-shadow:0 10px 24px rgba(109,40,217,.45)}
button.primary:disabled{opacity:.5;cursor:not-allowed;transform:none;box-shadow:none}
.lista{display:flex;flex-direction:column;gap:10px}
.pedido{background:rgba(15,23,42,0.6);border:1px solid rgba(167,139,250,.12);
        border-left:4px solid #a78bfa;border-radius:10px;padding:14px 18px}
.pedido.pendiente{border-left-color:#94a3b8}
.pedido.confirmado{border-left-color:#a78bfa}
.pedido.en_produccion{border-left-color:#f59e0b}
.pedido.despachado{border-left-color:#16a34a}
.pedido.cancelado{border-left-color:#dc2626;opacity:.6}
.pedido-prod{font-weight:700;font-size:14px;color:#e2e8f0}
.pedido-meta{font-size:11px;color:#94a3b8;margin-top:3px}
.pedido-estado{display:inline-block;background:rgba(167,139,250,.15);color:#c4b5fd;
                padding:3px 10px;border-radius:8px;font-size:10px;font-weight:700;
                text-transform:uppercase;letter-spacing:.5px;margin-top:6px}
.empty{text-align:center;color:#64748b;font-style:italic;padding:30px;font-size:13px}
.chip{display:inline-block;background:rgba(148,163,184,.15);color:#cbd5e1;
      padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700}
.chip.libre{background:rgba(22,163,74,.18);color:#86efac}
.chip.ocupada{background:rgba(202,138,4,.2);color:#fcd34d}
.chip.sucia{background:rgba(220,38,38,.2);color:#fca5a5}
.chip.area{background:rgba(167,139,250,.18);color:#c4b5fd}
.tl{margin-top:14px;padding-top:12px;border-top:1px dashed rgba(167,139,250,.2);
    display:flex;flex-direction:column;gap:8px}
.tl-step{display:flex;gap:10px;align-items:flex-start;padding:8px 10px;border-radius:8px;
         background:rgba(15,23,42,0.5);border-left:3px solid rgba(148,163,184,.3);opacity:.55}
.tl-step.completado{opacity:1;background:rgba(22,163,74,.12);border-left-color:#16a34a}
.tl-step.en_curso{opacity:1;background:rgba(202,138,4,.12);border-left-color:#f59e0b}
.tl-step.rechazado{opacity:1;background:rgba(220,38,38,.12);border-left-color:#dc2626}
.tl-step.pendiente{opacity:.45}
.tl-ico{font-size:18px;line-height:1.2;flex-shrink:0;width:24px;text-align:center}
.tl-body{flex:1;min-width:0}
.tl-lbl{font-size:13px;font-weight:700;color:#e2e8f0}
.tl-step.pendiente .tl-lbl{color:#64748b}
.tl-fecha{font-size:10px;color:#94a3b8;margin-top:1px}
.tl-det{font-size:11px;color:#cbd5e1;margin-top:2px}
.msg{padding:11px 14px;border-radius:10px;font-size:13px;margin-top:12px;display:none;
     border-left:3px solid}
.msg.ok{background:rgba(22,163,74,.12);color:#86efac;border-left-color:#16a34a;display:block}
.msg.err{background:rgba(220,38,38,.12);color:#fca5a5;border-left-color:#dc2626;display:block}
.app-footer{text-align:center;font-size:10px;color:#475569;letter-spacing:.5px;
            line-height:1.6;padding:24px 16px 32px;margin-top:20px}
.app-footer strong{color:#94a3b8}
@media (min-width:680px){
  .row{display:flex;gap:10px}
  .row > div{flex:1}
}
</style></head><body>
<header>
  <div class="brand">
    <span class="brand-mark" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="32" height="32" fill="none" stroke="#a78bfa" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#a78bfa"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>
      </svg>
    </span>
    <div>
      <h1>EOS · Portal Clientes</h1>
      <div class="sub">Todo el holding, al frente</div>
      <div class="meta" id="hdr-cliente">Cargando...</div>
    </div>
  </div>
  <a href="/portal/logout" class="logout">Cerrar sesión</a>
</header>
<div class="wrap">
  <div class="tabs">
    <button class="tab active" data-tab="solicitar" onclick="setTab('solicitar')">📦 Solicitar</button>
    <button class="tab" data-tab="mis" onclick="setTab('mis')">📋 Mis pedidos</button>
    <button class="tab" data-tab="pqr" onclick="setTab('pqr')">💬 PQR</button>
    <button class="tab" data-tab="mis-pqr" onclick="setTab('mis-pqr')">📜 Mis PQR</button>
    <button class="tab" data-tab="comm" onclick="setTab('comm')">✨ Comunicación</button>
  </div>

  <div id="panel-solicitar">
    <div class="card">
      <h2>Solicitar producto</h2>
      <p style="font-size:12px;color:#64748b;margin-bottom:8px">Elegí producto, cantidad y fecha estimada · te confirmamos por correo.</p>
      <label>Producto</label>
      <select id="sol-producto">
        <option value="">— Cargando productos —</option>
      </select>
      <label>Cantidad (unidades)</label>
      <input id="sol-cant" type="number" min="1" step="1" placeholder="Ej. 500 frascos">
      <input type="hidden" id="sol-ml" value="0">
      <label>Fecha estimada de entrega</label>
      <input id="sol-fecha" type="date">
      <div id="sol-fecha-aviso" style="display:none;margin-top:6px;padding:8px 10px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:4px;font-size:12px;color:#92400e"></div>
      <label>Urgencia</label>
      <select id="sol-urgencia">
        <option value="media" selected>🟡 Media · planificación normal</option>
        <option value="baja">🟢 Baja · sin apuro</option>
        <option value="alta">🔴 Alta · necesitamos prioridad</option>
      </select>
      <label>Notas (opcional)</label>
      <textarea id="sol-notas" rows="3" placeholder="Detalles, color, arte, etc."></textarea>
      <label>🔁 Repetir este pedido (opcional)</label>
      <select id="sol-repetir">
        <option value="0">No repetir (pedido único)</option>
        <option value="15">Cada 15 días</option>
        <option value="30">Cada mes (30 días)</option>
        <option value="60">Cada 2 meses</option>
        <option value="90">Cada 3 meses</option>
      </select>
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

  <div id="panel-comm" style="display:none">
    <div class="card">
      <h2>✨ Comunicación con nosotros</h2>
      <p style="color:#94a3b8;font-size:13px;margin-bottom:14px">Pedí un producto nuevo, una reunión con gerencia o mandanos una consulta · te respondemos.</p>
      <label>Tipo</label>
      <select id="comm-tipo" onchange="commTipoChange()">
        <option value="nuevo_producto">🆕 Solicitar producto nuevo</option>
        <option value="reunion">📅 Reunión con gerencia</option>
        <option value="consulta">💬 Consulta general</option>
      </select>
      <label id="comm-prod-lbl">¿Qué producto querés que desarrollemos?</label>
      <input id="comm-prod" placeholder="Ej. Serum de niacinamida 30ml">
      <label id="comm-fecha-lbl" style="display:none">Fecha deseada (opcional)</label>
      <input id="comm-fecha" type="date" style="display:none">
      <label>Mensaje / detalle</label>
      <textarea id="comm-msg" rows="4" placeholder="Contanos lo que necesitás…"></textarea>
      <button class="primary" id="comm-btn" onclick="enviarComunicacion()">📨 Enviar</button>
      <div class="msg" id="comm-msg-out"></div>
    </div>
    <div class="card">
      <h2>📜 Mis solicitudes</h2>
      <div id="mis-sol-lista" class="lista"><div class="empty">Cargando...</div></div>
    </div>
  </div>

  <!-- panel cotizar removido 25-may-2026 PM · Sebastián: "no me sirve, el
       cliente debe pedir productos del catálogo sin valores" · backend RFQ
       queda inactivo sin UI · si en el futuro se reactiva, restaurar tab -->
</div>

<script>
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function setTab(t){
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active', b.dataset.tab===t));
  document.getElementById('panel-solicitar').style.display = (t==='solicitar')?'block':'none';
  document.getElementById('panel-mis').style.display = (t==='mis')?'block':'none';
  document.getElementById('panel-pqr').style.display = (t==='pqr')?'block':'none';
  document.getElementById('panel-mis-pqr').style.display = (t==='mis-pqr')?'block':'none';
  document.getElementById('panel-comm').style.display = (t==='comm')?'block':'none';
  if(t==='mis') cargarMisPedidos();
  if(t==='mis-pqr') cargarMisPqr();
  if(t==='comm') cargarMisSolicitudes();
}
// ✨ Comunicación 26-jun (Sebastián) · nuevo producto / reunión / consulta · reusa /api/portal/solicitudes.
function commTipoChange(){
  var t=document.getElementById('comm-tipo').value;
  var pl=document.getElementById('comm-prod-lbl'), pi=document.getElementById('comm-prod');
  var fl=document.getElementById('comm-fecha-lbl'), fi=document.getElementById('comm-fecha');
  if(t==='nuevo_producto'){ pl.textContent='¿Qué producto querés que desarrollemos?'; pl.style.display='block'; pi.style.display='block'; fl.style.display='none'; fi.style.display='none'; }
  else if(t==='reunion'){ pl.textContent='Tema de la reunión'; pl.style.display='block'; pi.style.display='block'; fl.style.display='block'; fi.style.display='block'; }
  else { pl.style.display='none'; pi.style.display='none'; fl.style.display='none'; fi.style.display='none'; }
}
async function enviarComunicacion(){
  var tipo=document.getElementById('comm-tipo').value;
  var prod=document.getElementById('comm-prod').value.trim();
  var fecha=document.getElementById('comm-fecha').value;
  var msg=document.getElementById('comm-msg').value.trim();
  var out=document.getElementById('comm-msg-out'), btn=document.getElementById('comm-btn');
  if(tipo==='nuevo_producto' && !prod){ out.className='msg err'; out.textContent='Decinos qué producto querés.'; return; }
  if(!msg){ out.className='msg err'; out.textContent='Escribí un mensaje con el detalle.'; return; }
  btn.disabled=true; btn.textContent='Enviando...';
  try{
    var r=await fetch('/api/portal/solicitudes',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tipo:tipo,producto_nombre:prod,mensaje:msg,fecha_requerida:fecha})});
    var d=await r.json();
    if(!r.ok){ out.className='msg err'; out.textContent=d.error||'Error'; return; }
    out.className='msg ok'; out.textContent=d.mensaje||'Enviado · te respondemos pronto.';
    document.getElementById('comm-prod').value=''; document.getElementById('comm-msg').value=''; document.getElementById('comm-fecha').value='';
    cargarMisSolicitudes();
  }catch(e){ out.className='msg err'; out.textContent='Error de red'; }
  finally{ btn.disabled=false; btn.textContent='📨 Enviar'; }
}
async function cargarMisSolicitudes(){
  var box=document.getElementById('mis-sol-lista'); if(!box) return;
  try{
    var d=await (await fetch('/api/portal/mis-solicitudes',{credentials:'same-origin'})).json();
    var items=d.solicitudes||d.items||[];
    if(!items.length){ box.innerHTML='<div class="empty">Sin solicitudes todavía.</div>'; return; }
    var EM={nuevo_producto:'🆕',reunion:'📅',consulta:'💬',cotizacion:'💰',muestras:'🧪',ficha_tecnica:'📄'};
    var LB={nuevo_producto:'Nuevo producto',reunion:'Reunión con gerencia',consulta:'Consulta',cotizacion:'Cotización',muestras:'Muestras',ficha_tecnica:'Ficha técnica'};
    box.innerHTML=items.map(function(s){
      var pn=(s.producto_nombre&&s.producto_nombre!=='—')?(' · '+esc(s.producto_nombre)):'';
      var resp=s.respuesta_notas?('<div style="font-size:12px;color:#16a34a;margin-top:6px;border-left:3px solid #6ee7b7;padding-left:8px">💬 '+esc(s.respuesta_notas)+'</div>'):'';
      return '<div class="pedido"><div class="pedido-prod">'+(EM[s.tipo]||'•')+' '+esc(LB[s.tipo]||s.tipo)+pn+'</div>'+(s.mensaje?'<div style="font-size:12px;color:#94a3b8;margin-top:4px">'+esc(s.mensaje)+'</div>':'')+'<span class="chip area" style="margin-top:4px;display:inline-block">'+esc(s.estado||'nueva')+'</span>'+resp+'</div>';
    }).join('');
  }catch(e){ box.innerHTML='<div class="empty">Error</div>'; }
}

// Funciones enviarCotizacion / aceptarCotizacion / actualizarBadge /
// cargarMisCotizaciones removidas 25-may-2026 PM · tab Cotizar eliminado.
// Backend RFQ (/api/portal/solicitudes y siblings) queda inactivo · si
// alguna vez se reactiva, restaurar este bloque desde git history.

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
      (d.productos||[]).map(p=>'<option value="'+esc(p.nombre)+'">'+esc(p.mostrar||p.nombre)+'</option>').join('');
  } catch(e){
    document.getElementById('hdr-cliente').textContent = 'Error: ' + e.message;
  }
}

// Sebastián 25-may-2026 PM · alerta visual cuando cliente elige fecha
// < 30 días · "le sale pop up de que debe solicitar con un mes". El
// aviso se muestra inline al cambiar el input + valida al enviar.
function _diasHastaFecha(fechaIso){
  if(!fechaIso) return null;
  var hoy = new Date(); hoy.setHours(0,0,0,0);
  var f = new Date(fechaIso + 'T12:00:00');
  return Math.round((f - hoy) / 86400000);
}
function _actualizarAvisoFecha(){
  var box = document.getElementById('sol-fecha-aviso');
  if(!box) return;
  var fecha = document.getElementById('sol-fecha').value;
  var dias = _diasHastaFecha(fecha);
  if(dias === null || dias >= 30){ box.style.display = 'none'; return; }
  if(dias < 0){
    box.style.background = '#fee2e2';
    box.style.borderLeftColor = '#dc2626';
    box.style.color = '#991b1b';
    box.innerHTML = '⛔ La fecha está en el pasado · elegí una futura';
  } else {
    box.style.background = '#fef3c7';
    box.style.borderLeftColor = '#f59e0b';
    box.style.color = '#92400e';
    box.innerHTML = '⚠ Tu fecha es en ' + dias + ' día' + (dias===1?'':'s')
      + ' · pedimos solicitar con <b>mínimo 1 mes</b> de anticipación · '
      + 'al enviar te confirmaremos si podemos cumplir o sugerimos otra fecha.';
  }
  box.style.display = 'block';
}
document.addEventListener('DOMContentLoaded', function(){
  var f = document.getElementById('sol-fecha');
  if(f) f.addEventListener('change', _actualizarAvisoFecha);
});

async function enviarPedido(){
  var btn = document.getElementById('btn-enviar');
  var msg = document.getElementById('sol-msg');
  msg.style.display = 'none';
  var producto = document.getElementById('sol-producto').value;
  var cant = parseInt(document.getElementById('sol-cant').value);
  var ml = parseFloat(document.getElementById('sol-ml').value || '30');
  var fecha = document.getElementById('sol-fecha').value;
  var urgEl = document.getElementById('sol-urgencia');
  var urgencia = urgEl ? urgEl.value : 'media';
  var notas = document.getElementById('sol-notas').value.trim();
  if(!producto || !cant || cant<=0){
    msg.className = 'msg err';
    msg.textContent = 'Falta producto o cantidad';
    msg.style.display = 'block';
    return;
  }
  // Validación blanda · fecha < 30 días pide confirmación · alta urgencia
  // pasa directo (cliente sabe que es apurado). Sin fecha también pasa
  // (queda como "sin fecha estimada" · admin la define).
  var dias = _diasHastaFecha(fecha);
  if(dias !== null && dias < 0){
    msg.className = 'msg err';
    msg.textContent = 'La fecha está en el pasado · elegí una futura';
    msg.style.display = 'block';
    return;
  }
  if(dias !== null && dias < 30 && urgencia !== 'alta'){
    if(!confirm('⚠ Pediste para dentro de ' + dias + ' días.\n\n'
                + 'Lo ideal es solicitar con mínimo 1 mes de anticipación '
                + 'porque la producción tiene lead time.\n\n'
                + '¿Continuar de todos modos? Si es URGENTE, mejor cerrá '
                + 'esto, cambiá urgencia a "🔴 Alta" y reenviá.')){
      return;
    }
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
        urgencia: urgencia,
        notas: notas,
        repetir_cada_dias: (parseInt((document.getElementById('sol-repetir')||{}).value||'0',10)||0),
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
    document.getElementById('sol-fecha-aviso').style.display = 'none';
    if(urgEl) urgEl.value = 'media';
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
      // Sebastián 25-may-2026 PM · chip urgencia (alta/media/baja).
      var urgIco = {alta:'🔴', media:'🟡', baja:'🟢'}[p.urgencia || 'media'] || '🟡';
      var urgTxt = {alta:'Alta', media:'Media', baja:'Baja'}[p.urgencia || 'media'] || 'Media';
      var urgChip = '<span style="display:inline-block;margin-left:6px;padding:2px 7px;border-radius:10px;background:#f1f5f9;font-size:10px;color:#475569">' + urgIco + ' ' + urgTxt + '</span>';
      return '<div class="pedido '+esc(p.estado)+'">'
        + '<div class="pedido-prod">'+esc(p.producto_nombre)+'</div>'
        + '<div class="pedido-meta">'+p.cantidad_uds+' uds × '+p.ml_unidad+' ml · '+(p.kg_equivalente||0)+' kg' + (p.fecha_estimada?(' · entrega ~'+esc(p.fecha_estimada)):'')+'</div>'
        + '<span class="chip '+estChipCls+'" style="margin-top:4px;display:inline-block">'+esc(estLbl)+'</span>'
        + urgChip
        + (p.notas?'<div style="font-size:11px;color:#64748b;margin-top:6px">📝 '+esc(p.notas)+'</div>':'')
        + (p.estado === 'pendiente' ? '<div style="margin-top:8px"><button onclick="editarPedidoPortal('+p.id+')" style="background:#fff;border:1px solid #6d28d9;color:#6d28d9;border-radius:6px;padding:4px 12px;font-size:12px;cursor:pointer;font-weight:600">✏️ Editar</button></div>' : '')
        + tlHtml
        + '</div>';
    }).join('');
  } catch(e){
    box.innerHTML = '<div class="empty">Error: '+esc(e.message)+'</div>';
  }
}

// B2B mejora 4/4 (Sebastián 26-jun) · el cliente edita su pedido mientras esté pendiente.
async function editarPedidoPortal(pid){
  var cant = prompt('Nueva cantidad de unidades (vacío = no cambiar):', '');
  if (cant === null) return;
  var fecha = prompt('Nueva fecha de entrega deseada YYYY-MM-DD (vacío = no cambiar):', '');
  if (fecha === null) return;
  var body = {};
  if (cant && cant.trim()) { var n = parseInt(cant, 10); if (n > 0) body.cantidad_uds = n; }
  if (fecha && fecha.trim()) body.fecha_estimada = fecha.trim();
  if (!Object.keys(body).length) { return; }
  try{
    var r = await fetch('/api/portal/pedidos/' + pid, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      credentials: 'same-origin', body: JSON.stringify(body),
    });
    var d = await r.json();
    if (!r.ok) { alert(d.error || 'No se pudo editar'); return; }
    cargarMisPedidos();
  } catch(e){ alert('Error al editar el pedido'); }
}

cargarSesionYProductos();
</script>
<footer class="app-footer">
  <div><strong>EOS v1.0</strong> &middot; Edición Espagiria</div>
  <div style="margin-top:4px;">Desarrollado por <strong>HHA Group</strong></div>
  <div style="margin-top:6px;color:#334155;">&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>
</body></html>
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
    # Catálogo B2B (26-jun) · el cliente ve el nombre GENÉRICO (niacinamida, limpiador BHA...) si está
    # cargado; si no, cae al comercial. El `nombre` (valor del pedido) SIEMPRE es el real (para producir).
    try:
        rows = conn.execute(
            """SELECT producto_nombre, COALESCE(MAX(nombre_generico),'')
               FROM formula_headers
               WHERE COALESCE(activo, 1) = 1
                 AND producto_nombre IS NOT NULL AND TRIM(producto_nombre) != ''
               GROUP BY producto_nombre
               ORDER BY producto_nombre ASC""",
        ).fetchall()
        productos = [{'nombre': r[0], 'mostrar': ((r[1] or '').strip() or r[0])} for r in rows if r[0]]
    except Exception:
        rows = conn.execute(
            "SELECT DISTINCT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1 "
            "AND producto_nombre IS NOT NULL AND TRIM(producto_nombre) != '' ORDER BY producto_nombre ASC"
        ).fetchall()
        productos = [{'nombre': r[0], 'mostrar': r[0]} for r in rows if r[0]]
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
        ml = float(body.get('ml_unidad') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'ml_unidad inválida'}), 400
    fecha = (body.get('fecha_estimada') or '').strip() or None
    notas = (body.get('notas') or '').strip()[:500]
    # FEATURE B2B multi-envase 24-may-2026 · cliente puede solicitar
    # envase específico (e.g. Fernando 500ml propio vs 250ml Animus).
    envase_codigo = (body.get('envase_codigo') or '').strip().upper()
    envase_notas = (body.get('envase_notas') or '').strip()[:200]
    # Sebastián 25-may-2026 PM · urgencia del cliente (alta/media/baja).
    # Mig 182 agrega columna · default 'media' si no viene. Validamos
    # whitelist para evitar valores arbitrarios.
    urgencia = (body.get('urgencia') or 'media').strip().lower()
    if urgencia not in ('alta', 'media', 'baja'):
        urgencia = 'media'

    if not producto:
        return jsonify({'error': 'producto_nombre requerido'}), 400
    if cantidad <= 0:
        return jsonify({'error': 'cantidad_uds debe ser > 0'}), 400
    # SEC-FIX · 22-may-2026 · límites superiores (Bug #7 audit Portal)
    # · Antes: cantidad=2e9 + ml=1e6 → kg_b2b=2e15 polluía plan canonical
    # · Ahora: límites razonables · cliente debe contactar comercial para >50k uds
    if cantidad > 50_000:
        return jsonify({'error': 'cantidad máxima 50.000 uds · contactar comercial para volúmenes mayores'}), 400
    if ml > 5_000:
        return jsonify({'error': 'ml_unidad máximo 5.000 · contactar comercial'}), 400

    conn = get_db()
    cur = conn.cursor()
    # Validar que el producto exista Y esté ACTIVO (el catálogo del portal filtra
    # activo=1 · FIX 10-jun audit: sin este filtro un POST aceptaba fórmulas
    # descontinuadas (activo=0) que entraban al plan como Fijo eos_b2b).
    prod_row = cur.execute(
        "SELECT producto_nombre FROM formula_headers "
        "WHERE producto_nombre = ? AND COALESCE(activo,1) = 1",
        (producto,),
    ).fetchone()
    if not prod_row:
        return jsonify({'error': f"producto '{producto}' no disponible"}), 404
    # ml POR UNIDAD ya no lo pide el cliente (Sebastián 26-jun · "ellos piden 500 frascos y ya") · se deriva
    # del producto: presentación default de producto_presentaciones · fallback 30 ml.
    if ml <= 0:
        try:
            _pr = cur.execute(
                "SELECT COALESCE(volumen_ml,0) FROM producto_presentaciones "
                "WHERE producto_nombre=? AND COALESCE(activo,1)=1 "
                "ORDER BY es_default DESC, volumen_ml LIMIT 1", (producto,)).fetchone()
            ml = float(_pr[0]) if (_pr and _pr[0]) else 30.0
        except Exception:
            ml = 30.0
        if ml <= 0:
            ml = 30.0

    # Validar envase si fue solicitado.
    if envase_codigo:
        env_row = cur.execute(
            "SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo)) = ?",
            (envase_codigo,),
        ).fetchone()
        if not env_row:
            return jsonify({'error': f"envase '{envase_codigo}' no disponible"}), 404
        # FEATURE B2B 24-may-2026 · whitelist envase↔cliente (mig 173).
        # Default permisivo si no hay whitelist explícita para el cliente.
        try:
            tiene_wl = cur.execute(
                """SELECT COUNT(*) FROM clientes_b2b_envases
                   WHERE cliente_id = ? AND activo = 1""",
                (cid,),
            ).fetchone()
            if tiene_wl and int(tiene_wl[0] or 0) > 0:
                permitido = cur.execute(
                    """SELECT 1 FROM clientes_b2b_envases
                       WHERE cliente_id = ? AND UPPER(TRIM(envase_codigo)) = ?
                         AND activo = 1""",
                    (cid, envase_codigo),
                ).fetchone()
                if not permitido:
                    return jsonify({'error': f"envase '{envase_codigo}' no autorizado para tu cuenta",
                                    'codigo': 'ENVASE_NO_PERMITIDO'}), 403
        except Exception:
            pass
    try:
        cur.execute(
            """INSERT INTO pedidos_b2b
                 (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                  ml_unidad, fecha_estimada, notas, creado_por,
                  envase_codigo, envase_notas, urgencia)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, cnom, producto, cantidad, ml, fecha,
             notas + (' [via portal]' if notas else 'via portal'),
             f'portal:{email}', envase_codigo, envase_notas, urgencia),
        )
    except Exception as _e1:
        # Fallback SOLO si falta una columna (mig 172/182 no aplicada) · FIX 1-jun-2026
        # (audit): re-lanzar cualquier otro error (constraint, disco) para no perder
        # urgencia/envase en silencio. Patrón igual a convertir-a-pedido.
        if 'column' not in str(_e1).lower():
            raise
        try:
            cur.execute(
                """INSERT INTO pedidos_b2b
                     (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                      ml_unidad, fecha_estimada, notas, creado_por,
                      envase_codigo, envase_notas)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, cnom, producto, cantidad, ml, fecha,
                 notas + (' [via portal]' if notas else 'via portal'),
                 f'portal:{email}', envase_codigo, envase_notas),
            )
        except Exception as _e2:
            if 'column' not in str(_e2).lower():
                raise
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
                       'cantidad_uds': cantidad, 'ml': ml, 'fecha': fecha,
                       'urgencia': urgencia})
    conn.commit()

    kg_b2b = round(cantidad * ml / 1000.0, 2)
    # CONFIRMACIÓN 26-jun (Sebastián) · el pedido del portal YA NO entra solo al plan. Queda 'pendiente'
    # hasta que el equipo (Catalina) lo CONFIRME en el backoffice (revisa/ajusta cantidad+fecha y lo ubica
    # en producción). Así un cliente no modifica el plan en silencio. La integración la hace /confirmar.
    integracion = {'estado': 'pendiente_confirmacion',
                   'detalle': 'Tu pedido quedó registrado y espera confirmación del equipo.'}
    # MEJORA 3/4 (recurrentes · 26-jun) · si el cliente pidió repetir cada N días, registrar el recurrente ·
    # un cron (job_b2b_recurrentes) crea los próximos pedidos (pendiente) cuando vencen.
    recurrente = None
    try:
        _rb = request.get_json(silent=True) or {}
        _frec = int(_rb.get('repetir_cada_dias') or 0)
    except (TypeError, ValueError):
        _frec = 0
    if _frec >= 7:
        try:
            from datetime import datetime as _dtr, timedelta as _tdr
            _base = (fecha or (_dtr.utcnow() - _tdr(hours=5)).strftime('%Y-%m-%d'))[:10]
            try:
                _prox = (_dtr.strptime(_base, '%Y-%m-%d') + _tdr(days=_frec)).strftime('%Y-%m-%d')
            except Exception:
                _prox = ((_dtr.utcnow() - _tdr(hours=5)) + _tdr(days=_frec)).strftime('%Y-%m-%d')
            cur.execute(
                "INSERT INTO pedidos_b2b_recurrentes (cliente_id, cliente_nombre, producto_nombre, "
                "cantidad_uds, ml_unidad, envase_codigo, frecuencia_dias, proximo_at, activo, creado_por, "
                "creado_at_utc) VALUES (?,?,?,?,?,?,?,?,1,?, datetime('now','utc'))",
                (cid, cnom, producto, cantidad, ml, envase_codigo or '', _frec, _prox, f'portal:{email}'))
            conn.commit()
            recurrente = {'frecuencia_dias': _frec, 'proximo_at': _prox}
        except Exception as _er:
            log.warning('crear recurrente B2B fallo: %s', _er)

    # Notif in-app a Sebastián+Catalina (no email · CLAUDE.md memoria)
    try:
        from blueprints.notif import push_notif as _push_notif
        for dest in ('sebastian', 'catalina'):
            _push_notif(
                destinatario=dest,
                tipo='portal_pedido_nuevo',
                titulo=f'📦 Pedido B2B para CONFIRMAR · {cnom}',
                body=f'{producto} · {cantidad} uds × {ml} ml · {kg_b2b} kg' +
                      (f' para {fecha}' if fecha else '') +
                      ' · revisá y confirmá para que entre al plan',
                link='/dashboard#programacion',
                remitente=f'portal:{email}',
                importante=True,
            )
    except Exception:
        pass

    return jsonify({
        'ok': True, 'id': pid, 'kg_b2b': kg_b2b,
        'integracion_plan': integracion,
        'recurrente': recurrente,
    }), 201


# ────────────────────────────────────────────────────────────────────
# API: mis pedidos
# ────────────────────────────────────────────────────────────────────

@bp.route('/api/portal/pedidos/<int:pid>', methods=['PATCH'])
def portal_editar_pedido(pid):
    """B2B mejora 4/4 (Sebastián 26-jun) · el cliente edita SU pedido mientras esté 'pendiente'
    (cantidad/fecha/notas). Confirmado/en producción ya no se edita (solo cancelar)."""
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT cliente_id, estado FROM pedidos_b2b WHERE id=?", (pid,)).fetchone()
    if not row or str(row[0]) != str(cid):
        return jsonify({'error': 'pedido no encontrado'}), 404
    if row[1] != 'pendiente':
        return jsonify({'error': 'solo podés editar un pedido pendiente · ya está en proceso',
                        'codigo': 'NO_EDITABLE'}), 409
    fields, params = [], []
    if 'cantidad_uds' in body:
        try:
            cu = int(body['cantidad_uds'])
        except (ValueError, TypeError):
            return jsonify({'error': 'cantidad inválida'}), 400
        if cu <= 0 or cu > 50000:
            return jsonify({'error': 'cantidad fuera de rango (1 a 50.000)'}), 400
        fields.append('cantidad_uds=?')
        params.append(cu)
    if 'fecha_estimada' in body:
        fields.append('fecha_estimada=?')
        params.append((body['fecha_estimada'] or '').strip() or None)
    if 'notas' in body:
        fields.append('notas=?')
        params.append((body['notas'] or '').strip()[:500])
    if not fields:
        return jsonify({'error': 'sin cambios'}), 400
    params.append(pid)
    cur.execute(f"UPDATE pedidos_b2b SET {', '.join(fields)} WHERE id=? AND estado='pendiente'", params)
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'el pedido cambió de estado · recargá', 'codigo': 'ESTADO_CAMBIO'}), 409
    audit_log(cur, usuario=f'portal:{email}', accion='PORTAL_EDITAR_PEDIDO',
              tabla='pedidos_b2b', registro_id=pid, despues=body)
    conn.commit()
    return jsonify({'ok': True, 'id': pid})


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


@bp.route('/api/admin/portal/catalogo', methods=['GET', 'POST'])
def admin_portal_catalogo():
    """Catálogo B2B · nombres GENÉRICOS que ve el cliente en el portal (en vez del comercial de Ánimus).
    Sebastián 26-jun · interino mientras se cargan los productos propios de los clientes. Admin."""
    u, err = _require_admin_backoffice()
    if err:
        return err
    conn = get_db()
    c = conn.cursor()
    if request.method == 'GET':
        try:
            rows = c.execute(
                "SELECT producto_nombre, COALESCE(MAX(nombre_generico),'') FROM formula_headers "
                "WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL AND TRIM(producto_nombre)!='' "
                "GROUP BY producto_nombre ORDER BY producto_nombre").fetchall()
        except Exception:
            rows = []
        return jsonify({'items': [{'producto': r[0], 'generico': r[1]} for r in rows]})
    body = request.get_json(silent=True) or {}
    prod = (body.get('producto') or '').strip()
    gen = (body.get('nombre_generico') or '').strip()[:120]
    if not prod:
        return jsonify({'error': 'producto requerido'}), 400
    c.execute("UPDATE formula_headers SET nombre_generico=? WHERE producto_nombre=?", (gen, prod))
    audit_log(c, usuario=u, accion='PORTAL_SET_NOMBRE_GENERICO', tabla='formula_headers',
              registro_id=0, despues={'producto': prod, 'generico': gen})
    conn.commit()
    return jsonify({'ok': True, 'producto': prod, 'generico': gen})


# ────────────────────────────────────────────────────────────────────
# API: mis pedidos
# ────────────────────────────────────────────────────────────────────

def _construir_timeline_pedido(conn, pedido_id, pedido_creado_at, pedido_estado, lote_pre=None):
    """PERF-FIX · 21-may-2026 · acepta lote_pre opcional para skip query.
    Si lote_pre se pasa (tupla con 14 cols · ver bulk load), usa directo."""
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

    # 2) Buscar lote vinculado · si bulk pre-load lo tiene · skip query
    # PERF-FIX · 21-may-2026 · evita N+1 cuando portal_mis_pedidos llama bulk
    if lote_pre:
        # lote_pre viene de bulk: (id, observaciones, estado, ini, fin, area,
        #                          fecha, d_ini, d_fin, e_ini, e_fin, n_ini, n_fin, a_ini, a_fin)
        # Reconstruir tupla en formato esperado (sin observaciones)
        lote = (lote_pre[0],) + tuple(lote_pre[2:])
    else:
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

    # 8) Enviado · pedidos_b2b.estado='despachado' (mejora 2/4 · 26-jun: muestra fecha + guía/transportadora)
    estado_pedido = (pedido_estado or '').lower()
    if estado_pedido == 'despachado':
        _dat, _guia, _transp = '', '', ''
        try:
            _dr = conn.execute(
                "SELECT COALESCE(despachado_at,''), COALESCE(despacho_guia,''), "
                "COALESCE(despacho_transportadora,'') FROM pedidos_b2b WHERE id=?", (pedido_id,)).fetchone()
            if _dr:
                _dat, _guia, _transp = _dr[0], _dr[1], _dr[2]
        except Exception:
            pass
        _extra = ' · '.join([x for x in (_transp, ('guía ' + _guia) if _guia else '') if x])
        timeline.append({
            'key': 'enviado', 'label': 'Enviado', 'icon': '🚚',
            'estado': 'completado', 'fecha': (_dat or '')[:10] or None,
            'detalle': ('Despachado · ' + _extra) if _extra else 'Despachado al cliente',
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

    Sprint D Portal · 20-may-2026: cada pedido trae `timeline` con 8 steps.
    PERF-FIX · 21-may-2026 · Antes 1-3 queries por pedido (N+1, hasta 300
    queries en LIMIT 100). Ahora · pre-carga bulk de lotes + EBRs.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, _ = auth
    conn = get_db()
    # Sebastián 25-may-2026 PM · agregar urgencia al SELECT. Fallback si
    # mig 182 no aplicada (column not exists) · COALESCE no funciona porque
    # SQLite parsea el SELECT antes · usar try/except con SELECT alternativo.
    try:
        rows = conn.execute(
            """SELECT id, producto_nombre, cantidad_uds, ml_unidad, fecha_estimada,
                      estado, notas, creado_at_utc, COALESCE(urgencia,'media')
               FROM pedidos_b2b
               WHERE cliente_id = ?
               ORDER BY creado_at_utc DESC, id DESC
               LIMIT 100""",
            (cid,),
        ).fetchall()
        _has_urgencia = True
    except Exception:
        rows = conn.execute(
            """SELECT id, producto_nombre, cantidad_uds, ml_unidad, fecha_estimada,
                      estado, notas, creado_at_utc
               FROM pedidos_b2b
               WHERE cliente_id = ?
               ORDER BY creado_at_utc DESC, id DESC
               LIMIT 100""",
            (cid,),
        ).fetchall()
        _has_urgencia = False
    # PERF-FIX · pre-cargar lotes vinculados via bulk OR LIKE
    pedido_ids = [r[0] for r in rows]
    lotes_pre = {}
    if pedido_ids:
        try:
            # 1 query con N condiciones LIKE en vez de N queries
            like_parts = []
            params_b = []
            for pid in pedido_ids:
                like_parts.append('(observaciones LIKE ? OR observaciones LIKE ?)')
                params_b.extend([f'%(pedido #{pid})%', f'%· #{pid} ·%'])
            lote_rows = conn.execute(
                f"""SELECT id, observaciones,
                          COALESCE(estado,''), COALESCE(inicio_real_at,''),
                          COALESCE(fin_real_at,''), COALESCE(area_id,0),
                          COALESCE(fecha_programada,''),
                          COALESCE(etapa_disp_inicio_at,''), COALESCE(etapa_disp_fin_at,''),
                          COALESCE(etapa_elab_inicio_at,''), COALESCE(etapa_elab_fin_at,''),
                          COALESCE(etapa_env_inicio_at,''), COALESCE(etapa_env_fin_at,''),
                          COALESCE(etapa_acond_inicio_at,''), COALESCE(etapa_acond_fin_at,'')
                   FROM produccion_programada
                   WHERE ({' OR '.join(like_parts)})
                     AND LOWER(COALESCE(estado,'')) != 'cancelado'
                   ORDER BY id DESC""",
                params_b,
            ).fetchall()
            # Asignar el primero match por pedido_id
            for lr in lote_rows:
                obs_l = lr[1] or ''
                for pid in pedido_ids:
                    if (f'(pedido #{pid})' in obs_l or f'· #{pid} ·' in obs_l) and pid not in lotes_pre:
                        lotes_pre[pid] = lr
                        break
        except Exception as _e:
            log.warning('bulk lotes pre-load fallo: %s', _e)
    out = []
    for r in rows:
        uds = int(r[2] or 0); ml = float(r[3] or 0)
        pid = r[0]
        estado = r[5] or 'pendiente'
        creado = r[7] or ''
        try:
            tl = _construir_timeline_pedido(conn, pid, creado, estado, lote_pre=lotes_pre.get(pid))
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
        urg = (r[8] if _has_urgencia and len(r) > 8 else 'media') or 'media'
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
            'urgencia': urg,
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
    # SLA-FIX · 21-may-2026 · Ley 1755/2015 CO · plazos PQR
    # peticion=15 días hábiles · queja/reclamo=15 días · sugerencia=30 días
    from datetime import datetime as _dtpqr, timedelta as _tdpqr
    SLA_DIAS = {'peticion': 15, 'queja': 15, 'reclamo': 15, 'sugerencia': 30}
    sla_dias = SLA_DIAS.get(tipo, 15)
    sla_vence = (_dtpqr.utcnow() + _tdpqr(days=sla_dias)).isoformat()
    # Defensive · agregar columna si no existe (idempotente)
    try:
        c.execute("ALTER TABLE portal_pqr ADD COLUMN sla_vence_at_utc TEXT")
    except Exception:
        pass
    c.execute(
        """INSERT INTO portal_pqr
             (cliente_id, cliente_nombre, email_cliente, tipo, titulo,
              descripcion, sla_vence_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cid, cnom, email, tipo, titulo, descripcion, sla_vence),
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


# ════════════════════════════════════════════════════════════════════════
# Atajo demo · Sebastián 25-may-2026 PM · "dame credenciales a mi de prueba
# quiero ver que si funciona" · pagina admin one-click que crea (o
# resetea) la credencial demo y muestra password en plain · solo accesible
# desde sesión admin.
# ════════════════════════════════════════════════════════════════════════

@bp.route('/admin/clientes-b2b', methods=['GET'])
def admin_clientes_b2b_pagina():
    """Panel admin para crear/gestionar clientes del portal B2B (Sebastián 26-jun).
    Reusa /api/admin/portal/credenciales (crear/listar/resetear-clave/activar)."""
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/clientes-b2b')
    if session.get('compras_user', '') not in ADMIN_USERS:
        return ("<html><body style='font-family:system-ui;padding:48px'><h2>Solo admin</h2></body></html>"), 403
    return Response(_CLIENTES_B2B_HTML, mimetype='text/html')


_CLIENTES_B2B_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clientes B2B · EOS</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:#f5f3ff;color:#1e1b4b;padding:24px}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:24px;color:#5b21b6;margin-bottom:4px}.sub{color:#64748b;font-size:13px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e9d5ff;border-radius:14px;padding:18px;margin-bottom:18px;box-shadow:0 2px 10px rgba(109,40,217,.05)}
.card h2{font-size:15px;color:#6d28d9;margin-bottom:12px}
label{display:block;font-size:12px;font-weight:600;color:#475569;margin:8px 0 3px}
input{width:100%;padding:9px 11px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
.row{display:flex;gap:10px;flex-wrap:wrap}.row>div{flex:1;min-width:180px}
button{border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer}
.primary{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff}
.ghost{background:#fff;border:1px solid #c4b5fd;color:#6d28d9}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px;color:#5b21b6;border-bottom:2px solid #e9d5ff}td{padding:8px;border-bottom:1px solid #f1f5f9}
.acceso{background:#ecfdf5;border:1px solid #6ee7b7;border-radius:10px;padding:14px;margin-top:12px;font-size:13px;display:none}
.acceso pre{background:#fff;border:1px solid #d1fae5;border-radius:8px;padding:10px;margin:8px 0;white-space:pre-wrap;font-family:monospace;font-size:12px}
.chip{padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700}.on{background:#dcfce7;color:#15803d}.off{background:#fee2e2;color:#991b1b}
</style></head><body><div class="wrap">
<h1>👥 Clientes B2B</h1>
<div class="sub">Creá clientes del portal, copiales el acceso y gestioná sus claves. Entran por <b>/portal/login</b>.</div>
<div class="card"><h2>➕ Crear cliente</h2>
<div class="row"><div><label>Nombre del cliente</label><input id="c-nom" placeholder="Ej. Kelly Cosméticos" oninput="autoId()"></div>
<div><label>Email (con esto entra)</label><input id="c-email" type="email" placeholder="contacto@kelly.com"></div></div>
<div class="row"><div><label>ID del cliente (automático · editable)</label><input id="c-id" placeholder="kelly-cosmeticos"></div>
<div><label>Clave</label><div style="display:flex;gap:6px"><input id="c-pass" placeholder="(generar)"><button class="ghost" type="button" onclick="genClave()">🎲</button></div></div></div>
<button class="primary" style="margin-top:12px" onclick="crearCliente()">Crear cliente</button>
<div class="acceso" id="acceso-box"><b>✓ Cliente creado · copiale este acceso:</b><pre id="acceso-txt"></pre><button class="ghost" onclick="copiarAcceso()">📋 Copiar acceso</button></div>
<div id="c-msg" style="margin-top:8px;font-size:13px"></div></div>
<div class="card"><h2>📋 Clientes (<span id="n-cli">0</span>)</h2>
<div style="overflow-x:auto"><table><thead><tr><th>Cliente</th><th>Email</th><th>Estado</th><th>Último ingreso</th><th></th></tr></thead>
<tbody id="cli-tbody"><tr><td colspan="5" style="color:#94a3b8;padding:14px">Cargando&hellip;</td></tr></tbody></table></div></div>
<div class="card"><h2>🛒 Catálogo B2B · nombres genéricos</h2>
<div class="sub" style="margin-bottom:10px">El cliente ve el <b>nombre genérico</b> (ej. "Niacinamida", "Limpiador BHA") en vez del comercial de Ánimus. Vacío = ve el comercial. <i>Interino mientras cargás los productos propios.</i></div>
<div style="overflow-x:auto"><table><thead><tr><th>Producto (real · Ánimus)</th><th>Nombre genérico que ve el cliente</th><th></th></tr></thead>
<tbody id="cat-tbody"><tr><td colspan="3" style="color:#94a3b8;padding:14px">Cargando&hellip;</td></tr></tbody></table></div></div>
</div><script>
var BASE=location.origin, _CSRF='';
fetch('/api/csrf-token',{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(t){_CSRF=t.csrf_token||'';}).catch(function(){});
function _hdr(){ return {'Content-Type':'application/json','X-CSRF-Token':_CSRF}; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function autoId(){ var n=document.getElementById('c-nom').value||''; document.getElementById('c-id').value=n.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40); }
function genClave(){ var ch='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789',s=''; for(var i=0;i<10;i++)s+=ch[Math.floor(Math.random()*ch.length)]; document.getElementById('c-pass').value=s; return s; }
var _acc='';
async function crearCliente(){
  var nom=document.getElementById('c-nom').value.trim(),email=document.getElementById('c-email').value.trim(),id=document.getElementById('c-id').value.trim(),pass=document.getElementById('c-pass').value.trim(),msg=document.getElementById('c-msg');
  if(!pass) pass=genClave();
  if(!nom||!email||!id){ msg.style.color='#dc2626'; msg.textContent='Completá nombre, email e ID.'; return; }
  try{
    var r=await fetch('/api/admin/portal/credenciales',{method:'POST',headers:_hdr(),credentials:'same-origin',body:JSON.stringify({cliente_id:id,cliente_nombre:nom,email:email,password:pass})});
    var d=await r.json();
    if(!r.ok){ msg.style.color='#dc2626'; msg.textContent=d.error||'Error'; return; }
    msg.textContent='';
    _acc='Portal HHA \\u00b7 acceso\\n\\nLink: '+BASE+'/portal/login\\nEmail: '+email+'\\nClave: '+pass;
    document.getElementById('acceso-txt').textContent=_acc; document.getElementById('acceso-box').style.display='block';
    document.getElementById('c-nom').value='';document.getElementById('c-email').value='';document.getElementById('c-id').value='';document.getElementById('c-pass').value='';
    cargarClientes();
  }catch(e){ msg.style.color='#dc2626'; msg.textContent='Error de red'; }
}
function copiarAcceso(){ navigator.clipboard.writeText(_acc).then(function(){ alert('Acceso copiado \\u00b7 peg\\u00e1selo al cliente'); }); }
async function resetClave(id,email){
  var s=genClave();
  if(!confirm('Resetear la clave de '+email+'? La nueva ser\\u00e1: '+s)) return;
  var r=await fetch('/api/admin/portal/credenciales/'+id,{method:'PATCH',headers:_hdr(),credentials:'same-origin',body:JSON.stringify({password:s})});
  var d=await r.json(); if(!r.ok){ alert(d.error||'Error'); return; }
  var txt='Portal HHA \\u00b7 nuevo acceso\\n\\nLink: '+BASE+'/portal/login\\nEmail: '+email+'\\nClave: '+s;
  navigator.clipboard.writeText(txt).then(function(){ alert('Clave reseteada y acceso copiado \\u00b7 peg\\u00e1selo al cliente'); });
}
async function toggleActivo(id,nuevo){ var r=await fetch('/api/admin/portal/credenciales/'+id,{method:'PATCH',headers:_hdr(),credentials:'same-origin',body:JSON.stringify({activo:nuevo})}); if(r.ok)cargarClientes(); else alert('Error'); }
async function cargarClientes(){
  var tb=document.getElementById('cli-tbody');
  try{
    var d=await (await fetch('/api/admin/portal/credenciales',{credentials:'same-origin'})).json();
    var items=d.items||[]; document.getElementById('n-cli').textContent=items.length;
    if(!items.length){ tb.innerHTML='<tr><td colspan="5" style="color:#94a3b8;padding:14px">Sin clientes todav\\u00eda \\u00b7 cre\\u00e1 el primero arriba.</td></tr>'; return; }
    tb.innerHTML=items.map(function(c){
      var est=c.activo?'<span class="chip on">activo</span>':'<span class="chip off">inactivo</span>';
      var ult=c.ultimo_login_at_utc?esc(String(c.ultimo_login_at_utc).slice(0,16).replace('T',' ')):'<span style="color:#cbd5e1">nunca</span>';
      var tog=c.activo?('<button class="ghost" onclick="toggleActivo('+c.id+',false)">🚫 Desactivar</button>'):('<button class="ghost" onclick="toggleActivo('+c.id+',true)">✓ Activar</button>');
      return '<tr><td><b>'+esc(c.cliente_nombre)+'</b><br><span style="font-size:10px;color:#94a3b8">'+esc(c.cliente_id)+'</span></td><td>'+esc(c.email)+'</td><td>'+est+'</td><td style="font-size:12px">'+ult+'</td><td style="white-space:nowrap"><button class="ghost" onclick="resetClave('+c.id+',&#39;'+esc(c.email)+'&#39;)">🔄 Clave</button> '+tog+'</td></tr>';
    }).join('');
  }catch(e){ tb.innerHTML='<tr><td colspan="5" style="color:#dc2626">Error cargando</td></tr>'; }
}
var _CAT=[];
async function cargarCatalogo(){
  var tb=document.getElementById('cat-tbody');
  try{
    var d=await (await fetch('/api/admin/portal/catalogo',{credentials:'same-origin'})).json();
    _CAT=d.items||[];
    if(!_CAT.length){ tb.innerHTML='<tr><td colspan="3" style="color:#94a3b8;padding:14px">Sin productos.</td></tr>'; return; }
    tb.innerHTML=_CAT.map(function(it,i){
      return '<tr><td style="font-size:12px">'+esc(it.producto)+'</td><td><input id="gen-'+i+'" value="'+esc(it.generico)+'" placeholder="(gen\\u00e9rico)" style="width:100%"></td><td><button class="ghost" onclick="setGenerico('+i+')">Guardar</button></td></tr>';
    }).join('');
  }catch(e){ tb.innerHTML='<tr><td colspan="3" style="color:#dc2626">Error</td></tr>'; }
}
async function setGenerico(i){
  var prod=(_CAT[i]||{}).producto, gen=(document.getElementById('gen-'+i)||{}).value||'';
  if(!prod) return;
  var r=await fetch('/api/admin/portal/catalogo',{method:'POST',headers:_hdr(),credentials:'same-origin',body:JSON.stringify({producto:prod,nombre_generico:gen})});
  if(r.ok){ alert('Guardado \\u00b7 el cliente ahora ve "'+(gen||prod)+'"'); cargarCatalogo(); } else alert('Error');
}
genClave(); cargarClientes(); cargarCatalogo();
</script></body></html>"""


_PORTAL_DEMO_EMAIL = 'demo-cliente@hha.com'
_PORTAL_DEMO_CLIENTE_ID = 'DEMO_CLI_SEBASTIAN'
_PORTAL_DEMO_NOMBRE = 'Demo Sebastián'


@bp.route('/admin/portal-demo', methods=['GET'])
def admin_portal_demo_pagina():
    """Página one-click que crea (o resetea) la credencial demo y muestra
    el password para que Sebastián entre al portal cliente y vea el flujo
    con sus ojos. Genera password random cada vez que apretás el botón.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/portal-demo')
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_USERS)):
        return ("<html><body style='font-family:system-ui;padding:48px'>"
                 "<h2>Solo admin/compras</h2></body></html>"), 403
    return Response(_PORTAL_DEMO_HTML, mimetype='text/html')


@bp.route('/api/portal-demo/regenerar', methods=['POST'])
def admin_portal_demo_regenerar():
    """Crea la credencial demo si no existe · si existe, resetea password
    a uno random nuevo. Devuelve email + password en plain (solo este
    endpoint los muestra · luego solo queda hash en BD).

    Sebastián 25-may-2026 PM · path SIN prefix /api/admin/ para evitar
    auth.py:427 que exige X-CSRF-Token obligatorio en /api/admin/. Acá
    el endpoint sigue siendo admin-only via gate manual abajo + la capa
    Origin/Referer check (auth.py:383) sigue protegiendo igual.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_USERS)):
        return jsonify({'error': 'Solo admin/compras'}), 403
    # Password random fácil de copiar · 12 chars alfanuméricos
    pw_plain = secrets.token_urlsafe(9)[:12].replace('-', 'A').replace('_', 'B')
    pw_hash = generate_password_hash(pw_plain)
    conn = get_db(); c = conn.cursor()
    existe = c.execute(
        "SELECT id FROM portal_clientes_credenciales WHERE LOWER(email) = ?",
        (_PORTAL_DEMO_EMAIL,)).fetchone()
    if existe:
        c.execute(
            """UPDATE portal_clientes_credenciales
                  SET password_hash = ?, activo = 1,
                      cliente_nombre = ?
                WHERE id = ?""",
            (pw_hash, _PORTAL_DEMO_NOMBRE, existe[0]))
        accion = 'PORTAL_DEMO_RESET_PASSWORD'
        cred_id = existe[0]
        creada = False
    else:
        c.execute(
            """INSERT INTO portal_clientes_credenciales
                 (cliente_id, cliente_nombre, email, password_hash, activo, creado_por)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (_PORTAL_DEMO_CLIENTE_ID, _PORTAL_DEMO_NOMBRE,
             _PORTAL_DEMO_EMAIL, pw_hash, user))
        cred_id = c.lastrowid
        accion = 'PORTAL_DEMO_CREAR_CRED'
        creada = True
    try:
        audit_log(c, usuario=user, accion=accion,
                  tabla='portal_clientes_credenciales', registro_id=cred_id,
                  despues={'email': _PORTAL_DEMO_EMAIL, 'creada': creada})
    except Exception:
        pass
    conn.commit()
    return jsonify({
        'ok': True, 'creada': creada, 'cred_id': cred_id,
        'email': _PORTAL_DEMO_EMAIL, 'password': pw_plain,
        'portal_url': '/portal/login',
    })


_PORTAL_DEMO_HTML = """<!DOCTYPE html>
<html lang="es" translate="no"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Demo Portal Clientes</title>
<meta name="theme-color" content="#6d28d9">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
       background:radial-gradient(ellipse at top,#1e1b4b 0%,#0f172a 50%,#0a0a0f 100%);
       min-height:100vh;padding:48px 16px;color:#e2e8f0}
  .card{max-width:580px;margin:0 auto;background:rgba(30,41,59,0.7);
        backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
        border:1px solid rgba(167,139,250,0.2);border-radius:18px;
        box-shadow:0 20px 60px rgba(109,40,217,0.15);padding:32px}
  .brand{display:flex;align-items:center;gap:14px;margin-bottom:18px}
  .brand-mark{display:inline-flex;align-items:center;justify-content:center;
              width:48px;height:48px;border-radius:12px;background:rgba(109,40,217,.2);
              box-shadow:0 6px 18px rgba(109,40,217,.3)}
  h1{margin:0;font-size:22px;font-weight:800;letter-spacing:-0.4px;
     background:linear-gradient(135deg,#c4b5fd,#a78bfa);
     -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  .sub{color:#94a3b8;font-size:13px;margin-bottom:22px;margin-top:4px}
  .step{margin-bottom:18px}
  .step-num{display:inline-block;background:linear-gradient(135deg,#a78bfa,#6d28d9);
            color:#fff;width:26px;height:26px;border-radius:13px;text-align:center;
            font-weight:800;font-size:13px;line-height:26px;margin-right:8px;
            box-shadow:0 4px 12px rgba(109,40,217,.35)}
  .step-titulo{font-weight:700;font-size:14px;display:inline-block;color:#e2e8f0}
  .step-body{margin-top:6px;margin-left:34px;font-size:13px;color:#94a3b8}
  .btn{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border:none;
       padding:13px 22px;border-radius:10px;font-size:14px;font-weight:700;
       cursor:pointer;margin:8px 0;letter-spacing:.3px;transition:.15s;font-family:inherit}
  .btn:hover{transform:translateY(-1px);box-shadow:0 10px 24px rgba(109,40,217,.45)}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-link{display:inline-block;background:rgba(167,139,250,.18);color:#c4b5fd;
            padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;
            font-size:13px;margin-top:6px;border:1px solid rgba(167,139,250,.3);
            transition:.15s}
  .btn-link:hover{background:rgba(167,139,250,.28);color:#fff}
  .cred-box{background:rgba(15,23,42,0.7);border:2px solid rgba(167,139,250,.35);
            border-radius:12px;padding:18px;margin:14px 0;
            box-shadow:inset 0 2px 8px rgba(0,0,0,.2)}
  .cred-label{font-size:10px;color:#a78bfa;text-transform:uppercase;font-weight:700;
              letter-spacing:1px;margin-bottom:4px}
  .cred-value{font-family:'SF Mono',Consolas,monospace;font-size:16px;font-weight:700;
              color:#c4b5fd;background:rgba(167,139,250,.08);padding:8px 12px;
              border-radius:7px;border:1px solid rgba(167,139,250,.2);display:inline-block;
              user-select:all;cursor:pointer;transition:.15s}
  .cred-value:hover{background:rgba(167,139,250,.16);color:#e2e8f0}
  .copy-hint{font-size:11px;color:#64748b;margin-left:8px}
  .nota{font-size:12px;color:#fcd34d;background:rgba(202,138,4,.12);
        border-left:3px solid #f59e0b;padding:10px 14px;border-radius:7px;margin-top:14px}
  .ok-msg{color:#86efac;font-weight:700;margin-top:8px;
          background:rgba(22,163,74,.12);padding:8px 12px;border-radius:7px;
          border-left:3px solid #16a34a}
  .err-msg{color:#fca5a5;font-weight:700;margin-top:8px;
           background:rgba(220,38,38,.12);padding:8px 12px;border-radius:7px;
           border-left:3px solid #dc2626}
  .app-footer{text-align:center;font-size:10px;color:#475569;letter-spacing:.5px;
              margin-top:24px;line-height:1.6}
  .app-footer strong{color:#94a3b8}
</style></head><body>
<div class="card">
  <div class="brand">
    <span class="brand-mark" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="36" height="36" fill="none" stroke="#a78bfa" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#a78bfa"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>
      </svg>
    </span>
    <div>
      <h1>Demo Portal Clientes</h1>
      <div class="sub">Generá una credencial y entrá como cliente B2B.</div>
    </div>
  </div>

  <div class="step">
    <span class="step-num">1</span><span class="step-titulo">Generar credencial</span>
    <div class="step-body">
      Click acá · te genera o resetea la credencial demo.
      <br><button class="btn" id="btn-gen" onclick="generar()">🔑 Generar credencial demo</button>
    </div>
  </div>

  <div id="cred-display" style="display:none">
    <div class="cred-box">
      <div class="cred-label">Email</div>
      <div class="cred-value" id="cred-email" onclick="copiar(this)"></div>
      <div style="margin-top:14px"></div>
      <div class="cred-label">Contraseña (mostrada UNA vez · copiala)</div>
      <div class="cred-value" id="cred-pass" onclick="copiar(this)"></div>
      <span class="copy-hint">↑ click para copiar</span>
    </div>

    <div class="step">
      <span class="step-num">2</span><span class="step-titulo">Abrir el portal en ventana incógnita</span>
      <div class="step-body">
        Para no mezclar tu sesión admin con la del cliente, abrí incógnita
        (Ctrl+Shift+N) y pegá la URL.
        <br><a href="/portal/login" target="_blank" class="btn-link">🔗 Abrir /portal/login en pestaña nueva</a>
      </div>
    </div>

    <div class="step">
      <span class="step-num">3</span><span class="step-titulo">Pegá email + contraseña</span>
      <div class="step-body">
        Usá los datos de arriba · entrás como cliente B2B y ves:
        Solicitar · Mis pedidos · PQR · Mis PQR.
      </div>
    </div>

    <div class="nota">
      ⚠ Esta credencial es de prueba · el cliente real "Demo Sebastián"
      aparecerá en /admin/clientes-b2b. Si volvés a apretar el botón se
      RESETEA el password (la anterior deja de funcionar).
    </div>
  </div>

  <div id="msg"></div>
</div>

<script>
// CSRF token · auth.py:365 requiere X-CSRF-Token en POSTs sensibles.
window._csrfTok = '';
fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d && d.csrf_token) window._csrfTok = d.csrf_token; })
  .catch(() => {});

async function generar(){
  var btn = document.getElementById('btn-gen');
  var msg = document.getElementById('msg');
  msg.innerHTML = '';
  // Si el token aún no llegó (race · poco probable pero defensive), espero 300ms
  if(!window._csrfTok){
    try{
      var rt = await fetch('/api/csrf-token', {credentials:'same-origin'});
      var dt = await rt.json();
      if(dt && dt.csrf_token) window._csrfTok = dt.csrf_token;
    }catch(_){}
  }
  btn.disabled = true; btn.textContent = 'Generando...';
  try{
    var r = await fetch('/api/portal-demo/regenerar', {
      method:'POST',
      headers:{'Content-Type':'application/json',
                'X-CSRF-Token': window._csrfTok || ''},
      credentials:'same-origin',
      body:'{}'
    });
    var d = await r.json();
    if(!r.ok){
      msg.innerHTML = '<div class="err-msg">Error: ' + (d.error || r.status) + '</div>';
      btn.disabled = false; btn.textContent = '🔑 Reintentar';
      return;
    }
    document.getElementById('cred-email').textContent = d.email;
    document.getElementById('cred-pass').textContent = d.password;
    document.getElementById('cred-display').style.display = 'block';
    msg.innerHTML = '<div class="ok-msg">✓ ' + (d.creada ? 'Credencial creada' : 'Password reseteado') + '</div>';
    btn.disabled = false; btn.textContent = '🔄 Regenerar password';
  }catch(e){
    msg.innerHTML = '<div class="err-msg">Error de red: ' + e.message + '</div>';
    btn.disabled = false; btn.textContent = '🔑 Reintentar';
  }
}
function copiar(el){
  var t = el.textContent;
  if(navigator.clipboard){
    navigator.clipboard.writeText(t).then(function(){
      el.style.background = 'rgba(134,239,172,0.25)';
      setTimeout(function(){ el.style.background = 'rgba(167,139,250,.08)'; }, 600);
    });
  } else {
    // Fallback antiguo
    var range = document.createRange(); range.selectNode(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    try { document.execCommand('copy'); } catch(_){}
  }
}
</script>
<footer class="app-footer">
  <div><strong>EOS v1.0</strong> &middot; Edición Espagiria</div>
  <div style="margin-top:4px;">Desarrollado por <strong>HHA Group</strong></div>
</footer>
</body></html>
"""


# ════════════════════════════════════════════════════════════════════════
# Portal · Solicitudes de cotización / muestras / ficha técnica (RFQ)
# Sebastián 25-may-2026 · tarea pendiente #4 "Módulo portal solicitud B2B"
# Complementa el flujo de pedidos · cliente nuevo o existente pide
# cotización ANTES de comprometer · admin responde con precio + lead + MOQ
# · cliente convierte a pedido o lo deja en histórico.
# ════════════════════════════════════════════════════════════════════════

_PORTAL_SOL_TIPOS = ('cotizacion', 'muestras', 'ficha_tecnica',
                     'nuevo_producto', 'reunion', 'consulta')  # +comunicación 26-jun
# Tipos que NO necesitan producto (el cliente escribe en el mensaje)
_SOL_TIPOS_SIN_PRODUCTO = ('reunion', 'consulta')
_PORTAL_SOL_ESTADOS = ('nueva', 'en_revision', 'respondida',
                        'convertida', 'cerrada', 'rechazada')


@bp.route('/api/portal/solicitudes', methods=['POST'])
def portal_crear_solicitud():
    """Cliente externo crea una solicitud de cotización/muestras/ficha.

    Body: {
      tipo: 'cotizacion'|'muestras'|'ficha_tecnica' (default cotizacion),
      producto_nombre: str (requerido),
      cantidad_estimada: int (opcional · 0 si solo info),
      unidad: 'unidades'|'kg'|'litros' (default unidades),
      envase_preferencia: str (opcional · e.g. '500ml gotero'),
      fecha_requerida: 'YYYY-MM-DD' (opcional),
      mensaje: str (opcional · notas)
    }

    Sale en estado 'nueva' · Catalina la ve en /compras y responde.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    body = request.get_json(silent=True) or {}
    tipo = (body.get('tipo') or 'cotizacion').strip().lower()
    if tipo not in _PORTAL_SOL_TIPOS:
        return jsonify({'error': f'tipo inválido · usar {_PORTAL_SOL_TIPOS}'}), 400
    producto = (body.get('producto_nombre') or '').strip()
    if not producto:
        if tipo in _SOL_TIPOS_SIN_PRODUCTO:
            producto = '—'  # reunión/consulta · el detalle va en el mensaje
        else:
            return jsonify({'error': 'producto_nombre requerido'}), 400
    try:
        cantidad = int(body.get('cantidad_estimada') or 0)
    except (TypeError, ValueError):
        cantidad = 0
    if cantidad < 0 or cantidad > 1_000_000_000:
        return jsonify({'error': 'cantidad_estimada fuera de rango'}), 400
    unidad = (body.get('unidad') or 'unidades').strip().lower()[:30]
    envase_pref = (body.get('envase_preferencia') or '').strip()[:120]
    fecha_req = (body.get('fecha_requerida') or '').strip() or None
    mensaje = (body.get('mensaje') or '').strip()[:1000]
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        """INSERT INTO portal_solicitudes
           (cliente_id, cliente_nombre, cliente_email, tipo, producto_nombre,
            cantidad_estimada, unidad, envase_preferencia, fecha_requerida,
            mensaje, estado, creada_at, actualizada_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nueva',
                   datetime('now', '-5 hours'), datetime('now', '-5 hours'))""",
        (cid, cnom, email, tipo, producto, cantidad, unidad, envase_pref,
         fecha_req, mensaje),
    )
    sol_id = cur.lastrowid
    try:
        from audit_helpers import audit_log
        audit_log(cur, usuario=f'portal:{cnom}'[:80],
                  accion='CREAR_PORTAL_SOLICITUD',
                  tabla='portal_solicitudes', registro_id=str(sol_id),
                  despues={'tipo': tipo, 'producto': producto[:120],
                            'cantidad': cantidad, 'cliente_id': cid})
    except Exception:
        pass
    conn.commit()
    # Comunicación 26-jun · avisar al equipo por campana (Sebastián + Catalina)
    try:
        from blueprints.notif import push_notif as _pn
        _lbl = {'nuevo_producto': '🆕 Nuevo producto', 'reunion': '📅 Reunión con gerencia',
                'consulta': '💬 Consulta', 'cotizacion': '💰 Cotización', 'muestras': '🧪 Muestras',
                'ficha_tecnica': '📄 Ficha técnica'}.get(tipo, tipo)
        _body = ((producto + ' · ') if (producto and producto != '—') else '') + (mensaje[:140] or 'sin detalle')
        for _d in ('sebastian', 'catalina'):
            _pn(destinatario=_d, tipo='portal_solicitud_nueva',
                titulo=f'{_lbl} · {cnom}', body=_body,
                link='/admin/portal-rfq', remitente=f'portal:{email}', importante=True)
    except Exception:
        pass
    return jsonify({
        'ok': True, 'id': sol_id, 'tipo': tipo, 'estado': 'nueva',
        'mensaje': f"Solicitud #{sol_id} recibida · te respondemos en 24-48h hábiles",
    }), 201


@bp.route('/api/portal/mis-solicitudes', methods=['GET'])
def portal_mis_solicitudes():
    """Cliente externo ve sus solicitudes (todos los tipos).

    Query: ?estado=nueva|respondida|... (opcional · default todas)
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, _cnom, _email = auth
    estado_f = (request.args.get('estado') or '').strip().lower()
    conn = get_db(); cur = conn.cursor()
    sql = ("SELECT id, tipo, producto_nombre, cantidad_estimada, unidad, "
           "       envase_preferencia, fecha_requerida, mensaje, estado, "
           "       COALESCE(respuesta_precio_cop, 0), "
           "       COALESCE(respuesta_lead_time_dias, 0), "
           "       COALESCE(respuesta_moq, 0), "
           "       COALESCE(respuesta_validez_dias, 15), "
           "       COALESCE(respuesta_notas, ''), "
           "       COALESCE(respondido_por, ''), respondido_at, "
           "       creada_at, actualizada_at, "
           "       COALESCE(convertida_pedido_id, 0) "
           "FROM portal_solicitudes WHERE cliente_id = ?")
    params = [cid]
    if estado_f and estado_f in _PORTAL_SOL_ESTADOS:
        sql += " AND estado = ?"
        params.append(estado_f)
    sql += " ORDER BY creada_at DESC LIMIT 100"
    try:
        rows = cur.execute(sql, params).fetchall()
    except Exception:
        rows = []
    cols = ['id', 'tipo', 'producto_nombre', 'cantidad_estimada', 'unidad',
            'envase_preferencia', 'fecha_requerida', 'mensaje', 'estado',
            'respuesta_precio_cop', 'respuesta_lead_time_dias',
            'respuesta_moq', 'respuesta_validez_dias', 'respuesta_notas',
            'respondido_por', 'respondido_at', 'creada_at', 'actualizada_at',
            'convertida_pedido_id']
    items = [dict(zip(cols, r)) for r in rows]
    return jsonify({'items': items, 'total': len(items)})


@bp.route('/api/admin/portal/solicitudes', methods=['GET'])
def admin_portal_solicitudes_list():
    """Catalina/admin ve TODAS las solicitudes del portal (cross-cliente).

    Query: ?estado=nueva|... ?tipo=cotizacion|...
    """
    usuario = session.get('compras_user', '')
    if usuario not in COMPRAS_USERS and usuario not in ADMIN_USERS:
        return jsonify({'error': 'Solo Compras/Admin'}), 403
    estado_f = (request.args.get('estado') or '').strip().lower()
    tipo_f = (request.args.get('tipo') or '').strip().lower()
    conn = get_db(); cur = conn.cursor()
    sql = ("SELECT id, cliente_id, cliente_nombre, cliente_email, tipo, "
           "       producto_nombre, cantidad_estimada, unidad, "
           "       envase_preferencia, fecha_requerida, mensaje, estado, "
           "       COALESCE(respuesta_precio_cop, 0), "
           "       COALESCE(respuesta_lead_time_dias, 0), "
           "       COALESCE(respuesta_moq, 0), "
           "       COALESCE(respuesta_validez_dias, 15), "
           "       COALESCE(respuesta_notas, ''), "
           "       COALESCE(respondido_por, ''), respondido_at, "
           "       creada_at, actualizada_at, "
           "       COALESCE(convertida_pedido_id, 0) "
           "FROM portal_solicitudes WHERE 1=1")
    params = []
    if estado_f and estado_f in _PORTAL_SOL_ESTADOS:
        sql += " AND estado = ?"
        params.append(estado_f)
    if tipo_f and tipo_f in _PORTAL_SOL_TIPOS:
        sql += " AND tipo = ?"
        params.append(tipo_f)
    sql += " ORDER BY (estado='nueva') DESC, creada_at DESC LIMIT 300"
    try:
        rows = cur.execute(sql, params).fetchall()
    except Exception:
        rows = []
    cols = ['id', 'cliente_id', 'cliente_nombre', 'cliente_email', 'tipo',
            'producto_nombre', 'cantidad_estimada', 'unidad',
            'envase_preferencia', 'fecha_requerida', 'mensaje', 'estado',
            'respuesta_precio_cop', 'respuesta_lead_time_dias',
            'respuesta_moq', 'respuesta_validez_dias', 'respuesta_notas',
            'respondido_por', 'respondido_at', 'creada_at', 'actualizada_at',
            'convertida_pedido_id']
    items = [dict(zip(cols, r)) for r in rows]
    return jsonify({'items': items, 'total': len(items)})


@bp.route('/api/admin/portal/solicitudes/<int:sol_id>', methods=['PATCH'])
def admin_portal_solicitud_responder(sol_id):
    """Admin responde una solicitud · setea estado='respondida' + datos
    cotización (precio + lead + MOQ + validez + notas). Cliente la ve
    en /portal → Mis solicitudes.

    Body: {estado?, respuesta_precio_cop?, respuesta_lead_time_dias?,
           respuesta_moq?, respuesta_validez_dias?, respuesta_notas?}
    """
    usuario = session.get('compras_user', '')
    if usuario not in COMPRAS_USERS and usuario not in ADMIN_USERS:
        return jsonify({'error': 'Solo Compras/Admin'}), 403
    body = request.get_json(silent=True) or {}
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT estado, cliente_nombre FROM portal_solicitudes WHERE id = ?",
        (sol_id,),
    ).fetchone()
    if not row:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    estado_prev, _cli_nom = row
    sets = []
    params = []
    nuevo_estado = (body.get('estado') or '').strip().lower()
    if nuevo_estado:
        if nuevo_estado not in _PORTAL_SOL_ESTADOS:
            return jsonify({'error': f'estado inválido · {_PORTAL_SOL_ESTADOS}'}), 400
        sets.append('estado = ?'); params.append(nuevo_estado)
    # Campos respuesta · si vienen explícitos los acepta
    for campo, key, parser in [
        ('respuesta_precio_cop', 'respuesta_precio_cop', float),
        ('respuesta_lead_time_dias', 'respuesta_lead_time_dias', int),
        ('respuesta_moq', 'respuesta_moq', int),
        ('respuesta_validez_dias', 'respuesta_validez_dias', int),
    ]:
        if key in body and body[key] is not None:
            try:
                v = parser(body[key])
                if v < 0:
                    continue
                sets.append(f'{campo} = ?')
                params.append(v)
            except (TypeError, ValueError):
                pass
    if 'respuesta_notas' in body:
        notas = (body.get('respuesta_notas') or '').strip()[:1000]
        sets.append('respuesta_notas = ?'); params.append(notas)
    # Si admin responde por primera vez · sello respondido_por/at
    if (nuevo_estado == 'respondida' or
            any(k.startswith('respuesta_') for k in body if body.get(k) is not None)):
        sets.append('respondido_por = ?'); params.append(usuario)
        sets.append("respondido_at = datetime('now', '-5 hours')")
        # Auto-mover a 'respondida' si admin completó datos sin pasar estado
        if not nuevo_estado:
            sets.append("estado = 'respondida'")
    sets.append("actualizada_at = datetime('now', '-5 hours')")
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(sol_id)
    cur.execute(
        f"UPDATE portal_solicitudes SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    try:
        from audit_helpers import audit_log
        audit_log(cur, usuario=usuario, accion='RESPONDER_PORTAL_SOLICITUD',
                  tabla='portal_solicitudes', registro_id=str(sol_id),
                  antes={'estado_prev': estado_prev},
                  despues={'cambios': {k: v for k, v in body.items() if v is not None}})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'id': sol_id})


@bp.route('/api/portal/solicitudes/<int:sol_id>/convertir-a-pedido', methods=['POST'])
def portal_convertir_solicitud_a_pedido(sol_id):
    """Cliente acepta cotización · marca convertida + crea pedido inicial.

    Sebastián 25-may-2026 · Fase 3 paso 2 · cierre del loop RFQ → pedido.
    Solo solicitudes en estado='respondida' y tipo='cotizacion' se pueden
    convertir. Crea un pedido en estado 'borrador' con cantidad y precio
    cotizado · cliente lo confirma en /portal Mis pedidos.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT id, cliente_id, tipo, estado, producto_nombre, cantidad_estimada, "
        "       unidad, envase_preferencia, "
        "       COALESCE(respuesta_precio_cop, 0), "
        "       COALESCE(respuesta_lead_time_dias, 0), "
        "       COALESCE(respuesta_moq, 0), "
        "       COALESCE(convertida_pedido_id, 0) "
        "FROM portal_solicitudes WHERE id = ? AND cliente_id = ?",
        (sol_id, cid)).fetchone()
    if not row:
        return jsonify({'error': 'Solicitud no encontrada o no es tuya'}), 404
    (_id, _cid, tipo, estado, producto, cant_est, unidad, envase_pref,
     precio, lead, moq, ya_convertida) = row
    if ya_convertida:
        return jsonify({'error': f'Ya convertida al pedido #{ya_convertida}'}), 409
    if tipo != 'cotizacion':
        return jsonify({'error': 'Solo cotizaciones se pueden convertir · muestras/ficha técnica no'}), 400
    if estado != 'respondida':
        return jsonify({'error': f'Estado actual {estado} · debe estar respondida'}), 400
    if precio <= 0:
        return jsonify({'error': 'Cotización sin precio · pedile al equipo que complete'}), 400
    # MOQ check
    if moq > 0 and cant_est < moq:
        return jsonify({'error': f'Cantidad solicitada ({cant_est}) menor al MOQ ({moq})'}), 400
    # Convertir a pedidos_b2b · misma tabla que el flujo normal del portal.
    # Parsear ml del envase_preferencia ("500ml gotero" → 500.0) · default 50ml.
    import re as _re
    ml_unidad = 50.0
    if envase_pref:
        m = _re.search(r'(\d+(?:\.\d+)?)\s*ml', envase_pref.lower())
        if m:
            try:
                ml_unidad = float(m.group(1))
                if ml_unidad <= 0 or ml_unidad > 5000:
                    ml_unidad = 50.0
            except Exception:
                ml_unidad = 50.0
    notas_pedido = (f'Convertido desde cotización #{sol_id} · precio cotizado '
                    f'${int(precio):,} COP/ud · MOQ {moq} · lead {lead}d')[:500]
    try:
        cur.execute(
            """INSERT INTO pedidos_b2b
               (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                ml_unidad, fecha_estimada, notas, creado_por,
                envase_codigo, envase_notas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, cnom, producto, cant_est, ml_unidad, None,
             notas_pedido, f'portal:rfq:{email}', '', envase_pref[:200]))
        pedido_id = cur.lastrowid
    except Exception as e:
        emsg = str(e).lower()
        if 'no such column' in emsg or 'has no column' in emsg:
            # Schema sin envase_codigo/envase_notas · fallback (mig 172 vieja)
            try: conn.rollback()
            except Exception: pass
            cur.execute(
                """INSERT INTO pedidos_b2b
                   (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
                    ml_unidad, fecha_estimada, notas, creado_por)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, cnom, producto, cant_est, ml_unidad, None,
                 notas_pedido, f'portal:rfq:{email}'))
            pedido_id = cur.lastrowid
        else:
            raise
    # Marcar solicitud como convertida · CAS (FIX 10-jun audit · race 3 workers):
    # condicionado a que SIGA sin convertir y respondida · si otro request ganó la
    # carrera (doble clic), rowcount=0 → rollback (deshace el pedido recién insertado)
    # y 409, evitando 2 pedidos B2B del mismo RFQ.
    cur.execute(
        "UPDATE portal_solicitudes SET convertida_pedido_id = ?, "
        "       estado = 'convertida', "
        "       actualizada_at = datetime('now', '-5 hours') "
        "WHERE id = ? AND COALESCE(convertida_pedido_id,0) = 0 AND estado = 'respondida'",
        (pedido_id, sol_id))
    if cur.rowcount != 1:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': 'Esta solicitud ya fue convertida (doble envío)'}), 409
    try:
        from audit_helpers import audit_log
        audit_log(cur, usuario=f'portal:{cnom}'[:80],
                  accion='CONVERTIR_SOLICITUD_A_PEDIDO',
                  tabla='portal_solicitudes', registro_id=str(sol_id),
                  despues={'pedido_id': pedido_id, 'precio_cop': precio,
                            'cantidad': cant_est, 'producto': producto[:120]})
    except Exception:
        pass
    conn.commit()
    return jsonify({
        'ok': True, 'pedido_id': pedido_id, 'solicitud_id': sol_id,
        'mensaje': f'Pedido #{pedido_id} creado en borrador · confirmalo en Mis pedidos',
    }), 201


@bp.route('/api/portal/badge', methods=['GET'])
def portal_badge_cliente():
    """Contador para badge in-app del cliente · cotizaciones respondidas no vistas.

    Sebastián 25-may-2026 · Fase 3 paso 3 · cliente sabe sin refrescar
    cuando hay respuesta del equipo. Cuenta solicitudes en estado
    'respondida' que aún no fueron convertidas o cerradas.
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, _cnom, _email = auth
    conn = get_db(); cur = conn.cursor()
    try:
        n_cot = cur.execute(
            "SELECT COUNT(*) FROM portal_solicitudes "
            "WHERE cliente_id = ? AND estado = 'respondida'",
            (cid,)).fetchone()[0] or 0
    except Exception:
        n_cot = 0
    try:
        n_pqr = cur.execute(
            "SELECT COUNT(*) FROM portal_pqr "
            "WHERE cliente_id = ? AND estado = 'respondido'",
            (cid,)).fetchone()[0] or 0
    except Exception:
        n_pqr = 0
    return jsonify({'cotizaciones_respondidas': int(n_cot),
                     'pqr_respondidos': int(n_pqr),
                     'total': int(n_cot) + int(n_pqr)})


@bp.route('/admin/portal-rfq', methods=['GET'])
def admin_portal_rfq_pagina():
    """Página HTML admin para gestionar cotizaciones/muestras/ficha técnica.

    Sebastián 25-may-2026 · Fase 3 paso 1 · bloqueador del flujo RFQ.
    Hoy los endpoints existen pero Catalina no tiene UI · esta página
    lista cotizaciones por estado, permite responder con precio + lead +
    MOQ + validez + notas, y marcar cerradas/rechazadas.
    """
    if 'compras_user' not in session:
        return ("<html><body style='font-family:system-ui;padding:48px'>"
                 "<h2>No autorizado</h2>"
                 "<a href='/login'>Ir a login</a></body></html>"), 401
    user = session.get('compras_user', '')
    if user not in (set(ADMIN_USERS) | set(COMPRAS_USERS)):
        return ("<html><body style='font-family:system-ui;padding:48px'>"
                 "<h2>Solo Compras/Admin</h2></body></html>"), 403
    return _RFQ_ADMIN_HTML


# ── HTML página admin RFQ ────────────────────────────────────────────────────
# String constante (no f-string) · escapado JS con \\n y \\d donde aplica.
_RFQ_ADMIN_HTML = """<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cotizaciones B2B · Admin</title>
<style>
  *{box-sizing:border-box}
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:#f1f5f9;margin:0;padding:0;color:#0f172a}
  header{background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;
         padding:18px 24px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
  header h1{margin:0;font-size:20px}
  header .sub{font-size:13px;opacity:.85;margin-top:2px}
  .top-bar{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}
  .container{max-width:1400px;margin:18px auto;padding:0 18px}
  .filtros{background:#fff;padding:14px 18px;border-radius:10px;
           box-shadow:0 2px 8px rgba(0,0,0,.04);display:flex;
           gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
  .filtros label{font-size:12px;color:#475569;font-weight:600}
  .filtros select{padding:6px 10px;border:1px solid #cbd5e1;
                  border-radius:6px;font-size:13px;background:#fff}
  .filtros .stats{margin-left:auto;font-size:12px;color:#64748b}
  .stats b{color:#0f766e}
  .lista{background:#fff;border-radius:10px;
         box-shadow:0 2px 8px rgba(0,0,0,.04);overflow:hidden}
  .item{padding:14px 18px;border-bottom:1px solid #e2e8f0;
        display:grid;grid-template-columns:80px 1fr 140px 130px 110px 130px;
        gap:12px;align-items:center;cursor:pointer;transition:background .15s}
  .item:hover{background:#f0fdf4}
  .item:last-child{border-bottom:none}
  .item .id{font-family:monospace;color:#64748b;font-size:13px;font-weight:700}
  .item .producto{font-weight:600;color:#0f172a}
  .item .producto .meta{font-size:11px;color:#64748b;font-weight:400;margin-top:2px}
  .item .cliente{font-size:13px;color:#334155}
  .item .cliente .email{font-size:11px;color:#94a3b8}
  .item .tipo{font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.5px}
  .item .tipo.cotizacion{color:#0891b2}
  .item .tipo.muestras{color:#9333ea}
  .item .tipo.ficha_tecnica{color:#ea580c}
  .badge{display:inline-block;padding:3px 10px;border-radius:12px;
         font-size:11px;font-weight:700;text-transform:uppercase}
  .b-nueva{background:#fef3c7;color:#92400e}
  .b-en_revision{background:#dbeafe;color:#1e40af}
  .b-respondida{background:#d1fae5;color:#065f46}
  .b-convertida{background:#a7f3d0;color:#064e3b}
  .b-cerrada{background:#e2e8f0;color:#475569}
  .b-rechazada{background:#fee2e2;color:#991b1b}
  .fecha{font-size:11px;color:#64748b}
  .empty{padding:48px;text-align:center;color:#94a3b8}
  .empty-ic{font-size:48px;margin-bottom:8px}
  /* Modal */
  .modal-bg{position:fixed;inset:0;background:rgba(15,23,42,.55);
            display:none;align-items:flex-start;justify-content:center;
            z-index:1000;overflow-y:auto;padding:24px 14px}
  .modal-bg.open{display:flex}
  .modal{background:#fff;border-radius:14px;max-width:680px;width:100%;
         padding:24px 28px;box-shadow:0 20px 50px rgba(0,0,0,.3);margin:auto}
  .modal h2{margin:0 0 4px;color:#0f172a;font-size:18px}
  .modal .sub{font-size:12px;color:#64748b;margin-bottom:18px}
  .modal .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px}
  .modal .field{display:flex;flex-direction:column;gap:4px}
  .modal label{font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .modal input,.modal textarea,.modal select{
    padding:9px 11px;border:1px solid #cbd5e1;border-radius:7px;
    font-size:13px;font-family:inherit;color:#0f172a}
  .modal input:focus,.modal textarea:focus{outline:none;border-color:#0891b2;box-shadow:0 0 0 3px rgba(8,145,178,.15)}
  .modal textarea{resize:vertical;min-height:70px}
  .modal .full{grid-column:1/-1}
  .modal .info-box{background:#f8fafc;border-left:3px solid #0891b2;
                    padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px}
  .modal .info-box b{color:#0f172a}
  .modal .actions{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}
  .btn{padding:10px 18px;border:none;border-radius:7px;font-weight:700;font-size:13px;cursor:pointer;transition:all .15s}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-primary{background:#0891b2;color:#fff}
  .btn-primary:hover:not(:disabled){background:#0e7490}
  .btn-secondary{background:#e2e8f0;color:#475569}
  .btn-secondary:hover{background:#cbd5e1}
  .btn-danger{background:#fee2e2;color:#991b1b}
  .btn-danger:hover{background:#fecaca}
  .msg{padding:10px 14px;border-radius:7px;margin-top:14px;font-size:13px;display:none}
  .msg.ok{background:#d1fae5;color:#065f46;display:block}
  .msg.err{background:#fee2e2;color:#991b1b;display:block}
  .nav-back{color:#fff;text-decoration:none;font-size:13px;opacity:.85}
  .nav-back:hover{opacity:1}
  @media(max-width:900px){
    .item{grid-template-columns:60px 1fr 100px;gap:8px;font-size:12px}
    .item .tipo,.item .fecha,.item .cliente{display:none}
    .modal .grid{grid-template-columns:1fr}
  }
</style></head><body>

<header><div class="top-bar">
  <div>
    <h1>📨 Cotizaciones B2B (RFQ)</h1>
    <div class="sub">Cotización · Muestras · Ficha técnica · clientes del portal</div>
  </div>
  <a href="/modulos" class="nav-back">← Módulos</a>
</div></header>

<div class="container">

  <div class="filtros">
    <label>Estado:</label>
    <select id="f-estado">
      <option value="">Todas</option>
      <option value="nueva" selected>Nuevas</option>
      <option value="en_revision">En revisión</option>
      <option value="respondida">Respondidas</option>
      <option value="convertida">Convertidas</option>
      <option value="cerrada">Cerradas</option>
      <option value="rechazada">Rechazadas</option>
    </select>
    <label>Tipo:</label>
    <select id="f-tipo">
      <option value="">Todos</option>
      <option value="cotizacion">Cotización</option>
      <option value="muestras">Muestras</option>
      <option value="ficha_tecnica">Ficha técnica</option>
    </select>
    <button class="btn btn-secondary" onclick="cargar()">↻ Refrescar</button>
    <div class="stats" id="stats">— solicitudes</div>
  </div>

  <div class="lista" id="lista">
    <div class="empty">Cargando…</div>
  </div>

</div>

<!-- Modal responder -->
<div class="modal-bg" id="modal-bg">
  <div class="modal" onclick="event.stopPropagation()">
    <h2 id="m-titulo">Cotización #—</h2>
    <div class="sub" id="m-sub">Cliente · producto</div>

    <div class="info-box" id="m-info"></div>

    <div class="grid">
      <div class="field">
        <label>Precio unitario (COP)</label>
        <input type="number" id="m-precio" min="0" step="100">
      </div>
      <div class="field">
        <label>Lead time (días)</label>
        <input type="number" id="m-lead" min="0" max="365" step="1">
      </div>
      <div class="field">
        <label>MOQ (mínimo)</label>
        <input type="number" id="m-moq" min="0" step="1">
      </div>
      <div class="field">
        <label>Validez oferta (días)</label>
        <input type="number" id="m-validez" min="1" max="365" step="1" value="15">
      </div>
      <div class="field full">
        <label>Notas (opcional · términos, condiciones, descuentos)</label>
        <textarea id="m-notas" maxlength="1000" placeholder="Ej: precio incluye empaque básico · descuento 5% > 1000 unidades · pago contado"></textarea>
      </div>
    </div>

    <div class="msg" id="m-msg"></div>

    <div class="actions">
      <button class="btn btn-danger" id="b-rechazar" onclick="cambiarEstado('rechazada')">Rechazar</button>
      <button class="btn btn-secondary" id="b-cerrar" onclick="cambiarEstado('cerrada')">Cerrar sin respuesta</button>
      <button class="btn btn-secondary" onclick="cerrarModal()">Cancelar</button>
      <button class="btn btn-primary" id="b-responder" onclick="responder()">Enviar respuesta</button>
    </div>
  </div>
</div>

<script>
let _items = [];
let _solActual = null;

function fmtCop(n){
  return new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n||0);
}
function escapeHtml(s){
  if(s===null||s===undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtFecha(s){
  if(!s) return '—';
  try{ return s.substring(0,16).replace('T',' '); }catch(_){ return s; }
}
function csrfToken(){
  // Token vive en /api/csrf-token (servidor) o en window._csrfTok
  return window._csrfTok || '';
}

async function cargar(){
  const est = document.getElementById('f-estado').value;
  const tip = document.getElementById('f-tipo').value;
  const params = new URLSearchParams();
  if(est) params.set('estado', est);
  if(tip) params.set('tipo', tip);
  try{
    const r = await fetch('/api/admin/portal/solicitudes?' + params.toString());
    if(r.status === 401){ window.location.href = '/login'; return; }
    const d = await r.json();
    _items = d.items || [];
    render();
  }catch(e){
    document.getElementById('lista').innerHTML =
      '<div class="empty"><div class="empty-ic">⚠</div>Error: ' + escapeHtml(e.message) + '</div>';
  }
}

function render(){
  const lista = document.getElementById('lista');
  const stats = document.getElementById('stats');
  if(_items.length === 0){
    lista.innerHTML = '<div class="empty"><div class="empty-ic">📭</div>Sin solicitudes con esos filtros</div>';
    stats.innerHTML = '0 solicitudes';
    return;
  }
  const nuevas = _items.filter(x => x.estado === 'nueva').length;
  const resp = _items.filter(x => x.estado === 'respondida').length;
  stats.innerHTML = '<b>' + _items.length + '</b> solicitudes · ' +
                     '<b>' + nuevas + '</b> nuevas · <b>' + resp + '</b> respondidas';
  lista.innerHTML = _items.map(it => {
    const tipoTxt = {'cotizacion':'COTIZAR','muestras':'MUESTRAS','ficha_tecnica':'FICHA TÉC.'}[it.tipo] || it.tipo;
    return '<div class="item" onclick="abrirModal('+ it.id +')">'
      + '<div class="id">#' + it.id + '</div>'
      + '<div class="producto">' + escapeHtml(it.producto_nombre)
        + '<div class="meta">' + (it.cantidad_estimada||0) + ' ' + escapeHtml(it.unidad||'unidades')
        + (it.envase_preferencia ? ' · ' + escapeHtml(it.envase_preferencia) : '')
        + (it.fecha_requerida ? ' · necesita ' + escapeHtml(it.fecha_requerida) : '')
        + '</div></div>'
      + '<div class="cliente">' + escapeHtml(it.cliente_nombre||'')
        + '<div class="email">' + escapeHtml(it.cliente_email||'') + '</div></div>'
      + '<div class="tipo ' + it.tipo + '">' + tipoTxt + '</div>'
      + '<div class="fecha">' + fmtFecha(it.creada_at) + '</div>'
      + '<div><span class="badge b-' + it.estado + '">' + it.estado + '</span></div>'
      + '</div>';
  }).join('');
}

function abrirModal(id){
  const it = _items.find(x => x.id === id);
  if(!it) return;
  _solActual = it;
  document.getElementById('m-titulo').textContent =
    (it.tipo === 'cotizacion' ? 'Cotización' : it.tipo === 'muestras' ? 'Muestras' : 'Ficha técnica')
    + ' #' + it.id;
  document.getElementById('m-sub').textContent =
    (it.cliente_nombre||'') + ' · ' + (it.cliente_email||'');
  const info = document.getElementById('m-info');
  let html = '<b>Producto:</b> ' + escapeHtml(it.producto_nombre) + '<br>';
  html += '<b>Cantidad:</b> ' + (it.cantidad_estimada||0) + ' ' + escapeHtml(it.unidad||'unidades') + '<br>';
  if(it.envase_preferencia) html += '<b>Envase preferido:</b> ' + escapeHtml(it.envase_preferencia) + '<br>';
  if(it.fecha_requerida) html += '<b>Necesita para:</b> ' + escapeHtml(it.fecha_requerida) + '<br>';
  if(it.mensaje) html += '<b>Mensaje cliente:</b> ' + escapeHtml(it.mensaje);
  info.innerHTML = html;

  // Pre-cargar valores si ya tenía respuesta
  document.getElementById('m-precio').value = it.respuesta_precio_cop || '';
  document.getElementById('m-lead').value = it.respuesta_lead_time_dias || '';
  document.getElementById('m-moq').value = it.respuesta_moq || '';
  document.getElementById('m-validez').value = it.respuesta_validez_dias || 15;
  document.getElementById('m-notas').value = it.respuesta_notas || '';
  document.getElementById('m-msg').className = 'msg';
  document.getElementById('m-msg').textContent = '';

  // Si es muestras/ficha técnica, ocultar campos no aplicables
  const isCot = it.tipo === 'cotizacion';
  document.getElementById('m-precio').parentElement.style.display = isCot ? '' : 'none';
  document.getElementById('m-moq').parentElement.style.display = isCot ? '' : 'none';
  document.getElementById('m-validez').parentElement.style.display = isCot ? '' : 'none';

  // Estados terminales · solo lectura
  const terminal = ['convertida','cerrada','rechazada'].includes(it.estado);
  document.getElementById('b-responder').disabled = terminal;
  document.getElementById('b-rechazar').disabled = terminal;
  document.getElementById('b-cerrar').disabled = terminal;

  document.getElementById('modal-bg').classList.add('open');
}

function cerrarModal(){
  document.getElementById('modal-bg').classList.remove('open');
  _solActual = null;
}

async function responder(){
  if(!_solActual) return;
  const body = {};
  const precio = parseFloat(document.getElementById('m-precio').value);
  const lead = parseInt(document.getElementById('m-lead').value);
  const moq = parseInt(document.getElementById('m-moq').value);
  const validez = parseInt(document.getElementById('m-validez').value);
  const notas = document.getElementById('m-notas').value.trim();
  if(isFinite(precio) && precio >= 0) body.respuesta_precio_cop = precio;
  if(isFinite(lead) && lead >= 0) body.respuesta_lead_time_dias = lead;
  if(isFinite(moq) && moq >= 0) body.respuesta_moq = moq;
  if(isFinite(validez) && validez > 0) body.respuesta_validez_dias = validez;
  body.respuesta_notas = notas;

  // Si es cotización, exigir precio (las muestras/ficha técnica no)
  if(_solActual.tipo === 'cotizacion' && !(precio > 0)){
    mostrarMsg('Precio unitario es obligatorio para cotizaciones', false);
    return;
  }

  document.getElementById('b-responder').disabled = true;
  try{
    const r = await fetch('/api/admin/portal/solicitudes/' + _solActual.id, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json','X-CSRF-Token': csrfToken()},
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if(r.ok && d.ok){
      mostrarMsg('✓ Respuesta enviada · cliente la verá al refrescar /portal', true);
      setTimeout(() => { cerrarModal(); cargar(); }, 900);
    }else{
      mostrarMsg('Error: ' + (d.error || r.status), false);
    }
  }catch(e){
    mostrarMsg('Error de red: ' + e.message, false);
  }finally{
    document.getElementById('b-responder').disabled = false;
  }
}

async function cambiarEstado(nuevoEstado){
  if(!_solActual) return;
  const msg = nuevoEstado === 'rechazada'
    ? '¿Rechazar esta solicitud? El cliente verá el estado pero no recibe respuesta detallada.'
    : '¿Cerrar sin respuesta? Útil cuando ya se manejó por otro canal.';
  if(!confirm(msg)) return;
  document.getElementById('b-rechazar').disabled = true;
  document.getElementById('b-cerrar').disabled = true;
  try{
    const r = await fetch('/api/admin/portal/solicitudes/' + _solActual.id, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json','X-CSRF-Token': csrfToken()},
      body: JSON.stringify({estado: nuevoEstado}),
    });
    const d = await r.json();
    if(r.ok && d.ok){
      mostrarMsg('✓ Estado actualizado a ' + nuevoEstado, true);
      setTimeout(() => { cerrarModal(); cargar(); }, 700);
    }else{
      mostrarMsg('Error: ' + (d.error || r.status), false);
    }
  }catch(e){
    mostrarMsg('Error de red: ' + e.message, false);
  }finally{
    document.getElementById('b-rechazar').disabled = false;
    document.getElementById('b-cerrar').disabled = false;
  }
}

function mostrarMsg(texto, ok){
  const m = document.getElementById('m-msg');
  m.textContent = texto;
  m.className = 'msg ' + (ok ? 'ok' : 'err');
}

// Cerrar modal al click background
document.getElementById('modal-bg').addEventListener('click', function(e){
  if(e.target.id === 'modal-bg') cerrarModal();
});

// Cargar token CSRF
fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d && d.csrf_token) window._csrfTok = d.csrf_token; })
  .catch(() => {});

// Listeners filtros
document.getElementById('f-estado').addEventListener('change', cargar);
document.getElementById('f-tipo').addEventListener('change', cargar);

// Carga inicial + auto-refresh cada 60s (silencioso)
cargar();
setInterval(function(){
  if(!document.getElementById('modal-bg').classList.contains('open')) cargar();
}, 60000);
</script>
</body></html>
"""

