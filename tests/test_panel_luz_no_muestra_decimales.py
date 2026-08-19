# -*- coding: utf-8 -*-
"""El panel de Luz mostraba "hace 61.45688301557675 días" · 19-ago.

Abriendo Espagiría en producción, la alerta de lotes en cuarentena decía:

    🟡 10 lotes en cuarentena hace >7 días
       073526 · 61.45688301557675
       030658826 · 61.45688301557675

`julianday(a) - julianday(b)` devuelve un FLOAT y la pantalla lo pintaba crudo. No
rompe nada, pero es exactamente lo que hace que un tablero se vea sin terminar -- y
en una pantalla que alguien usa todos los días eso enseña a no mirarla.

El arreglo va en `_fmt_many`, el serializador que comparten las 24 alertas del panel,
no en cada consulta: 24 `CAST` copiados divergen el día que alguien agregue la 25 (M3).

De paso, el mismo cálculo mezclaba relojes: `julianday('now')` es UTC y las fechas del
kardex están ancladas a Colombia, así que el elapsed venía inflado 5 horas (M24 en su
variante de DURACIÓN -- un `now() - inicio` con bases distintas, no un "hoy").
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


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id='ZLUZ01'")
        cn.commit()
    finally:
        cn.close()


def test_ninguna_alerta_muestra_un_numero_con_decimales(app, db_clean):
    """Se mide sobre la RESPUESTA, no sobre el SQL: es lo que la pantalla pinta."""
    _limpiar()
    cn = _cn()
    try:
        # un lote viejo en cuarentena · dispara la alerta que tenía el defecto
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador) VALUES ('ZLUZ01','ZLUZ INCI',"
                   "'Entrada',5000,'ZLUZ-L1', date('now','-5 hours','-61 days'),"
                   "'CUARENTENA','guard')")
        cn.commit()
    finally:
        cn.close()
    try:
        d = _cli(app).get('/api/espagiria/quick-actions').get_json() or {}
        secciones = d.get('secciones') or []
        assert secciones, ("el panel no devolvió alertas · el guard no midió nada",
                           sorted(d.keys()))
        feos = []
        vistos = 0
        for sec in secciones:
            for it in (sec.get('items') or []):
                for k, v in it.items():
                    if k == 'dias' or k.startswith('dias_'):
                        vistos += 1
                        if isinstance(v, float) and v != int(v):
                            feos.append('%s.%s=%r' % (sec.get('id'), k, v))
        assert vistos >= 1, (
            "ninguna alerta trajo un campo de días · el guard dejó de medir (M210)")
        assert not feos, (
            "el panel muestra días con decimales · se ve como 'hace "
            "61.45688301557675 días': %s" % feos)
    finally:
        _limpiar()


def test_los_dias_siguen_siendo_el_numero_correcto(app, db_clean):
    """Redondear no puede inventar ni perder días (M96)."""
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "lote, fecha, estado_lote, operador) VALUES ('ZLUZ01','ZLUZ INCI',"
                   "'Entrada',5000,'ZLUZ-L2', date('now','-5 hours','-30 days'),"
                   "'CUARENTENA','guard')")
        cn.commit()
    finally:
        cn.close()
    try:
        d = _cli(app).get('/api/espagiria/quick-actions').get_json() or {}
        mios = [it for sec in (d.get('secciones') or [])
                for it in (sec.get('items') or [])
                if it.get('lote') == 'ZLUZ-L2']
        assert mios, "el lote sembrado no aparece en ninguna alerta"
        dias = mios[0].get('dias')
        assert dias is not None, mios[0]
        assert 29 <= int(dias) <= 31, (
            "los días en cuarentena dejaron de ser correctos · con el reloj mal "
            "anclado el elapsed se infla", dias)
    finally:
        _limpiar()
