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
