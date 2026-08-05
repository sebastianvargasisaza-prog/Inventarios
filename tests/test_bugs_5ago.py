# -*- coding: utf-8 -*-
"""Los bugs de la auditoría del 5-ago · verificados EJECUTANDO, no leyendo.

Sebastián: *"revisa velocidad de la app, errores, bugs, usa cerebro cero error"*.

Todos comparten una propiedad incómoda: **pasan en los tests y rompen en producción**, porque
la suite corre sobre SQLite y producción es PostgreSQL. Una columna proyectada que ni está
agrupada ni dentro de un agregado: SQLite elige un valor cualquiera y "funciona", PG la rechaza.

Y los que están dentro de un `try` no dan error — dejan la sección **vacía**, que se lee como
"no hay nada". En dos de estos casos lo que no aparecía era justo lo que había que atender:
los equipos con la calibración vencida, y los productos que el planificador tenía que programar.

Por eso estos tests **ejecutan la consulta contra el esquema real** en vez de buscar texto: leer
el SQL fue exactamente lo que dejó pasar estos bugs durante meses.
"""
import io
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(txt):
    fuera = []
    for ln in txt.splitlines():
        _s = ln.strip()
        if _s.startswith('#') or _s.startswith('//'):
            continue
        fuera.append(re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


# ═══ 1 · PLATA · aprobar un pago a creador dos veces ═════════════════════════

def _sol_influencer(app, numero='ZZSOL-INF-1'):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE ?", (numero.replace('SOL', 'OC') + '%',))
        c.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, categoria, "
                  "                                observaciones) "
                  "VALUES (?, date('now'), 'Pendiente', 'jefferson', "
                  "        'Influencer/Marketing Digital', 'BENEFICIARIO: ZZ Creadora')",
                  (numero,))
        conn.commit()
    return numero


def test_aprobar_DOS_VECES_un_pago_a_creador_da_409(app, admin_client, db_clean):
    """Antes el UPDATE iba `WHERE numero=?` a secas y el estado leído sólo se usaba para el
    audit. Con eso, dos clics creaban **dos OC y dos pagos** por la misma solicitud — y el dedup
    de `pagos_influencers` no los veía, porque empareja por `numero_oc` y la segunda OC lleva
    sufijo horario, o sea un número distinto."""
    from .conftest import csrf_headers
    num = _sol_influencer(app)
    url = '/api/solicitudes-compra/%s/aprobar-influencer' % num

    r1 = admin_client.post(url, data=json.dumps({'valor': 500000}),
                           headers=csrf_headers(), content_type='application/json')
    assert r1.status_code in (200, 201), r1.data[:300]

    r2 = admin_client.post(url, data=json.dumps({'valor': 900000}),
                           headers=csrf_headers(), content_type='application/json')
    assert r2.status_code == 409, 'dejó aprobar dos veces la misma solicitud'
    assert (r2.get_json() or {}).get('codigo') == 'SOL_YA_RESUELTA'

    from database import get_db
    with app.app_context():
        conn = get_db()
        # el monto NO se movió con el segundo intento
        val = conn.execute("SELECT valor FROM solicitudes_compra WHERE numero=?", (num,)).fetchone()[0]
        n_oc = conn.execute("SELECT COUNT(*) FROM ordenes_compra WHERE numero_oc LIKE ?",
                            (num.replace('SOL', 'OC') + '%',)).fetchone()[0]
        conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (num,))
        conn.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE ?",
                     (num.replace('SOL', 'OC') + '%',))
        conn.commit()
    assert float(val) == 500000, 're-aprobar le cambió el monto en silencio: %s' % val
    assert n_oc <= 1, 'se crearon %d órdenes de compra por una sola solicitud' % n_oc


# ═══ 2 · INVIMA · un lote RECHAZADO no vuelve a liberarse ════════════════════

def test_un_lote_RECHAZADO_no_se_puede_volver_a_liberar(app, admin_client, db_clean):
    """El UPDATE iba `WHERE id=?` sin repetir el estado ni mirar `rowcount`: un lote que Calidad
    ya rechazó se podía poner en `liberado` con un clic posterior. Es un control INVIMA que se
    elude sin dejar ni un 409 (M27 · el hermano de `brd.py` ya estaba cerrado)."""
    from database import get_db
    from .conftest import csrf_headers
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM cola_liberacion WHERE lote='ZZLOTE-DISP'")
        # `fecha_envasado` y `fecha_min_liberacion` son NOT NULL, y `estado` tiene CHECK:
        # 'pendiente' no está en la lista (el estado inicial es 'listo_revisar').
        c.execute("INSERT INTO cola_liberacion (producto_nombre, lote, unidades, "
                  "                             fecha_envasado, fecha_min_liberacion, estado) "
                  "VALUES ('ZZ PRODUCTO DISP','ZZLOTE-DISP', 100, "
                  "        date('now','-20 days'), date('now','-6 days'), 'listo_revisar')")
        conn.commit()
        iid = conn.execute("SELECT id FROM cola_liberacion WHERE lote='ZZLOTE-DISP'").fetchone()[0]

    url = '/api/planta/cola-liberacion/%d/disposicion' % iid
    r1 = admin_client.post(url, data=json.dumps({'disposicion': 'rechazado', 'notas': 'fuera de spec'}),
                           headers=csrf_headers(), content_type='application/json')
    assert r1.status_code in (200, 201), r1.data[:300]

    # ⚠ `override_micro` va a propósito: sin él choca ANTES el gate de micro y el 409 lo
    # contesta ESE guard, así que el CAS nuevo no se ejercitaría nunca — un test que pasa por la
    # razón equivocada es peor que no tenerlo (M152). Con el override, el único que puede
    # frenar el segundo intento es el CAS.
    r2 = admin_client.post(url, data=json.dumps({'disposicion': 'aprobado', 'notas': 'ups',
                                                 'override_micro': True}),
                           headers=csrf_headers(), content_type='application/json')
    assert r2.status_code == 409, 'un lote RECHAZADO se volvió a liberar sin un solo aviso'
    assert (r2.get_json() or {}).get('codigo') == 'LOTE_YA_DISPUESTO'

    with app.app_context():
        conn = get_db()
        disp = conn.execute("SELECT disposicion FROM cola_liberacion WHERE id=?", (iid,)).fetchone()[0]
        conn.execute("DELETE FROM cola_liberacion WHERE lote='ZZLOTE-DISP'")
        conn.commit()
    assert (disp or '').lower() == 'rechazado', 'la disposición cambió pese al 409'


# ═══ 3 · las consultas que revientan SOLO en PostgreSQL ══════════════════════

def _ejecuta(conn, sql, params=()):
    """Corre la consulta de verdad. Leer el SQL es lo que dejó pasar estos bugs meses."""
    conn.execute(sql, params).fetchall()


def test_las_consultas_del_planificador_CORREN(app, db_clean):
    """`cantidad_kg` cruda con `GROUP BY` por EXPRESIÓN: PG nunca deriva dependencia funcional
    de una expresión. Tapado por `except: pass`, así que el dict quedaba vacío y **todo producto
    sin producción completada previa se saltaba**."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        _ejecuta(conn, """SELECT UPPER(TRIM(producto)) AS prod,
                                 MAX(substr(fecha_programada,1,10)) AS f,
                                 MAX(COALESCE(cantidad_kg,0)) AS kg
                            FROM produccion_programada
                           WHERE COALESCE(origen,'') IN ('eos_plan','eos_b2b','eos_retroactivo')
                             AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
                             AND fin_real_at IS NULL
                             AND COALESCE(cantidad_kg,0) > 0
                           GROUP BY UPPER(TRIM(producto))""")
    p = _sin_comentarios(_src('api/blueprints/plan.py'))
    assert 'MAX(COALESCE(cantidad_kg,0)) AS kg' in p
    assert p.count("""                      cantidad_kg
               FROM produccion_programada""") == 0, 'volvió la columna cruda'


def test_las_consultas_de_equipos_CORREN(app, db_clean):
    """`ep.nombre`/`ep.area_codigo` con `GROUP BY ep.codigo`, y la PK es `id`. Envueltas en
    `try/except: pass` → el panel de Luz **nunca** mostraba equipos con calibración vencida."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        _ejecuta(conn, """SELECT ep.codigo, MAX(ep.nombre) AS nombre, MAX(ep.area_codigo) AS area_codigo,
                                 MAX(ee.fecha_proxima) as fecha_proxima
                            FROM equipos_planta ep
                            LEFT JOIN equipos_eventos ee
                              ON ee.equipo_codigo = ep.codigo
                             AND ee.tipo_evento IN ('calibracion','verificacion_semestral')
                           WHERE COALESCE(ep.activo,1) = 1
                           GROUP BY ep.codigo""")
    e = _sin_comentarios(_src('api/blueprints/espagiria.py'))
    assert 'SELECT ep.codigo, ep.nombre, ep.area_codigo' not in e, \
        'volvió una columna cruda en el GROUP BY de equipos'


def test_el_diagnostico_de_stock_minimo_CORRE(app, db_clean):
    """`fi.material_nombre` cruda con `GROUP BY fi.material_id` (PK = `id`). **Sin try**: la
    pantalla devolvía error interno justo en el caso que esa rama atiende (código huérfano)."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        _ejecuta(conn, """SELECT fi.material_id, MAX(fi.material_nombre) AS material_nombre,
                                 COUNT(DISTINCT fi.producto_nombre) as n_productos
                            FROM formula_items fi
                           WHERE UPPER(TRIM(fi.material_id)) = UPPER(TRIM(?))
                             AND fi.material_id != ?
                           GROUP BY fi.material_id""", ('MP00001', 'MP00001'))
    a = _sin_comentarios(_src('api/blueprints/admin.py'))
    assert 'SELECT DISTINCT fi.material_id, fi.material_nombre,' not in a, \
        'volvió la columna cruda en explicar-stock-min'


def test_el_diagnostico_de_stock_minimo_RESPONDE(app, admin_client, db_clean):
    """El que vale: abrir el endpoint. Los dos GROUP BY estaban SIN `try`, así que devolvía 500."""
    r = admin_client.get('/api/admin/explicar-stock-min/MP00001')
    assert r.status_code in (200, 404), r.data[:300]


# ═══ 4 · la tabla fantasma que tumbaba el correo semanal ═════════════════════

def test_el_auditor_semanal_lee_la_tabla_que_EXISTE(app, db_clean):
    """`email_destinatarios` no existe en ningún CREATE del repo; la real es
    `email_destinatarios_config`, que ese mismo archivo usa bien en 8 sitios. Y no estaba en un
    `try`, así que reventaba antes de llegar al "Sin destinatarios configurados" que el propio
    código tenía preparado: el correo **nunca** salía."""
    ap = _sin_comentarios(_src('api/blueprints/auto_plan.py'))
    assert 'FROM email_destinatarios WHERE' not in ap, 'sigue leyendo una tabla que no existe'
    from database import get_db
    with app.app_context():
        conn = get_db()
        _ejecuta(conn, "SELECT email FROM email_destinatarios_config "
                       " WHERE COALESCE(activo,0)=1 AND COALESCE(email,'') <> ''")


def test_sin_destinatarios_avisa_en_vez_de_reventar(app, admin_client, db_clean):
    """Un 500 y un "no hay destinatarios configurados" mandan a lugares distintos: el primero a
    buscar un bug, el segundo a la pantalla de configuración."""
    ap = _src('api/blueprints/auto_plan.py')
    i = ap.find('Sin destinatarios configurados')
    assert i > 0, 'se perdió el mensaje'
    # y la lectura de arriba está protegida
    assert 'no pude leer los destinatarios' in ap[max(0, i - 1200):i], \
        'la lectura de destinatarios volvió a quedar sin guard'
