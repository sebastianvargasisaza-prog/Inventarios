"""El rótulo de pesaje reparte por LOTE y no inventa cantidad (30-jul).

Sebastián, a punto de producir SUERO MULTIPÉPTIDOS de 45 kg: *"del palmitoyl tripéptido-4 hay
sólo uno, con menor cantidad de la que se requiere, y cuando le doy rótulos de pesaje me saca
ESE con la cantidad necesaria a pesar de que no hay. Debería tomar el lote más viejo con la
cantidad que hay + otro rótulo con el otro lote que tenga lo que falta, porque así estaría
registrando lo que no es"*.

El rótulo resolvía UN lote (el más próximo a vencer con stock) y le imprimía el peso teórico
COMPLETO sin mirar si alcanzaba. Es un registro regulado (PRD-PRO-001-F08) documentando un lote
y una cantidad que no existen -- y el operario terminaba completando de otro lote SIN rótulo.

El reparto ahora sale de `_distribuir_fefo`, **el mismo que usa el descuento de producción**: si
fueran dos cuentas distintas, el papel y el kardex divergirían (M1/M5).
"""
from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ SUERO REPARTO'
MP = 'MP-ZZREPARTO'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app, lotes):
    """Fórmula con UNA MP al 1% + los lotes que se le pasen [(lote, cant, vencimiento)]."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM movimientos WHERE material_id=?", (MP,))
        cu.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        cu.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        cu.execute(
            "INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
            "VALUES (?,?,?,1) ON CONFLICT (codigo_mp) DO UPDATE SET activo=1",
            (MP, 'PALMITOYL TRIPEPTIDE-4 TEST', 'Peptido de prueba reparto'))
        cu.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g) VALUES (?,1000)",
                   (PROD,))
        cu.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                   "porcentaje) VALUES (?,?,?,?)", (PROD, MP, 'Peptido de prueba reparto', 1.0))
        for lote, cant, venc in lotes:
            cu.execute(
                "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
                "lote, fecha_vencimiento, estado_lote, estanteria, posicion) "
                "VALUES (?,?,?, 'Entrada','2026-07-01T08:00:00',?,?, 'VIGENTE','A1','3')",
                (MP, 'Peptido de prueba reparto', cant, lote, venc))
        conn.commit()


def _rotulos(app, kg):
    r = _login(app).get('/rotulos/%s/%s' % (PROD.replace(' ', '%20'), kg))
    assert r.status_code == 200, r.data[:300]
    return r.data.decode('utf-8', 'replace')


# ══ el caso de Sebastián ════════════════════════════════════════════════════════

def test_un_solo_lote_con_MENOS_de_lo_necesario_no_finge_la_cantidad(app, db_clean):
    """45 kg al 1% = 450 g. El único lote tiene 120 g: el rótulo no puede decir 450."""
    _sembrar(app, [('LOTE-VIEJO', 120, '2027-06-30')])
    body = _rotulos(app, 45)
    assert 'LOTE-VIEJO' in body
    assert '120' in body, 'no imprimió la cantidad REAL del lote'
    assert 'NO HAY STOCK' in body, 'no avisó que falta: estaría documentando lo que no es'
    assert '330' in body, 'no dijo cuánto falta (450 - 120 = 330 g)'


def test_reparte_entre_DOS_lotes_el_mas_proximo_a_vencer_primero(app, db_clean):
    """Lo que pidió: el viejo con lo que tiene + otro rótulo con lo que falta."""
    _sembrar(app, [('LOTE-VIEJO', 120, '2027-01-31'),
                   ('LOTE-NUEVO', 900, '2028-12-31')])
    body = _rotulos(app, 45)          # necesita 450 g
    assert 'LOTE-VIEJO' in body and 'LOTE-NUEVO' in body, 'no repartió entre lotes'
    assert 'Parte 1 de 2' in body and 'Parte 2 de 2' in body, 'no numeró las partes'
    assert 'NO HAY STOCK' not in body, 'entre los dos alcanza: no debería avisar faltante'
    # el viejo aporta sus 120 y el nuevo los 330 restantes
    assert '120' in body and '330' in body, 'el reparto no es 120 + 330'


def test_un_lote_que_alcanza_sale_como_siempre(app, db_clean):
    """Dientes del otro lado: si un lote cubre todo, es UN rótulo y sin avisos."""
    _sembrar(app, [('LOTE-UNICO', 5000, '2028-01-31')])
    body = _rotulos(app, 45)
    assert 'LOTE-UNICO' in body
    assert 'Parte 1 de' not in body, 'partió algo que no hacía falta partir'
    assert 'NO HAY STOCK' not in body


def test_el_reparto_del_rotulo_es_el_MISMO_que_el_del_descuento(app, db_clean):
    """Si el papel y el kardex usaran dos cuentas distintas, divergirían (M1). Se compara
    contra el distribuidor canónico que usa la producción."""
    _sembrar(app, [('L1', 200, '2027-01-31'), ('L2', 500, '2028-05-31')])
    from database import get_db
    with app.app_context():
        from blueprints.programacion import _distribuir_fefo
        partes = _distribuir_fefo(get_db().cursor(), MP, 450.0)
    reales = [(str(p['lote']), round(float(p['cantidad']), 2))
              for p in partes if not p.get('sin_lote')]
    body = _rotulos(app, 45)
    for lote, cant in reales:
        assert lote in body, 'el rótulo no trae el lote %s que el descuento SÍ va a usar' % lote
        assert ('%g' % cant).replace('.', ',') in body or str(int(cant)) in body, (
            'la cantidad de %s no coincide con la del descuento (%s)' % (lote, cant))


def test_avisa_arriba_lo_que_falta_antes_de_bajar_a_bodega(app, db_clean):
    """*"además de irles diciendo"*: el aviso va en la pantalla, no impreso."""
    _sembrar(app, [('LOTE-CORTO', 50, '2027-06-30')])
    body = _rotulos(app, 45)
    assert 'no-print' in body, 'el aviso debería ser de pantalla, no del papel'
    assert 'No hay stock suficiente' in body
    assert 'PALMITOYL' in body.upper() or 'Peptido de prueba' in body
