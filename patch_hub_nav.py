"""
patch_hub_nav.py
=================
Fix: todos los módulos tienen un botón claro "← Panel Central" para volver al hub.

Cambios:
  gerencia_html.py — Quick Nav: agregar botón prominente "🏠 Panel Central" primero
  gerencia_html.py — topbar: hacer el link "← Inicio" más visible
  (los demás módulos ya tienen href="/" que redirige correctamente al hub)
"""

import os, sys, subprocess, shutil

REPO = "/tmp/inv_p8"

def patch_gerencia_nav():
    path = f"{REPO}/api/templates_py/gerencia_html.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # ---------- 1. Quick Nav: agregar Panel Central PRIMERO ----------
    old_quicknav = """  <!-- QUICK NAV -->
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;">
    <a href="/recepcion" style="background:rgba(43,122,120,0.2);border:1px solid rgba(43,122,120,0.4);color:#7ACFCC;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
  </div>"""

    new_quicknav = """  <!-- QUICK NAV -->
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;">
    <a href="/hub" style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.35);color:#fff;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:700;">🏠 Panel Central</a>
    <a href="/recepcion" style="background:rgba(43,122,120,0.2);border:1px solid rgba(43,122,120,0.4);color:#7ACFCC;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
    <a href="/calidad" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔬 Calidad</a>
    <a href="/rrhh" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👥 RRHH</a>
    <a href="/tecnica" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔧 Técnica</a>
  </div>"""

    if old_quicknav not in src:
        print("ERROR: patron Quick Nav no encontrado en gerencia_html.py")
        return False

    src = src.replace(old_quicknav, new_quicknav, 1)

    # ---------- 2. Topbar: hacer el link "← Inicio" visible y claro ----------
    # Hay DOS links "← Inicio" en el topbar — mejorar el de la derecha para que sea obvio
    old_topbar_right = '    <a href="/" style="font-size:12px;color:#a8a29e;text-decoration:none;">&#8592; Inicio</a>'
    new_topbar_right = '    <a href="/hub" style="font-size:12px;font-weight:700;color:#e2e8f0;text-decoration:none;border:1px solid rgba(255,255,255,0.25);padding:5px 12px;border-radius:6px;">&#8962; Panel</a>'

    if old_topbar_right in src:
        src = src.replace(old_topbar_right, new_topbar_right, 1)
        print("OK: topbar derecho actualizado")

    # Tambien mejorar el topbar izquierdo
    old_topbar_left = '    <a href="/" style="color:#a8a29e;text-decoration:none;font-size:12px;margin-right:4px;">&#8592; Inicio</a>'
    new_topbar_left = '    <a href="/hub" style="color:#e2e8f0;text-decoration:none;font-size:12px;font-weight:600;margin-right:4px;">&#8962; Hub</a>'

    if old_topbar_left in src:
        src = src.replace(old_topbar_left, new_topbar_left, 1)
        print("OK: topbar izquierdo actualizado")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: gerencia Quick Nav actualizado con Panel Central y módulos completos")
    return True


def patch_hub_add_missing_modules():
    """Agrega Calidad, Técnica, RRHH, Solicitudes al grid del Hub."""
    path = f"{REPO}/api/templates_py/hub_html.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # El grid termina con maquila — agregar los módulos que faltan
    old_grid_end = '      <a class="mod-btn" href="/hub-salida"><span class="mod-icon">&#x1F9EA;</span><span class="mod-name">Maquila</span><span class="mod-badge mb-ok">activo</span></a>\n    </div>'
    new_grid_end = (
        '      <a class="mod-btn" href="/hub-salida"><span class="mod-icon">&#x1F9EA;</span><span class="mod-name">Maquila</span><span class="mod-badge mb-ok">activo</span></a>\n'
        '      <a class="mod-btn" href="/calidad"><span class="mod-icon">&#x1F52C;</span><span class="mod-name">Calidad</span><span class="mod-badge mb-ok">activo</span></a>\n'
        '      <a class="mod-btn" href="/tecnica"><span class="mod-icon">&#x1F527;</span><span class="mod-name">T\u00e9cnica</span><span class="mod-badge mb-ok">activo</span></a>\n'
        '      <a class="mod-btn" href="/rrhh"><span class="mod-icon">&#x1F465;</span><span class="mod-name">RRHH</span><span class="mod-badge mb-ok">activo</span></a>\n'
        '      <a class="mod-btn" href="/solicitudes"><span class="mod-icon">&#x1F4DD;</span><span class="mod-name">Solicitudes</span><span class="mod-badge mb-ok">activo</span></a>\n'
        '    </div>'
    )

    if old_grid_end not in src:
        print("WARN: patron grid-end no encontrado — hub ya puede tener los módulos agregados")
        return True  # no es error critico

    src = src.replace(old_grid_end, new_grid_end, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: hub_html.py — Calidad, Tecnica, RRHH, Solicitudes agregados al grid")
    return True


def verify():
    print("\n--- VERIFICACION ---")
    path_g = f"{REPO}/api/templates_py/gerencia_html.py"
    with open(path_g) as f:
        gc = f.read()
    if 'href="/hub"' in gc and 'Panel Central' in gc:
        print("[OK] gerencia: botón Panel Central presente")
    else:
        print("[FAIL] gerencia: falta botón Panel Central")
    if 'href="/calidad"' in gc and 'href="/rrhh"' in gc:
        print("[OK] gerencia: Calidad y RRHH en Quick Nav")
    else:
        print("[FAIL] gerencia: faltan módulos en Quick Nav")

    path_h = f"{REPO}/api/templates_py/hub_html.py"
    with open(path_h) as f:
        hc = f.read()
    if 'href="/calidad"' in hc and 'href="/rrhh"' in hc and 'href="/tecnica"' in hc:
        print("[OK] hub: Calidad, RRHH, Tecnica en el grid")
    else:
        print("[WARN] hub: algunos módulos podrían faltar")


def push():
    TOKEN = "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"
    OWNER = "sebastianvargasisaza-prog"
    CLONE_DIR = "/tmp/inv_push_portal"

    print("\n--- PUSH A GITHUB ---")
    # reusar el clone existente
    r = subprocess.run(["git", "pull", "origin", "main"],
                       cwd=CLONE_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        print("WARN pull:", r.stderr[:200])

    for fname in ["api/templates_py/gerencia_html.py", "api/templates_py/hub_html.py"]:
        with open(f"{REPO}/{fname}", "rb") as fi, open(f"{CLONE_DIR}/{fname}", "wb") as fo:
            fo.write(fi.read())

    subprocess.run(["git", "config", "user.email", "sebas@espagiria.com"], cwd=CLONE_DIR)
    subprocess.run(["git", "config", "user.name", "Sebastian"], cwd=CLONE_DIR)
    subprocess.run(["git", "add", "-A"], cwd=CLONE_DIR, capture_output=True)

    r3 = subprocess.run(
        ["git", "commit", "-m",
         "fix(nav): gerencia agrega boton Panel Central; hub agrega Calidad/RRHH/Tecnica/Solicitudes"],
        cwd=CLONE_DIR, capture_output=True, text=True
    )
    if "nothing to commit" in r3.stdout:
        print("Nada que pushear"); return True

    r4 = subprocess.run(["git", "push", "origin", "main"], cwd=CLONE_DIR, capture_output=True, text=True)
    if r4.returncode == 0:
        print("Push OK — Render desplegando en ~60s")
        return True
    else:
        print("ERROR push:", r4.stderr[:300])
        return False


if __name__ == "__main__":
    print("=== patch_hub_nav.py ===\n")
    ok1 = patch_gerencia_nav()
    ok2 = patch_hub_add_missing_modules()
    if ok1:
        verify()
        push()
    else:
        print("Patch fallido"); sys.exit(1)
