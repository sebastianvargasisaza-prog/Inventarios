# -*- coding: utf-8 -*-
"""La verificación de stock es una HOJA DE VERIFICACIÓN FÍSICA · 21-ago-2026.

Sebastián: *"quiero que esto sea más top, es la verificación de si hay stock ... sería genial
que sirva de una vez como verificación de inventario: sale la materia prima, lo que se necesita,
lo que hay, el lote a usar; entonces van y revisan y dicen si está OK lo usaré; no está, ¿por
qué? se acabó; si hay pero menos, entonces usaré otro; esto lo selecciona, cuánto hay de cada
uno. Y de una vez se ve premium, no colapsado"*.

Dos invariantes, y las dos son la razón de existir de la pantalla:

  · lo que el operario declara **corrige el kardex** por el endpoint de cuadre que ya existe
    (M3, no una segunda puerta) -- una verificación que no corrige nada es una lista de lectura
    y el descuadre sigue ahí mañana;
  · después de declarar **se vuelve a preguntar al motor**, nunca se recalcula en el navegador:
    así lo que la pantalla muestra es lo que el descuento va a hacer (M5).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida

_COD = 'MP-VERIF-TEST'
_PROD = 'PRODUCTO VERIF TEST'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _conn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _limpiar():
    """Limpieza ANTES de sembrar, con códigos FIJOS (M103)."""
    cn = _conn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (_COD,))
        cn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (_COD,))
        cn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (_PROD,))
        cn.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc='CUADRE'")
        cn.commit()
    finally:
        cn.close()


def _sembrar(gramos=5000.0):
    """Un producto de 1 kg al 10% de una MP con UN lote vigente."""
    _limpiar()
    cn = _conn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, "
                   "  activo, controla_stock, precio_referencia) VALUES (?,?,?,1,1,0)",
                   (_COD, 'GOMA VERIF', 'VERIF GUM'))
        cn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                   "VALUES (?,?,1)", (_PROD, 1))
        cn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                   "  porcentaje) VALUES (?,?,?,?)", (_PROD, _COD, 'GOMA VERIF', 10))
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                   "  lote, fecha, operador, estado_lote, fecha_vencimiento, estanteria) "
                   "VALUES (?,?,'Entrada',?,?,'2026-08-01 08:00','test','VIGENTE','2027-06-30','A3')",
                   (_COD, 'GOMA VERIF', gramos, 'LOTE-VF-1'))
        cn.commit()
    finally:
        cn.close()


def _cuerpo_de(js, decl):
    """Recorta UNA funcion por balance de llaves desde su declaracion.

    Un `js[i:i+N]` mide lo que quede a N caracteres, asi que el guard se vuelve verde el dia
    que alguien escriba otra funcion debajo (M229).
    """
    i = js.find(decl)
    assert i != -1, 'no encontre %s' % decl
    j = js.index('{', i)
    prof = 0
    for k in range(j, len(js)):
        if js[k] == '{':
            prof += 1
        elif js[k] == '}':
            prof -= 1
            if prof == 0:
                return js[i:k + 1]
    raise AssertionError('no cerro %s' % decl)


def _simular(c, kg=1):
    r = c.post('/api/produccion/simular', json={'producto': _PROD, 'cantidad_kg': kg},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    fila = next((i for i in d['ingredientes'] if i.get('codigo_bodega') == _COD
                 or i.get('material_id') == _COD), None)
    assert fila, 'la simulación no trae la MP sembrada: %r' % (d,)
    return d, fila


# ───────────────────────── la hoja trae con qué trabajar ─────────────────────────

def test_la_hoja_trae_el_lote_con_su_cantidad_y_donde_esta(app, db_clean):
    """Lo que Sebastián pidió ver: la MP, lo que se necesita, lo que hay y el lote a usar."""
    _sembrar()
    try:
        d, fila = _simular(_login(app))
        assert fila['g_requerido'] == 100, fila           # 10% de 1 kg
        assert fila['g_disponible'] == 5000, fila
        lotes = fila.get('lotes') or []
        assert lotes, 'sin el lote, el operario no sabe qué bajar del estante'
        assert lotes[0]['lote'] == 'LOTE-VF-1'
        assert lotes[0]['g'] == 5000
        assert 'A3' in (lotes[0].get('ubicacion') or ''), \
            'no dice DÓNDE está: %r' % (lotes[0],)
    finally:
        _limpiar()


# ───────────── lo que se declara CORRIGE el kardex y el motor lo ve ─────────────

def test_declarar_HAY_MENOS_corrige_el_inventario_y_el_motor_lo_ve(app, db_clean):
    """El caso que motivó la pantalla: hay, pero menos de lo que el sistema creía."""
    _sembrar(gramos=5000)
    try:
        c = _login(app)
        _d, antes = _simular(c)
        assert antes['g_disponible'] == 5000

        r = c.post('/api/inventario/cuadre',
                   json={'codigo_mp': _COD, 'lote': 'LOTE-VF-1', 'fisico': 80,
                         'motivo': 'verificación física antes de producir',
                         'token': 'verif-menos-1'}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]

        _d2, despues = _simular(c)
        assert despues['g_disponible'] == 80, \
            'el motor sigue creyendo %r: la declaración no corrigió el kardex' % (despues['g_disponible'],)
        assert not despues['suficiente'] and despues['g_faltante'] == 20, despues
    finally:
        _limpiar()


def test_declarar_NO_ESTA_deja_el_lote_en_cero_y_conserva_su_rastro(app, db_clean):
    """*"no está, ¿por qué? se acabó"* -- el lote baja a 0 y el motivo queda auditado."""
    _sembrar(gramos=5000)
    try:
        c = _login(app)
        r = c.post('/api/inventario/cuadre',
                   json={'codigo_mp': _COD, 'lote': 'LOTE-VF-1', 'fisico': 0,
                         'motivo': 'se acabó', 'token': 'verif-noesta-1'},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]

        _d, fila = _simular(c)
        assert fila['g_disponible'] == 0, fila
        assert not fila['suficiente']
        assert not (fila.get('lotes') or []), \
            'el lote en cero sigue ofreciéndose como usable: el operario iría a buscar aire'

        cn = _conn()
        try:
            obs = cn.execute("SELECT observaciones FROM movimientos WHERE material_id=? "
                             "  AND tipo='Salida' ORDER BY id DESC LIMIT 1", (_COD,)).fetchone()
            aud = cn.execute("SELECT COUNT(*) FROM audit_log WHERE accion='CUADRE_INVENTARIO' "
                             "  AND registro_id=?", (_COD,)).fetchone()
        finally:
            cn.close()
        assert obs and 'se acab' in (obs[0] or ''), \
            'el motivo no quedó en el rastro del ajuste: %r' % (obs,)
        assert aud and aud[0] >= 1, 'el ajuste no dejó auditoría (Part 11)'
    finally:
        _limpiar()


def test_declarar_lo_MISMO_no_ensucia_el_kardex(app, db_clean):
    """Contar y encontrar lo mismo se confirma, pero no escribe un movimiento (M260)."""
    _sembrar(gramos=5000)
    try:
        c = _login(app)
        cn = _conn()
        try:
            n0 = cn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id=?",
                            (_COD,)).fetchone()[0]
        finally:
            cn.close()
        r = c.post('/api/inventario/cuadre',
                   json={'codigo_mp': _COD, 'lote': 'LOTE-VF-1', 'fisico': 5000,
                         'motivo': 'verificación física', 'token': 'verif-igual-1'},
                   headers=csrf_headers())
        assert r.status_code == 200 and r.get_json().get('sin_cambio') is True, r.data[:300]
        cn = _conn()
        try:
            n1 = cn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id=?",
                            (_COD,)).fetchone()[0]
        finally:
            cn.close()
        assert n1 == n0, 'confirmar que coincide escribió un movimiento de más'
    finally:
        _limpiar()


def test_un_doble_click_no_ajusta_dos_veces(app, db_clean):
    """El mismo token se rechaza: un doble ajuste de stock no da NINGÚN síntoma (M260)."""
    _sembrar(gramos=5000)
    try:
        c = _login(app)
        cuerpo = {'codigo_mp': _COD, 'lote': 'LOTE-VF-1', 'fisico': 80,
                  'motivo': 'verificación física', 'token': 'verif-doble-1'}
        assert c.post('/api/inventario/cuadre', json=cuerpo,
                      headers=csrf_headers()).status_code == 200
        r2 = c.post('/api/inventario/cuadre', json=cuerpo, headers=csrf_headers())
        assert r2.status_code == 409, r2.data[:200]
        _d, fila = _simular(c)
        assert fila['g_disponible'] == 80, \
            'el segundo clic volvió a ajustar: quedó en %r' % (fila['g_disponible'],)
    finally:
        _limpiar()


# ───────────────────────── la pantalla puede hacerlo ─────────────────────────

def test_la_pantalla_ofrece_las_TRES_declaraciones(app, db_clean):
    """Un endpoint sin puerta no existe (M121): los tres botones tienen que estar."""
    js = pantalla_servida(_login(app), '/inventarios')
    for fn in ('function verifOk', 'async function verifMenos', 'async function verifNoEsta'):
        assert fn in js, 'falta %s: esa declaración no se puede hacer desde la pantalla' % fn
    assert 'verifOk(' in js and 'verifMenos(' in js and 'verifNoEsta(' in js, \
        'las funciones existen y ningún botón las llama'


def test_lo_declarado_va_al_KARDEX_por_el_endpoint_que_YA_existe(app, db_clean):
    """No una segunda puerta de ajuste: la que ya audita y conserva estado y vencimiento (M3)."""
    js = pantalla_servida(_login(app), '/inventarios')
    i = js.find('async function _verifCuadrar')
    assert i != -1, 'lo que se declara no se guarda en ninguna parte'
    # La ventana se acota al CUERPO real, no a N caracteres: una ventana fija la secuestra
    # cualquier funcion que se escriba mas abajo y el guard deja de medir sin avisar (M229).
    cuerpo = _cuerpo_de(js, 'async function _verifCuadrar')
    assert '/api/inventario/cuadre' in cuerpo, \
        'la declaración no escribe el kardex: sería una lista de lectura'
    assert 'X-CSRF-Token' in cuerpo, 'POST sin token CSRF'
    assert 'simularProduccion()' in cuerpo, \
        'no vuelve a preguntarle al motor: mostraría una cuenta paralela que puede divergir (M5)'


def test_el_aviso_apunta_al_contenedor_REAL_y_sobrevive_al_refresco(app, db_clean):
    """El primer intento escribía en un id que no existe: el aviso no se veía NUNCA (M121).

    Y aunque se viera, `simularProduccion` reescribe el panel entero medio segundo después,
    así que el mensaje tiene que re-pintarse desde una variable, no vivir sólo en el DOM.
    """
    js = pantalla_servida(_login(app), '/inventarios')
    i = js.find('function _verifMsg')
    assert i != -1
    cuerpo = js[i:i + 700]
    assert "getElementById('prod-simul-result')" in cuerpo, \
        'el aviso apunta a un contenedor que no existe en esta pantalla'
    assert "getElementById('sim-result')" not in cuerpo, 'volvió el id equivocado'
    assert 'function _verifBannerHTML' in js, 'el aviso no sobrevive al re-render del panel'
    j = js.find('panel.innerHTML=_verifBannerHTML()')
    assert j != -1, 'el panel se re-pinta SIN el aviso: la confirmación se borra sola'


def test_el_dato_del_lote_no_puede_ROMPER_el_boton(app, db_clean):
    """Las comillas dobles de JSON.stringify cierran el atributo `onclick` (M173).

    El node-check pasa verde porque el JavaScript es válido: lo que queda partido es el HTML
    que ese JavaScript arma, y el botón deja de funcionar para ese lote.
    """
    js = pantalla_servida(_login(app), '/inventarios')
    # Se exige el helper CANONICO `_q`, no que esta pantalla lo resuelva a su manera: dos
    # copias del mismo idiom divergen y ahi un boton escapa las comillas y el de al lado
    # no. El guard de M173 ya lo decia con todas las letras y escribi la copia igual.
    cuerpo = _cuerpo_de(js, 'function _q(')
    assert 'replace(/"/g' in cuerpo, 'el helper canonico dejo de escapar las comillas'
    j = js.find('class="vf-b vf-b-ok"')
    assert j != -1, 'no encontre los botones de la hoja'
    ventana = js[j:j + 600]
    # Los TRES botones, no alguno: con `'_q(' in ventana` basta que uno lo use y el guard
    # pasa verde con los otros dos rotos. Son 3 botones x 2 argumentos = 6.
    assert 'JSON.stringify' not in ventana, \
        'un boton arma su argumento a mano en vez de pedirselo al helper canonico'
    assert ventana.count('_q(') >= 6, \
        'solo %d de los 6 argumentos pasan por _q: ese lote parte el onclick' % ventana.count('_q(')
    assert '_vfArg' not in js, \
        'volvio un segundo helper que hace lo mismo que _q (se rompe el punto unico)'


def test_la_hoja_se_ve_como_hoja_y_no_como_tabla_apretada(app, db_clean):
    """*"que se vea premium, no colapsado"* -- y con el progreso de lo ya revisado a la vista."""
    js = pantalla_servida(_login(app), '/inventarios')
    assert "id='vf-css'" in js or 'id="vf-css"' in js, 'la hoja no trae su estilo propio'
    for clase in ('.vf-card{', '.vf-lote{', '.vf-mat{', '.vf-prog-r{', '.vf-ret{'):
        assert clase in js, 'falta el estilo %s' % clase
    assert 'lotes revisados' in js, \
        'la hoja no dice cuántos lotes se llevan verificados: no se sabe qué falta por mirar'
    # los colores del panel salen de tokens: un hex fijo ignora el tema oscuro (M104/M114)
    i = js.find('async function simularProduccion')
    cuerpo = js[i:i + 6000]
    for muerto in ("'#f0fff4'", "'#fff5f5'", "'#28a745'", "'#dc3545'", "'#fff0f0'"):
        assert muerto not in cuerpo, \
            'quedó el color fijo %s: en tema oscuro la hoja se despinta' % muerto


# ───────────── la hoja muestra TODOS los lotes y cuánto sale de cada uno ─────────────

def test_muestra_TODOS_los_lotes_no_una_muestra_de_cuatro(app, db_clean):
    """Sebastián: *"que muestre lotes disponibles"*.

    Mostraba cuatro. Con el material repartido en más, el operario ve una parte y no sabe que
    hay más -- ni cuáles va a tomar el descuento.
    """
    _sembrar(gramos=100)
    cn = _conn()
    try:
        for i in range(2, 8):
            cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                       "  lote, fecha, operador, estado_lote, fecha_vencimiento, estanteria) "
                       "VALUES (?,?,'Entrada',?,?,'2026-08-01 08:00','test','VIGENTE',?,'A%d')"
                       % i, (_COD, 'GOMA VERIF', 100.0 * i, 'LOTE-VF-%d' % i,
                             # fechas REALES: '2027-02-30' no existe y el sistema la trata como
                             # ilegible -- correctamente. Un dato de prueba imposible mide el
                             # guard de fechas, no el de la lista (M170).
                             '2027-%02d-15' % (i + 1)))
        cn.commit()
    finally:
        cn.close()
    try:
        _d, fila = _simular(_login(app))
        assert len(fila['lotes']) == 7, \
            'sigue recortando la lista: muestra %d de 7' % len(fila['lotes'])
        assert fila.get('lotes_ocultos') == 0, \
            'oculta lotes sin declararlo: un tope que no se dice se lee como el total (M155)'
    finally:
        _limpiar()


def test_cada_lote_dice_CUANTO_sale_de_el_en_orden_FEFO(app, db_clean):
    """El operario necesita saber cuánto pesar de cada uno, no el saldo del lote.

    Y el reparto usa el MISMO orden que el FEFO real: si la hoja repartiera distinto, mandaría a
    pesar de un lote y el kardex anotaría el consumo de otro (M5/M263).
    """
    _sembrar(gramos=60)                      # LOTE-VF-1 vence 2027-06-30
    cn = _conn()
    try:
        cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                   "  fecha, operador, estado_lote, fecha_vencimiento, estanteria) "
                   "VALUES (?,?,'Entrada',500,'LOTE-TARDE','2026-08-01 08:00','test','VIGENTE',"
                   "        '2028-12-31','B1')", (_COD, 'GOMA VERIF'))
        cn.commit()
    finally:
        cn.close()
    try:
        _d, fila = _simular(_login(app))     # necesita 100 g (10% de 1 kg)
        lotes = {x['lote']: x for x in fila['lotes']}
        assert lotes['LOTE-VF-1']['toma_g'] == 60, \
            'el que vence antes tiene que salir COMPLETO primero: %r' % (lotes['LOTE-VF-1'],)
        assert lotes['LOTE-TARDE']['toma_g'] == 40, \
            'el resto sale del siguiente en vencimiento: %r' % (lotes['LOTE-TARDE'],)
        assert not lotes['LOTE-TARDE']['reserva']
    finally:
        _limpiar()


def test_el_lote_que_NO_hace_falta_se_marca_como_reserva(app, db_clean):
    """Un lote que la producción no va a tocar no puede verse igual que uno del que hay que
    pesar: el operario lo bajaría del estante para nada."""
    _sembrar(gramos=5000)
    try:
        _d, fila = _simular(_login(app))     # necesita 100 de 5000
        assert fila['lotes'][0]['toma_g'] == 100
        assert fila['lotes'][0]['reserva'] is False
    finally:
        _limpiar()


def test_la_hoja_separa_lo_que_FALTA_de_lo_que_ALCANZA(app, db_clean):
    """*"Sería bueno que se vea mejor, mayor claridad, que se diferencien las partes"*.

    Con el estante enfrente lo primero que hay que ver es qué falta; mezclado entre lo que
    alcanza se pierde entre decenas de lotes corridos.
    """
    js = pantalla_servida(_login(app), '/inventarios')
    assert 'function _vfSecciones' in js, 'la hoja no separa las secciones'
    cuerpo = _cuerpo_de(js, 'function _vfSecciones')
    assert 'Falta material' in cuerpo, 'no rotula la sección de lo que falta'
    assert 'suficiente' in cuerpo, 'el corte no usa el mismo criterio que el motor'
    assert '.vf-sec-falta' in js and '.vf-sec-ok' in js, 'las secciones no tienen estilo propio'


def test_el_corte_de_las_secciones_usa_el_ORDEN_del_motor(app, db_clean):
    """El backend ordena los insuficientes primero. Si la pantalla los re-ordenara por su cuenta,
    tendríamos dos criterios del mismo hecho y divergirían (M5/M99)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'function _vfSecciones')
    for propio in ('.sort(', '.filter('):
        assert propio not in cuerpo, \
            'la pantalla re-ordena por su cuenta (%s) en vez de respetar el orden del motor' % propio


# ───────────── la revisión se INICIA y se FINALIZA ─────────────

def test_la_revision_tiene_INICIAR_y_FINALIZAR(app, db_clean):
    """Sebastián: *"quiero que se le dé iniciar y finalizar, y así al finalizar que diga: estas
    materias primas no las tocaste, y las liste, así las buscamos o decimos no están"*.

    Sin cierre, una hoja de 52 lotes se abandona a la mitad y el progreso no distingue *"no
    arranqué"* de *"arranqué y me quedaron 40"*.
    """
    js = pantalla_servida(_login(app), '/inventarios')
    for fn in ('function vfIniciarRevision', 'function vfFinalizarRevision',
               'function _vfCierreHTML', 'function _vfBarraSesion'):
        assert fn in js, 'falta %s' % fn
    assert 'vfIniciarRevision()' in js and 'vfFinalizarRevision()' in js, \
        'las funciones existen y ningún botón las llama (M121)'


def test_iniciar_AVISA_antes_de_borrar_lo_declarado(app, db_clean):
    """Borrar el trabajo de la revisión anterior en silencio hace que el progreso mida otra cosa
    sin que nadie se entere."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'function vfIniciarRevision')
    assert 'confirm(' in cuerpo, 'reinicia la revisión sin avisar'
    assert 'no se tocan' in cuerpo or 'ya guardaste' in cuerpo, \
        ('no aclara que los ajustes YA guardados en el inventario no se borran: si no, nadie se '
         'anima a reiniciar')


def test_lo_pendiente_se_puede_CERRAR_desde_la_lista(app, db_clean):
    """Una lista de pendientes que sólo se puede leer manda a empezar de nuevo, y ahí es donde se
    abandona (M121: la acción va donde la persona está parada)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'function _vfCierreHTML')
    for accion in ('verifOk(', 'verifMenos(', 'verifNoEsta('):
        assert accion in cuerpo, 'desde el cierre no se puede declarar con %s' % accion
    assert 'no las tocaste' in cuerpo, 'el cierre no dice qué quedó sin revisar'


def test_declarar_desde_el_cierre_lo_saca_de_la_lista(app, db_clean):
    """Si el lote siguiera en la lista después de declararlo, la persona no sabría cuál ya cerró
    y volvería a buscarlo (M129)."""
    js = pantalla_servida(_login(app), '/inventarios')
    assert 'function _vfSacarDePendientes' in js, 'la lista no se achica al declarar'
    for fn in ('function verifOk', 'async function _verifCuadrar'):
        cuerpo = _cuerpo_de(js, fn)
        assert '_vfSacarDePendientes(' in cuerpo, \
            '%s no saca el lote de los pendientes' % fn


# ───────────── repartir a mano desde la hoja ─────────────

def test_la_hoja_deja_REPARTIR_a_mano_entre_lotes(app, db_clean):
    """*"Elegir a mano de qué lote sale cada gramo"*."""
    js = pantalla_servida(_login(app), '/inventarios')
    for fn in ('function vfRepartir', 'function vfRepCambio', 'function _vfPintarSuma',
               'function vfRepCuadraTodo'):
        assert fn in js, 'falta %s' % fn
    assert 'vfRepartir(' in js, 'ningún botón entra al reparto'


def test_el_reparto_se_valida_MIENTRAS_se_escribe(app, db_clean):
    """Descubrir que no cuadra recién al apretar el botón es mandar a rehacerlo (M197)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'function vfRepCambio')
    assert '_vfPintarSuma(' in cuerpo, 'la suma no se recalcula al escribir'
    pinta = _cuerpo_de(js, 'function _vfPintarSuma')
    assert 'faltan' in pinta and 'sobran' in pinta, \
        'no dice cuánto falta o sobra: obliga a hacer la cuenta a mano'
    assert '_vfBotonFabricar(' in pinta, 'el botón de fabricar no se entera'


def test_con_un_reparto_que_NO_cuadra_no_se_puede_fabricar(app, db_clean):
    """Un reparto que no cuadra se ve resuelto, y con eso se descontaría (M195)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'function _vfBotonFabricar')
    assert 'disabled' in cuerpo, 'el botón no se bloquea'
    assert 'vfRepCuadraTodo()' in cuerpo, 'no consulta si el reparto cuadra'
    # y el backend igual lo rechaza: la pantalla no es el control
    ini = _cuerpo_de(js, 'window.iniciarFabVivo=async function')
    assert 'reparto_lotes' in ini, \
        'el reparto se queda en la pantalla y el kardex descontaría por FEFO (M5/M109)'
    assert 'vfRepCuadraTodo' in ini, 'no revalida antes de mandar'
