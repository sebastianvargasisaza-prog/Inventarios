# -*- coding: utf-8 -*-
"""El tablero del Director Técnico contaba de una tabla que nadie escribe · 19-ago.

Sebastián pidió revisar Dirección Técnica. Todos sus indicadores en cero, y el de
documentos era el único que MENTÍA:

    DOCS SGD VIGENTES: 0        <- el DT
    Sistema documental: 2       <- Aseguramiento, el mismo día, el mismo hecho

El sistema documental vive en `sgd_documentos`. `documentos_sgd` es la tabla LEGACY,
y lo dice el propio código de este archivo:

    # Migracion one-shot · documentos_sgd legacy → sgd_documentos rico.

Desde esa migración nadie la escribe (0 INSERT en todo el repo) -- pero el dashboard
del DT y el cron de vencimientos del SGD le seguían preguntando a ella. O sea que el
DT veía cero documentos y **la alerta de "documentos por revisar" nunca pudo sonar**:
consultaba una tabla vacía (M127 · una integración que enmudece se ve igual que una
que no tiene nada que decir).

Es el tercer número de la noche con la misma forma: un criterio que una migración ya
jubiló, sirviendo el valor más tranquilizador. Los otros dos fueron el estado
`Revisada` del CEO (mig 157) y la llave `monto` de los pagos a creadores.

Los guards NO miden la fórmula: miden que el DT y el módulo dueño digan lo mismo, y
que ningún tablero vuelva a contar de la tabla muerta.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, ("no pudo entrar %s" % user)
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM sgd_documentos WHERE codigo LIKE 'ZDT-%'")
        cn.commit()
    finally:
        cn.close()


def _sembrar(codigo, estado, proxima):
    cn = _cn()
    try:
        cn.execute("INSERT INTO sgd_documentos (codigo, area, tipo_doc, numero, "
                   "titulo, version_actual, estado, vigente_desde, proxima_revision, "
                   "creado_por) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (codigo, 'ASG', 'PRO', 90, 'ZDT documento de prueba', '01',
                    estado, '2025-01-01', proxima, 'guard'))
        cn.commit()
    finally:
        cn.close()


def _dash(cli):
    r = cli.get('/api/tecnica/dashboard')
    assert r.status_code == 200, ("el tablero del DT no abre", r.status_code)
    return r.get_json() or {}


def test_el_DT_y_ASEGURAMIENTO_cuentan_igual_los_documentos_vigentes(app, db_clean):
    """La invariante: dos pantallas del mismo hecho no pueden dar números distintos.

    Si mañana el SGD se muda otra vez de tabla, esto falla igual -- no está atado al
    nombre de la tabla ni a la forma de la consulta (M150/M161).
    """
    _limpiar()
    _sembrar('ZDT-001', 'vigente', '2030-01-01')
    try:
        cli = _cli(app)
        dt = _dash(cli).get('docs_vigentes')
        lst = (cli.get('/api/aseguramiento/sgd/listado?estado=vigente')
               .get_json() or {})
        dueno = len(lst.get('items') or [])
        assert dt is not None, "el tablero del DT dejó de publicar docs_vigentes"
        assert int(dt) == int(dueno), (
            "el Director Técnico y Aseguramiento cuentan distinto el sistema "
            "documental · el DT está leyendo la tabla legacy que nadie escribe",
            {'dt': dt, 'aseguramiento': dueno})
        assert int(dt) >= 1, ("con un documento vigente sembrado el DT sigue en cero",
                              dt)
    finally:
        _limpiar()


def test_un_documento_por_vencer_aparece_como_POR_REVISAR(app, db_clean):
    """El aviso que nunca pudo sonar: la tabla que consultaba estaba vacía."""
    _limpiar()
    _sembrar('ZDT-002', 'vigente', "2000-01-01")   # vencidísimo → entra al aviso
    try:
        d = _dash(_cli(app))
        assert int(d.get('docs_revisar') or 0) >= 1, (
            "un documento con la revisión vencida no aparece como pendiente de "
            "revisar · el indicador cuenta de una tabla muerta", d.get('docs_revisar'))
    finally:
        _limpiar()


def test_un_documento_OBSOLETO_no_cuenta_como_vigente(app, db_clean):
    """El borde que impide que el arreglo infle el número (M96)."""
    _limpiar()
    cli = _cli(app)
    base = int(_dash(cli).get('docs_vigentes') or 0)
    _sembrar('ZDT-003', 'obsoleto', '2030-01-01')
    try:
        assert int(_dash(cli).get('docs_vigentes') or 0) == base, (
            "un documento obsoleto se está contando como vigente")
    finally:
        _limpiar()


def test_ningun_tablero_cuenta_de_la_tabla_LEGACY(app, db_clean):
    """La razón vive en el CÓDIGO, así que se mide sobre el fuente (M227).

    Un barrido de datos no sirve acá: la tabla legacy está vacía, así que consultarla
    devuelve cero sin error y el tablero se ve sano. Lo que hay que impedir es que
    alguien vuelva a ESCRIBIR una consulta contra ella.

    La única excepción es la migración one-shot que la vacía hacia `sgd_documentos`:
    esa TIENE que leerla. Se identifica por su bloque, no por su archivo.
    """
    import io
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    culpables = []
    for sub, arch in (('blueprints', None),):
        base = os.path.join(raiz, "api", sub)
        for nombre in sorted(os.listdir(base)):
            if not nombre.endswith(".py"):
                continue
            src = io.open(os.path.join(base, nombre), encoding="utf-8").read()
            # sin comentarios: la explicación de por qué NO se usa menciona la tabla
            # y el guard se encontraría a sí mismo (M154, otra vez).
            sin_com = "\n".join(l for l in src.splitlines()
                                if not l.strip().startswith("#"))
            for m in re.finditer(r"FROM\s+documentos_sgd", sin_com, re.I):
                ctx = sin_com[max(0, m.start() - 700):m.start()]
                # la migración one-shot es la única lectura legítima
                if "legacy_rows" in ctx or "one-shot" in ctx.lower():
                    continue
                culpables.append("%s: %s" % (nombre, ctx.splitlines()[-1][:60]))
    assert not culpables, (
        "hay tableros/crons contando de `documentos_sgd`, la tabla legacy que la "
        "migración vació y que nadie escribe · su cero se lee como 'no hay "
        "documentos': %s" % culpables)
