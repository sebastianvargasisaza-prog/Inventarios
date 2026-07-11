"""Sebastián 11-jul · CAPACIDAD DIARIA del calendario: máx 2 lotes/día · lote ≥100kg va SOLO ·
nunca finde/festivo · si el día está lleno, corre al próximo día hábil con cupo. Las cadenas ahora
usan _proxima_fecha_habil (antes _dia_habil ignoraba la capacidad → clusterización)."""
from datetime import date, timedelta
from collections import defaultdict


def _csrf():
    from tests.conftest import csrf_headers
    return csrf_headers()


def test_capacidad_max2_y_grande_solo(app, admin_client):
    prods = ["ZZ CAP A", "ZZ CAP B", "ZZ CAP C"]
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        for p in prods + ["ZZ CAP GRANDE"]:
            c.execute("DELETE FROM produccion_programada WHERE producto=?", (p,))
        try:
            conn.commit()
        except Exception:
            pass
    # 3 cadenas CHICAS con misma cadencia/arranque → tienden a chocar en los mismos días → máx 2/día, 3ª corre
    for p in prods:
        r = admin_client.post("/api/plan/programar-cadencia-producto",
                              json={"producto": p, "kg_por_lote": 20, "interval_dias": 40, "dias_hasta_primera": 40, "anios": 1})
        assert r.status_code == 200, r.get_data(as_text=True)[:150]
    # 1 cadena GRANDE (150kg ≥100) → cada lote debe quedar SOLO en su día
    rg = admin_client.post("/api/plan/programar-cadencia-producto",
                           json={"producto": "ZZ CAP GRANDE", "kg_por_lote": 150, "interval_dias": 40, "dias_hasta_primera": 40, "anios": 1})
    assert rg.status_code == 200, rg.get_data(as_text=True)[:150]
    with app.app_context():
        from database import get_db
        from blueprints.plan import es_festivo_colombia
        c = get_db().cursor()
        rows = c.execute("SELECT substr(fecha_programada,1,10), cantidad_kg FROM produccion_programada "
                         "WHERE COALESCE(estado,'') NOT IN ('cancelado','completado') AND producto LIKE 'ZZ CAP%'").fetchall()
        byday = defaultdict(list)
        for f, kg in rows:
            byday[f].append(float(kg or 0))
        for f, kgs in byday.items():
            d = date.fromisoformat(f)
            assert d.weekday() < 5 and not es_festivo_colombia(d), "lote en finde/festivo: %s" % f
            assert len(kgs) <= 2, ("día con >2 lotes: %s → %s" % (f, kgs))
            if any(k >= 100 for k in kgs):
                assert len(kgs) == 1, ("día con lote grande NO va solo: %s → %s" % (f, kgs))
