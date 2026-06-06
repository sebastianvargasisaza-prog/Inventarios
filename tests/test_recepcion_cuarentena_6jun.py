"""6-jun-2026 · Cuarentena para MATERIA PRIMA NUEVA.

Sebastián: "cuando llega una MP que ya existe hay botón de cuarentena, pero debería
también estar para MP nueva". Flujo real: la MP llega → estante físico CUARENTENA +
estado_lote CUARENTENA (bloqueada) → Calidad revisa → libera → ubicación final.

El backend /api/recepcion ya soportaba el flag `cuarentena`; el frontend de "Crear
Nueva MP" ahora enruta el primer ingreso por /api/recepcion con ese flag (antes iba
por /api/movimientos, que no pone cuarentena).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _firmar(c, *, record_id, meaning='libera'):
    rc = c.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=csrf_headers())
    assert rc.status_code == 200, rc.data
    token = rc.get_json()['token']
    rs = c.post('/api/sign', json={'record_table': 'movimientos', 'record_id': str(record_id),
                                   'meaning': meaning, 'challenge_token': token}, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()['signature_id']


def test_liberar_cc_mueve_a_ubicacion_final(admin_client):
    """6-jun · Al LIBERAR (cc-review APROBADO) con ubicación final, el lote pasa de
    la estantería CUARENTENA a su ubicación final (todas las filas) y queda APROBADO."""
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    rec = admin_client.post('/api/recepcion', json={
        'codigo_mp': 'MPLIBQC', 'nombre_comercial': 'Activo Libera', 'nombre_inci': 'LIBACT',
        'cantidad': 4000, 'lote': 'LLIBQC', 'estanteria': 'CUARENTENA', 'cuarentena': True,
        'proveedor': 'ProvZ'}, headers=h)
    assert rec.status_code in (200, 201), rec.data
    c = sqlite3.connect(os.environ['DB_PATH'])
    mov_id = c.execute("SELECT id FROM movimientos WHERE material_id='MPLIBQC' AND lote='LLIBQC' AND tipo='Entrada'").fetchone()[0]
    c.close()
    sig = _firmar(admin_client, record_id=mov_id, meaning='libera')
    r = admin_client.post('/api/lotes/cc-review', json={
        'mov_id': mov_id, 'lote': 'LLIBQC', 'codigo_mp': 'MPLIBQC',
        'coa_ok': True, 'lote_coincide': True, 'coa_vigente': True, 'ficha_ok': True,
        'solubilidad': 'CONFORME', 'resultado_aql': 'CONFORME', 'muestra_retencion': True,
        'estanteria_final': '14', 'posicion_final': 'E', 'signature_id': sig}, headers=h)
    assert r.status_code == 200, r.data
    c = sqlite3.connect(os.environ['DB_PATH'])
    row = c.execute("SELECT estado_lote, estanteria, posicion FROM movimientos WHERE id=?", (mov_id,)).fetchone()
    c.close()
    assert row[0] == 'APROBADO', f'debe quedar APROBADO · {row[0]}'
    assert row[1] == '14' and row[2] == 'E', f'debe moverse a la ubicación final · {row}'


def test_recepcion_mp_nueva_en_cuarentena(logged_client):
    """MP nueva ingresada con cuarentena=True → catálogo creado + lote en CUARENTENA."""
    payload = {
        'codigo_mp': 'MPNUEVACUAR', 'nombre_comercial': 'Activo Nuevo QC',
        'nombre_inci': 'NEWACTIVE', 'cantidad': 5000, 'lote': 'LNUEVOQC',
        'estanteria': 'CUARENTENA', 'cuarentena': True, 'proveedor': 'ProvX',
    }
    r = logged_client.post('/api/recepcion', json=payload)
    assert r.status_code in (200, 201), r.data
    c = sqlite3.connect(os.environ['DB_PATH'])
    row = c.execute("SELECT estado_lote FROM movimientos WHERE material_id='MPNUEVACUAR' AND lote='LNUEVOQC'").fetchone()
    mp = c.execute("SELECT codigo_mp FROM maestro_mps WHERE codigo_mp='MPNUEVACUAR'").fetchone()
    c.close()
    assert mp, 'la MP nueva debe quedar creada en catálogo'
    assert row and row[0] == 'CUARENTENA', f'la MP nueva debe quedar en CUARENTENA · {row}'


def test_recepcion_mp_nueva_sin_cuarentena_queda_vigente(logged_client):
    """Sin el flag, la MP nueva entra disponible (VIGENTE), no en cuarentena."""
    payload = {
        'codigo_mp': 'MPNUEVAOK', 'nombre_comercial': 'Activo Libre',
        'nombre_inci': 'FREEACTIVE', 'cantidad': 3000, 'lote': 'LLIBRE1',
        'estanteria': '9', 'cuarentena': False, 'proveedor': 'ProvY',
    }
    r = logged_client.post('/api/recepcion', json=payload)
    assert r.status_code in (200, 201), r.data
    c = sqlite3.connect(os.environ['DB_PATH'])
    row = c.execute("SELECT estado_lote FROM movimientos WHERE material_id='MPNUEVAOK' AND lote='LLIBRE1'").fetchone()
    c.close()
    assert row and row[0] != 'CUARENTENA', f'sin flag NO debe quedar en cuarentena · {row}'


def test_form_nueva_mp_tiene_checkbox_cuarentena(logged_client):
    """El form de 'Crear Nueva MP' debe ofrecer el checkbox de cuarentena."""
    r = logged_client.get('/inventarios')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'nmp-ing-cuarentena' in body, 'el checkbox de cuarentena debe estar en el form de MP nueva'
