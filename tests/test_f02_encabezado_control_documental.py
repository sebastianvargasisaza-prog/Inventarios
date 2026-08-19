# -*- coding: utf-8 -*-
"""El F02 digital no replicaba el encabezado de control documental · 19-ago-2026.

Aseguramiento: la version HTML del PRD-PRO-002-F02 habia reemplazado el encabezado
oficial por un bloque de metadatos suelto, y *"este encabezado no es decorativo: es la
evidencia de que el documento usado corresponde a la version vigente y autorizada"*
(ISO 22716 · Res. 2214/2021 · BPM cosmetica INVIMA).

La estructura es la misma en TODOS los formatos de Espagiria y tiene tres zonas fijas:

    [ logo + nombre ] | [ FORMATO / titulo ] | [ Codigo · Version · Pagina · Vigencia ]

Lo que estaba mal, en concreto: el titulo vivia FUERA del encabezado y sin la etiqueta
`FORMATO`, y la vigencia estaba resumida en un rango de una linea ("9-Abr-2026 a
8-Abr-2029") en vez de sus dos subcampos `Desde:` y `Hasta:`.

⚠ Se mide sobre las DOS pantallas que imprimen este formato: el rotulo operativo y el
snapshot inmutable que va al expediente del lote -- que es justamente el que se le
muestra a INVIMA, y tenia su PROPIO encabezado distinto (M45: el mismo formato con dos
estructuras es el formato sin estructura).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

# Las etiquetas son EXACTAS: Aseguramiento las declaro no negociables.
ETIQUETAS = ('FORMATO', 'Código:', 'Versión:', 'Página:', 'Vigencia:', 'Desde:', 'Hasta:')


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _registro_historico():
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)
    try:
        cn.execute("DELETE FROM rotulos_limpieza WHERE producto_elaborar='ZF02 GUARD'")
        cn.execute("INSERT INTO rotulos_limpieza (area_id, area_codigo, producto_elaborar, "
                   "lote_elaborar, estado, realizado_por, realizado_at) VALUES "
                   "(1,'FAB1','ZF02 GUARD','L-1','limpio','guard','2026-08-19 10:00:00')")
        cn.commit()
        return cn.execute("SELECT id FROM rotulos_limpieza "
                          "WHERE producto_elaborar='ZF02 GUARD'").fetchone()[0]
    finally:
        cn.close()


def _limpiar():
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)
    try:
        cn.execute("DELETE FROM rotulos_limpieza WHERE producto_elaborar='ZF02 GUARD'")
        cn.commit()
    finally:
        cn.close()


def test_las_DOS_pantallas_del_F02_llevan_el_encabezado_oficial(app, db_clean):
    cli = _cli(app)
    rid = _registro_historico()
    try:
        pantallas = {
            'rotulo operativo': '/planta/rotulos-limpieza?todos=1',
            'snapshot del expediente': '/planta/rotulo-limpieza/registro/%d/pdf' % rid,
        }
        problemas = {}
        medidas = 0
        for nombre, url in pantallas.items():
            r = cli.get(url, follow_redirects=True)
            if r.status_code != 200:
                problemas[nombre] = 'no abre (%s)' % r.status_code
                continue
            html = r.get_data(as_text=True)
            medidas += 1
            faltan = [e for e in ETIQUETAS if e not in html]
            if faltan:
                problemas[nombre] = {'etiquetas_faltantes': faltan}
            # las tres zonas
            for zona in ('brand', 'doc', 'ctrl'):
                if ('class="%s"' % zona) not in html and ("class='%s'" % zona) not in html:
                    problemas.setdefault(nombre, {}).setdefault('zonas_faltantes', []).append(zona)
        assert medidas == 2, (
            "no se pudieron medir las dos pantallas (%d de 2) · un guard que no abre lo "
            "que revisa pasa verde por omision (M210)" % medidas, problemas)
        assert not problemas, (
            "el encabezado de control documental no cumple el estandar de Espagiria · "
            "es la evidencia de que se esta usando la version vigente: %s" % problemas)
    finally:
        _limpiar()


def test_la_vigencia_NO_se_resume_en_una_sola_fecha(app, db_clean):
    """Aseguramiento fue explicito: no resumir Vigencia ni omitir el rango."""
    cli = _cli(app)
    html = cli.get('/planta/rotulos-limpieza?todos=1',
                   follow_redirects=True).get_data(as_text=True)
    i = html.find('Vigencia:')
    assert i > 0, "desaparecio la etiqueta Vigencia"
    ventana = html[i:i + 400]
    assert 'Desde:' in ventana and 'Hasta:' in ventana, (
        "la vigencia no lleva sus dos subcampos pegados · quedo resumida",
        ventana[:160])


def test_los_datos_de_control_salen_de_UN_solo_sitio(app, db_clean):
    """Dos copias divergen, y ahi el documento deja de probar de que version es (M3).

    El rotulo operativo y el snapshot imprimen el MISMO formato: si cada uno declara su
    propio codigo/version/vigencia, el dia que Aseguramiento libere la version 03 uno de
    los dos sigue diciendo 02 -- y los dos se ven igual de oficiales.
    """
    import io
    import re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "programacion.py")
    src = io.open(ruta, encoding="utf-8").read()
    sin_com = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    # La invariante que importa: las DOS pantallas arman su encabezado con el MISMO
    # helper. Contar apariciones del codigo no sirve -- hay otra hoja ("Despeje de
    # linea") que tambien lo menciona, y si eso es un rotulo equivocado lo decide
    # Aseguramiento, no este guard (M19: lo ambiguo se reporta, no se adivina).
    n = len(re.findall(r"_encabezado_formato_zonas" + re.escape("("), sin_com))
    assert n >= 3, (
        "las dos pantallas del F02 tienen que armar su encabezado con el helper "
        "canonico (1 definicion + 2 usos); se encontraron %d referencias" % n)
    from api.blueprints.programacion import F02_CONTROL
    for k in ('codigo', 'titulo', 'version', 'pagina', 'desde', 'hasta'):
        assert str(F02_CONTROL.get(k) or '').strip(), (
            "el bloque de control documental no declara '%s'" % k)


def test_ningun_formato_impreso_resume_la_vigencia(app, db_clean):
    """La regla vale para TODOS los formatos, no solo para el F02.

    Aseguramiento: *"no resumir Vigencia en una sola fecha ni omitir el rango"*. El
    rotulo de dispensacion (PRD-PRO-001-F08) la traia colapsada como
    "04-Mar-2025 / 03-Mar-2028".

    NO se exige aca el layout de tres zonas: para ese rotulo Sebastian pidio (30-jul) el
    titulo chico y al costado, porque lo que el operario lee de lejos en la bascula es la
    materia prima y el peso. Esa tension entre el estandar de Aseguramiento y el uso real
    la deciden ellos; el guard mide lo que NO esta en discusion.
    """
    import io as _io
    import os as _os
    import re as _re
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    base = _os.path.join(raiz, "api", "blueprints")
    culpables = []
    medidos = 0
    for nombre in sorted(_os.listdir(base)):
        if not nombre.endswith(".py"):
            continue
        src = _io.open(_os.path.join(base, nombre), encoding="utf-8").read()
        sin_com = chr(10).join(l for l in src.splitlines()
                               if not l.strip().startswith("#"))
        # ⚠ `.` NO cruza saltos de linea sin DOTALL, y el HTML de estos formatos viene
        # partido en literales concatenados: sin re.S la ventana se cortaba en el primer
        # renglon y el guard acusaba a codigo correcto (el detector, no el codigo).
        for m in _re.finditer(r"<b>Vigencia:</b>(.{0,200})", sin_com, _re.S):
            medidos += 1
            cola = m.group(1)
            if "Desde:" not in cola:
                culpables.append("%s: %s" % (nombre, cola.strip()[:70]))
    assert medidos >= 1, (
        "no se encontro ningun bloque de vigencia · el guard dejo de medir (M210)")
    assert not culpables, (
        "hay formatos impresos que resumen la vigencia en vez de declarar Desde/Hasta · "
        "Aseguramiento lo declaro no negociable: %s" % culpables)
