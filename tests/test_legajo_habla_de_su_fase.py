"""La línea de tiempo del legajo habla de SU fase (15-ago-2026).

`/brd/timeline/<id>` estaba cableada a fabricación: el título decía *"Batch Record Bulk"*
y las etapas eran *"Pesaje de Materias Primas"* y *"Fabricación / Mezclado"* para CUALQUIER
fase. Un lote de envasado no pesa materias primas ni mezcla; uno de acondicionamiento
menos.

Importa más de lo que parece porque **la cola de controles de Calidad enlaza justo acá**
(se construyó el 14-ago): Laura abre un control pendiente de un lote de acondicionamiento
y cae en una pantalla que le habla de granel. Es M205 otra vez —pedirle la densidad a una
caja— ahora en el encabezado del legajo.

⚠ CÓMO SE MIDE, que es la parte que costó: la pantalla arma su contenido en JavaScript, así
que **el HTML servido contiene las TRES ramas** y sólo una se ejecuta. Un assert de tipo
`"Pesaje de Materias Primas" not in html` es imposible de satisfacer y no mide nada (mi
primera versión falló por eso, y antes se había encontrado a sí misma en un comentario ·
M154). Entonces:
  · los tests de ESTRUCTURA verifican que exista una rama por fase con sus etapas;
  · y el test de DOM abre la página en un navegador de verdad y lee lo que quedó pintado —
    se salta solo si no hay Chrome, para no volverse un rojo que no habla del código.
"""
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile

import pytest

from .conftest import TEST_PASSWORD, csrf_headers

_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _visible():
    _exec("INSERT INTO app_settings (clave,valor) VALUES ('brd_visible','1') "
          "ON CONFLICT (clave) DO UPDATE SET valor='1'")


def _legajo(fase, sufijo):
    _exec("DELETE FROM ebr_ejecuciones WHERE lote LIKE 'ZFAS%'")
    _exec("DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZFAS%'")
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES ('ZFAS PRODUCTO',1,'aprobado',1000,'sebastian')")
    return _exec(
        "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
        "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
        "VALUES (?,1,?,'ZFAS-1','en_proceso',?,'sebastian','2026-08-14 09:00:00',1000)",
        (mbr, 'ZFAS-1' + sufijo, fase))


def _cliente(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _abrir(app, ebr):
    resp = _cliente(app).get("/brd/timeline/%d" % ebr)
    assert resp.status_code == 200, resp.status_code
    return resp.data.decode("utf-8")


# ── estructura ───────────────────────────────────────────────────────────────

def test_hay_una_rama_de_etapas_por_fase(app, db_clean):
    """Sin la rama, la pantalla sólo puede mostrar las etapas de fabricación."""
    _visible()
    html = _abrir(app, _legajo("envasado", "-OF"))
    assert "h.fase" in html or "_fase" in html, "la pantalla no mira la fase"
    for fase, etapa in (("envasado", "Alistamiento de envase y tapa"),
                        ("acondicionamiento", "Alistamiento de etiquetas y empaque"),
                        ("fabricacion", "Pesaje de Materias Primas")):
        assert etapa in html, "falta la etapa de %s" % fase
    assert "Batch Record de Envasado" in html
    assert "Batch Record de Acondicionamiento" in html


def test_el_javascript_de_la_pantalla_compila(app, db_clean):
    """Se node-checkea el RENDERIZADO: el fuente arrastra comentarios de Python (M173)."""
    _visible()
    html = _abrir(app, _legajo("envasado", "-OF"))
    bloques = [b for b in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S) if b.strip()]
    assert bloques, "la pantalla no tiene JavaScript"
    for i, b in enumerate(bloques):
        f = os.path.join(tempfile.gettempdir(), "tlfase%d.js" % i)
        io.open(f, "w", encoding="utf-8").write(b)
        r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
        assert r.returncode == 0, "bloque %d roto: %s" % (i, r.stderr[:400])


def test_calidad_llega_a_esta_pantalla(app, db_clean):
    """Por esto importaba el defecto: la cola de controles de Calidad enlaza acá."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "calidad.py")
    fuente = open(ruta, encoding="utf-8").read()
    assert "/brd/timeline/" in fuente, (
        "la cola de Calidad ya no enlaza al timeline: revisar si este guard sigue aplicando")


# ── lo que de verdad se ve (DOM) ─────────────────────────────────────────────

def _pintado(app, ebr):
    """Abre la pantalla en Chrome con los datos servidos y devuelve el texto del DOM."""
    if not (os.path.exists(_CHROME) or shutil.which("chrome") or shutil.which("chromium")):
        pytest.skip("sin Chrome: la verificación de DOM no puede correr acá")
    c = _cliente(app)
    html = c.get("/brd/timeline/%d" % ebr).data.decode("utf-8")
    datos = c.get("/api/brd/ebr/%d/vista-completa" % ebr).data.decode("utf-8")
    stub = ("<script>window.__D=" + datos + ";window.fetch=function(){return Promise.resolve("
            "{ok:true,status:200,json:function(){return Promise.resolve(window.__D);}});};"
            "</script>")
    html = html.replace("</head>", stub + "</head>", 1)
    d = tempfile.mkdtemp()
    f = os.path.join(d, "tl.html")
    io.open(f, "w", encoding="utf-8").write(html)
    exe = _CHROME if os.path.exists(_CHROME) else (shutil.which("chrome")
                                                   or shutil.which("chromium"))
    # El DOM viene en UTF-8; leerlo con la codificación de la consola (cp1252 en Windows)
    # revienta con los acentos y el test se SALTA -- o sea, deja de medir (M152).
    r = subprocess.run([exe, "--headless=new", "--disable-gpu", "--dump-dom",
                        "--virtual-time-budget=4000", "file:///" + f.replace("\\", "/")],
                       capture_output=True, timeout=90)
    dom = (r.stdout or b"").decode("utf-8", "replace")
    if len(dom) < 500:
        pytest.skip("Chrome no devolvió el DOM en este entorno")
    # El volcado del DOM trae el CÓDIGO de los <script>, y ahí están las tres ramas. Sin
    # sacarlos, el test vuelve a medir lo que la página contiene en vez de lo que muestra
    # -- que es el error que este archivo existe para no repetir.
    dom = re.sub(r"<script[^>]*>.*?</script>", " ", dom, flags=re.S | re.I)
    dom = re.sub(r"<style[^>]*>.*?</style>", " ", dom, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", dom)


def test_en_pantalla_el_envasado_no_pide_pesaje_de_materias_primas(app, db_clean):
    """La verificación que vale: lo que quedó PINTADO, no lo que el código contiene."""
    _visible()
    texto = _pintado(app, _legajo("envasado", "-OF"))
    assert "Batch Record de Envasado" in texto, texto[:300]
    assert "Alistamiento de envase y tapa" in texto
    assert "Pesaje de Materias Primas" not in texto, (
        "en pantalla le pide pesaje de materias primas a un lote de envasado")
    assert "Lote Bulk" not in texto, "en pantalla el rótulo del lote sigue diciendo Bulk"


def test_en_pantalla_la_fabricacion_no_cambio(app, db_clean):
    """El borde que hace que el arreglo no rompa el caso que ya andaba (M96)."""
    _visible()
    texto = _pintado(app, _legajo("fabricacion", ""))
    assert "Batch Record Bulk Lote" in texto, texto[:300]
    assert "Pesaje de Materias Primas" in texto
    assert "Alistamiento de envase y tapa" not in texto
