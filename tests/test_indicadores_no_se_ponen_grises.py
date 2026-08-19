# -*- coding: utf-8 -*-
"""Los indicadores de Aseguramiento se ponían GRISES justo cuando todo estaba mal · 19-ago.

Sebastián pidió revisar a fondo Aseguramiento. El tablero mostraba arriba:

    🚨 Alertas críticas · Queja salud sin responder · QC-2026-0002
                        · Queja salud sin responder · QC-2026-0003
                        · Queja salud sin responder · QC-2026-0004

...y el indicador **"Quejas/PQR respondidas en SLA"** en **gris · sin dato**.

La causa es la misma en CUATRO indicadores: sólo miraban lo ya CERRADO.

    WHERE COALESCE(respondido_at,'') <> ''     <- sólo las YA respondidas

Con cero respondidas el denominador es cero, `ratio()` devuelve None y el semáforo queda
gris. **El peor escenario posible producía "sin dato" en vez de rojo** -- y un número que
nadie calculó se lee como *"no hay nada que hacer"*, que es lo contrario de la verdad
(M129/M154/M100).

La regla nueva, igual para los cuatro (`_pct_a_tiempo`, uno solo · M3):

    cerrado dentro del plazo   -> cumple
    cerrado fuera del plazo    -> incumple
    ABIERTO y ya vencido       -> incumple   <- lo que antes era invisible
    abierto y todavía en plazo -> no entra al denominador: no incumplió nada
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _ind(app, codigo):
    d = _cli(app).get('/api/aseguramiento/indicadores').get_json() or {}
    for x in (d.get('indicadores') or []):
        if x.get('codigo') == codigo:
            return x
    return None


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM quejas_clientes WHERE codigo LIKE 'ZQ-%'")
        cn.execute("DELETE FROM capa_acciones WHERE descripcion LIKE 'ZCAPA%'")
        cn.commit()
    finally:
        cn.close()


def test_una_queja_SIN_responder_y_vencida_pone_el_indicador_en_ROJO(app, db_clean):
    """Antes: cero respondidas -> denominador cero -> gris. El peor caso, invisible."""
    _limpiar()
    cn = _cn()
    try:
        # recibida hace 60 días y nunca respondida · el plazo es 15
        cn.execute("INSERT INTO quejas_clientes (codigo, fecha_recepcion, recibido_por, "
                   "cliente_nombre, descripcion) VALUES ('ZQ-1', "
                   "date('now','-5 hours','-60 days'), 'guard', 'ZCLIENTE','sin responder')")
        cn.commit()
    finally:
        cn.close()
    try:
        i = _ind(app, 'quejas_sla')
        assert i, "desapareció el indicador de quejas"
        assert i['valor'] is not None, (
            "el indicador sigue en GRIS con una queja vencida sin responder · el peor "
            "escenario no puede leerse como 'sin dato'")
        assert float(i['valor']) == 0.0, (
            "una queja vencida y sin responder tiene que contar como incumplida",
            i['valor'])
        assert i.get('semaforo') == 'rojo', i.get('semaforo')
    finally:
        _limpiar()


def test_una_queja_reciente_y_sin_responder_TODAVIA_no_incumple(app, db_clean):
    """El borde que impide que el arreglo invente incumplimientos (M96)."""
    _limpiar()
    cn = _cn()
    try:
        # recibida ayer · el plazo de 15 días no venció
        cn.execute("INSERT INTO quejas_clientes (codigo, fecha_recepcion, recibido_por, "
                   "cliente_nombre, descripcion) VALUES ('ZQ-2', "
                   "date('now','-5 hours','-1 days'), 'guard', 'ZCLIENTE','recien recibida')")
        cn.commit()
    finally:
        cn.close()
    try:
        i = _ind(app, 'quejas_sla')
        assert i and i['valor'] is None, (
            "una queja que todavía está EN PLAZO se contó como incumplida", i)
    finally:
        _limpiar()


def test_una_queja_respondida_a_tiempo_cuenta_como_cumplida(app, db_clean):
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO quejas_clientes (codigo, fecha_recepcion, recibido_por, "
                   "cliente_nombre, descripcion, respondido_at) VALUES ('ZQ-3', "
                   "date('now','-5 hours','-30 days'), 'guard', 'ZCLIENTE','ok', "
                   "date('now','-5 hours','-25 days'))")
        cn.commit()
    finally:
        cn.close()
    try:
        i = _ind(app, 'quejas_sla')
        assert i and float(i['valor'] or -1) == 100.0, (
            "una queja respondida dentro del plazo dejó de contar como cumplida", i)
    finally:
        _limpiar()


def test_una_CAPA_vencida_sin_ejecutar_tambien_cuenta(app, db_clean):
    """El plazo de una CAPA es su fecha de COMPROMISO, no un número de días."""
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO capa_acciones (nc_id, tipo, descripcion, estado, "
                   "fecha_compromiso) VALUES (0, 'correctiva', 'ZCAPA vencida', "
                   "'Pendiente', date('now','-5 hours','-40 days'))")
        cn.commit()
    finally:
        cn.close()
    try:
        i = _ind(app, 'capa_a_tiempo')
        assert i and i['valor'] is not None, (
            "una CAPA con el compromiso vencido y sin ejecutar deja el indicador en gris", i)
        assert float(i['valor']) == 0.0, i['valor']
    finally:
        _limpiar()


def test_ningun_indicador_de_A_TIEMPO_mira_solo_lo_cerrado(app, db_clean):
    """La razón vive en la medición, no en el código: sin esto vuelven a ponerse grises."""
    import ast
    import io
    import re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "aseguramiento.py")
    src = io.open(ruta, encoding="utf-8").read()
    lin = src.splitlines()
    cuerpo = None
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == '_indicadores_asg_valores':
            cuerpo = "\n".join(lin[n.lineno - 1:n.end_lineno])
    assert cuerpo, "no encontré el cálculo de indicadores"
    sin_com = "\n".join(l for l in cuerpo.splitlines() if not l.strip().startswith("#"))
    for cod in ('desv_a_tiempo', 'quejas_sla', 'capa_a_tiempo', 'cambios_invima_ok'):
        m = re.search(r"v\['%s'\]\s*=\s*(\w+)" % cod, sin_com)
        assert m, ("desapareció el indicador %s" % cod)
        assert m.group(1) == '_pct_a_tiempo', (
            "%s volvió a medir sólo lo cerrado · con cero cerrados queda GRIS, que es "
            "justo cuando todo está mal" % cod, m.group(1))
