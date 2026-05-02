# blueprints/tecnica.py — Módulo Técnica & Aseguramiento
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, session, redirect
from auth import sin_acceso_html
from audit_helpers import audit_log
from config import DB_PATH, ADMIN_USERS, TECNICA_USERS
from database import get_db
from templates_py.tecnica_html import TECNICA_HTML

bp = Blueprint('tecnica', __name__)

def _check_access():
    """Verifica sesion activa y pertenencia a TECNICA_USERS o ADMIN_USERS."""
    u = session.get('compras_user', '')
    return bool(u) and (u in TECNICA_USERS or u in ADMIN_USERS)

def _init_tecnica():
    conn = get_db()
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
    conn = get_db()
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
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        usuario = session.get('compras_user', 'sistema')
        c.execute("""INSERT INTO formulas_maestras
                     (codigo,nombre,version,tipo,estado,fecha_version,descripcion,creado_por)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('codigo', ''), d.get('nombre', ''),
                   d.get('version', '1.0'), d.get('tipo', 'COSMETICO'),
                   d.get('estado', 'Vigente'),
                   d.get('fecha_version', datetime.now().strftime('%Y-%m-%d')),
                   d.get('descripcion', ''), usuario))
        fid = c.lastrowid
        audit_log(c, usuario=usuario, accion='CREAR_FORMULA', tabla='formulas_maestras',
                  registro_id=fid,
                  despues={k: d.get(k) for k in ('codigo','nombre','version','tipo','estado')},
                  detalle=f"Creó fórmula {d.get('codigo','')} · {d.get('nombre','')}")
        conn.commit()
        return jsonify({'ok': True, 'id': fid})
    c.execute("SELECT * FROM formulas_maestras ORDER BY fecha_creacion DESC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

def _snapshot_formula(c, formula_id, motivo, usuario):
    """Toma snapshot de la formula ANTES de modificar/eliminar.
    Asigna numero de version incremental por formula_id."""
    import json as _json
    try:
        row = c.execute("SELECT * FROM formulas_maestras WHERE id=?", (formula_id,)).fetchone()
        if not row:
            return
        snap = dict(row)
        # Tambien snapshot componentes si existen (tabla futura formula_componentes)
        try:
            comp_rows = c.execute(
                "SELECT * FROM formula_componentes WHERE formula_id=?", (formula_id,)
            ).fetchall()
            snap["_componentes"] = [dict(r) for r in comp_rows]
        except sqlite3.OperationalError:
            pass
        last = c.execute(
            "SELECT MAX(version_num) FROM formulas_versiones WHERE formula_id=?",
            (formula_id,)
        ).fetchone()
        ver_num = (last[0] or 0) + 1
        c.execute("""INSERT INTO formulas_versiones
                     (formula_id, version_num, snapshot_json, motivo_cambio, creado_por)
                     VALUES (?,?,?,?,?)""",
                  (formula_id, ver_num, _json.dumps(snap, ensure_ascii=False, default=str),
                   motivo, usuario))
    except Exception:
        # No bloquear el update por fallo de snapshot
        pass


@bp.route('/api/tecnica/formulas/<int:fid>', methods=['PATCH', 'DELETE'])
def formula_update(fid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')
    if request.method == 'DELETE':
        if usuario not in ADMIN_USERS:
            return jsonify({'error': 'Solo administradores'}), 403
        # Capturar antes para audit log
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM formulas_maestras WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        # Snapshot antes de eliminar
        _snapshot_formula(c, fid, 'Eliminacion', usuario)
        c.execute("DELETE FROM formulas_maestras WHERE id=?", (fid,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_FORMULA', tabla='formulas_maestras',
                  registro_id=fid, antes=antes,
                  detalle=f"Eliminó fórmula id={fid}" + (f" ({antes.get('codigo','')})" if antes else ""))
        conn.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['nombre', 'version', 'tipo', 'estado', 'fecha_version', 'descripcion']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [fid]
    if sets:
        # Snapshot ANTES del UPDATE
        motivo = d.get('motivo_cambio') or 'Modificacion'
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM formulas_maestras WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        _snapshot_formula(c, fid, motivo, usuario)
        c.execute(f"UPDATE formulas_maestras SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='MODIFICAR_FORMULA', tabla='formulas_maestras',
                  registro_id=fid, antes=antes, despues={k: d.get(k) for k in d if k in allowed},
                  detalle=f"Modificó fórmula id={fid} · motivo: {motivo}")
        conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/tecnica/formulas/<int:fid>/versiones', methods=['GET'])
def formula_versiones(fid):
    """Lista historial de versiones de una formula."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("""
        SELECT id, version_num, motivo_cambio, creado_por, fecha_creacion
        FROM formulas_versiones
        WHERE formula_id = ?
        ORDER BY version_num DESC
    """, (fid,)).fetchall()
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols, r)) for r in rows])


@bp.route('/api/tecnica/formulas/<int:fid>/versiones/<int:vid>', methods=['GET'])
def formula_version_detalle(fid, vid):
    """Devuelve snapshot completo de una version especifica."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    import json as _json
    conn = get_db()
    c = conn.cursor()
    row = c.execute("""
        SELECT id, formula_id, version_num, snapshot_json, motivo_cambio, creado_por, fecha_creacion
        FROM formulas_versiones
        WHERE formula_id=? AND id=?
    """, (fid, vid)).fetchone()
    if not row:
        return jsonify({'error': 'Version no encontrada'}), 404
    out = dict(row)
    try:
        out['snapshot'] = _json.loads(out.pop('snapshot_json'))
    except Exception:
        out['snapshot'] = {}
        out.pop('snapshot_json', None)
    return jsonify(out)


@bp.route('/api/tecnica/formulas/<int:fid>/restaurar/<int:vid>', methods=['POST'])
def formula_restaurar(fid, vid):
    """Restaura una formula a una version anterior. Toma snapshot del estado
    actual antes de restaurar (asi el restore tambien es reversible)."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    usuario = session.get('compras_user', 'sistema')
    if usuario not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores'}), 403
    import json as _json
    conn = get_db()
    c = conn.cursor()
    row = c.execute("""SELECT snapshot_json, version_num FROM formulas_versiones
                       WHERE formula_id=? AND id=?""", (fid, vid)).fetchone()
    if not row:
        return jsonify({'error': 'Version no encontrada'}), 404
    try:
        snap = _json.loads(row[0])
    except Exception:
        return jsonify({'error': 'Snapshot corrupto'}), 500
    # Snapshot del estado actual antes de pisar
    _snapshot_formula(c, fid, f'Pre-restore desde v{row[1]}', usuario)
    # Restaurar campos editables de la formula
    campos_rest = ['nombre', 'version', 'tipo', 'estado', 'fecha_version', 'descripcion']
    sets = ', '.join(f + '=?' for f in campos_rest if f in snap)
    vals = [snap[f] for f in campos_rest if f in snap] + [fid]
    if sets:
        c.execute(f"UPDATE formulas_maestras SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='RESTAURAR_FORMULA', tabla='formulas_maestras',
                  registro_id=fid,
                  despues={k: snap.get(k) for k in campos_rest if k in snap},
                  detalle=f"Restauró fórmula id={fid} a versión {row[1]} (vid={vid})")
        conn.commit()
    return jsonify({'ok': True, 'restaurado_a_version': row[1]})

# ── Fichas Técnicas ────────────────────────────────────────────────────────
@bp.route('/api/tecnica/fichas', methods=['GET', 'POST'])
def fichas_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        usuario = session.get('compras_user', 'sistema')
        c.execute("""INSERT INTO fichas_tecnicas
                     (codigo,nombre,formula_id,version,estado,fecha_actualizacion,url_documento,notas)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('codigo', ''), d.get('nombre', ''), d.get('formula_id'),
                   d.get('version', '1.0'), d.get('estado', 'Vigente'),
                   d.get('fecha_actualizacion', datetime.now().strftime('%Y-%m-%d')),
                   d.get('url_documento', ''), d.get('notas', '')))
        fid = c.lastrowid
        audit_log(c, usuario=usuario, accion='CREAR_FICHA', tabla='fichas_tecnicas',
                  registro_id=fid,
                  despues={k: d.get(k) for k in ('codigo','nombre','version','estado','formula_id')},
                  detalle=f"Creó ficha técnica {d.get('codigo','')} · {d.get('nombre','')}")
        conn.commit()
        return jsonify({'ok': True, 'id': fid})
    c.execute("SELECT * FROM fichas_tecnicas ORDER BY fecha_actualizacion DESC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/tecnica/fichas/<int:fid>', methods=['PATCH', 'DELETE'])
def ficha_update(fid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')
    if request.method == 'DELETE':
        if usuario not in ADMIN_USERS:
            return jsonify({'error': 'Solo administradores'}), 403
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM fichas_tecnicas WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute("DELETE FROM fichas_tecnicas WHERE id=?", (fid,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_FICHA', tabla='fichas_tecnicas',
                  registro_id=fid, antes=antes,
                  detalle=f"Eliminó ficha técnica id={fid}" + (f" ({antes.get('codigo','')})" if antes else ""))
        conn.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['nombre', 'version', 'estado', 'fecha_actualizacion', 'url_documento', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [fid]
    if sets:
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM fichas_tecnicas WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute(f"UPDATE fichas_tecnicas SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='MODIFICAR_FICHA', tabla='fichas_tecnicas',
                  registro_id=fid, antes=antes,
                  despues={k: d.get(k) for k in d if k in allowed},
                  detalle=f"Modificó ficha técnica id={fid}")
        conn.commit()
    return jsonify({'ok': True})

# ── Registros INVIMA ───────────────────────────────────────────────────────
@bp.route('/api/tecnica/invima', methods=['GET', 'POST'])
def invima_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        usuario = session.get('compras_user', 'sistema')
        c.execute("""INSERT INTO registros_invima
                     (producto,num_registro,num_lote,tipo_tramite,fecha_expedicion,fecha_vencimiento,estado,notas)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (d.get('producto', ''), d.get('num_registro', ''), d.get('num_lote', ''),
                   d.get('tipo_tramite', 'Notificacion Sanitaria'),
                   d.get('fecha_expedicion', ''), d.get('fecha_vencimiento', ''),
                   d.get('estado', 'Vigente'), d.get('notas', '')))
        rid = c.lastrowid
        audit_log(c, usuario=usuario, accion='CREAR_REGISTRO_INVIMA', tabla='registros_invima',
                  registro_id=rid,
                  despues={k: d.get(k) for k in ('producto','num_registro','tipo_tramite','fecha_vencimiento','estado')},
                  detalle=f"Creó registro INVIMA · {d.get('producto','')} ({d.get('num_registro','—')})")
        conn.commit()
        return jsonify({'ok': True, 'id': rid})
    c.execute("SELECT * FROM registros_invima ORDER BY fecha_vencimiento ASC")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/tecnica/invima/<int:rid>', methods=['PATCH', 'DELETE'])
def invima_update(rid):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')
    if request.method == 'DELETE':
        if usuario not in ADMIN_USERS:
            return jsonify({'error': 'Solo administradores'}), 403
        antes_row = c.execute("SELECT producto, num_registro, estado, fecha_vencimiento FROM registros_invima WHERE id=?", (rid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute("DELETE FROM registros_invima WHERE id=?", (rid,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_REGISTRO_INVIMA', tabla='registros_invima',
                  registro_id=rid, antes=antes,
                  detalle=f"Eliminó registro INVIMA id={rid}" + (f" ({antes.get('num_registro','—')})" if antes else ""))
        conn.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['producto', 'num_registro', 'num_lote', 'tipo_tramite',
               'fecha_expedicion', 'fecha_vencimiento', 'estado', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [rid]
    if sets:
        antes_row = c.execute("SELECT producto, num_registro, estado, fecha_vencimiento FROM registros_invima WHERE id=?", (rid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute(f"UPDATE registros_invima SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='MODIFICAR_REGISTRO_INVIMA', tabla='registros_invima',
                  registro_id=rid, antes=antes,
                  despues={k: d.get(k) for k in d if k in allowed},
                  detalle=f"Modificó registro INVIMA id={rid}")
        conn.commit()
    return jsonify({'ok': True})

# ── Documentos SGD ─────────────────────────────────────────────────────────
@bp.route('/api/tecnica/documentos', methods=['GET', 'POST'])
def documentos_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        usuario = session.get('compras_user', 'sistema')
        # Calcular fecha_proxima_revision si no viene explicita
        from datetime import datetime as _dt, timedelta as _td
        fecha_emision = d.get('fecha_emision', _dt.now().strftime('%Y-%m-%d'))
        frecuencia = int(d.get('frecuencia_revision_meses', 12))
        fecha_proxima = d.get('fecha_proxima_revision', '')
        if not fecha_proxima and fecha_emision:
            try:
                em = _dt.strptime(fecha_emision[:10], '%Y-%m-%d')
                fecha_proxima = (em + _td(days=frecuencia*30)).strftime('%Y-%m-%d')
            except Exception:
                pass
        try:
            c.execute("""INSERT INTO documentos_sgd
                         (tipo,codigo,nombre,version,fecha_emision,fecha_revision,
                          responsable,estado,url_documento,notas,
                          frecuencia_revision_meses,fecha_proxima_revision,
                          responsable_revision)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (d.get('tipo', 'SOP'), d.get('codigo', ''), d.get('nombre', ''),
                       d.get('version', '1.0'), fecha_emision,
                       d.get('fecha_revision', ''), d.get('responsable', ''),
                       d.get('estado', 'Vigente'), d.get('url_documento', ''),
                       d.get('notas', ''), frecuencia, fecha_proxima,
                       d.get('responsable_revision', d.get('responsable',''))))
        except sqlite3.OperationalError:
            # Fallback para instalaciones donde la migracion 38 aun no corrio
            c.execute("""INSERT INTO documentos_sgd
                         (tipo,codigo,nombre,version,fecha_emision,fecha_revision,
                          responsable,estado,url_documento,notas)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (d.get('tipo', 'SOP'), d.get('codigo', ''), d.get('nombre', ''),
                       d.get('version', '1.0'), fecha_emision,
                       d.get('fecha_revision', ''), d.get('responsable', ''),
                       d.get('estado', 'Vigente'), d.get('url_documento', ''),
                       d.get('notas', '')))
        did = c.lastrowid
        audit_log(c, usuario=usuario, accion='CREAR_SGD', tabla='documentos_sgd',
                  registro_id=did,
                  despues={k: d.get(k) for k in ('tipo','codigo','nombre','version','estado','responsable')},
                  detalle=f"Creó SGD {d.get('tipo','SOP')} {d.get('codigo','')} · {d.get('nombre','')}")
        conn.commit()
        return jsonify({'ok': True, 'id': did, 'fecha_proxima_revision': fecha_proxima})
    c.execute("SELECT * FROM documentos_sgd ORDER BY tipo, codigo")
    cols = [x[0] for x in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)


@bp.route('/api/tecnica/documentos/proximos-vencimientos')
def documentos_vencimientos():
    """Lista SGDs que requieren revision en los proximos 60 dias.
    Vinculado al centro de notificaciones."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT id, tipo, codigo, nombre, version, fecha_proxima_revision,
                   responsable_revision, frecuencia_revision_meses,
                   julianday(fecha_proxima_revision) - julianday('now') as dias_restantes
            FROM documentos_sgd
            WHERE estado='Vigente'
              AND COALESCE(fecha_proxima_revision,'') != ''
              AND fecha_proxima_revision <= date('now','+60 day')
            ORDER BY fecha_proxima_revision ASC
        """).fetchall()
    except sqlite3.OperationalError:
        return jsonify({'documentos': [], 'mensaje': 'Migracion #38 pendiente'})
    cols = [x[0] for x in c.description]
    return jsonify({'documentos': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/tecnica/documentos/<int:did>/marcar-revisado', methods=['POST'])
def documento_revisado(did):
    """Marca un SGD como revisado HOY y reprograma la proxima revision."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import datetime as _dt, timedelta as _td
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT frecuencia_revision_meses FROM documentos_sgd WHERE id=?",
                    (did,)).fetchone()
    if not row:
        return jsonify({'error': 'Documento no encontrado'}), 404
    frecuencia = row[0] or 12
    hoy = _dt.now().strftime('%Y-%m-%d')
    proxima = (_dt.now() + _td(days=frecuencia*30)).strftime('%Y-%m-%d')
    c.execute("""UPDATE documentos_sgd
                 SET fecha_revision=?, fecha_proxima_revision=?
                 WHERE id=?""", (hoy, proxima, did))
    audit_log(c, usuario=session.get('compras_user', 'sistema'),
              accion='REVISAR_SGD', tabla='documentos_sgd', registro_id=did,
              despues={'fecha_revision': hoy, 'fecha_proxima_revision': proxima},
              detalle=f"Marcó SGD id={did} como revisado · próxima {proxima}")
    conn.commit()
    return jsonify({'ok': True, 'fecha_revision': hoy, 'fecha_proxima_revision': proxima})

@bp.route('/api/tecnica/documentos/<int:did>', methods=['PATCH', 'DELETE'])
def documento_update(did):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')
    if request.method == 'DELETE':
        if usuario not in ADMIN_USERS:
            return jsonify({'error': 'Solo administradores'}), 403
        antes_row = c.execute("SELECT tipo, codigo, nombre, version, estado FROM documentos_sgd WHERE id=?", (did,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute("DELETE FROM documentos_sgd WHERE id=?", (did,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_SGD', tabla='documentos_sgd',
                  registro_id=did, antes=antes,
                  detalle=f"Eliminó SGD id={did}" + (f" ({antes.get('codigo','')})" if antes else ""))
        conn.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['tipo', 'nombre', 'version', 'fecha_emision', 'fecha_revision',
               'responsable', 'estado', 'url_documento', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [did]
    if sets:
        antes_row = c.execute("SELECT tipo, codigo, nombre, version, estado FROM documentos_sgd WHERE id=?", (did,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        c.execute(f"UPDATE documentos_sgd SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='MODIFICAR_SGD', tabla='documentos_sgd',
                  registro_id=did, antes=antes,
                  despues={k: d.get(k) for k in d if k in allowed},
                  detalle=f"Modificó SGD id={did}")
        conn.commit()
    return jsonify({'ok': True})
