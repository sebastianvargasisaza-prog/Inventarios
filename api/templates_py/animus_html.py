"""ÁNIMUS Lab — Panel administrativo (Caja Menor + Inventario Cíclico).

Reemplaza el panel anterior que duplicaba funcionalidad con marketing
(productos / clientes / IG / contenido / agentes IA / calendario). Ahora
está enfocado en lo que Daniela necesita en la tienda:

  1. Caja menor: registrar ingresos (efectivo de ventas contraentrega) +
     egresos (gastos del local), ver saldo acumulado, KPIs hoy/mes.
  2. Inventario cíclico: contar físicamente cada producto, comparar con
     lo vendido en Shopify, registrar diferencias con explicación.

Si en el futuro el user pide volver a tener marketing en /animus, hay que
crear un redirect de vuelta a /marketing.
"""

ANIMUS_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ÁNIMUS Lab — Panel Administrativo</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos10">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;font-size:14px;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#1e293b;}
::-webkit-scrollbar-thumb{background:#475569;border-radius:3px;}

.hdr{background:#1e293b;border-bottom:1px solid #334155;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.hdr-brand{display:flex;align-items:center;gap:10px;}
.hdr-brand h1{font-size:16px;font-weight:800;color:#fff;}
.hdr-brand span{font-size:11px;color:#94a3b8;background:#0f172a;padding:2px 8px;border-radius:20px;border:1px solid #334155;}
.hdr-user{font-size:12px;color:#64748b;}
.hdr-user strong{color:#e2e8f0;}
.back-link{font-size:12px;color:#667eea;text-decoration:none;display:flex;align-items:center;gap:4px;}
.back-link:hover{color:#818cf8;}

.tabs-bar{background:#1e293b;border-bottom:1px solid #334155;display:flex;overflow-x:auto;padding:0 20px;}
.tab-btn{padding:12px 20px;font-size:13px;font-weight:600;color:#64748b;border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab-btn:hover{color:#e2e8f0;}
.tab-btn.active{color:#34d399;border-bottom-color:#34d399;}
.tab-panel{display:none;padding:24px 20px;}
.tab-panel.active{display:block;}

.page-title{font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:4px;}
.page-sub{font-size:13px;color:#94a3b8;margin-bottom:18px;}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;}
.kpi-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;}
.kpi-card .label{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em;font-weight:700;}
.kpi-card .val{font-size:24px;font-weight:800;margin-top:6px;}
.kpi-card .sub{font-size:11px;color:#94a3b8;margin-top:4px;}
.kpi-green .val{color:#34d399;}
.kpi-red .val{color:#ef4444;}
.kpi-blue .val{color:#60a5fa;}
.kpi-yellow .val{color:#fbbf24;}
.kpi-purple .val{color:#a78bfa;}

.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:18px;margin-bottom:16px;}
.card-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.card-title{font-size:14px;font-weight:700;color:#e2e8f0;}

.btn{padding:8px 14px;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,#10b981,#059669);color:#fff;}
.btn-primary:hover{filter:brightness(1.1);}
.btn-outline{background:transparent;border:1px solid #475569;color:#cbd5e1;}
.btn-outline:hover{background:#334155;}
.btn-danger{background:#7f1d1d;color:#fef2f2;border:1px solid #991b1b;}
.btn-sm{padding:5px 10px;font-size:11px;}

.input,.select,.textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:8px 12px;border-radius:8px;font-size:13px;font-family:inherit;width:100%;}
.input:focus,.select:focus,.textarea:focus{outline:none;border-color:#10b981;}
.textarea{min-height:60px;resize:vertical;}
.label{display:block;font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}

.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;}
.form-row.full{grid-template-columns:1fr;}

table{width:100%;border-collapse:collapse;font-size:13px;}
table thead th{text-align:left;padding:8px 10px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #334155;background:#0f172a;}
table tbody td{padding:8px 10px;color:#e2e8f0;border-bottom:1px solid #1e293b;}
table tbody tr:hover{background:#0f172a55;}

.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;letter-spacing:.05em;}
.badge-green{background:#064e3b;color:#34d399;}
.badge-red{background:#7f1d1d;color:#fca5a5;}
.badge-yellow{background:#78350f;color:#fcd34d;}
.badge-blue{background:#1e3a8a;color:#93c5fd;}
.badge-gray{background:#1f2937;color:#9ca3af;}

.diff-pos{color:#34d399;font-weight:700;}
.diff-neg{color:#ef4444;font-weight:700;}
.diff-zero{color:#64748b;}

#js-error-banner{display:none;position:fixed;top:0;left:0;right:0;z-index:10000;background:#7f1d1d;color:#fef2f2;padding:10px 16px;font-size:12px;font-family:monospace;border-bottom:2px solid #ef4444;}
#toast-container{position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;}
.toast{background:#1e293b;border:1px solid #475569;color:#f1f5f9;padding:12px 18px;border-radius:8px;font-size:13px;font-weight:600;min-width:220px;max-width:360px;box-shadow:0 4px 20px rgba(0,0,0,.4);pointer-events:auto;}
.toast.success{background:#064e3b;border-color:#10b981;}
.toast.error{background:#7f1d1d;border-color:#ef4444;}
</style>
</head>

<div id="js-error-banner"></div>
<div id="toast-container"></div>
<script>
function showToast(msg, type){
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + (type||'');
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function(){ t.style.opacity='0'; t.style.transition='opacity .4s'; setTimeout(function(){t.remove();}, 400); }, 3200);
}
window.addEventListener('error', function(ev){
  try{
    const b = document.getElementById('js-error-banner');
    if (!b) return;
    const msg = (ev.message||(ev.error && ev.error.message)||'?') + ' @ ' + (ev.filename||'').split('/').pop() + ':' + (ev.lineno||'?');
    b.style.display='block';
    b.innerHTML = '! Error JS: ' + msg.substring(0,280);
  }catch(e){}
});
</script>

<body>

<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M12 3l1.9 5.4L19 10l-5.1 1.6L12 17l-1.9-5.4L5 10l5.1-1.6L12 3z"/><path d="M19 17l.6 1.7L21 19l-1.4.3L19 21l-.6-1.7L17 19l1.4-.3z"/></svg>
      ÁNIMUS Lab
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; marca DTC &middot; Shopify &middot; <span style="color:#a8a29e">{usuario}</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<div class="tabs-bar">
  <button class="tab-btn active" data-tab="caja" onclick="switchTab('caja')">&#128176; Caja Menor</button>
  <button class="tab-btn" data-tab="inventario" onclick="switchTab('inventario')">&#128230; Inventario Ciclico</button>
</div>

<!-- TAB: CAJA MENOR -->
<div id="tab-caja" class="tab-panel active">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128176; Caja Menor</div>
      <div class="page-sub">Ingresos en efectivo (ventas contraentrega) y egresos del local. Saldo acumulado.</div>
    </div>
    <button class="btn btn-primary" onclick="abrirRegistro('ingreso')">+ Registrar ingreso</button>
  </div>

  <div class="kpi-grid" id="caja-kpis"></div>

  <div class="card">
    <div class="card-hdr">
      <span class="card-title">Movimientos recientes</span>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <select id="caja-filtro-tipo" class="select" style="width:auto;" onchange="loadCaja()">
          <option value="">Todos</option>
          <option value="ingreso">Solo ingresos</option>
          <option value="egreso">Solo egresos</option>
        </select>
        <input id="caja-filtro-q" class="input" style="width:200px;" placeholder="Buscar concepto..." oninput="loadCaja()">
        <button class="btn btn-outline btn-sm" onclick="abrirRegistro('egreso')">+ Egreso</button>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>Fecha</th>
          <th>Tipo</th>
          <th>Concepto</th>
          <th style="text-align:right;">Monto</th>
          <th>Metodo</th>
          <th>Ref.</th>
          <th>Por</th>
          <th></th>
        </tr></thead>
        <tbody id="caja-body"><tr><td colspan="8" style="color:#64748b;text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- TAB: INVENTARIO CICLICO -->
<div id="tab-inventario" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128230; Inventario Ciclico</div>
      <div class="page-sub">Conta fisicamente cada producto y compara con lo vendido en Shopify. Si hay diferencia, explicala (rotura, devolucion, etc.).</div>
    </div>
    <button class="btn btn-primary" onclick="abrirConteo()">+ Nuevo conteo</button>
  </div>

  <div class="kpi-grid" id="inv-kpis"></div>

  <div class="card">
    <div class="card-hdr"><span class="card-title">SKUs vendidos en Shopify (para contar)</span></div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>SKU</th>
          <th style="text-align:right;">Pedidos</th>
          <th style="text-align:right;">Vendidas (acumulado)</th>
          <th>Ultima venta</th>
          <th>Ultimo conteo</th>
          <th></th>
        </tr></thead>
        <tbody id="inv-skus-body"><tr><td colspan="6" style="color:#64748b;text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-hdr"><span class="card-title">Historial de conteos</span></div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>Fecha</th>
          <th>SKU</th>
          <th>Producto</th>
          <th style="text-align:right;">Shopify</th>
          <th style="text-align:right;">Fisico</th>
          <th style="text-align:right;">Diferencia</th>
          <th>Explicacion</th>
          <th>Por</th>
        </tr></thead>
        <tbody id="inv-conteos-body"><tr><td colspan="8" style="color:#64748b;text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- MODAL: Registro caja menor -->
<div id="modal-caja" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:480px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 id="modal-caja-title" style="font-size:16px;color:#fff;">Registrar movimiento</h3>
      <button onclick="cerrarModal('modal-caja')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <input type="hidden" id="caja-tipo">
    <div class="form-row">
      <div><div class="label">Fecha</div><input id="caja-fecha" type="date" class="input"></div>
      <div><div class="label">Monto (COP) *</div><input id="caja-monto" type="number" min="0" step="100" class="input" placeholder="0"></div>
    </div>
    <div class="form-row full"><div><div class="label">Concepto *</div><input id="caja-concepto" class="input" placeholder="Ej: Pago contraentrega orden #1234"></div></div>
    <div class="form-row">
      <div><div class="label">Metodo</div>
        <select id="caja-metodo" class="select"><option>efectivo</option><option>transferencia</option><option>tarjeta</option><option>otro</option></select>
      </div>
      <div><div class="label">Referencia (opcional)</div><input id="caja-referencia" class="input" placeholder="N orden, factura, etc."></div>
    </div>
    <div class="form-row full"><div><div class="label">Observaciones</div><textarea id="caja-obs" class="textarea" placeholder="Notas adicionales..."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-caja')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCaja()">Guardar</button>
    </div>
  </div>
</div>

<!-- MODAL: Conteo ciclico -->
<div id="modal-conteo" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:520px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:#fff;">&#128230; Nuevo conteo ciclico</h3>
      <button onclick="cerrarModal('modal-conteo')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div class="form-row">
      <div><div class="label">SKU *</div><input id="conteo-sku" class="input" placeholder="Ej: LBHA-30" style="text-transform:uppercase;"></div>
      <div><div class="label">Fecha</div><input id="conteo-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row full"><div><div class="label">Nombre del producto (opcional)</div><input id="conteo-nombre" class="input" placeholder="Ej: Limpiador hidratante 30 g"></div></div>
    <div class="form-row">
      <div><div class="label">Cantidad segun Shopify *</div><input id="conteo-shopify" type="number" min="0" class="input" placeholder="0"></div>
      <div><div class="label">Cantidad fisica (contada) *</div><input id="conteo-fisica" type="number" min="0" class="input" placeholder="0"></div>
    </div>
    <div id="conteo-diff-preview" style="display:none;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:600;margin-bottom:10px;"></div>
    <div class="form-row full"><div><div class="label">Explicacion de la diferencia (si aplica)</div><textarea id="conteo-explicacion" class="textarea" placeholder="Rotura, devolucion no registrada, regalo, robo, error de carga..."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-conteo')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarConteo()">Guardar conteo</button>
    </div>
  </div>
</div>

<script>
// Tabs
const _loaded = {};
function switchTab(name){
  document.querySelectorAll('.tab-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.remove('active');});
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  if (!_loaded[name]) { _loaded[name] = true; loadTab(name); }
}
function loadTab(name){
  if (name === 'caja') loadCaja();
  else if (name === 'inventario') { loadInvSkus(); loadInvConteos(); }
}

function fmtCOP(n){
  if (n == null) return '$ 0';
  return '$ ' + Number(n).toLocaleString('es-CO', {maximumFractionDigits:0});
}
function fmtFecha(s){
  if (!s) return '-';
  return s.slice(0, 10);
}
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function abrirModal(id){ const m=document.getElementById(id); if(m) m.style.display='flex'; }
function cerrarModal(id){ const m=document.getElementById(id); if(m) m.style.display='none'; }

// Caja Menor
async function loadCaja(){
  const tipo = document.getElementById('caja-filtro-tipo').value;
  const q    = document.getElementById('caja-filtro-q').value.trim();
  const qs = [];
  if (tipo) qs.push('tipo=' + encodeURIComponent(tipo));
  if (q)    qs.push('q=' + encodeURIComponent(q));
  const url = '/api/animus/caja' + (qs.length ? '?' + qs.join('&') : '');
  try {
    const r = await fetch(url);
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    renderCajaKPIs(d.kpis||{});
    renderCajaMovs(d.movimientos||[]);
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

function renderCajaKPIs(k){
  const saldo = k.saldo_total || 0;
  const cards = [
    { label: 'Saldo total caja', val: fmtCOP(saldo),
      color: saldo >= 0 ? 'kpi-green' : 'kpi-red',
      sub: (k.n_total||0) + ' movimientos registrados' },
    { label: 'Ingresos hoy', val: fmtCOP(k.ingreso_hoy||0), color:'kpi-green', sub: '' },
    { label: 'Egresos hoy', val: fmtCOP(k.egreso_hoy||0), color:'kpi-red', sub: '' },
    { label: 'Ingresos del mes', val: fmtCOP(k.ingreso_mes||0), color:'kpi-blue', sub: '' },
    { label: 'Egresos del mes', val: fmtCOP(k.egreso_mes||0), color:'kpi-yellow', sub: '' },
  ];
  document.getElementById('caja-kpis').innerHTML = cards.map(function(c){
    return '<div class="kpi-card '+c.color+'">' +
      '<div class="label">'+c.label+'</div>' +
      '<div class="val">'+c.val+'</div>' +
      (c.sub ? '<div class="sub">'+c.sub+'</div>' : '') +
    '</div>';
  }).join('');
}

function renderCajaMovs(rows){
  const body = document.getElementById('caja-body');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8" style="color:#64748b;text-align:center;padding:24px;">Sin movimientos registrados.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(function(m){
    const tipoBadge = m.tipo === 'ingreso'
      ? '<span class="badge badge-green">+ Ingreso</span>'
      : '<span class="badge badge-red">- Egreso</span>';
    const monto = m.tipo === 'ingreso'
      ? '<span class="diff-pos">+' + fmtCOP(m.monto) + '</span>'
      : '<span class="diff-neg">-' + fmtCOP(m.monto) + '</span>';
    return '<tr>' +
      '<td>'+fmtFecha(m.fecha)+'</td>' +
      '<td>'+tipoBadge+'</td>' +
      '<td>'+esc(m.concepto||'')+'</td>' +
      '<td style="text-align:right;font-weight:700;">'+monto+'</td>' +
      '<td><span class="badge badge-gray">'+esc(m.metodo||'efectivo')+'</span></td>' +
      '<td style="font-size:11px;color:#94a3b8;">'+esc(m.referencia||'-')+'</td>' +
      '<td style="font-size:11px;color:#64748b;">'+esc(m.registrado_por||'-')+'</td>' +
      '<td><button class="btn btn-outline btn-sm" onclick="eliminarCaja('+m.id+')" title="Eliminar">x</button></td>' +
    '</tr>';
  }).join('');
}

function abrirRegistro(tipo){
  document.getElementById('caja-tipo').value = tipo;
  document.getElementById('modal-caja-title').textContent =
    tipo === 'ingreso' ? '+ Registrar ingreso' : '- Registrar egreso';
  document.getElementById('caja-fecha').value = new Date().toISOString().slice(0,10);
  ['monto','concepto','referencia','obs'].forEach(function(f){
    const el = document.getElementById('caja-'+f);
    if (el) el.value = '';
  });
  document.getElementById('caja-metodo').value = 'efectivo';
  abrirModal('modal-caja');
}

async function guardarCaja(){
  const body = {
    tipo: document.getElementById('caja-tipo').value,
    fecha: document.getElementById('caja-fecha').value,
    monto: parseFloat(document.getElementById('caja-monto').value || 0),
    concepto: document.getElementById('caja-concepto').value.trim(),
    metodo: document.getElementById('caja-metodo').value,
    referencia: document.getElementById('caja-referencia').value.trim(),
    observaciones: document.getElementById('caja-obs').value.trim(),
  };
  if (!body.monto || body.monto <= 0) { showToast('Monto debe ser mayor a 0', 'error'); return; }
  if (!body.concepto) { showToast('Concepto requerido', 'error'); return; }
  try {
    const r = await fetch('/api/animus/caja', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Movimiento registrado', 'success');
    cerrarModal('modal-caja');
    loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

async function eliminarCaja(id){
  if (!confirm('Eliminar este movimiento? Solo admin puede.')) return;
  try {
    const r = await fetch('/api/animus/caja/' + id, { method:'DELETE' });
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Eliminado', 'success');
    loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Inventario Ciclico
let _SKUS_CACHE = [];

async function loadInvSkus(){
  try {
    const r = await fetch('/api/animus/inventario-ciclico/skus');
    const d = await r.json();
    if (!d.ok) { showToast('Error skus: ' + (d.error||'?'), 'error'); return; }
    _SKUS_CACHE = d.skus || [];
    const body = document.getElementById('inv-skus-body');
    if (!_SKUS_CACHE.length) {
      body.innerHTML = '<tr><td colspan="6" style="color:#64748b;text-align:center;padding:24px;">Sin SKUs vendidos en Shopify aun. Sincroniza Shopify desde marketing primero.</td></tr>';
      return;
    }
    body.innerHTML = _SKUS_CACHE.map(function(s){
      const ult = s.ultimo_conteo;
      let ultStr = '<span style="color:#64748b;">Nunca contado</span>';
      if (ult) {
        const diffStr = ult.diferencia === 0 ? '<span class="diff-zero">0</span>'
          : (ult.diferencia > 0 ? '<span class="diff-pos">+'+ult.diferencia+'</span>'
                                : '<span class="diff-neg">'+ult.diferencia+'</span>');
        ultStr = '<span style="font-size:11px;color:#94a3b8;">'+fmtFecha(ult.fecha)+': fisico '+ult.cantidad_fisica+' &middot; dif '+diffStr+'</span>';
      }
      const skuEsc = esc(s.sku).replace(/'/g,'’');
      return '<tr>' +
        '<td style="font-family:monospace;font-weight:700;">'+esc(s.sku)+'</td>' +
        '<td style="text-align:right;">'+s.n_orders+'</td>' +
        '<td style="text-align:right;font-weight:700;color:#60a5fa;">'+s.uds_vendidas+'</td>' +
        '<td style="font-size:11px;color:#94a3b8;">'+fmtFecha(s.ultima_venta)+'</td>' +
        '<td>'+ultStr+'</td>' +
        '<td><button class="btn btn-primary btn-sm" data-sku="'+esc(s.sku)+'" data-uds="'+s.uds_vendidas+'" onclick="abrirConteoSkuFromBtn(this)">Contar</button></td>' +
      '</tr>';
    }).join('');
  } catch(e) {
    showToast('Error skus: ' + e.message, 'error');
  }
}

async function loadInvConteos(){
  try {
    const r = await fetch('/api/animus/inventario-ciclico');
    const d = await r.json();
    if (!d.ok) { showToast('Error conteos: ' + (d.error||'?'), 'error'); return; }
    renderInvKpis(d.kpis||{});
    const body = document.getElementById('inv-conteos-body');
    if (!d.conteos.length) {
      body.innerHTML = '<tr><td colspan="8" style="color:#64748b;text-align:center;padding:24px;">Sin conteos registrados aun.</td></tr>';
      return;
    }
    body.innerHTML = d.conteos.map(function(co){
      const dif = co.diferencia;
      const difStr = dif === 0 ? '<span class="diff-zero">0</span>'
        : (dif > 0 ? '<span class="diff-pos">+'+dif+'</span>' : '<span class="diff-neg">'+dif+'</span>');
      return '<tr>' +
        '<td>'+fmtFecha(co.fecha_conteo)+'</td>' +
        '<td style="font-family:monospace;font-weight:700;">'+esc(co.sku)+'</td>' +
        '<td>'+esc(co.producto_nombre||'-')+'</td>' +
        '<td style="text-align:right;color:#60a5fa;">'+co.cantidad_shopify+'</td>' +
        '<td style="text-align:right;font-weight:700;">'+co.cantidad_fisica+'</td>' +
        '<td style="text-align:right;font-weight:700;">'+difStr+'</td>' +
        '<td style="font-size:11px;color:#cbd5e1;max-width:240px;">'+esc(co.explicacion||'')+'</td>' +
        '<td style="font-size:11px;color:#64748b;">'+esc(co.registrado_por||'')+'</td>' +
      '</tr>';
    }).join('');
  } catch(e) {
    showToast('Error conteos: ' + e.message, 'error');
  }
}

function renderInvKpis(k){
  const cards = [
    { label:'Conteos totales', val: k.n_total||0, color:'kpi-blue', sub:'' },
    { label:'Conteos con diferencia', val: k.n_con_dif||0, color:'kpi-yellow', sub:'' },
    { label:'Unidades faltantes', val: k.uds_faltantes||0, color:'kpi-red', sub:'Acumulado' },
    { label:'Unidades sobrantes', val: k.uds_sobrantes||0, color:'kpi-green', sub:'Acumulado' },
  ];
  document.getElementById('inv-kpis').innerHTML = cards.map(function(c){
    return '<div class="kpi-card '+c.color+'">' +
      '<div class="label">'+c.label+'</div>' +
      '<div class="val">'+c.val+'</div>' +
      (c.sub ? '<div class="sub">'+c.sub+'</div>' : '') +
    '</div>';
  }).join('');
}

function abrirConteo(){
  ['sku','nombre','shopify','fisica','explicacion'].forEach(function(f){
    const el = document.getElementById('conteo-'+f);
    if (el) el.value = '';
  });
  document.getElementById('conteo-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('conteo-diff-preview').style.display='none';
  // Wire up live preview de diferencia
  const fisica = document.getElementById('conteo-fisica');
  fisica.oninput = actualizarPreviewDiff;
  abrirModal('modal-conteo');
}

function abrirConteoSkuFromBtn(btn){
  const sku = btn.getAttribute('data-sku');
  const uds = parseInt(btn.getAttribute('data-uds')||0);
  abrirConteo();
  document.getElementById('conteo-sku').value = sku;
  document.getElementById('conteo-shopify').value = uds;
  setTimeout(function(){ document.getElementById('conteo-fisica').focus(); }, 100);
}

function actualizarPreviewDiff(){
  const sh = parseInt(document.getElementById('conteo-shopify').value || 0);
  const fi = parseInt(document.getElementById('conteo-fisica').value || 0);
  const dif = fi - sh;
  const prev = document.getElementById('conteo-diff-preview');
  if (isNaN(fi) || document.getElementById('conteo-fisica').value === '') {
    prev.style.display = 'none';
    return;
  }
  prev.style.display = 'block';
  if (dif === 0) {
    prev.style.background = '#064e3b'; prev.style.color = '#34d399';
    prev.textContent = 'OK: cuadra perfecto - 0 unidades de diferencia';
  } else if (dif < 0) {
    prev.style.background = '#7f1d1d'; prev.style.color = '#fca5a5';
    prev.textContent = 'FALTAN ' + Math.abs(dif) + ' unidades. Explica la diferencia abajo.';
  } else {
    prev.style.background = '#78350f'; prev.style.color = '#fcd34d';
    prev.textContent = 'SOBRAN ' + dif + ' unidades. Explica la diferencia abajo.';
  }
}

async function guardarConteo(){
  const sku = document.getElementById('conteo-sku').value.trim().toUpperCase();
  if (!sku) { showToast('SKU requerido', 'error'); return; }
  const sh = parseInt(document.getElementById('conteo-shopify').value || 0);
  const fi = parseInt(document.getElementById('conteo-fisica').value || 0);
  if (isNaN(fi)) { showToast('Cantidad fisica requerida', 'error'); return; }
  const explicacion = document.getElementById('conteo-explicacion').value.trim();
  const dif = fi - sh;
  if (dif !== 0 && !explicacion) {
    if (!confirm('Hay diferencia de '+dif+' unidades sin explicacion. Guardar igual?')) return;
  }
  const body = {
    sku: sku,
    producto_nombre: document.getElementById('conteo-nombre').value.trim(),
    fecha_conteo: document.getElementById('conteo-fecha').value,
    cantidad_shopify: sh,
    cantidad_fisica: fi,
    explicacion: explicacion,
  };
  try {
    const r = await fetch('/api/animus/inventario-ciclico', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Conteo registrado - diferencia ' + d.diferencia, 'success');
    cerrarModal('modal-conteo');
    loadInvSkus();
    loadInvConteos();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Init
loadCaja();
</script>
</body>
</html>"""
