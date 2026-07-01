"""Rótulos de dispensación de MP · impresión térmica + QR con info real (Sebastián 1-jul).
Protege: (1) el rótulo ya NO imprime en hoja carta landscape sino en etiqueta térmica
configurable (@page en mm, una por sticker), (2) el QR apunta a /scan/<código>/<lote>, y
(3) /scan resuelve a la info REAL del lote (MP, stock canónico, vencimiento, ubicación)."""
import os
import sqlite3
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
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _seed():
    _exec("DELETE FROM movimientos WHERE material_id='MP-ROT'")
    _exec("DELETE FROM formula_items WHERE producto_nombre='PROD-ROT'")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, tipo, activo) "
          "VALUES ('MP-ROT','Niacinamida Test','Niacinamide','Materia Prima',1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
          "VALUES ('PROD-ROT','MP-ROT','Niacinamida Test',5.0)")
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
          "estanteria, posicion, fecha_vencimiento, estado_lote) "
          "VALUES ('MP-ROT','Niacinamida Test',5000,'Entrada','2026-06-01','LROT-1','14','f','2027-11-09','Aprobado')")


def test_rotulos_impresion_termica(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/rotulos/PROD-ROT/35.0')
    assert r.status_code == 200, r.data
    body = r.get_data(as_text=True)
    # librería QR cargada + @page térmico (mm), NO hoja carta landscape
    assert 'qrcode.min.js' in body
    assert '@page{size:100mm 150mm' in body
    assert 'letter landscape' not in body
    # el QR apunta al scan real de ESTE lote
    assert '/scan/MP-ROT/LROT-1' in body
    # peso teórico correcto (5% de 35kg = 1.750 g) sigue en el rótulo
    assert '1,750.00 g' in body


def test_rotulos_tamano_configurable(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/rotulos/PROD-ROT/35.0?w=100&h=75')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '@page{size:100mm 75mm' in body   # respeta el tamaño pedido


def test_scan_trae_info_real_del_lote(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/scan/MP-ROT/LROT-1')
    assert r.status_code == 200, r.data
    b = r.get_data(as_text=True)
    assert 'Niacinamida Test' in b       # nombre real del MP
    assert 'LROT-1' in b                 # lote
    assert '5,000.0 g' in b              # stock canónico SUM(movimientos)
    assert '2027-11-09' in b             # vencimiento real
    assert 'Est. 14f' in b               # ubicación real


def test_scan_sin_login_redirige(app, db_clean):
    c = app.test_client()
    r = c.get('/scan/MP-ROT/LROT-1', follow_redirects=False)
    assert r.status_code in (301, 302)
    assert '/login' in r.headers.get('Location', '')
