"""Verificar la limpieza DEVUELVE la sala a LIBRE · y el demo se puede caminar (16-ago-2026).

Sebastián, trabado al arrancar el demo: *"no me deja, porque dice que las áreas de fabricación
están sucias · creo que eso no está siendo útil el plano y limitar eso, ¿será que lo
eliminamos?"*.

Tenía razón en el síntoma y el diagnóstico estaba en otro lado. El circuito del área es:

    producir → OCUPADA → terminar → SUCIA → limpiar → LIMPIANDO → Calidad verifica → LIBRE

y el último paso **no existía**: `planta_rotulo_limpieza_verificar` marcaba el rótulo como
verificado, escribía en `area_eventos` que el área pasaba a 'libre'… y **nunca tocaba
`areas_planta`**. Así que la limpieza se hacía, Calidad la firmaba con su e-firma, y la sala se
quedaba en 'limpiando' para siempre -- el registro diciendo una cosa y la tabla otra (M19).

Como el sugeridor de área descarta lo que no está libre, la planta se auto-bloqueaba sola. Y la
otra vía a LIBRE (`/planta/despeje-linea`) **no estaba enlazada desde ninguna pantalla**, con el
mensaje de error mandando a `/api/planta/despeje-linea`, una ruta que nunca existió (M202).

Por eso NO se eliminó el control: el despeje de línea está en `PRD-PRO-001` (lo firma el Jefe de
Producción y lo verifica Calidad) y el rótulo F02 se apoya en ese mismo estado. Lo que faltaba
era que el ciclo pudiera cerrarse.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers, contenido_pantalla


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _area_sucia(app, codigo="ZZLIMP"):
    """Una sala de prueba en estado SUCIA, con nombre fijo y limpiando ANTES (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM areas_planta WHERE codigo=?", (codigo,))
        cur.execute("INSERT INTO areas_planta (codigo, nombre, tipo, estado, activo, "
                    "puede_producir) VALUES (?,?,'produccion','sucia',1,1)",
                    (codigo, "Sala de prueba limpieza"))
        aid = int(cur.execute("SELECT id FROM areas_planta WHERE codigo=?",
                              (codigo,)).fetchone()[0])
        conn.commit()
    return aid


def _firmar(cli, *, record_table, record_id, meaning):
    """La e-firma de verdad (Part 11) · verificar la limpieza la exige, y está bien que lo haga."""
    rc = cli.post("/api/sign/challenge", json={"password": TEST_PASSWORD},
                  headers=csrf_headers())
    assert rc.status_code == 200, rc.data[:200]
    rs = cli.post("/api/sign", json={
        "record_table": record_table, "record_id": str(record_id),
        "meaning": meaning, "challenge_token": rc.get_json()["token"],
    }, headers=csrf_headers())
    assert rs.status_code == 201, rs.data[:250]
    return rs.get_json()["signature_id"]


def _estado(app, aid):
    from database import get_db
    with app.app_context():
        return (get_db().execute("SELECT estado FROM areas_planta WHERE id=?",
                                 (aid,)).fetchone()[0] or "").lower()


# ══ el ciclo cierra ═════════════════════════════════════════════════════════════

def test_verificar_la_limpieza_deja_la_sala_LIBRE(app, db_clean):
    """El corazón del arreglo: sin esto, limpiar no sirve de nada."""
    aid = _area_sucia(app)
    cli = _login(app, "mayerlin")
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    r = cli.post("/api/planta/rotulo-limpieza/%d/realizar" % aid,
                 json={"sanitizante": "Alcohol 70", "detergente": "Neutro"}, headers=h)
    assert r.status_code in (200, 201), r.data[:250]
    assert _estado(app, aid) == "limpiando", "la limpieza registrada no movió la sala"

    qc = _login(app, "laura")
    hq = {"Content-Type": "application/json"}
    hq.update(csrf_headers())
    rid = (r.get_json() or {}).get("rotulo_id")
    sid = _firmar(qc, record_table="rotulos_limpieza", record_id=rid, meaning="revisa")
    rv = qc.post("/api/planta/rotulo-limpieza/%d/verificar" % aid,
                 json={"signature_id": sid}, headers=hq)
    assert rv.status_code in (200, 201), rv.data[:300]
    j = rv.get_json() or {}
    assert j.get("area_liberada") is True, (
        "la respuesta no declara que el área quedó libre · %s" % j.get("mensaje"))
    assert _estado(app, aid) == "libre", (
        "Calidad verificó la limpieza y la sala sigue en %r" % _estado(app, aid))


def test_no_libera_una_sala_con_produccion_adentro(app, db_clean):
    """El borde que hace que el arreglo sea seguro: si mientras tanto arrancó un lote, la sala
    está OCUPADA y ponerla libre borraría que hay producción adentro."""
    aid = _area_sucia(app, "ZZLIMP2")
    from database import get_db
    cli = _login(app, "mayerlin")
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    rr = cli.post("/api/planta/rotulo-limpieza/%d/realizar" % aid,
                  json={"sanitizante": "Alcohol 70"}, headers=h)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=?", (aid,))
        conn.commit()

    qc = _login(app, "laura")
    hq = {"Content-Type": "application/json"}
    hq.update(csrf_headers())
    rid = (rr.get_json() or {}).get("rotulo_id")
    sid = _firmar(qc, record_table="rotulos_limpieza", record_id=rid, meaning="revisa")
    rv = qc.post("/api/planta/rotulo-limpieza/%d/verificar" % aid,
                 json={"signature_id": sid}, headers=hq)
    assert rv.status_code in (200, 201), rv.data[:300]
    assert (rv.get_json() or {}).get("area_liberada") is False, (
        "liberó una sala ocupada · se perdería que hay un lote adentro")
    assert _estado(app, aid) == "ocupada"


# ══ hay por dónde llegar ════════════════════════════════════════════════════════

def test_la_pantalla_de_despeje_esta_enlazada(app, db_clean):
    """Existía desde mayo y NADIE la enlazaba: la única forma de llegar era escribir la URL de
    memoria. Una capacidad a la que no se puede llegar no existe (M121)."""
    html = contenido_pantalla("dashboard_html", "DASHBOARD_HTML")
    assert "/planta/despeje-linea" in html, (
        "ninguna pantalla lleva al despeje de línea · la sala no se puede devolver a LIBRE")


def test_el_aviso_manda_a_una_ruta_QUE_EXISTE(app, db_clean):
    """El 409 decía 'usar /api/planta/despeje-linea' y esa ruta nunca existió (la real no lleva
    /api). Un aviso que lleva a ninguna parte enseña a ignorar los avisos (M202)."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "programacion.py"),
                  encoding="utf-8").read()
    # sin comentarios: el que está al lado del aviso EXPLICA cuál era la ruta vieja, así que un
    # guard que la busque se encuentra a sí mismo y falla con el código correcto (M154)
    src = re.sub(r"#[^\n]*", "", src)
    i = src.index("'codigo': 'DESPEJE_REQUERIDO'")
    ventana = src[max(0, i - 900):i + 300]
    assert "/api/planta/despeje-linea" not in ventana, (
        "el aviso sigue mandando a la ruta que no existe")
    assert "/planta/despeje-linea" in ventana, "el aviso no dice a dónde ir"

    # y que la ruta a la que manda esté REGISTRADA de verdad, no sea otra vez de memoria
    rutas = {str(r.rule) for r in app.url_map.iter_rules()}
    assert "/planta/despeje-linea" in rutas, "la pantalla del despeje no está registrada"


# ══ el demo se puede caminar ════════════════════════════════════════════════════

def test_el_demo_nace_con_materia_prima(app, db_clean):
    """Sebastián: *"ahora dice stock insuficiente para el demo"*.

    El demo creaba sus MP en el maestro y ninguna entrada al kardex, así que arrancaba con stock
    CERO y se trababa en el primer paso. Es seguro sembrarlo porque `MP-DEMO*` son códigos
    propios del demo: no existe ese material en la realidad, así que no infla ningún inventario.
    """
    from database import get_db
    cli = _login(app, "sebastian")
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    r = cli.post("/api/admin/planta-demo/crear", json={}, headers=h)
    assert r.status_code in (200, 201), r.data[:300]
    with app.app_context():
        for cod in ("MP-DEMO1", "MP-DEMO2"):
            g = get_db().execute(
                "SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END),0) "
                "FROM movimientos WHERE material_id=?", (cod,)).fetchone()[0]
            assert (g or 0) > 0, "%s nace sin stock · el demo se traba al arrancar" % cod


def test_el_demo_siembra_LO_QUE_SU_FORMULA_PIDE(app, db_clean):
    """El caso real, y el que me costó dos vueltas: Sebastián seguía viendo *"Stock insuficiente
    para producir DEMO PLANTA (BORRAR): 2 MP(s) sin stock"* aun con el arreglo desplegado.

    `crear_planta_demo` sólo crea la fórmula **si no existe**, así que un demo creado antes se
    queda con SU fórmula — y yo sembraba stock para una lista fija (`MP-DEMO1/2`) que esa fórmula
    no pedía. El stock caía en códigos que nadie mira (M1: preguntarle a la fuente en vez de
    repetir una lista).
    """
    from database import get_db
    prod = "DEMO PLANTA (BORRAR)"
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        # el demo YA existe con otros materiales, como en producción
        cur.execute("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
        cur.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,))
        cur.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                    "VALUES (?,1,1)", (prod,))
        for cod, pct in (("ZZ-VIEJO-A", 90), ("ZZ-VIEJO-B", 10)):
            cur.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                        "VALUES (?, 'Demo vieja', 1)", (cod,))
            cur.execute("INSERT INTO formula_items (producto_nombre, material_id, "
                        "material_nombre, porcentaje, cantidad_g_por_lote) VALUES (?,?,?,?,?)",
                        (prod, cod, cod, pct, pct * 10))
        conn.commit()

    cli = _login(app, "sebastian")
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    r = cli.post("/api/admin/planta-demo/crear", json={}, headers=h)
    assert r.status_code in (200, 201), r.data[:300]

    with app.app_context():
        from blueprints.programacion import _get_mp_stock
        st = _get_mp_stock(get_db())
    for cod in ("ZZ-VIEJO-A", "ZZ-VIEJO-B"):
        assert (st.get(cod) or 0) > 0, (
            "%s es lo que la fórmula del demo pide y quedó sin stock · el demo se traba" % cod)


def test_el_aviso_de_stock_dice_QUE_falta(app, db_clean):
    """*"2 MP(s) sin stock"* no deja hacer nada: hay que saber CUÁLES para comprar o liberar.

    Se mira el fuente porque llegar al 422 exige una producción con déficit real, y un test que
    no puede llegar al caso se saltea en silencio (M152); lo que se protege es que el mensaje
    nombre los materiales, no el camino que lo produce.
    """
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "inventario.py"),
                  encoding="utf-8").read()
    i = src.index("'error': 'Stock insuficiente para producir'")
    ventana = re.sub(r"#[^\n]*", "", src[i:i + 2200])
    assert "MP(s) sin stock suficiente" not in ventana, (
        "el aviso sigue diciendo sólo cuántas faltan")
    assert "faltantes[:4]" in ventana, "no nombra los materiales que faltan"
    assert "requerido_g" in ventana and "disponible_g" in ventana, (
        "no dice cuánto se necesita y cuánto hay")


def test_borrar_el_demo_se_lleva_su_materia_prima(app, db_clean):
    """Si no, queda stock fantasma de un material que sólo existe para la demostración, y el
    inventario dice que hay 50 kg de algo que nadie compró."""
    from database import get_db
    cli = _login(app, "sebastian")
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    cli.post("/api/admin/planta-demo/crear", json={}, headers=h)
    r = cli.post("/api/brd/limpiar-demos", json={}, headers=h)
    assert r.status_code in (200, 201), r.data[:300]
    with app.app_context():
        quedan = get_db().execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id IN ('MP-DEMO1','MP-DEMO2')"
        ).fetchone()[0]
    assert quedan == 0, "quedaron %s movimientos de la MP del demo" % quedan
