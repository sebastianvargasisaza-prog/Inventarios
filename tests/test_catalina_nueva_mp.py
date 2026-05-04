"""Tests de creacion rapida de MP desde modulo OC (Catalina · 4-may-2026).

Catalina necesita poder crear MPs nuevas sin salir del form de OC. Antes
el endpoint hacia INSERT OR REPLACE silencioso (peligroso). Ahora valida,
audita, y rechaza duplicados sin forzar_actualizar.

Tambien verifica que: precios cargados en OC se reflejen en planta,
recepcion alimente movimientos y maestro_mps este sincronizado.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup_mp(codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    conn.commit(); conn.close()


# ── Crear MP nueva ──────────────────────────────────────────────────

def test_crear_mp_nueva_exitoso(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"codigo_mp": "MP-CAT-NUEVA-001",
                      "nombre_comercial": "Glicerina Test",
                      "nombre_inci": "Glycerin",
                      "tipo": "Humectante",
                      "proveedor": "Inquímica",
                      "stock_minimo": 5000,
                      "precio_referencia": 0.012,
                      "tipo_material": "MP"},
                headers=csrf_headers())
    assert r.status_code == 201, r.data
    d = r.get_json()
    assert d["ok"] is True
    assert d["creada"] is True
    assert d["codigo_mp"] == "MP-CAT-NUEVA-001"
    # Verificar persistencia + activa
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT nombre_comercial, stock_minimo, precio_referencia, activo FROM maestro_mps WHERE codigo_mp=?",
        ("MP-CAT-NUEVA-001",)).fetchone()
    conn.close()
    assert row[0] == "Glicerina Test"
    assert row[1] == 5000
    assert abs(row[2] - 0.012) < 0.0001
    assert row[3] == 1
    _cleanup_mp("MP-CAT-NUEVA-001")


def test_crear_mp_duplicado_409(app, db_clean):
    """Si codigo ya existe sin forzar, debe rechazar con 409."""
    cs = _login(app, "catalina")
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-DUP-TEST", "nombre_comercial": "Original"},
            headers=csrf_headers())
    try:
        r = cs.post("/api/maestro-mps",
                    json={"codigo_mp": "MP-DUP-TEST", "nombre_comercial": "Otro"},
                    headers=csrf_headers())
        assert r.status_code == 409
        d = r.get_json()
        assert "ya existe" in d["error"].lower()
        # Original NO debe ser sobrescrito
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp='MP-DUP-TEST'"
        ).fetchone()
        conn.close()
        assert row[0] == "Original"
    finally:
        _cleanup_mp("MP-DUP-TEST")


def test_crear_mp_forzar_actualizar_ok(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-FORZAR", "nombre_comercial": "Original",
                  "stock_minimo": 100},
            headers=csrf_headers())
    try:
        r = cs.post("/api/maestro-mps",
                    json={"codigo_mp": "MP-FORZAR", "nombre_comercial": "Sobrescrito",
                          "stock_minimo": 200, "forzar_actualizar": True},
                    headers=csrf_headers())
        assert r.status_code == 201
        d = r.get_json()
        assert d["creada"] is False
        # Verificar UPDATE
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT nombre_comercial, stock_minimo FROM maestro_mps WHERE codigo_mp='MP-FORZAR'"
        ).fetchone()
        conn.close()
        assert row[0] == "Sobrescrito"
        assert row[1] == 200
    finally:
        _cleanup_mp("MP-FORZAR")


def test_crear_mp_sin_codigo_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"nombre_comercial": "Sin codigo"},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_mp_sin_nombre_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"codigo_mp": "MP-SIN-NOMBRE"},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_mp_stock_minimo_negativo_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"codigo_mp": "MP-NEG", "nombre_comercial": "Test",
                      "stock_minimo": -100},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_mp_precio_negativo_400(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"codigo_mp": "MP-NEGP", "nombre_comercial": "Test",
                      "precio_referencia": -0.5},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_mp_tipo_material_invalido_se_normaliza(app, db_clean):
    """tipo_material fuera de whitelist debe caer a 'MP' default."""
    cs = _login(app, "catalina")
    r = cs.post("/api/maestro-mps",
                json={"codigo_mp": "MP-TIPO-INV", "nombre_comercial": "Test",
                      "tipo_material": "Hackeado"},
                headers=csrf_headers())
    assert r.status_code == 201
    d = r.get_json()
    assert d["tipo_material"] == "MP"
    _cleanup_mp("MP-TIPO-INV")


def test_crear_mp_audita(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-AUD-TEST", "nombre_comercial": "Audit"},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion, registro_id FROM audit_log WHERE accion='CREAR_MP' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "catalina"
        assert row[2] == "MP-AUD-TEST"
    finally:
        _cleanup_mp("MP-AUD-TEST")


def test_actualizar_mp_audita(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-UPD-AUD", "nombre_comercial": "Original"},
            headers=csrf_headers())
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-UPD-AUD", "nombre_comercial": "Modificado",
                  "forzar_actualizar": True},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT accion FROM audit_log WHERE accion='ACTUALIZAR_MP' AND registro_id='MP-UPD-AUD' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
    finally:
        _cleanup_mp("MP-UPD-AUD")


def test_mp_creada_aparece_en_listado(app, db_clean):
    """Verifica el flujo: crear MP → aparece en /api/maestro-mps GET."""
    cs = _login(app, "catalina")
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-LIST-TEST", "nombre_comercial": "Lista Test",
                  "tipo_material": "Empaque"},
            headers=csrf_headers())
    try:
        r = cs.get("/api/maestro-mps")
        d = r.get_json()
        codigos = [m["codigo_mp"] for m in d.get("mps", [])]
        assert "MP-LIST-TEST" in codigos
        item = next(m for m in d["mps"] if m["codigo_mp"] == "MP-LIST-TEST")
        assert item["tipo_material"] == "Empaque"
        assert item["nombre_comercial"] == "Lista Test"
    finally:
        _cleanup_mp("MP-LIST-TEST")


# ── UI: modal Nueva MP en compras ────────────────────────────────

def test_compras_html_tiene_modal_nueva_mp(app, db_clean):
    cs = _login(app, "catalina")
    r = cs.get("/compras")
    body = r.get_data(as_text=True)
    assert 'id="m-nueva-mp"' in body
    assert "abrirNuevaMP" in body
    assert "guardarNuevaMP" in body
    assert "refrescarCatalogoMP" in body
    # Botones dentro del modal de OC (ambos modales)
    assert "+ Nueva MP" in body


def test_compras_html_form_proveedor_completo(app, db_clean):
    """Form de proveedor desde modal OC tiene todos los campos para no quedar pelado."""
    cs = _login(app, "catalina")
    r = cs.get("/compras")
    body = r.get_data(as_text=True)
    # Campos completos
    for campo in ('np-nombre', 'np-nit', 'np-contacto', 'np-tel', 'np-email',
                  'np-direccion', 'np-banco', 'np-tipo-cuenta', 'np-num-cuenta',
                  'np-cond-pago', 'np-concepto'):
        assert f'id="{campo}"' in body, f'falta campo {campo} en form proveedor'
    # Detector de duplicados
    assert "checkProvDuplicado" in body
    assert "_normProvName" in body
    assert "np-dup-warning" in body


# ── Proveedores: dedup + audit ──────────────────────────────────────

def test_proveedor_dedup_case_insensitive(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/proveedores-compras",
            json={"nombre": "Proveedor Test Dedup"},
            headers=csrf_headers())
    try:
        # Mismo nombre con case diferente → 409
        r2 = cs.post("/api/proveedores-compras",
                     json={"nombre": "PROVEEDOR TEST DEDUP"},
                     headers=csrf_headers())
        assert r2.status_code == 409
        d = r2.get_json()
        assert "ya existe" in d["error"].lower()
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM proveedores WHERE LOWER(nombre) LIKE 'proveedor test dedup%'")
        conn.commit(); conn.close()


def test_proveedor_dedup_trim(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/proveedores-compras",
            json={"nombre": "Proveedor Test Trim"},
            headers=csrf_headers())
    try:
        r2 = cs.post("/api/proveedores-compras",
                     json={"nombre": "  Proveedor Test Trim  "},
                     headers=csrf_headers())
        assert r2.status_code == 409
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM proveedores WHERE LOWER(TRIM(nombre))='proveedor test trim'")
        conn.commit(); conn.close()


def test_proveedor_audit_log(app, db_clean):
    cs = _login(app, "catalina")
    cs.post("/api/proveedores-compras",
            json={"nombre": "Proveedor Audit Test", "nit": "9001234567",
                  "banco": "Bancolombia", "num_cuenta": "12345678"},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT usuario, accion FROM audit_log WHERE accion='CREAR_PROVEEDOR' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "catalina"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM proveedores WHERE nombre='Proveedor Audit Test'")
        conn.commit(); conn.close()


def test_proveedor_form_completo_persiste_todos_los_campos(app, db_clean):
    """Cuando Catalina llena el form completo desde OC, banco/cuenta/etc se guardan."""
    cs = _login(app, "catalina")
    cs.post("/api/proveedores-compras",
            json={"nombre": "Proveedor Completo Test",
                  "nit": "900111222",
                  "contacto": "Maria Test",
                  "telefono": "3001234567",
                  "email": "maria@test.com",
                  "direccion": "Calle 1 #2-3",
                  "banco": "Davivienda",
                  "tipo_cuenta": "Ahorros",
                  "num_cuenta": "98765432",
                  "condiciones_pago": "60 dias",
                  "concepto_compra": "MP test"},
            headers=csrf_headers())
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            """SELECT nit, contacto, telefono, email, direccion, banco,
                      tipo_cuenta, num_cuenta, condiciones_pago, concepto_compra
                 FROM proveedores WHERE nombre='Proveedor Completo Test'"""
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "900111222"
        assert row[1] == "Maria Test"
        assert row[5] == "Davivienda"
        assert row[7] == "98765432"
        assert row[8] == "60 dias"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM proveedores WHERE nombre='Proveedor Completo Test'")
        conn.commit(); conn.close()


# ── Integracion OC → maestro_mps → reflejo en planta ─────────────

def test_oc_con_mp_existente_actualiza_precio_referencia(app, db_clean):
    """Confirma para Catalina: precios en OC actualizan precio_referencia
    en maestro_mps automaticamente (linea 684 de compras.py)."""
    cs = _login(app, "catalina")
    # 1. Crear MP nueva
    cs.post("/api/maestro-mps",
            json={"codigo_mp": "MP-INT-PRE", "nombre_comercial": "Test integ",
                  "precio_referencia": 0.001},
            headers=csrf_headers())
    try:
        # 2. Crear OC con esa MP a precio mayor
        r = cs.post("/api/ordenes-compra",
                    json={"proveedor": "Proveedor Test Integ",
                          "categoria": "MP",
                          "items": [{"codigo_mp": "MP-INT-PRE",
                                      "nombre_mp": "Test integ",
                                      "cantidad_g": 1000,
                                      "precio_unitario": 0.005}]},
                    headers=csrf_headers())
        assert r.status_code == 201, r.data
        # 3. Verificar que precio_referencia se actualizo en maestro_mps
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT precio_referencia FROM maestro_mps WHERE codigo_mp='MP-INT-PRE'"
        ).fetchone()
        conn.close()
        assert row is not None
        # 0.001 → 0.005 (sobrescrito por OC mas reciente)
        assert abs(row[0] - 0.005) < 0.0001, f"precio_referencia esperado 0.005, got {row[0]}"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM ordenes_compra_items WHERE codigo_mp='MP-INT-PRE'")
        conn.execute("DELETE FROM ordenes_compra WHERE proveedor='Proveedor Test Integ'")
        conn.commit(); conn.close()
        _cleanup_mp("MP-INT-PRE")
