CONTABILIDAD_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contabilidad | HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0d0d0d;color:#e8e8e8;min-height:100vh}
.login-wrap{display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:40px;width:360px}
.login-box h2{text-align:center;margin-bottom:24px;font-size:20px;color:#fff}
.login-box input{width:100%;padding:10px 14px;margin-bottom:14px;background:#111;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px}
.login-box button{width:100%;padding:12px;background:#fff;color:#000;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}
.login-box button:hover{background:#e0e0e0}
.err{color:#ff6b6b;font-size:13px;text-align:center;margin-top:10px}
/* Layout */
.app{display:flex;flex-direction:column;min-height:100vh}
.topbar{background:#111;border-bottom:1px solid #2a2a2a;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:52px}
.topbar-left{display:flex;align-items:center;gap:16px}
.topbar-title{font-weight:700;font-size:15px;color:#fff}
.topbar-user{font-size:12px;color:#888}
.btn-logout{background:none;border:1px solid #444;color:#888;padding:4px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.btn-logout:hover{color:#fff;border-color:#666}
/* Tabs */
.tabs{display:flex;gap:2px;padding:0 24px;background:#111;border-bottom:1px solid #222;overflow-x:auto}
.tab{padding:12px 20px;cursor:pointer;font-size:13px;color:#888;border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap}
.tab:hover{color:#ccc}
.tab.active{color:#fff;border-bottom-color:#fff;font-weight:600}
.content{flex:1;padding:24px;overflow-y:auto}
.panel{display:none}.panel.active{display:block}
/* KPI Cards */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.kpi{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:18px}
.kpi-label{font-size:11px;color:#777;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.kpi-value{font-size:22px;font-weight:700;color:#fff}
.kpi-value.warn{color:#f59e0b}
.kpi-value.danger{color:#ef4444}
.kpi-value.ok{color:#22c55e}
/* Toolbar */
.toolbar{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.toolbar input,.toolbar select{background:#1a1a1a;border:1px solid #333;color:#e8e8e8;padding:8px 12px;border-radius:8px;font-size:13px}
.btn{padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .15s}
.btn-primary{background:#fff;color:#000}.btn-primary:hover{background:#e0e0e0}
.btn-secondary{background:#2a2a2a;color:#e8e8e8;border:1px solid #444}.btn-secondary:hover{background:#333}
.btn-success{background:#166534;color:#fff}.btn-success:hover{background:#14532d}
.btn-danger{background:#7f1d1d;color:#fff}.btn-danger:hover{background:#6b1919}
.btn-sm{padding:5px 10px;font-size:12px}
/* Table */
.tbl-wrap{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#111;padding:10px 14px;text-align:left;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.4px}
td{padding:10px 14px;border-top:1px solid #222}
tr:hover td{background:#202020}
/* Badge */
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge-green{background:#14532d;color:#86efac}
.badge-yellow{background:#78350f;color:#fde68a}
.badge-red{background:#7f1d1d;color:#fca5a5}
.badge-gray{background:#27272a;color:#a1a1aa}
/* Modal */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:28px;width:520px;max-height:80vh;overflow-y:auto}
.modal h3{font-size:16px;margin-bottom:18px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.form-group{display:flex;flex-direction:column;gap:4px;margin-bottom:12px}
.form-group label{font-size:12px;color:#888}
.form-group input,.form-group select,.form-group textarea{background:#111;border:1px solid #333;color:#e8e8e8;padding:8px 10px;border-radius:6px;font-size:13px;width:100%}
.form-group textarea{min-height:60px;resize:vertical}
.modal-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}
/* Items tabla en modal */
.items-table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px}
.items-table th{background:#111;padding:6px 8px;text-align:left;color:#888}
.items-table td{padding:6px 8px;border-top:1px solid #222}
.items-table input{width:100%;background:#0d0d0d;border:1px solid #333;color:#e8e8e8;padding:3px 6px;border-radius:4px}
.add-item-btn{font-size:12px;color:#666;cursor:pointer;background:none;border:1px dashed #444;padding:6px;border-radius:6px;width:100%;margin-top:4px}
.add-item-btn:hover{color:#ccc;border-color:#666}
/* Tesoreria / Nomina summary */
.summary-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.summary-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:16px}
.summary-card h4{font-size:12px;color:#777;text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}
.summary-card .big{font-size:20px;font-weight:700}
.toast{position:fixed;bottom:24px;right:24px;background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:14px 20px;font-size:13px;z-index:9999;transition:opacity .3s;opacity:0;pointer-events:none}
.toast.show{opacity:1}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-screen" class="login-wrap">
  <div class="login-box">
    <h2>Contabilidad</h2>
    <input id="l-user" type="text" placeholder="Usuario" autocomplete="username">
    <input id="l-pass" type="password" placeholder="Contrasena" autocomplete="current-password">
    <button onclick="doLogin()">Ingresar</button>
    <div id="l-err" class="err"></div>
  </div>
</div>

<!-- APP -->
<div id="app-screen" class="app" style="display:none">
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/></svg>
        Contabilidad
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; facturación · cartera · tesorería · nómina &middot; <span id="topbar-user" style="color:#a8a29e"></span></div>
    </div>
    <div class="cx-mod-header__nav">
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="doLogout()">Salir</button>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('facturacion',this)">Facturacion</div>
    <div class="tab" onclick="switchTab('cartera',this)">Cartera</div>
    <div class="tab" onclick="switchTab('tesoreria',this)">Tesoreria</div>
    <div class="tab" onclick="switchTab('nomina',this)">Nomina</div>
    <div class="tab" onclick="switchTab('siigo',this)">Exportar Siigo</div>
  </div>

  <div class="content">

    <!-- KPIs -->
    <div class="kpi-grid" id="kpi-grid">
      <div class="kpi"><div class="kpi-label">Facturado este mes</div><div class="kpi-value ok" id="k-mes">...</div></div>
      <div class="kpi"><div class="kpi-label">Cartera total</div><div class="kpi-value warn" id="k-cartera">...</div></div>
      <div class="kpi"><div class="kpi-label">Cartera vencida</div><div class="kpi-value danger" id="k-vencida">...</div></div>
      <div class="kpi"><div class="kpi-label">Facturas emitidas mes</div><div class="kpi-value" id="k-nfact">...</div></div>
    </div>

    <!-- TAB: Facturacion -->
    <div id="panel-facturacion" class="panel active">
      <div class="toolbar">
        <select id="f-empresa" onchange="loadFacturas()">
          <option value="">Todas las empresas</option>
          <option value="ANIMUS">ANIMUS Lab</option>
          <option value="Espagiria">Espagiria</option>
        </select>
        <select id="f-estado" onchange="loadFacturas()">
          <option value="">Todos los estados</option>
          <option value="Emitida">Emitida</option>
          <option value="Pagada">Pagada</option>
          <option value="Vencida">Vencida</option>
          <option value="Anulada">Anulada</option>
        </select>
        <input type="date" id="f-desde" onchange="loadFacturas()">
        <input type="date" id="f-hasta" onchange="loadFacturas()">
        <button class="btn btn-primary" onclick="openModalNueva()">+ Nueva factura</button>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Numero</th><th>Fecha</th><th>Cliente</th><th>Empresa</th>
            <th>Total</th><th>Pagado</th><th>Saldo</th><th>Estado</th><th>Acciones</th>
          </tr></thead>
          <tbody id="tbody-facturas"><tr><td colspan="9" style="text-align:center;color:#555;padding:24px">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- TAB: Cartera -->
    <div id="panel-cartera" class="panel">
      <div class="toolbar">
        <span style="color:#888;font-size:13px">Facturas pendientes de pago</span>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Numero</th><th>Fecha Emision</th><th>Vencimiento</th><th>Cliente</th>
            <th>Total</th><th>Saldo</th><th>Dias Vencido</th><th>Acciones</th>
          </tr></thead>
          <tbody id="tbody-cartera"><tr><td colspan="8" style="text-align:center;color:#555;padding:24px">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- TAB: Tesoreria -->
    <div id="panel-tesoreria" class="panel">
      <div class="toolbar">
        <input type="date" id="t-desde">
        <input type="date" id="t-hasta">
        <button class="btn btn-secondary" onclick="loadTesoreria()">Consultar</button>
      </div>
      <div class="summary-grid" id="tessum" style="display:none">
        <div class="summary-card"><h4>Total Ingresos</h4><div class="big ok" id="t-ing">$0</div></div>
        <div class="summary-card"><h4>Total Egresos</h4><div class="big danger" id="t-egr">$0</div></div>
        <div class="summary-card"><h4>Flujo Neto</h4><div class="big" id="t-neto">$0</div></div>
        <div class="summary-card"><h4>Movimientos</h4><div class="big" id="t-n">0</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div style="font-size:12px;color:#888;margin-bottom:8px;text-transform:uppercase">Ingresos</div>
          <div class="tbl-wrap"><table>
            <thead><tr><th>Fecha</th><th>Concepto</th><th>Monto</th></tr></thead>
            <tbody id="tbody-ingresos"></tbody>
          </table></div>
        </div>
        <div>
          <div style="font-size:12px;color:#888;margin-bottom:8px;text-transform:uppercase">Egresos</div>
          <div class="tbl-wrap"><table>
            <thead><tr><th>Fecha</th><th>Concepto</th><th>Monto</th><th>Comprobante</th></tr></thead>
            <tbody id="tbody-egresos"></tbody>
          </table></div>
        </div>
      </div>
    </div>

    <!-- TAB: Nomina -->
    <div id="panel-nomina" class="panel">
      <div class="toolbar">
        <select id="nom-periodo" onchange="loadNomina()">
          <option value="">Todos los periodos</option>
        </select>
      </div>
      <div class="summary-grid" id="nomsum" style="display:none">
        <div class="summary-card"><h4>Salario Bruto Total</h4><div class="big" id="n-bruto">$0</div></div>
        <div class="summary-card"><h4>Salario Neto Total</h4><div class="big ok" id="n-neto">$0</div></div>
        <div class="summary-card"><h4>Parafiscales</h4><div class="big warn" id="n-para">$0</div></div>
        <div class="summary-card"><h4>Empleados</h4><div class="big" id="n-emp">0</div></div>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Empleado</th><th>Cargo</th><th>Area</th><th>Periodo</th>
            <th>Salario Base</th><th>H.Extra</th><th>Neto</th><th>Estado</th>
          </tr></thead>
          <tbody id="tbody-nomina"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB: Siigo -->
    <div id="panel-siigo" class="panel">
      <div style="max-width:520px">
        <h3 style="margin-bottom:20px">Exportar a Siigo</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Desde</label>
            <input type="date" id="s-desde">
          </div>
          <div class="form-group">
            <label>Hasta</label>
            <input type="date" id="s-hasta">
          </div>
        </div>
        <div class="form-group">
          <label>Empresa</label>
          <select id="s-empresa">
            <option value="">Todas</option>
            <option value="ANIMUS">ANIMUS Lab</option>
            <option value="Espagiria">Espagiria</option>
          </select>
        </div>
        <div style="background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:16px;margin-bottom:20px;font-size:13px;color:#888">
          Genera un Excel con 3 hojas:<br>
          <strong style="color:#ccc">Libro de Ventas</strong> — una fila por factura<br>
          <strong style="color:#ccc">Detalle Items</strong> — una fila por producto<br>
          <strong style="color:#ccc">Pagos Recibidos</strong> — abonos registrados
        </div>
        <button class="btn btn-primary" style="width:100%;padding:14px" onclick="exportSiigo()">
          Descargar Excel para Siigo
        </button>
      </div>
    </div>

  </div><!-- /content -->
</div><!-- /app -->

<!-- MODAL: Nueva Factura -->
<div id="modal-nueva" class="modal-bg">
  <div class="modal">
    <h3>Nueva Factura</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Empresa</label>
        <select id="n-empresa">
          <option value="ANIMUS">ANIMUS Lab</option>
          <option value="Espagiria">Espagiria</option>
        </select>
      </div>
      <div class="form-group">
        <label>Pedido (opcional)</label>
        <input type="text" id="n-pedido" placeholder="Ej: PED-2026-001">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Cliente Nombre</label>
        <input type="text" id="n-cli-nombre" placeholder="Nombre o razon social">
      </div>
      <div class="form-group">
        <label>NIT</label>
        <input type="text" id="n-cli-nit" placeholder="000.000.000-0">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>IVA %</label>
        <select id="n-iva">
          <option value="0">Sin IVA (0%)</option>
          <option value="19">19%</option>
        </select>
      </div>
      <div class="form-group">
        <label>Fecha Vencimiento</label>
        <input type="date" id="n-venc">
      </div>
    </div>
    <div class="form-group">
      <label>Notas</label>
      <textarea id="n-notas" placeholder="Condiciones de pago, referencia, etc."></textarea>
    </div>
    <div style="font-size:12px;color:#888;margin-bottom:8px">
      Items (dejar vacio si el pedido ya los tiene)
    </div>
    <table class="items-table" id="items-table">
      <thead><tr><th>SKU</th><th>Descripcion</th><th>Cant</th><th>Precio Unit</th><th></th></tr></thead>
      <tbody id="items-body"></tbody>
    </table>
    <button class="add-item-btn" onclick="addItemRow()">+ Agregar item</button>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-nueva')">Cancelar</button>
      <button class="btn btn-primary" onclick="generarFactura()">Generar Factura</button>
    </div>
  </div>
</div>

<!-- MODAL: Registrar Pago -->
<div id="modal-pago" class="modal-bg">
  <div class="modal">
    <h3 id="pago-title">Registrar Pago</h3>
    <input type="hidden" id="pago-numero">
    <div class="form-group">
      <label>Monto (COP)</label>
      <input type="number" id="pago-monto" placeholder="0">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Medio de pago</label>
        <select id="pago-medio">
          <option value="Transferencia">Transferencia</option>
          <option value="Efectivo">Efectivo</option>
          <option value="Cheque">Cheque</option>
          <option value="PSE">PSE</option>
        </select>
      </div>
      <div class="form-group">
        <label>Referencia</label>
        <input type="text" id="pago-ref" placeholder="Num. comprobante">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-pago')">Cancelar</button>
      <button class="btn btn-success" onclick="registrarPago()">Registrar Pago</button>
    </div>
  </div>
</div>

<div id="toast" class="toast"></div>

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
const COP = n => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0}).format(n||0);
const fmt = s => s ? new Date(s+'T00:00:00').toLocaleDateString('es-CO') : '';

function toast(msg, ok=true){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.borderColor = ok ? '#22c55e' : '#ef4444';
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 3000);
}

async function doLogin(){
  const u = document.getElementById('l-user').value.trim().toLowerCase();
  const p = document.getElementById('l-pass').value;
  const r = await fetch('/api/contabilidad/login',_fetchOpts('POST', {usuario:u,password:p}));
  const d = await r.json();
  if(d.ok){
    document.getElementById('login-screen').style.display='none';
    document.getElementById('app-screen').style.display='flex';
    document.getElementById('topbar-user').textContent = d.usuario;
    initApp();
  } else {
    document.getElementById('l-err').textContent = d.error || 'Error';
  }
}
document.addEventListener('keydown',e=>{if(e.key==='Enter')doLogin()});

async function doLogout(){
  await fetch('/api/contabilidad/logout',_fetchOpts('POST'));
  location.reload();
}

async function checkSession(){
  const r = await fetch('/api/contabilidad/me');
  const d = await r.json();
  if(d.autenticado){
    document.getElementById('login-screen').style.display='none';
    document.getElementById('app-screen').style.display='flex';
    document.getElementById('topbar-user').textContent = d.usuario;
    initApp();
  } else {
    // Si ya tiene sesion del sistema pero no acceso, redirigir a modulos
    const me2 = await fetch('/api/contabilidad/me').then(x=>x.json());
    // Mostrar login screen (ya esta visible por default)
  }
}

function initApp(){
  loadKpis();
  loadFacturas();
  loadCartera();
  // Defaults fechas tesoreria
  const hoy = new Date().toISOString().split('T')[0];
  const hace30 = new Date(Date.now()-30*864e5).toISOString().split('T')[0];
  document.getElementById('t-desde').value = hace30;
  document.getElementById('t-hasta').value = hoy;
  // Defaults siigo
  const mes = new Date(); mes.setDate(1);
  document.getElementById('s-desde').value = mes.toISOString().split('T')[0];
  document.getElementById('s-hasta').value = hoy;
  loadNominaPeriodos();
}

function switchTab(name, el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='cartera') loadCartera();
  if(name==='tesoreria') loadTesoreria();
  if(name==='nomina') loadNomina();
}

async function loadKpis(){
  const d = await fetch('/api/contabilidad/kpis').then(r=>r.json());
  document.getElementById('k-mes').textContent = COP(d.facturado_mes);
  document.getElementById('k-cartera').textContent = COP(d.cartera_total);
  document.getElementById('k-vencida').textContent = COP(d.cartera_vencida);
  document.getElementById('k-nfact').textContent = d.facturas_mes;
}

function badgeEstado(e){
  const m={Emitida:'badge-yellow',Pagada:'badge-green',Anulada:'badge-gray',Vencida:'badge-red'};
  return `<span class="badge ${m[e]||'badge-gray'}">${e}</span>`;
}

async function loadFacturas(){
  const e=document.getElementById('f-empresa').value;
  const s=document.getElementById('f-estado').value;
  const d=document.getElementById('f-desde').value;
  const h=document.getElementById('f-hasta').value;
  let url=`/api/contabilidad/facturas?empresa=${e}&estado=${s}`;
  if(d) url+=`&desde=${d}`;
  if(h) url+=`&hasta=${h}`;
  const rows = await fetch(url).then(r=>r.json());
  const tb = document.getElementById('tbody-facturas');
  if(!rows.length){tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#555;padding:24px">Sin facturas</td></tr>';return;}
  tb.innerHTML = rows.map(f=>`
    <tr>
      <td><strong>${f.numero}</strong></td>
      <td>${fmt(f.fecha_emision)}</td>
      <td>${f.cliente_nombre||'—'}</td>
      <td>${f.empresa}</td>
      <td>${COP(f.total)}</td>
      <td>${COP(f.monto_pagado)}</td>
      <td>${COP(f.saldo)}</td>
      <td>${badgeEstado(f.estado)}</td>
      <td style="white-space:nowrap">
        <a href="/api/contabilidad/facturas/${f.numero}/pdf" target="_blank"><button class="btn btn-secondary btn-sm">PDF</button></a>
        ${f.estado==='Emitida'?`<button class="btn btn-success btn-sm" onclick="openPago('${f.numero}','${f.cliente_nombre}',${f.saldo})">Pago</button>`:''}
        ${f.estado==='Emitida'?`<button class="btn btn-danger btn-sm" onclick="anularFactura('${f.numero}')">Anular</button>`:''}
      </td>
    </tr>`).join('');
}

async function loadCartera(){
  const rows = await fetch('/api/contabilidad/facturas?estado=Emitida').then(r=>r.json());
  const hoy = new Date();
  const tb = document.getElementById('tbody-cartera');
  if(!rows.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#555;padding:24px">Sin cartera pendiente</td></tr>';return;}
  tb.innerHTML = rows.map(f=>{
    let diasV='';
    let vBadge='';
    if(f.fecha_vencimiento){
      const diff = Math.floor((hoy - new Date(f.fecha_vencimiento+'T00:00:00'))/864e5);
      if(diff>0){diasV=`<span style="color:#ef4444;font-weight:700">${diff}d</span>`;vBadge='badge-red';}
      else{diasV=`<span style="color:#22c55e">Al dia</span>`;vBadge='badge-green';}
    }
    return `<tr>
      <td><strong>${f.numero}</strong></td>
      <td>${fmt(f.fecha_emision)}</td>
      <td>${fmt(f.fecha_vencimiento)||'Sin fecha'}</td>
      <td>${f.cliente_nombre||'—'}</td>
      <td>${COP(f.total)}</td>
      <td>${COP(f.saldo)}</td>
      <td>${diasV}</td>
      <td>
        <a href="/api/contabilidad/facturas/${f.numero}/pdf" target="_blank"><button class="btn btn-secondary btn-sm">PDF</button></a>
        <button class="btn btn-success btn-sm" onclick="openPago('${f.numero}','${f.cliente_nombre}',${f.saldo})">Pago</button>
      </td>
    </tr>`;
  }).join('');
}

async function loadTesoreria(){
  const d=document.getElementById('t-desde').value;
  const h=document.getElementById('t-hasta').value;
  const data = await fetch(`/api/contabilidad/tesoreria?desde=${d}&hasta=${h}`).then(r=>r.json());
  document.getElementById('tessum').style.display='grid';
  document.getElementById('t-ing').textContent=COP(data.total_ingresos);
  document.getElementById('t-ing').className='big ok';
  document.getElementById('t-egr').textContent=COP(data.total_egresos);
  document.getElementById('t-neto').textContent=COP(data.flujo_neto);
  document.getElementById('t-neto').className='big '+(data.flujo_neto>=0?'ok':'danger');
  document.getElementById('t-n').textContent=(data.ingresos.length+data.egresos.length);
  const mkRowIng = (r,tipo) => `<tr><td>${fmt(r.fecha)}</td><td>${r.concepto||r.descripcion||tipo}</td><td>${COP(r.monto)}</td></tr>`;
  const mkRowEgr = (r) => {
    const ce = r.comprobante_numero_ce
      ? `<a href="/api/comprobantes-pago/${r.comprobante_id}/pdf" target="_blank"
            style="color:#1F5F5B;font-weight:600;text-decoration:none;font-size:12px;"
            title="Descargar PDF">📄 ${r.comprobante_numero_ce}</a>`
      : `<span style="color:#bbb;font-size:11px;">—</span>`;
    return `<tr>
      <td>${fmt(r.fecha)}</td>
      <td>${r.concepto||r.descripcion||'Egreso'}</td>
      <td>${COP(r.monto)}</td>
      <td>${ce}</td>
    </tr>`;
  };
  document.getElementById('tbody-ingresos').innerHTML = data.ingresos.map(r=>mkRowIng(r,'Ingreso')).join('')||'<tr><td colspan="3" style="color:#555;text-align:center">Sin datos</td></tr>';
  document.getElementById('tbody-egresos').innerHTML = data.egresos.map(mkRowEgr).join('')||'<tr><td colspan="4" style="color:#555;text-align:center">Sin datos</td></tr>';
}

async function loadNominaPeriodos(){
  const d = await fetch('/api/contabilidad/nomina').then(r=>r.json());
  const sel = document.getElementById('nom-periodo');
  const periodos = [...new Set(d.registros.map(r=>r.periodo))].sort().reverse();
  periodos.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;sel.appendChild(o);});
  if(periodos.length) sel.value=periodos[0];
  renderNomina(d);
}

async function loadNomina(){
  const p = document.getElementById('nom-periodo').value;
  const d = await fetch(`/api/contabilidad/nomina?periodo=${p}`).then(r=>r.json());
  renderNomina(d);
}

function renderNomina(d){
  const p = document.getElementById('nom-periodo').value;
  const rows = p ? d.registros.filter(r=>r.periodo===p) : d.registros;
  const tot = p ? d.totales[p] : null;
  if(tot){
    document.getElementById('nomsum').style.display='grid';
    document.getElementById('n-bruto').textContent=COP(tot.bruto);
    document.getElementById('n-neto').textContent=COP(tot.neto);
    document.getElementById('n-para').textContent=COP(tot.parafiscales);
    document.getElementById('n-emp').textContent=tot.empleados;
  }
  const tb = document.getElementById('tbody-nomina');
  tb.innerHTML = rows.length ? rows.map(r=>`
    <tr>
      <td>${r.nombre_completo||''}</td>
      <td style="color:#888">${r.cargo||''}</td>
      <td style="color:#888">${r.area||''}</td>
      <td>${r.periodo||''}</td>
      <td>${COP(r.salario_base)}</td>
      <td>${COP(r.valor_horas_extras||0)}</td>
      <td><strong>${COP(r.salario_neto)}</strong></td>
      <td><span class="badge ${r.estado==='Pagada'?'badge-green':'badge-yellow'}">${r.estado||'Generada'}</span></td>
    </tr>`).join('') : '<tr><td colspan="8" style="text-align:center;color:#555;padding:24px">Sin registros de nomina</td></tr>';
}

// ── Nueva Factura ────────────────────────────────────────────────────────────
function openModalNueva(){
  document.getElementById('items-body').innerHTML='';
  document.getElementById('n-pedido').value='';
  document.getElementById('n-cli-nombre').value='';
  document.getElementById('n-cli-nit').value='';
  document.getElementById('n-iva').value='0';
  document.getElementById('n-notas').value='';
  document.getElementById('n-venc').value='';
  document.getElementById('modal-nueva').classList.add('open');
}

function addItemRow(){
  const tr = document.createElement('tr');
  tr.innerHTML=`<td><input type="text" placeholder="SKU"></td>
    <td><input type="text" placeholder="Descripcion"></td>
    <td><input type="number" placeholder="0" style="width:60px"></td>
    <td><input type="number" placeholder="0"></td>
    <td><button onclick="this.closest('tr').remove()" style="background:none;border:none;color:#888;cursor:pointer;font-size:16px">x</button></td>`;
  document.getElementById('items-body').appendChild(tr);
}

async function generarFactura(){
  const items = [];
  document.querySelectorAll('#items-body tr').forEach(tr=>{
    const ins = tr.querySelectorAll('input');
    const sku=ins[0].value, desc=ins[1].value, cant=parseFloat(ins[2].value)||0, precio=parseFloat(ins[3].value)||0;
    if(desc||sku) items.push({sku,descripcion:desc,cantidad:cant,precio_unitario:precio,subtotal:cant*precio});
  });
  const body = {
    empresa: document.getElementById('n-empresa').value,
    numero_pedido: document.getElementById('n-pedido').value.trim(),
    iva_pct: parseFloat(document.getElementById('n-iva').value)||0,
    notas: document.getElementById('n-notas').value,
    fecha_vencimiento: document.getElementById('n-venc').value,
    items
  };
  const r = await fetch('/api/contabilidad/facturas/generar',_fetchOpts('POST', body));
  const d = await r.json();
  if(d.ok){
    closeModal('modal-nueva');
    toast(`Factura ${d.numero} generada — Total: ${COP(d.total)}`);
    loadFacturas(); loadKpis(); loadCartera();
  } else {
    toast(d.error||'Error al generar', false);
  }
}

// ── Pago ─────────────────────────────────────────────────────────────────────
function openPago(numero, cliente, saldo){
  document.getElementById('pago-numero').value=numero;
  document.getElementById('pago-title').textContent=`Registrar Pago — ${numero}`;
  document.getElementById('pago-monto').value=saldo;
  document.getElementById('pago-ref').value='';
  document.getElementById('modal-pago').classList.add('open');
}

async function registrarPago(){
  const numero = document.getElementById('pago-numero').value;
  const body = {
    monto: parseFloat(document.getElementById('pago-monto').value)||0,
    medio: document.getElementById('pago-medio').value,
    referencia: document.getElementById('pago-ref').value,
  };
  const r = await fetch(`/api/contabilidad/facturas/${numero}/pago`,_fetchOpts('POST', body));
  const d = await r.json();
  if(d.ok){
    closeModal('modal-pago');
    toast(`Pago registrado. Total pagado: ${COP(d.total_pagado)}`);
    loadFacturas(); loadKpis(); loadCartera();
  } else {
    toast(d.error||'Error', false);
  }
}

// ── Anular ────────────────────────────────────────────────────────────────────
async function anularFactura(numero){
  const motivo = prompt(`Motivo de anulacion de ${numero}:`);
  if(!motivo) return;
  const r = await fetch(`/api/contabilidad/facturas/${numero}/anular`,_fetchOpts('PATCH', {motivo}));
  const d = await r.json();
  if(d.ok){toast('Factura anulada'); loadFacturas(); loadKpis();}
  else toast(d.error||'Error', false);
}

// ── Export Siigo ──────────────────────────────────────────────────────────────
function exportSiigo(){
  const d=document.getElementById('s-desde').value;
  const h=document.getElementById('s-hasta').value;
  const e=document.getElementById('s-empresa').value;
  if(!d||!h){toast('Selecciona rango de fechas', false); return;}
  window.open(`/api/contabilidad/export/siigo?desde=${d}&hasta=${h}&empresa=${e}`, '_blank');
}

function closeModal(id){ document.getElementById(id).classList.remove('open'); }

checkSession();
</script>
</body>
</html>"""
