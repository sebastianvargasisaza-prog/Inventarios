"""Pagos › Influencers dentro del Centro de Mando · y el rechazo deja rastro (27-jul).

Sebastián: *"quisiera que hubiera arriba que dijera Pagos, y allí una subpestaña que diga
Influencers. Cuando le doy click al influencer me lleva a Marketing, no debería ser: debería
mostrarme el influencer con todos los datos -- cuenta bancaria, nombre, monto a pagar, qué le
estoy pagando, fecha de publicación"*. Y sobre la bandeja de rechazados: *"debería salir por
qué la rechacé"*.

Lo que estos tests fijan:
  · la bandeja trae TODO lo necesario para decidir el pago sin salir del módulo;
  · los datos bancarios sólo los ve admin o contadora (Habeas Data, Ley 1581);
  · rechazar exige motivo y MARCA la fila -- nunca la borra, que es lo que hacía antes y por
    eso la bandeja de Rechazados salía siempre en cero;
  · la cola de decisiones ya no se inunda con una tarjeta por pago.
"""
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f'no pudo entrar {user}'
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


NOM = 'ZZ BANDEJA CREADOR'
OC = 'OC-ZZ-BANDEJA'


def _sembrar(app, *, estado_oc='Autorizada', fecha_pub='2026-07-10', valor=750000):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida y en PG sobrevive."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (NOM,))
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        for r in cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?", (NOM,)).fetchall():
            cu.execute("DELETE FROM pagos_influencers WHERE influencer_id=?", (r[0],))
            cu.execute("DELETE FROM marketing_influencers WHERE id=?", (r[0],))
        cu.execute(
            "INSERT INTO marketing_influencers (nombre, estado, banco, cuenta_bancaria, "
            "tipo_cuenta, cedula_nit, usuario_red, ciudad, email, telefono) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (NOM, 'Activo', 'Bancolombia', '9991234567', 'Ahorros', '1094970527',
             'zzbandeja', 'Medellin', 'zz@test.co', '3001234567'))
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?", (NOM,)).fetchone()[0]
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, fecha, valor_total) "
                   "VALUES (?,?,?,?,?)", (OC, NOM, estado_oc, date.today().isoformat(), valor))
        cu.execute(
            "INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
            "estado, concepto, numero_oc, fecha_publicacion, entregable) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (iid, NOM, valor, date.today().isoformat(), 'Pendiente', 'test bandeja', OC,
             fecha_pub, 'REEL de lanzamiento'))
        pid = cu.execute("SELECT id FROM pagos_influencers WHERE influencer_nombre=? "
                         "ORDER BY id DESC", (NOM,)).fetchone()[0]
        conn.commit()
    return iid, pid


def _mio(js):
    return [p for p in (js.get('pagos') or []) if p['influencer_nombre'] == NOM]


# ═══════════════════════════════════════════════════════════════════════════════

def test_la_bandeja_trae_todo_lo_necesario_para_decidir_el_pago(app, db_clean):
    """Lo que pidió, campo por campo: nombre, cuenta bancaria, monto, qué se le paga y
    la fecha de publicación. Si falta uno, hay que irse a otra pantalla y el punto era
    justamente no tener que salir."""
    _sembrar(app)
    c = _login(app, 'sebastian')     # admin: ve datos bancarios
    r = c.get('/api/centro/pagos-influencers')
    assert r.status_code == 200, r.data[:300]
    js = r.get_json()
    p = _mio(js)
    assert p, 'el pago pendiente no salió en la bandeja'
    p = p[0]
    assert p['influencer_nombre'] == NOM
    assert p['valor'] == 750000
    assert p['entregable'] == 'REEL de lanzamiento'
    assert p['fecha_publicacion'] == '2026-07-10'
    assert p['banco'] == 'Bancolombia'
    assert p['cuenta_bancaria'] == '9991234567'
    assert p['tipo_cuenta'] == 'Ahorros'
    assert p['cedula_nit'] == '1094970527'
    assert p['numero_oc'] == OC
    assert js['ve_datos_bancarios'] is True


def test_los_datos_bancarios_no_se_le_muestran_a_cualquiera(app, db_clean):
    """Habeas Data (Ley 1581): la cuenta sólo admin y contadora. El resto ve la bandeja
    completa menos ese bloque."""
    _sembrar(app)
    c = _login(app, 'jefferson')
    r = c.get('/api/centro/pagos-influencers')
    assert r.status_code == 200
    js = r.get_json()
    p = _mio(js)
    assert p, 'jefferson debería ver la bandeja'
    assert js['ve_datos_bancarios'] is False
    assert p[0]['cuenta_bancaria'] == '***' and p[0]['banco'] == '***'
    assert p[0]['valor'] == 750000, 'lo que NO es bancario se sigue viendo'


def test_un_pago_sin_fecha_de_publicacion_llega_marcado_para_revisar(app, db_clean):
    """Sin fecha no se puede verificar que se entregó: es el caso en que se pagaría algo
    que quizá no se hizo, así que pesa igual que un cobro repetido."""
    _sembrar(app, fecha_pub='')
    c = _login(app)
    p = _mio(c.get('/api/centro/pagos-influencers').get_json())[0]
    codigos = [a.get('codigo') for a in p['graves']]
    assert 'SIN_FECHA_PUBLICACION' in codigos, p['graves']


def test_rechazar_exige_motivo(app, db_clean):
    _sembrar(app)
    _, pid = _sembrar(app)
    c = _login(app)
    r = c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
               json={'motivo': 'no'}, headers=_h())
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'MOTIVO_REQUERIDO'


def test_rechazar_MARCA_la_fila_y_guarda_por_que_nunca_la_borra(app, db_clean):
    """Sebastián: *"en rechazadas debería salir por qué la rechacé"*.

    Antes el auto-backfill hacía DELETE de las solicitudes cuya OC quedaba rechazada, así que
    el contador de Rechazados marcaba 0 y quien pidió el pago no tenía forma de saber por qué
    no le pagaron. Un rechazo sin rastro deja a Jefferson pidiendo lo mismo la semana siguiente.
    """
    from database import get_db
    _, pid = _sembrar(app)
    c = _login(app)
    r = c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
               json={'motivo': 'ese reel ya se pagó en junio'}, headers=_h())
    assert r.status_code == 200, r.data[:300]

    with app.app_context():
        conn = get_db()
        fila = conn.cursor().execute(
            "SELECT estado, motivo_rechazo, rechazado_por FROM pagos_influencers WHERE id=?",
            (pid,)).fetchone()
    assert fila is not None, 'la fila se borró · se perdió el rastro del rechazo'
    assert fila[0] == 'Rechazada'
    assert fila[1] == 'ese reel ya se pagó en junio'
    assert fila[2] == 'sebastian'

    # Y sale de la bandeja de pendientes: ya se decidió.
    assert not _mio(c.get('/api/centro/pagos-influencers').get_json())


def test_el_motivo_del_rechazo_le_llega_a_quien_pidio_el_pago(app, db_clean):
    """Marketing es el módulo de Jefferson: ahí tiene que poder leer por qué no se pagó."""
    _, pid = _sembrar(app)
    c = _login(app)
    c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
           json={'motivo': 'falta el link del post'}, headers=_h())

    js = c.get('/api/marketing/pagos-influencers').get_json()
    fila = [p for p in (js.get('pagos') or js.get('items') or [])
            if p.get('influencer_nombre') == NOM]
    assert fila, 'el pago rechazado desapareció de la lista de Marketing'
    assert fila[0].get('motivo_rechazo') == 'falta el link del post'

    html = pantalla_servida(c, '/marketing')
    assert 'motivo_rechazo' in html, 'la pantalla no muestra el motivo del rechazo'


def test_no_se_puede_rechazar_algo_ya_pagado(app, db_clean):
    from database import get_db
    _, pid = _sembrar(app)
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("UPDATE pagos_influencers SET estado='Pagada' WHERE id=?", (pid,))
        conn.commit()
    c = _login(app)
    r = c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
               json={'motivo': 'me arrepentí después de pagar'}, headers=_h())
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'YA_PAGADO'


def test_rechazar_dos_veces_no_pisa_el_primer_motivo(app, db_clean):
    """CAS (M27): con 3 workers, dos rechazos del mismo pago no pueden pasar los dos."""
    from database import get_db
    _, pid = _sembrar(app)
    c = _login(app)
    assert c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
                  json={'motivo': 'el primero que quedó'}, headers=_h()).status_code == 200
    r2 = c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
                json={'motivo': 'este no debería entrar'}, headers=_h())
    assert r2.status_code == 409
    with app.app_context():
        conn = get_db()
        motivo = conn.cursor().execute(
            "SELECT motivo_rechazo FROM pagos_influencers WHERE id=?", (pid,)).fetchone()[0]
    assert motivo == 'el primero que quedó'


def test_solo_un_administrador_rechaza(app, db_clean):
    _, pid = _sembrar(app)
    c = _login(app, 'jefferson')
    r = c.post(f'/api/centro/pagos-influencers/{pid}/rechazar',
               json={'motivo': 'no me quiero pagar a mí mismo'}, headers=_h())
    assert r.status_code == 403


def test_la_cola_de_decisiones_ya_no_se_inunda_con_una_tarjeta_por_pago(app, db_clean):
    """25 tarjetas de pago tapaban todo lo demás. Ahora va UNA de resumen que lleva a la
    pestaña Pagos, así nada queda escondido pero la cola se puede leer."""
    _sembrar(app)
    c = _login(app)
    dec = c.get('/api/centro/decisiones').get_json().get('decisiones') or []
    pagos = [d for d in dec if d.get('grupo') == 'pagos']
    assert len(pagos) <= 1, f'la cola trae {len(pagos)} tarjetas de pago en vez de un resumen'
    if pagos:
        assert pagos[0].get('ir_a_pagos') is True
        assert 'esperando' in (pagos[0].get('detalle') or '')


def test_el_centro_de_mando_tiene_la_pestana_pagos_con_su_subpestana(app, db_clean):
    c = _login(app)
    html = c.get('/hoy').data.decode('utf-8', 'replace')
    assert "showPane('pagos')" in html, 'no está la pestaña Pagos'
    assert "showSubPago('influencers')" in html, 'no está la subpestaña Influencers'
    assert '/api/centro/pagos-influencers' in html
    assert 'rechazarDesdeBandeja' in html, 'no se puede rechazar desde la bandeja'
    # Y la ficha se abre ahí mismo: no puede mandar a Marketing (era la queja).
    assert 'pagarDesdeBandeja' in html


# ═══════════════════════════════════════════════════════════════════════════════
# PQR MUDO · el silencio tiene que verse donde el CEO mira, no en un endpoint aparte
# ═══════════════════════════════════════════════════════════════════════════════

def test_si_PQR_lleva_semanas_sin_recibir_nada_llega_al_centro_de_mando(app, db_clean):
    """GHL dejó de enviar el 15-jun y se descubrió el 27-jul, de casualidad.

    El diagnóstico ya lo detectaba, pero sólo si alguien abría ESE endpoint. Un aviso que hay
    que ir a buscar no avisa: una integración muda se ve igual que "no hay quejas".
    """
    from database import get_db
    from datetime import date, timedelta
    viejo = (date.today() - timedelta(days=40)).isoformat() + ' 10:00:00'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM pqr_inbox WHERE ghl_message_id LIKE 'ZZ-MUDO%'")
        cu.execute("DELETE FROM pqr_inbox")   # el MAX() mira toda la tabla (M102)
        cu.execute("INSERT INTO pqr_inbox (ghl_message_id, recibido_en, canal, mensaje, estado) "
                   "VALUES (?,?,?,?,?)",
                   ('ZZ-MUDO-1', viejo, 'whatsapp', 'hola, consulta', 'pendiente'))
        conn.commit()

    c = _login(app)
    dec = c.get('/api/centro/decisiones').get_json().get('decisiones') or []
    pqr = [d for d in dec if 'PQR' in (d.get('titulo') or '')]
    assert pqr, 'el silencio de PQR no llega a la cola del CEO'
    assert 'días que no entra' in (pqr[0].get('detalle') or '')
    assert 'GHL' in (pqr[0].get('detalle') or ''), 'no dice de qué lado se cortó'


def test_si_PQR_recibio_hoy_no_molesta(app, db_clean):
    """Una alerta que sale siempre deja de mirarse."""
    from database import get_db
    from datetime import date
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM pqr_inbox")
        cu.execute("INSERT INTO pqr_inbox (ghl_message_id, recibido_en, canal, mensaje, estado) "
                   "VALUES (?,?,?,?,?)",
                   ('ZZ-VIVO-1', date.today().isoformat() + ' 09:00:00', 'whatsapp', 'hola', 'pendiente'))
        conn.commit()
    c = _login(app)
    dec = c.get('/api/centro/decisiones').get_json().get('decisiones') or []
    assert not [d for d in dec if 'PQR' in (d.get('titulo') or '')]


# ── la ficha se lee POR PARTES (Sebastián 4-ago) ─────────────────────────────

def _fuente_bandeja():
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(raiz, 'api/templates_py/centro_operaciones_html.py'),
                   encoding='utf-8').read()


def test_la_ficha_va_en_bloques_y_el_banco_aparte():
    """*"puede ir por partes: datos del creador arriba, datos bancarios abajo, o sea que la
    lectura sea mejor"*. Trece campos en una sola grilla se leen como un muro."""
    src = _fuente_bandeja()
    for titulo in ("'Quién es y qué publicó'", "'El cobro'", "'Para consignar'"):
        assert '_pgBloque(' + titulo in src, 'falta el bloque %s' % titulo
    assert '.pg-banco' in src, 'los datos bancarios no tienen su propio recuadro'
    # el número de cuenta es lo que se copia al banco: no puede ir del mismo tamaño que el resto
    assert "'pg-cuenta'" in src and '.pg-ficha .pg-cuenta .val' in src


def test_no_se_perdio_ningun_campo_al_reordenar():
    """Con dientes: reacomodar 13 campos en 3 bloques es justo donde se cae uno sin que nadie
    lo note (M112) · y el que falte sería el que hace falta para pagar."""
    src = _fuente_bandeja()
    for campo in ('Creador', 'Red', 'Ciudad', 'Monto a pagar', 'Qué se le paga',
                  'Fecha de publicación', 'Solicitado', 'Vence', 'Orden', 'Email',
                  'Teléfono', 'Banco', 'Tipo de cuenta', 'Número de cuenta', 'Cédula / NIT'):
        assert "_pgDato('" + campo + "'" in src, 'se perdió el campo %s de la ficha' % campo


def test_el_gate_de_habeas_data_sigue_puesto():
    """Mover el banco a su propio bloque no puede aflojar quién lo ve (Ley 1581)."""
    src = _fuente_bandeja()
    assert 've_datos_bancarios' in src
    assert 'sólo los ve un administrador o la contadora' in src
