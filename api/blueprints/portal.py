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
<title>Espagiria · Portal de clientes</title>
<meta name="application-name" content="Espagiria · Portal">
<meta name="apple-mobile-web-app-title" content="Portal Espagiria">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="description" content="Portal de clientes de Espagiria Laboratorio">
<meta name="author" content="HHA Group">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=eos11">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=eos11">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png?v=eos11">
<script>(function(){try{var t=localStorage.getItem('cx-theme');if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches){t='dark';}if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:var(--cx-bg, #f4f4f7);color:var(--cx-text, #18181b);min-height:100vh;font-size:15px;
     display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 18px;
     -webkit-font-smoothing:antialiased}
.aura{position:fixed;inset:0;pointer-events:none;z-index:0;
      background:radial-gradient(700px 420px at 50% -10%, rgba(167,139,250,.18), transparent 70%)}
.shell{position:relative;z-index:1;width:100%;max-width:430px}
.card{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:var(--cx-r-xl, 20px);padding:38px 32px 30px;
      box-shadow:var(--cx-sh-lg, 0 12px 32px rgba(15,23,42,.08))}
.brand{text-align:center;margin-bottom:26px}
.mark{display:inline-flex;align-items:center;justify-content:center;width:66px;height:66px;border-radius:19px;
      background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));
      box-shadow:0 12px 28px rgba(109,40,217,.32);margin-bottom:16px}
.name{font-size:29px;font-weight:800;letter-spacing:-.9px;line-height:1.1}
.tag{color:var(--cx-primary-text, #6d28d9);font-size:12.5px;font-style:italic;margin-top:3px}
.sub{color:var(--cx-text-mute, #6b6b74);font-size:11px;font-weight:800;text-transform:uppercase;
     letter-spacing:1.6px;margin-top:12px}
label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;
      color:var(--cx-text-mute, #6b6b74);margin:0 0 6px}
.fg{margin-bottom:16px}
input{width:100%;padding:13px 15px;font-size:15px;font-family:inherit;
      background:var(--cx-bg-alt, #fbfbfd);color:var(--cx-text, #18181b);
      border:1px solid var(--cx-border, #e6e6ea);border-radius:var(--cx-r-md, 10px);outline:none;transition:.15s}
input:focus{border-color:var(--cx-primary-light, #a78bfa);background:var(--cx-card, #ffffff);
            box-shadow:0 0 0 3px var(--cx-primary-pale, #f5f3ff)}
.btn{width:100%;background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;
     border:none;border-radius:var(--cx-r-md, 10px);padding:14px;font-size:15px;font-weight:800;
     letter-spacing:.2px;cursor:pointer;font-family:inherit;margin-top:6px;transition:.15s;
     box-shadow:0 8px 20px rgba(109,40,217,.28)}
.btn:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(109,40,217,.36)}
.btn:disabled{opacity:.55;cursor:not-allowed;transform:none}
.err{background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c);
     border-left:3px solid var(--cx-danger, #dc2626);padding:11px 14px;border-radius:var(--cx-r-sm, 6px);
     font-size:13px;margin-bottom:16px;display:none}
.help{text-align:center;color:var(--cx-text-mute, #6b6b74);font-size:12.5px;margin-top:18px;line-height:1.5}
.foot{text-align:center;font-size:11px;color:var(--cx-text-mute, #6b6b74);line-height:1.8;margin-top:22px}
.foot .sello{font-weight:800;color:var(--cx-text-soft, #3f3f46);letter-spacing:.3px}
@media(max-width:420px){.card{padding:30px 22px 26px}.name{font-size:25px}}
</style>
</head>
<body>
<div class="aura"></div>
<main class="shell">
  <div class="card">
    <div class="brand">
      <span class="mark" aria-label="Espagiria">
        <svg viewBox="0 0 32 32" width="36" height="36" fill="none" stroke="#ffffff" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="12" r="3" fill="#ffffff"/>
          <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>
          <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".45"/>
        </svg>
      </span>
      <div class="name">Espagiria</div>
      <div class="tag">Tu marca, nuestra fórmula</div>
      <div class="sub">Portal de clientes</div>
    </div>
    <div class="err" id="err"></div>
    <form id="form-login">
      <div class="fg"><label for="email">Correo</label>
        <input type="email" id="email" placeholder="vos@tuempresa.com" required autocomplete="username" autofocus></div>
      <div class="fg"><label for="password">Contraseña</label>
        <input type="password" id="password" placeholder="Tu contraseña" required autocomplete="current-password"></div>
      <button type="submit" class="btn" id="btn-entrar">Entrar</button>
    </form>
    <p class="help">¿Todavía no tenés acceso? Pedíselo a tu ejecutivo comercial.</p>
  </div>
  <footer class="foot">
    <div><span class="sello">Espagiria Laboratorio</span> sobre <span class="sello">EOS</span></div>
    <div>&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
  </footer>
</main>
<script>
document.getElementById('form-login').addEventListener('submit', async function(e){
  e.preventDefault();
  var email = document.getElementById('email').value.trim().toLowerCase();
  var pw = document.getElementById('password').value;
  var err = document.getElementById('err');
  var btn = document.getElementById('btn-entrar');
  err.style.display = 'none';
  btn.disabled = true; btn.textContent = 'Entrando...';
  try {
    var r = await fetch('/api/portal/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: email, password: pw}),
      credentials: 'same-origin',
    });
    var d = await r.json();
    if (!r.ok) {
      err.textContent = d.error || 'No pudimos entrar con esos datos';
      err.style.display = 'block';
      btn.disabled = false; btn.textContent = 'Entrar';
      return;
    }
    window.location.href = '/portal';
  } catch(ex){
    err.textContent = 'No hay conexión con el servidor: ' + ex.message;
    err.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Entrar';
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
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Espagiria · Portal de clientes</title>
<meta name="application-name" content="Espagiria · Portal">
<meta name="apple-mobile-web-app-title" content="Portal Espagiria">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="author" content="HHA Group">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=eos11">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=eos11">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png?v=eos11">
<script>(function(){try{var t=localStorage.getItem('cx-theme');if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches){t='dark';}if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:var(--cx-bg, #f4f4f7);color:var(--cx-text, #18181b);min-height:100vh;font-size:15px;
     -webkit-font-smoothing:antialiased}
.wrap{max-width:1500px;margin:0 auto;padding:22px 26px 70px}

/* ── cabecera + navegación (un solo bloque pegajoso) ─────────────── */
.top{position:sticky;top:0;z-index:20;background:var(--cx-card, #ffffff);
     border-bottom:1px solid var(--cx-border, #e6e6ea);box-shadow:var(--cx-sh-sm, 0 1px 2px rgba(15,23,42,.04))}
.top .in{max-width:1500px;margin:0 auto;padding:11px 26px;display:flex;align-items:center;gap:12px}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.mark{width:38px;height:38px;border-radius:11px;display:inline-flex;align-items:center;justify-content:center;
      background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));
      box-shadow:0 6px 16px rgba(109,40,217,.26);flex-shrink:0}
.bname{font-size:17px;font-weight:800;letter-spacing:-.4px;line-height:1.15;display:flex;align-items:center;gap:7px}
.sello{font-size:9px;font-weight:800;letter-spacing:1px;text-transform:uppercase;
       color:var(--cx-primary-text, #6d28d9);background:var(--cx-primary-pale, #f5f3ff);
       border-radius:var(--cx-r-pill, 999px);padding:3px 8px}
.bsub{font-size:11px;color:var(--cx-text-mute, #6b6b74);font-weight:600;margin-top:1px}
.right{margin-left:auto;display:flex;align-items:center;gap:8px}
.saludo{font-size:13px;font-weight:700;color:var(--cx-text-soft, #3f3f46);max-width:210px;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ghost{border:1px solid var(--cx-border, #e6e6ea);background:var(--cx-card, #ffffff);
       color:var(--cx-text-soft, #3f3f46);border-radius:var(--cx-r-md, 10px);padding:8px 13px;font-size:12.5px;
       font-weight:700;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-flex;
       align-items:center;gap:6px;transition:.15s;white-space:nowrap}
.ghost:hover{background:var(--cx-bg-alt, #fbfbfd);border-color:var(--cx-primary-light, #a78bfa);
             color:var(--cx-primary-text, #6d28d9)}
.nav{max-width:1500px;margin:0 auto;padding:0 26px 9px;display:flex;gap:6px;overflow-x:auto}
.nav::-webkit-scrollbar{display:none}
.nb{flex:1;min-width:104px;padding:9px 12px;border-radius:var(--cx-r-md, 10px);border:1px solid transparent;
    background:var(--cx-border-soft, #f1f1f4);color:var(--cx-text-mute, #6b6b74);font-size:13px;font-weight:700;
    cursor:pointer;font-family:inherit;transition:.15s;white-space:nowrap;position:relative}
.nb:hover{color:var(--cx-text, #18181b);background:var(--cx-bg-alt, #fbfbfd);border-color:var(--cx-border, #e6e6ea)}
.nb.on{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;
       border-color:transparent;box-shadow:0 6px 16px rgba(109,40,217,.28)}
.punto{position:absolute;top:5px;right:7px;width:8px;height:8px;border-radius:50%;
       background:var(--cx-danger, #dc2626);display:none}
.punto.on{display:block}

/* ── vistas ───────────────────────────────────────────────────────── */
.vista{display:none}
.vista.on{display:block}
.h1{font-size:23px;font-weight:800;letter-spacing:-.6px;margin-bottom:3px}
.h1s{font-size:13.5px;color:var(--cx-text-mute, #6b6b74);margin-bottom:18px}
.rot{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1.1px;
     color:var(--cx-text-mute, #6b6b74);margin:22px 0 10px}
.card{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:var(--cx-r-lg, 14px);padding:22px;margin-bottom:14px;
      box-shadow:var(--cx-sh-sm, 0 1px 2px rgba(15,23,42,.04))}
.card h2{font-size:16.5px;font-weight:800;letter-spacing:-.3px}
.hint{font-size:12.5px;color:var(--cx-text-mute, #6b6b74);margin-top:5px;line-height:1.5}

/* ── franja de KPIs ──────────────────────────────────────────────── */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px;margin-bottom:16px}
.kpi{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:var(--cx-r-md, 10px);padding:13px 15px}
.kpi .k{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;
        color:var(--cx-text-mute, #6b6b74)}
.kpi .v{font-size:21px;font-weight:800;letter-spacing:-.6px;margin-top:4px;line-height:1.15}
.kpi .v.chico{font-size:15px;letter-spacing:-.2px;padding-top:4px}

/* ── tarjeta de pedido ───────────────────────────────────────────── */
.ped{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:var(--cx-r-lg, 14px);padding:18px 20px 16px;margin-bottom:12px;position:relative;
     overflow:hidden;box-shadow:var(--cx-sh-sm, 0 1px 2px rgba(15,23,42,.04))}
.ped.destacado{box-shadow:var(--cx-sh-md, 0 4px 12px rgba(15,23,42,.06))}
.ped::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;
             background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9))}
.ped.encurso::before{background:var(--cx-warn, #f59e0b)}
.ped.listo::before{background:var(--cx-success, #15803d)}
.ped.frenado::before{background:var(--cx-danger, #dc2626)}
.ped.anulado{opacity:.62}
.ped.anulado::before{background:var(--cx-text-faint, #a1a1aa)}
.ped-top{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
.ped-prod{font-size:17px;font-weight:800;letter-spacing:-.4px;line-height:1.25}
.ped-meta{font-size:12.5px;color:var(--cx-text-mute, #6b6b74);margin-top:3px}
.ped-num{font-size:11px;font-weight:800;color:var(--cx-text-faint, #a1a1aa);letter-spacing:.4px}
.ped-acc{margin-left:auto;display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:11px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:var(--cx-r-pill, 999px);
      font-size:11.5px;font-weight:800;letter-spacing:.1px}
.chip.ok{background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d)}
.chip.now{background:var(--cx-warn-pale, #fffbeb);color:var(--cx-warn-text, #b45309)}
.chip.wait{background:var(--cx-border-soft, #f1f1f4);color:var(--cx-text-mute, #6b6b74)}
.chip.bad{background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c)}
.chip.info{background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #6d28d9)}
.nota{font-size:12.5px;color:var(--cx-text-soft, #3f3f46);margin-top:10px;
      background:var(--cx-bg-alt, #fbfbfd);border-radius:var(--cx-r-sm, 6px);padding:8px 11px;
      white-space:pre-wrap;word-break:break-word}

/* ── riel de avance (horizontal) ─────────────────────────────────── */
.riel{display:flex;margin-top:16px}
.rp{flex:1;min-width:0;text-align:center;position:relative}
.rp::before{content:'';position:absolute;top:10px;left:-50%;width:100%;height:2px;
            background:var(--cx-border, #e6e6ea)}
.rp:first-child::before{display:none}
.rp.ok::before,.rp.now::before{background:var(--cx-success, #15803d)}
.rp .dot{width:21px;height:21px;border-radius:50%;margin:0 auto;position:relative;z-index:1;
         border:2px solid var(--cx-border, #e6e6ea);background:var(--cx-card, #ffffff);
         display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;line-height:1}
.rp.ok .dot{background:var(--cx-success, #15803d);border-color:var(--cx-success, #15803d);color:#fff}
.rp.now .dot{background:var(--cx-warn, #f59e0b);border-color:var(--cx-warn, #f59e0b);color:#fff;
             box-shadow:0 0 0 4px var(--cx-warn-pale, #fffbeb)}
.rp.bad .dot{background:var(--cx-danger, #dc2626);border-color:var(--cx-danger, #dc2626);color:#fff}
.rp .lb{font-size:9.5px;font-weight:700;color:var(--cx-text-faint, #a1a1aa);margin-top:7px;line-height:1.3;
        padding:0 2px}
.rp.ok .lb,.rp.now .lb{color:var(--cx-text-soft, #3f3f46)}
@media(max-width:600px){.rp .lb{display:none}.rp.now .lb{display:block;font-size:9px}}

/* ── detalle (línea de tiempo vertical) ──────────────────────────── */
.det{display:none;margin-top:14px;padding-top:13px;border-top:1px dashed var(--cx-border, #e6e6ea)}
.det.on{display:block}
.tl{display:flex;flex-direction:column;gap:6px}
.tls{display:flex;gap:11px;padding:9px 11px;border-radius:var(--cx-r-md, 10px);
     background:var(--cx-bg-alt, #fbfbfd);border-left:3px solid var(--cx-border, #e6e6ea)}
.tls.completado{background:var(--cx-success-pale, #f0fdf4);border-left-color:var(--cx-success, #15803d)}
.tls.en_curso{background:var(--cx-warn-pale, #fffbeb);border-left-color:var(--cx-warn, #f59e0b)}
.tls.rechazado{background:var(--cx-danger-pale, #fef2f2);border-left-color:var(--cx-danger, #dc2626)}
.tls.pendiente{opacity:.62}
.tls .ico{font-size:17px;line-height:1.2;width:22px;text-align:center;flex-shrink:0}
.tls .lb{font-size:13.5px;font-weight:700;color:var(--cx-text, #18181b)}
.tls.pendiente .lb{color:var(--cx-text-mute, #6b6b74)}
.tls .fe{font-size:10.5px;color:var(--cx-text-mute, #6b6b74);margin-top:1px}
.tls .de{font-size:11.5px;color:var(--cx-text-soft, #3f3f46);margin-top:2px}

/* ── formularios ─────────────────────────────────────────────────── */
label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;
      color:var(--cx-text-mute, #6b6b74);margin:17px 0 6px}
input,select,textarea{width:100%;padding:12px 14px;font-size:15px;font-family:inherit;
                      background:var(--cx-bg-alt, #fbfbfd);color:var(--cx-text, #18181b);
                      border:1px solid var(--cx-border, #e6e6ea);border-radius:var(--cx-r-md, 10px);
                      outline:none;transition:.15s}
textarea{resize:vertical;line-height:1.5}
input::placeholder,textarea::placeholder{color:var(--cx-text-faint, #a1a1aa)}
input:focus,select:focus,textarea:focus{border-color:var(--cx-primary-light, #a78bfa);
      background:var(--cx-card, #ffffff);box-shadow:0 0 0 3px var(--cx-primary-pale, #f5f3ff)}
.btn{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;border:none;
     border-radius:var(--cx-r-md, 10px);padding:13px 24px;font-size:14.5px;font-weight:800;cursor:pointer;
     font-family:inherit;transition:.15s;box-shadow:0 7px 18px rgba(109,40,217,.26)}
.btn:hover{transform:translateY(-1px);box-shadow:0 11px 24px rgba(109,40,217,.34)}
.btn:disabled{opacity:.55;cursor:not-allowed;transform:none;box-shadow:none}
.btn.mini{padding:7px 14px;font-size:12.5px;box-shadow:none}
.btn-fila{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:20px}
.dosc{display:grid;grid-template-columns:1fr;gap:14px;align-items:start}
@media(min-width:1080px){.dosc{grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr)}}
.lado{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:var(--cx-r-lg, 14px);padding:20px}
.lado h3{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.9px;
         color:var(--cx-text-mute, #6b6b74);margin-bottom:12px}
.paso{display:flex;gap:10px;align-items:flex-start;padding:7px 0;font-size:13px;line-height:1.4}
.paso .n{width:21px;height:21px;border-radius:50%;background:var(--cx-primary-pale, #f5f3ff);
         color:var(--cx-primary-text, #6d28d9);font-size:11px;font-weight:800;flex-shrink:0;
         display:flex;align-items:center;justify-content:center;margin-top:1px}
.dos{display:grid;grid-template-columns:1fr;gap:0}
@media(min-width:660px){.dos{grid-template-columns:1fr 1fr;gap:0 16px}}
.aviso{display:none;margin-top:8px;padding:10px 12px;border-radius:var(--cx-r-md, 10px);font-size:12.5px;
       line-height:1.5;background:var(--cx-warn-pale, #fffbeb);color:var(--cx-warn-text, #b45309);
       border-left:3px solid var(--cx-warn, #f59e0b)}
.aviso.grave{background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c);
             border-left-color:var(--cx-danger, #dc2626)}
.aviso.on{display:block}
.msg{display:none;margin-top:14px;padding:12px 15px;border-radius:var(--cx-r-md, 10px);font-size:13.5px;
     border-left:3px solid}
.msg.ok{display:block;background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d);
        border-left-color:var(--cx-success, #15803d)}
.msg.err{display:block;background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c);
         border-left-color:var(--cx-danger, #dc2626)}

/* ── hilos de mensajes ───────────────────────────────────────────── */
.hilo{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:var(--cx-r-lg, 14px);padding:16px 18px;margin-bottom:11px}
.hilo-top{display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap}
.hilo-tit{font-size:14.5px;font-weight:800;letter-spacing:-.2px}
.hilo-fe{font-size:11px;color:var(--cx-text-mute, #6b6b74);margin-left:auto;white-space:nowrap;padding-top:2px}
.hilo-txt{font-size:13px;color:var(--cx-text-soft, #3f3f46);margin-top:7px;white-space:pre-wrap;
          word-break:break-word;line-height:1.5}
.resp{margin-top:11px;padding:11px 13px;border-radius:var(--cx-r-md, 10px);
      background:var(--cx-primary-pale, #f5f3ff);border-left:3px solid var(--cx-primary-light, #a78bfa);
      font-size:13px;color:var(--cx-text, #18181b);line-height:1.5;white-space:pre-wrap;word-break:break-word}
.resp b{color:var(--cx-primary-text, #6d28d9);font-size:11.5px;text-transform:uppercase;letter-spacing:.5px}

/* ── vacíos y modal ──────────────────────────────────────────────── */
.vacio{text-align:center;padding:36px 20px;color:var(--cx-text-mute, #6b6b74);font-size:14px;line-height:1.6}
.vacio .em{font-size:36px;display:block;margin-bottom:10px}
.vacio .t{font-size:16px;font-weight:800;color:var(--cx-text, #18181b);margin-bottom:5px}
.ov{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:60;padding:18px;
    display:none;align-items:center;justify-content:center}
.ov.on{display:flex}
.mo{background:var(--cx-card, #ffffff);border-radius:var(--cx-r-xl, 20px);padding:24px;width:100%;
    max-width:520px;max-height:90vh;overflow-y:auto;box-shadow:var(--cx-sh-lg, 0 12px 32px rgba(15,23,42,.08))}
.mo h2{font-size:18px;font-weight:800;letter-spacing:-.3px}
.pie{text-align:center;font-size:11px;color:var(--cx-text-mute, #6b6b74);line-height:1.8;
     padding:26px 16px 34px}
.pie .sello2{font-weight:800;color:var(--cx-text-soft, #3f3f46);letter-spacing:.3px}
@media(max-width:560px){
  .top .in{padding:10px 14px;gap:9px}
  .saludo{display:none}
  .nav{padding:0 14px 9px}
  .nb{min-width:88px;font-size:12.5px;padding:9px 8px}
  .wrap{padding:18px 14px 60px}
  .h1{font-size:20px}
  .saludo-h{font-size:21px}
  .mods{grid-template-columns:repeat(2,1fr);gap:10px}
  .mod{min-height:104px;padding:18px 8px 14px}
  .mod .ico svg{width:26px;height:26px}
}

/* ── portada de módulos (mismo lenguaje que /modulos) ────────────── */
.saludo-h{font-size:24px;font-weight:800;letter-spacing:-.7px}
.saludo-s{font-size:13.5px;color:var(--cx-text-mute, #6b6b74);margin:3px 0 20px}
.mods{display:grid;grid-template-columns:repeat(auto-fill,minmax(188px,1fr));gap:14px}
.mod{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;
     padding:22px 12px 18px;background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:var(--cx-r-lg, 14px);cursor:pointer;font-family:inherit;text-align:center;
     min-height:118px;transition:.18s;position:relative;color:var(--cx-text, #18181b);
     box-shadow:var(--cx-sh-sm, 0 1px 2px rgba(15,23,42,.04))}
.mod:hover{border-color:var(--cx-primary-light, #a78bfa);transform:translateY(-3px);
           box-shadow:var(--cx-sh-md, 0 4px 12px rgba(15,23,42,.06))}
.mod .ico{color:var(--cx-primary-text, #6d28d9);display:inline-flex;transition:transform .18s}
.mod:hover .ico{transform:scale(1.08)}
.mod .ico svg{width:30px;height:30px}
.mod .nm{font-size:14px;font-weight:800;letter-spacing:-.2px}
.mod .ds{font-size:10.5px;color:var(--cx-text-mute, #6b6b74);line-height:1.35;font-weight:500}
.mod .bdg{position:absolute;top:9px;right:10px;min-width:20px;height:20px;border-radius:999px;
          background:var(--cx-danger, #dc2626);color:#fff;font-size:10.5px;font-weight:800;
          display:none;align-items:center;justify-content:center;padding:0 6px}
.mod .bdg.on{display:flex}
.volver{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--cx-border, #e6e6ea);
        background:var(--cx-card, #ffffff);color:var(--cx-text-soft, #3f3f46);border-radius:var(--cx-r-md, 10px);
        padding:8px 13px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;margin-bottom:16px}
.volver:hover{border-color:var(--cx-primary-light, #a78bfa);color:var(--cx-primary-text, #6d28d9)}

/* ── filas (facturas, pagos, documentos) ─────────────────────────── */
.fila{background:var(--cx-card, #ffffff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:var(--cx-r-md, 10px);padding:14px 16px;margin-bottom:9px;
      display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.fila .izq{min-width:0;flex:1}
.fila .t1{font-size:14.5px;font-weight:800;letter-spacing:-.2px}
.fila .t2{font-size:12px;color:var(--cx-text-mute, #6b6b74);margin-top:2px}
.fila .der{text-align:right;white-space:nowrap}
.plata{font-size:16px;font-weight:800;letter-spacing:-.4px;font-variant-numeric:tabular-nums}
.plata.debe{color:var(--cx-danger-text, #b91c1c)}
.plata.paga{color:var(--cx-success-text, #15803d)}

/* ── consumo ─────────────────────────────────────────────────────── */
.barra{display:flex;align-items:center;gap:10px;margin-bottom:9px}
.barra .nm{font-size:13px;font-weight:700;width:38%;min-width:0;overflow:hidden;
           text-overflow:ellipsis;white-space:nowrap}
.barra .tr{flex:1;height:9px;border-radius:999px;background:var(--cx-border-soft, #f1f1f4);overflow:hidden}
.barra .fl{height:100%;border-radius:999px;background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9))}
.barra .vl{font-size:12px;font-weight:800;font-variant-numeric:tabular-nums;
           color:var(--cx-text-soft, #3f3f46);width:92px;text-align:right}
.aviso.info{background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-text, #18181b);
            border-left-color:var(--cx-primary-light, #a78bfa)}
input[type=file]{padding:10px;background:var(--cx-bg-alt, #fbfbfd);cursor:pointer}
</style>
</head>
<body>

<div class="top">
  <div class="in">
    <div class="brand">
      <span class="mark" aria-label="Espagiria">
        <svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="#ffffff" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="12" r="3" fill="#ffffff"/>
          <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.8" stroke-linecap="round" opacity=".8"/>
          <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.8" stroke-linecap="round" opacity=".45"/>
        </svg>
      </span>
      <div>
        <div class="bname">Espagiria <span class="sello">sobre EOS</span></div>
        <div class="bsub">Portal de clientes</div>
      </div>
    </div>
    <div class="right">
      <span class="saludo" id="saludo"></span>
      <button class="ghost" onclick="cambiarTema()" title="Cambiar entre claro y oscuro" aria-label="Cambiar tema">◐</button>
      <a href="/portal/logout" class="ghost">Salir</a>
    </div>
  </div>
</div>

<div class="wrap">

  <!-- ══ INICIO ══════════════════════════════════════════════════ -->
  <section class="vista on" id="v-inicio">
    <div class="saludo-h" id="ini-saludo">Hola</div>
    <div class="saludo-s">Tu portal con Espagiria: pedí, seguí tu producción, revisá tus facturas y mandanos lo que necesites.</div>
    <div class="kpis" id="ini-kpis"></div>
    <div id="ini-lista"></div>
    <div class="rot">Tu portal</div>
    <div class="mods">
      <button class="mod" onclick="irA('pedir')"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg></span><span class="nm">Pedir</span><span class="ds">productos y cantidades</span></button>
      <button class="mod" onclick="irA('pedidos')"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6a1 1 0 0 1 1 1v1H8V4a1 1 0 0 1 1-1z"/><path d="M16 5h2a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2"/><path d="M9 12l2 2 4-4"/></svg></span><span class="nm">Mis pedidos</span><span class="ds">estado y etapas</span></button>
      <button class="mod" onclick="irA('facturas')"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/></svg></span><span class="nm">Facturas</span><span class="ds">saldo y vencimientos</span></button>
      <button class="mod" onclick="irA('pagos')"><span class="bdg" id="bdg-pagos"></span><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M12 17l0-4M10 15l2-2 2 2"/></svg></span><span class="nm">Pagos</span><span class="ds">cargá tu comprobante</span></button>
      <button class="mod" onclick="irA('documentos')"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg></span><span class="nm">Documentos</span><span class="ds">certificados de análisis</span></button>
      <button class="mod" onclick="irA('consumo')"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l3-4 3 3 5-7"/></svg></span><span class="nm">Mi consumo</span><span class="ds">qué y cuánto pedís</span></button>
      <button class="mod" onclick="irA('mensajes')"><span class="bdg" id="bdg-mensajes"></span><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span><span class="nm">Mensajes</span><span class="ds">escribinos</span></button>
    </div>
  </section>

  <!-- ══ PEDIR ═══════════════════════════════════════════════════ -->
  <section class="vista" id="v-pedir">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Pedir producto</div>
    <div class="h1s">Elegí qué necesitás y para cuándo. Te confirmamos la fecha real apenas entre al plan de producción.</div>
    <div class="dosc">
    <div class="card">
      <label for="sol-producto">Producto</label>
      <select id="sol-producto"><option value="">Cargando productos...</option></select>
      <div class="dos">
        <div>
          <label for="sol-cant">Cantidad (unidades)</label>
          <input id="sol-cant" type="number" min="1" step="1" placeholder="Ej. 500">
        </div>
        <div>
          <label for="sol-fecha">Fecha de entrega deseada</label>
          <input id="sol-fecha" type="date">
        </div>
      </div>
      <div class="aviso" id="sol-aviso"></div>
      <input type="hidden" id="sol-ml" value="0">
      <div class="dos">
        <div>
          <label for="sol-urgencia">Urgencia</label>
          <select id="sol-urgencia">
            <option value="media" selected>Media · planificación normal</option>
            <option value="baja">Baja · sin apuro</option>
            <option value="alta">Alta · necesitamos prioridad</option>
          </select>
        </div>
        <div>
          <label for="sol-repetir">Repetir el pedido</label>
          <select id="sol-repetir">
            <option value="0">No repetir (pedido único)</option>
            <option value="15">Cada 15 días</option>
            <option value="30">Cada mes</option>
            <option value="60">Cada 2 meses</option>
            <option value="90">Cada 3 meses</option>
          </select>
        </div>
      </div>
      <label for="sol-notas">Notas para producción (opcional)</label>
      <textarea id="sol-notas" rows="3" placeholder="Color, arte, tipo de envase, cualquier detalle que debamos saber."></textarea>
      <div class="btn-fila">
        <button class="btn" id="btn-enviar" onclick="enviarPedido()">Enviar solicitud</button>
        <span class="hint" style="margin-top:0">Pedimos avisar con un mes de anticipación.</span>
      </div>
      <div class="msg" id="sol-msg"></div>
    </div>
    <div class="lado">
      <h3>Qué pasa después</h3>
      <div class="paso"><span class="n">1</span><div><b>Lo recibimos</b> y lo revisamos con producción.</div></div>
      <div class="paso"><span class="n">2</span><div><b>Te confirmamos la fecha</b> real, con el lote ya asignado en el plan.</div></div>
      <div class="paso"><span class="n">3</span><div><b>Fabricación y envasado</b>, con las etapas a la vista en Mis pedidos.</div></div>
      <div class="paso"><span class="n">4</span><div><b>Microbiología</b> y liberación de Control de Calidad.</div></div>
      <div class="paso"><span class="n">5</span><div><b>Despacho</b>, con su certificado de análisis en Documentos.</div></div>
      <div class="hint" style="margin-top:14px">Pedí con un mes de anticipación siempre que puedas: la producción se programa por lotes y el envase también se compra. Si es urgente, marcalo en Urgencia y lo miramos.</div>
    </div>
    </div>
  </section>

  <!-- ══ MIS PEDIDOS ═════════════════════════════════════════════ -->
  <section class="vista" id="v-pedidos">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Mis pedidos</div>
    <div class="h1s">Todo lo que nos pediste, con el detalle de cada etapa.</div>
    <div id="lista-pedidos"><div class="vacio">Cargando...</div></div>
  </section>

  <!-- ══ MENSAJES ════════════════════════════════════════════════ -->
  <section class="vista" id="v-mensajes">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Mensajes</div>
    <div class="h1s">Escribinos por lo que sea: un problema con un lote, un producto nuevo, una reunión o una duda.</div>
    <div class="dosc">
    <div class="card">
      <label for="msg-tipo">¿De qué se trata?</label>
      <select id="msg-tipo" onchange="msgTipoChange()">
        <optgroup label="Comercial">
          <option value="consulta" selected>Consulta general</option>
          <option value="nuevo_producto">Quiero un producto nuevo</option>
          <option value="reunion">Reunión con gerencia</option>
        </optgroup>
        <optgroup label="Sobre un pedido o un problema">
          <option value="reclamo">Reclamo · algo llegó mal</option>
          <option value="queja">Queja · algo no salió como esperabas</option>
          <option value="peticion">Petición formal</option>
          <option value="sugerencia">Sugerencia</option>
        </optgroup>
      </select>
      <div id="msg-box-tit">
        <label for="msg-titulo" id="msg-titulo-lbl">Asunto</label>
        <input id="msg-titulo" maxlength="200" placeholder="Una línea que resuma el tema">
      </div>
      <div id="msg-box-prod" style="display:none">
        <label for="msg-prod">¿Qué producto querés que desarrollemos?</label>
        <input id="msg-prod" placeholder="Ej. Serum de niacinamida 30 ml">
      </div>
      <div id="msg-box-fecha" style="display:none">
        <label for="msg-fecha">Fecha que te sirve</label>
        <input id="msg-fecha" type="date">
      </div>
      <label for="msg-texto" id="msg-texto-lbl">Contanos el detalle</label>
      <textarea id="msg-texto" rows="5" maxlength="5000" placeholder="Mientras más contexto nos des, mejor te podemos responder."></textarea>
      <div class="aviso" id="msg-aviso"></div>
      <div class="btn-fila"><button class="btn" id="btn-msg" onclick="enviarMensaje()">Enviar</button></div>
      <div class="msg" id="msg-salida"></div>
    </div>
    <div>
      <div class="rot" style="margin-top:0">Conversaciones</div>
      <div id="lista-hilos"><div class="vacio">Cargando...</div></div>
    </div>
    </div>
  </section>


  <!-- ══ FACTURAS ════════════════════════════════════════════════ -->
  <section class="vista" id="v-facturas">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Facturas</div>
    <div class="h1s">Lo que te facturamos, lo que ya pagaste y lo que queda pendiente.</div>
    <div class="kpis" id="fact-kpis"></div>
    <div id="fact-lista"><div class="vacio">Cargando...</div></div>
  </section>

  <!-- ══ PAGOS ═══════════════════════════════════════════════════ -->
  <section class="vista" id="v-pagos">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Reportar un pago</div>
    <div class="h1s">Cargá el comprobante y lo cruzamos con tu factura. Te avisamos acá mismo cuando quede aplicado.</div>
    <div class="dosc">
    <div class="card">
      <label for="pg-factura">Factura que estás pagando</label>
      <select id="pg-factura"><option value="">Sin factura puntual</option></select>
      <div class="dos">
        <div>
          <label for="pg-monto">Monto pagado</label>
          <input id="pg-monto" type="number" min="1" step="1" placeholder="Ej. 1500000">
        </div>
        <div>
          <label for="pg-fecha">Fecha del pago</label>
          <input id="pg-fecha" type="date">
        </div>
      </div>
      <div class="dos">
        <div>
          <label for="pg-metodo">Medio</label>
          <select id="pg-metodo">
            <option>Transferencia</option>
            <option>Consignación</option>
            <option>Efectivo</option>
            <option>Cheque</option>
            <option>Otro</option>
          </select>
        </div>
        <div>
          <label for="pg-ref">Referencia o número de la transacción</label>
          <input id="pg-ref" maxlength="120" placeholder="Opcional">
        </div>
      </div>
      <label for="pg-archivo">Comprobante (PDF o foto, hasta 8 MB)</label>
      <input id="pg-archivo" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp">
      <label for="pg-nota">Nota</label>
      <textarea id="pg-nota" rows="2" maxlength="500" placeholder="Algo que debamos tener en cuenta"></textarea>
      <div class="btn-fila"><button class="btn" id="pg-btn" onclick="enviarPago()">Enviar el pago</button></div>
      <div class="msg" id="pg-msg"></div>
    </div>
    <div>
      <div class="rot" style="margin-top:0">Pagos que reportaste</div>
      <div id="pg-lista"><div class="vacio">Cargando...</div></div>
    </div>
    </div>
  </section>

  <!-- ══ DOCUMENTOS ══════════════════════════════════════════════ -->
  <section class="vista" id="v-documentos">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Documentos</div>
    <div class="h1s">El certificado de análisis de cada lote que produjimos para vos, apenas Control de Calidad lo libera.</div>
    <div id="doc-lista"><div class="vacio">Cargando...</div></div>
  </section>

  <!-- ══ CONSUMO ═════════════════════════════════════════════════ -->
  <section class="vista" id="v-consumo">
    <button class="volver" onclick="irA('inicio')">Volver</button>
    <div class="h1">Mi consumo</div>
    <div class="h1s">Qué nos pedís, cuánto y con qué frecuencia. Sale de tus pedidos, sin los cancelados.</div>
    <div class="kpis" id="con-kpis"></div>
    <div id="con-cuerpo"><div class="vacio">Cargando...</div></div>
  </section>

</div>

<!-- ══ modal editar pedido ═══════════════════════════════════════ -->
<div class="ov" id="ov-editar" onclick="if(event.target===this)cerrarEditar()">
  <div class="mo">
    <h2>Editar pedido</h2>
    <p class="hint" id="ed-prod"></p>
    <div class="dos">
      <div>
        <label for="ed-cant">Cantidad (unidades)</label>
        <input id="ed-cant" type="number" min="1" step="1">
      </div>
      <div>
        <label for="ed-fecha">Fecha de entrega deseada</label>
        <input id="ed-fecha" type="date">
      </div>
    </div>
    <label for="ed-notas">Notas</label>
    <textarea id="ed-notas" rows="3" placeholder="Detalles para producción"></textarea>
    <div class="msg" id="ed-msg"></div>
    <div class="btn-fila">
      <button class="btn" id="ed-btn" onclick="guardarEdicion()">Guardar cambios</button>
      <button class="ghost" onclick="cerrarEditar()">Cancelar</button>
    </div>
  </div>
</div>

<footer class="pie">
  <div><span class="sello2">Espagiria Laboratorio</span> sobre <span class="sello2">EOS</span></div>
  <div>Desarrollado por <span class="sello2">HHA Group</span> &middot; &copy; 2026 HHA Group S.A.S.</div>
</footer>

<script>
var _PEDIDOS = [], _PEDIDOS_OK = false, _HILOS_OK = false, _EDITANDO = 0;
var _PQR_TIPOS = ['peticion', 'queja', 'reclamo', 'sugerencia'];
var _TIPO_LBL = {
  peticion: 'Petición', queja: 'Queja', reclamo: 'Reclamo', sugerencia: 'Sugerencia',
  nuevo_producto: 'Producto nuevo', reunion: 'Reunión con gerencia', consulta: 'Consulta',
  cotizacion: 'Cotización', muestras: 'Muestras', ficha_tecnica: 'Ficha técnica'
};
// El estado que ve el cliente se escribe como se habla · el valor crudo de la
// base ('en_revision') es de la base, no de la pantalla.
var _EST_LBL = {
  abierto: 'Abierta', en_revision: 'En revisión', respondido: 'Respondida',
  respondida: 'Respondida', cerrado: 'Cerrada', cerrada: 'Cerrada', nueva: 'Recibida',
  convertida: 'Convertida en pedido', rechazada: 'No procede'
};
function estadoLbl(e){
  var k = String(e || '').toLowerCase();
  return _EST_LBL[k] || (k ? k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, ' ') : '');
}

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function $(id){return document.getElementById(id);}
// El cliente lee "8 sep", no "2026-09-08". El año sólo aparece cuando no es
// el actual (si no, ocupa lugar y no informa nada).
var _MES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
function fmtMes(m){
  var p = String(m || '').split('-');
  if(p.length !== 2) return m;
  return (_MES[parseInt(p[1], 10) - 1] || p[1]) + ' ' + p[0];
}
function fmtFecha(f){
  if(!f) return '';
  var s = String(f).slice(0, 10), p = s.split('-');
  if(p.length !== 3) return s;
  var d = parseInt(p[2], 10), m = parseInt(p[1], 10) - 1;
  if(isNaN(d) || isNaN(m) || !_MES[m]) return s;
  return d + ' ' + _MES[m] + (String(new Date().getFullYear()) === p[0] ? '' : (' ' + p[0]));
}
function cambiarTema(){
  var h = document.documentElement;
  var n = h.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  if(n === 'dark'){ h.setAttribute('data-theme','dark'); } else { h.removeAttribute('data-theme'); }
  try{ localStorage.setItem('cx-theme', n); }catch(e){}
}
var _VISTAS = ['inicio','pedir','pedidos','facturas','pagos','documentos','consumo','mensajes'];
function irA(v){
  _VISTAS.forEach(function(k){
    var s = $('v-' + k); if(s) s.classList.toggle('on', k === v);
  });
  window.scrollTo(0, 0);
  if(v === 'inicio' || v === 'pedidos') cargarPedidos();
  if(v === 'mensajes') cargarHilos();
  if(v === 'facturas') cargarFacturas();
  if(v === 'pagos') cargarPagos();
  if(v === 'documentos') cargarDocumentos();
  if(v === 'consumo') cargarConsumo();
}
function plata(v){
  return '$' + Number(v || 0).toLocaleString('es-CO', {maximumFractionDigits: 0});
}

/* ── pedidos ─────────────────────────────────────────────────────── */
function activo(p){ return ['despachado','cancelado'].indexOf(p.estado) < 0; }
function nombreDe(p){ return p.producto_mostrar || p.producto_nombre || 'Producto'; }
function acentoDe(p){
  if(p.estado === 'cancelado') return 'anulado';
  if(p.estado === 'despachado') return 'listo';
  var k = p.estado_visible_kind || 'pendiente';
  if(k === 'rechazado') return 'frenado';
  if(k === 'en_curso') return 'encurso';
  return '';
}
function chipDe(p){
  var k = p.estado_visible_kind || 'pendiente';
  if(p.estado === 'cancelado') return 'wait';
  return {completado:'ok', en_curso:'now', rechazado:'bad', pendiente:'wait'}[k] || 'wait';
}
function rielHtml(tl){
  if(!tl || !tl.length) return '';
  return '<div class="riel">' + tl.map(function(s){
    var e = s.estado || 'pendiente';
    var c = e === 'completado' ? 'ok' : (e === 'en_curso' ? 'now' : (e === 'rechazado' ? 'bad' : ''));
    var m = e === 'completado' ? '✓' : (e === 'rechazado' ? '!' : '');
    return '<div class="rp ' + c + '"><div class="dot">' + m + '</div>'
         + '<div class="lb">' + esc(s.label || '') + '</div></div>';
  }).join('') + '</div>';
}
function tlHtml(tl){
  if(!tl || !tl.length) return '<div class="hint">Todavía no hay etapas registradas.</div>';
  return '<div class="tl">' + tl.map(function(s){
    return '<div class="tls ' + esc(s.estado || 'pendiente') + '">'
      + '<div class="ico">' + esc(s.icon || '·') + '</div><div style="min-width:0">'
      + '<div class="lb">' + esc(s.label || '') + '</div>'
      + (s.fecha ? '<div class="fe">' + esc(fmtFecha(s.fecha)) + '</div>' : '')
      + (s.detalle ? '<div class="de">' + esc(s.detalle) + '</div>' : '')
      + '</div></div>';
  }).join('') + '</div>';
}
// `ctx` dice en QUÉ lista se dibuja la tarjeta: un pedido en curso aparece en
// Inicio y en Mis pedidos, así que sin prefijo los dos paneles de detalle
// nacen con el MISMO id y getElementById devuelve el de Inicio, que está
// oculto (el botón de Mis pedidos no hacía nada · M120).
function tarjetaPedido(p, destacada, ctx){
  var urg = {alta:'Urgencia alta', media:'Urgencia media', baja:'Sin apuro'}[p.urgencia || 'media'] || 'Urgencia media';
  var urgCls = (p.urgencia === 'alta') ? 'bad' : 'wait';
  var fechaChip = p.fecha_lista
    ? '<span class="chip ok">Listo estimado: ' + esc(fmtFecha(p.fecha_lista)) + '</span>'
    : (p.fecha_estimada
        ? '<span class="chip wait">Pediste para ' + esc(fmtFecha(p.fecha_estimada)) + ' · a confirmar</span>' : '');
  var editable = (p.estado === 'pendiente');
  return '<div class="ped ' + acentoDe(p) + (destacada ? ' destacado' : '') + '">'
    + '<div class="ped-top"><div style="min-width:0">'
    +   '<div class="ped-num">Pedido #' + p.id + '</div>'
    +   '<div class="ped-prod">' + esc(nombreDe(p)) + '</div>'
    +   '<div class="ped-meta">' + p.cantidad_uds + ' unidades'
    +     (p.ml_unidad ? ' de ' + p.ml_unidad + ' ml' : '')
    +     (p.kg_equivalente ? ' · ' + p.kg_equivalente + ' kg' : '') + '</div>'
    + '</div><div class="ped-acc">'
    +   (editable ? '<button class="ghost" onclick="abrirEditar(' + p.id + ')">Editar</button>' : '')
    +   '<button class="ghost" onclick="verDetalle(&quot;' + ctx + '&quot;,' + p.id + ')" id="btn-det-' + ctx + '-' + p.id + '">Ver detalle</button>'
    + '</div></div>'
    + '<div class="chips">'
    +   '<span class="chip ' + chipDe(p) + '">' + esc(p.estado === 'cancelado' ? 'Cancelado' : (p.estado_visible || 'Recibido')) + '</span>'
    +   fechaChip
    +   '<span class="chip ' + urgCls + '">' + urg + '</span>'
    + '</div>'
    + rielHtml(p.timeline)
    + (p.notas ? '<div class="nota">' + esc(p.notas) + '</div>' : '')
    + '<div class="det" id="det-' + ctx + '-' + p.id + '">' + tlHtml(p.timeline) + '</div>'
    + '</div>';
}
function verDetalle(ctx, id){
  var d = $('det-' + ctx + '-' + id); if(!d) return;
  var abierto = d.classList.toggle('on');
  var b = $('btn-det-' + ctx + '-' + id);
  if(b) b.textContent = abierto ? 'Ocultar detalle' : 'Ver detalle';
}
async function cargarPedidos(forzar){
  if(_PEDIDOS_OK && !forzar){ pintarInicio(); pintarPedidos(); return; }
  try{
    var r = await fetch('/api/portal/mis-pedidos', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    _PEDIDOS = d.pedidos || [];
    _PEDIDOS_OK = true;
  }catch(e){
    var err = '<div class="vacio">No pudimos traer tus pedidos. Revisá la conexión y volvé a intentar.</div>';
    $('ini-lista').innerHTML = err; $('lista-pedidos').innerHTML = err;
    return;
  }
  pintarInicio(); pintarPedidos();
}
function pintarInicio(){
  var box = $('ini-lista'), kpis = $('ini-kpis');
  var enCurso = _PEDIDOS.filter(activo);
  var entregados = _PEDIDOS.filter(function(p){ return p.estado === 'despachado'; }).length;
  var fechas = enCurso.map(function(p){ return p.fecha_lista; }).filter(Boolean).sort();
  kpis.innerHTML =
      '<div class="kpi"><div class="k">En curso</div><div class="v">' + enCurso.length + '</div></div>'
    + '<div class="kpi"><div class="k">Próximo listo</div><div class="v'
    +   (fechas.length ? '' : ' chico') + '">' + (fechas.length ? esc(fmtFecha(fechas[0])) : 'A confirmar') + '</div></div>'
    + '<div class="kpi"><div class="k">Entregados</div><div class="v">' + entregados + '</div></div>';
  if(!enCurso.length){
    box.innerHTML = '<div class="card"><div class="vacio">'
      + '<span class="em">📦</span>'
      + '<div class="t">No tenés pedidos en curso</div>'
      + 'Cuando nos pidas un producto, acá vas a ver en qué etapa va: producción, envasado, microbiología y despacho.'
      + '</div></div>';
    return;
  }
  box.innerHTML = '<div class="rot" style="margin-top:0">'
    + (enCurso.length === 1 ? 'Tu pedido en curso' : 'Tus pedidos en curso') + '</div>'
    + enCurso.map(function(p){ return tarjetaPedido(p, true, 'ini'); }).join('');
}

/* ── facturas ────────────────────────────────────────────────────── */
var _FACTURAS = [];
async function cargarFacturas(forzar){
  var box = $('fact-lista'), kpis = $('fact-kpis');
  try{
    var r = await fetch('/api/portal/facturas', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    if(d.enlazado === false){
      kpis.innerHTML = '';
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">🔗</span>'
        + '<div class="t">Todavía no podemos mostrarte tus facturas</div>' + esc(d.mensaje || '')
        + '</div></div>';
      return;
    }
    _FACTURAS = d.facturas || [];
    llenarSelectFacturas();
    kpis.innerHTML =
        '<div class="kpi"><div class="k">Saldo pendiente</div><div class="v">' + plata(d.saldo_total) + '</div></div>'
      + '<div class="kpi"><div class="k">Vencido</div><div class="v" style="color:'
      +   (d.vencido_total > 0 ? 'var(--cx-danger-text, #b91c1c)' : 'inherit') + '">'
      +   plata(d.vencido_total) + '</div></div>'
      + '<div class="kpi"><div class="k">Facturas</div><div class="v">' + _FACTURAS.length + '</div></div>';
    if(!_FACTURAS.length){
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">🧾</span>'
        + '<div class="t">No tenés facturas registradas</div>'
        + 'Cuando emitamos la primera, la vas a ver acá con su saldo.</div></div>';
      return;
    }
    box.innerHTML = _FACTURAS.map(function(f){
      var chip = f.estado === 'Anulada' ? '<span class="chip wait">Anulada</span>'
        : (f.saldo <= 0.01 ? '<span class="chip ok">Pagada</span>'
          : (f.vencida ? '<span class="chip bad">Vencida</span>'
            : '<span class="chip now">Pendiente</span>'));
      return '<div class="fila"><div class="izq">'
        + '<div class="t1">' + esc(f.numero) + '</div>'
        + '<div class="t2">Emitida ' + esc(fmtFecha(f.fecha_emision))
        +   (f.fecha_vencimiento ? ' · vence ' + esc(fmtFecha(f.fecha_vencimiento)) : '')
        +   (f.numero_pedido ? ' · pedido ' + esc(f.numero_pedido) : '') + '</div>'
        + '<div class="chips">' + chip
        +   (f.pagado > 0 ? '<span class="chip info">Pagaste ' + plata(f.pagado) + '</span>' : '')
        + '</div></div>'
        + '<div class="der"><div class="plata ' + (f.saldo > 0.01 ? 'debe' : 'paga') + '">'
        +   plata(f.saldo > 0.01 ? f.saldo : f.total) + '</div>'
        + '<div class="t2">' + (f.saldo > 0.01 ? 'saldo de ' + plata(f.total) : 'total') + '</div>'
        + '<a class="ghost" style="margin-top:8px;display:inline-flex" target="_blank" rel="noopener"'
        +   ' href="/portal/factura/' + encodeURIComponent(f.numero) + '.pdf">Ver PDF</a>'
        + '</div></div>';
    }).join('');
  }catch(e){
    box.innerHTML = '<div class="vacio">No pudimos traer tus facturas. Revisá la conexión.</div>';
  }
}
function llenarSelectFacturas(){
  var sel = $('pg-factura'); if(!sel) return;
  var pend = _FACTURAS.filter(function(f){ return f.saldo > 0.01 && f.estado !== 'Anulada'; });
  sel.innerHTML = '<option value="">Sin factura puntual</option>'
    + pend.map(function(f){
        return '<option value="' + esc(f.numero) + '">' + esc(f.numero) + ' · saldo ' + plata(f.saldo) + '</option>';
      }).join('');
}

/* ── pagos que reporta el cliente ────────────────────────────────── */
async function cargarPagos(){
  // Esperar las facturas: si no, el desplegable de 'que factura estas pagando'
  // queda vacio justo cuando el cliente entra directo a Pagos.
  if(!_FACTURAS.length) await cargarFacturas();
  var box = $('pg-lista');
  try{
    var r = await fetch('/api/portal/pagos', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    var items = d.pagos || [];
    if(!items.length){
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">💳</span>'
        + '<div class="t">Todavía no reportaste pagos</div>'
        + 'Cuando cargues uno, acá vas a ver si quedó aplicado.</div></div>';
      return;
    }
    box.innerHTML = items.map(function(p){
      var chip = p.estado === 'conciliado' ? '<span class="chip ok">Aplicado</span>'
        : (p.estado === 'rechazado' ? '<span class="chip bad">No se pudo aplicar</span>'
          : '<span class="chip now">Lo estamos revisando</span>');
      return '<div class="fila"><div class="izq">'
        + '<div class="t1">' + plata(p.monto) + (p.factura_numero ? ' · ' + esc(p.factura_numero) : '') + '</div>'
        + '<div class="t2">' + esc(fmtFecha(p.fecha_pago)) + ' · ' + esc(p.metodo)
        +   (p.referencia ? ' · ' + esc(p.referencia) : '') + '</div>'
        + '<div class="chips">' + chip
        +   (p.archivo_estado === 'guardado'
              ? '<span class="chip info">Con comprobante</span>'
              : (p.archivo_estado === 'sin_archivo' ? '' : '<span class="chip wait">Sin comprobante</span>'))
        + '</div>'
        + (p.motivo ? '<div class="resp"><b>Motivo</b><br>' + esc(p.motivo) + '</div>' : '')
        + '</div></div>';
    }).join('');
  }catch(e){ box.innerHTML = '<div class="vacio">No pudimos traer tus pagos.</div>'; }
}
async function enviarPago(){
  var btn = $('pg-btn'), msg = $('pg-msg');
  msg.className = 'msg';
  var monto = parseFloat($('pg-monto').value || '0');
  if(!monto || monto <= 0){
    msg.className = 'msg err'; msg.textContent = 'Poné el monto que pagaste.'; return;
  }
  var fd = new FormData();
  fd.append('monto', monto);
  fd.append('factura_numero', $('pg-factura').value || '');
  fd.append('fecha_pago', $('pg-fecha').value || '');
  fd.append('metodo', $('pg-metodo').value || 'Transferencia');
  fd.append('referencia', $('pg-ref').value.trim());
  fd.append('nota', $('pg-nota').value.trim());
  var f = $('pg-archivo');
  if(f && f.files && f.files[0]) fd.append('archivo', f.files[0]);
  btn.disabled = true; btn.textContent = 'Enviando...';
  try{
    var r = await fetch('/api/portal/pagos', {method:'POST', credentials:'same-origin', body: fd});
    var d = await r.json();
    if(!r.ok){ msg.className = 'msg err'; msg.textContent = d.error || ('No se pudo enviar (' + r.status + ')'); return; }
    msg.className = 'msg ok';
    msg.textContent = (d.mensaje || 'Recibido.') + (d.aviso ? ' ' + d.aviso : '');
    $('pg-monto').value = ''; $('pg-ref').value = ''; $('pg-nota').value = '';
    if(f) f.value = '';
    cargarPagos();
    actualizarPunto();
  }catch(e){
    msg.className = 'msg err'; msg.textContent = 'No hay conexión con el servidor';
  }finally{
    btn.disabled = false; btn.textContent = 'Enviar el pago';
  }
}

/* ── documentos (certificados de análisis) ───────────────────────── */
async function cargarDocumentos(){
  var box = $('doc-lista');
  try{
    var r = await fetch('/api/portal/documentos', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    var docs = d.documentos || [];
    if(!docs.length){
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">📄</span>'
        + '<div class="t">Todavía no hay certificados</div>'
        + 'Apenas produzcamos un lote para vos y Control de Calidad lo libere, su certificado aparece acá.'
        + '</div></div>';
      return;
    }
    box.innerHTML = docs.map(function(x){
      return '<div class="fila"><div class="izq">'
        + '<div class="t1">' + esc(x.producto || 'Producto') + '</div>'
        + '<div class="t2">Lote ' + esc(x.lote) + ' · pedido #' + x.pedido_id
        +   (x.fecha ? ' · ' + esc(fmtFecha(x.fecha)) : '') + '</div>'
        + (x.disponible ? '' : '<div class="chips"><span class="chip wait">' + esc(x.motivo) + '</span></div>')
        + '</div><div class="der">'
        + (x.disponible
            ? '<a class="ghost" href="' + esc(x.url) + '" target="_blank" rel="noopener">Ver certificado</a>'
            : '')
        + '</div></div>';
    }).join('');
  }catch(e){ box.innerHTML = '<div class="vacio">No pudimos traer tus documentos.</div>'; }
}

/* ── mi consumo ──────────────────────────────────────────────────── */
async function cargarConsumo(){
  var box = $('con-cuerpo'), kpis = $('con-kpis');
  try{
    var r = await fetch('/api/portal/consumo', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    if(!d.hay_historia){
      kpis.innerHTML = '';
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">📊</span>'
        + '<div class="t">Todavía no hay historia para analizar</div>'
        + 'Con tu primer pedido empezamos a mostrarte qué pedís y cada cuánto.</div></div>';
      return;
    }
    kpis.innerHTML =
        '<div class="kpi"><div class="k">Pedidos</div><div class="v">' + d.pedidos + '</div></div>'
      + '<div class="kpi"><div class="k">Unidades</div><div class="v">'
      +   Number(d.unidades || 0).toLocaleString('es-CO') + '</div></div>'
      + '<div class="kpi"><div class="k">Producto</div><div class="v chico">'
      +   esc((d.productos && d.productos[0] ? d.productos[0].producto : '-')) + '</div></div>';
    var maxP = Math.max.apply(null, d.productos.map(function(p){ return p.unidades; }).concat([1]));
    var maxM = Math.max.apply(null, (d.meses || []).map(function(m){ return m.unidades; }).concat([1]));
    box.innerHTML = '<div class="card"><h2>Por producto</h2><div style="margin-top:14px">'
      + d.productos.map(function(p){
          return '<div class="barra"><div class="nm">' + esc(p.producto) + '</div>'
            + '<div class="tr"><div class="fl" style="width:' + Math.round(p.unidades * 100 / maxP) + '%"></div></div>'
            + '<div class="vl">' + Number(p.unidades).toLocaleString('es-CO') + ' uds</div></div>';
        }).join('')
      + '</div></div>'
      + (d.meses && d.meses.length
          ? '<div class="card"><h2>Por mes</h2><div style="margin-top:14px">'
            + d.meses.map(function(m){
                return '<div class="barra"><div class="nm">' + esc(fmtMes(m.mes)) + '</div>'
                  + '<div class="tr"><div class="fl" style="width:' + Math.round(m.unidades * 100 / maxM) + '%"></div></div>'
                  + '<div class="vl">' + Number(m.unidades).toLocaleString('es-CO') + ' uds</div></div>';
              }).join('')
            + '</div></div>'
          : '');
  }catch(e){ box.innerHTML = '<div class="vacio">No pudimos calcular tu consumo.</div>'; }
}
function pintarPedidos(){
  var box = $('lista-pedidos');
  if(!_PEDIDOS.length){
    box.innerHTML = '<div class="card"><div class="vacio"><span class="em">📋</span>'
      + '<div class="t">Todavía no nos pediste nada</div>'
      + 'Andá a <b>Pedir</b> y mandanos tu primera solicitud.</div></div>';
    return;
  }
  box.innerHTML = _PEDIDOS.map(function(p){ return tarjetaPedido(p, false, 'lis'); }).join('');
}

/* ── nuevo pedido ────────────────────────────────────────────────── */
function diasHasta(f){
  if(!f) return null;
  var hoy = new Date(); hoy.setHours(0,0,0,0);
  return Math.round((new Date(f + 'T12:00:00') - hoy) / 86400000);
}
function avisoFecha(){
  var box = $('sol-aviso'); if(!box) return;
  var d = diasHasta($('sol-fecha').value);
  box.className = 'aviso';
  if(d === null || d >= 30){ return; }
  if(d < 0){
    box.className = 'aviso grave on';
    box.textContent = 'Esa fecha ya pasó. Elegí una futura.';
  } else {
    box.className = 'aviso on';
    box.innerHTML = 'Pediste para dentro de ' + d + (d === 1 ? ' día' : ' días')
      + '. La producción necesita un mes de anticipación, así que al recibirla te confirmamos '
      + 'si llegamos o te proponemos otra fecha.';
  }
}
async function enviarPedido(){
  var btn = $('btn-enviar'), msg = $('sol-msg');
  msg.className = 'msg';
  var producto = $('sol-producto').value;
  var cant = parseInt($('sol-cant').value, 10);
  var ml = parseFloat($('sol-ml').value || '30');
  var fecha = $('sol-fecha').value;
  var urgencia = $('sol-urgencia').value;
  var notas = $('sol-notas').value.trim();
  if(!producto || !cant || cant <= 0){
    msg.className = 'msg err'; msg.textContent = 'Falta elegir el producto o la cantidad.'; return;
  }
  var d = diasHasta(fecha);
  if(d !== null && d < 0){
    msg.className = 'msg err'; msg.textContent = 'Esa fecha ya pasó. Elegí una futura.'; return;
  }
  if(d !== null && d < 30 && urgencia !== 'alta'){
    if(!confirm('Pediste para dentro de ' + d + ' días y lo ideal es un mes de anticipación. ¿Lo enviamos igual? Si es urgente, cancelá y marcá urgencia Alta.')) return;
  }
  btn.disabled = true; btn.textContent = 'Enviando...';
  try{
    var r = await fetch('/api/portal/pedidos', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify({
        producto_nombre: producto,
        cantidad_uds: cant,
        ml_unidad: ml,
        fecha_estimada: fecha,
        urgencia: urgencia,
        notas: notas,
        repetir_cada_dias: (parseInt(($('sol-repetir') || {}).value || '0', 10) || 0)
      })
    });
    var dd = await r.json();
    if(!r.ok){
      msg.className = 'msg err'; msg.textContent = dd.error || ('No se pudo enviar (' + r.status + ')');
      return;
    }
    msg.className = 'msg ok';
    msg.textContent = 'Listo, recibimos tu pedido #' + dd.id + '. Lo revisamos y te confirmamos la fecha.';
    $('sol-cant').value = ''; $('sol-fecha').value = ''; $('sol-notas').value = '';
    $('sol-urgencia').value = 'media'; $('sol-repetir').value = '0';
    $('sol-aviso').className = 'aviso';
    cargarPedidos(true);
  }catch(e){
    msg.className = 'msg err'; msg.textContent = 'No hay conexión con el servidor: ' + e.message;
  }finally{
    btn.disabled = false; btn.textContent = 'Enviar solicitud';
  }
}

/* ── editar pedido pendiente ─────────────────────────────────────── */
function abrirEditar(id){
  var p = _PEDIDOS.filter(function(x){ return x.id === id; })[0];
  if(!p) return;
  _EDITANDO = id;
  $('ed-prod').textContent = 'Pedido #' + id + ' · ' + nombreDe(p);
  $('ed-cant').value = p.cantidad_uds || '';
  $('ed-fecha').value = (p.fecha_estimada || '').slice(0, 10);
  $('ed-notas').value = p.notas || '';
  $('ed-msg').className = 'msg';
  $('ov-editar').classList.add('on');
}
function cerrarEditar(){ $('ov-editar').classList.remove('on'); _EDITANDO = 0; }
async function guardarEdicion(){
  if(!_EDITANDO) return;
  var btn = $('ed-btn'), msg = $('ed-msg');
  var cant = parseInt($('ed-cant').value, 10);
  if(!cant || cant <= 0){
    msg.className = 'msg err'; msg.textContent = 'La cantidad tiene que ser mayor a cero.'; return;
  }
  btn.disabled = true; btn.textContent = 'Guardando...';
  try{
    var r = await fetch('/api/portal/pedidos/' + _EDITANDO, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify({
        cantidad_uds: cant,
        fecha_estimada: $('ed-fecha').value,
        notas: $('ed-notas').value.trim()
      })
    });
    var d = await r.json();
    if(!r.ok){
      msg.className = 'msg err'; msg.textContent = d.error || 'No se pudo guardar';
      return;
    }
    cerrarEditar();
    cargarPedidos(true);
  }catch(e){
    msg.className = 'msg err'; msg.textContent = 'No hay conexión con el servidor';
  }finally{
    btn.disabled = false; btn.textContent = 'Guardar cambios';
  }
}

/* ── mensajes (PQR regulado + comercial, una sola entrada) ───────── */
function esPqr(t){ return _PQR_TIPOS.indexOf(t) >= 0; }
function msgTipoChange(){
  var t = $('msg-tipo').value;
  $('msg-box-prod').style.display = (t === 'nuevo_producto') ? 'block' : 'none';
  $('msg-box-fecha').style.display = (t === 'reunion') ? 'block' : 'none';
  $('msg-box-tit').style.display = esPqr(t) ? 'block' : (t === 'consulta' ? 'block' : 'block');
  $('msg-titulo-lbl').textContent = esPqr(t) ? 'Título corto' : 'Asunto';
  $('msg-texto-lbl').textContent = esPqr(t) ? 'Contanos qué pasó' : 'Contanos el detalle';
  var av = $('msg-aviso');
  if(esPqr(t)){
    av.className = 'aviso on';
    av.textContent = 'Esto queda registrado como PQR formal y le llega a Calidad. Te respondemos en máximo 5 días hábiles.';
  } else {
    av.className = 'aviso';
  }
}
async function enviarMensaje(){
  var t = $('msg-tipo').value;
  var titulo = $('msg-titulo').value.trim();
  var texto = $('msg-texto').value.trim();
  var btn = $('btn-msg'), out = $('msg-salida');
  out.className = 'msg';
  if(esPqr(t)){
    if(!titulo){ out.className = 'msg err'; out.textContent = 'Ponele un título corto.'; return; }
    if(texto.length < 10){ out.className = 'msg err'; out.textContent = 'Contanos un poco más (mínimo 10 caracteres).'; return; }
  } else {
    if(!texto){ out.className = 'msg err'; out.textContent = 'Escribinos el detalle.'; return; }
    if(t === 'nuevo_producto' && !$('msg-prod').value.trim()){
      out.className = 'msg err'; out.textContent = 'Decinos qué producto querés.'; return;
    }
  }
  btn.disabled = true; btn.textContent = 'Enviando...';
  try{
    var r, d;
    if(esPqr(t)){
      r = await fetch('/api/portal/pqr', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'same-origin',
        body: JSON.stringify({tipo: t, titulo: titulo, descripcion: texto})
      });
      d = await r.json();
      if(!r.ok){ out.className = 'msg err'; out.textContent = d.error || ('Error ' + r.status); return; }
      out.className = 'msg ok';
      out.textContent = 'Registramos tu ' + (_TIPO_LBL[t] || 'mensaje').toLowerCase() + ' #' + d.id + '. Te respondemos pronto.';
    } else {
      r = await fetch('/api/portal/solicitudes', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'same-origin',
        body: JSON.stringify({
          tipo: t,
          producto_nombre: $('msg-prod').value.trim(),
          mensaje: (titulo ? titulo + ' · ' : '') + texto,
          fecha_requerida: $('msg-fecha').value
        })
      });
      d = await r.json();
      if(!r.ok){ out.className = 'msg err'; out.textContent = d.error || ('Error ' + r.status); return; }
      out.className = 'msg ok';
      out.textContent = d.mensaje || 'Enviado. Te respondemos pronto.';
    }
    $('msg-titulo').value = ''; $('msg-texto').value = '';
    $('msg-prod').value = ''; $('msg-fecha').value = '';
    cargarHilos(true);
  }catch(e){
    out.className = 'msg err'; out.textContent = 'No hay conexión con el servidor';
  }finally{
    btn.disabled = false; btn.textContent = 'Enviar';
  }
}
async function cargarHilos(forzar){
  var box = $('lista-hilos');
  if(_HILOS_OK && !forzar) return;
  try{
    var res = await Promise.all([
      fetch('/api/portal/mis-pqr', {credentials:'same-origin'}),
      fetch('/api/portal/mis-solicitudes', {credentials:'same-origin'})
    ]);
    if(res[0].status === 401){ window.location.href = '/portal/login'; return; }
    var dp = await res[0].json(), ds = await res[1].json();
    var hilos = [];
    (dp.pqrs || []).forEach(function(p){
      hilos.push({
        fecha: (p.creado_at_utc || '').slice(0, 10),
        tipo: p.tipo, formal: true, titulo: p.titulo || (_TIPO_LBL[p.tipo] || 'PQR'),
        texto: p.descripcion || '', estado: p.estado || 'abierto',
        respuesta: p.respuesta_admin || '', quien: p.respondido_por || 'Espagiria'
      });
    });
    (ds.items || ds.solicitudes || []).forEach(function(s){
      // una reunión o una consulta no llevan producto: el backend guarda un
      // guión de relleno · un relleno NO es un dato (M193), así que se pregunta
      // si tiene letras o números, no si es igual a un carácter concreto.
      var pn = (s.producto_nombre || '').trim();
      var t = /[a-z0-9]/i.test(pn)
        ? (_TIPO_LBL[s.tipo] || s.tipo) + ' · ' + pn
        : (_TIPO_LBL[s.tipo] || s.tipo);
      hilos.push({
        fecha: (s.creada_at || '').slice(0, 10),
        tipo: s.tipo, formal: false, titulo: t,
        texto: s.mensaje || '', estado: s.estado || 'nueva',
        respuesta: s.respuesta_notas || '', quien: s.respondido_por || 'Espagiria'
      });
    });
    hilos.sort(function(a, b){ return (b.fecha || '').localeCompare(a.fecha || ''); });
    _HILOS_OK = true;
    if(!hilos.length){
      box.innerHTML = '<div class="card"><div class="vacio"><span class="em">💬</span>'
        + '<div class="t">Todavía no hay conversaciones</div>'
        + 'Escribinos con el formulario de arriba y acá vas a ver nuestra respuesta.</div></div>';
      return;
    }
    box.innerHTML = hilos.map(function(h){
      var cls = h.respuesta ? 'ok' : (h.formal ? 'info' : 'wait');
      return '<div class="hilo">'
        + '<div class="hilo-top"><div style="min-width:0">'
        +   '<div class="hilo-tit">' + esc(h.titulo) + '</div>'
        +   '<div class="chips" style="margin-top:6px">'
        +     '<span class="chip ' + cls + '">' + esc(estadoLbl(h.estado)) + '</span>'
        +     (h.formal ? '<span class="chip info">PQR formal</span>' : '')
        +   '</div>'
        + '</div><div class="hilo-fe">' + esc(fmtFecha(h.fecha)) + '</div></div>'
        + (h.texto ? '<div class="hilo-txt">' + esc(h.texto) + '</div>' : '')
        + (h.respuesta ? '<div class="resp"><b>Respuesta de ' + esc(h.quien) + '</b><br>' + esc(h.respuesta) + '</div>' : '')
        + '</div>';
    }).join('');
    actualizarPunto();
  }catch(e){
    box.innerHTML = '<div class="vacio">No pudimos traer las conversaciones. Revisá la conexión.</div>';
  }
}
async function actualizarPunto(){
  try{
    var d = await (await fetch('/api/portal/badge', {credentials:'same-origin'})).json();
    var b = $('bdg-mensajes');
    if(b){ b.textContent = d.total || ''; b.classList.toggle('on', (d.total || 0) > 0); }
  }catch(e){}
  // El número de la tarjeta de Pagos es lo que el cliente reportó y todavía
  // estamos revisando: sale de sus propios pagos, no de un contador aparte.
  try{
    var dp = await (await fetch('/api/portal/pagos', {credentials:'same-origin'})).json();
    var n = (dp.pagos || []).filter(function(p){ return p.estado === 'reportado'; }).length;
    var bp = $('bdg-pagos');
    if(bp){ bp.textContent = n || ''; bp.classList.toggle('on', n > 0); }
  }catch(e){}
}

/* ── arranque ────────────────────────────────────────────────────── */
async function arrancar(){
  try{
    var r = await fetch('/api/portal/productos', {credentials:'same-origin'});
    if(r.status === 401){ window.location.href = '/portal/login'; return; }
    var d = await r.json();
    $('saludo').textContent = d.cliente_nombre ? ('Hola, ' + d.cliente_nombre) : '';
    $('ini-saludo').textContent = d.cliente_nombre ? ('Hola, ' + d.cliente_nombre) : 'Hola';
    $('sol-producto').innerHTML = '<option value="">Elegí un producto</option>'
      + (d.productos || []).map(function(p){
          return '<option value="' + esc(p.nombre) + '">' + esc(p.mostrar || p.nombre) + '</option>';
        }).join('');
  }catch(e){
    $('sol-producto').innerHTML = '<option value="">No pudimos cargar el catálogo</option>';
  }
  var f = $('sol-fecha'); if(f) f.addEventListener('change', avisoFecha);
  var hoy = new Date(); hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
  var pf = $('pg-fecha'); if(pf) pf.value = hoy.toISOString().slice(0, 10);
  msgTipoChange();
  cargarPedidos();
  actualizarPunto();
}
arrancar();
</script>
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
    if ml > 5_000:
        ml = 5_000.0  # cap defensivo también para el ml derivado (consistente con el guard del input)

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
                      ultimo_login_ip, cliente_ref_id
               FROM portal_clientes_credenciales
               ORDER BY creado_at_utc DESC, id DESC""",
        ).fetchall()
        items = [{
            'id': r[0], 'cliente_id': r[1], 'cliente_nombre': r[2],
            'email': r[3], 'activo': bool(r[4]),
            'creado_por': r[5], 'creado_at_utc': r[6],
            'ultimo_login_at_utc': r[7], 'ultimo_login_ip': r[8],
            'cliente_ref_id': (r[9] if len(r) > 9 else None),
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
    # Aislamiento multi-cliente · cliente_id debe ser único entre credenciales ACTIVAS · toda la ownership
    # de pedidos/solicitudes se gatea por cliente_id (dos slugs iguales = un cliente vería pedidos del otro).
    dup_cid = c.execute(
        "SELECT id FROM portal_clientes_credenciales WHERE cliente_id = ? AND COALESCE(activo,1)=1",
        (cid,),
    ).fetchone()
    if dup_cid:
        return jsonify({'error': f'cliente_id "{cid}" ya está en uso (id={dup_cid[0]}) · usá otro ID'}), 409

    # ── El cliente tiene que quedar en la cola donde Luz mira quién necesita qué ──
    # 14-ago-2026 · dar el acceso NO lo dejaba en `clientes_b2b_maestro`, que es de
    # donde salen las secciones de "Necesidades por cliente". Consecuencia: el cliente
    # no aparecía hasta que pidiera algo, y si el identificador del portal no era el
    # mismo del maestro, al pedir salía DOS VECES (su fila en cero y otra sección con
    # los pedidos). Un alta que alguien tiene que acordarse de completar en otro lado
    # termina sin completarse (M189).
    #
    # Si ya existe una ficha con el MISMO nombre y es la única, se adopta SU id para
    # que el pedido caiga en esa fila. Si hay varias, no se elige: se crea la ficha
    # nueva y se declara la ambigüedad (M19).
    ficha = 'creada'
    ficha_aviso = ''
    try:
        ya = c.execute("SELECT cliente_id FROM clientes_b2b_maestro WHERE cliente_id = ?",
                       (cid,)).fetchone()
        if ya:
            ficha = 'reusada'
        else:
            objetivo = _norm_txt(cnom)
            candidatos = [r[0] for r in c.execute(
                "SELECT cliente_id, cliente_nombre FROM clientes_b2b_maestro "
                "WHERE COALESCE(activo,1)=1").fetchall() if _norm_txt(r[1]) == objetivo]
            libres = [x for x in candidatos if not c.execute(
                "SELECT 1 FROM portal_clientes_credenciales WHERE cliente_id=? "
                "AND COALESCE(activo,1)=1", (x,)).fetchone()]
            if len(libres) == 1:
                cid = libres[0]
                ficha = 'enlazada'
                ficha_aviso = 'Se enganchó a la ficha que ya existía con ese nombre.'
            elif len(candidatos) > 1:
                ficha_aviso = ('Hay más de una ficha con ese nombre · se creó una nueva '
                               'para no engancharlo al cliente equivocado.')
    except Exception as e:
        log.warning('cruce con el maestro de clientes B2B falló: %s', e)

    pw_hash = generate_password_hash(pw)
    c.execute(
        """INSERT INTO portal_clientes_credenciales
             (cliente_id, cliente_nombre, email, password_hash,
              activo, creado_por)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (cid, cnom, email, pw_hash, u),
    )
    new_id = c.lastrowid
    # La ficha se crea en la MISMA transacción que el acceso: si el acceso existe,
    # el cliente ya está en la cola de Necesidades, sin que nadie tenga que acordarse.
    if ficha == 'creada':
        try:
            c.execute(
                "INSERT INTO clientes_b2b_maestro (cliente_id, cliente_nombre, email, activo, tipo) "
                "SELECT ?, ?, ?, 1, 'B2B' WHERE NOT EXISTS "
                "(SELECT 1 FROM clientes_b2b_maestro WHERE cliente_id = ?)",
                (cid, cnom, email, cid))
        except Exception as e:
            # No se rompe el alta por esto · se declara en la respuesta (M4).
            log.warning('no se pudo crear la ficha del cliente %s: %s', cid, e)
            ficha = 'sin_ficha'
            ficha_aviso = ('El acceso quedó, pero el cliente no entró a la lista de '
                           'Necesidades · agregalo a mano en Clientes B2B.')
    audit_log(c, usuario=u, accion='PORTAL_CREAR_CREDENCIAL',
              tabla='portal_clientes_credenciales', registro_id=new_id,
              despues={'cliente_id': cid, 'email': email,
                       'cliente_nombre': cnom, 'ficha_cliente': ficha})
    conn.commit()
    return jsonify({
        'ok': True, 'id': new_id, 'cliente_id': cid, 'ficha_cliente': ficha,
        'aviso': ficha_aviso,
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
    # FIX · 13-ago-2026 · rediseño del portal · el catálogo (/api/portal/productos)
    # muestra el nombre GENÉRICO (mig 293) y esta lista mostraba el comercial de
    # ÁNIMUS: el cliente pedía "Niacinamida" y en sus pedidos leía otro nombre.
    # Dos pantallas del mismo portal nombrando distinto el mismo producto (M161).
    # `producto_nombre` NO se toca (es el valor real con el que se produce).
    _gen = {}
    try:
        for _gr in conn.execute(
            """SELECT producto_nombre, COALESCE(MAX(nombre_generico),'')
               FROM formula_headers
               WHERE COALESCE(activo,1) = 1
               GROUP BY producto_nombre""",
        ).fetchall():
            _g = (_gr[1] or '').strip()
            if _g:
                _gen[(_gr[0] or '').strip().upper()] = _g
    except Exception as _e:
        # mig 293 no aplicada · cae al nombre real (nunca deja la lista sin nombre)
        log.warning('mapa de nombres genéricos del portal falló: %s', _e)
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
        # Fecha que el CLIENTE ve como su lead time · sale del lote YA ASIGNADO (fecha_programada + 7d de
        # pipeline producción→disponible) · solo aparece cuando ya hicimos el match (post-confirmar) ·
        # Sebastián 27-jun: privado el calendario interno, pero "apenas se les asigna fecha, que les aparezca".
        _lote_r = lotes_pre.get(pid)
        fecha_lista = ''
        if _lote_r and _lote_r[6]:
            try:
                from datetime import datetime as _dtl, timedelta as _tdl
                fecha_lista = (_dtl.fromisoformat(str(_lote_r[6])[:10]) + _tdl(days=7)).date().isoformat()
            except Exception:
                fecha_lista = str(_lote_r[6])[:10]
        out.append({
            'id': pid,
            'producto_nombre': r[1] or '',
            'producto_mostrar': _gen.get((r[1] or '').strip().upper(), '') or (r[1] or ''),
            'cantidad_uds': uds,
            'ml_unidad': ml,
            'kg_equivalente': round(uds * ml / 1000.0, 2),
            'fecha_estimada': r[4] or '',
            'fecha_lista': fecha_lista,
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
                link='/admin/portal-mensajes',
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
    u, err = _require_pqr()
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
    u, err = _require_pqr()
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

@bp.route('/admin/portal-clientes', methods=['GET'])
def admin_clientes_b2b_pagina():
    """Panel admin para crear/gestionar clientes del portal B2B (Sebastián 26-jun).
    Reusa /api/admin/portal/credenciales (crear/listar/resetear-clave/activar).

    ⚠ 14-ago-2026 · esta página vivía en `/admin/clientes-b2b`, la MISMA ruta que
    el dashboard de clientes de `plan.py`. Flask se queda con la que registra el
    blueprint que entra primero (plan antes que portal · index.py), así que este
    panel estaba MUERTO: se podía crear la credencial por API, pero la pantalla
    para hacerlo no abría nunca (M97). URL propia y enlazada desde la que sí se
    sirve."""
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/portal-clientes')
    if session.get('compras_user', '') not in ADMIN_USERS:
        return ("<html><body style='font-family:system-ui;padding:48px'><h2>Solo admin</h2></body></html>"), 403
    return Response(_CLIENTES_B2B_HTML, mimetype='text/html')


_CLIENTES_B2B_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clientes B2B · EOS</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--cx-primary-pale, #f5f3ff);color:#1e1b4b;padding:24px}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:24px;color:var(--cx-primary-text, #5b21b6);margin-bottom:4px}.sub{color:var(--cx-text-mute, #64748b);font-size:13px;margin-bottom:20px}
.card{background:var(--cx-card, #fff);border:1px solid #e9d5ff;border-radius:14px;padding:18px;margin-bottom:18px;box-shadow:0 2px 10px rgba(109,40,217,.05)}
.card h2{font-size:15px;color:var(--cx-primary-text, #6d28d9);margin-bottom:12px}
label{display:block;font-size:12px;font-weight:600;color:var(--cx-text-soft, #475569);margin:8px 0 3px}
input{width:100%;padding:9px 11px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px;font-size:14px}
.row{display:flex;gap:10px;flex-wrap:wrap}.row>div{flex:1;min-width:180px}
button{border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer}
.primary{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff}
.ghost{background:var(--cx-card, #fff);border:1px solid var(--cx-primary-light, #c4b5fd);color:var(--cx-primary-text, #6d28d9)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px;color:var(--cx-primary-text, #5b21b6);border-bottom:2px solid #e9d5ff}td{padding:8px;border-bottom:1px solid var(--cx-border-soft, #f1f5f9)}
.acceso{background:#ecfdf5;border:1px solid #6ee7b7;border-radius:10px;padding:14px;margin-top:12px;font-size:13px;display:none}
.acceso pre{background:var(--cx-card, #fff);border:1px solid #d1fae5;border-radius:8px;padding:10px;margin:8px 0;white-space:pre-wrap;font-family:monospace;font-size:12px}
.chip{padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700}.on{background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #15803d)}.off{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b)}
</style></head><body><div class="wrap">
<h1>👥 Clientes B2B</h1>
<div class="sub">Creá clientes del portal, copiales el acceso y gestioná sus claves. Entran por <b>/portal/login</b>.</div>
<div class="sub" style="margin-bottom:14px"><a href="/admin/portal-pagos" style="font-weight:700">Pagos que reportaron los clientes y enlace con facturación &rarr;</a></div>
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
<tbody id="cli-tbody"><tr><td colspan="5" style="color:var(--cx-text-faint, #94a3b8);padding:14px">Cargando&hellip;</td></tr></tbody></table></div></div>
<div class="card"><h2>🛒 Catálogo B2B · nombres genéricos</h2>
<div class="sub" style="margin-bottom:10px">El cliente ve el <b>nombre genérico</b> (ej. "Niacinamida", "Limpiador BHA") en vez del comercial de Ánimus. Vacío = ve el comercial. <i>Interino mientras cargás los productos propios.</i></div>
<div style="overflow-x:auto"><table><thead><tr><th>Producto (real · Ánimus)</th><th>Nombre genérico que ve el cliente</th><th></th></tr></thead>
<tbody id="cat-tbody"><tr><td colspan="3" style="color:var(--cx-text-faint, #94a3b8);padding:14px">Cargando&hellip;</td></tr></tbody></table></div></div>
</div><script>
var BASE=location.origin, _CSRF='';
fetch('/api/csrf-token',{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(t){_CSRF=t.csrf_token||'';}).catch(function(){});
function _hdr(){ return {'Content-Type':'application/json','X-CSRF-Token':_CSRF}; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
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
    if(!items.length){ tb.innerHTML='<tr><td colspan="5" style="color:var(--cx-text-faint, #94a3b8);padding:14px">Sin clientes todav\\u00eda \\u00b7 cre\\u00e1 el primero arriba.</td></tr>'; return; }
    tb.innerHTML=items.map(function(c){
      var est=c.activo?'<span class="chip on">activo</span>':'<span class="chip off">inactivo</span>';
      var ult=c.ultimo_login_at_utc?esc(String(c.ultimo_login_at_utc).slice(0,16).replace('T',' ')):'<span style="color:var(--cx-border, #cbd5e1)">nunca</span>';
      var tog=c.activo?('<button class="ghost" onclick="toggleActivo('+c.id+',false)">🚫 Desactivar</button>'):('<button class="ghost" onclick="toggleActivo('+c.id+',true)">✓ Activar</button>');
      return '<tr><td><b>'+esc(c.cliente_nombre)+'</b><br><span style="font-size:10px;color:var(--cx-text-faint, #94a3b8)">'+esc(c.cliente_id)+'</span></td><td>'+esc(c.email)+'</td><td>'+est+'</td><td style="font-size:12px">'+ult+'</td><td style="white-space:nowrap"><button class="ghost" onclick="resetClave('+c.id+',&#39;'+esc(c.email)+'&#39;)">🔄 Clave</button> '+tog+'</td></tr>';
    }).join('');
  }catch(e){ tb.innerHTML='<tr><td colspan="5" style="color:var(--cx-danger-text, #dc2626)">Error cargando</td></tr>'; }
}
var _CAT=[];
async function cargarCatalogo(){
  var tb=document.getElementById('cat-tbody');
  try{
    var d=await (await fetch('/api/admin/portal/catalogo',{credentials:'same-origin'})).json();
    _CAT=d.items||[];
    if(!_CAT.length){ tb.innerHTML='<tr><td colspan="3" style="color:var(--cx-text-faint, #94a3b8);padding:14px">Sin productos.</td></tr>'; return; }
    tb.innerHTML=_CAT.map(function(it,i){
      return '<tr><td style="font-size:12px">'+esc(it.producto)+'</td><td><input id="gen-'+i+'" value="'+esc(it.generico)+'" placeholder="(gen\\u00e9rico)" style="width:100%"></td><td><button class="ghost" onclick="setGenerico('+i+')">Guardar</button></td></tr>';
    }).join('');
  }catch(e){ tb.innerHTML='<tr><td colspan="3" style="color:var(--cx-danger-text, #dc2626)">Error</td></tr>'; }
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
       min-height:100vh;padding:48px 16px;color:var(--cx-border, #e2e8f0)}
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
  .sub{color:var(--cx-text-faint, #94a3b8);font-size:13px;margin-bottom:22px;margin-top:4px}
  .step{margin-bottom:18px}
  .step-num{display:inline-block;background:linear-gradient(135deg,#a78bfa,#6d28d9);
            color:#fff;width:26px;height:26px;border-radius:13px;text-align:center;
            font-weight:800;font-size:13px;line-height:26px;margin-right:8px;
            box-shadow:0 4px 12px rgba(109,40,217,.35)}
  .step-titulo{font-weight:700;font-size:14px;display:inline-block;color:var(--cx-border, #e2e8f0)}
  .step-body{margin-top:6px;margin-left:34px;font-size:13px;color:var(--cx-text-faint, #94a3b8)}
  .btn{background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border:none;
       padding:13px 22px;border-radius:10px;font-size:14px;font-weight:700;
       cursor:pointer;margin:8px 0;letter-spacing:.3px;transition:.15s;font-family:inherit}
  .btn:hover{transform:translateY(-1px);box-shadow:0 10px 24px rgba(109,40,217,.45)}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-link{display:inline-block;background:rgba(167,139,250,.18);color:var(--cx-primary-light, #c4b5fd);
            padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;
            font-size:13px;margin-top:6px;border:1px solid rgba(167,139,250,.3);
            transition:.15s}
  .btn-link:hover{background:rgba(167,139,250,.28);color:#fff}
  .cred-box{background:rgba(15,23,42,0.7);border:2px solid rgba(167,139,250,.35);
            border-radius:12px;padding:18px;margin:14px 0;
            box-shadow:inset 0 2px 8px rgba(0,0,0,.2)}
  .cred-label{font-size:10px;color:var(--cx-primary-light, #a78bfa);text-transform:uppercase;font-weight:700;
              letter-spacing:1px;margin-bottom:4px}
  .cred-value{font-family:'SF Mono',Consolas,monospace;font-size:16px;font-weight:700;
              color:var(--cx-primary-light, #c4b5fd);background:rgba(167,139,250,.08);padding:8px 12px;
              border-radius:7px;border:1px solid rgba(167,139,250,.2);display:inline-block;
              user-select:all;cursor:pointer;transition:.15s}
  .cred-value:hover{background:rgba(167,139,250,.16);color:var(--cx-border, #e2e8f0)}
  .copy-hint{font-size:11px;color:var(--cx-text-mute, #64748b);margin-left:8px}
  .nota{font-size:12px;color:#fcd34d;background:rgba(202,138,4,.12);
        border-left:3px solid var(--cx-warn, #f59e0b);padding:10px 14px;border-radius:7px;margin-top:14px}
  .ok-msg{color:#86efac;font-weight:700;margin-top:8px;
          background:rgba(22,163,74,.12);padding:8px 12px;border-radius:7px;
          border-left:3px solid var(--cx-success, #16a34a)}
  .err-msg{color:#fca5a5;font-weight:700;margin-top:8px;
           background:rgba(220,38,38,.12);padding:8px 12px;border-radius:7px;
           border-left:3px solid var(--cx-danger, #dc2626)}
  .app-footer{text-align:center;font-size:10px;color:var(--cx-text-soft, #475569);letter-spacing:.5px;
              margin-top:24px;line-height:1.6}
  .app-footer strong{color:var(--cx-text-faint, #94a3b8)}
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
    # Comunicación · enrutado 27-jun (Sebastián): lo "nuevo" (producto nuevo / reunión / consulta) NO va a
    # Compras (Catalina) sino a ESPAGIRIA · asistente de gerencia (luz) + al CEO (sebastian) por su módulo.
    # (A futuro estas solicitudes alimentan el módulo de Investigación y Desarrollo.)
    try:
        from blueprints.notif import push_notif as _pn
        _lbl = {'nuevo_producto': '🆕 Nuevo producto', 'reunion': '📅 Reunión con gerencia',
                'consulta': '💬 Consulta', 'cotizacion': '💰 Cotización', 'muestras': '🧪 Muestras',
                'ficha_tecnica': '📄 Ficha técnica'}.get(tipo, tipo)
        _body = ((producto + ' · ') if (producto and producto != '—') else '') + (mensaje[:140] or 'sin detalle')
        for _d in ('luz', 'sebastian'):
            _pn(destinatario=_d, tipo='portal_solicitud_nueva',
                titulo=f'{_lbl} · {cnom}', body=_body,
                link='/admin/portal-mensajes', remitente=f'portal:{email}', importante=True)
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
    """14-ago-2026 · la bandeja de solicitudes se fundió con la de PQR en
    /admin/portal-mensajes (el cliente escribe desde un solo lugar, se lee desde uno
    solo). La ruta se conserva REDIRIGIENDO porque está enlazada en avisos viejos y
    en marcadores: una URL enlazada que empieza a dar 404 no explica nada (M120)."""
    return redirect('/admin/portal-mensajes')


@bp.route('/admin/portal-rfq-old', methods=['GET'])
def admin_portal_rfq_pagina_vieja():
    """La bandeja VIEJA de solicitudes · queda accesible por si hay que comparar.

    Se le dio URL propia en vez de dejarla como función sin llamador: una función que
    nadie puede ejecutar se ve viva en el código y no existe para nadie (M112)."""
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
       background:var(--cx-border-soft, #f1f5f9);margin:0;padding:0;color:var(--cx-text, #0f172a)}
  header{background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;
         padding:18px 24px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
  header h1{margin:0;font-size:20px}
  header .sub{font-size:13px;opacity:.85;margin-top:2px}
  .top-bar{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}
  .container{max-width:1400px;margin:18px auto;padding:0 18px}
  .filtros{background:var(--cx-card, #fff);padding:14px 18px;border-radius:10px;
           box-shadow:0 2px 8px rgba(0,0,0,.04);display:flex;
           gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
  .filtros label{font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600}
  .filtros select{padding:6px 10px;border:1px solid var(--cx-border, #cbd5e1);
                  border-radius:6px;font-size:13px;background:var(--cx-card, #fff)}
  .filtros .stats{margin-left:auto;font-size:12px;color:var(--cx-text-mute, #64748b)}
  .stats b{color:var(--cx-info-text, #0f766e)}
  .lista{background:var(--cx-card, #fff);border-radius:10px;
         box-shadow:0 2px 8px rgba(0,0,0,.04);overflow:hidden}
  .item{padding:14px 18px;border-bottom:1px solid var(--cx-border, #e2e8f0);
        display:grid;grid-template-columns:80px 1fr 140px 130px 110px 130px;
        gap:12px;align-items:center;cursor:pointer;transition:background .15s}
  .item:hover{background:var(--cx-success-pale, #f0fdf4)}
  .item:last-child{border-bottom:none}
  .item .id{font-family:monospace;color:var(--cx-text-mute, #64748b);font-size:13px;font-weight:700}
  .item .producto{font-weight:600;color:var(--cx-text, #0f172a)}
  .item .producto .meta{font-size:11px;color:var(--cx-text-mute, #64748b);font-weight:400;margin-top:2px}
  .item .cliente{font-size:13px;color:var(--cx-text-soft, #334155)}
  .item .cliente .email{font-size:11px;color:var(--cx-text-faint, #94a3b8)}
  .item .tipo{font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.5px}
  .item .tipo.cotizacion{color:var(--cx-info-text, #0891b2)}
  .item .tipo.muestras{color:#9333ea}
  .item .tipo.ficha_tecnica{color:#ea580c}
  .badge{display:inline-block;padding:3px 10px;border-radius:12px;
         font-size:11px;font-weight:700;text-transform:uppercase}
  .b-nueva{background:var(--cx-warn-pale, #fef3c7);color:var(--cx-warn-text, #92400e)}
  .b-en_revision{background:var(--cx-info-pale, #dbeafe);color:var(--cx-info-text, #1e40af)}
  .b-respondida{background:var(--cx-success-pale, #d1fae5);color:var(--cx-success-text, #065f46)}
  .b-convertida{background:#a7f3d0;color:#064e3b}
  .b-cerrada{background:var(--cx-border, #e2e8f0);color:var(--cx-text-soft, #475569)}
  .b-rechazada{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b)}
  .fecha{font-size:11px;color:var(--cx-text-mute, #64748b)}
  .empty{padding:48px;text-align:center;color:var(--cx-text-faint, #94a3b8)}
  .empty-ic{font-size:48px;margin-bottom:8px}
  /* Modal */
  .modal-bg{position:fixed;inset:0;background:rgba(15,23,42,.55);
            display:none;align-items:flex-start;justify-content:center;
            z-index:1000;overflow-y:auto;padding:24px 14px}
  .modal-bg.open{display:flex}
  .modal{background:var(--cx-card, #fff);border-radius:14px;max-width:680px;width:100%;
         padding:24px 28px;box-shadow:0 20px 50px rgba(0,0,0,.3);margin:auto}
  .modal h2{margin:0 0 4px;color:var(--cx-text, #0f172a);font-size:18px}
  .modal .sub{font-size:12px;color:var(--cx-text-mute, #64748b);margin-bottom:18px}
  .modal .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px}
  .modal .field{display:flex;flex-direction:column;gap:4px}
  .modal label{font-size:11px;color:var(--cx-text-soft, #475569);font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .modal input,.modal textarea,.modal select{
    padding:9px 11px;border:1px solid var(--cx-border, #cbd5e1);border-radius:7px;
    font-size:13px;font-family:inherit;color:var(--cx-text, #0f172a)}
  .modal input:focus,.modal textarea:focus{outline:none;border-color:var(--cx-info, #0891b2);box-shadow:0 0 0 3px rgba(8,145,178,.15)}
  .modal textarea{resize:vertical;min-height:70px}
  .modal .full{grid-column:1/-1}
  .modal .info-box{background:var(--cx-bg-alt, #f8fafc);border-left:3px solid var(--cx-info, #0891b2);
                    padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px}
  .modal .info-box b{color:var(--cx-text, #0f172a)}
  .modal .actions{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}
  .btn{padding:10px 18px;border:none;border-radius:7px;font-weight:700;font-size:13px;cursor:pointer;transition:all .15s}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-primary{background:var(--cx-info, #0891b2);color:#fff}
  .btn-primary:hover:not(:disabled){background:var(--cx-info, #0e7490)}
  .btn-secondary{background:var(--cx-border, #e2e8f0);color:var(--cx-text-soft, #475569)}
  .btn-secondary:hover{background:var(--cx-border, #cbd5e1)}
  .btn-danger{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b)}
  .btn-danger:hover{background:var(--cx-danger-pale, #fecaca)}
  .msg{padding:10px 14px;border-radius:7px;margin-top:14px;font-size:13px;display:none}
  .msg.ok{background:var(--cx-success-pale, #d1fae5);color:var(--cx-success-text, #065f46);display:block}
  .msg.err{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b);display:block}
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

# ══════════════════════════════════════════════════════════════════════
# FASE 3 · La plata y los papeles del cliente (Sebastián 14-ago-2026)
#
#   "piensa qué necesitan tener ellos en su módulo: facturas, pagos que
#    los carguen, análisis"
#
# Regla que ordena todo este bloque: lo que el cliente ve sale de un HECHO
# registrado, y lo que no se puede resolver se DECLARA. Una lista vacía se
# lee como "no tengo nada", y eso es lo contrario de "no se pudo cruzar".
# ══════════════════════════════════════════════════════════════════════

_PORTAL_DOC_MAX_BYTES = 8 * 1024 * 1024          # 8 MB · un comprobante no pesa más
_PORTAL_DOC_EXT = {'pdf': 'application/pdf', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                   'png': 'image/png', 'webp': 'image/webp'}


def _hoy_col_iso():
    """Hoy en Colombia (M24) · nunca `date('now')` en DML."""
    from datetime import datetime as _d, timedelta as _t
    return (_d.utcnow() - _t(hours=5)).date().isoformat()


def _ahora_col_iso():
    from datetime import datetime as _d, timedelta as _t
    return (_d.utcnow() - _t(hours=5)).replace(microsecond=0).isoformat(' ')


def _norm_txt(v):
    """Normalización fuerte para comparar nombres (M13): sin acentos ni puntuación."""
    import re as _re, unicodedata as _ud
    v = _ud.normalize('NFKD', str(v or '')).encode('ascii', 'ignore').decode('ascii')
    return _re.sub(r'[^A-Z0-9]+', ' ', v.upper()).strip()


def _cliente_ref(conn, cid, cnom):
    """Resuelve la cuenta de FACTURACIÓN (`clientes.id`) del cliente del portal.

    La credencial guarda un `cliente_id` de TEXTO (un slug) y `facturas` apunta a
    `clientes.id` (INTEGER): sin este puente el módulo de Facturas nace vacío.

    Tiers, del dato más DECLARADO al más inferido, y sin adivinar nunca:
      1. `cliente_ref_id` de la credencial · lo fijó una persona (mig 430)
      2. `clientes.codigo` igual al slug
      3. nombre normalizado, y SÓLO si hay UNA coincidencia (dos clientes que
         normalizan igual no se eligen a dedo · M19)

    Devuelve `(id|None, como)`. El `como` viaja hasta la pantalla: quien ve sus
    facturas tiene que poder saber por qué las ve, y quien no las ve, por qué no.
    """
    try:
        row = conn.execute(
            "SELECT cliente_ref_id FROM portal_clientes_credenciales "
            "WHERE cliente_id=? AND COALESCE(activo,1)=1 LIMIT 1", (cid,)).fetchone()
        if row and row[0]:
            return int(row[0]), 'enlace_declarado'
    except Exception as e:
        # mig 430 sin aplicar · se sigue con los tiers de abajo (M4: se dice, no se traga)
        log.warning('cliente_ref_id no disponible: %s', e)
    try:
        row = conn.execute(
            "SELECT id FROM clientes WHERE UPPER(TRIM(COALESCE(codigo,''))) = ? "
            "AND COALESCE(activo,1)=1", ((cid or '').strip().upper(),)).fetchall()
        if len(row) == 1:
            return int(row[0][0]), 'codigo'
    except Exception as e:
        log.warning('cruce por codigo de cliente falló: %s', e)
    try:
        objetivo = _norm_txt(cnom)
        if objetivo:
            cands = [r for r in conn.execute(
                "SELECT id, nombre FROM clientes WHERE COALESCE(activo,1)=1").fetchall()
                if _norm_txt(r[1]) == objetivo]
            if len(cands) == 1:
                return int(cands[0][0]), 'nombre'
            if len(cands) > 1:
                return None, 'nombre_ambiguo'
    except Exception as e:
        log.warning('cruce por nombre de cliente falló: %s', e)
    return None, 'sin_cuenta'


_MOTIVO_SIN_ENLACE = {
    'sin_cuenta': ('Todavía no tenemos tu portal enlazado con tu cuenta de facturación. '
                   'Escribinos por Mensajes y lo dejamos listo.'),
    'nombre_ambiguo': ('Hay más de una cuenta con tu mismo nombre y no queremos mostrarte '
                       'la equivocada. Escribinos por Mensajes y lo resolvemos.'),
}


@bp.route('/api/portal/facturas', methods=['GET'])
def portal_facturas():
    """Las facturas del cliente logueado, con lo pagado y el saldo real.

    El saldo sale de `facturas_pagos` (los cobros REGISTRADOS), no de un campo aparte:
    el número que se muestra es el mismo con el que se decide (M5).
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, _email = auth
    conn = get_db()
    ref, como = _cliente_ref(conn, cid, cnom)
    if not ref:
        return jsonify({'enlazado': False, 'motivo': como,
                        'mensaje': _MOTIVO_SIN_ENLACE.get(como, _MOTIVO_SIN_ENLACE['sin_cuenta']),
                        'facturas': [], 'total': 0})
    try:
        rows = conn.execute(
            """SELECT numero, tipo, fecha_emision, COALESCE(fecha_vencimiento,''),
                      COALESCE(total,0), COALESCE(estado,''), COALESCE(numero_pedido,''),
                      COALESCE(empresa,'')
                 FROM facturas
                WHERE cliente_id = ?
                ORDER BY fecha_emision DESC, id DESC
                LIMIT 200""", (ref,)).fetchall()
    except Exception as e:
        log.warning('facturas del portal fallaron: %s', e)
        return jsonify({'enlazado': True, 'error_lectura': True, 'facturas': [], 'total': 0}), 200
    pagado = {}
    if rows:
        marcas = ','.join('?' * len(rows))
        try:
            for pr in conn.execute(
                "SELECT numero_factura, COALESCE(SUM(monto),0) FROM facturas_pagos "
                "WHERE numero_factura IN (%s) GROUP BY numero_factura" % marcas,
                    [r[0] for r in rows]).fetchall():
                pagado[pr[0]] = float(pr[1] or 0)
        except Exception as e:
            log.warning('pagos de facturas del portal fallaron: %s', e)
    hoy = _hoy_col_iso()
    out, saldo_total, vencido_total = [], 0.0, 0.0
    for r in rows:
        numero, tipo, emision, vence, total, estado, pedido, empresa = r
        pag = pagado.get(numero, 0.0)
        saldo = round(float(total or 0) - pag, 2)
        anulada = (estado or '').lower() == 'anulada'
        vencida = (not anulada) and saldo > 0.01 and vence and vence[:10] < hoy
        if not anulada:
            saldo_total += max(saldo, 0)
            if vencida:
                vencido_total += max(saldo, 0)
        out.append({
            'numero': numero, 'tipo': tipo or 'Factura', 'fecha_emision': (emision or '')[:10],
            'fecha_vencimiento': (vence or '')[:10], 'total': round(float(total or 0), 2),
            'pagado': round(pag, 2), 'saldo': saldo, 'estado': estado or 'Emitida',
            'vencida': bool(vencida), 'numero_pedido': pedido, 'empresa': empresa,
        })
    return jsonify({
        'enlazado': True, 'como': como, 'facturas': out, 'total': len(out),
        'saldo_total': round(saldo_total, 2), 'vencido_total': round(vencido_total, 2),
    })


@bp.route('/portal/factura/<numero>.pdf', methods=['GET'])
def portal_factura_pdf(numero):
    """La factura del cliente en PDF · es el MISMO documento que emite Contabilidad.

    Gateado por PROPIEDAD: la factura tiene que estar a nombre de la cuenta enlazada
    a este portal. Se delega en `_generar_pdf_bytes` en vez de armar otro PDF: dos
    generadores del mismo documento divergen el día que se toque uno (M3).
    """
    auth = _require_portal_login()
    if not auth:
        return redirect('/portal/login')
    cid, cnom, _email = auth
    numero = (numero or '').strip()
    conn = get_db()
    ref, _como = _cliente_ref(conn, cid, cnom)
    if not ref:
        return Response('Todavía no tenemos tu portal enlazado con tu facturación',
                        status=403, mimetype='text/plain')
    fila = conn.execute("SELECT * FROM facturas WHERE numero=? AND cliente_id=?",
                        (numero, ref)).fetchone()
    if not fila:
        return Response('Esa factura no figura a tu nombre', status=403, mimetype='text/plain')
    try:
        items = [dict(r) for r in conn.execute(
            "SELECT * FROM facturas_items WHERE numero_factura=?", (numero,)).fetchall()]
        from blueprints.contabilidad import _generar_pdf_bytes
        pdf = _generar_pdf_bytes(dict(fila), items)
    except Exception as e:
        # Se dice que no se pudo · un 500 mudo se lee como "el botón no sirve" (M154).
        log.warning('PDF de la factura %s no se pudo generar: %s', numero, e)
        return Response('El PDF no está disponible en este momento. Escribinos por Mensajes '
                        'y te lo mandamos.', status=503, mimetype='text/plain')
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': 'inline; filename="%s.pdf"' % numero})


@bp.route('/api/portal/pagos', methods=['GET', 'POST'])
def portal_pagos():
    """GET · los pagos que el cliente reportó y en qué estado quedaron.
       POST · el cliente avisa un pago y sube el comprobante (multipart).

    Un pago reportado NO es un asiento: entra a la contabilidad sólo cuando alguien
    lo concilia por el camino canónico. El estado del dinero se deriva de un hecho de
    dinero, nunca de que el cliente diga que pagó (M168).
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, email = auth
    conn = get_db()

    if request.method == 'GET':
        try:
            rows = conn.execute(
                """SELECT id, COALESCE(factura_numero,''), COALESCE(monto,0),
                          COALESCE(fecha_pago,''), COALESCE(metodo,''), COALESCE(referencia,''),
                          COALESCE(estado,'reportado'), COALESCE(motivo,''),
                          COALESCE(archivo_estado,''), COALESCE(archivo_nombre,''),
                          COALESCE(creado_at,'')
                     FROM portal_pagos_reportados
                    WHERE cliente_id = ?
                    ORDER BY id DESC LIMIT 100""", (cid,)).fetchall()
        except Exception as e:
            log.warning('lista de pagos del portal falló: %s', e)
            rows = []
        return jsonify({'pagos': [{
            'id': r[0], 'factura_numero': r[1], 'monto': round(float(r[2] or 0), 2),
            'fecha_pago': r[3][:10], 'metodo': r[4], 'referencia': r[5], 'estado': r[6],
            'motivo': r[7], 'archivo_estado': r[8], 'archivo_nombre': r[9],
            'creado_at': (r[10] or '')[:10],
        } for r in rows], 'total': len(rows)})

    # ── POST · reportar un pago ──────────────────────────────────────
    f = request.form
    try:
        monto = float((f.get('monto') or '0').replace(',', '.'))
    except (TypeError, ValueError):
        return jsonify({'error': 'El monto no es un número'}), 400
    if monto <= 0:
        return jsonify({'error': 'El monto tiene que ser mayor a cero'}), 400
    factura = (f.get('factura_numero') or '').strip()
    fecha = (f.get('fecha_pago') or '').strip()[:10] or _hoy_col_iso()
    if fecha > _hoy_col_iso():
        return jsonify({'error': 'La fecha del pago no puede ser futura'}), 400
    metodo = (f.get('metodo') or 'Transferencia').strip()[:40]
    referencia = (f.get('referencia') or '').strip()[:120]
    nota = (f.get('nota') or '').strip()[:500]

    ref_id, _como = _cliente_ref(conn, cid, cnom)
    # La factura, si la eligió, tiene que ser SUYA · si no, no se ata a nada y se
    # reporta igual (perder el aviso sería peor que no poder atarlo).
    if factura and ref_id:
        propia = conn.execute(
            "SELECT 1 FROM facturas WHERE numero=? AND cliente_id=?", (factura, ref_id)).fetchone()
        if not propia:
            return jsonify({'error': 'Esa factura no figura a tu nombre'}), 403

    # Anti doble reporte (M63: el CAS protege transiciones, no la creación).
    dup = conn.execute(
        """SELECT id FROM portal_pagos_reportados
            WHERE cliente_id=? AND COALESCE(factura_numero,'')=? AND ROUND(monto,2)=ROUND(?,2)
              AND COALESCE(fecha_pago,'')=? AND estado='reportado'""",
        (cid, factura, monto, fecha)).fetchone()
    if dup:
        return jsonify({'ok': True, 'duplicado': True, 'id': dup[0],
                        'mensaje': 'Ese pago ya lo habíamos recibido, lo estamos revisando.'}), 200

    # ── comprobante ──────────────────────────────────────────────────
    archivo = request.files.get('archivo')
    a_key = a_nombre = a_sha = ''
    a_bytes = 0
    a_estado = 'sin_archivo'
    if archivo and (archivo.filename or '').strip():
        import hashlib as _hl
        a_nombre = (archivo.filename or '')[-120:]
        ext = a_nombre.rsplit('.', 1)[-1].lower() if '.' in a_nombre else ''
        if ext not in _PORTAL_DOC_EXT:
            return jsonify({'error': 'El comprobante tiene que ser PDF o imagen (jpg, png, webp)'}), 400
        datos = archivo.read()
        a_bytes = len(datos or b'')
        if a_bytes == 0:
            return jsonify({'error': 'El archivo llegó vacío'}), 400
        if a_bytes > _PORTAL_DOC_MAX_BYTES:
            return jsonify({'error': 'El comprobante pesa más de 8 MB'}), 413
        a_sha = _hl.sha256(datos).hexdigest()
        try:
            from r2_storage import r2_put, r2_configurado
            if r2_configurado():
                # Key determinista por contenido: volver a subir el mismo archivo no
                # crea una copia nueva.
                a_key = 'portal-pagos/%s/%s.%s' % (_norm_txt(cid).replace(' ', '-').lower() or 'cliente',
                                                    a_sha[:24], ext)
                a_estado = 'guardado' if r2_put(a_key, datos, _PORTAL_DOC_EXT[ext]) else 'fallo_guardado'
                if a_estado != 'guardado':
                    a_key = ''
            else:
                a_estado = 'sin_almacenamiento'
        except Exception as e:
            log.warning('comprobante de pago no se pudo guardar: %s', e)
            a_estado = 'fallo_guardado'
            a_key = ''

    cur = conn.cursor()
    cur.execute(
        """INSERT INTO portal_pagos_reportados
           (cliente_id, cliente_nombre, cliente_ref_id, factura_numero, monto, fecha_pago,
            metodo, referencia, nota, archivo_key, archivo_nombre, archivo_bytes,
            archivo_sha256, archivo_estado, estado, creado_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'reportado',?)""",
        (cid, cnom, ref_id, factura, monto, fecha, metodo, referencia, nota,
         a_key, a_nombre, a_bytes, a_sha, a_estado, _ahora_col_iso()))
    nuevo_id = cur.lastrowid
    audit_log(cur, usuario='portal:%s' % email, accion='PORTAL_REPORTA_PAGO',
              tabla='portal_pagos_reportados', registro_id=nuevo_id,
              despues={'cliente': cid, 'factura': factura, 'monto': monto,
                       'fecha': fecha, 'archivo': a_estado})
    conn.commit()

    try:
        from blueprints.notif import push_notif as _push
        try:
            from config import CONTADORA_USERS as _CU
        except Exception:
            _CU = set()
        for _u in sorted({'sebastian'} | set(_CU)):
            _push(_u, 'portal_pago',
                  '%s reportó un pago de $%s' % (cnom or cid, '{:,.0f}'.format(monto)),
                  body=('Factura %s · %s' % (factura or 'sin factura indicada', metodo)),
                  link='/admin/portal-pagos', remitente='portal', importante=True)
    except Exception as e:
        log.warning('aviso de pago del portal no salió: %s', e)

    aviso = ''
    if a_estado in ('fallo_guardado', 'sin_almacenamiento'):
        # Se dice: el aviso quedó, el archivo no · callarlo dejaría al cliente creyendo
        # que mandó el soporte (M198).
        aviso = ('Registramos el aviso, pero el comprobante no se pudo guardar. '
                 'Mandalo por Mensajes y lo adjuntamos nosotros.')
    return jsonify({'ok': True, 'id': nuevo_id, 'archivo_estado': a_estado, 'aviso': aviso,
                    'mensaje': 'Gracias, ya lo estamos revisando.'}), 201


@bp.route('/portal/comprobante/<int:pago_id>', methods=['GET'])
def portal_comprobante(pago_id):
    """Sirve el comprobante · lo ve su dueño o el backoffice, nadie más."""
    conn = get_db()
    row = conn.execute(
        "SELECT cliente_id, COALESCE(archivo_key,''), COALESCE(archivo_nombre,'') "
        "FROM portal_pagos_reportados WHERE id=?", (pago_id,)).fetchone()
    if not row:
        return Response('No existe', status=404)
    es_backoffice = session.get('compras_user', '') in (ADMIN_USERS | _CONTADORAS())
    auth = _require_portal_login()
    es_dueno = bool(auth) and str(auth[0]) == str(row[0])
    if not (es_backoffice or es_dueno):
        return Response('No autorizado', status=403)
    if not row[1]:
        return Response('Este pago se reportó sin comprobante', status=404)
    try:
        from r2_storage import r2_get
        datos = r2_get(row[1])
    except Exception as e:
        log.warning('no se pudo leer el comprobante %s: %s', pago_id, e)
        datos = None
    if not datos:
        return Response('El comprobante no se pudo recuperar del archivo', status=404)
    ext = (row[1].rsplit('.', 1)[-1] or '').lower()
    return Response(datos, mimetype=_PORTAL_DOC_EXT.get(ext, 'application/octet-stream'),
                    headers={'Content-Disposition': 'inline; filename="%s"' % (row[2] or 'comprobante')})


def _CONTADORAS():
    try:
        from config import CONTADORA_USERS as _CU
        return set(_CU)
    except Exception:
        return set()


def _lotes_del_cliente(conn, cid):
    """Los lotes que salieron de los pedidos de ESTE cliente.

    Cadena: pedidos_b2b → pedidos_b2b_lote → ebr_ejecuciones(produccion_id) → lote físico.
    Sin EBR no hay lote, y sin lote no hay certificado: eso se declara, no se inventa.
    """
    try:
        rows = conn.execute(
            """SELECT p.id, p.producto_nombre, COALESCE(e.lote_codigo, e.lote),
                      COALESCE(e.estado,''),
                      COALESCE(e.liberado_at_utc, e.completado_at_utc, e.iniciado_at_utc, '')
                 FROM pedidos_b2b p
                 JOIN pedidos_b2b_lote pl ON pl.pedido_b2b_id = p.id
                 JOIN ebr_ejecuciones e   ON e.produccion_id = pl.lote_produccion_id
                WHERE p.cliente_id = ?
                ORDER BY p.id DESC""", (cid,)).fetchall()
    except Exception as e:
        log.warning('lotes del cliente %s no se pudieron resolver: %s', cid, e)
        return []
    vistos, out = set(), []
    for pid, prod, lote, estado, fecha in rows:
        lote = (lote or '').strip()
        if not lote or lote in vistos:
            continue
        vistos.add(lote)
        out.append({'pedido_id': pid, 'producto': prod or '', 'lote': lote,
                    'estado_ebr': estado, 'fecha': (fecha or '')[:10]})
    return out


@bp.route('/api/portal/documentos', methods=['GET'])
def portal_documentos():
    """Los certificados de análisis de los lotes que el cliente recibió.

    Sólo se ofrece el COA de PRODUCTO TERMINADO. El batch record, las fórmulas y los
    certificados de materia prima son internos y no salen del backoffice: la lista es
    una whitelist, no una exclusión (default-deny).
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, _cnom, _email = auth
    conn = get_db()
    docs = []
    for l in _lotes_del_cliente(conn, cid):
        liberado = (l['estado_ebr'] or '').lower() == 'liberado'
        docs.append({
            'lote': l['lote'], 'producto': l['producto'], 'pedido_id': l['pedido_id'],
            'fecha': l['fecha'], 'disponible': liberado,
            'motivo': '' if liberado else 'El lote todavía no fue liberado por Control de Calidad',
            'url': ('/portal/coa/%s' % l['lote']) if liberado else '',
        })
    return jsonify({'documentos': docs, 'total': len(docs)})


@bp.route('/portal/coa/<path:lote>', methods=['GET'])
def portal_coa(lote):
    """El certificado de análisis de UN lote · gateado por PROPIEDAD del lote.

    Es el mismo documento que imprime Calidad (`coa_pt_imprimible`), no una copia.
    """
    auth = _require_portal_login()
    if not auth:
        return redirect('/portal/login')
    cid, _cnom, _email = auth
    lote = (lote or '').strip()
    conn = get_db()
    mios = {l['lote']: l for l in _lotes_del_cliente(conn, cid)}
    if lote not in mios:
        return Response('Ese lote no corresponde a ninguno de tus pedidos', status=403)
    if (mios[lote]['estado_ebr'] or '').lower() != 'liberado':
        return Response('El lote todavía no fue liberado por Control de Calidad', status=409)
    try:
        from blueprints.calidad import coa_pt_imprimible
    except Exception as e:
        log.warning('no se pudo cargar el generador del COA: %s', e)
        return Response('El certificado no está disponible en este momento', status=503)
    return coa_pt_imprimible(lote)


@bp.route('/api/portal/consumo', methods=['GET'])
def portal_consumo():
    """Cuánto pidió el cliente, por producto y por mes · derivado de sus pedidos.

    No se cuentan los cancelados. Si no hay historia, se dice que no la hay en vez de
    devolver ceros que se leen como "no compraste nada".
    """
    auth = _require_portal_login()
    if not auth:
        return jsonify({'error': 'No autorizado'}), 401
    cid, cnom, _email = auth
    conn = get_db()
    ref, _como = _cliente_ref(conn, cid, cnom)
    try:
        rows = conn.execute(
            """SELECT COALESCE(producto_nombre,''), COALESCE(cantidad_uds,0),
                      COALESCE(ml_unidad,0), COALESCE(creado_at_utc,''), COALESCE(estado,'')
                 FROM pedidos_b2b
                WHERE cliente_id = ? AND LOWER(COALESCE(estado,'')) != 'cancelado'""",
            (cid,)).fetchall()
    except Exception as e:
        log.warning('consumo del portal falló: %s', e)
        rows = []
    _gen = {}
    try:
        for gr in conn.execute(
            "SELECT producto_nombre, COALESCE(MAX(nombre_generico),'') FROM formula_headers "
            "WHERE COALESCE(activo,1)=1 GROUP BY producto_nombre").fetchall():
            if (gr[1] or '').strip():
                _gen[(gr[0] or '').strip().upper()] = gr[1].strip()
    except Exception:
        pass
    por_prod, por_mes = {}, {}
    tot_uds = tot_kg = 0.0
    for prod, uds, ml, creado, _est in rows:
        uds = int(uds or 0)
        kg = round(uds * float(ml or 0) / 1000.0, 2)
        nombre = _gen.get((prod or '').strip().upper(), '') or (prod or 'Producto')
        d = por_prod.setdefault(nombre, {'producto': nombre, 'pedidos': 0, 'unidades': 0, 'kg': 0.0})
        d['pedidos'] += 1
        d['unidades'] += uds
        d['kg'] = round(d['kg'] + kg, 2)
        mes = (creado or '')[:7]
        if mes:
            m = por_mes.setdefault(mes, {'mes': mes, 'pedidos': 0, 'unidades': 0, 'kg': 0.0})
            m['pedidos'] += 1
            m['unidades'] += uds
            m['kg'] = round(m['kg'] + kg, 2)
        tot_uds += uds
        tot_kg += kg
    productos = sorted(por_prod.values(), key=lambda x: -x['unidades'])
    meses = sorted(por_mes.values(), key=lambda x: x['mes'])[-12:]
    return jsonify({
        'hay_historia': bool(rows), 'pedidos': len(rows),
        'unidades': int(tot_uds), 'kg': round(tot_kg, 2),
        'productos': productos, 'meses': meses,
        'facturacion_enlazada': bool(ref),
    })


# ── Backoffice · conciliar lo que el cliente reportó ──────────────────

def _require_cobranza():
    """Admin o contadora · quien concilia plata que entra."""
    u = session.get('compras_user', '')
    if not u:
        return None, (jsonify({'error': 'No autenticado'}), 401)
    if u not in (ADMIN_USERS | _CONTADORAS()):
        return None, (jsonify({'error': 'Solo admin o contadora'}), 403)
    return u, None


@bp.route('/api/admin/portal/pagos', methods=['GET'])
def admin_portal_pagos_lista():
    u, err = _require_cobranza()
    if err:
        return err
    estado = (request.args.get('estado') or '').strip().lower()
    conn = get_db()
    sql = ("SELECT id, cliente_id, COALESCE(cliente_nombre,''), COALESCE(factura_numero,''), "
           "COALESCE(monto,0), COALESCE(fecha_pago,''), COALESCE(metodo,''), "
           "COALESCE(referencia,''), COALESCE(nota,''), COALESCE(estado,'reportado'), "
           "COALESCE(archivo_estado,''), COALESCE(archivo_nombre,''), COALESCE(creado_at,''), "
           "COALESCE(motivo,''), COALESCE(resuelto_por,''), COALESCE(resuelto_at,'') "
           "FROM portal_pagos_reportados")
    params = []
    if estado in ('reportado', 'conciliado', 'rechazado'):
        sql += " WHERE estado = ?"
        params.append(estado)
    sql += " ORDER BY (estado='reportado') DESC, id DESC LIMIT 300"
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        log.warning('lista admin de pagos del portal falló: %s', e)
        rows = []
    items = [{
        'id': r[0], 'cliente_id': r[1], 'cliente_nombre': r[2], 'factura_numero': r[3],
        'monto': round(float(r[4] or 0), 2), 'fecha_pago': r[5][:10], 'metodo': r[6],
        'referencia': r[7], 'nota': r[8], 'estado': r[9], 'archivo_estado': r[10],
        'archivo_nombre': r[11], 'creado_at': (r[12] or '')[:16], 'motivo': r[13],
        'resuelto_por': r[14], 'resuelto_at': (r[15] or '')[:16],
    } for r in rows]
    pend = sum(1 for i in items if i['estado'] == 'reportado')
    return jsonify({'items': items, 'total': len(items), 'pendientes': pend})


@bp.route('/api/admin/portal/pagos/<int:pago_id>/conciliar', methods=['POST'])
def admin_portal_pago_conciliar(pago_id):
    """Aplica el pago reportado a la factura · pasa por el camino canónico de cobranza.

    El CAS sobre `estado` es lo que impide que dos clics registren el cobro dos veces
    (M27): quien pierde la carrera ve un 409, no un segundo asiento.
    """
    u, err = _require_cobranza()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(factura_numero,''), COALESCE(monto,0), COALESCE(fecha_pago,''), "
        "COALESCE(metodo,''), COALESCE(referencia,''), COALESCE(estado,''), cliente_id "
        "FROM portal_pagos_reportados WHERE id=?", (pago_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Ese pago no existe'}), 404
    if row[5] != 'reportado':
        return jsonify({'error': 'Ese pago ya fue resuelto', 'codigo': 'YA_RESUELTO'}), 409
    factura = (body.get('factura_numero') or row[0] or '').strip()
    if not factura:
        return jsonify({'error': 'Falta la factura a la que se aplica'}), 400
    try:
        monto = float(body.get('monto') or row[1] or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'monto inválido'}), 400
    if monto <= 0:
        return jsonify({'error': 'El monto tiene que ser mayor a cero'}), 400

    # Reclamar ANTES de tocar la contabilidad · si otro lo tomó, no se cobra dos veces.
    cur.execute("UPDATE portal_pagos_reportados SET estado='conciliado', resuelto_por=?, "
                "resuelto_at=?, factura_numero=? WHERE id=? AND estado='reportado'",
                (u, _ahora_col_iso(), factura, pago_id))
    if cur.rowcount != 1:
        conn.rollback()
        return jsonify({'error': 'Otro usuario lo resolvió primero', 'codigo': 'YA_RESUELTO'}), 409

    try:
        from blueprints.contabilidad import registrar_pago_factura
    except Exception as e:
        conn.rollback()
        log.warning('no se pudo cargar el registrador de cobranza: %s', e)
        return jsonify({'error': 'La contabilidad no está disponible en este momento'}), 503
    ok, payload, status = registrar_pago_factura(
        conn, factura, monto, fecha=(row[2] or None),
        medio=(row[3] or 'Transferencia'),
        referencia=('portal #%s %s' % (pago_id, row[4] or '')).strip(), usuario=u)
    if not ok:
        conn.rollback()
        return jsonify(payload), status
    audit_log(cur, usuario=u, accion='PORTAL_PAGO_CONCILIADO',
              tabla='portal_pagos_reportados', registro_id=pago_id,
              despues={'factura': factura, 'monto': monto, 'cliente': row[6]})
    conn.commit()
    return jsonify({'ok': True, 'id': pago_id, 'factura': factura,
                    'estado_factura': payload.get('estado')})


@bp.route('/api/admin/portal/pagos/<int:pago_id>/rechazar', methods=['POST'])
def admin_portal_pago_rechazar(pago_id):
    """Rechaza un pago reportado · el motivo es obligatorio y el cliente lo lee."""
    u, err = _require_cobranza()
    if err:
        return err
    motivo = ((request.get_json(silent=True) or {}).get('motivo') or '').strip()[:300]
    if not motivo:
        return jsonify({'error': 'Escribí el motivo · el cliente lo va a leer'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE portal_pagos_reportados SET estado='rechazado', motivo=?, "
                "resuelto_por=?, resuelto_at=? WHERE id=? AND estado='reportado'",
                (motivo, u, _ahora_col_iso(), pago_id))
    if cur.rowcount != 1:
        conn.rollback()
        return jsonify({'error': 'Ese pago ya fue resuelto', 'codigo': 'YA_RESUELTO'}), 409
    audit_log(cur, usuario=u, accion='PORTAL_PAGO_RECHAZADO',
              tabla='portal_pagos_reportados', registro_id=pago_id,
              despues={'motivo': motivo})
    conn.commit()
    return jsonify({'ok': True, 'id': pago_id})


@bp.route('/api/admin/portal/credenciales/<int:cred_id>/enlazar', methods=['POST'])
def admin_portal_enlazar_cliente(cred_id):
    """Ata la credencial del portal a una cuenta de facturación (`clientes.id`).

    Es la pieza que hace que el módulo de Facturas del cliente muestre algo. Se hace a
    mano a propósito: enlazar mal deja a un cliente viendo las facturas de otro.
    """
    u, err = _require_admin_backoffice()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    cred = cur.execute("SELECT cliente_id, cliente_nombre FROM portal_clientes_credenciales "
                       "WHERE id=?", (cred_id,)).fetchone()
    if not cred:
        return jsonify({'error': 'Esa credencial no existe'}), 404
    if body.get('cliente_ref_id') in (None, '', 0, '0'):
        cur.execute("UPDATE portal_clientes_credenciales SET cliente_ref_id=NULL WHERE id=?",
                    (cred_id,))
        audit_log(cur, usuario=u, accion='PORTAL_DESENLAZAR_CLIENTE',
                  tabla='portal_clientes_credenciales', registro_id=cred_id,
                  antes={'cliente_id': cred[0]}, despues={'cliente_ref_id': None})
        conn.commit()
        return jsonify({'ok': True, 'cliente_ref_id': None})
    try:
        ref = int(body.get('cliente_ref_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'cliente_ref_id inválido'}), 400
    cli = cur.execute("SELECT nombre FROM clientes WHERE id=?", (ref,)).fetchone()
    if not cli:
        return jsonify({'error': 'Ese cliente de facturación no existe'}), 404
    ocupado = cur.execute("SELECT cliente_id FROM portal_clientes_credenciales "
                          "WHERE cliente_ref_id=? AND id<>? AND COALESCE(activo,1)=1",
                          (ref, cred_id)).fetchone()
    if ocupado:
        return jsonify({'error': 'Esa cuenta ya está enlazada a %s' % ocupado[0],
                        'codigo': 'YA_ENLAZADA'}), 409
    cur.execute("UPDATE portal_clientes_credenciales SET cliente_ref_id=? WHERE id=?",
                (ref, cred_id))
    audit_log(cur, usuario=u, accion='PORTAL_ENLAZAR_CLIENTE',
              tabla='portal_clientes_credenciales', registro_id=cred_id,
              despues={'cliente_ref_id': ref, 'cliente': cli[0], 'portal': cred[0]})
    conn.commit()
    return jsonify({'ok': True, 'cliente_ref_id': ref, 'cliente_nombre': cli[0]})


@bp.route('/api/admin/portal/clientes-facturacion', methods=['GET'])
def admin_portal_clientes_facturacion():
    """Las cuentas de facturación disponibles para enlazar (para el desplegable)."""
    u, err = _require_admin_backoffice()
    if err:
        return err
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, nombre, COALESCE(codigo,''), COALESCE(nit,'') FROM clientes "
            "WHERE COALESCE(activo,1)=1 ORDER BY nombre ASC LIMIT 500").fetchall()
    except Exception as e:
        log.warning('clientes de facturación no se pudieron listar: %s', e)
        rows = []
    return jsonify({'items': [{'id': r[0], 'nombre': r[1], 'codigo': r[2], 'nit': r[3]}
                              for r in rows], 'total': len(rows)})
# ── Pantalla de backoffice · sin ella, los endpoints de arriba no existen ──
# (M197: una capacidad a la que nadie puede llegar no existe · y desde adentro
#  se ve terminada, porque los tests pasan.)

_PORTAL_PAGOS_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pagos del portal · EOS</title>
<script>(function(){try{var t=localStorage.getItem('cx-theme');if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:var(--cx-bg, #f4f4f7);color:var(--cx-text, #18181b);font-size:14px}
.wrap{max-width:1500px;margin:0 auto;padding:22px 26px 60px}
.top{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:6px}
h1{font-size:24px;font-weight:800;letter-spacing:-.6px}
.sub{font-size:13px;color:var(--cx-text-mute, #6b6b74);margin-bottom:18px}
.volver{margin-left:auto;text-decoration:none;font-size:13px;font-weight:700;
        color:var(--cx-text-soft, #3f3f46);border:1px solid var(--cx-border, #e6e6ea);
        background:var(--cx-card, #fff);border-radius:10px;padding:8px 14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--cx-card, #fff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:12px;padding:14px 16px}
.kpi .k{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;
        color:var(--cx-text-mute, #6b6b74)}
.kpi .v{font-size:23px;font-weight:800;letter-spacing:-.6px;margin-top:4px}
.tabs{display:flex;gap:7px;margin-bottom:16px;flex-wrap:wrap}
.tb{padding:9px 16px;border-radius:10px;border:1px solid var(--cx-border, #e6e6ea);
    background:var(--cx-card, #fff);color:var(--cx-text-mute, #6b6b74);font-size:13.5px;
    font-weight:700;cursor:pointer;font-family:inherit}
.tb.on{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;
       border-color:transparent;box-shadow:0 6px 16px rgba(109,40,217,.26)}
.panel{display:none}
.panel.on{display:block}
.card{background:var(--cx-card, #fff);border:1px solid var(--cx-border, #e6e6ea);
      border-radius:14px;padding:0;overflow:hidden;box-shadow:var(--cx-sh-sm, 0 1px 2px rgba(15,23,42,.04))}
table{width:100%;border-collapse:collapse}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;text-align:left;
   color:var(--cx-text-mute, #6b6b74);padding:12px 14px;border-bottom:1px solid var(--cx-border, #e6e6ea);
   background:var(--cx-bg-alt, #fbfbfd);font-weight:800;white-space:nowrap}
td{padding:12px 14px;border-bottom:1px solid var(--cx-border-soft, #f1f1f4);vertical-align:top}
tr:last-child td{border-bottom:none}
.num{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.chip{display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;
      font-size:11px;font-weight:800}
.chip.esp{background:var(--cx-warn-pale, #fffbeb);color:var(--cx-warn-text, #b45309)}
.chip.ok{background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d)}
.chip.no{background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c)}
.chip.gris{background:var(--cx-border-soft, #f1f1f4);color:var(--cx-text-mute, #6b6b74)}
.btn{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;
     border:none;border-radius:9px;padding:8px 14px;font-size:12.5px;font-weight:700;
     cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.sec{background:var(--cx-card, #fff);color:var(--cx-text-soft, #3f3f46);
         border:1px solid var(--cx-border, #e6e6ea)}
.btn.peligro{background:var(--cx-card, #fff);color:var(--cx-danger-text, #b91c1c);
             border:1px solid var(--cx-danger-pale, #fef2f2)}
a.link{color:var(--cx-primary-text, #6d28d9);font-weight:700;text-decoration:none;font-size:12.5px}
.mut{color:var(--cx-text-mute, #6b6b74);font-size:12px}
.vacio{padding:34px;text-align:center;color:var(--cx-text-mute, #6b6b74)}
select,input,textarea{padding:9px 11px;border:1px solid var(--cx-border, #e6e6ea);border-radius:9px;
       background:var(--cx-bg-alt, #fbfbfd);color:var(--cx-text, #18181b);font-family:inherit;font-size:13.5px}
.ov{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:60;padding:18px;
    display:none;align-items:center;justify-content:center}
.ov.on{display:flex}
.mo{background:var(--cx-card, #fff);border-radius:16px;padding:22px;width:100%;max-width:460px}
.mo h2{font-size:17px;font-weight:800;margin-bottom:4px}
.mo label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
          color:var(--cx-text-mute, #6b6b74);margin:14px 0 5px}
.mo input,.mo textarea,.mo select{width:100%}
.mo .acc{display:flex;gap:8px;margin-top:18px}
.msg{margin-top:12px;padding:10px 13px;border-radius:9px;font-size:13px;display:none}
.msg.ok{display:block;background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d)}
.msg.err{display:block;background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c)}
</style></head><body>
<div class="wrap">
  <div class="top">
    <h1>Pagos del portal</h1>
    <a class="volver" href="/admin/portal-mensajes">Mensajes</a>
    <a class="volver" href="/admin/clientes-b2b">Clientes B2B</a>
    <a class="volver" href="/modulos">Volver</a>
  </div>
  <div class="sub">Lo que el cliente avisa que pagó. Un pago acá NO entra a la contabilidad hasta que lo concilies: al conciliar se registra el cobro por el mismo camino que Contabilidad.</div>

  <div class="kpis" id="kpis"></div>

  <div class="tabs">
    <button class="tb on" id="tb-pagos" onclick="verTab('pagos')">Pagos reportados</button>
    <button class="tb" id="tb-enlace" onclick="verTab('enlace')">Enlace de facturación</button>
  </div>

  <div class="panel on" id="p-pagos">
    <div style="margin-bottom:12px">
      <select id="filtro" onchange="cargarPagos()">
        <option value="reportado">Pendientes de conciliar</option>
        <option value="">Todos</option>
        <option value="conciliado">Conciliados</option>
        <option value="rechazado">Rechazados</option>
      </select>
    </div>
    <div class="card"><div id="tabla-pagos"><div class="vacio">Cargando...</div></div></div>
  </div>

  <div class="panel" id="p-enlace">
    <div class="sub" style="margin-bottom:12px">Sin este enlace, el cliente entra al portal y su modulo de Facturas sale vacio: el portal guarda un identificador de texto y la facturacion usa el id del cliente. Se hace a mano a proposito, porque enlazar mal deja a un cliente viendo las facturas de otro.</div>
    <div class="card"><div id="tabla-enlace"><div class="vacio">Cargando...</div></div></div>
  </div>
</div>

<div class="ov" id="ov" onclick="if(event.target===this)cerrar()">
  <div class="mo">
    <h2 id="mo-tit">Conciliar pago</h2>
    <div class="mut" id="mo-sub"></div>
    <div id="mo-conciliar">
      <label for="mo-factura">Factura a la que se aplica</label>
      <input id="mo-factura" placeholder="FV-2026-0001">
      <label for="mo-monto">Monto</label>
      <input id="mo-monto" type="number" step="0.01" min="0">
    </div>
    <div id="mo-rechazar" style="display:none">
      <label for="mo-motivo">Motivo (lo lee el cliente)</label>
      <textarea id="mo-motivo" rows="3" placeholder="Ej. el comprobante corresponde a otra factura"></textarea>
    </div>
    <div class="msg" id="mo-msg"></div>
    <div class="acc">
      <button class="btn" id="mo-btn" onclick="confirmar()">Confirmar</button>
      <button class="btn sec" onclick="cerrar()">Cancelar</button>
    </div>
  </div>
</div>

<script>
var _CSRF = '', _ACCION = '', _PAGO = 0, _PAGOS = [];
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function $(i){return document.getElementById(i);}
function plata(v){return '$' + Number(v||0).toLocaleString('es-CO',{maximumFractionDigits:0});}
async function csrf(){
  if(_CSRF) return _CSRF;
  try{ var d = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
       _CSRF = d.csrf_token || ''; }catch(e){}
  return _CSRF;
}
function verTab(t){
  ['pagos','enlace'].forEach(function(k){
    $('p-'+k).classList.toggle('on', k===t); $('tb-'+k).classList.toggle('on', k===t);
  });
  if(t==='enlace') cargarEnlace();
}
async function cargarPagos(){
  var f = $('filtro').value;
  try{
    var d = await (await fetch('/api/admin/portal/pagos?estado='+encodeURIComponent(f),
                               {credentials:'same-origin'})).json();
    _PAGOS = d.items || [];
    $('kpis').innerHTML =
        '<div class="kpi"><div class="k">Esperando conciliacion</div><div class="v">' + (d.pendientes||0) + '</div></div>'
      + '<div class="kpi"><div class="k">Monto pendiente</div><div class="v">'
      +   plata(_PAGOS.filter(function(p){return p.estado==='reportado';})
                       .reduce(function(a,p){return a+(p.monto||0);},0)) + '</div></div>'
      + '<div class="kpi"><div class="k">En esta lista</div><div class="v">' + _PAGOS.length + '</div></div>';
    if(!_PAGOS.length){
      $('tabla-pagos').innerHTML = '<div class="vacio">No hay pagos con ese filtro.</div>'; return;
    }
    $('tabla-pagos').innerHTML =
      '<table><thead><tr><th>Cliente</th><th>Factura</th><th>Monto</th><th>Pago</th>'
      + '<th>Metodo</th><th>Comprobante</th><th>Estado</th><th></th></tr></thead><tbody>'
      + _PAGOS.map(function(p){
        var cls = p.estado==='reportado'?'esp':(p.estado==='conciliado'?'ok':'no');
        var comp = p.archivo_estado==='guardado'
          ? '<a class="link" href="/portal/comprobante/'+p.id+'" target="_blank">Ver</a>'
          : '<span class="mut">'+esc(p.archivo_estado==='sin_archivo'?'sin adjunto':'no se guardo')+'</span>';
        return '<tr><td><b>'+esc(p.cliente_nombre||p.cliente_id)+'</b><div class="mut">'+esc(p.cliente_id)+'</div></td>'
          + '<td>'+(p.factura_numero?esc(p.factura_numero):'<span class="mut">no indico</span>')+'</td>'
          + '<td class="num">'+plata(p.monto)+'</td>'
          + '<td>'+esc(p.fecha_pago)+'<div class="mut">reporto '+esc(p.creado_at)+'</div></td>'
          + '<td>'+esc(p.metodo)+(p.referencia?'<div class="mut">'+esc(p.referencia)+'</div>':'')+'</td>'
          + '<td>'+comp+'</td>'
          + '<td><span class="chip '+cls+'">'+esc(p.estado)+'</span>'
          +   (p.motivo?'<div class="mut">'+esc(p.motivo)+'</div>':'')
          +   (p.resuelto_por?'<div class="mut">'+esc(p.resuelto_por)+'</div>':'')+'</td>'
          + '<td style="white-space:nowrap">'
          +   (p.estado==='reportado'
                ? '<button class="btn" onclick="abrir('+p.id+',&quot;conciliar&quot;)">Conciliar</button> '
                  + '<button class="btn peligro" onclick="abrir('+p.id+',&quot;rechazar&quot;)">Rechazar</button>'
                : '')
          + '</td></tr>';
      }).join('') + '</tbody></table>';
  }catch(e){ $('tabla-pagos').innerHTML = '<div class="vacio">No se pudo cargar: '+esc(e.message)+'</div>'; }
}
function abrir(id, accion){
  var p = _PAGOS.filter(function(x){return x.id===id;})[0]; if(!p) return;
  _PAGO = id; _ACCION = accion;
  $('mo-tit').textContent = accion==='conciliar' ? 'Conciliar pago' : 'Rechazar pago';
  $('mo-sub').textContent = (p.cliente_nombre||p.cliente_id) + ' · ' + plata(p.monto) + ' · ' + p.fecha_pago;
  $('mo-conciliar').style.display = accion==='conciliar' ? 'block' : 'none';
  $('mo-rechazar').style.display = accion==='rechazar' ? 'block' : 'none';
  $('mo-factura').value = p.factura_numero || '';
  $('mo-monto').value = p.monto || '';
  $('mo-motivo').value = '';
  $('mo-msg').className = 'msg';
  $('ov').classList.add('on');
}
function cerrar(){ $('ov').classList.remove('on'); _PAGO = 0; }
async function confirmar(){
  if(!_PAGO) return;
  var btn = $('mo-btn'), msg = $('mo-msg');
  var url, body;
  if(_ACCION==='conciliar'){
    var fac = $('mo-factura').value.trim();
    if(!fac){ msg.className='msg err'; msg.textContent='Indica la factura.'; return; }
    url = '/api/admin/portal/pagos/'+_PAGO+'/conciliar';
    body = {factura_numero: fac, monto: parseFloat($('mo-monto').value||'0')};
  } else {
    var mot = $('mo-motivo').value.trim();
    if(!mot){ msg.className='msg err'; msg.textContent='Escribi el motivo, el cliente lo lee.'; return; }
    url = '/api/admin/portal/pagos/'+_PAGO+'/rechazar';
    body = {motivo: mot};
  }
  btn.disabled = true; btn.textContent = 'Guardando...';
  try{
    var t = await csrf();
    var r = await fetch(url, {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(body)});
    var d = await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent = d.error || ('Error '+r.status); return; }
    cerrar(); cargarPagos();
  }catch(e){ msg.className='msg err'; msg.textContent='Error de red'; }
  finally{ btn.disabled=false; btn.textContent='Confirmar'; }
}
async function cargarEnlace(){
  try{
    var res = await Promise.all([
      fetch('/api/admin/portal/credenciales',{credentials:'same-origin'}),
      fetch('/api/admin/portal/clientes-facturacion',{credentials:'same-origin'})
    ]);
    var creds = (await res[0].json()).items || [];
    var clis = (await res[1].json()).items || [];
    if(!creds.length){
      $('tabla-enlace').innerHTML = '<div class="vacio">Todavia no hay clientes con acceso al portal.</div>'; return;
    }
    var opciones = '<option value="">Sin enlazar</option>' + clis.map(function(c){
      return '<option value="'+c.id+'">'+esc(c.nombre)+(c.nit?(' · '+esc(c.nit)):'')+'</option>';
    }).join('');
    $('tabla-enlace').innerHTML =
      '<table><thead><tr><th>Cliente del portal</th><th>Correo</th><th>Cuenta de facturacion</th><th></th></tr></thead><tbody>'
      + creds.map(function(c){
        return '<tr><td><b>'+esc(c.cliente_nombre)+'</b><div class="mut">'+esc(c.cliente_id)+'</div></td>'
          + '<td class="mut">'+esc(c.email)+'</td>'
          + '<td><select id="sel-'+c.id+'">'+opciones+'</select></td>'
          + '<td><button class="btn" onclick="enlazar('+c.id+')">Guardar</button></td></tr>';
      }).join('') + '</tbody></table>';
    creds.forEach(function(c){
      var s = $('sel-'+c.id); if(s && c.cliente_ref_id) s.value = String(c.cliente_ref_id);
    });
  }catch(e){ $('tabla-enlace').innerHTML = '<div class="vacio">No se pudo cargar.</div>'; }
}
async function enlazar(credId){
  var s = $('sel-'+credId); if(!s) return;
  try{
    var t = await csrf();
    var r = await fetch('/api/admin/portal/credenciales/'+credId+'/enlazar', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t},
      body: JSON.stringify({cliente_ref_id: s.value || null})});
    var d = await r.json();
    if(!r.ok){ alert(d.error || ('Error '+r.status)); return; }
    cargarEnlace();
  }catch(e){ alert('Error de red'); }
}
cargarPagos();
</script></body></html>
"""


@bp.route('/admin/portal-pagos', methods=['GET'])
def admin_portal_pagos_pagina():
    """Donde la contadora concilia lo que el cliente reportó y donde se enlaza su cuenta."""
    u = session.get('compras_user', '')
    if not u:
        return redirect('/login?next=/admin/portal-pagos')
    if u not in (ADMIN_USERS | _CONTADORAS()):
        # Una pantalla vacía se lee como rota, no como prohibida (M170).
        return Response('<p style="font-family:sans-serif;padding:40px">Esta pantalla es de '
                        'administración y contabilidad.</p>', status=403, mimetype='text/html')
    return Response(_PORTAL_PAGOS_HTML, mimetype='text/html')
# ══════════════════════════════════════════════════════════════════════
# La bandeja donde se RESPONDE lo que el cliente escribe (14-ago-2026)
#
# Hasta hoy no existía: los endpoints para responder un PQR estaban desde
# mayo, la campana avisaba con un enlace a `/admin?tab=portal_pqr` y el cron
# de plazos con otro a `/admin/portal/pqr` · NINGUNA de las dos rutas existe.
# O sea que un reclamo formal (registro regulado, con plazo) sólo se podía
# responder por API. Es M121 en su forma más cara: construido, avisado, y sin
# una pantalla por donde entrar.
#
# El cliente ahora escribe desde UN solo lugar, así que acá se lee igual: los
# PQR formales y lo comercial en la misma cola, ordenados por lo que urge.
# ══════════════════════════════════════════════════════════════════════

def _CALIDAD():
    try:
        from config import CALIDAD_USERS as _CU
        return set(_CU)
    except Exception:
        return set()


def _COMPRAS():
    try:
        from config import COMPRAS_ACCESS as _CA
        return set(_CA)
    except Exception:
        return set()


def _require_pqr():
    """Un PQR es un registro REGULADO y su dueño es CALIDAD, no sólo el admin.

    Estaba gateado a ADMIN_USERS: Calidad recibía la campana del reclamo y al
    entrar le daba 403, que es justo el hueco de M32 (dividir un cargo y dejar
    al dueño del módulo sin escritura sobre lo suyo).
    """
    u = session.get('compras_user', '')
    if not u:
        return None, (jsonify({'error': 'No autenticado'}), 401)
    if u not in (ADMIN_USERS | _CALIDAD()):
        return None, (jsonify({'error': 'Solo admin o calidad'}), 403)
    return u, None


@bp.route('/admin/portal-mensajes', methods=['GET'])
def admin_portal_mensajes_pagina():
    u = session.get('compras_user', '')
    if not u:
        return redirect('/login?next=/admin/portal-mensajes')
    if u not in (ADMIN_USERS | _CALIDAD() | _COMPRAS()):
        return Response('<p style="font-family:sans-serif;padding:40px">Esta bandeja es de '
                        'administración, calidad y compras.</p>', status=403, mimetype='text/html')
    return Response(_PORTAL_MENSAJES_HTML, mimetype='text/html')


_PORTAL_MENSAJES_HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mensajes de clientes · EOS</title>
<script>(function(){try{var t=localStorage.getItem('cx-theme');if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:var(--cx-bg, #f4f4f7);color:var(--cx-text, #18181b);font-size:14px}
.wrap{max-width:1500px;margin:0 auto;padding:22px 26px 60px}
.top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
h1{font-size:24px;font-weight:800;letter-spacing:-.6px}
.sub{font-size:13px;color:var(--cx-text-mute, #6b6b74);margin:4px 0 18px}
.volver{margin-left:auto;text-decoration:none;font-size:12.5px;font-weight:700;
        color:var(--cx-text-soft, #3f3f46);border:1px solid var(--cx-border, #e6e6ea);
        background:var(--cx-card, #fff);border-radius:10px;padding:8px 13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--cx-card, #fff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:12px;padding:14px 16px}
.kpi .k{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;
        color:var(--cx-text-mute, #6b6b74)}
.kpi .v{font-size:23px;font-weight:800;letter-spacing:-.6px;margin-top:4px}
.kpi.alerta .v{color:var(--cx-danger-text, #b91c1c)}
.filtros{display:flex;gap:7px;margin-bottom:16px;flex-wrap:wrap}
.fb{padding:9px 15px;border-radius:10px;border:1px solid var(--cx-border, #e6e6ea);
    background:var(--cx-card, #fff);color:var(--cx-text-mute, #6b6b74);font-size:13px;
    font-weight:700;cursor:pointer;font-family:inherit}
.fb.on{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;
       border-color:transparent;box-shadow:0 6px 16px rgba(109,40,217,.26)}
.msj{background:var(--cx-card, #fff);border:1px solid var(--cx-border, #e6e6ea);
     border-radius:14px;padding:16px 18px;margin-bottom:11px;position:relative;overflow:hidden}
.msj::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;
             background:var(--cx-border, #e6e6ea)}
.msj.urge::before{background:var(--cx-danger, #dc2626)}
.msj.espera::before{background:var(--cx-warn, #f59e0b)}
.msj.hecho::before{background:var(--cx-success, #15803d)}
.msj-top{display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap}
.msj-tit{font-size:15px;font-weight:800;letter-spacing:-.2px}
.msj-cli{font-size:12px;color:var(--cx-text-mute, #6b6b74);margin-top:2px}
.msj-edad{margin-left:auto;text-align:right;white-space:nowrap}
.msj-edad .d{font-size:15px;font-weight:800;font-variant-numeric:tabular-nums}
.msj-edad .l{font-size:10px;color:var(--cx-text-mute, #6b6b74);text-transform:uppercase;letter-spacing:.6px}
.msj-txt{font-size:13px;color:var(--cx-text-soft, #3f3f46);margin-top:9px;white-space:pre-wrap;
         word-break:break-word;line-height:1.5}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
.chip{display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;
      font-size:11px;font-weight:800}
.chip.rojo{background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c)}
.chip.ambar{background:var(--cx-warn-pale, #fffbeb);color:var(--cx-warn-text, #b45309)}
.chip.verde{background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d)}
.chip.violeta{background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #6d28d9)}
.chip.gris{background:var(--cx-border-soft, #f1f1f4);color:var(--cx-text-mute, #6b6b74)}
.resp{margin-top:10px;padding:11px 13px;border-radius:10px;
      background:var(--cx-primary-pale, #f5f3ff);border-left:3px solid var(--cx-primary-light, #a78bfa);
      font-size:13px;color:var(--cx-text, #18181b);white-space:pre-wrap;line-height:1.5}
.resp b{color:var(--cx-primary-text, #6d28d9);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.acc{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
.btn{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;border:none;
     border-radius:9px;padding:9px 15px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.sec{background:var(--cx-card, #fff);color:var(--cx-text-soft, #3f3f46);
         border:1px solid var(--cx-border, #e6e6ea)}
.vacio{padding:36px;text-align:center;color:var(--cx-text-mute, #6b6b74);
       background:var(--cx-card, #fff);border:1px solid var(--cx-border, #e6e6ea);border-radius:14px}
.aviso{padding:11px 14px;border-radius:10px;font-size:12.5px;margin-bottom:14px;
       background:var(--cx-warn-pale, #fffbeb);color:var(--cx-warn-text, #b45309);
       border-left:3px solid var(--cx-warn, #f59e0b);display:none}
.aviso.on{display:block}
.ov{position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:60;padding:18px;
    display:none;align-items:center;justify-content:center}
.ov.on{display:flex}
.mo{background:var(--cx-card, #fff);border-radius:16px;padding:22px;width:100%;max-width:540px;
    max-height:90vh;overflow:auto}
.mo h2{font-size:17px;font-weight:800}
.mo .ctx{font-size:12.5px;color:var(--cx-text-mute, #6b6b74);margin-top:4px}
.mo .orig{margin-top:12px;padding:11px 13px;border-radius:10px;background:var(--cx-bg-alt, #fbfbfd);
          font-size:13px;white-space:pre-wrap;line-height:1.5;max-height:180px;overflow:auto}
label{display:block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
      color:var(--cx-text-mute, #6b6b74);margin:14px 0 5px}
textarea,select{width:100%;padding:11px 13px;border:1px solid var(--cx-border, #e6e6ea);
       border-radius:10px;background:var(--cx-bg-alt, #fbfbfd);color:var(--cx-text, #18181b);
       font-family:inherit;font-size:14px;outline:none}
textarea:focus,select:focus{border-color:var(--cx-primary-light, #a78bfa);
       box-shadow:0 0 0 3px var(--cx-primary-pale, #f5f3ff)}
.msg{margin-top:12px;padding:10px 13px;border-radius:9px;font-size:13px;display:none}
.msg.ok{display:block;background:var(--cx-success-pale, #f0fdf4);color:var(--cx-success-text, #15803d)}
.msg.err{display:block;background:var(--cx-danger-pale, #fef2f2);color:var(--cx-danger-text, #b91c1c)}
</style></head><body>
<div class="wrap">
  <div class="top">
    <h1>Mensajes de clientes</h1>
    <a class="volver" href="/admin/portal-pagos">Pagos del portal</a>
    <a class="volver" href="/admin/clientes-b2b">Clientes B2B</a>
    <a class="volver" href="/modulos">Volver</a>
  </div>
  <div class="sub">Todo lo que los clientes escriben desde su portal, en una sola cola: los PQR formales (van al registro regulado que ve Calidad) y lo comercial. Ordenado por lo que lleva más tiempo esperando.</div>

  <div class="aviso" id="aviso-parcial"></div>
  <div class="kpis" id="kpis"></div>

  <div class="filtros">
    <button class="fb on" id="f-pendientes" onclick="filtrar('pendientes')">Sin responder</button>
    <button class="fb" id="f-formales" onclick="filtrar('formales')">PQR formales</button>
    <button class="fb" id="f-comercial" onclick="filtrar('comercial')">Comerciales</button>
    <button class="fb" id="f-todo" onclick="filtrar('todo')">Todo</button>
  </div>

  <div id="lista"><div class="vacio">Cargando...</div></div>
</div>

<div class="ov" id="ov" onclick="if(event.target===this)cerrar()">
  <div class="mo">
    <h2 id="mo-tit">Responder</h2>
    <div class="ctx" id="mo-ctx"></div>
    <div class="orig" id="mo-orig"></div>
    <div id="mo-estado-box">
      <label for="mo-estado">Estado</label>
      <select id="mo-estado">
        <option value="respondido">Respondido</option>
        <option value="en_revision">En revisión</option>
        <option value="cerrado">Cerrado</option>
      </select>
    </div>
    <label for="mo-texto">Respuesta (la lee el cliente en su portal)</label>
    <textarea id="mo-texto" rows="5" placeholder="Contale qué encontramos y qué vamos a hacer."></textarea>
    <div class="msg" id="mo-msg"></div>
    <div class="acc">
      <button class="btn" id="mo-btn" onclick="enviar()">Enviar respuesta</button>
      <button class="btn sec" onclick="cerrar()">Cancelar</button>
    </div>
  </div>
</div>

<script>
var _CSRF = '', _ITEMS = [], _FILTRO = 'pendientes', _ACTUAL = null;
var _TIPO_LBL = {peticion:'Petición', queja:'Queja', reclamo:'Reclamo', sugerencia:'Sugerencia',
                 nuevo_producto:'Producto nuevo', reunion:'Reunión', consulta:'Consulta',
                 cotizacion:'Cotización', muestras:'Muestras', ficha_tecnica:'Ficha técnica'};
var _EST_LBL = {abierto:'Sin responder', en_revision:'En revisión', respondido:'Respondido',
                cerrado:'Cerrado', nueva:'Sin responder', respondida:'Respondida',
                convertida:'Convertida en pedido', cerrada:'Cerrada', rechazada:'Rechazada'};

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function $(i){return document.getElementById(i);}
async function csrf(){
  if(_CSRF) return _CSRF;
  try{ var d = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
       _CSRF = d.csrf_token || ''; }catch(e){}
  return _CSRF;
}
function dias(f){
  if(!f) return 0;
  var t = Date.parse(String(f).replace(' ', 'T'));
  if(isNaN(t)) return 0;
  return Math.max(0, Math.floor((Date.now() - t) / 86400000));
}
function pendiente(m){
  return m.formal ? (m.estado === 'abierto' || m.estado === 'en_revision')
                  : (m.estado === 'nueva');
}
function urgente(m){
  return m.formal && (m.tipo === 'reclamo' || m.tipo === 'queja') && pendiente(m);
}

async function cargar(){
  var parciales = [];
  var items = [];
  try{
    var r = await fetch('/api/admin/portal/pqr', {credentials:'same-origin'});
    if(r.status === 403){
      parciales.push('Los PQR formales los ve Calidad · acá estás viendo sólo lo comercial.');
    } else {
      var d = await r.json();
      (d.items || []).forEach(function(p){
        items.push({id:p.id, formal:true, tipo:p.tipo, titulo:p.titulo, texto:p.descripcion,
                    cliente:p.cliente_nombre || p.cliente_id, email:p.email_cliente,
                    estado:p.estado, respuesta:p.respuesta_admin, quien:p.respondido_por,
                    fecha:p.creado_at_utc});
      });
    }
  }catch(e){ parciales.push('No se pudieron traer los PQR formales.'); }
  try{
    var r2 = await fetch('/api/admin/portal/solicitudes', {credentials:'same-origin'});
    if(r2.status === 403){
      parciales.push('Lo comercial lo ve Compras · acá estás viendo sólo los PQR formales.');
    } else {
      var d2 = await r2.json();
      (d2.items || []).forEach(function(s){
        var pn = (s.producto_nombre || '').trim();
        var tit = (_TIPO_LBL[s.tipo] || s.tipo) + (/[a-z0-9]/i.test(pn) ? (' · ' + pn) : '');
        items.push({id:s.id, formal:false, tipo:s.tipo, titulo:tit, texto:s.mensaje,
                    cliente:s.cliente_nombre || s.cliente_id, email:s.cliente_email,
                    estado:s.estado, respuesta:s.respuesta_notas, quien:s.respondido_por,
                    fecha:s.creada_at});
      });
    }
  }catch(e){ parciales.push('No se pudo traer lo comercial.'); }

  // Lo que NO se pudo traer se DICE · si no, la bandeja se lee como "no hay nada".
  var av = $('aviso-parcial');
  av.className = parciales.length ? 'aviso on' : 'aviso';
  av.textContent = parciales.join(' ');

  _ITEMS = items;
  pintarKpis();
  pintar();
}

function pintarKpis(){
  var pend = _ITEMS.filter(pendiente);
  var urg = _ITEMS.filter(urgente);
  var viejo = pend.map(function(m){ return dias(m.fecha); }).sort(function(a,b){ return b-a; })[0];
  $('kpis').innerHTML =
      '<div class="kpi"><div class="k">Sin responder</div><div class="v">' + pend.length + '</div></div>'
    + '<div class="kpi' + (urg.length ? ' alerta' : '') + '"><div class="k">Quejas y reclamos abiertos</div>'
    +   '<div class="v">' + urg.length + '</div></div>'
    + '<div class="kpi' + (viejo >= 5 ? ' alerta' : '') + '"><div class="k">El que más espera</div>'
    +   '<div class="v">' + (pend.length ? (viejo + (viejo === 1 ? ' día' : ' días')) : '-') + '</div></div>';
}

function filtrar(f){
  _FILTRO = f;
  ['pendientes','formales','comercial','todo'].forEach(function(k){
    $('f-' + k).classList.toggle('on', k === f);
  });
  pintar();
}

function pintar(){
  var lista = _ITEMS.filter(function(m){
    if(_FILTRO === 'pendientes') return pendiente(m);
    if(_FILTRO === 'formales') return m.formal;
    if(_FILTRO === 'comercial') return !m.formal;
    return true;
  });
  // Primero lo que urge, después lo que lleva más tiempo esperando · un aviso que no
  // envejece a la vista se vuelve ruido (M129).
  lista.sort(function(a, b){
    if(urgente(a) !== urgente(b)) return urgente(a) ? -1 : 1;
    if(pendiente(a) !== pendiente(b)) return pendiente(a) ? -1 : 1;
    return dias(b.fecha) - dias(a.fecha);
  });
  var box = $('lista');
  if(!lista.length){
    box.innerHTML = '<div class="vacio">No hay mensajes con este filtro.</div>';
    return;
  }
  box.innerHTML = lista.map(function(m){
    var d = dias(m.fecha);
    var cls = urgente(m) ? 'urge' : (pendiente(m) ? 'espera' : 'hecho');
    var chipTipo = m.formal
      ? '<span class="chip ' + ((m.tipo === 'reclamo' || m.tipo === 'queja') ? 'rojo' : 'violeta') + '">'
        + esc(_TIPO_LBL[m.tipo] || m.tipo) + '</span><span class="chip violeta">PQR formal</span>'
      : '<span class="chip gris">' + esc(_TIPO_LBL[m.tipo] || m.tipo) + '</span>';
    var chipEst = '<span class="chip ' + (pendiente(m) ? 'ambar' : 'verde') + '">'
      + esc(_EST_LBL[m.estado] || m.estado) + '</span>';
    return '<div class="msj ' + cls + '">'
      + '<div class="msj-top"><div style="min-width:0">'
      +   '<div class="msj-tit">' + esc(m.titulo || '(sin título)') + '</div>'
      +   '<div class="msj-cli">' + esc(m.cliente) + (m.email ? ' · ' + esc(m.email) : '') + '</div>'
      + '</div><div class="msj-edad"><div class="d">' + d + '</div>'
      +   '<div class="l">' + (d === 1 ? 'día' : 'días') + '</div></div></div>'
      + '<div class="chips">' + chipTipo + chipEst + '</div>'
      + (m.texto ? '<div class="msj-txt">' + esc(m.texto) + '</div>' : '')
      + (m.respuesta ? '<div class="resp"><b>Respondido por ' + esc(m.quien || 'EOS') + '</b><br>'
                       + esc(m.respuesta) + '</div>' : '')
      + '<div class="acc"><button class="btn" onclick="abrir(' + m.id + ',' + (m.formal ? 1 : 0) + ')">'
      +   (m.respuesta ? 'Responder de nuevo' : 'Responder') + '</button></div>'
      + '</div>';
  }).join('');
}

function abrir(id, formal){
  var m = _ITEMS.filter(function(x){ return x.id === id && x.formal === !!formal; })[0];
  if(!m) return;
  _ACTUAL = m;
  $('mo-tit').textContent = m.formal ? 'Responder PQR formal' : 'Responder';
  $('mo-ctx').textContent = m.cliente + ' · ' + (_TIPO_LBL[m.tipo] || m.tipo)
    + ' · hace ' + dias(m.fecha) + (dias(m.fecha) === 1 ? ' día' : ' días');
  $('mo-orig').textContent = (m.titulo ? m.titulo + '\n\n' : '') + (m.texto || '');
  $('mo-estado-box').style.display = m.formal ? 'block' : 'none';
  $('mo-texto').value = m.respuesta || '';
  $('mo-msg').className = 'msg';
  $('ov').classList.add('on');
}
function cerrar(){ $('ov').classList.remove('on'); _ACTUAL = null; }

async function enviar(){
  if(!_ACTUAL) return;
  var texto = $('mo-texto').value.trim();
  var btn = $('mo-btn'), msg = $('mo-msg');
  if(texto.length < 5){
    msg.className = 'msg err'; msg.textContent = 'Escribí la respuesta: el cliente la va a leer.'; return;
  }
  btn.disabled = true; btn.textContent = 'Enviando...';
  try{
    var t = await csrf();
    var url, cuerpo;
    if(_ACTUAL.formal){
      url = '/api/admin/portal/pqr/' + _ACTUAL.id;
      cuerpo = {respuesta: texto, estado: $('mo-estado').value};
    } else {
      url = '/api/admin/portal/solicitudes/' + _ACTUAL.id;
      cuerpo = {respuesta_notas: texto, estado: 'respondida'};
    }
    var r = await fetch(url, {method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(cuerpo)});
    var d = await r.json();
    if(!r.ok){ msg.className = 'msg err'; msg.textContent = d.error || ('Error ' + r.status); return; }
    cerrar();
    cargar();
  }catch(e){ msg.className = 'msg err'; msg.textContent = 'Error de red'; }
  finally{ btn.disabled = false; btn.textContent = 'Enviar respuesta'; }
}

cargar();
</script></body></html>
"""
