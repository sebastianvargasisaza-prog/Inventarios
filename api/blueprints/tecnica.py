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
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo                        TEXT DEFAULT 'SOP',
        codigo                      TEXT NOT NULL,
        nombre                      TEXT NOT NULL,
        version                     TEXT DEFAULT '1.0',
        fecha_emision               TEXT DEFAULT (date('now')),
        fecha_revision              TEXT,
        responsable                 TEXT,
        estado                      TEXT DEFAULT 'Vigente',
        url_documento               TEXT,
        notas                       TEXT,
        frecuencia_revision_meses   INTEGER DEFAULT 12,
        fecha_proxima_revision      TEXT DEFAULT '',
        responsable_revision        TEXT DEFAULT ''
    )""")
    # Cambio de Control formal · INVIMA Decreto 219/1998 exige clasificar
    # cambios a fórmulas (mayor/menor), justificar impacto y aprobar antes
    # de modificar. Tabla espejo de formulas_versiones con campos de control.
    c.execute("""CREATE TABLE IF NOT EXISTS cambios_control_formula (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        formula_id        INTEGER NOT NULL,
        clasificacion     TEXT NOT NULL CHECK(clasificacion IN ('mayor','menor')),
        justificacion     TEXT NOT NULL,
        impacto           TEXT,
        cambio_propuesto  TEXT,
        solicitado_por    TEXT NOT NULL,
        fecha_solicitud   TEXT NOT NULL DEFAULT (datetime('now')),
        aprobado_por      TEXT,
        fecha_aprobacion  TEXT,
        estado            TEXT NOT NULL DEFAULT 'pendiente'
                          CHECK(estado IN ('pendiente','aprobado','rechazado','aplicado')),
        version_resultante INTEGER,
        observaciones     TEXT,
        FOREIGN KEY (formula_id) REFERENCES formulas_maestras(id)
    )""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_cc_formula
                 ON cambios_control_formula(formula_id, fecha_solicitud DESC)""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_cc_estado
                 ON cambios_control_formula(estado, fecha_solicitud DESC)""")
    # Versionado generico (fichas_tecnicas, registros_invima, documentos_sgd).
    # Sebastian 3-may-2026: Auditoria INVIMA puede pedir historial completo
    # de cualquier documento regulatorio. formulas_maestras tiene su propia
    # tabla formulas_versiones (legacy); las demas usan esta tabla espejo.
    c.execute("""CREATE TABLE IF NOT EXISTS tecnica_versiones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        entidad         TEXT NOT NULL CHECK(entidad IN ('ficha','invima','sgd')),
        registro_id     INTEGER NOT NULL,
        version_num     INTEGER NOT NULL,
        snapshot_json   TEXT NOT NULL,
        motivo_cambio   TEXT,
        creado_por      TEXT,
        fecha_creacion  TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_tv_entidad_reg
                 ON tecnica_versiones(entidad, registro_id, version_num DESC)""")
    # Migracion one-shot · documentos_sgd legacy → sgd_documentos rico.
    # Idempotente: solo migra los que NO estan ya en sgd_documentos.
    # Sebastian 3-may-2026: unificacion SGD para que /tecnica y /aseguramiento
    # vean la misma fuente.
    try:
        legacy_rows = c.execute("""
            SELECT id, tipo, codigo, nombre, version, fecha_emision,
                   fecha_revision, responsable, estado, url_documento,
                   notas, frecuencia_revision_meses, fecha_proxima_revision,
                   responsable_revision
              FROM documentos_sgd
        """).fetchall()
    except sqlite3.OperationalError:
        legacy_rows = []
    if legacy_rows:
        # Ya migrado? Buscar marca en system table o usar set de codigos
        ya_existen = set()
        for r in c.execute("SELECT codigo FROM sgd_documentos").fetchall():
            ya_existen.add(r[0])
        import re as _re_mig
        for legacy in legacy_rows:
            (lid, tipo_legacy, codigo_legacy, nombre, version, fe, fr,
             resp, estado_legacy, url, notas, frec, fp_rev, resp_rev) = legacy
            codigo_legacy = (codigo_legacy or '').strip().upper()
            if not codigo_legacy or codigo_legacy in ya_existen:
                continue
            # Validar formato AAA-BBB-NNN. Si no matchea, skip (data legacy
            # malformada — operador debe corregir manualmente).
            m = _re_mig.match(r'^([A-Z]{3})-([A-Z]{3})-(\d{1,3})(?:-([A-Z]\d{1,2}))?$',
                              codigo_legacy)
            if not m:
                continue
            area_m, tipo_doc_m, num_m, sub_m = m.groups()
            try:
                num_int = int(num_m)
            except (TypeError, ValueError):
                continue
            estado_mapped = {
                'Vigente': 'vigente', 'En_Revision': 'revision',
                'Obsoleto': 'obsoleto', 'Borrador': 'borrador',
            }.get(estado_legacy, 'vigente')
            try:
                c.execute("""
                    INSERT OR IGNORE INTO sgd_documentos
                      (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                       titulo, version_actual, archivo_pdf_url,
                       fecha_creacion, vigente_desde, fecha_aprobacion,
                       proxima_revision, estado, elaborado_por,
                       aprobado_por, observaciones, creado_por)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (codigo_legacy, area_m, tipo_doc_m, num_int, sub_m,
                       '-'.join([area_m, tipo_doc_m, num_m]) if sub_m else None,
                       nombre or '', version or '1', url or '',
                       fe or '', fe or '', fr or '', fp_rev or '',
                       estado_mapped, resp or '', resp_rev or resp or '',
                       (notas or '') + ' [migrado de documentos_sgd]',
                       'migration-3may2026'))
                ya_existen.add(codigo_legacy)
            except Exception:
                continue
        try:
            conn.commit()
        except Exception:
            pass
    conn.commit()
_init_tecnica()


def _snapshot_tecnica(c, entidad, registro_id, motivo, usuario):
    """Snapshot generico para fichas/invima/sgd antes de UPDATE/DELETE.

    Asigna numero de version incremental por (entidad, registro_id).
    No bloquea el flujo principal: cualquier excepcion se traga.
    """
    import json as _json
    # SGD ahora vive en sgd_documentos (rich, unificado con aseguramiento).
    # Snapshots SGD usan la misma tabla tecnica_versiones — entidad='sgd'
    # apunta a sgd_documentos.id.
    tabla_map = {
        'ficha': 'fichas_tecnicas',
        'invima': 'registros_invima',
        'sgd': 'sgd_documentos',
    }
    tabla = tabla_map.get(entidad)
    if not tabla:
        return
    try:
        row = c.execute(f"SELECT * FROM {tabla} WHERE id=?", (registro_id,)).fetchone()
        if not row:
            return
        snap = dict(row)
        last = c.execute(
            "SELECT MAX(version_num) FROM tecnica_versiones WHERE entidad=? AND registro_id=?",
            (entidad, registro_id)
        ).fetchone()
        ver_num = (last[0] or 0) + 1
        c.execute("""INSERT INTO tecnica_versiones
                     (entidad, registro_id, version_num, snapshot_json, motivo_cambio, creado_por)
                     VALUES (?,?,?,?,?,?)""",
                  (entidad, registro_id, ver_num,
                   _json.dumps(snap, ensure_ascii=False, default=str),
                   motivo, usuario))
    except Exception:
        pass

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
    # Cambio de Control vinculado opcional. Si viene cambio_control_id, debe
    # estar en estado='aprobado' y referenciar esta misma fórmula.
    cc_id = d.get('cambio_control_id')
    cc_row = None
    if cc_id is not None:
        try:
            cc_id = int(cc_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'cambio_control_id invalido'}), 400
        cc_row = c.execute(
            """SELECT id, formula_id, estado, clasificacion
                 FROM cambios_control_formula WHERE id=?""", (cc_id,)
        ).fetchone()
        if not cc_row:
            return jsonify({'error': 'CC no encontrado'}), 404
        if cc_row[1] != fid:
            return jsonify({'error': 'CC no corresponde a esta formula'}), 400
        if cc_row[2] != 'aprobado':
            return jsonify({'error': f'CC en estado {cc_row[2]} · debe estar aprobado'}), 400
    if sets:
        # Snapshot ANTES del UPDATE
        motivo = d.get('motivo_cambio') or (
            f"CC #{cc_id} ({cc_row[3]})" if cc_row else 'Modificacion'
        )
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM formulas_maestras WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        _snapshot_formula(c, fid, motivo, usuario)
        c.execute(f"UPDATE formulas_maestras SET {sets} WHERE id=?", vals)
        # Si vinculo CC, marcarlo como aplicado y registrar version resultante
        if cc_row:
            ver_num = c.execute(
                "SELECT MAX(version_num) FROM formulas_versiones WHERE formula_id=?",
                (fid,)
            ).fetchone()
            c.execute(
                """UPDATE cambios_control_formula
                     SET estado='aplicado', version_resultante=?
                   WHERE id=?""",
                (ver_num[0] if ver_num else None, cc_id)
            )
            audit_log(c, usuario=usuario, accion='APLICAR_CAMBIO_CONTROL',
                      tabla='cambios_control_formula', registro_id=cc_id,
                      antes={'estado': 'aprobado'},
                      despues={'estado': 'aplicado', 'version_resultante': ver_num[0] if ver_num else None},
                      detalle=f"CC aplicado al modificar formula id={fid}")
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
        _snapshot_tecnica(c, 'ficha', fid, 'Eliminacion', usuario)
        c.execute("DELETE FROM fichas_tecnicas WHERE id=?", (fid,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_FICHA', tabla='fichas_tecnicas',
                  registro_id=fid, antes=antes,
                  detalle=f"Eliminó ficha técnica id={fid}" + (f" ({antes.get('codigo','')})" if antes else ""))
        conn.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    allowed = ['nombre', 'formula_id', 'version', 'estado', 'fecha_actualizacion', 'url_documento', 'notas']
    sets = ', '.join(f + '=?' for f in allowed if f in d)
    vals = [d[f] for f in allowed if f in d] + [fid]
    if sets:
        motivo = d.get('motivo_cambio') or 'Modificacion'
        antes_row = c.execute("SELECT codigo, nombre, version, estado FROM fichas_tecnicas WHERE id=?", (fid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        _snapshot_tecnica(c, 'ficha', fid, motivo, usuario)
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
        _snapshot_tecnica(c, 'invima', rid, 'Eliminacion', usuario)
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
        motivo = d.get('motivo_cambio') or 'Modificacion'
        antes_row = c.execute("SELECT producto, num_registro, estado, fecha_vencimiento FROM registros_invima WHERE id=?", (rid,)).fetchone()
        antes = dict(antes_row) if antes_row else None
        _snapshot_tecnica(c, 'invima', rid, motivo, usuario)
        c.execute(f"UPDATE registros_invima SET {sets} WHERE id=?", vals)
        audit_log(c, usuario=usuario, accion='MODIFICAR_REGISTRO_INVIMA', tabla='registros_invima',
                  registro_id=rid, antes=antes,
                  despues={k: d.get(k) for k in d if k in allowed},
                  detalle=f"Modificó registro INVIMA id={rid}")
        conn.commit()
    return jsonify({'ok': True})

# ── Documentos SGD ─────────────────────────────────────────────────────────
# Sebastian 3-may-2026: UNIFICADO con aseguramiento.sgd_documentos.
# Hernando carga SOPs desde /tecnica y aparecen en /aseguramiento. Antes
# eran dos tablas separadas (documentos_sgd legacy + sgd_documentos rico).
# Ahora /api/tecnica/documentos* delega a la tabla rica y traduce campos
# al schema simple que espera el frontend de tecnica.
#
# Mapeo schema simple (tecnica) ↔ rico (aseguramiento):
#   tipo (SOP, BPM, Instruccion, Formato, Manual, Protocolo, Otro)
#     ↔ tipo_doc (PRO, NOR, INS, FOR, MAN, PRO, REG)
#   nombre ↔ titulo
#   version ↔ version_actual
#   fecha_emision ↔ vigente_desde
#   fecha_revision ↔ fecha_aprobacion
#   fecha_proxima_revision ↔ proxima_revision
#   responsable ↔ elaborado_por
#   responsable_revision ↔ aprobado_por
#   estado: Vigente|En_Revision|Obsoleto ↔ vigente|revision|obsoleto
#   url_documento ↔ archivo_pdf_url
#   notas ↔ observaciones
#   frecuencia_revision_meses → calculado de fecha_emision a proxima_revision
#                                (no se persiste · solo se usa para calcular)

_TIPO_TECNICA_A_DOC = {
    'SOP': 'PRO', 'Protocolo': 'PRO',
    'BPM': 'NOR',
    'Instruccion': 'INS',
    'Formato': 'FOR',
    'Manual': 'MAN',
    'Otro': 'REG',
}
_TIPO_DOC_A_TECNICA = {
    'PRO': 'SOP', 'NOR': 'BPM', 'INS': 'Instruccion',
    'FOR': 'Formato', 'MAN': 'Manual',
    'POL': 'Otro', 'EVA': 'Otro', 'ACT': 'Otro',
    'REG': 'Otro', 'DES': 'Otro', 'LMA': 'Otro',
    'PGM': 'Otro', 'CRO': 'Otro',
}
_ESTADO_TECNICA_A_RICH = {
    'Vigente': 'vigente', 'En_Revision': 'revision',
    'Obsoleto': 'obsoleto', 'Borrador': 'borrador',
}
_ESTADO_RICH_A_TECNICA = {
    'vigente': 'Vigente', 'revision': 'En_Revision',
    'obsoleto': 'Obsoleto', 'borrador': 'Borrador',
    'retirado': 'Obsoleto', 'conflicto': 'En_Revision',
}


def _sgd_rich_to_simple(row_dict):
    """Transforma fila de sgd_documentos al schema simple del frontend tecnica."""
    fecha_emi = row_dict.get('vigente_desde') or row_dict.get('fecha_creacion') or ''
    fecha_prox = row_dict.get('proxima_revision') or ''
    # Calcular frecuencia si tenemos ambas fechas
    frecuencia = 12
    if fecha_emi and fecha_prox:
        try:
            from datetime import date as _date
            d1 = _date.fromisoformat(fecha_emi[:10])
            d2 = _date.fromisoformat(fecha_prox[:10])
            meses = round((d2 - d1).days / 30)
            if 1 <= meses <= 60:
                frecuencia = meses
        except Exception:
            pass
    return {
        'id': row_dict.get('id'),
        'tipo': _TIPO_DOC_A_TECNICA.get(row_dict.get('tipo_doc', 'REG'), 'Otro'),
        'codigo': row_dict.get('codigo', ''),
        'nombre': row_dict.get('titulo', ''),
        'version': row_dict.get('version_actual', '1'),
        'fecha_emision': fecha_emi,
        'fecha_revision': row_dict.get('fecha_aprobacion', '') or '',
        'fecha_proxima_revision': fecha_prox,
        'responsable': row_dict.get('elaborado_por', '') or '',
        'responsable_revision': row_dict.get('aprobado_por', '') or '',
        'frecuencia_revision_meses': frecuencia,
        'estado': _ESTADO_RICH_A_TECNICA.get(
            row_dict.get('estado', 'vigente'), 'Vigente'),
        'url_documento': row_dict.get('archivo_pdf_url', '') or '',
        'notas': row_dict.get('observaciones', '') or '',
    }


def _validar_codigo_sgd(codigo):
    """Valida formato AAA-BBB-NNN[-FNN]. Devuelve (ok, error_msg, parts)."""
    import re as _re
    codigo = (codigo or '').strip().upper()
    if not codigo:
        return False, 'codigo requerido', None
    if not _re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{1,3}(?:-[A-Z]\d{1,2})?$', codigo):
        return False, 'codigo formato invalido (esperado AAA-BBB-NNN, ej: COC-PRO-018)', None
    parts = codigo.split('-')
    return True, None, parts


@bp.route('/api/tecnica/documentos', methods=['GET', 'POST'])
def documentos_list():
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')

    if request.method == 'POST':
        d = request.json or {}
        codigo = (d.get('codigo') or '').strip().upper()
        ok, err, parts = _validar_codigo_sgd(codigo)
        if not ok:
            return jsonify({'error': err}), 400
        nombre = (d.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'nombre/titulo requerido'}), 400
        # Mapear schema simple → rico
        area = parts[0]
        tipo_doc_codigo = parts[1]
        try:
            numero = int(parts[2])
        except (ValueError, IndexError):
            return jsonify({'error': 'numero invalido en codigo'}), 400
        subtipo = parts[3] if len(parts) > 3 else None
        padre_codigo = '-'.join(parts[:3]) if subtipo else None
        version = (d.get('version') or '1.0').strip()
        estado_rich = _ESTADO_TECNICA_A_RICH.get(d.get('estado', 'Vigente'), 'vigente')

        from datetime import datetime as _dt, timedelta as _td
        fecha_emision = d.get('fecha_emision') or _dt.now().strftime('%Y-%m-%d')
        try:
            frecuencia = int(d.get('frecuencia_revision_meses', 12))
        except (TypeError, ValueError):
            frecuencia = 12
        fecha_proxima = d.get('fecha_proxima_revision') or ''
        if not fecha_proxima and fecha_emision:
            try:
                em = _dt.strptime(fecha_emision[:10], '%Y-%m-%d')
                fecha_proxima = (em + _td(days=frecuencia*30)).strftime('%Y-%m-%d')
            except Exception:
                pass

        # Idempotencia: si ya existe codigo, retornar conflicto
        existe = c.execute("SELECT id FROM sgd_documentos WHERE codigo=?", (codigo,)).fetchone()
        if existe:
            return jsonify({'error': f'codigo {codigo} ya existe (id={existe[0]}). Usa PATCH para actualizar.'}), 409

        c.execute("""INSERT INTO sgd_documentos
                     (codigo, area, tipo_doc, numero, subtipo, padre_codigo,
                      titulo, version_actual, archivo_pdf_url,
                      fecha_creacion, vigente_desde, proxima_revision,
                      estado, elaborado_por, aprobado_por,
                      observaciones, creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (codigo, area, tipo_doc_codigo, numero, subtipo, padre_codigo,
                   nombre, version, d.get('url_documento') or '',
                   fecha_emision, fecha_emision, fecha_proxima,
                   estado_rich, d.get('responsable') or '',
                   d.get('responsable_revision') or d.get('responsable') or '',
                   d.get('notas') or '', usuario))
        did = c.lastrowid
        audit_log(c, usuario=usuario, accion='CREAR_SGD', tabla='sgd_documentos',
                  registro_id=did,
                  despues={'codigo': codigo, 'titulo': nombre[:100], 'estado': estado_rich},
                  detalle=f"Creó SGD {codigo} · {nombre[:80]}")
        conn.commit()
        return jsonify({'ok': True, 'id': did, 'codigo': codigo,
                        'fecha_proxima_revision': fecha_proxima})

    # GET
    rows = c.execute("""
        SELECT id, codigo, area, tipo_doc, titulo, version_actual,
               vigente_desde, fecha_aprobacion, proxima_revision,
               elaborado_por, aprobado_por, estado, archivo_pdf_url,
               observaciones, fecha_creacion
          FROM sgd_documentos
          WHERE estado <> 'retirado'
          ORDER BY tipo_doc, codigo
    """).fetchall()
    cols = [x[0] for x in c.description]
    return jsonify([_sgd_rich_to_simple(dict(zip(cols, r))) for r in rows])


@bp.route('/api/tecnica/documentos/proximos-vencimientos')
def documentos_vencimientos():
    """Lista SGDs vigentes con proxima_revision <= +60d. Lee de sgd_documentos."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, codigo, tipo_doc, titulo, version_actual,
               proxima_revision, aprobado_por, vigente_desde,
               julianday(proxima_revision) - julianday('now') as dias_restantes
          FROM sgd_documentos
         WHERE estado='vigente'
           AND COALESCE(proxima_revision,'') != ''
           AND proxima_revision <= date('now','+60 day')
         ORDER BY proxima_revision ASC
    """).fetchall()
    out = []
    for r in rows:
        # Calcular frecuencia derivada
        frecuencia = 12
        if r[5] and r[7]:
            try:
                from datetime import date as _date
                meses = round((_date.fromisoformat(r[5][:10]) - _date.fromisoformat(r[7][:10])).days / 30)
                if 1 <= meses <= 60:
                    frecuencia = meses
            except Exception:
                pass
        out.append({
            'id': r[0],
            'codigo': r[1],
            'tipo': _TIPO_DOC_A_TECNICA.get(r[2], 'Otro'),
            'nombre': r[3],
            'version': r[4],
            'fecha_proxima_revision': r[5],
            'responsable_revision': r[6] or '',
            'frecuencia_revision_meses': frecuencia,
            'dias_restantes': r[8],
        })
    return jsonify({'documentos': out})


@bp.route('/api/tecnica/documentos/<int:did>/marcar-revisado', methods=['POST'])
def documento_revisado(did):
    """Marca SGD como revisado HOY + reprograma proxima_revision en sgd_documentos."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import datetime as _dt, timedelta as _td
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        "SELECT codigo, vigente_desde, proxima_revision FROM sgd_documentos WHERE id=?",
        (did,)).fetchone()
    if not row:
        return jsonify({'error': 'Documento no encontrado'}), 404
    # Calcular frecuencia derivada
    frecuencia = 12
    if row[1] and row[2]:
        try:
            from datetime import date as _date
            meses = round((_date.fromisoformat(row[2][:10]) - _date.fromisoformat(row[1][:10])).days / 30)
            if 1 <= meses <= 60:
                frecuencia = meses
        except Exception:
            pass
    hoy = _dt.now().strftime('%Y-%m-%d')
    proxima = (_dt.now() + _td(days=frecuencia*30)).strftime('%Y-%m-%d')
    c.execute("""UPDATE sgd_documentos
                 SET fecha_aprobacion=?, vigente_desde=?, proxima_revision=?,
                     actualizado_en=datetime('now')
                 WHERE id=?""", (hoy, hoy, proxima, did))
    audit_log(c, usuario=session.get('compras_user', 'sistema'),
              accion='REVISAR_SGD', tabla='sgd_documentos', registro_id=did,
              despues={'fecha_revision': hoy, 'fecha_proxima_revision': proxima},
              detalle=f"Revisó SGD {row[0]} · próxima {proxima}")
    conn.commit()
    return jsonify({'ok': True, 'fecha_revision': hoy, 'fecha_proxima_revision': proxima})


@bp.route('/api/tecnica/documentos/<int:did>', methods=['PATCH', 'DELETE'])
def documento_update(did):
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    usuario = session.get('compras_user', 'sistema')
    if request.method == 'DELETE':
        if usuario not in ADMIN_USERS:
            return jsonify({'error': 'Solo administradores'}), 403
        antes_row = c.execute(
            "SELECT codigo, titulo, version_actual, estado FROM sgd_documentos WHERE id=?",
            (did,)).fetchone()
        if not antes_row:
            return jsonify({'error': 'Documento no encontrado'}), 404
        antes = {'codigo': antes_row[0], 'titulo': antes_row[1],
                  'version': antes_row[2], 'estado': antes_row[3]}
        # Soft delete: marcar como retirado en lugar de DELETE (preserva historico)
        c.execute("""UPDATE sgd_documentos SET estado='retirado',
                     actualizado_en=datetime('now') WHERE id=?""", (did,))
        audit_log(c, usuario=usuario, accion='ELIMINAR_SGD',
                  tabla='sgd_documentos', registro_id=did, antes=antes,
                  detalle=f"Retiró SGD id={did} ({antes['codigo']})")
        conn.commit()
        return jsonify({'ok': True})

    d = request.json or {}
    # Mapeo simple → rico para UPDATE. Solo campos que matchean.
    set_clauses = []
    vals = []
    if 'nombre' in d:
        set_clauses.append('titulo=?'); vals.append(d['nombre'])
    if 'version' in d:
        set_clauses.append('version_actual=?'); vals.append(d['version'])
    if 'fecha_emision' in d:
        set_clauses.append('vigente_desde=?'); vals.append(d['fecha_emision'])
    if 'fecha_revision' in d:
        set_clauses.append('fecha_aprobacion=?'); vals.append(d['fecha_revision'])
    if 'fecha_proxima_revision' in d:
        set_clauses.append('proxima_revision=?'); vals.append(d['fecha_proxima_revision'])
    if 'responsable' in d:
        set_clauses.append('elaborado_por=?'); vals.append(d['responsable'])
    if 'responsable_revision' in d:
        set_clauses.append('aprobado_por=?'); vals.append(d['responsable_revision'])
    if 'estado' in d:
        set_clauses.append('estado=?')
        vals.append(_ESTADO_TECNICA_A_RICH.get(d['estado'], 'vigente'))
    if 'url_documento' in d:
        set_clauses.append('archivo_pdf_url=?'); vals.append(d['url_documento'])
    if 'notas' in d:
        set_clauses.append('observaciones=?'); vals.append(d['notas'])
    # Cambio de tipo va junto con codigo (no se permite cambiar tipo aislado)
    # frecuencia_revision_meses se traduce a recalcular proxima_revision
    if 'frecuencia_revision_meses' in d and 'fecha_proxima_revision' not in d:
        try:
            frec = int(d['frecuencia_revision_meses'])
            row = c.execute(
                "SELECT vigente_desde FROM sgd_documentos WHERE id=?", (did,)
            ).fetchone()
            if row and row[0]:
                from datetime import datetime as _dt, timedelta as _td
                em = _dt.strptime(row[0][:10], '%Y-%m-%d')
                set_clauses.append('proxima_revision=?')
                vals.append((em + _td(days=frec*30)).strftime('%Y-%m-%d'))
        except Exception:
            pass

    if not set_clauses:
        return jsonify({'ok': True, 'aviso': 'sin cambios'})

    motivo = d.get('motivo_cambio') or 'Modificacion'
    antes_row = c.execute(
        "SELECT codigo, titulo, version_actual, estado FROM sgd_documentos WHERE id=?",
        (did,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Documento no encontrado'}), 404
    antes = {'codigo': antes_row[0], 'titulo': antes_row[1],
              'version': antes_row[2], 'estado': antes_row[3]}
    _snapshot_tecnica(c, 'sgd', did, motivo, usuario)
    set_clauses.append("actualizado_en=datetime('now')")
    c.execute(f"UPDATE sgd_documentos SET {', '.join(set_clauses)} WHERE id=?",
              vals + [did])
    audit_log(c, usuario=usuario, accion='MODIFICAR_SGD',
              tabla='sgd_documentos', registro_id=did, antes=antes,
              despues={k: d.get(k) for k in d if k in (
                  'nombre','version','estado','fecha_proxima_revision',
                  'responsable','responsable_revision')},
              detalle=f"Modificó SGD {antes['codigo']} · motivo: {motivo}")
    conn.commit()
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────────────────────────────
#  Versionado generico (lectura)
# ─────────────────────────────────────────────────────────────────────────

@bp.route('/api/tecnica/<entidad>/<int:rid>/versiones', methods=['GET'])
def tecnica_versiones_list(entidad, rid):
    """Lista historial de versiones de una ficha/invima/sgd."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    if entidad not in ('fichas', 'invima', 'documentos'):
        return jsonify({'error': 'entidad invalida'}), 400
    ent_map = {'fichas': 'ficha', 'invima': 'invima', 'documentos': 'sgd'}
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT id, version_num, motivo_cambio, creado_por, fecha_creacion
          FROM tecnica_versiones
         WHERE entidad=? AND registro_id=?
         ORDER BY version_num DESC
    """, (ent_map[entidad], rid)).fetchall()
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols, r)) for r in rows])


@bp.route('/api/tecnica/<entidad>/<int:rid>/versiones/<int:vid>', methods=['GET'])
def tecnica_version_detalle(entidad, rid, vid):
    """Snapshot completo de una version específica."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    if entidad not in ('fichas', 'invima', 'documentos'):
        return jsonify({'error': 'entidad invalida'}), 400
    ent_map = {'fichas': 'ficha', 'invima': 'invima', 'documentos': 'sgd'}
    import json as _json
    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT id, entidad, registro_id, version_num, snapshot_json,
               motivo_cambio, creado_por, fecha_creacion
          FROM tecnica_versiones
         WHERE entidad=? AND registro_id=? AND id=?
    """, (ent_map[entidad], rid, vid)).fetchone()
    if not row:
        return jsonify({'error': 'Version no encontrada'}), 404
    out = dict(row)
    try:
        out['snapshot'] = _json.loads(out.pop('snapshot_json'))
    except Exception:
        out['snapshot'] = {}
        out.pop('snapshot_json', None)
    return jsonify(out)


# ─────────────────────────────────────────────────────────────────────────
#  CROSS-CHECK · INVIMA vs Stock Vendible
# ─────────────────────────────────────────────────────────────────────────
# Sebastian 2-may-2026: el director técnico necesita saber QUE PRODUCTOS
# en venta NO tienen registro INVIMA vigente. Riesgo regulatorio alto: si
# Animus vende un SKU sin notificación sanitaria activa, INVIMA puede
# decomisar lote + multar. Cruz por nombre de producto (matching fuzzy).

def _match_invima(producto_pt, registros_invima):
    """Encuentra registro INVIMA que matchea con un producto de stock_pt.

    Match: LOWER + sin acentos + containment bidireccional + match por
    palabras significativas (>3 chars, 2+ overlap). Devuelve la fila
    completa del registro o None.
    """
    if not producto_pt:
        return None
    import unicodedata
    def _norm(s):
        s = (s or '').strip().lower()
        s = unicodedata.normalize('NFD', s)
        return ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    npt = _norm(producto_pt)
    if not npt:
        return None
    # 1. Match por containment
    for r in registros_invima:
        nr = _norm(r.get('producto', ''))
        if nr and (npt in nr or nr in npt):
            return r
    # 2. Match por palabras (>=2 palabras significativas en común)
    pa = set(w for w in npt.split() if len(w) > 3)
    if len(pa) < 2:
        return None
    for r in registros_invima:
        nr = _norm(r.get('producto', ''))
        pb = set(w for w in nr.split() if len(w) > 3)
        if len(pa & pb) >= 2:
            return r
    return None


# ─────────────────────────────────────────────────────────────────────────
#  CAMBIO DE CONTROL · INVIMA Decreto 219/1998
# ─────────────────────────────────────────────────────────────────────────
# Toda modificación a una fórmula registrada debe pasar por un flujo
# formal: solicitud → clasificación (mayor/menor) → justificación e
# impacto → aprobación admin → aplicación. Esto deja trazabilidad
# regulatoria si INVIMA audita.

@bp.route('/api/tecnica/cambios-control', methods=['GET', 'POST'])
def cambios_control_list():
    """GET: lista cambios de control (filtra por estado y formula_id).
    POST: solicita nuevo cambio de control."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        usuario = session.get('compras_user', 'sistema')
        # Validaciones
        formula_id = d.get('formula_id')
        if not formula_id:
            return jsonify({'error': 'formula_id requerido'}), 400
        try:
            formula_id = int(formula_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'formula_id invalido'}), 400
        clasif = (d.get('clasificacion') or '').strip().lower()
        if clasif not in ('mayor', 'menor'):
            return jsonify({'error': "clasificacion debe ser 'mayor' o 'menor'"}), 400
        justificacion = (d.get('justificacion') or '').strip()
        if len(justificacion) < 20:
            return jsonify({'error': 'justificacion muy corta (min 20 chars)'}), 400
        # Verificar que formula existe
        existe = c.execute(
            "SELECT id, codigo FROM formulas_maestras WHERE id=?", (formula_id,)
        ).fetchone()
        if not existe:
            return jsonify({'error': 'formula no encontrada'}), 404
        c.execute("""INSERT INTO cambios_control_formula
                     (formula_id, clasificacion, justificacion, impacto,
                      cambio_propuesto, solicitado_por, estado, observaciones)
                     VALUES (?,?,?,?,?,?,'pendiente',?)""",
                  (formula_id, clasif, justificacion,
                   (d.get('impacto') or '').strip(),
                   (d.get('cambio_propuesto') or '').strip(),
                   usuario, (d.get('observaciones') or '').strip()))
        cc_id = c.lastrowid
        audit_log(c, usuario=usuario, accion='SOLICITAR_CAMBIO_CONTROL',
                  tabla='cambios_control_formula', registro_id=cc_id,
                  despues={'formula_id': formula_id, 'clasificacion': clasif,
                            'estado': 'pendiente'},
                  detalle=f"Solicitó CC {clasif} sobre formula {existe[1]}")
        conn.commit()
        # Notificar admins (TECNICA_USERS) que hay un CC pendiente
        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                ['sebastian', 'alejandro', 'hernando', 'miguel'],
                'tecnica',
                f'🔄 Cambio de Control {clasif.upper()} solicitado',
                body=f'Fórmula {existe[1]} · solicitado por {usuario}\n{justificacion[:200]}',
                link='/tecnica',
                remitente=usuario,
                importante=(clasif == 'mayor'),
            )
        except Exception:
            pass
        return jsonify({'ok': True, 'id': cc_id, 'estado': 'pendiente'})
    # GET
    formula_id = request.args.get('formula_id')
    estado = request.args.get('estado')
    where = []
    params = []
    if formula_id:
        try:
            where.append('cc.formula_id=?'); params.append(int(formula_id))
        except ValueError:
            return jsonify({'error': 'formula_id invalido'}), 400
    if estado:
        if estado not in ('pendiente', 'aprobado', 'rechazado', 'aplicado'):
            return jsonify({'error': 'estado invalido'}), 400
        where.append('cc.estado=?'); params.append(estado)
    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''
    rows = c.execute(f"""
        SELECT cc.id, cc.formula_id, fm.codigo, fm.nombre,
               cc.clasificacion, cc.justificacion, cc.impacto,
               cc.cambio_propuesto, cc.solicitado_por, cc.fecha_solicitud,
               cc.aprobado_por, cc.fecha_aprobacion, cc.estado,
               cc.version_resultante, cc.observaciones
          FROM cambios_control_formula cc
          LEFT JOIN formulas_maestras fm ON fm.id = cc.formula_id
          {where_sql}
          ORDER BY cc.fecha_solicitud DESC
          LIMIT 200
    """, params).fetchall()
    cols = [x[0] for x in c.description]
    return jsonify({'cambios': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/tecnica/cambios-control/<int:cc_id>/aprobar', methods=['POST'])
def cambio_control_aprobar(cc_id):
    """Aprueba (o rechaza) un cambio de control. Solo admins.

    Body: {decision: 'aprobar'|'rechazar', observaciones?: str}
    """
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    usuario = session.get('compras_user', 'sistema')
    if usuario not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden aprobar'}), 403
    d = request.json or {}
    decision = (d.get('decision') or '').strip().lower()
    if decision not in ('aprobar', 'rechazar'):
        return jsonify({'error': "decision debe ser 'aprobar' o 'rechazar'"}), 400
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        """SELECT id, formula_id, estado, clasificacion, solicitado_por
             FROM cambios_control_formula WHERE id=?""", (cc_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'CC no encontrado'}), 404
    if row[2] != 'pendiente':
        return jsonify({'error': f'CC ya esta en estado {row[2]} (solo pendientes pueden aprobarse)'}), 400
    nuevo_estado = 'aprobado' if decision == 'aprobar' else 'rechazado'
    obs = (d.get('observaciones') or '').strip()
    c.execute("""UPDATE cambios_control_formula
                 SET estado=?, aprobado_por=?,
                     fecha_aprobacion=datetime('now'),
                     observaciones=COALESCE(NULLIF(?,''), observaciones)
                 WHERE id=?""", (nuevo_estado, usuario, obs, cc_id))
    audit_log(c, usuario=usuario,
              accion='APROBAR_CAMBIO_CONTROL' if decision == 'aprobar' else 'RECHAZAR_CAMBIO_CONTROL',
              tabla='cambios_control_formula', registro_id=cc_id,
              antes={'estado': 'pendiente'},
              despues={'estado': nuevo_estado, 'observaciones': obs[:200]},
              detalle=f"{decision.title()} CC #{cc_id} · formula_id={row[1]}")
    conn.commit()
    # Notif al solicitante
    try:
        from blueprints.notif import push_notif
        push_notif(
            row[4], 'tecnica',
            f'{"✅" if decision == "aprobar" else "❌"} CC #{cc_id} {nuevo_estado}',
            body=f'Tu solicitud de cambio de control fue {nuevo_estado} por {usuario}.' +
                 (f'\nObservaciones: {obs}' if obs else ''),
            link='/tecnica', remitente=usuario,
        )
    except Exception:
        pass
    return jsonify({'ok': True, 'estado': nuevo_estado})


@bp.route('/api/tecnica/cambios-control/<int:cc_id>/aplicar', methods=['POST'])
def cambio_control_aplicar(cc_id):
    """Marca un CC aprobado como 'aplicado' una vez que la modificación a la
    fórmula efectivamente se realizó (vincula con version_num resultante)."""
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    usuario = session.get('compras_user', 'sistema')
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    row = c.execute(
        """SELECT id, formula_id, estado FROM cambios_control_formula WHERE id=?""",
        (cc_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'CC no encontrado'}), 404
    if row[2] != 'aprobado':
        return jsonify({'error': 'solo CCs aprobados pueden aplicarse'}), 400
    version_resultante = d.get('version_resultante')
    try:
        version_resultante = int(version_resultante) if version_resultante else None
    except (TypeError, ValueError):
        version_resultante = None
    c.execute("""UPDATE cambios_control_formula
                 SET estado='aplicado', version_resultante=?
                 WHERE id=?""", (version_resultante, cc_id))
    audit_log(c, usuario=usuario, accion='APLICAR_CAMBIO_CONTROL',
              tabla='cambios_control_formula', registro_id=cc_id,
              antes={'estado': 'aprobado'},
              despues={'estado': 'aplicado', 'version_resultante': version_resultante},
              detalle=f"Aplicó CC #{cc_id} · version v{version_resultante or '?'}")
    conn.commit()
    return jsonify({'ok': True, 'estado': 'aplicado'})


@bp.route('/api/tecnica/productos-sin-invima', methods=['GET'])
def productos_sin_invima():
    """Lista productos en stock_pt con disponibilidad que NO tienen INVIMA
    vigente (sin registro o registro vencido).

    Query params:
        umbral_dias (int, default 90): considerar 'por vencer' los registros
            con fecha_vencimiento dentro de N días. Aparecen como warning.
        empresa (str, default todas): filtrar por empresa de stock_pt.

    Devuelve:
        sin_invima: productos con stock disponible y SIN registro vigente
        por_vencer: productos con INVIMA vigente que vence pronto (<= umbral)
        cobertura: resumen del % de SKUs cubiertos
    """
    if not _check_access():
        return jsonify({'error': 'No autorizado'}), 401
    try:
        umbral = int(request.args.get('umbral_dias', 90))
    except (TypeError, ValueError):
        umbral = 90
    umbral = max(1, min(umbral, 365))
    empresa = request.args.get('empresa', '').strip()

    conn = get_db(); c = conn.cursor()
    # Cargar registros INVIMA Vigentes con fecha_vencimiento futura/null
    inv_rows = c.execute("""
        SELECT id, producto, num_registro, tipo_tramite, fecha_expedicion,
               fecha_vencimiento, estado
          FROM registros_invima
         WHERE LOWER(COALESCE(estado,'')) = 'vigente'
    """).fetchall()
    cols_inv = [x[0] for x in c.description]
    invima_vigentes = [dict(zip(cols_inv, r)) for r in inv_rows]

    # Productos vendibles agrupados por SKU + descripción
    where_emp = ""
    params = []
    if empresa:
        where_emp = " WHERE empresa = ?"
        params.append(empresa)
    pt_rows = c.execute(f"""
        SELECT sku, descripcion, empresa,
               SUM(COALESCE(unidades_disponible,0)) as disp,
               COUNT(*) as lotes,
               GROUP_CONCAT(DISTINCT estado) as estados
          FROM stock_pt
          {where_emp}
         GROUP BY sku, descripcion, empresa
         HAVING SUM(COALESCE(unidades_disponible,0)) > 0
         ORDER BY disp DESC
    """, params).fetchall()

    sin_invima = []
    por_vencer = []
    con_invima_ok = []
    from datetime import datetime as _dt
    hoy = _dt.now().date()
    for sku, desc, emp, disp, lotes, estados in pt_rows:
        match = _match_invima(desc, invima_vigentes)
        if not match:
            sin_invima.append({
                'sku': sku, 'descripcion': desc or '', 'empresa': emp,
                'unidades_disponibles': int(disp or 0),
                'lotes_pt': int(lotes or 0),
                'razon': 'sin_registro_vigente',
            })
            continue
        # Hay match — verificar fecha_vencimiento
        fv = match.get('fecha_vencimiento') or ''
        dias_rest = None
        if fv:
            try:
                fv_d = _dt.strptime(fv[:10], '%Y-%m-%d').date()
                dias_rest = (fv_d - hoy).days
            except Exception:
                dias_rest = None
        if dias_rest is not None and dias_rest < 0:
            sin_invima.append({
                'sku': sku, 'descripcion': desc or '', 'empresa': emp,
                'unidades_disponibles': int(disp or 0),
                'lotes_pt': int(lotes or 0),
                'razon': 'registro_vencido',
                'invima_match': {
                    'id': match['id'], 'producto': match['producto'],
                    'num_registro': match['num_registro'],
                    'fecha_vencimiento': fv,
                    'dias_vencido': abs(dias_rest),
                },
            })
            continue
        if dias_rest is not None and dias_rest <= umbral:
            por_vencer.append({
                'sku': sku, 'descripcion': desc or '', 'empresa': emp,
                'unidades_disponibles': int(disp or 0),
                'lotes_pt': int(lotes or 0),
                'invima': {
                    'id': match['id'], 'producto': match['producto'],
                    'num_registro': match['num_registro'],
                    'fecha_vencimiento': fv,
                    'dias_restantes': dias_rest,
                },
            })
        else:
            con_invima_ok.append({
                'sku': sku, 'descripcion': desc or '', 'empresa': emp,
                'unidades_disponibles': int(disp or 0),
                'invima_num_registro': match['num_registro'],
                'fecha_vencimiento': fv or 'sin fecha',
                'dias_restantes': dias_rest,
            })
    total_skus = len(pt_rows)
    cubiertos = total_skus - len(sin_invima)
    pct_cobertura = round((cubiertos / total_skus) * 100) if total_skus else 0
    return jsonify({
        'umbral_dias': umbral,
        'empresa_filtro': empresa or None,
        'cobertura': {
            'total_skus': total_skus,
            'con_invima_vigente': cubiertos,
            'sin_invima_o_vencido': len(sin_invima),
            'por_vencer': len(por_vencer),
            'pct_cobertura': pct_cobertura,
        },
        'sin_invima': sin_invima,
        'por_vencer': por_vencer,
        'con_invima_ok': con_invima_ok,
    })
