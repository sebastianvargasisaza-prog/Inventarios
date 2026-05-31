"""Consolidación de fórmulas del mismo producto (PIB CHINO temporal → definitivo)."""
import json


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed(app, src, tgt, target_con_receta=True):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        for nm in (src, tgt):
            c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (nm,))
            c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (nm,))
            c.execute("DELETE FROM produccion_programada WHERE producto=?", (nm,))
            c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (nm,))
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,12,1)", (src,))
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,12,1)", (tgt,))
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES ('MP1','Agua test',1)")
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, activo) VALUES (?,?,?,10,1)", (src, "T10", "10ml"))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) VALUES (?, date('now','+10 days'), 12, 'programado', 'eos_plan', 1)", (src,))
        c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES (?, 'MP1', 'Agua', 90)", (src,))
        if target_con_receta:
            c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES (?, 'MP1', 'Agua', 90)", (tgt,))
        conn.commit()


def _q1(app, sql, params=()):
    with app.app_context():
        from database import get_db
        return get_db().execute(sql, params).fetchone()


def test_consolidar_dry_run_y_aplicar(app, db_clean):
    SRC, TGT = "CONS SOURCE T1", "CONS TARGET T1"
    c = _login_as(app, "sebastian")
    _seed(app, SRC, TGT)
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers())
    r = c.post("/api/admin/consolidar-producto",
               data=json.dumps({"source": SRC, "target": TGT}), headers=h)
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["dry_run"] is True
    assert d["lotes_pendientes_a_mover"] == 1, d
    assert "T10" in d["presentaciones_a_mover"], d
    assert d["receta_target_items"] == 1, d
    r2 = c.post("/api/admin/consolidar-producto",
                data=json.dumps({"source": SRC, "target": TGT, "aplicar": True}), headers=h)
    assert r2.status_code == 200, r2.data
    assert r2.get_json().get("aplicado") is True, r2.data
    assert _q1(app, "SELECT producto_nombre FROM producto_presentaciones WHERE presentacion_codigo='T10'")[0] == TGT
    assert _q1(app, "SELECT COUNT(*) FROM produccion_programada WHERE producto=?", (TGT,))[0] == 1
    assert int(_q1(app, "SELECT activo FROM formula_headers WHERE producto_nombre=?", (SRC,))[0]) == 0


def test_consolidar_bloquea_si_target_sin_receta(app, db_clean):
    SRC, TGT = "CONS SOURCE T2", "CONS TARGET T2"
    c = _login_as(app, "sebastian")
    _seed(app, SRC, TGT, target_con_receta=False)
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers())
    r = c.post("/api/admin/consolidar-producto",
               data=json.dumps({"source": SRC, "target": TGT, "aplicar": True}), headers=h)
    assert r.status_code == 400, r.data
    r2 = c.post("/api/admin/consolidar-producto",
                data=json.dumps({"source": SRC, "target": TGT, "aplicar": True, "copiar_receta": True}), headers=h)
    assert r2.status_code == 200, r2.data
    assert _q1(app, "SELECT COUNT(*) FROM formula_items WHERE producto_nombre=?", (TGT,))[0] >= 1
