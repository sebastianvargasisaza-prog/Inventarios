"""Caja menor y cargos fijos: ¿funcionan de punta a punta? (30-jul)

Sebastián: *"aún tenemos PQR, caja menor y cargos fijos"*. Se revisan con el mismo método que
materia prima: **caminando los endpoints reales**, que es lo único que distingue "está
construido" de "funciona" (M94).

Lo que este archivo fija:
  · **caja menor**: cada movimiento nace con su recibo NUMERADO, el saldo cuadra, anular
    CONSERVA la fila (un talonario del que se pueden arrancar hojas no prueba nada · M106) y el
    período contable sale del HECHO, no del reloj;
  · **cargos fijos**: se crea el cargo, aparece en la lista, y **no se paga dos veces el mismo
    período** (eso es plata que sale dos veces por lo mismo).
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _limpiar_caja(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_caja_menor WHERE concepto LIKE 'ZZTEST%'")
        conn.commit()


# ══ CAJA MENOR ══════════════════════════════════════════════════════════════════

def test_caja_el_movimiento_nace_con_recibo_numerado(app, db_clean):
    """El módulo existe para reemplazar los recibos sueltos SIN numeración: si el movimiento
    no trae número, nació incumpliendo su propio motivo (M106)."""
    _limpiar_caja(app)
    r = _login(app).post('/api/animus/caja', headers=_h(), json={
        'tipo': 'egreso', 'concepto': 'ZZTEST taxi', 'monto': 25000, 'fecha': '2026-07-30'})
    assert r.status_code in (200, 201), r.data[:400]
    j = r.get_json()
    num = str(j.get('recibo_numero') or j.get('recibo') or '')
    assert num, 'el movimiento salió sin número de recibo: %r' % j
    assert 'RC-' in num, 'el correlativo no tiene la forma RC-año-NNNN: %r' % num


def test_caja_el_saldo_cuadra(app, db_clean):
    """Ingresos menos egresos. Si el saldo no cuadra, la caja no sirve para nada."""
    _limpiar_caja(app)
    cli = _login(app)
    for tipo, monto in (('ingreso', 100000), ('egreso', 30000), ('egreso', 20000)):
        r = cli.post('/api/animus/caja', headers=_h(), json={
            'tipo': tipo, 'concepto': 'ZZTEST %s' % tipo, 'monto': monto, 'fecha': '2026-07-30'})
        assert r.status_code in (200, 201), r.data[:300]
    from database import get_db
    with app.app_context():
        c = get_db().cursor()
        ing = c.execute("SELECT COALESCE(SUM(monto),0) FROM animus_caja_menor "
                        "WHERE concepto LIKE 'ZZTEST%' AND LOWER(tipo)='ingreso' "
                        "AND COALESCE(anulado,0)=0").fetchone()[0]
        egr = c.execute("SELECT COALESCE(SUM(monto),0) FROM animus_caja_menor "
                        "WHERE concepto LIKE 'ZZTEST%' AND LOWER(tipo)='egreso' "
                        "AND COALESCE(anulado,0)=0").fetchone()[0]
    assert float(ing) == 100000 and float(egr) == 50000, (ing, egr)


def test_caja_anular_conserva_la_fila_y_la_saca_del_saldo(app, db_clean):
    """Anular NO borra: el hueco tiene que verse. Y deja de sumar."""
    _limpiar_caja(app)
    cli = _login(app)
    r = cli.post('/api/animus/caja', headers=_h(), json={
        'tipo': 'egreso', 'concepto': 'ZZTEST anulame', 'monto': 40000, 'fecha': '2026-07-30'})
    mid = (r.get_json() or {}).get('id')
    assert mid, r.data[:300]
    r = cli.delete('/api/animus/caja/%d' % mid, headers=_h(),
                   json={'motivo': 'ZZTEST se registro dos veces'})
    assert r.status_code in (200, 201), r.data[:400]
    from database import get_db
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT COALESCE(anulado,0), COALESCE(anulado_motivo,'') "
            "FROM animus_caja_menor WHERE id=?", (mid,)).fetchone()
    assert row is not None, 'la anulación BORRÓ la fila: el hueco ya no se ve'
    assert int(row[0]) == 1, 'no quedó marcada como anulada: %r' % (row,)
    assert 'ZZTEST' in row[1], 'se anuló sin dejar el motivo: %r' % (row,)


def test_caja_el_periodo_sale_del_HECHO_no_del_reloj(app, db_clean):
    """La misma fila no puede tener dos meses distintos: el período contable se deriva de la
    fecha del movimiento, no de `now()` (M106)."""
    _limpiar_caja(app)
    r = _login(app).post('/api/animus/caja', headers=_h(), json={
        'tipo': 'egreso', 'concepto': 'ZZTEST mes viejo', 'monto': 15000, 'fecha': '2026-05-15'})
    mid = (r.get_json() or {}).get('id')
    from database import get_db
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT fecha FROM animus_caja_menor WHERE id=?", (mid,)).fetchone()
    assert row and str(row[0])[:7] == '2026-05', (
        'la fecha del movimiento no es la que se registró: %r' % (row,))


# ══ CARGOS FIJOS ════════════════════════════════════════════════════════════════

def _limpiar_cargos(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        ids = [r[0] for r in cu.execute(
            "SELECT id FROM cargos_fijos WHERE concepto LIKE 'ZZTEST%'").fetchall()]
        for i in ids:
            cu.execute("DELETE FROM cargos_fijos_pagos WHERE cargo_fijo_id=?", (i,))
            cu.execute("DELETE FROM cargos_fijos WHERE id=?", (i,))
        conn.commit()


def test_cargos_fijos_se_crea_y_aparece(app, db_clean):
    _limpiar_cargos(app)
    cli = _login(app)
    r = cli.post('/api/compras/cargos-fijos', headers=_h(), json={
        'concepto': 'ZZTEST arriendo bodega', 'monto_estimado': 2500000,
        'dia_pago': 5, 'proveedor': 'ARRENDADOR ZZ'})
    assert r.status_code in (200, 201), r.data[:400]
    r = cli.get('/api/compras/cargos-fijos')
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    # el GET devuelve `plantillas` (las definiciones) y `pagos` (los del periodo)
    lista = j.get('plantillas') or []
    mio = [c for c in lista if str(c.get('concepto', '')).startswith('ZZTEST')]
    assert mio, 'el cargo fijo creado no aparece en la lista · claves: %r' % list(j)[:8]


def test_cargos_fijos_no_se_paga_dos_veces_el_mismo_periodo(app, db_clean):
    """Un cargo fijo pagado dos veces es plata que sale dos veces por lo mismo.

    El control ya existe (CAS: `UPDATE ... WHERE estado='por_pagar'` + rowcount). Este test
    lo FIJA: sin el CAS, dos clicks del mismo botón espejan dos egresos."""
    _limpiar_cargos(app)
    cli = _login(app)
    cli.post('/api/compras/cargos-fijos', headers=_h(), json={
        'concepto': 'ZZTEST internet', 'monto_estimado': 300000, 'dia_pago': 10})
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cid = cu.execute("SELECT id FROM cargos_fijos WHERE concepto LIKE 'ZZTEST internet%'"
                         ).fetchone()[0]
        cu.execute("INSERT INTO cargos_fijos_pagos (cargo_fijo_id, periodo, monto, estado) "
                   # 'por_pagar' es el estado que el pago exige: el flujo real es
                   # pendiente_monto -> (Catalina carga el monto) -> por_pagar -> pagado
                   "VALUES (?,?,?,'por_pagar')", (cid, '2026-07', 300000))
        pid = cu.execute("SELECT id FROM cargos_fijos_pagos WHERE cargo_fijo_id=? "
                         "AND periodo='2026-07'", (cid,)).fetchone()[0]
        conn.commit()
    r1 = cli.post('/api/compras/cargos-fijos/pago/%d/pagar' % pid, headers=_h(),
                  json={'monto': 300000, 'fecha': '2026-07-30'})
    assert r1.status_code in (200, 201), r1.data[:400]
    r2 = cli.post('/api/compras/cargos-fijos/pago/%d/pagar' % pid, headers=_h(),
                  json={'monto': 300000, 'fecha': '2026-07-30'})
    assert r2.status_code >= 400, 'pagó dos veces el mismo período: %s' % r2.data[:300]
