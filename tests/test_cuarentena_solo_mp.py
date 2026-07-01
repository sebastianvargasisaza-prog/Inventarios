"""La cuarentena de CALIDAD (COC-PRO-001 · /api/lotes/cuarentena) es SOLO para materia prima.
EPP, dotación y OCs de categorías no-MP NO deben aparecer ahí (Sebastián 1-jul-2026)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_cuarentena_muestra_mp_oculta_epp(app, db_clean):
    _exec("DELETE FROM movimientos WHERE material_id IN ('MP-Q1','EPP-Q')")
    # Materia prima REAL, recibida por una OC de categoría 'Materia Prima', en cuarentena
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, tipo_material, activo) "
          "VALUES ('MP-Q1','MP Real Q','MP',1)")
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc, estado, categoria) "
          "VALUES ('OC-MP-Q','Recibida','Materia Prima')")
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
          "numero_oc, estado_lote) VALUES ('MP-Q1','MP Real Q',1000,'Entrada','2026-07-01','LMPQ1',"
          "'OC-MP-Q','CUARENTENA')")
    # EPP: OC de categoría 'EPP' · aunque el maestro quedó MAL catalogado como tipo_material='MP',
    # el filtro por categoría de la OC debe ocultarlo de la cuarentena de Calidad.
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, tipo_material, activo) "
          "VALUES ('EPP-Q','EPP','MP',1)")
    _exec("INSERT OR REPLACE INTO ordenes_compra (numero_oc, estado, categoria) "
          "VALUES ('OC-EPP-Q','Recibida','EPP')")
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
          "numero_oc, estado_lote) VALUES ('EPP-Q','EPP',1,'Entrada','2026-07-01','LEPPQ',"
          "'OC-EPP-Q','CUARENTENA')")

    c = _login(app)
    r = c.get("/api/lotes/cuarentena")
    assert r.status_code == 200, r.data
    codigos = {row["codigo_mp"] for row in r.get_json()}
    assert "MP-Q1" in codigos, "la MP real debe aparecer en la cuarentena de Calidad"
    assert "EPP-Q" not in codigos, "EPP (OC categoría no-MP) NO debe aparecer en la cuarentena de MP"


def test_cuarentena_muestra_mp_ingreso_manual_sin_oc(app, db_clean):
    """Un ingreso manual de MP (sin OC) en cuarentena sigue apareciendo (no se pierde)."""
    _exec("DELETE FROM movimientos WHERE material_id='MP-Q2'")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, tipo_material, activo) "
          "VALUES ('MP-Q2','MP Manual Q','MP',1)")
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
          "estado_lote) VALUES ('MP-Q2','MP Manual Q',500,'Entrada','2026-07-01','LMPQ2','CUARENTENA')")
    c = _login(app)
    r = c.get("/api/lotes/cuarentena")
    assert r.status_code == 200, r.data
    codigos = {row["codigo_mp"] for row in r.get_json()}
    assert "MP-Q2" in codigos, "un ingreso manual de MP sin OC debe seguir apareciendo"
