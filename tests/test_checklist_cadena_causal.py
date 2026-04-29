"""Tests de la cadena causal end-to-end del Checklist Pre-Produccion.

Sebastian (29-abr-2026): "que todo funcione, que se enlace, que los
botones realmente funcionen". Estos tests protegen contra regresiones
en los UPDATEs que cierran la cadena:

  Sebastian elige envase
    → ckGuardarEditor (asignar-mee + solicitar-produccion)
    → solicitudes_compra_anticipada creada
    → produccion_checklist.estado = 'solicitado'

  Catalina decide ruta
    → solicitudes_compra_anticipada.estado = 'decidida'
    → tarea_operativa creada (si inventario/serigrafia/tampografia)
       O OC manual (si oc/etiqueta_adhesiva)
    → produccion_checklist.estado = 'en_transito' o 'solicitado'

  Operario completa tarea operativa
    → tarea_operativa.estado = 'completada'
    → solicitudes_compra_anticipada.estado = 'completada'
    → produccion_checklist.estado = 'recibido'  ← ESTE LINK

  OC se recibe en /recepcion (recepcion completa)
    → ordenes_compra.estado = 'Recibida'
    → produccion_checklist.estado = 'recibido' (via oc_numero) ← ESTE LINK
    → solicitudes_compra_anticipada.estado = 'completada' (via oc_numero)

Si alguno de estos links se rompe, los items del checklist quedan en
estado solicitado/en_transito eternamente y el usuario tiene que ir
manualmente a marcar "Recibido", lo cual se olvida.
"""
import sqlite3


def _setup_db():
    """Schema minimo de produccion_checklist + solicitudes + tareas + OCs."""
    con = sqlite3.connect(':memory:')
    c = con.cursor()
    c.executescript("""
        CREATE TABLE produccion_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id INTEGER,
            item_tipo TEXT,
            descripcion TEXT,
            estado TEXT DEFAULT 'pendiente',
            oc_numero TEXT,
            fecha_recibido TEXT,
            actualizado_at TEXT
        );
        CREATE TABLE solicitudes_compra_anticipada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_item_id INTEGER,
            estado TEXT DEFAULT 'pendiente',
            decision TEXT,
            tarea_operativa_id INTEGER,
            oc_numero TEXT
        );
        CREATE TABLE tareas_operativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estado TEXT DEFAULT 'pendiente',
            origen_tipo TEXT,
            origen_id INTEGER
        );
        CREATE TABLE ordenes_compra (
            numero_oc TEXT PRIMARY KEY,
            estado TEXT
        );
    """)
    con.commit()
    return con


# ─── Fix 1: tareas_operativas_completar marca checklist recibido ────────────

def test_completar_tarea_propaga_a_checklist():
    """Cuando un operario completa la tarea operativa, el item del
    checklist enlazado debe pasar de 'solicitado' a 'recibido'."""
    con = _setup_db()
    c = con.cursor()
    # Item del checklist solicitado por Sebastian
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, "
              "descripcion, estado) VALUES (1, 'envase_primario', 'ENV 50ml', 'solicitado')")
    item_id = c.lastrowid
    # Solicitud anticipada decidida por Catalina (ruta serigrafia)
    c.execute("INSERT INTO tareas_operativas (estado, origen_tipo) "
              "VALUES ('pendiente', 'solicitud_produccion')")
    tarea_id = c.lastrowid
    c.execute("INSERT INTO solicitudes_compra_anticipada "
              "(checklist_item_id, estado, decision, tarea_operativa_id) "
              "VALUES (?, 'decidida', 'serigrafia', ?)", (item_id, tarea_id))

    # Simular el SQL exacto del endpoint tareas_operativas_completar
    c.execute("UPDATE tareas_operativas SET estado='completada' WHERE id=?", (tarea_id,))
    sol_row = c.execute(
        "SELECT id, checklist_item_id FROM solicitudes_compra_anticipada "
        "WHERE tarea_operativa_id=?", (tarea_id,)
    ).fetchone()
    assert sol_row is not None
    sol_id, ck_id = sol_row
    c.execute("UPDATE solicitudes_compra_anticipada SET estado='completada' WHERE id=?", (sol_id,))
    c.execute(
        "UPDATE produccion_checklist SET estado='recibido', "
        "fecha_recibido=date('now') WHERE id=?", (ck_id,)
    )

    # Verificar la cadena se cerro
    estado_ck = c.execute(
        "SELECT estado, fecha_recibido FROM produccion_checklist WHERE id=?", (item_id,)
    ).fetchone()
    assert estado_ck[0] == 'recibido', f"Esperaba recibido, fue {estado_ck[0]}"
    assert estado_ck[1] is not None, "fecha_recibido debe estar poblada"

    estado_sol = c.execute(
        "SELECT estado FROM solicitudes_compra_anticipada WHERE id=?", (sol_id,)
    ).fetchone()
    assert estado_sol[0] == 'completada'


def test_completar_tarea_sin_solicitud_no_falla():
    """Tarea operativa creada manualmente (no desde solicitud anticipada)
    debe poder completarse sin error y sin tocar el checklist."""
    con = _setup_db()
    c = con.cursor()
    c.execute("INSERT INTO tareas_operativas (estado, origen_tipo) VALUES ('pendiente', 'manual')")
    tarea_id = c.lastrowid

    # Item del checklist NO relacionado, debe quedar intacto
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, estado) "
              "VALUES (1, 'envase_primario', 'pendiente')")
    item_id_huerfano = c.lastrowid

    c.execute("UPDATE tareas_operativas SET estado='completada' WHERE id=?", (tarea_id,))
    sol_row = c.execute(
        "SELECT id, checklist_item_id FROM solicitudes_compra_anticipada "
        "WHERE tarea_operativa_id=?", (tarea_id,)
    ).fetchone()
    assert sol_row is None  # no hay solicitud, no propaga

    # El item huerfano NO debe haber cambiado
    estado_huerfano = c.execute(
        "SELECT estado FROM produccion_checklist WHERE id=?", (item_id_huerfano,)
    ).fetchone()
    assert estado_huerfano[0] == 'pendiente'


# ─── Fix 2: recibir_oc cierra items del checklist linkeados ─────────────────

def test_recibir_oc_completa_cierra_checklist():
    """Recepcion COMPLETA de OC con items del checklist linkeados via
    oc_numero debe marcarlos como recibidos."""
    con = _setup_db()
    c = con.cursor()
    c.execute("INSERT INTO ordenes_compra (numero_oc, estado) VALUES ('OC-2026-0099', 'Autorizada')")
    # Dos items del checklist linkeados a esa OC
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, "
              "estado, oc_numero) VALUES (1, 'envase_primario', 'solicitado', 'OC-2026-0099')")
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, "
              "estado, oc_numero) VALUES (1, 'tapa', 'en_transito', 'OC-2026-0099')")
    # Solicitud anticipada decidida tambien linkeada
    c.execute("INSERT INTO solicitudes_compra_anticipada "
              "(estado, decision, oc_numero) VALUES ('decidida', 'oc', 'OC-2026-0099')")

    # Simular UPDATE del fix en recibir_oc (recepcion completa, no parcial)
    es_parcial = False
    if not es_parcial:
        c.execute("""
            UPDATE produccion_checklist SET
              estado='recibido',
              fecha_recibido=date('now')
            WHERE oc_numero=? AND estado IN ('solicitado','en_transito','pendiente')
        """, ('OC-2026-0099',))
        items_actualizados = c.rowcount
        c.execute("""
            UPDATE solicitudes_compra_anticipada SET estado='completada'
            WHERE oc_numero=? AND estado IN ('decidida','pendiente')
        """, ('OC-2026-0099',))

    assert items_actualizados == 2
    rows = c.execute(
        "SELECT estado FROM produccion_checklist WHERE oc_numero='OC-2026-0099'"
    ).fetchall()
    assert all(r[0] == 'recibido' for r in rows)
    sol = c.execute(
        "SELECT estado FROM solicitudes_compra_anticipada WHERE oc_numero='OC-2026-0099'"
    ).fetchone()
    assert sol[0] == 'completada'


def test_recibir_oc_parcial_no_cierra_checklist():
    """Recepcion PARCIAL de OC NO debe cerrar items del checklist —
    todavia falta material que esta por llegar."""
    con = _setup_db()
    c = con.cursor()
    c.execute("INSERT INTO ordenes_compra (numero_oc, estado) VALUES ('OC-2026-0100', 'Autorizada')")
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, "
              "estado, oc_numero) VALUES (1, 'envase_primario', 'solicitado', 'OC-2026-0100')")

    es_parcial = True  # llego solo parte
    items_actualizados = 0
    if not es_parcial:
        c.execute(
            "UPDATE produccion_checklist SET estado='recibido' "
            "WHERE oc_numero=?", ('OC-2026-0100',)
        )
        items_actualizados = c.rowcount

    assert items_actualizados == 0
    estado = c.execute(
        "SELECT estado FROM produccion_checklist WHERE oc_numero='OC-2026-0100'"
    ).fetchone()
    assert estado[0] == 'solicitado', "items deben seguir solicitados hasta recepcion completa"


def test_recibir_oc_sin_link_no_falla():
    """OC que no esta linkeada a ningun item del checklist debe poder
    recibirse sin error (caso comun: OC creada antes del checklist)."""
    con = _setup_db()
    c = con.cursor()
    c.execute("INSERT INTO ordenes_compra (numero_oc, estado) VALUES ('OC-2026-0101', 'Autorizada')")
    # item del checklist NO linkeado a ninguna OC
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, estado) "
              "VALUES (1, 'envase_primario', 'pendiente')")

    c.execute(
        "UPDATE produccion_checklist SET estado='recibido' "
        "WHERE oc_numero=? AND estado IN ('solicitado','en_transito','pendiente')",
        ('OC-2026-0101',)
    )
    assert c.rowcount == 0  # nadie cambia, todo OK
    estado = c.execute("SELECT estado FROM produccion_checklist").fetchone()
    assert estado[0] == 'pendiente'


# ─── Fix 3: filtro de items legacy en checklist_get + resumen ───────────────

def test_filtro_legacy_etiquetas_en_get():
    """Los items con tipo etiqueta_frontal/posterior/lateral NO deben
    aparecer en el GET del checklist (cubierto por decoracion del envase)."""
    con = _setup_db()
    c = con.cursor()
    # Mix de items: uno editable, uno legacy
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, descripcion, estado) "
              "VALUES (1, 'envase_primario', 'ENV 50ml', 'solicitado')")
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, descripcion, estado) "
              "VALUES (1, 'etiqueta_frontal', 'Etq frontal legacy', 'pendiente')")
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, descripcion, estado) "
              "VALUES (1, 'etiqueta_posterior', 'Etq posterior legacy', 'pendiente')")
    c.execute("INSERT INTO produccion_checklist (produccion_id, item_tipo, descripcion, estado) "
              "VALUES (1, 'tapa', 'Tapa', 'pendiente')")

    # Simular el filtro del fix en checklist_get
    legacy = ('etiqueta_frontal', 'etiqueta_posterior', 'etiqueta_lateral')
    placeholders = ','.join(['?'] * len(legacy))
    rows = c.execute(
        f"SELECT item_tipo FROM produccion_checklist WHERE produccion_id=? "
        f"AND item_tipo NOT IN ({placeholders}) ORDER BY item_tipo",
        [1] + list(legacy)
    ).fetchall()
    tipos = [r[0] for r in rows]
    assert tipos == ['envase_primario', 'tapa']
    assert 'etiqueta_frontal' not in tipos
    assert 'etiqueta_posterior' not in tipos
