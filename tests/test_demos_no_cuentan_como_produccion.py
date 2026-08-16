"""Los legajos DEMO no cuentan como producción (15-ago-2026).

Sebastián, mirando Envasado: *"ese de allí es un demo"*. La pantalla decía **"1 orden
abierta · 1 con 3 días o más sin cerrar"** y lo único que había era un legajo de
demostración abierto hacía 26 días. Ese número no se apaga nunca —nadie va a cerrar un
demo— y un indicador que grita por algo que no se puede resolver enseña a ignorar el
tablero entero (M129/M154).

El demo NO se esconde: sigue en la lista, marcado. Una fila que desaparece sin explicación
manda a buscarla, y el demo existe justamente para poder mirarlo (M124). Lo que cambia es
que **no suma a los indicadores**, y la pantalla dice cuántos dejó afuera (M148).
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
    for sql in ("DELETE FROM ebr_ejecuciones WHERE lote LIKE 'ZDEM%' OR lote LIKE 'DEMO-ZZ%'",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZDEM%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _legajo(lote, dias_atras=30):
    from datetime import datetime, timedelta
    cuando = (datetime.utcnow() - timedelta(hours=5) - timedelta(days=dias_atras)
              ).strftime("%Y-%m-%d %H:%M:%S")
    # Un MBR por lote: `mbr_templates` tiene UNIQUE(producto, version), así que sembrar
    # dos legajos con el mismo nombre revienta el fixture (no el código).
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES (?,1,'aprobado',10000,'sebastian')",
                ("ZDEM %s" % lote,))
    return _exec(
        "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
        "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
        "VALUES (?,1,?,?,'en_proceso','envasado','sebastian',?,10000)",
        (mbr, lote, lote, cuando))


def _resumen(app):
    c = _login(app)
    r = c.get("/api/brd/ordenes-unificadas?fase=envasado")
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    return j["resumen"], j["ordenes"]


def test_un_demo_solo_no_hace_que_haya_ordenes_abiertas(app, db_clean):
    """El caso exacto de la captura: agregar un demo no puede mover los indicadores.

    Se mide por DIFERENCIA (antes/después de sembrarlo) en vez de exigir ceros absolutos:
    la base es compartida y otros archivos siembran legajos de envasado, así que un
    `abiertas == 0` pasa aislado y falla en el gate -- el test no controlaría su universo
    (M102/M103). Y el rojo del gate tenía razón: fue exactamente esto.
    """
    _limpiar()
    antes, _ = _resumen(app)
    _legajo("DEMO-ZZ0001", dias_atras=26)
    res, ordenes = _resumen(app)
    mios = [o for o in ordenes
            if (o.get("lote_bulk") or o.get("lote") or "").startswith("DEMO-ZZ")]
    assert mios, "el demo desapareció de la lista: tiene que verse, marcado"
    assert mios[0]["es_demo"] is True, mios[0]
    assert res["demos"] == antes["demos"] + 1, (antes, res)
    # el demo NO mueve los indicadores de producción real
    assert res["abiertas"] == antes["abiertas"], (
        "el demo cuenta como orden abierta: %s -> %s" % (antes, res))
    assert res["atrasadas"] == antes["atrasadas"], (
        "el demo cuenta como atrasada hace 26 días: %s -> %s" % (antes, res))


def test_una_orden_real_si_cuenta(app, db_clean):
    """El borde que hace que el arreglo no apague el indicador de verdad (M96)."""
    _limpiar()
    antes, _ = _resumen(app)
    _legajo("ZDEM-REAL-1", dias_atras=9)
    res, _ = _resumen(app)
    assert res["abiertas"] == antes["abiertas"] + 1, (
        "dejó de contar una orden real: %s -> %s" % (antes, res))
    assert res["atrasadas"] == antes["atrasadas"] + 1, (
        "dejó de marcar una orden real atrasada: %s -> %s" % (antes, res))


def test_el_total_declara_lo_que_dejo_afuera(app, db_clean):
    """Un total que excluye cosas sin nombrarlas se lee como un faltante (M148)."""
    _limpiar()
    _legajo("DEMO-ZZ0002", dias_atras=5)
    _legajo("ZDEM-REAL-2", dias_atras=1)
    res, ordenes = _resumen(app)
    assert "demos" in res and "total_con_demos" in res, res.keys()
    # La base es compartida y otros archivos siembran acá, así que se verifica la
    # RELACIÓN, no un número absoluto: un test que fija totales de una tabla común pasa
    # aislado y falla en el gate (M102/M103).
    assert res["total_con_demos"] == res["total"] + res["demos"], res
    assert res["demos"] == sum(1 for o in ordenes if o.get("es_demo")), res
    assert res["total"] == sum(1 for o in ordenes if not o.get("es_demo")), res


def test_la_pantalla_marca_el_demo_y_lo_explica(app, db_clean):
    """Sin la marca, la fila se lee como una orden real parada hace semanas (M115)."""
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    # ⚠ El JS del dashboard vive en los bundles, no inline: mirar sólo el HTML concluye
    # que la marca no existe (M166).
    js = ""
    for ruta in ("/planta-app.js", "/planta-core.js"):
        r = c.get(ruta)
        assert r.status_code == 200, ruta
        js += r.data.decode("utf-8")
    assert "demoChip" in js, "no marca la fila del demo"
    # El texto viaja partido por la concatenación de JS ('que no ' + 'suman a...'), así
    # que se busca el fragmento contiguo, no la frase completa.
    assert "suman a los indicadores" in js, (
        "no dice que los demos quedaron fuera de los números")
