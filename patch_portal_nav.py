"""
patch_portal_nav.py
====================
Fix: /gerencia sirve HUB_HTML en lugar de GERENCIA_HTML
Fix: hub_html.py enlaza a /maquila que no existe (debe ser /hub-salida)

Bugs encontrados:
  gerencia.py line 38: return Response(HUB_HTML, ...) → debe ser GERENCIA_HTML
  hub_html.py line 120: href="/maquila" → debe ser href="/hub-salida"
"""

import subprocess, sys, os

REPO = "/tmp/inv_p8"

def patch_gerencia_route():
    path = f"{REPO}/api/blueprints/gerencia.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Fix: /gerencia route sirve HUB_HTML cuando debe servir GERENCIA_HTML
    old = """@bp.route('/gerencia')
def gerencia_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('core.login'))
    return Response(HUB_HTML, mimetype='text/html')"""

    new = """@bp.route('/gerencia')
def gerencia_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('core.login'))
    return Response(GERENCIA_HTML, mimetype='text/html')"""

    if old not in src:
        print("ERROR: patron /gerencia no encontrado — verificar manualmente")
        return False

    src = src.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: /gerencia ahora sirve GERENCIA_HTML")
    return True

def patch_hub_maquila_link():
    path = f"{REPO}/api/templates_py/hub_html.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Fix: /maquila no existe, la ruta real es /hub-salida
    old = 'href="/maquila"'
    new = 'href="/hub-salida"'

    if old not in src:
        print("ERROR: href='/maquila' no encontrado en hub_html.py")
        return False

    src = src.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: hub_html.py — Maquila ahora enlaza a /hub-salida")
    return True

def verify():
    print("\n--- VERIFICACION ---")

    path_g = f"{REPO}/api/blueprints/gerencia.py"
    with open(path_g) as f:
        content = f.read()
    # Debe tener GERENCIA_HTML en la ruta /gerencia
    if "return Response(GERENCIA_HTML, mimetype='text/html')" in content:
        print("[OK] gerencia.py: /gerencia sirve GERENCIA_HTML")
    else:
        print("[FAIL] gerencia.py: todavia sirve HUB_HTML")

    # No debe tener HUB_HTML en la funcion gerencia_page
    idx = content.find("def gerencia_page():")
    snippet = content[idx:idx+300]
    if "HUB_HTML" in snippet:
        print("[FAIL] gerencia_page() todavia referencia HUB_HTML")
    else:
        print("[OK] gerencia_page() ya no usa HUB_HTML")

    path_h = f"{REPO}/api/templates_py/hub_html.py"
    with open(path_h) as f:
        hub_content = f.read()
    if 'href="/hub-salida"' in hub_content:
        print("[OK] hub_html.py: Maquila enlaza a /hub-salida")
    else:
        print("[FAIL] hub_html.py: Maquila no enlaza correctamente")
    if 'href="/maquila"' not in hub_content:
        print("[OK] hub_html.py: /maquila ya no aparece")
    else:
        print("[FAIL] hub_html.py: /maquila todavia presente")

def push_to_github():
    TOKEN = "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"
    OWNER = "sebastianvargasisaza-prog"
    REPO_NAME = "Inventarios"
    CLONE_URL = f"https://{OWNER}:{TOKEN}@github.com/{OWNER}/{REPO_NAME}.git"
    CLONE_DIR = "/tmp/inv_push_portal"

    print("\n--- PUSH A GITHUB ---")

    import shutil
    if os.path.exists(CLONE_DIR):
        shutil.rmtree(CLONE_DIR)

    r = subprocess.run(["git", "clone", CLONE_URL, CLONE_DIR], capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR al clonar:", r.stderr)
        return False

    for fname in ["api/blueprints/gerencia.py", "api/templates_py/hub_html.py"]:
        src = f"{REPO}/{fname}"
        dst = f"{CLONE_DIR}/{fname}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())

    subprocess.run(["git", "config", "user.email", "sebas@espagiria.com"], cwd=CLONE_DIR)
    subprocess.run(["git", "config", "user.name", "Sebastian"], cwd=CLONE_DIR)

    r2 = subprocess.run(["git", "add", "-A"], cwd=CLONE_DIR, capture_output=True, text=True)
    r3 = subprocess.run(
        ["git", "commit", "-m", "fix(nav): /gerencia sirve GERENCIA_HTML no HUB_HTML; hub Maquila -> /hub-salida"],
        cwd=CLONE_DIR, capture_output=True, text=True
    )
    if "nothing to commit" in r3.stdout:
        print("Nada que pushear (ya esta actualizado)")
        return True

    r4 = subprocess.run(["git", "push", "origin", "main"], cwd=CLONE_DIR, capture_output=True, text=True)
    if r4.returncode == 0:
        print("Push OK — Render desplegando en ~60s")
        return True
    else:
        print("ERROR en push:", r4.stderr)
        return False

if __name__ == "__main__":
    print("=== patch_portal_nav.py ===\n")
    ok1 = patch_gerencia_route()
    ok2 = patch_hub_maquila_link()
    if ok1 and ok2:
        verify()
        push_to_github()
    else:
        print("\nPatch fallido — no se hizo push")
        sys.exit(1)
