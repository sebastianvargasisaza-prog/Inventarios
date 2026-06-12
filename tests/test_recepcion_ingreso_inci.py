"""Recepción de MP rotula el kardex por INCI, no por nombre comercial
(Sebastián 12-jun: el comercial varía por proveedor y es la mayor fuente de
error en recepción). Identidad sigue siendo el código; el comercial NO se borra.

Cubre los 3 puntos de ingreso:
  · /api/ordenes-compra/<oc>/recibir   (recepción contra OC · compras.py)
  · /api/recepcion                     (ingreso manual · inventario.py)
  · /api/recepcion/detalle/<oc>        (el panel devuelve INCI · despachos.py)
"""
import os
import sqlite3
from datetime import date, timedelta
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _ultimo_material_nombre(codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        row = conn.execute(
            "SELECT material_nombre FROM movimientos WHERE material_id=? "
            "ORDER BY id DESC LIMIT 1", (codigo,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def test_recibir_oc_rotula_kardex_por_inci(app, db_clean):
    COD, INCI, COMERCIAL = "MP-RCP-OC", "GLYCERIN", "Glicerina USP ProveedorX"
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,?,?,1)", (COD, INCI, COMERCIAL))
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria) "
          "VALUES ('OC-RCP-INCI', date('now'), 'Autorizada', 'ProveedorX', 0, 'MP')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-RCP-INCI', ?, ?, 1000, 0)", (COD, COMERCIAL))

    fv = (date.today() + timedelta(days=365)).isoformat()
    cs = _login(app)
    r = cs.post('/api/ordenes-compra/OC-RCP-INCI/recibir',
                json={'items_recepcion': [{
                    'codigo_mp': COD, 'cantidad_recibida': 1000, 'lote': 'L-RCP-1',
                    'lote_proveedor': 'PROV-LOTE-1', 'fecha_vencimiento': fv, 'estado': 'OK'}],
                    'forzar': True},
                headers=csrf_headers())
    assert r.status_code in (200, 201), r.data

    # El kardex quedó rotulado por INCI, NO por el comercial.
    assert _ultimo_material_nombre(COD) == INCI, "el movimiento debe rotular por INCI"
    # El comercial NO se borró del maestro (trazabilidad / matching proveedor).
    conn = sqlite3.connect(os.environ["DB_PATH"])
    com = conn.execute("SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?", (COD,)).fetchone()[0]
    conn.close()
    assert com == COMERCIAL, "el nombre comercial debe conservarse en la BD"


def test_recibir_oc_sin_inci_cae_al_codigo_no_al_comercial(app, db_clean):
    COD, COMERCIAL = "MP-RCP-NOINCI", "Algo Comercial Raro"
    # MP sin INCI (nombre_inci vacío) — debe caer al CÓDIGO, nunca al comercial ni blanco.
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,'',?,1)", (COD, COMERCIAL))
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria) "
          "VALUES ('OC-RCP-NOINCI', date('now'), 'Autorizada', 'ProveedorX', 0, 'MP')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-RCP-NOINCI', ?, ?, 500, 0)", (COD, COMERCIAL))

    fv = (date.today() + timedelta(days=365)).isoformat()
    cs = _login(app)
    r = cs.post('/api/ordenes-compra/OC-RCP-NOINCI/recibir',
                json={'items_recepcion': [{
                    'codigo_mp': COD, 'cantidad_recibida': 500, 'lote': 'L-RCP-2',
                    'lote_proveedor': 'PROV-LOTE-2', 'fecha_vencimiento': fv, 'estado': 'OK'}],
                    'forzar': True},
                headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    assert _ultimo_material_nombre(COD) == COD, "sin INCI debe caer al código, no al comercial"


def test_detalle_oc_devuelve_inci(app, db_clean):
    COD, INCI, COMERCIAL = "MP-RCP-DET", "NIACINAMIDE", "Vitamina B3 ProvY"
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,?,?,1)", (COD, INCI, COMERCIAL))
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria) "
          "VALUES ('OC-RCP-DET', date('now'), 'Autorizada', 'ProvY', 0, 'MP')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-RCP-DET', ?, ?, 2000, 0)", (COD, COMERCIAL))

    cs = _login(app)
    r = cs.get('/api/recepcion/detalle/OC-RCP-DET')
    assert r.status_code == 200, r.data
    items = r.get_json()['items']
    it = next(x for x in items if x['codigo_mp'] == COD)
    assert it['inci'] == INCI, "el detalle de recepción debe traer el INCI para mostrar"


def test_recepcion_manual_rotula_por_inci(app, db_clean):
    COD, INCI, COMERCIAL = "MP-RCP-MAN", "PANTHENOL", "D-Pantenol ProvZ"
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
          "VALUES (?,?,?,1)", (COD, INCI, COMERCIAL))
    cs = _login(app)
    r = cs.post('/api/recepcion',
                json={'codigo_mp': COD, 'cantidad': 800, 'lote': 'L-MAN-1'},
                headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    assert _ultimo_material_nombre(COD) == INCI, "ingreso manual debe rotular por INCI"
