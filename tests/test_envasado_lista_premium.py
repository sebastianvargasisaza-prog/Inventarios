"""La lista de Envasado tiene que decir CÓMO van las órdenes, no sólo cuáles hay (26-jul).

Sebastián, mirando la pantalla: *"siempre me pregunto ¿es premium? · ¿qué hay para mejorar acá?"*.
La lista era una tabla de 5 columnas (n°, producto, lote, estado, botón): para saber si una orden
iba a la mitad, cuántos frascos salían o hacía cuántos días estaba parada, había que abrir el
legajo uno por uno.

Los datos que hacían falta ya existían, sólo que en otras tablas. Se calculan **server-side y en
consultas AGREGADAS**: pedirlos por fila desde el navegador serían N fetch desde una vista de
lista, que es justo lo que satura los 3 workers y deja la pantalla en "Cargando" (M43/M59/M86).

Este archivo limpia ANTES de sembrar y usa nombres fijos, porque la BD de tests es compartida y
en PostgreSQL persiste entre corridas (M103).
"""
from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = 'ENVLISTA PRODUCTO TEST'
LOTE = 'L-ENVLISTA-1'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app, dias_atras=4, pasos=(True, True, False, False, False), unidades=((30, 282), (15, 102))):
    """Un legajo de ENVASADO con pasos a medias y unidades registradas."""
    from datetime import datetime, timedelta
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        # limpiar ANTES (idempotente · no depende de que un finally haya corrido)
        for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote LIKE ?",
                             (LOTE + '%',)).fetchall():
            cur.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=?", (r[0],))
            cur.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id=?", (r[0],))
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
        for r in cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                             (PRODUCTO,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))

        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                    "creado_por) VALUES (?,1,'draft',12000,'test')", (PRODUCTO,))
        mbr = cur.lastrowid
        inicio = (datetime.utcnow() - timedelta(days=dias_atras)).strftime('%Y-%m-%dT%H:%M:%S')
        cur.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, fase, "
            "estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, numero_op) "
            "VALUES (?,1,?,?, 'envasado','iniciado','test',?,12000,'OF-TEST-0001')",
            (mbr, LOTE + '-OF', LOTE, inicio))
        ebr = cur.lastrowid
        for i, hecho in enumerate(pasos, start=1):
            cur.execute(
                "INSERT INTO ebr_pasos_ejecutados (ebr_id, mbr_paso_id, orden, descripcion, estado) "
                "VALUES (?,?,?,?,?)",
                (ebr, i, i, 'Paso %d de envasado' % i, 'completado' if hecho else 'pendiente'))
        for ml, uds in unidades:
            cur.execute(
                "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
                "volumen_ml, unidades, registrado_por, registrado_at_utc) "
                "VALUES (?,?,?,?,?,'test','2026-07-26T10:00:00')",
                (ebr, 'V%d' % ml, '%d ml' % ml, ml, uds))
        conn.commit()
        return ebr


def _orden(c, ebr_id):
    d = c.get('/api/brd/ordenes-unificadas?fase=envasado').get_json()
    assert d.get('ok'), d
    for o in d.get('ordenes') or []:
        if o.get('ebr_id') == ebr_id:
            return o, d.get('resumen') or {}
    raise AssertionError('la orden sembrada no aparece en la lista: %s'
                         % [o.get('ebr_id') for o in (d.get('ordenes') or [])])


def test_la_lista_dice_cuanto_avanzo_la_orden(app):
    """2 de 5 pasos = 40%. Antes había que abrir el legajo para saberlo."""
    ebr = _sembrar(app)
    o, _ = _orden(_admin(app), ebr)
    assert o['pasos_total'] == 5, o
    assert o['pasos_hechos'] == 2, o
    assert o['avance_pct'] == 40, o


def test_la_lista_trae_el_desglose_de_presentaciones(app):
    """De un granel de 12 kg salen 282 frascos de 30 ml y 102 de 15 ml: eso es lo que el jefe de
    planta necesita ver en la fila, no un total abstracto."""
    ebr = _sembrar(app)
    o, _ = _orden(_admin(app), ebr)
    pres = {int(p['volumen_ml']): p['unidades'] for p in o['presentaciones']}
    assert pres == {30: 282, 15: 102}, o['presentaciones']
    assert o['unidades_total'] == 384, o
    # ordenadas de mayor a menor volumen (la presentación principal primero)
    assert [int(p['volumen_ml']) for p in o['presentaciones']] == [30, 15]


def test_la_lista_dice_hace_cuantos_dias(app):
    """Una orden parada hace días es el caso que hay que ver de un vistazo."""
    ebr = _sembrar(app, dias_atras=4)
    o, _ = _orden(_admin(app), ebr)
    assert o['dias'] in (3, 4, 5), o['dias']   # tolerancia por el corte UTC-5


def test_el_resumen_cuenta_las_atrasadas(app):
    """El KPI de arriba: abiertas y, de esas, las que llevan 3 días o más sin cerrar."""
    ebr = _sembrar(app, dias_atras=6)
    _, res = _orden(_admin(app), ebr)
    assert res['abiertas'] >= 1, res
    assert res['atrasadas'] >= 1, res
    assert res['unidades_total'] >= 384, res


def test_una_orden_recien_abierta_no_cuenta_como_atrasada(app):
    """Con dientes: si todo contara como atrasado el KPI no serviría para nada."""
    ebr = _sembrar(app, dias_atras=0)
    o, _ = _orden(_admin(app), ebr)
    assert o['dias'] == 0, o['dias']


def test_sin_unidades_registradas_no_inventa_numeros(app):
    """Una orden sin registrar unidades muestra el aviso, no un total falso."""
    ebr = _sembrar(app, unidades=())
    o, _ = _orden(_admin(app), ebr)
    assert o['presentaciones'] == [], o
    assert o['unidades_total'] == 0, o


def test_la_lista_sigue_siendo_UNA_sola_consulta_por_pantalla(app):
    """El dato enriquecido tiene que venir en la MISMA respuesta. Si alguien lo mueve a un endpoint
    por orden, la lista vuelve a ser N+1 fetch y satura los workers (M43/M59)."""
    _sembrar(app)
    d = _admin(app).get('/api/brd/ordenes-unificadas?fase=envasado').get_json()
    for o in d['ordenes']:
        if o.get('ebr_id'):
            for k in ('pasos_total', 'pasos_hechos', 'presentaciones', 'unidades_total', 'dias'):
                assert k in o, 'falta %s en la respuesta de la lista' % k
