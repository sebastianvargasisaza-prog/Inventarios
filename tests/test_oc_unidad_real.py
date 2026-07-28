"""La OC muestra la unidad REAL, no gramos para todo (28-jul).

Catalina: *"le está colocando gramos a cosas que son cantidades"*. En la bandeja se veía un
`Servicio de Calibración por laboratorio acreditado` como **"1 g"**, y la serigrafía de 810
envases como **"810 g"**.

La unidad SÍ se capturaba: `solicitudes_compra_items.unidad` existe desde siempre. Pero
`ordenes_compra_items` no tenía la columna, así que el dato se perdía al crear la OC -- y la
pantalla, sin nada que mostrar, le pegaba una `g` a todo.

Un número con la unidad equivocada es peor que un número sin unidad: se lee como si fuera
cierto (M5, el número que se muestra tiene que ser el que decide). Por eso cuando no se sabe
la unidad no se inventa ninguna.
"""
from datetime import date

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f'no pudo entrar {user}'
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


OC = 'OC-ZZ-UNID'


def _sembrar(app, *, categoria='Servicios', unidad='servicio'):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (OC,))
        cu.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        hoy = date.today().isoformat()
        cu.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, fecha, "
                   "valor_total, categoria) VALUES (?,?,?,?,?,?)",
                   (OC, 'ZZ SIAMED', 'Borrador', hoy, 1142400, categoria))
        cu.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                   "cantidad_g, precio_unitario, subtotal, unidad) VALUES (?,?,?,?,?,?,?)",
                   (OC, 'ZZSVC1', 'Servicio de Calibracion', 1, 1142400, 1142400, unidad))
        conn.commit()


def _item(cli):
    # El endpoint que alimenta la pantalla del consolidado por proveedor (el de la
    # captura de Catalina) es `consolidado-proveedor`, no el de solicitudes agrupadas.
    js = cli.get('/api/compras/consolidado-proveedor').get_json()
    provs = js if isinstance(js, list) else (js.get('proveedores') or [])
    for p in provs:
        for it in (p.get('items') or []):
            if it.get('codigo_mp') == 'ZZSVC1':
                return it
    return None


# ═══════════════════════════════════════════════════════════════════════════════

def test_el_endpoint_devuelve_la_unidad_del_item(app, db_clean):
    """Sin esto la pantalla no tiene con qué, y termina inventando la unidad."""
    _sembrar(app)
    cli = _login(app)
    it = _item(cli)
    assert it, 'el item no salió en la bandeja agrupada'
    assert it.get('unidad') == 'servicio', (
        'el endpoint no devuelve la unidad real: %r' % it.get('unidad'))


def test_la_unidad_viaja_de_la_SOLICITUD_a_la_OC(app, db_clean):
    """Era el punto exacto donde se perdía: la SOL la tenía, el INSERT de la OC no la copiaba."""
    from database import get_db
    NUM = 'SOL-ZZ-UNID'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (NUM,))
        cu.execute("DELETE FROM solicitudes_compra WHERE numero=?", (NUM,))
        cu.execute("DELETE FROM ordenes_compra_items WHERE codigo_mp=?", ('ZZENV9',))
        hoy = date.today().isoformat()
        cu.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                   "categoria, empresa) VALUES (?,?,?,?,?,?)",
                   (NUM, hoy, 'Pendiente', 'jefferson', 'Empaque', 'Espagiria'))
        cu.execute("INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, "
                   "cantidad_g, unidad) VALUES (?,?,?,?,?)",
                   (NUM, 'ZZENV9', 'Serigrafia envase', 810, 'und'))
        conn.commit()

    cli = _login(app, 'sebastian')
    r = cli.post('/api/compras/oc-desde-solicitudes',
                 json={'solicitudes': [NUM], 'proveedor': 'ZZ LEONARDO'}, headers=_h())
    assert r.status_code in (200, 201), r.data[:300]

    with app.app_context():
        fila = get_db().cursor().execute(
            "SELECT COALESCE(unidad,'') FROM ordenes_compra_items WHERE codigo_mp=?",
            ('ZZENV9',)).fetchone()
    assert fila and fila[0] == 'und', (
        'la unidad se perdió al crear la OC (era el bug): %r' % (fila[0] if fila else None))


def test_la_pantalla_ya_no_pega_gramos_a_todo(app, db_clean):
    """El guard de la causa: si alguien vuelve a concatenar ' g' a la cantidad de la bandeja,
    los servicios y los envases vuelven a mostrarse en gramos."""
    cli = _login(app)
    html = cli.get('/compras').data.decode('utf-8', 'replace')
    assert "_cantUnidad(" in html, 'no está el formateador que respeta la unidad'
    assert "cantidad_total_g||0).toLocaleString('es-CO')+' g'" not in html, (
        "volvió el ' g' pegado a la cantidad de la bandeja")


def test_sin_unidad_no_se_inventa_ninguna(app, db_clean):
    """Mostrar el número solo es honesto; mostrar '1 g' de un servicio, no."""
    cli = _login(app)
    html = cli.get('/compras').data.decode('utf-8', 'replace')
    i = html.index('function _cantUnidad')
    cuerpo = html[i:i + 420]
    assert "if(!u) return n;" in cuerpo, (
        'sin unidad debería devolver el número solo · %s' % cuerpo[:200])
