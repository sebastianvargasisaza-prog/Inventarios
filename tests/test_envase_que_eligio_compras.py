"""El legajo de envasado muestra el envase que eligió COMPRAS, no el del catálogo (16-ago-2026).

Sebastián, describiendo cómo se construyó la cadena: *"la lógica dice: Catalina en compras
selecciona, si algo cambia se autocarga en calendario para que lo jale a envasado, así lo
construimos"*.

La cadena estaba a medias. `envase_codigo_override` se fija POR LOTE en el calendario (cuando no
alcanza el frasco habitual, o se decide otro), y desde el 7-jul lo honran **la compra** y **el
descuento** (M73). Pero `envases-plan` -- el endpoint que pinta el envase con su foto en el
legajo -- leía `producto_presentaciones` directo, o sea el frasco HABITUAL.

Resultado: el legajo mostraba un frasco y la planta descontaba otro. Y el operario alista **lo
que ve en la pantalla**, así que el error termina en el estante, no en un informe.

Es la misma regla que ya está escrita: si un lado de la cadena honra un override, el otro
también (M55/M73).
"""
import pytest

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ ENVASE COMPRAS"


def _login(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _sembrar(app):
    """Un lote con su presentación, su envase habitual y otro frasco distinto en el maestro."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ebr_ejecuciones WHERE lote_codigo='ZZ-EC-1'")
        cur.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        cur.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        cur.execute("DELETE FROM mbr_templates WHERE producto_nombre=?", (PROD,))
        for cod, desc, img in (("ZZ-EC-FRA", "Frasco habitual", "https://ej/a.png"),
                               ("ZZ-EC-FRB", "Frasco elegido por Compras", "https://ej/b.png")):
            cur.execute("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, imagen_url, "
                        "estado) VALUES (?,?,?,'Activo')", (cod, desc, img))
        cur.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                    "etiqueta, volumen_ml, envase_codigo, activo) "
                    "VALUES (?,'V30','30ml',30,'ZZ-EC-FRA',1)", (PROD,))
        cur.execute("INSERT INTO produccion_programada (producto, cantidad_kg, lotes, "
                    "fecha_programada, estado, origen) "
                    "VALUES (?, 30, 1, date('now'), 'programado', 'eos_plan')", (PROD,))
        pid = cur.execute("SELECT id FROM produccion_programada WHERE producto=?",
                          (PROD,)).fetchone()[0]
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                    "lote_size_g, creado_por) VALUES (?,1,'aprobado',?,30000,'test')",
                    (PROD, PROD))
        mid = cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                          (PROD,)).fetchone()[0]
        cur.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, produccion_id, lote, "
            "lote_codigo, estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,1,?,'ZZ-EC-1-OF','ZZ-EC-1','iniciado','envasado','sebastian',"
            "        '2026-08-16T10:00:00',30000)", (mid, pid))
        eid = int(cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote='ZZ-EC-1-OF'"
                              ).fetchone()[0])
        conn.commit()
    return eid, pid


def _elegir(app, pid, codigo):
    """Lo que hace Compras al fijar otro frasco para ESE lote."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("UPDATE produccion_programada SET envase_codigo_override=? WHERE id=?",
                  (codigo, pid))
        c.commit()


def _items(cli, eid):
    j = cli.get("/api/brd/ebr/%d/envases-plan" % eid).get_json() or {}
    return j.get("items") or []


# ══ la cadena ═══════════════════════════════════════════════════════════════════

def test_sin_decision_de_compras_va_el_envase_del_producto(app, db_clean):
    eid, _pid = _sembrar(app)
    it = _items(_login(app), eid)
    assert it, "el legajo no trae presentaciones"
    assert it[0]["envase_codigo"] == "ZZ-EC-FRA", it[0]
    assert it[0].get("envase_override") is False


def test_si_compras_elige_otro_frasco_el_legajo_LO_MUESTRA(app, db_clean):
    """El corazón: antes seguía mostrando el habitual mientras la planta descontaba el nuevo."""
    eid, pid = _sembrar(app)
    _elegir(app, pid, "ZZ-EC-FRB")
    it = _items(_login(app), eid)
    assert it[0]["envase_codigo"] == "ZZ-EC-FRB", (
        "el legajo sigue mostrando el frasco del catálogo · el operario alistaría el equivocado")
    assert it[0].get("envase_override") is True, "no se marca que este lote lleva otro envase"
    assert it[0].get("envase_catalogo") == "ZZ-EC-FRA", (
        "no dice cuál era el habitual · sin eso no se puede auditar la decisión")


def test_la_FOTO_es_la_del_frasco_que_se_va_a_usar(app, db_clean):
    """Sebastián: *"lo que quería ver es que arrastrara la foto del envase"*. Si la foto queda
    en el frasco viejo, el operario reconoce en el estante el que NO va."""
    eid, pid = _sembrar(app)
    _elegir(app, pid, "ZZ-EC-FRB")
    it = _items(_login(app), eid)
    assert (it[0].get("envase") or {}).get("foto") == "https://ej/b.png", (
        "la foto sigue siendo la del frasco del catálogo · %s" % (it[0].get("envase"),))


def test_la_descripcion_acompana_al_codigo(app, db_clean):
    """Un código como `MEE-ENV-012` no le dice nada a quien busca el frasco en el estante."""
    eid, pid = _sembrar(app)
    _elegir(app, pid, "ZZ-EC-FRB")
    it = _items(_login(app), eid)
    assert "Compras" in ((it[0].get("envase") or {}).get("descripcion") or ""), it[0].get("envase")
