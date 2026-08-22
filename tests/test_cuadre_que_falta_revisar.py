# -*- coding: utf-8 -*-
"""El cuadre dice cuál ya se revisó y, al ACABAR, qué lotes no se vieron · 22-ago-2026.

Sebastián, con la estantería 10 recién contada: *"no sé cuáles revisé y cuáles no"* · *"ya hice
toda la estantería 10 y no sé qué me faltó"* · *"lo más importante es que si digo ACABÉ me diga:
estos lotes, ¿dónde están? ¿no los encontraste?"*.

El contador decía **0 de 54** con la estantería entera declarada, porque sólo sumaba lo que se
apretó en ESA pestaña: al refrescar arranca en cero, y cada fila se ve idéntica.

**La verdad de qué se revisó ya existía**: cada declaración escribe `audit_log`
(`CUADRE_INVENTARIO` si ajustó, `CUADRE_CONFIRMA` si coincide). Leerlo de ahí es mejor que
guardar un estado nuevo -- sobrevive al refresco, vale aunque revisen entre dos personas, y no
puede divergir de lo que de verdad pasó (M9: el registro es el hecho).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida

# El `audit_log` es append-only por trigger (Part 11): no se puede limpiar entre tests, así que
# el rastro de uno marcaría como revisado el material del siguiente. Cada test se lleva su propio
# código y su propia estantería -- su universo es suyo (M102/M103).
_COD = 'MP-CUADRE-REV'
_EST = 'EST-REV-TEST'


def _propio(nombre):
    """Devuelve (codigo, estanteria) exclusivos de ese test."""
    _sufijo = nombre.upper()[:14]
    return ('MP-CQ-' + _sufijo, 'EST-CQ-' + _sufijo)


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _limpiar(cod=_COD):
    """Limpieza ANTES de sembrar, con códigos FIJOS (M103).

    El `audit_log` NO se limpia: es append-only por trigger, y ésa es justamente la razón de que
    cada test use su propio código.
    """
    cn = _cn()
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id=?", (cod,))
        cn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        cn.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc='CUADRE'")
        cn.commit()
    finally:
        cn.close()


def _sembrar(lotes=('L-A', 'L-B', 'L-C'), cod=_COD, est=_EST):
    _limpiar(cod)
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo, "
                   "  controla_stock, precio_referencia) VALUES (?,?,?,1,1,0)",
                   (cod, 'GOMA CUADRE', 'CUADRE GUM'))
        for i, lo in enumerate(lotes, start=1):
            cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                       "  lote, fecha, operador, estado_lote, fecha_vencimiento, estanteria, "
                       "  posicion) VALUES (?,?,'Entrada',?,?,'2026-08-01 08:00','test',"
                       "  'VIGENTE','2027-06-30',?,?)",
                       (cod, 'GOMA CUADRE', 100.0 * i, lo, est, chr(64 + i)))
        cn.commit()
    finally:
        cn.close()


def _lotes(cli, est=_EST):
    r = cli.get('/api/inventario/cuadre-lotes?est=%s' % est)
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('ok'), d
    return d


def _declarar(cli, lote, fisico, motivo='revision fisica', token=None,
              cod=_COD, est=_EST):
    return cli.post('/api/inventario/cuadre',
                    json={'codigo_mp': cod, 'lote': lote, 'fisico': fisico,
                          'motivo': motivo, 'estanteria': est,
                          'token': token or ('rev-%s-%s-%s' % (cod, lote, fisico))},
                    headers=csrf_headers())


# ───────────────── qué ya se revisó ─────────────────

def test_sin_revisar_nada_ningun_lote_figura_como_revisado(app, db_clean):
    cod, est = _propio('sinrevisar')
    _sembrar(cod=cod, est=est)
    try:
        d = _lotes(_login(app), est=est)
        assert d['revisados_hoy'] == 0
        assert d['falta_revisar'] == 3
        assert not any(x.get('revisado_hoy') for x in d['lotes'])
    finally:
        _limpiar(cod)


def test_declarar_un_lote_lo_deja_marcado_como_REVISADO(app, db_clean):
    """Lo que resuelve *"no sé cuáles revisé"*: la marca sale del rastro, no de la pestaña."""
    cod, est = _propio('marcado')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        assert _declarar(c, 'L-B', 55, cod=cod, est=est).status_code == 200
        d = _lotes(c, est=est)
        por_lote = {x['lote']: x for x in d['lotes']}
        assert por_lote['L-B'].get('revisado_hoy') is True, por_lote['L-B']
        assert por_lote['L-B'].get('revisado_como') == 'ajustado'
        assert por_lote['L-B'].get('revisado_por') == 'sebastian'
        assert not por_lote['L-A'].get('revisado_hoy'), 'marcó uno que nadie tocó'
        assert d['revisados_hoy'] == 1 and d['falta_revisar'] == 2
    finally:
        _limpiar(cod)


def test_la_marca_SOBREVIVE_a_recargar_la_pantalla(app, db_clean):
    """Ésa es la razón de leerla del `audit_log` y no de un contador del navegador: al refrescar
    o volver al rato, el trabajo hecho seguía diciendo 0."""
    cod, est = _propio('sobrevive')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        _declarar(c, 'L-A', 100, cod=cod, est=est)
        otra_sesion = _login(app)          # como si abriera la pantalla de nuevo
        d = _lotes(otra_sesion, est=est)
        assert d['revisados_hoy'] == 1, \
            'la marca no sobrevivió a recargar: %r' % (d['revisados_hoy'],)
    finally:
        _limpiar(cod)


def test_declarar_que_NO_EXISTE_tambien_queda_revisado(app, db_clean):
    """El lote baja a cero y sale de la estantería: lo que importa es que el conteo deje de
    reclamarlo."""
    cod, est = _propio('noexiste')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        assert _declarar(c, 'L-A', 0, motivo='no lo encontre',
                         cod=cod, est=est).status_code == 200
        d = _lotes(c, est=est)
        assert 'L-A' not in [x['lote'] for x in d['lotes']], \
            'el lote quedó en cero y sigue en la lista de la estantería'
        assert d['falta_revisar'] == 2, d
    finally:
        _limpiar(cod)


def test_una_revision_VIEJA_no_cuenta_como_de_hoy(app, db_clean):
    """Un lote declarado hace un mes contaría como revisado hoy y el conteo mediría otra cosa
    (M174: un estado que caduca deja de significar lo que dice).

    El rastro viejo se INSERTA, no se actualiza: el `audit_log` es append-only por trigger y esa
    negativa es la invariante funcionando (M93).
    """
    cod, est = _propio('vieja')
    _sembrar(cod=cod, est=est)
    try:
        cn = _cn()
        try:
            cn.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, despues, "
                "  fecha) VALUES ('sebastian','CUADRE_INVENTARIO','movimientos',?,?,?, "
                "  '2026-01-15 10:00:00')",
                (cod, 'cuadre viejo', '{"codigo": "%s", "lote": "L-B", "fisico": 55}' % cod))
            cn.commit()
        finally:
            cn.close()
        d = _lotes(_login(app), est=est)
        assert d['revisados_hoy'] == 0, \
            'una revisión de enero cuenta como de hoy: %r' % (d['revisados_hoy'],)
        assert d['falta_revisar'] == 3
    finally:
        _limpiar(cod)


# ───────────────── la pantalla ─────────────────

def _pantalla(app):
    return pantalla_servida(_login(app), '/planta/cuadre')


def test_la_pantalla_tiene_el_boton_ACABE(app, db_clean):
    """*"Si digo acabé, que me diga: estos lotes, ¿dónde están?"*."""
    js = _pantalla(app)
    assert 'function acabe(' in js, 'no existe el cierre'
    assert 'acabe()' in js, 'la función existe y ningún botón la llama (M121)'
    assert 'no los viste' in js.lower() or 'no los viste' in js, \
        'el cierre no dice qué quedó sin ver'


def test_lo_pendiente_se_resuelve_DESDE_la_lista(app, db_clean):
    """Una lista que sólo se puede leer manda a empezar de nuevo, y ahí se abandona (M121)."""
    js = _pantalla(app)
    i = js.find('function acabe(')
    cuerpo = js[i:js.find('\nfunction ', i + 10)]
    for accion in ('igual(', 'noExiste(', 'guardar('):
        assert accion in cuerpo, 'desde el cierre no se puede %s' % accion


def test_declarar_saca_el_lote_de_la_lista_del_cierre(app, db_clean):
    """Si siguiera ahí, la persona no sabría cuál ya cerró y volvería a buscarlo (M129)."""
    js = _pantalla(app)
    assert 'function _sacarDePendientes' in js
    i = js.find('async function guardar(')
    cuerpo = js[i:js.find('\nasync function ', i + 10)]
    assert '_sacarDePendientes(' in cuerpo, 'guardar no achica la lista del cierre'
    assert 'revisado_hoy = true' in cuerpo, \
        'la fila no queda marcada hasta recargar: el contador diría que sigue pendiente (M5)'


def test_el_contador_cuenta_lo_REVISADO_HOY_no_lo_apretado_en_la_pestaña(app, db_clean):
    """Es el bug que Sebastián reportó: 0 de 54 con la estantería entera declarada."""
    js = _pantalla(app)
    i = js.find('function pintarProg(')
    cuerpo = js[i:js.find('\n// ', i)]
    assert 'revisado_hoy' in cuerpo, \
        'el contador sigue saliendo sólo de lo que se apretó en la pestaña'
    assert 'faltan' in cuerpo, 'no dice cuántos faltan, que es lo que se necesita saber'


def test_se_puede_ver_SOLO_lo_que_falta(app, db_clean):
    """Con 54 lotes, encontrar los 6 que faltan revisando la lista entera es el problema."""
    js = _pantalla(app)
    assert 'function verSoloFalta' in js and 'verSoloFalta()' in js


# ───────────────── el informe de cierre ─────────────────

def _informe(cli, **kw):
    _q = '&'.join('%s=%s' % (k, v) for k, v in kw.items())
    r = cli.get('/api/inventario/cuadre-informe' + ('?' + _q if _q else ''))
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('ok'), d
    return d


def _mios(d, clave, cod):
    return [x for x in d.get(clave, [])
            if str(x.get('codigo_mp') or '').upper() == cod.upper()]


def test_el_informe_separa_lo_que_se_ENCONTRO_de_lo_que_NO(app, db_clean):
    """Sebastián: *"que quede algo al final, como informe: lo que se encontró y lo que no, así
    les pido que me busquen esas específicas, para cerrar el inventario full"*."""
    cod, est = _propio('informe')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        _declarar(c, 'L-A', 100, cod=cod, est=est)      # coincide (hay 100)
        _declarar(c, 'L-B', 55, cod=cod, est=est)       # ajustado (habia 200)
        _declarar(c, 'L-C', 0, motivo='no aparece por ningun lado', cod=cod, est=est)
        d = _informe(c)
        assert len(_mios(d, 'coinciden', cod)) == 1, _mios(d, 'coinciden', cod)
        assert len(_mios(d, 'ajustados', cod)) == 1, _mios(d, 'ajustados', cod)
        assert len(_mios(d, 'no_esta', cod)) == 1, _mios(d, 'no_esta', cod)
        _aj = _mios(d, 'ajustados', cod)[0]
        assert _aj['sistema'] == 200 and _aj['fisico'] == 55, _aj
        assert _aj['ajuste'] == -145, 'no dice cuánto se perdió: %r' % (_aj,)
    finally:
        _limpiar(cod)


def test_lo_que_NO_se_encontro_sale_del_RASTRO_no_del_stock(app, db_clean):
    """Al declarar que no está, el lote queda en CERO y desaparece del inventario: del stock
    actual no se puede reconstruir, así que el `audit_log` es la única fuente para eso."""
    cod, est = _propio('rastro')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        _declarar(c, 'L-B', 0, motivo='se acabo', cod=cod, est=est)
        assert 'L-B' not in [x['lote'] for x in _lotes(c, est=est)['lotes']], \
            'el lote deberia haber salido del inventario'
        d = _informe(c)
        _n = _mios(d, 'no_esta', cod)
        assert _n, 'el lote que no apareció se perdió también del informe'
        assert _n[0]['sistema'] == 200, 'no dice cuánto se creía tener: %r' % (_n[0],)
        assert 'se acabo' in (_n[0].get('motivo') or ''), 'el informe no trae el motivo'
    finally:
        _limpiar(cod)


def test_la_lista_PARA_BUSCAR_junta_lo_no_encontrado_y_lo_sin_revisar(app, db_clean):
    """Es la lista que se reparte al equipo: los dos casos mandan a la MISMA acción -- ir a
    buscarlo -- y separarlos en dos pantallas obliga a mirar dos veces."""
    cod, est = _propio('buscar')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        _declarar(c, 'L-A', 0, motivo='no aparece', cod=cod, est=est)
        d = _informe(c)
        _lista = _mios(d, 'a_buscar', cod)
        assert len(_lista) == 3, 'esperaba el no-encontrado + los 2 sin revisar: %r' % (_lista,)
        motivos = sorted(set(x['motivo_lista'] for x in _lista))
        assert motivos == ['nadie lo revisó', 'no se encontró al contar'], motivos
    finally:
        _limpiar(cod)


def test_el_informe_NO_cierra_nada_por_su_cuenta(app, db_clean):
    """Dar un lote por perdido es un ajuste que alguien decide, no el efecto de pedir un reporte
    (M19). Pedirlo dos veces no puede mover un gramo."""
    cod, est = _propio('nocierra')
    _sembrar(cod=cod, est=est)
    try:
        c = _login(app)
        antes = [x['stock_sistema'] for x in _lotes(c, est=est)['lotes']]
        _informe(c)
        _informe(c)
        despues = [x['stock_sistema'] for x in _lotes(c, est=est)['lotes']]
        assert antes == despues, 'pedir el informe movió el inventario'
    finally:
        _limpiar(cod)


def test_el_rango_se_puede_ABRIR_porque_un_inventario_toma_dias(app, db_clean):
    """Con default hoy, un conteo de tres días diría que falta casi todo (M174)."""
    cod, est = _propio('rango')
    _sembrar(cod=cod, est=est)
    try:
        cn = _cn()
        try:
            cn.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, despues, "
                "  fecha) VALUES ('sebastian','CUADRE_INVENTARIO','movimientos',?,?,?, "
                "  '2026-08-19 14:00:00')",
                (cod, 'cuadre de anteayer',
                 '{"codigo": "' + cod + '", "lote": "L-A", "fisico": 90, "sistema": 100, '
                 '"ajuste": -10}'))
            cn.commit()
        finally:
            cn.close()
        c = _login(app)
        assert not _mios(_informe(c), 'ajustados', cod), 'con rango de hoy trae lo de anteayer'
        _m = _mios(_informe(c, desde='2026-08-18'), 'ajustados', cod)
        assert _m, 'abriendo el rango no aparece lo de anteayer'
        assert _m[0]['ajuste'] == -10
    finally:
        _limpiar(cod)


def test_la_pantalla_del_informe_existe_y_se_llega_desde_el_cuadre(app, db_clean):
    """Un informe al que nadie puede llegar no existe (M121)."""
    c = _login(app)
    r = c.get('/planta/cuadre-informe')
    assert r.status_code == 200, r.data[:200]
    html = r.get_data(as_text=True)
    assert 'ir a buscar' in html, 'la pantalla no arranca por la lista que hay que buscar'
    assert 'window.print()' in html, 'no se puede imprimir: esa lista se camina en papel'
    assert 'copiar()' in html, 'no se puede pasar la lista al equipo'
    assert '/planta/cuadre-informe' in pantalla_servida(c, '/planta/cuadre'), \
        'desde el cuadre no se llega al informe'


def test_el_informe_DECLARA_si_no_pudo_leer_el_rastro(app, db_clean):
    """*"No pude leer"* y *"no se revisó nada"* son cosas distintas (M100)."""
    import io as _io
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = _io.open(os.path.join(raiz, 'api', 'blueprints', 'inventario.py'),
                   encoding='utf-8').read()
    i = src.find('def inventario_cuadre_informe(')
    assert i != -1
    # Al CUERPO real, no a N caracteres: una ventana fija se queda corta apenas la funcion
    # crece, y el guard deja de medir sin avisar (M229).
    j = src.find(chr(10) + '@bp.route', i)
    cuerpo = src[i:j if j > i else len(src)]
    assert cuerpo.count('lectura_fallo = True') >= 2, 'algún camino se cae en silencio'
    assert "'lectura_fallo': lectura_fallo" in cuerpo, 'no lo publica'
