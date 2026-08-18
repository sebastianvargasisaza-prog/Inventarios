# -*- coding: utf-8 -*-
"""El cierre de envasado mueve el KARDEX y el CACHE juntos · y valida el código.

`cerrar-envasado` y `cerrar-acondicionamiento` insertaban la Salida a mano y NO tocaban
`maestro_mee.stock_actual`: el cache quedaba alto después de cada cierre y sólo lo realineaba el
cron de las 3 AM. Entre medias, todo lo que clampea contra ese cache trabajaba inflado. Tampoco
validaban que el código existiera, así que uno mal escrito entraba como stock fantasma que nadie
puede reponer (M100) -- y en acondicionamiento los códigos los **teclea el operario**.

⚠ **Por qué NO se usa `aplicar_movimiento_mee` acá**, que sería lo obvio: ese helper CLAMPEA la
Salida contra `maestro_mee.stock_actual`, y M26 dice que el stock canónico es la SUMA DEL KARDEX,
no el cache. Lo probé y el gate lo cazó: con el cache en 0 -- que es como siembra a propósito el
fixture de `test_envase_partes_se_descuentan` -- la Salida se registraba en CERO. El envase se usó
y el kardex seguía diciendo que estaba en bodega. Eso es peor que el doble descuento y ya había
pasado una vez (M153).

Entonces: el kardex registra lo que de verdad se consumió (completo) y el cache se mueve con el
MISMO delta. En el caso sano queda exacto y sin drift; si el cache venía mal, el kardex igual dice
la verdad y el cron lo realinea.
"""
import json
import os
import re

PROD = 'ZZ PRODUCTO CANON'
FRASCO = 'MEE-ZZC-FRASCO'
LOTE = 'ZZC-LOTE-1'


def _sin_comentarios(txt):
    fuera = []
    for ln in txt.splitlines():
        if ln.strip().startswith('#'):
            continue
        fuera.append(re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


def _cuerpo(src, firma):
    """El texto de UNA función, hasta donde de verdad termina.

    ⚠ Antes se recortaba con una ventana FIJA (`src[i:i+16000]`), y eso hacía que el guard
    midiera código ajeno: `cerrar_acondicionamiento_ebr` termina a los ~3.900 caracteres, así
    que la ventana leía 12.000 más de las funciones que vienen después. El 17-ago encontró ahí
    el `INSERT INTO movimientos_mee` de `crear_planta_demo` -- que no tiene nada que ver con
    cerrar un lote -- y falló acusando al cierre de no validar el código, con el cierre sano y
    delegando bien en la puerta compartida.

    Un trinquete anclado por CONTEO DE CARACTERES lo secuestra cualquier función que se escriba
    más abajo, y deja de proteger sin avisar (M151/M157). Acotado al cuerpo real, además muerde
    más: mide el cierre, no lo que quede a 15.000 caracteres de distancia.
    """
    i = src.find(firma)
    assert i > 0, firma
    resto = src[i + len(firma):]
    m = re.search(chr(10) + r'(?:@|def )', resto)
    return src[i:i + len(firma) + (m.start() if m else len(resto))]


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (FRASCO,))
        c.execute("DELETE FROM maestro_mee WHERE codigo=?", (FRASCO,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_checklist WHERE produccion_id IN "
                  " (SELECT id FROM produccion_programada WHERE producto=?)", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        c.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id IN "
                  " (SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZC-%')")
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZC-%'")
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        conn.commit()


def _sembrar(app, cache=5000, kardex=5000, uds=300):
    from database import get_db
    _limpiar(app)
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, unidad, stock_actual, "
                  " stock_minimo, estado, fecha_creacion) "
                  "VALUES (?, 'ZZ frasco', 'Frasco', 'und', ?, 0, 'Activo', '2026-08-05')",
                  (FRASCO, cache))
        if kardex:
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, estado) "
                      "VALUES (?, 'Entrada', ?, 'ZZC-SEED', 'VIGENTE')", (FRASCO, kardex))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  " etiqueta, volumen_ml, envase_codigo, activo, es_default) "
                  "VALUES (?, 'ZZC30', 'ZZ 30 ml', 30, ?, 1, 1)", (PROD, FRASCO))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?, '2026-08-05', 10, 'pendiente', 'eos_plan')", (PROD,))
        pid = c.lastrowid
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", (PROD,))
        mbr = c.lastrowid
        c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                  " fase, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, "
                  " produccion_id) VALUES (?,1,?,?, 'envasado', 'en_proceso', 'zz', "
                  " datetime('now','utc'), 10000, ?)", (mbr, LOTE + '-OF', LOTE, pid))
        ebr = c.lastrowid
        c.execute("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, unidades) "
                  "VALUES (?, 'ZZC30', ?)", (ebr, uds))
        conn.commit()
    return pid, ebr


def _cerrar(admin_client, ebr):
    from .conftest import csrf_headers
    return admin_client.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, data=json.dumps({}),
                             headers=csrf_headers(), content_type='application/json')


def _cache(app):
    from database import get_db
    with app.app_context():
        return float(get_db().execute("SELECT COALESCE(stock_actual,0) FROM maestro_mee "
                                      " WHERE codigo=?", (FRASCO,)).fetchone()[0])


def _kardex(app):
    from database import get_db
    with app.app_context():
        return float(get_db().execute(
            "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='entrada' THEN cantidad "
            "                         WHEN LOWER(tipo)='salida' THEN -cantidad ELSE cantidad END),0) "
            "  FROM movimientos_mee WHERE mee_codigo=?", (FRASCO,)).fetchone()[0])


def test_el_cache_BAJA_con_el_envasado(app, admin_client, db_clean):
    """El `INSERT` a mano dejaba `stock_actual` intacto: el cache quedaba alto hasta el cron de
    las 3 AM, y entre medias todo lo que clampea contra él trabajaba inflado."""
    pid, ebr = _sembrar(app, cache=5000, kardex=5000, uds=300)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert _cache(app) == 4700, 'el cache no bajó con el envasado · quedó en %s' % _cache(app)
    _limpiar(app)


def test_el_cache_y_el_KARDEX_quedan_iguales(app, admin_client, db_clean):
    """Drift = 0 en el caso sano: los dos se mueven con el mismo delta."""
    pid, ebr = _sembrar(app, cache=5000, kardex=5000, uds=300)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert _cache(app) == _kardex(app), 'drift: cache %s vs kardex %s' % (_cache(app), _kardex(app))
    _limpiar(app)


def test_el_KARDEX_registra_lo_consumido_aunque_el_cache_este_en_CERO(app, admin_client, db_clean):
    """⚠ EL test que importa, y el que tumbó mi primer intento.

    Con el cache en 0 y stock real en el kardex, usar `aplicar_movimiento_mee` registraba una
    Salida de CERO: el envase se usaba y el kardex seguía diciendo que estaba en bodega -- peor
    que el doble descuento (M153). El stock canónico es la SUMA DEL KARDEX (M26), así que la
    Salida se registra completa y el cache se realinea solo.
    """
    pid, ebr = _sembrar(app, cache=0, kardex=5000, uds=300)
    k0 = _kardex(app)
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    assert k0 - _kardex(app) == 300, \
        'el envase NO salió del kardex teniendo stock real · el cache no puede decidir esto'
    _limpiar(app)


def test_un_codigo_que_no_existe_NO_entra_como_fantasma(app, admin_client, db_clean):
    """Un código mal escrito que entra igual crea stock que nadie puede reponer (M100)."""
    from database import get_db
    pid, ebr = _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE producto_presentaciones SET envase_codigo='MEE-ZZC-NOEXISTE' "
                     " WHERE producto_nombre=?", (PROD,))
        conn.commit()
    r = _cerrar(admin_client, ebr)
    assert r.status_code in (200, 201), r.data[:300]
    with app.app_context():
        n = get_db().execute("SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo=?",
                             ('MEE-ZZC-NOEXISTE',)).fetchone()[0]
    assert n == 0, 'entró un movimiento de un código que no existe en el maestro'
    _limpiar(app)


def test_el_codigo_rechazado_se_DECLARA(app, admin_client, db_clean):
    """Un rechazo silencioso deja el material sin descontar y a nadie enterado (M4/M124)."""
    from database import get_db
    pid, ebr = _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE producto_presentaciones SET envase_codigo='MEE-ZZC-NOEXISTE' "
                     " WHERE producto_nombre=?", (PROD,))
        conn.commit()
    assert _cerrar(admin_client, ebr).status_code in (200, 201)
    with app.app_context():
        fila = get_db().execute(
            "SELECT COALESCE(despues,'') FROM audit_log "
            " WHERE accion='CERRAR_ENVASADO_DESCONTAR_MEE' ORDER BY id DESC LIMIT 1").fetchone()
    assert fila and 'MEE-ZZC-NOEXISTE' in fila[0], \
        'el audit no dice que se saltó ese código · ' + str(fila)[:200]
    _limpiar(app)


def test_los_DOS_cierres_mueven_el_cache(app, db_clean):
    """M45: el `INSERT` sin tocar el cache vivía en envasado Y en acondicionamiento.

    ⚠ 17-ago: acondicionamiento dejó de tener el SQL adentro -- lo delega en
    `descontar_mee_del_lote`, la puerta que comparte con la pantalla vieja para que el envase no
    salga dos veces (INV-24). Este guard buscaba el texto DENTRO de la función y quedó rojo con
    el código sano: fijaba la IMPLEMENTACIÓN (que el SQL estuviera inline) en vez de la GARANTÍA
    (que quien descuenta valide el código, registre la Salida y mueva el cache con el mismo
    delta). Ahora acepta las dos formas -- inline o delegando -- y en el que delega exige que el
    helper cumpla las tres cosas.
    """
    src = _sin_comentarios(open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'api/blueprints/brd.py'), encoding='utf-8').read())
    for fn, quien in (('def cerrar_envasado_ebr', 'envasado'),
                      ('def cerrar_acondicionamiento_ebr', 'acondicionamiento'),
                      ('def descontar_mee_del_lote', 'la puerta compartida')):
        bloque = _cuerpo(src, fn)
        j = bloque.find("INSERT INTO movimientos_mee")
        if j < 0:
            # No lo hace acá: entonces tiene que DELEGAR en la puerta compartida, nunca
            # simplemente haber dejado de descontar.
            assert 'descontar_mee_del_lote(' in bloque, (
                'el cierre de %s ya no registra la Salida ni delega en la puerta compartida'
                % quien)
            continue
        # el UPDATE del cache va junto al INSERT, no en otra parte del archivo
        assert 'UPDATE maestro_mee SET stock_actual' in bloque[j:j + 1500], \
            'el cierre de %s registra la Salida y NO mueve el cache' % quien
        assert 'SELECT 1 FROM maestro_mee' in bloque[max(0, j - 1500):j], \
            'el cierre de %s no valida que el código exista' % quien


def test_el_cierre_de_acondicionamiento_mueve_kardex_y_cache_DE_VERDAD(app, db_clean):
    """La misma garantía, medida EJECUTANDO el cierre en vez de leyendo el fuente (M170).

    Un guard de texto dice dónde está escrito el SQL; éste dice qué le pasó al inventario.
    """
    import sqlite3
    from .conftest import TEST_PASSWORD, csrf_headers
    cod = 'ZZ-OA-CACHE'

    def _sql(q, p=()):
        cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
        try:
            cur = cn.execute(q, p); cn.commit(); return cur
        finally:
            cn.close()

    def _uno(q, p=()):
        cn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
        try:
            return cn.execute(q, p).fetchone()
        finally:
            cn.close()

    _sql("DELETE FROM movimientos_mee WHERE mee_codigo=?", (cod,))
    _sql("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
    _sql("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
         "VALUES (?, 'Estuche', 900, 'Activo')", (cod,))
    mbr = _sql("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
               "VALUES ('ZZ-OA-CACHE-PROD', 1, 'aprobado', 1000, 'sebastian')").lastrowid
    ebr = _sql("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, "
               " fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
               "VALUES (?, 1, 'ZZOACACHE-OA', 'ZZOACACHE', 'iniciado', 'acondicionamiento', "
               " 'sebastian', datetime('now','utc'), 1000)", (mbr,)).lastrowid

    cli = app.test_client()
    r = cli.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
                 headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    r = cli.post('/api/brd/ebr/%d/cerrar-acondicionamiento' % ebr,
                 json={'materiales': [{'codigo': cod, 'cantidad': 40}]}, headers=h)
    assert r.status_code == 200, r.data[:300]

    n, total = _uno("SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos_mee "
                    " WHERE mee_codigo=? AND tipo='Salida'", (cod,))
    assert (n, total) == (1, 40), ('el kardex no registró la Salida', n, total)
    assert _uno("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))[0] == 860, \
        'el cache no se movió con el MISMO delta que el kardex'
