"""El plano muestra la planta REAL y dice qué hacer en cada sala (16-ago-2026).

Sebastián dibujó la distribución física en Paint y pidió: *"me gustaría que el plano fuera así ·
la idea es que fuera súper inteligente · si salía sucia el área le daban click encima para
limpiar, entiendo que era así"*. Y después: *"que apenas la producción se monte aparezca allí el
producto y la cantidad con el operario · recordá los tiempos, todo debe calcular tiempos de
producción, envasado y demás, así Alejandro y yo sabemos en tiempo real qué hacen"*.

El plano era una grilla automática de tarjetas (`repeat(auto-fill,minmax(230px,1fr))`), o sea
que no decía dónde queda nada, y **no estaba enlazado desde ninguna pantalla**.

⚠ De dónde salen los tiempos, que es lo que decide si esto sirve: `produccion_programada` tiene
columnas `etapa_disp/elab/env_*_at` y **nadie las escribe** -- un plano que las leyera mostraría
tiempos vacíos para siempre (M154). Se derivan del legajo de cada fase y de los pasos
ejecutados, que es donde el hecho queda registrado.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _plano(app):
    r = _login(app).get("/planta/plano")
    assert r.status_code == 200, r.status_code
    return r.data.decode("utf-8", "replace")


# ══ la planta de verdad ═════════════════════════════════════════════════════════

def test_el_plano_dibuja_la_distribucion_real(app, db_clean):
    """Las salas en su lugar, no una grilla que las acomoda sola."""
    html = _plano(app)
    assert "grid-template-areas" in html, "sigue siendo una grilla automática"
    # el MAPA no puede acomodarse solo · el bloque de "otras áreas" sí, que ahí no hay posición
    # física que respetar (medir todo el HTML daba un rojo falso con el código correcto)
    i = html.index(".plano{")
    assert "auto-fill" not in html[i:html.index("}", i)], (
        "el mapa volvió al acomodo automático")
    for cod in ("LAV", "DISP", "PROD1", "ENV1", "ALMP", "PROD3", "PROD2", "ENV2", "CC"):
        assert "'%s'" % cod in html, "falta %s en el mapa" % cod


def test_las_salas_del_mapa_EXISTEN_en_el_sistema(app, db_clean):
    """Dibujar una sala que la base no tiene sería inventar planta.

    Si mañana se renombra un área, este test lo dice en vez de dejar un hueco mudo en la
    pantalla (el plano además lo declara en pantalla, pero eso nadie lo mira a diario).
    """
    from database import get_db
    html = _plano(app)
    codigos = re.findall(r"\['([A-Z0-9_]+)','[a-z0-9]+'\]", html)
    assert len(codigos) >= 9, "el mapa quedó con %d salas: %s" % (len(codigos), codigos)
    with app.app_context():
        reales = {r[0] for r in get_db().execute(
            "SELECT codigo FROM areas_planta WHERE COALESCE(activo,1)=1").fetchall()}
    faltan = [c for c in codigos if c not in reales]
    assert not faltan, "el plano dibuja salas que no existen: %s" % faltan


def test_ninguna_sala_queda_escondida(app, db_clean):
    """Las áreas que existen y no están en el dibujo se muestran igual: una sala sucia que nadie
    ve no se limpia nunca (M124)."""
    html = _plano(app)
    assert "Otras &aacute;reas" in html or "otras" in html, (
        "no hay dónde caigan las áreas fuera del mapa")


# ══ el clic hace lo que toca ════════════════════════════════════════════════════

def test_cada_estado_dice_que_hace_el_clic(app, db_clean):
    """El corazón del pedido: el área sucia deja de ser un cartel y pasa a ser la salida."""
    html = _plano(app)
    for pieza, que in (("Registrar la limpieza", "sucia → registrar la limpieza"),
                       ("Verificar (Calidad)", "limpiando → verificar"),
                       ("Ver el legajo", "ocupada → abrir su legajo"),
                       ("Disponible para producir", "libre → se puede usar")):
        assert pieza in html, "falta la acción de %s" % que
    assert "function actuar(" in html, "el clic no tiene a dónde ir"


def test_el_estado_no_se_lee_SOLO_por_color(app, db_clean):
    """Cada sala lleva su estado escrito · el color solo deja afuera a quien no lo distingue."""
    html = _plano(app)
    for palabra in ("Sucia", "En limpieza", "En proceso", "Libre"):
        assert palabra in html, "el estado %r no aparece como texto" % palabra


# ══ los tiempos ═════════════════════════════════════════════════════════════════

def test_el_plano_pide_los_tiempos_y_el_estimado(app, db_clean):
    html = _plano(app)
    for pieza in ("etapa_mins", "etapa_estimado_min", "paso_actual"):
        assert pieza in html, "el plano no muestra %s" % pieza
    assert "tarde" in html, "no marca cuando un lote se pasó del estimado"


def test_el_endpoint_manda_la_etapa_en_curso(app, db_clean):
    """Lo que hace que la pantalla pueda decir 'envasando hace 1 h 40'."""
    r = _login(app).get("/api/planta/plano-fabricacion?todas=1")
    assert r.status_code == 200, r.data[:200]
    j = r.get_json() or {}
    assert j.get("ok") is True, j
    assert isinstance(j.get("areas"), list) and j["areas"], "no devolvió áreas"
    # todas las salas del dibujo tienen que venir con ?todas=1, no sólo las de producción
    codigos = {a.get("codigo") for a in j["areas"]}
    for cod in ("LAV", "DISP", "ALMP", "CC"):
        assert cod in codigos, (
            "%s no viaja en el endpoint · el plano la dibujaría vacía" % cod)


def test_el_tiempo_no_depende_de_la_zona_del_servidor(app, db_clean):
    """El elapsed se anclaba a `datetime.now()`, que es la hora LOCAL del servidor: sólo daba
    bien porque Render corre en UTC, y en una máquina en hora Colombia restaba 5 horas de más y
    mostraba "hace 0 min" para un lote de dos horas (lo mostró la previa · M24)."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, "api", "blueprints", "programacion.py"),
                  encoding="utf-8").read()
    i = src.index("def plano_fabricacion_data")
    j = src.index("@bp.route", i + 10)
    cuerpo = re.sub(r"#[^\n]*", "", src[i:j])      # sin comentarios (M154)
    assert "datetime.now(timezone.utc)" in cuerpo, (
        "el elapsed volvió a anclarse a la hora local del servidor")


def test_el_plano_esta_enlazado(app, db_clean):
    """Existía y no lo enlazaba nadie: por eso Sebastián ni sabía que estaba (M121)."""
    from .conftest import contenido_pantalla
    html = contenido_pantalla("dashboard_html", "DASHBOARD_HTML")
    assert "/planta/plano" in html, "ninguna pantalla lleva al plano"


def test_la_pantalla_usa_el_sistema_de_diseno(app, db_clean):
    """Abre en pestaña propia, así que necesita su propio enlace a la hoja de estilos y su
    propia lectura del tema: sin eso cada var() cae al color de respaldo y queda clavada en
    claro, fuera del sistema (M203)."""
    html = _plano(app)
    assert "cortex.css" in html, "no enlaza la hoja de estilos"
    assert "cx-theme" in html or "data-theme" in html, "no lee el tema del usuario"
