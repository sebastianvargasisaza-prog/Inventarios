"""Modal de liberación CC como rótulo FINAL editable (Laura 16-jul).

Calidad verifica y corrige lo que llegó mal antes de liberar: INCI, cantidad real
(re-peso), lote, tipo de material, fecha de recepción. Todo se aplica y se audita al
firmar. El rótulo final (imprimir rótulo) sale con esos valores.
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


def test_cc_corrige_inci_cantidad_lote_tipo_fecha(admin_client):
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    rec = admin_client.post('/api/recepcion', json={
        'codigo_mp': 'MPCORR1', 'nombre_comercial': 'Activo Corr', 'nombre_inci': 'INCI VIEJO',
        'cantidad': 4000, 'lote': 'LOTEVIEJO', 'estanteria': 'CUARENTENA', 'cuarentena': True,
        'proveedor': 'ProvC'}, headers=h)
    assert rec.status_code in (200, 201), rec.data
    conn = sqlite3.connect(os.environ['DB_PATH'])
    mov_id = conn.execute("SELECT id FROM movimientos WHERE material_id='MPCORR1' AND lote='LOTEVIEJO' AND tipo='Entrada'").fetchone()[0]
    conn.close()
    sig = _firmar(admin_client, record_id=mov_id, meaning='libera')
    r = admin_client.post('/api/lotes/cc-review', json={
        'mov_id': mov_id, 'lote': 'LOTEVIEJO', 'codigo_mp': 'MPCORR1',
        'coa_ok': True, 'resultado_aql': 'CONFORME',
        'inci_corregido': 'INCI CORRECTO, AQUA',
        'cantidad_final': 3850,
        'lote_final': 'LOTENUEVO',
        'tipo_material': 'ME',
        'fecha_recepcion_final': '2026-07-10',
        'signature_id': sig}, headers=h)
    assert r.status_code == 200, r.data
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        mp = conn.execute("SELECT nombre_inci, tipo_material FROM maestro_mps WHERE codigo_mp='MPCORR1'").fetchone()
        mv = conn.execute("SELECT cantidad, lote, fecha, estado_lote FROM movimientos WHERE id=?", (mov_id,)).fetchone()
    finally:
        conn.close()
    assert mp[0] == 'INCI CORRECTO, AQUA', 'el INCI debe quedar corregido en el maestro'
    assert (mp[1] or '') == 'ME', 'el tipo de material debe quedar corregido'
    assert abs(float(mv[0]) - 3850) < 0.01, 'la cantidad debe quedar re-pesada'
    assert mv[1] == 'LOTENUEVO', 'el lote debe quedar corregido'
    assert str(mv[2])[:10] == '2026-07-10', 'la fecha de recepción debe quedar corregida'
    assert mv[3] == 'VIGENTE', 'aprobado = kardex VIGENTE (canónico)'


def test_rotulo_final_usa_overrides(admin_client):
    """El rótulo acepta ?inci=&tipo=&frec= (lo que Calidad verificó) y los muestra."""
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
                 "VALUES ('MPROT1','Comercial X','INCI BASE',1)")
    conn.commit(); conn.close()
    r = admin_client.get('/rotulo-recepcion/MPROT1/LOTX/1000?inci=INCI%20VERIFICADO&tipo=ME&frec=2026-07-09')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'INCI VERIFICADO' in html, 'el rótulo debe mostrar el INCI override'
    assert '2026-07-09' in html, 'el rótulo debe mostrar la fecha override'
    # tipo ME marcado (checkbox lleno &#9746;)
    assert '&#9746; Material de Envase (ME)' in html
