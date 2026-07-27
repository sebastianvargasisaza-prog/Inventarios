"""Lo que se COMPRA del envase tiene que ser lo que se DESCUENTA (26-jul).

Sebastián pidió recorrer la cadena del envase. Medido en producción apareció esto: de las **43
presentaciones activas, las 43 estaban sin tapa** configurada, así que al cerrar un envasado el
sistema **nunca descontó una tapa, en ningún producto**. Se compraban, entraban a bodega, se
usaban en el piso, y no salían jamás del kardex.

La causa era que había DOS tablas para lo mismo y no se hablaban:
  · `mee_partes` (frasco → gotero/tapa) la lee el ABASTECIMIENTO para comprar.
  · `producto_presentaciones.tapa_codigo/caja_codigo` la lee el ENVASADO para descontar.

Ahora las dos puntas leen `mee_partes`, así que cargar las partes de un frasco sincroniza compra y
descuento de una sola vez. Este archivo existe para que no vuelvan a separarse.

Es el patrón M55/M73 por tercera vez; por eso el test, y no sólo el arreglo.
"""
from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ PARTES PRODUCTO'
ENV = 'ZZ-FR-30'
GOTERO = 'ZZ-GOT-01'
TAPA = 'ZZ-TAP-01'
LOTE = 'L-ZZ-PARTES'


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


def _sembrar(app, con_tapa_en_presentacion=False):
    """Un frasco con gotero + tapa en `mee_partes`, y un legajo de envasado listo para cerrar.

    Limpia ANTES y usa códigos fijos: la BD de tests es compartida y en PG persiste (M103).
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote LIKE ?",
                             (LOTE + '%',)).fetchall():
            cur.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id=?", (r[0],))
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
        for r in cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                             (PROD,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
        cur.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cur.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV,))
        cur.execute("DELETE FROM movimientos_mee WHERE mee_codigo IN (?,?,?)", (ENV, GOTERO, TAPA))
        for cod, desc in ((ENV, 'Frasco 30 ml'), (GOTERO, 'Gotero'), (TAPA, 'Tapa')):
            cur.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
            cur.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, estado, "
                        "stock_actual, stock_minimo) VALUES (?,?,'Frasco','Activo',0,0)",
                        (cod, desc))
            # stock real por kardex (canónico · M26), no por el cache
            cur.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                        "responsable, observaciones) VALUES (?,'Entrada',1000,'und','test','seed')",
                        (cod,))
        # el frasco arrastra gotero + tapa
        for parte, desc in ((GOTERO, 'gotero'), (TAPA, 'tapa')):
            cur.execute("INSERT INTO mee_partes (mee_codigo, parte_codigo, descripcion, cantidad, "
                        "creado_at) VALUES (?,?,?,1,'2026-07-26')", (ENV, parte, desc))
        cur.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                    "etiqueta, volumen_ml, envase_codigo, tapa_codigo, activo) "
                    "VALUES (?,?,?,30,?,?,1)",
                    (PROD, 'V30', '30 ml', ENV, (TAPA if con_tapa_en_presentacion else '')))
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                    "creado_por) VALUES (?,1,'aprobado',10000,'test')", (PROD,))
        mbr = cur.lastrowid
        cur.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                    "fase, estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                    "VALUES (?,1,?,?,'envasado','en_proceso','test','2026-07-26T09:00:00',10000)",
                    (mbr, LOTE + '-OF', LOTE))
        ebr = cur.lastrowid
        cur.execute("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
                    "volumen_ml, unidades, registrado_por, registrado_at_utc) "
                    "VALUES (?, 'V30', '30 ml', 30, 100, 'test', '2026-07-26T10:00:00')", (ebr,))
        conn.commit()
        return ebr


def _salidas(app):
    """Cuánto salió del kardex de cada código, por el cierre del envasado."""
    from database import get_db
    with app.app_context():
        out = {}
        for r in get_db().execute(
            "SELECT mee_codigo, SUM(cantidad) FROM movimientos_mee "
            "WHERE tipo='Salida' AND mee_codigo IN (?,?,?) GROUP BY mee_codigo",
                (ENV, GOTERO, TAPA)).fetchall():
            out[r[0]] = float(r[1] or 0)
        return out


def test_al_cerrar_el_envasado_se_descuentan_las_partes_del_frasco(app):
    """El corazón del arreglo: 100 frascos → 100 goteros y 100 tapas salen del kardex.

    Antes salía SOLO el frasco: las tapas se compraban y no bajaban nunca.
    """
    ebr = _sembrar(app)
    c = _admin(app)
    r = c.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, headers=_h(c), json={})
    assert r.status_code == 200, r.data[:300]
    s = _salidas(app)
    assert s.get(ENV) == 100, 'el frasco: %s' % s
    assert s.get(GOTERO) == 100, 'el GOTERO no se descontó · %s' % s
    assert s.get(TAPA) == 100, 'la TAPA no se descontó · %s' % s


def test_no_descuenta_dos_veces_la_misma_parte(app):
    """Con dientes: si la presentación YA declara la tapa, la tapa baja UNA vez, no dos.

    Sin este guard, los productos que sí tienen `tapa_codigo` cargado empezarían a descontar el
    doble el día que alguien cargue esa misma tapa en `mee_partes`.
    """
    ebr = _sembrar(app, con_tapa_en_presentacion=True)
    c = _admin(app)
    r = c.post('/api/brd/ebr/%d/cerrar-envasado' % ebr, headers=_h(c), json={})
    assert r.status_code == 200, r.data[:300]
    s = _salidas(app)
    assert s.get(TAPA) == 100, 'la tapa se descontó %s veces las unidades · %s' % (
        (s.get(TAPA) or 0) / 100.0, s)
    assert s.get(GOTERO) == 100, s


def test_el_candado_avisa_si_falta_una_parte(app):
    """"Envases listos" miraba sólo el frasco: se podía arrancar un envasado sin goteros y nadie
    decía nada. El operario se enteraba en el puesto."""
    from blueprints.programacion import _gate_envases_listos
    from database import get_db
    _sembrar(app)
    with app.app_context():
        conn = get_db()
        # dejar el GOTERO en cero (el frasco sigue con stock)
        conn.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                     "responsable, observaciones) VALUES (?,'Salida',1000,'und','test','vaciar')",
                     (GOTERO,))
        conn.commit()
        g = _gate_envases_listos({'producto': PROD}, conn)
    assert g['status'] == 'warn', 'el candado no avisó: %s' % g
    assert GOTERO in g['mensaje'] or 'gotero' in g['mensaje'].lower(), g['mensaje']


def test_el_candado_pasa_cuando_hay_frasco_y_partes(app):
    """La contracara: si está todo, no puede estorbar."""
    from blueprints.programacion import _gate_envases_listos
    from database import get_db
    _sembrar(app)
    with app.app_context():
        g = _gate_envases_listos({'producto': PROD}, get_db())
    assert g['status'] == 'ok', g
    item = (g.get('meta') or {}).get('items', [{}])[0]
    assert len(item.get('partes') or []) == 2, 'el candado debería reportar las 2 partes: %s' % item
