"""Artes/Etiquetas · gate de Direccion Tecnica (Sebastian 19-jul).
Catalina solicita -> DT aprueba con e-firma (INCI) -> gate duro en marcacion."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _firma_directa(record_id, meaning, signer):
    """Inserta una e_signature valida directamente (bypass del challenge/TOTP en tests)."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        cur = conn.execute(
            "INSERT INTO e_signatures (record_table, record_id, meaning, signer_username, "
            "signed_at_utc, auth_factor, signature_hash) VALUES ('artes_etiquetas',?,?,?, "
            "'2026-07-19T00:00:00','password','testhash')", (str(record_id), meaning, signer))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_solicitar_y_aprobar_arte(app, db_clean):
    # Catalina (compras) solicita
    cat = _login(app, "catalina")
    r = cat.post("/api/artes/solicitar", json={"producto_nombre": "Suero Test DT",
                 "tipo": "etiqueta", "drive_url": "https://drive.google.com/file/d/ABC123/view"},
                 headers=csrf_headers())
    assert r.status_code == 201, r.get_data(as_text=True)
    aid = r.get_json()["id"]

    # aparece pendiente_dt
    d = cat.get("/api/artes?estado=pendiente_dt").get_json()
    assert any(a["id"] == aid for a in d["artes"])

    # DT (miguel) intenta aprobar SIN firma -> 400
    dt = _login(app, "miguel")
    r = dt.post(f"/api/artes/{aid}/aprobar-arte", json={"inci_revisado": True}, headers=csrf_headers())
    assert r.status_code == 400

    # con e-firma valida -> aprobado
    sid = _firma_directa(aid, "aprueba", "miguel")
    r = dt.post(f"/api/artes/{aid}/aprobar-arte", json={"signature_id": sid, "inci_revisado": True},
                headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)

    d = dt.get("/api/artes").get_json()
    arte = [a for a in d["artes"] if a["id"] == aid][0]
    assert arte["estado"] == "aprobado" and arte["arte_aprobado"] == 1 and arte["inci_revisado"] == 1


def test_gate_helper_arte_aprobado(app, db_clean):
    from api.blueprints.artes import arte_aprobado_para
    from api.database import get_db
    cat = _login(app, "catalina")
    cat.post("/api/artes/solicitar", json={"producto_nombre": "Gate Prod"}, headers=csrf_headers())
    with app.app_context():
        conn = get_db()
        assert arte_aprobado_para(conn, "Gate Prod") is False  # aun pendiente
    # aprobar
    aid = cat.get("/api/artes").get_json()["artes"][0]["id"]
    sid = _firma_directa(aid, "aprueba", "alejandro")
    dt = _login(app, "alejandro")
    dt.post(f"/api/artes/{aid}/aprobar-arte", json={"signature_id": sid}, headers=csrf_headers())
    with app.app_context():
        conn = get_db()
        assert arte_aprobado_para(conn, "GATE PROD") is True   # match normalizado


def test_solo_dt_aprueba(app, db_clean):
    cat = _login(app, "catalina")
    r = cat.post("/api/artes/solicitar", json={"producto_nombre": "X"}, headers=csrf_headers())
    aid = r.get_json()["id"]
    sid = _firma_directa(aid, "aprueba", "catalina")
    # catalina NO es DT -> 403
    r = cat.post(f"/api/artes/{aid}/aprobar-arte", json={"signature_id": sid}, headers=csrf_headers())
    assert r.status_code == 403
