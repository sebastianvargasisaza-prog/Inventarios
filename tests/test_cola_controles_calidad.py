"""Calidad necesita su cola de controles, no abrir lote por lote (15-ago-2026).

Entrando a MyBatch con el usuario de **Laura González, jefe de control de calidad**,
su tablero no es el del planeador: tiene tres colas propias, y la que usa a diario
es *"Controles en Proceso de Fabricación Pendientes"* — los controles de TODOS los
lotes abiertos en una sola lista, cada uno con su especificación al lado.

En EOS los controles viven dentro del legajo. La información estaba, pero para
saber qué le faltaba registrar había que abrir lote por lote: el trabajo de Calidad
no tenía pantalla (M121). Esta sección de la bandeja es esa pantalla.

Lo que fija el guard: que la cola aparezca, que respete la FASE de cada legajo (un
legajo de acondicionamiento pide atributos, no densidad), que un control ya
adjudicado salga de la cola, y que se arme con UNA consulta y no una por lote (M43).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _sembrar_legajo(fase, lote, producto):
    """Un legajo abierto de la fase pedida, por SQL directo (la bandeja sólo lee).

    Se siembra con fecha MUY ANTIGUA a propósito. La cola ordena por antigüedad -lo
    que lleva más tiempo esperando va primero, que es lo correcto para Calidad- y
    muestra los primeros 60 controles. Con la base de la suite llena, un legajo de
    hoy queda al final de esa lista y el test estaría midiendo otra cosa: controlar
    su universo es del test, no del código (M102).
    """
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES (?,1,'aprobado',1000,'sebastian')", (producto,))
    return _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                 "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                 "VALUES (?,1,?,?,'en_proceso',?,'sebastian','1990-01-01 00:00:00',1000)",
                 (mbr, lote, lote, fase))


def _limpiar():
    for sql in ("DELETE FROM ipc_estandar_resultados WHERE ebr_id IN "
                "(SELECT id FROM ebr_ejecuciones WHERE lote LIKE 'ZCOLA%')",
                "DELETE FROM ebr_ejecuciones WHERE lote LIKE 'ZCOLA%'",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZCOLA%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _cola(app):
    c = _login(app)
    r = c.get("/api/calidad/bandeja")
    assert r.status_code == 200, r.data[:200]
    return c, (r.get_json().get("secciones") or {}).get("controles_pendientes") or {}


def test_la_cola_junta_los_controles_de_todos_los_lotes(app, db_clean):
    _limpiar()
    e1 = _sembrar_legajo("fabricacion", "ZCOLA-OP-1", "ZCOLA PRODUCTO A")
    e2 = _sembrar_legajo("fabricacion", "ZCOLA-OP-2", "ZCOLA PRODUCTO B")
    _c, cola = _cola(app)
    mios = [i for i in cola["items"] if i["ebr_id"] in (e1, e2)]
    assert mios, "la cola de Calidad no trae los controles pendientes: %s" % cola
    assert {i["ebr_id"] for i in mios} == {e1, e2}, "no junta los lotes en una sola lista"
    # fabricación pide los cinco del granel
    codigos = {i["control_codigo"] for i in mios if i["ebr_id"] == e1}
    assert {"densidad", "ph", "olor", "color", "apariencia"} <= codigos, codigos


def test_la_cola_respeta_la_fase_del_legajo(app, db_clean):
    """Un legajo de acondicionamiento pide atributos, no la densidad de una caja."""
    _limpiar()
    eo = _sembrar_legajo("acondicionamiento", "ZCOLA-OA-1", "ZCOLA PRODUCTO C")
    _c, cola = _cola(app)
    codigos = {i["control_codigo"] for i in cola["items"] if i["ebr_id"] == eo}
    assert "etq_adherencia" in codigos, codigos
    assert "densidad" not in codigos, (
        "le pide la densidad a un lote de acondicionamiento: %s" % sorted(codigos))


def test_un_control_ya_adjudicado_sale_de_la_cola(app, db_clean):
    """Registrar el valor no alcanza: cuenta como hecho cuando Calidad lo adjudica."""
    _limpiar()
    e1 = _sembrar_legajo("fabricacion", "ZCOLA-OP-3", "ZCOLA PRODUCTO D")
    _c, antes = _cola(app)
    n_antes = len([i for i in antes["items"] if i["ebr_id"] == e1])
    assert n_antes >= 5, antes
    _exec("INSERT INTO ipc_estandar_resultados (ebr_id, control_codigo, control_nombre, "
          "valor_texto, conforme, medido_por, medido_at_utc) "
          "VALUES (?,'ph','pH a 25°C','4.8',1,'laura',datetime('now','utc'))", (e1,))
    _c2, despues = _cola(app)
    codigos = {i["control_codigo"] for i in despues["items"] if i["ebr_id"] == e1}
    assert "ph" not in codigos, "un control adjudicado sigue en la cola"
    assert len([i for i in despues["items"] if i["ebr_id"] == e1]) == n_antes - 1


def test_si_la_cola_se_recorta_lo_dice(app, db_clean):
    """Un tope que recorta sin decirlo convierte la lista en un total falso: "60"
    se lee como el total y podrían ser 400 (M155)."""
    _limpiar()
    for i in range(3):
        _sembrar_legajo("fabricacion", "ZCOLA-REC-%d" % i, "ZCOLA REC %d" % i)
    _c, cola = _cola(app)
    assert "recortado" in cola, cola.keys()
    # el total cuenta TODO, aunque items venga acotado
    assert cola["total"] >= len(cola["items"]), cola
    assert cola["recortado"] == max(0, cola["total"] - len(cola["items"])), cola
    # Y el total tiene que contar TODOS los legajos abiertos, no sólo los que
    # entraron en la ventana: un total calculado sobre un recorte es falso, y es
    # el número que alimenta el KPI de Calidad (M155).
    assert cola["lotes_sin_mirar"] == 0, (
        "quedaron %d legajos sin mirar: el total no es el total" % cola["lotes_sin_mirar"])
    assert cola["lotes_abiertos"] >= cola["lotes"], cola


def test_la_pantalla_de_calidad_pinta_la_cola(app, db_clean):
    """Un dato que el backend manda y la pantalla no pinta no existe (M115)."""
    c = _login(app)
    # Calidad sirve su JS como archivo aparte desde el 15-ago: la pantalla es el HTML mas
    # su bundle, o el guard daria rojo por donde quedo escrito el codigo (M166).
    html = pantalla_servida(c, "/calidad")
    # Se exige la CONDICIÓN que dibuja la tarjeta, no sólo que el texto aparezca:
    # con `if(false)` los títulos siguen en el archivo y el guard pasaría verde con
    # la cola apagada (mediría otra cosa · M152).
    for que, pieza in (("la condición que la dibuja", "if(s.controles_pendientes){"),
                       ("el título de la tarjeta", "Controles en proceso pendientes"),
                       ("el enlace para registrar", "registrar &rarr;")):
        assert pieza in html, "la bandeja de Calidad no muestra %s (%s)" % (que, pieza)


def test_no_hace_una_consulta_por_lote(app, db_clean):
    """Una consulta por fila es lo que tumba la pantalla (M43): el bloque de
    resultados va FUERA del recorrido de legajos."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "calidad.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("11. CONTROLES EN PROCESO PENDIENTES")
    assert i > 0, "no se encontró la sección"
    bloque = fuente[i:i + 3000]
    k = bloque.find("FROM ipc_estandar_resultados")
    m = bloque.find("for r in rows:")
    assert k > 0 and m > 0, bloque[:200]
    assert k < m, "la consulta de resultados quedó dentro del loop por legajo"
