# -*- coding: utf-8 -*-
"""Un lote que NO está vencido pero el sistema cree que sí: cómo se saca de la lista.

Sebastián 22-ago, mirando *Lotes YA vencidos*: *"me sale un lote vencido aquí, pero no está
vencido y no sé cómo sacarlo"*.

Y no había forma de sacarlo bien, porque **las dos acciones de esa tabla son las dos
equivocadas** para el caso:

  · **Dar de baja** borra los movimientos del lote. Para un lote que está sano y en el estante
    eso destruye el material bueno.
  · **Silenciar** apaga la alerta y deja la fecha mala puesta, así que el lote sigue fuera del
    stock usable y producción sigue sin poder tomarlo. Es lo peor: se ve resuelto y el material
    queda igual de bloqueado, ahora sin nada que lo recuerde (M100/M129).

Lo que faltaba es **corregir la fecha**, que es lo que de verdad pasa: alguien tecleó mal el
vencimiento al recibir. El endpoint existía y ninguna puerta de esta pantalla llevaba a él
(M121).

⚠ Y corregir la fecha **no alcanza sola**: el cron de las 7:50 ya dejó el lote en
`estado_lote='VENCIDO'`, y el stock canónico excluye ese estado. Cambiar sólo la fecha lo saca
de la alerta y lo deja igual de invisible para producción -- arreglado en apariencia y roto de
una forma mucho más difícil de ver.
"""
import pytest

CODIGO = 'MPVENCFIX'
LOTE = 'LOTE-VENC-1'
LOTE_CUAR = 'LOTE-CUAR-1'
EST = 'EST-VENC-FIX'
FUTURO = '2028-12-31'
PASADO = '2026-04-15'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


@pytest.fixture()
def vencido_por_error(app):
    """Como lo deja el cron: fecha pasada y `estado_lote='VENCIDO'`.

    Más un lote en CUARENTENA con fecha pasada, que es el borde: corregirle la fecha NO puede
    liberarlo, porque eso es material que Calidad retuvo (M31/M23).
    """
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, 'MP VENCIMIENTO MAL TECLEADO', 'TEST INCI'))
        for lote, estado in ((LOTE, 'VENCIDO'), (LOTE_CUAR, 'CUARENTENA')):
            c.execute(
                "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                " fecha, operador, estanteria, fecha_vencimiento, estado_lote) "
                "VALUES (?,?,'Entrada',?,?,?,?,?,?,?)",
                (CODIGO, 'MP VENCIMIENTO MAL TECLEADO', 1000.0, lote,
                 '2026-08-01 08:00:00', 'test', EST, PASADO, estado))
        c.commit()
    yield
    _limpiar(app)


def _estado(app, lote):
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT UPPER(COALESCE(estado_lote,'')), COALESCE(fecha_vencimiento,'') "
            "  FROM movimientos WHERE material_id=? AND lote=?", (CODIGO, lote)).fetchone()
    return (r[0], r[1]) if r else ('', '')


def _usable(client, lote):
    """Lo que el sistema considera stock usable de ese lote, por la puerta que todos leen."""
    r = client.get('/api/inventario/cuadre-lotes?est=' + EST)
    for l in (r.get_json() or {}).get('lotes') or []:
        if l.get('codigo_mp') == CODIGO and l.get('lote') == lote:
            return l.get('stock_sistema')
    return None


# ─────────────────────────────────────────────────────────────────────────────
# el estado de partida: el lote está bloqueado
# ─────────────────────────────────────────────────────────────────────────────

def test_un_lote_marcado_VENCIDO_no_cuenta_como_stock(admin_client, vencido_por_error):
    """Si esto no fuera cierto, el resto del archivo no probaría nada."""
    assert _usable(admin_client, LOTE) is None, (
        'el lote vencido sí contaba como stock: el escenario no es el que se quiere probar')


# ─────────────────────────────────────────────────────────────────────────────
# corregir la fecha tiene que DESBLOQUEARLO, o no sirve de nada
# ─────────────────────────────────────────────────────────────────────────────

def test_corregir_la_fecha_devuelve_el_lote_al_stock(admin_client, vencido_por_error):
    r = admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                         json={'fecha_vencimiento': FUTURO,
                               'motivo': 'estaba mal tecleada al recibir'})
    assert r.status_code == 200, r.data[:250]
    estado, fecha = _estado(admin_client.application, LOTE)
    assert fecha == FUTURO, 'no guardó la fecha nueva: %r' % fecha
    assert estado == 'VIGENTE', (
        'la fecha quedó bien pero el lote sigue en %r: sale de la alerta y sigue sin poder '
        'usarse, que es peor que no arreglarlo' % estado)
    assert _usable(admin_client, LOTE) == 1000.0, (
        'corregir la fecha no devolvió el lote al stock usable')


def test_la_respuesta_DICE_que_el_lote_volvio(admin_client, vencido_por_error):
    """Si no lo dice, quien corrige no sabe si tiene que hacer algo más."""
    r = admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                         json={'fecha_vencimiento': FUTURO, 'motivo': 'mal tecleada'})
    d = r.get_json() or {}
    assert d.get('reactivado') is True, 'no declara que el lote volvió a quedar disponible'


def test_produccion_puede_TOMARLO_otra_vez(admin_client, vencido_por_error):
    """La prueba que vale: que el motor del descuento lo vuelva a ver (M25 lo excluye por
    FECHA además de por estado, así que las dos mitades tienen que quedar bien)."""
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                     json={'fecha_vencimiento': FUTURO, 'motivo': 'mal tecleada'})
    import sys
    sys.path.insert(0, 'api')
    from database import get_db
    from blueprints.programacion import _lotes_disponibles_fefo
    with admin_client.application.app_context():
        lotes = _lotes_disponibles_fefo(get_db().cursor(), CODIGO)
    assert any(str(x[0]) == LOTE for x in (lotes or [])), (
        'producción sigue sin poder tomar el lote después de corregir la fecha')


# ─────────────────────────────────────────────────────────────────────────────
# el borde que lo hace seguro
# ─────────────────────────────────────────────────────────────────────────────

def test_corregir_la_fecha_NO_libera_lo_que_Calidad_retuvo(admin_client, vencido_por_error):
    """Un lote en cuarentena con la fecha corregida sigue en cuarentena: corregir un dato no
    puede liberar material por la puerta de atrás (M31/M23)."""
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE_CUAR),
                     json={'fecha_vencimiento': FUTURO, 'motivo': 'mal tecleada'})
    estado, fecha = _estado(admin_client.application, LOTE_CUAR)
    assert fecha == FUTURO, 'no corrigió la fecha del lote en cuarentena'
    assert estado == 'CUARENTENA', (
        'corregir la fecha liberó un lote que Calidad tenía retenido: %r' % estado)


def test_poner_una_fecha_PASADA_vuelve_a_bloquear(admin_client, vencido_por_error):
    """La simetría: si la fecha buena resulta ser pasada, el lote se marca en el momento y no
    se queda VIGENTE esperando al cron de mañana."""
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                     json={'fecha_vencimiento': FUTURO, 'motivo': 'primero se corrige'})
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                     json={'fecha_vencimiento': PASADO, 'motivo': 'no, sí estaba vencido'})
    estado, _ = _estado(admin_client.application, LOTE)
    assert estado == 'VENCIDO', 'quedó VIGENTE con fecha pasada: %r' % estado


def test_queda_rastro_de_la_fecha_ANTERIOR(admin_client, vencido_por_error):
    from database import get_db
    admin_client.put('/api/lotes/%s/%s/fecha-vencimiento' % (CODIGO, LOTE),
                     json={'fecha_vencimiento': FUTURO, 'motivo': 'mal tecleada al recibir'})
    with admin_client.application.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(detalle,'') || COALESCE(antes,'') || COALESCE(despues,'') "
            "  FROM audit_log WHERE accion='EDITAR_FECHA_VENC_LOTE' AND registro_id LIKE ?",
            (CODIGO + '%',)).fetchall()
    assert filas, 'corregir un vencimiento no dejó rastro'
    texto = ' '.join(f[0] for f in filas)
    assert PASADO in texto, 'el rastro no dice qué fecha tenía antes'
    assert 'mal tecleada al recibir' in texto, 'perdió el motivo'


# ─────────────────────────────────────────────────────────────────────────────
# y la puerta: sin botón, la capacidad no existe (M121)
# ─────────────────────────────────────────────────────────────────────────────

def test_la_tabla_de_vencidos_OFRECE_corregir_la_fecha(app):
    # El JS de esta pantalla vive en un BUNDLE, no en el HTML: buscarlo en el HTML concluye
    # que la funcion no existe (M166/M216).
    from templates_py.dashboard_html import DASHBOARD_CORE_JS as H
    i = H.find('_renderSeccionLotes')
    assert i != -1
    j = H.find('function _renderSeccionMEE', i)
    cuerpo = H[i:j if j > i else i + 12000]
    assert 'corregir-venc' in cuerpo, (
        'la tabla de lotes vencidos no ofrece corregir la fecha: las dos acciones que hay '
        '(dar de baja y silenciar) destruyen el lote o lo dejan bloqueado en silencio')
    assert 'fecha-vencimiento' in H, 'nadie llama al endpoint que corrige la fecha'
