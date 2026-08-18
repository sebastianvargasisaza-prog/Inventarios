# -*- coding: utf-8 -*-
"""Programar producción: cualquier producto, cualquier muestra, y los clientes de verdad.

Alejandro reportó que no podía programar. Al medirlo, el endpoint funcionaba perfecto para él
(200, producto existente y producto nuevo) y ninguna pantalla le bloqueaba: **el problema estaba
en el formulario**, y es de los que no dan error de servidor.

  · **"Cantidad (kg)" decía `opcional`** y el backend rechaza sin kilos con 400 SIN_KG. El campo
    prometía lo contrario de lo que el guard exige, así que quien lo dejaba vacío -- porque la
    pantalla se lo permitía -- no podía programar (M109).
  · **El desplegable de producto se llenaba SÓLO con lo ya agendado** en la ventana visible del
    calendario, así que un producto que existe pero no está programado no aparecía y había que
    escribirlo de memoria y exacto (M121: la capacidad está y no hay cómo llegar).
  · **El cliente era texto libre a secas**, sin los clientes que existen.

Lo que estos guards fijan es la regla general, no el caso: **un campo no puede anunciarse opcional
si el backend lo exige**, y las dos mitades se miden juntas.
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _login(app, user="alejandro"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _modal(cli):
    """El HTML del modal tal como se SIRVE (el calendario va en su propio iframe)."""
    r = cli.get("/admin/plan-calendario")
    assert r.status_code == 200, r.status_code
    return r.get_data(as_text=True)


def test_el_campo_kg_no_puede_decir_opcional_si_el_backend_lo_exige(app, db_clean):
    """Las dos mitades del mismo control, medidas juntas."""
    cli = _login(app)

    # (a) el backend lo EXIGE
    r = cli.post("/api/plan/programar-manual", headers=_h(), json={
        "producto": "ZZ PROG SIN KG", "fecha": "2026-09-14", "lotes": 1})
    assert r.status_code == 400 and (r.get_json() or {}).get("codigo") == "SIN_KG", (
        "el backend dejó de exigir los kilos · si esto cambia, el formulario también", r.get_json())

    # (b) entonces el formulario NO puede decir que es opcional
    html = _modal(cli)
    m = re.search(r'<input[^>]*id="np-kg"[^>]*>', html)
    assert m, "no encontré el campo de kilos en el modal"
    campo = m.group(0)
    assert "opcional" not in campo.lower(), (
        "el campo de kilos se anuncia OPCIONAL y el backend lo rechaza sin kilos: quien lo deja "
        "vacío no puede programar y la pantalla se lo permitió", campo)
    assert "required" in campo, ("el campo de kilos no está marcado como obligatorio", campo)


def test_el_modal_ofrece_los_productos_que_EXISTEN_y_los_clientes(app, db_clean):
    cli = _login(app)
    d = cli.get("/api/plan/opciones-programar").get_json() or {}
    assert d.get("ok"), d
    nombres = [p.get("nombre") for p in (d.get("productos") or [])]
    assert len(nombres) >= 5, ("el modal no tiene de dónde sacar los productos reales", d)
    con_kg = [p for p in (d.get("productos") or []) if (p.get("kg_lote") or 0) > 0]
    assert con_kg, ("ningún producto trae su lote estándar · el botón de kg no tendría qué "
                    "ofrecer", nombres[:5])
    assert "clientes" in d, "el modal no puede ofrecer clientes reales"

    html = _modal(cli)
    assert 'id="np-clientes-list"' in html, "el campo de cliente no ofrece los clientes que existen"
    assert 'list="np-clientes-list"' in html, "el campo de cliente no está enlazado a su lista"


def test_se_puede_programar_un_piloto_que_no_existe_en_ninguna_tabla(app, db_clean):
    """El modal se construyó para esto: pilotos, muestras y productos de otros clientes.

    El producto sigue siendo TEXTO LIBRE -- las sugerencias no pueden volverse una obligación.
    """
    cli = _login(app)
    r = cli.post("/api/plan/programar-manual", headers=_h(), json={
        "producto": "ZZ MUESTRA PILOTO QUE NO EXISTE", "fecha": "2026-09-14",
        "kg": 3, "lotes": 1, "cliente": "CLIENTE NUEVO", "observaciones": "muestra"})
    assert r.status_code == 200, (
        "no se puede programar un piloto que no existe en ninguna tabla", r.get_data(as_text=True)[:300])

    html = _modal(cli)
    m = re.search(r'<input[^>]*id="np-producto"[^>]*>', html)
    assert m and 'list="np-productos-list"' in m.group(0), (
        "el producto dejó de ser texto libre con sugerencias", m.group(0) if m else None)
    assert "<select" not in (m.group(0) if m else ""), (
        "el producto se volvió un desplegable cerrado: un piloto no se podría escribir")


def test_el_boton_de_programar_no_manda_a_fallar(app, db_clean):
    """Avisar MIENTRAS se escribe, no al guardar (M197).

    Se mide sobre el JS SERVIDO, sin comentarios, para que el guard no se satisfaga con la nota
    que lo explica (M154).
    """
    html = _modal(_login(app))
    js = re.sub(r"//.*", "", html)
    for fn in ("_npValidarKg", "_npSugerirKg", "_npCargarOpciones"):
        assert re.search(r"function\s+" + fn + r"\s*\(", js), (
            "falta %s en la pantalla servida" % fn)
    assert "_npValidarKg()" in js, "nadie llama a la validación de kilos"
    # y el guardado tiene que cortar ANTES de mandar
    i = js.find("async function guardarNuevaProduccion")
    assert i > 0, "no encontré el guardado del modal"
    cuerpo = js[i:i + 3000]
    assert "kg > 0" in cuerpo, (
        "el guardado no verifica los kilos antes de mandar: deja que el backend rechace y "
        "recién ahí explica")
