"""Tests del workflow de Recall (ASG-PRO-004)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(rid_or_codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    if isinstance(rid_or_codigo, int):
        conn.execute("DELETE FROM recalls_eventos WHERE recall_id=?", (rid_or_codigo,))
        conn.execute("DELETE FROM recalls WHERE id=?", (rid_or_codigo,))
    else:
        row = conn.execute("SELECT id FROM recalls WHERE codigo=?", (rid_or_codigo,)).fetchone()
        if row:
            conn.execute("DELETE FROM recalls_eventos WHERE recall_id=?", (row[0],))
            conn.execute("DELETE FROM recalls WHERE id=?", (row[0],))
    conn.commit(); conn.close()


def test_recalls_listar_estructura(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/recalls")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "kpis" in data
    for k in ["total","sin_clasificar","clase_I_abiertos","invima_pendiente","en_recoleccion","cerrados_30d"]:
        assert k in data["kpis"]


def test_recalls_iniciar_solo_calidad(app, db_clean):
    """luis (no Calidad/Admin) NO puede iniciar recall."""
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "SAH-30ml",
                     "lotes_afectados": "LOTE-2026-001",
                     "motivo": "Defecto detectado en envase con riesgo de contaminación"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_recalls_iniciar_codigo_auto(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"origen": "queja_cliente",
                     "origen_referencia": "QC-2026-0010",
                     "producto": "SAH-30ml",
                     "lotes_afectados": "LOTE-2026-005",
                     "cantidad_fabricada": 5000,
                     "cantidad_distribuida": 4200,
                     "motivo": "Múltiples reportes de envase con defecto en tapa que puede contaminar producto"},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "RCL-" in data["codigo"]
    _cleanup(data["id"])


def test_recalls_motivo_corto_400(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "X", "lotes_afectados": "L1", "motivo": "corto"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_recalls_workflow_completo(app, db_clean):
    """iniciado → clasificado → invima → distribuidores → recolección → completado → cerrado."""
    c = _login(app, "laura")

    # 1. Iniciar
    r = c.post("/api/aseguramiento/recalls",
               json={"origen": "hallazgo_interno",
                     "producto": "TRX-50ml",
                     "lotes_afectados": "LOTE-2026-007",
                     "cantidad_fabricada": 2000,
                     "cantidad_distribuida": 1800,
                     "motivo": "Análisis post-distribución detectó OOS en pH del lote 007"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]

    # 2. Clasificar
    r = c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
               json={"clase_recall": "clase_II",
                     "alcance_geografico": "nacional",
                     "justificacion_clasificacion": "OOS en pH puede causar irritación leve, riesgo temporal y reversible"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 3. Notificar INVIMA
    r = c.post(f"/api/aseguramiento/recalls/{rid}/notificar-invima",
               json={"referencia": "INVIMA-2026-RCL-001"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 4. Notificar distribuidores
    r = c.post(f"/api/aseguramiento/recalls/{rid}/notificar-distribuidores",
               json={"distribuidores_notificados": "Distribuidor Nacional A, Cadena Retail B, E-commerce propio"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 5. Registrar recolección parcial
    r = c.post(f"/api/aseguramiento/recalls/{rid}/recoleccion",
               json={"cantidad_recolectada": 1200, "completa": False},
               headers=csrf_headers())
    assert r.status_code == 200

    # 6. Marcar recolección completa
    r = c.post(f"/api/aseguramiento/recalls/{rid}/recoleccion",
               json={"cantidad_recolectada": 1700, "completa": True},
               headers=csrf_headers())
    assert r.status_code == 200

    # 7. Cerrar con disposición + efectividad
    r = c.post(f"/api/aseguramiento/recalls/{rid}/cerrar",
               json={"disposicion_final": "destruccion",
                     "disposicion_descripcion": "Destrucción certificada del producto recolectado en gestor autorizado",
                     "efectividad_porcentaje": 94,
                     "efectividad_descripcion": "1700/1800 distribuido recolectado, 100 unidades dadas por perdidas",
                     "observaciones_cierre": "Recall efectivo · proceso revisado"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar estado final
    r = c.get(f"/api/aseguramiento/recalls/{rid}")
    data = r.get_json()
    assert data["estado"] == "cerrado"
    assert data["clase_recall"] == "clase_II"
    assert data["disposicion_final"] == "destruccion"
    assert data["efectividad_porcentaje"] == 94
    assert data["cantidad_recolectada"] == 1700
    # 7 transiciones: iniciado, clasificado, invima, distribuidores, recolección parcial, completa, cerrado
    assert len(data["timeline"]) >= 7

    _cleanup(codigo)


def test_recalls_clase_invalida_400(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-X", "lotes_afectados": "L1",
                     "motivo": "Motivo suficientemente largo para crear recall"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    r = c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
               json={"clase_recall": "clase_IV",
                     "alcance_geografico": "nacional",
                     "justificacion_clasificacion": "x"*25},
               headers=csrf_headers())
    assert r.status_code == 400
    _cleanup(rid)


def test_recalls_no_invima_sin_clasificar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-X", "lotes_afectados": "L1",
                     "motivo": "Motivo suficientemente largo para crear recall"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    # Intentar notificar INVIMA sin clasificar primero
    r = c.post(f"/api/aseguramiento/recalls/{rid}/notificar-invima",
               json={"referencia": "X-123"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup(rid)


def test_recalls_no_cerrar_sin_completar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-X", "lotes_afectados": "L1",
                     "motivo": "Motivo suficientemente largo para crear recall"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    # Intentar cerrar directo
    r = c.post(f"/api/aseguramiento/recalls/{rid}/cerrar",
               json={"disposicion_final": "destruccion",
                     "disposicion_descripcion": "Descripción suficiente para cerrar recall"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup(rid)


def test_recalls_efectividad_porcentaje_invalido(app, db_clean):
    """efectividad_porcentaje fuera de 0-100 → 400."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-X", "lotes_afectados": "L1",
                     "motivo": "Motivo suficientemente largo para crear recall"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    # Avanzar al estado completado primero
    c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
           json={"clase_recall":"clase_III","alcance_geografico":"local",
                 "justificacion_clasificacion":"x"*25}, headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/notificar-invima",
           json={"referencia":"X"}, headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/notificar-distribuidores",
           json={"distribuidores_notificados":"Dist1"}, headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/recoleccion",
           json={"cantidad_recolectada":100,"completa":True}, headers=csrf_headers())
    # Ahora intentar cerrar con efectividad inválida
    r = c.post(f"/api/aseguramiento/recalls/{rid}/cerrar",
               json={"disposicion_final": "destruccion",
                     "disposicion_descripcion": "Descripción suficiente para cerrar recall",
                     "efectividad_porcentaje": 150},
               headers=csrf_headers())
    assert r.status_code == 400
    _cleanup(rid)


def test_recalls_codigo_secuencial(app, db_clean):
    c = _login(app, "laura")
    codigos = []
    ids = []
    for i in range(3):
        r = c.post("/api/aseguramiento/recalls",
                   json={"producto": f"PROD-{i+1}",
                         "lotes_afectados": f"LOTE-{i+1}",
                         "motivo": f"Recall secuencial número {i+1} suficientemente descrito"},
                   headers=csrf_headers())
        codigos.append(r.get_json()["codigo"])
        ids.append(r.get_json()["id"])
    assert len(set(codigos)) == 3
    for cod in codigos:
        assert cod.startswith("RCL-")
        parts = cod.split("-")
        assert len(parts) == 3
    for rid in ids:
        _cleanup(rid)


def test_recalls_endpoints_requieren_auth(client, db_clean):
    for path in ["/api/aseguramiento/recalls"]:
        r = client.get(path)
        assert r.status_code == 401
