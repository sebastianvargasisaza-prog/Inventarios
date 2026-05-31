"""Composición de envases con CANTIDAD FIJA (mig 204).

Caso SUERO ILUMINADOR TRX: 10ml = SIEMPRE 1200 uds, el resto del bulk al 30ml.
composicion-mee debe reservar las fijas primero y repartir el resto por ratio.
"""
import os
import sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def test_composicion_mee_cantidad_fija(app, db_clean):
    PROD = "PROD-FIJA-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute(
        """INSERT INTO producto_presentaciones
           (producto_nombre, presentacion_codigo, etiqueta, volumen_ml,
            envase_codigo, activo, cantidad_fija_uds)
           VALUES (?,?,?,?,?,1,0)""",
        (PROD, "P30", "30ml", 30, "ENV-30"))
    db.execute(
        """INSERT INTO producto_presentaciones
           (producto_nombre, presentacion_codigo, etiqueta, volumen_ml,
            envase_codigo, activo, cantidad_fija_uds)
           VALUES (?,?,?,?,?,1,1200)""",
        (PROD, "P10", "10ml", 10, "ENV-10"))
    cur = db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes)
           VALUES (?, date('now','+10 days'), 110, 'programado', 'eos_plan', 1)""",
        (PROD,))
    lote_id = cur.lastrowid
    db.commit()
    db.close()

    r = c.get("/api/programacion/programar/%d/composicion-mee" % lote_id)
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] and d.get("tiene_fija") is True, d
    by = {v["volumen_ml"]: v for v in d["variantes"]}
    # 10ml: cantidad FIJA = 1200 (no proporcional al bulk)
    assert by[10]["es_fija"] is True, by[10]
    assert by[10]["unidades_estimadas"] == 1200, by[10]
    # 30ml: el resto · (110 - 12)kg = 98kg ÷ 30ml = 3266-3267 uds
    assert by[30]["es_fija"] is False, by[30]
    assert 3260 <= by[30]["unidades_estimadas"] <= 3270, by[30]


def test_composicion_mee_sin_fija_sigue_proporcional(app, db_clean):
    """Sin cantidad fija → comportamiento previo (proporcional)."""
    PROD = "PROD-NOFIJA-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute(
        """INSERT INTO producto_presentaciones
           (producto_nombre, presentacion_codigo, etiqueta, volumen_ml,
            envase_codigo, activo, cantidad_fija_uds)
           VALUES (?,?,?,?,?,1,0)""",
        (PROD, "P30", "30ml", 30, "ENV-30"))
    cur = db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes)
           VALUES (?, date('now','+10 days'), 30, 'programado', 'eos_plan', 1)""",
        (PROD,))
    lote_id = cur.lastrowid
    db.commit()
    db.close()
    r = c.get("/api/programacion/programar/%d/composicion-mee" % lote_id)
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d.get("tiene_fija") is False, d
    # 30kg ÷ 30ml = 1000 uds
    assert d["variantes"][0]["unidades_estimadas"] == 1000, d["variantes"]


def test_upsert_preserva_fija_al_editar_ratio(app, db_clean):
    """El upsert persiste cantidad_fija_uds, y editar SOLO el ratio (sin enviar
    cantidad_fija_uds) NO la borra."""
    import json
    from .conftest import csrf_headers
    PROD = "PROD-UPSERT-FIJA"
    c = _login_as(app, "sebastian")
    h = csrf_headers()
    h["Content-Type"] = "application/json"
    # 1) Crear presentación con cantidad fija = 1200
    r = c.post("/api/admin/producto-presentaciones-upsert",
               data=json.dumps({"producto_nombre": PROD, "presentacion_codigo": "P10",
                                "etiqueta": "10 ml", "volumen_ml": 10,
                                "envase_codigo": "", "cantidad_fija_uds": 1200}),
               headers=h)
    assert r.status_code == 200, r.data
    g = c.get("/api/admin/producto-presentaciones?producto=" + PROD)
    assert g.status_code == 200, g.data
    pres = g.get_json()["presentaciones"]
    fila = next(p for p in pres if p["presentacion_codigo"] == "P10")
    assert abs(float(fila["cantidad_fija_uds"]) - 1200) < 0.01, fila
    # 2) Editar SOLO el ratio (sin cantidad_fija_uds) → no debe borrar la fija
    r2 = c.post("/api/admin/producto-presentaciones-upsert",
                data=json.dumps({"producto_nombre": PROD, "presentacion_codigo": "P10",
                                 "etiqueta": "10 ml", "volumen_ml": 10,
                                 "envase_codigo": "", "ventas_mes_referencia": 50}),
                headers=h)
    assert r2.status_code == 200, r2.data
    g2 = c.get("/api/admin/producto-presentaciones?producto=" + PROD)
    fila2 = next(p for p in g2.get_json()["presentaciones"] if p["presentacion_codigo"] == "P10")
    assert abs(float(fila2["cantidad_fija_uds"]) - 1200) < 0.01, fila2  # sigue 1200


def test_fija_override_por_lote(app, db_clean):
    """Override de cantidad fija SOLO para un lote · no toca el default del producto."""
    import json
    from .conftest import csrf_headers
    PROD = "PROD-OVR-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    # default del producto: 10ml = 1200 fija
    db.execute(
        """INSERT INTO producto_presentaciones
           (producto_nombre, presentacion_codigo, etiqueta, volumen_ml,
            envase_codigo, activo, cantidad_fija_uds)
           VALUES (?,?,?,?,?,1,1200)""",
        (PROD, "P10", "10ml", 10, "ENV-10"))
    db.execute(
        """INSERT INTO producto_presentaciones
           (producto_nombre, presentacion_codigo, etiqueta, volumen_ml,
            envase_codigo, activo, cantidad_fija_uds)
           VALUES (?,?,?,?,?,1,0)""",
        (PROD, "P30", "30ml", 30, "ENV-30"))
    cur = db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes)
           VALUES (?, date('now','+10 days'), 110, 'programado', 'eos_plan', 1)""",
        (PROD,))
    lote_id = cur.lastrowid
    db.commit()
    db.close()

    h = csrf_headers(); h["Content-Type"] = "application/json"
    # Sin override → usa el default (1200)
    d0 = c.get("/api/programacion/programar/%d/composicion-mee" % lote_id).get_json()
    by0 = {v["volumen_ml"]: v for v in d0["variantes"]}
    assert by0[10]["unidades_estimadas"] == 1200, by0[10]
    assert by0[10]["fija_es_override"] is False

    # Override SOLO este lote → 2000
    r = c.patch("/api/programacion/lote/%d/fija-override" % lote_id,
                data=json.dumps({"presentacion_codigo": "P10", "uds": 2000}), headers=h)
    assert r.status_code == 200, r.data
    d1 = c.get("/api/programacion/programar/%d/composicion-mee" % lote_id).get_json()
    by1 = {v["volumen_ml"]: v for v in d1["variantes"]}
    assert by1[10]["unidades_estimadas"] == 2000, by1[10]
    assert by1[10]["fija_es_override"] is True
    assert by1[10]["cantidad_fija_default"] == 1200, by1[10]
    assert d1.get("tiene_override") is True

    # El DEFAULT del producto sigue 1200 (no lo tocó)
    db = sqlite3.connect(os.environ["DB_PATH"])
    defv = db.execute("SELECT cantidad_fija_uds FROM producto_presentaciones WHERE producto_nombre=? AND presentacion_codigo='P10'", (PROD,)).fetchone()[0]
    db.close()
    assert abs(float(defv) - 1200) < 0.01, defv

    # Limpiar override (uds vacío) → vuelve al default 1200
    r2 = c.patch("/api/programacion/lote/%d/fija-override" % lote_id,
                 data=json.dumps({"presentacion_codigo": "P10", "uds": ""}), headers=h)
    assert r2.status_code == 200, r2.data
    d2 = c.get("/api/programacion/programar/%d/composicion-mee" % lote_id).get_json()
    by2 = {v["volumen_ml"]: v for v in d2["variantes"]}
    assert by2[10]["unidades_estimadas"] == 1200, by2[10]
    assert by2[10]["fija_es_override"] is False
