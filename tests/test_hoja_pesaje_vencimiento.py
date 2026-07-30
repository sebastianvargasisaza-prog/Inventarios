"""La hoja de pesaje dice el VENCIMIENTO de la materia prima que se está usando (30-jul).

Sebastián: *"en el rótulo de pesaje que vaya la fecha de vencimiento de la materia prima que
usan"*.

El rótulo de dispensación ya lo imprimía; la **hoja de pesaje del batch record** (el documento
que el operario sigue en piso) no. Y es donde más importa: es el punto de USO. Sale del kardex
para el (material, lote) que se pesó de verdad -- no del maestro, que no tiene lotes -- y si el
lote ya venció se marca, porque una MP vencida no puede entrar al producto (M25).
"""
from .conftest import TEST_PASSWORD, csrf_headers

MP = 'MP-ZZPESA'
LOTE = 'LZZ-PESA-1'
LOTE_EBR = 'ZZ-PESAJE-VENC'
PROD = 'ZZ PRODUCTO PESAJE'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app, vencimiento='2028-05-31'):
    """MP con lote y vencimiento + fórmula + legajo con un pesaje registrado de ESE lote."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE_EBR,)).fetchone()
        if f:
            cu.execute("DELETE FROM ebr_pesajes WHERE ebr_id=?", (f[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute("DELETE FROM movimientos WHERE material_id=?", (MP,))
        cu.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        cu.execute(
            "INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
            "VALUES (?,?,?,1) ON CONFLICT (codigo_mp) DO UPDATE SET activo=1",
            (MP, 'TEST INCI PESAJE', 'MP de prueba pesaje'))
        cu.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
            "fecha_vencimiento, estado_lote) VALUES (?,?,?, 'Entrada','2026-07-01T08:00:00',?,?, 'VIGENTE')",
            (MP, 'MP de prueba pesaje', 5000, LOTE, vencimiento))
        # `formula_headers` real: (producto_nombre UNIQUE, unidad_base_g, descripcion,
        # fecha_creacion) + las columnas que agregaron las migraciones. Verificado contra el
        # CREATE TABLE antes de escribir el INSERT (auto-check del cerebro).
        cu.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g) VALUES (?,10000)",
                   (PROD,))
        cu.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                   "porcentaje) VALUES (?,?,?,?)", (PROD, MP, 'MP de prueba pesaje', 5.0))
        cu.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                   "lote_size_g, creado_por) VALUES (?,1,'draft','MBR pesaje',10000,'sebastian')",
                   (PROD,))
        mbr = cu.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?", (PROD,)).fetchone()[0]
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, "
            "fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,1,?,?, 'en_proceso','fabricacion','sebastian','2026-07-30T09:00:00',10000)",
            (mbr, LOTE_EBR, LOTE_EBR))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE_EBR,)).fetchone()[0]
        cu.execute(
            "INSERT INTO ebr_pesajes (ebr_id, material_id, material_nombre, cantidad_teorica_g, "
            "cantidad_real_g, lote_mp, pesado_por, pesado_at_utc) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (eid, MP, 'MP de prueba pesaje', 500, 499.5, LOTE, 'mayerlin', '2026-07-30T10:00:00'))
        conn.commit()
    return eid


def test_la_hoja_de_pesaje_imprime_el_vencimiento_del_lote(app, db_clean):
    eid = _sembrar(app, '2028-05-31')
    r = _login(app).get('/brd/dispensado/%d' % eid)
    assert r.status_code == 200, r.data[:300]
    body = r.data.decode('utf-8', 'replace')
    assert 'Vence' in body, 'no está la columna de vencimiento'
    assert '2028-05-31' in body, 'no imprimió el vencimiento del lote que se pesó'
    assert LOTE in body


def test_un_lote_VENCIDO_se_marca_en_la_hoja(app, db_clean):
    """Una MP vencida no puede entrar al producto: el operario tiene que verlo en el papel
    que tiene en la mano, no en otra pantalla."""
    eid = _sembrar(app, '2020-01-31')
    body = _login(app).get('/brd/dispensado/%d' % eid).data.decode('utf-8', 'replace')
    assert '2020-01-31' in body
    assert 'VENCIDO' in body, 'no marcó el lote vencido'


def test_sin_lote_pesado_no_inventa_fecha(app, db_clean):
    """Sin dato no se pone una fecha: se declara que falta (M115)."""
    eid = _sembrar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM ebr_pesajes WHERE ebr_id=?", (eid,))
        conn.commit()
    body = _login(app).get('/brd/dispensado/%d' % eid).data.decode('utf-8', 'replace')
    assert 'Vence' in body
    assert '2028-05-31' not in body, 'imprimió un vencimiento sin que nadie haya pesado ese lote'
