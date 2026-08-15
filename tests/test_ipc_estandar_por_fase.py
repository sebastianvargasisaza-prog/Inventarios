"""Los controles en proceso dependen de la FASE (15-ago-2026 · clon de MyBatch).

EOS mostraba los mismos cinco controles del granel -Densidad a 25°C, pH, Olor,
Color, Apariencia- en las tres fases. En un legajo de ACONDICIONAMIENTO eso es
pedirle la densidad a una caja: el control no aplica, se marca "No aplica" por
inercia, y el que sí importa (que la etiqueta esté adherida y derecha, que la caja
no venga aplastada, que el sellado sea continuo) no aparece.

MyBatch pide control de llenado en envasado y **14 controles de atributos** en
acondicionamiento, y son los que firma Calidad antes de liberar. Este test fija
que cada fase pida los suyos y que fabricación no cambie.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-IPCFASE"


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _legajo(app, fase, lote, pasos):
    for sql in ("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-IPCFASE%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-IPCFASE%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-IPCFASE%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-IPCFASE%'"):
        try:
            _exec(sql)
        except Exception:
            pass
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-IPCF','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-IPCF','Agua',100,1000)",
          (PRODUCTO,))
    c = _login(app)
    c.post("/api/brd/mbr/generar-desde-formula",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    c.post("/api/brd/mbr/cargar-instructivo",
           json={"producto": PRODUCTO, "fase": fase, "pasos": pasos}, headers=_h())
    c.post("/api/brd/mbr/preparar-aprobado",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": lote, "fase": fase}, headers=_h())
    assert r.status_code in (200, 201), (fase, r.data)
    d = r.get_json()
    return c, (d.get("id") or d.get("ebr_id"))


def _controles(c, ebr_id):
    r = c.get(f"/api/brd/ebr/{ebr_id}/ipc-estandar")
    assert r.status_code == 200, r.data
    return {(it["control_codigo"], it["control_nombre"]) for it in r.get_json()["items"]}


def test_acondicionamiento_pide_los_atributos_no_la_densidad(app, db_clean):
    c, ebr_id = _legajo(app, "acondicionamiento", "LOTE-IPC-OA",
                        ["Paso 1. Etiquetar.", "Paso 2. Encajar."])
    ctrl = _controles(c, ebr_id)
    codigos = {x[0] for x in ctrl}
    assert "etq_adherencia" in codigos, "falta el control de adherencia de la etiqueta"
    assert "caja_integridad" in codigos, "falta el control de la caja plegadiza"
    assert "sellado" in codigos and "legibilidad" in codigos, codigos
    assert len(codigos) >= 14, "MyBatch pide 14 atributos, EOS ofrece %d" % len(codigos)
    assert "densidad" not in codigos, (
        "le sigue pidiendo la densidad a una caja: %s" % sorted(codigos))
    assert "ph" not in codigos, sorted(codigos)


def test_envasado_pide_el_control_de_llenado(app, db_clean):
    c, ebr_id = _legajo(app, "envasado", "LOTE-IPC-OF",
                        ["Paso 1. Llenar.", "Paso 2. Sellar."])
    codigos = {x[0] for x in _controles(c, ebr_id)}
    assert "llenado" in codigos, "falta el control de llenado (el de MyBatch): %s" % codigos
    assert "densidad" not in codigos, codigos


def test_fabricacion_conserva_los_cinco_de_siempre(app, db_clean):
    """Lo que ya se usa no cambia: el granel sí se mide por densidad y pH."""
    c, ebr_id = _legajo(app, "fabricacion", "LOTE-IPC-OP",
                        ["Paso 1. Mezclar.", "Paso 2. Enfriar."])
    codigos = {x[0] for x in _controles(c, ebr_id)}
    for cod in ("densidad", "ph", "olor", "color", "apariencia"):
        assert cod in codigos, "se perdió el control %s de fabricación: %s" % (cod, codigos)


def test_se_puede_registrar_un_atributo_de_acondicionamiento(app, db_clean):
    """Ofrecer el control y no dejar registrarlo sería una lista decorativa."""
    c, ebr_id = _legajo(app, "acondicionamiento", "LOTE-IPC-OA2",
                        ["Paso 1. Etiquetar."])
    r = c.post(f"/api/brd/ebr/{ebr_id}/ipc-estandar",
               json={"control_codigo": "etq_adherencia", "valor_texto": "Cumple",
                     "conforme": 1}, headers=_h())
    assert r.status_code in (200, 201), r.data
    reg = [it for it in c.get(f"/api/brd/ebr/{ebr_id}/ipc-estandar").get_json()["items"]
           if it["control_codigo"] == "etq_adherencia"]
    assert reg and reg[0]["conforme"] == 1, reg
