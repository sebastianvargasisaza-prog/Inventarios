"""Plano de fabricación · POST /api/planta/fabricacion/crear-iniciar (programacion.py).

Crea la producción (producto + área + kg) y DELEGA en prog_iniciar_produccion (M3):
inicio_real_at + sala→ocupada + descuento FEFO de MP. No reimplementa el descuento.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ FAB PLANO PROD"
MP = "MPFABPLANO"
AREA = "ZZFABPLANO"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM areas_planta WHERE codigo=?", (AREA,))
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    conn.execute("DELETE FROM movimientos WHERE material_id=?", (MP,))
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (MP,))
    conn.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    # MP activo + stock VIGENTE (5kg) para que el FEFO alcance
    conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo, controla_stock) "
                 "VALUES (?,?,?,1,1)", (MP, "ZZ MP FAB PLANO", "T"))
    conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                 "VALUES (?,?,?,?,?,?,?)", (MP, "ZZ MP FAB PLANO", 5000, "Entrada", "2026-01-01", "LFABPLANO", "VIGENTE"))
    # fórmula 100% del MP (lote 1kg → 1000g)
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)", (PROD,))
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?,?,?,?,?)", (PROD, MP, "ZZ MP FAB PLANO", 100, 1000))
    # área de fabricación libre
    conn.execute("INSERT INTO areas_planta (codigo, nombre, puede_producir, puede_envasar, tipo, activo, orden, estado, marmita_ml) "
                 "VALUES (?,?,1,0,'produccion',1,95,'libre',200)", (AREA, "ZZ Fab Plano"))
    conn.commit()
    aid = conn.execute("SELECT id FROM areas_planta WHERE codigo=?", (AREA,)).fetchone()[0]
    conn.close()
    return aid


def _stock(mp):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','Ajuste +','Ajuste') THEN cantidad "
        "WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad ELSE 0 END),0) FROM movimientos WHERE material_id=?",
        (mp,)).fetchone()[0]
    conn.close()
    return row


def test_crear_iniciar_ocupa_area_y_descuenta(app, db_clean):
    aid = _seed()
    c = _login(app)
    antes = _stock(MP)
    r = c.post("/api/planta/fabricacion/crear-iniciar",
               json={"producto": PROD, "area_id": aid, "cantidad_kg": 1}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    conn = sqlite3.connect(os.environ["DB_PATH"])
    pp = conn.execute("SELECT inicio_real_at, area_id, estado FROM produccion_programada WHERE producto=? "
                      "ORDER BY id DESC LIMIT 1", (PROD,)).fetchone()
    estado_area = conn.execute("SELECT estado FROM areas_planta WHERE id=?", (aid,)).fetchone()[0]
    conn.close()
    assert pp is not None and pp[0]            # inicio_real_at seteado
    assert pp[1] == aid                        # área guardada
    assert estado_area == "ocupada"            # área quedó ocupada
    assert _stock(MP) == antes - 1000          # descontó 1kg = 1000g (100% × 1kg)


def test_area_inexistente_404(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/planta/fabricacion/crear-iniciar",
               json={"producto": PROD, "area_id": 999999, "cantidad_kg": 1}, headers=_csrf(c))
    assert r.status_code == 404


def test_area_ocupada_409(app, db_clean):
    """En modo ESTRICTO (INVIMA) el área debe estar LIBRE: 'ocupada' bloquea con 409."""
    aid = _seed()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=?", (aid,))
    # El gate de estado de área SOLO aplica en estricto (M68): en beta el estado NUNCA
    # bloquea el registro. Forzamos estricto para validar el gate INVIMA legítimo.
    conn.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('exigir_area_limpia', '1')")
    conn.commit()
    conn.close()
    c = _login(app)
    r = c.post("/api/planta/fabricacion/crear-iniciar",
               json={"producto": PROD, "area_id": aid, "cantidad_kg": 1}, headers=_csrf(c))
    assert r.status_code == 409
    assert r.get_json().get("codigo") == "AREA_OCUPADA"


def test_area_ocupada_beta_no_bloquea(app, db_clean):
    """Beta (M68): el estado del área NO bloquea el registro · se pueden registrar varias
    producciones en la misma sala aunque esté 'ocupada' con una producción en curso. Esto es
    lo que Sebastián pidió mientras se termina de construir el flujo de planta (30-jun)."""
    aid = _seed()
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE areas_planta SET estado='ocupada' WHERE id=?", (aid,))
    # una producción REALMENTE activa ya ocupa la sala (el caso que antes trababa)
    conn.execute("INSERT INTO produccion_programada "
                 "(producto, fecha_programada, area_id, cantidad_kg, estado, inicio_real_at, origen) "
                 "VALUES (?,?,?,?,?,?,?)",
                 ("ZZ OCUPANTE ACTIVA", "2026-06-30", aid, 1, "en_proceso",
                  "2026-06-30 08:00:00", "eos_plan"))
    # asegurar beta explícito (default) · el estado del área no debe frenar
    conn.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('exigir_area_limpia', '0')")
    conn.commit()
    conn.close()
    c = _login(app)
    r = c.post("/api/planta/fabricacion/crear-iniciar",
               json={"producto": PROD, "area_id": aid, "cantidad_kg": 1}, headers=_csrf(c))
    # NO 409 por área · se registra (200) pese a la sala ocupada con producción en curso
    assert r.status_code != 409, r.data
    assert r.get_json().get("codigo") != "AREA_OCUPADA"


def test_stock_insuficiente_limpia_huerfana(app, db_clean):
    aid = _seed()
    # vaciar el stock → el motor debe fallar 422 y NO dejar producción colgada
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                 "VALUES (?,?,?,?,?,?,?)", (MP, "ZZ MP FAB PLANO", 5000, "Salida", "2026-01-02", "LFABPLANO", "VIGENTE"))
    conn.commit()
    conn.close()
    c = _login(app)
    r = c.post("/api/planta/fabricacion/crear-iniciar",
               json={"producto": PROD, "area_id": aid, "cantidad_kg": 1}, headers=_csrf(c))
    assert r.status_code == 422
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto=?", (PROD,)).fetchone()[0]
    estado = conn.execute("SELECT estado FROM areas_planta WHERE id=?", (aid,)).fetchone()[0]
    conn.close()
    assert n == 0                  # producción huérfana borrada
    assert estado == "libre"       # área quedó libre (nunca se ocupó)
