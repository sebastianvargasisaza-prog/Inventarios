# salida_html.py — extraído de index.py (Fase C prep)
SALIDA_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Hub de Salida - ANIMUS Lab</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos8">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f8f7f5;color:#1C1917;font-size:14px;}
.topbar{background:#1C1917;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:18px;font-weight:600;}
.topbar a{color:#a8a29e;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.topbar .rec-link{background:#292524;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px;margin-bottom:20px;}
.card h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#292524;}
.ped-queue{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;margin-bottom:8px;}
.ped-card{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;cursor:pointer;transition:all .15s;border-left:3px solid #4A6741;}
.ped-card:hover{border-color:#292524;background:#f5f5f4;}
.ped-card.selected{border-left-color:#1e40af;background:#eff6ff;}
.ped-card .pn{font-weight:700;font-size:13px;}
.ped-card .pc{font-size:12px;color:#78716c;margin-top:2px;}
.ped-card .pv{font-size:12px;color:#4A6741;font-weight:600;margin-top:4px;}
.ped-card .pe{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;background:#fef3c7;color:#92400e;margin-top:4px;}
.ped-card .pe.prep{background:#dbeafe;color:#1e40af;}
.btn{padding:9px 18px;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:500;}
.btn-primary{background:#292524;color:#fff;}
.btn-primary:hover{background:#1c1917;}
.btn-success{background:#4A6741;color:#fff;}
.btn-success:hover{background:#3a5331;}
.btn-print{background:#1e40af;color:#fff;}
.btn-print:hover{background:#1d4ed8;}
.btn-sm{padding:5px 12px;font-size:12px;}
.ped-info{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;}
.ped-info .lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;}
.ped-info .val{font-size:14px;font-weight:600;color:#292524;margin-top:2px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f5f5f4;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;}
td{padding:8px 12px;border-bottom:1px solid #f5f5f4;vertical-align:middle;}
tr:hover td{background:#fafaf9;}
td input[type=number]{width:100px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
td input[type=text]{width:100%;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
.stock-ok{color:#16a34a;font-weight:600;}
.stock-low{color:#d97706;font-weight:600;}
.stock-zero{color:#dc2626;font-weight:600;}
.submit-row{margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.msg{font-size:13px;padding:8px 14px;border-radius:6px;}
.msg-ok{background:#d1fae5;color:#065f46;}
.msg-err{background:#fee2e2;color:#991b1b;}
.empty{text-align:center;padding:32px;color:#a8a29e;font-size:13px;}
.tabs{display:flex;gap:2px;margin-bottom:16px;border-bottom:2px solid #e7e5e4;}
.tab-btn{padding:9px 18px;border:none;background:none;font-size:13px;font-weight:500;color:#78716c;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;}
.tab-btn.active{color:#292524;border-bottom-color:#292524;}
.tab-btn:hover{color:#292524;}
.tab-content{display:none;}
.tab-content.active{display:block;}
.cnt-badge{display:inline-block;background:#292524;color:#fff;border-radius:20px;font-size:11px;padding:1px 7px;margin-left:4px;}
.section-title{font-size:13px;font-weight:600;color:#57534e;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M14 9h3l3 4v5h-2"/></svg>
      Hub de Salida
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; despachos de pedidos a clientes</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="container">

  <div class="card">
    <h2>&#128203; Pedidos Listos para Despachar</h2>
    <div id="ped-queue"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card" id="despacho-form-card" style="display:none;">
    <h2>&#128230; Preparar Despacho</h2>
    <div class="ped-info" id="ped-header"></div>

    <div class="section-title">Items del Pedido</div>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Descripcion</th>
            <th>Cant. Pedida</th>
            <th>Stock Disp.</th>
            <th>Cant. a Despachar</th>
            <th>Lote PT</th>
          </tr>
        </thead>
        <tbody id="despacho-body"></tbody>
      </table>
    </div>

    <div style="margin-top:16px;">
      <label style="font-size:13px;font-weight:600;display:block;margin-bottom:6px;">Observaciones del despacho:</label>
      <textarea id="despacho-obs" style="width:100%;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;min-height:60px;" placeholder="Condiciones de entrega, instrucciones especiales..."></textarea>
    </div>

    <div class="submit-row">
      <button class="btn btn-success" onclick="registrarDespacho()">&#10003; Confirmar Despacho</button>
      <button class="btn btn-print" onclick="previsualizarActa()">&#128438; Vista Previa Acta</button>
      <button class="btn btn-primary" onclick="cancelarDespacho()">Cancelar</button>
      <div id="despacho-msg"></div>
    </div>
  </div>

  <div class="card">
    <h2>&#128202; Historial de Despachos</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-recientes" onclick="showTab('recientes')">
        Recientes <span class="cnt-badge" id="cnt-recientes">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-pendientes" onclick="showTab('pendientes')">
        Pedidos Pendientes <span class="cnt-badge" id="cnt-pendientes">0</span>
      </button>
    </div>
    <div id="tab-recientes" class="tab-content active"></div>
    <div id="tab-pendientes" class="tab-content"></div>
  </div>

</div>
<script>
var currentPed = null;
var stockCache = {};

async function loadPedQueue() {
  try {
    var r = await fetch('/api/hub-salida/pedidos-pendientes');
    var d = await r.json();
    var peds = d.pedidos || [];
    var el = document.getElementById('ped-queue');
    if (!peds.length) {
      el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Sin pedidos listos para despachar.</p>';
      return;
    }
    var html = '<div class="ped-queue">';
    peds.forEach(function(p) {
      var estCls = (p.estado||'').toLowerCase().includes('prep') ? 'prep' : '';
      html += '<div class="ped-card" onclick="cargarPedido(\''  + p.numero + '\')" id="pc-' + p.numero + '">'
        + '<div class="pn">' + p.numero + '</div>'
        + '<div class="pc">' + (p.cliente||'Sin cliente') + '</div>'
        + '<div class="pv">$' + Number(p.valor_total||0).toLocaleString() + '</div>'
        + '<div><span class="pe ' + estCls + '">' + p.estado + '</span></div>'
        + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  } catch(e) { console.error(e); }
}

async function cargarPedido(num) {
  document.querySelectorAll('.ped-card').forEach(function(c) { c.classList.remove('selected'); });
  var card = document.getElementById('pc-' + num);
  if (card) card.classList.add('selected');
  try {
    var r = await fetch('/api/hub-salida/pedido/' + encodeURIComponent(num));
    var d = await r.json();
    if (d.error) { alert(d.error); return; }
    currentPed = d;
    await renderDespachoForm(d);
    document.getElementById('despacho-form-card').style.display = 'block';
    document.getElementById('despacho-form-card').scrollIntoView({behavior:'smooth'});
  } catch(e) { alert('Error: ' + e.message); }
}

async function renderDespachoForm(d) {
  document.getElementById('ped-header').innerHTML =
    '<div><div class="lbl">Pedido</div><div class="val">' + d.numero + '</div></div>' +
    '<div><div class="lbl">Cliente</div><div class="val">' + (d.cliente||'—') + '</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">' + (d.fecha||'').slice(0,10) + '</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val">' + (d.estado||'—') + '</div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(d.valor_total||0).toLocaleString() + '</div></div>';

  var tbody = document.getElementById('despacho-body');
  tbody.innerHTML = '';
  var items = d.items || [];
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    var stockData = await fetchStock(it.sku);
    var stockUds = stockData.total || 0;
    var stockCls = stockUds <= 0 ? 'stock-zero' : stockUds < it.cantidad ? 'stock-low' : 'stock-ok';
    var loteOpts = (stockData.lotes || []).map(function(l) {
      return '<option value="' + l.lote + '">' + l.lote + ' (' + l.disponible + ' uds)</option>';
    }).join('');
    if (!loteOpts) loteOpts = '<option value="">Sin lotes disponibles</option>';
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><strong>' + it.sku + '</strong></td>' +
      '<td>' + (it.descripcion||'—') + '</td>' +
      '<td>' + it.cantidad + ' uds</td>' +
      '<td class="' + stockCls + '">' + stockUds + ' uds</td>' +
      '<td><input type="number" id="dsp-cant-' + i + '" value="' + Math.min(it.cantidad, stockUds) + '" min="0" max="' + stockUds + '" step="1" data-sku="' + it.sku + '" data-desc="' + (it.descripcion||'') + '" data-precio="' + (it.precio_unitario||0) + '"></td>' +
      '<td><select id="dsp-lote-' + i + '">' + loteOpts + '</select></td>';
    tbody.appendChild(tr);
  }
}

async function fetchStock(sku) {
  if (stockCache[sku]) return stockCache[sku];
  try {
    var r = await fetch('/api/hub-salida/stock/' + encodeURIComponent(sku));
    var d = await r.json();
    stockCache[sku] = d;
    return d;
  } catch(e) { return {total: 0, lotes: []}; }
}

function previsualizarActa() {
  if (!currentPed) return;
  var items = buildDespachoItems();
  imprimirActaEntrega(currentPed, items, null, true);
}

function buildDespachoItems() {
  var items = [];
  var rows = document.querySelectorAll('#despacho-body tr');
  rows.forEach(function(tr, i) {
    var cantEl = document.getElementById('dsp-cant-' + i);
    var loteEl = document.getElementById('dsp-lote-' + i);
    if (!cantEl) return;
    items.push({
      sku: cantEl.dataset.sku,
      descripcion: cantEl.dataset.desc,
      cantidad: parseInt(cantEl.value) || 0,
      precio_unitario: parseFloat(cantEl.dataset.precio) || 0,
      lote_pt: loteEl ? loteEl.value : ''
    });
  });
  return items;
}

async function registrarDespacho() {
  if (!currentPed) return;
  var items = buildDespachoItems();
  var obs = document.getElementById('despacho-obs').value.trim();
  if (!items.length || items.every(function(it) { return it.cantidad <= 0; })) {
    showMsg('despacho-msg', 'Ingresa al menos un item con cantidad > 0', 'err'); return;
  }
  showMsg('despacho-msg', 'Registrando despacho...', '');
  try {
    var r = await fetch('/api/hub-salida/despachar', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({numero_pedido: currentPed.numero, cliente_id: currentPed.cliente_id, items: items, observaciones: obs})
    });
    var d = await r.json();
    if (d.numero) {
      showMsg('despacho-msg', 'Despacho ' + d.numero + ' registrado correctamente.', 'ok');
      imprimirActaEntrega(currentPed, items, d.numero, false);
      setTimeout(function() {
        document.getElementById('despacho-form-card').style.display = 'none';
        currentPed = null;
        stockCache = {};
        loadPedQueue();
        loadHistorial();
      }, 1200);
    } else {
      showMsg('despacho-msg', d.error || 'Error al registrar', 'err');
    }
  } catch(e) { showMsg('despacho-msg', 'Error: ' + e.message, 'err'); }
}

function imprimirActaEntrega(ped, items, numDespacho, preview) {
  var w = window.open('', '_blank', 'width=760,height=900,toolbar=0,scrollbars=1,resizable=1');
  var hoy = new Date().toLocaleString('es-CO');
  var totalUds = items.reduce(function(a, it) { return a + it.cantidad; }, 0);
  var totalVal = items.reduce(function(a, it) { return a + it.cantidad * it.precio_unitario; }, 0);
  var itemsHtml = items.filter(function(it) { return it.cantidad > 0; }).map(function(it) {
    var sub = it.cantidad * it.precio_unitario;
    return '<tr><td>' + it.sku + '</td><td>' + (it.descripcion||'—') + '</td>'
      + '<td style="text-align:center;">' + it.cantidad + '</td>'
      + '<td>' + (it.lote_pt||'—') + '</td>'
      + '<td style="text-align:right;">$' + Number(it.precio_unitario||0).toLocaleString() + '</td>'
      + '<td style="text-align:right;font-weight:600;">$' + Number(sub||0).toLocaleString() + '</td></tr>';
  }).join('');
  var previewBanner = preview
    ? '<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:10px;margin-bottom:16px;color:#92400e;font-size:12px;font-weight:600;">BORRADOR — Vista previa. El despacho aun no ha sido confirmado en el sistema.</div>'
    : '';
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Acta de Entrega</title>'
    + '<style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#1C1917;}'
    + 'h2{color:#1C1917;margin-bottom:4px;}h3{color:#57534e;margin:20px 0 10px;}'
    + '.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}'
    + 'table{width:100%;border-collapse:collapse;margin-bottom:16px;}'
    + 'th{background:#f5f5f4;padding:8px 10px;text-align:left;font-size:11px;color:#57534e;border:1px solid #e7e5e4;}'
    + 'td{padding:7px 10px;border:1px solid #e7e5e4;}'
    + '.meta{background:#fafaf9;border-radius:6px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '.meta .lbl{font-size:10px;color:#78716c;text-transform:uppercase;} .meta .val{font-size:13px;font-weight:600;}'
    + '.total-row td{background:#f5f5f4;font-weight:700;}'
    + '.firma{display:grid;grid-template-columns:1fr 1fr 1fr;gap:30px;margin-top:40px;}'
    + '.firma-box{border-top:1px solid #292524;padding-top:8px;font-size:11px;color:#78716c;text-align:center;}'
    + '.noPrint{text-align:center;margin-bottom:20px;} @media print{.noPrint{display:none!important;}}'
    + '</style></head><body>'
    + '<div class="noPrint"><button onclick="window.print()" style="padding:9px 24px;background:#1C1917;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">Imprimir</button></div>'
    + previewBanner
    + '<div class="header">'
    + '<div><h2>ACTA DE ENTREGA / REMISION</h2><p style="color:#78716c;font-size:12px;">ANIMUS Lab — HHA Group</p></div>'
    + '<div style="text-align:right;font-size:11px;color:#78716c;">'
    + '<div>No. Despacho: <strong>' + (numDespacho||'BORRADOR') + '</strong></div>'
    + '<div>Fecha: ' + hoy + '</div></div></div>'
    + '<div class="meta">'
    + '<div><div class="lbl">No. Pedido</div><div class="val">' + (ped ? ped.numero : '—') + '</div></div>'
    + '<div><div class="lbl">Cliente</div><div class="val">' + (ped ? (ped.cliente||'—') : '—') + '</div></div>'
    + '<div><div class="lbl">Total Unidades</div><div class="val">' + totalUds + ' uds</div></div>'
    + '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(totalVal).toLocaleString() + '</div></div>'
    + '</div>'
    + '<h3>Detalle del despacho</h3>'
    + '<table><thead><tr><th>SKU</th><th>Descripcion</th><th style="text-align:center;">Cant.</th><th>Lote PT</th><th style="text-align:right;">P. Unit.</th><th style="text-align:right;">Subtotal</th></tr></thead>'
    + '<tbody>' + itemsHtml + '</tbody>'
    + '<tfoot><tr class="total-row"><td colspan="5" style="text-align:right;">TOTAL</td><td style="text-align:right;">$' + Number(totalVal).toLocaleString() + '</td></tr></tfoot>'
    + '</table>'
    + '<div class="firma">'
    + '<div class="firma-box">Despachado por<br><br>&nbsp;</div>'
    + '<div class="firma-box">Recibido por / Transportista<br><br>&nbsp;</div>'
    + '<div class="firma-box">Control de Calidad<br><br>&nbsp;</div>'
    + '</div>'
    + '</body></html>');
  w.document.close();
}

function cancelarDespacho() {
  currentPed = null;
  document.getElementById('despacho-form-card').style.display = 'none';
  document.querySelectorAll('.ped-card').forEach(function(c) { c.classList.remove('selected'); });
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  ['recientes','pendientes'].forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-' + t).classList.toggle('active', t === name);
  });
}

async function loadHistorial() {
  try {
    var r = await fetch('/api/despachos');
    var d = await r.json();
    var desps = (d.despachos || []).slice(0, 20);
    var el = document.getElementById('tab-recientes');
    document.getElementById('cnt-recientes').textContent = desps.length;
    if (!desps.length) { el.innerHTML = '<div class="empty">Sin despachos registrados</div>'; return; }
    var h = '<div style="overflow-x:auto"><table><thead><tr><th>No. Despacho</th><th>Cliente</th><th>Pedido</th><th>Operador</th><th>Fecha</th><th>Estado</th></tr></thead><tbody>';
    desps.forEach(function(d) {
      h += '<tr><td><strong>' + d.numero + '</strong></td><td>' + (d.cliente||'—') + '</td><td>' + (d.numero_pedido||'—') + '</td><td>' + (d.operador||'—') + '</td><td>' + (d.fecha||'').slice(0,10) + '</td><td>' + (d.estado||'—') + '</td></tr>';
    });
    h += '</tbody></table></div>';
    el.innerHTML = h;

    var r2 = await fetch('/api/hub-salida/pedidos-pendientes');
    var d2 = await r2.json();
    var pend = d2.pedidos || [];
    document.getElementById('cnt-pendientes').textContent = pend.length;
    var el2 = document.getElementById('tab-pendientes');
    if (!pend.length) { el2.innerHTML = '<div class="empty">Sin pedidos pendientes</div>'; return; }
    var h2 = '<div style="overflow-x:auto"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Valor</th><th>Estado</th><th>Fecha</th><th>Accion</th></tr></thead><tbody>';
    pend.forEach(function(p) {
      h2 += '<tr><td><strong>' + p.numero + '</strong></td><td>' + (p.cliente||'—') + '</td><td>$' + Number(p.valor_total||0).toLocaleString() + '</td><td>' + p.estado + '</td><td>' + (p.fecha||'').slice(0,10) + '</td><td><button class="btn btn-primary btn-sm" onclick="cargarPedido(\''  + p.numero + '\')" >Despachar</button></td></tr>';
    });
    h2 += '</tbody></table></div>';
    el2.innerHTML = h2;
  } catch(e) { console.error(e); }
}

loadPedQueue();
loadHistorial();
</script>
</body>
</html>
"""

