#!/usr/bin/env python3
# patch_recepcion3.py - Adds standalone /recepcion panel + monitoring
import re, os, subprocess, shutil

SRC = '/sessions/magical-great-cray/mnt/Inventarios/api/index.py'

content = open(SRC, 'r').read()

# ─────────────────────────────────────────────
# 0. Guard
# ─────────────────────────────────────────────
html_already = 'RECEPCION_HTML' in content
routes_already = '/api/recepcion/seguimiento' in content
migration_already = 'observaciones_recepcion' in content

# ─────────────────────────────────────────────
# 1. RECEPCION_HTML  (raw string)
# ─────────────────────────────────────────────
RECEPCION_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Recepcion - Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f8f7f5;color:#1C1917;font-size:14px;}
.topbar{background:#292524;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:18px;font-weight:600;}
.topbar a{color:#a8a29e;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px;margin-bottom:20px;}
.card h2{font-size:16px;font-weight:600;margin-bottom:16px;color:#292524;}
.search-row{display:flex;gap:10px;align-items:center;margin-bottom:16px;}
.search-row input{flex:1;max-width:320px;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:14px;}
.search-row input:focus{outline:none;border-color:#57534e;}
.btn{padding:9px 18px;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:500;}
.btn-primary{background:#292524;color:#fff;}
.btn-primary:hover{background:#1c1917;}
.btn-success{background:#16a34a;color:#fff;}
.btn-success:hover{background:#15803d;}
.oc-info{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;}
.oc-info .lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;}
.oc-info .val{font-size:14px;font-weight:600;color:#292524;margin-top:2px;}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;}
.badge-autorizada{background:#fef3c7;color:#92400e;}
.badge-pagada{background:#d1fae5;color:#065f46;}
.badge-recibida{background:#dbeafe;color:#1e40af;}
.badge-borrador{background:#f3f4f6;color:#374151;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f5f5f4;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;}
td{padding:8px 12px;border-bottom:1px solid #f5f5f4;vertical-align:middle;}
tr:hover td{background:#fafaf9;}
td input[type=number]{width:90px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
td input[type=number]:focus{outline:none;border-color:#57534e;}
td select{padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;background:#fff;}
td input[type=text]{width:100%;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
.obs-row{margin-top:12px;}
.obs-row label{font-size:13px;font-weight:600;display:block;margin-bottom:6px;color:#292524;}
.obs-row textarea{width:100%;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;min-height:72px;}
.receptor-row{display:flex;gap:12px;align-items:center;margin-top:12px;}
.receptor-row label{font-size:13px;font-weight:600;white-space:nowrap;color:#292524;}
.receptor-row input{flex:1;max-width:260px;padding:8px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.submit-row{margin-top:16px;display:flex;align-items:center;gap:12px;}
.msg{font-size:13px;padding:8px 14px;border-radius:6px;display:none;}
.msg-ok{background:#d1fae5;color:#065f46;}
.msg-err{background:#fee2e2;color:#991b1b;}
.tabs{display:flex;gap:2px;margin-bottom:16px;border-bottom:2px solid #e7e5e4;}
.tab-btn{padding:9px 18px;border:none;background:none;font-size:13px;font-weight:500;color:#78716c;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;}
.tab-btn.active{color:#292524;border-bottom-color:#292524;}
.tab-btn:hover{color:#292524;}
.tab-content{display:none;}
.tab-content.active{display:block;}
.empty{text-align:center;padding:32px;color:#a8a29e;font-size:13px;}
.cnt-badge{display:inline-block;background:#292524;color:#fff;border-radius:20px;font-size:11px;padding:1px 7px;margin-left:4px;}
.disc{color:#dc2626;font-weight:600;}
.valor{font-family:'Courier New',monospace;font-size:12px;}
</style>
</head>
<body>
<div class="topbar">
  <h1>Recepcion de Mercancia</h1>
  <a href="/compras">Modulo de Compras</a>
</div>
<div class="container">

  <div class="card">
    <h2>Registrar Recepcion de OC</h2>
    <div class="search-row">
      <input type="text" id="oc-input" placeholder="Numero de OC (ej: OC-2026-001)" onkeydown="if(event.key==='Enter')buscarOC()">
      <button class="btn btn-primary" onclick="buscarOC()">Buscar</button>
    </div>
    <div id="oc-msg" class="msg"></div>

    <div id="oc-section" style="display:none">
      <div class="oc-info" id="oc-header"></div>

      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Material</th>
              <th>Solicitado</th>
              <th>Cantidad Recibida</th>
              <th>Estado</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody id="items-body"></tbody>
        </table>
      </div>

      <div class="receptor-row">
        <label for="receptor-input">Recibido por:</label>
        <input type="text" id="receptor-input" placeholder="Tu nombre">
      </div>

      <div class="obs-row">
        <label>Observaciones generales (danos, faltantes, condicion del paquete, etc.):</label>
        <textarea id="obs-input" placeholder="Ej: Caja exterior golpeada pero producto en buen estado. Falto 1 item."></textarea>
      </div>

      <div class="submit-row">
        <button class="btn btn-success" onclick="registrarRecepcion()">Registrar Recepcion</button>
        <div id="submit-msg" class="msg"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Monitoreo: Pagado - Llego?</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-transito" onclick="showTab('transito')">
        En Transito <span class="cnt-badge" id="cnt-transito">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-recibidas" onclick="showTab('recibidas')">
        Recibidas <span class="cnt-badge" id="cnt-recibidas">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-disc" onclick="showTab('disc')">
        Con Discrepancias <span class="cnt-badge" id="cnt-disc">0</span>
      </button>
    </div>
    <div id="tab-transito" class="tab-content active"></div>
    <div id="tab-recibidas" class="tab-content"></div>
    <div id="tab-disc" class="tab-content"></div>
  </div>

</div>
<script>
var currentOC = null;

async function buscarOC() {
  var num = document.getElementById('oc-input').value.trim().toUpperCase();
  if (num.length === 0) return;
  showMsg('oc-msg','','');
  try {
    var r = await fetch('/api/recepcion/detalle/' + encodeURIComponent(num));
    var d = await r.json();
    if (r.ok === false || d.error) {
      showMsg('oc-msg', d.error || 'OC no encontrada', 'err');
      document.getElementById('oc-section').style.display='none';
      return;
    }
    currentOC = d;
    renderOC(d);
    document.getElementById('oc-section').style.display='block';
  } catch(e) { showMsg('oc-msg','Error de red: '+e.message,'err'); }
}

function renderOC(d) {
  var badgeCls = 'badge-' + (d.estado||'').toLowerCase();
  document.getElementById('oc-header').innerHTML =
    '<div><div class="lbl">OC</div><div class="val">'+d.numero_oc+'</div></div>' +
    '<div><div class="lbl">Proveedor</div><div class="val">'+d.proveedor+'</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">'+(d.fecha||'').slice(0,10)+'</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val"><span class="badge '+badgeCls+'">'+d.estado+'</span></div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$'+Number(d.valor_total||0).toLocaleString()+'</div></div>' +
    '<div><div class="lbl">Categoria</div><div class="val">'+(d.categoria||'MP')+'</div></div>';

  var tbody = document.getElementById('items-body');
  tbody.innerHTML = '';
  var items = d.items || [];
  for (var idx = 0; idx < items.length; idx++) {
    var it = items[idx];
    var unidad = (d.categoria === 'MEE') ? 'uds' : 'g';
    var prevRec = (it.cantidad_recibida_g > 0) ? it.cantidad_recibida_g : it.cantidad_g;
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><strong>'+it.nombre_mp+'</strong><br><small style="color:#78716c">'+it.codigo_mp+'</small></td>' +
      '<td class="valor">'+Number(it.cantidad_g||0).toLocaleString()+' '+unidad+'</td>' +
      '<td><input type="number" id="cant-'+idx+'" data-codigo="'+it.codigo_mp+'" value="'+prevRec+'" min="0" step="0.01"></td>' +
      '<td><select id="est-'+idx+'">' +
        '<option value="OK">OK - Conforme</option>' +
        '<option value="Incompleto">Incompleto</option>' +
        '<option value="Danado">Danado</option>' +
        '<option value="NoLlego">No llego</option>' +
      '</select></td>' +
      '<td><input type="text" id="nota-'+idx+'" placeholder="Observacion opcional"></td>';
    tbody.appendChild(tr);
  }
}

async function registrarRecepcion() {
  if (currentOC === null) return;
  var obs = document.getElementById('obs-input').value.trim();
  var receptor = document.getElementById('receptor-input').value.trim();
  var items = [];
  var discrepancias = false;
  var ocItems = currentOC.items || [];
  for (var idx = 0; idx < ocItems.length; idx++) {
    var it = ocItems[idx];
    var cantEl = document.getElementById('cant-'+idx);
    var estEl = document.getElementById('est-'+idx);
    var notaEl = document.getElementById('nota-'+idx);
    var cant = cantEl ? (parseFloat(cantEl.value) || 0) : 0;
    var est = estEl ? estEl.value : 'OK';
    var nota = notaEl ? notaEl.value.trim() : '';
    if (est !== 'OK' || cant < it.cantidad_g) discrepancias = true;
    items.push({codigo_mp: it.codigo_mp, cantidad_recibida: cant, estado: est, notas: nota});
  }
  var payload = {
    observaciones_recepcion: obs,
    tiene_discrepancias: discrepancias ? 1 : 0,
    items_recepcion: items,
    receptor_nombre: receptor
  };
  showMsg('submit-msg', 'Registrando...', '');
  try {
    var r = await fetch('/api/ordenes-compra/' + encodeURIComponent(currentOC.numero_oc) + '/recibir', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    var d = await r.json();
    if (d.ok) {
      showMsg('submit-msg', 'Recepcion registrada. ' + (d.ingresos||0) + ' item(s) ingresado(s).', 'ok');
      document.getElementById('oc-section').style.display = 'none';
      currentOC = null;
      document.getElementById('oc-input').value = '';
      document.getElementById('obs-input').value = '';
      loadMonitoreo();
    } else {
      showMsg('submit-msg', d.error || 'Error al registrar', 'err');
    }
  } catch(e) { showMsg('submit-msg', 'Error de red: '+e.message, 'err'); }
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (el === null) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  var tabs = ['transito','recibidas','disc'];
  for (var i = 0; i < tabs.length; i++) {
    var t = tabs[i];
    document.getElementById('tab-'+t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-'+t).classList.toggle('active', t === name);
  }
}

function fmtDate(s) { return s ? String(s).slice(0,10) : '-'; }
function fmtVal(v) { return '$' + Number(v||0).toLocaleString(); }

function buildTable(rows) {
  if (rows.length === 0) return '<div class="empty">Sin registros</div>';
  var h = '<div style="overflow-x:auto"><table><thead><tr>' +
    '<th>OC</th><th>Proveedor</th><th>Cat.</th><th>Valor</th>' +
    '<th>Fecha OC</th><th>F. Aut.</th><th>F. Pago</th><th>F. Recepcion</th><th>Observaciones</th>' +
    '</tr></thead><tbody>';
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var disc = row.tiene_discrepancias ? '<span class="disc"> DISC</span>' : '';
    h += '<tr>' +
      '<td><strong>'+row.numero_oc+'</strong>'+disc+'</td>' +
      '<td>'+row.proveedor+'</td>' +
      '<td>'+row.categoria+'</td>' +
      '<td class="valor">'+fmtVal(row.valor_total)+'</td>' +
      '<td>'+fmtDate(row.fecha)+'</td>' +
      '<td>'+fmtDate(row.fecha_autorizacion)+'</td>' +
      '<td>'+fmtDate(row.fecha_pago)+'</td>' +
      '<td>'+(row.fecha_recepcion ? fmtDate(row.fecha_recepcion) : '<span style="color:#d97706">Pendiente</span>')+'</td>' +
      '<td style="max-width:200px;color:#57534e">'+(row.observaciones||'-')+'</td>' +
      '</tr>';
  }
  h += '</tbody></table></div>';
  return h;
}

async function loadMonitoreo() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (Array.isArray(all) === false) all = [];
    var transito = all.filter(function(x){ return x.estado === 'Autorizada' && (x.fecha_recepcion === '' || x.fecha_recepcion === null); });
    var recibidas = all.filter(function(x){ return x.fecha_recepcion && x.fecha_recepcion.length > 2; });
    var disc = all.filter(function(x){ return x.tiene_discrepancias; });
    document.getElementById('cnt-transito').textContent = transito.length;
    document.getElementById('cnt-recibidas').textContent = recibidas.length;
    document.getElementById('cnt-disc').textContent = disc.length;
    document.getElementById('tab-transito').innerHTML = buildTable(transito);
    document.getElementById('tab-recibidas').innerHTML = buildTable(recibidas);
    document.getElementById('tab-disc').innerHTML = buildTable(disc);
  } catch(e) {
    console.error('Error cargando monitoreo:', e);
  }
}

loadMonitoreo();
</script>
</body>
</html>"""

# ─────────────────────────────────────────────
# 2. Insert RECEPCION_HTML before SOLICITUDES_HTML
# ─────────────────────────────────────────────
SOLICITUDES_MARKER = 'SOLICITUDES_HTML = """'

if not html_already:
    tri = chr(34) * 3
    insertion = 'RECEPCION_HTML = r' + tri + '\n' + RECEPCION_HTML + '\n' + tri + '\n\n'
    idx = content.find(SOLICITUDES_MARKER)
    if idx == -1:
        print('ERROR: SOLICITUDES_HTML marker not found'); exit(1)
    content = content[:idx] + insertion + content[idx:]
    print('Inserted RECEPCION_HTML (%d chars)' % len(RECEPCION_HTML))
else:
    print('RECEPCION_HTML already present, skipping')

# ─────────────────────────────────────────────
# 3. Enhance recibir_oc
# ─────────────────────────────────────────────
OLD_END = (
    "    cur.execute(\"UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=? WHERE numero_oc=?\", (fecha, numero_oc))\n"
    "    conn.commit(); conn.close()\n"
    "    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos})"
)

NEW_END = (
    "    data2 = request.get_json(silent=True) or {}\n"
    "    obs_r = data2.get('observaciones_recepcion', '')\n"
    "    disc_r = 1 if data2.get('tiene_discrepancias') else 0\n"
    "    items_r = data2.get('items_recepcion', [])\n"
    "    receptor_nombre = data2.get('receptor_nombre', '') or operador\n"
    "    for ir in items_r:\n"
    "        try:\n"
    "            cur.execute(\n"
    "                \"UPDATE ordenes_compra_items SET cantidad_recibida_g=?, estado_recepcion=?, notas_recepcion=?\"\n"
    "                \" WHERE numero_oc=? AND codigo_mp=?\",\n"
    "                (float(ir.get('cantidad_recibida', 0)), ir.get('estado', 'OK'), ir.get('notas', ''), numero_oc, ir.get('codigo_mp', '')))\n"
    "        except Exception:\n"
    "            pass\n"
    "    try:\n"
    "        cur.execute(\n"
    "            \"UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=?,\"\n"
    "            \" observaciones_recepcion=?, tiene_discrepancias=?, recibido_por=? WHERE numero_oc=?\",\n"
    "            (fecha, obs_r, disc_r, receptor_nombre, numero_oc))\n"
    "    except Exception:\n"
    "        cur.execute(\"UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=? WHERE numero_oc=?\", (fecha, numero_oc))\n"
    "    conn.commit(); conn.close()\n"
    "    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos})"
)

if OLD_END in content:
    content = content.replace(OLD_END, NEW_END, 1)
    print('Enhanced recibir_oc')
elif 'receptor_nombre' in content:
    print('recibir_oc already enhanced, skipping')
else:
    print('WARNING: recibir_oc end pattern not found')

# ─────────────────────────────────────────────
# 4. New routes
# ─────────────────────────────────────────────
if not routes_already:
    NR = '''

# ─── Panel de Recepcion — rutas standalone ────────────────────────────────────

@app.route('/recepcion')
def recepcion_panel():
    return Response(RECEPCION_HTML, mimetype='text/html')


@app.route('/api/recepcion/detalle/<numero_oc>')
def recepcion_detalle_oc(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, proveedor, estado, categoria, fecha, '
        'COALESCE(valor_total,0), creado_por, observaciones '
        'FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    oc = c.fetchone()
    if oc is None:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    c.execute(
        'SELECT codigo_mp, nombre_mp, COALESCE(cantidad_g,0), '
        'COALESCE(precio_unitario,0), COALESCE(cantidad_recibida_g,0), '
        'COALESCE(lote_asignado,"") '
        'FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
    items = c.fetchall()
    conn.close()
    return jsonify({
        'numero_oc': oc[0], 'proveedor': oc[1], 'estado': oc[2],
        'categoria': oc[3], 'fecha': oc[4], 'valor_total': oc[5],
        'creado_por': oc[6], 'observaciones': oc[7],
        'items': [
            {'codigo_mp': i[0], 'nombre_mp': i[1], 'cantidad_g': i[2],
             'precio_unitario': i[3], 'cantidad_recibida_g': i[4], 'lote_asignado': i[5]}
            for i in items
        ]
    })


@app.route('/api/recepcion/seguimiento')
def recepcion_seguimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, fecha, estado, proveedor, categoria, '
        'COALESCE(valor_total,0), COALESCE(fecha_recepcion,""), '
        'COALESCE(observaciones_recepcion,""), COALESCE(tiene_discrepancias,0), '
        'COALESCE(fecha_pago,""), COALESCE(fecha_autorizacion,"") '
        "FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Pagada') "
        'ORDER BY fecha DESC LIMIT 200')
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {'numero_oc': r[0], 'fecha': r[1], 'estado': r[2], 'proveedor': r[3],
         'categoria': r[4], 'valor_total': r[5], 'fecha_recepcion': r[6],
         'observaciones': r[7], 'tiene_discrepancias': r[8],
         'fecha_pago': r[9], 'fecha_autorizacion': r[10]}
        for r in rows
    ])

'''
    MAIN_MARKER = "if __name__ == '__main__':"
    idx = content.rfind(MAIN_MARKER)
    if idx == -1:
        print('ERROR: __main__ marker not found'); exit(1)
    content = content[:idx] + NR + content[idx:]
    print('Inserted new routes')
else:
    print('Routes already present, skipping')

# ─────────────────────────────────────────────
# 5. DB Migrations
# ─────────────────────────────────────────────
if not migration_already:
    OLD_MIG = (
        '        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_col}")\n'
        '        except: pass'
    )
    NEW_MIG = (
        '        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_col}")\n'
        '        except: pass\n'
        '    # Reception tracking columns\n'
        "    for _rc in [\"observaciones_recepcion TEXT DEFAULT ''\", \"tiene_discrepancias INTEGER DEFAULT 0\"]:\n"
        '        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_rc}")\n'
        '        except: pass\n'
        "    for _ri in [\"estado_recepcion TEXT DEFAULT 'OK'\", \"notas_recepcion TEXT DEFAULT ''\"]:\n"
        '        try: c.execute(f"ALTER TABLE ordenes_compra_items ADD COLUMN {_ri}")\n'
        '        except: pass'
    )
    if OLD_MIG in content:
        content = content.replace(OLD_MIG, NEW_MIG, 1)
        print('Added DB migrations')
    else:
        print('WARNING: migration marker not found — skipping DB migration')
else:
    print('DB migrations already present, skipping')

# ─────────────────────────────────────────────
# 6. Write back
# ─────────────────────────────────────────────
open(SRC, 'w').write(content)
print('Written: %s (%d lines)' % (SRC, content.count('\n')))

# ─────────────────────────────────────────────
# 7. Validate Python syntax
# ─────────────────────────────────────────────
r = subprocess.run(['python3', '-m', 'py_compile', SRC], capture_output=True, text=True)
if r.returncode != 0:
    print('PYTHON SYNTAX ERROR:')
    print(r.stderr)
    exit(1)
print('Python syntax OK')

# ─────────────────────────────────────────────
# 8. Push to GitHub
# ─────────────────────────────────────────────
REPO = '/tmp/inv_push'
TOKEN = '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'
REMOTE = 'https://' + TOKEN + '@github.com/sebastianvargasisaza-prog/Inventarios.git'

if os.path.exists(REPO):
    shutil.rmtree(REPO)

cmds = [
    'git clone ' + REMOTE + ' ' + REPO,
    'cp ' + SRC + ' ' + REPO + '/api/index.py',
    'cd ' + REPO + ' && git config user.email "patch@espagiria.co"',
    'cd ' + REPO + ' && git config user.name "PatchBot"',
    'cd ' + REPO + ' && git add api/index.py',
    'cd ' + REPO + ' && git commit -m "feat: /recepcion standalone panel + monitoring"',
    'cd ' + REPO + ' && git push origin main',
]
for cmd in cmds:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        label = cmd.split('&&')[-1].strip() if '&&' in cmd else cmd[:60]
        print('CMD FAILED: ' + label)
        print(res.stderr)
        exit(1)
    else:
        label = cmd.split('&&')[-1].strip() if '&&' in cmd else cmd[:60]
        print('OK: ' + label)

print('\nAll done - pushed to GitHub')
