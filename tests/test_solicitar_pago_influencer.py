"""Repro: subir/solicitar pago de influencer (reporte marketing 1-jun)."""
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


def test_solicitar_pago_influencer(app, db_clean):
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('TestInfluencer', 'Activo')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='TestInfluencer'").fetchone()[0]
        conn.commit()
    r = c.post(f"/api/marketing/influencers/{iid}/solicitar-pago",
               data=json.dumps({"valor": 500000, "concepto": "Pago test junio"}), headers=_h())
    print("STATUS", r.status_code, "BODY", r.data[:400])
    assert r.status_code == 200, r.data
    assert r.get_json().get("ok") is True


def test_solicitar_pago_no_colisiona_con_numero_existente(app, db_clean):
    """Bug 'no sirve' permanente: si el último SOL-2026 tiene formato no numérico,
    seq caía a 1 y generaba un numero YA existente → UNIQUE violation → 500 en cada
    intento. Ahora el blindaje anti-colisión debe encontrar un numero libre."""
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('InfCol', 'Activo')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='InfCol'").fetchone()[0]
        # numero con sufijo no numérico → fuerza el except del seq → seq=1
        cu.execute("DELETE FROM solicitudes_compra WHERE numero IN ('SOL-2026-0001','SOL-2026-ZZZ')")
        cu.execute("INSERT INTO solicitudes_compra (numero, fecha, estado) VALUES ('SOL-2026-0001','2026-06-01','Aprobada')")
        cu.execute("INSERT INTO solicitudes_compra (numero, fecha, estado) VALUES ('SOL-2026-ZZZ','2026-06-01','Aprobada')")
        conn.commit()
    r = c.post(f"/api/marketing/influencers/{iid}/solicitar-pago",
               data=json.dumps({"valor": 250000, "concepto": "anti-colisión"}), headers=_h())
    assert r.status_code == 200, r.data            # ya NO 500
    d = r.get_json()
    assert d.get("ok") is True, d
    assert d["numero"] != "SOL-2026-0001", d        # encontró uno libre


def test_solicitar_pago_guarda_publicacion_y_entregable(app, db_clean):
    """Rediseño 13-jul (Sebastián): el pago guarda fecha_publicacion + entregable
    → fluyen a la tarjeta de Compras para verificar que el creador SÍ publicó."""
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('InfPub', 'Activo')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='InfPub'").fetchone()[0]
        conn.commit()
    r = c.post(f"/api/marketing/influencers/{iid}/solicitar-pago",
               data=json.dumps({"valor": 300000, "concepto": "Reel",
                                 "fecha_publicacion": "2026-06-20",
                                 "entregable": "1 Reel del serum · https://instagram.com/p/abc",
                                 "fecha_contenido": "2026-06-20"}), headers=_h())
    assert r.status_code == 200, r.data
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        row = cu.execute("SELECT fecha_publicacion, entregable FROM pagos_influencers "
                         "WHERE influencer_id=? ORDER BY id DESC LIMIT 1", (iid,)).fetchone()
    assert row is not None, "no se creó el pago"
    assert row[0] == "2026-06-20", ("fecha_publicacion", row[0])
    assert "Reel del serum" in (row[1] or ""), ("entregable", row[1])
    assert "instagram.com" in (row[1] or ""), ("link en entregable", row[1])
