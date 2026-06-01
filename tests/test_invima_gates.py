"""Gates INVIMA (audit 1-jun · con Sebastián): liberación avisar+override + marcador micro."""
import json
def _login(app, user="sebastian"):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c
def _h():
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def test_liberacion_avisa_sin_micro_conforme_y_permite_override(app, db_clean):
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM cola_liberacion WHERE lote='LIB-T1'")
        cu.execute("DELETE FROM calidad_micro_resultados WHERE lote='LIB-T1'")
        cu.execute("INSERT INTO cola_liberacion (producto_nombre, lote, estado, unidades, fecha_envasado, fecha_min_liberacion) VALUES ('ProdT','LIB-T1','listo_revisar',100,date('now'),date('now'))")
        iid = cu.execute("SELECT id FROM cola_liberacion WHERE lote='LIB-T1'").fetchone()[0]
        conn.commit()
    # sin micro conforme → avisa (409 requiere_override)
    r = c.post(f"/api/planta/cola-liberacion/{iid}/disposicion",
               data=json.dumps({"disposicion":"aprobado"}), headers=_h())
    assert r.status_code == 409, r.data
    assert r.get_json().get("requiere_override") is True
    assert r.get_json().get("bloqueo") == "micro_sin_conforme"
    # con override → libera
    r2 = c.post(f"/api/planta/cola-liberacion/{iid}/disposicion",
                data=json.dumps({"disposicion":"aprobado","override_micro":True}), headers=_h())
    assert r2.status_code == 200, r2.data


def test_liberacion_con_micro_conforme_pasa_sin_override(app, db_clean):
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM cola_liberacion WHERE lote='LIB-T2'")
        cu.execute("DELETE FROM calidad_micro_resultados WHERE lote='LIB-T2'")
        cu.execute("INSERT INTO cola_liberacion (producto_nombre, lote, estado, unidades, fecha_envasado, fecha_min_liberacion) VALUES ('ProdT','LIB-T2','listo_revisar',100,date('now'),date('now'))")
        iid = cu.execute("SELECT id FROM cola_liberacion WHERE lote='LIB-T2'").fetchone()[0]
        cu.execute("INSERT INTO calidad_micro_resultados (lote, producto_nombre, microorganismo, estado) VALUES ('LIB-T2','ProdT','Mesofilos','ok')")
        conn.commit()
    r = c.post(f"/api/planta/cola-liberacion/{iid}/disposicion",
               data=json.dumps({"disposicion":"aprobado"}), headers=_h())
    assert r.status_code == 200, r.data


def test_liberacion_oos_sigue_bloqueada_duro(app, db_clean):
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM cola_liberacion WHERE lote='LIB-T3'")
        cu.execute("DELETE FROM calidad_micro_resultados WHERE lote='LIB-T3'")
        cu.execute("INSERT INTO cola_liberacion (producto_nombre, lote, estado, unidades, fecha_envasado, fecha_min_liberacion) VALUES ('ProdT','LIB-T3','listo_revisar',100,date('now'),date('now'))")
        iid = cu.execute("SELECT id FROM cola_liberacion WHERE lote='LIB-T3'").fetchone()[0]
        cu.execute("INSERT INTO calidad_micro_resultados (lote, producto_nombre, microorganismo, estado) VALUES ('LIB-T3','ProdT','E.coli','fuera_industria')")
        conn.commit()
    # OOS → bloqueo duro incluso con override
    r = c.post(f"/api/planta/cola-liberacion/{iid}/disposicion",
               data=json.dumps({"disposicion":"aprobado","override_micro":True}), headers=_h())
    assert r.status_code == 409, r.data
    assert r.get_json().get("bloqueo") == "micro_fuera_industria"


def test_marcador_micro_se_crea_al_envasar(app, db_clean):
    """Item 2: planta_envasado_iniciar ahora crea el marcador micro (antes fallaba en silencio)."""
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM produccion_programada WHERE producto='ENVMICRO-T'")
        cu.execute("DELETE FROM calidad_micro_resultados WHERE lote='LOTE-ENVT'")
        cu.execute("INSERT INTO produccion_programada (producto, fecha_programada, estado, origen) VALUES ('ENVMICRO-T', date('now'), 'en_proceso','eos_plan')")
        pid = cu.execute("SELECT id FROM produccion_programada WHERE producto='ENVMICRO-T'").fetchone()[0]
        conn.commit()
    r = c.post("/api/planta/envasado/iniciar",
               data=json.dumps({"produccion_id": pid, "lote": "LOTE-ENVT", "unidades_planeadas": 50}), headers=_h())
    assert r.status_code in (200, 201), r.data
    with app.app_context():
        from database import get_db
        row = get_db().execute(
            "SELECT producto_nombre, microorganismo, estado FROM calidad_micro_resultados WHERE lote='LOTE-ENVT'"
        ).fetchone()
    assert row is not None, "el marcador micro debe crearse al envasar"
    assert row[0] == "ENVMICRO-T"
    assert row[1] == "pendiente_recoleccion"
    assert row[2] == "observacion"
