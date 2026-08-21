"""El plano: cuadrados con estado, click para registrar, y sin contradecirse · 21-ago-2026.

Sebastián: *"te hice un plano simple, solo de las áreas como cuadrados y ya, algo sencillo:
muestra estado, le dan click y registran cambios"*.

Lo que estaba roto no era el dibujo -- el plano de la planta ya se pinta en vivo -- sino que el
tablero se contradecía: la barra decía "0 ocupadas" mientras el mapa mostraba tres salas con
lote adentro, y esos lotes llevaban 1.237, 1.220 y 906 horas "corriendo". Un lote de 51 días no
está corriendo: está SIN CERRAR (M161/M5).
"""


def _plano_js(cli):
    """El JS del plano vive en el bundle, no en el HTML (M166/M216)."""
    from .conftest import pantalla_servida
    return pantalla_servida(cli, "/inventarios")


def test_un_lote_sin_cerrar_no_se_muestra_como_corriendo(admin_client):
    js = _plano_js(admin_client)
    assert "SIN_CERRAR=1440" in js.replace(" ", ""), "no hay umbral de lote sin cerrar"
    assert "sin cerrar" in js, "no lo nombra con esas palabras"
    assert "nSinCerrar" in js, "no lo cuenta aparte de las ocupadas"


def test_el_resumen_cuenta_lo_mismo_que_se_pinta(admin_client):
    """Un tablero cuyas dos mitades se contradicen no deja al usuario con una duda: lo deja
    sin creerle a ninguna de las dos."""
    js = _plano_js(admin_client)
    # Se ancla donde el resumen se CONSTRUYE (`rs.innerHTML`), no en el <div> vacío del HTML:
    # la primera aparición del id es el contenedor y ahí no hay nada que medir (M151).
    i = js.find("rs.innerHTML")
    assert i > 0, "no se encontró dónde se arma el resumen del plano"
    bloque = js[i:i + 1800]
    assert "sin cerrar" in bloque, "el resumen no declara los lotes sin cerrar"


def test_el_cuadrado_se_puede_apretar_y_registra(admin_client):
    """*"le dan click y registran cambios"*: la tarjeta abre la sala, y desde ahí se cambia el
    estado contra el endpoint que audita."""
    js = _plano_js(admin_client)
    i = js.find("cards+='<div onclick=")
    assert i > 0, "los cuadrados no son clicables"
    assert "planoAbrirSala" in js[i:i + 400], "el cuadrado no abre la sala"
    assert "window.planoEstado" in js, "no hay forma de registrar el cambio de estado"
    assert "/api/planta/areas/'+aid+'/estado" in js, "no usa el endpoint que audita"
    assert "X-CSRF-Token" in js, "el cambio de estado iría sin token"


def test_sucia_a_libre_lleva_al_despeje_y_no_promete_lo_que_el_gate_niega(admin_client):
    """El backend exige el despeje de línea firmado (BPM · PRD-PRO-001). El botón no puede
    prometer algo que el gate va a rechazar: lleva a la pantalla donde se hace (M109/M233)."""
    js = _plano_js(admin_client)
    i = js.find("window.planoEstado")
    bloque = js[i:i + 900]
    assert "despeje-linea" in bloque, "sucia→libre no lleva al despeje"
    assert "actual==='sucia'" in bloque.replace(' ', '') or 'actual===\'sucia\'' in bloque, \
        "no distingue el caso que el gate bloquea"
