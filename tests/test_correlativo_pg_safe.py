"""Audit ultracode 7-jul (M45) · siguiente_correlativo NO revienta con un número de sufijo no numérico
(lo que hacía CAST(SUBSTR(...) AS INTEGER) en PG → 500 en toda creación de SOL/OS del año) y devuelve
el correlativo correcto ignorando el sufijo."""
import os
import sqlite3


def test_siguiente_correlativo_ignora_sufijo_no_numerico(app, db_clean):
    from audit_helpers import siguiente_correlativo
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'SOL-2099-%'")
    # una SOL con sufijo no numérico (el caso que CAST reventaba en PG) + una normal mayor
    db.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante) VALUES "
               "('SOL-2099-0215-1', '2099-01-01', 'Pendiente', 'test')")
    db.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante) VALUES "
               "('SOL-2099-0300', '2099-01-01', 'Pendiente', 'test')")
    db.commit()
    c = db.cursor()
    # NO debe lanzar (el CAST sí lanzaría en PG) y debe devolver max(215,300)+1 = 301
    nxt = siguiente_correlativo(c, 'solicitudes_compra', 'numero', 'SOL-2099-')
    db.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'SOL-2099-%'")
    db.commit(); db.close()
    assert nxt == 301, ("debe ignorar el sufijo y devolver max+1", nxt)


def test_siguiente_correlativo_vacio_es_1(app, db_clean):
    from audit_helpers import siguiente_correlativo
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'ZZZ-2099-%'")
    db.commit(); c = db.cursor()
    nxt = siguiente_correlativo(c, 'solicitudes_compra', 'numero', 'ZZZ-2099-')
    db.close()
    assert nxt == 1, ("sin existentes → 1", nxt)
