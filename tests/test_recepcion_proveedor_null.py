def test_recepcion_mp_proveedor_null_pg(admin_client):
    """[500 en prod · 10-jul] Recibir una MP cuyo maestro tiene proveedor NULL + precio, sin proveedor
    en el request → antes '' or None = None → INSERT precios_mp_historico con proveedor NULL → 500 en PG
    (NOT NULL). Ahora coerce a '' → recepción OK."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material,proveedor) VALUES ('MPNULLPR','X NULLPROV',1,'MP',NULL)")
        conn.commit()
    r = admin_client.post('/api/recepcion', json={'codigo_mp': 'MPNULLPR', 'cantidad': 1000, 'lote': 'RNULL1', 'precio_kg': 50000, 'cuarentena': True})
    assert r.status_code in (200, 201), (r.status_code, r.get_data(as_text=True)[:200])
    # el histórico de precios quedó con proveedor '' (no NULL)
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        row = c.execute("SELECT proveedor FROM precios_mp_historico WHERE codigo_mp='MPNULLPR'").fetchone()
        assert row is not None and row[0] == ''
