"""Directorio de creadores · qué le pagamos a cada uno, mes por mes (27-jul).

Sebastián: *"cada influencer puede ser cada mes un pago diferente, entonces debería haber un
directorio perfecto y premium, y uno donde estén los pagos, los pendientes"*.

La lista de pagos ya existía y ordena por FECHA ("¿qué pago sigue?"). Esto ordena por PERSONA
y responde la pregunta del CEO cuando Jefferson pide el pago del mes: **cuánto le llevamos
puesto a este creador, con qué ritmo, y qué nos devolvió**.

Lo que estos tests fijan, que es donde un directorio se vuelve mentiroso:
  · la serie mensual incluye los meses VACÍOS (un mes sin pago es información: paró);
  · el histórico sin `influencer_id` (los pagos importados) sigue contando para su creador;
  · "pendiente" acá significa lo mismo que en el centro de pagos (misma derivación desde la OC);
  · sin código de descuento el revenue va en None, nunca en 0 (0 se leería como "no vendió").
"""
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _mes_atras(n):
    """Primer día del mes n meses atrás (el 1 evita el desborde de fin de mes)."""
    d = date.today().replace(day=1)
    for _ in range(n):
        d = (d - timedelta(days=1)).replace(day=1)
    return d


def _limpiar(app, nombres):
    """Limpiar ANTES de sembrar, con nombres FIJOS (M103): la BD de tests es compartida
    y en PostgreSQL sobrevive entre corridas."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for nom in nombres:
            cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (nom,))
            for r in cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                                (nom,)).fetchall():
                cu.execute("DELETE FROM pagos_influencers WHERE influencer_id=?", (r[0],))
                cu.execute("DELETE FROM marketing_influencers WHERE id=?", (r[0],))
        conn.commit()


def _crear(app, nombre, *, estado='Activo', code=''):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("INSERT INTO marketing_influencers (nombre, estado, discount_code) "
                   "VALUES (?,?,?)", (nombre, estado, code))
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                         (nombre,)).fetchone()[0]
        conn.commit()
    return iid


def _pago(app, *, nombre, iid=None, valor, fecha, estado='Pagada', pub='', tema=''):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute(
            "INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
            "estado, concepto, numero_oc, fecha_publicacion, entregable) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (iid, nombre, valor, fecha.isoformat() if hasattr(fecha, 'isoformat') else fecha,
             estado, 'test directorio', '', pub, tema))
        conn.commit()


def _buscar(cli, nombre, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    r = cli.get(f"/api/marketing/directorio-creadores?q={nombre}" + (("&" + qs) if qs else ""))
    assert r.status_code == 200, r.data[:300]
    js = r.get_json()
    hit = [x for x in js["creadores"] if x["nombre"] == nombre]
    return js, (hit[0] if hit else None)


# ═══════════════════════════════════════════════════════════════════════════════

def test_serie_mensual_incluye_los_meses_vacios(app, db_clean):
    """Lo que Sebastián quiere ver es el RITMO: 'cada mes es un pago diferente'.

    Si los meses sin pago no aparecieran, tres pagos salteados se verían como tres meses
    seguidos y el directorio contaría una historia falsa.
    """
    NOM = 'ZZ DIR RITMO'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid, valor=300000, fecha=_mes_atras(0))
    _pago(app, nombre=NOM, iid=iid, valor=500000, fecha=_mes_atras(2))

    cli = _login(app)
    js, cr = _buscar(cli, NOM, meses=6)
    assert cr, 'el creador no salió en el directorio'

    assert len(cr["serie"]) == len(js["meses"]) >= 6, cr["serie"]
    por_mes = {s["mes"]: s["pagado"] for s in cr["serie"]}
    assert por_mes[_mes_atras(0).strftime('%Y-%m')] == 300000
    assert por_mes[_mes_atras(2).strftime('%Y-%m')] == 500000
    assert por_mes[_mes_atras(1).strftime('%Y-%m')] == 0, 'el mes sin pago debe salir en 0, no faltar'
    assert cr["pagado"] == 800000 and cr["n_pagos"] == 2
    assert cr["ticket_prom"] == 400000


def test_el_historico_sin_influencer_id_sigue_contando_para_su_creador(app, db_clean):
    """Los pagos importados quedaron con `influencer_id` en NULL y sólo el nombre.

    Agrupar únicamente por id dejaría fuera plata REAL y el directorio subestimaría lo que
    se le lleva pagado a un creador -- justo el número por el que se abre esta pantalla.
    """
    NOM = 'ZZ DIR HISTORICO'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid,  valor=200000, fecha=_mes_atras(0))
    _pago(app, nombre=NOM, iid=None, valor=150000, fecha=_mes_atras(1))   # importado

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=6)
    assert cr["pagado"] == 350000, f'perdió el pago histórico sin id: {cr["pagado"]}'
    assert cr["n_pagos"] == 2


def test_pendiente_significa_lo_mismo_que_en_el_centro_de_pagos(app, db_clean):
    """El estado se deriva de la OC en los dos lados; si el directorio lo dedujera distinto,
    los dos tableros mostrarían números diferentes de la MISMA plata (M5)."""
    NOM = 'ZZ DIR PENDIENTE'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid, valor=400000, fecha=_mes_atras(0), estado='Pendiente')
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(0), estado='Pagada')

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=3)
    assert cr["pendiente"] == 400000 and cr["n_pendientes"] == 1
    assert cr["pagado"] == 100000, 'lo pendiente no puede sumarse a lo pagado'

    lista = cli.get('/api/marketing/pagos-influencers?estado=Pendiente').get_json()
    mios = [p for p in (lista.get('pagos') or lista.get('items') or [])
            if p.get('influencer_nombre') == NOM]
    assert len(mios) == cr["n_pendientes"], (
        'el directorio y el centro de pagos no cuentan los mismos pendientes')


def test_pago_marcado_pagada_por_la_OC_cuenta_como_pagado(app, db_clean):
    """`pi.estado` queda stale cuando un sync falla; la verdad es el estado de la OC."""
    from database import get_db
    NOM = 'ZZ DIR OCPAGADA'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", ('OC-ZZ-DIR-1',))
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, fecha, valor_total) "
                   "VALUES (?,?,?,?,?)",
                   ('OC-ZZ-DIR-1', NOM, 'Pagada', _mes_atras(0).isoformat(), 250000))
        cu.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, "
                   "fecha, estado, numero_oc) VALUES (?,?,?,?,?,?)",
                   (iid, NOM, 250000, _mes_atras(0).isoformat(), 'Pendiente', 'OC-ZZ-DIR-1'))
        conn.commit()

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=3)
    assert cr["pagado"] == 250000, 'la OC está Pagada: el directorio debe reflejarlo'
    assert cr["pendiente"] == 0


def test_sin_codigo_de_descuento_el_revenue_va_en_None_no_en_cero(app, db_clean):
    """Un creador sin código no es un creador que no vendió: es un creador sin dato.

    Mostrarlo en 0 lo haría ver como el peor del ranking por algo que nadie midió (M33).
    """
    NOM = 'ZZ DIR SINCODE'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM, code='')
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(0))

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=3)
    assert cr["revenue"] is None and cr["roi_pct"] is None, cr


def test_marca_los_pagos_sin_fecha_de_publicacion(app, db_clean):
    """Un pago sin fecha de publicación no se puede verificar: es exactamente lo que el CEO
    pidió ver ('necesito trazabilidad de lo que estoy pagando')."""
    NOM = 'ZZ DIR SINPUB'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(0), pub='', tema='')
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(0),
          pub=_mes_atras(0).isoformat(), tema='reel')

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=3)
    assert cr["sin_publicacion"] == 1, cr["sin_publicacion"]


def test_el_ultimo_pago_y_los_dias_sin_pago_salen_del_pago_real(app, db_clean):
    NOM = 'ZZ DIR ULTIMO'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(2), tema='viejo')
    ayer = date.today() - timedelta(days=1)
    _pago(app, nombre=NOM, iid=iid, valor=900000, fecha=ayer, tema='reel nuevo')

    cli = _login(app)
    _, cr = _buscar(cli, NOM, meses=6)
    assert cr["ultimo_pago"]["valor"] == 900000
    assert cr["ultimo_pago"]["entregable"] == 'reel nuevo'
    assert cr["dias_sin_pago"] in (0, 1, 2), cr["dias_sin_pago"]


def test_ordena_por_plata_puesta_y_los_kpis_cuadran_con_las_filas(app, db_clean):
    """El directorio abre mostrando en quién se está invirtiendo de verdad, no el alfabético.
    Y un KPI que no sea la suma de lo que se ve abajo es un KPI que miente (M5)."""
    A, B = 'ZZ DIR ORDEN A', 'ZZ DIR ORDEN B'
    _limpiar(app, [A, B])
    ia = _crear(app, A)
    ib = _crear(app, B)
    _pago(app, nombre=A, iid=ia, valor=100000, fecha=_mes_atras(0))
    _pago(app, nombre=B, iid=ib, valor=900000, fecha=_mes_atras(0))

    cli = _login(app)
    r = cli.get('/api/marketing/directorio-creadores?q=ZZ DIR ORDEN&meses=3')
    assert r.status_code == 200
    js = r.get_json()
    nombres = [x["nombre"] for x in js["creadores"]]
    assert nombres[:2] == [B, A], nombres

    assert js["kpis"]["pagado_total"] == sum(x["pagado"] for x in js["creadores"])
    assert js["kpis"]["pendiente_total"] == sum(x["pendiente"] for x in js["creadores"])
    assert js["kpis"]["creadores"] == len(js["creadores"])


def test_la_ventana_de_meses_recorta_de_verdad(app, db_clean):
    NOM = 'ZZ DIR VENTANA'
    _limpiar(app, [NOM])
    iid = _crear(app, NOM)
    _pago(app, nombre=NOM, iid=iid, valor=700000, fecha=_mes_atras(5))
    _pago(app, nombre=NOM, iid=iid, valor=100000, fecha=_mes_atras(0))

    cli = _login(app)
    _, corto = _buscar(cli, NOM, meses=2)
    _, largo = _buscar(cli, NOM, meses=12)
    assert corto["pagado"] == 100000, 'el pago viejo no debería entrar en la ventana corta'
    assert largo["pagado"] == 800000


def test_la_atribucion_usa_el_mismo_motor_que_el_directorio(app, db_clean):
    """M1: un solo motor de atribución. Si fueran dos cálculos, el revenue del creador y el
    de la tabla de atribución divergirían y el CEO vería dos verdades."""
    import inspect
    from blueprints import marketing as mkt
    src = inspect.getsource(mkt.mkt_atribucion_influencers)
    assert 'atribucion_por_influencer(' in src, (
        'la tabla de atribución volvió a tener su propia copia del cálculo')
    src_dir = inspect.getsource(mkt.mkt_directorio_creadores)
    assert 'atribucion_por_influencer(' in src_dir


def test_la_pantalla_de_marketing_trae_el_directorio(app, db_clean):
    cli = _login(app)
    html = pantalla_servida(cli, '/marketing')
    assert 'loadDirectorio' in html, 'el directorio no está montado en la pantalla'
    assert '/api/marketing/directorio-creadores' in html
