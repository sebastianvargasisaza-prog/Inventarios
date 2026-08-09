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


# El escaneo del CODIGO, cacheado por la FIRMA de los archivos que lee.
#
# Se cachea porque el codigo no puede cambiar dentro de un proceso vivo: un despliegue reinicia
# los workers. Y se cachea SOLO esta mitad -- la otra, quien tiene la cuenta bloqueada, sale de la
# base y se vuelve a leer en cada carga, porque si se cacheara la pantalla mostraria con permisos
# a alguien que se fue (M9).
#
# La firma incluye tamano y fecha de cada archivo: si alguno cambia, el cache se descarta solo. No
# hay forma de que quede vieja sin que se note, que es justo lo que esta pantalla promete.
_CACHE_ESCANEO = {'firma': None, 'rutas': None}


def _firma_fuentes():
    """(archivo, tamano, fecha) de todo lo que el escaneo LEE."""
    partes = []
    try:
        for fn in sorted(os.listdir(BLUEPRINTS)):
            if not fn.endswith('.py'):
                continue
            st = os.stat(os.path.join(BLUEPRINTS, fn))
            partes.append((fn, st.st_size, int(st.st_mtime)))
        st = os.stat(os.path.join(RAIZ, 'auth.py'))
        partes.append(('auth.py', st.st_size, int(st.st_mtime)))
    except Exception:
        return None            # no se pudo firmar -> no se cachea (mejor lento que viejo)
    return tuple(partes)


def _copia_rutas(rutas):
    """Copia de lo cacheado · compartir la referencia es que el primer caller se la pise a todos
    los demas (M167)."""
    return [{'modulo': r['modulo'], 'ruta': r['ruta'], 'metodos': list(r['metodos']),
             'funcion': r['funcion'], 'gate': r['gate'], 'resuelto': r['resuelto'],
             'escribe': r['escribe'],
             'quienes': (list(r['quienes']) if r['quienes'] is not None else None)}
            for r in rutas]


def construir():
    """Recorre los blueprints y devuelve la matriz + los hallazgos."""
    sets = _conjuntos()
    PUBLICAS = _publicas()
    todos_login = sets['TODOS_CON_LOGIN']
    inactivos = _desactivados()
    _firma = _firma_fuentes()
    if _firma is not None and _CACHE_ESCANEO['firma'] == _firma \
            and _CACHE_ESCANEO['rutas'] is not None:
        rutas = _copia_rutas(_CACHE_ESCANEO['rutas'])
        return _armar(rutas, sets, inactivos)
    rutas = []
    for fn, src in _fuentes():
        try:
            arbol = ast.parse(src)
        except Exception:
            continue
        # ⚠ Las líneas se parten UNA vez por archivo. `ast.get_source_segment` vuelve a partir el
        # archivo ENTERO en cada llamada, y acá se llama una vez por ruta: sobre `admin.py`
        # (28.000 líneas) son ~700 pasadas sobre 1,5 MB. Medido: 23 de los 26 segundos que tardaba
        # la matriz se iban ahí, y esos 26 segundos en producción se comen un worker de tres y
        # pasan del timeout, así que la pantalla no abría nunca (M43).
        _lineas = src.splitlines()
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
            # Se corta por número de línea. Devuelve las líneas COMPLETAS (a lo sumo la
            # sangría inicial de más), y lo único que se hace con el cuerpo es buscarle
            # patrones con expresiones regulares: el resultado es idéntico, y hay un test
            # que compara la matriz entera contra la del camino anterior.
            cuerpo = '\n'.join(_lineas[n.lineno - 1:(n.end_lineno or n.lineno)])
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

    if _firma is not None:
        _CACHE_ESCANEO['firma'], _CACHE_ESCANEO['rutas'] = _firma, _copia_rutas(rutas)
    return _armar(rutas, sets, inactivos)


def _armar(rutas, sets, inactivos):
    """La vista por PERSONA y los hallazgos · se rehace en cada carga, no se cachea."""
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
