"""La cadena del envase: lo que se COMPRA tiene que ser lo que se DESCUENTA (26-jul).

Sebastián: *"revisemos cómo está el inventario de envase, si realmente trae el envase con sus
partes, y todo lo está juntando, si en necesidades y calendario cuando calcula abastecimiento jala
esos envases, y finalmente los pone disponibles en envasado."*

Al recorrerlo apareció que hay **dos mecanismos para las partes de un envase y no se hablan**:

  · `mee_partes` (frasco → gotero/tapa) lo lee el ABASTECIMIENTO: compra el frasco con sus
    componentes.
  · `producto_presentaciones.tapa_codigo/caja_codigo` lo lee el ENVASADO al cerrar: es lo que
    DESCUENTA del kardex.

Una parte que está en el primero y no en el segundo **se compra y nunca se descuenta**: el stock
de goteros sube en el papel y no baja jamás. Es el patrón M55/M73 otra vez, ahora entre estas dos
tablas. Este diagnóstico mide el daño; estos tests protegen que el diagnóstico no mienta.
"""
from .conftest import TEST_PASSWORD, csrf_headers

RUTA = '/api/admin/diag-envases-partes'


def _login(app, quien):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar como %s' % quien
    return c


def test_solo_admin(app):
    """Expone el maestro de envases y los códigos de los proveedores: va gateado (M95)."""
    anon = app.test_client()
    assert anon.get(RUTA).status_code in (401, 403, 302)
    assert _login(app, 'laura').get(RUTA).status_code in (401, 403)
    assert _login(app, 'sebastian').get(RUTA).status_code == 200


def test_no_escribe_nada(app):
    """Es un diagnóstico: llamarlo dos veces no puede cambiar una sola fila."""
    from database import get_db
    c = _login(app, 'sebastian')

    def _foto():
        with app.app_context():
            return get_db().execute(
                "SELECT COUNT(*) FROM mee_partes").fetchone()[0]
    antes = _foto()
    c.get(RUTA); c.get(RUTA)
    assert _foto() == antes, 'el diagnóstico escribió en mee_partes'


def test_detecta_la_parte_que_se_compra_y_no_se_descuenta(app):
    """Con dientes: se siembra el caso exacto (un frasco con gotero en `mee_partes`, y una
    presentación que usa ese frasco pero NO declara el gotero como tapa) y el diagnóstico tiene
    que señalarlo. Si no lo detecta, no sirve para dimensionar nada."""
    from database import get_db
    ENV, GOTERO, PROD = 'ZZTEST-FR-30', 'ZZTEST-GOTERO', 'ZZTEST PRODUCTO ENVASE'
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        # limpiar ANTES (la BD de tests es compartida y en PG persiste · M103)
        cur.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
        cur.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cur.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                    "creado_at) VALUES (?,?,?,1,'2026-07-26')",
                    (ENV, GOTERO, 'Gotero del frasco de 30'))
        cur.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                    "etiqueta, volumen_ml, envase_codigo, activo) VALUES (?,?,?,30,?,1)",
                    (PROD, 'V30', '30 ml', ENV))
        conn.commit()
    try:
        d = _login(app, 'sebastian').get(RUTA).get_json()
        casos = d['se_compra_y_no_se_descuenta']
        mio = [x for x in casos if x['envase'] == ENV]
        assert mio, ('no detectó el gotero que se compra y no se descuenta · casos: %d'
                     % len(casos))
        assert mio[0]['parte_que_se_compra'] == GOTERO
        assert mio[0]['se_descuenta'] is False
        assert d['resumen']['partes_huerfanas'] >= 1
    finally:
        with app.app_context():
            conn = get_db()
            conn.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
            conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
            conn.commit()


def test_no_marca_la_parte_que_SI_se_descuenta(app):
    """La contracara: si la presentación declara el gotero como tapa, ya se descuenta y NO debe
    aparecer. Un diagnóstico que marca todo no distingue nada."""
    from database import get_db
    ENV, GOTERO, PROD = 'ZZTEST-FR-15', 'ZZTEST-GOTERO-OK', 'ZZTEST PRODUCTO ENVASE OK'
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
        cur.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cur.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                    "creado_at) VALUES (?,?,'Gotero',1,'2026-07-26')", (ENV, GOTERO))
        cur.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                    "etiqueta, volumen_ml, envase_codigo, tapa_codigo, activo) "
                    "VALUES (?,?,?,15,?,?,1)", (PROD, 'V15', '15 ml', ENV, GOTERO))
        conn.commit()
    try:
        d = _login(app, 'sebastian').get(RUTA).get_json()
        mio = [x for x in d['se_compra_y_no_se_descuenta'] if x['envase'] == ENV]
        assert not mio, 'marcó como huérfana una parte que SÍ se descuenta: %s' % mio
    finally:
        with app.app_context():
            conn = get_db()
            conn.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
            conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
            conn.commit()


def test_declara_los_chequeos_que_no_corrieron(app):
    """Un diagnóstico con un chequeo caído que devuelve lista vacía MIENTE (M100). Tiene que
    decir cuáles no corrieron."""
    d = _login(app, 'sebastian').get(RUTA).get_json()
    assert 'checks_fallidos' in d
    assert d['ok'] is (len(d['checks_fallidos']) == 0)
    for clave in ('maestro', 'partes', 'presentaciones', 'resumen'):
        assert clave in d, 'falta %s en la respuesta' % clave
