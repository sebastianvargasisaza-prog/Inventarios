"""El vigía de materias primas · el detector que faltaba (2-ago).

La colisión de códigos del 9-jul estuvo TRES SEMANAS a la vista y nadie la vio: un kardex con un
descuento de más se ve igual que uno sano. Todo este frente se verificaba abriendo un endpoint,
o sea sólo cuando alguien se acordaba. Lo que faltaba no era el arreglo, era el detector (M127).

Las cinco firmas GRAVES tienen que dar cero. Estos tests prueban que **muerden**: si no fallan
al sembrar el defecto, el vigía es decorativo (M104 · una regla que nadie verifica es una
intención, no un blindaje).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

URL = '/api/programacion/salud-materias-primas'
PROD = 'QA SALUD MP PRODUCTO'
COD_OK = 'MPQASALUD1'
COD_MUERTO = 'MPQASALUDNOEXISTE'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _cli(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    """M103: limpiar ANTES de sembrar · la BD de tests es compartida y en PG sobrevive."""
    db = _db()
    try:
        db.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
        db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        db.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD_OK,))
        db.execute("DELETE FROM movimientos WHERE material_id IN (?,?,?,?)",
                   (COD_OK, ' ' + COD_OK, 'MPQANEG1', 'MPQAFV1'))
        db.commit()
    finally:
        db.close()


def _sembrar_formula(pct_total=100.0, codigo=COD_OK, activo=1):
    db = _db()
    try:
        db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                   "VALUES (?,?,?,1)", (COD_OK, 'QA Salud MP', 'QA SALUD INCI'))
        db.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, activo) "
                   "VALUES (?,1000,?)", (PROD, activo))
        db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
                   "VALUES (?,?,?,?)", (PROD, codigo, 'QA Salud MP', pct_total))
        db.commit()
    finally:
        db.close()


def _hall(js, clave):
    return js['hallazgos'].get(clave) or []


def test_una_formula_sana_no_dispara_nada(app):
    _limpiar(); _sembrar_formula(100.0)
    js = _cli(app).get(URL).get_json()
    assert not [h for h in _hall(js, 'formula_no_suma_100') if h['producto'] == PROD]
    assert not [h for h in _hall(js, 'formula_apunta_a_codigo_muerto') if h['producto'] == PROD]
    assert js['checks_fallidos'] == [], 'un chequeo caído se DECLARA, no se traga'


def test_caza_la_formula_que_dejo_de_sumar_100(app):
    """Es el control de integridad que trajo el batch record. Hasta hoy sólo corría si alguien
    abría el endpoint a mano."""
    _limpiar(); _sembrar_formula(77.5)
    js = _cli(app).get(URL).get_json()
    malas = [h for h in _hall(js, 'formula_no_suma_100') if h['producto'] == PROD]
    assert len(malas) == 1 and malas[0]['suma_pct'] == 77.5
    assert js['ok'] is False and js['n_graves'] >= 1


def test_caza_el_item_cuyo_codigo_DESACTIVARON_despues(app):
    """Un ítem apuntando a un código muerto NO descuenta: la producción se lleva el material del
    estante y el sistema no se entera.

    El trigger de `formula_items` (mig 38) ya impide APUNTAR a un código inexistente o inactivo,
    tanto al insertar como al actualizar -- se verifica abajo. Pero no puede hacer nada cuando el
    código se desactiva DESPUÉS, con la fórmula ya escrita: ése es el hueco exacto que este
    chequeo tapa, y por eso el test lo reproduce por ese camino y no inventando un INSERT que la
    base nunca aceptaría.
    """
    _limpiar(); _sembrar_formula(100.0)
    db = _db()
    try:
        db.execute("UPDATE maestro_mps SET activo=0 WHERE codigo_mp=?", (COD_OK,))
        db.commit()
    finally:
        db.close()
    js = _cli(app).get(URL).get_json()
    malos = [h for h in _hall(js, 'formula_apunta_a_codigo_muerto') if h['producto'] == PROD]
    assert len(malos) == 1 and malos[0]['codigo'] == COD_OK
    assert js['ok'] is False


def test_el_trigger_sigue_impidiendo_apuntar_a_un_codigo_muerto(app):
    """La primera línea de defensa no se puede aflojar: el vigía es el respaldo, no el reemplazo."""
    _limpiar(); _sembrar_formula(100.0)
    db = _db()
    try:
        try:
            db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                       "porcentaje) VALUES (?,?,?,?)", (PROD, COD_MUERTO, 'inventado', 1.0))
            db.commit()
            assert False, 'el trigger tenía que rechazar un material_id que no está en el maestro'
        except sqlite3.IntegrityError:
            pass
    finally:
        db.close()


def test_no_mira_las_formulas_inactivas(app):
    """Descontinuar una fórmula es una decisión, no un defecto: si el vigía la reportara, la
    alerta se llenaría de ruido y dejaría de mirarse."""
    _limpiar(); _sembrar_formula(50.0, activo=0)
    js = _cli(app).get(URL).get_json()
    assert not [h for h in _hall(js, 'formula_no_suma_100') if h['producto'] == PROD]


def test_caza_el_codigo_con_espacios_pegados(app):
    """Un tabulador pegado a un código es una CLAVE DISTINTA: el stock queda invisible y no da
    ni un error. Así se perdieron 1000 envases del kardex (M100)."""
    _limpiar(); _sembrar_formula(100.0)
    db = _db()
    try:
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                   "VALUES (?,?,?,'Entrada','2026-08-01 08:00:00','L-QA','VIGENTE')",
                   (' ' + COD_OK, 'QA Salud MP', 10.0))
        db.commit()
    finally:
        db.close()
    js = _cli(app).get(URL).get_json()
    assert [h for h in _hall(js, 'codigo_con_espacios_en_kardex')
            if h['codigo_crudo'].strip() == COD_OK]


def test_caza_el_lote_en_negativo(app):
    _limpiar(); _sembrar_formula(100.0)
    db = _db()
    try:
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                   "VALUES ('MPQANEG1','QA Neg',5.0,'Entrada','2026-08-01 08:00:00','L-NEG','VIGENTE')")
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
                   "VALUES ('MPQANEG1','QA Neg',30.0,'Salida','2026-08-01 09:00:00','L-NEG','VIGENTE')")
        db.commit()
    finally:
        db.close()
    js = _cli(app).get(URL).get_json()
    negs = [h for h in _hall(js, 'stock_negativo_por_lote') if h['codigo'] == 'MPQANEG1']
    assert len(negs) == 1 and negs[0]['stock_g'] == -25.0


def test_caza_la_fecha_de_vencimiento_que_el_motor_no_puede_leer(app):
    """El bug del 21-ago, que no daba UN solo síntoma: con `26-Dic-2026` en vez de ISO,
    `date(...)` devuelve NULL, el lote se cae del stock distribuible -- producción dice "no hay"
    con el material en la estantería -- y el cron de vencidos tampoco lo puede marcar, así que
    un lote vencido así se queda VIGENTE para siempre.

    Se prueba que el detector DISTINGUE: sembrar el bug, verlo, dejar la fecha en ISO, verlo
    desaparecer (M172 · un vigía que no distingue no sirve)."""
    _limpiar(); _sembrar_formula(100.0)
    db = _db()
    try:
        db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,"
                   "lote,fecha_vencimiento,estado_lote) VALUES "
                   "('MPQAFV1','QA FechaVenc',1000.0,'Entrada','2026-08-01 08:00:00',"
                   "'L-FV','26-Dic-2027','VIGENTE')")
        db.commit()
    finally:
        db.close()
    js = _cli(app).get(URL).get_json()
    hall = [h for h in _hall(js, 'fecha_vencimiento_que_el_motor_no_lee')
            if h['codigo'] == 'MPQAFV1']
    assert len(hall) == 1, "no cazó la fecha en texto: %r" % (hall,)
    assert hall[0]['sugerida'] == '2027-12-26',         "no dice cuál sería la fecha correcta: %r" % (hall[0],)
    # y es GRAVE: un lote que se cae del stock sin avisar no puede ser informativo
    assert 'fecha_vencimiento_que_el_motor_no_lee' in (js.get('graves') or []),         "la firma quedó fuera de las graves, así que el cron no avisaría"

    # Con la fecha en ISO, el vigía se calla.
    db = _db()
    try:
        db.execute("UPDATE movimientos SET fecha_vencimiento='2027-12-26' "
                   "WHERE material_id='MPQAFV1'")
        db.commit()
    finally:
        db.close()
    js2 = _cli(app).get(URL).get_json()
    assert not [h for h in _hall(js2, 'fecha_vencimiento_que_el_motor_no_lee')
                if h['codigo'] == 'MPQAFV1'], "sigue reportando una fecha que ya está bien"
    _limpiar()


def test_la_colision_a_medio_corregir_usa_el_MISMO_calculo_que_la_devolucion(app):
    """No una copia: si el vigía tuviera su propia versión, las dos divergirían en silencio (M1)."""
    import inspect
    try:
        from api.blueprints.programacion import _salud_mp_core
    except Exception:
        from blueprints.programacion import _salud_mp_core
    src = inspect.getsource(_salud_mp_core)
    assert '_plan_colisiones_net_zero' in src


def test_el_cron_esta_registrado_y_apunta_a_la_funcion_real(app):
    """Una feature que nadie dispara no existe: el job tiene que estar en la tabla del cron y
    el nombre tiene que resolver a una función de verdad."""
    try:
        from api.blueprints import auto_plan_jobs as J
    except Exception:
        from blueprints import auto_plan_jobs as J
    assert callable(getattr(J, 'job_salud_materias_primas', None))
    import inspect
    src = inspect.getsource(J)
    assert "'salud_mp'" in src and "'job_salud_materias_primas'" in src


def test_solo_autenticado(app):
    assert app.test_client().get(URL).status_code == 401
