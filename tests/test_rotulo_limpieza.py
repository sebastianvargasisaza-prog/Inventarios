"""Rótulo virtual de limpieza PRD-PRO-002-F02 · mig 223 · 6-jun-2026.

Cubre el flujo de dos roles (operario realiza · Calidad verifica con e-firma)
y la liberación física por la ruta ÚNICA (despeje · M3):

  Sucio → [operario realiza] → En limpieza → [Calidad verifica+firma] → Limpio

Verifica también: snapshot inmutable, permisos por rol, gate de firma.
"""
import json
import pytest


def _area_sucia(app, codigo='PROD1'):
    """Devuelve (area_id) de un área activa y la deja en estado 'sucia'."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        row = conn.execute(
            "SELECT id FROM areas_planta WHERE codigo=? AND activo=1", (codigo,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id FROM areas_planta WHERE activo=1 ORDER BY id LIMIT 1"
            ).fetchone()
        area_id = row[0]
        conn.execute("UPDATE areas_planta SET estado='sucia' WHERE id=?", (area_id,))
        conn.commit()
        return area_id


def _firmar(client, *, record_table, record_id, meaning, password="TestPass123"):
    """Genera una e_signature (challenge + sign) y devuelve signature_id."""
    r = client.post("/api/sign/challenge", json={"password": password})
    assert r.status_code == 200, f"challenge falló: {r.status_code} {r.data[:200]}"
    token = r.get_json()["token"]
    r = client.post("/api/sign", json={
        "record_table": record_table, "record_id": str(record_id),
        "meaning": meaning, "challenge_token": token,
    })
    assert r.status_code in (200, 201), f"sign falló: {r.status_code} {r.data[:200]}"
    return r.get_json()["signature_id"]


def test_rotulo_get_devuelve_estado_y_equipos(admin_client, app):
    area_id = _area_sucia(app)
    r = admin_client.get(f"/api/planta/rotulo-limpieza/{area_id}")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert d["rotulo"]["estado"] == "Sucio"            # sucia → Sucio
    assert "equipos" in d["rotulo"]
    assert d["puede_realizar"] is True                 # admin = planta, sala sucia
    assert d["sanitizantes_sugeridos"]                 # lista de ayuda


def test_flujo_realizar_y_verificar_libera_area(admin_client, app):
    area_id = _area_sucia(app, 'PROD2')

    # 1) Operario realiza la limpieza
    r = admin_client.post(
        f"/api/planta/rotulo-limpieza/{area_id}/realizar",
        json={"sanitizante": "Alcohol 70%", "equipos": ["FAB2-X"],
              "producto_anterior": "Suero Test", "lote_anterior": "TST-001"},
    )
    assert r.status_code == 200, r.data[:300]
    rid = r.get_json()["rotulo_id"]

    # Estado físico ahora 'limpiando' (En limpieza)
    with app.app_context():
        from database import get_db
        est = get_db().execute(
            "SELECT estado FROM areas_planta WHERE id=?", (area_id,)
        ).fetchone()[0]
    assert est == "limpiando"

    # 2) Calidad firma (meaning 'revisa') y verifica
    sig = _firmar(admin_client, record_table="rotulos_limpieza",
                  record_id=rid, meaning="revisa")
    r = admin_client.post(
        f"/api/planta/rotulo-limpieza/{area_id}/verificar",
        json={"signature_id": sig},
    )
    assert r.status_code == 200, r.data[:300]
    body = r.get_json()
    assert body["estado"] == "Limpio"
    checklist_id = body["checklist_id"]

    # Área liberada + despeje canónico creado + rótulo cerrado (inmutable)
    with app.app_context():
        from database import get_db
        conn = get_db()
        assert conn.execute(
            "SELECT estado FROM areas_planta WHERE id=?", (area_id,)
        ).fetchone()[0] == "libre"
        assert conn.execute(
            "SELECT COUNT(*) FROM despeje_linea_checklist WHERE id=?", (checklist_id,)
        ).fetchone()[0] == 1
        rot = conn.execute(
            "SELECT estado, verificado_por, producto_anterior, despeje_checklist_id "
            "FROM rotulos_limpieza WHERE id=?", (rid,)
        ).fetchone()
        assert rot[0] == "verificado"
        assert rot[1] == "sebastian"
        assert rot[2] == "Suero Test"            # snapshot inmutable
        assert rot[3] == checklist_id


def test_verificar_sin_firma_rechaza(admin_client, app):
    area_id = _area_sucia(app, 'PROD3')
    admin_client.post(f"/api/planta/rotulo-limpieza/{area_id}/realizar", json={})
    r = admin_client.post(
        f"/api/planta/rotulo-limpieza/{area_id}/verificar", json={})
    assert r.status_code == 400
    assert r.get_json()["codigo"] == "FIRMA_REQUERIDA"


def test_realizar_requiere_area_sucia(admin_client, app):
    # Área libre (Limpio) no admite registrar limpieza
    with app.app_context():
        from database import get_db
        conn = get_db()
        area_id = conn.execute(
            "SELECT id FROM areas_planta WHERE codigo='ENV1' AND activo=1"
        ).fetchone()[0]
        conn.execute("UPDATE areas_planta SET estado='libre' WHERE id=?", (area_id,))
        conn.commit()
    r = admin_client.post(f"/api/planta/rotulo-limpieza/{area_id}/realizar", json={})
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "AREA_NO_SUCIA"


def test_rotulo_pdf_renderiza_formato_f02(admin_client, app):
    area_id = _area_sucia(app, 'PROD1')
    admin_client.post(
        f"/api/planta/rotulo-limpieza/{area_id}/realizar",
        json={"sanitizante": "Amonio Cuaternario", "producto_anterior": "Crema X",
              "lote_anterior": "LX-9"})
    r = admin_client.get(f"/planta/rotulo-limpieza/{area_id}/pdf")
    assert r.status_code == 200
    body = r.data.decode("utf-8", "replace")
    assert "PRD-PRO-002-F02" in body
    assert "ESTADO DE LIMPIEZA" in body
    assert "Amonio Cuaternario" in body
    assert "Crema X" in body


def test_lista_rotulos_incluye_7_areas_oficiales(admin_client, app):
    r = admin_client.get("/api/planta/rotulos-limpieza")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    nombres = {a["nombre"] for a in d["areas"]}
    codigos = {a["codigo"] for a in d["areas"]}
    # Las 7 oficiales (mig 224)
    assert "Fabricación 1" in nombres
    assert "Fabricación y Envasado 2" in nombres
    assert "Fabricación y Envasado 3" in nombres
    assert "Envasado 1" in nombres
    assert "Envasado 2" in nombres
    assert "Dispensación" in nombres
    assert "Acondicionamiento" in nombres
    # Sin duplicados FAB* (desactivados)
    assert not (codigos & {"FAB1", "FAB2", "FAB3", "FAB_FLOAT"})


def test_usuario_no_planta_no_puede_realizar(logged_client, app):
    # valentina (comercial) no es planta → 403
    area_id = _area_sucia(app, 'PROD1')
    r = logged_client.post(
        f"/api/planta/rotulo-limpieza/{area_id}/realizar", json={})
    assert r.status_code == 403
