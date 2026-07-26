"""Mover un ENVASE del kardex de MATERIA PRIMA al de ENVASES · corrección regulada (25-jul).

Caso real: MEE-IMP-019 y MEE-IMP-020 (1000 uds c/u, OC-2026-0275) quedaron dentro de
`movimientos` (kardex de MP) porque su código todavía no estaba en `maestro_mee`. El origen
ya está tapado en `recibir_oc`; estas unidades hay que MOVERLAS, y moverlas es una corrección
regulada: Salida compensatoria + Entrada, net-zero y auditada, sin borrar el rastro original.

Lo que estos tests fijan:
  · net-zero EXACTO en el kardex de MP (la Salida espeja el estado_lote original · M31)
  · las unidades aparecen en el kardex de envases con el MISMO lote y el MISMO estado
  · un lote en CUARENTENA sigue en cuarentena (no se libera nada por la puerta de atrás)
  · un código que SÍ es materia prima jamás se toca
  · idempotente: correrlo dos veces no duplica
  · queda auditado (Part 11)
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

CASO = "CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad " \
       "WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END"


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _sembrar(codigo, lote, uds, estado='VIGENTE'):
    db = _db()
    try:
        db.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
            "                         observaciones, lote, estado_lote, operador) "
            "VALUES (?,?,?,'Entrada','2026-07-20T10:00:00','Recepcion OC de prueba',?,?,'test')",
            (codigo, codigo, uds, lote, estado))
        db.commit()
    finally:
        db.close()


def _neto_mp(codigo):
    db = _db()
    try:
        r = db.execute("SELECT COALESCE(SUM(" + CASO + "),0) FROM movimientos "
                       "WHERE UPPER(TRIM(material_id))=?", (codigo.upper(),)).fetchone()
        return float(r[0] or 0)
    finally:
        db.close()


def _mee(codigo):
    """(unidades, estados) del kardex de envases para ese código."""
    db = _db()
    try:
        rows = db.execute("SELECT tipo, cantidad, COALESCE(estado,'VIGENTE'), COALESCE(lote_ref,'') "
                          "FROM movimientos_mee WHERE UPPER(TRIM(mee_codigo))=?",
                          (codigo.upper(),)).fetchall()
    finally:
        db.close()
    uds = sum(float(r[1] or 0) for r in rows if str(r[0]).lower() == 'entrada')
    return uds, [r[2] for r in rows], [r[3] for r in rows]


def test_el_envase_pasa_al_kardex_correcto_y_el_de_MP_queda_en_cero(app):
    cod, lote = 'MEE-TST-901', 'LOTE-901'
    _sembrar(cod, lote, 1000)
    c = _admin(app)

    prev = c.get("/api/admin/envases-kardex-mp").get_json()
    mio = [x for x in prev['plan'] if x['codigo'] == cod]
    assert mio, 'la vista previa debe ver el envase dentro del kardex de MP: %s' % prev
    assert mio[0]['uds_movibles'] == 1000
    assert mio[0]['en_maestro_mee'] is False, 'el caso real es justo un código que no estaba dado de alta'

    # dry_run NO escribe
    r = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c), json={'codigos': [cod]})
    assert r.status_code == 200 and r.get_json()['dry_run'] is True
    assert _neto_mp(cod) == 1000, 'la vista previa no puede tocar el kardex'

    r = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
               json={'codigos': [cod], 'aplicar': True})
    d = r.get_json()
    assert r.status_code == 200, d
    assert d['uds_movidas'] == 1000, d

    # net-zero EXACTO en el kardex de materia prima
    assert _neto_mp(cod) == 0, 'la Salida compensatoria tiene que dejar el kardex de MP en cero'
    # y las unidades aparecen en el de envases, con el mismo lote
    uds, estados, lotes = _mee(cod)
    assert uds == 1000
    assert estados == ['VIGENTE']
    assert lotes == [lote], 'el lote es la trazabilidad: no se puede perder al mover'


def test_el_movimiento_original_se_conserva(app):
    """INVIMA: la corrección no borra el error, lo compensa. El rastro queda."""
    cod, lote = 'MEE-TST-902', 'LOTE-902'
    _sembrar(cod, lote, 300)
    c = _admin(app)
    c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
           json={'codigos': [cod], 'aplicar': True})
    db = _db()
    try:
        rows = db.execute("SELECT tipo, cantidad, COALESCE(estado_lote,'') FROM movimientos "
                          "WHERE UPPER(TRIM(material_id))=? ORDER BY id", (cod,)).fetchall()
    finally:
        db.close()
    assert len(rows) == 2, 'Entrada original + Salida compensatoria: %s' % (rows,)
    assert rows[0][0] == 'Entrada' and float(rows[0][1]) == 300
    assert rows[1][0] == 'Salida' and float(rows[1][1]) == 300
    assert rows[0][2] == rows[1][2], ('la Salida DEBE espejar el estado_lote de la Entrada · '
                                      'si no, el neto no cuadra en las vistas que filtran por estado (M31)')


def test_un_lote_en_cuarentena_sigue_en_cuarentena(app):
    """Mover de kardex no puede liberar material por la puerta de atrás."""
    cod, lote = 'MEE-TST-903', 'LOTE-903'
    _sembrar(cod, lote, 500, estado='CUARENTENA')
    c = _admin(app)
    d = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
               json={'codigos': [cod], 'aplicar': True}).get_json()
    assert d['uds_movidas'] == 500, d
    _uds, estados, _l = _mee(cod)
    assert estados == ['CUARENTENA'], 'la disposición de Calidad se conserva'
    # y el stock canónico de envases NO la cuenta como disponible
    from index import app as _flask
    with _flask.app_context():
        from database import get_db
        from blueprints.programacion import _get_mee_stock
        assert _get_mee_stock(get_db()).get(cod.upper(), 0) == 0, (
            'un envase en cuarentena no puede figurar como disponible')


def test_una_materia_prima_de_verdad_jamas_se_mueve(app):
    """El guard duro: si el código está en maestro_mps es MP, aunque el nombre parezca de envase."""
    cod, lote = 'ENV-REAL-MP', 'LOTE-904'
    db = _db()
    try:
        db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                   "VALUES (?,?,?,1)", (cod, 'Alcohol test', 'Alcohol test'))
        db.commit()
    finally:
        db.close()
    _sembrar(cod, lote, 700)
    c = _admin(app)
    prev = c.get("/api/admin/envases-kardex-mp").get_json()
    mio = [x for x in prev['plan'] if x['codigo'] == cod]
    assert mio and mio[0]['uds_movibles'] == 0, 'no puede haber unidades movibles de una MP real'
    assert mio[0]['es_materia_prima'] is True
    d = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
               json={'codigos': [cod], 'aplicar': True}).get_json()
    assert d['movidos'] == [], d
    assert _neto_mp(cod) == 700, 'el kardex de materia prima quedó intacto'


def test_correrlo_dos_veces_no_duplica(app):
    cod, lote = 'MEE-TST-905', 'LOTE-905'
    _sembrar(cod, lote, 250)
    c = _admin(app)
    c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
           json={'codigos': [cod], 'aplicar': True})
    d2 = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
                json={'codigos': [cod], 'aplicar': True}).get_json()
    assert d2['movidos'] == [], 'la 2ª corrida no tiene nada que mover: %s' % d2
    uds, _e, _l = _mee(cod)
    assert uds == 250, 'no se puede duplicar la Entrada al kardex de envases'
    assert _neto_mp(cod) == 0


def test_una_recepcion_errada_POSTERIOR_tambien_se_puede_mover(app):
    """El ancla del CAS no puede quedar 'quemada' por la corrección anterior.

    Si el ancla fuera MIN(id) a secas, una recepción nueva del MISMO (código, lote, estado)
    heredaría el movimiento ya marcado → el CAS daría rowcount 0 y esas unidades nuevas
    quedarían atrapadas en el kardex de materia prima para siempre.
    """
    cod, lote = 'MEE-TST-907', 'LOTE-907'
    _sembrar(cod, lote, 400)
    c = _admin(app)
    c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
           json={'codigos': [cod], 'aplicar': True})
    assert _neto_mp(cod) == 0

    _sembrar(cod, lote, 150)          # el error se repite por otro camino
    d = c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
               json={'codigos': [cod], 'aplicar': True}).get_json()
    assert d['uds_movidas'] == 150, d
    assert _neto_mp(cod) == 0
    uds, _e, _l = _mee(cod)
    assert uds == 550


def test_queda_auditado(app):
    """Part 11: toda mutación de inventario deja rastro de quién y cuándo."""
    cod, lote = 'MEE-TST-906', 'LOTE-906'
    _sembrar(cod, lote, 120)
    c = _admin(app)
    c.post("/api/admin/envases-kardex-mp/mover", headers=_csrf(c),
           json={'codigos': [cod], 'aplicar': True})
    db = _db()
    try:
        r = db.execute("SELECT usuario FROM audit_log WHERE accion='MOVER_ENVASE_A_KARDEX_MEE' "
                       "AND registro_id=?", (cod,)).fetchone()
    finally:
        db.close()
    assert r is not None, 'la corrección de kardex tiene que quedar en audit_log'
    assert r[0] == 'sebastian'


def test_la_pagina_carga(app):
    c = _admin(app)
    r = c.get("/admin/envases-kardex-mp")
    assert r.status_code == 200
    assert b'kardex de envases' in r.data


def test_solo_admin(app, logged_client):
    assert logged_client.get("/api/admin/envases-kardex-mp").status_code == 403
