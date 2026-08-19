# -*- coding: utf-8 -*-
"""El panel del CEO mostraba $0 para 22 pagos que sí tenían monto · 19-ago-2026.

Sebastián: *"revisá a fondo el CEO, mi panel propio, que tenga todo lo necesario para ir
viendo cómo sucede"*. Abriéndolo en producción:

    📣 PAGOS A CREADORES · $0 · 22 esperando
       Leidy Diana Hidalgo Perea   $0
       Monssa                       $0
       ...

Y en la respuesta del endpoint, cada fila traía **las dos cosas**:

    "monto": 0            <- lo que el panel leía
    "valor": 420000       <- lo que de verdad se debe

`_pagos_influencer_pendientes` devuelve el importe en `valor` (`COALESCE(pi.valor,0) valor`)
y nunca en `monto`, así que `x.get('monto')` daba None, el `or 0` lo volvía cero, y el CEO
veía que no hay plata pendiente. **Una llave supuesta no falla: se ve como que no hay nada
que pagar** (M94/M215), que es justo la conclusión contraria a la verdadera.

Los otros DOS consumidores del mismo helper leen `valor` bien. **La asimetría entre
hermanos era la firma del hallazgo** (M150): cuando tres sitios hacen lo mismo y uno da
cero, el que da cero casi nunca tiene razón.

Este guard mide la INVARIANTE (lo que el panel dice tiene que ser lo que se debe), no la
llave: si mañana el helper renombra el campo otra vez, esto falla igual.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

NOMBRE = "ZCEO CREADORA"
VALOR = 420000.0


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
        cn.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (NOMBRE,))
        cn.commit()
    finally:
        cn.close()


def _sembrar(n=2):
    _limpiar()
    cn = _cn()
    try:
        for i in range(n):
            # Fecha VIEJA a propósito: la cola del CEO ordena por antigüedad y muestra
            # las primeras 12, así que un pago sembrado "hoy" queda al final y el test
            # mediría el recorte en vez del cálculo (M207/M102 · el test controla su
            # universo).
            cn.execute(
                "INSERT INTO pagos_influencers (influencer_nombre, valor, fecha, estado, "
                "concepto, vence_pago_at) "
                "VALUES (?,?,'2020-01-01','Pendiente','REEL','2020-01-15')",
                (NOMBRE, VALOR))
        cn.commit()
    finally:
        cn.close()


def test_el_panel_del_CEO_muestra_lo_que_de_verdad_se_debe(app, db_clean):
    _sembrar(2)
    try:
        d = _cli(app).get('/api/gerencia/decisiones-ceo').get_json() or {}
        inf = d.get('influencers') or {}
        assert inf, ("el bloque de pagos a creadores no llegó", sorted(d.keys()))

        mios = [x for x in (inf.get('pendientes') or [])
                if x.get('influencer_nombre') == NOMBRE]
        assert len(mios) == 2, ("los pagos sembrados no aparecen en la cola del CEO",
                                len(mios))
        for x in mios:
            assert float(x.get('monto') or 0) == VALOR, (
                "la fila muestra $0 con un pago que sí tiene monto · el panel está leyendo "
                "una llave que el productor no manda", x.get('monto'), x.get('valor'))

        assert float(inf.get('monto') or 0) >= VALOR * 2, (
            "el total del bloque no suma lo que se debe", inf.get('monto'))
    finally:
        _limpiar()


def test_el_total_es_la_suma_de_lo_que_LISTA(app, db_clean):
    """El número de arriba no puede contradecir la lista de abajo (M161)."""
    _sembrar(3)
    try:
        inf = ((_cli(app).get('/api/gerencia/decisiones-ceo').get_json() or {})
               .get('influencers') or {})
        filas = inf.get('pendientes') or []
        assert filas, "el bloque llegó sin filas"
        # el detalle viene recortado a 12 · sólo se puede comparar si no se recortó
        if int(inf.get('n') or 0) <= len(filas):
            suma = round(sum(float(x.get('monto') or 0) for x in filas), 2)
            assert abs(suma - float(inf.get('monto') or 0)) < 1.0, (
                "el total y la lista dicen cosas distintas", suma, inf.get('monto'))
    finally:
        _limpiar()


def test_un_pago_en_CERO_sigue_siendo_cero(app, db_clean):
    """El borde que hace que el arreglo no invente plata (M96)."""
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO pagos_influencers (influencer_nombre, valor, fecha, estado, "
                   "concepto, vence_pago_at) "
                   "VALUES (?,0,'2020-01-01','Pendiente','REEL','2020-01-15')",
                   (NOMBRE,))
        cn.commit()
    finally:
        cn.close()
    try:
        inf = ((_cli(app).get('/api/gerencia/decisiones-ceo').get_json() or {})
               .get('influencers') or {})
        mios = [x for x in (inf.get('pendientes') or [])
                if x.get('influencer_nombre') == NOMBRE]
        assert mios, ("el pago en cero no aparece en la cola", mios)
        # ⚠ `x.get('monto') or -1` daría -1 con monto=0, porque CERO ES FALSY · es
        # exactamente la familia de bug que este archivo arregla, y me mordió acá mismo.
        assert float(mios[0].get('monto', -1)) == 0.0, (
            "un pago sin monto dejó de ser cero", mios[0].get('monto'))
    finally:
        _limpiar()


# ── COMPRAS que esperan su firma ────────────────────────────────────────────────

def _limpiar_oc():
    cn = _cn()
    try:
        cn.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE 'ZCEO-OC-%'")
        cn.commit()
    finally:
        cn.close()


def test_las_ordenes_por_autorizar_usan_el_criterio_de_COMPRAS(app, db_clean):
    """El bloque preguntaba por un estado MUERTO, así que decía siempre cero.

    `Revisada` es legacy: `compras.py` lo declara *"solo lectura · mig 157 los migró"*. El
    panel del CEO filtraba **sólo** por ese estado, así que mostraba *"Ninguna orden
    esperando tu firma"* teniendo diez en `Borrador`. Compras cuenta las que faltan
    autorizar como `estado IN ('Borrador','Revisada')`, y el CEO tiene que usar ESA misma
    definición: dos criterios del mismo hecho divergen, y el que se olvida es el que
    decide (M1/M5).
    """
    _limpiar_oc()
    cn = _cn()
    try:
        cn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, valor_total, fecha, "
                   "estado) VALUES ('ZCEO-OC-1','ZPROV',1500000,'2020-01-01','Borrador')")
        cn.commit()
    finally:
        cn.close()
    try:
        d = _cli(app).get('/api/gerencia/decisiones-ceo').get_json() or {}
        ocs = d.get('ocs_por_autorizar')
        assert ocs is not None, ("el bloque de compras no llegó", sorted(d.keys()))
        mias = [o for o in ocs if o.get('numero_oc') == 'ZCEO-OC-1']
        assert mias, ("una orden en Borrador no aparece como pendiente de firma · el panel "
                      "sigue preguntando por un estado que ya no se usa", ocs[:3])
        assert float(mias[0].get('valor') or 0) == 1500000.0, mias[0]
    finally:
        _limpiar_oc()


def test_una_orden_ya_AUTORIZADA_no_vuelve_a_pedir_firma(app, db_clean):
    """El borde: ampliar el filtro no puede traer de vuelta lo ya firmado (M96)."""
    _limpiar_oc()
    cn = _cn()
    try:
        cn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, valor_total, fecha, "
                   "estado) VALUES ('ZCEO-OC-2','ZPROV',900000,'2020-01-01','Autorizada')")
        cn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, valor_total, fecha, "
                   "estado) VALUES ('ZCEO-OC-3','ZPROV',800000,'2020-01-01','Pagada')")
        cn.commit()
    finally:
        cn.close()
    try:
        ocs = ((_cli(app).get('/api/gerencia/decisiones-ceo').get_json() or {})
               .get('ocs_por_autorizar') or [])
        nums = [o.get('numero_oc') for o in ocs]
        assert 'ZCEO-OC-2' not in nums, ("pide firmar una orden ya autorizada", nums[:5])
        assert 'ZCEO-OC-3' not in nums, ("pide firmar una orden ya pagada", nums[:5])
    finally:
        _limpiar_oc()
