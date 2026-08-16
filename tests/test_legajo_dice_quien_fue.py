"""El legajo dice QUIÉN, no el cargo · y nunca el nombre de otra persona (16-ago-2026).

Sebastián, mirando el legajo de envasado: *"sale el cargo sin la persona · tú tienes el
nombre de cada jefe, ellos se loguean"*.

Tenía razón a medias: los nombres están cargados, pero repartidos en tres tablas y ninguna
es la que el legajo miraba. `usuarios_identidad` tiene a los 18 que entran a la app con su
CARGO y el `nombre_completo` vacío en todos; los nombres reales viven en `empleados` (19
personas) y en `operarios_planta`. Por eso el batch record imprimía «Supervisado por: Jefe
de Producción» -- el cargo solo, que como firma en un registro regulado no dice nada.

⚠ Y el arreglo obvio (emparejar por nombre de pila) es peligroso, lo comprobé al probarlo:
resolvió `sebastian` a **Sebastian Murillo**, el operario de envasado, en vez de Sebastián
Vargas. Poner el nombre de alguien que no ejecutó el acto es peor que no poner ninguno: es
una firma falsa (M193/M177). Con nombre repetido no se elige.
"""
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _conn():
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    cn.row_factory = sqlite3.Row
    return cn


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def test_resuelve_el_nombre_de_quien_esta_cargado(app):
    """Los que tienen nombre en `empleados` salen con nombre y apellido."""
    from blueprints.identidad import nombre_de
    cn = _conn()
    try:
        hay = cn.execute("SELECT COUNT(*) FROM empleados").fetchone()[0]
        if not hay:
            pytest.skip("la base no tiene empleados cargados")
        # alguien inequívoco: nombre de pila que aparece una sola vez
        fila = cn.execute(
            "SELECT nombre, COALESCE(apellido,'') ap FROM empleados "
            "WHERE COALESCE(apellido,'')<>'' ORDER BY id").fetchall()
        nombres = [f["nombre"].split()[0].lower() for f in fila]
        unico = None
        for f in fila:
            pila = f["nombre"].split()[0].lower()
            if nombres.count(pila) == 1:
                unico = (pila, (f["nombre"] + " " + f["ap"]).strip())
                break
        if not unico:
            pytest.skip("no hay ningún nombre de pila inequívoco para probar")
        usuario, esperado = unico
        assert nombre_de(cn, usuario) == esperado, (
            "no resolvió a %s (devolvió %r)" % (esperado, nombre_de(cn, usuario)))
    finally:
        cn.close()


def test_con_el_nombre_repetido_NO_elige(app):
    """El borde que evita firmar con el nombre de otro.

    En esta casa hay tres personas cuyo nombre de pila es Sebastián: el CEO y dos operarios.
    Adivinar puso al operario de envasado como responsable de un lote ajeno.
    """
    from blueprints.identidad import nombre_de
    cn = _conn()
    try:
        # se siembran dos personas con el mismo nombre de pila
        cn.execute("DELETE FROM empleados WHERE COALESCE(codigo,'') LIKE 'ZDUP%'")
        for i, ape in enumerate(("Perez Uno", "Gomez Dos"), 1):
            cn.execute(
                "INSERT INTO empleados (codigo, nombre, apellido, cedula, cargo) "
                "VALUES (?,?,?,?,?)", ("ZDUP%d" % i, "Zutano", ape, "ZDUP%d" % i, "Operario"))
        cn.commit()
        assert nombre_de(cn, "zutano") == "", (
            "con dos personas del mismo nombre eligió una: %r" % nombre_de(cn, "zutano"))
        # y con una sola, sí resuelve
        cn.execute("DELETE FROM empleados WHERE codigo='ZDUP2'")
        cn.commit()
        assert nombre_de(cn, "zutano") == "Zutano Perez Uno", nombre_de(cn, "zutano")
    finally:
        try:
            cn.execute("DELETE FROM empleados WHERE COALESCE(codigo,'') LIKE 'ZDUP%'")
            cn.commit()
        except Exception:
            pass
        cn.close()


def test_no_devuelve_a_alguien_dado_de_baja(app):
    """`operarios_planta` marca los inactivos: el jefe de producción anterior está dado de
    baja, y un legajo firmado por quien ya no trabaja acá es peor que uno sin nombre."""
    from blueprints.identidad import nombre_de
    cn = _conn()
    try:
        cn.execute("DELETE FROM operarios_planta WHERE nombre='Zmengano'")
        cn.execute("INSERT INTO operarios_planta (nombre, apellido, activo) "
                   "VALUES ('Zmengano','Retirado',0)")
        cn.commit()
        assert nombre_de(cn, "zmengano") == "", (
            "devolvió a alguien inactivo: %r" % nombre_de(cn, "zmengano"))
    finally:
        try:
            cn.execute("DELETE FROM operarios_planta WHERE nombre='Zmengano'")
            cn.commit()
        except Exception:
            pass
        cn.close()


def test_sin_nombre_cargado_el_legajo_lo_DICE(app):
    """Un cargo solo se lee como si esa fuera la firma. Si falta el nombre, se declara."""
    cn = _conn()
    try:
        r = cn.execute("SELECT id FROM ebr_ejecuciones ORDER BY id DESC LIMIT 1").fetchone()
        if not r:
            pytest.skip("no hay legajos en la base de pruebas")
        ebr = r["id"]
    finally:
        cn.close()
    c = _login(app)
    resp = c.get("/api/brd/ebr/%d/vista-completa" % ebr)
    if resp.status_code != 200:
        pytest.skip("el legajo %s no abre en este entorno: %s" % (ebr, resp.status_code))
    sup = ((resp.get_json() or {}).get("header") or {}).get("supervisado_por") or ""
    if not sup:
        pytest.skip("este legajo no tiene supervisor resuelto")
    # o trae un nombre, o dice que falta · nunca el cargo pelado como si fuera la firma
    assert ("falta cargar el nombre" in sup) or ("," in sup), (
        "el supervisor sale como cargo pelado, sin nombre ni aviso: %r" % sup)
