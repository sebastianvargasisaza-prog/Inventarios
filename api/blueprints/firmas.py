"""Blueprint firmas · 21 CFR Part 11 §§11.50/11.70/11.200 + INVIMA.

Sebastián 12-may-2026 · Fase 0 Bloque C del salto a BRD.

Workflow de firma electrónica con re-autenticación obligatoria. La sesión
HTTP autenticada NO basta para firmar — Part 11 §11.200(a)(1)(i) exige que
las firmas no-biométricas usen al menos dos componentes (algo que sabes +
algo que tenés) y que el primer componente se reverifique en cada firma.

Workflow:
  1. Usuario en UI hace click "Firmar como liberado".
  2. Modal pide password (+ TOTP si MFA enrolado).
  3. Frontend → POST /api/sign/challenge {password, totp_token}
     → backend valida factores → emite token efímero (5 min, single-use).
  4. Frontend → POST /api/sign {record_table, record_id, meaning, comment,
                                challenge_token, record_hash?}
     → backend consume token → snapshot identidad → INSERT e_signatures.
  5. Lista visible: GET /api/sign/<table>/<id> retorna firmas sobre el record.

`meaning` es enum de strings cortos: 'autoriza', 'revisa', 'aprueba',
'libera', 'rechaza', 'reabre'. Cada uno deja una firma separada — un
record puede acumular varias firmas (ej. autoriza→revisa→aprueba→libera).

`record_hash` es opcional pero recomendado: si el caller calcula un SHA256
del estado actual del record y lo pasa, queda en la firma. Si después se
modifica el record, la firma muestra que ese estado en particular fue
firmado (tamper-evidence).
"""
import hashlib
import hmac
import logging
import os
import secrets as _secrets
import sys
from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, jsonify, request, session

from database import get_db
from config import COMPRAS_USERS
from werkzeug.security import check_password_hash

# mfa.py vive en blueprints/ — import relativo dentro del paquete
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

bp = Blueprint("firmas", __name__)
log = logging.getLogger("firmas")

CHALLENGE_TTL_SECONDS = 300  # 5 minutos · suficiente para llenar comment + confirmar

VALID_MEANINGS = {
    "autoriza", "revisa", "aprueba", "libera", "rechaza", "reabre",
    "ejecuta", "supervisa", "ack",
}


def _now_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _client_ip():
    try:
        return request.headers.get("X-Forwarded-For", request.remote_addr or "")[:45]
    except Exception:
        return ""


def _verify_password(username, password):
    """Verifica password contra el hash del usuario (BD users_passwords → env
    COMPRAS_USERS), igual que el login principal.

    Fix 28-may: antes solo miraba COMPRAS_USERS (env) e ignoraba
    users_passwords → un usuario que cambió su contraseña vía UI no podía
    e-firmar (Part 11). Ahora resuelve BD→env como /login.

    Retorna True/False. Defensivo: no filtra la razón del fallo.
    """
    if not username or not password:
        return False
    try:
        from blueprints.core import _resolve_password_hash
        stored = _resolve_password_hash(username)
    except Exception:
        stored = COMPRAS_USERS.get(username, "")
    if not stored:
        return False
    try:
        if stored.startswith('pbkdf2:') or stored.startswith('scrypt:'):
            return check_password_hash(stored, password)
        import hmac as _hmac
        return _hmac.compare_digest(stored, password)
    except Exception:
        return False


def _verify_totp_if_enrolled(username, totp_token):
    """Si el usuario tiene MFA enrolado, valida el TOTP. Retorna (ok, factor_used).

    factor_used: 'password+totp' si MFA enrolled y verificado,
                 'password' si MFA NO enrolled (factor único permitido pero menor seguridad),
                 None si verificación falló.
    """
    try:
        from blueprints.mfa import _is_mfa_enabled, _get_mfa_record, _verify_totp
    except Exception as e:
        # Fail-closed: si no se puede verificar el estado de MFA, NO degradar
        # a solo-password · una firma electrónica regulada (Part 11) exige
        # certeza del segundo factor. Rechazar es más seguro que degradar.
        log.error("mfa import falló · firma rechazada por seguridad: %s", e)
        return (False, None)
    if not _is_mfa_enabled(username):
        return (True, "password")
    rec = _get_mfa_record(username)
    if not rec or not _verify_totp(rec.get("secret", ""), totp_token):
        return (False, None)
    return (True, "password+totp")


def _sign_payload(*, record_table, record_id, meaning, signer_username,
                   signed_at_utc, ip, auth_factor, comment, record_hash):
    """Calcula HMAC-SHA256 sobre los campos críticos.

    SECRET_KEY actúa como llave HMAC. La firma queda persistida; un cambio
    posterior en cualquier campo de e_signatures (que no debería suceder por
    el trigger append-only de mig 107) sería detectable porque el hash
    re-calculado no coincidiría.
    """
    secret = (current_app.secret_key or "").encode("utf-8")
    payload = "|".join([
        record_table or "", record_id or "", meaning or "",
        signer_username or "", signed_at_utc or "", ip or "",
        auth_factor or "", comment or "", record_hash or "",
    ]).encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def crear_firma_directa(conn, *, username, record_table, record_id,
                        meaning, auth_factor='password', comment=''):
    """Crea una e_signature server-side cuando los factores YA fueron verificados
    por el caller (password + TOTP). Para operaciones BATCH que re-autentican UNA
    vez y firman N records en una sesión continua (21 CFR Part 11 §11.200(a)(1)(ii):
    serie de firmas durante un acceso continuo · primera con todos los factores).

    Reusa _sign_payload (mismo HMAC/tamper-evidence que /api/sign). NO commitea
    (el caller maneja la transacción). Devuelve signature_id.
    """
    cur = conn.cursor()
    now_utc_str = _now_utc_iso()
    ident = cur.execute(
        "SELECT nombre_completo, cedula, cargo FROM usuarios_identidad WHERE username=?",
        (username,)).fetchone()
    fn = (ident["nombre_completo"] if ident else "") or ""
    ced = (ident["cedula"] if ident else "") or ""
    cargo = (ident["cargo"] if ident else "") or ""
    ip = _client_ip()
    rid = str(record_id)
    sig_hash = _sign_payload(
        record_table=record_table, record_id=rid, meaning=meaning,
        signer_username=username, signed_at_utc=now_utc_str, ip=ip,
        auth_factor=auth_factor, comment=comment, record_hash="")
    cur.execute(
        """INSERT INTO e_signatures
             (record_table, record_id, meaning, signer_username,
              signer_full_name, signer_cedula, signer_cargo,
              signed_at_utc, ip, auth_factor, comment, record_hash,
              signature_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (record_table, rid, meaning, username, fn, ced, cargo,
         now_utc_str, ip, auth_factor, comment, "", sig_hash))
    return cur.lastrowid


# ── /api/sign/challenge ───────────────────────────────────────────────────

@bp.route("/api/sign/challenge", methods=["POST"])
def sign_challenge():
    """Verifica password (+ TOTP si MFA) y emite token efímero single-use.

    Body: {password, totp_token?}
    Response: {token, expires_at_utc, auth_factor}
    """
    username = session.get("compras_user", "")
    if not username:
        return jsonify({"error": "No autorizado · login requerido"}), 401

    body = request.get_json(silent=True) or {}
    password = body.get("password", "")
    totp_token = body.get("totp_token", "")

    if not _verify_password(username, password):
        log.info("sign_challenge: password rechazado para user=%s", username)
        return jsonify({"error": "Credenciales inválidas"}), 401

    ok_totp, factor = _verify_totp_if_enrolled(username, totp_token)
    if not ok_totp:
        log.info("sign_challenge: TOTP rechazado para user=%s", username)
        return jsonify({"error": "Token MFA inválido"}), 401

    token = _secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=CHALLENGE_TTL_SECONDS)

    conn = get_db()
    conn.execute(
        """INSERT INTO sign_challenges
             (token, username, auth_factor, created_at_utc, expires_at_utc, ip)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (token, username, factor,
         now.strftime("%Y-%m-%d %H:%M:%S"),
         expires.strftime("%Y-%m-%d %H:%M:%S"),
         _client_ip()),
    )
    conn.commit()

    return jsonify({
        "token": token,
        "expires_at_utc": expires.strftime("%Y-%m-%d %H:%M:%S"),
        "auth_factor": factor,
        "ttl_seconds": CHALLENGE_TTL_SECONDS,
    })


# ── /api/sign ─────────────────────────────────────────────────────────────

@bp.route("/api/sign", methods=["POST"])
def sign_record():
    """Consume challenge_token y crea registro inmutable en e_signatures.

    Body: {record_table, record_id, meaning, challenge_token,
           comment?, record_hash?}
    Response 201: {ok, signature_id, signature_hash}
    """
    username = session.get("compras_user", "")
    if not username:
        return jsonify({"error": "No autorizado · login requerido"}), 401

    body = request.get_json(silent=True) or {}
    record_table = (body.get("record_table") or "").strip()
    record_id = (body.get("record_id") or "").strip()
    meaning = (body.get("meaning") or "").strip().lower()
    challenge_token = (body.get("challenge_token") or "").strip()
    comment = (body.get("comment") or "").strip()[:500]
    record_hash = (body.get("record_hash") or "").strip()[:128]

    if not record_table or not record_id:
        return jsonify({"error": "record_table y record_id requeridos"}), 400
    if meaning not in VALID_MEANINGS:
        return jsonify({"error": f"meaning inválido · use {sorted(VALID_MEANINGS)}"}), 400
    if not challenge_token:
        return jsonify({"error": "challenge_token requerido (POST /api/sign/challenge primero)"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Consumir challenge atómicamente: verificar + marcar consumed=1 en
    # el mismo UPDATE para evitar race conditions de re-uso.
    chall = cur.execute(
        """SELECT username, auth_factor, expires_at_utc, consumed
           FROM sign_challenges WHERE token = ?""",
        (challenge_token,),
    ).fetchone()
    if not chall:
        return jsonify({"error": "challenge_token inválido"}), 401
    if int(chall["consumed"] or 0) != 0:
        return jsonify({"error": "challenge_token ya fue usado"}), 401
    if chall["username"] != username:
        return jsonify({"error": "challenge_token pertenece a otro usuario"}), 401
    # Verificar expiración (comparación lex sobre strings ISO funciona)
    now_utc_str = _now_utc_iso()
    if (chall["expires_at_utc"] or "") < now_utc_str:
        return jsonify({"error": "challenge_token expirado · re-autenticá"}), 401

    cur.execute(
        """UPDATE sign_challenges
             SET consumed = 1, consumed_at_utc = ?
           WHERE token = ? AND consumed = 0""",
        (now_utc_str, challenge_token),
    )
    if cur.rowcount != 1:
        # Otro request lo consumió en paralelo
        return jsonify({"error": "challenge_token consumido en paralelo"}), 409
    auth_factor = chall["auth_factor"] or "password"
    # INVIMA-FIX · 21-may-2026 · 21 CFR Part 11 §11.200 · MFA obligatorio
    # para meanings críticos (libera/rechaza/aprueba) en admin/QC.
    # Si user es admin y meaning crítico → exigir auth_factor='totp' (MFA real)
    _MEANINGS_CRITICOS = {'libera', 'rechaza', 'aprueba', 'autoriza'}
    if meaning in _MEANINGS_CRITICOS:
        try:
            from config import ADMIN_USERS as _ADM, CALIDAD_USERS as _QC
            _grupo_estricto = {x.lower() for x in (set(_ADM) | set(_QC))}
        except Exception:
            _grupo_estricto = set()
        if username.lower() in _grupo_estricto and auth_factor != 'totp':
            # Verificar que MFA esté enrolado (no exigir si user no tiene MFA setup)
            try:
                mfa_row = cur.execute(
                    "SELECT enabled FROM mfa_secrets WHERE username=? AND COALESCE(enabled,0)=1",
                    (username,),
                ).fetchone()
                if mfa_row:
                    # Sí tiene MFA · debe usarlo para meanings críticos
                    return jsonify({
                        'error': 'Meaning crítico requiere firma con MFA TOTP · re-firmá con auth_factor=totp',
                        'codigo': 'MFA_REQUIRED_FOR_CRITICAL_SIGN',
                    }), 403
            except Exception:
                pass  # graceful · no bloquear si tabla no existe

    # Snapshot identidad humana del firmante (Part 11 §11.50: printed name)
    ident = cur.execute(
        """SELECT nombre_completo, cedula, cargo
           FROM usuarios_identidad WHERE username = ?""",
        (username,),
    ).fetchone()
    signer_full_name = (ident["nombre_completo"] if ident else "") or ""
    signer_cedula = (ident["cedula"] if ident else "") or ""
    signer_cargo = (ident["cargo"] if ident else "") or ""

    ip = _client_ip()
    sig_hash = _sign_payload(
        record_table=record_table, record_id=record_id, meaning=meaning,
        signer_username=username, signed_at_utc=now_utc_str, ip=ip,
        auth_factor=auth_factor, comment=comment, record_hash=record_hash,
    )

    cur.execute(
        """INSERT INTO e_signatures
             (record_table, record_id, meaning, signer_username,
              signer_full_name, signer_cedula, signer_cargo,
              signed_at_utc, ip, auth_factor, comment, record_hash,
              signature_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (record_table, record_id, meaning, username,
         signer_full_name, signer_cedula, signer_cargo,
         now_utc_str, ip, auth_factor, comment, record_hash, sig_hash),
    )
    sig_id = cur.lastrowid
    conn.commit()

    log.info(
        "sign_record ok user=%s table=%s id=%s meaning=%s factor=%s",
        username, record_table, record_id, meaning, auth_factor,
    )
    return jsonify({
        "ok": True,
        "signature_id": sig_id,
        "signature_hash": sig_hash,
        "signed_at_utc": now_utc_str,
        "auth_factor": auth_factor,
    }), 201


# ── /api/sign/<table>/<id> ────────────────────────────────────────────────

@bp.route("/api/sign/<record_table>/<path:record_id>", methods=["GET"])
def list_signatures(record_table, record_id):
    """Lista firmas sobre un record · cualquier user logueado."""
    if not session.get("compras_user"):
        return jsonify({"error": "No autorizado"}), 401

    conn = get_db()
    rows = conn.execute(
        """SELECT id, record_table, record_id, meaning, signer_username,
                  signer_full_name, signer_cedula, signer_cargo,
                  signed_at_utc, ip, auth_factor, comment, record_hash,
                  signature_hash
           FROM e_signatures
           WHERE record_table = ? AND record_id = ?
           ORDER BY signed_at_utc, id""",
        (record_table, record_id),
    ).fetchall()
    # Re-verificar el HMAC de cada firma al leerla · tamper-evidence Part 11.
    # Si alguien modificó una fila de e_signatures saltándose el trigger
    # append-only, el hash recalculado NO coincide → tampered=True. La firma
    # ya no se cree solo porque está en la tabla.
    sigs = []
    for r in rows:
        d = dict(r)
        try:
            recalculado = _sign_payload(
                record_table=d.get("record_table"), record_id=d.get("record_id"),
                meaning=d.get("meaning"), signer_username=d.get("signer_username"),
                signed_at_utc=d.get("signed_at_utc"), ip=d.get("ip"),
                auth_factor=d.get("auth_factor"), comment=d.get("comment"),
                record_hash=d.get("record_hash"),
            )
            d["tampered"] = not hmac.compare_digest(
                recalculado, d.get("signature_hash") or "")
        except Exception:
            d["tampered"] = None  # no se pudo verificar
        sigs.append(d)
    return jsonify({
        "record_table": record_table,
        "record_id": record_id,
        "signatures": sigs,
    })
