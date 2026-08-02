"""Renombrar un producto tiene que alcanzar TODAS las llaves (2-ago).

Sebastián: *"deberías hacer que HYDRABALANCE sea pegado, y que quede así en todo lado"*.

El nombre del producto es la LLAVE en 34 tablas y el renombrador tocaba 8. La más cara de
olvidar era `sku_producto_map`: ahí vive el enlace con las ventas de Shopify, así que un
producto renombrado a medias pierde su velocidad, sale con velocidad CERO y deja de
programarse -- sin un solo error a la vista (M1/M2).

Y lo que NO se renombra se DECLARA: los registros de calidad, quejas, recalls y movimientos
dicen el nombre que el producto tenía cuando ocurrieron, y así deben quedar (M105).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

VIEJO = 'ZZREN PRODUCTO VIEJO'
NUEVO = 'ZZRENPRODUCTONUEVO'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    for n in (VIEJO, NUEVO):
        for t, col in (('formula_items', 'producto_nombre'), ('formula_headers', 'producto_nombre'),
                       ('sku_producto_map', 'producto_nombre'),
                       ('produccion_programada', 'producto')):
            try:
                _sql("DELETE FROM %s WHERE %s=?" % (t, col), (n,))
            except Exception:
                pass
    _sql("DELETE FROM maestro_mps WHERE codigo_mp='ZZREN-MP'")


def test_el_rename_arrastra_el_mapeo_de_VENTAS(app, db_clean):
    """`sku_producto_map` es el enlace con Shopify. Si queda con el nombre viejo, el producto
    renombrado sale con velocidad CERO y el motor deja de programarlo."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock) VALUES ('ZZREN-MP','ZZ ren','ZZ REN',1,1)")
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,1)", (VIEJO,))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,100)", (VIEJO, 'ZZREN-MP', 'ZZ ren'))
    _sql("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)",
         ('ZZREN-SKU', VIEJO))
    try:
        r = _login(app).post('/api/admin/renombrar-producto',
                             headers={'Content-Type': 'application/json', **csrf_headers()},
                             json={'viejo': VIEJO, 'nuevo': NUEVO, 'dry_run': 0})
        assert r.status_code == 200, r.data[:300]
        j = r.get_json()
        assert j.get('aplicado') is True, j
        quedo = _sql("SELECT producto_nombre FROM sku_producto_map WHERE sku='ZZREN-SKU'")
        assert quedo and quedo[0][0] == NUEVO, (
            'el mapeo de ventas quedó con el nombre VIEJO: %r · el producto pierde su velocidad'
            % (quedo,))
        assert 'sku_producto_map' in (j.get('tablas_vivas_renombradas') or {}), j
    finally:
        _limpiar()


def test_declara_lo_que_NO_renombra(app, db_clean):
    """Un renombrado parcial silencioso es peor que uno declarado: hay que poder saber dónde
    sigue el nombre viejo y por qué (M100)."""
    _limpiar()
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,1)", (VIEJO,))
    try:
        r = _login(app).post('/api/admin/renombrar-producto',
                             headers={'Content-Type': 'application/json', **csrf_headers()},
                             json={'viejo': VIEJO, 'nuevo': NUEVO, 'dry_run': 0})
        j = r.get_json()
        hist = j.get('historico_NO_renombrado') or []
        assert 'movimientos' in hist and 'quejas_clientes' in hist, hist
    finally:
        _limpiar()


def test_el_dry_run_no_cambia_nada(app, db_clean):
    _limpiar()
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,1)", (VIEJO,))
    try:
        r = _login(app).post('/api/admin/renombrar-producto',
                             headers={'Content-Type': 'application/json', **csrf_headers()},
                             json={'viejo': VIEJO, 'nuevo': NUEVO})
        assert r.get_json().get('dry_run') is True, r.get_json()
        assert _sql("SELECT 1 FROM formula_headers WHERE producto_nombre=?", (VIEJO,)), (
            'el dry_run renombró igual')
    finally:
        _limpiar()


def test_el_preview_cuenta_LO_MISMO_que_el_apply_toca(app, db_clean):
    """M101 · el preview y el apply salen de la MISMA lista.

    El apply se extendió a 14 tablas vivas y el `ocurrencias` del dry_run seguía contando 7.
    Un preview que subestima el alcance da confianza para ejecutar algo que no se entendió --
    es exactamente lo que me hizo vaciar un legajo: la vista previa decía "5 → 15 pasos" y el
    resultado real fue 5 → 0, porque el COUNT no filtraba igual que el INSERT.
    """
    _limpiar()
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,10,1)", (VIEJO,))
    _sql("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)",
         ('ZZREN-SKU2', VIEJO))
    try:
        prev = _login(app).post('/api/admin/renombrar-producto',
                                headers={'Content-Type': 'application/json', **csrf_headers()},
                                json={'viejo': VIEJO, 'nuevo': NUEVO}).get_json()
        assert prev['dry_run'] is True
        assert prev['ocurrencias'].get('sku_producto_map') == 1, (
            'el preview no cuenta el mapeo de ventas que el apply SÍ renombra: %r'
            % prev['ocurrencias'])

        apl = _login(app).post('/api/admin/renombrar-producto',
                               headers={'Content-Type': 'application/json', **csrf_headers()},
                               json={'viejo': VIEJO, 'nuevo': NUEVO, 'dry_run': 0}).get_json()
        # todo lo que el preview contó con filas, el apply lo tocó
        for t, n in (prev['ocurrencias'] or {}).items():
            if n and t in dict(_tablas_vivas()):
                assert (apl.get('tablas_vivas_renombradas') or {}).get(t) == n, (
                    'preview dijo %d en %s y el apply renombró %r'
                    % (n, t, (apl.get('tablas_vivas_renombradas') or {}).get(t)))
    finally:
        _limpiar()


def _tablas_vivas():
    from blueprints.admin import _PROD_TABLAS_VIVAS
    return _PROD_TABLAS_VIVAS
