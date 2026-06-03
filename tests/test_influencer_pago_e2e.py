"""E2E cadena pago influencer: Marketing crea SOL → aparece en Compras Influencers
→ pagar → desaparece (estado Pagada). Valida el fix 'le doy pagar y no desaparece'
y prueba que la creación (lo que Jeferson hace) funciona end-to-end.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, (user, r.data)
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _crear_influencer():
    db = sqlite3.connect(os.environ['DB_PATH'])
    try:
        db.execute("INSERT INTO marketing_influencers (nombre) VALUES ('ZZ Influencer Test')")
        iid = db.execute(
            "SELECT id FROM marketing_influencers WHERE nombre='ZZ Influencer Test' "
            "ORDER BY id DESC LIMIT 1").fetchone()[0]
        db.commit()
    finally:
        db.close()
    return iid


def test_cadena_pago_influencer_e2e(app, db_clean):
    iid = _crear_influencer()

    # 1. Jeferson (marketing) solicita el pago — esto es "lo que no cargaba"
    cm = _login(app, 'jefferson')
    cm.patch('/api/identidad/jefferson', json={'cedula': '88888888'}, headers=_h())
    r = cm.post(f'/api/marketing/influencers/{iid}/solicitar-pago',
                json={'valor': 250000, 'concepto': 'Reel colaboración'}, headers=_h())
    assert r.status_code == 200, f'CREAR pago influencer falló: {r.status_code} {r.data}'
    d = r.get_json()
    assert d.get('ok'), d
    oc = d.get('oc')
    assert oc, d

    # 2. Sebastian (admin) ve la SOL en el tab Influencers de Compras
    cs = _login(app, 'sebastian')
    lst = cs.get('/api/solicitudes-compra?categoria=Influencer/Marketing Digital')
    assert lst.status_code == 200, lst.data
    sols = lst.get_json()['solicitudes']
    mine = [s for s in sols if s.get('numero_oc') == oc]
    assert mine, f'la SOL creada no aparece en compras influencers · oc={oc} · sols={[s.get("numero_oc") for s in sols]}'
    sol = mine[0]
    assert sol['estado'] == 'Aprobada', sol
    sol_numero = sol['numero']

    # 3. Pagar (con sol_numero · el fix bulletproof)
    rp = cs.patch(f'/api/ordenes-compra/{oc}/pagar',
                  json={'monto': 250000, 'medio': 'Transferencia',
                        'sol_numero': sol_numero}, headers=_h())
    assert rp.status_code == 200, f'PAGAR falló: {rp.status_code} {rp.data}'
    assert rp.get_json().get('ok'), rp.data

    # 4. La SOL ya NO está pendiente: su estado quedó Pagada (desaparece del grid)
    lst2 = cs.get('/api/solicitudes-compra?categoria=Influencer/Marketing Digital')
    sols2 = lst2.get_json()['solicitudes']
    again = [s for s in sols2 if s.get('numero') == sol_numero]
    assert again, 'la SOL desapareció de la data (no debería · solo cambia de estado)'
    assert again[0]['estado'] == 'Pagada', \
        f"BUG 'no desaparece': la SOL sigue en {again[0]['estado']} tras pagar"
