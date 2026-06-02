"""Audit Abastecimiento 1-jun-2026: la demanda de MP no debe doble-contar fórmulas
duplicadas, y debe cruzar fórmula↔producción aunque el nombre difiera en espacios."""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _consumo_mp(client, codigo, h="30"):
    r = client.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    d = r.get_json()
    it = next((x for x in (d.get("mps") or []) if str(x.get("codigo")).upper() == codigo.upper()), None)
    return (it["consumo"].get(h) if it else None), it


def test_demanda_mp_no_doble_cuenta_formula_duplicada(app, db_clean):
    producto = "ZZABA DEDUP TEST"
    mp = "MPZZABA01"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (mp,))
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?, 'ZZ MP', 1)", (mp,))
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (producto,))
        # DUPLICADO: mismo producto + mismo material_id, 50% → debe contarse UNA vez
        for _ in range(2):
            conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                         "VALUES (?, ?, 'ZZ MP', 50, 0)", (producto, mp))
        # producción Fijo de 10kg en 5 días
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                     "VALUES (?, date('now','-5 hours','+5 days'), 10, 1, 'programado', 'eos_plan')", (producto,))
        conn.commit()
    consumo, it = _consumo_mp(c, mp, "30")
    assert it is not None, "la MP debe aparecer en la demanda"
    # 50% × 10kg × 1000 = 5000 g · NO 10000 (que sería doble conteo de la fórmula dup)
    assert abs(consumo - 5000.0) < 1.0, f"esperado ~5000g (una vez), got {consumo}"
