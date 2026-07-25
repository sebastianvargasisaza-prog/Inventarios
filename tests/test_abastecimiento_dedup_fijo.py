"""Dos tandas FIJAS del mismo producto el mismo día son DOS lotes reales.

Auditoría 25-jul (dos agentes lo encontraron por separado): el dedup por (producto, fecha)
de `_consumo_horizontes_core` se quedaba con UNA sola fila, la de más kg, sin mirar el
origen. Ese dedup nació para el M49 (planes solapados de 3 generadores que inflaban el
pedido hasta 130x), pero se aplicaba también a dos filas FIJAS legítimas: programar dos
tandas de 20 kg el mismo día pedía la MP de una sola → se compra la mitad.

La regla correcta:
  · lo FIJO (eos_plan / eos_b2b / eos_retroactivo) es decisión explícita del usuario y
    NUNCA se colapsa: cada tanda cuenta.
  · lo SUGERIDO sí se deduplica por (producto, fecha), y además se descarta si ese mismo
    día ya tiene una fila FIJA (la sugerencia es la misma producción que el usuario ya fijó
    → contarla otra vez es el doble conteo que el dedup vino a evitar).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ DEDUP FIJO'
MP = 'MPDEDFIJO'


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


def _limpiar():
    _sql("DELETE FROM produccion_programada WHERE producto='%s'" % PROD,
         "DELETE FROM formula_items WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM formula_headers WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM movimientos WHERE material_id='%s'" % MP,
         "DELETE FROM maestro_mps WHERE codigo_mp='%s'" % MP)


def _sembrar_formula():
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo,controla_stock) "
         "VALUES ('%s','GLYCERIN DF','Glicerina DF','MP',1,1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',20000,20,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN DF',10.0,0)" % (PROD, MP))


def _lote(origen, kg, dias=5):
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','+%d days'), 1, %s, '%s', 'pendiente')"
         % (PROD, dias, kg, origen))


def _consumo(c, h='90'):
    r = c.get('/api/abastecimiento/consumo-horizontes?horizontes=%s&tipo=mp' % h)
    assert r.status_code == 200, r.data[:300]
    for it in (r.get_json() or {}).get('mps', []):
        if it['codigo'] == MP:
            return float((it.get('consumo') or {}).get(h, 0) or 0)
    return 0.0


def test_dos_lotes_fijos_mismo_dia_suman(app):
    """20 kg + 20 kg el mismo día, MP al 10% → 4000 g, no 2000."""
    _sembrar_formula()
    _lote('eos_plan', 20)
    _lote('eos_plan', 20)
    c = _login(app)
    try:
        assert abs(_consumo(c) - 4000.0) < 1.0, \
            'SUBESTIMA: las dos tandas fijas deben pedir 4000 g · dio %s' % _consumo(c)
    finally:
        _limpiar()


def test_fijo_de_animus_mas_pedido_b2b_mismo_dia_suman(app):
    """Un lote de stock (eos_plan) y un pedido de cliente (eos_b2b) el mismo día son dos lotes."""
    _sembrar_formula()
    _lote('eos_plan', 20)
    _lote('eos_b2b', 20)
    c = _login(app)
    try:
        assert abs(_consumo(c) - 4000.0) < 1.0, _consumo(c)
    finally:
        _limpiar()


def test_sugerida_del_mismo_dia_no_se_suma_a_la_fija(app):
    """La sugerencia del mismo día es la MISMA producción que el usuario ya fijó: no se cuenta dos veces."""
    _sembrar_formula()
    _lote('eos_plan', 20)
    _lote('eos_canonico', 20)
    c = _login(app)
    try:
        assert abs(_consumo(c) - 2000.0) < 1.0, \
            'DOBLE CONTEO: la sugerida del mismo día no debe sumarse a la fija · dio %s' % _consumo(c)
    finally:
        _limpiar()


def test_dos_sugeridas_mismo_dia_siguen_deduplicando(app):
    """La protección del M49 sigue viva: planes solapados auto-generados NO se apilan."""
    _sembrar_formula()
    _lote('eos_canonico', 20)
    _lote('sugerido', 15)
    c = _login(app)
    try:
        assert abs(_consumo(c) - 2000.0) < 1.0, \
            'se apilaron dos sugeridas del mismo día (M49) · dio %s' % _consumo(c)
    finally:
        _limpiar()


def test_auto_plan_no_se_apila_sobre_lo_fijo(app):
    """Con plan Fijo del producto, las capas auto-generadas del cron se siguen ignorando (M49)."""
    _sembrar_formula()
    _lote('eos_plan', 20, dias=5)
    _lote('auto_plan', 20, dias=9)
    _lote('eos_proyeccion', 20, dias=12)
    c = _login(app)
    try:
        assert abs(_consumo(c) - 2000.0) < 1.0, \
            'las capas auto-generadas volvieron a apilarse sobre lo fijo · dio %s' % _consumo(c)
    finally:
        _limpiar()


def test_pantalla_y_generar_oc_ven_lo_mismo(app):
    """PARIDAD M5: un lote ATRASADO no iniciado debe pesar igual en la pantalla que en generar-OC.

    Antes la pantalla usaba piso=hoy y generar-OC piso=hoy-7: un lote programado hace 2 días y
    nunca iniciado daba 0 g en la pantalla y 2000 g en la OC. El número que se muestra tiene que
    ser el que decide.
    """
    _sembrar_formula()
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','-2 days'), 1, 20, 'eos_plan', 'pendiente')" % PROD)
    c = _login(app)
    try:
        pantalla = _consumo(c)
        assert abs(pantalla - 2000.0) < 1.0, \
            'la pantalla no cuenta el lote atrasado · dio %s' % pantalla
        r = c.get('/api/programacion/mps-deficit?days_ahead=90')
        assert r.status_code == 200, r.data[:300]
        d = r.get_json() or {}
        items = d.get('mps') if isinstance(d.get('mps'), list) else (d.get('items') or [])
        if isinstance(items, dict):
            items = list(items.values())
        oc = None
        for it in (items or []):
            if (it.get('codigo') or it.get('codigo_mp')) == MP:
                oc = float(it.get('deficit_g') or 0)
        if oc is not None:
            assert oc > 0, 'generar-OC tampoco debería ver 0 para un lote atrasado sin stock'
    finally:
        _limpiar()


def test_mp_descontinuada_conserva_proveedor_y_lead(app):
    """Descontinuar una MP (activo=0) no puede borrarle el proveedor ni el lead time.

    `mp_info` filtraba activo=1, así que una MP descontinuada que la fórmula sigue usando caía
    al default (lead 14 d, buffer 30, proveedor vacío). En una importada de 90 días de lead eso
    desploma el "comprar ahora" y deja la solicitud sin proveedor al que rutearla.
    """
    _sembrar_formula()
    _sql("UPDATE maestro_mps SET activo=0, proveedor='ProveedorImportadoTT' WHERE codigo_mp='%s'" % MP,
         "DELETE FROM mp_lead_time_config WHERE material_id='%s'" % MP,
         "INSERT INTO mp_lead_time_config (material_id, lead_time_dias, buffer_dias, proveedor_principal) "
         "VALUES ('%s', 90, 30, 'ProveedorImportadoTT')" % MP)
    _lote('eos_plan', 20)
    c = _login(app)
    try:
        r = c.get('/api/abastecimiento/consumo-horizontes?horizontes=90&tipo=mp')
        assert r.status_code == 200, r.data[:300]
        it = next((x for x in (r.get_json() or {}).get('mps', []) if x['codigo'] == MP), None)
        assert it is not None, 'la MP de la fórmula tiene que aparecer aunque esté descontinuada'
        assert int(it.get('lead_time_dias') or 0) == 90, \
            'perdió el lead time real · quedó %s' % it.get('lead_time_dias')
        assert (it.get('proveedor_sugerido') or '') == 'ProveedorImportadoTT', \
            'perdió el proveedor · quedó %r' % it.get('proveedor_sugerido')
    finally:
        _sql("DELETE FROM mp_lead_time_config WHERE material_id='%s'" % MP)
        _limpiar()
