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

log = logging.getLogger('r2_storage')


def _cfg():
    return {
        'endpoint': (os.environ.get('R2_ENDPOINT', '') or '').strip(),
        'bucket': (os.environ.get('R2_BUCKET', '') or '').strip(),
        'key': (os.environ.get('R2_ACCESS_KEY', '') or '').strip(),
        'secret': (os.environ.get('R2_SECRET_KEY', '') or '').strip(),
    }


def r2_configurado():
    """¿Están las 4 variables de entorno? (no valida credenciales · solo presencia)."""
    c = _cfg()
    return bool(c['endpoint'] and c['bucket'] and c['key'] and c['secret'])


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
        import boto3  # noqa: F401 · verificar que boto3 está instalado antes de operar
    except Exception:
        return {'ok': False, 'configurado': True, 'error': 'boto3 no está instalado en el servidor (revisar requirements/deploy)'}
    try:
        if not r2_put(key, payload, 'text/plain'):
            return {'ok': False, 'configurado': True,
                    'error': 'no se pudo ESCRIBIR (PUT) · revisá que el token tenga permiso Object Read & Write sobre el bucket, y que el endpoint/bucket sean correctos'}
        got = r2_get(key)
        r2_delete(key)
        if got != payload:
            return {'ok': False, 'configurado': True, 'error': 'escribió pero la LECTURA no coincidió'}
        c = _cfg()
        return {'ok': True, 'configurado': True, 'bucket': c['bucket'], 'endpoint': c['endpoint'],
                'mensaje': 'R2 conectado correctamente: escritura + lectura + borrado OK'}
    except Exception as e:
        return {'ok': False, 'configurado': True, 'error': str(e)[:280]}
