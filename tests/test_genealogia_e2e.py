"""GENEALOGÍA de un lote de PT · validación END-TO-END con el flujo REAL (Sebastián 24-jul).

La Fase 1 de la genealogía estaba construida pero NUNCA validada contra un flujo completo:
"aún no hacemos todo completo en EOS, apenas estamos montando todo → ir revisando esto".

Este test recorre la cadena entera por los ENDPOINTS de verdad (no por SQL):

    recepción de MP (cuarentena) → F01 recepción técnica → F02 certificado (libera la MP)
    → FABRICACIÓN DIRECTA (el flujo que EOS usa de verdad) → análisis del PT → liberación

y después le pregunta a la genealogía "¿de qué está hecho este lote?", que es exactamente
lo que responde una auditoría INVIMA. Valida las 4 piezas que pidió Sebastián:
  (1) las MP con su lote de proveedor + su documentación (F01/F02),
  (2) el área y los equipos, con su estado de calibración,
  (3) el envasado / los envases consumidos,
  (4) la liberación y los análisis del lote.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'GEN E2E CREMA'
MP = 'MPGENE2E'
LOTE_MP = 'LP-GEN-E2E'
LOTE_PT = 'LOTE-GEN-E2E'
AREA = 'AGENE2E'
EQUIPO = 'EQ-GEN-E2E'
MEE = 'MEE-GEN-E2E'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s) if isinstance(s, str) else db.execute(s[0], s[1])
        db.commit()
    finally:
        db.close()


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _firmar(c, record_id, meaning='libera', tabla='movimientos'):
    rc = c.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=csrf_headers())
    assert rc.status_code == 200, rc.data
    rs = c.post('/api/sign', json={'record_table': tabla, 'record_id': str(record_id),
                                   'meaning': meaning, 'challenge_token': rc.get_json()['token']},
                headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()['signature_id']


def _limpiar():
    _sql("DELETE FROM movimientos WHERE material_id='%s'" % MP,
         "DELETE FROM movimientos WHERE lote='%s'" % LOTE_PT,
         "DELETE FROM movimientos_mee WHERE mee_codigo='%s'" % MEE,
         "DELETE FROM maestro_mee WHERE codigo='%s'" % MEE,
         "DELETE FROM recepcion_tecnica_doc WHERE codigo_insumo='%s'" % MP,
         "DELETE FROM certificado_analisis_mp WHERE codigo_mp='%s'" % MP,
         "DELETE FROM documentos_regulados WHERE lote IN ('%s','%s')" % (LOTE_MP, LOTE_PT),
         "DELETE FROM calidad_micro_resultados WHERE lote='%s'" % LOTE_PT,
         "DELETE FROM liberaciones WHERE lote='%s'" % LOTE_PT,
         "DELETE FROM producciones WHERE producto='%s'" % PROD,
         "DELETE FROM formula_items WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM formula_headers WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM maestro_mps WHERE codigo_mp='%s'" % MP,
         "DELETE FROM equipos_eventos WHERE equipo_codigo='%s'" % EQUIPO,
         "DELETE FROM equipos_planta WHERE codigo='%s'" % EQUIPO,
         "DELETE FROM areas_planta WHERE codigo='%s'" % AREA)
    # el EBR y el MBR de prueba (el EBR se borra primero por la FK lógica)
    db = _db()
    try:
        ids = [r[0] for r in db.execute(
            "SELECT id FROM mbr_templates WHERE producto_nombre=?", (PROD,)).fetchall()]
        for mid in ids:
            db.execute("DELETE FROM ebr_ejecuciones WHERE mbr_template_id=?", (mid,))
            db.execute("UPDATE mbr_templates SET estado='draft' WHERE id=?", (mid,))
            db.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (mid,))
            db.execute("DELETE FROM mbr_templates WHERE id=?", (mid,))
        db.commit()
    finally:
        db.close()


def _sembrar_catalogo():
    """Catálogo/estructura (lo que ya existe en la planta): MP, fórmula, área, equipo, MBR aprobado."""
    _sql(
        "INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
        "VALUES ('%s','GLYCERIN GEN','Glicerina Gen','MP',1)" % MP,
        "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
        "VALUES ('%s',10000,10,1,datetime('now'))" % PROD,
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
        "VALUES ('%s','%s','GLYCERIN GEN',5.0,0)" % (PROD, MP),
        "INSERT INTO areas_planta (codigo,nombre,tipo,activo) VALUES ('%s','Sala Gen E2E','produccion',1)" % AREA,
        "INSERT INTO equipos_planta (codigo,nombre,area_codigo,tipo,activo) "
        "VALUES ('%s','Marmita Gen E2E','%s','marmita',1)" % (EQUIPO, AREA),
        # calibración vigente del equipo (lo que responde "¿estaba calibrado cuando se fabricó?")
        "INSERT INTO equipos_eventos (equipo_codigo,tipo_evento,fecha,fecha_proxima,estado,responsable,empresa_externa) "
        "VALUES ('%s','calibracion','2026-01-15','2027-01-15','completado','miguel','CI Balanzas de Colombia')" % EQUIPO,
    )
    # MBR: nace draft, se le cargan los pasos y RECIÉN ahí se aprueba (los pasos de un MBR
    # aprobado son inmutables · mig 109). Sin MBR aprobado no nace el EBR automático.
    db = _db()
    try:
        db.execute("INSERT INTO mbr_templates (producto_nombre,formula_version_id,version,estado,lote_size_g,"
                   "creado_por,creado_at_utc) VALUES (?,1,1,'draft',10000,'hernando','2026-07-01 08:00:00')", (PROD,))
        mid = db.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?", (PROD,)).fetchone()[0]
        db.execute("INSERT INTO mbr_pasos (mbr_template_id,orden,fase,descripcion,tipo_paso,requiere_e_sign,requiere_qc) "
                   "VALUES (?,1,'Dispensación','Dispensar GLYCERIN GEN','dispensacion',0,0)", (mid,))
        db.execute("UPDATE mbr_templates SET estado='aprobado', aprobado_por='laura', "
                   "aprobado_at_utc='2026-07-01 12:00:00' WHERE id=?", (mid,))
        db.commit()
    finally:
        db.close()


def _mov_id_entrada():
    db = _db()
    try:
        r = db.execute("SELECT id FROM movimientos WHERE material_id=? AND lote=? AND tipo='Entrada' "
                       "ORDER BY id DESC LIMIT 1", (MP, LOTE_MP)).fetchone()
    finally:
        db.close()
    return r[0] if r else None


def test_genealogia_end_to_end_flujo_real(app):
    """El recorrido completo: lo que entra por recepción tiene que salir en la genealogía del lote."""
    _limpiar()
    _sembrar_catalogo()
    c = _login(app)
    h = csrf_headers()
    try:
        # ── 1) RECEPCIÓN de la MP · entra en CUARENTENA con el lote del proveedor ──
        r = c.post('/api/recepcion', json={
            'codigo_mp': MP, 'nombre_comercial': 'Glicerina Gen', 'nombre_inci': 'GLYCERIN GEN',
            'cantidad': 5000, 'lote': LOTE_MP, 'estanteria': 'CUARENTENA', 'cuarentena': True,
            'proveedor': 'Proveedor Gen E2E', 'fecha_vencimiento': '2027-12-31'}, headers=h)
        assert r.status_code in (200, 201), r.data[:400]
        mov_id = _mov_id_entrada()
        assert mov_id, 'la recepción no dejó la Entrada en el kardex'

        # ── 2) F01 · recepción técnica y documental (Laura) ──
        r = c.post('/api/calidad/recepcion-tecnica', json={
            'mov_id': mov_id, 'origen': 'MP', 'lote': LOTE_MP, 'tipo_insumo': 'materia_prima',
            'codigo_insumo': MP, 'nombre_insumo': 'Glicerina Gen', 'lote_proveedor': LOTE_MP,
            'cantidad_recibida': '5000', 'proveedor': 'Proveedor Gen E2E',
            'fecha_recepcion': '2026-07-24', 'fecha_vencimiento': '2027-12-31',
            'crit_rotulado': 'cumple', 'crit_empaque': 'cumple', 'crit_coa': 'cumple',
            'crit_doc_coincide': 'cumple', 'resultado': 'conforme',
            'realiza_por': 'hernando', 'realiza_fecha': '2026-07-24',
            'aprueba_por': 'laura', 'aprueba_fecha': '2026-07-24'}, headers=h)
        assert r.status_code in (200, 201), r.data[:400]

        # ── 3) F02 · certificado de análisis · APROBADO libera la MP (exige e-firma Part 11) ──
        sig = _firmar(c, mov_id, meaning='libera')
        r = c.post('/api/calidad/certificado-analisis', json={
            'mov_id': mov_id, 'lote': LOTE_MP, 'codigo_mp': MP, 'nombre_mp': 'Glicerina Gen',
            'lote_proveedor': LOTE_MP, 'cantidad_recibida': '5000', 'proveedor': 'Proveedor Gen E2E',
            'fecha_recepcion': '2026-07-24', 'fecha_analisis': '2026-07-24',
            'aspecto_spec': 'Líquido incoloro', 'aspecto_result': 'Conforme', 'aspecto_cumple': 'cumple',
            'ph_spec': '5-7', 'ph_result': '6.1', 'ph_cumple': 'cumple',
            'resultado': 'aprobado', 'responsable_analisis': 'laura', 'aprobo_por': 'laura',
            'signature_id': sig}, headers=h)
        assert r.status_code in (200, 201), r.data[:400]
        db = _db()
        try:
            est = db.execute("SELECT estado_lote FROM movimientos WHERE id=?", (mov_id,)).fetchone()[0]
        finally:
            db.close()
        assert (est or '').upper() == 'VIGENTE', 'el F02 aprobado debía liberar la MP · quedó %r' % est

        # ── 4) FABRICACIÓN DIRECTA (el flujo real de EOS) · 10 kg = 500 g de MP ──
        r = c.post('/api/produccion', json={
            'producto': PROD, 'cantidad_kg': 10, 'operador': 'sebastian', 'presentacion': 'x',
            'lote': LOTE_PT, 'area_codigo': AREA}, headers=h)
        assert r.status_code in (200, 201), r.data[:400]
        assert (r.get_json() or {}).get('lote') == LOTE_PT

        # ── 5) Envasado · consumo de envases (MEE) con la MISMA observación que escribe el
        # cierre de envasado del EBR ("Envasado EBR-<id> lote <lote> · ..."), que es como la
        # genealogía los encuentra hoy. El lote DEL FRASCO todavía no se trackea (Fase 4).
        _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,unidad) "
             "VALUES ('%s','Frasco Gen E2E 50 g','Envase','und')" % MEE,
             "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,observaciones,responsable,fecha) "
             "VALUES ('%s','Salida',400,'Envasado EBR-1 lote %s · envase 50 g','sebastian',datetime('now'))"
             % (MEE, LOTE_PT))

        # ── 6) Análisis del PT + liberación final (lo que cierra el dossier) ──
        _sql("INSERT INTO calidad_micro_resultados (lote,producto_nombre,fecha_analisis,microorganismo,"
             "valor_texto,unidad,estado,laboratorio,analista,creado_por) "
             "VALUES ('%s','%s','2026-07-24','Recuento total','<10','UFC/g','ok','Interno','laura','laura')"
             % (LOTE_PT, PROD),
             "INSERT INTO liberaciones (lote,producto,unidades,presentacion,fecha_produccion,destino,creado_en) "
             "VALUES ('%s','%s',400,'50 g','2026-07-24','ANIMUS',datetime('now'))" % (LOTE_PT, PROD))

        # ── 6) LA PREGUNTA DE LA AUDITORÍA: ¿de qué está hecho este lote? ──
        g = c.get('/api/calidad/genealogia-pt/%s' % LOTE_PT)
        assert g.status_code == 200, g.data[:400]
        d = g.get_json()

        assert d['encontrado'] is True, 'la genealogía no encontró el lote fabricado'
        assert d['producto'] == PROD, d['producto']

        # (1) MP con su lote de proveedor y su documentación
        mps = d['materias_primas']
        assert mps, 'la genealogía NO trajo las materias primas del lote'
        mp = next((m for m in mps if m['material_id'] == MP), None)
        assert mp is not None, [m['material_id'] for m in mps]
        assert mp['lote_mp'] == LOTE_MP, 'debe traer el lote del PROVEEDOR, no el del PT'
        assert abs(mp['gramos'] - 500.0) < 1.0, mp['gramos']
        assert mp['proveedor'] == 'Proveedor Gen E2E'
        assert mp['fecha_vencimiento'].startswith('2027-12-31')
        tipos = {doc['tipo'] for doc in mp['docs']}
        assert 'F01' in tipos, 'falta el F01 en el expediente de la MP · %s' % tipos
        assert 'F02' in tipos, 'falta el F02 en el expediente de la MP · %s' % tipos
        assert d['fuente_mp'] == 'fefo_tag', \
            'Fabricación directa se rastrea por el tag FEFO · fuente=%r' % d['fuente_mp']

        # (2) batch record de la fase + área + equipos + calibración
        assert d['fases'], 'no trajo el batch record (EBR) del lote'
        fab = next((f for f in d['fases'] if f['fase'] == 'fabricacion'), None)
        assert fab is not None, d['fases']
        assert fab['area_codigo'] == AREA, 'el EBR debe guardar el área elegida al fabricar'
        area = d['areas'].get('fabricacion')
        assert area is not None, 'la genealogía no resolvió el área de fabricación'
        assert area['codigo'] == AREA and area['nombre'] == 'Sala Gen E2E'
        eq = next((e for e in area['equipos'] if e['codigo'] == EQUIPO), None)
        assert eq is not None, area['equipos']
        assert eq['calibracion'], 'el equipo debe traer su estado de calibración (INVIMA)'
        assert eq['calibracion']['ultima'] == '2026-01-15', eq['calibracion']
        assert eq['calibracion']['proxima'] == '2027-01-15', eq['calibracion']
        assert eq['calibracion']['vigente'] is True, 'la calibración de 2027 está vigente hoy'

        # (3) envases consumidos en el envasado
        env = next((e for e in d['envases'] if e['mee_codigo'] == MEE), None)
        assert env is not None, 'la genealogía no trajo los envases del lote · %s' % d['envases']
        assert env['cantidad'] == 400 and env['nombre'] == 'Frasco Gen E2E 50 g'

        # (4) análisis del PT + liberación final
        assert d['analisis']['micro'], 'no trajo el control microbiológico del lote'
        assert d['analisis']['micro'][0]['param'] == 'Recuento total'
        assert d['liberacion_final'] is not None, 'no trajo la liberación final del lote'
        assert d['liberacion_final']['unidades'] == 400
        assert d['liberacion_final']['destino'] == 'ANIMUS'
    finally:
        _limpiar()


def test_genealogia_lote_inexistente(app):
    """Un lote que no existe responde limpio (no 500, no árbol a medias)."""
    c = _login(app)
    g = c.get('/api/calidad/genealogia-pt/NO-EXISTE-JAMAS-XYZ')
    assert g.status_code == 200, g.data[:300]
    d = g.get_json()
    assert d['ok'] is True and d['encontrado'] is False
    assert d['materias_primas'] == [] and d['fases'] == []


def test_genealogia_exige_login(client):
    r = client.get('/api/calidad/genealogia-pt/%s' % LOTE_PT)
    assert r.status_code in (401, 302)
