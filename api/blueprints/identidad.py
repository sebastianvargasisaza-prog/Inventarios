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
