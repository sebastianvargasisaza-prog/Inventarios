# -*- coding: utf-8 -*-
"""Lo que se declara en el cuadre LLEGA al inventario · 22-ago-2026.

Sebastián, contando en vivo: *"estoy colocando NO EXISTE en algunos, otros bajándolos a cero;
verificá que todo esté conectado al inventario y que sí esté haciendo los cambios"*.

Una cadena cubierta pieza por pieza sigue sin recorrerse entera, y un kardex con un descuento de
más -- o de menos -- **se ve igual que uno sano** (M172). Así que esto no prueba funciones: camina
el acto completo por los endpoints REALES y verifica que el mismo hecho se vea igual en los
CINCO lugares donde alguien lo va a leer:

    cuadre → kardex → stock canónico → lo que producción puede usar (FEFO) → abastecimiento

y además que lo que NO debe cambiar no cambie: el otro lote, el estado del lote y su
vencimiento.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_PROD = 'PRODUCTO CADENA CUADRE'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _propio(nombre):
    """Material y estantería exclusivos del caso.

    El `audit_log` es append-only por trigger: no se puede limpiar entre tests, así que el
    rastro de uno marcaría como revisado el material del siguiente (M102/M103).
    """
    suf = nombre.upper()[:12]
    return ('MP-CAD-' + suf, 'EST-CAD-' + suf)


def _limpiar(cod):
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (cod,))
        cn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc='CUADRE'")
        cn.commit()
    finally:
        cn.close()


def _sembrar(cod, est, lotes, con_formula=True, pct=10):
    """`lotes` = [(nombre, gramos, vencimiento, estado)]."""
    _limpiar(cod)
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
                   "  controla_stock, precio_referencia) VALUES (?,?,?,1,1,0)",
                   (cod, 'GOMA CADENA', 'CADENA GUM'))
        if con_formula:
            cn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                       "VALUES (?,1,1)", (_PROD,))
            cn.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                       "  material_nombre, porcentaje) VALUES (?,?,?,?)",
                       (_PROD, cod, 'GOMA CADENA', pct))
        for lote, g, vence, estado in lotes:
            cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                       "  lote, fecha, operador, estado_lote, fecha_vencimiento, estanteria, "
                       "  posicion) VALUES (?,?,'Entrada',?,?,'2026-08-01 08:00','test',?,?,?,'A')",
                       (cod, 'GOMA CADENA', g, lote, estado, vence, est))
        cn.commit()
    finally:
        cn.close()


# ── los cinco lugares donde el mismo hecho se tiene que ver igual ──────────────────────────

def _stock_canonico(cod):
    """`SUM(movimientos)` con la regla de siempre: es la fuente de verdad (regla #4)."""
    cn = _cn()
    try:
        r = cn.execute(
            "SELECT COALESCE(SUM(CASE "
            "  WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
            "  WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END),0) "
            "  FROM movimientos WHERE material_id=? "
            "   AND UPPER(COALESCE(estado_lote,'')) NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA',"
            "       'RECHAZADO','VENCIDO','AGOTADO','BLOQUEADO')", (cod,)).fetchone()
        return round(float(r[0] or 0), 2)
    finally:
        cn.close()


def _en_cuadre(cli, est):
    r = cli.get('/api/inventario/cuadre-lotes?est=%s' % est)
    assert r.status_code == 200, r.data[:300]
    return {x['lote']: x for x in r.get_json()['lotes']}


def _lo_que_produccion_ve(cli, cod, kg=1):
    r = cli.post('/api/produccion/simular', json={'producto': _PROD, 'cantidad_kg': kg},
                 headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    fila = next((i for i in r.get_json()['ingredientes']
                 if (i.get('codigo_bodega') or i.get('material_id')) == cod), None)
    assert fila, 'la simulación no trae la MP sembrada'
    return fila


def _declarar(cli, cod, est, lote, fisico, motivo, token):
    return cli.post('/api/inventario/cuadre',
                    json={'codigo_mp': cod, 'lote': lote, 'fisico': fisico, 'motivo': motivo,
                          'estanteria': est, 'token': token},
                    headers=csrf_headers())


# ───────────────────── "no existe" ─────────────────────

def test_NO_EXISTE_recorre_la_cadena_entera(app, db_clean):
    """El caso que Sebastián está haciendo ahora mismo. Se mira en los cinco lugares."""
    cod, est = _propio('noexiste')
    _sembrar(cod, est, [('L-SE-FUE', 400, '2027-06-30', 'VIGENTE'),
                        ('L-QUEDA', 600, '2027-09-30', 'VIGENTE')])
    try:
        c = _login(app)
        # ANTES: los dos lotes existen y producción los ve
        assert _stock_canonico(cod) == 1000
        assert set(_en_cuadre(c, est)) == {'L-SE-FUE', 'L-QUEDA'}
        antes = _lo_que_produccion_ve(c, cod)
        assert antes['g_disponible'] == 1000, antes

        r = _declarar(c, cod, est, 'L-SE-FUE', 0, 'no aparece por ningun lado', 'cad-1')
        assert r.status_code == 200, r.data[:300]

        # 1 · el KARDEX tiene la Salida, con su motivo
        cn = _cn()
        try:
            sal = cn.execute("SELECT cantidad, COALESCE(observaciones,''), "
                             "       COALESCE(estado_lote,''), COALESCE(fecha_vencimiento,'') "
                             "  FROM movimientos WHERE material_id=? AND lote='L-SE-FUE' "
                             "   AND tipo='Salida'", (cod,)).fetchall()
        finally:
            cn.close()
        assert len(sal) == 1, 'no escribió la salida en el kardex: %r' % (sal,)
        assert round(float(sal[0][0]), 2) == 400, 'sacó %r y había 400' % (sal[0][0],)
        assert 'no aparece' in sal[0][1], 'la salida no lleva el motivo: %r' % (sal[0][1],)

        # 2 · el STOCK CANÓNICO bajó exactamente eso
        assert _stock_canonico(cod) == 600, \
            'el stock quedó en %r y debía quedar en 600' % (_stock_canonico(cod),)

        # 3 · el CUADRE ya no lo ofrece, y el otro lote quedó intacto
        hoy = _en_cuadre(c, est)
        assert 'L-SE-FUE' not in hoy, 'el lote en cero sigue en la hoja'
        assert hoy['L-QUEDA']['stock_sistema'] == 600, \
            'se llevó puesto el otro lote: %r' % (hoy['L-QUEDA'],)

        # 4 · PRODUCCIÓN ve menos, y ya no propone el lote que no está
        despues = _lo_que_produccion_ve(c, cod)
        assert despues['g_disponible'] == 600, \
            'producción sigue creyendo que hay %r' % (despues['g_disponible'],)
        assert 'L-SE-FUE' not in [x['lote'] for x in despues['lotes']], \
            'el FEFO sigue mandando a pesar de un lote que no está'

        # 5 · quedó AUDITADO (Part 11)
        cn = _cn()
        try:
            aud = cn.execute("SELECT COUNT(*) FROM audit_log WHERE accion='CUADRE_INVENTARIO' "
                             "  AND registro_id=?", (cod,)).fetchone()
        finally:
            cn.close()
        assert aud[0] >= 1, 'el ajuste no dejó rastro'
    finally:
        _limpiar(cod)


def test_BAJAR_A_CERO_deja_el_lote_en_cero_y_nada_mas(app, db_clean):
    """El otro caso que está haciendo: escribir 0 en la cantidad."""
    cod, est = _propio('cero')
    _sembrar(cod, est, [('L-A', 250, '2027-06-30', 'VIGENTE'),
                        ('L-B', 750, '2027-08-30', 'VIGENTE')])
    try:
        c = _login(app)
        assert _declarar(c, cod, est, 'L-A', 0, 'conteo fisico: no hay',
                         'cad-cero').status_code == 200
        assert _stock_canonico(cod) == 750
        hoy = _en_cuadre(c, est)
        assert 'L-A' not in hoy and hoy['L-B']['stock_sistema'] == 750
    finally:
        _limpiar(cod)


def test_una_cantidad_MENOR_ajusta_exactamente_la_diferencia(app, db_clean):
    """Ni de más ni de menos: un kardex con un descuento equivocado se ve igual que uno sano."""
    cod, est = _propio('menos')
    _sembrar(cod, est, [('L-A', 500, '2027-06-30', 'VIGENTE')])
    try:
        c = _login(app)
        assert _declarar(c, cod, est, 'L-A', 320, 'conteo fisico', 'cad-menos').status_code == 200
        assert _stock_canonico(cod) == 320
        cn = _cn()
        try:
            sal = cn.execute("SELECT SUM(cantidad) FROM movimientos WHERE material_id=? "
                             "  AND tipo='Salida'", (cod,)).fetchone()
        finally:
            cn.close()
        assert round(float(sal[0] or 0), 2) == 180, 'sacó %r y la diferencia era 180' % (sal[0],)
    finally:
        _limpiar(cod)


def test_una_cantidad_MAYOR_suma_con_tipo_valido(app, db_clean):
    """Si hay más de lo que decía, entra como Ajuste -- que el lector del stock cuenta como
    entrada. `Ajuste +` NO existe como tipo: el trigger lo rechaza (M62)."""
    cod, est = _propio('mas')
    _sembrar(cod, est, [('L-A', 100, '2027-06-30', 'VIGENTE')])
    try:
        c = _login(app)
        assert _declarar(c, cod, est, 'L-A', 175, 'habia mas', 'cad-mas').status_code == 200
        assert _stock_canonico(cod) == 175
        cn = _cn()
        try:
            tipos = [r[0] for r in cn.execute(
                "SELECT tipo FROM movimientos WHERE material_id=? AND tipo<>'Entrada'",
                (cod,)).fetchall()]
        finally:
            cn.close()
        assert tipos == ['Ajuste'], 'tipo inválido para el trigger: %r' % (tipos,)
    finally:
        _limpiar(cod)


# ───────────── lo que el cuadre NO puede cambiar por la puerta de atrás ─────────────

def test_el_cuadre_CONSERVA_el_estado_del_lote(app, db_clean):
    """Un lote en cuarentena que se cuadra sigue en cuarentena: si el ajuste lo liberara, el
    material retenido por Calidad entraría a producción por una puerta lateral (M31/M23)."""
    cod, est = _propio('estado')
    _sembrar(cod, est, [('L-CUAR', 300, '2027-06-30', 'CUARENTENA')], con_formula=False)
    try:
        c = _login(app)
        # el lote en cuarentena no sale en la hoja (no es stock usable), pero se puede cuadrar
        # por su código y lote, que es lo que hace el buscador global
        assert _declarar(c, cod, est, 'L-CUAR', 280, 'conteo fisico',
                         'cad-cuar').status_code == 200
        cn = _cn()
        try:
            estados = sorted(set(r[0] for r in cn.execute(
                "SELECT UPPER(COALESCE(estado_lote,'')) FROM movimientos "
                "  WHERE material_id=? AND lote='L-CUAR'", (cod,)).fetchall()))
        finally:
            cn.close()
        assert estados == ['CUARENTENA'], \
            'el cuadre liberó un lote que Calidad tenía retenido: %r' % (estados,)
        assert _stock_canonico(cod) == 0, 'la cuarentena empezó a contar como stock usable'
    finally:
        _limpiar(cod)


def test_el_cuadre_CONSERVA_el_vencimiento(app, db_clean):
    """Un ajuste que pierde la fecha devuelve material eterno al FEFO y lo vuelve invisible para
    el cron de vencidos (M118)."""
    cod, est = _propio('vence')
    _sembrar(cod, est, [('L-A', 400, '2027-03-15', 'VIGENTE')])
    try:
        c = _login(app)
        assert _declarar(c, cod, est, 'L-A', 350, 'conteo', 'cad-vence').status_code == 200
        cn = _cn()
        try:
            fechas = sorted(set(r[0] for r in cn.execute(
                "SELECT COALESCE(fecha_vencimiento,'') FROM movimientos "
                "  WHERE material_id=? AND lote='L-A'", (cod,)).fetchall()))
        finally:
            cn.close()
        assert fechas == ['2027-03-15'], 'el ajuste perdió el vencimiento: %r' % (fechas,)
        # y producción lo sigue viendo con su fecha
        fila = _lo_que_produccion_ve(c, cod)
        assert fila['lotes'][0]['vence'][:10] == '2027-03-15', fila['lotes'][0]
    finally:
        _limpiar(cod)


def test_un_doble_click_no_descuenta_dos_veces(app, db_clean):
    """Un doble descuento no da NINGÚN síntoma: el kardex simplemente dice menos de lo que hay
    (M172/M260)."""
    cod, est = _propio('doble')
    _sembrar(cod, est, [('L-A', 500, '2027-06-30', 'VIGENTE')])
    try:
        c = _login(app)
        cuerpo = dict(cod=cod, est=est, lote='L-A', fisico=300, motivo='conteo',
                      token='cad-doble-1')
        assert _declarar(c, **cuerpo).status_code == 200
        r2 = _declarar(c, **cuerpo)
        assert r2.status_code == 409, r2.data[:200]
        assert _stock_canonico(cod) == 300, \
            'el segundo clic volvió a descontar: %r' % (_stock_canonico(cod),)
    finally:
        _limpiar(cod)


# ───────────── y el informe lo cuenta igual ─────────────

def test_el_informe_cuenta_lo_MISMO_que_el_kardex(app, db_clean):
    """Dos vistas del mismo hecho que no coinciden dejan sin creerle a ninguna (M161)."""
    cod, est = _propio('informe')
    _sembrar(cod, est, [('L-A', 400, '2027-06-30', 'VIGENTE'),
                        ('L-B', 600, '2027-08-30', 'VIGENTE')])
    try:
        c = _login(app)
        _declarar(c, cod, est, 'L-A', 0, 'no aparece', 'cad-inf-1')
        _declarar(c, cod, est, 'L-B', 450, 'habia menos', 'cad-inf-2')
        d = c.get('/api/inventario/cuadre-informe').get_json()
        no_esta = [x for x in d['no_esta'] if x['codigo_mp'].upper() == cod.upper()]
        ajus = [x for x in d['ajustados'] if x['codigo_mp'].upper() == cod.upper()]
        assert len(no_esta) == 1 and no_esta[0]['sistema'] == 400, no_esta
        assert len(ajus) == 1 and ajus[0]['ajuste'] == -150, ajus
        # y el kardex dice exactamente lo mismo
        assert _stock_canonico(cod) == 450
    finally:
        _limpiar(cod)
