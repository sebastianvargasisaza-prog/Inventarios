# -*- coding: utf-8 -*-
"""UN registro para el bloque de control de los formatos regulados · 21-ago-2026.

Aseguramiento declaró no negociable que un formato impreso lleve **Código · Versión · Página ·
Vigencia**: es la evidencia de que se llenó la versión vigente (M251). El rótulo de ingreso de
MATERIA PRIMA sólo decía el código y la fecha de impresión.

Y el arreglo de fondo no es escribirle la versión al rótulo, es que **los tres formatos la pidan
al mismo lugar**: dos copias escritas a mano divergen, y el día que se libere la versión 03 una
sigue diciendo 02 con la misma cara de oficial.

⚠ Lo que NO se hace: inventar la versión del F07. Un dato de control fabricado en un documento
regulado es peor que su ausencia (M19/M242) -- se declara el hueco para que alguien lo llene.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _resolver(codigo):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    'api'))
    from audit_helpers import formato_control
    cn = _cn()
    try:
        return formato_control(cn.cursor(), codigo)
    finally:
        cn.close()


# ───────────────────── el registro existe y trae lo que ya se imprimía ─────────────────────

def test_los_formatos_que_YA_se_imprimian_no_cambian(app, db_clean):
    """El cambio mueve de DÓNDE sale el dato, no lo que dice: si el F02 o el F06 salieran
    distintos, se habría cambiado un documento regulado sin que nadie lo pidiera."""
    f02 = _resolver('PRD-PRO-002-F02')
    assert f02['version'] == '02' and f02['pagina'] == '1 de 1'
    assert f02['desde'] == '09-Abr-2026' and f02['hasta'] == '08-Abr-2029'
    assert f02['completo'] is True

    f06 = _resolver('COC-PRO-002-F06')
    assert f06['version'] == '02'
    assert f06['desde'] == '21-Jul-2026' and f06['hasta'] == '20-Jul-2029'
    assert f06['completo'] is True


def test_el_F07_declara_lo_que_le_FALTA_en_vez_de_inventarlo(app, db_clean):
    """No conozco su versión ni su vigencia. Una versión fabricada en un documento regulado es
    peor que su ausencia: nadie la corrige porque nadie se entera (M19/M242)."""
    f07 = _resolver('COC-PRO-002-F07')
    assert f07['codigo'] == 'COC-PRO-002-F07'
    assert f07['titulo'], 'ni siquiera dice de qué formato es'
    assert f07['version'] == '', 'le inventó una versión'
    assert f07['completo'] is False
    assert 'version' in f07['falta'] and 'desde' in f07['falta'], f07['falta']


def test_un_formato_desconocido_no_inventa_nada(app, db_clean):
    """Pedir un código que no está registrado devuelve el hueco declarado, no un bloque vacío
    que parece completo (M100)."""
    d = _resolver('XXX-NO-EXISTE-F99')
    assert d['completo'] is False
    assert d['version'] == '' and d['titulo'] == ''
    assert set(d['falta']) == {'version', 'desde', 'hasta'}


def test_lo_que_Aseguramiento_cargue_MANDA_sobre_el_respaldo(app, db_clean):
    """El respaldo en código existe para que un rótulo no salga sin identificar si la migración
    no corrió; en cuanto la tabla tiene el dato, manda la tabla -- si no, cargar la versión 03
    no cambiaría nada y la tabla sería decorativa."""
    cn = _cn()
    try:
        cn.execute("UPDATE formatos_control SET version='03', desde='01-Ene-2027', "
                   "  hasta='31-Dic-2029' WHERE codigo='COC-PRO-002-F06'")
        cn.commit()
    finally:
        cn.close()
    try:
        d = _resolver('COC-PRO-002-F06')
        assert d['version'] == '03', 'sigue leyendo el valor escrito en el código: %r' % (d,)
        assert d['desde'] == '01-Ene-2027'
    finally:
        cn = _cn()
        try:
            cn.execute("UPDATE formatos_control SET version='02', desde='21-Jul-2026', "
                       "  hasta='20-Jul-2029' WHERE codigo='COC-PRO-002-F06'")
            cn.commit()
        finally:
            cn.close()


# ───────────────────── el rótulo IMPRESO lo lleva ─────────────────────

def _html_rotulo_mp(cli):
    """El HTML SERVIDO del rótulo, que es contra lo que hay que comparar -- no contra el fuente
    ni contra el recuerdo de qué imprime la pantalla (M264)."""
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id='MP-ROT-F07'")
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                   "  fecha, operador, estado_lote, fecha_vencimiento) "
                   "VALUES ('MP-ROT-F07','GOMA ROTULO F07','Entrada',5000,'LOTE-F07',"
                   "        '2026-08-01 08:00','test','CUARENTENA','2027-06-30')")
        cn.commit()
    finally:
        cn.close()
    # La ruta se verifica contra el codigo, no contra el recuerdo (M202): la de a UNO es
    # `/rotulo-recepcion/<codigo>/<lote>/<cantidad>`; `/rotulos-recepcion` es la de bloque y
    # pide `?movs=`.
    return cli.get('/rotulo-recepcion/MP-ROT-F07/LOTE-F07/5000')


def test_el_rotulo_de_MP_imprime_su_bloque_de_control_completo(app, db_clean):
    """Antes decía el código del formato y la fecha de impresión: sin versión, sin página y sin
    vigencia, que es justamente la evidencia de que se usó la versión vigente (M251/M264)."""
    cli = _login(app)
    r = _html_rotulo_mp(cli)
    assert r.status_code == 200, r.data[:300]
    html = r.get_data(as_text=True)
    try:
        assert 'COC-PRO-002-F07' in html, 'el rótulo dejó de decir de qué formato es'
        assert 'gina</b> 1 de 1' in html, 'no imprime la página'
        # el F07 todavía no tiene versión cargada: el rótulo tiene que DECIRLO
        assert 'Falta cargar' in html, \
            'el hueco no se ve en el papel: un renglón ausente se lee como si estuviera completo'
        assert 'ctrl-falta' in html, 'el aviso no tiene estilo propio: en térmica no marcaría'
    finally:
        cn = _cn()
        try:
            cn.execute("DELETE FROM movimientos WHERE material_id='MP-ROT-F07'")
            cn.commit()
        finally:
            cn.close()


def test_cargar_la_version_hace_desaparecer_el_aviso_del_papel(app, db_clean):
    """La prueba de que el registro sirve: cargar el dato cambia lo impreso, sin desplegar."""
    cli = _login(app)
    cn = _cn()
    try:
        cn.execute("UPDATE formatos_control SET version='01', desde='01-Ene-2026', "
                   "  hasta='31-Dic-2028' WHERE codigo='COC-PRO-002-F07'")
        cn.commit()
    finally:
        cn.close()
    try:
        html = _html_rotulo_mp(cli).get_data(as_text=True)
        assert 'Versi&oacute;n</b> 01' in html, 'cargó la versión y el rótulo la ignora'
        assert '01-Ene-2026' in html, 'no imprime la vigencia cargada'
        assert 'Falta cargar' not in html, 'sigue avisando de algo que ya está cargado'
    finally:
        cn = _cn()
        try:
            cn.execute("UPDATE formatos_control SET version='', desde='', hasta='' "
                       "  WHERE codigo='COC-PRO-002-F07'")
            cn.execute("DELETE FROM movimientos WHERE material_id='MP-ROT-F07'")
            cn.commit()
        finally:
            cn.close()


def test_el_bloque_se_arma_UNA_vez_y_no_por_recipiente(app, db_clean):
    """Una tanda son 40 rótulos: consultar el registro en cada uno es pagar 40 veces lo mismo
    dentro de un loop (M43)."""
    import io as _io
    import re as _re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = _io.open(os.path.join(raiz, 'api', 'blueprints', 'inventario.py'),
                   encoding='utf-8').read()
    i = src.find('def _sheet_mp(amt, idx):')
    assert i != -1
    # el cuerpo del generador por-recipiente no puede llamar al resolvedor
    j = src.find('\n    return ', i)
    cuerpo = src[i:j if j > i else i + 4000]
    assert '_rotulo_ctrl_mp(' not in cuerpo, \
        'el bloque de control se resuelve DENTRO del loop: 40 rótulos = 40 consultas'
    assert '_ctrl_f07' in cuerpo, 'el rótulo no usa el bloque que se armó afuera'
    del _re


# ───────────────────── la pantalla existe y el permiso es el correcto ─────────────────────

def test_Aseguramiento_puede_CARGAR_la_version(app, db_clean):
    """Sin pantalla, el registro es una capacidad a la que nadie llega (M121)."""
    c = _login(app, 'miguel')            # Aseguramiento
    r = c.get('/admin/formatos-control')
    assert r.status_code == 200, r.data[:200]
    html = r.get_data(as_text=True)
    assert 'COC-PRO-002-F07' in html, 'la pantalla no lista el formato que falta completar'
    assert 'Falta' in html, 'no marca cuál está incompleto'

    r2 = c.post('/api/admin/formatos-control',
                json={'codigo': 'COC-PRO-002-F07', 'version': '01'},
                headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:250]
    try:
        assert _resolver('COC-PRO-002-F07')['version'] == '01'
    finally:
        cn = _cn()
        try:
            cn.execute("UPDATE formatos_control SET version='' WHERE codigo='COC-PRO-002-F07'")
            cn.commit()
        finally:
            cn.close()


def test_el_Director_Tecnico_tambien_entra(app, db_clean):
    """Hernando firma con estos formatos todos los días: un gate escrito con el set de OTRO
    puesto le cierra la puerta a quien hace el acto (M210/M257)."""
    r = _login(app, 'hernando').get('/admin/formatos-control')
    assert r.status_code == 200, r.data[:200]


def test_y_el_guard_sigue_teniendo_dientes(app, db_clean):
    """Ampliar un permiso sin probar el borde es cambiar un control por una puerta abierta."""
    c = _login(app, 'jefferson')          # marketing: no gobierna documentos del SGC
    assert c.get('/admin/formatos-control').status_code == 403
    r = c.post('/api/admin/formatos-control',
               json={'codigo': 'COC-PRO-002-F06', 'version': '99'}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]
    assert _resolver('COC-PRO-002-F06')['version'] == '02', 'igual escribió'


def test_cambiar_la_version_deja_RASTRO_de_cual_era_antes(app, db_clean):
    """Ante un rótulo con la versión equivocada la pregunta es *cuál decía antes* (M175)."""
    c = _login(app, 'miguel')
    c.post('/api/admin/formatos-control',
           json={'codigo': 'COC-PRO-002-F06', 'version': '03'}, headers=csrf_headers())
    try:
        cn = _cn()
        try:
            fila = cn.execute(
                "SELECT antes, despues FROM audit_log WHERE accion='FORMATO_CONTROL_ACTUALIZAR' "
                "  AND registro_id='COC-PRO-002-F06' ORDER BY id DESC LIMIT 1").fetchone()
        finally:
            cn.close()
        assert fila, 'cambiar la versión de un formato regulado no dejó rastro'
        assert '02' in str(fila[0]), 'el rastro no dice cuál era antes: %r' % (fila[0],)
        assert '03' in str(fila[1])
    finally:
        cn = _cn()
        try:
            cn.execute("UPDATE formatos_control SET version='02' WHERE codigo='COC-PRO-002-F06'")
            cn.commit()
        finally:
            cn.close()


def test_la_pestaña_de_Aseguramiento_tiene_sus_CUATRO_enganches(app, db_clean):
    """Falta uno y el panel queda en blanco sin un solo error: el conmutador apaga todos los
    paneles antes de encender el destino (M155/M112)."""
    import io as _io
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = _io.open(os.path.join(raiz, 'api', 'templates_py', 'aseguramiento_html.py'),
                   encoding='utf-8').read()
    assert "goTab('tab-formatos')" in src, 'no hay botón'
    assert 'id="tab-formatos"' in src, 'no hay panel'
    assert "'tab-formatos'" in src.split('_tabIds')[1][:900], \
        'la pestaña no está en el conmutador: la pantalla quedaría en blanco'
    assert "formatos-ifr" in src and '/admin/formatos-control' in src, \
        'el panel nunca carga la pantalla'
