"""Tests Compras: Pre-Sprint + Sprints 1-5."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


# ═══ Pre-Sprint: por-pagar ════════════════════════════════════════════════


def test_por_pagar_endpoint_works(app, db_clean):
    c = _login(app, "catalina")
    r = c.get("/api/compras/por-pagar")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("items", "count", "total_valor", "desglose"):
        assert key in data
    assert "pagos_directos_servicios" in data["desglose"]
    assert "mercancia_recibida" in data["desglose"]


def test_por_pagar_includes_influencer_oc(app, db_clean):
    """OCs en estado Aprobada con categoría Influencer deben aparecer."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, categoria, valor_total)
                    VALUES ('OC-TEST-INF', date('now'), 'Aprobada', 'Influencer X',
                            'Influencer/Marketing Digital', 500000)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    r = c.get("/api/compras/por-pagar")
    items = r.get_json()["items"]
    nums = [i["numero_oc"] for i in items]
    assert "OC-TEST-INF" in nums
    inf_item = next(i for i in items if i["numero_oc"] == "OC-TEST-INF")
    assert inf_item["pago_directo"] is True


# ═══ Sprint 1: permisos + bug first_oc ════════════════════════════════════


def test_compras_write_blocked_for_marketing(app, db_clean):
    """Felipe (Marketing) NO debe poder editar OCs."""
    c = _login(app, "felipe")
    r = c.put("/api/ordenes-compra/OC-NO-EXISTE",
              json={"estado": "Aprobada"}, headers=csrf_headers())
    assert r.status_code == 403


def test_compras_write_allowed_for_catalina(app, db_clean):
    """Catalina (Asist. Compras) SÍ puede."""
    c = _login(app, "catalina")
    r = c.put("/api/ordenes-compra/OC-NO-EXISTE",
              json={"estado": "Aprobada"}, headers=csrf_headers())
    # No 403; será 200 o 404 dependiendo si la OC existe
    assert r.status_code != 403


def test_autorizar_oc_blocked_for_marketing(app, db_clean):
    c = _login(app, "jefferson")
    r = c.patch("/api/ordenes-compra/OC-X/autorizar", headers=csrf_headers())
    assert r.status_code == 403


# ═══ Sprint 2: pagos_oc + historial + 3-way matching ══════════════════════


def test_pagos_oc_endpoint_exists(app, db_clean):
    c = _login(app, "catalina")
    # Para OC inexistente → respuesta vacía (no 404), porque tabla puede tener registros
    r = c.get("/api/ordenes-compra/OC-NO-EXISTE/pagos")
    assert r.status_code == 200
    data = r.get_json()
    assert "pagos" in data and "total_pagado" in data


def test_pagar_oc_registra_en_pagos_oc(app, db_clean):
    """Pagar registra fila en pagos_oc, no solo sobrescribe ordenes_compra."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-PAY-1', date('now'), 'Recibida', 'Prov X', 1000000)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    r = c.patch("/api/ordenes-compra/OC-PAY-1/pagar",
                json={"monto": 1000000, "medio": "Transferencia",
                      "numero_factura_proveedor": "FAC-12345"},
                headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["estado"] == "Pagada"
    assert data["monto_este_pago"] == 1000000

    # Verificar que la fila está en pagos_oc
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute("SELECT monto, numero_factura_proveedor FROM pagos_oc WHERE numero_oc='OC-PAY-1'").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == 1000000
    assert rows[0][1] == "FAC-12345"


def test_pago_parcial_estado_correcto(app, db_clean):
    """Pago parcial deja OC en estado 'Parcial', no 'Pagada'."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-PAR-1', date('now'), 'Recibida', 'Prov Y', 2000000)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    r = c.patch("/api/ordenes-compra/OC-PAR-1/pagar",
                json={"monto": 800000, "numero_factura_proveedor": "FAC-PARCIAL-1"},
                headers=csrf_headers())
    data = r.get_json()
    assert data["estado"] == "Parcial"
    assert data["pendiente"] == 1200000


def test_factura_duplicada_rechazada(app, db_clean):
    """3-way matching: misma factura en 2 OCs → 409."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-DUP-1', date('now'), 'Recibida', 'P', 100)""")
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-DUP-2', date('now'), 'Recibida', 'P', 100)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    # Primer pago con factura: OK
    r = c.patch("/api/ordenes-compra/OC-DUP-1/pagar",
                json={"monto": 100, "numero_factura_proveedor": "FAC-UNICA"},
                headers=csrf_headers())
    assert r.status_code == 200
    # Segundo pago con MISMA factura en OC distinta: 409
    r = c.patch("/api/ordenes-compra/OC-DUP-2/pagar",
                json={"monto": 100, "numero_factura_proveedor": "FAC-UNICA"},
                headers=csrf_headers())
    assert r.status_code == 409
    assert r.get_json().get("codigo") == "FACTURA_DUPLICADA"


# ═══ Sprint 3: alertas vivas ══════════════════════════════════════════════


def test_alertas_vivas_compras_endpoint(app, db_clean):
    c = _login(app, "catalina")
    r = c.get("/api/compras/alertas-vivas")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("ocs_sin_recibir", "pagos_por_vencer", "solicitudes_pendientes",
                "ocs_borrador_estancadas", "total", "severidad_max"):
        assert key in data


def test_alertas_vivas_requires_auth(client, db_clean):
    r = client.get("/api/compras/alertas-vivas")
    assert r.status_code == 401


# ═══ Sprint 4: aprobación por monto + reporte ejecutivo ═══════════════════


def test_reporte_ejecutivo_endpoint(app, db_clean):
    c = _login(app, "catalina")
    r = c.get("/api/compras/reporte-ejecutivo")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("top_proveedores", "gasto_categoria_mes",
                "pasivo_corriente", "variaciones_precio", "mes_actual"):
        assert key in data


def test_limite_aprobacion_admin_sin_limite(app, db_clean):
    """Admin (sebastian) puede autorizar montos enormes."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-BIG', date('now'), 'Revisada', 'Prov', 999999999)""")
    conn.commit()
    conn.close()

    c = _login(app, "sebastian")
    r = c.patch("/api/ordenes-compra/OC-BIG/autorizar", headers=csrf_headers())
    assert r.status_code != 403


def test_limite_aprobacion_catalina_no_excede(app, db_clean):
    """Catalina (límite 5M) NO puede autorizar OC de 10M."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-EXCEDE', date('now'), 'Revisada', 'P', 10_000_000)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    r = c.patch("/api/ordenes-compra/OC-EXCEDE/autorizar", headers=csrf_headers())
    assert r.status_code == 403
    assert r.get_json().get("codigo") == "EXCEDE_LIMITE_APROBACION"


def test_limite_aprobacion_catalina_dentro(app, db_clean):
    """Catalina puede autorizar OC dentro de su límite (5M)."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO ordenes_compra
                    (numero_oc, fecha, estado, proveedor, valor_total)
                    VALUES ('OC-OK', date('now'), 'Revisada', 'P', 3_000_000)""")
    conn.commit()
    conn.close()

    c = _login(app, "catalina")
    r = c.patch("/api/ordenes-compra/OC-OK/autorizar", headers=csrf_headers())
    assert r.status_code != 403


# ═══ Sprint 5: cotizaciones + centro de costos ════════════════════════════


def test_crear_ronda_cotizaciones(app, db_clean):
    c = _login(app, "catalina")
    r = c.post("/api/compras/cotizaciones/rondas",
               json={"descripcion": "Compra MP cera de abeja",
                     "proveedores": [
                         {"nombre": "Prov A", "tiempo_entrega_dias": 7},
                         {"nombre": "Prov B", "tiempo_entrega_dias": 10},
                         {"nombre": "Prov C", "tiempo_entrega_dias": 5},
                     ]},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert data["count"] == 3
    assert data["ronda_id"].startswith("COT-")


def test_ronda_minimo_2_proveedores(app, db_clean):
    c = _login(app, "catalina")
    r = c.post("/api/compras/cotizaciones/rondas",
               json={"descripcion": "Solo uno", "proveedores": [{"nombre": "P"}]},
               headers=csrf_headers())
    assert r.status_code == 400


def test_actualizar_cotizacion_y_elegir_ganadora(app, db_clean):
    c = _login(app, "catalina")
    # Crear ronda
    r = c.post("/api/compras/cotizaciones/rondas",
               json={"descripcion": "Test", "proveedores": [
                   {"nombre": "A"}, {"nombre": "B"}]},
               headers=csrf_headers())
    cot_a_id = r.get_json()["cotizaciones"][0]["id"]
    cot_b_id = r.get_json()["cotizaciones"][1]["id"]
    ronda_id = r.get_json()["ronda_id"]

    # Actualizar valores
    c.patch(f"/api/compras/cotizaciones/{cot_a_id}",
            json={"valor_total": 1_500_000}, headers=csrf_headers())
    c.patch(f"/api/compras/cotizaciones/{cot_b_id}",
            json={"valor_total": 1_200_000}, headers=csrf_headers())

    # Elegir B (más barata) como ganadora
    r = c.post(f"/api/compras/cotizaciones/{cot_b_id}/elegir-ganadora",
               json={"numero_oc": "OC-FROM-COT"}, headers=csrf_headers())
    assert r.status_code == 200

    # Verificar estado
    r = c.get(f"/api/compras/cotizaciones/rondas/{ronda_id}")
    cots = r.get_json()["cotizaciones"]
    cot_b = next(c for c in cots if c["id"] == cot_b_id)
    cot_a = next(c for c in cots if c["id"] == cot_a_id)
    assert cot_b["ganadora"] == 1
    assert cot_b["estado"] == "Ganadora"
    assert cot_a["estado"] == "No seleccionada"


def test_centros_costos_endpoint(app, db_clean):
    c = _login(app, "catalina")
    r = c.get("/api/compras/centros-costos")
    assert r.status_code == 200
    data = r.get_json()
    assert "centros" in data
    assert isinstance(data["centros"], list)
