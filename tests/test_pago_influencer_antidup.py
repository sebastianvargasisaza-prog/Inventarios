"""Trazabilidad obligatoria y alertas anti doble-pago a influencers (27-jul).

Sebastián, definiendo cómo funciona de verdad: *"Jefferson me va pidiendo pagos según quién
publique... sin aprobación, es solo para pago, porque ya publicaron toca pagarles. Pero
necesito trazabilidad de lo que estoy pagando, que coloque fecha de publicación, qué tema
publicó, y siempre darme alertas del influencer que me reingresa sin justificación o que me está
pidiendo pagar lo mismo."*

Lo que define el diseño: **no hay paso de aprobación**, y está bien — el creador ya publicó, hay
que pagarle. Pero eso significa que estas alertas son **lo único** que separa un pago legítimo de
pagar dos veces el mismo contenido. Por eso:

  · avisan, no bloquean (bloquear un pago legítimo sería peor que mostrarlo con advertencia);
  · cada alerta trae **el pago anterior concreto**, para comparar los dos de frente;
  · y la fecha de publicación + el tema pasaron a ser OBLIGATORIOS, porque sin ellos no hay ni
    trazabilidad ni con qué comparar.
"""
import json

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _influencer(app, nombre, estado='Activo'):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for r in cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                            (nombre,)).fetchall():
            cu.execute("DELETE FROM pagos_influencers WHERE influencer_id=?", (r[0],))
            cu.execute("DELETE FROM marketing_influencers WHERE id=?", (r[0],))
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES (?,?)",
                   (nombre, estado))
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                         (nombre,)).fetchone()[0]
        conn.commit()
    return iid


def _pago_previo(app, iid, nombre, *, valor, fecha, fecha_pub='', tema='', estado='Pagada',
                 vence=''):
    """`vence` importa para los tests del Centro de Mando: la cola ordena por lo que vence
    primero y corta en 25, asi que sin una fecha temprana las filas sembradas quedan fuera
    detras de los pagos que ya existen en la BD compartida (M102)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute(
            "INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
            "estado, concepto, fecha_publicacion, entregable, vence_pago_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (iid, nombre, valor, fecha, estado, 'previo', fecha_pub, tema, vence))
        conn.commit()


def _alertas(app, iid, **kw):
    from database import get_db
    from blueprints.marketing import alertas_pago_influencer
    with app.app_context():
        base = {'influencer_id': iid, 'nombre': 'x', 'valor': 0,
                'fecha_publicacion': '', 'entregable': ''}
        base.update(kw)
        return alertas_pago_influencer(get_db().cursor(), **base)


def _codigos(alertas):
    return {a['codigo'] for a in alertas}


# ── Trazabilidad obligatoria ─────────────────────────────────────────────────

def test_sin_fecha_de_publicacion_no_se_puede_pedir_el_pago(app, db_clean):
    """Sin ese dato no hay como verificar que publicó ni con qué comparar después."""
    iid = _influencer(app, 'ZZ SIN PUB')
    c = _login(app)
    r = c.post("/api/marketing/influencers/%d/solicitar-pago" % iid,
               data=json.dumps({"valor": 300000, "concepto": "x",
                                "entregable": "Reel de prueba"}), headers=_h())
    assert r.status_code == 400, r.data[:300]
    assert r.get_json().get('codigo') == 'FALTA_FECHA_PUBLICACION', r.data[:300]


def test_sin_decir_que_publico_tampoco(app, db_clean):
    iid = _influencer(app, 'ZZ SIN TEMA')
    c = _login(app)
    r = c.post("/api/marketing/influencers/%d/solicitar-pago" % iid,
               data=json.dumps({"valor": 300000, "concepto": "x",
                                "fecha_publicacion": "2026-07-10"}), headers=_h())
    assert r.status_code == 400, r.data[:300]
    assert r.get_json().get('codigo') == 'FALTA_ENTREGABLE', r.data[:300]


def test_el_adelanto_se_puede_pedir_pero_hay_que_declararlo(app, db_clean):
    """La excepción legítima no se bloquea: se declara y queda escrita (M39). Si se bloqueara,
    alguien terminaría inventando una fecha de publicación falsa para poder pagar."""
    iid = _influencer(app, 'ZZ ADELANTO')
    c = _login(app)
    r = c.post("/api/marketing/influencers/%d/solicitar-pago" % iid,
               data=json.dumps({"valor": 300000, "concepto": "adelanto",
                                "sin_publicacion_motivo": "adelanto acordado, publica en agosto"}),
               headers=_h())
    assert r.status_code == 200, r.data[:400]
    from database import get_db
    with app.app_context():
        ent = get_db().execute(
            "SELECT COALESCE(entregable,'') FROM pagos_influencers WHERE influencer_id=? "
            "ORDER BY id DESC LIMIT 1", (iid,)).fetchone()[0]
    assert 'SIN PUBLICACIÓN' in ent and 'agosto' in ent, (
        'el motivo del adelanto no quedó visible en el pago: %r' % ent)


# ── Las alertas ──────────────────────────────────────────────────────────────

def test_avisa_si_ya_se_pago_esa_misma_publicacion(app, db_clean):
    """La señal más fuerte: misma fecha de publicación = es el mismo contenido."""
    iid = _influencer(app, 'ZZ MISMA PUB')
    _pago_previo(app, iid, 'ZZ MISMA PUB', valor=400000, fecha='2026-07-12',
                 fecha_pub='2026-07-10', tema='Reel niacinamida')
    a = _alertas(app, iid, valor=400000, fecha_publicacion='2026-07-10', entregable='Otra cosa')
    assert 'MISMA_PUBLICACION' in _codigos(a), a
    alta = [x for x in a if x['codigo'] == 'MISMA_PUBLICACION'][0]
    assert alta['nivel'] == 'alto'
    assert alta['pago_previo'] and alta['pago_previo']['valor'] == 400000, (
        'la alerta no trae el pago anterior · sin eso no se puede comparar')


def test_avisa_si_es_el_mismo_tema_escrito_distinto(app, db_clean):
    """'Reel Niacinamida!' y 'reel  niacinamida' son el mismo trabajo. Si la comparación fuera
    literal, cambiar una mayúscula bastaría para cobrar dos veces."""
    iid = _influencer(app, 'ZZ MISMO TEMA')
    _pago_previo(app, iid, 'ZZ MISMO TEMA', valor=200000, fecha='2026-03-05',
                 fecha_pub='2026-03-01', tema='Reel Niacinamida!')
    a = _alertas(app, iid, valor=999999, fecha_publicacion='2026-07-20',
                 entregable='reel  niacinamida')
    assert 'MISMO_TEMA' in _codigos(a), a


def test_avisa_el_mismo_monto_pocos_dias_despues(app, db_clean):
    """El patrón clásico del cobro repetido."""
    from tz_colombia import hoy_colombia
    from datetime import timedelta
    iid = _influencer(app, 'ZZ MISMO MONTO')
    hace5 = (hoy_colombia() - timedelta(days=5)).isoformat()
    _pago_previo(app, iid, 'ZZ MISMO MONTO', valor=350000, fecha=hace5,
                 fecha_pub=hace5, tema='contenido A')
    a = _alertas(app, iid, valor=350000, fecha_publicacion=hoy_colombia().isoformat(),
                 entregable='contenido B totalmente distinto')
    assert 'MISMO_MONTO_RECIENTE' in _codigos(a), a


def test_avisa_si_ya_tiene_un_pago_este_mes(app, db_clean):
    """No es un error, pero hay que verlo antes de sumar otro."""
    from tz_colombia import hoy_colombia
    iid = _influencer(app, 'ZZ ESTE MES')
    _pago_previo(app, iid, 'ZZ ESTE MES', valor=100000, fecha=hoy_colombia().isoformat(),
                 fecha_pub='2026-01-01', tema='algo viejo')
    a = _alertas(app, iid, valor=777000, fecha_publicacion=hoy_colombia().isoformat(),
                 entregable='contenido nuevo distinto')
    assert 'YA_TIENE_ESTE_MES' in _codigos(a), a
    assert [x for x in a if x['codigo'] == 'YA_TIENE_ESTE_MES'][0]['nivel'] == 'info'


def test_avisa_si_el_creador_estaba_dado_de_baja(app, db_clean):
    """"El influencer que me reingresa sin justificación", textual."""
    iid = _influencer(app, 'ZZ DE BAJA', estado='Inactivo')
    a = _alertas(app, iid, valor=100000, fecha_publicacion='2026-07-01', entregable='algo')
    assert 'REINGRESA_DADO_DE_BAJA' in _codigos(a), a


def test_un_pago_legitimo_no_dispara_nada(app, db_clean):
    """Con dientes al revés: si las alertas saltan siempre, dejan de mirarse y no protegen nada."""
    iid = _influencer(app, 'ZZ LIMPIO')
    _pago_previo(app, iid, 'ZZ LIMPIO', valor=111111, fecha='2026-01-15',
                 fecha_pub='2026-01-10', tema='campana de enero')
    a = _alertas(app, iid, valor=222222, fecha_publicacion='2026-07-20',
                 entregable='campana de julio, producto nuevo')
    assert a == [], ('un pago legítimo disparó alertas: %s' % a)


def test_las_graves_salen_primero(app, db_clean):
    """El orden importa: la primera que se lee tiene que ser la que puede costar plata."""
    from tz_colombia import hoy_colombia
    iid = _influencer(app, 'ZZ ORDEN')
    hoy = hoy_colombia().isoformat()
    _pago_previo(app, iid, 'ZZ ORDEN', valor=500000, fecha=hoy, fecha_pub='2026-07-09',
                 tema='tema previo')
    a = _alertas(app, iid, valor=500000, fecha_publicacion='2026-07-09', entregable='otro')
    assert a and a[0]['nivel'] == 'alto', a


# ── La lista de pagos las expone ─────────────────────────────────────────────

def test_la_lista_de_pendientes_trae_las_alertas(app, db_clean):
    """De nada sirve calcularlas si la pantalla donde se decide no las recibe."""
    iid = _influencer(app, 'ZZ LISTA')
    _pago_previo(app, iid, 'ZZ LISTA', valor=300000, fecha='2026-07-01',
                 fecha_pub='2026-06-30', tema='reel de junio', estado='Pagada')
    _pago_previo(app, iid, 'ZZ LISTA', valor=300000, fecha='2026-07-15',
                 fecha_pub='2026-06-30', tema='reel de junio', estado='Pendiente')
    c = _login(app)
    d = c.get('/api/marketing/pagos-influencers?estado=Pendiente').get_json()
    mios = [p for p in (d.get('pagos') or []) if p.get('influencer_nombre') == 'ZZ LISTA']
    assert mios, 'el pendiente no salió en la lista'
    assert mios[0].get('alertas'), 'la lista no trae las alertas: %s' % mios[0]
    assert 'MISMA_PUBLICACION' in {a['codigo'] for a in mios[0]['alertas']}, mios[0]['alertas']


def test_un_pendiente_sin_fecha_de_publicacion_se_marca(app, db_clean):
    """Los históricos ya cargados sin ese dato tienen que verse: es donde se estaría pagando
    algo que no se puede verificar."""
    iid = _influencer(app, 'ZZ VIEJO SIN PUB')
    _pago_previo(app, iid, 'ZZ VIEJO SIN PUB', valor=150000, fecha='2026-07-20',
                 fecha_pub='', tema='', estado='Pendiente')
    c = _login(app)
    d = c.get('/api/marketing/pagos-influencers?estado=Pendiente').get_json()
    mios = [p for p in (d.get('pagos') or []) if p.get('influencer_nombre') == 'ZZ VIEJO SIN PUB']
    assert mios, 'no salió en la lista'
    assert 'SIN_FECHA_PUBLICACION' in {a['codigo'] for a in (mios[0].get('alertas') or [])}, mios[0]


def test_la_pantalla_pinta_las_alertas(app, db_clean):
    """Calcularlas y no mostrarlas seria repetir el error que ya tenia este modulo: el dato
    capturado que nadie ve. Si alguien quita el render, esto lo caza."""
    c = _login(app)
    html = c.get('/marketing').data.decode('utf-8', 'replace')
    assert '_pagoAlertas' in html, 'desapareció el render de alertas'
    assert '+_pagoAlertas(p)' in html, 'las alertas no se pintan en la tarjeta del pago'
    assert 'pago_previo' in html or 'prev.valor' in html, (
        'la alerta no muestra el pago anterior · sin eso no se puede comparar')
    assert 'posible cobro repetido' in html, 'falta el resumen de alertas graves arriba'


def test_el_pago_llega_al_centro_de_mando_del_CEO(app, db_clean):
    """Sebastián: "Marketing es de Jefferson, el que paga soy yo como CEO... mejor que me llegue
    aquí, para ir centralizando mi módulo y no ir a otros". Antes tenía que entrar a
    Compras → Bandeja → Influencers.

    Va como un tipo de DECISIÓN más en la cola que ya existe, no como pantalla nueva (M1).
    """
    iid = _influencer(app, 'ZZ CENTRO')
    _pago_previo(app, iid, 'ZZ CENTRO', valor=640000, fecha='2026-07-20',
                 fecha_pub='2026-07-18', tema='reel colaboracion', estado='Pendiente',
                 vence='2001-01-01')
    c = _login(app)
    d = c.get('/api/centro/decisiones').get_json()
    pagos = [x for x in (d.get('decisiones') or []) if x.get('grupo') == 'pagos']
    assert pagos, 'los pagos a creadores no llegan al Centro de Mando: %s' % (
        sorted({x.get('grupo') for x in (d.get('decisiones') or [])}))
    mio = [x for x in pagos if 'ZZ CENTRO' in (x.get('detalle') or '')]
    assert mio, 'el pendiente no aparece en la cola: %s' % pagos[:3]
    assert 'publicó' in mio[0]['detalle'], 'la decisión no muestra cuándo publicó'
    assert mio[0]['valor'] == 640000, mio[0]


def test_un_pago_sospechoso_llega_como_CRITICO(app, db_clean):
    """La cola del CEO tiene que distinguir "pagá esto" de "mirá esto antes de pagar"."""
    iid = _influencer(app, 'ZZ CENTRO DUP')
    _pago_previo(app, iid, 'ZZ CENTRO DUP', valor=500000, fecha='2026-07-10',
                 fecha_pub='2026-07-05', tema='reel x', estado='Pagada')
    _pago_previo(app, iid, 'ZZ CENTRO DUP', valor=500000, fecha='2026-07-22',
                 fecha_pub='2026-07-05', tema='reel x', estado='Pendiente',
                 vence='2001-01-02')
    c = _login(app)
    d = c.get('/api/centro/decisiones').get_json()
    mio = [x for x in (d.get('decisiones') or [])
           if x.get('grupo') == 'pagos' and 'ZZ CENTRO DUP' in (x.get('detalle') or '')]
    assert mio, 'no llegó a la cola'
    assert mio[0]['nivel'] == 'critico', 'un posible cobro repetido no salió como crítico: %s' % mio[0]
    assert 'Revisar antes de pagar' in mio[0]['titulo'], mio[0]['titulo']


def test_el_pago_se_resuelve_desde_el_centro_de_mando(app, db_clean):
    """Sebastián: "la idea es que no me salga de mi módulo, que en mi módulo de CEO haga todo".

    La decisión no solo AVISA: viaja con lo necesario para ejecutarla ahí mismo (la OC, el monto,
    las alertas). Si sólo avisara, el CEO tendría que irse igual a otro módulo.
    """
    iid = _influencer(app, 'ZZ RESUELVE')
    _pago_previo(app, iid, 'ZZ RESUELVE', valor=450000, fecha='2026-07-21',
                 fecha_pub='2026-07-19', tema='reel julio', estado='Pendiente',
                 vence='2001-01-03')
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("UPDATE pagos_influencers SET numero_oc=? "
                   "WHERE influencer_id=? AND estado=?",
                   ('OC-ZZ-RESUELVE', iid, 'Pendiente'))
        conn.commit()
    c = _login(app)
    d = c.get('/api/centro/decisiones').get_json()
    mio = [x for x in (d.get('decisiones') or [])
           if x.get('grupo') == 'pagos' and 'ZZ RESUELVE' in (x.get('detalle') or '')]
    assert mio, 'no llegó a la cola del CEO'
    pago = mio[0].get('pago')
    assert pago, 'la decisión no trae con qué pagarla · el CEO tendría que irse a otro módulo'
    assert pago['numero_oc'] == 'OC-ZZ-RESUELVE' and pago['valor'] == 450000, pago
    assert 'alertas' in pago, 'no viajan las alertas con la decisión'


def test_el_centro_de_mando_tiene_el_boton_y_usa_el_endpoint_canonico(app, db_clean):
    c = _login(app)
    html = c.get('/hoy').data.decode('utf-8', 'replace')
    assert 'pagarCreador' in html, 'no está el botón de pagar en el Centro de Mando'
    assert "'/api/ordenes-compra/'+encodeURIComponent(p.numero_oc)+'/pagar'" in html, (
        'no usa el endpoint canónico de Compras · no crear una segunda vía para la plata')
    assert 'OJO con este pago' in html, 'no pone la alerta delante antes de confirmar'
    assert 'numero_transaccion' in html, 'no pide la referencia bancaria'


def test_marketing_ya_no_deja_pagar(app, db_clean):
    """Marketing es el módulo de Jefferson y él no autoriza pagos: el backend lo rechazaría, así
    que un botón ahí sería un botón que falla. Él pide y ve el estado; el CEO paga."""
    c = _login(app)
    html = c.get('/marketing').data.decode('utf-8', 'replace')
    assert 'onclick="pagarDesdeMarketing' not in html, (
        'quedó un botón de pagar en el módulo de Jefferson')


def test_compras_ya_no_tiene_la_central_de_pago_de_influencers(app, db_clean):
    """Sebastián: "quitarlo entonces la central de pago de influencers de Compras, porque allí
    tampoco". Jefferson pide en Marketing, el CEO decide y paga en Centro de Mando.

    Se saca SOLO la sub-vista: la pestaña Gerencia se queda porque también tiene Cargos Fijos.
    Y el filtro `fuente=influencers` del backend NO se toca — es INV-1 (las 3 fuentes de SOL no
    se mezclan) y es lo que evita que las SOL de influencer aparezcan en las bandejas de Catalina.
    """
    c = _login(app)
    html = c.get('/compras').data.decode('utf-8', 'replace')
    assert "showGerencia('influencer')" not in html, (
        'quedó la sub-vista de influencers en Compras')
    assert 'gtn-cargos' in html, 'se llevó por delante Cargos Fijos, que sí vive en Compras'
    # el aislamiento de las 3 fuentes sigue en pie
    d = c.get('/api/solicitudes-compra?fuente=influencers').get_json()
    assert d is not None and 'error' not in (d if isinstance(d, dict) else {}), (
        'se rompió el filtro por fuente · las SOL de influencer se mezclarían con las de planta')
