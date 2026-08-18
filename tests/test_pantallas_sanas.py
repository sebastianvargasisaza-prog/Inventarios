# -*- coding: utf-8 -*-
"""Dos invariantes de salud de las pantallas grandes, medidas y no supuestas.

Salió de la revisión módulo por módulo del 18-ago (Planta · Calidad · Compras · CEO). Las dos
cosas que se miden acá son las que se rompen en silencio: nadie reporta un botón que no hace
nada, ni una pantalla que hace 200 consultas.

1. **Ningún `fetch` del frontend apunta a una ruta que no existe.** Un endpoint que se renombró
   deja el botón mudo: no hay error, no hay log, y desde afuera se ve como que "no funciona"
   (M166/M202).

2. **Las pantallas de lectura no tienen N+1.** Lo que delata un N+1 no es el reloj -- con datos
   de juguete no se mueve -- sino que el CONTEO de consultas crezca con las filas (M167/M216).

⚠ Los dos guards se caen si dejan de encontrar su objeto: un barrido que no puede medir lo que
revisa pasa verde por omisión, que es peor que un rojo (M158/M210).
"""
import os
import re
import sqlite3
import sys

from .conftest import TEST_PASSWORD, csrf_headers

PANTALLAS = ["/inventarios", "/calidad", "/compras", "/aseguramiento", "/hoy", "/tesoreria"]

# fetch("/algo") seguido de , o ) · sólo literales COMPLETOS. Si la URL se arma concatenando
# (`fetch('/api/x/' + id)`), el prefijo suelto no prueba nada y reportarlo es ruido (M170).
PAT_FETCH = re.compile(r"""fetch\(\s*(['"`])(/[^'"`]+)\1\s*[,)]""")

LECTURA = ["/api/plan/necesidades", "/api/calidad/indicadores", "/api/calidad/bandeja",
           "/api/centro/decisiones", "/api/inventario", "/api/indicadores/despachos"]


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _servido(cli, ruta):
    h = cli.get(ruta).get_data(as_text=True)
    for src in set(re.findall(r'<script[^>]+src="(/[^"]+\.js[^"]*)"', h)):
        rb = cli.get(src)
        if rb.status_code == 200:
            h += rb.get_data(as_text=True)
    return h


def test_ningun_boton_llama_a_una_ruta_que_no_existe(app, db_clean):
    cli = _login(app)
    def _rx(regla):
        # ⚠ El ORDEN importa: `<path:filename>` cruza barras (`/static/scripts/x.json`), así
        # que va PRIMERO. Con la sustitución genérica adelante, `<path:...>` ya quedó
        # convertido en algo que no cruza `/` y el archivo estático se reporta como ruta
        # inexistente -- un falso positivo que ensucia la lista entera (M170).
        r = re.sub(r"<path:[^>]+>", "@@PATH@@", str(regla))
        r = re.sub(r"<[^>]+>", "[^/]+", r)
        return re.compile("^" + r.replace("@@PATH@@", ".+") + "$")

    reglas = [_rx(r.rule) for r in app.url_map.iter_rules()]
    muertas, total = {}, 0
    for ruta in PANTALLAS:
        urls = {m.group(2) for m in PAT_FETCH.finditer(_servido(cli, ruta))}
        urls = {u for u in urls if "${" not in u}
        total += len(urls)
        malas = [u for u in sorted(urls)
                 if not any(rg.match(re.sub(r"/\d+(?=/|$)", "/1", u.split("?")[0].rstrip("/")))
                            for rg in reglas)]
        if malas:
            muertas[ruta] = malas
    assert total >= 200, (
        "el detector encontró muy pocas llamadas (%d): dejó de medir lo que revisa" % total)
    assert not muertas, ("hay botones llamando a rutas que no existen: %s" % muertas)


def test_las_pantallas_de_lectura_no_tienen_N_mas_1(app, db_clean):
    """El costo no puede crecer con las filas."""
    cli = _login(app)

    def _consultas(ruta):
        n = [0]
        orig = sqlite3.connect

        def _conn(*a, **k):
            c = orig(*a, **k)
            try:
                c.set_trace_callback(lambda _s: n.__setitem__(0, n[0] + 1))
            except Exception:
                pass
            return c
        # ⚠ Se engancha `sqlite3.connect`, NO `database.get_db`: los blueprints hacen
        # `from database import get_db`, así que se quedan con la referencia original y un
        # espía puesto ahí no corre nunca -- daba 0 consultas en TODAS las pantallas, que se
        # lee igual que "no consulta" (M170).
        sqlite3.connect = _conn
        try:
            cli.get(ruta)
        finally:
            sqlite3.connect = orig
        return n[0]

    antes = {r: _consultas(r) for r in LECTURA}
    assert sum(antes.values()) > 0, "no se midió ninguna consulta: el espía no está enganchado"

    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)
    try:
        cn.execute("DELETE FROM movimientos WHERE material_id LIKE 'ZNP%'")
        cn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZNP-%'")
        for i in range(60):
            cn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                       "VALUES (?,?,1)", ("ZNP%03d" % i, "NmasUno %d" % i))
            cn.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                       "lote, fecha, estado_lote, operador) VALUES (?,?,'Entrada',1000,?,"
                       "date('now','-5 hours'),'VIGENTE','guard')",
                       ("ZNP%03d" % i, "NmasUno %d" % i, "ZNPL%03d" % i))
            cn.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, estado, "
                       "estado_pago, creado_en) VALUES (?,?,100,'','paid',"
                       "date('now','-5 hours'))", ("ZNP-%03d" % i, "n%d" % i))
        cn.commit()
    finally:
        cn.close()

    crecen = {}
    for r in LECTURA:
        d = _consultas(r) - antes[r]
        if d > 5:      # margen para lo que legítimamente depende de 1-2 lecturas más
            crecen[r] = "de %d a %d consultas con 60 filas más" % (antes[r], antes[r] + d)
    assert not crecen, (
        "el costo crece con los datos · eso es un N+1 y con la tabla real satura los tres "
        "workers (M43): %s" % crecen)
