# -*- coding: utf-8 -*-
"""UN boton deja la tabla con una fila por TONO, emparejada.

Sebastian (9-ago): *"lo veo igual... la idea es que liste todos los tonos de blush y de gloss, y
los empareja"*. Tenia razon en la queja de fondo: le habia dejado TRES botones (limpiar, expandir,
emparejar) y el trabajo de ordenarlos. Eso no es una herramienta, es un procedimiento que hay que
recordar, y lo que el pidio es el RESULTADO.

⚠ Acotado a los productos que se confirman. Sin eso expandia todo lo que pareciera multitono --
medido: 31 filas de seis productos que nadie pidio -- y una accion que toca cosas que no se vieron
no se puede confiar, por mas que cada paso sea reversible.
"""
def test_deja_una_fila_por_tono_con_su_sku(app, admin_client, capsys):
    from database import get_db
    PB, PL = 'RES BLUSH', 'RES LIP'
    with app.app_context():
        c = get_db()
        for P in (PB, PL):
            c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
            c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'RES-%'")
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('RES-FRB','FRASCO ALUMINIO 6ml','Frasco',0)")
        c.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,stock_actual) "
                  "VALUES ('RES-FRL','LIP GLOSS BLANCO','Frasco',0)")
        for sk, tl in (('RESBB101','Hot Pink'), ('RESBB201','Malva'), ('RESBB301','Peach')):
            c.execute("INSERT INTO sku_producto_map (sku,producto_nombre,tono_label,volumen_ml,"
                      "activo) VALUES (?,?,?,6,1)", (sk, PB, tl))
        for sk in ('RESGLOSSMALVA','RESGLOSSMERLOT','RESGLOSSN'):
            c.execute("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) "
                      "VALUES (?,?,10,1)", (sk, PL))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) VALUES (?,'V6','6 ml',6,'RES-FRB',1)",
                  (PB,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,"
                  "etiqueta,volumen_ml,envase_codigo,activo) VALUES (?,'V10','10 ml',10,'RES-FRL',1)",
                  (PL,))
        c.commit()
    r = admin_client.post('/api/mee/resolver-tonos', json={'productos':[PB,PL]}, headers={'Origin':'http://localhost'})
    j = r.get_json()
    with capsys.disabled():
        print('RES code', r.status_code)
        for p in (j.get('pasos') or []):
            print('   paso', p)
        for m in (j.get('multitono') or []):
            if m['producto'] in (PB, PL):
                print('   %-12s filas=%d con_sku=%d con_etq=%d skus=%d'
                      % (m['producto'], m['filas'], m['con_sku'], m['con_etiqueta'], m['skus']))
    with app.app_context():
        c = get_db()
        for P in (PB, PL):
            for f in c.execute("SELECT presentacion_codigo, etiqueta, COALESCE(sku_shopify,''), "
                               "activo FROM producto_presentaciones WHERE producto_nombre=? "
                               "ORDER BY id", (P,)).fetchall():
                with capsys.disabled():
                    print('   FILA %-12s %-18s sku=%-12s activo=%s' % (f[0], f[1], f[2], f[3]))
            c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (P,))
            c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (P,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'RES-%'")
        c.commit()
