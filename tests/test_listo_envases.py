"""Smoke del endpoint listo-envases (readiness de envases por lote · #9 · Sebastián 16-jul).

GET /api/programacion/programar/<evento_id>/listo-envases → ¿hay frascos para este lote?
Reusa _composicion_envases_lote + _get_mee_stock. Read-only.
"""
import os
import sqlite3
from datetime import date, timedelta


def _db():
    return sqlite3.connect(os.environ["DB_PATH"])


def test_listo_envases_lote_inexistente_404(admin_client):
    r = admin_client.get("/api/programacion/programar/99999999/listo-envases")
    assert r.status_code == 404, r.data


def test_listo_envases_sin_presentaciones_ok(admin_client):
    """Lote válido sin presentaciones configuradas → 200 con sin_variantes (no crashea)."""
    producto = "PROD_ENVASE_TEST9"
    con = _db()
    con.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
    fecha = (date.today() + timedelta(days=10)).isoformat()
    con.execute(
        "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
        "VALUES (?, ?, 1, 'pendiente', 10, 'eos_plan')", (producto, fecha))
    pid = con.execute("SELECT id FROM produccion_programada WHERE producto=? ORDER BY id DESC LIMIT 1",
                      (producto,)).fetchone()[0]
    con.commit()
    con.close()
    try:
        r = admin_client.get(f"/api/programacion/programar/{pid}/listo-envases")
        assert r.status_code == 200, r.data
        d = r.get_json()
        assert d.get("ok") is True
        # sin presentaciones → sin_variantes True y resumen en 0 (estructura estable)
        assert "resumen" in d and "items" in d
        assert isinstance(d["items"], list)
    finally:
        con = _db()
        con.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        con.commit()
        con.close()
