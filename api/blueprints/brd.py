"""Blueprint brd · Master Batch Record (MBR) CRUD.

Sebastián 12-may-2026 · Fase 1 del salto a Batch Record digital.

MBR = procedimiento aprobado por QA para fabricar UN producto en UN tamaño
de lote estándar. Workflow:
    draft        → editable libremente por el creador.
    en_revision  → submit a QA · ya no editable, esperando aprobación.
    aprobado     → vigente · puede instanciarse en EBR. Inmutable (mig 109
                   triggers bloquean UPDATE de campos críticos).
    obsoleto     → reemplazado por nueva versión.

Endpoints:
    GET    /api/brd/mbr                       lista (filtros: producto, estado)
    GET    /api/brd/mbr/<id>                  detalle (template + pasos)
    POST   /api/brd/mbr                       crea draft nuevo
    PATCH  /api/brd/mbr/<id>                  edita header del draft
    POST   /api/brd/mbr/<id>/pasos            agrega paso al final
    PATCH  /api/brd/mbr/<id>/pasos/<paso_id>  edita paso (solo en draft)
    DELETE /api/brd/mbr/<id>/pasos/<paso_id>  borra paso (solo en draft)
    POST   /api/brd/mbr/<id>/submit           draft → en_revision
    POST   /api/brd/mbr/<id>/aprobar          en_revision → aprobado (requiere
                                              signature_id de e_signatures con
                                              meaning='aprueba')
    POST   /api/brd/mbr/<id>/obsoletar        aprobado → obsoleto (requiere motivo)

Permisos:
    - Crear/editar drafts: cualquier user logueado (después restringir a
      Técnica/Calidad si se necesita).
    - Submit a revisión: el creador o admin.
    - Aprobar/obsoletar: ADMIN_USERS o CALIDAD_USERS.
"""
import json as _json
import logging
from flask import Blueprint, jsonify, request, session

from database import get_db
from config import ADMIN_USERS, CALIDAD_USERS
from audit_helpers import audit_log

bp = Blueprint("brd", __name__)
log = logging.getLogger("brd")

VALID_TIPO_PASO = {
    "pesaje", "dispensacion", "mezclado", "caliente",
    "enfriamiento", "control_ipc", "envasado", "inspeccion",
    "limpieza", "otro",
}


# ── helpers permisos ────────────────────────────────────────────────────────

def _require_login():
    if not session.get("compras_user"):
        return jsonify({"error": "No autorizado"}), 401
    return None


def _require_qa_or_admin():
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return jsonify({"error": "Solo admin o calidad pueden aprobar/obsoletar MBR"}), 403
    return None


# ── helpers data ────────────────────────────────────────────────────────────

def _mbr_to_dict(row, pasos=None):
    d = {
        "id": row["id"],
        "producto_nombre": row["producto_nombre"],
        "formula_version_id": row["formula_version_id"],
        "version": row["version"],
        "estado": row["estado"],
        "titulo": row["titulo"] or "",
        "descripcion": row["descripcion"] or "",
        "lote_size_g": row["lote_size_g"],
        "tiempo_total_estimado_min": row["tiempo_total_estimado_min"] or 0,
        "creado_por": row["creado_por"],
        "creado_at_utc": row["creado_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
        "aprobado_por": row["aprobado_por"] or "",
        "aprobado_at_utc": row["aprobado_at_utc"],
        "aprobado_signature_id": row["aprobado_signature_id"],
        "obsoleto_at_utc": row["obsoleto_at_utc"],
        "obsoleto_motivo": row["obsoleto_motivo"] or "",
    }
    if pasos is not None:
        d["pasos"] = [_paso_to_dict(p) for p in pasos]
    return d


def _paso_to_dict(row):
    return {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "orden": row["orden"],
        "fase": row["fase"] or "",
        "descripcion": row["descripcion"],
        "tipo_paso": row["tipo_paso"] or "otro",
        "equipo_requerido": row["equipo_requerido"] or "",
        "tiempo_estimado_min": row["tiempo_estimado_min"] or 0,
        "requiere_e_sign": int(row["requiere_e_sign"] or 0),
        "requiere_qc": int(row["requiere_qc"] or 0),
        "notas": row["notas"] or "",
    }


def _next_version(conn, producto):
    row = conn.execute(
        "SELECT MAX(version) FROM mbr_templates WHERE producto_nombre = ?",
        (producto,),
    ).fetchone()
    return int(row[0] or 0) + 1


# ── endpoints ───────────────────────────────────────────────────────────────

@bp.route("/api/brd/mbr", methods=["GET"])
def listar_mbr():
    err = _require_login()
    if err:
        return err
    producto = (request.args.get("producto") or "").strip()
    estado = (request.args.get("estado") or "").strip()
    where = []
    params = []
    if producto:
        where.append("producto_nombre = ?")
        params.append(producto)
    if estado:
        where.append("estado = ?")
        params.append(estado)
    sql = """SELECT id, producto_nombre, formula_version_id, version, estado,
                    titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
                    creado_por, creado_at_utc, updated_at_utc,
                    aprobado_por, aprobado_at_utc, aprobado_signature_id,
                    obsoleto_at_utc, obsoleto_motivo
             FROM mbr_templates"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY producto_nombre, version DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_mbr_to_dict(r) for r in rows]})


@bp.route("/api/brd/mbr/<int:mbr_id>", methods=["GET"])
def detalle_mbr(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        """SELECT id, producto_nombre, formula_version_id, version, estado,
                  titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
                  creado_por, creado_at_utc, updated_at_utc,
                  aprobado_por, aprobado_at_utc, aprobado_signature_id,
                  obsoleto_at_utc, obsoleto_motivo
           FROM mbr_templates WHERE id = ?""",
        (mbr_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    pasos = conn.execute(
        """SELECT id, mbr_template_id, orden, fase, descripcion, tipo_paso,
                  equipo_requerido, tiempo_estimado_min, requiere_e_sign,
                  requiere_qc, notas
           FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr_id,),
    ).fetchall()
    return jsonify(_mbr_to_dict(row, pasos))


@bp.route("/api/brd/mbr", methods=["POST"])
def crear_mbr():
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    try:
        lote_size_g = float(body.get("lote_size_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "lote_size_g inválido"}), 400
    if lote_size_g <= 0:
        return jsonify({"error": "lote_size_g debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    version = _next_version(conn, producto)
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO mbr_templates
             (producto_nombre, formula_version_id, version, estado,
              titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
              creado_por)
           VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)""",
        (producto,
         body.get("formula_version_id"),
         version,
         (body.get("titulo") or f"{producto} v{version}").strip(),
         (body.get("descripcion") or "").strip(),
         lote_size_g,
         int(body.get("tiempo_total_estimado_min") or 0),
         user),
    )
    mbr_id = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="CREATE_MBR_DRAFT",
              tabla="mbr_templates", registro_id=mbr_id,
              despues={"producto": producto, "version": version})
    return jsonify({"ok": True, "id": mbr_id, "version": version}), 201


@bp.route("/api/brd/mbr/<int:mbr_id>", methods=["PATCH"])
def editar_mbr(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT estado, creado_por FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    if row["estado"] != "draft":
        return jsonify({"error": f"solo editable en estado 'draft' (actual: {row['estado']})"}), 409
    body = request.get_json(silent=True) or {}
    EDITABLE = {"titulo", "descripcion", "lote_size_g",
                "tiempo_total_estimado_min", "formula_version_id"}
    cambios = {k: v for k, v in body.items() if k in EDITABLE}
    if not cambios:
        return jsonify({"error": "No hay campos editables", "editables": sorted(EDITABLE)}), 400
    set_clause = ", ".join(f"{k} = ?" for k in cambios)
    cur.execute(f"UPDATE mbr_templates SET {set_clause} WHERE id = ?",
                list(cambios.values()) + [mbr_id])
    conn.commit()
    audit_log(cur, usuario=session.get("compras_user", ""),
              accion="UPDATE_MBR_DRAFT", tabla="mbr_templates",
              registro_id=mbr_id, despues=cambios)
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos", methods=["POST"])
def agregar_paso(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    if row["estado"] != "draft":
        return jsonify({"error": "solo se agregan pasos en draft"}), 409
    body = request.get_json(silent=True) or {}
    descripcion = (body.get("descripcion") or "").strip()
    if not descripcion:
        return jsonify({"error": "descripcion requerida"}), 400
    tipo = (body.get("tipo_paso") or "otro").strip().lower()
    if tipo not in VALID_TIPO_PASO:
        return jsonify({"error": f"tipo_paso inválido · use {sorted(VALID_TIPO_PASO)}"}), 400
    siguiente_orden = (cur.execute(
        "SELECT COALESCE(MAX(orden), 0) FROM mbr_pasos WHERE mbr_template_id = ?",
        (mbr_id,),
    ).fetchone()[0] or 0) + 1
    cur.execute(
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mbr_id, siguiente_orden,
         (body.get("fase") or "").strip(), descripcion, tipo,
         (body.get("equipo_requerido") or "").strip(),
         int(body.get("tiempo_estimado_min") or 0),
         1 if body.get("requiere_e_sign") else 0,
         1 if body.get("requiere_qc") else 0,
         (body.get("notas") or "").strip()),
    )
    paso_id = cur.lastrowid
    conn.commit()
    return jsonify({"ok": True, "id": paso_id, "orden": siguiente_orden}), 201


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>", methods=["PATCH"])
def editar_paso(mbr_id, paso_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se editan pasos en draft"}), 409
    body = request.get_json(silent=True) or {}
    EDITABLE = {"fase", "descripcion", "tipo_paso", "equipo_requerido",
                "tiempo_estimado_min", "requiere_e_sign", "requiere_qc",
                "notas", "orden"}
    cambios = {k: v for k, v in body.items() if k in EDITABLE}
    if "tipo_paso" in cambios:
        if cambios["tipo_paso"] not in VALID_TIPO_PASO:
            return jsonify({"error": "tipo_paso inválido"}), 400
    if not cambios:
        return jsonify({"error": "No hay campos editables", "editables": sorted(EDITABLE)}), 400
    # bool/int normalización
    if "requiere_e_sign" in cambios:
        cambios["requiere_e_sign"] = 1 if cambios["requiere_e_sign"] else 0
    if "requiere_qc" in cambios:
        cambios["requiere_qc"] = 1 if cambios["requiere_qc"] else 0
    set_clause = ", ".join(f"{k} = ?" for k in cambios)
    cur.execute(
        f"UPDATE mbr_pasos SET {set_clause} WHERE id = ? AND mbr_template_id = ?",
        list(cambios.values()) + [paso_id, mbr_id],
    )
    if cur.rowcount == 0:
        return jsonify({"error": "paso no encontrado o no pertenece al MBR"}), 404
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>", methods=["DELETE"])
def borrar_paso(mbr_id, paso_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se borran pasos en draft"}), 409
    cur.execute(
        "DELETE FROM mbr_pasos WHERE id = ? AND mbr_template_id = ?",
        (paso_id, mbr_id),
    )
    if cur.rowcount == 0:
        return jsonify({"error": "paso no encontrado"}), 404
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/submit", methods=["POST"])
def submit_a_revision(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado, creado_por FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": f"solo draft puede submit (actual: {tpl['estado']})"}), 409
    user = session.get("compras_user", "")
    if user != tpl["creado_por"] and user not in ADMIN_USERS:
        return jsonify({"error": "Solo el creador o admin puede submit"}), 403
    n_pasos = cur.execute(
        "SELECT COUNT(*) FROM mbr_pasos WHERE mbr_template_id = ?", (mbr_id,)
    ).fetchone()[0]
    if n_pasos < 1:
        return jsonify({"error": "MBR debe tener al menos 1 paso antes de submit"}), 400
    cur.execute(
        "UPDATE mbr_templates SET estado = 'en_revision' WHERE id = ?",
        (mbr_id,),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="SUBMIT_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "draft"}, despues={"estado": "en_revision"})
    return jsonify({"ok": True, "estado": "en_revision"})


@bp.route("/api/brd/mbr/<int:mbr_id>/aprobar", methods=["POST"])
def aprobar_mbr(mbr_id):
    """Aprueba un MBR en revisión. Requiere signature_id de e_signatures
    con meaning='aprueba' del usuario actual sobre este MBR."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    if not signature_id:
        return jsonify({
            "error": "signature_id requerido · primero firmá vía POST /api/sign con "
                      "{record_table:'mbr_templates', record_id:'<id>', meaning:'aprueba'}"
        }), 400

    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "en_revision":
        return jsonify({"error": f"solo en_revision puede aprobarse (actual: {tpl['estado']})"}), 409

    # Validar la firma: debe ser del usuario actual, sobre este MBR, meaning='aprueba'
    user = session.get("compras_user", "")
    sig = cur.execute(
        """SELECT id FROM e_signatures
           WHERE id = ? AND record_table = 'mbr_templates'
             AND record_id = ? AND meaning = 'aprueba' AND signer_username = ?""",
        (int(signature_id), str(mbr_id), user),
    ).fetchone()
    if not sig:
        return jsonify({
            "error": "signature_id no corresponde a una firma 'aprueba' de este MBR por vos",
        }), 400

    cur.execute(
        """UPDATE mbr_templates
             SET estado = 'aprobado',
                 aprobado_por = ?,
                 aprobado_at_utc = datetime('now', 'utc'),
                 aprobado_signature_id = ?
           WHERE id = ?""",
        (user, int(signature_id), mbr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="APROBAR_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "en_revision"},
              despues={"estado": "aprobado", "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "aprobado"})


@bp.route("/api/brd/mbr/<int:mbr_id>/obsoletar", methods=["POST"])
def obsoletar_mbr(mbr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()
    if not motivo:
        return jsonify({"error": "motivo requerido para obsoletar"}), 400
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "aprobado":
        return jsonify({"error": f"solo aprobado puede obsoletarse (actual: {tpl['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE mbr_templates
             SET estado = 'obsoleto',
                 obsoleto_at_utc = datetime('now', 'utc'),
                 obsoleto_motivo = ?
           WHERE id = ?""",
        (motivo, mbr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="OBSOLETAR_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "aprobado"},
              despues={"estado": "obsoleto", "motivo": motivo})
    return jsonify({"ok": True, "estado": "obsoleto"})


# ════════════════════════════════════════════════════════════════════════════
# EBR (Executed Batch Record) · ejecución de un lote real desde un MBR
# ════════════════════════════════════════════════════════════════════════════
# Flujo típico:
#   1. POST /api/brd/ebr {mbr_template_id, lote, produccion_id?}
#      → clona pasos del MBR a ebr_pasos_ejecutados (pendientes).
#   2. Operario va al wizard del EBR. Por cada paso: iniciar → completar
#      con observaciones + e-sign si requerido.
#   3. POST /api/brd/ebr/<id>/completar con cantidad_real_g → yield_pct.
#   4. QC firma: POST /api/brd/ebr/<id>/liberar con signature_id.

VALID_ESTADOS_EBR = {"iniciado", "en_proceso", "completado",
                     "en_revision_qc", "liberado", "rechazado"}


def _ebr_to_dict(row, pasos=None):
    d = {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "mbr_version": row["mbr_version"],
        "produccion_id": row["produccion_id"],
        "lote": row["lote"],
        "estado": row["estado"],
        "iniciado_por": row["iniciado_por"],
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "liberado_por": row["liberado_por"] or "",
        "liberado_at_utc": row["liberado_at_utc"],
        "liberado_signature_id": row["liberado_signature_id"],
        "rechazado_motivo": row["rechazado_motivo"] or "",
        "cantidad_objetivo_g": row["cantidad_objetivo_g"],
        "cantidad_real_g": row["cantidad_real_g"],
        "yield_pct": row["yield_pct"],
        "notas": row["notas"] or "",
    }
    if pasos is not None:
        d["pasos"] = [_paso_ej_to_dict(p) for p in pasos]
    return d


def _paso_ej_to_dict(row):
    return {
        "id": row["id"],
        "ebr_id": row["ebr_id"],
        "mbr_paso_id": row["mbr_paso_id"],
        "orden": row["orden"],
        "descripcion": row["descripcion"],
        "tipo_paso": row["tipo_paso"] or "otro",
        "equipo_requerido": row["equipo_requerido"] or "",
        "requiere_e_sign": int(row["requiere_e_sign"] or 0),
        "requiere_qc": int(row["requiere_qc"] or 0),
        "estado": row["estado"],
        "operario_username": row["operario_username"] or "",
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "observaciones": row["observaciones"] or "",
        "e_sign_id": row["e_sign_id"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "desviacion_id": row["desviacion_id"],
    }


def _validar_signature(cur, signature_id, *, record_table, record_id,
                       meaning, signer_username):
    sig = cur.execute(
        """SELECT id FROM e_signatures
           WHERE id = ? AND record_table = ? AND record_id = ?
             AND meaning = ? AND signer_username = ?""",
        (int(signature_id), record_table, str(record_id), meaning, signer_username),
    ).fetchone()
    return sig is not None


@bp.route("/api/brd/ebr", methods=["POST"])
def iniciar_ebr():
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    mbr_id = body.get("mbr_template_id")
    lote = (body.get("lote") or "").strip()
    if not mbr_id or not lote:
        return jsonify({"error": "mbr_template_id y lote requeridos"}), 400

    conn = get_db()
    cur = conn.cursor()
    mbr = cur.execute(
        """SELECT id, producto_nombre, version, estado, lote_size_g
           FROM mbr_templates WHERE id = ?""", (int(mbr_id),),
    ).fetchone()
    if not mbr:
        return jsonify({"error": "MBR no encontrado"}), 404
    if mbr["estado"] != "aprobado":
        return jsonify({
            "error": f"solo MBR aprobado puede instanciar EBR (actual: {mbr['estado']})",
        }), 409

    if cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote = ?", (lote,)).fetchone():
        return jsonify({"error": f"lote '{lote}' ya tiene un EBR"}), 409

    try:
        cantidad_obj = float(body.get("cantidad_objetivo_g") or mbr["lote_size_g"])
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_objetivo_g inválida"}), 400

    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_ejecuciones
             (mbr_template_id, mbr_version, produccion_id, lote, estado,
              iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas)
           VALUES (?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?)""",
        (mbr["id"], mbr["version"], body.get("produccion_id"), lote,
         user, cantidad_obj, (body.get("notas") or "").strip()),
    )
    ebr_id = cur.lastrowid

    pasos_mbr = cur.execute(
        """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                  requiere_e_sign, requiere_qc
           FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr["id"],),
    ).fetchall()
    for p in pasos_mbr:
        cur.execute(
            """INSERT INTO ebr_pasos_ejecutados
                 (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                  equipo_requerido, requiere_e_sign, requiere_qc, estado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente')""",
            (ebr_id, p["id"], p["orden"], p["descripcion"], p["tipo_paso"],
             p["equipo_requerido"], p["requiere_e_sign"], p["requiere_qc"]),
        )
    conn.commit()
    audit_log(cur, usuario=user, accion="INICIAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"mbr_template_id": mbr["id"], "lote": lote,
                        "pasos_clonados": len(pasos_mbr)})
    return jsonify({"ok": True, "id": ebr_id, "pasos": len(pasos_mbr)}), 201


@bp.route("/api/brd/ebr", methods=["GET"])
def listar_ebr():
    err = _require_login()
    if err:
        return err
    estado = (request.args.get("estado") or "").strip()
    lote = (request.args.get("lote") or "").strip()
    where, params = [], []
    if estado:
        where.append("estado = ?")
        params.append(estado)
    if lote:
        where.append("lote = ?")
        params.append(lote)
    sql = """SELECT id, mbr_template_id, mbr_version, produccion_id, lote,
                    estado, iniciado_por, iniciado_at_utc, completado_at_utc,
                    liberado_por, liberado_at_utc, liberado_signature_id,
                    rechazado_motivo, cantidad_objetivo_g, cantidad_real_g,
                    yield_pct, notas
             FROM ebr_ejecuciones"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY iniciado_at_utc DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_ebr_to_dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>", methods=["GET"])
def detalle_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM ebr_ejecuciones WHERE id = ?""", (ebr_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "EBR no encontrado"}), 404
    pasos = conn.execute(
        """SELECT * FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? ORDER BY orden""", (ebr_id,),
    ).fetchall()
    return jsonify(_ebr_to_dict(row, pasos))


@bp.route("/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/iniciar", methods=["POST"])
def iniciar_paso_ebr(ebr_id, orden):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    paso = cur.execute(
        """SELECT id, estado FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND orden = ?""", (ebr_id, orden),
    ).fetchone()
    if not paso:
        return jsonify({"error": "paso no encontrado"}), 404
    if paso["estado"] != "pendiente":
        return jsonify({"error": f"paso ya iniciado (estado: {paso['estado']})"}), 409

    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE ebr_pasos_ejecutados
             SET estado = 'en_proceso',
                 operario_username = ?,
                 iniciado_at_utc = datetime('now', 'utc')
           WHERE id = ?""",
        (user, paso["id"]),
    )
    cur.execute(
        """UPDATE ebr_ejecuciones SET estado = 'en_proceso'
           WHERE id = ? AND estado = 'iniciado'""", (ebr_id,),
    )
    conn.commit()
    return jsonify({"ok": True, "estado": "en_proceso"})


@bp.route("/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/completar", methods=["POST"])
def completar_paso_ebr(ebr_id, orden):
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    observaciones = (body.get("observaciones") or "").strip()[:500]
    signature_id = body.get("signature_id")
    qc_signature_id = body.get("qc_signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    paso = cur.execute(
        """SELECT id, estado, requiere_e_sign, requiere_qc, operario_username
           FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND orden = ?""", (ebr_id, orden),
    ).fetchone()
    if not paso:
        return jsonify({"error": "paso no encontrado"}), 404
    if paso["estado"] not in ("en_proceso", "pendiente"):
        return jsonify({"error": f"paso ya completado (estado: {paso['estado']})"}), 409

    user = session.get("compras_user", "")

    if paso["requiere_e_sign"]:
        if not signature_id:
            return jsonify({
                "error": "paso requiere e-signature · meaning='ejecuta' "
                          "record_table='ebr_pasos_ejecutados'",
                "paso_id": paso["id"],
            }), 400
        if not _validar_signature(
            cur, signature_id, record_table="ebr_pasos_ejecutados",
            record_id=paso["id"], meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido para este paso"}), 400

    qc_username = ""
    if paso["requiere_qc"]:
        if not qc_signature_id:
            return jsonify({
                "error": "paso requiere QC e-signature · meaning='supervisa'",
            }), 400
        qc_sig = cur.execute(
            """SELECT signer_username FROM e_signatures
               WHERE id = ? AND record_table = 'ebr_pasos_ejecutados'
                 AND record_id = ? AND meaning = 'supervisa'""",
            (int(qc_signature_id), str(paso["id"])),
        ).fetchone()
        if not qc_sig:
            return jsonify({"error": "qc_signature_id inválido"}), 400
        qc_username = qc_sig["signer_username"]

    op_username = paso["operario_username"] or user
    cur.execute(
        """UPDATE ebr_pasos_ejecutados
             SET estado = 'completado',
                 operario_username = ?,
                 iniciado_at_utc = COALESCE(iniciado_at_utc, datetime('now', 'utc')),
                 completado_at_utc = datetime('now', 'utc'),
                 observaciones = ?,
                 e_sign_id = ?,
                 qc_username = ?,
                 qc_e_sign_id = ?
           WHERE id = ?""",
        (op_username, observaciones,
         int(signature_id) if signature_id else None,
         qc_username,
         int(qc_signature_id) if qc_signature_id else None,
         paso["id"]),
    )
    conn.commit()
    return jsonify({"ok": True, "estado": "completado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/completar", methods=["POST"])
def completar_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        cantidad_real = float(body.get("cantidad_real_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_real_g inválida"}), 400
    if cantidad_real <= 0:
        return jsonify({"error": "cantidad_real_g debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, cantidad_objetivo_g FROM ebr_ejecuciones WHERE id = ?",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no completable (estado: {ebr['estado']})"}), 409

    pendientes = cur.execute(
        """SELECT COUNT(*) FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND estado NOT IN ('completado', 'omitido')""",
        (ebr_id,),
    ).fetchone()[0]
    if pendientes:
        return jsonify({"error": f"hay {pendientes} paso(s) sin completar"}), 409

    yield_pct = round((cantidad_real / ebr["cantidad_objetivo_g"]) * 100, 2) if ebr["cantidad_objetivo_g"] else None
    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'completado',
                 completado_at_utc = datetime('now', 'utc'),
                 cantidad_real_g = ?,
                 yield_pct = ?
           WHERE id = ?""",
        (cantidad_real, yield_pct, ebr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="COMPLETAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"cantidad_real_g": cantidad_real, "yield_pct": yield_pct})
    return jsonify({"ok": True, "estado": "completado", "yield_pct": yield_pct})


@bp.route("/api/brd/ebr/<int:ebr_id>/liberar", methods=["POST"])
def liberar_ebr(ebr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    if not signature_id:
        return jsonify({
            "error": "signature_id requerido · meaning='libera' record_table='ebr_ejecuciones'",
        }), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("completado", "en_revision_qc"):
        return jsonify({"error": f"solo completado puede liberarse (actual: {ebr['estado']})"}), 409

    user = session.get("compras_user", "")
    if not _validar_signature(
        cur, signature_id, record_table="ebr_ejecuciones",
        record_id=ebr_id, meaning="libera", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a una firma 'libera' de este EBR por vos"}), 400

    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'liberado',
                 liberado_por = ?,
                 liberado_at_utc = datetime('now', 'utc'),
                 liberado_signature_id = ?
           WHERE id = ?""",
        (user, int(signature_id), ebr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="LIBERAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"liberado_por": user, "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "liberado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/rechazar", methods=["POST"])
def rechazar_ebr(ebr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()
    signature_id = body.get("signature_id")
    if not motivo:
        return jsonify({"error": "motivo requerido"}), 400
    if not signature_id:
        return jsonify({"error": "signature_id requerido (meaning='rechaza')"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("completado", "en_revision_qc"):
        return jsonify({"error": f"solo completado puede rechazarse (actual: {ebr['estado']})"}), 409

    user = session.get("compras_user", "")
    if not _validar_signature(
        cur, signature_id, record_table="ebr_ejecuciones",
        record_id=ebr_id, meaning="rechaza", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a una firma 'rechaza' de este EBR por vos"}), 400

    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'rechazado',
                 rechazado_motivo = ?
           WHERE id = ?""",
        (motivo, ebr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="RECHAZAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"motivo": motivo, "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "rechazado"})
