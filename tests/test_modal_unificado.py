# -*- coding: utf-8 -*-
"""Los dos modales cruzan exacto, y muestran presentaciones + foto del envase (4-ago).

Sebastián: *"quisiera que se viera igual que el de Necesidades, colocando eso que decimos
adicional, así hacemos que crucen perfecto y no tengamos cosas diferentes"*, y antes:
*"debería aparecer la foto del envase que se usará, desde la bodega, para ir anclando eso ·
aquí deben salir las presentaciones del producto · aquí debe decir cuánto se envasará de cada
uno"*.

Lo que había: cada modal preguntaba a SU endpoint. El del calendario a `listo-producir?lotes=1`
(un lote del maestro de fórmulas) y el de Necesidades a `disponibilidad-para-kg` (los kg que se
van a programar, con el stock que la producción puede consumir de verdad). Dos respuestas
distintas sobre el mismo producto, y ninguna mostraba la foto del envase — que existe en el
maestro desde hace meses y se carga desde Bodega.
"""
import io
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROD = 'ZZUNI PRODUCTO'
FR30, FR10, TAPA = 'ZZUNI-FR30', 'ZZUNI-FR10', 'ZZUNI-TP'


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'ZZUNI%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'ZZUNI%'")
        c.execute("DELETE FROM movimientos WHERE material_id LIKE 'ZZUNI%'")
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZUNI%'")
        conn.commit()


def _sembrar(app):
    """Un producto de DOS presentaciones (30 ml y 10 ml), como el SUERO ILUMINADOR TRX."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO formula_headers (producto_nombre, activo, lote_size_kg) "
                  "VALUES (?,1,10)", (PROD,))
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo, controla_stock) "
                  "VALUES ('ZZUNI-MP','Activo',1,1)")
        c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                  "porcentaje, cantidad_g_por_lote) VALUES (?, 'ZZUNI-MP','Activo',100,0)", (PROD,))
        c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                  "fecha, estado_lote) VALUES ('ZZUNI-MP','x','Entrada',9000000,'L1',"
                  "date('now','-5 hours'),'VIGENTE')")
        # el frasco de 30 ml CON foto cargada desde bodega · el de 10 ml sin foto
        for cod, desc, img in ((FR30, 'Frasco 30 ml', 'https://ejemplo/f30.png'),
                               (FR10, 'Frasco 10 ml', ''),
                               (TAPA, 'Tapa', '')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual, "
                      "imagen_url) VALUES (?,?, 'Activo', 0, ?)", (cod, desc, img))
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, "
                      "responsable) VALUES (?, 'Entrada', 50000, 'und','SEED','t')", (cod,))
        for vol, env, ventas in ((30, FR30, 800), (10, FR10, 200)):
            c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                      "etiqueta, volumen_ml, envase_codigo, tapa_codigo, ventas_mes_referencia, "
                      "activo) VALUES (?,?,?,?,?,?,?,1)",
                      (PROD, 'ZZUNI-P%d' % vol, '%d ml' % vol, vol, env, TAPA, ventas))
        conn.commit()


def _disp(app, kg=100):
    from database import get_db
    from blueprints.plan import disponibilidad_para_kg
    with app.app_context():
        return disponibilidad_para_kg(get_db(), PROD, kg)


# ── lo que Sebastián pidió ver ───────────────────────────────────────────────

def test_salen_LAS_PRESENTACIONES_del_producto(app, db_clean):
    _limpiar(app); _sembrar(app)
    ps = _disp(app)['envases']['presentaciones']
    assert len(ps) == 2, 'no salieron las dos presentaciones'
    vols = sorted(p['volumen_ml'] for p in ps)
    assert vols == [10.0, 30.0]


def test_dice_CUANTAS_UNIDADES_salen_de_cada_una(app, db_clean):
    """*"aquí debe decir cuánto se envasará de cada producto"*. Y la suma tiene que cerrar con
    los kilos del lote: si no cierra, el desglose es decorativo."""
    _limpiar(app); _sembrar(app)
    ps = _disp(app, kg=100)['envases']['presentaciones']
    por_vol = {p['volumen_ml']: p for p in ps}
    assert por_vol[30.0]['uds'] > 0 and por_vol[10.0]['uds'] > 0
    ml_total = sum(p['uds'] * p['volumen_ml'] for p in ps)
    assert abs(ml_total / 1000.0 - 100) < 1.5, \
        'las unidades no cierran con los 100 kg del lote: %s' % ml_total


def test_el_reparto_PESA_POR_VOLUMEN_no_por_unidades(app, db_clean):
    """M72: una unidad de 30 ml se lleva el TRIPLE de granel que una de 10, así que aplicar el
    share de unidades al kg sub-asigna la presentación grande. Con ventas 800/200, el 30 ml
    tiene que llevarse mucho más del 80% del bulk."""
    _limpiar(app); _sembrar(app)
    ps = _disp(app, kg=100)['envases']['presentaciones']
    por_vol = {p['volumen_ml']: p for p in ps}
    assert por_vol[30.0]['porcion'] > 90, \
        'el 30 ml se llevó sólo %s%% del bulk · se repartió por unidades' % por_vol[30.0]['porcion']
    # y las UNIDADES sí quedan proporcionales a las ventas (800 vs 200 = 4 a 1)
    ratio = por_vol[30.0]['uds'] / max(1, por_vol[10.0]['uds'])
    assert 3.0 < ratio < 5.0, 'las unidades no siguen la proporción de ventas: %.2f' % ratio


def test_viene_la_FOTO_del_envase_de_bodega(app, db_clean):
    """*"debería aparecer la foto del envase que se usará, desde la bodega"*. El dato ya existía
    en el maestro (se carga desde Bodega) y no llegaba a esta pantalla."""
    _limpiar(app); _sembrar(app)
    d = _disp(app)
    fotos = {i['codigo']: i.get('imagen_url', '') for i in d['envases']['items']}
    assert fotos.get(FR30) == 'https://ejemplo/f30.png', 'no trajo la foto del envase'
    # el que no tiene foto viene vacío, no inventado
    assert fotos.get(FR10) == ''
    # y la foto también viaja pegada a la presentación que la usa
    p30 = [p for p in d['envases']['presentaciones'] if p['volumen_ml'] == 30.0][0]
    fr = [c for c in p30['componentes'] if c['tipo'] == 'frasco'][0]
    assert fr['imagen_url'] == 'https://ejemplo/f30.png'


def test_un_envase_DESCONTINUADO_se_declara(app, db_clean):
    """Nada bloquea hoy una presentación que apunta a un envase dado de baja · si no se dice,
    sorprende cuando alguien va a pedirlo (M124)."""
    from database import get_db
    _limpiar(app); _sembrar(app)
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE maestro_mee SET estado='Inactivo' WHERE codigo=?", (FR10,))
        conn.commit()
    items = {i['codigo']: i for i in _disp(app)['envases']['items']}
    assert items[FR10]['descontinuado'] is True
    assert items[FR30]['descontinuado'] is False


# ── que los dos modales crucen ───────────────────────────────────────────────

def test_el_CALENDARIO_usa_el_mismo_endpoint_que_necesidades(app, db_clean):
    """El nudo de todo: dos pantallas que contestan lo mismo tienen que preguntarle a la misma
    cuenta. Antes una usaba `listo-producir?lotes=1` (un lote del maestro) y la otra los kg
    reales de la cadena."""
    plan = _src('api/blueprints/plan.py')
    dash = _src('api/templates_py/dashboard_html.py')
    assert '/api/plan/disponibilidad-para-kg' in plan, 'el calendario no usa el bloque compartido'
    assert '/api/plan/disponibilidad-para-kg' in dash, 'Necesidades no usa el bloque compartido'
    assert '_calDisponibilidad(producto, kg)' in plan
    # el bloque viejo queda SÓLO de respaldo, dentro del catch
    i = plan.find('try{ _calDisponibilidad(producto, kg); }catch(e){')
    assert i > 0, 'no se llama al bloque nuevo'
    assert '_calCargarListoProducir(producto)' in plan[i:i + 500], \
        'se borró el respaldo · si el bloque nuevo falla queda un hueco (M112)'


def test_los_dos_pintan_LAS_MISMAS_secciones(app, db_clean):
    """Con dientes: si a uno le falta una sección, volvimos a tener dos pantallas distintas."""
    plan = _src('api/blueprints/plan.py')
    dash = _src('api/templates_py/dashboard_html.py')
    for marca in ('De este lote salen', 'Con qu', 'Materia prima', 'Envases',
                  'en serigraf', 'esperando arte', 'sin envase asignado'):
        assert marca in plan, 'al calendario le falta: %s' % marca
        assert marca in dash, 'a Necesidades le falta: %s' % marca


def test_el_bloque_compartido_no_dispara_una_consulta_por_tecla(app, db_clean):
    """Se llama al cambiar los kg · sin debounce ni descarte de respuestas viejas, tres
    consultas concurrentes ocupan los 3 workers (M43)."""
    plan = _src('api/blueprints/plan.py')
    dash = _src('api/templates_py/dashboard_html.py')
    for src, quien in ((plan, 'calendario'), (dash, 'Necesidades')):
        assert 'setTimeout' in src and 'clearTimeout' in src, '%s sin debounce' % quien
    assert '_CAL_DISP_SEQ' in plan and '_DISP_SEQ' in dash, \
        'sin token de secuencia una respuesta vieja pisa a la nueva'
