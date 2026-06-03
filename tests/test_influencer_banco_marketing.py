"""Jeferson (marketing, NO admin) DEBE poder capturar/editar datos bancarios.

CEO 3-jun-2026 (LEY): marketing es quien sube/mantiene los datos bancarios del
influencer (banco/cuenta/cédula/tipo) que viajan a la cuenta de cobro → Compras
para que Sebastián pague. El PRIVACY-FIX previo los filtraba en silencio para
no-admin (PUT respondía ok:true pero NO guardaba) y el GET no los devolvía
(modal en blanco). Este test blinda el flujo reconciliado: marketing CAPTURA/EDITA
y VERIFICA; la privacidad se preserva con audit enmascarado y masking de vistas
masivas (no probado aquí).
"""
import json


def _login(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, (user, r.status_code)
    return c


def _h():
    from .conftest import csrf_headers
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def test_jeferson_edita_banco_persiste(app, db_clean):
    """jefferson edita banco de un influencer existente y el dato PERSISTE
    (antes se descartaba en silencio devolviendo ok:true)."""
    c = _login(app, "jefferson")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('InfBanco', 'Activo')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='InfBanco'").fetchone()[0]
        conn.commit()

    # PUT con datos bancarios
    r = c.put(f"/api/marketing/influencers/{iid}",
              data=json.dumps({
                  "nombre": "InfBanco",
                  "banco": "Bancolombia",
                  "cuenta_bancaria": "12345678901",
                  "tipo_cuenta": "Ahorros",
                  "cedula_nit": "1020304050",
              }), headers=_h())
    assert r.status_code == 200, r.data
    assert "aviso" not in (r.get_json() or {}), r.data  # NO debe avisar que ignoró banco

    # Persistió en BD
    with app.app_context():
        from database import get_db
        row = get_db().execute(
            "SELECT banco, cuenta_bancaria, tipo_cuenta, cedula_nit "
            "FROM marketing_influencers WHERE id=?", (iid,)).fetchone()
        assert row["banco"] == "Bancolombia", dict(row)
        assert row["cuenta_bancaria"] == "12345678901", dict(row)
        assert row["cedula_nit"] == "1020304050", dict(row)


def test_jeferson_ve_banco_en_get_detalle(app, db_clean):
    """El GET de detalle DEBE devolver el banco a marketing (modal no en blanco)."""
    c = _login(app, "jefferson")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado, banco, cuenta_bancaria) "
                   "VALUES ('InfVer', 'Activo', 'Davivienda', '99988877766')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='InfVer'").fetchone()[0]
        conn.commit()

    r = c.get(f"/api/marketing/influencers/{iid}")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d.get("banco") == "Davivienda", d
    assert d.get("cuenta_bancaria") == "99988877766", d


def test_jeferson_audit_banco_enmascarado(app, db_clean):
    """El rastro de audit de una edición bancaria NO debe guardar el valor en
    claro (Habeas Data): debe quedar enmascarado '***xxx'."""
    c = _login(app, "jefferson")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('InfAud', 'Activo')")
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre='InfAud'").fetchone()[0]
        conn.commit()

    r = c.put(f"/api/marketing/influencers/{iid}",
              data=json.dumps({"nombre": "InfAud", "cuenta_bancaria": "55544433322"}),
              headers=_h())
    assert r.status_code == 200, r.data

    with app.app_context():
        from database import get_db
        rows = get_db().execute(
            "SELECT accion, antes, despues FROM audit_log "
            "WHERE tabla='marketing_influencers' AND registro_id=? "
            "ORDER BY id DESC LIMIT 1", (iid,)).fetchall()
        assert rows, "no se registró audit_log"
        blob = (str(rows[0]["antes"]) + str(rows[0]["despues"]))
        assert "55544433322" not in blob, f"cuenta en claro en audit: {blob}"
        assert rows[0]["accion"] == "MODIFICAR_BANCO_INFLUENCER", dict(rows[0])
