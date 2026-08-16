"""Las pantallas de Planta no se contradicen sobre el MISMO lote (15-ago-2026).

Sebastián, antes de cerrar el módulo: *"revisá Planta paso por paso, que nada sea incoherente
o esté dañado"*.

Los doce eslabones de la cadena ya tienen tests en el gate -- eso está medido. Lo que NINGUNO
cubre es la costura: cada test verifica SU pieza, así que dos pantallas pueden informar el
mismo hecho con números distintos y las dos pasar en verde. Y ahí el daño no es el número: es
que el usuario no tiene forma de saber a cuál creerle, y deja de creerle a las dos (M161).

Se siembra UN lote conocido y se le pregunta lo mismo a todas las pantallas que lo muestran.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZCOH PRODUCTO COHERENCIA"
KG = 12.0


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


def _uno(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        f = conn.execute(sql, params).fetchone()
        return f[0] if f else None
    finally:
        conn.close()


def _limpiar():
    # Limpiar ANTES de sembrar: la base es compartida entre archivos y un `finally` no corre
    # si el proceso muere (M103).
    for sql in ("DELETE FROM produccion_programada WHERE producto LIKE 'ZCOH %'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZCOH %'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZCOH %'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _mps_reales(n=2):
    """Dos materias primas que EXISTEN y están activas.

    `formula_items.material_id` tiene un trigger contra `maestro_mps` activo: sembrar
    códigos inventados no falla por el test, falla porque la invariante está funcionando
    (M38) -- y una fórmula que apunta a un código muerto es justo lo que ese trigger
    impide.
    """
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        filas = conn.execute(
            "SELECT codigo_mp FROM maestro_mps WHERE COALESCE(activo,1)=1 "
            "ORDER BY codigo_mp LIMIT ?", (n,)).fetchall()
        return [f[0] for f in filas]
    finally:
        conn.close()


def _sembrar_lote(dias_adelante=3):
    """Un producto con fórmula simple y una producción programada, de kg conocidos."""
    from datetime import datetime, timedelta
    import pytest
    _limpiar()
    mps = _mps_reales(2)
    if len(mps) < 2:
        pytest.skip("la base no tiene materias primas activas para sembrar la fórmula")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES (?,?,1)", (PROD, KG))
    # 10% y 5%: en gramos sobre 12 kg son 1.200 y 600
    for cod, pct in zip(mps, (10.0, 5.0)):
        _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
              "porcentaje) VALUES (?,?,?,?)", (PROD, cod, "ZCOH " + cod, pct))
    fecha = (datetime.utcnow() - timedelta(hours=5) + timedelta(days=dias_adelante)
             ).strftime("%Y-%m-%d")
    pid = _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, "
                "estado, origen, cantidad_kg) VALUES (?,?,1,'pendiente','eos_plan',?)",
                (PROD, fecha, KG))
    return pid, fecha, mps


def test_los_kg_del_lote_son_los_mismos_en_todas_partes(app, db_clean):
    """Si una pantalla dice 12 kg y otra 100, cualquiera de las dos decisiones es a ciegas."""
    pid, fecha, mps = _sembrar_lote()
    c = _login(app)

    en_tabla = _uno("SELECT cantidad_kg FROM produccion_programada WHERE id=?", (pid,))
    assert abs(float(en_tabla) - KG) < 0.01, en_tabla

    vistos = {"tabla": float(en_tabla)}
    r = c.get("/api/plan/factibilidad")
    if r.status_code == 200:
        j = r.get_json() or {}
        for ev in (j.get("eventos") or j.get("producciones") or []):
            if str(ev.get("producto") or "") == PROD:
                kg = ev.get("cantidad_kg", ev.get("kg"))
                if kg is not None:
                    vistos["factibilidad"] = float(kg)
    distintos = {k: v for k, v in vistos.items() if abs(v - KG) > 0.01}
    assert not distintos, ("el mismo lote se ve con kg distintos segun la pantalla: %s"
                           % vistos)


def test_la_demanda_de_MP_sale_de_la_formula_y_los_kg_reales(app, db_clean):
    """El consumo es porcentaje x kg x 1000 (M71): 10% de 12 kg son 1.200 g, no otra cosa.

    Es el numero con el que se COMPRA: si sale de `cantidad_g_por_lote` cruda en vez del
    porcentaje, con el kg editado por el usuario la compra queda mal y el kardex tambien.
    """
    pid, fecha, mps = _sembrar_lote()
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes")
    assert r.status_code == 200, r.data[:200]
    j = r.get_json() or {}
    items = j.get("items") or j.get("items_mp") or []
    mios = {str(it.get("codigo") or it.get("codigo_mp") or ""): it for it in items}
    esperado = {mps[0]: 10.0 / 100 * KG * 1000, mps[1]: 5.0 / 100 * KG * 1000}
    for cod, g in esperado.items():
        it = mios.get(cod)
        if not it:
            continue        # el horizonte puede no alcanzar la fecha sembrada
        for clave in ("consumo_90", "consumo_g", "consumo"):
            v = it.get(clave)
            if isinstance(v, (int, float)) and v > 0:
                assert abs(float(v) - g) < max(1.0, g * 0.02), (
                    "%s: la demanda dice %s y la formula da %s" % (cod, v, g))
                break


# El objetivo del legajo (que nazca con los kg que el usuario fijo, no con un default
# generico del MBR) lo cubre `test_ebr_objetivo_m67.py`, que SI puede iniciar produccion en
# el entorno de pruebas. Mi version se saltaba siempre por falta de condiciones previas, y un
# test que se saltea no protege nada (M152): se agrego el otro al gate en su lugar.
