"""Guardián de JavaScript en plantillas (Sebastián 6-jun-2026).

POR QUÉ EXISTE: el JS embebido en las plantillas Python ("""  # noqa
"""..."""  # noqa
""") no lo validaba NADA. Los tests golden prueban el backend/HTTP, nunca la
EJECUCIÓN del JS en el navegador. Por eso se colaron bugs que solo el operador
veía en vivo:
  · "Cargando…" eterno = un \\n crudo en una cadena JS → SyntaxError (lo atrapa
    node --check sobre el HTML YA renderizado, como lo ve el navegador).
  · escapeHtml is not defined = función llamada pero no definida en ese <script>.

Este guardián RENDERIZA las páginas críticas (igual que producción, pasando por
los after_request) y corre `node --check` sobre cada bloque <script> inline. Si
hay un error de sintaxis (incluido el \\n que parte una cadena), falla el test.

Se salta solo si `node` no está instalado (para no romper entornos sin Node).
"""
import os
import re
import shutil
import subprocess
import tempfile

import pytest

NODE = shutil.which('node')

# Páginas con JS inline crítico (las que usa planta/calidad/operarios a diario).
PAGINAS = [
    ('/inventarios', 'admin'),
    ('/planta/orden/1', 'admin'),
    ('/brd/timeline/1', 'admin'),
    ('/brd/despeje/1', 'admin'),
    ('/brd/dispensado/1', 'admin'),
    ('/admin/conteo-rescate', 'admin'),
]


def _scripts_inline(html):
    """Devuelve los bloques <script>…</script> SIN src (JS embebido)."""
    out = []
    for m in re.finditer(r'<script\b([^>]*)>(.*?)</script>', html, re.S | re.I):
        attrs, body = m.group(1), m.group(2)
        if 'src=' in attrs.lower():
            continue
        if body.strip():
            out.append(body)
    return out


@pytest.mark.skipif(NODE is None, reason='node no instalado · guardián JS se salta')
@pytest.mark.parametrize('ruta,_rol', PAGINAS)
def test_js_inline_sin_errores_sintaxis(admin_client, ruta, _rol):
    r = admin_client.get(ruta)
    assert r.status_code == 200, f'{ruta} no cargó ({r.status_code})'
    html = r.get_data(as_text=True)
    scripts = _scripts_inline(html)
    # Páginas server-rendered (despeje, rescate) pueden no tener <script> inline
    # (usan onclick). No es error · simplemente no hay nada que node-checkear.
    for idx, js in enumerate(scripts):
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js)
            path = f.name
        try:
            res = subprocess.run([NODE, '--check', path], capture_output=True, text=True)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        assert res.returncode == 0, (
            f'{ruta} · bloque <script> #{idx} tiene ERROR DE SINTAXIS JS '
            f'(esto rompería la página en el navegador):\n{res.stderr[:600]}'
        )
