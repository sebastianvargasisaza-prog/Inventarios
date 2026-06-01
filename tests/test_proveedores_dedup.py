"""Dedup de proveedores variante de mayúsculas (caso Agenquimicos).

La tabla proveedores tiene UNIQUE(nombre) → los duplicados reales son variantes
de mayúsculas/espacios ('Agenquimicos' vs 'AGENQUIMICOS'), no nombres idénticos.
La fusión por nombre los bloqueaba (keeper.lower()==merge_from.lower()); el dedup
por id los resuelve.
"""
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


def test_dedup_variante_mayusculas(app, db_clean):
    import json
    c = _login(app)
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM proveedores WHERE UPPER(TRIM(nombre))='AGENQUIMICOS-T'")
        cu.execute("DELETE FROM ordenes_compra WHERE proveedor IN ('agenquimicos-t','AGENQUIMICOS-T')")
        # variante minúscula CON NIT (más completa) + variante mayúscula sin nada
        cu.execute("INSERT INTO proveedores (nombre, nit, activo) VALUES ('agenquimicos-t','900123',1)")
        cu.execute("INSERT INTO proveedores (nombre, activo) VALUES ('AGENQUIMICOS-T',1)")
        # una OC apuntando a la variante mayúscula → debe moverse al keeper
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total) VALUES ('OC-DEDUP-T','AGENQUIMICOS-T','Borrador',0)")
        conn.commit()
    r = c.post("/api/admin/proveedores-dedup-nombre",
               data=json.dumps({"nombre": "AGENQUIMICOS-T"}), headers=_h())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True and d["n_baja"] == 1, d
    with app.app_context():
        from database import get_db
        cu = get_db().cursor()
        act = cu.execute("SELECT COUNT(*) FROM proveedores WHERE UPPER(TRIM(nombre))='AGENQUIMICOS-T' AND COALESCE(activo,1)=1").fetchone()[0]
        keeper = cu.execute("SELECT nombre, nit FROM proveedores WHERE id=?", (d["keeper_id"],)).fetchone()
        oc_prov = cu.execute("SELECT proveedor FROM ordenes_compra WHERE numero_oc='OC-DEDUP-T'").fetchone()[0]
    assert act == 1, "debe quedar 1 activo"
    assert keeper[1] == "900123", "keeper = el más completo (con NIT)"
    # la OC debe ahora apuntar al nombre del keeper (referencia movida)
    assert oc_prov == keeper[0], f"OC debe apuntar al keeper · {oc_prov} vs {keeper[0]}"
