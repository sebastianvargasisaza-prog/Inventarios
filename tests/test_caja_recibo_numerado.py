"""Todo movimiento de efectivo sale con un recibo NUMERADO (27-jul).

Sebastián, al pedir el módulo de caja (5-jul): reemplaza *"los recibos sueltos sin numeración"*.
El módulo se construyó a medias: guardaba el movimiento, pero sin número propio, y el botón de
borrar hacía un `DELETE` de verdad. Las dos mitades faltantes son la misma:

    un correlativo del que se pueden arrancar hojas no prueba nada —
    el valor de numerar es justamente que un hueco se vea.

Ahora cada movimiento nace con `RC-<año>-NNNN` (UNIQUE) y anular conserva la fila, con quién y
por qué. El saldo deja de contarla; la lista la sigue mostrando, tachada.

La regla de control que da sentido a todo esto: *todo ingreso/egreso en efectivo pasa por EOS;
sin registro, no existe.*
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _registrar(c, **kw):
    cuerpo = {"tipo": "ingreso", "concepto": "ZZ recibo test", "monto": 1000}
    cuerpo.update(kw)
    r = c.post("/api/animus/caja", json=cuerpo, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida y en PG persiste entre
    corridas, así que un `recibo_numero` UNIQUE de una corrida anterior haría fallar la
    siguiente."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_caja_menor WHERE concepto LIKE 'ZZ recibo%'")
        conn.commit()


def test_cada_movimiento_nace_con_recibo_numerado(app, db_clean):
    _limpiar(app)
    c = _admin(app)
    d = _registrar(c, concepto="ZZ recibo uno")
    assert d.get("recibo_numero", "").startswith("RC-"), (
        "el movimiento salió sin número de recibo: %s" % (d,))


def test_el_correlativo_no_se_repite_ni_se_salta(app, db_clean):
    """Tres movimientos seguidos = tres números consecutivos, sin repetir."""
    _limpiar(app)
    c = _admin(app)
    nums = [_registrar(c, concepto="ZZ recibo serie %d" % i)["recibo_numero"] for i in range(3)]
    assert len(set(nums)) == 3, "se repitió un número de recibo: %s" % (nums,)
    corr = [int(n.rsplit("-", 1)[1]) for n in nums]
    assert corr == sorted(corr) and corr[-1] - corr[0] == 2, (
        "el correlativo no avanzó de a uno: %s" % (nums,))


def test_el_numero_lleva_el_ano_del_movimiento(app, db_clean):
    """Un movimiento con fecha de otro año numera en la serie de ESE año, no en la de hoy: si no,
    el correlativo de un año quedaría con saltos que nadie puede explicar."""
    _limpiar(app)
    c = _admin(app)
    d = _registrar(c, concepto="ZZ recibo viejo", fecha="2025-03-04")
    assert d["recibo_numero"].startswith("RC-2025-"), d["recibo_numero"]


def test_una_fecha_mal_formada_no_arranca_una_serie_paralela(app, db_clean):
    """`RC-abc-0001` sería una serie que nadie puede auditar. Cae al año de Colombia."""
    _limpiar(app)
    c = _admin(app)
    d = _registrar(c, concepto="ZZ recibo fecha rara", fecha="no-es-fecha")
    anio = d["recibo_numero"].split("-")[1]
    assert anio.isdigit() and len(anio) == 4, d["recibo_numero"]


def test_el_recibo_anulado_no_suma_al_saldo_pero_sigue_a_la_vista(app, db_clean):
    """La diferencia exacta entre anular y borrar: deja de contar, pero se puede auditar."""
    _limpiar(app)
    c = _admin(app)
    antes = c.get("/api/animus/caja").get_json()["kpis"]["saldo_total"]
    d = _registrar(c, concepto="ZZ recibo anulable", monto=7777, tipo="ingreso")
    con_mov = c.get("/api/animus/caja").get_json()["kpis"]["saldo_total"]
    assert round(con_mov - antes, 2) == 7777, "el ingreso no entró al saldo"

    r = c.delete("/api/animus/caja/%d" % d["id"],
                 json={"motivo": "se cargó dos veces"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]

    data = c.get("/api/animus/caja").get_json()
    assert round(data["kpis"]["saldo_total"] - antes, 2) == 0, (
        "el recibo anulado sigue sumando al saldo")
    fila = [m for m in data["movimientos"] if m["id"] == d["id"]]
    assert fila, "el recibo anulado desapareció de la lista: eso es borrar, no anular"
    assert fila[0]["anulado"] and fila[0]["anulado_motivo"] == "se cargó dos veces"
    assert fila[0]["recibo_numero"] == d["recibo_numero"], (
        "el recibo anulado perdió su número · el hueco tiene que poder verse")


def test_ninguna_fila_de_caja_queda_sin_recibo(app, db_clean):
    """Invariante durable, incluye el backfill de la mig 383: si mañana alguien agrega otro
    camino que inserta en caja y se olvida del número, esto lo caza."""
    _limpiar(app)
    c = _admin(app)
    _registrar(c, concepto="ZZ recibo invariante")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    huerfanas = conn.execute(
        "SELECT id, fecha, concepto FROM animus_caja_menor "
        "WHERE COALESCE(recibo_numero,'') = '' LIMIT 5").fetchall()
    conn.close()
    assert not huerfanas, (
        "hay movimientos de caja sin número de recibo: %s. Todo INSERT a animus_caja_menor "
        "asigna el correlativo (ver animus_caja_registrar)." % (huerfanas,))
