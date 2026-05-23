"""Resolver-todo · migraciones pendientes PG + fix MPs abreviaturas en prod.

Sebastián 22-may-2026 noche · 'resuelve todo'. Orquesta en orden:

  1. Login a prod (https://inventarios-0363.onrender.com)
  2. Dry-run de migraciones · muestra resumen
  3. CONFIRMACIÓN HUMANA: aplicar migraciones
  4. POST {aplicar:true, solo_version:158}  → crea mp_aliases primero
  5. Verifica que mps-abreviaturas-audit ya NO falla
  6. POST {aplicar:true}                     → aplica las 19 restantes
  7. Reporta falladas (si hay)
  8. GET /mps-abreviaturas-audit             → muestra hallazgos reales
  9. CONFIRMACIÓN HUMANA: aplicar fix
 10. POST /mps-abreviaturas-fix {dry_run:true}   → preview
 11. POST /mps-abreviaturas-fix {}                → aplica
 12. Resumen final + audit limpio

Uso:
    python scripts/resolver_todo_22may.py
    (te pedirá password de sebastian@prod, NO se loguea en archivo)

Vars opcionales:
    EOS_URL        URL base (default https://inventarios-0363.onrender.com)
    EOS_USER       usuario admin (default sebastian)
    EOS_PASSWORD   password (si no, prompt interactivo seguro)
"""
import getpass
import json
import os
import sys

import requests


BASE_URL = os.environ.get('EOS_URL', 'https://inventarios-0363.onrender.com').rstrip('/')
USER = os.environ.get('EOS_USER', 'sebastian')
PASSWORD = os.environ.get('EOS_PASSWORD') or getpass.getpass(f'Password para {USER}@prod: ')


def jprint(d, indent=2):
    print(json.dumps(d, indent=indent, ensure_ascii=False))


def confirmar(prompt):
    print()
    print('=' * 70)
    resp = input(f'{prompt}\nEscribe "SI APLICAR" para continuar (cualquier otra cosa aborta): ').strip()
    print('=' * 70)
    if resp != 'SI APLICAR':
        print(f'Abortado por el usuario (respuesta: {resp!r}).')
        sys.exit(1)


def main():
    s = requests.Session()
    # Origin header obligatorio (CSRF defense capa 1 · api/auth.py:393).
    # Lo seteamos en la sesión para que aplique a TODAS las peticiones.
    from urllib.parse import urlparse
    origin = f'{urlparse(BASE_URL).scheme}://{urlparse(BASE_URL).netloc}'
    s.headers.update({'Origin': origin, 'Referer': origin + '/'})

    print(f'\n[1/12] Login {USER} @ {BASE_URL}')
    # Ruta real: POST /login (form-data, no JSON · api/blueprints/core.py:1387)
    # Campos: username + password. Redirige 302:
    #   - /modulos (login completo, sin MFA)
    #   - /login/mfa (paso 2 · TOTP)
    r = s.post(f'{BASE_URL}/login',
               data={'username': USER, 'password': PASSWORD},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        snippet = r.text[:300]
        print(f'  ERROR login: {r.status_code} · {snippet}')
        sys.exit(1)
    location = r.headers.get('Location', '')
    print(f'  Paso 1 OK · status {r.status_code} → {location}')

    if '/login/mfa' in location:
        print('\n  ⚠ MFA activado · necesito el codigo de 6 digitos de tu')
        print('    app de autenticacion (Google Authenticator, Authy, etc.)')
        for intento in range(3):
            totp = input(f'    Codigo MFA (6 digitos) [intento {intento+1}/3]: ').strip()
            if not totp or not totp.isdigit() or len(totp) != 6:
                print('    ✗ debe ser 6 digitos · reintenta')
                continue
            r2 = s.post(f'{BASE_URL}/login/mfa',
                        data={'token': totp},
                        allow_redirects=False, timeout=30)
            if r2.status_code in (302, 303) and '/login/mfa' not in r2.headers.get('Location', ''):
                print(f'  Paso 2 OK · MFA verificado → {r2.headers.get("Location", "?")}')
                break
            print('    ✗ token incorrecto · reintenta')
        else:
            print('  ERROR MFA: 3 intentos fallidos · aborta')
            sys.exit(1)

    # CSRF token obligatorio para POST /api/admin/* (api/auth.py:425-427).
    print('  Obteniendo CSRF token...')
    r = s.get(f'{BASE_URL}/api/csrf-token', timeout=15)
    if not r.ok:
        print(f'  ERROR csrf-token: {r.status_code} · {r.text[:200]}')
        sys.exit(1)
    csrf = r.json().get('csrf_token', '')
    if not csrf:
        print(f'  ERROR · csrf_token vacío: {r.text[:200]}')
        sys.exit(1)
    s.headers.update({'X-CSRF-Token': csrf})
    print('  OK · csrf token obtenido')

    # ---------------------------------------------------------------- 1. Dry-run
    print('\n[2/12] Dry-run migraciones pendientes')
    r = s.get(f'{BASE_URL}/api/admin/aplicar-migraciones-pg', timeout=60)
    if not r.ok:
        print(f'  ERROR: {r.status_code} · {r.text[:500]}')
        sys.exit(1)
    d = r.json()
    pendientes = d.get('pendientes', 0)
    aplicadas_prev = d.get('aplicadas_previamente', 0)
    print(f'  Aplicadas previamente: {aplicadas_prev}')
    print(f'  Pendientes: {pendientes}')
    if pendientes == 0:
        print('  Nada que aplicar. Saltando al fix de abreviaturas.')
    else:
        print('\n  Versiones pendientes:')
        for m in d.get('detalle', []):
            print(f'    {m["version"]:>3} · {m["n_stmts"]:>2} stmts · {m["description"]}')

        confirmar(f'¿Aplicar las {pendientes} migraciones pendientes a PROD PG?')

        # ---------------------------------------------- 3. Aplicar 158 primero
        print('\n[3/12] POST {aplicar:true, solo_version:158} · mp_aliases')
        r = s.post(f'{BASE_URL}/api/admin/aplicar-migraciones-pg',
                   json={'aplicar': True, 'solo_version': 158}, timeout=120)
        if not r.ok:
            print(f'  ERROR: {r.status_code} · {r.text[:500]}')
            sys.exit(1)
        d3 = r.json()
        print(f'  Aplicadas: {d3["aplicadas"]} · Falladas: {d3["falladas"]}')
        if d3['falladas']:
            print('  FALLADAS:')
            jprint(d3['detalle_falladas'])
            sys.exit(1)

        # ---------------------------------------------- 4. Verificar mp_aliases vive
        print('\n[4/12] Verificar: GET /mps-abreviaturas-audit (sin error?)')
        r = s.get(f'{BASE_URL}/api/admin/mps-abreviaturas-audit', timeout=60)
        if r.status_code != 200:
            print(f'  ERROR · audit aún falla: {r.status_code} · {r.text[:300]}')
            sys.exit(1)
        print(f'  OK · audit responde 200')

        # ---------------------------------------------- 5. Aplicar las restantes
        print('\n[5/12] POST {aplicar:true} · resto de migraciones (19)')
        r = s.post(f'{BASE_URL}/api/admin/aplicar-migraciones-pg',
                   json={'aplicar': True}, timeout=300)
        if not r.ok:
            print(f'  ERROR: {r.status_code} · {r.text[:500]}')
            sys.exit(1)
        d5 = r.json()
        print(f'  Aplicadas: {d5["aplicadas"]} · Falladas: {d5["falladas"]}')
        if d5['detalle_aplicadas']:
            print('  Versiones aplicadas:')
            for a in d5['detalle_aplicadas']:
                print(f'    {a["version"]:>3} · {a["description"]}')
        if d5['falladas']:
            print('  ⚠ FALLADAS (revisar manualmente):')
            jprint(d5['detalle_falladas'])
            print('  ⚠ Continuando · las falladas se pueden re-intentar individualmente luego.')

    # ---------------------------------------------- 6. Audit abreviaturas en prod
    print('\n[6/12] GET /mps-abreviaturas-audit · hallazgos reales en prod')
    r = s.get(f'{BASE_URL}/api/admin/mps-abreviaturas-audit', timeout=60)
    if not r.ok:
        print(f'  ERROR: {r.status_code} · {r.text[:500]}')
        sys.exit(1)
    d6 = r.json()
    print(f'  Total hallazgos: {d6["total_hallazgos"]}')
    print(f'  A renombrar:     {d6["a_renombrar"]}')
    print(f'  Duplicados merge:{d6["duplicados_a_merge"]}')
    print(f'  Aliases cargados:{d6["aliases_cargados"]}')
    if d6['total_hallazgos'] == 0:
        print('  Nada que arreglar. Cron job_auto_normalizar_formulas tomará deltas futuros.')
        print('\nLISTO. ✓')
        return

    print('\n  Primeros 30 hallazgos:')
    for h in d6.get('hallazgos', [])[:30]:
        print(f'    {h["codigo_mp"]:>10} · {h["campo"]:>16} = {h["valor_actual"]!r:>20} '
              f'→ {h["inci_canonical"]!r:>40} · {h["accion_sugerida"]}'
              + (f' [DUP de {h["es_duplicado_de"]}]' if h["es_duplicado_de"] else ''))

    confirmar(f'¿Aplicar fix a {d6["total_hallazgos"]} MPs '
              f'({d6["a_renombrar"]} renombrar + {d6["duplicados_a_merge"]} merge)?')

    # ---------------------------------------------- 7. Fix dry-run
    print('\n[7/12] POST /mps-abreviaturas-fix {dry_run:true} · preview')
    r = s.post(f'{BASE_URL}/api/admin/mps-abreviaturas-fix',
               json={'dry_run': True}, timeout=120)
    if not r.ok:
        print(f'  ERROR: {r.status_code} · {r.text[:500]}')
        sys.exit(1)
    d7 = r.json()
    print(f'  (dry) Renombrados: {d7["renombrados"]} · Mergeados: {d7["mergeados"]} · Saltados: {d7["saltados"]}')

    # ---------------------------------------------- 8. Fix real
    print('\n[8/12] POST /mps-abreviaturas-fix {} · APLICANDO')
    r = s.post(f'{BASE_URL}/api/admin/mps-abreviaturas-fix',
               json={}, timeout=180)
    if not r.ok:
        print(f'  ERROR: {r.status_code} · {r.text[:500]}')
        sys.exit(1)
    d8 = r.json()
    print(f'  Renombrados: {d8["renombrados"]}')
    print(f'  Mergeados:   {d8["mergeados"]}')
    print(f'  Saltados:    {d8["saltados"]}')
    if d8['detalle_saltados']:
        print('  ⚠ SALTADOS:')
        jprint(d8['detalle_saltados'][:10])

    # ---------------------------------------------- 9. Validación final
    print('\n[9/12] GET /mps-abreviaturas-audit · validar que quedó limpio')
    r = s.get(f'{BASE_URL}/api/admin/mps-abreviaturas-audit', timeout=60)
    if r.ok:
        df = r.json()
        print(f'  Hallazgos restantes: {df["total_hallazgos"]}')
        if df['total_hallazgos'] == 0:
            print('  ✓ Cero abreviaturas residuales.')
        else:
            print('  ⚠ Aún hay hallazgos · revisar manualmente:')
            for h in df.get('hallazgos', [])[:10]:
                print(f'    {h["codigo_mp"]} · {h["campo"]}={h["valor_actual"]!r} → {h["inci_canonical"]!r}')

    print('\n' + '=' * 70)
    print('RESUELTO. ✓')
    print('=' * 70)


if __name__ == '__main__':
    main()
