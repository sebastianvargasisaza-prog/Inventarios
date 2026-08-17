"""El visto bueno del Director Técnico, en la pantalla del PRODUCTO TERMINADO (16-ago-2026).

Al mover la firma del DT a la fase de acondicionamiento -que es donde el formato la pone
(`PRD-PRO-001-F01`) y donde el propio Hernando la ubicó en el acta del 27-jul- apareció que la
pantalla de esa fase **no la ofrecía**: el endpoint existe desde junio (mig 286) y la única
forma de dar el visto bueno era el modal del dashboard. La firma existía y ahí era inalcanzable
(M121), y el dato ni siquiera viajaba: `/vista-completa` no mandaba `aprobado_dt_por`.

Además había dos whitelists desalineadas en el camino de la firma:

  · `firmar-rapido` no aceptaba el meaning `aprueba_dt` -- el mismo defecto que en julio tenía
    `/api/sign` (M116), en el otro endpoint;
  · y su gate de rol era `ADMIN ∪ CALIDAD` mientras el mensaje prometía *"Calidad / Dirección
    Técnica"*: o sea que **el Director Técnico no podía firmar ni la liberación** que el propio
    endpoint `/liberar` sí le permite, y Aseguramiento tampoco. El gate de la FIRMA y el de la
    ACCIÓN decían cosas distintas y la pantalla se trababa sin explicar por qué (M32).

Ahora los dos salen de `_batch_role_info`, que es la única fuente.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _sembrar(app, fase):
    """Un legajo por fase, con nombre fijo y limpiando ANTES (M103)."""
    from database import get_db
    lote = "ZZ-VBDT-%s" % fase[:4].upper()
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        v = cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()
        if v:
            cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (v[0],))
        cur.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,'completado',?,'sebastian','2026-08-16T10:00:00',1000)",
            (1, 1, lote, lote, fase))
        eid = int(cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0])
        conn.commit()
    return eid


# ══ el dato viaja ═══════════════════════════════════════════════════════════════

def test_vista_completa_manda_el_visto_bueno(app, db_clean):
    """Sin el dato no hay pantalla posible: era el eslabón que faltaba."""
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "laura").get("/api/brd/ebr/%d/vista-completa" % eid)
    assert r.status_code == 200, r.data[:200]
    j = r.get_json() or {}
    assert "aprobado_dt_por" in j, "/vista-completa no manda quién dio el visto bueno"
    assert "aprobado_dt_at" in j, "ni cuándo"


# ══ la pantalla lo ofrece, y sólo donde va ══════════════════════════════════════

def test_el_legajo_de_producto_terminado_ofrece_el_visto_bueno(app, db_clean):
    eid = _sembrar(app, "acondicionamiento")
    html = _login(app, "sebastian").get(
        "/planta/legajo-acondicionamiento/%d" % eid).data.decode("utf-8", "replace")
    for pieza, que in (("aprobarDtAcond", "la función que lo ejecuta"),
                       ("aprueba_dt", "firma con el meaning correcto"),
                       ("aprobado_dt_por", "muestra quién firmó"),
                       ("aprobar-dt", "llama al endpoint que ya existía")):
        assert pieza in html, "falta %s (%s)" % (pieza, que)


def test_el_javascript_de_la_pantalla_compila(app, db_clean):
    """Un escape roto no rompe Python ni el gate: deja la pantalla MUERTA, en silencio (M65/M173).

    Se compila el HTML SERVIDO, no el fuente: los escapes del string de Python no son los que
    llega a ver el navegador, así que revisar el fuente pasa verde con la pantalla partida. Y se
    exige haber revisado al menos un bloque -- una verificación que puede saltarse su objeto sin
    decirlo no es una verificación.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        pytest.skip("node no está instalado en esta máquina")
    eid = _sembrar(app, "acondicionamiento")
    cli = _login(app, "sebastian")
    revisados = 0
    for ruta in ("/planta/legajo-acondicionamiento/%d" % eid,
                 "/planta/legajo-envasado/%d" % eid):
        html = cli.get(ruta).data.decode("utf-8", "replace")
        for i, js in enumerate(re.findall(
                r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)):
            if not js.strip():
                continue
            revisados += 1
            f = os.path.join(tempfile.gettempdir(), "vbdt_%d.js" % (revisados,))
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(js)
            cr = subprocess.run([node, "--check", f], capture_output=True)
            assert cr.returncode == 0, "%s bloque %d no compila: %s" % (
                ruta, i, cr.stderr.decode("utf-8", "replace")[:300])
    assert revisados >= 2, (
        "sólo se revisaron %d bloques · el chequeo se estaría salteando la pantalla" % revisados)


def test_toda_funcion_llamada_desde_un_boton_existe(app, db_clean):
    """Un `onclick` que llama a algo inexistente no da error visible: el botón simplemente no
    hace nada (M146/M166), que es como se despliega una feature muerta."""
    eid = _sembrar(app, "acondicionamiento")
    html = _login(app, "sebastian").get(
        "/planta/legajo-acondicionamiento/%d" % eid).data.decode("utf-8", "replace")
    llamadas = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\(', html))
    assert llamadas, "no se encontró ningún botón · el guard no estaría midiendo nada"
    huerfanas = [f for f in llamadas if ("function " + f) not in html]
    assert not huerfanas, "botones que llaman a funciones inexistentes: %s" % huerfanas


# ══ quién puede firmarlo ════════════════════════════════════════════════════════

def test_el_director_tecnico_puede_firmar_su_visto_bueno(app, db_clean):
    """El acto es suyo: si `firmar-rapido` lo rechaza, el botón existe y no sirve."""
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "hernando").post(
        "/api/brd/ebr/%d/firmar-rapido" % eid,
        json={"meaning": "aprueba_dt"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    assert (r.get_json() or {}).get("signature_id"), "no devolvió la firma"


def test_produccion_no_da_el_visto_bueno_del_DT(app, db_clean):
    """Dientes del otro lado: sin esto, un gate que dejara pasar a todos daría verde igual."""
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "mayerlin").post(
        "/api/brd/ebr/%d/firmar-rapido" % eid,
        json={"meaning": "aprueba_dt"}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:250]


def test_el_director_tecnico_tambien_puede_firmar_la_liberacion(app, db_clean):
    """El gate de la FIRMA tiene que decir lo mismo que el de la ACCIÓN.

    `firmar-rapido` limitaba `libera` a ADMIN ∪ CALIDAD mientras su propio mensaje prometía
    "Calidad / Dirección Técnica" y `/liberar` sí acepta al DT: el DT veía el botón y la firma
    lo rechazaba. Es la liberación del producto terminado, o sea justo su acto.
    """
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "hernando").post(
        "/api/brd/ebr/%d/firmar-rapido" % eid,
        json={"meaning": "libera"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]


def test_aseguramiento_tampoco_queda_trabado(app, db_clean):
    """Miguel puede liberar por `_batch_role_info`, así que la firma no puede negárselo."""
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "miguel").post(
        "/api/brd/ebr/%d/firmar-rapido" % eid,
        json={"meaning": "libera"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]


def test_compras_sigue_afuera(app, db_clean):
    """Ampliar un gate no puede abrirle la puerta a otra área."""
    eid = _sembrar(app, "acondicionamiento")
    r = _login(app, "catalina").post(
        "/api/brd/ebr/%d/firmar-rapido" % eid,
        json={"meaning": "libera"}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:250]


# ══ la verificación va por ETAPA, no por renglón ════════════════════════════════

def test_el_instructivo_no_pide_una_firma_por_paso(app, db_clean):
    """Sebastián, con el procedimiento enfrente: **"entonces por etapa"**.

    `requiere_qc=1` no es decorativo: bloquea el registro del paso (400) hasta que otra persona
    firme. Con ~20 pasos por lote eran 20 firmas de Calidad por lote, y el sistema documental
    pide las verificaciones por ETAPA (despeje, controles en proceso, pesajes, material de
    envase, liberación), no por renglón.
    """
    from blueprints.brd import _REQUIERE_QC_INSTRUCTIVO
    assert _REQUIERE_QC_INSTRUCTIVO == 0, (
        "los pasos del instructivo volvieron a exigir la 2ª firma uno por uno")


def test_la_migracion_baja_los_ya_sembrados_solo_donde_corresponde(app, db_clean):
    """Y la mitad que de verdad destraba: los pasos que YA estaban cargados (mig 438).

    Sin esto el cambio no servía de nada hoy -- el default nuevo sólo alcanza a los instructivos
    que se carguen de aquí en adelante.

    ⚠ La primera versión de este test contaba los pasos con `requiere_qc=1` en TODA la tabla, y
    estaba mal por dos motivos: se rompía con cualquier test vecino que sembrara uno (M102/M103)
    y, sobre todo, **prohibía algo que decidimos permitir** -- marcar un paso crítico desde el
    MBR sigue siendo un clic, y eso dejaría de poder probarse. Lo que hay que medir es la
    MIGRACIÓN, sobre datos propios, en los tres casos que la distinguen.
    """
    from database import get_db, MIGRATIONS
    sql = [m for m in MIGRATIONS if m[0] == 438][0][2]
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for pref in ("ZZQC BORRADOR", "ZZQC APROBADO", "ZZQC FIRMADO"):
            cur.execute("DELETE FROM mbr_pasos WHERE descripcion LIKE ?", (pref + "%",))
            cur.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (pref,))

        def _tpl(nombre):
            cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                        "lote_size_g, creado_por) VALUES (?,1,'draft',?,1000,'test')",
                        (nombre, nombre))
            return cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                               (nombre,)).fetchone()[0]

        def _paso(tid, desc):
            cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, "
                        "tipo_paso, requiere_qc) VALUES (?,1,'Envasado',?,'envasado',1)",
                        (tid, desc))
            return cur.execute("SELECT id FROM mbr_pasos WHERE descripcion=?",
                               (desc,)).fetchone()[0]

        a = _paso(_tpl("ZZQC BORRADOR"), "ZZQC BORRADOR paso")
        # el aprobado se arma en el ORDEN REAL (draft -> pasos -> aprobar): el trigger prohíbe
        # insertarle pasos a un MBR ya aprobado, y esa negativa es la invariante, no un estorbo
        tb = _tpl("ZZQC APROBADO")
        b = _paso(tb, "ZZQC APROBADO paso")
        cur.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (tb,))
        tc = _tpl("ZZQC FIRMADO")
        cc = _paso(tc, "ZZQC FIRMADO paso")
        cur.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,1,'ZZQC-L','ZZQC-L','en_proceso','envasado','test','2026-08-16T10:00:00',1000)",
            (tc,))
        eid = cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote='ZZQC-L'").fetchone()[0]
        cur.execute(
            "INSERT INTO ebr_pasos_ejecutados (ebr_id, mbr_paso_id, orden, descripcion, "
            "requiere_qc, estado, operario_username, qc_username) "
            "VALUES (?,?,1,'ZZQC FIRMADO paso',1,'completado','mayerlin','laura')", (eid, cc))
        conn.commit()

        for s in sql:
            cur.execute(s)
        conn.commit()

        def _qc(pid):
            return int(cur.execute("SELECT COALESCE(requiere_qc,0) FROM mbr_pasos WHERE id=?",
                                   (pid,)).fetchone()[0])
        borrador, aprobado, firmado = _qc(a), _qc(b), _qc(cc)

    assert borrador == 0, "el paso de un MBR en borrador tenía que quedar por etapa"
    assert aprobado == 1, (
        "tocó un MBR APROBADO · es inmutable y además es un documento firmado")
    assert firmado == 1, (
        "tocó un paso ya ejecutado CON la firma dada · eso es reescribir su historia")


def test_lo_que_se_firma_por_ETAPA_sigue_firmandose(app, db_clean):
    """El borde que hace que bajar el default no sea aflojar un control.

    Las cinco verificaciones que el procedimiento SÍ pide siguen en pie; la que se prueba acá es
    la de los controles en proceso, que es la que Calidad adjudica y nadie más (INV-18).
    """
    with app.app_context():
        from blueprints.brd import _batch_role_info
        assert _batch_role_info("mayerlin")["verifica"] is False
        assert _batch_role_info("laura")["verifica"] is True
