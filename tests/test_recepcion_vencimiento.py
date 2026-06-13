"""REC-01 (Sebastián 12-jun · auditoría recepciones): el ingreso manual
(/api/recepcion) NO debe aceptar MP ya vencida como disponible (puerta lateral ·
recibir_oc ya lo bloquea). Override admin: forzar_vencido=true.
"""
import os
import sqlite3
from datetime import date, timedelta
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _salidas_entradas(cod):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM movimientos WHERE material_id=? AND tipo='Entrada'", (cod,)).fetchone()[0]
    finally:
        conn.close()


def test_ingreso_manual_bloquea_mp_vencida(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MP-VENC','GLYCERIN','Glic',1)")
    venc_pasado = (date.today() - timedelta(days=30)).isoformat()
    c = _login(app)
    r = c.post('/api/recepcion', json={'codigo_mp': 'MP-VENC', 'cantidad': 500, 'lote': 'L-VENC',
                                       'fecha_vencimiento': venc_pasado}, headers=csrf_headers())
    assert r.status_code == 409, f"MP vencida no debe ingresar · {r.status_code} {r.data}"
    assert (r.get_json() or {}).get('vencimiento_pasado') is True
    assert _salidas_entradas('MP-VENC') == 0, "no debe crear la Entrada de MP vencida"


def test_ingreso_manual_vencida_con_forzar(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MP-VENC2','GLYCERIN','Glic',1)")
    venc_pasado = (date.today() - timedelta(days=10)).isoformat()
    c = _login(app)
    r = c.post('/api/recepcion', json={'codigo_mp': 'MP-VENC2', 'cantidad': 500, 'lote': 'L-VENC2',
                                       'fecha_vencimiento': venc_pasado, 'forzar_vencido': True},
               headers=csrf_headers())
    assert r.status_code in (200, 201), f"con forzar_vencido (admin) debe pasar · {r.data}"


def test_ingreso_manual_vigente_pasa(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MP-VIG','GLYCERIN','Glic',1)")
    venc_futuro = (date.today() + timedelta(days=365)).isoformat()
    c = _login(app)
    r = c.post('/api/recepcion', json={'codigo_mp': 'MP-VIG', 'cantidad': 500, 'lote': 'L-VIG',
                                       'fecha_vencimiento': venc_futuro}, headers=csrf_headers())
    assert r.status_code in (200, 201), f"MP vigente debe ingresar normal · {r.data}"
