# recepcion_html.py — extraído de index.py (Fase C prep)
RECEPCION_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Recepcion de Mercancia - Espagiria</title>
<link rel="stylesheet" href="/static/cortex.css?v=cortex4">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f8f7f5;color:#1C1917;font-size:14px;}
.topbar{background:#292524;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:18px;font-weight:600;}
.topbar a{color:#a8a29e;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.topbar .hub-link{background:#4A6741;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;}
.topbar .hub-link:hover{background:#3a5331;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px;margin-bottom:20px;}
.card h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#292524;display:flex;align-items:center;gap:8px;}
.oc-queue{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-bottom:16px;}
.oc-card{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;cursor:pointer;transition:all .15s;}
.oc-card:hover{border-color:#57534e;background:#f5f5f4;}
.oc-card .oc-num{font-weight:700;font-size:13px;color:#292524;}
.oc-card .oc-prov{font-size:12px;color:#78716c;margin-top:2px;}
.oc-card .oc-val{font-size:12px;color:#4A6741;font-weight:600;margin-top:4px;}
.oc-card .oc-dias{font-size:11px;color:#a8a29e;}
.search-row{display:flex;gap:10px;align-items:center;margin-bottom:16px;}
.search-row input{flex:1;max-width:320px;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:14px;}
.search-row input:focus{outline:none;border-color:#57534e;}
.btn{padding:9px 18px;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:500;}
.btn-primary{background:#292524;color:#fff;}
.btn-primary:hover{background:#1c1917;}
.btn-success{background:#16a34a;color:#fff;}
.btn-success:hover{background:#15803d;}
.btn-print{background:#1e40af;color:#fff;}
.btn-print:hover{background:#1d4ed8;}
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
td input[type=number]{width:100px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
td input[type=number]:focus{outline:none;border-color:#57534e;}
td select{padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;background:#fff;}
td input[type=text]{width:100%;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
.row-ok td{background:#f0fdf4;}
.row-disc td{background:#fff7ed;}
.row-falta td{background:#fef2f2;}
.obs-row{margin-top:12px;}
.obs-row label{font-size:13px;font-weight:600;display:block;margin-bottom:6px;color:#292524;}
.obs-row textarea{width:100%;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;min-height:72px;}
.receptor-row{display:flex;gap:12px;align-items:center;margin-top:12px;}
.receptor-row label{font-size:13px;font-weight:600;white-space:nowrap;color:#292524;}
.receptor-row input{flex:1;max-width:260px;padding:8px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.submit-row{margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.msg{font-size:13px;padding:8px 14px;border-radius:6px;}
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
.progress-bar{background:#e7e5e4;border-radius:4px;height:6px;margin-top:4px;}
.progress-fill{background:#16a34a;height:6px;border-radius:4px;transition:width .3s;}
.item-pct{font-size:11px;color:#78716c;margin-top:2px;}
.icon-ok{color:#16a34a;font-size:16px;}
.icon-disc{color:#d97706;font-size:16px;}
.icon-falta{color:#dc2626;font-size:16px;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <img src="/static/icons/icon-192.png?v=cortex4" alt="Cortex Labs" class="cx-mod-header__logo">
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/><path d="M15 18h-3M22 18h-2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M14 9h3l3 4v5h-2"/></svg>
      Recepción de Mercancía
    </div>
    <div class="cx-mod-header__sub"><strong>Cortex Labs</strong> &middot; ingreso de MP &amp; MEE desde OCs</div>
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
    <h2>&#9203; OCs Pendientes de Recepcion</h2>
    <div id="queue-list"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card">
    <h2>&#128269; Registrar Recepcion</h2>
    <div class="search-row">
      <input type="text" id="oc-input" placeholder="Numero de OC (ej: OC-2026-001)" onkeydown="if(event.key==='Enter')buscarOC()">
      <button class="btn btn-primary" onclick="buscarOC()">Buscar OC</button>
    </div>
    <div id="oc-msg"></div>

    <div id="oc-section" style="display:none">
      <div class="oc-info" id="oc-header"></div>
      <div id="oc-estado-warn" style="display:none;margin:10px 0;padding:12px 16px;border-radius:6px;font-weight:600;"></div>
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th style="width:36px;"></th>
              <th>Material</th>
              <th>Solicitado</th>
              <th>Cantidad Recibida</th>
              <th>Diferencia</th>
              <th>% Cumpl.</th>
              <th>Estado</th>
              <th>Lote</th>
              <th>Vence</th>
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
        <label>Observaciones generales:</label>
        <textarea id="obs-input" placeholder="Ej: Caja exterior golpeada pero producto en buen estado. Falto 1 item."></textarea>
      </div>

      <div class="submit-row">
        <button class="btn btn-success" onclick="registrarRecepcion()">&#10003; Registrar Recepcion</button>
        <div id="submit-msg"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>&#128202; Monitoreo: Pagado - Llego?</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-transito" onclick="showTab('transito')">
        En Transito <span class="cnt-badge" id="cnt-transito">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-parcial" onclick="showTab('parcial')">
        Parciales <span class="cnt-badge" id="cnt-parcial">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-recibidas" onclick="showTab('recibidas')">
        Recibidas <span class="cnt-badge" id="cnt-recibidas">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-disc" onclick="showTab('disc')">
        Con Discrepancias <span class="cnt-badge" id="cnt-disc">0</span>
      </button>
    </div>
    <div id="tab-transito" class="tab-content active"></div>
    <div id="tab-parcial" class="tab-content"></div>
    <div id="tab-recibidas" class="tab-content"></div>
    <div id="tab-disc" class="tab-content"></div>
  </div>

  <div class="card">
    <h2>&#9203; Lotes en Cuarentena</h2>
    <p style="font-size:12px;color:#78716c;margin-bottom:12px;">Lotes recibidos pendientes de aprobacion de Control de Calidad.</p>
    <div id="cuarentena-list"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card">
    <h2>&#128269; Trazabilidad de Lote</h2>
    <div class="search-row">
      <input type="text" id="lote-input" placeholder="Numero de lote (ej: L-2026-001)" onkeydown="if(event.key==='Enter')buscarLote()">
      <button class="btn btn-primary" onclick="buscarLote()">Buscar</button>
    </div>
    <div id="lote-result" style="margin-top:12px;"></div>
  </div>

</div>
<script>
var currentOC = null;

async function loadQueue() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (!Array.isArray(all)) all = [];
    var pendientes = all.filter(function(x) {
      return (x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3)) || x.estado === 'Parcial';
    });
    var el = document.getElementById('queue-list');
    if (pendientes.length === 0) {
      el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Sin OCs pendientes de recepcion.</p>';
      return;
    }
    var today = new Date();
    var html = '<div class="oc-queue">';
    pendientes.forEach(function(oc) {
      var dt = oc.fecha ? new Date(oc.fecha) : null;
      var dias = dt ? Math.floor((today - dt) / 86400000) : 0;
      html += '<div class="oc-card" data-oc="' + oc.numero_oc + '" onclick="cargarOC(this.dataset.oc)">'
        + '<div class="oc-num">' + oc.numero_oc + '</div>'
        + '<div class="oc-prov">' + (oc.proveedor || '') + '</div>'
        + '<div class="oc-val">$' + Number(oc.valor_total||0).toLocaleString() + '</div>'
        + '<div class="oc-dias">' + (dias > 0 ? dias + 'd en transito' : 'Reciente') + '</div>'
        + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  } catch(e) { console.error(e); }
}

function cargarOC(num) {
  document.getElementById('oc-input').value = num;
  buscarOC();
  document.getElementById('oc-section').scrollIntoView({behavior:'smooth'});
}

async function buscarOC() {
  var num = document.getElementById('oc-input').value.trim().toUpperCase();
  if (!num) return;
  showMsg('oc-msg', '', '');
  try {
    var r = await fetch('/api/recepcion/detalle/' + encodeURIComponent(num));
    var d = await r.json();
    if (!r.ok || d.error) {
      var msg = d.error || 'OC no encontrada';
      if (r.status === 422) msg = '⛔ ' + msg;
      showMsg('oc-msg', msg, 'err');
      document.getElementById('oc-section').style.display = 'none';
      return;
    }
    currentOC = d;
    renderOC(d);
    document.getElementById('oc-section').style.display = 'block';
  } catch(e) { showMsg('oc-msg', 'Error de red: ' + e.message, 'err'); }
}

function getItemIcon(est, pct) {
  if (est === 'OK' && pct >= 100) return '<span class="icon-ok">&#10003;</span>';
  if (est === 'Danado' || est === 'NoLlego') return '<span class="icon-falta">&#10007;</span>';
  if (pct < 100 || est !== 'OK') return '<span class="icon-disc">&#9888;</span>';
  return '';
}

function renderOC(d) {
  var badgeCls = 'badge-' + (d.estado||'').toLowerCase();
  document.getElementById('oc-header').innerHTML =
    '<div><div class="lbl">OC</div><div class="val">' + d.numero_oc + '</div></div>' +
    '<div><div class="lbl">Proveedor</div><div class="val">' + d.proveedor + '</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">' + (d.fecha||'').slice(0,10) + '</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val"><span class="badge ' + badgeCls + '">' + d.estado + '</span></div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(d.valor_total||0).toLocaleString() + '</div></div>' +
    '<div><div class="lbl">Categoria</div><div class="val">' + (d.categoria||'MP') + '</div></div>';

  // Advertencia si OC ya fue procesada (static div in HTML, no DOM insertion needed)
  var warnEl = document.getElementById('oc-estado-warn');
  if (d.estado === 'Recibida' || d.estado === 'Pagada') {
    warnEl.style.background = '#fef9c3'; warnEl.style.color = '#854d0e'; warnEl.style.border = '1px solid #fde047'; warnEl.style.display = 'block';
    warnEl.textContent = '\u26a0 Esta OC ya fue recibida (' + d.estado + '). Puedes consultar pero el registro de recepcion esta completo.';
  } else if (d.estado === 'Rechazada') {
    warnEl.style.background = '#fee2e2'; warnEl.style.color = '#991b1b'; warnEl.style.border = '1px solid #fca5a5'; warnEl.style.display = 'block';
    warnEl.textContent = '\u274c Esta OC fue rechazada y no puede recibirse.';
  } else {
    warnEl.style.display = 'none'; warnEl.textContent = '';
  }
  var tbody = document.getElementById('items-body');
  tbody.innerHTML = '';
  var items = d.items || [];
  for (var idx = 0; idx < items.length; idx++) {
    (function(i, it) {
      var unidad = it.unidad || ((d.categoria === 'MEE') ? 'uds' : 'g');
      var prevRec = (it.cantidad_recibida_g > 0) ? it.cantidad_recibida_g : it.cantidad_g;
      var pct = it.cantidad_g > 0 ? Math.round(prevRec / it.cantidad_g * 100) : 100;
      var tr = document.createElement('tr');
      tr.id = 'item-row-' + i;
      tr.innerHTML =
        '<td style="text-align:center;">' + getItemIcon('OK', pct) + '</td>' +
        '<td><strong>' + it.nombre_mp + '</strong><br><small style="color:#78716c">' + it.codigo_mp + '</small></td>' +
        '<td class="valor">' + Number(it.cantidad_g||0).toLocaleString() + ' ' + unidad + '</td>' +
        '<td><input type="number" id="cant-' + i + '" data-codigo="' + it.codigo_mp + '" data-sol="' + it.cantidad_g + '" value="' + prevRec + '" min="0" step="0.01" oninput="updateRow(' + i + ')"></td>' +
        '<td id="dif-' + i + '" class="valor" style="font-weight:600;"></td>' +
        '<td><div class="progress-bar"><div class="progress-fill" id="prog-' + i + '" style="width:' + Math.min(pct,100) + '%"></div></div><div class="item-pct" id="pct-' + i + '">' + pct + '%</div></td>' +
        '<td><select id="est-' + i + '" onchange="updateRow(' + i + ')">' +
          '<option value="OK">OK - Conforme</option>' +
          '<option value="Incompleto">Incompleto</option>' +
          '<option value="Danado">Danado</option>' +
          '<option value="NoLlego">No llego</option>' +
        '</select></td>' +
        '<td><input type="text" id="lote-' + i + '" placeholder="Ej: L-2026-001" style="width:110px;"></td>' +
        '<td><input type="date" id="fv-' + i + '" style="width:130px;"></td>' +
        '<td><input type="text" id="nota-' + i + '" placeholder="Observacion opcional"></td>';
      tbody.appendChild(tr);
      updateRow(i);
    })(idx, items[idx]);
  }
}

function updateRow(i) {
  var cantEl = document.getElementById('cant-' + i);
  var estEl = document.getElementById('est-' + i);
  var progEl = document.getElementById('prog-' + i);
  var pctEl = document.getElementById('pct-' + i);
  var difEl = document.getElementById('dif-' + i);
  var row = document.getElementById('item-row-' + i);
  if (!cantEl) return;
  var sol = parseFloat(cantEl.dataset.sol) || 0;
  var rec = parseFloat(cantEl.value) || 0;
  var est = estEl ? estEl.value : 'OK';
  var pct = sol > 0 ? Math.round(rec / sol * 100) : 100;
  var dif = rec - sol;
  if (difEl) {
    if (Math.abs(dif) < 0.001) { difEl.textContent = '\u2713'; difEl.style.color = '#16a34a'; }
    else if (dif < 0) { difEl.textContent = dif.toLocaleString(); difEl.style.color = '#dc2626'; }
    else { difEl.textContent = '+' + dif.toLocaleString(); difEl.style.color = '#d97706'; }
  }
  if (progEl) { progEl.style.width = Math.min(pct,100) + '%'; progEl.style.background = pct >= 100 ? '#16a34a' : pct > 50 ? '#d97706' : '#dc2626'; }
  if (pctEl) pctEl.textContent = pct + '%';
  if (row) { row.className = (est === 'OK' && pct >= 100) ? 'row-ok' : (est === 'Danado' || est === 'NoLlego' || pct === 0) ? 'row-falta' : 'row-disc'; }
}

async function registrarRecepcion() {
  if (!currentOC) return;
  var obs = document.getElementById('obs-input').value.trim();
  var receptor = document.getElementById('receptor-input').value.trim();
  if (!receptor) { showMsg('submit-msg', 'Ingresa quien recibe la mercancia', 'err'); return; }
  var items = [];
  var discrepancias = false;
  var ocItems = currentOC.items || [];
  for (var idx = 0; idx < ocItems.length; idx++) {
    var it = ocItems[idx];
    var cantEl = document.getElementById('cant-' + idx);
    var estEl = document.getElementById('est-' + idx);
    var notaEl = document.getElementById('nota-' + idx);
    var cant = cantEl ? (parseFloat(cantEl.value) || 0) : 0;
    var est = estEl ? estEl.value : 'OK';
    var nota = notaEl ? notaEl.value.trim() : '';
    var loteEl = document.getElementById('lote-' + idx);
    var fvEl = document.getElementById('fv-' + idx);
    var lote = loteEl ? loteEl.value.trim() : '';
    var fv = fvEl ? fvEl.value.trim() : '';
    if (est !== 'OK' || cant < it.cantidad_g) discrepancias = true;
    items.push({codigo_mp: it.codigo_mp, cantidad_recibida: cant, estado: est, notas: nota, lote: lote, fecha_vencimiento: fv});
  }
  var payload = {
    observaciones_recepcion: obs,
    tiene_discrepancias: discrepancias ? 1 : 0,
    items_recepcion: items,
    receptor_nombre: receptor
  };
  showMsg('submit-msg', 'Registrando...', '');
  var _submitBtn = document.querySelector('.btn-success');
  if (_submitBtn) { _submitBtn.disabled = true; _submitBtn.textContent = 'Registrando...'; }
  try {
    var r = await fetch('/api/ordenes-compra/' + encodeURIComponent(currentOC.numero_oc) + '/recibir', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    var d = await r.json();
    if (d.ok) {
      var discMsg = discrepancias ? ' \u26a0 Con discrepancias.' : '';
      var parcialMsg = d.parcial ? ' \u26a1 Recepcion PARCIAL — OC sigue abierta para completar.' : '';
      showMsg('submit-msg', 'Recepcion registrada. ' + (d.ingresos||0) + ' item(s) ingresado(s).' + discMsg + parcialMsg, 'ok');
      var submitRow = document.querySelector('.submit-row');
      if (submitRow) {
        var printBtn = document.createElement('button');
        printBtn.className = 'btn btn-print';
        printBtn.textContent = '🖨 Imprimir Acta de Recepcion';
        printBtn.onclick = function() { imprimirActaRecepcion(currentOC, payload, d); };
        submitRow.appendChild(printBtn);
      }
      document.getElementById('oc-section').style.display = 'none';
      currentOC = null;
      document.getElementById('oc-input').value = '';
      document.getElementById('receptor-input').value = '';
      document.getElementById('obs-input').value = '';
      if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; }
      loadMonitoreo();
      loadQueue();
      loadCuarentena();
    } else {
      showMsg('submit-msg', d.error || 'Error al registrar', 'err');
      if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; }
    }
  } catch(e) { showMsg('submit-msg', 'Error de red: ' + e.message, 'err'); if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; } }
}

function imprimirActaRecepcion(oc, payload, result) {
  var w = window.open('', '_blank', 'width=760,height=900,toolbar=0,scrollbars=1,resizable=1');
  var hoy = new Date().toLocaleString('es-CO');
  var itemsHtml = (payload.items_recepcion || []).map(function(it) {
    var cls = it.estado === 'OK' ? 'color:#16a34a' : 'color:#dc2626';
    return '<tr><td>' + it.codigo_mp + '</td><td>' + it.cantidad_recibida.toLocaleString() + '</td><td style="' + cls + ';font-weight:600;">' + it.estado + '</td><td>' + (it.notas||'—') + '</td></tr>';
  }).join('');
  var discBanner = payload.tiene_discrepancias
    ? '<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:12px;margin-bottom:16px;color:#92400e;font-weight:600;">⚠ Esta recepcion contiene discrepancias. Requiere revision.</div>'
    : '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:12px;margin-bottom:16px;color:#166534;font-weight:600;">✓ Recepcion conforme sin discrepancias.</div>';
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Acta Recepcion</title>'
    + '<style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#1C1917;}'
    + 'h2{color:#292524;margin-bottom:4px;}h3{color:#57534e;margin:20px 0 10px;}'
    + '.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}'
    + 'table{width:100%;border-collapse:collapse;margin-bottom:16px;}'
    + 'th{background:#f5f5f4;padding:8px 10px;text-align:left;font-size:11px;color:#57534e;border:1px solid #e7e5e4;}'
    + 'td{padding:7px 10px;border:1px solid #e7e5e4;}'
    + '.meta{background:#fafaf9;border-radius:6px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '.meta .lbl{font-size:10px;color:#78716c;text-transform:uppercase;} .meta .val{font-size:13px;font-weight:600;}'
    + '.firma{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:40px;}'
    + '.firma-box{border-top:1px solid #292524;padding-top:8px;font-size:11px;color:#78716c;text-align:center;}'
    + '.noPrint{text-align:center;margin-bottom:20px;} @media print{.noPrint{display:none!important;}}'
    + '</style></head><body>'
    + '<div class="noPrint"><button onclick="window.print()" style="padding:9px 24px;background:#292524;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">Imprimir</button></div>'
    + '<div class="header"><div><h2>ACTA DE RECEPCION DE MERCANCIA</h2><p style="color:#78716c;font-size:12px;">Espagiria Laboratorio — COC-PRO-002-F07</p></div>'
    + '<div style="text-align:right;font-size:11px;color:#78716c;"><div>Fecha: ' + hoy + '</div></div></div>'
    + discBanner
    + '<div class="meta">'
    + '<div><div class="lbl">No. OC</div><div class="val">' + (oc ? oc.numero_oc : '—') + '</div></div>'
    + '<div><div class="lbl">Proveedor</div><div class="val">' + (oc ? oc.proveedor : '—') + '</div></div>'
    + '<div><div class="lbl">Categoria</div><div class="val">' + (oc ? (oc.categoria||'MP') : '—') + '</div></div>'
    + '<div><div class="lbl">Valor Total OC</div><div class="val">$' + Number((oc ? oc.valor_total : 0)||0).toLocaleString() + '</div></div>'
    + '</div>'
    + '<h3>Detalle de items recibidos</h3>'
    + '<table><thead><tr><th>Codigo MP</th><th>Cant. Recibida</th><th>Estado</th><th>Notas</th></tr></thead><tbody>' + itemsHtml + '</tbody></table>'
    + '<h3>Observaciones</h3>'
    + '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:6px;padding:12px;min-height:60px;">' + (payload.observaciones_recepcion||'Sin observaciones adicionales.') + '</div>'
    + '<div class="firma">'
    + '<div class="firma-box">Recibido por<br><br><strong>' + payload.receptor_nombre + '</strong></div>'
    + '<div class="firma-box">Control de Calidad<br><br>&nbsp;</div>'
    + '</div>'
    + '</body></html>');
  w.document.close();
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  ['transito','parcial','recibidas','disc'].forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-' + t).classList.toggle('active', t === name);
  });
}

function fmtDate(s) { return s ? String(s).slice(0,10) : '—'; }
function fmtVal(v) { return '$' + Number(v||0).toLocaleString(); }

function buildTable(rows) {
  if (!rows.length) return '<div class="empty">Sin registros</div>';
  var h = '<div style="overflow-x:auto"><table><thead><tr>'
    + '<th>OC</th><th>Proveedor</th><th>Cat.</th><th>Valor</th>'
    + '<th>Fecha OC</th><th>F. Aut.</th><th>F. Pago</th><th>F. Recepcion</th><th>Recibido Por</th><th>Observaciones</th>'
    + '</tr></thead><tbody>';
  rows.forEach(function(row) {
    var disc = row.tiene_discrepancias ? '<span class="disc"> &#9888; DISC</span>' : '';
    h += '<tr><td><strong>' + row.numero_oc + '</strong>' + disc + '</td>'
      + '<td>' + row.proveedor + '</td><td>' + row.categoria + '</td>'
      + '<td class="valor">' + fmtVal(row.valor_total) + '</td>'
      + '<td>' + fmtDate(row.fecha) + '</td>'
      + '<td>' + fmtDate(row.fecha_autorizacion) + '</td>'
      + '<td>' + fmtDate(row.fecha_pago) + '</td>'
      + '<td>' + (row.fecha_recepcion ? fmtDate(row.fecha_recepcion) : '<span style="color:#d97706">Pendiente</span>') + '</td>'
      + '<td style="color:#57534e">' + (row.recibido_por||'—') + '</td>'
      + '<td style="max-width:200px;color:#57534e">' + (row.observaciones||'—') + '</td>'
      + '</tr>';
  });
  h += '</tbody></table></div>';
  return h;
}

async function loadMonitoreo() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (!Array.isArray(all)) all = [];
    var transito = all.filter(function(x) { return x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3); });
    var parcial = all.filter(function(x) { return x.estado === 'Parcial'; });
    var recibidas = all.filter(function(x) { return (x.estado === 'Recibida' || x.estado === 'Pagada') && x.fecha_recepcion && x.fecha_recepcion.length > 2; });
    var disc = all.filter(function(x) { return x.tiene_discrepancias; });
    document.getElementById('cnt-transito').textContent = transito.length;
    document.getElementById('cnt-parcial').textContent = parcial.length;
    document.getElementById('cnt-recibidas').textContent = recibidas.length;
    document.getElementById('cnt-disc').textContent = disc.length;
    document.getElementById('tab-transito').innerHTML = buildTable(transito);
    document.getElementById('tab-parcial').innerHTML = buildTable(parcial);
    document.getElementById('tab-recibidas').innerHTML = buildTable(recibidas);
    document.getElementById('tab-disc').innerHTML = buildTable(disc);
  } catch(e) { console.error(e); }
}

async function loadCuarentena() {
  try {
    var r = await fetch('/api/recepcion/lotes-cuarentena');
    var lotes = await r.json();
    var el = document.getElementById('cuarentena-list');
    if (!lotes.length) { el.innerHTML = '<p style="color:#16a34a;font-size:13px;">\u2713 Sin lotes en cuarentena.</p>'; return; }
    var h = '<div style="overflow-x:auto"><table><thead><tr><th>Material</th><th>Lote</th><th>Cantidad</th><th>Proveedor</th><th>F. Recepcion</th><th>Vence</th><th>OC</th><th>Accion</th></tr></thead><tbody>';
    lotes.forEach(function(l) {
      var fv = l.fecha_vencimiento ? l.fecha_vencimiento.slice(0,10) : '—';
      h += '<tr><td><strong>' + (l.material_nombre||'') + '</strong></td>'
        + '<td style="font-family:monospace;">' + (l.lote||'—') + '</td>'
        + '<td>' + Number(l.cantidad||0).toLocaleString() + '</td>'
        + '<td>' + (l.proveedor||'—') + '</td>'
        + '<td>' + (l.fecha||'—').slice(0,10) + '</td>'
        + '<td>' + fv + '</td>'
        + '<td>' + (l.numero_oc||'—') + '</td>'
        + '<td style="white-space:nowrap;">'
        + '<button class="btn" style="background:#16a34a;color:#fff;padding:4px 10px;font-size:11px;margin-right:4px;" data-aprobarlote="' + l.id + '" data-est="Aprobado">Aprobar</button>'
        + '<button class="btn" style="background:#dc2626;color:#fff;padding:4px 10px;font-size:11px;" data-aprobarlote="' + l.id + '" data-est="Rechazado">Rechazar</button>'
        + '</td></tr>';
    });
    h += '</tbody></table></div>';
    el.innerHTML = h;
  } catch(e) { document.getElementById('cuarentena-list').innerHTML = '<p style="color:#a8a29e;">Error al cargar.</p>'; }
}

document.addEventListener('click', function(e) {
  var btn = e.target.closest('[data-aprobarlote]');
  if (!btn) return;
  var movId = btn.getAttribute('data-aprobarlote');
  var est = btn.getAttribute('data-est');
  if (!confirm('Marcar lote como ' + est + '?')) return;
  fetch('/api/recepcion/aprobar-lote', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mov_id: movId, estado: est})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.ok) loadCuarentena();
    else alert('Error: ' + (d.error||'desconocido'));
  });
});

async function buscarLote() {
  var lote = document.getElementById('lote-input').value.trim();
  if (!lote) return;
  var el = document.getElementById('lote-result');
  el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Buscando...</p>';
  try {
    var r = await fetch('/api/recepcion/trazabilidad/' + encodeURIComponent(lote));
    var d = await r.json();
    var movs = d.movimientos || [];
    if (!movs.length) { el.innerHTML = '<p style="color:#dc2626;font-size:13px;">Lote no encontrado.</p>'; return; }
    var oc = d.oc;
    var h = '';
    if (oc) {
      h += '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;margin-bottom:12px;">'
        + '<div style="font-weight:700;margin-bottom:6px;">OC de Origen: ' + oc.numero_oc + '</div>'
        + '<div style="font-size:12px;color:#57534e;">Proveedor: ' + (oc.proveedor||'—') + ' | Fecha: ' + (oc.fecha||'—').slice(0,10) + ' | Estado OC: ' + (oc.estado||'—') + ' | Recibido por: ' + (oc.recibido_por||'—') + '</div>'
        + '</div>';
    }
    h += '<table><thead><tr><th>Material</th><th>Cant.</th><th>Tipo</th><th>Fecha</th><th>Estado Lote</th><th>Proveedor</th><th>Vence</th></tr></thead><tbody>';
    movs.forEach(function(m) {
      var estadoColor = m.estado_lote === 'Aprobado' ? '#16a34a' : m.estado_lote === 'Rechazado' ? '#dc2626' : '#d97706';
      h += '<tr><td><strong>' + (m.material_nombre||m.material_id||'') + '</strong></td>'
        + '<td>' + Number(m.cantidad||0).toLocaleString() + '</td>'
        + '<td>' + (m.cantidad > 0 ? 'Entrada' : 'Salida') + '</td>'
        + '<td>' + (m.fecha||'—').slice(0,10) + '</td>'
        + '<td style="color:' + estadoColor + ';font-weight:600;">' + (m.estado_lote||'Sin estado') + '</td>'
        + '<td>' + (m.proveedor||'—') + '</td>'
        + '<td>' + (m.fecha_vencimiento||'—').slice(0,10) + '</td>'
        + '</tr>';
    });
    h += '</tbody></table>';
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: ' + e.message + '</p>'; }
}

loadQueue();
loadMonitoreo();
loadCuarentena();
</script>
</body>
</html>
"""

