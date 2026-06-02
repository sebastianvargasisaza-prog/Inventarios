"""Sebastián 1-jun-2026: 'todo debe unificarse en produccion_programada'. El audit de
mínimos ahora mide la demanda desde produccion_programada (vía abastecimiento), no desde
Google Calendar. Una producción Fijo que consume una MP debe verse como consumo > 0 y
recibir mínimo recomendado (antes, sin calendario, salía SIN_USO)."""
import os, sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_audit_minimos_consume_de_produccion_programada(app, db_clean):
    producto = "ZZUNIF AUDIT"
    mp = "MPUNIF01"
    c = _login(app)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (mp,))
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
    conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
    conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) VALUES (?, 'UNIF MP', 'Inchemical', 1)", (mp,))
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (producto,))
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?, ?, 'UNIF MP', 100, 10000)", (producto, mp))
    # producción Fijo de 10kg dentro del horizonte (90d)
    conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                 "VALUES (?, date('now','-5 hours','+10 days'), 10, 1, 'programado', 'eos_plan')", (producto,))
    conn.commit(); conn.close()

    r = c.get("/api/admin/auditar-minimos?proyeccion_dias=90")
    assert r.status_code == 200, r.data
    d = r.get_json()
    item = next((a for a in d["auditoria"] if a["codigo_mp"] == mp), None)
    assert item is not None, "la MP debe aparecer en el audit"
    # consumo viene de produccion_programada (100% × 10kg = 10000 g en el horizonte)
    assert item["consumo_horizonte_g"] >= 9000, item
    assert item["consumo_diario_g"] > 0, item
    assert item["minimo_recomendado_g"] > 0, item
    assert not item["estado"].startswith("SIN_USO"), item
