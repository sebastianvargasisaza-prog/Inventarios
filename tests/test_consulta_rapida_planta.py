"""Consulta rápida: el lote y DÓNDE está, sin salirse de la pantalla (30-jul).

Sebastián, mirando "Verificar stock" antes de fabricar: *"aquí pienso que debería ser un punto de
consulta rápida · como aquí dice si alcanza o no, debería salir el lote y la posición de la
materia prima, así pueden ir consultando sin salirse de allí"*. Y sobre los vencidos: *"poner la
ubicación para identificarlos más rápido"*.

Un número sin el lote ni la ubicación obliga a abrir Bodega en otra pestaña y buscar material por
material -- y el operario termina bajando a la bodega con un papel a medias. Es la misma familia
del aviso de lotes de esta mañana (M124): el dato ya estaba, faltaba mostrarlo donde se decide.

Acá también: **la cola de calificación de Calidad la decide quien recibe**. Antes toda referencia
nueva nacía sin calificar y la bandeja acumulaba material que nadie pidió revisar; una bandeja con
22 ítems que no hay que mirar deja de mirarse.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ CONSULTA RAPIDA'
COD = 'MP-ZZCONS'
NOMBRE = 'Material de consulta ZZTEST'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _sembrar():
    _sql("DELETE FROM movimientos WHERE material_id=?", (COD,))
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    _sql("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo) "
         "VALUES (?,?,1)", (COD, NOMBRE))
    _sql("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
         "VALUES (?,1000,1,1)", (PROD,))
    _sql("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
         "VALUES (?,?,?,10)", (PROD, COD, NOMBRE))
    # dos lotes con ubicación distinta + uno en cuarentena que NO se puede tocar
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote, estanteria, posicion) "
         "VALUES (?,?,5000,'Entrada','2026-07-01','LOTE-A','2027-05-31','VIGENTE','B2','4')",
         (COD, NOMBRE))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote, estanteria, posicion) "
         "VALUES (?,?,9000,'Entrada','2026-07-02','LOTE-B','2028-01-31','VIGENTE','C1','2')",
         (COD, NOMBRE))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote, estanteria, posicion) "
         "VALUES (?,?,7000,'Entrada','2026-07-03','LOTE-CUAR','2028-06-30','CUARENTENA','D3','1')",
         (COD, NOMBRE))


def test_verificar_stock_dice_QUE_lote_y_DONDE_esta(app, db_clean):
    _sembrar()
    r = _login(app).post('/api/produccion/simular', headers=_h(),
                         json={'producto': PROD, 'cantidad_kg': 1})
    assert r.status_code == 200, r.data[:300]
    ing = next((i for i in r.get_json()['ingredientes'] if i['material_id'] == COD), None)
    assert ing is not None, 'la MP no salió en la verificación'
    lotes = ing.get('lotes') or []
    assert lotes, 'no dijo de qué lote sacarlo'
    # FEFO: primero el que vence antes
    assert lotes[0]['lote'] == 'LOTE-A', lotes
    assert lotes[0]['ubicacion'] == 'Est. B24', (
        'sin la ubicación hay que ir a buscarlo material por material: %r' % lotes[0])
    assert any(l['lote'] == 'LOTE-B' and l['ubicacion'] == 'Est. C12' for l in lotes), lotes


def test_verificar_stock_muestra_lo_que_NO_se_puede_tocar(app, db_clean):
    """El lote en cuarentena está en el estante y se ve: si la pantalla no lo nombra, el
    operario cree que el sistema no lo tiene (M124)."""
    _sembrar()
    r = _login(app).post('/api/produccion/simular', headers=_h(),
                         json={'producto': PROD, 'cantidad_kg': 1})
    ing = next(i for i in r.get_json()['ingredientes'] if i['material_id'] == COD)
    bloq = ing.get('lotes_bloqueados') or []
    assert any(b['lote'] == 'LOTE-CUAR' for b in bloq), bloq
    assert 'CUARENTENA' in str(bloq[0].get('motivo', '')).upper(), bloq[0]


def test_los_lotes_vencidos_traen_su_ubicacion(app, db_clean):
    """Dar de baja 12 lotes sin saber dónde están es recorrer la bodega buscando cada uno."""
    _sql("DELETE FROM movimientos WHERE material_id=?", (COD,))
    _sql("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo) "
         "VALUES (?,?,1)", (COD, NOMBRE))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote, estanteria, posicion) "
         "VALUES (?,?,800,'Entrada','2024-01-01','LOTE-VIEJO','2024-06-30','VIGENTE','A5','7')",
         (COD, NOMBRE))
    r = _login(app).get('/api/alertas/all')
    assert r.status_code == 200, r.data[:300]
    venc = [x for x in (r.get_json().get('lotes_vencidos') or [])
            if x.get('material_id') == COD]
    assert venc, 'el lote vencido no salió en las alertas'
    assert venc[0].get('ubicacion') == 'Est. A57', (
        'el lote vencido salió sin ubicación: %r' % venc[0])


# ══ la cola de calificación la decide quien recibe ══════════════════════════════

def _crear_ref(cli, requiere):
    return cli.post('/api/mee/crear-auto', headers=_h(), json={
        'tipo': 'ENV', 'descripcion': 'ZZTEST envase calificacion %s' % requiere,
        'volumen_ml': 30, 'requiere_calificacion': requiere})


def test_por_defecto_NO_entra_a_la_cola_de_calidad(app, db_clean):
    """Sebastián: *"deberíamos poner en recepción si requiere calificación, que Catalina escoja,
    porque si no, no"*. Antes TODA referencia nueva caía en la cola."""
    _sql("DELETE FROM maestro_mee WHERE descripcion LIKE 'ZZTEST envase calificacion%'")
    j = _crear_ref(_login(app), False).get_json()
    cod = j.get('codigo')
    assert cod, j
    fila = _sql("SELECT calificado FROM maestro_mee WHERE codigo=?", (cod,))
    assert int(fila[0][0]) == 1, 'entró a la cola de Calidad sin que nadie lo pidiera'


def test_si_se_marca_SI_entra_a_la_cola(app, db_clean):
    """Dientes del otro lado: la opción tiene que servir para las dos cosas."""
    _sql("DELETE FROM maestro_mee WHERE descripcion LIKE 'ZZTEST envase calificacion%'")
    cli = _login(app)
    cod = _crear_ref(cli, True).get_json()['codigo']
    fila = _sql("SELECT calificado FROM maestro_mee WHERE codigo=?", (cod,))
    assert int(fila[0][0]) == 0, 'se marcó que requiere calificación y no quedó pendiente'
    r = cli.get('/api/mee/por-calificar')
    assert r.status_code == 200
    assert any(x['codigo'] == cod for x in r.get_json()['pendientes']), (
        'no aparece en la cola de Calidad')
