"""Tesoreria - fusion UI de Finanzas + Contabilidad.

Una sola URL /tesoreria con tabs que consumen los endpoints existentes
de /api/financiero/* y /api/contabilidad/*. Los blueprints viejos siguen
funcionando (no se elimina codigo). Esta es solo capa UI unificada.
"""

HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tesorería - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--cx-bg-alt); color:var(--cx-text); }
  .header { background:linear-gradient(135deg,#0f3a1f 0%,#15803d 100%); color:#fff; padding:18px 28px; display:flex; align-items:center; justify-content:space-between; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; }
  .header a { color:#bbf7d0; font-size:0.85em; text-decoration:none; }
  .container { max-width:1500px; margin:0 auto; padding:18px; }
  .tabs { display:flex; gap:4px; margin-bottom:18px; border-bottom:2px solid var(--cx-border); padding-bottom:0; flex-wrap:wrap; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .tab { padding:10px 16px; background:transparent; border:none; cursor:pointer; font-size:13px; color:var(--cx-text-soft); font-weight:600; white-space:nowrap; border-bottom:3px solid transparent; }
  .tab:hover { color:var(--cx-success-text); }
  .tab.active { color:var(--cx-success-text); border-bottom-color:var(--cx-success); }
  .grid { display:grid; gap:14px; }
  .grid-4 { grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
  .grid-2 { grid-template-columns:1fr 1fr; }
  .card { background:var(--cx-card); border:1px solid var(--cx-border); border-radius:10px; padding:16px; }
  .card h3 { margin:0 0 8px; font-size:0.78em; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:0.06em; }
  .card .val { font-size:1.6em; font-weight:800; color:var(--cx-text); line-height:1; }
  .card .sub { font-size:0.78em; color:var(--cx-text-faint); margin-top:4px; }
  .panel { background:var(--cx-card); border:1px solid var(--cx-border); border-radius:10px; padding:18px; margin-bottom:14px; }
  .panel h3 { margin:0 0 12px; font-size:0.95em; color:var(--cx-text); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:var(--cx-bg-alt); color:var(--cx-text-mute); font-weight:600; text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.04em; }
  td { padding:8px 12px; border-bottom:1px solid var(--cx-bg-alt); }
  tr:hover td { background:var(--cx-bg-alt); }
  .badge { padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700; display:inline-block; }
  .b-ok { background:var(--cx-success-pale); color:var(--cx-success-text); }
  .b-warn { background:var(--cx-warn-pale); color:var(--cx-warn-text); }
  .b-err { background:var(--cx-danger-pale); color:var(--cx-danger-text); }
  .empty { color:var(--cx-text-faint); font-style:italic; padding:32px; text-align:center; }
  .btn { padding:8px 14px; border:none; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; }
  .btn-primary { background:var(--cx-success); color:#fff; }
  .btn-secondary { background:var(--cx-bg-alt); color:var(--cx-text-soft); border:1px solid var(--cx-border); }
  .hidden { display:none; }
  .pos { color:var(--cx-success-text); font-weight:700; }
  .neg { color:var(--cx-danger-text); font-weight:700; }
  @media (max-width:768px) {
    .header { padding:14px 16px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.1em; }
    .container { padding:10px; }
    .grid-4 { grid-template-columns:1fr 1fr; }
    .grid-2 { grid-template-columns:1fr; }
    .tab { padding:8px 12px; font-size:12px; }
    table thead { display:none; }
    table, table tbody, table tr, table td { display:block; width:100%; }
    table tr { background:var(--cx-card); border:1px solid var(--cx-border); border-radius:8px; padding:10px; margin-bottom:8px; }
    table td { padding:4px 0; border-bottom:none; font-size:12px; }
    table td:first-child { font-weight:700; padding-bottom:6px; }
  }
</style>
</head>
<body>
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#15803d" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/></svg>
        Tesorería
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Caja · P&amp;L · Cartera · Pagos · Facturación · Nómina · SIIGO</div>
    </div>
    <div class="cx-mod-header__nav">
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">Módulos</a>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

  <div class="container">
    <div class="tabs" id="tabs">
      <button class="tab active" data-tab="caja" onclick="switchTab('caja')">📊 Caja & KPIs</button>
      <button class="tab" data-tab="cajamenor" onclick="switchTab('cajamenor')">💵 Caja menor</button>
      <button class="tab" data-tab="pnl" onclick="switchTab('pnl')">📈 P&L · Margen</button>
      <button class="tab" data-tab="cartera" onclick="switchTab('cartera')">📥 Cartera (AR)</button>
      <button class="tab" data-tab="pagar" onclick="switchTab('pagar')">📤 Por Pagar (AP)</button>
      <button class="tab" data-tab="ocs" onclick="switchTab('ocs')">📚 Archivo OCs</button>
      <button class="tab" data-tab="facturacion" onclick="switchTab('facturacion')">📄 Facturación</button>
      <button class="tab" data-tab="nomina" onclick="switchTab('nomina')">👥 Nómina</button>
      <button class="tab" data-tab="config" onclick="switchTab('config')">⚙️ Configuración</button>
    </div>

    <!-- TAB: CAJA & KPIs -->
    <div id="tab-caja" class="tabpanel">
      <div class="grid grid-4" style="margin-bottom:18px">
        <div class="card"><h3>Ingresos mes</h3><div class="val" id="kpi-ing-mes">-</div><div class="sub" id="kpi-ing-shopify"></div></div>
        <div class="card"><h3>Egresos mes</h3><div class="val" id="kpi-egr-mes" style="color:var(--cx-danger-text)">-</div><div class="sub">OCs+nómina+otros</div></div>
        <div class="card"><h3>Neto mes</h3><div class="val" id="kpi-neto"></div><div class="sub" id="kpi-neto-sub"></div></div>
        <div class="card"><h3>Saldo caja (empresa)</h3><div class="val" id="kpi-saldo"></div><div class="sub" id="kpi-saldo-sub"></div></div>
        <div class="card"><h3>Caja menor</h3><div class="val" id="kpi-caja-menor"></div><div class="sub" id="kpi-caja-menor-sub">efectivo en la gaveta</div></div>
      </div>
      <div class="grid grid-2">
        <div class="panel">
          <h3>Sync Shopify → Ingresos</h3>
          <div id="shopify-status" style="font-size:13px;color:var(--cx-text-soft)">Cargando...</div>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-secondary" onclick="syncDryRun()">👁️ Previsualizar</button>
            <button class="btn btn-primary" onclick="syncEjecutar()">✨ Sincronizar ahora</button>
          </div>
          <div id="shopify-msg" style="margin-top:10px;font-size:12px"></div>
        </div>
        <div class="panel">
          <h3>Importar OCs recibidas → egresos</h3>
          <p style="font-size:12px;color:var(--cx-text-mute);margin:0 0 10px">Trae a flujo_egresos las OCs marcadas Recibida que aún no se importaron.</p>
          <button class="btn btn-secondary" onclick="importarOCs()">📦 Importar OCs</button>
          <div id="import-msg" style="margin-top:10px;font-size:12px"></div>
        </div>
      </div>
    </div>

    <!-- TAB: CAJA MENOR · lo que la contadora revisa -->
    <div id="tab-cajamenor" class="tabpanel hidden">
      <div class="panel" style="margin-bottom:16px">
        <div style="display:flex;gap:10px;align-items:end;flex-wrap:wrap">
          <div><label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Desde</label>
            <input type="date" id="cm-desde" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;background:var(--cx-card);color:var(--cx-text)"></div>
          <div><label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Hasta</label>
            <input type="date" id="cm-hasta" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;background:var(--cx-card);color:var(--cx-text)"></div>
          <div><label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Empresa</label>
            <select id="cm-empresa" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;background:var(--cx-card);color:var(--cx-text)">
              <option value="">Todas</option><option value="ANIMUS">ÁNIMUS</option><option value="ESPAGIRIA">Espagiria</option>
            </select></div>
          <button class="btn btn-primary" onclick="cargarCajaMenor()">Ver</button>
          <button class="btn btn-secondary" onclick="cmExportar()">⬇ Descargar CSV</button>
        </div>
      </div>

      <div class="grid grid-4" style="margin-bottom:16px">
        <div class="card"><h3>Hay en la gaveta</h3><div class="val" id="cm-saldo">-</div><div class="sub">saldo actual · efectivo</div></div>
        <div class="card"><h3>Entró a la gaveta</h3><div class="val pos" id="cm-gaveta">-</div><div class="sub">en el rango</div></div>
        <div class="card"><h3>Entró al banco</h3><div class="val" id="cm-banco">-</div><div class="sub">no está en la gaveta</div></div>
        <div class="card"><h3>Salió</h3><div class="val neg" id="cm-egr">-</div><div class="sub" id="cm-sinresp"></div></div>
      </div>

      <div class="panel" style="margin-bottom:16px">
        <h3>Con qué ingresó</h3>
        <div id="cm-origenes" class="empty">Cargando...</div>
      </div>

      <div class="panel">
        <h3>Movimiento por movimiento</h3>
        <div id="cm-tabla" class="empty">Cargando...</div>
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

    <!-- TAB: ARCHIVO OCs (histórico completo · gasto por categoría/mes · Sebastián 21-jul) -->
    <div id="tab-ocs" class="tabpanel hidden">
      <div class="grid grid-4" style="margin-bottom:18px">
        <div class="card"><h3>Total pedido (histórico)</h3><div class="val" id="oc-kpi-total">-</div><div class="sub">todas las OCs, cualquier estado</div></div>
        <div class="card"><h3>Órdenes</h3><div class="val" id="oc-kpi-count">-</div><div class="sub" id="oc-kpi-count-sub">registradas</div></div>
        <div class="card"><h3>Pedido <span id="oc-kpi-anio-lbl"></span></h3><div class="val" id="oc-kpi-anio">-</div><div class="sub">año en curso</div></div>
        <div class="card"><h3>Ticket promedio</h3><div class="val" id="oc-kpi-avg">-</div><div class="sub">por OC</div></div>
      </div>
      <div class="grid grid-2">
        <div class="panel">
          <h3>Gasto por categoría</h3>
          <div id="oc-por-cat" class="empty">Cargando…</div>
        </div>
        <div class="panel">
          <h3>Gasto por mes</h3>
          <div id="oc-por-mes" class="empty">Cargando…</div>
        </div>
      </div>
      <div class="panel">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
          <h3 style="margin:0">Todas las órdenes de compra</h3>
          <input type="text" id="oc-q" placeholder="Buscar OC, proveedor, categoría…" oninput="renderArchivoOCs()" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px;min-width:220px">
          <select id="oc-estado" onchange="renderArchivoOCs()" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px">
            <option value="">Todos los estados</option>
            <option value="Borrador">Borrador</option><option value="Revisada">Revisada</option>
            <option value="Autorizada">Autorizada</option><option value="Recibida">Recibida</option>
            <option value="Parcial">Parcial</option><option value="Pagada">Pagada</option>
          </select>
          <button class="btn btn-secondary" onclick="cargarArchivoOCs()" style="font-size:12px">↻ Actualizar</button>
        </div>
        <div style="overflow-x:auto"><div id="oc-tabla" class="empty">Cargando órdenes…</div></div>
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

    <!-- TAB: NÓMINA (movido desde /rrhh el 29-abr-2026 - Sebastian) -->
    <div id="tab-nomina" class="tabpanel hidden">
      <div class="panel">
        <h3>👥 Nómina · Cálculo y aprobación quincenal</h3>
        <div class="ctrl-bar" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
          <select id="nom-mes" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px">
            <option value="01">Enero</option><option value="02">Febrero</option>
            <option value="03">Marzo</option><option value="04">Abril</option>
            <option value="05">Mayo</option><option value="06">Junio</option>
            <option value="07">Julio</option><option value="08">Agosto</option>
            <option value="09">Septiembre</option><option value="10">Octubre</option>
            <option value="11">Noviembre</option><option value="12">Diciembre</option>
          </select>
          <select id="nom-anio" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px"><option>2026</option><option>2025</option></select>
          <select id="nom-quinc" style="padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px;font-weight:600">
            <option value="Q1">1ª Quincena (1‑15)</option>
            <option value="Q2">2ª Quincena (16‑fin)</option>
          </select>
          <button class="btn btn-primary" onclick="loadNomina()">Calcular</button>
          <label class="btn" style="background:var(--cx-primary);color:#fff;cursor:pointer" title="Importar Excel de nómina">📂 Importar Excel<input type="file" accept=".xlsx" style="display:none" onchange="importarExcelNomina(this)"></label>
          <button class="btn btn-primary" onclick="guardarNomina()" style="margin-left:auto">💾 Guardar</button>
          <button class="btn" id="nom-btn-aprobar" style="display:none;background:var(--cx-success);color:#fff" onclick="aprobarNomina()">✓ Aprobar</button>
          <button class="btn" id="nom-btn-pagar" style="display:none;background:var(--cx-success);color:#fff" onclick="pagarNomina()">💸 Marcar Pagada</button>
          <button class="btn" onclick="exportarNominaExcel()" style="background:#0284c7;color:#fff" title="Descargar Excel">⬇️ Excel</button>
          <span id="nom-estado-badge"></span>
        </div>
        <div style="overflow-x:auto">
          <table id="nom-table" style="font-size:12px">
            <thead><tr>
              <th>Empleado</th><th>Empresa</th><th>Días</th>
              <th>Salario Base</th><th>Aux. Transp.</th><th>H. Extras</th><th>Bonos</th>
              <th>‑Salud (4%)</th><th>‑Pensión (4%)</th><th>NETO</th><th>Banco / Cuenta</th><th></th>
            </tr></thead>
            <tbody id="nom-body"><tr><td colspan="12" class="empty">Click "Calcular" para cargar el periodo seleccionado.</td></tr></tbody>
          </table>
        </div>
        <div id="nom-summary" style="display:none;margin-top:14px;padding:14px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:10px;display:none;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px"></div>
        <div class="panel" id="nom-aportes" style="display:none;margin-top:14px">
          <h3>🏛 Aportes Empleador (no deducidos del empleado)</h3>
          <div id="nom-aportes-body"></div>
        </div>
      </div>
    </div>

    <!-- TAB: CONFIG -->
    <div id="tab-config" class="tabpanel hidden">
      <div class="panel">
        <h3>Información</h3>
        <p style="font-size:13px;color:var(--cx-text-soft);line-height:1.6">
          Tesorería unifica los dashboards de <strong>Finanzas</strong> (caja, P&amp;L, cartera, pagos)
          y <strong>Contabilidad</strong> (facturas, SIIGO, nómina).
          Las URLs viejas <code>/financiero</code> y <code>/contabilidad</code> siguen funcionando
          como atajos directos.
        </p>
        <p style="font-size:12px;color:var(--cx-text-mute);margin-top:14px">
          <strong>Acceso rápido:</strong>
          <a href="/financiero" style="color:var(--cx-success-text)">Ir a Financiero (vista clásica)</a> ·
          <a href="/contabilidad" style="color:var(--cx-success-text)">Ir a Contabilidad (vista clásica)</a>
        </p>
      </div>
    </div>
  </div>

<script>
function fmtM(n){n=parseFloat(n||0); if(n>=1e6) return '$'+(n/1e6).toFixed(1)+'M'; if(n>=1e3) return '$'+(n/1e3).toFixed(0)+'K'; return '$'+Math.round(n).toLocaleString('es-CO');}
function fmtN(n){return (n||0).toLocaleString('es-CO');}
function _esc(s){return String(s||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));}

const TABS = ['caja','cajamenor','pnl','cartera','pagar','ocs','facturacion','nomina','config'];

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
  else if (t === 'cajamenor') cargarCajaMenor();
  else if (t === 'pnl') cargarPnL();
  else if (t === 'cartera') cargarCartera();
  else if (t === 'pagar') cargarPagar();
  else if (t === 'ocs') cargarArchivoOCs();
  else if (t === 'facturacion') cargarFacturacion();
  else if (t === 'nomina') cargarNomina();
}

async function cargarCaja() {
  try {
    const k = await fetch('/api/financiero/kpis').then(r=>r.json());
    // El endpoint devuelve `ing_mes`/`egr_mes` (financiero.py) · leer `ingresos_mes` daba
    // undefined -> fmtM lo pinta "$0" y el neto salia SIEMPRE en superavit de $0. Un cero que
    // nadie calculo se lee como "no hubo movimiento" y significa lo contrario (M5/M98).
    document.getElementById('kpi-ing-mes').textContent = fmtM(k.ing_mes);
    document.getElementById('kpi-egr-mes').textContent = fmtM(k.egr_mes);
    const neto = (k.ing_mes||0) - (k.egr_mes||0);
    const eN = document.getElementById('kpi-neto');
    eN.textContent = (neto>=0?'+':'')+fmtM(Math.abs(neto));
    eN.className = 'val ' + (neto>=0?'pos':'neg');
    document.getElementById('kpi-neto-sub').textContent = neto>=0?'superávit':'déficit';
    document.getElementById('kpi-saldo').textContent = fmtM(k.saldo_caja||0);
    document.getElementById('kpi-saldo').className = 'val ' + ((k.saldo_caja||0)>=0?'pos':'neg');
    // De CUÁNDO es. Lo teclea gerencia una vez al mes, y se mostraba pelado al lado de tres
    // números calculados en vivo: un dato de hace seis semanas se leía igual de fresco que el
    // ingreso de hoy (M109/M124).
    var _ss = document.getElementById('kpi-saldo-sub');
    if (!k.saldo_caja_periodo) {
      _ss.textContent = 'nadie lo ha cargado todavía';
      _ss.style.color = 'var(--cx-warn-text)';
    } else if (k.saldo_caja_vigente) {
      _ss.textContent = 'cargado por gerencia · ' + k.saldo_caja_periodo;
      _ss.style.color = 'var(--cx-text-mute)';
    } else {
      _ss.textContent = 'DESACTUALIZADO · último dato ' + k.saldo_caja_periodo;
      _ss.style.color = 'var(--cx-danger-text)';
    }
    // La caja menor SÍ es verificable: sale del helper canónico, el mismo contra el que se
    // autorizan los pagos y contra el que se arquea (M1/M148).
    var _cm = document.getElementById('kpi-caja-menor');
    if (k.caja_menor_ok) {
      _cm.textContent = fmtM(k.caja_menor||0);
      _cm.className = 'val ' + ((k.caja_menor||0)>=0?'pos':'neg');
      document.getElementById('kpi-caja-menor-sub').textContent = 'efectivo en la gaveta · contado en el arqueo';
    } else {
      // Un cero que nadie calculó se lee como "no hay plata" y significa lo contrario (M100).
      _cm.textContent = 'sin dato';
      _cm.className = 'val';
      document.getElementById('kpi-caja-menor-sub').textContent = 'no se pudo leer';
    }
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
  // el endpoint devuelve `total_importado` · leer `total_a_importar` decia siempre "por $0"
  msg.textContent = 'Importaría '+d.pendientes+' pedidos por '+fmtM(d.total_importado);
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

// -- CAJA MENOR - la pantalla que la contadora revisa ------------------------------------
// El endpoint (`/api/caja/libro`) ya trae `origen`, `subtipo` y `comprobante_url`: eran cuatro
// columnas que se escribian desde la mig 409 y NUNCA salian por la API, asi que "con que
// ingreso cada peso" estaba en la base sin forma de verlo (M115). Aca se pintan.
var _CM = null;

function cmEsc(v){
  return String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function cmPesos(n){ return '$' + Math.round(parseFloat(n||0)).toLocaleString('es-CO'); }
function cmFechaLocal(d){
  // OJO: `toISOString()` es UTC - despues de las 19:00 en Colombia ya devuelve el dia
  // SIGUIENTE y el rango arrancaria un dia corrido (M106). Se arma con componentes locales.
  var m = String(d.getMonth()+1).padStart(2,'0'), dd = String(d.getDate()).padStart(2,'0');
  return d.getFullYear() + '-' + m + '-' + dd;
}

async function cargarCajaMenor(){
  var hoy = new Date();
  var iDesde = document.getElementById('cm-desde'), iHasta = document.getElementById('cm-hasta');
  if (!iDesde.value) iDesde.value = cmFechaLocal(new Date(hoy.getFullYear(), hoy.getMonth(), 1));
  if (!iHasta.value) iHasta.value = cmFechaLocal(hoy);
  var q = 'desde=' + encodeURIComponent(iDesde.value) + '&hasta=' + encodeURIComponent(iHasta.value);
  var emp = document.getElementById('cm-empresa').value;
  if (emp) q += '&empresa=' + encodeURIComponent(emp);
  document.getElementById('cm-tabla').innerHTML = '<div class="empty">Cargando...</div>';
  try {
    var r = await fetch('/api/caja/libro?' + q, {credentials:'same-origin'});
    var d = await r.json();
    if (!d.ok) throw new Error(d.error || 'no se pudo leer el libro de caja');
    _CM = d;
    document.getElementById('cm-saldo').textContent  = cmPesos(d.saldo_actual);
    document.getElementById('cm-gaveta').textContent = cmPesos(d.ingresos_a_gaveta);
    document.getElementById('cm-banco').textContent  = cmPesos(d.ingresos_al_banco);
    document.getElementById('cm-egr').textContent    = cmPesos(d.egresos);
    // Un egreso sin soporte es lo primero que una contadora busca. Si son cero se DICE:
    // un hueco en blanco no se distingue de "no se calculo" (M154).
    var sr = d.egresos_sin_respaldo || 0;
    var elSr = document.getElementById('cm-sinresp');
    elSr.textContent = sr ? (sr + ' sin soporte') : 'todos con soporte';
    elSr.style.color = sr ? 'var(--cx-danger-text)' : 'var(--cx-text-mute)';
    cmPintarOrigenes(d);
    cmPintarTabla(d);
  } catch (e) {
    document.getElementById('cm-tabla').innerHTML =
      '<div class="empty">No se pudo cargar: ' + cmEsc(e.message) + '</div>';
    document.getElementById('cm-origenes').innerHTML = '<div class="empty">-</div>';
  }
}

function cmPintarOrigenes(d){
  var el = document.getElementById('cm-origenes');
  var ors = d.por_origen || [];
  if (!ors.length) { el.innerHTML = '<div class="empty">No entro plata en este rango</div>'; return; }
  var h = '<div style="overflow-x:auto"><table><thead><tr><th>Origen</th>' +
          '<th style="text-align:right">Movs</th><th style="text-align:right">Total</th>' +
          '<th style="text-align:right">A la gaveta</th><th style="text-align:right">Al banco</th>' +
          '</tr></thead><tbody>';
  ors.forEach(function(o){
    var banco = (o.total || 0) - (o.a_gaveta || 0);
    h += '<tr><td><b>' + cmEsc(o.origen) + '</b></td>' +
         '<td style="text-align:right">' + fmtN(o.n) + '</td>' +
         '<td style="text-align:right;font-variant-numeric:tabular-nums">' + cmPesos(o.total) + '</td>' +
         '<td style="text-align:right;font-variant-numeric:tabular-nums" class="pos">' + cmPesos(o.a_gaveta) + '</td>' +
         '<td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--cx-text-mute)">' + cmPesos(banco) + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table></div>';
}

function cmPintarTabla(d){
  var el = document.getElementById('cm-tabla');
  var ms = d.movimientos || [];
  if (!ms.length) { el.innerHTML = '<div class="empty">Sin movimientos en este rango</div>'; return; }
  var h = '<div style="overflow-x:auto"><table><thead><tr>' +
          '<th>Recibo</th><th>Fecha</th><th>Concepto</th><th>Con que</th><th>Metodo</th>' +
          '<th>Quien</th><th>Soporte</th><th style="text-align:right">Monto</th>' +
          '</tr></thead><tbody>';
  ms.forEach(function(m){
    var anul = m.anulado;
    var estilo = anul ? ' style="opacity:.55;text-decoration:line-through"' : '';
    var signo = (m.tipo === 'ingreso') ? '' : '-';
    var clase = anul ? '' : (m.tipo === 'ingreso' ? 'pos' : 'neg');
    // Lo que NO cuenta al saldo se dice fila por fila: si no, ella tendria que descubrirlo
    // restando, y ahi es donde el arqueo deja de cuadrar sin que nadie entienda por que (M124).
    var chip = '';
    if (anul) chip = '<span class="badge b-err">anulado</span>';
    else if (m.tipo === 'ingreso') chip = m.cuenta_en_saldo
      ? '<span class="badge b-ok">gaveta</span>' : '<span class="badge b-warn">al banco</span>';
    var soporte = m.comprobante_url
      ? '<a href="' + cmEsc(m.comprobante_url) + '" target="_blank" rel="noopener">ver</a>'
      : (m.tipo === 'ingreso' ? '<span style="color:var(--cx-text-faint)">-</span>'
                              : '<span class="badge b-warn">falta</span>');
    var motivo = m.anulado_motivo
      ? '<div style="font-size:11px;color:var(--cx-danger-text)">' + cmEsc(m.anulado_motivo) + '</div>' : '';
    var sub = m.subtipo
      ? '<span style="color:var(--cx-text-faint)"> - ' + cmEsc(m.subtipo) + '</span>' : '';
    h += '<tr' + estilo + '><td style="font-family:monospace;font-size:11px">' + cmEsc(m.recibo || '-') + '</td>' +
         '<td>' + cmEsc(String(m.fecha || '').slice(0,10)) + '</td>' +
         '<td>' + cmEsc(m.concepto) + motivo + '</td>' +
         '<td>' + cmEsc(m.origen) + sub + ' ' + chip + '</td>' +
         '<td>' + cmEsc(m.metodo || '-') + '</td>' +
         '<td style="font-size:12px">' + cmEsc(m.registrado_por || '-') + '</td>' +
         '<td>' + soporte + '</td>' +
         '<td style="text-align:right;font-variant-numeric:tabular-nums" class="' + clase + '">' +
           signo + cmPesos(m.monto) + '</td></tr>';
  });
  h += '</tbody></table></div>';
  h += '<div style="margin-top:10px;font-size:12px;color:var(--cx-text-mute)">' +
       fmtN(ms.length) + ' movimientos' +
       (d.cerrada_hasta ? ' - caja cerrada hasta ' + cmEsc(d.cerrada_hasta) : '') + '</div>';
  el.innerHTML = h;
}

function cmExportar(){
  if (!_CM || !(_CM.movimientos || []).length) { alert('Primero cargá un rango con movimientos.'); return; }
  var cab = ['recibo','fecha','tipo','concepto','origen','subtipo','metodo','empresa',
             'registrado_por','comprobante_url','anulado','cuenta_en_saldo','monto'];
  var filas = [cab.join(';')];
  _CM.movimientos.forEach(function(m){
    filas.push(cab.map(function(c){
      var v = m[c];
      if (v === true) v = 'si'; else if (v === false) v = 'no';
      return String(v == null ? '' : v).split(';').join(',').split('\n').join(' ').split('\r').join('');
    }).join(';'));
  });
  var blob = new Blob([String.fromCharCode(0xFEFF) + filas.join('\r\n')],
                      {type:'text/csv;charset=utf-8;'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'caja-menor-' + (_CM.desde || '') + '_' + (_CM.hasta || '') + '.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

async function cargarPnL() {
  try {
    const p = await fetch('/api/financiero/pnl').then(r=>r.json());
    let html = '<table><thead><tr><th>Empresa</th><th>Ingresos</th><th>Egresos</th><th>EBITDA</th><th>Margen %</th></tr></thead><tbody>';
    // `empresas` viene como OBJETO {ANIMUS:{...}, ESPAGIRIA:{...}, TOTAL:{...}} · hacerle
    // .forEach lanzaba TypeError y el catch pintaba "Error cargando P&L" SIEMPRE.
    const _emp = p.empresas || {};
    Object.keys(_emp).forEach(_k => {
      const e = Object.assign({empresa:_k}, _emp[_k] || {});
      const margen = e.ingresos > 0 ? ((e.ebitda/e.ingresos)*100).toFixed(1)+'%' : '-';
      html += '<tr'+(_k==='TOTAL'?' style="font-weight:800;border-top:2px solid var(--cx-border)"':'')+'>'
            + '<td><strong>'+_esc(e.empresa)+'</strong></td>' +
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

// Los aging devuelven `buckets.{corriente,dias_30,dias_60,dias_90}.total` · leer llaves
// planas (`ar.corriente`) daba undefined y pintaba TODA la cartera en $0 (M5/M98).
function _bk(d, k){ return ((((d||{}).buckets)||{})[k]||{}).total || 0; }

async function cargarCartera() {
  try {
    const ar = await fetch('/api/financiero/ar-aging').then(r=>r.json());
    let html = '<div class="grid grid-4" style="margin-bottom:14px">' +
      // El endpoint devuelve `ar_total` y `buckets.{corriente,dias_30,dias_60,dias_90}.total`
      // (financiero.py) · las 6 llaves que se leian aca no existian: la cartera entera en $0.
      '<div class="card"><h3>Total por cobrar</h3><div class="val">'+fmtM(ar.ar_total||0)+'</div></div>' +
      '<div class="card"><h3>Corriente</h3><div class="val pos">'+fmtM(_bk(ar,'corriente'))+'</div></div>' +
      '<div class="card"><h3>Vencido 30d</h3><div class="val" style="color:var(--cx-warn-text)">'+fmtM(_bk(ar,'dias_30'))+'</div></div>' +
      '<div class="card"><h3>Vencido 60+d</h3><div class="val neg">'+fmtM(_bk(ar,'dias_60')+_bk(ar,'dias_90'))+'</div></div>' +
      '</div>';
    if (ar.pedidos && ar.pedidos.length) {
      html += '<table><thead><tr><th>Cliente</th><th>Pedido</th><th>Monto</th><th>Días</th></tr></thead><tbody>';
      ar.pedidos.slice(0,20).forEach(p => {
        html += '<tr><td>'+_esc(p.cliente)+'</td><td>'+_esc(p.numero_pedido)+'</td><td>'+fmtM(p.valor_total)+'</td><td>'+(p.dias||0)+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    document.getElementById('ar-content').innerHTML = html;
  } catch(e) { document.getElementById('ar-content').innerHTML = '<div class="empty">Error</div>'; }

  try {
    const f = await fetch('/api/contabilidad/facturas').then(r=>r.json());
    // `/api/contabilidad/facturas` devuelve un ARRAY (contabilidad.py) · leer `f.facturas`
    // daba [] y la pantalla decia "Sin facturas pendientes" con un check verde: un OK que miente.
    const _fac = Array.isArray(f) ? f : (f.facturas || []);
    const pend = _fac.filter(x => x.estado === 'Emitida' || x.estado === 'Parcial');
    if (!pend.length) { document.getElementById('facturas-pendientes').innerHTML = '<div class="empty">Sin facturas pendientes ✓</div>'; return; }
    let html = '<table><thead><tr><th>Factura</th><th>Cliente</th><th>Total</th><th>Saldo</th><th>Estado</th></tr></thead><tbody>';
    pend.slice(0,30).forEach(fa => {
      // el saldo YA viene calculado por el backend · `fa.pagado` no existe (es `monto_pagado`)
      const saldo = (fa.saldo !== undefined) ? fa.saldo : ((fa.total||0) - (fa.monto_pagado||0));
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
      '<div class="card"><h3>Total por pagar</h3><div class="val">'+fmtM(ap.ap_total||0)+'</div></div>' +
      '<div class="card"><h3>Corriente</h3><div class="val">'+fmtM(_bk(ap,'corriente'))+'</div></div>' +
      '<div class="card"><h3>Vencido 30d</h3><div class="val" style="color:var(--cx-warn-text)">'+fmtM(_bk(ap,'dias_30'))+'</div></div>' +
      '<div class="card"><h3>Vencido 60+d</h3><div class="val neg">'+fmtM(_bk(ap,'dias_60')+_bk(ap,'dias_90'))+'</div></div>' +
      '</div>';
    if (ap.ocs && ap.ocs.length) {
      html += '<table><thead><tr><th>Proveedor</th><th>OC</th><th>Monto</th><th>Días</th></tr></thead><tbody>';
      ap.ocs.slice(0,20).forEach(p => {
        html += '<tr><td>'+_esc(p.proveedor)+'</td><td>'+_esc(p.numero_oc)+'</td><td>'+fmtM(p.valor_total)+'</td><td>'+(p.dias||0)+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    document.getElementById('ap-content').innerHTML = html;
  } catch(e) { document.getElementById('ap-content').innerHTML = '<div class="empty">Error</div>'; }
}

// ── Archivo de OCs · histórico completo + gasto por categoría/mes (Sebastián 21-jul) ──
// El total acumulado de plata vive acá (Tesorería), no en el módulo operativo de Compras.
let _ARCHIVO_OCS = [];
function _ocMoney(n){ return '$'+Math.round(parseFloat(n||0)).toLocaleString('es-CO'); }
function _ocEstChip(e){
  var m={'Pagada':['#dcfce7','#15803d'],'Parcial':['#fef3c7','#92400e'],'Recibida':['#e0e7ff','#3730a3'],
         'Autorizada':['#dbeafe','#1e40af'],'Revisada':['#f3e8ff','#7c3aed'],'Borrador':['#f1f5f9','#475569']};
  var c=m[e]||['#f1f5f9','#475569'];
  return '<span style="font-size:10px;background:'+c[0]+';color:'+c[1]+';border-radius:10px;padding:2px 8px;font-weight:700">'+_esc(e||'-')+'</span>';
}
async function cargarArchivoOCs(){
  var tabla=document.getElementById('oc-tabla'); if(tabla) tabla.innerHTML='<div class="empty">Cargando órdenes…</div>';
  try{
    const d = await fetch('/api/ordenes-compra').then(r=>r.json());
    _ARCHIVO_OCS = (d && d.ordenes) || [];
  }catch(e){ _ARCHIVO_OCS=[]; }
  renderArchivoOCs();
}
function renderArchivoOCs(){
  var q=((document.getElementById('oc-q')||{}).value||'').toLowerCase().trim();
  var est=((document.getElementById('oc-estado')||{}).value||'');
  var all=_ARCHIVO_OCS;
  var list=all.filter(function(o){
    if(est && (o.estado||'')!==est) return false;
    if(!q) return true;
    return ((o.numero_oc||'')+' '+(o.proveedor||'')+' '+(o.categoria||'')).toLowerCase().indexOf(q)>=0;
  });
  list.sort(function(a,b){ return String(b.fecha||'').localeCompare(String(a.fecha||'')); });
  var tot=list.reduce(function(s,o){ return s+(parseFloat(o.valor_total)||0); },0);
  var anio=String(new Date().getFullYear());
  var totAnio=list.reduce(function(s,o){ return s+((String(o.fecha||'').slice(0,4)===anio)?(parseFloat(o.valor_total)||0):0); },0);
  // KPIs
  document.getElementById('oc-kpi-total').textContent=_ocMoney(tot);
  document.getElementById('oc-kpi-count').textContent=list.length;
  document.getElementById('oc-kpi-count-sub').textContent=(est||q)?('filtradas de '+all.length):'registradas';
  document.getElementById('oc-kpi-anio-lbl').textContent='('+anio+')';
  document.getElementById('oc-kpi-anio').textContent=_ocMoney(totAnio);
  document.getElementById('oc-kpi-avg').textContent=_ocMoney(list.length?tot/list.length:0);
  // Gasto por categoría (barras)
  var cats={}; list.forEach(function(o){ var k=o.categoria||'—'; cats[k]=(cats[k]||0)+(parseFloat(o.valor_total)||0); });
  var catArr=Object.keys(cats).map(function(k){ return {k:k,v:cats[k]}; }).sort(function(a,b){ return b.v-a.v; });
  var maxc=catArr.reduce(function(m,x){ return Math.max(m,x.v); },0)||1;
  var catBox=document.getElementById('oc-por-cat');
  catBox.className='';
  catBox.innerHTML=catArr.length?catArr.map(function(c){
    return '<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px"><span style="font-weight:600">'+_esc(c.k)+'</span><span style="font-variant-numeric:tabular-nums;color:var(--cx-text-soft)">'+_ocMoney(c.v)+'</span></div>'
      +'<div style="height:8px;background:var(--cx-border-soft);border-radius:6px;overflow:hidden"><div style="height:100%;width:'+(c.v/maxc*100).toFixed(1)+'%;background:linear-gradient(90deg,#7c3aed,#a855f7);border-radius:6px"></div></div></div>';
  }).join(''):'<div class="empty">Sin datos</div>';
  // Gasto por mes (últimos 12, barras)
  var meses={}; list.forEach(function(o){ var k=String(o.fecha||'').slice(0,7); if(k) meses[k]=(meses[k]||0)+(parseFloat(o.valor_total)||0); });
  var mesArr=Object.keys(meses).sort().reverse().slice(0,12).map(function(k){ return {k:k,v:meses[k]}; });
  var maxm=mesArr.reduce(function(m,x){ return Math.max(m,x.v); },0)||1;
  var mesBox=document.getElementById('oc-por-mes');
  mesBox.className='';
  mesBox.innerHTML=mesArr.length?mesArr.map(function(c){
    return '<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px"><span style="font-weight:600">'+_esc(c.k)+'</span><span style="font-variant-numeric:tabular-nums;color:var(--cx-text-soft)">'+_ocMoney(c.v)+'</span></div>'
      +'<div style="height:8px;background:var(--cx-border-soft);border-radius:6px;overflow:hidden"><div style="height:100%;width:'+(c.v/maxm*100).toFixed(1)+'%;background:linear-gradient(90deg,#0d9488,#2dd4bf);border-radius:6px"></div></div></div>';
  }).join(''):'<div class="empty">Sin datos</div>';
  // Tabla
  var tabla=document.getElementById('oc-tabla'); tabla.className='';
  if(!list.length){ tabla.innerHTML='<div class="empty">No hay órdenes que coincidan.</div>'; return; }
  var rows=list.map(function(o){
    return '<tr><td style="font-weight:700">'+_esc(o.numero_oc)+'</td><td>'+_esc(String(o.fecha||'').slice(0,10))+'</td><td>'+_esc(o.proveedor||'-')+'</td><td>'+_esc(o.categoria||'-')+'</td><td>'+_ocEstChip(o.estado)+'</td><td style="text-align:right;font-variant-numeric:tabular-nums">'+_ocMoney(o.valor_total||0)+'</td></tr>';
  }).join('');
  tabla.innerHTML='<table><thead><tr><th>N° OC</th><th>Fecha</th><th>Proveedor</th><th>Categoría</th><th>Estado</th><th style="text-align:right">Valor</th></tr></thead><tbody>'+rows+'</tbody></table>';
}

async function cargarFacturacion() {
  try {
    const f = await fetch('/api/contabilidad/facturas').then(r=>r.json());
    const _fl = Array.isArray(f) ? f : (f.facturas || []);
    if (!_fl.length) { document.getElementById('facturas-list').innerHTML = '<div class="empty">Sin facturas emitidas. Click "+ Emitir factura"</div>'; return; }
    let html = '<table><thead><tr><th>Número</th><th>Cliente</th><th>Fecha</th><th>Total</th><th>Estado</th><th></th></tr></thead><tbody>';
    _fl.slice(0,50).forEach(fa => {
      const cls = fa.estado==='Pagada'?'b-ok':fa.estado==='Anulada'?'b-err':'b-warn';
      html += '<tr><td><strong>'+_esc(fa.numero)+'</strong></td>' +
              '<td>'+_esc(fa.cliente_nombre)+'</td>' +
              '<td>'+_esc(fa.fecha_emision)+'</td>' +
              '<td>'+fmtM(fa.total)+'</td>' +
              '<td><span class="badge '+cls+'">'+_esc(fa.estado)+'</span></td>' +
              '<td><a href="/api/contabilidad/facturas/'+_esc(fa.numero)+'/pdf" target="_blank" style="color:var(--cx-success-text)">📄 PDF</a></td></tr>';
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

// ════════════════════════════════════════════════════════════════════
// NÓMINA - Cálculo y aprobación quincenal (movido desde /rrhh 29-abr-2026)
// Reusa endpoints de /api/rrhh/nomina/* (no se duplica backend).
// ════════════════════════════════════════════════════════════════════
var nominaData = [];

function fmtCop(n){ return '$'+Math.round(n||0).toLocaleString('es-CO'); }

function badgeEmpresa(e){
  var m={'Espagiria':'#5b21b6','ÁNIMUS Lab':'#92400e','HHA Group':'#1e40af'};
  var col = m[e] || '#475569';
  return '<span class="badge" style="background:'+col+'22;color:'+col+';font-size:10px">'+_esc(e||'-')+'</span>';
}

async function cargarNomina(){
  // Setear defaults la primera vez
  var mesEl = document.getElementById('nom-mes');
  if(mesEl && !mesEl.dataset.inited){
    var now = new Date();
    mesEl.value = String(now.getMonth()+1).padStart(2,'0');
    document.getElementById('nom-anio').value = String(now.getFullYear());
    document.getElementById('nom-quinc').value = now.getDate() <= 15 ? 'Q1' : 'Q2';
    mesEl.dataset.inited = '1';
    loadNomina();
    checkEstadoNomina();
  }
}

async function loadNomina(){
  var mes = document.getElementById('nom-mes').value;
  var anio = document.getElementById('nom-anio').value;
  var quinc = document.getElementById('nom-quinc').value;
  var periodo = anio+'-'+mes+'-'+quinc;
  try {
    nominaData = await fetch('/api/rrhh/nomina/'+periodo).then(r=>r.json());
    if(!Array.isArray(nominaData)) nominaData = [];
    renderNomina();
    checkEstadoNomina();
  } catch(e){ console.error(e); }
}

function calcNeto(row){
  var base = parseFloat(row.salario_base)||0;
  var aux  = parseFloat(row.aux_transporte)||0;
  var he   = parseFloat(row.valor_horas_extras)||0;
  var bonos= parseFloat(row.bonificaciones)||0;
  var salud= Math.round(base*0.04);
  var pension = Math.round(base*0.04);
  var otros = parseFloat(row.otros_descuentos)||0;
  return base+aux+he+bonos-salud-pension-otros;
}

function renderNomina(){
  var tbody = document.getElementById('nom-body');
  if(!nominaData.length){
    tbody.innerHTML = '<tr><td colspan="12" class="empty">Sin empleados con nómina en este periodo.</td></tr>';
    var s = document.getElementById('nom-summary'); if(s){ s.style.display='none'; }
    var ap = document.getElementById('nom-aportes'); if(ap){ ap.style.display='none'; }
    return;
  }
  var totalBruto=0,totalNeto=0,totalDed=0;
  var aportesTot={salud:0,pension:0,arl:0,sena:0,icbf:0,caja:0,total:0};
  tbody.innerHTML = nominaData.map(function(e,i){
    var neto = calcNeto(e);
    totalBruto += (e.salario_base||0)+(e.aux_transporte||0)+(e.valor_horas_extras||0)+(e.bonificaciones||0);
    totalDed += (e.desc_salud||0)+(e.desc_pension||0)+(e.otros_descuentos||0);
    totalNeto += neto;
    var ae = e.aportes_empleador||{};
    Object.keys(aportesTot).forEach(function(k){aportesTot[k]+=(ae[k]||0);});
    return '<tr>' +
      '<td><strong>'+_esc(e.nombre||'')+'</strong><br><small style="color:var(--cx-text-mute)">'+_esc(e.cargo||'')+'</small></td>' +
      '<td>'+badgeEmpresa(e.empresa)+'</td>' +
      '<td><input type="number" value="'+(e.dias_trabajados||0)+'" min="0" max="31" style="width:55px;padding:3px 5px;border:1px solid var(--cx-border);border-radius:4px;font-size:12px" onchange="nominaData['+i+'].dias_trabajados=this.value;renderNomina();"></td>' +
      '<td>'+fmtCop(e.salario_base)+'</td>' +
      '<td style="color:var(--cx-success-text)">'+fmtCop(e.aux_transporte)+'</td>' +
      '<td><input type="number" value="'+(e.valor_horas_extras||0)+'" min="0" step="10000" style="width:80px;padding:3px 5px;border:1px solid var(--cx-border);border-radius:4px;font-size:12px" onchange="nominaData['+i+'].valor_horas_extras=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td><input type="number" value="'+(e.bonificaciones||0)+'" min="0" step="10000" style="width:80px;padding:3px 5px;border:1px solid var(--cx-border);border-radius:4px;font-size:12px" onchange="nominaData['+i+'].bonificaciones=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td style="color:var(--cx-danger-text)">-'+fmtCop(e.desc_salud)+'</td>' +
      '<td style="color:var(--cx-danger-text)">-'+fmtCop(e.desc_pension)+'</td>' +
      '<td style="font-weight:700;color:var(--cx-primary-text)">'+fmtCop(neto)+'</td>' +
      '<td style="font-size:11px">' +
        (e.banco ? '<span style="display:block;font-weight:600">'+_esc(e.banco)+'</span><span style="color:var(--cx-text-mute)">'+_esc(e.tipo_cuenta||'')+'</span><span style="display:block;font-family:monospace;font-size:10px;color:var(--cx-primary-text)">'+_esc(e.numero_cuenta||'')+'</span>' : '<span style="color:var(--cx-border);font-style:italic">Sin registrar</span>') +
      '</td>' +
      '<td><button class="btn" style="padding:2px 7px;font-size:10px;background:var(--cx-bg-alt);color:var(--cx-text)" onclick="verComprobante('+e.id+')" title="Ver comprobante">🖨️</button></td>' +
      '</tr>';
  }).join('');
  var s = document.getElementById('nom-summary');
  s.style.display='grid';
  s.innerHTML =
    '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px">Total Devengado</div><div style="font-size:18px;font-weight:800;color:var(--cx-text);margin-top:4px">'+fmtCop(totalBruto)+'</div></div>'+
    '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px">Total Deducciones</div><div style="font-size:18px;font-weight:800;color:var(--cx-danger-text);margin-top:4px">-'+fmtCop(totalDed)+'</div></div>'+
    '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px">Neto a Pagar</div><div style="font-size:18px;font-weight:800;color:var(--cx-success-text);margin-top:4px">'+fmtCop(totalNeto)+'</div></div>'+
    '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px">Aportes Empleador</div><div style="font-size:18px;font-weight:800;color:var(--cx-primary-text);margin-top:4px">'+fmtCop(aportesTot.total)+'</div></div>'+
    '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px">Costo Total Empresa</div><div style="font-size:18px;font-weight:800;color:var(--cx-primary-text);margin-top:4px">'+fmtCop(totalBruto+aportesTot.total)+'</div></div>';
  var ap = document.getElementById('nom-aportes');
  ap.style.display='block';
  ap.querySelector('#nom-aportes-body').innerHTML =
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px">' +
    [['Salud (8.5%)',aportesTot.salud],['Pensión (12%)',aportesTot.pension],
     ['ARL',aportesTot.arl],['SENA (2%)',aportesTot.sena],
     ['ICBF (3%)',aportesTot.icbf],['Caja (4%)',aportesTot.caja],['TOTAL',aportesTot.total]].map(function(x){
      return '<div style="text-align:center;background:var(--cx-bg-alt);border-radius:8px;padding:10px"><div style="font-size:10px;color:var(--cx-text-mute)">'+x[0]+'</div><div style="font-size:14px;font-weight:700;color:'+(x[0]==='TOTAL'?'#6d28d9':'#1c1917')+';margin-top:2px">'+fmtCop(x[1])+'</div></div>';
    }).join('') + '</div>';
}

async function guardarNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  var periodo=anio+'-'+mes+'-'+quinc;
  nominaData.forEach(function(e){e.neto=calcNeto(e);});
  try {
    var r=await fetch('/api/rrhh/nomina/guardar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({periodo:periodo,registros:nominaData})});
    var d=await r.json();
    if(d.ok){ alert('Nómina guardada: '+d.registros+' registros para '+periodo); checkEstadoNomina(); }
    else alert(d.error||'Error');
  } catch(e){ alert('Error: '+e.message); }
}

async function checkEstadoNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  var periodo=anio+'-'+mes+'-'+quinc;
  try{
    var res=await fetch('/api/rrhh/nomina/'+periodo).then(r=>r.json());
    if(!Array.isArray(res)) return;
    var estados=res.map(e=>e.estado||'').filter(Boolean);
    var pagadas=estados.filter(s=>s==='Pagada').length;
    var aprobadas=estados.filter(s=>s==='Aprobada').length;
    var badge=document.getElementById('nom-estado-badge');
    var btnAp=document.getElementById('nom-btn-aprobar');
    var btnPag=document.getElementById('nom-btn-pagar');
    // ⚠ Estaba en `true` fijo, y aprobar/pagar nomina son SOLO admin (rrhh.py): a Mayra le
    // aparecian los botones y le devolvian 403. Un boton que se ve y no se puede usar es
    // peor que no tenerlo -- el servidor manda, la pantalla solo refleja.
    var esAdmin = !!window._ES_ADMIN;
    if(pagadas>0 && pagadas===estados.length){
      badge.innerHTML='<span style="background:var(--cx-success);color:#fff;padding:3px 12px;border-radius:12px;font-size:11px;font-weight:700">💸 Pagada</span>';
      if(btnAp) btnAp.style.display='none'; if(btnPag) btnPag.style.display='none';
    } else if(aprobadas>0 && aprobadas===estados.length){
      badge.innerHTML='<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">✓ Aprobada - pendiente pago</span>';
      if(btnAp) btnAp.style.display='none';
      if(btnPag && esAdmin) btnPag.style.display='inline-block';
    } else if(estados.length>0){
      badge.innerHTML='<span style="background:var(--cx-warn-pale);color:var(--cx-warn-text);padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">Pendiente aprobación</span>';
      if(btnAp && esAdmin) btnAp.style.display='inline-block';
      if(btnPag) btnPag.style.display='none';
    } else { badge.innerHTML=''; if(btnAp) btnAp.style.display='none'; if(btnPag) btnPag.style.display='none'; }
  } catch(e){}
}

async function aprobarNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  var periodo=anio+'-'+mes+'-'+quinc;
  if(!confirm('¿Aprobar nómina '+periodo+'? Esta acción quedará registrada.')) return;
  try{
    var r=await fetch('/api/rrhh/nomina/'+periodo+'/aprobar',{method:'PATCH'});
    var d=await r.json();
    if(d.ok){ alert('✓ Nómina '+periodo+' aprobada por '+d.por+' ('+d.aprobados+' registros)'); checkEstadoNomina(); }
    else alert(d.error||'Sin permiso');
  } catch(e){ alert('Error: '+e.message); }
}

async function pagarNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  var periodo=anio+'-'+mes+'-'+quinc;
  if(!confirm('¿Marcar nómina '+periodo+' como PAGADA? Registrará fecha y usuario. No se puede deshacer.')) return;
  try{
    var r=await fetch('/api/rrhh/nomina/'+periodo+'/pagar',{method:'PATCH'});
    var d=await r.json();
    if(d.ok){ alert('✅ Nómina '+periodo+' marcada como Pagada por '+d.por+' el '+d.fecha); checkEstadoNomina(); }
    else alert(d.error||'Sin permiso');
  } catch(e){ alert('Error: '+e.message); }
}

function verComprobante(empId){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  var periodo=anio+'-'+mes+'-'+quinc;
  window.open('/api/rrhh/nomina/'+periodo+'/comprobante/'+empId,'_blank','width=700,height=900');
}

function exportarNominaExcel(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value, quinc=document.getElementById('nom-quinc').value;
  window.location.href='/api/rrhh/nomina/'+anio+'-'+mes+'-'+quinc+'/export';
}

async function importarExcelNomina(input){
  var file=input.files[0]; if(!file) return;
  var fd=new FormData(); fd.append('file',file);
  try{
    var r=await fetch('/api/rrhh/nomina/importar-excel',{method:'POST',body:fd});
    var d=await r.json();
    if(!d.ok){ alert(d.error||'Error al importar'); return; }
    var matched=d.data||[];
    matched.forEach(function(row){
      var idx=nominaData.findIndex(function(e){return e.id===row.empleado_id;});
      if(idx>=0){
        if(row.dias_trabajados!=null) nominaData[idx].dias_trabajados=row.dias_trabajados;
        if(row.valor_horas_extras!=null) nominaData[idx].valor_horas_extras=row.valor_horas_extras;
        if(row.bonificaciones!=null) nominaData[idx].bonificaciones=row.bonificaciones;
        if(row.otros_descuentos!=null) nominaData[idx].otros_descuentos=row.otros_descuentos;
      }
    });
    renderNomina();
    alert('Excel importado: '+matched.length+' empleados actualizados. Revisa y haz clic en "Guardar".');
  } catch(e){ alert('Error: '+e.message); }
}

cargarCaja();
setInterval(cargarCaja, 5*60*1000);
</script>
</body>
</html>
"""
