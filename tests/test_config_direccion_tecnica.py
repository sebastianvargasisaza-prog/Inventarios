"""Las herramientas del Director Técnico viven en SU módulo (16-ago-2026).

Sebastián: *"todo lo que sea del director técnico lo podemos montar en el módulo dirección
técnica"*.

En MyBatch, el perfil de Director Técnico tiene una sección **Configuración** con las áreas
productivas, los equipos, los despejes de línea y los controles de atributos, más el Audit
Trail. En EOS esas pantallas existían pero **repartidas en otros módulos** (Aseguramiento,
Planta, admin), así que Hernando tenía que saberse las URLs o pasar por el módulo de otro.

Es la misma regla que ya está escrita para Recepción: **el punto de entrada lo define de quién
es la herramienta**, no qué blueprint la sirve (M120). Las URLs no se mueven -- están enlazadas
desde otros lados y en marcadores --: lo que se agrega es la puerta desde su módulo.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _tecnica(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    resp = c.get("/tecnica")
    assert resp.status_code == 200, resp.status_code
    return resp.data.decode("utf-8", "replace")


def test_el_DT_tiene_sus_herramientas_en_su_modulo(app, db_clean):
    html = _tecnica(app)
    assert "Direcci&oacute;n T&eacute;cnica" in html or "Dirección Técnica" in html
    for ruta, que in (("/aseguramiento/checklists", "configurar las verificaciones"),
                      ("/aseguramiento/reemplazo-mybatch", "el estado del reemplazo"),
                      ("/aseguramiento/audit-trail", "el audit trail"),
                      ("/planta/plano", "las áreas productivas"),
                      ("/aseguramiento/calibracion", "los equipos y su calibración")):
        assert ruta in html, "falta %s (%s)" % (ruta, que)


def test_ningun_enlace_lleva_a_una_ruta_QUE_NO_EXISTE(app, db_clean):
    """Puse `/calidad/equipos` de memoria y esa ruta no existe: la real es
    `/aseguramiento/calibracion`. Un enlace roto no da error -- lleva a un 404 y la persona
    aprende que el módulo no sirve (M202). Se valida contra el `url_map` REAL, no contra lo que
    yo recuerde."""
    html = _tecnica(app)
    i = html.find("CONFIGURACI")
    if i < 0:
        i = html.find("Configuraci&oacute;n &middot; Direcci")
    assert i > 0, "no se encontró la sección de configuración del DT"
    bloque = html[i:i + 6000]
    enlaces = [h for h in re.findall(r'href="(/[^"#?]+)', bloque)]
    assert enlaces, "la sección no tiene enlaces · no estaría midiendo nada"
    rutas = {str(r.rule) for r in app.url_map.iter_rules()}
    rotos = [h for h in enlaces if h not in rutas]
    assert not rotos, "enlaces que no llevan a ninguna parte: %s" % rotos


def test_cada_herramienta_dice_QUE_hace_ahi(app, db_clean):
    """Un nombre solo no alcanza: *"Verificaciones"* no le dice al DT que revisarlas y
    guardarlas es lo que deja constancia de que las aprobó."""
    html = _tecnica(app)
    for pista in ("despeje", "instructivo", "INVIMA", "calibraci"):
        assert pista in html, "la sección no explica para qué sirve cada herramienta (%s)" % pista


def test_la_seccion_usa_el_sistema_de_diseno_del_modulo(app, db_clean):
    """Premium por defecto (regla 0): la sección usa las clases y los tokens que el módulo ya
    tiene, no estilos sueltos que se vean pegados ni colores fijos que ignoren el tema."""
    html = _tecnica(app)
    i = html.find("Configuraci&oacute;n &middot; Direcci")
    assert i > 0
    bloque = html[max(0, i - 400):i + 6000]
    assert 'class="card"' in bloque, "no usa la tarjeta del módulo"
    assert "var(--cx-" in bloque, "usa colores fijos en vez de los tokens del tema"
    assert not re.search(r"(?:background|color)\s*:\s*#[0-9a-fA-F]{3,6}\b", bloque), (
        "hay un color fijo · en tema oscuro quedaría ilegible (M114)")
