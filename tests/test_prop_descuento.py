"""25-jul-2026 · TEST DE PROPIEDADES del descuento de MP en producción.

Prueba por los ENDPOINTS REALES (POST /api/produccion y POST /api/produccion/simular)
que el descuento de materia prima es EXACTO. NO llama helpers internos: todo entra por
HTTP, igual que lo hace Fabricación en la app.

Propiedades demostradas:
  P1 · CONSERVACIÓN — Σ Salidas insertadas == Σ requerimiento de la fórmula
       (% × kg × 1000), tolerancia 0.01 g.
  P2 · FEFO REAL — sale de lotes reales, vence-primero-se-consume-primero, reparte
       entre varios lotes cuando uno no alcanza, y ningún lote queda en negativo.
  P3 · RECHAZO LIMPIO — si el stock no alcanza NO se escribe nada (kardex intacto,
       sin fila en producciones ni en produccion_programada).
  P4 · PARIDAD SIMULADOR — "Verificar stock" da el MISMO veredicto que el descuento
       real, en todos los escenarios (M5: el número que se muestra es el que decide).
       ⚠ ESTA PROPIEDAD ESTÁ EN ROJO A PROPÓSITO (no es un test flaky · 25-jul):
       el escenario AGUANOM la rompe. El simulador da por INFINITA a cualquier MP
       cuyo nombre empiece por "AGUA " (inventario.py:3425-3427
       `if _n == 'AGUA' or _n.startswith('AGUA '): return True`), mientras el
       descuento real solo salta el stock si `controla_stock=0` o si el nombre está
       en `_MP_UNLIMITED` (programacion.py:662 · las 6 aguas del lab). Una MP
       COMPRADA con nombre de agua (agua de rosas / micelar / termal / floral) sale
       "factible" en Verificar Stock y luego el POST devuelve 422. Dirección
       fail-safe (no descuenta de más) pero viola M5. NO ablandar el test: el fix va
       en el simulador (que reconozca solo las aguas del lab / controla_stock=0).
  P5 · ESTADOS RETENIDOS — CUARENTENA / CUARENTENA_EXTENDIDA / VENCIDO / RECHAZADO /
       BLOQUEADO / AGOTADO nunca se consumen, sin importar el case del texto (M23).
  P6 · VENCIDO POR FECHA — un lote vencido por fecha no se consume aunque el cron
       diario todavía no lo haya marcado VENCIDO (M25).
  P7 · CONSOLIDACIÓN — dos filas de fórmula que resuelven al MISMO material de bodega
       se suman ANTES de validar y descontar (fix P0 25-jul · antes cada fila miraba
       el stock completo → doble descuento → lote en negativo).
  P8 · AGUA (controla_stock=0) — no bloquea la producción ni mueve el kardex (mig 218).

Convenciones del repo: fixtures de tests/conftest.py, BD SQLite temporal en
os.environ['DB_PATH'], siembra por sqlite3 directo con try/finally y conexiones
cerradas SIEMPRE (si no, la BD queda locked para el resto del archivo).
"""
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers

PREF_MAT = 'MPPROP'
PREF_PROD = 'PROP-DESC'
HOY = date.today()

# Los 6 estados que el canónico excluye · con el case REVUELTO a propósito (M23)
ESTADOS_NO_PRODUCIBLES = [
    'cuarentena',
    'Cuarentena_Extendida',
    'vencido',
    'Rechazado',
    'bloqueado',
    'AgOtAdO',
]


# ─────────────────────────── utilidades de BD ────────────────────────────────
def _d(dias):
    """Fecha ISO a N días de hoy (evita que el test se pudra con el calendario)."""
    return (HOY + timedelta(days=dias)).isoformat()


def _conn():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=20)


def _exec(sql, params=()):
    conn = _conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _rows(sql, params=()):
    conn = _conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _one(sql, params=()):
    r = _rows(sql, params)
    return r[0][0] if r else None


def _limpiar():
    """Borra TODO lo sembrado por este archivo (prefijos propios · idempotente)."""
    conn = _conn()
    try:
        conn.execute("DELETE FROM movimientos WHERE material_id LIKE ?", (PREF_MAT + '%',))
        conn.execute("DELETE FROM formula_items WHERE producto_nombre LIKE ?", (PREF_PROD + '%',))
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre LIKE ?", (PREF_PROD + '%',))
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE ?", (PREF_MAT + '%',))
        conn.execute("DELETE FROM producciones WHERE producto LIKE ?", (PREF_PROD + '%',))
        conn.execute("DELETE FROM produccion_programada WHERE producto LIKE ?", (PREF_PROD + '%',))
        conn.commit()
    finally:
        conn.close()


def _material(cod, nombre, inci=None, controla=1):
    _exec("INSERT OR REPLACE INTO maestro_mps "
          "(codigo_mp, nombre_inci, nombre_comercial, activo, controla_stock) "
          "VALUES (?,?,?,1,?)", (cod, inci or nombre, nombre, controla))


def _formula(prod, filas, lote_kg=10):
    """filas = [(codigo, nombre, porcentaje), ...]"""
    conn = _conn()
    try:
        conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,))
        conn.execute("INSERT INTO formula_headers "
                     "(producto_nombre, unidad_base_g, lote_size_kg, activo, fecha_creacion) "
                     "VALUES (?,?,?,1,datetime('now'))", (prod, lote_kg * 1000, lote_kg))
        for cod, nom, pct in filas:
            conn.execute("INSERT INTO formula_items "
                         "(producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                         "VALUES (?,?,?,?,0)", (prod, cod, nom, pct))
        conn.commit()
    finally:
        conn.close()


def _lote(cod, nombre, lote, gramos, estado='VIGENTE', vence=None):
    _exec("INSERT INTO movimientos "
          "(material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, "
          " fecha_vencimiento, operador) VALUES (?,?,?,'Entrada',?,?,?,?,'seed-prop')",
          (cod, nombre, gramos, _d(-10), lote, estado, vence))


def _salidas(lote_ref):
    """Movimientos de Salida que ESA producción escribió (marca FEFO:/UNLIMITED:<ref>:)."""
    return _rows("SELECT material_id, COALESCE(lote,''), cantidad FROM movimientos "
                 "WHERE tipo='Salida' AND COALESCE(observaciones,'') LIKE ?",
                 ('%:' + lote_ref + ':%',))


def _neto_por_lote(cod):
    rows = _rows(
        "SELECT COALESCE(lote,''), SUM(CASE "
        "  WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
        "  WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END) "
        "FROM movimientos WHERE material_id=? GROUP BY lote", (cod,))
    return {r[0]: float(r[1] or 0) for r in rows}


def _total_movimientos():
    return int(_one("SELECT COUNT(*) FROM movimientos") or 0)


# ─────────────────────────── utilidades HTTP ─────────────────────────────────
def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f'login falló ({user}): {r.status_code}'
    return c


def _producir(cli, producto, kg, operador='sebastian'):
    r = cli.post('/api/produccion',
                 json={'producto': producto, 'cantidad_kg': kg,
                       'operador': operador, 'presentacion': 'x'},
                 headers=csrf_headers())
    return r.status_code, (r.get_json() or {})


def _simular(cli, producto, kg):
    r = cli.post('/api/produccion/simular',
                 json={'producto': producto, 'cantidad_kg': kg},
                 headers=csrf_headers())
    return r.status_code, (r.get_json() or {})


# ═══════════════════════════ P1 · CONSERVACIÓN ═══════════════════════════════
def test_p1_conservacion_suma_salidas_igual_requerimiento(app, db_clean):
    """Para toda producción ACEPTADA: Σ Salidas == Σ (% × kg × 1000) ± 0.01 g.

    Se corre sobre 3 formas de fórmula/tamaño de lote distintas y con los lotes
    partidos a propósito (el 1º NUNCA alcanza) para que el reparto FEFO también
    tenga que conservar la masa.
    """
    _limpiar()
    try:
        cli = _login(app)
        casos = [
            (8.0,  [('C1', 12.5), ('C2', 3.75), ('C3', 0.625), ('C4', 0.333)]),
            (1.0,  [('C5', 50.0), ('C6', 2.5)]),
            (12.5, [('C7', 4.0), ('C8', 0.08)]),
        ]
        for idx, (kg, filas) in enumerate(casos):
            prod = f'{PREF_PROD} CONSERVA {idx}'
            ff = []
            for suf, pct in filas:
                cod, nom = f'{PREF_MAT}-{suf}', f'Prop Material {suf}'
                req = pct / 100.0 * kg * 1000
                _material(cod, nom)
                _lote(cod, nom, f'L-{suf}-A', round(req * 0.4, 2), vence=_d(120))
                _lote(cod, nom, f'L-{suf}-B', round(req * 3 + 100, 2), vence=_d(400))
                ff.append((cod, nom, pct))
            _formula(prod, ff, lote_kg=kg)

            st, js = _producir(cli, prod, kg)
            assert st == 201, f'{prod}: esperaba 201 · vino {st} · {js}'
            ref = js.get('lote')
            assert ref, f'{prod}: la respuesta no trae lote · {js}'

            esperado = sum(pct / 100.0 * kg * 1000 for _s, pct in filas)
            real = sum(float(r[2]) for r in _salidas(ref))
            assert abs(real - esperado) <= 0.01, (
                f'{prod}: Σ Salidas={real} vs Σ requerimiento={esperado} '
                f'(dif {abs(real - esperado)} g)')

            # y material por material (la conservación global podría compensar errores)
            for suf, pct in filas:
                cod = f'{PREF_MAT}-{suf}'
                esp_m = pct / 100.0 * kg * 1000
                real_m = sum(float(r[2]) for r in _salidas(ref) if r[0] == cod)
                assert abs(real_m - esp_m) <= 0.01, (
                    f'{prod}/{cod}: descontó {real_m} g y la fórmula pide {esp_m} g')
    finally:
        _limpiar()


# ═══════════════════════ P2 · FEFO real · reparto · sin negativos ════════════
def test_p2_fefo_ordena_por_vencimiento_reparte_y_no_deja_negativos(app, db_clean):
    """El descuento sale de lotes REALES, el que vence primero se consume primero,
    reparte cuando un lote no alcanza y ningún lote queda en negativo."""
    _limpiar()
    try:
        prod = f'{PREF_PROD} FEFO'
        cod, nom = f'{PREF_MAT}-FEFO', 'Prop Material Fefo'
        _material(cod, nom)
        # sembrados DESORDENADOS a propósito: el orden lo tiene que poner el FEFO
        _lote(cod, nom, 'L-TARDE', 1000, vence=_d(500))
        _lote(cod, nom, 'L-PRONTO', 300, vence=_d(20))
        _lote(cod, nom, 'L-MEDIO', 400, vence=_d(120))
        _lote(cod, nom, 'L-SINVENC', 900, vence=None)
        _formula(prod, [(cod, nom, 5.0)])   # 5% × 10 kg = 500 g

        cli = _login(app)
        st, js = _producir(cli, prod, 10)
        assert st == 201, f'esperaba 201 · vino {st} · {js}'
        ref = js['lote']

        por_lote = {}
        for _mid, lote, cant in _salidas(ref):
            por_lote[lote] = por_lote.get(lote, 0.0) + float(cant)

        # 1) el que vence PRIMERO se agota primero
        assert abs(por_lote.get('L-PRONTO', 0) - 300) <= 0.01, (
            f'L-PRONTO (vence primero) debía entregar sus 300 g · {por_lote}')
        # 2) reparte el resto al SIGUIENTE por vencimiento
        assert abs(por_lote.get('L-MEDIO', 0) - 200) <= 0.01, (
            f'el faltante (200 g) debía salir de L-MEDIO · {por_lote}')
        # 3) no toca los que vencen después ni el sin-vencimiento (van al final)
        assert 'L-TARDE' not in por_lote and 'L-SINVENC' not in por_lote, (
            f'FEFO consumió lotes que vencen después · {por_lote}')
        # 4) todo salió de lotes REALES (ninguna Salida sin lote / S/L)
        assert all(l and l != 'S/L' for _m, l, _c in _salidas(ref)), _salidas(ref)
        # 5) NINGÚN lote en negativo
        netos = _neto_por_lote(cod)
        assert all(v >= -0.01 for v in netos.values()), f'lote en negativo · {netos}'
        assert abs(netos.get('L-PRONTO', 0)) <= 0.01, netos
        assert abs(netos.get('L-MEDIO', 0) - 200) <= 0.01, netos

        # ── reparto DURO: 24 lotes de 41.67 g para cubrir 1000 g exactos ─────
        # estresa la acumulación de round() del loop FEFO (23 lotes completos +
        # una fracción) y el guard de no insertar movimientos de 0 g (M18).
        prod = f'{PREF_PROD} FEFO MULTI'
        cod, nom = f'{PREF_MAT}-FEFOM', 'Prop Material Fefo Multi'
        _material(cod, nom, inci='PROP INCI FEFOM')
        for i in range(24):
            _lote(cod, nom, f'L-M{i:02d}', 41.67, vence=_d(30 + i))
        _formula(prod, [(cod, nom, 10.0)])   # 10% × 10 kg = 1000 g
        st, js = _producir(cli, prod, 10)
        assert st == 201, f'{st} · {js}'
        sal = _salidas(js['lote'])
        total = sum(float(r[2]) for r in sal)
        assert abs(total - 1000.0) <= 0.01, (
            f'reparto entre 24 lotes perdió masa: descontó {total} de 1000 g')
        assert all(float(r[2]) > 0 for r in sal), (
            f'se escribió una Salida de 0 g (el trigger PG la rechaza · M18) · {sal}')
        assert len(sal) == 24, (
            f'debía tocar los 24 lotes en orden de vencimiento · tocó {len(sal)}')
        netos = _neto_por_lote(cod)
        assert all(v >= -0.01 for v in netos.values()), f'lote en negativo · {netos}'
        assert abs(sum(netos.values()) - (24 * 41.67 - 1000.0)) <= 0.01, netos
    finally:
        _limpiar()


# ═══════════════════════ P3 · rechazo limpio (nada escrito) ══════════════════
def test_p3_stock_insuficiente_no_escribe_nada(app, db_clean):
    """Si el stock no alcanza: 422 y el kardex queda EXACTAMENTE igual."""
    _limpiar()
    try:
        prod = f'{PREF_PROD} FALTA'
        cod, nom = f'{PREF_MAT}-FALTA', 'Prop Material Falta'
        _material(cod, nom)
        _lote(cod, nom, 'L-FALTA-1', 100, vence=_d(300))
        _formula(prod, [(cod, nom, 5.0)])   # pide 500 g y solo hay 100 g

        cli = _login(app)
        movs_antes = _total_movimientos()
        stock_antes = sum(_neto_por_lote(cod).values())

        st, js = _producir(cli, prod, 10)
        assert st == 422, f'esperaba 422 (stock insuficiente) · vino {st} · {js}'

        assert _total_movimientos() == movs_antes, (
            'el kardex se movió en una producción RECHAZADA '
            f'({movs_antes} → {_total_movimientos()})')
        assert abs(sum(_neto_por_lote(cod).values()) - stock_antes) <= 1e-9, (
            'el stock del material cambió en una producción rechazada')
        assert _one("SELECT COUNT(*) FROM producciones WHERE producto=?", (prod,)) == 0, (
            'quedó una fila en producciones tras el rechazo')
        assert _one("SELECT COUNT(*) FROM produccion_programada WHERE producto=?",
                    (prod,)) == 0, 'quedó espejo en produccion_programada tras el rechazo'
    finally:
        _limpiar()


# ═══════════════════ P4 · simulador == descuento real, SIEMPRE ═══════════════
def _nombre_mat(suf):
    """S9 = MP COMPRADA con nombre de agua (agua de rosas): mismo trato que cualquier MP."""
    return 'Agua de Rosas Prop' if suf == 'S9' else f'Prop Material {suf}'


def test_p4_simulador_da_el_mismo_veredicto_que_el_descuento(app, db_clean):
    """Veredicto de /api/produccion/simular == veredicto de POST /api/produccion.

    factible=True  ⟺  el POST real registra (201)
    factible=False ⟺  el POST real rechaza (422)

    ⚠ FALLA HOY en el escenario AGUANOM (divergencia REAL, ver docstring del módulo).
    Los otros 8 escenarios pasan. Dejado en rojo a propósito.
    """
    _limpiar()
    try:
        cli = _login(app)
        # cada escenario: (tag, filas_formula, lotes, kg, factible_esperado)
        # filas_formula: [(sufijo_cod, pct, controla_stock)]
        # lotes:         [(sufijo_cod, lote, g, estado, vence)]
        escenarios = [
            ('SOBRA',  [('S1', 5.0, 1)], [('S1', 'L1', 5000, 'VIGENTE', _d(300))], 10, True),
            ('EXACTO', [('S2', 5.0, 1)], [('S2', 'L1', 500, 'VIGENTE', _d(300))], 10, True),
            ('CORTO',  [('S3', 5.0, 1)], [('S3', 'L1', 499, 'VIGENTE', _d(300))], 10, False),
            ('CUAR',   [('S4', 5.0, 1)], [('S4', 'L1', 5000, 'cuarentena', _d(300))], 10, False),
            ('VENCE',  [('S5', 5.0, 1)], [('S5', 'L1', 5000, 'VIGENTE', _d(-30))], 10, False),
            ('SINLOTE', [('S6', 5.0, 1)], [('S6', 'S/L', 5000, 'VIGENTE', _d(300))], 10, False),
            # dos filas al MISMO material: cada una cabe sola (300 y 200) pero la suma no
            ('DOBLE',  [('S7', 3.0, 1), ('S7', 2.0, 1)],
             [('S7', 'L1', 400, 'VIGENTE', _d(300))], 10, False),
            # agua (controla_stock=0) sin una gota de stock → igual es factible
            ('AGUA',   [('S8', 70.0, 0)], [], 10, True),
            # MP COMPRADA cuyo nombre empieza por "Agua " (agua de rosas / micelar /
            # termal / floral): controla_stock=1 → el descuento real EXIGE stock.
            # El simulador la da por infinita solo por el prefijo del nombre
            # (inventario.py:3426 `_n.startswith('AGUA ')`) → veredictos distintos.
            ('AGUANOM', [('S9', 5.0, 1)], [], 10, False),
        ]
        divergencias = []
        for tag, filas, lotes, kg, esperado in escenarios:
            prod = f'{PREF_PROD} PARIDAD {tag}'
            ff = []
            for suf, pct, controla in filas:
                cod, nom = f'{PREF_MAT}-{suf}', _nombre_mat(suf)
                _material(cod, nom, inci=f'PROP INCI {suf}', controla=controla)
                ff.append((cod, nom, pct))
            for suf, lote, g, estado, vence in lotes:
                cod, nom = f'{PREF_MAT}-{suf}', _nombre_mat(suf)
                _lote(cod, nom, lote, g, estado=estado, vence=vence)
            _formula(prod, ff, lote_kg=kg)

            st_sim, js_sim = _simular(cli, prod, kg)
            assert st_sim == 200, f'{tag}: simular devolvió {st_sim} · {js_sim}'
            factible = bool(js_sim.get('factible'))
            if tag == 'DOBLE':
                # el simulador tiene que SUMAR las dos filas (500 g), no mirarlas
                # sueltas (300 y 200, que caben las dos en 400 g de stock)
                ings = js_sim.get('ingredientes') or []
                assert len(ings) == 1, f'DOBLE: el simulador no consolidó · {ings}'
                assert abs(float(ings[0].get('g_requerido') or 0) - 500) <= 0.01, (
                    f'DOBLE: el simulador pide {ings[0].get("g_requerido")} g y son 500 · {ings}')

            st_post, js_post = _producir(cli, prod, kg)
            assert st_post in (201, 422), f'{tag}: POST devolvió {st_post} · {js_post}'
            acepta = (st_post == 201)

            if factible != acepta:
                divergencias.append(
                    f'{tag}: simular.factible={factible} pero el descuento real '
                    f'{"ACEPTÓ" if acepta else "RECHAZÓ"} (HTTP {st_post})')
            if acepta != esperado:
                divergencias.append(
                    f'{tag}: el descuento real dio {st_post} y se esperaba '
                    f'{"201" if esperado else "422"} · {js_post}')
        assert not divergencias, 'PARIDAD ROTA:\n  - ' + '\n  - '.join(divergencias)
    finally:
        _limpiar()


# ═══════════ P5 · estados retenidos, sin importar el case del texto ══════════
def test_p5_estados_retenidos_nunca_se_consumen(app, db_clean):
    """CUARENTENA / CUARENTENA_EXTENDIDA / VENCIDO / RECHAZADO / BLOQUEADO / AGOTADO
    no se consumen ni con el case revuelto (M23: el filtro va con UPPER)."""
    _limpiar()
    try:
        cli = _login(app)
        fallos = []
        for i, estado in enumerate(ESTADOS_NO_PRODUCIBLES):
            tag = f'E{i}'
            prod = f'{PREF_PROD} ESTADO {tag}'
            cod, nom = f'{PREF_MAT}-{tag}', f'Prop Material {tag}'
            _material(cod, nom, inci=f'PROP INCI {tag}')
            _lote(cod, nom, f'L-{tag}', 5000, estado=estado, vence=_d(300))
            _formula(prod, [(cod, nom, 5.0)])   # pide 500 g

            st, js = _producir(cli, prod, 10)
            if st != 422:
                fallos.append(f"estado_lote='{estado}': el POST dio {st} (debía ser 422) · {js}")
            salidas = _rows("SELECT COUNT(*) FROM movimientos WHERE material_id=? AND tipo='Salida'",
                            (cod,))[0][0]
            if salidas:
                fallos.append(f"estado_lote='{estado}': se escribieron {salidas} Salidas "
                              "sobre un lote NO producible")
        assert not fallos, 'ESTADOS RETENIDOS CONSUMIDOS:\n  - ' + '\n  - '.join(fallos)

        # mezcla: un lote retenido enorme + uno VIGENTE justo → solo se toca el VIGENTE
        prod = f'{PREF_PROD} ESTADO MIX'
        cod, nom = f'{PREF_MAT}-MIX', 'Prop Material Mix'
        _material(cod, nom, inci='PROP INCI MIX')
        _lote(cod, nom, 'L-MIX-BLOQ', 5000, estado='Bloqueado', vence=_d(300))
        _lote(cod, nom, 'L-MIX-OK', 500, estado='VIGENTE', vence=_d(300))
        _formula(prod, [(cod, nom, 5.0)])
        st, js = _producir(cli, prod, 10)
        assert st == 201, f'con un lote VIGENTE suficiente debía producir · {st} · {js}'
        por_lote = {}
        for _m, lote, cant in _salidas(js['lote']):
            por_lote[lote] = por_lote.get(lote, 0.0) + float(cant)
        assert abs(por_lote.get('L-MIX-OK', 0) - 500) <= 0.01, por_lote
        assert 'L-MIX-BLOQ' not in por_lote, f'consumió el lote BLOQUEADO · {por_lote}'
    finally:
        _limpiar()


# ═════════════════ P6 · vencido POR FECHA aunque el cron no corrió ═══════════
def test_p6_vencido_por_fecha_no_se_consume_aunque_el_cron_no_marcó(app, db_clean):
    """El lote sigue 'VIGENTE' (el cron diario no ha corrido) pero su fecha ya pasó:
    ni el simulador lo promete ni el FEFO lo consume (M25)."""
    _limpiar()
    try:
        cli = _login(app)
        # (a) vencido ayer, estado VIGENTE → NO se puede producir
        prod = f'{PREF_PROD} VENC FECHA'
        cod, nom = f'{PREF_MAT}-VF', 'Prop Material Venc Fecha'
        _material(cod, nom, inci='PROP INCI VF')
        _lote(cod, nom, 'L-VF-VENCIDO', 5000, estado='VIGENTE', vence=_d(-1))
        _formula(prod, [(cod, nom, 5.0)])

        _st_sim, js_sim = _simular(cli, prod, 10)
        assert not js_sim.get('factible'), (
            f'el simulador promete stock de un lote vencido por fecha · {js_sim}')
        st, js = _producir(cli, prod, 10)
        assert st == 422, f'consumió material vencido por fecha · {st} · {js}'
        assert _one("SELECT COUNT(*) FROM movimientos WHERE material_id=? AND tipo='Salida'",
                    (cod,)) == 0

        # (b) control: vence mañana / sin vencimiento → SÍ se consume (no sobre-bloquea)
        for tag, vence in (('MAN', _d(1)), ('NUL', None)):
            prod2 = f'{PREF_PROD} VENC OK {tag}'
            cod2, nom2 = f'{PREF_MAT}-VOK{tag}', f'Prop Material Vok {tag}'
            _material(cod2, nom2, inci=f'PROP INCI VOK {tag}')
            _lote(cod2, nom2, f'L-VOK-{tag}', 5000, estado='VIGENTE', vence=vence)
            _formula(prod2, [(cod2, nom2, 5.0)])
            st2, js2 = _producir(cli, prod2, 10)
            assert st2 == 201, (
                f'lote con vencimiento {vence!r} NO debía bloquearse · {st2} · {js2}')
    finally:
        _limpiar()


# ═══════ P7 · dos filas al mismo material de bodega se CONSOLIDAN (fix P0) ═══
def test_p7_dos_filas_mismo_material_se_consolidan(app, db_clean):
    """Fix 25-jul: el requerimiento se SUMA por código de bodega ANTES de validar y
    descontar. Antes cada fila hacía su propio pre-check contra los MISMOS lotes →
    ambas veían el stock completo → doble descuento y lote en NEGATIVO."""
    _limpiar()
    try:
        cli = _login(app)

        # (a) mismo código dos veces (fase A + fase B) · 3% + 2% de 10 kg = 500 g
        prod = f'{PREF_PROD} CONSOL A'
        cod, nom = f'{PREF_MAT}-CONA', 'Prop Material Consol A'
        _material(cod, nom, inci='PROP INCI CONA')
        _lote(cod, nom, 'L-CONA', 700, vence=_d(300))
        _formula(prod, [(cod, nom, 3.0), (cod, nom, 2.0)])
        st, js = _producir(cli, prod, 10)
        assert st == 201, f'{st} · {js}'
        total = sum(float(r[2]) for r in _salidas(js['lote']))
        assert abs(total - 500) <= 0.01, f'debía descontar 500 g (3%+2%) y descontó {total}'
        netos = _neto_por_lote(cod)
        assert abs(netos.get('L-CONA', 0) - 200) <= 0.01, netos
        assert all(v >= -0.01 for v in netos.values()), f'lote en negativo · {netos}'

        # (b) cada fila CABE sola (300 y 200) pero la SUMA no (500 > 400) → rechazo limpio
        prod = f'{PREF_PROD} CONSOL B'
        cod, nom = f'{PREF_MAT}-CONB', 'Prop Material Consol B'
        _material(cod, nom, inci='PROP INCI CONB')
        _lote(cod, nom, 'L-CONB', 400, vence=_d(300))
        _formula(prod, [(cod, nom, 3.0), (cod, nom, 2.0)])
        movs_antes = _total_movimientos()
        st, js = _producir(cli, prod, 10)
        assert st == 422, (
            'dos filas del mismo material pasaron el pre-check por separado '
            f'(doble descuento) · {st} · {js}')
        falt = js.get('faltantes') or []
        assert len(falt) == 1 and abs(float(falt[0].get('requerido_g') or 0) - 500) <= 0.01, (
            f'el faltante debe reportar el requerimiento SUMADO (500 g) · {falt}')
        assert _total_movimientos() == movs_antes, 'escribió kardex en un rechazo'
        assert abs(_neto_por_lote(cod).get('L-CONB', 0) - 400) <= 1e-9

        # (c) DOS CÓDIGOS distintos que el resolver colapsa al mismo material de bodega
        #     (mismo INCI · el de fórmula sin stock) → también se consolidan
        prod = f'{PREF_PROD} CONSOL C'
        cod_f, nom_f = f'{PREF_MAT}-CONCF', 'Prop Material Consol C Formula'
        cod_b, nom_b = f'{PREF_MAT}-CONCB', 'Prop Material Consol C Bodega'
        _material(cod_f, nom_f, inci='PROP INCI CONC')
        _material(cod_b, nom_b, inci='PROP INCI CONC')
        _lote(cod_b, nom_b, 'L-CONC', 400, vence=_d(300))   # stock SOLO en el de bodega
        _formula(prod, [(cod_f, nom_f, 3.0), (cod_b, nom_b, 2.0)])
        movs_antes = _total_movimientos()
        st, js = _producir(cli, prod, 10)
        assert st == 422, (
            'dos códigos que resuelven al MISMO material de bodega pasaron el pre-check '
            f'por separado · {st} · {js}')
        falt = js.get('faltantes') or []
        assert len(falt) == 1, f'debe haber UN faltante (el material consolidado) · {falt}'
        assert falt[0].get('material_id') == cod_b, (
            f'el faltante debe salir bajo el código de BODEGA resuelto · {falt}')
        assert abs(float(falt[0].get('requerido_g') or 0) - 500) <= 0.01, (
            f'el faltante debe reportar el requerimiento SUMADO (500 g) · {falt}')
        assert _total_movimientos() == movs_antes, 'escribió kardex en un rechazo'
        assert abs(_neto_por_lote(cod_b).get('L-CONC', 0) - 400) <= 1e-9
    finally:
        _limpiar()


# ═════════════ P8 · agua (controla_stock=0) no bloquea ni mueve kardex ═══════
def test_p8_agua_no_bloquea_ni_mueve_kardex(app, db_clean):
    """AGUA del lab (mig 218 · controla_stock=0): se fabrica en casa, no tiene stock
    en bodega, no puede frenar una producción y NO debe dejar movimientos (si los
    dejara, acumularía stock negativo eterno)."""
    _limpiar()
    try:
        prod = f'{PREF_PROD} AGUA'
        cod_agua, nom_agua = f'{PREF_MAT}-AGUA', 'Agua Desionizada Prop'
        cod_mp, nom_mp = f'{PREF_MAT}-AGUAMP', 'Prop Material Con Agua'
        _material(cod_agua, nom_agua, inci='AQUA PROP', controla=0)
        _material(cod_mp, nom_mp, inci='PROP INCI AGUAMP', controla=1)
        # el agua NO tiene ni un gramo en el kardex · la MP real sí
        _lote(cod_mp, nom_mp, 'L-AGUAMP', 1000, vence=_d(300))
        _formula(prod, [(cod_agua, nom_agua, 70.0), (cod_mp, nom_mp, 5.0)])

        cli = _login(app)
        _st_sim, js_sim = _simular(cli, prod, 10)
        assert js_sim.get('factible'), f'el agua bloqueó el simulador · {js_sim}'

        st, js = _producir(cli, prod, 10)
        assert st == 201, f'el agua sin stock bloqueó la producción · {st} · {js}'

        assert _one("SELECT COUNT(*) FROM movimientos WHERE material_id=?", (cod_agua,)) == 0, (
            'el agua movió el kardex (acumularía stock negativo · mig 218)')
        real = sum(float(r[2]) for r in _salidas(js['lote']) if r[0] == cod_mp)
        assert abs(real - 500) <= 0.01, f'la MP real debía descontar 500 g · descontó {real}'
        assert abs(_neto_por_lote(cod_mp).get('L-AGUAMP', 0) - 500) <= 0.01
    finally:
        _limpiar()
