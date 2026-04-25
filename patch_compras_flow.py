"""
patch_compras_flow.py
======================
Fix: flujo de Compras — Catalina hace UN solo paso para enviar a autorización.

Cambios:
  BACKEND compras.py:
    - cuando crear_oc=true, crear OC como 'Revisada' (no 'Borrador')
    - incluir valor_total, fecha_entrega_est, categoria en el INSERT
    - leer categoria de la solicitud si no viene en el body

  FRONTEND compras_html.py:
    - openSolicitudDetail: agregar hidden input sol-cat con s.categoria
    - openSolicitudDetail: botón "Aprobar y crear OC" → "Enviar a Autorización"
    - gestionarSol: pasar valor, fent, categoria al backend
"""

import os, sys

REPO = "/tmp/inv_p8"

# ─── BACKEND ────────────────────────────────────────────────────────────

def patch_backend():
    path = f"{REPO}/api/blueprints/compras.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # ---------- 1. Cambiar INSERT para incluir todos los campos ----------
    old_insert = """    oc_creada = ''
    if d.get('crear_oc'):
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
        items_sol = cur.fetchall()
        proveedor_oc = d.get('proveedor', 'Por definir')
        cur.execute("SELECT COUNT(*) FROM ordenes_compra")
        n_oc = cur.fetchone()[0] + 1
        oc_num = f"OC-{datetime.now().year}-{n_oc:04d}"
        cur.execute(\"\"\"INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones, creado_por)
                     VALUES (?,?,?,?,?,?)\"\"\",
                  (oc_num, datetime.now().isoformat(), 'Borrador', proveedor_oc,
                   f'Generado desde {numero.upper()}', session.get('compras_user','')))
        for it in items_sol:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (oc_num, it[0], it[1], it[2]))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (oc_num, numero.upper()))
        oc_creada = oc_num"""

    new_insert = """    oc_creada = ''
    if d.get('crear_oc'):
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad, categoria FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
        items_sol = cur.fetchall()
        # Obtener categoria de la solicitud para la OC
        cur.execute("SELECT categoria FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
        sol_row = cur.fetchone()
        categoria_oc = d.get('categoria') or (sol_row[0] if sol_row and sol_row[0] else 'MP')
        proveedor_oc = d.get('proveedor', 'Por definir')
        valor_oc = float(d.get('valor_total') or 0)
        fent_oc = d.get('fecha_entrega_est', '')
        obs_oc = d.get('observaciones_oc') or f'Generado desde {numero.upper()}'
        cur.execute("SELECT COUNT(*) FROM ordenes_compra")
        n_oc = cur.fetchone()[0] + 1
        oc_num = f"OC-{datetime.now().year}-{n_oc:04d}"
        # OC creada directamente como 'Revisada' — lista para autorizar
        cur.execute(
            "INSERT INTO ordenes_compra "
            "(numero_oc, fecha, estado, proveedor, observaciones, creado_por, valor_total, fecha_entrega_est, categoria) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (oc_num, datetime.now().isoformat(), 'Revisada', proveedor_oc,
             obs_oc, session.get('compras_user',''),
             valor_oc if valor_oc > 0 else None, fent_oc or None, categoria_oc))
        for it in items_sol:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (oc_num, it[0], it[1], it[2]))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (oc_num, numero.upper()))
        oc_creada = oc_num"""

    if old_insert not in src:
        print("ERROR: patron backend no encontrado en compras.py — verificar manualmente")
        return False

    src = src.replace(old_insert, new_insert, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK backend: OC se crea como 'Revisada' con valor/fecha/categoria")
    return True


# ─── FRONTEND ───────────────────────────────────────────────────────────

def patch_frontend():
    path = f"{REPO}/api/templates_py/compras_html.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # ---------- 2. Agregar input oculto sol-cat en el form de gestión ----------
    old_hidden = "      h+='<input type=\"hidden\" id=\"sol-det-num\" value=\"'+esc(s.numero||num)+'\">';"
    new_hidden = (
        "      h+='<input type=\"hidden\" id=\"sol-det-num\" value=\"'+esc(s.numero||num)+'\">';\n"
        "      h+='<input type=\"hidden\" id=\"sol-det-cat\" value=\"'+esc(s.categoria||'MP')+'\">';"
    )
    if old_hidden not in src:
        print("ERROR: patron hidden input no encontrado en compras_html.py")
        return False
    src = src.replace(old_hidden, new_hidden, 1)
    print("OK frontend: hidden input sol-det-cat agregado")

    # ---------- 3. Cambiar botón "Aprobar y crear OC" → "Enviar a Autorización" ----------
    old_btn = "      fbtns+='<button class=\"btn bg\" onclick=\"_solDetApr()\">&#10003; Aprobar y crear OC</button>';"
    new_btn = "      fbtns+='<button class=\"btn bg\" onclick=\"_solDetApr()\">&#9654; Enviar a Autorizaci\u00f3n</button>';"
    if old_btn not in src:
        print("ERROR: patron boton aprobar no encontrado")
        return False
    src = src.replace(old_btn, new_btn, 1)
    print("OK frontend: botón cambiado a 'Enviar a Autorización'")

    # ---------- 4. gestionarSol: pasar valor, fent y categoria ----------
    old_gestion = """  var body={estado:decision,observaciones:motivo};
  if(decision==='Aprobada'){
    body.crear_oc=true;
    body.proveedor=prov||'Por definir';
  }"""
    new_gestion = """  var body={estado:decision,observaciones:motivo};
  if(decision==='Aprobada'){
    body.crear_oc=true;
    body.proveedor=prov||'Por definir';
    if(valor>0) body.valor_total=valor;
    if(fent) body.fecha_entrega_est=fent;
    var catEl=document.getElementById('sol-det-cat');
    if(catEl) body.categoria=catEl.value;
    body.observaciones_oc=motivo||('Generado desde '+num);
  }"""
    if old_gestion not in src:
        print("ERROR: patron gestionarSol no encontrado")
        return False
    src = src.replace(old_gestion, new_gestion, 1)
    print("OK frontend: gestionarSol pasa valor/fecha/categoria al backend")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    return True


# ─── VERIFICACIÓN ───────────────────────────────────────────────────────

def verify():
    print("\n--- VERIFICACION ---")

    path_b = f"{REPO}/api/blueprints/compras.py"
    with open(path_b) as f:
        bc = f.read()

    if "'Revisada'" in bc and "valor_total, fecha_entrega_est, categoria" in bc and "crear_oc" in bc:
        print("[OK] backend: OC se crea como Revisada con campos completos")
    else:
        print("[FAIL] backend: verificar manualmente")

    if "Borrador" not in bc[bc.find("crear_oc"):bc.find("crear_oc")+1200]:
        print("[OK] backend: 'Borrador' eliminado del flujo de solicitudes")
    else:
        print("[WARN] backend: todavia aparece 'Borrador' en el bloque crear_oc")

    path_f = f"{REPO}/api/templates_py/compras_html.py"
    with open(path_f) as f:
        fc = f.read()

    if "sol-det-cat" in fc:
        print("[OK] frontend: hidden input sol-det-cat presente")
    else:
        print("[FAIL] frontend: falta hidden input")

    if "Enviar a Autorizaci" in fc:
        print("[OK] frontend: botón dice 'Enviar a Autorización'")
    else:
        print("[FAIL] frontend: botón no actualizado")

    if "body.valor_total=valor" in fc:
        print("[OK] frontend: valor_total se pasa al backend")
    else:
        print("[FAIL] frontend: valor_total no se pasa")


# ─── PUSH ───────────────────────────────────────────────────────────────

def push_to_github():
    import subprocess, shutil
    TOKEN = "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"
    OWNER = "sebastianvargasisaza-prog"
    REPO_NAME = "Inventarios"
    CLONE_URL = f"https://{OWNER}:{TOKEN}@github.com/{OWNER}/{REPO_NAME}.git"
    CLONE_DIR = "/tmp/inv_push_compras"

    print("\n--- PUSH A GITHUB ---")
    if os.path.exists(CLONE_DIR):
        shutil.rmtree(CLONE_DIR)

    r = subprocess.run(["git", "clone", CLONE_URL, CLONE_DIR], capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR al clonar:", r.stderr)
        return False

    for fname in ["api/blueprints/compras.py", "api/templates_py/compras_html.py"]:
        src_f = f"{REPO}/{fname}"
        dst_f = f"{CLONE_DIR}/{fname}"
        os.makedirs(os.path.dirname(dst_f), exist_ok=True)
        with open(src_f, "rb") as fi, open(dst_f, "wb") as fo:
            fo.write(fi.read())

    subprocess.run(["git", "config", "user.email", "sebas@espagiria.com"], cwd=CLONE_DIR)
    subprocess.run(["git", "config", "user.name", "Sebastian"], cwd=CLONE_DIR)
    subprocess.run(["git", "add", "-A"], cwd=CLONE_DIR, capture_output=True)

    r3 = subprocess.run(
        ["git", "commit", "-m",
         "feat(compras): solicitud→OC Revisada en un paso; Catalina agrega proveedor/valor y envía a autorización"],
        cwd=CLONE_DIR, capture_output=True, text=True
    )
    if "nothing to commit" in r3.stdout:
        print("Nada que pushear")
        return True

    r4 = subprocess.run(["git", "push", "origin", "main"], cwd=CLONE_DIR, capture_output=True, text=True)
    if r4.returncode == 0:
        print("Push OK — Render desplegando en ~60s")
        return True
    else:
        print("ERROR en push:", r4.stderr)
        return False


if __name__ == "__main__":
    print("=== patch_compras_flow.py ===\n")
    ok1 = patch_backend()
    ok2 = patch_frontend()
    if ok1 and ok2:
        verify()
        push_to_github()
    else:
        print("\nPatch fallido — no se hizo push")
        sys.exit(1)
