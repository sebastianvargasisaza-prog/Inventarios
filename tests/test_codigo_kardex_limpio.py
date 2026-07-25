"""Un código con espacio o tabulador invisible parte el stock en silencio (25-jul).

Caso real en producción: 1000 unidades del envase MEE-IMP-020 entraron al kardex como
`'\\tMEE-IMP-020'` (un tabulador pegado al copiar/pegar la OC). Para la app eso es una CLAVE
DISTINTA: no cruza con fórmulas, no suma al stock de envases, no aparece en abastecimiento.
Stock invisible, sin ningún error a la vista.

Dos defensas:
  · `recibir_oc` limpia el código ANTES de tocar el kardex (los dos sitios donde desempaqueta
    el ítem de la OC)
  · mig 379 corrige la fila que ya existía

Y el invariante de abajo lo caza si vuelve a colarse por otro camino.
"""
import os
import re
import sqlite3

CTRL = re.compile(r'[\x00-\x1f]')


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sucios(filas):
    out = []
    for (val,) in filas:
        s = '' if val is None else str(val)
        if not s:
            continue
        if s != s.strip() or CTRL.search(s):
            out.append({'valor': repr(s), 'codepoints': [ord(ch) for ch in s[:4]]})
    return out


def test_ningun_codigo_del_kardex_tiene_espacios_ni_control(app):
    """MP y envases: la clave del kardex tiene que estar limpia."""
    db = _db()
    try:
        mp = db.execute("SELECT DISTINCT material_id FROM movimientos "
                        "WHERE material_id IS NOT NULL AND material_id <> ''").fetchall()
        mee = db.execute("SELECT DISTINCT mee_codigo FROM movimientos_mee "
                         "WHERE mee_codigo IS NOT NULL AND mee_codigo <> ''").fetchall()
    finally:
        db.close()
    assert _sucios(mp) == [], 'códigos de MP sucios en el kardex: %s' % _sucios(mp)
    assert _sucios(mee) == [], 'códigos de envase sucios en el kardex: %s' % _sucios(mee)


def test_ningun_codigo_del_maestro_ni_de_las_OC_tiene_basura(app):
    """Si el maestro o la OC traen el código sucio, el kardex se ensucia en la próxima recepción."""
    db = _db()
    try:
        mps = db.execute("SELECT DISTINCT codigo_mp FROM maestro_mps "
                         "WHERE codigo_mp IS NOT NULL AND codigo_mp <> ''").fetchall()
        mees = db.execute("SELECT DISTINCT codigo FROM maestro_mee "
                          "WHERE codigo IS NOT NULL AND codigo <> ''").fetchall()
        oci = db.execute("SELECT DISTINCT codigo_mp FROM ordenes_compra_items "
                         "WHERE codigo_mp IS NOT NULL AND codigo_mp <> ''").fetchall()
    finally:
        db.close()
    assert _sucios(mps) == [], 'maestro_mps: %s' % _sucios(mps)
    assert _sucios(mees) == [], 'maestro_mee: %s' % _sucios(mees)
    assert _sucios(oci) == [], 'ordenes_compra_items: %s' % _sucios(oci)


def test_la_recepcion_limpia_el_codigo_antes_de_tocar_el_kardex(app):
    """El guard vive en los DOS sitios donde recibir_oc desempaqueta el ítem de la OC."""
    import inspect

    from blueprints.compras import recibir_oc
    src = inspect.getsource(recibir_oc)
    assert src.count("codigo = (codigo or '').strip()") >= 2, (
        'los dos caminos de recepción deben limpiar el código, no sólo uno')


def test_un_codigo_con_tab_es_una_clave_distinta(app):
    """Deja explícito POR QUÉ importa: no es cosmético, es otra llave."""
    assert '\tMEE-IMP-020' != 'MEE-IMP-020'
    assert '\tMEE-IMP-020'.strip() == 'MEE-IMP-020'
    d = {'MEE-IMP-020': 1000}
    assert d.get('\tMEE-IMP-020') is None, 'por eso el stock quedaba invisible'


def test_un_envase_no_puede_entrar_al_kardex_de_materia_prima(app):
    """Un envase recibido por OC cuyo codigo aun no esta en maestro_mee caia al kardex de MP.

    Caso real (25-jul): MEE-IMP-019 y MEE-IMP-020, 1000 uds cada uno, quedaron dentro de
    `movimientos`. Inflaban el inventario de MP, dejaban el stock de envase en 0 (abastecimiento
    los volvia a pedir) y se saltaban la cuarentena de envases. Sin un solo error a la vista.
    """
    import inspect

    from blueprints.compras import recibir_oc
    src = inspect.getsource(recibir_oc)
    assert "prefijo de ENVASE" in src, (
        "recibir_oc debe enrutar por prefijo cuando el codigo aun no esta en maestro_mee")


def test_la_auditoria_reporta_envases_dentro_del_kardex_de_MP(app):
    """El desvio tiene que ser VISIBLE, no descubrirse revisando a mano."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    d = c.get("/api/admin/auditoria-lotes?dias=2").get_json()
    assert "envases_en_kardex_mp" in d, d.keys()
    assert "envases_en_kardex_mp_error" not in d, d.get("envases_en_kardex_mp_error")
    assert isinstance(d["envases_en_kardex_mp"], list)
