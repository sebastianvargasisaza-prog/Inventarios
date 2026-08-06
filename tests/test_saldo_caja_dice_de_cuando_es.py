# -*- coding: utf-8 -*-
"""El "Saldo caja" de Tesorería dice de cuándo es, y la caja menor sale del helper canónico.

`gerencia_inputs.saldo_caja` es el efectivo de la EMPRESA y lo **teclea gerencia una vez al
mes**. Se mostraba pelado -- "Saldo caja / acumulado" -- al lado de tres números calculados en
vivo (ingresos del mes, egresos del mes, neto), y tomando el último período que existiera. O sea
que un número de hace seis semanas se leía exactamente igual de fresco que el ingreso de hoy, y
un indicador que alguien tiene que acordarse de actualizar termina viejo sin que nadie lo note
(M109/M124).

⚠ Lo que NO se hizo, y es lo importante: **cambiar la fuente al helper de caja menor**. Son dos
cosas distintas -- `gerencia_inputs.saldo_caja` es la caja de la empresa y `caja_saldo()` es la
gaveta chica. Sustituir uno por otro hundiría el runway y el capital de trabajo, que leen ese
mismo número: un arreglo que se siente como arreglo y rompe dos indicadores.

Lo que sí: el dato dice su período y se marca cuando está vencido, y la caja menor se agrega
como su propio número -- ése sí verificable, porque es el que se cuenta en el arqueo y contra el
que se autorizan los pagos (M1/M148).
"""
import io
import os
import re

from .conftest import TEST_PASSWORD, csrf_headers

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _kpis(app, periodo_del_dato):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM gerencia_inputs WHERE periodo LIKE '20%'")
        conn.execute("INSERT INTO gerencia_inputs (periodo, saldo_caja) VALUES (?,?)",
                     (periodo_del_dato, 7500000))
        conn.commit()
    r = _admin(app).get('/api/financiero/kpis')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_dice_DE_QUE_PERIODO_es_el_saldo(app, db_clean):
    d = _kpis(app, '2020-01')
    assert d['saldo_caja_periodo'] == '2020-01', d.get('saldo_caja_periodo')
    assert d['saldo_caja_vigente'] is False, (
        'un dato de 2020 se está presentando como vigente')


def test_lo_marca_VIGENTE_cuando_es_del_mes_en_curso(app, db_clean):
    """El borde en la otra dirección: si siempre dijera "desactualizado", la alerta se vuelve
    ruido y deja de mirarse (M129)."""
    from tz_colombia import hoy_colombia
    d = _kpis(app, hoy_colombia().strftime('%Y-%m'))
    assert d['saldo_caja_vigente'] is True, 'marcó como viejo un dato cargado este mes'


def test_la_caja_menor_sale_del_helper_CANONICO(app, db_clean):
    """Tiene que ser el MISMO número contra el que se autorizan los pagos y se arquea · si el
    KPI armara su propio SUM, volvería a divergir en silencio (M1/M148)."""
    from database import get_db
    from blueprints.animus import caja_saldo
    d = _kpis(app, '2026-08')
    assert d.get('caja_menor_ok') is True, d
    with app.app_context():
        canon = float(caja_saldo(get_db()) or 0)
    assert float(d['caja_menor']) == canon, 'el KPI calcula su propia caja menor'

    # ⚠ Comparar los dos números NO alcanza: con la caja vacía o por casualidad coinciden, y
    # el test pasa con un SUM propio puesto a propósito (lo probé y pasó verde). Lo que hay que
    # medir es que DELEGUE -- dos sumas que hoy dan igual divergen el día que cambie una regla,
    # que es exactamente el drift que M1 previene.
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'financiero.py'), encoding='utf-8').read()
    i = s.find('caja_menor =')
    assert i > 0, 'desapareció el cálculo de la caja menor'
    bloque = re.sub(r'^\s*#[^\n]*$', '', s[max(0, i - 600):i + 200], flags=re.M)
    assert 'caja_saldo' in bloque, 'el KPI dejó de delegar en el helper canónico'
    assert 'animus_caja_menor' not in bloque, (
        'el KPI volvió a armar su propio SUM sobre la tabla de caja · va a divergir del número '
        'contra el que se autorizan los pagos')


def test_NO_se_reemplazo_la_fuente_del_runway(app):
    """Guard de la decisión: `working_capital` sigue leyendo la caja de la EMPRESA. Cambiarla
    por la gaveta chica dejaría el runway calculado sobre unos pocos millones."""
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'financiero.py'), encoding='utf-8').read()
    i = s.find('def working_capital')
    if i < 0:
        i = s.find('working_capital')
    ventana = s[i:i + 4000]
    assert 'gerencia_inputs' in ventana, (
        'el capital de trabajo dejó de usar la caja de la empresa · si ahora lee la caja menor, '
        'el runway quedó calculado sobre la gaveta')


def test_la_pantalla_PINTA_las_dos_cosas_distintas(app):
    """Dos números con el mismo rótulo se leen como uno solo: cada uno con su tarjeta y su
    explicación, o vuelve la confusión que esto viene a arreglar (M161)."""
    from templates_py.tesoreria_html import HTML
    assert 'id="kpi-saldo-sub"' in HTML, 'el saldo no dice de cuándo es'
    assert 'id="kpi-caja-menor"' in HTML, 'la caja menor no se ve'
    # y la vista lee llaves que el endpoint MANDA (el contrato roto de siempre)
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'financiero.py'), encoding='utf-8').read()
    for llave in ('saldo_caja_periodo', 'saldo_caja_vigente', 'caja_menor', 'caja_menor_ok'):
        assert llave in HTML, 'la vista no usa %s' % llave
        assert ("'%s'" % llave) in s, 'la vista lee `%s` y el endpoint no la manda' % llave


def test_el_fallback_de_la_caja_menor_no_TUMBA_el_endpoint(app):
    """Este módulo no tiene un `log` global: un `log.warning` dentro del except habría lanzado
    NameError y tirado abajo la página entera -- el fallback que existe para no caerse."""
    s = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'financiero.py'), encoding='utf-8').read()
    i = s.find('no pude leer la caja menor')
    assert i > 0, 'desapareció el aviso'
    ventana = s[max(0, i - 400):i + 120]
    assert 'getLogger' in ventana, 'usa un logger que no existe en este módulo'
    assert not re.search(r'^\s*log\.warning', ventana, re.M), 'volvió el `log` global inexistente'
