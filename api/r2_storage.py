"""Cliente Cloudflare R2 (S3-compatible) · archivo inmutable de documentos regulados.

Sebastián 24-jul-2026 · Fase 2 del expediente por lote (zero-paper INVIMA). Guarda un snapshot
inmutable de cada documento regulado (F01/F02/EBR/COA/rótulo) en R2, como segunda capa encima de
PostgreSQL (la fuente de verdad). Egress gratis · WORM/Object Lock activable en el bucket.

Config por env vars (se cargan en Render · NUNCA en el repo):
  R2_ENDPOINT    = https://<accountid>.r2.cloudflarestorage.com
  R2_BUCKET      = eos-documentos
  R2_ACCESS_KEY  = <Access Key ID>
  R2_SECRET_KEY  = <Secret Access Key>

boto3 se importa PEREZOSAMENTE dentro de las funciones → si boto3 no está instalado o el entorno
no está configurado, la app arranca igual y las llamadas devuelven False/None (best-effort · el
documento vive en PostgreSQL de todos modos). NUNCA rompe un flujo regulado.
"""
import logging
import os
import re

log = logging.getLogger('r2_storage')

# Caracteres invisibles/whitespace unicode que .strip() NO remueve (se cuelan al copiar/pegar
# desde el dashboard de Cloudflare o desde HTML renderizado) → rompen la validación de endpoint de boto3.
_INVIS = '\t\n\r\x0b\x0c \xa0​‌‍⁠﻿'


def _strip_invis(v):
    """Quita whitespace estándar + invisibles unicode (nbsp, zero-width, BOM) de los bordes Y del interior."""
    v = (v or '').strip()
    return ''.join(ch for ch in v if ch not in _INVIS)


def _clean_endpoint(v):
    """Endpoint R2: solo caracteres válidos de URL (letras/dígitos/:/._-). Elimina cualquier
    carácter invisible o basura pegada. Un endpoint R2 legítimo solo contiene esos chars."""
    v = _strip_invis(v)
    v = re.sub(r'[^A-Za-z0-9:/._\-]', '', v)
    return v.rstrip('/')  # boto3 no quiere slash final


def _cfg():
    return {
        'endpoint': _clean_endpoint(os.environ.get('R2_ENDPOINT', '')),
        'bucket': _strip_invis(os.environ.get('R2_BUCKET', '')),
        'key': _strip_invis(os.environ.get('R2_ACCESS_KEY', '')),
        'secret': _strip_invis(os.environ.get('R2_SECRET_KEY', '')),
    }


def r2_configurado():
    """¿Están las 4 variables de entorno? (no valida credenciales · solo presencia)."""
    c = _cfg()
    return bool(c['endpoint'] and c['bucket'] and c['key'] and c['secret'])


def _host_de_endpoint(ep):
    from urllib.parse import urlsplit
    return urlsplit(ep).hostname or ''


def _tls_probe(host, timeout=8):
    """Handshake TLS crudo (socket+ssl) a host:443 con SNI. Aísla si el problema es de RED/TLS
    (independiente de boto3/credenciales)."""
    import socket
    import ssl
    if not host:
        return {'ok': False, 'error': 'host vacío'}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return {'ok': True, 'tls': ssock.version(), 'host': host}
    except Exception as e:
        return {'ok': False, 'host': host, 'error': type(e).__name__ + ': ' + str(e)[:140]}


def _client():
    import boto3
    from botocore.config import Config
    c = _cfg()
    return boto3.client(
        's3', endpoint_url=c['endpoint'], aws_access_key_id=c['key'],
        aws_secret_access_key=c['secret'], region_name='auto',
        config=Config(signature_version='s3v4', retries={'max_attempts': 2}, connect_timeout=8, read_timeout=20))


def r2_put(key, data, content_type='application/octet-stream'):
    """Sube un objeto a R2. data = bytes o str. Devuelve True/False (best-effort · loguea si falla)."""
    if not r2_configurado():
        return False
    try:
        cl = _client()
        c = _cfg()
        if isinstance(data, str):
            data = data.encode('utf-8')
        cl.put_object(Bucket=c['bucket'], Key=key, Body=data, ContentType=content_type)
        return True
    except Exception as e:
        log.warning('r2_put falló (%s): %s', key, e)
        return False


def r2_get(key):
    """Descarga un objeto de R2 → bytes, o None si no existe/falla."""
    if not r2_configurado():
        return None
    try:
        cl = _client()
        c = _cfg()
        return cl.get_object(Bucket=c['bucket'], Key=key)['Body'].read()
    except Exception as e:
        log.warning('r2_get falló (%s): %s', key, e)
        return None


def r2_existe(key):
    """¿Existe el objeto en R2? (head_object · barato). True/False/None(si R2 no configurado)."""
    if not r2_configurado():
        return None
    try:
        cl = _client()
        c = _cfg()
        cl.head_object(Bucket=c['bucket'], Key=key)
        return True
    except Exception:
        return False


def r2_delete(key):
    if not r2_configurado():
        return False
    try:
        cl = _client()
        c = _cfg()
        cl.delete_object(Bucket=c['bucket'], Key=key)
        return True
    except Exception as e:
        log.warning('r2_delete falló (%s): %s', key, e)
        return False


def r2_selftest():
    """Escribe → lee → borra un objeto de prueba: confirma credenciales + conectividad. Para el
    endpoint /api/admin/r2-check (el usuario lo dispara para verificar antes de integrar)."""
    if not r2_configurado():
        _c = _cfg()
        _faltan = [k for k in ('R2_ENDPOINT', 'R2_BUCKET', 'R2_ACCESS_KEY', 'R2_SECRET_KEY')
                   if not (os.environ.get(k, '') or '').strip()]
        return {'ok': False, 'configurado': False,
                'error': 'R2 no configurado · faltan variables en el entorno: ' + ', '.join(_faltan)}
    key = '_selftest/eos-r2-check.txt'
    payload = b'EOS R2 self-test OK'
    try:
        import boto3  # noqa: F401
        from botocore.exceptions import ClientError, EndpointConnectionError, ParamValidationError
    except Exception:
        return {'ok': False, 'configurado': True, 'error': 'boto3 no está instalado en el servidor (revisar requirements/deploy)'}
    c = _cfg()
    _raw_ep = os.environ.get('R2_ENDPOINT', '') or ''
    _diag = {'endpoint': c['endpoint'], 'bucket': c['bucket'],
             'access_key_prefijo': (c['key'][:6] + '…') if c['key'] else '',
             'access_key_len': len(c['key']), 'secret_len': len(c['secret'])}
    # si el endpoint crudo traía caracteres invisibles, mostrarlo (repr revela nbsp/zero-width)
    if _raw_ep != c['endpoint']:
        _diag['endpoint_crudo_repr'] = repr(_raw_ep)[:180]
        _diag['aviso'] = 'el endpoint en Render tenía caracteres extra (se limpiaron en el código)'
    try:
        cl = _client()
        cl.put_object(Bucket=c['bucket'], Key=key, Body=payload, ContentType='text/plain')
        got = cl.get_object(Bucket=c['bucket'], Key=key)['Body'].read()
        try:
            cl.delete_object(Bucket=c['bucket'], Key=key)
        except Exception:
            pass
        if got != payload:
            return {'ok': False, 'configurado': True, 'error': 'escribió pero la LECTURA no coincidió', **_diag}
        return {'ok': True, 'configurado': True, 'mensaje': 'R2 conectado correctamente: escritura + lectura + borrado OK', **_diag}
    except EndpointConnectionError as e:
        return {'ok': False, 'configurado': True, 'code': 'ENDPOINT',
                'error': 'No se pudo conectar al endpoint · revisá R2_ENDPOINT (debe ser https://<accountid>.r2.cloudflarestorage.com): %s' % str(e)[:200], **_diag}
    except ClientError as e:
        _err = e.response.get('Error', {}) if hasattr(e, 'response') else {}
        _code = _err.get('Code', '')
        _http = (e.response.get('ResponseMetadata', {}) or {}).get('HTTPStatusCode') if hasattr(e, 'response') else None
        _pistas = {
            'AccessDenied': 'el token NO tiene permiso de escritura sobre el bucket → recrealo con "Object Read & Write" (no "Object Read only") y aplicado a eos-documentos',
            'SignatureDoesNotMatch': 'la Clave de acceso SECRETA está mal (typo al pegar en Render) → revisá R2_SECRET_KEY',
            'InvalidAccessKeyId': 'el ID de clave de acceso está mal → revisá R2_ACCESS_KEY',
            'NoSuchBucket': 'el bucket no existe con ese nombre → revisá R2_BUCKET (debe ser eos-documentos)',
        }
        return {'ok': False, 'configurado': True, 'code': _code, 'http': _http,
                'error': 'R2 rechazó (%s · HTTP %s): %s' % (_code or '?', _http or '?', _err.get('Message', '')),
                'pista': _pistas.get(_code, 'revisá endpoint/bucket/keys y que el token sea Object Read & Write'), **_diag}
    except Exception as e:
        _out = {'ok': False, 'configurado': True, 'code': type(e).__name__,
                'error': '%s: %s' % (type(e).__name__, str(e)[:220]), **_diag}
        # SSL/conexión → sondear TLS del host base y del host de jurisdicción EU
        _msg = (type(e).__name__ + str(e)).lower()
        if 'ssl' in _msg or 'handshake' in _msg or 'connect' in _msg or 'timed out' in _msg:
            _host = _host_de_endpoint(c['endpoint'])
            _host_eu = _host.replace('.r2.cloudflarestorage.com', '.eu.r2.cloudflarestorage.com') if _host and '.eu.' not in _host else _host
            _out['tls_base'] = _tls_probe(_host)
            if _host_eu and _host_eu != _host:
                _out['tls_eu'] = _tls_probe(_host_eu)
                if not _out['tls_base'].get('ok') and _out['tls_eu'].get('ok'):
                    _out['pista'] = ('el bucket parece ser de jurisdicción UNIÓN EUROPEA → cambiá R2_ENDPOINT a '
                                     'https://' + _host_eu + ' (con .eu.) en Render')
            if _out['tls_base'].get('ok'):
                _out['pista'] = ('el TLS al host base SÍ conecta a nivel red → el fallo SSL viene de boto3/config, '
                                 'no del endpoint; revisá versión boto3/urllib3 o proxy de salida')
        return _out


# ══════════════════════════════════════════════════════════════════════════════
# Fase 2b · Archivo INMUTABLE del expediente por lote (Sebastián 24-jul · INVIMA)
# Cada documento regulado (F01/F02/EBR/COA/rótulo) ya vive en su tabla + en el
# índice `documentos_regulados`. Aquí lo snapshoteamos a R2 (WORM, off-site) como
# 2ª capa: si se pierde el disco de Render, el PDF/HTML firmado sobrevive.
# Lo corre el cron job_archivar_r2 (hilo multi-cron) y el botón POST /api/calidad/archivar-r2.
# ⚠ El trabajo es I/O de red (render + PUT a R2), así que archivar_pendientes_r2 SIEMPRE se acota con
# `presupuesto_seg` (wall-clock, < gunicorn --timeout 120) + circuit-breaker por fallos de R2 → nunca
# retiene un worker hasta el SIGKILL ni cuelga el hilo del cron si R2 está lento/caído (M89/M90/M91).
# Como es idempotente (solo toma pendientes r2_key vacío), el resto se drena en llamadas cortas sucesivas.
# ══════════════════════════════════════════════════════════════════════════════

# Sesión de servicio (solo lectura) para renderizar los imprimibles internos.
# El gate de /api/ solo exige presencia de `compras_user`; un string sintético
# pasa (no es admin → no dispara MFA) y deja claro en logs que es el archivador.
_SVC_USER = 'sistema-archivo-r2'


def _ext_de(content_type, url):
    ct = (content_type or '').lower()
    if 'pdf' in ct:
        return 'pdf'
    if 'html' in ct:
        return 'html'
    u = (url or '').lower()
    for e in ('.pdf', '.png', '.jpg', '.jpeg', '.html'):
        if e in u:
            return e.lstrip('.')
    return 'bin'


def _slug(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', (str(s or '').strip()))[:60].strip('-') or 'sin'


def _r2_key_documento(doc, sha, ext):
    """Key determinista e inmutable. Incluye el id del documento → cada versión
    (registrar_documento anula la vieja e inserta nueva con id nuevo) obtiene su
    propia key: R2 nunca sobrescribe (WORM)."""
    ent = _slug(doc.get('entidad') or 'MP')
    grupo = _slug(doc.get('lote') or doc.get('codigo') or 'sin-lote')
    tipo = _slug(doc.get('tipo_doc') or 'DOC')
    return 'expediente/%s/%s/%s/%s-%s.%s' % (ent, grupo, tipo, doc.get('id'), (sha or '')[:12], ext)


def _render_doc_bytes(app, url):
    """Renderiza el documento (imprimible HTML o archivo COA) vía test_client con
    sesión de servicio. Devuelve (bytes, content_type) o (None, motivo)."""
    if not url:
        return None, 'sin url'
    try:
        import time as _t
        tc = app.test_client()
        # base_url https → la cookie de sesión (SESSION_COOKIE_SECURE=True) viaja; login_time reciente
        # evita el check de sesión-expirada. El gate solo exige compras_user presente (imprimibles GET).
        _bu = 'https://localhost'
        with tc.session_transaction(base_url=_bu) as sess:
            sess['compras_user'] = _SVC_USER
            sess['login_time'] = _t.time()
        resp = tc.get(url, base_url=_bu)
        if resp.status_code != 200:
            return None, 'HTTP %s' % resp.status_code
        data = resp.get_data()
        if not data:
            return None, 'vacío'
        return data, (resp.headers.get('Content-Type') or 'application/octet-stream')
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, str(e)[:120])


def archivar_pendientes_r2(app, limite=50, presupuesto_seg=45):
    """Sube a R2 los documentos regulados aún sin snapshot (r2_key vacío).
    Idempotente (solo toma los pendientes), batched (limite), best-effort. Retorna dict con conteos.

    ANTI-HANG (M89/M90/M91): `presupuesto_seg` = tope de reloj (wall-clock) por corrida → el loop corta
    aunque falte trabajo (el resto queda en `pendientes`, se drena en la próxima llamada · idempotente),
    así NUNCA retiene un worker hasta el SIGKILL (--timeout 120) ni cuelga el hilo del cron. Circuit-breaker:
    tras varios PUT fallidos SEGUIDOS (R2 caído) corta el lote en vez de moler cada ítem contra el timeout."""
    import hashlib
    import time as _time
    if not r2_configurado():
        return {'ok': False, 'error': 'R2 no configurado', 'archivados': 0, 'pendientes': None}
    try:
        from database import get_db
    except Exception:
        from api.database import get_db  # pragma: no cover
    res = {'ok': True, 'archivados': 0, 'fallidos': 0, 'saltados': 0, 'detalle_fallos': []}
    with app.app_context():
        conn = get_db()
        c = conn.cursor()
        rows = c.execute(
            "SELECT id, entidad, codigo, producto_nombre, lote, tipo_doc, url "
            "FROM documentos_regulados WHERE COALESCE(anulado,0)=0 AND COALESCE(r2_key,'')='' "
            "ORDER BY id DESC LIMIT ?", (int(limite),)).fetchall()
        cols = [x[0] for x in c.description]
    _t0 = _time.monotonic()
    _fallos_r2_seguidos = 0
    for row in rows:
        if _time.monotonic() - _t0 > presupuesto_seg:
            res['corte_por_tiempo'] = True  # el resto queda en 'pendientes' · se retoma en la próxima corrida
            break
        if _fallos_r2_seguidos >= 4:
            res['corte_por_r2_caido'] = True  # circuit-breaker: R2 no responde · no molemos el lote entero
            break
        doc = dict(zip(cols, row))
        data, ct = _render_doc_bytes(app, doc.get('url'))
        if data is None:
            res['fallidos'] += 1  # fuente 404/render falla → NO cuenta para el circuit-breaker (no es R2 caído)
            if len(res['detalle_fallos']) < 12:
                res['detalle_fallos'].append({'id': doc.get('id'), 'tipo': doc.get('tipo_doc'), 'motivo': ct})
            continue
        sha = hashlib.sha256(data).hexdigest()
        ext = _ext_de(ct, doc.get('url'))
        key = _r2_key_documento(doc, sha, ext)
        if not r2_put(key, data, ct if isinstance(ct, str) else 'application/octet-stream'):
            res['fallidos'] += 1
            _fallos_r2_seguidos += 1  # PUT de red falló → si se repite, R2 está caído
            if len(res['detalle_fallos']) < 12:
                res['detalle_fallos'].append({'id': doc.get('id'), 'tipo': doc.get('tipo_doc'), 'motivo': 'PUT R2 falló'})
            continue
        _fallos_r2_seguidos = 0  # éxito → resetea el circuit-breaker
        # marcar como archivado (fecha en Python · PG-safe)
        try:
            from datetime import datetime as _dt
            _at = _dt.utcnow().replace(microsecond=0).isoformat() + 'Z'
            with app.app_context():
                conn = get_db()
                conn.execute("UPDATE documentos_regulados SET r2_key=?, r2_at=?, r2_sha256=?, r2_bytes=? "
                             "WHERE id=?", (key, _at, sha, len(data), doc.get('id')))
                conn.commit()
            res['archivados'] += 1
        except Exception as e:
            res['fallidos'] += 1
            log.warning('marcar r2 archivado falló (id=%s): %s', doc.get('id'), e)
    # pendientes restantes (informativo)
    try:
        with app.app_context():
            conn = get_db()
            res['pendientes'] = conn.execute(
                "SELECT COUNT(*) FROM documentos_regulados WHERE COALESCE(anulado,0)=0 AND COALESCE(r2_key,'')=''"
            ).fetchone()[0]
    except Exception:
        res['pendientes'] = None
    return res


def coa_key(nombre):
    """Key ESTABLE del COA en R2 (para servir si se pierde el disco). Distinta de la key del expediente
    (que lleva sha+id · inmutable). Esta es 1:1 con el nombre de archivo → coa-download la resuelve directo."""
    import os as _os
    return 'coa/' + _os.path.basename(str(nombre or ''))


def backfill_coa_r2(app=None, limite=300, presupuesto_seg=90):
    """Sube a R2 (key estable coa/<nombre>) los COA que están en disco y aún no están en R2 → el disco
    deja de ser punto único (habilita quitarlo). Idempotente (salta los que ya están). Best-effort.

    ANTI-HANG (M90): corre en el hilo ÚNICO del multi-cron, así que se acota con `presupuesto_seg`
    (wall-clock · el resto se retoma la próxima noche, es idempotente) + circuit-breaker por fallos de R2
    seguidos → si R2 está caído no muele miles de archivos a ~30s c/u bloqueando los demás crons."""
    import os as _os
    import time as _time
    if not r2_configurado():
        return {'ok': False, 'error': 'R2 no configurado', 'subidos': 0}
    coa_dir = (_os.environ.get('COA_STORAGE_DIR', '') or '/var/data/coa').strip()
    res = {'ok': True, 'subidos': 0, 'ya_estaban': 0, 'fallidos': 0, 'dir': coa_dir}
    try:
        nombres = _os.listdir(coa_dir) if _os.path.isdir(coa_dir) else []
    except Exception as e:
        return {'ok': False, 'error': 'no pude leer %s: %s' % (coa_dir, e), 'subidos': 0}
    _mime = {'pdf': 'application/pdf', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}
    _t0 = _time.monotonic()
    _fallos_seguidos = 0
    _procesados = 0
    for nombre in nombres:
        if _procesados >= limite:
            res['corte_por_limite'] = True
            break
        if _time.monotonic() - _t0 > presupuesto_seg:
            res['corte_por_tiempo'] = True  # el resto se retoma la próxima corrida (idempotente)
            break
        if _fallos_seguidos >= 4:
            res['corte_por_r2_caido'] = True  # circuit-breaker: R2 no responde
            break
        full = _os.path.join(coa_dir, nombre)
        if not _os.path.isfile(full):
            continue
        key = coa_key(nombre)
        _existe = r2_existe(key)
        if _existe is True:
            res['ya_estaban'] += 1
            _fallos_seguidos = 0
            continue
        if _existe is None:  # R2 no configurado (no debería llegar acá) o error de red en head
            _fallos_seguidos += 1
            continue
        _procesados += 1
        try:
            with open(full, 'rb') as fh:
                data = fh.read()
            ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
            if r2_put(key, data, _mime.get(ext, 'application/octet-stream')):
                res['subidos'] += 1
                _fallos_seguidos = 0
            else:
                res['fallidos'] += 1
                _fallos_seguidos += 1
        except Exception as e:
            res['fallidos'] += 1
            log.warning('backfill_coa_r2 falló (%s): %s', nombre, e)
    return res


def coa_disco_vs_r2(limite=2000):
    """Audita cuántos COA del disco ya están en R2 (key estable coa/<nombre>) · read-only · para el
    preflight de 'quitar el disco'. Bounded (M92): head_object por archivo, tope `limite`."""
    import os as _os
    coa_dir = (_os.environ.get('COA_STORAGE_DIR', '') or '/var/data/coa').strip()
    res = {'dir': coa_dir, 'en_disco': 0, 'en_r2': 0, 'faltan_n': 0, 'faltan': []}
    if not _os.path.isdir(coa_dir):
        res['nota'] = 'el directorio COA no existe en disco (nada que migrar)'
        return res
    if not r2_configurado():
        res['nota'] = 'R2 no configurado'
        return res
    _n = 0
    for nombre in _os.listdir(coa_dir):
        if _n >= limite:
            res['truncado'] = True
            break
        full = _os.path.join(coa_dir, nombre)
        if not _os.path.isfile(full):
            continue
        _n += 1
        res['en_disco'] += 1
        if r2_existe(coa_key(nombre)) is True:
            res['en_r2'] += 1
        else:
            res['faltan_n'] += 1
            if len(res['faltan']) < 25:
                res['faltan'].append(nombre)
    return res


def r2_stats_expediente(conn):
    """Conteo archivados/pendientes para mostrar en la página de expediente."""
    try:
        arch = conn.execute("SELECT COUNT(*) FROM documentos_regulados WHERE COALESCE(anulado,0)=0 "
                            "AND COALESCE(r2_key,'')<>''").fetchone()[0]
        pend = conn.execute("SELECT COUNT(*) FROM documentos_regulados WHERE COALESCE(anulado,0)=0 "
                            "AND COALESCE(r2_key,'')=''").fetchone()[0]
        return {'archivados': arch, 'pendientes': pend, 'configurado': r2_configurado()}
    except Exception:
        return {'archivados': 0, 'pendientes': 0, 'configurado': r2_configurado()}
