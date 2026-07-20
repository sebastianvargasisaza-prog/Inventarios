"""Finalizar/completar NO descuenta envases (Sebastián 20-jul · decisión "envases SOLO en Envasado").

Los tipos envase/tapa/caja/etiqueta se consumen EXCLUSIVAMENTE en Envasado (cerrar-envasado EBR o el
flujo _descontar_mee_envasado). prog_completar_evento los EXCLUYE → invariante duro contra doble
descuento (antes solo se salvaba porque el ítem quedaba en estado 'pendiente')."""
import os
import sqlite3
import importlib
import sys
from .conftest import TEST_PASSWORD, csrf_headers


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_completar_excluye_envases_incluye_no_envase(app, db_clean):
    _api()
    prog = importlib.import_module("blueprints.programacion")
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    prod = "ZZ COMPLETAR ENV PROD"
    envase = "ENV-CE-30ML"
    try:
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, volumen_unitario_ml) "
                     "VALUES (?,1,1,30)", (prod,))
        conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
                     "VALUES (?, 'Frasco CE 30ml','Envase',1000,0)", (envase,))
        conn.execute("INSERT INTO producto_presentaciones "
                     "(producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,es_default,activo) "
                     "VALUES (?, 'CE-30','30 ml',30,?,1,1)", (prod, envase))
        cur = conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
                           "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',3,'eos_plan')", (prod,))
        pid = cur.lastrowid
        conn.commit()
        prog._generar_checklist_produccion(conn.cursor(), pid, prod, '2026-06-25', 3.0,
                                           generar_mps=False, usuario='test')
        # Poner el item de ENVASE en estado descontable (simula que alguien lo marcó "listo")
        conn.execute("UPDATE produccion_checklist SET estado='listo', cantidad_unidades=100, "
                     "mee_codigo_asignado=? WHERE produccion_id=? AND item_tipo='envase_primario'",
                     (envase, pid))
        # Agregar un item NO-envase (decoración) en estado descontable → completar SÍ lo debe tomar
        conn.execute("INSERT INTO produccion_checklist "
                     "(produccion_id, producto_nombre, fecha_planeada, item_tipo, descripcion, cantidad_unidades, "
                     " unidad, estado, mee_codigo_asignado) "
                     "VALUES (?,?, date('now','-5 hours'),'decoracion','Sticker deco',50,'uds','listo',?)",
                     (pid, prod, envase))
        conn.commit()
    finally:
        conn.close()

    c = _login(app, "sebastian")
    r = c.post(f"/api/programacion/programar/{pid}/completar",
               json={"dry_run": True}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    tipos = {(m.get("tipo_item") or "").lower() for m in d.get("mees_a_descontar", [])}
    assert "envase_primario" not in tipos, "Finalizar NO debe descontar el envase (va en Envasado)"
    assert "decoracion" in tipos, "Finalizar SÍ debe descontar MEE no-envase (decoración/serigrafía al cierre)"
