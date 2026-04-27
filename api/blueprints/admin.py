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


# ─── Test SMTP: envía un correo de prueba con PDF demo ────────────────────────

@bp.route("/api/admin/test-email", methods=["POST"])
def admin_test_email():
    """Envía un correo de prueba al destinatario indicado.

    Body JSON: {"destinatario": "email@dominio.com"}
       Si no se especifica, usa EMAIL_REMITENTE (te lo manda a ti mismo).

    Genera un PDF demo (CE-TEST-0000) y lo adjunta para validar:
      1. SMTP configurado y credenciales correctas
      2. PDF generator funcionando
      3. Email llega con HTML + adjunto

    Devuelve:
      200 OK    si se envió (revisar bandeja del destinatario)
      503       si EMAIL_REMITENTE/EMAIL_PASSWORD no están seteados
      502       si SMTP rechaza credenciales o no puede entregar
      500       error inesperado (PDF generator, etc.)
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    body = request.get_json(silent=True) or {}
    destinatario = (body.get('destinatario') or '').strip()
    # 'animus' o 'espagiria' — para probar ambos formatos del PDF
    empresa_test = (body.get('empresa') or 'espagiria').strip().lower()
    if 'animus' in empresa_test:
        empresa_test = 'animus'
    else:
        empresa_test = 'espagiria'

    # Probar primero la config SMTP
    try:
        import sys
        from pathlib import Path
        # notificaciones.py está en la raíz del repo, no en api/
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from notificaciones import SistemaNotificaciones
    except Exception as e:
        return jsonify({'error': 'No se pudo cargar SistemaNotificaciones', 'detalle': str(e)}), 500

    sn = SistemaNotificaciones()
    if not sn.email_remitente or not sn.contraseña:
        return jsonify({
            'error': 'SMTP no configurado',
            'detalle': 'Faltan EMAIL_REMITENTE y/o EMAIL_PASSWORD en variables de entorno.',
            'pasos': [
                '1) Genera App Password en https://myaccount.google.com/apppasswords',
                '2) Render dashboard → tu servicio → Environment → Add Environment Variable',
                '3) EMAIL_REMITENTE = facturasespagirialaboratorio@gmail.com',
                '4) EMAIL_PASSWORD = (la app password de 16 chars sin espacios)',
                '5) Save Changes → Render redeploya solo',
                '6) Vuelve a probar /api/admin/test-email',
            ],
            'env_status': {
                'EMAIL_REMITENTE': 'set' if sn.email_remitente else 'MISSING',
                'EMAIL_PASSWORD':  'set' if sn.contraseña else 'MISSING',
                'SMTP_SERVER':     sn.smtp_server,
                'SMTP_PORT':       sn.smtp_port,
            }
        }), 503

    # Si no especificó destinatario, mandárselo a sí mismo (al remitente)
    if not destinatario:
        destinatario = sn.email_remitente
    if '@' not in destinatario:
        return jsonify({'error': 'Destinatario inválido'}), 400

    # Generar PDF demo
    try:
        import sys
        from pathlib import Path
        api_dir = Path(__file__).resolve().parents[1]  # api/
        if str(api_dir) not in sys.path:
            sys.path.insert(0, str(api_dir))
        from comprobante_pago import generar_comprobante_egreso_pdf
        from datetime import datetime as _dt
        pdf_bytes = generar_comprobante_egreso_pdf(
            numero_ce='CE-TEST-0000',
            fecha_pago=_dt.now(),
            beneficiario={
                'nombre': 'PRUEBA SMTP — Test Influencer',
                'cedula': '00000000',
                'banco': 'Bancolombia',
                'cuenta': '0000000000',
                'tipo_cuenta': 'Ahorros',
                'ciudad': 'Cali',
            },
            items=[{
                'descripcion': 'Correo de prueba — validación de configuración SMTP',
                'fecha': _dt.now().strftime('%Y-%m-%d'),
                'cantidad': 1,
                'valor_unit': 100000,
            }],
            aplicar_retefuente=False,
            aplicar_retica=False,
            aplicar_iva=False,
            medio_pago='N/A — prueba',
            observaciones=f'Test enviado por {u} desde /admin',
            pagado_por=u,
            empresa_clave=empresa_test,
        )
    except Exception as e:
        import traceback
        return jsonify({
            'error': 'Falló generación de PDF demo',
            'detalle': str(e),
            'traceback': traceback.format_exc()[-800:]
        }), 500

    # Enviar el correo (sincrónico para que la respuesta indique éxito/fallo real)
    try:
        ok = sn.enviar_comprobante_egreso(
            destinatario=destinatario,
            numero_ce='CE-TEST-0000',
            beneficiario='PRUEBA SMTP',
            total_pagado=100000,
            pdf_bytes=pdf_bytes,
            fecha_emision=_dt.now().strftime('%Y-%m-%d'),
            numero_oc='OC-TEST-0000',
            empresa='ANIMUS Lab' if empresa_test == 'animus' else 'Espagiria',
        )
    except Exception as e:
        return jsonify({'error': 'Excepción al enviar', 'detalle': str(e)}), 500

    if not ok:
        return jsonify({
            'error': 'SMTP rechazó el envío',
            'detalle': (
                'Las credenciales se cargaron pero Gmail/SMTP rechazó el envío. '
                'Causas comunes: App Password incorrecta, 2FA deshabilitado, '
                'la cuenta tiene "Less secure apps" off, o el remitente no '
                'coincide con la cuenta autenticada. Revisa los logs de Render.'
            ),
            'remitente': sn.email_remitente,
            'destinatario': destinatario,
            'smtp_server': f'{sn.smtp_server}:{sn.smtp_port}',
        }), 502

    _log_sec(u, _client_ip(), 'admin_test_email', f'destinatario={destinatario}')

    return jsonify({
        'ok': True,
        'mensaje': 'Correo de prueba enviado',
        'remitente': sn.email_remitente,
        'destinatario': destinatario,
        'asunto': 'Comprobante de pago CE-TEST-0000 — Espagiria',
        'verificacion': [
            f'1. Revisa la bandeja de {destinatario} (también la carpeta Spam)',
            '2. El correo trae un PDF adjunto (CE-TEST-0000.pdf)',
            '3. El PDF debe abrir y mostrar el logo HHA + datos demo',
            '4. Si todo OK, el sistema está listo para enviar comprobantes reales',
        ],
    })


# ─── Diagnóstico: tipos de material en maestro_mps ────────────────────────────

@bp.route("/api/admin/debug-solicitud/<numero>", methods=["GET"])
def admin_debug_solicitud(numero):
    """Devuelve los items RAW de una solicitud para depurar.

    Útil cuando el modal muestra cantidades raras y queremos ver qué hay
    realmente en la DB sin transformaciones del frontend.
    """
    u, err, code = _require_admin()
    if err:
        return err, code
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    sol = c.execute(
        "SELECT numero, fecha, estado, observaciones, numero_oc, categoria FROM solicitudes_compra WHERE numero=?",
        (numero.upper(),)
    ).fetchone()
    if not sol:
        return jsonify({'error': 'Solicitud no encontrada', 'numero': numero}), 404
    items = c.execute(
        """SELECT id, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion
           FROM solicitudes_compra_items WHERE numero=?""",
        (numero.upper(),)
    ).fetchall()
    conn.close()
    return jsonify({
        'solicitud': dict(sol),
        'items_raw': [dict(i) for i in items],
        'count': len(items),
        'items_con_cantidad_cero': sum(1 for i in items if (i['cantidad_g'] or 0) <= 0),
    })


@bp.route("/api/admin/stock-mp-diagnostico", methods=["GET"])
def admin_stock_mp_diagnostico():
    """Diagnóstico de por qué un MP aparece con stock 0.

    Query: ?codigos=COD1,COD2,COD3  o  ?nombres=GLICERINA,ALOE
    Devuelve para cada uno:
      - en_maestro_mps: si existe en el catálogo
      - movimientos_count: cuántos movimientos hay
      - movimientos_match_por: 'codigo' / 'nombre' / 'no_match'
      - stock_total_g: suma calculada
      - ultimo_movimiento: fecha
      - sugerencia: qué hacer
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    codigos = (request.args.get('codigos') or '').strip()
    nombres = (request.args.get('nombres') or '').strip()
    if not codigos and not nombres:
        return jsonify({'error': 'Pasa ?codigos= o ?nombres= separados por coma'}), 400

    cods = [x.strip() for x in codigos.split(',') if x.strip()] if codigos else []
    noms = [x.strip() for x in nombres.split(',') if x.strip()] if nombres else []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    resultados = []
    for cod in cods:
        info = {'codigo_mp': cod, 'busqueda_por': 'codigo'}
        # ¿existe en maestro?
        r = c.execute(
            "SELECT codigo_mp, nombre_comercial, proveedor FROM maestro_mps WHERE codigo_mp=?",
            (cod,)
        ).fetchone()
        if r:
            info['en_maestro_mps'] = True
            info['nombre_comercial'] = r['nombre_comercial']
            info['proveedor_catalogo'] = r['proveedor']
        else:
            info['en_maestro_mps'] = False
        # ¿movimientos por código?
        r2 = c.execute("""SELECT COUNT(*) as n,
                          COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) as stock,
                          MAX(fecha) as ultimo
                          FROM movimientos WHERE material_id=?""", (cod,)).fetchone()
        info['movimientos_count'] = r2['n'] if r2 else 0
        info['stock_total_g'] = float(r2['stock'] or 0) if r2 else 0
        info['ultimo_movimiento'] = r2['ultimo'] if r2 else None
        if info['movimientos_count'] > 0:
            info['movimientos_match_por'] = 'codigo'
        else:
            # Fallback por nombre del catálogo si lo tenemos
            nm = info.get('nombre_comercial')
            if nm:
                r3 = c.execute("""SELECT COUNT(*) as n,
                                  COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) as stock
                                  FROM movimientos WHERE UPPER(TRIM(material_nombre))=UPPER(TRIM(?))""", (nm,)).fetchone()
                if r3 and r3['n'] > 0:
                    info['movimientos_count'] = r3['n']
                    info['stock_total_g'] = float(r3['stock'] or 0)
                    info['movimientos_match_por'] = 'nombre'
                else:
                    info['movimientos_match_por'] = 'no_match'
            else:
                info['movimientos_match_por'] = 'no_match'
        # Sugerencia
        if not info['en_maestro_mps']:
            info['sugerencia'] = 'Código NO está en catálogo maestro_mps. Crear primero el item en /planta → Catálogo MPs.'
        elif info['movimientos_count'] == 0:
            info['sugerencia'] = 'Ítem existe en catálogo pero NUNCA se registró entrada de stock. Hacer carga inicial en /planta → Movimientos (Entrada inicial).'
        elif info['stock_total_g'] <= 0:
            info['sugerencia'] = f'Tuvo {info["movimientos_count"]} movimientos pero el balance es 0 o negativo (más salidas que entradas). Revisar si falta registrar una compra reciente.'
        else:
            info['sugerencia'] = f'Stock real: {info["stock_total_g"]}g. Si el modal muestra 0, refresca con Ctrl+Shift+R.'
        resultados.append(info)

    for nom in noms:
        info = {'nombre': nom, 'busqueda_por': 'nombre'}
        r = c.execute("""SELECT codigo_mp, nombre_comercial, proveedor FROM maestro_mps
                         WHERE UPPER(nombre_comercial) LIKE UPPER(?) LIMIT 5""",
                      (f'%{nom}%',)).fetchall()
        info['matches_catalogo'] = [dict(x) for x in r]
        r2 = c.execute("""SELECT COUNT(*) as n,
                          COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) as stock,
                          MAX(fecha) as ultimo
                          FROM movimientos
                          WHERE UPPER(material_nombre) LIKE UPPER(?)""", (f'%{nom}%',)).fetchone()
        info['movimientos_count'] = r2['n'] if r2 else 0
        info['stock_total_g'] = float(r2['stock'] or 0) if r2 else 0
        info['ultimo_movimiento'] = r2['ultimo'] if r2 else None
        resultados.append(info)

    conn.close()
    return jsonify({'resultados': resultados, 'total': len(resultados)})


@bp.route("/api/admin/mps-proveedores-status", methods=["GET"])
def admin_mps_proveedores_status():
    """Diagnóstico: qué MPs tienen proveedor asignado y cuáles no.

    El campo maestro_mps.proveedor lo lee la auto-generación de OCs sugeridas
    para agrupar el déficit. Si está vacío, las solicitudes salen con
    'Sin asignar' como proveedor y el user tiene que corregir a mano.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Resumen por proveedor
    rows = c.execute("""
        SELECT COALESCE(NULLIF(TRIM(proveedor), ''), '(SIN PROVEEDOR)') AS prov,
               COUNT(*) AS total
        FROM maestro_mps
        WHERE activo = 1
        GROUP BY prov
        ORDER BY (CASE WHEN prov='(SIN PROVEEDOR)' THEN 0 ELSE 1 END), total DESC, prov
    """).fetchall()
    por_proveedor = [{'proveedor': r['prov'], 'total': r['total']} for r in rows]
    total_activos = sum(r['total'] for r in por_proveedor)
    sin_proveedor_count = next(
        (r['total'] for r in por_proveedor if r['proveedor'] == '(SIN PROVEEDOR)'), 0
    )

    # Lista detallada de los SIN proveedor
    rows_sin = c.execute("""
        SELECT codigo_mp, nombre_comercial, COALESCE(tipo,'') as tipo
        FROM maestro_mps
        WHERE activo = 1
          AND (proveedor IS NULL OR TRIM(proveedor) = '')
        ORDER BY codigo_mp LIMIT 200
    """).fetchall()
    sin_proveedor_lista = [
        {'codigo_mp': r['codigo_mp'], 'nombre': r['nombre_comercial'], 'tipo': r['tipo']}
        for r in rows_sin
    ]

    # Lista de proveedores existentes (para que la UI ofrezca dropdown)
    provs_existentes = [
        r['prov'] for r in por_proveedor if r['prov'] != '(SIN PROVEEDOR)'
    ]

    # Cross-check con MPs en déficit real (los que importan operacionalmente)
    # Esto requiere correr la lógica de Programación, lo evitamos aquí para
    # mantener este endpoint rápido. El user lo puede ver en /compras banner.

    conn.close()
    return jsonify({
        'total_activos': total_activos,
        'con_proveedor': total_activos - sin_proveedor_count,
        'sin_proveedor': sin_proveedor_count,
        'pct_cobertura': round(
            (total_activos - sin_proveedor_count) / total_activos * 100, 1
        ) if total_activos else 0,
        'por_proveedor': por_proveedor,
        'sin_proveedor_lista': sin_proveedor_lista,
        'proveedores_existentes': provs_existentes,
    })


@bp.route("/api/admin/mps-asignar-proveedor", methods=["POST"])
def admin_mps_asignar_proveedor():
    """Asigna proveedor a una MP. Body: {codigo_mp, proveedor}."""
    u, err, code = _require_admin()
    if err:
        return err, code
    d = request.get_json(silent=True) or {}
    codigo = (d.get('codigo_mp') or '').strip()
    proveedor = (d.get('proveedor') or '').strip()
    if not codigo:
        return jsonify({'error': 'codigo_mp requerido'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?",
              (proveedor, codigo))
    n = c.rowcount or 0
    conn.commit()
    conn.close()
    if n == 0:
        return jsonify({'error': f"No se encontró MP '{codigo}'"}), 404
    _log_sec(u, _client_ip(),
             "admin_mp_asignar_proveedor",
             f"codigo={codigo} proveedor={proveedor}")
    return jsonify({'ok': True, 'codigo_mp': codigo, 'proveedor': proveedor})


@bp.route("/api/admin/tipos-mp-stats", methods=["GET"])
def admin_tipos_mp_stats():
    """Cuenta items en maestro_mps agrupados por tipo_material.

    Útil para diagnosticar por qué la programación cíclica de E&E aparece
    vacía: si no hay items con tipo='Envase Secundario' (exacto), la rotación
    no tiene de dónde sacar los 3 ítems de la semana.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Conteo por tipo (incluye nulos/vacíos)
    rows = c.execute("""
        SELECT COALESCE(NULLIF(TRIM(tipo_material), ''), '(sin tipo)') AS tipo,
               COUNT(*) AS total,
               SUM(CASE WHEN activo=1 THEN 1 ELSE 0 END) AS activos,
               SUM(CASE WHEN COALESCE(stock_minimo,0) > 0 THEN 1 ELSE 0 END) AS con_min
        FROM maestro_mps
        GROUP BY tipo
        ORDER BY total DESC
    """).fetchall()

    # Primeros 5 ejemplos por tipo (para verificar nombres exactos)
    ejemplos = {}
    for r in rows:
        c.execute("""SELECT codigo_mp, nombre_comercial
                     FROM maestro_mps
                     WHERE COALESCE(NULLIF(TRIM(tipo_material),''),'(sin tipo)')=?
                       AND activo=1
                     ORDER BY codigo_mp LIMIT 5""", (r["tipo"],))
        ejemplos[r["tipo"]] = [
            {"codigo": e["codigo_mp"], "nombre": e["nombre_comercial"]}
            for e in c.fetchall()
        ]

    conn.close()

    return jsonify({
        "tipos": [dict(r) for r in rows],
        "ejemplos": ejemplos,
        "esperados_e_e": ["Envase Primario", "Envase Secundario", "Empaque"],
        "nota": (
            "Si un tipo esperado no aparece, no hay items clasificados con "
            "ese valor exacto. Editá los items en el catálogo y asignales "
            "tipo_material correcto."
        ),
    })


# ─── Sync Banco Influencers desde Excel ───────────────────────────────────────

@bp.route("/api/admin/sync-influencers-excel", methods=["POST"])
def admin_sync_influencers_excel():
    """Sube un Excel de banco de influencers y hace UPSERT preservando datos.

    Body: multipart/form-data con campo 'file' = .xlsx
    Query: ?dry_run=1  para previsualizar sin escribir

    Hoja esperada: 'cuentas de creadores' con columnas:
       A: nombre, B: banco, C: cuenta, D: tipo cta, E: cédula,
       F: ciudad, G: usuario red, H: tipo creador

    Mapeo a marketing_influencers:
       nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit,
       ciudad, instagram (si existe col), tipo (si existe col)

    UPSERT por LOWER(TRIM(nombre)). Solo actualiza columnas vacías en DB.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'El archivo debe ser .xlsx'}), 400

    dry_run = request.args.get('dry_run', '0') in ('1', 'true', 'True')

    try:
        from openpyxl import load_workbook
    except Exception:
        return jsonify({'error': 'openpyxl no instalado en el servidor'}), 500

    def _norm(s):
        return (s or "").strip().lower() if isinstance(s, str) else ""

    def _str(v):
        if v is None:
            return ""
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()

    try:
        wb = load_workbook(f, data_only=True, read_only=True)
    except Exception as e:
        return jsonify({'error': f'Excel inválido: {e}'}), 400

    if "cuentas de creadores" not in wb.sheetnames:
        return jsonify({
            'error': "Hoja 'cuentas de creadores' no existe",
            'hojas_disponibles': wb.sheetnames
        }), 400

    ws = wb["cuentas de creadores"]
    creadores = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or not row[0]:
            continue
        creadores.append({
            "nombre":      _str(row[0]),
            "banco":       _str(row[1]) if len(row) > 1 else "",
            "cuenta":      _str(row[2]) if len(row) > 2 else "",
            "tipo_cta":    _str(row[3]) if len(row) > 3 else "",
            "cedula":      _str(row[4]) if len(row) > 4 else "",
            "ciudad":      _str(row[5]) if len(row) > 5 else "",
            "user":        _str(row[6]) if len(row) > 6 else "",
            "tipo_creador": _str(row[7]) if len(row) > 7 else "",
        })

    EXCEL_TO_DB = {
        "banco":         "banco",
        "cuenta":        "cuenta_bancaria",
        "tipo_cta":      "tipo_cuenta",
        "cedula":        "cedula_nit",
        "ciudad":        "ciudad",
        "user":          "instagram",
        "tipo_creador":  "tipo",
    }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("PRAGMA table_info(marketing_influencers)")
    cols_db = {r["name"] for r in c.fetchall()}

    nuevos, actualizados, sin_cambios = [], [], []
    for ex in creadores:
        nombre = ex["nombre"]
        c.execute(
            "SELECT * FROM marketing_influencers WHERE LOWER(TRIM(nombre)) = ? LIMIT 1",
            (nombre.lower(),)
        )
        existing = c.fetchone()
        if not existing:
            cols_to_insert = ["nombre"]
            vals = [nombre]
            for k_ex, k_db in EXCEL_TO_DB.items():
                if k_db in cols_db and ex.get(k_ex):
                    cols_to_insert.append(k_db)
                    vals.append(ex[k_ex])
            placeholders = ",".join("?" * len(cols_to_insert))
            sql = f"INSERT INTO marketing_influencers ({','.join(cols_to_insert)}) VALUES ({placeholders})"
            if not dry_run:
                c.execute(sql, vals)
            nuevos.append(nombre)
            continue

        sets, vals, cambios_locales = [], [], []
        for k_ex, k_db in EXCEL_TO_DB.items():
            if k_db not in cols_db:
                continue
            new_val = ex.get(k_ex, "")
            old_val = existing[k_db] if k_db in existing.keys() else ""
            old_val = (old_val or "").strip() if isinstance(old_val, str) else ""
            if new_val and not old_val:
                sets.append(f"{k_db}=?")
                vals.append(new_val)
                cambios_locales.append(f"{k_db}: <vacío> → {new_val[:40]}")
        if sets:
            vals.append(existing["id"])
            if not dry_run:
                c.execute(
                    f"UPDATE marketing_influencers SET {','.join(sets)} WHERE id=?",
                    vals
                )
            actualizados.append({'nombre': nombre, 'cambios': cambios_locales})
        else:
            sin_cambios.append(nombre)

    if not dry_run:
        conn.commit()
    conn.close()

    _log_sec(u, _client_ip(),
             "admin_sync_influencers_excel",
             f"dry_run={dry_run} nuevos={len(nuevos)} act={len(actualizados)}")

    return jsonify({
        'ok': True,
        'dry_run': dry_run,
        'total_excel': len(creadores),
        'nuevos':       {'count': len(nuevos), 'lista': nuevos},
        'actualizados': {'count': len(actualizados), 'lista': actualizados},
        'sin_cambios':  {'count': len(sin_cambios), 'lista': sin_cambios[:50]},
        'cols_db_disponibles': sorted(cols_db),
    })


# ─── Importar pagos pendientes de influencers desde Excel ────────────────────

# Patrones para detectar columnas automáticamente — soporta Excel con
# diferentes naming sin que el user tenga que renombrar nada
_COL_PATTERNS_PAGOS = {
    'nombre':       ['influencer', 'creador', 'nombre', 'usuario'],
    'fecha':        ['fecha publicacion', 'fecha de publicacion', 'fecha publicación',
                     'fecha de publicación', 'fecha post', 'fecha contenido',
                     'publicacion', 'publicación', 'fecha'],
    'valor':        ['valor', 'monto', 'pago', 'total', 'precio'],
    'estado':       ['estado', 'pago realizado', 'pagado', 'status'],
    'concepto':     ['concepto', 'producto', 'campana', 'campaña', 'entregable',
                     'descripcion', 'descripción'],
    'instagram':    ['instagram', 'cuenta', 'user', '@'],
}


def _norm_header(s):
    """Normaliza un header de Excel: lower, sin acentos, sin extra spaces."""
    import unicodedata as _ud
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = ''.join(c for c in _ud.normalize('NFD', s) if _ud.category(c) != 'Mn')
    return ' '.join(s.split())


def _detect_cols(headers):
    """Devuelve dict {nuestro_campo: indice_en_excel} matcheando por patterns."""
    out = {}
    norms = [_norm_header(h) for h in headers]
    for field, patterns in _COL_PATTERNS_PAGOS.items():
        for i, h in enumerate(norms):
            if not h:
                continue
            if any(p in h for p in patterns):
                if field not in out:
                    out[field] = i
                    break
    return out


def _norm_nombre(s):
    """Normaliza nombre influencer para matching: lower + trim + sin acentos."""
    import unicodedata as _ud
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = ''.join(c for c in _ud.normalize('NFD', s) if _ud.category(c) != 'Mn')
    return ' '.join(s.split())


def _parse_fecha(v):
    """Acepta datetime, date, o string YYYY-MM-DD / DD/MM/YYYY. Devuelve ISO o ''."""
    if v is None or v == '':
        return ''
    from datetime import datetime as _dt, date as _date
    if isinstance(v, _dt):
        return v.date().isoformat()
    if isinstance(v, _date):
        return v.isoformat()
    s = str(v).strip()
    # YYYY-MM-DD
    try:
        return _dt.strptime(s[:10], '%Y-%m-%d').date().isoformat()
    except ValueError:
        pass
    # DD/MM/YYYY
    try:
        return _dt.strptime(s[:10], '%d/%m/%Y').date().isoformat()
    except ValueError:
        pass
    # DD-MM-YYYY
    try:
        return _dt.strptime(s[:10], '%d-%m-%Y').date().isoformat()
    except ValueError:
        pass
    return ''


def _parse_valor(v):
    """Acepta int, float, o string con $/coma/punto. Devuelve float >= 0."""
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace('$', '').replace(' ', '')
    # Si tiene coma como decimal Y punto como miles → quitar puntos, comma a punto
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        # Solo coma — si tiene 3 dígitos después es miles, sino decimal
        partes = s.split(',')
        if len(partes[-1]) == 3:
            s = s.replace(',', '')
        else:
            s = s.replace(',', '.')
    elif '.' in s:
        partes = s.split('.')
        if len(partes[-1]) == 3:
            s = s.replace('.', '')
    try:
        return max(0.0, float(s))
    except ValueError:
        return 0.0


@bp.route("/api/admin/import-pagos-influencers-excel", methods=["POST"])
def admin_import_pagos_influencers_excel():
    """Importa pagos pendientes de influencers desde Excel.

    Modo "reset solo pendientes" (opción B aprobada por user):
      - Borra solicitudes Influencer con estado != Pagada (más sus OCs y pagos)
      - Importa cada fila del Excel como nueva solicitud Aprobada lista para pagar
      - Conserva intacto el historial de pagos hechos

    Detecta columnas del Excel automáticamente buscando keywords en los
    headers (influencer/creador/nombre, fecha publicación, valor, etc.).

    Body: multipart/form-data 'file' = .xlsx
    Query: ?dry_run=1 → previsualiza sin escribir nada

    Para cada fila válida:
      1. Match influencer en marketing_influencers por nombre normalizado
      2. INSERT solicitudes_compra (estado=Aprobada, categoria=Influencer/Marketing Digital)
      3. INSERT ordenes_compra (proveedor=nombre, valor_total=valor)
      4. INSERT ordenes_compra_items (descripción=concepto, valor)
      5. INSERT pagos_influencers con fecha_publicacion = fecha del Excel
         (esto es lo que permitirá ordenar correctamente en /compras)
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'El archivo debe ser .xlsx'}), 400

    dry_run = request.args.get('dry_run', '0') in ('1', 'true', 'True')

    try:
        from openpyxl import load_workbook
    except Exception:
        return jsonify({'error': 'openpyxl no instalado'}), 500

    try:
        wb = load_workbook(f, data_only=True, read_only=True)
    except Exception as e:
        return jsonify({'error': f'Excel inválido: {e}'}), 400

    # Buscar la hoja: priorizar nombres conocidos, sino la primera
    nombres_prioridad = ['pagos', 'pagos influencers', 'publicaciones',
                         'contenido', 'campanas', 'campañas']
    sheet_name = None
    for n in wb.sheetnames:
        if any(p in _norm_header(n) for p in nombres_prioridad):
            sheet_name = n
            break
    if sheet_name is None:
        # Excluir hojas de banco/configuración si las detecta
        for n in wb.sheetnames:
            if 'cuenta' not in _norm_header(n) and 'banco' not in _norm_header(n):
                sheet_name = n
                break
    if sheet_name is None:
        sheet_name = wb.sheetnames[0]

    ws = wb[sheet_name]
    rows_excel = list(ws.iter_rows(values_only=True))
    if len(rows_excel) < 2:
        return jsonify({
            'error': f'Hoja "{sheet_name}" tiene menos de 2 filas',
            'hojas_disponibles': wb.sheetnames,
        }), 400

    headers = rows_excel[0]
    cols_idx = _detect_cols(headers)

    if 'nombre' not in cols_idx or 'valor' not in cols_idx:
        return jsonify({
            'error': 'No se detectó columna de Influencer y/o Valor en el Excel',
            'hoja_usada': sheet_name,
            'headers_detectados': [str(h) for h in headers if h],
            'columnas_mapeadas': cols_idx,
            'hojas_disponibles': wb.sheetnames,
            'sugerencia': (
                'Asegúrate de que el Excel tenga columnas con nombres como '
                '"Influencer/Creador/Nombre" y "Valor/Monto/Pago". '
                'Mira hojas_disponibles si la hoja correcta es otra.'
            ),
        }), 400

    # Cargar tabla de influencers para matching
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM marketing_influencers")
    inf_by_norm = {}
    inf_norm_keys = []  # lista para fuzzy matching con difflib
    for r in c.fetchall():
        nm = _norm_nombre(r['nombre'])
        if nm and nm not in inf_by_norm:
            inf_by_norm[nm] = r['id']
            inf_norm_keys.append(nm)

    import difflib

    def _match_influencer(nombre_str):
        """Devuelve (inf_id, match_type, match_nombre) o (None, None, None).

        Estrategia escalonada:
          1. Match exacto normalizado
          2. Prefix match (uno empieza con el otro)
          3. Substring match (uno contiene al otro)
          4. Fuzzy con difflib.get_close_matches cutoff 0.82
        """
        nm = _norm_nombre(nombre_str)
        if not nm:
            return None, None, None
        if nm in inf_by_norm:
            return inf_by_norm[nm], 'exacto', nm
        # Prefix
        for k in inf_norm_keys:
            if k.startswith(nm) or nm.startswith(k):
                return inf_by_norm[k], 'prefix', k
        # Substring
        for k in inf_norm_keys:
            if nm in k or k in nm:
                return inf_by_norm[k], 'substring', k
        # Fuzzy
        candidatos = difflib.get_close_matches(nm, inf_norm_keys, n=1, cutoff=0.82)
        if candidatos:
            k = candidatos[0]
            return inf_by_norm[k], 'fuzzy', k
        return None, None, None

    # Procesar filas
    plan_import = []
    sin_match = []
    sin_valor = []
    sin_nombre = []
    pagadas_skipped = []

    estado_pagado_kws = {'pagado', 'pagada', 'paid', 'pago realizado', 'si', 'sí', 'yes', 'x'}

    for i, row in enumerate(rows_excel[1:], start=2):
        if not row or not any(row):
            continue
        nombre = row[cols_idx['nombre']] if cols_idx.get('nombre') is not None else None
        valor_raw = row[cols_idx['valor']] if cols_idx.get('valor') is not None else None
        fecha_raw = row[cols_idx['fecha']] if cols_idx.get('fecha') is not None else None
        estado_raw = row[cols_idx.get('estado')] if cols_idx.get('estado') is not None else None
        concepto_raw = row[cols_idx.get('concepto')] if cols_idx.get('concepto') is not None else None
        instagram_raw = row[cols_idx.get('instagram')] if cols_idx.get('instagram') is not None else None

        nombre_str = str(nombre or '').strip()
        if not nombre_str:
            sin_nombre.append({'fila': i})
            continue
        valor = _parse_valor(valor_raw)
        if valor <= 0:
            sin_valor.append({'fila': i, 'nombre': nombre_str})
            continue
        # Saltar las que ya estén marcadas como pagadas
        estado_norm = _norm_header(estado_raw)
        if any(kw in estado_norm for kw in estado_pagado_kws):
            pagadas_skipped.append({'fila': i, 'nombre': nombre_str, 'valor': valor})
            continue

        inf_id, match_type, match_nombre = _match_influencer(nombre_str)
        if not inf_id:
            sin_match.append({
                'fila': i, 'nombre': nombre_str, 'valor': valor,
                'instagram': str(instagram_raw or '').strip()
            })
            continue

        plan_import.append({
            'fila': i,
            'influencer_id': inf_id,
            'nombre': nombre_str,
            'valor': valor,
            'fecha_publicacion': _parse_fecha(fecha_raw),
            'concepto': str(concepto_raw or '').strip() or 'Pago influencer',
            'match_type': match_type,
            'match_nombre_banco': match_nombre,
        })

    if dry_run:
        return jsonify({
            'ok': True,
            'dry_run': True,
            'hoja_usada': sheet_name,
            'columnas_mapeadas': cols_idx,
            'a_importar': {
                'count': len(plan_import),
                'preview': plan_import[:30],
                'valor_total': round(sum(p['valor'] for p in plan_import), 0),
            },
            'sin_match': {
                'count': len(sin_match),
                'lista': sin_match[:30],
                'nota': 'Estos NO se van a importar. Agrega el influencer al banco primero (/admin sync banco) o corrige el nombre en el Excel.',
            },
            'pagadas_skipped': {'count': len(pagadas_skipped), 'lista': pagadas_skipped[:20]},
            'sin_valor': {'count': len(sin_valor)},
            'sin_nombre': {'count': len(sin_nombre)},
        })

    # ── APLICAR ─────────────────────────────────────────────────────────────
    # SAFETY: si no hay nada para importar (plan_import vacío) NO borramos
    # las solicitudes pendientes existentes — eso dejaría la base vacía.
    # El user debe arreglar nombres en el Excel o agregar al banco primero.
    # Override con ?force=1 si el user QUIERE limpiar todo aunque no importe nada.
    force = request.args.get('force', '0') in ('1', 'true', 'True')
    if not plan_import and not force:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({
            'error': 'No hay filas válidas para importar — reset abortado',
            'detalle': (
                f'{len(sin_match)} fila(s) sin match en el banco, '
                f'{len(sin_valor)} sin valor, {len(sin_nombre)} sin nombre, '
                f'{len(pagadas_skipped)} ya marcadas como pagadas. '
                'No se borró nada. Arregla los nombres del Excel o agrega los '
                'influencers al banco antes de aplicar. Si querés forzar el '
                'reset igual (vaciar pendientes), usa ?force=1.'
            ),
            'hoja_usada': sheet_name,
            'columnas_mapeadas': cols_idx,
            'sin_match': {
                'count': len(sin_match),
                'lista': sin_match[:30],
            },
            'sin_valor': {'count': len(sin_valor)},
            'pagadas_skipped': {'count': len(pagadas_skipped)},
        }), 400

    # Reset opción B: borrar solicitudes Influencer no-pagadas + sus OCs y pagos
    deleted = {'solicitudes': 0, 'ordenes_compra': 0, 'pagos_influencers': 0}
    try:
        # 1. Listar OCs de influencer cuyo estado de SC sea != 'Pagada'
        ocs_a_borrar = c.execute("""
            SELECT DISTINCT sc.numero_oc FROM solicitudes_compra sc
            WHERE sc.categoria = 'Influencer/Marketing Digital'
              AND sc.estado IN ('Pendiente', 'Aprobada', 'Rechazada')
              AND sc.numero_oc IS NOT NULL AND sc.numero_oc != ''
        """).fetchall()
        ocs_list = [r[0] for r in ocs_a_borrar]
        if ocs_list:
            placeholders = ','.join('?' * len(ocs_list))
            d = c.execute(
                f"DELETE FROM pagos_influencers WHERE numero_oc IN ({placeholders}) "
                f"AND COALESCE(estado,'') != 'Pagada'", ocs_list
            )
            deleted['pagos_influencers'] = d.rowcount or 0
            try:
                c.execute(
                    f"DELETE FROM ordenes_compra_items WHERE numero_oc IN ({placeholders})",
                    ocs_list
                )
            except sqlite3.OperationalError:
                pass
            d = c.execute(
                f"DELETE FROM ordenes_compra WHERE numero_oc IN ({placeholders})",
                ocs_list
            )
            deleted['ordenes_compra'] = d.rowcount or 0
        # Items de la solicitud
        try:
            c.execute("""DELETE FROM solicitudes_compra_items
                         WHERE numero IN (SELECT numero FROM solicitudes_compra
                                          WHERE categoria='Influencer/Marketing Digital'
                                            AND estado IN ('Pendiente','Aprobada','Rechazada'))""")
        except sqlite3.OperationalError:
            pass
        d = c.execute("""DELETE FROM solicitudes_compra
                         WHERE categoria='Influencer/Marketing Digital'
                           AND estado IN ('Pendiente','Aprobada','Rechazada')""")
        deleted['solicitudes'] = d.rowcount or 0

        # ── Importar plan ───────────────────────────────────────────────────
        from datetime import datetime as _dt
        anio = _dt.now().year
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero, 10) AS INTEGER)),0) "
                  "FROM solicitudes_compra WHERE numero LIKE ?", (f'SOL-{anio}-%',))
        n_sol = (c.fetchone()[0] or 0)
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero_oc, 9) AS INTEGER)),0) "
                  "FROM ordenes_compra WHERE numero_oc LIKE ?", (f'OC-{anio}-%',))
        n_oc = (c.fetchone()[0] or 0)

        importadas = []
        for plan in plan_import:
            n_sol += 1
            n_oc += 1
            num_sol = f'SOL-{anio}-{n_sol:04d}'
            num_oc = f'OC-{anio}-{n_oc:04d}'
            obs = (f"BENEFICIARIO: {plan['nombre']} | VALOR: ${plan['valor']:,.0f} | "
                   f"FECHA PUB: {plan['fecha_publicacion'] or 'sin fecha'} | "
                   f"CONCEPTO: {plan['concepto']} | Importado desde Excel por {u}")

            c.execute("""INSERT INTO solicitudes_compra
                (numero, fecha, estado, solicitante, urgencia, observaciones,
                 area, empresa, categoria, tipo, numero_oc, influencer_id, fecha_requerida)
                VALUES (?, datetime('now'), 'Aprobada', ?, 'Normal', ?, 'Marketing',
                        'Animus', 'Influencer/Marketing Digital', 'Servicio', ?, ?, ?)""",
                (num_sol, u, obs, num_oc, plan['influencer_id'],
                 plan['fecha_publicacion'] or ''))
            c.execute("""INSERT INTO ordenes_compra
                (numero_oc, fecha, estado, proveedor, valor_total, observaciones, creado_por)
                VALUES (?, datetime('now'), 'Aprobada', ?, ?, ?, ?)""",
                (num_oc, plan['nombre'], plan['valor'],
                 f"Pago influencer importado desde Excel · pub: {plan['fecha_publicacion'] or 'n/a'}", u))
            try:
                c.execute("""INSERT INTO ordenes_compra_items
                    (numero_oc, codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal)
                    VALUES (?, '', ?, 1, ?, ?)""",
                    (num_oc, plan['concepto'][:200], plan['valor'], plan['valor']))
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("""INSERT INTO pagos_influencers
                    (influencer_id, influencer_nombre, valor, fecha, estado, concepto, numero_oc, fecha_publicacion)
                    VALUES (?, ?, ?, datetime('now'), 'Pendiente', ?, ?, ?)""",
                    (plan['influencer_id'], plan['nombre'], plan['valor'],
                     plan['concepto'][:200], num_oc, plan['fecha_publicacion'] or ''))
            except sqlite3.OperationalError:
                pass
            importadas.append({
                'sol': num_sol, 'oc': num_oc,
                'nombre': plan['nombre'], 'valor': plan['valor'],
                'fecha_publicacion': plan['fecha_publicacion'],
            })

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        import traceback
        return jsonify({
            'error': 'Falla durante la importación',
            'detalle': str(e),
            'traceback': traceback.format_exc()[-800:],
            'rollback': 'aplicado',
        }), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

    _log_sec(u, _client_ip(),
             "admin_import_pagos_influencers_excel",
             f"deleted={deleted} imported={len(importadas)}")

    return jsonify({
        'ok': True,
        'dry_run': False,
        'hoja_usada': sheet_name,
        'reset': deleted,
        'importadas': {
            'count': len(importadas),
            'lista': importadas[:50],
            'valor_total': round(sum(i['valor'] for i in importadas), 0),
        },
        'sin_match': {
            'count': len(sin_match),
            'lista': sin_match[:30],
            'nota': 'NO importados — agrega los influencers al banco o corrige el nombre.',
        },
        'pagadas_skipped': {'count': len(pagadas_skipped)},
        'sin_valor': {'count': len(sin_valor)},
        'sin_nombre': {'count': len(sin_nombre)},
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
  <button class="tab" data-tab="banco" onclick="switchTab('banco')">&#x1F4B3; Banco Influencers</button>
  <button class="tab" data-tab="mps" onclick="switchTab('mps')">&#x1F9EA; Cat&aacute;logo MPs</button>
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
  <div class="card">
    <h2>&#x1F4E7; Test de SMTP (envío de correo)</h2>
    <div class="section-sub">
      Manda un correo de prueba con un PDF demo (CE-TEST-0000) al destinatario que indiques.
      Si dejas el campo vacío, se envía al remitente (a ti mismo). Sirve para validar
      que <code>EMAIL_REMITENTE</code> y <code>EMAIL_PASSWORD</code> están bien seteados
      antes de pagarle a un influencer real.
    </div>
    <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="email" id="test-email-dest" placeholder="destinatario@gmail.com (opcional)"
             style="padding:9px 14px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;min-width:280px;font-size:13px;">
      <select id="test-email-empresa"
              style="padding:9px 14px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:13px;">
        <option value="espagiria">PDF como Espagiria</option>
        <option value="animus">PDF como ANIMUS Lab</option>
      </select>
      <button class="btn" onclick="enviarTestEmail()">&#x26A1; Enviar correo de prueba</button>
    </div>
    <div id="test-email-result" style="margin-top:14px;"></div>
  </div>
</div>

<!-- ─── TAB BANCO INFLUENCERS ─── -->
<div id="tab-banco" class="tab-panel">
  <div class="card">
    <h2>&#x1F4B3; Sincronizar banco de influencers desde Excel</h2>
    <div class="section-sub">
      Sube el Excel de creadores (hoja <code>cuentas de creadores</code>). El sync
      hace UPSERT por nombre <strong>preservando datos existentes</strong> — solo
      llena columnas vacías de la base con datos del Excel. Nunca borra ni
      sobrescribe banco/cuenta/cédula que ya estén cargados.
    </div>
    <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="file" id="excel-file" accept=".xlsx,.xlsm"
             style="padding:8px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;">
      <button class="btn btn-outline" onclick="syncExcel(true)">&#x1F441; Vista previa (dry-run)</button>
      <button class="btn" onclick="syncExcel(false)">&#x26A1; Aplicar a la base</button>
    </div>
    <div id="banco-result" style="margin-top:18px;"></div>
  </div>

  <div class="card" style="border-left:3px solid #fbbf24;">
    <h2>&#x1F4B8; Importar pagos pendientes desde Excel</h2>
    <div class="section-sub">
      Sube el Excel con la lista de pagos pendientes (uno por fila). El sistema:
      <ul style="margin:6px 0 0 16px;">
        <li>Detecta automáticamente las columnas (Influencer, Fecha publicación, Valor, Estado, Concepto)</li>
        <li><strong>Borra las solicitudes Influencer no-pagadas</strong> (mantiene las Pagadas)</li>
        <li>Crea cada fila como solicitud Aprobada lista para pagar, con su <code>fecha_publicacion</code></li>
        <li>Saltea filas marcadas como "Pagado" en el Excel</li>
        <li>Saltea filas donde el nombre no matchea ningún influencer del banco</li>
      </ul>
    </div>
    <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="file" id="pagos-excel-file" accept=".xlsx,.xlsm"
             style="padding:8px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;">
      <button class="btn btn-outline" onclick="syncPagos(true)">&#x1F441; Vista previa (dry-run)</button>
      <button class="btn" onclick="syncPagos(false)" style="background:linear-gradient(135deg,#f59e0b,#d97706);">&#x26A1; Aplicar (borra pendientes + importa)</button>
    </div>
    <div id="pagos-result" style="margin-top:18px;"></div>
  </div>
</div>

<!-- ─── TAB CATÁLOGO MPs ─── -->
<div id="tab-mps" class="tab-panel">
  <div class="card">
    <h2>&#x1F9EA; Cat&aacute;logo de Materias Primas - estado de proveedor</h2>
    <div class="section-sub">
      Cuando creas una OC sugerida desde Compras, el sistema agrupa las MPs por
      <code>maestro_mps.proveedor</code>. Las MPs sin proveedor caen en
      'Sin asignar' y tienes que corregir manualmente cada vez. Asigna aqu&iacute;
      el proveedor habitual de cada MP para que las futuras OCs salgan
      correctamente agrupadas.
    </div>
    <div class="kpi-row" id="mps-kpis">
      <div class="kpi"><div class="kpi-l">Total activos</div><div class="kpi-v" id="mps-kpi-total">-</div></div>
      <div class="kpi"><div class="kpi-l">Con proveedor</div><div class="kpi-v" id="mps-kpi-con" style="color:#34d399;">-</div></div>
      <div class="kpi"><div class="kpi-l">Sin proveedor</div><div class="kpi-v" id="mps-kpi-sin" style="color:#f87171;">-</div></div>
      <div class="kpi"><div class="kpi-l">Cobertura</div><div class="kpi-v" id="mps-kpi-pct" style="font-size:14px;">-</div></div>
    </div>
    <h3 style="color:#a78bfa;font-size:13px;margin-top:16px;margin-bottom:8px;">Distribuci&oacute;n por proveedor</h3>
    <table>
      <thead><tr><th>Proveedor</th><th style="text-align:right;">Cantidad de MPs</th></tr></thead>
      <tbody id="mps-tbody-prov"><tr><td>Cargando...</td></tr></tbody>
    </table>
    <h3 style="color:#f87171;font-size:13px;margin-top:20px;margin-bottom:8px;">MPs sin proveedor asignado</h3>
    <div id="mps-sin-prov-info" style="font-size:12px;color:#94a3b8;margin-bottom:8px;"></div>
    <table>
      <thead><tr><th>C&oacute;digo</th><th>Nombre</th><th>Tipo</th><th>Asignar proveedor</th></tr></thead>
      <tbody id="mps-tbody-sin"><tr><td>Cargando...</td></tr></tbody>
    </table>
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
const _loaded = {backups:false, users:false, security:false, config:false, banco:false, mps:false};
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
    if (name === 'mps')      loadMpsStatus();
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

// ── TEST EMAIL (SMTP) ─────────────────────────────────────────────────────────
async function enviarTestEmail() {
  const dest = (document.getElementById('test-email-dest').value || '').trim();
  const empSel = document.getElementById('test-email-empresa');
  const empresa = empSel ? empSel.value : 'espagiria';
  const out = document.getElementById('test-email-result');
  out.innerHTML = '<div style="color:#94a3b8;padding:14px;">Generando PDF (' + empresa + ') y enviando...</div>';
  try {
    const r = await fetch('/api/admin/test-email', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({destinatario: dest, empresa: empresa})
    });
    let data;
    try { data = await r.json(); } catch(e) { data = {error: 'Respuesta inválida'}; }
    if (r.ok && data.ok) {
      const checks = (data.verificacion || []).map(v => '<li>' + v + '</li>').join('');
      out.innerHTML = '<div style="color:#34d399;padding:14px;background:#0f172a;border:1px solid #34d399;border-radius:8px;">'
        + '&#x2705; <strong>' + data.mensaje + '</strong><br>'
        + '<div style="margin-top:8px;font-size:12px;color:#cbd5e1;">'
        + '<div>De: <code>' + data.remitente + '</code></div>'
        + '<div>Para: <code>' + data.destinatario + '</code></div>'
        + '<div>Asunto: <em>' + data.asunto + '</em></div>'
        + '</div>'
        + '<ul style="margin-top:10px;font-size:12px;color:#cbd5e1;padding-left:18px;">' + checks + '</ul>'
        + '</div>';
      toast('Correo de prueba enviado', 'ok');
    } else {
      const pasos = (data.pasos || []).map(p => '<li>' + p + '</li>').join('');
      const env = data.env_status ? Object.entries(data.env_status)
        .map(([k,v]) => '<div style="font-family:monospace;font-size:11px;color:#94a3b8;">' + k + ': <strong style="color:' + (String(v)==='MISSING'?'#f87171':'#34d399') + '">' + v + '</strong></div>').join('') : '';
      out.innerHTML = '<div style="color:#f87171;padding:14px;background:#0f172a;border:1px solid #f87171;border-radius:8px;">'
        + '&#x274C; <strong>Error ' + r.status + ': ' + (data.error || 'Falló envío') + '</strong>'
        + (data.detalle ? '<div style="margin-top:8px;font-size:12px;color:#fbbf24;">' + data.detalle + '</div>' : '')
        + (env ? '<div style="margin-top:10px;padding:8px 12px;background:#1e293b;border-radius:6px;">' + env + '</div>' : '')
        + (pasos ? '<div style="margin-top:10px;font-size:12px;color:#cbd5e1;"><strong>Pasos para configurar:</strong><ul style="margin-top:6px;padding-left:20px;">' + pasos + '</ul></div>' : '')
        + '</div>';
      toast('SMTP no configurado o credenciales inválidas', 'warn');
    }
  } catch(e) {
    out.innerHTML = '<div style="color:#f87171;padding:14px;">Error de red: ' + (e.message || e) + '</div>';
  }
}

// ── BANCO INFLUENCERS (sync Excel) ────────────────────────────────────────────
async function syncExcel(dryRun) {
  const fi = document.getElementById('excel-file');
  const out = document.getElementById('banco-result');
  if (!fi.files.length) {
    toast('Selecciona un archivo .xlsx', 'warn');
    return;
  }
  out.innerHTML = '<div style="color:#94a3b8;padding:14px;">Procesando...</div>';
  const fd = new FormData();
  fd.append('file', fi.files[0]);
  const url = '/api/admin/sync-influencers-excel' + (dryRun ? '?dry_run=1' : '');
  const r = await fetch(url, {method:'POST', body: fd});
  let data;
  try { data = await r.json(); } catch(e) { data = {error: 'Respuesta inválida'}; }
  if (!r.ok) {
    out.innerHTML = '<div style="color:#f87171;padding:14px;background:#1e293b;border-radius:8px;">'
      + 'Error ' + r.status + ': ' + (data.error || '') + '</div>';
    return;
  }
  const banner = dryRun
    ? '<div style="color:#fbbf24;padding:10px 14px;background:#0f172a;border:1px solid #fbbf24;border-radius:8px;margin-bottom:14px;">'
      + '&#x1F441; <strong>VISTA PREVIA</strong> — nada se escribió en la base. Pulsa "Aplicar" para confirmar.</div>'
    : '<div style="color:#34d399;padding:10px 14px;background:#0f172a;border:1px solid #34d399;border-radius:8px;margin-bottom:14px;">'
      + '&#x2705; <strong>APLICADO</strong> — la base fue actualizada.</div>';
  const lstNuevos = (data.nuevos.lista || []).slice(0, 30).map(n =>
    '<li style="padding:3px 0;">' + n + '</li>').join('');
  const lstAct = (data.actualizados.lista || []).slice(0, 30).map(a =>
    '<li style="padding:3px 0;"><strong>' + a.nombre + '</strong>'
    + (a.cambios && a.cambios.length ? ' <span style="color:#94a3b8;font-size:11px;">— '
       + a.cambios.join('; ') + '</span>' : '') + '</li>').join('');
  out.innerHTML = banner + ''
    + '<div class="kpi-row">'
      + '<div class="kpi"><div class="kpi-l">Excel</div><div class="kpi-v">' + data.total_excel + '</div></div>'
      + '<div class="kpi"><div class="kpi-l">Nuevos</div><div class="kpi-v" style="color:#34d399;">' + data.nuevos.count + '</div></div>'
      + '<div class="kpi"><div class="kpi-l">Actualizados</div><div class="kpi-v" style="color:#fbbf24;">' + data.actualizados.count + '</div></div>'
      + '<div class="kpi"><div class="kpi-l">Sin cambios</div><div class="kpi-v" style="color:#64748b;">' + data.sin_cambios.count + '</div></div>'
    + '</div>'
    + (lstNuevos ? '<div class="card"><h2>&#x2795; Nuevos (' + data.nuevos.count + ')</h2><ul style="font-size:13px;color:#cbd5e1;list-style:none;padding-left:0;">' + lstNuevos + '</ul></div>' : '')
    + (lstAct ? '<div class="card"><h2>&#x270F; Actualizados (' + data.actualizados.count + ')</h2><ul style="font-size:13px;color:#cbd5e1;list-style:none;padding-left:0;">' + lstAct + '</ul></div>' : '');
  if (!dryRun) toast('Sync aplicado: ' + data.nuevos.count + ' nuevos, ' + data.actualizados.count + ' actualizados', 'ok');
}

// ── PAGOS INFLUENCERS — import Excel + reset pendientes ──────────────────────
async function syncPagos(dryRun) {
  const fi = document.getElementById('pagos-excel-file');
  const out = document.getElementById('pagos-result');
  if (!fi.files.length) {
    toast('Selecciona un archivo .xlsx', 'warn');
    return;
  }
  if (!dryRun) {
    if (!confirm('Esto va a BORRAR todas las solicitudes Influencer no-pagadas y reemplazarlas con las del Excel. Las solicitudes ya pagadas se conservan.\n\n¿Confirmás?')) return;
  }
  out.innerHTML = '<div style="color:#94a3b8;padding:14px;">Procesando...</div>';
  const fd = new FormData();
  fd.append('file', fi.files[0]);
  const url = '/api/admin/import-pagos-influencers-excel' + (dryRun ? '?dry_run=1' : '');
  const r = await fetch(url, {method:'POST', body: fd});
  let data;
  try { data = await r.json(); } catch(e) { data = {error: 'Respuesta inválida'}; }
  if (!r.ok) {
    let extra = '';
    if (data.headers_detectados) {
      extra += '<div style="margin-top:8px;font-size:11px;color:#94a3b8;"><strong>Headers detectados:</strong> ' + data.headers_detectados.join(' · ') + '</div>';
    }
    if (data.hojas_disponibles) {
      extra += '<div style="margin-top:4px;font-size:11px;color:#94a3b8;"><strong>Hojas en el Excel:</strong> ' + data.hojas_disponibles.join(' · ') + '</div>';
    }
    if (data.sugerencia) {
      extra += '<div style="margin-top:8px;font-size:12px;color:#fbbf24;">' + data.sugerencia + '</div>';
    }
    out.innerHTML = '<div style="color:#f87171;padding:14px;background:#1e293b;border-radius:8px;">'
      + 'Error ' + r.status + ': ' + (data.error || '') + extra + '</div>';
    return;
  }
  const banner = dryRun
    ? '<div style="color:#fbbf24;padding:10px 14px;background:#0f172a;border:1px solid #fbbf24;border-radius:8px;margin-bottom:14px;">'
      + '&#x1F441; <strong>VISTA PREVIA</strong> — nada se escribió. Pulsa "Aplicar" para confirmar.</div>'
    : '<div style="color:#34d399;padding:10px 14px;background:#0f172a;border:1px solid #34d399;border-radius:8px;margin-bottom:14px;">'
      + '&#x2705; <strong>APLICADO</strong> — la base fue actualizada.</div>';

  const cm = (data.columnas_mapeadas || {});
  const cmList = Object.entries(cm).map(([k,v]) => k+'→col'+v).join(' · ');

  let kpis = '<div class="kpi-row">';
  if (data.a_importar) {
    kpis += '<div class="kpi"><div class="kpi-l">A importar</div><div class="kpi-v" style="color:#34d399;">' + data.a_importar.count + '</div></div>';
    kpis += '<div class="kpi"><div class="kpi-l">Valor total</div><div class="kpi-v" style="color:#34d399;font-size:14px;">$' + Number(data.a_importar.valor_total||0).toLocaleString('es-CO') + '</div></div>';
  }
  if (data.importadas) {
    kpis += '<div class="kpi"><div class="kpi-l">Importadas</div><div class="kpi-v" style="color:#34d399;">' + data.importadas.count + '</div></div>';
    kpis += '<div class="kpi"><div class="kpi-l">Valor total</div><div class="kpi-v" style="color:#34d399;font-size:14px;">$' + Number(data.importadas.valor_total||0).toLocaleString('es-CO') + '</div></div>';
  }
  if (data.reset) {
    kpis += '<div class="kpi"><div class="kpi-l">Solic. borradas</div><div class="kpi-v" style="color:#fbbf24;">' + data.reset.solicitudes + '</div></div>';
  }
  kpis += '<div class="kpi"><div class="kpi-l">Sin match</div><div class="kpi-v" style="color:#f87171;">' + (data.sin_match ? data.sin_match.count : 0) + '</div></div>';
  if (data.pagadas_skipped) {
    kpis += '<div class="kpi"><div class="kpi-l">Skipped (pagadas)</div><div class="kpi-v" style="color:#94a3b8;">' + data.pagadas_skipped.count + '</div></div>';
  }
  kpis += '</div>';

  let preview = '';
  const lst = (data.a_importar && data.a_importar.preview) || (data.importadas && data.importadas.lista) || [];
  if (lst.length) {
    preview = '<div class="card"><h2>&#x2795; A importar / Importadas</h2>'
      + '<table><thead><tr><th>Sol/OC</th><th>Influencer</th><th>Valor</th><th>Fecha pub</th></tr></thead><tbody>'
      + lst.map(p => '<tr><td style="font-family:monospace;font-size:11px;">' + (p.sol || ('#' + p.fila)) + (p.oc ? ' / ' + p.oc : '') + '</td><td>' + p.nombre + '</td><td>$' + Number(p.valor||0).toLocaleString('es-CO') + '</td><td style="font-size:11px;color:#94a3b8;">' + (p.fecha_publicacion || '—') + '</td></tr>').join('')
      + '</tbody></table></div>';
  }
  let nomatch = '';
  if (data.sin_match && data.sin_match.count > 0) {
    nomatch = '<div class="card" style="border-left:3px solid #f87171;"><h2>&#x274C; Sin match en banco (' + data.sin_match.count + ')</h2>'
      + '<div style="font-size:12px;color:#fbbf24;margin-bottom:8px;">' + (data.sin_match.nota || '') + '</div>'
      + '<table><tbody>'
      + data.sin_match.lista.map(p => '<tr><td style="font-size:11px;">fila ' + p.fila + '</td><td>' + p.nombre + '</td><td>$' + Number(p.valor||0).toLocaleString('es-CO') + '</td><td style="font-size:11px;color:#94a3b8;">' + (p.instagram || '') + '</td></tr>').join('')
      + '</tbody></table></div>';
  }

  out.innerHTML = banner
    + '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">Hoja: <strong>' + (data.hoja_usada || '?') + '</strong> · Columnas: ' + cmList + '</div>'
    + kpis + preview + nomatch;
  if (!dryRun) toast('Importación aplicada: ' + (data.importadas ? data.importadas.count : 0) + ' nuevas, ' + (data.reset ? data.reset.solicitudes : 0) + ' borradas', 'ok');
}

// ── CATÁLOGO MPs (proveedores) ─────────────────────────────────────────────
let _MPS_PROVS_LIST = [];

async function loadMpsStatus(){
  const r = await fetch('/api/admin/mps-proveedores-status');
  if (!r.ok) {
    document.getElementById('mps-tbody-sin').innerHTML =
      '<tr><td colspan="4" style="color:#f87171;">Error '+r.status+'</td></tr>';
    return;
  }
  const data = await r.json();
  document.getElementById('mps-kpi-total').textContent = data.total_activos || 0;
  document.getElementById('mps-kpi-con').textContent = data.con_proveedor || 0;
  document.getElementById('mps-kpi-sin').textContent = data.sin_proveedor || 0;
  document.getElementById('mps-kpi-pct').textContent = (data.pct_cobertura || 0) + '%';

  // Tabla por proveedor
  const tbody1 = document.getElementById('mps-tbody-prov');
  if (data.por_proveedor && data.por_proveedor.length) {
    tbody1.innerHTML = data.por_proveedor.map(p => {
      const isSin = p.proveedor === '(SIN PROVEEDOR)';
      const color = isSin ? '#f87171' : '#cbd5e1';
      return '<tr><td style="color:'+color+';font-weight:'+(isSin?'700':'400')+';">'+p.proveedor+'</td>'
        + '<td style="text-align:right;font-family:monospace;">'+p.total+'</td></tr>';
    }).join('');
  } else {
    tbody1.innerHTML = '<tr><td colspan="2" style="color:#94a3b8;">Sin datos</td></tr>';
  }

  // Lista de MPs sin proveedor (con dropdown para asignar)
  _MPS_PROVS_LIST = data.proveedores_existentes || [];
  const sinList = data.sin_proveedor_lista || [];
  const info = document.getElementById('mps-sin-prov-info');
  if (info) {
    info.textContent = sinList.length === 0
      ? '✅ Todas las MPs tienen proveedor asignado.'
      : sinList.length + ' MPs sin proveedor — asígnalos para que la auto-generación de OC los agrupe correctamente.';
  }
  const tbody2 = document.getElementById('mps-tbody-sin');
  if (sinList.length === 0) {
    tbody2.innerHTML = '<tr><td colspan="4" style="color:#34d399;text-align:center;padding:20px;">✅ Sin pendientes</td></tr>';
  } else {
    tbody2.innerHTML = sinList.map(m => {
      const opts = '<option value="">(sin asignar)</option>'
        + _MPS_PROVS_LIST.map(p => '<option value="'+p+'">'+p+'</option>').join('')
        + '<option value="__nuevo__">+ Otro proveedor (escribir)...</option>';
      return '<tr>'
        + '<td style="font-family:monospace;font-size:11px;">'+m.codigo_mp+'</td>'
        + '<td>'+m.nombre+'</td>'
        + '<td style="color:#94a3b8;font-size:11px;">'+(m.tipo||'')+'</td>'
        + '<td><select class="mp-prov-sel" data-cod="'+m.codigo_mp+'" style="background:#0f172a;border:1px solid #334155;border-radius:4px;color:#e2e8f0;padding:4px 8px;font-size:12px;width:100%;" onchange="asignarMpProv(this)">'
        + opts
        + '</select></td></tr>';
    }).join('');
  }
}

async function asignarMpProv(selEl){
  const codigo = selEl.dataset.cod;
  let proveedor = selEl.value;
  if (proveedor === '__nuevo__') {
    proveedor = (prompt('Nombre del nuevo proveedor para ' + codigo + ':') || '').trim();
    if (!proveedor) {
      selEl.value = '';
      return;
    }
  }
  if (!proveedor) {
    if (!confirm('¿Quitar proveedor de ' + codigo + '?')) return;
  }
  const r = await fetch('/api/admin/mps-asignar-proveedor', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({codigo_mp: codigo, proveedor: proveedor})
  });
  const d = await r.json();
  if (d.ok) {
    toast(codigo + ' → ' + (proveedor || 'sin proveedor'), 'ok');
    // Recargar para que la fila desaparezca de la tabla
    loadMpsStatus();
  } else {
    toast('Error: ' + (d.error || 'no se pudo asignar'), 0);
    selEl.value = '';
  }
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
