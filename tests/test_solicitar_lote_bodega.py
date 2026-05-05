"""Reproduce el flujo del boton 'Solicitar' en Bodega MP que Luis Enrique
reporta como 'no hace nada'.

Sebastian 5-may-2026: investigar si el endpoint funciona, si hay un bug
o si el problema es solo UX (sin feedback visible al operario).

Flujo:
  1. Luis logged in
  2. Va a /inventarios → Bodega MP
  3. Click 'Solicitar' en un lote
  4. Modal abre con datos del lote
  5. Llena cantidad + observacion
  6. Click 'Enviar a Compras' → POST /api/solicitudes-compra
  7. ¿Que ve Luis en planta despues?
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luis"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_solicitar_mp_endpoint_acepta_payload_de_bodega_mp(app, db_clean):
    """El payload que envía enviarSolicitarLote() debe crear una solicitud."""
    cs = _login(app, 'luis')
    payload = {
        'solicitante': 'luis',
        'urgencia': 'Normal',
        'observaciones': 'Stock por debajo del minimo, requerido para producir GEL',
        'empresa': 'Espagiria',
        'categoria': 'Materia Prima',
        'tipo': 'Compra',
        'area': 'Produccion',
        'items': [{
            'codigo_mp': 'MP-TEST-SOL',
            'nombre_mp': 'Glicerina test',
            'cantidad_g': 5000,
            'unidad': 'g',
            'justificacion': 'Stock bajo minimo',
            'valor_estimado': 0,
        }],
    }
    r = cs.post('/api/solicitudes-compra', json=payload, headers=csrf_headers())
    assert r.status_code == 201, r.data
    d = r.get_json()
    assert d['numero'].startswith('SOL-')
    # Limpiar
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (d['numero'],))
    conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (d['numero'],))
    conn.commit(); conn.close()


def test_lotes_marca_tiene_solicitud_pendiente(app, db_clean):
    """Si hay una solicitud Pendiente para un codigo_mp, el lote
    correspondiente debe llegar con flag tiene_solicitud_pendiente=true.
    Sin pendiente → False. Esto alimenta el badge 'Solicitada' en UI."""
    cs = _login(app, 'luis')
    # Crear lote con stock para 2 codigos
    conn = sqlite3.connect(os.environ["DB_PATH"])
    for cod in ('MP-SOL-PEN', 'MP-SIN-SOL'):
        conn.execute(
            """INSERT OR REPLACE INTO maestro_mps
               (codigo_mp, nombre_comercial, tipo_material, activo)
               VALUES (?, 'X', 'MP', 1)""",
            (cod,),
        )
        conn.execute(
            """INSERT INTO movimientos
               (material_id, material_nombre, cantidad, tipo, fecha,
                lote, fecha_vencimiento, estado_lote, operador)
               VALUES (?, 'X', 1000, 'Entrada', date('now'),
                       ?, '2027-01-01', 'VIGENTE', 'test')""",
            (cod, f'L-{cod}'),
        )
    conn.commit(); conn.close()
    # Crear solicitud pendiente para MP-SOL-PEN
    r = cs.post('/api/solicitudes-compra',
                json={'solicitante': 'luis', 'urgencia': 'Normal',
                      'observaciones': 'test pendiente flag',
                      'empresa': 'Espagiria', 'categoria': 'Materia Prima',
                      'tipo': 'Compra', 'area': 'Produccion',
                      'items': [{'codigo_mp': 'MP-SOL-PEN', 'nombre_mp': 'X',
                                  'cantidad_g': 1000, 'unidad': 'g',
                                  'justificacion': 'test'}]},
                headers=csrf_headers())
    numero = r.get_json()['numero']
    try:
        # GET /api/lotes
        r2 = cs.get('/api/lotes')
        d = r2.get_json()
        lotes = {l['material_id']: l for l in d['lotes']}
        assert lotes['MP-SOL-PEN']['tiene_solicitud_pendiente'] is True, \
            "Lote con solicitud pendiente debe llevar flag=true"
        assert lotes['MP-SIN-SOL']['tiene_solicitud_pendiente'] is False, \
            "Lote sin solicitud debe llevar flag=false"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,))
        conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
        conn.execute("DELETE FROM movimientos WHERE material_id IN ('MP-SOL-PEN','MP-SIN-SOL')")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp IN ('MP-SOL-PEN','MP-SIN-SOL')")
        conn.commit(); conn.close()


def test_dashboard_html_tiene_funcion_toast(app, db_clean):
    """HTML debe exponer _toastSolicitudCreada · feedback visible al click."""
    cs = _login(app, 'luis')
    body = cs.get('/inventarios').get_data(as_text=True)
    assert '_toastSolicitudCreada' in body
    assert 'toast-sol-creada' in body
    assert 'Solicitud enviada a Compras' in body
    # Badge en lote
    assert 'tiene_solicitud_pendiente' in body
    assert 'Solicitada' in body


def test_luis_ve_su_solicitud_en_mis_solicitudes(app, db_clean):
    """Luis NO debería tener que ir a /compras a buscar su solicitud.
    Esta es la queja real: 'no hace nada' = no la ve en planta despues."""
    cs = _login(app, 'luis')
    r = cs.post('/api/solicitudes-compra',
                json={
                    'solicitante': 'luis',
                    'urgencia': 'Normal',
                    'observaciones': 'Test luis solicita',
                    'empresa': 'Espagiria',
                    'categoria': 'Materia Prima',
                    'tipo': 'Compra',
                    'area': 'Produccion',
                    'items': [{'codigo_mp': 'MP-LUIS-1', 'nombre_mp': 'X',
                                'cantidad_g': 100, 'unidad': 'g',
                                'justificacion': 'test'}],
                },
                headers=csrf_headers())
    assert r.status_code == 201
    numero = r.get_json()['numero']
    try:
        # Endpoint que Luis (operario) puede usar para ver SUS solicitudes
        r2 = cs.get('/api/solicitudes-compra/mis')
        assert r2.status_code == 200, r2.data
        d = r2.get_json()
        # Debe aparecer en alguna lista
        nums = []
        if isinstance(d, list):
            nums = [x.get('numero') for x in d]
        elif isinstance(d, dict):
            nums = [x.get('numero') for x in d.get('solicitudes', [])]
        assert numero in nums, \
            f"Luis no ve su solicitud {numero} · /api/solicitudes-compra/mis devuelve: {nums[:5]}"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,))
        conn.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
        conn.commit(); conn.close()
