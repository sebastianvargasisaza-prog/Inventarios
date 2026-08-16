# -*- coding: utf-8 -*-
"""Ninguna pantalla ni GET de API puede devolver 500.

8-ago · barrido de las 912 rutas GET sin parámetros. Aparecieron DOS que reventaban siempre, y
ninguna de las dos la cubría un test:

  · `/api/planta/plan-semanal-v2` -- `pp.COALESCE(estado,...)`: el alias de la tabla quedó pegado
    al nombre de la FUNCIÓN. Error de sintaxis en los dos motores, o sea que ese endpoint no
    funcionó nunca desde que se escribió esa línea.
  · `/api/admin/mps-proveedores-status` -- `r['prov']` cuando el dict se había construido con la
    clave `'proveedor'`. KeyError en cada llamada.

Las dos son de la familia más barata de cazar y la más cara de no ver: **no hay que entender el
dominio, sólo hay que ABRIR la ruta**. Un 500 permanente se vive como "esa pantalla no carga" y
nadie lo reporta como bug.

Corre sobre el backend activo; en modo PostgreSQL (`guardian.sh --pg`) caza además lo que SQLite
tolera y producción no: GROUP BY incompleto, CAST sobre texto, `""` como identificador.

⚠ Las excepciones se ENUMERAN con su motivo (M122): una lista negra vaga se pudre y el guard deja
de mirarse. Si una ruta nueva aparece acá, la pregunta es por qué contesta 500, no cómo excluirla.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

# Motivo por ruta · un 500 DELIBERADO es un contrato, y se declara.
#
# 16-ago: quedó VACÍA. `/api/programacion/debug-calendar` daba 500 permanente desde que se
# retiró Google Calendar, y eso no es un fallo: es una integración que ya no existe. Ahora
# contesta 200 diciéndolo, igual que su hermano `debug-calendario` -- dos endpoints que
# responden distinto a la MISMA causa se contradicen (M161/M211).
#
# ⚠ Lo que NO cambió, y es lo que importa: `_fetch_calendar_events` sigue devolviendo
# `error` a propósito. Los consumidores DESTRUCTIVOS (el espejo con force_mirror) hacen
# early-return con ese error; si la fuente devolviera vacío-sin-error, el sincronizador
# leería "no hay eventos" y BORRARÍA producción (M79 · casi se pierde el plan entero).
# El diagnóstico dejó de propagar el 500; la fuente sigue declarando el error.
ESPERAN_500 = {}

# Prefijos que no son pantallas de la app
SALTAR = ('/static', '/diag')


def _rutas(app):
    out = []
    for r in app.url_map.iter_rules():
        if 'GET' not in (r.methods or set()) or r.arguments:
            continue
        u = str(r.rule)
        if u.startswith(SALTAR):
            continue
        out.append(u)
    return sorted(set(out))


def test_ninguna_ruta_GET_devuelve_500(app, admin_client):
    rotas = []
    for u in _rutas(app):
        try:
            r = admin_client.get(u)
            code = r.status_code
        except Exception as e:
            rotas.append('%s reventó con %s: %s' % (u, type(e).__name__, str(e)[:120]))
            continue
        if code >= 500 and u not in ESPERAN_500:
            rotas.append('%s devolvió %d · %s'
                         % (u, code, r.data[:150].decode('utf-8', 'replace')))
    assert not rotas, 'rutas que revientan:\n' + '\n'.join(rotas)


def test_las_excepciones_declaradas_SIGUEN_siendo_ciertas(app, admin_client):
    """Una excepción que ya no aplica es una ruta que dejó de vigilarse en silencio."""
    quedaron = []
    for u, motivo in ESPERAN_500.items():
        r = admin_client.get(u)
        if r.status_code < 500:
            quedaron.append('%s ya NO da 500 (%s) · sacala de ESPERAN_500' % (u, motivo))
    assert not quedaron, quedaron


def test_ningun_ALIAS_pegado_a_una_FUNCION_sql(app):
    """`pp.COALESCE(...)` es el alias de la tabla pegado al nombre de la función.

    No falla en un motor y anda en el otro: es sintaxis inválida en los DOS, así que la consulta
    nunca corrió. Se busca el patrón en todo el repo porque estas cosas se copian (M45).
    """
    import re
    FUNCS = ('COALESCE', 'UPPER', 'LOWER', 'TRIM', 'SUM', 'MAX', 'MIN', 'COUNT', 'SUBSTR',
             'CAST', 'ROUND', 'LENGTH', 'ABS', 'IFNULL', 'NULLIF', 'GROUP_CONCAT')
    pat = re.compile(r'\b[a-z_][a-z0-9_]{0,4}\.(' + '|'.join(FUNCS) + r')\s*\(')
    malos = []
    base = os.path.join(RAIZ, 'api')
    for raiz, _d, archivos in os.walk(base):
        if '__pycache__' in raiz:
            continue
        for a in archivos:
            if not a.endswith('.py'):
                continue
            ruta = os.path.join(raiz, a)
            with open(ruta, encoding='utf-8') as fh:
                for n, linea in enumerate(fh, 1):
                    if pat.search(linea):
                        malos.append('%s:%d  %s' % (a, n, linea.strip()[:100]))
    assert not malos, 'alias pegado al nombre de una función SQL:\n' + '\n'.join(malos)


def test_ningun_GET_crea_PRODUCCION(app, admin_client):
    """Abrir una pantalla no puede meter lotes en el calendario.

    Lo encontró este mismo barrido: `/api/plan/recuperar-semana-19may2026` -- una recuperación
    puntual de un incidente de mayo, con las cuatro producciones escritas a mano en el código --
    aceptaba GET a propósito (para poder dispararla desde el navegador) y su idempotencia sólo
    miraba lotes no cancelados ni completados. Con aquellos cuatro ya completados, **volvía a
    crear cuatro producciones fechadas en mayo, marcadas como Fijas**, que ningún proceso
    automático limpia (regla #3). Bastaba abrir la URL.

    `produccion_programada` la leen 15 blueprints (calendario, necesidades, abastecimiento): una
    fila de más ahí no da error, cambia lo que se compra.
    """
    from database import get_db
    with app.app_context():
        antes = get_db().execute('SELECT COUNT(*) FROM produccion_programada').fetchone()[0]
    for u in _rutas(app):
        try:
            admin_client.get(u)
        except Exception:
            pass
    with app.app_context():
        despues = get_db().execute('SELECT COUNT(*) FROM produccion_programada').fetchone()[0]
    assert despues == antes, \
        'abrir las rutas GET creó %d producciones (antes %d, después %d)' % (
            despues - antes, antes, despues)
