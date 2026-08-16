"""Firma manuscrita por usuario · manifestación visible Part 11 §11.50 (Sebastián 24-jul).

La e-firma (identidad + HMAC + reauth) es el control legal; la imagen es la rúbrica que se
estampa en los documentos. Cubre: mig 373 (columna), el seeder de los 5 jefes, la página admin,
el set/clear gateado a ADMIN, y que /api/sign devuelva signer_firma_img.
"""
import os
import sqlite3


ORIGIN = {"Origin": "http://localhost"}


def test_mig373_columna_firma_img(app):
    with app.app_context():
        from database import get_db
        cols = {r[1] for r in get_db().execute("PRAGMA table_info(usuarios_identidad)").fetchall()}
    assert 'firma_img' in cols, 'falta columna firma_img (mig 373)'


def test_seed_firmas_de_los_jefes(app):
    """El seeder cargó la firma manuscrita de los 5 jefes desde api/static/firmas_seed/.
    J. Rodriguez es 'jose' (Jefe de Producción), NO jefferson (mig 374 lo corrigió)."""
    with app.app_context():
        from database import get_db
        db = get_db()
        for u in ('hernando', 'miguel', 'laura', 'gloria', 'jose'):
            row = db.execute("SELECT firma_img FROM usuarios_identidad WHERE username=?", (u,)).fetchone()
            assert row is not None, 'usuario %s no existe' % u
            v = row[0] or ''
            assert v.startswith('data:image/png;base64,'), (u, v[:32])
            assert len(v) > 500, ('firma sospechosamente corta', u, len(v))
        # jefferson (Marketing) NO debe tener la firma de J. Rodriguez (mig 374 la limpió)
        jf = db.execute("SELECT COALESCE(firma_img,'') FROM usuarios_identidad WHERE username=?", ('jefferson',)).fetchone()
        assert (jf[0] if jf else '') == '', 'jefferson no debe tener firma (era el mapeo errado)'


def test_crear_persona_firma(admin_client, app):
    """Aseguramiento/admin registra una persona nueva (inducción) + firma + login."""
    px = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
    r = admin_client.post('/api/admin/crear-persona-firma', headers=ORIGIN, json={
        'username': 'ttinduccion', 'nombre_completo': 'Test Inducción', 'cargo': 'Operario',
        'area': 'Producción', 'password': 'ClaveTest123', 'data_uri': px})
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['ok'] and d['login_creado'] is True and d['tiene_firma'] is True
    with app.app_context():
        from database import get_db
        db = get_db()
        ident = db.execute("SELECT nombre_completo, firma_img FROM usuarios_identidad WHERE username='ttinduccion'").fetchone()
        assert ident is not None and ident[0] == 'Test Inducción' and (ident[1] or '').startswith('data:image')
        login = db.execute("SELECT 1 FROM users_passwords WHERE username='ttinduccion'").fetchone()
        assert login is not None, 'debió crear el login'
    # duplicado → 409
    r = admin_client.post('/api/admin/crear-persona-firma', headers=ORIGIN,
                          json={'username': 'ttinduccion', 'nombre_completo': 'X'})
    assert r.status_code == 409
    # username inválido → 400
    r = admin_client.post('/api/admin/crear-persona-firma', headers=ORIGIN,
                          json={'username': 'X Y', 'nombre_completo': 'X'})
    assert r.status_code == 400


def test_crear_persona_solo_aseguramiento(logged_client):
    """valentina (no aseguramiento/admin) NO puede crear personas."""
    r = logged_client.post('/api/admin/crear-persona-firma', headers=ORIGIN,
                           json={'username': 'zznope', 'nombre_completo': 'X'})
    assert r.status_code == 403


def test_firma_estampa_y_resolver(app):
    """El helper de estampa devuelve <img> para quien tiene firma, y resuelve por username y por nombre."""
    from blueprints.firmas import firma_estampa_html, firma_img_resolver
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("UPDATE usuarios_identidad SET nombre_completo='Hernando Acevedo' WHERE username='hernando'")
    db.commit(); db.close()
    with app.app_context():
        from database import get_db
        c = get_db()
        stamp = firma_estampa_html(c, 'hernando')
        assert stamp.startswith('<img') and 'data:image/png' in stamp
        assert firma_estampa_html(c, 'NADIE-XYZ') == ''
        # resuelve por username y por nombre completo
        assert firma_img_resolver(c, 'hernando').startswith('data:image/png')
        assert firma_img_resolver(c, 'Hernando Acevedo').startswith('data:image/png')
        assert firma_img_resolver(c, '') == ''


def test_luis_desactivado(app):
    """Offboarding luis (mig 375): login bloqueado (activo=0) + fuera de la lista de firmas.

    ⚠ El test SIEMBRA su propio universo: `db_clean` vacía `users_passwords` entre tests, así que
    mirar las filas que dejó la migración pasa en una base virgen y falla en cuanto cualquier otro
    test corrió antes (M102/M103) -- que es exactamente por qué este archivo llevaba tiempo rojo
    fuera del gate. Se prueba el MECANISMO (una fila con activo=0 cierra la puerta de verdad,
    aunque exista PASS_LUIS en el entorno), y que la migración la escriba se verifica aparte,
    leyendo el SQL, que no depende del estado de la base.
    """
    with app.app_context():
        from database import get_db, MIGRATIONS
        from blueprints.core import _resolve_password_hash
        db = get_db()
        db.execute("DELETE FROM users_passwords WHERE username='luis'")
        db.execute("INSERT INTO users_passwords (username, password_hash, activo, changed_by) "
                   "VALUES ('luis', '!DESACTIVADO', 0, 'test')")
        db.execute("UPDATE usuarios_identidad SET activo=0 WHERE username='luis'")
        db.commit()
        assert _resolve_password_hash('luis') == '', 'luis no debe poder autenticar'

        # y la migración es la que lo deja así en producción
        sql = " ".join(str(s) for v, _d, stmts in MIGRATIONS if v == 375 for s in stmts)
        assert sql, 'la migración 375 (offboarding) desapareció'
        assert "users_passwords" in sql and "activo=0" in sql.replace(" = ", "=")
        assert "usuarios_identidad" in sql, 'también sale de la lista de firmas del personal'
        assert "DELETE" not in sql.upper(), 'nunca se borra: GMP conserva el histórico'


def test_helper_firma_img(app):
    from blueprints.firmas import firma_img_de_usuario
    with app.app_context():
        from database import get_db
        c = get_db()
        assert firma_img_de_usuario(c, 'hernando').startswith('data:image/png')
        assert firma_img_de_usuario(c, '') == ''
        assert firma_img_de_usuario(c, 'NO-EXISTE-XYZ') == ''


def test_pagina_admin_firmas(admin_client):
    r = admin_client.get('/admin/firmas-usuarios')
    assert r.status_code == 200
    assert b'cortex.css' in r.data and b'Firmas de los jefes' in r.data
    # las firmas ya sembradas aparecen como <img ... data:image
    assert b'data:image/png;base64,' in r.data


def test_pagina_admin_firmas_solo_admin(logged_client):
    """valentina (no admin) NO puede ver/gestionar firmas."""
    r = logged_client.get('/admin/firmas-usuarios')
    assert r.status_code == 403


def test_set_y_clear_firma(admin_client):
    px = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
    # set (usuario que arranca sin firma · smurillo operario)
    r = admin_client.post('/api/admin/firma-usuario', json={'username': 'smurillo', 'data_uri': px}, headers=ORIGIN)
    assert r.status_code == 200, r.data
    assert r.get_json().get('tiene_firma') is True
    # clear
    r = admin_client.post('/api/admin/firma-usuario', json={'username': 'smurillo', 'data_uri': ''}, headers=ORIGIN)
    assert r.status_code == 200 and r.get_json().get('tiene_firma') is False
    # usuario inexistente → 404
    r = admin_client.post('/api/admin/firma-usuario', json={'username': 'NO-EXISTE-XYZ', 'data_uri': px}, headers=ORIGIN)
    assert r.status_code == 404
    # basura (no imagen) → 400
    r = admin_client.post('/api/admin/firma-usuario', json={'username': 'smurillo', 'data_uri': 'hola'}, headers=ORIGIN)
    assert r.status_code == 400


def test_set_firma_solo_admin(logged_client):
    r = logged_client.post('/api/admin/firma-usuario',
                           json={'username': 'laura', 'data_uri': 'data:image/png;base64,AAAA'}, headers=ORIGIN)
    assert r.status_code == 403


def test_sign_response_incluye_firma(app, logged_client):
    """GET /api/sign/<t>/<id> trae signer_firma_img del firmante (manifestación §11.50)."""
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute(
        """INSERT INTO e_signatures
             (record_table, record_id, meaning, signer_username, signer_full_name,
              signer_cedula, signer_cargo, signed_at_utc, ip, auth_factor, comment,
              record_hash, signature_hash)
           VALUES ('ebr_ejecuciones','999001','libera','laura','Laura Gonzalez',
                   '0','Calidad','2026-07-24 10:00:00','','password','','','deadbeef')""")
    db.commit(); db.close()
    r = logged_client.get('/api/sign/ebr_ejecuciones/999001')
    assert r.status_code == 200, r.data
    sigs = r.get_json().get('signatures') or []
    assert sigs, 'no devolvió firmas'
    laura = next((s for s in sigs if s.get('signer_username') == 'laura'), None)
    assert laura is not None
    assert (laura.get('signer_firma_img') or '').startswith('data:image/png'), \
        'la firma de laura debe venir estampada en la respuesta'


# ── Estampa en documentos: F01 recepción técnica · MBR maestro · CoA de PT ──
# (Sebastián: "todos los documentos deben ir firmados").

def _sql(*stmts):
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()  # sin esto, un fallo deja la conexión abierta y el resto del archivo da "database is locked"


def test_f01_imprimible_estampa_firma(logged_client):
    """El F01 (COC-PRO-002-F01) estampa la rúbrica de quien realiza y de quien aprueba."""
    _sql("UPDATE usuarios_identidad SET nombre_completo='Laura Gonzalez' WHERE username='laura'",
         "DELETE FROM recepcion_tecnica_doc WHERE mov_id=987001",
         """INSERT INTO recepcion_tecnica_doc
              (mov_id, numero_oc, lote, tipo_insumo, codigo_insumo, nombre_insumo, lote_proveedor,
               cantidad_recibida, proveedor, fecha_recepcion, resultado,
               realiza_por, realiza_fecha, aprueba_por, aprueba_fecha, creado_por, creado_en, anulado)
            VALUES (987001,'OC-1','L-987','materia_prima','MP00001','GLICERINA','LP-77',
                    '1000','ProvTest','2026-07-24','conforme',
                    'hernando','2026-07-24','Laura Gonzalez','2026-07-24','hernando','2026-07-24 09:00:00',0)""")
    r = logged_client.get('/api/calidad/recepcion-tecnica/imprimible?mov_id=987001&origen=MP')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    assert html.count('class="firma-estampa"') == 2, 'deben ir 2 rúbricas (realiza + aprueba)'
    assert 'data:image/png' in html
    assert 'Realiza la recepción' in html and 'Aprueba la recepción' in html
    assert 'Fecha: 2026-07-24' in html, 'toda firma va fechada (GMP)'


def test_f01_sin_firma_cargada_no_rompe(logged_client):
    """Si el responsable no tiene rúbrica cargada, el documento sale igual (solo el nombre)."""
    _sql("DELETE FROM recepcion_tecnica_doc WHERE mov_id=987002",
         """INSERT INTO recepcion_tecnica_doc
              (mov_id, lote, tipo_insumo, codigo_insumo, nombre_insumo, resultado,
               realiza_por, aprueba_por, creado_por, creado_en, anulado)
            VALUES (987002,'L-988','materia_prima','MP00002','UREA','no_conforme',
                    'FulanoSinFirma','MenganoSinFirma','x','2026-07-24 09:00:00',0)""")
    r = logged_client.get('/api/calidad/recepcion-tecnica/imprimible?mov_id=987002&origen=MP')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    assert 'firma-estampa' not in html
    assert 'FulanoSinFirma' in html and 'NO CONFORME' in html


def test_mbr_imprimible_estampa_aprobador(logged_client):
    """El maestro (MBR) imprimible existe y lleva la rúbrica de quien lo aprobó (§11.50)."""
    _sql("DELETE FROM mbr_pasos WHERE mbr_template_id=987010",
         "DELETE FROM mbr_templates WHERE id=987010",
         "DELETE FROM e_signatures WHERE id=987020",
         """INSERT INTO e_signatures
              (id, record_table, record_id, meaning, signer_username, signer_full_name,
               signer_cedula, signer_cargo, signed_at_utc, ip, auth_factor, comment,
               record_hash, signature_hash)
            VALUES (987020,'mbr_templates','987010','aprueba','laura','Laura Gonzalez',
                    '43111222','Jefe de Control de Calidad','2026-07-24 12:00:00','','password','','','abc123')""",
         # El maestro nace en draft y SOLO después se aprueba: los pasos de un MBR aprobado son
         # inmutables (mig 109) · insertarlos con estado='aprobado' lo bloquea el trigger.
         """INSERT INTO mbr_templates
              (id, producto_nombre, formula_version_id, version, estado, titulo, descripcion,
               lote_size_g, tiempo_total_estimado_min, creado_por, creado_at_utc)
            VALUES (987010,'PRODUCTO TEST MBR',1,3,'draft','Maestro de prueba','desc',
                    20000,120,'hernando','2026-07-20 08:00:00')""",
         """INSERT INTO mbr_pasos
              (mbr_template_id, orden, fase, descripcion, tipo_paso, equipo_requerido,
               tiempo_estimado_min, requiere_e_sign, requiere_qc)
            VALUES (987010,1,'Dispensación','Dispensar GLICERINA (MP00001) · 500 g (2.5%)',
                    'dispensacion','Balanza BAL-01',10,1,0)""",
         """UPDATE mbr_templates SET estado='aprobado', aprobado_por='laura',
              aprobado_at_utc='2026-07-24 12:00:00', aprobado_signature_id=987020 WHERE id=987010""")
    r = logged_client.get('/api/brd/mbr/987010/imprimible')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    assert 'Registro maestro de lote' in html and 'MBR v3' in html
    assert 'APROBADO Y VIGENTE' in html
    assert html.count('class="firma-estampa"') == 2, 'rúbrica de quien elabora y de quien aprueba'
    assert 'Laura Gonzalez' in html and 'C.C. 43111222' in html
    assert 'Dispensar GLICERINA' in html and 'Balanza BAL-01' in html
    assert '20.000 g' in html, 'tamaño de lote con separador de miles'


def test_mbr_imprimible_borrador_y_404(logged_client):
    """Un maestro sin aprobar se imprime marcado como BORRADOR (sin valor regulatorio)."""
    _sql("DELETE FROM mbr_templates WHERE id=987011",
         """INSERT INTO mbr_templates
              (id, producto_nombre, version, estado, lote_size_g, creado_por, creado_at_utc)
            VALUES (987011,'PRODUCTO TEST DRAFT',1,'draft',1000,'hernando','2026-07-20 08:00:00')""")
    r = logged_client.get('/api/brd/mbr/987011/imprimible')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    assert 'BORRADOR' in html
    assert 'no tiene pasos cargados' in html
    r404 = logged_client.get('/api/brd/mbr/987999/imprimible')
    assert r404.status_code == 404


def test_mbr_imprimible_exige_login(client):
    r = client.get('/api/brd/mbr/987010/imprimible')
    assert r.status_code in (401, 302)


def test_coa_pt_estampa_analista(logged_client):
    """El CoA de producto terminado ya no queda sin firmante: lleva al analista con su rúbrica."""
    _sql("DELETE FROM calidad_micro_resultados WHERE lote='LOTE-COA-TEST'",
         """INSERT INTO calidad_micro_resultados
              (lote, producto_nombre, fecha_analisis, microorganismo, valor_texto, unidad,
               estado, laboratorio, analista, metodo, creado_por)
            VALUES ('LOTE-COA-TEST','TRIACTIVE','2026-07-24','Recuento total','<10','UFC/g',
                    'ok','Interno','laura','USP 61','laura')""")
    r = logged_client.get('/api/calidad/coa-pt/LOTE-COA-TEST/imprimible')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    assert 'class="firma-estampa"' in html, 'el analista debe ir con su rúbrica'
    assert 'Realiza el análisis' in html
    assert 'Fecha: 2026-07-24' in html
