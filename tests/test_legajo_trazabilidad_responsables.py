"""La sección INVIMA "quién hizo qué" del batch record no puede salir vacía si hubo acciones.

Sebastián, revisando el legajo del lote OP-2026-0026 (25-jul): la sección 11 "Trazabilidad de
responsables" decía "Sin acciones registradas todavía" aunque arriba se veían 13/13 verificaciones
firmadas. En producción ese lote tenía 47 acciones en el audit trail.

Causa: el legajo embebido en Planta se arma con `/api/brd/ebr/<id>` + sub-recursos en paralelo, y
el `audit` sólo existía dentro de `/vista-completa`, que ese camino nunca llama → `d.audit`
siempre undefined → el render pintaba el texto de "vacío". Los datos estaban; la pantalla no los
pedía. Indistinguible de "no pasó nada" (M94).
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_existe_el_endpoint_de_trazabilidad_del_lote(app):
    c = _admin(app)
    r = c.get("/api/brd/ebr/1/audit")
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert 'items' in d and isinstance(d['items'], list)
    assert 'error' not in d, d.get('error')


def test_devuelve_las_acciones_con_responsable_y_fecha(app):
    """Si el lote tuvo acciones auditadas, tienen que salir · con quién y cuándo (Part 11)."""
    from audit_helpers import audit_log
    from database import get_db
    with app.app_context():
        conn = get_db()
        audit_log(conn.cursor(), usuario='sebastian', accion='COMPLETAR_EBR',
                  tabla='ebr_ejecuciones', registro_id='777', detalle='cierre de prueba')
        conn.commit()
    d = _admin(app).get("/api/brd/ebr/777/audit").get_json()
    acciones = [x['accion'] for x in d['items']]
    assert 'COMPLETAR_EBR' in acciones, d
    fila = [x for x in d['items'] if x['accion'] == 'COMPLETAR_EBR'][0]
    assert fila['usuario'] == 'sebastian'
    assert fila['fecha'], 'una firma sin fecha no sirve como registro GMP'


def test_las_dos_vistas_del_legajo_usan_EL_MISMO_productor(app):
    """Dos copias de la query es exactamente cómo una de las dos se queda vieja (M1)."""
    import inspect

    from blueprints import brd
    assert hasattr(brd, '_ebr_audit_rows')
    assert '_ebr_audit_rows(' in inspect.getsource(brd.ebr_vista_completa)
    assert '_ebr_audit_rows(' in inspect.getsource(brd.ebr_audit)


def test_el_legajo_de_planta_pide_la_trazabilidad(app):
    """El bug no estaba en el backend: estaba en que la pantalla nunca la pedía."""
    from templates_py import dashboard_html as D
    src = None
    for k in dir(D):
        v = getattr(D, k)
        if isinstance(v, str) and 'async function abrirEBR' in v:
            src = v
            break
    assert src, 'no encontré el template del dashboard'
    bloque = src[src.index('async function abrirEBR'):]
    bloque = bloque[:bloque.index('_ebrRender(')]
    assert re.search(r"/audit'", bloque), (
        'abrirEBR debe traer el audit del lote, o la sección 11 vuelve a salir vacía')
    assert 'd.audit=' in bloque, 'y tiene que asignarlo a d.audit, que es lo que lee el render'
