"""Tesoreria — fusion UI de Finanzas + Contabilidad.

Una sola URL /tesoreria con tabs que consumen los endpoints existentes
de /api/financiero/* y /api/contabilidad/*. Los blueprints viejos siguen
funcionando (no se elimina codigo). Esta es solo capa UI unificada.
"""

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tesorería — HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos6">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f5f4f0; color:#1c1917; }
  .header { background:linear-gradient(135deg,#0f3a1f 0%,#15803d 100%); color:#fff; padding:18px 28px; display:flex; align-items:center; justify-content:space-between; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; }
  .header a { color:#bbf7d0; font-size:0.85em; text-decoration:none; }
  .container { max-width:1500px; margin:0 auto; padding:18px; }
  .tabs { display:flex; gap:4px; margin-bottom:18px; border-bottom:2px solid #e5e7eb; padding-bottom:0; flex-wrap:wrap; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .tab { padding:10px 16px; background:transparent; border:none; cursor:pointer; font-size:13px; color:#57534e; font-weight:600; white-space:nowrap; border-bottom:3px solid transparent; }
  .tab:hover { color:#15803d; }
  .tab.active { color:#15803d; border-bottom-color:#15803d; }
  .grid { display:grid; gap:14px; }
  .grid-4 { grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
  .grid-2 { grid-template-columns:1fr 1fr; }
  .card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; }
  .card h3 { margin:0 0 8px; font-size:0.78em; color:#78716c; text-transform:uppercase; letter-spacing:0.06em; }
  .card .val { font-size:1.6em; font-weight:800; color:#1c1917; line-height:1; }
  .card .sub { font-size:0.78em; color:#a8a29e; margin-top:4px; }
  .panel { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:18px; margin-bottom:14px; }
  .panel h3 { margin:0 0 12px; font-size:0.95em; color:#1c1917; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:#fafaf9; color:#78716c; font-weight:600; text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.04em; }
  td { padding:8px 12px; border-bottom:1px solid #f5f5f4; }
  tr:hover td { background:#fafaf9; }
  .badge { padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700; display:inline-block; }
  .b-ok { background:#dcfce7; color:#15803d; }
  .b-warn { background:#fef3c7; color:#92400e; }
  .b-err { background:#fee2e2; color:#991b1b; }
  .empty { color:#a8a29e; font-style:italic; padding:32px; text-align:center; }
  .btn { padding:8px 14px; border:none; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; }
  .btn-primary { background:#15803d; color:#fff; }
  .btn-secondary { background:#f5f5f4; color:#44403c; border:1px solid #e7e5e4; }
  .hidden { display:none; }
  .pos { color:#15803d; font-weight:700; }
  .neg { color:#dc2626; font-weight:700; }
  @media (max-width:768px) {
    .header { padding:14px 16px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.1em; }
    .container { padding:10px; }
    .grid-4 { grid-template-columns:1fr 1fr; }
    .grid-2 { grid-template-columns:1fr; }
    .tab { padding:8px 12px; font-size:12px; }
    table thead { display:none; }
    table, table tbody, table tr, table td { display:block; width:100%; }
    table tr { background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:10px; margin-bottom:8px; }
    table td { padding:4px 0; border-bottom:none; font-size:12px; }
    table td:first-child { font-weight:700; padding-bottom:6px; }
  }
</style>
</head>
<body>
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#15803d" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/></svg>
        Tesorería
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Caja · P&amp;L · Cartera · Pagos · Facturación · Nómina · SIIGO</div>
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
    <div class="tabs" id="tabs">
      <button class="tab active" data-tab="caja" onclick="switchTab('caja')">📊 Caja & KPIs</button>
      <button class="tab" data-tab="pnl" onclick="switchTab('pnl')">📈 P&L · Margen</button>
      <button class="tab" data-tab="cartera" onclick="switchTab('cartera')">📥 Cartera (AR)</button>
      <button class="tab" data-tab="pagar" onclick="switchTab('pagar')">📤 Por Pagar (AP)</button>
      <button class="tab" data-tab="facturacion" onclick="switchTab('facturacion')">📄 Facturación</button>
      <button class="tab" data-tab="nomina" onclick="switchTab('nomina')">👥 Nómina</button>
      <button class="tab" data-tab="config" onclick="switchTab('config')">⚙️ Configuración</button>
    </div>

    <!-- TAB: CAJA & KPIs -->
    <div id="tab-caja" class="tabpanel">
      <div class="grid grid-4" style="margin-bottom:18px">
        <div class="card"><h3>Ingresos mes</h3><div class="val" id="kpi-ing-mes">—</div><div class="sub" id="kpi-ing-shopify"></div></div>
        <div class="card"><h3>Egresos mes</h3><div class="val" id="kpi-egr-mes" style="color:#dc2626">—</div><div class="sub">OCs+nómina+otros</div></div>
        <div class="card"><h3>Neto mes</h3><div class="val" id="kpi-neto"></div><div class="sub" id="kpi-neto-sub"></div></div>
        <div class="card"><h3>Saldo caja</h3><div class="val" id="kpi-saldo"></div><div class="sub">acumulado</div></div>
      </div>
      <div class="grid grid-2">
        <div class="panel">
          <h3>Sync Shopify → Ingresos</h3>
          <div id="shopify-status" style="font-size:13px;color:#57534e">Cargando...</div>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-secondary" onclick="syncDryRun()">👁️ Previsualizar</button>
            <button class="btn btn-primary" onclick="syncEjecutar()">✨ Sincronizar ahora</button>
          </div>
          <div id="shopify-msg" style="margin-top:10px;font-size:12px"></div>
        </div>
        <div class="panel">
          <h3>Importar OCs recibidas → egresos</h3>
          <p style="font-size:12px;color:#78716c;margin:0 0 10px">Trae a flujo_egresos las OCs marcadas Recibida que aún no se importaron.</p>
          <button class="btn btn-secondary" onclick="importarOCs()">📦 Importar OCs</button>
          <div id="import-msg" style="margin-top:10px;font-size:12px"></div>
        </div>
      </div>
    </div>

    <!-- TAB: P&L -->
    <div id="tab-pnl" class="tabpanel hidden">
      <div class="panel">
        <h3>P&amp;L mensual por empresa</h3>
        <div id="pnl-content" class="empty">Cargando P&amp;L...</div>
      </div>
      <div class="panel">
        <h3>Working Capital · DSO · DPO · Runway</h3>
        <div id="wc-content" class="empty">Cargando capital...</div>
      </div>
    </div>

    <!-- TAB: CARTERA -->
    <div id="tab-cartera" class="tabpanel hidden">
      <div class="panel">
        <h3>Aging de cartera (cuentas por cobrar)</h3>
        <div id="ar-content" class="empty">Cargando cartera...</div>
      </div>
      <div class="panel">
        <h3>Facturas con saldo pendiente</h3>
        <div id="facturas-pendientes" class="empty">Cargando facturas...</div>
      </div>
    </div>

    <!-- TAB: POR PAGAR -->
    <div id="tab-pagar" class="tabpanel hidden">
      <div class="panel">
        <h3>Aging de cuentas por pagar (proveedores)</h3>
        <div id="ap-content" class="empty">Cargando AP...</div>
      </div>
    </div>

    <!-- TAB: FACTURACIÓN -->
    <div id="tab-facturacion" class="tabpanel hidden">
      <div class="panel">
        <h3>Facturas emitidas</h3>
        <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="abrirEmitir()">+ Emitir factura</button>
          <button class="btn btn-secondary" onclick="exportarSiigo()">📥 Exportar SIIGO</button>
        </div>
        <div id="facturas-list" class="empty">Cargando facturas...</div>
      </div>
    </div>

    <!-- TAB: NÓMINA -->
    <div id="tab-nomina" class="tabpanel hidden">
      <div class="panel">
        <h3>Períodos de nómina</h3>
        <div id="nomina-list" class="empty">Cargando nómina...</div>
      </div>
    </div>

    <!-- TAB: CONFIG -->
    <div id="tab-config" class="tabpanel hidden">
      <div class="panel">
        <h3>Información</h3>
        <p style="font-size:13px;color:#57534e;line-height:1.6">
          Tesorería unifica los dashboards de <strong>Finanzas</strong> (caja, P&amp;L, cartera, pagos)
          y <strong>Contabilidad</strong> (facturas, SIIGO, nómina).
          Las URLs viejas <code>/financiero</code> y <code>/contabilidad</code> siguen funcionando
          como atajos directos.
        </p>
        <p style="font-size:12px;color:#78716c;margin-top:14px">
          <strong>Acceso rápido:</strong>
          <a href="/financiero" style="color:#15803d">Ir a Financiero (vista clásica)</a> ·
          <a href="/contabilidad" style="color:#15803d">Ir a Contabilidad (vista clásica)</a>
        </p>
      </div>
    </div>
  </div>

<script>
function fmtM(n){n=parseFloat(n||0); if(n>=1e6) return '$'+(n/1e6).toFixed(1)+'M'; if(n>=1e3) return '$'+(n/1e3).toFixed(0)+'K'; return '$'+Math.round(n).toLocaleString('es-CO');}
function fmtN(n){return (n||0).toLocaleString('es-CO');}
function _esc(s){return String(s||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));}

const TABS = ['caja','pnl','cartera','pagar','facturacion','nomina','config'];

function switchTab(t) {
  TABS.forEach(x => {
    document.getElementById('tab-'+x).classList.toggle('hidden', x !== t);
  });
  document.querySelectorAll('.tab').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === t);
  });
  cargarTab(t);
}

function cargarTab(t) {
  if (t === 'caja') cargarCaja();
  else if (t === 'pnl') cargarPnL();
  else if (t === 'cartera') cargarCartera();
  else if (t === 'pagar') cargarPagar();
  else if (t === 'facturacion') cargarFacturacion();
  else if (t === 'nomina') cargarNomina();
}

async function cargarCaja() {
  try {
    const k = await fetch('/api/financiero/kpis').then(r=>r.json());
    document.getElementById('kpi-ing-mes').textContent = fmtM(k.ingresos_mes);
    document.getElementById('kpi-egr-mes').textContent = fmtM(k.egresos_mes);
    const neto = (k.ingresos_mes||0) - (k.egresos_mes||0);
    const eN = document.getElementById('kpi-neto');
    eN.textContent = (neto>=0?'+':'')+fmtM(Math.abs(neto));
    eN.className = 'val ' + (neto>=0?'pos':'neg');
    document.getElementById('kpi-neto-sub').textContent = neto>=0?'superávit':'déficit';
    document.getElementById('kpi-saldo').textContent = fmtM(k.saldo_caja||0);
    document.getElementById('kpi-saldo').className = 'val ' + ((k.saldo_caja||0)>=0?'pos':'neg');
    if (k.shopify_mes) {
      document.getElementById('kpi-ing-shopify').textContent = 'Shopify mes: '+fmtM(k.shopify_mes);
    }
  } catch(e) { console.error(e); }

  try {
    const s = await fetch('/api/financiero/sync-shopify-status').then(r=>r.json());
    document.getElementById('shopify-status').innerHTML =
      '<strong>'+s.pendientes_count+'</strong> pedidos pendientes ('+fmtM(s.pendientes_total)+')<br>' +
      '<strong>'+s.sincronizados_count+'</strong> ya sincronizados ('+fmtM(s.sincronizados_total)+')<br>' +
      '<small>Último: '+(s.ultimo_sync_fecha||'nunca')+'</small>';
  } catch(e) { console.error(e); }
}

async function syncDryRun() {
  const msg = document.getElementById('shopify-msg');
  msg.textContent = 'Calculando...';
  const r = await fetch('/api/financiero/sync-shopify-ingresos',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({dry_run: true, solo_pagados: true})
  });
  const d = await r.json();
  if (!r.ok) { msg.style.color='#dc2626'; msg.textContent = d.error||'Error'; return; }
  msg.style.color='#15803d';
  msg.textContent = 'Importaría '+d.pendientes+' pedidos por '+fmtM(d.total_a_importar);
}

async function syncEjecutar() {
  if (!confirm('Sincronizar pedidos Shopify a flujo de ingresos?')) return;
  const msg = document.getElementById('shopify-msg');
  msg.textContent = 'Sincronizando...';
  const r = await fetch('/api/financiero/sync-shopify-ingresos',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({solo_pagados: true})
  });
  const d = await r.json();
  msg.style.color = r.ok ? '#15803d' : '#dc2626';
  msg.textContent = d.mensaje || d.error;
  if (r.ok) cargarCaja();
}

async function importarOCs() {
  const msg = document.getElementById('import-msg');
  msg.textContent = 'Importando...';
  const r = await fetch('/api/financiero/importar-ocs',{method:'POST'});
  const d = await r.json();
  msg.style.color = r.ok ? '#15803d' : '#dc2626';
  msg.textContent = d.message || d.error;
  if (r.ok) cargarCaja();
}

async function cargarPnL() {
  try {
    const p = await fetch('/api/financiero/pnl').then(r=>r.json());
    let html = '<table><thead><tr><th>Empresa</th><th>Ingresos</th><th>Egresos</th><th>EBITDA</th><th>Margen %</th></tr></thead><tbody>';
    (p.empresas||[]).forEach(e => {
      const margen = e.ingresos > 0 ? ((e.ebitda/e.ingresos)*100).toFixed(1)+'%' : '-';
      html += '<tr><td><strong>'+_esc(e.empresa)+'</strong></td>' +
              '<td>'+fmtM(e.ingresos)+'</td>' +
              '<td>'+fmtM(e.egresos)+'</td>' +
              '<td class="'+((e.ebitda||0)>=0?'pos':'neg')+'">'+fmtM(e.ebitda)+'</td>' +
              '<td>'+margen+'</td></tr>';
    });
    html += '</tbody></table>';
    document.getElementById('pnl-content').innerHTML = html;
  } catch(e) { document.getElementById('pnl-content').innerHTML = '<div class="empty">Error cargando P&L</div>'; }

  try {
    const w = await fetch('/api/financiero/working-capital').then(r=>r.json());
    document.getElementById('wc-content').innerHTML =
      '<div class="grid grid-4">' +
      '<div class="card"><h3>DSO (días cobranza)</h3><div class="val">'+fmtN(w.dso||0)+'</div></div>' +
      '<div class="card"><h3>DPO (días pago)</h3><div class="val">'+fmtN(w.dpo||0)+'</div></div>' +
      '<div class="card"><h3>Runway (meses)</h3><div class="val '+((w.runway_meses||0)>3?'pos':'neg')+'">'+(w.runway_meses||0).toFixed(1)+'</div></div>' +
      '<div class="card"><h3>Burn rate / mes</h3><div class="val">'+fmtM(w.burn_rate||0)+'</div></div>' +
      '</div>';
  } catch(e) { document.getElementById('wc-content').innerHTML = '<div class="empty">Error</div>'; }
}

async function cargarCartera() {
  try {
    const ar = await fetch('/api/financiero/ar-aging').then(r=>r.json());
    let html = '<div class="grid grid-4" style="margin-bottom:14px">' +
      '<div class="card"><h3>Total por cobrar</h3><div class="val">'+fmtM(ar.total||0)+'</div></div>' +
      '<div class="card"><h3>Corriente</h3><div class="val pos">'+fmtM(ar.corriente||0)+'</div></div>' +
      '<div class="card"><h3>Vencido 30d</h3><div class="val" style="color:#f59e0b">'+fmtM(ar.vencido_30||0)+'</div></div>' +
      '<div class="card"><h3>Vencido 60+d</h3><div class="val neg">'+fmtM((ar.vencido_60||0)+(ar.vencido_90||0))+'</div></div>' +
      '</div>';
    if (ar.detalle && ar.detalle.length) {
      html += '<table><thead><tr><th>Cliente</th><th>Pedido</th><th>Monto</th><th>Días</th></tr></thead><tbody>';
      ar.detalle.slice(0,20).forEach(p => {
        html += '<tr><td>'+_esc(p.cliente)+'</td><td>'+_esc(p.numero)+'</td><td>'+fmtM(p.valor)+'</td><td>'+(p.dias||0)+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    document.getElementById('ar-content').innerHTML = html;
  } catch(e) { document.getElementById('ar-content').innerHTML = '<div class="empty">Error</div>'; }

  try {
    const f = await fetch('/api/contabilidad/facturas').then(r=>r.json());
    const pend = (f.facturas||[]).filter(x => x.estado === 'Emitida' || x.estado === 'Parcial');
    if (!pend.length) { document.getElementById('facturas-pendientes').innerHTML = '<div class="empty">Sin facturas pendientes ✓</div>'; return; }
    let html = '<table><thead><tr><th>Factura</th><th>Cliente</th><th>Total</th><th>Saldo</th><th>Estado</th></tr></thead><tbody>';
    pend.slice(0,30).forEach(fa => {
      const saldo = (fa.total||0) - (fa.pagado||0);
      html += '<tr><td><strong>'+_esc(fa.numero)+'</strong></td>' +
              '<td>'+_esc(fa.cliente_nombre)+'</td>' +
              '<td>'+fmtM(fa.total)+'</td>' +
              '<td class="neg">'+fmtM(saldo)+'</td>' +
              '<td><span class="badge '+(fa.estado==='Parcial'?'b-warn':'b-err')+'">'+_esc(fa.estado)+'</span></td></tr>';
    });
    html += '</tbody></table>';
    document.getElementById('facturas-pendientes').innerHTML = html;
  } catch(e) { document.getElementById('facturas-pendientes').innerHTML = '<div class="empty">Error</div>'; }
}

async function cargarPagar() {
  try {
    const ap = await fetch('/api/financiero/ap-aging').then(r=>r.json());
    let html = '<div class="grid grid-4" style="margin-bottom:14px">' +
      '<div class="card"><h3>Total por pagar</h3><div class="val">'+fmtM(ap.total||0)+'</div></div>' +
      '<div class="card"><h3>Corriente</h3><div class="val">'+fmtM(ap.corriente||0)+'</div></div>' +
      '<div class="card"><h3>Vencido 30d</h3><div class="val" style="color:#f59e0b">'+fmtM(ap.vencido_30||0)+'</div></div>' +
      '<div class="card"><h3>Vencido 60+d</h3><div class="val neg">'+fmtM((ap.vencido_60||0)+(ap.vencido_90||0))+'</div></div>' +
      '</div>';
    if (ap.detalle && ap.detalle.length) {
      html += '<table><thead><tr><th>Proveedor</th><th>OC</th><th>Monto</th><th>Días</th></tr></thead><tbody>';
      ap.detalle.slice(0,20).forEach(p => {
        html += '<tr><td>'+_esc(p.proveedor)+'</td><td>'+_esc(p.numero_oc)+'</td><td>'+fmtM(p.valor)+'</td><td>'+(p.dias||0)+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    document.getElementById('ap-content').innerHTML = html;
  } catch(e) { document.getElementById('ap-content').innerHTML = '<div class="empty">Error</div>'; }
}

async function cargarFacturacion() {
  try {
    const f = await fetch('/api/contabilidad/facturas').then(r=>r.json());
    if (!(f.facturas||[]).length) { document.getElementById('facturas-list').innerHTML = '<div class="empty">Sin facturas emitidas. Click "+ Emitir factura"</div>'; return; }
    let html = '<table><thead><tr><th>Número</th><th>Cliente</th><th>Fecha</th><th>Total</th><th>Estado</th><th></th></tr></thead><tbody>';
    f.facturas.slice(0,50).forEach(fa => {
      const cls = fa.estado==='Pagada'?'b-ok':fa.estado==='Anulada'?'b-err':'b-warn';
      html += '<tr><td><strong>'+_esc(fa.numero)+'</strong></td>' +
              '<td>'+_esc(fa.cliente_nombre)+'</td>' +
              '<td>'+_esc(fa.fecha_emision)+'</td>' +
              '<td>'+fmtM(fa.total)+'</td>' +
              '<td><span class="badge '+cls+'">'+_esc(fa.estado)+'</span></td>' +
              '<td><a href="/api/contabilidad/facturas/'+_esc(fa.numero)+'/pdf" target="_blank" style="color:#15803d">📄 PDF</a></td></tr>';
    });
    html += '</tbody></table>';
    document.getElementById('facturas-list').innerHTML = html;
  } catch(e) { document.getElementById('facturas-list').innerHTML = '<div class="empty">Error</div>'; }
}

function abrirEmitir() {
  alert('Para emitir factura, ir a Contabilidad clásica:\n\n→ /contabilidad\n\nFlujo completo de generación con cliente y pedido.');
  window.location.href = '/contabilidad';
}

async function exportarSiigo() {
  const desde = prompt('Fecha desde (YYYY-MM-DD):', new Date().toISOString().slice(0,7)+'-01');
  if (!desde) return;
  const hasta = prompt('Fecha hasta (YYYY-MM-DD):', new Date().toISOString().slice(0,10));
  if (!hasta) return;
  window.location.href = '/api/contabilidad/export/siigo?desde='+desde+'&hasta='+hasta;
}

async function cargarNomina() {
  try {
    const n = await fetch('/api/contabilidad/nomina').then(r=>r.json());
    if (!(n.periodos||[]).length) { document.getElementById('nomina-list').innerHTML = '<div class="empty">Sin períodos cargados. Ir a /rrhh para gestión completa.</div>'; return; }
    let html = '<table><thead><tr><th>Período</th><th>Empleados</th><th>Total devengado</th><th>Estado</th></tr></thead><tbody>';
    n.periodos.forEach(p => {
      const cls = p.estado==='Pagada'?'b-ok':p.estado==='Aprobada'?'b-warn':'b-err';
      html += '<tr><td><strong>'+_esc(p.periodo)+'</strong></td>' +
              '<td>'+(p.count||0)+'</td>' +
              '<td>'+fmtM(p.total_devengado)+'</td>' +
              '<td><span class="badge '+cls+'">'+_esc(p.estado||'-')+'</span></td></tr>';
    });
    html += '</tbody></table>';
    document.getElementById('nomina-list').innerHTML = html;
  } catch(e) { document.getElementById('nomina-list').innerHTML = '<div class="empty">Error</div>'; }
}

cargarCaja();
setInterval(cargarCaja, 5*60*1000);
</script>
</body>
</html>
"""
