"""La corrección de colisiones del 15-jul quedó de UN SOLO LADO · devolución net-zero (2-ago).

Caso real: el 9-jul un consumo retroactivo descontó materiales por el código EQUIVOCADO
(MyBatch y EOS usan el mismo número para moléculas distintas). El 15-jul se corrigió: se agregó
el descuento al código CORRECTO... y nunca se devolvió el del equivocado. Las cantidades cuadran
al gramo en los tres pares, así que la corrección identificó bien el material -- lo que faltó fue
la otra pata.

Resultado: MP00300, MP00301 y MP00302 muestran MENOS stock del que hay en el estante, y el
consumo figura registrado dos veces.

Lo que estos tests fijan:
  · devuelve exactamente lo que la corrección se llevó, al MISMO lote
  · idempotente: correrlo dos veces no duplica la devolución
  · una salida SIN corrección que la explique NO se toca (nunca se inventa una devolución)
  · nunca devuelve MÁS de lo que la corrección movió (tope duro)
  · la Entrada conserva el VENCIMIENTO del lote (si se pierde, el FEFO lo trata como eterno · M118)
  · espeja el estado del lote (un lote en cuarentena no se libera por la puerta de atrás · M31)
  · la vista previa NO escribe (y muestra el mismo número que el apply · M101)
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

# el CASE canónico de stock (regla #4 · cuenta los Ajuste como entrada)
CASO = "CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad " \
       "WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END"

MAL, BUENO = 'MP00302', 'MP00301'          # isododecane ← se le imputó ethylhexylglycerin
LOTE = 'LOTE-NET0-1'


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


def _limpiar():
    """M103: limpiar ANTES de sembrar. Un `finally` no corre si el proceso muere, y la BD de
    tests es compartida y en PostgreSQL sobrevive entre corridas."""
    db = _db()
    try:
        db.execute("DELETE FROM movimientos WHERE material_id IN (?,?)", (MAL, BUENO))
        db.commit()
    finally:
        db.close()


def _sembrar_colision(*, g_mal=140.0, g_corr=140.0, lote=LOTE, estado='VIGENTE',
                      venc=None, con_correccion=True, marca_cant=None):
    """Reproduce el estado real: el descuento equivocado del 9-jul + la corrección del 15-jul."""
    mc = int(marca_cant if marca_cant is not None else round(g_mal))
    db = _db()
    try:
        if venc:
            db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,"
                       "observaciones,lote,fecha_vencimiento,estado_lote) "
                       "VALUES (?,?,?,'Entrada','2026-06-18 08:00:00','Recepción',?,?,?)",
                       (MAL, 'Isododecane', 1000.0, lote, venc, estado))
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,"
                   "observaciones,lote,estado_lote,operador) VALUES (?,?,?,'Salida',"
                   "'2026-07-09 10:00:00',?,?,?,'sebastian')",
                   (MAL, 'Isododecane', g_mal,
                    'Consumo retroactivo · PT-NET0 · lote real %s [retro BULKNET0|%s|%s|%d]'
                    % (lote, MAL, lote, mc), lote, estado))
        if con_correccion:
            db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,"
                       "observaciones,lote,operador) VALUES (?,?,?,'Salida',"
                       "'2026-07-15 09:00:00',?,?,'sebastian')",
                       (BUENO, 'Ethylhexylglycerin', g_corr,
                        'Corrección colisión %s->%s · PT-NET0 · lote %s [retro-corr BULKNET0|%s|%s|%d]'
                        % (MAL, BUENO, lote, BUENO, lote, mc), lote))
        db.commit()
    finally:
        db.close()


def _stock(cod):
    db = _db()
    try:
        r = db.execute("SELECT COALESCE(SUM(%s),0) FROM movimientos WHERE material_id=? "
                       "AND UPPER(COALESCE(estado_lote,'')) NOT IN "
                       "('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO')"
                       % CASO, (cod,)).fetchone()
        return round(float(r[0] or 0), 2)
    finally:
        db.close()


def _par(js):
    return next(p for p in js['pares'] if p['de'] == MAL and p['a'] == BUENO)


def _entradas_devolucion():
    db = _db()
    try:
        return db.execute("SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos "
                          "WHERE material_id=? AND tipo='Entrada' "
                          "AND observaciones LIKE '%Devolución net-zero%'", (MAL,)).fetchone()
    finally:
        db.close()


def test_devuelve_al_estante_lo_que_la_correccion_se_llevo(app):
    _limpiar(); _sembrar_colision()
    c = _admin(app)

    antes = _stock(MAL)
    prev = c.get("/api/admin/colisiones-net-zero").get_json()
    assert prev['dry_run'] is True
    assert _par(prev)['a_devolver_g'] == 140.0
    assert _par(prev)['corregido_g'] == 140.0
    assert _stock(MAL) == antes, "la vista previa NO puede escribir"

    r = c.post("/api/admin/colisiones-net-zero", json={'aplicar': True}, headers=_csrf(c))
    js = r.get_json()
    assert r.status_code == 200 and js['ok'] is True
    assert js['resumen']['g_devueltos_ahora'] == 140.0
    assert _stock(MAL) == round(antes + 140.0, 2)

    n, g = _entradas_devolucion()
    assert (n, round(float(g), 2)) == (1, 140.0)
    db = _db()
    try:
        lote = db.execute("SELECT lote FROM movimientos WHERE material_id=? AND tipo='Entrada' "
                          "AND observaciones LIKE '%Devolución net-zero%'", (MAL,)).fetchone()[0]
        assert lote == LOTE, "la devolución va al MISMO lote del que salió"
        assert db.execute("SELECT COUNT(*) FROM audit_log WHERE accion='COLISION_NET_ZERO'",
                          ()).fetchone()[0] >= 1
    finally:
        db.close()


def test_idempotente_no_duplica_la_devolucion(app):
    _limpiar(); _sembrar_colision()
    c = _admin(app)
    c.post("/api/admin/colisiones-net-zero", json={'aplicar': True}, headers=_csrf(c))
    despues_1 = _stock(MAL)

    js = c.post("/api/admin/colisiones-net-zero", json={'aplicar': True},
                headers=_csrf(c)).get_json()
    assert js['resumen']['g_devueltos_ahora'] == 0.0
    assert _stock(MAL) == despues_1
    assert _entradas_devolucion()[0] == 1
    assert _par(js)['ya_devuelto_g'] == 140.0 and _par(js)['a_devolver_g'] == 0.0

    # la Salida original quedó RECLAMADA con la marca. El CAS no se puede probar en secuencia
    # (M27: protege sólo la ventana concurrente de los 3 workers), pero sí se verifica que la
    # marca se escriba -- sin ella, dos apply simultáneos devolverían los gramos dos veces.
    db = _db()
    try:
        wid, wobs = db.execute(
            "SELECT id, COALESCE(observaciones,'') FROM movimientos WHERE material_id=? "
            "AND tipo='Salida' AND observaciones LIKE '%[retro %'", (MAL,)).fetchone()
        assert ('[retro-corr-rev #%s]' % wid) in wobs
    finally:
        db.close()


def test_no_toca_una_salida_sin_correccion_que_la_explique(app):
    """Sin la corrección del 15-jul, ese descuento puede ser legítimo: no se inventa nada."""
    _limpiar(); _sembrar_colision(con_correccion=False)
    c = _admin(app)
    antes = _stock(MAL)
    js = c.post("/api/admin/colisiones-net-zero", json={'aplicar': True},
                headers=_csrf(c)).get_json()
    assert _par(js)['a_devolver_g'] == 0.0
    assert js['resumen']['g_devueltos_ahora'] == 0.0
    assert _stock(MAL) == antes
    assert _entradas_devolucion()[0] == 0


def test_nunca_devuelve_mas_de_lo_que_la_correccion_movio(app):
    """Tope duro: si el descuento equivocado fue de 500 g y la corrección sólo movió 140,
    devolver los 500 inventaría 360 g de material."""
    _limpiar(); _sembrar_colision(g_mal=500.0, g_corr=140.0, marca_cant=140)
    c = _admin(app)
    antes = _stock(MAL)
    js = c.post("/api/admin/colisiones-net-zero", json={'aplicar': True},
                headers=_csrf(c)).get_json()
    par = _par(js)
    assert par['a_devolver_g'] == 0.0
    assert len(par['excedente']) == 1 and par['excedente'][0]['g'] == 500.0
    assert _stock(MAL) == antes


def test_conserva_el_vencimiento_del_lote(app):
    """Si vuelve sin fecha, el cron de vencidos deja de verlo y el FEFO lo trata como eterno."""
    _limpiar(); _sembrar_colision(venc='2027-03-31')
    c = _admin(app)
    c.post("/api/admin/colisiones-net-zero", json={'aplicar': True}, headers=_csrf(c))
    db = _db()
    try:
        fv = db.execute("SELECT fecha_vencimiento FROM movimientos WHERE material_id=? "
                        "AND tipo='Entrada' AND observaciones LIKE '%Devolución net-zero%'",
                        (MAL,)).fetchone()[0]
        assert str(fv or '')[:10] == '2027-03-31'
    finally:
        db.close()


def test_espeja_el_estado_del_lote_no_libera_cuarentena(app):
    """Un lote en CUARENTENA no cuenta como stock: la devolución tampoco, o la corrección
    liberaría material por la puerta de atrás (M31: net-zero en TODA vista)."""
    _limpiar(); _sembrar_colision(estado='CUARENTENA')
    c = _admin(app)
    antes = _stock(MAL)
    c.post("/api/admin/colisiones-net-zero", json={'aplicar': True}, headers=_csrf(c))
    db = _db()
    try:
        est = db.execute("SELECT estado_lote FROM movimientos WHERE material_id=? "
                         "AND tipo='Entrada' AND observaciones LIKE '%Devolución net-zero%'",
                         (MAL,)).fetchone()[0]
        assert (est or '').upper() == 'CUARENTENA'
    finally:
        db.close()
    assert _stock(MAL) == antes, "no puede aparecer stock disponible que estaba en cuarentena"


def test_solo_admin(app):
    _limpiar()
    c = app.test_client()
    c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    assert c.get("/api/admin/colisiones-net-zero").status_code in (401, 403)
