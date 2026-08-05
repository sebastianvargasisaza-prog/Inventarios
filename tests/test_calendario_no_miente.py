# -*- coding: utf-8 -*-
"""Lo que el Calendario afirmaba sin haberlo comprobado (4-ago · auditoría de las 5 pestañas).

Sebastián: *"todo calendario tiene muchas cosas por mejorar"*. Los defectos no eran de estilo:
eran pantallas que decían cosas que no había mirado nadie.

1. **Factibilidad y Abastecimiento se contradecían sobre el MISMO calendario.** Factibilidad
   contaba sólo lo fijado a mano; Abastecimiento, además, lo proyectado y lo sugerido. Con un
   plan armado con "Proyectar 2 años" (casi todo `eos_proyeccion`), una decía "nada que comprar,
   el plan es ejecutable" mientras la otra mostraba déficit. Y el subtítulo prometía "¿alcanzan
   las MP para TODO lo programado?".

2. **El semáforo de "Alistar envases" estaba muerto.** La urgencia se escribía UNA vez al crear
   la orden con el valor 'media' y nunca se recalculaba; como 'media' siempre es truthy, el
   `or` jamás llegaba al cálculo real. Una orden vencida hace 5 días se pintaba amarilla, con
   el texto "hace 5d" al lado.

3. **Estacionalidad marcaba pico en TODOS.** Usaba el mes MÁS ALTO (que existe siempre) sin
   compararlo contra el umbral, y la lista correcta se calculaba y no se usaba. Además el mes
   EN CURSO se promediaba como si estuviera completo: el 4 de agosto, agosto entraba con 4 días
   contra los 31 de los agostos anteriores → índice hundido y crecimiento año-contra-año
   siempre subestimado. Ese número alimenta el acelerador de compras.

4. **Tres KPIs clavados en cero** y una lista que decía "todo cubierto" sin haber calculado
   nada: se llenan sólo con el autoplan de IA, cuyo botón está oculto.
"""
import io
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(txt):
    """Saca los comentarios de línea (Python `#` y JS `//`) antes de buscar.

    Dos veces hoy un test buscó un nombre y encontró MI PROPIO COMENTARIO explicando por qué ese
    nombre ya no se usa · pasaba o fallaba por la razón equivocada. Se busca en el código."""
    import re as _re
    fuera = []
    for ln in txt.splitlines():
        _s = ln.strip()
        if _s.startswith('#') or _s.startswith('//'):
            continue
        fuera.append(_re.sub(r'\s+//\s.*$', '', ln))
    return chr(10).join(fuera)


# ── 1 · el mismo universo que Abastecimiento ─────────────────────────────────

def test_factibilidad_cuenta_lo_MISMO_que_abastecimiento(app, db_clean):
    """Dos pantallas que miran el mismo calendario no pueden contar universos distintos."""
    plan = _src('api/blueprints/plan.py')
    prog = _src('api/blueprints/programacion.py')
    # los orígenes de abastecimiento, tal como los enumera su motor
    for origen in ('eos_canonico', 'auto_plan', 'sugerido', 'eos_proyeccion', 'manual'):
        assert origen in prog, 'cambió la lista de orígenes de abastecimiento'
        assert origen in plan, 'factibilidad no conoce el origen %s' % origen
    assert "_ORIG_TODO = _ORIG_FIJO + ('eos_canonico', 'auto_plan', 'sugerido'," in plan
    assert "solo_fijo = str(request.args.get('solo_fijo', '0'))" in plan, \
        'factibilidad sigue contando sólo lo Fijo por defecto'


def test_factibilidad_DECLARA_que_universo_conto(app, db_clean):
    """Un veredicto de "es ejecutable" sin decir sobre qué es lo que hacía imposible entender
    la contradicción con la pestaña de al lado (M124)."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    assert c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
                  headers=csrf_headers(), follow_redirects=False).status_code == 302
    d = c.get('/api/plan/factibilidad?dias=30').get_json() or {}
    assert 'origenes_contados' in d and d['origenes_contados'], 'no dice qué contó'
    assert 'universo' in d and d['universo']
    assert 'eos_proyeccion' in d['origenes_contados'], \
        'por defecto tiene que contar lo proyectado, como Abastecimiento'


def test_se_puede_volver_a_solo_lo_FIJO(app, db_clean):
    """Con dientes al revés: el modo estricto no se perdió, sólo dejó de ser el default."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    d = c.get('/api/plan/factibilidad?dias=30&solo_fijo=1').get_json() or {}
    assert d.get('solo_fijo') is True
    assert 'eos_proyeccion' not in (d.get('origenes_contados') or [])


# ── 2 · el semáforo de envases ───────────────────────────────────────────────

def test_la_urgencia_del_envase_se_DERIVA_de_la_fecha(app, db_clean):
    """Un indicador que alguien tiene que acordarse de actualizar termina viejo (M109)."""
    prog = _src('api/blueprints/programacion.py')
    assert "'urgencia': _urg," in prog, 'la urgencia sigue saliendo de la columna guardada'
    assert "'urgencia_manual': (r[13] or '')" in prog, 'se perdió la marca manual'
    assert "'urgencia': (r[13] or _urg)" not in prog, 'volvió el `or` que mataba el cálculo'


def test_una_orden_VENCIDA_no_sale_igual_que_una_al_dia(app, db_clean):
    """El caso concreto: la de hace 5 días se pintaba amarilla igual que la de mañana."""
    from datetime import date, timedelta
    from database import get_db
    from .conftest import TEST_PASSWORD, csrf_headers
    hoy = date.today()
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM marcacion_ordenes WHERE base_codigo LIKE 'ZZURG%'")
        for cod, dias in (('ZZURG-VENC', -5), ('ZZURG-LEJOS', 30)):
            cur.execute(
                "INSERT INTO marcacion_ordenes (base_codigo, serigrafiado_codigo, "
                "producto_nombre, metodo, proveedor, cantidad_enviada, estado, fecha_alistar, "
                "urgencia, creado_por) "
                "VALUES (?,?, 'ZZ', 'Serigrafia', 'ZZ', 100, 'enviado', ?, 'media', 't')",
                (cod, cod + '-S', (hoy + timedelta(days=dias)).isoformat()))
        conn.commit()
    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    items = (c.get('/api/programacion/marcacion-ordenes').get_json() or {}).get('items') or []
    porcod = {i['base']: i for i in items if str(i.get('base', '')).startswith('ZZURG')}
    assert porcod, 'no volvieron las órdenes sembradas'
    assert porcod['ZZURG-VENC']['urgencia'] == 'vencido', \
        'una orden vencida hace 5 días sigue sin marcarse como vencida'
    assert porcod['ZZURG-LEJOS']['urgencia'] == 'ok'
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM marcacion_ordenes WHERE base_codigo LIKE 'ZZURG%'")
        conn.commit()


# ── 3 · estacionalidad ───────────────────────────────────────────────────────

def test_el_pico_solo_es_pico_si_SUPERA_el_umbral(app, db_clean):
    """El mes más alto existe siempre; un PICO no. Pintar 🔥 en todos vuelve el dato ruido."""
    plan = _src('api/blueprints/plan.py')
    assert "_es_pico = bool(_mx is not None and ind_ef[_mx] >= umbral_pico)" in plan
    assert "'pico_max_mes': ((_mx + 1) if _es_pico else None)," in plan
    assert "'mes_mas_alto':" in plan, 'se perdió el dato informativo del mes más alto'
    # y la tarjeta global aplica la misma regla, no su propio máximo
    assert 'Misma regla que el backend aplica por producto' in plan


def test_el_mes_EN_CURSO_no_se_promedia_como_completo(app, db_clean):
    """4 días de agosto contra los 31 de los agostos anteriores no es un mes flojo: es un mes
    incompleto, y tratarlos igual hunde el índice y subestima el crecimiento."""
    plan = _src('api/blueprints/plan.py')
    assert "_ym_curso = (hoy.year, hoy.month)" in plan
    assert "if (y, m) == _ym_curso:" in plan, 'la curva sigue promediando el mes a medias'
    assert "if (y, m) in _last12 and (y, m) != _ym_curso" in plan, \
        'el año contra año sigue incluyendo el mes parcial · sale subestimado siempre'


# ── 4 · no afirmar sin haber calculado ───────────────────────────────────────

def test_no_dice_TODO_CUBIERTO_sin_haber_calculado(app, db_clean):
    """Afirmar que no falta producir sin haberlo mirado es peor que no decir nada."""
    plan = _src('api/blueprints/plan.py')
    assert "'No hay sugerencias para este horizonte · todo cubierto'" not in plan
    assert 'esto NO quiere decir que esté todo cubierto' in plan


def test_los_KPIs_del_plan_IA_no_muestran_cero_sin_correr(app, db_clean):
    """Un cero que nadie calculó se lee como "no hay nada que hacer" y es lo contrario de la
    verdad: es "no se miró"."""
    plan = _src('api/blueprints/plan.py')
    assert 'const _planIA = !!(k && (k.total_producciones != null' in plan
    assert 'if (_planIA) {' in plan


# ── 5 · los dos botones que no llevaban a ningún lado ────────────────────────

def test_el_boton_programar_de_las_alertas_usa_una_ruta_QUE_EXISTE(app, db_clean):
    """Llamaba a una función del padre con el nombre donde espera un índice, y su plan B pegaba
    a `/api/plan/lote-manual`, que no existe. Los dos caminos rotos, en silencio."""
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert '/api/plan/lote-manual' not in plan, 'sigue apuntando a una ruta inexistente'
    assert "abrirGenerarDesdeAlerta" in plan
    i = plan.find('function abrirGenerarDesdeAlerta')
    bloque = plan[i:i + 2500]
    assert '/api/plan/programar-manual' in bloque, 'no usa el endpoint real'
    assert 'skip_validacion_dia' in bloque, 'perdió la confirmación de día no hábil'


def test_el_link_de_mapear_SKUs_apunta_a_algo_que_existe(app, db_clean):
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert '/herramientas#skus-huerfanos' not in plan, 'sigue el link a una ruta que no existe'
    assert 'tab-necesidades' in plan


def test_las_rutas_que_el_calendario_llama_ESTAN_registradas(app, db_clean):
    """El chequeo que más rinde: cada fetch a /api/ tiene que existir en el url_map real."""
    import re
    plan = _src('api/blueprints/plan.py')
    reglas = []
    for r in app.url_map.iter_rules():
        reglas.append(re.sub(r'<[^>]+>', '[^/]+', str(r)))

    def existe(ruta):
        return any(re.fullmatch(rx, ruta) for rx in reglas)

    faltan = []
    for m in re.finditer(r"fetch\(\s*['\"`](/api/[^'\"`?]+)", plan):
        cruda = m.group(1)
        # Una URL que sigue con una variable (`'/api/x/' + id + '/y'`) queda cortada acá: se
        # prueba con un valor de relleno en vez de darla por rota (si no, el guard grita sobre
        # rutas sanas y se vuelve ruido · un trinquete con falsos positivos deja de mirarse).
        base = cruda.rstrip('/')
        cand = [base, base + '/X', base + '/1', base + '/X/presentaciones',
                base + '/1/cantidad', base + '/X/desglose']
        if any(existe(x) for x in cand):
            continue
        if cruda.endswith('/'):
            # La URL sigue con una variable (`'/api/x/' + id + '/y'`) y el fuente la corta acá:
            # no se puede resolver, así que no se acusa. Un guard con falsos positivos deja de
            # mirarse, que es peor que no tenerlo.
            continue
        faltan.append(base)
    assert not faltan, 'el calendario llama rutas que no existen: %s' % sorted(set(faltan))


# ── 6 · lo que quedaba pendiente del calendario (4-ago, segunda tanda) ───────

def test_el_desglose_de_lotes_CUADRA_con_el_total(app, db_clean):
    """Se leía "1.400 lotes · 120 Fijos · 60 Sugeridos" y el resto no aparecía: lo proyectado
    -- que suele ser la mayoría -- caía en un cajón que la pantalla nunca pintaba. Un desglose
    que no suma el total obliga a desconfiar de los tres números."""
    prog = _src('api/blueprints/programacion.py')
    i = prog.find('n_fijas = sum(1 for r in prod_rows')
    assert i > 0
    bloque = prog[i:i + 700]
    assert 'eos_proyeccion' in bloque, 'lo proyectado sigue sin caer en ninguna categoría'
    assert "'calendar'" not in bloque, "sigue contando 'calendar', un origen que se eliminó"
    # y el subtítulo separa PEDIDOS de LOTES en vez de sumarlos
    assert 'pedido(s) B2B pendientes' in prog
    assert 'de otro origen' in prog, 'no muestra el resto cuando lo hay'


def test_el_truncado_del_calendario_se_DECLARA(app, db_clean):
    """Corta en 6.000 filas ordenando por fecha ASC, así que lo que se pierde es EL FUTURO ·
    justo lo que el calendario existe para mostrar. Un total que se cortó y no lo dice es un
    total falso."""
    prog = _src('api/blueprints/programacion.py')
    assert "'truncado': _truncado" in prog and "'tope': 6000" in prog
    assert 'se está recortando' in prog, 'no queda rastro en el log'


def test_los_rotulos_de_ANIO_dicen_lo_que_cuentan(app, db_clean):
    """"Lotes/año" y "programados en el año" contaban TODA la ventana (histórico + 3 años)."""
    plan = _src('api/blueprints/plan.py')
    assert '<th>Lotes/año</th>' not in plan, 'el rótulo sigue diciendo un período que no cuenta'
    assert 'Lotes en el plan' in plan
    assert "' programados en el año'" not in plan
    assert 'en todo el plan cargado' in plan


def test_el_escaneo_de_huerfanos_tiene_CACHE(app, db_clean):
    """Parsea 60 días de órdenes de Shopify y el banner lo pide en CADA apertura de la pestaña,
    por cada worker · es el patrón que satura los 3 workers y devuelve HTML 504 (M43)."""
    plan = _src('api/blueprints/plan.py')
    assert '_HUERFANOS_CACHE' in plan
    assert '_HUERFANOS_CACHE[_ck_h] = (_t_h.time(), _payload_h)' in plan, 'no guarda en el cache'
    assert "'cacheado': True" in plan or 'cacheado=True' in plan, 'no declara que viene del cache'


def test_estacionalidad_NO_abre_en_pestana_nueva(app, db_clean):
    """Sebastián pidió explícitamente no abrir ventanas nuevas · y sin `data-prog-sub` además
    perdía el resaltado de la sub-barra."""
    dash = _sin_comentarios(_src('api/templates_py/dashboard_html.py'))
    assert "window.open('/planta/estacionalidad','_blank')" not in dash
    assert "switchProgTab('estacionalidad')" in dash
    assert 'id="ptab-estacionalidad"' in dash, 'sin panel, el conmutador deja la pantalla en blanco'
    assert "'estacionalidad': 'ptab-estacionalidad'" in dash, 'falta en el mapa del conmutador'


def test_las_acciones_de_MANTENIMIENTO_tienen_boton(app, db_clean):
    """14 funciones construidas y sin ningún call-site · trece endpoints de mantenimiento del
    plan, inalcanzables desde la pantalla. Es M112 al revés: allá quedaron botones sin destino,
    acá quedó el destino sin botones."""
    plan = _src('api/blueprints/plan.py')
    for fn in ('dedupMismoDia', 'repartirSobrecargados', 'recuperarCancelados',
               'backfillFabricacion', 'revertirHoy', 'sellarPlan', 'dejarSoloReal'):
        assert 'function ' + fn + '(' in plan, 'desapareció %s' % fn
        assert 'onclick="' + fn + '()"' in plan, '%s sigue sin botón' % fn
    # y cada botón trae el id que su función busca, o el botón queda mudo
    for _id in ('btn-dedup', 'btn-repartir', 'btn-recuperar', 'btn-revertir-hoy', 'btn-sellar'):
        assert 'id="' + _id + '"' in plan, 'falta el id %s' % _id


def test_el_AUTOPLAN_se_retiro_entero(app, db_clean):
    """Sebastián: *"autoplan ya no lo usamos"*. Se poda el par completo -- disparador y destino
    -- para no dejar botones vivos apuntando a lo que se borró (M112)."""
    plan = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert 'id="filtro-solo-ia"' not in plan, \
        'sigue el filtro que dejaba el calendario en blanco sin mensaje'
    assert 'onclick="autoplanIA()"' not in plan
    assert 'onclick="aplicarIAanual()"' not in plan
    assert 'id="sugerencias-lista"' not in plan, 'sigue la lista del autoplan'
    assert 'id="btn-aplicar"' not in plan
