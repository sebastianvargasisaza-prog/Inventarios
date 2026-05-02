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
"""
import json as _json
import logging
import sqlite3 as _sqlite3
from datetime import datetime
from flask import request

log = logging.getLogger('audit_helpers')


def audit_log(c, *, usuario, accion, registro_id, tabla=None,
                antes=None, despues=None, detalle=None):
    """INSERT a audit_log para evidencia regulatoria (Resolución 2214/2021).

    Args:
        c: cursor SQLite (no se hace commit aquí · caller controla la tx).
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
    try:
        antes_s = _json.dumps(antes) if antes is not None and not isinstance(antes, str) else antes
        despues_s = _json.dumps(despues) if despues is not None and not isinstance(despues, str) else despues
        # IP del cliente (si estamos en request context)
        try:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')[:45]
        except RuntimeError:
            ip = ''  # fuera de request context (cron, script)
        c.execute("""
            INSERT INTO audit_log (usuario, accion, tabla, registro_id,
                                     detalle, antes, despues, ip, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (usuario or '', accion, tabla,
              str(registro_id) if registro_id is not None else None,
              detalle, antes_s, despues_s, ip))
    except Exception as e:
        msg = str(e).lower()
        if 'no column named' in msg or 'has no column' in msg:
            # Migración 91 no aplicada · fallback al schema mínimo
            log.warning('audit_log antes/despues no disponible · fallback: %s', e)
            try:
                try:
                    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')[:45]
                except RuntimeError:
                    ip = ''
                c.execute("""
                    INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (usuario or '', accion, tabla,
                      str(registro_id) if registro_id is not None else None,
                      detalle, ip))
            except Exception as e2:
                log.exception('audit_log fallback también falló: %s', e2)
                raise  # regulatorio · debe rollback la operación
        else:
            log.exception('audit_log fallo inesperado: %s', e)
            raise


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
