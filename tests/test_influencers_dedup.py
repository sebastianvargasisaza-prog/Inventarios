"""Dedup masivo de influencers duplicados (reporte 'todos juanito rebel' 1-jun)."""
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


def test_dedup_merge_influencers(app, db_clean):
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM marketing_influencers WHERE UPPER(TRIM(nombre))='JUANITO REBEL'")
        cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre='Juanito Rebel'")
        # 3 duplicados del mismo nombre (distinto formato/case)
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('Juanito Rebel','Activo')")
        a = cu.lastrowid
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('juanito rebel','Activo')")
        b = cu.lastrowid
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES ('JUANITO  REBEL','Activo')")
        cc = cu.lastrowid
        # b tiene 2 pagos (será keeper), cc tiene 1 (se repunta a b)
        for iid_ in (b, b, cc):
            cu.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha) VALUES (?, 'Juanito Rebel', 100, date('now'))", (iid_,))
        conn.commit()
    # dry-run
    r = c.post("/api/marketing/influencers/dedup-merge", data=json.dumps({}), headers=_h())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["dry_run"] is True
    grp = next((g for g in d["grupos"] if g["keeper_id"] == b), None)
    assert grp is not None and grp["duplicados"] == 2, d["grupos"]
    # apply
    r2 = c.post("/api/marketing/influencers/dedup-merge", data=json.dumps({"apply": True}), headers=_h())
    assert r2.status_code == 200, r2.data
    d2 = r2.get_json()
    assert d2["aplicado"] is True
    assert d2["duplicados_eliminados"] == 2
    assert d2["unique_index"] is True
    with app.app_context():
        from database import get_db
        cu = get_db().cursor()
        n = cu.execute("SELECT COUNT(*) FROM marketing_influencers WHERE UPPER(TRIM(nombre))='JUANITO REBEL'").fetchone()[0]
        pagos_keeper = cu.execute("SELECT COUNT(*) FROM pagos_influencers WHERE influencer_id=?", (b,)).fetchone()[0]
    assert n == 1, f"debe quedar 1 'juanito rebel', quedan {n}"
    assert pagos_keeper == 3, f"los 3 pagos deben apuntar al keeper, hay {pagos_keeper}"
