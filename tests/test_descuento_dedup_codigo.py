"""El descuento directo debe ACUMULAR por código de bodega resuelto ANTES del pre-check.

Auditoría 25-jul: `_handle_produccion_inner` planificaba UNA entrada por FILA de fórmula y
cada fila hacía su propio SELECT FEFO y su propio chequeo de stock contra los MISMOS lotes.
Dos filas que apuntan al mismo material de bodega (por código repetido, o por dos códigos
distintos que el resolver colapsa a uno) pasaban las dos el pre-check viendo el stock
COMPLETO cada una, y descontaban el doble → stock NEGATIVO por lote, silencioso: el kardex
dice que un lote entregó gramos que no tenía (trazabilidad falsa · INVIMA).

Es el mismo bug que el path programado ya tenía arreglado desde el 1-jun (P0-1, el `_acc`
de `programacion.py:_calcular_mp_consumo_produccion`); la ruta de Fabricación directa (que
es la que EOS usa de verdad) se había quedado sin él.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ DEDUP PROD'
MP = 'MPDEDUP1'
MP_B = 'MPDEDUP2'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _neto(material_id):
    db = _db()
    try:
        v = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +','Ajuste') THEN cantidad "
            "WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad ELSE 0 END),0) "
            "FROM movimientos WHERE material_id=?", (material_id,)).fetchone()[0]
    finally:
        db.close()
    return float(v or 0)


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    _sql("DELETE FROM movimientos WHERE material_id IN ('%s','%s')" % (MP, MP_B),
         "DELETE FROM formula_items WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM formula_headers WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM producciones WHERE producto='%s'" % PROD,
         "DELETE FROM maestro_mps WHERE codigo_mp IN ('%s','%s')" % (MP, MP_B))


def test_dos_filas_mismo_material_no_descuentan_doble(app):
    """Dos filas de la MISMA MP (10% + 10%) con stock solo para una: debe RECHAZAR, no dejar negativo."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('%s','GLYCERIN DEDUP','Glicerina Dedup','MP',1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
         # dos filas del mismo material · formula_items no tiene UNIQUE, así que esto es posible
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         # stock para UNA sola de las dos filas (necesita 100 + 100 = 200 g)
         "INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,"
         "fecha_vencimiento,operador) VALUES ('%s','GLYCERIN DEDUP',150,'Entrada',date('now'),"
         "'L-DEDUP-1','VIGENTE','2027-12-31','test')" % MP)
    c = _login(app)
    try:
        r = c.post('/api/produccion', json={'producto': PROD, 'cantidad_kg': 1,
                                            'operador': 'sebastian', 'presentacion': 'x'},
                   headers=csrf_headers())
        assert r.status_code != 201, (
            'debió RECHAZAR por stock insuficiente (necesita 200 g y hay 150) · devolvió %s: %s'
            % (r.status_code, r.data[:300]))
        assert _neto(MP) == 150.0, 'no debió tocar el kardex · quedó %s' % _neto(MP)
    finally:
        _limpiar()


def test_dos_filas_mismo_material_con_stock_suficiente_suman(app):
    """Con stock suficiente, las dos filas se consolidan y descuentan el TOTAL exacto (200 g)."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('%s','GLYCERIN DEDUP','Glicerina Dedup','MP',1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,"
         "fecha_vencimiento,operador) VALUES ('%s','GLYCERIN DEDUP',1000,'Entrada',date('now'),"
         "'L-DEDUP-2','VIGENTE','2027-12-31','test')" % MP)
    c = _login(app)
    try:
        r = c.post('/api/produccion', json={'producto': PROD, 'cantidad_kg': 1,
                                            'operador': 'sebastian', 'presentacion': 'x'},
                   headers=csrf_headers())
        assert r.status_code in (200, 201), r.data[:300]
        assert abs(_neto(MP) - 800.0) < 0.01, 'debió descontar 200 g (100+100) · quedó %s' % _neto(MP)
        # una sola línea de descuento para esa MP (consolidada), no dos
        desc = [d for d in (r.get_json() or {}).get('descuentos', []) if d.get('material_id') == MP]
        assert len(desc) == 1, 'debe haber UNA línea consolidada por MP · %s' % desc
        assert abs(float(desc[0]['cantidad_g']) - 200.0) < 0.01, desc[0]
    finally:
        _limpiar()


def test_simular_consolida_igual_que_el_descuento(app):
    """"Verificar stock" debe dar el MISMO veredicto que el descuento real (M5).

    Con dos filas de la misma MP (100 g + 100 g) y solo 150 g en bodega, el simulador
    miraba el stock completo por cada fila y decía "alcanza" en las dos.
    """
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo,controla_stock) "
         "VALUES ('%s','GLYCERIN DEDUP','Glicerina Dedup','MP',1,1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,"
         "fecha_vencimiento,operador) VALUES ('%s','GLYCERIN DEDUP',150,'Entrada',date('now'),"
         "'L-DEDUP-3','VIGENTE','2027-12-31','test')" % MP)
    c = _login(app)
    try:
        r = c.post('/api/produccion/simular', json={'producto': PROD, 'cantidad_kg': 1},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        ing = [i for i in d['ingredientes'] if i['material_id'] == MP]
        assert len(ing) == 1, 'debe consolidar las dos filas en una · %s' % ing
        assert abs(ing[0]['g_requerido'] - 200.0) < 0.01, ing[0]
        assert ing[0]['suficiente'] is False, 'con 150 g y 200 g requeridos NO alcanza'
        assert d['factible'] is False, 'el simulador debe decir NO factible, igual que el descuento'
    finally:
        _limpiar()


def test_descuento_de_mp_deja_audit_log(app):
    """Part 11 / INVIMA: descontar MP tiene que dejar rastro de quién descontó qué lote.

    Auditoría 25-jul: el bloque de audit hacía `from database import audit_log`, y audit_log
    NO vive en database.py (vive en audit_helpers.py, que el propio módulo ya importa bien
    arriba). El ImportError lo tragaba un `except Exception: pass`, así que el audit cuyo
    comentario dice "P0-6 · descontaba MP sin escribir audit_log" NUNCA se aplicó.
    """
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('%s','GLYCERIN DEDUP','Glicerina Dedup','MP',1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DEDUP',10.0,0)" % (PROD, MP),
         "INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,"
         "fecha_vencimiento,operador) VALUES ('%s','GLYCERIN DEDUP',1000,'Entrada',date('now'),"
         "'L-AUDIT-1','VIGENTE','2027-12-31','test')" % MP)
    c = _login(app)
    try:
        r = c.post('/api/produccion', json={'producto': PROD, 'cantidad_kg': 1,
                                            'operador': 'sebastian', 'presentacion': 'x'},
                   headers=csrf_headers())
        assert r.status_code in (200, 201), r.data[:300]
        db = _db()
        try:
            n = db.execute("SELECT COUNT(*) FROM audit_log WHERE accion='PRODUCCION_DESCONTAR_MP'").fetchone()[0]
        finally:
            db.close()
        assert n >= 1, 'el descuento de MP no dejó audit_log (Part 11 · INVIMA)'
    finally:
        _limpiar()
