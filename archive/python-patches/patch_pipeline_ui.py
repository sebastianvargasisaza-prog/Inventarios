"""
patch_pipeline_ui.py
====================
Mueve Envasado y Acondicionamiento al sub-tab de Produccion,
agrega cola automatica y endpoint de producciones-sin-envasar.

Correr desde la raiz del repo:
  python patch_pipeline_ui.py
"""
import re, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, 'api', 'templates_py', 'dashboard_html.py')
INV  = os.path.join(BASE, 'api', 'blueprints', 'inventario.py')

# ─── helpers ────────────────────────────────────────────────────────────────
def patch(path, old, new, label):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old not in content:
        print(f'  [SKIP] {label} — anchor not found')
        return
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  [OK]   {label}')

# ═══════════════════════════════════════════════════════════════════
# 1. dashboard_html.py — quitar Envasado y Acondicionamiento del nav
# ═══════════════════════════════════════════════════════════════════
patch(HTML,
    '    <button class="tab-button" onclick="switchTab(\'envasado\',this)">&#128230; Envasado</button>\n'
    '    <button class="tab-button" onclick="switchTab(\'acondicionamiento\',this)">&#128295; Acondicionamiento</button>\n',
    '',
    'Quitar Envasado y Acondicionamiento del nav top-level')

# ─── 2. Sub-tabs de Produccion: agregar Envasado y Acondicionamiento ────────
patch(HTML,
    '  <div id="bar-prodHub" class="sub-tab-bar">\n'
    '    <button class="sub-btn active" onclick="subSwitchTab(\'formulas\',this,\'bar-prodHub\')">&#129514; Fórmulas</button>\n'
    '    <button class="sub-btn" onclick="subSwitchTab(\'produccion\',this,\'bar-prodHub\')">&#127981; Lote</button>\n'
    '  </div>',
    '  <div id="bar-prodHub" class="sub-tab-bar">\n'
    '    <button class="sub-btn active" onclick="subSwitchTab(\'formulas\',this,\'bar-prodHub\')">&#129514; Fórmulas</button>\n'
    '    <button class="sub-btn" onclick="subSwitchTab(\'produccion\',this,\'bar-prodHub\')">&#127981; Fabricación</button>\n'
    '    <button class="sub-btn" onclick="subSwitchTab(\'envasado\',this,\'bar-prodHub\');loadColaSinEnvasar()">&#128230; Envasado</button>\n'
    '    <button class="sub-btn" onclick="subSwitchTab(\'acondicionamiento\',this,\'bar-prodHub\');loadAcond()">&#128295; Acondicionamiento</button>\n'
    '  </div>',
    'Sub-tabs Produccion: agregar Envasado y Acondicionamiento')

# ─── 3. Cola de lotes sin envasar — insertar al inicio del div envasado ─────
COLA_ENVASADO = (
    '<div id="cola-sin-envasar" style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;'
    'padding:14px;margin-bottom:18px">\n'
    '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">\n'
    '    <h3 style="margin:0;font-size:14px;color:#1b5e20">&#128230; Cola: lotes listos para envasar</h3>\n'
    '    <button onclick="loadColaSinEnvasar()" style="background:#1b5e20;color:#fff;border:none;'
    'border-radius:4px;padding:4px 12px;font-size:12px;cursor:pointer">&#8635; Actualizar</button>\n'
    '  </div>\n'
    '  <div id="cola-env-tbody-wrap" style="overflow-x:auto">\n'
    '    <table style="width:100%;border-collapse:collapse;font-size:13px">\n'
    '      <thead><tr style="background:#2e7d32;color:#fff">\n'
    '        <th style="padding:7px">Lote</th><th style="padding:7px">Producto</th>'
    '<th style="padding:7px">Batch (kg)</th><th style="padding:7px">Fecha</th>'
    '<th style="padding:7px">Operador</th><th style="padding:7px">Acción</th>\n'
    '      </tr></thead>\n'
    '      <tbody id="cola-env-tbody"><tr><td colspan="6" style="text-align:center;'
    'color:#999;padding:10px">Cargando...</td></tr></tbody>\n'
    '    </table>\n'
    '  </div>\n'
    '</div>\n'
)

patch(HTML,
    '<div id="envasado" class="tab-content">\n'
    '<div style="padding:18px">\n'
    '  <h2 style="margin:0 0 4px;color:#1a4a7a">&#128230; Envasado</h2>',
    '<div id="envasado" class="tab-content">\n'
    '<div style="padding:18px">\n'
    '  <h2 style="margin:0 0 4px;color:#1a4a7a">&#128230; Envasado</h2>',
    'Envasado div anchor (sin cambios, se agrega despues)')

# Insert cola before the form
patch(HTML,
    '  <p style="color:#666;font-size:13px;margin-bottom:16px">Registra el uso de envases y tapas por lote de produccion terminado.</p>\n'
    '\n'
    '  <div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">\n'
    '    <h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Envasado</h3>',
    '  <p style="color:#666;font-size:13px;margin-bottom:16px">Registra el uso de envases y tapas por lote de produccion terminado.</p>\n'
    '\n'
    + COLA_ENVASADO +
    '  <div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">\n'
    '    <h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Envasado</h3>',
    'Insertar cola sin-envasar al inicio del tab Envasado')

# ─── 4. Cola envasados-sin-acond — insertar al inicio del tab Acondicionamiento ─
COLA_ACOND = (
    '<div id="cola-sin-acond" style="background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;'
    'padding:14px;margin-bottom:18px">\n'
    '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">\n'
    '    <h3 style="margin:0;font-size:14px;color:#0d47a1">&#128295; Cola: lotes listos para acondicionar</h3>\n'
    '    <button onclick="loadAcond()" style="background:#0d47a1;color:#fff;border:none;'
    'border-radius:4px;padding:4px 12px;font-size:12px;cursor:pointer">&#8635; Actualizar</button>\n'
    '  </div>\n'
    '  <div style="overflow-x:auto">\n'
    '    <table style="width:100%;border-collapse:collapse;font-size:13px">\n'
    '      <thead><tr style="background:#1565c0;color:#fff">\n'
    '        <th style="padding:7px">Lote</th><th style="padding:7px">Producto</th>'
    '<th style="padding:7px">Uds</th><th style="padding:7px">Presentación</th>'
    '<th style="padding:7px">Fecha</th><th style="padding:7px">Acción</th>\n'
    '      </tr></thead>\n'
    '      <tbody id="cola-acond-tbody"><tr><td colspan="6" style="text-align:center;'
    'color:#999;padding:10px">Cargando...</td></tr></tbody>\n'
    '    </table>\n'
    '  </div>\n'
    '</div>\n'
)

patch(HTML,
    '<div id="acondicionamiento" class="tab-content">\n'
    '<div style="padding:18px">\n'
    '<h2 style="margin:0 0 14px;color:#1a4a7a">&#128230; Acondicionamiento PT</h2>\n'
    '<div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">\n'
    '<h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Batch de Acondicionamiento</h3>',
    '<div id="acondicionamiento" class="tab-content">\n'
    '<div style="padding:18px">\n'
    '<h2 style="margin:0 0 14px;color:#1a4a7a">&#128295; Acondicionamiento PT</h2>\n'
    + COLA_ACOND +
    '<div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">\n'
    '<h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Batch de Acondicionamiento</h3>',
    'Insertar cola envasados-sin-acond al inicio del tab Acondicionamiento')

# ─── 5. JS: loadColaSinEnvasar() + prefill form ──────────────────────────────
JS_COLA = """
function loadColaSinEnvasar() {
  var tb = document.getElementById('cola-env-tbody');
  if (!tb) return;
  tb.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/producciones/sin-envasar')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows = d.cola || [];
      if (!rows.length) {
        tb.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de envasar</td></tr>';
        return;
      }
      tb.innerHTML = rows.map(function(r){
        return '<tr style="border-bottom:1px solid #c8e6c9">' +
          '<td style="padding:7px;font-weight:600">' + (r.lote||'S/L') + '</td>' +
          '<td style="padding:7px">' + r.producto + '</td>' +
          '<td style="padding:7px;text-align:center">' + (r.cantidad_kg||0) + ' kg</td>' +
          '<td style="padding:7px">' + (r.fecha||'') + '</td>' +
          '<td style="padding:7px">' + (r.operador||'') + '</td>' +
          '<td style="padding:7px"><button onclick="prefillEnvasado(' + JSON.stringify(r) + ')" ' +
          'style="background:#1b5e20;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">' +
          '&#128393; Envasar</button></td>' +
          '</tr>';
      }).join('');
    })
    .catch(function(){ tb.innerHTML = '<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>'; });
}

function prefillEnvasado(lote_obj) {
  var sel = document.getElementById('env-prod-sel');
  if (sel) {
    for (var i=0; i<sel.options.length; i++) {
      if (sel.options[i].value === lote_obj.producto || sel.options[i].text.includes(lote_obj.producto)) {
        sel.value = sel.options[i].value; break;
      }
    }
  }
  var fl = document.getElementById('env-lote'); if (fl) fl.value = lote_obj.lote || '';
  var fp = document.getElementById('env-pres'); if (fp) fp.value = lote_obj.presentacion || '';
  document.getElementById('env-lote').scrollIntoView({behavior:'smooth',block:'center'});
}

function loadColaAcond() {
  var tb = document.getElementById('cola-acond-tbody');
  if (!tb) return;
  tb.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/envasado/pendientes-acond')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows = d.pendientes || [];
      if (!rows.length) {
        tb.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de acondicionar</td></tr>';
        return;
      }
      tb.innerHTML = rows.map(function(r){
        return '<tr style="border-bottom:1px solid #bbdefb">' +
          '<td style="padding:7px;font-weight:600">' + (r.lote||'S/L') + '</td>' +
          '<td style="padding:7px">' + r.producto + '</td>' +
          '<td style="padding:7px;text-align:center">' + (r.unidades||0) + '</td>' +
          '<td style="padding:7px">' + (r.presentacion||'') + '</td>' +
          '<td style="padding:7px">' + (r.fecha||'') + '</td>' +
          '<td style="padding:7px"><button onclick="prefillAcond(' + JSON.stringify(r) + ')" ' +
          'style="background:#0d47a1;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">' +
          '&#128393; Acondicionar</button></td>' +
          '</tr>';
      }).join('');
    })
    .catch(function(){ tb.innerHTML = '<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>'; });
}

function prefillAcond(env) {
  var fl = document.getElementById('ac-lote'); if (fl) fl.value = env.lote || '';
  var fp = document.getElementById('ac-prod'); if (fp) fp.value = env.producto || '';
  var fps = document.getElementById('ac-pres'); if (fps) fps.value = env.presentacion || '';
  var fb = document.getElementById('ac-batch'); if (fb) fb.value = env.batch_g || '';
  var fu = document.getElementById('ac-uds'); if (fu) fu.value = env.unidades || '';
  if (document.getElementById('ac-lote')) document.getElementById('ac-lote').scrollIntoView({behavior:'smooth',block:'center'});
}
"""

# Insert JS before closing </script> or before a known function
patch(HTML,
    'function loadColaSinEnvasar()',
    '// loadColaSinEnvasar already defined',
    'JS ya existe (skip)')

# If not already there, insert before loadAcond or end of script
with open(HTML, 'r', encoding='utf-8') as f:
    html_content = f.read()

if 'function loadColaSinEnvasar()' not in html_content and '// loadColaSinEnvasar already defined' not in html_content:
    anchor = 'function loadAcond()'
    if anchor in html_content:
        html_content = html_content.replace(anchor, JS_COLA + '\nfunction loadAcond()', 1)
        with open(HTML, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print('  [OK]   JS loadColaSinEnvasar + prefill insertado')
    else:
        print('  [WARN] No se encontro anchor para insertar JS — agregar manualmente')

# Also update loadAcond to call loadColaAcond
with open(HTML, 'r', encoding='utf-8') as f:
    html_content = f.read()
if 'loadColaAcond()' not in html_content:
    patch(HTML,
        'function loadAcond()',
        'function loadAcond() { try { loadColaAcond(); } catch(e){} }\nfunction _loadAcond_impl()',
        'loadAcond llama loadColaAcond')
    # Revert last patch if it broke things (loadAcond probably has a body already)
    with open(HTML, 'r', encoding='utf-8') as f:
        check = f.read()
    if 'function _loadAcond_impl()' in check:
        # Undo that — instead insert loadColaAcond() call at START of loadAcond body
        check = check.replace(
            'function loadAcond() { try { loadColaAcond(); } catch(e){} }\nfunction _loadAcond_impl()',
            'function loadAcond()',
            1)
        with open(HTML, 'w', encoding='utf-8') as f:
            f.write(check)

# ═══════════════════════════════════════════════════════════════════
# 6. inventario.py — endpoint /api/producciones/sin-envasar
# ═══════════════════════════════════════════════════════════════════
NEW_ENDPOINT = '''
@bp.route('/api/producciones/sin-envasar', methods=['GET'])
def producciones_sin_envasar():
    """Cola de producciones sin registro de envasado vinculado."""
    conn = get_db(); c = conn.cursor()
    c.execute("""
        SELECT p.id, p.lote, p.producto, p.cantidad, p.fecha, p.operador, p.presentacion
        FROM producciones p
        LEFT JOIN envasado e ON e.produccion_id = p.id
        WHERE e.id IS NULL
          AND COALESCE(p.estado,'') NOT IN ('cancelado','Cancelado')
        ORDER BY p.id DESC LIMIT 100
    """)
    cols = ['id','lote','producto','cantidad_kg','fecha','operador','presentacion']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'cola': rows})

'''

with open(INV, 'r', encoding='utf-8') as f:
    inv_content = f.read()

if '/api/producciones/sin-envasar' in inv_content:
    print('  [SKIP] endpoint sin-envasar ya existe')
else:
    # Insert before the envasado_list route
    anchor = "@bp.route('/api/envasado', methods=['GET', 'POST'])"
    if anchor in inv_content:
        inv_content = inv_content.replace(anchor, NEW_ENDPOINT + anchor, 1)
        with open(INV, 'w', encoding='utf-8') as f:
            f.write(inv_content)
        print('  [OK]   endpoint /api/producciones/sin-envasar agregado')
    else:
        print('  [WARN] anchor envasado route no encontrado')

print('\nListo. Corre: git add -A && git commit -m "feat: pipeline Fabricacion->Envasado->Acondicionamiento como sub-tabs" && git push origin main')
