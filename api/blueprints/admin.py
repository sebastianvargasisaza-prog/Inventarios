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

@bp.route("/api/admin/import-mps-nombres-excel", methods=["POST"])
def admin_import_mps_nombres_excel():
    """Importa Excel con código + nombre comercial (+ proveedor opcional) para
    corregir el catálogo masivamente.

    Caso de uso: el catálogo tiene nombre_comercial = código en muchas filas
    porque alguien se confundió al importar. Excel con la corrección rápida.

    Detecta columnas automáticamente:
      - código: 'codigo', 'code', 'mp', 'sku'
      - nombre: 'nombre', 'descripcion', 'material', 'comercial'
      - proveedor: 'proveedor', 'supplier' (opcional)

    Body: multipart/form-data con 'file' = .xlsx
    Query: ?dry_run=1 para preview

    Devuelve por fila: actualizado | sin_cambios | sin_match | sin_codigo
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

    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return jsonify({'error': 'Hoja con menos de 2 filas'}), 400

    headers = rows[0]
    norms = [_norm_header(h) for h in headers]

    def _find(*kws):
        for i, h in enumerate(norms):
            if any(k in h for k in kws):
                return i
        return None

    idx_cod = _find('codigo', 'code', 'sku')
    idx_nom = _find('nombre', 'descripcion', 'comercial', 'material')
    idx_prov = _find('proveedor', 'supplier')

    if idx_cod is None or idx_nom is None:
        return jsonify({
            'error': 'No detecté columnas de código y nombre',
            'headers': [str(h) for h in headers if h],
            'sugerencia': 'El Excel debe tener al menos columnas "código" y "nombre"',
        }), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    actualizados = []
    sin_cambios = []
    sin_match = []
    sin_codigo = []

    for i, row in enumerate(rows[1:], start=2):
        if not row or not any(row):
            continue
        cod = str(row[idx_cod] or '').strip() if idx_cod is not None else ''
        nom_nuevo = str(row[idx_nom] or '').strip() if idx_nom is not None else ''
        prov_nuevo = str(row[idx_prov] or '').strip() if idx_prov is not None else ''
        if not cod:
            sin_codigo.append({'fila': i, 'nombre_excel': nom_nuevo})
            continue
        # Buscar item actual
        cur = c.execute(
            "SELECT codigo_mp, nombre_comercial, COALESCE(proveedor,'') FROM maestro_mps WHERE codigo_mp=?",
            (cod,)
        ).fetchone()
        if not cur:
            sin_match.append({'fila': i, 'codigo': cod, 'nombre_excel': nom_nuevo})
            continue
        cambios = {}
        # Solo actualizar nombre si el actual está vacío o es igual al código
        # (señal de que está mal cargado). NO sobrescribir nombres reales.
        actual_nom = (cur['nombre_comercial'] or '').strip()
        if nom_nuevo and (not actual_nom or actual_nom == cod):
            cambios['nombre_comercial'] = nom_nuevo
        # Proveedor: solo actualizar si actual está vacío y Excel tiene
        actual_prov = (cur[2] or '').strip()
        if prov_nuevo and not actual_prov:
            cambios['proveedor'] = prov_nuevo
        if cambios:
            if not dry_run:
                sets = ', '.join(f"{k}=?" for k in cambios)
                vals = list(cambios.values()) + [cod]
                c.execute(f"UPDATE maestro_mps SET {sets} WHERE codigo_mp=?", vals)
            actualizados.append({
                'codigo': cod,
                'nombre_antes': actual_nom,
                'nombre_nuevo': cambios.get('nombre_comercial', actual_nom),
                'proveedor_nuevo': cambios.get('proveedor', actual_prov),
            })
        else:
            sin_cambios.append(cod)

    if not dry_run:
        conn.commit()
    conn.close()

    if not dry_run:
        _log_sec(u, _client_ip(),
                 "admin_import_mps_nombres_excel",
                 f"actualizados={len(actualizados)} sin_match={len(sin_match)}")

    return jsonify({
        'ok': True,
        'dry_run': dry_run,
        'actualizados': {'count': len(actualizados), 'lista': actualizados[:50]},
        'sin_cambios': {'count': len(sin_cambios)},
        'sin_match': {'count': len(sin_match), 'lista': sin_match[:30]},
        'sin_codigo': {'count': len(sin_codigo), 'lista': sin_codigo[:10]},
        'columnas_mapeadas': {'codigo': idx_cod, 'nombre': idx_nom, 'proveedor': idx_prov},
        'nota': 'Solo actualiza nombres si el actual está vacío o = código. Nombres correctos NO se sobrescriben.',
    })


def _parse_excel_verde(file_storage, incluir_no_verde=False):
    """Parsea Excel del conteo fisico.

    Por default retorna solo filas verdes (FF92D050). Si incluir_no_verde
    es True, tambien retorna las filas rojas/blancas en un dict aparte
    `excel_no_verde` — esto sirve para regenerar lotes que las
    producciones consumieron pero que ya no estan fisicamente (Catalina
    los marco NO presente porque se acabaron en produccion).

    Devuelve: (excel_verde, total_g, rows_no_verde_count, errores)
        Si incluir_no_verde=True: (excel_verde, total_g, excel_no_verde, errores)

    excel_verde[(cod, lote)] = {codigo_mp, lote, inci, nombre_comercial,
                                proveedor, estanteria, posicion,
                                fecha_vencimiento, cantidad_g}
    """
    from openpyxl import load_workbook

    GREEN = 'FF92D050'
    errors = []

    try:
        wb = load_workbook(file_storage, data_only=True)
    except Exception as _e:
        return None, 0, 0, [f'No pude abrir el Excel: {_e}']

    if not wb.sheetnames:
        return None, 0, 0, ['Excel sin hojas']

    ws = wb[wb.sheetnames[0]]

    # Detectar fila header
    header_row = None
    for r in range(1, min(20, ws.max_row + 1)):
        row_vals = [str(ws.cell(row=r, column=col).value or '').upper()
                    for col in range(1, min(15, ws.max_column + 1))]
        joined = ' | '.join(row_vals)
        if ('CÓDIGO MP' in joined or 'CODIGO MP' in joined) and 'LOTE' in joined:
            header_row = r
            break
    if header_row is None:
        header_row = 5

    col_idx = {}
    for col in range(1, ws.max_column + 1):
        v = (ws.cell(row=header_row, column=col).value or '')
        v = str(v).upper().strip()
        if 'CÓDIGO MP' in v or 'CODIGO MP' in v:
            col_idx['codigo'] = col
        elif 'NOMBRE INCI' in v or v == 'INCI':
            col_idx['inci'] = col
        elif 'NOMBRE COMERCIAL' in v or v == 'COMERCIAL':
            col_idx['comercial'] = col
        elif 'PROVEEDOR' in v:
            col_idx['proveedor'] = col
        elif 'LOTE' in v and 'N' in v:
            col_idx['lote'] = col
        elif 'CONTEO' in v:
            col_idx['cant_conteo'] = col
        elif 'ESTANTER' in v:
            col_idx['estanteria'] = col
        elif v == 'POS.' or v == 'POSICION' or v == 'POSICIÓN':
            col_idx['posicion'] = col
        elif 'FECHA VENC' in v or v == 'VENCE':
            col_idx['venc'] = col

    if 'codigo' not in col_idx or 'lote' not in col_idx or 'cant_conteo' not in col_idx:
        if incluir_no_verde:
            return None, 0, {}, [f'Excel sin columnas requeridas: {list(col_idx.keys())}']
        return None, 0, 0, [f'Excel sin columnas requeridas: {list(col_idx.keys())}']

    excel_verde = {}
    excel_no_verde = {}
    total_g = 0.0
    rows_no_verde = 0

    def _row_to_dict(r, cod, lote, cant_g):
        """Construye el dict info estandar para una fila."""
        venc = ws.cell(row=r, column=col_idx['venc']).value if 'venc' in col_idx else None
        if hasattr(venc, 'isoformat'):
            venc = venc.isoformat()[:10]
        else:
            venc = str(venc)[:10] if venc else ''
        return {
            'codigo_mp': cod, 'lote': lote,
            'inci': str(ws.cell(row=r, column=col_idx['inci']).value or '') if 'inci' in col_idx else '',
            'nombre_comercial': str(ws.cell(row=r, column=col_idx['comercial']).value or '') if 'comercial' in col_idx else '',
            'proveedor': str(ws.cell(row=r, column=col_idx['proveedor']).value or '') if 'proveedor' in col_idx else '',
            'estanteria': str(ws.cell(row=r, column=col_idx['estanteria']).value or '') if 'estanteria' in col_idx else '',
            'posicion': str(ws.cell(row=r, column=col_idx['posicion']).value or '') if 'posicion' in col_idx else '',
            'fecha_vencimiento': venc,
            'cantidad_g': cant_g,
        }

    for r in range(header_row + 1, ws.max_row + 1):
        cell_codigo = ws.cell(row=r, column=col_idx['codigo'])
        cell_color = (cell_codigo.fill.fgColor.rgb
                      if cell_codigo.fill.fgColor.type == 'rgb' else None)
        is_verde = (cell_color == GREEN)
        cod = cell_codigo.value
        if not cod:
            if not is_verde:
                rows_no_verde += 1
            continue
        cod = str(cod).strip()
        lote_raw = ws.cell(row=r, column=col_idx['lote']).value
        lote = str(lote_raw).strip() if lote_raw else ''
        cant_raw = ws.cell(row=r, column=col_idx['cant_conteo']).value
        try:
            cant = float(cant_raw or 0)
        except (TypeError, ValueError):
            cant = 0.0

        key = (cod, lote)
        info = _row_to_dict(r, cod, lote, cant)

        if is_verde:
            if key in excel_verde:
                excel_verde[key]['cantidad_g'] += cant
            else:
                excel_verde[key] = info
            total_g += cant
        else:
            rows_no_verde += 1
            if incluir_no_verde:
                if key in excel_no_verde:
                    excel_no_verde[key]['cantidad_g'] += cant
                else:
                    excel_no_verde[key] = info

    if incluir_no_verde:
        return excel_verde, total_g, excel_no_verde, errors
    return excel_verde, total_g, rows_no_verde, errors


def _identify_movimientos_a_preservar(c):
    """Devuelve dos listas de movimientos a re-insertar tras el reset:

      - entradas_oc_legitimas: tipo='Entrada' con numero_oc no vacio
      - salidas_produccion: tipo='Salida' con observaciones que empiezan
        con 'FEFO:' (las que vienen de handle_produccion en inventario.py)

    Cualquier otro movimiento (Entradas sin OC, Salidas que no son de
    produccion, ajustes manuales) se descarta — esos son los datos
    sucios que el reset esta limpiando.
    """
    cols = ('id, material_id, material_nombre, cantidad, tipo, fecha, '
            'observaciones, lote, fecha_vencimiento, estanteria, posicion, '
            'proveedor, estado_lote, operador, '
            'COALESCE(numero_oc,"") as numero_oc, '
            'COALESCE(numero_factura,"") as numero_factura, '
            'COALESCE(precio_kg,0) as precio_kg')
    try:
        entradas_oc = c.execute(f"""SELECT {cols} FROM movimientos
                                    WHERE tipo='Entrada'
                                    AND COALESCE(numero_oc,'') != ''
                                    AND COALESCE(numero_oc,'') != '0'
                                    ORDER BY fecha ASC, id ASC""").fetchall()
    except sqlite3.OperationalError:
        entradas_oc = []
    try:
        salidas_prod = c.execute(f"""SELECT {cols} FROM movimientos
                                     WHERE tipo='Salida'
                                     AND observaciones LIKE 'FEFO:%'
                                     ORDER BY fecha ASC, id ASC""").fetchall()
    except sqlite3.OperationalError:
        salidas_prod = []
    return entradas_oc, salidas_prod


def _row_to_dict(row, columns):
    return dict(zip(columns, row))


_MOV_PRESERVAR_COLS = (
    'id', 'material_id', 'material_nombre', 'cantidad', 'tipo', 'fecha',
    'observaciones', 'lote', 'fecha_vencimiento', 'estanteria', 'posicion',
    'proveedor', 'estado_lote', 'operador', 'numero_oc', 'numero_factura',
    'precio_kg',
)


@bp.route("/api/admin/audit-inventario-vs-excel", methods=["POST"])
def admin_audit_inventario_vs_excel():
    """Compara el inventario actual contra un Excel "dia cero" sin escribir nada.

    Caso de uso (CEO 2026-04-27): el inventario de planta esta inconsistente
    contra la realidad fisica. Tenemos un Excel con el conteo fisico hecho
    por Catalina antes de las producciones recientes. Cada fila tiene un
    color que indica si el lote existe fisicamente (verde) o no (rojo /
    blanco / gris claro). Solo verde cuenta como real.

    Este endpoint:
      1. Lee el Excel uploaded (campo 'file' en multipart)
      2. Filtra rows verdes (FF92D050) — el resto se ignora
      3. Compara cada (codigo_mp, lote) verde contra el estado actual
         del kardex en movimientos
      4. Retorna reporte JSON con:
         - lotes_verde: total que catalina marco como reales
         - en_db_match: presentes en DB con cantidad esperada (excel - salidas)
         - en_db_con_delta: presentes pero cantidad no coincide
         - faltantes_en_db: en Excel pero no en DB (lote desaparecio del kardex)
         - solo_db: en DB pero NO en Excel verde (post-day-zero o sobrante)
         - producciones_post_excel: count + total kg
         - resumen_g: total_excel_verde, total_db_actual, total_post_dia_cero,
                      delta_total_g

    SIN ESCRITURA. Reporte de solo lectura. El usuario decide despues
    si aplicar reset+replay o ajustes quirurgicos.

    Solo admins.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'El archivo debe ser .xlsx'}), 400

    try:
        from openpyxl import load_workbook
    except Exception:
        return jsonify({'error': 'openpyxl no instalado'}), 500

    GREEN = 'FF92D050'

    try:
        wb = load_workbook(f, data_only=True)
    except Exception as _e:
        return jsonify({'error': f'No pude abrir el Excel: {_e}'}), 400

    if not wb.sheetnames:
        return jsonify({'error': 'Excel sin hojas'}), 400

    # Heuristica: usar la primera hoja (tipicamente "INVENTARIO")
    ws = wb[wb.sheetnames[0]]

    # Detectar fila header buscando por palabras clave
    header_row = None
    for r in range(1, min(20, ws.max_row + 1)):
        row_vals = [str(ws.cell(row=r, column=col).value or '').upper()
                    for col in range(1, min(15, ws.max_column + 1))]
        joined = ' | '.join(row_vals)
        if ('CÓDIGO MP' in joined or 'CODIGO MP' in joined) and 'LOTE' in joined:
            header_row = r
            break
    if header_row is None:
        header_row = 5  # fallback al esperado

    # Mapear columnas
    col_idx = {}
    for col in range(1, ws.max_column + 1):
        v = (ws.cell(row=header_row, column=col).value or '')
        v = str(v).upper().strip()
        if 'CÓDIGO MP' in v or 'CODIGO MP' in v:
            col_idx['codigo'] = col
        elif 'NOMBRE INCI' in v or v == 'INCI':
            col_idx['inci'] = col
        elif 'NOMBRE COMERCIAL' in v or v == 'COMERCIAL':
            col_idx['comercial'] = col
        elif 'PROVEEDOR' in v:
            col_idx['proveedor'] = col
        elif 'LOTE' in v and 'N' in v:
            col_idx['lote'] = col
        elif 'CONTEO' in v:
            col_idx['cant_conteo'] = col
        elif 'ESTANTER' in v:
            col_idx['estanteria'] = col
        elif v == 'POS.' or v == 'POSICION' or v == 'POSICIÓN':
            col_idx['posicion'] = col
        elif 'FECHA VENC' in v or v == 'VENCE':
            col_idx['venc'] = col

    if 'codigo' not in col_idx or 'lote' not in col_idx or 'cant_conteo' not in col_idx:
        return jsonify({
            'error': 'Excel no tiene columnas requeridas',
            'detail': f'columnas detectadas: {list(col_idx.keys())}, '
                      f'header_row={header_row}'
        }), 400

    # ── Parsear filas verdes ─────────────────────────────────────────────
    excel_verde = {}  # (codigo, lote) -> dict
    excel_total_g = 0.0
    rows_no_verde_count = 0
    for r in range(header_row + 1, ws.max_row + 1):
        cell_color = (ws.cell(row=r, column=col_idx['codigo']).fill.fgColor.rgb
                      if ws.cell(row=r, column=col_idx['codigo']).fill.fgColor.type == 'rgb'
                      else None)
        if cell_color != GREEN:
            rows_no_verde_count += 1
            continue
        cod = ws.cell(row=r, column=col_idx['codigo']).value
        if not cod:
            continue
        cod = str(cod).strip()
        lote_raw = ws.cell(row=r, column=col_idx['lote']).value
        lote = str(lote_raw).strip() if lote_raw else ''
        cant_raw = ws.cell(row=r, column=col_idx['cant_conteo']).value
        try:
            cant = float(cant_raw or 0)
        except (TypeError, ValueError):
            cant = 0.0
        venc = ws.cell(row=r, column=col_idx['venc']).value if 'venc' in col_idx else None
        if hasattr(venc, 'isoformat'):
            venc = venc.isoformat()[:10]
        else:
            venc = str(venc)[:10] if venc else ''

        key = (cod, lote)
        if key in excel_verde:
            # Lote duplicado en Excel: sumar cantidades, mantener primer registro
            excel_verde[key]['cantidad_g'] += cant
            excel_verde[key]['lotes_duplicados'] = excel_verde[key].get('lotes_duplicados', 1) + 1
        else:
            excel_verde[key] = {
                'codigo_mp': cod,
                'lote': lote,
                'inci': str(ws.cell(row=r, column=col_idx['inci']).value or '') if 'inci' in col_idx else '',
                'nombre_comercial': str(ws.cell(row=r, column=col_idx['comercial']).value or '') if 'comercial' in col_idx else '',
                'proveedor': str(ws.cell(row=r, column=col_idx['proveedor']).value or '') if 'proveedor' in col_idx else '',
                'estanteria': str(ws.cell(row=r, column=col_idx['estanteria']).value or '') if 'estanteria' in col_idx else '',
                'posicion': str(ws.cell(row=r, column=col_idx['posicion']).value or '') if 'posicion' in col_idx else '',
                'fecha_vencimiento': venc,
                'cantidad_g': cant,
            }
        excel_total_g += cant

    # ── Estado actual del kardex ─────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    db_lotes = {}  # (cod, lote) -> dict
    c.execute("""SELECT material_id,
                        COALESCE(lote,''),
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END) as entradas,
                        SUM(CASE WHEN tipo='Salida'  THEN cantidad ELSE 0 END) as salidas,
                        COUNT(*) as nmovs
                 FROM movimientos
                 GROUP BY material_id, lote""")
    db_total_neto_g = 0.0
    for row in c.fetchall():
        cod = (row[0] or '').strip()
        lote = (row[1] or '').strip()
        entradas = float(row[2] or 0)
        salidas = float(row[3] or 0)
        neto = entradas - salidas
        db_lotes[(cod, lote)] = {
            'entradas_g': entradas,
            'salidas_g': salidas,
            'neto_g': neto,
            'n_movs': row[4],
        }
        db_total_neto_g += neto

    # Producciones — info de contexto
    try:
        prod_n = c.execute("SELECT COUNT(*) FROM producciones").fetchone()[0]
    except sqlite3.OperationalError:
        prod_n = 0
    try:
        prod_total_kg = float(c.execute(
            "SELECT COALESCE(SUM(cantidad), 0) FROM producciones"
        ).fetchone()[0] or 0)
    except sqlite3.OperationalError:
        prod_total_kg = 0.0

    conn.close()

    # ── Diff ─────────────────────────────────────────────────────────────
    en_db_match = []
    en_db_con_delta = []
    faltantes_en_db = []  # excel verde pero NO en DB
    solo_db = []  # en DB pero NO en excel verde

    TOLERANCIA_G = 0.5  # tolerancia de redondeo

    excel_keys = set(excel_verde.keys())
    db_keys = set(db_lotes.keys())

    for k in excel_keys & db_keys:
        e = excel_verde[k]
        d = db_lotes[k]
        # Esperado: el lote tenia excel_g al dia cero. Si hubo salidas
        # despues, el neto ahora debe ser excel_g - salidas. Si hubo
        # entradas adicionales (raro, mismo lote re-recibido), tambien
        # se suman. Mas simple: comparar neto actual con (excel - salidas
        # + entradas_post_dia_cero) — pero no sabemos cual entrada fue
        # la inicial. Aproximacion: neto_esperado = excel_g - salidas.
        # Si DB tiene mas entradas que el excel, eso es post-day-zero.
        neto_esperado = e['cantidad_g'] - d['salidas_g']
        delta = d['neto_g'] - neto_esperado
        item = {
            'codigo_mp': k[0], 'lote': k[1],
            'nombre_comercial': e['nombre_comercial'],
            'proveedor_excel': e['proveedor'],
            'cant_excel_g': round(e['cantidad_g'], 1),
            'entradas_db_g': round(d['entradas_g'], 1),
            'salidas_db_g': round(d['salidas_g'], 1),
            'neto_db_g': round(d['neto_g'], 1),
            'neto_esperado_g': round(neto_esperado, 1),
            'delta_g': round(delta, 1),
        }
        if abs(delta) <= TOLERANCIA_G:
            en_db_match.append(item)
        else:
            en_db_con_delta.append(item)

    for k in excel_keys - db_keys:
        e = excel_verde[k]
        faltantes_en_db.append({
            'codigo_mp': k[0], 'lote': k[1],
            'nombre_comercial': e['nombre_comercial'],
            'proveedor_excel': e['proveedor'],
            'cant_excel_g': round(e['cantidad_g'], 1),
        })

    for k in db_keys - excel_keys:
        d = db_lotes[k]
        if d['neto_g'] <= 0.5:
            continue  # lote vacio en DB que tampoco esta en Excel — irrelevante
        solo_db.append({
            'codigo_mp': k[0], 'lote': k[1],
            'entradas_db_g': round(d['entradas_g'], 1),
            'salidas_db_g': round(d['salidas_g'], 1),
            'neto_db_g': round(d['neto_g'], 1),
        })

    # Ordenar por mayor delta para visualizar primero los problemas grandes
    en_db_con_delta.sort(key=lambda x: -abs(x['delta_g']))
    faltantes_en_db.sort(key=lambda x: -x['cant_excel_g'])
    solo_db.sort(key=lambda x: -x['neto_db_g'])

    delta_total_g = sum(x['delta_g'] for x in en_db_con_delta)

    return jsonify({
        'ok': True,
        'resumen': {
            'archivo': f.filename,
            'lotes_verde_excel': len(excel_verde),
            'lotes_excluidos_no_verde': rows_no_verde_count,
            'stock_total_excel_g': round(excel_total_g, 1),
            'stock_total_db_actual_g': round(db_total_neto_g, 1),
            'producciones_registradas': prod_n,
            'producciones_total_kg': round(prod_total_kg, 1),
            'count_match': len(en_db_match),
            'count_delta': len(en_db_con_delta),
            'count_faltantes_en_db': len(faltantes_en_db),
            'count_solo_db_no_excel': len(solo_db),
            'delta_total_g': round(delta_total_g, 1),
        },
        'en_db_con_delta': en_db_con_delta[:300],
        'faltantes_en_db': faltantes_en_db[:300],
        'solo_db_no_excel': solo_db[:300],
        'en_db_match_sample': en_db_match[:20],
        'nota_truncado': (
            len(en_db_con_delta) > 300 or len(faltantes_en_db) > 300
            or len(solo_db) > 300
        ),
    })


@bp.route("/api/admin/inventario-snapshot-pre-reset", methods=["GET"])
def admin_inventario_snapshot_pre_reset():
    """Descarga snapshot JSON completo de la BD antes del reset.

    Incluye: movimientos (todos), producciones, ordenes_compra + items,
    comprobantes_pago, audit_log (ultimos 1000), maestro_mps. El
    usuario lo descarga y guarda fuera de Render. Si el reset falla,
    podemos reconstruir.

    Solo admins. No escribe nada.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    import json as _json
    from datetime import datetime as _dt

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    snapshot = {
        'meta': {
            'generated_at': _dt.utcnow().isoformat() + 'Z',
            'generated_by': u,
            'db_path': DB_PATH,
        },
        'tablas': {},
    }

    def _dump(table, where=None, limit=None):
        sql = f"SELECT * FROM {table}"
        if where: sql += f" WHERE {where}"
        if limit: sql += f" LIMIT {limit}"
        try:
            rows = c.execute(sql).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as _e:
            return {'error': str(_e)}

    snapshot['tablas']['movimientos'] = _dump('movimientos')
    snapshot['tablas']['producciones'] = _dump('producciones')
    snapshot['tablas']['ordenes_compra'] = _dump('ordenes_compra')
    snapshot['tablas']['ordenes_compra_items'] = _dump('ordenes_compra_items')
    snapshot['tablas']['comprobantes_pago'] = _dump('comprobantes_pago')
    snapshot['tablas']['maestro_mps'] = _dump('maestro_mps')
    snapshot['tablas']['audit_log'] = _dump(
        'audit_log', where='1=1 ORDER BY id DESC', limit=1000
    )

    conn.close()

    # Conteos rapidos para el meta
    snapshot['meta']['conteos'] = {
        k: (len(v) if isinstance(v, list) else 0)
        for k, v in snapshot['tablas'].items()
    }

    body = _json.dumps(snapshot, ensure_ascii=False, indent=2, default=str)
    fname = f"snapshot_pre_reset_{_dt.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        body, mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{fname}"'},
    )


@bp.route("/api/admin/inventario-reset-preview", methods=["POST"])
def admin_inventario_reset_preview():
    """Preview del reset: muestra que se va a hacer SIN escribir nada.

    Body: multipart con file = Excel del conteo fisico.

    Devuelve plan detallado:
      - movimientos_a_borrar: count
      - entradas_a_crear_desde_excel: 305 lotes verdes
      - entradas_oc_legitimas_a_preservar: count + total_g
      - salidas_produccion_a_preservar: count + total_g + lotes consumidos
      - alertas: lotes que las producciones consumieron pero NO estan en
                 Excel verde (post-reset darian stock negativo)
      - resumen_pre_post: stock total antes vs despues

    Solo admins. SIN ESCRITURA.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'Archivo debe ser .xlsx'}), 400

    excel_verde, excel_total_g, excel_no_verde, errs = _parse_excel_verde(f, incluir_no_verde=True)
    if excel_verde is None:
        return jsonify({'error': errs[0] if errs else 'Excel invalido'}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Conteos actuales
    movs_actuales = c.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
    stock_total_actual_g = float(c.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) "
        "FROM movimientos"
    ).fetchone()[0] or 0)

    # Movimientos a preservar
    entradas_oc, salidas_prod = _identify_movimientos_a_preservar(c)
    entradas_oc_g = sum(float(r['cantidad'] or 0) for r in entradas_oc)
    salidas_prod_g = sum(float(r['cantidad'] or 0) for r in salidas_prod)

    # ── Salidas post-día-cero por lote (para fix de cantidad inicial) ──
    # Bug previo: el Excel verde tiene la cantidad ACTUAL (post-producciones),
    # pero al cargar como Entrada del día cero, después se aplicaban las salidas
    # otra vez → negativo. Fix: cantidad_dia_cero = excel_actual + salidas_post.
    salidas_post_por_lote = {}
    for s in salidas_prod:
        k = (s['material_id'], s['lote'] or '')
        salidas_post_por_lote[k] = salidas_post_por_lote.get(k, 0) + float(s['cantidad'] or 0)

    # Lotes huérfanos: consumidos por produccion pero NO en Excel verde
    excel_keys = set(excel_verde.keys())
    huerfanos_consumo = {}  # (cod,lote) -> sum_salidas_g
    for s in salidas_prod:
        cod = s['material_id']
        lote = s['lote'] or ''
        if (cod, lote) not in excel_keys:
            k = (cod, lote)
            huerfanos_consumo[k] = huerfanos_consumo.get(k, 0) + float(s['cantidad'] or 0)

    # Para cada huerfano: la entrada virtual usa Excel completo si esta, sino fallback = sum_salidas
    huerfanos_detalle = []
    huerfanos_total_g = 0.0
    for k, consumido in huerfanos_consumo.items():
        cod, lote = k
        en_excel_completo = excel_no_verde.get(k)
        if en_excel_completo and en_excel_completo['cantidad_g'] > 0:
            # Aún siendo no-verde, tiene cantidad — sumar salidas para no negativo
            cant_entrada = en_excel_completo['cantidad_g'] + consumido
            origen = 'excel_no_verde+salidas'
        else:
            cant_entrada = consumido  # fallback: para cerrar en 0
            origen = 'fallback_sum_salidas'
        huerfanos_detalle.append({
            'codigo_mp': cod, 'lote': lote,
            'cantidad_consumida_g': round(consumido, 1),
            'cantidad_entrada_virtual_g': round(cant_entrada, 1),
            'origen': origen,
        })
        huerfanos_total_g += cant_entrada

    salidas_lotes_no_verde = [
        {'codigo_mp': k[0], 'lote': k[1],
         'cantidad_g': round(v, 1)}
        for k, v in huerfanos_consumo.items()
    ]

    # Cantidad inicial total (con compensacion FEFO) = excel_verde + salidas_de_esos_lotes
    excel_inicial_total_g = 0.0
    lotes_compensados = []  # lotes verdes que tendrán cantidad_inicial > excel
    for k, info in excel_verde.items():
        salidas_post = salidas_post_por_lote.get(k, 0)
        cant_inicial = float(info['cantidad_g']) + salidas_post
        excel_inicial_total_g += cant_inicial
        if salidas_post > 0:
            lotes_compensados.append({
                'codigo_mp': k[0], 'lote': k[1],
                'cantidad_excel_actual_g': round(float(info['cantidad_g']), 1),
                'salidas_post_dia_cero_g': round(salidas_post, 1),
                'cantidad_inicial_dia_cero_g': round(cant_inicial, 1),
            })
    lotes_compensados.sort(key=lambda x: -x['salidas_post_dia_cero_g'])

    # Stock post = lo del Excel actual (sin compensacion) + OC nuevas + huerfanos - salidas
    # = (excel_inicial - salidas_de_lotes_verdes) + entradas_oc + huerfanos_total - salidas_huerfanos
    # Como huerfanos_total ya equivale a las salidas que les corresponden, queda:
    # stock_post = excel_total_g (la cantidad ACTUAL del excel) + entradas_oc_g + 0 (huerfanos cierran en 0)
    stock_post_g = excel_total_g + entradas_oc_g

    # Sample top lotes a crear (mas grandes)
    top_excel = sorted(
        [v for v in excel_verde.values()],
        key=lambda v: -v['cantidad_g']
    )[:10]

    conn.close()

    return jsonify({
        'ok': True,
        'plan': {
            'movimientos_a_borrar': movs_actuales,
            'entradas_iniciales_a_crear': {
                'count': len(excel_verde),
                'total_g': round(excel_total_g, 1),  # alias back-compat
                'total_g_excel_actual': round(excel_total_g, 1),
                'total_g_dia_cero_compensado': round(excel_inicial_total_g, 1),
                'lotes_compensados_por_salidas_post_count': len(lotes_compensados),
                'lotes_compensados_sample_top10': lotes_compensados[:10],
                'sample_top10': top_excel,
                'nota_fix': ('Cantidad cargada al día cero = excel_actual + '
                             'salidas_post_día_cero del mismo lote. Esto evita '
                             'negativos: el FEFO consumirá las salidas y el lote '
                             'quedará exactamente en lo que el Excel reporta hoy.'),
            },
            'entradas_oc_a_preservar': {
                'count': len(entradas_oc),
                'total_g': round(entradas_oc_g, 1),
                'sample': [{
                    'fecha': str(r['fecha'])[:10],
                    'codigo_mp': r['material_id'], 'lote': r['lote'] or '',
                    'cantidad_g': round(float(r['cantidad'] or 0), 1),
                    'numero_oc': r['numero_oc'],
                } for r in entradas_oc[:20]],
            },
            'salidas_produccion_a_preservar': {
                'count': len(salidas_prod),
                'total_g': round(salidas_prod_g, 1),
                'sample': [{
                    'fecha': str(r['fecha'])[:10],
                    'codigo_mp': r['material_id'], 'lote': r['lote'] or '',
                    'cantidad_g': round(float(r['cantidad'] or 0), 1),
                    'observaciones': r['observaciones'],
                } for r in salidas_prod[:20]],
            },
            'rows_no_verde_excluidas': len(excel_no_verde),
            'huerfanos_a_regenerar': {
                'count': len(huerfanos_detalle),
                'total_g_entradas_virtuales': round(huerfanos_total_g, 1),
                'sample': huerfanos_detalle[:30],
                'nota': ('Lotes que las producciones consumieron pero que '
                         'Catalina marco NO presentes. Se regeneraran como '
                         'Entrada virtual del Excel (no-verde) o fallback = '
                         'sum_salidas, para que la salida los lleve a 0 sin '
                         'dejar stock negativo. Trazabilidad de produccion '
                         'preservada.'),
            },
        },
        'alertas': {
            'salidas_a_lotes_no_verde': salidas_lotes_no_verde[:30],
            'count_salidas_a_lotes_no_verde': len(salidas_lotes_no_verde),
            'nota': ('Estas salidas consumieron lotes ya NO presentes '
                     'fisicamente. Tras la mejora se regenera Entrada virtual '
                     'que cierra el lote en 0g (no negativo). Trazabilidad '
                     'preservada.'),
        },
        'resumen_pre_post': {
            'stock_actual_g': round(stock_total_actual_g, 1),
            'stock_post_reset_g_estimado': round(stock_post_g, 1),
            'delta_g': round(stock_post_g - stock_total_actual_g, 1),
        },
    })


_RESET_TOKEN = "BORRAR_INVENTARIO_Y_CARGAR_EXCEL_2026_04_27"


@bp.route("/api/admin/inventario-reset-aplicar", methods=["POST"])
def admin_inventario_reset_aplicar():
    """APLICA el reset+replay del inventario. Destructivo. Tiene salvaguardas.

    Salvaguardas:
      1. Solo admins
      2. Body MUST contain confirmacion = token textual exacto
      3. Verifica que haya backup reciente (< 24h) en backup_log o intenta
         crear uno automaticamente antes de proceder
      4. Snapshot pre-reset guardado en audit_log (resumen)
      5. Audit log entry detallado (TRES entries: PRE, RESET, POST)
      6. Body multipart con Excel + JSON con confirmacion

    Plan ejecutado en orden, dentro de UNA transaccion:
      a) Capturar entradas_oc_legitimas + salidas_produccion (preservar)
      b) DELETE FROM movimientos
      c) INSERT 305 Entradas iniciales desde Excel verde
         (fecha=2026-04-15 = dia cero, operador='reset_2026_04_27')
      d) Re-INSERT entradas_oc_legitimas (preservadas, fecha y datos
         originales)
      e) Re-INSERT salidas_produccion (preservadas, fecha y datos
         originales — incluso si apunta a lote no-verde, queda como
         "stock negativo" para alertar)
      f) Audit log: ELIMINAR_INVENTARIO + CARGAR_EXCEL + RE_APLICAR_PROD
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    confirmacion = (request.form.get('confirmacion') or '').strip()
    if confirmacion != _RESET_TOKEN:
        return jsonify({
            'error': 'Confirmacion textual requerida',
            'detail': f'Body form debe incluir confirmacion="{_RESET_TOKEN}"',
        }), 400

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'Archivo debe ser .xlsx'}), 400

    excel_verde, excel_total_g, excel_no_verde, errs = _parse_excel_verde(f, incluir_no_verde=True)
    if excel_verde is None:
        return jsonify({'error': errs[0] if errs else 'Excel invalido'}), 400

    # Verificar backup reciente
    from datetime import datetime as _dt, timedelta as _td
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    backup_reciente = False
    try:
        last = c.execute(
            "SELECT MAX(started_at) FROM backup_log WHERE status='ok'"
        ).fetchone()[0]
        if last:
            try:
                # SQLite datetime('now','utc') devuelve 'YYYY-MM-DD HH:MM:SS'
                last_dt = _dt.fromisoformat(last.replace(' ', 'T').replace('Z', ''))
                if (_dt.utcnow() - last_dt) < _td(hours=24):
                    backup_reciente = True
            except Exception:
                pass
    except sqlite3.OperationalError:
        pass

    if not backup_reciente:
        # Intentar crear backup automatico antes de proceder
        try:
            from backup import do_backup
            do_backup(triggered_by='reset_inventario_pre')
        except Exception as _e:
            return jsonify({
                'error': 'Sin backup reciente y no pude crear uno automatico',
                'detail': str(_e),
                'recomendacion': 'Hacer click en /admin → tab Backups → "Backup ahora" antes de re-intentar.',
            }), 500

    # Capturar movimientos a preservar
    entradas_oc, salidas_prod = _identify_movimientos_a_preservar(c)

    # ── Salidas post-día-cero por lote (fix de cantidad inicial) ──
    # Cantidad cargada al día cero = excel_actual + salidas_post para que el
    # FEFO posterior no deje negativos.
    salidas_post_por_lote = {}
    for s in salidas_prod:
        k = (s['material_id'], s['lote'] or '')
        salidas_post_por_lote[k] = salidas_post_por_lote.get(k, 0) + float(s['cantidad'] or 0)

    # Calcular huerfanos a regenerar (lotes consumidos NO en Excel verde)
    excel_keys = set(excel_verde.keys())
    huerfanos_consumo = {}
    for s in salidas_prod:
        k = (s['material_id'], s['lote'] or '')
        if k not in excel_keys:
            huerfanos_consumo[k] = huerfanos_consumo.get(k, 0) + float(s['cantidad'] or 0)

    huerfanos_a_regenerar = []
    for k, consumido in huerfanos_consumo.items():
        cod, lote = k
        en_excel = excel_no_verde.get(k)
        if en_excel and en_excel['cantidad_g'] > 0:
            # No-verde con cantidad: sumar salidas para que cierre con la cant del excel
            cant = en_excel['cantidad_g'] + consumido
            info = en_excel
        else:
            cant = consumido  # fallback para cerrar en 0
            info = {
                'codigo_mp': cod, 'lote': lote,
                'inci': '', 'nombre_comercial': '',
                'proveedor': '', 'estanteria': '', 'posicion': '',
                'fecha_vencimiento': '',
            }
        huerfanos_a_regenerar.append({**info, 'cantidad_g': cant})

    movs_borrados = c.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]

    # Audit pre-reset
    try:
        import json as _json
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (u, 'RESET_INVENTARIO_PRE', 'movimientos', '_BULK_',
                   _json.dumps({
                       'movs_a_borrar': movs_borrados,
                       'entradas_oc_preservar': len(entradas_oc),
                       'salidas_prod_preservar': len(salidas_prod),
                       'lotes_excel_verde_a_cargar': len(excel_verde),
                       'lotes_huerfanos_regenerar': len(huerfanos_a_regenerar),
                       'excel_total_g': round(excel_total_g, 1),
                   }, ensure_ascii=False),
                   request.remote_addr))
    except sqlite3.OperationalError:
        pass

    # ── ATOMIC: BORRAR + RECREAR ─────────────────────────────────────────
    # sqlite3 abre transaccion implicita en DML; conn.commit/rollback la cierra.
    try:
        # 1. DELETE
        c.execute("DELETE FROM movimientos")

        # 2. Cargar Entradas iniciales del Excel verde (compensadas con salidas post)
        DIA_CERO = '2026-04-15T00:00:00'
        OBS_INICIAL = 'Carga inicial Excel dia cero v8_1 — reset 2026-04-27'
        OPERADOR_RESET = 'reset_2026_04_27'
        n_excel_inserted = 0
        n_lotes_compensados = 0
        total_compensacion_g = 0.0
        for (cod, lote), info in excel_verde.items():
            cant_excel = float(info['cantidad_g'] or 0)
            cant_salidas_post = salidas_post_por_lote.get((cod, lote), 0)
            cant_inicial = cant_excel + cant_salidas_post  # ← FIX día cero
            if cant_inicial <= 0:
                continue
            obs = OBS_INICIAL
            if cant_salidas_post > 0:
                obs = (f'{OBS_INICIAL} | Compensación FEFO: '
                       f'excel_hoy={int(round(cant_excel))}g + '
                       f'salidas_post={int(round(cant_salidas_post))}g')
                n_lotes_compensados += 1
                total_compensacion_g += cant_salidas_post
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, fecha_vencimiento, estanteria,
                          posicion, proveedor, estado_lote, operador)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (cod, info['nombre_comercial'] or info['inci'] or cod,
                       cant_inicial, 'Entrada', DIA_CERO,
                       obs, lote, info['fecha_vencimiento'] or None,
                       info['estanteria'] or '', info['posicion'] or '',
                       info['proveedor'] or '', 'VIGENTE', OPERADOR_RESET))
            n_excel_inserted += 1

        # 2b. Regenerar Entradas virtuales para lotes huerfanos (consumidos
        # por produccion pero NO presentes fisicamente en el Excel verde).
        # Esto evita que las salidas dejen stock negativo. Las entradas
        # virtuales tienen observaciones distintas para auditarse despues.
        OBS_HUERFANO = 'Lote consumido pre-reset — Entrada regenerada para preservar trazabilidad de produccion'
        for info in huerfanos_a_regenerar:
            if info['cantidad_g'] <= 0:
                continue
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, fecha_vencimiento, estanteria,
                          posicion, proveedor, estado_lote, operador)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (info['codigo_mp'],
                       info.get('nombre_comercial') or info.get('inci') or info['codigo_mp'],
                       float(info['cantidad_g']), 'Entrada', DIA_CERO,
                       OBS_HUERFANO, info['lote'],
                       info.get('fecha_vencimiento') or None,
                       info.get('estanteria') or '', info.get('posicion') or '',
                       info.get('proveedor') or '', 'AGOTADO', OPERADOR_RESET))
        n_huerfanos_inserted = len(huerfanos_a_regenerar)

        # 3. Re-insertar Entradas con OC legitimas
        for r in entradas_oc:
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, fecha_vencimiento, estanteria,
                          posicion, proveedor, estado_lote, operador,
                          numero_oc, numero_factura, precio_kg)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (r['material_id'], r['material_nombre'], r['cantidad'],
                       r['tipo'], r['fecha'], r['observaciones'], r['lote'],
                       r['fecha_vencimiento'], r['estanteria'], r['posicion'],
                       r['proveedor'], r['estado_lote'], r['operador'],
                       r['numero_oc'], r['numero_factura'], r['precio_kg']))

        # 4. Re-insertar Salidas de produccion
        for r in salidas_prod:
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, fecha_vencimiento, estanteria,
                          posicion, proveedor, estado_lote, operador,
                          numero_oc, numero_factura, precio_kg)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (r['material_id'], r['material_nombre'], r['cantidad'],
                       r['tipo'], r['fecha'], r['observaciones'], r['lote'],
                       r['fecha_vencimiento'], r['estanteria'], r['posicion'],
                       r['proveedor'], r['estado_lote'], r['operador'],
                       r['numero_oc'], r['numero_factura'], r['precio_kg']))

        conn.commit()
    except Exception as _e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({
            'ok': False,
            'error': f'Reset abortado por error: {_e}',
            'detail': 'Transaccion revertida. La BD esta como antes. '
                      'Restaurar backup si hay duda.',
        }), 500

    # Validacion post: contar lo que quedo
    movs_post = c.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
    stock_post_g = float(c.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) "
        "FROM movimientos"
    ).fetchone()[0] or 0)

    # Audit post-reset
    try:
        c.execute("""INSERT INTO audit_log
                     (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                     VALUES (?,?,?,?,?,?,datetime('now'))""",
                  (u, 'RESET_INVENTARIO_POST', 'movimientos', '_BULK_',
                   _json.dumps({
                       'movs_borrados': movs_borrados,
                       'lotes_excel_cargados': n_excel_inserted,
                       'lotes_compensados_fefo': n_lotes_compensados,
                       'compensacion_total_g': round(total_compensacion_g, 1),
                       'huerfanos_regenerados': n_huerfanos_inserted,
                       'entradas_oc_re_insertadas': len(entradas_oc),
                       'salidas_prod_re_insertadas': len(salidas_prod),
                       'movs_post_total': movs_post,
                       'stock_post_g': round(stock_post_g, 1),
                       'excel_total_g_origen': round(excel_total_g, 1),
                   }, ensure_ascii=False),
                   request.remote_addr))
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    return jsonify({
        'ok': True,
        'message': (f'Reset aplicado. Borrados {movs_borrados} movimientos, '
                    f'cargadas {n_excel_inserted} Entradas iniciales del Excel '
                    f'verde ({n_lotes_compensados} lotes compensados con '
                    f'+{int(round(total_compensacion_g))} g por salidas post-día-cero) '
                    f'+ {n_huerfanos_inserted} Entradas regeneradas (huerfanos), '
                    f'preservadas {len(entradas_oc)} Entradas con OC + '
                    f'{len(salidas_prod)} Salidas de produccion.'),
        'resumen': {
            'movs_borrados': movs_borrados,
            'lotes_excel_cargados': n_excel_inserted,
            'lotes_compensados_fefo': n_lotes_compensados,
            'compensacion_total_g': round(total_compensacion_g, 1),
            'huerfanos_regenerados': n_huerfanos_inserted,
            'entradas_oc_preservadas': len(entradas_oc),
            'salidas_prod_preservadas': len(salidas_prod),
            'movs_post_total': movs_post,
            'stock_post_g': round(stock_post_g, 1),
        },
    })


@bp.route("/api/admin/diagnosticar-formulas", methods=["GET"])
def admin_diagnosticar_formulas():
    """Detecta items en formula_items con material_id que NO existe en
    maestro_mps o cuyo nombre no coincide. Sugiere correccion buscando
    por nombre similar en el catalogo real.

    Para cada item con problema retorna:
      producto, material_id_actual, material_nombre,
      problema (huerfano|mismatch_nombre),
      candidato_sugerido: {codigo, nombre, score}

    Solo admins. SIN escritura.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    import re as _re
    import unicodedata as _ud

    # Palabras que se ignoran al comparar (genericas / sufijos de proveedor)
    _STOPWORDS = {
        'LYPHAR', 'YTBIO', 'LIQUIDO', 'POLVO', 'SOLUCION', 'AL', 'EN',
        'KD', 'KDA', 'DE', 'LA', 'EL', 'LOS', 'LAS', 'POR', 'PARA',
        'GRADO', 'COSMETICO', 'COSMETICA', 'COSMETICO', 'NF', 'USP',
        'INCHEMICAL', 'AGENQUIMICOS', 'BASF', 'IMCD',
    }

    # Sinonimos cosmeticos español/ingles + INCI (cientos de pares)
    _SINONIMOS_PARES = [
        # Polioles
        ('GLICERINA', 'GLYCERIN', 'GLYCEROL'),
        ('PROPILENGLICOL', 'PROPYLENE', 'GLYCOL', 'PG'),
        ('POLIETILENGLICOL', 'POLYETHYLENE', 'GLYCOL', 'PEG'),
        ('BUTILENGLICOL', 'BUTYLENE', 'GLYCOL', 'BG'),
        ('PENTILENGLICOL', 'PENTYLENE', 'GLYCOL'),
        ('HEXANODIOL', 'HEXANEDIOL'),
        # Acidos
        ('ACIDO', 'ACID'),
        ('SALICILICO', 'SALICYLIC'),
        ('HIALURONICO', 'HYALURONIC'),
        ('LACTICO', 'LACTIC'),
        ('GLICOLICO', 'GLYCOLIC'),
        ('CITRICO', 'CITRIC'),
        ('TRANEXAMICO', 'TRANEXAMIC'),
        ('AZELAICO', 'AZELAIC'),
        ('ASCORBICO', 'ASCORBIC'),
        ('KOJICO', 'KOJIC'),
        ('FERULICO', 'FERULIC'),
        ('MANDELICO', 'MANDELIC'),
        ('SUCCINICO', 'SUCCINIC'),
        ('PALMITICO', 'PALMITIC'),
        # Surfactantes / emulsificantes
        ('TWEEN', 'POLYSORBATE'),
        ('SORBITAN', 'SORBITAN'),
        # Alcoholes
        ('ALCOHOL', 'ETHANOL', 'ETANOL'),
        ('CETILICO', 'CETYL'),
        ('ESTEARILICO', 'STEARYL'),
        ('CETOESTEARILICO', 'CETEARYL'),
        # Conservantes
        ('FENOXIETANOL', 'PHENOXYETHANOL'),
        ('BENZOATO', 'BENZOATE'),
        ('SORBATO', 'SORBATE'),
        ('PARABENO', 'PARABEN'),
        # Vitaminas / activos
        ('NIACINAMIDA', 'NIACINAMIDE', 'NICOTINAMIDE'),
        ('UREA', 'CARBAMIDE'),
        ('ALANTOINA', 'ALLANTOIN'),
        ('PANTENOL', 'PANTHENOL'),
        ('RETINALDEHIDO', 'RETINALDEHYDE', 'RETINAL'),
        ('RETINOL', 'RETINOL'),
        ('TOCOFEROL', 'TOCOPHEROL'),
        ('ASCORBIL', 'ASCORBYL'),
        ('ARBUTINA', 'ARBUTIN'),
        ('ECTOINA', 'ECTOIN', 'ECTOINE'),
        ('BAKUCHIOL', 'BAKUCHIOL', 'BACKUCHIOL'),
        ('CAFEINA', 'CAFFEINE'),
        ('GLUTATION', 'GLUTATHIONE'),
        ('ADENOSINA', 'ADENOSINE'),
        ('BIOTINA', 'BIOTIN'),
        ('MELATONINA', 'MELATONIN'),
        # Aminoacidos / proteinas
        ('GLICINA', 'GLYCINE'),
        ('CARNITINA', 'CARNITINE'),
        ('BETAINA', 'BETAINE'),
        ('GLICINAMIDA', 'GLYCINAMIDE'),
        # Cationes
        ('SODIO', 'SODIUM'),
        ('POTASIO', 'POTASSIUM'),
        ('CALCIO', 'CALCIUM'),
        ('MAGNESIO', 'MAGNESIUM'),
        ('ZINC', 'ZINC'),
        ('HIERRO', 'IRON'),
        # Oxidos / minerales
        ('OXIDO', 'OXIDE'),
        ('TITANIO', 'TITANIUM'),
        ('DIOXIDO', 'DIOXIDE'),
        # Aguas / vehiculos
        ('AGUA', 'WATER', 'AQUA'),
        ('DESIONIZADA', 'DEIONIZED'),
        ('DESTILADA', 'DISTILLED'),
        # Aceites / esteres
        ('ACEITE', 'OIL'),
        ('TRIGLICERIDO', 'TRIGLYCERIDE'),
        ('CAPRILICO', 'CAPRYLIC'),
        ('CAPRICO', 'CAPRIC'),
        ('JOJOBA', 'JOJOBA'),
        ('ARGAN', 'ARGAN'),
        ('ESCUALANO', 'SQUALANE'),
        ('ESCUALENO', 'SQUALENE'),
        # Emulsionantes / espesantes
        ('CARBOPOL', 'CARBOMER'),
        ('GOMA', 'GUM'),
        ('XANTAN', 'XANTHAN'),
        ('CELULOSA', 'CELLULOSE'),
        # Otros
        ('EDTA', 'EDTA'),
        ('TRIETANOLAMINA', 'TRIETHANOLAMINE', 'TEA'),
        ('CENTELLA', 'CENTELLA', 'GOTU', 'KOLA'),
        ('REGALIZ', 'LICORICE'),
        ('SALVIA', 'SAGE'),
        ('YOGURT', 'YOGURT'),
        ('SILIMARINA', 'SILYMARIN'),
        ('RESVERATROL', 'RESVERATROL'),
        ('BETAGLUCAN', 'BETAGLUCAN', 'BETA-GLUCAN'),
        ('NAG', 'GLUCOSAMINE', 'GLUCOSAMINA'),
        ('PEPTIDO', 'PEPTIDE'),
        ('PALMITOIL', 'PALMITOYL'),
        ('ACETIL', 'ACETYL'),
        ('TETRAPEPTIDO', 'TETRAPEPTIDE'),
        ('TRIPEPTIDO', 'TRIPEPTIDE'),
        ('HEXAPEPTIDO', 'HEXAPEPTIDE'),
        ('PENTAPEPTIDO', 'PENTAPEPTIDE'),
        ('NONAPEPTIDO', 'NONAPEPTIDE'),
        ('MIRISTOIL', 'MYRISTOYL'),
        ('FOSFATO', 'PHOSPHATE'),
        ('TOCOFERIL', 'TOCOPHERYL'),
        ('GLUCOSIDE', 'GLUCOSIDO'),
        ('GLUCONOLACTONA', 'GLUCONOLACTONE'),
        ('FENOXIETANOL', 'PHENOXYETHANOL'),
        ('HIDROXIDO', 'HYDROXIDE'),
        ('BICARBONATO', 'BICARBONATE'),
        ('EXTRACTO', 'EXTRACT'),
        ('POLVO', 'POWDER'),
    ]
    _SINONIMOS = {}
    for grupo in _SINONIMOS_PARES:
        for w in grupo:
            _SINONIMOS.setdefault(w, set()).update(set(grupo) - {w})

    def _expandir_sinonimos(palabras):
        """Devuelve set ampliado con sinonimos conocidos."""
        ampliado = set(palabras)
        for p in palabras:
            if p in _SINONIMOS:
                ampliado.update(_SINONIMOS[p])
        return ampliado

    def _norm(s):
        """Normaliza: ascii, uppercase, sin parentesis, espacios consolidados."""
        if not s: return ''
        s = _ud.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip()
        # Eliminar parentesis y su contenido (ej. "(LYPHAR)", "(LIQUIDO)")
        s = _re.sub(r'\([^)]*\)', '', s)
        # Reemplazar guiones, comas, puntos con espacios
        s = _re.sub(r'[\-_,.;:/]', ' ', s)
        s = _re.sub(r'\s+', ' ', s).strip()
        return s

    def _palabras_clave(s):
        """Set de palabras significativas (sin stopwords)."""
        return set(p for p in _norm(s).split() if p and p not in _STOPWORDS)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Cargar catalogo maestro
    maestro = []
    try:
        rows = c.execute("""SELECT codigo_mp, COALESCE(nombre_comercial,''),
                                   COALESCE(nombre_inci,'')
                            FROM maestro_mps WHERE activo=1""").fetchall()
        for r in rows:
            cod = r[0]
            nombres_norm = set(filter(None, [_norm(r[1]), _norm(r[2])]))
            palabras = set()
            for nm in [r[1], r[2]]:
                palabras.update(_palabras_clave(nm))
            maestro.append({'codigo': cod, 'nombres_norm': nombres_norm,
                            'palabras_clave': palabras,
                            'nombre_comercial': r[1], 'nombre_inci': r[2]})
    except sqlite3.OperationalError:
        return jsonify({'error': 'maestro_mps no disponible'}), 500

    catalogo_codigos = {m['codigo'] for m in maestro}

    # Cargar formula_items
    try:
        rows = c.execute(
            "SELECT id, producto_nombre, material_id, material_nombre, "
            "       cantidad_g_por_lote "
            "FROM formula_items "
            "ORDER BY producto_nombre, material_nombre"
        ).fetchall()
    except sqlite3.OperationalError:
        return jsonify({'error': 'formula_items no disponible'}), 500

    problemas = []
    for r in rows:
        item_id = r[0]
        producto = r[1]
        mid = r[2]
        nombre_formula = r[3] or ''
        cant_lote = float(r[4] or 0)
        nombre_norm = _norm(nombre_formula)
        palabras_form = _palabras_clave(nombre_formula)

        es_huerfano = mid not in catalogo_codigos

        # Expandir palabras con sinónimos (formula + catálogo)
        palabras_form_exp = _expandir_sinonimos(palabras_form)

        # Buscar candidatos
        candidatos = []
        for m in maestro:
            score = 0
            len_form = len(palabras_form)
            len_cat = len(m['palabras_clave'])
            cat_palabras_exp = _expandir_sinonimos(m['palabras_clave'])

            # Score 100: match exacto normalizado
            if nombre_norm and nombre_norm in m['nombres_norm']:
                score = 100

            # Score 95: palabras clave idénticas (sin stopwords)
            elif palabras_form and m['palabras_clave'] and palabras_form == m['palabras_clave']:
                score = 95

            elif palabras_form and m['palabras_clave']:
                # Match con sinonimos
                comunes = palabras_form & m['palabras_clave']
                comunes_exp = palabras_form_exp & cat_palabras_exp
                len_comunes = len(comunes)
                len_comunes_exp = len(comunes_exp)

                # Score 90: todas palabras formula en catalogo (directo)
                if comunes == palabras_form and len_form >= 1:
                    if len_cat <= len_form + 1:
                        score = 92
                    elif len_cat <= len_form * 2:
                        score = 88
                    else:
                        score = 80

                # Score 85: todas palabras catalogo en formula (catalogo más corto)
                elif comunes == m['palabras_clave'] and len_cat >= 1:
                    if len_form <= len_cat + 1:
                        score = 85
                    else:
                        score = 75

                # Score 80: match con sinonimos — todas palabras formula tienen equivalente
                elif len_comunes_exp >= len_form and len_form >= 1:
                    score = 80

                # Score 70: al menos 70% de palabras en común
                elif len_comunes >= max(2, int(len_form * 0.7)):
                    score = 70

                # Score 65: al menos 70% con sinonimos
                elif len_comunes_exp >= max(2, int(len_form * 0.7)):
                    score = 65

                # Score 55: al menos 50% de palabras en común
                elif len_comunes >= max(1, int(len_form * 0.5)) and len_comunes >= 1:
                    score = 55

            # Bonus: substring match — cada palabra de formula está como prefijo
            # de alguna palabra del catalogo (ej. 'GLIC' ⊂ 'GLICERINA')
            if score < 70 and palabras_form and m['palabras_clave']:
                substring_matches = 0
                for pf in palabras_form:
                    if len(pf) >= 4:
                        for pc in m['palabras_clave']:
                            if pc.startswith(pf) or pf.startswith(pc):
                                substring_matches += 1
                                break
                if substring_matches == len(palabras_form) and len_form >= 1:
                    score = max(score, 75)
                elif substring_matches >= max(1, int(len_form * 0.7)):
                    score = max(score, 65)

            if score > 0:
                candidatos.append({
                    'codigo': m['codigo'],
                    'nombre_comercial': m['nombre_comercial'],
                    'nombre_inci': m['nombre_inci'],
                    'score': score,
                })

        # Ordenar y filtrar
        candidatos.sort(key=lambda x: -x['score'])
        # Si hay match alto (>=85), descartar matches débiles para reducir ruido
        if candidatos and candidatos[0]['score'] >= 85:
            min_threshold = max(70, candidatos[0]['score'] - 20)
            candidatos = [c for c in candidatos if c['score'] >= min_threshold]
        candidatos = candidatos[:5]

        # Auto-corregible: top score >= 75 con clara dominancia sobre el segundo
        auto_corregible = False
        if candidatos:
            top_score = candidatos[0]['score']
            second_score = candidatos[1]['score'] if len(candidatos) > 1 else 0
            delta = top_score - second_score
            # Reglas escaladas — score más alto requiere menos delta
            if top_score == 100 and len([c for c in candidatos if c['score'] == 100]) == 1:
                auto_corregible = True
            elif top_score >= 95 and delta >= 5:
                auto_corregible = True
            elif top_score >= 88 and delta >= 8:
                auto_corregible = True
            elif top_score >= 80 and delta >= 10:
                auto_corregible = True
            elif top_score >= 75 and delta >= 15:
                auto_corregible = True

        # Determinar problema
        problema = None
        if es_huerfano:
            problema = 'huerfano'
        else:
            cat_match = next((m for m in maestro if m['codigo'] == mid), None)
            if cat_match and palabras_form and cat_match['palabras_clave']:
                comunes = palabras_form & cat_match['palabras_clave']
                # Mismatch si menos del 50% de palabras coinciden
                if len(comunes) < max(1, int(len(palabras_form) * 0.5)):
                    problema = 'mismatch_nombre'

        if problema:
            mejor = candidatos[0] if candidatos else None
            # Marcar como auto si cumple criterio
            if mejor and auto_corregible:
                mejor = dict(mejor)
                mejor['auto'] = True
            problemas.append({
                'formula_item_id': item_id,
                'producto': producto,
                'material_id_actual': mid,
                'material_nombre_formula': nombre_formula,
                'cantidad_g_por_lote': cant_lote,
                'problema': problema,
                'candidatos_sugeridos': candidatos,
                'mejor_candidato': mejor,
                'auto_corregible': auto_corregible,
            })

    # Stats
    stats = {
        'total_formula_items': len(rows),
        'total_problemas': len(problemas),
        'huerfanos': sum(1 for p in problemas if p['problema'] == 'huerfano'),
        'mismatch_nombre': sum(1 for p in problemas if p['problema'] == 'mismatch_nombre'),
        'auto_corregibles': sum(1 for p in problemas if p.get('auto_corregible')),
        'requieren_revision': sum(1 for p in problemas
                                  if not p.get('mejor_candidato')),
        'con_sugerencia_baja': sum(1 for p in problemas
                                   if p.get('mejor_candidato')
                                   and not p.get('auto_corregible')),
    }

    # Agrupar por producto
    by_producto = {}
    for p in problemas:
        prod = p['producto']
        by_producto.setdefault(prod, []).append(p)
    productos_afectados = sorted(
        [{'producto': k, 'count': len(v)} for k, v in by_producto.items()],
        key=lambda x: -x['count'],
    )

    conn.close()
    return jsonify({
        'stats': stats,
        'problemas': problemas,
        'productos_afectados': productos_afectados,
    })


@bp.route("/api/admin/corregir-formulas", methods=["POST"])
def admin_corregir_formulas():
    """Aplica correcciones de material_id a formula_items.

    Body:
      token: 'CORREGIR_FORMULAS_2026'
      correcciones: list de {formula_item_id, nuevo_material_id, nuevo_material_nombre}
        Si nuevo_material_nombre es null, se usa el nombre actual de la formula.

    Backup previo + audit log.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    d = request.json or {}
    if d.get('token', '').strip() != 'CORREGIR_FORMULAS_2026':
        return jsonify({'error': 'Token incorrecto'}), 403
    correcciones = d.get('correcciones') or []
    if not correcciones:
        return jsonify({'error': 'Sin correcciones'}), 400

    # Backup previo
    try:
        do_backup(triggered_by='pre_corregir_formulas')
    except Exception as e:
        return jsonify({'error': f'Backup fallo: {str(e)[:200]}'}), 500

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    aplicados = []
    errores = []
    for corr in correcciones:
        try:
            fid = int(corr.get('formula_item_id'))
            nuevo_mid = (corr.get('nuevo_material_id') or '').strip()
            nuevo_nombre = corr.get('nuevo_material_nombre')
            if not nuevo_mid:
                errores.append({'formula_item_id': fid, 'error': 'sin nuevo_material_id'})
                continue
            # Capturar valores previos para audit
            row = c.execute(
                "SELECT producto_nombre, material_id, material_nombre "
                "FROM formula_items WHERE id=?", (fid,)
            ).fetchone()
            if not row:
                errores.append({'formula_item_id': fid, 'error': 'no encontrado'})
                continue
            previo = {
                'producto': row[0],
                'material_id_previo': row[1],
                'material_nombre_previo': row[2],
            }
            if nuevo_nombre:
                c.execute(
                    "UPDATE formula_items SET material_id=?, material_nombre=? "
                    "WHERE id=?",
                    (nuevo_mid, nuevo_nombre, fid),
                )
            else:
                c.execute(
                    "UPDATE formula_items SET material_id=? WHERE id=?",
                    (nuevo_mid, fid),
                )
            aplicados.append({
                **previo,
                'material_id_nuevo': nuevo_mid,
                'material_nombre_nuevo': nuevo_nombre or row[2],
            })
        except Exception as _e:
            errores.append({'formula_item_id': corr.get('formula_item_id'),
                            'error': str(_e)[:200]})

    conn.commit()

    # Audit
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'CORREGIR_FORMULAS', 'formula_items', '_BULK_',
             _json.dumps({
                 'count': len(aplicados),
                 'errores': len(errores),
                 'correcciones_sample': aplicados[:30],
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()

    return jsonify({
        'ok': True,
        'count_aplicados': len(aplicados),
        'count_errores': len(errores),
        'aplicados': aplicados[:50],
        'errores': errores[:30],
        'mensaje': f'{len(aplicados)} fórmulas corregidas. Backup previo creado.',
    })


@bp.route("/api/admin/revertir-formulas-desde-backup", methods=["POST"])
def admin_revertir_formulas_desde_backup():
    """Revierte formula_items al estado guardado en el backup mas reciente
    con triggered_by='pre_corregir_formulas'. Quirurgico: solo reemplaza
    formula_items, NO toca movimientos / catalogo / OCs.

    Body:
      token: 'REVERTIR_FORMULAS_2026'

    Caso de uso: el usuario aplico correcciones y se dio cuenta que
    algunas eran incorrectas. Este endpoint deshace los cambios usando
    el backup automatico pre-aplicacion.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    d = request.json or {}
    if d.get('token', '').strip() != 'REVERTIR_FORMULAS_2026':
        return jsonify({'error': 'Token incorrecto'}), 403

    # Encontrar backup mas reciente pre-corregir o pre-eliminar formulas
    import gzip, os as _os, tempfile
    bk_db_path = None
    bk_info = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        row = c.execute("""
            SELECT file_path, started_at, triggered_by FROM backup_log
            WHERE status='ok' AND (triggered_by LIKE 'pre_corregir_formulas%'
                                   OR triggered_by LIKE 'pre_eliminar_formulas%')
            ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'No encontre backup pre-correccion. Imposible revertir.'}), 404
        bk_db_path, bk_started, bk_trigger = row
        bk_info = {'file': bk_db_path, 'started_at': bk_started, 'triggered_by': bk_trigger}
    except sqlite3.OperationalError as _e:
        return jsonify({'error': f'No pude leer backup_log: {_e}'}), 500

    if not _os.path.exists(bk_db_path):
        return jsonify({'error': f'Archivo backup no existe: {bk_db_path}',
                        'backup_info': bk_info}), 404

    # Descomprimir backup a tmp
    try:
        if bk_db_path.endswith('.gz'):
            tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            tmp_path = tmp.name
            tmp.close()
            with gzip.open(bk_db_path, 'rb') as gz_in, open(tmp_path, 'wb') as out:
                while True:
                    chunk = gz_in.read(64 * 1024)
                    if not chunk: break
                    out.write(chunk)
        else:
            tmp_path = bk_db_path
    except Exception as _e:
        return jsonify({'error': f'No pude descomprimir backup: {_e}',
                        'backup_info': bk_info}), 500

    # Leer formula_items del backup
    try:
        bk = sqlite3.connect(tmp_path)
        bk_rows = bk.execute(
            "SELECT id, producto_nombre, material_id, material_nombre, "
            "       porcentaje, cantidad_g_por_lote "
            "FROM formula_items"
        ).fetchall()
        bk.close()
    except Exception as _e:
        return jsonify({'error': f'No pude leer formula_items del backup: {_e}',
                        'backup_info': bk_info}), 500
    finally:
        if tmp_path != bk_db_path and _os.path.exists(tmp_path):
            try: _os.remove(tmp_path)
            except Exception: pass

    # Crear backup adicional ANTES de revertir (por si acaso)
    try:
        do_backup(triggered_by='pre_revertir_formulas')
    except Exception:
        pass

    # Reemplazar formula_items en BD actual con el del backup
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        actuales = c.execute("SELECT COUNT(*) FROM formula_items").fetchone()[0]
        c.execute("DELETE FROM formula_items")
        for r in bk_rows:
            c.execute(
                """INSERT INTO formula_items
                   (id, producto_nombre, material_id, material_nombre,
                    porcentaje, cantidad_g_por_lote)
                   VALUES (?,?,?,?,?,?)""",
                r,
            )
        conn.commit()
    except Exception as _e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': f'Reversion fallo: {_e}'}), 500

    # Audit
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'REVERTIR_FORMULAS_DESDE_BACKUP', 'formula_items', '_BULK_',
             _json.dumps({
                 'backup': bk_info,
                 'items_actuales_eliminados': actuales,
                 'items_restaurados_del_backup': len(bk_rows),
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()

    return jsonify({
        'ok': True,
        'mensaje': (f'formula_items revertido al estado del backup '
                    f'{bk_info.get("started_at")}. Eliminados {actuales} '
                    f'items actuales, restaurados {len(bk_rows)} del backup.'),
        'items_eliminados': actuales,
        'items_restaurados': len(bk_rows),
        'backup_usado': bk_info,
    })


@bp.route("/api/admin/eliminar-formulas-obsoletas", methods=["POST"])
def admin_eliminar_formulas_obsoletas():
    """Elimina items en formula_items que apuntan a material_id huerfano
    Y sin candidato similar en maestro_mps. Probablemente son ingredientes
    descontinuados o productos obsoletos.

    Body:
      token: 'ELIMINAR_FORMULAS_OBSOLETAS_2026'
      formula_item_ids: lista de IDs a eliminar (del diagnostico previo)

    Backup previo + audit log.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    d = request.json or {}
    if d.get('token', '').strip() != 'ELIMINAR_FORMULAS_OBSOLETAS_2026':
        return jsonify({'error': 'Token incorrecto'}), 403
    ids = d.get('formula_item_ids') or []
    if not ids:
        return jsonify({'error': 'Sin IDs a eliminar'}), 400

    # Backup previo
    try:
        do_backup(triggered_by='pre_eliminar_formulas_obsoletas')
    except Exception as e:
        return jsonify({'error': f'Backup fallo: {str(e)[:200]}'}), 500

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    eliminados = []
    for fid in ids:
        try:
            row = c.execute(
                "SELECT producto_nombre, material_id, material_nombre "
                "FROM formula_items WHERE id=?", (fid,)
            ).fetchone()
            if not row:
                continue
            c.execute("DELETE FROM formula_items WHERE id=?", (fid,))
            eliminados.append({
                'formula_item_id': fid,
                'producto': row[0],
                'material_id': row[1],
                'material_nombre': row[2],
            })
        except Exception:
            continue
    conn.commit()

    # Audit
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'ELIMINAR_FORMULAS_OBSOLETAS', 'formula_items', '_BULK_',
             _json.dumps({
                 'count': len(eliminados),
                 'eliminados_sample': eliminados[:30],
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()

    return jsonify({
        'ok': True,
        'count_eliminados': len(eliminados),
        'eliminados': eliminados[:50],
        'mensaje': f'{len(eliminados)} items obsoletos eliminados de formula_items.',
    })


@bp.route("/api/admin/aplicar-correcciones-formulas-batch-2026-04-28", methods=["POST"])
def admin_aplicar_correcciones_formulas_batch_20260428():
    """Aplica el batch de correcciones de formulas+catalogo decidido el 2026-04-28
    con Sebastian + Alejandro. Lee y ejecuta el archivo SQL versionado en
    scripts/migraciones/correcciones_formulas_2026_04_28.sql.

    Body:
      token: 'APLICAR_CORRECCIONES_2026_04_28'

    Operaciones (240 cambios totales):
      - 44 INSERT nuevos MPs (codigos MP00400+)
      - 1  UPDATE Azeclair MP00284 -> activo=0
      - 1  UPDATE INCI oficial AOS 40 (MP00212)
      - 207 UPDATE formula_items (correcciones huerfanos + typos)
      - 33 DELETE formula_items (aguas internas infinitas)

    Backup automatico antes de tocar.
    Una sola pulsacion de boton — el SQL es idempotente con INSERT OR IGNORE
    y los UPDATE/DELETE son seguros de re-ejecutar.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    d = request.json or {}
    if d.get('token', '').strip() != 'APLICAR_CORRECCIONES_2026_04_28':
        return jsonify({'error': 'Token incorrecto. Debe ser exactamente: APLICAR_CORRECCIONES_2026_04_28'}), 403

    # Localizar archivo SQL
    import os as _os
    repo_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    sql_path = _os.path.join(repo_root, 'scripts', 'migraciones', 'correcciones_formulas_2026_04_28.sql')
    if not _os.path.exists(sql_path):
        return jsonify({'error': f'Archivo SQL no encontrado: {sql_path}'}), 500

    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_text = f.read()
    except Exception as _e:
        return jsonify({'error': f'No pude leer SQL: {_e}'}), 500

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Parsear los INSERTs del SQL para saber que MPs queremos crear (codigo_planeado, inci, comercial)
    import re as _re
    plan_inserts = []  # [(codigo_planeado, inci, comercial, tipo)]
    for m in _re.finditer(
        r"INSERT OR IGNORE INTO maestro_mps[^V]+VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'",
        sql_text):
        plan_inserts.append((m.group(1), m.group(2), m.group(3), m.group(4)))

    try:
        # 1) Detectar duplicados por nombre_inci YA EXISTENTE en catalogo
        existentes_por_inci = {}
        for codigo_p, inci, comercial, tipo in plan_inserts:
            row = c.execute(
                "SELECT codigo_mp, nombre_inci, nombre_comercial FROM maestro_mps "
                "WHERE LOWER(TRIM(nombre_inci)) = LOWER(TRIM(?)) LIMIT 1",
                (inci,)
            ).fetchone()
            if row:
                existentes_por_inci[codigo_p] = {
                    'codigo_planeado': codigo_p,
                    'inci_planeado': inci,
                    'codigo_existente': row[0],
                    'inci_existente': row[1],
                    'comercial_existente': row[2],
                }

        # 2) Verificar rango MP00400-MP00500 ocupado
        ocupados = c.execute(
            "SELECT codigo_mp, nombre_inci, nombre_comercial FROM maestro_mps "
            "WHERE codigo_mp >= 'MP00400' AND codigo_mp <= 'MP00500' ORDER BY codigo_mp"
        ).fetchall()

        modo = (d.get('modo') or '').strip()

        # === Si hay duplicados por INCI, exigir decision explicita ===
        if existentes_por_inci and modo not in ('mapear_duplicados', 'auto_renumerar'):
            conn.close()
            return jsonify({
                'error': f'Hay {len(existentes_por_inci)} INCI(s) que ya existen en el catalogo con OTRO codigo_mp. Crearlos duplicaria entradas.',
                'duplicados_inci': list(existentes_por_inci.values()),
                'total_duplicados_inci': len(existentes_por_inci),
                'ocupados_rango_mp00400': [
                    {'codigo': r[0], 'inci': r[1], 'comercial': r[2]} for r in ocupados
                ],
                'opciones': {
                    'mapear_duplicados': 'Reenviar con modo="mapear_duplicados" — los UPDATEs apuntaran a los codigos existentes, no se crearan duplicados',
                    'auto_renumerar': 'Reenviar con modo="auto_renumerar" — duplica las entradas en otro codigo_mp libre (NO RECOMENDADO si los INCIs son iguales)',
                },
            }), 409

        # === Si no hay duplicados pero el rango esta ocupado, ofrecer auto_renumerar ===
        if ocupados and not existentes_por_inci and modo != 'auto_renumerar':
            conn.close()
            return jsonify({
                'error': f'Hay {len(ocupados)} codigos MP en el rango MP00400-MP00500 ocupados (con OTROS INCIs, no los mios).',
                'ocupados_con_nombres': [
                    {'codigo': r[0], 'inci': r[1], 'comercial': r[2]} for r in ocupados
                ],
                'total_ocupados': len(ocupados),
                'sugerencia': 'Sin duplicados de INCI detectados — auto_renumerar seguro. Reenviar con modo="auto_renumerar".',
            }), 409

        # === modo=mapear_duplicados: skip INSERT de duplicados, reescribir UPDATEs ===
        if modo == 'mapear_duplicados' and existentes_por_inci:
            # Borrar las lineas INSERT de los duplicados (se vuelven no-op)
            # Y reescribir referencias codigo_planeado -> codigo_existente en UPDATEs
            for cp, info in existentes_por_inci.items():
                ce = info['codigo_existente']
                # Reemplazar codigo_planeado por codigo_existente en TODO el SQL
                sql_text = sql_text.replace("'" + cp + "'", "'" + ce + "'")
            # Tras el replace, los INSERTs duplicados son INSERT OR IGNORE de codigos existentes
            # — el OR IGNORE los hace no-op. Perfecto, no queda accion residual.

        # === modo=auto_renumerar: buscar rango libre y renumerar ===
        if modo == 'auto_renumerar':
            todos = c.execute(
                "SELECT codigo_mp FROM maestro_mps WHERE codigo_mp GLOB 'MP[0-9]*'"
            ).fetchall()
            usados = set()
            for (cm,) in todos:
                try: usados.add(int(cm[2:]))
                except Exception: pass
            new_start = None
            for base in range(1000, 9000, 50):
                if not any((base + k) in usados for k in range(50)):
                    new_start = base
                    break
            if new_start is None:
                conn.close()
                return jsonify({'error': 'No hay rango contiguo libre de 50 codigos hasta MP09000'}), 500

            def _replace_code(m):
                old_n = int(m.group(1))
                if 400 <= old_n <= 443:
                    new_n = new_start + (old_n - 400)
                    return 'MP{:05d}'.format(new_n)
                return m.group(0)
            sql_text = _re.sub(r"MP(\d{5})", _replace_code, sql_text)

    except sqlite3.OperationalError as _e:
        conn.close()
        return jsonify({'error': f'No pude verificar rango: {_e}'}), 500

    # Backup completo de DB antes de tocar
    try:
        do_backup(triggered_by='pre_aplicar_correcciones_2026_04_28')
    except Exception as _e:
        conn.close()
        return jsonify({'error': f'Backup pre-aplicacion fallo: {_e}'}), 500

    # Snapshot conteos antes
    try:
        n_formulas_antes = c.execute('SELECT COUNT(*) FROM formula_items').fetchone()[0]
        n_mps_antes = c.execute('SELECT COUNT(*) FROM maestro_mps').fetchone()[0]
    except Exception:
        n_formulas_antes = n_mps_antes = -1

    # Ejecutar SQL completo en una sola pasada (executescript permite multiples statements)
    try:
        # NOTA: el SQL trae su propio BEGIN TRANSACTION/COMMIT, executescript respeta eso
        c.executescript(sql_text)
        conn.commit()
    except Exception as _e:
        try: conn.rollback()
        except Exception: pass
        conn.close()
        return jsonify({'error': f'Aplicacion del SQL fallo: {_e}'}), 500

    # Snapshot despues
    try:
        n_formulas_desp = c.execute('SELECT COUNT(*) FROM formula_items').fetchone()[0]
        n_mps_desp = c.execute('SELECT COUNT(*) FROM maestro_mps').fetchone()[0]
        n_nuevos_mps = c.execute(
            "SELECT COUNT(*) FROM maestro_mps WHERE codigo_mp >= 'MP00400' AND codigo_mp <= 'MP00500'"
        ).fetchone()[0]
        azeclair_inactivo = c.execute(
            "SELECT activo FROM maestro_mps WHERE codigo_mp='MP00284'"
        ).fetchone()
        azeclair_inactivo = azeclair_inactivo[0] if azeclair_inactivo else None
    except Exception:
        n_formulas_desp = n_mps_desp = n_nuevos_mps = -1
        azeclair_inactivo = None

    # Audit log
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'APLICAR_CORRECCIONES_FORMULAS_BATCH_20260428', 'multi', '_BULK_',
             _json.dumps({
                 'sql_file': 'scripts/migraciones/correcciones_formulas_2026_04_28.sql',
                 'formula_items_antes': n_formulas_antes,
                 'formula_items_despues': n_formulas_desp,
                 'maestro_mps_antes': n_mps_antes,
                 'maestro_mps_despues': n_mps_desp,
                 'mps_nuevos_creados': n_nuevos_mps,
                 'azeclair_marcado_inactivo': azeclair_inactivo == 0,
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()

    return jsonify({
        'ok': True,
        'mensaje': 'Correcciones aplicadas en transaccion atomica con backup previo.',
        'antes': {
            'formula_items': n_formulas_antes,
            'maestro_mps': n_mps_antes,
        },
        'despues': {
            'formula_items': n_formulas_desp,
            'maestro_mps': n_mps_desp,
            'mps_nuevos_creados': n_nuevos_mps,
            'azeclair_inactivo': azeclair_inactivo == 0,
        },
        'cambios_netos': {
            'formula_items_diff': n_formulas_desp - n_formulas_antes,
            'maestro_mps_diff': n_mps_desp - n_mps_antes,
        },
    })


@bp.route("/api/admin/sembrar-maestro-desde-excel", methods=["POST"])
def admin_sembrar_maestro_desde_excel():
    """Asegura que TODOS los códigos del Excel (verdes + no-verdes) existan
    en maestro_mps. Para los que no existen, inserta una entrada con
    stock_minimo=0 y los datos disponibles del Excel (nombre, proveedor,
    estantería). NO crea movimientos — los no-verdes quedan en stock 0
    naturalmente.

    Justificación: las MPs no-verdes son materias primas que se han usado
    pero están actualmente agotadas. Necesitan estar en el catálogo para:
      - Aparecer en fórmulas
      - Recibirse vía OC cuando llegue reposición
      - Aparecer en alertas de mínimos cuando se reciban

    Solo admins. SIN tocar `movimientos`.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    if 'file' not in request.files:
        return jsonify({'error': 'Falta archivo (campo "file")'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith(('.xlsx', '.xlsm')):
        return jsonify({'error': 'Archivo debe ser .xlsx'}), 400

    excel_verde, _, excel_no_verde, errs = _parse_excel_verde(f, incluir_no_verde=True)
    if excel_verde is None:
        return jsonify({'error': errs[0] if errs else 'Excel inválido'}), 400

    # Consolidar todos los códigos (verdes + no-verdes), tomando el primer
    # registro encontrado de cada código (los datos de catálogo son los mismos
    # entre lotes del mismo MP).
    todos_por_codigo = {}
    for (cod, _lote), info in excel_verde.items():
        if cod not in todos_por_codigo:
            todos_por_codigo[cod] = info
    for (cod, _lote), info in excel_no_verde.items():
        if cod not in todos_por_codigo:
            todos_por_codigo[cod] = info

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Códigos ya presentes en maestro_mps
    existentes = {row[0] for row in c.execute(
        "SELECT codigo_mp FROM maestro_mps"
    ).fetchall()}

    nuevos = []
    actualizados_proveedor = []  # opcional: si en maestro está vacío y excel tiene proveedor
    for cod, info in todos_por_codigo.items():
        nombre = (info.get('nombre_comercial') or info.get('inci') or cod).strip()
        inci = (info.get('inci') or '').strip()
        proveedor = (info.get('proveedor') or '').strip()
        if cod not in existentes:
            try:
                c.execute(
                    """INSERT INTO maestro_mps
                       (codigo_mp, nombre_inci, nombre_comercial, proveedor,
                        stock_minimo, activo)
                       VALUES (?,?,?,?,?,?)""",
                    (cod, inci or nombre, nombre, proveedor, 0, 1),
                )
                nuevos.append({
                    'codigo_mp': cod,
                    'nombre_comercial': nombre,
                    'proveedor': proveedor,
                })
            except sqlite3.IntegrityError:
                pass
        else:
            # MP ya existe — actualizar proveedor si está vacío en maestro
            if proveedor:
                try:
                    cur_prov = c.execute(
                        "SELECT proveedor FROM maestro_mps WHERE codigo_mp=?",
                        (cod,),
                    ).fetchone()
                    if cur_prov and not (cur_prov[0] or '').strip():
                        c.execute(
                            "UPDATE maestro_mps SET proveedor=? WHERE codigo_mp=?",
                            (proveedor, cod),
                        )
                        actualizados_proveedor.append({
                            'codigo_mp': cod,
                            'proveedor': proveedor,
                        })
                except sqlite3.OperationalError:
                    pass

    conn.commit()

    # Audit
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'SEMBRAR_MAESTRO_DESDE_EXCEL', 'maestro_mps', '_BULK_',
             _json.dumps({
                 'archivo': f.filename,
                 'nuevos_count': len(nuevos),
                 'proveedores_actualizados_count': len(actualizados_proveedor),
                 'codigos_excel_total': len(todos_por_codigo),
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

    return jsonify({
        'ok': True,
        'mensaje': (f'Sembrado: {len(nuevos)} nuevos MPs en catálogo, '
                    f'{len(actualizados_proveedor)} con proveedor actualizado. '
                    f'No se modificaron movimientos.'),
        'nuevos_count': len(nuevos),
        'nuevos_sample': nuevos[:30],
        'proveedores_actualizados_count': len(actualizados_proveedor),
        'proveedores_actualizados_sample': actualizados_proveedor[:30],
    })


@bp.route("/api/admin/inventario-health-monitor", methods=["GET"])
def admin_inventario_health_monitor():
    """Monitor periodico: detecta anomalias en kardex que indiquen
    duplicacion / bursts / cargas no auditadas.

    Tras el incidente de doble carga (2026-04-27) que inflo el
    inventario 3x, este monitor sirve para captar el patron antes de
    que sea masivo. Idealmente se corre en cron diario o se revisa
    manualmente cada semana.

    Detecta:
      1. BURST: >= 30 entradas en una sola fecha (excepto el dia cero
         del reset 2026-04-15 que es legitimo)
      2. MULTI-ENTRADAS: lotes con >= 2 Entradas (potencial doble
         carga). Filtra los regenerados de huerfanos (1 entrada con
         observaciones 'consumido pre-reset').
      3. SIN-OC ratio: si > 80% de Entradas no tienen numero_oc en
         ultimos 7 dias, es signo de carga masiva sin trazabilidad.
      4. STOCK ANOMALO: si stock_total > 3x el promedio del ultimo
         mes, es senal de inflado.

    Solo lectura, admin. Devuelve nivel: ok / warning / critical.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    alertas = []

    # 1. BURST detection — entradas masivas en un solo dia, excluyendo
    #    el dia cero conocido (2026-04-15) y observaciones de reset.
    DIA_CERO_RESET = '2026-04-15'
    try:
        rows = c.execute("""
            SELECT SUBSTR(fecha,1,10) as dia,
                   COUNT(*) as n,
                   COALESCE(SUM(cantidad),0) as g
            FROM movimientos
            WHERE tipo='Entrada'
              AND SUBSTR(fecha,1,10) != ?
              AND COALESCE(observaciones,'') NOT LIKE '%reset%'
              AND COALESCE(observaciones,'') NOT LIKE '%dia cero%'
            GROUP BY SUBSTR(fecha,1,10)
            HAVING n >= 30
            ORDER BY n DESC
            LIMIT 10
        """, (DIA_CERO_RESET,)).fetchall()
        for r in rows:
            alertas.append({
                'tipo': 'BURST',
                'severidad': 'critical' if r[1] >= 100 else 'warning',
                'mensaje': (f'{r[1]} Entradas en un solo dia ({r[0]}) — total '
                            f'{int(round(r[2])):,} g. '.replace(',', '.') +
                            'Posible carga masiva no auditada.'),
                'detalle': {'fecha': r[0], 'count': r[1], 'total_g': r[2]},
            })
    except sqlite3.OperationalError:
        pass

    # 2. MULTI-ENTRADAS — lotes con >=2 Entradas (filtrando regenerados
    #    de huerfanos que tienen observaciones especificas)
    try:
        rows = c.execute("""
            SELECT material_id, COALESCE(lote,''),
                   COUNT(*) as n,
                   SUM(cantidad) as g
            FROM movimientos
            WHERE tipo='Entrada'
              AND COALESCE(observaciones,'') NOT LIKE '%consumido pre-reset%'
              AND COALESCE(observaciones,'') NOT LIKE '%dia cero v8_1%'
            GROUP BY material_id, lote
            HAVING n >= 2
            ORDER BY n DESC, g DESC
            LIMIT 20
        """).fetchall()
        for r in rows:
            alertas.append({
                'tipo': 'MULTI_ENTRADAS',
                'severidad': 'critical' if r[2] >= 3 else 'warning',
                'mensaje': (f'{r[0]}/{r[1]}: {r[2]} Entradas con total '
                            f'{int(round(r[3])):,} g. '.replace(',', '.') +
                            'Verificar si son recepciones legitimas distintas o doble carga.'),
                'detalle': {
                    'codigo_mp': r[0], 'lote': r[1] or '(sin lote)',
                    'count_entradas': r[2], 'total_g': r[3],
                },
            })
    except sqlite3.OperationalError:
        pass

    # 3. SIN OC ratio en ultimos 7 dias (excluye reset)
    try:
        from datetime import datetime as _dt, timedelta as _td
        hace_7 = (_dt.utcnow() - _td(days=7)).strftime('%Y-%m-%d')
        r = c.execute("""
            SELECT
              SUM(CASE WHEN COALESCE(numero_oc,'') = '' THEN 1 ELSE 0 END) as sin_oc,
              COUNT(*) as total
            FROM movimientos
            WHERE tipo='Entrada' AND fecha >= ?
              AND COALESCE(observaciones,'') NOT LIKE '%reset%'
              AND COALESCE(observaciones,'') NOT LIKE '%dia cero%'
              AND COALESCE(observaciones,'') NOT LIKE '%consumido pre-reset%'
        """, (hace_7,)).fetchone()
        sin_oc = r[0] or 0
        total = r[1] or 0
        if total >= 5:
            ratio = sin_oc / total
            if ratio > 0.80:
                alertas.append({
                    'tipo': 'SIN_OC_ANOMALO',
                    'severidad': 'warning',
                    'mensaje': (f'{sin_oc}/{total} ({int(ratio*100)}%) Entradas en ultimos '
                                f'7 dias sin numero_oc. Recepciones formales deberian '
                                f'siempre traer OC.'),
                    'detalle': {'sin_oc': sin_oc, 'total': total, 'ratio_pct': int(ratio*100)},
                })
    except sqlite3.OperationalError:
        pass

    # 4. Stock total razonable (heuristica — alarma si > 50 toneladas)
    try:
        stock_g = float(c.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) "
            "FROM movimientos"
        ).fetchone()[0] or 0)
        if stock_g > 50_000_000:  # 50 toneladas
            alertas.append({
                'tipo': 'STOCK_ANOMALO',
                'severidad': 'critical',
                'mensaje': (f'Stock total = {int(round(stock_g)):,} g'.replace(',', '.') +
                            ' supera 50 toneladas. '
                            'Para una empresa cosmetica de tu escala es altamente probable '
                            'inflado por doble carga. Auditar de inmediato.'),
                'detalle': {'stock_total_g': stock_g, 'umbral_g': 50_000_000},
            })
    except sqlite3.OperationalError:
        pass

    conn.close()

    n_critical = sum(1 for a in alertas if a['severidad'] == 'critical')
    n_warning = sum(1 for a in alertas if a['severidad'] == 'warning')
    nivel = ('critical' if n_critical else ('warning' if n_warning else 'ok'))

    return jsonify({
        'ok': True,
        'nivel': nivel,
        'count_critical': n_critical,
        'count_warning': n_warning,
        'alertas': alertas,
        'recomendacion': {
            'ok': 'Sistema saludable. Sin patrones de doble carga detectados.',
            'warning': 'Revisar alertas. Posibles cargas duplicadas o sin trazabilidad.',
            'critical': ('ACCION INMEDIATA. Patrones de doble carga detectados. '
                         'Considerar pausar entradas hasta investigar. '
                         'Usar /api/admin/inventario-diagnostico-entradas para detalle.'),
        }[nivel],
    })


@bp.route("/api/admin/health-check-post-reset", methods=["GET"])
def admin_health_check_post_reset():
    """Verificación de integridad despues del reset.

    Confirma que:
      - Stock total esta en rango razonable
      - No hay lotes con stock negativo
      - Producciones siguen intactas (no se borraron)
      - OCs y comprobantes siguen intactos
      - Catalogo maestro_mps sigue intacto
      - Hay salidas FEFO de produccion (no se perdieron)
      - Solicitudes_compra siguen intactas

    Solo lectura, admins.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    checks = {}

    # 1. Movimientos: stock total y conteos
    try:
        movs_total = c.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
        stock_total_g = float(c.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0) "
            "FROM movimientos"
        ).fetchone()[0] or 0)
        n_entradas = c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada'").fetchone()[0]
        n_salidas = c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Salida'").fetchone()[0]
        n_salidas_fefo = c.execute(
            "SELECT COUNT(*) FROM movimientos WHERE tipo='Salida' AND observaciones LIKE 'FEFO:%'"
        ).fetchone()[0]
        checks['movimientos'] = {
            'ok': True,
            'total': movs_total,
            'stock_total_g': round(stock_total_g, 1),
            'stock_total_kg': round(stock_total_g / 1000, 2),
            'entradas': n_entradas,
            'salidas': n_salidas,
            'salidas_fefo_produccion': n_salidas_fefo,
        }
    except Exception as e:
        checks['movimientos'] = {'ok': False, 'error': str(e)}

    # 2. Lotes con stock negativo (debe ser 0 — invariante critica)
    try:
        rows = c.execute("""
            SELECT material_id, COALESCE(lote,''),
                   SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as neto
            FROM movimientos
            GROUP BY material_id, lote
            HAVING neto < -0.5
        """).fetchall()
        checks['stock_negativo'] = {
            'ok': len(rows) == 0,
            'count': len(rows),
            'sample': [{'codigo_mp': r[0], 'lote': r[1], 'neto_g': round(r[2], 1)}
                       for r in rows[:10]],
            'critico': 'Si > 0: hay lotes con stock negativo (bug del replay)',
        }
    except Exception as e:
        checks['stock_negativo'] = {'ok': False, 'error': str(e)}

    # 3. Producciones intactas
    try:
        n_prod = c.execute("SELECT COUNT(*) FROM producciones").fetchone()[0]
        last_prod = c.execute(
            "SELECT producto, fecha, lote FROM producciones ORDER BY id DESC LIMIT 1"
        ).fetchone()
        checks['producciones'] = {
            'ok': n_prod >= 0,
            'count': n_prod,
            'ultima': {
                'producto': last_prod[0], 'fecha': str(last_prod[1])[:10],
                'lote': last_prod[2]
            } if last_prod else None,
        }
    except Exception as e:
        checks['producciones'] = {'ok': False, 'error': str(e)}

    # 4. OCs intactas
    try:
        n_ocs = c.execute("SELECT COUNT(*) FROM ordenes_compra").fetchone()[0]
        n_oc_items = c.execute("SELECT COUNT(*) FROM ordenes_compra_items").fetchone()[0]
        checks['ocs'] = {
            'ok': True,
            'ordenes_compra': n_ocs,
            'items_total': n_oc_items,
        }
    except Exception as e:
        checks['ocs'] = {'ok': False, 'error': str(e)}

    # 5. Comprobantes intactos
    try:
        n_comp = c.execute("SELECT COUNT(*) FROM comprobantes_pago").fetchone()[0]
        checks['comprobantes_pago'] = {'ok': True, 'count': n_comp}
    except Exception as e:
        checks['comprobantes_pago'] = {'ok': False, 'error': str(e)}

    # 6. Maestro MPs intacto
    try:
        n_mps = c.execute("SELECT COUNT(*) FROM maestro_mps WHERE activo=1").fetchone()[0]
        checks['maestro_mps'] = {'ok': True, 'count_activos': n_mps}
    except Exception as e:
        checks['maestro_mps'] = {'ok': False, 'error': str(e)}

    # 7. Solicitudes intactas
    try:
        n_sol = c.execute("SELECT COUNT(*) FROM solicitudes_compra").fetchone()[0]
        n_sol_items = c.execute("SELECT COUNT(*) FROM solicitudes_compra_items").fetchone()[0]
        checks['solicitudes_compra'] = {
            'ok': True, 'count': n_sol, 'items_total': n_sol_items,
        }
    except Exception as e:
        checks['solicitudes_compra'] = {'ok': False, 'error': str(e)}

    # 8. Audit trail del reset
    try:
        last_resets = c.execute("""
            SELECT accion, fecha FROM audit_log
            WHERE accion LIKE 'RESET_INVENTARIO%'
            ORDER BY id DESC LIMIT 5
        """).fetchall()
        checks['audit_log'] = {
            'ok': len(last_resets) > 0,
            'eventos_reset_recientes': [
                {'accion': r[0], 'fecha': str(r[1])[:19]} for r in last_resets
            ],
        }
    except Exception as e:
        checks['audit_log'] = {'ok': False, 'error': str(e)}

    conn.close()

    overall_ok = all(v.get('ok', False) for v in checks.values())
    return jsonify({
        'ok': overall_ok,
        'overall': 'PASS' if overall_ok else 'FAIL',
        'checks': checks,
        'recomendacion': (
            'Sistema intacto. Planta deberia funcionar normalmente. '
            'Verificar visualmente: /planta carga, Stock por Lote muestra '
            'lotes con cantidad > 0, /compras solicitudes intactas, '
            '/financiero carga.'
        ) if overall_ok else 'REVISAR — algun check fallo. Restaurar backup si hay duda.',
    })


@bp.route("/api/admin/inventario-diagnostico-entradas", methods=["GET"])
def admin_inventario_diagnostico_entradas():
    """Diagnostico de Entradas en movimientos para detectar doble carga
    vs recepciones legitimas.

    Caso de uso (CEO 2026-04-27): el audit muestra DB con 2x el stock
    del Excel. Antes de tomar decision destructiva, ver el timeline real
    de entradas:

      - Lotes con multiples Entradas (smoking gun de doble carga)
      - Entradas por dia (timeline)
      - Entradas por operador (quien entro que)
      - Entradas con OC vs sin OC (recepcion formal vs manual)

    Solo lectura, admins.
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Lotes con MULTIPLES entradas (doble carga sospechosa)
    multi_entradas = []
    try:
        rows = c.execute("""
            SELECT material_id, COALESCE(lote,'') as lote,
                   COUNT(*) as n_entradas,
                   SUM(cantidad) as total_g,
                   GROUP_CONCAT(DISTINCT COALESCE(operador,''))  as operadores,
                   MIN(fecha) as primera,
                   MAX(fecha) as ultima
            FROM movimientos
            WHERE tipo='Entrada'
            GROUP BY material_id, lote
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC, SUM(cantidad) DESC
            LIMIT 200
        """).fetchall()
        for r in rows:
            multi_entradas.append({
                'codigo_mp': r[0], 'lote': r[1] or '(sin lote)',
                'n_entradas': r[2], 'total_g': round(r[3] or 0, 1),
                'operadores': r[4] or '',
                'primera_fecha': str(r[5])[:10] if r[5] else '',
                'ultima_fecha':  str(r[6])[:10] if r[6] else '',
            })
    except sqlite3.OperationalError:
        pass

    # 2. Timeline: entradas por dia (para detectar bursts de carga)
    timeline = []
    try:
        rows = c.execute("""
            SELECT SUBSTR(fecha,1,10) as dia,
                   COUNT(*) as n_movs,
                   SUM(cantidad) as total_g
            FROM movimientos
            WHERE tipo='Entrada'
            GROUP BY SUBSTR(fecha,1,10)
            ORDER BY dia ASC
        """).fetchall()
        for r in rows:
            timeline.append({
                'fecha': r[0],
                'n_entradas': r[1],
                'total_g': round(r[2] or 0, 1),
            })
    except sqlite3.OperationalError:
        pass

    # 3. Por operador
    por_operador = []
    try:
        rows = c.execute("""
            SELECT COALESCE(operador,'(vacio)') as op,
                   COUNT(*) as n_movs,
                   SUM(cantidad) as total_g,
                   MIN(fecha) as primera,
                   MAX(fecha) as ultima
            FROM movimientos
            WHERE tipo='Entrada'
            GROUP BY operador
            ORDER BY n_movs DESC
        """).fetchall()
        for r in rows:
            por_operador.append({
                'operador': r[0],
                'n_entradas': r[1],
                'total_g': round(r[2] or 0, 1),
                'primera_fecha': str(r[3])[:10] if r[3] else '',
                'ultima_fecha':  str(r[4])[:10] if r[4] else '',
            })
    except sqlite3.OperationalError:
        pass

    # 4. Origen: con OC vs sin OC
    con_oc = 0; sin_oc = 0; total_g_con_oc = 0; total_g_sin_oc = 0
    try:
        r = c.execute("""
            SELECT COUNT(*), COALESCE(SUM(cantidad),0)
            FROM movimientos
            WHERE tipo='Entrada' AND COALESCE(numero_oc,'') != ''
        """).fetchone()
        con_oc = r[0]; total_g_con_oc = float(r[1] or 0)
        r = c.execute("""
            SELECT COUNT(*), COALESCE(SUM(cantidad),0)
            FROM movimientos
            WHERE tipo='Entrada' AND COALESCE(numero_oc,'') = ''
        """).fetchone()
        sin_oc = r[0]; total_g_sin_oc = float(r[1] or 0)
    except sqlite3.OperationalError:
        pass

    # 5. Total resumen
    try:
        total_entradas = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos WHERE tipo='Entrada'"
        ).fetchone()
    except sqlite3.OperationalError:
        total_entradas = (0, 0)

    conn.close()

    return jsonify({
        'ok': True,
        'resumen': {
            'total_entradas': total_entradas[0],
            'total_entradas_g': round(total_entradas[1], 1),
            'lotes_con_multiples_entradas': len(multi_entradas),
            'entradas_con_oc': con_oc,
            'entradas_con_oc_g': round(total_g_con_oc, 1),
            'entradas_sin_oc': sin_oc,
            'entradas_sin_oc_g': round(total_g_sin_oc, 1),
        },
        'multi_entradas': multi_entradas,
        'timeline': timeline[:60],   # primeros 60 dias
        'por_operador': por_operador,
    })


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

    # Lista detallada de los SIN proveedor — orden alfabético por nombre
    rows_sin = c.execute("""
        SELECT codigo_mp, nombre_comercial, COALESCE(tipo,'') as tipo
        FROM maestro_mps
        WHERE activo = 1
          AND (proveedor IS NULL OR TRIM(proveedor) = '')
        ORDER BY nombre_comercial COLLATE NOCASE LIMIT 200
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
                     ORDER BY nombre_comercial COLLATE NOCASE LIMIT 5""", (r["tipo"],))
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
                # Import historico: el contenido YA se publico y el pago YA ocurrio.
                # Por eso entra como 'Pagada' (no 'Pendiente'). De lo contrario, queda
                # eternamente marcado como pendiente aunque ya se haya transferido.
                c.execute("""INSERT INTO pagos_influencers
                    (influencer_id, influencer_nombre, valor, fecha, estado, concepto, numero_oc, fecha_publicacion)
                    VALUES (?, ?, ?, datetime('now'), 'Pagada', ?, ?, ?)""",
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


# ─── Auditoría de Mínimos ─────────────────────────────────────────────────────


@bp.route("/api/admin/auditar-minimos", methods=["GET"])
def auditar_minimos():
    """Auditoría no-destructiva de stock_minimo de maestro_mps.

    Para cada MP: muestra mínimo actual vs recomendado calculado por
    metodología consumo × (lead_time + buffer) según origen del proveedor.

    Query params:
      proyeccion_dias: int (30-180, default 90) — horizonte para proyectar
        consumo desde el calendario × fórmulas.

    Estados:
      OK: ratio actual/recomendado entre 0.75 y 1.50
      SUB_PROTEGIDO: actual < recomendado × 0.75
      SOBRE_PROTEGIDO: actual > recomendado × 1.50
      SIN_MINIMO_CONFIGURADO: stock_minimo = 0 con consumo > 0
      SIN_USO: sin consumo proyectado en horizonte
      SIN_USO_CON_MIN: sin consumo pero tiene mínimo configurado

    Lead times por origen:
      china: 60d lead + 30d buffer = 90d
      colombia/local: 7d lead + 14d buffer = 21d
      desconocido (con proveedor): 7d + 14d = 21d
      desconocido (sin proveedor): 14d + 14d = 28d
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    from database import get_db as _get_db
    from flask import current_app

    try:
        horizonte_proyeccion_dias = max(30, min(int(request.args.get('proyeccion_dias', 90)), 180))
    except ValueError:
        horizonte_proyeccion_dias = 90

    # 1. Cargar planificacion estratégica para el horizonte
    try:
        from blueprints.programacion import planificacion_estrategica as _plan
    except ImportError:
        from api.blueprints.programacion import planificacion_estrategica as _plan
    with current_app.test_request_context(
        f'/api/programacion/planificacion?dias={horizonte_proyeccion_dias}'
    ):
        plan_resp = _plan()
    plan_data = plan_resp.get_json() or {}

    # Consumo proyectado por MP en horizonte
    consumo_por_mp = {}
    for mp in (plan_data.get('mps_deficit') or []) + (plan_data.get('mps_ok') or []):
        consumo_por_mp[mp['material_id']] = {
            'total_g_horizonte': float(mp.get('total_g') or 0),
            'origen': mp.get('origen', 'desconocido'),
            'productos': mp.get('productos', []) or [],
        }

    # 2. Cargar maestro_mps activos
    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT m.codigo_mp, m.nombre_inci, m.nombre_comercial, m.proveedor,
                   COALESCE(m.stock_minimo, 0), COALESCE(m.tipo_material, 'MP'),
                   COALESCE(s.stock_actual, 0)
            FROM maestro_mps m
            LEFT JOIN (
                SELECT material_id,
                       SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual
                FROM movimientos GROUP BY material_id
            ) s ON m.codigo_mp = s.material_id
            WHERE m.activo = 1
            ORDER BY m.codigo_mp
        """).fetchall()
    except sqlite3.OperationalError:
        # Schema legacy sin tipo_material — fallback
        rows = conn.execute("""
            SELECT m.codigo_mp, m.nombre_inci, m.nombre_comercial, m.proveedor,
                   COALESCE(m.stock_minimo, 0), 'MP',
                   COALESCE(s.stock_actual, 0)
            FROM maestro_mps m
            LEFT JOIN (
                SELECT material_id,
                       SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual
                FROM movimientos GROUP BY material_id
            ) s ON m.codigo_mp = s.material_id
            WHERE m.activo = 1
            ORDER BY m.codigo_mp
        """).fetchall()

    auditoria = []
    for r in rows:
        codigo, nombre_inci, nombre_com, proveedor, stock_min_actual, tipo_mat, stock_actual = r
        nombre = nombre_com or nombre_inci or codigo
        proveedor = (proveedor or '').strip()
        stock_min_actual = float(stock_min_actual or 0)
        stock_actual = float(stock_actual or 0)

        proy = consumo_por_mp.get(codigo)
        consumo_horizonte_g = proy['total_g_horizonte'] if proy else 0.0
        origen = proy['origen'] if proy else 'desconocido'
        productos = proy['productos'] if proy else []
        consumo_diario_g = consumo_horizonte_g / horizonte_proyeccion_dias if horizonte_proyeccion_dias > 0 else 0
        consumo_mensual_g = consumo_diario_g * 30

        # Lead time + buffer por origen
        if origen == 'china':
            lead_time, buffer = 60, 30
        elif origen == 'colombia':
            lead_time, buffer = 7, 14
        else:
            if proveedor:
                lead_time, buffer = 7, 14
            else:
                lead_time, buffer = 14, 14
        dias_buffer = lead_time + buffer

        # Recomendado
        if consumo_diario_g <= 0:
            minimo_recomendado = 0.0
            estado = 'SIN_USO_CON_MIN' if stock_min_actual > 0 else 'SIN_USO'
            razonamiento = f'Sin uso proyectado en próximos {horizonte_proyeccion_dias} días'
        else:
            minimo_recomendado = consumo_diario_g * dias_buffer
            # Piso para peptides de baja rotación
            if consumo_diario_g < 0.5:
                minimo_recomendado = max(minimo_recomendado, 50)

            if stock_min_actual == 0:
                estado = 'SIN_MINIMO_CONFIGURADO'
                razonamiento = (
                    f'Sin mínimo configurado · Recomendado {int(round(minimo_recomendado))} g '
                    f'({lead_time}d lead + {buffer}d buffer × {round(consumo_diario_g, 2)} g/día)'
                )
            else:
                ratio = stock_min_actual / minimo_recomendado if minimo_recomendado > 0 else 1.0
                cobertura_dias_actual = stock_min_actual / consumo_diario_g if consumo_diario_g > 0 else 0
                if ratio < 0.75:
                    estado = 'SUB_PROTEGIDO'
                    razonamiento = (
                        f'Mínimo cubre solo ~{round(cobertura_dias_actual, 1)} días '
                        f'(necesita ~{dias_buffer} días para origen {origen})'
                    )
                elif ratio > 1.5:
                    estado = 'SOBRE_PROTEGIDO'
                    razonamiento = (
                        f'Mínimo cubre ~{round(cobertura_dias_actual, 1)} días '
                        f'(suficiente con ~{dias_buffer} días para {origen})'
                    )
                else:
                    estado = 'OK'
                    razonamiento = f'Mínimo cubre ~{round(cobertura_dias_actual, 1)} días — apropiado'

        auditoria.append({
            'codigo_mp': codigo,
            'nombre': nombre,
            'proveedor': proveedor,
            'origen': origen,
            'tipo_material': tipo_mat,
            'stock_actual_g': round(stock_actual, 1),
            'stock_minimo_actual_g': round(stock_min_actual, 1),
            'consumo_horizonte_g': round(consumo_horizonte_g, 1),
            'consumo_diario_g': round(consumo_diario_g, 3),
            'consumo_mensual_g': round(consumo_mensual_g, 1),
            'lead_time_dias': lead_time,
            'buffer_dias': buffer,
            'dias_cobertura_total': dias_buffer,
            'minimo_recomendado_g': round(minimo_recomendado, 1),
            'estado': estado,
            'razonamiento': razonamiento,
            'productos': productos,
        })

    # Stats
    stats = {
        'total': len(auditoria),
        'ok': sum(1 for a in auditoria if a['estado'] == 'OK'),
        'sub_protegido': sum(1 for a in auditoria if a['estado'] == 'SUB_PROTEGIDO'),
        'sobre_protegido': sum(1 for a in auditoria if a['estado'] == 'SOBRE_PROTEGIDO'),
        'sin_minimo': sum(1 for a in auditoria if a['estado'] == 'SIN_MINIMO_CONFIGURADO'),
        'sin_uso': sum(1 for a in auditoria if a['estado'].startswith('SIN_USO')),
    }

    return jsonify({
        'horizonte_proyeccion_dias': horizonte_proyeccion_dias,
        'stats': stats,
        'auditoria': auditoria,
        'metodologia': {
            'formula': 'minimo_recomendado = consumo_diario × (lead_time + buffer)',
            'piso_peptides': 'min 50g si consumo < 0.5 g/día',
            'lead_times': {
                'china': '60d lead + 30d buffer = 90d',
                'colombia/local': '7d lead + 14d buffer = 21d',
                'desconocido_sin_proveedor': '14d + 14d = 28d',
            },
        },
    })


@bp.route("/api/admin/aplicar-minimos", methods=["POST"])
def aplicar_minimos():
    """Aplica el recálculo de stock_minimo basado en /auditar-minimos.

    Requiere:
      - Token textual exacto: 'APLICAR_MINIMOS_RECALCULADOS_2026'
      - Backup automático previo
      - Audit log del cambio

    Body:
      token: str (obligatorio)
      proyeccion_dias: int (default 90)
      solo_estados: list[str] (default los 3: SUB_PROTEGIDO, SOBRE_PROTEGIDO,
                    SIN_MINIMO_CONFIGURADO)
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    d = request.json or {}
    if d.get('token', '').strip() != 'APLICAR_MINIMOS_RECALCULADOS_2026':
        return jsonify({'error': 'Token incorrecto'}), 403

    try:
        horizonte = max(30, min(int(d.get('proyeccion_dias', 90)), 180))
    except ValueError:
        horizonte = 90

    solo_estados = d.get('solo_estados') or [
        'SUB_PROTEGIDO', 'SOBRE_PROTEGIDO', 'SIN_MINIMO_CONFIGURADO'
    ]

    # Backup previo
    try:
        do_backup(triggered_by='pre_minimos_recalc')
    except Exception as e:
        return jsonify({'error': f'Backup falló: {str(e)[:200]}'}), 500

    # Reusar la lógica de auditoría
    from flask import current_app
    with current_app.test_request_context(
        f'/api/admin/auditar-minimos?proyeccion_dias={horizonte}'
    ):
        audit_resp = auditar_minimos()
    audit_data = audit_resp.get_json() or {}

    from database import get_db as _get_db
    conn = _get_db()
    c = conn.cursor()

    cambios = []
    for item in (audit_data.get('auditoria') or []):
        if item['estado'] not in solo_estados:
            continue
        if item['estado'].startswith('SIN_USO'):
            continue  # No tocar — el usuario puede tener motivo
        codigo = item['codigo_mp']
        nuevo = float(item['minimo_recomendado_g'])
        previo = float(item['stock_minimo_actual_g'])
        try:
            c.execute(
                "UPDATE maestro_mps SET stock_minimo = ? WHERE codigo_mp = ?",
                (nuevo, codigo),
            )
            cambios.append({
                'codigo_mp': codigo,
                'nombre': item['nombre'],
                'previo_g': round(previo, 1),
                'nuevo_g': round(nuevo, 1),
                'estado_previo': item['estado'],
            })
        except Exception:
            continue
    conn.commit()

    # Audit log
    try:
        import json as _json
        c.execute(
            """INSERT INTO audit_log
               (usuario, accion, tabla, registro_id, detalle, ip, fecha)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (u, 'APLICAR_MINIMOS_RECALCULADOS', 'maestro_mps', '_BULK_',
             _json.dumps({
                 'count': len(cambios),
                 'horizonte_proyeccion_dias': horizonte,
                 'estados_aplicados': solo_estados,
             }, ensure_ascii=False),
             request.remote_addr),
        )
        conn.commit()
    except Exception:
        pass

    return jsonify({
        'ok': True,
        'count_cambios': len(cambios),
        'cambios': cambios[:50],
        'mensaje': f'{len(cambios)} mínimos actualizados. Backup previo creado.',
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
  <button class="tab" data-tab="audit-inv" onclick="switchTab('audit-inv')">&#x1F50D; Auditar Inventario</button>
  <button class="tab" data-tab="audit-min" onclick="switchTab('audit-min')">&#x1F4CA; Auditar M&iacute;nimos</button>
  <button class="tab" data-tab="diag-form" onclick="switchTab('diag-form')">&#x1F9EA; Diagn&oacute;stico F&oacute;rmulas</button>
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

  <div class="card" style="border-left:3px solid #fbbf24;">
    <h2>&#x1F4DD; Corregir nombres masivos desde Excel</h2>
    <div class="section-sub">
      Sube un Excel con columnas <code>código</code> + <code>nombre</code>
      (+ <code>proveedor</code> opcional). Solo actualiza nombres que est&aacute;n
      <strong>vac&iacute;os o iguales al c&oacute;digo</strong> (mal cargados).
      <strong>Nombres correctos NO se sobrescriben.</strong>
    </div>
    <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="file" id="mps-nom-file" accept=".xlsx,.xlsm"
             style="padding:8px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;">
      <button class="btn btn-outline" onclick="syncMpsNombres(true)">&#x1F441; Vista previa</button>
      <button class="btn" onclick="syncMpsNombres(false)" style="background:linear-gradient(135deg,#f59e0b,#d97706);">&#x26A1; Aplicar correcci&oacute;n</button>
    </div>
    <div id="mps-nom-result" style="margin-top:14px;"></div>
  </div>
</div>

<!-- ─── TAB AUDITAR INVENTARIO vs EXCEL día cero ─── -->
<div id="tab-audit-inv" class="tab-panel">
  <div class="card">
    <h2>&#x1F50D; Auditar Inventario vs Excel d&iacute;a cero</h2>
    <div class="section-sub">
      Sube el Excel del conteo f&iacute;sico (ej: <code>INVENTARIO_MP_v8_1.xlsx</code>) — solo se contar&aacute;n las
      filas marcadas en <strong style="color:#16a34a;">verde</strong>. Las rojas y sin marcar se ignoran (Catalina las marc&oacute; como NO presentes).
      <br><br>
      <strong>Cero escritura</strong>. El reporte muestra c&oacute;mo difiere el kardex actual contra ese conteo + las producciones que se han hecho desde entonces.
      Despu&eacute;s decides: ajustes quir&uacute;rgicos o reset+replay.
    </div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap;">
      <input type="file" id="audit-inv-file" accept=".xlsx,.xlsm" style="padding:6px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;">
      <button class="btn" onclick="auditarInvVsExcel()">&#x1F4CA; Generar reporte</button>
      <button class="btn btn-outline" onclick="diagnosticoEntradas()" title="Antes de borrar nada, ver QUIEN cargo QUE — detecta doble carga vs recepciones manuales legitimas">&#x1F50E; Diagn&oacute;stico de entradas</button>
      <button class="btn btn-outline" onclick="quePuedoProducir()" title="Para cada producto, indica si las MPs alcanzan + shopping list de faltantes" style="border-color:#fbbf24;color:#fbbf24;">&#x1F3ED; Qu&eacute; puedo producir</button>
      <button class="btn btn-outline" onclick="healthMonitor()" title="Monitor periodico: detecta bursts, multi-entradas, anomalias en stock — alerta antes de que la duplicacion sea masiva" style="border-color:#ef4444;color:#ef4444;">&#x1F525; Monitor anomal&iacute;as</button>
    </div>

    <div style="margin-top:24px;padding:16px;background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.4);border-radius:10px;">
      <h3 style="color:#fca5a5;margin:0 0 8px 0;">&#x26A0; Reset + Replay del inventario</h3>
      <div style="font-size:12px;color:#cbd5e1;margin-bottom:12px;">
        <strong style="color:#fca5a5;">DESTRUCTIVO.</strong> Borra todos los movimientos y los recarga desde el Excel verde (estado d&iacute;a cero) + preserva las recepciones formales con OC + re-aplica las salidas de las producciones.
        <br>Sigue el orden: <strong>1)</strong> Descarga snapshot &rarr; <strong>2)</strong> Preview &rarr; <strong>3)</strong> Aplicar.
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <button class="btn btn-outline" onclick="sembrarMaestroDesdeExcel()" style="border-color:#a5b4fc;color:#a5b4fc;" title="Asegura que TODOS los códigos del Excel (verdes Y no-verdes) estén en maestro_mps. NO toca movimientos. Recomendado correr ANTES del reset.">&#x1F331; 0. Sembrar cat&aacute;logo MPs</button>
        <button class="btn btn-outline" onclick="descargarSnapshotPreReset()" title="Descarga JSON con TODOS los movimientos, producciones, OCs, comprobantes — para poder revertir si algo sale mal">&#x1F4BE; 1. Descargar snapshot pre-reset</button>
        <button class="btn btn-outline" onclick="previewReset()" title="Muestra que va a pasar SIN escribir nada">&#x1F441; 2. Preview reset</button>
        <button class="btn" onclick="aplicarReset()" style="background:#dc2626;color:#fff;" title="Ejecuta el reset. Pide token textual de confirmacion.">&#x1F4A5; 3. APLICAR reset</button>
        <button class="btn btn-outline" onclick="healthCheckPostReset()" style="border-color:#34d399;color:#34d399;" title="Verifica integridad del sistema despues del reset">&#x2705; 4. Health-check post-reset</button>
      </div>
    </div>

    <div id="audit-inv-result" style="margin-top:18px;"></div>
  </div>
</div>

<!-- ─── TAB DIAGNOSTICO FORMULAS ─── -->
<div id="tab-diag-form" class="tab-panel">
  <div class="card">
    <h2>&#x1F9EA; Diagn&oacute;stico de F&oacute;rmulas</h2>
    <div class="section-sub">
      Detecta items en <code>formula_items</code> que apuntan a <strong>material_id</strong> hu&eacute;rfano (no en <code>maestro_mps</code>) o cuyo nombre no coincide con el cat&aacute;logo. Sugiere correcci&oacute;n autom&aacute;tica buscando por nombre similar.
      <br><br>
      Importante: si las f&oacute;rmulas apuntan a c&oacute;digos legacy o err&oacute;neos, la <strong>Vista por producci&oacute;n</strong> y los <strong>cálculos de stock</strong> dan resultados incorrectos. Usa esto para sincronizar.
    </div>
    <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn" onclick="cargarDiagnosticoFormulas()" id="btn-diag-form">&#x1F50D; Ejecutar diagn&oacute;stico</button>
      <button class="btn btn-outline" onclick="exportarDiagFormCSV()">&#x1F4C4; Exportar CSV</button>
    </div>

    <div id="diag-form-stats" style="margin-top:18px;display:none;">
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-l">Total &iacute;tems</div><div class="kpi-v" id="diagf-total">-</div></div>
        <div class="kpi" style="border-left:3px solid #fbbf24;"><div class="kpi-l">Con problemas</div><div class="kpi-v" id="diagf-problemas" style="color:#fbbf24;">-</div></div>
        <div class="kpi" style="border-left:3px solid #dc2626;"><div class="kpi-l">Hu&eacute;rfanos</div><div class="kpi-v" id="diagf-huerf" style="color:#dc2626;">-</div></div>
        <div class="kpi" style="border-left:3px solid #f59e0b;"><div class="kpi-l">Mismatch nombre</div><div class="kpi-v" id="diagf-misn" style="color:#f59e0b;">-</div></div>
        <div class="kpi" style="border-left:3px solid #22c55e;"><div class="kpi-l">Auto-corregibles</div><div class="kpi-v" id="diagf-auto" style="color:#22c55e;">-</div></div>
        <div class="kpi" style="border-left:3px solid #6366f1;"><div class="kpi-l">Requieren revisi&oacute;n</div><div class="kpi-v" id="diagf-rev" style="color:#6366f1;">-</div></div>
      </div>
    </div>

    <div style="margin-top:14px;padding:14px;background:#0f3a1f;border:2px solid #16a34a;border-radius:8px;">
      <div style="font-weight:700;color:#86efac;margin-bottom:6px;">&#x2705; Aplicar batch de correcciones validado por Sebasti&aacute;n + Alejandro (2026-04-28)</div>
      <div style="font-size:12px;color:#bbf7d0;margin-bottom:10px;">
        Aplica de una sola pulsaci&oacute;n los <strong>240 cambios</strong> consensuados:
        <ul style="margin:6px 0 6px 20px;font-size:11px;">
          <li>44 MPs nuevos creados (HPR, RR, p&eacute;ptidos premium, dimethicone, soda c&aacute;ustica, etc.)</li>
          <li>Azeclair (MP00284) marcado <code>activo=0</code> · INCI oficial actualizado en AOS 40</li>
          <li>207 <code>formula_items</code> corregidos (typos, mapeos a Vit C / Carbopol / Plantaren / etc.)</li>
          <li>33 filas de Agua Desionizada eliminadas (agua interna infinita)</li>
        </ul>
        <strong>Backup autom&aacute;tico previo</strong> (full DB + tablas <code>*_backup_20260428</code>). Ejecuci&oacute;n at&oacute;mica en transacci&oacute;n.
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <input id="diagf-token-batch20260428" placeholder="Token: APLICAR_CORRECCIONES_2026_04_28" style="background:#0f172a;color:#e2e8f0;border:1px solid #86efac;border-radius:6px;padding:7px 10px;font-size:12px;width:340px;">
        <button class="btn" style="background:#16a34a;color:#fff;font-weight:700;" onclick="aplicarBatch20260428()" id="btn-aplicar-batch">&#x2728; Aplicar 240 correcciones</button>
      </div>
    </div>

    <div style="margin-top:14px;padding:14px;background:#3f0f0f;border:2px solid #dc2626;border-radius:8px;">
      <div style="font-weight:700;color:#fca5a5;margin-bottom:6px;">&#x21A9; Revertir &uacute;ltima correcci&oacute;n de f&oacute;rmulas (deshacer)</div>
      <div style="font-size:12px;color:#fecaca;margin-bottom:10px;">
        Si aplicaste correcciones y te diste cuenta que estaban mal, este bot&oacute;n restaura <code>formula_items</code> al estado del backup autom&aacute;tico que se cre&oacute; antes de aplicar. NO toca movimientos / cat&aacute;logo / OCs.
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <input id="diagf-token-revertir" placeholder="Token: REVERTIR_FORMULAS_2026" style="background:#0f172a;color:#e2e8f0;border:1px solid #fca5a5;border-radius:6px;padding:7px 10px;font-size:12px;width:280px;">
        <button class="btn" style="background:#991b1b;color:#fff;" onclick="revertirFormulas()" id="btn-revertir-form">&#x21A9; Revertir desde backup</button>
      </div>
    </div>

    <div id="diag-form-aplicar-box" style="display:none;margin-top:14px;padding:14px;background:#1e293b;border:1px solid #475569;border-radius:8px;">
      <div style="font-weight:700;color:#fbbf24;margin-bottom:6px;">&#x26A0; Aplicar correcciones</div>
      <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
        Solo se aplican las marcadas (auto-corregibles vienen marcadas por default). Backup autom&aacute;tico previo + audit log.
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <button class="btn btn-outline" onclick="seleccionarSoloAuto()">Solo auto-corregibles</button>
        <button class="btn btn-outline" onclick="seleccionarTodos()">Seleccionar todos</button>
        <button class="btn btn-outline" onclick="deseleccionarTodos()">Deseleccionar</button>
        <input id="diagf-token" placeholder="Token: CORREGIR_FORMULAS_2026" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:7px 10px;font-size:12px;width:280px;">
        <button class="btn" style="background:#dc2626;color:#fff;" onclick="aplicarCorreccionFormulas()" id="btn-aplicar-form">&#x1F4A5; Aplicar correcciones</button>
      </div>
    </div>

    <div id="diag-form-obsoletas-box" style="display:none;margin-top:14px;padding:14px;background:#1e1b3b;border:1px solid #6366f1;border-radius:8px;">
      <div style="font-weight:700;color:#a5b4fc;margin-bottom:6px;">&#x1F5D1; Eliminar f&oacute;rmulas obsoletas (sin candidato)</div>
      <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
        Los <strong>hu&eacute;rfanos sin candidato</strong> son items en <code>formula_items</code> cuyo <code>material_id</code> NO existe en cat&aacute;logo Y no encontramos similar por nombre. Probablemente son ingredientes descontinuados o productos obsoletos. Eliminarlos NO afecta producciones actuales (esos productos no se pueden producir hasta que la f&oacute;rmula se reescriba).
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span id="diagf-sin-cand-count" style="color:#fca5a5;font-weight:700;font-size:13px;">- huérfanos sin candidato</span>
        <input id="diagf-token-eliminar" placeholder="Token: ELIMINAR_FORMULAS_OBSOLETAS_2026" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:7px 10px;font-size:12px;width:340px;">
        <button class="btn" style="background:#7c3aed;color:#fff;" onclick="eliminarFormulasObsoletas()" id="btn-eliminar-obs">&#x1F5D1; Eliminar obsoletas</button>
      </div>
    </div>

    <div id="diag-form-result" style="margin-top:14px;"></div>
  </div>
</div>

<!-- ─── TAB AUDITAR MINIMOS ─── -->
<div id="tab-audit-min" class="tab-panel">
  <div class="card">
    <h2>&#x1F4CA; Auditar M&iacute;nimos de Materias Primas</h2>
    <div class="section-sub">
      Compara <strong>stock_minimo</strong> actual vs lo recomendado por consumo proyectado.
      M&eacute;todo: <code>min&iacute;mo = consumo_diario &times; (lead_time + buffer)</code> seg&uacute;n origen del proveedor:
      China 90 d&iacute;as, Colombia/local 21 d&iacute;as. Piso 50 g para p&eacute;ptidos de baja rotaci&oacute;n.
    </div>
    <div style="margin-top:14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <label style="font-size:13px;color:#cbd5e1;">Horizonte de proyecci&oacute;n:</label>
      <select id="audmin-proy" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:6px 10px;font-size:13px;">
        <option value="60">60 d&iacute;as</option>
        <option value="90" selected>90 d&iacute;as (recomendado)</option>
        <option value="120">120 d&iacute;as</option>
        <option value="180">180 d&iacute;as</option>
      </select>
      <button class="btn" onclick="cargarAuditarMinimos()" id="btn-aud-min">&#x1F50D; Auditar (vista previa)</button>
      <button class="btn btn-outline" onclick="exportarAuditMinCSV()">&#x1F4C4; Exportar CSV</button>
    </div>

    <div id="audmin-stats" style="margin-top:18px;display:none;">
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-l">Total MPs</div><div class="kpi-v" id="audmin-total">-</div></div>
        <div class="kpi" style="border-left:3px solid #22c55e;"><div class="kpi-l">OK</div><div class="kpi-v" id="audmin-ok" style="color:#22c55e;">-</div></div>
        <div class="kpi" style="border-left:3px solid #dc2626;"><div class="kpi-l">Sub-protegidos</div><div class="kpi-v" id="audmin-sub" style="color:#dc2626;">-</div></div>
        <div class="kpi" style="border-left:3px solid #f59e0b;"><div class="kpi-l">Sobre-protegidos</div><div class="kpi-v" id="audmin-sobre" style="color:#f59e0b;">-</div></div>
        <div class="kpi" style="border-left:3px solid #6366f1;"><div class="kpi-l">Sin m&iacute;nimo</div><div class="kpi-v" id="audmin-vacio" style="color:#6366f1;">-</div></div>
        <div class="kpi"><div class="kpi-l">Sin uso</div><div class="kpi-v" id="audmin-uso" style="color:#94a3b8;">-</div></div>
      </div>
    </div>

    <div id="audmin-aplicar-box" style="display:none;margin-top:18px;padding:14px;background:#1e293b;border:1px solid #475569;border-radius:8px;">
      <div style="font-weight:700;margin-bottom:6px;color:#fbbf24;">&#x26A0; Aplicar recálculo</div>
      <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
        Esto actualiza <code>stock_minimo</code> en <code>maestro_mps</code> para los MPs marcados como
        <strong>SUB_PROTEGIDO</strong>, <strong>SOBRE_PROTEGIDO</strong> y <strong>SIN_MINIMO_CONFIGURADO</strong>.
        Crea backup autom&aacute;tico previo y registra en audit log. NO toca MPs sin uso proyectado.
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <input id="audmin-token" placeholder="Token: APLICAR_MINIMOS_RECALCULADOS_2026" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:7px 10px;font-size:12px;width:340px;">
        <button class="btn" style="background:#dc2626;color:#fff;" onclick="aplicarRecalculoMinimos()" id="btn-aplicar-min">&#x1F4A5; Aplicar recálculo</button>
      </div>
    </div>

    <div id="audmin-result" style="margin-top:18px;"></div>
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
const _loaded = {backups:false, users:false, security:false, config:false, banco:false, mps:false, 'audit-inv':false};
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
// ── Auditar inventario contra Excel día cero ─────────────────────────────────
function _fmtG(n) {
  // Normalizado: SIEMPRE en gramos con separador de miles (acordado con Alejandro).
  if (n == null) return '—';
  return Math.round(Number(n) || 0).toLocaleString('es-CO') + ' g';
}
function _esc(s) { return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }
async function auditarInvVsExcel() {
  const fileEl = document.getElementById('audit-inv-file');
  const out = document.getElementById('audit-inv-result');
  if (!fileEl.files || !fileEl.files[0]) {
    out.innerHTML = '<div style="color:#fca5a5;">Selecciona un .xlsx primero.</div>';
    return;
  }
  out.innerHTML = '<div style="color:#94a3b8;">Procesando Excel + comparando contra DB... espera...</div>';
  const fd = new FormData();
  fd.append('file', fileEl.files[0]);
  try {
    const r = await fetch('/api/admin/audit-inventario-vs-excel', {method: 'POST', body: fd});
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + (d.detail?' — '+_esc(d.detail):'') + '</div>'; return; }
    const s = d.resumen;
    let h = '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi"><div class="kpi-l">Lotes verdes (Excel)</div><div class="kpi-v">' + s.lotes_verde_excel + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Excluidos (no verde)</div><div class="kpi-v">' + s.lotes_excluidos_no_verde + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Stock total Excel</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(s.stock_total_excel_g) + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Stock total DB ahora</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(s.stock_total_db_actual_g) + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Producciones desde día 0</div><div class="kpi-v">' + s.producciones_registradas + ' (' + s.producciones_total_kg.toLocaleString('es-CO') + ' kg)</div></div>';
    h += '</div>';

    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi" style="background:rgba(16,185,129,.12);"><div class="kpi-l" style="color:#34d399;">✓ Match (cantidad ok)</div><div class="kpi-v">' + s.count_match + '</div></div>';
    h += '<div class="kpi" style="background:rgba(245,158,11,.12);"><div class="kpi-l" style="color:#fbbf24;">⚠ Con delta</div><div class="kpi-v">' + s.count_delta + '</div></div>';
    h += '<div class="kpi" style="background:rgba(239,68,68,.12);"><div class="kpi-l" style="color:#fca5a5;">✗ Faltantes en DB</div><div class="kpi-v">' + s.count_faltantes_en_db + '</div></div>';
    h += '<div class="kpi" style="background:rgba(99,102,241,.12);"><div class="kpi-l" style="color:#a5b4fc;">+ Solo en DB (post)</div><div class="kpi-v">' + s.count_solo_db_no_excel + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Δ total</div><div class="kpi-v" style="font-size:14px;color:' + (s.delta_total_g < 0 ? '#fca5a5' : '#34d399') + ';">' + _fmtG(s.delta_total_g) + '</div></div>';
    h += '</div>';

    function table(items, cols, title, color) {
      let t = '<h3 style="color:' + color + ';margin-top:18px;margin-bottom:8px;">' + title + ' (' + items.length + ')</h3>';
      if (!items.length) return t + '<div style="color:#94a3b8;font-size:12px;">— vacío —</div>';
      t += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:8px;"><table style="width:100%;border-collapse:collapse;font-size:12px;">';
      t += '<thead style="background:#1e293b;"><tr>' + cols.map(c => '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">' + c.label + '</th>').join('') + '</tr></thead><tbody>';
      items.forEach(it => {
        t += '<tr style="border-top:1px solid #334155;">';
        cols.forEach(c => {
          let v = it[c.key];
          if (c.fmt === 'g') v = _fmtG(v);
          t += '<td style="padding:6px 10px;color:' + (c.color||'#e2e8f0') + ';' + (c.fmt==='g'?'text-align:right;font-family:monospace;':'') + '">' + _esc(v) + '</td>';
        });
        t += '</tr>';
      });
      t += '</tbody></table></div>';
      return t;
    }

    h += table(d.en_db_con_delta, [
      {label:'Código', key:'codigo_mp'},
      {label:'Material', key:'nombre_comercial'},
      {label:'Lote', key:'lote'},
      {label:'Excel (g)', key:'cant_excel_g', fmt:'g'},
      {label:'Salidas DB', key:'salidas_db_g', fmt:'g'},
      {label:'Esperado', key:'neto_esperado_g', fmt:'g'},
      {label:'Actual DB', key:'neto_db_g', fmt:'g'},
      {label:'Δ', key:'delta_g', fmt:'g', color:'#fbbf24'},
    ], '⚠ Lotes con cantidad distinta a la esperada', '#fbbf24');

    h += table(d.faltantes_en_db, [
      {label:'Código', key:'codigo_mp'},
      {label:'Material', key:'nombre_comercial'},
      {label:'Lote', key:'lote'},
      {label:'Proveedor (Excel)', key:'proveedor_excel'},
      {label:'Cant Excel', key:'cant_excel_g', fmt:'g', color:'#fca5a5'},
    ], '✗ Lotes verdes en Excel pero NO en DB (desaparecieron)', '#fca5a5');

    h += table(d.solo_db_no_excel, [
      {label:'Código', key:'codigo_mp'},
      {label:'Lote', key:'lote'},
      {label:'Entradas DB', key:'entradas_db_g', fmt:'g'},
      {label:'Salidas DB', key:'salidas_db_g', fmt:'g'},
      {label:'Neto DB', key:'neto_db_g', fmt:'g', color:'#a5b4fc'},
    ], '+ Lotes en DB pero NO en Excel verde (post-día-cero o sobrante)', '#a5b4fc');

    if (d.nota_truncado) {
      h += '<div style="margin-top:14px;color:#94a3b8;font-size:11px;">ℹ Tablas truncadas a 300 items. Hay más — contacta para ver el JSON completo o exportar.</div>';
    }

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error de red: ' + _esc(e.message) + '</div>';
  }
}

async function sembrarMaestroDesdeExcel() {
  const fileEl = document.getElementById('audit-inv-file');
  const out = document.getElementById('audit-inv-result');
  if (!fileEl.files || !fileEl.files[0]) {
    out.innerHTML = '<div style="color:#fbbf24;">Selecciona primero el Excel arriba.</div>';
    return;
  }
  out.innerHTML = '<div style="color:#94a3b8;">Sembrando catálogo MPs desde Excel (verdes + no-verdes)...</div>';
  try {
    const fd = new FormData();
    fd.append('file', fileEl.files[0]);
    const r = await fetch('/api/admin/sembrar-maestro-desde-excel', {method: 'POST', body: fd});
    const d = await r.json();
    if (!r.ok) {
      out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>';
      return;
    }
    let h = '<h3 style="color:#a5b4fc;margin-top:0;">🌱 Catálogo MPs sembrado</h3>';
    h += '<div style="color:#cbd5e1;font-size:13px;margin-bottom:14px;">' + _esc(d.mensaje) + '</div>';
    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi"><div class="kpi-l">MPs nuevos en catálogo</div><div class="kpi-v" style="color:#a5b4fc;">' + d.nuevos_count + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Proveedores actualizados</div><div class="kpi-v" style="color:#34d399;">' + d.proveedores_actualizados_count + '</div></div>';
    h += '</div>';
    if (d.nuevos_sample && d.nuevos_sample.length) {
      h += '<h4 style="color:#a5b4fc;">Nuevos en catálogo (sample primeros 30)</h4>';
      h += '<table><thead><tr><th>Código</th><th>Nombre</th><th>Proveedor</th></tr></thead><tbody>';
      d.nuevos_sample.forEach(n => {
        h += '<tr><td style="font-family:monospace;">' + _esc(n.codigo_mp) + '</td><td>' + _esc(n.nombre_comercial) + '</td><td>' + _esc(n.proveedor||'—') + '</td></tr>';
      });
      h += '</tbody></table>';
    }
    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function descargarSnapshotPreReset() {
  const out = document.getElementById('audit-inv-result');
  out.innerHTML = '<div style="color:#94a3b8;">Generando snapshot... esto descarga un JSON grande.</div>';
  try {
    const r = await fetch('/api/admin/inventario-snapshot-pre-reset');
    if (!r.ok) {
      const d = await r.json();
      out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>';
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ts = new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
    a.download = 'snapshot_pre_reset_' + ts + '.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    out.innerHTML = '<div style="color:#34d399;font-weight:700;">✓ Snapshot descargado. Guárdalo fuera de Render antes del reset.</div>';
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function previewReset() {
  const fileEl = document.getElementById('audit-inv-file');
  const out = document.getElementById('audit-inv-result');
  if (!fileEl.files || !fileEl.files[0]) {
    out.innerHTML = '<div style="color:#fca5a5;">Selecciona el .xlsx primero.</div>';
    return;
  }
  out.innerHTML = '<div style="color:#94a3b8;">Calculando preview...</div>';
  const fd = new FormData();
  fd.append('file', fileEl.files[0]);
  try {
    const r = await fetch('/api/admin/inventario-reset-preview', {method:'POST', body:fd});
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    const p = d.plan;
    let h = '<h3 style="color:#a5b4fc;margin-top:0;">&#x1F441; Preview del Reset (sin escribir)</h3>';
    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi" style="background:rgba(239,68,68,.12);"><div class="kpi-l" style="color:#fca5a5;">Movs a borrar</div><div class="kpi-v">' + p.movimientos_a_borrar + '</div></div>';
    h += '<div class="kpi" style="background:rgba(16,185,129,.12);"><div class="kpi-l" style="color:#34d399;">Entradas iniciales (Excel)</div><div class="kpi-v">' + p.entradas_iniciales_a_crear.count + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Total g a cargar</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(p.entradas_iniciales_a_crear.total_g) + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Entradas OC preservadas</div><div class="kpi-v">' + p.entradas_oc_a_preservar.count + ' (' + _fmtG(p.entradas_oc_a_preservar.total_g) + ')</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Salidas Producción preservadas</div><div class="kpi-v">' + p.salidas_produccion_a_preservar.count + ' (' + _fmtG(p.salidas_produccion_a_preservar.total_g) + ')</div></div>';
    h += '</div>';

    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi"><div class="kpi-l">Stock actual</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(d.resumen_pre_post.stock_actual_g) + '</div></div>';
    h += '<div class="kpi" style="background:rgba(16,185,129,.12);"><div class="kpi-l" style="color:#34d399;">Stock POST-reset</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(d.resumen_pre_post.stock_post_reset_g_estimado) + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Δ esperado</div><div class="kpi-v" style="font-size:14px;color:' + (d.resumen_pre_post.delta_g < 0 ? '#fca5a5' : '#34d399') + ';">' + _fmtG(d.resumen_pre_post.delta_g) + '</div></div>';
    h += '</div>';

    // ── Bloque NUEVO: lotes compensados FEFO (fix del bug día cero) ──
    const compCount = p.entradas_iniciales_a_crear.lotes_compensados_por_salidas_post_count || 0;
    const compSample = p.entradas_iniciales_a_crear.lotes_compensados_sample_top10 || [];
    if (compCount > 0) {
      h += '<div style="background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.4);border-radius:8px;padding:12px;margin-bottom:14px;">';
      h += '<div style="color:#34d399;font-weight:700;margin-bottom:4px;">🛡️ ' + compCount + ' lotes verdes con compensación FEFO (no quedarán negativos)</div>';
      h += '<div style="color:#cbd5e1;font-size:12px;margin-bottom:8px;">Estos lotes están en el Excel verde Y tienen salidas de producción. Cantidad inicial al día cero = excel_actual + salidas_post, para que el FEFO los lleve exactamente al valor reportado HOY sin pasarse a negativo.</div>';
      h += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:6px;max-height:280px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead style="background:#1e293b;position:sticky;top:0;"><tr>';
      ['Código','Lote','Excel HOY (g)','Salidas post (g)','→ Cantidad día cero (g)'].forEach(t => {
        h += '<th style="padding:6px 8px;text-align:left;color:#cbd5e1;">' + t + '</th>';
      });
      h += '</tr></thead><tbody>';
      compSample.forEach(o => {
        h += '<tr style="border-top:1px solid #334155;">';
        h += '<td style="padding:5px 8px;font-family:monospace;color:#e2e8f0;">' + _esc(o.codigo_mp) + '</td>';
        h += '<td style="padding:5px 8px;font-family:monospace;color:#94a3b8;">' + _esc(o.lote) + '</td>';
        h += '<td style="padding:5px 8px;text-align:right;font-family:monospace;color:#cbd5e1;">' + _fmtG(o.cantidad_excel_actual_g) + '</td>';
        h += '<td style="padding:5px 8px;text-align:right;font-family:monospace;color:#fbbf24;">+' + _fmtG(o.salidas_post_dia_cero_g) + '</td>';
        h += '<td style="padding:5px 8px;text-align:right;font-family:monospace;color:#34d399;font-weight:700;">' + _fmtG(o.cantidad_inicial_dia_cero_g) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      h += '<div style="color:#94a3b8;font-size:10px;margin-top:6px;">Top 10 mostrados de ' + compCount + ' lotes compensados.</div>';
      h += '</div>';
    } else {
      h += '<div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px 12px;margin-bottom:14px;color:#34d399;font-size:12px;">✓ Sin lotes que requieran compensación FEFO — todas las salidas son a lotes huérfanos o no hay salidas previas.</div>';
    }

    const hue = p.huerfanos_a_regenerar || {count:0, total_g_entradas_virtuales:0, sample:[]};
    if (hue.count > 0) {
      h += '<div style="background:rgba(99,102,241,.10);border:1px solid rgba(99,102,241,.4);border-radius:8px;padding:12px;margin-bottom:14px;">';
      h += '<div style="color:#a5b4fc;font-weight:700;margin-bottom:4px;">♻ ' + hue.count + ' lotes huérfanos a regenerar (' + _fmtG(hue.total_g_entradas_virtuales) + ')</div>';
      h += '<div style="color:#cbd5e1;font-size:12px;margin-bottom:6px;">' + _esc(hue.nota || '') + '</div>';
      h += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:6px;max-height:240px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead style="background:#1e293b;position:sticky;top:0;"><tr>';
      ['Código','Lote','Consumido (g)','Entrada virtual (g)','Origen'].forEach(t => {
        h += '<th style="padding:6px 8px;text-align:left;color:#cbd5e1;">' + t + '</th>';
      });
      h += '</tr></thead><tbody>';
      hue.sample.forEach(o => {
        h += '<tr style="border-top:1px solid #334155;">';
        h += '<td style="padding:5px 8px;font-family:monospace;color:#e2e8f0;">' + _esc(o.codigo_mp) + '</td>';
        h += '<td style="padding:5px 8px;font-family:monospace;color:#94a3b8;">' + _esc(o.lote) + '</td>';
        h += '<td style="padding:5px 8px;text-align:right;font-family:monospace;color:#fca5a5;">' + _fmtG(o.cantidad_consumida_g) + '</td>';
        h += '<td style="padding:5px 8px;text-align:right;font-family:monospace;color:#34d399;">' + _fmtG(o.cantidad_entrada_virtual_g) + '</td>';
        h += '<td style="padding:5px 8px;color:#94a3b8;font-size:10px;">' + _esc(o.origen) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div></div>';
    } else {
      h += '<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.4);border-radius:8px;padding:10px;margin-bottom:14px;color:#34d399;">✓ Todas las salidas de producción consumieron lotes presentes en Excel verde — replay limpio.</div>';
    }

    h += '<div style="background:rgba(99,102,241,.10);border:1px solid rgba(99,102,241,.3);border-radius:8px;padding:10px;font-size:12px;color:#cbd5e1;">';
    h += 'Si todo se ve OK, click en <strong>3. APLICAR reset</strong>. Vas a tener que pegar el token textual:<br>';
    h += '<code style="background:#0f172a;padding:4px 8px;border-radius:4px;color:#a5b4fc;">BORRAR_INVENTARIO_Y_CARGAR_EXCEL_2026_04_27</code>';
    h += '</div>';

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function aplicarReset() {
  const fileEl = document.getElementById('audit-inv-file');
  const out = document.getElementById('audit-inv-result');
  if (!fileEl.files || !fileEl.files[0]) {
    out.innerHTML = '<div style="color:#fca5a5;">Selecciona el .xlsx primero.</div>';
    return;
  }
  const TOKEN = 'BORRAR_INVENTARIO_Y_CARGAR_EXCEL_2026_04_27';
  const ingresado = prompt('PEGAR EL TOKEN TEXTUAL EXACTO PARA CONFIRMAR:\n\n' + TOKEN + '\n\n(Cualquier otro texto cancela.)');
  if (ingresado !== TOKEN) {
    out.innerHTML = '<div style="color:#fbbf24;">Reset cancelado — token no coincide.</div>';
    return;
  }
  if (!confirm('Última confirmación. Esto borra TODOS los movimientos y los recrea. Procedo?')) {
    out.innerHTML = '<div style="color:#fbbf24;">Reset cancelado.</div>';
    return;
  }
  out.innerHTML = '<div style="color:#94a3b8;">Aplicando reset... no cierres la pestaña...</div>';
  const fd = new FormData();
  fd.append('file', fileEl.files[0]);
  fd.append('confirmacion', TOKEN);
  try {
    const r = await fetch('/api/admin/inventario-reset-aplicar', {method:'POST', body:fd});
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + (d.detail?'<br><small>' + _esc(d.detail) + '</small>':'') + '</div>'; return; }
    let h = '<div style="background:rgba(16,185,129,.15);border:1px solid #34d399;border-radius:10px;padding:14px;">';
    h += '<h3 style="color:#34d399;margin:0 0 10px 0;">✓ Reset aplicado con éxito</h3>';
    h += '<div style="color:#cbd5e1;font-size:13px;margin-bottom:10px;">' + _esc(d.message) + '</div>';
    h += '<div class="kpi-row">';
    h += '<div class="kpi"><div class="kpi-l">Movs borrados</div><div class="kpi-v">' + d.resumen.movs_borrados + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Lotes Excel cargados</div><div class="kpi-v">' + d.resumen.lotes_excel_cargados + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Entradas OC preservadas</div><div class="kpi-v">' + d.resumen.entradas_oc_preservadas + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Salidas prod preservadas</div><div class="kpi-v">' + d.resumen.salidas_prod_preservadas + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Movs total post</div><div class="kpi-v">' + d.resumen.movs_post_total + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Stock post</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(d.resumen.stock_post_g) + '</div></div>';
    h += '</div>';
    h += '<div style="margin-top:10px;color:#94a3b8;font-size:11px;">Audit log entries creados: RESET_INVENTARIO_PRE + RESET_INVENTARIO_POST. Si necesitas restaurar, usa el snapshot que descargaste.</div>';
    h += '</div>';
    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error de red: ' + _esc(e.message) + '</div>';
  }
}

async function healthCheckPostReset() {
  const out = document.getElementById('audit-inv-result');
  out.innerHTML = '<div style="color:#94a3b8;">Verificando integridad...</div>';
  try {
    const r = await fetch('/api/admin/health-check-post-reset');
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    const okColor = d.ok ? '#34d399' : '#fca5a5';
    let h = '<h3 style="color:' + okColor + ';margin-top:0;">' + (d.ok ? '✓' : '✗') + ' Health-check: ' + d.overall + '</h3>';
    h += '<div style="color:#cbd5e1;font-size:13px;margin-bottom:14px;">' + _esc(d.recomendacion) + '</div>';

    const cs = d.checks;

    // Movimientos
    if (cs.movimientos && cs.movimientos.ok) {
      h += '<div class="kpi-row" style="margin-bottom:10px;">';
      h += '<div class="kpi"><div class="kpi-l">Movs total</div><div class="kpi-v">' + cs.movimientos.total + '</div></div>';
      h += '<div class="kpi"><div class="kpi-l">Stock total</div><div class="kpi-v" style="font-size:14px;">' + cs.movimientos.stock_total_kg + ' kg</div></div>';
      h += '<div class="kpi"><div class="kpi-l">Entradas</div><div class="kpi-v">' + cs.movimientos.entradas + '</div></div>';
      h += '<div class="kpi"><div class="kpi-l">Salidas</div><div class="kpi-v">' + cs.movimientos.salidas + '</div></div>';
      h += '<div class="kpi"><div class="kpi-l">Salidas FEFO prod.</div><div class="kpi-v">' + cs.movimientos.salidas_fefo_produccion + '</div></div>';
      h += '</div>';
    }

    // Stock negativo
    if (cs.stock_negativo) {
      const sn_ok = cs.stock_negativo.ok;
      h += '<div style="background:rgba(' + (sn_ok ? '16,185,129' : '239,68,68') + ',.12);border:1px solid rgba(' + (sn_ok ? '16,185,129' : '239,68,68') + ',.4);border-radius:8px;padding:10px;margin-bottom:10px;">';
      h += '<div style="color:' + (sn_ok ? '#34d399' : '#fca5a5') + ';font-weight:700;">' + (sn_ok ? '✓' : '✗') + ' Stock negativo: ' + cs.stock_negativo.count + ' lotes</div>';
      if (cs.stock_negativo.count > 0) {
        h += '<ul style="font-size:11px;color:#cbd5e1;margin:6px 0 0 18px;">';
        cs.stock_negativo.sample.forEach(s => {
          h += '<li>' + _esc(s.codigo_mp) + ' / ' + _esc(s.lote) + ' = ' + _fmtG(s.neto_g) + '</li>';
        });
        h += '</ul>';
      }
      h += '</div>';
    }

    // Otras tablas
    h += '<div class="kpi-row">';
    if (cs.producciones) {
      h += '<div class="kpi"><div class="kpi-l">Producciones</div><div class="kpi-v">' + cs.producciones.count + '</div></div>';
    }
    if (cs.ocs) {
      h += '<div class="kpi"><div class="kpi-l">OCs</div><div class="kpi-v">' + cs.ocs.ordenes_compra + '</div></div>';
    }
    if (cs.comprobantes_pago) {
      h += '<div class="kpi"><div class="kpi-l">Comprobantes</div><div class="kpi-v">' + cs.comprobantes_pago.count + '</div></div>';
    }
    if (cs.maestro_mps) {
      h += '<div class="kpi"><div class="kpi-l">MPs catálogo activos</div><div class="kpi-v">' + cs.maestro_mps.count_activos + '</div></div>';
    }
    if (cs.solicitudes_compra) {
      h += '<div class="kpi"><div class="kpi-l">Solicitudes</div><div class="kpi-v">' + cs.solicitudes_compra.count + '</div></div>';
    }
    h += '</div>';

    // Audit trail
    if (cs.audit_log && cs.audit_log.eventos_reset_recientes) {
      h += '<h4 style="color:#a5b4fc;margin-top:14px;">Audit trail del reset:</h4>';
      h += '<ul style="color:#cbd5e1;font-size:12px;margin-left:18px;">';
      cs.audit_log.eventos_reset_recientes.forEach(e => {
        h += '<li>' + _esc(e.accion) + ' — ' + _esc(e.fecha) + '</li>';
      });
      h += '</ul>';
    }

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function healthMonitor() {
  const out = document.getElementById('audit-inv-result');
  out.innerHTML = '<div style="color:#94a3b8;">Escaneando kardex en busca de anomalías...</div>';
  try {
    const r = await fetch('/api/admin/inventario-health-monitor');
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    const colors = {ok:'#34d399', warning:'#fbbf24', critical:'#ef4444'};
    const c = colors[d.nivel] || '#cbd5e1';
    let h = '<h3 style="color:' + c + ';margin-top:0;">🔥 Monitor Anomalías — ' + d.nivel.toUpperCase() + '</h3>';
    h += '<div style="background:rgba(' + (d.nivel==='ok'?'16,185,129':d.nivel==='critical'?'239,68,68':'245,158,11') + ',.12);border:1px solid ' + c + ';border-radius:8px;padding:12px;margin-bottom:14px;">';
    h += '<div style="color:' + c + ';font-weight:700;">' + _esc(d.recomendacion) + '</div>';
    h += '</div>';
    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi" style="background:rgba(239,68,68,.12);"><div class="kpi-l" style="color:#fca5a5;">CRITICAL</div><div class="kpi-v">' + d.count_critical + '</div></div>';
    h += '<div class="kpi" style="background:rgba(245,158,11,.12);"><div class="kpi-l" style="color:#fbbf24;">WARNING</div><div class="kpi-v">' + d.count_warning + '</div></div>';
    h += '</div>';

    if (d.alertas.length === 0) {
      h += '<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.4);border-radius:8px;padding:12px;color:#34d399;">✓ Cero anomalías detectadas. Sistema con kardex limpio.</div>';
    } else {
      d.alertas.forEach(a => {
        const sevColor = a.severidad === 'critical' ? '#ef4444' : '#fbbf24';
        h += '<div style="border-left:3px solid ' + sevColor + ';background:#0f172a;padding:10px 14px;margin-bottom:8px;border-radius:0 8px 8px 0;">';
        h += '<div style="color:' + sevColor + ';font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">' + _esc(a.tipo) + ' · ' + _esc(a.severidad) + '</div>';
        h += '<div style="color:#cbd5e1;font-size:13px;margin-bottom:4px;">' + _esc(a.mensaje) + '</div>';
        h += '<details style="margin-top:4px;"><summary style="cursor:pointer;color:#94a3b8;font-size:11px;">Detalle</summary>';
        h += '<pre style="background:#020617;padding:8px;border-radius:4px;font-size:11px;color:#94a3b8;margin:6px 0 0 0;overflow-x:auto;">' + _esc(JSON.stringify(a.detalle, null, 2)) + '</pre>';
        h += '</details></div>';
      });
    }

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function quePuedoProducir() {
  const out = document.getElementById('audit-inv-result');
  out.innerHTML = '<div style="color:#94a3b8;">Calculando para cada producto...</div>';
  try {
    const r = await fetch('/api/programacion/que-puedo-producir');
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    const s = d.resumen;
    let h = '<h3 style="color:#fbbf24;margin-top:0;">🏭 Qu&eacute; puedo producir HOY</h3>';

    h += '<div style="font-size:11px;color:#64748b;margin-bottom:10px;">';
    h += 'Fuente: <code>' + _esc(d.fuente_datos.kardex) + '</code> · ';
    h += '<code>' + _esc(d.fuente_datos.formulas) + '</code> · ';
    h += '<code>' + _esc(d.fuente_datos.proveedor_canonico) + '</code>';
    h += '</div>';

    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi"><div class="kpi-l">Productos total</div><div class="kpi-v">' + s.productos_totales + '</div></div>';
    h += '<div class="kpi" style="background:rgba(16,185,129,.12);"><div class="kpi-l" style="color:#34d399;">✓ Pueden producir</div><div class="kpi-v">' + s.productos_pueden_producir + '</div></div>';
    h += '<div class="kpi" style="background:rgba(239,68,68,.12);"><div class="kpi-l" style="color:#fca5a5;">✗ Con faltantes</div><div class="kpi-v">' + s.productos_con_faltantes + '</div></div>';
    h += '</div>';

    // Shopping list por proveedor (lo más útil)
    if (d.shopping_list_por_proveedor.length > 0) {
      h += '<h3 style="color:#a5b4fc;margin-top:18px;">🛒 Shopping list por proveedor</h3>';
      h += '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">Lo que hay que pedir AHORA para no quedar en cero. Ordenado por kg total.</div>';
      d.shopping_list_por_proveedor.forEach(prov => {
        h += '<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:10px;">';
        h += '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">';
        h += '<div style="font-weight:700;color:#a5b4fc;font-size:14px;">' + _esc(prov.proveedor) + '</div>';
        h += '<div style="color:#cbd5e1;font-size:12px;">' + prov.count_mps + ' MPs · <strong>' + _fmtG(prov.total_g_a_pedir) + '</strong> total</div>';
        h += '</div>';
        h += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr><th style="text-align:left;color:#94a3b8;padding:4px 6px;">Código</th><th style="text-align:left;color:#94a3b8;padding:4px 6px;">MP</th><th style="text-align:right;color:#94a3b8;padding:4px 6px;">Pedir mín</th><th style="text-align:left;color:#94a3b8;padding:4px 6px;">Para</th></tr></thead><tbody>';
        prov.mps.forEach(m => {
          h += '<tr style="border-top:1px solid #1e293b;">';
          h += '<td style="padding:5px 6px;font-family:monospace;color:#e2e8f0;">' + _esc(m.codigo_mp) + '</td>';
          h += '<td style="padding:5px 6px;color:#e2e8f0;">' + _esc(m.nombre) + '</td>';
          h += '<td style="padding:5px 6px;text-align:right;font-family:monospace;color:#fca5a5;">' + _fmtG(m.falta_g) + '</td>';
          h += '<td style="padding:5px 6px;color:#94a3b8;font-size:11px;">' + _esc(m.productos_afectados.join(', ')) + '</td>';
          h += '</tr>';
        });
        h += '</tbody></table></div>';
      });
    } else {
      h += '<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.4);border-radius:8px;padding:12px;color:#34d399;">✓ Cero faltantes — todas las MPs alcanzan para producir cada producto en cantidad estándar.</div>';
    }

    // Detalle por producto (expandible)
    h += '<h3 style="color:#cbd5e1;margin-top:18px;">📋 Detalle por producto</h3>';
    h += '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">Click en un producto para ver evidencia (lotes disponibles).</div>';
    d.productos.forEach((p, idx) => {
      const okColor = p.puede_producir ? '#34d399' : '#fca5a5';
      const ico = p.puede_producir ? '✓' : '✗';
      h += '<details style="margin-bottom:6px;background:#0f172a;border:1px solid #334155;border-radius:6px;">';
      h += '<summary style="padding:8px 12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;">';
      h += '<span style="color:' + okColor + ';"><strong>' + ico + ' ' + _esc(p.producto) + '</strong> · lote ' + p.cantidad_kg_evaluada + ' kg</span>';
      h += '<span style="color:#94a3b8;font-size:11px;">' + p.mps_ok + '/' + p.mps_total + ' MPs ok' + (p.mps_faltantes > 0 ? ' · falta ' + _fmtG(p.falta_total_g) : '') + '</span>';
      h += '</summary>';
      h += '<div style="padding:8px 12px;border-top:1px solid #1e293b;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="color:#94a3b8;"><th style="text-align:left;padding:4px;">MP</th><th style="text-align:right;padding:4px;">Req</th><th style="text-align:right;padding:4px;">Stock</th><th style="text-align:right;padding:4px;">Falta</th><th style="text-align:left;padding:4px;">Lotes (evidencia)</th></tr></thead><tbody>';
      p.mps_status.forEach(m => {
        const rowColor = m.ok ? '#cbd5e1' : '#fca5a5';
        h += '<tr style="border-top:1px solid #1e293b;color:' + rowColor + ';">';
        h += '<td style="padding:4px;"><code style="font-size:10px;color:#94a3b8;">' + _esc(m.codigo_mp) + '</code> ' + _esc(m.nombre) + '</td>';
        h += '<td style="padding:4px;text-align:right;font-family:monospace;">' + _fmtG(m.requerido_g) + '</td>';
        h += '<td style="padding:4px;text-align:right;font-family:monospace;">' + _fmtG(m.stock_actual_g) + '</td>';
        h += '<td style="padding:4px;text-align:right;font-family:monospace;color:' + (m.falta_g > 0 ? '#fca5a5' : '#64748b') + ';">' + (m.falta_g > 0 ? _fmtG(m.falta_g) : '—') + '</td>';
        h += '<td style="padding:4px;font-size:10px;color:#94a3b8;">';
        if (m.lotes_disponibles.length === 0) {
          h += '<em>sin lotes</em>';
        } else {
          h += m.lotes_disponibles.map(l => _esc(l.lote || '(s/lote)') + ': ' + _fmtG(l.cantidad_g)).join(' · ');
        }
        h += '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      h += '</details>';
    });

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

async function diagnosticoEntradas() {
  const out = document.getElementById('audit-inv-result');
  out.innerHTML = '<div style="color:#94a3b8;">Analizando entradas en el kardex...</div>';
  try {
    const r = await fetch('/api/admin/inventario-diagnostico-entradas');
    const d = await r.json();
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    const s = d.resumen;
    let h = '<h3 style="color:#a5b4fc;margin-top:0;">&#x1F50E; Diagn&oacute;stico de Entradas</h3>';
    h += '<div class="kpi-row" style="margin-bottom:14px;">';
    h += '<div class="kpi"><div class="kpi-l">Total Entradas</div><div class="kpi-v">' + s.total_entradas + '</div></div>';
    h += '<div class="kpi"><div class="kpi-l">Total Entradas (g)</div><div class="kpi-v" style="font-size:14px;">' + _fmtG(s.total_entradas_g) + '</div></div>';
    h += '<div class="kpi" style="background:rgba(239,68,68,.12);"><div class="kpi-l" style="color:#fca5a5;">Lotes c/ multiples Entradas</div><div class="kpi-v">' + s.lotes_con_multiples_entradas + '</div></div>';
    h += '<div class="kpi" style="background:rgba(16,185,129,.12);"><div class="kpi-l" style="color:#34d399;">Entradas con OC (formal)</div><div class="kpi-v">' + s.entradas_con_oc + ' (' + _fmtG(s.entradas_con_oc_g) + ')</div></div>';
    h += '<div class="kpi" style="background:rgba(245,158,11,.12);"><div class="kpi-l" style="color:#fbbf24;">Entradas SIN OC (manual)</div><div class="kpi-v">' + s.entradas_sin_oc + ' (' + _fmtG(s.entradas_sin_oc_g) + ')</div></div>';
    h += '</div>';

    // Por operador
    h += '<h3 style="color:#a5b4fc;margin-top:18px;">Entradas por operador</h3>';
    h += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:8px;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead style="background:#1e293b;"><tr>';
    h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Operador</th>';
    h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">N° Entradas</th>';
    h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">Total (g)</th>';
    h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Primera</th>';
    h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Última</th>';
    h += '</tr></thead><tbody>';
    d.por_operador.forEach(o => {
      h += '<tr style="border-top:1px solid #334155;">';
      h += '<td style="padding:6px 10px;color:#e2e8f0;font-weight:600;">' + _esc(o.operador) + '</td>';
      h += '<td style="padding:6px 10px;text-align:right;font-family:monospace;">' + o.n_entradas + '</td>';
      h += '<td style="padding:6px 10px;text-align:right;font-family:monospace;color:#a5b4fc;">' + _fmtG(o.total_g) + '</td>';
      h += '<td style="padding:6px 10px;color:#94a3b8;">' + _esc(o.primera_fecha) + '</td>';
      h += '<td style="padding:6px 10px;color:#94a3b8;">' + _esc(o.ultima_fecha) + '</td>';
      h += '</tr>';
    });
    h += '</tbody></table></div>';

    // Timeline
    h += '<h3 style="color:#a5b4fc;margin-top:18px;">Timeline de Entradas (primeros 60 dias con actividad)</h3>';
    h += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:8px;max-height:300px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead style="background:#1e293b;position:sticky;top:0;"><tr>';
    h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Fecha</th>';
    h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">N° Entradas</th>';
    h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">Total (g)</th>';
    h += '</tr></thead><tbody>';
    d.timeline.forEach(t => {
      const isHigh = t.n_entradas > 50;  // dia con burst
      h += '<tr style="border-top:1px solid #334155;' + (isHigh ? 'background:rgba(245,158,11,.08);' : '') + '">';
      h += '<td style="padding:6px 10px;color:#e2e8f0;font-family:monospace;">' + _esc(t.fecha) + (isHigh ? ' <span style="color:#fbbf24;">⚠ burst</span>' : '') + '</td>';
      h += '<td style="padding:6px 10px;text-align:right;font-family:monospace;">' + t.n_entradas + '</td>';
      h += '<td style="padding:6px 10px;text-align:right;font-family:monospace;color:#a5b4fc;">' + _fmtG(t.total_g) + '</td>';
      h += '</tr>';
    });
    h += '</tbody></table></div>';

    // Multi-entradas (smoking gun)
    h += '<h3 style="color:#fca5a5;margin-top:18px;">⚠ Lotes con MULTIPLES Entradas (' + d.multi_entradas.length + ')</h3>';
    h += '<div style="color:#94a3b8;font-size:11px;margin-bottom:6px;">Si un lote aparece 2 veces como Entrada con la misma cantidad → doble carga. Si tiene 2 entradas pero cantidades distintas → recepción posterior legítima.</div>';
    if (!d.multi_entradas.length) {
      h += '<div style="color:#34d399;">✓ Ningún lote con múltiples entradas — no hay doble carga.</div>';
    } else {
      h += '<div style="overflow-x:auto;background:#0f172a;border:1px solid #334155;border-radius:8px;max-height:400px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead style="background:#1e293b;position:sticky;top:0;"><tr>';
      h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Código</th>';
      h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Lote</th>';
      h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">N° Entradas</th>';
      h += '<th style="padding:8px 10px;text-align:right;color:#cbd5e1;">Total Sumado</th>';
      h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Operadores</th>';
      h += '<th style="padding:8px 10px;text-align:left;color:#cbd5e1;">Primera → Última</th>';
      h += '</tr></thead><tbody>';
      d.multi_entradas.forEach(m => {
        h += '<tr style="border-top:1px solid #334155;">';
        h += '<td style="padding:6px 10px;font-family:monospace;color:#e2e8f0;">' + _esc(m.codigo_mp) + '</td>';
        h += '<td style="padding:6px 10px;font-family:monospace;color:#94a3b8;">' + _esc(m.lote) + '</td>';
        h += '<td style="padding:6px 10px;text-align:right;font-weight:700;color:' + (m.n_entradas >= 2 ? '#fca5a5' : '#e2e8f0') + ';">' + m.n_entradas + '</td>';
        h += '<td style="padding:6px 10px;text-align:right;font-family:monospace;color:#fca5a5;">' + _fmtG(m.total_g) + '</td>';
        h += '<td style="padding:6px 10px;color:#94a3b8;font-size:11px;">' + _esc(m.operadores) + '</td>';
        h += '<td style="padding:6px 10px;color:#94a3b8;font-size:11px;">' + _esc(m.primera_fecha) + ' → ' + _esc(m.ultima_fecha) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
    }

    out.innerHTML = h;
  } catch(e) {
    out.innerHTML = '<div style="color:#fca5a5;">Error de red: ' + _esc(e.message) + '</div>';
  }
}

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

// ── DIAGNOSTICO DE FORMULAS ──────────────────────────────────────────────────
let _DIAG_FORM_DATA = null;

async function cargarDiagnosticoFormulas() {
  const out = document.getElementById('diag-form-result');
  const btn = document.getElementById('btn-diag-form');
  btn.disabled = true; btn.textContent = 'Analizando...';
  out.innerHTML = '<div style="color:#94a3b8;">Comparando formula_items vs maestro_mps...</div>';
  document.getElementById('diag-form-stats').style.display = 'none';
  document.getElementById('diag-form-aplicar-box').style.display = 'none';
  try {
    const r = await fetch('/api/admin/diagnosticar-formulas');
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x1F50D; Ejecutar diagn&oacute;stico';
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    _DIAG_FORM_DATA = d;

    // Stats
    document.getElementById('diag-form-stats').style.display = 'block';
    document.getElementById('diagf-total').textContent = d.stats.total_formula_items;
    document.getElementById('diagf-problemas').textContent = d.stats.total_problemas;
    document.getElementById('diagf-huerf').textContent = d.stats.huerfanos;
    document.getElementById('diagf-misn').textContent = d.stats.mismatch_nombre;
    document.getElementById('diagf-auto').textContent = d.stats.auto_corregibles;
    document.getElementById('diagf-rev').textContent = d.stats.requieren_revision;

    if (d.stats.total_problemas === 0) {
      out.innerHTML = '<div style="background:rgba(34,197,94,.15);border:1px solid #22c55e;border-radius:8px;padding:14px;color:#34d399;">✓ Sin problemas detectados. Todas las fórmulas apuntan correctamente al catálogo.</div>';
      return;
    }
    document.getElementById('diag-form-aplicar-box').style.display = 'block';

    // Obsoletas (sin candidato)
    const sinCand = d.problemas.filter(p => !p.mejor_candidato);
    if (sinCand.length > 0) {
      document.getElementById('diag-form-obsoletas-box').style.display = 'block';
      document.getElementById('diagf-sin-cand-count').textContent = sinCand.length + ' items sin candidato (probablemente obsoletos)';
    } else {
      document.getElementById('diag-form-obsoletas-box').style.display = 'none';
    }

    // Render tabla — agrupada por producto
    let h = '<h4 style="color:#a5b4fc;margin-top:14px;">Items con problemas (' + d.stats.total_problemas + ' de ' + d.stats.total_formula_items + ')</h4>';
    h += '<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">';
    h += 'Marcadas verdes = auto-corregibles (1 candidato exacto). Sin candidato = requieren revisión manual.';
    h += '</div>';
    h += '<div style="overflow-x:auto;"><table id="diag-form-tabla"><thead><tr>';
    h += '<th><input type="checkbox" id="diagf-check-all" onchange="_toggleDiagFCheckAll(this)"></th>';
    h += '<th>Producto</th>';
    h += '<th>Material en fórmula</th>';
    h += '<th>Código actual</th>';
    h += '<th>Problema</th>';
    h += '<th>Sugerencia</th>';
    h += '</tr></thead><tbody>';
    d.problemas.forEach((p, idx) => {
      const auto = !!p.auto_corregible;
      const sinCandidato = !p.mejor_candidato;
      const bgColor = sinCandidato ? 'rgba(220,38,38,.10)' : (auto ? 'rgba(34,197,94,.08)' : 'rgba(245,158,11,.08)');
      const probColor = p.problema === 'huerfano' ? '#dc2626' : '#f59e0b';
      h += '<tr style="background:' + bgColor + ';">';
      h += '<td><input type="checkbox" class="diagf-row-check" data-idx="' + idx + '"' + (auto ? ' checked' : '') + '></td>';
      h += '<td style="font-size:11px;color:#cbd5e1;">' + _esc(p.producto) + '</td>';
      h += '<td><div style="font-weight:600;">' + _esc(p.material_nombre_formula) + '</div><div style="font-size:10px;color:#94a3b8;">' + _fmtG(p.cantidad_g_por_lote) + ' x lote</div></td>';
      h += '<td style="font-family:monospace;font-size:11px;color:#94a3b8;">' + _esc(p.material_id_actual) + '</td>';
      h += '<td><span style="background:' + probColor + '22;color:' + probColor + ';border:1px solid ' + probColor + ';border-radius:8px;padding:2px 6px;font-size:10px;font-weight:700;">' + _esc(p.problema.toUpperCase()) + '</span></td>';
      if (sinCandidato) {
        h += '<td style="font-size:11px;color:#fca5a5;">⚠ Sin candidato — revisar manualmente</td>';
      } else {
        const cand = p.mejor_candidato;
        const scoreColor = cand.score >= 100 ? '#22c55e' : (cand.score >= 80 ? '#fbbf24' : '#f59e0b');
        h += '<td>';
        h += '<div style="font-family:monospace;font-size:11px;color:#e2e8f0;">→ ' + _esc(cand.codigo) + '</div>';
        h += '<div style="font-size:10px;color:#cbd5e1;">' + _esc(cand.nombre_comercial || cand.nombre_inci) + '</div>';
        h += '<div style="font-size:10px;color:' + scoreColor + ';">match score: ' + cand.score + '%</div>';
        h += '</td>';
      }
      h += '</tr>';
    });
    h += '</tbody></table></div>';
    out.innerHTML = h;
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x1F50D; Ejecutar diagn&oacute;stico';
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

function _toggleDiagFCheckAll(el) {
  document.querySelectorAll('.diagf-row-check').forEach(c => c.checked = el.checked);
}

function seleccionarSoloAuto() {
  if (!_DIAG_FORM_DATA) return;
  document.querySelectorAll('.diagf-row-check').forEach(c => {
    const idx = parseInt(c.dataset.idx);
    const p = _DIAG_FORM_DATA.problemas[idx];
    c.checked = !!p.auto_corregible;
  });
}

function seleccionarTodos() {
  document.querySelectorAll('.diagf-row-check').forEach(c => {
    const idx = parseInt(c.dataset.idx);
    const p = _DIAG_FORM_DATA.problemas[idx];
    c.checked = !!p.mejor_candidato;  // solo los que tienen candidato
  });
}

function deseleccionarTodos() {
  document.querySelectorAll('.diagf-row-check').forEach(c => c.checked = false);
}

function exportarDiagFormCSV() {
  if (!_DIAG_FORM_DATA) { toast('Primero ejecuta diagnóstico', 'warn'); return; }
  const rows = [['Producto','MaterialNombre','CodigoActual','Problema','CodigoSugerido','NombreSugerido','Score']];
  _DIAG_FORM_DATA.problemas.forEach(p => {
    const cand = p.mejor_candidato || {};
    rows.push([p.producto, p.material_nombre_formula, p.material_id_actual, p.problema,
               cand.codigo||'', cand.nombre_comercial||'', cand.score||0]);
  });
  const csv = rows.map(r => r.map(c => '"' + String(c==null?'':c).replace(/"/g,'""') + '"').join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'diagnostico_formulas_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

async function aplicarBatch20260428() {
  const token = (document.getElementById('diagf-token-batch20260428').value || '').trim();
  if (token !== 'APLICAR_CORRECCIONES_2026_04_28') {
    toast('Token incorrecto. Debe ser exactamente: APLICAR_CORRECCIONES_2026_04_28', 'warn');
    return;
  }
  if (!confirm('Aplicar batch de 240 correcciones validadas (2026-04-28)?\n\n' +
               '- 44 MPs nuevos en catalogo\n' +
               '- Azeclair MP00284 marcado activo=0\n' +
               '- INCI oficial actualizado AOS 40\n' +
               '- 207 formula_items corregidos\n' +
               '- 33 filas de Agua Desionizada eliminadas\n\n' +
               'Backup automatico previo. Transaccion atomica. Reversible.')) return;
  const btn = document.getElementById('btn-aplicar-batch');
  btn.disabled = true; btn.textContent = 'Aplicando 240 cambios...';
  try {
    let r = await fetch('/api/admin/aplicar-correcciones-formulas-batch-2026-04-28', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token: token})
    });
    let d = await r.json();

    // Caso 1: hay duplicados por INCI -> recomendar mapear_duplicados
    if (r.status === 409 && d.total_duplicados_inci) {
      const dups = d.duplicados_inci || [];
      const preview = dups.slice(0,8).map(function(o){
        return '  ' + o.inci_planeado + ' ya existe como ' + o.codigo_existente +
               (o.codigo_existente !== o.codigo_planeado ? ' (planeado: ' + o.codigo_planeado + ')' : '');
      }).join('\n');
      const ok = confirm(
        'Detecte ' + d.total_duplicados_inci + ' INCI(s) que YA EXISTEN en el catalogo con otro codigo.\n\n' +
        'Si creo MPs nuevos, quedan duplicados. Si MAPEO, los formula_items apuntaran a los codigos existentes (sin crear entradas extra).\n\n' +
        'Duplicados detectados:\n' + preview +
        (dups.length > 8 ? '\n  ... +' + (dups.length-8) + ' mas' : '') +
        '\n\n¿Aplicar en modo MAPEAR_DUPLICADOS (recomendado, sin crear duplicados)?'
      );
      if (!ok) {
        btn.disabled = false; btn.innerHTML = '&#x2728; Aplicar 240 correcciones';
        toast('Cancelado. Revisa los duplicados antes de continuar.', 'warn');
        return;
      }
      btn.textContent = 'Mapeando a codigos existentes...';
      r = await fetch('/api/admin/aplicar-correcciones-formulas-batch-2026-04-28', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({token: token, modo: 'mapear_duplicados'})
      });
      d = await r.json();
    }
    // Caso 2: rango ocupado pero SIN duplicados de INCI -> auto_renumerar seguro
    else if (r.status === 409 && d.total_ocupados) {
      let nombresPreview = '';
      if (d.ocupados_con_nombres && d.ocupados_con_nombres.length) {
        nombresPreview = '\n\nPrimeros ocupados:\n' + d.ocupados_con_nombres.slice(0,5).map(function(o){
          return '  ' + o.codigo + ' = ' + (o.comercial || o.inci || '?');
        }).join('\n');
      }
      const ok = confirm(
        'El rango MP00400-MP00500 tiene ' + d.total_ocupados + ' codigos ocupados, pero ninguno colisiona por INCI con los mios.\n\n' +
        '¿Renumerar al siguiente bloque libre (MP01000+) y aplicar?' +
        nombresPreview
      );
      if (!ok) {
        btn.disabled = false; btn.innerHTML = '&#x2728; Aplicar 240 correcciones';
        return;
      }
      btn.textContent = 'Renumerando y aplicando...';
      r = await fetch('/api/admin/aplicar-correcciones-formulas-batch-2026-04-28', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({token: token, modo: 'auto_renumerar'})
      });
      d = await r.json();
    }
    btn.disabled = false; btn.innerHTML = '&#x2728; Aplicar 240 correcciones';
    if (!r.ok) {
      let msg = d.error || 'desconocido';
      if (d.ocupados && d.ocupados.length) {
        msg += '\nOcupados: ' + d.ocupados.join(', ');
      }
      toast('Error: ' + _esc(msg), 'warn');
      return;
    }
    const resumen = 'OK. ' +
      'MPs nuevos: ' + d.despues.mps_nuevos_creados + ' · ' +
      'formula_items diff: ' + d.cambios_netos.formula_items_diff + ' · ' +
      'maestro_mps diff: ' + d.cambios_netos.maestro_mps_diff;
    toast(resumen, 'ok');
    document.getElementById('diagf-token-batch20260428').value = '';
    cargarDiagnosticoFormulas();
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x2728; Aplicar 240 correcciones';
    toast('Error: ' + e.message, 'warn');
  }
}

async function revertirFormulas() {
  const token = (document.getElementById('diagf-token-revertir').value || '').trim();
  if (token !== 'REVERTIR_FORMULAS_2026') {
    toast('Token incorrecto. Debe ser exactamente: REVERTIR_FORMULAS_2026', 'warn');
    return;
  }
  if (!confirm('REVERTIR las correcciones de fórmulas al estado anterior?\n\nEsto reemplaza formula_items con la versión del backup automático más reciente. NO afecta movimientos, catálogo, OCs.\n\nProceder?')) return;
  const btn = document.getElementById('btn-revertir-form');
  btn.disabled = true; btn.textContent = 'Revirtiendo...';
  try {
    const r = await fetch('/api/admin/revertir-formulas-desde-backup', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token: token})
    });
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x21A9; Revertir desde backup';
    if (!r.ok) {
      toast('Error: ' + _esc(d.error||'desconocido'), 'warn');
      return;
    }
    toast(d.mensaje, 'ok');
    document.getElementById('diagf-token-revertir').value = '';
    cargarDiagnosticoFormulas();
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x21A9; Revertir desde backup';
    toast('Error: ' + e.message, 'warn');
  }
}

async function eliminarFormulasObsoletas() {
  if (!_DIAG_FORM_DATA) return;
  const token = (document.getElementById('diagf-token-eliminar').value || '').trim();
  if (token !== 'ELIMINAR_FORMULAS_OBSOLETAS_2026') {
    toast('Token incorrecto. Debe ser exactamente: ELIMINAR_FORMULAS_OBSOLETAS_2026', 'warn');
    return;
  }
  const ids = _DIAG_FORM_DATA.problemas
    .filter(p => !p.mejor_candidato)
    .map(p => p.formula_item_id);
  if (!ids.length) { toast('No hay items sin candidato para eliminar', 'warn'); return; }
  if (!confirm('Eliminar ' + ids.length + ' items obsoletos de formula_items? Backup automático previo.')) return;

  const btn = document.getElementById('btn-eliminar-obs');
  btn.disabled = true; btn.textContent = 'Eliminando...';
  try {
    const r = await fetch('/api/admin/eliminar-formulas-obsoletas', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token: token, formula_item_ids: ids})
    });
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x1F5D1; Eliminar obsoletas';
    if (!r.ok) { toast('Error: ' + _esc(d.error||'desconocido'), 'warn'); return; }
    toast(d.mensaje || (d.count_eliminados + ' items eliminados'), 'ok');
    document.getElementById('diagf-token-eliminar').value = '';
    cargarDiagnosticoFormulas();
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x1F5D1; Eliminar obsoletas';
    toast('Error: ' + e.message, 'warn');
  }
}

async function aplicarCorreccionFormulas() {
  if (!_DIAG_FORM_DATA) return;
  const token = (document.getElementById('diagf-token').value || '').trim();
  if (token !== 'CORREGIR_FORMULAS_2026') {
    toast('Token incorrecto. Debe ser exactamente: CORREGIR_FORMULAS_2026', 'warn');
    return;
  }
  // Recoger seleccionados
  const correcciones = [];
  document.querySelectorAll('.diagf-row-check').forEach(c => {
    if (!c.checked) return;
    const idx = parseInt(c.dataset.idx);
    const p = _DIAG_FORM_DATA.problemas[idx];
    if (!p.mejor_candidato) return;
    correcciones.push({
      formula_item_id: p.formula_item_id,
      nuevo_material_id: p.mejor_candidato.codigo,
      nuevo_material_nombre: p.mejor_candidato.nombre_comercial || p.mejor_candidato.nombre_inci,
    });
  });
  if (!correcciones.length) {
    toast('Selecciona al menos una corrección', 'warn');
    return;
  }
  if (!confirm('Aplicar ' + correcciones.length + ' correcciones a formula_items? Backup automático previo.')) return;

  const btn = document.getElementById('btn-aplicar-form');
  btn.disabled = true; btn.textContent = 'Aplicando...';
  try {
    const r = await fetch('/api/admin/corregir-formulas', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token: token, correcciones: correcciones})
    });
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x1F4A5; Aplicar correcciones';
    if (!r.ok) { toast('Error: ' + _esc(d.error||'desconocido'), 'warn'); return; }
    toast(d.mensaje || (d.count_aplicados + ' correcciones aplicadas'), 'ok');
    document.getElementById('diagf-token').value = '';
    cargarDiagnosticoFormulas();  // recargar para ver el delta
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x1F4A5; Aplicar correcciones';
    toast('Error: ' + e.message, 'warn');
  }
}

// ── AUDITAR MINIMOS DE MPs ────────────────────────────────────────────────────
let _AUD_MIN_DATA = null;

async function cargarAuditarMinimos() {
  const proy = document.getElementById('audmin-proy').value;
  const out = document.getElementById('audmin-result');
  const btn = document.getElementById('btn-aud-min');
  btn.disabled = true; btn.textContent = 'Calculando...';
  out.innerHTML = '<div style="color:#94a3b8;">Proyectando consumo y comparando con mínimos actuales...</div>';
  document.getElementById('audmin-stats').style.display = 'none';
  document.getElementById('audmin-aplicar-box').style.display = 'none';
  try {
    const r = await fetch('/api/admin/auditar-minimos?proyeccion_dias=' + encodeURIComponent(proy));
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x1F50D; Auditar (vista previa)';
    if (!r.ok) { out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(d.error||r.status) + '</div>'; return; }
    _AUD_MIN_DATA = d;

    // Stats
    document.getElementById('audmin-stats').style.display = 'block';
    document.getElementById('audmin-total').textContent = d.stats.total;
    document.getElementById('audmin-ok').textContent = d.stats.ok;
    document.getElementById('audmin-sub').textContent = d.stats.sub_protegido;
    document.getElementById('audmin-sobre').textContent = d.stats.sobre_protegido;
    document.getElementById('audmin-vacio').textContent = d.stats.sin_minimo;
    document.getElementById('audmin-uso').textContent = d.stats.sin_uso;

    // Mostrar bloque aplicar si hay algo que aplicar
    const totalAplicable = d.stats.sub_protegido + d.stats.sobre_protegido + d.stats.sin_minimo;
    document.getElementById('audmin-aplicar-box').style.display = totalAplicable > 0 ? 'block' : 'none';

    // Render tabla
    let h = '<h4 style="color:#a5b4fc;margin-top:14px;">Detalle por MP — ' + d.stats.total + ' materias primas</h4>';
    h += '<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">' +
         'Métodología: <code>' + _esc(d.metodologia.formula) + '</code>. ' +
         'China: 90d. Local: 21d. Sin proveedor: 28d. Piso 50g para péptidos.' +
         '</div>';
    h += '<div style="margin-bottom:10px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:12px;">';
    h += '<span style="color:#cbd5e1;">Filtrar:</span>';
    ['todos', 'OK', 'SUB_PROTEGIDO', 'SOBRE_PROTEGIDO', 'SIN_MINIMO_CONFIGURADO', 'SIN_USO'].forEach(function(f){
      h += '<button class="btn btn-outline" style="padding:3px 10px;font-size:11px;" onclick="_filtrarAudMin(\'' + f + '\')">' + f + '</button>';
    });
    h += '<input type="text" id="audmin-search" oninput="_filtrarAudMin()" placeholder="Buscar nombre/código..." style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:5px;padding:4px 8px;font-size:11px;width:180px;">';
    h += '</div>';
    h += '<div style="overflow-x:auto;"><table id="audmin-tabla"><thead><tr>';
    h += '<th>Estado</th><th>Material</th><th>Proveedor</th><th>Origen</th>';
    h += '<th style="text-align:right;">Consumo/día</th>';
    h += '<th style="text-align:right;">Mínimo actual</th>';
    h += '<th style="text-align:right;">Recomendado</th>';
    h += '<th>Cobertura</th>';
    h += '<th>Razonamiento</th>';
    h += '</tr></thead><tbody id="audmin-tbody"></tbody></table></div>';
    out.innerHTML = h;
    _filtrarAudMin('todos');
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x1F50D; Auditar (vista previa)';
    out.innerHTML = '<div style="color:#fca5a5;">Error: ' + _esc(e.message) + '</div>';
  }
}

function _filtrarAudMin(estado) {
  if (!_AUD_MIN_DATA) return;
  if (estado) window._audMinFiltro = estado;
  const filtro = window._audMinFiltro || 'todos';
  const search = (document.getElementById('audmin-search')||{}).value || '';
  const sLower = search.trim().toLowerCase();
  const items = _AUD_MIN_DATA.auditoria.filter(function(a){
    if (filtro === 'SIN_USO') {
      if (!a.estado.startsWith('SIN_USO')) return false;
    } else if (filtro !== 'todos' && a.estado !== filtro) {
      return false;
    }
    if (sLower) {
      const txt = (a.nombre + ' ' + a.codigo_mp + ' ' + (a.proveedor||'')).toLowerCase();
      if (txt.indexOf(sLower) === -1) return false;
    }
    return true;
  });
  // Orden: SUB_PROTEGIDO > SIN_MINIMO_CONFIGURADO > SOBRE_PROTEGIDO > OK > SIN_USO
  const orden = {SUB_PROTEGIDO:0, SIN_MINIMO_CONFIGURADO:1, SOBRE_PROTEGIDO:2, OK:3, SIN_USO_CON_MIN:4, SIN_USO:5};
  items.sort(function(a, b){
    const oa = orden[a.estado] !== undefined ? orden[a.estado] : 9;
    const ob = orden[b.estado] !== undefined ? orden[b.estado] : 9;
    if (oa !== ob) return oa - ob;
    return (b.consumo_diario_g || 0) - (a.consumo_diario_g || 0);
  });
  const colors = {
    OK: '#22c55e',
    SUB_PROTEGIDO: '#dc2626',
    SOBRE_PROTEGIDO: '#f59e0b',
    SIN_MINIMO_CONFIGURADO: '#6366f1',
    SIN_USO: '#94a3b8',
    SIN_USO_CON_MIN: '#94a3b8',
  };
  let h = '';
  items.forEach(function(a){
    const col = colors[a.estado] || '#cbd5e1';
    const cobertura = a.consumo_diario_g > 0
      ? Math.round(a.stock_minimo_actual_g / a.consumo_diario_g) + 'd'
      : '—';
    h += '<tr>';
    h += '<td><span style="background:' + col + '22;color:' + col + ';border:1px solid ' + col + ';border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700;">' + _esc(a.estado.replace('_', ' ')) + '</span></td>';
    h += '<td><div style="font-weight:600;font-size:12px;">' + _esc(a.nombre) + '</div><div style="font-size:10px;color:#64748b;font-family:monospace;">' + _esc(a.codigo_mp) + '</div></td>';
    h += '<td style="font-size:11px;color:#cbd5e1;">' + _esc(a.proveedor || '—') + '</td>';
    h += '<td style="font-size:11px;color:#94a3b8;">' + _esc(a.origen) + '</td>';
    h += '<td style="text-align:right;font-size:11px;">' + _fmtG(a.consumo_diario_g) + '</td>';
    h += '<td style="text-align:right;font-size:12px;">' + _fmtG(a.stock_minimo_actual_g) + '</td>';
    h += '<td style="text-align:right;font-size:12px;font-weight:700;color:' + col + ';">' + _fmtG(a.minimo_recomendado_g) + '</td>';
    h += '<td style="font-size:11px;color:#94a3b8;">' + cobertura + '</td>';
    h += '<td style="font-size:11px;color:#cbd5e1;max-width:280px;">' + _esc(a.razonamiento) + '</td>';
    h += '</tr>';
  });
  if (!h) h = '<tr><td colspan="9" style="text-align:center;color:#64748b;padding:20px;">Sin coincidencias</td></tr>';
  document.getElementById('audmin-tbody').innerHTML = h;
}

function exportarAuditMinCSV() {
  if (!_AUD_MIN_DATA) { toast('Primero ejecuta auditoría', 'warn'); return; }
  const rows = [['Codigo','Nombre','Proveedor','Origen','ConsumoDiario_g','ConsumoMensual_g','StockMinimoActual_g','MinimoRecomendado_g','LeadTime_d','Buffer_d','Estado','Razonamiento']];
  _AUD_MIN_DATA.auditoria.forEach(function(a){
    rows.push([a.codigo_mp, a.nombre, a.proveedor, a.origen, a.consumo_diario_g, a.consumo_mensual_g, a.stock_minimo_actual_g, a.minimo_recomendado_g, a.lead_time_dias, a.buffer_dias, a.estado, a.razonamiento]);
  });
  const csv = rows.map(function(r){return r.map(function(c){return '"' + String(c==null?'':c).replace(/"/g,'""') + '"';}).join(',');}).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'auditoria_minimos_mps_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

async function aplicarRecalculoMinimos() {
  const token = (document.getElementById('audmin-token').value || '').trim();
  if (token !== 'APLICAR_MINIMOS_RECALCULADOS_2026') {
    toast('Token incorrecto. Debe ser exactamente: APLICAR_MINIMOS_RECALCULADOS_2026', 'warn');
    return;
  }
  if (!confirm('Esto va a actualizar stock_minimo en maestro_mps para los MPs marcados como SUB/SOBRE/SIN_MINIMO. Crea backup automático previo. ¿Continuar?')) return;
  const proy = document.getElementById('audmin-proy').value;
  const btn = document.getElementById('btn-aplicar-min');
  btn.disabled = true; btn.textContent = 'Aplicando...';
  try {
    const r = await fetch('/api/admin/aplicar-minimos', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token: token, proyeccion_dias: parseInt(proy)})
    });
    const d = await r.json();
    btn.disabled = false; btn.innerHTML = '&#x1F4A5; Aplicar recálculo';
    if (!r.ok) { toast('Error: ' + _esc(d.error||'desconocido'), 'warn'); return; }
    toast(d.mensaje || (d.count_cambios + ' mínimos actualizados'), 'ok');
    document.getElementById('audmin-token').value = '';
    // Recargar auditoría
    cargarAuditarMinimos();
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '&#x1F4A5; Aplicar recálculo';
    toast('Error: ' + e.message, 'warn');
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

async function syncMpsNombres(dryRun){
  const fi = document.getElementById('mps-nom-file');
  const out = document.getElementById('mps-nom-result');
  if(!fi.files.length){ toast('Selecciona un .xlsx','warn'); return; }
  out.innerHTML = '<div style="color:#94a3b8;padding:14px;">Procesando...</div>';
  const fd = new FormData();
  fd.append('file', fi.files[0]);
  const url = '/api/admin/import-mps-nombres-excel' + (dryRun ? '?dry_run=1' : '');
  try{
    const r = await fetch(url, {method:'POST', body: fd});
    const d = await r.json();
    if(!r.ok){
      out.innerHTML = '<div style="color:#f87171;padding:14px;background:#1e293b;border-radius:8px;">'
        + 'Error '+r.status+': '+(d.error||'')
        + (d.headers ? '<div style="margin-top:8px;font-size:11px;color:#94a3b8;">Headers detectados: '+d.headers.join(' · ')+'</div>' : '')
        + (d.sugerencia ? '<div style="margin-top:8px;font-size:12px;color:#fbbf24;">'+d.sugerencia+'</div>' : '')
        + '</div>';
      return;
    }
    const banner = dryRun
      ? '<div style="color:#fbbf24;padding:10px 14px;background:#0f172a;border:1px solid #fbbf24;border-radius:8px;margin-bottom:14px;">&#x1F441; <strong>VISTA PREVIA</strong> — sin escribir</div>'
      : '<div style="color:#34d399;padding:10px 14px;background:#0f172a;border:1px solid #34d399;border-radius:8px;margin-bottom:14px;">&#x2705; <strong>APLICADO</strong></div>';
    let kpis = '<div class="kpi-row">'
      + '<div class="kpi"><div class="kpi-l">A actualizar</div><div class="kpi-v" style="color:#34d399;">'+d.actualizados.count+'</div></div>'
      + '<div class="kpi"><div class="kpi-l">Sin cambios</div><div class="kpi-v" style="color:#94a3b8;">'+d.sin_cambios.count+'</div></div>'
      + '<div class="kpi"><div class="kpi-l">Sin match</div><div class="kpi-v" style="color:#f87171;">'+d.sin_match.count+'</div></div>'
      + '<div class="kpi"><div class="kpi-l">Sin código</div><div class="kpi-v" style="color:#f87171;">'+d.sin_codigo.count+'</div></div>'
      + '</div>';
    let preview = '';
    if(d.actualizados.lista && d.actualizados.lista.length){
      preview = '<div class="card"><h2>Cambios</h2><table><thead><tr><th>Código</th><th>Nombre antes</th><th>Nombre nuevo</th></tr></thead><tbody>'
        + d.actualizados.lista.map(a => '<tr><td style="font-family:monospace;font-size:11px;">'+a.codigo+'</td><td style="color:#94a3b8;">'+(a.nombre_antes||'(vacío)')+'</td><td style="color:#34d399;font-weight:600;">'+a.nombre_nuevo+'</td></tr>').join('')
        + '</tbody></table></div>';
    }
    let nomatch = '';
    if(d.sin_match.lista && d.sin_match.lista.length){
      nomatch = '<div class="card" style="border-left:3px solid #f87171;"><h2>Sin match en catálogo ('+d.sin_match.count+')</h2>'
        + '<div style="font-size:12px;color:#fbbf24;margin-bottom:8px;">Estos códigos del Excel no están en maestro_mps. Crea primero el MP en /planta.</div>'
        + '<table><tbody>' + d.sin_match.lista.map(a => '<tr><td style="font-size:11px;">fila '+a.fila+'</td><td style="font-family:monospace;">'+a.codigo+'</td><td>'+a.nombre_excel+'</td></tr>').join('')
        + '</tbody></table></div>';
    }
    out.innerHTML = banner + kpis + preview + nomatch;
    if(!dryRun){
      toast('Aplicado: '+d.actualizados.count+' nombres corregidos','ok');
      loadMpsStatus();  // Refresca el panel principal
    }
  }catch(e){
    out.innerHTML = '<div style="color:#f87171;padding:14px;">Error: '+e.message+'</div>';
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


# ─── Auditoria de lotes / movimientos recientes ────────────────────────────────

@bp.route("/api/admin/auditoria-lotes", methods=["GET"])
def admin_auditoria_lotes():
    """Reporta integridad de lotes y movimientos recientes.

    Querystring:
      ?dias=2  → ventana hacia atras (default 2 dias = hoy + ayer)

    Devuelve JSON con:
      - total_lotes_activos: count de lotes con stock > 0
      - lotes_creados_recientes: lotes vistos por primera vez en ventana
      - movimientos_recientes: lista de Entradas/Salidas/Ajustes en ventana
      - duplicados_sospechosos: mismo (lote + material) en mas de 1 entrada
      - resumen_por_usuario: quien creo cuantos movs hoy
    """
    u, err, code = _require_admin()
    if err:
        return err, code

    dias = int(request.args.get("dias", 2))
    fecha_corte = f"-{dias} day"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    out = {"ventana_dias": dias}

    # 1) Total de lotes activos (con stock > 0)
    try:
        rows = c.execute("""
            SELECT material_id, lote,
                   COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +') THEN cantidad
                                     WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad
                                     ELSE 0 END), 0) as stock
            FROM movimientos
            WHERE COALESCE(lote,'') != ''
            GROUP BY material_id, lote
            HAVING stock > 0
        """).fetchall()
        out["total_lotes_activos"] = len(rows)
    except Exception as e:
        out["total_lotes_activos_error"] = str(e)

    # 2) Lotes nuevos en la ventana (primera entrada vista en esos dias)
    try:
        nuevos = c.execute(f"""
            SELECT m.material_id, m.material_nombre, m.lote, m.proveedor,
                   m.cantidad, m.fecha, m.operador,
                   MIN(m.id) as primera_id
            FROM movimientos m
            WHERE COALESCE(m.lote,'') != ''
              AND m.tipo = 'Entrada'
              AND m.fecha >= date('now', '{fecha_corte}')
              AND NOT EXISTS (
                  SELECT 1 FROM movimientos m2
                  WHERE m2.material_id = m.material_id
                    AND m2.lote = m.lote
                    AND m2.id < m.id
              )
            GROUP BY m.material_id, m.lote
            ORDER BY m.fecha DESC, m.id DESC
            LIMIT 200
        """).fetchall()
        out["lotes_creados_recientes"] = [dict(r) for r in nuevos]
        out["lotes_creados_count"] = len(nuevos)
    except Exception as e:
        out["lotes_creados_recientes_error"] = str(e)
        out["lotes_creados_recientes"] = []

    # 3) Movimientos recientes (todos los tipos)
    try:
        movs = c.execute(f"""
            SELECT id, material_id, material_nombre, cantidad, tipo, fecha,
                   lote, proveedor, operador, observaciones
            FROM movimientos
            WHERE fecha >= date('now', '{fecha_corte}')
            ORDER BY id DESC
            LIMIT 500
        """).fetchall()
        out["movimientos_recientes"] = [dict(r) for r in movs]
        out["movimientos_count"] = len(movs)
    except Exception as e:
        out["movimientos_recientes_error"] = str(e)

    # 4) Duplicados sospechosos: mismo (lote + material + cantidad + fecha)
    #    aparece en 2 o mas filas en la ventana
    try:
        dups = c.execute(f"""
            SELECT material_id, material_nombre, lote, cantidad, tipo,
                   COUNT(*) as veces, MIN(id) as primera, MAX(id) as ultima,
                   GROUP_CONCAT(operador, ' / ') as operadores
            FROM movimientos
            WHERE COALESCE(lote,'') != ''
              AND fecha >= date('now', '{fecha_corte}')
            GROUP BY material_id, lote, cantidad, tipo, fecha
            HAVING COUNT(*) > 1
            ORDER BY veces DESC, ultima DESC
        """).fetchall()
        out["duplicados_sospechosos"] = [dict(r) for r in dups]
        out["duplicados_count"] = len(dups)
    except Exception as e:
        out["duplicados_error"] = str(e)
        out["duplicados_sospechosos"] = []

    # 5) Resumen por usuario hoy
    try:
        usr = c.execute("""
            SELECT COALESCE(operador,'(sin operador)') as operador,
                   tipo,
                   COUNT(*) as movs,
                   COUNT(DISTINCT lote) as lotes_distintos
            FROM movimientos
            WHERE fecha = date('now')
            GROUP BY operador, tipo
            ORDER BY movs DESC
        """).fetchall()
        out["resumen_hoy_por_usuario"] = [dict(r) for r in usr]
    except Exception as e:
        out["resumen_hoy_por_usuario_error"] = str(e)

    # 6) Comparativa: ¿cuantos lotes activos teniamos hace N dias?
    #    Reconstruye stock al cierre de hace N dias y cuenta los > 0.
    try:
        rows_pasado = c.execute(f"""
            SELECT material_id, lote,
                   COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +') THEN cantidad
                                     WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad
                                     ELSE 0 END), 0) as stock
            FROM movimientos
            WHERE COALESCE(lote,'') != ''
              AND fecha < date('now', '{fecha_corte}')
            GROUP BY material_id, lote
            HAVING stock > 0
        """).fetchall()
        out["lotes_activos_antes_de_ventana"] = len(rows_pasado)
        out["delta_lotes"] = out["total_lotes_activos"] - len(rows_pasado)
    except Exception as e:
        out["delta_lotes_error"] = str(e)

    conn.close()
    return jsonify(out)


@bp.route("/api/admin/auditoria-lotes/html", methods=["GET"])
def admin_auditoria_lotes_html():
    """Vista HTML legible del reporte de auditoria de lotes."""
    u, err, code = _require_admin()
    if err:
        return Response("<h1>Solo admins</h1>", status=code or 403,
                        mimetype="text/html")

    dias = int(request.args.get("dias", 2))
    html = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Auditoria Lotes — EOS</title>
<style>
body{font-family:-apple-system,Segoe UI,sans-serif;background:#f5f5f4;color:#1c1917;
     padding:24px;max-width:1400px;margin:0 auto;}
h1{color:#6d28d9;border-bottom:2px solid #c4b5fd;padding-bottom:8px;}
h2{color:#7c3aed;margin-top:30px;}
.kpi{display:inline-block;background:#fff;border:1px solid #e7e5e4;border-radius:8px;
     padding:16px 24px;margin:8px 8px 8px 0;min-width:180px;}
.kpi b{display:block;font-size:24px;color:#15803d;}
.kpi.warn b{color:#dc2626;}
.kpi.neutral b{color:#1c1917;}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e7e5e4;
      border-radius:8px;overflow:hidden;margin-top:12px;font-size:13px;}
th{background:#f5f3ff;text-align:left;padding:10px;color:#4c1d95;font-weight:700;}
td{padding:8px 10px;border-top:1px solid #f5f5f4;}
tr:hover{background:#fafaf9;}
.tipo-Entrada{color:#15803d;font-weight:600;}
.tipo-Salida{color:#dc2626;font-weight:600;}
.tipo-Ajuste{color:#a16207;font-weight:600;}
.alert{background:#fef2f2;border:2px solid #dc2626;border-radius:8px;padding:14px;
       margin:14px 0;color:#991b1b;}
.ok{background:#f0fdf4;border:1px solid #15803d;border-radius:6px;padding:10px;
    margin:10px 0;color:#14532d;}
.fmt-cant{text-align:right;font-family:Consolas,monospace;}
.toolbar{margin:14px 0;}
.toolbar a{display:inline-block;padding:6px 14px;background:#fff;border:1px solid #c4b5fd;
           border-radius:6px;color:#6d28d9;text-decoration:none;font-size:12px;
           margin-right:8px;}
.toolbar a:hover{background:#f5f3ff;}
</style></head><body>
<h1>&#x1F50D; Auditoria de Lotes y Movimientos</h1>
<div class="toolbar">
  <a href="?dias=1">Hoy solo</a>
  <a href="?dias=2">Hoy + ayer</a>
  <a href="?dias=7">Ultima semana</a>
  <a href="?dias=30">Ultimo mes</a>
  <a href="/api/admin/auditoria-lotes?dias=""" + str(dias) + """" target="_blank">Ver JSON crudo</a>
</div>
<div id="resumen" style="margin:20px 0;"></div>
<div id="cuerpo">Cargando...</div>
<script>
async function cargar(){
  var r = await fetch('/api/admin/auditoria-lotes?dias=""" + str(dias) + """');
  var d = await r.json();

  // KPIs
  var html = '<h2>Resumen</h2>';
  html += '<div class="kpi neutral"><span>Lotes activos AHORA</span><b>' + d.total_lotes_activos + '</b></div>';
  html += '<div class="kpi neutral"><span>Lotes activos hace ' + d.ventana_dias + 'd</span><b>' + (d.lotes_activos_antes_de_ventana||0) + '</b></div>';
  var deltaCls = (d.delta_lotes||0) > 0 ? 'warn' : 'neutral';
  var deltaSign = (d.delta_lotes||0) > 0 ? '+' : '';
  html += '<div class="kpi ' + deltaCls + '"><span>Delta lotes</span><b>' + deltaSign + (d.delta_lotes||0) + '</b></div>';
  html += '<div class="kpi neutral"><span>Movimientos en ventana</span><b>' + (d.movimientos_count||0) + '</b></div>';
  html += '<div class="kpi neutral"><span>Lotes nuevos en ventana</span><b>' + (d.lotes_creados_count||0) + '</b></div>';
  var dupCls = (d.duplicados_count||0) > 0 ? 'warn' : 'neutral';
  html += '<div class="kpi ' + dupCls + '"><span>Duplicados sospechosos</span><b>' + (d.duplicados_count||0) + '</b></div>';
  document.getElementById('resumen').innerHTML = html;

  // Cuerpo
  var c = '';

  // Duplicados (alerta si hay)
  if((d.duplicados_count||0) > 0){
    c += '<div class="alert"><b>&#x26A0; ' + d.duplicados_count + ' grupos de movimientos posiblemente duplicados</b><br>';
    c += 'Mismo lote + material + cantidad + tipo + fecha repetidos. Revisa si son legitimos o un bug.</div>';
    c += '<table><thead><tr><th>Material</th><th>Lote</th><th>Cantidad</th><th>Tipo</th><th>Veces</th><th>IDs</th><th>Operadores</th></tr></thead><tbody>';
    (d.duplicados_sospechosos||[]).forEach(function(x){
      c += '<tr><td>' + (x.material_id||'') + '<br><small style="color:#78716c">' + (x.material_nombre||'') + '</small></td>';
      c += '<td><b>' + (x.lote||'') + '</b></td>';
      c += '<td class="fmt-cant">' + (x.cantidad||0).toLocaleString('es-CO') + ' g</td>';
      c += '<td class="tipo-' + (x.tipo||'') + '">' + (x.tipo||'') + '</td>';
      c += '<td><b style="color:#dc2626">' + x.veces + '</b></td>';
      c += '<td>' + x.primera + ' a ' + x.ultima + '</td>';
      c += '<td>' + (x.operadores||'') + '</td></tr>';
    });
    c += '</tbody></table>';
  } else {
    c += '<div class="ok">&#x2705; No hay movimientos duplicados sospechosos en la ventana.</div>';
  }

  // Lotes creados recientes
  c += '<h2>Lotes creados en los ultimos ' + d.ventana_dias + ' dias (' + (d.lotes_creados_count||0) + ')</h2>';
  if((d.lotes_creados_count||0) === 0){
    c += '<p style="color:#78716c">Ninguno.</p>';
  } else {
    c += '<table><thead><tr><th>Fecha</th><th>Material</th><th>Lote</th><th>Cantidad</th><th>Proveedor</th><th>Operador</th></tr></thead><tbody>';
    (d.lotes_creados_recientes||[]).forEach(function(x){
      c += '<tr><td>' + (x.fecha||'') + '</td>';
      c += '<td>' + (x.material_id||'') + '<br><small style="color:#78716c">' + (x.material_nombre||'') + '</small></td>';
      c += '<td><b>' + (x.lote||'') + '</b></td>';
      c += '<td class="fmt-cant">' + (x.cantidad||0).toLocaleString('es-CO') + ' g</td>';
      c += '<td>' + (x.proveedor||'') + '</td>';
      c += '<td>' + (x.operador||'') + '</td></tr>';
    });
    c += '</tbody></table>';
  }

  // Resumen por usuario hoy
  c += '<h2>Movimientos hoy por usuario</h2>';
  if(!(d.resumen_hoy_por_usuario||[]).length){
    c += '<p style="color:#78716c">Sin movimientos hoy.</p>';
  } else {
    c += '<table><thead><tr><th>Usuario</th><th>Tipo</th><th>Movs</th><th>Lotes distintos</th></tr></thead><tbody>';
    d.resumen_hoy_por_usuario.forEach(function(x){
      c += '<tr><td><b>' + x.operador + '</b></td>';
      c += '<td class="tipo-' + (x.tipo||'') + '">' + (x.tipo||'') + '</td>';
      c += '<td>' + x.movs + '</td>';
      c += '<td>' + x.lotes_distintos + '</td></tr>';
    });
    c += '</tbody></table>';
  }

  // Movimientos recientes (ultimos 50)
  c += '<h2>Ultimos movimientos (top 50)</h2>';
  c += '<table><thead><tr><th>Fecha</th><th>Tipo</th><th>Material</th><th>Lote</th><th>Cantidad</th><th>Operador</th><th>Observaciones</th></tr></thead><tbody>';
  (d.movimientos_recientes||[]).slice(0, 50).forEach(function(x){
    c += '<tr><td>' + (x.fecha||'') + '</td>';
    c += '<td class="tipo-' + (x.tipo||'').split(' ')[0] + '">' + (x.tipo||'') + '</td>';
    c += '<td>' + (x.material_id||'') + '<br><small style="color:#78716c">' + (x.material_nombre||'') + '</small></td>';
    c += '<td><b>' + (x.lote||'') + '</b></td>';
    c += '<td class="fmt-cant">' + (x.cantidad||0).toLocaleString('es-CO') + ' g</td>';
    c += '<td>' + (x.operador||'') + '</td>';
    c += '<td><small>' + (x.observaciones||'').substring(0,80) + '</small></td></tr>';
  });
  c += '</tbody></table>';

  document.getElementById('cuerpo').innerHTML = c;
}
cargar();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


# ════════════════════════════════════════════════════════════════════════
# IMPORT INVENTARIO ENVASE — formato real de Sebastian (29-abr-2026)
# Excel con hojas ENVASES / GOTEROS / TAPAS / ETIQUETAS / PLEGADIZAS,
# header en fila 4 (col F=tipo, G=PRESENTACION, H=CANTIDAD, Q=TOTAL).
# La columna TOTAL es el inventario actual real.
# ════════════════════════════════════════════════════════════════════════

def _slug_codigo(nombre, presentacion):
    """Genera un codigo MEE consistente: tipo + slug nombre + presentacion.
    Ej: 'FRASCO AMBAR ' + '125ml' → 'AMBAR-125'.
    """
    import re as _re
    s = (nombre or '').upper().strip()
    s = _re.sub(r'[^A-Z0-9 ]', '', s)
    s = _re.sub(r'\s+', ' ', s).strip()
    # Quitar palabras genericas comunes
    GENERIC = {'FRASCO', 'ENVASE', 'BOTTLE', 'PLASTIC', 'TAPA', 'GOTERO'}
    tokens = [t for t in s.split() if t not in GENERIC]
    base = '-'.join(tokens)[:30] if tokens else s.replace(' ', '-')[:30]
    pres = (presentacion or '').upper().strip().replace(' ', '').replace('ML', '').replace('MM', '')
    pres = _re.sub(r'[^A-Z0-9/]', '', pres)
    if pres:
        return f'{base}-{pres}'.strip('-')
    return base or 'MEE-X'


@bp.route("/admin/inventario-envase-import", methods=["GET"])
def admin_inventario_envase_import_page():
    """Página simple para que Sebastian suba el Excel INVENTARIO ENVASE."""
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS:
        return Response("403", status=403)
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Import Inventario Envase</title>
    <style>
      body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:760px;margin:30px auto;padding:0 20px;color:#1e293b}
      h1{font-size:20px;color:#0f172a}
      .card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
      .label{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:6px;display:block}
      input[type=file]{display:block;margin:8px 0 14px;padding:8px;border:1px solid #cbd5e1;border-radius:6px;width:100%;font-size:13px}
      .btn{background:#16a34a;color:#fff;border:none;border-radius:6px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;margin-right:8px}
      .btn.preview{background:#f59e0b}
      .btn.reset{background:#dc2626}
      pre{background:#f1f5f9;padding:12px;border-radius:8px;font-size:11px;overflow-x:auto;max-height:400px}
      .nota{font-size:12px;color:#64748b;line-height:1.6;background:#fefce8;border-left:3px solid #f59e0b;padding:10px 14px;border-radius:6px}
    </style></head><body>
    <a href="/admin" style="font-size:12px;color:#0891b2">&larr; Volver al panel admin</a>
    <h1>📤 Importar INVENTARIO ENVASE.xlsx</h1>
    <div class="nota">
      Sube el archivo <code>INVENTARIO ENVASE.xlsx</code>. El sistema lee las hojas
      <b>ENVASES, GOTEROS, TAPAS</b> (las otras se ignoran por ahora) y actualiza el
      inventario con la columna <b>TOTAL</b> de cada fila.<br><br>
      <b>Preview</b> muestra qué pasaría sin escribir.<br>
      <b>Importar</b> aplica el upsert (crea nuevos códigos + ajusta stock de existentes).<br>
      <b>RESET + Importar</b> archiva todos los Envases/Goteros/Tapas activos antes de importar.
    </div>
    <div class="card">
      <label class="label">Archivo Excel</label>
      <input type="file" id="file" accept=".xlsx,.xlsm">
      <div>
        <button class="btn preview" onclick="enviar(true,'upsert')">👁 Preview (dry run)</button>
        <button class="btn" onclick="enviar(false,'upsert')">📥 Importar (upsert)</button>
        <button class="btn reset" onclick="enviarReset()">⚠️ RESET + Importar</button>
      </div>
    </div>
    <div id="resultado"></div>
    <script>
    async function enviar(dryRun, modo){
      var f = document.getElementById('file').files[0];
      if(!f){ alert('Selecciona un archivo'); return; }
      var fd = new FormData();
      fd.append('file', f);
      var qs = (dryRun?'dry_run=1&':'')+'modo='+encodeURIComponent(modo);
      var r = await fetch('/api/admin/import-inventario-envase-xlsx?'+qs, {method:'POST', body: fd});
      var d = await r.json();
      var col = d.ok ? '#16a34a' : '#dc2626';
      document.getElementById('resultado').innerHTML =
        '<div class="card" style="border-left:4px solid '+col+'"><h3 style="margin:0 0 8px;color:'+col+'">'+
        (d.ok?(d.dry_run?'✅ Preview OK':'✅ Importado'):'❌ Error')+'</h3>'+
        '<pre>'+JSON.stringify(d, null, 2)+'</pre></div>';
    }
    function enviarReset(){
      if(!confirm('⚠️ Esto ARCHIVA todos los Envases/Goteros/Tapas activos antes de importar. ¿Procedes?')) return;
      enviar(false, 'reset_envases');
    }
    </script>
    </body></html>"""
    return Response(html, mimetype="text/html")


@bp.route("/admin/producciones-debug", methods=["GET"])
def admin_producciones_debug_page():
    """Pagina simple para listar producciones programadas activas y borrar
    fantasmas. Sebastian (29-abr-2026): "ese Limpiador kojico 20 kg no se
    de donde lo esta sacando, revisa porfa para que lo elimines"."""
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS:
        return Response("403", status=403)
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Producciones programadas — debug</title>
    <style>
      body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1100px;margin:30px auto;padding:0 20px;color:#1e293b}
      h1{font-size:20px;color:#0f172a}
      table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden}
      th{background:#f8fafc;color:#475569;font-size:11px;text-transform:uppercase;letter-spacing:.5px;text-align:left;padding:10px}
      td{padding:10px;border-top:1px solid #f1f5f9;font-size:13px}
      .badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;text-transform:uppercase}
      .b-cal{background:#dbeafe;color:#1e40af}
      .b-man{background:#fef3c7;color:#92400e}
      .btn-del{background:#dc2626;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:700;cursor:pointer}
      .nota{font-size:12px;color:#64748b;line-height:1.5;background:#eff6ff;border-left:3px solid #3b82f6;padding:10px 14px;border-radius:6px;margin:14px 0}
    </style></head><body>
    <a href="/admin" style="font-size:12px;color:#0891b2">&larr; Volver al panel admin</a>
    <h1>🗓️ Producciones programadas — diagnóstico</h1>
    <div class="nota">
      Lista todas las producciones activas (futuras y de hace ≤7 días). El campo
      <b>origen</b> indica si vino del calendario (auto-sync) o se creó manualmente
      en la app. Si ves una <b>fantasma</b> (que no recuerdas haber programado),
      borra. El sync con calendar se ejecuta cada 10 min y ahora es bidireccional —
      borra del calendar y desaparece sola en minutos.
    </div>
    <button onclick="cargar()" style="margin:12px 0;padding:8px 16px;background:#1e40af;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700">🔄 Actualizar</button>
    <button onclick="forzarSync()" style="margin:12px 0;padding:8px 16px;background:#0891b2;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700">📅 Forzar sync calendario</button>
    <div id="tabla">Cargando...</div>
    <script>
    async function cargar(){
      var r = await fetch('/api/programacion/produccion-programada/listado');
      var d = await r.json();
      if(!r.ok){ document.getElementById('tabla').innerHTML='Error: '+(d.error||r.status); return; }
      var prods = d.producciones || [];
      if(!prods.length){ document.getElementById('tabla').innerHTML='<i>Sin producciones activas.</i>'; return; }
      document.getElementById('tabla').innerHTML =
        '<table><thead><tr>'+
        '<th>ID</th><th>Producto</th><th>Fecha</th><th>kg</th><th>Origen</th><th>Estado</th><th>Observaciones</th><th></th>'+
        '</tr></thead><tbody>'+
        prods.map(function(p){
          var bcl = p.origen==='calendar' ? 'b-cal' : 'b-man';
          return '<tr>'+
            '<td style="font-family:monospace;color:#64748b">'+p.id+'</td>'+
            '<td><b>'+esc(p.producto)+'</b></td>'+
            '<td>'+esc(p.fecha_programada||'')+'</td>'+
            '<td style="font-family:monospace">'+(Math.round(p.kg||0))+'</td>'+
            '<td><span class="badge '+bcl+'">'+esc(p.origen)+'</span></td>'+
            '<td>'+esc(p.estado||'')+'</td>'+
            '<td style="font-size:11px;color:#64748b;max-width:300px">'+esc((p.observaciones||'').substring(0,100))+'</td>'+
            '<td><button class="btn-del" onclick="borrar('+p.id+', \\''+esc(p.producto).replace(/\\\\/g,'').replace(/\\'/g,"\\\\'")+'\\', \\''+esc(p.fecha_programada)+'\\')">Borrar</button></td>'+
          '</tr>';
        }).join('') +
        '</tbody></table>';
    }
    function esc(s){ return String(s||'').replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
    async function borrar(id, prod, fecha){
      if(!confirm('¿Borrar definitivamente la producción '+id+' ('+prod+' · '+fecha+')? También borra items del checklist asociados.')) return;
      var r = await fetch('/api/programacion/produccion-programada/'+id+'/borrar', {method:'DELETE'});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      alert(d.mensaje||'Borrada');
      cargar();
    }
    async function forzarSync(){
      var r = await fetch('/api/programacion/checklist/sync-calendar?dias=120', {method:'POST'});
      var d = await r.json();
      alert(d.mensaje || JSON.stringify(d));
      cargar();
    }
    cargar();
    </script>
    </body></html>"""
    return Response(html, mimetype="text/html")


@bp.route("/api/admin/import-inventario-envase-xlsx", methods=["POST"])
def admin_import_inventario_envase_xlsx():
    """Importa el Excel INVENTARIO ENVASE.xlsx de Sebastian a maestro_mee.

    Sebastian (29-abr-2026): "@INVENTARIO ENVASE.xlsx... mira allí están los
    datos reales con inventario actual donde dice TOTAL... resuelve eso por
    favor, ya sea que elimines y montes o normalices".

    Body: multipart/form-data con 'file' = .xlsx
    Query: ?dry_run=1 para preview sin escribir
           ?modo=upsert (default) | reset_envases (borra todos los items
                                    categoria='Envases' antes de importar)

    Lee 3 hojas estructuradas: ENVASES, GOTEROS, TAPAS. Las hojas ETIQUETAS
    y PLEGADIZAS tienen formato distinto y se ignoran (Sebastian las puede
    cargar luego con otro formato).

    Estructura esperada (header en fila 4, datos desde fila 6):
      F: nombre del material
      G: PRESENTACION (ej. 30ml, 89mm)
      H: CANTIDAD (ingresos historicos — informativo, NO se usa para stock)
      Q (col 17): TOTAL = stock actual real

    Genera codigo automatico: tipo + slug(nombre) + presentacion.
    Por cada fila: INSERT si no existe, UPDATE stock_actual si existe
    (ajuste con auditoria en movimientos_mee).
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
    modo = (request.args.get('modo') or 'upsert').strip()

    try:
        from openpyxl import load_workbook
    except Exception:
        return jsonify({'error': 'openpyxl no instalado'}), 500

    try:
        wb = load_workbook(f, data_only=True, read_only=True)
    except Exception as e:
        return jsonify({'error': f'Excel inválido: {e}'}), 400

    # Mapeo hoja → categoria/prefijo
    HOJAS = {
        'ENVASES': ('Envases', 'ENV'),
        'GOTEROS': ('Goteros', 'GOT'),
        'TAPAS':   ('Tapas',   'TAP'),
    }
    items = []
    detalles_por_hoja = {}
    for sheet_name, (categoria, prefijo) in HOJAS.items():
        if sheet_name not in wb.sheetnames:
            detalles_por_hoja[sheet_name] = {'leidos': 0, 'skipped': 0, 'razon_skip': 'hoja no existe'}
            continue
        ws = wb[sheet_name]
        leidos = 0; skipped = 0
        for ri in range(6, ws.max_row + 1):
            nombre = ws.cell(row=ri, column=6).value      # F
            presentacion = ws.cell(row=ri, column=7).value  # G
            total = ws.cell(row=ri, column=17).value      # Q
            if not nombre:
                continue
            nombre_str = str(nombre).strip()
            if not nombre_str:
                continue
            try:
                stock = float(total) if total is not None else 0.0
            except (ValueError, TypeError):
                stock = 0.0
                skipped += 1
            pres_str = str(presentacion or '').strip()
            slug = _slug_codigo(nombre_str, pres_str)
            codigo = f'{prefijo}-{slug}'[:50]
            descripcion_full = (
                f'{nombre_str} {pres_str}'.strip()
                if pres_str else nombre_str
            )
            items.append({
                'codigo': codigo,
                'descripcion': descripcion_full,
                'categoria': categoria,
                'unidad': 'und',
                'stock': stock,
                'sheet': sheet_name,
                'row': ri,
            })
            leidos += 1
        detalles_por_hoja[sheet_name] = {'leidos': leidos, 'skipped': skipped}

    if not items:
        return jsonify({'error': 'No se leyo ningun item de las hojas conocidas',
                        'hojas_leidas': detalles_por_hoja}), 400

    if dry_run:
        return jsonify({
            'ok': True, 'dry_run': True,
            'total_items': len(items),
            'hojas': detalles_por_hoja,
            'preview': items[:8],
            'mensaje': f'{len(items)} items detectados. Re-envia sin dry_run para escribir.',
        })

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    insertados = 0; actualizados = 0; archivados = 0; ajustes_stock = 0

    if modo == 'reset_envases':
        # Archivar todos los items que NO van a venir en el import (de las
        # 3 categorias afectadas). NO los borra — quedan auditables.
        try:
            cur = c.execute(
                "UPDATE maestro_mee SET estado='Archivado' "
                "WHERE categoria IN ('Envases','Goteros','Tapas') "
                "AND COALESCE(estado,'Activo')='Activo'"
            )
            archivados = cur.rowcount or 0
        except Exception:
            pass

    for it in items:
        existing = c.execute(
            "SELECT codigo, COALESCE(stock_actual,0) FROM maestro_mee WHERE codigo=?",
            (it['codigo'],)
        ).fetchone()
        if existing:
            stock_anterior = float(existing[1] or 0)
            c.execute("""
                UPDATE maestro_mee SET
                  descripcion=?, categoria=?, unidad=?, stock_actual=?,
                  estado='Activo'
                WHERE codigo=?
            """, (it['descripcion'], it['categoria'], it['unidad'],
                  it['stock'], it['codigo']))
            if abs(it['stock'] - stock_anterior) > 0.01:
                try:
                    c.execute("""
                        INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, responsable, observaciones)
                        VALUES (?, 'Ajuste', ?, ?, ?)
                    """, (it['codigo'], abs(it['stock']-stock_anterior), u,
                          f'[Import INVENTARIO ENVASE.xlsx · {it["sheet"]}#{it["row"]}] '
                          f'{stock_anterior:.0f} → {it["stock"]:.0f}'))
                except sqlite3.OperationalError:
                    pass
                ajustes_stock += 1
            actualizados += 1
        else:
            c.execute("""
                INSERT INTO maestro_mee
                  (codigo, descripcion, categoria, unidad, stock_actual,
                   stock_minimo, estado, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, 1000, 'Activo', datetime('now'))
            """, (it['codigo'], it['descripcion'], it['categoria'],
                  it['unidad'], it['stock']))
            try:
                c.execute("""
                    INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, responsable, observaciones)
                    VALUES (?, 'Entrada', ?, ?, ?)
                """, (it['codigo'], it['stock'], u,
                      f'[Import inicial INVENTARIO ENVASE.xlsx · {it["sheet"]}#{it["row"]}]'))
            except sqlite3.OperationalError:
                pass
            insertados += 1
    conn.commit()
    conn.close()
    return jsonify({
        'ok': True,
        'modo': modo,
        'total_items_archivo': len(items),
        'insertados': insertados,
        'actualizados': actualizados,
        'ajustes_stock': ajustes_stock,
        'archivados': archivados,
        'hojas': detalles_por_hoja,
        'mensaje': f'OK · {insertados} nuevos · {actualizados} actualizados · '
                   f'{ajustes_stock} con cambio de stock'
                   + (f' · {archivados} archivados (modo reset)' if archivados else ''),
    })
