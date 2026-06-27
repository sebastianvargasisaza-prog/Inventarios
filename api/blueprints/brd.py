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
    from templates_py.ui_help import TOOLTIP_CSS
except Exception:  # deploy-safe
    try:
        from api.templates_py.ui_help import TOOLTIP_CSS
    except Exception:
        TOOLTIP_CSS = ""
try:
    from config import EBR_MODE
except ImportError:  # deploy-safe
    EBR_MODE = "off"


def _ebr_mode_now(c=None):
    """Modo EBR EFECTIVO por request: app_settings 'ebr_mode' (toggle UI) → env EBR_MODE → 'off'.
    Usar esto en los gates (no la constante de import) para que el interruptor de la UI tenga efecto
    inmediato sin redeploy. Sebastián 24-jun: activar warn → pulir con uso → strict."""
    try:
        from database import ebr_mode
    except ImportError:
        from api.database import ebr_mode
    return ebr_mode(c)


from audit_helpers import audit_log

bp = Blueprint("brd", __name__)
log = logging.getLogger("brd")


def _brd_visible(conn=None):
    """¿El Batch Record (EBR/MBR/legajos) está VISIBLE para el usuario ACTUAL?

    Gobernado por app_settings.brd_visible:
      - '1'/'true'/'on'   → visible para TODOS
      - '0'/''/ausente    → OCULTO para todos (default · seguro)
      - 'admin'           → visible solo para ADMIN_USERS
      - '<usuario>' (o lista coma-separada) → visible solo para ese/esos usuario(s)
    Sebastián 18-jun: oculto hasta validación Part 11. 22-jun: modo por-usuario para que
    Sebastián trabaje el batch digital sin que el resto lo vea. Reversible · sin redeploy."""
    try:
        c = conn or get_db()
        r = c.execute("SELECT valor FROM app_settings WHERE clave='brd_visible' LIMIT 1").fetchone()
        val = (str(r[0]).strip().lower() if (r and r[0] is not None) else '')
    except Exception:
        return False  # ante la duda, OCULTO (seguro · no exponer regulado sin validar)
    if val in ('1', 'true', 'yes', 'si', 'sí', 'on'):
        return True
    if val in ('', '0', 'false', 'no', 'off'):
        return False
    # modo restringido por usuario(s): 'admin' o username(s) coma-separados
    try:
        u = (session.get('compras_user') or '').strip().lower()
    except Exception:
        return False
    if not u:
        return False
    if val == 'admin':
        return u in {x.lower() for x in ADMIN_USERS}
    return u in {x.strip() for x in val.split(',') if x.strip()}


_BRD_OCULTO_HTML = (
    "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Módulo en validación</title>"
    "<style>body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;"
    "align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px}"
    ".c{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:40px;max-width:520px;text-align:center}"
    "h2{color:#a78bfa;margin:0 0 12px}p{color:#94a3b8;line-height:1.5;margin:0 0 18px}"
    "a{display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:10px 24px;border-radius:8px;font-weight:700}</style>"
    "</head><body><div class='c'><div style='font-size:46px;margin-bottom:8px'>&#128272;</div>"
    "<h2>Batch Record · en validación</h2>"
    "<p>El registro digital de lote (EBR/MBR · GMP) está <b>oculto temporalmente</b> hasta completar "
    "la validación por un tercero (21 CFR Part 11). El resto de Planta funciona normal.</p>"
    "<a href='/planta'>&larr; Volver a Planta</a></div></body></html>"
)


@bp.before_request
def _gate_brd_pages():
    """Oculta las PÁGINAS del batch record (no las APIs · /api/brd/* siguen vivas para que
    el historial de producción del dashboard no se rompa) hasta que Part 11 esté lista."""
    try:
        p = request.path or ''
    except Exception:
        return None
    if p.startswith('/api/'):
        return None
    if _brd_visible():
        return None
    return Response(_BRD_OCULTO_HTML, mimetype='text/html; charset=utf-8')

# Despeje de Línea · Dispensación (MyBatch estación ②) · checklist GMP canónico.
# Sebastián 5-jun-2026: estas 13 verificaciones son el SOP de despeje de línea
# (no son datos inventados, son los controles regulatorios estándar). El CUMPLE
# por ítem se guarda en ebr_despeje_items con e-firma del responsable.
DESPEJE_LINEA_ITEMS = [
    "Temperatura menor a 30 grados",
    "¿Cuenta con los EPP requeridos para el proceso?",
    "¿Los equipos requeridos se encuentran aptos para su uso? (mantenimiento y calibración al día)",
    "¿El formato de registro de condiciones ambientales se encuentra diligenciado y al día?",
    "¿Las condiciones ambientales son las idóneas para el proceso?",
    "Las materias primas, material de envase y empaque, graneles, etiquetas y documentación corresponden al producto a trabajar.",
    "El área se encuentra identificada con el producto en proceso",
    "El área y sus equipos y/o utensilios se encuentran completamente limpios y con los respectivos rótulos de Limpieza Área / Equipo.",
    "¿Se comprueba que todas las áreas están rotuladas como \"Área limpia\" y están listas para ser usadas?",
    "¿Se comprueba que todos los equipos están rotulados como \"Equipo limpio\" y están listos para ser usados?",
    "¿Los formatos de Limpieza de áreas se encuentran diligenciados y al día?",
    "¿Se asegura que las áreas de producción estén limpias y desinfectadas antes de cada lote?",
    "El área está libre de materias primas, material de envase y empaque, gráneles, etiquetas, producto terminado y documentación del producto anterior.",
]

# Controles en Proceso ESTÁNDAR · Sebastián 6-jun-2026. Se muestran SIEMPRE en
# la sección 6 (aunque el MBR del producto no defina IPCs), y cada uno se puede
# registrar con valor o marcar "No aplica". (codigo, nombre, unidad).
IPC_ESTANDAR = [
    ("densidad",   "Densidad a 25°C", "g/mL"),
    ("ph",         "pH a 25°C",       ""),
    ("olor",       "Olor",            ""),
    ("color",      "Color",           ""),
    ("apariencia", "Apariencia",      ""),
]


def _batch_role_info(usuario):
    """Rol del usuario en el batch record (segregación de funciones GMP · 25-jun).
    UI-hint: el backend YA bloquea con 403; esto adapta la vista — quién REALIZA
    (operario/jefe prod) vs quién VERIFICA (calidad/jefe prod/dir. téc.). Reusa los
    sets de config.py. Roles finos: operario · jefe_produccion · calidad ·
    aseguramiento · director_tecnico · admin · consulta."""
    u = (usuario or "").strip().lower()
    try:
        from config import ASEGURAMIENTO_USERS, TECNICA_USERS
    except Exception:
        ASEGURAMIENTO_USERS, TECNICA_USERS = set(), set()
    A, C, P = set(ADMIN_USERS), set(CALIDAD_USERS), set(PLANTA_USERS)
    AS_, T = set(ASEGURAMIENTO_USERS), set(TECNICA_USERS)
    if u in A:
        tipo, rol = "admin", "Dirección / Admin"
    elif u in (C - A):
        tipo, rol = "calidad", "Control de Calidad"
    elif u in (AS_ - A):
        tipo, rol = "aseguramiento", "Aseguramiento"
    elif u in (T - A - AS_):
        tipo, rol = "director_tecnico", "Director Técnico"
    elif u in {"jose"}:
        tipo, rol = "jefe_produccion", "Jefe de Producción"
    elif u in (P | {"milton"}):
        tipo, rol = "operario", "Operario"
    elif u in {"luz", "catalina"}:
        tipo, rol = "administrativo", "Administrativo"
    else:
        tipo, rol = "consulta", "Consulta"
    realiza = tipo in ("operario", "jefe_produccion", "admin")
    verifica = tipo in ("calidad", "jefe_produccion", "director_tecnico", "admin")
    return {
        "usuario": u, "tipo": tipo, "rol": rol,
        "realiza": realiza,
        "verifica": verifica,
        "corrige": tipo in ("calidad", "aseguramiento", "director_tecnico", "admin"),
        "aprueba_dt": tipo in ("director_tecnico", "admin"),
        "puede_ejecutar": tipo in ("operario", "jefe_produccion", "calidad", "admin"),
        "puede_verificar": verifica,
        "puede_liberar": tipo in ("calidad", "aseguramiento", "director_tecnico", "admin"),
        "puede_aprobar": tipo in ("calidad", "director_tecnico", "admin"),
    }


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
    audit_log(None, usuario=user, accion="CREATE_MBR_DRAFT",
              tabla="mbr_templates", registro_id=mbr_id,
              despues={"producto": producto, "version": version})
    return jsonify({"ok": True, "id": mbr_id, "version": version}), 201


_INSTRUCTIVO_SUERO_MULTIP = """En un recipiente con capacidad adecuada, adicionar con agitación constante y a temperatura ambiente: Agua (60% de la fórmula), Niacinamida, Gluconolactona y Glucosamina.
Adicionar uno por uno hasta total disolución (no adicionar la siguiente MP si la anterior no se disolvió). En esta primera parte ajustar el pH = 6.0 con Trietanolamina. pH final: ___ · Cantidad de TEA: ___ ml.
Una vez ajustado el pH, adicionar lentamente y con agitación constante: Glicina, Copper tripeptide-1, Glutatión, Adenosina, PDRN, Dipeptide Diaminobutiroil benzalamida diacetato.
Adicionar uno por uno hasta total disolución. En esta segunda parte ajustar el pH = 6.0 con Trietanolamina. pH final: ___ · Cantidad de TEA: ___ ml.
Seguir agitando manteniendo el pH.
Finalmente, adicionar con agitación constante y temperatura ambiente: Acetyl tetrapeptide-5, Acetyl hexapeptido-8, Palmitoyl Tripeptide-5, Colágeno hidrolizado, EDTA disódico. Verificar pH=6.0 y ajustar con TEA si es necesario.
En otro recipiente, calentar el Propilenglicol a ~60°C. Al llegar a esa temperatura adicionar: Palmitoyl tripeptide-1, Palmitoyl tetrapeptide-7, Palmitoyl Pentapeptide-4.
Enfriar de forma rápida; luego agregar esta solución a los Ácidos hialurónicos 50KDa, 300KDa y 1500KDa hasta total dispersión.
Agregar esta dispersión con agitación constante al resto del agua de la fórmula (40%) y seguir agitando 20 minutos más, hasta total hidratación.
Usar la batidora de mano para total homogenización y disolución de los péptidos.
Una vez hidratados los AH y a temperatura menor de 40°C, adicionar la mezcla anterior suavemente y con agitación constante a la fase acuosa inicial.
Adicionar a la mezcla anterior, con agitación constante: Gransil VX 419 y Biosure FE.
Verificar pH=6.0 y ajustar con TEA si es necesario. pH final: ___ · TEA: ___ ml. Seguir agitando 20 minutos más. Tiempo real: ___ min."""


@bp.route("/admin/cargar-instructivo", methods=["GET"])
def cargar_instructivo_page():
    """Página simple para cargar el instructivo de fabricación (pasos de proceso) en el MBR de un producto."""
    err = _require_qa_or_admin()
    if err:
        return err
    try:
        prods = [r[0] for r in get_db().execute(
            "SELECT DISTINCT producto_nombre FROM mbr_templates ORDER BY producto_nombre").fetchall()]
    except Exception:
        prods = []
    import html as _html
    opts = "".join(
        f'<option value="{_html.escape(p)}"{" selected" if "MULTIP" in (p or "").upper() else ""}>{_html.escape(p)}</option>'
        for p in prods)
    pre = _html.escape(_INSTRUCTIVO_SUERO_MULTIP)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cargar instructivo de fabricación</title>
<style>body{{font-family:system-ui,Segoe UI,Arial;background:#0f0f14;color:#e7e7ea;margin:0;padding:24px 14px}}
.wrap{{max-width:780px;margin:0 auto}}h1{{font-size:19px;color:#a78bfa}}label{{display:block;font-size:13px;color:#a1a1aa;margin:14px 0 5px;font-weight:700}}
select,textarea{{width:100%;box-sizing:border-box;background:#1a1a22;color:#e7e7ea;border:1px solid #34343f;border-radius:9px;padding:11px;font-size:14px}}
textarea{{min-height:300px;line-height:1.5;font-family:inherit}}button{{margin-top:16px;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border:none;border-radius:9px;padding:13px 22px;font-size:15px;font-weight:800;cursor:pointer}}
.hint{{font-size:12px;color:#71717a;margin-top:6px}}#res{{margin-top:16px;font-size:14px;font-weight:700;min-height:22px}}</style></head>
<body><div class="wrap">
<h1>📋 Cargar instructivo de fabricación al MBR</h1>
<p class="hint">Cada línea = un paso del proceso de mezcla. El dispensado de MP sale solo de la fórmula (sección 3). Si el MBR está aprobado, se crea una versión NUEVA en borrador (la apruebás después con e-firma).</p>
<label>Producto (MBR destino)</label><select id="prod">{opts}</select>
<label>Pasos del proceso (uno por línea)</label><textarea id="pasos">{pre}</textarea>
<div class="hint">Pre-cargado: instructivo del Suero Multipéptidos (de tu PDF). Editá o cambiá de producto.</div>
<button onclick="cargar()">✓ Cargar instructivo</button>
<div id="res"></div>
</div>
<script>
async function cargar(){{
  var prod=document.getElementById('prod').value;
  var pasos=document.getElementById('pasos').value;
  var res=document.getElementById('res');
  res.style.color='#a1a1aa'; res.textContent='Cargando…';
  try{{
    var r=await fetch('/api/brd/mbr/cargar-instructivo',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{producto:prod,pasos:pasos}})}});
    var d=await r.json();
    if(!r.ok){{ res.style.color='#f87171'; res.textContent='Error: '+(d.error||r.status); return; }}
    res.style.color='#34d399'; res.textContent='✓ '+d.pasos+' pasos cargados en '+d.producto+' · '+(d.aviso||'');
  }}catch(e){{ res.style.color='#f87171'; res.textContent='Error de red'; }}
}}
</script></body></html>"""


@bp.route("/api/brd/mbr/cargar-instructivo", methods=["POST"])
def cargar_instructivo_mbr():
    """Carga el INSTRUCTIVO de fabricación REAL (los pasos de proceso de mezcla) en el MBR de un
    producto · Sebastián 25-jun. body: {producto, pasos: [texto...] o texto multilínea}.
    Respeta inmutabilidad GMP: si el MBR activo está APROBADO, crea una versión NUEVA en borrador con
    estos pasos (Calidad la aprueba con e-firma para que entre en vigor); si está en BORRADOR, reemplaza
    sus pasos. El dispensado de MP sigue saliendo de la fórmula (sección 3), no de estos pasos."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto_in = (body.get("producto") or "").strip()
    pasos = body.get("pasos") or []
    if isinstance(pasos, str):
        pasos = pasos.split("\n")
    pasos = [str(p).strip() for p in pasos if str(p or "").strip()][:80]
    if not producto_in or not pasos:
        return jsonify({"error": "producto y pasos requeridos"}), 400
    conn = get_db()
    cur = conn.cursor()
    user = session.get("compras_user", "")
    mbr = cur.execute(
        "SELECT id, estado, COALESCE(lote_size_g,0), producto_nombre FROM mbr_templates "
        "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) ORDER BY version DESC LIMIT 1",
        (producto_in,)).fetchone()
    if not mbr:
        return jsonify({"error": f"No hay MBR para '{producto_in}'. Generá el MBR del producto primero."}), 404
    producto = mbr[3]  # nombre canónico
    if (mbr[1] or "") == "draft":
        target_id = mbr[0]
        nueva_version = False
        cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (target_id,))
    else:
        version = _next_version(conn, producto)
        cur.execute(
            "INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, lote_size_g, creado_por) "
            "VALUES (?, ?, 'draft', ?, ?, ?)",
            (producto, version, f"{producto} v{version} · instructivo de fabricación", mbr[2], user))
        target_id = cur.lastrowid
        nueva_version = True
    for i, txt in enumerate(pasos, start=1):
        cur.execute(
            "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, requiere_qc) "
            "VALUES (?, ?, 'fabricacion', ?, 'mezclado', 1)",
            (target_id, i, txt[:1500]))
    audit_log(cur, usuario=user, accion="CARGAR_INSTRUCTIVO_MBR", tabla="mbr_templates",
              registro_id=target_id,
              despues={"producto": producto, "pasos": len(pasos), "nueva_version": nueva_version})
    conn.commit()
    return jsonify({"ok": True, "mbr_id": target_id, "producto": producto, "pasos": len(pasos),
                    "nueva_version": nueva_version,
                    "aviso": ("Versión NUEVA en borrador creada · aprobala con e-firma en el módulo MBR "
                              "para que entre en vigor (la anterior sigue activa hasta entonces)"
                              if nueva_version else "Pasos del MBR en borrador reemplazados")}), 200


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
    audit_log(None, usuario=session.get("compras_user", ""),
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
    audit_log(None, usuario=user, accion="SUBMIT_MBR",
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
    audit_log(None, usuario=user, accion="APROBAR_MBR",
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
    audit_log(None, usuario=user, accion="OBSOLETAR_MBR",
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
                        fase='fabricacion', area_codigo=''):
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
    # `ebr_ejecuciones.lote` es UNIQUE a nivel BD. Para que el MISMO lote físico tenga
    # legajo de fabricación/envasado/acondicionamiento (órdenes OP/OF/OA distintas, como
    # MyBatch · 10-jun), la LLAVE `lote` lleva sufijo de fase (·OF/·OA) y el lote físico
    # real se guarda en `lote_codigo`. La idempotencia/dedup van por (lote_codigo, FASE).
    _fase_norm = fase if fase in _FASES_VALIDAS else 'fabricacion'
    lote_codigo = (lote or '').strip()
    _suf = {'fabricacion': '', 'envasado': '-OF', 'acondicionamiento': '-OA'}.get(_fase_norm, '')
    lote_key = lote_codigo + _suf
    # Idempotencia por (produccion_id, lote_codigo, FASE): re-aceptar la misma fase reusa
    # el legajo de ESE lote físico. Batch C · multi-lote: lotes físicos distintos = N legajos.
    if produccion_id is not None:
        ex = cur.execute(
            "SELECT id, numero_op FROM ebr_ejecuciones "
            "WHERE produccion_id=? AND COALESCE(lote_codigo,lote)=? AND COALESCE(fase,'fabricacion')=?",
            (produccion_id, lote_codigo, _fase_norm),
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
    # Un solo EBR por (lote físico, FASE): Fabricación/Envasado/Acondicionamiento del
    # mismo lote conviven. Dentro de UNA fase, el lote sigue siendo único.
    if cur.execute(
        "SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote)=? AND COALESCE(fase,'fabricacion')=?",
        (lote_codigo, _fase_norm)).fetchone():
        return {'ok': False, 'error': 'LOTE_DUPLICADO',
                'detail': f"el lote '{lote_codigo}' ya tiene un EBR de fase {_fase_norm}"}
    # Resolver colisión del UNIQUE `lote` (por si la llave sufijada ya existe por otra vía).
    _base_key = lote_key; _n = 1
    while cur.execute("SELECT 1 FROM ebr_ejecuciones WHERE lote=?", (lote_key,)).fetchone():
        _n += 1
        lote_key = f"{_base_key}-{_n}"
    cant = cantidad_objetivo_g if cantidad_objetivo_g is not None else mbr[2]
    numero_op = assign_numero_op(cur)
    try:
        cur.execute(
            """INSERT INTO ebr_ejecuciones
                 (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
                  estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
                  fase, area_codigo)
               VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?, ?)""",
            (mbr[0], mbr[1], produccion_id, lote_key, numero_op, usuario,
             float(cant or 0), notas, _fase_norm, (area_codigo or '')),
        )
    except Exception:
        # Fallback si la columna area_codigo aún no existe (mig 219 sin aplicar)
        cur.execute(
            """INSERT INTO ebr_ejecuciones
                 (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
                  estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
                  fase)
               VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?)""",
            (mbr[0], mbr[1], produccion_id, lote_key, numero_op, usuario,
             float(cant or 0), notas, _fase_norm),
        )
    ebr_id = cur.lastrowid
    # lote_codigo = lote físico real (la llave `lote` puede llevar sufijo de fase).
    try:
        cur.execute("UPDATE ebr_ejecuciones SET lote_codigo=? WHERE id=?",
                    (lote_codigo, ebr_id))
    except Exception:
        pass
    _fase_ebr = _fase_norm
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
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1
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
             FROM formula_items WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
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
        ('Envasado', 'Luego que control de calidad apruebe el granel, se debe realizar el despeje de línea indicado.', 'envasado'),
        ('Envasado', 'Realizar el alistamiento de los envases y de la máquina de envasado que se requiere para este llenado.', 'envasado'),
        ('Envasado', 'Ajustar la máquina a la cantidad requerida.', 'envasado'),
        ('Envasado', 'Realizar controles periódicos al proceso de llenado con el fin de verificar que se mantiene en el rango de llenado.', 'envasado'),
        ('Envasado', 'Al finalizar despejar el área, dejar todo limpio y realizar la entrega al área de acondicionamiento.', 'envasado'),
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


@bp.route("/api/brd/mbr/preparar-aprobado", methods=["POST"])
def mbr_preparar_aprobado():
    """Genera (si falta) Y APRUEBA el MBR de un producto en UN paso · para probar el
    legajo de envasado sin el flujo manual submit→firmar→aprobar. Firma con la identidad
    del usuario actual (e_signature REAL · 21 CFR Part 11 · auditable). Solo Admin/Calidad.
    Body: {producto_nombre}. Sebastián 9-jun-2026."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"ok": False, "error": "solo Admin/Calidad puede aprobar MBR"}), 403
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"ok": False, "error": "producto_nombre requerido"}), 400
    _regenerar = body.get("regenerar") in (True, 1, "1", "true", "True", "si")
    conn = get_db(); cur = conn.cursor()
    if _regenerar:
        # Obsoletar el MBR vigente para generar uno fresco (nueva versión) con los pasos
        # actualizados · forma GMP correcta (obsoletar + version+1 · el trigger lo permite).
        # audit_log por cada MBR obsoletado (mutación regulada · ANTES del commit final).
        try:
            _viejos = cur.execute(
                "SELECT id FROM mbr_templates WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) "
                "AND COALESCE(estado,'') != 'obsoleto'", (producto,)).fetchall()
            cur.execute(
                "UPDATE mbr_templates SET estado='obsoleto', "
                "obsoleto_at_utc=datetime('now','utc'), "
                "obsoleto_motivo='Regeneración: pasos de envasado actualizados' "
                "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) "
                "AND COALESCE(estado,'') != 'obsoleto'",
                (producto,))
            for _row in _viejos:
                _vid = (_row[0] if not hasattr(_row, 'keys') else _row['id'])
                audit_log(cur, usuario=user, accion="OBSOLETAR_MBR_REGENERAR",
                          tabla="mbr_templates", registro_id=_vid,
                          antes={"estado": "vigente"},
                          despues={"estado": "obsoleto",
                                   "motivo": "Regeneración: pasos de envasado actualizados"})
        except Exception as _eo:
            __import__('logging').getLogger('brd').warning('regenerar: obsoletar fallo: %s', _eo)
    res = _generar_mbr_desde_formula(cur, producto, usuario=user)
    if not res.get("ok"):
        return jsonify({"ok": False, "error": res.get("error") or "no se pudo generar el MBR"}), 404
    mbr_id = res["id"]
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
    estado = (row[0] if row else None)
    if estado == "aprobado":
        conn.commit()
        return jsonify({"ok": True, "id": mbr_id, "ya_aprobado": True})
    if estado == "draft":
        cur.execute("UPDATE mbr_templates SET estado='en_revision' WHERE id=?", (mbr_id,))
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                 record_id=str(mbr_id), meaning="aprueba",
                                 comment="Aprobación rápida para prueba de legajo de envasado")
    cur.execute("""UPDATE mbr_templates SET estado='aprobado', aprobado_por=?,
                     aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=?
                   WHERE id=?""", (user, sig_id, mbr_id))
    audit_log(cur, usuario=user, accion="APROBAR_MBR_RAPIDO",
              tabla="mbr_templates", registro_id=mbr_id,
              despues={"producto": producto, "estado": "aprobado", "signature_id": sig_id})
    conn.commit()
    return jsonify({"ok": True, "id": mbr_id, "version": res.get("version"),
                    "pasos": res.get("pasos"), "signature_id": sig_id})


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


@bp.route("/api/brd/mbr/aprobar-todas", methods=["POST"])
def mbr_aprobar_todas():
    """ACTIVACIÓN MASIVA de legajos automáticos · Sebastián 5-jun-2026.

    Genera (desde fórmula) y APRUEBA en lote todos los MBR faltantes, con UNA
    re-autenticación (password + TOTP si MFA). 21 CFR Part 11 §11.200(a)(1)(ii):
    serie de firmas durante un acceso continuo controlado. Solo Admin/Calidad.
    Después, con EBR_MODE=warn, cada producción crea su legajo automático."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    password = body.get("password", "")
    totp = body.get("totp_token", "")
    try:
        from blueprints.firmas import (_verify_password, _verify_totp_if_enrolled,
                                       crear_firma_directa)
    except Exception:
        from api.blueprints.firmas import (_verify_password, _verify_totp_if_enrolled,
                                           crear_firma_directa)
    user = session.get("compras_user", "")
    if not _verify_password(user, password):
        return jsonify({"error": "Credenciales inválidas", "codigo": "PWD"}), 401
    ok_totp, factor = _verify_totp_if_enrolled(user, totp)
    if not ok_totp:
        return jsonify({"error": "Token MFA inválido", "codigo": "MFA"}), 401
    conn = get_db(); cur = conn.cursor()
    productos = [r[0] for r in cur.execute(
        "SELECT DISTINCT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1 "
        "AND producto_nombre IS NOT NULL AND TRIM(producto_nombre)!='' "
        "ORDER BY producto_nombre").fetchall()]
    generados = 0; aprobados = 0; ya = 0; fallidos = []
    for p in productos:
        try:
            res = _generar_mbr_desde_formula(cur, p, usuario=user)
            if not res.get("ok"):
                fallidos.append({"producto": p, "error": res.get("error", "sin_formula")})
                continue
            mbr_id = res["id"]
            if not res.get("ya_existe"):
                generados += 1
            est_row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
            est = (est_row[0] if est_row else "") or ""
            if est == "aprobado":
                ya += 1
                continue
            if est == "draft":
                cur.execute("UPDATE mbr_templates SET estado='en_revision' WHERE id=? AND estado='draft'", (mbr_id,))
            sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                         record_id=mbr_id, meaning="aprueba", auth_factor=factor)
            cur.execute(
                "UPDATE mbr_templates SET estado='aprobado', aprobado_por=?, "
                "aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=? WHERE id=?",
                (user, sig_id, mbr_id))
            try:
                audit_log(cur, usuario=user, accion="APROBAR_MBR_BULK", tabla="mbr_templates",
                          registro_id=mbr_id, despues={"producto": p, "signature_id": sig_id})
            except Exception:
                pass
            aprobados += 1
        except Exception as e:
            fallidos.append({"producto": p, "error": str(e)[:140]})
    conn.commit()
    return jsonify({
        "ok": True,
        "total_productos": len(productos),
        "mbr_generados": generados,
        "mbr_aprobados": aprobados,
        "ya_estaban_aprobados": ya,
        "fallidos": fallidos,
        "nota": "MBR aprobados. Con EBR_MODE=warn cada producción crea su legajo automático.",
    })


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
    audit_log(None, usuario=user, accion="INICIAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"mbr_template_id": mbr["id"], "lote": lote,
                        "numero_op": numero_op, "fase": fase,
                        "pasos_clonados": n_clonados})
    return jsonify({"ok": True, "id": ebr_id, "numero_op": numero_op,
                     "pasos": n_clonados}), 201


@bp.route("/api/brd/legajo-rapido", methods=["POST"])
def legajo_rapido():
    """Crea un legajo EBR rápido (producto + lote + fase) con el resolver canónico
    crear_ebr_desde_mbr (resuelve MBR aprobado, sufijo de fase, idempotencia). Para el
    botón '+ Nueva orden de envasado' de la página de Órdenes (9-jun-2026)."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto") or "").strip()
    lote = (body.get("lote") or "").strip()
    fase = (body.get("fase") or "envasado").strip().lower()
    if not producto or not lote:
        return jsonify({"ok": False, "error": "producto y lote requeridos"}), 400
    if fase not in _FASES_VALIDAS:
        return jsonify({"ok": False, "error": "fase inválida"}), 400
    conn = get_db(); cur = conn.cursor()
    user = session.get("compras_user", "")
    r = crear_ebr_desde_mbr(cur, producto_nombre=producto, lote=lote, usuario=user, fase=fase)
    if not r.get("ok"):
        msg = ("El producto no tiene MBR APROBADO con pasos de esa fase · aprueba su MBR primero."
               if r.get("error") == "NO_MBR_APROBADO" else (r.get("detail") or r.get("error") or "error"))
        return jsonify({"ok": False, "error": msg, "detail": r.get("error")}), 409
    try:
        audit_log(cur, usuario=user or "sistema", accion="CREAR_LEGAJO_RAPIDO",
                  tabla="ebr_ejecuciones", registro_id=r.get("id"),
                  despues={"producto": producto, "lote": lote, "fase": fase})
    except Exception:
        pass
    conn.commit()
    return jsonify({"ok": True, "id": r.get("id"), "numero_op": r.get("numero_op"),
                    "link": f"/planta/orden/{r.get('id')}", "reusado": r.get("reusado", False)})


@bp.route("/api/brd/demo-legajo", methods=["POST"])
def demo_legajo():
    """DEMO (Sebastián 25-jun) · crea una orden EN CURSO + su legajo EBR para VER el batch record inline
    en Fabricación, SIN descontar MP (inserción directa · no pasa por el motor de descuento). Marcada
    'DEMO_LEGAJO' en observaciones → se borra con 🧹 Limpiar. Solo para ver la UI."""
    err = _require_login()
    if err:
        return err
    from database import get_db
    conn = get_db(); cur = conn.cursor()
    row = cur.execute("SELECT producto_nombre FROM mbr_templates WHERE estado='aprobado' "
                      "ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"error": "No hay ningún MBR aprobado · activá los legajos primero en "
                                 "/planta/activar-legajos"}), 400
    producto = row[0]
    from datetime import datetime, timedelta
    _co = datetime.now() - timedelta(hours=5)
    lote = 'DEMO-' + _co.strftime('%y%m%d%H%M%S')
    user = session.get("compras_user", "")
    cur.execute(
        "INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, "
        "inicio_real_at, estado, origen, observaciones) VALUES (?,?,?,?,?,?,?,?)",
        (producto, _co.strftime('%Y-%m-%d'), 10, 1, _co.isoformat(timespec='seconds'),
         'programado', 'eos_plan', 'DEMO_LEGAJO · sin descuento de MP · borrar con 🧹 Limpiar'))
    pid = cur.lastrowid
    try:
        r = crear_ebr_desde_mbr(cur, producto_nombre=producto, lote=lote, produccion_id=pid,
                                cantidad_objetivo_g=10000, usuario=user, notas='DEMO')
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "No se pudo crear el legajo demo: " + str(e)[:160]}), 500
    conn.commit()
    return jsonify({"ok": True, "producto": producto, "lote": lote, "produccion_id": pid,
                    "ebr_id": (r.get("id") if isinstance(r, dict) else None)})


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
    else:
        # por defecto NO mostrar legajos descartados (p.ej. los de prueba que limpió el jefe)
        where.append("LOWER(COALESCE(estado,'')) <> 'descartado'")
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
    # Timeline estilo MyBatch (Sebastián 6-jun-2026) · "Batch Record Bulk Lote N°"
    # línea de tiempo vertical de NODOS de etapa (no eventos sueltos): Orden de
    # Producción → Instrucciones de Fabricación (con estado por etapa) → Liberación.
    # OJO ESCAPES: este HTML va en un string Python '''...''' → NUNCA usar \n/\t
    # crudos en cadenas JS (Python los volvería saltos de línea reales y romperían
    # el <script>). Ver memoria feedback_js_escapes_template_python.
    html = '''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Timeline BR · ''' + str(ebr_id) + '''</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;font-family:'Inter',system-ui,Arial,sans-serif}
body{margin:0;background:#f5f3ff;padding:22px;color:#0f172a}
.wrap{max-width:880px;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:#fff;color:#7c3aed;font-size:13px;font-weight:700;text-decoration:none;padding:9px 16px;border-radius:10px;border:1px solid #e9d5ff;box-shadow:0 2px 8px rgba(124,58,237,.10)}
h1{text-align:center;color:#1e293b;margin:18px 0 2px;font-size:24px}
.sub{text-align:center;color:#6d28d9;font-weight:600;margin:0 0 24px;font-size:16px}
.tl{position:relative;padding-left:56px}
.tl::before{content:'';position:absolute;left:21px;top:8px;bottom:8px;width:3px;background:#fbcfe8}
.node{position:relative;margin-bottom:26px}
.node .ico{position:absolute;left:-49px;top:6px;width:42px;height:42px;border-radius:50%;background:#fb923c;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 3px 10px rgba(251,146,60,.4)}
.card{background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 3px 14px rgba(76,29,149,.08)}
.tag{display:inline-block;background:#fb923c;color:#fff;font-size:11px;font-weight:800;letter-spacing:.4px;padding:4px 12px;border-radius:6px;text-transform:uppercase;margin-bottom:12px}
.tag.fab{background:#7c2d12}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;font-size:13px}
.grid .lbl{color:#94a3b8;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.grid .val{color:#1e293b;margin-top:2px;font-weight:600}
.mono{font-family:ui-monospace,monospace;color:#1e40af}
.stages{list-style:none;margin:6px 0 0;padding:0}
.stages li{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 4px;border-bottom:1px solid #f1f5f9;font-size:13.5px}
.stages li:last-child{border-bottom:none}
.st-badge{font-size:10px;font-weight:800;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap}
.fin{background:#dcfce7;color:#166534}
.proc{background:#fef9c3;color:#854d0e}
.pend{background:#f1f5f9;color:#94a3b8}
.btns{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap}
.btns a{border:none;border-radius:9px;padding:9px 16px;font-size:12.5px;font-weight:700;cursor:pointer;text-decoration:none;color:#fff}
.b-ver{background:#fb923c}.b-desc{background:#ef4444}
</style></head><body>
<div class="wrap">
<a class="back" href="/planta/orden/''' + str(ebr_id) + '''">&larr; Volver a la Orden</a>
<h1 id="t1">Batch Record</h1>
<div class="sub" id="t2">Cargando…</div>
<div class="tl" id="timeline"></div>
</div>
<script>
var EBR_ID = ''' + str(ebr_id) + ''';
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'—';}
function stBadge(done,partial){
  if(done) return '<span class="st-badge fin">Finalizado</span>';
  if(partial) return '<span class="st-badge proc">En proceso</span>';
  return '<span class="st-badge pend">Pendiente</span>';
}
async function load(){
  try{
    var ctrl=new AbortController();var to=setTimeout(function(){ctrl.abort();},15000);
    var r;
    try{ r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store',signal:ctrl.signal}); }
    catch(fe){ clearTimeout(to); document.getElementById('t2').textContent='No se pudo cargar (timeout/red).'; return; }
    clearTimeout(to);
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){ document.getElementById('t2').textContent='Error: '+esc(d.error||r.status); return; }
    var h=d.header||{};
    document.getElementById('t1').textContent='Batch Record Bulk Lote N°: '+(h.lote_codigo||'—');
    document.getElementById('t2').textContent=h.producto||h.titulo||'—';
    // Estado de cada etapa (honesto · desde la data real)
    var prec=d.precauciones||[], chk=d.despeje_checklist||[], sheet=d.pesaje_sheet||[], pasos=d.pasos||[];
    var estado=(h.estado||'').toLowerCase();
    var liberado=(estado.indexOf('liber')>=0)||!!h.liberado_at_utc;
    var completado=liberado||(estado.indexOf('complet')>=0)||!!h.completado_at_utc;
    var precDone=prec.length>0;
    var chkDone=chk.length>0 && chk.every(function(x){return x.cumple===1;});
    var chkPart=chk.some(function(x){return x.cumple!=null;});
    var sheetDone=sheet.length>0 && sheet.every(function(x){return x.pesado;});
    var sheetPart=sheet.some(function(x){return x.pesado;});
    var pasosDone=completado||(pasos.length>0 && pasos.every(function(p){return p.completado_flag;}));
    var pasosPart=pasos.some(function(p){return p.completado_flag;});
    // Etapas estilo MyBatch (Instrucciones de Fabricación)
    var etapas=[
      {n:'1. Precauciones', done:precDone, part:false},
      {n:'2. Despeje de Línea - Dispensación', done:chkDone, part:chkPart},
      {n:'3. Pesaje de Materias Primas', done:sheetDone, part:sheetPart},
      {n:'4. Fabricación / Mezclado', done:pasosDone, part:pasosPart}
    ];
    var etapasHtml=etapas.map(function(e){
      return '<li><span>'+esc(e.n)+'</span>'+stBadge(e.done,e.part)+'</li>';
    }).join('');
    // Nodo 1: Orden de Producción
    var ordenCard=
      '<div class="node"><div class="ico">📋</div><div class="card">'+
        '<span class="tag">Orden de Producción</span>'+
        '<div class="grid">'+
          '<div><div class="lbl">N° de Lote Bulk</div><div class="val mono">'+esc(h.lote_codigo||'—')+'</div></div>'+
          '<div><div class="lbl">Tamaño de Lote</div><div class="val">'+(h.lote_size_g!=null?Number(h.lote_size_g).toLocaleString('es-CO')+' g':'—')+'</div></div>'+
          '<div><div class="lbl">Fecha / Hora</div><div class="val">'+dt(h.iniciado_at_utc)+'</div></div>'+
          '<div><div class="lbl">Estado Actual</div><div class="val">'+esc(h.estado||'—')+'</div></div>'+
          '<div><div class="lbl">Elaborado por</div><div class="val">'+esc(h.operario||'—')+'</div></div>'+
          '<div><div class="lbl">Supervisado por</div><div class="val">'+esc(h.supervisado_por||'—')+'</div></div>'+
        '</div>'+
        '<div class="btns">'+
          '<a class="b-ver" href="/planta/orden/'+EBR_ID+'">Ver</a>'+
          '<a class="b-desc" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">📄 Descargar</a>'+
        '</div>'+
      '</div></div>';
    // Nodo 2: Instrucciones de Fabricación
    var instrCard=
      '<div class="node"><div class="ico">📖</div><div class="card">'+
        '<span class="tag fab">Instrucciones de Fabricación</span>'+
        '<ul class="stages">'+etapasHtml+'</ul>'+
        '<div class="btns"><a class="b-ver" href="/planta/orden/'+EBR_ID+'">Ver</a></div>'+
      '</div></div>';
    // Nodo 3 (si liberado/completado): Liberación QC
    var libCard='';
    if(completado){
      libCard='<div class="node"><div class="ico" style="background:'+(liberado?'#16a34a':'#0891b2')+'">'+(liberado?'🔓':'🏁')+'</div><div class="card">'+
        '<span class="tag" style="background:'+(liberado?'#16a34a':'#0891b2')+'">'+(liberado?'Liberación de Calidad':'Fabricación Completada')+'</span>'+
        '<div class="grid">'+
          '<div><div class="lbl">'+(liberado?'Liberado por':'Completado')+'</div><div class="val">'+esc(liberado?(h.liberado_por_full||h.liberado_por||'—'):dt(h.completado_at_utc))+'</div></div>'+
          (h.rechazado_at_utc?'<div><div class="lbl">⛔ Rechazado</div><div class="val">'+esc(h.rechazado_motivo||'')+'</div></div>':'')+
        '</div>'+
      '</div></div>';
    }
    document.getElementById('timeline').innerHTML = ordenCard + instrCard + libCard;
  }catch(e){
    document.getElementById('t2').textContent='Error: '+esc(e&&e.message||e);
  }
}
load();
</script></body></html>'''
    return Response(html, mimetype='text/html')


def _pp_id_para_producto(cur, producto, ebr_produccion_id=None):
    """Resuelve el produccion_programada.id relevante para un producto (no hay FK · se
    enlaza por producto). Prefiere el produccion_id del EBR si coincide; si no, el más
    reciente no-cancelado del producto. Devuelve id o None."""
    if not producto:
        return None
    try:
        if ebr_produccion_id:
            r = cur.execute(
                "SELECT id FROM produccion_programada WHERE id=? "
                "AND LOWER(TRIM(producto))=LOWER(TRIM(?))",
                (ebr_produccion_id, producto)).fetchone()
            if r:
                return r[0]
        r = cur.execute(
            "SELECT id FROM produccion_programada "
            "WHERE LOWER(TRIM(producto))=LOWER(TRIM(?)) "
            "AND COALESCE(estado,'') NOT IN ('cancelado') "
            "ORDER BY id DESC LIMIT 1", (producto,)).fetchone()
        return r[0] if r else None
    except Exception:
        return None


def _materiales_envase_planeados(conn, producto, ebr_produccion_id=None, lote=''):
    """Material de envase PLANEADO de un producto desde la PROGRAMACIÓN (paridad MyBatch ·
    11-jun): por cada presentación, el envase + sus componentes (tapa/gotero/etiqueta vía
    sku_mee_config) con cant. REQUERIDA = unidades de esa presentación. Auto-carga la
    sección 'Materiales de Envase' del legajo cuando aún no hay envasado real. READ-ONLY."""
    if not producto:
        return []
    cur = conn.cursor()
    pp_id = _pp_id_para_producto(cur, producto, ebr_produccion_id)
    if not pp_id:
        return []
    try:
        from blueprints.programacion import _composicion_envases_lote
    except Exception:
        try:
            from api.blueprints.programacion import _composicion_envases_lote
        except Exception:
            return []
    try:
        comp = _composicion_envases_lote(cur, pp_id) or {}
    except Exception:
        return []
    variantes = comp.get('variantes') or []
    if not variantes:
        return []
    # sku_mee_config: sku_codigo(upper) -> [(mee_codigo, cant_por_unidad)]
    sku_mee = {}
    try:
        for r in cur.execute(
            "SELECT UPPER(TRIM(sku_codigo)), mee_codigo, COALESCE(cantidad_por_unidad,1) "
            "FROM sku_mee_config WHERE COALESCE(aplica,1)=1").fetchall():
            if r[1]:
                sku_mee.setdefault(r[0], []).append((str(r[1]).strip(), float(r[2] or 1)))
    except Exception:
        sku_mee = {}
    acc = {}  # codigo_mee -> requerida total
    for v in variantes:
        uds = int(v.get('unidades_estimadas') or 0)
        if uds <= 0:
            continue
        sku = (v.get('sku_shopify') or '').strip().upper()
        comps = sku_mee.get(sku)
        if comps:  # envase + tapa + gotero + etiqueta… definidos por SKU
            for cod, cx in comps:
                if cod:
                    acc[cod] = acc.get(cod, 0.0) + uds * cx
        else:  # sin config MEE · al menos el envase de la presentación
            env = (v.get('envase_codigo') or '').strip()
            if env:
                acc[env] = acc.get(env, 0.0) + uds
    if not acc:
        return []
    out = []
    for cod, req in sorted(acc.items(), key=lambda x: -x[1]):
        nom = ''
        try:
            n = cur.execute("SELECT COALESCE(descripcion,'') FROM maestro_mee WHERE codigo=?",
                            (cod,)).fetchone()
            nom = (n[0] if n else '') or ''
        except Exception:
            pass
        out.append({
            'lote_envasado': lote, 'lote_acond': lote,
            'material': (cod + (' ' + nom if nom else '')),
            'lote_material': '', 'requerida': round(req, 0),
            'recibida': None, 'devuelta': None, 'utilizada': None,
            'averiada': None, 'diferencia': None,
        })
    return out


def _presentaciones_planeadas(conn, producto, ebr_produccion_id=None):
    """Presentaciones PLANEADAS (estado 'Programado') de un producto desde la
    PROGRAMACIÓN · para auto-cargar el legajo de Envasado/Acondicionamiento cuando aún
    no hay envasado/acond real registrado (paridad MyBatch · 10-jun-2026).

    Una sola producción de granel → N presentaciones = envase × cliente:
      - Animus (DTC): variantes por ratio de ventas (helper canónico
        `_composicion_envases_lote`) MENOS la porción que va a clientes B2B (no doble
        contar).
      - B2B: una fila por aporte de pedido (`pedidos_b2b_lote`: cliente + envase + uds).

    Best-effort y READ-ONLY: si no hay programación enlazable o algo falla → []
    (el legajo queda como antes, sin presentaciones). NO escribe nada."""
    if not producto:
        return []
    cur = conn.cursor()
    pp_id = _pp_id_para_producto(cur, producto, ebr_produccion_id)
    if not pp_id:
        return []
    # Reusar las funciones CANÓNICAS de programación (mismas que el modal "Plan de
    #    envasado") para que el legajo muestre EXACTO lo mismo: Animus DTC (composición −
    #    B2B) + una fila por cada cliente B2B (ej. Kelly/Fernando Meza). 10-jun-2026.
    try:
        from blueprints.programacion import _composicion_envases_lote, _plan_envasado_por_cliente
    except Exception:
        try:
            from api.blueprints.programacion import _composicion_envases_lote, _plan_envasado_por_cliente
        except Exception:
            return []
    try:
        comp = _composicion_envases_lote(cur, pp_id) or {}
        plan = _plan_envasado_por_cliente(cur, pp_id, comp.get('variantes') or [])
    except Exception:
        return []
    out = []
    for grupo in (plan or []):
        cli = grupo.get('cliente') or 'Animus'
        for env in (grupo.get('envases') or []):
            uds = int(env.get('uds') or 0)
            ml = float(env.get('ml') or 0)
            out.append({
                'presentacion': env.get('etiqueta') or (f'{int(ml)}ml' if ml else '—'),
                'lote': '', 'unidades': uds, 'area': '',
                'cantidad_ml': (uds * ml) if (uds and ml) else None,
                'unidades_final': None, 'rend_pct': None,
                'estado': 'Programado', 'cliente': cli,
            })
    return out


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
                      rechazado_motivo,
                      COALESCE(numero_op,'') AS numero_op,
                      COALESCE(fase,'fabricacion') AS fase,
                      COALESCE(area_codigo,'') AS area_codigo,
                      COALESCE(cantidad_objetivo_g,0) AS cantidad_objetivo_g,
                      cantidad_real_g, yield_pct,
                      COALESCE(densidad_g_ml,0) AS densidad_g_ml,
                      COALESCE(ml_envasable,0) AS ml_envasable
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
            'numero_op': row[14] or '', 'fase': row[15] or 'fabricacion',
            'area_codigo': row[16] or '',
            'cantidad_objetivo_g': float(row[17] or 0),
            'cantidad_real_g': (float(row[18]) if row[18] is not None else None),
            'yield_pct': (float(row[19]) if row[19] is not None else None),
            'densidad_g_ml': (float(row[20]) if row[20] else None),
            'ml_envasable': (float(row[21]) if row[21] else None),
        }
        # Área o Línea: resolver el nombre legible desde areas_planta.
        try:
            _ac = out['header'].get('area_codigo') or ''
            if _ac:
                _ar = conn.execute(
                    "SELECT id, nombre FROM areas_planta WHERE codigo=?", (_ac,)).fetchone()
                out['header']['area_linea'] = (
                    (str(_ar[1]) + ' (' + _ac + ')') if _ar and _ar[1] else _ac)
                # area_id para enlazar el rótulo de limpieza F02 del área.
                out['header']['area_id'] = (_ar[0] if _ar else None)
        except Exception:
            pass
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
    # Fase a top-level (el front ramifica por d.fase) + presentaciones de envasado.
    # Para un legajo de ENVASADO, el cuerpo es "Lotes de Producto por Presentación"
    # (envase × unidades × área), leído de la tabla `envasado` por el lote físico.
    out['fase'] = out['header'].get('fase', 'fabricacion')
    # Rol del usuario + permisos (segregación de funciones GMP · la UI se adapta · 9-jun).
    # El backend YA bloquea (403); esto es para que la UI muestre el rol y oculte lo que
    # no le toca. Operario ejecuta · Calidad verifica/libera/corrige · Admin/Dir.Téc todo.
    _u = session.get("compras_user", "")
    _es_admin = _u in ADMIN_USERS
    _es_calidad = _u in CALIDAD_USERS
    _es_planta = _u in PLANTA_USERS
    out['mi_rol'] = {
        'usuario': _u,
        'rol': ('Dirección Técnica / Admin' if _es_admin
                else 'Calidad / Aseguramiento' if _es_calidad
                else 'Operario' if _es_planta else 'Usuario'),
        'puede_ejecutar': (_es_planta or _es_calidad or _es_admin),
        'puede_corregir': (_es_calidad or _es_admin),
        'puede_verificar': (_es_calidad or _es_admin),
        'puede_liberar': (_es_calidad or _es_admin),
        'puede_aprobar': (_es_calidad or _es_admin),
    }
    if out['fase'] == 'envasado':
        out['envasado_presentaciones'] = []
        try:
            _lote = (out['header'].get('lote_codigo') or '').strip()
            if _lote:
                _rows = conn.execute(
                    """SELECT COALESCE(e.presentacion,'') AS presentacion,
                              COALESCE(e.lote,'') AS lote, COALESCE(e.unidades,0) AS unidades,
                              COALESCE(ap.nombre, e.area_codigo, '') AS area,
                              COALESCE(e.estado,'') AS estado, COALESCE(e.envase_codigo,'') AS envase
                         FROM envasado e
                         LEFT JOIN areas_planta ap ON ap.codigo = e.area_codigo
                        WHERE UPPER(TRIM(e.lote))=UPPER(TRIM(?))
                        ORDER BY e.id ASC""",
                    (_lote,),
                ).fetchall()
                for r in _rows:
                    rd = dict(r)
                    out['envasado_presentaciones'].append({
                        'presentacion': rd.get('presentacion') or rd.get('envase') or '—',
                        'lote': rd.get('lote') or _lote,
                        'unidades': int(rd.get('unidades') or 0),
                        'area': rd.get('area') or '',
                        'cantidad_ml': None, 'unidades_final': None, 'rend_pct': None,
                        'estado': rd.get('estado') or 'En proceso',
                    })
        except Exception as _ep:
            __import__('logging').getLogger('brd').warning('envasado_presentaciones fallo: %s', _ep)
        # Auto-carga (MyBatch · 10-jun): si aún no hay envasado real registrado, mostrar
        # las presentaciones PLANEADAS desde la programación (Animus + B2B · 'Programado').
        if not out['envasado_presentaciones']:
            try:
                out['envasado_presentaciones'] = _presentaciones_planeadas(
                    conn, out['header'].get('producto'), out['header'].get('produccion_id'))
            except Exception as _epp:
                __import__('logging').getLogger('brd').warning('presentaciones planeadas OF fallo: %s', _epp)
        # + presentaciones agregadas/editadas A MANO (se suman a lo auto-cargado · editables).
        try:
            out['envasado_presentaciones'] = (out['envasado_presentaciones'] or []) + _presentaciones_manuales(conn, ebr_id)
        except Exception:
            pass
        # Materiales de Envase (envase + tapa usados) · conciliación de empaque (MyBatch):
        # cant. requerida vs devuelta/utilizada/averiada/diferencia. Iteración 2 · requerida.
        out['envasado_materiales'] = []
        try:
            _lote2 = (out['header'].get('lote_codigo') or '').strip()
            if _lote2:
                _erows = conn.execute(
                    "SELECT COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), "
                    "COALESCE(unidades,0) FROM envasado "
                    "WHERE UPPER(TRIM(lote))=UPPER(TRIM(?))", (_lote2,)).fetchall()
                _acc = {}
                for er in _erows:
                    _env = (er[0] or '').strip(); _tapa = (er[1] or '').strip()
                    _uds = int(er[2] or 0)
                    if _env:
                        _acc[_env] = _acc.get(_env, 0) + _uds
                    if _tapa:
                        _acc[_tapa] = _acc.get(_tapa, 0) + _uds
                for _cod, _req in _acc.items():
                    _nom = ''
                    try:
                        _n = conn.execute(
                            "SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?",
                            (_cod,)).fetchone()
                        _nom = (_n[0] if _n else '') or ''
                    except Exception:
                        pass
                    out['envasado_materiales'].append({
                        'lote_envasado': _lote2,
                        'material': (_cod + (' ' + _nom if _nom else '')),
                        'lote_material': '', 'requerida': _req,
                        'devuelta': None, 'utilizada': None, 'averiada': None, 'diferencia': None,
                    })
        except Exception as _em:
            __import__('logging').getLogger('brd').warning('envasado_materiales fallo: %s', _em)
        # Auto-carga (MyBatch · 11-jun): si aún no hay envasado real, mostrar el material
        # de envase PLANEADO del producto (envase + tapa/gotero/etiqueta · cant requerida).
        if not out['envasado_materiales']:
            try:
                out['envasado_materiales'] = _materiales_envase_planeados(
                    conn, out['header'].get('producto'),
                    out['header'].get('produccion_id'), out['header'].get('lote_codigo') or '')
            except Exception as _emp:
                __import__('logging').getLogger('brd').warning('materiales envase planeados OF fallo: %s', _emp)
        # + materiales agregados/editados A MANO (se suman a lo auto-cargado · editables).
        try:
            out['envasado_materiales'] = (out['envasado_materiales'] or []) + _materiales_envase_manuales(conn, ebr_id)
        except Exception:
            pass
    # Acondicionamiento (OA · 10-jun) · el cuerpo del legajo es "Unidades por
    # Presentación" (lo acondicionado del lote) + "Materiales de Empaque" (etiquetas,
    # plegadizas, insertos · leídos del mee_consumido). Espeja la rama de envasado.
    if out['fase'] == 'acondicionamiento':
        out['acond_presentaciones'] = []
        out['acond_materiales'] = []
        try:
            _loa = (out['header'].get('lote_codigo') or '').strip()
            if _loa:
                _arows = conn.execute(
                    """SELECT COALESCE(presentacion,'') AS presentacion,
                              COALESCE(lote,'') AS lote,
                              COALESCE(unidades_producidas,0) AS unidades,
                              COALESCE(estado,'') AS estado,
                              COALESCE(mee_consumido,'[]') AS mee_consumido,
                              COALESCE(sku,'') AS sku
                         FROM acondicionamiento
                        WHERE UPPER(TRIM(lote))=UPPER(TRIM(?))
                        ORDER BY id ASC""",
                    (_loa,),
                ).fetchall()
                _acc_oa = {}  # codigo -> unidades acumuladas (material de empaque)
                for r in _arows:
                    rd = dict(r)
                    out['acond_presentaciones'].append({
                        'presentacion': rd.get('presentacion') or rd.get('sku') or '—',
                        'lote': rd.get('lote') or _loa,
                        'unidades': int(rd.get('unidades') or 0),
                        'estado': rd.get('estado') or 'En proceso',
                    })
                    try:
                        _mlist = json.loads(rd.get('mee_consumido') or '[]')
                    except Exception:
                        _mlist = []
                    for _m in (_mlist or []):
                        _c = str(_m.get('codigo', _m.get('codigo_mee', '')) or '').strip()
                        _q = float(_m.get('cantidad', 0) or 0)
                        if _c:
                            _acc_oa[_c] = _acc_oa.get(_c, 0) + _q
                for _cod, _req in _acc_oa.items():
                    _nom = ''
                    try:
                        _n = conn.execute(
                            "SELECT descripcion FROM maestro_mee WHERE codigo=?",
                            (_cod,)).fetchone()
                        _nom = (_n[0] if _n else '') or ''
                    except Exception:
                        pass
                    out['acond_materiales'].append({
                        'lote_acond': _loa,
                        'material': (_cod + (' ' + _nom if _nom else '')),
                        'lote_material': '', 'requerida': _req,
                        'devuelta': None, 'utilizada': None, 'averiada': None, 'diferencia': None,
                    })
        except Exception as _ea:
            __import__('logging').getLogger('brd').warning('acond_presentaciones fallo: %s', _ea)
        # Auto-carga (MyBatch · 10-jun): si aún no hay acondicionamiento real, mostrar
        # las presentaciones PLANEADAS desde la programación (Animus + B2B · 'Programado').
        if not out['acond_presentaciones']:
            try:
                out['acond_presentaciones'] = _presentaciones_planeadas(
                    conn, out['header'].get('producto'), out['header'].get('produccion_id'))
            except Exception as _epp:
                __import__('logging').getLogger('brd').warning('presentaciones planeadas OA fallo: %s', _epp)
        # + presentaciones agregadas/editadas A MANO (se suman a lo auto-cargado · editables).
        try:
            out['acond_presentaciones'] = (out['acond_presentaciones'] or []) + _presentaciones_manuales(conn, ebr_id)
        except Exception:
            pass
        # Auto-carga del material de empaque planeado si aún no hay acond real.
        if not out['acond_materiales']:
            try:
                out['acond_materiales'] = _materiales_envase_planeados(
                    conn, out['header'].get('producto'),
                    out['header'].get('produccion_id'), out['header'].get('lote_codigo') or '')
            except Exception as _emp:
                __import__('logging').getLogger('brd').warning('materiales envase planeados OA fallo: %s', _emp)
        # + materiales agregados/editados A MANO (se suman a lo auto-cargado · editables).
        try:
            out['acond_materiales'] = (out['acond_materiales'] or []) + _materiales_envase_manuales(conn, ebr_id)
        except Exception:
            pass
    # Elaborado por (enriquecido) + Supervisado por · Sebastián 5-jun-2026:
    # "el área productiva la supervisa el Jefe de Producción; calidad el Jefe de
    # Control de Calidad". Resolvemos nombre+cargo desde usuarios_identidad
    # (fallback operarios.es_jefe_produccion). Solo lectura.
    try:
        op = out['header'].get('operario', '')
        if op:
            ir = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1",
                (op,)).fetchone()
            if ir:
                _partes = [p for p in (ir[0], ir[1]) if p and p != 'Por definir']
                if _partes:
                    out['header']['operario'] = ', '.join(_partes) + f' ({op})'
        # Supervisado por = Jefe de Producción (fases productivas).
        sup = ''
        jp = conn.execute(
            "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') FROM usuarios_identidad "
            "WHERE LOWER(cargo) LIKE '%jefe%produc%' AND COALESCE(activo,1)=1 LIMIT 1").fetchone()
        if jp and (jp[0] or jp[1]):
            sup = ((jp[0] + ', ') if jp[0] else '') + (jp[1] or 'Jefe de Producción')
        else:
            jo = conn.execute(
                "SELECT nombre, COALESCE(apellido,'') FROM operarios "
                "WHERE COALESCE(es_jefe_produccion,0)=1 LIMIT 1").fetchone()
            if jo:
                sup = (str(jo[0] or '') + ' ' + str(jo[1] or '')).strip() + ', Jefe de Producción'
        out['header']['supervisado_por'] = sup
    except Exception:
        pass
    # Aprobado por (Calidad) enriquecido · MyBatch parity (Sebastián 5-jun-2026):
    # "calidad la libera el Jefe de Control de Calidad". liberado_por es el username
    # firmante → resolvemos Nombre, Cargo (username) + fecha de liberación.
    try:
        lp = (out['header'].get('liberado_por') or '').strip()
        if lp:
            qr = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1",
                (lp,)).fetchone()
            full = lp
            if qr:
                _pq = [p for p in (qr[0], qr[1]) if p and p != 'Por definir']
                if _pq:
                    full = ', '.join(_pq) + f' ({lp})'
            _la = (out['header'].get('liberado_at_utc') or '')
            if _la:
                full += ' · ' + _la[:16].replace('T', ' ')
            out['header']['liberado_por_full'] = full
    except Exception:
        pass
    # Cantidad Disponible (mL) · MyBatch parity: granel producido menos el granel
    # ya envasado/acondicionado del MISMO lote (OF/OA). Sin envasado registrado =>
    # disponible = producido. Cálculo honesto sobre la propia data EOS (no inventado).
    try:
        prod_ml = out['header'].get('ml_envasable')
        lote_b = (out['header'].get('lote_codigo') or '').strip()
        if prod_ml is not None and lote_b:
            cons = conn.execute(
                "SELECT COALESCE(SUM(COALESCE(ml_envasable,0)),0) FROM ebr_ejecuciones "
                "WHERE lote_codigo=? AND id<>? AND COALESCE(fase,'') IN ('envasado','acondicionamiento')",
                (lote_b, ebr_id)).fetchone()
            consumido = float(cons[0] or 0) if cons else 0.0
            out['header']['cantidad_disponible_ml'] = max(0.0, round(float(prod_ml) - consumido, 2))
    except Exception:
        pass
    # 2. Pesajes MP
    # Resolver username → "Nombre, Cargo (user)" para Realizado/Verificado por
    # (MyBatch "Detalle del Pesaje"). Cache por request · solo lectura.
    _persona_cache = {}

    def _persona(u):
        u = (u or '').strip()
        if not u:
            return ''
        if u in _persona_cache:
            return _persona_cache[u]
        txt = u
        try:
            ir = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1", (u,)).fetchone()
            if ir:
                partes = [p for p in (ir[0], ir[1]) if p and p != 'Por definir']
                if partes:
                    txt = ', '.join(partes) + ' (' + u + ')'
        except Exception:
            pass
        _persona_cache[u] = txt
        return txt
    try:
        rows = conn.execute(
            """SELECT p.material_id, COALESCE(p.material_nombre,''),
                      p.cantidad_teorica_g, p.cantidad_real_g, COALESCE(p.lote_mp,''),
                      COALESCE(p.pesado_por,''), COALESCE(p.pesado_at_utc,''),
                      COALESCE(p.notas,''), p.id,
                      COALESCE(p.verificado_por,''), COALESCE(p.verificado_at_utc,''),
                      COALESCE(mm.nombre_inci,'')
               FROM ebr_pesajes p LEFT JOIN maestro_mps mm ON mm.codigo_mp=p.material_id
               WHERE p.ebr_id=? ORDER BY p.id""",
            (ebr_id,),
        ).fetchall()
        out['pesajes'] = [{
            'material_id': r[0], 'material_nombre': r[1], 'nombre_inci': r[11],
            'esperada_g': float(r[2] or 0), 'real_g': float(r[3] or 0),
            'lote_mp': r[4], 'operario': r[5], 'fecha': r[6],
            'observaciones': r[7], 'pesaje_id': r[8],
            'verificado_por': r[9], 'verificado_at': r[10],
            'realizado_por_full': _persona(r[5]),
            'verificado_por_full': _persona(r[9]),
            'delta_pct': round(((r[3] - r[2]) / r[2] * 100) if r[2] else 0, 2),
        } for r in rows]
    except Exception:
        out['pesajes'] = []
    # 2b. HOJA DE PESAJE (MyBatch parity · Sebastián 5-jun): TODAS las MP de la
    # fórmula con cant a pesar (teórico), lote FEFO (resuelto + producible) y la
    # cant pesada/operario si ya se registró. Es la "Pesaje de Materias Primas".
    try:
        prod_nom = out['header'].get('producto') or ''
        obj_g = float(out['header'].get('cantidad_objetivo_g') or 0)
        recorded = {}
        for p in out.get('pesajes', []):
            recorded.setdefault(p['material_id'], p)
        try:
            from blueprints.inventario import _fefo_lote_rotulo as _fefo
        except Exception:
            _fefo = None
        # Presupuesto de tiempo · el resolver FEFO escanea maestro_mps por cada MP
        # (en prod son miles de filas) → sin tope, una fórmula grande cuelga la
        # página. Tras ~2.5s dejamos de resolver lotes (se muestra '—'); el resto
        # de la hoja (%, cant a pesar, pesados) sale igual y el descuento real en
        # producción sigue usando el resolver completo. Sebastián 5-jun-2026.
        import time as _time
        _fefo_deadline = _time.monotonic() + 2.5
        _fefo_cache = {}
        sheet = []
        if prod_nom:
            fitems = conn.execute(
                "SELECT fi.material_id, COALESCE(fi.material_nombre,''), COALESCE(fi.porcentaje,0), "
                "COALESCE(mm.nombre_inci,'') "
                "FROM formula_items fi LEFT JOIN maestro_mps mm ON mm.codigo_mp=fi.material_id "
                "WHERE fi.producto_nombre=? ORDER BY fi.porcentaje DESC", (prod_nom,)).fetchall()
            for fr in fitems:
                mid = str(fr[0] or '').strip()
                if not mid:
                    continue
                pct = float(fr[2] or 0)
                cant_a_pesar = round(pct / 100.0 * obj_g, 2) if obj_g else None
                rec = recorded.get(mid)
                lote = (rec['lote_mp'] if rec and rec.get('lote_mp') else '')
                if not lote and _fefo:
                    if mid in _fefo_cache:
                        lote = _fefo_cache[mid]
                    elif _time.monotonic() < _fefo_deadline:
                        try:
                            lote = _fefo(conn, mid, fr[1]) or ''
                        except Exception:
                            lote = ''
                        _fefo_cache[mid] = lote
                    else:
                        lote = ''  # presupuesto agotado · no colgar la página
                sheet.append({
                    'material_id': mid, 'material_nombre': fr[1] or '',
                    'nombre_inci': fr[3] or '',
                    'porcentaje': pct,
                    'cant_a_pesar_g': cant_a_pesar,
                    'lote': lote or '—',
                    'cant_pesada_g': (rec['real_g'] if rec else None),
                    'pesado_por': (rec['operario'] if rec else ''),
                    'pesado_at': (rec['fecha'] if rec else ''),
                    'pesado': bool(rec),
                    'pesaje_id': (rec.get('pesaje_id') if rec else None),
                    'realizado_por_full': (rec.get('realizado_por_full') if rec else ''),
                    'verificado_por': (rec.get('verificado_por') if rec else ''),
                    'verificado_at': (rec.get('verificado_at') if rec else ''),
                    'verificado_por_full': (rec.get('verificado_por_full') if rec else ''),
                    'obs_pesaje': (rec.get('observaciones') if rec else ''),
                })
        out['pesaje_sheet'] = sheet
    except Exception:
        out['pesaje_sheet'] = []
    # 2c. Precauciones / equipos (MyBatch "Instrucción de Manufactura" · estación ①)
    try:
        prows = conn.execute(
            "SELECT COALESCE(tipo,'precaucion'), descripcion, COALESCE(registrado_por,''), "
            "COALESCE(registrado_at_utc,'') FROM ebr_precauciones WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        out['precauciones'] = [{'tipo': r[0], 'descripcion': r[1],
                                'registrado_por': r[2], 'fecha': r[3]} for r in prows]
    except Exception:
        out['precauciones'] = []
    # 2d. Despeje de Línea · checklist 13 ítems (MyBatch · Sebastián 5/6-jun).
    # DOS etapas independientes con el mismo template: 'dispensacion' (sección 2)
    # y 'fabricacion' (sección 4). CUMPLE: 1=Sí, 0=No, None=pendiente.
    def _despeje_por_etapa(etapa):
        reg = {}
        try:
            drows = conn.execute(
                "SELECT item_idx, cumple, COALESCE(observaciones,''), "
                "COALESCE(registrado_por,''), COALESCE(registrado_at_utc,'') "
                "FROM ebr_despeje_items WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=?",
                (ebr_id, etapa)).fetchall()
            for dr in drows:
                reg[int(dr[0])] = dr
        except Exception:
            reg = {}
        chk = []
        for i, texto in enumerate(DESPEJE_LINEA_ITEMS):
            r = reg.get(i)
            chk.append({
                'idx': i, 'texto': texto,
                'cumple': (int(r[1]) if r and r[1] is not None else None),
                'observaciones': (r[2] if r else ''),
                'registrado_por': (r[3] if r else ''),
                'fecha': (r[4] if r else ''),
            })
        return chk
    try:
        out['despeje_checklist'] = _despeje_por_etapa('dispensacion')
        out['despeje_checklist_fab'] = _despeje_por_etapa('fabricacion')
    except Exception:
        out['despeje_checklist'] = []
        out['despeje_checklist_fab'] = []
    # 3. Pasos (Fabricación/Mezcla) · FIX 6-jun: la tabla real es
    # ebr_pasos_ejecutados (no 'ebr_pasos', que no existe → la sección 5 salía
    # siempre vacía). Realizado por = operario_username; Verificado por = qc_username.
    try:
        rows = conn.execute(
            """SELECT orden, descripcion, COALESCE(estado,''),
                      COALESCE(iniciado_at_utc,''), COALESCE(completado_at_utc,''),
                      COALESCE(operario_username,''), COALESCE(observaciones,''),
                      COALESCE(qc_username,'')
               FROM ebr_pasos_ejecutados WHERE ebr_id=? ORDER BY orden""",
            (ebr_id,),
        ).fetchall()
        out['pasos'] = [{
            'orden': r[0], 'descripcion': r[1], 'estado': r[2],
            'iniciado': r[3], 'completado': r[4],
            'operario': r[5], 'observaciones': r[6],
            'verificado_por': r[7],
            'realizado_por_full': _persona(r[5]),
            'verificado_por_full': _persona(r[7]),
            'completado_flag': bool(r[4]),
        } for r in rows]
    except Exception:
        out['pasos'] = []
    # 4. IPC resultados
    # 4. Controles en Proceso (IPC) · FIX 6-jun: la tabla real es ipc_resultados +
    # ipc_specs (no 'ebr_ipc_resultados', inexistente → la sección 6 salía vacía).
    # Specs por producto (MBR) + resultado por lote. CONTROL/RESULTADO/conforme/
    # observaciones/Realizado por (Calidad).
    try:
        mbr_tpl = out['header'].get('mbr_template_id')
        rows = conn.execute(
            """SELECT s.parametro, COALESCE(s.unidad,''), s.valor_min, s.valor_max,
                      r.valor_medido, COALESCE(r.valor_texto,''), r.conforme,
                      COALESCE(r.medido_por,''), COALESCE(r.medido_at_utc,''),
                      COALESCE(r.notas,''), COALESCE(s.obligatorio,1), s.id
               FROM ipc_specs s
               LEFT JOIN ipc_resultados r ON r.ipc_spec_id=s.id AND r.ebr_id=?
               WHERE s.mbr_template_id=? ORDER BY s.id""",
            (ebr_id, mbr_tpl),
        ).fetchall()
        ipc = []
        nombres_mbr = set()
        for r in rows:
            vmin, vmax = r[2], r[3]
            rango = ''
            if vmin is not None and vmax is not None:
                rango = f"{vmin} – {vmax} {r[1]}".strip()
            elif vmin is not None:
                rango = f"≥ {vmin} {r[1]}".strip()
            elif vmax is not None:
                rango = f"≤ {vmax} {r[1]}".strip()
            resultado = (f"{r[4]} {r[1]}".strip() if r[4] is not None else (r[5] or ''))
            ipc.append({
                'control': r[0], 'unidad': r[1], 'rango': rango,
                'resultado': resultado,
                'conforme': (int(r[6]) if r[6] is not None else None),
                'observaciones': r[9] or 'No aplica',
                'realizado_por': r[7], 'realizado_por_full': _persona(r[7]),
                'fecha': r[8], 'obligatorio': bool(r[10]),
                'tipo': 'mbr', 'spec_id': r[11],
            })
            nombres_mbr.add((r[0] or '').strip().lower())
        # Controles ESTÁNDAR siempre presentes (los que el MBR no define).
        est = {}
        try:
            for er in conn.execute(
                """SELECT control_codigo, COALESCE(valor_texto,''), conforme,
                          COALESCE(observaciones,''), COALESCE(medido_por,''),
                          COALESCE(medido_at_utc,'')
                   FROM ipc_estandar_resultados WHERE ebr_id=?""",
                (ebr_id,),
            ).fetchall():
                est[er[0]] = er
        except Exception:
            est = {}
        for cod, nom, uni in IPC_ESTANDAR:
            if nom.strip().lower() in nombres_mbr:
                continue  # el MBR ya define este control · no duplicar
            er = est.get(cod)
            conf = (int(er[2]) if er and er[2] is not None else None)
            ipc.append({
                'control': nom, 'unidad': uni, 'rango': '',
                'resultado': (er[1] if er else ''),
                'conforme': conf,
                'observaciones': (er[3] if er and er[3] else ('No aplica' if conf == 2 else '')),
                'realizado_por': (er[4] if er else ''),
                'realizado_por_full': _persona(er[4] if er else ''),
                'fecha': (er[5] if er else ''), 'obligatorio': False,
                'tipo': 'estandar', 'codigo': cod,
            })
        out['ipc'] = ipc
    except Exception:
        out['ipc'] = []
    # 7. Observaciones Generales del Proceso (MyBatch ⑦) · bitácora.
    try:
        rows = conn.execute(
            "SELECT descripcion, COALESCE(registrado_por,''), COALESCE(registrado_at_utc,'') "
            "FROM ebr_observaciones WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
        out['observaciones_proceso'] = [{
            'descripcion': r[0], 'registrado_por': r[1],
            'registrado_por_full': _persona(r[1]), 'fecha': r[2],
        } for r in rows]
    except Exception:
        out['observaciones_proceso'] = []
    # 8. Registros Físicos del Proceso (MyBatch ⑧) · PDFs adjuntos.
    try:
        rows = conn.execute(
            "SELECT id, descripcion, COALESCE(tipo,''), "
            "(CASE WHEN COALESCE(archivo_b64,'')!='' THEN 1 ELSE 0 END) AS tiene_pdf, "
            "COALESCE(registrado_por,''), COALESCE(registrado_at_utc,'') "
            "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        out['registros_fisicos'] = [{
            'id': r[0], 'descripcion': r[1], 'tipo': r[2],
            'tiene_pdf': bool(r[3]), 'registrado_por': r[4], 'fecha': r[5],
        } for r in rows]
    except Exception:
        out['registros_fisicos'] = []
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
    # 6. Audit log filtrado + Correcciones (Audit Trail Part 11 · MyBatch parity).
    # A nivel orden (registro_id=ebr_id) y por MP/paso/IPC (despues contiene ebr_id).
    try:
        rows = conn.execute(
            """SELECT fecha, usuario, accion, COALESCE(detalle,''),
                      COALESCE(antes,''), COALESCE(despues,''), COALESCE(tabla,'')
               FROM audit_log
               WHERE (tabla='ebr_ejecuciones' AND registro_id = ?)
                  OR (tabla IN ('ebr_pesajes','ebr_pasos_ejecutados','ipc_resultados',
                                'ipc_estandar_resultados','ebr_despeje_items','ebr_despeje_linea')
                      AND (despues LIKE ? OR despues LIKE ?))
               ORDER BY fecha DESC LIMIT 200""",
            (str(ebr_id), '%"ebr_id": ' + str(ebr_id) + ',%',
             '%"ebr_id": ' + str(ebr_id) + '}%'),
        ).fetchall()
        out['audit'] = [{
            'fecha': r[0], 'usuario': r[1], 'accion': r[2], 'detalle': r[3],
        } for r in rows]
        # Correcciones con diff campo/anterior/nuevo (parse antes/despues JSON).
        correcciones = []
        for r in rows:
            try:
                antes = _json.loads(r[4]) if r[4] else {}
            except Exception:
                antes = {}
            try:
                despues = _json.loads(r[5]) if r[5] else {}
            except Exception:
                despues = {}
            campos = []
            if isinstance(despues, dict):
                for k, vn in despues.items():
                    if k == 'ebr_id':
                        continue
                    va = antes.get(k) if isinstance(antes, dict) else None
                    if str(va) != str(vn):  # solo cambios reales
                        campos.append({'campo': k,
                                       'anterior': ('' if va is None else str(va)),
                                       'nuevo': ('' if vn is None else str(vn))})
            correcciones.append({
                'fecha': r[0], 'usuario': r[1],
                'usuario_full': _persona(r[1]), 'accion': r[2],
                'detalle': r[3], 'tabla': r[6], 'campos': campos,
            })
        out['correcciones'] = correcciones
    except Exception:
        out['audit'] = []
        out['correcciones'] = []
    # Resumen métricas
    completados = sum(1 for p in out['pasos'] if p['completado_flag'])
    out['progreso_pasos_pct'] = round((completados / len(out['pasos']) * 100) if out['pasos'] else 0, 1)
    out['pesajes_count'] = len(out['pesajes'])
    out['ipc_dentro_rango'] = sum(1 for i in out['ipc'] if i.get('conforme') == 1)
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
    d = _ebr_to_dict(row, pasos)
    # producto + área para el header del legajo (alinear con MyBatch · Sebastián 25-jun)
    try:
        mb = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?",
                          (d.get("mbr_template_id"),)).fetchone()
        d["producto_nombre"] = (mb[0] if mb else "")
    except Exception:
        d["producto_nombre"] = ""
    try:
        ar = conn.execute(
            "SELECT COALESCE(ap.nombre,'') FROM produccion_programada pp "
            "LEFT JOIN areas_planta ap ON ap.id=pp.area_id WHERE pp.id=?",
            (d.get("produccion_id"),)).fetchone()
        d["area_nombre"] = (ar[0] if ar else "")
    except Exception:
        d["area_nombre"] = ""
    # Rol del usuario en el batch (segregación de funciones GMP · el runner se adapta)
    d["mi_rol"] = _batch_role_info(session.get("compras_user", ""))
    # Cierre · 3ª firma Director Técnico + correcciones (Part 11) + ajustes de MP
    try:
        dt = conn.execute("SELECT COALESCE(aprobado_dt_por,''), COALESCE(aprobado_dt_at_utc,'') "
                          "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        d["aprobado_dt_por"] = (dt[0] if dt else "")
        d["aprobado_dt_at"] = (dt[1] if dt else "")
    except Exception:
        d["aprobado_dt_por"] = ""
        d["aprobado_dt_at"] = ""
    try:
        d["correcciones"] = [dict(r) for r in conn.execute(
            "SELECT COALESCE(campo_afectado,'') AS campo_afectado, COALESCE(motivo,'') AS motivo, "
            "COALESCE(descripcion,'') AS descripcion, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_correcciones "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()]
    except Exception:
        d["correcciones"] = []
    try:
        d["ajustes_mp"] = [dict(r) for r in conn.execute(
            "SELECT COALESCE(material,'') AS material, COALESCE(cantidad_g,0) AS cantidad_g, "
            "COALESCE(motivo,'') AS motivo, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_ajustes_mp "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()]
    except Exception:
        d["ajustes_mp"] = []
    return jsonify(d)


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
    # CAS (race · M27): solo completar si el paso sigue pendiente/en_proceso ·
    # evita que dos completados concurrentes se pisen la e-firma/QC.
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
           WHERE id = ? AND estado IN ('en_proceso', 'pendiente')""",
        (op_username, observaciones,
         int(signature_id) if signature_id else None,
         qc_username,
         int(qc_signature_id) if qc_signature_id else None,
         paso["id"]),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "paso ya completado (concurrencia) · refrescá",
                        "codigo": "ESTADO_CAMBIO"}), 409
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
    # Ahora cargamos lote + lote_codigo (lote FISICO) y lo dejamos como dict.
    # FIX 12-jun: lote_codigo SI existe (ALTER ebr_ejecuciones · database.py:7933,
    # backfill COALESCE(lote_codigo,lote)). El PT se keyea por el lote fisico, no
    # por la llave sufijada -OF/-OA (antes inflaba el PT una vez por fase · A-3).
    _ef = cur.execute(
        "SELECT mbr_template_id, lote, lote_codigo FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)
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
           WHERE id = ? AND estado IN ('iniciado', 'en_proceso')""",
        (cantidad_real, yield_pct, densidad, ml_envasable,
         uds_teoricas, uds_buenas, yield_uds_pct, ebr_id),
    )
    if cur.rowcount == 0:
        # CAS (race · regla M-race): otro worker ya completó este EBR · evita
        # doble Entrada PT en CUARENTENA (infla el PT · A-3/M10).
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue completado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
    # INVIMA-FIX · 21-may-2026 · cuarentena explícita auto al completar
    # Antes: lote PT quedaba 'completado' pero NO había movimiento de
    # Entrada con estado_lote='CUARENTENA' · podía usarse antes de QC.
    # Ahora: INSERT movimientos · libera_ebr promueve a VIGENTE (Fix prev).
    cuarentena_creada = False
    try:
        # A-3 (Sebastian 12-jun): el PT vendible se cuenta al terminar la fase FINAL
        # del lote + liberar. Keyear por LOTE FISICO (lote_codigo), no la llave
        # sufijada. Gate de fase terminal: si existe un EBR de una fase POSTERIOR
        # para el mismo lote fisico, esta fase NO crea el PT (lo creara la final) ->
        # evita 2-3 Entradas PT del mismo lote (una por OP/OF/OA · M10/M3).
        lote_ref = (ebr_full.get('lote_codigo') or ebr_full.get('lote') or '').strip()
        _FASE_ORDEN = {'fabricacion': 1, 'envasado': 2, 'acondicionamiento': 3}
        _orden_actual = _FASE_ORDEN.get(ebr['fase'] or 'fabricacion', 1)
        _hay_fase_posterior = False
        if lote_ref:
            for _r in cur.execute(
                "SELECT DISTINCT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones "
                "WHERE COALESCE(NULLIF(lote_codigo,''), lote) = ? AND id != ?",
                (lote_ref, ebr_id)).fetchall():
                if _FASE_ORDEN.get(_r[0], 1) > _orden_actual:
                    _hay_fase_posterior = True
                    break
        if lote_ref and cantidad_real and cantidad_real > 0 and not _hay_fase_posterior:
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
    audit_log(None, usuario=user, accion="COMPLETAR_EBR",
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


@bp.route("/api/brd/ebr/<int:ebr_id>/firmar-rapido", methods=["POST"])
def firmar_ebr_rapido(ebr_id):
    """Crea una e-firma server-side (identidad de la sesión · 21 CFR Part 11 §11.200(a)(1)(ii)
    acceso continuo) para una acción del lote, y devuelve signature_id para encadenar con
    liberar/etc. 'libera'/'verifica' requieren Calidad/Dirección Técnica. Botones de cierre
    del batch (9-jun-2026)."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    meaning = (body.get("meaning") or "").strip()
    if meaning not in ("libera", "ejecuta", "verifica", "aprueba"):
        return jsonify({"ok": False, "error": "meaning inválido"}), 400
    user = session.get("compras_user", "")
    if meaning in ("libera", "verifica", "aprueba") and user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"ok": False, "error": "Solo Calidad / Dirección Técnica puede firmar esta acción"}), 403
    conn = get_db(); cur = conn.cursor()
    if not cur.execute("SELECT id FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone():
        return jsonify({"ok": False, "error": "EBR no encontrado"}), 404
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="ebr_ejecuciones",
                                 record_id=str(ebr_id), meaning=meaning,
                                 comment="Firma de cierre/verificación de lote")
    conn.commit()
    return jsonify({"ok": True, "signature_id": sig_id})


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

    # GATE MICRO · Fase 2 (14-jun · decisión Sebastián = bloqueo duro). El lote NO se
    # libera si tiene un resultado micro FUERA DE SPEC DE INDUSTRIA sin resolver (OOS
    # abierto) — esto es incondicional y seguro (solo dispara con dato real de OOS, no
    # rompe lotes sin micro). El requisito de que el análisis micro ESTÉ PRESENTE
    # ("faltante") es más estricto y se enciende por fases con BRD_MICRO_GATE='strict'
    # (igual que EBR_MODE off→warn→strict), para no frenar la operación antes de que
    # estén cargando micro consistentemente.
    try:
        _mr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _lote_pt = (_mr[0] if _mr else '') or ''
    except Exception:
        _lote_pt = ''
    if _lote_pt:
        try:
            micro_oos = cur.execute(
                "SELECT mr.microorganismo, mr.valor, mr.valor_texto, mr.unidad "
                "FROM calidad_micro_resultados mr "
                "LEFT JOIN calidad_oos o ON o.id = mr.oos_id "
                "WHERE (mr.ebr_id=? OR mr.lote=?) AND mr.estado='fuera_industria' "
                "AND (mr.oos_id IS NULL OR LOWER(COALESCE(o.estado,'')) NOT IN ('cerrado','rechazado','descartado')) "
                "ORDER BY mr.id DESC LIMIT 1",
                (ebr_id, _lote_pt),
            ).fetchone()
        except Exception:
            micro_oos = None  # tabla/columna ausente · deploy-safe
        if micro_oos:
            return jsonify({
                "error": (f"No se puede liberar: análisis microbiológico FUERA DE SPEC "
                          f"({micro_oos[0]}: {micro_oos[1] if micro_oos[1] is not None else micro_oos[2]} "
                          f"{micro_oos[3] or ''}) sin OOS resuelto para el lote {_lote_pt}. "
                          f"Resolvé el OOS micro antes de liberar."),
                "codigo": "MICRO_OOS",
            }), 409
        # Modo del gate "micro presente": app_settings.micro_gate_mode (toggle desde la
        # UI de Calidad, sin tocar Render) → fallback env BRD_MICRO_GATE → 'off'.
        _gate_mode = 'off'
        try:
            _gm = cur.execute("SELECT valor FROM app_settings WHERE clave='micro_gate_mode' LIMIT 1").fetchone()
            if _gm and _gm[0]:
                _gate_mode = str(_gm[0]).lower()
            else:
                import os as _os_micro
                _gate_mode = _os_micro.environ.get('BRD_MICRO_GATE', 'off').lower()
        except Exception:
            import os as _os_micro
            _gate_mode = _os_micro.environ.get('BRD_MICRO_GATE', 'off').lower()
        if _gate_mode == 'strict':
            try:
                _micro_ok = cur.execute(
                    "SELECT COUNT(*) FROM calidad_micro_resultados "
                    "WHERE (ebr_id=? OR lote=?) AND estado IN ('ok','fuera_meta')",
                    (ebr_id, _lote_pt),
                ).fetchone()[0]
            except Exception:
                _micro_ok = 1  # deploy-safe
            if not _micro_ok:
                return jsonify({
                    "error": (f"No se puede liberar: falta el análisis microbiológico del "
                              f"lote {_lote_pt} (BRD_MICRO_GATE=strict). Registrá el resultado "
                              f"micro conforme antes de liberar."),
                    "codigo": "MICRO_FALTANTE",
                }), 409

    # Audit 3-jun · GATE DE COMPLETITUD del legajo · solo EBR_MODE='strict' (BPM
    # duro). En 'warn' (piloto) NO bloquea, para no frenar mientras se adopta.
    if _ebr_mode_now(cur) == 'strict':
        # #5/#6 (27-jun · auditoría de planta · solo FABRICACIÓN del granel) · cerrar 2 huecos del gate.
        _fase_lib = str((cur.execute("SELECT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones WHERE id=?",
                                     (ebr_id,)).fetchone() or ['fabricacion'])[0]).strip().lower()
        if _fase_lib == 'fabricacion':
            # #5 · sin registro de pesaje/dispensado de MP no se libera (antes un EBR con CERO pesajes pasaba:
            # el gate de 2ª firma de abajo cuenta 0 sin-verificar → ok). Un lote sin dispensado es inadmisible.
            try:
                _n_pes = cur.execute("SELECT COUNT(*) FROM ebr_pesajes WHERE ebr_id=?", (ebr_id,)).fetchone()[0]
            except Exception:
                _n_pes = 0
            if _n_pes == 0:
                return jsonify({"error": "No se puede liberar: no hay registro de pesaje/dispensado de "
                                "materias primas del lote.", "codigo": "SIN_PESAJES"}), 409
            # #6 · rendimiento (yield) fuera de rango razonable (80-115%) exige justificación (GMP · un yield
            # anómalo —pérdida de batch o error de tara— no puede liberarse en silencio · queda en el audit).
            try:
                _yp = (cur.execute("SELECT yield_pct FROM ebr_ejecuciones WHERE id=?",
                                   (ebr_id,)).fetchone() or [None])[0]
            except Exception:
                _yp = None
            if _yp is not None and (_yp < 80 or _yp > 115) and not (body.get('yield_justificacion') or '').strip():
                return jsonify({"error": f"Rendimiento fuera de rango ({_yp}%) · GMP exige justificar un yield "
                                f"anómalo (<80% o >115%) antes de liberar.",
                                "codigo": "YIELD_FUERA_RANGO", "yield_pct": _yp}), 409
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

    # CAS (race multi-worker · regla M-race): transicionar SOLO si sigue en un
    # estado liberable. Sin esto, un liberar y un rechazar concurrentes (ambos
    # pasan el check-then-act de arriba) podían dejar el EBR 'rechazado' pero con
    # el PT ya promovido a VIGENTE = producto rechazado vendible (riesgo INVIMA).
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'liberado',
                 liberado_por = ?,
                 liberado_at_utc = datetime('now', 'utc'),
                 liberado_signature_id = ?
           WHERE id = ? AND estado IN ('completado', 'en_revision_qc')""",
        (user, int(signature_id), ebr_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue liberado/rechazado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
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
        # A-3 (12-jun): el PT ahora se crea bajo el LOTE FISICO (lote_codigo) en la
        # fase final · liberar debe promoverlo por ese mismo lote fisico (antes
        # usaba la llave sufijada 'lote' y no encontraba el PT tras el fix).
        lote_ref = ((lote_row['lote_codigo'] or lote_row['lote']) if lote_row else '') or ''
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
    audit_log(None, usuario=user, accion="LIBERAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"liberado_por": user, "signature_id": signature_id,
                       "pt_lotes_promovidos": pt_lote_promovidos,
                       "yield_justificacion": (body.get('yield_justificacion') or '').strip() or None})
    # ENVASADO Fase 2 (26-jun · Sebastián) · al LIBERAR el granel de FABRICACIÓN (QC aprobó → PT VIGENTE)
    # se HABILITA automático el legajo de Envasado del MISMO lote físico (idempotente vía crear_ebr_desde_mbr
    # · best-effort · NO bloquea la liberación si falla). SOLO fase='fabricacion' (no encadenar al liberar un
    # envasado/acondicionamiento). Así Envasado queda "en blanco" hasta que algo se libera (no autocarga prod).
    _envasado_habilitado = None
    try:
        _erow = conn.execute(
            "SELECT COALESCE(e.fase,'fabricacion'), COALESCE(m.producto_nombre,''), "
            "COALESCE(e.lote_codigo, e.lote) "
            "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id "
            "WHERE e.id=?", (ebr_id,)).fetchone()
        if _erow and str(_erow[0]).strip().lower() == 'fabricacion' and _erow[1] and _erow[2]:
            _res_env = crear_ebr_desde_mbr(conn.cursor(), producto_nombre=_erow[1],
                                           lote=_erow[2], usuario=user, fase='envasado')
            conn.commit()
            if _res_env.get('ok'):
                _envasado_habilitado = _res_env.get('id')
                if not _res_env.get('reusado'):
                    audit_log(None, usuario=user, accion="AUTO_CREAR_EBR_ENVASADO",
                              tabla="ebr_ejecuciones", registro_id=_res_env.get('id'),
                              despues={"origen_fabricacion_ebr": ebr_id, "lote": _erow[2]})
    except Exception as _e2:
        import logging as _log2
        _log2.getLogger('inventario.brd').warning(
            'auto-crear EBR envasado al liberar fallo (no bloquea): %s', _e2)
    return jsonify({"ok": True, "estado": "liberado",
                    "pt_lotes_promovidos": pt_lote_promovidos,
                    "envasado_ebr_id": _envasado_habilitado})


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
    # CAS (race · igual que liberar): no rechazar si ya se liberó/rechazó.
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'rechazado',
                 rechazado_motivo = ?,
                 rechazado_at_utc = datetime('now', 'utc')
           WHERE id = ? AND estado IN ('completado', 'en_revision_qc')""",
        (motivo, ebr_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue liberado/rechazado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
    conn.commit()
    audit_log(None, usuario=user, accion="RECHAZAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"motivo": motivo, "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "rechazado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/descartar", methods=["POST"])
def descartar_ebr(ebr_id):
    """Elimina un legajo (EBR) creado POR ERROR del sistema (artefacto de bug, sin
    ejecución real) · solo Admin. HARD delete (sin rastro en la lista ni en el legajo):
    borra el EBR y sus filas hijas. CANDADO: solo aplica a iniciado/en_proceso/cancelado
    · un completado/liberado/rechazado representa un LOTE REAL y NO se elimina (409).
    Deja un audit_log de mantenimiento (quién/qué/cuándo · no es un lote en la lista).
    Sebastián 10-jun-2026."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS:
        return jsonify({"error": "solo Admin puede eliminar un legajo"}), 403
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "Legajo inventado por error del sistema").strip()
    conn = get_db(); cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, COALESCE(numero_op,'') AS numero_op, "
        "COALESCE(lote_codigo, lote) AS lote, COALESCE(fase,'fabricacion') AS fase "
        "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    estado = ebr["estado"]
    if estado in ("completado", "liberado", "rechazado"):
        return jsonify({"error": f"este legajo es un lote REAL ({estado}) · no se elimina"}), 409
    # audit de mantenimiento ANTES de borrar (rastro interno · no un batch en la lista).
    audit_log(cur, usuario=user, accion="ELIMINAR_EBR_ERRONEO",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              antes={"estado": estado, "numero_op": ebr["numero_op"],
                     "lote": ebr["lote"], "fase": ebr["fase"]},
              despues={"motivo": motivo})
    # Hijas (best-effort · según migraciones algunas tablas pueden no existir).
    for _t in ("ebr_pasos_ejecutados", "ipc_resultados", "ebr_pesajes",
               "ebr_despeje_items", "ebr_artes_codificacion", "ebr_observaciones",
               "ebr_registros_fisicos", "ebr_conciliacion_material", "ebr_precauciones"):
        try:
            cur.execute(f"DELETE FROM {_t} WHERE ebr_id=?", (ebr_id,))
        except Exception:
            pass
    try:
        cur.execute("DELETE FROM e_signatures WHERE record_table='ebr_ejecuciones' AND record_id=?",
                    (str(ebr_id),))
    except Exception:
        pass
    cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (ebr_id,))
    conn.commit()
    return jsonify({"ok": True, "eliminado": True, "id": ebr_id})


# ════════════════════════════════════════════════════════════════════════════
# Materiales de envase MANUALES del legajo (Sebastián 11-jun) · elegir/agregar/editar
# desde el desplegable de TODOS los envases (maestro_mee). Tabla aparte
# (ebr_envase_materiales) · no toca el envasado real ni la inmutabilidad del EBR.
# ════════════════════════════════════════════════════════════════════════════
@bp.route("/api/brd/envase-opciones", methods=["GET"])
def brd_envase_opciones():
    """Catálogo de TODOS los materiales de envase (maestro_mee) para el desplegable del
    legajo. Solo lectura. ?q= filtra por código/descripción."""
    err = _require_login()
    if err:
        return err
    conn = get_db(); cur = conn.cursor()
    try:
        rows = cur.execute(
            "SELECT codigo, COALESCE(descripcion,'') FROM maestro_mee ORDER BY codigo").fetchall()
    except Exception:
        rows = []
    out = [{"codigo": r[0], "descripcion": r[1],
            "label": (str(r[0]) + (" · " + r[1] if r[1] else ""))} for r in rows if r[0]]
    q = (request.args.get("q") or "").strip().upper()
    if q:
        out = [o for o in out if q in (o["label"] or "").upper()]
    return jsonify({"ok": True, "opciones": out})


def _ebr_estado_lote(cur, ebr_id):
    r = cur.execute(
        "SELECT estado, COALESCE(lote_codigo, lote, '') AS lote FROM ebr_ejecuciones WHERE id=?",
        (ebr_id,)).fetchone()
    return r


@bp.route("/api/brd/ebr/<int:ebr_id>/material-envase", methods=["POST"])
def brd_material_envase_upsert(ebr_id):
    """Agrega o EDITA a mano un material de envase del legajo (elegido del desplegable de
    maestro_mee). Bloqueado si el lote está liberado/rechazado (inmutable · Part 11)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    cod = (body.get("material_codigo") or "").strip()
    if not cod:
        return jsonify({"error": "Elegí un material de envase del desplegable"}), 400
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable) · no se edita"}), 409

    def _num(k):
        v = body.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except Exception:
            return None

    nom = (body.get("material_nombre") or "").strip()
    if not nom:
        try:
            r = cur.execute("SELECT COALESCE(descripcion,'') FROM maestro_mee WHERE codigo=?",
                            (cod,)).fetchone()
            nom = (r[0] if r else "") or ""
        except Exception:
            nom = ""
    requerida = _num("requerida") or 0
    lote_mat = (body.get("lote_material") or "").strip()
    lote_env = (body.get("lote_envasado") or ebr["lote"] or "").strip()
    row_id = body.get("id")
    if row_id:
        cur.execute(
            "UPDATE ebr_envase_materiales SET material_codigo=?, material_nombre=?, "
            "lote_material=?, requerida=?, devuelta=?, utilizada=?, averiada=?, lote_envasado=? "
            "WHERE id=? AND ebr_id=?",
            (cod, nom, lote_mat, requerida, _num("devuelta"), _num("utilizada"),
             _num("averiada"), lote_env, int(row_id), ebr_id))
        if cur.rowcount != 1:
            return jsonify({"error": "fila no encontrada"}), 404
        nuevo_id = int(row_id); accion = "EDITAR_MATERIAL_ENVASE_EBR"
    else:
        cur.execute(
            "INSERT INTO ebr_envase_materiales (ebr_id, lote_envasado, material_codigo, "
            "material_nombre, lote_material, requerida, devuelta, utilizada, averiada, creado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ebr_id, lote_env, cod, nom, lote_mat, requerida, _num("devuelta"),
             _num("utilizada"), _num("averiada"), user))
        nuevo_id = cur.lastrowid; accion = "AGREGAR_MATERIAL_ENVASE_EBR"
    audit_log(cur, usuario=user, accion=accion, tabla="ebr_envase_materiales",
              registro_id=nuevo_id, despues={"material": cod, "requerida": requerida})
    conn.commit()
    return jsonify({"ok": True, "id": nuevo_id})


@bp.route("/api/brd/ebr/<int:ebr_id>/material-envase/<int:row_id>", methods=["DELETE"])
def brd_material_envase_delete(ebr_id, row_id):
    """Elimina una fila de material de envase agregada a mano (no toca las auto-cargadas
    del plan, que no tienen id). Bloqueado si el lote está liberado/rechazado."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable)"}), 409
    cur.execute("DELETE FROM ebr_envase_materiales WHERE id=? AND ebr_id=?", (row_id, ebr_id))
    if cur.rowcount != 1:
        return jsonify({"error": "fila no encontrada"}), 404
    audit_log(cur, usuario=user, accion="ELIMINAR_MATERIAL_ENVASE_EBR",
              tabla="ebr_envase_materiales", registro_id=row_id)
    conn.commit()
    return jsonify({"ok": True, "eliminado": True})


def _materiales_envase_manuales(conn, ebr_id):
    """Filas de material de envase agregadas/editadas a mano (ebr_envase_materiales).
    Tienen `id` y `fuente='manual'` → la UI permite editarlas/borrarlas."""
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, lote_envasado, material_codigo, material_nombre, lote_material, "
            "requerida, devuelta, utilizada, averiada FROM ebr_envase_materiales "
            "WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        req = r["requerida"]; dev = r["devuelta"]; uti = r["utilizada"]
        dif = None
        if req is not None and uti is not None:
            dif = round(float(req) - float(uti), 2)
        nom = r["material_nombre"] or ""
        out.append({
            "id": r["id"], "fuente": "manual",
            "lote_envasado": r["lote_envasado"] or "", "lote_acond": r["lote_envasado"] or "",
            "material": (r["material_codigo"] + (" " + nom if nom else "")),
            "material_codigo": r["material_codigo"], "material_nombre": nom,
            "lote_material": r["lote_material"] or "",
            "requerida": req, "devuelta": dev, "utilizada": uti,
            "averiada": r["averiada"], "diferencia": dif,
        })
    return out


# ── Presentaciones MANUALES del legajo (gemelo de los materiales · 11-jun) ──────
@bp.route("/api/brd/ebr/<int:ebr_id>/presentacion", methods=["POST"])
def brd_presentacion_upsert(ebr_id):
    """Agrega o EDITA a mano una presentación del legajo (por si no cargó del plan).
    Bloqueado si el lote está liberado/rechazado (inmutable · Part 11)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    pres = (body.get("presentacion") or "").strip()
    if not pres:
        return jsonify({"error": "Indicá la presentación (ej. 30 ml)"}), 400
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable) · no se edita"}), 409

    def _num(k):
        v = body.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except Exception:
            return None

    cliente = (body.get("cliente") or "Animus DTC").strip()
    envase = (body.get("envase_codigo") or "").strip()
    area = (body.get("area") or "").strip()
    lote = (body.get("lote") or ebr["lote"] or "").strip()
    vol = _num("volumen_ml"); uds = _num("unidades")
    row_id = body.get("id")
    if row_id:
        cur.execute(
            "UPDATE ebr_presentaciones_manual SET presentacion=?, cliente=?, volumen_ml=?, "
            "envase_codigo=?, unidades=?, area=?, lote=? WHERE id=? AND ebr_id=?",
            (pres, cliente, vol, envase, uds, area, lote, int(row_id), ebr_id))
        if cur.rowcount != 1:
            return jsonify({"error": "fila no encontrada"}), 404
        nuevo_id = int(row_id); accion = "EDITAR_PRESENTACION_EBR"
    else:
        cur.execute(
            "INSERT INTO ebr_presentaciones_manual (ebr_id, presentacion, cliente, volumen_ml, "
            "envase_codigo, unidades, area, lote, creado_por) VALUES (?,?,?,?,?,?,?,?,?)",
            (ebr_id, pres, cliente, vol, envase, uds, area, lote, user))
        nuevo_id = cur.lastrowid; accion = "AGREGAR_PRESENTACION_EBR"
    audit_log(cur, usuario=user, accion=accion, tabla="ebr_presentaciones_manual",
              registro_id=nuevo_id, despues={"presentacion": pres, "unidades": uds, "cliente": cliente})
    conn.commit()
    return jsonify({"ok": True, "id": nuevo_id})


@bp.route("/api/brd/ebr/<int:ebr_id>/presentacion/<int:row_id>", methods=["DELETE"])
def brd_presentacion_delete(ebr_id, row_id):
    """Elimina una presentación agregada a mano (no toca las auto-cargadas del plan)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable)"}), 409
    cur.execute("DELETE FROM ebr_presentaciones_manual WHERE id=? AND ebr_id=?", (row_id, ebr_id))
    if cur.rowcount != 1:
        return jsonify({"error": "fila no encontrada"}), 404
    audit_log(cur, usuario=user, accion="ELIMINAR_PRESENTACION_EBR",
              tabla="ebr_presentaciones_manual", registro_id=row_id)
    conn.commit()
    return jsonify({"ok": True, "eliminado": True})


def _presentaciones_manuales(conn, ebr_id):
    """Presentaciones agregadas/editadas a mano (ebr_presentaciones_manual). Tienen `id`
    y `fuente='manual'` → la UI permite editarlas/borrarlas. Estado 'Programado (manual)'."""
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, presentacion, cliente, volumen_ml, envase_codigo, unidades, area, lote "
            "FROM ebr_presentaciones_manual WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        uds = r["unidades"]; ml = r["volumen_ml"]
        out.append({
            "id": r["id"], "fuente": "manual",
            "presentacion": r["presentacion"] or "—", "cliente": r["cliente"] or "Animus DTC",
            "lote": r["lote"] or "", "unidades": uds, "area": r["area"] or "",
            "envase_codigo": r["envase_codigo"] or "", "volumen_ml": ml,
            "cantidad_ml": (uds * ml) if (uds and ml) else None,
            "unidades_final": None, "rend_pct": None, "estado": "Programado (manual)",
        })
    return out


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

    if body.get("no_aplica"):
        # "No aplica" (conforme=2): el control no corresponde a este producto.
        # No bloquea la liberación y NO abre desviación.
        conforme = 2
        valor_f = None
        valor_texto = valor_texto or "No aplica"
    elif spec["valor_min"] is not None or spec["valor_max"] is not None:
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


@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-estandar", methods=["GET", "POST"])
def reportar_ipc_estandar(ebr_id):
    """GET: lista los 5 controles ESTÁNDAR con su resultado (para el legajo).
    POST: registra/actualiza uno. Soporta 'No aplica' (conforme=2). Upsert por
    (ebr_id, control_codigo). No abre desviación.

    Body POST: {control_codigo, control_nombre?, valor_texto?, conforme?(bool),
                no_aplica?(bool), observaciones?}
    """
    if request.method == "GET":
        if not session.get("compras_user"):
            return jsonify({"error": "No autorizado"}), 401
        cur = get_db().cursor()
        est = {}
        try:
            for er in cur.execute(
                """SELECT control_codigo, COALESCE(valor_texto,''), conforme,
                          COALESCE(observaciones,''), COALESCE(medido_por,''),
                          COALESCE(medido_at_utc,'')
                   FROM ipc_estandar_resultados WHERE ebr_id=?""",
                (ebr_id,),
            ).fetchall():
                est[er[0]] = er
        except Exception:
            est = {}
        items = []
        for cod, nom, uni in IPC_ESTANDAR:
            er = est.get(cod)
            items.append({
                "control_codigo": cod, "control_nombre": nom, "unidad": uni,
                "valor_texto": (er[1] if er else ""),
                "conforme": (int(er[2]) if er and er[2] is not None else None),
                "observaciones": (er[3] if er else ""),
                "medido_por": (er[4] if er else ""),
                "medido_at_utc": (er[5] if er else ""),
            })
        return jsonify({"items": items})
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    cod = (body.get("control_codigo") or "").strip().lower()
    validos = {c[0]: c[1] for c in IPC_ESTANDAR}
    if cod not in validos:
        return jsonify({"error": "control_codigo inválido"}), 400
    nombre = (body.get("control_nombre") or validos[cod]).strip()[:120]
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    valor_texto = (body.get("valor_texto") or "").strip()[:200]
    obs = (body.get("observaciones") or "").strip()[:300]
    if body.get("no_aplica"):
        conforme = 2
        valor_texto = valor_texto or "No aplica"
    else:
        conf = body.get("conforme")
        conforme = (1 if conf else 0) if conf is not None else None
    user = session.get("compras_user", "")
    # Upsert por (ebr_id, control_codigo): borra el previo y reinserta.
    cur.execute(
        "DELETE FROM ipc_estandar_resultados WHERE ebr_id=? AND control_codigo=?",
        (ebr_id, cod),
    )
    cur.execute(
        """INSERT INTO ipc_estandar_resultados
             (ebr_id, control_codigo, control_nombre, valor_texto, conforme,
              observaciones, medido_por, medido_at_utc)
           VALUES (?,?,?,?,?,?,?, datetime('now','utc'))""",
        (ebr_id, cod, nombre, valor_texto, conforme, obs, user),
    )
    rid = cur.lastrowid
    try:
        audit_log(cur, usuario=user, accion='IPC_ESTANDAR_REGISTRAR',
                  tabla='ipc_estandar_resultados', registro_id=rid,
                  despues={'ebr_id': ebr_id, 'control': cod, 'conforme': conforme,
                           'valor': valor_texto})
    except Exception:
        pass
    conn.commit()
    estado_txt = {1: 'Cumple', 0: 'No cumple', 2: 'No aplica'}.get(conforme, 'pendiente')
    return jsonify({"ok": True, "id": rid, "conforme": conforme, "estado": estado_txt})


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
        "SELECT p.material_id, p.material_nombre, p.cantidad_teorica_g, p.cantidad_real_g, "
        "p.delta_g, p.delta_pct, p.lote_mp, p.pesado_por, p.verificado_por, p.verificado_at_utc, "
        "COALESCE(mm.nombre_inci,'') AS nombre_inci "
        "FROM ebr_pesajes p LEFT JOIN maestro_mps mm ON mm.codigo_mp=p.material_id "
        "WHERE p.ebr_id=? ORDER BY p.id", ebr_id)
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

    # Despeje GRANULAR por ítem (13 verificaciones × 2 etapas · Realizó/Verificó · MyBatch §2/§4 · 25-jun)
    def _despeje_items_pdf(etapa):
        reg = {}
        for dr in _q("SELECT item_idx, cumple, COALESCE(registrado_por,''), "
                     "COALESCE(verificado_por,'') FROM ebr_despeje_items "
                     "WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=?", ebr_id, etapa):
            reg[int(dr[0])] = dr
        out = []
        for i, texto in enumerate(DESPEJE_LINEA_ITEMS):
            r = reg.get(i)
            out.append((texto, (int(r[1]) if r and r[1] is not None else None),
                        (r[2] if r else ''), (r[3] if r else '')))
        return out
    despeje_gran = [("Dispensación", _despeje_items_pdf("dispensacion")),
                    ("Fabricación", _despeje_items_pdf("fabricacion"))]

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

    # Header · banda de marca violeta (premium · consistente con los rótulos HTML)
    pdf.set_fill_color(109, 40, 217)            # violeta de marca ANIMUS
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, _safe_pdf("ESPAGIRIA Laboratorio SAS  ·  ANIMUS Lab"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_fill_color(245, 243, 255)           # pale violeta
    pdf.set_text_color(76, 29, 149)             # violeta oscuro
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, _safe_pdf(f"Executed Batch Record  ·  Lote {ebr['lote']}"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_text_color(60, 60, 67)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe_pdf(
        f"Producto: {mbr['producto_nombre']}  ·  MBR v{ebr['mbr_version']}  ·  Estado: {ebr['estado'].upper()}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
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
            # UI por INCI (regulado · INCI + comercial para trazabilidad)
            _nm = w['nombre_inci'] or w['material_nombre'] or ''
            if w['nombre_inci'] and w['material_nombre'] and w['nombre_inci'] != w['material_nombre']:
                _nm = f"{w['nombre_inci']} ({w['material_nombre']})"
            _line(
                f"{w['material_id']} {_nm}: teórico "
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

    # Despeje granular · 13 verificaciones × 2 etapas (MyBatch §2 Dispensación + §4 Fabricación)
    for _et_nom, _et_items in despeje_gran:
        if any(it[1] is not None for it in _et_items):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, _safe_pdf(f"Despeje de Línea · {_et_nom} (Realizó / Verificó)"),
                     new_x="LMARGIN", new_y="NEXT")
            for texto, cumple, reg_por, ver_por in _et_items:
                _est = "SI" if cumple == 1 else ("NO" if cumple == 0 else "-")
                _line(f"[{_est}] {texto}", h=4, font_size=8)
                _line(f"      Realizo: {reg_por or '-'}  |  Verifico: {ver_por or '-'}",
                      h=4, font_size=7)
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
        """SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                  COALESCE(mm.nombre_inci,'') AS nombre_inci
           FROM formula_items fi LEFT JOIN maestro_mps mm ON mm.codigo_mp=fi.material_id
           WHERE fi.producto_nombre = ?""",
        (producto_nombre,),
    ).fetchall()
    teoricos = {}
    for r in rows:
        teoricos[r["material_id"]] = {
            "material_id": r["material_id"],
            "material_nombre": r["material_nombre"] or "",
            "nombre_inci": r["nombre_inci"] or "",
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
    if not signature_id and _ebr_mode_now(cur) != "off":
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


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes-plan", methods=["GET"])
def pesajes_plan_ebr(ebr_id):
    """Lista COMPLETA de MP a dispensar (teóricos de la fórmula) + estado de pesaje de cada una.
    Sección 3 'Dispensado de MP' (MyBatch §3): muestra QUÉ pesar ANTES de pesarlo (no solo lo ya
    pesado). Los teóricos se calculan de formula_items × tamaño de lote (no se crean filas en BD)."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    ebr = conn.execute(
        "SELECT mbr_template_id, COALESCE(cantidad_objetivo_g,0) AS objetivo "
        "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"items": []})
    producto = ""
    lote_size = ebr["objetivo"] or 0
    try:
        mb = conn.execute("SELECT producto_nombre, COALESCE(lote_size_g,0) FROM mbr_templates WHERE id=?",
                          (ebr["mbr_template_id"],)).fetchone()
        if mb:
            producto = mb[0] or ""
            if not lote_size:
                lote_size = mb[1] or 0
    except Exception:
        pass
    teoricos = _calcular_teoricos_mp(conn, producto, lote_size)
    pesados = {}
    try:
        for p in conn.execute(
            "SELECT id, material_id, material_nombre, cantidad_teorica_g, cantidad_real_g, "
            "COALESCE(lote_mp,'') AS lote_mp, COALESCE(pesado_por,'') AS pesado_por, "
            "COALESCE(verificado_por,'') AS verificado_por FROM ebr_pesajes WHERE ebr_id=?",
            (ebr_id,)).fetchall():
            pesados[p["material_id"]] = dict(p)
    except Exception:
        pesados = {}
    items = []
    for mid, t in teoricos.items():
        pp = pesados.get(mid)
        items.append({
            "material_id": mid,
            "material_nombre": t["material_nombre"] or mid,
            "porcentaje": t["porcentaje"],
            "cantidad_teorica_g": round(t["cantidad_teorica_g"], 3),
            "id": (pp["id"] if pp else None),
            "cantidad_real_g": (pp["cantidad_real_g"] if pp else None),
            "lote_mp": (pp["lote_mp"] if pp else ""),
            "pesado_por": (pp["pesado_por"] if pp else ""),
            "verificado_por": (pp["verificado_por"] if pp else ""),
        })
    for mid, pp in pesados.items():
        if mid not in teoricos:
            items.append({
                "material_id": mid, "material_nombre": pp.get("material_nombre") or mid,
                "porcentaje": None, "cantidad_teorica_g": pp.get("cantidad_teorica_g"),
                "id": pp["id"], "cantidad_real_g": pp.get("cantidad_real_g"),
                "lote_mp": pp.get("lote_mp", ""), "pesado_por": pp.get("pesado_por", ""),
                "verificado_por": pp.get("verificado_por", ""),
            })
    items.sort(key=lambda x: -((x["porcentaje"] or 0)))
    return jsonify({"items": items, "producto": producto, "lote_size_g": lote_size})


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


# ── ENVASADO Fase 3 (Sebastián 26-jun) · captura de unidades por presentación + descuento de envases ──
# Modelo: las presentaciones (15/30/50ml) salen de producto_presentaciones (envase/tapa/caja · MISMA
# fuente que la compra → compra==descuento · M55/M56). El operario entra UNIDADES por presentación; al
# CERRAR se descuenta envase+tapa+caja × unidades de movimientos_mee (canónico M26) UNA sola vez (CAS).
@bp.route("/api/brd/ebr/<int:ebr_id>/envases-plan", methods=["GET"])
def envases_plan_ebr(ebr_id):
    """Plan de envasado · SOLO lectura: presentaciones del producto + unidades ya registradas."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    erow = conn.execute(
        "SELECT COALESCE(m.producto_nombre,''), COALESCE(e.lote_codigo, e.lote), "
        "COALESCE(e.fase,'fabricacion'), COALESCE(e.envases_descontados_at,'') "
        "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?",
        (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    producto = erow[0] or ""
    reg = {}
    try:
        for r in conn.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(unidades,0), COALESCE(registrado_por,'') "
            "FROM ebr_envasado_unidades WHERE ebr_id=?", (ebr_id,)).fetchall():
            reg[r[0]] = {"unidades": r[1], "registrado_por": r[2]}
    except Exception:
        pass
    items = []
    try:
        for p in conn.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
            "COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), COALESCE(caja_codigo,'') "
            "FROM producto_presentaciones "
            "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1 "
            "ORDER BY volumen_ml", (producto,)).fetchall():
            pc = p[0]
            items.append({
                "presentacion_codigo": pc, "etiqueta": p[1], "volumen_ml": p[2],
                "envase_codigo": p[3], "tapa_codigo": p[4], "caja_codigo": p[5],
                "unidades": reg.get(pc, {}).get("unidades", 0),
                "registrado_por": reg.get(pc, {}).get("registrado_por", ""),
            })
    except Exception as _e:
        log.warning("envases-plan fallo: %s", _e)
    return jsonify({"ok": True, "producto": producto, "lote": erow[1],
                    "descontado": bool((erow[3] or "").strip()), "items": items})


@bp.route("/api/brd/ebr/<int:ebr_id>/registrar-unidades", methods=["POST"])
def registrar_unidades_envasado(ebr_id):
    """Guarda las unidades envasadas de una presentación (operario/ejecutor)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    pc = (body.get("presentacion_codigo") or "").strip()
    if not pc:
        return jsonify({"error": "presentacion_codigo requerido"}), 400
    try:
        unidades = float(body.get("unidades") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "unidades inválida"}), 400
    if unidades < 0:
        return jsonify({"error": "unidades no puede ser negativa"}), 400
    conn = get_db(); cur = conn.cursor()
    drow = cur.execute("SELECT COALESCE(envases_descontados_at,'') FROM ebr_ejecuciones WHERE id=?",
                       (ebr_id,)).fetchone()
    if drow and (drow[0] or "").strip():
        return jsonify({"error": "el envasado ya se cerró/descontó · no editable", "codigo": "YA_CERRADO"}), 409
    try:
        volumen = float(body.get("volumen_ml") or 0)
    except (TypeError, ValueError):
        volumen = 0
    cur.execute(
        "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, volumen_ml, "
        "unidades, registrado_por, registrado_at_utc) VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc')) "
        "ON CONFLICT(ebr_id, presentacion_codigo) DO UPDATE SET unidades=excluded.unidades, "
        "etiqueta=excluded.etiqueta, volumen_ml=excluded.volumen_ml, "
        "registrado_por=excluded.registrado_por, registrado_at_utc=excluded.registrado_at_utc",
        (ebr_id, pc, (body.get("etiqueta") or "").strip(), volumen, unidades, user))
    audit_log(cur, usuario=user, accion="REGISTRAR_UNIDADES_ENVASADO",
              tabla="ebr_envasado_unidades", registro_id=ebr_id,
              despues={"presentacion": pc, "unidades": unidades})
    conn.commit()
    return jsonify({"ok": True, "presentacion_codigo": pc, "unidades": unidades})


@bp.route("/api/brd/ebr/<int:ebr_id>/cerrar-envasado", methods=["POST"])
def cerrar_envasado_ebr(ebr_id):
    """Cierra el envasado: descuenta envase+tapa+caja × unidades (movimientos_mee) UNA vez (CAS) y marca
    completado. Reversa segura: si el descuento falla, rollback (no queda marcado) y se puede reintentar."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    erow = cur.execute(
        "SELECT COALESCE(m.producto_nombre,''), COALESCE(e.lote_codigo, e.lote), COALESCE(e.fase,'fabricacion') "
        "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?",
        (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(erow[2]).strip().lower() != "envasado":
        return jsonify({"error": "este cierre es solo para legajos de envasado"}), 400
    producto = erow[0] or ""
    lote = erow[1] or ""
    uds = {}
    for r in cur.execute(
        "SELECT COALESCE(presentacion_codigo,''), COALESCE(unidades,0) FROM ebr_envasado_unidades "
        "WHERE ebr_id=?", (ebr_id,)).fetchall():
        if (r[1] or 0) > 0:
            uds[r[0]] = r[1]
    if not uds:
        return jsonify({"error": "registrá las unidades envasadas (al menos una presentación) antes de cerrar"}), 400
    # CAS idempotente: reclamar el descuento — solo 1 vez y solo si está en proceso (race multi-worker · M27)
    cur.execute(
        "UPDATE ebr_ejecuciones SET envases_descontados_at=datetime('now','utc'), estado='completado', "
        "completado_at_utc=datetime('now','utc') "
        "WHERE id=? AND COALESCE(fase,'')='envasado' AND COALESCE(envases_descontados_at,'')='' "
        "AND estado IN ('iniciado','en_proceso')", (ebr_id,))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El envasado ya se cerró/descontó o no está en proceso · refrescá",
                        "codigo": "YA_CERRADO"}), 409
    descuentos = []
    try:
        for p in cur.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), "
            "COALESCE(caja_codigo,'') FROM producto_presentaciones "
            "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1", (producto,)).fetchall():
            n = uds.get(p[0], 0)
            if n <= 0:
                continue
            for cod, etq in ((p[1], "envase"), (p[2], "tapa"), (p[3], "caja")):
                cod = (cod or "").strip()
                if not cod:
                    continue
                cur.execute(
                    "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, observaciones, responsable, fecha) "
                    "VALUES (?, 'Salida', ?, ?, ?, datetime('now','utc'))",
                    (cod, n, "Envasado EBR-" + str(ebr_id) + " lote " + lote + " · " + etq + " " + p[0], user))
                descuentos.append({"mee_codigo": cod, "tipo": etq, "cantidad": n, "presentacion": p[0]})
    except Exception as _e:
        conn.rollback()
        log.warning("cerrar-envasado descuento MEE fallo (rollback): %s", _e)
        return jsonify({"error": "falló el descuento de envases · reintentá", "detalle": str(_e)}), 500
    conn.commit()
    audit_log(None, usuario=user, accion="CERRAR_ENVASADO_DESCONTAR_MEE",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"lote": lote, "descuentos": descuentos})
    # CADENA OF→OA (27-jun · Sebastián) · al CERRAR el envasado se HABILITA automático el legajo de
    # ACONDICIONAMIENTO del mismo lote físico (idempotente vía crear_ebr_desde_mbr · best-effort · NO
    # bloquea el cierre si falla). Espeja el hook fabricación→envasado de liberar_ebr. Así OF→OA deja de
    # ser manual/silencioso (hueco #1): el operario ve el siguiente paso al terminar el envasado.
    _acond_habilitado = None
    try:
        if producto and lote:
            _res_oa = crear_ebr_desde_mbr(conn.cursor(), producto_nombre=producto,
                                          lote=lote, usuario=user, fase='acondicionamiento')
            conn.commit()
            if _res_oa.get('ok'):
                _acond_habilitado = _res_oa.get('id')
                if not _res_oa.get('reusado'):
                    audit_log(None, usuario=user, accion="AUTO_CREAR_EBR_ACONDICIONAMIENTO",
                              tabla="ebr_ejecuciones", registro_id=_res_oa.get('id'),
                              despues={"origen_envasado_ebr": ebr_id, "lote": lote})
    except Exception as _e2:
        log.warning("auto-crear EBR acondicionamiento al cerrar envasado fallo (no bloquea): %s", _e2)
    return jsonify({"ok": True, "estado": "completado", "descuentos": descuentos,
                    "n_descuentos": len(descuentos), "acond_ebr_id": _acond_habilitado})


# ── ACONDICIONAMIENTO · cierre canónico (27-jun · Sebastián · hueco #2) ──────────────────────────────
# El operario lista los materiales de acondicionamiento consumidos (etiquetas/estuches/insertos · código +
# cantidad); al CERRAR se descuentan vía movimientos_mee (canónico M26 · NUNCA el cache stock_actual) UNA
# sola vez (CAS · M27). Reemplaza el descuento de la ruta legacy /api/acondicionamiento (que tocaba el cache
# sin CAS → drift + doble descuento). Reusa la marca envases_descontados_at como "materiales descontados".
@bp.route("/api/brd/ebr/<int:ebr_id>/cerrar-acondicionamiento", methods=["POST"])
def cerrar_acondicionamiento_ebr(ebr_id):
    """Cierra el acondicionamiento: descuenta los materiales listados × cantidad (movimientos_mee) UNA vez
    (CAS) y marca completado. Body: {materiales:[{codigo, cantidad}]}. Reversa segura: si el descuento falla,
    rollback (no queda marcado) y se puede reintentar."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    conn = get_db(); cur = conn.cursor()
    erow = cur.execute(
        "SELECT COALESCE(e.lote_codigo, e.lote), COALESCE(e.fase,'fabricacion') "
        "FROM ebr_ejecuciones e WHERE e.id=?", (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(erow[1]).strip().lower() != "acondicionamiento":
        return jsonify({"error": "este cierre es solo para legajos de acondicionamiento"}), 400
    lote = erow[0] or ""
    items = []
    for it in (body.get("materiales") or []):
        cod = str((it or {}).get("codigo") or (it or {}).get("mee_codigo") or "").strip()
        try:
            cant = float((it or {}).get("cantidad") or 0)
        except (TypeError, ValueError):
            cant = 0
        if cod and cant > 0:
            items.append((cod, cant))
    if not items:
        return jsonify({"error": "listá al menos un material consumido (código + cantidad) antes de cerrar"}), 400
    # CAS idempotente (M27): reclamar el cierre — solo 1 vez y solo si está en proceso (race multi-worker).
    cur.execute(
        "UPDATE ebr_ejecuciones SET envases_descontados_at=datetime('now','utc'), estado='completado', "
        "completado_at_utc=datetime('now','utc') "
        "WHERE id=? AND COALESCE(fase,'')='acondicionamiento' AND COALESCE(envases_descontados_at,'')='' "
        "AND estado IN ('iniciado','en_proceso')", (ebr_id,))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El acondicionamiento ya se cerró/descontó o no está en proceso · refrescá",
                        "codigo": "YA_CERRADO"}), 409
    descuentos = []
    try:
        for cod, cant in items:
            cur.execute(
                "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, observaciones, responsable, fecha) "
                "VALUES (?, 'Salida', ?, ?, ?, datetime('now','utc'))",
                (cod, cant, "Acondicionamiento EBR-" + str(ebr_id) + " lote " + lote, user))
            descuentos.append({"mee_codigo": cod, "cantidad": cant})
    except Exception as _e:
        conn.rollback()
        log.warning("cerrar-acondicionamiento descuento MEE fallo (rollback): %s", _e)
        return jsonify({"error": "falló el descuento de materiales · reintentá", "detalle": str(_e)}), 500
    conn.commit()
    audit_log(None, usuario=user, accion="CERRAR_ACONDICIONAMIENTO_DESCONTAR_MEE",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"lote": lote, "descuentos": descuentos})
    return jsonify({"ok": True, "estado": "completado", "descuentos": descuentos,
                    "n_descuentos": len(descuentos)})


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


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-items", methods=["GET"])
def listar_despeje_items_ebr(ebr_id):
    """Checklist granular de despeje (13 ítems GMP estándar) por etapa: dispensacion + fabricacion
    (MyBatch secciones 2 y 4). Cada ítem: idx, texto, cumple (1/0/None), observaciones, registrado_por."""
    err = _require_login()
    if err:
        return err
    conn = get_db()

    def _chk(etapa):
        reg = {}
        try:
            for dr in conn.execute(
                "SELECT item_idx, cumple, COALESCE(observaciones,''), COALESCE(registrado_por,''), "
                "COALESCE(registrado_at_utc,''), COALESCE(verificado_por,''), COALESCE(verificado_at_utc,'') "
                "FROM ebr_despeje_items "
                "WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=?", (ebr_id, etapa)).fetchall():
                reg[int(dr[0])] = dr
        except Exception:
            reg = {}
        out = []
        for i, texto in enumerate(DESPEJE_LINEA_ITEMS):
            r = reg.get(i)
            out.append({'idx': i, 'texto': texto,
                        'cumple': (int(r[1]) if r and r[1] is not None else None),
                        'observaciones': (r[2] if r else ''),
                        'registrado_por': (r[3] if r else ''),
                        'registrado_at': (r[4] if r else ''),
                        'verificado_por': (r[5] if r and len(r) > 5 else ''),
                        'verificado_at': (r[6] if r and len(r) > 6 else '')})
        return out

    return jsonify({"dispensacion": _chk("dispensacion"), "fabricacion": _chk("fabricacion")})


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


# ── MyBatch ② detalle · Despeje de línea por ÍTEM (checklist 13 verificaciones) ──
@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-item", methods=["POST"])
def registrar_despeje_item_ebr(ebr_id):
    """Registra el CUMPLE (Sí/No) de UNA verificación del despeje de línea.
    Botón ✏️ de la tabla VERIFICACIÓN/CUMPLE/ACCIONES (MyBatch ② detalle)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        idx = int(body.get("item_idx"))
    except (TypeError, ValueError):
        return jsonify({"error": "item_idx inválido"}), 400
    if idx < 0 or idx >= len(DESPEJE_LINEA_ITEMS):
        return jsonify({"error": "item_idx fuera de rango"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    cumple = 1 if body.get("cumple") in (1, True, '1', 'true', 'on', 'si', 'Si', 'sí') else 0
    obs = (body.get("observaciones") or "").strip()[:500]
    etapa = (body.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    user = session.get("compras_user", "")
    texto = DESPEJE_LINEA_ITEMS[idx]
    # DOS ROLES (Sebastián 6-jun-2026): el despeje lo REGISTRA el operario; SOLO
    # Calidad/Dirección Técnica puede CORREGIR un resultado ya registrado (botón
    # "Corregir Resultado" de MyBatch). Trazabilidad INVIMA: queda en audit_log
    # quién registró y quién corrigió.
    prev = cur.execute(
        "SELECT cumple, COALESCE(observaciones,''), COALESCE(registrado_por,'') "
        "FROM ebr_despeje_items WHERE ebr_id=? AND item_idx=? AND COALESCE(etapa,'dispensacion')=?",
        (ebr_id, idx, etapa)).fetchone()
    es_correccion = bool(prev and prev[0] is not None)
    # Corregir un resultado ya registrado = atribución de quien CORRIGE (Calidad / Aseguramiento /
    # Dir. Técnica / Admin · resolver canónico _batch_role_info, consistente con la sección Correcciones).
    es_calidad = bool(_batch_role_info(user).get("corrige"))
    if es_correccion and not es_calidad:
        return jsonify({
            "error": "Corregir un resultado ya registrado es atribución de Calidad / "
                     "Dirección Técnica. El operario solo registra el despeje inicial.",
            "codigo": "SOLO_CALIDAD_CORRIGE",
        }), 403
    # Upsert por (ebr_id, item_idx, etapa) · índice único de mig 222.
    cur.execute(
        """INSERT INTO ebr_despeje_items
             (ebr_id, item_idx, item_texto, cumple, observaciones,
              registrado_por, registrado_at_utc, etapa)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc'), ?)
           ON CONFLICT(ebr_id, item_idx, etapa) DO UPDATE SET
             cumple=excluded.cumple, observaciones=excluded.observaciones,
             registrado_por=excluded.registrado_por,
             registrado_at_utc=excluded.registrado_at_utc""",
        (ebr_id, idx, texto, cumple, obs, user, etapa))
    audit_log(cur, usuario=user,
              accion=("CORREGIR_DESPEJE_ITEM_EBR" if es_correccion else "REGISTRAR_DESPEJE_ITEM_EBR"),
              tabla="ebr_despeje_items", registro_id=ebr_id,
              antes=({"cumple": prev[0], "observaciones": prev[1], "registrado_por": prev[2]} if es_correccion else None),
              despues={"ebr_id": ebr_id, "item_idx": idx, "cumple": cumple, "por": user})
    conn.commit()
    return jsonify({"ok": True, "item_idx": idx, "cumple": cumple,
                    "correccion": es_correccion}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-verificar", methods=["POST"])
def verificar_despeje_item_ebr(ebr_id):
    """2ª firma de Calidad sobre el despeje (regla 2 personas · MyBatch · 25-jun).
    El operario marca CUMPLE (registrado_por); Calidad/Jefe de Producción VERIFICA después
    (verificado_por). body: {item_idx, etapa} verifica uno · {todos:true, etapa} verifica todos
    los cumple sin verificar. Solo verifica ítems ya marcados cumple=1 (no se verifica lo no hecho)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    etapa = (body.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("verifica"):
        return jsonify({"error": "Verificar el despeje es atribución de Calidad / Jefe de Producción / "
                                 "Dirección Técnica. El operario solo registra el despeje.",
                        "codigo": "SOLO_VERIFICA_DESPEJE"}), 403
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    # No autoverificación: quien verifica no puede ser quien registró (2 personas).
    if body.get("todos"):
        cur.execute(
            "UPDATE ebr_despeje_items SET verificado_por=?, verificado_at_utc=datetime('now','utc') "
            "WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=? AND cumple=1 "
            "AND COALESCE(verificado_por,'')='' AND COALESCE(registrado_por,'')<>?",
            (user, ebr_id, etapa, user))
        n = cur.rowcount
    else:
        try:
            idx = int(body.get("item_idx"))
        except (TypeError, ValueError):
            return jsonify({"error": "item_idx inválido"}), 400
        cur.execute(
            "UPDATE ebr_despeje_items SET verificado_por=?, verificado_at_utc=datetime('now','utc') "
            "WHERE ebr_id=? AND item_idx=? AND COALESCE(etapa,'dispensacion')=? AND cumple=1 "
            "AND COALESCE(verificado_por,'')='' AND COALESCE(registrado_por,'')<>?",
            (user, ebr_id, idx, etapa, user))
        n = cur.rowcount
    audit_log(cur, usuario=user, accion="VERIFICAR_DESPEJE_ITEM_EBR",
              tabla="ebr_despeje_items", registro_id=ebr_id,
              despues={"ebr_id": ebr_id, "etapa": etapa, "verificados": n, "por": user})
    conn.commit()
    return jsonify({"ok": True, "verificados": n}), 200


@bp.route("/api/brd/mi-trabajo", methods=["GET"])
def mi_trabajo_brd():
    """Bandeja por ROL (Nivel 2 · 25-jun): tareas pendientes del usuario en TODOS los legajos en curso.
    realiza (operario/jefe) → despeje por marcar + pasos por ejecutar · verifica (calidad) → despeje y
    pesajes por verificar. Una sola pantalla: cada quien ve SU cola de trabajo."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    rinfo = _batch_role_info(user)
    conn = get_db()

    def _ct(sql, *p):
        try:
            r = conn.execute(sql, p).fetchone()
            return int(r[0]) if r and r[0] is not None else 0
        except Exception:
            return 0

    ebrs = conn.execute(
        "SELECT id, COALESCE(numero_op,'') AS numero_op, COALESCE(lote_codigo,lote,'') AS lote, "
        "mbr_template_id, COALESCE(fase,'fabricacion') AS fase "
        "FROM ebr_ejecuciones WHERE estado IN ('iniciado','en_proceso') ORDER BY id DESC").fetchall()
    items = []
    n_items = len(DESPEJE_LINEA_ITEMS) * 2  # 13 × 2 etapas
    for e in ebrs:
        eid = e["id"]
        prod = ""
        try:
            mb = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?",
                              (e["mbr_template_id"],)).fetchone()
            prod = (mb[0] if mb else "")
        except Exception:
            prod = ""
        tareas = []
        if rinfo.get("realiza"):
            np = _ct("SELECT COUNT(*) FROM ebr_pasos_ejecutados WHERE ebr_id=? AND estado IN ('pendiente','en_proceso')", eid)
            if np:
                tareas.append({"tipo": "pasos", "n": np, "txt": f"{np} paso(s) por ejecutar"})
            marc = _ct("SELECT COUNT(*) FROM ebr_despeje_items WHERE ebr_id=? AND cumple IS NOT NULL", eid)
            dpend = n_items - marc
            if dpend > 0:
                tareas.append({"tipo": "despeje", "n": dpend, "txt": f"{dpend} verificación(es) de despeje por marcar"})
        if rinfo.get("verifica"):
            dv = _ct("SELECT COUNT(*) FROM ebr_despeje_items WHERE ebr_id=? AND cumple=1 AND COALESCE(verificado_por,'')=''", eid)
            if dv:
                tareas.append({"tipo": "verif_despeje", "n": dv, "txt": f"{dv} ítem(s) de despeje por verificar"})
            pv = _ct("SELECT COUNT(*) FROM ebr_pesajes WHERE ebr_id=? AND COALESCE(pesado_por,'')<>'' AND COALESCE(verificado_por,'')=''", eid)
            if pv:
                tareas.append({"tipo": "verif_pesaje", "n": pv, "txt": f"{pv} pesaje(s) por verificar"})
        if tareas:
            items.append({"ebr_id": eid, "numero_op": e["numero_op"], "lote": e["lote"],
                          "producto": prod, "fase": e["fase"], "tareas": tareas,
                          "total": sum(t["n"] for t in tareas)})
    return jsonify({"rol": rinfo, "items": items, "total_legajos": len(items)})


@bp.route("/api/brd/ebr/<int:ebr_id>/aprobar-dt", methods=["POST"])
def aprobar_dt_ebr(ebr_id):
    """3ª firma · Director Técnico: visto bueno final (responsable INVIMA), además de Producción +
    Calidad. Requiere e-firma (signature_id · meaning='aprueba_dt')."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("aprueba_dt"):
        return jsonify({"error": "El visto bueno final es atribución del Director Técnico.",
                        "codigo": "SOLO_DIRECTOR_TECNICO"}), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    if not signature_id:
        return jsonify({"error": "signature_id requerido · meaning='aprueba_dt' record_table='ebr_ejecuciones'"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado, COALESCE(aprobado_dt_por,'') FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if (ebr[1] or "").strip():
        return jsonify({"error": "Ya tiene visto bueno del Director Técnico"}), 409
    cur.execute("UPDATE ebr_ejecuciones SET aprobado_dt_por=?, aprobado_dt_at_utc=datetime('now','utc'), "
                "aprobado_dt_signature_id=? WHERE id=? AND COALESCE(aprobado_dt_por,'')=''",
                (user, signature_id, ebr_id))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "Ya aprobado o EBR cambió de estado"}), 409
    audit_log(cur, usuario=user, accion="APROBAR_DT_EBR", tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"aprobado_dt_por": user})
    conn.commit()
    return jsonify({"ok": True, "aprobado_dt_por": user}), 200


@bp.route("/api/brd/ebr/<int:ebr_id>/correcciones", methods=["GET"])
def listar_correcciones_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT COALESCE(campo_afectado,'') AS campo_afectado, COALESCE(motivo,'') AS motivo, "
            "COALESCE(descripcion,'') AS descripcion, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_correcciones "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/correcciones", methods=["POST"])
def agregar_correccion_ebr(ebr_id):
    """Registra una corrección/enmienda al registro (21 CFR Part 11): motivo + descripción + autor + fecha.
    Atribución de Calidad / Aseguramiento / Dirección Técnica."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("corrige"):
        return jsonify({"error": "Registrar una corrección es atribución de Calidad / Aseguramiento / "
                                 "Dirección Técnica.", "codigo": "SOLO_CALIDAD_CORRIGE"}), 403
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()[:500]
    desc = (body.get("descripcion") or "").strip()[:1000]
    campo = (body.get("campo_afectado") or "").strip()[:200]
    if not motivo and not desc:
        return jsonify({"error": "Indicá el motivo de la corrección"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO ebr_correcciones (ebr_id, campo_afectado, motivo, descripcion, registrado_por, "
                "registrado_at_utc, signature_id) VALUES (?, ?, ?, ?, ?, datetime('now','utc'), ?)",
                (ebr_id, campo, motivo, desc, user, body.get("signature_id")))
    audit_log(cur, usuario=user, accion="CORRECCION_EBR", tabla="ebr_correcciones", registro_id=ebr_id,
              despues={"motivo": motivo, "campo": campo, "por": user})
    conn.commit()
    return jsonify({"ok": True}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/ajustes-mp", methods=["GET"])
def listar_ajustes_mp_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT COALESCE(material,'') AS material, COALESCE(cantidad_g,0) AS cantidad_g, "
            "COALESCE(motivo,'') AS motivo, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_ajustes_mp "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/ajustes-mp", methods=["POST"])
def agregar_ajuste_mp_ebr(ebr_id):
    """Registra un ajuste de materia prima durante la fabricación (MyBatch §3 'Ajustes de MP' ·
    ej. + Trietanolamina para ajustar pH). Lo hace el operario que ejecuta."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    material = (body.get("material") or "").strip()[:200]
    motivo = (body.get("motivo") or "").strip()[:500]
    try:
        cant = float(str(body.get("cantidad_g") or 0).replace(",", "."))
    except (TypeError, ValueError):
        cant = 0.0
    if not material:
        return jsonify({"error": "Indicá la materia prima ajustada"}), 400
    user = session.get("compras_user", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO ebr_ajustes_mp (ebr_id, material, cantidad_g, motivo, registrado_por, "
                "registrado_at_utc) VALUES (?, ?, ?, ?, ?, datetime('now','utc'))",
                (ebr_id, material, cant, motivo, user))
    audit_log(cur, usuario=user, accion="AJUSTE_MP_EBR", tabla="ebr_ajustes_mp", registro_id=ebr_id,
              despues={"material": material, "cantidad_g": cant, "motivo": motivo, "por": user})
    conn.commit()
    return jsonify({"ok": True}), 201


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
        return jsonify({"error": "archivo inválido"}), 500
    # Detectar tipo por extensión del nombre (las fotos de rótulos son imágenes,
    # no PDF) y servir INLINE para verlo en el navegador (como el modal de MyBatch).
    nombre = (row["archivo_nombre"] or f"registro_{rid}").lower()
    if nombre.endswith(('.jpg', '.jpeg')):
        mime = "image/jpeg"
    elif nombre.endswith('.png'):
        mime = "image/png"
    elif nombre.endswith('.webp'):
        mime = "image/webp"
    elif nombre.endswith('.gif'):
        mime = "image/gif"
    elif nombre.endswith('.pdf'):
        mime = "application/pdf"
    else:
        # Sin extensión clara: inferir por los primeros bytes (magic number).
        if raw[:4] == b'%PDF':
            mime = "application/pdf"
        elif raw[:3] == b'\xff\xd8\xff':
            mime = "image/jpeg"
        elif raw[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        else:
            mime = "application/octet-stream"
    return send_file(_io.BytesIO(raw), mimetype=mime, as_attachment=False,
                     download_name=(row["archivo_nombre"] or f"registro_{rid}"))


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
                "nombre_inci": spec.get("nombre_inci", ""),
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
            "nombre_inci": spec.get("nombre_inci", ""),
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

    # 0) Fabricaciones EN CURSO (produccion_programada · inicio sin fin) → para mostrar Finalizar en la
    # orden. Si ya tienen legajo, se anota su produccion_id en la fila del legajo; si no, fila propia.
    _enp = {}
    if fase == "fabricacion":
        try:
            for r in conn.execute(
                "SELECT pp.id, COALESCE(pp.producto,''), COALESCE(pp.cantidad_kg,0), pp.inicio_real_at, "
                "COALESCE(o.nombre,'') FROM produccion_programada pp "
                "LEFT JOIN operarios_planta o ON o.id=pp.operario_elaboracion_id "
                "WHERE COALESCE(pp.inicio_real_at,'')<>'' AND COALESCE(pp.fin_real_at,'')='' "
                "AND LOWER(COALESCE(pp.estado,'')) NOT IN ('completado','cancelado')").fetchall():
                _enp[r[0]] = {'producto': r[1], 'kg': float(r[2] or 0),
                              'inicio': r[3], 'operador': r[4]}
        except Exception as _e:
            log.warning("ordenes-unificadas en-curso query fallo: %s", _e)

    # 1) Legajos EBR (ya MyBatch-shaped) · producto vía mbr_templates
    try:
        ebr_rows = conn.execute(
            """SELECT e.id, e.numero_op, e.produccion_id,
                      COALESCE(e.lote_codigo, e.lote) AS lote, e.estado,
                      e.cantidad_objetivo_g, e.cantidad_real_g,
                      COALESCE(e.ml_envasable, NULL) AS ml_envasable,
                      e.iniciado_at_utc, e.liberado_at_utc,
                      COALESCE(e.fase,'fabricacion') AS fase,
                      COALESCE(m.producto_nombre,'') AS producto
               FROM ebr_ejecuciones e
               LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id
               WHERE COALESCE(e.fase,'fabricacion') = ?
                 AND COALESCE(e.estado,'') != 'cancelado'
               ORDER BY e.iniciado_at_utc DESC""",
            (fase,),
        ).fetchall()
    except Exception as _e:
        log.warning("ordenes-unificadas EBR query fallo: %s", _e)
        ebr_rows = []
    _lotes_con_legajo = set()  # para no duplicar la fila simple si ya tiene EBR
    for r in ebr_rows:
        rd = dict(r)
        liberado = bool(rd.get("liberado_at_utc"))
        if rd.get("lote"):
            _lotes_con_legajo.add(str(rd["lote"]).strip())
        _ppid = rd.get("produccion_id")
        _en_curso = _ppid in _enp
        if _en_curso:
            _enp.pop(_ppid, None)  # se muestra como esta orden (con Finalizar)
        items.append({
            "origen": "legajo",
            "numero_op": rd.get("numero_op") or f"EBR-{rd['id']}",
            "lote_bulk": rd.get("lote") or "",
            "producto": rd.get("producto") or "",
            "teorica_g": rd.get("cantidad_objetivo_g"),
            "producida_g": rd.get("cantidad_real_g"),
            "aprobada": (rd.get("cantidad_real_g") if liberado else None),
            "ml_envasable": rd.get("ml_envasable"),
            "estado": ("En proceso" if _en_curso else _estado_orden_norm("legajo", rd.get("estado"))),
            "fecha": (rd.get("iniciado_at_utc") or "")[:10],
            "link": f"/planta/orden/{rd['id']}",
            "ebr_id": rd["id"],
            "produccion_id": (_ppid if _en_curso else None),
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
            # dedup: si esta producción YA tiene legajo (mismo lote), no la repetimos
            # como fila 'simple' · gana la fila LEGAJO (el legajo automático).
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
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

    # 2b) Registros simples de ENVASADO (tabla envasado · 9-jun) → la OF muestra las
    # órdenes de envasado CON su estado (como MyBatch), no solo legajos EBR. Agrupa por
    # lote+producto (la modal registra 1 fila por presentación · 1 orden por lote).
    if fase == "envasado":
        try:
            env_rows = conn.execute(
                """SELECT MIN(id) AS id, COALESCE(producto,'') AS producto,
                          COALESCE(lote,'') AS lote, MAX(COALESCE(estado,'Completado')) AS estado,
                          MAX(COALESCE(fecha,'')) AS fecha, MAX(COALESCE(operador,'')) AS operador,
                          SUM(COALESCE(unidades,0)) AS unidades
                   FROM envasado
                   GROUP BY producto, lote
                   ORDER BY id DESC LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas envasado query fallo: %s", _e)
            env_rows = []
        for r in env_rows:
            rd = dict(r)
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"ENV-{rd['id']:05d}",
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": None, "producida_g": None, "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # 2c) Registros simples de ACONDICIONAMIENTO (tabla acondicionamiento · 10-jun) →
    # la OA muestra las órdenes con su estado (como MyBatch), aunque aún no tengan
    # legajo EBR. Agrupa por lote+producto.
    if fase == "acondicionamiento":
        try:
            ac_rows = conn.execute(
                """SELECT MIN(id) AS id, COALESCE(producto,'') AS producto,
                          COALESCE(lote,'') AS lote, MAX(COALESCE(estado,'En proceso')) AS estado,
                          MAX(COALESCE(fecha,'')) AS fecha, MAX(COALESCE(operador,'')) AS operador,
                          SUM(COALESCE(unidades_producidas,0)) AS unidades
                   FROM acondicionamiento
                   GROUP BY producto, lote
                   ORDER BY id DESC LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas acondicionamiento query fallo: %s", _e)
            ac_rows = []
        for r in ac_rows:
            rd = dict(r)
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"ACOND-{rd['id']:05d}",
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": None, "producida_g": None, "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # en-curso SIN legajo (productos sin MBR aprobado) → fila propia "En proceso" con Finalizar
    for _pid, _v in _enp.items():
        items.append({
            "origen": "en_proceso",
            "numero_op": f"PROD-{_pid:05d}",
            "lote_bulk": "",
            "producto": _v['producto'],
            "teorica_g": round(_v['kg'] * 1000, 1),
            "producida_g": None, "aprobada": None, "ml_envasable": None,
            "estado": "En proceso",
            "fecha": (_v['inicio'] or "")[:10],
            "link": None,
            "produccion_id": _pid,
            "operador": _v['operador'],
        })
    # orden: en-curso PRIMERO, luego por fecha desc (sort estable)
    items.sort(key=lambda x: (x.get("fecha") or ""), reverse=True)
    items.sort(key=lambda x: 0 if (x.get("estado") or "").lower().startswith("en proceso") else 1)
    resumen = {
        "total": len(items),
        "legajos": sum(1 for i in items if i["origen"] == "legajo"),
        "simples": sum(1 for i in items if i["origen"] in ("simple", "en_proceso")),
        "en_proceso": sum(1 for i in items if i.get("produccion_id")),
    }
    return jsonify({"ok": True, "fase": fase, "resumen": resumen, "ordenes": items})


_ORDENES_PROD_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Órdenes de Producción · EOS</title>
<style>
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f4f4f7;color:#18181b;margin:0;padding:20px;-webkit-font-smoothing:antialiased}
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
<div style="margin-bottom:12px">
  <button onclick="crearLegajoRapido()" style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer">+ Nueva orden de esta fase</button>
  <span style="font-size:12px;color:#64748b;margin-left:8px">crea el legajo (requiere MBR aprobado del producto)</span>
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
var _FASE_ACTUAL='fabricacion';
async function crearLegajoRapido(){
  var f=_FASE_ACTUAL||'envasado';
  var fl=({fabricacion:'fabricación (OP)',envasado:'envasado (OF)',acondicionamiento:'acondicionamiento (OA)'})[f]||f;
  var prod=prompt('Producto para la orden de '+fl+' (nombre exacto):');
  if(!prod)return;
  var lote=prompt('N° de lote:');
  if(!lote)return;
  try{
    var r=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:lote,fase:f})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo crear el legajo: '+((d&&d.error)||r.status));return;}
    location.href=d.link||('/planta/orden/'+d.id);
  }catch(e){alert('Error de red: '+(e.message||e));}
}
async function ver(fase,btn){
  _FASE_ACTUAL=fase;
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  if(btn)btn.classList.add('active');
  var out=document.getElementById('out'); out.innerHTML='Cargando…';
  // Envasado se gestiona en UN solo lugar (Planta → Envasado) · este tab ya NO
  // duplica la lista · redirige al lugar canónico (9-jun · quitar redundancia).
  if(fase==='envasado'){
    document.getElementById('summary').innerHTML='';
    out.innerHTML='<div style="text-align:center;padding:34px 20px"><div style="font-size:34px;margin-bottom:8px">&#128230;</div><b style="font-size:15px;color:#6d28d9">Las Órdenes de Envasado viven en un solo lugar</b><br><span style="color:#64748b;font-size:13px">Planta &rarr; Envasado (la cola, el estado y el legajo) &middot; sin duplicados.</span><br><br><a href="/inventarios#envasado" style="display:inline-block;background:#7c3aed;color:#fff;padding:11px 24px;border-radius:9px;text-decoration:none;font-weight:700">Ir a Envasado &rarr;</a></div>';
    return;
  }
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


# ──────────────────────────────────────────────────────────────────────────
# Detalle de Orden de Producción · layout estilo MyBatch (Sebastián 4-jun-2026)
# Sub-pasos A+B: cabecera + 5 botones + tabla "Pesaje de Materias Primas".
# Reusa /api/brd/ebr/<id>/vista-completa (datos ya existentes). Aditivo.
# El Timeline cronológico queda como uno de los botones.
# ──────────────────────────────────────────────────────────────────────────

_ORDEN_DETALLE_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Producción · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<script>
/* Capturador de errores VISIBLE (6-jun-diag) · corre antes que todo. Si el
   script principal de la página falla al parsear/ejecutar, el error se pinta
   en pantalla (sin DevTools) para diagnosticar el "Cargando…" eterno. */
window.addEventListener('error',function(e){
  try{
    var m=document.getElementById('cxerr');
    if(!m){m=document.createElement('div');m.id='cxerr';
      m.style.cssText='background:#fee2e2;color:#991b1b;padding:12px 16px;margin:8px 0;border-radius:10px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;border:1px solid #fca5a5';
      (document.body||document.documentElement).insertBefore(m,(document.body||document.documentElement).firstChild);}
    m.textContent='⚠ ERROR JS (por esto no carga): '+(e.message||(e.error&&e.error.message)||'desconocido')+
      '\\n@ '+((e.filename||'').split('/').pop())+' línea '+e.lineno+':'+e.colno;
  }catch(_){}
},true);
window.addEventListener('unhandledrejection',function(e){
  try{
    var m=document.getElementById('cxerr');
    if(!m){m=document.createElement('div');m.id='cxerr';
      m.style.cssText='background:#fef3c7;color:#92400e;padding:12px 16px;margin:8px 0;border-radius:10px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;border:1px solid #fcd34d';
      (document.body||document.documentElement).insertBefore(m,(document.body||document.documentElement).firstChild);}
    var r=e&&e.reason; m.textContent='⚠ Promesa rechazada: '+((r&&r.message)||r||'?');
  }catch(_){}
});
</script>
<style>
/*__TOOLTIP_CSS__*/
*{box-sizing:border-box}
body{font-family:var(--cx-font);background:var(--cx-bg);color:var(--cx-text);margin:0;padding:24px}
.wrap{max-width:1150px;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:#fff;color:#7c3aed;font-size:13px;font-weight:700;text-decoration:none;padding:10px 18px;border-radius:11px;border:1px solid #e9d5ff;box-shadow:0 2px 10px rgba(124,58,237,.10);transition:all .14s ease}
a.back:hover{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border-color:transparent;box-shadow:0 6px 18px rgba(124,58,237,.30);transform:translateY(-1px)}
a.back .arw{font-size:15px;line-height:1}
.card{background:#fff;border-radius:16px;padding:0;box-shadow:0 4px 16px rgba(76,29,149,.07);margin-bottom:18px;overflow:hidden}
.card.pad{padding:22px}
#head{padding:0}
.hbar{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:22px 26px}
.hkicker{font-size:12px;font-weight:700;opacity:.85;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
h1{font-size:28px;margin:0;color:#fff;letter-spacing:.5px}
.prod{font-size:16px;color:#ede9fe;font-weight:600;margin-top:4px}
.estado-badge{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:800;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.12)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:18px;font-size:13px;padding:22px 26px}
.grid .lbl{color:#94a3b8;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}
.grid .val{color:#1e293b;margin-top:3px;font-weight:600;font-size:14px}
.liber-line{margin:0 26px 4px;padding:10px 14px;background:#dcfce7;color:#166534;border-radius:8px;font-size:13px;font-weight:600}
.btns{display:flex;gap:10px;flex-wrap:wrap;padding:6px 26px 24px}
.btns a,.btns button{border:1px solid transparent;border-radius:var(--cx-r-md);padding:11px 18px;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;transition:background var(--cx-tr-fast),color var(--cx-tr-fast),border-color var(--cx-tr-fast),box-shadow var(--cx-tr-fast),transform .06s}
.btns a:active,.btns button:active{transform:translateY(1px)}
/* Toolbar RESTRINGIDO (premium): los secundarios son ghost neutro · solo
   "Instrucción de Manufactura" (la acción de trabajo) lleva el acento violeta.
   Antes: 5 colores saturados (arcoíris) = el tell #1 de amateur. */
.b-time,.b-pdf,.b-rot,.b-aj{background:var(--cx-card);color:var(--cx-text-soft);border-color:var(--cx-border)}
.b-time:hover,.b-pdf:hover,.b-rot:hover,.b-aj:hover{border-color:var(--cx-primary-light);color:var(--cx-primary-dark);background:var(--cx-primary-pale)}
.b-mbr{background:var(--cx-primary);color:#fff}
.b-mbr:hover{background:var(--cx-primary-dark);box-shadow:var(--cx-sh-violet-sm)}
.b-soon{background:#e2e8f0;color:#94a3b8;cursor:not-allowed}
.b-mini{background:#14b8a6;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer}
.b-i{background:#0ea5e9;color:#fff;border:none;border-radius:7px;width:30px;height:30px;font-style:italic;font-weight:800;cursor:pointer}
.b-e{background:#f59e0b;color:#fff;border:none;border-radius:7px;width:30px;height:30px;cursor:pointer}
.b-pdf-sm{display:inline-flex;align-items:center;gap:5px;background:#ef4444;color:#fff;text-decoration:none;font-size:11px;font-weight:700;padding:4px 10px;border-radius:7px;margin-left:10px;vertical-align:middle}
.cxmodal{display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:99998;align-items:center;justify-content:center;padding:20px}
.cxbox{background:var(--cx-card);border-radius:var(--cx-r-lg);max-width:560px;width:100%;box-shadow:var(--cx-sh-lg);overflow:hidden}
.cxhead{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:16px 22px;display:flex;justify-content:space-between;align-items:center}
.cxhead h3{margin:0;font-size:16px}
.cxx{background:rgba(255,255,255,.25);border:none;color:#fff;width:30px;height:30px;border-radius:50%;font-size:16px;cursor:pointer;font-weight:700}
.cxbody{padding:18px 22px}
.mrow{display:flex;gap:14px;padding:9px 0;border-bottom:1px solid #f1f5f9}
.mrow:last-child{border-bottom:none}
.mk{flex:0 0 120px;color:#94a3b8;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.3px;padding-top:2px}
.mv{flex:1;color:#1e293b;font-size:14px;font-weight:500}
.st-fin{color:#166534;font-weight:800}.st-no{color:#b91c1c;font-weight:800}.st-pend{color:#94a3b8;font-weight:700}
h2{font-size:18px;color:#7c3aed;margin:0 0 14px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:10px 9px;background:#f5f3ff;color:#6d28d9;font-weight:800;font-size:11px;text-transform:uppercase;letter-spacing:.3px}
td{padding:10px 9px;border-bottom:1px solid #f1f5f9;vertical-align:middle}
tbody tr:hover{background:#faf5ff}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:#1e40af}
.num{text-align:right;font-variant-numeric:tabular-nums}
.delta-ok{color:#166534}.delta-warn{color:#b45309;font-weight:700}
.muted{color:#94a3b8}
#pasos-sec{display:block}
.printonly{display:none}
.btn-print{display:inline-flex;align-items:center;gap:6px;background:#ea580c;color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;margin-bottom:12px}
@media print{
  body{padding:0;background:#fff;color:#000}
  .back,.btn-print,.noprint,.cxmodal,.b-time,.b-mbr,.b-pdf,.b-rot,.b-aj,.b-soon,.b-mini,.b-i,.b-e,.b-pdf-sm{display:none !important}
  .printonly{display:block;text-align:center;border-bottom:2px solid #0f172a;margin-bottom:12px;padding-bottom:8px}
  .printonly b{font-size:16px;letter-spacing:.5px}
  .printonly span{font-size:12px;color:#334155}
  .wrap{max-width:100%;margin:0}
  .card{box-shadow:none;border:1px solid #cbd5e1;break-inside:avoid;page-break-inside:avoid}
  h2{font-size:14px}
  table{font-size:10px;width:100%}
  tr{break-inside:avoid;page-break-inside:avoid}
  th,td{padding:4px 6px !important}
}
</style></head><body>
<div class="wrap">
<a class="back" href="/inventarios#fabricacion"><span class="arw">&larr;</span> Volver a Producción</a>
<div class="printonly"><b>Espagiria Laboratorio SAS</b><br><span>INSTRUCTIVO DE MANUFACTURA &middot; PRD-PRO-001-F01</span></div>
<div style="height:10px"></div>
<button class="btn-print" onclick="window.print()">&#128196; Descargar / Imprimir instructivo (PDF)</button>
<div class="card" id="head">Cargando…</div>
<div class="card pad" id="pasos-sec"><h2>📖 Instrucción de Manufactura</h2><div id="pasos"></div></div>
</div>
<div class="cxmodal" id="cxmodal" onclick="if(event.target===this)cerrarModal()">
  <div class="cxbox">
    <div class="cxhead"><h3>ℹ️ Detalles de la Verificación</h3><button class="cxx" onclick="cerrarModal()">×</button></div>
    <div class="cxbody" id="cxmbody"></div>
  </div>
</div>
<input type="file" id="reg-file" accept="image/*,application/pdf" capture="environment" style="display:none" onchange="_subirRegistroFile(this.files&&this.files[0])">
<div class="cxmodal" id="pesomodal" onclick="if(event.target===this)cerrarPeso()">
  <div class="cxbox">
    <div class="cxhead" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><h3>✏️ Materia Prima Dispensada</h3><button class="cxx" onclick="cerrarPeso()">×</button></div>
    <div class="cxbody">
      <div id="peso-mp" style="font-weight:700;color:#1e293b;margin-bottom:4px"></div>
      <div id="peso-apesar" class="muted" style="font-size:12px;margin-bottom:12px"></div>
      <label style="display:block;font-size:11px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">Cantidad pesada (g)</label>
      <input id="peso-cant" type="number" step="0.01" min="0" style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:8px;font-size:15px;margin-bottom:12px">
      <label style="display:block;font-size:11px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">N° de lote</label>
      <input id="peso-lote" type="text" style="width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;margin-bottom:12px">
      <label style="display:block;font-size:11px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">Observaciones</label>
      <textarea id="peso-obs" rows="2" style="width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;resize:vertical"></textarea>
      <div id="peso-msg" style="font-size:12px;margin-top:8px"></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:14px">
        <button onclick="cerrarPeso()" style="background:#f1f5f9;color:#475569;border:none;border-radius:8px;padding:9px 18px;font-weight:700;cursor:pointer">Cerrar</button>
        <button id="peso-save" onclick="guardarPeso()" style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:9px 22px;font-weight:700;cursor:pointer">Guardar</button>
      </div>
    </div>
  </div>
</div>
<script>
var EBR_ID = __EBR_ID__;
// DIAGNÓSTICO VISIBLE (6-jun) · prueba que el script SÍ corre en el navegador.
// Marca #head con un contador en vivo apenas arranca; load() lo reemplaza al
// recibir datos. Si el usuario ve "⏳ Conectando… Ns" subiendo, el JS está vivo.
(function(){
  try{
    var s=0;
    var el=document.getElementById('head');
    if(el) el.innerHTML='⏳ Conectando al servidor… <b id="cxsec">0</b>s';
    window.__cxTick=setInterval(function(){s++;var c=document.getElementById('cxsec');if(c)c.textContent=s;},1000);
  }catch(e){}
})();
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return (n==null||n==='')?'—':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1})+' g';}
function estadoColor(e){var s=(e||'').toLowerCase();
  if(s.indexOf('liber')>=0||s.indexOf('aprob')>=0)return '#166534';
  if(s.indexOf('rechaz')>=0)return '#991b1b';
  if(s.indexOf('cuarentena')>=0)return '#1e40af';
  if(s.indexOf('complet')>=0)return '#0e7490';
  return '#854d0e';}
function estadoBg(e){var s=(e||'').toLowerCase();
  if(s.indexOf('liber')>=0||s.indexOf('aprob')>=0)return '#dcfce7';
  if(s.indexOf('rechaz')>=0)return '#fee2e2';
  if(s.indexOf('cuarentena')>=0)return '#dbeafe';
  if(s.indexOf('complet')>=0)return '#cffafe';
  return '#fef9c3';}
function togglePasos(){var s=document.getElementById('pasos-sec');s.style.display=s.style.display==='none'?'block':'none';if(s.style.display==='block')s.scrollIntoView({behavior:'smooth'});}
// 3. Dispensado · botón "✏️" → modal "Corregir Peso" (Cantidad + lote + obs)
var _pesoIdx=null;
function cerrarPeso(){var m=document.getElementById('pesomodal');if(m)m.style.display='none';}
function registrarPesaje(idx){
  var it=(window._pesajeSheet||[])[idx]; if(!it) return;
  _pesoIdx=idx;
  document.getElementById('peso-mp').innerHTML='<span class="mono">'+esc(it.material_id)+'</span> '+esc(it.material_nombre||'');
  document.getElementById('peso-apesar').textContent='Cantidad a pesar: '+(it.cant_a_pesar_g!=null?Number(it.cant_a_pesar_g).toLocaleString('es-CO',{maximumFractionDigits:1})+' g':'—');
  document.getElementById('peso-cant').value=(it.cant_pesada_g!=null?it.cant_pesada_g:(it.cant_a_pesar_g!=null?it.cant_a_pesar_g:''));
  document.getElementById('peso-lote').value=(it.lote&&it.lote!=='—'?it.lote:'');
  document.getElementById('peso-obs').value=it.obs_pesaje||'';
  document.getElementById('peso-msg').innerHTML='';
  document.getElementById('pesomodal').style.display='flex';
}
async function guardarPeso(){
  if(_pesoIdx===null) return;
  var it=(window._pesajeSheet||[])[_pesoIdx]; if(!it) return;
  var msg=document.getElementById('peso-msg');
  var real=parseFloat(document.getElementById('peso-cant').value);
  if(isNaN(real)||real<0){msg.innerHTML='<span style="color:#b91c1c">Cantidad inválida</span>';return;}
  var lote=(document.getElementById('peso-lote').value||'').trim();
  var obs=(document.getElementById('peso-obs').value||'').trim();
  var btn=document.getElementById('peso-save'); btn.disabled=true; btn.textContent='Guardando…';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pesajes',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({material_id:it.material_id,cantidad_real_g:real,lote_mp:lote,notas:obs})});
    var d=await r.json();
    if(!r.ok){
      if(d&&d.codigo==='FIRMA_REQUERIDA'){msg.innerHTML='<span style="color:#b45309">🔒 Requiere e-firma (motor EBR estricto). Regístralo desde el runner de legajos.</span>';}
      else{msg.innerHTML='<span style="color:#b91c1c">Error: '+esc((d&&d.error)||r.status)+'</span>';}
      btn.disabled=false; btn.textContent='Guardar'; return;
    }
    cerrarPeso(); load();
  }catch(e){ msg.innerHTML='<span style="color:#b91c1c">Error de red: '+esc(e.message)+'</span>'; btn.disabled=false; btn.textContent='Guardar'; }
}
// 3. Dispensado · botón "i" → "Detalle del Pesaje" (Realizado por / Verificado por)
function infoPesaje(idx){
  var it=(window._pesajeSheet||[])[idx]; if(!it) return;
  function dpct(){ if(it.cant_a_pesar_g&&it.cant_pesada_g!=null){var dl=(it.cant_pesada_g-it.cant_a_pesar_g)/it.cant_a_pesar_g*100; return dl.toLocaleString('es-CO',{maximumFractionDigits:2})+'%';} return '—';}
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var realizado = it.pesado ? (esc(it.realizado_por_full||it.pesado_por||'—')+(it.pesado_at?' · '+fdt(it.pesado_at):'')) : '<span class="st-pend">— sin registrar</span>';
  var verificado = (it.verificado_por&&it.verificado_por.trim()) ? (esc(it.verificado_por_full||it.verificado_por)+(it.verificado_at?' · '+fdt(it.verificado_at):'')) : '<span class="st-pend">pendiente de verificación (Calidad)</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Materia Prima</div><div class="mv"><span class="mono">'+esc(it.material_id)+'</span> '+esc(it.material_nombre||'')+'</div></div>'
    +'<div class="mrow"><div class="mk">N° Lote</div><div class="mv mono">'+esc(it.lote||'—')+'</div></div>'
    +'<div class="mrow"><div class="mk">Cant. a pesar</div><div class="mv">'+gfmt(it.cant_a_pesar_g)+'</div></div>'
    +'<div class="mrow"><div class="mk">Cantidad Pesada</div><div class="mv"><b>'+(it.cant_pesada_g!=null?gfmt(it.cant_pesada_g):'<span class="st-pend">pendiente</span>')+'</b> <span class="muted">(desv '+dpct()+')</span></div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>'
    +'<div class="mrow"><div class="mk">Verificado por</div><div class="mv">'+verificado+'</div></div>'
    +(it.obs_pesaje?'<div class="mrow"><div class="mk">Observación</div><div class="mv">'+esc(it.obs_pesaje)+'</div></div>':'');
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Pesaje';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 3. Dispensado · "✓ Verificar Dispensado" → valida completitud + tolerancia
function verificarDispensado(){
  var sh=window._pesajeSheet||[];
  if(!sh.length){alert('Esta orden no tiene fórmula con materias primas.');return;}
  var pend=sh.filter(function(x){return !x.pesado;});
  var fuera=sh.filter(function(x){return x.pesado && x.cant_a_pesar_g && x.cant_pesada_g!=null && Math.abs((x.cant_pesada_g-x.cant_a_pesar_g)/x.cant_a_pesar_g*100)>5;});
  if(pend.length){
    alert('⚠ Dispensado INCOMPLETO · faltan '+pend.length+' de '+sh.length+' materias primas por pesar:\\n\\n'+pend.slice(0,12).map(function(x){return '· '+(x.material_nombre||x.material_id);}).join('\\n')+(pend.length>12?'\\n…':''));
    return;
  }
  if(fuera.length){
    alert('⚠ Dispensado completo PERO '+fuera.length+' MP con desviación > 5% (revisar):\\n\\n'+fuera.map(function(x){return '· '+(x.material_nombre||x.material_id)+' ('+((x.cant_pesada_g-x.cant_a_pesar_g)/x.cant_a_pesar_g*100).toFixed(1)+'%)';}).join('\\n'));
    return;
  }
  alert('✓ Dispensado VERIFICADO · las '+sh.length+' materias primas están pesadas y dentro de tolerancia (±5%).');
}
// 5. Fabricación/Mezcla · botón "i" → detalle del paso (reusa el modal)
function infoPaso(i){
  var p=(window._pasos||[])[i]; if(!p) return;
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var realizado = p.completado_flag ? (esc(p.realizado_por_full||p.operario||'—')+(p.completado?' · '+fdt(p.completado):'')) : '<span class="st-pend">— pendiente</span>';
  var verificado = (p.verificado_por&&p.verificado_por.trim()) ? esc(p.verificado_por_full||p.verificado_por) : '<span class="st-pend">pendiente de verificación (Calidad)</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Paso</div><div class="mv"><b>'+esc(p.orden)+'</b></div></div>'
    +'<div class="mrow"><div class="mk">Actividad</div><div class="mv">'+esc(p.descripcion||'')+'</div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>'
    +'<div class="mrow"><div class="mk">Verificado por</div><div class="mv">'+verificado+'</div></div>'
    +(p.observaciones?'<div class="mrow"><div class="mk">Observación / Resultado</div><div class="mv">'+esc(p.observaciones)+'</div></div>':'');
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Paso';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 5. Fabricación/Mezcla · botón "✏️" → registrar/completar el paso
async function completarPaso(i){
  var p=(window._pasos||[])[i]; if(!p) return;
  var obs=prompt('Resultado / observación del paso '+p.orden+':', p.observaciones||'');
  if(obs===null) return;
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs})});
  var d=await r.json();
  if(!r.ok){
    if(d&&(''+(d.error||'')).indexOf('e-signature')>=0){alert('🔒 Este paso requiere e-firma (motor EBR estricto). Regístralo desde el runner de legajos.');}
    else{alert('Error: '+((d&&d.error)||r.status));}
    return;
  }
  load();
}
// 6. Controles en Proceso · botón "i" → detalle del control (reusa el modal)
function infoIpc(i){
  var c=(window._ipc||[])[i]; if(!c) return;
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var conf = c.conforme===1?'<span class="st-fin">Cumple ✓</span>':c.conforme===0?'<span class="st-no">No cumple ✗</span>':c.conforme===2?'<span class="st-pend">No aplica</span>':'<span class="st-pend">pendiente</span>';
  var realizado = c.realizado_por ? (esc(c.realizado_por_full||c.realizado_por)+(c.fecha?' · '+fdt(c.fecha):'')) : '<span class="st-pend">— sin registrar</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Control</div><div class="mv">'+esc(c.control||'')+'</div></div>'
    +(c.rango?'<div class="mrow"><div class="mk">Rango / Spec</div><div class="mv">'+esc(c.rango)+'</div></div>':'')
    +'<div class="mrow"><div class="mk">Resultado</div><div class="mv"><b>'+esc(c.resultado||'pendiente')+'</b></div></div>'
    +'<div class="mrow"><div class="mk">Conforme</div><div class="mv">'+conf+'</div></div>'
    +'<div class="mrow"><div class="mk">Observaciones</div><div class="mv">'+esc(c.observaciones||'No aplica')+'</div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>';
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Control';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// Registrar un Control en Proceso (sección 6) · valor + Cumple/No cumple, o
// marcar "No aplica". Enruta a /ipc-resultados (MBR) o /ipc-estandar (estándar).
async function registrarIpc(i){
  var cc=(window._ipc||[])[i]; if(!cc) return;
  var aplica=confirm('Control: '+(cc.control||'')+'\\n\\n¿APLICA a este producto?\\n\\nAceptar = Sí (registrar resultado)\\nCancelar = NO APLICA');
  var body={};
  if(!aplica){
    body.no_aplica=true;
  } else if(cc.rango){
    var v=prompt('Valor medido ('+(cc.rango||'')+'):'); if(v===null)return; v=(v||'').trim(); if(v==='')return;
    if(isNaN(parseFloat(v.replace(',','.')))){alert('Valor numérico inválido');return;}
    body.valor_medido=parseFloat(v.replace(',','.'));
  } else {
    var conf=confirm('¿El control CUMPLE?\\n\\nAceptar = Cumple · Cancelar = No cumple');
    var txt=prompt('Resultado / observación (ej: 1,056 g/mL · Inodoro · Amarillento…):')||'';
    body.conforme=conf?1:0; body.valor_texto=txt.trim();
  }
  var url;
  if(cc.tipo==='estandar'){
    url='/api/brd/ebr/'+EBR_ID+'/ipc-estandar';
    body.control_codigo=cc.codigo; body.control_nombre=cc.control;
  } else {
    url='/api/brd/ebr/'+EBR_ID+'/ipc-resultados';
    body.ipc_spec_id=cc.spec_id;
  }
  try{
    var r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert((d&&d.error)||'No se pudo registrar el control');return;}
    if(d.desviacion){alert('⚠ Fuera de especificación · se abrió la desviación '+((d.desviacion&&d.desviacion.codigo)||'')+' automáticamente.');}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
// 8. Registros Físicos · subir foto/PDF (el rótulo se imprime, se diligencia y se
// sube la foto · MyBatch). En el celular abre la cámara (capture=environment).
var _regDesc='';
function subirRegistroPick(){
  // El Estado de Limpieza de Áreas ya NO se sube como foto: es DIGITAL (rótulo
  // F02 auto-rellenado, ver arriba "rótulo de limpieza"). Aquí solo se suben los
  // registros que SÍ son evidencia física: rótulos de pesaje / MP dispensada.
  var c=prompt('¿Qué registro vas a subir?\\n\\n1 = Materia Prima Dispensada / Rótulo de pesaje\\n2 = Otro (escribir)\\n\\nNota: el Estado de Limpieza de Áreas es DIGITAL — usá el rótulo F02 (no subir foto).','1');
  if(c===null) return;
  var map={'1':'Materia Prima Dispensada / Rótulo de pesaje'};
  _regDesc = map[(c||'').trim()];
  if(!_regDesc){ _regDesc = prompt('Describe el registro:','') || 'Registro físico'; }
  var f=document.getElementById('reg-file'); if(f){f.value='';f.click();}
}
async function _subirRegistroFile(file){
  if(!file) return;
  if(file.size > 6*1024*1024){ alert('Archivo muy grande (máx ~6MB). Toma la foto en menor resolución.'); return; }
  var desc=_regDesc || file.name;
  var reader=new FileReader();
  reader.onload=async function(){
    var b64=((reader.result||'')+'').split(',')[1]||'';
    if(!b64){ alert('No se pudo leer el archivo'); return; }
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/registros-fisicos',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({descripcion:(desc||file.name),tipo:'foto',archivo_nombre:file.name,archivo_b64:b64})});
    var d=await r.json(); if(!r.ok){ alert('Error: '+((d&&d.error)||r.status)); return; }
    load();
  };
  reader.onerror=function(){ alert('Error al leer el archivo'); };
  reader.readAsDataURL(file);
}
// 7. Observaciones Generales · "+ Registrar"
async function registrarObservacion(){
  var desc=prompt('Observación general del proceso:');
  if(!desc) return;
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/observaciones',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({descripcion:desc})});
  var d=await r.json(); if(!r.ok){alert('Error: '+((d&&d.error)||r.status));return;}
  load();
}
// 1. Precauciones · "+ Agregar Equipo" (MyBatch ①)
async function agregarEquipo(){
  var desc=prompt('Equipo / precaución a registrar:');
  if(!desc) return;
  var tipo=confirm('¿Es un EQUIPO? (Aceptar=Equipo · Cancelar=Precaución)')?'equipo':'precaucion';
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/precauciones',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tipo:tipo,descripcion:desc})});
  var d=await r.json(); if(!r.ok){alert('Error: '+(d.error||r.status));return;}
  load();
}
// 2/4. Despeje · botón "i" → modal "Detalles de la Verificación" (MyBatch parity)
function cerrarModal(){var m=document.getElementById('cxmodal');if(m)m.style.display='none';}
function _despArr(fab){return fab?(window._despejeChkFab||[]):(window._despejeChk||[]);}
function infoDespeje(idx, fab){
  var it=_despArr(fab).find(function(x){return x.idx===idx;}); if(!it) return;
  var estadoTxt = it.cumple===1?'<span class="st-fin">Sí cumple ✓</span>'
                : it.cumple===0?'<span class="st-no">No cumple ✗</span>'
                : '<span class="st-pend">Pendiente de verificar</span>';
  var rows=''
    + '<div class="mrow"><div class="mk">Verificación</div><div class="mv">'+esc(it.texto)+'</div></div>'
    + '<div class="mrow"><div class="mk">Cumple</div><div class="mv">'+estadoTxt+'</div></div>'
    + '<div class="mrow"><div class="mk">Responsable</div><div class="mv">'+esc(it.registrado_por||'— sin registrar')+'</div></div>'
    + '<div class="mrow"><div class="mk">Fecha / Hora</div><div class="mv">'+(it.fecha?esc(it.fecha.substring(0,16).replace('T',' ')):'—')+'</div></div>'
    + '<div class="mrow"><div class="mk">Observación</div><div class="mv">'+esc(it.observaciones||'Ninguna')+'</div></div>';
  var body=document.getElementById('cxmbody');
  if(body) body.innerHTML=rows;
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 2/4. Despeje · botón "✏️" · operario REGISTRA / Calidad CORRIGE
async function editDespeje(idx, fab){
  var etapa = fab?'fabricacion':'dispensacion';
  var it=_despArr(fab).find(function(x){return x.idx===idx;}); if(!it) return;
  var esCorreccion = it.cumple!=null;
  var titulo = esCorreccion ? 'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)' : 'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar=Sí · Cancelar=No)');
  var obs=prompt('Observación'+(esCorreccion?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:etapa})});
  var d=await r.json();
  if(!r.ok){
    if(r.status===403){alert('🔒 '+(d.error||'Solo Calidad / Dirección Técnica puede corregir un resultado ya registrado.'));}
    else{alert('Error: '+(d.error||r.status));}
    return;
  }
  load();
}
async function ajustarOrden(){
  // + Ajuste: corrige la cantidad de la producción asociada (re-escala MP por FEFO).
  // Reusa /api/produccion/<pid>/ajustar-cantidad (admin · audit INVIMA).
  try{
    var pr=await fetch('/api/brd/ebr/'+EBR_ID+'/produccion-id',{credentials:'same-origin'});
    var pd=await pr.json();
    if(!pd.produccion_id){alert('Esta orden no tiene una producción asociada para ajustar (legajo sin registro de producción).');return;}
    var nv=prompt('Nueva cantidad a fabricar (kg):'); if(nv===null)return; nv=parseFloat(nv);
    if(!nv||nv<=0){alert('Cantidad inválida');return;}
    var mot=(prompt('Motivo del ajuste (mínimo 10 caracteres · audit INVIMA):')||'').trim();
    if(mot.length<10){alert('El motivo debe tener al menos 10 caracteres');return;}
    var t=''; try{var cr=await fetch('/api/csrf-token',{credentials:'same-origin'});t=(await cr.json()).csrf_token||'';}catch(e){}
    var r=await fetch('/api/produccion/'+pd.produccion_id+'/ajustar-cantidad',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({nueva_cantidad_kg:nv,motivo:mot})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo ajustar: '+((d&&d.error)||r.status));return;}
    alert('✓ Ajustado a '+nv+' kg. '+(d.mensaje||''));
    location.reload();
  }catch(e){alert('Error de red: '+(e&&e.message||e));}
}
async function load(){
  var headEl=document.getElementById('head');
  try{
    // Timeout duro 25s · una orden nunca debe quedarse en "Cargando…" eterno.
    var ctrl=new AbortController();
    var to=setTimeout(function(){ctrl.abort();},15000);
    var r;
    try{
      r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store',signal:ctrl.signal});
    }catch(fe){
      clearTimeout(to); try{clearInterval(window.__cxTick);}catch(e){}
      var msg=(fe&&fe.name==='AbortError')
        ? 'El servidor no respondió en 15s (posible cuelgue del lote '+EBR_ID+'). Avísame para revisarlo.'
        : 'No se pudo contactar el servidor: '+esc((fe&&fe.message)||fe);
      headEl.innerHTML='<div style="padding:24px;color:#b91c1c"><b>⏱ '+msg+'</b><br><button onclick="load()" style="margin-top:10px;background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer">Reintentar</button></div>';
      return;
    }
    clearTimeout(to);
    if(r.status===401){location.href='/login';return;}
    var d;
    try{ d=await r.json(); }
    catch(je){
      var txt=''; try{txt=await r.text();}catch(e2){}
      headEl.innerHTML='<div style="padding:24px;color:#b91c1c"><b>Error '+r.status+' del servidor.</b><br><span style="font-size:12px;color:#64748b">'+esc((txt||'').substring(0,300))+'</span></div>';
      return;
    }
    if(!r.ok){headEl.innerHTML='<div style="padding:24px;color:#b91c1c"><b>Error '+r.status+': '+esc(d.error||'fallo')+'</b></div>';return;}
    var h=d.header||{};
    var numop = h.numero_op || ('EBR-'+EBR_ID);
    var estado = h.estado||'—';
    var fase = h.fase||'fabricacion';
    var faseLbl = ({fabricacion:'Fabricación · OP',envasado:'Envasado · OF',acondicionamiento:'Acondicionamiento · OA'})[fase]||fase;
    // Rótulos de pesaje: reusa el generador existente /rotulos/<producto>/<kg>
    var prodRot = encodeURIComponent(h.producto||h.titulo||'');
    var kgRot = (Number(h.lote_size_g||0)/1000) || 1;
    try{clearInterval(window.__cxTick);}catch(e){}
    document.getElementById('head').innerHTML =
      '<div class="hbar">'+
        '<div class="htitle">'+
          '<div class="hkicker">📋 Orden de Producción · '+esc(faseLbl)+'</div>'+
          '<h1>'+esc(numop)+'</h1>'+
          '<div class="prod">'+esc(h.producto||h.titulo||'—')+'</div>'+
          ((d.mi_rol&&d.mi_rol.rol)?'<div style="margin-top:6px"><span style="display:inline-flex;align-items:center;gap:5px;background:#f5f3ff;color:#6d28d9;font-size:12px;font-weight:700;padding:4px 11px;border-radius:20px;border:1px solid #a78bfa">&#128100; '+esc(d.mi_rol.rol)+'</span></div>':'')+
        '</div>'+
        '<span class="estado-badge" style="background:'+estadoBg(estado)+';color:'+estadoColor(estado)+'">'+esc(estado)+'</span>'+
      '</div>'+
      '<div class="grid">'+
        '<div><div class="lbl">N° de Lote Bulk</div><div class="val mono">'+esc(h.lote_codigo||'—')+'</div></div>'+
        '<div><div class="lbl">Tamaño de Lote</div><div class="val">'+gfmt(h.lote_size_g)+'</div></div>'+
        '<div><div class="lbl">Fecha / Hora</div><div class="val">'+esc((h.iniciado_at_utc||'—').substring(0,16).replace("T"," "))+'</div></div>'+
        '<div><div class="lbl">Área o Línea</div><div class="val">'+esc(h.area_linea||'—')+'</div></div>'+
        '<div><div class="lbl">Elaborado por</div><div class="val">'+esc(h.operario||'—')+'</div></div>'+
        '<div><div class="lbl">Supervisado por</div><div class="val">'+esc(h.supervisado_por||'—')+'</div></div>'+
        '<div style="grid-column:1/-1"><div class="lbl">Observaciones</div><div class="val" style="font-weight:400">'+esc(h.observaciones||'Ninguna')+'</div></div>'+
      '</div>'+
      (h.liberado_por ? '<div class="liber-line">✅ Liberado por <b>'+esc(h.liberado_por)+'</b>'+(h.liberado_at_utc?(' · '+esc(h.liberado_at_utc.substring(0,16).replace("T"," "))):'')+'</div>' : '')+
      '<div class="btns">'+
        '<a class="b-time" data-tip="Línea de tiempo del lote: cada evento del legajo (inicio, pesajes, pasos, IPC, firmas) en orden cronológico." href="/brd/timeline/'+EBR_ID+'">📜 Timeline Batch Record</a>'+
        '<button class="b-mbr" data-tip="Abre la instrucción de manufactura: cabecera del lote, precauciones, despeje de línea y pasos del proceso." onclick="togglePasos()">📖 Instrucción de Manufactura</button>'+
        '<a class="b-pdf" data-tip="Descarga el legajo completo del lote en PDF (Batch Record) para imprimir o archivar." href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">📄 Descargar PDF</a>'+
        '<a class="b-rot" data-tip="Genera los rótulos de pesaje de materias primas para imprimir y pegar en cada recipiente." href="/rotulos/'+prodRot+'/'+kgRot+'" target="_blank">🖨 Rótulos de Pesaje</a>'+
        '<button class="b-aj" data-tip="Corrige la cantidad fabricada del lote y re-escala las materias primas (queda auditado · INVIMA)." onclick="ajustarOrden()">➕ Ajuste</button>'+
      '</div>';
    // Instrucción de Manufactura (MyBatch parity): cabecera de manufactura
    // (cantidades · densidad · rendimiento · aprobado calidad) + precauciones + pasos.
    function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
    function dt(s){return s? esc(String(s).substring(0,16).replace("T"," ")) : '—';}
    function mlf(v){return v!=null? (Number(v).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' mL') : '—';}
    // Cantidad Producida/Aprobada = "X Gr - Y mL" (granel en gramos y su equivalente mL).
    var prodAprob = (h.cantidad_real_g!=null? gfmt(h.cantidad_real_g):'—') +
                    (h.ml_envasable!=null? (' - '+mlf(h.ml_envasable)) : '');
    var estManuf = h.estado||'—';
    // Cabecera fiel a "INSTRUCCIONES DE MANUFACTURA" (MyBatch · Sebastián 5-jun).
    var manuf='<div class="grid" style="padding:0;margin-bottom:16px">'+
      fld('N° de Lote Bulk', '<span class="mono">'+esc(h.lote_codigo||'—')+'</span>')+
      fld('Cantidad Ordenada', gfmt(h.cantidad_objetivo_g))+
      fld('Área o Línea', esc(h.area_linea||'—'))+
      fld('Fecha Inicio', dt(h.iniciado_at_utc))+
      fld('Fecha Final', dt(h.completado_at_utc))+
      fld('Estado Actual', '<b style="color:'+estadoColor(estManuf)+'">'+esc(estManuf)+'</b>')+
      fld('Cantidad Producida/Aprobada', prodAprob)+
      fld('Densidad', h.densidad_g_ml? (Number(h.densidad_g_ml).toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'—')+
      fld('Rendimiento', h.yield_pct!=null? (Number(h.yield_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%'):'—')+
      fld('Cantidad Disponible', mlf(h.cantidad_disponible_ml))+
      fld('Supervisado por', esc(h.supervisado_por||'—'))+
      fld('Aprobado por (Calidad)', esc(h.liberado_por_full||h.liberado_por||'—'))+
      '</div>';
    var editable = (estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    // 1. Precauciones (MyBatch ① · texto + "+ Agregar Equipo" + lista de equipos/precauciones)
    var prec=d.precauciones||[];
    var precHtml='<div style="display:flex;align-items:center;gap:12px;margin:14px 0 8px">'+
        '<h3 style="font-size:15px;color:#7c3aed;margin:0">1. Precauciones</h3>'+
        (editable?'<button class="b-mini" data-tip="Registra un equipo usado o una precaución del proceso en este lote." onclick="agregarEquipo()">+ Agregar Equipo</button>':'')+
      '</div>'+
      '<div style="font-size:13px;color:#334155;margin-bottom:8px">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de fabricación:</div>'+
      (prec.length
        ? '<ul style="margin:0 0 14px 18px;font-size:13px;color:#334155">'+prec.map(function(p){
            var et=(p.tipo==='equipo')?'🛠 Equipo':'⚠ Precaución';
            return '<li><b>'+et+':</b> '+esc(p.descripcion||'')+(p.registrado_por?' <span class="muted">('+esc(p.registrado_por)+')</span>':'')+'</li>';}).join('')+'</ul>'
        : '<div class="muted" style="margin-bottom:14px">Sin equipos/precauciones registrados.</div>');
    // 2/4. Despeje de Línea · MISMO checklist, dos etapas (dispensación + fabricación).
    window._despejeChk=d.despeje_checklist||[];
    window._despejeChkFab=d.despeje_checklist_fab||[];
    function cumpleCell(c){
      if(c===1) return '<span style="color:#166534;font-weight:700">Sí ✓</span>';
      if(c===0) return '<span style="color:#b91c1c;font-weight:700">No ✗</span>';
      return '<span class="muted">Pendiente</span>';
    }
    // num=número de sección, titulo=Dispensación/Fabricación, etapa=string, fab=0/1
    function buildDespeje(arr, num, titulo, etapa, fab){
      return '<h3 style="font-size:15px;color:#7c3aed;margin:18px 0 6px">'+num+'. Despeje de Línea - '+titulo+
        '<a class="b-pdf-sm" href="/brd/despeje/'+EBR_ID+'?etapa='+etapa+'" target="_blank" data-tip="Descarga/imprime el formato del despeje de '+titulo.toLowerCase()+' (registro GMP firmable).">📄 PDF</a>'+
        '</h3>'+
        '<div style="font-size:13px;color:#334155;margin-bottom:8px">Realizar despeje en el área de '+titulo.toLowerCase()+' de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
        '<table><thead><tr><th>Verificación</th><th style="text-align:center">Cumple</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        arr.map(function(it){
          return '<tr><td>'+esc(it.texto)+'</td>'+
            '<td style="text-align:center">'+cumpleCell(it.cumple)+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalles de la verificación: texto completo, si cumple, quién lo verificó y cuándo." onclick="infoDespeje('+it.idx+','+fab+')">i</button> '+
              (editable?'<button class="b-e tip-r" data-tip="'+(it.cumple!=null?'Corregir Resultado · solo Calidad / Dirección Técnica puede cambiar un resultado ya registrado.':'Registrar verificación (operario): marca si cumple Sí/No + observación.')+'" onclick="editDespeje('+it.idx+','+fab+')">✏️</button>':'')+
            '</td></tr>';
        }).join('')+'</tbody></table>'+
        '<div style="font-size:11px;color:#94a3b8;margin:6px 0 14px">Sí = cumple · No = no cumple · Pendiente = sin verificar. Cada verificación queda con responsable y hora.</div>';
    }
    var despHtml=buildDespeje(window._despejeChk, '2', 'Dispensación', 'dispensacion', 0);
    var despFabHtml=buildDespeje(window._despejeChkFab, '4', 'Fabricación', 'fabricacion', 1);
    // 3. Dispensado de Materias Primas · INTEGRADO en el instructivo (en secuencia,
    // como en MyBatch · ya no es una tarjeta aparte). % · N° Lote · Cant. a pesar ·
    // Cant. pesada · Acciones (i / ✏️) + Verificar Dispensado + PDF.
    var sheet=d.pesaje_sheet||[];
    window._pesajeSheet=sheet;
    var dispHtml;
    if(sheet.length){
      var pend=sheet.filter(function(x){return !x.pesado;}).length;
      dispHtml='<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0 6px">'+
          '<h3 style="font-size:15px;color:#7c3aed;margin:0">3. Dispensado de Materias Primas'+
            '<a class="b-pdf-sm" href="/brd/dispensado/'+EBR_ID+'" target="_blank" data-tip="Descarga/imprime la hoja de dispensado (registro GMP).">📄 PDF</a></h3>'+
          (editable?'<button class="b-mini" data-tip="Valida que todas las MP estén pesadas y dentro de tolerancia (±5%)." onclick="verificarDispensado()">✓ Verificar Dispensado</button>':'')+
        '</div>'+
        '<div style="font-size:12px;color:#64748b;margin-bottom:6px">'+sheet.length+' materias primas · '+(sheet.length-pend)+' pesadas · '+pend+' pendientes</div>'+
        '<div style="font-size:12.5px;color:#334155;margin-bottom:8px">Realizar el dispensado de materias primas según las cantidades de la orden y los procedimientos internos.</div>'+
        '<table><thead><tr><th>Materia Prima</th><th class="num">%</th><th>N° Lote</th>'+
        '<th class="num">Cant. a pesar</th><th class="num">Cant. pesada</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        sheet.map(function(p,i){
          var pesadaCol;
          if(p.pesado){
            var delta = (p.cant_a_pesar_g&&p.cant_pesada_g!=null)?((p.cant_pesada_g-p.cant_a_pesar_g)/p.cant_a_pesar_g*100):null;
            var dcl = (delta!=null&&Math.abs(delta)>5)?'delta-warn':'delta-ok';
            pesadaCol='<span class="'+dcl+'">'+gfmt(p.cant_pesada_g)+' ✓</span>';
          } else { pesadaCol='<span style="color:#cbd5e1">pendiente</span>'; }
          return '<tr>'+
            '<td><span class="mono">'+esc(p.material_id)+'</span> '+esc(p.material_nombre||'')+'</td>'+
            '<td class="num">'+(p.porcentaje!=null?Number(p.porcentaje).toLocaleString('es-CO',{maximumFractionDigits:3})+'%':'—')+'</td>'+
            '<td class="mono">'+esc(p.lote||'—')+'</td>'+
            '<td class="num">'+gfmt(p.cant_a_pesar_g)+'</td>'+
            '<td class="num">'+pesadaCol+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalle del Pesaje: cantidad pesada, realizado por (operario) y verificado por (Calidad)." onclick="infoPesaje('+i+')">i</button> '+
              (editable?'<button class="b-e tip-r" data-tip="Corregir Peso: ajusta la cantidad pesada y agrega observación." onclick="registrarPesaje('+i+')">✏️</button>':'')+
            '</td>'+
          '</tr>';
        }).join('')+'</tbody></table>'+
        '<div class="muted" style="margin:6px 0 14px;font-size:11px">El pesaje queda con tu usuario y la hora. Con el motor EBR en modo estricto, además exige e-firma (se registra desde el runner de legajos).</div>';
    } else {
      dispHtml='<h3 style="font-size:15px;color:#7c3aed;margin:18px 0 6px">3. Dispensado de Materias Primas</h3>'+
        '<div class="muted" style="margin-bottom:14px">Esta orden no tiene fórmula con materias primas.</div>';
    }
    // Ajustes de materias primas (MyBatch · subsección entre dispensado y despeje fab)
    var ajustesHtml='<h3 style="font-size:15px;color:#7c3aed;margin:18px 0 6px">Ajustes</h3>'+
      '<div class="muted" style="margin-bottom:14px;font-size:13px">Sin registro de ajustes de materias primas.</div>';
    // 5. Fabricación / Mezclado · ACTIVIDAD / Realizado por / Verificado por / Acciones
    // (MyBatch) · los pasos vienen del MBR del producto (mbr_pasos → ebr_pasos_ejecutados).
    var pasos=d.pasos||[];
    window._pasos=pasos;
    var pasosHtml='<h3 style="font-size:15px;color:#7c3aed;margin:18px 0 6px">5. Fabricación / Mezclado</h3>'+
      '<div style="font-size:13px;color:#334155;margin-bottom:8px">Realizar las siguientes actividades de acuerdo al orden establecido.</div>'+
      (pasos.length
      ? '<table><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){
          var realizado = p.completado_flag ? (esc(p.realizado_por_full||p.operario||'—')+(p.completado?' <span class="muted">'+esc(p.completado.substring(0,16).replace("T"," "))+'</span>':'')) : '<span class="muted">pendiente</span>';
          var verificado = (p.verificado_por&&p.verificado_por.trim()) ? esc(p.verificado_por_full||p.verificado_por) : '<span class="muted">—</span>';
          return '<tr><td style="font-size:12.5px"><b>Paso '+esc(p.orden)+'.</b> '+esc(p.descripcion)+'</td>'+
            '<td style="font-size:11.5px">'+realizado+'</td>'+
            '<td style="font-size:11.5px">'+verificado+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalles del paso: actividad, realizado por y verificado por." onclick="infoPaso('+i+')">i</button> '+
              (editable?'<button class="b-e tip-r" data-tip="Registrar / corregir este paso (queda con tu usuario y la hora)." onclick="completarPaso('+i+')">✏️</button>':'')+
            '</td></tr>';
        }).join('')+'</tbody></table>'
      : '<div class="muted">Sin pasos registrados · los pasos de fabricación se definen en el MBR del producto y se copian al crear el legajo.</div>');
    // 6. Controles en Proceso (IPC) · CONTROL / RESULTADO / OBSERVACIONES / Realizado por
    var ipc=d.ipc||[];
    window._ipc=ipc;
    function cumpleBadge(c){
      if(c===1) return ' <span style="background:#dcfce7;color:#166534;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">CUMPLE</span>';
      if(c===0) return ' <span style="background:#fee2e2;color:#991b1b;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">NO CUMPLE</span>';
      if(c===2) return ' <span style="background:#e2e8f0;color:#475569;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">NO APLICA</span>';
      return '';
    }
    var ipcHtml='<h3 style="font-size:15px;color:#7c3aed;margin:18px 0 6px">6. Controles en Proceso</h3>'+
      '<div style="font-size:13px;color:#334155;margin-bottom:8px">Realizar muestreo y registrar el control en proceso:</div>'+
      (ipc.length
      ? '<table><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        ipc.map(function(cc,i){
          var resCol = cc.conforme===2 ? cumpleBadge(2)
                     : (cc.resultado ? (esc(cc.resultado)+cumpleBadge(cc.conforme)) : '<span class="muted">pendiente</span>');
          var regBtn = editable ? '<button class="b-e tip-r" data-tip="Registrar el control: valor + Cumple/No cumple, o marcar No aplica." onclick="registrarIpc('+i+')">✏️</button>' : '';
          return '<tr><td style="font-size:12.5px">'+esc(cc.control)+(cc.rango?' <span class="muted" style="font-size:10px">('+esc(cc.rango)+')</span>':'')+'</td>'+
            '<td style="font-size:12.5px">'+resCol+'</td>'+
            '<td style="font-size:11.5px">'+esc(cc.observaciones||'No aplica')+'</td>'+
            '<td style="font-size:11.5px">'+(cc.realizado_por?esc(cc.realizado_por_full||cc.realizado_por):'<span class="muted">—</span>')+'</td>'+
            '<td style="text-align:center;white-space:nowrap"><button class="b-i tip-r" data-tip="Detalle del control: rango, resultado, conforme, quién y cuándo." onclick="infoIpc('+i+')">i</button> '+regBtn+'</td>'+
          '</tr>';
        }).join('')+'</tbody></table>'
      : '<div class="muted">Sin controles en proceso · se definen en el MBR del producto (parámetros como densidad, pH, color…).</div>');
    // 7. Observaciones Generales del Proceso (bitácora · + Registrar)
    var obsP=d.observaciones_proceso||[];
    var obsHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px">'+
        '<h3 style="font-size:15px;color:#7c3aed;margin:0">7. Observaciones Generales del Proceso</h3>'+
        (editable?'<button class="b-mini" data-tip="Registra una observación general del proceso (queda con tu usuario y la hora)." onclick="registrarObservacion()">+ Registrar</button>':'')+
      '</div>'+
      (obsP.length
      ? '<table><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obsP.map(function(o){return '<tr><td style="font-size:12.5px">'+esc(o.descripcion||'')+'</td>'+
          '<td style="font-size:11.5px">'+esc(o.registrado_por_full||o.registrado_por||'—')+'</td>'+
          '<td class="muted" style="font-size:11px">'+esc((o.fecha||'').substring(0,16).replace("T"," "))+'</td></tr>';}).join('')+'</tbody></table>'
      : '<div class="muted">Sin observaciones registradas.</div>');
    // 8. Registros Físicos del Proceso Manufactura (fotos/PDF adjuntos)
    var regs=d.registros_fisicos||[];
    var regHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px">'+
        '<h3 style="font-size:15px;color:#7c3aed;margin:0">8. Registros Físicos del Proceso Manufactura</h3>'+
        (editable?'<button class="b-mini" data-tip="Sube una foto o PDF del registro físico diligenciado (ej: rótulo de pesaje firmado). En el celular abre la cámara." onclick="subirRegistroPick()">📷 Subir registro</button>':'')+
      '</div>'+
      (regs.length
      ? '<table><thead><tr><th>Código</th><th>Descripción</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td style="font-size:12.5px">'+esc(g.descripcion||'')+'</td>'+
          '<td style="text-align:center">'+(g.tiene_pdf?'<a class="b-pdf-sm" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" data-tip="Ver el registro físico (foto o PDF).">📄 Ver</a>':'<span class="muted">—</span>')+'</td></tr>';}).join('')+'</tbody></table>'
      : '<div class="muted">Sin registros físicos adjuntos.</div>');
    // Rótulo de limpieza del área (PRD-PRO-002-F02) · enlace al rótulo virtual.
    var _aid=(d.header&&d.header.area_id)?d.header.area_id:null;
    var rotuloHtml=_aid
      ? '<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px"><h3 style="font-size:15px;color:#7c3aed;margin:0">🏷️ Rótulo de limpieza del área</h3></div>'
        + '<div class="muted" style="font-size:12.5px;margin-bottom:6px">Estado de limpieza de '+esc(d.header.area_linea||'')+' (formato PRD-PRO-002-F02). El estado fluye con la producción · se opera desde «Estado salas en vivo».</div>'
        + '<a class="b-pdf-sm" href="/planta/rotulo-limpieza/'+_aid+'/pdf" target="_blank" data-tip="Abre el rótulo de limpieza F02 del área de esta orden.">🖨️ Ver / imprimir rótulo F02</a>'
      : '';
    // 9. Correcciones / Auditoría (Audit Trail · Part 11 · MyBatch parity).
    var corrs=d.correcciones||[];
    var corrHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px"><h3 style="font-size:15px;color:#7c3aed;margin:0">📝 Correcciones / Auditoría</h3></div>'+
      (corrs.length
       ? corrs.map(function(cr){
           var hd='<div style="font-weight:700;font-size:12.5px;margin-top:10px">'+esc(cr.usuario_full||cr.usuario)+' · '+esc(cr.accion)+' <span class="muted" style="font-weight:400">'+dt(cr.fecha)+'</span></div>';
           if(cr.campos && cr.campos.length){
             hd+='<table style="margin-top:4px"><thead><tr><th>Campo</th><th>Valor anterior</th><th>Valor nuevo</th></tr></thead><tbody>'+
               cr.campos.map(function(cp){return '<tr><td style="font-size:11.5px">'+esc(cp.campo)+'</td><td style="font-size:11.5px;color:#94a3b8">'+esc(cp.anterior||'—')+'</td><td style="font-size:11.5px;color:#166534">'+esc(cp.nuevo||'—')+'</td></tr>';}).join('')+'</tbody></table>';
           } else if(cr.detalle){
             hd+='<div class="muted" style="font-size:11.5px">'+esc(cr.detalle)+'</div>';
           }
           return hd;
         }).join('')
       : '<div class="muted">Sin correcciones registradas.</div>');
    document.getElementById('pasos').innerHTML = manuf + precHtml + despHtml + dispHtml + ajustesHtml + despFabHtml + pasosHtml + ipcHtml + obsHtml + regHtml + rotuloHtml + corrHtml;
  }catch(e){document.getElementById('head').innerHTML='<span style="color:#b91c1c">Error red: '+esc(e.message)+'</span>';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/orden/<int:ebr_id>", methods=["GET"])
def orden_detalle_page(ebr_id):
    """Detalle de Orden de Producción (legajo EBR) estilo MyBatch · solo lectura.
    Sub-pasos A+B: cabecera + botones + pesaje. Reusa vista-completa.
    El ENVASADO tiene su PROPIA página (aislada de producción · 9-jun) → redirige."""
    if not session.get("compras_user"):
        return Response(f'<script>location.href="/login?next=/planta/orden/{ebr_id}"</script>',
                        mimetype="text/html")
    try:
        _f = get_db().execute(
            "SELECT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones WHERE id=?",
            (ebr_id,)).fetchone()
        if _f and (_f[0] or '') == 'envasado':
            return Response(
                f'<script>location.href="/planta/legajo-envasado/{ebr_id}"</script>',
                mimetype="text/html")
        if _f and (_f[0] or '') == 'acondicionamiento':
            return Response(
                f'<script>location.href="/planta/legajo-acondicionamiento/{ebr_id}"</script>',
                mimetype="text/html")
    except Exception:
        pass
    return Response(_ORDEN_DETALLE_HTML
                    .replace("/*__TOOLTIP_CSS__*/", TOOLTIP_CSS)
                    .replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_ENVASADO_LEGAJO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Envasado · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.ortit{font-size:26px;font-weight:800;color:var(--cx-text,#18181b);margin:6px 0 6px;letter-spacing:-.4px}
.prod{color:var(--cx-text-mute,#71717a);font-size:17px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px 22px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:14px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.btnrow{display:flex;gap:12px;justify-content:flex-start;flex-wrap:wrap;margin-top:24px}
.bt{padding:11px 20px;border-radius:10px;font-size:13px;font-weight:600;border:1px solid transparent;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:all .15s ease}
.bt-add{background:var(--cx-primary,#6d28d9);color:#fff}.bt-add:hover{background:var(--cx-primary-dark,#4c1d95)}
.bt-pdf{background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);border-color:var(--cx-border,#e6e6ea)}.bt-pdf:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary,#6d28d9)}
.bt-back{background:transparent;color:var(--cx-text-mute,#71717a);border-color:var(--cx-border,#e6e6ea)}.bt-back:hover{background:var(--cx-bg-alt,#fbfbfd)}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 16px}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:13px 12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t thead th .ar{color:var(--cx-text-faint,#a1a1aa);font-size:10px;margin-left:3px}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
table.t tfoot td{font-weight:800;color:var(--cx-text,#18181b);border-top:2px solid var(--cx-border,#e6e6ea)}
.tnum{text-align:right}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.act{display:inline-flex;gap:6px;flex-wrap:wrap}
.ab{width:32px;height:32px;border-radius:8px;border:none;cursor:pointer;color:#fff;font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-play{background:var(--cx-success,#15803d)}.ab-plus{background:var(--cx-primary,#6d28d9)}.ab-x{background:var(--cx-danger,#dc2626)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-ed2{background:var(--cx-success,#15803d)}.ab-i{background:var(--cx-info,#2563eb)}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios#envasado">&larr; Envasado</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return n==null?'—':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1})+' g';}
function mlf(n){return n==null?'—':Number(n).toLocaleString('es-CO',{maximumFractionDigits:2})+' mL';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#b45309';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'—';
    var densi=h.densidad_g_ml?Number(h.densidad_g_ml):null;
    var gB=(Number(h.lote_size_g||0)>0)?Number(h.lote_size_g):(h.cantidad_objetivo_g!=null?Number(h.cantidad_objetivo_g):null);
    var mlB=(gB!=null&&densi)?(gB/densi):null;
    var tamBulk=(gB!=null?gfmt(gB):'—')+(mlB!=null?(' - '+mlf(mlB)):'');
    document.getElementById('cab').innerHTML=
      '<div class="ortit">ORDEN DE ENVASADO N°: '+esc(h.numero_op||('OF-'+EBR_ID))+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'—')+'</div>'+
      '<div style="margin:-10px 0 18px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div>'+
      '<div class="grid">'+
        fld('N° Lote Bulk','<span class="mono">'+esc(h.lote_codigo||'—')+'</span>')+
        fld('Tamaño Bulk',esc(tamBulk))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
        fld('Elaborado por',esc(h.operario||'—'))+
        fld('Observaciones',esc(h.observaciones||'Ninguna'))+
        fld('Cantidad por Envasar',mlB!=null?mlf(mlB):'—')+
        fld('Densidad Bulk',densi?(densi.toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'—')+
        fld('Supervisado por',esc(h.supervisado_por||'—'))+
      '</div>'+
      '<div class="btnrow">'+
        '<a class="bt bt-add" href="/planta/instrucciones-envasado/'+EBR_ID+'">&#9654; Instrucciones de Envasado</a>'+
        ((d.mi_rol&&d.mi_rol.puede_ejecutar&&(estado==='iniciado'||estado==='en_proceso'))?'<button class="bt bt-pdf" onclick="terminarLote()" title="Operario: termina el lote (cantidad real · todos los pasos completos)">&#10003; Terminar lote</button>':'')+
        ((d.mi_rol&&d.mi_rol.puede_liberar&&(estado==='completado'||estado==='en_revision_qc'))?'<button class="bt bt-add" onclick="liberarLote()" style="background:var(--cx-success,#15803d)" title="Calidad/Aseguramiento: libera el lote con e-firma (cierra el batch record)">&#128275; Liberar lote</button>':'')+
        '<button class="bt bt-pdf" onclick="adicionarLote()">+ Adicionar Lote</button>'+
        '<a class="bt bt-pdf" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
        ((d.mi_rol&&d.mi_rol.puede_aprobar)?'<button class="bt bt-pdf" onclick="regenerarMBR()" title="Crea una nueva versión del MBR con los pasos de envasado actualizados (GMP · obsoleta el anterior · solo Calidad/Dirección Técnica)">&#8635; Regenerar MBR</button>':'')+
        '<a class="bt bt-back" href="/inventarios#envasado">&#9198; Atrás</a>'+
      '</div>';
    window._prod=h.producto||h.titulo||''; window._lote=h.lote_codigo||'';
    // Paso 2 · Lotes de Producto por Presentación + Materiales de Envase (tal cual MyBatch).
    function ar(){return '<span class="ar">&#8645;</span>';}
    var pres=d.envasado_presentaciones||[];
    window._pres=pres;
    var puedeEdPres=(estado!=='liberado'&&estado!=='rechazado');
    var totUds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    var totCant=pres.reduce(function(a,p){return a+(Number(p.cantidad_ml)||0);},0);
    var presRows=pres.length
      ? pres.map(function(p,i){
          var acc='<a class="ab ab-play" href="/planta/instrucciones-envasado/'+EBR_ID+'" title="Ejecutar / Instrucciones de Envasado">&#9654;</a>';
          if(puedeEdPres){
            acc+='<button class="ab ab-ed" onclick="presModal('+i+')" title="Editar">&#9998;</button>';
            if(p.id){acc='<button class="ab ab-x" onclick="borrarPres('+p.id+')" title="Eliminar">&#215;</button>'+acc;}
          }
          return '<tr>'+
            '<td>'+esc(p.presentacion||'—')+(p.cliente?' <span style="color:#94a3b8;font-size:11px">· '+esc(p.cliente)+'</span>':'')+(p.fuente==='manual'?' <span style="color:#7c3aed;font-size:10px;font-weight:700">·manual</span>':'')+'</td>'+
            '<td class="mono">'+esc(p.lote||'—')+'</td>'+
            '<td>'+(p.unidades!=null?Number(p.unidades).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+esc(p.area||'—')+'</td>'+
            '<td>'+(p.cantidad_ml!=null?mlf(p.cantidad_ml):'')+'</td>'+
            '<td>'+(p.unidades_final!=null?Number(p.unidades_final).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+(p.rend_pct!=null?(Number(p.rend_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%'):'')+'</td>'+
            '<td>'+esc(p.estado||'—')+'</td>'+
            '<td><div class="act">'+acc+'</div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="9" class="muted" style="text-align:center;background:#fff">Sin presentaciones registradas aún.</td></tr>';
    var presCard='<div class="card"><div class="sechead" style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div class="sectit">Lotes de Producto por Presentación</div>'+
      (puedeEdPres?'<button class="bt bt-pdf" onclick="presModal(-1)" title="Agregar una presentación a mano (por si no cargó del plan)">+ Presentación</button>':'')+'</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>Presentación'+ar()+'</th><th>N° de lote'+ar()+'</th><th>Unid.'+ar()+'</th><th>Área/Línea'+ar()+'</th><th>Cantidad'+ar()+'</th><th>Unid. final'+ar()+'</th><th>%Rend.'+ar()+'</th><th>Estado'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+presRows+'</tbody>'+
      (pres.length?('<tfoot><tr><td><b>Total</b></td><td></td><td>'+totUds.toLocaleString('es-CO')+'</td><td></td><td>'+(totCant>0?mlf(totCant):'')+'</td><td></td><td></td><td></td><td></td></tr></tfoot>'):'')+
      '</table></div>'+
      '<div class="regfoot">Mostrando '+pres.length+' de '+pres.length+' registro'+(pres.length===1?'':'s')+'</div></div>';
    var mats=d.envasado_materiales||[];
    window._mats=mats;
    var puedeEditarMat=(estado!=='liberado'&&estado!=='rechazado');
    function mc(v){return v!=null?Number(v).toLocaleString('es-CO'):'';}
    var matRows=mats.length
      ? mats.map(function(m,i){
          var acc='<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';
          if(puedeEditarMat){
            acc='<button class="ab ab-ed" onclick="matModal('+i+')" title="Editar / registrar cantidades">&#9998;</button>'+acc;
            if(m.id){acc='<button class="ab ab-x" onclick="borrarMat('+m.id+')" title="Eliminar">&#215;</button>'+acc;}
          }
          return '<tr>'+
            '<td class="mono">'+esc(m.lote_envasado||'—')+'</td>'+
            '<td>'+esc(m.material||'—')+(m.fuente==='manual'?' <span style="color:#7c3aed;font-size:10px;font-weight:700">·manual</span>':'')+'</td>'+
            '<td class="mono">'+esc(m.lote_material||'—')+'</td>'+
            '<td>'+mc(m.requerida)+'</td>'+
            '<td>'+mc(m.devuelta)+'</td>'+
            '<td>'+mc(m.utilizada)+'</td>'+
            '<td>'+mc(m.averiada)+'</td>'+
            '<td>'+mc(m.diferencia)+'</td>'+
            '<td><div class="act">'+acc+'</div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="9" class="muted" style="text-align:center;background:#fff">Sin materiales de envase registrados aún.</td></tr>';
    var matCard='<div class="card"><div class="sechead" style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div class="sectit">Materiales de Envase</div>'+
      (puedeEditarMat?'<button class="bt bt-pdf" onclick="matModal(-1)" title="Elegir un material de envase del catálogo completo">+ Material de envase</button>':'')+'</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>N° lote envasado'+ar()+'</th><th>Material de envase'+ar()+'</th><th>N° de lote material'+ar()+'</th><th>Cant. requerida'+ar()+'</th><th>Cant. devuelta'+ar()+'</th><th>Cant. utilizada'+ar()+'</th><th>Cant. averiada'+ar()+'</th><th>Diferencia'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    document.getElementById('cuerpo').innerHTML = presCard + matCard;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error de red: '+esc(e.message)+'</span>';}
}
function adicionarLote(){alert('“Adicionar Lote” lo construimos en el siguiente paso.');}
async function regenerarMBR(){
  var prod=(window._prod||'');
  if(!prod){alert('No identifiqué el producto.');return;}
  if(!confirm('¿Regenerar el MBR de "'+prod+'" con los pasos de envasado actualizados (los 5 reales) y abrir un legajo NUEVO para verlos?\\n\\nObsoleta el MBR anterior (forma GMP correcta · queda auditado).'))return;
  try{
    var r=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod,regenerar:true})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo regenerar: '+((d&&d.error)||r.status));return;}
    // Crea un legajo nuevo (lote + sufijo) que clona la versión nueva del MBR → 5 pasos.
    var base=(window._lote||prod).replace(/-R\\d+$/,'');
    var nuevoLote=base+'-R'+(Math.floor(Date.now()/1000)%100000);
    var rl=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:nuevoLote,fase:'envasado'})});
    var dl=await rl.json();
    if(rl.ok&&dl.ok&&dl.id){location.href='/planta/legajo-envasado/'+dl.id;return;}
    alert('✅ MBR regenerado (v'+(d.version||'?')+'). No pude abrir el legajo nuevo automáticamente; créalo desde Envasado.');
  }catch(e){alert('Error: '+(e.message||e));}
}
async function terminarLote(){
  // Operario · termina el lote (cantidad real · requiere todos los pasos completos).
  var cant=prompt('Terminar el lote · cantidad real producida (g):');
  if(cant===null)return; cant=parseFloat(cant);
  if(!cant||cant<=0){alert('Cantidad inválida');return;}
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({cantidad_real_g:cant})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo terminar: '+(d.error||r.status));return;}
    alert('✅ Lote terminado. Ahora Calidad/Aseguramiento puede liberarlo.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function liberarLote(){
  // Calidad/Aseguramiento · libera el lote con e-firma (cierra el batch record · Part 11).
  if(!confirm('¿LIBERAR el lote? Cierra el batch record con tu firma electrónica (Calidad / Aseguramiento · queda auditado · 21 CFR Part 11).'))return;
  try{
    var rf=await fetch('/api/brd/ebr/'+EBR_ID+'/firmar-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({meaning:'libera'})});
    var df=await rf.json();
    if(!rf.ok||!df.ok){alert('No se pudo firmar la liberación: '+((df&&df.error)||rf.status));return;}
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/liberar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({signature_id:df.signature_id})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo liberar: '+((d&&d.error)||r.status));return;}
    alert('✅ Lote LIBERADO. Batch record cerrado.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
var _envOpc=null;
async function cargarEnvaseOpc(){
  if(_envOpc)return _envOpc;
  try{var r=await fetch('/api/brd/envase-opciones',{credentials:'same-origin'});var d=await r.json();_envOpc=(d&&d.opciones)||[];}catch(e){_envOpc=[];}
  return _envOpc;
}
async function matModal(i){
  var m=(i>=0&&window._mats)?window._mats[i]:null;
  var opc=await cargarEnvaseOpc();
  var ov=document.getElementById('matov');
  if(!ov){ov=document.createElement('div');ov.id='matov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  var selCod=(m&&m.material_codigo)||'';
  var opciones='<option value="">— elegí un material de envase —</option>'+opc.map(function(o){return '<option value="'+esc(o.codigo)+'"'+(o.codigo===selCod?' selected':'')+'>'+esc(o.label)+'</option>';}).join('');
  function v(x){return (x==null?'':x);}
  ov.innerHTML='<div style="background:#fff;border-radius:14px;padding:22px;max-width:520px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:17px;margin-bottom:14px">'+(m?'Editar material de envase':'Agregar material de envase')+'</div>'+
    '<input type="hidden" id="m_id" value="'+v(m&&m.id)+'">'+
    '<label style="font-size:12px;color:#475569;font-weight:600">Material de envase (catálogo completo)</label>'+
    '<select id="m_cod" style="width:100%;padding:9px;margin:4px 0 12px;border:1px solid #cbd5e1;border-radius:8px">'+opciones+'</select>'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">N° lote material</label><input id="m_lote" value="'+esc(v(m&&m.lote_material))+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Cant. requerida</label><input id="m_req" type="number" value="'+v(m&&m.requerida)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Cant. devuelta</label><input id="m_dev" type="number" value="'+v(m&&m.devuelta)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Cant. utilizada</label><input id="m_uti" type="number" value="'+v(m&&m.utilizada)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Cant. averiada</label><input id="m_ave" type="number" value="'+v(m&&m.averiada)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">'+
      '<button onclick="cerrarMat()" style="padding:9px 16px;border:1px solid #cbd5e1;background:#f1f5f9;border-radius:8px;cursor:pointer">Cancelar</button>'+
      '<button onclick="guardarMat()" style="padding:9px 16px;border:0;background:#7c3aed;color:#fff;border-radius:8px;cursor:pointer;font-weight:700">Guardar</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarMat(){var ov=document.getElementById('matov');if(ov)ov.style.display='none';}
async function guardarMat(){
  var cod=document.getElementById('m_cod').value;
  if(!cod){alert('Elegí un material del desplegable.');return;}
  function n(id){var x=document.getElementById(id).value;return x===''?null:parseFloat(x);}
  var body={material_codigo:cod,lote_material:document.getElementById('m_lote').value,requerida:n('m_req'),devuelta:n('m_dev'),utilizada:n('m_uti'),averiada:n('m_ave')};
  var idv=document.getElementById('m_id').value;if(idv)body.id=parseInt(idv,10);
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/material-envase',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo guardar: '+((d&&d.error)||r.status));return;}
    cerrarMat();load();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function borrarMat(id){
  if(!confirm('¿Eliminar este material de envase agregado a mano?'))return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/material-envase/'+id,{method:'DELETE',credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo eliminar: '+((d&&d.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
}
function presModal(i){
  var p=(i>=0&&window._pres)?window._pres[i]:null;
  var ov=document.getElementById('presov');
  if(!ov){ov=document.createElement('div');ov.id='presov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  function v(x){return (x==null?'':x);}
  ov.innerHTML='<div style="background:#fff;border-radius:14px;padding:22px;max-width:520px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:17px;margin-bottom:14px">'+(p?'Editar presentación':'Agregar presentación')+'</div>'+
    '<input type="hidden" id="p_id" value="'+v(p&&p.id)+'">'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Presentación *</label><input id="p_pres" value="'+esc(v(p&&p.presentacion))+'" placeholder="ej. 30 ml" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Cliente</label><input id="p_cli" value="'+esc(v((p&&p.cliente)||"Animus DTC"))+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Unidades</label><input id="p_uds" type="number" value="'+v(p&&p.unidades)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Volumen (mL/ud)</label><input id="p_vol" type="number" value="'+v(p&&p.volumen_ml)+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:#475569;font-weight:600">Área/Línea</label><input id="p_area" value="'+esc(v(p&&p.area))+'" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">'+
      '<button onclick="cerrarPres()" style="padding:9px 16px;border:1px solid #cbd5e1;background:#f1f5f9;border-radius:8px;cursor:pointer">Cancelar</button>'+
      '<button onclick="guardarPres()" style="padding:9px 16px;border:0;background:#7c3aed;color:#fff;border-radius:8px;cursor:pointer;font-weight:700">Guardar</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarPres(){var ov=document.getElementById('presov');if(ov)ov.style.display='none';}
async function guardarPres(){
  var pres=document.getElementById('p_pres').value.trim();
  if(!pres){alert('Indicá la presentación (ej. 30 ml).');return;}
  function n(id){var x=document.getElementById(id).value;return x===''?null:parseFloat(x);}
  var body={presentacion:pres,cliente:document.getElementById('p_cli').value,unidades:n('p_uds'),volumen_ml:n('p_vol'),area:document.getElementById('p_area').value};
  var idv=document.getElementById('p_id').value;if(idv)body.id=parseInt(idv,10);
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/presentacion',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo guardar: '+((d&&d.error)||r.status));return;}
    cerrarPres();load();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function borrarPres(id){
  if(!confirm('¿Eliminar esta presentación agregada a mano?'))return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/presentacion/'+id,{method:'DELETE',credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo eliminar: '+((d&&d.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
load();
</script>
</body></html>"""


@bp.route("/planta/legajo-envasado/<int:ebr_id>", methods=["GET"])
def legajo_envasado_page(ebr_id):
    """Legajo de Envasado · página PROPIA, aislada de producción · se construye paso a
    paso con Sebastián (9-jun-2026). Reusa vista-completa para la cabecera."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/legajo-envasado/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_ENVASADO_LEGAJO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_ACOND_LEGAJO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Acondicionamiento · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.ortit{font-size:26px;font-weight:800;color:var(--cx-text,#18181b);margin:6px 0 6px;letter-spacing:-.4px}
.prod{color:var(--cx-text-mute,#71717a);font-size:17px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px 22px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:14px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.btnrow{display:flex;gap:12px;justify-content:flex-start;flex-wrap:wrap;margin-top:24px}
.bt{padding:11px 20px;border-radius:10px;font-size:13px;font-weight:600;border:1px solid transparent;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:all .15s ease}
.bt-add{background:var(--cx-primary,#6d28d9);color:#fff}.bt-add:hover{background:var(--cx-primary-dark,#4c1d95)}
.bt-pdf{background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);border-color:var(--cx-border,#e6e6ea)}.bt-pdf:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary,#6d28d9)}
.bt-back{background:transparent;color:var(--cx-text-mute,#71717a);border-color:var(--cx-border,#e6e6ea)}.bt-back:hover{background:var(--cx-bg-alt,#fbfbfd)}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 16px}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:13px 12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t thead th .ar{color:var(--cx-text-faint,#a1a1aa);font-size:10px;margin-left:3px}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
table.t tfoot td{font-weight:800;color:var(--cx-text,#18181b);border-top:2px solid var(--cx-border,#e6e6ea)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.act{display:inline-flex;gap:6px;flex-wrap:wrap}
.ab{width:32px;height:32px;border-radius:8px;border:none;cursor:pointer;color:#fff;font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-play{background:var(--cx-success,#15803d)}.ab-plus{background:var(--cx-primary,#6d28d9)}.ab-x{background:var(--cx-danger,#dc2626)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-ed2{background:var(--cx-success,#15803d)}.ab-i{background:var(--cx-info,#2563eb)}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios#acondicionamiento">&larr; Acondicionamiento</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function ufmt(n){return n==null?'—':Number(n).toLocaleString('es-CO');}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#b45309';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'—';
    var pres=d.acond_presentaciones||[];
    var totUds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('cab').innerHTML=
      '<div class="ortit">ORDEN DE ACONDICIONAMIENTO N°: '+esc(h.numero_op||('OA-'+EBR_ID))+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'—')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div style="margin:-10px 0 18px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div>'+
      '<div class="grid">'+
        fld('N° Lote','<span class="mono">'+esc(h.lote_codigo||'—')+'</span>')+
        fld('Unidades acondicionadas',ufmt(totUds))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
        fld('Elaborado por',esc(h.operario||'—'))+
        fld('Observaciones',esc(h.observaciones||'Ninguna'))+
        fld('Área / Línea',esc(h.area_linea||'—'))+
        fld('Supervisado por',esc(h.supervisado_por||'—'))+
        fld('Liberado por',esc(h.liberado_por_full||'—'))+
      '</div>'+
      '<div class="btnrow">'+
        '<a class="bt bt-add" href="/planta/instrucciones-acondicionamiento/'+EBR_ID+'">&#9654; Instrucciones de Acondicionamiento</a>'+
        ((d.mi_rol&&d.mi_rol.puede_ejecutar&&(estado==='iniciado'||estado==='en_proceso'))?'<button class="bt bt-pdf" onclick="terminarLote()" title="Operario: termina el acondicionamiento (todos los pasos completos)">&#10003; Terminar</button>':'')+
        ((d.mi_rol&&d.mi_rol.puede_liberar&&(estado==='completado'||estado==='en_revision_qc'))?'<button class="bt bt-add" onclick="liberarLote()" style="background:var(--cx-success,#15803d)" title="Calidad/Aseguramiento: libera el lote con e-firma (cierra el batch record)">&#128275; Liberar lote</button>':'')+
        '<a class="bt bt-pdf" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
        ((d.mi_rol&&d.mi_rol.puede_aprobar)?'<button class="bt bt-pdf" onclick="regenerarMBR()" title="Crea una nueva versión del MBR con los pasos de acondicionamiento actualizados (GMP · obsoleta el anterior · solo Calidad/Dirección Técnica)">&#8635; Regenerar MBR</button>':'')+
        '<a class="bt bt-back" href="/inventarios#acondicionamiento">&#9198; Atrás</a>'+
      '</div>';
    window._prod=h.producto||h.titulo||''; window._lote=h.lote_codigo||'';
    function ar(){return '<span class="ar">&#8645;</span>';}
    var presRows=pres.length
      ? pres.map(function(p){
          return '<tr>'+
            '<td>'+esc(p.presentacion||'—')+(p.cliente?' <span style="color:#94a3b8;font-size:11px">· '+esc(p.cliente)+'</span>':'')+'</td>'+
            '<td class="mono">'+esc(p.lote||'—')+'</td>'+
            '<td>'+(p.unidades!=null?Number(p.unidades).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+esc(p.estado||'—')+'</td>'+
            '<td><div class="act"><a class="ab ab-play" href="/planta/instrucciones-acondicionamiento/'+EBR_ID+'" title="Ejecutar / Instrucciones de Acondicionamiento">&#9654;</a></div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="5" class="muted" style="text-align:center;background:#fff">Sin presentaciones acondicionadas aún.</td></tr>';
    var presCard='<div class="card"><div class="sectit">Unidades por Presentación</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>Presentación'+ar()+'</th><th>N° de lote'+ar()+'</th><th>Unidades'+ar()+'</th><th>Estado'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+presRows+'</tbody>'+
      (pres.length?('<tfoot><tr><td><b>Total</b></td><td></td><td>'+totUds.toLocaleString('es-CO')+'</td><td></td><td></td></tr></tfoot>'):'')+
      '</table></div>'+
      '<div class="regfoot">Mostrando '+pres.length+' de '+pres.length+' registro'+(pres.length===1?'':'s')+'</div></div>';
    var mats=d.acond_materiales||[];
    function mc(v){return v!=null?Number(v).toLocaleString('es-CO'):'';}
    var matRows=mats.length
      ? mats.map(function(m){
          return '<tr>'+
            '<td class="mono">'+esc(m.lote_acond||'—')+'</td>'+
            '<td>'+esc(m.material||'—')+'</td>'+
            '<td class="mono">'+esc(m.lote_material||'—')+'</td>'+
            '<td>'+mc(m.requerida)+'</td>'+
            '<td>'+mc(m.devuelta)+'</td>'+
            '<td>'+mc(m.utilizada)+'</td>'+
            '<td>'+mc(m.averiada)+'</td>'+
            '<td>'+mc(m.diferencia)+'</td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="8" class="muted" style="text-align:center;background:#fff">Sin materiales de empaque registrados aún.</td></tr>';
    var matCard='<div class="card"><div class="sectit">Materiales de Empaque</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>N° lote acond.'+ar()+'</th><th>Material de empaque'+ar()+'</th><th>N° de lote material'+ar()+'</th><th>Cant. requerida'+ar()+'</th><th>Cant. devuelta'+ar()+'</th><th>Cant. utilizada'+ar()+'</th><th>Cant. averiada'+ar()+'</th><th>Diferencia'+ar()+'</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    document.getElementById('cuerpo').innerHTML = presCard + matCard;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error de red: '+esc(e.message)+'</span>';}
}
async function regenerarMBR(){
  var prod=(window._prod||'');
  if(!prod){alert('No identifiqué el producto.');return;}
  if(!confirm('¿Regenerar el MBR de "'+prod+'" con los pasos de acondicionamiento actualizados y abrir un legajo NUEVO para verlos?\\n\\nObsoleta el MBR anterior (forma GMP correcta · queda auditado).'))return;
  try{
    var r=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod,regenerar:true})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo regenerar: '+((d&&d.error)||r.status));return;}
    var base=(window._lote||prod).replace(/-R\\d+$/,'');
    var nuevoLote=base+'-OA'+(Math.floor(Date.now()/1000)%100000);
    var rl=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:nuevoLote,fase:'acondicionamiento'})});
    var dl=await rl.json();
    if(rl.ok&&dl.ok&&dl.id){location.href='/planta/legajo-acondicionamiento/'+dl.id;return;}
    alert('✅ MBR regenerado (v'+(d.version||'?')+'). No pude abrir el legajo nuevo automáticamente; créalo desde Acondicionamiento.');
  }catch(e){alert('Error: '+(e.message||e));}
}
async function terminarLote(){
  var cant=prompt('Terminar el acondicionamiento · cantidad real (g, opcional · Enter para usar el objetivo):');
  if(cant===null)return;
  var body={};
  if(String(cant).trim()!==''){var n=parseFloat(cant);if(n>0)body.cantidad_real_g=n;}
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert('No se pudo terminar: '+(d.error||r.status));return;}
    alert('✅ Acondicionamiento terminado. Ahora Calidad/Aseguramiento puede liberarlo.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function liberarLote(){
  if(!confirm('¿LIBERAR el lote? Cierra el batch record con tu firma electrónica (Calidad / Aseguramiento · queda auditado · 21 CFR Part 11).'))return;
  try{
    var rf=await fetch('/api/brd/ebr/'+EBR_ID+'/firmar-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({meaning:'libera'})});
    var df=await rf.json();
    if(!rf.ok||!df.ok){alert('No se pudo firmar la liberación: '+((df&&df.error)||rf.status));return;}
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/liberar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({signature_id:df.signature_id})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo liberar: '+((d&&d.error)||r.status));return;}
    alert('✅ Lote LIBERADO. Batch record cerrado.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
load();
</script>
</body></html>"""


@bp.route("/planta/legajo-acondicionamiento/<int:ebr_id>", methods=["GET"])
def legajo_acondicionamiento_page(ebr_id):
    """Legajo de Acondicionamiento (OA) · página propia, aislada de producción ·
    espeja el legajo de envasado (10-jun-2026). Reusa vista-completa."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/legajo-acondicionamiento/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_ACOND_LEGAJO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_INSTRUCCIONES_ENVASADO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Instrucciones de Envasado · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.htop{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.htit{font-size:25px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.4px}
.btns{display:flex;gap:10px;flex-wrap:wrap}
.bt{padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;border:1px solid var(--cx-border,#e6e6ea);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);transition:all .15s ease}
.bt:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary,#6d28d9)}
.bt-up{background:var(--cx-primary,#6d28d9);color:#fff;border-color:transparent}.bt-up:hover{background:var(--cx-primary-dark,#4c1d95);color:#fff}
.subl{font-size:16px;color:var(--cx-text-soft,#3f3f46);font-weight:600;margin:2px 0 4px}
.prod{font-size:17px;color:var(--cx-text,#18181b);font-weight:700;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:13.5px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 12px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.sechead{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;margin-bottom:6px}
.sechead .sectit{margin:0}
.sechint{font-size:13.5px;color:var(--cx-text-mute,#71717a);margin:6px 0 14px;line-height:1.5}
.btreg{padding:9px 15px;border-radius:9px;font-size:12px;font-weight:600;border:none;cursor:pointer;background:var(--cx-primary,#6d28d9);color:#fff;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}.btreg:hover{background:var(--cx-primary-dark,#4c1d95)}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.ok{color:var(--cx-success,#15803d);font-weight:700}.no{color:var(--cx-danger,#dc2626);font-weight:700}.pend{color:var(--cx-text-faint,#a1a1aa)}
.bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.bdg-ok{background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success,#15803d)}.bdg-no{background:var(--cx-danger-pale,#fef2f2);color:var(--cx-danger,#dc2626)}
.pasonum{font-weight:700;color:var(--cx-primary,#6d28d9);margin-right:5px}
.act{display:inline-flex;gap:6px}
.ab{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-i{background:var(--cx-info,#2563eb)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-pdf{background:var(--cx-danger,#dc2626)}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/planta/legajo-envasado/__EBR_ID__">&larr; Orden de Envasado</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'—';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0||e.indexOf('complet')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#0d9488';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'—';
    var pres=d.envasado_presentaciones||[];
    var uds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('cab').innerHTML=
      '<div class="htop">'+
        '<div><div class="htit">INSTRUCCIONES DE ENVASADO</div>'+
          '<div style="margin-top:7px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div></div>'+
        '<div class="btns">'+
          '<a class="bt bt-tl" href="/brd/timeline/'+EBR_ID+'">&#9198; Timeline Batch Record</a>'+
          '<a class="bt bt-oe" href="/planta/legajo-envasado/'+EBR_ID+'">&#128196; Orden de Envase</a>'+
          '<a class="bt bt-dl" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
          '<button class="bt bt-up" onclick="location.reload()">&#8635; Actualizar</button>'+
        '</div>'+
      '</div>'+
      '<div class="subl">'+esc(h.numero_op||('OF-'+EBR_ID))+'. Lote N°: '+esc(h.lote_codigo||'—')+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'—')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div class="grid">'+
        fld('Programado por',esc(h.operario||'—'))+
        fld('Unidades',uds?uds.toLocaleString('es-CO'):'—')+
        fld('N° de Lote Bulk','<span style="font-family:ui-monospace,monospace">'+esc(h.lote_codigo||'—')+'</span>')+
        fld('Fecha Inicio',dt(h.iniciado_at_utc))+
        fld('Fecha Final',dt(h.completado_at_utc))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
      '</div>';
    var editable=(estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    function cumpleCell(c){if(c===1)return '<span class="ok">Sí &#10003;</span>';if(c===0)return '<span class="no">No &#10007;</span>';return '<span class="pend">Pendiente</span>';}
    function regBtn(t){return editable?('<button class="btreg" onclick="prox()">+ '+t+'</button>'):'';}
    function abI(){return '<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';}
    function abEd(){return editable?'<button class="ab ab-ed" onclick="prox()" title="Registrar">&#9998;</button>':'';}
    function bdgC(c){if(c===1)return ' <span class="bdg bdg-ok">Cumple</span>';if(c===0)return ' <span class="bdg bdg-no">No cumple</span>';return '';}
    var html='';
    // Leyenda de responsabilidades (segregación de funciones GMP · diseño por roles).
    html+='<div class="card" style="padding:15px 20px"><div style="font-size:13px;color:var(--cx-text-soft,#3f3f46);line-height:1.7">'+
      '<b>Responsabilidades:</b> &nbsp;'+
      '<span style="color:var(--cx-primary,#6d28d9);font-weight:800">●</span> <b>Operario</b> ejecuta y registra (precauciones, despeje, recepción, envasado). &nbsp;'+
      '<span style="color:var(--cx-success,#15803d);font-weight:800">●</span> <b>Calidad / Aseguramiento</b> verifica los controles, corrige resultados y <b>libera el lote</b>. &nbsp;'+
      '<span style="color:var(--cx-warn,#f59e0b);font-weight:800">●</span> <b>Dirección Técnica</b> aprueba el MBR.'+
      '</div></div>';
    var prec=d.precauciones||[];
    html+='<div class="card"><div class="sectit">1. Precauciones</div>'+
      '<div class="sechint">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de envasado:</div>'+
      (prec.length?('<ul style="margin:0;padding-left:18px;color:var(--cx-text-soft);font-size:13.5px;line-height:1.95">'+prec.map(function(p){return '<li><b>'+(p.tipo==='equipo'?'&#128296; Equipo':'&#9888; Precaución')+':</b> '+esc(p.descripcion||'')+'</li>';}).join('')+'</ul>'):'<div class="muted">Sin precauciones registradas (se definen en el MBR).</div>')+
      '</div>';
    var dch=d.despeje_checklist||[]; window._dch=dch;
    html+='<div class="card"><div class="sectit">2. Despejes de Línea</div>'+
      '<div class="sechint">Realizar despeje en el área de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
      (dch.length?('<div class="tw"><table class="t"><thead><tr><th>Verificación</th><th>Cumple</th><th>Acciones</th></tr></thead><tbody>'+
        dch.map(function(it){return '<tr><td>'+esc(it.texto||'')+'</td><td>'+cumpleCell(it.cumple)+'</td><td><div class="act"><button class="ab ab-i" onclick="infoDespeje('+it.idx+')" title="Detalle">i</button>'+(editable?'<button class="ab ab-ed" onclick="regDespeje('+it.idx+')" title="Registrar verificación">&#9998;</button>':'')+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin verificaciones de despeje (se definen en el MBR).</div>')+
      '</div>';
    var mats=d.envasado_materiales||[];
    html+='<div class="card"><div class="sectit">3. Recepción de Material de Envase</div>'+
      '<div class="sechint">Verificar contra la orden de envasado y la etiqueta o rótulo de identificación de los siguientes materiales de envase:</div>'+
      '<div class="tw"><table class="t"><thead><tr><th>Material</th><th>N° lote</th><th>Cant. requerida</th><th>Cant. recibida</th><th>Acciones</th></tr></thead><tbody>'+
      (mats.length?mats.map(function(m){return '<tr><td>'+esc(m.material||'—')+'</td><td class="mono">'+esc(m.lote_material||m.lote_envasado||'—')+'</td><td>'+(m.requerida!=null?Number(m.requerida).toLocaleString('es-CO'):'')+'</td><td>'+(m.recibida!=null?Number(m.recibida).toLocaleString('es-CO'):'<span class="pend">pendiente</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')
        :'<tr><td colspan="5" class="muted" style="text-align:center">Sin materiales registrados.</td></tr>')+
      '</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    var pasos=d.pasos||[]; window._pasos=pasos;
    html+='<div class="card"><div class="sechead"><div class="sectit">4. Envasado</div>'+(editable?'<button class="btreg" onclick="registrarActividades()">&#10003; Registrar Actividades</button>':'')+'</div>'+
      '<div class="sechint">Realizar las siguientes actividades de acuerdo al orden establecido:</div>'+
      (pasos.length?('<div class="tw"><table class="t"><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th>Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){var ts=p.completado?('<br><span class="muted" style="font-size:11.5px">'+dt(p.completado)+'</span>'):'';return '<tr><td><span class="pasonum">Paso '+(i+1)+'.</span>'+esc(p.descripcion||'')+'</td><td>'+(p.realizado_por_full?(esc(p.realizado_por_full)+ts):'<span class="pend">—</span>')+'</td><td>'+(p.verificado_por_full?(esc(p.verificado_por_full)+ts):'<span class="pend">—</span>')+'</td><td><div class="act"><button class="ab ab-i" onclick="infoPaso('+p.orden+')" title="Detalles de la Verificación">i</button></div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin pasos de envasado (se definen en el MBR).</div>')+
      '</div>';
    var ipc=d.ipc||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">5. Controles en Proceso</div>'+(editable?'<button class="btreg" onclick="prox()">+ Control de Volumen</button>':'')+'</div>'+
      '<div class="sechint">Realizar muestreo y registrar control en proceso:</div>'+
      (ipc.length?('<div class="tw"><table class="t"><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th>Acciones</th></tr></thead><tbody>'+
        ipc.map(function(c){var res=c.conforme===2?'<span class="bdg" style="background:var(--cx-bg-alt);color:var(--cx-text-mute)">No aplica</span>':(c.resultado?(esc(c.resultado)+bdgC(c.conforme)):'<span class="pend">pendiente</span>');return '<tr><td>'+esc(c.control||'')+(c.rango?' <span class="muted" style="font-size:11px">('+esc(c.rango)+')</span>':'')+'</td><td>'+res+'</td><td>'+esc(c.observaciones||'No aplica')+'</td><td>'+(c.realizado_por?esc(c.realizado_por_full||c.realizado_por):'<span class="pend">—</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin controles en proceso (se definen en el MBR).</div>')+
      '</div>';
    var obs=d.observaciones_proceso||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">6. Observaciones Generales del Proceso</div>'+regBtn('Registrar')+'</div>'+
      (obs.length?('<div class="tw"><table class="t"><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obs.map(function(o){return '<tr><td>'+esc(o.descripcion||'')+'</td><td>'+esc(o.registrado_por_full||o.registrado_por||'—')+'</td><td class="muted">'+dt(o.fecha)+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin observaciones registradas.</div>')+
      '</div>';
    var regs=d.registros_fisicos||[];
    html+='<div class="card"><div class="sectit">7. Registros Físicos del Proceso de Envasado</div>'+
      (regs.length?('<div class="tw"><table class="t"><thead><tr><th>Código</th><th>Descripción</th><th>Documento</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td>'+esc(g.descripcion||'')+'</td><td>'+(g.tiene_pdf?('<a class="ab ab-pdf" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" title="Ver">&#128196;</a>'):'<span class="pend">—</span>')+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin registros físicos adjuntos.</div>')+
      '</div>';
    document.getElementById('cuerpo').innerHTML=html;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error de red: '+esc(e.message)+'</span>';}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
async function regDespeje(idx){
  // Registrar la verificación de despeje (operario) · Cumple Sí/No + observación.
  // Mismo endpoint GMP que producción (e-firma/audit en el backend).
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var esCorr=(it.cumple!=null);
  var titulo=esCorr?'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)':'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar = Sí · Cancelar = No)');
  var obs=prompt('Observación'+(esCorr?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:'dispensacion'})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
function infoDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var res=it.cumple===1?'Sí cumple':(it.cumple===0?'No cumple':'Pendiente');
  alert('VERIFICACIÓN DE DESPEJE\\n\\n'+it.texto+'\\n\\nResultado: '+res+(it.observaciones?('\\nObservación: '+it.observaciones):'')+(it.registrado_por?('\\nRegistrado por: '+it.registrado_por):''));
}
function infoPaso(orden){
  // Detalles de la Verificación (sección 4 · read-only). Numera 1..N dentro de la fase.
  var pasos=(window._pasos||[]);
  var i=pasos.findIndex(function(x){return x.orden===orden;}); if(i<0)return;
  var p=pasos[i];
  var est=p.completado_flag?'Completado':(p.iniciado?'En proceso':'Pendiente');
  alert('DETALLES DE LA VERIFICACIÓN\\n\\nPaso '+(i+1)+': '+p.descripcion+'\\n\\nEstado: '+est+'\\nRealizado por: '+(p.realizado_por_full||'—')+'\\nVerificado por: '+(p.verificado_por_full||'—')+(p.observaciones?('\\nObservaciones: '+p.observaciones):''));
}
async function registrarActividades(){
  // Registra (completa) la siguiente actividad pendiente · endpoint GMP con audit/e-firma.
  var pend=(window._pasos||[]).filter(function(p){return !p.completado_flag;});
  if(!pend.length){alert('Todas las actividades ya están registradas.');return;}
  var p=pend[0];
  var _i=(window._pasos||[]).findIndex(function(x){return x.orden===p.orden;});
  var obs=prompt('Registrar Paso '+(_i+1)+':\\n'+p.descripcion+'\\n\\nResultado / observación:', p.observaciones||'');
  if(obs===null)return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs||''})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
load();
</script>
</body></html>"""


@bp.route("/planta/instrucciones-envasado/<int:ebr_id>", methods=["GET"])
def instrucciones_envasado_page(ebr_id):
    """Instrucciones de Envasado · ejecución de la presentación (abre desde el ▶ de la
    Orden de Envasado) · página propia, aislada · se construye paso a paso (9-jun-2026)."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/instrucciones-envasado/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_INSTRUCCIONES_ENVASADO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_INSTRUCCIONES_ACOND_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Instrucciones de Acondicionamiento · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.htop{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.htit{font-size:25px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.4px}
.btns{display:flex;gap:10px;flex-wrap:wrap}
.bt{padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;border:1px solid var(--cx-border,#e6e6ea);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);transition:all .15s ease}
.bt:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary,#6d28d9)}
.bt-up{background:var(--cx-primary,#6d28d9);color:#fff;border-color:transparent}.bt-up:hover{background:var(--cx-primary-dark,#4c1d95);color:#fff}
.subl{font-size:16px;color:var(--cx-text-soft,#3f3f46);font-weight:600;margin:2px 0 4px}
.prod{font-size:17px;color:var(--cx-text,#18181b);font-weight:700;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:13.5px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 12px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.sechead{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;margin-bottom:6px}
.sechead .sectit{margin:0}
.sechint{font-size:13.5px;color:var(--cx-text-mute,#71717a);margin:6px 0 14px;line-height:1.5}
.btreg{padding:9px 15px;border-radius:9px;font-size:12px;font-weight:600;border:none;cursor:pointer;background:var(--cx-primary,#6d28d9);color:#fff;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}.btreg:hover{background:var(--cx-primary-dark,#4c1d95)}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.ok{color:var(--cx-success,#15803d);font-weight:700}.no{color:var(--cx-danger,#dc2626);font-weight:700}.pend{color:var(--cx-text-faint,#a1a1aa)}
.bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.bdg-ok{background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success,#15803d)}.bdg-no{background:var(--cx-danger-pale,#fef2f2);color:var(--cx-danger,#dc2626)}
.pasonum{font-weight:700;color:var(--cx-primary,#6d28d9);margin-right:5px}
.act{display:inline-flex;gap:6px}
.ab{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-i{background:var(--cx-info,#2563eb)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-pdf{background:var(--cx-danger,#dc2626)}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/planta/legajo-acondicionamiento/__EBR_ID__">&larr; Orden de Acondicionamiento</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'—';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0||e.indexOf('complet')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#0d9488';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'—';
    var pres=d.acond_presentaciones||[];
    var uds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('cab').innerHTML=
      '<div class="htop">'+
        '<div><div class="htit">INSTRUCCIONES DE ACONDICIONAMIENTO</div>'+
          '<div style="margin-top:7px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div></div>'+
        '<div class="btns">'+
          '<a class="bt bt-tl" href="/brd/timeline/'+EBR_ID+'">&#9198; Timeline Batch Record</a>'+
          '<a class="bt bt-oe" href="/planta/legajo-acondicionamiento/'+EBR_ID+'">&#128196; Orden de Acondicionamiento</a>'+
          '<a class="bt bt-dl" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
          '<button class="bt bt-up" onclick="location.reload()">&#8635; Actualizar</button>'+
        '</div>'+
      '</div>'+
      '<div class="subl">'+esc(h.numero_op||('OA-'+EBR_ID))+'. Lote N°: '+esc(h.lote_codigo||'—')+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'—')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div class="grid">'+
        fld('Programado por',esc(h.operario||'—'))+
        fld('Unidades',uds?uds.toLocaleString('es-CO'):'—')+
        fld('N° de Lote','<span style="font-family:ui-monospace,monospace">'+esc(h.lote_codigo||'—')+'</span>')+
        fld('Fecha Inicio',dt(h.iniciado_at_utc))+
        fld('Fecha Final',dt(h.completado_at_utc))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
      '</div>';
    var editable=(estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    function cumpleCell(c){if(c===1)return '<span class="ok">Sí &#10003;</span>';if(c===0)return '<span class="no">No &#10007;</span>';return '<span class="pend">Pendiente</span>';}
    function regBtn(t){return editable?('<button class="btreg" onclick="prox()">+ '+t+'</button>'):'';}
    function abI(){return '<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';}
    function abEd(){return editable?'<button class="ab ab-ed" onclick="prox()" title="Registrar">&#9998;</button>':'';}
    function bdgC(c){if(c===1)return ' <span class="bdg bdg-ok">Cumple</span>';if(c===0)return ' <span class="bdg bdg-no">No cumple</span>';return '';}
    var html='';
    html+='<div class="card" style="padding:15px 20px"><div style="font-size:13px;color:var(--cx-text-soft,#3f3f46);line-height:1.7">'+
      '<b>Responsabilidades:</b> &nbsp;'+
      '<span style="color:var(--cx-primary,#6d28d9);font-weight:800">●</span> <b>Operario</b> ejecuta y registra (despeje, recepción de empaque, etiquetado, encajado). &nbsp;'+
      '<span style="color:var(--cx-success,#15803d);font-weight:800">●</span> <b>Calidad / Aseguramiento</b> verifica los controles, corrige resultados y <b>libera el lote</b>. &nbsp;'+
      '<span style="color:var(--cx-warn,#f59e0b);font-weight:800">●</span> <b>Dirección Técnica</b> aprueba el MBR.'+
      '</div></div>';
    var prec=d.precauciones||[];
    html+='<div class="card"><div class="sectit">1. Precauciones</div>'+
      '<div class="sechint">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de acondicionamiento:</div>'+
      (prec.length?('<ul style="margin:0;padding-left:18px;color:var(--cx-text-soft);font-size:13.5px;line-height:1.95">'+prec.map(function(p){return '<li><b>'+(p.tipo==='equipo'?'&#128296; Equipo':'&#9888; Precaución')+':</b> '+esc(p.descripcion||'')+'</li>';}).join('')+'</ul>'):'<div class="muted">Sin precauciones registradas (se definen en el MBR).</div>')+
      '</div>';
    var dch=d.despeje_checklist||[]; window._dch=dch;
    html+='<div class="card"><div class="sectit">2. Despeje de Área</div>'+
      '<div class="sechint">Realizar despeje en el área de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
      (dch.length?('<div class="tw"><table class="t"><thead><tr><th>Verificación</th><th>Cumple</th><th>Acciones</th></tr></thead><tbody>'+
        dch.map(function(it){return '<tr><td>'+esc(it.texto||'')+'</td><td>'+cumpleCell(it.cumple)+'</td><td><div class="act"><button class="ab ab-i" onclick="infoDespeje('+it.idx+')" title="Detalle">i</button>'+(editable?'<button class="ab ab-ed" onclick="regDespeje('+it.idx+')" title="Registrar verificación">&#9998;</button>':'')+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin verificaciones de despeje (se definen en el MBR).</div>')+
      '</div>';
    var mats=d.acond_materiales||[];
    html+='<div class="card"><div class="sectit">3. Recepción de Material de Empaque</div>'+
      '<div class="sechint">Verificar contra la orden de acondicionamiento y la etiqueta o rótulo de identificación de los siguientes materiales de empaque (etiquetas, plegadizas, insertos):</div>'+
      '<div class="tw"><table class="t"><thead><tr><th>Material</th><th>N° lote</th><th>Cant. requerida</th><th>Cant. recibida</th><th>Acciones</th></tr></thead><tbody>'+
      (mats.length?mats.map(function(m){return '<tr><td>'+esc(m.material||'—')+'</td><td class="mono">'+esc(m.lote_material||m.lote_acond||'—')+'</td><td>'+(m.requerida!=null?Number(m.requerida).toLocaleString('es-CO'):'')+'</td><td><span class="pend">pendiente</span></td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')
        :'<tr><td colspan="5" class="muted" style="text-align:center">Sin materiales registrados.</td></tr>')+
      '</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    var pasos=d.pasos||[]; window._pasos=pasos;
    html+='<div class="card"><div class="sechead"><div class="sectit">4. Acondicionamiento</div>'+(editable?'<button class="btreg" onclick="registrarActividades()">&#10003; Registrar Actividades</button>':'')+'</div>'+
      '<div class="sechint">Realizar las siguientes actividades de acuerdo al orden establecido:</div>'+
      (pasos.length?('<div class="tw"><table class="t"><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th>Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){var ts=p.completado?('<br><span class="muted" style="font-size:11.5px">'+dt(p.completado)+'</span>'):'';return '<tr><td><span class="pasonum">Paso '+(i+1)+'.</span>'+esc(p.descripcion||'')+'</td><td>'+(p.realizado_por_full?(esc(p.realizado_por_full)+ts):'<span class="pend">—</span>')+'</td><td>'+(p.verificado_por_full?(esc(p.verificado_por_full)+ts):'<span class="pend">—</span>')+'</td><td><div class="act"><button class="ab ab-i" onclick="infoPaso('+p.orden+')" title="Detalles de la Verificación">i</button></div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin pasos de acondicionamiento (se definen en el MBR).</div>')+
      '</div>';
    var ipc=d.ipc||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">5. Controles en Proceso</div>'+(editable?'<button class="btreg" onclick="prox()">+ Control</button>':'')+'</div>'+
      '<div class="sechint">Realizar muestreo y registrar control en proceso:</div>'+
      (ipc.length?('<div class="tw"><table class="t"><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th>Acciones</th></tr></thead><tbody>'+
        ipc.map(function(c){var res=c.conforme===2?'<span class="bdg" style="background:var(--cx-bg-alt);color:var(--cx-text-mute)">No aplica</span>':(c.resultado?(esc(c.resultado)+bdgC(c.conforme)):'<span class="pend">pendiente</span>');return '<tr><td>'+esc(c.control||'')+(c.rango?' <span class="muted" style="font-size:11px">('+esc(c.rango)+')</span>':'')+'</td><td>'+res+'</td><td>'+esc(c.observaciones||'No aplica')+'</td><td>'+(c.realizado_por?esc(c.realizado_por_full||c.realizado_por):'<span class="pend">—</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin controles en proceso (se definen en el MBR).</div>')+
      '</div>';
    var obs=d.observaciones_proceso||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">6. Observaciones Generales del Proceso</div>'+regBtn('Registrar')+'</div>'+
      (obs.length?('<div class="tw"><table class="t"><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obs.map(function(o){return '<tr><td>'+esc(o.descripcion||'')+'</td><td>'+esc(o.registrado_por_full||o.registrado_por||'—')+'</td><td class="muted">'+dt(o.fecha)+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin observaciones registradas.</div>')+
      '</div>';
    var regs=d.registros_fisicos||[];
    html+='<div class="card"><div class="sectit">7. Registros Físicos del Proceso de Acondicionamiento</div>'+
      (regs.length?('<div class="tw"><table class="t"><thead><tr><th>Código</th><th>Descripción</th><th>Documento</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td>'+esc(g.descripcion||'')+'</td><td>'+(g.tiene_pdf?('<a class="ab ab-pdf" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" title="Ver">&#128196;</a>'):'<span class="pend">—</span>')+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin registros físicos adjuntos.</div>')+
      '</div>';
    document.getElementById('cuerpo').innerHTML=html;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:#b91c1c">Error de red: '+esc(e.message)+'</span>';}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
async function regDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var esCorr=(it.cumple!=null);
  var titulo=esCorr?'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)':'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar = Sí · Cancelar = No)');
  var obs=prompt('Observación'+(esCorr?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:'dispensacion'})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
function infoDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var res=it.cumple===1?'Sí cumple':(it.cumple===0?'No cumple':'Pendiente');
  alert('VERIFICACIÓN DE DESPEJE\\n\\n'+it.texto+'\\n\\nResultado: '+res+(it.observaciones?('\\nObservación: '+it.observaciones):'')+(it.registrado_por?('\\nRegistrado por: '+it.registrado_por):''));
}
function infoPaso(orden){
  var pasos=(window._pasos||[]);
  var i=pasos.findIndex(function(x){return x.orden===orden;}); if(i<0)return;
  var p=pasos[i];
  var est=p.completado_flag?'Completado':(p.iniciado?'En proceso':'Pendiente');
  alert('DETALLES DE LA VERIFICACIÓN\\n\\nPaso '+(i+1)+': '+p.descripcion+'\\n\\nEstado: '+est+'\\nRealizado por: '+(p.realizado_por_full||'—')+'\\nVerificado por: '+(p.verificado_por_full||'—')+(p.observaciones?('\\nObservaciones: '+p.observaciones):''));
}
async function registrarActividades(){
  var pend=(window._pasos||[]).filter(function(p){return !p.completado_flag;});
  if(!pend.length){alert('Todas las actividades ya están registradas.');return;}
  var p=pend[0];
  var _i=(window._pasos||[]).findIndex(function(x){return x.orden===p.orden;});
  var obs=prompt('Registrar Paso '+(_i+1)+':\\n'+p.descripcion+'\\n\\nResultado / observación:', p.observaciones||'');
  if(obs===null)return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs||''})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
load();
</script>
</body></html>"""


@bp.route("/planta/instrucciones-acondicionamiento/<int:ebr_id>", methods=["GET"])
def instrucciones_acondicionamiento_page(ebr_id):
    """Instrucciones de Acondicionamiento (OA) · ejecución (abre desde el ▶ de la Orden
    de Acondicionamiento) · página propia, aislada · espeja envasado (10-jun-2026)."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/instrucciones-acondicionamiento/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_INSTRUCCIONES_ACOND_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


@bp.route("/api/brd/analitica-lotes", methods=["GET"])
def analitica_lotes():
    """Analítica operativa del batch (gerencia + Dirección Técnica): tiempo de ciclo, duración
    de procedimientos (cuellos de botella), rendimiento, productividad · derivado de los
    timestamps que el EBR YA captura (no inventa nada). Solo Dir.Téc/Calidad/Admin · 9-jun-2026."""
    err = _require_login()
    if err:
        return err
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS:
        return jsonify({"error": "Privado · solo Gerencia / Dirección"}), 403
    from datetime import datetime as _DT

    def _pd(s):
        if not s:
            return None
        try:
            return _DT.fromisoformat(str(s).strip().replace('Z', '').replace(' ', 'T', 1)[:26])
        except Exception:
            return None

    def _horas(a, b):
        da, db = _pd(a), _pd(b)
        if not da or not db:
            return None
        h = (db - da).total_seconds() / 3600.0
        return h if h >= 0 else None

    def _avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    conn = get_db()
    try:
        lotes = conn.execute(
            """SELECT e.id, COALESCE(e.fase,'fabricacion') AS fase,
                      COALESCE(m.producto_nombre,'') AS producto, COALESCE(e.estado,'') AS estado,
                      e.iniciado_at_utc, e.completado_at_utc, e.liberado_at_utc,
                      e.yield_pct, COALESCE(e.cantidad_objetivo_g,0) AS obj, e.cantidad_real_g
                 FROM ebr_ejecuciones e
                 LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id""").fetchall()
    except Exception:
        lotes = []
    estados, ciclo_fase, rend_prod, libera = {}, {}, {}, []
    for r in lotes:
        d = dict(r)
        est = (d.get('estado') or '').lower()
        estados[est] = estados.get(est, 0) + 1
        c = _horas(d.get('iniciado_at_utc'), d.get('completado_at_utc'))
        if c is not None:
            ciclo_fase.setdefault(d.get('fase') or 'fabricacion', []).append(c)
        y = d.get('yield_pct')
        if y is None and d.get('obj') and d.get('cantidad_real_g'):
            try:
                y = float(d['cantidad_real_g']) / float(d['obj']) * 100
            except Exception:
                y = None
        if y is not None:
            rend_prod.setdefault(d.get('producto') or '—', []).append(float(y))
        lh = _horas(d.get('completado_at_utc'), d.get('liberado_at_utc'))
        if lh is not None:
            libera.append(lh)
    try:
        pasos = conn.execute(
            """SELECT p.descripcion, COALESCE(p.operario_username,'') AS operario,
                      p.iniciado_at_utc, p.completado_at_utc
                 FROM ebr_pasos_ejecutados p
                WHERE p.completado_at_utc IS NOT NULL""").fetchall()
    except Exception:
        pasos = []
    cuellos, prod_op = {}, {}
    for r in pasos:
        d = dict(r)
        m = _horas(d.get('iniciado_at_utc'), d.get('completado_at_utc'))
        if m is not None:
            cuellos.setdefault((d.get('descripcion') or '—')[:70], []).append(m * 60.0)
        op = d.get('operario') or ''
        if op:
            prod_op[op] = prod_op.get(op, 0) + 1
    return jsonify({
        'ok': True,
        'resumen': {
            'total': len(lotes),
            'en_proceso': sum(v for k, v in estados.items() if k in ('iniciado', 'en_proceso')),
            'completados': estados.get('completado', 0) + estados.get('en_revision_qc', 0),
            'liberados': estados.get('liberado', 0),
            'rechazados': estados.get('rechazado', 0),
        },
        'ciclo_por_fase': sorted(
            [{'fase': f, 'lotes': len(v), 'ciclo_horas_prom': _avg(v)} for f, v in ciclo_fase.items()],
            key=lambda x: -(x['ciclo_horas_prom'] or 0)),
        'cuellos': sorted(
            [{'paso': p, 'n': len(v), 'duracion_min_prom': _avg(v)} for p, v in cuellos.items()],
            key=lambda x: -(x['duracion_min_prom'] or 0))[:10],
        'rendimiento': sorted(
            [{'producto': p, 'lotes': len(v), 'yield_prom': _avg(v)} for p, v in rend_prod.items()],
            key=lambda x: -(x['yield_prom'] or 0))[:12],
        'productividad': sorted(
            [{'operario': o, 'pasos': n} for o, n in prod_op.items()], key=lambda x: -x['pasos'])[:12],
        'completar_a_liberar_horas_prom': _avg(libera),
    })


_ANALITICA_BATCH_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Analítica del Batch · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;font-variant-numeric:tabular-nums}
.wrap{max-width:1200px;margin:0 auto}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
h1{font-size:24px;font-weight:800;letter-spacing:-.4px;margin:8px 0 2px}
.sub{color:var(--cx-text-mute,#71717a);font-size:13px;margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:22px}
.kpi{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:18px 20px;box-shadow:0 1px 3px rgba(24,24,27,.04)}
.kpi .v{font-size:27px;font-weight:800;color:var(--cx-text,#18181b)}
.kpi .l{font-size:11.5px;font-weight:700;color:var(--cx-text-mute,#71717a);text-transform:uppercase;letter-spacing:.4px;margin-top:2px}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:22px 26px;box-shadow:0 1px 3px rgba(24,24,27,.04);margin-bottom:18px}
.sectit{font-size:16px;font-weight:800;color:var(--cx-text,#18181b);margin:0 0 3px}
.sechint{font-size:12.5px;color:var(--cx-text-mute,#71717a);margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:11px 12px;text-align:left;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
th{color:var(--cx-text-mute,#71717a);font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
td{color:var(--cx-text-soft,#3f3f46)}
.num{text-align:right;font-weight:700}
.bar{height:8px;border-radius:6px;background:var(--cx-primary,#6d28d9);display:inline-block;vertical-align:middle}
.bartrk{background:var(--cx-primary-pale,#f5f3ff);border-radius:6px;width:122px;display:inline-block;vertical-align:middle;margin-right:8px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.cols{grid-template-columns:1fr}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/gerencia">&larr; Gerencia</a>
  <h1>&#128202; Analítica del Batch</h1>
  <div class="sub">&#128274; Privado &middot; Gerencia &nbsp;&mdash;&nbsp; tiempos, rendimiento y productividad, derivado de los registros de lote (EBR) en vivo.</div>
  <div id="cont"><div class="muted">Cargando&hellip;</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function nf(n,dec){return n==null?'—':Number(n).toLocaleString('es-CO',{maximumFractionDigits:dec==null?1:dec});}
function kpi(v,l){return '<div class="kpi"><div class="v">'+(typeof v==='number'?nf(v,0):esc(v))+'</div><div class="l">'+l+'</div></div>';}
function tbl(heads,rows){var h='<table><thead><tr>';heads.forEach(function(x,i){h+='<th'+(i>0?' class="num"':'')+'>'+esc(x)+'</th>';});h+='</tr></thead><tbody>';
  if(!rows.length){h+='<tr><td colspan="'+heads.length+'" class="muted">Sin datos aún.</td></tr>';}
  else{rows.forEach(function(r){h+='<tr>';r.forEach(function(c,i){h+='<td'+(i>0?' class="num"':'')+'>'+(c==null?'—':esc(c))+'</td>';});h+='</tr>';});}
  return h+'</tbody></table>';}
async function load(){
  try{
    var r=await fetch('/api/brd/analitica-lotes',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    if(r.status===403){document.getElementById('cont').innerHTML='<div class="card">&#128274; Privado · solo Gerencia / Dirección.</div>';return;}
    var d=await r.json();
    if(!d.ok){document.getElementById('cont').innerHTML='<div class="card" style="color:#b91c1c">Error</div>';return;}
    var R=d.resumen||{};
    var h='<div class="kpis">'+
      kpi(R.total,'Lotes totales')+kpi(R.en_proceso,'En proceso')+kpi(R.completados,'Completados')+
      kpi(R.liberados,'Liberados')+kpi(R.rechazados,'Rechazados')+
      kpi(d.completar_a_liberar_horas_prom!=null?(nf(d.completar_a_liberar_horas_prom)+' h'):'—','Completar→Liberar')+
    '</div>';
    h+='<div class="cols">';
    h+='<div class="card"><div class="sectit">&#9201;&#65039; Tiempo de ciclo por fase</div><div class="sechint">Horas promedio de inicio a completado.</div>'+
      tbl(['Fase','Lotes','Horas prom'],(d.ciclo_por_fase||[]).map(function(x){return [x.fase,x.lotes,nf(x.ciclo_horas_prom)+' h'];}))+'</div>';
    h+='<div class="card"><div class="sectit">&#128200; Rendimiento (yield) por producto</div><div class="sechint">% real vs objetivo · ¿se pierde granel?</div>'+
      tbl(['Producto','Lotes','Yield prom'],(d.rendimiento||[]).map(function(x){return [x.producto,x.lotes,nf(x.yield_prom)+'%'];}))+'</div>';
    h+='</div>';
    var cu=d.cuellos||[]; var maxc=cu.length?Math.max.apply(null,cu.map(function(x){return x.duracion_min_prom||0;})):1;
    h+='<div class="card"><div class="sectit">&#128269; Cuellos de botella · duración por procedimiento</div><div class="sechint">Los pasos que más tardan (minutos promedio). Ahí se pierde tiempo.</div>'+
      '<table><thead><tr><th>Procedimiento</th><th class="num">Veces</th><th>Duración prom</th></tr></thead><tbody>'+
      (cu.length?cu.map(function(x){var w=Math.round((x.duracion_min_prom||0)/(maxc||1)*120);return '<tr><td>'+esc(x.paso)+'</td><td class="num">'+x.n+'</td><td><span class="bartrk"><span class="bar" style="width:'+w+'px"></span></span>'+nf(x.duracion_min_prom)+' min</td></tr>';}).join(''):'<tr><td colspan="3" class="muted">Sin pasos con tiempos aún.</td></tr>')+
      '</tbody></table></div>';
    h+='<div class="card"><div class="sectit">&#128119; Productividad por operario</div><div class="sechint">Pasos ejecutados (registrados).</div>'+
      tbl(['Operario','Pasos'],(d.productividad||[]).map(function(x){return [x.operario,x.pasos];}))+'</div>';
    document.getElementById('cont').innerHTML=h;
  }catch(e){document.getElementById('cont').innerHTML='<div class="card" style="color:#b91c1c">Error de red: '+esc(e.message)+'</div>';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/analitica-batch", methods=["GET"])
def analitica_batch_page():
    """Tablero de analítica del batch (gerencia / Dirección Técnica) · premium · 9-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/analitica-batch"</script>',
                        mimetype="text/html")
    return Response(_ANALITICA_BATCH_HTML, mimetype="text/html")


@bp.route("/api/brd/mbr/<int:mbr_id>/aprobar-rapido", methods=["POST"])
def aprobar_mbr_rapido(mbr_id):
    """Aprueba un MBR en_revision con la e-firma del usuario (Bandeja DT · 9-jun). Solo
    Calidad/Dir.Téc/Admin. Crea firma 'aprueba' + estado=aprobado + audit."""
    err = _require_qa_or_admin()
    if err:
        return err
    conn = get_db(); cur = conn.cursor()
    user = session.get("compras_user", "")
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "MBR no encontrado"}), 404
    est = (row[0] if not hasattr(row, 'keys') else row['estado'])
    if est != 'en_revision':
        return jsonify({"ok": False, "error": f"solo en_revision puede aprobarse (actual: {est})"}), 409
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                 record_id=str(mbr_id), meaning="aprueba",
                                 comment="Aprobación desde bandeja DT")
    cur.execute("""UPDATE mbr_templates SET estado='aprobado', aprobado_por=?,
                     aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=?
                   WHERE id=?""", (user, sig_id, mbr_id))
    audit_log(cur, usuario=user, accion="APROBAR_MBR", tabla="mbr_templates",
              registro_id=mbr_id, antes={"estado": "en_revision"},
              despues={"estado": "aprobado", "signature_id": sig_id})
    conn.commit()
    return jsonify({"ok": True, "estado": "aprobado"})


@bp.route("/api/brd/bandeja-dt", methods=["GET"])
def bandeja_dt():
    """Bandeja del Director Técnico / Calidad: decisiones que requieren su firma · MBRs por
    aprobar + lotes por liberar (9-jun). Solo Dir.Téc/Calidad/Admin."""
    err = _require_login()
    if err:
        return err
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return jsonify({"error": "solo Dirección Técnica / Calidad / Admin"}), 403
    conn = get_db()
    try:
        mbrs = conn.execute(
            "SELECT id, COALESCE(producto_nombre,'') AS producto, COALESCE(version,1) AS version, "
            "COALESCE(creado_por,'') AS creado_por FROM mbr_templates "
            "WHERE estado='en_revision' ORDER BY id DESC LIMIT 100").fetchall()
    except Exception:
        mbrs = []
    try:
        lotes = conn.execute(
            "SELECT e.id, COALESCE(e.numero_op,'') AS numero_op, COALESCE(e.lote,'') AS lote, "
            "COALESCE(e.fase,'fabricacion') AS fase, COALESCE(m.producto_nombre,'') AS producto, "
            "COALESCE(e.completado_at_utc,'') AS completado_at FROM ebr_ejecuciones e "
            "LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id "
            "WHERE COALESCE(e.estado,'') IN ('completado','en_revision_qc') "
            "ORDER BY e.completado_at_utc DESC LIMIT 100").fetchall()
    except Exception:
        lotes = []
    return jsonify({"ok": True,
                    "mbr_pendientes": [dict(r) for r in mbrs],
                    "lotes_por_liberar": [dict(r) for r in lotes]})


_BANDEJA_DT_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bandeja · Dirección Técnica · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;font-variant-numeric:tabular-nums}
.wrap{max-width:1100px;margin:0 auto}
a.back{color:var(--cx-primary,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
h1{font-size:24px;font-weight:800;letter-spacing:-.4px;margin:8px 0 2px}
.sub{color:var(--cx-text-mute,#71717a);font-size:13px;margin-bottom:20px}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:22px 26px;box-shadow:0 1px 3px rgba(24,24,27,.04);margin-bottom:18px}
.sectit{font-size:17px;font-weight:800;color:var(--cx-text,#18181b);margin:0 0 3px}
.sectit .badge{font-size:12px;background:var(--cx-warn-pale,#fffbeb);color:var(--cx-warn,#f59e0b);font-weight:800;padding:2px 10px;border-radius:20px;margin-left:8px;vertical-align:middle}
.sechint{font-size:12.5px;color:var(--cx-text-mute,#71717a);margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:12px;text-align:left;border-bottom:1px solid var(--cx-border-soft,#f1f1f4);vertical-align:middle}
th{color:var(--cx-text-mute,#71717a);font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
td{color:var(--cx-text-soft,#3f3f46)}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.bt{padding:8px 15px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:5px;color:#fff}
.bt-ap{background:var(--cx-success,#15803d)}.bt-ver{background:var(--cx-primary,#6d28d9)}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios">&larr; Planta</a>
  <h1>&#128203; Bandeja &middot; Dirección Técnica</h1>
  <div class="sub">Decisiones que requieren tu firma &middot; aprobar procedimientos (MBR) y liberar lotes.</div>
  <div id="cont"><div class="muted">Cargando&hellip;</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'—';}
async function load(){
  try{
    var r=await fetch('/api/brd/bandeja-dt',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    if(r.status===403){document.getElementById('cont').innerHTML='<div class="card">Solo Dirección Técnica / Calidad / Admin.</div>';return;}
    var d=await r.json();
    var mbr=d.mbr_pendientes||[], lot=d.lotes_por_liberar||[];
    var h='<div class="card"><div class="sectit">&#128221; MBR por aprobar'+(mbr.length?'<span class="badge">'+mbr.length+'</span>':'')+'</div>'+
      '<div class="sechint">Procedimientos maestros en revisión esperando tu aprobación (e-firma).</div>'+
      '<table><thead><tr><th>Producto</th><th>Versión</th><th>Creado por</th><th>Acción</th></tr></thead><tbody>'+
      (mbr.length?mbr.map(function(m){return '<tr><td>'+esc(m.producto)+'</td><td>v'+esc(m.version)+'</td><td>'+esc(m.creado_por||'—')+'</td><td><button class="bt bt-ap" onclick="aprobar('+m.id+',this)">&#10003; Aprobar</button></td></tr>';}).join(''):'<tr><td colspan="4" class="muted">Nada pendiente de aprobar.</td></tr>')+
      '</tbody></table></div>';
    h+='<div class="card"><div class="sectit">&#128275; Lotes por liberar'+(lot.length?'<span class="badge">'+lot.length+'</span>':'')+'</div>'+
      '<div class="sechint">Lotes completados esperando liberación de Calidad/Dirección Técnica.</div>'+
      '<table><thead><tr><th>N&deg; orden</th><th>Producto</th><th>N&deg; lote</th><th>Fase</th><th>Completado</th><th>Acción</th></tr></thead><tbody>'+
      (lot.length?lot.map(function(l){var url=(l.fase==='envasado'?'/planta/legajo-envasado/':'/planta/orden/')+l.id;return '<tr><td class="mono">'+esc(l.numero_op||('EBR-'+l.id))+'</td><td>'+esc(l.producto)+'</td><td class="mono">'+esc(l.lote)+'</td><td>'+esc(l.fase)+'</td><td class="muted">'+dt(l.completado_at)+'</td><td><a class="bt bt-ver" href="'+url+'">Abrir &amp; liberar &rarr;</a></td></tr>';}).join(''):'<tr><td colspan="6" class="muted">Ningún lote esperando liberación.</td></tr>')+
      '</tbody></table></div>';
    document.getElementById('cont').innerHTML=h;
  }catch(e){document.getElementById('cont').innerHTML='<div class="card" style="color:#b91c1c">Error de red: '+esc(e.message)+'</div>';}
}
async function aprobar(id,btn){
  if(!confirm('¿Aprobar este MBR con tu firma electrónica? (queda auditado · Part 11)'))return;
  btn.disabled=true; btn.textContent='Aprobando…';
  try{
    var r=await fetch('/api/brd/mbr/'+id+'/aprobar-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:'{}'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo aprobar: '+((d&&d.error)||r.status));btn.disabled=false;btn.textContent='Aprobar';return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));btn.disabled=false;btn.textContent='Aprobar';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/bandeja-dt", methods=["GET"])
def bandeja_dt_page():
    """Bandeja de Dirección Técnica · decisiones pendientes · premium · 9-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/bandeja-dt"</script>',
                        mimetype="text/html")
    return Response(_BANDEJA_DT_HTML, mimetype="text/html")


@bp.route("/brd/despeje/<int:ebr_id>", methods=["GET"])
def despeje_imprimible(ebr_id):
    """Formato IMPRIMIBLE del Despeje de Línea - Dispensación (MyBatch: el ícono
    PDF junto al título). Registro GMP con las 13 verificaciones, CUMPLE,
    responsable, fecha y firmas. Server-side (sin JS) · Ctrl+P o auto-print.
    Sebastián 6-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/brd/despeje/' + str(ebr_id) + '"</script>',
                        mimetype="text/html")
    etapa = (request.args.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    etapa_label = "FABRICACIÓN" if etapa == "fabricacion" else "DISPENSACIÓN"
    etapa_area = "fabricación" if etapa == "fabricacion" else "dispensación"
    conn = get_db()
    import html as _h
    # Cabecera del legajo
    hdr = {}
    try:
        row = conn.execute(
            "SELECT COALESCE(lote,''), COALESCE(numero_op,''), COALESCE(area_codigo,''), "
            "mbr_template_id, COALESCE(estado,''), COALESCE(iniciado_at_utc,'') "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if row:
            hdr = {'lote': row[0], 'numero_op': row[1], 'area_codigo': row[2],
                   'mbr': row[3], 'estado': row[4], 'iniciado': row[5]}
    except Exception:
        hdr = {}
    producto = ''
    try:
        if hdr.get('mbr'):
            mr = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?", (hdr['mbr'],)).fetchone()
            producto = (mr[0] if mr else '') or ''
    except Exception:
        pass
    area = hdr.get('area_codigo', '')
    try:
        if area:
            ar = conn.execute("SELECT nombre FROM areas_planta WHERE codigo=?", (area,)).fetchone()
            if ar and ar[0]:
                area = str(ar[0]) + ' (' + hdr['area_codigo'] + ')'
    except Exception:
        pass
    # Items registrados
    reg = {}
    try:
        for dr in conn.execute(
            "SELECT item_idx, cumple, COALESCE(observaciones,''), COALESCE(registrado_por,''), "
            "COALESCE(registrado_at_utc,'') FROM ebr_despeje_items "
            "WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=?", (ebr_id, etapa)).fetchall():
            reg[int(dr[0])] = dr
    except Exception:
        reg = {}

    def _cumple_txt(c):
        if c == 1:
            return '<span style="color:#166534;font-weight:800">Sí</span>'
        if c == 0:
            return '<span style="color:#b91c1c;font-weight:800">No</span>'
        return '<span style="color:#94a3b8">—</span>'

    filas = []
    for i, texto in enumerate(DESPEJE_LINEA_ITEMS):
        r = reg.get(i)
        cumple = (int(r[1]) if r and r[1] is not None else None)
        obs = _h.escape(r[2]) if r else ''
        resp = _h.escape(r[3]) if r else ''
        fecha = (r[4][:16].replace('T', ' ') if r and r[4] else '')
        filas.append(
            '<tr><td class="n">' + str(i + 1) + '</td>'
            '<td>' + _h.escape(texto) + '</td>'
            '<td class="c">' + _cumple_txt(cumple) + '</td>'
            '<td class="c">' + _h.escape(resp) + '</td>'
            '<td class="c">' + _h.escape(fecha) + '</td>'
            '<td>' + obs + '</td></tr>')
    filas_html = ''.join(filas)
    e = _h.escape
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Despeje de Línea · ' + e(hdr.get('numero_op') or str(ebr_id)) + '</title>'
        '<style>'
        '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");'
        '*{box-sizing:border-box;font-family:"Inter",system-ui,Arial,sans-serif}'
        'body{margin:0;background:#f4f4f7;color:#18181b;padding:28px;-webkit-font-smoothing:antialiased}'
        '.sheet{max-width:980px;margin:0 auto;background:#fff;padding:30px 34px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}'
        '.topacc{height:5px;margin:-30px -34px 16px;background:linear-gradient(90deg,#a78bfa,#6d28d9)}'
        '.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e4e4e7;padding-bottom:14px;margin-bottom:16px}'
        '.top h1{font-size:18px;margin:0;letter-spacing:.5px}'
        '.top .co{font-size:13px;font-weight:700;color:#334155}'
        '.meta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 18px;font-size:12.5px;margin-bottom:16px}'
        '.meta b{color:#64748b;font-weight:700;display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.3px}'
        '.intro{font-size:12.5px;color:#334155;margin-bottom:10px}'
        'table{width:100%;border-collapse:collapse;font-size:12px}'
        'th{background:#f5f3ff;color:#4c1d95;padding:9px 10px;text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.3px;font-weight:700}'
        'td{padding:8px;border-bottom:1px solid #e2e8f0;vertical-align:top}'
        'td.n{text-align:center;color:#94a3b8;width:26px}td.c{text-align:center;white-space:nowrap}'
        '.firmas{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-top:42px;font-size:12px}'
        '.firma{text-align:center}.firma .ln{border-top:1px solid #0f172a;margin-bottom:5px;padding-top:5px}'
        '.no-print{text-align:center;margin:16px 0}'
        '.btn{background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer}'
        '@media print{.no-print{display:none}body{background:#fff;padding:0}.sheet{box-shadow:none;border-radius:0}}'
        '</style></head><body>'
        '<div class="no-print"><button class="btn" onclick="window.print()">🖨 Imprimir / Guardar PDF</button></div>'
        '<div class="sheet">'
        '<div class="topacc"></div>'
        '<div class="top"><div><h1>DESPEJE DE LÍNEA · ' + etapa_label + '</h1>'
        '<div style="font-size:11px;color:#71717a;margin-top:3px">Registro de verificación previo a fabricación · BPM / INVIMA · 21 CFR Part 11</div></div>'
        '<div class="co" style="display:flex;align-items:center;gap:10px"><span style="width:38px;height:38px;border-radius:11px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#a78bfa,#6d28d9);box-shadow:0 4px 12px rgba(109,40,217,.2)"><svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="#fff"><circle cx="16" cy="12" r="3" fill="#fff"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".7"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".4"/></svg></span><div style="text-align:left;line-height:1.2">ESPAGIRIA Laboratorio SAS<br><span style="font-weight:400;color:#71717a;font-size:11px">ÁNIMUS Lab</span></div></div></div>'
        '<div class="meta">'
        '<div><b>Orden de Producción</b>' + e(hdr.get('numero_op') or ('EBR-' + str(ebr_id))) + '</div>'
        '<div><b>N° de Lote Bulk</b>' + e(hdr.get('lote') or '—') + '</div>'
        '<div><b>Producto</b>' + e(producto or '—') + '</div>'
        '<div><b>Área o Línea</b>' + e(area or '—') + '</div>'
        '<div><b>Estado</b>' + e(hdr.get('estado') or '—') + '</div>'
        '<div><b>Fecha</b>' + e((hdr.get('iniciado') or '')[:16].replace('T', ' ') or '—') + '</div>'
        '</div>'
        '<div class="intro">Realizar despeje en el área de ' + etapa_area + ' de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'
        '<table><thead><tr><th>#</th><th>Verificación</th><th style="text-align:center">Cumple</th>'
        '<th style="text-align:center">Responsable</th><th style="text-align:center">Fecha</th><th>Observación</th></tr></thead>'
        '<tbody>' + filas_html + '</tbody></table>'
        '<div class="firmas">'
        '<div class="firma"><div class="ln">&nbsp;</div>Realizó (Operario)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Revisó (Jefe de Producción)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Aprobó (Calidad)</div>'
        '</div>'
        '</div></body></html>')
    return Response(html, mimetype='text/html')


@bp.route("/brd/dispensado/<int:ebr_id>", methods=["GET"])
def dispensado_imprimible(ebr_id):
    """Hoja IMPRIMIBLE del Dispensado de Materias Primas (MyBatch: ícono PDF de la
    sección 3). Lista todas las MP de la fórmula con %, lote, cant. a pesar y cant.
    pesada (lo registrado) + firmas. Server-side · Sebastián 6-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/brd/dispensado/' + str(ebr_id) + '"</script>',
                        mimetype="text/html")
    conn = get_db()
    import html as _h
    hdr = {}
    try:
        row = conn.execute(
            "SELECT COALESCE(lote,''), COALESCE(numero_op,''), mbr_template_id, "
            "COALESCE(estado,''), COALESCE(iniciado_at_utc,''), COALESCE(cantidad_objetivo_g,0) "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if row:
            hdr = {'lote': row[0], 'numero_op': row[1], 'mbr': row[2],
                   'estado': row[3], 'iniciado': row[4], 'obj_g': float(row[5] or 0)}
    except Exception:
        hdr = {}
    producto = ''
    try:
        if hdr.get('mbr'):
            mr = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?", (hdr['mbr'],)).fetchone()
            producto = (mr[0] if mr else '') or ''
    except Exception:
        pass
    # Recordado (cant. pesada) por material · última fila por material.
    recorded = {}
    try:
        for pr in conn.execute(
            "SELECT material_id, cantidad_real_g, COALESCE(lote_mp,''), COALESCE(pesado_por,''), "
            "COALESCE(pesado_at_utc,'') FROM ebr_pesajes WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall():
            recorded[str(pr[0])] = pr  # la última gana
    except Exception:
        recorded = {}
    obj_g = hdr.get('obj_g', 0)
    filas = []
    try:
        fitems = conn.execute(
            "SELECT material_id, COALESCE(material_nombre,''), COALESCE(porcentaje,0) "
            "FROM formula_items WHERE producto_nombre=? ORDER BY porcentaje DESC", (producto,)).fetchall()
        for i, fr in enumerate(fitems):
            mid = str(fr[0] or '').strip()
            if not mid:
                continue
            pct = float(fr[2] or 0)
            a_pesar = round(pct / 100.0 * obj_g, 1) if obj_g else 0
            rec = recorded.get(mid)
            pesada = ('{:,.1f}'.format(rec[1]) if rec and rec[1] is not None else '')
            lote = (rec[2] if rec else '') or ''
            por = (rec[3] if rec else '') or ''
            filas.append(
                '<tr><td class="n">' + str(i + 1) + '</td>'
                '<td><span class="mono">' + _h.escape(mid) + '</span> ' + _h.escape(fr[1] or '') + '</td>'
                '<td class="c">' + ('{:.3f}'.format(pct)).rstrip('0').rstrip('.') + '%</td>'
                '<td class="mono">' + _h.escape(lote or '________') + '</td>'
                '<td class="r">' + ('{:,.1f}'.format(a_pesar)) + ' g</td>'
                '<td class="r">' + (pesada + ' g' if pesada else '__________') + '</td>'
                '<td class="c">' + _h.escape(por or '______') + '</td></tr>')
    except Exception:
        pass
    filas_html = ''.join(filas) or '<tr><td colspan="7" style="text-align:center;color:#94a3b8">Sin fórmula con materias primas.</td></tr>'
    e = _h.escape
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Dispensado · ' + e(hdr.get('numero_op') or str(ebr_id)) + '</title><style>'
        '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");'
        '*{box-sizing:border-box;font-family:"Inter",system-ui,Arial,sans-serif}'
        'body{margin:0;background:#f4f4f7;color:#18181b;padding:28px;-webkit-font-smoothing:antialiased}'
        '.sheet{max-width:1000px;margin:0 auto;background:#fff;padding:30px 34px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}'
        '.top{display:flex;justify-content:space-between;border-bottom:2px solid #0f172a;padding-bottom:10px;margin-bottom:14px}'
        '.top h1{font-size:18px;margin:0}.top .co{font-size:13px;font-weight:700;color:#334155;text-align:right}'
        '.meta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 18px;font-size:12.5px;margin-bottom:14px}'
        '.meta b{color:#64748b;font-weight:700;display:block;font-size:10.5px;text-transform:uppercase}'
        'table{width:100%;border-collapse:collapse;font-size:12px}'
        'th{background:#f5f3ff;color:#4c1d95;padding:9px 10px;text-align:left;font-size:10.5px;text-transform:uppercase;font-weight:700}'
        'td{padding:7px 8px;border-bottom:1px solid #e2e8f0}'
        'td.n{text-align:center;color:#94a3b8;width:26px}td.c{text-align:center}td.r{text-align:right;font-variant-numeric:tabular-nums}'
        '.mono{font-family:ui-monospace,monospace}'
        '.firmas{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-top:40px;font-size:12px}'
        '.firma{text-align:center}.firma .ln{border-top:1px solid #0f172a;margin-bottom:5px;padding-top:5px}'
        '.no-print{text-align:center;margin:16px 0}.btn{background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:700;cursor:pointer}'
        '@media print{.no-print{display:none}body{background:#fff;padding:0}.sheet{box-shadow:none}}'
        '</style></head><body>'
        '<div class="no-print"><button class="btn" onclick="window.print()">🖨 Imprimir / Guardar PDF</button></div>'
        '<div class="sheet">'
        '<div class="topacc"></div>'
        '<div class="top"><div><h1>DISPENSADO DE MATERIAS PRIMAS</h1>'
        '<div style="font-size:11px;color:#71717a;margin-top:3px">Hoja de pesaje · BPM / INVIMA · 21 CFR Part 11</div></div>'
        '<div class="co" style="display:flex;align-items:center;gap:10px"><span style="width:38px;height:38px;border-radius:11px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#a78bfa,#6d28d9);box-shadow:0 4px 12px rgba(109,40,217,.2)"><svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="#fff"><circle cx="16" cy="12" r="3" fill="#fff"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".7"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".4"/></svg></span><div style="text-align:left;line-height:1.2">ESPAGIRIA Laboratorio SAS<br><span style="font-weight:400;color:#71717a;font-size:11px">ÁNIMUS Lab</span></div></div></div>'
        '<div class="meta">'
        '<div><b>Orden</b>' + e(hdr.get('numero_op') or ('EBR-' + str(ebr_id))) + '</div>'
        '<div><b>N° de Lote</b>' + e(hdr.get('lote') or '—') + '</div>'
        '<div><b>Producto</b>' + e(producto or '—') + '</div>'
        '<div><b>Tamaño de lote</b>' + ('{:,.0f} g'.format(obj_g) if obj_g else '—') + '</div>'
        '<div><b>Estado</b>' + e(hdr.get('estado') or '—') + '</div>'
        '<div><b>Fecha</b>' + e((hdr.get('iniciado') or '')[:16].replace('T', ' ') or '—') + '</div>'
        '</div>'
        '<table><thead><tr><th>#</th><th>Materia Prima</th><th style="text-align:center">%</th><th>N° Lote</th>'
        '<th style="text-align:right">Cant. a pesar</th><th style="text-align:right">Cant. pesada</th>'
        '<th style="text-align:center">Pesó</th></tr></thead><tbody>' + filas_html + '</tbody></table>'
        '<div class="firmas">'
        '<div class="firma"><div class="ln">&nbsp;</div>Dispensó (Operario)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Verificó</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Revisó (Calidad)</div>'
        '</div></div></body></html>')
    return Response(html, mimetype='text/html')


# ──────────────────────────────────────────────────────────────────────────
# Activación de legajos automáticos · Sebastián 5-jun-2026
# Pantalla limpia (no popups) que genera+aprueba todos los MBR de una sola firma
# (password + MFA). Después, con EBR_MODE=warn, cada producción crea su legajo.
# ──────────────────────────────────────────────────────────────────────────

_ACTIVAR_LEGAJOS_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Activar legajos automáticos · EOS</title>
<style>
*{box-sizing:border-box}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f4f4f7;color:#18181b;margin:0;padding:24px;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:#fff;color:#7c3aed;font-size:13px;font-weight:700;text-decoration:none;padding:10px 18px;border-radius:11px;border:1px solid #e9d5ff;box-shadow:0 2px 10px rgba(124,58,237,.10)}
.card{background:#fff;border-radius:16px;box-shadow:0 4px 16px rgba(76,29,149,.07);margin:14px 0;overflow:hidden}
.hbar{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:22px 26px}
.hbar h1{margin:0;font-size:22px}.hbar p{margin:6px 0 0;font-size:13px;opacity:.9}
.body{padding:24px 26px}
.step{display:flex;gap:12px;margin-bottom:14px;font-size:13.5px;color:#475569}
.step b{color:#1e293b}
.num{flex:none;width:24px;height:24px;border-radius:50%;background:#ede9fe;color:#6d28d9;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:12px}
label{display:block;font-size:12px;font-weight:700;color:#64748b;margin:14px 0 5px;text-transform:uppercase;letter-spacing:.3px}
input{width:100%;padding:12px 14px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:15px}
input:focus{outline:none;border-color:#7c3aed}
.btn{margin-top:20px;width:100%;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border:none;border-radius:11px;padding:14px;font-size:15px;font-weight:800;cursor:pointer;box-shadow:0 6px 18px rgba(124,58,237,.28)}
.btn:disabled{opacity:.6;cursor:wait}
.note{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;border-radius:10px;padding:12px 14px;font-size:12.5px;margin-top:16px}
#out{margin-top:18px}
.res{padding:14px 16px;border-radius:10px;font-size:14px;margin-bottom:10px}
.res.ok{background:#dcfce7;color:#166534}.res.err{background:#fee2e2;color:#991b1b}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
.kpi div{background:#f5f3ff;border-radius:9px;padding:9px 14px;font-size:13px;font-weight:700;color:#5b21b6}
.fail{font-size:12px;color:#991b1b;margin-top:8px}
</style></head><body>
<div class="wrap">
<a class="back" href="/inventarios#fabricacion"><span>&larr;</span> Volver a Producción</a>
<div class="card">
  <div class="hbar"><h1>🏭 Activar legajos automáticos</h1>
    <p>Aprobá todos los procedimientos maestros (MBR) de una sola firma. Luego cada producción crea su legajo solo, como MyBatch.</p></div>
  <div class="body">
    <div class="step"><div class="num">1</div><div>Se <b>generan</b> los MBR faltantes desde tus fórmulas (procedimiento por componente).</div></div>
    <div class="step"><div class="num">2</div><div>Se <b>aprueban todos</b> con tu firma electrónica (tu contraseña + código MFA · 21 CFR Part 11).</div></div>
    <div class="step"><div class="num">3</div><div>Quedan como <b>procedimiento oficial</b>. Desde ahí, producir crea el legajo automático.</div></div>
    <label>Tu contraseña de EOS</label>
    <input id="pass" type="password" autocomplete="off" placeholder="Contraseña">
    <label>Código MFA de 6 dígitos (vacío si no usás MFA)</label>
    <input id="totp" type="text" inputmode="numeric" autocomplete="off" placeholder="123456">
    <button class="btn" id="go" onclick="activar()">✅ Generar y aprobar todos los MBR</button>
    <div class="note">Es una sola vez. Tu firma queda registrada (quién, qué, cuándo) como exige INVIMA. La contraseña no se guarda.</div>
    <div id="out"></div>
  </div>
</div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
async function activar(){
  var pass=document.getElementById('pass').value;
  var totp=document.getElementById('totp').value.trim();
  if(!pass){alert('Escribí tu contraseña');return;}
  var btn=document.getElementById('go'), out=document.getElementById('out');
  btn.disabled=true; btn.textContent='Procesando… (puede tardar unos segundos)';
  out.innerHTML='';
  try{
    var t='';
    try{var cr=await fetch('/api/csrf-token',{credentials:'same-origin'});t=(await cr.json()).csrf_token||'';}catch(e){}
    var r=await fetch('/api/brd/mbr/aprobar-todas',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t},
      body:JSON.stringify({password:pass,totp_token:totp})});
    var d=await r.json();
    if(!r.ok){
      var hint = d.codigo==='MFA' ? ' (revisá el código de 6 dígitos · cambia cada 30s)' : (d.codigo==='PWD'?' (revisá la contraseña)':'');
      out.innerHTML='<div class="res err">❌ '+esc(d.error||r.status)+hint+'</div>';
      btn.disabled=false; btn.textContent='✅ Generar y aprobar todos los MBR'; return;
    }
    out.innerHTML='<div class="res ok">✅ ¡Listo! Procedimientos aprobados.</div>'+
      '<div class="kpi">'+
        '<div>'+(d.mbr_aprobados||0)+' aprobados ahora</div>'+
        '<div>'+(d.ya_estaban_aprobados||0)+' ya estaban</div>'+
        '<div>'+(d.mbr_generados||0)+' generados</div>'+
        '<div>'+(d.total_productos||0)+' productos</div>'+
      '</div>'+
      ((d.fallidos&&d.fallidos.length)?('<div class="fail">⚠ '+d.fallidos.length+' sin fórmula o con problema: '+d.fallidos.slice(0,8).map(function(f){return esc(f.producto);}).join(', ')+(d.fallidos.length>8?'…':'')+'</div>'):'')+
      '<div class="note">Siguiente: activar <b>EBR_MODE=warn</b> para que cada producción cree su legajo sola. Avisale a tu equipo técnico o pedímelo y lo dejo activo.</div>';
    btn.textContent='✅ Hecho';
  }catch(e){out.innerHTML='<div class="res err">Error de red: '+esc(e.message)+'</div>';btn.disabled=false;btn.textContent='✅ Generar y aprobar todos los MBR';}
}
</script>
</body></html>"""


@bp.route("/planta/activar-legajos", methods=["GET"])
def activar_legajos_page():
    """Pantalla de activación masiva de legajos automáticos (Admin/Calidad)."""
    u = session.get("compras_user", "")
    if not u:
        return Response('<script>location.href="/login?next=/planta/activar-legajos"</script>',
                        mimetype="text/html")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return Response('<div style="font-family:sans-serif;padding:40px;color:#991b1b">Solo Admin o Calidad pueden activar legajos automáticos.</div>',
                        mimetype="text/html")
    return Response(_ACTIVAR_LEGAJOS_HTML, mimetype="text/html")


@bp.route("/api/brd/ebr/<int:ebr_id>/produccion-id", methods=["GET"])
def ebr_produccion_id(ebr_id):
    """Devuelve el id de la producción (tabla producciones) asociada a este EBR,
    matcheando por su lote. Permite ajustar la cantidad desde el detalle de orden
    (botón "+ Ajuste") reusando /api/produccion/<pid>/ajustar-cantidad."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(lote_codigo, lote) FROM ebr_ejecuciones WHERE id=?",
        (ebr_id,)).fetchone()
    if not row:
        return jsonify({"error": "EBR no existe"}), 404
    lote = (row[0] or "").strip()
    pid = None
    if lote:
        pr = conn.execute(
            "SELECT id FROM producciones WHERE lote=? ORDER BY id DESC LIMIT 1",
            (lote,)).fetchone()
        pid = pr[0] if pr else None
    return jsonify({"ok": True, "produccion_id": pid, "lote": lote})
