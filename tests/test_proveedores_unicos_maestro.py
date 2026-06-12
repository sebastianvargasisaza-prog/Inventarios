"""/api/proveedores-unicos incluye el maestro de proveedores (Sebastián 12-jun).
Antes solo salían los proveedores YA asignados a alguna MP/movimiento -> no se
podía corregir una MP a un proveedor registrado pero aún no usado (ej. Quincream
es de GYM, no Agenquimicos). Ahora el desplegable lista TODOS los activos.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_proveedores_unicos_incluye_maestro_no_asignado(app, db_clean):
    # GYM existe en el maestro de proveedores pero NO está en ninguna MP/movimiento
    _exec("INSERT OR IGNORE INTO proveedores (nombre, activo) VALUES ('GYM Quimicos', 1)")
    # Un proveedor que SÍ está asignado a una MP (debe seguir saliendo)
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, proveedor, activo) "
          "VALUES ('MP-PUTST','X','Agenquimicos',1)")

    c = _login(app)
    r = c.get('/api/proveedores-unicos')
    assert r.status_code == 200, r.data
    provs = r.get_json()['proveedores']
    assert 'GYM Quimicos' in provs, "el proveedor del maestro (no asignado) debe salir en el desplegable"
    assert any(p.lower() == 'agenquimicos' for p in provs), "los ya asignados a MP siguen saliendo"


def test_proveedores_unicos_excluye_inactivos(app, db_clean):
    _exec("INSERT OR IGNORE INTO proveedores (nombre, activo) VALUES ('Proveedor Muerto ZZ', 0)")
    c = _login(app)
    r = c.get('/api/proveedores-unicos')
    provs = r.get_json()['proveedores']
    assert 'Proveedor Muerto ZZ' not in provs, "proveedores inactivos no deben listarse"
