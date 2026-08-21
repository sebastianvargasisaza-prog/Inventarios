"""Cuadre rápido de inventario · 21-ago-2026.

Sebastián: *"el inventario está descuadrado ... necesito algo súper rápido: estantería por cada
cosa, productos, y si tiene varios lotes que los muestre, con la opción de corregir o de colocar
'no existe' ... lo más importante es que sea muy rápido y se refleje"*.

Rápido no puede significar flojo. Lo que estos guards fijan:
  · el ajuste va como movimiento con cantidad > 0 (nunca 0 · el trigger de PG lo rechaza);
  · CONSERVA el estado del lote -- un cuadre no libera por la puerta de atrás lo que está en
    cuarentena -- y su vencimiento, o el FEFO recibiría material eterno;
  · contar y encontrar lo mismo no escribe kardex, pero SÍ queda en el rastro;
  · dar de alta lo que el sistema no tenía exige decir de dónde salió;
  · y un doble clic no ajusta dos veces.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = "ZCUA-MP-1"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.fetchall()
    finally:
        conn.close()


def _limpiar():
    """Limpiar ANTES de sembrar (M103)."""
    _sql("DELETE FROM movimientos WHERE material_id LIKE 'ZCUA-%'")
    _sql("DELETE FROM oc_recepcion_dedup WHERE numero_oc='CUADRE'")


def _sembrar(lote="L-1", cant=100.0, estado="VIGENTE", vence="2027-05-05"):
    _sql("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, fecha, "
         "operador, estanteria, posicion, fecha_vencimiento, estado_lote) "
         "VALUES (?,?,'Entrada',?,?,?,'seed','A','A-1',?,?)",
         (COD, "MP DE PRUEBA CUADRE", cant, lote, "2026-08-01 08:00:00", vence, estado))


def _stock(lote="L-1"):
    r = _sql("SELECT SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') "
             "THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') "
             "THEN -cantidad ELSE 0 END) FROM movimientos WHERE material_id=? AND lote=?",
             (COD, lote))
    return float((r[0][0] or 0) if r else 0)


def test_corregir_deja_el_stock_en_lo_que_hay(app, db_clean):
    _limpiar()
    _sembrar(cant=100.0)
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-1", "fisico": 87.5, "token": "zc-1"},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d["stock"] == 87.5 and d["tipo"] == "Salida", d
    assert abs(_stock() - 87.5) < 0.001, "el kardex no quedó en lo que hay"
    # El movimiento lleva cantidad POSITIVA (el trigger de PG rechaza 0 o negativo · M18)
    mov = _sql("SELECT tipo, cantidad, estado_lote, fecha_vencimiento, observaciones "
               "FROM movimientos WHERE material_id=? AND observaciones LIKE '%cuadre%'", (COD,))
    assert len(mov) == 1 and mov[0][1] > 0, mov
    assert "cuadre" in (mov[0][4] or ""), "el ajuste no dice que salió del cuadre"
    _limpiar()


def test_no_existe_lo_deja_en_cero(app, db_clean):
    _limpiar()
    _sembrar(cant=40.0)
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-1", "fisico": 0, "token": "zc-2",
                     "motivo": "no existe en el estante"},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert abs(_stock()) < 0.001, "no lo dejó en cero"
    _limpiar()


def test_el_cuadre_conserva_el_estado_y_el_vencimiento_del_lote(app, db_clean):
    """Un lote en cuarentena que se cuadra sigue en cuarentena: el ajuste no puede liberarlo por
    la puerta de atrás (M31/M23). Y sin el vencimiento, el FEFO lo trataría como eterno (M118)."""
    _limpiar()
    _sembrar(lote="L-Q", cant=50.0, estado="CUARENTENA", vence="2026-12-31")
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-Q", "fisico": 45, "token": "zc-3"},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    mov = _sql("SELECT estado_lote, fecha_vencimiento FROM movimientos "
               "WHERE material_id=? AND lote='L-Q' AND observaciones LIKE '%cuadre%'", (COD,))
    assert mov and mov[0][0] == "CUARENTENA", "el ajuste liberó un lote en cuarentena: %r" % (mov,)
    assert mov[0][1] == "2026-12-31", "el ajuste perdió el vencimiento: %r" % (mov,)
    _limpiar()


def test_contar_y_encontrar_lo_mismo_no_escribe_kardex_pero_queda_en_el_rastro(app, db_clean):
    _limpiar()
    _sembrar(cant=30.0)
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-1", "fisico": 30, "token": "zc-4"},
               headers=csrf_headers())
    assert r.status_code == 200 and r.get_json().get("sin_cambio") is True, r.data[:300]
    ajustes = _sql("SELECT id FROM movimientos WHERE material_id=? AND observaciones LIKE '%cuadre%'", (COD,))
    assert not ajustes, "escribió un movimiento para una diferencia de cero"
    rastro = _sql("SELECT COUNT(*) FROM audit_log WHERE accion='CUADRE_CONFIRMA' "
                  "AND registro_id=?", (COD,))
    assert rastro[0][0] >= 1, "confirmar que cuadra no dejó rastro"
    _limpiar()


def test_dar_de_alta_exige_decir_de_donde_salio(app, db_clean):
    """Una Entrada sin documento que aparece de la nada tiene que decir su origen."""
    _limpiar()
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-NUEVO", "fisico": 12, "token": "zc-5"},
               headers=csrf_headers())
    assert r.status_code == 400 and r.get_json().get("codigo") == "MOTIVO_REQUERIDO", r.data[:300]
    r2 = c.post("/api/inventario/cuadre",
                json={"codigo_mp": COD, "lote": "L-NUEVO", "fisico": 12, "token": "zc-6",
                      "motivo": "estaba en bodega sin registrar"},
                headers=csrf_headers())
    assert r2.status_code == 200 and r2.get_json().get("alta") is True, r2.data[:300]
    assert abs(_stock("L-NUEVO") - 12) < 0.001
    _limpiar()


def test_un_doble_clic_no_ajusta_dos_veces(app, db_clean):
    _limpiar()
    _sembrar(cant=100.0)
    c = _login(app)
    cuerpo = {"codigo_mp": COD, "lote": "L-1", "fisico": 60, "token": "zc-repetido"}
    r1 = c.post("/api/inventario/cuadre", json=cuerpo, headers=csrf_headers())
    r2 = c.post("/api/inventario/cuadre", json=cuerpo, headers=csrf_headers())
    assert r1.status_code == 200, r1.data[:200]
    assert r2.status_code == 409 and r2.get_json().get("codigo") == "CUADRE_DUPLICADO", r2.data[:200]
    assert abs(_stock() - 60) < 0.001, "el doble clic ajustó dos veces"
    _limpiar()


def test_no_acepta_cantidad_negativa(app, db_clean):
    _limpiar()
    _sembrar(cant=10.0)
    c = _login(app)
    r = c.post("/api/inventario/cuadre",
               json={"codigo_mp": COD, "lote": "L-1", "fisico": -5, "token": "zc-7"},
               headers=csrf_headers())
    assert r.status_code == 400, r.data[:200]
    _limpiar()


def test_la_pantalla_abre_y_trae_las_tres_acciones(app, db_clean):
    c = _login(app)
    r = c.get("/planta/cuadre")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    for txt in ("Cuadre de inventario", "No existe", "= Igual", "/api/inventario/cuadre",
                "/api/conteo/estanterias", "X-CSRF-Token"):
        assert txt in html, "falta %r en la pantalla" % txt
    assert "Enter" in html, "no dice que Enter guarda"


def test_hay_como_llegar_desde_bodega(app, db_clean):
    """Una pantalla sin enlace no existe (M121)."""
    from .conftest import pantalla_servida
    c = _login(app)
    dash = pantalla_servida(c, "/inventarios")
    assert "/planta/cuadre" in dash, "no hay puerta al cuadre desde el dashboard"
