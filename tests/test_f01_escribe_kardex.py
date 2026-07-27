"""Lo que Calidad verifica contra el envase entra al kardex EN EL F01, no al final (27-jul).

Sebastián: *"Calidad allí hace la recepción, pero entonces deben poder poner todos los datos de su
F01 pero a la vez editar el rótulo en todos los pasos de la recepción, ¿no?"*

El F01 ya pedía lote real, cantidad pesada y vencimiento, pero los guardaba **sólo en el
documento**: el kardex se quedaba con el lote provisional que asigna la recepción administrativa y
con la cantidad que se compró. Y el **rótulo se imprime leyendo el kardex**, así que el envase se
rotulaba con datos viejos. Las correcciones sólo aterrizaban al aprobar el F02 — el último paso,
cuando el envase ya lleva rato rotulado y guardado.

Estos tres datos no son un juicio de calidad, son hechos sobre lo que llegó, y quien los puede
leer es quien tiene el envase en la mano. Por eso se escriben en el F01, y sólo mientras el lote
sigue en CUARENTENA (M86): corregir hacia atrás un lote ya consumido corrompería el kardex.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'MP00050'
LOTE_PROV = 'L-REAL-7788'


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % usuario
    return c


def _sembrar_entrada(app, lote, cantidad=15000, estado='CUARENTENA'):
    """Una Entrada en cuarentena, como la deja la recepción administrativa. Limpia ANTES (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM movimientos WHERE material_id=? AND lote LIKE 'ZZF01%'", (COD,))
        cur.execute("DELETE FROM movimientos WHERE material_id=? AND lote=?", (COD, LOTE_PROV))
        cur.execute("DELETE FROM recepcion_tecnica_doc WHERE lote LIKE 'ZZF01%'")
        cur.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            "fecha, estado_lote, numero_oc, proveedor) "
            "VALUES (?,?,'Entrada',?,?,?,?,?,?)",
            (COD, 'CAPRYLYL GLUCOSIDE', cantidad, lote, '2026-07-22', estado,
             'OC-ZZF01', 'PROVEEDOR ZZ'))
        mov_id = cur.lastrowid
        conn.commit()
    return mov_id


def _f01(c, mov_id, **extra):
    cuerpo = {
        'mov_id': mov_id, 'origen': 'MP', 'resultado': 'conforme',
        'codigo_insumo': COD, 'nombre_insumo': 'CAPRYLYL GLUCOSIDE',
        'lote': 'ZZF01-PROV', 'lote_proveedor': LOTE_PROV,
        'cantidad_recibida': '14750', 'fecha_vencimiento': '2028-03-15',
        'proveedor': 'PROVEEDOR ZZ', 'numero_oc': 'OC-ZZF01',
        'crit_rotulado': 'si', 'crit_empaque': 'si', 'crit_hoja_seguridad': 'si',
        'crit_ficha_tecnica': 'si', 'crit_coa': 'si', 'crit_doc_coincide': 'si',
        'realiza_por': 'laura',
    }
    cuerpo.update(extra)
    return c.post('/api/calidad/recepcion-tecnica', json=cuerpo, headers=csrf_headers())


def _kardex(mov_id):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    fila = conn.execute(
        "SELECT lote, cantidad, COALESCE(fecha_vencimiento,''), COALESCE(lote_proveedor,''), "
        "       UPPER(COALESCE(estado_lote,'')) FROM movimientos WHERE id=?", (mov_id,)).fetchone()
    conn.close()
    return fila


def test_el_lote_real_del_envase_reemplaza_al_provisional(app, db_clean):
    """El caso central: la recepción administrativa dejó 'OC-...' y Calidad pone el de verdad."""
    mov = _sembrar_entrada(app, 'ZZF01-OC-PROVISIONAL')
    c = _login(app, 'sebastian')
    r = _f01(c, mov)
    assert r.status_code == 200, r.data[:400]
    k = _kardex(mov)
    assert k[0] == LOTE_PROV, 'el kardex se quedó con el lote provisional: %s' % (k[0],)
    assert k[3] == LOTE_PROV, 'el lote del proveedor no quedó en su columna (cruce con CoA)'


def test_la_cantidad_pesada_en_balanza_manda_sobre_la_facturada(app, db_clean):
    """Lo que entra a bodega es lo que pesó, no lo que decía la factura."""
    mov = _sembrar_entrada(app, 'ZZF01-CANT', cantidad=15000)
    c = _login(app, 'sebastian')
    assert _f01(c, mov).status_code == 200
    k = _kardex(mov)
    assert abs(float(k[1]) - 14750) < 0.01, 'el kardex no tomó el peso real: %s' % (k[1],)


def test_el_vencimiento_del_envase_llega_al_kardex(app, db_clean):
    """Sin esto el lote queda sin fecha y el cron de vencidos nunca lo puede marcar."""
    mov = _sembrar_entrada(app, 'ZZF01-VENC')
    c = _login(app, 'sebastian')
    assert _f01(c, mov).status_code == 200
    assert _kardex(mov)[2][:10] == '2028-03-15', _kardex(mov)


def test_el_rotulo_sale_con_los_datos_que_puso_calidad(app, db_clean):
    """La razón de todo esto: el rótulo se imprime leyendo el KARDEX, así que si el F01 no
    escribe ahí, el envase se rotula con los datos viejos."""
    mov = _sembrar_entrada(app, 'ZZF01-ROT')
    c = _login(app, 'sebastian')
    assert _f01(c, mov).status_code == 200
    r = c.get('/rotulo-recepcion/%s/%s/14750' % (COD, LOTE_PROV))
    assert r.status_code == 200, r.data[:200]
    html = r.data.decode('utf-8', 'replace')
    assert LOTE_PROV in html, 'el rótulo no salió con el lote real'
    assert '2028' in html, 'el rótulo no salió con el vencimiento que puso Calidad'


def test_no_corrige_un_lote_que_ya_salio_de_cuarentena(app, db_clean):
    """Con dientes (M86): reescribir el lote o la cantidad de material ya liberado y consumido
    corrompería el kardex hacia atrás."""
    mov = _sembrar_entrada(app, 'ZZF01-VIGENTE', estado='VIGENTE')
    c = _login(app, 'sebastian')
    assert _f01(c, mov).status_code == 200
    k = _kardex(mov)
    assert k[0] == 'ZZF01-VIGENTE', 'tocó un lote que ya estaba fuera de cuarentena: %s' % (k[0],)
    assert abs(float(k[1]) - 15000) < 0.01, 'cambió la cantidad de un lote ya liberado'


def test_la_correccion_queda_auditada(app, db_clean):
    """Cambiar el lote o la cantidad de un registro regulado sin rastro es justo lo que INVIMA
    no perdona."""
    mov = _sembrar_entrada(app, 'ZZF01-AUDIT')
    c = _login(app, 'sebastian')
    assert _f01(c, mov).status_code == 200
    conn = sqlite3.connect(os.environ["DB_PATH"])
    fila = conn.execute(
        "SELECT antes, despues FROM audit_log WHERE accion='F01_CORRIGE_KARDEX' "
        "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(mov),)).fetchone()
    conn.close()
    assert fila, 'la corrección del kardex no dejó rastro en audit_log'
    assert 'ZZF01-AUDIT' in (fila[0] or ''), 'el audit no guardó el valor anterior: %s' % (fila[0],)


def test_despues_del_f01_el_lote_ya_se_puede_liberar(app, db_clean):
    """Cierra el circuito con el control que se agregó hoy: la recepción administrativa deja un
    lote provisional que NO se puede liberar; el F01 pone el real y recién ahí se puede."""
    mov = _sembrar_entrada(app, 'OC-ZZF01-9')          # provisional, como lo deja la recepción
    c = _login(app, 'sebastian')
    r = c.post('/api/lotes/liberar', json={'id': mov, 'accion': 'APROBAR'},
               headers=csrf_headers())
    assert r.status_code == 422 and (r.get_json() or {}).get('codigo') == 'LOTE_SINTETICO_SIN_LIBERAR', \
        'el provisional debería frenar la liberación: %s' % r.data[:200]

    assert _f01(c, mov).status_code == 200
    r = c.post('/api/lotes/liberar', json={'id': mov, 'accion': 'APROBAR'},
               headers=csrf_headers())
    # ya no frena por el lote (ahora pide la firma electrónica, que es el control siguiente)
    assert (r.get_json() or {}).get('codigo') != 'LOTE_SINTETICO_SIN_LIBERAR', (
        'sigue viendo el lote como provisional después del F01: %s' % r.data[:300])
