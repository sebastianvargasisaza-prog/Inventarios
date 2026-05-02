"""Tests del endpoint /api/bandeja-ceo + página /mi-bandeja.

Verifica:
- RBAC: solo admin
- Estructura del JSON: timestamp, total, counts, items
- Items con campos esperados (severidad, modulo, titulo, link, etc.)
- Detección de items críticos/high/medium con datos sembrados
- UI render con elementos clave
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


def test_bandeja_requires_auth(client, db_clean):
    r = client.get("/api/bandeja-ceo")
    assert r.status_code == 401


def test_bandeja_no_admin_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/bandeja-ceo")
    assert r.status_code == 403


def test_bandeja_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/bandeja-ceo")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("timestamp", "usuario", "total", "counts", "items"):
        assert k in d
    assert isinstance(d["items"], list)
    assert isinstance(d["counts"], dict)
    for sev in ("critical", "high", "medium"):
        assert sev in d["counts"]


def test_bandeja_item_estructura(app, db_clean):
    """Sembrar 1 hallazgo INVIMA vencido y verificar que aparece como crítico."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO hallazgos
        (codigo, origen, titulo, severidad, fecha_limite, estado, fecha_deteccion)
        VALUES ('HLZ-INV-T1', 'INVIMA', 'Test crítico vencido',
                'mayor', date('now','-15 days'), 'abierto', date('now','-30 days'))""")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/bandeja-ceo")
        d = r.get_json()
        # Debe aparecer un item crítico de compliance
        criticos = [it for it in d["items"]
                     if it["severidad"] == "critical" and it["modulo"] == "compliance"]
        match = [it for it in criticos if "HLZ-INV-T1" in it["titulo"]]
        assert len(match) >= 1, f"Hallazgo INVIMA no apareció. items: {d['items']}"
        item = match[0]
        for k in ("severidad", "modulo", "titulo", "descripcion", "link", "edad_dias"):
            assert k in item
        assert item["link"] == "/compliance"
        assert item["edad_dias"] >= 14
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM hallazgos WHERE codigo='HLZ-INV-T1'")
        conn.commit(); conn.close()


def test_bandeja_oc_autorizada_pendiente_aparece(app, db_clean):
    """OC autorizada hace 10 días sin pagar debe aparecer como high."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
        (numero_oc, fecha, estado, proveedor, valor_total, fecha_autorizacion)
        VALUES ('OC-BANDEJA-T1', date('now','-15 days'), 'Autorizada',
                'Prov bandeja test', 5000000, date('now','-10 days'))""")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/bandeja-ceo")
        d = r.get_json()
        match = [it for it in d["items"]
                  if "OC-BANDEJA-T1" in it["titulo"]]
        assert len(match) >= 1
        item = match[0]
        assert item["severidad"] == "high"
        assert item["modulo"] == "compras"
        assert item["edad_dias"] >= 9
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-BANDEJA-T1'")
        conn.commit(); conn.close()


def test_bandeja_invima_por_vencer_30d_aparece_medium(app, db_clean):
    """Registro INVIMA que vence en 20 días debe aparecer como medium."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO registros_invima
        (producto, num_registro, tipo_tramite, fecha_vencimiento, estado)
        VALUES ('Producto Bandeja Test', 'NSO-BAND-T1', 'Notificacion Sanitaria',
                date('now','+20 days'), 'Vigente')""")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/bandeja-ceo")
        d = r.get_json()
        match = [it for it in d["items"]
                  if "NSO-BAND-T1" in it["titulo"]]
        assert len(match) >= 1
        item = match[0]
        assert item["severidad"] == "medium"
        assert item["modulo"] == "tecnica"
        # Edad ~ 20 días
        assert item["edad_dias"] >= 19
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM registros_invima WHERE num_registro='NSO-BAND-T1'")
        conn.commit(); conn.close()


def test_bandeja_counts_consistentes(app, db_clean):
    """counts debe sumar igual al total de items."""
    c = _login(app, "sebastian")
    r = c.get("/api/bandeja-ceo")
    d = r.get_json()
    suma = sum(d["counts"].values())
    assert suma == d["total"]


def test_mi_bandeja_page_requires_auth(client, db_clean):
    r = client.get("/mi-bandeja", follow_redirects=False)
    assert r.status_code == 302  # redirect to /login


def test_mi_bandeja_page_no_admin_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/mi-bandeja")
    assert r.status_code == 403


def test_mi_bandeja_page_admin_renderiza(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/mi-bandeja")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Mi Bandeja" in body
    assert "/api/bandeja-ceo" in body
    # Filtros visibles
    for label in ("Críticos", "Alta", "Media"):
        assert label in body
    # Auto-refresh wired
    assert "setInterval" in body
    assert "loadBandeja" in body
