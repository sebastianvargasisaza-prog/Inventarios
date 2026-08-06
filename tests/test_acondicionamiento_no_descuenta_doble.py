# -*- coding: utf-8 -*-
"""El cierre de acondicionamiento no vuelve a descontar lo que envasado ya consumió.

Tercera instancia de M162, encontrada revisando Planta: **por cada cosa que se descuenta, contá
cuántos endpoints la descuentan y contra qué marca**. Acá había TRES caminos y sólo dos usaban
el libro mayor:

| camino | qué descuenta | contra qué marca |
|---|---|---|
| `cerrar-envasado` | envase+tapa+caja de `producto_presentaciones` | `produccion_checklist.consumido_at` ✓ |
| cierre del Kanban | lo del checklist | `consumido_at` ✓ |
| `cerrar-acondicionamiento` | **lo que teclea el operario** | ninguna ✗ |

El tercero es el más expuesto justamente porque los códigos los escribe una persona: si lista el
frasco o la caja que envasado ya consumió, sale del kardex DOS VECES. Y un doble descuento no da
síntoma -- el kardex simplemente dice menos de lo que hay, y se descubre contando físico.

El arreglo no es un cuarto candado: es que el tercer camino use el libro que ya existe.
"""
import uuid

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'ZZACOND-FRASCO'


def _cli(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sembrar(app, consumido):
    """Deja una producción con su checklist y un EBR de acondicionamiento listo para cerrar.

    `consumido` decide si el checklist ya marcó ese envase como salido -- que es exactamente la
    condición que separa el descuento legítimo del doble.
    """
    from database import get_db
    lote = 'ZZACOND-' + uuid.uuid4().hex[:6].upper()
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        # Limpieza en orden HIJAS -> quien la apunta -> MADRE: borrar el maestro con sus
        # movimientos vivos revienta la FK, y entre tests de este mismo archivo los hay (M119).
        c.execute("DELETE FROM movimientos_mee WHERE UPPER(TRIM(mee_codigo))=?", (COD,))
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZACOND-%'")
        c.execute("DELETE FROM produccion_checklist WHERE mee_codigo_asignado=?", (COD,))
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", ('ZZ ACOND PRODUCTO',))
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
                  "VALUES (?,?,?,?) ON CONFLICT (codigo) DO NOTHING",
                  (COD, 'Frasco de prueba', 0, 'Activo'))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, estado, "
                  " cantidad_kg, origen) VALUES (?,?,?,?,?)",
                  ('ZZ ACOND PRODUCTO', '2026-08-04', 'en_proceso', 10, 'eos_plan'))
        pid = c.lastrowid
        c.execute("INSERT INTO produccion_checklist (produccion_id, producto_nombre, "
                  " fecha_planeada, item_tipo, descripcion, mee_codigo_asignado, consumido_at) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (pid, 'ZZ ACOND PRODUCTO', '2026-08-04', 'envase', 'Frasco',
                   COD, '2026-08-04T10:00:00' if consumido else ''))
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", ('ZZ ACOND PRODUCTO',))
        mbr = c.lastrowid
        # El legajo lleva sufijo de fase en `lote` (UNIQUE) y el lote FISICO en `lote_codigo` (M10).
        c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                  " fase, estado, produccion_id, iniciado_por, iniciado_at_utc, "
                  " cantidad_objetivo_g) VALUES (?,1,?,?,?,?,?,?,?,?)",
                  (mbr, lote + '-OA', lote, 'acondicionamiento', 'en_proceso', pid,
                   'zz', '2026-08-04T10:00:00', 10000))
        ebr = c.lastrowid
        conn.commit()
    return ebr, lote


def _stock(app):
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT COALESCE(SUM(CASE WHEN LOWER(tipo)='salida' THEN cantidad ELSE 0 END),0) "
            "FROM movimientos_mee WHERE UPPER(TRIM(mee_codigo))=?", (COD,)).fetchone()
        return float(r[0] or 0)


def _cerrar(cli, ebr, cant=100):
    return cli.post('/api/brd/ebr/%d/cerrar-acondicionamiento' % ebr, headers=csrf_headers(),
                    json={'materiales': [{'codigo': COD, 'cantidad': cant}]})


def test_NO_descuenta_lo_que_envasado_ya_consumio(app, db_clean):
    """El caso que producía el doble descuento."""
    ebr, _ = _sembrar(app, consumido=True)
    antes = _stock(app)
    r = _cerrar(_cli(app), ebr)
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert _stock(app) == antes, 'volvió a descontar un envase que ya había salido del kardex'
    motivos = [s.get('motivo', '') for s in (d.get('saltados') or [])]
    assert any('ya consumido' in m for m in motivos), (
        'lo saltó sin decir por qué · un descuento que no ocurre y no se declara se ve igual '
        'que uno que sí (M124) · %s' % d)


def test_SI_descuenta_lo_que_todavia_no_salio(app, db_clean):
    """El borde que hay que probar para que el guard no sea un muro: si el envase NO se consumió
    todavía, el acondicionamiento tiene que descontarlo igual que siempre."""
    ebr, _ = _sembrar(app, consumido=False)
    antes = _stock(app)
    r = _cerrar(_cli(app), ebr)
    assert r.status_code == 200, r.data[:300]
    assert _stock(app) == antes + 100, 'dejó de descontar un envase que sí había que descontar'


def test_lo_RECLAMA_en_el_libro_para_que_el_otro_cierre_lo_respete(app, db_clean):
    """Saltar no alcanza: si este cierre descuenta y no MARCA, el cierre de envasado lo vuelve a
    descontar. La coordinación es en los dos sentidos."""
    from database import get_db
    ebr, _ = _sembrar(app, consumido=False)
    r = _cerrar(_cli(app), ebr)
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        marcas = get_db().execute(
            "SELECT COALESCE(consumido_at,'') FROM produccion_checklist "
            " WHERE mee_codigo_asignado=?", (COD,)).fetchall()
    assert any(str(m[0]).strip() for m in marcas), (
        'descontó sin reclamar el libro mayor · el otro cierre lo descontaría otra vez')


def test_DECLARA_cuando_no_pudo_coordinar(app, db_clean):
    """Un EBR sin producción asociada no tiene libro mayor que consultar. Se sigue descontando
    (que un envase no salga es peor que arriesgar el doble) pero la respuesta lo DICE."""
    from database import get_db
    lote = 'ZZACOND-' + uuid.uuid4().hex[:6].upper()
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        # Limpieza en orden HIJAS -> quien la apunta -> MADRE: borrar el maestro con sus
        # movimientos vivos revienta la FK, y entre tests de este mismo archivo los hay (M119).
        c.execute("DELETE FROM movimientos_mee WHERE UPPER(TRIM(mee_codigo))=?", (COD,))
        c.execute("DELETE FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote) LIKE 'ZZACOND-%'")
        c.execute("DELETE FROM produccion_checklist WHERE mee_codigo_asignado=?", (COD,))
        c.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", ('ZZ ACOND PRODUCTO',))
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
                  "VALUES (?,?,?,?) ON CONFLICT (codigo) DO NOTHING",
                  (COD, 'Frasco de prueba', 0, 'Activo'))
        c.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                  " creado_por) VALUES (?, 1, 'aprobado', 10000, 'zz')", ('ZZ ACOND PRODUCTO',))
        mbr = c.lastrowid
        # El legajo lleva sufijo de fase en `lote` (UNIQUE) y el lote FISICO en `lote_codigo` (M10).
        c.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                  " fase, estado, produccion_id, iniciado_por, iniciado_at_utc, "
                  " cantidad_objetivo_g) VALUES (?,1,?,?,?,?,?,?,?,?)",
                  (mbr, lote + '-OA', lote, 'acondicionamiento', 'en_proceso', 0,
                   'zz', '2026-08-04T10:00:00', 10000))
        ebr = c.lastrowid
        conn.commit()
    r = _cerrar(_cli(app), ebr)
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get('sin_libro_mayor') is True, (
        'no declaró que descontó sin poder coordinar · si mañana hay un descuadre, nadie puede '
        'saber por qué')
