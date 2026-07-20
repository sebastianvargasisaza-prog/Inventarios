"""cerrar-envasado honra el envase OVERRIDE del lote (Sebastián 20-jul: "el envase puede variar,
debe poderse cambiar"). Antes descontaba el envase DEFAULT de la presentación aunque el lote usara
otro (drift de inventario). Ahora usa envase_codigo_override (igual que _descontar_mee_envasado · M55/M73)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_cierre_envasado_usa_envase_override(app, db_clean):
    prod = "ZZ OF OVERRIDE PROD"
    env_default = "ENV-DEF-30"
    env_override = "ENV-OVR-30"
    lote = "OFOVR-2026-001"
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        for cod in (env_default, env_override):
            conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
                         "VALUES (?, 'Frasco',?, 5000, 0)", (cod, 'Envase'))
        conn.execute("INSERT INTO producto_presentaciones "
                     "(producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,es_default,activo) "
                     "VALUES (?, 'OVR-30','30 ml',30,?,1,1)", (prod, env_default))
        # produccion con OVERRIDE de envase
        cur = conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen,envase_codigo_override) "
                           "VALUES (?, date('now','-5 hours'),1,'completado',3,'eos_plan',?)", (prod, env_override))
        pid = cur.lastrowid
        # MBR + EBR envasado en proceso
        m = conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                         "VALUES (?,1,3000,'test','aprobado')", (prod,))
        mbr_id = m.lastrowid
        e = conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                         "iniciado_at_utc,cantidad_objetivo_g,fase,produccion_id,envases_descontados_at) "
                         "VALUES (?,1,?,?, 'en_proceso','test','2026-07-20T00:00:00',3000,'envasado',?, '')",
                         (mbr_id, lote + '-OF', lote, pid))
        ebr_id = e.lastrowid
        # unidades registradas para esa presentación
        conn.execute("INSERT INTO ebr_envasado_unidades (ebr_id,presentacion_codigo,etiqueta,volumen_ml,unidades,registrado_por,registrado_at_utc) "
                     "VALUES (?, 'OVR-30','30 ml',30,100,'test','2026-07-20T00:00:00')", (ebr_id,))
        conn.commit()
    finally:
        conn.close()

    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{ebr_id}/cerrar-envasado", json={}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)

    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        ovr = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos_mee "
                           "WHERE mee_codigo=? AND tipo='Salida'", (env_override,)).fetchone()[0]
        def_ = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos_mee "
                            "WHERE mee_codigo=? AND tipo='Salida'", (env_default,)).fetchone()[0]
    finally:
        conn.close()
    assert ovr == 100, f"debe descontar 100 del envase OVERRIDE · got {ovr}"
    assert def_ == 0, f"NO debe descontar el envase default cuando hay override · got {def_}"
