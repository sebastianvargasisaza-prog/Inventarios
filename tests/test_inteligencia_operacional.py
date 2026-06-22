"""Inteligencia Operacional · Fase 1 (admin.py).

READ-ONLY: inicio de labores (security_events.login_success) + tiempos de producción
por fase (produccion_programada). Duraciones en Python (M24). Gerencia (admin).
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


def test_inicio_labores_primera_hora_por_dia(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM security_events WHERE username='zoperario'")
    # 2 logins el mismo día Colombia (UTC: 13:30 y 15:00 → Colombia 08:30 y 10:00)
    conn.execute("INSERT INTO security_events (ts, event, username, ip) VALUES "
                 "('2026-06-20T13:30:00Z','login_success','zoperario','1.1.1.1')")
    conn.execute("INSERT INTO security_events (ts, event, username, ip) VALUES "
                 "('2026-06-20T15:00:00Z','login_success','zoperario','1.1.1.1')")
    conn.commit(); conn.close()
    c = _login(app)
    r = c.get("/api/admin/io/inicio-labores?desde=2026-06-20&hasta=2026-06-20")
    assert r.status_code == 200, r.data
    item = next((x for x in r.get_json()["items"] if x["usuario"] == "zoperario"), None)
    assert item is not None
    assert item["inicio"] == "08:30"   # primera hora del día (Colombia)
    assert item["ultima"] == "10:00"
    assert item["n_logins"] == 2


def test_tiempos_produccion_calcula_fases(app, db_clean):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='ZZ IO TEST'")
    # fabricación con marcas de fase: disp 30m, elab 120m, env 60m, acond 45m; total 5h
    conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, estado, origen, cantidad_kg, kg_real, unidades_real, merma_pct,
         inicio_real_at, fin_real_at,
         etapa_disp_inicio_at, etapa_disp_fin_at, etapa_elab_inicio_at, etapa_elab_fin_at,
         etapa_env_inicio_at, etapa_env_fin_at, etapa_acond_inicio_at, etapa_acond_fin_at)
        VALUES ('ZZ IO TEST','2026-06-20','completado','eos_plan',10,10,1000,2.0,
         '2026-06-20 08:00:00','2026-06-20 13:00:00',
         '2026-06-20 08:00:00','2026-06-20 08:30:00','2026-06-20 08:30:00','2026-06-20 10:30:00',
         '2026-06-20 10:30:00','2026-06-20 11:30:00','2026-06-20 11:30:00','2026-06-20 12:15:00')""")
    conn.commit(); conn.close()
    c = _login(app)
    r = c.get("/api/admin/io/tiempos-produccion?desde=2026-06-20&hasta=2026-06-20")
    assert r.status_code == 200, r.data
    j = r.get_json()
    it = next((x for x in j["items"] if x["producto"] == "ZZ IO TEST"), None)
    assert it is not None
    assert it["disp_min"] == 30 and it["elab_min"] == 120
    assert it["env_min"] == 60 and it["acond_min"] == 45
    assert it["total_min"] == 300   # 5h
    # cuello de botella = elaboración (la más larga)
    assert j["resumen"]["cuello_botella"] == "Elaboración"


def test_io_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")  # no admin
    r1 = c.get("/api/admin/io/inicio-labores")
    r2 = c.get("/api/admin/io/tiempos-produccion")
    assert r1.status_code in (401, 403) and r2.status_code in (401, 403)
