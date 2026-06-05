"""Órdenes de Producción unificadas (estilo MyBatch) · paso 1 · SOLO LECTURA.

Sebastián 4-jun-2026: la vista nueva /planta/ordenes-produccion une los
registros simples (tabla producciones) con los legajos EBR, en el formato de
MyBatch (N° orden · lote · teórica/producida/aprobada · estado). Aditivo.

Cubre:
  · endpoint devuelve ok + estructura esperada
  · un registro simple (producciones) aparece como origen='simple'
  · la página responde HTML 200
  · requiere login
"""
import os
import sqlite3
import pytest
from .conftest import TEST_PASSWORD, csrf_headers


@pytest.fixture(autouse=True)
def _aislar_brd():
    """Aísla la BD compartida de sesión: estos tests crean fórmulas, MPs,
    movimientos, MBR, EBR y producciones que contaminarían los golden brd-seed /
    zero-error si corren en el mismo proceso. Snapshot antes → revierte estados de
    MBR y BORRA todo lo nuevo después de cada test (revertir aprobado→draft está
    permitido · el trigger solo bloquea editar un MBR que SIGUE aprobado)."""
    c = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)

    def _ids(sql):
        try:
            return {r[0] for r in c.execute(sql).fetchall()}
        except Exception:
            return set()
    try:
        pre_mbr = dict(c.execute("SELECT id, estado FROM mbr_templates").fetchall())
    except Exception:
        pre_mbr = {}
    pre = {
        'ebr': _ids("SELECT id FROM ebr_ejecuciones"),
        'prod': _ids("SELECT id FROM producciones"),
        'fh': _ids("SELECT producto_nombre FROM formula_headers"),
        'fi': _ids("SELECT id FROM formula_items"),
        'mp': _ids("SELECT codigo_mp FROM maestro_mps"),
        'mov': _ids("SELECT id FROM movimientos"),
    }
    c.close()
    yield
    c = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        for eid, in c.execute("SELECT id FROM ebr_ejecuciones").fetchall():
            if eid not in pre['ebr']:
                c.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=?", (eid,))
                c.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (eid,))
        for pid, in c.execute("SELECT id FROM producciones").fetchall():
            if pid not in pre['prod']:
                c.execute("DELETE FROM producciones WHERE id=?", (pid,))
        for mid, est in c.execute("SELECT id, estado FROM mbr_templates").fetchall():
            if mid in pre_mbr:
                if est != pre_mbr[mid]:
                    c.execute("UPDATE mbr_templates SET estado=? WHERE id=?", (pre_mbr[mid], mid))
            else:
                c.execute("UPDATE mbr_templates SET estado='draft' WHERE id=?", (mid,))
                c.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (mid,))
                c.execute("DELETE FROM mbr_templates WHERE id=?", (mid,))
        # fórmulas/MPs/movimientos nuevos (orden: hijos antes que padres por FK)
        for fid, in c.execute("SELECT id FROM formula_items").fetchall():
            if fid not in pre['fi']:
                c.execute("DELETE FROM formula_items WHERE id=?", (fid,))
        for pn, in c.execute("SELECT producto_nombre FROM formula_headers").fetchall():
            if pn not in pre['fh']:
                c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (pn,))
        for vid, in c.execute("SELECT id FROM movimientos").fetchall():
            if vid not in pre['mov']:
                c.execute("DELETE FROM movimientos WHERE id=?", (vid,))
        for cod, in c.execute("SELECT codigo_mp FROM maestro_mps").fetchall():
            if cod not in pre['mp']:
                c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        c.commit()
    except Exception:
        pass
    finally:
        c.close()


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _conn():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def test_ordenes_unificadas_incluye_registro_simple(app, db_clean):
    c = _conn()
    c.execute("INSERT INTO producciones (producto, cantidad, fecha, estado, operador, lote) "
              "VALUES ('PROD ORDEN TEST', 20, '2026-06-04 10:00', 'Completado', 'sebastian', 'PROD-09999')")
    c.commit(); c.close()
    cl = _login(app)
    r = cl.get('/api/brd/ordenes-unificadas?fase=fabricacion')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['ok'] and d['fase'] == 'fabricacion'
    fila = next((o for o in d['ordenes'] if o['producto'] == 'PROD ORDEN TEST'), None)
    assert fila, f"el registro simple debe aparecer · {d['resumen']}"
    assert fila['origen'] == 'simple'
    assert fila['numero_op'] == 'PROD-09999'
    assert fila['teorica_g'] == 20000.0   # 20 kg → 20.000 g
    assert fila['producida_g'] == 20000.0
    assert fila['aprobada'] is None       # registro simple no tiene QC
    assert 'simple' in fila['estado'].lower()


def test_ordenes_unificadas_fase_invalida_cae_a_fabricacion(app, db_clean):
    cl = _login(app)
    r = cl.get('/api/brd/ordenes-unificadas?fase=xyz')
    assert r.status_code == 200, r.data
    assert r.get_json()['fase'] == 'fabricacion'


def test_ordenes_produccion_page_html(app, db_clean):
    cl = _login(app)
    r = cl.get('/planta/ordenes-produccion')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Órdenes de Producción' in body
    assert 'ordenes-unificadas' in body  # llama al endpoint


def test_ordenes_unificadas_requiere_login(app, db_clean):
    cl = app.test_client()
    r = cl.get('/api/brd/ordenes-unificadas')
    assert r.status_code == 401


def test_registro_produccion_crea_legajo_automatico(app, db_clean):
    """5-jun · LEGAJO AUTOMÁTICO (replica MyBatch): con un MBR APROBADO,
    "Registrar Producción" crea el legajo solo (sin botón, sin depender de
    EBR_MODE) y la orden aparece UNA vez como LEGAJO (dedup del registro simple)."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-AUTO1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-AUTO1','Glicerina','Entrada',100000,'LA1',date('now'))")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD AUTO TEST',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD AUTO TEST','MP-AUTO1','Glicerina',10)")
    # MBR: crear en draft → agregar pasos → aprobar (insertar pasos en un MBR
    # aprobado está prohibido por trigger de inmutabilidad).
    c.execute("INSERT INTO mbr_templates (producto_nombre,version,estado,lote_size_g,titulo,creado_por,creado_at_utc) VALUES ('PROD AUTO TEST',1,'draft',1000,'MBR auto','sebastian','2026-06-04')")
    mbr_id = c.execute("SELECT id FROM mbr_templates WHERE producto_nombre='PROD AUTO TEST'").fetchone()[0]
    c.execute("INSERT INTO mbr_pasos (mbr_template_id,orden,descripcion,tipo_paso,fase) VALUES (?,1,'Mezclar bulk','mezclado','fabricacion')", (mbr_id,))
    c.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr_id,))
    c.commit(); c.close()
    cl = _login(app)
    r = cl.post('/api/produccion', json={'producto': 'PROD AUTO TEST', 'cantidad_kg': 1,
                                         'operador': 'sebastian', 'presentacion': 'test'},
                headers=_h())
    assert r.status_code in (200, 201), r.data
    d = r.get_json()
    assert d.get('ebr') and d['ebr'].get('numero_op'), f"debe crear legajo automático · {d}"
    lote = d['lote']
    c = _conn(); row = c.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone(); c.close()
    assert row, "el EBR debe existir para el lote de la producción"
    od = cl.get('/api/brd/ordenes-unificadas?fase=fabricacion').get_json()
    filas = [o for o in od['ordenes'] if o.get('lote_bulk') == lote]
    assert len(filas) == 1 and filas[0]['origen'] == 'legajo', f"1 sola fila LEGAJO (sin duplicar) · {filas}"


def test_registro_produccion_guarda_area_linea(app, db_clean):
    """5-jun · Área o Línea: al registrar producción con area_codigo (de las áreas
    INVIMA seed PROD1..4), el legajo la guarda y vista-completa la resuelve a
    nombre (Área o Línea deja de salir '—')."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-AREA1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-AREA1','Glicerina','Entrada',100000,'LAR1',date('now'))")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD AREA TEST',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD AREA TEST','MP-AREA1','Glicerina',10)")
    c.execute("INSERT INTO mbr_templates (producto_nombre,version,estado,lote_size_g,titulo,creado_por,creado_at_utc) VALUES ('PROD AREA TEST',1,'draft',1000,'t','sebastian','2026-06-05')")
    mbr = c.execute("SELECT id FROM mbr_templates WHERE producto_nombre='PROD AREA TEST'").fetchone()[0]
    c.execute("INSERT INTO mbr_pasos (mbr_template_id,orden,descripcion,tipo_paso,fase) VALUES (?,1,'Mezclar','mezclado','fabricacion')", (mbr,))
    c.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr,))
    c.commit(); c.close()
    cl = _login(app)
    r = cl.post('/api/produccion', json={'producto': 'PROD AREA TEST', 'cantidad_kg': 1,
                                         'operador': 'sebastian', 'presentacion': 'test',
                                         'area_codigo': 'PROD2'}, headers=_h())
    assert r.status_code in (200, 201), r.data
    d = r.get_json()
    assert d.get('ebr') and d['ebr'].get('id'), f"debe crear legajo · {d}"
    ebr_id = d['ebr']['id']
    h = cl.get(f'/api/brd/ebr/{ebr_id}/vista-completa').get_json()['header']
    assert h.get('area_codigo') == 'PROD2', h.get('area_codigo')
    # area_linea = "<nombre> (PROD2)" · resuelto desde areas_planta
    al = h.get('area_linea') or ''
    assert 'PROD2' in al and len(al) > len('PROD2'), al


def test_registro_produccion_lote_personalizado(app, db_clean):
    """5-jun · N° de Lote editable (MyBatch parity): si el operario escribe el
    lote bulk (ej. 261561), se usa ese; si lo deja vacío, auto PROD-NNNNN."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-LOT1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-LOT1','Glicerina','Entrada',100000,'LL1',date('now'))")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD LOTE TEST',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD LOTE TEST','MP-LOT1','Glicerina',10)")
    c.commit(); c.close()
    cl = _login(app)
    r = cl.post('/api/produccion', json={'producto': 'PROD LOTE TEST', 'cantidad_kg': 1,
                                         'operador': 'sebastian', 'presentacion': 'test',
                                         'lote': '261561'}, headers=_h())
    assert r.status_code in (200, 201), r.data
    assert r.get_json().get('lote') == '261561', r.get_json().get('lote')
    c = _conn()
    lt = c.execute("SELECT lote FROM producciones WHERE producto='PROD LOTE TEST' ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    assert lt and lt[0] == '261561', f"la producción debe guardar el lote escrito · {lt}"


def test_registro_produccion_sin_mbr_no_crea_legajo(app, db_clean):
    """Si el producto NO tiene MBR aprobado, el registro NO crea legajo (se
    comporta idéntico a antes · cero riesgo). El legajo automático depende del
    MBR aprobado, no de EBR_MODE."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-OFF1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MP-OFF1','Glicerina','Entrada',100000,'LO1',date('now'))")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD OFF TEST',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD OFF TEST','MP-OFF1','Glicerina',10)")
    c.commit(); c.close()
    cl = _login(app)
    r = cl.post('/api/produccion', json={'producto': 'PROD OFF TEST', 'cantidad_kg': 1,
                                         'operador': 'sebastian', 'presentacion': 'test'},
                headers=_h())
    assert r.status_code in (200, 201), r.data
    assert r.get_json().get('ebr') is None, "sin MBR aprobado no debe crear legajo"


def test_aprobar_todas_genera_y_aprueba(app, db_clean):
    """Activación masiva: genera+aprueba MBR de todos los productos con fórmula,
    con una sola re-autenticación (password, sin MFA en test)."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-AT1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD APROBAR TODAS',1,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD APROBAR TODAS','MP-AT1','Glicerina',100)")
    c.commit(); c.close()
    cl = _login(app)
    r = cl.post('/api/brd/mbr/aprobar-todas', json={'password': TEST_PASSWORD, 'totp_token': ''}, headers=_h())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['ok'] and d['mbr_aprobados'] >= 1, d
    c = _conn()
    est = c.execute("SELECT estado FROM mbr_templates WHERE producto_nombre='PROD APROBAR TODAS' ORDER BY version DESC LIMIT 1").fetchone()
    c.close()
    assert est and est[0] == 'aprobado', f"el MBR debe quedar aprobado · {est}"


def test_aprobar_todas_password_invalida(app, db_clean):
    cl = _login(app)
    r = cl.post('/api/brd/mbr/aprobar-todas', json={'password': 'malísima', 'totp_token': ''}, headers=_h())
    assert r.status_code == 401, r.data


def test_activar_legajos_page_html(app, db_clean):
    cl = _login(app)
    r = cl.get('/planta/activar-legajos')
    assert r.status_code == 200
    b = r.get_data(as_text=True)
    assert 'Activar legajos' in b and 'aprobar-todas' in b


def test_vista_completa_supervisado_y_elaborado(app, db_clean):
    """5-jun · regla del CEO: el área productiva la supervisa el Jefe de
    Producción. vista-completa resuelve 'Supervisado por' = Jefe de Producción y
    enriquece 'Elaborado por' con nombre+cargo desde usuarios_identidad."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO usuarios_identidad (username,nombre_completo,cargo,activo) VALUES ('jprodtest','Jose Alfredo Rodriguez','Jefe de Producción',1)")
    c.execute("INSERT OR REPLACE INTO usuarios_identidad (username,nombre_completo,cargo,activo) VALUES ('opertest','Maierlin Rivera','Operaria de producción',1)")
    c.execute("INSERT INTO mbr_templates (producto_nombre,version,estado,lote_size_g,titulo,creado_por,creado_at_utc) VALUES ('PROD SUP TEST',1,'draft',1000,'t','sebastian','2026-06-05')")
    mbr = c.execute("SELECT id FROM mbr_templates WHERE producto_nombre='PROD SUP TEST'").fetchone()[0]
    c.execute("INSERT INTO mbr_pasos (mbr_template_id,orden,descripcion,tipo_paso,fase) VALUES (?,1,'Mezclar','mezclado','fabricacion')", (mbr,))
    c.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr,))
    c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,numero_op,estado,iniciado_por,iniciado_at_utc,cantidad_objetivo_g,fase) VALUES (?,1,'LSUP-1','OP-2026-7777','iniciado','opertest','2026-06-05',1000,'fabricacion')", (mbr,))
    ebr = c.execute("SELECT id FROM ebr_ejecuciones WHERE lote='LSUP-1'").fetchone()[0]
    c.commit(); c.close()
    cl = _login(app)
    h = cl.get(f'/api/brd/ebr/{ebr}/vista-completa').get_json()['header']
    assert 'Jefe de Producción' in (h.get('supervisado_por') or ''), h.get('supervisado_por')
    assert 'Jose Alfredo' in (h.get('supervisado_por') or '')
    assert 'Maierlin' in (h.get('operario') or '') and 'opertest' in (h.get('operario') or '')
    assert h.get('numero_op') == 'OP-2026-7777'


def test_orden_detalle_page_html(app, db_clean):
    """Detalle de Orden estilo MyBatch (cabecera + botones + pesaje) · solo lectura."""
    cl = _login(app)
    r = cl.get('/planta/orden/123')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Orden de Producción' in body
    assert 'Pesaje de Materias Primas' in body
    assert 'vista-completa' in body          # reusa el endpoint existente
    assert 'var EBR_ID = 123;' in body       # id inyectado correctamente


def test_bootstrap_legajo_chain(app, db_clean):
    """Cadena exacta del botón "➕ Crear legajo": generar MBR desde fórmula →
    submit → firmar (e-Part11) → aprobar → crear EBR. Al final el detalle existe
    y la orden aparece como LEGAJO. Garantiza que el bootstrap de 1-clic funciona."""
    c = _conn()
    c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) VALUES ('MP-BOOT1','GLYCERIN','Glicerina','MP',1)")
    c.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('PROD BOOT TEST',10,1)")
    c.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('PROD BOOT TEST','MP-BOOT1','Glicerina',100)")
    c.commit(); c.close()
    cl = _login(app)
    # identidad con cédula (la e-firma la exige)
    cl.patch('/api/identidad/sebastian', json={'cedula': '99999999'}, headers=_h())
    # 1) generar MBR desde fórmula
    g = cl.post('/api/brd/mbr/generar-desde-formula',
                json={'producto_nombre': 'PROD BOOT TEST'}, headers=_h())
    assert g.status_code in (200, 201), g.data
    mbr_id = g.get_json()['id']
    # 2) submit
    s = cl.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    assert s.status_code == 200, s.data
    # 3) firma e-Part11
    ch = cl.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=_h())
    assert ch.status_code == 200, ch.data
    token = ch.get_json()['token']
    sg = cl.post('/api/sign', json={'record_table': 'mbr_templates', 'record_id': str(mbr_id),
                                    'meaning': 'aprueba', 'challenge_token': token}, headers=_h())
    assert sg.status_code == 201, sg.data
    sig = sg.get_json()['signature_id']
    # 4) aprobar
    ap = cl.post(f'/api/brd/mbr/{mbr_id}/aprobar', json={'signature_id': sig}, headers=_h())
    assert ap.status_code == 200, ap.data
    # 5) crear EBR (legajo)
    e = cl.post('/api/brd/ebr', json={'mbr_template_id': mbr_id, 'lote': 'BOOT-LOTE-1',
                                      'fase': 'fabricacion'}, headers=_h())
    assert e.status_code == 201, e.data
    ebr_id = e.get_json()['id']
    # el detalle carga y la orden aparece como LEGAJO
    vc = cl.get(f'/api/brd/ebr/{ebr_id}/vista-completa')
    assert vc.status_code == 200, vc.data
    d = cl.get('/api/brd/ordenes-unificadas?fase=fabricacion').get_json()
    fila = next((o for o in d['ordenes'] if o.get('lote_bulk') == 'BOOT-LOTE-1'), None)
    assert fila and fila['origen'] == 'legajo', f"la orden debe ser LEGAJO · {d['resumen']}"
    assert fila['link'] == f'/planta/orden/{ebr_id}'


def test_orden_detalle_link_apunta_a_detalle(app, db_clean):
    """El link de las órdenes EBR debe apuntar a /planta/orden/<id> (no al timeline)."""
    import sqlite3
    c = _conn()
    # crear un MBR + EBR mínimo para que aparezca como legajo con link
    c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, titulo, creado_por, creado_at_utc) "
              "VALUES ('PROD DET TEST', 1, 'aprobado', 1000, 'MBR test', 'sebastian', '2026-06-04')")
    mbr_id = c.execute("SELECT id FROM mbr_templates WHERE producto_nombre='PROD DET TEST'").fetchone()[0]
    c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, numero_op, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, fase) "
              "VALUES (?, 1, 'LOTE-DET-1', 'OP-2026-9999', 'iniciado', 'sebastian', '2026-06-04', 1000, 'fabricacion')", (mbr_id,))
    c.commit(); c.close()
    cl = _login(app)
    d = cl.get('/api/brd/ordenes-unificadas?fase=fabricacion').get_json()
    fila = next((o for o in d['ordenes'] if o.get('numero_op') == 'OP-2026-9999'), None)
    assert fila and fila['origen'] == 'legajo', f"el EBR debe aparecer como legajo · {d['resumen']}"
    assert fila['link'] == f"/planta/orden/{fila['ebr_id']}", f"link al detalle · {fila.get('link')}"
