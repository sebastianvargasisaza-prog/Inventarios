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
