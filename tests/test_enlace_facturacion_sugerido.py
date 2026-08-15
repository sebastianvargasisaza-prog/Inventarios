"""El enlace de facturación se SUGIERE, nunca se hace solo (15-ago-2026).

Sin el enlace entre la credencial del portal y la cuenta de facturación, el cliente entra
y su módulo de Facturas sale VACÍO — y una lista vacía se lee como *"no debo nada"*, que
es lo contrario de *"no se pudo cruzar"* (M200). Por eso el enlace lo fija una persona:
enlazar mal deja a un cliente viendo las facturas de otro, y eso no se descubre hasta que
alguien reclama.

Lo que este guard fija es el punto medio correcto: cuando el cruce es INEQUÍVOCO se
propone y se dice de dónde sale, para que confirmar cueste un clic; cuando es ambiguo NO
se propone nada (M179: se ofrece, no se elige solo).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM portal_clientes_credenciales WHERE cliente_id LIKE 'ZENL%'",
                "DELETE FROM clientes WHERE nombre LIKE 'ZENL%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _cred(cliente_id, nombre, email):
    return _exec(
        "INSERT INTO portal_clientes_credenciales (cliente_id, cliente_nombre, email, "
        "password_hash, activo, creado_por, creado_at_utc) "
        "VALUES (?,?,?,'x',1,'sebastian','2026-08-15 10:00:00')",
        (cliente_id, nombre, email))


def _cuenta(nombre, nit=''):
    return _exec("INSERT INTO clientes (nombre, nit, activo) VALUES (?,?,1)", (nombre, nit))


def _credenciales(app):
    c = _login(app)
    r = c.get("/api/admin/portal/credenciales")
    assert r.status_code == 200, r.data[:200]
    return {i["cliente_id"]: i for i in r.get_json()["items"]}


def test_sugiere_cuando_el_nombre_cruza_exacto_y_es_unico(app, db_clean):
    _limpiar()
    cta = _cuenta("ZENL Kelly Cosmetics", "")
    _cred("ZENL-kelly", "ZENL Kelly Cosmetics", "kelly@zenl.test")
    it = _credenciales(app)["ZENL-kelly"]
    assert it["sugerido_id"] == cta, it
    assert it["sugerido_por"] == "nombre", it
    assert "Kelly" in it["sugerido_nombre"]


def test_no_sugiere_nada_cuando_hay_dos_candidatas(app, db_clean):
    """Con dos cuentas que normalizan igual no hay forma de saber cuál es (M179/M19)."""
    _limpiar()
    _cuenta("ZENL Dos Iguales")
    _cuenta("zenl  dos   iguales")     # normaliza al mismo texto
    _cred("ZENL-dos", "ZENL Dos Iguales", "dos@zenl.test")
    it = _credenciales(app)["ZENL-dos"]
    assert it["sugerido_id"] is None, (
        "propuso una cuenta habiendo dos candidatas: así se enlaza al cliente equivocado")


def test_no_sugiere_cuando_no_hay_a_quien_parecerse(app, db_clean):
    _limpiar()
    _cuenta("ZENL Otra Empresa")
    _cred("ZENL-sola", "ZENL Sin Pareja", "sola@zenl.test")
    it = _credenciales(app)["ZENL-sola"]
    assert it["sugerido_id"] is None, it


def test_lo_ya_enlazado_no_se_toca(app, db_clean):
    """Una sugerencia sobre algo ya resuelto invita a cambiarlo sin motivo."""
    _limpiar()
    cta = _cuenta("ZENL Ya Enlazada")
    cid = _cred("ZENL-ya", "ZENL Ya Enlazada", "ya@zenl.test")
    _exec("UPDATE portal_clientes_credenciales SET cliente_ref_id=? WHERE id=?", (cta, cid))
    it = _credenciales(app)["ZENL-ya"]
    assert it["cliente_ref_id"] == cta
    assert "sugerido_id" not in it or it.get("sugerido_id") is None, it


def test_la_pantalla_presselecciona_y_dice_que_es_una_sugerencia(app, db_clean):
    """Preseleccionar sin decir que es una sugerencia se lee como un hecho ya resuelto."""
    c = _login(app)
    html = c.get("/admin/portal-pagos").data.decode("utf-8")
    for que, pieza in (("la preselección", "if(c.sugerido_id){"),
                       ("el aviso de que hay que confirmar", "confirm&aacute;"),
                       ("de dónde sale la sugerencia", "sugerido por ")):
        assert pieza in html, "la pantalla no muestra %s" % que


def test_la_sugerencia_nunca_escribe(app, db_clean):
    """Sugerir y enlazar son dos actos distintos: el segundo lo hace una persona."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "portal.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("def _sugerir_cuenta_facturacion(")
    assert i > 0, "no está el helper"
    bloque = fuente[i:i + 3000]
    for prohibido in ("UPDATE ", "INSERT ", "DELETE ", "commit()"):
        assert prohibido not in bloque, (
            "el sugeridor escribe (%s): enlazar es una decisión de una persona" % prohibido)
