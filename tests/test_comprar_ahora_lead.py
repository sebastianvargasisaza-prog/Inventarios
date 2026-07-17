"""Sebastián 17-jul · Punto 4: columna 'COMPRAR AHORA' que resuelve el horizonte SOLA por el
lead time de cada MP (H objetivo = lead + buffer), neta (consumo − stock − pendiente), redondeada
al MOQ/múltiplo. Reemplaza que el humano elija columna."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def _seed(cod, prod, lead, buffer, moq=0, mult=0, kg=100, pct=10, stock=500):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Compra ZZ', 'COMPRA INCI', 1)", (cod,))
    _exec("INSERT OR REPLACE INTO mp_lead_time_config (material_id, lead_time_dias, buffer_dias, moq_g, multiplo_g) "
          "VALUES (?, ?, ?, ?, ?)", (cod, lead, buffer, moq, mult))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Compra ZZ', ?, 0)", (prod, cod, pct))
    # producción a +10 días → su consumo entra completo desde el 1er horizonte (15d)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+10 days'), 1, 'pendiente', ?, 'eos_plan')", (prod, kg))
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, lote, fecha) "
          "VALUES (?, 'Compra ZZ', ?, 'Entrada', ?, date('now','-5 hours'))", (cod, stock, prod + "-L1"))


def test_comprar_ahora_por_lead_time(app, db_clean):
    # lead 30 + buffer 20 → horizonte objetivo 50d · consumo 10% × 100kg = 10000 g · stock 500
    _seed("MP-COMPRA1", "QACOMPRA1", lead=30, buffer=20, kg=100, pct=10, stock=500)
    mp = _mp(app, "MP-COMPRA1")
    assert mp is not None, "la MP debe aparecer"
    assert mp["horizonte_objetivo_dias"] == 50, mp["horizonte_objetivo_dias"]  # lead+buffer
    # comprar_ahora = consumo@50 (10000) − stock (500) − pendiente (0) = 9500
    assert abs(mp["comprar_ahora_g"] - 9500) < 50, mp["comprar_ahora_g"]
    # cobertura muy baja (500g / ~111 g/día ≈ 4.5d) << lead 30 → TARDE
    assert mp["reorden_estado"] in ("TARDE", "COMPRAR"), mp["reorden_estado"]


def test_comprar_ahora_redondea_a_moq_y_multiplo(app, db_clean):
    # comprar neto ≈ 9500 pero MOQ 12000 → sube a 12000
    _seed("MP-COMPRA2", "QACOMPRA2", lead=30, buffer=20, moq=12000, kg=100, pct=10, stock=500)
    mp = _mp(app, "MP-COMPRA2")
    assert mp is not None
    assert abs(mp["comprar_ahora_g"] - 12000) < 1, mp["comprar_ahora_g"]
    # múltiplo de 1000: 9500 → 10000
    _seed("MP-COMPRA3", "QACOMPRA3", lead=30, buffer=20, mult=1000, kg=100, pct=10, stock=500)
    mp3 = _mp(app, "MP-COMPRA3")
    assert mp3 is not None
    assert abs(mp3["comprar_ahora_g"] - 10000) < 1, mp3["comprar_ahora_g"]


def test_comprar_ahora_cero_si_stock_cubre(app, db_clean):
    # stock 20000 > consumo@50 (10000) → no comprar
    _seed("MP-COMPRA4", "QACOMPRA4", lead=30, buffer=20, kg=100, pct=10, stock=20000)
    mp = _mp(app, "MP-COMPRA4")
    assert mp is not None
    assert mp["comprar_ahora_g"] == 0, mp["comprar_ahora_g"]
    assert mp["reorden_estado"] == "OK", mp["reorden_estado"]
