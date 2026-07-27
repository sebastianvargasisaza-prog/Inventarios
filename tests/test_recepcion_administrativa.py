"""La recepción ADMINISTRATIVA no exige datos que sólo Calidad puede tomar (27-jul).

Sebastián, mostrando `/recepcion`: *"aquí es donde Catalina verifica lo llegado, pone cuánto trae
registrado... a Catalina no la está dejando, necesito que pueda hacer la recepción administrativa,
que no es nada de calidad"*.

Eran dos fallas encadenadas:

1. **La pantalla manda `lote` y el backend validaba `lote_proveedor`.** Una sola llave, dos
   nombres: el lote que Catalina tecleaba se descartaba en silencio, así que la validación lo veía
   SIEMPRE vacío y devolvía 422 aunque ella lo hubiera escrito. Por eso los lotes que le llegan a
   Calidad son los sintéticos `OC-OC-2026-...`.
2. **La recepción administrativa exigía el lote del proveedor.** Quien recibe cuenta bultos; el
   lote real, el peso en balanza y el vencimiento los lee CALIDAD del envase físico (F01).

El control INVIMA no se quitó, se movió a donde se puede cumplir (M39): el material entra en
CUARENTENA (el FEFO la excluye, así que no se puede consumir) y **liberar exige lote real** — un
lote sintético no se aprueba. Rechazar sí se permite con lote provisional: trabar un rechazo
dejaría material malo atascado en cuarentena.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

OC_MP = 'OC-ZZADM-MP'
OC_MEE = 'OC-ZZADM-MEE'


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % usuario
    return c


def _sembrar_oc(app, numero, categoria_sol, codigos):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (numero,))
        cur.execute("DELETE FROM solicitudes_compra WHERE numero_oc=?", (numero,))
        cur.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (numero,))
        cur.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc=?", (numero,))
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                    "valor_total, creado_por) VALUES (?,?,?,?,?,?,?)",
                    (numero, 'PROVEEDOR ZZ', 'Autorizada',
                     'MP' if categoria_sol == 'Materia Prima' else 'MEE',
                     '2026-07-22', 1000, 'catalina'))
        for cod, nom in codigos:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                        "cantidad_g, precio_unitario) VALUES (?,?,?,?,?)",
                        (numero, cod, nom, 15000, 1))
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "numero_oc, categoria) VALUES (?,?,?,?,?,?)",
                    ('SOL-' + numero, '2026-07-22', 'Aprobada', 'catalina', numero, categoria_sol))
        conn.commit()


def _recibir(c, numero, items, token):
    return c.post('/api/ordenes-compra/%s/recibir' % numero,
                  json={'observaciones_recepcion': '', 'tiene_discrepancias': 0,
                        'items_recepcion': items, 'receptor_nombre': 'Catalina',
                        'recepcion_id': token})


def test_catalina_puede_cerrar_la_recepcion_de_materia_prima_sin_el_lote(app, db_clean):
    """El caso que Sebastián mostró: quien recibe cuenta lo que llegó y cierra. El lote lo pone
    Calidad después, contra el envase."""
    _sembrar_oc(app, OC_MP, 'Materia Prima', [('MP00050', 'CAPRYLYL GLUCOSIDE')])
    c = _login(app, 'catalina')
    r = _recibir(c, OC_MP, [{'codigo_mp': 'MP00050', 'cantidad_recibida': 15000, 'estado': 'OK',
                             'notas': '', 'lote': '', 'fecha_vencimiento': '', 'recipientes': 1}],
                 'rcp-adm-1')
    assert r.status_code == 200, ('la recepción administrativa sigue bloqueada: %s'
                                  % r.data[:400])


def test_el_lote_que_teclea_quien_recibe_no_se_descarta(app, db_clean):
    """Con dientes. La pantalla manda `lote`; si el backend vuelve a leer sólo `lote_proveedor`,
    ese dato se pierde y la trazabilidad queda con el lote sintético."""
    _sembrar_oc(app, OC_MP, 'Materia Prima', [('MP00050', 'CAPRYLYL GLUCOSIDE')])
    c = _login(app, 'catalina')
    r = _recibir(c, OC_MP, [{'codigo_mp': 'MP00050', 'cantidad_recibida': 15000, 'estado': 'OK',
                             'notas': '', 'lote': 'L-PROV-9988', 'fecha_vencimiento': '',
                             'recipientes': 1}], 'rcp-adm-2')
    assert r.status_code == 200, r.data[:300]
    conn = sqlite3.connect(os.environ["DB_PATH"])
    fila = conn.execute(
        "SELECT lote, COALESCE(lote_proveedor,'') FROM movimientos "
        "WHERE numero_oc=? AND material_id='MP00050' ORDER BY id DESC LIMIT 1", (OC_MP,)).fetchone()
    conn.close()
    assert fila, 'no quedó el movimiento de kardex'
    assert fila[0] == 'L-PROV-9988', 'el lote tecleado no llegó al kardex: %s' % (fila[0],)
    assert fila[1] == 'L-PROV-9988', (
        'el lote del proveedor quedó vacío · se sigue leyendo una llave que la pantalla no manda')


def test_sin_lote_avisa_que_quedo_uno_provisional(app, db_clean):
    """No bloquea, pero tampoco lo esconde: quien recibe tiene que enterarse de que ese lote no
    cruza con el CoA."""
    _sembrar_oc(app, OC_MP, 'Materia Prima', [('MP00050', 'CAPRYLYL GLUCOSIDE')])
    c = _login(app, 'catalina')
    r = _recibir(c, OC_MP, [{'codigo_mp': 'MP00050', 'cantidad_recibida': 15000, 'estado': 'OK',
                             'notas': '', 'lote': '', 'fecha_vencimiento': '', 'recipientes': 1}],
                 'rcp-adm-3')
    assert r.status_code == 200, r.data[:300]
    body = r.get_json() or {}
    avisos = body.get('lotes_sinteticos') or body.get('lotes_sinteticos_advertencia') or []
    assert avisos, ('no avisó que el lote quedó provisional · el receptor creería que la '
                    'trazabilidad está completa: %s' % body)


def test_no_se_libera_un_lote_con_numero_provisional(app, db_clean):
    """Acá vive ahora el control INVIMA: el lote provisional no cruza con el CoA del proveedor,
    así que no puede pasar a VIGENTE. Es lo que permite que la recepción administrativa sea
    laxa sin perder trazabilidad."""
    _sembrar_oc(app, OC_MP, 'Materia Prima', [('MP00050', 'CAPRYLYL GLUCOSIDE')])
    c = _login(app, 'catalina')
    assert _recibir(c, OC_MP, [{'codigo_mp': 'MP00050', 'cantidad_recibida': 15000,
                                'estado': 'OK', 'notas': '', 'lote': '',
                                'fecha_vencimiento': '', 'recipientes': 1}],
                    'rcp-adm-4').status_code == 200
    conn = sqlite3.connect(os.environ["DB_PATH"])
    mov = conn.execute("SELECT id, lote FROM movimientos WHERE numero_oc=? "
                       "AND material_id='MP00050' ORDER BY id DESC LIMIT 1", (OC_MP,)).fetchone()
    conn.close()
    assert mov and str(mov[1]).startswith('OC-'), 'esperaba un lote sintético, quedó %s' % (mov,)

    qc = _login(app, 'sebastian')
    r = qc.post('/api/lotes/liberar', json={'id': mov[0], 'accion': 'APROBAR'},
                headers=csrf_headers())
    assert r.status_code == 422, (
        'liberó un lote con número provisional · eso rompe el cruce con el CoA: %s' % r.data[:300])
    assert (r.get_json() or {}).get('codigo') == 'LOTE_SINTETICO_SIN_LIBERAR', r.data[:300]

    # y el lote sigue en cuarentena (no se consumió el intento)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    est = conn.execute("SELECT estado_lote FROM movimientos WHERE id=?", (mov[0],)).fetchone()[0]
    conn.close()
    assert str(est).upper().startswith('CUARENTENA'), est


def test_los_envases_tampoco_exigen_lote(app, db_clean):
    """La OC de la captura era de envases: la recepción administrativa de MEE nunca pidió lote y
    tiene que seguir así."""
    _sembrar_oc(app, OC_MEE, 'Material de Empaque',
                [('MEE-ENV-002', 'SUERO NIACINAMIDA'), ('MEE-GOT-005', 'GREY SCREW PUMP DROPPER')])
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for cod, nom in (('MEE-ENV-002', 'SUERO NIACINAMIDA'),
                         ('MEE-GOT-005', 'GREY SCREW PUMP DROPPER')):
            cur.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, estado) "
                        "VALUES (?,?,'Frasco','Activo') ON CONFLICT(codigo) DO NOTHING", (cod, nom))
        conn.commit()
    c = _login(app, 'catalina')
    r = _recibir(c, OC_MEE,
                 [{'codigo_mp': 'MEE-ENV-002', 'cantidad_recibida': 15000, 'estado': 'OK',
                   'notas': '', 'lote': '', 'fecha_vencimiento': '', 'recipientes': 1},
                  {'codigo_mp': 'MEE-GOT-005', 'cantidad_recibida': 15000, 'estado': 'OK',
                   'notas': '', 'lote': '', 'fecha_vencimiento': '', 'recipientes': 1}],
                 'rcp-adm-5')
    assert r.status_code == 200, r.data[:400]


def test_la_pantalla_llega_con_quien_recibe_ya_puesto(app, db_clean):
    """El campo "Recibido por" nacía vacío y la pantalla frena el registro si falta, con el
    mensaje abajo del formulario, lejos de donde se está mirando: una traba silenciosa. Ahora
    llega con el usuario de la sesión (editable: a veces recibe otra persona)."""
    c = _login(app, 'catalina')
    r = c.get('/recepcion')
    assert r.status_code == 200
    html = r.data.decode('utf-8', 'replace')
    assert '__RECEPTOR__' not in html, 'quedó el placeholder sin reemplazar'
    assert 'id="receptor-input"' in html and 'value="catalina"' in html, (
        'la pantalla no pre-llena quién recibe')


def test_una_oc_pagada_no_dice_que_ya_fue_recibida(app, db_clean):
    """PAGADA no es RECIBIDA: con varios proveedores se paga por anticipado y la mercancía llega
    después (por eso el backend permite recibir una OC 'Pagada'). El aviso las trataba igual y
    decía "ya fue recibida, el registro está completo" justo mientras se intentaba recibirla —
    sonaba a que la pantalla estaba cerrada."""
    c = _login(app, 'catalina')
    html = c.get('/recepcion').data.decode('utf-8', 'replace')
    i = html.find("d.estado === 'Pagada'")
    assert i > 0, 'ya no se distingue el estado Pagada'
    # La ventana se mide hasta el siguiente `else if`, no por un largo fijo: al pasar los colores
    # a tokens la rama creció y un corte de N caracteres dejaba el texto afuera.
    j = html.find('else if', i)
    ventana = html[i:j if j > i else i + 1200]
    assert 'ya fue recibida' not in ventana, (
        'la OC pagada sigue diciendo que ya fue recibida')
    assert 'pago anticipado' in ventana.lower(), ventana[:400]


def test_el_caso_exacto_de_catalina(app, db_clean):
    """La captura del 27-jul: OC-2026-0274, HANDLER SAS, estado **Pagada**, categoría MP, un solo
    ítem de 1000 g, campo LOTE vacío, "Recibido por: c.erazo" → "Recepción bloqueada por
    validaciones".

    Se deja como test porque es el escenario real que la tuvo frenada, no una aproximación.
    """
    from database import get_db
    NUM = 'OC-ZZCAT-0274'
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for t, w in (('ordenes_compra_items', 'numero_oc'), ('solicitudes_compra', 'numero_oc'),
                     ('ordenes_compra', 'numero_oc'), ('oc_recepcion_dedup', 'numero_oc')):
            cur.execute("DELETE FROM %s WHERE %s=?" % (t, w), (NUM,))
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                    "valor_total, creado_por) VALUES (?,?,?,?,?,?,?)",
                    (NUM, 'HANDLER SAS', 'Pagada', 'MP', '2026-07-14', 149940, 'catalina'))
        cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                    "cantidad_g, precio_unitario) VALUES (?,?,?,?,?)",
                    (NUM, 'MP00063', 'PENTAERYTHRITYL TETRA-DI-T-BUTYL HYDROXYHYDROCINNAMATE',
                     1000, 149.94))
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "numero_oc, categoria) VALUES (?,?,?,?,?,?)",
                    ('SOL-ZZCAT-0274', '2026-07-14', 'Aprobada', 'catalina', NUM, 'Materia Prima'))
        conn.commit()

    c = _login(app, 'catalina')
    r = c.post('/api/ordenes-compra/%s/recibir' % NUM,
               json={'observaciones_recepcion': '', 'tiene_discrepancias': 0,
                     'items_recepcion': [{'codigo_mp': 'MP00063', 'cantidad_recibida': 1000,
                                          'estado': 'OK', 'notas': '', 'lote': '',
                                          'fecha_vencimiento': '', 'recipientes': 1}],
                     'receptor_nombre': 'c.erazo', 'recepcion_id': 'rcp-cat-0274'})
    assert r.status_code == 200, ('sigue bloqueada en el caso real de Catalina: %s'
                                  % r.data[:400])
    assert (r.get_json() or {}).get('ok'), r.data[:300]
