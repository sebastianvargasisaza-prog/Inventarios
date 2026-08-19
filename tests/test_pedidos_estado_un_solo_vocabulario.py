# -*- coding: utf-8 -*-
"""Cinco pantallas contaban los pedidos con TRES vocabularios distintos · 19-ago.

El estado de un pedido tiene seis valores, y quien los produce es el desplegable de la
pantalla de Clientes:

    Confirmado · Produciendo · Listo · Despachado · Facturado · Cancelado

Y así los contaba cada tablero:

    CEO (kpis)              ('Confirmado', 'En preparacion')
    Espagiría               ('Pendiente', 'En produccion', 'Listo', 'En despacho')
    Centro de Mando         ('Pendiente', 'En produccion', 'Listo')
    CEO (por despachar)     ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
    Hub de salida           idem

De esas palabras, **'Pendiente', 'En produccion', 'En despacho', 'En preparacion',
'En Produccion' y 'Aprobado' no existen**: nadie las escribe nunca. Entonces un pedido
en `Confirmado` -el estado en el que NACE cada pedido- era invisible para Espagiría y
para el Centro de Mando, y uno en `Produciendo` no lo contaba **ninguna** de las cinco.

Es la misma familia que el resto de la noche: un criterio que no corresponde a nada que
el sistema produzca, sirviendo el número más tranquilizador. Y la firma vuelve a ser la
asimetría entre hermanos (M150): cinco sitios contando el mismo hecho, cinco listas.

El arreglo es UNA definición en el dueño de la tabla y cinco consumidores que la piden
(M1/M3) -- cinco listas copiadas divergen el día que alguien agregue un estado.
"""
import io
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM pedidos WHERE numero LIKE 'ZPED-%'")
        cn.commit()
    finally:
        cn.close()


def _sembrar(numero, estado):
    cn = _cn()
    try:
        cn.execute("INSERT INTO pedidos (numero, cliente_id, fecha, estado, empresa, "
                   "valor_total, creado_por) VALUES (?,?,?,?,?,?,?)",
                   (numero, 1, '2020-01-01', estado, 'ANIMUS', 500000.0, 'guard'))
        cn.commit()
    finally:
        cn.close()


def test_un_pedido_PRODUCIENDO_cuenta_como_activo_en_TODAS_las_pantallas(app, db_clean):
    """`Produciendo` es un estado REAL y no lo contaba ninguno de los cinco."""
    _limpiar()
    cli = _cli(app)

    def _medir():
        # el CEO lo publica bajo `animus`, no en la raíz · leer la llave equivocada
        # haría que el guard se saltee justo la pantalla que se está arreglando (M245)
        ceo = ((cli.get('/api/gerencia/kpis').get_json() or {})
               .get('animus') or {}).get('pedidos_activos')
        esp = (cli.get('/api/espagiria/dashboard').get_json() or {}).get('pedidos_activos')
        cen = ((cli.get('/api/centro/operaciones').get_json() or {})
               .get('comercial') or {}).get('pedidos_b2b_activos')
        return {'ceo': ceo, 'espagiria': esp, 'centro': cen}

    base = _medir()
    _sembrar('ZPED-1', 'Produciendo')
    try:
        despues = _medir()
        medidas = 0
        for k in ('ceo', 'espagiria', 'centro'):
            if base[k] is None or despues[k] is None:
                continue          # esa pantalla no publica el dato · se declara abajo
            medidas += 1
            assert int(despues[k]) == int(base[k]) + 1, (
                "un pedido en 'Produciendo' no se cuenta como activo en %s · el tablero "
                "filtra por un estado que nadie escribe" % k, base, despues)
        # Un guard que no puede leer lo que revisa pasa verde POR OMISIÓN (M210).
        assert medidas == 3, (
            "no se pudieron medir las tres pantallas (%d de 3) · si una dejó de "
            "publicar su contador, este guard dejó de vigilarla" % medidas, base)
    finally:
        _limpiar()


def test_un_pedido_CONFIRMADO_es_visible_donde_nace(app, db_clean):
    """Todo pedido nace `Confirmado`; dos tableros no lo contaban jamás."""
    _limpiar()
    cli = _cli(app)
    antes = (cli.get('/api/espagiria/dashboard').get_json() or {}).get('pedidos_activos')
    _sembrar('ZPED-2', 'Confirmado')
    try:
        ahora = (cli.get('/api/espagiria/dashboard').get_json() or {}).get('pedidos_activos')
        assert antes is not None and ahora is not None, (antes, ahora)
        assert int(ahora) == int(antes) + 1, (
            "un pedido recién creado (Confirmado) no aparece como activo en Espagiría",
            antes, ahora)
    finally:
        _limpiar()


def test_un_pedido_DESPACHADO_ya_no_esta_activo(app, db_clean):
    """El borde que impide que unificar la lista infle el número (M96)."""
    _limpiar()
    cli = _cli(app)
    antes = (cli.get('/api/espagiria/dashboard').get_json() or {}).get('pedidos_activos')
    _sembrar('ZPED-3', 'Despachado')
    try:
        ahora = (cli.get('/api/espagiria/dashboard').get_json() or {}).get('pedidos_activos')
        assert int(ahora) == int(antes), (
            "un pedido ya despachado sigue contando como activo", antes, ahora)
    finally:
        _limpiar()


def test_ninguna_pantalla_inventa_un_estado_de_pedido(app, db_clean):
    """La invariante vive en el CÓDIGO, así que se mide sobre el fuente (M227).

    Un barrido de datos no la ve: filtrar por un estado inexistente devuelve cero sin
    error, y el tablero se ve sano. Lo que hay que impedir es que alguien vuelva a
    ESCRIBIR una lista de estados de pedido a mano.
    """
    from api.blueprints.clientes import ESTADOS_PEDIDO_VALIDOS
    validos = {v.lower() for v in ESTADOS_PEDIDO_VALIDOS}
    base = os.path.join(RAIZ, "api", "blueprints")
    culpables = []
    medidos = 0
    for nombre in sorted(os.listdir(base)):
        if not nombre.endswith(".py"):
            continue
        src = io.open(os.path.join(base, nombre), encoding="utf-8").read()
        sin_com = "\n".join(l for l in src.splitlines()
                            if not l.strip().startswith("#"))
        # sólo consultas que filtran el estado de la tabla `pedidos`
        for m in re.finditer(r"FROM\s+pedidos\b(.{0,400}?)(?:\"\"\"|'''|$)",
                             sin_com, re.I | re.S):
            frag = m.group(1)
            for mm in re.finditer(r"\bp?\.?estado\s+IN\s*\(([^)]*)\)", frag, re.I):
                lits = re.findall(r"'([^']+)'", mm.group(1))
                if not lits:
                    continue          # parametrizado (?) = usa la lista canónica
                medidos += 1
                malos = [v for v in lits if v.lower() not in validos]
                if malos:
                    culpables.append("%s: %s" % (nombre, malos))
    assert not culpables, (
        "hay pantallas filtrando pedidos por estados que NADIE escribe · su cero se lee "
        "como 'no hay pedidos activos': %s · el vocabulario real es %s"
        % (culpables, list(ESTADOS_PEDIDO_VALIDOS)))
