"""Transparencia "no jala lo que hay en bodega" (2-jun-2026).

Cuando producción no puede fabricar, el faltante debe decir cuánto stock del
MISMO código está RETENIDO (cuarentena, etc) — el caso "bodega muestra 600g
pero producción ve 17.5g porque 583g están en cuarentena sin liberar".
"""
import os
import sqlite3


def _conn():
    return sqlite3.connect(os.environ["DB_PATH"])


def test_validar_reporta_retenido_cuarentena(app, db_clean):
    from blueprints.programacion import _validar_stock_para_produccion
    cod = "MPTRANSPCUAR"
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo) "
            "VALUES (?,?,1)", (cod, "MP Transparencia"))
        # 17.5g disponibles (sin estado) + 600g en CUARENTENA
        cur.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote) "
            "VALUES (?,?,?,?,?,?)", (cod, "MP Transparencia", 17.5, "Entrada", "2026-06-01", "L-OK"))
        cur.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
            "VALUES (?,?,?,?,?,?,?)", (cod, "MP Transparencia", 600, "Entrada", "2026-06-01", "L-CUAR", "CUARENTENA"))
        conn.commit()

        faltantes = _validar_stock_para_produccion(cur, [
            {"codigo_mp": cod, "nombre": "MP Transparencia", "cantidad_g": 140}
        ])
    finally:
        conn.close()

    assert len(faltantes) == 1, faltantes
    f = faltantes[0]
    assert abs(f["disponible_g"] - 17.5) < 0.01, f
    assert abs(f["falta_g"] - 122.5) < 0.01, f
    # debe reportar los 600g retenidos en cuarentena
    assert abs(f["retenido_g"] - 600) < 0.01, f
    assert "CUARENTENA" in (f.get("retenido_por_estado") or {}), f

    # cleanup
    conn = _conn()
    try:
        conn.execute("DELETE FROM movimientos WHERE material_id=?", (cod,))
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        conn.commit()
    finally:
        conn.close()
