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
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ÁNIMUS Lab — Panel Administrativo</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
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

// CSRF defense-in-depth - Sebastian 3-may-2026
function _csrf() {
  var m = document.cookie.match(/(?:^|;[ \t]*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}
function _fetchOpts(method, body) {
  var headers = {};
  var tok = _csrf();
  if (tok) headers['X-CSRF-Token'] = tok;
  var opts = {method: method || 'GET', headers: headers, credentials: 'same-origin'};
  if (body !== undefined && body !== null) {
    headers['Content-Type'] = 'application/json';
    opts.body = (typeof body === 'string') ? body : JSON.stringify(body);
  }
  return opts;
}
fetch('/api/csrf-token', {credentials: 'same-origin'}).catch(function(){});
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
  <button class="tab-btn" data-tab="invfis" onclick="switchTab('invfis')">&#128202; Inventario Fisico</button>
  <button class="tab-btn" data-tab="inventario" onclick="switchTab('inventario')">&#128230; Conteo Ciclico</button>
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

<!-- TAB: INVENTARIO FISICO (modelo nuevo · ecuacion contable) -->
<div id="tab-invfis" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128202; Inventario Fisico</div>
      <div class="page-sub">Esperado = baseline + entradas - ventas Shopify - salidas. Si no cuadra, se ve el desglose y donde esta el error.</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-outline" onclick="abrirBaseline()">+ Baseline</button>
      <button class="btn btn-primary" onclick="abrirEntrada()">+ Entrada</button>
      <button class="btn btn-outline" onclick="abrirSalida()">+ Salida</button>
      <button class="btn btn-outline" onclick="syncShopifyInv()" title="Refleja ventas Shopify ya descargadas en inv fisico">&#128260; Sync Shopify</button>
      <button class="btn btn-outline" onclick="asignarConteoHoy()" title="Asigna SKUs al azar a contar hoy">&#128202; Asignar conteo hoy</button>
    </div>
  </div>

  <div id="invfis-resumen" class="kpi-grid"></div>

  <!-- DIAGNOSTICO -->
  <div class="card" id="invfis-diag-card" style="display:none;">
    <div class="card-hdr">
      <span class="card-title">&#127919; Diagnostico de discrepancias (90d)</span>
      <button class="btn btn-outline btn-sm" onclick="cargarDiagnostico()">Refrescar</button>
    </div>
    <div id="invfis-diag-content" style="padding:8px 0;"></div>
  </div>

  <!-- CONTEOS PENDIENTES -->
  <div class="card" id="invfis-conteos-card" style="border-left:4px solid #6366f1;">
    <div class="card-hdr">
      <span class="card-title">&#9888; Conteos pendientes hoy</span>
      <span id="invfis-conteos-count" style="font-size:11px;color:#94a3b8;"></span>
    </div>
    <div id="invfis-pendientes" style="padding:8px 0;">
      <div style="color:#64748b;text-align:center;padding:14px;font-size:13px;">Sin conteos pendientes</div>
    </div>
  </div>

  <div class="card">
    <div class="card-hdr">
      <span class="card-title">Inventario esperado por SKU</span>
      <input id="invfis-q" class="input" style="max-width:220px" placeholder="Buscar SKU..." oninput="renderInvFis()">
    </div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>SKU</th>
          <th>Baseline</th>
          <th>Fecha</th>
          <th style="text-align:right;">Entradas</th>
          <th style="text-align:right;">Shopify</th>
          <th style="text-align:right;">Salidas</th>
          <th style="text-align:right;">Ajustes</th>
          <th style="text-align:right;">Esperado</th>
          <th></th>
        </tr></thead>
        <tbody id="invfis-tbody"><tr><td colspan="9" style="color:#64748b;text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
    <div id="pg-invfis"></div>
  </div>

  <div class="card">
    <div class="card-hdr"><span class="card-title">Movimientos recientes</span></div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>Fecha</th>
          <th>SKU</th>
          <th>Tipo</th>
          <th style="text-align:right;">Cantidad</th>
          <th>Origen</th>
          <th>Motivo</th>
          <th>Por</th>
        </tr></thead>
        <tbody id="invfis-mov-body"><tr><td colspan="7" style="color:#64748b;text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- MODAL: Baseline -->
<div id="modal-baseline" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:480px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:#fff;">&#128202; Registrar baseline</h3>
      <button onclick="cerrarModal('modal-baseline')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="background:#0f172a;border-left:3px solid #6366f1;padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px;color:#cbd5e1;">
      El baseline es la cantidad fisica que tienes HOY de un SKU. A partir de aqui el sistema rastrea entradas y salidas. Si ya hay baseline para este SKU, se actualiza.
    </div>
    <div class="form-row">
      <div><div class="label">SKU *</div><input id="bl-sku" class="input" placeholder="Ej: LBHA-30" style="text-transform:uppercase"></div>
      <div><div class="label">Fecha</div><input id="bl-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row full"><div><div class="label">Descripcion (opcional)</div><input id="bl-desc" class="input" placeholder="Hydra Balance 30ml"></div></div>
    <div class="form-row full"><div><div class="label">Unidades fisicas que TIENES HOY *</div><input id="bl-unidades" type="number" min="0" class="input" placeholder="0"></div></div>
    <div class="form-row full"><div><div class="label">Observaciones</div><textarea id="bl-obs" class="textarea" placeholder="Como se conto, donde estaban, etc."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-baseline')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarBaseline()">Guardar baseline</button>
    </div>
  </div>
</div>

<!-- MODAL: Entrada -->
<div id="modal-entrada" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:480px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:#fff;">+ Entrada de inventario</h3>
      <button onclick="cerrarModal('modal-entrada')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div class="form-row">
      <div><div class="label">SKU *</div><input id="en-sku" class="input" placeholder="Ej: LBHA-30" style="text-transform:uppercase"></div>
      <div><div class="label">Fecha</div><input id="en-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row">
      <div><div class="label">Cantidad *</div><input id="en-cantidad" type="number" min="1" class="input" placeholder="0"></div>
      <div><div class="label">Origen *</div>
        <select id="en-origen" class="select">
          <option value="produccion">Produccion (lote nuevo)</option>
          <option value="devolucion">Devolucion cliente</option>
          <option value="ajuste">Ajuste positivo</option>
          <option value="otro">Otro</option>
        </select>
      </div>
    </div>
    <div class="form-row full"><div><div class="label">Referencia (lote, factura)</div><input id="en-ref" class="input" placeholder="LOTE-001 / FAC-XX"></div></div>
    <div class="form-row full"><div><div class="label">Motivo / Notas</div><textarea id="en-motivo" class="textarea" placeholder="Detalles..."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-entrada')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarEntrada()">Guardar entrada</button>
    </div>
  </div>
</div>

<!-- MODAL: Salida -->
<div id="modal-salida" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:480px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:#fff;">- Salida de inventario (NO Shopify)</h3>
      <button onclick="cerrarModal('modal-salida')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="background:#0f172a;border-left:3px solid #f59e0b;padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px;color:#cbd5e1;">
      Las ventas de Shopify se descuentan automaticamente. Esto es para SALIDAS QUE NO SON SHOPIFY: regalos, daños, vencidos, ventas presenciales, devoluciones a planta.
    </div>
    <div class="form-row">
      <div><div class="label">SKU *</div><input id="sa-sku" class="input" placeholder="Ej: LBHA-30" style="text-transform:uppercase"></div>
      <div><div class="label">Fecha</div><input id="sa-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row">
      <div><div class="label">Cantidad *</div><input id="sa-cantidad" type="number" min="1" class="input" placeholder="0"></div>
      <div><div class="label">Origen *</div>
        <select id="sa-origen" class="select">
          <option value="presencial">Venta presencial</option>
          <option value="regalo">Regalo / muestra</option>
          <option value="dano">Daño / rotura</option>
          <option value="vencido">Vencido</option>
          <option value="devolucion_planta">Devolucion a planta</option>
          <option value="otro">Otro</option>
        </select>
      </div>
    </div>
    <div class="form-row full"><div><div class="label">Referencia</div><input id="sa-ref" class="input" placeholder="Pedido, persona, etc."></div></div>
    <div class="form-row full"><div><div class="label">Motivo / Notas</div><textarea id="sa-motivo" class="textarea" placeholder="Detalles..."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-salida')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSalida()">Guardar salida</button>
    </div>
  </div>
</div>

<!-- MODAL: Registrar conteo de SKU asignado -->
<div id="modal-conteo-fisico" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#1e293b;border:1px solid #475569;border-radius:14px;padding:22px;width:560px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:#fff;">&#128202; Registrar conteo fisico</h3>
      <button onclick="cerrarModal('modal-conteo-fisico')" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <input type="hidden" id="cf-asig-id">
    <div id="cf-sku-info" style="background:#0f172a;border-left:3px solid #22d3ee;padding:14px;border-radius:6px;margin-bottom:14px;font-size:13px;color:#cbd5e1;">
      <div id="cf-sku-titulo" style="font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">SKU</div>
      <div id="cf-desglose"></div>
    </div>
    <div class="form-row full"><div><div class="label">Cantidad fisica contada *</div><input id="cf-cantidad" type="number" min="0" class="input" placeholder="0"></div></div>
    <div id="cf-diff-preview" style="display:none;padding:14px;border-radius:8px;font-size:14px;font-weight:700;margin-bottom:14px;text-align:center;"></div>
    <div class="form-row full" id="cf-motivo-row" style="display:none;"><div><div class="label">Motivo de la diferencia *</div><textarea id="cf-motivo" class="textarea" placeholder="Robo, daño, devolucion no registrada, regalo no anotado, error mapeo Shopify..."></textarea></div></div>
    <div class="form-row full"><label style="display:flex;align-items:center;gap:8px;color:#cbd5e1;font-size:13px;"><input type="checkbox" id="cf-aplicar"> Aplicar ajuste para que el sistema cuadre con tu conteo</label></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-conteo-fisico')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarConteoFisico()">Guardar conteo</button>
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
  else if (name === 'invfis') { cargarInvFisico(); cargarMovimientosInvFis(); }
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
    const r = await fetch('/api/animus/caja', _fetchOpts('POST', body));
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
    const r = await fetch('/api/animus/inventario-ciclico', _fetchOpts('POST', body));
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

// ════════════════════════════════════════════════════════════════
// INVENTARIO FISICO (Fase 1 UI)
// ════════════════════════════════════════════════════════════════
var INVFIS_DATA = [];

async function cargarInvFisico() {
  try {
    var r = await fetch('/api/animus/inv-fisico/esperado');
    var d = await r.json();
    INVFIS_DATA = d.items || [];
    renderInvFis();
  } catch(e) { showToast('Error cargando inv fisico: ' + e.message, 'error'); }
}

function renderInvFis() {
  var q = (document.getElementById('invfis-q')||{value:''}).value.toLowerCase();
  var tb = document.getElementById('invfis-tbody');
  var resumen = document.getElementById('invfis-resumen');
  var data = q ? INVFIS_DATA.filter(function(x){
    return (x.sku||'').toLowerCase().indexOf(q) >= 0;
  }) : INVFIS_DATA;

  if (resumen) {
    var totEsp = data.reduce(function(s,x){ return s + (x.esperado||0); }, 0);
    var totBase = data.reduce(function(s,x){ return s + (x.baseline||0); }, 0);
    var totEnt = data.reduce(function(s,x){ return s + (x.entradas||0); }, 0);
    var totShop = data.reduce(function(s,x){ return s + (x.shopify||0); }, 0);
    resumen.innerHTML =
      '<div class="kpi"><div class="kpi-label">SKUs activos</div><div class="kpi-val">' + data.length + '</div></div>' +
      '<div class="kpi"><div class="kpi-label">Stock esperado</div><div class="kpi-val">' + totEsp + '</div></div>' +
      '<div class="kpi"><div class="kpi-label">Total baseline</div><div class="kpi-val">' + totBase + '</div></div>' +
      '<div class="kpi"><div class="kpi-label">Entradas registradas</div><div class="kpi-val good">+' + totEnt + '</div></div>' +
      '<div class="kpi"><div class="kpi-label">Vendido Shopify</div><div class="kpi-val warn">-' + totShop + '</div></div>';
  }

  if (!data.length) {
    tb.innerHTML = '<tr><td colspan="9" style="color:#64748b;text-align:center;padding:24px;">' +
      (q ? 'Sin coincidencias' : 'Aun no hay SKUs con baseline. Click "+ Baseline" para empezar.') +
      '</td></tr>';
    return;
  }
  tb.innerHTML = data.map(function(x) {
    return '<tr>' +
      '<td><b>' + (x.sku||'') + '</b></td>' +
      '<td>' + x.baseline + '</td>' +
      '<td style="font-size:11px;color:#94a3b8;">' + (x.fecha_baseline||'') + '</td>' +
      '<td style="text-align:right;color:#4ade80;font-weight:600;">+' + x.entradas + '</td>' +
      '<td style="text-align:right;color:#fbbf24;font-weight:600;">-' + x.shopify + '</td>' +
      '<td style="text-align:right;color:#f87171;font-weight:600;">-' + x.salidas + '</td>' +
      '<td style="text-align:right;color:#a78bfa;font-weight:600;">' + (x.ajustes>0?'+':'') + x.ajustes + '</td>' +
      '<td style="text-align:right;font-weight:800;font-size:14px;color:#22d3ee;">' + x.esperado + '</td>' +
      '<td><button class="btn btn-outline btn-sm" onclick="verMovsSku(\'' + (x.sku||'').replace(/[\'\\\\]/g, '') + '\')">Ver mov</button></td>' +
      '</tr>';
  }).join('');
}

async function cargarMovimientosInvFis() {
  try {
    var r = await fetch('/api/animus/inv-fisico/movimientos');
    var d = await r.json();
    var tb = document.getElementById('invfis-mov-body');
    var movs = d.movimientos || [];
    if (!movs.length) { tb.innerHTML = '<tr><td colspan="7" style="color:#64748b;text-align:center;padding:24px;">Sin movimientos</td></tr>'; return; }
    tb.innerHTML = movs.slice(0, 100).map(function(m) {
      var col = m.tipo === 'ENTRADA' ? '#4ade80' :
                m.tipo === 'SHOPIFY_VENTA' ? '#fbbf24' :
                m.tipo === 'SALIDA' ? '#f87171' :
                m.tipo === 'AJUSTE' ? '#a78bfa' : '#94a3b8';
      var sign = (m.tipo === 'ENTRADA' || m.tipo === 'BASELINE') ? '+' :
                 (m.tipo === 'AJUSTE' ? '' : '-');
      return '<tr>' +
        '<td style="font-size:12px;">' + (m.fecha||'') + '</td>' +
        '<td><b>' + (m.sku||'') + '</b></td>' +
        '<td><span style="background:' + col + '22;color:' + col + ';padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">' + (m.tipo||'') + '</span></td>' +
        '<td style="text-align:right;color:' + col + ';font-weight:700;">' + sign + (m.cantidad||0) + '</td>' +
        '<td style="font-size:12px;color:#cbd5e1;">' + (m.origen||'') + '</td>' +
        '<td style="font-size:12px;color:#94a3b8;">' + (m.motivo||'') + '</td>' +
        '<td style="font-size:11px;color:#94a3b8;">' + (m.usuario||'') + '</td>' +
        '</tr>';
    }).join('');
  } catch(e) { console.error(e); }
}

function verMovsSku(sku) {
  document.getElementById('invfis-q').value = sku;
  fetch('/api/animus/inv-fisico/movimientos?sku=' + encodeURIComponent(sku))
    .then(function(r){return r.json();})
    .then(function(d){
      var tb = document.getElementById('invfis-mov-body');
      var movs = d.movimientos || [];
      if (!movs.length) { tb.innerHTML = '<tr><td colspan="7" style="color:#64748b;text-align:center;padding:24px;">Sin movimientos para ' + sku + '</td></tr>'; return; }
      tb.innerHTML = movs.map(function(m) {
        var col = m.tipo === 'ENTRADA' ? '#4ade80' :
                  m.tipo === 'SHOPIFY_VENTA' ? '#fbbf24' :
                  m.tipo === 'SALIDA' ? '#f87171' :
                  m.tipo === 'AJUSTE' ? '#a78bfa' : '#94a3b8';
        var sign = (m.tipo === 'ENTRADA' || m.tipo === 'BASELINE') ? '+' : (m.tipo === 'AJUSTE' ? '' : '-');
        return '<tr><td>' + (m.fecha||'') + '</td><td><b>' + (m.sku||'') + '</b></td><td>' + (m.tipo||'') + '</td><td style="text-align:right;color:' + col + ';font-weight:700;">' + sign + (m.cantidad||0) + '</td><td>' + (m.origen||'') + '</td><td>' + (m.motivo||'') + '</td><td>' + (m.usuario||'') + '</td></tr>';
      }).join('');
    });
  renderInvFis();
}

function abrirBaseline() {
  document.getElementById('bl-sku').value = '';
  document.getElementById('bl-desc').value = '';
  document.getElementById('bl-unidades').value = '';
  document.getElementById('bl-obs').value = '';
  document.getElementById('bl-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('modal-baseline').style.display = 'flex';
}
async function guardarBaseline() {
  var payload = {
    sku: (document.getElementById('bl-sku').value||'').toUpperCase().trim(),
    descripcion: document.getElementById('bl-desc').value,
    unidades_baseline: parseInt(document.getElementById('bl-unidades').value, 10),
    fecha_baseline: document.getElementById('bl-fecha').value,
    observaciones: document.getElementById('bl-obs').value,
  };
  if (!payload.sku) { showToast('SKU obligatorio', 'error'); return; }
  if (isNaN(payload.unidades_baseline) || payload.unidades_baseline < 0) { showToast('Unidades invalido', 'error'); return; }
  try {
    var r = await fetch('/api/animus/inv-fisico/baseline', _fetchOpts('POST', payload));
    var d = await r.json();
    if (d.ok) {
      showToast('Baseline guardado: ' + payload.sku + ' = ' + payload.unidades_baseline, 'success');
      cerrarModal('modal-baseline');
      cargarInvFisico();
    } else { showToast('Error: ' + (d.error||'?'), 'error'); }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

function abrirEntrada() {
  document.getElementById('en-sku').value = '';
  document.getElementById('en-cantidad').value = '';
  document.getElementById('en-ref').value = '';
  document.getElementById('en-motivo').value = '';
  document.getElementById('en-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('modal-entrada').style.display = 'flex';
}
async function guardarEntrada() {
  var payload = {
    sku: (document.getElementById('en-sku').value||'').toUpperCase().trim(),
    cantidad: parseInt(document.getElementById('en-cantidad').value, 10),
    origen: document.getElementById('en-origen').value,
    fecha: document.getElementById('en-fecha').value,
    referencia: document.getElementById('en-ref').value,
    motivo: document.getElementById('en-motivo').value,
  };
  if (!payload.sku) { showToast('SKU obligatorio', 'error'); return; }
  if (isNaN(payload.cantidad) || payload.cantidad <= 0) { showToast('Cantidad debe ser > 0', 'error'); return; }
  try {
    var r = await fetch('/api/animus/inv-fisico/entrada', _fetchOpts('POST', payload));
    var d = await r.json();
    if (d.ok) {
      showToast('Entrada registrada: +' + payload.cantidad + ' uds de ' + payload.sku, 'success');
      cerrarModal('modal-entrada');
      cargarInvFisico();
      cargarMovimientosInvFis();
    } else { showToast('Error: ' + (d.error||'?'), 'error'); }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

function abrirSalida() {
  document.getElementById('sa-sku').value = '';
  document.getElementById('sa-cantidad').value = '';
  document.getElementById('sa-ref').value = '';
  document.getElementById('sa-motivo').value = '';
  document.getElementById('sa-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('modal-salida').style.display = 'flex';
}
async function guardarSalida() {
  var payload = {
    sku: (document.getElementById('sa-sku').value||'').toUpperCase().trim(),
    cantidad: parseInt(document.getElementById('sa-cantidad').value, 10),
    origen: document.getElementById('sa-origen').value,
    fecha: document.getElementById('sa-fecha').value,
    referencia: document.getElementById('sa-ref').value,
    motivo: document.getElementById('sa-motivo').value,
  };
  if (!payload.sku) { showToast('SKU obligatorio', 'error'); return; }
  if (isNaN(payload.cantidad) || payload.cantidad <= 0) { showToast('Cantidad debe ser > 0', 'error'); return; }
  try {
    var r = await fetch('/api/animus/inv-fisico/salida', _fetchOpts('POST', payload));
    var d = await r.json();
    if (d.ok) {
      showToast('Salida registrada: -' + payload.cantidad + ' uds de ' + payload.sku, 'success');
      cerrarModal('modal-salida');
      cargarInvFisico();
      cargarMovimientosInvFis();
    } else { showToast('Error: ' + (d.error||'?'), 'error'); }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

// ════════════════════════════════════════════════════════════════
// CONTEO CICLICO Fase 2 (asignaciones + registro)
// ════════════════════════════════════════════════════════════════
async function cargarPendientesConteo() {
  try {
    var r = await fetch('/api/animus/inv-fisico/conteo/pendientes');
    var d = await r.json();
    var pend = d.pendientes || [];
    var el = document.getElementById('invfis-pendientes');
    var cnt = document.getElementById('invfis-conteos-count');
    if (cnt) cnt.textContent = pend.length ? (pend.length + ' SKUs por contar') : '';
    if (!pend.length) {
      el.innerHTML = '<div style="color:#64748b;text-align:center;padding:14px;font-size:13px;">Sin conteos pendientes &middot; Click "Asignar conteo hoy" para empezar</div>';
      return;
    }
    el.innerHTML = pend.map(function(p) {
      return '<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid #334155;">' +
        '<div><b style="color:#fff;">' + (p.sku||'') + '</b> ' +
        '<span style="color:#94a3b8;font-size:12px;margin-left:8px;">esperado: ' + (p.esperado!=null?p.esperado:'?') + '</span>' +
        '<span style="color:#64748b;font-size:11px;margin-left:8px;">' + (p.fecha_asignado||'') + '</span></div>' +
        '<button class="btn btn-primary btn-sm" onclick="abrirConteoFisico(' + p.id + ', \'' + (p.sku||'').replace(/[\'\\\\]/g,'') + '\', ' + (p.esperado||0) + ')">Contar</button>' +
        '</div>';
    }).join('');
  } catch(e) { console.error(e); }
}

async function asignarConteoHoy() {
  if (!confirm('Asignar 5 SKUs para contar hoy? Si ya hay asignaciones pendientes, no se duplican.')) return;
  try {
    var r = await fetch('/api/animus/inv-fisico/conteo/asignar-hoy', _fetchOpts('POST', {n: 5}));
    var d = await r.json();
    if (d.ok) {
      var n = (d.asignados||[]).length || d.ya_asignados_hoy || 0;
      showToast(n + ' SKUs asignados', 'success');
      cargarPendientesConteo();
    } else {
      showToast('Error: ' + (d.error||'?'), 'error');
    }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

async function syncShopifyInv() {
  showToast('Sincronizando ventas Shopify...', 'info');
  try {
    var r = await fetch('/api/animus/inv-fisico/sync-shopify', _fetchOpts('POST'));
    var d = await r.json();
    if (d.ok) {
      showToast(d.ventas_creadas + ' ventas Shopify reflejadas en inventario', 'success');
      cargarInvFisico();
      cargarMovimientosInvFis();
    } else { showToast('Error: ' + (d.error||'?'), 'error'); }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

var CONTEO_DESGLOSE = null;
function abrirConteoFisico(asigId, sku, esperado) {
  document.getElementById('cf-asig-id').value = asigId;
  document.getElementById('cf-sku-titulo').textContent = sku;
  document.getElementById('cf-cantidad').value = '';
  document.getElementById('cf-motivo').value = '';
  document.getElementById('cf-aplicar').checked = false;
  document.getElementById('cf-diff-preview').style.display = 'none';
  document.getElementById('cf-motivo-row').style.display = 'none';
  // Cargar desglose
  fetch('/api/animus/inv-fisico/esperado/' + encodeURIComponent(sku))
    .then(function(r){return r.json();})
    .then(function(info){
      CONTEO_DESGLOSE = info;
      var d = document.getElementById('cf-desglose');
      d.innerHTML =
        '<div style="display:grid;grid-template-columns:auto auto;gap:6px 16px;font-size:12px;">' +
        '<span style="color:#94a3b8;">Baseline (' + (info.fecha_baseline||'') + ')</span><span style="text-align:right;color:#fff;font-weight:600;">' + info.baseline + '</span>' +
        '<span style="color:#94a3b8;">+ Entradas</span><span style="text-align:right;color:#4ade80;font-weight:600;">+' + info.entradas + '</span>' +
        '<span style="color:#94a3b8;">- Ventas Shopify</span><span style="text-align:right;color:#fbbf24;font-weight:600;">-' + info.shopify + '</span>' +
        '<span style="color:#94a3b8;">- Salidas otras</span><span style="text-align:right;color:#f87171;font-weight:600;">-' + info.salidas + '</span>' +
        '<span style="color:#94a3b8;">+/- Ajustes</span><span style="text-align:right;color:#a78bfa;font-weight:600;">' + (info.ajustes>=0?'+':'') + info.ajustes + '</span>' +
        '<hr style="grid-column:1/-1;border:none;border-top:1px solid #334155;margin:4px 0;">' +
        '<span style="color:#fff;font-weight:700;">= ESPERADO</span><span style="text-align:right;color:#22d3ee;font-weight:800;font-size:18px;">' + info.esperado + '</span>' +
        '</div>';
    });
  // Live preview de diferencia al escribir
  var input = document.getElementById('cf-cantidad');
  input.oninput = function() {
    var fisica = parseInt(input.value, 10);
    if (isNaN(fisica) || !CONTEO_DESGLOSE) {
      document.getElementById('cf-diff-preview').style.display = 'none';
      document.getElementById('cf-motivo-row').style.display = 'none';
      return;
    }
    var diff = fisica - CONTEO_DESGLOSE.esperado;
    var prev = document.getElementById('cf-diff-preview');
    prev.style.display = 'block';
    if (diff === 0) {
      prev.style.background = '#064e3b';
      prev.style.color = '#4ade80';
      prev.innerHTML = '&#10003; Cuadra perfecto · esperado=' + CONTEO_DESGLOSE.esperado + ' · fisico=' + fisica;
      document.getElementById('cf-motivo-row').style.display = 'none';
    } else {
      var col = Math.abs(diff) > 2 ? '#7f1d1d' : '#78350f';
      var fc  = Math.abs(diff) > 2 ? '#fca5a5' : '#fbbf24';
      prev.style.background = col;
      prev.style.color = fc;
      prev.innerHTML = (diff>0?'&#9650; +':'&#9660; ') + diff + ' diferencia · esperado=' + CONTEO_DESGLOSE.esperado + ' · fisico=' + fisica;
      // motivo obligatorio si > |2|
      document.getElementById('cf-motivo-row').style.display = Math.abs(diff) > 2 ? 'block' : 'none';
    }
  };
  document.getElementById('modal-conteo-fisico').style.display = 'flex';
}

async function guardarConteoFisico() {
  var asigId = parseInt(document.getElementById('cf-asig-id').value, 10);
  var fisica = parseInt(document.getElementById('cf-cantidad').value, 10);
  if (isNaN(fisica) || fisica < 0) { showToast('Cantidad invalida', 'error'); return; }
  var motivo = document.getElementById('cf-motivo').value;
  var aplicar = document.getElementById('cf-aplicar').checked;
  try {
    var r = await fetch('/api/animus/inv-fisico/conteo/' + asigId + '/registrar',
                        _fetchOpts('POST', {cantidad_fisica: fisica, motivo_diferencia: motivo, aplicar_ajuste: aplicar}));
    var d = await r.json();
    if (d.ok) {
      var msg = d.diferencia === 0 ? 'Cuadra perfecto' : ('Diferencia ' + d.diferencia + (aplicar?' · ajustado':''));
      showToast(d.sku + ': ' + msg, d.diferencia === 0 ? 'success' : 'warning');
      cerrarModal('modal-conteo-fisico');
      cargarPendientesConteo();
      cargarInvFisico();
      cargarMovimientosInvFis();
    } else { showToast('Error: ' + (d.error||'?'), 'error'); }
  } catch(e) { showToast('Error red: ' + e.message, 'error'); }
}

// ════════════════════════════════════════════════════════════════
// DIAGNOSTICO Fase 3
// ════════════════════════════════════════════════════════════════
async function cargarDiagnostico() {
  try {
    var r = await fetch('/api/animus/inv-fisico/diagnostico');
    var d = await r.json();
    var card = document.getElementById('invfis-diag-card');
    var c = document.getElementById('invfis-diag-content');
    var k = d.kpis || {};
    var hay_dato = (k.total_conteos > 0) || (d.patrones_detectados||[]).length > 0 || (d.sin_baseline||[]).length > 0;
    if (!hay_dato) { card.style.display = 'none'; return; }
    card.style.display = 'block';
    var html = '';
    // KPIs en línea
    html += '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;font-size:13px;">';
    html += '<div style="background:#0f172a;padding:8px 14px;border-radius:6px;"><span style="color:#94a3b8;">Conteos 30d</span> <b style="color:#fff;margin-left:8px;">' + (k.total_conteos||0) + '</b></div>';
    html += '<div style="background:#0f172a;padding:8px 14px;border-radius:6px;"><span style="color:#94a3b8;">Con diferencia</span> <b style="color:#fbbf24;margin-left:8px;">' + (k.con_dif||0) + '</b></div>';
    html += '<div style="background:#0f172a;padding:8px 14px;border-radius:6px;"><span style="color:#94a3b8;">Faltantes</span> <b style="color:#f87171;margin-left:8px;">-' + (k.faltantes||0) + '</b></div>';
    html += '<div style="background:#0f172a;padding:8px 14px;border-radius:6px;"><span style="color:#94a3b8;">Sobrantes</span> <b style="color:#4ade80;margin-left:8px;">+' + (k.sobrantes||0) + '</b></div>';
    html += '</div>';
    // Patrones detectados
    if ((d.patrones_detectados||[]).length) {
      html += '<div style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Patrones detectados</div>';
      d.patrones_detectados.forEach(function(p) {
        var col = p.severidad === 'alta' ? '#7f1d1d' : '#78350f';
        var fc  = p.severidad === 'alta' ? '#fca5a5' : '#fbbf24';
        var icon = p.severidad === 'alta' ? '&#9888;' : '&#x1F50D;';
        html += '<div style="background:' + col + ';color:' + fc + ';padding:10px 14px;border-radius:6px;margin-bottom:6px;font-size:13px;">' +
                icon + ' ' + p.mensaje + '</div>';
      });
    } else {
      html += '<div style="background:#064e3b;color:#4ade80;padding:10px 14px;border-radius:6px;margin-bottom:12px;font-size:13px;">&#10003; Sin patrones de discrepancia detectados</div>';
    }
    // SKUs vendidos sin baseline
    if ((d.sin_baseline||[]).length) {
      html += '<div style="background:#1e1b4b;color:#a5b4fc;padding:10px 14px;border-radius:6px;margin-bottom:6px;font-size:13px;">';
      html += '&#9432; ' + d.sin_baseline.length + ' SKUs vendidos en Shopify (30d) SIN baseline registrado: ';
      html += '<b>' + d.sin_baseline.slice(0, 8).join(', ') + (d.sin_baseline.length > 8 ? ' y ' + (d.sin_baseline.length - 8) + ' mas' : '') + '</b>';
      html += '</div>';
    }
    // Top problemáticos
    if ((d.top_problematicos||[]).length) {
      html += '<div style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin:14px 0 6px 0;">Top SKUs problematicos (90d)</div>';
      html += '<table style="width:100%;font-size:13px;"><thead><tr style="color:#94a3b8;">';
      html += '<th style="text-align:left;padding:6px;">SKU</th>';
      html += '<th style="text-align:right;padding:6px;">Veces contado</th>';
      html += '<th style="text-align:right;padding:6px;">Con diferencia</th>';
      html += '<th style="text-align:right;padding:6px;">Suma diferencia</th>';
      html += '<th style="text-align:right;padding:6px;">Abs diff</th>';
      html += '</tr></thead><tbody>';
      d.top_problematicos.forEach(function(t) {
        var col = t.suma_dif < 0 ? '#f87171' : '#4ade80';
        html += '<tr style="border-top:1px solid #334155;">';
        html += '<td style="padding:6px;"><b>' + t.sku + '</b></td>';
        html += '<td style="text-align:right;padding:6px;">' + t.veces_contado + '</td>';
        html += '<td style="text-align:right;padding:6px;color:#fbbf24;">' + t.veces_con_dif + '/' + t.veces_contado + '</td>';
        html += '<td style="text-align:right;padding:6px;color:' + col + ';font-weight:700;">' + (t.suma_dif > 0 ? '+' : '') + t.suma_dif + '</td>';
        html += '<td style="text-align:right;padding:6px;">' + t.abs_dif + '</td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
    }
    c.innerHTML = html;
  } catch(e) { console.error(e); }
}

// Hook into loadTab para cargar pendientes al entrar al tab
var _origLoadTab_invfis = loadTab;
loadTab = function(name) {
  _origLoadTab_invfis(name);
  if (name === 'invfis') {
    cargarPendientesConteo();
    cargarDiagnostico();
  }
};

// Init
loadCaja();
</script>
</body>
</html>"""
