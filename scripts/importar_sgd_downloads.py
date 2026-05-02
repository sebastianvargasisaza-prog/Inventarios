"""Importador 1-shot del SGD desde C:\\Users\\sebas\\Downloads\\.

Recorre los archivos .docx/.xlsx/.pdf del directorio, extrae código
(AAA-BBB-NNN[-FNN]) del nombre del archivo, deduplica versiones (mantiene
la más reciente "FINAL"/"v02"), detecta conflictos temáticos (mismo código
con temas distintos), y POSTea al endpoint /api/aseguramiento/sgd/importar.

Uso:
    python scripts/importar_sgd_downloads.py \\
        --base-url http://localhost:5000 \\
        --user sebastian --password XXX

Sebastián 1-may-2026 · ASG-NOR-001 · listado maestro automático.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from urllib import request, parse, error


SGD_PATTERN = re.compile(r'^([A-Z]{3})-([A-Z]{3})-(\d{1,3})(?:-([A-Z]\d{1,2}))?')


def extraer_codigo(filename: str) -> tuple[str | None, str | None, str | None, int | None, str | None]:
    """Devuelve (codigo_completo, area, tipo_doc, numero, subtipo) o (None,...) si no parsea."""
    base = os.path.basename(filename)
    m = SGD_PATTERN.match(base)
    if not m:
        return None, None, None, None, None
    area, tipo, num, sub = m.groups()
    codigo = f'{area}-{tipo}-{num}'
    if sub:
        codigo += f'-{sub}'
    return codigo, area, tipo, int(num), sub


def es_borrador(filename: str) -> bool:
    """Detecta archivos que son borradores/duplicados (no la versión vigente)."""
    base = os.path.basename(filename).lower()
    indicadores = [' (1).', ' (2).', ' (3).', ' (4).', '_borrador',
                    'falta separar', 'corr.', '_v01_v02']
    return any(ind in base for ind in indicadores)


def es_final(filename: str) -> bool:
    """Detecta archivos marcados como FINAL/v02/aprobados."""
    base = os.path.basename(filename).lower()
    return any(s in base for s in ['_final.', 'final.docx', 'final.pdf',
                                     '_v02', '_v03', 'actualizado', 'definitivo'])


def extraer_titulo(filename: str, codigo: str | None) -> str:
    """Extrae título limpio del nombre del archivo (después del código)."""
    base = os.path.splitext(os.path.basename(filename))[0]
    if codigo:
        # Quitar el código del inicio
        base = re.sub(r'^[A-Z]{3}-[A-Z]{3}-\d{1,3}(?:-[A-Z]\d{1,2})?', '', base)
    # Limpiar separadores
    base = base.lstrip(' _-').replace('_', ' ').replace('  ', ' ').strip()
    # Quitar versión y borradores
    base = re.sub(r'\bv\d+\b', '', base, flags=re.I).strip()
    base = re.sub(r'\bFINAL\b', '', base, flags=re.I).strip()
    base = re.sub(r'\(\d+\)', '', base).strip()
    return base[:200] or codigo or 'Sin título'


def escanear(directorio: str) -> tuple[list, list]:
    """Recorre el directorio · devuelve (items_a_importar, conflictos).

    Estrategia:
      - Agrupa archivos por código
      - Para cada código, elige el archivo "mejor" (FINAL > v02 > base > borrador)
      - Si hay archivos con temas claramente distintos al mismo código → conflicto
    """
    archivos = []
    for ext in ('.docx', '.xlsx', '.pdf', '.doc'):
        for f in sorted(os.listdir(directorio)):
            if f.lower().endswith(ext):
                full = os.path.join(directorio, f)
                if os.path.isfile(full):
                    archivos.append(f)

    # Agrupar por código
    por_codigo = defaultdict(list)
    sin_codigo = []
    for f in archivos:
        codigo, _, _, _, _ = extraer_codigo(f)
        if codigo:
            por_codigo[codigo].append(f)
        else:
            sin_codigo.append(f)

    items = []
    conflictos = []
    for codigo, files in sorted(por_codigo.items()):
        # Elegir archivo "mejor"
        files_sorted = sorted(files, key=lambda f: (
            0 if es_final(f) else (2 if es_borrador(f) else 1),  # FINAL=0, base=1, borrador=2
            -len(f),  # más largo gana en empate (más informativo)
        ))
        mejor = files_sorted[0]
        codigo_full, area, tipo, numero, sub = extraer_codigo(mejor)
        item = {
            'codigo': codigo_full,
            'area': area,
            'tipo_doc': tipo,
            'numero': numero,
            'subtipo': sub,
            'titulo': extraer_titulo(mejor, codigo_full),
            'archivo_origen': mejor,
            'version': 'v02' if 'v02' in mejor.lower() else ('v03' if 'v03' in mejor.lower() else '1'),
        }
        items.append(item)

        # Detectar conflicto temático: si los archivos del mismo código tienen
        # palabras clave MUY distintas, es señal de tema repetido (bug de Espagiria)
        if len(files) >= 2:
            temas = set()
            for f in files:
                # Extraer 3 primeras palabras significativas después del código
                titulo = extraer_titulo(f, codigo).lower()
                palabras = re.findall(r'[a-záéíóúñ]{4,}', titulo)
                # Filtrar palabras filler
                fillers = {'final', 'borrador', 'corr', 'actualizado', 'docx',
                            'pdf', 'definitivo', 'espagiria', 'laboratorio'}
                significativas = [p for p in palabras if p not in fillers][:2]
                if significativas:
                    temas.add(' '.join(significativas))
            # Si ≥2 temas únicos distintos → conflicto
            if len(temas) >= 2:
                conflictos.append({
                    'codigo': codigo,
                    'archivos': '; '.join(files),
                    'temas': '; '.join(sorted(temas)),
                })
    return items, conflictos, sin_codigo


def login(base_url: str, user: str, password: str) -> str | None:
    """Login y retorna cookie."""
    data = parse.urlencode({'username': user, 'password': password}).encode()
    req = request.Request(
        f'{base_url}/login',
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded',
                 'Origin': base_url},
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            cookies = resp.headers.get('Set-Cookie', '')
        return cookies.split(';')[0] if cookies else None
    except error.HTTPError as e:
        if e.code == 302:
            cookies = e.headers.get('Set-Cookie', '')
            return cookies.split(';')[0] if cookies else None
    except Exception as e:
        print(f'login error: {e}')
    return None


def post_importar(base_url: str, cookie: str, items: list) -> dict:
    """POST al endpoint de importación. Hace batches de 500."""
    resultados = {'insertados': 0, 'saltados': 0, 'errores': []}
    for i in range(0, len(items), 500):
        batch = items[i:i+500]
        body = json.dumps({'items': batch}).encode()
        req = request.Request(
            f'{base_url}/api/aseguramiento/sgd/importar',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Origin': base_url,
                'Cookie': cookie,
            },
            method='POST',
        )
        try:
            with request.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read())
            resultados['insertados'] += d.get('insertados', 0)
            resultados['saltados'] += d.get('saltados_ya_existian', 0)
            resultados['errores'].extend(d.get('errores', []))
        except error.HTTPError as e:
            print(f'batch {i}: HTTP {e.code}: {e.read()[:200]}')
            resultados['errores'].append(f'batch {i}: HTTP {e.code}')
        except Exception as e:
            print(f'batch {i}: {e}')
            resultados['errores'].append(f'batch {i}: {e}')
    return resultados


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directorio', default=r'C:\Users\sebas\Downloads')
    p.add_argument('--base-url', default='http://localhost:5000')
    p.add_argument('--user', default=os.environ.get('SMOKE_USER', ''))
    p.add_argument('--password', default=os.environ.get('SMOKE_PASSWORD', ''))
    p.add_argument('--dry-run', action='store_true', help='Solo escanear, no enviar')
    args = p.parse_args()

    print(f'Escaneando {args.directorio}...')
    items, conflictos, sin_codigo = escanear(args.directorio)
    print(f'\nResultados:')
    print(f'  Items SGD detectados: {len(items)}')
    print(f'  Conflictos temáticos: {len(conflictos)}')
    print(f'  Archivos sin código:  {len(sin_codigo)}')

    print(f'\nConflictos detectados (mismo código, temas distintos):')
    for c in conflictos[:20]:
        print(f'  · {c["codigo"]}: {c["temas"]}')
    if len(conflictos) > 20:
        print(f'  ... y {len(conflictos)-20} más')

    if args.dry_run:
        print('\n--dry-run · no se envía nada al servidor')
        # Imprimir primeros 10 items
        print('\nPrimeros 10 items que se importarían:')
        for it in items[:10]:
            print(f'  {it["codigo"]:18s} · {it["titulo"][:60]}')
        return

    if not args.user or not args.password:
        print('\nERROR: Faltan --user y --password (o env SMOKE_USER/SMOKE_PASSWORD)')
        sys.exit(1)

    print(f'\nAutenticando como {args.user}...')
    cookie = login(args.base_url, args.user, args.password)
    if not cookie:
        print('ERROR: login falló')
        sys.exit(1)
    print(f'Login OK · cookie obtenida')

    print(f'\nEnviando {len(items)} items al servidor...')
    res = post_importar(args.base_url, cookie, items)
    print(f'  Insertados: {res["insertados"]}')
    print(f'  Saltados (ya existían): {res["saltados"]}')
    if res['errores']:
        print(f'  Errores ({len(res["errores"])}):')
        for e in res['errores'][:10]:
            print(f'    · {e}')


if __name__ == '__main__':
    main()
