"""La verificación de MP tiene que MOSTRAR los lotes, no sólo el total (30-jul).

Sebastián, mirando en vivo una fabricación: *"vi que goma xantana tenía dos lotes, pero cuando se
iba a fabricar y se hacía verificación de materias primas sólo jalaba uno; ese uno tenía poca
cantidad y lo mostraba como sin stock (...) es la parte de que muestre los lotes que deben usar,
para que no pase esto en todo, porque estaría diciendo las cosas mal"*.

El motor estaba BIEN: suma todos los lotes usables del código. Lo que faltaba era decirlo. La
pantalla mostraba `necesita / hay / falta` y nada más, así que un lote en CUARENTENA esperando la
liberación de Calidad -- o vencido -- se veía como si no existiera: el operario tiene dos lotes
enfrente y el sistema le dice "no hay". Eso es lo que él llama "decir las cosas mal".

Lo que este archivo fija:
  · el faltante trae **los lotes**: los que sí se pueden usar y los BLOQUEADOS con su MOTIVO;
  · los dos caminos (fabricación directa y producción programada) dicen lo MISMO (M5), porque
    los dos salen del mismo helper `_lotes_de_material`;
  · se puede diagnosticar por NOMBRE: si el material quedó partido en dos códigos, salen los dos
    con sus lotes (producción consume UN código por ítem de fórmula, así que el otro NO se suma).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ GOMA PROD'
COD_A = 'MP-ZZGOMA-A'
COD_B = 'MP-ZZGOMA-B'
NOMBRE = 'Goma xantana ZZTEST'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _limpiar():
    for cod in (COD_A, COD_B):
        _exec("DELETE FROM movimientos WHERE material_id=?", (cod,))
        _exec("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
    _exec("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _exec("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))


def _sembrar_dos_lotes():
    """Exactamente el caso de goma xantana: un lote chico usable + uno grande en CUARENTENA."""
    _limpiar()
    _exec("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
          (COD_A, NOMBRE, 'XANTHAN GUM'))
    _exec("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES (?,1000,1)",
          (PROD,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
          "VALUES (?,?,?,10)", (PROD, COD_A, NOMBRE))
    # 30 g usables (poco) + 5.000 g esperando a Calidad
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
          "fecha_vencimiento,estado_lote) VALUES (?,?,30,'Entrada','2026-07-01','LOTE-CHICO',"
          "'2028-01-31','VIGENTE')", (COD_A, NOMBRE))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
          "fecha_vencimiento,estado_lote) VALUES (?,?,5000,'Entrada','2026-07-02','LOTE-GRANDE',"
          "'2028-06-30','CUARENTENA')", (COD_A, NOMBRE))


def _faltante(app, kg=1):
    r = _login(app).post('/api/produccion', headers=csrf_headers(),
                         json={'producto': PROD, 'cantidad_kg': kg,
                               'operador': 'sebastian', 'presentacion': 'x'})
    assert r.status_code == 422, 'debía faltar stock · %s %s' % (r.status_code, r.data[:300])
    j = r.get_json() or {}
    fs = j.get('faltantes') or []
    assert fs, 'no devolvió faltantes: %r' % list(j)[:8]
    return fs[0]


# ══ el caso de Sebastián ════════════════════════════════════════════════════════

def test_dice_QUE_lote_puede_usar_y_cual_no(app, db_clean):
    """Lo que él pidió: que muestre los lotes. Y sobre todo, POR QUÉ no puede usar el otro."""
    _sembrar_dos_lotes()
    f = _faltante(app)
    usables = f.get('lotes_usables') or []
    bloq = f.get('lotes_retenidos') or []
    assert len(usables) == 1 and usables[0]['lote'] == 'LOTE-CHICO', (
        'no dijo cuál lote SÍ puede usar: %r' % usables)
    assert abs(float(usables[0]['g']) - 30) < 0.01, usables
    assert len(bloq) == 1 and bloq[0]['lote'] == 'LOTE-GRANDE', (
        'el lote que el operario VE en bodega no aparece en el aviso: %r' % bloq)
    assert 'CUARENTENA' in str(bloq[0].get('motivo', '')).upper(), (
        'no explica por qué no lo puede tocar: %r' % bloq[0])


def test_un_lote_VENCIDO_por_fecha_tambien_se_declara(app, db_clean):
    """El cron de vencidos corre una vez al día: entre que vence y que corre, el lote sigue
    marcado VIGENTE. El FEFO ya no lo consume (M25) -- el aviso tiene que decir lo mismo."""
    _limpiar()
    _exec("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (COD_A, NOMBRE))
    _exec("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES (?,1000,1)",
          (PROD,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
          "VALUES (?,?,?,10)", (PROD, COD_A, NOMBRE))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
          "fecha_vencimiento,estado_lote) VALUES (?,?,5000,'Entrada','2024-01-01','LOTE-VIEJO',"
          "'2024-06-30','VIGENTE')", (COD_A, NOMBRE))
    f = _faltante(app)
    bloq = f.get('lotes_retenidos') or []
    assert any('VENCID' in str(b.get('motivo', '')).upper() for b in bloq), (
        'un lote vencido por fecha debe salir declarado, no desaparecer: %r' % bloq)


def test_el_camino_PROGRAMADO_dice_lo_mismo(app, db_clean):
    """Si la fabricación directa y el arranque desde el calendario avisaran distinto, cada
    pantalla contaría una historia (M5). Los dos salen del MISMO helper."""
    _sembrar_dos_lotes()
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _validar_stock_para_produccion
        faltantes = _validar_stock_para_produccion(
            get_db().cursor(),
            [{'codigo_mp': COD_A, 'nombre': NOMBRE, 'cantidad_g': 100.0, 'controla_stock': 1}])
    assert faltantes, 'debía faltar'
    f = faltantes[0]
    assert [x['lote'] for x in f.get('lotes_usables') or []] == ['LOTE-CHICO'], f
    assert [x['lote'] for x in f.get('lotes_retenidos') or []] == ['LOTE-GRANDE'], f


def test_no_avisa_lotes_cuando_alcanza(app, db_clean):
    """Dientes del otro lado: si alcanza, no hay faltante ni ruido."""
    _limpiar()
    _exec("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (COD_A, NOMBRE))
    _exec("INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES (?,1000,1)",
          (PROD,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) "
          "VALUES (?,?,?,10)", (PROD, COD_A, NOMBRE))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
          "fecha_vencimiento,estado_lote) VALUES (?,?,9000,'Entrada','2026-07-01','LOTE-OK',"
          "'2028-01-31','VIGENTE')", (COD_A, NOMBRE))
    r = _login(app).post('/api/produccion', headers=csrf_headers(),
                         json={'producto': PROD, 'cantidad_kg': 1,
                               'operador': 'sebastian', 'presentacion': 'x'})
    assert r.status_code in (200, 201), r.data[:300]


# ══ diagnosticar por NOMBRE · ¿el material está partido en dos códigos? ═════════

def test_buscar_por_nombre_muestra_TODOS_los_codigos_con_stock(app, db_clean):
    """Para diagnosticar hay que saber el código, y justo lo que se investiga es si el material
    quedó partido en dos. Producción consume UN código por ítem de fórmula: el stock del otro
    NO se suma, y eso tiene que quedar dicho."""
    _sembrar_dos_lotes()
    _exec("INSERT INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES (?,?,?,1)",
          (COD_B, NOMBRE + ' (otro proveedor)', 'XANTHAN GUM'))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,"
          "fecha_vencimiento,estado_lote) VALUES (?,?,8000,'Entrada','2026-07-05','LOTE-OTRO-COD',"
          "'2028-09-30','VIGENTE')", (COD_B, NOMBRE))
    r = _login(app).get('/api/admin/mp-diag?q=' + 'Goma xantana ZZTEST'.replace(' ', '%20'))
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    cods = {c['codigo'] for c in j.get('codigos') or []}
    assert COD_A in cods and COD_B in cods, 'no listó los dos códigos: %r' % cods
    assert j.get('codigos_con_stock', 0) >= 2, j
    assert j.get('aviso'), 'con dos códigos con stock tiene que AVISAR que no se suman'
    b = [c for c in j['codigos'] if c['codigo'] == COD_A][0]
    assert [l['lote'] for l in b['lotes_usables']] == ['LOTE-CHICO'], b
    assert [l['lote'] for l in b['lotes_retenidos']] == ['LOTE-GRANDE'], b


def test_la_pagina_de_diagnostico_trae_el_buscador(app, db_clean):
    """El endpoint sin pantalla no lo usa nadie (M112: el botón y su destino van juntos)."""
    r = _login(app).get('/admin/mp-diag')
    assert r.status_code == 200, r.status_code
    body = r.data.decode('utf-8', 'replace')
    assert 'function buscar(' in body and 'id="q"' in body, (
        'la página quedó sin el buscador por nombre')


def test_el_JS_de_la_pagina_PARSEA(app, db_clean):
    """Que la función esté ESCRITA no significa que el navegador la pueda ejecutar.

    Pasó el 30-jul: metí el buscador con `\\'` dentro de un template de Python que NO es raw,
    así que los backslashes se perdieron y quedó una comilla suelta -> `Uncaught ReferenceError:
    buscar is not defined` y el botón sin hacer nada. El test anterior pasaba en verde porque
    sólo miraba que el TEXTO 'function buscar(' estuviera en el HTML (M65/M125).

    La única verificación que caza esto es node --check del JS RENDERIZADO. Si no hay node en la
    máquina, el test se salta declarándolo (nunca da un verde silencioso).
    """
    import os
    import re
    import shutil
    import subprocess
    import tempfile
    import pytest
    if not shutil.which('node'):
        pytest.skip('node no está instalado · sin él no se puede validar el JS renderizado')
    body = _login(app).get('/admin/mp-diag').data.decode('utf-8', 'replace')
    bloques = [b for b in re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', body, re.S)
               if b.strip()]
    assert bloques, 'la página no tiene JS inline: ¿se rompió el render?'
    for i, b in enumerate(bloques):
        ruta = os.path.join(tempfile.gettempdir(), '_eos_chk_mpdiag_%d.js' % i)
        with open(ruta, 'w', encoding='utf-8') as fh:
            fh.write(b)
        try:
            r = subprocess.run(['node', '--check', ruta], capture_output=True, text=True)
        finally:
            try:
                os.remove(ruta)
            except OSError:
                pass
        assert r.returncode == 0, (
            'el bloque %d de /admin/mp-diag NO parsea · la página se sirve igual pero los '
            'botones no hacen nada:\n%s' % (i, r.stderr[:600]))
