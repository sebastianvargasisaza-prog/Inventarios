"""Programación v4 · Pieza 4 · mix_mode en /api/plan/desglose-tonos (Sebastián 15-jul).

El reparto entre referencias/tonos según el modo guardado en sku_planeacion_config:
  - auto  = venta de toda la ventana (default · comportamiento actual)
  - crece = venta RECIENTE (mitad de la ventana) → sigue la tendencia por color
  - fijo  = mix CONGELADO (se congela 1 vez y se repite hasta re-congelar)
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "V4MIX PROD"
SKA = "V4MIXA"
SKB = "V4MIXB"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _venta(sku, qty, dias_atras, tag):
    f = (datetime.utcnow() - timedelta(days=dias_atras))
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, creado_en) "
          "VALUES (?,?,?,?,?)",
          (f'V4MIX-{tag}', 'paid', 'paid', json.dumps([{'sku': sku, 'qty': qty}]),
           f.strftime('%Y-%m-%dT%H:%M:%S')))


def _limpiar():
    for sql, p in (
        ("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,)),
        ("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (PROD,)),
        ("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'V4MIX-%'", ()),
    ):
        _exec(sql, p)


def _base(mix_mode=None):
    _limpiar()
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo, es_regalo) VALUES (?,?,?,1,0)", (SKA, PROD, 50.0))
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo, es_regalo) VALUES (?,?,?,1,0)", (SKB, PROD, 50.0))
    if mix_mode:
        _exec("INSERT INTO sku_planeacion_config (producto_nombre, activo, mix_mode) VALUES (?,1,?)", (PROD, mix_mode))
    else:
        _exec("INSERT INTO sku_planeacion_config (producto_nombre, activo) VALUES (?,1)", (PROD,))


def _pct(client):
    r = client.get(f"/api/plan/desglose-tonos?producto={PROD}&ventana_dias=60")
    d = r.get_json()
    assert d and d.get('ok'), d
    return {it['sku'].upper(): it['porcentaje'] for it in d['items']}, d.get('mix_mode')


def test_auto_reparte_por_venta_full_window(app):
    _base(mix_mode='auto')
    _venta(SKA, 80, 45, 'a1')   # full window
    _venta(SKB, 40, 45, 'b1')
    try:
        c = _login(app)
        pct, mode = _pct(c)
        assert mode == 'auto'
        assert pct[SKA] > pct[SKB], pct
        assert abs(pct[SKA] - 66.67) < 1.5, pct  # 80/120
    finally:
        _limpiar()


def test_crece_sigue_la_venta_reciente(app):
    _base(mix_mode='crece')
    # SKA fuerte en lo VIEJO, SKB fuerte en lo RECIENTE. Full window ≈ 50/50.
    _venta(SKA, 100, 45, 'aold'); _venta(SKA, 20, 15, 'arec')
    _venta(SKB, 20, 45, 'bold'); _venta(SKB, 100, 15, 'brec')
    try:
        c = _login(app)
        pct, mode = _pct(c)
        assert mode == 'crece'
        # con 'crece' (venta reciente) SKB debe dominar (100 vs 20 en la mitad reciente)
        assert pct[SKB] > pct[SKA], pct
        assert pct[SKB] > 75, pct
    finally:
        _limpiar()


def test_crece_difiere_de_auto(app):
    # mismos datos, distinto modo → distinto reparto
    _venta_data = [(SKA, 100, 45, 'aold'), (SKA, 20, 15, 'arec'),
                   (SKB, 20, 45, 'bold'), (SKB, 100, 15, 'brec')]
    _base(mix_mode='auto')
    for s, q, dd, t in _venta_data:
        _venta(s, q, dd, t)
    try:
        c = _login(app)
        pct_auto, _ = _pct(c)
    finally:
        pass
    # cambiar a crece (mismos datos)
    _exec("UPDATE sku_planeacion_config SET mix_mode='crece' WHERE producto_nombre=?", (PROD,))
    try:
        pct_crece, _ = _pct(c)
        assert pct_crece[SKB] > pct_auto[SKB], (pct_auto, pct_crece)
    finally:
        _limpiar()


def _congelado(prod=PROD):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute("SELECT mix_congelado_json FROM sku_planeacion_config "
                         "WHERE producto_nombre=?", (prod,)).fetchone()
        return (r[0] if r else None)
    finally:
        conn.close()


def test_reguardar_mismo_fijo_no_descongela(app):
    """FIX P1 15-jul: re-guardar la decisión con el MISMO mix_mode='fijo' (p.ej. al cambiar
    kg/ritmo con 'fijo' aún seleccionado) NO debe borrar el mix congelado."""
    _base(mix_mode=None)
    _venta(SKA, 50, 20, 'a1'); _venta(SKB, 50, 20, 'b1')
    try:
        c = _login(app)
        c.post("/api/programacion/decision-produccion",
               json={'producto': PROD, 'mix_mode': 'fijo'}, headers=csrf_headers())
        pct1, _ = _pct(c)   # congela 50/50
        cong1 = _congelado()
        assert cong1, "debe haber quedado un mix congelado"
        # re-guardar con el MISMO modo 'fijo' + kg → NO debe descongelar
        r = c.post("/api/programacion/decision-produccion",
                   json={'producto': PROD, 'mix_mode': 'fijo', 'kg_objetivo_lote': 30},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data
        assert 'mix_congelado' not in (r.get_json().get('guardado') or {}), r.get_json()
        assert _congelado() == cong1, "el mix congelado NO debe cambiar al re-guardar el mismo modo"
        # y una venta nueva enorme sigue sin mover el reparto (sigue congelado)
        _venta(SKB, 500, 5, 'bmega')
        pct2, _ = _pct(c)
        assert abs(pct2[SKA] - pct1[SKA]) < 0.5, (pct1, pct2)
    finally:
        _limpiar()


def test_cambiar_modo_si_descongela(app):
    """Cambiar el mix_mode (fijo→auto) SÍ debe limpiar el congelado (re-congela la próxima vez)."""
    _base(mix_mode=None)
    _venta(SKA, 50, 20, 'a1'); _venta(SKB, 50, 20, 'b1')
    try:
        c = _login(app)
        c.post("/api/programacion/decision-produccion",
               json={'producto': PROD, 'mix_mode': 'fijo'}, headers=csrf_headers())
        _pct(c)
        assert _congelado(), "quedó congelado"
        r = c.post("/api/programacion/decision-produccion",
                   json={'producto': PROD, 'mix_mode': 'auto'}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        assert (r.get_json().get('guardado') or {}).get('mix_congelado') == 'reset', r.get_json()
        assert _congelado() is None, "al cambiar de modo el congelado debe limpiarse"
    finally:
        _limpiar()


def test_fijo_congela_y_no_cambia_con_nuevas_ventas(app):
    _base(mix_mode=None)
    _venta(SKA, 50, 20, 'a1'); _venta(SKB, 50, 20, 'b1')   # 50/50
    try:
        c = _login(app)
        # elegir 'fijo' vía el endpoint (limpia el congelado → se re-congela al pedir el desglose)
        r = c.post("/api/programacion/decision-produccion",
                   json={'producto': PROD, 'mix_mode': 'fijo'}, headers=csrf_headers())
        assert r.status_code == 200, r.data
        pct1, mode = _pct(c)   # congela 50/50
        assert mode == 'fijo'
        assert abs(pct1[SKA] - 50) < 2 and abs(pct1[SKB] - 50) < 2, pct1
        # ahora SKB vende MUCHO más → pero fijo NO debe cambiar
        _venta(SKB, 500, 5, 'bmega')
        pct2, _ = _pct(c)
        assert abs(pct2[SKA] - pct1[SKA]) < 0.5 and abs(pct2[SKB] - pct1[SKB]) < 0.5, (pct1, pct2)
    finally:
        _limpiar()
