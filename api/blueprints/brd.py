"""Blueprint brd · Batch Record Digital (MBR + EBR + IPCs + cleaning + pesajes).

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
from flask import Blueprint, Response, jsonify, request, session

from database import get_db
from config import ADMIN_USERS, CALIDAD_USERS, PLANTA_USERS
try:
    from config import EBR_MODE
except ImportError:  # deploy-safe
    EBR_MODE = "off"
from audit_helpers import audit_log

bp = Blueprint("brd", __name__)
log = logging.getLogger("brd")


# ── UI dashboard (read-only listings) ──────────────────────────────────────

@bp.route("/brd", methods=["GET"])
@bp.route("/brd/", methods=["GET"])
def brd_dashboard():
    """UI dashboard read-only del BRD. Listados de MBR/EBR/Cleaning con
    drill-down a detalle. Acciones (crear, firmar, ejecutar) vía API."""
    if not session.get("compras_user"):
        return Response("No autorizado · login requerido", status=401)
    from templates_py.brd_html import render_brd_dashboard
    return Response(render_brd_dashboard(), mimetype="text/html")

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


def _require_brd_ejecutor():
    """Solo personal que ejecuta lotes: Planta, Calidad o Admin. Evita que
    un usuario de otra área (compras, marketing, RRHH...) ejecute pasos de
    un registro de lote regulado (INVIMA · escalada de privilegios)."""
    u = session.get("compras_user", "")
    if not u:
        return jsonify({"error": "No autorizado"}), 401
    if u not in (PLANTA_USERS | CALIDAD_USERS | ADMIN_USERS):
        return jsonify({"error": "Solo Planta/Calidad/Admin pueden ejecutar pasos del registro de lote"}), 403
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


def assign_numero_op(c, year=None):
    """Genera atómicamente el siguiente numero_op MyBatch-compat.

    Format: 'OP-YYYY-NNNN' (4 dígitos zero-padded).

    Usa tabla op_counters (mig 117) como counter atómico por año. SQLite WAL
    serializa los writes · safe ante races concurrentes (worker A y B
    bloquean uno al otro mientras hacen UPDATE op_counters).

    Reset implícito de año: la primera vez que se llama con un año nuevo
    se inserta fila counter=0 y arranca en 1. No hay reset manual.

    El cursor debe ser de una transacción viva (caller debe hacer commit
    después de la INSERT INTO ebr_ejecuciones que use el numero_op
    retornado · si rollback, op_counters queda con el counter incrementado
    pero ese numero queda sin uso · es comportamiento aceptable porque
    Part 11 no exige numeros contiguos, solo únicos).
    """
    if year is None:
        from datetime import datetime as _dt, timezone as _tz
        year = _dt.now(_tz.utc).year
    c.execute(
        "INSERT OR IGNORE INTO op_counters (year, counter) VALUES (?, 0)",
        (year,),
    )
    c.execute(
        """UPDATE op_counters
           SET counter = counter + 1,
               updated_at_utc = datetime('now', 'utc')
           WHERE year = ?""",
        (year,),
    )
    counter = c.execute(
        "SELECT counter FROM op_counters WHERE year = ?", (year,),
    ).fetchone()[0]
    return f"OP-{year}-{counter:04d}"


# ── endpoints ───────────────────────────────────────────────────────────────

@bp.route("/api/brd/cuarentena-explicita", methods=["GET"])
def brd_cuarentena_explicita():
    """MyBatch parity Sprint E · 21-may-2026 · Estado cuarentena explícito.

    Lista TODOS los EBRs en cuarentena (completados pero no liberados):
    - lote · producto · fecha completado · días en cuarentena
    - flag bandera_roja si >7 días sin liberar
    - acción: link al detalle + botón liberar/rechazar visible
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    try:
        # FIX · 21-may-2026 · usar COALESCE(lote_codigo, lote) + COALESCE(operario, iniciado_por)
        # · compat con BD sin mig 153 aplicada (aliases nuevos)
        rows = conn.execute(
            """SELECT e.id,
                      COALESCE(e.lote_codigo, e.lote) AS lote_codigo,
                      e.completado_at_utc,
                      COALESCE(e.operario, e.iniciado_por) AS operario,
                      mb.producto_nombre,
                      julianday('now','-5 hours') - julianday(e.completado_at_utc) as dias
               FROM ebr_ejecuciones e
               LEFT JOIN mbr_templates mb ON mb.id = e.mbr_template_id
               WHERE e.estado = 'completado'
                 AND e.completado_at_utc IS NOT NULL
                 AND (e.liberado_at_utc IS NULL OR e.liberado_at_utc = '')
                 AND (COALESCE(e.rechazado_at_utc,'') = '')
               ORDER BY e.completado_at_utc ASC""",
        ).fetchall()
    except Exception as e:
        return jsonify({'error': f'query fallo: {e}'}), 500
    items = []
    bandera_roja_count = 0
    for r in rows:
        dias = round(float(r[5] or 0), 1) if r[5] else 0
        bandera = dias > 7
        if bandera:
            bandera_roja_count += 1
        items.append({
            'ebr_id': r[0], 'lote': r[1] or '',
            'completado_at_utc': r[2] or '',
            'operario': r[3] or '',
            'producto': r[4] or '',
            'dias_en_cuarentena': dias,
            'bandera_roja': bandera,
        })
    # Estadísticas adicionales: rechazados últimos 30d
    rechazados_30d = 0
    try:
        # FIX · 21-may-2026 · cutoff Python (date multi-arg falla en PG)
        from datetime import datetime as _dtbrd2, timedelta as _tdbrd2
        cutoff_30d = (_dtbrd2.now() - _tdbrd2(days=30)).date().isoformat()
        rechazados_30d = int((conn.execute(
            """SELECT COUNT(*) FROM ebr_ejecuciones
               WHERE COALESCE(rechazado_at_utc,'') != ''
                 AND date(rechazado_at_utc) >= ?""",
            (cutoff_30d,),
        ).fetchone() or [0])[0])
    except Exception:
        pass
    return jsonify({
        'items': items,
        'total_cuarentena': len(items),
        'bandera_roja_count': bandera_roja_count,
        'rechazados_30d': rechazados_30d,
    })


@bp.route("/api/brd/dashboard-estados", methods=["GET"])
def brd_dashboard_estados():
    """MyBatch parity Sprint A · 21-may-2026 · Sebastián.

    Reemplaza la pantalla INICIO de MyBatch · muestra:
    - Counts de MBRs por estado (draft / en_revision / aprobado / obsoleto)
    - Counts de EBRs (ejecuciones) por estado (iniciado / en_curso / completado)
    - Productos sin MBR aprobado (gap crítico)
    - Próximos vencimientos de MBR (>6 meses sin revisión)
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    out = {'mbr': {}, 'ebr': {}, 'gaps': [], 'vencimientos': []}
    # MBR por estado
    try:
        rows = conn.execute(
            "SELECT estado, COUNT(*) FROM mbr_templates GROUP BY estado",
        ).fetchall()
        for r in rows:
            out['mbr'][r[0] or 'sin_estado'] = int(r[1] or 0)
    except Exception:
        pass
    # Total productos vs productos con MBR aprobado
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM formula_headers WHERE COALESCE(activo,1)=1",
        ).fetchone()
        con_mbr = conn.execute(
            """SELECT COUNT(DISTINCT fh.producto_nombre)
               FROM formula_headers fh
               JOIN mbr_templates mb ON mb.producto_nombre = fh.producto_nombre
                                    AND mb.estado = 'aprobado'
               WHERE COALESCE(fh.activo,1)=1""",
        ).fetchone()
        out['productos_total'] = int(total[0] or 0) if total else 0
        out['productos_con_mbr_aprobado'] = int(con_mbr[0] or 0) if con_mbr else 0
        out['cobertura_pct'] = round(
            (out['productos_con_mbr_aprobado'] / out['productos_total'] * 100)
            if out['productos_total'] else 0, 1
        )
    except Exception:
        out['productos_total'] = 0
        out['productos_con_mbr_aprobado'] = 0
        out['cobertura_pct'] = 0
    # Productos SIN MBR aprobado (gap)
    try:
        rows = conn.execute(
            """SELECT fh.producto_nombre
               FROM formula_headers fh
               WHERE COALESCE(fh.activo,1)=1
                 AND fh.producto_nombre NOT IN (
                   SELECT producto_nombre FROM mbr_templates WHERE estado='aprobado'
                 )
               ORDER BY fh.producto_nombre LIMIT 20""",
        ).fetchall()
        out['gaps'] = [r[0] for r in rows]
    except Exception:
        pass
    # EBR ejecuciones por estado
    try:
        rows = conn.execute(
            "SELECT estado, COUNT(*) FROM ebr_ejecuciones GROUP BY estado",
        ).fetchall()
        for r in rows:
            out['ebr'][r[0] or 'sin_estado'] = int(r[1] or 0)
    except Exception:
        pass
    # MBR aprobados hace >180d sin revisión
    try:
        rows = conn.execute(
            """SELECT producto_nombre, version, aprobado_at_utc
               FROM mbr_templates
               WHERE estado='aprobado'
                 AND COALESCE(aprobado_at_utc,'') != ''
                 AND date(aprobado_at_utc) < date('now','-180 days')
               ORDER BY aprobado_at_utc ASC LIMIT 20""",
        ).fetchall()
        out['vencimientos'] = [
            {'producto': r[0], 'version': r[1], 'aprobado': r[2]}
            for r in rows
        ]
    except Exception:
        pass
    return jsonify(out)


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
    audit_log(cur, usuario=session.get("compras_user", ""), accion="AGREGAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id,
              despues={"mbr_id": mbr_id, "orden": siguiente_orden,
                       "descripcion": descripcion[:120]})
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
    audit_log(cur, usuario=session.get("compras_user", ""), accion="EDITAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id, despues=cambios)
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
    audit_log(cur, usuario=session.get("compras_user", ""), accion="BORRAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id, detalle=f"MBR {mbr_id}")
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
        "numero_op": row["numero_op"] if "numero_op" in row.keys() else None,
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
        # fase del legajo · defensivo: SELECTs viejos pueden no traer la columna
        "fase": (row["fase"] if "fase" in row.keys() and row["fase"] else "fabricacion"),
        # puente OP→OF · defensivo
        "densidad_g_ml": (row["densidad_g_ml"] if "densidad_g_ml" in row.keys() else None),
        "ml_envasable": (row["ml_envasable"] if "ml_envasable" in row.keys() else None),
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
        # fase del paso · defensivo (SELECTs viejos pueden no traer la columna)
        "fase": (row["fase"] if "fase" in row.keys() and row["fase"] else ""),
    }


# Fases del motor EBR único (reemplazo MyBatch · OP/OF/OA comparten esqueleto).
_FASES_VALIDAS = {"fabricacion", "envasado", "acondicionamiento"}


def _fase_canonica(label):
    """Normaliza la etiqueta libre de fase de un paso de MBR (p.ej.
    'Dispensación', 'Fabricación', 'Envasado', 'Acondicionamiento/Etiquetado')
    a la fase canónica del EBR (fabricacion/envasado/acondicionamiento).

    Batch B (audit 3-jun) · el motor EBR es por fase: un EBR de envasado debe
    clonar SOLO los pasos de envasado, no los de fabricación. Todo lo que no sea
    claramente envasado/acondicionamiento cuenta como 'fabricacion' (default
    seguro · preserva el comportamiento actual de los MBR de una sola fase)."""
    s = (label or "").strip().lower()
    # quitar acentos básicos
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        s = s.replace(a, b)
    if any(k in s for k in ("acondi", "etiqu", "codif", "empaqu", "estuch", "arte")):
        return "acondicionamiento"
    if any(k in s for k in ("envas", "llen", "sell", "tapad")):
        return "envasado"
    return "fabricacion"


def _validar_signature(cur, signature_id, *, record_table, record_id,
                       meaning, signer_username):
    sig = cur.execute(
        """SELECT id FROM e_signatures
           WHERE id = ? AND record_table = ? AND record_id = ?
             AND meaning = ? AND signer_username = ?""",
        (int(signature_id), record_table, str(record_id), meaning, signer_username),
    ).fetchone()
    return sig is not None


def crear_ebr_desde_mbr(cur, *, producto_nombre, lote, produccion_id=None,
                        cantidad_objetivo_g=None, usuario='', notas='',
                        fase='fabricacion'):
    """Crea (o reusa) un EBR para un lote desde el MBR APROBADO del producto.

    Reutilizable fuera de brd.py (p.ej. hook de aceptar producción en planta ·
    reemplazo de MyBatch fase 1). NO hace commit ni audit_log: el caller maneja
    la transacción y la auditoría. Usa índices posicionales (no row['k']) para
    funcionar con cualquier row_factory del cursor del caller.

    Returns dict:
      {ok:True, id, numero_op, pasos}            · EBR creado
      {ok:True, id, numero_op, reusado:True}     · ya existía para esa producción
      {ok:False, error:'NO_MBR_APROBADO'|'LOTE_DUPLICADO', detail}
    """
    # Idempotencia por (produccion_id, lote): re-aceptar reusa el legajo de ESE
    # lote. Batch C · multi-lote: una producción con lotes>1 crea N legajos (uno
    # por lote físico, lotes distintos), cada uno idempotente por su código.
    if produccion_id is not None:
        ex = cur.execute(
            "SELECT id, numero_op FROM ebr_ejecuciones WHERE produccion_id=? AND lote=?",
            (produccion_id, lote),
        ).fetchone()
        if ex:
            return {'ok': True, 'id': ex[0], 'numero_op': ex[1],
                    'pasos': 0, 'reusado': True}
    # MBR aprobado más reciente del producto (BPM: no se fabrica sin MBR aprobado).
    mbr = cur.execute(
        """SELECT id, version, lote_size_g
             FROM mbr_templates
            WHERE producto_nombre=? AND estado='aprobado'
            ORDER BY version DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if not mbr:
        return {'ok': False, 'error': 'NO_MBR_APROBADO',
                'detail': f"No hay MBR aprobado para '{producto_nombre}'"}
    if cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone():
        return {'ok': False, 'error': 'LOTE_DUPLICADO',
                'detail': f"el lote '{lote}' ya tiene un EBR"}
    cant = cantidad_objetivo_g if cantidad_objetivo_g is not None else mbr[2]
    numero_op = assign_numero_op(cur)
    cur.execute(
        """INSERT INTO ebr_ejecuciones
             (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
              estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
              fase)
           VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?)""",
        (mbr[0], mbr[1], produccion_id, lote, numero_op, usuario,
         float(cant or 0), notas,
         (fase if fase in _FASES_VALIDAS else 'fabricacion')),
    )
    ebr_id = cur.lastrowid
    _fase_ebr = fase if fase in _FASES_VALIDAS else 'fabricacion'
    pasos = cur.execute(
        """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                  requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
             FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden""",
        (mbr[0],),
    ).fetchall()
    # Batch B · clonar SOLO los pasos de la fase del EBR (un EBR de envasado no
    # debe traer los pasos de fabricación, y viceversa).
    n_clonados = 0
    for p in pasos:
        if _fase_canonica(p[7]) != _fase_ebr:
            continue
        cur.execute(
            """INSERT INTO ebr_pasos_ejecutados
                 (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                  equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
            (ebr_id, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]),
        )
        n_clonados += 1
    return {'ok': True, 'id': ebr_id, 'numero_op': numero_op, 'pasos': n_clonados}


def _generar_mbr_desde_formula(cur, producto_nombre, usuario=''):
    """Crea un MBR borrador a partir de la fórmula EXISTENTE del producto.

    Reemplazo MyBatch · las fórmulas ya viven en EOS (formula_headers/items), así
    que no se re-ingresa la receta: el MBR se vincula a la fórmula
    (formula_version_id = formula_headers.id) y genera un paso de dispensación
    por componente + un paso de mezcla. El usuario revisa, agrega IPCs y aprueba.
    NO commitea. Idempotente: si el producto ya tiene un MBR no-obsoleto, lo reusa.

    Returns dict: {ok, id, version, pasos, lote_size_g} | {ok, id, estado, ya_existe}
                  | {ok:False, error:'SIN_FORMULA'}
    """
    # No duplicar: si ya hay un MBR vigente (draft/en_revision/aprobado), reusar.
    ex = cur.execute(
        """SELECT id, estado, version FROM mbr_templates
            WHERE producto_nombre=? AND COALESCE(estado,'') != 'obsoleto'
            ORDER BY version DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if ex:
        return {'ok': True, 'id': ex[0], 'estado': ex[1], 'version': ex[2],
                'ya_existe': True}
    # Fórmula activa del producto (la receta ya existe en EOS).
    fh = cur.execute(
        """SELECT id, COALESCE(lote_size_kg,0), COALESCE(unidad_base_g,0)
             FROM formula_headers
            WHERE producto_nombre=? AND COALESCE(activo,1)=1
            ORDER BY id DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if not fh:
        return {'ok': False, 'error': 'SIN_FORMULA',
                'detail': f"'{producto_nombre}' no tiene fórmula activa"}
    formula_id = fh[0]
    items = cur.execute(
        """SELECT material_nombre, material_id, COALESCE(porcentaje,0),
                  COALESCE(cantidad_g_por_lote,0)
             FROM formula_items WHERE producto_nombre=?
            ORDER BY cantidad_g_por_lote DESC""",
        (producto_nombre,),
    ).fetchall()
    # Tamaño de lote en g: lote_size_kg*1000, o unidad_base_g, o suma de componentes.
    lote_size_g = fh[1] * 1000.0 or fh[2] or sum(float(i[3] or 0) for i in items)
    if lote_size_g <= 0:
        lote_size_g = 1000.0  # fallback razonable; el usuario lo ajusta en draft
    version = _next_version(cur, producto_nombre)
    cur.execute(
        """INSERT INTO mbr_templates
             (producto_nombre, formula_version_id, version, estado, lote_size_g, creado_por)
           VALUES (?, ?, ?, 'draft', ?, ?)""",
        (producto_nombre, formula_id, version, float(lote_size_g), usuario),
    )
    mbr_id = cur.lastrowid
    orden = 0
    for it in items:
        orden += 1
        mat_nom, mat_id, pct, cant_g = it[0], it[1], it[2], it[3]
        desc = f"Dispensar {mat_nom or mat_id} ({mat_id}) — {round(float(cant_g or 0),2)} g ({round(float(pct or 0),2)}%)"
        cur.execute(
            """INSERT INTO mbr_pasos
                 (mbr_template_id, orden, fase, descripcion, tipo_paso,
                  requiere_e_sign, requiere_qc)
               VALUES (?, ?, 'Dispensación', ?, 'dispensacion', 1, 0)""",
            (mbr_id, orden, desc),
        )
    # Paso de mezcla/homogenización tras la dispensación.
    orden += 1
    cur.execute(
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              requiere_e_sign, requiere_qc)
           VALUES (?, ?, 'Fabricación', 'Mezcla y homogenización del granel', 'mezclado', 1, 0)""",
        (mbr_id, orden),
    )
    # Batch B · pasos genéricos de Envasado (OF) y Acondicionamiento (OA), para
    # que el EBR de cada fase tenga un esqueleto editable (el usuario los ajusta
    # por producto en el draft). Sin esto, un EBR de OF/OA nacería vacío.
    _pasos_fase = [
        ('Envasado', 'Alistamiento de envase/tapa (verificar limpieza y especificación)', 'envasado'),
        ('Envasado', 'Llenado y control de peso/volumen', 'envasado'),
        ('Envasado', 'Sellado/tapado', 'envasado'),
        ('Acondicionamiento', 'Aprobación de arte/etiqueta y codificación (lote/vencimiento)', 'acondicionamiento'),
        ('Acondicionamiento', 'Etiquetado', 'acondicionamiento'),
        ('Acondicionamiento', 'Encajado / empaque secundario', 'acondicionamiento'),
    ]
    for _et, _desc, _tipo in _pasos_fase:
        orden += 1
        cur.execute(
            """INSERT INTO mbr_pasos
                 (mbr_template_id, orden, fase, descripcion, tipo_paso,
                  requiere_e_sign, requiere_qc)
               VALUES (?, ?, ?, ?, ?, 1, 0)""",
            (mbr_id, orden, _et, _desc, _tipo),
        )
    return {'ok': True, 'id': mbr_id, 'version': version, 'pasos': orden,
            'lote_size_g': float(lote_size_g)}


@bp.route("/api/brd/mbr/generar-desde-formula", methods=["POST"])
def mbr_generar_desde_formula():
    """Genera un MBR borrador desde la fórmula de UN producto. Body: {producto_nombre}."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede generar MBR"}), 403
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    conn = get_db(); cur = conn.cursor()
    res = _generar_mbr_desde_formula(cur, producto, usuario=user)
    if not res.get("ok"):
        return jsonify(res), 404
    if not res.get("ya_existe"):
        audit_log(cur, usuario=user, accion="GENERAR_MBR_DESDE_FORMULA",
                  tabla="mbr_templates", registro_id=res["id"],
                  despues={"producto": producto, "version": res.get("version"),
                            "pasos": res.get("pasos")})
    conn.commit()
    return jsonify(res), (200 if res.get("ya_existe") else 201)


@bp.route("/api/brd/mbr/generar-todas-desde-formulas", methods=["POST"])
def mbr_generar_todas_desde_formulas():
    """Genera MBR borrador para TODAS las fórmulas activas sin MBR vigente (bulk).

    Idempotente: salta productos que ya tienen MBR no-obsoleto. Devuelve resumen.
    """
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede generar MBR"}), 403
    conn = get_db(); cur = conn.cursor()
    productos = [r[0] for r in cur.execute(
        """SELECT DISTINCT producto_nombre FROM formula_headers
            WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
              AND TRIM(producto_nombre) != ''
            ORDER BY producto_nombre""",
    ).fetchall()]
    creados, reusados, sin_formula = [], [], []
    for p in productos:
        res = _generar_mbr_desde_formula(cur, p, usuario=user)
        if not res.get("ok"):
            sin_formula.append(p)
        elif res.get("ya_existe"):
            reusados.append(p)
        else:
            creados.append({"producto": p, "mbr_id": res["id"], "pasos": res.get("pasos")})
            audit_log(cur, usuario=user, accion="GENERAR_MBR_DESDE_FORMULA",
                      tabla="mbr_templates", registro_id=res["id"],
                      despues={"producto": p, "version": res.get("version"),
                                "pasos": res.get("pasos"), "bulk": True})
    conn.commit()
    return jsonify({
        "ok": True,
        "total_formulas": len(productos),
        "mbr_creados": len(creados),
        "ya_tenian_mbr": len(reusados),
        "sin_formula": sin_formula,
        "creados": creados,
        "nota": "MBR creados en DRAFT · revisá pasos, agregá IPCs y aprobá cada uno "
                "(la aprobación exige e-firma). Recién ahí EBR_MODE=strict los usará.",
    }), 201


def _get_or_create_draft_mbr(cur, producto, usuario=''):
    """Devuelve (mbr_id, creado) de un MBR DRAFT editable para el producto.
    Si el último MBR vigente es draft → lo reusa. Si está aprobado/en_revisión →
    crea una NUEVA versión draft (para no pisar el aprobado · BPM versionado).
    Si no existe ninguno → crea uno draft vinculado a la fórmula activa.
    Integración MyBatch · 2-jun-2026 · editar procedimiento/IPC desde Fórmulas."""
    row = cur.execute(
        "SELECT id, estado, version FROM mbr_templates "
        "WHERE producto_nombre=? AND COALESCE(estado,'')!='obsoleto' "
        "ORDER BY version DESC LIMIT 1", (producto,)).fetchone()
    if row and row["estado"] == "draft":
        return row["id"], False
    fh = cur.execute(
        "SELECT id AS fid, COALESCE(lote_size_kg,0) AS lk, COALESCE(unidad_base_g,0) AS ub "
        "FROM formula_headers WHERE producto_nombre=? AND COALESCE(activo,1)=1 "
        "ORDER BY id DESC LIMIT 1", (producto,)).fetchone()
    formula_id = fh["fid"] if fh else None
    lote_size_g = ((fh["lk"] if fh else 0) or 0) * 1000.0 or (fh["ub"] if fh else 0) or 1000.0
    version = _next_version(cur, producto)
    cur.execute(
        "INSERT INTO mbr_templates (producto_nombre, formula_version_id, version, estado, lote_size_g, creado_por) "
        "VALUES (?,?,?,'draft',?,?)", (producto, formula_id, version, float(lote_size_g), usuario))
    return cur.lastrowid, True


@bp.route("/api/brd/mbr/por-producto", methods=["GET"])
def mbr_por_producto():
    """Devuelve el MBR vigente (procedimiento + IPC) de un producto · para precargar
    el editor de Fórmulas. ?producto=NOMBRE."""
    err = _require_login()
    if err:
        return err
    producto = (request.args.get("producto") or "").strip()
    if not producto:
        return jsonify({"error": "producto requerido"}), 400
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT id, estado, version FROM mbr_templates "
        "WHERE producto_nombre=? AND COALESCE(estado,'')!='obsoleto' "
        "ORDER BY version DESC LIMIT 1", (producto,)).fetchone()
    if not row:
        return jsonify({"ok": True, "existe": False, "pasos": [], "ipc": []})
    mbr_id = row["id"]
    pasos = [{"orden": p["orden"], "descripcion": p["descripcion"],
              "fase": p["fase"], "resultado_label": p["notas"]}
             for p in cur.execute(
                 "SELECT orden, descripcion, COALESCE(fase,'') fase, COALESCE(notas,'') notas "
                 "FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden", (mbr_id,)).fetchall()]
    ipc = [{"parametro": s["parametro"], "unidad": s["unidad"],
            "valor_min": s["valor_min"], "valor_max": s["valor_max"],
            "especificacion": s["notas"]}
           for s in cur.execute(
               "SELECT parametro, COALESCE(unidad,'') unidad, valor_min, valor_max, COALESCE(notas,'') notas "
               "FROM ipc_specs WHERE mbr_template_id=?", (mbr_id,)).fetchall()]
    return jsonify({"ok": True, "existe": True, "mbr_id": mbr_id,
                    "estado": row["estado"], "version": row["version"],
                    "pasos": pasos, "ipc": ipc})


@bp.route("/api/brd/mbr/sync-procedimiento", methods=["POST"])
def mbr_sync_procedimiento():
    """Guarda el PROCEDIMIENTO (pasos de fabricación) + IPC de un producto como su
    MBR draft · lo usa el editor de Fórmulas (integración MyBatch · el procedimiento
    vive junto a la receta). Reemplaza pasos/IPC del draft. NO aprueba (eso exige
    e-firma vía /aprobar). Body: {producto_nombre, pasos:[{descripcion,fase?,
    resultado_label?,tipo_paso?}], ipc:[{parametro,unidad?,valor_min?,valor_max?,
    especificacion?,metodo?}]}."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede editar el MBR"}), 403
    b = request.get_json(silent=True) or {}
    producto = (b.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    pasos = b.get("pasos") or []
    ipc = b.get("ipc") or []
    conn = get_db(); cur = conn.cursor()
    mbr_id, creado = _get_or_create_draft_mbr(cur, producto, user)
    # reemplazar procedimiento (pasos)
    cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (mbr_id,))
    orden = 0
    for p in pasos:
        desc = (p.get("descripcion") or "").strip()
        if not desc:
            continue
        orden += 1
        tipo = (p.get("tipo_paso") or "mezclado").strip().lower()
        if tipo not in VALID_TIPO_PASO:
            tipo = "otro"
        cur.execute(
            "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, "
            "requiere_e_sign, requiere_qc, notas) VALUES (?,?,?,?,?,1,0,?)",
            (mbr_id, orden, (p.get("fase") or "Fabricación").strip(), desc, tipo,
             (p.get("resultado_label") or "").strip()))
    # reemplazar IPC
    cur.execute("DELETE FROM ipc_specs WHERE mbr_template_id=?", (mbr_id,))

    def _f(v):
        try:
            return float(v) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None
    n_ipc = 0
    for s in ipc:
        par = (s.get("parametro") or "").strip()
        if not par:
            continue
        n_ipc += 1
        cur.execute(
            "INSERT INTO ipc_specs (mbr_template_id, parametro, unidad, valor_min, valor_max, "
            "metodo, obligatorio, notas) VALUES (?,?,?,?,?,?,?,?)",
            (mbr_id, par, (s.get("unidad") or "").strip(), _f(s.get("valor_min")), _f(s.get("valor_max")),
             (s.get("metodo") or "").strip(), 1 if s.get("obligatorio", 1) else 0,
             (s.get("especificacion") or s.get("notas") or "").strip()))
    audit_log(cur, usuario=user, accion="SYNC_MBR_PROCEDIMIENTO", tabla="mbr_templates",
              registro_id=mbr_id, despues={"producto": producto, "n_pasos": orden,
                                           "n_ipc": n_ipc, "mbr_creado": creado})
    conn.commit()
    return jsonify({"ok": True, "mbr_id": mbr_id, "n_pasos": orden, "n_ipc": n_ipc,
                    "mbr_creado": creado})


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

    fase = (body.get("fase") or "fabricacion").strip().lower()
    if fase not in _FASES_VALIDAS:
        return jsonify({"error": f"fase inválida · use {sorted(_FASES_VALIDAS)}"}), 400

    # `lote` es UNIQUE a nivel BD (1 legajo por código de lote). Para que el
    # MISMO lote físico tenga legajo de fabricación/envasado/acondicionamiento,
    # el código de lote del EBR lleva sufijo de fase (·OF/·OA) y el lote físico
    # real se guarda en lote_codigo (vía asignar-lote-fisico). Batch B.
    if cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote = ?", (lote,)).fetchone():
        return jsonify({"error": f"lote '{lote}' ya tiene un EBR"}), 409

    try:
        cantidad_obj = float(body.get("cantidad_objetivo_g") or mbr["lote_size_g"])
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_objetivo_g inválida"}), 400

    user = session.get("compras_user", "")
    numero_op = assign_numero_op(cur)
    cur.execute(
        """INSERT INTO ebr_ejecuciones
             (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
              estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
              fase)
           VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?)""",
        (mbr["id"], mbr["version"], body.get("produccion_id"), lote, numero_op,
         user, cantidad_obj, (body.get("notas") or "").strip(), fase),
    )
    ebr_id = cur.lastrowid

    pasos_mbr = cur.execute(
        """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                  requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
           FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr["id"],),
    ).fetchall()
    # Batch B · clonar SOLO los pasos de la fase del EBR.
    n_clonados = 0
    for p in pasos_mbr:
        if _fase_canonica(p["fase"]) != fase:
            continue
        cur.execute(
            """INSERT INTO ebr_pasos_ejecutados
                 (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                  equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
            (ebr_id, p["id"], p["orden"], p["descripcion"], p["tipo_paso"],
             p["equipo_requerido"], p["requiere_e_sign"], p["requiere_qc"],
             p["fase"]),
        )
        n_clonados += 1
    conn.commit()
    audit_log(cur, usuario=user, accion="INICIAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"mbr_template_id": mbr["id"], "lote": lote,
                        "numero_op": numero_op, "fase": fase,
                        "pasos_clonados": n_clonados})
    return jsonify({"ok": True, "id": ebr_id, "numero_op": numero_op,
                     "pasos": n_clonados}), 201


@bp.route("/api/brd/ebr", methods=["GET"])
def listar_ebr():
    err = _require_login()
    if err:
        return err
    estado = (request.args.get("estado") or "").strip()
    lote = (request.args.get("lote") or "").strip()
    numero_op = (request.args.get("numero_op") or "").strip()
    fase = (request.args.get("fase") or "").strip().lower()
    where, params = [], []
    if estado:
        where.append("estado = ?")
        params.append(estado)
    if fase:
        # COALESCE → legajos viejos (fase NULL) cuentan como 'fabricacion'
        where.append("COALESCE(fase,'fabricacion') = ?")
        params.append(fase)
    if lote:
        where.append("lote = ?")
        params.append(lote)
    if numero_op:
        # Match exacto · MyBatch-compat
        where.append("numero_op = ?")
        params.append(numero_op)
    sql = """SELECT id, mbr_template_id, mbr_version, produccion_id, lote,
                    numero_op, estado, iniciado_por, iniciado_at_utc,
                    completado_at_utc, liberado_por, liberado_at_utc,
                    liberado_signature_id, rechazado_motivo,
                    cantidad_objetivo_g, cantidad_real_g, yield_pct, notas,
                    COALESCE(fase,'fabricacion') AS fase
             FROM ebr_ejecuciones"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY iniciado_at_utc DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_ebr_to_dict(r) for r in rows]})


@bp.route("/brd/timeline/<int:ebr_id>", methods=["GET"])
def brd_timeline_page(ebr_id):
    """MyBatch parity Sprint D · 21-may-2026 · Timeline visual del BR.

    Página HTML standalone con timeline cronológico de eventos del lote:
    pesajes · pasos · IPC · liberación · todo en orden temporal con
    badges de estado. Renderiza vista-completa pero como línea de tiempo.
    """
    err = _require_login()
    if err:
        return err
    html = '''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Timeline BR · ''' + str(ebr_id) + '''</title>
<style>
*{box-sizing:border-box;font-family:'Segoe UI',Roboto,sans-serif}
body{margin:0;background:#f1f5f9;padding:18px;color:#0f172a}
.wrap{max-width:900px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,.06)}
h1{color:#0f766e;margin:0 0 6px}
.subtitle{color:#64748b;font-size:13px;margin-bottom:20px}
.header-card{background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;font-size:13px}
.tl{position:relative;padding-left:38px;margin-top:14px}
.tl::before{content:'';position:absolute;left:14px;top:0;bottom:0;width:2px;background:#cbd5e1}
.evt{position:relative;margin-bottom:18px;padding:12px 14px;background:#fff;border:1px solid #e2e8f0;border-radius:8px}
.evt::before{content:'';position:absolute;left:-31px;top:14px;width:18px;height:18px;border-radius:50%;background:#fff;border:3px solid #cbd5e1}
.evt.ok::before{border-color:#16a34a;background:#dcfce7}
.evt.warn::before{border-color:#ca8a04;background:#fef3c7}
.evt.err::before{border-color:#dc2626;background:#fee2e2}
.evt.info::before{border-color:#0891b2;background:#cffafe}
.evt .ts{font-size:11px;color:#94a3b8;font-family:monospace}
.evt .tit{font-weight:700;font-size:14px;color:#0f172a;margin:3px 0}
.evt .det{font-size:12px;color:#475569;line-height:1.5}
.badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;margin-left:6px}
.b-ok{background:#dcfce7;color:#166534}
.b-warn{background:#fef3c7;color:#78350f}
.b-err{background:#fee2e2;color:#991b1b}
</style></head><body>
<div class="wrap">
<h1>📜 Timeline del BR</h1>
<p class="subtitle">Vista cronológica de eventos · INVIMA-ready · genera PDF con Ctrl+P</p>
<div id="head"></div>
<div class="tl" id="timeline"></div>
</div>
<script>
async function load(){
  try{
    var r = await fetch('/api/brd/ebr/''' + str(ebr_id) + '''/vista-completa');
    var d = await r.json();
    if(!r.ok){
      document.getElementById('timeline').innerHTML = '<div style="color:#dc2626">Error: '+(d.error||r.status)+'</div>';
      return;
    }
    var h = d.header || {};
    document.getElementById('head').innerHTML =
      '<div class="header-card">'+
        '<div><b>Producto</b><br>'+(h.producto||'—')+'</div>'+
        '<div><b>Lote</b><br><span style="font-family:monospace;color:#dc2626;font-weight:700">'+(h.lote_codigo||'—')+'</span></div>'+
        '<div><b>Estado</b><br>'+(h.estado||'—')+'</div>'+
        '<div><b>Operario</b><br>'+(h.operario||'—')+'</div>'+
        '<div><b>Iniciado</b><br>'+(h.iniciado_at_utc||'').substring(0,16)+'</div>'+
        '<div><b>Completado</b><br>'+((h.completado_at_utc||'—').substring(0,16))+'</div>'+
        '<div><b>Progreso</b><br><span style="color:#0891b2;font-weight:700">'+(d.progreso_pasos_pct||0)+'%</span></div>'+
        '<div><b>IPC OK</b><br>'+(d.ipc_dentro_rango||0)+' / '+(d.ipc_total||0)+'</div>'+
      '</div>';
    // Construir eventos cronológicos
    var eventos = [];
    if(h.iniciado_at_utc) eventos.push({ts:h.iniciado_at_utc,tipo:'info',tit:'🚀 EBR iniciado',det:'Operario: '+(h.operario||'?')});
    (d.pesajes||[]).forEach(function(p){
      var ok = Math.abs(p.delta_pct) <= 3;
      eventos.push({
        ts:p.fecha,
        tipo:ok?'ok':'warn',
        tit:'⚖ Pesaje: '+p.material_nombre,
        det:'Esperado: '+p.esperada_g+' g · Real: '+p.real_g+' g · Δ '+p.delta_pct+'%'+(p.lote_mp?' · Lote MP: '+p.lote_mp:'')+(p.operario?' · Op: '+p.operario:'')
      });
    });
    (d.pasos||[]).forEach(function(s){
      // SEC-FIX · 21-may-2026 · _escBRD aplica luego (al render). Aquí solo data.
      if(s.iniciado) eventos.push({ts:s.iniciado,tipo:'info',tit:'▶ Paso #'+s.orden+': '+(s.descripcion||'')+' (inicio)',det:'Operario: '+(s.operario||'?')});
      if(s.completado) eventos.push({ts:s.completado,tipo:'ok',tit:'✓ Paso #'+s.orden+': '+(s.descripcion||'')+' (fin)',det:s.observaciones||'sin notas'});
    });
    (d.ipc||[]).forEach(function(i){
      eventos.push({
        ts:i.fecha,
        tipo:i.dentro_rango?'ok':'err',
        tit:(i.dentro_rango?'✓':'✗')+' IPC: '+i.nombre,
        det:'Esperado: '+i.esperado+' · Real: '+i.real+(i.observaciones?' · '+i.observaciones:'')
      });
    });
    if(h.completado_at_utc) eventos.push({ts:h.completado_at_utc,tipo:'ok',tit:'🏁 EBR completado',det:'Tiempo total: '+(h.tiempo_total_min||0)+' min'});
    if(h.liberado_at_utc) eventos.push({ts:h.liberado_at_utc,tipo:'ok',tit:'🔓 LIBERADO QC',det:'Por: '+(h.liberado_por||'?')});
    if(h.rechazado_at_utc) eventos.push({ts:h.rechazado_at_utc,tipo:'err',tit:'⛔ RECHAZADO',det:h.rechazado_motivo||''});
    // Sort cronológico
    eventos.sort(function(a,b){ return (a.ts||'').localeCompare(b.ts||''); });
    var tl = document.getElementById('timeline');
    if(!eventos.length){
      tl.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:30px">Sin eventos registrados todavía</div>';
      return;
    }
    // SEC-FIX · 21-may-2026 · XSS · escapar todos los strings concatenados
    // Antes: tit/det/operario/observaciones de DB sin escape · XSS stored
    function _escBRD(s){return String(s||'').replace(/[&<>"\\\\'/]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',"/":'&#47;'}[c];});}
    tl.innerHTML = eventos.map(function(e){
      return '<div class="evt '+_escBRD(e.tipo)+'">'+
        '<div class="ts">'+_escBRD((e.ts||'').substring(0,16))+'</div>'+
        '<div class="tit">'+_escBRD(e.tit)+'</div>'+
        '<div class="det">'+_escBRD(e.det||'')+'</div>'+
      '</div>';
    }).join('');
  }catch(e){
    document.getElementById('timeline').innerHTML = '<div style="color:#dc2626">Error red: '+e.message+'</div>';
  }
}
load();
</script></body></html>'''
    return Response(html, mimetype='text/html')


@bp.route("/api/brd/ebr/<int:ebr_id>/vista-completa", methods=["GET"])
def ebr_vista_completa(ebr_id):
    """MyBatch parity Sprint B · 21-may-2026 · Sebastián.

    Vista BR de 8 secciones unificada · 1 request en lugar de N round-trips
    (la pantalla que MyBatch tiene como núcleo del día a día):
    1. Header (lote, producto, fecha, operario, estado)
    2. Pesajes MP (con firmas si hay)
    3. Pasos del proceso (con timestamps real vs estimado)
    4. IPC resultados (in-process checks)
    5. Despejes de línea firmados (BPM)
    6. Observaciones acumuladas
    7. Estado cuarentena/liberación (post-completar)
    8. Audit log filtrado por ebr_id
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    out = {'ebr_id': ebr_id}
    # 1. Header · INVIMA-FIX 21-may-2026 · usar columnas originales + COALESCE
    # con aliases (mig 153) para que funcione antes y después de la migración.
    try:
        row = conn.execute(
            """SELECT id, mbr_template_id, produccion_id,
                      COALESCE(lote_codigo, lote) AS lote_codigo,
                      estado,
                      iniciado_at_utc, completado_at_utc,
                      COALESCE(operario, iniciado_por) AS operario,
                      COALESCE(tiempo_total_min,
                               CASE WHEN completado_at_utc IS NOT NULL
                                    THEN (julianday(completado_at_utc) - julianday(iniciado_at_utc)) * 24 * 60
                                    ELSE 0 END) AS tiempo_total_min,
                      COALESCE(observaciones, notas) AS observaciones,
                      liberado_at_utc, liberado_por,
                      COALESCE(rechazado_at_utc, '') AS rechazado_at_utc,
                      rechazado_motivo
               FROM ebr_ejecuciones WHERE id=?""",
            (ebr_id,),
        ).fetchone()
        if not row:
            return jsonify({'error': 'EBR no existe'}), 404
        out['header'] = {
            'id': row[0], 'mbr_template_id': row[1],
            'produccion_id': row[2], 'lote_codigo': row[3] or '',
            'estado': row[4] or '', 'iniciado_at_utc': row[5] or '',
            'completado_at_utc': row[6] or '', 'operario': row[7] or '',
            'tiempo_total_min': row[8] or 0, 'observaciones': row[9] or '',
            'liberado_at_utc': row[10] or '', 'liberado_por': row[11] or '',
            'rechazado_at_utc': row[12] or '', 'rechazado_motivo': row[13] or '',
        }
    except Exception as e:
        return jsonify({'error': f'header fallo: {e}'}), 500
    # Producto del MBR
    try:
        mbr = conn.execute(
            "SELECT producto_nombre, version, titulo, lote_size_g FROM mbr_templates WHERE id=?",
            (out['header']['mbr_template_id'],),
        ).fetchone()
        if mbr:
            out['header']['producto'] = mbr[0]
            out['header']['mbr_version'] = mbr[1]
            out['header']['titulo'] = mbr[2]
            out['header']['lote_size_g'] = float(mbr[3] or 0)
    except Exception:
        pass
    # 2. Pesajes MP
    try:
        rows = conn.execute(
            """SELECT material_id, COALESCE(material_nombre,''),
                      cantidad_esperada_g, cantidad_real_g, COALESCE(lote_mp,''),
                      COALESCE(operario,''), COALESCE(creado_at_utc,''),
                      COALESCE(observaciones,'')
               FROM ebr_pesajes WHERE ebr_id=? ORDER BY id""",
            (ebr_id,),
        ).fetchall()
        out['pesajes'] = [{
            'material_id': r[0], 'material_nombre': r[1],
            'esperada_g': float(r[2] or 0), 'real_g': float(r[3] or 0),
            'lote_mp': r[4], 'operario': r[5], 'fecha': r[6],
            'observaciones': r[7],
            'delta_pct': round(((r[3] - r[2]) / r[2] * 100) if r[2] else 0, 2),
        } for r in rows]
    except Exception:
        out['pesajes'] = []
    # 3. Pasos
    try:
        rows = conn.execute(
            """SELECT orden, descripcion, COALESCE(tiempo_estimado_min,0),
                      COALESCE(iniciado_at_utc,''), COALESCE(completado_at_utc,''),
                      COALESCE(operario,''), COALESCE(observaciones,'')
               FROM ebr_pasos WHERE ebr_id=? ORDER BY orden""",
            (ebr_id,),
        ).fetchall()
        out['pasos'] = [{
            'orden': r[0], 'descripcion': r[1],
            'tiempo_estimado_min': r[2],
            'iniciado': r[3], 'completado': r[4],
            'operario': r[5], 'observaciones': r[6],
            'completado_flag': bool(r[4]),
        } for r in rows]
    except Exception:
        out['pasos'] = []
    # 4. IPC resultados
    try:
        rows = conn.execute(
            """SELECT nombre, valor_esperado, valor_real, dentro_rango,
                      observaciones, COALESCE(creado_at_utc,'')
               FROM ebr_ipc_resultados WHERE ebr_id=? ORDER BY id""",
            (ebr_id,),
        ).fetchall()
        out['ipc'] = [{
            'nombre': r[0], 'esperado': r[1], 'real': r[2],
            'dentro_rango': bool(r[3]), 'observaciones': r[4],
            'fecha': r[5],
        } for r in rows]
    except Exception:
        out['ipc'] = []
    # 5. Despejes (referenciados por lote o produccion_id)
    try:
        rows = conn.execute(
            """SELECT area_codigo, marcado_por, ts, COALESCE(observaciones,'')
               FROM despeje_linea_checklist
               ORDER BY ts DESC LIMIT 5""",
        ).fetchall()
        out['despejes_recientes'] = [{
            'area': r[0], 'marcado_por': r[1], 'fecha': r[2],
            'observaciones': r[3],
        } for r in rows]
    except Exception:
        out['despejes_recientes'] = []
    # 6. Audit log filtrado
    try:
        rows = conn.execute(
            """SELECT fecha, usuario, accion, COALESCE(detalle,'')
               FROM audit_log
               WHERE tabla IN ('ebr_ejecuciones','ebr_pesajes','ebr_pasos','ebr_ipc_resultados')
                 AND registro_id = ?
               ORDER BY fecha DESC LIMIT 30""",
            (str(ebr_id),),
        ).fetchall()
        out['audit'] = [{
            'fecha': r[0], 'usuario': r[1], 'accion': r[2], 'detalle': r[3],
        } for r in rows]
    except Exception:
        out['audit'] = []
    # Resumen métricas
    completados = sum(1 for p in out['pasos'] if p['completado_flag'])
    out['progreso_pasos_pct'] = round((completados / len(out['pasos']) * 100) if out['pasos'] else 0, 1)
    out['pesajes_count'] = len(out['pesajes'])
    out['ipc_dentro_rango'] = sum(1 for i in out['ipc'] if i['dentro_rango'])
    out['ipc_total'] = len(out['ipc'])
    return jsonify(out)


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
    err = _require_brd_ejecutor()
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
    audit_log(cur, usuario=user, accion="INICIAR_PASO_EBR",
              tabla="ebr_pasos_ejecutados", registro_id=paso["id"],
              despues={"ebr_id": ebr_id, "orden": orden, "operario": user})
    conn.commit()
    return jsonify({"ok": True, "estado": "en_proceso"})


@bp.route("/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/completar", methods=["POST"])
def completar_paso_ebr(ebr_id, orden):
    err = _require_brd_ejecutor()
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
        # Segregación de funciones GMP · el QC (supervisa) no puede ser la
        # misma persona que ejecuta el paso · auto-aprobación rompe el control.
        if qc_username and qc_username == (paso["operario_username"] or user):
            return jsonify({"error": "El QC (supervisa) no puede ser el mismo operario que ejecutó el paso"}), 409

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
    audit_log(cur, usuario=user, accion="COMPLETAR_PASO_EBR",
              tabla="ebr_pasos_ejecutados", registro_id=paso["id"],
              despues={"ebr_id": ebr_id, "orden": orden,
                       "operario": op_username, "qc": qc_username or None})
    conn.commit()
    return jsonify({"ok": True, "estado": "completado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/completar", methods=["POST"])
def completar_ebr(ebr_id):
    err = _require_brd_ejecutor()
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
        "SELECT estado, cantidad_objetivo_g, COALESCE(fase,'fabricacion') AS fase "
        "FROM ebr_ejecuciones WHERE id = ?",
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

    # IPCs obligatorios deben estar reportados Y conformes (Part 11 + GMP).
    # mbr_template_id viene de ebr_ejecuciones · re-leemos para no asumir.
    # FIX 1-jun-2026 audit Planta (P0 INVIMA) · ANTES seleccionaba solo
    # mbr_template_id pero abajo (cuarentena) accedía ebr_full['lote'] / .get('lote')
    # → KeyError/AttributeError SIEMPRE → la Entrada en CUARENTENA NUNCA se creaba
    # (lote PT no pasaba por cuarentena · liberar_ebr no tenía qué promover).
    # Ahora cargamos lote y lo dejamos como dict (para .get) · lote_codigo no existe
    # como columna, se elimina su referencia.
    _ef = cur.execute(
        "SELECT mbr_template_id, lote FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)
    ).fetchone()
    ebr_full = dict(_ef) if _ef else {}
    ipcs_faltantes = cur.execute(
        """SELECT s.parametro
           FROM ipc_specs s
           LEFT JOIN ipc_resultados r
             ON r.ipc_spec_id = s.id AND r.ebr_id = ?
           WHERE s.mbr_template_id = ?
             AND s.obligatorio = 1
             AND r.id IS NULL""",
        (ebr_id, ebr_full["mbr_template_id"]),
    ).fetchall()
    if ipcs_faltantes:
        return jsonify({
            "error": "IPCs obligatorios sin reportar",
            "parametros": [r["parametro"] for r in ipcs_faltantes],
        }), 409
    # Audit 3-jun · incluir conforme IS NULL: un IPC cualitativo obligatorio
    # reportado pero SIN adjudicar (Conforme/No conforme) por QC no debe dejar
    # completar el lote (antes solo bloqueaba conforme=0 → cualitativo NULL pasaba).
    ipcs_no_conformes = cur.execute(
        """SELECT s.parametro, r.valor_medido, s.valor_min, s.valor_max, r.conforme
           FROM ipc_resultados r
           JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
             AND s.obligatorio = 1
             AND (r.conforme = 0 OR r.conforme IS NULL)""",
        (ebr_id,),
    ).fetchall()
    if ipcs_no_conformes:
        return jsonify({
            "error": "IPCs obligatorios fuera de spec o sin adjudicar QC "
                     "(conforme=NULL) · debe resolverse antes de completar",
            "parametros": [{
                "parametro": r["parametro"],
                "medido": r["valor_medido"],
                "min": r["valor_min"], "max": r["valor_max"],
                "conforme": r["conforme"],
            } for r in ipcs_no_conformes],
        }), 409

    yield_pct = round((cantidad_real / ebr["cantidad_objetivo_g"]) * 100, 2) if ebr["cantidad_objetivo_g"] else None
    # Puente OP→OF · densidad (g/mL) opcional → mL envasable = real_g / densidad.
    try:
        densidad = float(body.get("densidad_g_ml") or 0)
    except (ValueError, TypeError):
        densidad = 0.0
    densidad = densidad if densidad > 0 else None
    ml_envasable = round(cantidad_real / densidad, 2) if densidad else None
    # Batch C · rendimiento por UNIDADES (Envasado/Acondicionamiento). El yield de
    # granel (yield_pct) sigue igual; acá se calcula yield_uds_pct si el body trae
    # unidades. Aplica a cualquier fase pero típicamente OF/OA.
    def _num_opt(k):
        v = body.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    uds_teoricas = _num_opt("unidades_teoricas")
    uds_buenas = _num_opt("unidades_buenas_real")
    yield_uds_pct = (round(uds_buenas / uds_teoricas * 100, 2)
                     if uds_teoricas and uds_buenas is not None and uds_teoricas > 0
                     else None)
    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'completado',
                 completado_at_utc = datetime('now', 'utc'),
                 cantidad_real_g = ?,
                 yield_pct = ?,
                 densidad_g_ml = ?,
                 ml_envasable = ?,
                 unidades_teoricas = ?,
                 unidades_buenas_real = ?,
                 yield_uds_pct = ?
           WHERE id = ?""",
        (cantidad_real, yield_pct, densidad, ml_envasable,
         uds_teoricas, uds_buenas, yield_uds_pct, ebr_id),
    )
    # INVIMA-FIX · 21-may-2026 · cuarentena explícita auto al completar
    # Antes: lote PT quedaba 'completado' pero NO había movimiento de
    # Entrada con estado_lote='CUARENTENA' · podía usarse antes de QC.
    # Ahora: INSERT movimientos · libera_ebr promueve a VIGENTE (Fix prev).
    cuarentena_creada = False
    try:
        lote_ref = (ebr_full.get('lote') or '').strip()
        if lote_ref and cantidad_real and cantidad_real > 0:
            # Buscar producto del producción para material_id (puede ser PT)
            prod_row = cur.execute(
                """SELECT pp.producto FROM produccion_programada pp
                   WHERE pp.id = (SELECT produccion_id FROM ebr_ejecuciones WHERE id=?)""",
                (ebr_id,),
            ).fetchone()
            prod_nombre = prod_row[0] if prod_row else ''
            # Check si ya existe el movimiento PT para no duplicar.
            # Audit 3-jun · scopear por material_id PT (LIKE 'PT_%') · antes filtraba
            # solo por lote → una Entrada MP con el MISMO string de lote bloqueaba la
            # creación del PT (y viceversa en liberar/asignar-lote).
            existe = cur.execute(
                "SELECT 1 FROM movimientos WHERE lote=? AND tipo='Entrada' "
                "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\' LIMIT 1",
                (lote_ref,),
            ).fetchone()
            if not existe:
                cur.execute(
                    """INSERT INTO movimientos
                       (material_id, material_nombre, cantidad, tipo, fecha,
                        observaciones, operador, lote, estado_lote)
                       VALUES (?, ?, ?, 'Entrada', datetime('now','-5 hours'),
                               ?, ?, ?, 'CUARENTENA')""",
                    ('PT_' + (prod_nombre[:20] if prod_nombre else 'GENERICO'),
                     prod_nombre or 'PT',
                     cantidad_real,
                     f'Granel BRD completado · EBR #{ebr_id} · pendiente liberación QC',
                     user, lote_ref),
                )
                cuarentena_creada = True
    except Exception as _e:
        import logging as _logc
        _logc.getLogger('inventario.brd').warning('cuarentena auto completar_ebr fallo: %s', _e)
    conn.commit()
    audit_log(cur, usuario=user, accion="COMPLETAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"cantidad_real_g": cantidad_real, "yield_pct": yield_pct,
                       "cuarentena_auto_creada": cuarentena_creada})
    return jsonify({"ok": True, "estado": "completado", "yield_pct": yield_pct,
                    "densidad_g_ml": densidad, "ml_envasable": ml_envasable,
                    "yield_uds_pct": yield_uds_pct,
                    "cuarentena_creada": cuarentena_creada})


@bp.route("/api/brd/ebr/<int:ebr_id>/asignar-lote-fisico", methods=["POST"])
def asignar_lote_fisico_ebr(ebr_id):
    """Reemplaza el lote provisional 'PP<id>' por el lote físico/comercial real
    (audit 3-jun). QC firma y libera el lote REAL, no un código interno; y la
    Entrada de PT en el kardex queda bajo el mismo lote. Solo antes de liberar.

    Body: {lote_fisico}
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    nuevo = (body.get("lote_fisico") or "").strip()
    if not nuevo:
        return jsonify({"error": "lote_fisico requerido"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"EBR {ebr['estado']} es inmutable · no se puede "
                                 f"reasignar el lote"}), 409
    anterior = ebr["lote"] or ""
    if nuevo == anterior:
        return jsonify({"ok": True, "lote": nuevo, "sin_cambios": True})
    # Unicidad: ningún otro EBR puede tener ese lote
    dup = cur.execute(
        "SELECT id FROM ebr_ejecuciones WHERE lote=? AND id<>?", (nuevo, ebr_id),
    ).fetchone()
    if dup:
        return jsonify({"error": f"el lote '{nuevo}' ya está en uso por otro EBR",
                        "codigo": "LOTE_DUPLICADO"}), 409
    cur.execute(
        "UPDATE ebr_ejecuciones SET lote=?, lote_codigo=? WHERE id=?",
        (nuevo, nuevo, ebr_id),
    )
    # Propagar al movimiento de Entrada PT creado con el lote provisional, para
    # que la promoción a VIGENTE (al liberar) y el kardex apunten al lote real.
    mov_actualizados = 0
    if anterior:
        try:
            cur.execute(
                "UPDATE movimientos SET lote=? WHERE lote=? AND tipo='Entrada' "
                "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\'",
                (nuevo, anterior),
            )
            mov_actualizados = cur.rowcount or 0
        except Exception:
            pass  # deploy-safe
    audit_log(cur, usuario=session.get("compras_user", ""),
              accion="ASIGNAR_LOTE_FISICO_EBR", tabla="ebr_ejecuciones",
              registro_id=ebr_id,
              antes={"lote": anterior}, despues={"lote": nuevo,
                                                 "movimientos_actualizados": mov_actualizados})
    conn.commit()
    return jsonify({"ok": True, "lote": nuevo, "lote_anterior": anterior,
                    "movimientos_actualizados": mov_actualizados})


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

    # Reemplazo MyBatch fase 2 · no liberar un lote con una desviación ABIERTA
    # (la que abre un IPC OOS, u otra del lote). Debe cerrarse/anularse antes.
    try:
        _lr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _lote = (_lr[0] if _lr else '') or ''
        if _lote:
            # FIX 1-jun-2026 (audit): bloquear también desviaciones CERRADAS con CAPA
            # NO EFECTIVO (efectividad_ok=0) — antes una cerrada-no-efectiva desbloqueaba
            # la liberación. (El LIKE '%lote%' se mantiene a propósito: afinarlo a token
            # exacto podría NO ver una desviación real si lotes_afectados es texto libre →
            # liberaría producto no conforme. El falso positivo bloquea de más = lado seguro.)
            desv_open = cur.execute(
                """SELECT codigo, COALESCE(estado,''), COALESCE(efectividad_ok,1)
                     FROM desviaciones
                    WHERE lotes_afectados LIKE ?
                      AND ( COALESCE(estado,'') NOT IN ('cerrada', 'anulada')
                            OR (COALESCE(estado,'') = 'cerrada'
                                AND COALESCE(efectividad_ok,1) = 0) )
                    ORDER BY id DESC LIMIT 1""",
                (f'%{_lote}%',),
            ).fetchone()
            if desv_open:
                _cerrada_inef = (desv_open[1] == 'cerrada')
                return jsonify({
                    "error": (f"No se puede liberar: desviación {desv_open[0]} "
                              + ("CERRADA con CAPA NO EFECTIVO" if _cerrada_inef else "ABIERTA")
                              + f" para el lote {_lote}. "
                              + ("Reabrí/resolvé con un CAPA efectivo antes de liberar."
                                 if _cerrada_inef else
                                 "Cerrá/resolvé la desviación (clasificar→investigar→CAPA→cerrar) primero.")),
                    "codigo": ("DESVIACION_CAPA_INEFECTIVO" if _cerrada_inef
                               else "DESVIACION_ABIERTA"),
                }), 409
    except Exception:
        pass  # deploy-safe (tabla/columna ausente no debe romper liberación)

    # Audit 3-jun · GATE DIRECTO IPC OOS (fail-closed, independiente del texto del
    # lote). El gate por desviación de arriba depende del matching textual de
    # lotes_afectados y de que la auto-desviación se haya creado. Acá chequeamos
    # por ebr_id directo: si hay IPC no-conforme o sin adjudicar, bloquear salvo
    # que CADA uno tenga su desviación resuelta (cerrada + CAPA efectivo).
    try:
        _oos_n = cur.execute(
            "SELECT COUNT(*) FROM ipc_resultados "
            "WHERE ebr_id=? AND (conforme=0 OR conforme IS NULL)", (ebr_id,),
        ).fetchone()[0]
    except Exception:
        _oos_n = 0
    if _oos_n:
        try:
            _sin_resolver = cur.execute(
                """SELECT COUNT(*) FROM ipc_resultados r
                     LEFT JOIN desviaciones d ON d.id = r.desviacion_id
                    WHERE r.ebr_id = ?
                      AND (r.conforme = 0 OR r.conforme IS NULL)
                      AND ( r.desviacion_id IS NULL
                            OR COALESCE(d.estado,'') NOT IN ('cerrada','anulada')
                            OR (COALESCE(d.estado,'') = 'cerrada'
                                AND COALESCE(d.efectividad_ok,1) = 0) )""",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            # No se pudo verificar el enlace (p.ej. desviacion_id ausente en PG):
            # hay OOS y no podemos probar que esté resuelto → bloquear (fail-closed).
            _sin_resolver = _oos_n
        if _sin_resolver:
            return jsonify({
                "error": (f"No se puede liberar: {_sin_resolver} IPC fuera de "
                          f"especificación o sin adjudicar QC sin desviación "
                          f"resuelta (cerrada con CAPA efectivo)."),
                "codigo": "IPC_OOS_SIN_RESOLVER",
            }), 409

    # Batch B · Acondicionamiento · no liberar con arte/etiqueta sin aprobar
    # (gate de etiquetado GMP). Aplica si hay artes registradas (costo nulo si no).
    try:
        _artes_sin = cur.execute(
            "SELECT COUNT(*) FROM ebr_artes_codificacion "
            "WHERE ebr_id=? AND COALESCE(aprobado_por,'')=''", (ebr_id,),
        ).fetchone()[0]
    except Exception:
        _artes_sin = 0
    if _artes_sin:
        return jsonify({
            "error": f"No se puede liberar: {_artes_sin} arte/etiqueta sin aprobar "
                     f"(aprobá la codificación/etiqueta antes de liberar).",
            "codigo": "ARTES_SIN_APROBAR",
        }), 409

    # Audit 3-jun · GATE DE COMPLETITUD del legajo · solo EBR_MODE='strict' (BPM
    # duro). En 'warn' (piloto) NO bloquea, para no frenar mientras se adopta.
    if EBR_MODE == 'strict':
        try:
            _pes_sin_verif = cur.execute(
                "SELECT COUNT(*) FROM ebr_pesajes "
                "WHERE ebr_id=? AND COALESCE(verificado_por,'')=''", (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _pes_sin_verif = 0
        if _pes_sin_verif:
            return jsonify({
                "error": f"No se puede liberar: {_pes_sin_verif} pesaje(s) sin "
                         f"2ª firma de verificación.",
                "codigo": "PESAJES_SIN_VERIFICAR",
            }), 409
        try:
            _n_concil = cur.execute(
                "SELECT COUNT(*) FROM ebr_conciliacion_material WHERE ebr_id=?",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _n_concil = 0
        if _n_concil == 0:
            return jsonify({
                "error": "No se puede liberar: falta la conciliación de material "
                         "(envase/empaque) del lote.",
                "codigo": "CONCILIACION_FALTANTE",
            }), 409
        # MyBatch ② · despeje de línea conforme obligatorio (GMP)
        try:
            _despeje_ok = cur.execute(
                "SELECT COUNT(*) FROM ebr_despeje_linea WHERE ebr_id=? AND conforme=1",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _despeje_ok = 1  # tabla ausente · no bloquear (deploy-safe)
        if not _despeje_ok:
            return jsonify({
                "error": "No se puede liberar: falta el despeje de línea CONFORME.",
                "codigo": "DESPEJE_FALTANTE",
            }), 409

    # INVIMA-FIX · 21-may-2026 · tiempo mínimo cuarentena antes de liberar
    # Antes: QA podía liberar EBR completado inmediatamente
    # Default: 0 días (sin gate) · env BRD_CUARENTENA_MIN_DIAS=N para gate
    try:
        import os as _os_brd
        min_dias_cuarentena = int(_os_brd.environ.get('BRD_CUARENTENA_MIN_DIAS', '0'))
    except Exception:
        min_dias_cuarentena = 0
    if min_dias_cuarentena > 0:
        try:
            row_t = cur.execute(
                "SELECT completado_at_utc FROM ebr_ejecuciones WHERE id=?",
                (ebr_id,),
            ).fetchone()
            if row_t and row_t[0]:
                from datetime import datetime as _dtbrd
                completado_dt = _dtbrd.fromisoformat(str(row_t[0]).replace('Z', '+00:00').split('.')[0])
                horas_transc = (_dtbrd.utcnow() - completado_dt).total_seconds() / 3600
                if horas_transc < min_dias_cuarentena * 24:
                    return jsonify({
                        'error': f'Tiempo mínimo cuarentena: {min_dias_cuarentena} días · transcurridos {horas_transc/24:.1f}d',
                        'codigo': 'CUARENTENA_TIEMPO_MINIMO',
                    }), 409
        except Exception:
            pass  # graceful

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
    # INVIMA-FIX · 21-may-2026 · promociona lote PT a VIGENTE
    # Antes: estado solo cambiaba en ebr_ejecuciones · movimientos PT
    # seguía CUARENTENA · Compras/Despachos no podía facturarlo aunque
    # QC firmó · doble operación manual + riesgo despacho sin liberación.
    pt_lote_promovidos = 0
    try:
        lote_row = cur.execute(
            "SELECT lote, lote_codigo FROM ebr_ejecuciones WHERE id=?",
            (ebr_id,),
        ).fetchone()
        lote_ref = (lote_row['lote'] or lote_row.get('lote_codigo', '') if lote_row else '') or ''
        if lote_ref:
            cur.execute(
                """UPDATE movimientos SET estado_lote='VIGENTE'
                   WHERE lote=? AND tipo='Entrada'
                     AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\'
                     AND estado_lote IN ('CUARENTENA','CUARENTENA_EXTENDIDA')""",
                (lote_ref,),
            )
            pt_lote_promovidos = cur.rowcount or 0
    except Exception as _e:
        import logging as _log
        _log.getLogger('inventario.brd').warning('liberar_ebr promocion PT fallo: %s', _e)
    conn.commit()
    audit_log(cur, usuario=user, accion="LIBERAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"liberado_por": user, "signature_id": signature_id,
                       "pt_lotes_promovidos": pt_lote_promovidos})
    return jsonify({"ok": True, "estado": "liberado",
                    "pt_lotes_promovidos": pt_lote_promovidos})


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

    # INVIMA-FIX · 21-may-2026 · grabar timestamp rechazo (KPI 30d en dashboard)
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'rechazado',
                 rechazado_motivo = ?,
                 rechazado_at_utc = datetime('now', 'utc')
           WHERE id = ?""",
        (motivo, ebr_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="RECHAZAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"motivo": motivo, "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "rechazado"})


# ════════════════════════════════════════════════════════════════════════════
# IPCs · In-Process Controls (specs en MBR + resultados en EBR)
# ════════════════════════════════════════════════════════════════════════════
# specs: pH, viscosidad, T°, apariencia, etc. con rangos de aceptación.
# resultados: medición real durante la ejecución del lote.
# Si un spec obligatorio queda sin medir o NO conforme, el endpoint
# /api/brd/ebr/<id>/completar (lo veremos abajo en la ampliación) bloquea.

def _spec_to_dict(row):
    return {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "mbr_paso_id": row["mbr_paso_id"],
        "parametro": row["parametro"],
        "unidad": row["unidad"] or "",
        "valor_min": row["valor_min"],
        "valor_max": row["valor_max"],
        "metodo": row["metodo"] or "",
        "obligatorio": int(row["obligatorio"] or 0),
        "notas": row["notas"] or "",
    }


def _resultado_to_dict(row):
    return {
        "id": row["id"],
        "ebr_id": row["ebr_id"],
        "ipc_spec_id": row["ipc_spec_id"],
        "valor_medido": row["valor_medido"],
        "valor_texto": row["valor_texto"] or "",
        "conforme": row["conforme"],
        "medido_por": row["medido_por"],
        "medido_at_utc": row["medido_at_utc"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "notas": row["notas"] or "",
    }


# ── /api/brd/mbr/<id>/ipc-specs · CRUD specs (solo en draft) ──────────────

@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs", methods=["GET"])
def listar_ipc_specs(mbr_id):
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, mbr_template_id, mbr_paso_id, parametro, unidad,
                  valor_min, valor_max, metodo, obligatorio, notas
           FROM ipc_specs WHERE mbr_template_id = ? ORDER BY id""",
        (mbr_id,),
    ).fetchall()
    return jsonify({"items": [_spec_to_dict(r) for r in rows]})


@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs", methods=["POST"])
def crear_ipc_spec(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se agregan specs IPC en MBR draft"}), 409

    body = request.get_json(silent=True) or {}
    parametro = (body.get("parametro") or "").strip()
    if not parametro:
        return jsonify({"error": "parametro requerido"}), 400

    def _f(v):
        try:
            return float(v) if v is not None and v != "" else None
        except (ValueError, TypeError):
            return None

    cur.execute(
        """INSERT INTO ipc_specs
             (mbr_template_id, mbr_paso_id, parametro, unidad,
              valor_min, valor_max, metodo, obligatorio, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mbr_id,
         body.get("mbr_paso_id"),
         parametro,
         (body.get("unidad") or "").strip(),
         _f(body.get("valor_min")),
         _f(body.get("valor_max")),
         (body.get("metodo") or "").strip(),
         1 if body.get("obligatorio", 1) else 0,
         (body.get("notas") or "").strip()),
    )
    spec_id = cur.lastrowid
    conn.commit()
    return jsonify({"ok": True, "id": spec_id}), 201


@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs/<int:spec_id>", methods=["DELETE"])
def borrar_ipc_spec(mbr_id, spec_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se borran specs en MBR draft"}), 409
    cur.execute(
        "DELETE FROM ipc_specs WHERE id = ? AND mbr_template_id = ?",
        (spec_id, mbr_id),
    )
    if cur.rowcount == 0:
        return jsonify({"error": "spec no encontrado"}), 404
    conn.commit()
    return jsonify({"ok": True})


# ── /api/brd/ebr/<id>/ipc-resultados · reportar mediciones ────────────────

@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-resultados", methods=["GET"])
def listar_ipc_resultados(ebr_id):
    err = _require_login()
    if err:
        return err
    # JOIN con specs para devolver detalle del parámetro
    rows = get_db().execute(
        """SELECT r.*, s.parametro AS spec_parametro, s.unidad AS spec_unidad,
                  s.valor_min AS spec_min, s.valor_max AS spec_max,
                  s.obligatorio AS spec_obligatorio
           FROM ipc_resultados r
           JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
           ORDER BY r.medido_at_utc""",
        (ebr_id,),
    ).fetchall()
    items = []
    for r in rows:
        d = _resultado_to_dict(r)
        d["spec"] = {
            "parametro": r["spec_parametro"],
            "unidad": r["spec_unidad"] or "",
            "valor_min": r["spec_min"],
            "valor_max": r["spec_max"],
            "obligatorio": int(r["spec_obligatorio"] or 0),
        }
        items.append(d)
    return jsonify({"items": items})


@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-resultados", methods=["POST"])
def reportar_ipc_resultado(ebr_id):
    """Operario reporta medición de un IPC. Calcula conforme automáticamente
    si hay rango numérico; para parámetros cualitativos QC debe firmar después."""
    # SEC-FIX · 21-may-2026 · solo ejecutores BRD (planta/admin/QC)
    # Antes: cualquier compras_user podía falsificar IPCs
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    spec_id = body.get("ipc_spec_id")
    if not spec_id:
        return jsonify({"error": "ipc_spec_id requerido"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, mbr_template_id FROM ebr_ejecuciones WHERE id = ?",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    spec = cur.execute(
        "SELECT * FROM ipc_specs WHERE id = ? AND mbr_template_id = ?",
        (int(spec_id), ebr["mbr_template_id"]),
    ).fetchone()
    if not spec:
        return jsonify({"error": "spec no pertenece al MBR del EBR"}), 400

    # Validar valor_medido vs rango si aplica
    valor = body.get("valor_medido")
    valor_texto = (body.get("valor_texto") or "").strip()
    try:
        valor_f = float(valor) if valor is not None and valor != "" else None
    except (ValueError, TypeError):
        return jsonify({"error": "valor_medido inválido"}), 400

    if spec["valor_min"] is not None or spec["valor_max"] is not None:
        if valor_f is None:
            return jsonify({"error": "valor_medido requerido (spec numérico)"}), 400
        conforme = 1
        if spec["valor_min"] is not None and valor_f < float(spec["valor_min"]):
            conforme = 0
        if spec["valor_max"] is not None and valor_f > float(spec["valor_max"]):
            conforme = 0
    else:
        # Cualitativo: pendiente de validación QC (NULL hasta que firme)
        conforme = body.get("conforme")
        if conforme is not None:
            conforme = 1 if conforme else 0

    user = session.get("compras_user", "")
    try:
        cur.execute(
            """INSERT INTO ipc_resultados
                 (ebr_id, ipc_spec_id, valor_medido, valor_texto, conforme,
                  medido_por, medido_at_utc, notas)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
            (ebr_id, int(spec_id), valor_f, valor_texto, conforme,
             user, (body.get("notas") or "").strip()),
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            return jsonify({"error": "ya existe resultado para este spec en este EBR"}), 409
        raise
    rid = cur.lastrowid
    # Reemplazo MyBatch fase 2 · IPC NO conforme → abre desviación/CAPA
    # automática (aseguramiento) ligada a este resultado y al lote del EBR.
    # Deploy-safe: si la mig 203 (desviacion_id) o el helper no están, no rompe.
    desviacion = None
    if conforme == 0:
        try:
            lr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
            lote = (lr[0] if lr else '') or f'EBR{ebr_id}'
            _vis = valor_f if valor_f is not None else (valor_texto or '?')
            desc = (f"IPC fuera de especificación · lote {lote} (EBR #{ebr_id}) · "
                    f"{spec['parametro']} = {_vis} {spec['unidad'] or ''} "
                    f"(rango {spec['valor_min']}–{spec['valor_max']}). "
                    f"Desviación abierta automáticamente desde el EBR.")
            from blueprints.aseguramiento import crear_desviacion_auto
            cod, desv_id = crear_desviacion_auto(
                cur, tipo='proceso', descripcion=desc, lotes_afectados=lote,
                detectado_por=user, area_origen='Producción', impacto_producto=1)
            try:
                cur.execute("UPDATE ipc_resultados SET desviacion_id=? WHERE id=?", (desv_id, rid))
            except Exception:
                pass  # mig 203 aún no aplicada · enlace opcional
            desviacion = {"codigo": cod, "id": desv_id}
        except Exception as _ed:
            # FAIL-CLOSED (audit 3-jun): un IPC OOS DEBE quedar con su desviación.
            # Si la auto-desviación falla, NO persistir el resultado en silencio
            # (dejaría un OOS sin trazabilidad y el gate de liberación, que mira
            # desviaciones, no lo vería → liberaría producto no conforme).
            logging.getLogger('brd').error('auto-desviación IPC OOS fallo: %s', _ed)
            try:
                conn.rollback()
            except Exception:
                pass
            return jsonify({
                "error": "El IPC quedó fuera de especificación pero no se pudo "
                         "abrir la desviación automática. No se guardó el "
                         "resultado · reintentá o avisá a Calidad.",
                "codigo": "DESVIACION_AUTO_FALLO",
            }), 500
    conn.commit()
    audit_log(cur, usuario=user, accion="REPORTAR_IPC",
              tabla="ipc_resultados", registro_id=rid,
              despues={"ebr_id": ebr_id, "spec_id": spec_id,
                        "valor": valor_f, "conforme": conforme,
                        "desviacion": (desviacion or {}).get("codigo")})
    return jsonify({"ok": True, "id": rid, "conforme": conforme,
                     "desviacion": desviacion}), 201


# ════════════════════════════════════════════════════════════════════════════
# Equipment cleaning log (F6)
# ════════════════════════════════════════════════════════════════════════════

VALID_TIPO_LIMPIEZA = {"rutinaria", "profunda", "cambio_producto"}


def _cleaning_to_dict(row):
    return {
        "id": row["id"],
        "equipo_codigo": row["equipo_codigo"],
        "lote_anterior": row["lote_anterior"] or "",
        "lote_siguiente": row["lote_siguiente"] or "",
        "tipo_limpieza": row["tipo_limpieza"],
        "operario_username": row["operario_username"],
        "operario_e_sign_id": row["operario_e_sign_id"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "visual_ok": row["visual_ok"],
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "observaciones": row["observaciones"] or "",
    }


@bp.route("/api/brd/cleaning", methods=["POST"])
def reportar_cleaning():
    """Operario reporta INICIO de limpieza de un equipo."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    equipo = (body.get("equipo_codigo") or "").strip()
    if not equipo:
        return jsonify({"error": "equipo_codigo requerido"}), 400
    tipo = (body.get("tipo_limpieza") or "rutinaria").strip().lower()
    if tipo not in VALID_TIPO_LIMPIEZA:
        return jsonify({"error": f"tipo_limpieza inválido · use {sorted(VALID_TIPO_LIMPIEZA)}"}), 400

    user = session.get("compras_user", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO equipo_limpieza_log
             (equipo_codigo, lote_anterior, lote_siguiente, tipo_limpieza,
              operario_username, iniciado_at_utc, observaciones)
           VALUES (?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (equipo,
         (body.get("lote_anterior") or "").strip(),
         (body.get("lote_siguiente") or "").strip(),
         tipo, user,
         (body.get("observaciones") or "").strip()),
    )
    cl_id = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="INICIAR_LIMPIEZA",
              tabla="equipo_limpieza_log", registro_id=cl_id,
              despues={"equipo": equipo, "tipo": tipo})
    return jsonify({"ok": True, "id": cl_id}), 201


@bp.route("/api/brd/cleaning/<int:cl_id>/completar", methods=["POST"])
def completar_cleaning(cl_id):
    """Operario marca limpieza como completada con e-sign opcional."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT operario_username, completado_at_utc FROM equipo_limpieza_log WHERE id = ?",
        (cl_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "cleaning log no encontrado"}), 404
    if row["completado_at_utc"]:
        return jsonify({"error": "limpieza ya completada"}), 409

    user = session.get("compras_user", "")
    # Validar e-sign si se pasa
    if signature_id:
        if not _validar_signature(
            cur, signature_id, record_table="equipo_limpieza_log",
            record_id=cl_id, meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido"}), 400

    cur.execute(
        """UPDATE equipo_limpieza_log
             SET completado_at_utc = datetime('now', 'utc'),
                 operario_e_sign_id = ?
           WHERE id = ?""",
        (int(signature_id) if signature_id else None, cl_id),
    )
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/cleaning/<int:cl_id>/validar", methods=["POST"])
def validar_cleaning_qc(cl_id):
    """QC firma inspección visual y marca visual_ok=1/0."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    visual_ok = body.get("visual_ok")
    signature_id = body.get("signature_id")
    if visual_ok is None:
        return jsonify({"error": "visual_ok requerido (1=conforme, 0=no)"}), 400
    if not signature_id:
        return jsonify({
            "error": "signature_id requerido · meaning='supervisa' record_table='equipo_limpieza_log'",
        }), 400

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT qc_e_sign_id FROM equipo_limpieza_log WHERE id = ?",
        (cl_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "cleaning log no encontrado"}), 404
    if row["qc_e_sign_id"]:
        return jsonify({"error": "ya validado por QC (inmutable)"}), 409

    user = session.get("compras_user", "")
    if not _validar_signature(
        cur, signature_id, record_table="equipo_limpieza_log",
        record_id=cl_id, meaning="supervisa", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a 'supervisa' tuya en este log"}), 400

    cur.execute(
        """UPDATE equipo_limpieza_log
             SET qc_username = ?,
                 qc_e_sign_id = ?,
                 visual_ok = ?
           WHERE id = ?""",
        (user, int(signature_id), 1 if visual_ok else 0, cl_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="VALIDAR_LIMPIEZA_QC",
              tabla="equipo_limpieza_log", registro_id=cl_id,
              despues={"visual_ok": visual_ok, "signature_id": signature_id})
    return jsonify({"ok": True, "visual_ok": int(bool(visual_ok))})


@bp.route("/api/brd/cleaning", methods=["GET"])
def listar_cleaning():
    err = _require_login()
    if err:
        return err
    equipo = (request.args.get("equipo") or "").strip()
    where, params = [], []
    if equipo:
        where.append("equipo_codigo = ?")
        params.append(equipo)
    sql = """SELECT * FROM equipo_limpieza_log"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY iniciado_at_utc DESC LIMIT 200"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_cleaning_to_dict(r) for r in rows]})


@bp.route("/api/brd/cleaning/equipo/<equipo>/ultima", methods=["GET"])
def ultima_cleaning(equipo):
    """Última limpieza del equipo (validada o no). Útil para wizard que
    decide si el equipo puede usarse en un lote nuevo."""
    err = _require_login()
    if err:
        return err
    row = get_db().execute(
        """SELECT * FROM equipo_limpieza_log
           WHERE equipo_codigo = ?
           ORDER BY iniciado_at_utc DESC LIMIT 1""",
        (equipo,),
    ).fetchone()
    if not row:
        return jsonify({"equipo_codigo": equipo, "ultima": None,
                         "apto_para_uso": False,
                         "razon": "sin registros de limpieza"})
    apto = (row["completado_at_utc"] is not None
             and int(row["visual_ok"] or 0) == 1)
    return jsonify({
        "equipo_codigo": equipo,
        "ultima": _cleaning_to_dict(row),
        "apto_para_uso": apto,
        "razon": "" if apto else "limpieza pendiente o no validada por QC",
    })


# ════════════════════════════════════════════════════════════════════════════
# PDF maestro auditable EBR (F8)
# ════════════════════════════════════════════════════════════════════════════

def _safe_pdf(text):
    """fpdf2 latin-1 compatible (replica de api/comprobante_pago._safe)."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    repl = {"—": "-", "–": "-", "…": "...", "“": '"', "”": '"',
            "‘": "'", "’": "'", "•": "·", "→": "->", "≥": ">=", "≤": "<="}
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


@bp.route("/api/brd/ebr/<int:ebr_id>/pdf", methods=["GET"])
def pdf_ebr(ebr_id):
    """Genera el PDF maestro del EBR para auditoría INVIMA / archivo regulatorio.

    Estructura:
      1. Header: producto, lote, MBR version, estado
      2. Identificación: iniciado/completado/liberado por con timestamps
      3. Reconciliación cantidad objetivo vs real + yield_pct
      4. Tabla de pasos ejecutados con operarios + e-signature IDs
      5. Tabla de IPCs reportados con conformidad
      6. Tabla de firmas electrónicas asociadas (de e_signatures)
      7. Footer: hash SHA256 del cuerpo + timestamp de generación
    """
    err = _require_login()
    if err:
        return err

    import hashlib
    import io
    from datetime import datetime, timezone
    from flask import send_file
    try:
        from fpdf import FPDF
    except ImportError:
        return jsonify({"error": "fpdf2 no instalado · agregar a requirements.txt"}), 500

    conn = get_db()
    ebr = conn.execute("SELECT * FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404

    mbr = conn.execute(
        "SELECT producto_nombre, version, lote_size_g FROM mbr_templates WHERE id = ?",
        (ebr["mbr_template_id"],),
    ).fetchone()
    pasos = conn.execute(
        "SELECT * FROM ebr_pasos_ejecutados WHERE ebr_id = ? ORDER BY orden",
        (ebr_id,),
    ).fetchall()
    ipcs = conn.execute(
        """SELECT r.*, s.parametro AS p, s.unidad AS u,
                  s.valor_min AS vmin, s.valor_max AS vmax
           FROM ipc_resultados r JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
           ORDER BY r.medido_at_utc""",
        (ebr_id,),
    ).fetchall()
    # Audit 3-jun · el legajo debe incluir TODAS las estaciones (no solo pasos/
    # IPC): pesajes con 2ª firma, conciliación de material, artes/codificación y
    # observaciones. Deploy-safe: si una tabla no existe, queda lista vacía.
    def _q(sql, *p):
        try:
            return conn.execute(sql, p).fetchall()
        except Exception:
            return []
    pesajes = _q(
        "SELECT material_id, material_nombre, cantidad_teorica_g, cantidad_real_g, "
        "delta_g, delta_pct, lote_mp, pesado_por, verificado_por, verificado_at_utc "
        "FROM ebr_pesajes WHERE ebr_id=? ORDER BY id", ebr_id)
    concil = _q(
        "SELECT tipo, material_nombre, lote_material, cant_requerida, cant_recibida, "
        "cant_devuelta, cant_utilizada, registrado_por FROM ebr_conciliacion_material "
        "WHERE ebr_id=? ORDER BY id", ebr_id)
    artes = _q(
        "SELECT descripcion, codigo_lote, codigo_vencimiento, aprobado_por, "
        "aprobado_at_utc FROM ebr_artes_codificacion WHERE ebr_id=? ORDER BY id", ebr_id)
    observs = _q(
        "SELECT descripcion, registrado_por, registrado_at_utc "
        "FROM ebr_observaciones WHERE ebr_id=? ORDER BY id", ebr_id)
    # MyBatch ①②⑦ · precauciones, despeje, registros físicos (audit 3-jun)
    precs = _q("SELECT tipo, descripcion, registrado_por FROM ebr_precauciones "
               "WHERE ebr_id=? ORDER BY id", ebr_id)
    despejes = _q("SELECT area_limpia, sin_producto_anterior, equipos_limpios, "
                  "documentacion_ok, conforme, observaciones, realizado_por, "
                  "realizado_at_utc FROM ebr_despeje_linea WHERE ebr_id=? ORDER BY id", ebr_id)
    regfis = _q("SELECT descripcion, archivo_nombre, registrado_por, registrado_at_utc "
                "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id", ebr_id)
    firmas = conn.execute(
        """SELECT meaning, signer_username, signer_full_name, signer_cedula,
                  signer_cargo, signed_at_utc, comment
           FROM e_signatures
           WHERE (record_table='ebr_ejecuciones' AND record_id=?)
              OR (record_table='ebr_pasos_ejecutados' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_pasos_ejecutados WHERE ebr_id=?))
              OR (record_table='ipc_resultados' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ipc_resultados WHERE ebr_id=?))
              OR (record_table='ebr_pesajes' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_pesajes WHERE ebr_id=?))
              OR (record_table='ebr_pesajes' AND record_id LIKE ? )
              OR (record_table='ebr_artes_codificacion' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_artes_codificacion WHERE ebr_id=?))
           ORDER BY signed_at_utc""",
        (str(ebr_id), ebr_id, ebr_id, ebr_id, f"{ebr_id}:%", ebr_id),
    ).fetchall()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe_pdf(f"Executed Batch Record · Lote {ebr['lote']}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe_pdf(f"Producto: {mbr['producto_nombre']} · MBR v{ebr['mbr_version']}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 6, _safe_pdf(f"Estado: {ebr['estado'].upper()}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Identificación
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("1. Identificación del lote"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, _safe_pdf(f"Iniciado por: {ebr['iniciado_por']}  ·  {ebr['iniciado_at_utc']} UTC"),
             new_x="LMARGIN", new_y="NEXT")
    if ebr["completado_at_utc"]:
        pdf.cell(0, 5, _safe_pdf(f"Completado: {ebr['completado_at_utc']} UTC"),
                 new_x="LMARGIN", new_y="NEXT")
    if ebr["liberado_at_utc"]:
        pdf.cell(0, 5, _safe_pdf(
            f"Liberado por: {ebr['liberado_por']}  ·  {ebr['liberado_at_utc']} UTC  ·  "
            f"firma e-sig #{ebr['liberado_signature_id']}"),
                 new_x="LMARGIN", new_y="NEXT")
    if ebr["rechazado_motivo"]:
        pdf.cell(0, 5, _safe_pdf(f"RECHAZADO · motivo: {ebr['rechazado_motivo']}"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Reconciliación
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("2. Reconciliación cantidad"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    obj = ebr["cantidad_objetivo_g"]
    real = ebr["cantidad_real_g"]
    yld = ebr["yield_pct"]
    pdf.cell(0, 5, _safe_pdf(
        f"Objetivo: {obj:,.2f} g   ·   Real: {real:,.2f} g   ·   Yield: {yld:.2f} %"
        if real is not None else
        f"Objetivo: {obj:,.2f} g   ·   Real: pendiente"),
        new_x="LMARGIN", new_y="NEXT")
    # Batch C · rendimiento por unidades (Envasado/Acondicionamiento)
    try:
        _uds_t = ebr["unidades_teoricas"]; _uds_b = ebr["unidades_buenas_real"]
        _yld_u = ebr["yield_uds_pct"]
    except Exception:
        _uds_t = _uds_b = _yld_u = None
    if _uds_b is not None or _yld_u is not None:
        pdf.cell(0, 5, _safe_pdf(
            f"Unidades buenas: {_uds_b or 0:,.0f}   ·   teóricas: {_uds_t or 0:,.0f}"
            + (f"   ·   Yield uds: {_yld_u:.2f} %" if _yld_u is not None else "")),
            new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def _line(text, h=5, font_size=9, italic=False):
        """multi_cell que siempre arranca al margen izquierdo (evita FPDFException)."""
        pdf.set_x(pdf.l_margin)
        if italic:
            pdf.set_font("Helvetica", "I", font_size)
        else:
            pdf.set_font("Helvetica", "", font_size)
        pdf.multi_cell(0, h, _safe_pdf(text))

    # Pasos ejecutados (formato lista)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf(f"3. Pasos ejecutados ({len(pasos)})"),
             new_x="LMARGIN", new_y="NEXT")
    for p in pasos:
        sig_str = f"#{p['e_sign_id']}" if p["e_sign_id"] else "-"
        if p["qc_e_sign_id"]:
            sig_str += f" QC#{p['qc_e_sign_id']}"
        _line(f"Paso {p['orden']}: {p['descripcion']}", h=5, font_size=9)
        _line(
            f"   operario: {p['operario_username'] or '-'}  "
            f"completado: {(p['completado_at_utc'] or '-')[:19]} UTC  "
            f"e-sign: {sig_str}",
            h=4, font_size=8,
        )
        if p["observaciones"]:
            _line(f"   obs: {p['observaciones']}", h=4, font_size=8, italic=True)
    pdf.ln(2)

    # IPCs (formato lista)
    if ipcs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4. In-Process Controls ({len(ipcs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for ipc in ipcs:
            conf = "Conforme" if ipc["conforme"] == 1 else ("NO conforme" if ipc["conforme"] == 0 else "pendiente")
            rango = ""
            if ipc["vmin"] is not None or ipc["vmax"] is not None:
                rango = f" [rango: {ipc['vmin']} - {ipc['vmax']} {ipc['u'] or ''}]"
            _line(
                f"{ipc['p']}: {ipc['valor_medido']} {ipc['u'] or ''}"
                f"{rango}  ·  {conf}  ·  {ipc['medido_por']}  ·  "
                f"{(ipc['medido_at_utc'] or '')[:19]} UTC",
                h=5, font_size=9,
            )
        pdf.ln(2)

    # Pesajes de materias primas (con 2ª firma de verificación)
    if pesajes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4b. Pesajes de materias primas ({len(pesajes)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for w in pesajes:
            dp = w["delta_pct"]
            dp_s = f"{dp:+.2f}%" if dp is not None else "-"
            verif = (f"verificó: {w['verificado_por']} ({(w['verificado_at_utc'] or '')[:19]} UTC)"
                     if w["verificado_por"] else "SIN 2ª firma")
            _line(
                f"{w['material_id']} {w['material_nombre'] or ''}: teórico "
                f"{w['cantidad_teorica_g']} g · real {w['cantidad_real_g']} g · "
                f"delta {w['delta_g']} g ({dp_s}) · lote MP {w['lote_mp'] or '-'}",
                h=5, font_size=9)
            _line(f"   pesó: {w['pesado_por'] or '-'}  ·  {verif}", h=4, font_size=8)
        pdf.ln(2)

    # Conciliación de material de envase/empaque
    if concil:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4c. Conciliación de material ({len(concil)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for m in concil:
            _line(
                f"[{m['tipo']}] {m['material_nombre']} (lote {m['lote_material'] or '-'}): "
                f"requerida {m['cant_requerida']} · recibida {m['cant_recibida']} · "
                f"devuelta {m['cant_devuelta']} · utilizada {m['cant_utilizada']}  ·  "
                f"{m['registrado_por'] or '-'}",
                h=5, font_size=9)
        pdf.ln(2)

    # Artes / codificación (acondicionamiento)
    if artes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4d. Artes / codificación ({len(artes)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for a in artes:
            ap = (f"APROBADO por {a['aprobado_por']} ({(a['aprobado_at_utc'] or '')[:19]} UTC)"
                  if a["aprobado_por"] else "SIN aprobar")
            _line(
                f"{a['descripcion']} · cód. lote {a['codigo_lote'] or '-'} · "
                f"venc. {a['codigo_vencimiento'] or '-'}  ·  {ap}",
                h=5, font_size=9)
        pdf.ln(2)

    # Observaciones / bitácora
    if observs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4e. Observaciones / bitácora ({len(observs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for o in observs:
            _line(f"{(o['registrado_at_utc'] or '')[:19]} UTC · {o['registrado_por'] or '-'}: "
                  f"{o['descripcion']}", h=5, font_size=9)
        pdf.ln(2)

    # Precauciones y equipos (MyBatch ①)
    if precs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4f. Precauciones y equipos ({len(precs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for p in precs:
            _line(f"[{p['tipo']}] {p['descripcion']}  ·  {p['registrado_por'] or '-'}",
                  h=5, font_size=9)
        pdf.ln(2)

    # Despeje de línea (MyBatch ②)
    if despejes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf("4g. Despeje de línea"), new_x="LMARGIN", new_y="NEXT")
        for dl in despejes:
            def _sn(v):
                return "SI" if v else "NO"
            _line(f"Área limpia: {_sn(dl['area_limpia'])} · Sin producto anterior: "
                  f"{_sn(dl['sin_producto_anterior'])} · Equipos limpios: "
                  f"{_sn(dl['equipos_limpios'])} · Documentación: {_sn(dl['documentacion_ok'])}",
                  h=5, font_size=9)
            _line(f"   Resultado: {'CONFORME' if dl['conforme'] else 'NO CONFORME'} · "
                  f"{dl['realizado_por'] or '-'} · {(dl['realizado_at_utc'] or '')[:19]} UTC"
                  + (f" · {dl['observaciones']}" if dl['observaciones'] else ""),
                  h=4, font_size=8)
        pdf.ln(2)

    # Registros físicos (MyBatch ⑦)
    if regfis:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4h. Registros físicos ({len(regfis)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for rg in regfis:
            _adj = f" [PDF: {rg['archivo_nombre']}]" if rg['archivo_nombre'] else ""
            _line(f"{rg['descripcion']}{_adj}  ·  {rg['registrado_por'] or '-'}",
                  h=5, font_size=9)
        pdf.ln(2)

    # Firmas electrónicas
    if firmas:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"5. Firmas electrónicas ({len(firmas)}) · Part 11 §11.50"),
                 new_x="LMARGIN", new_y="NEXT")
        for f in firmas:
            _line(
                f"{f['signed_at_utc']} UTC · {f['meaning']} · "
                f"{f['signer_username']} ({f['signer_full_name'] or '-'}, "
                f"cédula {f['signer_cedula'] or '-'}, {f['signer_cargo'] or '-'})",
                h=5, font_size=9,
            )
            if f["comment"]:
                _line(f'   "{f["comment"]}"', h=4, font_size=8, italic=True)

    # 6. Disposición del lote / Certificado de liberación
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("6. Disposición del lote"), new_x="LMARGIN", new_y="NEXT")
    _est = (ebr["estado"] or "").upper()
    if ebr["estado"] == "liberado":
        _line(f"DECISIÓN QC: LIBERADO · por {ebr['liberado_por']} · "
              f"{(ebr['liberado_at_utc'] or '')[:19]} UTC · firma e-sig "
              f"#{ebr['liberado_signature_id']}", h=6, font_size=10)
    elif ebr["estado"] == "rechazado":
        _line(f"DECISIÓN QC: RECHAZADO · motivo: {ebr['rechazado_motivo'] or '-'}",
              h=6, font_size=10)
    else:
        _line(f"DECISIÓN QC: PENDIENTE (estado actual: {_est})", h=6, font_size=10)
    if yld is not None:
        _line(f"Rendimiento: {yld:.2f} %", h=5, font_size=9)

    # Hash de contenido (NO de los bytes del PDF · esos cambian con timestamp).
    # Este hash es estable: depende solo de los datos del EBR. Sirve para que
    # el auditor verifique que el PDF que tiene en mano corresponde a un EBR
    # específico y no fue alterado el record fuente.
    payload = "|".join([
        str(ebr["id"]), ebr["lote"], str(ebr["mbr_template_id"]),
        str(ebr["mbr_version"]), ebr["estado"], ebr["iniciado_at_utc"],
        str(ebr["cantidad_objetivo_g"]),
        str(ebr["cantidad_real_g"]) if ebr["cantidad_real_g"] is not None else "-",
        str(ebr["yield_pct"]) if ebr["yield_pct"] is not None else "-",
        str(ebr["liberado_signature_id"] or "-"),
        str(len(pasos)), str(len(ipcs)), str(len(firmas)),
        # Audit 3-jun · sellar también las estaciones nuevas en el hash
        str(len(pesajes)), str(len(concil)), str(len(artes)), str(len(observs)),
        str(len(precs)), str(len(despejes)), str(len(regfis)),
    ])
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Footer con hash · agregar ANTES de output() final
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 4, _safe_pdf(f"Generado: {gen_at}  ·  EOS app.eossuite.com  ·  EBR id #{ebr_id}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 4, _safe_pdf(f"SHA-256 del contenido EBR: {content_hash}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    final_bytes = bytes(pdf.output())
    pdf_hash = content_hash

    # Audit log de la descarga (importante para Part 11 evidencia)
    audit_log(None, usuario=session.get("compras_user", ""),
              accion="DOWNLOAD_EBR_PDF", tabla="ebr_ejecuciones",
              registro_id=ebr_id,
              detalle=f"hash={pdf_hash[:16]} bytes={len(final_bytes)}")

    return send_file(
        io.BytesIO(final_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"EBR_{ebr['lote']}.pdf",
    )


# ════════════════════════════════════════════════════════════════════════════
# Reconciliación granular pesajes MP (F7)
# ════════════════════════════════════════════════════════════════════════════
# Captura cada pesaje individual del operario durante un paso de
# dispensación. Compara contra el teórico calculado de formula_items
# (porcentaje × cantidad_objetivo_g del lote).

def _calcular_teoricos_mp(conn, producto_nombre, lote_size_g):
    """Devuelve {material_id: cantidad_teorica_g} desde formula_items.

    Si la fórmula no existe (producto no fórmula-driven), devuelve dict vacío.
    """
    rows = conn.execute(
        """SELECT material_id, material_nombre, porcentaje
           FROM formula_items WHERE producto_nombre = ?""",
        (producto_nombre,),
    ).fetchall()
    teoricos = {}
    for r in rows:
        teoricos[r["material_id"]] = {
            "material_id": r["material_id"],
            "material_nombre": r["material_nombre"] or "",
            "porcentaje": r["porcentaje"],
            "cantidad_teorica_g": (r["porcentaje"] / 100.0) * lote_size_g,
        }
    return teoricos


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes", methods=["POST"])
def reportar_pesaje(ebr_id):
    """Operario reporta el pesaje real de un MP.

    Body: {material_id, cantidad_real_g, lote_mp?, ebr_paso_id?,
           signature_id?, notas?}
    El cantidad_teorica_g se calcula del lado del servidor desde
    formula_items + cantidad_objetivo_g del EBR (no se acepta del cliente
    para evitar manipulación). delta_g y delta_pct también se calculan acá.
    """
    # Audit 3-jun · era _require_login (cualquier usuario logueado). Es una
    # mutación de registro de lote regulado → exige ejecutor (Planta/Calidad/
    # Admin), igual que pasos/conciliación. Evita escalada de privilegios.
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    material_id = (body.get("material_id") or "").strip()
    if not material_id:
        return jsonify({"error": "material_id requerido"}), 400
    try:
        real = float(body.get("cantidad_real_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_real_g inválido"}), 400
    if real < 0:
        return jsonify({"error": "cantidad_real_g debe ser >= 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        """SELECT e.estado, e.cantidad_objetivo_g, m.producto_nombre
           FROM ebr_ejecuciones e
           JOIN mbr_templates m ON m.id = e.mbr_template_id
           WHERE e.id = ?""",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    # Calcular teórico desde formula_items
    teoricos = _calcular_teoricos_mp(conn, ebr["producto_nombre"],
                                     ebr["cantidad_objetivo_g"])
    spec = teoricos.get(material_id)
    if not spec:
        return jsonify({
            "error": f"material_id '{material_id}' no está en formula_items "
                      f"de '{ebr['producto_nombre']}'",
        }), 400

    teorico = spec["cantidad_teorica_g"]
    delta = real - teorico
    delta_pct = (delta / teorico * 100.0) if teorico > 0 else None

    # Validar e-sign. Audit 3-jun · con el motor encendido (EBR_MODE != off)
    # la 1ª firma del pesaje es OBLIGATORIA (Part 11 / dato de lote regulado).
    user = session.get("compras_user", "")
    signature_id = body.get("signature_id")
    if not signature_id and EBR_MODE != "off":
        return jsonify({
            "error": "Falta la e-firma del pesaje (firmá como ejecutor).",
            "codigo": "FIRMA_REQUERIDA",
            "record_table": "ebr_pesajes",
            "record_id": f"{ebr_id}:{material_id}",
            "meaning": "ejecuta",
        }), 400
    if signature_id:
        if not _validar_signature(
            cur, signature_id, record_table="ebr_pesajes",
            record_id=f"{ebr_id}:{material_id}",
            meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido para este pesaje"}), 400

    cur.execute(
        """INSERT INTO ebr_pesajes
             (ebr_id, ebr_paso_id, material_id, material_nombre,
              cantidad_teorica_g, cantidad_real_g, delta_g, delta_pct,
              lote_mp, pesado_por, pesado_at_utc, e_sign_id, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?, ?)""",
        (ebr_id, body.get("ebr_paso_id"), material_id, spec["material_nombre"],
         teorico, real, delta, delta_pct,
         (body.get("lote_mp") or "").strip(), user,
         int(signature_id) if signature_id else None,
         (body.get("notas") or "").strip()),
    )
    pid = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="REPORTAR_PESAJE",
              tabla="ebr_pesajes", registro_id=pid,
              despues={"ebr_id": ebr_id, "material_id": material_id,
                        "real": real, "teorico": teorico, "delta_pct": delta_pct})
    return jsonify({
        "ok": True, "id": pid,
        "cantidad_teorica_g": teorico,
        "cantidad_real_g": real,
        "delta_g": delta,
        "delta_pct": delta_pct,
    }), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes", methods=["GET"])
def listar_pesajes(ebr_id):
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, ebr_paso_id, material_id, material_nombre,
                  cantidad_teorica_g, cantidad_real_g, delta_g, delta_pct,
                  lote_mp, pesado_por, pesado_at_utc, e_sign_id, notas,
                  COALESCE(verificado_por,'') AS verificado_por,
                  verificado_at_utc, verificado_e_sign_id
           FROM ebr_pesajes WHERE ebr_id = ?
           ORDER BY pesado_at_utc""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes/<int:pesaje_id>/verificar",
          methods=["POST"])
def verificar_pesaje_ebr(ebr_id, pesaje_id):
    """2ª firma GMP: una 2ª persona (Calidad/Admin) VERIFICA un pesaje ya
    reportado. Reemplazo del `verified_weight` de MyBatch.

    Reglas (cero-error / GMP):
      · Solo Calidad o Admin verifican (segregación de funciones).
      · El verificador NO puede ser quien pesó.
      · Solo sobre EBR iniciado/en_proceso (post-liberación es inmutable).
      · Requiere e-firma meaning='supervisa' sobre record_table='ebr_pesajes',
        record_id=pesaje_id (mismo patrón que la QC de pasos).
      · Un pesaje ya verificado no se re-verifica.
    """
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in (CALIDAD_USERS | ADMIN_USERS):
        return jsonify({
            "error": "Solo Calidad o Admin pueden verificar pesajes (2ª firma GMP)"
        }), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    pes = cur.execute(
        """SELECT id, pesado_por, COALESCE(verificado_por,'') AS verificado_por
           FROM ebr_pesajes WHERE id = ? AND ebr_id = ?""",
        (pesaje_id, ebr_id),
    ).fetchone()
    if not pes:
        return jsonify({"error": "pesaje no encontrado"}), 404
    if (pes["verificado_por"] or "").strip():
        return jsonify({"error": "pesaje ya verificado"}), 409
    # Segregación de funciones GMP · quien verifica ≠ quien pesó (igual que la
    # regla de la QC de pasos en completar_paso_ebr).
    if user == (pes["pesado_por"] or ""):
        return jsonify({
            "error": "El verificador no puede ser quien pesó (segregación de funciones GMP)"
        }), 409

    if not signature_id:
        return jsonify({
            "error": "verificación requiere e-signature · meaning='supervisa' "
                      "record_table='ebr_pesajes'",
            "pesaje_id": pesaje_id,
        }), 400
    if not _validar_signature(
        cur, signature_id, record_table="ebr_pesajes",
        record_id=pesaje_id, meaning="supervisa", signer_username=user,
    ):
        return jsonify({"error": "signature_id inválido para esta verificación"}), 400

    cur.execute(
        """UPDATE ebr_pesajes
             SET verificado_por = ?,
                 verificado_at_utc = datetime('now', 'utc'),
                 verificado_e_sign_id = ?
           WHERE id = ?""",
        (user, int(signature_id), pesaje_id),
    )
    audit_log(cur, usuario=user, accion="VERIFICAR_PESAJE_EBR",
              tabla="ebr_pesajes", registro_id=pesaje_id,
              despues={"ebr_id": ebr_id, "verificado_por": user})
    conn.commit()
    return jsonify({"ok": True, "verificado_por": user})


@bp.route("/api/brd/ebr/<int:ebr_id>/conciliacion-material", methods=["GET"])
def listar_conciliacion_material(ebr_id):
    """Conciliación de material de envase/empaque del legajo (MyBatch OF/OA):
    cuánto se requirió / recibió / devolvió / utilizó."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, tipo, material_codigo, material_nombre, lote_material,
                  cant_requerida, cant_recibida, cant_devuelta, cant_utilizada,
                  registrado_por, registrado_at_utc, e_sign_id, notas
           FROM ebr_conciliacion_material WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/conciliacion-material", methods=["POST"])
def registrar_conciliacion_material(ebr_id):
    """Registra una línea de conciliación de material (envase/etiqueta/estuche...).

    utilizada = recibida - devuelta si no se especifica. Solo sobre EBR
    iniciado/en_proceso (post-liberación es inmutable · guard + trigger)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    nombre = (body.get("material_nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "material_nombre requerido"}), 400

    def _num(k):
        try:
            return max(0.0, float(body.get(k) or 0))
        except (ValueError, TypeError):
            return 0.0

    requerida = _num("cant_requerida")
    recibida = _num("cant_recibida")
    devuelta = _num("cant_devuelta")
    if body.get("cant_utilizada") not in (None, ""):
        utilizada = _num("cant_utilizada")
    else:
        utilizada = max(0.0, recibida - devuelta)

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    tipo = (body.get("tipo") or "envase").strip().lower()
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_conciliacion_material
             (ebr_id, tipo, material_codigo, material_nombre, lote_material,
              cant_requerida, cant_recibida, cant_devuelta, cant_utilizada,
              registrado_por, registrado_at_utc, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (ebr_id, tipo, (body.get("material_codigo") or "").strip(), nombre,
         (body.get("lote_material") or "").strip(),
         requerida, recibida, devuelta, utilizada, user,
         (body.get("notas") or "").strip()),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_CONCILIACION_MATERIAL",
              tabla="ebr_conciliacion_material", registro_id=rid,
              despues={"ebr_id": ebr_id, "material": nombre,
                        "utilizada": utilizada})
    conn.commit()
    return jsonify({"ok": True, "id": rid, "cant_utilizada": utilizada}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/artes", methods=["GET"])
def listar_artes_codificacion(ebr_id):
    """Artes/codificación del legajo (gate de etiquetado · MyBatch OA)."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, descripcion, codigo_lote, codigo_vencimiento,
                  COALESCE(aprobado_por,'') AS aprobado_por, aprobado_at_utc,
                  e_sign_id, creado_por, creado_at_utc, notas
           FROM ebr_artes_codificacion WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/artes", methods=["POST"])
def registrar_arte_codificacion(ebr_id):
    """Registra una línea de arte/codificación (descripción + código lote/venc).
    Aún sin aprobar · la aprobación va por /artes/<id>/aprobar con e-firma."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_artes_codificacion
             (ebr_id, descripcion, codigo_lote, codigo_vencimiento,
              creado_por, creado_at_utc, notas)
           VALUES (?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (ebr_id, desc, (body.get("codigo_lote") or "").strip(),
         (body.get("codigo_vencimiento") or "").strip(), user,
         (body.get("notas") or "").strip()),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_ARTE_CODIFICACION",
              tabla="ebr_artes_codificacion", registro_id=rid,
              despues={"ebr_id": ebr_id, "descripcion": desc})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/artes/<int:arte_id>/aprobar",
          methods=["POST"])
def aprobar_arte_codificacion(ebr_id, arte_id):
    """Aprueba el arte/codificación (gate de etiquetado). Solo Calidad/Admin,
    con e-firma meaning='aprueba'. No re-aprueba."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in (CALIDAD_USERS | ADMIN_USERS):
        return jsonify({
            "error": "Solo Calidad o Admin aprueban artes/codificación"
        }), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    arte = cur.execute(
        """SELECT id, COALESCE(aprobado_por,'') AS aprobado_por
           FROM ebr_artes_codificacion WHERE id = ? AND ebr_id = ?""",
        (arte_id, ebr_id),
    ).fetchone()
    if not arte:
        return jsonify({"error": "arte/codificación no encontrada"}), 404
    if (arte["aprobado_por"] or "").strip():
        return jsonify({"error": "arte/codificación ya aprobada"}), 409
    if not signature_id:
        return jsonify({
            "error": "aprobación requiere e-signature · meaning='aprueba' "
                      "record_table='ebr_artes_codificacion'",
            "arte_id": arte_id,
        }), 400
    if not _validar_signature(
        cur, signature_id, record_table="ebr_artes_codificacion",
        record_id=arte_id, meaning="aprueba", signer_username=user,
    ):
        return jsonify({"error": "signature_id inválido para esta aprobación"}), 400

    cur.execute(
        """UPDATE ebr_artes_codificacion
             SET aprobado_por = ?, aprobado_at_utc = datetime('now', 'utc'),
                 e_sign_id = ?
           WHERE id = ?""",
        (user, int(signature_id), arte_id),
    )
    audit_log(cur, usuario=user, accion="APROBAR_ARTE_CODIFICACION",
              tabla="ebr_artes_codificacion", registro_id=arte_id,
              despues={"ebr_id": ebr_id, "aprobado_por": user})
    conn.commit()
    return jsonify({"ok": True, "aprobado_por": user})


@bp.route("/api/brd/ebr/<int:ebr_id>/observaciones", methods=["GET"])
def listar_observaciones_ebr(ebr_id):
    """Bitácora de observaciones generales del proceso (MyBatch)."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, descripcion, registrado_por, registrado_at_utc
           FROM ebr_observaciones WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/observaciones", methods=["POST"])
def registrar_observacion_ebr(ebr_id):
    """Agrega una observación general al legajo (append-only · solo EBR editable)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_observaciones
             (ebr_id, descripcion, registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, datetime('now', 'utc'))""",
        (ebr_id, desc[:1000], user),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_OBSERVACION_EBR",
              tabla="ebr_observaciones", registro_id=rid,
              despues={"ebr_id": ebr_id})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


# ── MyBatch ② · Despeje de línea ────────────────────────────────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/despeje", methods=["GET"])
def listar_despeje_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT * FROM ebr_despeje_linea WHERE ebr_id=? ORDER BY id DESC",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje", methods=["POST"])
def registrar_despeje_ebr(ebr_id):
    """Registra el despeje de línea del legajo (checklist CUMPLE · MyBatch ②)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    def _b(k):
        return 1 if body.get(k) in (1, True, '1', 'true', 'on') else 0
    al, sp, eq, doc = _b("area_limpia"), _b("sin_producto_anterior"), _b("equipos_limpios"), _b("documentacion_ok")
    conforme = 1 if (al and sp and eq and doc) else 0
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_despeje_linea
             (ebr_id, area_limpia, sin_producto_anterior, equipos_limpios,
              documentacion_ok, conforme, observaciones, realizado_por,
              realizado_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, al, sp, eq, doc, conforme,
         (body.get("observaciones") or "").strip()[:500], user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_DESPEJE_EBR",
              tabla="ebr_despeje_linea", registro_id=rid,
              despues={"ebr_id": ebr_id, "conforme": conforme})
    conn.commit()
    return jsonify({"ok": True, "id": rid, "conforme": conforme}), 201


# ── MyBatch ① · Precauciones + Equipos ──────────────────────────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/precauciones", methods=["GET"])
def listar_precauciones_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT * FROM ebr_precauciones WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/precauciones", methods=["POST"])
def registrar_precaucion_ebr(ebr_id):
    """Agrega una precaución o equipo usado al legajo (MyBatch ①)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    tipo = (body.get("tipo") or "precaucion").strip().lower()
    if tipo not in ("precaucion", "equipo"):
        tipo = "precaucion"
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_precauciones
             (ebr_id, tipo, descripcion, registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, tipo, desc[:500], user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_PRECAUCION_EBR",
              tabla="ebr_precauciones", registro_id=rid,
              despues={"ebr_id": ebr_id, "tipo": tipo})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


# ── MyBatch ⑦ · Registros físicos (adjuntar PDF/referencia) ─────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos", methods=["GET"])
def listar_registros_fisicos_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT id, ebr_id, descripcion, tipo, archivo_nombre, "
            "(CASE WHEN COALESCE(archivo_b64,'')!='' THEN 1 ELSE 0 END) AS tiene_pdf, "
            "registrado_por, registrado_at_utc "
            "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos", methods=["POST"])
def registrar_registro_fisico_ebr(ebr_id):
    """Adjunta un registro físico al legajo: descripción + PDF opcional (base64)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    b64 = body.get("archivo_b64") or None
    if b64 and len(b64) > 8 * 1024 * 1024:  # ~6MB PDF
        return jsonify({"error": "archivo muy grande (max ~6MB)"}), 413
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_registros_fisicos
             (ebr_id, descripcion, tipo, archivo_nombre, archivo_b64,
              registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, desc[:300], (body.get("tipo") or "registro").strip()[:40],
         (body.get("archivo_nombre") or "").strip()[:120], b64, user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_REGISTRO_FISICO_EBR",
              tabla="ebr_registros_fisicos", registro_id=rid,
              despues={"ebr_id": ebr_id, "tiene_pdf": bool(b64)})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos/<int:rid>/pdf", methods=["GET"])
def descargar_registro_fisico_pdf(ebr_id, rid):
    err = _require_login()
    if err:
        return err
    import base64 as _b64
    from flask import send_file
    import io as _io
    row = get_db().execute(
        "SELECT archivo_b64, archivo_nombre FROM ebr_registros_fisicos "
        "WHERE id=? AND ebr_id=?", (rid, ebr_id)).fetchone()
    if not row or not row["archivo_b64"]:
        return jsonify({"error": "sin PDF"}), 404
    try:
        raw = _b64.b64decode(row["archivo_b64"])
    except Exception:
        return jsonify({"error": "PDF inválido"}), 500
    return send_file(_io.BytesIO(raw), mimetype="application/pdf",
                     as_attachment=True,
                     download_name=(row["archivo_nombre"] or f"registro_{rid}.pdf"))


@bp.route("/api/brd/ebr/<int:ebr_id>/reconciliacion", methods=["GET"])
def reconciliacion_ebr(ebr_id):
    """Resumen MP-por-MP de teórico vs real.

    Threshold de outlier: |delta_pct| > 5% se marca para revisión QC.
    Se exponen 3 listas: ok (sin outliers), outliers (>5% delta),
    no_pesados (MPs de la fórmula que no tienen pesaje todavía).
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    ebr = conn.execute(
        """SELECT e.cantidad_objetivo_g, e.cantidad_real_g, e.yield_pct,
                  e.estado, m.producto_nombre
           FROM ebr_ejecuciones e
           JOIN mbr_templates m ON m.id = e.mbr_template_id
           WHERE e.id = ?""", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404

    teoricos = _calcular_teoricos_mp(conn, ebr["producto_nombre"],
                                     ebr["cantidad_objetivo_g"])
    pesajes_rows = conn.execute(
        """SELECT material_id, SUM(cantidad_real_g) AS suma_real,
                  COUNT(*) AS n_pesajes,
                  GROUP_CONCAT(DISTINCT lote_mp) AS lotes_mp
           FROM ebr_pesajes WHERE ebr_id = ? AND material_id != ''
           GROUP BY material_id""",
        (ebr_id,),
    ).fetchall()
    pesajes = {r["material_id"]: dict(r) for r in pesajes_rows}

    OUTLIER_THRESHOLD_PCT = 5.0
    ok, outliers, no_pesados = [], [], []
    total_teorico = 0.0
    total_real = 0.0
    for mid, spec in teoricos.items():
        teorico = spec["cantidad_teorica_g"]
        total_teorico += teorico
        p = pesajes.get(mid)
        if not p:
            no_pesados.append({
                "material_id": mid,
                "material_nombre": spec["material_nombre"],
                "cantidad_teorica_g": teorico,
            })
            continue
        real = p["suma_real"] or 0
        total_real += real
        delta = real - teorico
        delta_pct = (delta / teorico * 100.0) if teorico > 0 else None
        item = {
            "material_id": mid,
            "material_nombre": spec["material_nombre"],
            "cantidad_teorica_g": teorico,
            "cantidad_real_g": real,
            "delta_g": delta,
            "delta_pct": delta_pct,
            "n_pesajes": p["n_pesajes"],
            "lotes_mp": (p["lotes_mp"] or "").split(",") if p["lotes_mp"] else [],
        }
        if delta_pct is not None and abs(delta_pct) > OUTLIER_THRESHOLD_PCT:
            outliers.append(item)
        else:
            ok.append(item)

    return jsonify({
        "ebr_id": ebr_id,
        "producto_nombre": ebr["producto_nombre"],
        "cantidad_objetivo_g": ebr["cantidad_objetivo_g"],
        "cantidad_real_g_lote": ebr["cantidad_real_g"],
        "yield_pct_lote": ebr["yield_pct"],
        "totales_pesajes": {
            "total_teorico_g": total_teorico,
            "total_real_g": total_real,
            "delta_g": total_real - total_teorico,
            "delta_pct": ((total_real - total_teorico) / total_teorico * 100.0) if total_teorico > 0 else None,
        },
        "ok": ok,
        "outliers": outliers,
        "no_pesados": no_pesados,
        "outlier_threshold_pct": OUTLIER_THRESHOLD_PCT,
        "estado_ebr": ebr["estado"],
    })


# ──────────────────────────────────────────────────────────────────────────
# Órdenes de Producción · vista unificada estilo MyBatch (Sebastián 4-jun-2026)
#
# PASO 1 (100% aditivo · SOLO LECTURA): surface las "Órdenes de Producción"
# como MyBatch (N° orden OP-AAAA-NNNN · lote · producto · cant teórica/producida/
# aprobada · estado). Une los DOS mundos que hoy están separados:
#   - ebr_ejecuciones  → legajos formales (ya tienen numero_op, fase, estados).
#   - producciones      → registros simples del formulario "Registrar Producción"
#                         (sin N° de orden ni legajo · se muestran como 'simple').
# NO toca el formulario, ni el descuento, ni el motor EBR. Solo lee y presenta.
# ──────────────────────────────────────────────────────────────────────────

def _estado_orden_norm(origen, estado):
    """Mapea el estado interno al vocabulario MyBatch (En Proceso / Aprobado /
    Cancelado / Completado)."""
    e = (estado or "").strip().lower()
    if origen == "legajo":
        return {
            "iniciado": "En Proceso",
            "en_proceso": "En Proceso",
            "completado": "En Proceso · Cuarentena",
            "liberado": "Aprobado",
            "rechazado": "Rechazado",
        }.get(e, estado or "—")
    # registro simple (producciones)
    if e in ("completado", "completada"):
        return "Completado (registro simple)"
    if e in ("cancelado", "cancelada"):
        return "Cancelado"
    return estado or "Completado (registro simple)"


@bp.route("/api/brd/ordenes-unificadas", methods=["GET"])
def ordenes_unificadas():
    """Lista unificada de Órdenes de Producción (legajos EBR + registros simples).

    Query: ?fase=fabricacion|envasado|acondicionamiento (default fabricacion).
    Los registros simples (tabla producciones) solo aplican a 'fabricacion'.
    SOLO LECTURA · no escribe nada."""
    err = _require_login()
    if err:
        return err
    fase = (request.args.get("fase") or "fabricacion").strip().lower()
    if fase not in _FASES_VALIDAS:
        fase = "fabricacion"
    conn = get_db()
    items = []

    # 1) Legajos EBR (ya MyBatch-shaped) · producto vía mbr_templates
    try:
        ebr_rows = conn.execute(
            """SELECT e.id, e.numero_op, e.lote, e.estado,
                      e.cantidad_objetivo_g, e.cantidad_real_g,
                      COALESCE(e.ml_envasable, NULL) AS ml_envasable,
                      e.iniciado_at_utc, e.liberado_at_utc,
                      COALESCE(e.fase,'fabricacion') AS fase,
                      COALESCE(m.producto_nombre,'') AS producto
               FROM ebr_ejecuciones e
               LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id
               WHERE COALESCE(e.fase,'fabricacion') = ?
               ORDER BY e.iniciado_at_utc DESC""",
            (fase,),
        ).fetchall()
    except Exception as _e:
        log.warning("ordenes-unificadas EBR query fallo: %s", _e)
        ebr_rows = []
    for r in ebr_rows:
        rd = dict(r)
        liberado = bool(rd.get("liberado_at_utc"))
        items.append({
            "origen": "legajo",
            "numero_op": rd.get("numero_op") or f"EBR-{rd['id']}",
            "lote_bulk": rd.get("lote") or "",
            "producto": rd.get("producto") or "",
            "teorica_g": rd.get("cantidad_objetivo_g"),
            "producida_g": rd.get("cantidad_real_g"),
            "aprobada": (rd.get("cantidad_real_g") if liberado else None),
            "ml_envasable": rd.get("ml_envasable"),
            "estado": _estado_orden_norm("legajo", rd.get("estado")),
            "fecha": (rd.get("iniciado_at_utc") or "")[:10],
            "link": f"/brd/timeline/{rd['id']}",
            "ebr_id": rd["id"],
        })

    # 2) Registros simples (producciones) · solo en fabricación
    if fase == "fabricacion":
        try:
            prod_rows = conn.execute(
                """SELECT id, producto, COALESCE(cantidad,0) AS cantidad,
                          fecha, COALESCE(estado,'') AS estado,
                          COALESCE(lote,'') AS lote, COALESCE(operador,'') AS operador
                   FROM producciones
                   ORDER BY fecha DESC
                   LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas producciones query fallo: %s", _e)
            prod_rows = []
        for r in prod_rows:
            rd = dict(r)
            kg = float(rd.get("cantidad") or 0)
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"PROD-{rd['id']:05d}",
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": round(kg * 1000, 1),
                "producida_g": round(kg * 1000, 1),
                "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # orden global por fecha desc
    items.sort(key=lambda x: (x.get("fecha") or ""), reverse=True)
    resumen = {
        "total": len(items),
        "legajos": sum(1 for i in items if i["origen"] == "legajo"),
        "simples": sum(1 for i in items if i["origen"] == "simple"),
    }
    return jsonify({"ok": True, "fase": fase, "resumen": resumen, "ordenes": items})


_ORDENES_PROD_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Órdenes de Producción · EOS</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f3ff;color:#1e293b;margin:0;padding:20px}
.wrap{max-width:1200px;margin:0 auto}
h1{color:#7c3aed;font-size:22px;margin:0 0 4px}
.sub{color:#64748b;font-size:13px;margin-bottom:14px}
.tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tab{padding:8px 16px;border-radius:8px;background:#ede9fe;color:#5b21b6;font-weight:700;font-size:13px;cursor:pointer;border:none}
.tab.active{background:#7c3aed;color:#fff}
.card{background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:9px 8px;background:#f1f5f9;color:#475569;font-weight:700;font-size:11.5px;position:sticky;top:0}
td{padding:9px 8px;border-bottom:1px solid #f1f5f9;vertical-align:middle}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:#1e40af}
.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{padding:2px 9px;border-radius:11px;font-size:10.5px;font-weight:700;white-space:nowrap}
.proc{background:#fef9c3;color:#854d0e}.cuar{background:#dbeafe;color:#1e40af}
.apr{background:#dcfce7;color:#166534}.rech{background:#fee2e2;color:#991b1b}.simp{background:#f1f5f9;color:#475569}
.org{font-size:10px;padding:1px 6px;border-radius:8px;font-weight:700}
.org-l{background:#ede9fe;color:#6d28d9}.org-s{background:#f1f5f9;color:#64748b}
.muted{color:#94a3b8}a.legajo{color:#7c3aed;font-weight:700;text-decoration:none}
.summary{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.box{padding:7px 12px;border-radius:8px;font-size:12px;font-weight:700;background:#ede9fe;color:#5b21b6}
</style></head><body>
<div class="wrap">
<a href="/inventarios" style="color:#7c3aed;font-size:13px">&larr; Planta</a>
<h1>📋 Órdenes de Producción</h1>
<div class="sub">Vista unificada (solo lectura) · legajos EBR + registros de Fabricación · equivalente a MyBatch.</div>
<div class="tabs">
  <button class="tab active" data-fase="fabricacion" onclick="ver('fabricacion',this)">🏭 Fabricación (OP)</button>
  <button class="tab" data-fase="envasado" onclick="ver('envasado',this)">📦 Envasado (OF)</button>
  <button class="tab" data-fase="acondicionamiento" onclick="ver('acondicionamiento',this)">🎨 Acondicionamiento (OA)</button>
</div>
<div id="summary" class="summary"></div>
<div class="card"><div id="out">Cargando…</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return n==null?'—':Number(n).toLocaleString('es-CO')+' g';}
function pill(estado){
  var e=(estado||'').toLowerCase(); var c='simp';
  if(e.indexOf('cuarentena')>=0)c='cuar'; else if(e.indexOf('proceso')>=0)c='proc';
  else if(e.indexOf('aprob')>=0)c='apr'; else if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)c='rech';
  return '<span class="pill '+c+'">'+esc(estado)+'</span>';
}
async function ver(fase,btn){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  if(btn)btn.classList.add('active');
  var out=document.getElementById('out'); out.innerHTML='Cargando…';
  try{
    var r=await fetch('/api/brd/ordenes-unificadas?fase='+encodeURIComponent(fase),{credentials:'same-origin'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok||!d.ok){out.innerHTML='<span style="color:#b91c1c">Error: '+esc((d&&d.error)||r.status)+'</span>';return;}
    document.getElementById('summary').innerHTML=
      '<div class="box">'+d.resumen.total+' órdenes</div>'+
      '<div class="box">'+d.resumen.legajos+' con legajo EBR</div>'+
      '<div class="box">'+d.resumen.simples+' registro simple</div>';
    if(!d.ordenes.length){out.innerHTML='<div class="muted">Sin órdenes en esta fase.</div>';return;}
    var h='<table><thead><tr>'+
      '<th>N° de orden</th><th>N° lote</th><th>Producto</th>'+
      '<th class="num">Cant. teórica</th><th class="num">Cant. producida</th>'+
      '<th class="num">Cant. aprobada</th><th>Estado</th><th>Origen</th><th>Fecha</th><th></th>'+
      '</tr></thead><tbody>';
    d.ordenes.forEach(function(o){
      var aprob = o.aprobada!=null ? gfmt(o.aprobada) : (o.ml_envasable!=null? (Number(o.ml_envasable).toLocaleString('es-CO')+' mL') : '—');
      var acc = o.link ? '<a class="legajo" href="'+o.link+'">Abrir legajo →</a>' : '<span class="muted">—</span>';
      var org = o.origen==='legajo' ? '<span class="org org-l">LEGAJO</span>' : '<span class="org org-s">SIMPLE</span>';
      h+='<tr>'+
        '<td class="mono">'+esc(o.numero_op)+'</td>'+
        '<td class="mono">'+esc(o.lote_bulk||'—')+'</td>'+
        '<td>'+esc(o.producto||'—')+'</td>'+
        '<td class="num">'+gfmt(o.teorica_g)+'</td>'+
        '<td class="num">'+gfmt(o.producida_g)+'</td>'+
        '<td class="num">'+aprob+'</td>'+
        '<td>'+pill(o.estado)+'</td>'+
        '<td>'+org+'</td>'+
        '<td class="muted">'+esc(o.fecha||'—')+'</td>'+
        '<td>'+acc+'</td>'+
      '</tr>';
    });
    h+='</tbody></table>';
    out.innerHTML=h;
  }catch(e){out.innerHTML='<span style="color:#b91c1c">Error red: '+esc(e.message)+'</span>';}
}
ver('fabricacion',document.querySelector('.tab'));
</script>
</body></html>"""


@bp.route("/planta/ordenes-produccion", methods=["GET"])
def ordenes_produccion_page():
    """Página (solo lectura) · Órdenes de Producción unificadas estilo MyBatch."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/ordenes-produccion"</script>',
                        mimetype="text/html")
    return Response(_ORDENES_PROD_HTML, mimetype="text/html")
