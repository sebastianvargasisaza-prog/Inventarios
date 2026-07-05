"""Sebastián 4-jul · P1-C (audit) · el motor de COMPRA no debe pedir MP de productos DESCONTINUADOS.

_compute_mp_deficit_aggregated (alimenta /generar-oc /regenerar-oc /mps-deficit) usaba _get_formulas SIN
filtro activo → un producto activo=0 con un lote futuro huérfano (migs 335/336 no cancelan produccion_
programada) seguía generando demanda de MP → sobre-compra. La pantalla (abastecimiento_consumo_horizontes)
SÍ filtra activo=1 → divergían. Fix: filtrar la copia local de formulas en el motor de compra.
"""
import os
import sqlite3


def _seed(db, prod, activo, mp_id):
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,))
    db.execute("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (prod,))
    db.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
               "VALUES (?, ?, ?, 1)", (mp_id, "Material " + mp_id, "INCI " + mp_id))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, ?)",
               (prod, activo))
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
               "VALUES (?,?,?,50,5000)", (prod, mp_id, "Material " + mp_id))
    # lote futuro (dentro del horizonte 90d) · pendiente · sin descuento · Fijo
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
               "VALUES (?, date('now','+30 days','-5 hours'), 1, 'pendiente', 'eos_plan', 10)", (prod,))


def test_compra_excluye_producto_descontinuado(app, db_clean):
    from blueprints.programacion import _compute_mp_deficit_aggregated
    db = sqlite3.connect(os.environ["DB_PATH"])
    _seed(db, "PROD-COMPRA-ACTIVO", 1, "MPACTIVOC")
    _seed(db, "PROD-COMPRA-DESCONT", 0, "MPDESCONTC")
    db.commit()
    db.close()

    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        res = _compute_mp_deficit_aggregated(conn, days_ahead=90)
    finally:
        conn.close()

    prods_en_compra = set()
    for mid, info in (res or {}).items():
        for p in info.get("productos", []):
            prods_en_compra.add(p)

    # El descontinuado NO debe aparecer en ninguna necesidad de MP
    assert "PROD-COMPRA-DESCONT" not in prods_en_compra, (
        "un producto descontinuado (activo=0) NO debe generar compra de MP", prods_en_compra)
    # El activo SÍ debe aparecer (control · confirma que el test ejercita el motor)
    assert "PROD-COMPRA-ACTIVO" in prods_en_compra, (
        "el producto activo debería generar demanda de MP (control del test)", prods_en_compra)


def test_compra_no_borra_activa_con_case_dup(app, db_clean):
    """P0 (Fable 5) · caso BLUSH BALM: una fórmula ACTIVA que comparte UPPER con una DUP inactiva
    ('Blush Balm' activo=0 + 'BLUSH BALM' activo=1) NO debe ser borrada del motor de compra."""
    from blueprints.programacion import _compute_mp_deficit_aggregated
    db = sqlite3.connect(os.environ["DB_PATH"])
    # dup inactiva (case distinto) SIN producción · la ACTIVA con producción
    _seed(db, "Blush Test Dup", 0, "MPBLUSHDUP")
    _seed(db, "BLUSH TEST DUP", 1, "MPBLUSHDUP")   # mismo UPPER, activa, misma MP
    db.execute("DELETE FROM produccion_programada WHERE producto=?", ("Blush Test Dup",))  # la inactiva sin prod
    db.commit()
    db.close()

    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        res = _compute_mp_deficit_aggregated(conn, days_ahead=90)
    finally:
        conn.close()
    prods = {p for info in (res or {}).values() for p in info.get("productos", [])}
    # la ACTIVA (mayúsculas, con producción) debe generar demanda de MP · NO fue borrada por el UPPER-dup
    assert "BLUSH TEST DUP" in prods, (
        "la fórmula ACTIVA no debe borrarse por compartir UPPER con una dup inactiva", prods)
