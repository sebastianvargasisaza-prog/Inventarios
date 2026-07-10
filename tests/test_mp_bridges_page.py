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
