"""Revertir correcciones de fórmulas recientes desde audit_log (2-jun-2026).

Incidente: sugerencias automáticas de baja confianza aplicadas en masa
(glucosamina→cisteína). Cada CORREGIR_FORMULAS guardó el material_id previo;
este revert las deshace exacto, DB-native (sin depender de backups)."""
import os
import sqlite3
import json

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_revertir_deshace_correccion(app, db_clean):
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPREVOK','Glucosamina real',1)")
        db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPREVMAL','Cisteina',1)")
        # estado actual: línea YA mal corregida a MPREVMAL (lo que pasó en prod)
        db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
                   "VALUES ('ZZ REV','MPREVMAL','N-acetil glucosamina',1,10)")
        # audit que registra la corrección hecha: previo MPREVOK -> nuevo MPREVMAL
        det = json.dumps({'count': 1, 'errores': 0, 'correcciones_sample': [
            {'producto': 'ZZ REV', 'material_id_previo': 'MPREVOK',
             'material_nombre_previo': 'N-acetil glucosamina', 'material_id_nuevo': 'MPREVMAL'}
        ]})
        db.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha) "
                   "VALUES ('sebastian','CORREGIR_FORMULAS','formula_items','_BULK_',?,?,datetime('now','-5 hours'))",
                   (det, "127.0.0.1"))
        db.commit()
    finally:
        db.close()

    c = _login(app)
    r = c.post("/api/admin/revertir-correcciones-formulas-recientes",
               json={"token": "REVERTIR_FORMULAS_2026", "horas": 12}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["revertidos"] >= 1, d

    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        row = db.execute("SELECT material_id FROM formula_items WHERE producto_nombre='ZZ REV'").fetchone()
    finally:
        db.close()
    assert row[0] == "MPREVOK", f"debió volver a MPREVOK, quedó {row[0]}"

    # cleanup
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ REV'")
        db.execute("DELETE FROM maestro_mps WHERE codigo_mp IN ('MPREVOK','MPREVMAL')")
        db.execute("DELETE FROM audit_log WHERE detalle LIKE '%ZZ REV%'")
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def test_revertir_requiere_token(app, db_clean):
    c = _login(app)
    r = c.post("/api/admin/revertir-correcciones-formulas-recientes",
               json={"token": "MAL"}, headers=csrf_headers())
    assert r.status_code == 403
