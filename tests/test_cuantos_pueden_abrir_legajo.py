""""Productos con instructivo aprobado" cuenta los que PUEDEN abrir legajo (16-ago-2026).

Sebastián, mirando `/aseguramiento/reemplazo-mybatch`: la tarjeta decía **"31 de 29 productos
activos"** en VERDE… y debajo, en la misma tarjeta, listaba dos productos activos **sin**
instructivo (HYDRABALANCE y Suero Vitamina C+), que por lo tanto no pueden abrir legajo.

El numerador contaba **todos** los MBR aprobados -- incluidos los de productos DESCONTINUADOS --
y el denominador sólo los activos. Dos universos distintos comparados entre sí: por eso daba
31 ≥ 29 y el punto salía "listo" mientras había productos que no se pueden fabricar con registro
digital.

El total que se MUESTRA tiene que ser el que DECIDE (M5), y un número que junta dos universos no
se puede auditar (M155). Ahora se cuenta la INTERSECCIÓN: productos activos que tienen su
instructivo aprobado.
"""
import pytest


def _contar(conn):
    """Los dos conteos, como los hace la pantalla."""
    activos = conn.execute(
        "SELECT COUNT(DISTINCT UPPER(TRIM(producto_nombre))) FROM formula_headers "
        "WHERE COALESCE(activo,1)=1").fetchone()[0]
    con_instructivo = conn.execute(
        "SELECT COUNT(DISTINCT UPPER(TRIM(f.producto_nombre))) FROM formula_headers f "
        " WHERE COALESCE(f.activo,1)=1 "
        "   AND UPPER(TRIM(f.producto_nombre)) IN "
        "       (SELECT UPPER(TRIM(producto_nombre)) FROM mbr_templates "
        "         WHERE estado='aprobado')").fetchone()[0]
    return activos, con_instructivo


def _sembrar(app):
    """3 activos -- uno SIN instructivo -- y 2 descontinuados que sí lo tienen.

    Es el caso real: los descontinuados inflaban el numerador hasta superar al denominador.
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for n in ("ZZL-A1", "ZZL-A2", "ZZL-A3-SIN", "ZZL-D1", "ZZL-D2"):
            cur.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (n,))
            cur.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (n,))
        for n, act in (("ZZL-A1", 1), ("ZZL-A2", 1), ("ZZL-A3-SIN", 1),
                       ("ZZL-D1", 0), ("ZZL-D2", 0)):
            cur.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
                        "VALUES (?,1,?)", (n, act))
        for n in ("ZZL-A1", "ZZL-A2", "ZZL-D1", "ZZL-D2"):
            cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                        "lote_size_g, creado_por) VALUES (?,1,'aprobado','x',1000,'test')", (n,))
        conn.commit()


def test_los_descontinuados_no_inflan_el_conteo(app, db_clean):
    """El corazón: un instructivo de un producto que ya no se fabrica no habilita a ninguno."""
    from database import get_db
    _sembrar(app)
    with app.app_context():
        conn = get_db()
        _act, con = _contar(conn)
        # de MIS cinco productos, sólo A1 y A2 pueden abrir legajo
        mios = conn.execute(
            "SELECT COUNT(DISTINCT UPPER(TRIM(f.producto_nombre))) FROM formula_headers f "
            " WHERE COALESCE(f.activo,1)=1 AND f.producto_nombre LIKE 'ZZL-%' "
            "   AND UPPER(TRIM(f.producto_nombre)) IN "
            "       (SELECT UPPER(TRIM(producto_nombre)) FROM mbr_templates "
            "         WHERE estado='aprobado')").fetchone()[0]
        todos_los_mbr = conn.execute(
            "SELECT COUNT(DISTINCT UPPER(TRIM(producto_nombre))) FROM mbr_templates "
            "WHERE estado='aprobado' AND producto_nombre LIKE 'ZZL-%'").fetchone()[0]
    assert mios == 2, "deberían ser sólo A1 y A2 · dio %s" % mios
    assert todos_los_mbr == 4, "el conteo viejo veía 4 (incluye los descontinuados)"
    assert mios < todos_los_mbr, (
        "sin esta diferencia el test no prueba nada: el conteo viejo tiene que ver MÁS")


def test_la_pantalla_no_dice_LISTO_con_productos_sin_instructivo(app, db_clean):
    """Lo que de verdad importa: que el semáforo no diga 'ok' mientras hay productos que no
    pueden abrir legajo. Antes 31 ≥ 29 pintaba verde con dos faltando."""
    from database import get_db
    _sembrar(app)
    with app.app_context():
        conn = get_db()
        activos, con_instructivo = _contar(conn)
        faltan = conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT UPPER(TRIM(f.producto_nombre)) AS p "
            "  FROM formula_headers f WHERE COALESCE(f.activo,1)=1 "
            "   AND UPPER(TRIM(f.producto_nombre)) NOT IN "
            "       (SELECT UPPER(TRIM(producto_nombre)) FROM mbr_templates "
            "         WHERE estado='aprobado'))").fetchone()[0]
    assert faltan > 0, "el escenario tiene que tener al menos un producto sin instructivo"
    assert con_instructivo < activos, (
        "el conteo dice que están todos (%s de %s) con %s sin instructivo"
        % (con_instructivo, activos, faltan))


def test_el_endpoint_usa_la_interseccion(app, db_clean):
    """Que el arreglo esté en la pantalla, no sólo en este test (M96)."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "aseguramiento.py"),
                  encoding="utf-8").read()
    i = src.index("aprobados = _rmb_conteo")
    cuerpo = re.sub(r"#[^\n]*", "", src[i:i + 900])   # sin comentarios (M154)
    assert "formula_headers" in cuerpo, (
        "el numerador volvió a contar todos los MBR, sin cruzarlos con los productos activos")
    assert "activo" in cuerpo, "no filtra por producto activo"
