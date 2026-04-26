"""
admin.py — Blueprint de administración: panel, backups, eventos de seguridad.

Acceso: SOLO ADMIN_USERS (sebastian, alejandro). El resto recibe 403.
"""
import os
import secrets
import sqlite3
import string

from flask import Blueprint, jsonify, request, session, send_file, Response
from werkzeug.security import generate_password_hash

from config import (
    DB_PATH, ADMIN_USERS, COMPRAS_USERS, validate_config,
    CONTADORA_USERS, RRHH_USERS, COMPRAS_ACCESS, FINANZAS_ACCESS,
    CLIENTES_ACCESS, TECNICA_USERS, MARKETING_USERS, ANIMUS_ACCESS,
    ESPAGIRIA_ACCESS, CALIDAD_USERS, PLANTA_USERS,
)
from auth import _client_ip, _log_sec
from backup import (
    do_backup, list_backups, get_backup_path, BACKUPS_DIR,
    RETENTION_DAYS, BACKUP_INTERVAL_HOURS,
)

bp = Blueprint("admin", __name__)


def _require_admin():
    """Retorna (None, response, status) si NO admin, (user, None, None) si OK."""
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    if u not in ADMIN_USERS:
        return None, jsonify({"error": "Solo admins"}), 403
    return u, None, None


# ─── Backups ──────────────────────────────────────────────────────────────────

@bp.route("/api/admin/backups", methods=["GET"])
def admin_backups_list():
    """Lista backups disponibles + status del último."""
    u, err, code = _require_admin()
    if err:
        return err, code

    items = list_backups()

    # Trae stats del backup_log para mostrar contexto
    try:
        conn = sqlite3.connect(DB_PATH)
        recent = conn.execute(
            """SELECT id, started_at, completed_at, status, size_bytes,
                      triggered_by, error
               FROM backup_log
               ORDER BY id DESC LIMIT 20"""
        ).fetchall()
        conn.close()
        recent_list = [
            {
                "id": r[0], "started_at": r[1], "completed_at": r[2],
                "status": r[3], "size_bytes": r[4], "triggered_by": r[5],
                "error": r[6],
            } for r in recent
        ]
    except Exception:
        recent_list = []

    return jsonify({
        "backups": items,
        "recent_runs": recent_list,
        "config": {
            "retention_days": RETENTION_DAYS,
            "interval_hours": BACKUP_INTERVAL_HOURS,
            "backups_dir": BACKUPS_DIR,
        }
    })


@bp.route("/api/admin/backup-now", methods=["POST"])
def admin_backup_now():
    """Trigger manual de backup."""
    u, err, code = _require_admin()
    if err:
        return err, code

    _log_sec("backup_manual_triggered", u, _client_ip())
    result = do_backup(triggered_by=f"manual:{u}")
    # ok=True → backup creado, status 200
    # skipped=True → otro worker está haciendo backup, status 200 (no es error)
    # else → error real, status 500
    if result.get("ok") or result.get("skipped"):
        return jsonify(result), 200
    return jsonify(result), 500


@bp.route("/api/admin/backup/<path:filename>", methods=["GET"])
def admin_backup_download(filename):
    """Descarga un backup específico para off-site."""
    u, err, code = _require_admin()
    if err:
        return err, code

    path = get_backup_path(filename)
    if not path:
        return jsonify({"error": "backup no encontrado o nombre inválido"}), 404

    _log_sec("backup_downloaded", u, _client_ip(), f"file={filename}")
    return send_file(
        path,
        mimetype="application/gzip",
        as_attachment=True,
        download_name=filename,
    )


# ─── Users management ────────────────────────────────────────────────────────


def _user_groups(username):
    """Retorna la lista de grupos a los que pertenece un usuario."""
    groups = []
    if username in ADMIN_USERS:        groups.append("Admin")
    if username in CONTADORA_USERS:    groups.append("Contadora")
    if username in COMPRAS_ACCESS:     groups.append("Compras")
    if username in FINANZAS_ACCESS:    groups.append("Finanzas")
    if username in CLIENTES_ACCESS:    groups.append("Clientes")
    if username in MARKETING_USERS:    groups.append("Marketing")
    if username in ANIMUS_ACCESS:      groups.append("ANIMUS")
    if username in ESPAGIRIA_ACCESS:   groups.append("Espagiria")
    if username in TECNICA_USERS:      groups.append("Técnica")
    if username in CALIDAD_USERS:      groups.append("Calidad")
    if username in RRHH_USERS:         groups.append("RRHH")
    if username in PLANTA_USERS:       groups.append("Planta")
    return groups


def _password_source(username, conn):
    """Retorna 'db' / 'env' / 'missing' indicando dónde está la password."""
    try:
        row = conn.execute(
            "SELECT password_hash FROM users_passwords WHERE username=?",
            (username,)
        ).fetchone()
        if row and row[0]:
            return "db"
    except Exception:
        pass
    env_pwd = COMPRAS_USERS.get(username, "")
    if env_pwd and (env_pwd.startswith("pbkdf2:") or env_pwd.startswith("scrypt:")):
        return "env"
    if env_pwd:
        return "env_plaintext"   # alerta: plaintext en env var
    return "missing"


@bp.route("/api/admin/users", methods=["GET"])
def admin_users_list():
    """Lista todos los usuarios con: grupos, fuente de password, último login."""
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    out = []
    for username in sorted(COMPRAS_USERS.keys()):
        # Última vez que entró exitosamente
        last_login = None
        try:
            row = conn.execute(
                """SELECT ts FROM security_events
                   WHERE event='login_success' AND username=?
                   ORDER BY id DESC LIMIT 1""",
                (username,)
            ).fetchone()
            if row:
                last_login = row[0]
        except Exception:
            pass

        # Cuándo se cambió la password (si existe en DB)
        pwd_changed_at = None
        try:
            row = conn.execute(
                "SELECT changed_at, changed_by FROM users_passwords WHERE username=?",
                (username,)
            ).fetchone()
            if row:
                pwd_changed_at = row[0]
        except Exception:
            pass

        out.append({
            "username":       username,
            "groups":         _user_groups(username),
            "is_admin":       username in ADMIN_USERS,
            "password_source": _password_source(username, conn),
            "last_login":     last_login,
            "pwd_changed_at": pwd_changed_at,
        })

    conn.close()
    return jsonify({"users": out, "total": len(out)})


@bp.route("/api/admin/reset-password", methods=["POST"])
def admin_reset_password():
    """Resetea la password de OTRO usuario. Genera password aleatoria,
    la guarda hasheada en users_passwords, y devuelve la plaintext UNA SOLA VEZ.

    Body JSON: {"username": "<target>"}
    """
    admin_user, err, code = _require_admin()
    if err:
        return err, code

    body = request.get_json(silent=True) or {}
    target = (body.get("username") or "").strip().lower()

    if not target:
        return jsonify({"error": "Falta 'username'"}), 400

    if target not in COMPRAS_USERS:
        return jsonify({"error": f"Usuario '{target}' no existe"}), 404

    # Generar password aleatoria fuerte (12 chars, sin caracteres ambiguos)
    safe_alphabet = "".join(
        c for c in (string.ascii_letters + string.digits + "!@#%&*+=?")
        if c not in "0Oo1Il"
    )
    while True:
        new_pwd = "".join(secrets.choice(safe_alphabet) for _ in range(12))
        if (any(c.isupper() for c in new_pwd)
                and any(c.islower() for c in new_pwd)
                and any(c.isdigit() for c in new_pwd)
                and any(not c.isalnum() for c in new_pwd)):
            break

    new_hash = generate_password_hash(new_pwd, method="pbkdf2:sha256:600000")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("""
            INSERT INTO users_passwords (username, password_hash, changed_at, changed_by)
            VALUES (?, ?, datetime('now', 'utc'), ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                changed_at    = excluded.changed_at,
                changed_by    = excluded.changed_by
        """, (target, new_hash, admin_user))
        conn.commit()
        conn.close()
    except Exception as e:
        _log_sec("password_reset_db_error", admin_user, _client_ip(), str(e)[:200])
        return jsonify({"error": "Error guardando nueva password"}), 500

    _log_sec(
        "password_reset_by_admin",
        admin_user,
        _client_ip(),
        f"target={target}"
    )

    return jsonify({
        "ok": True,
        "username": target,
        "new_password": new_pwd,
        "warning": "Esta password se muestra UNA SOLA VEZ. Comunícala al "
                   "usuario por canal seguro y dile que la cambie en su "
                   "primer login."
    })


# ─── Security events ─────────────────────────────────────────────────────────


@bp.route("/api/admin/security-events", methods=["GET"])
def admin_security_events():
    """Últimos eventos de seguridad. Soporta filtros: ?event=login_failure&limit=100"""
    u, err, code = _require_admin()
    if err:
        return err, code

    event_filter = request.args.get("event", "").strip()
    try:
        limit = min(int(request.args.get("limit", "50")), 500)
    except ValueError:
        limit = 50

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if event_filter:
            rows = conn.execute(
                """SELECT id, ts, event, username, ip, user_agent, details
                   FROM security_events
                   WHERE event = ?
                   ORDER BY id DESC LIMIT ?""",
                (event_filter, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, ts, event, username, ip, user_agent, details
                   FROM security_events
                   ORDER BY id DESC LIMIT ?""",
                (limit,)
            ).fetchall()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "events": []}), 500

    out = [dict(r) for r in rows]

    # Estadísticas rápidas: conteo por evento en últimas 24h
    stats = {}
    try:
        agg = conn.execute("""
            SELECT event, COUNT(*) as n FROM security_events
            WHERE ts > datetime('now', 'utc', '-1 day')
            GROUP BY event
            ORDER BY n DESC
        """).fetchall()
        stats = {r[0]: r[1] for r in agg}
    except Exception:
        pass
    conn.close()

    return jsonify({
        "events": out,
        "total":  len(out),
        "stats_24h": stats,
    })


# ─── Config status ────────────────────────────────────────────────────────────


@bp.route("/api/admin/config-status", methods=["GET"])
def admin_config_status():
    """Status de configuración: env vars críticas y opcionales presentes/faltan."""
    u, err, code = _require_admin()
    if err:
        return err, code

    issues = validate_config()

    # Lista de env vars que deberían estar configuradas
    critical_vars = ["SECRET_KEY", "DB_PATH"]
    user_pass_vars = [f"PASS_{u.upper()}" for u in COMPRAS_USERS.keys()]
    optional_vars = [
        "FORMULA_PIN",
        "ANTHROPIC_API_KEY", "GHL_API_KEY", "GHL_LOCATION_ID",
        "SHOPIFY_TOKEN", "SHOPIFY_SHOP",
        "INSTAGRAM_TOKEN", "INSTAGRAM_USER_ID",
        "META_APP_ID", "META_APP_SECRET",
        "EMAIL_REMITENTE", "EMAIL_PASSWORD",
        "SENTRY_DSN",
    ]

    def status(name):
        val = os.environ.get(name, "")
        return {"name": name, "set": bool(val), "length": len(val) if val else 0}

    return jsonify({
        "issues":         issues,
        "critical":       [status(v) for v in critical_vars],
        "user_passwords": [status(v) for v in user_pass_vars],
        "optional":       [status(v) for v in optional_vars],
    })


# ─── Panel HTML ───────────────────────────────────────────────────────────────

_ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin — HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;font-size:14px;}
.hdr{background:#1e293b;border-bottom:1px solid #334155;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;}
.hdr h1{font-size:16px;font-weight:800;color:#fff;}
.hdr a{color:#667eea;text-decoration:none;font-size:12px;}
.tabs{background:#1e293b;border-bottom:1px solid #334155;display:flex;overflow-x:auto;padding:0 24px;position:sticky;top:48px;z-index:9;}
.tab{padding:14px 22px;font-size:13px;font-weight:600;color:#64748b;border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab:hover{color:#e2e8f0;}
.tab.active{color:#a78bfa;border-bottom-color:#7c3aed;}
.main{max-width:1200px;margin:0 auto;padding:24px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;margin-bottom:18px;}
.card h2{font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:12px;display:flex;align-items:center;gap:10px;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px;}
.kpi{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px;}
.kpi-l{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}
.kpi-v{font-size:20px;font-weight:800;color:#a78bfa;}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:700;color:#fff;background:linear-gradient(135deg,#7c3aed,#4c1d95);text-decoration:none;}
.btn:hover{filter:brightness(1.1);}
.btn:disabled{opacity:.5;cursor:wait;}
.btn-sm{padding:4px 10px;font-size:11px;}
.btn-outline{background:transparent;border:1px solid #475569;color:#94a3b8;}
.btn-warn{background:linear-gradient(135deg,#dc2626,#7f1d1d);}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;padding:8px 12px;text-align:left;background:#0f172a;border-bottom:1px solid #334155;}
td{padding:10px 12px;border-bottom:1px solid #1e293b;}
tr:hover td{background:#263348;}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;}
.badge-ok{background:#052e16;color:#34d399;}
.badge-err{background:#2d0000;color:#f87171;}
.badge-warn{background:#3a2a00;color:#fbbf24;}
.badge-info{background:#1e3a5f;color:#93c5fd;}
.badge-run{background:#1e1b4b;color:#a78bfa;}
.badge-gray{background:#0f172a;color:#94a3b8;border:1px solid #334155;}
#toast{position:fixed;top:80px;right:20px;background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:14px 20px;border-radius:10px;font-size:13px;display:none;z-index:1000;box-shadow:0 8px 24px rgba(0,0,0,0.4);max-width:400px;}
.section-sub{font-size:12px;color:#64748b;margin-top:-8px;margin-bottom:16px;line-height:1.5;}
.tab-panel{display:none;}
.tab-panel.active{display:block;}

/* Modal */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:100;align-items:center;justify-content:center;}
.modal-bg.show{display:flex;}
.modal{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:28px;max-width:480px;width:92%;}
.modal h3{font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:8px;}
.modal-msg{font-size:13px;color:#94a3b8;margin-bottom:18px;line-height:1.5;}
.modal-result{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px;margin:12px 0;font-family:'Cascadia Code',Consolas,monospace;font-size:14px;color:#34d399;text-align:center;letter-spacing:0.05em;word-break:break-all;}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:14px;}
</style>
</head>
<body>
<div class="hdr">
  <h1>&#x1F510; Panel de Administracion</h1>
  <a href="/hub">&#x2190; Volver al Hub</a>
</div>

<div class="tabs">
  <button class="tab active" data-tab="backups" onclick="switchTab('backups')">&#x1F4C0; Backups</button>
  <button class="tab" data-tab="users" onclick="switchTab('users')">&#x1F465; Usuarios</button>
  <button class="tab" data-tab="security" onclick="switchTab('security')">&#x1F6E1; Eventos de Seguridad</button>
  <button class="tab" data-tab="config" onclick="switchTab('config')">&#x2699; Config Status</button>
</div>

<div class="main">

<!-- ─── TAB BACKUPS ─── -->
<div id="tab-backups" class="tab-panel active">
  <div class="card">
    <h2>&#x1F4C0; Backups de Base de Datos</h2>
    <div class="section-sub">
      Backups automaticos cada 23h, 7 dias de retencion. Descarga el mas reciente regularmente
      para tener una copia <strong>fuera de Render</strong> — eso te protege si el disco se corrompe.
    </div>
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-l">Disponibles</div><div class="kpi-v" id="kpi-count">-</div></div>
      <div class="kpi"><div class="kpi-l">Espacio total</div><div class="kpi-v" id="kpi-size">-</div></div>
      <div class="kpi"><div class="kpi-l">Ultimo backup</div><div class="kpi-v" id="kpi-last" style="font-size:13px;">-</div></div>
      <div class="kpi"><div class="kpi-l">Retencion</div><div class="kpi-v" style="font-size:14px;" id="kpi-ret">-</div></div>
    </div>
    <button class="btn" id="btn-backup" onclick="triggerBackup()">
      <span id="btn-label">&#x26A1; Hacer backup ahora</span>
    </button>
    <div style="margin-top:24px;">
      <table>
        <thead><tr><th>Archivo</th><th>Fecha (UTC)</th><th>Tamano</th><th>Accion</th></tr></thead>
        <tbody id="tbody-backups"><tr><td colspan="4" style="text-align:center;color:#64748b;padding:30px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <h2>&#x1F4DC; Historial de ejecuciones</h2>
    <div class="section-sub">Audita backups exitosos y fallidos.</div>
    <table>
      <thead><tr><th>ID</th><th>Inicio (UTC)</th><th>Estado</th><th>Trigger</th><th>Tamano</th><th>Error</th></tr></thead>
      <tbody id="tbody-runs"><tr><td colspan="6" style="text-align:center;color:#64748b;padding:30px;">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ─── TAB USERS ─── -->
<div id="tab-users" class="tab-panel">
  <div class="card">
    <h2>&#x1F465; Usuarios del sistema</h2>
    <div class="section-sub">
      Aqui ves a los 19 usuarios con sus grupos, fuente de password (DB = cambiada por el user, ENV = de Render),
      y ultimo login. Si alguien olvida su password, presiona <strong>Resetear</strong> y comparte
      la nueva contrasena 1-on-1.
    </div>
    <table>
      <thead>
        <tr>
          <th>Usuario</th><th>Grupos</th><th>Password</th>
          <th>Ult. login</th><th>Pwd cambiada</th><th>Accion</th>
        </tr>
      </thead>
      <tbody id="tbody-users"><tr><td colspan="6" style="text-align:center;color:#64748b;padding:30px;">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ─── TAB SECURITY ─── -->
<div id="tab-security" class="tab-panel">
  <div class="card">
    <h2>&#x1F6E1; Estadisticas (ultimas 24h)</h2>
    <div class="section-sub">Conteo de eventos por tipo en las ultimas 24 horas. Picos sospechosos = investigar.</div>
    <div class="kpi-row" id="kpi-stats">
      <div class="kpi"><div class="kpi-l">Cargando...</div><div class="kpi-v">-</div></div>
    </div>
  </div>
  <div class="card">
    <h2>&#x1F50D; Eventos de seguridad</h2>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px;">
      <label style="font-size:11px;color:#94a3b8;">Filtrar:</label>
      <select id="filter-event" onchange="loadSecurityEvents()" style="background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:6px 10px;border-radius:8px;font-size:12px;">
        <option value="">Todos los eventos</option>
        <option value="login_success">login_success</option>
        <option value="login_failure">login_failure</option>
        <option value="password_changed">password_changed</option>
        <option value="password_change_failed">password_change_failed</option>
        <option value="password_reset_by_admin">password_reset_by_admin</option>
        <option value="csrf_blocked">csrf_blocked</option>
        <option value="backup_manual_triggered">backup_manual_triggered</option>
        <option value="backup_downloaded">backup_downloaded</option>
      </select>
      <button class="btn btn-sm btn-outline" onclick="loadSecurityEvents()">&#x21BB; Refrescar</button>
    </div>
    <table>
      <thead>
        <tr><th>ID</th><th>Timestamp UTC</th><th>Evento</th><th>Usuario</th><th>IP</th><th>Detalles</th></tr>
      </thead>
      <tbody id="tbody-security"><tr><td colspan="6" style="text-align:center;color:#64748b;padding:30px;">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ─── TAB CONFIG ─── -->
<div id="tab-config" class="tab-panel">
  <div class="card">
    <h2>&#x26A0; Issues de configuracion</h2>
    <div class="section-sub">
      Issues detectados por <code>validate_config()</code> al startup.
      <strong>Cero CRITICAL/HIGH = todo OK.</strong>
    </div>
    <div id="config-issues" style="margin-top:8px;">Cargando...</div>
  </div>
  <div class="card">
    <h2>&#x1F511; Variables de entorno</h2>
    <div class="section-sub">
      Solo se muestra si la variable esta seteada y su longitud — nunca el valor.
      Las criticas DEBEN estar; las de PASS_USER son las contrasenas individuales;
      las opcionales habilitan integraciones.
    </div>
    <h3 style="color:#a78bfa;font-size:13px;margin-top:16px;margin-bottom:8px;">Criticas</h3>
    <table><tbody id="tbody-config-critical"><tr><td>Cargando...</td></tr></tbody></table>
    <h3 style="color:#a78bfa;font-size:13px;margin-top:16px;margin-bottom:8px;">Passwords por usuario</h3>
    <table><tbody id="tbody-config-users"><tr><td>Cargando...</td></tr></tbody></table>
    <h3 style="color:#a78bfa;font-size:13px;margin-top:16px;margin-bottom:8px;">Opcionales (integraciones)</h3>
    <table><tbody id="tbody-config-optional"><tr><td>Cargando...</td></tr></tbody></table>
  </div>
</div>

</div>

<div id="toast"></div>

<!-- Modal de password reseteada -->
<div id="modal-bg" class="modal-bg">
  <div class="modal">
    <h3 id="modal-title">Password reseteada</h3>
    <div class="modal-msg" id="modal-msg"></div>
    <div class="modal-result" id="modal-result"></div>
    <div class="modal-msg" style="font-size:11px;color:#fbbf24;">
      &#x26A0; Esta password se muestra UNA SOLA VEZ. Comunicala al usuario por canal seguro
      y dile que la cambie en su primer login.
    </div>
    <div class="modal-actions">
      <button class="btn btn-outline" onclick="copyResult()">Copiar</button>
      <button class="btn" onclick="closeModal()">Cerrar</button>
    </div>
  </div>
</div>

<script>
// ── Tabs ──────────────────────────────────────────────────────────────────────
const _loaded = {backups:false, users:false, security:false, config:false};
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (!_loaded[name]) {
    _loaded[name] = true;
    if (name === 'backups')  loadBackups();
    if (name === 'users')    loadUsers();
    if (name === 'security') loadSecurityEvents();
    if (name === 'config')   loadConfigStatus();
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, kind) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.borderColor = kind === 'ok' ? '#34d399' : (kind === 'warn' ? '#fbbf24' : '#f87171');
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 5000);
}

// ── BACKUPS ───────────────────────────────────────────────────────────────────
async function loadBackups() {
  const r = await fetch('/api/admin/backups');
  if (!r.ok) {
    document.getElementById('tbody-backups').innerHTML = '<tr><td colspan="4" style="color:#f87171;text-align:center;padding:20px;">Error '+r.status+'</td></tr>';
    return;
  }
  const data = await r.json();
  const items = data.backups || [];
  document.getElementById('kpi-count').textContent = items.length;
  document.getElementById('kpi-size').textContent = items.length
    ? (items.reduce((a,b)=>a+(b.size_bytes||0),0)/1024/1024).toFixed(1) + ' MB' : '0 MB';
  document.getElementById('kpi-last').textContent = items.length
    ? items[0].modified.replace('T',' ').replace('Z','') : 'nunca';
  document.getElementById('kpi-ret').textContent = (data.config && data.config.retention_days || 7) + ' dias';
  if (!items.length) {
    document.getElementById('tbody-backups').innerHTML = '<tr><td colspan="4" style="text-align:center;color:#64748b;padding:20px;">Sin backups aun.</td></tr>';
  } else {
    document.getElementById('tbody-backups').innerHTML = items.map(b =>
      `<tr><td style="font-family:monospace;font-size:12px;color:#cbd5e1;">${b.filename}</td>
       <td style="color:#94a3b8;">${b.modified.replace('T',' ').replace('Z','')}</td>
       <td><span class="badge badge-ok">${b.size_mb} MB</span></td>
       <td><a href="/api/admin/backup/${encodeURIComponent(b.filename)}" class="btn btn-sm" download>&#x1F4E5; Descargar</a></td></tr>`
    ).join('');
  }
  const runs = data.recent_runs || [];
  if (!runs.length) {
    document.getElementById('tbody-runs').innerHTML = '<tr><td colspan="6" style="text-align:center;color:#64748b;padding:20px;">Sin ejecuciones aun.</td></tr>';
  } else {
    document.getElementById('tbody-runs').innerHTML = runs.map(r => {
      const cls = r.status === 'ok' ? 'badge-ok' : (r.status === 'error' ? 'badge-err' : 'badge-run');
      const size = r.size_bytes ? (r.size_bytes/1024/1024).toFixed(1) + ' MB' : '-';
      const err = r.error ? `<span style="color:#f87171;font-size:11px;">${r.error}</span>` : '-';
      return `<tr><td>${r.id}</td><td style="color:#94a3b8;">${(r.started_at||'').replace('T',' ').replace('Z','')}</td>
        <td><span class="badge ${cls}">${r.status}</span></td>
        <td style="font-size:12px;color:#94a3b8;">${r.triggered_by || ''}</td>
        <td>${size}</td><td>${err}</td></tr>`;
    }).join('');
  }
}

async function triggerBackup() {
  const btn = document.getElementById('btn-backup');
  const lbl = document.getElementById('btn-label');
  btn.disabled = true;
  lbl.textContent = '⏳ Haciendo backup...';
  try {
    const r = await fetch('/api/admin/backup-now', {method:'POST', headers:{'Content-Type':'application/json'}});
    const data = await r.json();
    if (r.ok && data.ok) { toast('Backup creado: ' + data.filename, 'ok'); loadBackups(); }
    else toast('Error: ' + (data.error || 'desconocido'), 'err');
  } catch (e) { toast('Error de red: ' + e.message, 'err'); }
  finally { btn.disabled = false; lbl.textContent = '⚡ Hacer backup ahora'; }
}

// ── USERS ─────────────────────────────────────────────────────────────────────
function _pwdBadge(src) {
  if (src === 'db')             return '<span class="badge badge-ok">DB (cambiada)</span>';
  if (src === 'env')            return '<span class="badge badge-info">ENV (Render)</span>';
  if (src === 'env_plaintext')  return '<span class="badge badge-err">PLAINTEXT</span>';
  return '<span class="badge badge-err">SIN CONFIG</span>';
}
async function loadUsers() {
  const r = await fetch('/api/admin/users');
  if (!r.ok) {
    document.getElementById('tbody-users').innerHTML = '<tr><td colspan="6" style="color:#f87171;">Error</td></tr>';
    return;
  }
  const data = await r.json();
  document.getElementById('tbody-users').innerHTML = (data.users || []).map(u => {
    const groups = (u.groups || []).map(g => `<span class="badge badge-gray">${g}</span>`).join(' ');
    const last = u.last_login ? u.last_login.replace('T',' ').replace('Z','') : '<span style="color:#64748b;">nunca</span>';
    const changed = u.pwd_changed_at ? u.pwd_changed_at.replace('T',' ').replace('Z','') : '<span style="color:#64748b;">—</span>';
    const adminTag = u.is_admin ? ' <span class="badge badge-warn">ADMIN</span>' : '';
    return `<tr>
      <td><strong style="color:#e2e8f0;">${u.username}</strong>${adminTag}</td>
      <td style="display:flex;gap:4px;flex-wrap:wrap;">${groups || '<span style="color:#64748b;">—</span>'}</td>
      <td>${_pwdBadge(u.password_source)}</td>
      <td style="font-size:11px;color:#94a3b8;">${last}</td>
      <td style="font-size:11px;color:#94a3b8;">${changed}</td>
      <td><button class="btn btn-sm btn-warn" onclick="resetPassword('${u.username}')">&#x1F511; Resetear</button></td>
    </tr>`;
  }).join('');
}

async function resetPassword(username) {
  if (!confirm('¿Resetear la password de "' + username + '"?\\n\\nSe generará una password aleatoria que verás UNA SOLA VEZ. Tienes que comunicársela al usuario.')) return;
  try {
    const r = await fetch('/api/admin/reset-password', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username: username})
    });
    const data = await r.json();
    if (r.ok && data.ok) {
      document.getElementById('modal-title').textContent = 'Password reseteada para ' + data.username;
      document.getElementById('modal-msg').textContent = 'Comparte esta password con el usuario por canal seguro:';
      document.getElementById('modal-result').textContent = data.new_password;
      document.getElementById('modal-bg').classList.add('show');
      loadUsers();
    } else {
      toast('Error: ' + (data.error || 'desconocido'), 'err');
    }
  } catch (e) { toast('Error: ' + e.message, 'err'); }
}

function copyResult() {
  const text = document.getElementById('modal-result').textContent;
  navigator.clipboard.writeText(text).then(
    () => toast('Password copiada al portapapeles', 'ok'),
    () => toast('No se pudo copiar', 'err')
  );
}
function closeModal() {
  document.getElementById('modal-bg').classList.remove('show');
  document.getElementById('modal-result').textContent = '';
}
document.getElementById('modal-bg').addEventListener('click', e => {
  if (e.target.id === 'modal-bg') closeModal();
});

// ── SECURITY ──────────────────────────────────────────────────────────────────
async function loadSecurityEvents() {
  const filter = document.getElementById('filter-event').value;
  const url = '/api/admin/security-events' + (filter ? '?event=' + encodeURIComponent(filter) + '&limit=100' : '?limit=100');
  const r = await fetch(url);
  if (!r.ok) {
    document.getElementById('tbody-security').innerHTML = '<tr><td colspan="6" style="color:#f87171;">Error</td></tr>';
    return;
  }
  const data = await r.json();
  // Stats KPIs
  const stats = data.stats_24h || {};
  const keys = Object.keys(stats);
  if (!keys.length) {
    document.getElementById('kpi-stats').innerHTML = '<div class="kpi"><div class="kpi-l">Sin eventos</div><div class="kpi-v" style="font-size:14px;">en las ultimas 24h</div></div>';
  } else {
    document.getElementById('kpi-stats').innerHTML = keys.map(k => {
      const isErr = /failure|blocked|error|csrf/i.test(k);
      return `<div class="kpi"><div class="kpi-l">${k}</div><div class="kpi-v" style="color:${isErr ? '#f87171' : '#34d399'};">${stats[k]}</div></div>`;
    }).join('');
  }
  // Lista
  const events = data.events || [];
  if (!events.length) {
    document.getElementById('tbody-security').innerHTML = '<tr><td colspan="6" style="text-align:center;color:#64748b;padding:20px;">Sin eventos.</td></tr>';
  } else {
    document.getElementById('tbody-security').innerHTML = events.map(e => {
      const isErr = /failure|blocked|error/i.test(e.event);
      const evtClass = isErr ? 'badge-err' : (/success|changed/i.test(e.event) ? 'badge-ok' : 'badge-info');
      return `<tr>
        <td style="color:#64748b;">${e.id}</td>
        <td style="font-size:11px;color:#94a3b8;">${(e.ts||'').replace('T',' ').replace('Z','')}</td>
        <td><span class="badge ${evtClass}">${e.event}</span></td>
        <td><strong>${e.username || '-'}</strong></td>
        <td style="font-size:12px;color:#94a3b8;font-family:monospace;">${e.ip || '-'}</td>
        <td style="font-size:11px;color:#94a3b8;">${e.details || ''}</td>
      </tr>`;
    }).join('');
  }
}

// ── CONFIG ────────────────────────────────────────────────────────────────────
async function loadConfigStatus() {
  const r = await fetch('/api/admin/config-status');
  if (!r.ok) {
    document.getElementById('config-issues').innerHTML = '<div style="color:#f87171;">Error '+r.status+'</div>';
    return;
  }
  const data = await r.json();
  const issues = data.issues || [];
  if (!issues.length) {
    document.getElementById('config-issues').innerHTML = '<div class="badge badge-ok" style="padding:8px 16px;font-size:13px;">&#x2705; Sin issues — todo configurado correctamente.</div>';
  } else {
    document.getElementById('config-issues').innerHTML = issues.map(i => {
      const cls = i.severity === 'CRITICAL' ? 'badge-err' : (i.severity === 'HIGH' ? 'badge-err' : (i.severity === 'MEDIUM' ? 'badge-warn' : 'badge-info'));
      return `<div style="background:#0f172a;border:1px solid #334155;border-left:3px solid ${i.severity==='CRITICAL'?'#dc2626':(i.severity==='HIGH'?'#dc2626':(i.severity==='MEDIUM'?'#fbbf24':'#3b82f6'))};border-radius:8px;padding:12px 14px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
          <span class="badge ${cls}">${i.severity}</span>
          <strong style="color:#e2e8f0;font-size:13px;">${i.code}</strong>
        </div>
        <div style="font-size:12px;color:#cbd5e1;line-height:1.5;">${i.msg}</div>
      </div>`;
    }).join('');
  }
  const renderRow = (v) => {
    const status = v.set
      ? `<span class="badge badge-ok">SET (${v.length} chars)</span>`
      : '<span class="badge badge-err">FALTA</span>';
    return `<tr><td style="font-family:monospace;color:#cbd5e1;">${v.name}</td><td style="text-align:right;">${status}</td></tr>`;
  };
  document.getElementById('tbody-config-critical').innerHTML = (data.critical || []).map(renderRow).join('');
  document.getElementById('tbody-config-users').innerHTML = (data.user_passwords || []).map(renderRow).join('');
  document.getElementById('tbody-config-optional').innerHTML = (data.optional || []).map(renderRow).join('');
}

// Init
loadBackups();
</script>
</body>
</html>"""


@bp.route("/admin", methods=["GET"])
def admin_panel():
    """Panel HTML de administración."""
    u = session.get("compras_user", "")
    if not u:
        return Response("Login requerido", status=401)
    if u not in ADMIN_USERS:
        return Response("<h1>403</h1><p>Solo admins.</p><a href='/hub'>Volver</a>",
                        status=403, mimetype="text/html")
    return Response(_ADMIN_HTML, mimetype="text/html")
