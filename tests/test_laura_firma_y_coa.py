# -*- coding: utf-8 -*-
"""Los dos pedidos de Laura (jefa de Control de Calidad) · 18-ago-2026.

**1. El formato no preimprime el cargo de quien firma.** El F02 (COC-PRO-002-F02,
certificado de análisis para liberar materia prima) decía *"Aprueba · Jefe de Control de
Calidad"* fijo. La liberación también la dan el **director técnico** y **aseguramiento**,
así que el formato estaba LIMITANDO quién puede firmar -- lo contrario de lo que un
registro debe hacer. Ahora la línea dice el cargo de QUIEN firmó, y si no se puede
resolver queda sólo el acto: inventar un cargo en un documento regulado es peor que no
ponerlo (M19/M93).

⚠ Y cambiar el rótulo sin mirar el permiso habría dejado el formato prometiendo lo que el
sistema niega (M109). Al medirlo aparecieron **dos gates del MISMO acto que no decían lo
mismo**: el F02 gateaba con `_require_calidad` (Calidad ∪ admin) mientras el otro camino
de liberación usa `QC_USERS`, que sí incluye al DT y a Aseguramiento -- o sea que el
director técnico podía liberar por una puerta y no por la otra (M32/M219). La política ya
estaba escrita en `config.py` cuando se sacó a Catalina por la Res. 2214/2021:
*"la liberación queda donde corresponde: Control de Calidad, Aseguramiento, Dirección
Técnica y Dirección"*.

**2. El informe del laboratorio se puede SUBIR, y es opcional.** El campo sólo aceptaba una
URL, así que para adjuntar el PDF había que hospedarlo en otra parte: en la práctica no se
adjuntaba. Se guarda en la BASE y no en disco, porque el servicio no tiene disco
persistente y lo que el importador escribe en `/var/data/coas` desaparece en cada
despliegue -- siendo documento regulado (M91).
"""
import base64
import io as _io
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, ("no pudo entrar %s" % user)
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _un(conjunto):
    """Un usuario del rol · sale de config, no de un nombre escrito a mano (M102)."""
    import config
    s = getattr(config, conjunto, set()) or set()
    return sorted(s)[0] if s else None


# ── 1 · la firma ────────────────────────────────────────────────────────────────

def _cuerpo_de(nombre, archivo="calidad.py"):
    """El cuerpo REAL de la función · nunca una ventana de N caracteres, que la secuestra
    cualquier función escrita más abajo (M151)."""
    import ast as _ast
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", archivo)
    src = _io.open(ruta, encoding="utf-8").read()
    lin = src.splitlines()
    for nodo in _ast.walk(_ast.parse(src)):
        if isinstance(nodo, _ast.FunctionDef) and nodo.name == nombre:
            cuerpo = "\n".join(lin[nodo.lineno - 1:nodo.end_lineno])
            # Sin comentarios: el que EXPLICA por qué el cargo ya no va contiene la frase,
            # y el guard se encontraría a sí mismo (M154).
            return "\n".join(l for l in cuerpo.splitlines()
                             if not l.strip().startswith("#"))
    raise AssertionError("no encontré %s" % nombre)


def test_el_F02_no_preimprime_el_cargo_de_quien_firma(app, db_clean):
    cuerpo = _cuerpo_de("calidad_f02_imprimible")
    assert "COC-PRO-002-F02" in cuerpo, "no es el F02"
    assert "Jefe de Control de Calidad" not in cuerpo, (
        "el formato sigue preimprimiendo un cargo, así que limita quién puede firmar")
    assert "_rc_acto(" in cuerpo, "la línea de firma no resuelve el cargo de quien firmó"


def test_el_CoA_de_producto_terminado_tampoco(app, db_clean):
    cuerpo = _cuerpo_de("coa_pt_imprimible")
    assert "Jefe de Control de Calidad" not in cuerpo, (
        "el certificado de producto terminado sigue con el cargo preimpreso")


def test_el_cargo_sale_de_QUIEN_firmo(app, db_clean):
    try:
        from blueprints.calidad import _rc_cargo
    except ImportError:
        from api.blueprints.calidad import _rc_cargo
    cn = _cn()
    try:
        cn.execute("DELETE FROM usuarios_identidad WHERE username IN ('zqa','zdt','zsin')")
        for u, nom, cargo in (('zqa', 'Zoe Calidad', 'Jefa de Control de Calidad'),
                              ('zdt', 'Zacarias Tecnico', 'Director Técnico'),
                              ('zsin', 'Zulma Sin', 'Por definir')):
            cn.execute("INSERT INTO usuarios_identidad (username, nombre_completo, cargo) "
                       "VALUES (?,?,?)", (u, nom, cargo))
        cn.commit()
        c = cn.cursor()
        assert _rc_cargo(c, 'zqa') == 'Jefa de Control de Calidad'
        # también resuelve por NOMBRE COMPLETO: los formatos guardan el nombre, no el usuario
        assert _rc_cargo(c, 'Zacarias Tecnico') == 'Director Técnico'
        # 'Por definir' es el DEFAULT de la tabla · no es un cargo, es la ausencia de uno
        assert _rc_cargo(c, 'zsin') == '', "inventó un cargo donde no lo hay"
        assert _rc_cargo(c, 'nadie') == ''
        assert _rc_cargo(c, '') == ''
    finally:
        cn.execute("DELETE FROM usuarios_identidad WHERE username IN ('zqa','zdt','zsin')")
        cn.commit()
        cn.close()


def test_el_director_tecnico_y_aseguramiento_PUEDEN_liberar_MP(app, db_clean):
    """El rótulo y el permiso tienen que decir lo mismo (M109), y ya lo decía config.py."""
    try:
        from blueprints.inventario import QC_USERS
    except ImportError:
        from api.blueprints.inventario import QC_USERS
    import config
    for conjunto in ('TECNICA_USERS', 'ASEGURAMIENTO_USERS', 'CALIDAD_USERS'):
        s = getattr(config, conjunto, set()) or set()
        assert s <= set(QC_USERS), (
            "%s quedó fuera de quien puede liberar MP, y la política de config.py dice "
            "que la liberación es de Control de Calidad, Aseguramiento y Dirección "
            "Técnica" % conjunto)
    # y el que RECIBE sigue afuera (Res. 2214/2021 · quien compra no libera)
    assert not (getattr(config, 'MP_LIBERA_USERS', set()) or set()), (
        "volvió a haber alguien fuera de los tres roles con permiso de liberar MP")

    # el ENDPOINT del F02 usa ese mismo conjunto, no uno más angosto
    fuente = _io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "api", "blueprints", "calidad.py"), encoding="utf-8").read()
    i = fuente.find("def calidad_certificado_analisis")
    j = fuente.find("\ndef ", i + 10)
    cuerpo = fuente[i:j if j > 0 else i + 12000]
    assert "_require_libera_mp()" in cuerpo, (
        "el F02 volvió a gatear más angosto que la política: el director técnico podría "
        "liberar por una puerta y no por la otra")


def test_un_usuario_sin_rol_NO_puede_guardar_el_F02(app, db_clean):
    """El borde · ampliar un permiso sin probarlo es cambiarlo por una puerta abierta.

    El candidato sale de los usuarios que el harness PUEDE loguear (`ALL_USERS`) menos los
    autorizados: buscarlo en un set de config puede devolver a alguien sin clave en el
    harness, y entonces el guard se saltea y deja de medir (M152/M222).
    """
    from .conftest import ALL_USERS
    try:
        from blueprints.inventario import QC_USERS
    except ImportError:
        from api.blueprints.inventario import QC_USERS
    ajenos = [u for u in ALL_USERS if u not in QC_USERS]
    assert ajenos, ("todos los usuarios del harness pueden liberar MP · este guard dejó "
                    "de poder medir el borde")
    for ajeno in ajenos[:3]:
        r = _cli(app, ajeno).post('/api/calidad/certificado-analisis', headers=_h(),
                                  json={'mov_id': 1, 'resultado': 'aprobado'})
        assert r.status_code == 403, (
            "%s puede liberar materia prima sin estar en Calidad, Aseguramiento ni "
            "Dirección Técnica" % ajeno, r.status_code)


# ── 2 · el informe del laboratorio ──────────────────────────────────────────────

def test_registrar_micro_SIN_archivo_sigue_funcionando(app, db_clean):
    """Opcional quiere decir opcional: sin adjunto, se guarda igual."""
    cli = _cli(app)
    r = cli.post('/api/calidad/micro/resultados', headers=_h(), json={
        'producto_nombre': 'ZCOA PRODUCTO', 'lote': 'ZCOA-1',
        'microorganismo': 'Mesofilos aerobios', 'valor': 10})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:250]
    assert (r.get_json() or {}).get('ok'), r.get_json()


def test_el_informe_se_sube_y_el_resultado_lo_ACEPTA(app, db_clean):
    """El eslabón que se rompe solo: el campo ofrece subir y el guard rechaza la URL.

    Si el validador sólo admite http(s), adjuntar el informe y guardar el resultado falla
    en el paso siguiente -- el formulario prometiendo lo contrario de lo que exige (M109).
    """
    cli = _cli(app)
    datos = b'%PDF-1.4 informe de laboratorio de prueba'
    r = cli.post('/api/calidad/micro/coa-archivo',
                 data={'archivo': (_io.BytesIO(datos), 'informe.pdf'), 'lote': 'ZCOA-2'},
                 headers=csrf_headers(), content_type='multipart/form-data')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    j = r.get_json() or {}
    assert j.get('url', '').startswith('/api/calidad/micro/coa-archivo/'), j
    assert j.get('bytes') == len(datos), j

    # el archivo se puede volver a leer · y sale con el mismo contenido
    rv = cli.get(j['url'])
    assert rv.status_code == 200, rv.status_code
    assert rv.data == datos, "el informe no vuelve igual que como se subió"

    # y el resultado de micro con esa URL se GUARDA (el validador la acepta)
    r2 = cli.post('/api/calidad/micro/resultados', headers=_h(), json={
        'producto_nombre': 'ZCOA PRODUCTO', 'lote': 'ZCOA-2',
        'microorganismo': 'Mesofilos aerobios', 'valor': 5,
        'archivo_coa_url': j['url']})
    assert r2.status_code in (200, 201), (
        "subió el informe y después no dejó guardar el resultado con él",
        r2.get_data(as_text=True)[:250])


def test_el_informe_se_guarda_en_la_BASE_no_en_disco(app, db_clean):
    """El servicio no tiene disco persistente: en disco, el certificado se pierde en cada
    despliegue, y es documento regulado (M91)."""
    cli = _cli(app)
    datos = b'%PDF-1.4 persistente'
    j = cli.post('/api/calidad/micro/coa-archivo',
                 data={'archivo': (_io.BytesIO(datos), 'persiste.pdf')},
                 headers=csrf_headers(),
                 content_type='multipart/form-data').get_json() or {}
    aid = j.get('id')
    assert aid, j
    cn = _cn()
    try:
        row = cn.execute("SELECT nombre, mime, contenido, bytes FROM calidad_coa_archivos "
                         "WHERE id=?", (aid,)).fetchone()
    finally:
        cn.close()
    assert row, "el informe no quedó en la base"
    assert row[0] == 'persiste.pdf' and row[1] == 'application/pdf'
    assert base64.b64decode(row[2]) == datos
    assert row[3] == len(datos)


def test_rechaza_lo_que_no_es_un_informe(app, db_clean):
    cli = _cli(app)
    r = cli.post('/api/calidad/micro/coa-archivo',
                 data={'archivo': (_io.BytesIO(b'MZ...'), 'virus.exe')},
                 headers=csrf_headers(), content_type='multipart/form-data')
    assert r.status_code == 400, r.status_code
    r2 = cli.post('/api/calidad/micro/coa-archivo', data={}, headers=csrf_headers(),
                  content_type='multipart/form-data')
    assert r2.status_code == 400, r2.status_code


def test_la_pantalla_ofrece_subir_el_informe_y_dice_que_es_OPCIONAL(app, db_clean):
    """Una capacidad sin puerta no existe (M121), y un campo que no dice que es opcional
    se llena por las dudas."""
    from .conftest import pantalla_servida
    js = pantalla_servida(_cli(app), '/calidad')
    assert 'subirCoaMicro' in js, "no hay forma de subir el informe desde la pantalla"
    assert '/api/calidad/micro/coa-archivo' in js, "el botón no apunta al endpoint"
    i = js.find('m-micro-coa')
    assert i > 0, "desapareció el campo del COA"
    assert 'opcional' in js[max(0, i - 500):i + 200].lower(), (
        "el campo no dice que es opcional")
