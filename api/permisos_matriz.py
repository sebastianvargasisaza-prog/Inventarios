# -*- coding: utf-8 -*-
"""Matriz de permisos GENERADA del código, nunca escrita a mano.

Sebastián 7-ago: *"dejemos esta tarea pendiente revisar qué puede hacer cada usuario"*.

Una matriz mantenida a mano queda vieja el día que alguien agrega un endpoint, y a partir de ahí
miente con cara de documento (M122: una lista negra escrita a mano se pudre). Ésta se calcula
leyendo el código en el momento en que se pide, así que no puede quedar desactualizada.

**Qué NO hace, a propósito:** no adivina. Cuando no puede resolver el guard de una ruta lo dice
(`resuelto: false`) en vez de suponer que está abierta o cerrada. Un cero inventado acá sería lo
peor de los dos mundos: una ruta desprotegida reportada como protegida (M100).

Cómo resuelve el guard, en orden:
  1. el guard nombrado (`_require_*`, `_auth()`, `_autorizados_*`) → se resuelve su conjunto;
  2. la comparación directa contra un conjunto de `config` (`not in ADMIN_USERS`, ...);
  3. sólo `'compras_user' not in session` → cualquiera con login;
  4. nada de lo anterior → SIN GATE (y eso es un hallazgo, no un dato neutro).
"""
import ast
import io
import os
import re

RAIZ = os.path.dirname(os.path.abspath(__file__))
BLUEPRINTS = os.path.join(RAIZ, 'blueprints')

# Conjuntos de config que un guard puede nombrar. Se resuelven EN VIVO desde config.py para que
# agregar a alguien a un rol se refleje sin tocar este archivo.
_SETS = ('ADMIN_USERS', 'COMPRAS_ACCESS', 'CONTADORA_USERS', 'CALIDAD_USERS',
         'ASEGURAMIENTO_USERS', 'PLANTA_USERS', 'RRHH_USERS', 'CLIENTES_ACCESS',
         'TECNICA_USERS', 'MARKETING_USERS', 'FINANZAS_ACCESS', 'ANIMUS_ACCESS',
         'ESPAGIRIA_ACCESS', 'OC_AUTORIZA_USERS')


def _conjuntos():
    import config as _cfg
    out = {}
    for n in _SETS:
        v = getattr(_cfg, n, None)
        if isinstance(v, (set, frozenset)):
            out[n] = set(v)
    out['TODOS_CON_LOGIN'] = set(getattr(_cfg, 'COMPRAS_USERS', {}) or {})
    return out


def _fuentes():
    for fn in sorted(os.listdir(BLUEPRINTS)):
        if fn.endswith('.py') and not fn.startswith('_'):
            yield fn, io.open(os.path.join(BLUEPRINTS, fn), encoding='utf-8').read()


def _sin_comentarios(txt):
    """Los comentarios explican por qué se quitó un guard · si se leen, el detector encuentra la
    palabra y cree que el guard está (M154, que mordió cuatro veces en un solo día)."""
    txt = re.sub(r'#[^\n]*', '', txt)
    return re.sub(r'"""(?:.|\n)*?"""', '', txt)


def _resolver_guard(cuerpo, sets):
    """Devuelve (quienes:set|None, etiqueta:str, resuelto:bool)."""
    c = _sin_comentarios(cuerpo)
    todos = sets['TODOS_CON_LOGIN']

    # 1 · guard nombrado, resuelto contra lo que ese guard exige de verdad
    nombrados = {
        '_require_compras_write': ('COMPRAS_ACCESS', 'ADMIN_USERS'),
        '_require_authorize_oc': ('OC_AUTORIZA_USERS', 'ADMIN_USERS'),
        '_require_qc': ('CALIDAD_USERS', 'ADMIN_USERS'),
        '_require_brd_ejecutor': ('PLANTA_USERS', 'CALIDAD_USERS', 'ADMIN_USERS',
                                  'ASEGURAMIENTO_USERS', 'TECNICA_USERS'),
        '_autorizados_escritura': ('ASEGURAMIENTO_USERS', 'CALIDAD_USERS', 'ADMIN_USERS'),
        '_autorizados_equipos': ('CALIDAD_USERS', 'ASEGURAMIENTO_USERS', 'ADMIN_USERS'),
        '_require_admin': ('ADMIN_USERS',),
        '_require_planta_write': (),          # cualquiera con login · decision documentada (M39)
        '_require_login': (),                 # cualquiera con login
        '_require_qa_or_admin': ('CALIDAD_USERS', 'ASEGURAMIENTO_USERS', 'ADMIN_USERS'),
    }
    for g, comps in nombrados.items():
        if g + '(' in c:
            if not comps:                     # el guard sólo exige sesión
                return set(todos), g + ' (cualquiera con login)', True
            quienes = set()
            for x in comps:
                quienes |= sets.get(x, set())
            return quienes, g, True

    # 2 · comparación directa contra conjuntos de config
    usados = [n for n in sets if n != 'TODOS_CON_LOGIN' and re.search(r'\b' + n + r'\b', c)]
    if usados:
        quienes = set()
        for n in usados:
            quienes |= sets[n]
        # `puede_archivar` es por EXCLUSIÓN: todos menos los operarios
        if 'puede_archivar' in c:
            quienes |= (todos - sets.get('PLANTA_USERS', set()))
        return quienes, ' | '.join(sorted(usados)), True
    if 'puede_archivar' in c:
        return todos - sets.get('PLANTA_USERS', set()), 'puede_archivar (todos menos operarios)', True

    # 3 · sólo pide sesión
    # ⚠ Las DOS formas de comilla: el detector sólo miraba `'compras_user'` y por eso reportó
    # como abiertas páginas que sí gatean con `session.get("compras_user")` · un detector que
    # depende del estilo de comillas de quien escribió la línea no mide nada (M122).
    if re.search(r'''["']compras_user["']\s+not\s+in\s+session|session\.get\(["']compras_user["']''', c) or '_auth(' in c:
        return set(todos), 'cualquiera con login', True

    # 3b · tiene un guard PROPIO que este detector no sabe resolver.
    # ⚠ No es lo mismo que no tener gate, y confundirlos fue el falso positivo que casi me hace
    # reportar 82 páginas de admin como abiertas: todas llamaban a `_require_admin()`. Se declara
    # "hay gate, no sé a quién deja pasar" en vez de inventar cualquiera de las dos cosas (M100).
    _otro = re.search(r'(_require_[a-z_]+|_autorizados_[a-z_]+)\s*\(', c)
    if _otro:
        return None, 'gate propio · %s (conjunto sin resolver)' % _otro.group(1), True

    # 4 · nada propio · lo cubre (o no) el hook global, que decide el llamador
    return None, '', False


def _publicas():
    """Las rutas exentas del login global · se LEEN de auth.py, no se copian: una lista
    duplicada se queda vieja el dia que alguien exime una ruta nueva (M99)."""
    import re as _re
    try:
        src = io.open(os.path.join(RAIZ, 'auth.py'), encoding='utf-8').read()
        i = src.find('PUBLIC_API = {')
        if i < 0:
            return set()
        j = src.find('}', i)
        return set(_re.findall(r"'([^']+)'", src[i:j]))
    except Exception:
        return set()


def _desactivados():
    """Quien tiene la cuenta bloqueada en la BD · si no, la matriz muestra a alguien que se fue
    con permisos de escritura en 29 modulos, que es justo la objecion que uno no quiere en una
    auditoria (config.py conserva su usuario a proposito: Part 11 no borra personas)."""
    try:
        from database import db_connect
        con = db_connect(timeout=10)
        try:
            filas = con.execute(
                "SELECT username FROM users_passwords WHERE COALESCE(activo,1)=0").fetchall()
            return {(r[0] or '').strip().lower() for r in filas}
        finally:
            con.close()
    except Exception:
        return set()


def construir():
    """Recorre los blueprints y devuelve la matriz + los hallazgos."""
    sets = _conjuntos()
    PUBLICAS = _publicas()
    todos_login = sets['TODOS_CON_LOGIN']
    inactivos = _desactivados()
    rutas = []
    for fn, src in _fuentes():
        try:
            arbol = ast.parse(src)
        except Exception:
            continue
        for n in ast.walk(arbol):
            if not isinstance(n, ast.FunctionDef):
                continue
            reglas = []
            for d in n.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr == 'route' and d.args
                        and isinstance(d.args[0], ast.Constant)):
                    mets = ['GET']
                    for kw in d.keywords:
                        if kw.arg == 'methods':
                            try:
                                mets = [x.value for x in kw.value.elts]
                            except Exception:
                                pass
                    reglas.append((d.args[0].value, [m.upper() for m in mets]))
            if not reglas:
                continue
            cuerpo = ast.get_source_segment(src, n) or ''
            quienes, etiqueta, resuelto = _resolver_guard(cuerpo, sets)
            muta = bool(re.search(r'\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b',
                                  _sin_comentarios(cuerpo), re.I))
            for ruta, mets in reglas:
                escribe = muta or bool({'POST', 'PUT', 'PATCH', 'DELETE'} & set(mets))
                _q, _et, _res = quienes, etiqueta, resuelto
                if not _res:
                    # ⚠ Sin guard PROPIO no significa "abierta": todo lo que cuelga de /api/ pasa
                    # por el hook global de login (`require_auth_for_api`). Etiquetarlas a todas
                    # como SIN GATE daba 667 falsos positivos, y un detector que grita de más deja
                    # de mirarse justo el día que hay uno de verdad (M122).
                    #
                    # Lo que SÍ es un hallazgo es una ruta FUERA de /api/ sin gate propio: ésas no
                    # las cubre nadie. Es exactamente por donde `/diag/*` quedó abierto a internet
                    # (M95), y es la razón por la que este generador existe.
                    if ruta in PUBLICAS:
                        _q, _et, _res = None, 'PUBLICA (exenta del login)', True
                    elif ruta.startswith('/api/'):
                        _q, _et, _res = set(todos_login), 'solo login (hook global)', True
                    else:
                        _q, _et, _res = None, 'SIN GATE PROPIO Y FUERA DE /api/', False
                rutas.append({
                    'modulo': fn[:-3], 'ruta': ruta, 'metodos': mets, 'funcion': n.name,
                    'gate': _et, 'resuelto': _res, 'escribe': escribe,
                    'quienes': sorted(_q) if _q is not None else None,
                })

    # ── Vista por PERSONA: qué módulos toca y dónde puede escribir ────────────────────────
    por_usuario = {}
    for u in sorted(sets['TODOS_CON_LOGIN']):
        mods = {}
        for r in rutas:
            if r['quienes'] is None or u not in r['quienes']:
                continue
            m = mods.setdefault(r['modulo'], {'lee': 0, 'escribe': 0})
            m['escribe' if r['escribe'] else 'lee'] += 1
        por_usuario[u] = {
            'modulos': dict(sorted(mods.items())),
            'total_escribe': sum(v['escribe'] for v in mods.values()),
            'cuenta_activa': u.lower() not in inactivos,
        }

    sin_gate = [r for r in rutas if not r['resuelto']]
    return {
        'ok': True,
        'total_rutas': len(rutas),
        'roles': {k: sorted(v) for k, v in sets.items()},
        'por_usuario': por_usuario,
        'rutas': rutas,
        # Lo que el generador NO pudo resolver se DECLARA · una ruta sin gate reconocido puede
        # estar abierta o tener un guard que este detector no conoce, y confundir las dos cosas
        # es peor que no medir (M100).
        'usuarios_desactivados': sorted(inactivos),
        'sin_gate_reconocido': sorted(
            [{'modulo': r['modulo'], 'ruta': r['ruta'], 'metodos': r['metodos'],
              'escribe': r['escribe'], 'funcion': r['funcion']} for r in sin_gate],
            key=lambda x: (not x['escribe'], x['modulo'], x['ruta'])),
        'aviso': ('La matriz se genera leyendo el código en este momento: no puede quedar vieja. '
                  'Lo que no se pudo resolver sale en `sin_gate_reconocido` en vez de suponerse.'),
    }
