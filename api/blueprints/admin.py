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


def _parse_excel_verde(file_storage):
    """Parsea Excel del conteo fisico, retorna solo filas verdes.

    Devuelve: (excel_verde dict, total_g, rows_no_verde_count, errores_list)
    excel_verde[(cod, lote)] = {codigo_mp, lote, inci, nombre_comercial,
                                proveedor, estanteria, posicion,
                                fecha_vencimiento, cantidad_g}

    Compartido entre audit / preview / aplicar para mantener una sola
    fuente de verdad sobre como interpretamos el Excel.
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
        return None, 0, 0, [f'Excel sin columnas requeridas: {list(col_idx.keys())}']

    excel_verde = {}
    total_g = 0.0
    rows_no_verde = 0

    for r in range(header_row + 1, ws.max_row + 1):
        cell_codigo = ws.cell(row=r, column=col_idx['codigo'])
        cell_color = (cell_codigo.fill.fgColor.rgb
                      if cell_codigo.fill.fgColor.type == 'rgb' else None)
        if cell_color != GREEN:
            rows_no_verde += 1
            continue
        cod = cell_codigo.value
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
            # Lote duplicado en Excel verde — sumar (raro pero defensivo)
            excel_verde[key]['cantidad_g'] += cant
        else:
            excel_verde[key] = {
                'codigo_mp': cod, 'lote': lote,
                'inci': str(ws.cell(row=r, column=col_idx['inci']).value or '') if 'inci' in col_idx else '',
                'nombre_comercial': str(ws.cell(row=r, column=col_idx['comercial']).value or '') if 'comercial' in col_idx else '',
                'proveedor': str(ws.cell(row=r, column=col_idx['proveedor']).value or '') if 'proveedor' in col_idx else '',
                'estanteria': str(ws.cell(row=r, column=col_idx['estanteria']).value or '') if 'estanteria' in col_idx else '',
                'posicion': str(ws.cell(row=r, column=col_idx['posicion']).value or '') if 'posicion' in col_idx else '',
                'fecha_vencimiento': venc,
                'cantidad_g': cant,
            }
        total_g += cant

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

    excel_verde, excel_total_g, rows_no_verde, errs = _parse_excel_verde(f)
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

    # Validar: lotes que las salidas de produccion consumieron, ¿estan en Excel verde?
    excel_keys = set(excel_verde.keys())
    salidas_lotes_no_verde = []
    for s in salidas_prod:
        cod = s['material_id']
        lote = s['lote'] or ''
        if (cod, lote) not in excel_keys:
            salidas_lotes_no_verde.append({
                'fecha': str(s['fecha'])[:10],
                'codigo_mp': cod, 'lote': lote,
                'cantidad_g': round(float(s['cantidad'] or 0), 1),
                'observaciones': s['observaciones'],
            })

    stock_post_g = excel_total_g + entradas_oc_g - salidas_prod_g

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
                'total_g': round(excel_total_g, 1),
                'sample_top10': top_excel,
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
            'rows_no_verde_excluidas': rows_no_verde,
        },
        'alertas': {
            'salidas_a_lotes_no_verde': salidas_lotes_no_verde[:30],
            'count_salidas_a_lotes_no_verde': len(salidas_lotes_no_verde),
            'nota': ('Si > 0: la produccion consumio de un lote que '
                     'Catalina marco como NO presente. Tras reset el '
                     'stock de ese lote sera negativo. Hay que decidir: '
                     '(a) ignorar la salida (no replay), (b) ajustar '
                     'manualmente despues, o (c) revisar el conteo.'),
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

    excel_verde, excel_total_g, rows_no_verde, errs = _parse_excel_verde(f)
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
            "SELECT MAX(timestamp) FROM backup_log"
        ).fetchone()[0]
        if last:
            try:
                last_dt = _dt.fromisoformat(last.replace('Z', ''))
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

        # 2. Cargar 305 Entradas iniciales del Excel verde
        DIA_CERO = '2026-04-15T00:00:00'
        OBS_INICIAL = 'Carga inicial Excel dia cero v8_1 — reset 2026-04-27'
        OPERADOR_RESET = 'reset_2026_04_27'
        for (cod, lote), info in excel_verde.items():
            if info['cantidad_g'] <= 0:
                continue
            c.execute("""INSERT INTO movimientos
                         (material_id, material_nombre, cantidad, tipo, fecha,
                          observaciones, lote, fecha_vencimiento, estanteria,
                          posicion, proveedor, estado_lote, operador)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (cod, info['nombre_comercial'] or info['inci'] or cod,
                       float(info['cantidad_g']), 'Entrada', DIA_CERO,
                       OBS_INICIAL, lote, info['fecha_vencimiento'] or None,
                       info['estanteria'] or '', info['posicion'] or '',
                       info['proveedor'] or '', 'VIGENTE', OPERADOR_RESET))
        n_excel_inserted = len(excel_verde)

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
                    f'verde, preservadas {len(entradas_oc)} Entradas con OC + '
                    f'{len(salidas_prod)} Salidas de produccion.'),
        'resumen': {
            'movs_borrados': movs_borrados,
            'lotes_excel_cargados': n_excel_inserted,
            'entradas_oc_preservadas': len(entradas_oc),
            'salidas_prod_preservadas': len(salidas_prod),
            'movs_post_total': movs_post,
            'stock_post_g': round(stock_post_g, 1),
        },
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
  <button class="tab" data-tab="audit-inv" onclick="switchTab('audit-inv')">&#x1F50D; Auditar Inventario</button>
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
    </div>

    <div style="margin-top:24px;padding:16px;background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.4);border-radius:10px;">
      <h3 style="color:#fca5a5;margin:0 0 8px 0;">&#x26A0; Reset + Replay del inventario</h3>
      <div style="font-size:12px;color:#cbd5e1;margin-bottom:12px;">
        <strong style="color:#fca5a5;">DESTRUCTIVO.</strong> Borra todos los movimientos y los recarga desde el Excel verde (estado d&iacute;a cero) + preserva las recepciones formales con OC + re-aplica las salidas de las producciones.
        <br>Sigue el orden: <strong>1)</strong> Descarga snapshot &rarr; <strong>2)</strong> Preview &rarr; <strong>3)</strong> Aplicar.
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <button class="btn btn-outline" onclick="descargarSnapshotPreReset()" title="Descarga JSON con TODOS los movimientos, producciones, OCs, comprobantes — para poder revertir si algo sale mal">&#x1F4BE; 1. Descargar snapshot pre-reset</button>
        <button class="btn btn-outline" onclick="previewReset()" title="Muestra que va a pasar SIN escribir nada">&#x1F441; 2. Preview reset</button>
        <button class="btn" onclick="aplicarReset()" style="background:#dc2626;color:#fff;" title="Ejecuta el reset. Pide token textual de confirmacion.">&#x1F4A5; 3. APLICAR reset</button>
      </div>
    </div>

    <div id="audit-inv-result" style="margin-top:18px;"></div>
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
  if (n == null) return '—';
  if (Math.abs(n) >= 1000) return (n/1000).toLocaleString('es-CO',{maximumFractionDigits:2}) + ' kg';
  return Math.round(n).toLocaleString('es-CO') + ' g';
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

    if (d.alertas.count_salidas_a_lotes_no_verde > 0) {
      h += '<div style="background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.4);border-radius:8px;padding:12px;margin-bottom:14px;">';
      h += '<div style="color:#fbbf24;font-weight:700;margin-bottom:4px;">⚠ ' + d.alertas.count_salidas_a_lotes_no_verde + ' salidas de producción consumieron lotes que NO están en Excel verde</div>';
      h += '<div style="color:#cbd5e1;font-size:11px;">' + _esc(d.alertas.nota) + '</div>';
      h += '<div style="color:#94a3b8;font-size:11px;margin-top:6px;">Sample (primeros 30):</div>';
      h += '<ul style="margin:4px 0 0 18px;color:#cbd5e1;font-size:11px;">';
      d.alertas.salidas_a_lotes_no_verde.forEach(s => {
        h += '<li>' + _esc(s.fecha) + ' · ' + _esc(s.codigo_mp) + ' · ' + _esc(s.lote) + ' · ' + _fmtG(s.cantidad_g) + ' (' + _esc(s.observaciones) + ')</li>';
      });
      h += '</ul></div>';
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
