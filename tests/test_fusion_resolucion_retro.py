def test_fusion_resuelve_en_descuento(admin_client):
    """Un código fusionado (ej. MP00303→MP00301) se resuelve solo: el consumo anotado bajo el
    viejo se descuenta del canónico (Sebastián 9-jul · Ethylhexylglycerin)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPFRSRC','ETHYLHEX SRC',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPFRSRC','EH',5000,'Entrada','2026-01-01','LFR','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPFRDUP','ETHYLHEX DUP',1,'MP')")
        conn.commit()
    # fusionar el duplicado en el canónico (MPFRDUP → MPFRSRC)
    ap = admin_client.post("/api/admin/normalizar-lote/apply", json={"texto": "MPFRDUP -> MPFRSRC"}).get_json()
    assert ap["ok"] and ap["hechos"][0]["modo"] == "fusion"
    # el Excel dice el código viejo (MPFRDUP, ahora inactivo) → debe resolver a MPFRSRC y quedar OK
    filas = [{"cod": "MPFRDUP", "desc": "EH", "lote": "x", "cant": 350, "prod": "PT-EH", "bulk": "BEH"}]
    d = admin_client.post("/api/admin/descuento-retro/preview", json={"filas": filas}).get_json()
    row = d["rows"][0]
    assert row["status"] == "OK" and row["cod_resuelto"] == "MPFRSRC"
    assert "fusionado" in row["detalle"]
    # aplicar → descuenta de MPFRSRC
    da = admin_client.post("/api/admin/descuento-retro/apply", json={"filas": [row]}).get_json()
    assert da["ok"] and da["n_aplicadas"] == 1 and abs(da["total_descontado_g"] - 350) < 1
    assert abs(admin_client.get("/api/admin/mp-diag?codigo=MPFRSRC").get_json()["stock_usable_g"] - 4650) < 1
