# -*- coding: utf-8 -*-
"""Una orden registrada por la vía SIMPLE también cuenta sus unidades.

Sebastián, mirando la pestaña de acondicionamiento: *"no me parece que deba ser así"* ·
*"le falta ser más EOS fusionado con MyBatch"*.

La vista de órdenes ya mezclaba las dos mitades -- el LEGAJO (la orden de MyBatch) y el registro
SIMPLE (la pantalla que usa la planta) --, pero el bucle que enriquece los items arrancaba con
`if not eid: continue`, así que sólo los legajos recibían `unidades_total`.

Consecuencia, con el trabajo hecho y registrado:
  · el KPI "Unidades acondicionadas" contaba **0**
  · y la tarjeta decía **"Sin unidades registradas todavía"**

El SQL ya sumaba `SUM(unidades_producidas)` y el diccionario la tiraba: un dato que se captura,
se calcula y se pierde en el camino lo termina inventando la pantalla (M115).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ-ORD-SIMPLE"
LOTE = "ZZORDSIMPLE1"


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _sql(q, p=()):
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = cn.execute(q, p)
        cn.commit()
        return cur.fetchall()
    finally:
        cn.close()


def _orden_del_lote(cli, fase):
    d = cli.get("/api/brd/ordenes-unificadas?fase=%s" % fase).get_json() or {}
    fila = next((o for o in (d.get("ordenes") or []) if (o.get("lote_bulk") or "") == LOTE), None)
    return d, fila


def test_el_acondicionamiento_registrado_a_mano_muestra_sus_unidades(app, db_clean):
    _sql("DELETE FROM acondicionamiento WHERE lote=?", (LOTE,))
    cli = _login(app)

    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": LOTE, "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 120, "batch_g": 3600, "observaciones": "registro por la pantalla"})
    assert r.status_code in (200, 201), r.data[:300]

    d, fila = _orden_del_lote(cli, "acondicionamiento")
    assert fila, "el registro simple ni siquiera aparece en la lista de órdenes"
    assert fila.get("unidades_total") == 120, (
        "la orden aparece pero sin sus unidades: la tarjeta diría 'sin unidades registradas' "
        "con el trabajo hecho", fila)
    assert (d.get("resumen") or {}).get("unidades_total", 0) >= 120, (
        "el KPI de unidades acondicionadas no cuenta lo registrado a mano", d.get("resumen"))


def test_lo_mismo_para_envasado(app, db_clean):
    """El bucle era compartido, así que envasado tenía el mismo hueco (M45)."""
    _sql("DELETE FROM envasado WHERE lote=?", (LOTE,))
    cli = _login(app)

    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": LOTE, "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 75, "batch_g": 2250})
    assert r.status_code in (200, 201), r.data[:300]

    _d, fila = _orden_del_lote(cli, "envasado")
    assert fila, "el envasado registrado no aparece en la lista"
    assert fila.get("unidades_total") == 75, (
        "el envasado simple aparece sin sus unidades", fila)


def test_una_orden_SIN_unidades_sigue_avisando(app, db_clean):
    """El borde del otro lado: si de verdad no hay nada registrado, la tarjeta tiene que seguir
    diciéndolo. Convertir el aviso en un cero silencioso sería cambiar un bug por otro."""
    _sql("DELETE FROM acondicionamiento WHERE lote=?", (LOTE + "V",))
    cli = _login(app)
    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": LOTE + "V", "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 0, "batch_g": 0})
    assert r.status_code in (200, 201, 400), r.data[:300]
    d = cli.get("/api/brd/ordenes-unificadas?fase=acondicionamiento").get_json() or {}
    fila = next((o for o in (d.get("ordenes") or []) if (o.get("lote_bulk") or "") == LOTE + "V"),
                None)
    if fila:
        assert not fila.get("unidades_total"), (
            "una orden sin unidades no puede reportar un total", fila)


def test_la_excepcion_va_PLEGADA_y_la_cola_manda(app, db_clean):
    """La pestaña tiene que empujar al camino normal, no al excepcional.

    "Registrar a mano" son nueve campos vacíos y su propio subtítulo dice que es para reprocesos
    y entregas puntuales; abierto de fábrica era el bloque más grande de la pantalla, más que la
    cola -- cuyo botón YA pre-llena producto, lote, unidades y presentación. Eso invita a teclear
    a mano lo que el sistema ya sabe.

    Se pliega, **no se esconde**: sigue a un clic, con sus campos y su botón, y dice cuándo usarlo
    (una función que desaparece sin explicación se lee como un faltante · M124).
    """
    from .conftest import pantalla_servida
    cli = _login(app)
    html = pantalla_servida(cli, "/inventarios")

    i = html.find('id="ac-form-manual"')
    assert i > 0, "desapareció el formulario de registro a mano"
    apertura = html[max(0, i - 200):i + 40]
    assert "<details" in apertura, (
        "el formulario de excepción volvió a estar desplegado de fábrica: ocupa más pantalla "
        "que la cola, que es el camino normal")
    assert "open" not in apertura.split("<details")[1].split(">")[0], (
        "el <details> nace ABIERTO, que es lo mismo que no plegarlo")

    # sigue completo y alcanzable
    for x in ("ac-prod-sel", "ac-lote", "ac-form-msg"):
        assert x in html, "se perdió %s al plegar el formulario" % x
    # y la cola -- el camino normal -- sigue ahí con su botón
    assert "Lotes listos para acondicionar" in html
    assert "prefillAcond(" in html, "la cola perdió el botón que pre-llena el registro"


def test_la_tarjeta_de_acondicionamiento_no_habla_de_GRANEL(app, db_clean):
    """El renderizador es UNO para las tres fases -a propósito, para que el estilo no diverja-
    pero el CONTENIDO tiene que hablar de su fase.

    En una orden de acondicionamiento decía "1.000 g de granel": ahí el producto ya está
    envasado y no se maneja granel, se manejan unidades, etiquetas y plegadizas. Es pedirle la
    densidad a una caja (M205/M214).

    ⚠ Se mide sobre el JS que el navegador CARGA, no sobre el HTML: las funciones del dashboard
    viven en los bundles (M166).
    """
    from .conftest import pantalla_servida
    cli = _login(app)
    import re as _re
    js = pantalla_servida(cli, "/inventarios")
    # ⚠ SIN comentarios: el bloque lleva arriba una nota que explica por qué el granel no va en
    #   acondicionamiento, y la primera versión de este guard se encontró a sí misma (M154).
    js = _re.sub("//.*", "", js)   # sin DOTALL, el punto no cruza el salto de línea
    i = js.find("g de granel")
    assert i > 0, "desapareció la línea del granel (fabricación y envasado la necesitan)"
    ventana = js[max(0, i - 260):i]
    assert "fase!==" in ventana.replace(" ", "") or "fase !==" in ventana, (
        "la línea de 'g de granel' no está condicionada a la fase: vuelve a aparecer en una "
        "orden de acondicionamiento, donde ya no hay granel que medir")


def test_abrir_o_crear_el_legajo_de_un_lote_es_UNA_llamada(app, db_clean):
    """`legajo-rapido` contestaba 409 cuando el legajo YA existía -- el caso más común -- así que
    "abrir o crear" obligaba a cada botón a inventar su propio rescate.

    Es el mismo defecto que el enganche envasado→acondicionamiento ya había cobrado: "ya existe"
    no es un error, es la respuesta (M129). Ahora devuelve el que hay, marcado como reusado, y
    con el enlace de SU fase.
    """
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    assert d.get("ok"), d

    r = cli.post("/api/brd/legajo-rapido", headers=_h(),
                 json={"producto": d["producto"], "lote": d["lote"], "fase": "acondicionamiento"})
    assert r.status_code == 200, ("el legajo ya existe: eso no es un 409 · %s" % r.data[:250])
    j = r.get_json()
    assert j.get("ok") and j.get("id") == d["acondicionamiento_ebr"], (
        "devolvió otro legajo, no el del lote", j, d["acondicionamiento_ebr"])
    assert j.get("reusado") is True, ("tiene que DECIR que lo reusó, no fingir que lo creó", j)
    assert j.get("link") == "/planta/legajo-acondicionamiento/%d" % d["acondicionamiento_ebr"], (
        "el enlace no lleva a la pantalla de su fase", j)

    # y el de envasado, por su propio camino
    r2 = cli.post("/api/brd/legajo-rapido", headers=_h(),
                  json={"producto": d["producto"], "lote": d["lote"], "fase": "envasado"})
    assert r2.status_code == 200, r2.data[:250]
    assert r2.get_json().get("link") == "/planta/legajo-envasado/%d" % d["envasado_ebr"], r2.data[:250]


def test_el_boton_de_la_cola_abre_el_LEGAJO(app, db_clean):
    """La cola tiene que llevar al batch record, no a un registro paralelo.

    Se mide sobre el JS que el navegador CARGA (M166), y con los comentarios quitados: el bloque
    lleva arriba la explicación de por qué, y un guard que se encuentra a sí mismo no mide nada
    (M154).
    """
    import re as _re
    from .conftest import pantalla_servida
    cli = _login(app)
    js = _re.sub("//.*", "", pantalla_servida(cli, "/inventarios"))
    i = js.find("function prefillAcond")
    assert i > 0, "desapareció el handler del botón de la cola"
    # ⚠ acotado al CUERPO, no a N caracteres: con una ventana fija el guard se come la función
    #   siguiente y pasa verde con el bug puesto -- probado (M151/M176).
    _sig = min([x for x in (js.find("\nfunction ", i + 1), js.find("\nasync function ", i + 1))
                if x > 0] or [i + 2000])
    cuerpo = js[i:_sig]
    assert "legajo-rapido" in cuerpo, (
        "el botón de la cola volvió a abrir un registro suelto en vez del legajo del lote")
    assert "abrirAcond" in cuerpo, (
        "se perdió la caída al registro a mano: un lote sin MBR aprobado no puede quedar sin "
        "forma de registrarse")
