"""Sebastián 1-jul: cuando Catalina guarda precios en una OC (items-precios), el precio
DEBE grabarse en maestro_mps.precio_referencia ("último precio manda") → se conserva y
auto-carga en la próxima OC. Antes solo iba al histórico → parecía que "no se guardaba"."""
import os, sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _one(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_precio_oc_se_graba_en_maestro(app, db_clean):
    cod = 'MP-PWT-1'
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo,tipo_material,precio_referencia) "
          "VALUES (?,'MP write-through',1,'MP',0)", (cod,))
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc,fecha,estado,proveedor,categoria,con_iva,valor_total) "
          "VALUES ('OC-PWT', date('now','-5 hours'),'Borrador','Prov','Materia Prima',0,0)")
    _exec("DELETE FROM ordenes_compra_items WHERE numero_oc='OC-PWT'")
    _exec("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) "
          "VALUES ('OC-PWT',?,'MP write-through',1000,0,0)", (cod,))

    c = _login(app, 'catalina')
    r = c.patch('/api/ordenes-compra/OC-PWT/items-precios',
                json={'items': [{'codigo_mp': cod, 'precio_unitario': 50}]},
                headers=csrf_headers())
    assert r.status_code == 200, f"{r.status_code} {r.data[:200]}"
    ref = _one("SELECT precio_referencia FROM maestro_mps WHERE codigo_mp=?", (cod,))
    assert ref and abs(float(ref[0]) - 50) < 0.001, f"precio_referencia debe quedar en 50 (último precio manda) · got {ref}"

    # 2º precio sobrescribe (último manda)
    r2 = c.patch('/api/ordenes-compra/OC-PWT/items-precios',
                 json={'items': [{'codigo_mp': cod, 'precio_unitario': 73.5}]},
                 headers=csrf_headers())
    assert r2.status_code == 200
    ref2 = _one("SELECT precio_referencia FROM maestro_mps WHERE codigo_mp=?", (cod,))
    assert ref2 and abs(float(ref2[0]) - 73.5) < 0.001, f"debe sobrescribir a 73.5 · got {ref2}"
