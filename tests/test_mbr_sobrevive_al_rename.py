"""Un MBR aprobado conserva el nombre VIEJO · el producto renombrado no puede quedarse sin legajo.

Un MBR aprobado es INMUTABLE (mig 109), así que al renombrar un producto su nombre queda viejo y
`crear_ebr_desde_mbr` -- que lo busca por nombre con UPPER(TRIM) -- deja de encontrarlo: el
producto pasa a NO poder generar su batch record.

Pasó de verdad el 2-ago: al renombrar "HYDRA BALANCE" → "HYDRABALANCE" y "SUERO DE VITAMINA C+
FORMULA NUEVA" → "Suero Vitamina C+", la herramienta lo reportó como `aprobados_inmutables: 2` --
que se lee como un pendiente de Calidad y era una ROTURA.

El documento sigue siendo VÁLIDO; lo viejo es la etiqueta. Estos tests fijan que:
  · el legajo se sigue creando cuando el MBR conserva el nombre viejo
  · el rename DEJA el puente (causa raíz), no sólo lo reporta
  · con dos candidatos ambiguos NO se elige uno (un dato regulado no se adivina · M19/M132)
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD_VIEJO, PROD_NUEVO = 'QA MBR RENAME VIEJO', 'QAMBRRENAMEVIEJO'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _limpiar():
    db = _db()
    try:
        for p in (PROD_VIEJO, PROD_NUEVO, 'QA MBR OTRO'):
            db.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (p,))
            db.execute("DELETE FROM producto_formula_alias WHERE producto_plan=? OR producto_formula=?",
                       (p, p))
        db.commit()
    finally:
        db.close()


def _mbr(nombre, estado='aprobado', version=1):
    db = _db()
    try:
        db.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                   "creado_por) VALUES (?,?,?,1000,'qa')", (nombre, version, estado))
        db.commit()
    finally:
        db.close()


def _buscar(app, nombre):
    """Corre el resolutor real de `crear_ebr_desde_mbr` sobre el nombre dado."""
    try:
        from api.blueprints import brd as B
    except Exception:
        from blueprints import brd as B
    db = _db()
    try:
        db.row_factory = sqlite3.Row
        with app.app_context():
            return B.crear_ebr_desde_mbr(db.cursor(), producto_nombre=nombre,
                                         lote='QA-LOTE-%s' % os.urandom(3).hex())
    finally:
        db.close()


def test_encuentra_el_MBR_aunque_conserve_el_nombre_viejo(app):
    """"HYDRA BALANCE" vs "HYDRABALANCE": UPPER(TRIM) no colapsa el espacio de adentro."""
    _limpiar(); _mbr(PROD_VIEJO)
    r = _buscar(app, PROD_NUEVO)
    assert r.get('error') != 'NO_MBR_APROBADO', (
        'el producto renombrado se quedó sin batch record: %r' % r)


def test_con_DOS_candidatos_ambiguos_no_elige(app):
    """Un dato regulado no se adivina: con dos MBR que normalizan igual, se avisa."""
    _limpiar(); _mbr(PROD_VIEJO); _mbr('QAMBR RENAME VIEJO', version=2)
    r = _buscar(app, PROD_NUEVO)
    assert r.get('error') == 'NO_MBR_APROBADO', (
        'con dos candidatos NO puede elegir uno: %r' % r)
    _limpiar()


def test_el_rename_DEJA_el_puente(app):
    """La causa raíz: hasta hoy sólo se REPORTABA que el MBR quedaba con el nombre viejo."""
    _limpiar(); _mbr(PROD_VIEJO)
    db = _db()
    try:
        db.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, activo) "
                   "VALUES (?,1000,1)", (PROD_VIEJO,))
        db.commit()
    finally:
        db.close()
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    c.post('/api/admin/renombrar-producto', headers=h,
           json={'viejo': PROD_VIEJO, 'nuevo': PROD_NUEVO, 'dry_run': 0})
    db = _db()
    try:
        r = db.execute("SELECT producto_formula FROM producto_formula_alias "
                       "WHERE producto_plan=? AND COALESCE(activo,1)=1", (PROD_NUEVO,)).fetchone()
        assert r and r[0] == PROD_VIEJO, 'el rename tiene que dejar el puente al MBR aprobado'
    finally:
        db.close()
        _limpiar()
