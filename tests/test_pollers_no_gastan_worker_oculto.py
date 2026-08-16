"""Un refresco automático no trabaja contra una pestaña que nadie mira (15-ago-2026).

Sebastián: *"revisá la velocidad de cada módulo, están lentos en cada cosa cargando y
mostrando"*. Medido: **18 pantallas** se refrescan solas cada 20-300 segundos (producción y
dashboard cada 20s, la campana cada 25s, compras y el operario cada 30s, gerencia con cinco
de 300s) y ninguna miraba si la pestaña estaba visible. EOS se usa con varias pestañas
abiertas, así que cuatro pestañas eran cuatro veces el tráfico contra TRES workers, y cada
request lento retiene uno de los tres (M43/M91).

El arreglo vive en UN solo lugar -- `cortex.js`, que `after_request` inyecta en todas las
páginas -- en vez de en dieciocho archivos (M3).

Estos tests ejercitan el comportamiento con un navegador simulado, no buscan texto en el
fuente: un guard que sólo comprueba que cierta palabra está escrita pasa verde aunque la
lógica esté al revés (M142/M152).
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORTEX = os.path.join(RAIZ, "api", "static", "cortex.js")

# El simulacro: un `document` con `hidden` que se puede mover y un `window` con timers de
# mentira, para poder disparar los ticks a mano y contar cuántas veces corrió cada poller.
_SIMULACRO = r"""
const listeners = {};
global.document = {
  hidden: false,
  body: { classList:{add(){},remove(){}}, setAttribute(){}, removeAttribute(){} },
  addEventListener(ev, fn){ (listeners[ev] = listeners[ev] || []).push(fn); },
};
let seq = 0; const timers = {};
global.window = {
  setInterval(fn, ms){ const id = ++seq; timers[id] = {fn, ms}; return id; },
  clearInterval(id){ delete timers[id]; },
  addEventListener(){},
};
window.document = document;
const fs = require('fs');
eval(fs.readFileSync(process.argv[2],'utf8').replace(/window\.addEventListener/g,'(function(){})'));
const tick = id => { if (timers[id]) timers[id].fn(); };
const enfocar = () => (listeners['visibilitychange']||[]).forEach(f=>f());

const r = {};
let datos = 0, reloj = 0, zombie = 0;
const idDatos = window.setInterval(() => datos++, 20000);   // refresco de datos
const idReloj = window.setInterval(() => reloj++, 1000);    // reloj/animación

document.hidden = true;
for (let i=0;i<5;i++){ tick(idDatos); tick(idReloj); }
r.datos_oculta = datos;      // 0: no se gasta un worker
r.reloj_oculta = reloj;      // 5: lo corto no se toca

document.hidden = false; enfocar();
r.datos_al_volver = datos;   // 1: refresca enseguida, no espera al próximo tick

const idZ = window.setInterval(() => zombie++, 30000);
document.hidden = true; tick(idZ);
window.clearInterval(idZ);
document.hidden = false; enfocar();
r.zombie = zombie;           // 0: un intervalo cancelado no revive al enfocar

console.log(JSON.stringify(r));
"""


def _node():
    for n in ("node", "node.exe"):
        p = shutil.which(n)
        if p:
            return p
    return None


def _correr():
    node = _node()
    if not node:
        pytest.skip("node no disponible en este entorno")
    tmp = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    try:
        tmp.write(_SIMULACRO)
        tmp.close()
        out = subprocess.run([node, tmp.name, CORTEX], capture_output=True, timeout=60)
        assert out.returncode == 0, out.stderr.decode("utf-8", "replace")[:600]
        return json.loads(out.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def test_un_refresco_no_corre_con_la_pestana_oculta():
    r = _correr()
    assert r["datos_oculta"] == 0, (
        "el refresco de 20s siguió pidiendo datos con la pestaña oculta: %s" % r)


def test_lo_corto_no_se_toca():
    """Un reloj o una animación por debajo de 15s tienen que seguir corriendo igual.

    Es el borde que evita que el arreglo apague de más (M96): sin este test, frenar TODOS
    los intervalos también pasaría el primero.
    """
    r = _correr()
    assert r["reloj_oculta"] == 5, "se frenó un intervalo corto (reloj/animación): %s" % r


def test_al_volver_a_la_pestana_refresca_enseguida():
    """Sin esto el usuario vuelve a datos viejos hasta el próximo tick, que en gerencia son
    cinco minutos: se habría cambiado lentitud por información desactualizada."""
    r = _correr()
    assert r["datos_al_volver"] == 1, (
        "al enfocar no se refrescó una vez lo que se salteó: %s" % r)


def test_un_intervalo_cancelado_no_revive_al_enfocar():
    """El poller de un modal ya cerrado no puede ejecutarse una vez más contra un DOM que ya
    no existe (M112: el disparador y su destino se retiran juntos)."""
    r = _correr()
    assert r["zombie"] == 0, "un intervalo cancelado volvió a correr al enfocar: %s" % r


def test_cortex_se_sirve_en_las_pantallas(app):
    """El arreglo no sirve de nada si la página no carga el archivo (M164/M197)."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    for ruta in ("/inventarios", "/compras", "/calidad"):
        h = c.get(ruta).data.decode("utf-8", "replace")
        assert "/static/cortex.js" in h, "%s no carga cortex.js" % ruta
