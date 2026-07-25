"""TEST DE PROPIEDADES · el cálculo de Abastecimiento (MRP) por los ENDPOINTS REALES.

No prueba funciones internas: golpea `/api/abastecimiento/consumo-horizontes` (la PANTALLA),
`/api/programacion/mps-deficit` y `POST /api/programacion/generar-oc` (la COMPRA) y
`/api/plan/factibilidad` (lo que se puede PRODUCIR).

Propiedades demostradas:
  P1 · ADITIVIDAD      · N lotes ⇒ consumo = N × requerimiento (1/2/3 lotes · misma y distinta fecha)
  P2 · MONOTONÍA       · consumo(15) ≤ consumo(30) ≤ consumo(60) ≤ consumo(90) · siempre
  P3 · DÉFICIT/NETO    · deficit = max(0, consumo − stock − cuarentena)
                         neto_a_pedir = max(0, deficit − pendiente)  (cada término verificado aparte)
  P4 · PARIDAD DURA    · pantalla == mps-deficit == cantidad escrita por generar-OC (incl. backlog atrasado)
                         ⚠ la segunda mitad (POST generar-oc) FALLA: el endpoint da 500 · ver su docstring
  P5 · B2B UNA VEZ     · pedido pendiente cuenta 1 vez · integrado a lote NO se cuenta doble
  P6 · AGUA            · MP con controla_stock=0 nunca aparece con déficit (ni se pide)
  P7 · CUARENTENA      · lo retenido NO es stock disponible para producir

Convenciones del repo: fixtures de tests/conftest.py, BD SQLite temporal en DB_PATH,
siembra con prefijo único 'QAPROP' y limpieza SIEMPRE en try/finally (conexiones cerradas).
"""
import os
import sqlite3

from .conftest import csrf_headers


# ──────────────────────────── infraestructura ────────────────────────────────

def _db():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _exec(sql, params=()):
    con = _db()
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def _run(pairs):
    """Ejecuta una lista de (sql, params) tolerando tablas/columnas ausentes."""
    con = _db()
    try:
        for sql, params in pairs:
            try:
                con.execute(sql, params)
            except sqlite3.OperationalError:
                pass
        con.commit()
    finally:
        con.close()


def _dias(n):
    """Modificador SQLite anclado a Colombia: +3 / -3 días."""
    return "%+d days" % int(n)


# ──────────────────────────────── siembra ────────────────────────────────────

def _seed_mp(codigo, nombre, controla_stock=1):
    """MP con nombre/INCI ÚNICOS · así `_resolver_material_bodega` la resuelve a sí misma
    (nada de colapsos por INCI/nombre con otra MP del maestro seed)."""
    _run([
        ("DELETE FROM maestro_mps WHERE codigo_mp=?", (codigo,)),
        ("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
         "controla_stock, tipo_material) VALUES (?,?,?,1,?,'MP')",
         (codigo, nombre, "INCI " + codigo, controla_stock)),
    ])


def _seed_formula(producto, lote_size_kg, items):
    """items = [(codigo_mp, nombre_mp, porcentaje)]"""
    _run([("DELETE FROM formula_items WHERE producto_nombre=?", (producto,)),
          ("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))])
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,?,1)",
          (producto, lote_size_kg))
    for cod, nom, pct in items:
        _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
              "porcentaje, cantidad_g_por_lote) VALUES (?,?,?,?,0)", (producto, cod, nom, pct))


def _programar(producto, dias, lotes=1, cantidad_kg=0, origen="eos_plan"):
    return _exec(
        "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, "
        "cantidad_kg, origen) VALUES (?, date('now','-5 hours',?), ?, 'pendiente', ?, ?)",
        (producto, _dias(dias), lotes, cantidad_kg, origen))


def _borrar_producciones(producto):
    _exec("DELETE FROM produccion_programada WHERE producto=?", (producto,))


def _mov(codigo, nombre, gramos, estado_lote="VIGENTE", lote=None):
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
          "lote, estado_lote, operador) VALUES (?,?,?,'Entrada', date('now'), ?, ?, 'qaprop')",
          (codigo, nombre, gramos, lote or ("LOTE-" + codigo), estado_lote))


def _sol_pendiente(numero, codigo, nombre, gramos):
    """Pendiente en compras: SOL 'Pendiente' de Materia Prima, SIN OC ligada."""
    _run([("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,)),
          ("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))])
    _exec("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, categoria) "
          "VALUES (?, date('now'), 'Pendiente', 'qaprop', 'Materia Prima')", (numero,))
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, cantidad_g) "
          "VALUES (?,?,?,?)", (numero, codigo, nombre, gramos))


def _pedido_b2b(producto, uds, ml, dias, cliente_id="9900"):
    return _exec(
        "INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, cantidad_uds, "
        "ml_unidad, fecha_estimada, estado, creado_por) "
        "VALUES (?, 'Cliente QAPROP', ?, ?, ?, date('now','-5 hours',?), 'pendiente', 'qaprop')",
        (cliente_id, producto, uds, ml, _dias(dias)))


def _limpiar(codigos=(), productos=(), sols=(), clientes=()):
    pairs = []
    for p in productos:
        pairs += [("DELETE FROM formula_items WHERE producto_nombre=?", (p,)),
                  ("DELETE FROM formula_headers WHERE producto_nombre=?", (p,)),
                  ("DELETE FROM produccion_programada WHERE producto=?", (p,)),
                  ("DELETE FROM pedidos_b2b_lote WHERE pedido_b2b_id IN "
                   "(SELECT id FROM pedidos_b2b WHERE producto_nombre=?)", (p,)),
                  ("DELETE FROM pedidos_b2b WHERE producto_nombre=?", (p,))]
    for cl in clientes:
        pairs.append(("DELETE FROM pedidos_b2b WHERE cliente_id=?", (cl,)))
    for s in sols:
        pairs += [("DELETE FROM solicitudes_compra_items WHERE numero=?", (s,)),
                  ("DELETE FROM solicitudes_compra WHERE numero=?", (s,))]
    for cod in codigos:
        pairs += [("DELETE FROM movimientos WHERE material_id=?", (cod,)),
                  ("DELETE FROM ordenes_compra_items WHERE codigo_mp=?", (cod,)),
                  ("DELETE FROM solicitudes_compra_items WHERE codigo_mp=?", (cod,)),
                  ("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))]
    _run(pairs)


# ─────────────────────────────── endpoints ───────────────────────────────────

def _pantalla(client, horizontes="15,30,60,90", tipo="mp"):
    r = client.get("/api/abastecimiento/consumo-horizontes?tipo=%s&horizontes=%s"
                   % (tipo, horizontes))
    assert r.status_code == 200, r.data
    return r.get_json()


def _fila(payload, codigo):
    for m in (payload.get("mps") or []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def _fila_mp(client, codigo, horizontes="15,30,60,90"):
    return _fila(_pantalla(client, horizontes), codigo)


def _oc_deficit(client, codigo):
    """Lo que el motor de COMPRA (mps-deficit · el mismo que alimenta generar-OC) pediría."""
    r = client.get("/api/programacion/mps-deficit")
    assert r.status_code == 200, r.data
    for m in (r.get_json().get("mps") or []):
        if str(m.get("codigo_mp") or "").upper() == codigo.upper():
            return float(m.get("deficit_g") or 0)
    return 0.0


# ═════════════════════════ P1 · ADITIVIDAD ═══════════════════════════════════

def test_p1_aditividad_lotes_misma_y_distinta_fecha(admin_client, db_clean):
    """N lotes ⇒ consumo = N × requerimiento. Probado con 1, 2 y 3 lotes,
    en la MISMA fecha y en fechas DISTINTAS, y con N en la columna `lotes`."""
    cod, nom = "MPQAPADD", "QAPROP Aditiva Uno"
    prod = "QAPROP ADITIVIDAD"
    POR_LOTE = 500.0                      # 10% × 5 kg × 1000
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 5, [(cod, nom, 10)])

        # (a) N filas de 1 lote en la MISMA fecha
        for n in (1, 2, 3):
            _borrar_producciones(prod)
            for _ in range(n):
                _programar(prod, 3)
            f = _fila_mp(admin_client, cod)
            assert f is not None, "la MP programada debe aparecer en Abastecimiento (n=%d)" % n
            assert abs(f["consumo"]["15"] - n * POR_LOTE) < 0.5, (
                "MISMA fecha · %d lotes deben sumar %.0f g · obtuve %s"
                % (n, n * POR_LOTE, f["consumo"]))

        # (b) N filas de 1 lote en fechas DISTINTAS (todas dentro de 15 d)
        for n in (1, 2, 3):
            _borrar_producciones(prod)
            for i in range(n):
                _programar(prod, 2 + i * 4)      # +2, +6, +10
            f = _fila_mp(admin_client, cod)
            assert f is not None, "n=%d" % n
            assert abs(f["consumo"]["15"] - n * POR_LOTE) < 0.5, (
                "fechas DISTINTAS · %d lotes deben sumar %.0f g · obtuve %s"
                % (n, n * POR_LOTE, f["consumo"]))

        # (c) UNA fila con `lotes`=N debe dar lo mismo que N filas de 1 lote
        for n in (1, 2, 3):
            _borrar_producciones(prod)
            _programar(prod, 3, lotes=n)
            f = _fila_mp(admin_client, cod)
            assert f is not None, "n=%d" % n
            assert abs(f["consumo"]["15"] - n * POR_LOTE) < 0.5, (
                "columna lotes=%d debe dar %.0f g · obtuve %s" % (n, n * POR_LOTE, f["consumo"]))
    finally:
        _limpiar(codigos=[cod], productos=[prod])


def test_p1_aditividad_dos_productos_comparten_mp(admin_client, db_clean):
    """La aditividad cruza productos: 2 productos distintos que usan la MISMA MP
    suman sus requerimientos (no se pisan ni se deduplican)."""
    cod, nom = "MPQAPADD2", "QAPROP Aditiva Dos"
    pa, pb = "QAPROP ADITIVA PRODA", "QAPROP ADITIVA PRODB"
    try:
        _seed_mp(cod, nom)
        _seed_formula(pa, 10, [(cod, nom, 10)])    # 1 lote = 1000 g
        _seed_formula(pb, 10, [(cod, nom, 25)])    # 1 lote = 2500 g
        _programar(pa, 4)
        f = _fila_mp(admin_client, cod)
        assert abs(f["consumo"]["15"] - 1000) < 0.5, f["consumo"]
        _programar(pb, 5)
        f = _fila_mp(admin_client, cod)
        assert abs(f["consumo"]["15"] - 3500) < 0.5, (
            "la MP compartida suma 1000+2500=3500 g · obtuve %s" % f["consumo"])
    finally:
        _limpiar(codigos=[cod], productos=[pa, pb])


# ═════════════════════════ P2 · MONOTONÍA ════════════════════════════════════

def test_p2_monotonia_por_horizonte(admin_client, db_clean):
    """consumo(15) ≤ consumo(30) ≤ consumo(60) ≤ consumo(90), y el déficit hereda
    la monotonía. Verificado en UNA request y también en requests SEPARADAS por
    horizonte (el valor de un horizonte no depende de con qué otros se pida)."""
    cod, nom = "MPQAPMON", "QAPROP Monotona"
    prod = "QAPROP MONOTONIA"
    POR_LOTE = 500.0                      # 10% × 5 kg × 1000
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 5, [(cod, nom, 10)])
        for d in (5, 20, 45, 75):         # cae en 15 / 30 / 60 / 90
            _programar(prod, d)

        f = _fila_mp(admin_client, cod)
        cons = f["consumo"]
        esperado = {"15": 1, "30": 2, "60": 3, "90": 4}
        for h, n in esperado.items():
            assert abs(cons[h] - n * POR_LOTE) < 0.5, (
                "consumo[%s] debe acumular %d lotes (%.0f g) · %s" % (h, n, n * POR_LOTE, cons))
        assert cons["15"] <= cons["30"] <= cons["60"] <= cons["90"], cons

        defi = f["deficit"]
        assert defi["15"] <= defi["30"] <= defi["60"] <= defi["90"], (
            "el déficit hereda la monotonía del consumo · %s" % defi)
        neto = f["neto_a_pedir"]
        assert neto["15"] <= neto["30"] <= neto["60"] <= neto["90"], neto

        # Requests SEPARADAS · un horizonte pedido solo debe dar lo mismo.
        sueltos = {}
        for h in ("15", "30", "60", "90"):
            fh = _fila_mp(admin_client, cod, horizontes=h)
            assert fh is not None, "h=%s" % h
            sueltos[h] = fh["consumo"][h]
            assert abs(sueltos[h] - cons[h]) < 0.5, (
                "consumo[%s] cambia según con qué horizontes se pida (%.1f vs %.1f)"
                % (h, sueltos[h], cons[h]))
        assert sueltos["15"] <= sueltos["30"] <= sueltos["60"] <= sueltos["90"], sueltos
    finally:
        _limpiar(codigos=[cod], productos=[prod])


# ═════════════════════ P3 · DÉFICIT y NETO A PEDIR ═══════════════════════════

def test_p3_deficit_y_neto_termino_por_termino(admin_client, db_clean):
    """Números redondos, cada término verificado por separado:
         consumo 10.000 · stock 3.000 · cuarentena 2.000 · pendiente 1.500
         deficit       = max(0, 10.000 − 3.000 − 2.000) = 5.000
         neto_a_pedir  = max(0, deficit − 1.500)         = 3.500
    """
    cod, nom = "MPQAPDEF", "QAPROP Deficit"
    prod = "QAPROP DEFICIT"
    sol = "SOL-QAPROP-DEF"
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 10, [(cod, nom, 50)])
        _programar(prod, 3, cantidad_kg=20)              # 50% × 20 kg × 1000 = 10.000 g
        _mov(cod, nom, 3000, "VIGENTE", "L-VIG")
        _mov(cod, nom, 2000, "CUARENTENA", "L-CUAR")
        _sol_pendiente(sol, cod, nom, 1500)

        f = _fila_mp(admin_client, cod)
        assert f is not None

        # Término por término
        assert abs(f["consumo"]["15"] - 10000) < 0.5, f["consumo"]
        assert abs(f["stock_actual_g"] - 3000) < 0.5, (
            "stock disponible = solo lo VIGENTE · %s" % f["stock_actual_g"])
        assert abs(f["cuarentena_g"] - 2000) < 0.5, (
            "la cuarentena se reporta aparte · %s" % f["cuarentena_g"])
        assert abs(f["pendiente_compras_g"] - 1500) < 0.5, (
            "el pendiente de compras se reporta aparte · %s" % f["pendiente_compras_g"])

        # Fórmulas
        for h in ("15", "30", "60", "90"):
            esp_def = max(0.0, f["consumo"][h] - f["stock_actual_g"] - f["cuarentena_g"])
            assert abs(f["deficit"][h] - esp_def) < 0.5, (
                "deficit[%s] = max(0, consumo − stock − cuarentena) · esperado %.1f, got %.1f"
                % (h, esp_def, f["deficit"][h]))
            esp_neto = max(0.0, f["deficit"][h] - f["pendiente_compras_g"])
            assert abs(f["neto_a_pedir"][h] - esp_neto) < 0.5, (
                "neto_a_pedir[%s] = max(0, deficit − pendiente) · esperado %.1f, got %.1f"
                % (h, esp_neto, f["neto_a_pedir"][h]))
        assert abs(f["deficit"]["15"] - 5000) < 0.5, f["deficit"]
        assert abs(f["neto_a_pedir"]["15"] - 3500) < 0.5, f["neto_a_pedir"]
    finally:
        _limpiar(codigos=[cod], productos=[prod], sols=[sol])


def test_p3_deficit_nunca_negativo(admin_client, db_clean):
    """Si stock + cuarentena cubren el consumo, deficit = 0 y neto = 0 (nunca negativos)."""
    cod, nom = "MPQAPDEF2", "QAPROP Deficit Cubierto"
    prod = "QAPROP DEFICIT CUBIERTO"
    sol = "SOL-QAPROP-DEF2"
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 10, [(cod, nom, 50)])
        _programar(prod, 3, cantidad_kg=20)              # 10.000 g
        _mov(cod, nom, 9000, "VIGENTE", "L-VIG2")
        _mov(cod, nom, 4000, "CUARENTENA", "L-CUAR2")    # 13.000 disponibles > 10.000
        _sol_pendiente(sol, cod, nom, 7000)
        f = _fila_mp(admin_client, cod)
        assert f is not None
        for h in ("15", "30", "60", "90"):
            assert f["deficit"][h] == 0, "deficit nunca negativo · h=%s · %s" % (h, f["deficit"])
            assert f["neto_a_pedir"][h] == 0, "neto nunca negativo · h=%s · %s" % (h, f["neto_a_pedir"])
        assert f["urgencia"] == "OK", f["urgencia"]
        assert _oc_deficit(admin_client, cod) == 0, "sin déficit no se pide nada"
    finally:
        _limpiar(codigos=[cod], productos=[prod], sols=[sol])


# ═════════════════════════ P4 · PARIDAD DURA ═════════════════════════════════

def _seed_paridad(cod, nom, prod):
    """Escenario de paridad: incluye a propósito un lote ATRASADO (programado hace 3 días,
    no iniciado). Históricamente la pantalla lo ignoraba y generar-OC sí lo contaba: el
    backlog salía de la vista con la que se decide."""
    _seed_mp(cod, nom)
    _seed_formula(prod, 10, [(cod, nom, 50)])
    _programar(prod, -3, cantidad_kg=10)     # ATRASADO · 5.000 g
    _programar(prod, 20, cantidad_kg=10)     # futuro   · 5.000 g
    _mov(cod, nom, 1000, "VIGENTE", "L-PAR")


def test_p4_paridad_pantalla_vs_motor_de_compra(admin_client, db_clean):
    """La pantalla de Abastecimiento y el motor que alimenta 'generar OC'
    (`/api/programacion/mps-deficit`) deben dar lo MISMO para la misma MP y el
    mismo horizonte (90 d), incluido el backlog de lotes atrasados."""
    cod, nom = "MPQAPPAR", "QAPROP Paridad"
    prod = "QAPROP PARIDAD"
    try:
        _seed_paridad(cod, nom, prod)

        f = _fila_mp(admin_client, cod, horizontes="90")
        assert f is not None, "la MP debe aparecer en la pantalla"
        consumo_pantalla = f["consumo"]["90"]
        neto_pantalla = f["neto_a_pedir"]["90"]

        # (a) el backlog atrasado ESTÁ en el número que se MUESTRA
        assert abs(consumo_pantalla - 10000) < 1, (
            "la pantalla debe contar el lote ATRASADO + el futuro (10.000 g) · obtuve %.1f "
            "(si da 5.000, el backlog volvió a quedar fuera de la vista)" % consumo_pantalla)
        assert abs(neto_pantalla - 9000) < 1, (
            "control: 10.000 consumo − 1.000 stock = 9.000 g a pedir · obtuve %.1f" % neto_pantalla)

        # (b) motor de compra == pantalla
        oc_prev = _oc_deficit(admin_client, cod)
        assert abs(neto_pantalla - oc_prev) < 1, (
            "DRIFT pantalla↔motor de compra para %s: pantalla 'Pedir'=%.1f g vs mps-deficit=%.1f g"
            % (cod, neto_pantalla, oc_prev))
    finally:
        _limpiar(codigos=[cod], productos=[prod])


def test_p4_generar_oc_escribe_lo_mismo_que_la_pantalla(admin_client, db_clean):
    """PARIDAD DURA de punta a punta: la cantidad que la pantalla muestra en 'Pedir'
    debe ser EXACTAMENTE la que el botón 'Generar OC' escribe en la SOL y en la OC.

    ⚠ HOY FALLA, y no por un número: `POST /api/programacion/generar-oc` responde 500.
    `prog_generar_oc` (programacion.py:12623) llama
    `siguiente_correlativo(conn, ...)` pasándole la CONEXIÓN, pero el helper
    (api/audit_helpers.py:225-228) hace `c.execute(...)` y después `c.fetchall()`:
    ni `sqlite3.Connection` ni `PgConnection` (api/pg_adapter.py:427) tienen
    `fetchall` → AttributeError. Lo mismo en `prog_regenerar_oc` (12473) y en las
    dos llamadas a `siguiente_numero_oc(conn, ...)` (12487 y 12644).
    El resto de callers del repo pasan un CURSOR (`c`), que sí es correcto.
    Consecuencia: el botón nunca crea la OC en cuanto hay al menos una MP en déficit.
    """
    cod, nom = "MPQAPPAR2", "QAPROP Paridad OC"
    prod = "QAPROP PARIDAD OC"
    try:
        _seed_paridad(cod, nom, prod)

        f = _fila_mp(admin_client, cod, horizontes="90")
        assert f is not None, "la MP debe aparecer en la pantalla"
        neto_pantalla = f["neto_a_pedir"]["90"]
        assert abs(neto_pantalla - 9000) < 1, neto_pantalla

        r = admin_client.post("/api/programacion/generar-oc", headers=csrf_headers(), json={})
        assert r.status_code == 200, (
            "generar-OC debe responder 200 · respondió %d · %s" % (r.status_code, r.data[:300]))

        con = _db()
        try:
            pedido_oc = float(con.execute(
                "SELECT COALESCE(SUM(cantidad_g),0) FROM ordenes_compra_items WHERE codigo_mp=?",
                (cod,)).fetchone()[0] or 0)
            pedido_sol = float(con.execute(
                "SELECT COALESCE(SUM(cantidad_g),0) FROM solicitudes_compra_items WHERE codigo_mp=?",
                (cod,)).fetchone()[0] or 0)
        finally:
            con.close()

        assert pedido_oc > 0, "generar-OC debía pedir esta MP (déficit real de %.1f g)" % neto_pantalla
        assert abs(pedido_oc - neto_pantalla) < 1, (
            "PARIDAD ROTA: la pantalla muestra 'Pedir'=%.1f g y la OC generada pide %.1f g"
            % (neto_pantalla, pedido_oc))
        assert abs(pedido_sol - neto_pantalla) < 1, (
            "PARIDAD ROTA: la SOL generada pide %.1f g y la pantalla muestra %.1f g"
            % (pedido_sol, neto_pantalla))
    finally:
        _limpiar(codigos=[cod], productos=[prod])


# ═════════════════════════ P5 · PEDIDO B2B ═══════════════════════════════════

def test_p5_b2b_cuenta_una_sola_vez(admin_client, db_clean):
    """Un pedido B2B pendiente cuenta UNA vez; si ya está integrado a un lote,
    se cuenta por el lote y no se duplica."""
    cod, nom = "MPQAPB2B", "QAPROP B2B"
    prod = "QAPROP PEDIDO B2B"
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 10, [(cod, nom, 10)])

        # (a) un pedido pendiente sin lote · 200 uds × 30 ml = 6 kg → 10% × 6 kg × 1000 = 600 g
        pb1 = _pedido_b2b(prod, 200, 30, 10)
        f = _fila_mp(admin_client, cod)
        assert f is not None, "la MP del pedido B2B pendiente debe aparecer"
        assert abs(f["consumo"]["15"] - 600) < 0.5, (
            "un pedido B2B cuenta una vez (600 g) · obtuve %s" % f["consumo"])

        # (b) un SEGUNDO pedido pendiente suma (aditividad), no se colapsa
        pb2 = _pedido_b2b(prod, 200, 30, 12, cliente_id="9901")
        f = _fila_mp(admin_client, cod)
        assert abs(f["consumo"]["15"] - 1200) < 0.5, (
            "dos pedidos B2B distintos suman 1.200 g · obtuve %s" % f["consumo"])

        # (c) el 2º se integra a un lote real → deja de contar como pedido suelto:
        #     ahora manda la producción (5 kg → 500 g) + el pedido 1 (600 g) = 1.100 g
        pp = _programar(prod, 12, cantidad_kg=5, origen="eos_b2b")
        _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, "
              "unidades_aporte, ml_unidad, envase_codigo, modo, cliente_nombre) "
              "VALUES (?,?,6,200,30,'','sumado_a_lote_canonico','Cliente QAPROP')", (pb2, pp))
        f = _fila_mp(admin_client, cod)
        assert abs(f["consumo"]["15"] - 1100) < 0.5, (
            "el pedido integrado NO se cuenta doble: 600 (pedido suelto) + 500 (lote) = 1.100 g "
            "· obtuve %s (si da 1.700 hay doble conteo)" % f["consumo"])
        assert pb1 and pb2
    finally:
        _limpiar(codigos=[cod], productos=[prod], clientes=["9900", "9901"])


# ═════════════════════════ P6 · AGUA (controla_stock=0) ══════════════════════

def test_p6_controla_stock_cero_nunca_tiene_deficit(admin_client, db_clean):
    """El agua del lab (controla_stock=0) NO se compra: nunca aparece con déficit
    en la pantalla ni en lo que pide generar-OC, en NINGÚN horizonte."""
    agua, agua_nom = "MPQAPAGUA", "QAPROP Agua Infinita"
    normal, normal_nom = "MPQAPNORM", "QAPROP Normal Controlada"
    prod = "QAPROP AGUA"
    try:
        _seed_mp(agua, agua_nom, controla_stock=0)
        _seed_mp(normal, normal_nom, controla_stock=1)
        _seed_formula(prod, 10, [(agua, agua_nom, 80), (normal, normal_nom, 10)])
        _programar(prod, 3, cantidad_kg=100)     # demanda enorme y CERO stock de ambas

        payload = _pantalla(admin_client)
        f_agua = _fila(payload, agua)
        f_norm = _fila(payload, normal)
        assert f_agua is None, (
            "el agua (controla_stock=0) no debe aparecer en Abastecimiento · %s" % f_agua)
        assert f_norm is not None, "la MP controlada de la MISMA fórmula sí debe aparecer"
        assert f_norm["deficit"]["15"] > 0, "control: la MP normal sí tiene déficit"

        assert _oc_deficit(admin_client, agua) == 0, "el agua nunca se pide en la OC"
        assert _oc_deficit(admin_client, normal) > 0, "control: la MP normal sí se pide"
    finally:
        _limpiar(codigos=[agua, normal], productos=[prod])


# ═════════════════════════ P7 · CUARENTENA ═══════════════════════════════════

def test_p7_cuarentena_no_es_stock_para_producir(admin_client, db_clean):
    """Nada de lo que está en CUARENTENA cuenta como stock disponible para PRODUCIR:
      · en Abastecimiento el `stock_actual_g` la excluye (se reporta aparte),
      · en Factibilidad el lote queda NO factible físicamente y la MP sale como faltante
        con disponible_g = 0.
    """
    cod, nom = "MPQAPCUAR", "QAPROP Cuarentena"
    prod = "QAPROP CUARENTENA"
    try:
        _seed_mp(cod, nom)
        _seed_formula(prod, 10, [(cod, nom, 40)])
        _programar(prod, 5, cantidad_kg=10)          # 40% × 10 kg × 1000 = 4.000 g
        _mov(cod, nom, 9000, "CUARENTENA", "L-CUAR-ONLY")   # TODO retenido

        f = _fila_mp(admin_client, cod)
        assert f is not None
        assert abs(f["consumo"]["15"] - 4000) < 0.5, f["consumo"]
        assert abs(f["stock_actual_g"] - 0) < 0.5, (
            "lo retenido en CUARENTENA no puede figurar como stock disponible · %s"
            % f["stock_actual_g"])
        assert abs(f["cuarentena_g"] - 9000) < 0.5, (
            "la cuarentena se reporta en su propia columna · %s" % f["cuarentena_g"])

        r = admin_client.get("/api/plan/factibilidad?dias=30&solo_fijo=1")
        assert r.status_code == 200, r.data
        mias = [p for p in (r.get_json().get("producciones") or [])
                if str(p.get("producto") or "").strip().upper() == prod]
        assert mias, "la producción sembrada debe estar en Factibilidad"
        p0 = mias[0]
        assert p0.get("factible_fisico") is False, (
            "con toda la MP en cuarentena el lote NO es factible físicamente · %s" % p0)
        faltan = {str(x.get("material_id")).upper(): x for x in (p0.get("mps_faltantes") or [])}
        assert cod.upper() in faltan, (
            "la MP retenida debe salir como faltante para producir · %s" % p0.get("mps_faltantes"))
        assert abs(float(faltan[cod.upper()]["disponible_g"]) - 0) < 0.5, (
            "disponible para producir debe ser 0 (la cuarentena no cuenta) · %s"
            % faltan[cod.upper()])
    finally:
        _limpiar(codigos=[cod], productos=[prod])
