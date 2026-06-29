"""Auditoría Shopify→Necesidades (27-jun) · el SKU se cruza case-insensitive entre el motor del calendario
(auto_plan) y los datos de Shopify (igual que Necesidades) · antes case-sensitive daba velocidad 0."""
import os
import json
import sqlite3


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_ventas_diarias_sku_case_insensitive(app, db_clean):
    # orden Shopify (no cancelada, pagada) con el SKU en MINÚSCULA
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TCASE1','','paid',?,5,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'abc-30', 'qty': 5}]),))
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _ventas_diarias_por_sku
        c = get_db()
        # el motor del calendario busca el SKU en MAYÚSCULA → debe encontrar la venta (case-insensitive)
        ventas = _ventas_diarias_por_sku(c, 'ABC-30', dias=30)
    total = sum(q for _, q in ventas)
    assert total == 5, ('SKU case-insensitive falló · velocidad quedaría en 0', ventas)


def _login(app, user="sebastian"):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def test_diag_detecta_mapeo_zombi(app, db_clean):
    # SKU mapeado a un producto que NO existe en formula_headers (zombi) + una venta
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('ZOMBI-30','XX NO EXISTE EN FORMULAS XX',1)")
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TZ1','','paid',?,3,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'ZOMBI-30', 'qty': 3}]),))
    c = _login(app)
    r = c.get("/api/plan/diagnostico-shopify")
    assert r.status_code == 200, r.data
    d = r.get_json()
    zombi = [x for x in d['por_sku'] if x['sku'] == 'ZOMBI-30']
    assert zombi and zombi[0]['estado'] == 'MAPEADO_SIN_FORMULA', (zombi, d['reconciliacion'])
    assert d['reconciliacion']['n_skus_mapeo_zombi'] >= 1, d['reconciliacion']


def _q1(sql, params=()):
    import os as _o, sqlite3 as _s
    conn = _s.connect(_o.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_job_alerta_skus_sin_mapear(app, db_clean):
    # orden con un SKU NUEVO sin mapear (huérfano) que vende
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TALERT1','','paid',?,7,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'NUEVO-SIN-MAPEAR-99', 'qty': 7}]),))
    from blueprints.auto_plan_jobs import job_alerta_skus_sin_mapear
    job_alerta_skus_sin_mapear(app)
    n = _q1("SELECT COUNT(*) FROM notificaciones_app WHERE destinatario='sebastian' "
            "AND tipo='shopify_sku_sin_mapear'")[0]
    assert n >= 1, 'no se creó el aviso de SKU sin mapear'


def test_mig294_limpiador_iluminador_remapea(app, db_clean):
    # SKU mapeado al nombre VIEJO (kójico) + la fórmula con el nombre NUEVO (iluminador)
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('Limpiador Iluminador',1,1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) "
          "VALUES ('LIMPILU-30','Limpiador Ácido Kójico',1)")
    _upd = ("UPDATE sku_producto_map SET producto_nombre = ("
            " SELECT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1"
            " AND LOWER(producto_nombre) LIKE '%iluminador%' AND LOWER(producto_nombre) LIKE '%limpiador%'"
            " ORDER BY id LIMIT 1)"
            " WHERE (LOWER(producto_nombre) LIKE '%kojico%' OR LOWER(producto_nombre) LIKE '%kójico%')"
            " AND EXISTS (SELECT 1 FROM formula_headers WHERE COALESCE(activo,1)=1"
            " AND LOWER(producto_nombre) LIKE '%iluminador%' AND LOWER(producto_nombre) LIKE '%limpiador%')")
    _exec(_upd)
    n = _q1("SELECT producto_nombre FROM sku_producto_map WHERE sku='LIMPILU-30'")[0]
    assert 'luminador' in (n or '').lower(), ('el SKU no se re-apuntó a Iluminador', n)


def test_mig295_gloss_y_hidrabalance(app, db_clean):
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) "
          "VALUES ('GLOSSPEACH','SERUM VOLUMINIZADOR DE LABIOS PEPTIDOS',1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('GLOSSMALVA','Brillo Malva',1)")
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('HYDRA BALANCE',1,1)")
    _g = ("UPDATE sku_producto_map SET producto_nombre = ("
          " SELECT producto_nombre FROM sku_producto_map WHERE UPPER(TRIM(sku))='GLOSSPEACH' LIMIT 1)"
          " WHERE UPPER(TRIM(sku)) IN ('GLOSSMALVA','GLOSSMERLOT')"
          " AND EXISTS (SELECT 1 FROM sku_producto_map WHERE UPPER(TRIM(sku))='GLOSSPEACH')")
    _h = ("INSERT INTO sku_producto_map (sku, producto_nombre, activo)"
          " SELECT 'HYDBALANCE', producto_nombre, 1 FROM formula_headers"
          " WHERE COALESCE(activo,1)=1 AND LOWER(producto_nombre) LIKE '%balance%'"
          " AND (LOWER(producto_nombre) LIKE '%hydra%' OR LOWER(producto_nombre) LIKE '%hidra%')"
          " AND NOT EXISTS (SELECT 1 FROM sku_producto_map WHERE UPPER(TRIM(sku))='HYDBALANCE')"
          " ORDER BY id LIMIT 1")
    _exec(_g)
    _exec(_h)
    assert _q1("SELECT producto_nombre FROM sku_producto_map WHERE sku='GLOSSMALVA'")[0] == \
        'SERUM VOLUMINIZADOR DE LABIOS PEPTIDOS', 'gloss no re-apuntó'
    assert 'balance' in (_q1("SELECT producto_nombre FROM sku_producto_map WHERE sku='HYDBALANCE'")[0] or '').lower(), \
        'Hidrabalance no se mapeó'


def test_mig296_blush_consolida(app, db_clean):
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('BLUSH BALM',1,1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('BBTEST401','BLUSH BÁLSAMO',1)")
    _u = ("UPDATE sku_producto_map SET producto_nombre = ("
          " SELECT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1"
          " AND UPPER(TRIM(producto_nombre))='BLUSH BALM' LIMIT 1)"
          " WHERE UPPER(TRIM(producto_nombre)) LIKE '%BLUSH%'"
          " AND (UPPER(TRIM(producto_nombre)) LIKE '%BALSAMO%' OR UPPER(TRIM(producto_nombre)) LIKE '%BÁLSAMO%')"
          " AND EXISTS (SELECT 1 FROM formula_headers WHERE COALESCE(activo,1)=1"
          " AND UPPER(TRIM(producto_nombre))='BLUSH BALM')")
    _exec(_u)
    assert _q1("SELECT producto_nombre FROM sku_producto_map WHERE sku='BBTEST401'")[0] == 'BLUSH BALM', \
        'no consolidó a BLUSH BALM'


def test_desglose_tonos_usa_volumen_sku_producto_map(app, db_clean):
    # M44 · el desglose por referencia debe usar el volumen canónico de sku_producto_map.volumen_ml
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('PROD DESG TEST',1,1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES ('PDT-30','PROD DESG TEST',30,1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES ('PDT-15','PROD DESG TEST',15,1)")
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TDESG1','','paid',?,10,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'PDT-30', 'qty': 6}, {'sku': 'PDT-15', 'qty': 4}]),))
    c = _login(app)
    r = c.get('/api/plan/desglose-tonos?producto=PROD%20DESG%20TEST')
    assert r.status_code == 200, r.data
    d = r.get_json()
    mls = {it['sku']: it['ml_unidad'] for it in d['items']}
    assert mls.get('PDT-30') == 30 and mls.get('PDT-15') == 15, ('ml no salió de sku_producto_map', mls)


def test_mig297_envases_normalizados_cargados(app, db_clean):
    # los 57 envases del Excel deben quedar ACTIVOS en maestro_mee (reemplazan a los viejos)
    n = _q1("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND (codigo LIKE 'FR-%' "
            "OR codigo LIKE 'IMP-%' OR codigo LIKE 'ETQ-%' OR codigo LIKE 'CJA-%')")[0]
    assert n >= 50, ('no se cargaron los envases normalizados activos', n)
    assert _q1("SELECT estado FROM maestro_mee WHERE codigo='FR-GLOSS-10-PEACH'")[0] == 'Activo', 'gloss peach no activo'
    assert _q1("SELECT estado FROM maestro_mee WHERE codigo='CJA-TRX'")[0] == 'Activo', 'caja TRX no activa'


def test_mig298_envase_foto_partes(app, db_clean):
    # imagen_url en maestro_mee + tabla mee_partes (Fase 1 rediseño envases)
    _exec("UPDATE maestro_mee SET imagen_url='http://x/foto.jpg' WHERE codigo='CJA-TRX'")
    assert _q1("SELECT imagen_url FROM maestro_mee WHERE codigo='CJA-TRX'")[0] == 'http://x/foto.jpg', 'imagen_url no quedó'
    _exec("INSERT INTO mee_partes (mee_codigo, parte_codigo, cantidad) VALUES ('FR-VIDRIOOPAL-30','TAP-X',2)")
    assert _q1("SELECT cantidad FROM mee_partes WHERE mee_codigo='FR-VIDRIOOPAL-30' AND parte_codigo='TAP-X'")[0] == 2, 'parte no quedó'


def test_mig299_envases_stock_limpio(app, db_clean):
    # los 57 envases normalizados quedan con stock 0 y sin mínimo falso (no disparan bajo-mínimo)
    r = _q1("SELECT stock_actual, stock_minimo FROM maestro_mee WHERE codigo='CJA-TRX'")
    assert r[0] == 0 and r[1] == 0, ('stock/mínimo placeholder no limpiado', r)


def test_mig300_recepcion_mee_columnas(app, db_clean):
    # columnas de recepción MP-style en movimientos_mee (proveedor/zona/precio/fecha venc/OC/factura)
    _exec("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,proveedor,zona,precio_unitario,"
          "fecha_vencimiento,oc_numero,factura_numero) "
          "VALUES ('FR-VIDRIOOPAL-30','Entrada',10,'Cafarcol','Zona A',1200,'2027-01-01','OC-1','FAC-1')")
    r = _q1("SELECT proveedor, zona, precio_unitario, oc_numero, factura_numero FROM movimientos_mee "
            "WHERE mee_codigo='FR-VIDRIOOPAL-30' AND oc_numero='OC-1'")
    assert r[0] == 'Cafarcol' and r[1] == 'Zona A' and float(r[2]) == 1200 and r[3] == 'OC-1' and r[4] == 'FAC-1', \
        ('columnas de recepción MEE no funcionan', r)


def test_mee_crear_con_partes(app, db_clean):
    # el wizard "Material nuevo" crea el envase + sus partes (gotero/plegadiza) en mee_partes
    from .conftest import csrf_headers
    c = _login(app)
    r = c.post('/api/mee', json={'codigo': 'FR-TESTPARTES-30', 'descripcion': 'test partes',
                                 'categoria': 'Frasco',
                                 'partes': [{'codigo': 'GOT-X', 'cantidad': 1},
                                            {'codigo': 'CJA-X', 'cantidad': 2}]},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    n = _q1("SELECT COUNT(*) FROM mee_partes WHERE mee_codigo='FR-TESTPARTES-30'")[0]
    assert n == 2, ('las partes del empaque no se guardaron', n)
    # y el endpoint de partes las devuelve (para la recepción múltiple)
    rp = c.get('/api/mee/partes?codigo=FR-TESTPARTES-30')
    assert rp.status_code == 200, rp.data
    assert len(rp.get_json().get('partes', [])) == 2, rp.data


def test_mee_cuarentena_calidad(app, db_clean):
    # recibir un envase → entra en CUARENTENA · Calidad lo libera → VIGENTE
    from .conftest import csrf_headers
    c = _login(app)
    c.post('/api/mee', json={'codigo': 'FR-CUARTEST-30', 'descripcion': 'cuar test', 'categoria': 'Frasco'},
           headers=csrf_headers())
    r = c.post('/api/mee/movimiento', json={'tipo': 'Entrada', 'codigo': 'FR-CUARTEST-30', 'cantidad': 10,
                                            'unidad': 'und'}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    est = _q1("SELECT estado FROM movimientos_mee WHERE mee_codigo='FR-CUARTEST-30' AND tipo='Entrada' "
              "ORDER BY id DESC LIMIT 1")[0]
    assert est == 'CUARENTENA', ('la recepción no entró en cuarentena', est)
    pend = c.get('/api/mee/cuarentena-pendientes').get_json()['pendientes']
    mov = [p for p in pend if p['codigo'] == 'FR-CUARTEST-30']
    assert mov, 'no aparece en cuarentena pendientes'
    rl = c.post('/api/mee/cuarentena/' + str(mov[0]['id']) + '/liberar', headers=csrf_headers())
    assert rl.status_code == 200, rl.data
    est2 = _q1("SELECT estado FROM movimientos_mee WHERE id=?", (mov[0]['id'],))[0]
    assert est2 == 'VIGENTE', ('Calidad no liberó la cuarentena', est2)


def test_mee_calificar_material_nuevo(app, db_clean):
    # material nuevo entra "por calificar" (Nivel 1) · Calidad lo califica con el checklist completo
    from .conftest import csrf_headers
    c = _login(app)
    c.post('/api/mee', json={'codigo': 'FR-CALIFTEST-30', 'descripcion': 'calif test', 'categoria': 'Frasco'},
           headers=csrf_headers())
    assert _q1("SELECT calificado FROM maestro_mee WHERE codigo='FR-CALIFTEST-30'")[0] == 0, 'nuevo debe entrar por calificar'
    pend = c.get('/api/mee/por-calificar').get_json()['pendientes']
    assert any(p['codigo'] == 'FR-CALIFTEST-30' for p in pend), 'no aparece en por-calificar'
    # sin los 4 items → rechaza
    r0 = c.post('/api/mee/calificar', json={'codigo': 'FR-CALIFTEST-30', 'detalle': {'capacidad': True}},
                headers=csrf_headers())
    assert r0.status_code == 400, r0.data
    # checklist completo → calificado
    r = c.post('/api/mee/calificar', json={'codigo': 'FR-CALIFTEST-30',
               'detalle': {'capacidad': True, 'material': True, 'medidas': True, 'documentos': True}},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _q1("SELECT calificado FROM maestro_mee WHERE codigo='FR-CALIFTEST-30'")[0] == 1, 'no quedó calificado'


def test_mee_gate_cuarentena_no_cuenta_produccion(app, db_clean):
    # GATE: el stock en CUARENTENA no cuenta para producción (_get_mee_stock); al liberar, sí
    import sqlite3
    import os
    from blueprints.programacion import _get_mee_stock
    _exec("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,estado) VALUES ('FR-GATE-30','Entrada',100,'CUARENTENA')")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        st = _get_mee_stock(conn)
    finally:
        conn.close()
    assert st.get('FR-GATE-30', 0) == 0, ('cuarentena no debe contar para producción', st.get('FR-GATE-30'))
    _exec("UPDATE movimientos_mee SET estado='VIGENTE' WHERE mee_codigo='FR-GATE-30'")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        st2 = _get_mee_stock(conn)
    finally:
        conn.close()
    assert st2.get('FR-GATE-30', 0) == 100, ('liberado debe contar', st2.get('FR-GATE-30'))


def test_mee_shopify_fotos_bulk(app, db_clean):
    # el bulk trae la foto del producto Shopify que matchea al envase sin foto
    from .conftest import csrf_headers
    c = _login(app)
    _exec("INSERT INTO formula_headers (producto_nombre, imagen_url, activo) VALUES "
          "('SUERO DE NIACINAMIDA FOTOTEST','http://x/nia.jpg',1)")
    _exec("INSERT INTO maestro_mee (codigo,descripcion,categoria,estado,imagen_url,stock_actual,stock_minimo,unidad,fecha_creacion) "
          "VALUES ('FR-NIAFOTO-30','SUERO NIACINAMIDA FOTOTEST 30ml','Frasco','Activo','',0,0,'und','')")
    r = c.post('/api/mee/shopify-fotos-bulk', headers=csrf_headers())
    assert r.status_code == 200, r.data
    img = _q1("SELECT imagen_url FROM maestro_mee WHERE codigo='FR-NIAFOTO-30'")[0]
    assert img == 'http://x/nia.jpg', ('no trajo la foto de Shopify por match', img)


def test_mee_set_imagen(app, db_clean):
    # subir/setear la foto de un envase desde la bodega
    from .conftest import csrf_headers
    c = _login(app)
    _exec("INSERT INTO maestro_mee (codigo,descripcion,categoria,estado,imagen_url,stock_actual,stock_minimo,unidad,fecha_creacion) "
          "VALUES ('FR-SETIMG-30','test','Frasco','Activo','',0,0,'und','')")
    r = c.post('/api/mee/set-imagen', json={'codigo': 'FR-SETIMG-30', 'imagen_url': 'data:image/jpeg;base64,ZZZ'},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _q1("SELECT imagen_url FROM maestro_mee WHERE codigo='FR-SETIMG-30'")[0] == 'data:image/jpeg;base64,ZZZ'


def test_mee_recodificar(app, db_clean):
    # re-codificar un envase con la lógica del wizard · arrastra stock + referencias
    from .conftest import csrf_headers
    c = _login(app)
    _exec("INSERT INTO maestro_mee (codigo,descripcion,categoria,estado,stock_actual,stock_minimo,unidad,fecha_creacion) "
          "VALUES ('FR-OLDCODE-30','test','Frasco','Activo',0,0,'und','')")
    _exec("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad) VALUES ('FR-OLDCODE-30','Entrada',5)")
    r = c.post('/api/mee/recodificar', json={'codigo_viejo': 'FR-OLDCODE-30', 'codigo_nuevo': 'FR-VID-NIA-30'},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _q1("SELECT COUNT(*) FROM maestro_mee WHERE codigo='FR-VID-NIA-30'")[0] == 1, 'no renombró el maestro'
    assert _q1("SELECT COUNT(*) FROM maestro_mee WHERE codigo='FR-OLDCODE-30'")[0] == 0, 'quedó el viejo'
    assert _q1("SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo='FR-VID-NIA-30'")[0] == 1, 'no arrastró movimientos'
    # no permite chocar con un código existente
    _exec("INSERT INTO maestro_mee (codigo,descripcion,categoria,estado) VALUES ('FR-EXISTE-30','x','Frasco','Activo')")
    r2 = c.post('/api/mee/recodificar', json={'codigo_viejo': 'FR-VID-NIA-30', 'codigo_nuevo': 'FR-EXISTE-30'},
                headers=csrf_headers())
    assert r2.status_code == 409, r2.data


def test_mig305_saldo_inicial_excel(app):
    # el inventario real del Excel se cargó como movimiento de saldo inicial (se muestra en la bodega)
    r = _q1("SELECT cantidad FROM movimientos_mee WHERE mee_codigo='FR-TRX-30' AND lote_ref='SALDO-EXCEL'")
    assert r and int(r[0]) == 254, ('saldo inicial TRX no cargó', r)
    r2 = _q1("SELECT cantidad FROM movimientos_mee WHERE mee_codigo='FR-VIDRIOOPAL-30' AND lote_ref='SALDO-EXCEL'")
    assert r2 and int(r2[0]) == 7510, ('saldo Vidrio Opal', r2)
    # y el stock canónico de producción lo refleja
    import sqlite3
    import os
    from blueprints.programacion import _get_mee_stock
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        st = _get_mee_stock(conn)
    finally:
        conn.close()
    assert st.get('FR-TRX-30', 0) == 254, ('_get_mee_stock TRX', st.get('FR-TRX-30'))



def test_mig306_cliente(app):
    # auto-marca Kelly Guerra las 2 serigrafías de urea + set-cliente funciona
    from .conftest import csrf_headers
    assert _q1("SELECT cliente FROM maestro_mee WHERE codigo='IMP-SG-CCUREA'")[0] == 'Kelly Guerra', 'auto Kelly'
    c = _login(app)
    rs = c.post('/api/mee/set-cliente', json={'codigo': 'FR-VIDRIOOPAL-30', 'cliente': 'Kelly Guerra'},
                headers=csrf_headers())
    assert rs.status_code == 200, rs.data
    assert _q1("SELECT cliente FROM maestro_mee WHERE codigo='FR-VIDRIOOPAL-30'")[0] == 'Kelly Guerra'



def test_mapear_envase(app):
    # tool de mapeo producto->envase: upsert en producto_presentaciones + valida envase
    from .conftest import csrf_headers
    c = _login(app)
    rs = c.post('/api/admin/mapear-envase',
                json={'producto': 'PROD MAP TEST', 'envase_codigo': 'FR-VIDRIOOPAL-30', 'volumen_ml': 30},
                headers=csrf_headers())
    assert rs.status_code == 200, rs.data
    r = _q1("SELECT envase_codigo, volumen_ml FROM producto_presentaciones "
            "WHERE producto_nombre='PROD MAP TEST' AND presentacion_codigo='PPAL'")
    assert r and r[0] == 'FR-VIDRIOOPAL-30', r
    # envase inexistente -> 400 (no deja fantasma)
    r2 = c.post('/api/admin/mapear-envase', json={'producto': 'X', 'envase_codigo': 'NO-EXISTE-99'},
                headers=csrf_headers())
    assert r2.status_code == 400, r2.data
