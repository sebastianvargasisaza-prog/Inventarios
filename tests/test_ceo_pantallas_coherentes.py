# -*- coding: utf-8 -*-
"""Las tres pantallas del CEO dicen lo MISMO (5-ago).

`/gerencia`, `/hoy` y `/mi-bandeja` mostraban el mismo hecho con números distintos, y el usuario
no tiene forma de saber cuál creer — que es peor que no mostrarlo, porque termina desconfiando
de los tres:

- **Los kg producidos se dividían por 1000 en `/hoy`.** `producciones.cantidad` YA está en kg
  (así lo escriben los dos writers), así que esa tarjeta mostraba **0 kg** mientras `/gerencia`
  mostraba el número correcto.
- **"MP bajo mínimo" se contaba de tres formas**: dos CASE que tratan `Ajuste` como salida y no
  excluyen cuarentena/vencido/rechazado — y la versión correcta ya estaba escrita en el MISMO
  archivo, 800 líneas más arriba.
- **"Lotes por vencer" contaba MOVIMIENTOS**: un lote recibido en tres partidas contaba tres veces.
- **"Registros INVIMA: 0"** con un comentario afirmando que la tabla no existe. Existe.

Y dos cosas que corrían para nadie: seis consultas de AR/AP cuyos contenedores no están en el
HTML, y un N+1 que hacía una consulta **por cliente** para producir un solo entero.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(txt):
    fuera = []
    for ln in txt.splitlines():
        _s = ln.strip()
        if _s.startswith('#') or _s.startswith('//') or _s.startswith('<!--'):
            continue
        ln = re.sub(r'\s+//\s.*$', '', ln)
        ln = re.sub(r'\s+#\s.*$', '', ln)
        fuera.append(ln)
    return chr(10).join(fuera)


def _html(modulo, atributo):
    import sys
    api = os.path.join(RAIZ, 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    return getattr(__import__('templates_py.' + modulo, fromlist=[atributo]), atributo)


# ── 1 · los kg son kg en las dos pantallas ───────────────────────────────────

def test_los_KG_no_se_dividen_por_mil(app, admin_client, db_clean):
    """`producciones.cantidad` ya está en kilos · dividir otra vez mostraba 0 kg en /hoy
    mientras /gerencia mostraba el valor real."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producciones WHERE producto='ZZ KG COHER'")
        c.execute("INSERT INTO producciones (producto, cantidad, fecha, estado) "
                  "VALUES ('ZZ KG COHER', 40, date('now'), 'Completado')")
        conn.commit()

    ger = admin_client.get('/api/gerencia/kpis').get_json()['espagiria']['kg_mes']
    hoy = admin_client.get('/api/centro/operaciones').get_json().get('produccion', {}).get('kg_mes')

    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM producciones WHERE producto='ZZ KG COHER'")
        conn.commit()

    assert float(ger) >= 40, 'los kg del mes no llegaron a /gerencia: %s' % ger
    assert hoy is not None, '/hoy no devuelve los kg del mes'
    assert abs(float(ger) - float(hoy)) < 0.01, \
        'las dos pantallas del CEO dan kg distintos: /gerencia=%s vs /hoy=%s' % (ger, hoy)


def test_los_KG_DE_LA_SEMANA_tampoco_se_dividen(app, admin_client, db_clean):
    """El reporte semanal tenía su propia división por 1000 — la misma unidad, el mismo error, en
    otro sitio. Al cerrar un patrón hay que grepearlo entero (M45)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producciones WHERE producto='ZZ KG SEM'")
        c.execute("INSERT INTO producciones (producto, cantidad, fecha, estado) "
                  "VALUES ('ZZ KG SEM', 25, date('now'), 'Completado')")
        conn.commit()
    r = admin_client.get('/api/reporte/semanal-ceo')
    kg = None
    if r.status_code == 200:
        kg = ((r.get_json() or {}).get('producciones_semana') or {}).get('kg')
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM producciones WHERE producto='ZZ KG SEM'")
        conn.commit()
    assert kg is not None, 'el reporte semanal no devuelve los kg (status %s)' % r.status_code
    assert float(kg) >= 25, \
        'los kg de la semana salen divididos: %s (sembré 25 kg)' % kg


def test_el_front_de_HOY_no_vuelve_a_dividir(app, db_clean):
    h = _sin_comentarios(_html('centro_operaciones_html', 'HTML'))
    assert '(p.kg_mes||0)/1000' not in h, 'el front de /hoy volvió a dividir los kg por mil'


# ── 2 · una sola definición de "cuánta MP hay" ───────────────────────────────

def test_el_hub_cuenta_la_MP_con_el_canonico(app, db_clean):
    """Dos CASE que tratan `Ajuste` como salida y no excluyen cuarentena · la versión correcta
    ya estaba en el MISMO archivo, 800 líneas más arriba."""
    hub = _sin_comentarios(_src('api/blueprints/hub.py'))
    assert "WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad" not in hub, \
        'volvió un CASE de stock que no es el canónico'
    # el fragmento compartido, para que no vuelvan a separarse
    assert '_CASE_STOCK' in hub and '_FROM_STOCK' in hub
    assert hub.count("'CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO'") >= 2, \
        'alguna de las cuentas de MP dejó de excluir los 6 estados'


def test_los_LOTES_por_vencer_se_cuentan_por_LOTE(app, db_clean):
    """Un lote recibido en tres partidas contaba tres veces · y ese número alimenta una alerta."""
    hub = _sin_comentarios(_src('api/blueprints/hub.py'))
    i = hub.find('venc7 = c.execute')
    assert i > 0
    bloque = hub[i:i + 700]
    assert 'GROUP BY material_id, lote' in bloque, 'sigue contando movimientos, no lotes'
    ger = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    assert 'GROUP BY material_id, lote' in ger, '/gerencia sigue contando movimientos'


def test_las_dos_pantallas_cuentan_la_MISMA_cantidad_de_MP_critica(app, admin_client, db_clean):
    """El que vale: ejecutar los dos endpoints y comparar. Las definiciones pueden verse iguales
    en el código y dar números distintos por un detalle del WHERE."""
    a = admin_client.get('/api/centro/decisiones').get_json()
    b = admin_client.get('/api/centro/operaciones').get_json()
    _cero_a = next((d.get('n') for d in (a.get('decisiones') or [])
                    if 'cero' in (d.get('titulo') or '').lower()), 0) or 0
    _cero_b = (b.get('inventario') or {}).get('mps_cero', 0) or 0
    assert int(_cero_a) == int(_cero_b), \
        'las dos pantallas cuentan distinto las MP en cero: %s vs %s' % (_cero_a, _cero_b)


# ── 3 · los registros INVIMA existen ─────────────────────────────────────────

def test_los_registros_INVIMA_se_leen_de_su_TABLA(app, admin_client, db_clean):
    """El comentario afirmaba que la tabla no existe · la crea `tecnica._init_tecnica()` al
    importar el blueprint, y `tecnica.py` la consulta sin problema."""
    hub = _sin_comentarios(_src('api/blueprints/hub.py'))
    assert 'FROM registros_invima' in hub, 'sigue sin leer la tabla real'
    assert "'invima_vigentes': None," not in hub, 'sigue fijando None a mano'
    d = admin_client.get('/api/centro/operaciones').get_json()
    tec = d.get('tecnica') or {}
    assert 'invima_vigentes' in tec
    # y el front distingue un cero de un "no pude mirar"
    h = _sin_comentarios(_html('centro_operaciones_html', 'HTML'))
    assert "'sin dato'" in h, 'la pantalla vuelve a pintar 0 cuando no hay dato'


# ── 4 · lo que corría para nadie ─────────────────────────────────────────────

def test_el_AR_AP_inventado_se_retiro_ENTERO(app, db_clean):
    """Seis consultas por carga, cada 5 minutos, cuyos contenedores no existen en el HTML. Y
    encima eran conceptos inventados: "por cobrar" era TODO pedido no cancelado. Se poda el PAR
    completo — cálculo y pintado — porque dejar una punta viva es lo que produce estos
    fantasmas (M112)."""
    ger = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    for muerto in ('ar_total', 'ap_total', "'ar': ar", "'ap': ap"):
        assert muerto not in ger, 'quedó viva una punta del AR/AP retirado: %s' % muerto
    h = _sin_comentarios(_html('gerencia_html', 'GERENCIA_HTML'))
    for muerto in ('d.ar||{}', 'd.ap||{}', "getElementById('gx-ar')", "getElementById('gx-ap')"):
        assert muerto not in h, 'el front sigue pintando el AR/AP retirado: %s' % muerto


def test_los_INGRESOS_por_canal_ahora_SE_PINTAN(app, db_clean):
    """Tres consultas que ya corrían y cuyo contenedor no existía en el HTML."""
    h = _html('gerencia_html', 'GERENCIA_HTML')
    assert 'id="gx-ingresos"' in h, 'el panel de ingresos por canal sigue sin existir'
    assert "getElementById('gx-ingresos')" in h, 'nadie lo llena'


def test_TODO_lo_que_el_front_pinta_TIENE_su_contenedor(app, db_clean):
    """El guard general: un `getElementById('gx-…')` sin su `id` en el HTML es una consulta que
    corre para nadie, cada 5 minutos."""
    h = _html('gerencia_html', 'GERENCIA_HTML')
    ids = set(re.findall(r'id="(gx-[\w-]+)"', h))
    usados = set(re.findall(r"getElementById\('(gx-[\w-]+)'\)", h))
    huerfanos = sorted(usados - ids)
    assert not huerfanos, 'el front pinta en contenedores que no existen: %s' % huerfanos


def test_aliados_feed_YA_NO_consulta_por_cliente(app, db_clean):
    """Era un N+1 puro: una consulta POR CLIENTE para producir UN entero, en la ruta crítica de
    carga y con refresco cada 5 minutos."""
    ger = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    assert 'SELECT fecha FROM pedidos WHERE cliente_id=?' not in ger, 'volvió el N+1'
    assert '_fechas_por_cli' in ger, 'no se agrupó en una sola consulta'


def test_aliados_feed_RESPONDE(app, admin_client, db_clean):
    r = admin_client.get('/api/gerencia/aliados-feed')
    assert r.status_code == 200, r.data[:300]
    assert 'alertas' in (r.get_json() or {}) or 'canal' in (r.get_json() or {})


# ── 5 · la bandeja dejó de ser huérfana ──────────────────────────────────────

def test_MI_BANDEJA_ya_se_puede_ALCANZAR(app, db_clean):
    """230 líneas de pendientes cross-módulo a las que sólo se llegaba tecleando la URL. Una
    feature a la que nadie puede llegar es una feature que no existe (M121)."""
    h = _html('gerencia_html', 'GERENCIA_HTML')
    assert 'href="/mi-bandeja"' in h, 'la bandeja del CEO sigue sin un solo enlace'
    assert 'href="/hoy"' in h, 'el Centro de Mando no está enlazado desde /gerencia'
