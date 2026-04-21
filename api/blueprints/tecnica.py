# blueprints/tecnica.py — Módulo Técnica & Aseguramiento
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, session, redirect
from auth import sin_acceso_html
from config import DB_PATH, ADMIN_USERS, TECNICA_USERS
from templates_py.tecnica_html import TECNICA_HTML

bp = Blueprint('tecnica', __name__)


def _check_access():
    """Verifica sesion activa y pertenencia a TECNICA_USERS o ADMIN_USERS."""
    u = session.get('compras_user', '')
    return bool(u) and (u in TECNICA_USERS or u in ADMIN_USERS)


def _init_tecnica():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS formulas_maestras (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo           TEXT NOT NULL,
        nombre           TEXT NOT NULL,
        version          TEXT DEFAULT '1.0',
        tipo             TEXT DEFAULT 'COSMETICO',
        estado           TEXT DEFAULT 'Vigente',
        fecha_version    TEXT,
        descripcion      TEXT,
        creado_por       TEXT,
        fecha_creacion   TEXT DEFAULT (date('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS fichas_tecnicas (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo              TEXT NOT NULL,
        nombre              TEXT NOT NULL,
        formula_id          INTEGER,
        version             TEXT DEFAULT '1.0',
        estado              TEXT DEFAULT 'Vigente',
        fecha_actualizacion TEXT DEFAULT (date('now')),
        url_documento       TEXT,
        notas               TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS registros_invima (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        producto          TEXT NOT NULL,
        num_registro      TEXT,
        num_lote          TEXT,
        tipo_tramite      TEXT DEFAULT 'Notificacion Sanitaria',
        fecha_expedicion  TEXT,
        fecha_vencimiento TEXT,
        estado            TEXT DEFAULT 'Vigente',
        notas             TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS documentos_sgd (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo           TEXT DEFAULT 'SOP',
        codigo         TEXT NOT NULL,
        nombre         TEXT NOT NULL,
        version        TEXT DEFAULT '1.0',
        fecha_emision  TEXT DEFAULT (date('now')),
        fecha_revision TEXT,
        responsable    TEXT,
        estado         TEXT DEFAULT 'Vigente',
        url_documento  TEXT,
        notas          TEXT
    )""")
    conn.commit()
    conn.close()


_init_tecnica()


# ── Página ─────────────────────────────────────────────────────────────────
@bp.route('/tecnica')
def tecnica_page():
    # Separar check de sesion vs check de rol para dar respuesta correcta
    if 'compras_user' not in session:
        return redirect('/login?next=/tecnica')
    if not _check_access():
        return Response(sin_acceso_html('Tecnica'), mimetype='text/html')
    return Response(TECNICA_HTML, mimetype='text/html')


# ── Dashboard ──────────────────────────────────────────────────────────────
@bp.route('/api/tecnica/dashboard')
def tecnica_dashboard():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM formulas_maestras WHERE estado='Vigente'")
    formulas_vigentes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM fichas_tecnicas WHERE estado='Vigente'")
    fichas_vigentes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM registros_invima WHERE estado='Vigente'")
    registros_vigentes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM registros_invima WHERE estado='En_Tramite'")
    registros_tramite = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM registros_invima
                 WHERE estado='Vigente' AND fecha_vencimiento IS NOT NULL
                   AND fecha_vencimiento <= date('now','+90 days')
                   AND fecha_vencimiento >= date('now')""")
    por_vencer = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM documentos_sgd WHERE estado='Vigente'")
    docs_vigentes = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM documentos_sgd
                 WHERE estado='Vigente' AND fecha_revision IS NOT NULL
                   AND fecha_revision <= date('now','+30 days')""")
    docs_revisar = c.fetchone()[0]
    # Próximos vencimientos INVIMA
    c.execute("""SELECT producto, num_registro, fecha_vencimiento, estado
                 FROM registros_invima
                 WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento != ''
                 ORDER BY fecha_vencimiento ASC LIMIT 5""")
    proximos = [{'producto': r[0], 'num_registro': r[1],
                 'fecha_vencimiento': r[2], 'estado': r[3]}
                for r in c.fetchall()]
    conn.close()
    return jsonify({
        'formulas_vigentes': formulas_vigentes,
        'fichas_vigentes': fichas_vigentes,
        'registros_vigentes': registros_vigentes,
        'registros_tramite': registros_tramite,
        'por_vencer': por_vencer,
        'docs_vigentes': docs_vigentes,
        'docs_revisar': docs_revisar,
        'proximos_vencimientos': proximos
    })


# ── Fórmulas Maestras ──────────────────────────────────────────────────────
@bp.route('/api/tecnica/formulas', methods=['GET', 'POST'])
def formulas_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""INSERT INTO formulas_maestras
                     (codigo,nombre,version,tipo,estado,fecha_version,descripcion,creado_por)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('codigo', ''), d.get('nombre', ''),
                   d.get('version', '1.0'), d.get('tipo', 'COSMETICO'),
                   d.get('estado', 'Vigente'),
                   d.get('fecha_version', datetime.now().strftime('%Y-%m-%d')),
                   d.get('descripcion', ''), session.get('compras_user', 'sistema')))
        conn.commit()
        fid = c.lastrowid
        conn.close()
        return jsonify({'ok': True, 'id': fid})
    c.execute("SELECT * FROM formulas_maestras ORDER BY fecha_creacion DESC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/tecnica/formulas/<int:fid>', methods=['PATCH', 'DELETE'])
def formula_update(fid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'DELETE':
        if session.get('compras_user') not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Solo administradores'}), 403
        c.execute("DELETE FROM formulas_maestras WHERE id=?", (fid,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['nombre', 'version', 'tipo', 'estado', 'fecha_version', 'descripcion']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [fid]
    if sets:
        c.execute(f"UPDATE formulas_maestras SET {sets} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Fichas Técnicas ────────────────────────────────────────────────────────
@bp.route('/api/tecnica/fichas', methods=['GET', 'POST'])
def fichas_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""INSERT INTO fichas_tecnicas
                     (codigo,nombre,formula_id,version,estado,fecha_actualizacion,url_documento,notas)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('codigo', ''), d.get('nombre', ''), d.get('formula_id'),
                   d.get('version', '1.0'), d.get('estado', 'Vigente'),
                   d.get('fecha_actualizacion', datetime.now().strftime('%Y-%m-%d')),
                   d.get('url_documento', ''), d.get('notas', '')))
        conn.commit()
        fid = c.lastrowid
        conn.close()
        return jsonify({'ok': True, 'id': fid})
    c.execute("SELECT * FROM fichas_tecnicas ORDER BY fecha_actualizacion DESC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/tecnica/fichas/<int:fid>', methods=['PATCH', 'DELETE'])
def ficha_update(fid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'DELETE':
        if session.get('compras_user') not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Solo administradores'}), 403
        c.execute("DELETE FROM fichas_tecnicas WHERE id=?", (fid,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['nombre', 'version', 'estado', 'fecha_actualizacion', 'url_documento', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [fid]
    if sets:
        c.execute(f"UPDATE fichas_tecnicas SET {sets} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Registros INVIMA ───────────────────────────────────────────────────────
@bp.route('/api/tecnica/invima', methods=['GET', 'POST'])
def invima_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""INSERT INTO registros_invima
                     (producto,num_registro,num_lote,tipo_tramite,fecha_expedicion,fecha_vencimiento,estado,notas)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('producto', ''), d.get('num_registro', ''), d.get('num_lote', ''),
                   d.get('tipo_tramite', 'Notificacion Sanitaria'),
                   d.get('fecha_expedicion', ''), d.get('fecha_vencimiento', ''),
                   d.get('estado', 'Vigente'), d.get('notas', '')))
        conn.commit()
        rid = c.lastrowid
        conn.close()
        return jsonify({'ok': True, 'id': rid})
    c.execute("SELECT * FROM registros_invima ORDER BY fecha_vencimiento ASC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/tecnica/invima/<int:rid>', methods=['PATCH', 'DELETE'])
def invima_update(rid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'DELETE':
        if session.get('compras_user') not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Solo administradores'}), 403
        c.execute("DELETE FROM registros_invima WHERE id=?", (rid,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['producto', 'num_registro', 'num_lote', 'tipo_tramite',
               'fecha_expedicion', 'fecha_vencimiento', 'estado', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [rid]
    if sets:
        c.execute(f"UPDATE registros_invima SET {sets} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Documentos SGD ─────────────────────────────────────────────────────────
@bp.route('/api/tecnica/documentos', methods=['GET', 'POST'])
def documentos_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("""INSERT INTO documentos_sgd
                     (tipo,codigo,nombre,version,fecha_emision,fecha_revision,responsable,estado,url_documento,notas)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (d.get('tipo', 'SOP'), d.get('codigo', ''), d.get('nombre', ''),
                   d.get('version', '1.0'),
                   d.get('fecha_emision', datetime.now().strftime('%Y-%m-%d')),
                   d.get('fecha_revision', ''), d.get('responsable', ''),
                   d.get('estado', 'Vigente'), d.get('url_documento', ''), d.get('notas', '')))
        conn.commit()
        did = c.lastrowid
        conn.close()
        return jsonify({'ok': True, 'id': did})
    c.execute("SELECT * FROM documentos_sgd ORDER BY tipo, codigo")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/tecnica/documentos/<int:did>', methods=['PATCH', 'DELETE'])
def documento_update(did):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'DELETE':
        if session.get('compras_user') not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Solo administradores'}), 403
        c.execute("DELETE FROM documentos_sgd WHERE id=?", (did,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['tipo', 'nombre', 'version', 'fecha_emision', 'fecha_revision',
               'responsable', 'estado', 'url_documento', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [did]
    if sets:
        c.execute(f"UPDATE documentos_sgd SET {sets} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({'ok': True})
