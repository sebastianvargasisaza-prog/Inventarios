"""Audit Abastecimiento 1-jun-2026: el anti-duplicación (_pendiente_en_compras_g)
debe ser case-insensitive en codigo_mp y contar SOLs 'En revision', para no
sub-contar lo ya pedido (que llevaría a sobre-orden)."""
import os, sqlite3


def test_pendiente_case_insensitive_y_en_revision(app, db_clean):
    with app.app_context():
        from database import get_db
        from blueprints.compras import _pendiente_en_compras_g, _pendiente_en_compras_bulk
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'SOLDEDUP%'")
        c.execute("DELETE FROM solicitudes_compra_items WHERE numero LIKE 'SOLDEDUP%'")
        # SOL 'Pendiente' con codigo en MAYÚSCULAS, sin OC
        c.execute("INSERT INTO solicitudes_compra (numero, fecha, estado) VALUES ('SOLDEDUP-1','2026-06-01','Pendiente')")
        c.execute("INSERT INTO solicitudes_compra_items (numero, codigo_mp, cantidad_g) VALUES ('SOLDEDUP-1','MPDEDUP',1000)")
        # SOL 'En revision' del mismo MP
        c.execute("INSERT INTO solicitudes_compra (numero, fecha, estado) VALUES ('SOLDEDUP-2','2026-06-01','En revision')")
        c.execute("INSERT INTO solicitudes_compra_items (numero, codigo_mp, cantidad_g) VALUES ('SOLDEDUP-2','MPDEDUP',500)")
        conn.commit()

        # consulta en minúsculas → debe encontrar ambas (case-insensitive) = 1500
        tot = _pendiente_en_compras_g(c, 'mpdedup')
        assert abs(tot - 1500.0) < 0.1, f"esperado 1500 (case-insensitive + En revision), got {tot}"

        # bulk: la clave normalizada UPPER(TRIM) debe sumar 1500
        bulk = _pendiente_en_compras_bulk(c)
        assert abs(bulk.get('MPDEDUP', 0) - 1500.0) < 0.1, bulk
