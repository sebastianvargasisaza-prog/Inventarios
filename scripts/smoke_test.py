"""Smoke test post-deploy.

Pega los endpoints críticos en producción y verifica que están vivos.
Útil después de cada `git push origin main` para detectar regresiones rápido.

Uso:
    python scripts/smoke_test.py https://app.eossuite.com
    python scripts/smoke_test.py http://localhost:5000  # local

Exit code 0 = todos OK, 1 = al menos uno falló.

Requiere usuario+password de test si se pasa --auth (sino solo prueba públicos).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional
from urllib import request, parse, error


# Endpoints públicos (no requieren auth)
PUBLIC_ENDPOINTS = [
    ('GET', '/api/health', None),
    ('GET', '/login', None),  # HTML, debe cargar
]

# Endpoints autenticados críticos (requieren login)
AUTH_ENDPOINTS = [
    ('GET',  '/api/planta/health-check',           None),
    ('GET',  '/api/planta/cron-jobs-status',       None),
    ('GET',  '/api/programacion/resumen',          None),
    ('GET',  '/api/movimientos',                   None),
    ('GET',  '/api/maestro-mps?limit=5',           None),
    ('GET',  '/api/solicitudes-compra?limit=5',    None),
    ('GET',  '/api/ordenes-compra?limit=5',        None),
    ('GET',  '/api/calidad/no-conformidades',      None),
    ('GET',  '/api/planta/validar-hermanos-skus',  None),
    ('GET',  '/api/auto-plan/configs/sku',         None),
]


def _login(base_url: str, username: str, password: str) -> Optional[str]:
    """Login y retorna cookie jar serializado o None si falla."""
    data = parse.urlencode({'username': username, 'password': password}).encode()
    req = request.Request(
        f'{base_url}/login',
        data=data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': base_url,
        },
        method='POST',
    )
    try:
        # Permitir 302 (redirect después de login OK)
        opener = request.build_opener(request.HTTPRedirectHandler())
        with opener.open(req, timeout=15) as resp:
            cookies = resp.headers.get('Set-Cookie', '')
        return cookies.split(';')[0] if cookies else None
    except error.HTTPError as e:
        if e.code == 302:
            cookies = e.headers.get('Set-Cookie', '')
            return cookies.split(';')[0] if cookies else None
        return None
    except Exception:
        return None


def _hit(base_url: str, method: str, path: str, cookie: Optional[str],
         body: Optional[dict] = None, timeout: int = 20) -> tuple[bool, int, str]:
    """Ejecuta una request. Retorna (ok, status_code, error_msg)."""
    headers = {'User-Agent': 'smoke-test/1.0', 'Accept': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    if body is not None:
        headers['Content-Type'] = 'application/json'
        headers['Origin'] = base_url
    data = json.dumps(body).encode() if body else None
    req = request.Request(f'{base_url}{path}', data=data,
                           headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return True, resp.status, ''
    except error.HTTPError as e:
        # 401 esperado en endpoints auth si no hay cookie
        return False, e.code, f'HTTP {e.code}'
    except Exception as e:
        return False, 0, f'{type(e).__name__}: {e}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('base_url', help='Base URL · ej. https://app.eossuite.com')
    parser.add_argument('--user', default=os.environ.get('SMOKE_USER', ''),
                         help='Usuario para tests autenticados')
    parser.add_argument('--password', default=os.environ.get('SMOKE_PASSWORD', ''),
                         help='Password para tests autenticados')
    parser.add_argument('--skip-auth', action='store_true',
                         help='Solo probar endpoints públicos')
    args = parser.parse_args()

    base_url = args.base_url.rstrip('/')
    print(f'\n=== SMOKE TEST · {base_url} ===\n')

    # Tests públicos
    print('\n[1] Endpoints públicos:')
    fails = []
    for method, path, body in PUBLIC_ENDPOINTS:
        t0 = time.time()
        ok, code, err = _hit(base_url, method, path, cookie=None, body=body)
        dur = int((time.time() - t0) * 1000)
        status = 'OK' if ok else 'FAIL'
        print(f'  [{status}] {method} {path}  · {code}  · {dur}ms  {err}')
        if not ok:
            fails.append(f'{method} {path}: {err}')

    # Tests autenticados
    if not args.skip_auth and args.user and args.password:
        print(f'\n[2] Login con user={args.user}:')
        cookie = _login(base_url, args.user, args.password)
        if not cookie:
            print('  [FAIL] login falló (verifica credenciales o que el dominio resuelva)')
            fails.append('login fallo')
        else:
            print(f'  [OK] login · cookie obtenida')
            print('\n[3] Endpoints autenticados:')
            for method, path, body in AUTH_ENDPOINTS:
                t0 = time.time()
                ok, code, err = _hit(base_url, method, path, cookie=cookie, body=body)
                dur = int((time.time() - t0) * 1000)
                status = 'OK' if ok else 'FAIL'
                print(f'  [{status}] {method} {path}  · {code}  · {dur}ms  {err}')
                if not ok:
                    fails.append(f'{method} {path}: {err}')
    elif not args.skip_auth:
        print('\n[2] Login skipped (sin --user / --password ni env SMOKE_USER/SMOKE_PASSWORD)')

    # Resumen
    print('\n=== RESUMEN ===')
    total_public = len(PUBLIC_ENDPOINTS)
    total_auth = len(AUTH_ENDPOINTS) if not args.skip_auth and args.user else 0
    total = total_public + total_auth
    print(f'Total: {total} · OK: {total - len(fails)} · FAIL: {len(fails)}')
    if fails:
        print('\nFALLAS:')
        for f in fails:
            print(f'  - {f}')
        sys.exit(1)
    print('Todos los smokes OK.')
    sys.exit(0)


if __name__ == '__main__':
    main()
