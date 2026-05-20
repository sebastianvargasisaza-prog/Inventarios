"""Aplica recálculo de stock_minimo en producción con modo uniforme.

Sebastián 20-may-2026 · "los mínimos sean para 90 días, que sí sean
reales los que están". Este script:

1. Login a producción (Render direct domain o app.eossuite.com)
2. GET /api/planta/auditar-minimos con dias_cobertura_minimo=90 (dry-run)
3. Muestra resumen: cuántos MPs cambian + delta total g
4. Pide confirmación humana ('SI APLICAR')
5. POST /api/admin/aplicar-minimos con token + dias_cobertura_minimo=90
6. Muestra resultado: count_cambios + audit_log id

Uso:
    python scripts/aplicar_minimos_uniforme_prod.py

Variables de entorno opcionales:
    EOS_URL        URL base (default https://inventarios-0363.onrender.com)
    EOS_USER       usuario admin (default sebastian)
    EOS_PASSWORD   password (si no, prompt interactivo)
"""
import getpass
import json
import os
import sys

import requests


BASE_URL = os.environ.get('EOS_URL', 'https://inventarios-0363.onrender.com').rstrip('/')
USER = os.environ.get('EOS_USER', 'sebastian')
PASSWORD = os.environ.get('EOS_PASSWORD') or getpass.getpass(f'Password para {USER}: ')
DIAS_COBERTURA = int(os.environ.get('EOS_DIAS_COBERTURA', '90'))


def main():
    session = requests.Session()
    print(f'\n[1/4] Login {USER} @ {BASE_URL}')
    r = session.post(
        f'{BASE_URL}/api/login',
        json={'usuario': USER, 'password': PASSWORD},
        timeout=30,
    )
    if not r.ok:
        print(f'  ✗ Login falló · {r.status_code} · {r.text[:200]}')
        sys.exit(1)
    print(f'  ✓ Login OK · status {r.status_code}')

    print(f'\n[2/4] Dry-run · auditando con dias_cobertura_minimo={DIAS_COBERTURA}')
    r2 = session.get(
        f'{BASE_URL}/api/planta/auditar-minimos',
        params={'proyeccion_dias': 90, 'dias_cobertura_minimo': DIAS_COBERTURA},
        timeout=120,
    )
    if not r2.ok:
        print(f'  ✗ Audit falló · {r2.status_code} · {r2.text[:200]}')
        sys.exit(1)
    d = r2.json()
    stats = d.get('stats', {})
    total = stats.get('total', 0)
    sub = stats.get('sub_protegido', 0)
    sobre = stats.get('sobre_protegido', 0)
    vacios = stats.get('sin_minimo', 0)
    ok_count = stats.get('ok', 0)
    sin_uso = stats.get('sin_uso', 0)
    print(f'  ✓ {total} MPs auditadas · modo uniforme {DIAS_COBERTURA}d')
    print(f'    ▸ OK         : {ok_count}')
    print(f'    ▸ SUB        : {sub} (mínimo < 75% recomendado)')
    print(f'    ▸ SOBRE      : {sobre} (mínimo > 150% recomendado)')
    print(f'    ▸ Sin mínimo : {vacios} (consumo > 0 pero stock_min=0)')
    print(f'    ▸ Sin uso    : {sin_uso} (no se tocarán)')

    # Calcular delta total
    suma_actual = 0.0
    suma_nuevo = 0.0
    cambios = 0
    for item in (d.get('auditoria') or []):
        if item['estado'] not in ('SUB_PROTEGIDO', 'SOBRE_PROTEGIDO', 'SIN_MINIMO_CONFIGURADO'):
            continue
        actual = float(item.get('stock_minimo_actual_g') or 0)
        nuevo = float(item.get('minimo_recomendado_g') or 0)
        if abs(nuevo - actual) < 0.5:
            continue
        suma_actual += actual
        suma_nuevo += nuevo
        cambios += 1
    delta = suma_nuevo - suma_actual
    print(f'\n  ▸ MPs que cambiarían   : {cambios}')
    print(f'  ▸ Suma mínimos actual  : {suma_actual:,.0f} g')
    print(f'  ▸ Suma mínimos nuevo   : {suma_nuevo:,.0f} g')
    print(f'  ▸ Delta neto           : {"+" if delta >= 0 else ""}{delta:,.0f} g')

    if cambios == 0:
        print('\n  ✓ Nada para aplicar · ya están todos OK.')
        return

    print(f'\n[3/4] Confirmación')
    resp = input(
        f'  ¿Aplicar {cambios} cambios en producción? (escribí "SI APLICAR" exacto): '
    ).strip()
    if resp != 'SI APLICAR':
        print('  ✗ Cancelado por el usuario.')
        return

    print(f'\n[4/4] Aplicando recálculo · puede tardar 10-30s')
    r3 = session.post(
        f'{BASE_URL}/api/admin/aplicar-minimos',
        json={
            'token': 'APLICAR_MINIMOS_RECALCULADOS_2026',
            'proyeccion_dias': 90,
            'dias_cobertura_minimo': DIAS_COBERTURA,
        },
        timeout=180,
    )
    if not r3.ok:
        print(f'  ✗ Apply falló · {r3.status_code} · {r3.text[:300]}')
        sys.exit(1)
    res = r3.json()
    print(f'  ✓ Aplicado · {res.get("mensaje", "OK")}')
    print(f'    count_cambios: {res.get("count_cambios")}')
    if res.get('backup_estado'):
        print(f'    backup_estado: {res["backup_estado"]}')
    print('\n✓ Listo. Recarga Bodega MP en EOS para ver los nuevos mínimos.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n✗ Interrumpido')
        sys.exit(1)
    except requests.RequestException as e:
        print(f'\n✗ Error de red: {e}')
        sys.exit(1)
