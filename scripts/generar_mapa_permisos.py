#!/usr/bin/env python3
"""Genera MAPA_PERMISOS.md · quién puede entrar a cada ruta de EOS.

Por qué GENERADO y no escrito a mano: son ~1.650 rutas. Un documento escrito a mano sobre eso
está desactualizado el día que se termina, y un mapa de permisos desactualizado es peor que no
tenerlo (da confianza falsa). Esto se vuelve a correr y listo:

    python scripts/generar_mapa_permisos.py

Cómo funciona: recorre el `url_map` REAL de Flask (no una lista a mano · lección M97: un guardián
con lista blanca hardcodeada se pudre y da falsos positivos), busca la función que atiende cada
ruta y detecta en su código qué gate aplica. Lo que no puede resolver lo marca `?` en vez de
inventarlo.

Limitación honesta: detecta el gate por PATRÓN de código. Si alguien inventa una forma nueva de
gatear, sale como `?` — que es la señal de "andá a mirar eso", no un error del script.
"""
import ast
import os
import re
import sys
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
os.environ.setdefault('DB_PATH', os.path.join(RAIZ, '_mapa_permisos.db'))

# Patrón de gate → (etiqueta, cómo se lee). El orden importa: gana el más restrictivo.
GATES = [
    (r'_require_admin\(\)|ADMIN_USERS\b(?!.*\|)', 'ADMIN', 'solo Sebastián y Alejandro'),
    (r'gate_ver_formulas|_puede_ver_formulas', 'FÓRMULAS (INVIMA)', 'Técnica ∪ Calidad ∪ Aseguramiento ∪ Dirección'),
    (r'_require_qa_or_admin', 'CALIDAD+ADMIN', 'Control de Calidad o Dirección'),
    (r'_require_brd_ejecutor', 'EJECUTOR DE LOTE', 'Planta ∪ Calidad ∪ Admin'),
    (r'_autorizados_equipos|ASEGURAMIENTO_USERS', 'ASEGURAMIENTO', 'Miguel + Calidad + Admin'),
    (r'CALIDAD_USERS', 'CALIDAD', 'Laura, Yulieth + Admin'),
    (r'TECNICA_USERS', 'TÉCNICA', 'Hernando, Miguel + Admin'),
    (r'CONTADORA_USERS|FINANZAS_ACCESS', 'FINANZAS', 'contadora / compras + Admin'),
    (r'COMPRAS_ACCESS|_require_compras_write', 'COMPRAS', 'Catalina, Mayra + Admin'),
    (r'_require_planta_write|PLANTA_USERS', 'PLANTA', 'operarios de planta + Admin'),
    (r'MARKETING_USERS', 'MARKETING', 'equipo de marketing + Admin'),
    (r'RRHH_USERS', 'RRHH', 'Gloria + asistentes + Admin'),
    (r'_require_session|_require_login|_auth\(\)|compras_user', 'AUTENTICADO', 'cualquier usuario con sesión'),
]

PUBLICAS = ('/login', '/logout', '/static/', '/api/health', '/api/csrf-token', '/api/pqr/inbound')

# Gates que NO viven en la función sino en un `before_request` por PREFIJO (index.py). Un
# detector que sólo mira el cuerpo de la función los reporta como "sin gate" — falso positivo
# que hace que el mapa deje de mirarse, que es peor que no tenerlo (M97). Se leen de acá.
# Rutas SIN gate que están así A PROPÓSITO, con el motivo. Declararlas acá deja la lista de
# "sin gate" como una ALARMA de verdad: si aparece una nueva, es que alguien abrió algo.
# Verificadas una por una el 26-jul.
PUBLICAS_DELIBERADAS = {
    '/healthz': 'health check de Render · no devuelve datos',
    '/manifest.json': 'PWA · metadatos de la app',
    '/sw.js': 'PWA · service worker',
    '/planta-app.js': 'código JS de la app, sin datos (los datos vienen de APIs con login)',
    '/planta-core.js': 'código JS de la app, sin datos',
    '/reportar': 'formulario de reporte ANÓNIMO de empleados (bienestar) · anónimo por diseño',
    '/contabilidad': 'pantalla de LOGIN del módulo contable (tiene su propia sesión)',
}

GATES_POR_PREFIJO = [
    ('/diag/', 'ADMIN', 'before_request `_gate_diagnosticos` (index.py) · 404 al que no es admin'),
    ('/portal', 'PORTAL B2B', 'sesión propia de cliente externo (`portal_cliente_id`)'),
]


def _fuentes():
    """Mapa endpoint→código fuente de su función, leyendo los blueprints con AST."""
    src_por_funcion = {}
    bdir = os.path.join(RAIZ, 'api', 'blueprints')
    archivos = [os.path.join(bdir, f) for f in os.listdir(bdir) if f.endswith('.py')]
    archivos.append(os.path.join(RAIZ, 'api', 'index.py'))
    for path in archivos:
        try:
            src = open(path, encoding='utf-8').read()
            arbol = ast.parse(src)
        except Exception:
            continue
        lineas = src.splitlines()
        for n in ast.walk(arbol):
            if isinstance(n, ast.FunctionDef):
                cuerpo = '\n'.join(lineas[n.lineno - 1:(n.end_lineno or n.lineno)])
                src_por_funcion[n.name] = (os.path.basename(path), cuerpo)
    return src_por_funcion


def _detectar(cuerpo):
    for patron, etiqueta, quien in GATES:
        if re.search(patron, cuerpo):
            return etiqueta, quien
    return '?', 'no pude detectarlo · revisar a mano'


def main():
    from index import app
    fuentes = _fuentes()
    filas = []
    for regla in app.url_map.iter_rules():
        ruta = str(regla.rule)
        if ruta.startswith('/static'):
            continue
        metodos = sorted(m for m in regla.methods if m not in ('HEAD', 'OPTIONS'))
        nombre = regla.endpoint.split('.')[-1]
        archivo, cuerpo = fuentes.get(nombre, ('?', ''))
        _pref = next((g for g in GATES_POR_PREFIJO if ruta.startswith(g[0])), None)
        if ruta in PUBLICAS_DELIBERADAS:
            etiqueta, quien = 'PÚBLICA', PUBLICAS_DELIBERADAS[ruta]
        elif any(ruta.startswith(p) for p in PUBLICAS):
            etiqueta, quien = 'PÚBLICA', 'sin sesión (a propósito)'
        elif _pref:
            etiqueta, quien = _pref[1], _pref[2]
        else:
            etiqueta, quien = _detectar(cuerpo) if cuerpo else ('?', 'no encontré su función')
            if etiqueta == '?':
                # Sin gate propio: lo que decide es el hook global `require_auth_for_api`
                # (auth.py), que cubre SOLO las rutas que empiezan con /api/. Una ruta
                # fuera de ese prefijo y sin gate propio está ABIERTA A INTERNET — así
                # estuvieron las 18 rutas /diag/* sirviendo las fórmulas maestras (M95).
                if ruta.startswith('/api/'):
                    etiqueta, quien = 'AUTENTICADO', 'hook global de login (auth.py)'
                else:
                    etiqueta, quien = '⚠ SIN GATE', 'NADIE la protege · revisar YA'
        muta = bool({'POST', 'PUT', 'PATCH', 'DELETE'} & set(metodos))
        filas.append({'ruta': ruta, 'metodos': ','.join(metodos), 'gate': etiqueta,
                      'quien': quien, 'archivo': archivo, 'muta': muta})
    filas.sort(key=lambda f: (f['archivo'], f['ruta']))

    por_gate = defaultdict(int)
    for f in filas:
        por_gate[f['gate']] += 1
    # Lo que más importa de un mapa de permisos: qué MUTA y no sabemos quién puede.
    sospechosas = [f for f in filas if f['muta'] and f['gate'] in ('AUTENTICADO', '?')]
    abiertas = [f for f in filas if f['gate'] == '⚠ SIN GATE']

    out = [
        '# Mapa de permisos · EOS',
        '',
        '> **GENERADO** por `python scripts/generar_mapa_permisos.py` · no editar a mano.',
        '> Se lee del `url_map` real de Flask, así que no puede quedar desactualizado en silencio.',
        '',
        '## Resumen',
        '',
        '| Gate | Rutas | Quién entra |',
        '|---|---:|---|',
    ]
    leyenda = {e: q for _p, e, q in GATES}
    leyenda['PÚBLICA'] = 'sin sesión (a propósito)'
    leyenda['?'] = 'no detectado · revisar a mano'
    leyenda['⚠ SIN GATE'] = 'NADIE la protege · fuera de /api/ y sin gate propio'
    for gate, n in sorted(por_gate.items(), key=lambda x: -x[1]):
        out.append('| `%s` | %d | %s |' % (gate, n, leyenda.get(gate, '')))
    out += [
        '',
        '## 🚨 Rutas SIN NINGÚN gate (fuera de /api/)',
        '',
        'El hook global de login cubre sólo `/api/`. Una ruta fuera de ese prefijo sin gate propio',
        'la puede abrir cualquiera desde internet. Así estuvieron las 18 rutas `/diag/*` sirviendo',
        'las fórmulas maestras hasta el 25-jul. **Esta lista debería estar vacía o ser sólo páginas',
        'públicas a propósito.**',
        '',
        '| Ruta | Métodos | Archivo |',
        '|---|---|---|',
    ] + ['| `%s` | %s | %s |' % (f['ruta'], f['metodos'], f['archivo']) for f in abiertas] + [
        '',
        '_%d rutas._' % len(abiertas),
        '',
        '## ⚠ Rutas que MUTAN y sólo piden estar logueado',
        '',
        'No todas son un problema (muchas son acciones que cualquier empleado hace), pero **acá es',
        'donde aparecen los agujeros**: el 25-jul se encontraron dos controles que parecían control',
        'y no lo eran. Si una de estas toca dinero, inventario o un registro regulado, necesita rol.',
        '',
        '| Ruta | Métodos | Archivo |',
        '|---|---|---|',
    ]
    for f in sospechosas:
        out.append('| `%s` | %s | %s |' % (f['ruta'], f['metodos'], f['archivo']))
    out += ['', '_%d rutas en esta lista._' % len(sospechosas), '', '## Todas las rutas', '',
            '| Ruta | Métodos | Gate | Archivo |', '|---|---|---|---|']
    for f in filas:
        out.append('| `%s` | %s | %s | %s |' % (f['ruta'], f['metodos'], f['gate'], f['archivo']))

    destino = os.path.join(RAIZ, 'MAPA_PERMISOS.md')
    with open(destino, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')
    print('MAPA_PERMISOS.md · %d rutas · %d mutan con gate débil · %d SIN GATE'
          % (len(filas), len(sospechosas), len(abiertas)))
    for gate, n in sorted(por_gate.items(), key=lambda x: -x[1]):
        print('   %-20s %4d' % (gate.encode('ascii','replace').decode(), n))


if __name__ == '__main__':
    main()
