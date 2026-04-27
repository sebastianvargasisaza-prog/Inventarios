#!/usr/bin/env python3
"""
Patch — Compras module redesign
Written with the Write tool (no bash heredoc, no ! corruption)
"""
import ast, shutil

SRC = '/sessions/magical-great-cray/mnt/Inventarios/api/index.py'
HTML_FILE = '/sessions/magical-great-cray/mnt/outputs/new_compras.html'
ENDPOINTS_FILE = '/sessions/magical-great-cray/mnt/outputs/new_endpoints.py'

shutil.copy(SRC, '/sessions/magical-great-cray/mnt/outputs/index_bak2.py')
content = open(SRC, 'r', errors='replace').read()
new_html = open(HTML_FILE, 'r').read()
new_endpoints = open(ENDPOINTS_FILE, 'r').read()
print(f"Original: {len(content)} chars, {content.count(chr(10))+1} lines")

# ── 1. MIGRATIONS ──────────────────────────────────────────────────────────
MIGS = """
    # Compras redesign migrations
    for _col in [
        "categoria TEXT DEFAULT 'MP'",
        "remision_code TEXT DEFAULT ''",
        "autorizado_por TEXT DEFAULT ''",
        "fecha_autorizacion TEXT DEFAULT ''",
        "pagado_por TEXT DEFAULT ''",
        "fecha_pago TEXT DEFAULT ''",
        "fecha_recepcion TEXT DEFAULT ''"
    ]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_col}")
        except: pass
"""
anchor = "    try:\n        c.execute(\"ALTER TABLE solicitudes_compra ADD COLUMN area TEXT DEFAULT 'Produccion'\")\n    except: pass"
if anchor in content:
    content = content.replace(anchor, anchor + MIGS, 1)
    print("OK migrations")
else:
    print("WARN migrations anchor not found")

# ── 2. REPLACE COMPRAS_HTML ─────────────────────────────────────────────────
BANG = chr(33)
start_marker = f'COMPRAS_HTML = """{chr(60)}{BANG}DOCTYPE html>'
end_marker = f'{chr(60)}/html>"""'

idx_s = content.find(start_marker)
idx_e = content.find(end_marker, idx_s + 100) if idx_s >= 0 else -1
print(f"COMPRAS_HTML bounds: {idx_s} to {idx_e}")

if idx_s >= 0 and idx_e >= 0:
    idx_e += len(end_marker)
    old_len = idx_e - idx_s
    new_block = 'COMPRAS_HTML = """' + new_html + '"""'
    content = content[:idx_s] + new_block + content[idx_e:]
    print(f"OK COMPRAS_HTML replaced: {old_len} -> {len(new_block)} chars")
else:
    print("ERR could not find COMPRAS_HTML bounds")
    exit(1)

# ── 3. UPDATE GET /api/ordenes-compra ──────────────────────────────────────
OLD_GET_FRAG = "GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 100"
idx_frag = content.find(OLD_GET_FRAG)
if idx_frag >= 0:
    block_start = content.rfind('    c.execute("""SELECT o.numero_oc', 0, idx_frag)
    ret_start = content.find("return jsonify({'ordenes':", block_start)
    ret_end = content.find('\n', ret_start) + 1
    NEW_GET = (
        "    cat_filter = request.args.get('categoria', '')\n"
        "    _sql = (\n"
        "        \"SELECT o.numero_oc, o.fecha, o.estado, o.proveedor, o.fecha_entrega_est,\"\n"
        "        \" o.observaciones, o.creado_por, COUNT(i.id) as num_items,\"\n"
        "        \" o.categoria, o.remision_code, o.autorizado_por,\"\n"
        "        \" COALESCE(o.valor_total, 0) as valor_total\"\n"
        "        \" FROM ordenes_compra o LEFT JOIN ordenes_compra_items i ON o.numero_oc=i.numero_oc\"\n"
        "    )\n"
        "    if cat_filter:\n"
        "        c.execute(_sql + \" WHERE o.categoria=? GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300\", (cat_filter,))\n"
        "    else:\n"
        "        c.execute(_sql + \" GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300\")\n"
        "    cols = ['numero_oc','fecha','estado','proveedor','fecha_entrega_est','observaciones',\n"
        "            'creado_por','num_items','categoria','remision_code','autorizado_por','valor_total']\n"
        "    rows = c.fetchall(); conn.close()\n"
        "    return jsonify({'ordenes': [dict(zip(cols, r)) for r in rows]})\n"
    )
    content = content[:block_start] + NEW_GET + content[ret_end:]
    print("OK GET /api/ordenes-compra updated")
else:
    print("WARN GET ordenes-compra fragment not found")

# ── 4. UPDATE POST to accept categoria and calc valor_total ─────────────────
OLD_INSERT = (
    "        c.execute(\"INSERT INTO ordenes_compra "
    "(numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est) VALUES (?,?,?,?,?,?,?)\",\n"
    "                  (numero_oc, datetime.now().isoformat(), 'Pendiente', d['proveedor'],\n"
    "                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est','')))"
)
NEW_INSERT = (
    "        categoria = d.get('categoria', 'MP')\n"
    "        c.execute(\"INSERT INTO ordenes_compra "
    "(numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est,categoria) VALUES (?,?,?,?,?,?,?,?)\",\n"
    "                  (numero_oc, datetime.now().isoformat(), 'Borrador', d['proveedor'],\n"
    "                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est',''), categoria))"
)
if OLD_INSERT in content:
    content = content.replace(OLD_INSERT, NEW_INSERT, 1)
    print("OK POST insert updated")
else:
    print("WARN POST insert not found")

OLD_COMMIT = (
    "        conn.commit(); conn.close()\n"
    "        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201"
)
NEW_COMMIT = (
    "        valor_total_calc = sum(\n"
    "            round((it.get('cantidad_g',0))*(it.get('precio_unitario',0)),2)\n"
    "            for it in (d.get('items') or [])\n"
    "        )\n"
    "        if valor_total_calc > 0:\n"
    "            c.execute(\"UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?\", (valor_total_calc, numero_oc))\n"
    "        conn.commit(); conn.close()\n"
    "        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201"
)
if OLD_COMMIT in content:
    content = content.replace(OLD_COMMIT, NEW_COMMIT, 1)
    print("OK valor_total calc added")
else:
    print("WARN commit anchor not found")

# ── 5. UPDATE single OC GET to return dict ──────────────────────────────────
OLD_GET_S = (
    "    c.execute(\"SELECT * FROM ordenes_compra WHERE numero_oc=?\", (numero_oc,))\n"
    "    oc = c.fetchone()\n"
    "    c.execute(\"SELECT * FROM ordenes_compra_items WHERE numero_oc=?\", (numero_oc,))\n"
    "    items = c.fetchall(); conn.close()\n"
    "    if not oc: return jsonify({'error': 'OC no encontrada'}), 404\n"
    "    return jsonify({'oc': oc, 'items': items})"
)
NEW_GET_S = (
    "    c.execute(\"SELECT * FROM ordenes_compra WHERE numero_oc=?\", (numero_oc,))\n"
    "    oc_row = c.fetchone()\n"
    "    oc_cols = [d[0] for d in c.description] if c.description else []\n"
    "    c.execute(\"SELECT * FROM ordenes_compra_items WHERE numero_oc=?\", (numero_oc,))\n"
    "    items = c.fetchall(); conn.close()\n"
    "    if not oc_row: return jsonify({'error': 'OC no encontrada'}), 404\n"
    "    return jsonify({'oc': dict(zip(oc_cols, oc_row)), 'items': items})"
)
if OLD_GET_S in content:
    content = content.replace(OLD_GET_S, NEW_GET_S, 1)
    print("OK single OC GET -> dict")
else:
    print("WARN single OC GET not found")

# ── 6. UPDATE recibir_oc for MEE auto-routing ───────────────────────────────
OLD_RECIBIR_FRAG = (
    "    cur.execute(\"UPDATE ordenes_compra SET estado='Recibida' WHERE numero_oc=?\", (numero_oc,))\n"
    "    conn.commit(); conn.close()\n"
    "    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': len(items_oc)})"
)
idx_rec = content.find(OLD_RECIBIR_FRAG)
if idx_rec >= 0:
    func_start = content.rfind("@app.route('/api/ordenes-compra/<numero_oc>/recibir'", 0, idx_rec)
    func_end = idx_rec + len(OLD_RECIBIR_FRAG)
    NEW_RECIBIR = (
        "@app.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])\n"
        "def recibir_oc(numero_oc):\n"
        "    if 'compras_user' not in session:\n"
        "        return jsonify({'error': 'No autorizado'}), 401\n"
        "    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()\n"
        "    cur.execute(\"SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?\", (numero_oc,))\n"
        "    oc_row = cur.fetchone()\n"
        "    if not oc_row:\n"
        "        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404\n"
        "    prov_nombre = oc_row[1] or ''\n"
        "    categoria = oc_row[2] or 'MP'\n"
        "    cur.execute(\"SELECT codigo_mp, nombre_mp, cantidad_g FROM ordenes_compra_items WHERE numero_oc=?\", (numero_oc,))\n"
        "    items_oc = cur.fetchall()\n"
        "    fecha = datetime.now().isoformat()\n"
        "    operador = session.get('compras_user', '')\n"
        "    ingresos = 0\n"
        "    for item in items_oc:\n"
        "        codigo, nombre, cantidad = item\n"
        "        if categoria == 'MEE':\n"
        "            cur.execute(\"UPDATE maestro_mee SET stock_actual = stock_actual + ? WHERE codigo=?\", (cantidad, codigo))\n"
        "            cur.execute(\"INSERT INTO movimientos_mee (codigo_mee, tipo, cantidad, referencia, observaciones, operador, fecha) VALUES (?,?,?,?,?,?,?)\",\n"
        "                       (codigo, 'entrada', cantidad, numero_oc, f'Recepcion OC {numero_oc}', operador, fecha))\n"
        "        else:\n"
        "            cur.execute(\"INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, proveedor, operador) VALUES (?,?,?,?,?,?,?,?)\",\n"
        "                       (codigo, nombre, cantidad, 'Entrada', fecha, f'Recepcion OC {numero_oc}', prov_nombre, operador))\n"
        "        ingresos += 1\n"
        "    cur.execute(\"UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=? WHERE numero_oc=?\", (fecha, numero_oc))\n"
        "    conn.commit(); conn.close()\n"
        "    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos})"
    )
    content = content[:func_start] + NEW_RECIBIR + content[func_end:]
    print("OK recibir_oc updated with MEE routing")
else:
    print("WARN recibir_oc fragment not found")

# ── 7. INSERT NEW ENDPOINTS ─────────────────────────────────────────────────
AFTER_ANCHOR = "    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos})"
idx_after = content.find(AFTER_ANCHOR)
if idx_after >= 0:
    insert_pt = idx_after + len(AFTER_ANCHOR)
    content = content[:insert_pt] + "\n" + new_endpoints + content[insert_pt:]
    print("OK new endpoints inserted")
else:
    print("WARN new endpoints insertion point not found")

# ── VALIDATE + WRITE ────────────────────────────────────────────────────────
print(f"\nFinal: {len(content)} chars, {content.count(chr(10))+1} lines")
try:
    ast.parse(content)
    print("OK Python syntax valid")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    lines = content.split('\n')
    ln = e.lineno or 0
    for i in range(max(0, ln-4), min(len(lines), ln+4)):
        marker = " <<< ERROR" if i+1 == ln else ""
        print(f"  L{i+1}: {lines[i][:130]}{marker}")
    exit(1)

with open(SRC, 'w') as f:
    f.write(content)
print(f"Written to {SRC}")
