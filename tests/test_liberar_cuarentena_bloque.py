import re, subprocess, os, shutil
def test_liberar_cuarentena_bloque(admin_client):
    assert admin_client.get("/admin/liberar-cuarentena").status_code == 200
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPCUAR1','AZELA X',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPCUAR1','AZELA X',2000,'Entrada','2026-01-01','LCUAR1','CUARENTENA')")
        conn.commit()
    li = admin_client.get("/api/admin/cuarentena-lista").get_json()
    assert li["ok"] and any(x["cod"] == "MPCUAR1" for x in li["lotes"])
    r = admin_client.post("/api/admin/liberar-cuarentena-bloque", json={})
    assert r.status_code == 200 and r.get_json()["liberados"] >= 1
    # ahora MPCUAR1 tiene stock usable (VIGENTE)
    dg = admin_client.get("/api/admin/mp-diag?codigo=MPCUAR1").get_json()
    assert abs(dg["stock_usable_g"] - 2000) < 1 and dg["stock_retenido_g"] == 0
    if shutil.which("node"):
        html = admin_client.get("/admin/liberar-cuarentena").get_data(as_text=True)
        for i, s in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
            p = "_lc%d.js" % i; open(p, "w", encoding="utf-8").write(s)
            rr = subprocess.run(["node", "--check", p], capture_output=True, text=True); os.remove(p)
            assert rr.returncode == 0, rr.stderr[:200]


def test_cuarentena_excluye_epp_y_seleccion(admin_client):
    """La lista/liberación de cuarentena excluye NO-MP (EPP) y permite selección (Sebastián 9-jul)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPQAA','AZ A',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPQAA','AZ A',500,'Entrada','2026-01-01','LQAA','CUARENTENA')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('EPP','EPP',7,'Entrada','2026-01-01','OC-OC-Z','CUARENTENA')")
        conn.commit()
    d = admin_client.get("/api/admin/cuarentena-lista").get_json()
    cods = {x["cod"] for x in d["lotes"]}
    assert "MPQAA" in cods and "EPP" not in cods and d["no_mp_excluidos"] >= 1
    admin_client.post("/api/admin/liberar-cuarentena-bloque", json={"seleccion": [{"cod": "MPQAA", "lote": "LQAA"}]})
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        assert c.execute("SELECT estado_lote FROM movimientos WHERE material_id='EPP' AND lote='OC-OC-Z'").fetchone()[0] == "CUARENTENA"
