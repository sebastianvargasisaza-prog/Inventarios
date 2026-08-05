# -*- coding: utf-8 -*-
"""El cierre de la auditoría del 5-ago.

Tres cosas que quedaban, verificadas una por una contra el código real antes de tocar:

1. **Cerrar una no conformidad no tenía CAS.** Lee el estado, verifica que no esté cerrada, y
   después actualiza sin repetir la condición: con 3 workers, dos cierres simultáneos pasan LOS
   DOS y dejan dos entradas de `audit_log` del mismo cierre — en un registro regulado.
2. **`/api/animus/alertas-stock` revienta en PostgreSQL**: `stock_pt` tiene PK `id`, no `sku`, y
   proyectaba cinco columnas crudas. El hermano de abajo ya se había arreglado el 16-jun con su
   comentario explicando el drift; éste quedó (M45).
3. **`_estacionalidad_mensual` sin caché compartida**: escanea 24 meses con un `json.loads` por
   fila, y su gemelo la tiene desde M85. Cada worker frío lo re-escaneaba.

⚠ Y uno que **NO era un bug**: el informe decía que cerrar una desviación tampoco tenía CAS, y
sí lo tiene (`WHERE id=? AND estado IN (...)` + `rowcount != 1`). Verificar antes de aplicar es
lo que evitó "arreglar" código sano — la regla #1 del cerebro existe por esto.
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
        if ln.strip().startswith('#'):
            continue
        fuera.append(re.sub(r'\s+#\s.*$', '', ln))
    return chr(10).join(fuera)


# ── 1 · cerrar una NC dos veces ──────────────────────────────────────────────

def test_cerrar_una_NC_dos_veces_da_409(app, admin_client, db_clean):
    """El comportamiento visible: no se cierra dos veces.

    ⚠ Este test NO prueba el CAS, y conviene decirlo en vez de creer que sí: el chequeo previo
    (check-then-act) ya atrapa el reintento SECUENCIAL, así que pasa igual con o sin la condición
    en el `WHERE`. Lo comprobé quitándola. El CAS protege sólo la ventana CONCURRENTE — dos
    workers que leen antes de que el otro commitee — y eso no se puede reproducir desde un
    cliente de test (M27 ya lo dice). Quien verifica el CAS es el test estructural de abajo."""
    from database import get_db
    from .conftest import csrf_headers
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM no_conformidades WHERE descripcion='ZZ NC CIERRE'")
        # `fecha` es NOT NULL y la columna de detección se llama así, no `fecha_deteccion`.
        c.execute("INSERT INTO no_conformidades (descripcion, estado, tipo, fecha, area) "
                  "VALUES ('ZZ NC CIERRE', 'Abierta', 'MP', date('now'), 'Produccion')")
        conn.commit()
        ncid = conn.execute("SELECT id FROM no_conformidades "
                            " WHERE descripcion='ZZ NC CIERRE'").fetchone()[0]

    cuerpo = json.dumps({'motivo_cierre': 'cerrada tras verificar la acción',
                         'accion_correctiva': 'se ajustó el procedimiento'})
    url = '/api/calidad/no-conformidades/%d/cerrar' % ncid
    r1 = admin_client.post(url, data=cuerpo, headers=csrf_headers(), content_type='application/json')
    assert r1.status_code in (200, 201), r1.data[:300]
    r2 = admin_client.post(url, data=cuerpo, headers=csrf_headers(), content_type='application/json')
    assert r2.status_code == 409, 'dejó cerrar dos veces la misma no conformidad'

    with app.app_context():
        conn = get_db()
        n = conn.execute("SELECT COUNT(*) FROM audit_log WHERE tabla='no_conformidades' "
                         "  AND registro_id=? AND accion LIKE '%CERRAR%'", (str(ncid),)).fetchone()[0]
        conn.execute("DELETE FROM no_conformidades WHERE descripcion='ZZ NC CIERRE'")
        conn.commit()
    assert n <= 1, 'quedaron %d rastros de cierre para la misma NC' % n


def test_el_cierre_de_NC_lleva_la_condicion_en_el_WHERE(app, db_clean):
    cal = _sin_comentarios(_src('api/blueprints/calidad.py'))
    i = cal.find("SET estado='Cerrada', fecha_cierre")
    assert i > 0, 'no encontré el cierre de NC'
    bloque = cal[i:i + 500]
    assert "WHERE id=? AND COALESCE(estado,'') <> 'Cerrada'" in bloque, 'el UPDATE sigue sin CAS'
    assert 'c.rowcount == 0' in bloque, 'no verifica el rowcount'


def test_cerrar_una_DESVIACION_ya_tenia_CAS(app, db_clean):
    """⚠ El informe lo reportó como faltante y NO lo era. Este test existe para que nadie
    "arregle" lo que ya estaba bien — y para dejar por escrito que se verificó."""
    asg = _sin_comentarios(_src('api/blueprints/aseguramiento.py'))
    i = asg.find("SET estado='cerrada', fecha_cierre")
    assert i > 0, 'no encontré el cierre de desviación'
    bloque = asg[i:i + 700]
    assert "WHERE id=? AND estado IN ('capa_propuesto','capa_implementado')" in bloque
    assert 'c.rowcount != 1' in bloque


# ── 2 · el GROUP BY que revienta en PG ───────────────────────────────────────

def test_alertas_stock_CORRE(app, db_clean):
    """Ejecutar la consulta contra el esquema real · leerla es lo que dejó pasar el bug."""
    from database import get_db
    with app.app_context():
        get_db().execute("""SELECT sku, MIN(descripcion) AS descripcion, MIN(empresa) AS empresa,
                                   SUM(unidades_disponible) as disponible,
                                   MIN(stock_minimo_ud) AS stock_minimo_ud
                              FROM stock_pt
                             WHERE empresa='ANIMUS' AND estado='Disponible'
                             GROUP BY sku
                            HAVING SUM(unidades_disponible) < MIN(stock_minimo_ud)
                               AND MIN(stock_minimo_ud) > 0""").fetchall()
    m = _sin_comentarios(_src('api/blueprints/maquila.py'))
    assert 'SELECT sku, descripcion, empresa,' not in m, 'volvieron las columnas crudas'
    assert 'HAVING disponible < stock_minimo_ud' not in m, 'el HAVING sigue sobre el alias'


def test_alertas_stock_RESPONDE(app, admin_client, db_clean):
    r = admin_client.get('/api/animus/alertas-stock')
    assert r.status_code == 200, r.data[:300]


# ── 3 · la estacionalidad deja de re-escanear ────────────────────────────────

def test_la_estacionalidad_tiene_CACHE_COMPARTIDA(app, db_clean):
    """Su gemelo la tiene desde M85 · sin ella cada worker frío re-escanea 24 meses de órdenes
    con un `json.loads` por fila, que es la forma exacta de M43/M85."""
    prog = _sin_comentarios(_src('api/blueprints/programacion.py'))
    assert '_estacionalidad_mensual_cached' in prog, 'no tiene el envoltorio con caché'
    i = prog.find('def _estacionalidad_mensual_cached')
    bloque = prog[i:i + 2200]
    assert 'plan_vmaps_cache' in bloque, 'no usa la caché compartida en BD'
    assert '_ESTAC_MENSUAL_CACHE' in bloque, 'no tiene el nivel 1 por worker'
    assert 'PYTEST_CURRENT_TEST' in bloque, 'la caché no se desactiva en tests'


def test_las_LLAVES_de_los_meses_vuelven_como_NUMERO(app, db_clean):
    """⚠ JSON convierte las llaves de un dict a TEXTO. Sin re-convertirlas, el consumidor pide
    `multiplicadores[3]` y no encuentra nada — en silencio, y sólo cuando la caché está
    caliente: o sea el peor tipo de bug, el que no aparece al probarlo."""
    prog = _src('api/blueprints/programacion.py')
    i = prog.find('def _estacionalidad_mensual_cached')
    bloque = prog[i:i + 2200]
    assert "int(m)" in bloque, 'las llaves de los meses vuelven de JSON como texto'


def test_la_estacionalidad_DEVUELVE_lo_mismo_desde_la_cache(app, db_clean):
    """M128: un atajo puede acelerar la respuesta, NO cambiarla. Se calcula, se guarda, se lee
    de la caché y las dos tienen que dar lo mismo — incluidas las llaves de los meses."""
    import os as _os
    from database import get_db
    with app.app_context():
        conn = get_db()
        import sys
        sys.path.insert(0, os.path.join(RAIZ, 'api'))
        from blueprints.programacion import _estacionalidad_mensual_cached as _ec
        # La caché se desactiva bajo pytest a propósito · para probar el round-trip hay que
        # levantar la variable, que es justo lo que M85 dice que hay que hacer.
        _guardado = _os.environ.pop('PYTEST_CURRENT_TEST', None)
        try:
            a = _ec(conn.cursor(), 24, force=True)      # calcula y persiste
            b = _ec(conn.cursor(), 24)                   # debería venir de la caché
        finally:
            if _guardado is not None:
                _os.environ['PYTEST_CURRENT_TEST'] = _guardado
    assert set(a.keys()) == set(b.keys()), 'la caché devuelve otros productos'
    for prod in list(a.keys())[:5]:
        assert a[prod]['multiplicadores'] == b[prod]['multiplicadores'], \
            'la caché cambia los multiplicadores de %s' % prod
