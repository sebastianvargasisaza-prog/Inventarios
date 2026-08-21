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
def inscribir_rotulo_envase(c, mov_id, codigo_mee, lote='', usuario='', descripcion=''):
    """Inscribe el rótulo de ingreso de envase (COC-PRO-002-F06) en el expediente.

    La URL es estable y por MOVIMIENTO (`?mov=<id>`), que es la que imprime un rótulo por caja:
    quien audite el lote llega a la identificación de TODAS las cajas, no a una.
    """
    if not mov_id:
        return
    registrar_documento(
        c, tipo_doc='ROTULO_ENVASE', formato='COC-PRO-002-F06',
        titulo='Identificacion de material de envase',
        url='/rotulos-recepcion-mee?mov=%s' % mov_id,
        entidad='MEE', codigo=str(codigo_mee or ''), producto_nombre=str(descripcion or ''),
        lote=str(lote or ''), ref_tabla='movimientos_mee', ref_id=str(mov_id),
        generado_por=str(usuario or ''))


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


def agregar_parte_envase(c, *, envase, parte, descripcion='', cantidad=1, usuario=''):
    """Declara una PIEZA de un envase (`mee_partes`) · punto ÚNICO de escritura.

    Sebastián 26-jul: *"revisa también si en inventario de MEE está bien montada la lógica para
    agregar los envases con sus partes"*. Estaba escrita CUATRO veces y sólo una lo hacía bien:

    | camino                         | validaba | dedupeaba | auditaba |
    |--------------------------------|----------|-----------|----------|
    | herramienta admin tapas+goteros| sí       | sí        | sí       |
    | alta de envase nuevo           | NO       | NO        | no       |
    | alta con código automático     | NO       | NO        | no (+ `except` mudo) |

    Los dos del medio son el problema: **un código mal tecleado crea una pieza fantasma** que el
    abastecimiento intenta comprar y el envasado intenta descontar, sin existir en el maestro y sin
    que nadie pueda reponerla. Es el mismo patrón que costó caro con los códigos de MP (M1: nunca
    inventar un material). Y uno tragaba el error en silencio, así que la pieza no se guardaba y
    nadie se enteraba (M4).

    Reglas, iguales para todos los que la llamen:
      · la pieza tiene que EXISTIR en `maestro_mee`;
      · no puede ser el propio envase;
      · no se declara dos veces (descontaría el doble);
      · cantidad > 0;
      · queda en `audit_log` quién la declaró, porque cambia lo que se compra y lo que se descuenta
        en todos los lotes futuros.

    Returns:
        (True, None) si quedó declarada · (False, motivo) si no. **Nunca lanza**: el caller decide
        si el motivo es un 400 al usuario o una línea de log en una carga masiva.
    """
    env = (str(envase or '')).strip().upper()
    par = (str(parte or '')).strip().upper()
    if not env or not par:
        return False, 'envase y pieza son obligatorios'
    if par == env:
        return False, 'un envase no puede ser pieza de sí mismo'
    try:
        cant = float(cantidad or 1)
    except (TypeError, ValueError):
        return False, 'cantidad inválida'
    if cant <= 0:
        return False, 'la cantidad debe ser mayor que cero'
    try:
        if not c.execute("SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo))=?", (par,)).fetchone():
            return False, ("la pieza '%s' no existe en el maestro de envases · creala primero en "
                           "Bodega MEE" % par)
        if c.execute("SELECT 1 FROM mee_partes WHERE UPPER(TRIM(mee_codigo))=? "
                     "AND UPPER(TRIM(COALESCE(parte_codigo,'')))=?", (env, par)).fetchone():
            return False, 'esa pieza ya está declarada para este envase'
        c.execute(
            "INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, creado_at) "
            "VALUES (?,?,?,?, datetime('now','-5 hours'))",
            (env, par, str(descripcion or '')[:120], cant))
        audit_log(c, usuario=usuario or '', accion='AGREGAR_PARTE_ENVASE', tabla='mee_partes',
                  registro_id=env,
                  despues={'envase': env, 'parte': par, 'cantidad': cant,
                           'descripcion': str(descripcion or '')[:120]})
        return True, None
    except Exception as e:
        log.warning('agregar_parte_envase(%s, %s) falló: %s', env, par, e)
        return False, 'no se pudo declarar la pieza: %s' % str(e)[:120]


def lote_interno_mee(c):
    """Lote INTERNO para un envase cuyo proveedor no manda lote · punto ÚNICO (M1).

    Sebastián 30-jul: *"es posible que no tengan lote, qué tal si ponés la opción de lote
    interno"*. Forma `INT-AAMMDD-NNN`: lleva la fecha de recepción (el hecho que lo origina) y
    un correlativo del día, así que dos referencias del mismo contenedor no comparten lote -- si
    mañana hay un reclamo, el lote apunta a UNA recepción concreta y no a "lo que llegó ese día".

    El prefijo `INT-` lo distingue a simple vista de un lote del proveedor: que se confundan
    sería peor que no tener lote (M115 · sin dato no se inventa un default que parezca real).

    Vive acá y no dentro de una vista porque lo usan las DOS puertas de recepción de envases (la
    manual y la de orden de compra). Cuando cada puerta arma su propio lote, la numeración se
    parte en dos series que se pisan (M99).
    """
    import re as _re
    from datetime import timedelta as _td
    base = 'INT-' + (datetime.utcnow() - _td(hours=5)).strftime('%y%m%d') + '-'
    mx = 0
    try:
        for (lr,) in c.execute(
                "SELECT lote_ref FROM movimientos_mee WHERE COALESCE(lote_ref,'') LIKE ?",
                (base + '%',)).fetchall():
            m = _re.match(r'^' + _re.escape(base) + r'(\d+)$', str(lr or '').strip())
            if m:
                mx = max(mx, int(m.group(1)))
    except Exception as e:
        # Un except mudo acá arrancaría el correlativo en 001 y CHOCARÍA con el lote de otra
        # recepción del mismo día: dos materiales distintos bajo el mismo lote es lo peor que
        # le puede pasar a la trazabilidad.
        log.warning('correlativo de lote interno MEE: %s', e)
    return base + '%03d' % (mx + 1)


def lote_juliano(c, fecha=None):
    """El número de lote como lo numera la planta: año + día juliano + consecutivo.

    Sebastián 16-ago-2026: *"los números de lote ellos los calculan con una tabla especial"*.
    La tabla es el CALENDARIO JULIANO -- el día del año, 001 a 365 -- y la regla salió de sus
    propios batch records firmados: de los 28, veinticinco encajan exactos y las órdenes
    consecutivas caen en días crecientes. La prueba está en el día 183 (2 de julio), que tiene
    DOS lotes (`261831` y `261832`): ahí se ve que el último dígito es el consecutivo del día.

        261621  =  26      162           1
                   año     11 de junio   primer lote de ese día

    Hasta ahora EOS numeraba distinto en cada camino (`DEMO-<hora>`, `ESP260815xxx`,
    `260815-42`), así que el número del sistema no era el que iba en el rótulo ni en el batch
    record -- y el lote es la llave de toda la trazabilidad: kardex, genealogía, expediente.

    El consecutivo se calcula mirando los lotes que YA existen de ese día, en las dos tablas
    donde vive un lote (el legajo y el kardex): si sólo mirara una, dos lotes del mismo día
    podrían salir con el mismo número, que es lo peor que le puede pasar a un registro
    regulado (dos materiales distintos bajo la misma llave).

    ⚠ El formato admite 9 lotes por día. Al décimo NO se inventa un dígito de más en
    silencio -- se devuelve `None` y quien llama lo declara: un lote con formato distinto
    al del rótulo es peor que pedirle el número a una persona (M100/M124).

    Devuelve el número (str) o None si ese día ya no admite más.
    """
    from datetime import datetime, timedelta
    if fecha is None:
        # Ancla Colombia, nunca UTC crudo: de noche el servidor ya está en el día siguiente
        # y el lote saldría con el juliano de mañana (M24).
        fecha = (datetime.utcnow() - timedelta(hours=5)).date()
    prefijo = '%02d%03d' % (fecha.year % 100, fecha.timetuple().tm_yday)

    usados = set()
    for sql, col in (
            ("SELECT lote_codigo FROM ebr_ejecuciones WHERE lote_codigo LIKE ?", 'lote_codigo'),
            ("SELECT lote FROM ebr_ejecuciones WHERE lote LIKE ?", 'lote'),
            ("SELECT DISTINCT lote FROM movimientos WHERE lote LIKE ?", 'lote')):
        try:
            for r in c.execute(sql, (prefijo + '%',)).fetchall():
                v = str((r[0] if not hasattr(r, 'keys') else r[col]) or '').strip()
                if len(v) >= len(prefijo) + 1 and v[len(prefijo)].isdigit():
                    usados.add(int(v[len(prefijo)]))
        except Exception as e:
            # Se avisa y se sigue: perder una fuente puede repetir un consecutivo, así que
            # no puede quedar mudo (M4).
            log.warning('lote_juliano: no se pudo leer %s: %s', sql.split()[3], e)

    for n in range(1, 10):
        if n not in usados:
            return prefijo + str(n)
    log.warning('lote_juliano: el día %s ya tiene 9 lotes · el formato no admite más', prefijo)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Fecha de vencimiento del kardex · UN solo formato · 21-ago-2026
# ──────────────────────────────────────────────────────────────────────────────
_MESES_TXT = {
    'ene': '01', 'jan': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'apr': '04',
    'may': '05', 'jun': '06', 'jul': '07', 'ago': '08', 'aug': '08', 'sep': '09',
    'set': '09', 'oct': '10', 'nov': '11', 'dic': '12', 'dec': '12',
}


def fecha_iso(v):
    """Toda fecha que va al kardex se guarda en **ISO `YYYY-MM-DD`**. Devuelve '' si no se puede.

    Sebastián 21-ago-2026, con el AZ HYBRID CLEAR abierto: *"le digo que me mire stock y dice
    esto, pero cuando reviso el inventario sí tengo esas materias primas"*. El PROPYLENE GLYCOL
    decía **"disponible 0g · FALTA 4000g"** y en la misma fila, tres milímetros más abajo,
    *"LOTES A USAR (FEFO): 20251226 · 29.137,5g"* — con 29 kg VIGENTES en bodega.

    La causa no era el motor: era el FORMATO de `movimientos.fecha_vencimiento`. El lote tenía
    `26-Dic-2026` en vez de `2026-12-26`, y de ahí salen dos comportamientos distintos:

      · el cálculo del DISPONIBLE compara con `date(fecha_vencimiento)`, que ante un texto que
        no es ISO devuelve **NULL** → la comparación es falsa → el lote se excluye del stock
        distribuible. Lo mismo hace el FEFO, así que el material existe y no se puede consumir.
      · la lista de lotes de la pantalla compara **como texto**, donde `26-Dic-2026` es "mayor"
        que `2026-08-21` sólo porque empieza por `2`, así que lo daba por vigente.

    Las dos mitades de la misma fila se contradicen, y ninguna de las dos se puede creer (M161).
    Peor: `job_marcar_vencidos` también usa `date(...)`, así que un lote REALMENTE vencido con
    fecha en texto **nunca se marca** — el control de vencimiento deja de sonar en silencio.

    Acepta lo que la gente y los Excel escriben de verdad: ISO (con o sin hora), `DD/MM/YYYY`,
    `DD-MM-YYYY`, `DD-Mmm-YYYY` con el mes en letras (español o inglés) y `YYYY/MM/DD`. Lo que
    no se puede leer devuelve '' — **nunca se adivina una fecha de vencimiento**: inventarla es
    dejar entrar material vencido a producción (M19/M118).
    """
    if v is None or v == '':
        return ''
    from datetime import datetime as _dt, date as _date
    if isinstance(v, _dt):
        return v.date().isoformat()
    if isinstance(v, _date):
        return v.isoformat()
    s = str(v).strip()
    if not s:
        return ''
    # ISO, que es lo normal: se valida de verdad (un '2026-13-45' no pasa).
    cab = s[:10]
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return _dt.strptime(cab, fmt).date().isoformat()
        except ValueError:
            pass
    # Mes en letras: `26-Dic-2026`, `26 dic 26`, `26/DICIEMBRE/2026`.
    import re as _re
    m = _re.match(r'^\s*(\d{1,2})[-/ ]\s*([A-Za-zÁÉÍÓÚáéíóú]{3,12})\.?[-/ ]\s*(\d{2,4})\s*$', s)
    if m:
        mes = _MESES_TXT.get(m.group(2)[:3].lower())
        if mes:
            anio = m.group(3)
            if len(anio) == 2:
                # Un lote no vence 90 años atrás: dos dígitos son de este siglo.
                anio = '20' + anio
            try:
                return _dt.strptime('%s-%s-%02d' % (anio, mes, int(m.group(1))),
                                    '%Y-%m-%d').date().isoformat()
            except ValueError:
                return ''
    return ''
