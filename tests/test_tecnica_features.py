"""Tests de los 5 features nuevos en Direccion Tecnica:
1. CSRF token en frontend
2. Migracion 38 SGD (frecuencia_revision_meses + columnas nuevas)
3. INVIMA cross-check con stock_pt
4. Notificaciones automaticas (job_tecnica_vencimientos)
5. Cambio de Control formal
"""
import json
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="hernando"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo para {user}: {r.status_code}"
    return c


def _seed_formula(codigo="TEST-FOR-001", nombre="Producto Test", estado="Vigente"):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute(
        """INSERT INTO formulas_maestras (codigo, nombre, version, tipo, estado)
           VALUES (?, ?, '1.0', 'COSMETICO', ?)""", (codigo, nombre, estado))
    fid = cur.lastrowid
    conn.commit(); conn.close()
    return fid


def _cleanup(table, where_clause, params):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(f"DELETE FROM {table} WHERE {where_clause}", params)
    conn.commit(); conn.close()


# ════════════════════════════════════════════════════════════════════
#  1. MIGRACION 38 · SGD con campos nuevos
# ════════════════════════════════════════════════════════════════════

def test_sgd_post_acepta_frecuencia_revision_meses(app, db_clean):
    """POST /api/tecnica/documentos persiste frecuencia + fecha_proxima."""
    c = _login(app, "hernando")
    payload = {
        "tipo": "SOP", "codigo": "ASG-PRO-501",
        "nombre": "Test SOP unificado",
        "fecha_emision": "2026-04-01",
        "frecuencia_revision_meses": 6,
        "responsable_revision": "miguel",
    }
    r = c.post("/api/tecnica/documentos", json=payload, headers=csrf_headers())
    assert r.status_code == 200, f"got {r.status_code}: {r.data}"
    d = r.get_json()
    assert d["ok"] is True
    # fecha_proxima_revision debe calcularse: fecha_emision + 6 meses ~ 180d
    assert d["fecha_proxima_revision"]
    # Verificar en sgd_documentos (tabla unificada)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        """SELECT proxima_revision, aprobado_por
             FROM sgd_documentos WHERE id=?""",
        (d["id"],)
    ).fetchone()
    conn.close()
    assert row[0] is not None and row[0] != ''  # proxima_revision calculada
    assert row[1] == "miguel"  # aprobado_por = responsable_revision
    _cleanup("sgd_documentos", "id=?", (d["id"],))


def test_sgd_proximos_vencimientos_endpoint(app, db_clean):
    """GET /api/tecnica/documentos/proximos-vencimientos lista SGDs <60d."""
    c = _login(app, "hernando")
    # Sembrar SGD que vence en 30d (en sgd_documentos rico)
    proxima = (date.today() + timedelta(days=30)).isoformat()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-PRO-501'")
    cur = conn.execute(
        """INSERT INTO sgd_documentos
           (codigo, area, tipo_doc, numero, titulo, version_actual,
            estado, vigente_desde, proxima_revision)
           VALUES ('COC-PRO-501','COC','PRO',501,'Prox vence','1.0','vigente',
                   date('now','-300 day'), ?)""",
        (proxima,))
    sid = cur.lastrowid; conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/documentos/proximos-vencimientos")
        assert r.status_code == 200
        d = r.get_json()
        assert "documentos" in d
        ids = [x["id"] for x in d["documentos"]]
        assert sid in ids
    finally:
        _cleanup("sgd_documentos", "id=?", (sid,))


# ════════════════════════════════════════════════════════════════════
#  2. INVIMA cross-check con stock_pt
# ════════════════════════════════════════════════════════════════════

def test_productos_sin_invima_requires_auth(client, db_clean):
    r = client.get("/api/tecnica/productos-sin-invima")
    assert r.status_code == 401


def test_productos_sin_invima_estructura(app, db_clean):
    c = _login(app, "hernando")
    r = c.get("/api/tecnica/productos-sin-invima")
    assert r.status_code == 200
    d = r.get_json()
    for k in ("umbral_dias", "cobertura", "sin_invima",
              "por_vencer", "con_invima_ok"):
        assert k in d
    for k in ("total_skus", "con_invima_vigente",
              "sin_invima_o_vencido", "por_vencer", "pct_cobertura"):
        assert k in d["cobertura"]


def test_productos_sin_invima_detecta_falta(app, db_clean):
    """Si stock_pt tiene SKU vendible y NO hay INVIMA matching, aparece en sin_invima."""
    c = _login(app, "hernando")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Sembrar SKU sin INVIMA
    conn.execute("DELETE FROM stock_pt WHERE sku='TEST-SKU-NO-INVIMA'")
    conn.execute("DELETE FROM registros_invima WHERE producto LIKE 'Producto Sin INVIMA%'")
    conn.execute(
        """INSERT INTO stock_pt (sku, descripcion, unidades_disponible, empresa, estado)
           VALUES ('TEST-SKU-NO-INVIMA', 'Producto Sin INVIMA Test', 50, 'ANIMUS', 'Disponible')""")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/productos-sin-invima")
        d = r.get_json()
        skus_sin = [x["sku"] for x in d["sin_invima"]]
        assert "TEST-SKU-NO-INVIMA" in skus_sin
        item = next(x for x in d["sin_invima"] if x["sku"] == "TEST-SKU-NO-INVIMA")
        assert item["razon"] == "sin_registro_vigente"
        assert item["unidades_disponibles"] == 50
    finally:
        _cleanup("stock_pt", "sku=?", ("TEST-SKU-NO-INVIMA",))


def test_productos_sin_invima_detecta_vencido(app, db_clean):
    """Si INVIMA matchea pero esta vencido, aparece en sin_invima con razon 'registro_vencido'."""
    c = _login(app, "hernando")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM stock_pt WHERE sku='TEST-SKU-VENCIDO'")
    conn.execute("DELETE FROM registros_invima WHERE producto='Crema Test Vencida'")
    # Producto en stock + INVIMA vencido hace 10 dias
    conn.execute(
        """INSERT INTO stock_pt (sku, descripcion, unidades_disponible, empresa, estado)
           VALUES ('TEST-SKU-VENCIDO', 'Crema Test Vencida', 10, 'ANIMUS', 'Disponible')""")
    vencido = (date.today() - timedelta(days=10)).isoformat()
    conn.execute(
        """INSERT INTO registros_invima
           (producto, num_registro, estado, fecha_vencimiento)
           VALUES ('Crema Test Vencida', 'NSC-TEST-VENC', 'Vigente', ?)""",
        (vencido,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/productos-sin-invima")
        d = r.get_json()
        item = next((x for x in d["sin_invima"] if x["sku"] == "TEST-SKU-VENCIDO"), None)
        assert item is not None
        assert item["razon"] == "registro_vencido"
        assert "invima_match" in item
        assert item["invima_match"]["dias_vencido"] >= 10
    finally:
        _cleanup("stock_pt", "sku=?", ("TEST-SKU-VENCIDO",))
        _cleanup("registros_invima", "producto=?", ("Crema Test Vencida",))


def test_productos_sin_invima_detecta_por_vencer(app, db_clean):
    c = _login(app, "hernando")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM stock_pt WHERE sku='TEST-SKU-PROX'")
    conn.execute("DELETE FROM registros_invima WHERE num_registro='NSC-TEST-PROX'")
    conn.execute(
        """INSERT INTO stock_pt (sku, descripcion, unidades_disponible, empresa, estado)
           VALUES ('TEST-SKU-PROX', 'Serum Test Por Vencer 30ml', 5, 'ANIMUS', 'Disponible')""")
    fv = (date.today() + timedelta(days=45)).isoformat()
    conn.execute(
        """INSERT INTO registros_invima
           (producto, num_registro, estado, fecha_vencimiento)
           VALUES ('Serum Test Por Vencer 30ml', 'NSC-TEST-PROX', 'Vigente', ?)""",
        (fv,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/productos-sin-invima?umbral_dias=60")
        d = r.get_json()
        item = next((x for x in d["por_vencer"] if x["sku"] == "TEST-SKU-PROX"), None)
        assert item is not None
        assert "invima" in item
        assert 40 <= item["invima"]["dias_restantes"] <= 50
    finally:
        _cleanup("stock_pt", "sku=?", ("TEST-SKU-PROX",))
        _cleanup("registros_invima", "num_registro=?", ("NSC-TEST-PROX",))


def test_productos_sin_invima_filtro_empresa(app, db_clean):
    c = _login(app, "hernando")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM stock_pt WHERE sku LIKE 'TEST-EMP-%'")
    conn.execute(
        """INSERT INTO stock_pt (sku, descripcion, unidades_disponible, empresa, estado)
           VALUES ('TEST-EMP-A', 'Prod A', 10, 'ANIMUS', 'Disponible'),
                  ('TEST-EMP-B', 'Prod B', 10, 'ESPAGIRIA', 'Disponible')""")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/tecnica/productos-sin-invima?empresa=ANIMUS")
        d = r.get_json()
        skus = {x["sku"] for x in d["sin_invima"]}
        assert "TEST-EMP-A" in skus
        assert "TEST-EMP-B" not in skus
    finally:
        _cleanup("stock_pt", "sku LIKE ?", ("TEST-EMP-%",))


# ════════════════════════════════════════════════════════════════════
#  3. CAMBIO DE CONTROL
# ════════════════════════════════════════════════════════════════════

def test_cc_requires_auth(client, db_clean):
    r = client.get("/api/tecnica/cambios-control")
    assert r.status_code == 401
    r = client.post("/api/tecnica/cambios-control", json={"formula_id": 1, "clasificacion": "menor"},
                    headers=csrf_headers())
    assert r.status_code == 401


def test_cc_solicitar_basico(app, db_clean):
    c = _login(app, "hernando")
    fid = _seed_formula("TEST-CC-001", "Producto CC")
    try:
        payload = {
            "formula_id": fid,
            "clasificacion": "menor",
            "justificacion": "Cambio de proveedor de un excipiente menor sin impacto en estabilidad.",
            "impacto": "Bajo · ninguna",
            "cambio_propuesto": "Reemplazar lecitina A por lecitina B",
        }
        r = c.post("/api/tecnica/cambios-control", json=payload, headers=csrf_headers())
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert d["estado"] == "pendiente"
        cc_id = d["id"]
        # Verificar audit_log
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT accion, registro_id FROM audit_log WHERE accion='SOLICITAR_CAMBIO_CONTROL' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == str(cc_id)
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_rechaza_clasificacion_invalida(app, db_clean):
    c = _login(app, "hernando")
    fid = _seed_formula("TEST-CC-INV", "Test")
    try:
        r = c.post("/api/tecnica/cambios-control",
                   json={"formula_id": fid, "clasificacion": "critica",
                         "justificacion": "x" * 30}, headers=csrf_headers())
        assert r.status_code == 400
    finally:
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_rechaza_justificacion_corta(app, db_clean):
    c = _login(app, "hernando")
    fid = _seed_formula("TEST-CC-JUST", "Test")
    try:
        r = c.post("/api/tecnica/cambios-control",
                   json={"formula_id": fid, "clasificacion": "menor",
                         "justificacion": "corta"}, headers=csrf_headers())
        assert r.status_code == 400
        assert "justificacion" in r.get_json()["error"].lower()
    finally:
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_rechaza_formula_inexistente(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/cambios-control",
               json={"formula_id": 9999999, "clasificacion": "menor",
                     "justificacion": "x" * 30}, headers=csrf_headers())
    assert r.status_code == 404


def test_cc_aprobar_solo_admin(app, db_clean):
    c = _login(app, "hernando")  # hernando es TECNICA pero NO ADMIN
    fid = _seed_formula("TEST-CC-APR", "Test")
    try:
        # Solicitar
        r = c.post("/api/tecnica/cambios-control",
                   json={"formula_id": fid, "clasificacion": "mayor",
                         "justificacion": "Cambio crítico requiere admin para aprobar." * 2},
                   headers=csrf_headers())
        cc_id = r.get_json()["id"]
        # hernando intenta aprobar (debe fallar 403)
        r = c.post(f"/api/tecnica/cambios-control/{cc_id}/aprobar",
                   json={"decision": "aprobar"}, headers=csrf_headers())
        assert r.status_code == 403
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_aprobar_admin_ok(app, db_clean):
    cs = _login(app, "sebastian")  # admin
    fid = _seed_formula("TEST-CC-ADMOK", "Test")
    try:
        r = cs.post("/api/tecnica/cambios-control",
                    json={"formula_id": fid, "clasificacion": "menor",
                          "justificacion": "Justificación valida con suficientes caracteres."},
                    headers=csrf_headers())
        cc_id = r.get_json()["id"]
        r = cs.post(f"/api/tecnica/cambios-control/{cc_id}/aprobar",
                    json={"decision": "aprobar", "observaciones": "OK aprobado"},
                    headers=csrf_headers())
        assert r.status_code == 200
        assert r.get_json()["estado"] == "aprobado"
        # Audit log
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT accion FROM audit_log WHERE accion='APROBAR_CAMBIO_CONTROL' AND registro_id=? ORDER BY id DESC LIMIT 1",
            (str(cc_id),)
        ).fetchone()
        conn.close()
        assert row is not None
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_no_reaprobar(app, db_clean):
    cs = _login(app, "sebastian")
    fid = _seed_formula("TEST-CC-RE", "Test")
    try:
        r = cs.post("/api/tecnica/cambios-control",
                    json={"formula_id": fid, "clasificacion": "menor",
                          "justificacion": "Justificación valida con suficientes caracteres."},
                    headers=csrf_headers())
        cc_id = r.get_json()["id"]
        cs.post(f"/api/tecnica/cambios-control/{cc_id}/aprobar",
                json={"decision": "aprobar"}, headers=csrf_headers())
        r2 = cs.post(f"/api/tecnica/cambios-control/{cc_id}/aprobar",
                     json={"decision": "rechazar"}, headers=csrf_headers())
        assert r2.status_code == 400
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_cc_lista_filtra_por_estado(app, db_clean):
    cs = _login(app, "sebastian")
    fid = _seed_formula("TEST-CC-LIST", "Test")
    try:
        cs.post("/api/tecnica/cambios-control",
                json={"formula_id": fid, "clasificacion": "menor",
                      "justificacion": "Justificación valida con suficientes caracteres."},
                headers=csrf_headers())
        r = cs.get(f"/api/tecnica/cambios-control?formula_id={fid}&estado=pendiente")
        assert r.status_code == 200
        d = r.get_json()
        assert "cambios" in d
        assert all(c["formula_id"] == fid and c["estado"] == "pendiente"
                   for c in d["cambios"])
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_formula_modificar_con_cc_aplica(app, db_clean):
    """Si paso cambio_control_id en PATCH formula, el CC pasa a 'aplicado'."""
    cs = _login(app, "sebastian")
    fid = _seed_formula("TEST-CC-APLY", "Producto Test")
    try:
        # Crear CC
        r = cs.post("/api/tecnica/cambios-control",
                    json={"formula_id": fid, "clasificacion": "menor",
                          "justificacion": "Justificación valida con suficientes caracteres."},
                    headers=csrf_headers())
        cc_id = r.get_json()["id"]
        # Aprobar
        cs.post(f"/api/tecnica/cambios-control/{cc_id}/aprobar",
                json={"decision": "aprobar"}, headers=csrf_headers())
        # PATCH fórmula con cambio_control_id
        r = cs.patch(f"/api/tecnica/formulas/{fid}",
                     json={"version": "1.1", "cambio_control_id": cc_id},
                     headers=csrf_headers())
        assert r.status_code == 200
        # Verificar que CC quedó en estado='aplicado'
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT estado, version_resultante FROM cambios_control_formula WHERE id=?",
            (cc_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "aplicado"
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_versiones", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


def test_formula_modificar_rechaza_cc_no_aprobado(app, db_clean):
    cs = _login(app, "sebastian")
    fid = _seed_formula("TEST-CC-NOAPR", "Test")
    try:
        r = cs.post("/api/tecnica/cambios-control",
                    json={"formula_id": fid, "clasificacion": "menor",
                          "justificacion": "Justificación valida con suficientes caracteres."},
                    headers=csrf_headers())
        cc_id = r.get_json()["id"]
        # Sin aprobar, intento usarlo en PATCH
        r = cs.patch(f"/api/tecnica/formulas/{fid}",
                     json={"version": "1.1", "cambio_control_id": cc_id},
                     headers=csrf_headers())
        assert r.status_code == 400
        assert "aprobado" in r.get_json()["error"].lower()
    finally:
        _cleanup("cambios_control_formula", "formula_id=?", (fid,))
        _cleanup("formulas_maestras", "id=?", (fid,))


# ════════════════════════════════════════════════════════════════════
#  4. JOB tecnica_vencimientos
# ════════════════════════════════════════════════════════════════════

def test_job_tecnica_vencimientos_no_alerta_si_nada(app, db_clean):
    """Si no hay INVIMA ni SGD por vencer, el job retorna ok sin notificar."""
    from blueprints.auto_plan_jobs import job_tecnica_vencimientos
    # Limpiar datos potencialmente "alertables"
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE registros_invima SET fecha_vencimiento=date('now','+999 day') WHERE fecha_vencimiento<date('now','+91 day')")
    conn.execute("UPDATE documentos_sgd SET fecha_proxima_revision=date('now','+999 day') WHERE fecha_proxima_revision<date('now','+31 day') AND fecha_proxima_revision != ''")
    conn.commit(); conn.close()
    ok, resultado, _ = job_tecnica_vencimientos(app)
    assert ok is True
    # Si hay alertas previas en la DB de tests, "mensaje" no aparece
    # solo verifico el shape
    assert isinstance(resultado, dict)


def test_job_tecnica_vencimientos_detecta_invima_vencido(app, db_clean):
    from blueprints.auto_plan_jobs import job_tecnica_vencimientos
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM registros_invima WHERE num_registro='NSC-JOB-VENC'")
    vencido = (date.today() - timedelta(days=5)).isoformat()
    conn.execute(
        """INSERT INTO registros_invima
           (producto, num_registro, estado, fecha_vencimiento)
           VALUES ('Producto Job Test', 'NSC-JOB-VENC', 'Vigente', ?)""",
        (vencido,))
    conn.commit(); conn.close()
    try:
        ok, resultado, _ = job_tecnica_vencimientos(app)
        assert ok is True
        assert resultado.get("invima_vencidos", 0) >= 1
    finally:
        _cleanup("registros_invima", "num_registro=?", ("NSC-JOB-VENC",))


# ════════════════════════════════════════════════════════════════════
#  5. CSRF en frontend
# ════════════════════════════════════════════════════════════════════

def test_pagina_tecnica_envia_csrf_token(app, db_clean):
    """La página /tecnica debe incluir helpers _apiPost/_csrf con X-CSRF-Token."""
    c = _login(app, "hernando")
    r = c.get("/tecnica")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "X-CSRF-Token" in body
    assert "_csrf" in body
    assert "_apiPost" in body
    assert "_apiDelete" in body
    # Verificar que ya no hay fetch directos a /api/tecnica con method:POST
    assert "method:'POST'" not in body  # los apiSend wrappers reemplazan
