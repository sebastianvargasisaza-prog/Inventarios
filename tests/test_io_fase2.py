"""Inteligencia Operacional · Fase 2 (admin.py).

Lead time de compras (ordenes_compra + solicitudes_compra) + productividad por operario
(produccion_programada · operario_*_id + etapa_*). READ-ONLY admin. Días/min en Python (M24).
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


def test_lead_time_compras(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM ordenes_compra WHERE numero_oc='OC-LT-1'")
    conn.execute("DELETE FROM solicitudes_compra WHERE numero_oc='OC-LT-1'")
    # SOL 06-01 → OC 06-03 (2d) → autoriz 06-05 (2d) → pago 06-06 (1d) → recep 06-10 (4d) · total 9d
    conn.execute("INSERT INTO solicitudes_compra (numero, fecha, numero_oc, categoria, estado) "
                 "VALUES ('SOL-LT-1','2026-06-01','OC-LT-1','Materia Prima','Convertida')")
    conn.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                 "fecha_autorizacion, fecha_pago, fecha_recepcion) VALUES "
                 "('OC-LT-1','Prov LT','Recibida','Materia Prima','2026-06-03','2026-06-05','2026-06-06','2026-06-10')")
    conn.commit(); conn.close()
    c = _login(app)
    r = c.get("/api/admin/io/lead-time-compras?desde=2026-06-01&hasta=2026-06-30")
    assert r.status_code == 200, r.data
    j = r.get_json()
    it = next((x for x in j["items"] if x["numero_oc"] == "OC-LT-1"), None)
    assert it is not None
    assert it["sol_oc_d"] == 2 and it["oc_aut_d"] == 2
    assert it["aut_pago_d"] == 1 and it["pago_rec_d"] == 4
    assert it["total_d"] == 9


def test_productividad_operario(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='ZZ PROD OP'")
    conn.execute("DELETE FROM operarios_planta WHERE nombre='ZOPER'")
    cur = conn.execute("INSERT INTO operarios_planta (nombre, apellido) VALUES ('ZOPER','Uno')")
    oid = cur.lastrowid
    # 1 lote: ZOPER hace elaboración (2h) y envasado (1h)
    conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, estado, inicio_real_at, fin_real_at,
         operario_elaboracion_id, etapa_elab_inicio_at, etapa_elab_fin_at,
         operario_envasado_id, etapa_env_inicio_at, etapa_env_fin_at)
        VALUES ('ZZ PROD OP','2026-06-20','completado','2026-06-20 08:00:00','2026-06-20 13:00:00',
         ?, '2026-06-20 08:00:00','2026-06-20 10:00:00', ?, '2026-06-20 10:00:00','2026-06-20 11:00:00')""",
                 (oid, oid))
    conn.commit(); conn.close()
    c = _login(app)
    r = c.get("/api/admin/io/productividad-operario?desde=2026-06-20&hasta=2026-06-20")
    assert r.status_code == 200, r.data
    it = next((x for x in r.get_json()["items"] if x["operario"] == "ZOPER Uno"), None)
    assert it is not None
    assert it["n_lotes"] == 1 and it["n_tareas"] == 2
    assert it["total_min"] == 180          # 2h + 1h
    assert it["por_fase"]["Elaboración"] == 120 and it["por_fase"]["Envasado"] == 60


def test_io_fase2_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")
    assert c.get("/api/admin/io/lead-time-compras").status_code in (401, 403)
    assert c.get("/api/admin/io/productividad-operario").status_code in (401, 403)
