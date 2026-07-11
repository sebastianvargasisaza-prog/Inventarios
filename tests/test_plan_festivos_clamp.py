"""Audit ultracode del motor de plan · 10-jul. Dos P1 con dientes:
 #7  Los generadores automáticos de 2 años agendaban lotes en FESTIVOS (viola 'sin tocar
     festivos'): _next_dia_produccion solo filtraba L/M/V. Ahora salta festivos también.
 #1/#10/#24  programar-cadencia-producto NO clampaba a hoy → con ancla_fecha pasada sembraba
     lotes de la cadena en el PASADO (ancla-fantasma que infla cobertura → sub-compra). Ahora
     clampa a hoy, espejo del gemelo desde-lote.
"""
from datetime import date, timedelta


def test_next_dia_produccion_salta_festivos(app):  # app → asegura api/ en sys.path
    import blueprints.auto_plan as ap
    from blueprints.plan import es_festivo_colombia
    # 2026-08-17 = lunes (día de producción) Y festivo (Asunción movida por Ley Emiliani).
    d = date(2026, 8, 17)
    assert d.weekday() == 0 and es_festivo_colombia(d), "sanity: 17-ago-2026 es lunes festivo"
    r = ap._next_dia_produccion(d)
    assert r != d, "NO debe devolver el festivo"
    assert r.weekday() in (0, 2, 4) and not es_festivo_colombia(r), "debe ser L/M/V no-festivo"
    # Un lunes normal SÍ se devuelve igual (no rompe el caso feliz).
    lun = date(2026, 8, 24)
    assert not es_festivo_colombia(lun)
    assert ap._next_dia_produccion(lun) == lun


def test_cadencia_producto_no_siembra_en_pasado(admin_client):
    """Con ancla_fecha pasada, ningún lote creado puede quedar antes de hoy."""
    from .conftest import csrf_headers  # noqa: F401
    hoy = date.today()
    ancla_pasada = (hoy - timedelta(days=120)).isoformat()
    body = {
        "producto": "ZZ CADENCIA CLAMP TEST",
        "kg_por_lote": 10.0,
        "interval_dias": 60,
        "dias_hasta_primera": 1,   # chico + ancla vieja → sin clamp caería en el pasado
        "ancla_fecha": ancla_pasada,
    }
    r = admin_client.post("/api/plan/programar-cadencia-producto", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    d = r.get_json()
    fechas = d.get("fechas") or []
    assert fechas, "debe crear al menos un lote"
    hoy_iso = hoy.isoformat()
    for f in fechas:
        assert f[:10] >= hoy_iso, "ningún lote de la cadena puede quedar en el pasado (%s)" % f


def test_cadencia_producto_rechaza_interval_cero(admin_client):
    """[audit multinivel #4] Sin cadencia válida (interval_dias=0) el endpoint DEBE rechazar (400),
    no crear una cadena semanal de ~82 lotes tras cancelar todas las futuras del producto."""
    r = admin_client.post("/api/plan/programar-cadencia-producto",
                          json={"producto": "ZZ INTERVAL CERO", "kg_por_lote": 10.0,
                                "interval_dias": 0, "dias_hasta_primera": 30})
    assert r.status_code == 400, r.get_data(as_text=True)[:200]


def test_cadencia_no_vanish_primera_fuera_de_horizonte(app, admin_client):
    """[audit multinivel P1 · anti-vanish M35] Si la 1ª producción cae FUERA del horizonte (dias_hasta_primera
    > anios×365), el endpoint DEBE rechazar (400) ANTES de cancelar — no dejar la cadena en 0 tras cancelar todo."""
    PROD = "ZZ NO VANISH"
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        # una cadena existente que NO se debe perder
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
                  "VALUES (?,?,1,'pendiente','eos_plan',10)", (PROD, (date.today() + timedelta(days=60)).isoformat()))
        try:
            conn.commit()
        except Exception:
            pass
    # dias_hasta_primera=400 > 365 (anios=1) → debe rechazar
    r = admin_client.post("/api/plan/programar-cadencia-producto",
                          json={"producto": PROD, "kg_por_lote": 10.0, "interval_dias": 60,
                                "dias_hasta_primera": 400, "anios": 1})
    assert r.status_code == 400, r.get_data(as_text=True)[:200]
    # la cadena previa sigue viva (no se canceló)
    with app.app_context():
        from database import get_db
        n = get_db().execute("SELECT COUNT(*) FROM produccion_programada WHERE producto=? "
                             "AND COALESCE(estado,'')<>'cancelado'", (PROD,)).fetchone()[0]
        assert n >= 1, "la cadena previa NO debe cancelarse cuando se rechaza"
