"""Tests del endpoint /api/planta/cronograma-comparar-alejandro + página."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_comparar_requires_auth(client, db_clean):
    r = client.get("/api/planta/cronograma-comparar-alejandro")
    assert r.status_code == 401


def test_comparar_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/planta/cronograma-comparar-alejandro")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("rango", "resumen", "matches",
              "en_alejandro_no_calendar", "en_calendar_no_alejandro"):
        assert k in d
    for k in ("total_alejandro", "total_calendar", "matches_completos",
              "falta_en_calendar", "extra_en_calendar"):
        assert k in d["resumen"]


def test_comparar_match_completo(app, db_clean):
    """Si Calendar tiene exactamente lo de Alejandro, debe matchear."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Sembrar uno de los productos que Alejandro tiene
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0] if pr1 else None
    conn.execute("DELETE FROM produccion_programada WHERE producto LIKE 'Gel Hidratante%'")
    conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado, area_id)
        VALUES ('Gel Hidratante 50ml', '2026-05-05', 1, 'pendiente', ?)""",
        (pr1_id,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/planta/cronograma-comparar-alejandro")
        d = r.get_json()
        # Debe haber al menos 1 match
        matches_gel = [m for m in d["matches"]
                        if "Gel Hidratante" in m["producto_alejandro"]
                        and m["fecha"] == "2026-05-05"]
        assert len(matches_gel) >= 1
        assert matches_gel[0]["area_match"] is True
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE producto LIKE 'Gel Hidratante%' AND fecha_programada='2026-05-05'")
        conn.commit(); conn.close()


def test_comparar_falta_en_calendar(app, db_clean):
    """Si Calendar está vacío, todos los items de Alejandro aparecen como faltantes."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Limpiar mayo
    conn.execute("""DELETE FROM produccion_programada
                    WHERE fecha_programada BETWEEN '2026-05-01' AND '2026-05-31'""")
    conn.commit(); conn.close()
    r = c.get("/api/planta/cronograma-comparar-alejandro")
    d = r.get_json()
    assert d["resumen"]["falta_en_calendar"] >= 15  # Alejandro tiene ~19 items
    assert d["resumen"]["matches_completos"] == 0


def test_comparar_extra_en_calendar(app, db_clean):
    """Si Calendar tiene producto que Alejandro no mencionó, aparece en extra."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0] if pr1 else None
    conn.execute("DELETE FROM produccion_programada WHERE producto='Producto Inventado X'")
    conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado, area_id)
        VALUES ('Producto Inventado X', '2026-05-15', 1, 'pendiente', ?)""",
        (pr1_id,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/planta/cronograma-comparar-alejandro")
        d = r.get_json()
        extras = [x for x in d["en_calendar_no_alejandro"]
                   if x["producto"] == "Producto Inventado X"]
        assert len(extras) == 1
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE producto='Producto Inventado X'")
        conn.commit(); conn.close()


def test_comparar_pagina_renderiza(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/programacion-comparar")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Alejandro vs Calendar" in body
    assert "/api/planta/cronograma-comparar-alejandro" in body


def test_normalizar_y_matchea():
    from templates_py.cronograma_alejandro_data import matchea
    assert matchea("Gel Hidratante", "Gel Hidratante 50ml") is True
    assert matchea("Suero Vitamina C+ 30ml", "Suero Vitamina C") is True
    assert matchea("Hydra Balance", "hydra balance ⚡ NUEVA") is True
    assert matchea("Hydra Balance", "Hydra Peptide") is False
    assert matchea("", "X") is False
