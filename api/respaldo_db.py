# -*- coding: utf-8 -*-
"""Copia completa de la base de datos FUERA del proveedor (tarea B-01 · ASG-PRO-014).

EL HUECO QUE CIERRA
-------------------
Los documentos regulados ya tienen copia inmutable en R2 (`r2_storage`), pero **los DATOS
vivos existían en un solo proveedor**: kardex, lotes, fórmulas, órdenes, planeación, firmas y
`audit_log` sólo en el PostgreSQL de Render. El respaldo de Render protege contra que se dañe la
base; **no protege contra perder la cuenta**, porque vive adentro del servicio que se pierde.

Y el código que debía cubrirlo estaba MUERTO: `backup._do_pg_backup_to_gz` existe, pero
`backup.do_backup()` retorna en su primera línea cuando el motor es PostgreSQL, así que nunca se
alcanza. Un respaldo que no corre se ve igual que uno que corre (M119: si el gate lee una tabla
vacía, el gate no existe) -- por eso esto se mide, no se supone: `estado()` dice la FECHA de la
última copia, y si no hay ninguna lo dice con esas palabras.

QUÉ SE GUARDA Y POR QUÉ ASÍ
---------------------------
Volcado LÓGICO de datos (JSONL por fila), no un `pg_dump`. La razón no es comodidad: EOS
**reconstruye su propio esquema** desde la lista `MIGRATIONS` de `database.py`, así que los datos
son lo único irrecuperable. Un volcado de datos + `init_db()` restituye el sistema completo, y
además queda legible sin PostgreSQL, que es lo que exige una retención de tres años (numeral 5.5
del ASG-PRO-014: la conservación supera la vida previsible de cualquier motor).

⚠ Consecuencia que hay que respetar al restaurar: el esquema se crea PRIMERO con `init_db()` y
después se cargan los datos. `scripts/restaurar_respaldo.py` hace eso y además resetea las
secuencias -- sin ese paso, el primer INSERT posterior choca contra un id que ya existe.

MEMORIA Y TIEMPO (M92)
----------------------
Todo va en flujo a un archivo temporal: se lee la tabla de a bloques, se comprime al vuelo y se
cifra por bloques. La memoria no crece con el tamaño de la base. El trabajo está acotado por
presupuesto de reloj porque corre en el hilo único del multi-cron: un job que se cuelga ahí
detiene TODOS los crons siguientes (M90), incluidos `ventas_diarias` y `marcar_vencidos`.
"""
import base64
import gzip
import hashlib
import io
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# Bloque de cifrado. 4 MB es el equilibrio: suficientemente grande para que el gasto por bloque
# sea despreciable, suficientemente chico para que la memoria quede acotada pase lo que pase.
BLOQUE = 4 * 1024 * 1024
MAGIC = b'EOSBK1\n'

# Retención, espejo del numeral 5.5 del ASG-PRO-014.
RETENCION = {'semanal': 90, 'mensual': 1100}

PREFIJO = 'respaldo'


def _hoy_col():
    """Fecha de Colombia. El servidor corre en UTC (M24): con `utcnow` una copia de las 20:00
    del 31 quedaría archivada con fecha del mes siguiente y la rotación mensual se correría."""
    return datetime.utcnow() - timedelta(hours=5)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Cifrado
# ─────────────────────────────────────────────────────────────────────────────────────────────

def clave_configurada():
    return bool((os.environ.get('BACKUP_CIPHER_KEY') or '').strip())


def _clave():
    """Deriva 32 bytes de la variable de entorno. Se admite cualquier texto: derivar con SHA-256
    evita que una clave mal formateada rompa el respaldo, que es el peor intercambio posible."""
    raw = (os.environ.get('BACKUP_CIPHER_KEY') or '').strip()
    if not raw:
        return None
    return hashlib.sha256(raw.encode('utf-8')).digest()


def _cifrar_a(origen, destino, clave):
    """AES-256-GCM por bloques. Cada bloque lleva su nonce y su etiqueta de autenticidad, así que
    una alteración del archivo se DETECTA al restaurar en vez de producir datos corruptos silenciosos.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aes = AESGCM(clave)
    n = 0
    with open(origen, 'rb') as fi, open(destino, 'wb') as fo:
        fo.write(MAGIC)
        while True:
            bloque = fi.read(BLOQUE)
            if not bloque:
                break
            # El nonce NUNCA se repite con la misma clave: el contador del bloque lo garantiza
            # dentro del archivo, y los 4 bytes aleatorios, entre archivos distintos.
            nonce = os.urandom(4) + n.to_bytes(8, 'big')
            ct = aes.encrypt(nonce, bloque, None)
            fo.write(len(ct).to_bytes(4, 'big'))
            fo.write(nonce)
            fo.write(ct)
            n += 1
    return n


def _descifrar_a(origen, destino, clave):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aes = AESGCM(clave)
    with open(origen, 'rb') as fi, open(destino, 'wb') as fo:
        cab = fi.read(len(MAGIC))
        if cab != MAGIC:
            raise ValueError('el archivo no tiene la cabecera de un respaldo de EOS')
        while True:
            largo = fi.read(4)
            if not largo:
                break
            nonce = fi.read(12)
            ct = fi.read(int.from_bytes(largo, 'big'))
            fo.write(aes.decrypt(nonce, ct, None))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Volcado
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _tablas(c):
    """Las tablas de datos del motor en uso. Se leen del catálogo y no de una lista escrita a
    mano: una lista a mano deja afuera la tabla que se cree mañana, y nadie se entera hasta que
    hay que restaurar (M122)."""
    try:
        from database import es_postgres
        pg = es_postgres()
    except Exception:
        pg = bool((os.environ.get('EOS_DB_BACKEND') or '').strip().lower() == 'postgres')
    if pg:
        c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    else:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                  "AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in c.fetchall()]


def _jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {'__b64__': base64.b64encode(bytes(v)).decode('ascii')}
    if isinstance(v, (datetime,)):
        return v.isoformat()
    try:
        import decimal
        if isinstance(v, decimal.Decimal):
            return str(v)
    except Exception:
        pass
    try:
        import datetime as _d
        if isinstance(v, (_d.date, _d.time)):
            return v.isoformat()
    except Exception:
        pass
    return str(v)


def volcar(conn, ruta_gz, presupuesto_seg=600):
    """Escribe el volcado comprimido y devuelve el manifiesto (filas por tabla).

    El manifiesto es lo que hace verificable el respaldo: sin él, "el archivo pesa 40 MB" es todo
    lo que se puede afirmar, y eso no distingue una copia completa de una cortada a la mitad.
    """
    t0 = time.monotonic()
    c = conn.cursor()
    tablas = _tablas(c)
    manifiesto = {}
    truncado = []
    filas_tot = 0

    with gzip.open(ruta_gz, 'wb', compresslevel=6) as gz:
        cab = {'__eos_respaldo__': 1, 'generado': _hoy_col().isoformat(),
               'tablas': len(tablas), 'formato': 'jsonl-datos'}
        gz.write((json.dumps(cab, ensure_ascii=False) + '\n').encode('utf-8'))

        for t in tablas:
            if time.monotonic() - t0 > presupuesto_seg:
                # Se corta y se DECLARA. Un respaldo recortado que no lo dice se lee como completo,
                # y esa es exactamente la copia con la que uno descubre el problema al restaurar.
                truncado.append(t)
                continue
            try:
                c.execute('SELECT * FROM "%s"' % t)
            except Exception as e:
                log.warning('respaldo: no pude leer %s: %s', t, e)
                manifiesto[t] = {'filas': -1, 'error': str(e)[:200]}
                continue
            cols = [d[0] for d in (c.description or [])]
            n = 0
            while True:
                bloque = c.fetchmany(500)
                if not bloque:
                    break
                for fila in bloque:
                    d = {cols[i]: _jsonable(fila[i]) for i in range(len(cols))}
                    gz.write((json.dumps({'t': t, 'f': d}, ensure_ascii=False) + '\n')
                             .encode('utf-8'))
                    n += 1
            manifiesto[t] = {'filas': n}
            filas_tot += n

    return {'tablas': manifiesto, 'filas_totales': filas_tot, 'truncado': truncado,
            'completo': not truncado, 'segundos': round(time.monotonic() - t0, 1)}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Respaldo completo
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _key(tipo, cuando, sha):
    return '%s/%s/%s-%s.jsonl.gz.enc' % (PREFIJO, tipo, cuando.strftime('%Y%m%d-%H%M'), sha[:10])


def respaldar(app, tipo='semanal', presupuesto_seg=600):
    """Genera, cifra y sube la copia. Devuelve el resultado sin lanzar."""
    from r2_storage import r2_configurado, r2_put_archivo
    if not r2_configurado():
        return {'ok': False, 'motivo': 'el almacenamiento de objetos no está configurado'}

    t0 = time.monotonic()
    tmpd = tempfile.mkdtemp(prefix='eosbk_')
    crudo = os.path.join(tmpd, 'datos.jsonl.gz')
    cifrado = os.path.join(tmpd, 'datos.jsonl.gz.enc')
    try:
        with app.app_context():
            from database import get_db
            man = volcar(get_db(), crudo, presupuesto_seg=presupuesto_seg)

        sha = hashlib.sha256()
        with open(crudo, 'rb') as f:
            for b in iter(lambda: f.read(1024 * 1024), b''):
                sha.update(b)
        huella = sha.hexdigest()

        clave = _clave()
        if clave:
            _cifrar_a(crudo, cifrado, clave)
            subir, cifr = cifrado, True
        else:
            # Sin clave se respalda IGUAL. Tener los datos importa más que la confidencialidad
            # perfecta de una copia que vive en un contenedor privado; lo que no se puede hacer es
            # callarlo, así que `estado()` lo reporta como hallazgo hasta que se configure.
            log.warning('respaldo sin cifrar: BACKUP_CIPHER_KEY no está configurada')
            subir, cifr = crudo, False

        cuando = _hoy_col()
        key = _key(tipo, cuando, huella)
        tam = os.path.getsize(subir)
        if not r2_put_archivo(key, subir, 'application/octet-stream'):
            return {'ok': False, 'motivo': 'no pude subir la copia al almacenamiento',
                    'bytes': tam}

        # El manifiesto va aparte y SIN cifrar: es la única forma de verificar el respaldo sin
        # descargarlo entero ni tener la clave a mano (verificación mensual del numeral 5.8).
        meta = {'tipo': tipo, 'fecha': cuando.isoformat(), 'key': key, 'bytes': tam,
                'sha256_datos': huella, 'cifrado': cifr, 'formato': 'jsonl-datos',
                'restaura_con': 'scripts/restaurar_respaldo.py',
                'esquema_desde': 'database.MIGRATIONS (init_db)', **man}
        from r2_storage import r2_put
        r2_put(key + '.manifiesto.json',
               json.dumps(meta, ensure_ascii=False, indent=1).encode('utf-8'),
               'application/json')

        _registrar(app, meta)
        meta['segundos'] = round(time.monotonic() - t0, 1)
        meta['ok'] = True
        return meta
    except Exception as e:
        log.exception('respaldo falló')
        return {'ok': False, 'motivo': '%s: %s' % (type(e).__name__, str(e)[:200])}
    finally:
        for p in (crudo, cifrado):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmpd)
        except OSError:
            pass


def _registrar(app, meta):
    """Deja constancia en la base. Es lo que lee la verificación mensual: preguntarle al
    almacenamiento en cada carga sería una llamada de red dentro de una pantalla (M43)."""
    try:
        with app.app_context():
            from database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, "
                      "cifrado, detalle) VALUES (?,?,?,?,?,?,?,?)",
                      (meta.get('tipo'), meta.get('fecha'), meta.get('key'),
                       int(meta.get('bytes') or 0), int(meta.get('filas_totales') or 0),
                       1 if meta.get('completo') else 0, 1 if meta.get('cifrado') else 0,
                       json.dumps({'truncado': meta.get('truncado') or []}, ensure_ascii=False)))
            conn.commit()
    except Exception as e:
        log.warning('no pude registrar el respaldo en respaldo_log: %s', e)


def rotar(tipo, hoy=None):
    """Borra las copias vencidas de ese tipo. Devuelve cuántas borró."""
    from r2_storage import _client, _cfg, r2_delete
    if not _client():
        return 0
    hoy = hoy or _hoy_col()
    dias = RETENCION.get(tipo)
    if not dias:
        return 0
    corte = hoy - timedelta(days=dias)
    cl = _client()
    c = _cfg()
    borradas = 0
    try:
        token = None
        while True:
            kw = {'Bucket': c['bucket'], 'Prefix': '%s/%s/' % (PREFIJO, tipo), 'MaxKeys': 1000}
            if token:
                kw['ContinuationToken'] = token
            resp = cl.list_objects_v2(**kw)
            for obj in (resp.get('Contents') or []):
                k = obj['Key']
                base = k.split('/')[-1]
                try:
                    f = datetime.strptime(base[:13], '%Y%m%d-%H%M')
                except ValueError:
                    continue          # nombre que no reconozco: no lo borro (M19)
                if f < corte:
                    if r2_delete(k):
                        borradas += 1
            if not resp.get('IsTruncated'):
                break
            token = resp.get('NextContinuationToken')
    except Exception as e:
        log.warning('rotación de respaldos falló: %s', e)
    return borradas


def listar(tipo=None, limite=50):
    """Las copias que EXISTEN en el almacenamiento (no lo que dice la base)."""
    from r2_storage import _client, _cfg
    cl = _client()
    if not cl:
        return []
    c = _cfg()
    out = []
    for tp in ([tipo] if tipo else list(RETENCION.keys())):
        try:
            resp = cl.list_objects_v2(Bucket=c['bucket'], Prefix='%s/%s/' % (PREFIJO, tp),
                                      MaxKeys=1000)
            for obj in (resp.get('Contents') or []):
                if obj['Key'].endswith('.manifiesto.json'):
                    continue
                out.append({'tipo': tp, 'key': obj['Key'], 'bytes': obj.get('Size'),
                            'fecha': obj.get('LastModified').isoformat()
                            if obj.get('LastModified') else ''})
        except Exception as e:
            log.warning('no pude listar respaldos %s: %s', tp, e)
    out.sort(key=lambda x: x.get('fecha') or '', reverse=True)
    return out[:limite]


def verificar(key, presupuesto_seg=120):
    """Descarga una copia, la descifra, la descomprime y CUENTA las filas.

    Es la verificación que exige el numeral 5.8: que la copia se pueda abrir y esté completa. Un
    respaldo que nunca se abrió es una suposición, no un respaldo.
    """
    from r2_storage import r2_get
    t0 = time.monotonic()
    datos = r2_get(key)
    if not datos:
        return {'ok': False, 'motivo': 'no pude descargar la copia'}
    man = r2_get(key + '.manifiesto.json')
    manifiesto = {}
    if man:
        try:
            manifiesto = json.loads(man.decode('utf-8'))
        except Exception:
            manifiesto = {}

    tmpd = tempfile.mkdtemp(prefix='eosvf_')
    enc = os.path.join(tmpd, 'c.bin')
    gz = os.path.join(tmpd, 'd.gz')
    try:
        with open(enc, 'wb') as f:
            f.write(datos)
        if datos[:len(MAGIC)] == MAGIC:
            clave = _clave()
            if not clave:
                return {'ok': False, 'motivo': 'la copia está cifrada y no hay clave configurada'}
            _descifrar_a(enc, gz, clave)
        else:
            gz = enc

        por_tabla = {}
        filas = 0
        with gzip.open(gz, 'rb') as f:
            primera = f.readline()
            try:
                cab = json.loads(primera.decode('utf-8'))
            except Exception:
                return {'ok': False, 'motivo': 'la copia no tiene cabecera legible'}
            if not cab.get('__eos_respaldo__'):
                return {'ok': False, 'motivo': 'la cabecera no corresponde a un respaldo de EOS'}
            for linea in f:
                if time.monotonic() - t0 > presupuesto_seg:
                    return {'ok': False, 'motivo': 'la verificación excedió el presupuesto',
                            'filas_leidas': filas}
                try:
                    r = json.loads(linea.decode('utf-8'))
                except Exception:
                    return {'ok': False, 'motivo': 'hay una línea ilegible', 'filas_leidas': filas}
                por_tabla[r['t']] = por_tabla.get(r['t'], 0) + 1
                filas += 1

        esperado = {k: v.get('filas') for k, v in (manifiesto.get('tablas') or {}).items()
                    if isinstance(v, dict) and (v.get('filas') or 0) > 0}
        difs = [{'tabla': t, 'manifiesto': n, 'leidas': por_tabla.get(t, 0)}
                for t, n in esperado.items() if por_tabla.get(t, 0) != n]
        return {'ok': not difs, 'filas': filas, 'tablas': len(por_tabla),
                'diferencias': difs[:20], 'n_diferencias': len(difs),
                'cifrado': datos[:len(MAGIC)] == MAGIC,
                'segundos': round(time.monotonic() - t0, 1)}
    except Exception as e:
        return {'ok': False, 'motivo': '%s: %s' % (type(e).__name__, str(e)[:200])}
    finally:
        for p in (enc, gz):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmpd)
        except OSError:
            pass


def estado(conn):
    """Lo que necesita la verificación mensual del ASG-PRO-014-F01, en un solo lugar.

    Devuelve HALLAZGOS, no sólo datos: una pantalla que muestra la fecha del último respaldo
    obliga a que alguien sepa cuál es el límite aceptable. Aquí el límite está escrito.
    """
    from r2_storage import r2_configurado
    out = {'almacenamiento_configurado': r2_configurado(), 'cifrado_configurado': clave_configurada(),
           'ultimo': {}, 'hallazgos': []}
    try:
        c = conn.cursor()
        for tipo in ('semanal', 'mensual'):
            r = c.execute("SELECT fecha, bytes, filas, completo, cifrado, r2_key FROM respaldo_log "
                          "WHERE tipo=? ORDER BY id DESC LIMIT 1", (tipo,)).fetchone()
            if r:
                out['ultimo'][tipo] = {'fecha': r[0], 'bytes': r[1], 'filas': r[2],
                                       'completo': bool(r[3]), 'cifrado': bool(r[4]),
                                       'key': r[5]}
    except Exception as e:
        out['hallazgos'].append('no pude leer el registro de respaldos: %s' % str(e)[:120])
        return out

    if not out['almacenamiento_configurado']:
        out['hallazgos'].append('El almacenamiento de objetos no está configurado: '
                                'no se está guardando ninguna copia fuera del proveedor.')
    if not out['cifrado_configurado']:
        out['hallazgos'].append('Falta configurar BACKUP_CIPHER_KEY: las copias se están '
                                'guardando sin cifrar.')

    hoy = _hoy_col()
    sem = out['ultimo'].get('semanal')
    if not sem:
        out['hallazgos'].append('Nunca se ha generado una copia semanal.')
    else:
        try:
            edad = (hoy - datetime.fromisoformat(sem['fecha'])).days
            if edad > 10:
                out['hallazgos'].append('La última copia semanal tiene %d días.' % edad)
        except Exception:
            pass
        if not sem.get('completo'):
            out['hallazgos'].append('La última copia semanal quedó incompleta.')
    men = out['ultimo'].get('mensual')
    if not men:
        out['hallazgos'].append('Nunca se ha generado una copia mensual.')
    else:
        try:
            edad = (hoy - datetime.fromisoformat(men['fecha'])).days
            if edad > 40:
                out['hallazgos'].append('La última copia mensual tiene %d días.' % edad)
        except Exception:
            pass
    out['ok'] = not out['hallazgos']
    return out
