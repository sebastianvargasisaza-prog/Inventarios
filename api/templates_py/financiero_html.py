# Auto-extraído de index.py - Fase A refactor
FINANCIERO_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Financiero - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;}
.topbar{background:#B5924A;color:white;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 12px rgba(181,146,74,0.3);}
.topbar-title{font-size:1.1em;font-weight:800;letter-spacing:2px;}
.topbar a{color:rgba(255,255,255,0.8);text-decoration:none;font-size:0.82em;padding:6px 14px;border:1px solid rgba(255,255,255,0.3);border-radius:6px;}
.tabs{background:var(--cx-card);border-bottom:1px solid var(--cx-border);padding:0 28px;display:flex;gap:4px;}
.tab{padding:14px 22px;cursor:pointer;font-size:0.88em;font-weight:600;color:#9C8B7A;border-bottom:3px solid transparent;transition:all 0.2s;white-space:nowrap;}
.tab.active{color:#B5924A;border-bottom-color:#B5924A;}
.tab:hover:not(.active){color:#B5924A;background:#fdf9f4;}
.content{padding:28px;max-width:1200px;margin:0 auto;}
.page{display:none;}.page.active{display:block;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px;}
.kpi{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:20px 22px;border-left:4px solid var(--c,#B5924A);}
.kpi-val{font-size:1.8em;font-weight:900;color:var(--c,#B5924A);line-height:1;}
.kpi-lbl{font-size:0.78em;color:#9C8B7A;text-transform:uppercase;letter-spacing:1px;margin-top:6px;}
.kpi-sub{font-size:0.82em;color:#9C8B7A;margin-top:4px;}
.kpi-delta{font-size:0.82em;margin-top:6px;font-weight:700;}
.kpi-delta.up{color:var(--cx-primary-text);}.kpi-delta.down{color:var(--cx-danger-text);}
.tbl{width:100%;border-collapse:collapse;background:var(--cx-card);border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.06);}
.tbl thead th{background:#fdf9f4;color:#9C8B7A;font-size:0.78em;text-transform:uppercase;letter-spacing:0.8px;padding:10px 14px;text-align:left;border-bottom:1px solid var(--cx-border);}
.tbl tbody td{padding:11px 14px;border-bottom:1px solid #F5F0EA;font-size:0.88em;vertical-align:middle;}
.tbl tbody tr:hover{background:#fdf9f4;}
.tbl tbody tr:last-child td{border-bottom:none;}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border:none;border-radius:8px;cursor:pointer;font-size:0.88em;font-weight:600;transition:all 0.2s;background:#B5924A;color:white;}
.btn:hover{background:#9a7a3e;}
.btn-ghost{background:var(--cx-card);color:#B5924A;border:1.5px solid #B5924A;}
.btn-red{background:var(--cx-danger);}.btn-green{background:var(--cx-primary);}
.card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:22px;margin-bottom:20px;}
.section-title{font-size:1em;font-weight:800;color:#1C2B30;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:16px;}
.fg label{display:block;font-size:0.78em;color:#9C8B7A;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;margin-bottom:5px;}
.fg input,.fg select,.fg textarea{width:100%;padding:9px 12px;border:1.5px solid var(--cx-border);border-radius:8px;font-size:0.9em;background:var(--cx-card);outline:none;transition:border-color 0.2s;}
.fg input:focus,.fg select:focus{border-color:#B5924A;}
.badge-ing{background:rgba(109,40,217,.1);color:var(--cx-primary-text);padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;}
.badge-egr{background:rgba(192,57,43,.1);color:var(--cx-danger-text);padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;}
.chart-wrap{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:22px;margin-bottom:20px;}
.flujo-pos{color:var(--cx-primary-text);font-weight:700;}
.flujo-neg{color:var(--cx-danger-text);font-weight:700;}
.bar-container{width:100%;background:#f0eeea;border-radius:4px;height:8px;margin-top:6px;}
.bar-fill{height:8px;border-radius:4px;background:var(--bc,#B5924A);transition:width 0.5s;}
/* Mobile responsive · 27-may-2026 */
@media (max-width: 768px) {
  body > div[style*="grid-template-columns:1fr 1fr"],
  body div[style*="grid-template-columns:1fr 1fr"] {
    grid-template-columns: 1fr !important;
  }
  .chart-wrap { padding: 14px; }
}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#15803d" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/></svg>
      Financiero
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; P&amp;L · flujo de caja · capital de trabajo · <span id="periodo-label" style="color:var(--cx-text-faint)"></span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/gerencia" class="cx-btn cx-btn-ghost cx-btn-sm" title="Gerencia">Gerencia</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="tabs">
  <div class="tab active" onclick="goTab('dashboard',this)">📊 Dashboard</div>
  <div class="tab" onclick="goTab('ingresos',this)">📈 Ingresos</div>
  <div class="tab" onclick="goTab('egresos',this)">📉 Egresos</div>
  <div class="tab" onclick="goTab('flujo',this)">🗓️ Flujo Mensual</div>
  <div class="tab" onclick="goTab('ar',this)">📬 Por Cobrar</div>
  <div class="tab" onclick="goTab('ap',this)">📤 Por Pagar</div>
  <div class="tab" onclick="goTab('pnl',this)">📊 P&amp;L</div>
  <div class="tab" onclick="goTab('wc',this)">💼 Capital</div>
  <div class="tab" onclick="goTab('config',this)">⚙️ Supuestos</div>
</div>
<div class="content">

<!-- ─── DASHBOARD ─── -->
<div id="page-dashboard" class="page active">
  <div class="kpi-grid" id="kpi-financiero">
    <div class="kpi" style="--c:var(--cx-primary-text, #6d28d9)"><div class="kpi-val" id="kpi-ing-mes">-</div><div class="kpi-lbl">Ingresos del mes</div><div class="kpi-sub" id="kpi-ing-sub"></div></div>
    <div class="kpi" style="--c:var(--cx-danger-text, #c0392b)"><div class="kpi-val" id="kpi-egr-mes">-</div><div class="kpi-lbl">Egresos del mes</div><div class="kpi-sub" id="kpi-egr-sub"></div></div>
    <div class="kpi" style="--c:var(--cx-warn-text, #B5924A)"><div class="kpi-val" id="kpi-flujo-mes">-</div><div class="kpi-lbl">Flujo neto mes</div><div class="kpi-sub" id="kpi-flujo-sub"></div></div>
    <div class="kpi" style="--c:var(--cx-primary-text, #7A4A8B)"><div class="kpi-val" id="kpi-caja">-</div><div class="kpi-lbl">Saldo de caja</div><div class="kpi-sub" id="kpi-caja-sub"></div></div>
    <div class="kpi" style="--c:var(--cx-success-text, #10b981);border-left:3px solid var(--cx-success);"><div class="kpi-val" id="kpi-shopify" style="color:var(--cx-success-text);">-</div><div class="kpi-lbl">Shopify DTC · mes</div><div class="kpi-sub" id="kpi-shopify-sub"></div></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="chart-wrap">
      <div class="section-title">Ingresos vs Egresos - Últimos 6 meses</div>
      <canvas id="chart-ing-egr" height="200"></canvas>
    </div>
    <div class="card">
      <div class="section-title">📋 Desglose del mes</div>
      <div id="desglose-mes"></div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">⚠️ Alertas financieras</div>
    <div id="alertas-fin"></div>
  </div>
  <div class="card" style="margin-top:20px">
    <div class="section-title">📊 Tendencia 12 meses · MoM</div>
    <div id="mom-12-stats" style="display:flex;flex-wrap:wrap;gap:18px;font-size:0.88em;color:#7A6A55;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--cx-border)">
      <span>Cargando…</span>
    </div>
    <canvas id="chart-mom-12" height="160"></canvas>
    <div style="overflow-x:auto;margin-top:18px">
      <table style="width:100%;font-size:0.85em;border-collapse:collapse">
        <thead>
          <tr style="background:#F5F0E8;color:#7A6A55">
            <th style="padding:8px 10px;text-align:left;font-size:0.78em;text-transform:uppercase">Mes</th>
            <th style="padding:8px 10px;text-align:right;font-size:0.78em;text-transform:uppercase">Ingresos</th>
            <th style="padding:8px 10px;text-align:right;font-size:0.78em;text-transform:uppercase">Egresos</th>
            <th style="padding:8px 10px;text-align:right;font-size:0.78em;text-transform:uppercase">Margen</th>
            <th style="padding:8px 10px;text-align:right;font-size:0.78em;text-transform:uppercase">% Margen</th>
            <th style="padding:8px 10px;text-align:right;font-size:0.78em;text-transform:uppercase">MoM Ingreso</th>
          </tr>
        </thead>
        <tbody id="mom-12-tbody">
          <tr><td colspan="6" style="text-align:center;padding:18px;color:var(--cx-text-faint)">Cargando…</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ─── INGRESOS ─── -->
<div id="page-ingresos" class="page">
  <div class="card">
    <div class="section-title">+ Registrar Ingreso</div>
    <div class="form-grid">
      <div class="fg"><label>Fecha</label><input type="date" id="ing-fecha"></div>
      <div class="fg"><label>Empresa</label>
        <select id="ing-empresa">
          <option value="ANIMUS">ÁNIMUS Lab</option>
          <option value="ESPAGIRIA">Espagiria</option>
          <option value="HHA">HHA Group</option>
        </select>
      </div>
      <div class="fg"><label>Categoría</label>
        <select id="ing-cat">
          <option value="Ventas directas">Ventas directas</option>
          <option value="Maquila">Maquila</option>
          <option value="Distribuidor">Distribuidor (FM)</option>
          <option value="E-commerce">E-commerce</option>
          <option value="Otro">Otro</option>
        </select>
      </div>
      <div class="fg"><label>Concepto</label><input type="text" id="ing-concepto" placeholder="Ej: Pedido FM Abril"></div>
      <div class="fg"><label>Monto (COP)</label><input type="number" id="ing-monto" placeholder="0"></div>
      <div class="fg"><label>Referencia</label><input type="text" id="ing-ref" placeholder="Nro factura, pedido..."></div>
    </div>
    <button class="btn btn-green" onclick="guardarIngreso()">+ Registrar Ingreso</button>
    <div id="ing-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div class="section-title" style="margin:0;">Historial de Ingresos</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <input type="text" placeholder="Buscar..." oninput="buscarTabla('ing', this.value)" style="padding:6px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:0.85em;max-width:180px">
        <select id="ing-filtro-mes" onchange="loadIngresos()" style="padding:6px 12px;border:1px solid var(--cx-border);border-radius:6px;font-size:0.85em;">
          <option value="">Todos los meses</option>
        </select>
      </div>
    </div>
    <table class="tbl">
      <thead><tr><th>Fecha</th><th>Empresa</th><th>Categoría</th><th>Concepto</th><th>Referencia</th><th style="text-align:right;">Monto</th></tr></thead>
      <tbody id="ing-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">Cargando...</td></tr></tbody>
    </table>
    <div id="ing-total" style="text-align:right;font-weight:700;padding:12px 14px;font-size:1.05em;color:var(--cx-primary-text);"></div>
    <div id="pg-ing"></div>
  </div>
</div>

<!-- ─── EGRESOS ─── -->
<div id="page-egresos" class="page">
  <div class="card">
    <div class="section-title">+ Registrar Egreso</div>
    <div class="form-grid">
      <div class="fg"><label>Fecha</label><input type="date" id="egr-fecha"></div>
      <div class="fg"><label>Empresa</label>
        <select id="egr-empresa">
          <option value="ESPAGIRIA">Espagiria</option>
          <option value="ANIMUS">ÁNIMUS Lab</option>
          <option value="HHA">HHA Group</option>
        </select>
      </div>
      <div class="fg"><label>Categoría</label>
        <select id="egr-cat">
          <option value="MPs">Materias Primas</option>
          <option value="MEE">Material Empaque/Envase</option>
          <option value="Nomina">Nómina</option>
          <option value="Arrendamiento">Arrendamiento</option>
          <option value="Servicios">Servicios públicos</option>
          <option value="Marketing">Marketing</option>
          <option value="Logistica">Logística</option>
          <option value="Regulatorio">Regulatorio / INVIMA</option>
          <option value="Otro">Otro</option>
        </select>
      </div>
      <div class="fg"><label>Concepto</label><input type="text" id="egr-concepto" placeholder="Ej: Compra MPs Abril"></div>
      <div class="fg"><label>Monto (COP)</label><input type="number" id="egr-monto" placeholder="0"></div>
      <div class="fg"><label>Referencia</label><input type="text" id="egr-ref" placeholder="Nro OC, factura..."></div>
    </div>
    <button class="btn btn-red" onclick="guardarEgreso()">+ Registrar Egreso</button>
    <div id="egr-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div class="section-title" style="margin:0;">Historial de Egresos</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <input type="text" placeholder="Buscar..." oninput="buscarTabla('egr', this.value)" style="padding:6px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:0.85em;max-width:180px">
        <select id="egr-filtro-mes" onchange="loadEgresos()" style="padding:6px 12px;border:1px solid var(--cx-border);border-radius:6px;font-size:0.85em;">
          <option value="">Todos los meses</option>
        </select>
      </div>
    </div>
    <table class="tbl">
      <thead><tr><th>Fecha</th><th>Empresa</th><th>Categoría</th><th>Concepto</th><th>Referencia</th><th style="text-align:right;">Monto</th></tr></thead>
      <tbody id="egr-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">Cargando...</td></tr></tbody>
    </table>
    <div id="egr-total" style="text-align:right;font-weight:700;padding:12px 14px;font-size:1.05em;color:var(--cx-danger-text);"></div>
    <div id="pg-egr"></div>
  </div>
</div>

<!-- ─── FLUJO MENSUAL ─── -->
<div id="page-flujo" class="page">
  <div class="card">
    <div class="section-title">🗓️ Flujo de Caja Mensual</div>
    <div style="overflow-x:auto;">
    <table class="tbl" id="flujo-tbl">
      <thead><tr>
        <th>Período</th>
        <th style="text-align:right;color:var(--cx-primary-text);">Ingresos</th>
        <th style="text-align:right;color:var(--cx-danger-text);">Egresos</th>
        <th style="text-align:right;">Flujo Neto</th>
        <th style="text-align:right;">Acumulado</th>
        <th>Estado</th>
      </tr></thead>
      <tbody id="flujo-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">Cargando...</td></tr></tbody>
    </table>
    </div>
  </div>
  <div class="chart-wrap">
    <div class="section-title">Flujo Neto Mensual</div>
    <canvas id="chart-flujo" height="180"></canvas>
  </div>
</div>

<!-- ─── SUPUESTOS ─── -->
<div id="page-config" class="page">
  <div class="card">
    <div class="section-title">⚙️ Supuestos y Configuración</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:20px;">Parámetros base del modelo financiero. Actualizar cuando cambien las condiciones del negocio.</p>
    <div id="config-list"></div>
    <button class="btn" onclick="guardarConfig()" style="margin-top:16px;">Guardar cambios</button>
    <div id="config-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card" style="border:1px solid rgba(34,211,238,0.3);">
    <div class="section-title" style="color:#22d3ee;">🛍️ Sync automático Shopify → Ingresos</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:12px;">Importa los pedidos pagados de Shopify como ingresos en el flujo financiero. Idempotente: cada pedido solo se importa una vez (marcado <code>flujo_synced=1</code>).</p>
    <div id="shopify-sync-status" style="background:var(--cx-text);padding:12px;border-radius:8px;margin-bottom:12px;font-size:0.85em;color:var(--cx-text-faint);">Cargando estado...</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <button class="btn btn-ghost" onclick="syncShopifyDryRun()" style="border-color:#22d3ee;color:#22d3ee;">👁️ Previsualizar</button>
      <button class="btn btn-ghost" onclick="syncShopifyEjecutar()" style="background:var(--cx-info);color:#fff;border-color:var(--cx-info);">✨ Sincronizar ahora</button>
    </div>
    <div id="shopify-sync-msg" style="margin-top:10px;font-size:0.88em;"></div>
  </div>
  <div class="card">
    <div class="section-title">📤 Importar desde OCs (egresos automáticos)</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Importa las órdenes de compra recibidas como egresos de MPs automáticamente.</p>
    <button class="btn btn-ghost" onclick="importarOCs()">📦 Importar OCs recibidas como egresos</button>
    <div id="import-msg" style="margin-top:10px;"></div>
    <div style="margin-top:20px;padding-top:16px;border-top:1px solid #2d2420;">
      <div style="font-size:0.82em;color:var(--cx-danger-text);font-weight:600;margin-bottom:8px;">⚠️ Zona de peligro - solo admin</div>
      <p style="font-size:0.82em;color:#9C8B7A;margin-bottom:10px;">Elimina <strong>todos</strong> los registros de flujo de egresos e ingresos (útil si hay datos incorrectos importados).</p>
      <button class="btn btn-ghost" style="border-color:var(--cx-danger);color:var(--cx-danger-text);" onclick="limpiarFlujo()">🗑️ Limpiar todo el flujo (egresos e ingresos)</button>
      <div id="limpiar-msg" style="margin-top:8px;font-size:0.82em;"></div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">💲 Precios Mayorista por SKU</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Precio de venta mayorista en COP por unidad. Solo visible para administración - no aparece en el módulo de operarios.</p>
    <div id="precios-list"><p style="color:#9C8B7A;font-size:0.88em;">Cargando...</p></div>
    <div id="precios-msg" style="margin-top:10px;"></div>
  </div>
</div>

<!-- AR AGING -->
<div id="page-ar" class="page">
  <div class="card">
    <div class="section-title">📬 Cuentas por Cobrar - AR Aging</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Pedidos activos con saldo pendiente, agrupados por antigüedad.</p>
    <div id="ar-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="ar-table"></div>
  </div>
</div>

<!-- AP AGING -->
<div id="page-ap" class="page">
  <div class="card">
    <div class="section-title">📤 Cuentas por Pagar - AP Aging</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Órdenes de compra autorizadas/recibidas sin registrar pago, agrupadas por antigüedad.</p>
    <div id="ap-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="ap-table"></div>
  </div>
</div>

<!-- P&L -->
<div id="page-pnl" class="page">
  <div class="card">
    <div class="section-title">📊 P&amp;L - Estado de Resultados</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Ingresos, egresos y margen operacional por empresa y consolidado. Actualización mensual.</p>
    <div id="pnl-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="pnl-brands" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;"></div>
    <div id="pnl-ytd" style="margin-bottom:16px;"></div>
    <div class="section-title" style="font-size:0.9em;margin-bottom:8px;">📈 Histórico 6 meses</div>
    <canvas id="pnl-chart" height="100"></canvas>
  </div>
</div>

<!-- WORKING CAPITAL -->
<div id="page-wc" class="page">
  <div class="card">
    <div class="section-title">💼 Capital de Trabajo &amp; CCC</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Working capital, ciclo de conversión de efectivo (CCC), burn rate y runway.</p>
    <div id="wc-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="wc-ccc" style="margin-bottom:20px;"></div>
    <div id="wc-equation"></div>
  </div>
</div>

</div>

<script>
// CSRF defense-in-depth · Sebastian 3-may-2026
function _csrf() {
  var m = document.cookie.match(/(?:^|;\\s*)csrf_token=([^;]+)/);
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

// Filtros + Paginacion (client-side)
var TBL_STATE = {
  ing:    {q: '', page: 1, size: 50, fields: ['fecha','empresa','concepto','categoria','referencia']},
  egr:    {q: '', page: 1, size: 50, fields: ['fecha','empresa','concepto','categoria','referencia']},
  precios:{q: '', page: 1, size: 50, fields: ['sku','descripcion']},
};
function _filtrar(data, query, fields) {
  if (!query) return data || [];
  var q = query.toLowerCase().trim();
  return (data || []).filter(function(r) {
    return fields.some(function(f) {
      var v = r[f]; return v != null && String(v).toLowerCase().indexOf(q) !== -1;
    });
  });
}
function _paginar(data, page, size) {
  if (size >= 999) return {items: data, total: data.length, totalPages: 1, page: 1};
  var total = data.length;
  var totalPages = Math.max(1, Math.ceil(total / size));
  var p = Math.min(Math.max(1, page), totalPages);
  return {items: data.slice((p-1)*size, p*size), total: total, totalPages: totalPages, page: p};
}
function _renderPag(tabla, info) {
  var s = TBL_STATE[tabla];
  if (info.total <= s.size && info.total < 51) {
    return '<div style="font-size:11px;color:var(--cx-text-mute);padding:6px 0;">' + info.total + ' filas</div>';
  }
  var html = '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;font-size:12px;color:var(--cx-text-mute);">';
  html += '<span>P' + String.fromCharCode(225) + 'g ' + info.page + '/' + info.totalPages + ' ' + String.fromCharCode(183) + ' ' + info.total + '</span>';
  html += '<span style="flex:1"></span>';
  html += '<button class="btn-sm" data-act="prev" data-tbl="' + tabla + '"' +
          (info.page <= 1 ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid var(--cx-border);border-radius:5px;background:var(--cx-card);cursor:pointer">&larr;</button>';
  html += '<button class="btn-sm" data-act="next" data-tbl="' + tabla + '"' +
          (info.page >= info.totalPages ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid var(--cx-border);border-radius:5px;background:var(--cx-card);cursor:pointer">&rarr;</button>';
  html += '<select data-act="size" data-tbl="' + tabla + '" ' +
          'style="border:1px solid var(--cx-border);padding:4px 6px;border-radius:5px;font-size:12px;">';
  ['25','50','100','999'].forEach(function(o){
    var label = o === '999' ? 'Todas' : o;
    html += '<option value="' + o + '"' + (String(s.size)===o?' selected':'') + '>' + label + '</option>';
  });
  html += '</select></div>';
  return html;
}
document.addEventListener('click', function(ev){
  var btn = ev.target.closest('[data-act][data-tbl]');
  if (!btn) return;
  var tbl = btn.dataset.tbl;
  var act = btn.dataset.act;
  if (act === 'prev') cambiarPag(tbl, -1);
  else if (act === 'next') cambiarPag(tbl, 1);
});
document.addEventListener('change', function(ev){
  var sel = ev.target.closest('select[data-act="size"][data-tbl]');
  if (!sel) return;
  cambiarPagSize(sel.dataset.tbl, sel.value);
})
var _PAG_REFRESH = {
  ing: function(){ if(window.loadIngresos) loadIngresos(); },
  egr: function(){ if(window.loadEgresos) loadEgresos(); },
  precios: function(){ if(window.loadPreciosMayorista) loadPreciosMayorista(); },
};
function cambiarPag(tabla, delta){ TBL_STATE[tabla].page = Math.max(1, TBL_STATE[tabla].page + delta); if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function cambiarPagSize(tabla, valor){ TBL_STATE[tabla].size = parseInt(valor,10)||50; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function buscarTabla(tabla, valor){ TBL_STATE[tabla].q = valor||''; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }

var _chartIngEgr=null, _chartFlujo=null;
var _config={};

function fmt(n){
  if(!n&&n!==0) return '-';
  var abs=Math.abs(n);
  if(abs>=1000000) return (n<0?'-':'')+'$'+(abs/1000000).toFixed(1)+'M';
  if(abs>=1000) return (n<0?'-':'')+'$'+(abs/1000).toFixed(0)+'K';
  return (n<0?'-':'')+'$'+abs.toLocaleString('es-CO');
}
function fmtFull(n){
  if(!n&&n!==0) return '-';
  return (n<0?'-':'')+'$'+Math.abs(n).toLocaleString('es-CO');
}

function goTab(id,el){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById('page-'+id).classList.add('active');
  if(el)el.classList.add('active');
  if(id==='dashboard')loadDashboard();
  if(id==='ingresos')loadIngresos();
  if(id==='egresos')loadEgresos();
  if(id==='flujo')loadFlujo();
  if(id==='config'){loadConfig();loadPreciosMayorista();}
  if(id==='ar')loadARaging();
  if(id==='ap')loadAPaging();
  if(id==='pnl')loadPNL();
  if(id==='wc')loadWorkingCapital();
}

async function loadDashboard(){
  try{
    var d=await fetch('/api/financiero/kpis').then(function(r){return r.json();});
    var hoy=new Date();
    document.getElementById('periodo-label').textContent=hoy.toLocaleString('es',{month:'long',year:'numeric'});
    document.getElementById('kpi-ing-mes').textContent=fmt(d.ing_mes||0);
    // Shopify real-time
    if(document.getElementById('kpi-shopify')){
      document.getElementById('kpi-shopify').textContent=fmt(d.shopify_mes||0);
      document.getElementById('kpi-shopify-sub').textContent=(d.shopify_pedidos||0)+' pedidos · YTD '+fmt(d.shopify_anio||0);
    }
    document.getElementById('kpi-ing-sub').textContent=(d.ing_count||0)+' transacciones';
    document.getElementById('kpi-egr-mes').textContent=fmt(d.egr_mes||0);
    document.getElementById('kpi-egr-sub').textContent=(d.egr_count||0)+' transacciones';
    var flujo=(d.ing_mes||0)-(d.egr_mes||0);
    var kflujo=document.getElementById('kpi-flujo-mes');
    kflujo.textContent=fmt(flujo);
    kflujo.style.color=flujo>=0?'#6d28d9':'#c0392b';
    document.getElementById('kpi-flujo-sub').textContent=flujo>=0?'Superávit':'Déficit';
    document.getElementById('kpi-caja').textContent=fmt(d.saldo_caja||0);
    var meta=parseFloat(_config.meta_caja_min||50000000);
    document.getElementById('kpi-caja-sub').textContent=(d.saldo_caja||0)>=meta?'✓ Por encima del mínimo':'⚠️ Bajo el mínimo ($'+fmt(meta)+')';
    // Desglose
    var des='<table style="width:100%;font-size:0.88em;">';
    if(d.desglose_ing&&d.desglose_ing.length){
      des+='<tr><td colspan="2" style="font-weight:700;color:var(--cx-primary-text);padding:6px 0;">INGRESOS</td></tr>';
      d.desglose_ing.forEach(function(r){des+='<tr><td style="color:var(--cx-text-mute);">'+r.categoria+'</td><td style="text-align:right;font-weight:600;">'+fmt(r.total)+'</td></tr>';});
    }
    if(d.desglose_egr&&d.desglose_egr.length){
      des+='<tr><td colspan="2" style="font-weight:700;color:var(--cx-danger-text);padding:6px 0;padding-top:14px;">EGRESOS</td></tr>';
      d.desglose_egr.forEach(function(r){des+='<tr><td style="color:var(--cx-text-mute);">'+r.categoria+'</td><td style="text-align:right;font-weight:600;">'+fmt(r.total)+'</td></tr>';});
    }
    des+='</table>';
    document.getElementById('desglose-mes').innerHTML=des;
    // Alertas
    var alertas='';
    var metaCaja=parseFloat(_config.meta_caja_min||50000000);
    if((d.saldo_caja||0)<metaCaja) alertas+='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:8px;">🟡 Saldo de caja ($'+fmt(d.saldo_caja||0)+') está por debajo del mínimo ($'+fmt(metaCaja)+')</div>';
    if(flujo<0) alertas+='<div style="background:#fde8e8;border:1px solid #f5c6cb;border-radius:8px;padding:12px 16px;margin-bottom:8px;">🔴 Flujo neto negativo este mes: '+fmt(flujo)+'</div>';
    if(!alertas) alertas='<div style="color:var(--cx-primary-text);font-size:0.92em;padding:8px;">✅ Sin alertas críticas este mes.</div>';
    document.getElementById('alertas-fin').innerHTML=alertas;
    // Chart
    if(d.historico&&d.historico.length){
      var labels=d.historico.map(function(h){return h.periodo;});
      var ings=d.historico.map(function(h){return h.ingresos||0;});
      var egrs=d.historico.map(function(h){return h.egresos||0;});
      if(_chartIngEgr)_chartIngEgr.destroy();
      _chartIngEgr=new Chart(document.getElementById('chart-ing-egr'),{
        type:'bar',
        data:{labels:labels,datasets:[
          {label:'Ingresos',data:ings,backgroundColor:'rgba(109,40,217,0.7)',borderRadius:4},
          {label:'Egresos',data:egrs,backgroundColor:'rgba(192,57,43,0.7)',borderRadius:4}
        ]},
        options:{responsive:true,plugins:{legend:{position:'top'}},scales:{y:{ticks:{callback:function(v){return fmt(v);}}}}}
      });
    }
    // 12-month MoM trend (independent · doesn't share state with chart-ing-egr)
    loadMoM12();
  }catch(e){console.error(e);}
}

var _chartMoM12 = null;
async function loadMoM12(){
  try{
    var r = await fetch('/api/financiero/mom-12-meses');
    if(!r.ok) return;
    var d = await r.json();
    var meses = d.meses || [];
    if(!meses.length) return;

    // Stats summary
    var s = d.stats || {};
    var statsEl = document.getElementById('mom-12-stats');
    if(statsEl){
      var parts = [];
      if(s.mejor_mes) parts.push('🏆 Mejor: <b>'+s.mejor_mes+'</b> ('+fmt(s.mejor_mes_margen)+')');
      if(s.peor_mes) parts.push('📉 Peor: <b>'+s.peor_mes+'</b> ('+fmt(s.peor_mes_margen)+')');
      if(s.margen_promedio !== undefined) parts.push('📊 Promedio: <b>'+fmt(s.margen_promedio)+'</b>');
      if(s.top_categoria_egreso) parts.push('💸 Top egreso: <b>'+s.top_categoria_egreso+'</b> ('+fmt(s.top_categoria_egreso_monto)+')');
      statsEl.innerHTML = parts.length ? parts.join(' · ') : '<span style="color:var(--cx-text-faint)">Sin datos en los últimos 12 meses</span>';
    }

    // Chart bar dual: ingresos / egresos / margen line
    var labels = meses.map(function(m){return m.periodo;});
    var ings = meses.map(function(m){return m.ingresos;});
    var egrs = meses.map(function(m){return m.egresos;});
    var margenes = meses.map(function(m){return m.margen;});

    if(_chartMoM12) _chartMoM12.destroy();
    _chartMoM12 = new Chart(document.getElementById('chart-mom-12'), {
      data: {
        labels: labels,
        datasets: [
          {type:'bar', label:'Ingresos', data:ings,
            backgroundColor:'rgba(109,40,217,0.65)', borderRadius:3, order:2},
          {type:'bar', label:'Egresos', data:egrs,
            backgroundColor:'rgba(192,57,43,0.65)', borderRadius:3, order:2},
          {type:'line', label:'Margen', data:margenes,
            borderColor:'#B5924A', backgroundColor:'rgba(181,146,74,0.1)',
            tension:0.25, fill:false, borderWidth:2.5, pointRadius:4, order:1},
        ]
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        plugins: {legend:{position:'top'}},
        scales: {y:{ticks:{callback:function(v){return fmt(v);}}}},
      }
    });

    // Tabla MoM
    var tbody = document.getElementById('mom-12-tbody');
    if(tbody){
      tbody.innerHTML = meses.map(function(m){
        var marColor = m.margen >= 0 ? '#6d28d9' : '#c0392b';
        var momHtml = '-';
        if(m.mom_pct !== null && m.mom_pct !== undefined){
          var momColor = m.mom_pct >= 0 ? '#6d28d9' : '#c0392b';
          var arrow = m.mom_pct >= 0 ? '▲' : '▼';
          momHtml = '<span style="color:'+momColor+';font-weight:600">'+arrow+' '+m.mom_pct.toFixed(1)+'%</span>';
        }
        // Onclicks computed separately to keep template clean
        var clickIng = 'abrirMesDetalle("'+m.periodo+'","ingresos")';
        var clickEgr = 'abrirMesDetalle("'+m.periodo+'","egresos")';
        return '<tr style="border-bottom:1px solid #F5F0E8">'
          +'<td style="padding:8px 10px"><b>'+m.periodo+'</b></td>'
          +'<td style="padding:8px 10px;text-align:right;cursor:pointer;text-decoration:underline dotted #94a3b8" onclick=\\\''+clickIng+'\\\' title="Ver desglose">'+fmt(m.ingresos)+'</td>'
          +'<td style="padding:8px 10px;text-align:right;color:var(--cx-danger-text);cursor:pointer;text-decoration:underline dotted #fca5a5" onclick=\\\''+clickEgr+'\\\' title="Ver desglose">'+fmt(m.egresos)+'</td>'
          +'<td style="padding:8px 10px;text-align:right;color:'+marColor+';font-weight:700">'+fmt(m.margen)+'</td>'
          +'<td style="padding:8px 10px;text-align:right;color:#7A6A55">'+m.margen_pct.toFixed(1)+'%</td>'
          +'<td style="padding:8px 10px;text-align:right">'+momHtml+'</td>'
          +'</tr>';
      }).join('');
    }
  }catch(e){console.error('loadMoM12 fallo:',e);}
}

async function loadIngresos(){
  var mes=document.getElementById('ing-filtro-mes')&&document.getElementById('ing-filtro-mes').value||'';
  try{
    var url='/api/financiero/ingresos'+(mes?'?mes='+mes:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var rows=d.ingresos||[];
    // populate mes filter
    var sel=document.getElementById('ing-filtro-mes');
    if(sel&&sel.options.length<=1){
      var meses=[...new Set(rows.map(function(r){return(r.periodo||r.fecha||'').substring(0,7);}))].sort().reverse();
      meses.forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o);});
    }
    var total=rows.reduce(function(s,r){return s+(r.monto||0);},0);
    var s=TBL_STATE.ing;
    var filtrado=_filtrar(rows, s.q, s.fields);
    var info=_paginar(filtrado, s.page, s.size);
    s.page=info.page;
    var pgEl=document.getElementById('pg-ing');
    var h='';
    if(!info.items.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">'+(s.q?'Sin coincidencias':'Sin ingresos registrados')+'</td></tr>';}
    info.items.forEach(function(r){
      h+='<tr><td>'+((r.fecha||'').substring(0,10))+'</td>';
      h+='<td><span class="badge-ing">'+r.empresa+'</span></td>';
      h+='<td>'+r.categoria+'</td>';
      h+='<td>'+r.concepto+'</td>';
      h+='<td style="color:var(--cx-text-mute);font-size:0.85em;">'+(r.referencia||'')+'</td>';
      h+='<td style="text-align:right;font-weight:700;color:var(--cx-primary-text);">'+fmtFull(r.monto)+'</td></tr>';
    });
    document.getElementById('ing-tbody').innerHTML=h;
    document.getElementById('ing-total').textContent='Total: '+fmtFull(total);
    if(pgEl) pgEl.innerHTML=_renderPag('ing', info);
  }catch(e){console.error(e);}
}

async function loadEgresos(){
  var mes=document.getElementById('egr-filtro-mes')&&document.getElementById('egr-filtro-mes').value||'';
  try{
    var url='/api/financiero/egresos'+(mes?'?mes='+mes:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var rows=d.egresos||[];
    var sel=document.getElementById('egr-filtro-mes');
    if(sel&&sel.options.length<=1){
      var meses=[...new Set(rows.map(function(r){return(r.periodo||r.fecha||'').substring(0,7);}))].sort().reverse();
      meses.forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o);});
    }
    var total=rows.reduce(function(s,r){return s+(r.monto||0);},0);
    var st=TBL_STATE.egr;
    var filtrado=_filtrar(rows, st.q, st.fields);
    var info=_paginar(filtrado, st.page, st.size);
    st.page=info.page;
    var pgEl=document.getElementById('pg-egr');
    var h='';
    if(!info.items.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">'+(st.q?'Sin coincidencias':'Sin egresos registrados')+'</td></tr>';}
    info.items.forEach(function(r){
      h+='<tr><td>'+((r.fecha||'').substring(0,10))+'</td>';
      h+='<td><span class="badge-egr">'+r.empresa+'</span></td>';
      h+='<td>'+r.categoria+'</td>';
      h+='<td>'+r.concepto+'</td>';
      h+='<td style="color:var(--cx-text-mute);font-size:0.85em;">'+(r.referencia||'')+'</td>';
      h+='<td style="text-align:right;font-weight:700;color:var(--cx-danger-text);">'+fmtFull(r.monto)+'</td></tr>';
    });
    document.getElementById('egr-tbody').innerHTML=h;
    document.getElementById('egr-total').textContent='Total egresos: '+fmtFull(total);
    if(pgEl) pgEl.innerHTML=_renderPag('egr', info);
  }catch(e){console.error(e);}
}

async function loadFlujo(){
  try{
    var d=await fetch('/api/financiero/flujo-mensual').then(function(r){return r.json();});
    var meses=d.meses||[];
    var acum=0;
    var h='';
    if(!meses.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-faint);">Sin datos de flujo</td></tr>';}
    meses.forEach(function(m){
      var flujo=(m.ingresos||0)-(m.egresos||0);
      acum+=flujo;
      var cls=flujo>=0?'flujo-pos':'flujo-neg';
      var acls=acum>=0?'flujo-pos':'flujo-neg';
      h+='<tr><td style="font-weight:600;">'+m.periodo+'</td>';
      h+='<td style="text-align:right;color:var(--cx-primary-text);font-weight:700;">'+fmtFull(m.ingresos||0)+'</td>';
      h+='<td style="text-align:right;color:var(--cx-danger-text);font-weight:700;">'+fmtFull(m.egresos||0)+'</td>';
      h+='<td style="text-align:right;" class="'+cls+'">'+fmtFull(flujo)+'</td>';
      h+='<td style="text-align:right;" class="'+acls+'">'+fmtFull(acum)+'</td>';
      h+='<td><span style="background:'+(flujo>=0?'rgba(109,40,217,.1)':'rgba(192,57,43,.1)')+';color:'+(flujo>=0?'#6d28d9':'#c0392b')+';padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;">'+(flujo>=0?'Superávit':'Déficit')+'</span></td></tr>';
    });
    document.getElementById('flujo-tbody').innerHTML=h;
    // Chart
    if(meses.length){
      var labels=meses.map(function(m){return m.periodo;});
      var flujos=meses.map(function(m){return(m.ingresos||0)-(m.egresos||0);});
      var colors=flujos.map(function(f){return f>=0?'rgba(109,40,217,0.7)':'rgba(192,57,43,0.7)';});
      if(_chartFlujo)_chartFlujo.destroy();
      _chartFlujo=new Chart(document.getElementById('chart-flujo'),{
        type:'bar',data:{labels:labels,datasets:[{label:'Flujo Neto',data:flujos,backgroundColor:colors,borderRadius:4}]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:function(v){return fmt(v);}}}}}
      });
    }
  }catch(e){console.error(e);}
}

async function loadConfig(){
  try{
    var d=await fetch('/api/financiero/config').then(function(r){return r.json();});
    _config=d.config||{};
    var h='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">';
    Object.entries(_config).forEach(function([k,v]){
      h+='<div class="fg"><label>'+k.replace(/_/g,' ').toUpperCase()+'</label>';
      h+='<input type="text" id="cfg-'+k+'" value="'+v+'"></div>';
    });
    h+='</div>';
    document.getElementById('config-list').innerHTML=h;
  }catch(e){}
}

async function guardarConfig(){
  var updates={};
  document.querySelectorAll('[id^="cfg-"]').forEach(function(el){
    var key=el.id.replace('cfg-','');
    updates[key]=el.value;
  });
  var r=await fetch('/api/financiero/config',_fetchOpts('POST', updates));
  var d=await r.json();
  document.getElementById('config-msg').innerHTML=r.ok?'<span style="color:var(--cx-primary-text);">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
}

async function guardarIngreso(){
  var fecha=document.getElementById('ing-fecha').value;
  var empresa=document.getElementById('ing-empresa').value;
  var cat=document.getElementById('ing-cat').value;
  var concepto=document.getElementById('ing-concepto').value.trim();
  var monto=parseFloat(document.getElementById('ing-monto').value)||0;
  var ref=document.getElementById('ing-ref').value.trim();
  if(!concepto||!monto){alert('Concepto y monto son requeridos');return;}
  if(!fecha){fecha=new Date().toISOString().substring(0,10);}
  var r=await fetch('/api/financiero/ingresos',_fetchOpts('POST', {fecha:fecha,empresa:empresa,categoria:cat,concepto:concepto,monto:monto,referencia:ref}));
  var d=await r.json();
  document.getElementById('ing-msg').innerHTML=r.ok?'<span style="color:var(--cx-primary-text);">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
  if(r.ok){document.getElementById('ing-concepto').value='';document.getElementById('ing-monto').value='';document.getElementById('ing-ref').value='';loadIngresos();}
}

async function guardarEgreso(){
  var fecha=document.getElementById('egr-fecha').value;
  var empresa=document.getElementById('egr-empresa').value;
  var cat=document.getElementById('egr-cat').value;
  var concepto=document.getElementById('egr-concepto').value.trim();
  var monto=parseFloat(document.getElementById('egr-monto').value)||0;
  var ref=document.getElementById('egr-ref').value.trim();
  if(!concepto||!monto){alert('Concepto y monto son requeridos');return;}
  if(!fecha){fecha=new Date().toISOString().substring(0,10);}
  var r=await fetch('/api/financiero/egresos',_fetchOpts('POST', {fecha:fecha,empresa:empresa,categoria:cat,concepto:concepto,monto:monto,referencia:ref}));
  var d=await r.json();
  document.getElementById('egr-msg').innerHTML=r.ok?'<span style="color:var(--cx-danger-text);">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
  if(r.ok){document.getElementById('egr-concepto').value='';document.getElementById('egr-monto').value='';document.getElementById('egr-ref').value='';loadEgresos();}
}

async function limpiarFlujo(){
  if(!confirm('⚠ Esto eliminara TODOS los registros de egresos e ingresos del flujo de caja.\\n\\n¿Estas seguro?')) return;
  if(!confirm('Segunda confirmación: ¿BORRAR definitivamente todos los registros de flujo?')) return;
  var msg=document.getElementById('limpiar-msg');
  msg.textContent='Eliminando...'; msg.style.color='#f59e0b';
  try{
    var r=await fetch('/api/financiero/limpiar-flujo',_fetchOpts('POST', {confirmar:'LIMPIAR_TODO'}));
    var d=await r.json();
    if(d.ok){
      msg.textContent='✅ '+d.message; msg.style.color='#4ade80';
      setTimeout(()=>loadDashboard(),800);   // `loadKPIs` no existe en esta pantalla (M146)
    } else {
      msg.textContent='❌ '+(d.error||'Error'); msg.style.color='#f87171';
    }
  }catch(e){
    msg.textContent='❌ Error de conexión'; msg.style.color='#f87171';
  }
}

async function importarOCs(){
  var r=await fetch('/api/financiero/importar-ocs',_fetchOpts('POST'));
  var d=await r.json();
  document.getElementById('import-msg').innerHTML=r.ok?'<span style="color:var(--cx-primary-text);">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  if(r.ok)loadEgresos();
}

// ─── Shopify sync ────────────────────────────────────────────────────────
async function loadShopifyStatus(){
  try {
    var r = await fetch('/api/financiero/sync-shopify-status');
    var d = await r.json();
    if (!r.ok) {
      document.getElementById('shopify-sync-status').innerHTML =
        '<span style="color:#fca5a5;">' + (d.error||'Error') + '</span>';
      return;
    }
    var fmt = function(n) { return (n||0).toLocaleString('es-CO'); };
    document.getElementById('shopify-sync-status').innerHTML =
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">' +
        '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;">Pendientes de sync</div>' +
          '<div style="font-size:1.4em;font-weight:700;color:var(--cx-accent);">' + d.pendientes_count + '</div>' +
          '<div style="font-size:11px;color:var(--cx-text-faint);">$' + fmt(d.pendientes_total) + ' COP</div></div>' +
        '<div><div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;">Ya sincronizados</div>' +
          '<div style="font-size:1.4em;font-weight:700;color:#34d399;">' + d.sincronizados_count + '</div>' +
          '<div style="font-size:11px;color:var(--cx-text-faint);">$' + fmt(d.sincronizados_total) + ' COP - ult: ' + (d.ultimo_sync_fecha||'nunca') + '</div></div>' +
      '</div>';
  } catch(e) {
    document.getElementById('shopify-sync-status').textContent = 'Error: ' + e.message;
  }
}

async function syncShopifyDryRun() {
  var msg = document.getElementById('shopify-sync-msg');
  msg.innerHTML = '<span style="color:var(--cx-text-faint);">Calculando...</span>';
  var r = await fetch('/api/financiero/sync-shopify-ingresos', _fetchOpts('POST', {dry_run: true, solo_pagados: true}));
  var d = await r.json();
  if (!r.ok) { msg.innerHTML = '<span style="color:#fca5a5;">' + (d.error||'Error') + '</span>'; return; }
  msg.innerHTML = '<span style="color:#22d3ee;">📋 Se importarían ' + d.pendientes +
    ' pedidos por $' + (d.total_a_importar||0).toLocaleString('es-CO') + ' COP. ' +
    'Click "Sincronizar ahora" para ejecutar.</span>';
}

async function syncShopifyEjecutar() {
  var confirmMsg = 'Sincronizar pedidos Shopify pagados a flujo_ingresos? Idempotente: re-ejecutable sin duplicar. Solo importa orders no marcadas como sincronizadas.';
  if (!confirm(confirmMsg)) return;
  var msg = document.getElementById('shopify-sync-msg');
  var btnDis = document.querySelectorAll('#shopify-sync-status ~ div button');
  btnDis.forEach(function(b){b.disabled=true;});
  msg.innerHTML = '<span style="color:var(--cx-text-faint);">Sincronizando...</span>';
  var r = await fetch('/api/financiero/sync-shopify-ingresos', _fetchOpts('POST', {solo_pagados: true}));
  var d = await r.json();
  btnDis.forEach(function(b){b.disabled=false;});
  if (!r.ok) { msg.innerHTML = '<span style="color:#fca5a5;">' + (d.error||'Error') + '</span>'; return; }
  msg.innerHTML = '<span style="color:#34d399;">✓ ' + d.mensaje + '</span>';
  loadShopifyStatus(); loadIngresos();
}

// Cargar estado al abrir tab
document.addEventListener('DOMContentLoaded', function(){ setTimeout(loadShopifyStatus, 500); });

async function loadPreciosMayorista(){
  try{
    var r=await fetch('/api/financiero/precios-mayorista');
    var data=await r.json();
    if(!data.length){document.getElementById('precios-list').innerHTML='<p style="color:#9C8B7A;font-size:0.88em;">Sin SKUs registrados.</p>';return;}
    var h='<table style="width:100%;border-collapse:collapse;font-size:0.88em;">';
    h+='<thead><tr style="border-bottom:2px solid var(--cx-border-soft);">';
    h+='<th style="text-align:left;padding:8px 6px;color:var(--cx-text-soft);">SKU</th>';
    h+='<th style="text-align:left;padding:8px 6px;color:var(--cx-text-soft);">Producto</th>';
    h+='<th style="text-align:right;padding:8px 6px;color:var(--cx-text-soft);">Precio Mayorista (COP)</th>';
    h+='<th style="text-align:center;padding:8px 6px;color:var(--cx-text-soft);">Unidad</th>';
    h+='<th style="padding:8px 6px;"></th>';
    h+='</tr></thead><tbody>';
    data.forEach(function(s){
      h+='<tr style="border-bottom:1px solid #f0f0f0;">';
      h+='<td style="padding:8px 6px;font-family:monospace;color:var(--cx-primary-text);font-weight:700;">'+s.sku+'</td>';
      h+='<td style="padding:8px 6px;">'+s.descripcion+'</td>';
      h+='<td style="padding:8px 6px;text-align:right;"><input type="number" id="pm-'+s.sku+'" value="'+(s.precio_mayorista||0)+'" min="0" step="100" style="width:120px;padding:5px 8px;border:1px solid var(--cx-border);border-radius:6px;text-align:right;font-size:0.95em;"></td>';
      h+='<td style="padding:8px 6px;text-align:center;color:var(--cx-text-mute);">'+s.unidad+'</td>';
      h+='<td style="padding:8px 6px;"><button onclick="guardarPrecio(&apos;'+s.sku+'&apos;)" style="padding:5px 12px;background:var(--cx-primary);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Guardar</button></td>';
      h+='</tr>';
    });
    h+='</tbody></table>';
    document.getElementById('precios-list').innerHTML=h;
  }catch(e){document.getElementById('precios-list').innerHTML='<p style="color:red;">Error cargando precios.</p>';}
}

async function guardarPrecio(sku){
  var input=document.getElementById('pm-'+sku);
  if(!input)return;
  var precio=parseFloat(input.value)||0;
  var r=await fetch('/api/financiero/precios-mayorista/'+encodeURIComponent(sku),_fetchOpts('POST', {precio_mayorista:precio}));
  var d=await r.json();
  var msg=document.getElementById('precios-msg');
  msg.innerHTML=r.ok?'<span style="color:var(--cx-primary-text);">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  setTimeout(function(){msg.innerHTML='';},2500);
}

// Init

var _ccLoteActual = null;







// Firma electrónica Part 11 §11.200 · re-autenticación + signature_id sobre el
// movimiento. Devuelve {signature_id}, {error}, o null si el usuario cancela.










var _conteoActivo = null;
var _conteoItems = [];

















var _chartPNL = null;

async function loadPNL(){
  try{
    var d=await fetch('/api/financiero/pnl').then(function(r){return r.json();});
    var fmt2=function(n){if(!n&&n!==0)return '-';return '$'+Math.abs(parseFloat(n)||0).toLocaleString('es-CO',{maximumFractionDigits:0});};
    var tot=d.empresas&&d.empresas['TOTAL']||{};
    var ytd=d.ytd||{}; var mvp=d.mes_vs_prior||{};
    var crec=ytd.crecimiento_pct;
    var crecMes=mvp.crecimiento_pct;
    // KPI cards
    var kh='';
    kh+='<div style="background:rgba(109,40,217,0.12);border:1px solid rgba(109,40,217,0.3);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:var(--cx-primary-text);">'+fmt2(tot.ingresos)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">Ingresos este mes</div>';
    if(crecMes!=null) kh+='<div style="font-size:0.75em;color:'+(crecMes>=0?'#27ae60':'#e74c3c');
    if(crecMes!=null) kh+=';margin-top:3px;">'+(crecMes>=0?'&#8593;':'&#8595;')+Math.abs(crecMes)+'% vs mismo mes año ant.</div>';
    kh+='</div>';
    kh+='<div style="background:rgba(192,57,43,0.08);border:1px solid rgba(192,57,43,0.2);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:var(--cx-danger-text);">'+fmt2(tot.egresos)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">Egresos este mes</div></div>';
    kh+='<div style="background:rgba(39,174,96,0.1);border:1px solid rgba(39,174,96,0.25);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:#27ae60;">'+fmt2(tot.margen)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">Margen mes ('+( tot.margen_pct||0)+'%)</div></div>';
    kh+='<div style="background:rgba(52,152,219,0.1);border:1px solid rgba(52,152,219,0.25);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:#3498db;">'+fmt2(ytd.ingresos)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">Ingresos YTD</div>';
    if(crec!=null) kh+='<div style="font-size:0.75em;color:'+(crec>=0?'#27ae60':'#e74c3c')+';margin-top:3px;">'+(crec>=0?'&#8593;':'&#8595;')+Math.abs(crec)+'% vs año anterior</div>';
    kh+='</div>';
    kh+='<div style="background:rgba(155,89,182,0.1);border:1px solid rgba(155,89,182,0.25);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:#9b59b6;">'+fmt2(d.nomina_mes)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">Nomina mes</div></div>';
    kh+='<div style="background:rgba(230,126,34,0.1);border:1px solid rgba(230,126,34,0.25);border-radius:10px;padding:16px;text-align:center;">';
    kh+='<div style="font-size:1.8em;font-weight:900;color:#e67e22;">'+fmt2(d.ebitda)+'</div>';
    kh+='<div style="font-size:0.72em;color:rgba(0,0,0,0.5);text-transform:uppercase;margin-top:4px;">EBITDA aprox.</div></div>';
    document.getElementById('pnl-kpis').innerHTML=kh;
    // Brands
    var bh='';
    ['ANIMUS','ESPAGIRIA'].forEach(function(k){
      var b=d.empresas&&d.empresas[k]||{};
      bh+='<div style="background:#f8f9fa;border:1px solid #e9ecef;border-radius:10px;padding:16px;">';
      bh+='<div style="font-weight:700;font-size:0.9em;color:var(--cx-primary-text);margin-bottom:12px;">'+k+'</div>';
      bh+='<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #e9ecef;"><span style="color:var(--cx-text-mute);">Ingresos mes</span><span style="font-weight:700;">'+fmt2(b.ingresos)+'</span></div>';
      bh+='<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #e9ecef;"><span style="color:var(--cx-text-mute);">YTD</span><span style="font-weight:700;color:#3498db;">'+fmt2(b.ingresos_ytd)+'</span></div>';
      bh+='<div style="display:flex;justify-content:space-between;padding:6px 0;"><span style="color:var(--cx-text-mute);">Margen</span><span style="font-weight:700;color:#27ae60;">'+fmt2(b.margen)+'</span></div>';
      bh+='</div>';
    });
    document.getElementById('pnl-brands').innerHTML=bh;
    // Chart
    if(d.historico&&d.historico.length){
      var labels=d.historico.map(function(h){return h.periodo;});
      var ings=d.historico.map(function(h){return h.ingresos||0;});
      var egrs=d.historico.map(function(h){return h.egresos||0;});
      var mars=d.historico.map(function(h){return h.margen||0;});
      if(_chartPNL)_chartPNL.destroy();
      _chartPNL=new Chart(document.getElementById('pnl-chart'),{
        type:'bar',
        data:{labels:labels,datasets:[
          {label:'Ingresos',data:ings,backgroundColor:'rgba(109,40,217,0.7)',borderRadius:4},
          {label:'Egresos',data:egrs,backgroundColor:'rgba(192,57,43,0.5)',borderRadius:4},
          {label:'Margen',data:mars,type:'line',borderColor:'#27ae60',backgroundColor:'rgba(39,174,96,0.1)',tension:0.3,fill:true}
        ]},
        options:{responsive:true,plugins:{legend:{position:'top'}},scales:{y:{ticks:{callback:function(v){return '$'+Math.round(v/1000000)+'M';}}}}}
      });
    }
  }catch(e){console.error('loadPNL:',e);}
}

var _chartAR=null;
// Las tres pestanas de abajo (AP, AR, Working Capital) abrian EN BLANCO: el JS escribia en
// `ap-content` / `ar-content` / `wc-content` y el HTML tiene `ap-table`, `ar-table`, `wc-kpis`.
// Los dos lados se renombraron por separado y el `if(!el) return` lo hacia fallar EN SILENCIO --
// una pestana vacia se lee como "no hay datos", que es lo contrario de lo que pasaba (M100/M112).
// Ahora se resuelve contra los nombres posibles y, si no hay NINGUNO, se dice.
function _finCont(base, etiqueta){
  var cands=[base+'-content', base+'-table', base+'-kpis', base+'-ccc'];
  for(var i=0;i<cands.length;i++){
    var el=document.getElementById(cands[i]);
    if(el) return el;
  }
  console.warn('[financiero] no encontre donde pintar ' + (etiqueta||base));
  return null;
}
function _finSinDonde(base, etiqueta){
  // Si de verdad no hay contenedor, la pantalla lo DICE en vez de quedarse muda.
  var p=document.getElementById('page-'+base);
  if(p) p.insertAdjacentHTML('beforeend',
    '<div style="background:var(--cx-danger-pale);color:var(--cx-danger-text);border-radius:10px;'
    + 'padding:12px 14px;font-size:13px;margin-top:10px">No pude pintar ' + (etiqueta||base)
    + ': falta el contenedor en la pantalla.</div>');
}

async function loadARaging(){
  try{
    var d=await fetch('/api/financiero/ar-aging').then(function(r){return r.json();});
    var fmt2=function(n){return '$'+Math.abs(parseFloat(n||0)).toLocaleString('es-CO',{maximumFractionDigits:0});};
    var el=_finCont('ar','Cuentas por Cobrar');
    if(!el){ _finSinDonde('ar','Cuentas por Cobrar'); return; }
    var bk=d.buckets||{};
    var h='<table style="width:100%;border-collapse:collapse;font-size:0.88em;">';
    h+='<tr style="background:#f8f9fa;"><th style="text-align:left;padding:8px;">Bucket</th><th style="text-align:right;padding:8px;">Total</th><th style="text-align:right;padding:8px;"># Pedidos</th></tr>';
    var buckets=[['corriente','Corriente (0-30d)','#27ae60'],['dias_30','31-60 dias','#e67e22'],['dias_60','61-90 dias','#e74c3c'],['dias_90','>90 dias','#8e44ad']];
    buckets.forEach(function(b){
      var bdata=bk[b[0]]||{};
      h+='<tr style="border-bottom:1px solid #e9ecef;"><td style="padding:8px;color:'+b[2]+';">'+b[1]+'</td>';
      h+='<td style="text-align:right;padding:8px;font-weight:700;">'+fmt2(bdata.total)+'</td>';
      h+='<td style="text-align:right;padding:8px;">'+(bdata.count||0)+'</td></tr>';
    });
    h+='<tr style="font-weight:900;background:#f8f9fa;"><td style="padding:8px;">TOTAL AR</td><td style="text-align:right;padding:8px;">'+fmt2(d.ar_total)+'</td><td style="text-align:right;padding:8px;">'+(d.count||0)+'</td></tr>';
    h+='</table>';
    el.innerHTML=h;
  }catch(e){console.error('loadARaging:',e);}
}

var _chartAP=null;
async function loadAPaging(){
  try{
    var d=await fetch('/api/financiero/ap-aging').then(function(r){return r.json();});
    var fmt2=function(n){return '$'+Math.abs(parseFloat(n||0)).toLocaleString('es-CO',{maximumFractionDigits:0});};
    var el=_finCont('ap','Cuentas por Pagar');
    if(!el){ _finSinDonde('ap','Cuentas por Pagar'); return; }
    var bk=d.buckets||{};
    var h='<table style="width:100%;border-collapse:collapse;font-size:0.88em;">';
    h+='<tr style="background:#f8f9fa;"><th style="text-align:left;padding:8px;">Bucket</th><th style="text-align:right;padding:8px;">Total</th><th style="text-align:right;padding:8px;"># OCs</th></tr>';
    var buckets=[['corriente','Corriente (0-30d)','#27ae60'],['dias_30','31-60 dias','#e67e22'],['dias_60','61-90 dias','#e74c3c'],['dias_90','>90 dias','#8e44ad']];
    buckets.forEach(function(b){
      var bdata=bk[b[0]]||{};
      h+='<tr style="border-bottom:1px solid #e9ecef;"><td style="padding:8px;color:'+b[2]+';">'+b[1]+'</td>';
      h+='<td style="text-align:right;padding:8px;font-weight:700;">'+fmt2(bdata.total)+'</td>';
      h+='<td style="text-align:right;padding:8px;">'+(bdata.count||0)+'</td></tr>';
    });
    h+='<tr style="font-weight:900;background:#f8f9fa;"><td style="padding:8px;">TOTAL AP</td><td style="text-align:right;padding:8px;">'+fmt2(d.ap_total)+'</td><td style="text-align:right;padding:8px;">'+(d.count||0)+'</td></tr>';
    h+='</table>';
    el.innerHTML=h;
  }catch(e){console.error('loadAPaging:',e);}
}

async function loadWorkingCapital(){
  try{
    var d=await fetch('/api/financiero/working-capital').then(function(r){return r.json();});
    var fmt2=function(n){return '$'+Math.abs(parseFloat(n||0)).toLocaleString('es-CO',{maximumFractionDigits:0});};
    var el=_finCont('wc','Capital de Trabajo');
    if(!el){ _finSinDonde('wc','Capital de Trabajo'); return; }
    var wc=d.working_capital||0;
    var h='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px;">';
    var cards=[
      ['Working Capital',fmt2(wc),wc>=0?'#27ae60':'#e74c3c'],
      ['AR Total',fmt2(d.ar_total),'#6d28d9'],
      ['AP Total',fmt2(d.ap_total),'#e67e22'],
      ['Inventario MP',fmt2(d.inventory_value),'#3498db'],
      ['Caja',fmt2(d.cash),'#9b59b6'],
      ['Burn Rate/mes',fmt2(d.burn_rate),'#e74c3c'],
      ['Runway',d.runway_meses?(d.runway_meses.toFixed(1)+' meses'):'-','#27ae60'],
    ];
    cards.forEach(function(c){
      h+='<div style="background:#f8f9fa;border:1px solid #e9ecef;border-radius:8px;padding:12px;text-align:center;">';
      h+='<div style="font-size:1.3em;font-weight:900;color:'+c[2]+';">'+c[1]+'</div>';
      h+='<div style="font-size:0.72em;color:var(--cx-text-mute);text-transform:uppercase;margin-top:4px;">'+c[0]+'</div></div>';
    });
    h+='</div>';
    h+='<table style="width:100%;border-collapse:collapse;font-size:0.88em;">';
    h+='<tr style="background:#f8f9fa;"><th style="text-align:left;padding:8px;">Métrica</th><th style="text-align:right;padding:8px;">Valor</th></tr>';
    [['DSO (días cobro)',d.dso?d.dso.toFixed(0)+'d':'-'],['DPO (días pago)',d.dpo?d.dpo.toFixed(0)+'d':'-'],['DIO (días inventario)',d.dio?d.dio.toFixed(0)+'d':'-'],['CCC (ciclo caja)',d.ccc?d.ccc.toFixed(0)+'d':'-']].forEach(function(r){
      h+='<tr style="border-bottom:1px solid #e9ecef;"><td style="padding:8px;">'+r[0]+'</td><td style="text-align:right;padding:8px;font-weight:700;">'+r[1]+'</td></tr>';
    });
    h+='</table>';
    el.innerHTML=h;
  }catch(e){console.error('loadWorkingCapital:',e);}
}
document.addEventListener('DOMContentLoaded',function(){
  var hoy=new Date().toISOString().substring(0,10);
  var ingFecha=document.getElementById('ing-fecha');if(ingFecha)ingFecha.value=hoy;
  var egrFecha=document.getElementById('egr-fecha');if(egrFecha)egrFecha.value=hoy;
  loadConfig().then(function(){loadDashboard();});   // `cargarOCsPendientes()` se llamaba
  // aca y NO EXISTE: quedo viva la llamada de una seccion que se podo (M112). Adentro de
  // un `.then()` sin `.catch`, el ReferenceError es una promesa rechazada en SILENCIO --
  // ni un error en pantalla ni nada que reportar. No hay ninguna seccion de OCs
  // pendientes en esta pantalla, asi que se retira el par completo, no una punta sola.
});

// ─── Drill-down modal: detalle de mes por categoría ─────────────────
async function abrirMesDetalle(periodo, tipo){
  var modal = document.getElementById('mes-detalle-modal');
  document.getElementById('md-titulo').textContent = (tipo==='ingresos'?'Ingresos':'Egresos')+' · '+periodo;
  document.getElementById('md-body').innerHTML = '<div style="padding:30px;text-align:center;color:var(--cx-text-faint)">Cargando…</div>';
  modal.style.display = 'flex';
  try{
    var url = '/api/financiero/mes-detalle?periodo='+encodeURIComponent(periodo)+'&tipo='+encodeURIComponent(tipo);
    var r = await fetch(url);
    if(!r.ok){
      document.getElementById('md-body').innerHTML = '<div style="padding:20px;color:var(--cx-danger-text)">Error '+r.status+'</div>';
      return;
    }
    var d = await r.json();
    var html = '<div style="padding:14px 20px;background:#F5F0E8;border-radius:8px;margin-bottom:14px;font-size:0.95em">';
    html += '<b>Total '+tipo+'</b>: '+fmt(d.total)+' · <b>'+d.count+'</b> transacciones · <b>'+d.categorias.length+'</b> categorías';
    html += '</div>';
    if(!d.categorias.length){
      html += '<div style="padding:30px;text-align:center;color:var(--cx-text-faint);font-style:italic">Sin movimientos en '+periodo+'</div>';
    }else{
      d.categorias.forEach(function(cat, idx){
        var color = tipo==='ingresos' ? '#6d28d9' : '#c0392b';
        // Header clickeable que toggea el trend inline
        var trendId = 'trend-'+idx+'-'+Math.random().toString(36).slice(2,7);
        var toggle = 'toggleCategoriaTrend("'+trendId+'","'+_esc(cat.categoria)+'","'+tipo+'")';
        html += '<div style="margin-bottom:18px;border:1px solid var(--cx-border);border-radius:10px;overflow:hidden">';
        html += '<div style="padding:12px 16px;background:#FAFAF7;display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick=\\\''+toggle+'\\\' title="Click para ver tendencia 12 meses">';
        html += '<div><b style="color:'+color+'">'+_esc(cat.categoria)+'</b> <span style="color:var(--cx-text-faint);font-size:0.78em;margin-left:6px">📈 ver 12m</span> · <span style="color:#7A6A55;font-size:0.88em">'+cat.count+' tx · '+cat.pct.toFixed(1)+'%</span></div>';
        html += '<div style="font-weight:700;color:'+color+';font-size:1.05em">'+fmt(cat.monto)+'</div>';
        html += '</div>';
        // Slot del trend chart (oculto inicialmente)
        html += '<div id="'+trendId+'" style="display:none;padding:14px 16px;background:#FCFAF7;border-top:1px dashed var(--cx-border)"></div>';
        if(cat.top_items && cat.top_items.length){
          html += '<table style="width:100%;font-size:0.85em;border-collapse:collapse">';
          html += '<thead><tr style="background:#FAFAF7;color:#7A6A55"><th style="padding:6px 12px;text-align:left;font-size:0.78em;text-transform:uppercase">Fecha</th><th style="padding:6px 12px;text-align:left;font-size:0.78em;text-transform:uppercase">Concepto</th><th style="padding:6px 12px;text-align:right;font-size:0.78em;text-transform:uppercase">Monto</th><th style="padding:6px 12px;text-align:left;font-size:0.78em;text-transform:uppercase">Ref</th></tr></thead><tbody>';
          cat.top_items.forEach(function(it){
            var refLink = it.referencia || '';
            // Si es OC, link al tab de OCs
            if(refLink && /^OC-/.test(refLink)){
              refLink = '<a href="/compras#oc-'+_esc(refLink)+'" style="color:var(--cx-primary-text);text-decoration:none">'+_esc(refLink)+'</a>';
            }else if(refLink){
              refLink = '<span style="color:#7A6A55;font-size:0.82em">'+_esc(refLink)+'</span>';
            }else{
              refLink = '<span style="color:#bbb">-</span>';
            }
            html += '<tr style="border-top:1px solid #F5F0E8">';
            html += '<td style="padding:6px 12px;color:#7A6A55">'+_esc((it.fecha||'').substring(0,10))+'</td>';
            html += '<td style="padding:6px 12px">'+_esc(it.concepto)+'</td>';
            html += '<td style="padding:6px 12px;text-align:right;font-weight:600">'+fmt(it.monto)+'</td>';
            html += '<td style="padding:6px 12px;font-size:0.82em">'+refLink+'</td>';
            html += '</tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      });
    }
    document.getElementById('md-body').innerHTML = html;
  }catch(e){
    document.getElementById('md-body').innerHTML = '<div style="padding:20px;color:var(--cx-danger-text)">Error red: '+_esc(e.message)+'</div>';
  }
}

function cerrarMesDetalle(){
  var m = document.getElementById('mes-detalle-modal');
  if(m) m.style.display = 'none';
}

// Track de charts por slot id para destruir antes de recrear
var _categoriaTrendCharts = {};

async function toggleCategoriaTrend(slotId, categoria, tipo){
  var slot = document.getElementById(slotId);
  if(!slot) return;
  // Si ya está abierto, cerrar
  if(slot.style.display !== 'none' && slot.dataset.loaded === '1'){
    slot.style.display = 'none';
    return;
  }
  slot.style.display = 'block';
  slot.innerHTML = '<div style="text-align:center;color:var(--cx-text-faint);font-size:0.85em;padding:14px">Cargando tendencia 12 meses…</div>';
  try{
    var url = '/api/financiero/categoria-trend?categoria='+encodeURIComponent(categoria)+'&tipo='+encodeURIComponent(tipo);
    var r = await fetch(url);
    if(!r.ok){
      slot.innerHTML = '<div style="color:var(--cx-danger-text);font-size:0.85em;padding:8px">Error '+r.status+'</div>';
      return;
    }
    var d = await r.json();
    var s = d.stats || {};
    var color = tipo === 'ingresos' ? '#6d28d9' : '#c0392b';
    // Stats summary
    var statsLine = [];
    if(s.promedio !== undefined) statsLine.push('📊 Promedio: <b>'+fmt(s.promedio)+'</b>');
    if(s.max_mes) statsLine.push('🏔️ Pico: <b>'+s.max_mes+'</b> ('+fmt(s.max_monto)+')');
    if(s.min_mes && s.min_monto > 0) statsLine.push('🟦 Mínimo: <b>'+s.min_mes+'</b> ('+fmt(s.min_monto)+')');
    if(s.ultimo_vs_promedio_pct !== null && s.ultimo_vs_promedio_pct !== undefined){
      var arrow = s.ultimo_vs_promedio_pct >= 0 ? '▲' : '▼';
      var c2 = s.ultimo_vs_promedio_pct >= 0 ? (tipo==='egresos'?'#c0392b':'#6d28d9') : (tipo==='egresos'?'#6d28d9':'#c0392b');
      statsLine.push('Último vs prom: <b style="color:'+c2+'">'+arrow+' '+s.ultimo_vs_promedio_pct.toFixed(1)+'%</b>');
    }
    var canvasId = slotId+'-canvas';
    slot.innerHTML = '<div style="font-size:0.85em;color:#7A6A55;margin-bottom:10px">'+statsLine.join(' · ')+'</div>'
      +'<canvas id="'+canvasId+'" height="80" style="max-height:200px"></canvas>';
    slot.dataset.loaded = '1';

    // Render chart line
    var labels = d.meses.map(function(m){return m.periodo.slice(2);});  // YY-MM
    var montos = d.meses.map(function(m){return m.monto;});
    if(_categoriaTrendCharts[slotId]) _categoriaTrendCharts[slotId].destroy();
    _categoriaTrendCharts[slotId] = new Chart(document.getElementById(canvasId), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: categoria,
          data: montos,
          borderColor: color,
          backgroundColor: color+'33',  // 20% alpha
          tension: 0.25, fill: true, pointRadius: 3, borderWidth: 2,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {legend: {display: false}},
        scales: {y: {ticks: {callback: function(v){return fmt(v);}}}},
      }
    });
  }catch(e){
    slot.innerHTML = '<div style="color:var(--cx-danger-text);font-size:0.85em;padding:8px">Error red: '+_esc(e.message)+'</div>';
  }
}

// helper escape (puede ya existir; redefinir es seguro)
function _esc(s){
  return String(s||'').replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}
</script>

<!-- Mes-detalle modal · drill-down de ingresos/egresos por categoría -->
<div id="mes-detalle-modal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,0.65);z-index:9999;align-items:flex-start;justify-content:center;padding:50px 20px;overflow-y:auto">
  <div style="background:var(--cx-card);max-width:780px;width:100%;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.35);overflow:hidden">
    <div style="padding:18px 24px;background:linear-gradient(135deg,#6d28d9,#205C5A);color:#fff;display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:11px;color:#a7f3d0;text-transform:uppercase;letter-spacing:.5px">Detalle del mes</div>
        <h2 id="md-titulo" style="margin:4px 0 0 0;font-size:18px">-</h2>
      </div>
      <button onclick="cerrarMesDetalle()" style="background:rgba(255,255,255,0.15);color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:14px;font-weight:700">✕ Cerrar</button>
    </div>
    <div id="md-body" style="padding:20px 24px;max-height:75vh;overflow-y:auto"></div>
  </div>
</div>
</body>
</html>"""
