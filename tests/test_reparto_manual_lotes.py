# -*- coding: utf-8 -*-
"""El operario reparte a mano de qué lote sale cada gramo · 22-ago-2026.

Sebastián lo eligió con esas palabras: *"elegir a mano de qué lote sale cada gramo"* -- 600 de
éste, 400 de aquél, y que cuadre.

Un reparto manual sobre un kardex regulado es una puerta nueva al inventario, así que lo que se
fija acá es lo que impide que sea una puerta de atrás:

  · **llega hasta el kardex** -- si la pantalla lo arma y el motor hace FEFO igual, la persona
    cree que pesó de los lotes que eligió y el sistema anotó otros (M5/M109);
  · **no alcanza lo que el FEFO no alcanza**: se valida contra la MISMA lista de lotes, así que
    no se puede consumir material en cuarentena, vencido o rechazado (M31/M23/M25);
  · **tiene que CUADRAR**: un reparto que no cuadra se ve resuelto y con eso se descuenta,
    así que faltarían o sobrarían gramos sin que nadie se entere hasta el piso (M195);
  · y lo que no valida **se RECHAZA con el motivo**, nunca se cae a FEFO en silencio.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_COD = 'MP-REPARTO-TEST'
_PROD = 'PRODUCTO REPARTO TEST'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _limpiar():
    """Limpieza ANTES de sembrar, con códigos FIJOS (M103)."""
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (_COD,))
        cn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (_COD,))
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM produccion_programada WHERE producto=?", (_PROD,))
        cn.commit()
    finally:
        cn.close()


def _lote(nombre, gramos, vence, estado='VIGENTE'):
    cn = _cn()
    try:
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                   "  fecha, operador, estado_lote, fecha_vencimiento, estanteria) "
                   "VALUES (?,?,'Entrada',?,?,'2026-08-01 08:00','test',?,?,'A1')",
                   (_COD, 'GOMA REPARTO', gramos, nombre, estado, vence))
        cn.commit()
    finally:
        cn.close()


def _sembrar():
    """Un producto de 1 kg al 10% -> necesita 100 g."""
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
                   "  controla_stock, precio_referencia) VALUES (?,?,?,1,1,0)",
                   (_COD, 'GOMA REPARTO', 'REPARTO GUM'))
        cn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                   "VALUES (?,1,1)", (_PROD,))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                   "  porcentaje) VALUES (?,?,?,10)", (_PROD, _COD, 'GOMA REPARTO'))
        cn.commit()
    finally:
        cn.close()


def _area(cli):
    cn = _cn()
    try:
        r = cn.execute("SELECT id FROM areas_planta WHERE COALESCE(activo,1)=1 "
                       "  AND COALESCE(puede_producir,0)=1 LIMIT 1").fetchone()
        if r:
            return r[0]
        r = cn.execute("SELECT id FROM areas_planta LIMIT 1").fetchone()
        return r[0] if r else None
    finally:
        cn.close()


def _fabricar(cli, reparto=None, kg=1):
    cuerpo = {'producto': _PROD, 'area_id': _area(cli), 'cantidad_kg': kg}
    if reparto is not None:
        cuerpo['reparto_lotes'] = reparto
    return cli.post('/api/planta/fabricacion/crear-iniciar', json=cuerpo,
                    headers=csrf_headers())


def _salidas():
    cn = _cn()
    try:
        return {r[0]: round(float(r[1]), 2) for r in cn.execute(
            "SELECT lote, SUM(cantidad) FROM movimientos WHERE material_id=? AND tipo='Salida' "
            "  GROUP BY lote", (_COD,)).fetchall()}
    finally:
        cn.close()


# ───────────────────── el reparto LLEGA al kardex ─────────────────────

def test_el_reparto_manual_MANDA_sobre_el_FEFO(app, db_clean):
    """La prueba de que la cadena entera lo respeta: si el motor hiciera FEFO igual, el operario
    pesaría de los lotes que eligió y el sistema anotaría otros (M5/M109)."""
    _sembrar()
    try:
        _lote('LOTE-VIEJO', 500, '2027-01-31')      # el que el FEFO tomaría primero
        _lote('LOTE-NUEVO', 500, '2029-12-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'LOTE-NUEVO': 100}})
        assert r.status_code in (200, 201), r.data[:300]
        s = _salidas()
        assert s.get('LOTE-NUEVO') == 100, \
            'no salió del lote que el operario eligió: %r' % (s,)
        assert 'LOTE-VIEJO' not in s, \
            'el FEFO se impuso sobre el reparto manual: %r' % (s,)
    finally:
        _limpiar()


def test_reparte_entre_VARIOS_lotes_como_el_operario_dijo(app, db_clean):
    """*"600 de éste, 400 de aquél"*."""
    _sembrar()
    try:
        _lote('L-A', 500, '2027-01-31')
        _lote('L-B', 500, '2028-01-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-A': 60, 'L-B': 40}})
        assert r.status_code in (200, 201), r.data[:300]
        s = _salidas()
        assert s.get('L-A') == 60 and s.get('L-B') == 40, \
            'el reparto no salió como se pidió: %r' % (s,)
    finally:
        _limpiar()


def test_sin_reparto_sigue_mandando_el_FEFO(app, db_clean):
    """Aditivo: quien no reparte no cambia en nada (M117)."""
    _sembrar()
    try:
        _lote('LOTE-VIEJO', 500, '2027-01-31')
        _lote('LOTE-NUEVO', 500, '2029-12-31')
        c = _login(app)
        assert _fabricar(c).status_code in (200, 201)
        s = _salidas()
        assert s.get('LOTE-VIEJO') == 100, \
            'sin reparto tiene que consumir el que vence antes: %r' % (s,)
    finally:
        _limpiar()


# ───────────── lo que un reparto NO puede alcanzar ─────────────

def test_un_reparto_NO_puede_consumir_un_lote_en_CUARENTENA(app, db_clean):
    """Sería la puerta de atrás para usar material que Calidad retuvo (M31/M23)."""
    _sembrar()
    try:
        _lote('L-LIBRE', 500, '2027-01-31')
        _lote('L-CUAR', 500, '2027-01-31', estado='CUARENTENA')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-CUAR': 100}})
        assert r.status_code >= 400, 'dejó consumir un lote en cuarentena: %s' % r.data[:200]
        assert not _salidas(), 'igual descontó: %r' % (_salidas(),)
        d = r.get_json() or {}
        assert 'CUAR' in str(d).upper() or 'retenido' in str(d).lower() \
            or 'no se puede usar' in str(d).lower(), \
            'el rechazo no dice por qué: %r' % (d,)
    finally:
        _limpiar()


def test_un_reparto_NO_puede_consumir_un_lote_VENCIDO_por_fecha(app, db_clean):
    """El cron que marca vencidos corre una vez al día: el filtro por FECHA es el que cierra esa
    ventana, y el reparto tiene que respetarlo igual que el FEFO (M25)."""
    _sembrar()
    try:
        _lote('L-OK', 500, '2029-01-31')
        _lote('L-VENC', 500, '2020-01-31')       # vencido por fecha, el cron aún no lo marcó
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-VENC': 100}})
        assert r.status_code >= 400, 'dejó consumir un lote vencido: %s' % r.data[:200]
        assert not _salidas(), 'igual descontó: %r' % (_salidas(),)
    finally:
        _limpiar()


def test_no_se_puede_asignar_a_un_lote_mas_de_lo_que_tiene(app, db_clean):
    _sembrar()
    try:
        _lote('L-CHICO', 40, '2027-01-31')
        _lote('L-GRANDE', 500, '2028-01-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-CHICO': 100}})
        assert r.status_code >= 400, r.data[:200]
        assert not _salidas(), 'descontó más de lo que el lote tenía'
    finally:
        _limpiar()


def test_un_reparto_que_NO_CUADRA_se_rechaza(app, db_clean):
    """Un reparto que no cuadra es peor que ninguno porque se ve resuelto, y con eso se
    descuenta: faltarían gramos sin que nadie se entere hasta el piso (M195)."""
    _sembrar()
    try:
        _lote('L-A', 500, '2027-01-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-A': 70}})       # pide 100
        assert r.status_code >= 400, 'aceptó un reparto que no cuadra: %s' % r.data[:200]
        assert not _salidas(), 'descontó un reparto incompleto: %r' % (_salidas(),)
        assert '30' in str(r.get_json() or {}) or 'cuadra' in str(r.get_json() or {}).lower(), \
            'el rechazo no dice cuánto falta: %r' % (r.get_json(),)
    finally:
        _limpiar()


def test_un_reparto_de_MAS_tambien_se_rechaza(app, db_clean):
    """Sobrar tampoco cuadra: descontaría material que la fórmula no pide."""
    _sembrar()
    try:
        _lote('L-A', 500, '2027-01-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-A': 150}})      # pide 100
        assert r.status_code >= 400, r.data[:200]
        assert not _salidas()
    finally:
        _limpiar()


def test_un_lote_INVENTADO_no_pasa(app, db_clean):
    """Escribir un lote que no existe no puede crear stock de la nada."""
    _sembrar()
    try:
        _lote('L-A', 500, '2027-01-31')
        c = _login(app)
        r = _fabricar(c, reparto={_COD: {'L-QUE-NO-EXISTE': 100}})
        assert r.status_code >= 400, r.data[:200]
        assert not _salidas()
    finally:
        _limpiar()


def test_el_rechazo_NO_cae_a_FEFO_en_silencio(app, db_clean):
    """Si al rechazar el reparto se descontara por FEFO, la pantalla habría prometido una cosa y
    el kardex hecho otra -- que es justo lo que este reparto viene a evitar."""
    _sembrar()
    try:
        _lote('L-VIEJO', 500, '2027-01-31')
        _lote('L-CUAR', 500, '2027-01-31', estado='CUARENTENA')
        c = _login(app)
        _fabricar(c, reparto={_COD: {'L-CUAR': 100}})
        assert not _salidas(), \
            'rechazó el reparto y descontó por FEFO igual: %r' % (_salidas(),)
    finally:
        _limpiar()


# ───────────── el reparto y el FEFO comparten la MISMA lista ─────────────

def test_los_DOS_miran_la_misma_lista_de_lotes(app, db_clean):
    """Si fueran dos consultas, el día que una se ajuste -- un estado más, la guarda de
    vencimiento por fecha -- la otra dejaría pasar lo que la primera bloquea, y el reparto sería
    la puerta de atrás (M1/M3/M31)."""
    import io as _io
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = _io.open(os.path.join(raiz, 'api', 'blueprints', 'programacion.py'),
                   encoding='utf-8').read()
    assert 'def _lotes_disponibles_fefo(' in src, 'no existe el punto único'
    i = src.find('def _distribuir_fefo(')
    j = src.find('\ndef ', i + 10)
    cuerpo_fefo = src[i:j if j > i else i + 6000]
    assert '_lotes_disponibles_fefo(' in cuerpo_fefo, \
        'el FEFO volvió a tener su propia consulta de lotes'
    i2 = src.find('def _distribuir_con_reparto(')
    j2 = src.find('\ndef ', i2 + 10)
    cuerpo_rep = src[i2:j2 if j2 > i2 else i2 + 6000]
    assert '_lotes_disponibles_fefo(' in cuerpo_rep, \
        'el reparto valida contra otra lista que el FEFO: puerta de atrás'
