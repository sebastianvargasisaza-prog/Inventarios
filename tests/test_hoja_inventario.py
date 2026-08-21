# -*- coding: utf-8 -*-
"""La hoja de trabajo del inventario: todo lo del lote en un solo lugar · 21-ago-2026.

Sebastián: *"quiero la opción de mover todo, modificar INCI, lote, eliminar o declarar que se usó
y ya no está... si en esa estantería aparece digamos propilenglicol y hay en otra ubicación, de
una me lo sugiera... que además me permita cambiar fecha de vencimiento, todo lo que corresponda
en un solo lugar... si la materia prima no está en EOS, me permita ingresarla sin pasar por
cuarentena, pero súper importante que me permita buscar allí mismo sin salirme"*.

Casi todo existía y estaba repartido: cambiar ubicación, lote, vencimiento y proveedor ya tenían
su endpoint, y el cuadre ajusta el stock. Lo que faltaba era juntarlo en una hoja y agregar las
dos piezas que no existían:

  · **la sugerencia**, que viaja CON los lotes y no detrás de un clic -- parado frente al estante
    es cuando se puede resolver, después nadie vuelve. Se calcula en UNA consulta agregada para
    todos los materiales de la estantería: pedirla por fila satura los tres workers (M43);
  · **buscar en todo el inventario sin salir**, porque "no aparece nada" significaba dos cosas
    distintas -- no existe, o está en otro estante -- y desde la silla se leen igual (M100).
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_COD = 'MP-HOJA-TEST'
_NOM = 'PROPILENGLICOL DE PRUEBA'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _limpiar():
    """Limpieza ANTES de sembrar, con códigos FIJOS (M103)."""
    _sql("DELETE FROM movimientos WHERE material_id=?", (_COD,))
    _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (_COD,))


def _sembrar():
    """El mismo material en DOS estanterías y un lote sin ubicar: el caso que motivó todo."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?,?,1)",
         (_COD, 'PROPYLENE GLYCOL'))
    for est, lote, cant in (('HOJA-A1', 'LH-1', 1000.0),
                            ('HOJA-2C', 'LH-2', 500.0),
                            ('', 'LH-3', 250.0)):
        _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
             "lote, estanteria, estado_lote) VALUES (?,?,?,'Entrada','2026-01-10',?,?,'VIGENTE')",
             (_COD, _NOM, cant, lote, est))


# ── la sugerencia, sin que haya que pedirla ──────────────────────────────────

def test_avisa_que_el_material_TAMBIEN_esta_en_otra_estanteria(app, db_clean):
    _sembrar()
    try:
        d = _login(app).get('/api/inventario/cuadre-lotes?est=HOJA-A1').get_json()
        filas = [x for x in d['lotes'] if x['codigo_mp'] == _COD and x['lote'] == 'LH-1']
        assert filas, "no trajo el lote de esta estantería"
        otras = filas[0].get('otras_ubic') or []
        assert otras, "no avisa que el mismo material está en otra estantería"
        assert any(u['estanteria'] == 'HOJA-2C' and u['g'] == 500.0 for u in otras), \
            "no dice DÓNDE ni CUÁNTO: %r" % (otras,)
        # y no se avisa a sí misma: la estantería que estás revisando no es "otra parte"
        assert not any(u['estanteria'] == 'HOJA-A1' for u in otras), \
            "se cuenta a sí misma como otra ubicación"
        assert d.get('con_otras_ubic', 0) >= 1, "no declara cuántas filas tienen aviso"
    finally:
        _limpiar()


def test_la_sugerencia_NO_cuesta_una_consulta_por_fila(app, db_clean):
    """Pedirla por fila desde el navegador es lo que satura los tres workers (M43): el bloque
    que la calcula tiene que estar FUERA del loop que arma las filas."""
    import io as _io
    src = _io.open('api/blueprints/inventario.py', encoding='utf-8').read()
    i = src.find('def inventario_cuadre_lotes')
    assert i != -1
    fin = src.find('\n@bp.route', i)
    cuerpo = src[i:fin if fin > 0 else i + 9000]
    j = cuerpo.find('otras ubicaciones del material')
    assert j != -1, "no está el bloque que calcula la sugerencia"
    bloque = cuerpo[max(0, j - 1500):j]
    assert 'IN (%s)' in bloque or 'IN (' in bloque, \
        "la sugerencia no se pide para todos los materiales de una vez"


# ── buscar sin salirse ───────────────────────────────────────────────────────

def test_busca_en_TODO_el_inventario_sin_salir_de_la_hoja(app, db_clean):
    """Estando en una estantería, buscar un material que está en otra tiene que encontrarlo:
    "no aparece nada" se lee como "no existe", que es lo contrario (M100)."""
    _sembrar()
    try:
        c = _login(app)
        d = c.get('/api/inventario/cuadre-lotes?q=PROPILENGLICOL+DE+PRUEBA').get_json()
        ests = set(x['estanteria'] for x in d['lotes'] if x['codigo_mp'] == _COD)
        assert 'HOJA-A1' in ests and 'HOJA-2C' in ests, \
            "la búsqueda no cruza las estanterías: %r" % (ests,)
        assert d.get('busqueda'), "no declara sobre qué se buscó"
        # también por LOTE, que es como se busca parado frente a un envase
        d2 = c.get('/api/inventario/cuadre-lotes?q=LH-2').get_json()
        assert any(x['lote'] == 'LH-2' for x in d2['lotes']), "no encuentra por número de lote"
    finally:
        _limpiar()


def test_el_buscador_de_la_pantalla_consulta_todo_el_inventario(app, db_clean):
    """Un endpoint sin puerta no existe (M121). Se mide sobre la pantalla SERVIDA (M216)."""
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app), '/planta/cuadre')
    assert 'function buscarGlobal' in js, "el buscador no consulta el inventario completo"
    assert 'cuadre-lotes?q=' in js, "no usa el modo de búsqueda global"
    assert 'id="busca-global"' in js, "no hay dónde mostrar lo que encontró"
    assert 'function irA' in js, "encontrado el material, no hay forma de ir a su estantería"
    # con retardo: una consulta por tecla satura los tres workers (M43)
    i = js.find('function filtrar')
    assert 'setTimeout' in js[i:i + 1500], "busca en cada tecla, sin esperar"


# ── todo lo del lote, en un solo lugar ───────────────────────────────────────

def test_la_hoja_permite_editar_lote_vencimiento_INCI_y_ubicacion(app, db_clean):
    from .conftest import pantalla_servida
    js = pantalla_servida(_login(app), '/planta/cuadre')
    for f in ('function editar', 'function guardarCampo', 'function borrarLote'):
        assert f in js, "falta %s" % f
    # cada campo va contra el endpoint que YA existe para ese dato: un endpoint nuevo que los
    # junte duplicaría la mutación y las dos copias divergen (M3)
    for url in ('/codigo-lote', '/fecha-vencimiento', '/ubicacion', '/inci'):
        assert url in js, "el panel no sabe guardar %s" % url
    # y guarda al SALIR del campo, no en cada tecla
    assert 'onchange="guardarCampo' in js, "no autoguarda al salir del campo"


def test_el_INCI_se_corrige_y_queda_auditado(app, db_clean):
    _sembrar()
    try:
        c = _login(app)
        r = c.put('/api/inventario/mp/%s/inci' % _COD,
                  json={'nombre_inci': 'PROPANEDIOL'}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:200]
        d = r.get_json()
        assert d['nombre_inci'] == 'PROPANEDIOL'
        assert d['antes'] == 'PROPYLENE GLYCOL', \
            "no devuelve el valor anterior, que es lo que permite deshacer (M175)"
        conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE accion='EDITAR_INCI_MP' AND registro_id=?",
                (_COD,)).fetchone()[0]
        finally:
            conn.close()
        assert n >= 1, "cambiar la identidad química de una MP no dejó rastro"
    finally:
        _limpiar()


def test_el_INCI_no_se_puede_dejar_VACIO(app, db_clean):
    """Sin INCI el resolver cae a otros criterios y puede elegir la molécula de al lado (M137).
    Vaciarlo no es una corrección: es perder la identidad del material."""
    _sembrar()
    try:
        r = _login(app).put('/api/inventario/mp/%s/inci' % _COD,
                            json={'nombre_inci': '   '}, headers=csrf_headers())
        assert r.status_code == 400, "dejó vaciar el INCI"
        assert 'INCI' in (r.get_json() or {}).get('error', ''), "no explica por qué"
    finally:
        _limpiar()


def test_dice_TODAS_las_ubicaciones_de_un_material(app, db_clean):
    _sembrar()
    try:
        d = _login(app).get('/api/inventario/material-ubicaciones/%s' % _COD).get_json()
        assert d['n_ubicaciones'] == 3, "no ve las tres ubicaciones: %r" % (d,)
        assert d['total_g'] == 1750.0, "no suma bien: %r" % (d['total_g'],)
        assert d['sin_ubicar_g'] == 250.0, \
            "no separa lo que no tiene ubicación, que es la cola de trabajo"
    finally:
        _limpiar()
