# -*- coding: utf-8 -*-
"""El catalogo de estados de una OC tiene que incluir los que el codigo ESCRIBE · 19-ago.

Anoche reporte "27 ordenes en estado `Aprobada`, que no esta en ESTADOS_OC_VALIDOS y que
ningun codigo escribe hoy". La segunda mitad era falsa: SI lo escribe
`mkt_solicitar_pago_influencer` -- son las solicitudes de pago a creadores, cuya OC nace
'Aprobada' porque el acto de solicitar el pago ya es la decision.

Verificado de punta a punta: esa OC se paga bien (PATCH /pagar -> OC 'Pagada' y el pago
del creador 'Pagada'). O sea que el estado es real y funcional, y lo que estaba
desactualizado era el catalogo.

Este guard mide la INVARIANTE, no la lista: todo estado que el codigo escriba tiene que
estar declarado. Es la version sistematica de lo que encontre a mano en los pedidos (cinco
pantallas, tres vocabularios): un catalogo que no cubre lo que el sistema produce hace que
un registro legitimo se lea como huerfano.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _estados_escritos():
    base = os.path.join(RAIZ, "api", "blueprints")
    vistos = {}
    for f in sorted(os.listdir(base)):
        if not f.endswith(".py"):
            continue
        s = io.open(os.path.join(base, f), encoding="utf-8").read()
        sc = "\n".join(l for l in s.splitlines() if not l.strip().startswith("#"))
        for m in re.finditer(r"UPDATE\s+ordenes_compra\s+SET\s+(.{0,300}?)(?:WHERE|$)",
                             sc, re.I | re.S):
            for mm in re.finditer(r"\bestado\s*=\s*'([^']+)'", m.group(1), re.I):
                vistos.setdefault(mm.group(1), set()).add(f)
        for m in re.finditer(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+ordenes_compra\b"
                             r"(.{0,700}?)(?:\"\"\"|'''|\n\s*\))", sc, re.I | re.S):
            for mm in re.finditer(r"\('estado',\s*'([^']+)'\)", m.group(1)):
                vistos.setdefault(mm.group(1), set()).add(f)
    return vistos


def test_todo_estado_que_el_codigo_escribe_esta_declarado():
    from api.blueprints.compras import ESTADOS_OC_VALIDOS, ESTADOS_OC_LEGACY
    conocidos = {x.lower() for x in ESTADOS_OC_VALIDOS} | {x.lower() for x in ESTADOS_OC_LEGACY}
    escritos = _estados_escritos()
    assert escritos, ("no se encontro ningun estado escrito · el barrido dejo de medir "
                      "y pasaria verde por omision (M210)")
    faltan = {v: sorted(d) for v, d in escritos.items() if v.lower() not in conocidos}
    assert not faltan, (
        "hay estados de OC que el codigo escribe y el catalogo no declara · una orden "
        "real termina figurando como huerfana: %s · declarados: %s"
        % (faltan, list(ESTADOS_OC_VALIDOS)))


def test_el_catalogo_no_declara_estados_FANTASMA():
    """El otro lado: un estado declarado que nadie escribe ni lee es letra muerta.

    No falla -- se DECLARA en el mensaje, porque puede ser un estado legitimo que
    todavia no se usa (M124: lo que se excluye se dice, no se esconde).
    """
    from api.blueprints.compras import ESTADOS_OC_VALIDOS
    escritos = {v.lower() for v in _estados_escritos()}
    base = os.path.join(RAIZ, "api", "blueprints")
    leidos = set()
    for f in sorted(os.listdir(base)):
        if not f.endswith(".py"):
            continue
        s = io.open(os.path.join(base, f), encoding="utf-8").read()
        for e in ESTADOS_OC_VALIDOS:
            if ("'%s'" % e) in s:
                leidos.add(e.lower())
    sin_uso = [e for e in ESTADOS_OC_VALIDOS
               if e.lower() not in escritos and e.lower() not in leidos]
    assert not sin_uso, (
        "estados declarados que ni se escriben ni se leen en ninguna parte: %s" % sin_uso)
