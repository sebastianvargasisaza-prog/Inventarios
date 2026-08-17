"""El legajo DEMO se camina de punta a punta, por UNA persona, sin pedir permisos (16-ago-2026).

Sebastián, trabado a mitad del recorrido: *"lo importante es que el demo no pida permisos, que
me deje probar cada botón, continuar, guardar y seguir los flujos hasta el final, así compruebo"*.

Un demo existe para comprobar el flujo. Si en el segundo paso pide la firma de Calidad o la
autorización de Producción, no se puede comprobar nada: hay que juntar a tres personas para
mirar una pantalla.

El salteo ya existía para algunos gates (la liberación, los controles en proceso, el visto bueno
del DT) y **faltaba en otros**, con el agravante de que el cálculo de "esto es un demo" estaba
copiado a mano en SIETE sitios, cada uno mirando un campo distinto -- así que cada gate nuevo
nacía sin la excepción y trababa el recorrido justo ahí (M3/M45). Ahora hay un solo helper.

⚠ Lo que el demo NO afloja, y por eso hay tests de los dos lados: los controles de ESTADO y de
DATO (`YA_CERRADO`, `LOTE_DUPLICADO`, `CANTIDAD_INVALIDA`). Esos no piden permiso a nadie -- son
parte de lo que se está comprobando -- y frenan igual. Y sobre todo: **un lote REAL sigue
pidiendo todo**, que es lo único que hace que este salteo sea aceptable.
"""
import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _sembrar(app, lote):
    """Un legajo con su MBR y un material, para caminarlo."""
    from database import get_db
    prod = "ZZ CAMINA %s" % lote
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ebr_ejecuciones WHERE lote=?", (lote,))
        cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                    "(SELECT id FROM mbr_templates WHERE producto_nombre=?)", (prod,))
        cur.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (prod,))
        cur.execute("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
        cur.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                    "VALUES ('ZZ-CAM-1','Camina',1)")
        cur.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                    "porcentaje, cantidad_g_por_lote) VALUES (?,?,?,100,1000)",
                    (prod, "ZZ-CAM-1", "Camina"))
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                    "lote_size_g, creado_por) VALUES (?,1,'draft',?,1000,'test')", (prod, prod))
        mid = cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                          (prod,)).fetchone()[0]
        cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso) "
                    "VALUES (?,1,'Fabricación','Mezclar','mezclado')", (mid,))
        cur.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mid,))
        cur.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,1,?,?,'iniciado','fabricacion','sebastian','2026-08-16T10:00:00',1000)",
            (mid, lote, lote))
        eid = int(cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0])
        conn.commit()
    return eid


# ══ el demo camina ══════════════════════════════════════════════════════════════

def _exigir_aprobacion(app, on=True):
    """El gate vive detrás de un toggle · sin encenderlo el test pasaría sin medir nada (M66)."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES "
                  "('exigir_aprobacion_orden', ?)", ("1" if on else "0",))
        c.commit()


def test_el_demo_no_pide_que_la_orden_este_aprobada(app, db_clean):
    """El que frenó a Sebastián: *"La orden todavía no está aprobada · Producción debe
    autorizarla antes de arrancar"*.

    Se ejerce por el ENDPOINT y no llamando al gate suelto: `_gate_aprobacion_orden` lee el
    `ebr_id` de la RUTA, así que invocarla a mano mediría otra cosa (M170).
    """
    eid = _sembrar(app, "DEMO-CAMINA-1")
    _exigir_aprobacion(app, True)
    try:
        r = _login(app).post("/api/brd/ebr/%d/ipc-estandar" % eid,
                             json={"control_codigo": "apariencia", "valor_texto": "ok"},
                             headers=_h())
        assert (r.get_json() or {}).get("codigo") != "ORDEN_SIN_APROBAR", (
            "el demo pide que otro autorice la orden · %s" % r.data[:200])
    finally:
        _exigir_aprobacion(app, False)


def test_un_lote_REAL_si_pide_la_aprobacion(app, db_clean):
    """El borde que hace aceptable el salteo · sin esto el 'arreglo' sería un agujero."""
    eid = _sembrar(app, "ZZ-REAL-1")
    _exigir_aprobacion(app, True)
    try:
        r = _login(app).post("/api/brd/ebr/%d/ipc-estandar" % eid,
                             json={"control_codigo": "apariencia", "valor_texto": "ok"},
                             headers=_h())
        assert (r.get_json() or {}).get("codigo") == "ORDEN_SIN_APROBAR", (
            "un lote real arrancó sin que Producción lo autorice · %s" % r.data[:200])
    finally:
        _exigir_aprobacion(app, False)


def _ebr_mode(app, modo):
    """El gate de la firma del pesaje sólo corre con el motor ENCENDIDO (`EBR_MODE != off`), y
    off es el default: sin esto el test pasa con el guard quitado, o sea mide el caso donde no
    hay nada que saltear (M152 · lo mostró la prueba de dientes, que dio NO MUERDE)."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('ebr_mode', ?)",
                  (modo,))
        c.commit()


def test_el_demo_no_pide_firma_para_pesar(app, db_clean):
    """`reportar_pesaje` devolvía FIRMA_REQUERIDA y el pesaje es el primer paso del legajo: sin
    esto el recorrido se traba antes de empezar."""
    eid = _sembrar(app, "DEMO-CAMINA-2")
    _ebr_mode(app, "warn")
    try:
        r = _login(app).post("/api/brd/ebr/%d/pesajes" % eid,
                             json={"material_id": "ZZ-CAM-1", "cantidad_real_g": 1000},
                             headers=_h())
        assert (r.get_json() or {}).get("codigo") != "FIRMA_REQUERIDA", (
            "el demo pide e-firma para pesar · %s" % r.data[:200])
    finally:
        _ebr_mode(app, "off")   # se restaura: si no, el motor queda encendido para los tests
                                # siguientes y los rompe desde otro archivo (M103)


def test_un_lote_REAL_si_pide_firma_para_pesar(app, db_clean):
    """Los dos lados, siempre: el pesaje de un lote de verdad es un dato regulado."""
    eid = _sembrar(app, "ZZ-REAL-2")
    _ebr_mode(app, "warn")
    try:
        r = _login(app).post("/api/brd/ebr/%d/pesajes" % eid,
                             json={"material_id": "ZZ-CAM-1", "cantidad_real_g": 1000},
                             headers=_h())
        assert (r.get_json() or {}).get("codigo") == "FIRMA_REQUERIDA", (
            "un pesaje real pasó sin e-firma · %s" % r.data[:200])
    finally:
        _ebr_mode(app, "off")


# ══ un solo lugar decide qué es un demo ═════════════════════════════════════════

def test_hay_UN_SOLO_calculo_de_que_es_un_demo(app, db_clean):
    """Estaba copiado siete veces, cada copia mirando un campo distinto, así que un gate nuevo
    nacía sin la excepción y el demo se trababa ahí (M3/M45)."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "brd.py"), encoding="utf-8").read()
    src = re.sub(r"#[^\n]*", "", src)          # sin comentarios: explican el patrón viejo (M154)
    src = re.sub(r'"""[\s\S]*?"""', "", src)   # ni docstrings
    crudas = re.findall(r"startswith\(\s*[\"']DEMO-[\"']\s*\)", src)
    assert len(crudas) <= 1, (
        "hay %d cálculos de 'es demo' a mano · deben pasar por es_lote_demo()" % len(crudas))


def test_el_helper_distingue_bien(app, db_clean):
    from blueprints.brd import es_lote_demo
    for v in ("DEMO-PLANTA-1", "demo-planta-1", " DEMO-X ", "DEMO-PLANTA-1-OF"):
        assert es_lote_demo(v) is True, v
    for v in ("", None, "260815-1", "DEMOSTRACION-1", "LOTE-DEMO-3"):
        assert es_lote_demo(v) is False, (
            "%r no es un lote de demostración · sólo cuenta el prefijo DEMO-" % (v,))


def test_el_demo_NO_afloja_los_controles_de_estado(app, db_clean):
    """Lo que un demo sí debe respetar: `YA_CERRADO`, `LOTE_DUPLICADO`, `CANTIDAD_INVALIDA` no
    piden permiso a nadie -- dicen 'ya lo hiciste' o 'el dato está mal' -- y son parte de lo que
    se viene a comprobar."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "brd.py"), encoding="utf-8").read()
    for cod in ("YA_CERRADO", "LOTE_DUPLICADO", "CANTIDAD_INVALIDA"):
        i = src.find('"codigo": "%s"' % cod)
        if i < 0:
            continue
        ventana = re.sub(r"#[^\n]*", "", src[max(0, i - 700):i])
        assert "es_lote_demo" not in ventana and "_es_demo" not in ventana, (
            "%s se saltea en el demo · eso no es un permiso, es parte de lo que se prueba" % cod)
