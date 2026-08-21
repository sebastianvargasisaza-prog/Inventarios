# -*- coding: utf-8 -*-
"""El rótulo de ingreso de envase/empaque ES el formato COC-PRO-002-F06 · 21-ago-2026.

Sebastián mandó el formato oficial (versión 02, vigencia 21-Jul-2026 a 20-Jul-2029) y pidió que
el rótulo *"esté así, bien configurado, que funcione perfecto"*. Medido campo por campo contra
el HTML que EOS servía, lo que estaba mal:

  · el rótulo citaba **COC-PRO-002-F04**, que es OTRO formato -- un registro regulado diciendo
    ser un formato que no es --, y sin versión, página ni vigencia, que es justamente la
    evidencia de que se llenó en la versión vigente (M251);
  · faltaba **FECHA DE ANÁLISIS**;
  · el tipo de insumo ofrecía TRES casillas (agregaba "Materia Prima") y el oficial tiene DOS;
  · el campo decía "Nombre comercial" y el oficial dice **NOMBRE DEL INSUMO**;
  · el **PROVEEDOR salía en blanco** aunque el maestro lo tuviera: `COALESCE(mv.proveedor,
    mm.proveedor,'')` no cae al maestro porque la columna es `TEXT DEFAULT ''` y nunca guarda
    NULL, así que el fallback jamás corría (mismo patrón que el FEFO de hoy · M263);
  · y medido con las reglas del `@media print` aplicadas, la hoja daba **131 mm de alto sobre
    una etiqueta de 100** -- o sea que cada rótulo se partía en dos etiquetas. Con el encabezado
    de tres zonas compactado quedó en **96,8 mm y cero desbordes** (M123: se mide, no se mira).
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_COD = 'QA-F06-ENV'
_LOTE = 'LOTE-F06-1'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def _limpiar():
    """Limpieza ANTES de sembrar, con códigos FIJOS (M103)."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        ids = [r[0] for r in conn.execute(
            "SELECT id FROM movimientos_mee WHERE mee_codigo=?", (_COD,)).fetchall()]
        for i in ids:
            conn.execute("DELETE FROM mee_cajas_disposicion WHERE mov_id=?", (i,))
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (_COD,))
        conn.execute("DELETE FROM maestro_mee WHERE codigo=?", (_COD,))
        conn.commit()
    finally:
        conn.close()


def _sembrar(con_analisis=True, proveedor_en_mov=''):
    """Una recepción de envase. El proveedor va en el MAESTRO y (opcionalmente) en el movimiento:
    así se ve si el rótulo cae al maestro cuando la fila viene vacía."""
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
         "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
         (_COD, 'FRASCO VIDRIO 30ML', 'Envase', 'VIDRIOS SA'))
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(
            "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,responsable,"
            "fecha,observaciones,estado,proveedor,anulado) VALUES (?,'Entrada',500,'und',?,"
            "'catalina','2026-08-20','sin novedad','CUARENTENA',?,0)",
            (_COD, _LOTE, proveedor_en_mov))
        mov_id = cur.lastrowid
        if con_analisis:
            conn.execute("INSERT INTO mee_cajas_disposicion (mov_id,caja,estado,cantidad,"
                         "dispuesto_por,dispuesto_at_utc) VALUES (?,1,'APROBADO',500,'laura',?)",
                         (mov_id, '2026-08-21T14:05:00'))
        conn.commit()
        return mov_id
    finally:
        conn.close()


def _rotulo(app, mov_id=None):
    c = _login(app)
    url = ('/rotulos-recepcion-mee?mov=%d' % mov_id if mov_id
           else '/rotulo-recepcion-mee/%s/500?lote=%s' % (_COD, _LOTE))
    r = c.get(url)
    assert r.status_code == 200, r.data[:200]
    return r.get_data(as_text=True)


# ── el encabezado: la evidencia de qué formato y qué versión se está usando ──

def test_el_rotulo_cita_el_formato_COC_PRO_002_F06_con_su_control(app, db_clean):
    """Un formato regulado se identifica por su encabezado: código, versión, página y vigencia.
    Antes decía COC-PRO-002-F04 -- el código de OTRO formato -- y sin nada de lo demás."""
    mov = _sembrar()
    try:
        for html in (_rotulo(app), _rotulo(app, mov)):
            assert 'COC-PRO-002-F06' in html, "no cita el formato oficial"
            assert 'COC-PRO-002-F04' not in html, "sigue citando el formato equivocado"
            assert 'FORMATO' in html, "falta la etiqueta FORMATO del encabezado"
            assert 'IDENTIFICACI' in html and 'MATERIAL DE ENVASE' in html.upper(), \
                "falta el título del formato"
            assert '02' in html and 'Versi' in html, "falta la versión"
            assert '1 de 1' in html, "falta la página"
            assert '21-Jul-2026' in html and '20-Jul-2029' in html, "falta la vigencia"
    finally:
        _limpiar()


def test_el_control_del_formato_sale_de_UNA_constante(app, db_clean):
    """Dos rótulos con su propio bloque de control divergen, y el día que Aseguramiento libere
    la versión 03 uno seguiría diciendo 02 -- los dos con cara de oficiales (M251)."""
    from api.blueprints.inventario import F06_CONTROL
    assert F06_CONTROL['codigo'] == 'COC-PRO-002-F06'
    assert F06_CONTROL['version'] == '02'
    import io as _io
    src = _io.open('api/blueprints/inventario.py', encoding='utf-8').read()
    src = re.sub(r'^\s*#.*$', '', src, flags=re.M)
    assert src.count("'COC-PRO-002-F06'") == 1, \
        "el código del formato está escrito más de una vez: dos copias divergen"


# ── los campos del formato oficial, uno por uno ──────────────────────────────

def test_estan_todos_los_campos_del_formato(app, db_clean):
    mov = _sembrar()
    try:
        html = _rotulo(app)
        for etiqueta in ('Nombre del insumo', 'Tipo de insumo', 'Codigo interno', 'Lote',
                         'Cantidad', 'Proveedor', 'Fecha de recepci', 'Fecha de an',
                         'Observaciones', 'Estado', 'Realizado por', 'Aprobado por'):
            assert etiqueta in html, "falta el campo del formato: %s" % etiqueta
    finally:
        _limpiar()


def test_el_tipo_de_insumo_ofrece_las_DOS_casillas_del_formato(app, db_clean):
    """El oficial tiene MATERIAL DE EMPAQUE y MATERIAL DE ENVASE. La materia prima tiene su
    propio formato: ofrecer su casilla acá invita a marcar la equivocada."""
    _sembrar()
    try:
        html = _rotulo(app)
        assert 'MATERIAL DE ENVASE' in html and 'MATERIAL DE EMPAQUE' in html
        assert 'Materia Prima' not in html, \
            "ofrece una casilla que el formato oficial no tiene"
        # y viene MARCADA la que corresponde al insumo (categoría Envase)
        cuerpo = html[html.find('Tipo de insumo'):]
        cuerpo = cuerpo[:cuerpo.find('</tr>')]
        marcada = cuerpo.find('&#9746;')
        assert marcada != -1, "ninguna casilla viene marcada"
        assert cuerpo.find('MATERIAL DE ENVASE') > marcada, \
            "marcó la casilla equivocada para un envase"
    finally:
        _limpiar()


def test_la_fecha_de_analisis_sale_del_hecho_registrado(app, db_clean):
    """Cuándo Calidad dispuso la caja. Si nadie la revisó, la celda va VACÍA para llenarla a
    mano: poner la fecha de impresión sería fechar un análisis que no ocurrió (M19)."""
    mov = _sembrar(con_analisis=True)
    try:
        html = _rotulo(app, mov)
        assert '21 AGOSTO 2026' in html, "no imprimió la fecha en que Calidad dispuso la caja"
    finally:
        _limpiar()
    mov2 = _sembrar(con_analisis=False)
    try:
        html2 = _rotulo(app, mov2)
        cuerpo = html2[html2.find('Fecha de an'):]
        celda = cuerpo[:cuerpo.find('</tr>')]
        assert '2026' not in celda, \
            "inventó una fecha de análisis para una caja que nadie revisó: %r" % celda[:120]
    finally:
        _limpiar()


def test_el_proveedor_cae_al_maestro_cuando_la_recepcion_no_lo_trae(app, db_clean):
    """`COALESCE(mv.proveedor, mm.proveedor)` no caía nunca: la columna es TEXT DEFAULT '' y
    COALESCE sólo salta el NULL, así que el formato salía SIN proveedor teniéndolo el maestro."""
    mov = _sembrar(proveedor_en_mov='')
    try:
        html = _rotulo(app, mov)
        assert 'VIDRIOS SA' in html, "el rótulo salió sin proveedor teniéndolo el maestro"
    finally:
        _limpiar()


# ── que quepa impreso, y que no vuelva a desbordar ───────────────────────────

def test_el_encabezado_conserva_las_tres_zonas_medidas(app, db_clean):
    """Medido con las reglas del `@media print` aplicadas: 96,8 mm de alto sobre una etiqueta de
    100 y cero desbordes. Antes daba 131 mm, o sea que cada rótulo se partía en dos etiquetas.

    El alto depende de que el bloque de control quede compacto y en su columna: si alguien
    borra estas reglas, el encabezado vuelve a estirarse y el rótulo a no caber."""
    _sembrar()
    try:
        html = _rotulo(app)
        for regla in ('.top.f06', '.f06doc', '.f06ctrl', '.f06tit'):
            assert regla + '{' in html, "falta la regla de layout %s" % regla
        m = re.search(r"\.f06ctrl\{([^}]*)\}", html)
        assert m, "no llegó el CSS del bloque de control"
        # Se fija la GARANTÍA, no el número: el bloque tiene ancho FIJO en milímetros -- si se
        # vuelve flexible, el encabezado se estira y el rótulo deja de caber -- y un cuerpo
        # pequeño. El valor exacto se ajusta al compactar, y eso no es una regresión (M97).
        _anchos = re.findall(r'flex:0 0 (\d+(?:\.\d+)?)mm', m.group(1))
        assert _anchos and 18 <= float(_anchos[0]) <= 32, \
            "el bloque de control perdió su ancho fijo: %r" % (m.group(1),)
        _fs = re.findall(r'font-size:\s*(\d+(?:\.\d+)?)(px|pt)', m.group(1))
        assert _fs and float(_fs[0][0]) <= 9, \
            "el bloque de control volvió a un tamaño que estira el encabezado: %r" % (_fs,)
    finally:
        _limpiar()


def test_las_marcas_del_SISTEMA_no_se_imprimen_en_el_formato(app, db_clean):
    """En producción el rótulo salía con *"[liberado 30-jul: los envases no van a cuarentena]"*
    dentro de OBSERVACIONES. Esa marca la escribió una MIGRACIÓN, no una persona: es correcta en
    la base -- traza el cambio de política -- y en el cartón se lee como una nota de quien
    recibió. Se quitan sólo las marcas DECLARADAS: filtrar cualquier corchete borraría lo que la
    gente escribe entre corchetes a propósito.
    """
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
         "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
         (_COD, 'ENVASE QA', 'Envase', 'PROV QA'))
    obs = ('Recepcion OC OC-2026-0282 [liberado 30-jul: los envases no van a cuarentena] '
           '[REVISADO] llego en [dos] estibas')
    _sql("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,responsable,"
         "fecha,observaciones,estado,anulado) VALUES (?,'Entrada',500,'und',?,'catalina',"
         "'2026-08-20',?,'VIGENTE',0)", (_COD, _LOTE, obs))
    try:
        html = _rotulo(app)
        assert 'liberado 30-jul' not in html, "imprime una marca que escribió una migración"
        assert 'REVISADO' not in html, "imprime la marca interna del cierre de revisión"
        assert 'Recepcion OC OC-2026-0282' in html, "se llevó por delante la observación real"
        assert 'llego en [dos] estibas' in html,             "borró un corchete que escribió una persona"
    finally:
        _limpiar()


# ── un rótulo POR CAJA, según lo que se declaró al recibir ───────────────────

def test_imprime_un_rotulo_por_CAJA_segun_lo_que_se_recibio(app, db_clean):
    """Sebastián 21-ago: *"en la recepción puso cuántas cajas y cuánto venían; al darle imprimir
    rótulo necesito que me genere TODOS para poder imprimirlos, según lo que ella puso"*.

    El circuito existía y ningún botón lo usaba: todos abrían la ruta de a UNO, así que de una
    recepción de 6 cajas salía un solo rótulo y las otras 5 cajas quedaban sin identificar.
    """
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
         "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
         (_COD, 'ENVASE QA', 'Envase', 'PROV QA'))
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        sin_cajas = conn.execute(
            "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,responsable,"
            "fecha,estado,anulado) VALUES (?,'Entrada',5551,'und','INT-1','catalina',"
            "'2026-08-06','VIGENTE',0)", (_COD,)).lastrowid
        con_cajas = conn.execute(
            "INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,responsable,"
            "fecha,estado,anulado,n_cajas,unidades_por_caja) VALUES (?,'Entrada',5551,'und',"
            "'OC-2026-0309','catalina','2026-08-06','VIGENTE',0,6,1000)", (_COD,)).lastrowid
        conn.commit()
    finally:
        conn.close()
    try:
        c = _login(app)
        html = c.get('/rotulos-recepcion-mee?mov=%d' % con_cajas).get_data(as_text=True)
        assert html.count('class="sheet"') == 6,             "se declararon 6 cajas y salieron %d rótulos" % html.count('class="sheet"')
        cajas = re.findall(r'Caja (\d+) de (\d+)', html)
        assert [x[0] for x in cajas] == ['1', '2', '3', '4', '5', '6'],             "los rótulos no vienen numerados por caja: %r" % (cajas,)
        assert all(x[1] == '6' for x in cajas), "no dicen de cuántas cajas son"
        # Sin cajas declaradas sale UNO: no hay caso en que imprima de menos.
        h1 = c.get('/rotulos-recepcion-mee?mov=%d' % sin_cajas).get_data(as_text=True)
        assert h1.count('class="sheet"') == 1,             "sin cajas declaradas debería salir un rótulo, salieron %d" % h1.count('class="sheet"')
    finally:
        _limpiar()


def test_el_boton_del_historial_pide_los_rotulos_POR_MOVIMIENTO(app, db_clean):
    """La capacidad estaba construida y sin puerta: el botón mandaba código y cantidad, que es
    justo lo que NO sabe de cajas (M121). Se mide sobre la pantalla SERVIDA (M216)."""
    from .conftest import pantalla_servida
    c = _login(app)
    js = pantalla_servida(c, '/inventarios')
    assert 'data-mov="' in js, "el botón del historial no manda el movimiento"
    i = js.find('function abrirRotuloMEE')
    assert i != -1, "no existe la función que abre el rótulo"
    cuerpo = js[i:i + 900]
    assert "/rotulos-recepcion-mee?mov=" in cuerpo,         "el botón sigue abriendo la ruta de a UNO, así que de 6 cajas imprime 1"


# ── la etiqueta térmica de 10x10 ────────────────────────────────────────────

def test_el_rotulo_esta_configurado_para_la_termica_de_10x10(app, db_clean):
    """Sebastián 21-ago: *"que sean configurados para ocupar la impresión de calor, que es
    10 x 10, que quede bien y se vean bien"*.

    Medido en el navegador con las reglas del `@media print` aplicadas, y con el PEOR caso
    (nombre de 65 caracteres, lote largo, observación de tres renglones): **95,3 mm de alto
    sobre 100, 4,7 mm de margen, cero desbordes y cero celdas solapadas**. Antes de estos
    ajustes el mismo caso daba **137,7 mm**, o sea que cada rótulo se comía dos etiquetas.

    Lo que sostiene esa medida y por eso se fija acá:
      · `print-color-adjust: exact` -- sin él el navegador DESCARTA los fondos y el chip del
        estado marcado se imprime sin relleno (M123);
      · el nombre del insumo se **escala** según su largo en vez de cortarse: un rótulo de
        identificación truncado no identifica (M203);
      · el ancho de las columnas -- con las etiquetas más anchas, "CAFARCOL" se partía en
        "CAFARC / OL" y la fecha en dos renglones;
      · el `@page` con el tamaño real de la etiqueta.
    """
    _sembrar()
    try:
        html = _rotulo(app)
        assert 'print-color-adjust:exact' in html.replace(' ', ''),             "sin esto la térmica no imprime los fondos ni el estado marcado"
        assert '@page{size:100mm 100mm' in html.replace(' ', '').replace(
            '@page{size:100mm100mm', '@page{size:100mm 100mm'),             "la página no está configurada al tamaño de la etiqueta"
        for regla in ('.name.n2{', '.name.n3{', '.name.n4{'):
            assert regla in html, "falta el escalón %s del nombre" % regla
        assert 'td.k{width:21%' in html.replace(' ', ''),             "el ancho de las etiquetas volvió a comerse el de los valores"
    finally:
        _limpiar()


def test_el_nombre_largo_se_ACHICA_pero_no_se_corta(app, db_clean):
    """Un nombre de 65 caracteres estiraba el título a 57 mm y el rótulo no cabía. Se escala,
    NUNCA se trunca: cortar el nombre del insumo en su rótulo de identificación es lo mismo
    que no identificarlo."""
    largo = 'ENVASE VIDRIO AMBAR 10 ML CON GOTERO PLASTICO NEGRO Y CONTRAPUNTA'
    _limpiar()
    _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
         "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
         (_COD, largo, 'Envase', 'CAFARCOL'))
    _sql("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,responsable,"
         "fecha,estado,anulado) VALUES (?,'Entrada',500,'und',?,'catalina','2026-08-20',"
         "'VIGENTE',0)", (_COD, _LOTE))
    try:
        html = _rotulo(app)
        assert largo in html, "cortó el nombre del insumo"
        assert 'class="name n4"' in html,             "un nombre de 65 caracteres tiene que bajar al escalón más chico"
        # y uno corto se queda en el tamaño grande, que es lo que se lee de lejos
        _limpiar()
        _sql("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
             "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
             (_COD, 'FRASCO 30ML', 'Envase', 'CAFARCOL'))
        _sql("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,unidad,lote_ref,"
             "responsable,fecha,estado,anulado) VALUES (?,'Entrada',500,'und',?,'catalina',"
             "'2026-08-20','VIGENTE',0)", (_COD, _LOTE))
        html2 = _rotulo(app)
        assert 'class="name n1"' in html2, "un nombre corto no debería achicarse"
    finally:
        _limpiar()


def test_el_logo_se_BINARIZA_para_la_termica(app, db_clean):
    """La térmica es de 1 bit: cada gris lo resuelve con una trama de puntos, así que un PNG
    con antialiasing sale RAYADO (M256, reportado con el F02 en la mano). Se reduce al tamaño
    de impresión y se binariza; si no se puede convertir, cae al logo normal -- un rótulo sin
    logo es peor que uno con el logo tramado."""
    from api.blueprints.inventario import _rotulo_logo_termico
    import io as _io
    src = _io.open('api/blueprints/inventario.py', encoding='utf-8').read()
    src = re.sub(r'^\s*#.*$', '', src, flags=re.M)
    assert '_rotulo_logo_termico(c)' in src,         "los rótulos de envase dejaron de usar el logo binarizado"
    assert '_logo_mono_datauri' in src, "no reusa el binarizador del F02 (dos binarizadores divergen)"


# ── el patrón que causó el proveedor vacío, en todo el repo ──────────────────

def test_ningun_COALESCE_deja_su_fallback_muerto(app, db_clean):
    """`COALESCE(a, b)` con `a` declarada `TEXT DEFAULT ''` devuelve la cadena vacía y **b nunca
    corre**: el fallback es un no-op justo donde uno cree que protege.

    Las excepciones se ENUMERAN con su motivo, no se dejan pasar en silencio (M122): en las tres
    el fallback MENTIRÍA, así que el vacío es la respuesta honesta.
    """
    import glob
    import io as _io
    esquema = _io.open('api/database.py', encoding='utf-8').read()
    defv = set(m.group(1).lower()
               for m in re.finditer(r"(\w+)\s+TEXT\s+DEFAULT\s+''", esquema, re.I))
    assert len(defv) > 100, "no se pudo leer el esquema: el barrido dejaría de medir"

    # Acá el vacío es MÁS honesto que el fallback:
    #  · fecha_recepcion -> fecha de la OC: diría que se recibió el día que se hizo la orden;
    #  · cantidad_recibida -> cantidad_enviada: ocultaría la merma de la serigrafía.
    EXCEPCIONES = {
        'COALESCE(oc.fecha_recepcion, oc.fecha',
        'COALESCE(mo.cantidad_recibida, mo.cantidad_enviada',
    }
    pat = re.compile(r"COALESCE\(\s*([a-z]{1,4})\.([a-z_]+)\s*,\s*([a-z]{1,4})\.([a-z_]+)", re.I)
    medidos, culpables = 0, []
    for f in sorted(glob.glob('api/blueprints/*.py')):
        src = _io.open(f, encoding='utf-8').read()
        for m in pat.finditer(src):
            medidos += 1
            a = (m.group(1).lower(), m.group(2).lower())
            b = (m.group(3).lower(), m.group(4).lower())
            if a == b or a[1] not in defv:
                continue
            if m.group(0) in EXCEPCIONES:
                continue
            if 'NULLIF' in src[max(0, m.start() - 30):m.start() + 90].upper():
                continue
            culpables.append('%s:%d  %s' % (f.replace(chr(92), '/'),
                                            src[:m.start()].count(chr(10)) + 1, m.group(0)))
    assert medidos >= 40, \
        "el barrido midió sólo %d expresiones: dejó de medir sin avisar" % medidos
    assert not culpables, (
        "estos COALESCE tienen el fallback muerto (la 1a columna nunca es NULL):\n  "
        + "\n  ".join(culpables))
