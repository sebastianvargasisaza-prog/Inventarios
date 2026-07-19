"""Envases (MEE) por partes (Sebastián 19-jul): la recepción soporta entregas PARCIALES ancladas a la
OC → cada parte crea una Entrada en movimientos_mee (cuarentena) ligada a la OC, la línea acumula
lo recibido y la OC queda 'Parcial' hasta completar. Empaque (MEMP) usa el mismo camino."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302
    return c


def _seed_oc_mee(numero_oc, cod, nombre, unidades):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO maestro_mee (codigo, descripcion, categoria, estado) VALUES (?,?, 'Envase','Activo')",
              (cod, nombre))
    c.execute("INSERT OR REPLACE INTO ordenes_compra (numero_oc, fecha, estado, proveedor, valor_total, categoria, creado_por) "
              "VALUES (?, date('now'), 'Autorizada', 'Prov MEE', 0, 'MEE', 'test')", (numero_oc,))
    c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
              "VALUES (?, ?, ?, ?, 0)", (numero_oc, cod, nombre, unidades))
    conn.commit(); conn.close()


def _oc_estado(numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,)).fetchone()[0]
    finally:
        conn.close()


def _oci_recibido(numero_oc, cod):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT COALESCE(cantidad_recibida_g,0) FROM ordenes_compra_items WHERE numero_oc=? AND codigo_mp=?",
                            (numero_oc, cod)).fetchone()[0]
    finally:
        conn.close()


def _mee_entradas(cod, numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        return conn.execute("SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos_mee "
                            "WHERE mee_codigo=? AND tipo='Entrada' AND lote_ref=? AND UPPER(COALESCE(estado,''))='CUARENTENA'",
                            (cod, numero_oc)).fetchone()
    finally:
        conn.close()


def test_mee_recepcion_por_partes_ancladas(app, db_clean):
    _seed_oc_mee("OC-MEE-P1", "MEE-PARC", "Frasco 30ml", 1000)
    c = _login(app)
    # 1ra parte: 600 de 1000
    r1 = c.post("/api/ordenes-compra/OC-MEE-P1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tok-1",
        "items_recepcion": [{"codigo_mp": "MEE-PARC", "cantidad_recibida": 600, "estado": "OK"}]},
        headers=csrf_headers())
    assert r1.status_code in (200, 201), r1.data[:300]
    assert _oci_recibido("OC-MEE-P1", "MEE-PARC") == 600, "la línea debe acumular 600"
    assert _oc_estado("OC-MEE-P1") == "Parcial", "con faltante la OC queda Parcial"
    n, tot = _mee_entradas("MEE-PARC", "OC-MEE-P1")
    assert n == 1 and tot == 600, "1 Entrada MEE en cuarentena anclada a la OC"
    # 2da parte: los 400 restantes
    r2 = c.post("/api/ordenes-compra/OC-MEE-P1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tok-2",
        "items_recepcion": [{"codigo_mp": "MEE-PARC", "cantidad_recibida": 400, "estado": "OK"}]},
        headers=csrf_headers())
    assert r2.status_code in (200, 201), r2.data[:300]
    assert _oci_recibido("OC-MEE-P1", "MEE-PARC") == 1000, "acumula el total"
    assert _oc_estado("OC-MEE-P1") == "Recibida", "completa → Recibida"
    n2, tot2 = _mee_entradas("MEE-PARC", "OC-MEE-P1")
    assert n2 == 2 and tot2 == 1000, "2 Entradas ancladas, total 1000, ambas en cuarentena"


def _mee_estado(cod, numero_oc):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        r = conn.execute("SELECT id, estado FROM movimientos_mee WHERE mee_codigo=? AND tipo='Entrada' AND lote_ref=? "
                         "ORDER BY id DESC LIMIT 1", (cod, numero_oc)).fetchone()
        return r
    finally:
        conn.close()


def test_ciclo_mee_recepcion_a_disponible(app, db_clean):
    """Ciclo MEE (idéntico a MP): envase recibido → CUARENTENA → aparece en Calidad → F01 conforme + firma
    del jefe → VIGENTE (disponible, deja de estar en cuarentena)."""
    _seed_oc_mee("OC-MEE-C1", "MEE-CICLO", "Tapa negra", 500)
    c = _login(app)
    c.post("/api/ordenes-compra/OC-MEE-C1/recibir", json={
        "receptor_nombre": "Luz", "recepcion_id": "tokc-1",
        "items_recepcion": [{"codigo_mp": "MEE-CICLO", "cantidad_recibida": 500, "estado": "OK"}]},
        headers=csrf_headers())
    row = _mee_estado("MEE-CICLO", "OC-MEE-C1")
    assert row is not None and str(row[1]).upper() == "CUARENTENA", "el envase entra en cuarentena"
    mid = row[0]
    # aparece en el pipeline de Calidad (rama MEE)
    pipe = c.get("/api/calidad/recepcion-pipeline").get_json()
    mee_ids = [l["mov_id"] for l in pipe.get("lotes", []) if l.get("tipo") == "MEE"]
    assert mid in mee_ids, "el envase en cuarentena debe aparecer en Calidad (F01)"
    # F01 conforme + e-firma Part 11 del jefe → libera (envases no llevan F02)
    def _firmar_mee(cl, rid, meaning="libera"):
        rc = cl.post("/api/sign/challenge", json={"password": TEST_PASSWORD, "totp_token": ""}, headers=csrf_headers())
        tok = rc.get_json()["token"]
        rs = cl.post("/api/sign", json={"record_table": "movimientos_mee", "record_id": str(rid),
                                        "meaning": meaning, "challenge_token": tok}, headers=csrf_headers())
        return rs.get_json()["signature_id"]
    sig = _firmar_mee(c, mid, "libera")
    r = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "origen": "MEE", "tipo_insumo": "envase", "crit_rotulado": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel", "aprueba_por": "Laura", "signature_id": sig}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get("liberado") == 1
    row2 = _mee_estado("MEE-CICLO", "OC-MEE-C1")
    assert str(row2[1]).upper() == "VIGENTE", "el envase liberado queda VIGENTE (disponible, fuera de cuarentena)"
    # y ya no aparece en cuarentena/Calidad
    pipe2 = c.get("/api/calidad/recepcion-pipeline").get_json()
    assert mid not in [l["mov_id"] for l in pipe2.get("lotes", [])], "liberado sale del pipeline de cuarentena"
