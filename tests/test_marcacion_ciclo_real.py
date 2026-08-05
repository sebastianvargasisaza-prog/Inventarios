# -*- coding: utf-8 -*-
"""El ciclo COMPLETO de marcación, por los endpoints reales (4-ago · revisión adversarial).

El arreglo del doble descuento se probó con un fixture que ponía `maestro_mee.stock_actual` A
MANO. Producción no hace eso: `marcacion_orden_enviar` DECREMENTA el cache del base, pero el
retorno insertaba la Entrada del serigrafiado sin volver a subirlo. Y `aplicar_movimiento_mee`
CLAMPEA la Salida contra ese cache, no contra la suma del kardex.

Resultado: con el cache del serigrafiado en 0, la Salida se registraba en **CERO** -- sin error,
sin log, y con el ítem del checklist marcado como consumido. O sea que el doble descuento se
había convertido en **cero descuento**, que es peor: el kardex dice que el envase sigue ahí.

Este test recorre enviar → recibir → liberar → producir por los ENDPOINTS, sin tocar el cache a
mano. Es la única forma de que el fixture no tape el bug (M94: construido no es validado hasta
que un E2E lo recorre por el camino real).
"""
from .conftest import TEST_PASSWORD, csrf_headers

BASE = 'ZZCIC-BASE'
SERIG = 'ZZCIC-SERIG'
PROD_ID = 7710


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'ZZCIC%'")
        c.execute("DELETE FROM marcacion_ordenes WHERE base_codigo LIKE 'ZZCIC%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZCIC%'")
        c.execute("DELETE FROM produccion_checklist WHERE mee_codigo_asignado LIKE 'ZZCIC%'")
        conn.commit()


def _sembrar(app):
    """Como está en producción: el base con stock REAL (kardex + cache en sincronía, que es lo
    que dejan la recepción y el cron de drift) y el serigrafiado en cero."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual) "
                  "VALUES (?,?, 'Activo', 1000)", (BASE, 'Frasco sin serigrafía'))
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual, "
                  "material_referencia) VALUES (?,?, 'Activo', 0, ?)",
                  (SERIG, 'Frasco CON serigrafía', BASE))
        c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, "
                  "responsable) VALUES (?, 'Entrada', 1000, 'und', 'SEED', 'test')", (BASE,))
        c.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, "
                  "fecha_planeada, item_tipo, descripcion, mee_codigo_asignado, "
                  "cantidad_unidades) VALUES (?, 'ZZ CICLO', date('now','-5 hours'), 'envase', "
                  "'Frasco', ?, 300)", (PROD_ID, BASE))
        conn.commit()


def _stock(app, codigo):
    from database import get_db
    from blueprints.programacion import _get_mee_stock
    with app.app_context():
        return float((_get_mee_stock(get_db()) or {}).get(codigo.upper(), 0) or 0)


def _cache(app, codigo):
    from database import get_db
    with app.app_context():
        r = get_db().execute("SELECT COALESCE(stock_actual,0) FROM maestro_mee WHERE codigo=?",
                             (codigo,)).fetchone()
        return float(r[0] or 0) if r else None


def _ciclo_hasta_liberado(app, cli):
    """enviar → recibir → liberar, todo por los endpoints reales."""
    r = cli.post('/api/programacion/marcacion-orden/enviar',
                 json={'serigrafiado_codigo': SERIG, 'cantidad': 300, 'producto': 'ZZ CICLO',
                       'metodo': 'Serigrafia', 'proveedor': 'ZZ Prov', 'produccion_id': PROD_ID},
                 headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    from database import get_db
    with app.app_context():
        oid = get_db().execute(
            "SELECT id FROM marcacion_ordenes WHERE base_codigo=? ORDER BY id DESC LIMIT 1",
            (BASE,)).fetchone()[0]
    r = cli.post('/api/programacion/marcacion-orden/%d/recibir' % oid,
                 json={'cantidad_recibida': 300}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    # La liberación directa está deshabilitada a propósito: el retorno se libera SOLO por el
    # checklist de arte (Dirección Técnica / Aseguramiento / Calidad). Usar el endpoint viejo
    # habría hecho pasar el test por un camino que en producción devuelve 409.
    r = cli.post('/api/programacion/marcacion-orden/%d/liberar-checklist' % oid,
                 json={'arte': True, 'estado': True, 'caracteristicas': True, 'cantidad': True},
                 headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    return oid


def test_el_ciclo_real_SI_descuenta_el_serigrafiado(app, db_clean):
    """Lo que el fixture tapaba: sin tocar el cache a mano, la Salida se registraba en CERO."""
    from database import get_db
    _limpiar(app); _sembrar(app)
    c = _cli(app)
    _ciclo_hasta_liberado(app, c)

    assert _stock(app, BASE) == 700, 'el base debería haber salido una sola vez (a marcar)'
    assert _stock(app, SERIG) == 300, 'el serigrafiado liberado tiene que estar disponible'

    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        from blueprints.programacion import _descontar_mee_envasado
        _descontar_mee_envasado(cur, PROD_ID, 'ZZLOTE', 300, 300, 'test')
        conn.commit()

    assert _stock(app, BASE) == 700, 'el base se descontó DOS veces'
    assert _stock(app, SERIG) == 0, \
        ('el serigrafiado NO se descontó · la Salida se registró en cero por el clamp contra el '
         'cache, y el envase queda en el kardex como si no se hubiera usado')


def test_liberar_deja_el_cache_en_sincronia_con_el_kardex(app, db_clean):
    """La causa raíz: `enviar` decrementa el cache del base y nadie lo volvía a subir para el
    serigrafiado. El momento correcto es LIBERAR, que es cuando el envase pasa a ser usable."""
    _limpiar(app); _sembrar(app)
    c = _cli(app)
    _ciclo_hasta_liberado(app, c)
    assert _cache(app, SERIG) == _stock(app, SERIG), \
        'el cache del serigrafiado quedó desalineado del kardex · toda Salida se clampea a cero'
    assert _cache(app, BASE) == _stock(app, BASE), 'el cache del base también quedó desalineado'


def test_una_orden_solo_RECIBIDA_no_redirige_el_descuento(app, db_clean):
    """Recibido = está en CUARENTENA esperando a Calidad, o sea NO se puede usar. Redirigir el
    descuento ahí lo mandaría contra un stock que todavía no existe."""
    from database import get_db
    _limpiar(app); _sembrar(app)
    c = _cli(app)
    r = c.post('/api/programacion/marcacion-orden/enviar',
               json={'serigrafiado_codigo': SERIG, 'cantidad': 300, 'producto': 'ZZ CICLO',
                     'metodo': 'Serigrafia', 'proveedor': 'ZZ Prov', 'produccion_id': PROD_ID},
               headers=csrf_headers())
    assert r.status_code == 200
    with app.app_context():
        oid = get_db().execute(
            "SELECT id FROM marcacion_ordenes WHERE base_codigo=? ORDER BY id DESC LIMIT 1",
            (BASE,)).fetchone()[0]
    assert c.post('/api/programacion/marcacion-orden/%d/recibir' % oid,
                  json={'cantidad_recibida': 300},
                  headers=csrf_headers()).status_code == 200
    # sin liberar: el serigrafiado está en cuarentena
    assert _stock(app, SERIG) == 0

    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        from blueprints.programacion import _descontar_mee_envasado
        res = _descontar_mee_envasado(cur, PROD_ID, 'ZZLOTE2', 300, 300, 'test')
        conn.commit()
    assert res, 'no descontó nada'
    assert res[0]['codigo_descontado'].upper() == BASE, \
        'redirigió a un envase que sigue en cuarentena'


def test_una_salida_que_se_registra_CORTA_no_pasa_en_silencio(app, db_clean):
    """El guard durable: `aplicar_movimiento_mee` clampea contra el cache, así que un cache
    stale convierte un descuento en una Salida de cero SIN un solo error. Eso tiene que quedar
    declarado en el resultado, o el próximo drift vuelve a ser invisible (M4/M100)."""
    from database import get_db
    _limpiar(app); _sembrar(app)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        # cache a cero a propósito, con kardex sano: la firma exacta del drift
        cur.execute("UPDATE maestro_mee SET stock_actual=0 WHERE codigo=?", (BASE,))
        conn.commit()
        from blueprints.programacion import _descontar_mee_envasado
        res = _descontar_mee_envasado(cur, PROD_ID, 'ZZLOTE3', 300, 300, 'test')
        conn.commit()
    assert res, 'no devolvió nada'
    assert res[0].get('cantidad_registrada') == 0
    assert res[0].get('descuento_incompleto') is True, \
        'una Salida que se registró corta tiene que decirlo'


def test_confirmar_la_segunda_tanda_NO_apaga_el_guard_de_stock(app, db_clean):
    """`forzar` ya apagaba el guard de STOCK_INSUFICIENTE (kardex negativo) y el gate de arte de
    Dirección Técnica. Reusarlo para confirmar una segunda tanda apagaría los tres de una."""
    _limpiar(app); _sembrar(app)
    c = _cli(app)
    cuerpo = {'serigrafiado_codigo': SERIG, 'producto': 'ZZ CICLO', 'metodo': 'Serigrafia',
              'proveedor': 'ZZ Prov', 'produccion_id': PROD_ID}
    assert c.post('/api/programacion/marcacion-orden/enviar',
                  json=dict(cuerpo, cantidad=300),
                  headers=csrf_headers()).status_code == 200
    # segunda tanda confirmada, pero pidiendo MÁS de lo que hay (quedan 700)
    r = c.post('/api/programacion/marcacion-orden/enviar',
               json=dict(cuerpo, cantidad=5000, forzar_marcacion=True),
               headers=csrf_headers())
    assert r.status_code == 422, 'confirmar la tanda apagó el guard de stock'
    assert r.get_json().get('codigo') == 'STOCK_INSUFICIENTE'


def test_el_409_dice_QUE_flag_hay_que_reenviar(app, db_clean):
    """Un 409 que dice "confirmá" sin decir con qué se confirma obliga a adivinar, y adivinar
    acá es mandar `forzar` y apagar de más."""
    _limpiar(app); _sembrar(app)
    c = _cli(app)
    cuerpo = {'serigrafiado_codigo': SERIG, 'cantidad': 300, 'producto': 'ZZ CICLO',
              'metodo': 'Serigrafia', 'proveedor': 'ZZ Prov', 'produccion_id': PROD_ID}
    c.post('/api/programacion/marcacion-orden/enviar', json=cuerpo, headers=csrf_headers())
    r = c.post('/api/programacion/marcacion-orden/enviar', json=cuerpo, headers=csrf_headers())
    assert r.status_code == 409
    j = r.get_json()
    assert j.get('codigo') == 'MARCACION_YA_ABIERTA'
    assert j.get('flag') == 'forzar_marcacion', 'el 409 no dice con qué flag se confirma'
