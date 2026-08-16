"""Blueprint identidad · Part 11 §11.100(b) identity binding.

Sebastián 12-may-2026 · Fase 0 Bloque D del salto a BRD.

Mantiene la tabla `usuarios_identidad` (mig 106) con la persona real detrás
de cada `username` de la app: cédula, nombre completo, cargo, área, manager
directo. En auditoría INVIMA / Part 11, el inspector pregunta "¿quién firmó
este registro electrónico y con qué autoridad?" — sin esta tabla la
respuesta es "el username 'sebastian'", que no es defendible.

Endpoints:
  GET  /api/identidad                · listado completo (cualquier user logueado).
  GET  /api/identidad/<username>     · detalle.
  PATCH /api/identidad/<username>    · admin actualiza campos.
  POST /api/identidad                · admin crea entry para username nuevo.

Editar la cédula/nombre/cargo NO es destructivo (la columna `audit_log`
captura el cambio vía e-signature workflow del Bloque C).
"""
import logging
from flask import Blueprint, jsonify, request, session
from database import get_db
from config import ADMIN_USERS
from audit_helpers import audit_log

bp = Blueprint("identidad", __name__)
log = logging.getLogger("identidad")


def _require_logged_in():
    """Cualquier user logueado puede LEER. Para escritura usar _require_admin."""
    if not session.get("compras_user"):
        return jsonify({"error": "No autorizado"}), 401
    return None


def _require_admin():
    if session.get("compras_user") not in ADMIN_USERS:
        return jsonify({"error": "Solo admin (sebastian/alejandro)"}), 403
    return None


_EDITABLE_FIELDS = {"cedula", "nombre_completo", "cargo", "area", "email",
                    "manager_username", "activo"}


def nombre_de(conn, username):
    """El NOMBRE de la persona detrás de un username, o '' si no está cargado.

    Sebastián 16-ago-2026, viendo el legajo de envasado: *"sale el cargo sin la persona ·
    tú tienes el nombre de cada jefe, ellos se loguean"*. Y tenía razón a medias: los
    nombres están, pero repartidos en TRES tablas y ninguna es la que el legajo mira.

      · `usuarios_identidad` tiene a los 18 que entran a la app, con su CARGO, y el
        `nombre_completo` vacío en todos;
      · `empleados` tiene 19 personas con nombre y apellido reales;
      · `operarios_planta` tiene a los del piso.

    Por eso el batch record imprimía *"Supervisado por: Jefe de Producción"* -- el cargo
    solo, que como firma en un registro regulado no sirve: no dice QUIÉN supervisó.

    ⚠ Y el cruce se hace por PERSONA, nunca por CARGO. Buscar "quién es el jefe de
    producción" en `empleados` devuelve a Luis Enrique Dorronsoro, que fue dado de BAJA
    (mig 375): el legajo terminaría firmado por alguien que ya no trabaja acá, que es peor
    que no poner nombre (M19: el estado se deriva de un hecho, y su baja es un hecho).
    Los inactivos quedan afuera en las tres fuentes.

    Devuelve '' cuando no hay nombre cargado -- y quien llama DECLARA que falta en vez de
    poner la etiqueta del cargo como si fuera la firma (M100/M124).
    """
    u = (username or "").strip()
    if not u:
        return ""
    try:
        r = conn.execute(
            "SELECT COALESCE(nombre_completo,'') FROM usuarios_identidad "
            "WHERE LOWER(username)=LOWER(?) AND COALESCE(activo,1)=1", (u,)).fetchone()
        if r and (r[0] or "").strip() and (r[0] or "").strip() != "Por definir":
            return r[0].strip()
    except Exception as e:
        log.warning("nombre_de: usuarios_identidad no disponible (%s): %s", u, e)

    # Las otras dos guardan el nombre partido y sin username: se empareja por el nombre de
    # pila, que es de donde salen los usuarios de esta casa (mayerlin -> Maierlin Rivera).
    import unicodedata

    def _norm(s):
        s = unicodedata.normalize("NFKD", str(s or ""))
        s = "".join(c for c in s if not unicodedata.combining(c))
        return s.strip().lower()

    objetivo = _norm(u)
    candidatos = []
    for tabla in ("empleados", "operarios_planta"):
        # ⚠ `empleados` NO tiene columna `activo` y `operarios_planta` sí: filtrar a ciegas
        # hace que la consulta falle y se descarte la tabla ENTERA -- con eso se perdían los
        # 19 nombres reales y el resolvedor "no encontraba" a gente que sí estaba cargada.
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(%s)" % tabla)}
        except Exception:
            cols = set()
        if not cols:
            continue
        donde = " WHERE COALESCE(activo,1)=1" if "activo" in cols else ""
        try:
            filas = conn.execute(
                "SELECT COALESCE(nombre,''), COALESCE(apellido,'') FROM %s%s"
                % (tabla, donde)).fetchall()
        except Exception as e:
            log.warning("nombre_de: no se pudo leer %s: %s", tabla, e)
            continue
        for f in filas:
            nom, ape = (f[0] or "").strip(), (f[1] or "").strip()
            if not nom:
                continue
            partes = [_norm(p) for p in nom.split()]
            if objetivo in partes or (len(objetivo) >= 4 and objetivo in _norm(nom + ape)):
                completo = (nom + " " + ape).strip()
                if completo not in candidatos:
                    candidatos.append(completo)

    # ⚠ Un solo candidato se usa; VARIOS no se eligen. En esta casa hay tres personas cuyo
    # nombre de pila es Sebastián (el CEO y dos operarios) y dos Camilo: adivinar puso
    # "Sebastian Murillo" -- el operario de envasado -- como responsable de un lote que
    # ejecutó otra persona. Poner el nombre de alguien que no actuó es peor que no poner
    # ninguno: es una firma falsa en un registro regulado (M193/M177).
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        log.info("nombre_de: %r coincide con %d personas (%s) · no se elige",
                 u, len(candidatos), ", ".join(candidatos[:3]))
    return ""


def _row_to_dict(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "cedula": row["cedula"] or "",
        "nombre_completo": row["nombre_completo"] or "",
        "cargo": row["cargo"] or "",
        "area": row["area"] or "",
        "email": row["email"] or "",
        "manager_username": row["manager_username"] or "",
        "activo": int(row["activo"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@bp.route("/api/identidad", methods=["GET"])
def listar_identidades():
    """Listado de identidades · cualquier user logueado lo ve."""
    err = _require_logged_in()
    if err:
        return err
    conn = get_db()
    rows = conn.execute(
        """SELECT id, username, cedula, nombre_completo, cargo, area, email,
                  manager_username, activo, created_at, updated_at
           FROM usuarios_identidad
           ORDER BY activo DESC, area, username"""
    ).fetchall()
    return jsonify({"items": [_row_to_dict(r) for r in rows]})


@bp.route("/api/identidad/<username>", methods=["GET"])
def detalle_identidad(username):
    err = _require_logged_in()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        """SELECT id, username, cedula, nombre_completo, cargo, area, email,
                  manager_username, activo, created_at, updated_at
           FROM usuarios_identidad WHERE username = ?""",
        (username,),
    ).fetchone()
    if not row:
        return jsonify({"error": "username no encontrado en identidad"}), 404
    return jsonify(_row_to_dict(row))


@bp.route("/api/identidad/<username>", methods=["PATCH"])
def actualizar_identidad(username):
    """Admin edita campos de identidad. Cambios quedan en audit_log."""
    err = _require_admin()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    cambios = {k: v for k, v in body.items() if k in _EDITABLE_FIELDS}
    if not cambios:
        return jsonify({"error": "No hay campos editables en el body",
                         "editables": sorted(_EDITABLE_FIELDS)}), 400

    conn = get_db()
    cur = conn.cursor()
    row_antes = cur.execute(
        """SELECT cedula, nombre_completo, cargo, area, email,
                  manager_username, activo
           FROM usuarios_identidad WHERE username = ?""",
        (username,),
    ).fetchone()
    if not row_antes:
        return jsonify({"error": "username no encontrado"}), 404
    antes = dict(row_antes)

    set_clause = ", ".join(f"{k} = ?" for k in cambios)
    params = list(cambios.values()) + [username]
    cur.execute(
        f"UPDATE usuarios_identidad SET {set_clause} WHERE username = ?",
        params,
    )
    conn.commit()

    audit_log(
        cur,
        usuario=session.get("compras_user", ""),
        accion="UPDATE_IDENTIDAD",
        tabla="usuarios_identidad",
        registro_id=username,
        antes=antes,
        despues=cambios,
        detalle=f"actualizó identidad de {username}",
    )
    conn.commit()

    row_despues = cur.execute(
        """SELECT id, username, cedula, nombre_completo, cargo, area, email,
                  manager_username, activo, created_at, updated_at
           FROM usuarios_identidad WHERE username = ?""",
        (username,),
    ).fetchone()
    return jsonify({"ok": True, "identidad": _row_to_dict(row_despues)})


@bp.route("/api/identidad", methods=["POST"])
def crear_identidad():
    """Admin crea entry para un username nuevo (post-onboarding RRHH)."""
    err = _require_admin()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip().lower()
    if not username:
        return jsonify({"error": "username requerido"}), 400

    conn = get_db()
    cur = conn.cursor()
    existe = cur.execute(
        "SELECT id FROM usuarios_identidad WHERE username = ?", (username,)
    ).fetchone()
    if existe:
        return jsonify({"error": f"identidad para '{username}' ya existe"}), 409

    cur.execute(
        """INSERT INTO usuarios_identidad
             (username, cedula, nombre_completo, cargo, area, email,
              manager_username, activo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            username,
            (body.get("cedula") or "").strip(),
            (body.get("nombre_completo") or "").strip(),
            (body.get("cargo") or "Por definir").strip(),
            (body.get("area") or "").strip(),
            (body.get("email") or "").strip(),
            (body.get("manager_username") or "").strip(),
            1 if body.get("activo", 1) else 0,
        ),
    )
    conn.commit()

    audit_log(
        cur,
        usuario=session.get("compras_user", ""),
        accion="CREATE_IDENTIDAD",
        tabla="usuarios_identidad",
        registro_id=username,
        despues={k: body.get(k) for k in _EDITABLE_FIELDS if k in body},
        detalle=f"creó identidad para {username}",
    )
    conn.commit()

    return jsonify({"ok": True, "username": username}), 201
