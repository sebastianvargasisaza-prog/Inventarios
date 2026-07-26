"""El libro de facturas de proveedor es dinero: exige rol de Compras (26-jul).

`pagar_oc` pide rol desde el 21-may, pero sus hermanos del libro de facturas (crear, editar y
**pagar** una factura de proveedor) sólo exigían estar logueado: cualquier usuario del sistema
—planta, marketing, calidad, RRHH— podía registrar un pago. Y `fp_pagar` recalcula el estado de
la OC, así que mueve el mismo dinero. Es el patrón M45: al endurecer un guard de dinero, uno de
los pagadores hermanos se queda sin endurecer.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _cli(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, usuario
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return c, h


def test_un_usuario_sin_rol_de_compras_no_toca_el_libro(app):
    for usuario in ('valentina', 'mayerlin'):
        c, h = _cli(app, usuario)
        assert c.post("/api/compras/facturas-proveedor", headers=h,
                      json={'numero_factura': 'X1', 'proveedor': 'P', 'total': 1000}
                      ).status_code == 403, usuario
        assert c.patch("/api/compras/facturas-proveedor/1", headers=h,
                       json={'total': 5}).status_code == 403, usuario
        assert c.post("/api/compras/facturas-proveedor/1/pagar", headers=h,
                      json={'monto': 1000}).status_code == 403, usuario


def test_compras_y_la_contadora_SI_pueden(app):
    """Registrar pagos a proveedor es el trabajo de Catalina y Mayra: no se les puede cerrar."""
    for usuario in ('catalina', 'mayra', 'sebastian'):
        c, h = _cli(app, usuario)
        r = c.post("/api/compras/facturas-proveedor", headers=h,
                   json={'numero_factura': 'FP-TEST-' + usuario, 'proveedor': 'Proveedor test',
                         'total': 1000})
        assert r.status_code != 403, '%s quedó sin poder trabajar: %s' % (usuario, r.status_code)
