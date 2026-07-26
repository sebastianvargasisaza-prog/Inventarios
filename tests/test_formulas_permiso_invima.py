"""La RECETA de una fórmula maestra sólo la ve quien tiene permiso INVIMA (Sebastián 25-jul).

Antes: `GET /api/formulas` sólo exigía estar logueado, así que CUALQUIER usuario (una operaria de
planta, marketing, la contadora) recibía las 40 recetas completas con código de MP y porcentaje.
El candado de la pantalla ("Fórmulas desbloqueadas / Bloquear") es un PIN de NAVEGADOR: la receta
ya había viajado al browser antes de pedirlo. Ocultaba sin proteger.

Regla: la receta es de Dirección Técnica ∪ Control de Calidad ∪ Aseguramiento ∪ Dirección.
El resto sigue viendo los NOMBRES (los necesita el select de Fabricación y el pedido B2B) —
cerrar un permiso sin mirar a los consumidores deja el módulo roto (M32).
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo loguear %s' % usuario
    return c


def _formulas(c):
    r = c.get("/api/formulas")
    assert r.status_code == 200, r.status_code
    return r.get_json() or {}


def test_un_usuario_cualquiera_NO_ve_los_ingredientes(app):
    """El caso que disparó el fix: valentina no es técnica, ni calidad, ni admin."""
    d = _formulas(_login(app, 'valentina'))
    assert d.get('solo_nombres') is True, 'debe venir marcado como recorte, no silencioso'
    assert d['formulas'], 'los NOMBRES sí se ven (sin ellos no se puede ni fabricar)'
    for f in d['formulas']:
        assert f['items'] == [], (
            'FUGA: %s expone ingredientes a un usuario sin permiso INVIMA' % f['producto_nombre'])
    # El payload de DATOS no puede traer ni un porcentaje ni un código de MP. (El texto
    # explicativo `motivo` sí menciona la palabra "porcentajes" · se excluye a propósito.)
    crudo = str(d['formulas'])
    assert 'porcentaje' not in crudo, 'ni un porcentaje puede viajar en el payload'
    assert 'MP00' not in crudo, 'ni un código de MP puede viajar en el payload'


def test_tecnica_calidad_aseguramiento_y_direccion_SI_las_ven(app):
    """Los que hoy trabajan con fórmulas no pueden perder acceso al cerrar el permiso."""
    for usuario in ('hernando', 'miguel', 'laura', 'alejandro', 'sebastian'):
        d = _formulas(_login(app, usuario))
        assert not d.get('solo_nombres'), '%s DEBE ver la receta completa' % usuario
        con_items = [f for f in d['formulas'] if f['items']]
        assert con_items, '%s no recibió ninguna fórmula con ingredientes' % usuario
        assert 'porcentaje' in con_items[0]['items'][0]


def test_el_nombre_del_producto_sigue_disponible_para_fabricar(app):
    """El select de Fabricación y el formulario B2B se llenan de acá: no pueden quedar vacíos."""
    d = _formulas(_login(app, 'valentina'))
    nombres = [f['producto_nombre'] for f in d['formulas']]
    assert len(nombres) == len(set(nombres)) and nombres, nombres
    assert all(n and n.strip() for n in nombres)


def test_escribir_una_formula_sigue_exigiendo_rol(app):
    """No perder el gate de ESCRITURA que ya existía (auditoría 25-jul)."""
    c = _login(app, 'valentina')
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    r = c.post("/api/formulas", headers=h, json={
        'producto_nombre': 'HACKEADA', 'unidad_base_g': 1000,
        'items': [{'material_id': 'MP00001', 'material_nombre': 'x', 'porcentaje': 100}]})
    assert r.status_code == 403, r.status_code


def test_el_resolver_es_uno_solo_y_falla_cerrado(app):
    """Si la config no carga, NO se muestra la receta (dato regulado · fail-closed)."""
    from blueprints.inventario import _puede_ver_formulas
    assert _puede_ver_formulas('sebastian') is True
    assert _puede_ver_formulas('hernando') is True
    assert _puede_ver_formulas('valentina') is False
    assert _puede_ver_formulas('') is False
    assert _puede_ver_formulas('usuario-que-no-existe') is False
