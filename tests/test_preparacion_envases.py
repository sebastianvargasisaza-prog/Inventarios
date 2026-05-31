"""Pieza 1 · jalonar envases de producciones próximas para preparación."""
import datetime as dt


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_preparacion_envases_jalona(app, db_clean):
    PROD = "PREP-ENV-T1"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        cu.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,30,1)", (PROD,))
        cu.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, envase_codigo, activo) VALUES (?,?,?,30,?,1)", (PROD, "P30", "30ml", "ENV-PREP-30"))
        cu.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) VALUES (?, date('now','-5 hours','+20 days'), 30, 'programado', 'eos_plan', 1)", (PROD,))
        conn.commit()
    r = c.get("/api/compras/preparacion-envases?dias=90&anticipo=30")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True
    fila = next((x for x in d["items"] if x["envase_codigo"] == "ENV-PREP-30" and x["producto"] == PROD), None)
    assert fila is not None, d["items"]
    assert fila["uds"] == 1000, fila  # 30kg / 30ml = 1000
    # fecha_lista = fecha_produccion - 30 días
    fp = dt.date.fromisoformat(fila["fecha_produccion"])
    fl = dt.date.fromisoformat(fila["fecha_lista_sugerida"])
    assert (fp - fl).days == 30, fila
