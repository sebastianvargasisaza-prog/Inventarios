def test_normalizar_lote(admin_client):
    """Normalizar en lote: renombra (destino libre) y fusiona (destino existe), TODO o NADA."""
    assert admin_client.get("/admin/normalizar-codigos").status_code == 200
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPBNSRC1','ALPHA ARBUTIN X',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPBNSRC1','X',500,'Entrada','2026-01-01','LB1','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPBNSRC2','CACAY X',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPBNSRC2','X',300,'Entrada','2026-01-01','LB2','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPBNDST2','CACAY DST',1,'MP')")
        conn.commit()
    texto = "MPBNSRC1 -> MPBNNEW1\nMPBNSRC2 -> MPBNDST2"
    pv = admin_client.post("/api/admin/normalizar-lote/preview", json={"texto": texto}).get_json()
    est = {p["origen"]: p["estado"] for p in pv["pares"]}
    assert est["MPBNSRC1"] == "RENOMBRAR" and est["MPBNSRC2"] == "FUSION"
    ap = admin_client.post("/api/admin/normalizar-lote/apply", json={"texto": texto}).get_json()
    assert ap["ok"] and ap["n"] == 2
    assert abs(admin_client.get("/api/admin/mp-diag?codigo=MPBNNEW1").get_json()["stock_usable_g"] - 500) < 1
    assert abs(admin_client.get("/api/admin/mp-diag?codigo=MPBNDST2").get_json()["stock_usable_g"] - 300) < 1
    # todo-o-nada: un par con origen inexistente → 400 y no aplica el otro
    r = admin_client.post("/api/admin/normalizar-lote/apply", json={"texto": "MPNOEXISTEQ -> MPZZ1"})
    assert r.status_code == 400
