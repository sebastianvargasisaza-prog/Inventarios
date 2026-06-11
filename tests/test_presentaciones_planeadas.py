"""Auto-carga de presentaciones planeadas en el legajo de Envasado/Acondicionamiento.

Reemplazo MyBatch · 10-jun-2026: una producción de granel → N presentaciones
(envase × cliente: Animus + B2B). Cuando aún no hay envasado real registrado, el
legajo muestra las presentaciones PLANEADAS desde la programación ('Programado').
"""
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
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_envasado_autocarga_presentaciones_b2b_y_animus(app, db_clean):
    c = _login(app, "sebastian")
    prod = "ZZ-PRESENT"
    # produccion_programada del producto (cantidad_kg para la composición Animus)
    pp_id = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, lotes) "
                  "VALUES (?, date('now','-5 hours'), 10, 'pendiente', 1)", (prod,))
    # una presentación Animus (envase 30ml)
    _exec("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
          "volumen_ml, envase_codigo, activo) VALUES (?, 'ZZ-30', 'Envase 30ml', 30, 'ENV-ZZ-30', 1)", (prod,))
    # un aporte B2B (Fernando Mesa) sobre ese mismo lote programado
    _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte, "
          "ml_unidad, envase_codigo, modo, cliente_nombre) "
          "VALUES (999001, ?, 3, 100, 30, 'ENV-ZZ-30', 'sumado_a_lote_canonico', 'Fernando Mesa ZZ')", (pp_id,))
    # EBR de ENVASADO del producto, enlazado a ese produccion_programada, SIN envasado real
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES (?, 1, 'aprobado', 10000, 'sebastian')", (prod,))
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, ?, 'ZZPRES-OF', 'iniciado', 'envasado', 'sebastian', "
                   "datetime('now','utc'), 10000)", (mbr_id, pp_id))

    v = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa")
    assert v.status_code == 200, v.data
    pres = v.get_json().get("envasado_presentaciones", [])
    assert pres, "el legajo debe auto-cargar presentaciones planeadas (Programado)"
    clientes = {p.get("cliente") for p in pres}
    # La fila B2B (cliente) debe aparecer · es la parte determinista.
    assert "Fernando Mesa ZZ" in clientes, clientes
    # Y debe haber al menos una fila Animus (la presentación 30ml del producto).
    assert "Animus" in clientes, clientes
    # Todas las planeadas van en estado 'Programado'.
    assert all((p.get("estado") == "Programado") for p in pres), pres


def test_envasado_con_real_no_usa_planeadas(app, db_clean):
    """Si YA hay envasado real registrado, manda lo real (no las planeadas)."""
    c = _login(app, "sebastian")
    prod = "ZZ-PRESENT2"
    pp_id = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, lotes) "
                  "VALUES (?, date('now','-5 hours'), 10, 'pendiente', 1)", (prod,))
    _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte, "
          "ml_unidad, envase_codigo, modo, cliente_nombre) "
          "VALUES (999002, ?, 3, 100, 30, 'ENV-ZZ-30', 'sumado_a_lote_canonico', 'Fernando Mesa ZZ')", (pp_id,))
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES (?, 1, 'aprobado', 10000, 'sebastian')", (prod,))
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, ?, 'ZZPRES2-OF', 'iniciado', 'envasado', 'sebastian', "
                   "datetime('now','utc'), 10000)", (mbr_id, pp_id))
    # envasado REAL del lote físico (lote_codigo del EBR = 'ZZPRES2-OF')
    _exec("INSERT INTO envasado (produccion_id, lote, producto, presentacion, unidades, estado) "
          "VALUES (0, 'ZZPRES2-OF', ?, 'Real 30ml', 50, 'Completado')", (prod,))

    v = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa")
    assert v.status_code == 200, v.data
    pres = v.get_json().get("envasado_presentaciones", [])
    assert len(pres) == 1 and pres[0]["presentacion"] == "Real 30ml", pres
    # no debe haber filas 'Programado' planeadas si ya hay real
    assert all(p.get("estado") != "Programado" for p in pres), pres
