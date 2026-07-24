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
