"""Sebastián 10-jul · MODELO CANÓNICO MANUAL. La programación vive SOLO de las cadenas
manuales (punto de origen + cadencia); los crons/sugerencias no crean producciones. Flag
maestro `programacion_solo_manual` (default OFF · reversible). Endpoint horizonte 1|2 años."""
from datetime import date, timedelta


def test_toggle_solo_manual(app, admin_client):
    # DEFAULT ON (Sebastián 10-jul · el modelo manual es EL modelo · automáticos viejos apagados)
    r = admin_client.get("/api/plan/solo-manual")
    assert r.status_code == 200 and r.get_json()["activo"] is True
    with app.app_context():
        from database import programacion_solo_manual
        assert programacion_solo_manual() is True
    # apagar explícitamente (para reactivar los automáticos viejos / lógica futura) · reversible
    a = admin_client.post("/api/plan/solo-manual", json={"activo": False})
    assert a.status_code == 200 and a.get_json()["activo"] is False
    with app.app_context():
        from database import programacion_solo_manual
        assert programacion_solo_manual() is False
    # volver a prender
    p = admin_client.post("/api/plan/solo-manual", json={"activo": True})
    assert p.status_code == 200 and p.get_json()["activo"] is True


def test_cadencia_producto_horizonte_anios(admin_client):
    """El horizonte 1 vs 2 años cambia cuántos lotes crea (la cadena de 2 años llega más lejos)."""
    base = {"producto": "ZZ HORIZONTE TEST", "kg_por_lote": 10.0,
            "interval_dias": 60, "dias_hasta_primera": 60}
    r1 = admin_client.post("/api/plan/programar-cadencia-producto", json={**base, "anios": 1})
    assert r1.status_code == 200, r1.get_data(as_text=True)[:200]
    d1 = r1.get_json()
    r2 = admin_client.post("/api/plan/programar-cadencia-producto", json={**base, "anios": 2})
    assert r2.status_code == 200
    d2 = r2.get_json()
    # 2 años crea más lotes que 1 año (misma cadencia)
    assert d2["creados"] > d1["creados"], (d1["creados"], d2["creados"])
    # ningún lote de la cadena de 1 año supera ~1 año + margen de día hábil
    hoy = date.today()
    tope_1y = (hoy + timedelta(days=372)).isoformat()
    for f in (d1.get("fechas") or []):
        assert f[:10] <= tope_1y, "lote fuera del horizonte de 1 año: %s" % f


def test_cadencia_desde_lote_acepta_3_anios(app, admin_client):
    """[review P1] El botón '📌 recalcular' manda años hasta 3 a programar-cadencia-desde-lote;
    el endpoint debe RESPETAR 3 (antes clampaba a 2 en silencio → display≠motor)."""
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM produccion_programada WHERE producto='ZZ DESDE LOTE 3Y'")
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
                  "VALUES ('ZZ DESDE LOTE 3Y', ?, 1, 'pendiente', 'eos_plan', 10)", (date.today().isoformat(),))
        lote_id = c.lastrowid
        try:
            conn.commit()
        except Exception:
            pass
    r = admin_client.post("/api/plan/programar-cadencia-desde-lote/%d" % lote_id,
                          json={"interval_dias": 61, "first_offset_dias": 61, "kg_por_lote": 10.0, "anios": 3})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    d = r.get_json()
    assert d.get("anios") == 3, "el endpoint debe respetar 3 años, devolvió %s" % d.get("anios")
    fechas = sorted(d.get("fechas") or [])
    if len(fechas) >= 2:
        span = (date.fromisoformat(fechas[-1][:10]) - date.fromisoformat(fechas[0][:10])).days
        assert span >= 900, "la cadena de 3 años debe abarcar >900 días, dio %d" % span


def test_origen_fuente_colocado_y_reemplazo(app, admin_client):
    """[Sebastián 10-jul · 2ª fuente de la verdad] Al programar la cadena manual con una fecha de
    ORIGEN pasada: (1) coloca la producción FUENTE en el calendario en esa fecha pasada (histórica,
    no descuenta), (2) crea la cadena desde ahí, (3) REEMPLAZA las producciones futuras stale del
    producto, (4) preserva B2B y lo ejecutado, (5) es idempotente (re-programar no duplica la fuente)."""
    PROD = "ZZ FUENTE ORIGEN"
    origen = (date.today() - timedelta(days=40)).isoformat()   # produjo hace 40 días
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        # producción STALE futura (auto) que debe ser reemplazada
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
                  "VALUES (?,?,1,'pendiente','eos_canonico',50)", (PROD, (date.today() + timedelta(days=15)).isoformat()))
        # B2B futuro (debe preservarse)
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
                  "VALUES (?,?,1,'pendiente','eos_b2b',30)", (PROD, (date.today() + timedelta(days=20)).isoformat()))
        try:
            conn.commit()
        except Exception:
            pass
    body = {"producto": PROD, "ancla_fecha": origen, "kg_origen": 100.0, "kg_por_lote": 100.0,
            "interval_dias": 30, "dias_hasta_primera": 30, "anios": 1, "crear_origen": True}
    r = admin_client.post("/api/plan/programar-cadencia-producto", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    d = r.get_json()
    assert d["origen_creado"] is True and d["origen_fecha"] == origen
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        # (1) fuente colocada en la fecha PASADA, histórica, kg 100, no cancelada
        fuente = c.execute("SELECT origen, cantidad_kg FROM produccion_programada WHERE producto=? "
                           "AND substr(fecha_programada,1,10)=? AND COALESCE(estado,'')<>'cancelado'",
                           (PROD, origen)).fetchone()
        assert fuente is not None, "no se colocó la producción fuente en la fecha de origen"
        assert fuente[0] == 'eos_retroactivo' and abs(float(fuente[1]) - 100.0) < 0.5
        # (2) cadena creada desde el origen, ninguna en el pasado
        hoy = date.today().isoformat()
        for f in (d.get("fechas") or []):
            assert f[:10] >= hoy, "lote de la cadena en el pasado: %s" % f
        # (3) la stale futura eos_canonico fue cancelada
        stale = c.execute("SELECT estado FROM produccion_programada WHERE producto=? AND origen='eos_canonico'", (PROD,)).fetchone()
        assert stale and stale[0] == 'cancelado', "la producción stale no fue reemplazada"
        # (4) el B2B se preservó
        b2b = c.execute("SELECT estado FROM produccion_programada WHERE producto=? AND origen='eos_b2b'", (PROD,)).fetchone()
        assert b2b and b2b[0] != 'cancelado', "el B2B NO debe cancelarse"
    # (5) idempotencia: re-programar NO duplica la fuente
    r2 = admin_client.post("/api/plan/programar-cadencia-producto", json=body)
    assert r2.status_code == 200
    assert r2.get_json()["origen_creado"] is False, "re-programar NO debe duplicar la fuente"
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        n = c.execute("SELECT COUNT(*) FROM produccion_programada WHERE producto=? AND substr(fecha_programada,1,10)=? "
                      "AND COALESCE(estado,'')<>'cancelado'", (PROD, origen)).fetchone()[0]
        assert n == 1, "debe haber exactamente 1 producción fuente, hay %d" % n


def test_verificar_cadenas_1anio_no_incompleta(admin_client):
    """[audit] Una cadena de 1 año (el DEFAULT) con cadencia normal NO debe marcarse 'incompleta'
    (antes los umbrales fijos span<480/n<4 la marcaban falsa · ahora se calibra por la cadencia real)."""
    PROD = "ZZ VERIF 1ANIO"
    r = admin_client.post("/api/plan/programar-cadencia-producto",
                          json={"producto": PROD, "kg_por_lote": 10, "interval_dias": 61,
                                "dias_hasta_primera": 61, "anios": 1})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert (r.get_json().get("creados") or 0) >= 4   # ~6 lotes en 1 año cada 2 meses
    v = admin_client.get("/api/plan/verificar-cadenas").get_json()
    fila = next((x for x in (v.get("productos") or []) if (x.get("producto") or "").upper() == PROD.upper()), None)
    assert fila is not None, "el producto no aparece en verificar-cadenas"
    assert fila["estado"] not in ("incompleta", "sin_cadena", "hueco_grande"), \
        ("cadena de 1 año NO debe ser incompleta/hueco", fila["estado"], fila.get("lotes_cadena"), fila.get("span_dias"))


def test_cron_auto_plan_gateado_por_flag(app):
    """Con el flag ON, el helper que gobierna los crons devuelve True → los generadores
    automáticos hacen early-return (verificado por el propio helper; los crons lo consultan)."""
    with app.app_context():
        from database import get_db, programacion_solo_manual
        conn = get_db()
        conn.execute("DELETE FROM app_settings WHERE clave='programacion_solo_manual'")
        conn.execute("INSERT INTO app_settings (clave, valor) VALUES ('programacion_solo_manual','1')")
        try:
            conn.commit()
        except Exception:
            pass
        assert programacion_solo_manual(conn) is True
