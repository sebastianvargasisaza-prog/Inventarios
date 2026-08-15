"""El rótulo F02 sale para FIRMAR, y sólo de los equipos que se van a usar (15-ago-2026).

Sebastián, abriendo los rótulos de limpieza desde Registrar Producción:
  1. *"siempre sale que fui yo sin importar el usuario"*
  2. *"no van a usar todos los equipos, deberían poder seleccionarlos... que primero
     pregunte cuáles usarán para que sean esos rótulos los que se impriman"*

**Lo primero no era la sesión**: el rótulo tomaba el ÚLTIMO ciclo de limpieza del área, y
en producción ése era una demo del 24-jun firmada por él. Así que TODAS las salas salían
de la impresora **ya firmadas por alguien que no ejecutó esa limpieza**, con "SIMULACRO
Demo" como producto a elaborar. Un registro regulado prefirmado por quien no hizo el acto
es un registro falso — y encima invita a pegarlo tal cual.

Lo que fija este guard:
  · que una firma vieja NO se preimprima (sale la línea en blanco para firmar);
  · que una limpieza RECIENTE sí salga firmada — si no, el arreglo rompería el caso bueno;
  · que se pueda elegir qué equipos se imprimen, y que se impriman SÓLO ésos;
  · que la URL vieja (`?todos=1`) siga funcionando: está enlazada desde el dashboard y una
    URL viva no se rompe (M120).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _area():
    """El id de un área limpiable cualquiera (las que la pantalla lista)."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute(
            "SELECT id, codigo FROM areas_planta WHERE activo=1 "
            "AND (tipo='produccion' OR codigo IN ('DISP','ACOND')) "
            "ORDER BY orden, codigo LIMIT 1").fetchone()
    finally:
        conn.close()
    assert r, "no hay áreas limpiables sembradas"
    return r[0], r[1]


def _ciclo(area_id, area_codigo, realizado_at, quien="sebastian"):
    _exec("DELETE FROM rotulos_limpieza WHERE area_id=?", (area_id,))
    return _exec(
        "INSERT INTO rotulos_limpieza (area_id, area_codigo, producto_elaborar, "
        "sanitizante, detergente, realizado_por, realizado_at, estado) "
        "VALUES (?,?,'SIMULACRO Demo','Alcohol 70%','Detergente Neutro Industrial',?,?,'limpiando')",
        (area_id, area_codigo, quien, realizado_at))


def _hoy_menos(dias):
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(hours=5) - timedelta(days=dias)).strftime(
        "%Y-%m-%d %H:%M:%S")


def test_una_firma_vieja_no_se_preimprime(app, db_clean):
    """El caso real: una demo de hace dos meses firmando todos los rótulos de la planta."""
    aid, acod = _area()
    _ciclo(aid, acod, "2026-06-24 23:16:56")
    c = _login(app)
    html = c.get("/planta/rotulo-limpieza/%d/pdf" % aid).data.decode("utf-8")
    assert "Firma electr" not in html, (
        "el rótulo sale prefirmado con un ciclo viejo: es un registro falso")
    assert "Firma y fecha" in html, "no dejó la línea en blanco para firmar"
    assert "SIMULACRO Demo" not in html, (
        "arrastra el producto del ciclo viejo: no es el que se va a elaborar ahora")


def test_una_limpieza_reciente_si_sale_firmada(app, db_clean):
    """El borde que hace que el arreglo no rompa el caso bueno (M96)."""
    aid, acod = _area()
    _ciclo(aid, acod, _hoy_menos(0), quien="mayerlin")
    c = _login(app)
    html = c.get("/planta/rotulo-limpieza/%d/pdf" % aid).data.decode("utf-8")
    assert "Firma electr" in html, "una limpieza de hoy tiene que salir firmada"
    assert "mayerlin" in html.lower(), "no muestra a quien la ejecutó"


def test_el_limite_de_vigencia_se_respeta(app, db_clean):
    """Justo adentro sale firmado; justo afuera, en blanco."""
    from api.blueprints.programacion import (_rotulo_firma_vigente,
                                             _ROTULO_FIRMA_VIGENTE_DIAS)
    assert _rotulo_firma_vigente(_hoy_menos(0)) is True
    assert _rotulo_firma_vigente(_hoy_menos(_ROTULO_FIRMA_VIGENTE_DIAS + 1)) is False
    # sin fecha o con basura se trata como vieja: el formato sale en blanco
    assert _rotulo_firma_vigente("") is False
    assert _rotulo_firma_vigente("no es una fecha") is False


def test_primero_pregunta_que_equipos(app, db_clean):
    """Sin elegir nada, la pantalla ofrece el selector en vez de imprimir todo."""
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza").data.decode("utf-8")
    assert "Imprimir los seleccionados" in html, "no ofrece elegir"
    assert "function imprimir()" in html, "falta la función que arma la impresión"
    assert "ESTADO DE LIMPIEZA" not in html.upper(), (
        "imprimió los rótulos sin preguntar qué equipos se van a usar")


def test_imprime_solo_los_equipos_elegidos(app, db_clean):
    """El punto del pedido: un rótulo por equipo que SÍ se va a usar."""
    aid, acod = _area()
    from api.blueprints.programacion import _equipos_de_area
    from api.database import get_db
    with app.app_context():
        eqs = _equipos_de_area(get_db(), acod)
    if len(eqs) < 2:
        import pytest
        pytest.skip("el área sembrada no tiene dos equipos para distinguir")
    elegido, descartado = eqs[0], eqs[1]
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?equipos=%s" % elegido["codigo"]).data.decode("utf-8")
    assert elegido["codigo"] in html, "no salió el rótulo del equipo elegido"
    assert descartado["codigo"] not in html, (
        "salió el rótulo de un equipo que no se eligió: eso es papel descartado o un "
        "rótulo pegado donde no corresponde")


def test_la_url_vieja_sigue_funcionando(app, db_clean):
    """Está enlazada desde el dashboard: una URL viva no se rompe (M120)."""
    c = _login(app)
    r = c.get("/planta/rotulos-limpieza?todos=1")
    assert r.status_code == 200
    html = r.data.decode("utf-8")
    assert "ESTADO DE LIMPIEZA" in html.upper(), "el modo 'todos' dejó de imprimir"


def test_los_botones_dicen_lo_que_hacen(app, db_clean):
    """"Imprimir TODOS" tiene que seguir imprimiendo todos: si el botón promete una cosa
    y hace otra, se deja de creer en la pantalla (M161). Y el de Registrar Producción
    ahora pregunta qué equipos, así que su texto lo dice."""
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    assert "/planta/rotulos-limpieza?todos=1" in html, (
        "el botón 'Imprimir TODOS' perdió el modo todos: abriría el selector")
    assert "qu&eacute; equipos se van a usar" in html or "qué equipos se van a usar" in html, (
        "el botón de Registrar Producción no avisa que ahora se eligen los equipos")
