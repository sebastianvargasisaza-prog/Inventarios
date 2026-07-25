"""Mismo INCI, GRADO distinto: el resolver NO puede elegir por stock a ciegas.

El cerebro ya lo declara (M17 punto 3 y M19 punto c): "mismo INCI, GRADO distinto = NO
unificar a ciegas · el % de fórmula cambia con el grado → mezclarlos = potencia errada
(riesgo INVIMA) → decisión de Alejandro, NO automático". El gate nunca se implementó.

El tier 2b de `_resolver_material_bodega` busca otros códigos activos con el MISMO INCI
normalizado y devuelve el de MÁS STOCK, sin log. Y `_norm_mp_name` borra el paréntesis,
que es justo donde vive el grado ("(triterpenos 80%)", "(50 kD)").

Grupos ambiguos reales del maestro que tocan fórmulas vivas:
  HYALURONIC ACID → 50 kD / 300 kD / 1500 kD
  PARFUM          → tres fragancias distintas
  TOCOPHEROL      → Vitamina E líquida / polvo
  CENTELLA        → extracto / triterpenos 80%
  PANTHENOL       → líquido / polvo

Regla nueva: si hay UN solo candidato por INCI, se resuelve (ese es el caso legítimo del
código duplicado). Si hay VARIOS, es ambiguo: no se adivina, se deja pasar al tier 3 (que
matchea por NOMBRE y sí distingue el grado) y se DEJA RASTRO en el log.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ INCI AMBIGUO'
MP_FORMULA = 'MPHA50TT'      # el que pide la fórmula · sin stock
MP_A = 'MPHA300TT'           # mismo INCI, otro grado, con stock
MP_B = 'MPHA1500TT'          # mismo INCI, otro grado, con MÁS stock
PROD_UNICO = 'ZZ INCI UNICO'
MP_U_FORMULA = 'MPPANTTT1'
MP_U_BODEGA = 'MPPANTTT2'
INCI = 'HYALURONIC ACID TT'


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


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _neto(mid):
    db = _db()
    try:
        return float(db.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +','Ajuste') THEN cantidad "
            "WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad ELSE 0 END),0) "
            "FROM movimientos WHERE material_id=?", (mid,)).fetchone()[0] or 0)
    finally:
        db.close()


def _limpiar():
    cods = (MP_FORMULA, MP_A, MP_B, MP_U_FORMULA, MP_U_BODEGA)
    _in = ','.join("'%s'" % x for x in cods)
    _sql("DELETE FROM movimientos WHERE material_id IN (%s)" % _in,
         "DELETE FROM formula_items WHERE producto_nombre IN ('%s','%s')" % (PROD, PROD_UNICO),
         "DELETE FROM formula_headers WHERE producto_nombre IN ('%s','%s')" % (PROD, PROD_UNICO),
         "DELETE FROM producciones WHERE producto IN ('%s','%s')" % (PROD, PROD_UNICO),
         "DELETE FROM maestro_mps WHERE codigo_mp IN (%s)" % _in)


def _mp(cod, inci, comercial):
    return ("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo,controla_stock) "
            "VALUES ('%s','%s','%s','MP',1,1)" % (cod, inci, comercial))


def _entrada(cod, g, lote):
    return ("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,"
            "fecha_vencimiento,operador) VALUES ('%s','x',%s,'Entrada',date('now'),'%s','VIGENTE',"
            "'2027-12-31','test')" % (cod, g, lote))


def test_inci_ambiguo_no_descuenta_otro_grado(app):
    """Tres grados del mismo INCI: no puede elegir uno por stock y descontarlo."""
    _limpiar()
    _sql(_mp(MP_FORMULA, INCI, 'Ac. hialuronico (50 kD)'),
         _mp(MP_A, INCI, 'Ac. hialuronico (300 kD)'),
         _mp(MP_B, INCI, 'Ac. hialuronico (1500 kD)'),
         _entrada(MP_A, 5000, 'L-HA300-TT'),
         _entrada(MP_B, 9000, 'L-HA1500-TT'),
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','Ac. hialuronico (50 kD)',1.0,0)" % (PROD, MP_FORMULA))
    c = _login(app)
    try:
        r = c.post('/api/produccion', json={'producto': PROD, 'cantidad_kg': 1,
                                            'operador': 'sebastian', 'presentacion': 'x'},
                   headers=csrf_headers())
        assert _neto(MP_A) == 5000.0, \
            'descontó el grado 300 kD que la fórmula NO pide · quedó %s' % _neto(MP_A)
        assert _neto(MP_B) == 9000.0, \
            'descontó el grado 1500 kD que la fórmula NO pide · quedó %s' % _neto(MP_B)
        assert r.status_code != 201, \
            'debió frenar por falta de stock del grado correcto, no fabricar con otro · %s' % r.data[:200]
    finally:
        _limpiar()


def test_inci_con_un_solo_candidato_sigue_resolviendo(app):
    """El caso legítimo (un código duplicado del MISMO material) NO se rompe."""
    _limpiar()
    _sql(_mp(MP_U_FORMULA, 'PANTHENOL TT', 'D-Pantenol'),
         _mp(MP_U_BODEGA, 'PANTHENOL TT', 'D-Pantenol'),
         _entrada(MP_U_BODEGA, 5000, 'L-PANT-TT'),
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',10000,10,1,datetime('now'))" % PROD_UNICO,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','D-Pantenol',1.0,0)" % (PROD_UNICO, MP_U_FORMULA))
    c = _login(app)
    try:
        r = c.post('/api/produccion', json={'producto': PROD_UNICO, 'cantidad_kg': 1,
                                            'operador': 'sebastian', 'presentacion': 'x'},
                   headers=csrf_headers())
        assert r.status_code in (200, 201), \
            'el caso de código duplicado del mismo material debe seguir resolviendo · %s' % r.data[:300]
        assert abs(_neto(MP_U_BODEGA) - 4990.0) < 1.0, \
            'debió descontar 10 g (1%% de 1 kg) del código con stock · quedó %s' % _neto(MP_U_BODEGA)
    finally:
        _limpiar()
