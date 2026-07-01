"""Lente de seguridad · CSRF en fetch mutantes a endpoints admin-sensibles.

auth.py exige X-CSRF-Token (403 si falta) para los paths obligatorios:
/api/admin/, /api/maestro-mps/, /api/maestros-mps/, /api/mfa/. Un fetch del
frontend a esos endpoints con method POST/PUT/PATCH/DELETE que NO manda el
header falla con 403 EN PRODUCCIÓN (los tests lo saltan por app.testing, por
eso pasó desapercibido meses). Este test escanea TODO el frontend y falla si
aparece uno, para que el bug se cace el día que se introduce (Sebastián 1-jul).
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# opciones de fetch inline con method mutante + headers literal
_OPT = re.compile(
    r"""\{[^{}]*method\s*:\s*['"](POST|PATCH|PUT|DELETE)['"][^{}]*headers\s*:\s*\{[^{}]*\}[^{}]*\}"""
)
# paths donde el token es OBLIGATORIO (auth.py · _admin_paths)
_SENS = re.compile(r"/api/(admin|maestro-mps|maestros-mps|mfa)\b")


def test_fetch_admin_sensibles_llevan_csrf_token():
    files = (glob.glob(os.path.join(ROOT, 'api', 'templates_py', '*.py'))
             + glob.glob(os.path.join(ROOT, 'api', 'blueprints', '*.py')))
    offenders = []
    for f in files:
        txt = open(f, encoding='utf-8').read()
        for m in _OPT.finditer(txt):
            blk = m.group(0)
            if 'X-CSRF-Token' in blk or 'FormData' in blk:
                continue  # ya lleva token · o es subida de archivo (excepción)
            pre = txt[max(0, m.start() - 200):m.start() + 1]
            fm = list(re.finditer(r"fetch\(\s*([^;]+?)\s*,\s*\{", pre))
            url = fm[-1].group(1) if fm else ''
            if _SENS.search(url):
                ln = txt[:m.start()].count('\n') + 1
                offenders.append(f"{os.path.basename(f)}:{ln}  {url.strip()[:60]}")
    assert not offenders, (
        "fetch mutante a endpoint admin-sensible SIN X-CSRF-Token → dará 403 en prod.\n"
        "Agregá 'X-CSRF-Token' al header (window._csrfTok en dashboard, o "
        "fetch('/api/csrf-token') inline):\n  " + "\n  ".join(offenders)
    )
