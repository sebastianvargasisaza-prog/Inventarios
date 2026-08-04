"""El envase que va a serigrafía no puede descontarse dos veces (Catalina, 4-ago).

Sebastián: *"Catalina dice que descuenta doble. Está en Compras, donde ella solicita alistar
envases que serán enviados a serigrafía: salen de la planta y después ingresan, se vuelven a
recepcionar, cambian de nombre al volver porque ya tienen serigrafía"*.

Dos causas reales, las dos verificadas contra el código:

**A · Producción descontaba el BASE otra vez.** El descuento de envasado usa el código de
`producto_presentaciones` (vía `produccion_checklist`), que sigue apuntando al base. Pero ese
base YA SALIÓ del kardex cuando se envió a marcar. Resultado: el base se descuenta dos veces, y
el serigrafiado -- que es el que de verdad se usa -- no se consume nunca: su stock sólo crece.

**B · Enviar no tenía guard anti-duplicado.** "Solicitar alistamiento" llama al MISMO endpoint
que enviar a marcación, y ese endpoint insertaba la orden sin mirar si ya había una abierta. Dos
clics = dos órdenes = dos Salidas del base. El CAS protege TRANSICIONES, no la CREACIÓN (M63).

El arreglo de (A) no adivina: la orden guarda `produccion_id`, `base_codigo` y
`serigrafiado_codigo`, así que "este base, para esta producción, volvió como aquel serigrafiado"
es un hecho registrado, no un parecido (M19).
"""
from .conftest import TEST_PASSWORD, csrf_headers

BASE = 'ZZMEE-BASE'
SERIG = 'ZZMEE-SERIG'


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
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'ZZMEE%'")
        cur.execute("DELETE FROM marcacion_ordenes WHERE base_codigo LIKE 'ZZMEE%'")
        cur.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZMEE%'")
        cur.execute("DELETE FROM produccion_checklist WHERE mee_codigo_asignado LIKE 'ZZMEE%'")
        conn.commit()


def _sembrar(app, stock_base=1000):
    """El base con stock, y el serigrafiado apuntando a él por `material_referencia`.

    ⚠ `stock_actual` se siembra junto con el movimiento: `aplicar_movimiento_mee` CLAMPEA la
    Salida contra esa columna (si la deja en 0, registra una Salida de 0 y el test mide otra
    cosa). El stock que se CONSULTA sigue siendo `SUM(movimientos_mee)` (M26).
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual) "
                    "VALUES (?,?, 'Activo', ?)", (BASE, 'Frasco sin serigrafía', stock_base))
        cur.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual, "
                    "material_referencia) VALUES (?,?, 'Activo', 0, ?)",
                    (SERIG, 'Frasco CON serigrafía', BASE))
        cur.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, "
                    "responsable) VALUES (?, 'Entrada', ?, 'und', 'SEED', 'test')",
                    (BASE, stock_base))
        conn.commit()


def _stock(app, codigo):
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _get_mee_stock
        return float((_get_mee_stock(get_db()) or {}).get(codigo.upper(), 0) or 0)


def _enviar(cli, **kw):
    body = {'serigrafiado_codigo': SERIG, 'cantidad': 300, 'producto': 'ZZ PROD',
            'metodo': 'Serigrafia', 'proveedor': 'ZZ Prov'}
    body.update(kw)
    return cli.post('/api/programacion/marcacion-orden/enviar', json=body,
                    headers=csrf_headers())


# ── B · el doble clic ────────────────────────────────────────────────────────

def test_enviar_DOS_veces_no_descuenta_dos_veces(app, db_clean):
    """"Solicitar alistamiento" llama a este mismo endpoint · dos clics descontaban 600 donde
    salieron 300."""
    _limpiar(app); _sembrar(app, stock_base=1000)
    c = _cli(app)
    r1 = _enviar(c, produccion_id=None)
    assert r1.status_code == 200, r1.data[:250]
    assert _stock(app, BASE) == 700, 'la primera salida no descontó bien'

    r2 = _enviar(c, produccion_id=None)
    assert r2.status_code == 409, 'dejó crear una segunda orden abierta del mismo envase'
    assert r2.get_json()['codigo'] == 'MARCACION_YA_ABIERTA'
    assert r2.get_json()['puede_forzar'] is True
    assert _stock(app, BASE) == 700, 'DESCONTÓ DOS VECES'


def test_una_segunda_tanda_LEGITIMA_se_puede_forzar(app, db_clean):
    """Con dientes al revés: mandar otra tanda del mismo envase es válido · el guard avisa, no
    prohíbe."""
    _limpiar(app); _sembrar(app, stock_base=1000)
    c = _cli(app)
    _enviar(c, produccion_id=None)
    r = _enviar(c, produccion_id=None, forzar=True)
    assert r.status_code == 200, r.data[:250]
    assert _stock(app, BASE) == 400, 'con forzar debería descontar la segunda tanda'


def test_el_guard_distingue_PRODUCCIONES_distintas(app, db_clean):
    """Dos producciones distintas del mismo envase son dos envíos legítimos."""
    _limpiar(app); _sembrar(app, stock_base=1000)
    c = _cli(app)
    assert _enviar(c, produccion_id=901).status_code == 200
    assert _enviar(c, produccion_id=902).status_code == 200, \
        'bloqueó un envío de OTRA producción'
    assert _stock(app, BASE) == 400


# ── A · producción descuenta el serigrafiado, no el base otra vez ────────────

def _orden_recibida(app, produccion_id):
    """Simula el ciclo completo: se envió, volvió y Calidad lo liberó."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("UPDATE marcacion_ordenes SET estado='liberado', cantidad_recibida=300 "
                    "WHERE produccion_id=? AND base_codigo=?", (produccion_id, BASE))
        # el serigrafiado ya entró al kardex y está liberado
        cur.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, "
                    "responsable) VALUES (?, 'Entrada', 300, 'und', 'MARCACION-RET', 'test')",
                    (SERIG,))
        cur.execute("UPDATE maestro_mee SET stock_actual=300 WHERE codigo=?", (SERIG,))
        conn.commit()


def test_al_producir_se_descuenta_el_SERIGRAFIADO_no_el_base(app, db_clean):
    """El base ya salió al enviarlo a marcar. Descontarlo otra vez lo cuenta dos veces, y el
    serigrafiado -- el que de verdad se usa -- no se consume nunca."""
    from database import get_db
    _limpiar(app); _sembrar(app, stock_base=1000)
    c = _cli(app)
    assert _enviar(c, produccion_id=910).status_code == 200
    assert _stock(app, BASE) == 700
    _orden_recibida(app, 910)
    assert _stock(app, SERIG) == 300

    # el checklist de la producción todavía apunta al BASE (es lo que hace `producto_presentaciones`)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, fecha_planeada, item_tipo, "
                    "descripcion, mee_codigo_asignado, cantidad_unidades) "
                    "VALUES (?, 'ZZ PROD', date('now','-5 hours'), 'envase', ?, ?, 300)", (910, 'Frasco', BASE))
        conn.commit()
        from blueprints.programacion import _descontar_mee_envasado
        _descontar_mee_envasado(cur, 910, 'ZZLOTE', 300, 300, 'test')
        conn.commit()

    assert _stock(app, BASE) == 700, ('el base se descontó DOS veces · debería quedar en 700 '
                                      '(salió una sola vez, a marcación)')
    assert _stock(app, SERIG) == 0, 'el serigrafiado no se consumió · su stock sólo crecería'


def test_sin_marcacion_el_descuento_NO_se_redirige(app, db_clean):
    """Con dientes: si redirigiera siempre, un envase que nunca fue a serigrafía dejaría de
    descontarse y el kardex mostraría stock que no existe."""
    from database import get_db
    _limpiar(app); _sembrar(app, stock_base=1000)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, fecha_planeada, item_tipo, "
                    "descripcion, mee_codigo_asignado, cantidad_unidades) "
                    "VALUES (?, 'ZZ PROD', date('now','-5 hours'), 'envase', ?, ?, 200)", (920, 'Frasco', BASE))
        conn.commit()
        from blueprints.programacion import _descontar_mee_envasado
        _descontar_mee_envasado(cur, 920, 'ZZLOTE2', 200, 200, 'test')
        conn.commit()
    assert _stock(app, BASE) == 800, 'sin marcación de por medio el base SÍ se descuenta'


def test_una_orden_TODAVIA_AFUERA_no_redirige(app, db_clean):
    """Si el envase todavía está en serigrafía, el serigrafiado no existe para usarse · redirigir
    ahí descontaría algo que no volvió."""
    from database import get_db
    _limpiar(app); _sembrar(app, stock_base=1000)
    c = _cli(app)
    assert _enviar(c, produccion_id=930).status_code == 200   # queda en estado 'enviado'
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, fecha_planeada, item_tipo, "
                    "descripcion, mee_codigo_asignado, cantidad_unidades) "
                    "VALUES (?, 'ZZ PROD', date('now','-5 hours'), 'envase', ?, ?, 100)", (930, 'Frasco', BASE))
        conn.commit()
        from blueprints.programacion import _descontar_mee_envasado
        _descontar_mee_envasado(cur, 930, 'ZZLOTE3', 100, 100, 'test')
        conn.commit()
    # 1000 - 300 (envío) - 100 (producción sobre el base, porque el serigrafiado no volvió)
    assert _stock(app, BASE) == 600
    assert _stock(app, SERIG) == 0
