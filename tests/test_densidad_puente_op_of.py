"""La densidad del granel es el puente fabricación → envasado, y no tenía por dónde entrar (26-jul).

Comparando la pantalla de EOS contra MyBatch, Sebastián notó que la cabecera del legajo mostraba
`Densidad: -` y `Área/Línea: -`. Al revisarlo apareció que **no faltaba la función: faltaba la
puerta**. `ebr_ejecuciones.densidad_g_ml` existe, el endpoint de cierre la acepta y calcula con
ella los mL envasables… pero **ninguna pantalla la pedía nunca**, así que el dato no tenía forma
de entrar y siempre llegaba vacío al envasado.

Es el mismo patrón que la foto del envase: construido en el modelo, sin camino en la interfaz. Un
campo que sólo se puede llenar por API es un campo que en la práctica está vacío.

Para qué sirve: MyBatch convierte 17.000 g de granel a 0,916 g/mL en los 13.658,95 mL que
realmente se envasan. Sin densidad, envasado no sabe cuánto volumen tiene para repartir entre
presentaciones.
"""
from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ DENSIDAD PRODUCTO'
LOTE = 'L-ZZ-DENS'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _sembrar(app):
    """Un EBR de fabricación en proceso, listo para cerrar. Limpia ANTES (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote LIKE ?",
                             (LOTE + '%',)).fetchall():
            cur.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=?", (r[0],))
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
        for r in cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                             (PROD,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                    "creado_por) VALUES (?,1,'aprobado',17000,'test')", (PROD,))
        mbr = cur.lastrowid
        cur.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, fase, "
                    "estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                    "VALUES (?,1,?, 'fabricacion','en_proceso','test','2026-07-26T09:00:00',17000)",
                    (mbr, LOTE))
        ebr = cur.lastrowid
        conn.commit()
        return ebr


def test_la_densidad_convierte_los_gramos_en_ml_envasables(app):
    """El caso de MyBatch: 17.000 g a 0,916 g/mL = 18.558 mL. Sin este dato, envasado no sabe
    cuánto volumen tiene para repartir entre presentaciones."""
    from database import get_db
    ebr = _sembrar(app)
    c = _admin(app)
    r = c.post('/api/brd/ebr/%d/completar' % ebr, headers=_h(c),
               json={'cantidad_real_g': 17000, 'densidad_g_ml': 0.916})
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        row = get_db().execute(
            "SELECT densidad_g_ml, ml_envasable FROM ebr_ejecuciones WHERE id=?", (ebr,)).fetchone()
    assert float(row[0]) == 0.916, 'no guardó la densidad: %s' % (row[0],)
    assert abs(float(row[1]) - 18558.95) < 1, 'mL envasables mal calculados: %s' % (row[1],)


def test_sin_densidad_el_cierre_igual_funciona(app):
    """Es opcional a propósito: si no se midió, el lote se cierra igual. Bloquear el cierre por un
    dato que quizá nadie tomó dejaría la producción trabada."""
    from database import get_db
    ebr = _sembrar(app)
    c = _admin(app)
    r = c.post('/api/brd/ebr/%d/completar' % ebr, headers=_h(c),
               json={'cantidad_real_g': 17000})
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        row = get_db().execute(
            "SELECT densidad_g_ml, ml_envasable FROM ebr_ejecuciones WHERE id=?", (ebr,)).fetchone()
    assert row[0] is None and row[1] is None, 'inventó una densidad: %s' % (row,)


def test_una_densidad_invalida_no_rompe_el_cierre(app):
    """Un cero o un texto no pueden tumbar el cierre de una producción real ni provocar una
    división por cero."""
    ebr = _sembrar(app)
    c = _admin(app)
    r = c.post('/api/brd/ebr/%d/completar' % ebr, headers=_h(c),
               json={'cantidad_real_g': 17000, 'densidad_g_ml': 'abc'})
    assert r.status_code == 200, r.data[:300]


def test_la_pantalla_de_cierre_pide_la_densidad(app):
    """El bug real no era que faltara el campo, era que NINGUNA pantalla lo pedía: un dato que
    sólo se puede cargar por API está vacío en la práctica. Si alguien quita el diálogo, la
    densidad vuelve a no tener puerta de entrada."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'templates_py', 'dashboard_html.py'),
                encoding='utf-8').read()
    i = s.find('function ebrTerminarLote')
    assert i > 0, 'no existe ebrTerminarLote'
    cuerpo = s[i:i + 2200]
    assert 'densidad_g_ml' in cuerpo, (
        'el cierre de producción ya no pide la densidad · sin eso el legajo de envasado la '
        'muestra siempre vacía')


def test_el_legajo_hereda_el_area_del_lote_programado(app):
    """La cabecera mostraba "Área/Línea: -" siempre. No faltaba la columna (existe desde la mig
    219) ni la vista (ya la pinta): **ninguno de los 8 sitios que crean un EBR la pasaba**. Ahora
    se hereda del lote programado, que es quien sabe en qué área se produce.

    Se deriva dentro del helper y no en cada caller, porque 8 copias de la misma regla vuelven a
    divergir (M1).
    """
    from blueprints.brd import crear_ebr_desde_mbr
    from database import get_db
    PRODA, LOTEA = 'ZZ AREA PRODUCTO', 'L-ZZ-AREA'
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote LIKE ?",
                             (LOTEA + '%',)).fetchall():
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
        for r in cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                             (PRODA,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
        # El fixture se arma en el ORDEN REAL del flujo: draft -> pasos -> aprobar. Insertar los
        # pasos con el MBR ya aprobado lo rechaza el disparador de inmutabilidad, y ese rechazo es
        # la invariante funcionando, no un bug del test (M93).
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                    "creado_por) VALUES (?,1,'draft',10000,'test')", (PRODA,))
        mbr = cur.lastrowid
        cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, descripcion, tipo_paso, fase) "
                    "VALUES (?,1,'Mezclar','mezclado','fabricacion')", (mbr,))
        cur.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr,))
        ar = cur.execute("SELECT id, codigo FROM areas_planta ORDER BY id LIMIT 1").fetchone()
        assert ar, 'no hay áreas de planta sembradas'
        cur.execute("INSERT INTO produccion_programada (producto, cantidad_kg, fecha_programada, "
                    "estado, origen, area_id) VALUES (?,10,'2026-07-27','pendiente','eos_plan',?)",
                    (PRODA, ar[0]))
        pid = cur.lastrowid
        conn.commit()
        res = crear_ebr_desde_mbr(cur, producto_nombre=PRODA, lote=LOTEA,
                                  produccion_id=pid, usuario='test')
        conn.commit()
        # el helper devuelve la clave 'id', no 'ebr_id' · leer el return antes de indexarlo (M94)
        assert res and res.get('id'), res
        got = cur.execute("SELECT COALESCE(area_codigo,'') FROM ebr_ejecuciones WHERE id=?",
                          (res['id'],)).fetchone()[0]
    assert got == ar[1], 'el legajo no heredó el área del lote: "%s" (esperaba "%s")' % (got, ar[1])
