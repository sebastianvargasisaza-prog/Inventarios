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
    """M45: el `INSERT` sin tocar el cache vivía en envasado Y en acondicionamiento. El guard
    cubre los dos, y fue el que encontró el hermano que se me había pasado."""
    src = _sin_comentarios(open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'api/blueprints/brd.py'), encoding='utf-8').read())
    for fn, quien in (('def cerrar_envasado_ebr', 'envasado'),
                      ('def cerrar_acondicionamiento_ebr', 'acondicionamiento')):
        i = src.find(fn)
        assert i > 0, fn
        bloque = src[i:i + 16000]
        j = bloque.find("INSERT INTO movimientos_mee")
        assert j > 0, 'el cierre de %s ya no registra la Salida' % quien
        # el UPDATE del cache va junto al INSERT, no en otra parte del archivo
        assert 'UPDATE maestro_mee SET stock_actual' in bloque[j:j + 1500], \
            'el cierre de %s registra la Salida y NO mueve el cache' % quien
        assert 'SELECT 1 FROM maestro_mee' in bloque[max(0, j - 1500):j], \
            'el cierre de %s no valida que el código exista' % quien
