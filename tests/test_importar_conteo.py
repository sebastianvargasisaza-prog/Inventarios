"""16-jun · Importar conteo físico: mapea el Excel al código_mp REAL y carga.

Valida código vs maestro_mps, corrige typo PM→MP, matchea por INCI los sin código,
carga movimientos Entrada VIGENTE con el código real y dedup por (código, lote).
"""
import io
import os
import sqlite3
import openpyxl
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _seed_catalogo():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        for cod, inci, com in [('MPCT01', 'HEXANEDIOL TEST', 'Hexanediol'),
                               ('MPCT50', 'GLYCERIN TEST', 'Glicerina'),
                               ('MPCT77', 'NIACINAMIDE TEST', 'Niacinamida')]:
            conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
            conn.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES (?,?,?,1)",
                         (cod, inci, com))
        conn.commit()
    finally:
        conn.close()


def _xlsx_bytes(rows):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(['Codigo MP', 'Nombre INCI', 'Nombre Comercial', 'Lote', 'Cantidad (g)',
               'Stock Min (g)', 'Total MP (g)', 'Estanteria', 'Posicion', 'Proveedor', 'Fecha Vencimiento', 'Dias'])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.read()


def _conteo_rows():
    # codigo, inci, comercial, lote, cant, min, total, est, pos, prov, venc, dias
    return [
        ['MPCT01', 'HEXANEDIOL TEST', 'Hexanediol', 'L1', 1200, 50, 1200, '4', 'C', 'YTBIO', '2028-04-30', 600],   # ok
        ['PMCT50', 'GLYCERIN TEST', 'Glicerina', 'L2', 800, 50, 800, '4', 'B', 'X', '2027-06-25', 300],            # typo PM->MP00... no: PMCT50 -> MPCT50
        ['', 'NIACINAMIDE TEST', 'Niacinamida', 'L3', 500, 50, 500, '5', 'A', 'Y', '2027-01-01', 200],             # sin código → por INCI
        ['MPNOEXISTE', 'NADA QUE VER', 'Desconocido', 'L4', 300, 0, 300, '', '', '', '', ''],                       # sin match
        ['MPCT01', 'HEXANEDIOL TEST', 'Hexanediol', 'L9', 0, 50, 0, '', '', '', '', ''],                            # en cero
    ]


def test_analizar_mapea_codigos(app, db_clean):
    _seed_catalogo()
    c = _login(app)
    data = {'archivo': (io.BytesIO(_xlsx_bytes(_conteo_rows())), 'conteo.xlsx')}
    r = c.post('/api/inventario/importar-conteo/analizar', data=data,
               content_type='multipart/form-data', headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    by = {(x['codigo'] or x['inci']): x for x in j['filas']}
    assert by['MPCT01']['codigo_real'] == 'MPCT01' and by['MPCT01']['match'] == 'ok'
    assert by['PMCT50']['codigo_real'] == 'MPCT50' and by['PMCT50']['match'] == 'corregido'
    # fila sin código → matchea por INCI
    sin_cod = [x for x in j['filas'] if not x['codigo']][0]
    assert sin_cod['codigo_real'] == 'MPCT77' and sin_cod['match'] == 'por_inci'
    assert by['MPNOEXISTE']['match'] == 'sin_match' and by['MPNOEXISTE']['codigo_real'] is None
    # contrasta el INCI del Excel vs el de la app (tal cual)
    assert by['MPCT01']['inci_app'] == 'HEXANEDIOL TEST' and by['MPCT01']['inci_coincide'] is True
    assert 'inci_distinto' in j['resumen']
    assert j['resumen']['cargables'] == 3  # MPCT01, PMCT50→MPCT50, sin_cod→MPCT77 (los con cant>0 y match)


def test_cargar_usa_codigo_real_y_dedup(app, db_clean):
    _seed_catalogo()
    c = _login(app)
    # analizar
    data = {'archivo': (io.BytesIO(_xlsx_bytes(_conteo_rows())), 'conteo.xlsx')}
    j = c.post('/api/inventario/importar-conteo/analizar', data=data,
               content_type='multipart/form-data', headers=csrf_headers()).get_json()
    # cargar
    r = c.post('/api/inventario/importar-conteo/cargar', json={'filas': j['filas']}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d['cargados'] == 3, d
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # cargó con el código REAL (PM→MP)
        assert conn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id='MPCT50' AND lote='L2'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id='MPCT77' AND lote='L3'").fetchone()[0] == 1
        # NO cargó el sin_match ni el cero
        assert conn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id='MPNOEXISTE'").fetchone()[0] == 0
    finally:
        conn.close()
    # re-cargar → dedup, no duplica
    r2 = c.post('/api/inventario/importar-conteo/cargar', json={'filas': j['filas']}, headers=csrf_headers())
    d2 = r2.get_json()
    assert d2['cargados'] == 0 and d2['saltados_duplicado'] == 3, d2


def test_importar_requiere_admin(app, db_clean):
    c = _login(app, 'valentina')
    r = c.post('/api/inventario/importar-conteo/analizar', data={}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]
