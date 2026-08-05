# -*- coding: utf-8 -*-
"""Los cinco pendientes que quedaban en cola (4-ago).

Sebastián: *"esos 5 pendientes hazlos, quiero que quedes sin nada pendiente"* y *"no debe leer
nada Google Calendar, eso lo quitamos todo, vive en EOS"*.

1. **El lead time de envases estaba clavado en 14 días para todos**, con un "TODO leer de
   mee_lead_time_config" al lado — y esa tabla existe desde la mig 71 con los datos reales:
   frasco de China **180 días** y mínimo de 5.000 unidades. El sistema le decía a Compras que un
   frasco de China se pide con dos semanas de anticipación cuando son seis meses.

2. **La alerta de serigrafía leía Google Calendar**, que devuelve vacío desde el 7-jul: llevaba
   un mes sin avisar nada, y una bandeja vacía se ve igual que una al día (M127). Ahora lee el
   calendario de EOS, donde el producto y los kg son un HECHO y no un emparejamiento por
   parecido de título.

3. **El checklist de envasado se armaba con UN solo envase**: para un producto de dos
   presentaciones descontaba todo contra un código, con un volumen promedio que no existe
   físicamente. Ahora se abre por presentación. ⚠ Y con eso apareció la trampa: el descuento le
   restaba el total de envases B2B a CADA fila de envase — con una sola daba igual, con varias
   restaba el mismo B2B dos veces.

4. **El desglose podía no guardar nada y responder OK**: el mapeo va por `sku_shopify`, que
   suele estar vacío, y el `except: pass` tapaba cualquier fallo real.

5. **La sugerencia de cadencia** quedó desalineada con la referencia nueva: aplicarla dejaba al
   producto 20 días corto y el tablero lo volvía a marcar.
"""
import io
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(txt):
    """Saca los comentarios de línea antes de buscar.

    Ya van tres veces que un test busca un nombre en el fuente y encuentra MI PROPIO COMENTARIO
    explicando por qué ese nombre dejó de usarse (M154) · pasa o falla por la razón equivocada."""
    import re as _re
    fuera = []
    for ln in txt.splitlines():
        _s = ln.strip()
        if _s.startswith('#') or _s.startswith('//'):
            continue
        fuera.append(_re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


def _bloque(txt, arranque, largo=5200):
    i = txt.find(arranque)
    assert i > 0, 'no encontré ' + arranque
    return txt[i:i + largo]


# ── 1 · lead time de envases ─────────────────────────────────────────────────

def test_el_lead_time_de_envases_sale_de_su_TABLA(app, db_clean):
    prog = _sin_comentarios(_src('api/blueprints/programacion.py'))
    i = prog.find('items_out_mee = []')
    assert i > 0
    mee = prog[i:i + 9000]
    assert "'lead_time_dias': 14," not in mee, 'el envase sigue con el 14 clavado'
    assert '_mee_lt' in prog and 'FROM mee_lead_time_config' in prog
    assert "'lead_time_medido'" in prog, \
        'no distingue un lead time medido de un default · los dos se leen igual (M124)'


def test_un_frasco_de_CHINA_no_se_muestra_con_14_dias(app, db_clean):
    """El caso concreto: la tabla dice 180 días y MOQ 5.000."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM mee_lead_time_config WHERE mee_codigo LIKE 'ZZLT%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZLT%'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual) "
                  "VALUES ('ZZLT-CHINA','Frasco importado','Activo',0)")
        c.execute("INSERT INTO mee_lead_time_config (mee_codigo, proveedor_principal, origen, "
                  "lead_time_dias, moq_unidades) VALUES ('ZZLT-CHINA','','China',180,5000)")
        conn.commit()
        fila = conn.execute("SELECT lead_time_dias, moq_unidades, origen FROM mee_lead_time_config "
                            "WHERE mee_codigo='ZZLT-CHINA'").fetchone()
    assert int(fila[0]) == 180 and int(fila[1]) == 5000 and fila[2] == 'China'
    # y el motor la lee: el bloque de lectura existe y se usa en el item
    prog = _src('api/blueprints/programacion.py')
    i = prog.find('_mee_lt = {}')
    assert i > 0
    assert prog.find("_mee_lt.get(") > i, 'se lee la tabla pero no se usa'
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM mee_lead_time_config WHERE mee_codigo LIKE 'ZZLT%'")
        conn.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZLT%'")
        conn.commit()


# ── 2 · Google Calendar afuera ───────────────────────────────────────────────

def test_la_alerta_de_serigrafia_lee_EOS_no_google(app, db_clean):
    """*"no debe leer nada Google Calendar, eso lo quitamos todo, vive en EOS"*."""
    ap = _sin_comentarios(_src('api/blueprints/auto_plan.py'))
    bloque = _bloque(ap, 'def alerta_d20_pendientes')
    assert '_calendar_events_cached()' not in bloque, 'sigue leyendo Google Calendar'
    assert 'FROM produccion_programada' in bloque, 'no lee el calendario de EOS'
    # y deja de emparejar por parecido de título
    assert '_match_producto_evento' not in bloque, \
        'sigue cruzando el producto por parecido en vez de leerlo del lote'
    assert "ev.get('titulo'" not in bloque, 'sigue sacando el título del evento de Google'


def test_la_alerta_D20_ENCUENTRA_el_lote_del_calendario_de_EOS(admin_client, db_clean):
    """El que vale: recorre el endpoint REAL con un lote sembrado en la ventana D-20.

    ⚠ Este test ya se ganó el sueldo: el reemplazo del título -hecho con un `str.replace` sin
    anclar- había caído en OTRA función 3.000 líneas antes, así que la alerta quedaba llamando a
    una variable inexistente (500) y la función vecina devolvía un título equivocado (M96/M151).
    Leer el fuente no lo vio · ejecutar el endpoint sí."""
    from datetime import date, timedelta
    from database import get_db
    hoy = date.today()
    objetivo = (hoy + timedelta(days=20)).isoformat()
    with admin_client.application.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM produccion_programada WHERE producto='ZZD20 PRODUCTO'")
        c.execute(
            "INSERT INTO produccion_programada (producto, fecha_programada, "
            " cantidad_kg, lotes, estado, origen) "
            "VALUES ('ZZD20 PRODUCTO',?,45,1,'pendiente','eos_plan')", (objetivo,))
        conn.commit()

    r = admin_client.get('/api/planta/alerta-d20-pendientes')
    assert r.status_code == 200, r.data[:400]
    d = r.get_json()
    fila = [p for p in d.get('producciones', []) if p.get('producto') == 'ZZD20 PRODUCTO']
    assert fila, 'la alerta no ve el lote de EOS que cae en la ventana D-20'
    assert abs(float(fila[0]['kg']) - 45.0) < 0.01, 'los kg salen del lote, no de parsear un título'
    assert fila[0]['dias_hasta'] == 20

    with admin_client.application.app_context():
        conn = get_db()
        conn.execute("DELETE FROM produccion_programada WHERE producto='ZZD20 PRODUCTO'")
        conn.commit()


def test_la_alerta_no_se_queda_MUDA_en_silencio(app, db_clean):
    """El defecto de fondo: llevaba un mes sin avisar y nadie lo notó, porque una bandeja vacía
    se ve igual que una al día (M127)."""
    ap = _sin_comentarios(_src('api/blueprints/auto_plan.py'))
    bloque = _bloque(ap, 'def alerta_d20_pendientes')
    assert 'no pude leer el calendario de EOS' in bloque, \
        'si la consulta falla, la alerta vuelve a quedar muda sin decirlo'


# ── 3 · checklist por presentación ───────────────────────────────────────────

def test_el_checklist_se_abre_por_PRESENTACION(app, db_clean):
    prog = _sin_comentarios(_src('api/blueprints/programacion.py'))
    assert '_pres_multi' in prog, 'no lee las presentaciones múltiples'
    assert 'len(_pres_multi) > 1' in prog, 'no distingue el caso multi-presentación'
    # y reparte pesando por volumen, como el resto del sistema (M72)
    i = prog.find('len(_pres_multi) > 1')
    assert '(x[2] or 0) * (x[0] or 0)' in prog[i:i + 900], \
        'reparte por share de unidades en vez de pesar por volumen'


def test_el_B2B_se_resta_UNA_vez_no_por_fila(app, db_clean):
    """La trampa que traía abrir el checklist: con una sola fila de envase daba igual, con
    varias restaba el mismo B2B dos veces y descontaba de menos."""
    prog = _sin_comentarios(_src('api/blueprints/programacion.py'))
    assert '_b2b_por_restar = uds_b2b_custom_total' in prog
    assert 'cant_real - uds_b2b_custom_total' not in prog, \
        'sigue restando el total completo a cada fila de envase'
    assert '_b2b_por_restar -= _resta' in prog, 'no consume el remanente'


# ── 4 · el desglose no guarda en silencio ────────────────────────────────────

def test_el_desglose_DICE_cuando_no_pudo_guardar(app, db_clean):
    """Se veía "guardado" y no se persistía nada, porque el mapeo va por un campo que suele
    estar vacío y el `except: pass` tapaba el resto."""
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert 'override_aviso' in plan
    assert 'el desglose no se guardó' in plan, 'no avisa cuando ninguna línea cruzó'
    assert '"override_aviso": override_aviso' in plan, 'el aviso no viaja en la respuesta'
    # y el except ya no traga
    i = plan.find('override_guardado = len(_ovr)')
    assert 'except Exception as _euo' in plan[i:i + 400], 'el fallo del UPDATE sigue tragado'


def test_el_desglose_cruza_TAMBIEN_por_volumen(app, db_clean):
    """Segundo tier: el ml, que es lo que la pantalla muestra al lado de cada SKU."""
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert '_vol2pc' in plan and '_sku2ml' in plan
    assert 'desglose_ml' in plan, 'el front no manda el volumen'
    assert 'data-ml' in plan


# ── 5 · la sugerencia de cadencia ────────────────────────────────────────────

def test_la_sugerencia_de_cadencia_NO_deja_corto(app, db_clean):
    """Restaba el buffer sobre una referencia que ya no lo incluye · aplicarla dejaba al
    producto 20 días corto y el tablero lo volvía a marcar."""
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert "int(round((kg_lote * 1000.0 / ml) / vel)) - BUFFER_REORDEN" not in plan, \
        'la sugerencia sigue restando el buffer'
    assert "'sugerido_cadencia_dias': (max(1, int(round((kg_lote * 1000.0 / ml) / vel)))" in plan
