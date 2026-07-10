def test_recibir_oc_item_sin_codigo_no_500(admin_client):
    """[500 prod · 10-jul · workflow M80] Recibir una OC que tiene un ítem con codigo_mp VACÍO
    disparaba el trigger material_id-requerido → INSERT COA fallaba → except lo tomaba como 'faltan
    columnas' → reintentaba INSERT legacy SIN try → mismo trigger → 500. Ahora se saltea (como MEE)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo,tipo_material,proveedor) VALUES ('ECMPX','ok',1,'MP','P')")
        c.execute("INSERT INTO ordenes_compra (numero_oc,fecha,proveedor,estado,valor_total,creado_por) VALUES ('ECOCX','2026-07-01','P','Autorizada',1000,'sebastian')")
        c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES ('ECOCX','ECMPX','ok',5000,10,50000)")
        c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES ('ECOCX','','sin codigo',3000,5,15000)")
        conn.commit()
    body = {'items_recepcion': [
        {'codigo_mp': 'ECMPX', 'cantidad_recibida': 5000, 'lote': 'L-ECX', 'lote_proveedor': 'LP', 'fecha_vencimiento': '2027-12-31', 'estanteria': 'A'},
        {'codigo_mp': '', 'cantidad_recibida': 3000, 'lote': 'L-ECX2', 'lote_proveedor': 'LP2', 'fecha_vencimiento': '2027-12-31'},
    ], 'receptor_nombre': 'sebastian', 'forzar_excepciones': True}
    r = admin_client.post('/api/ordenes-compra/ECOCX/recibir', json=body)
    assert r.status_code in (200, 201), (r.status_code, r.get_data(as_text=True)[:200])
    assert r.get_json().get('ingresos') == 1  # solo el ítem con código
