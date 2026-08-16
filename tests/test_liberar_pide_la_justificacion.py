"""Liberar un lote: el aviso explica y deja resolverlo ahí mismo (16-ago-2026).

Sebastián, liberando un lote de prueba: *"estos pop up deberían ser premium todos · esto qué
significa dónde se hace · debería ser allí mismo que se ponga la justificación"*.

Lo que salía era un cuadro gris del navegador:

    Error: Rendimiento fuera de rango (10.0%) · GMP exige justificar un yield anómalo
    (<80% o >115%) antes de liberar.

El control está bien -- un lote al 10% es pérdida de producto, error de tara o unidades de
otra orden, y GMP pide explicarlo. Lo que estaba mal es que el mensaje FRENA y no ofrece la
salida: no dice dónde se justifica ni deja hacerlo. Un aviso que no lleva a ninguna parte
enseña a ignorarlo (M202), y encima ese cuadro no se parece en nada al resto de EOS.

Ahora es un modal propio: trae el rendimiento, explica qué puede haber pasado, y el campo
para escribirlo está en el mismo lugar. **El control no se afloja**: sigue siendo
obligatorio, sólo que ahora se puede cumplir donde aparece.

Se mira el FUENTE y no una pantalla servida porque la base de pruebas no siempre tiene un
legajo que abra, y un test que se saltea no protege nada (M152). Los comentarios se quitan
para que el guard no se encuentre a sí mismo explicando lo que ya no va (M154).
"""
import io
import os
import re


def _fuente_legajos():
    """El JS de las dos pantallas de legajo, sin comentarios."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "brd.py"),
                  encoding="utf-8").read()
    return re.sub(r"#[^\n]*", "", src)


def test_el_aviso_no_es_el_cuadro_del_navegador():
    """Un `confirm()` del navegador no es parte de EOS: se ve prestado y, sobre todo, no
    permite hacer nada con lo que informa."""
    cuerpo = _fuente_legajos()
    assert "confirm('¿LIBERAR" not in cuerpo, (
        "todavía se libera con el cuadro del navegador")


def test_el_modal_trae_el_campo_para_justificar():
    """El punto del pedido: que la justificación se escriba donde aparece el aviso."""
    cuerpo = _fuente_legajos()
    for pieza, que in (('id="libjust"', "el campo donde se escribe"),
                       ("YIELD_FUERA_RANGO", "reconoce el motivo del rechazo"),
                       ("yield_justificacion", "manda la justificación al servidor"),
                       ("_libAbrir", "abre el modal"),
                       ("_libConfirmar", "confirma desde el modal")):
        assert pieza in cuerpo, "falta %s (%s)" % (pieza, que)
    # las DOS pantallas (envasado y acondicionamiento) tienen que tenerlo: un patrón vive
    # en varios hermanos y el que se olvida es el que después falla (M45)
    assert cuerpo.count("_libConfirmar") >= 2, (
        "una de las dos pantallas se quedó sin el modal")


def test_no_deja_liberar_con_una_justificacion_de_relleno():
    """El control no se afloja: un 'ok' no es una explicación.

    Sin este borde, el arreglo sería una forma cómoda de saltarse el control (M96).
    """
    cuerpo = _fuente_legajos().replace(" ", "")
    assert "trim().length<10" in cuerpo, (
        "el modal acepta cualquier texto como justificación")


def test_el_servidor_sigue_exigiendo_la_justificacion():
    """Lo que de verdad protege el lote es el backend, no la pantalla: el control real nunca
    vive en la vista."""
    cuerpo = _fuente_legajos()
    assert "YIELD_FUERA_RANGO" in cuerpo, "desapareció el gate del rendimiento"
    assert "yield_justificacion" in cuerpo, (
        "el backend ya no lee la justificación que manda el modal")


def test_el_modal_explica_que_significa():
    """Sebastián: *"esto qué significa"*. El aviso tiene que decir qué pudo haber pasado,
    no sólo que el número está fuera de rango."""
    cuerpo = _fuente_legajos()
    for pista in ("tara", "otra orden"):
        assert pista in cuerpo, (
            "el modal no explica qué puede haber pasado (falta '%s')" % pista)
