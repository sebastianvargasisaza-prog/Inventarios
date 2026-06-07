"""Controles en Proceso ESTÁNDAR + opción 'No aplica' · mig 225 · 6-jun-2026.

La sección 6 (Controles en Proceso) muestra SIEMPRE un set estándar (Densidad,
pH, Olor, Color, Apariencia) aunque el MBR no los defina, y cada control se
puede registrar con valor / Cumple / No cumple, o marcar 'No aplica' (conforme=2).
"""
import pytest


def _crear_ebr(app, lote="LOTE-IPC-EST-1"):
    """Crea un MBR + EBR mínimos en estado 'iniciado'. Devuelve ebr_id."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO mbr_templates (producto_nombre, version, estado,
                 lote_size_g, creado_por) VALUES (?, 1, 'aprobado',
                 1000, 'sebastian')""", (f"PROD-IPC-EST-{lote}",))
        mbr_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote,
                 estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, fase)
               VALUES (?,1,?,'iniciado','sebastian','2026-06-06 10:00:00',1000,'fabricacion')""",
            (mbr_id, lote))
        ebr_id = cur.lastrowid
        conn.commit()
        return ebr_id


def test_get_estandar_devuelve_5_controles(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-IPC-EST-GET")
    r = admin_client.get(f"/api/brd/ebr/{ebr}/ipc-estandar")
    assert r.status_code == 200
    items = r.get_json()["items"]
    cods = {i["control_codigo"] for i in items}
    assert cods == {"densidad", "ph", "olor", "color", "apariencia"}
    # Todos pendientes (conforme None) al inicio
    assert all(i["conforme"] is None for i in items)


def test_no_aplica_guarda_conforme_2(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-IPC-EST-NA")
    r = admin_client.post(f"/api/brd/ebr/{ebr}/ipc-estandar",
                          json={"control_codigo": "olor", "no_aplica": True})
    assert r.status_code == 200
    assert r.get_json()["conforme"] == 2
    assert r.get_json()["estado"] == "No aplica"
    # GET lo refleja
    items = admin_client.get(f"/api/brd/ebr/{ebr}/ipc-estandar").get_json()["items"]
    olor = next(i for i in items if i["control_codigo"] == "olor")
    assert olor["conforme"] == 2


def test_registrar_cumple_y_upsert(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-IPC-EST-CUMPLE")
    r = admin_client.post(f"/api/brd/ebr/{ebr}/ipc-estandar",
                          json={"control_codigo": "densidad", "conforme": True,
                                "valor_texto": "1,056 g/mL"})
    assert r.status_code == 200
    assert r.get_json()["conforme"] == 1
    # Upsert: re-registrar el mismo control no duplica ni falla
    r2 = admin_client.post(f"/api/brd/ebr/{ebr}/ipc-estandar",
                           json={"control_codigo": "densidad", "no_aplica": True})
    assert r2.status_code == 200
    items = admin_client.get(f"/api/brd/ebr/{ebr}/ipc-estandar").get_json()["items"]
    dens = [i for i in items if i["control_codigo"] == "densidad"]
    assert len(dens) == 1 and dens[0]["conforme"] == 2  # quedó el último (No aplica)


def test_vista_completa_incluye_controles_estandar(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-IPC-EST-VC")
    d = admin_client.get(f"/api/brd/ebr/{ebr}/vista-completa").get_json()
    controles = {c["control"] for c in d.get("ipc", [])}
    # MBR sin specs → deben aparecer los 5 estándar igualmente
    assert "Densidad a 25°C" in controles
    assert "pH a 25°C" in controles
    assert "Apariencia" in controles
    # Cada estándar trae tipo y codigo para el registro
    est = [c for c in d["ipc"] if c.get("tipo") == "estandar"]
    assert len(est) == 5


def test_operacion_vivo_direccion_tecnica(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-OPVIVO")
    r = admin_client.get("/api/tecnica/operacion-vivo")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert "areas" in d and "resumen_areas" in d
    # El EBR iniciado debe aparecer en el resumen de lotes
    lotes = {b["lote"] for b in d["batches"]}
    assert "LOTE-OPVIVO" in lotes


def test_control_codigo_invalido_rechaza(admin_client, app):
    ebr = _crear_ebr(app, "LOTE-IPC-EST-BAD")
    r = admin_client.post(f"/api/brd/ebr/{ebr}/ipc-estandar",
                          json={"control_codigo": "inexistente", "no_aplica": True})
    assert r.status_code == 400
