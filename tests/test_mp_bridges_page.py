import re, subprocess, os, shutil
def test_mp_bridges_page(admin_client):
    r = admin_client.get("/admin/mp-bridges")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Puentes MP" in html and "mp-bridge" in html and "desactivar" in html
    if shutil.which("node"):
        for i, s in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
            p = "_b%d.js" % i; open(p, "w", encoding="utf-8").write(s)
            rr = subprocess.run(["node", "--check", p], capture_output=True, text=True); os.remove(p)
            assert rr.returncode == 0, rr.stderr[:200]
    # el API de lista responde (aunque vacío)
    lr = admin_client.get("/api/programacion/mp-bridge")
    assert lr.status_code == 200 and isinstance(lr.get_json(), list)


def test_mp_bridge_flujo(admin_client):
    """[FIX 10-jul] La gestión de puentes usaba _db() inexistente → 500. Ahora agregar/listar/
    desactivar funciona (para separar códigos mal puenteados como Panthenol polvo↔líquido)."""
    a = admin_client.post("/api/programacion/mp-bridge",
                          json={"formula_material_id": "MPTB236", "bodega_material_id": "MPTB110",
                                "formula_material_nombre": "Pantenol polvo", "bodega_material_nombre": "Pantenol liq"})
    assert a.status_code == 200, a.get_data(as_text=True)[:200]
    lst = admin_client.get("/api/programacion/mp-bridge").get_json()
    b = [x for x in lst if x["formula_material_id"] == "MPTB236" and x["bodega_material_id"] == "MPTB110"]
    assert b and b[0]["activo"] in (1, True)
    bid = b[0]["id"]
    d = admin_client.delete("/api/programacion/mp-bridge/" + str(bid))
    assert d.status_code == 200 and d.get_json()["ok"]
    b2 = [x for x in admin_client.get("/api/programacion/mp-bridge").get_json() if x["id"] == bid][0]
    assert b2["activo"] in (0, False)


def test_mp_bridge_reapuntar(app, admin_client):
    """[10-jul] Re-apuntar un código de fórmula a OTRO código de bodega (corregir cruces como
    Panthenol líquido MPPANTLI01 que apuntaba al polvo MP00236 → debe ir a MP00110). Desactiva
    el puente viejo y crea el nuevo al destino correcto; el destino debe existir en el maestro."""
    fid, viejo, nuevo = "MPRPFORM01", "MPRPVIEJO01", "MPRPNUEVO01"
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM mp_formula_bridge WHERE formula_material_id=?", (fid,))
        for cod, nom in [(viejo, "Destino viejo"), (nuevo, "Destino nuevo")]:
            conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
            conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) VALUES (?,?,?,1)",
                         (cod, nom, nom))
        try:
            conn.commit()
        except Exception:
            pass
    # destino inexistente → 404
    from .conftest import csrf_headers
    r404 = admin_client.post("/api/admin/mp-bridge-reapuntar", json={"formula_material_id": fid, "nuevo_bodega": "NOEXISTE999"})
    assert r404.status_code == 404
    # puente inicial al viejo
    admin_client.post("/api/programacion/mp-bridge",
                      json={"formula_material_id": fid, "bodega_material_id": viejo,
                            "formula_material_nombre": "Fórmula RP", "bodega_material_nombre": "Destino viejo"})
    # re-apuntar al nuevo
    rp = admin_client.post("/api/admin/mp-bridge-reapuntar",
                           json={"formula_material_id": fid, "formula_nombre": "Fórmula RP", "nuevo_bodega": nuevo})
    assert rp.status_code == 200, rp.get_data(as_text=True)[:200]
    assert rp.get_json()["nuevo_destino"] == nuevo
    lst = admin_client.get("/api/programacion/mp-bridge").get_json()
    activos = [x for x in lst if x["formula_material_id"] == fid and x["activo"] in (1, True)]
    assert len(activos) == 1 and activos[0]["bodega_material_id"] == nuevo
    # el viejo quedó desactivado
    viejos = [x for x in lst if x["formula_material_id"] == fid and x["bodega_material_id"] == viejo]
    assert viejos and viejos[0]["activo"] in (0, False)
