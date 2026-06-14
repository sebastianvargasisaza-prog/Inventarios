"""13-jun · Cola final INCI (Sebastián "todo por INCI"): el consolidado por
proveedor (/api/compras/consolidado-proveedor) debe exponer nombre_inci en cada
item — tanto en el consolidado de lectura (items) como en los items_raw por OC
(modo editar) — para que las tablas de detalle de OC muestren INCI como nombre
principal. La LLAVE sigue siendo codigo_mp (JOIN maestro_mps), nunca INCI.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_consolidado_proveedor_expone_inci(admin_client):
    # MP con INCI distinto del comercial
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MPINCITEST','Cetiol CC','DICAPRYLYL CARBONATE',1)")
    _exec("INSERT INTO ordenes_compra (numero_oc,proveedor,estado,fecha,valor_total,categoria,con_iva) "
          "VALUES ('OC-INCI-1','ProvINCI','Autorizada','2026-06-13',100000,'Materia Prima',0)")
    _exec("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) "
          "VALUES ('OC-INCI-1','MPINCITEST','Cetiol CC',5000,20,100000)")

    r = admin_client.get('/api/compras/consolidado-proveedor?estados=Autorizada')
    assert r.status_code == 200, r.data[:200]
    data = r.get_json()['proveedores']
    prov = next((p for p in data if p['proveedor'] == 'ProvINCI'), None)
    assert prov, 'el proveedor debe aparecer en el consolidado'

    # consolidado de lectura
    item = next((i for i in prov['items'] if i['codigo_mp'] == 'MPINCITEST'), None)
    assert item and item.get('nombre_inci') == 'DICAPRYLYL CARBONATE', \
        f'el item consolidado debe traer nombre_inci · {item}'

    # items_raw por OC (modo editar)
    oc = next((o for o in prov['ocs'] if o['numero_oc'] == 'OC-INCI-1'), None)
    assert oc, 'la OC debe aparecer'
    raw = next((i for i in oc['items_raw'] if i['codigo_mp'] == 'MPINCITEST'), None)
    assert raw and raw.get('nombre_inci') == 'DICAPRYLYL CARBONATE', \
        f'el items_raw debe traer nombre_inci · {raw}'
