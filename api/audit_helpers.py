"""Helpers regulatorios reutilizables · audit_log + race-safe codigo + retry.

Sebastián 2-may-2026: extraído de blueprints/aseguramiento.py para uso global
después de la auditoría zero-error. Permite que TODOS los blueprints
(compras, contabilidad, planta, calidad, compliance) compartan la misma
implementación de:

1. `audit_log()` · INSERT centralizado a tabla audit_log con schema unificado
   (usuario, accion, tabla, registro_id, detalle, antes, despues, ip, fecha).
   Errores se loguean con log.warning, NO se silencian con `try: except: pass`.

2. `intentar_insert_con_retry()` · wrapper para POSTs que generan códigos
   secuenciales (DESV-AAAA-NNNN, OC-2026-NNNN, etc.) con retry hasta 5 veces
   ante IntegrityError sobre `codigo` (race condition entre requests).

3. `siguiente_codigo_secuencial()` · helper genérico SELECT MAX + format.
   Caller debe usar `intentar_insert_con_retry()` para race-safety completa.

Compatible con la migración 91 (audit_log columnas antes/despues).
Si la migración no se aplicó, hace fallback al schema mínimo.

──────────────────────────────────────────────────────────────────────────────
Sebastián 12-may-2026 · Part 11 §11.10(e) · audit_log INMUTABLE + indep opcional
──────────────────────────────────────────────────────────────────────────────
La protección principal es la migración 105: triggers SQL que bloquean UPDATE
y DELETE sobre `audit_log`. Eso garantiza la inmutabilidad ("secure" en el
texto del §11.10(e)) sin importar el camino del INSERT.

Además, `audit_log()` soporta dos modos:

- Modo **legacy** (cursor pasado, `c=cursor`): inserta dentro de la transacción
  del caller. Si el caller hace ROLLBACK, el rastro también rollback. Es lo
  que hacían los ~485 call sites pre-existentes y mantiene compatibilidad
  con el patrón "una conn por request".

- Modo **independent** (cursor `None`, recomendado para nuevos call sites):
  abre una conn SQLite separada con autocommit (`isolation_level=None`) y
  escribe el INSERT ahí. El rastro queda incluso si la operación principal
  falla — útil para forensia y para Part 11 puro ("independently recorded").
  Migrar call sites a este modo de a uno, midiendo impacto en concurrencia.
"""
import json as _json
import logging
import os as _os
import sqlite3 as _sqlite3
from datetime import datetime
from flask import request

log = logging.getLogger('audit_helpers')


def _audit_conn():
    """Conexión SQLite dedicada al audit_log con autocommit.

    Cada llamada a audit_log() abre una conexión nueva, escribe el INSERT
    en autocommit (isolation_level=None) y la cierra. La conexión es
    INDEPENDIENTE de la transacción que esté corriendo en el request actual:
    si el caller hace ROLLBACK la evidencia queda persistida igual.

    `busy_timeout=10000` cubre el caso de 3 workers Gunicorn con WAL escribiendo
    al mismo tiempo. SQLite WAL permite N readers + 1 writer concurrente, así
    que el lock real es muy breve (sub-milisegundo en INSERTs cortos).
    """
    if _os.environ.get('EOS_DB_BACKEND', '').strip().lower() == 'postgres':
        # Migración Fase 3 · conexión Postgres autocommit (equivale al
        # isolation_level=None de SQLite · cada INSERT se confirma solo).
        from pg_adapter import connect as _pg_connect
        return _pg_connect(autocommit=True)
    db_path = _os.environ.get("DB_PATH", "/var/data/inventario.db")
    conn = _sqlite3.connect(db_path, isolation_level=None, timeout=10.0)
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def audit_log(c=None, *, usuario, accion, registro_id, tabla=None,
                antes=None, despues=None, detalle=None):
    """INSERT a audit_log para evidencia regulatoria (Part 11 §11.10(e)).

    Args:
        c: cursor SQLite del caller para inserción en la misma transacción
           (modo legacy, default de los ~485 call sites). Si se pasa `None`,
           audit_log abre una conn separada con autocommit (modo independent,
           recomendado para call sites nuevos · ver docstring del módulo).
           La inmutabilidad la garantiza el trigger SQL de la mig 105 en
           ambos modos.
        usuario: username del actor.
        accion: string corto identificador (ej. 'CERRAR_DESVIACION', 'PAGAR_OC').
        registro_id: ID o código del registro afectado.
        tabla: nombre de la tabla afectada (opcional, recomendado).
        antes: estado anterior · dict serializable (opcional).
        despues: estado nuevo · dict serializable (opcional).
        detalle: descripción libre (opcional).

    Errores: NO se silencian. Se loguea con log.warning si la inserción
    falla. Si la migración 91 no se aplicó (sin columnas antes/despues),
    hace fallback al schema mínimo (usuario, accion, tabla, registro_id,
    detalle, ip, fecha).
    """
    # IP del cliente (si estamos en request context)
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')[:45]
    except RuntimeError:
        ip = ''  # fuera de request context (cron, script)

    antes_s = _json.dumps(antes) if antes is not None and not isinstance(antes, str) else antes
    despues_s = _json.dumps(despues) if despues is not None and not isinstance(despues, str) else despues
    registro_id_s = str(registro_id) if registro_id is not None else None

    # Resolver executor: cursor del caller (legacy) o conn separada autocommit (Part 11 puro).
    independent_conn = None
    if c is None:
        try:
            independent_conn = _audit_conn()
            executor = independent_conn
        except Exception as e:
            log.exception('audit_log: no pude abrir conn separada: %s', e)
            raise
    else:
        executor = c

    try:
        try:
            executor.execute("""
                INSERT INTO audit_log (usuario, accion, tabla, registro_id,
                                         detalle, antes, despues, ip, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (usuario or '', accion, tabla, registro_id_s,
                  detalle, antes_s, despues_s, ip))
        except _sqlite3.OperationalError as e:
            msg = str(e).lower()
            if 'no column named' in msg or 'has no column' in msg:
                # Migración 91 no aplicada · fallback al schema mínimo
                log.warning('audit_log antes/despues no disponible · fallback: %s', e)
                executor.execute("""
                    INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (usuario or '', accion, tabla, registro_id_s, detalle, ip))
            else:
                raise
    except Exception as e:
        log.exception('audit_log fallo: %s', e)
        raise  # regulatorio · debe rollback la operación si falla la auditoría
    finally:
        if independent_conn is not None:
            try:
                independent_conn.close()
            except Exception:
                pass


def siguiente_codigo_secuencial(c, prefijo, tabla, columna='codigo', anio=None):
    """Genera código <prefijo>-AAAA-NNNN secuencial · SELECT MAX + format.

    NO race-safe por sí solo. Usar con `intentar_insert_con_retry()`.

    Args:
        c: cursor SQLite.
        prefijo: prefijo del código (ej. 'DESV', 'OC', 'CHG').
        tabla: tabla a consultar.
        columna: nombre de la columna del código (default 'codigo').
        anio: año a usar (default: año actual).

    Returns:
        Próximo código en formato `<prefijo>-AAAA-NNNN`.
    """
    if anio is None:
        anio = datetime.now().year
    row = c.execute(
        f"SELECT {columna} FROM {tabla} WHERE {columna} LIKE ? "
        f"ORDER BY id DESC LIMIT 1",
        (f'{prefijo}-{anio}-%',),
    ).fetchone()
    if row and row[0]:
        try:
            return f'{prefijo}-{anio}-{int(row[0].split("-")[-1])+1:04d}'
        except (ValueError, IndexError):
            pass
    return f'{prefijo}-{anio}-0001'


def siguiente_numero_oc(c, anio=None):
    """Próximo 'OC-AAAA-NNNN' PG-SAFE (extrae el correlativo en Python).

    FIX · 16-jun-2026 · drift SQLite↔PG. El patrón viejo
    `SELECT MAX(CAST(SUBSTR(numero_oc,9) AS INTEGER))` revienta en PostgreSQL
    cuando una OC tiene sufijo no numérico (ej. 'OC-2026-0215-1', que generan las
    OCs de influencer al colisionar): `CAST('0215-1' AS INTEGER)` → "invalid
    input syntax for type integer" → 500 en TODA creación de OC del año. SQLite
    lo toleraba devolviendo 0. Aquí se trae los numero_oc del año y se extrae el
    correlativo (dígitos iniciales tras 'OC-AAAA-') ignorando sufijos. NO es
    race-safe por sí solo: usar con un loop de reintento por UNIQUE en el caller.
    """
    import re as _re
    y = str(anio) if anio else datetime.now().strftime('%Y')
    pref = f'OC-{y}-'
    c.execute("SELECT numero_oc FROM ordenes_compra WHERE numero_oc LIKE ?", (pref + '%',))
    mx = 0
    for row in c.fetchall():
        n = (row[0] if not isinstance(row, str) else row) or ''
        m = _re.match(r'(\d+)', n[len(pref):])
        if m:
            try:
                mx = max(mx, int(m.group(1)))
            except (ValueError, OverflowError):
                pass
    return f'{pref}{mx + 1:04d}'


def siguiente_correlativo(c, tabla, columna, prefijo):
    """Próximo correlativo ENTERO (int) para un numerador '<prefijo>NNNN...' PG-SAFE.

    FIX · 7-jul-2026 (audit ultracode · M45) · generaliza `siguiente_numero_oc` a SOL/OS/AUTO.
    El patrón viejo `MAX(CAST(SUBSTR(numero,N) AS INTEGER))` revienta en PostgreSQL si algún
    número trae sufijo no numérico (ej. 'SOL-2026-0215-1') → "invalid input syntax for type
    integer" → 500 en TODA creación del año. Trae los números del año y extrae el correlativo
    (dígitos iniciales tras el prefijo) en Python, ignorando sufijos. Devuelve el ENTERO (el
    caller formatea como quiera). NO race-safe: usar con retry por UNIQUE en el caller.

    Args:
        tabla/columna: de dónde leer (ej. 'solicitudes_compra','numero').
        prefijo: prefijo completo con año si aplica (ej. 'SOL-2026-', 'OS-2026-', 'AUTO-').
    Returns: int — el próximo correlativo (max_existente + 1; 1 si no hay ninguno).
    """
    import re as _re
    c.execute(f"SELECT {columna} FROM {tabla} WHERE {columna} LIKE ?", (str(prefijo) + '%',))
    mx = 0
    _pl = len(str(prefijo))
    for row in c.fetchall():
        n = (row[0] if not isinstance(row, (str, int)) else row)
        n = '' if n is None else str(n)
        m = _re.match(r'(\d+)', n[_pl:])
        if m:
            try:
                mx = max(mx, int(m.group(1)))
            except (ValueError, OverflowError):
                pass
    return mx + 1


def intentar_insert_con_retry(insert_fn, *, max_intentos=5, columna='codigo'):
    """Ejecuta insert_fn() con retry si falla por UNIQUE (race condition).

    insert_fn debe devolver (codigo_intentado, lastrowid_o_None) en éxito.
    Si IntegrityError menciona la columna del código, reintenta hasta
    max_intentos veces. Para otros errores (NOT NULL, FK, etc.), propaga.

    Args:
        insert_fn: función que ejecuta el INSERT y retorna (codigo, id).
        max_intentos: cuántas veces reintenta antes de propagar.
        columna: nombre de la columna en mensaje IntegrityError (default 'codigo').

    Returns:
        Lo que devuelva insert_fn.
    """
    for intento in range(max_intentos):
        try:
            return insert_fn()
        except _sqlite3.IntegrityError as e:
            if columna.lower() in str(e).lower() and intento < max_intentos - 1:
                log.info('codigo race · reintento %d/%d: %s', intento+1, max_intentos, e)
                continue
            raise


# ──────────────────────────────────────────────────────────────────────────────
# Registro CENTRAL de documentos regulados · Expediente por lote · zero-paper INVIMA
# Sebastián 24-jul-2026. REGLA (cerebro): TODO documento regulado nuevo (F01, F02, COA,
# rótulo, batch record/EBR, liberación, CoA micro/FQ...) DEBE inscribirse aquí en el mismo
# commit vía registrar_documento() → el Expediente por lote junta todos los docs de un lote.
# ──────────────────────────────────────────────────────────────────────────────
def registrar_documento(c, *, tipo_doc, url, entidad='MP', codigo='', producto_nombre='', lote='',
                        formato='', titulo='', ref_tabla='', ref_id='', mov_id=None, firma_id=None,
                        generado_por='', generado_at=None):
    """Inscribe un documento REGULADO en el índice central `documentos_regulados` (mig 371).

    Idempotente: anula la versión previa del MISMO documento (mismo tipo_doc + mov_id, o tipo_doc +
    ref_tabla + ref_id) antes de insertar la nueva → re-guardar un F01/F02 no duplica su entrada.
    Best-effort: si falla, loguea y NO rompe al caller (el documento ya está en su tabla origen; esto
    es solo el índice del expediente). Fecha calculada en Python (no date() en DML · PG-safe).
    """
    try:
        gen_at = generado_at or (datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')
        if mov_id is not None:
            c.execute("UPDATE documentos_regulados SET anulado=1 WHERE COALESCE(anulado,0)=0 "
                      "AND tipo_doc=? AND mov_id=?", (str(tipo_doc), mov_id))
        elif ref_tabla and str(ref_id or ''):
            c.execute("UPDATE documentos_regulados SET anulado=1 WHERE COALESCE(anulado,0)=0 "
                      "AND tipo_doc=? AND ref_tabla=? AND ref_id=?", (str(tipo_doc), str(ref_tabla), str(ref_id)))
        c.execute(
            "INSERT INTO documentos_regulados (entidad,codigo,producto_nombre,lote,tipo_doc,formato,"
            "titulo,url,ref_tabla,ref_id,mov_id,firma_id,generado_por,generado_at,anulado) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
            (str(entidad or 'MP'), str(codigo or ''), str(producto_nombre or ''), str(lote or ''),
             str(tipo_doc or ''), str(formato or ''), str(titulo or ''), str(url or ''),
             str(ref_tabla or ''), str(ref_id or ''), mov_id, firma_id, str(generado_por or ''), gen_at))
        return c.lastrowid
    except Exception as e:
        log.warning("registrar_documento falló (tipo=%s lote=%s): %s", tipo_doc, lote, e)
        return None
