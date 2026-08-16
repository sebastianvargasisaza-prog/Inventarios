"""El número de lote se calcula como lo calcula la planta (16-ago-2026).

Sebastián: *"los números de lote ellos los calculan con una tabla especial, no sé cómo se
llama, investiga"*. La tabla es el **calendario juliano** -- el día del año, 001 a 365 -- y
la regla es:

    261621  =  26      162           1
               año     11 de junio   primer lote de ese día

Salió de sus propios batch records firmados: de los 28, veinticinco encajan exactos y las
órdenes consecutivas caen en días crecientes (OP-41 → 30 de abril, OP-101 → 22 de julio). La
prueba está en el día 183, que tiene DOS lotes (`261831` y `261832`): ahí se ve que el
último dígito es el consecutivo del día.

Hasta ahora EOS numeraba distinto en cada camino (`DEMO-<hora>`, `ESP260815xxx`,
`260815-42`), así que el número del sistema no era el que iba en el rótulo ni en el batch
record -- y el lote es la llave de toda la trazabilidad: kardex, genealogía, expediente.

Se SUGIERE, no se impone: quien fabrica puede cambiarlo. Lo que estaba mal era proponer un
formato que no existe en el rótulo.
"""
import datetime
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers

# Un lote REAL, de un batch record firmado: ANIMUSLASH, orden OP-2026-74.
LOTE_REAL = "261621"
FECHA_REAL = "2026-06-11"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _conn():
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    return cn


def _limpiar(prefijo="26162"):
    cn = _conn()
    try:
        cn.execute("DELETE FROM ebr_ejecuciones WHERE lote LIKE ?", (prefijo + "%",))
        cn.execute("DELETE FROM movimientos WHERE material_id='ZLOTETEST'")
        cn.commit()
    except Exception:
        pass
    finally:
        cn.close()


def test_el_numero_coincide_con_el_de_los_batch_records_firmados(app, db_clean):
    """El 11 de junio de 2026 tiene que dar 261621 · es el lote real de ANIMUSLASH."""
    _limpiar()
    c = _login(app)
    r = c.get("/api/brd/lote-sugerido?fecha=" + FECHA_REAL)
    assert r.status_code == 200, r.data[:200]
    j = r.get_json() or {}
    assert j.get("sugerido") == LOTE_REAL, (
        "para el %s el sistema propone %r y el batch record real dice %s"
        % (FECHA_REAL, j.get("sugerido"), LOTE_REAL))
    assert j.get("dia_juliano") == 162, j


def test_el_consecutivo_avanza_con_los_lotes_del_dia(app, db_clean):
    """Dos lotes el mismo día son `...1` y `...2` (el caso real del día 183).

    Si no avanzara, dos materiales distintos quedarían bajo la misma llave -- lo peor que le
    puede pasar a la trazabilidad.
    """
    _limpiar()
    c = _login(app)
    primero = (c.get("/api/brd/lote-sugerido?fecha=" + FECHA_REAL).get_json() or {}).get("sugerido")
    assert primero == LOTE_REAL

    cn = _conn()
    try:
        mbr = cn.execute("SELECT id FROM mbr_templates ORDER BY id DESC LIMIT 1").fetchone()
        if not mbr:
            pytest.skip("no hay MBR en la base de pruebas")
        cn.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,1,?,?,'en_proceso','fabricacion','sebastian',?,1000)",
            (mbr[0], primero, primero, FECHA_REAL + " 08:00:00"))
        cn.commit()
    finally:
        cn.close()

    segundo = (c.get("/api/brd/lote-sugerido?fecha=" + FECHA_REAL).get_json() or {}).get("sugerido")
    assert segundo == "261622", (
        "con %s ya usado debería proponer 261622 y propone %r" % (primero, segundo))
    _limpiar()


def test_tambien_mira_el_kardex(app, db_clean):
    """Un lote puede existir sólo en el kardex: si no se mira, se repite el número."""
    _limpiar()
    c = _login(app)
    primero = (c.get("/api/brd/lote-sugerido?fecha=" + FECHA_REAL).get_json() or {}).get("sugerido")
    cn = _conn()
    try:
        cn.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            "fecha, operador) VALUES ('ZLOTETEST','prueba','Entrada',1,?,?,'test')",
            (primero, FECHA_REAL))
        cn.commit()
    except Exception as e:
        pytest.skip("no se pudo sembrar en el kardex: %s" % str(e)[:80])
    finally:
        cn.close()
    segundo = (c.get("/api/brd/lote-sugerido?fecha=" + FECHA_REAL).get_json() or {}).get("sugerido")
    assert segundo != primero, (
        "un lote que sólo está en el kardex no se contó: propondría %r otra vez" % primero)
    _limpiar()


def test_el_dia_se_ancla_en_colombia(app, db_clean):
    """De noche el servidor ya está en el día siguiente (corre en UTC): sin anclar, el lote
    saldría con el juliano de mañana y no coincidiría con el rótulo (M24)."""
    c = _login(app)
    j = c.get("/api/brd/lote-sugerido").get_json() or {}
    hoy_co = (datetime.datetime.utcnow() - datetime.timedelta(hours=5)).date()
    assert j.get("dia_juliano") == hoy_co.timetuple().tm_yday, (
        "el día juliano no está anclado a Colombia: dice %s y hoy acá es %s"
        % (j.get("dia_juliano"), hoy_co.timetuple().tm_yday))


def test_cuando_el_dia_se_llena_lo_DICE(app, db_clean):
    """El formato admite 9 lotes por día. Al décimo no se inventa un dígito de más: se avisa,
    porque un lote con otro formato no coincide con el rótulo (M100/M124)."""
    from audit_helpers import lote_juliano
    _limpiar()
    cn = _conn()
    try:
        mbr = cn.execute("SELECT id FROM mbr_templates ORDER BY id DESC LIMIT 1").fetchone()
        if not mbr:
            pytest.skip("no hay MBR en la base de pruebas")
        for n in range(1, 10):
            lote = "26162%d" % n
            cn.execute(
                "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
                "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,?,?,'en_proceso','fabricacion','sebastian',?,1000)",
                (mbr[0], lote, lote, FECHA_REAL + " 08:00:00"))
        cn.commit()
        assert lote_juliano(cn.cursor(), datetime.date(2026, 6, 11)) is None, (
            "con los 9 lotes del día usados debería avisar, no inventar un número")
    finally:
        cn.close()
        _limpiar()
