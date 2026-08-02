"""Re-apuntar un ingrediente de UNA fórmula · la decisión de Alejandro sobre la centella (2-ago).

El batch record pide extracto de centella en 13 productos y EOS descuenta triterpenos 80%; la
Esencia lleva los DOS (0,15% + 0,10%) y EOS los fundió en uno al 0,25%. Alejandro confirmó que en
los 13 va el extracto.

No se puede arreglar con el `reapuntar-formula` que ya existe: ése cambia el código en TODAS las
fórmulas, y Hydrapeptide y la Esencia sí llevan triterpenos (M19: el scope es el ítem, nunca el
material_id a secas).

Lo que estos tests fijan:
  · mover un ingrediente de un código a otro, sólo en ESE producto
  · partirlo en dos (el caso de la Esencia), y que los dos pedazos sumen lo que había
  · que NUNCA se pueda romper el "suma 100": los porcentajes tienen que cuadrar
  · que un PUENTE activo sobre el destino BLOQUEE (si no, el cambio queda muerto: la fórmula
    diría un código y el descuento sacaría otro · fue lo que pasó con el puente 184)
  · que no toque las otras fórmulas
  · preview que no escribe, y auditoría con el valor previo
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

URL = '/api/programacion/editar-formula-items'
PROD_A = 'QA EDITFI PRODUCTO A'
PROD_B = 'QA EDITFI PRODUCTO B'
VIEJO, NUEVO, OTRO = 'MPQAEDIT1', 'MPQAEDIT2', 'MPQAEDIT3'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _sembrar():
    """M103: limpiar ANTES · la BD de tests es compartida y en PG sobrevive entre corridas."""
    db = _db()
    try:
        for p in (PROD_A, PROD_B):
            db.execute("DELETE FROM formula_items WHERE producto_nombre=?", (p,))
            db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (p,))
        db.execute("DELETE FROM mp_formula_bridge WHERE formula_material_id IN (?,?,?)",
                   (VIEJO, NUEVO, OTRO))
        db.execute("DELETE FROM maestro_mps WHERE codigo_mp IN (?,?,?)", (VIEJO, NUEVO, OTRO))
        for cod, nom in ((VIEJO, 'QA Viejo'), (NUEVO, 'QA Nuevo'), (OTRO, 'QA Otro')):
            db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                       "VALUES (?,?,?,1)", (cod, nom, nom.upper()))
        for p in (PROD_A, PROD_B):
            db.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, activo) "
                       "VALUES (?,1000,1)", (p,))
            db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                       "porcentaje) VALUES (?,?,?,?)", (p, VIEJO, 'QA Viejo', 0.25))
            db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                       "porcentaje) VALUES (?,?,?,?)", (p, OTRO, 'QA Otro', 99.75))
        db.commit()
    finally:
        db.close()


def _items(prod):
    db = _db()
    try:
        return {r[0]: round(float(r[1] or 0), 4) for r in db.execute(
            "SELECT material_id, porcentaje FROM formula_items WHERE producto_nombre=?",
            (prod,)).fetchall()}
    finally:
        db.close()


def test_mueve_el_ingrediente_solo_en_ese_producto(app):
    _sembrar()
    c = _admin(app)
    body = {'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.25, 'pct_de': 0}]}
    js = c.post(URL, json=body, headers=_csrf(c)).get_json()
    assert js['ok'] is True and js['resumen']['aplicados'] == 1, js
    assert _items(PROD_A) == {NUEVO: 0.25, OTRO: 99.75}
    assert _items(PROD_B) == {VIEJO: 0.25, OTRO: 99.75}, 'no puede tocar la otra fórmula'
    assert js['formulas_fuera_de_100'] == []


def test_parte_el_ingrediente_en_dos(app):
    """El caso de la Esencia: 0,25% se parte en 0,15% del nuevo + 0,10% del viejo."""
    _sembrar()
    c = _admin(app)
    js = c.post(URL, headers=_csrf(c), json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.15, 'pct_de': 0.10}]}).get_json()
    assert js['ok'] is True, js
    assert _items(PROD_A) == {VIEJO: 0.10, NUEVO: 0.15, OTRO: 99.75}
    assert js['formulas_fuera_de_100'] == []


def test_los_porcentajes_tienen_que_cuadrar(app):
    """Sin esta regla un error de tipeo deja la fórmula sin sumar 100, que es el control de
    integridad de todo este frente."""
    _sembrar()
    c = _admin(app)
    js = c.post(URL, headers=_csrf(c), json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.20, 'pct_de': 0.10}]}).get_json()
    assert js['resumen']['aplicados'] == 0
    assert len(js['bloqueados']) == 1 and 'sumar 100' in js['bloqueados'][0]['motivo']
    assert _items(PROD_A) == {VIEJO: 0.25, OTRO: 99.75}, 'no pudo escribir nada'


def test_un_PUENTE_activo_sobre_el_destino_bloquea(app):
    """El puente 184 (`MP00181 -> MP00176`) es la razón por la que esto existe: la fórmula diría
    un código y el descuento seguiría sacando el otro, sin un solo error a la vista."""
    _sembrar()
    db = _db()
    try:
        db.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
                   "VALUES (?,?,1)", (NUEVO, OTRO))
        db.commit()
    finally:
        db.close()
    c = _admin(app)
    js = c.post(URL, headers=_csrf(c), json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.25, 'pct_de': 0}]}).get_json()
    assert js['resumen']['aplicados'] == 0
    assert 'PUENTE' in js['bloqueados'][0]['motivo'] and 'muerto' in js['bloqueados'][0]['motivo']
    assert _items(PROD_A) == {VIEJO: 0.25, OTRO: 99.75}


def test_no_fusiona_si_la_formula_ya_tiene_el_destino(app):
    _sembrar()
    c = _admin(app)
    js = c.post(URL, headers=_csrf(c), json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': OTRO, 'pct_a': 0.25, 'pct_de': 0}]}).get_json()
    assert js['resumen']['aplicados'] == 0
    assert 'fusionar' in js['bloqueados'][0]['motivo']


def test_la_vista_previa_no_escribe(app):
    _sembrar()
    c = _admin(app)
    js = c.post(URL, headers=_csrf(c), json={'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.25, 'pct_de': 0}]}).get_json()
    assert js['dry_run'] is True and len(js['plan']) == 1
    assert _items(PROD_A) == {VIEJO: 0.25, OTRO: 99.75}


def test_queda_auditado_con_el_valor_previo(app):
    _sembrar()
    c = _admin(app)
    c.post(URL, headers=_csrf(c), json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.25, 'pct_de': 0}]})
    db = _db()
    try:
        n = db.execute("SELECT COUNT(*) FROM audit_log WHERE accion='EDITAR_FORMULA_ITEM' "
                       "AND antes LIKE ?", ('%' + VIEJO + '%',)).fetchone()[0]
        assert n >= 1, 'sin el valor previo no se puede revertir'
    finally:
        db.close()


def test_solo_admin(app):
    _sembrar()
    c = app.test_client()
    c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    r = c.post(URL, headers=h, json={'aplicar': True, 'cambios': [
        {'producto': PROD_A, 'de': VIEJO, 'a': NUEVO, 'pct_a': 0.25, 'pct_de': 0}]})
    assert r.status_code in (401, 403)
    assert _items(PROD_A) == {VIEJO: 0.25, OTRO: 99.75}
