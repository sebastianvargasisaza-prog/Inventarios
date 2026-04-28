"""
comunicacion.py — Sistema interno de tareas + chat + actas + quejas.

Solucion al problema crónico detectado en las actas del comité semanal:
compromisos verbales sin trazabilidad. Diseño:

- TAREAS con matriz RACI (Responsible/Accountable/Consulted/Informed)
- CHAT interno entre usuarios (asíncrono, opcional vinculado a tarea)
- PARSER de actas: recibe transcripción Gemini → extrae compromisos auto
- QUEJAS: usuario reporta problema → IA analiza severidad → escala a gerente

Acceso: cualquier usuario autenticado (todos en el holding necesitan ver
sus tareas y participar en chat). Admins ven todo.
"""
import json
import re
import urllib.request
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template_string

from config import DB_PATH, ADMIN_USERS, USER_EMAILS
from database import get_db

bp = Blueprint("comunicacion", __name__)


# ─── auth ──────────────────────────────────────────────────────────────────

def _auth():
    """Cualquier usuario logueado puede usar el modulo."""
    u = session.get("compras_user", "")
    if not u:
        return None, jsonify({"error": "No autenticado"}), 401
    return u, None, None


def _is_admin(u):
    return u in ADMIN_USERS


def _fmt_many(rows):
    return [dict(r) for r in rows] if rows else []


# ─── HOME ───────────────────────────────────────────────────────────────────

@bp.route("/comunicacion")
def comunicacion_home():
    u = session.get("compras_user", "")
    if not u:
        return jsonify({"error": "No autenticado"}), 401
    from templates_py.comunicacion_html import HTML
    return render_template_string(HTML, usuario=u)


# ─── TAREAS CON RACI ────────────────────────────────────────────────────────

@bp.route("/api/comunicacion/tareas", methods=["GET", "POST"])
def tareas_list():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    if request.method == "POST":
        d = request.json or {}
        titulo = (d.get("titulo") or "").strip()
        if not titulo:
            return jsonify({"error": "Titulo requerido"}), 400
        c.execute("""INSERT INTO tareas_internas
                     (titulo, descripcion, estado, prioridad, area, origen, origen_ref,
                      fecha_compromiso, creado_por, reincidente_de_id)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (titulo, d.get("descripcion", ""),
                   d.get("estado", "Asignada"),
                   d.get("prioridad", "Media"),
                   d.get("area", ""),
                   d.get("origen", "manual"),
                   d.get("origen_ref", ""),
                   d.get("fecha_compromiso") or None,
                   u,
                   d.get("reincidente_de_id") or None))
        tarea_id = c.lastrowid

        # RACI: lista de {usuario, rol}
        raci = d.get("raci") or []
        for r in raci:
            usr = (r.get("usuario") or "").strip().lower()
            rol = (r.get("rol") or "").upper()
            if not usr or rol not in ("R", "A", "C", "I"):
                continue
            try:
                c.execute("""INSERT OR IGNORE INTO tareas_raci
                             (tarea_id, usuario, rol, asignado_por)
                             VALUES (?,?,?,?)""",
                          (tarea_id, usr, rol, u))
            except Exception:
                pass

        conn.commit()
        return jsonify({"ok": True, "id": tarea_id}), 201

    # GET — filtros opcionales
    filtro_usuario = request.args.get("usuario", "").strip().lower()
    filtro_estado  = request.args.get("estado", "").strip()
    filtro_origen  = request.args.get("origen", "").strip()
    filtro_area    = request.args.get("area", "").strip()
    solo_mis       = request.args.get("mis") == "1"

    where, params = [], []
    if filtro_estado:
        where.append("t.estado = ?"); params.append(filtro_estado)
    if filtro_origen:
        where.append("t.origen = ?"); params.append(filtro_origen)
    if filtro_area:
        where.append("t.area = ?"); params.append(filtro_area)

    base = """
        SELECT t.id, t.titulo, t.descripcion, t.estado, t.prioridad, t.area,
               t.origen, t.origen_ref, t.fecha_compromiso, t.fecha_creacion,
               t.fecha_completada, t.creado_por, t.reincidente_de_id,
               (SELECT GROUP_CONCAT(usuario, ',') FROM tareas_raci WHERE tarea_id=t.id AND rol='R') as r,
               (SELECT GROUP_CONCAT(usuario, ',') FROM tareas_raci WHERE tarea_id=t.id AND rol='A') as a,
               (SELECT GROUP_CONCAT(usuario, ',') FROM tareas_raci WHERE tarea_id=t.id AND rol='C') as cc,
               (SELECT GROUP_CONCAT(usuario, ',') FROM tareas_raci WHERE tarea_id=t.id AND rol='I') as i
        FROM tareas_internas t
    """
    if solo_mis:
        base += " WHERE t.id IN (SELECT tarea_id FROM tareas_raci WHERE usuario = ?)"
        params.insert(0, u)
        if where:
            base += " AND " + " AND ".join(where)
    elif filtro_usuario:
        base += " WHERE t.id IN (SELECT tarea_id FROM tareas_raci WHERE usuario = ?)"
        params.insert(0, filtro_usuario)
        if where:
            base += " AND " + " AND ".join(where)
    elif where:
        base += " WHERE " + " AND ".join(where)

    base += """
        ORDER BY
          CASE t.estado WHEN 'Bloqueada' THEN 1 WHEN 'Asignada' THEN 2
                       WHEN 'EnProceso' THEN 3 WHEN 'Hecha' THEN 4 ELSE 5 END,
          CASE t.prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END,
          COALESCE(t.fecha_compromiso, '9999-12-31')
        LIMIT 500
    """
    rows = c.execute(base, params).fetchall()
    return jsonify(_fmt_many(rows))


@bp.route("/api/comunicacion/tareas/<int:tid>", methods=["GET", "PATCH", "DELETE"])
def tarea_detalle(tid):
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    if request.method == "DELETE":
        if not _is_admin(u):
            return jsonify({"error": "Solo admins pueden borrar"}), 403
        c.execute("DELETE FROM tareas_raci WHERE tarea_id=?", (tid,))
        c.execute("DELETE FROM tareas_internas WHERE id=?", (tid,))
        conn.commit()
        return jsonify({"ok": True})

    if request.method == "PATCH":
        d = request.json or {}
        allowed = ["titulo", "descripcion", "estado", "prioridad", "area",
                   "fecha_compromiso", "notas_avance"]
        sets = ", ".join(f + "=?" for f in allowed if f in d)
        vals = [d[f] for f in allowed if f in d] + [tid]
        if sets:
            c.execute(f"UPDATE tareas_internas SET {sets} WHERE id=?", vals)
        # Si estado pasa a Hecha, registrar fecha_completada
        if d.get("estado") == "Hecha":
            c.execute("UPDATE tareas_internas SET fecha_completada=datetime('now') "
                      "WHERE id=? AND fecha_completada IS NULL", (tid,))
        # RACI delta opcional
        raci = d.get("raci") or []
        if raci:
            for r in raci:
                usr = (r.get("usuario") or "").strip().lower()
                rol = (r.get("rol") or "").upper()
                accion = r.get("accion", "agregar")
                if not usr or rol not in ("R", "A", "C", "I"):
                    continue
                if accion == "remover":
                    c.execute("DELETE FROM tareas_raci WHERE tarea_id=? AND usuario=? AND rol=?",
                              (tid, usr, rol))
                else:
                    c.execute("""INSERT OR IGNORE INTO tareas_raci
                                 (tarea_id, usuario, rol, asignado_por)
                                 VALUES (?,?,?,?)""", (tid, usr, rol, u))
        conn.commit()
        return jsonify({"ok": True})

    # GET
    row = c.execute("""
        SELECT t.*,
               (SELECT GROUP_CONCAT(usuario||':'||rol, ',') FROM tareas_raci WHERE tarea_id=t.id) as raci_csv
        FROM tareas_internas t WHERE t.id=?
    """, (tid,)).fetchone()
    if not row:
        return jsonify({"error": "Tarea no encontrada"}), 404
    out = dict(row)
    raci_pairs = (out.pop("raci_csv") or "").split(",") if out.get("raci_csv") else []
    raci = []
    for p in raci_pairs:
        if ":" in p:
            usr, rol = p.split(":", 1)
            raci.append({"usuario": usr, "rol": rol})
    out["raci"] = raci
    return jsonify(out)


@bp.route("/api/comunicacion/tareas/<int:tid>/avance", methods=["POST"])
def tarea_avance(tid):
    """Registra una nota de avance sin cambiar estado."""
    u, err, code = _auth()
    if err: return err, code
    d = request.json or {}
    nota = (d.get("nota") or "").strip()
    if not nota:
        return jsonify({"error": "Nota requerida"}), 400
    conn = get_db(); c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    nueva = f"[{timestamp}] {u}: {nota}"
    c.execute("""UPDATE tareas_internas
                 SET notas_avance = COALESCE(notas_avance,'') || ? || char(10)
                 WHERE id=?""", (nueva, tid))
    conn.commit()
    return jsonify({"ok": True})


# ─── CHAT INTERNO ───────────────────────────────────────────────────────────

@bp.route("/api/comunicacion/mensajes", methods=["GET", "POST"])
def mensajes():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    if request.method == "POST":
        d = request.json or {}
        a_user = (d.get("a_usuario") or "").strip().lower()
        msg = (d.get("mensaje") or "").strip()
        if not a_user or not msg:
            return jsonify({"error": "Destinatario y mensaje requeridos"}), 400
        c.execute("""INSERT INTO mensajes_internos
                     (de_usuario, a_usuario, asunto, mensaje, relacionado_tarea_id)
                     VALUES (?,?,?,?,?)""",
                  (u, a_user, d.get("asunto", ""), msg,
                   d.get("relacionado_tarea_id") or None))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid})

    # GET — bandeja del usuario actual o conversacion con otro
    con_usuario = (request.args.get("con") or "").strip().lower()
    if con_usuario:
        rows = c.execute("""
            SELECT id, de_usuario, a_usuario, asunto, mensaje, fecha, leido_at,
                   relacionado_tarea_id
            FROM mensajes_internos
            WHERE (de_usuario=? AND a_usuario=?) OR (de_usuario=? AND a_usuario=?)
            ORDER BY fecha DESC LIMIT 100
        """, (u, con_usuario, con_usuario, u)).fetchall()
    else:
        rows = c.execute("""
            SELECT id, de_usuario, a_usuario, asunto, mensaje, fecha, leido_at,
                   relacionado_tarea_id
            FROM mensajes_internos
            WHERE a_usuario=? OR de_usuario=?
            ORDER BY fecha DESC LIMIT 200
        """, (u, u)).fetchall()
    return jsonify(_fmt_many(rows))


@bp.route("/api/comunicacion/mensajes/<int:mid>/leido", methods=["POST"])
def mensaje_leer(mid):
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE mensajes_internos SET leido_at=datetime('now')
                 WHERE id=? AND a_usuario=? AND leido_at IS NULL""", (mid, u))
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/comunicacion/mensajes/no-leidos")
def mensajes_no_leidos():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    n = c.execute("SELECT COUNT(*) FROM mensajes_internos WHERE a_usuario=? AND leido_at IS NULL",
                  (u,)).fetchone()[0]
    return jsonify({"count": n})


# ─── ACTAS DE COMITE + PARSER ───────────────────────────────────────────────

# Patron heuristico para extraer compromisos de transcripciones Gemini.
# Busca seccion "Conclusiones / Compromisos / Tareas" y extrae bullets con
# "responsable: X, plazo: Y" o similar.
_COMPROMISO_REGEX = re.compile(
    r"(?:^|\n)\s*[-•*]\s*(.+?)(?:\n|$)",
    re.MULTILINE
)
_RESPONSABLE_REGEX = re.compile(
    r"(?:resp(?:onsable)?|asign(?:ado a)?|por)\s*:?\s*([\w\s]+?)(?:[,\.\n]|$)",
    re.IGNORECASE
)
_PLAZO_REGEX = re.compile(
    r"(?:plazo|fecha|deadline|para)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[\/-]\d{1,2}(?:[\/-]\d{2,4})?)",
    re.IGNORECASE
)
_USERS_KNOWN = {"sebastian", "alejandro", "luz", "daniela", "jefferson", "felipe",
                "catalina", "mayra", "hernando", "miguel", "evelin", "gisseth",
                "laura", "valentina", "gerencia", "calidad", "tecnica", "marketing"}


def _parsear_seccion_compromisos(texto):
    """Extrae bullets de la seccion 'Compromisos' / 'Conclusiones' del acta."""
    # Buscar inicio de seccion compromisos
    secciones = re.split(
        r"(?i)\n\s*(?:#+\s*)?(?:conclusiones?\s*y?/?o?\s*compromisos?|compromisos?|tareas?\s*asignadas?|acuerdos?)\s*[:\n]",
        texto, maxsplit=1
    )
    if len(secciones) < 2:
        # No hay seccion explicita — devolver todo el texto
        bloque = texto
    else:
        bloque = secciones[1]
    # Cortar en la siguiente seccion (otro h2/h3 o "observaciones")
    bloque = re.split(r"(?i)\n\s*(?:#+\s*)?(?:observaciones|proxima|siguiente)\s*[:\n]",
                      bloque, maxsplit=1)[0]

    items = []
    for m in _COMPROMISO_REGEX.finditer(bloque):
        linea = m.group(1).strip()
        if len(linea) < 8:
            continue
        # Extraer responsable
        resp_m = _RESPONSABLE_REGEX.search(linea)
        responsable = ""
        if resp_m:
            cand = resp_m.group(1).strip().lower()
            for nombre in _USERS_KNOWN:
                if nombre in cand:
                    responsable = nombre
                    break
            if not responsable:
                responsable = cand.split()[0]  # primer token
        else:
            # Buscar nombre conocido en cualquier parte
            for nombre in _USERS_KNOWN:
                if re.search(r"\b" + nombre + r"\b", linea, re.IGNORECASE):
                    responsable = nombre
                    break
        # Extraer plazo
        plazo_m = _PLAZO_REGEX.search(linea)
        plazo = plazo_m.group(1) if plazo_m else ""

        items.append({
            "titulo": linea[:200],
            "responsable": responsable,
            "fecha_compromiso": plazo,
        })
    return items


@bp.route("/api/comunicacion/actas", methods=["GET", "POST"])
def actas_list():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    if request.method == "POST":
        d = request.json or {}
        c.execute("""INSERT INTO comites_actas
                     (fecha, plataforma, titulo, asistentes_json, transcripcion,
                      transcripcion_url, registrado_por)
                     VALUES (?,?,?,?,?,?,?)""",
                  (d.get("fecha", datetime.now().strftime("%Y-%m-%d")),
                   d.get("plataforma", "Google Meet"),
                   d.get("titulo", "Comite Semanal Espagiria"),
                   json.dumps(d.get("asistentes", [])),
                   d.get("transcripcion", ""),
                   d.get("transcripcion_url", ""),
                   u))
        conn.commit()
        return jsonify({"ok": True, "id": c.lastrowid}), 201

    rows = c.execute("""
        SELECT id, fecha, plataforma, titulo, asistentes_json,
               LENGTH(transcripcion) as len_transcripcion,
               parseada, tareas_creadas, registrado_por, fecha_creacion
        FROM comites_actas
        ORDER BY fecha DESC LIMIT 100
    """).fetchall()
    out = _fmt_many(rows)
    for r in out:
        try:
            r["asistentes"] = json.loads(r.pop("asistentes_json", "[]"))
        except Exception:
            r["asistentes"] = []
    return jsonify(out)


@bp.route("/api/comunicacion/actas/<int:aid>/parsear", methods=["POST"])
def acta_parsear(aid):
    """Parsea la transcripcion del acta y crea tareas tentativas con RACI."""
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    row = c.execute("SELECT transcripcion, fecha FROM comites_actas WHERE id=?",
                    (aid,)).fetchone()
    if not row:
        return jsonify({"error": "Acta no encontrada"}), 404
    texto = row["transcripcion"] or ""
    if len(texto) < 50:
        return jsonify({"error": "Transcripcion vacia o muy corta"}), 400

    items = _parsear_seccion_compromisos(texto)
    creadas = []
    for item in items:
        c.execute("""INSERT INTO tareas_internas
                     (titulo, estado, prioridad, origen, origen_ref,
                      fecha_compromiso, creado_por)
                     VALUES (?,?,?,?,?,?,?)""",
                  (item["titulo"], "Asignada", "Media", "comite", str(aid),
                   item.get("fecha_compromiso") or None, u))
        tarea_id = c.lastrowid
        if item.get("responsable"):
            c.execute("""INSERT OR IGNORE INTO tareas_raci
                         (tarea_id, usuario, rol, asignado_por) VALUES (?,?,?,?)""",
                      (tarea_id, item["responsable"], "R", u))
        creadas.append(tarea_id)

    c.execute("UPDATE comites_actas SET parseada=1, tareas_creadas=? WHERE id=?",
              (len(creadas), aid))
    conn.commit()
    return jsonify({"ok": True, "tareas_creadas": len(creadas), "ids": creadas})


# ─── QUEJAS / PROBLEMAS REPORTADOS (con análisis IA opcional) ───────────────

def _analizar_queja_ia(contexto):
    """Llama Claude API para analizar una queja interna.
    Devuelve dict con severidad/analisis/accion_sugerida o None si falla."""
    conn = get_db()
    try:
        api_key = conn.execute(
            "SELECT valor FROM animus_config WHERE clave='anthropic_api_key'"
        ).fetchone()
        if not api_key:
            return None
        api_key = api_key[0]
    except Exception:
        return None

    prompt = (
        "Eres asesor de gerencia de HHA Group (laboratorio cosmetico colombiano "
        "con marca ANIMUS Lab). Un empleado reporto el siguiente problema o queja "
        "interna. Tu tarea: analizar severidad, identificar causa raiz probable, "
        "y sugerir accion concreta para gerencia. Responde EN ESPANOL en JSON "
        "estricto con estas claves: "
        '{"severidad": "Baja|Media|Alta|Critica", '
        '"analisis": "1-3 lineas con tu lectura del problema", '
        '"accion_sugerida": "1-2 lineas con accion concreta", '
        '"escalar_a": "sebastian|alejandro|gerencia|jefe_area|ninguno"}\n\n'
        "Queja del empleado:\n" + (contexto or "")[:2000]
    )
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["content"][0]["text"]
            # Extraer JSON del texto (puede venir con prefijo/sufijo)
            m = re.search(r"\{[\s\S]+\}", text)
            if m:
                return json.loads(m.group(0))
    except Exception:
        return None
    return None


@bp.route("/api/comunicacion/quejas", methods=["GET", "POST"])
def quejas_list():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()

    if request.method == "POST":
        d = request.json or {}
        contexto = (d.get("contexto") or "").strip()
        if not contexto:
            return jsonify({"error": "Contexto requerido"}), 400

        # Insert primero (sin analisis)
        c.execute("""INSERT INTO quejas_internas (de_usuario, contexto, estado)
                     VALUES (?,?,?)""", (u, contexto, "Pendiente"))
        qid = c.lastrowid
        conn.commit()

        # Intentar analisis IA en background (best-effort)
        analisis = _analizar_queja_ia(contexto)
        if analisis:
            try:
                c.execute("""UPDATE quejas_internas
                             SET severidad_ia=?, analisis_ia=?,
                                 accion_sugerida_ia=?, escalada_a=?,
                                 estado='Analizada'
                             WHERE id=?""",
                          (analisis.get("severidad", "Media"),
                           analisis.get("analisis", "")[:500],
                           analisis.get("accion_sugerida", "")[:500],
                           analisis.get("escalar_a", ""),
                           qid))
                # Si severidad Alta/Critica, escalar a admin via mensaje
                sev = analisis.get("severidad", "Media")
                if sev in ("Alta", "Critica"):
                    destinos = ADMIN_USERS
                    for admin in destinos:
                        c.execute("""INSERT INTO mensajes_internos
                                     (de_usuario, a_usuario, asunto, mensaje)
                                     VALUES (?,?,?,?)""",
                                  ("sistema_ia", admin,
                                   f"Queja {sev}: revision urgente",
                                   f"Empleado {u} reporto problema severidad {sev}.\n\n"
                                   f"Analisis: {analisis.get('analisis','')}\n\n"
                                   f"Accion sugerida: {analisis.get('accion_sugerida','')}\n\n"
                                   f"Queja original: {contexto[:500]}"))
                conn.commit()
            except Exception:
                pass

        return jsonify({"ok": True, "id": qid, "analisis": analisis}), 201

    # GET — admins ven todas, usuarios ven las suyas
    if _is_admin(u):
        rows = c.execute("""SELECT * FROM quejas_internas
                            ORDER BY
                              CASE severidad_ia
                                WHEN 'Critica' THEN 1 WHEN 'Alta' THEN 2
                                WHEN 'Media' THEN 3 ELSE 4 END,
                              fecha DESC
                            LIMIT 100""").fetchall()
    else:
        rows = c.execute("""SELECT * FROM quejas_internas
                            WHERE de_usuario=? ORDER BY fecha DESC""", (u,)).fetchall()
    return jsonify(_fmt_many(rows))


@bp.route("/api/comunicacion/quejas/<int:qid>/resolver", methods=["POST"])
def queja_resolver(qid):
    u, err, code = _auth()
    if err: return err, code
    if not _is_admin(u):
        return jsonify({"error": "Solo admins"}), 403
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE quejas_internas
                 SET estado=?, resolucion=?, fecha_resolucion=datetime('now')
                 WHERE id=?""",
              (d.get("estado", "Resuelta"),
               d.get("resolucion", "")[:1000], qid))
    conn.commit()
    return jsonify({"ok": True})


# ─── DASHBOARD CONSOLIDADO ──────────────────────────────────────────────────

@bp.route("/api/comunicacion/dashboard")
def dashboard():
    u, err, code = _auth()
    if err: return err, code
    conn = get_db(); c = conn.cursor()
    out = {}

    # Mis tareas activas
    out["mis_tareas"] = c.execute("""
        SELECT COUNT(*) FROM tareas_internas t
        JOIN tareas_raci r ON r.tarea_id = t.id
        WHERE r.usuario=? AND r.rol IN ('R','A')
          AND t.estado NOT IN ('Hecha','Cancelada')
    """, (u,)).fetchone()[0]

    # Vencidas
    out["mis_vencidas"] = c.execute("""
        SELECT COUNT(*) FROM tareas_internas t
        JOIN tareas_raci r ON r.tarea_id = t.id
        WHERE r.usuario=? AND r.rol IN ('R','A')
          AND t.estado NOT IN ('Hecha','Cancelada')
          AND t.fecha_compromiso IS NOT NULL
          AND t.fecha_compromiso < date('now')
    """, (u,)).fetchone()[0]

    # No leidos
    out["mensajes_no_leidos"] = c.execute(
        "SELECT COUNT(*) FROM mensajes_internos WHERE a_usuario=? AND leido_at IS NULL",
        (u,)).fetchone()[0]

    # Quejas pendientes (admin)
    if _is_admin(u):
        out["quejas_alta"] = c.execute(
            "SELECT COUNT(*) FROM quejas_internas WHERE estado IN ('Pendiente','Analizada','Escalada') "
            "AND severidad_ia IN ('Alta','Critica')"
        ).fetchone()[0]
    else:
        out["quejas_alta"] = 0

    # Total tareas activas en la organizacion (admin only)
    if _is_admin(u):
        out["total_activas"] = c.execute(
            "SELECT COUNT(*) FROM tareas_internas WHERE estado NOT IN ('Hecha','Cancelada')"
        ).fetchone()[0]
    else:
        out["total_activas"] = None

    return jsonify(out)
