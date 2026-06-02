"""Audit Abastecimiento 1-jun-2026: factibilidad debe ARRASTRAR el déficit (no clavar
el stock en 0). 3 lotes que comparten MP con stock para ~medio lote → el faltante del
3er lote debe ser acumulativo, no plano."""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_factibilidad_arrastra_deficit(app, db_clean):
    producto = "ZZFACT ARRASTRE"
    mp = "MPFACTARR"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (mp,))
        conn.execute("DELETE FROM movimientos WHERE material_id=?", (mp,))
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?, 'ARR MP', 1)", (mp,))
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (producto,))
        conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                     "VALUES (?, ?, 'ARR MP', 100, 10000)", (producto, mp))
        # stock 5000 g (medio lote · cada lote necesita 10000 g)
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote) "
                     "VALUES (?, 'ARR MP', 5000, 'Entrada', '2026-06-01', 'L-ARR')", (mp,))
        for dd in (5, 10, 15):
            conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                         "VALUES (?, date('now','-5 hours','+%d days'), 10, 1, 'programado', 'eos_plan')" % dd, (producto,))
        conn.commit()
    r = c.get("/api/plan/factibilidad?dias=60")
    assert r.status_code == 200, r.data
    d = r.get_json()
    lotes = [p for p in d["producciones"] if p["producto"] == producto]
    assert len(lotes) == 3, lotes
    lotes.sort(key=lambda x: x["fecha"])
    # todos bloqueados (stock insuficiente)
    assert all(p["factible"] is False for p in lotes), lotes
    def _falt(p):
        return sum(f["faltante_g"] for f in p.get("mps_faltantes", []) if f["material_id"] == mp)
    f1, f2, f3 = _falt(lotes[0]), _falt(lotes[1]), _falt(lotes[2])
    # arrastre: faltante crece lote a lote (5000 → 15000 → 25000), no plano (10000)
    assert f1 == 5000, f1
    assert f3 > f2 > f1, (f1, f2, f3)
    assert f3 >= 24000, f3   # acumulado, no 10000 plano
