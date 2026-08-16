"""La ubicación del F01 llega COMPLETA al kardex (28-jul).

Sebastián: *"la lógica del inventario es que hay estanterías y posiciones, y nevera; debería
pedir esos datos, y cuando se guarda debe traducirse a trazabilidad y aparecer en todo lado --
me dicen que no se refleja en inventario"*.

Tres problemas, medidos contra el código:
  1. El F01 escribía sólo `movimientos.estanteria`; **`posicion` quedaba vacía para siempre**,
     aunque la vista de inventario, el rótulo y el conteo cíclico la leen. Eso era la mitad de
     la ubicación perdiéndose en cada recepción.
  2. Era UN texto libre: 'A3', 'Estante 3' y 'estanteria A-3' son tres estantes distintos para
     el sistema, y el conteo cíclico agrupa POR estantería -- cada variante inventaba un estante.
  3. **La nevera no existía en ningún lado**, aunque hay materia prima que va refrigerada.

Decisión de Sebastián: una sola nevera por ahora, sin posiciones adentro.
"""
from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f'no pudo entrar {user}'
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


COD, LOTE = 'ZZUB001', 'LOTE-ZZ-UBIC'


def _sembrar(app):
    """Una Entrada en cuarentena, como la deja la recepción. Limpia antes (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM recepcion_tecnica_doc WHERE codigo_insumo=?", (COD,))
        cu.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
        cu.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))
        # Las columnas son `nombre_inci` / `nombre_comercial`, no `nombre` (verificado contra
        # el CREATE TABLE · el auto-check del cerebro: confirmar el nombre real antes de
        # escribir el SQL, no deducirlo).
        cu.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                   "VALUES (?,?,?,1)", (COD, 'ZZ Insumo Ubicacion', 'ZZ Insumo Ubicacion'))
        cu.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, fecha, "
            "lote, estado_lote, estanteria, posicion) VALUES (?,?,?,?,?,?,?,?,?)",
            (COD, 'ZZ Insumo Ubicacion', 'Entrada', 2000, '2026-07-28', LOTE,
             'CUARENTENA', '', ''))
        mov = cu.execute("SELECT MAX(id) FROM movimientos WHERE material_id=?", (COD,)).fetchone()[0]
        conn.commit()
    return mov


def _ubic(app):
    from database import get_db
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT COALESCE(estanteria,''), COALESCE(posicion,'') FROM movimientos "
            "WHERE material_id=? AND tipo='Entrada'", (COD,)).fetchone()
    return (r[0], r[1]) if r else (None, None)


def _f01(cli, mov, **extra):
    cuerpo = {
        'mov_id': mov, 'origen': 'MP', 'codigo_insumo': COD,
        'nombre_insumo': 'ZZ Insumo Ubicacion', 'lote': LOTE,
        'lote_proveedor': 'LP-1', 'cantidad_recibida': '2000', 'proveedor': 'ZZ Prov',
        'fecha_recepcion': '2026-07-28', 'resultado': 'conforme',
        'crit_rotulado': 'cumple', 'crit_empaque': 'cumple', 'crit_hoja_seguridad': 'cumple',
        'crit_ficha_tecnica': 'cumple', 'crit_coa': 'cumple', 'crit_doc_coincide': 'cumple',
        'realiza_por': 'laura',
    }
    cuerpo.update(extra)
    return cli.post('/api/calidad/recepcion-tecnica', json=cuerpo, headers=_h())


# ═══════════════════════════════════════════════════════════════════════════════

def test_estanteria_y_posicion_llegan_LAS_DOS_al_kardex(app, db_clean):
    """El bug original: `posicion` nunca se escribía, así que en inventario se veía media
    ubicación y el conteo no podía ubicar el lote dentro del estante."""
    mov = _sembrar(app)
    cli = _login(app)
    r = _f01(cli, mov, ubic_tipo='estanteria', ubic_estanteria='A3', ubic_posicion='2')
    assert r.status_code in (200, 201), r.data[:300]

    est, pos = _ubic(app)
    assert est == 'A3', 'la estantería no llegó al kardex: %r' % est
    assert pos == '2', 'la POSICIÓN no llegó al kardex (era el bug): %r' % pos


def test_la_nevera_queda_registrada_y_sin_posicion(app, db_clean):
    """Una sola nevera, sin posiciones adentro (decisión de Sebastián). Lo importante es que
    quede DICHO que va refrigerado: antes no había forma de expresarlo."""
    mov = _sembrar(app)
    cli = _login(app)
    r = _f01(cli, mov, ubic_tipo='nevera', ubic_estanteria='', ubic_posicion='')
    assert r.status_code in (200, 201), r.data[:300]

    est, pos = _ubic(app)
    assert est == 'NEVERA', 'la nevera no llegó al kardex: %r' % est
    assert pos == '', 'la nevera no lleva posición: %r' % pos


def test_la_nevera_ignora_lo_que_haya_quedado_en_estanteria(app, db_clean):
    """Si alguien escribió un estante y después cambia a Nevera, no puede quedar la mezcla."""
    mov = _sembrar(app)
    cli = _login(app)
    _f01(cli, mov, ubic_tipo='nevera', ubic_estanteria='A9', ubic_posicion='7')
    est, pos = _ubic(app)
    assert (est, pos) == ('NEVERA', ''), 'quedó mezclado: %r / %r' % (est, pos)


def test_el_texto_del_F01_se_DERIVA_de_los_campos_estructurados(app, db_clean):
    """El F01 es un documento firmado: lo que se imprime no puede decir algo distinto de lo
    que se guardó en el kardex (M5). Por eso el texto lo compone el backend."""
    mov = _sembrar(app)
    cli = _login(app)
    _f01(cli, mov, ubic_tipo='estanteria', ubic_estanteria='B7', ubic_posicion='3',
         area_almacenamiento='cualquier cosa que mande el front')
    r = cli.get('/api/calidad/recepcion-tecnica?mov_id=%d&origen=MP' % mov)
    d = r.get_json() or {}
    doc = d.get('registro') or d.get('f01') or d
    txt = str(doc.get('area_almacenamiento') or '')
    assert 'B7' in txt and '3' in txt, 'el texto del F01 no refleja la ubicación real: %r' % txt


def test_un_F01_viejo_de_texto_libre_no_se_pierde(app, db_clean):
    """Los registros ya firmados no se reescriben: si no viene ubicación estructurada, se
    respeta el texto que se había escrito y se manda a estantería."""
    mov = _sembrar(app)
    cli = _login(app)
    r = _f01(cli, mov, area_almacenamiento='Bodega fría pasillo 2')
    assert r.status_code in (200, 201), r.data[:300]
    est, _ = _ubic(app)
    assert est == 'Bodega fría pasillo 2', 'se perdió la ubicación del F01 viejo: %r' % est


def test_la_ubicacion_se_ve_en_la_vista_de_inventario(app, db_clean):
    """"Que aparezca en todo lado": el punto del cambio es que se REFLEJE, no que se guarde.

    El lote se libera antes de mirar: `/api/lotes` excluye CUARENTENA a propósito (un lote
    retenido no es stock disponible), así que un lote recién recibido no sale ahí. Lo que se
    verifica es que la ubicación que escribió el F01 viaja hasta la vista, no el flujo de
    liberación -- eso lo cubren los tests de Calidad.
    """
    from database import get_db
    mov = _sembrar(app)
    cli = _login(app)
    _f01(cli, mov, ubic_tipo='estanteria', ubic_estanteria='C1', ubic_posicion='4')
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("UPDATE movimientos SET estado_lote='VIGENTE' WHERE material_id=?", (COD,))
        conn.commit()
    lotes = cli.get('/api/lotes').get_json()
    filas = lotes if isinstance(lotes, list) else (lotes.get('lotes') or lotes.get('items') or [])
    mio = [x for x in filas if x.get('codigo_mp') == COD or x.get('material_id') == COD]
    assert mio, 'el lote no aparece en la vista de inventario'
    assert mio[0].get('estanteria') == 'C1', mio[0]
    assert mio[0].get('posicion') == '4', mio[0]


def test_la_pantalla_pide_la_ubicacion_estructurada(app, db_clean):
    cli = _login(app)
    html = pantalla_servida(cli, '/calidad')
    for marca in ('f01_ubic_tipo', 'f01_ubic_estanteria', 'f01_ubic_posicion',
                  'Nevera (refrigerado)', '_rcCargarEstanterias'):
        assert marca in html, 'falta %s en el formulario' % marca
    assert 'f01_area_almacenamiento' not in html, (
        'quedó el campo de texto libre viejo · dos formas de decir lo mismo divergen')
