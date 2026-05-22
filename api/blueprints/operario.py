"""Blueprint operario · "Mi día en Planta" · 13-may-2026.

Vista mobile-first para Mayerlin/Camilo/Milton/Sebastian Murillo/Luis
Enrique. Cada operario abre /operario en su tablet o celular y ve solo
las producciones que LE tocan hoy, con botones grandes para iniciar /
reportar / completar.

Filosofía:
- BRD invisible: el operario aprieta "Iniciar producción", el sistema
  hookea auto-EBR por debajo (commit 73e4cd5). El operario nunca ve la
  palabra "EBR" o "MBR" — solo "Iniciar / Reportar paso / Completar".
- Permisos: Mayerlin solo ve donde es operario_dispensacion_id (o
  cualquiera de los 4 roles). Sebastián/Alejandro (admin) ven TODAS.
  Luis Enrique (jefe) también ve todas para coordinar.
- Mapeo username → operario_id: por LOWER(nombre) en operarios_planta.
  Si no hay match (usuario sin operario asociado), devolvemos lista
  vacía — no rompemos.

Endpoints:
- GET /operario           HTML mobile-first (todos los users logueados)
- GET /api/operario/mi-dia    JSON con producciones del día filtradas
"""
import logging
from flask import Blueprint, Response, jsonify, request, session

from database import get_db
from config import ADMIN_USERS, PLANTA_USERS

bp = Blueprint("operario", __name__)
log = logging.getLogger("operario")


def _hoy_str(c):
    """Fecha Bogotá (UTC-5) · usada por mi_dia. Movido arriba (21-may-2026)
    para definir antes de su uso (era footgun de hoisting Python)."""
    row = c.execute("SELECT date('now', '-5 hours')").fetchone()
    return row[0] if row else ""


def _require_login():
    if not session.get("compras_user"):
        return jsonify({"error": "login requerido"}), 401
    return None


def _username_to_operario_id(c, username):
    """Mapea username Flask → operarios_planta.id por LOWER(nombre).

    Heurística: el username (e.g., 'mayerlin', 'smurillo', 'luis')
    matchea el primer nombre del operario (case-insensitive).
    'smurillo' → 'Sebastian Murillo' usando match por apellido también.

    Retorna int id o None si no hay match (usuario sin operario asociado).
    """
    if not username:
        return None
    u = username.lower().strip()
    # Match 1 · primer nombre exacto (mayerlin → Mayerlin)
    row = c.execute(
        "SELECT id FROM operarios_planta WHERE LOWER(nombre) = ? AND activo = 1 LIMIT 1",
        (u,),
    ).fetchone()
    if row:
        return int(row[0])
    # Match 2 · apellido (smurillo → 'S' + Murillo = Sebastian Murillo)
    # Patrón: primer-letra + apellido (smurillo, jdiaz, etc)
    if len(u) >= 4:
        letra = u[0]
        apellido = u[1:]
        row = c.execute(
            """SELECT id FROM operarios_planta
               WHERE LOWER(apellido) = ? AND LOWER(SUBSTR(nombre, 1, 1)) = ?
                 AND activo = 1 LIMIT 1""",
            (apellido, letra),
        ).fetchone()
        if row:
            return int(row[0])
    # BUG-6 fix · 20-may-2026: Match 3 antes hacía LIKE 'u%' con LIMIT 1
    # · colisión silenciosa si dos operarios empezaban con la misma
    # letra (ej. 'm' → Mayerlin o Milton aleatorio). Ahora:
    #   - exige username ≥ 3 chars (evita matches genéricos 'm'/'a')
    #   - exige resultado ÚNICO (si LIKE devuelve >1, devolver None ·
    #     mejor falle limpio que mapee a operario equivocado)
    if len(u) >= 3:
        rows = c.execute(
            """SELECT id FROM operarios_planta
               WHERE LOWER(nombre) LIKE ? AND activo = 1 LIMIT 2""",
            (u + '%',),
        ).fetchall()
        if len(rows) == 1:
            return int(rows[0][0])
    return None


def _siguiente_accion(pp_row, ebr_row):
    """Determina qué acción es la próxima visible al operario.

    Estados posibles devueltos:
      'iniciar'       · producción pendiente, descontar inventario
      'continuar'     · producción iniciada, pasos del EBR pendientes
      'completar_pp'  · pasos EBR completados, falta reportar kg_real
      'ya_completado' · producción terminada (fin_real_at set)
    """
    inicio = pp_row['inicio_real_at']
    fin = pp_row['fin_real_at']
    if fin:
        return 'ya_completado'
    if not inicio:
        return 'iniciar'
    # iniciado pero no terminado · si hay EBR, mostrar progreso pasos
    if ebr_row and ebr_row['pasos_pendientes'] > 0:
        return 'continuar'
    return 'completar_pp'


@bp.route("/operario", methods=["GET"])
@bp.route("/mi-dia", methods=["GET"])
def operario_dashboard():
    """UI mobile-first del operario. Renderiza HTML que pollea
    /api/operario/mi-dia cada 30s."""
    if not session.get("compras_user"):
        return Response("No autorizado · login requerido", status=401)
    from templates_py.operario_html import render_operario
    return Response(render_operario(), mimetype="text/html")


@bp.route("/api/operario/mi-dia", methods=["GET"])
def mi_dia():
    """JSON con producciones del día asignadas al usuario.

    Respuesta:
    {
      "user": "mayerlin",
      "nombre": "Mayerlin Rivera",
      "rol_predeterminado": "dispensacion",
      "es_jefe": false,
      "es_admin": false,
      "ve_todas": false,   // admin o jefe ven todas, no filtran
      "producciones": [ { ... } ],
      "fecha": "2026-05-13"
    }
    """
    err = _require_login()
    if err:
        return err

    user = session.get("compras_user", "")
    es_admin = user in ADMIN_USERS

    conn = get_db()
    c = conn.cursor()

    # Identificar operario
    operario_id = _username_to_operario_id(c, user)

    # Sebastián 19-may-2026: admin puede ver Mi Día de otro operario
    # (drill-down desde Centro de Mando → tarjeta del operario).
    as_op = request.args.get('as_operario_id', type=int)
    drill_down_activo = False
    if as_op and es_admin:
        operario_id = as_op
        drill_down_activo = True
    operario_info = None
    es_jefe = False
    if operario_id is not None:
        row = c.execute(
            """SELECT id, nombre, apellido, rol_predeterminado, es_jefe_produccion
               FROM operarios_planta WHERE id = ?""",
            (operario_id,),
        ).fetchone()
        if row:
            operario_info = {
                "id": row[0],
                "nombre": f"{row[1]} {row[2] or ''}".strip(),
                "rol_predeterminado": row[3] or "",
            }
            es_jefe = bool(row[4])

    # BUG-3 fix · 19-may-2026 audit Planta PERFECTA:
    # Cuando admin/jefe usa drill-down (?as_operario_id=X), queremos ver
    # las producciones DE ESE operario, no TODAS. Antes ve_todas seguía
    # True por es_admin/es_jefe → el filtro WHERE no se aplicaba → admin
    # con ?as_operario_id=3 veía TODAS las producciones del día.
    if drill_down_activo:
        ve_todas = False
    else:
        ve_todas = es_admin or es_jefe

    # FIX · 21-may-2026 · ventana exacta hoy Bogotá (UTC-5)
    # Antes: ±1 día abría posibilidad de iniciar producción de mañana por error
    # Ahora: date('now', '-5 hours') exacto (compatible PG + SQLite)
    where_fecha = "date(fecha_programada) = date('now', '-5 hours')"
    where_op = ""
    params = []
    if not ve_todas and operario_id is not None:
        where_op = """ AND (operario_dispensacion_id = ?
                       OR operario_elaboracion_id = ?
                       OR operario_envasado_id = ?
                       OR operario_acondicionamiento_id = ?)"""
        params = [operario_id, operario_id, operario_id, operario_id]
    elif not ve_todas and operario_id is None:
        # Usuario sin operario asociado y no admin/jefe · devolver vacío
        return jsonify({
            "user": user,
            "nombre": "",
            "rol_predeterminado": "",
            "es_jefe": False,
            "es_admin": False,
            "ve_todas": False,
            "operario_id": None,
            "producciones": [],
            "fecha": _hoy_str(c),
            "mensaje": "Tu usuario no tiene operario asignado en planta. "
                        "Pídele a Sebastián que te dé acceso.",
        })

    sql = f"""SELECT pp.id, pp.producto, pp.cantidad_kg,
                     pp.fecha_programada, pp.estado, pp.area_id,
                     ap.codigo as area_codigo, ap.nombre as area_nombre,
                     pp.operario_dispensacion_id, pp.operario_elaboracion_id,
                     pp.operario_envasado_id, pp.operario_acondicionamiento_id,
                     pp.inicio_real_at, pp.fin_real_at,
                     pp.inventario_descontado_at, pp.kg_real, pp.merma_pct,
                     COALESCE(ap.estado, '') as area_estado
              FROM produccion_programada pp
              LEFT JOIN areas_planta ap ON ap.id = pp.area_id
              WHERE {where_fecha}{where_op}
              ORDER BY pp.fecha_programada ASC, pp.id ASC"""
    rows = c.execute(sql, params).fetchall()

    # PERF-FIX · 21-may-2026 · pre-cargar EBRs + pasos pendientes en bulk
    # Antes: 1 query EBR + 2 sub-COUNT por producción · 20 prods → 60 queries
    # Ahora: 2 queries totales sin importar # de producciones
    pp_ids = [r[0] for r in rows]
    ebr_map = {}
    if pp_ids:
        placeholders = ','.join(['?'] * len(pp_ids))
        try:
            ebr_rows = c.execute(
                f"""SELECT produccion_id, id, numero_op, lote, estado FROM ebr_ejecuciones
                    WHERE produccion_id IN ({placeholders})""",
                pp_ids,
            ).fetchall()
            ebr_ids_all = [e[1] for e in ebr_rows]
            pasos_pend = {}
            pasos_total = {}
            if ebr_ids_all:
                eph = ','.join(['?'] * len(ebr_ids_all))
                p_pend = c.execute(
                    f"""SELECT ebr_id, COUNT(*) FROM ebr_pasos_ejecutados
                        WHERE ebr_id IN ({eph}) AND estado='pendiente'
                        GROUP BY ebr_id""",
                    ebr_ids_all,
                ).fetchall()
                pasos_pend = {pp[0]: pp[1] for pp in p_pend}
                p_tot = c.execute(
                    f"""SELECT ebr_id, COUNT(*) FROM ebr_pasos_ejecutados
                        WHERE ebr_id IN ({eph})
                        GROUP BY ebr_id""",
                    ebr_ids_all,
                ).fetchall()
                pasos_total = {pp[0]: pp[1] for pp in p_tot}
            for er in ebr_rows:
                ebr_map[er[0]] = {
                    'id': er[1], 'numero_op': er[2], 'lote': er[3],
                    'estado': er[4],
                    'pasos_pendientes': pasos_pend.get(er[1], 0),
                    'pasos_total': pasos_total.get(er[1], 0),
                }
        except Exception:
            pass

    out = []
    for r in rows:
        # Determinar el rol del operario actual en esta producción
        mi_rol = ""
        if operario_id is not None:
            if r[8] == operario_id:
                mi_rol = "dispensacion"
            elif r[9] == operario_id:
                mi_rol = "elaboracion"
            elif r[10] == operario_id:
                mi_rol = "envasado"
            elif r[11] == operario_id:
                mi_rol = "acondicionamiento"

        # PERF-FIX · usar pre-cargado en bulk (era N+1)
        ebr_info = ebr_map.get(r[0])

        # Estado simplificado para el operario
        pp_dict = {
            'inicio_real_at': r[12],
            'fin_real_at': r[13],
        }
        accion = _siguiente_accion(pp_dict, ebr_info)

        out.append({
            "id": r[0],
            "producto": r[1] or "",
            "cantidad_kg": float(r[2] or 0),
            "fecha_programada": r[3] or "",
            "estado": r[4] or "",
            "area_id": r[5],
            "area_codigo": r[6] or "",
            "area_nombre": r[7] or "",
            "area_estado": r[17] or "",
            "mi_rol_aqui": mi_rol,
            "inicio_real_at": r[12],
            "fin_real_at": r[13],
            "inventario_descontado_at": r[14],
            "kg_real": r[15],
            "merma_pct": r[16],
            "ebr": ebr_info,
            "siguiente_accion": accion,
        })

    return jsonify({
        "user": user,
        "nombre": (operario_info or {}).get("nombre", ""),
        "rol_predeterminado": (operario_info or {}).get("rol_predeterminado", ""),
        "operario_id": operario_id,
        "es_jefe": es_jefe,
        "es_admin": es_admin,
        "ve_todas": ve_todas,
        "producciones": out,
        "fecha": _hoy_str(c),
    })
