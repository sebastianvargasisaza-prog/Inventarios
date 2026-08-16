"""Quién firma el cierre del batch record (16-ago-2026).

Sebastián, mirando la sección *Cierre y Aprobaciones* del legajo: **"aquí solo debería ser jefe
y calidad, ¿entendés?"**, y antes: *"el director técnico solo libera el producto terminado,
incluso en esto aparece firma de él y no debería"*. Cuando le pregunté por el detalle, la
respuesta fue mejor que una respuesta: *"si tienes dudas entra al sistema documental de la
empresa en drive, allí todas las verificaciones las pueden hacer analista y jefe de control de
calidad"*.

Y el sistema documental es claro, en tres piezas que se apoyan entre sí:

  · `COC-PRO-010` (procedimiento del batch digital) §3.4 -- "Analista de Calidad: EJECUTAR
    verificaciones, revisiones y aprobaciones conforme a su perfil autorizado".
  · `PRD-INS-001-004` (instructivos operativos) -- las tablas de verificación son "de
    diligenciamiento EXCLUSIVO de Control de Calidad" y las firma el Analista CC.
  · `PRD-PRO-001-F01` (lista de chequeo del batch record) cierra con RESPONSABLES DEL PROCESO =
    Jefe de Producción + Jefe de Control de Calidad, y el VBO de Dirección Técnica aparte.

La pieza que ordena el resto es el acta de la revisión con Hernando -el propio Director
Técnico- del 27-jul: **"la LIBERACIÓN es una responsabilidad del director técnico, mientras que
el envasado requiere APROBACIÓN en lugar de liberación"**. O sea que fabricación y envasado se
APRUEBAN entre Producción y Calidad, y la firma del DT es el acto final sobre el producto
terminado -- que es exactamente lo que Sebastián dijo con otras palabras.

Estos tests fijan las dos mitades: quién puede dar la 2ª firma de un control de proceso, y en
qué fase aparece el bloque del Director Técnico.
"""
import io
import os
import re


def _fuente_legajo():
    """El JS de la pantalla del legajo, sin comentarios.

    Se quitan porque este archivo explica largamente lo que ya NO va, y un guard que se
    encuentra a sí mismo en un comentario pasa o falla por la razón equivocada (M154).
    """
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "templates_py", "dashboard_html.py"),
                  encoding="utf-8").read()
    i = src.find("Cierre y Aprobaciones finales")
    j = src.find("Correcciones del Registro", i)
    assert i > 0 and j > i, "no se encontró el bloque de Cierre · el guard mediría otra cosa"
    return re.sub(r"//[^\n']*", "", src[i:j])


# ══ quién verifica ═════════════════════════════════════════════════════════════

def test_las_verificaciones_son_de_calidad(app):
    """Analista y Jefe de Control de Calidad, más Aseguramiento (Jefe de Garantía)."""
    with app.app_context():
        from blueprints.brd import _batch_role_info
        for quien, tipo in (("laura", "calidad"), ("yuliel", "calidad"),
                            ("miguel", "aseguramiento")):
            r = _batch_role_info(quien)
            assert r["tipo"] == tipo, (quien, r)
            assert r["verifica"] is True, "%s tiene que poder verificar" % quien


def test_el_director_tecnico_no_verifica_pero_conserva_su_firma(app):
    """La corrección completa: sale de verificar, se queda con lo suyo.

    Quitarle `aprueba_dt` habría sido pasarse de largo -- el visto bueno del Director Técnico
    es un requisito del formato `PRD-PRO-001-F01` y de la normativa, no un permiso de más. Lo
    que se corrige es dónde firma, no que firme (M112: podar es borrar el par completo, y acá
    el par no sobra).
    """
    with app.app_context():
        from blueprints.brd import _batch_role_info
        dt = _batch_role_info("hernando")
        assert dt["tipo"] == "director_tecnico", dt
        assert dt["verifica"] is False, "el DT no da la 2ª firma de un control de proceso"
        assert dt["aprueba_dt"] is True, "pero SÍ conserva el visto bueno final"


def test_el_operario_no_verifica_lo_que_ejecuta(app):
    """El borde que hace que todo lo anterior signifique algo.

    Sin este assert, un cambio que le diera `verifica` a todo el mundo pasaría verde: los tests
    de arriba sólo miran a quienes SÍ deben tenerlo (M171).
    """
    with app.app_context():
        from blueprints.brd import _batch_role_info
        op = _batch_role_info("mayerlin")
        assert op["realiza"] is True
        assert op["verifica"] is False


def test_la_campana_de_verificacion_va_a_quien_puede_firmar(app):
    """A quién se le avisa y quién puede actuar tienen que ser el mismo conjunto.

    Si al Director Técnico le sigue sonando la campana por cada ítem marcado, entra al legajo y
    no puede hacer nada: un aviso que no lleva a ninguna parte enseña a ignorar todos los demás
    (M202/M32).
    """
    with app.app_context():
        from blueprints.brd import _qc_verificadores, _batch_role_info
        dest = _qc_verificadores()
        assert dest, "sin destinatarios no se avisa a nadie"
        for u in dest:
            assert _batch_role_info(u)["verifica"] is True, (
                "se le avisa a %s y no puede firmar la verificación" % u)


# ══ dónde firma el Director Técnico ════════════════════════════════════════════

def test_el_cierre_de_proceso_es_produccion_y_calidad(app):
    """Fabricación y envasado se aprueban entre Producción y Calidad · el bloque del DT queda
    detrás de la fase de producto terminado."""
    cuerpo = _fuente_legajo()
    assert "_esPT" in cuerpo, "no quedó la marca de producto terminado"
    assert "acondicionamiento" in cuerpo, "la marca no se ancla en la fase"
    # el bloque del DT se emite sólo si es producto terminado (o si ya firmó)
    i_guard = cuerpo.find("if(_esPT||_dtYaFirmo)")
    i_dt = cuerpo.find("Visto bueno")
    assert 0 <= i_guard < i_dt, (
        "el bloque del Director Técnico no está detrás de la fase de producto terminado")


def test_lo_que_no_se_muestra_se_explica(app):
    """Una tarjeta que desaparece sin decir por qué se lee como un faltante (M148/M124).

    En fabricación y envasado, donde el DT no firma, la sección lo DICE y remite a dónde sí va.
    """
    cuerpo = _fuente_legajo()
    for pista in ("Dirección Técnica", "producto terminado", "acondicionamiento"):
        assert pista in cuerpo, "el aviso no explica dónde firma el DT (falta '%s')" % pista


def test_una_firma_ya_dada_nunca_se_esconde(app):
    """Si el Director Técnico ya firmó un legajo, se sigue viendo pase lo que pase con la fase.

    Ocultar una firma registrada de un documento regulado no es simplificar la pantalla: es
    quitarle a un registro Part 11 una firma que existe.
    """
    cuerpo = _fuente_legajo()
    assert "_dtYaFirmo" in cuerpo, "no hay salida para los legajos que ya llevan la firma"
    assert "if(_esPT||_dtYaFirmo)" in cuerpo, (
        "la firma ya dada tiene que mostrarse aunque la fase no sea producto terminado")


def test_el_legajo_y_la_vista_completa_hablan_del_MISMO_rol(app, db_clean):
    """Las dos pantallas del legajo tienen que recibir el rol con las MISMAS llaves.

    Había dos mapas de roles escritos a mano y divergían en silencio: el de `/vista-completa`
    publicaba `puede_verificar` mientras la pantalla de envasado lee `d.mi_rol.verifica` -- una
    llave que ese dict nunca tuvo. `PUEDE_VERIF` daba false para TODO el mundo, así que el botón
    de verificar el material de envase (2ª firma del envase) no aparecía nunca, sin un solo error
    a la vista (M94/M116). Y de paso ese mapa no conocía a Aseguramiento, o sea que a Miguel la
    pantalla le escondía lo que el gate real sí le permite.

    Ahora los dos salen del resolvedor único. El test lo ejerce por los ENDPOINTS, no leyendo el
    código, porque lo que rompía era justamente el contrato entre los dos (M170).
    """
    from database import get_db
    from .conftest import TEST_PASSWORD, csrf_headers
    cli = app.test_client()
    r = cli.post('/login', data={'username': 'laura', 'password': TEST_PASSWORD},
                 headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar laura'
    # El legajo se SIEMBRA acá, con nombre fijo y limpiando ANTES (M103): depender de que la
    # base traiga uno deja el test saltándose en silencio, y un test que se saltea no protege
    # nada (M152) -- que es justo cómo este defecto sobrevivió tanto tiempo.
    lote = 'ZZ-ROL-VC'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        vieja = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()
        if vieja:
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (vieja[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,'en_proceso','envasado','sebastian','2026-08-16T10:00:00',1000)",
            (1, 1, lote, lote))
        eid = int(cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0])
        conn.commit()

    a = cli.get('/api/brd/ebr/%d' % eid)
    b = cli.get('/api/brd/ebr/%d/vista-completa' % eid)
    assert a.status_code == 200 and b.status_code == 200, (a.status_code, b.status_code)
    rol_a = (a.get_json() or {}).get('mi_rol') or {}
    rol_b = (b.get_json() or {}).get('mi_rol') or {}
    assert rol_a and rol_b, 'alguna de las dos vistas dejó de mandar el rol'
    for llave in ('usuario', 'tipo', 'realiza', 'verifica', 'puede_ejecutar',
                  'puede_verificar', 'puede_liberar'):
        assert llave in rol_b, (
            "/vista-completa no manda '%s' · la pantalla que la lee se queda sin esa acción"
            % llave)
        assert rol_a.get(llave) == rol_b.get(llave), (
            "las dos vistas discrepan en '%s': %r vs %r" % (llave, rol_a.get(llave),
                                                            rol_b.get(llave)))
    assert rol_b.get('verifica') is True, 'Calidad tiene que poder verificar en las dos'
    assert 'puede_corregir' in rol_b, 'se perdió el alias que esa pantalla ya publicaba'


def test_el_rotulo_distingue_aprobar_de_liberar(app):
    """El acta lo dejó dicho con todas las letras: el proceso se APRUEBA, el producto terminado
    se LIBERA. Que la pantalla use la misma palabra que el procedimiento no es cosmético -- son
    dos actos regulatorios distintos."""
    cuerpo = _fuente_legajo().replace(" ", "")
    assert "_esPT?'Aprobadopor&middot;Calidad(liberación)'" in cuerpo, (
        "el rótulo de Calidad no distingue aprobación de liberación")
    assert ":'Aprobadopor&middot;Calidad'" in cuerpo, (
        "falta el rótulo de APROBACIÓN para fabricación y envasado")
