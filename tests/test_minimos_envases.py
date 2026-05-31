"""Pieza 3 · mínimos de envases dinámicos (del consumo del plan)."""
import json


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_minimos_envases_sugeridos_y_aplicar(app, db_clean):
    PROD = "MINENV-T1"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        cu.execute("DELETE FROM maestro_mee WHERE codigo='ENV-MIN-TEST'")
        cu.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,30,1)", (PROD,))
        cu.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, envase_codigo, activo) VALUES (?,?,?,30,?,1)", (PROD, "P30", "30ml", "ENV-MIN-TEST"))
        cu.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_minimo, stock_actual) VALUES ('ENV-MIN-TEST','Envase test', 1000, 500)")
        # 2 lotes de 30kg en el horizonte → 2000 uds del envase en ~30d
        cu.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) VALUES (?, date('now','-5 hours','+10 days'), 30, 'programado','eos_plan',1)", (PROD,))
        cu.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) VALUES (?, date('now','-5 hours','+20 days'), 30, 'programado','eos_plan',1)", (PROD,))
        conn.commit()
    r = c.get("/api/compras/minimos-envases-sugeridos?dias=90&cobertura_dias=45")
    assert r.status_code == 200, r.data
    d = r.get_json()
    fila = next((x for x in d["items"] if x["envase_codigo"] == "ENV-MIN-TEST"), None)
    assert fila is not None, d["items"]
    assert fila["consumo_horizonte"] == 2000, fila  # 2×(30kg/30ml)=2000
    assert fila["minimo_actual"] == 1000, fila
    # consumo_diario = 2000/90 = 22.2 · sugerido = ceil(22.2*45) = 1000
    assert fila["minimo_sugerido"] >= 999, fila
    # aplicar
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers())
    r2 = c.post("/api/compras/minimos-envases-aplicar",
                data=json.dumps({"items": [{"codigo": "ENV-MIN-TEST", "stock_minimo": 1500}]}), headers=h)
    assert r2.status_code == 200, r2.data
    assert r2.get_json()["actualizados"] == 1
    with app.app_context():
        from database import get_db
        v = get_db().execute("SELECT stock_minimo FROM maestro_mee WHERE codigo='ENV-MIN-TEST'").fetchone()[0]
    assert abs(float(v) - 1500) < 0.01, v
