"""La precarga de alertas de creadores acelera SIN cambiar la respuesta (15-ago-2026).

Sebastián salió y pidió revisar la velocidad de cada módulo. Medido con sonda local, la cola
de decisiones del Centro de Mando gastaba **22 de sus 55 consultas** leyendo, de a una por
pago, el historial y el estado del creador -- once creadores pendientes, dos lecturas cada
uno. En producción cada consulta es un viaje a la base, así que eso es lo que se siente como
"carga lento" (M43).

Lo que estos tests protegen no es la velocidad (un umbral en milisegundos mide la máquina
tanto como el código · M176), sino las dos cosas que un atajo así puede romper en silencio:

  1. **El tope de 60 es POR CREADOR.** Traer el historial con un `IN (...)` y un límite
     global dejaría a los creadores con más movimiento sin antecedentes, o sea que las
     alertas de doble pago se apagarían justo donde más importan, sin un solo error (M133).
  2. **La respuesta tiene que ser la misma.** Un atajo que puede contestar distinto no es un
     atajo (M128).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    # Limpiar ANTES de sembrar: un `finally` no corre si el proceso muere y la base es
    # compartida entre archivos (M103).
    for sql in ("DELETE FROM pagos_influencers WHERE influencer_nombre LIKE 'ZPRE %'",
                "DELETE FROM marketing_influencers WHERE nombre LIKE 'ZPRE %'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _creador(nombre, estado="Activo"):
    return _exec("INSERT INTO marketing_influencers (nombre, estado) VALUES (?,?)",
                 (nombre, estado))


def _pago(inf_id, nombre, valor, fecha, estado="Pagada"):
    return _exec(
        "INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
        "estado, concepto) VALUES (?,?,?,?,?,'ZPRE historico')",
        (inf_id, nombre, valor, fecha, estado))


def test_el_tope_de_historial_es_por_creador_no_compartido(app, db_clean):
    """Dos creadores con historial largo: cada uno conserva el suyo.

    Con un límite global, el segundo creador se quedaría sin antecedentes y su alerta de
    doble pago no se dispararía -- el fallo silencioso que este test existe para impedir.
    """
    _limpiar()
    from flask import g
    from blueprints.marketing import precargar_alertas_influencers
    import database

    a = _creador("ZPRE Creador A")
    b = _creador("ZPRE Creador B")
    for i in range(70):                       # más que el tope de 60, a propósito
        _pago(a, "ZPRE Creador A", 100000 + i, "2026-01-%02d" % ((i % 28) + 1))
        _pago(b, "ZPRE Creador B", 200000 + i, "2026-02-%02d" % ((i % 28) + 1))

    with app.test_request_context():
        c = database.get_db()
        precargar_alertas_influencers(
            c, [{"influencer_id": a}, {"influencer_id": b}])
        memo = getattr(g, "_alertas_prev_memo", {})
        assert a in memo and b in memo, "algún creador quedó sin historial precargado"
        assert len(memo[a]) == 60, "creador A: %d (el tope se compartió)" % len(memo[a])
        assert len(memo[b]) == 60, "creador B: %d (el tope se compartió)" % len(memo[b])
        # y son SUS pagos, no los del vecino
        assert all(f[1] >= 200000 for f in memo[b]), "al creador B le llegó historial ajeno"


def test_la_alerta_de_doble_pago_sigue_saliendo_con_la_precarga(app, db_clean):
    """El borde que hace que el atajo no apague un control (M96).

    Se siembra un antecedente que DEBE disparar la alerta y se comprueba que sale igual con
    el memo precargado -- si la precarga entregara el historial en otro formato, la alerta
    se caería sin ruido.
    """
    _limpiar()
    from flask import g
    from blueprints.marketing import (precargar_alertas_influencers,
                                      alertas_pago_influencer)
    import database

    # Se dispara por la MISMA PUBLICACIÓN (compara textos), no por monto ni por mes: esas
    # dos reglas se anclan en `hoy`, así que un antecedente con fecha fija se sale de la
    # ventana con el correr del calendario y el test dejaría de medir (M99).
    x = _creador("ZPRE Repetido")
    _exec("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, "
          "estado, concepto, fecha_publicacion) VALUES (?,?,?,?,?,'ZPRE historico',?)",
          (x, "ZPRE Repetido", 500000, "2026-03-10", "Pagada", "2026-03-09"))
    nuevo = _pago(x, "ZPRE Repetido", 500000, "2026-03-11", estado="Pendiente")

    def _alertas(precargar):
        with app.test_request_context():
            c = database.get_db()
            if precargar:
                precargar_alertas_influencers(c, [{"influencer_id": x}])
            return alertas_pago_influencer(
                c, influencer_id=x, nombre="ZPRE Repetido", valor=500000,
                fecha_publicacion="2026-03-09", entregable="", excluir_pago_id=nuevo)

    con = _alertas(True)
    sin = _alertas(False)
    cods_con = sorted(a.get("codigo") for a in con)
    cods_sin = sorted(a.get("codigo") for a in sin)
    assert cods_con == cods_sin, ("la precarga cambió las alertas: %s vs %s"
                                  % (cods_con, cods_sin))
    assert cods_con, "no salió ninguna alerta: el test no está midiendo el caso que cree"


def test_el_estado_precargado_distingue_sin_estado_de_no_existe(app, db_clean):
    """Un creador que no está en el maestro NO es lo mismo que uno con estado en blanco.

    El consumidor recibía None (fetchone sin fila) y no emitía alerta; si la precarga
    devolviera una tupla vacía se leería como estado en blanco -- misma pantalla, otra
    decisión (M124).
    """
    _limpiar()
    from flask import g
    from blueprints.marketing import precargar_alertas_influencers
    import database

    vivo = _creador("ZPRE Vivo", estado="Inactivo")
    fantasma = 99000123                       # id que no existe en el maestro

    with app.test_request_context():
        c = database.get_db()
        precargar_alertas_influencers(
            c, [{"influencer_id": vivo}, {"influencer_id": fantasma}])
        memo = getattr(g, "_alertas_estado_memo", {})
        assert memo.get(vivo) == ("Inactivo",), memo.get(vivo)
        assert memo.get(fantasma) is None, (
            "un creador inexistente tiene que quedar como 'sin fila', no como estado vacío")


def test_la_cola_de_decisiones_responde_igual(app, db_clean):
    """El endpoint real sigue contestando lo mismo (M128: el atajo no cambia la respuesta)."""
    _limpiar()
    import blueprints.marketing as mkt

    x = _creador("ZPRE Cola")
    _pago(x, "ZPRE Cola", 300000, "2026-04-01", estado="Pendiente")

    c = _login(app)
    r1 = c.get("/api/centro/decisiones")
    assert r1.status_code == 200, r1.data[:200]

    real = mkt.precargar_alertas_influencers
    mkt.precargar_alertas_influencers = lambda conn, filas: None
    try:
        r2 = c.get("/api/centro/decisiones")
    finally:
        mkt.precargar_alertas_influencers = real
    assert r2.status_code == 200, r2.data[:200]

    # `generado_en` es la marca de tiempo de cada respuesta: se compara el resto.
    j1, j2 = r1.get_json(), r2.get_json()
    assert j1["decisiones"] == j2["decisiones"], "la precarga cambió la cola de decisiones"
    assert j1["resumen"] == j2["resumen"], "la precarga cambió el resumen"
