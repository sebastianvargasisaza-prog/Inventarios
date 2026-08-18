# -*- coding: utf-8 -*-
"""El material de empaque del acondicionamiento se puede REGISTRAR, no sólo mirar.

Caminando el lote completo apareció la asimetría entre las dos pantallas hermanas:

    Legajo de ENVASADO          6 columnas de conciliación + editor (agregar / editar / borrar)
    Legajo de ACONDICIONAMIENTO las MISMAS 6 columnas · ninguna acción

Y el endpoint `POST /api/brd/ebr/<id>/material-envase` **no es de una fase**: escribe en
`ebr_materiales_envase` por `ebr_id`, y el legajo de acondicionamiento YA leía esas filas
(`_materiales_envase_manuales`). O sea que la capacidad estaba entera y desde esa pantalla no
había cómo llegar (M121), que es la forma más cara de un hueco: desde adentro se ve terminado.

Este test recorre lo que hace la persona: abrir el legajo de acondicionamiento, registrar la
conciliación de una etiqueta, y verlo en la tabla.
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


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


def test_la_conciliacion_del_empaque_se_puede_llenar_desde_el_legajo(app, db_clean):
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    oa = d["acondicionamiento_ebr"]

    r = cli.post("/api/brd/ebr/%d/material-envase" % oa, headers=_h(), json={
        "material_codigo": "ETIQ-DEMO", "lote_material": "ETQ-L1",
        "requerida": 30, "devuelta": 2, "utilizada": 27, "averiada": 1})
    assert r.status_code in (200, 201), (
        "no se pudo registrar la conciliación del empaque desde el acondicionamiento · %s"
        % r.get_data(as_text=True)[:400])

    mats = (cli.get("/api/brd/ebr/%d/vista-completa" % oa).get_json()
            or {}).get("acond_materiales") or []
    fila = [m for m in mats if (m.get("material_codigo") or "") == "ETIQ-DEMO"
            and m.get("utilizada") is not None]
    assert fila, ("lo registrado no aparece en la tabla del legajo de acondicionamiento", mats)
    f = fila[0]
    assert float(f.get("devuelta") or 0) == 2 and float(f.get("utilizada") or 0) == 27, f
    assert float(f.get("averiada") or 0) == 1, (
        "sin `averiada` lo que se rompió en la línea se mezcla con lo devuelto a bodega, y uno "
        "de los dos NO vuelve al stock (M205)", f)


def test_el_legajo_de_acondicionamiento_OFRECE_el_editor(app, db_clean):
    """Una capacidad a la que nadie puede llegar no existe (M121) · y todo botón tiene que
    llamar a una función que EXISTE en la página servida, no en otra (M166/M197)."""
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    html = cli.get("/planta/legajo-acondicionamiento/%d" % d["acondicionamiento_ebr"]
                   ).get_data(as_text=True)

    assert "+ Material de empaque" in html, "la pantalla no ofrece agregar material de empaque"
    assert "matModal(-1)" in html, "el botón de agregar no llama al editor"

    llamadas = sorted(set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\(', html)))
    faltan = [f for f in llamadas
              if not re.search(r'(?:async )?function\s+' + f + r'\b', html)]
    assert not faltan, "botones que llaman a algo que no existe en esta página: %s" % faltan


def test_el_editor_vive_UNA_sola_vez_en_cada_pantalla(app, db_clean):
    """Se INYECTA en las dos, no se copia.

    Dos definiciones idénticas son desperdicio y dos distintas son un bug (M217): el día que
    alguien toque una copia, la otra se queda vieja y las dos pantallas conciliarían distinto.
    """
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    paginas = {
        "envasado": cli.get("/planta/legajo-envasado/%d" % d["envasado_ebr"]).get_data(as_text=True),
        "acondicionamiento": cli.get("/planta/legajo-acondicionamiento/%d"
                                     % d["acondicionamiento_ebr"]).get_data(as_text=True),
    }
    for quien, html in paginas.items():
        for fn in ("matModal", "guardarMat", "borrarMat", "cargarEnvaseOpc"):
            n = len(re.findall(r'(?:async )?function\s+' + fn + r'\s*\(', html))
            assert n == 1, ("en %s la función %s está definida %d veces" % (quien, fn, n))
        assert "/*__EDITOR_MATERIAL__*/" not in html, (
            "la marca del editor quedó SIN reemplazar en %s · la pantalla queda con botones "
            "llamando a funciones inexistentes (M116)" % quien)


def test_la_diferencia_cuenta_lo_devuelto_y_lo_averiado(app, db_clean):
    """UNA sola derivación de "lo que no se puede explicar".

    Medido en producción caminando el lote: con 30 requeridas, 27 utilizadas, 2 devueltas a
    bodega y 1 averiada -- o sea TODO explicado -- el legajo mostraba **3 sin explicar**, porque
    ahí la diferencia se calculaba como `requerida - utilizada` mientras el resolvedor canónico
    (`_conc_diferencia`, el de `/conciliacion-material`) resta también lo devuelto y lo averiado.

    Dos derivaciones del mismo número divergen siempre (M99), y el legajo es el registro que lee
    una auditoría: mandaba a buscar tres etiquetas que están contadas (M205).
    """
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    oa = d["acondicionamiento_ebr"]

    r = cli.post("/api/brd/ebr/%d/material-envase" % oa, headers=_h(), json={
        "material_codigo": "CAJA-DEMO", "lote_material": "CJ-L9",
        "requerida": 30, "devuelta": 2, "utilizada": 27, "averiada": 1})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]

    mats = (cli.get("/api/brd/ebr/%d/vista-completa" % oa).get_json()
            or {}).get("acond_materiales") or []
    fila = [m for m in mats if m.get("lote_material") == "CJ-L9"]
    assert fila, ("no encontré la fila que acabo de registrar", mats)
    assert float(fila[0].get("diferencia")) == 0.0, (
        "la diferencia ignora lo devuelto y lo averiado: dice %s donde todo está explicado "
        "(27 usadas + 2 devueltas + 1 averiada = 30)" % fila[0].get("diferencia"))

    # y el resolvedor único tiene que VER ese registro y dar el mismo número · `/conciliacion-
    # material` lee su propia tabla (la del modal del dashboard), así que la unión vive en
    # `conciliacion_material_lote`, que es la que usan el gate de liberación, Calidad y el PDF.
    try:
        from blueprints.brd import conciliacion_material_lote
    except Exception:
        from api.blueprints.brd import conciliacion_material_lote
    with app.app_context():
        from database import get_db
        todas = conciliacion_material_lote(get_db(), oa)
    mio = [x for x in todas if x.get("lote_material") == "CJ-L9"]
    assert mio, ("el resolvedor único no ve lo registrado desde el legajo", todas)
    assert float(mio[0].get("diferencia")) == 0.0, mio[0]


def test_llenar_la_conciliacion_en_el_LEGAJO_deja_liberar_el_lote(app, db_clean):
    """El gate de liberación miraba UNA de las dos tablas.

    La conciliación se puede registrar por dos pantallas que escriben distinto:

        modal del dashboard  ->  ebr_conciliacion_material
        legajo (OF / OA)     ->  ebr_materiales_envase

    y el gate contaba sólo la primera. Entonces quien la llenaba en el legajo veía su pantalla
    completa y al liberar recibía *"falta la conciliación de material"* -- la pantalla y el
    botón diciendo lo contrario sobre el mismo hecho (M161), y encima trabando la liberación de
    un lote cuyo dato SÍ está.

    Este test mide el GATE, no la tabla: registra por el legajo y exige que el motivo del
    rechazo ya no sea la conciliación faltante.
    """
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    oa = d["acondicionamiento_ebr"]

    r = cli.post("/api/brd/ebr/%d/material-envase" % oa, headers=_h(), json={
        "material_codigo": "CAJA-DEMO", "lote_material": "CJ-GATE",
        "requerida": 30, "devuelta": 0, "utilizada": 30, "averiada": 0})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]

    # Dos cosas hay que FIJAR para que este test mida lo que dice medir, y las dos las
    # aprendí midiendo, no leyendo:
    #
    #  (a) el legajo tiene que estar `completado` · si no, liberar choca ANTES con el gate de
    #      ESTADO y el 409 lo contesta otro guard: el test pasaría verde sin haber ejercitado
    #      nunca el que se está probando (M96/M152/M160);
    #  (b) el gate de conciliación vive DENTRO de `if _ebr_mode_now(cur)=='strict'`, y el modo
    #      real hoy es `warn` · sin fijar el modo, liberar devuelve 200 y el assert pasa por la
    #      razón equivocada. Un test que valida un modo estricto lo FIJA, nunca confía en el
    #      default (M66/M206).
    #
    # El lote DEMO sólo se salta la e-firma; los gates regulatorios -- éste incluido -- siguen
    # aplicando, así que medir con el demo es legítimo (M119).
    import os
    import sqlite3
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cn.execute("UPDATE ebr_ejecuciones SET estado='completado' WHERE id=?", (oa,))
        cn.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('ebr_mode','strict')")
        cn.commit()
    finally:
        cn.close()

    try:
        rl = cli.post("/api/brd/ebr/%d/liberar" % oa, json={}, headers=_h())
        cuerpo = rl.get_json() or {}
        assert cuerpo.get("codigo") != "CONCILIACION_FALTANTE", (
            "el gate sigue diciendo que falta la conciliación con la conciliación registrada "
            "desde el legajo", rl.status_code, cuerpo)
    finally:
        cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            cn.execute("DELETE FROM app_settings WHERE clave='ebr_mode'")
            cn.commit()
        finally:
            cn.close()
