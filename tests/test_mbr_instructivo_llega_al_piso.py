"""El instructivo de fabricación aprobado tiene que LLEGAR al legajo del lote (26-jul).

Sebastián había cargado el procedimiento real (fases, °C, hidratación) en 27 de los 30 MBR
aprobados. Igual el operario veía 3 pasos genéricos de relleno. Dos causas distintas:

  1. `crear_ebr_desde_mbr` buscaba el MBR por nombre EXACTO (case-sensitive). La fórmula dice
     'BLUSH BALM' y el MBR está guardado 'Blush Balm' → para el sistema eran productos
     distintos → NO_MBR_APROBADO → la orden nacía sin legajo (M2).
  2. Los legajos ya ABIERTOS siguieron apuntando a la versión vieja (que al aprobar la nueva
     pasó a `obsoleto`), así que conservaban los pasos de relleno.

Y el texto del paso de dispensación no puede llevar un peso absoluto congelado: el mismo legajo
mostraba "Dispensar AGUA · 77,79 g" y una hoja de pesaje que decía 7.779 g (M5/M67).
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _limpiar(conn, productos=(), lotes=()):
    """Borra lo que este archivo siembra, ANTES de sembrarlo.

    ⚠ Sin esto los tests no son re-ejecutables: `ebr_ejecuciones.lote` es UNIQUE y la BD de tests
    PERSISTE entre corridas del gate, así que la 2ª vez chocaban con IntegrityError. Me pasó: el
    gate pasó dos veces y a la tercera se puso rojo por mis propios datos, no por el código.
    Limpiar-antes es determinista (nada de sufijos aleatorios) y deja el test corrible N veces.
    `audit_log` NO se toca: es inmutable por trigger (Part 11) y no molesta.
    """
    cur = conn.cursor()
    for lote in lotes:
        for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote)=? "
                             "OR lote=?", (lote, lote)).fetchall():
            cur.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=?", (r[0],))
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
    for prod in productos:
        for r in cur.execute("SELECT id FROM mbr_templates WHERE UPPER(TRIM(producto_nombre))="
                             "UPPER(TRIM(?))", (prod,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
    conn.commit()


def _mbr_aprobado(conn, producto, pasos, version=1):
    cur = conn.cursor()
    cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                "VALUES (?,?,'draft',10000,'test')", (producto, version))
    mid = cur.lastrowid
    for i, d in enumerate(pasos, 1):
        cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso) "
                    "VALUES (?,?,'fabricacion',?,'mezclado')", (mid, i, d))
    cur.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mid,))
    conn.commit()
    return mid


# ─────────────────────────── 1 · match por nombre ───────────────────────────

def test_el_MBR_se_encuentra_aunque_el_nombre_este_en_otras_mayusculas(app):
    """El caso real: fórmula 'BLUSH BALM' · MBR guardado 'Blush Balm'."""
    from blueprints.brd import crear_ebr_desde_mbr
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar(conn, productos=('Prueba Case Balm',), lotes=('LOTE-CASE-1',))
        _mbr_aprobado(conn, 'Prueba Case Balm', ['Paso 1. Calentar fase A a 75°C'])
        r = crear_ebr_desde_mbr(conn.cursor(), producto_nombre='PRUEBA CASE BALM',
                                lote='LOTE-CASE-1', usuario='sebastian')
        conn.commit()
    assert r['ok'] is True, ('el MBR existe con otras mayúsculas y tiene que encontrarse: %s' % r)
    assert r['pasos'] == 1


def test_sin_MBR_aprobado_sigue_sin_poder_fabricar(app):
    """El match flexible NO puede volverse permisivo: sin MBR aprobado, no se fabrica (BPM)."""
    from blueprints.brd import crear_ebr_desde_mbr
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar(conn, lotes=('LOTE-CASE-2',))
        r = crear_ebr_desde_mbr(conn.cursor(), producto_nombre='PRODUCTO QUE NO EXISTE JAMAS',
                                lote='LOTE-CASE-2', usuario='sebastian')
    assert r['ok'] is False and r['error'] == 'NO_MBR_APROBADO', r


def test_gana_la_version_aprobada_mas_alta(app):
    """Con v1 y v2 aprobadas del mismo producto, el legajo tiene que nacer con la v2."""
    from blueprints.brd import crear_ebr_desde_mbr
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar(conn, productos=('Prueba Version',), lotes=('LOTE-VER-1',))
        _mbr_aprobado(conn, 'Prueba Version', ['viejo'], version=1)
        _mbr_aprobado(conn, 'Prueba Version', ['Paso 1. nuevo', 'Paso 2. nuevo'], version=2)
        r = crear_ebr_desde_mbr(conn.cursor(), producto_nombre='PRUEBA VERSION',
                                lote='LOTE-VER-1', usuario='sebastian')
        conn.commit()
    assert r['ok'] is True and r['pasos'] == 2, r


# ─────────────────── 2 · el paso no congela un peso absoluto ───────────────────

def test_el_paso_de_dispensacion_no_lleva_gramos_congelados(app):
    """Un texto que sobrevive al lote no puede afirmar un peso: el lote cambia de tamaño."""
    import inspect

    from blueprints.brd import _generar_mbr_desde_formula
    src = inspect.getsource(_generar_mbr_desde_formula)
    assert 'de la fórmula' in src and 'hoja de pesaje' in src, (
        'el paso debe expresar la PROPORCIÓN y remitir a la hoja de pesaje')
    assert 'g ({round(float(pct' not in src, 'volvió el gramaje congelado'


def test_el_paso_generado_expresa_porcentaje_y_no_un_peso(app):
    """⚠ Este test SIEMBRA una fórmula y tiene que BORRARLA: la BD de tests es compartida y una
    fórmula al 77,79% dejada ahí rompe la property test que verifica que toda fórmula activa sume
    ~100 (me pasó · el gate se puso rojo por mi propia basura)."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                    "VALUES ('MPTESTX','Agua test','Agua test',1)")
        cur.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, "
                    "descripcion, fecha_creacion) VALUES ('PROD PCT TEST', 1000, 1.0, '', '2026-07-26')")
        cur.execute("DELETE FROM formula_items WHERE producto_nombre='PROD PCT TEST'")
        cur.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
                    "porcentaje, cantidad_g_por_lote) VALUES ('PROD PCT TEST','MPTESTX','Agua test',77.79,777.9)")
        conn.commit()
        from blueprints.brd import _generar_mbr_desde_formula
        res = _generar_mbr_desde_formula(conn.cursor(), 'PROD PCT TEST', usuario='sebastian')
        conn.commit()
        assert res.get('ok'), res
        desc = conn.execute(
            "SELECT descripcion FROM mbr_pasos WHERE mbr_template_id=? AND orden=1",
            (res['id'],)).fetchone()[0]
        # limpiar lo sembrado ANTES de assertar, para que un assert que falle no deje basura
        try:
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (res['id'],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (res['id'],))
            cur.execute("DELETE FROM formula_items WHERE producto_nombre='PROD PCT TEST'")
            cur.execute("DELETE FROM formula_headers WHERE producto_nombre='PROD PCT TEST'")
            conn.commit()
        except Exception:
            conn.rollback()
    assert '77.79%' in desc, desc
    assert '777.9 g' not in desc and '777.9g' not in desc, (
        'el peso por lote NO puede quedar congelado en el texto del paso: %s' % desc)
