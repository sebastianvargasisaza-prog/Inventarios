"""Recepción MP por OC · desglose por envase (Sebastián 18-jul).

Cuando una MP llega repartida en varios envases individuales (ej. 3500 g = 3 de
1000 + 1 de 500), la recepción persiste ese desglose en las notas del movimiento
para trazabilidad INVIMA (el rótulo por envase lleva el detalle físico). El N° de
recipientes se guarda como antes en n_recipientes.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_oc(numero_oc, codigo, nombre, cantidad_g):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO ordenes_compra
           (numero_oc, fecha, estado, proveedor, valor_total, observaciones, creado_por, categoria)
           VALUES (?, date('now'), 'Autorizada', 'Prov Test', 0, 'seed', 'test', 'MP')""",
        (numero_oc,),
    )
    c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)",
              (codigo, nombre))
    c.execute(
        """INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g)
           VALUES (?, ?, ?, ?, 0)""",
        (numero_oc, codigo, nombre, cantidad_g),
    )
    conn.commit(); conn.close()


def _obs_nrec(codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        row = conn.execute(
            "SELECT observaciones, n_recipientes FROM movimientos "
            "WHERE material_id=? AND tipo='Entrada' ORDER BY id DESC LIMIT 1", (codigo,)).fetchone()
        return (row[0] if row else None, row[1] if row else None)
    finally:
        conn.close()


def test_desglose_envases_persiste_en_notas(app, db_clean):
    _seed_oc('OC-ENV-001', 'MP-ENV1', 'Glicerina Test', 3500)
    cs = _login(app)
    body = {'receptor_nombre': 'Catalina', 'items_recepcion': [
        {'codigo_mp': 'MP-ENV1', 'cantidad_recibida': 3500, 'estado': 'OK',
         'lote': 'L-ENV-1', 'recipientes': 4, 'envases_detalle': [1000, 1000, 1000, 500]}
    ]}
    r = cs.post('/api/ordenes-compra/OC-ENV-001/recibir', json=body, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    obs, nrec = _obs_nrec('MP-ENV1')
    assert obs is not None, "debe haber una Entrada"
    assert 'envases: 1000+1000+1000+500 g' in obs, f"desglose en notas · {obs}"
    assert nrec == 4, f"n_recipientes = 4 · {nrec}"


def test_un_solo_envase_sin_desglose(app, db_clean):
    _seed_oc('OC-ENV-002', 'MP-ENV2', 'Glicerina Test 2', 1000)
    cs = _login(app)
    body = {'receptor_nombre': 'Catalina', 'items_recepcion': [
        {'codigo_mp': 'MP-ENV2', 'cantidad_recibida': 1000, 'estado': 'OK',
         'lote': 'L-ENV-2', 'recipientes': 1}
    ]}
    r = cs.post('/api/ordenes-compra/OC-ENV-002/recibir', json=body, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    obs, nrec = _obs_nrec('MP-ENV2')
    assert obs is not None
    assert 'envases:' not in obs, f"un solo envase no agrega desglose · {obs}"
    assert nrec == 1
