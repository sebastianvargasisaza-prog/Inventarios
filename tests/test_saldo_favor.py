"""Catalina 17-jul · Saldo a favor por proveedor (mig 359). Alejandro hace anticipos / paga de más /
notas crédito → queda saldo a favor, aplicable a la próxima OC. Ledger: saldo = SUM(credito) − SUM(aplicacion)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _oc(numero, proveedor, valor, estado="Autorizada"):
    _exec("INSERT INTO ordenes_compra (numero_oc, proveedor, valor_total, estado, fecha) "
          "VALUES (?, ?, ?, ?, date('now'))", (numero, proveedor, valor, estado))


def _saldo(client, prov):
    r = client.get("/api/compras/saldos-favor?proveedor=" + prov)
    return (r.get_json().get("saldos") or [{}])[0].get("saldo", 0)


def test_registrar_anticipo_y_ajuste(app, db_clean):
    c = _login(app)
    r = c.post("/api/compras/proveedor-saldo/registrar",
               json={"proveedor": "ProvSaldo1", "origen": "anticipo", "monto": 500000, "medio": "Transferencia"},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert abs(r.get_json().get("saldo", 0) - 500000) < 1
    # ajuste (nota crédito) suma
    r2 = c.post("/api/compras/proveedor-saldo/registrar",
                json={"proveedor": "ProvSaldo1", "origen": "ajuste", "monto": 50000, "observaciones": "devolución"},
                headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]
    assert abs(r2.get_json().get("saldo", 0) - 550000) < 1
    # anticipo dejó egreso; ajuste no
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        n_egr = conn.execute("SELECT COUNT(*) FROM flujo_egresos WHERE referencia='ProvSaldo1'").fetchone()[0]
    finally:
        conn.close()
    assert n_egr == 1, "el anticipo (sale plata) debe dejar 1 egreso; el ajuste (nota crédito) NO"


def test_aplicar_saldo_a_oc(app, db_clean):
    c = _login(app)
    c.post("/api/compras/proveedor-saldo/registrar",
           json={"proveedor": "ProvSaldo2", "origen": "ajuste", "monto": 100000}, headers=csrf_headers())
    _oc("OC-SF-1", "ProvSaldo2", 80000, "Autorizada")
    # aplicar 60000 del saldo → pendiente 20000, saldo restante 40000, OC 'Parcial'
    r = c.post("/api/compras/ordenes-compra/OC-SF-1/aplicar-saldo", json={"monto": 60000}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert abs(d["pendiente"] - 20000) < 1, d
    assert abs(d["saldo_restante"] - 40000) < 1, d
    # OC quedó Parcial + hay un pago SaldoAFavor sin egreso
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        est = conn.execute("SELECT estado FROM ordenes_compra WHERE numero_oc='OC-SF-1'").fetchone()[0]
        pago = conn.execute("SELECT monto, medio FROM pagos_oc WHERE numero_oc='OC-SF-1'").fetchone()
        n_egr = conn.execute("SELECT COUNT(*) FROM flujo_egresos WHERE referencia='OC-SF-1'").fetchone()[0]
    finally:
        conn.close()
    assert est == "Parcial", est
    assert pago and abs(pago[0] - 60000) < 1 and pago[1] == "SaldoAFavor", pago
    assert n_egr == 0, "aplicar saldo NO genera egreso (la plata ya salió cuando entró el crédito)"


def test_aplicar_saldo_insuficiente(app, db_clean):
    c = _login(app)
    c.post("/api/compras/proveedor-saldo/registrar",
           json={"proveedor": "ProvSaldo3", "origen": "ajuste", "monto": 10000}, headers=csrf_headers())
    _oc("OC-SF-2", "ProvSaldo3", 100000, "Autorizada")
    r = c.post("/api/compras/ordenes-compra/OC-SF-2/aplicar-saldo", json={"monto": 50000}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:300]
    assert r.get_json().get("codigo") == "SALDO_INSUFICIENTE"


def test_sobrepago_genera_saldo_favor(app, db_clean):
    c = _login(app)
    _oc("OC-SP-1", "ProvSobre1", 50000, "Autorizada")
    # sin flag: pagar 60000 (OC vale 50000) → rechazo 422
    r0 = c.patch("/api/ordenes-compra/OC-SP-1/pagar", json={"monto": 60000, "medio": "Transferencia"},
                 headers=csrf_headers())
    assert r0.status_code == 422, r0.data[:300]
    assert r0.get_json().get("codigo") == "OVER_PAYMENT"
    # con flag: 50000 a la OC (Pagada) + 10000 a favor del proveedor
    r = c.patch("/api/ordenes-compra/OC-SP-1/pagar",
                json={"monto": 60000, "medio": "Transferencia", "permitir_saldo_favor": True},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:400]
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        est = conn.execute("SELECT estado FROM ordenes_compra WHERE numero_oc='OC-SP-1'").fetchone()[0]
        pag = conn.execute("SELECT COALESCE(SUM(monto),0) FROM pagos_oc WHERE numero_oc='OC-SP-1'").fetchone()[0]
        # egreso por el monto REAL pagado (60000), no por 50000
        egr = conn.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE referencia='OC-SP-1'").fetchone()[0]
    finally:
        conn.close()
    assert est == "Pagada", est
    assert abs(pag - 50000) < 1, ("la OC solo recibe su valor (50000), no el sobrepago", pag)
    assert abs(egr - 60000) < 1, ("el egreso = plata real que salió (60000)", egr)
    # el excedente quedó a favor
    assert abs(_saldo(c, "ProvSobre1") - 10000) < 1, "10000 de sobrepago a favor"


def test_numero_transaccion_anclado_a_oc(app, db_clean):
    c = _login(app)
    _oc("OC-TX-1", "ProvTx", 40000, "Autorizada")
    r = c.patch("/api/ordenes-compra/OC-TX-1/pagar",
                json={"monto": 40000, "medio": "Transferencia", "numero_transaccion": "TRX-998877"},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = c.get("/api/ordenes-compra/OC-TX-1/pagos").get_json()
    assert d["pagos"] and d["pagos"][0].get("numero_transaccion") == "TRX-998877", d["pagos"]


def test_registro_pagos_excluye_influencers(app, db_clean):
    # Compras (Catalina) NO debe ver pagos a influencers · van en Tesorería/Marketing
    _oc("OC-NORM-1", "ProvNormal", 10000, "Pagada")
    _exec("INSERT INTO ordenes_compra (numero_oc, proveedor, valor_total, estado, categoria, fecha) "
          "VALUES ('OC-INFLU-1', 'Influencer X', 20000, 'Pagada', 'Influencer/Marketing Digital', date('now'))")
    # ambas con un pago para que aparezcan (estado Pagada)
    _exec("INSERT INTO pagos_oc (numero_oc, monto, medio, fecha_pago) VALUES ('OC-NORM-1', 10000, 'Transferencia', date('now'))")
    _exec("INSERT INTO pagos_oc (numero_oc, monto, medio, fecha_pago) VALUES ('OC-INFLU-1', 20000, 'Transferencia', date('now'))")
    c = _login(app)
    d = c.get("/api/compras/pagos").get_json()
    ocs = [(p.get("numero_oc") or "") for p in d.get("pagos", [])]
    assert "OC-NORM-1" in ocs, "la OC normal de compras SÍ aparece"
    assert "OC-INFLU-1" not in ocs, "la OC de influencer NO debe aparecer en Compras"


def test_compras_ui_saldofavor_render(app, db_clean):
    c = _login(app)
    body = c.get('/compras').get_data(as_text=True)
    assert 'm-saldofavor' in body          # modal
    assert 'openSaldoFavor' in body        # botón
    assert 'aplicarSaldoOC' in body        # aplicar en el modal de pago


def test_aplicar_saldo_excede_pendiente(app, db_clean):
    c = _login(app)
    c.post("/api/compras/proveedor-saldo/registrar",
           json={"proveedor": "ProvSaldo4", "origen": "ajuste", "monto": 500000}, headers=csrf_headers())
    _oc("OC-SF-3", "ProvSaldo4", 30000, "Autorizada")
    r = c.post("/api/compras/ordenes-compra/OC-SF-3/aplicar-saldo", json={"monto": 50000}, headers=csrf_headers())
    assert r.status_code == 422, r.data[:300]
    assert r.get_json().get("codigo") == "EXCEDE_PENDIENTE"
