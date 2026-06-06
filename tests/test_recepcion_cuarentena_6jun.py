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
