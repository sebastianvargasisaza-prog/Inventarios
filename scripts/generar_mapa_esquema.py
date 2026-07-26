#!/usr/bin/env python3
"""Genera MAPA_ESQUEMA.md · las 269 tablas de EOS, quién las escribe y quién las lee.

    python scripts/generar_mapa_esquema.py

Por qué generado: el esquema son ~269 tablas y ~3.470 columnas construidas por 378 migraciones.
Un diagrama dibujado a mano queda viejo en la siguiente migración, y un mapa de datos que miente
hace tomar decisiones equivocadas (varias de las que costaron caro en EOS fueron por consultar una
columna que no existía o confundir dos tablas parecidas · `facturas` AR vs `facturas_proveedor` AP).

Lo que hace: crea el esquema REAL en una BD temporal (corriendo `init_db`, o sea las 378
migraciones), lo lee, y cruza cada tabla contra los blueprints para saber quién le ESCRIBE
(INSERT/UPDATE/DELETE) y quién la LEE. La columna "escribe" es la importante: si una tabla la
escriben 5 módulos distintos, ahí es donde aparece el drift.
"""
import os
import re
import sqlite3
import sys
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(RAIZ, '_mapa_esquema_tmp.db')

# Tablas que son el corazón: si una de estas cambia, hay que mirar dos veces.
CRITICAS = {
    'movimientos': 'kardex de MATERIA PRIMA · el stock es SUM(movimientos), nunca un cache',
    'movimientos_mee': 'kardex de ENVASES · idem, vía _get_mee_stock',
    'formula_headers': 'la receta maestra (cabecera) · `activo=0` = descontinuada, NUNCA DELETE',
    'formula_items': 'la receta: % por MP · `porcentaje` es la verdad, `cantidad_g_por_lote` es derivada',
    'produccion_programada': 'el plan · `origen` separa lo que fijó el usuario de lo que sugiere la IA',
    'mbr_templates': 'procedimiento maestro aprobado · INMUTABLE una vez aprobado (mig 109)',
    'mbr_pasos': 'los pasos del procedimiento · inmutables si el MBR está aprobado',
    'ebr_ejecuciones': 'el legajo de UN lote real · inmutable si está liberado/rechazado (mig 111)',
    'ebr_pasos_ejecutados': 'ejecución paso a paso, con firma · una firma no se borra jamás',
    'audit_log': 'evidencia Part 11 · inmutable por trigger (mig 105)',
    'e_signatures': 'firmas electrónicas con snapshot de identidad',
    'ordenes_compra': 'las OC · el dinero',
    'maestro_mps': 'maestro de materias primas · la identidad es el CÓDIGO, no el INCI',
    'maestro_mee': 'maestro de envases',
    'app_settings': 'interruptores de negocio (modo inventario, gates, crons) · sin redeploy',
}

ESCRITURA = re.compile(r'(INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+["\']?(\w+)', re.I)
LECTURA = re.compile(r'FROM\s+["\']?(\w+)|JOIN\s+["\']?(\w+)', re.I)


def _uso_por_modulo():
    escribe, lee = defaultdict(set), defaultdict(set)
    for sub in ('blueprints', ''):
        d = os.path.join(RAIZ, 'api', sub) if sub else os.path.join(RAIZ, 'api')
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.py'):
                continue
            path = os.path.join(d, f)
            if os.path.isdir(path):
                continue
            try:
                src = open(path, encoding='utf-8').read()
            except Exception:
                continue
            mod = f[:-3]
            for m in ESCRITURA.finditer(src):
                escribe[m.group(2).lower()].add(mod)
            for m in LECTURA.finditer(src):
                t = (m.group(1) or m.group(2) or '').lower()
                if t:
                    lee[t].add(mod)
    return escribe, lee


def main():
    if os.path.exists(TMP):
        os.remove(TMP)
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    os.environ['DB_PATH'] = TMP
    os.environ['EOS_DISABLE_DAEMONS'] = '1'
    import database as D
    D.init_db()
    conn = sqlite3.connect(TMP)
    tablas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    escribe, lee = _uso_por_modulo()

    info = {}
    total_cols = 0
    for t in tablas:
        cols = list(conn.execute('PRAGMA table_info(%s)' % t))
        total_cols += len(cols)
        pk = [c[1] for c in cols if c[5]]
        fks = list(conn.execute('PRAGMA foreign_key_list(%s)' % t))
        idx = [r[1] for r in conn.execute('PRAGMA index_list(%s)' % t)]
        info[t] = {'cols': cols, 'pk': pk, 'fks': fks, 'idx': idx,
                   'escribe': sorted(escribe.get(t, set())), 'lee': sorted(lee.get(t, set()))}

    mig = len(D.MIGRATIONS)
    out = [
        '# Mapa del esquema · EOS',
        '',
        '> **GENERADO** por `python scripts/generar_mapa_esquema.py` · no editar a mano.',
        '> Sale del esquema REAL (corre las %d migraciones en una BD temporal), así que no puede' % mig,
        '> quedar desactualizado en silencio.',
        '',
        '**%d tablas · %d columnas · %d migraciones**' % (len(tablas), total_cols, mig),
        '',
        '## Tablas del corazón',
        '',
        'Si tocás una de estas, leé antes el CONTRACT del módulo dueño.',
        '',
        '| Tabla | Qué es | Columnas | Escriben |',
        '|---|---|---:|---|',
    ]
    for t, desc in CRITICAS.items():
        if t not in info:
            out.append('| `%s` | %s | — | **NO EXISTE con ese nombre** |' % (t, desc))
            continue
        i = info[t]
        out.append('| `%s` | %s | %d | %s |' % (
            t, desc, len(i['cols']), ', '.join(i['escribe']) or '—'))

    # Una tabla que escriben muchos módulos es donde nace el drift.
    multi = sorted(((len(i['escribe']), t) for t, i in info.items() if len(i['escribe']) >= 4),
                   reverse=True)
    out += ['', '## Tablas que escriben 4+ módulos', '',
            'Acá nace el drift: si cinco módulos escriben la misma tabla, tarde o temprano uno lo',
            'hace con otro criterio. Cada una debería tener UN dueño y que el resto delegue (M3).',
            '', '| Tabla | Módulos que escriben |', '|---|---|']
    for _n, t in multi:
        out.append('| `%s` | %s |' % (t, ', '.join(info[t]['escribe'])))

    huerfanas = [t for t, i in info.items() if not i['escribe'] and not i['lee']]
    out += ['', '## Tablas que nadie toca (%d)' % len(huerfanas), '',
            'Ni un INSERT ni un SELECT en todo el código. O son histórico que se conserva a',
            'propósito, o son features muertas. Vale revisarlas antes de que confundan a alguien.',
            '', '```', ', '.join(huerfanas) or '(ninguna)', '```']

    out += ['', '## Todas las tablas', '']
    for t in tablas:
        i = info[t]
        out += ['### `%s`' % t, '',
                '- **Columnas (%d):** %s' % (len(i['cols']), ', '.join('`%s`' % c[1] for c in i['cols'])),
                '- **PK:** %s' % (', '.join('`%s`' % c for c in i['pk']) or '—'),
                '- **Escriben:** %s' % (', '.join(i['escribe']) or '—'),
                '- **Leen:** %s' % (', '.join(i['lee']) or '—')]
        if i['fks']:
            out.append('- **FK:** %s' % ', '.join('`%s`→`%s.%s`' % (f[3], f[2], f[4]) for f in i['fks']))
        out.append('')

    with open(os.path.join(RAIZ, 'MAPA_ESQUEMA.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')
    conn.close()
    os.remove(TMP)
    print('MAPA_ESQUEMA.md · %d tablas · %d columnas · %d con 4+ escritores · %d huerfanas'
          % (len(tablas), total_cols, len(multi), len(huerfanas)))


if __name__ == '__main__':
    main()
