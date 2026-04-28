MARKETING_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Marketing — HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;font-size:14px;}
::-webkit-scrollbar{width:6px;height:6px;}::-webkit-scrollbar-track{background:#1e293b;}::-webkit-scrollbar-thumb{background:#475569;border-radius:3px;}

/* ─── Header ─── */
.hdr{background:#1e293b;border-bottom:1px solid #334155;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.hdr-brand{display:flex;align-items:center;gap:10px;}
.hdr-brand h1{font-size:16px;font-weight:800;color:#fff;}
.hdr-brand span{font-size:11px;color:#94a3b8;background:#0f172a;padding:2px 8px;border-radius:20px;border:1px solid #334155;}
.hdr-user{font-size:12px;color:#64748b;}
.hdr-user strong{color:#e2e8f0;}
.back-link{font-size:12px;color:#667eea;text-decoration:none;display:flex;align-items:center;gap:4px;}
.back-link:hover{color:#818cf8;}

/* ─── Tabs ─── */
.tabs-bar{background:#1e293b;border-bottom:1px solid #334155;display:flex;overflow-x:auto;padding:0 20px;}
.tab-btn{padding:12px 20px;font-size:13px;font-weight:600;color:#64748b;border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab-btn:hover{color:#e2e8f0;}
.tab-btn.active{color:#667eea;border-bottom-color:#667eea;}
.tab-panel{display:none;padding:24px 20px;}
.tab-panel.active{display:block;}

/* ─── Cards & Layout ─── */
.page-title{font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:4px;}
.page-sub{font-size:12px;color:#64748b;margin-bottom:24px;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;margin-bottom:24px;}
.kpi-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;}
.kpi-label{font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}
.kpi-val{font-size:24px;font-weight:800;color:#f1f5f9;line-height:1;}
.kpi-sub{font-size:11px;color:#64748b;margin-top:4px;}
.kpi-card.green .kpi-val{color:#34d399;}
.kpi-card.red .kpi-val{color:#f87171;}
.kpi-card.blue .kpi-val{color:#60a5fa;}
.kpi-card.yellow .kpi-val{color:#fbbf24;}
.kpi-card.purple .kpi-val{color:#a78bfa;}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
@media(max-width:800px){.grid2,.grid3{grid-template-columns:1fr;}}

.card{background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden;}
.card-hdr{padding:14px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #334155;}
.card-title{font-size:13px;font-weight:700;color:#f1f5f9;}
.card-body{padding:16px;}

/* ─── Table ─── */
.tbl-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;}
th{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px;padding:10px 12px;text-align:left;background:#0f172a;border-bottom:1px solid #334155;}
td{padding:10px 12px;border-bottom:1px solid #1e293b;font-size:13px;}
tr:hover td{background:#263348;}
.empty-row td{text-align:center;color:#64748b;padding:32px;}

/* ─── Badges ─── */
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;}
.badge-green{background:#052e16;color:#34d399;border:1px solid #065f46;}
.badge-blue{background:#0c1a4d;color:#60a5fa;border:1px solid #1e3a8a;}
.badge-yellow{background:#2d1a00;color:#fbbf24;border:1px solid #78350f;}
.badge-red{background:#2d0000;color:#f87171;border:1px solid #7f1d1d;}
.badge-gray{background:#1e293b;color:#94a3b8;border:1px solid #334155;}
.badge-purple{background:#1e0a3c;color:#a78bfa;border:1px solid #4c1d95;}

/* ─── Buttons ─── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;}
.btn-primary:hover{opacity:.9;}
.btn-sm{padding:5px 12px;font-size:12px;}
.btn-outline{background:transparent;border:1px solid #334155;color:#94a3b8;}
.btn-outline:hover{border-color:#475569;color:#e2e8f0;}
.btn-danger{background:#7f1d1d;color:#fca5a5;}
.btn-danger:hover{background:#991b1b;}
.btn-agent{background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #4c1d95;color:#a78bfa;width:100%;padding:14px;font-size:14px;font-weight:700;border-radius:10px;cursor:pointer;transition:.2s;display:flex;align-items:center;justify-content:center;gap:8px;}
.btn-agent:hover{background:linear-gradient(135deg,#4c1d95,#1e293b);border-color:#7c3aed;}
.btn-agent.running{opacity:.6;cursor:not-allowed;}

/* ─── Forms ─── */
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.form-row.full{grid-template-columns:1fr;}
.form-group{display:flex;flex-direction:column;gap:4px;}
label{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.4px;}
input,select,textarea{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px 12px;color:#e2e8f0;font-size:13px;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#667eea;}
textarea{resize:vertical;min-height:80px;}

/* ─── Modal ─── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;}
.modal-bg.open{display:flex;}
.modal{background:#1e293b;border:1px solid #334155;border-radius:16px;width:min(600px,95vw);max-height:90vh;overflow-y:auto;padding:24px;}
.modal-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.modal-title{font-size:16px;font-weight:700;color:#f1f5f9;}
.modal-close{background:none;border:none;color:#64748b;cursor:pointer;font-size:20px;padding:4px;}
.modal-close:hover{color:#f87171;}

/* ─── Agent cards ─── */
.agents-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.agent-card{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:20px;}
.agent-icon{font-size:32px;margin-bottom:12px;}
.agent-name{font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:4px;}
.agent-desc{font-size:12px;color:#64748b;margin-bottom:16px;line-height:1.5;}
.agent-result{margin-top:16px;background:#0f172a;border-radius:8px;padding:14px;font-size:12px;color:#94a3b8;max-height:240px;overflow-y:auto;display:none;}
.agent-result.show{display:block;}
.agent-result pre{white-space:pre-wrap;word-break:break-word;font-family:'Segoe UI',sans-serif;font-size:12px;}

/* ─── Progress bar ─── */
.progress-bar{background:#0f172a;border-radius:4px;height:8px;overflow:hidden;}
.progress-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#667eea,#764ba2);transition:width .5s;}

/* ─── Alert ─── */
.alert{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;}
.alert-success{background:#052e16;color:#34d399;border:1px solid #065f46;}
.alert-error{background:#2d0000;color:#f87171;border:1px solid #7f1d1d;}
.alert-info{background:#0c1a4d;color:#60a5fa;border:1px solid #1e3a8a;}

/* ─── Spinner ─── */
.spin{display:inline-block;width:16px;height:16px;border:2px solid #334155;border-top-color:#667eea;border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}

/* ─── Trend item ─── */
.trend-item{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1e293b;}
.trend-item:last-child{border-bottom:none;}
.trend-sku{font-weight:700;color:#e2e8f0;font-size:13px;}
.trend-bar{flex:1;margin:0 12px;}
.trend-pct{font-size:12px;font-weight:700;min-width:60px;text-align:right;}
.trend-up{color:#34d399;}
.trend-dn{color:#f87171;}
.trend-flat{color:#94a3b8;}

/* ─── Topbar actions ─── */
.actions-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;}
.search-box{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;width:240px;}
.search-box:focus{outline:none;border-color:#667eea;}

/* ─── Content calendar ─── */
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:12px;}
.cal-day-hdr{text-align:center;font-size:10px;font-weight:700;color:#64748b;padding:6px 0;}
.cal-day{background:#0f172a;border-radius:6px;min-height:70px;padding:6px;position:relative;}
.cal-day-num{font-size:10px;color:#64748b;margin-bottom:4px;}
.cal-item{background:#4c1d95;border-radius:3px;padding:2px 4px;font-size:9px;color:#ddd6fe;margin-bottom:2px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.cal-item.published{background:#065f46;color:#6ee7b7;}
.cal-item.draft{background:#334155;color:#94a3b8;}
.cal-item.scheduled{background:#1e3a8a;color:#93c5fd;}
.platform-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;cursor:default;transition:all .2s;}
.pill-off{background:#1e293b;color:#475569;border:1px solid #334155;}
.pill-shopify{background:#0d2e1a;color:#34d399;border:1px solid #065f46;}
.pill-ghl{background:#1a1033;color:#a78bfa;border:1px solid #4c1d95;}
.pill-ig{background:#2d1520;color:#f9a8d4;border:1px solid #831843;}
</style>
</head>

<div id="toast-container" style="position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;"></div>
<!-- Banner de errores JS — visible para diagnosticar en prod cuando un botón
     no responde. Si ves este banner, hay un bug específico para reportar. -->
<div id="js-error-banner" style="display:none;position:fixed;top:0;left:0;right:0;z-index:10000;background:#7f1d1d;color:#fef2f2;padding:10px 16px;font-size:12px;font-family:monospace;border-bottom:2px solid #ef4444;"></div>
<script>
function showToast(msg, type) {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  const bg = type==='error'?'#7f1d1d':type==='success'?'#064e3b':type==='warning'?'#78350f':'#1e293b';
  const border = type==='error'?'#ef4444':type==='success'?'#10b981':type==='warning'?'#f59e0b':'#475569';
  t.style.cssText = `background:${bg};border:1px solid ${border};color:#f1f5f9;padding:12px 18px;border-radius:8px;font-size:13px;font-weight:600;min-width:220px;max-width:360px;box-shadow:0 4px 20px rgba(0,0,0,.4);pointer-events:auto;`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; t.style.transition='opacity .4s'; setTimeout(()=>t.remove(), 400); }, 3200);
}

// Captura errores globales y los muestra en banner para no esconder
// problemas silenciosos en producción.
window.addEventListener('error', function(ev) {
  try {
    const banner = document.getElementById('js-error-banner');
    if (!banner) return;
    const msg = (ev.message || ev.error?.message || 'Error desconocido') +
                ' @ ' + (ev.filename || '').split('/').pop() + ':' + (ev.lineno||'?');
    banner.style.display = 'block';
    banner.innerHTML = '⚠️ Error JS: ' + msg.substring(0, 280) +
      ' <button onclick="this.parentElement.style.display=\'none\'" style="float:right;background:transparent;border:1px solid #fca5a5;color:#fff;padding:1px 8px;border-radius:4px;cursor:pointer;font-size:11px;">cerrar</button>';
    console.error('[marketing] global error', ev);
  } catch (e) { /* swallow */ }
});
window.addEventListener('unhandledrejection', function(ev) {
  console.error('[marketing] unhandled rejection', ev.reason);
});
</script>
<body>

<div class="hdr">
  <div class="hdr-brand">
    <h1>&#x1F4E3; Marketing</h1>
    <span style="font-size:11px;color:#64748b;letter-spacing:1px;text-transform:uppercase;">HHA Group</span>
  </div>
  <div style="display:flex;align-items:center;gap:20px;">
    <a class="back-link" href="/modulos">&#x2190; Módulos</a>
    <div class="hdr-user">Usuario: <strong>{usuario}</strong></div>
  </div>
</div>

<div class="tabs-bar">
  <button class="tab-btn active" data-tab="dashboard" onclick="switchTab('dashboard')">&#x1F3AF; Dashboard</button>
  <button class="tab-btn" data-tab="campanas" onclick="switchTab('campanas')">&#x1F4E2; Campañas</button>
  <button class="tab-btn" data-tab="influencers" onclick="switchTab('influencers')">&#x1F465; Influencers</button>
  <button class="tab-btn" data-tab="pagos" onclick="switchTab('pagos')">&#x1F4B0; Pagos Realizados</button>
  <button class="tab-btn" data-tab="contenido" onclick="switchTab('contenido')">&#x1F4C5; Contenido</button>
  <button class="tab-btn" data-tab="inteligencia" onclick="switchTab('inteligencia')">&#x1F9E0; Inteligencia</button>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: DASHBOARD -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-dashboard" class="tab-panel active">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:6px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">&#x1F4CA; Marketing — Dashboard</div>
      <div class="page-sub" id="dash-fecha">Cargando...</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <div id="pill-shopify" class="platform-pill pill-off">🛍️ Shopify</div>
      <div id="pill-ghl" class="platform-pill pill-off">📋 GHL</div>
      <div id="pill-ig" class="platform-pill pill-off">📸 Instagram</div>
      <button id="btn-sync-shopify" class="btn btn-outline btn-sm" onclick="syncPlatform('shopify')">↻ Shopify</button>
      <button class="btn btn-outline btn-sm" style="color:#f59e0b;border-color:#f59e0b;font-size:10px;" onclick="syncPlatform('shopify',true)" title="Trae todo el historial">📥 Histórico</button>
      <button id="btn-sync-ghl" class="btn btn-outline btn-sm" onclick="syncPlatform('ghl')">↻ GHL</button>
      <button id="btn-sync-instagram" class="btn btn-outline btn-sm" onclick="syncPlatform('instagram')">↻ IG</button>
      <button class="btn btn-outline btn-sm" style="border-color:#e1306c;color:#e1306c;" onclick="refreshIgToken()">🔑 Renovar token IG</button>
      <span id="ig-token-status" style="font-size:10px;padding:2px 8px;border-radius:10px;display:none;"></span>
      <span id="sync-status" style="font-size:11px;color:#64748b;"></span>
    </div>
  </div>

  <!-- KPIs Shopify -->
  <div style="font-size:11px;font-weight:700;color:#d4af37;text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px;">🛍️ Shopify — Ventas reales</div>
  <div id="sh-cobertura-banner" style="display:none;background:#78350f;color:#fde68a;border-radius:8px;padding:8px 14px;font-size:11px;margin-bottom:10px;"></div>
<div class="kpi-grid" id="dash-shopify-kpis">
    <div class="kpi-card yellow"><div class="kpi-label" id="sh-rev30-label">Revenue</div><div class="kpi-val" id="sh-rev30">—</div><div class="kpi-sub" id="sh-rev7">vs período ant.: —</div></div>
    <div class="kpi-card blue"><div class="kpi-label" id="sh-ped30-label">Pedidos</div><div class="kpi-val" id="sh-ped30">—</div><div class="kpi-sub" id="sh-ped-total">Total: —</div></div>
    <div class="kpi-card green"><div class="kpi-label">Ticket promedio</div><div class="kpi-val" id="sh-ticket">—</div><div class="kpi-sub" id="sh-clientes">Clientes: —</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Clientes nuevos 30d</div><div class="kpi-val" id="sh-nuevos">—</div><div class="kpi-sub" id="sh-recurrentes">Recurrentes: —</div></div>
    <div class="kpi-card"><div class="kpi-label">Revenue total</div><div class="kpi-val" id="sh-rev-total" style="font-size:16px;">—</div><div class="kpi-sub">Histórico</div></div>
    <div class="kpi-card blue"><div class="kpi-label">Contactos GHL</div><div class="kpi-val" id="ghl-total">—</div><div class="kpi-sub" id="ghl-nuevos">Nuevos 30d: —</div></div>
  </div>

  <!-- Instagram KPIs -->
  <div style="font-size:11px;font-weight:700;color:#e1306c;text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px;">📸 Instagram — Engagement real</div>
  <div class="kpi-grid" id="dash-ig-kpis">
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Posts 30d</div><div class="kpi-val" id="ig-posts30">—</div><div class="kpi-sub" id="ig-posts-total">Total: —</div></div>
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Likes 30d</div><div class="kpi-val" id="ig-likes30">—</div><div class="kpi-sub" id="ig-avg-likes">Promedio: —</div></div>
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Comentarios 30d</div><div class="kpi-val" id="ig-comments30">—</div><div class="kpi-sub">@animuslb</div></div>
  </div>

  <!-- Gráfica de ventas + Top SKUs -->
  <div class="grid2" style="margin:20px 0;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">📈 Ventas mensuales Shopify</span></div>
      <div class="card-body" id="dash-chart" style="min-height:160px;">Cargando...</div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">🏆 Top SKUs por revenue (30d)</span></div>
      <div class="card-body" id="dash-top-skus">Cargando...</div>
    </div>
  </div>

  <!-- Campañas + Ciudades -->
  <div class="grid2" style="margin-bottom:20px;">
    <div class="card">
      <div class="card-hdr">
        <span class="card-title">📢 Campañas activas</span>
        <div class="kpi-grid" id="dash-kpis" style="display:none;"></div>
      </div>
      <div class="card-body">
        <table><thead><tr><th>Nombre</th><th>Canal</th><th>Estado</th><th>Budget</th><th>Ventas</th></tr></thead>
        <tbody id="dash-campanas"><tr class="empty-row"><td colspan="5">Cargando...</td></tr></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">🌎 Top ciudades Shopify</span></div>
      <div class="card-body" id="dash-ciudades">Cargando...</div>
    </div>
  </div>

  <!-- Instagram token update form -->
  <div id="ig-token-form" style="background:#0f172a;border:1px solid #e1306c44;border-radius:8px;padding:12px 16px;margin-bottom:12px;display:none;">
    <div style="font-size:11px;color:#e1306c;font-weight:700;margin-bottom:8px;">🔑 Token expirado — pega un nuevo token de Graph API Explorer</div>
    <div style="display:flex;gap:8px;align-items:center;">
      <input id="ig-token-input" type="text" placeholder="EAANXh..." 
        style="flex:1;background:#1e293b;border:1px solid #334155;color:#f1f5f9;padding:7px 10px;border-radius:6px;font-size:11px;font-family:monospace;">
      <button onclick="saveIgToken()" class="btn btn-sm" style="background:#e1306c;color:#fff;border:none;white-space:nowrap;">Guardar y activar</button>
      <button onclick="document.getElementById('ig-token-form').style.display='none'" class="btn btn-outline btn-sm">✕</button>
    </div>
    <div style="font-size:10px;color:#64748b;margin-top:6px;">
      Ve a <a href="https://developers.facebook.com/tools/explorer" target="_blank" style="color:#6366f1;">Graph API Explorer</a> → selecciona "Inventario ÁNIMUS" → Generate Access Token → pega aquí
    </div>
  </div>

  <!-- Instagram Top Posts -->
  <div class="card" style="margin-bottom:20px;" id="dash-ig-posts-section">
    <div class="card-hdr"><span class="card-title">📸 Top posts Instagram (por engagement)</span></div>
    <div class="card-body" id="dash-ig-posts">
      <div style="color:#64748b;text-align:center;padding:20px;">Conecta Instagram y sincroniza para ver tus mejores posts</div>
    </div>
  </div>

  <!-- Contenido + Canal -->
  <div class="grid2">
    <div class="card">
      <div class="card-hdr"><span class="card-title">📱 Contenido reciente</span></div>
      <div class="card-body">
        <table><thead><tr><th>Tipo</th><th>Plataforma</th><th>Estado</th><th>Alcance</th></tr></thead>
        <tbody id="dash-contenido"><tr class="empty-row"><td colspan="4">Cargando...</td></tr></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">💰 Presupuesto por canal</span></div>
      <div class="card-body" id="dash-canales">Cargando...</div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: CAMPAÑAS -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-campanas" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4E2; Campañas</div>
    </div>
    <div style="display:flex;gap:10px;">
      <select id="camp-filtro-estado" onchange="loadCampanas()" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;">
        <option value="">Todos los estados</option>
        <option value="Planificada">Planificada</option>
        <option value="Activa">Activa</option>
        <option value="Pausada">Pausada</option>
        <option value="Finalizada">Finalizada</option>
      </select>
      <button class="btn btn-primary" onclick="openCampanaModal()">+ Nueva Campaña</button>
    </div>
  </div>
  <div id="camp-alert" style="display:none;"></div>
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>#</th><th>Nombre</th><th>Tipo</th><th>Canal</th><th>Estado</th><th>Presupuesto</th><th>Gastado</th><th>Ventas</th><th>ROI</th><th>Infls</th><th>Acciones</th></tr></thead>
        <tbody id="camp-body"><tr class="empty-row"><td colspan="11"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: INFLUENCERS -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-influencers" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F465; Influencers</div>
    </div>
    <div style="display:flex;gap:10px;">
      <input class="search-box" id="inf-search" placeholder="Buscar nombre, @usuario, nicho..." oninput="loadInfluencers()">
      <button class="btn btn-primary" onclick="openInfluencerModal()">+ Nuevo Influencer</button>
    </div>
  </div>
  <div id="inf-kpi-bar" style="display:none;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;"></div>
  <div id="inf-alert" style="display:none;"></div>
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>#</th><th>Nombre</th><th>Red</th><th>@Usuario</th><th>Seguidores</th><th>ER%</th><th>Nicho</th><th>Tarifa/post</th><th>Email</th><th>Banco / Cuenta</th><th>Estado Pago</th><th>Acciones</th></tr></thead>
        <tbody id="inf-body"><tr class="empty-row"><td colspan="12"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: PAGOS REALIZADOS — vista cronológica para Jefferson/Marketing -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-pagos" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4B0; Pagos Realizados a Influencers</div>
      <div style="color:#94a3b8;font-size:13px;margin-top:2px;">Histórico cronológico · descarga el comprobante PDF de cada pago</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input class="search-box" id="pag-search" placeholder="Buscar influencer, OC, concepto..." oninput="renderPagos()">
      <select id="pag-mes" onchange="renderPagos()" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;">
        <option value="">Todos los meses</option>
      </select>
      <select id="pag-estado" onchange="renderPagos()" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;">
        <option value="" selected>Todos</option>
        <option value="Pagada">Pagados</option>
        <option value="Pendiente">Pendientes</option>
      </select>
      <button class="btn btn-outline btn-sm" onclick="loadPagosInfluencers()" title="Refrescar">&#x21BB;</button>
      <button id="btn-bulk-fix-empresa" class="btn btn-sm" onclick="bulkRegenerarLegacy()" title="Detectar y corregir comprobantes que dicen Espagiria pero deberian decir ANIMUS Lab" style="background:#7c3aed;color:white;border:1px solid #6d28d9;font-size:11px;padding:6px 10px;">&#x1F527; Fix legacy ANIMUS</button>
    </div>
  </div>

  <!-- ═══ Atribución de ventas (discount codes) ═══════════════════════════ -->
  <div class="card" style="margin-bottom:16px;background:linear-gradient(135deg,rgba(52,211,153,.06),rgba(52,211,153,.02));border:1px solid rgba(52,211,153,.25);">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">
      <div>
        <div style="font-size:14px;font-weight:700;color:#34d399;">&#x1F3AF; Atribución de ventas — últimos 90 días</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">Revenue Shopify atribuido vía discount code de cada influencer.</div>
      </div>
      <button class="btn btn-outline btn-sm" onclick="loadAtribucion()" title="Refrescar atribución">&#x21BB;</button>
    </div>
    <div id="atrib-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:12px;"></div>
    <div class="tbl-wrap">
      <table style="font-size:12px;">
        <thead><tr>
          <th>Influencer</th>
          <th>Discount code</th>
          <th style="text-align:right;">Pedidos</th>
          <th style="text-align:right;">Unidades</th>
          <th style="text-align:right;">Revenue</th>
          <th style="text-align:right;">Invertido</th>
          <th style="text-align:right;">ROI</th>
          <th>Último</th>
        </tr></thead>
        <tbody id="atrib-body"><tr class="empty-row"><td colspan="8" style="color:#64748b;text-align:center;padding:14px;">Cargando atribución...</td></tr></tbody>
      </table>
    </div>
  </div>

  <div id="pag-kpi-bar" style="display:none;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;"></div>
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Fecha</th>
          <th>Influencer</th>
          <th>Concepto</th>
          <th style="text-align:right;">Valor</th>
          <th>OC</th>
          <th>Comprobante</th>
          <th>Estado</th>
        </tr></thead>
        <tbody id="pag-body"><tr class="empty-row"><td colspan="7"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: CONTENIDO (Kanban Brief→Producción→Pendiente→Publicado→Performance) -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<style>
.kanban-wrap{display:grid;grid-template-columns:repeat(5,minmax(220px,1fr));gap:12px;overflow-x:auto;padding-bottom:10px;}
.kanban-col{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px;min-height:300px;display:flex;flex-direction:column;}
.kanban-col-hdr{display:flex;justify-content:space-between;align-items:center;padding:4px 6px 10px;border-bottom:1px solid #1e293b;margin-bottom:8px;}
.kanban-col-hdr .name{font-weight:700;font-size:13px;color:#f1f5f9;}
.kanban-col-hdr .count{background:#1e293b;color:#94a3b8;padding:1px 9px;border-radius:10px;font-size:11px;font-weight:700;}
.kanban-col[data-estado="Brief"]       .name{color:#60a5fa;}
.kanban-col[data-estado="Produccion"]  .name{color:#fbbf24;}
.kanban-col[data-estado="Pendiente"]   .name{color:#a78bfa;}
.kanban-col[data-estado="Publicado"]   .name{color:#34d399;}
.kanban-col[data-estado="Performance"] .name{color:#f472b6;}
.kanban-card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px;margin-bottom:8px;cursor:pointer;transition:.15s;font-size:12px;}
.kanban-card:hover{border-color:#7c3aed;transform:translateY(-1px);}
.kanban-card .sku{font-family:monospace;color:#34d399;font-size:11px;font-weight:700;}
.kanban-card .titulo{font-weight:700;color:#e2e8f0;margin:4px 0;line-height:1.3;}
.kanban-card .meta{display:flex;flex-wrap:wrap;gap:6px;font-size:10px;color:#64748b;margin-top:6px;}
.kanban-card .meta span{background:#0f172a;padding:1px 7px;border-radius:6px;}
.kanban-card .perf{display:flex;gap:8px;font-size:10px;margin-top:6px;color:#94a3b8;}
.kanban-card .perf b{color:#f1f5f9;}
.kanban-empty{color:#475569;font-size:11px;text-align:center;padding:20px 0;font-style:italic;}
.kanban-add-btn{background:#0f172a;color:#64748b;border:1px dashed #334155;border-radius:6px;padding:6px;font-size:11px;cursor:pointer;width:100%;margin-top:auto;transition:.15s;}
.kanban-add-btn:hover{color:#a78bfa;border-color:#7c3aed;}
</style>

<div id="tab-contenido" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4C5; Calendario de Contenido</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:2px;">Pipeline visual del contenido — desde el brief hasta el performance medido.</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;">
      <button class="btn btn-outline btn-sm" onclick="loadContenido()" title="Refrescar">&#x21BB;</button>
      <button class="btn btn-primary btn-sm" onclick="openContenidoModal()">+ Nueva pieza</button>
    </div>
  </div>
  <div id="cont-alert" style="display:none;"></div>

  <div class="kanban-wrap" id="kanban-wrap">
    <div class="kanban-col" data-estado="Brief">
      <div class="kanban-col-hdr"><span class="name">&#x1F4DD; Brief</span><span class="count" id="kb-c-Brief">0</span></div>
      <div class="kanban-items" id="kb-Brief"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Brief')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Produccion">
      <div class="kanban-col-hdr"><span class="name">&#x1F3AC; Producción</span><span class="count" id="kb-c-Produccion">0</span></div>
      <div class="kanban-items" id="kb-Produccion"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Produccion')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Pendiente">
      <div class="kanban-col-hdr"><span class="name">&#x23F0; Pendiente</span><span class="count" id="kb-c-Pendiente">0</span></div>
      <div class="kanban-items" id="kb-Pendiente"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Pendiente')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Publicado">
      <div class="kanban-col-hdr"><span class="name">&#x2705; Publicado</span><span class="count" id="kb-c-Publicado">0</span></div>
      <div class="kanban-items" id="kb-Publicado"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Publicado')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Performance">
      <div class="kanban-col-hdr"><span class="name">&#x1F4CA; Performance</span><span class="count" id="kb-c-Performance">0</span></div>
      <div class="kanban-items" id="kb-Performance"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Performance')">+ Agregar</button>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: INTELIGENCIA (envuelve Agentes IA + Histórico + Creadores) -->
<!-- Es un contenedor lógico — los 3 sub-paneles (tab-agentes, tab-analytics,
     tab-agencia) viven debajo y se alternan con showSub() / sub-nav.        -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<style>
.intel-subnav{display:flex;gap:4px;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:4px;margin-bottom:18px;flex-wrap:wrap;}
.intel-subnav button{flex:1;min-width:130px;padding:9px 16px;background:transparent;color:#94a3b8;border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.intel-subnav button:hover{color:#e2e8f0;background:#1e293b;}
.intel-subnav button.intel-active{background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;}
</style>

<!-- Sub-tab dedicada para el resultado de Estrategia (agente master).
     Persiste el último output para que el jefe pueda volver y accionar
     sin tener que regenerar. Si nunca se generó, invita a generarlo. -->
<div id="tab-estrategia" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button class="intel-active" onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div id="estrategia-vista" style="margin-top:12px;">
    <div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 60%,#312e81 100%);border:1px solid #7c3aed;border-radius:14px;padding:36px 24px;text-align:center;">
      <div style="font-size:48px;margin-bottom:12px;">&#x1F9E0;</div>
      <div style="font-size:22px;font-weight:800;color:#fff;margin-bottom:8px;">Estrategia del mes</div>
      <div style="font-size:13px;color:#cbd5e1;max-width:560px;margin:0 auto 18px;line-height:1.6;">
        Aún no generaste la estrategia este mes. El agente cruza ventas Shopify, engagement IG, stock, producción programada, influencers activos y eventos cosméticos para devolver el plan accionable.
      </div>
      <button onclick="runAgent('estrategia')"
        style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:14px 28px;font-size:14px;font-weight:800;border-radius:10px;cursor:pointer;box-shadow:0 8px 24px rgba(124,58,237,.4);">
        &#x25B6; Generar estrategia ahora
      </button>
    </div>
  </div>
</div>

<div id="tab-agentes" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button class="intel-active" onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div class="page-title">&#x1F916; Agentes IA — Marketing</div>
  <div class="page-sub">11 agentes inteligentes con Claude AI — análisis real de datos ERP + Shopify + GHL + Instagram.</div>

  <!-- ═══ Agente destacado: Estrategia (master) ════════════════════════════ -->
  <div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 60%,#312e81 100%);border:1px solid #7c3aed;border-radius:14px;padding:22px;margin-bottom:22px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-40%;right:-10%;width:300px;height:300px;background:radial-gradient(circle,#7c3aed33 0%,transparent 70%);pointer-events:none;"></div>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:relative;z-index:1;">
      <div style="font-size:36px;line-height:1;">&#x1F9E0;</div>
      <div style="flex:1;min-width:240px;">
        <div style="font-size:11px;color:#a78bfa;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:2px;">Master agent · cruza todo</div>
        <div style="font-size:18px;font-weight:800;color:#fff;margin-bottom:4px;">Estrategia del mes</div>
        <div style="font-size:12px;color:#cbd5e1;line-height:1.5;">Analiza ventas Shopify, engagement IG, stock, producción programada, influencers activos y eventos cosméticos. Devuelve: foco del mes · calendario de publicaciones (4 semanas) · 3 oportunidades de venta · 3 riesgos · recomendación al fundador.</div>
      </div>
      <button class="btn-agent" id="btn-estrategia" onclick="runAgent('estrategia')" style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:14px 22px;font-size:14px;font-weight:800;border-radius:10px;white-space:nowrap;">
        <span>&#x25B6; Generar estrategia</span>
      </button>
    </div>
    <div class="agent-result" id="result-estrategia" style="margin-top:18px;"></div>
  </div>

  <div class="agents-grid">

    <div class="agent-card">
      <div class="agent-icon">&#x1F4C6;</div>
      <div class="agent-name">Estacionalidad</div>
      <div class="agent-desc">Cruza stock PT vs demanda proyectada para eventos del calendario cosmético (Día de la Madre, Black Friday...). Detecta déficits y calcula deadlines de producción.</div>
      <button class="btn-agent" id="btn-estacionalidad" onclick="runAgent('estacionalidad')">
        <span>&#x25B6; Analizar estacionalidad</span>
      </button>
      <div class="agent-result" id="result-estacionalidad"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F50D;</div>
      <div class="agent-name">Oportunidad</div>
      <div class="agent-desc">Detecta SKUs con alto stock, baja rotación o sin ventas en Shopify. Propone acciones de campaña urgentes o recomendadas con canal sugerido.</div>
      <button class="btn-agent" id="btn-oportunidad" onclick="runAgent('oportunidad')">
        <span>&#x25B6; Detectar oportunidades</span>
      </button>
      <div class="agent-result" id="result-oportunidad"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4B0;</div>
      <div class="agent-name">ROI</div>
      <div class="agent-desc">Calcula el ROI real por campaña cruzando inversión vs ventas atribuidas. Incluye revenue Shopify de los últimos 30 días.</div>
      <button class="btn-agent" id="btn-roi" onclick="runAgent('roi')">
        <span>&#x25B6; Calcular ROI</span>
      </button>
      <div class="agent-result" id="result-roi"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4C8;</div>
      <div class="agent-name">Tendencias</div>
      <div class="agent-desc">Compara liberaciones ERP e histórico Shopify mes a mes. Identifica SKUs en alza, en caída y estables con variación porcentual.</div>
      <button class="btn-agent" id="btn-tendencias" onclick="runAgent('tendencias')">
        <span>&#x25B6; Ver tendencias</span>
      </button>
      <div class="agent-result" id="result-tendencias"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4CB;</div>
      <div class="agent-name">Brief de Contenido</div>
      <div class="agent-desc">Genera briefs por SKU top: canal recomendado, claim científico, formato, menciones en Instagram. Listo para enviar a influencers.</div>
      <div style="margin-bottom:10px;">
        <label style="font-size:11px;color:#64748b;">Campaña (opcional)</label>
        <select id="brief-campana-sel" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;width:100%;margin-top:4px;">
          <option value="">Sin campaña específica</option>
        </select>
      </div>
      <button class="btn-agent" id="btn-brief" onclick="runAgent('brief')">
        <span>&#x25B6; Generar brief</span>
      </button>
      <div class="agent-result" id="result-brief"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F3F7;&#xFE0F;</div>
      <div class="agent-name">Pricing</div>
      <div class="agent-desc">Calcula el descuento máximo seguro por SKU manteniendo margen ≥40%. Para SKUs con >4 meses de cobertura — activa promociones sin destruir rentabilidad.</div>
      <button class="btn-agent" id="btn-pricing" onclick="runAgent('pricing')">
        <span>&#x25B6; Calcular precios promo</span>
      </button>
      <div class="agent-result" id="result-pricing"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F504;</div>
      <div class="agent-name">Reorden B2B</div>
      <div class="agent-desc">Analiza patrones de compra de clientes B2B en Shopify. Predice cuándo hará su próximo pedido cada cliente y clasifica urgencia (hoy / esta semana / este mes).</div>
      <button class="btn-agent" id="btn-reorden" onclick="runAgent('reorden')">
        <span>&#x25B6; Predecir reórdenes</span>
      </button>
      <div class="agent-result" id="result-reorden"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x26A0;&#xFE0F;</div>
      <div class="agent-name">Canibalización</div>
      <div class="agent-desc">Detecta campañas activas que compiten por el mismo SKU o canal en fechas solapadas. Propone calendario optimizado para evitar conflictos.</div>
      <button class="btn-agent" id="btn-canibal" onclick="runAgent('canibal')">
        <span>&#x25B6; Detectar conflictos</span>
      </button>
      <div class="agent-result" id="result-canibal"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x270D;&#xFE0F;</div>
      <div class="agent-name">Contenido Auto</div>
      <div class="agent-desc">Genera captions para Instagram, asuntos de email y textos de WhatsApp para los 3 SKUs con mayor rotación del último mes.</div>
      <button class="btn-agent" id="btn-contenido_auto" onclick="runAgent('contenido_auto')">
        <span>&#x25B6; Generar contenido</span>
      </button>
      <div class="agent-result" id="result-contenido_auto"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F6A8;</div>
      <div class="agent-name">Alerta Stock</div>
      <div class="agent-desc">Cruza stock ERP + demanda Shopify para detectar SKUs con cobertura crítica (≤7d) o en advertencia (≤21d). Dispara alertas de reposición urgente.</div>
      <button class="btn-agent" id="btn-alerta_stock" onclick="runAgent('alerta_stock')">
        <span>&#x25B6; Ver alertas stock</span>
      </button>
      <div class="agent-result" id="result-alerta_stock"></div>
    </div>

  </div>

  <div style="margin-top:28px;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4DC; Historial de Agentes</span>
        <button class="btn btn-outline btn-sm" onclick="loadAgentLog()">&#x21BB; Actualizar</button>
      </div>
      <div class="card-body">
        <table>
          <thead><tr><th>Fecha</th><th>Agente</th><th>Acción</th><th>Ejecutado por</th><th>Ver</th></tr></thead>
          <tbody id="agent-log-body"><tr class="empty-row"><td colspan="5">Cargando historial...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: ANALYTICS -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-analytics" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button class="intel-active" onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div class="page-title">&#x1F4CA; Analytics — Programa de Influencers</div>
  <div class="page-sub">Inversión histórica, rendimiento por creador y Shopify revenue.</div>

  <!-- KPI fila 1: histórico -->
  <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Histórico total</div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:20px;">
    <div class="kpi-card blue"><div class="kpi-label">Invertido total</div><div class="kpi-val" id="an-total-hist">—</div></div>
    <div class="kpi-card green"><div class="kpi-label">Colaboraciones</div><div class="kpi-val" id="an-colabs-hist">—</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Creadores únicos</div><div class="kpi-val" id="an-creadores-hist">—</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Promedio / colab</div><div class="kpi-val" id="an-avg-colab">—</div></div>
    <div class="kpi-card red"><div class="kpi-label">Pendiente pago</div><div class="kpi-val" id="an-pendiente-total">—</div></div>
    <div class="kpi-card" style="border-color:#6366f1;"><div class="kpi-label">Top creador</div><div class="kpi-val" id="an-top-creador" style="font-size:13px;color:#818cf8;">—</div></div>
  </div>

  <!-- KPI fila 2: Shopify -->
  <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Shopify — Revenue actual</div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:24px;">
    <div class="kpi-card blue"><div class="kpi-label">Revenue últimos 30d</div><div class="kpi-val" id="an-sh-30d">—</div></div>
    <div class="kpi-card green"><div class="kpi-label">Revenue este mes</div><div class="kpi-val" id="an-sh-mes">—</div></div>
    <div class="kpi-card" id="an-sh-crec-card" style="border-color:#34d399;"><div class="kpi-label">Crecimiento vs mes ant.</div><div class="kpi-val" id="an-sh-crec">—</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Pedidos últimos 30d</div><div class="kpi-val" id="an-sh-orders">—</div></div>
  </div>

  <div class="grid2" style="margin-bottom:20px;">
    <!-- Gasto mensual chart -->
    <div class="card">
      <div class="card-hdr">
        <span class="card-title">&#x1F4B0; Gasto mensual histórico (COP)</span>
        <span id="an-total-label" style="font-size:12px;color:#64748b;"></span>
      </div>
      <div class="card-body" id="an-gasto-chart" style="min-height:200px;padding:8px 0;"></div>
    </div>
    <!-- Nuevos creadores -->
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F331; Nuevos creadores por mes</span></div>
      <div class="card-body" id="an-nuevos-chart" style="min-height:200px;padding:8px 0;"></div>
    </div>
  </div>

  <!-- Ranking ALL TIME -->
  <div class="card" style="margin-bottom:20px;">
    <div class="card-hdr"><span class="card-title">&#x1F3C6; Ranking — Inversión por creador (histórico)</span></div>
    <div class="card-body">
      <table>
        <thead><tr><th>#</th><th>Creador</th><th>Colabs</th><th>Total pagado</th><th>Pendiente</th><th>Promedio/colab</th><th>Primer pago</th><th>Último pago</th><th>Estado</th></tr></thead>
        <tbody id="an-ranking-body"><tr class="empty-row"><td colspan="9">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Detalle mensual -->
  <div class="card">
    <div class="card-hdr"><span class="card-title">&#x1F4C5; Detalle por mes</span></div>
    <div class="card-body">
      <table>
        <thead><tr><th>Mes</th><th>Colaboraciones</th><th>Creadores únicos</th><th>Total pagado</th><th>Pendiente</th><th>Nuevos creadores</th></tr></thead>
        <tbody id="an-meses-body"><tr class="empty-row"><td colspan="6">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- KPI año actual (hidden label, kept for compat) -->
  <span id="an-total-2025" style="display:none;"></span>
  <span id="an-colabs-2025" style="display:none;"></span>
  <span id="an-creadores-2025" style="display:none;"></span>
</div><!-- /tab-analytics -->

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- MODALS — DEBEN VIVIR FUERA de cualquier tab-panel.               -->
<!-- Bug previo: tab-analytics no cerraba antes de los modales, así    -->
<!-- que cuando esa tab era display:none, todos los modales también.   -->
<!-- El user veía: 'el botón editar solo abre el modal cuando estoy    -->
<!-- en la pestaña Histórico de inversión'.                            -->
<!-- ═══════════════════════════════════════════════════════════════ -->

<!-- Modal: Historial Influencer -->
<div class="modal-bg" id="modal-historial">
  <div class="modal" style="max-width:680px;max-height:85vh;overflow-y:auto;">
    <div class="modal-title" id="hist-title">Historial</div>
    <button class="modal-close" onclick="closeModal('modal-historial')">&times;</button>
    <div id="hist-content" style="margin-top:8px;"></div>
  </div>
</div>

<!-- Modal: Nueva Campaña -->
<div class="modal-bg" id="modal-campana">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-campana-title">Nueva Campaña</div>
      <button class="modal-close" onclick="closeModal('modal-campana')">&times;</button>
    </div>
    <input type="hidden" id="camp-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Nombre *</label><input id="camp-nombre" placeholder="Ej: Lanzamiento Crema Vitamina C"></div>
      <div class="form-group"><label>Tipo</label>
        <select id="camp-tipo">
          <option>Digital</option><option>Influencer</option><option>Email</option><option>OOH</option><option>Mixta</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Canal</label><input id="camp-canal" placeholder="Ej: Instagram, TikTok, Email..."></div>
      <div class="form-group"><label>Estado</label>
        <select id="camp-estado">
          <option>Planificada</option><option>Activa</option><option>Pausada</option><option>Finalizada</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha Inicio</label><input type="date" id="camp-inicio"></div>
      <div class="form-group"><label>Fecha Fin</label><input type="date" id="camp-fin"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Presupuesto (COP)</label><input type="number" id="camp-presupuesto" placeholder="0"></div>
      <div class="form-group"><label>SKU Objetivo</label><input id="camp-sku" placeholder="Ej: LBHA-30, NIAC-50"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Objetivo Unidades</label><input type="number" id="camp-obj-uds" placeholder="0"></div>
      <div class="form-group"><label>Resultado Unidades</label><input type="number" id="camp-res-uds" placeholder="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Resultado Ventas (COP)</label><input type="number" id="camp-res-ventas" placeholder="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Notas</label><textarea id="camp-notas" placeholder="Observaciones..."></textarea></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-campana')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveCampana()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Nuevo Influencer -->
<div class="modal-bg" id="modal-influencer">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-inf-title">Nuevo Influencer</div>
      <button class="modal-close" onclick="closeModal('modal-influencer')">&times;</button>
    </div>
    <input type="hidden" id="inf-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Nombre *</label><input id="inf-nombre" placeholder="Nombre completo"></div>
      <div class="form-group"><label>Red Social</label>
        <select id="inf-red">
          <option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Twitter</option><option>Otro</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>@Usuario</label><input id="inf-usuario" placeholder="@handle"></div>
      <div class="form-group"><label>Seguidores</label><input type="number" id="inf-seguidores" placeholder="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Engagement Rate %</label><input type="number" step="0.1" id="inf-er" placeholder="0.0"></div>
      <div class="form-group"><label>Nicho</label><input id="inf-nicho" placeholder="Skincare, Lifestyle..."></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Tarifa por post (COP)</label><input type="number" id="inf-tarifa" placeholder="0"></div>
      <div class="form-group"><label>Estado</label>
        <select id="inf-estado"><option>Activo</option><option>Inactivo</option><option>Bloqueado</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Email</label><input type="email" id="inf-email" placeholder="correo@ejemplo.com"></div>
      <div class="form-group"><label>Teléfono</label><input id="inf-tel" placeholder="+57..."></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Notas</label><textarea id="inf-notas" placeholder="Observaciones..."></textarea></div>
    </div>
    <div style="border-top:1px solid #334155;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🏦 Datos Bancarios</div>
      <div class="form-row">
        <div class="form-group"><label>Banco</label><input id="inf-banco" placeholder="Bancolombia, Nequi, Daviplata..."></div>
        <div class="form-group"><label>Tipo de cuenta</label>
          <select id="inf-tipo-cta">
            <option>Ahorros</option><option>Corriente</option><option>Nequi</option><option>Daviplata</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Número cuenta / Cel</label><input id="inf-cuenta" placeholder="3114902203 / 0123456789"></div>
        <div class="form-group"><label>Cédula / NIT</label><input id="inf-cedula" placeholder="1234567890"></div>
      </div>
    </div>
    <div style="border-top:1px solid #334155;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#fbbf24;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">⏰ Ciclo de pago</div>
      <div class="form-row">
        <div class="form-group">
          <label>Frecuencia con la que se le paga</label>
          <select id="inf-ciclo-pago" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px;width:100%;">
            <option value="Mensual">Mensual (cada 30 días)</option>
            <option value="Bimensual">Bimensual (cada 60 días)</option>
            <option value="Trimestral">Trimestral (cada 90 días)</option>
            <option value="Único">Único (no recurrente)</option>
            <option value="Sin ciclo">Sin ciclo definido</option>
          </select>
          <div style="font-size:10px;color:#64748b;margin-top:4px;">
            Cuando se cumple el ciclo y no hay solicitud activa, el panel muestra <span style="color:#fde047;">⏰ Toca pagar</span>.
          </div>
        </div>
      </div>
    </div>
    <div style="border-top:1px solid #334155;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#34d399;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🎟️ Atribución de ventas</div>
      <div class="form-row full">
        <div class="form-group">
          <label>Discount code de Shopify</label>
          <input id="inf-discount-code" placeholder="ANIMUS_LAURA10" style="text-transform:uppercase;font-family:monospace;">
          <div style="font-size:10px;color:#64748b;margin-top:4px;line-height:1.4;">
            Cuando un cliente use este código en Shopify, la venta se atribuye automáticamente a este influencer.
            Convención: <code style="background:#0f172a;padding:1px 6px;border-radius:4px;color:#34d399;">ANIMUS_NOMBRE_PCT</code> (ej: ANIMUS_LAURA10).
          </div>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-influencer')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveInfluencer()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Solicitar Pago Influencer -->
<div class="modal-bg" id="modal-inf-pago">
  <div class="modal" style="max-width:460px;">
    <div class="modal-hdr">
      <div class="modal-title">&#x1F4B8; Solicitar Pago</div>
      <button class="modal-close" onclick="closeModal('modal-inf-pago')">&times;</button>
    </div>
    <input type="hidden" id="pago-inf-id">
    <div style="margin-bottom:14px;">
      <div style="font-size:13px;color:#94a3b8;margin-bottom:4px;">Influencer</div>
      <div id="pago-inf-nombre" style="font-weight:700;font-size:15px;color:#e2e8f0;"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Valor a pagar (COP) *</label><input type="number" id="pago-valor" placeholder="0"></div>
      <div class="form-group"><label>Concepto</label><input id="pago-concepto" placeholder="Post + Story / Reel..."></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha de publicación</label><input type="date" id="pago-fecha-pub"></div>
      <div class="form-group"><label>Entregable</label><input id="pago-entregable" placeholder="1 Reel + 2 Stories..."></div>
    </div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin:8px 0;font-size:12px;color:#94a3b8;">
      <div style="font-weight:700;color:#a78bfa;margin-bottom:6px;">&#x1F3E6; Datos bancarios</div>
      <div id="pago-banco-preview" style="line-height:1.8;"></div>
    </div>
    <div id="pago-inf-alert" style="display:none;margin-bottom:8px;"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;">
      <button class="btn btn-outline" onclick="closeModal('modal-inf-pago')">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarPagoInf()">Crear Solicitud</button>
    </div>
  </div>
</div>


<!-- Modal: Dar de Baja Influencer -->
<div class="modal-bg" id="modal-dar-baja">
  <div class="modal" style="max-width:420px;">
    <div class="modal-hdr">
      <div class="modal-title">&#x26D4; Dar de Baja Influencer</div>
      <button class="modal-close" onclick="closeModal('modal-dar-baja')">&times;</button>
    </div>
    <input type="hidden" id="baja-inf-id">
    <div style="margin-bottom:14px;">
      <div style="font-size:13px;color:#94a3b8;margin-bottom:4px;">Influencer</div>
      <div id="baja-inf-nombre" style="font-weight:700;font-size:15px;color:#e2e8f0;"></div>
    </div>
    <div class="form-group" style="margin-bottom:12px;">
      <label>Motivo de baja *</label>
      <select id="baja-motivo-tipo" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px;color:#e2e8f0;">
        <option value="Pausa temporal">Pausa temporal</option>
        <option value="No cumplió métricas">No cumplió métricas</option>
        <option value="Conflicto de marca">Conflicto de marca</option>
        <option value="Presupuesto">Presupuesto</option>
        <option value="Solicitud del influencer">Solicitud del influencer</option>
        <option value="Otro">Otro</option>
      </select>
    </div>
    <div class="form-group" style="margin-bottom:12px;">
      <label>Observación (opcional)</label>
      <textarea id="baja-observacion" rows="3" placeholder="Detalles adicionales..." style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px;color:#e2e8f0;resize:vertical;"></textarea>
    </div>
    <div style="background:#1c1a14;border:1px solid #78350f;border-radius:8px;padding:10px;font-size:12px;color:#fcd34d;margin-bottom:12px;">
      &#x26A0;&#xFE0F; El influencer quedará en estado <b>Baja</b> y visible en el historial. Podrá reactivarse en cualquier momento.
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="closeModal('modal-dar-baja')">Cancelar</button>
      <button class="btn btn-danger" onclick="confirmarDarDeBaja()">Dar de Baja</button>
    </div>
  </div>
</div>

<!-- Modal: Nuevo Contenido -->
<div class="modal-bg" id="modal-contenido">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-cont-title">Nueva Pieza de Contenido</div>
      <button class="modal-close" onclick="closeModal('modal-contenido')">&times;</button>
    </div>
    <input type="hidden" id="cont-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Tipo</label>
        <select id="cont-tipo"><option>Post</option><option>Story</option><option>Reel</option><option>Video</option><option>Email</option><option>Banner</option></select>
      </div>
      <div class="form-group"><label>Plataforma</label>
        <select id="cont-plataforma"><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Email</option><option>Web</option><option>Otro</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Campaña</label>
        <select id="cont-campana-sel"><option value="">Sin campaña</option></select>
      </div>
      <div class="form-group"><label>Influencer</label>
        <select id="cont-influencer-sel"><option value="">Sin influencer (interno)</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha programada</label><input type="date" id="cont-fecha-prog"></div>
      <div class="form-group"><label>Fecha publicación real</label><input type="date" id="cont-fecha"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Estado (Kanban)</label>
        <select id="cont-estado">
          <option value="Brief">📝 Brief</option>
          <option value="Produccion">🎬 Producción</option>
          <option value="Pendiente">⏰ Pendiente publicación</option>
          <option value="Publicado">✅ Publicado</option>
          <option value="Performance">📊 Performance</option>
        </select>
      </div>
      <div class="form-group"><label>SKU objetivo</label><input id="cont-sku" placeholder="Ej: LBHA-30" style="text-transform:uppercase;font-family:monospace;"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Mensaje principal (claim)</label><input id="cont-mensaje" placeholder="Lo que el creador debe transmitir en una frase"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>URL Publicación (cuando ya se publicó)</label><input id="cont-url" placeholder="https://instagram.com/p/..."></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Likes</label><input type="number" id="cont-likes" value="0"></div>
      <div class="form-group"><label>Comentarios</label><input type="number" id="cont-comentarios" value="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Alcance</label><input type="number" id="cont-alcance" value="0"></div>
      <div class="form-group"><label>Conversiones</label><input type="number" id="cont-conversiones" value="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Caption / Descripción completa</label><textarea id="cont-caption"></textarea></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-contenido')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveContenido()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Ver resultado agente -->
<div class="modal-bg" id="modal-agente-result">
  <div class="modal" style="max-width:700px;">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-agent-title">Resultado</div>
      <button class="modal-close" onclick="closeModal('modal-agente-result')">&times;</button>
    </div>
    <div id="modal-agent-content" style="font-size:13px;color:#e2e8f0;white-space:pre-wrap;max-height:500px;overflow-y:auto;background:#0f172a;border-radius:8px;padding:16px;font-family:'Segoe UI',sans-serif;"></div>
  </div>
</div>
<!-- /MODALS -->

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: AGENCIA                                                   -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-agencia" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button class="intel-active" onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:6px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">&#x1F3C6; Score de Creadores &#x2014; Inteligencia de Mercado</div>
      <div class="page-sub">Score de influencers, auditoría de portafolio, análisis competitivo y propuestas de campaña.</div>
    </div>
    <button class="btn-primary" style="font-size:12px;padding:8px 16px;" onclick="loadAgencia(true)">&#x1F504; Actualizar</button>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-bottom:20px;">
    <div class="kpi-card blue"><div class="kpi-label">Influencers activos</div><div class="kpi-val" id="ag-kpi-activos">-</div></div>
    <div class="kpi-card green"><div class="kpi-label">Score promedio</div><div class="kpi-val" id="ag-kpi-score">-</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">En riesgo</div><div class="kpi-val" id="ag-kpi-riesgo">-</div></div>
    <div class="kpi-card red"><div class="kpi-label">Hallazgos criticos</div><div class="kpi-val" id="ag-kpi-critical">-</div></div>
    <div class="kpi-card" style="border-color:#667eea;"><div class="kpi-label">Inversion total</div><div class="kpi-val" id="ag-kpi-inversion" style="color:#667eea;">-</div></div>
  </div>
  <div class="card" style="margin-bottom:20px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div style="font-weight:700;color:#e2e8f0;font-size:15px;">Score de Influencers</div>
      <div style="font-size:11px;color:#64748b;">engagement 30pct &middot; inversion 25pct &middot; seguidores 20pct &middot; recencia 15pct &middot; contenido 10pct</div>
    </div>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #334155;">
        <th style="padding:8px;text-align:left;color:#64748b;font-weight:600;">Influencer</th>
        <th style="padding:8px;text-align:left;color:#64748b;font-weight:600;">Nicho</th>
        <th style="padding:8px;text-align:center;color:#64748b;font-weight:600;">Score</th>
        <th style="padding:8px;text-align:right;color:#64748b;font-weight:600;">Engagement</th>
        <th style="padding:8px;text-align:right;color:#64748b;font-weight:600;">Seguidores</th>
        <th style="padding:8px;text-align:right;color:#64748b;font-weight:600;">Campanas</th>
        <th style="padding:8px;text-align:right;color:#64748b;font-weight:600;">Invertido</th>
        <th style="padding:8px;text-align:center;color:#64748b;font-weight:600;">Estado</th>
      </tr></thead>
      <tbody id="ag-scoring-tbody"><tr class="empty-row"><td colspan="8">Cargando...</td></tr></tbody>
    </table>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="card">
      <div style="font-weight:700;color:#e2e8f0;font-size:15px;margin-bottom:14px;">Auditoria de Portafolio</div>
      <div id="ag-audit-list"><div style="color:#64748b;font-size:13px;">Cargando...</div></div>
    </div>
    <div class="card">
      <div style="font-weight:700;color:#e2e8f0;font-size:15px;margin-bottom:14px;">Analisis Competitivo</div>
      <div id="ag-competition"><div style="color:#64748b;font-size:13px;">Cargando...</div></div>
    </div>
  </div>
  <div class="card">
    <div style="font-weight:700;color:#e2e8f0;font-size:15px;margin-bottom:14px;">Propuestas de Campana</div>
    <div id="ag-proposals"><div style="color:#64748b;font-size:13px;">Cargando...</div></div>
  </div>
</div>

<!-- Tab "Agencia Ads" eliminado: no se usaba data HHA y se solapaba con
     el agente master Estrategia (que sí cruza Shopify + IG + stock + calendar
     + influencers). El skill genérico ads_skill.py se conserva en backend
     por si se necesita en el futuro (reusable). -->
<div id="tab-ads" class="tab-panel" style="display:none !important;"></div>


<script>
// ──────────────────────────────────────────────────────────────────────────────
// UTILS
// ──────────────────────────────────────────────────────────────────────────────
const fmt = n => Number(n||0).toLocaleString('es-CO');
const fmtM = n => {
  const v = Number(n||0);
  if(v>=1000000) return '$'+(v/1000000).toFixed(1)+'M';
  if(v>=1000) return '$'+(v/1000).toFixed(0)+'K';
  return '$'+fmt(v);
};
const badgeEstadoCamp = e => {
  const m = {Activa:'green',Planificada:'blue',Pausada:'yellow',Finalizada:'gray'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const badgeEstadoCont = e => {
  const m = {Publicado:'green',Programado:'blue',Borrador:'gray',Archivado:'gray'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const badgeEstadoInf = e => {
  const m = {Activo:'green',Inactivo:'yellow',Bloqueado:'red'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const roiBadge = r => {
  if(r===null||r===undefined||r==='') return '<span class="badge badge-gray">—</span>';
  const v = parseFloat(r);
  const cl = v>100?'green':v>0?'blue':v>-50?'yellow':'red';
  return `<span class="badge badge-${cl}">${v>0?'+':''}${v}%</span>`;
};
function showAlert(containerId, msg, type='success') {
  const el = document.getElementById(containerId);
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(()=>el.style.display='none', 4000);
}

// ──────────────────────────────────────────────────────────────────────────────
// TABS
// ──────────────────────────────────────────────────────────────────────────────
const _loaded = {};
// Sub-tab activa dentro de "Inteligencia". Persiste para que cuando el user
// vuelve a la tab Inteligencia se quede en la última vista que estaba viendo.
// Default = 'estrategia' — el master agent es lo que el jefe ve primero.
let _intelSub = 'estrategia';

function switchTab(name) {
  // Resolver: 'inteligencia' es virtual — abre el sub-panel actual (default agentes)
  const realPanel = (name === 'inteligencia') ? _intelSub : name;

  // Highlight botón superior — match por data-tab. Inteligencia se activa
  // cuando estamos viendo cualquiera de sus sub-paneles.
  document.querySelectorAll('.tab-btn').forEach(b => {
    const t = b.dataset.tab;
    const isActive = (t === name) ||
                     (t === 'inteligencia' && ['estrategia','agentes','analytics','agencia'].includes(realPanel));
    b.classList.toggle('active', isActive);
  });

  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('tab-' + realPanel);
  if (panel) panel.classList.add('active');

  if (!_loaded[realPanel]) { _loaded[realPanel] = true; loadTab(realPanel); }
}

// Sub-navegación dentro de Inteligencia (Agentes / Creadores / Histórico)
function showSub(sub) {
  _intelSub = sub;
  // Highlight de los botones de sub-nav (el activo se sincroniza en TODAS las
  // copias de la sub-nav porque cada panel tiene su propia copia)
  document.querySelectorAll('.intel-subnav button').forEach(btn => {
    const target = (btn.getAttribute('onclick')||'').match(/showSub\('(\w+)'\)/);
    if (!target) return;
    btn.classList.toggle('intel-active', target[1] === sub);
  });
  switchTab(sub);
}

function loadTab(name) {
  if(name==='dashboard') loadDashboard();
  else if(name==='campanas') loadCampanas();
  else if(name==='influencers') loadInfluencers();
  else if(name==='pagos') loadPagosInfluencers();
  else if(name==='contenido') loadContenido();
  else if(name==='estrategia') loadUltimaEstrategia();
  else if(name==='agentes') { loadAgentLog(); loadCampanasForSelect(); loadConnections(); loadFeedbackStats(); }
  else if(name==='analytics') loadAnalytics();
  else if(name==='agencia') loadAgencia();
}

// ─── Vista persistente de Estrategia ──────────────────────────────────
async function loadUltimaEstrategia() {
  // Buscar la ejecución más reciente del agente 'Estrategia' en el log
  try {
    const rows = await fetch('/api/marketing/agentes/log').then(r=>r.json());
    const latest = (rows||[]).find(r => (r.agente||'').toLowerCase() === 'estrategia');
    if (!latest) return; // no hay corrida previa — vista invitando se mantiene
    const det = await fetch('/api/marketing/agentes/log/' + latest.id).then(r=>r.json());
    const view = document.getElementById('estrategia-vista');
    if (!view) return;
    let resultado = det.resultado;
    if (typeof resultado === 'string') {
      try { resultado = JSON.parse(resultado); } catch (e) { /* keep as string */ }
    }
    // Header con timestamp + botón regenerar
    const fecha = (det.fecha || latest.fecha || '').slice(0, 16).replace('T',' ');
    let html = `<div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:12px 18px;margin-bottom:14px;">
      <div>
        <div style="font-size:14px;font-weight:700;color:#a78bfa;">&#x1F9E0; Última estrategia generada</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">${fecha} · por ${det.ejecutado_por||'sistema'}</div>
      </div>
      <button onclick="runAgent('estrategia')" style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:8px 16px;font-size:12px;font-weight:700;border-radius:8px;cursor:pointer;">&#x21BB; Regenerar</button>
    </div>`;
    if (typeof resultado === 'object' && resultado) {
      html += formatAgentResult('estrategia', resultado);
      if (latest.id) html += renderFeedbackBar(latest.id);
    } else {
      html += '<div style="color:#94a3b8;padding:14px;">Sin contenido detallado.</div>';
    }
    view.innerHTML = html;
  } catch(e) {
    console.warn('[loadUltimaEstrategia]', e);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// DASHBOARD
// ──────────────────────────────────────────────────────────────────────────────
async function saveIgToken() {
  const token = document.getElementById('ig-token-input').value.trim();
  if (!token || !token.startsWith('EAA')) { showToast('Token invalido', 'error'); return; }
  try {
    const r = await fetch('/api/marketing/ig-update-token', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if (d.ok) {
      showToast('✅ Token guardado — sincronizando...', 'success');
      document.getElementById('ig-token-form').style.display = 'none';
      document.getElementById('ig-token-input').value = '';
      setTimeout(() => syncPlatform('instagram'), 800);
    } else {
      showToast('❌ ' + (d.error||'Error'), 'error');
    }
  } catch(e) { showToast('❌ Error de conexion', 'error'); }
}

async function refreshIgToken() {
  const btn = event.target;
  btn.disabled = true; btn.textContent = '⏳ Renovando...';
  try {
    const r = await fetch('/api/marketing/ig-refresh', {method:'POST', headers:{'Content-Type':'application/json'}});
    const d = await r.json();
    if (d.ok) {
      showToast('✅ ' + d.msg, 'success');
    } else {
      showToast('❌ ' + (d.error||'Error al renovar'), 'error');
    }
  } catch(e) {
    showToast('❌ Error de conexion', 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🔑 Renovar token IG';
  }
}

async function loadDashboard() {
  loadConnections();
  let _dashResp;
  try { _dashResp = await fetch('/api/marketing/dashboard'); }
  catch(e) { console.error('dashboard fetch:', e); return; }
  if(!_dashResp.ok && _dashResp.status===401){ location.reload(); return; }
  const data = await _dashResp.json().catch(()=>null);
  if(!data){ console.error('dashboard: respuesta no es JSON'); return; }
  const k = data.kpis || {};
  const sh = data.shopify || {};
  const ghl = data.ghl || {};

  document.getElementById('dash-fecha').textContent = 'Actualizado: '+new Date().toLocaleString('es-CO');

  // ── Shopify KPIs ──────────────────────────────────────────────────────────
  const fmt2 = v => v==null?'—':String(v);
  const fmtCOP = v => v==null?'—':'$'+Number(v).toLocaleString('es-CO');
  // Cobertura real de datos Shopify
  var shBanner = document.getElementById('sh-cobertura-banner');
  if(sh.datos_desde){
    var dias = sh.cobertura_dias || 0;
    var lRev = dias < 25 ? 'Revenue ('+dias+'d)' : 'Revenue 30d';
    var lPed = dias < 25 ? 'Pedidos ('+dias+'d)' : 'Pedidos 30d';
    if(document.getElementById('sh-rev30-label')) document.getElementById('sh-rev30-label').textContent = lRev;
    if(document.getElementById('sh-ped30-label')) document.getElementById('sh-ped30-label').textContent = lPed;
    if(sh.cobertura_parcial && shBanner){
      shBanner.style.display='block';
      shBanner.innerHTML = '⚠️ Datos Shopify disponibles desde <strong>'+sh.datos_desde+'</strong> ('+dias+' días). '+'Usa <strong>Sync histórico</strong> para traer el historial completo.';
    } else if(shBanner){ shBanner.style.display='none'; }
  }
  document.getElementById('sh-rev30').textContent    = fmtCOP(sh.revenue_30d);
  document.getElementById('sh-rev7').textContent     = 'Últimos 7d: '+fmtCOP(sh.revenue_7d);
  document.getElementById('sh-ped30').textContent    = fmt2(sh.pedidos_30d);
  document.getElementById('sh-ped-total').textContent= 'Total: '+fmt2(sh.pedidos_total);
  document.getElementById('sh-ticket').textContent   = fmtCOP(sh.ticket_promedio);
  document.getElementById('sh-clientes').textContent = 'Clientes: '+fmt2(sh.clientes_total);
  document.getElementById('sh-nuevos').textContent   = fmt2(sh.clientes_nuevos_30d);
  document.getElementById('sh-recurrentes').textContent = 'Recurrentes: '+fmt2(sh.clientes_recurrentes_30d);
  document.getElementById('sh-rev-total').textContent = fmtCOP(sh.revenue_total);
  document.getElementById('ghl-total').textContent   = fmt2(ghl.contactos_total);
  document.getElementById('ghl-nuevos').textContent  = 'Nuevos 30d: '+fmt2(ghl.contactos_nuevos_30d);

  // ── Gráfica ventas mensuales (SVG bar chart) ──────────────────────────────
  const mensual = sh.mensual || [];
  const chartEl = document.getElementById('dash-chart');
  if (!mensual.length) {
    chartEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:32px;">Sin datos de ventas</div>';
  } else {
    const W=560, H=140, PAD_L=52, PAD_B=32, PAD_T=10, PAD_R=10;
    const plotW = W-PAD_L-PAD_R;
    const plotH = H-PAD_T-PAD_B;
    const maxV = Math.max(...mensual.map(m=>m.total||0), 1);
    const barW = Math.max(6, Math.floor(plotW/mensual.length)-4);
    const scale = v => plotH - Math.round((v/maxV)*plotH);
    const fmtK = v => v>=1000000 ? (v/1000000).toFixed(1)+'M' : v>=1000 ? Math.round(v/1000)+'k' : String(v);
    const bars = mensual.map((m,i)=>{
      const x = PAD_L + Math.round(i*(plotW/mensual.length)) + Math.round((plotW/mensual.length-barW)/2);
      const y = PAD_T + scale(m.total||0);
      const bH = plotH - scale(m.total||0);
      const label = (m.mes||'').slice(5,7)+'/'+((m.mes||'').slice(2,4));
      return `<rect x="${x}" y="${y}" width="${barW}" height="${Math.max(2,bH)}" fill="#d4af37" rx="2" opacity="0.85"/>
<text x="${x+barW/2}" y="${PAD_T+plotH+16}" text-anchor="middle" font-size="9" fill="#94a3b8">${label}</text>`;
    }).join('\n');
    // Y axis labels
    const yLabels = [0,0.25,0.5,0.75,1].map(pct=>{
      const val = Math.round(maxV*pct);
      const y = PAD_T + plotH - Math.round(pct*plotH);
      return `<line x1="${PAD_L-4}" y1="${y}" x2="${PAD_L+plotW}" y2="${y}" stroke="#1e293b" stroke-width="1"/>
<text x="${PAD_L-6}" y="${y+3}" text-anchor="end" font-size="9" fill="#64748b">${fmtK(val)}</text>`;
    }).join('\n');
    chartEl.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;display:block;">
${yLabels}
${bars}
</svg>`;
  }

  // ── Top SKUs ──────────────────────────────────────────────────────────────
  const skuEl = document.getElementById('dash-top-skus');
  const topSkus = sh.top_skus || [];
  if (!topSkus.length) {
    skuEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:32px;">Sin datos de SKUs</div>';
  } else {
    const maxSku = topSkus[0].total || 1;
    skuEl.innerHTML = topSkus.map((s,i)=>`
      <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #1e293b;">
        <span style="color:#d4af37;font-weight:700;min-width:18px;">#${i+1}</span>
        <span style="flex:1;font-weight:600;font-size:12px;">${s.sku||'—'}</span>
        <div style="flex:2;">
          <div style="background:#1e293b;border-radius:3px;height:6px;">
            <div style="background:#d4af37;height:6px;border-radius:3px;width:${Math.round((s.total/maxSku)*100)}%;"></div>
          </div>
        </div>
        <span style="color:#34d399;font-size:11px;min-width:72px;text-align:right;">${fmtCOP(s.total)}</span>
        <span style="color:#64748b;font-size:11px;min-width:36px;text-align:right;">${fmt2(s.uds)} uds</span>
      </div>`).join('');
  }

  // ── Ciudades ──────────────────────────────────────────────────────────────
  const ciudEl = document.getElementById('dash-ciudades');
  const ciudades = sh.ciudades || [];
  if (!ciudades.length) {
    ciudEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:32px;">Sin datos de ciudades</div>';
  } else {
    const maxCiud = ciudades[0].pedidos || 1;
    ciudEl.innerHTML = ciudades.map((c,i)=>`
      <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #1e293b;">
        <span style="color:#94a3b8;min-width:18px;font-size:11px;">${i+1}</span>
        <span style="flex:1;font-size:12px;">${c.ciudad||'—'}</span>
        <div style="flex:2;">
          <div style="background:#1e293b;border-radius:3px;height:6px;">
            <div style="background:#6366f1;height:6px;border-radius:3px;width:${Math.round((c.pedidos/maxCiud)*100)}%;"></div>
          </div>
        </div>
        <span style="color:#94a3b8;font-size:11px;min-width:54px;text-align:right;">${fmt2(c.pedidos)} pedidos</span>
      </div>`).join('');
  }

  // ── Campañas activas ──────────────────────────────────────────────────────
  const cBody = document.getElementById('dash-campanas');
  if (!data.campanas_activas || !data.campanas_activas.length) {
    cBody.innerHTML = '<tr class="empty-row"><td colspan="5">Sin campañas</td></tr>';
  } else {
    cBody.innerHTML = data.campanas_activas.map(c=>`
      <tr>
        <td style="font-weight:700;">${c.nombre}</td>
        <td><span class="badge badge-gray">${c.canal||'—'}</span></td>
        <td>${badgeEstadoCamp(c.estado)}</td>
        <td>${fmtM(c.presupuesto)}</td>
        <td style="color:#34d399;">${fmtM(c.resultado_ventas)}</td>
      </tr>`).join('');
  }

  // ── Contenido reciente ────────────────────────────────────────────────────
  const coBody = document.getElementById('dash-contenido');
  if (!data.contenido_reciente || !data.contenido_reciente.length) {
    coBody.innerHTML = '<tr class="empty-row"><td colspan="4">Sin contenido</td></tr>';
  } else {
    coBody.innerHTML = data.contenido_reciente.map(c=>`
      <tr><td>${c.tipo}</td><td>${c.plataforma}</td><td>${badgeEstadoCont(c.estado)}</td><td>${fmt(c.alcance)}</td></tr>`).join('');
  }

  // ── Instagram KPIs ───────────────────────────────────────────────────────
  const ig = data.instagram || {};
  document.getElementById('ig-posts30').textContent    = fmt2(ig.posts_30d);
  document.getElementById('ig-posts-total').textContent = 'Total: '+fmt2(ig.total_posts);
  document.getElementById('ig-likes30').textContent    = fmt2(ig.likes_30d);
  document.getElementById('ig-avg-likes').textContent  = 'Promedio: '+fmt2(ig.avg_likes)+' ♥/post';
  document.getElementById('ig-comments30').textContent = fmt2(ig.comentarios_30d);

  // ── Instagram Top Posts ───────────────────────────────────────────────────
  const igEl = document.getElementById('dash-ig-posts');
  const topPosts = ig.top_posts || [];
  // ── Token status badge ───────────────────────────────────────────────────
  const igStatusEl = document.getElementById('ig-token-status');
  if (igStatusEl && ig.configurado) {
    const daysLeft = ig.token_days_left || 0;
    const expired  = ig.token_expired;
    const refreshed = ig.token_refreshed;
    const nearExp  = ig.token_near_expiry;
    if (expired) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#7f1d1d';
      igStatusEl.style.color = '#fca5a5';
      igStatusEl.textContent = '⚠️ Token expirado — renovar manualmente';
    } else if (refreshed) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#14532d';
      igStatusEl.style.color = '#86efac';
      igStatusEl.textContent = '🔄 Token renovado automáticamente (' + daysLeft + 'd)';
    } else if (nearExp) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#78350f';
      igStatusEl.style.color = '#fde68a';
      igStatusEl.textContent = '⚠️ Token vence en ' + daysLeft + ' días';
    } else if (daysLeft > 0) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#0f2d1a';
      igStatusEl.style.color = '#4ade80';
      igStatusEl.textContent = '🔑 Token válido — ' + daysLeft + 'd restantes';
    } else {
      igStatusEl.style.display = 'none';
    }
    // Si se auto-renovó silenciosamente, notificar una vez
    if (refreshed && !window._igRefreshToastShown) {
      window._igRefreshToastShown = true;
      showToast('🔄 Token de Instagram renovado automáticamente por 60 días', 'success');
    }
  }

  if (!ig.configurado) {
    igEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">⚠️ Instagram no configurado — agrega INSTAGRAM_TOKEN en Render</div>';
  } else if (!topPosts.length) {
    igEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">Sin posts — haz clic en ↻ IG para sincronizar</div>';
  } else {
    igEl.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:12px;">' +
      topPosts.map(p => {
        const eng = (p.likes||0) + (p.comentarios||0)*3;
        const desc = (p.descripcion||'').slice(0,80) + ((p.descripcion||'').length>80?'…':'');
        const date = (p.publicado_en||'').slice(0,10);
        const tipo = p.tipo||'IMAGE';
        const icon = tipo==='VIDEO'?'🎬':tipo==='CAROUSEL_ALBUM'?'🗂️':'📸';
        return `<div style="flex:1;min-width:200px;max-width:260px;background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:11px;color:#94a3b8;">${icon} ${tipo}</span>
            <span style="font-size:10px;color:#64748b;">${date}</span>
          </div>
          <div style="font-size:11px;color:#cbd5e1;margin-bottom:8px;line-height:1.4;">${desc||'(sin caption)'}</div>
          <div style="display:flex;gap:12px;font-size:11px;">
            <span style="color:#e1306c;">♥ ${p.likes||0}</span>
            <span style="color:#64748b;">💬 ${p.comentarios||0}</span>
            <span style="color:#d4af37;margin-left:auto;">eng ${eng}</span>
          </div>
          ${p.url_permalink?`<a href="${p.url_permalink}" target="_blank" style="display:block;margin-top:6px;font-size:10px;color:#6366f1;">Ver en IG →</a>`:''}
        </div>`;
      }).join('') +
    '</div>';
  }

  // ── Por canal ─────────────────────────────────────────────────────────────
  const chEl = document.getElementById('dash-canales');
  if (!data.por_canal || !data.por_canal.length) {
    chEl.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">Sin datos de campañas por canal</div>';
  } else {
    chEl.innerHTML = data.por_canal.map(ch=>`
      <div style="padding:10px 0;border-bottom:1px solid #1e293b;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-weight:700;">${ch.canal}</span>
          <span style="color:#34d399;">${fmtM(ch.ventas_total)} ventas</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;">
          <span>${ch.campanas} campaña${ch.campanas!=1?'s':''} · ${fmtM(ch.presupuesto_total)} invertido</span>
        </div>
      </div>`).join('');
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// CAMPAÑAS
// ──────────────────────────────────────────────────────────────────────────────
async function loadCampanas() {
  const estado = document.getElementById('camp-filtro-estado').value;
  const url = '/api/marketing/campanas'+(estado?'?estado='+estado:'');
  const rows = await fetch(url).then(r=>r.json());
  const body = document.getElementById('camp-body');
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="11">Sin campañas. Crea la primera.</td></tr>'; return; }
  body.innerHTML = rows.map(r=>{
    const roi = r.presupuesto_gastado>0 ? ((r.resultado_ventas-r.presupuesto_gastado)/r.presupuesto_gastado*100).toFixed(1) : null;
    return `<tr>
      <td style="color:#64748b;">${r.id}</td>
      <td style="font-weight:700;">${r.nombre}</td>
      <td><span class="badge badge-gray">${r.tipo}</span></td>
      <td>${r.canal||'—'}</td>
      <td>${badgeEstadoCamp(r.estado)}</td>
      <td>${fmtM(r.presupuesto)}</td>
      <td>${fmtM(r.presupuesto_gastado)}</td>
      <td style="color:#34d399;">${fmtM(r.resultado_ventas)}</td>
      <td>${roiBadge(roi)}</td>
      <td><span class="badge badge-purple">${r.num_influencers}</span></td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="editCampana(${r.id})">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="deleteCampana(${r.id},'${r.nombre.replace(/'/g,"\\'")}')">🗑</button>
      </td>
    </tr>`;
  }).join('');
}

function openCampanaModal(data) {
  document.getElementById('camp-edit-id').value = '';
  document.getElementById('modal-campana-title').textContent = 'Nueva Campaña';
  ['nombre','canal','sku','notas'].forEach(f=>document.getElementById('camp-'+f).value='');
  ['presupuesto','obj-uds','res-uds','res-ventas'].forEach(f=>document.getElementById('camp-'+f).value=0);
  document.getElementById('camp-inicio').value='';
  document.getElementById('camp-fin').value='';
  document.getElementById('camp-tipo').value='Digital';
  document.getElementById('camp-estado').value='Planificada';
  document.getElementById('modal-campana').classList.add('open');
}

async function editCampana(id) {
  const r = await fetch(`/api/marketing/campanas/${id}`).then(r=>r.json());
  document.getElementById('camp-edit-id').value = id;
  document.getElementById('modal-campana-title').textContent = 'Editar Campaña';
  document.getElementById('camp-nombre').value = r.nombre||'';
  document.getElementById('camp-canal').value = r.canal||'';
  document.getElementById('camp-sku').value = r.sku_objetivo||'';
  document.getElementById('camp-notas').value = r.notas||'';
  document.getElementById('camp-presupuesto').value = r.presupuesto||0;
  document.getElementById('camp-obj-uds').value = r.objetivo_unidades||0;
  document.getElementById('camp-res-uds').value = r.resultado_unidades||0;
  document.getElementById('camp-res-ventas').value = r.resultado_ventas||0;
  document.getElementById('camp-inicio').value = r.fecha_inicio||'';
  document.getElementById('camp-fin').value = r.fecha_fin||'';
  document.getElementById('camp-tipo').value = r.tipo||'Digital';
  document.getElementById('camp-estado').value = r.estado||'Planificada';
  document.getElementById('modal-campana').classList.add('open');
}

async function saveCampana() {
  const id = document.getElementById('camp-edit-id').value;
  const body = {
    nombre: document.getElementById('camp-nombre').value.trim(),
    tipo: document.getElementById('camp-tipo').value,
    estado: document.getElementById('camp-estado').value,
    canal: document.getElementById('camp-canal').value.trim(),
    presupuesto: parseFloat(document.getElementById('camp-presupuesto').value)||0,
    fecha_inicio: document.getElementById('camp-inicio').value||null,
    fecha_fin: document.getElementById('camp-fin').value||null,
    sku_objetivo: document.getElementById('camp-sku').value.trim(),
    objetivo_unidades: parseInt(document.getElementById('camp-obj-uds').value)||0,
    resultado_unidades: parseInt(document.getElementById('camp-res-uds').value)||0,
    resultado_ventas: parseFloat(document.getElementById('camp-res-ventas').value)||0,
    notas: document.getElementById('camp-notas').value.trim()
  };
  if(!body.nombre) { showAlert('camp-alert','El nombre es obligatorio','error'); return; }
  const url = id ? `/api/marketing/campanas/${id}` : '/api/marketing/campanas';
  const method = id ? 'PUT' : 'POST';
  const resp = await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await resp.json();
  if(data.ok||data.id) {
    closeModal('modal-campana');
    showAlert('camp-alert', id?'Campaña actualizada':'Campaña creada exitosamente');
    loadCampanas();
  } else { showAlert('camp-alert', data.error||'Error','error'); }
}

async function deleteCampana(id, nombre) {
  if(!confirm(`¿Eliminar campaña "${nombre}"? Se borrarán todas las asignaciones y contenido relacionado.`)) return;
  const resp = await fetch(`/api/marketing/campanas/${id}`,{method:'DELETE'});
  const data = await resp.json();
  if(data.ok) { showAlert('camp-alert','Campaña eliminada'); loadCampanas(); }
  else showAlert('camp-alert',data.error||'Error','error');
}

// ──────────────────────────────────────────────────────────────────────────────
// INFLUENCERS
// ──────────────────────────────────────────────────────────────────────────────
// ─── PAGOS REALIZADOS — vista cronológica para Marketing ───────────────────
let _PAGOS_INF_CACHE = [];

async function bulkRegenerarLegacy() {
  // Paso 1: dry_run para listar candidatos
  let drylist;
  try {
    const r = await fetch('/api/comprobantes-pago/regenerar-legacy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dry_run: true})
    });
    if (r.status === 403) {
      showToast('Solo administradores pueden corregir comprobantes en bloque.', 'error');
      return;
    }
    drylist = await r.json();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
    return;
  }
  const cands = (drylist && drylist.candidatos) || [];
  if (cands.length === 0) {
    showToast('No hay comprobantes legacy con dispatch incorrecto. Todo en orden.', 'ok');
    return;
  }
  // Paso 2: confirmar con el listado
  const preview = cands.slice(0, 6).map(x => '· ' + x.numero_ce + ' (' + (x.beneficiario||'?') + ')').join('\n');
  const extra = cands.length > 6 ? '\n  + ' + (cands.length-6) + ' mas...' : '';
  if (!confirm('Se detectaron ' + cands.length + ' comprobante(s) marcados como Espagiria que deberian ser ANIMUS Lab:\n\n' + preview + extra + '\n\nRegenerar todos? El PDF de cada uno se reemplaza con la version correcta.')) return;
  // Paso 3: aplicar
  showToast('Regenerando ' + cands.length + ' PDFs...', 'info');
  try {
    const r = await fetch('/api/comprobantes-pago/regenerar-legacy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dry_run: false})
    });
    const d = await r.json();
    const ok = (d.count_corregidos || 0);
    const err = (d.count_errores || 0);
    if (err > 0) {
      showToast(ok + ' corregidos, ' + err + ' con error. Ver consola.', 'error');
      console.warn('Errores bulk regenerar:', d.errores);
    } else {
      showToast(ok + ' comprobantes corregidos. Ahora dicen ANIMUS Lab.', 'ok');
    }
    setTimeout(() => loadPagosInfluencers(), 800);
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function regenerarCE(compId, numCE) {
  if (!confirm('Re-generar PDF del ' + numCE + '?\n\nEsto corrige empresa (ANIMUS vs Espagiria), datos bancarios y montos en el PDF almacenado.')) return;
  try {
    const r = await fetch('/api/comprobantes-pago/' + compId + '/regenerar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({forzar_obs: true})
    });
    const d = await r.json();
    if (d.ok) {
      showToast('PDF regenerado: ' + d.numero_ce + ' · ' + d.empresa + ' · ' + d.pdf_size_kb + ' KB', 'ok');
      setTimeout(() => loadPagosInfluencers(), 600);
    } else {
      showToast('Error: ' + (d.error || 'Fallo al regenerar'), 'error');
    }
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

// ─── Atribución de ventas via discount codes ───────────────────────────
async function loadAtribucion() {
  const body = document.getElementById('atrib-body');
  const kpiEl = document.getElementById('atrib-kpis');
  if (body) body.innerHTML = '<tr class="empty-row"><td colspan="8"><span class="spin"></span></td></tr>';
  try {
    const r = await fetch('/api/marketing/atribucion-influencers');
    const d = await r.json();
    if (!d.ok) {
      body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:#dc2626;">Error: ' + (d.error||'desconocido') + '</td></tr>';
      return;
    }
    const k = d.kpis || {};
    const list = d.influencers || [];

    // KPIs
    kpiEl.innerHTML = [
      {label:'Influencers con código', val: k.influencers_con_code||0, color:'#34d399'},
      {label:'Pedidos atribuidos',     val: k.pedidos_atribuidos||0,   color:'#60a5fa'},
      {label:'Revenue atribuido',      val: fmtM(k.revenue_atribuido||0), color:'#f59e0b'},
      {label:'Inversión total',        val: fmtM(k.inversion_total||0),  color:'#a78bfa'},
      {label:'ROI global',             val: (k.roi_global_pct==null?'—':k.roi_global_pct+'%'),
        color: k.roi_global_pct==null ? '#64748b' : (k.roi_global_pct >= 100 ? '#34d399' : (k.roi_global_pct >= 0 ? '#fbbf24' : '#ef4444'))},
    ].map(c=>`<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 12px;">
      <div style="font-size:18px;font-weight:800;color:${c.color};line-height:1;">${c.val}</div>
      <div style="font-size:10px;color:#64748b;margin-top:4px;">${c.label}</div>
    </div>`).join('');

    if (!list.length) {
      body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:#64748b;text-align:center;padding:18px;">Ningún influencer tiene discount code asignado todavía. Editá un influencer y agregá el código (ej: ANIMUS_LAURA10).</td></tr>';
      return;
    }
    body.innerHTML = list.map(x => {
      const roi = x.roi_pct;
      const roiCol = (roi==null) ? '#64748b' : (roi >= 100 ? '#34d399' : (roi >= 0 ? '#fbbf24' : '#ef4444'));
      const roiTxt = (roi==null) ? '—' : roi + '%';
      return `<tr>
        <td style="font-weight:600;">${x.nombre||'—'}${x.usuario_red?'<div style="font-size:10px;color:#64748b;font-weight:400;">@'+x.usuario_red+'</div>':''}</td>
        <td><code style="background:#0f172a;color:#34d399;padding:2px 8px;border-radius:4px;font-size:11px;">${x.discount_code}</code></td>
        <td style="text-align:right;">${x.n_pedidos||0}</td>
        <td style="text-align:right;color:#94a3b8;">${x.unidades||0}</td>
        <td style="text-align:right;font-weight:700;color:#34d399;">${fmtM(x.revenue_total||0)}</td>
        <td style="text-align:right;color:#94a3b8;">${fmtM(x.invertido||0)}</td>
        <td style="text-align:right;font-weight:700;color:${roiCol};">${roiTxt}</td>
        <td style="font-size:11px;color:#64748b;">${(x.ultimo_pedido||'').slice(0,10)||'—'}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:#dc2626;">Error de red: ' + e.message + '</td></tr>';
  }
}

async function loadPagosInfluencers() {
  // Trigger atribución en paralelo (independiente de pagos)
  loadAtribucion();
  const body = document.getElementById('pag-body');
  if (body) body.innerHTML = '<tr class="empty-row"><td colspan="7"><span class="spin"></span></td></tr>';
  try {
    const r = await fetch('/api/marketing/pagos-influencers');
    const d = await r.json();
    _PAGOS_INF_CACHE = d.pagos || [];
    // Llenar select de meses con los disponibles + opción 'Todos'
    const mesSel = document.getElementById('pag-mes');
    if (mesSel) {
      const cur = mesSel.value;
      mesSel.innerHTML = '<option value="">Todos los meses</option>'
        + (d.meses_disponibles || []).map(m => '<option value="' + m + '"' + (m===cur?' selected':'') + '>' + m + '</option>').join('');
    }
    // KPIs
    const kpis = d.kpis || {};
    const kpiBar = document.getElementById('pag-kpi-bar');
    if (kpiBar) {
      kpiBar.style.display = 'grid';
      kpiBar.innerHTML = [
        {label:'Pagado este mes', val:fmtM(kpis.pagos_mes_valor||0), sub:(kpis.pagos_mes_count||0)+' pagos', color:'#34d399'},
        {label:'Pagado en 2026', val:fmtM(kpis.pagos_anio_valor||0), sub:(kpis.pagos_anio_count||0)+' pagos', color:'#60a5fa'},
        {label:'Pendientes (todos)', val:fmtM(kpis.total_pendiente||0), sub:'sin ejecutar', color:'#f59e0b'},
        {label:'Total mostrado', val:fmtM(kpis.total_pagado||0), sub:_PAGOS_INF_CACHE.length+' filas', color:'#a78bfa'},
      ].map(k => '<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:12px 16px;">'
        + '<div style="font-size:18px;font-weight:800;color:'+k.color+';">'+k.val+'</div>'
        + '<div style="font-size:11px;color:#64748b;margin-top:2px;">'+k.label+'</div>'
        + '<div style="font-size:10px;color:#475569;margin-top:1px;">'+k.sub+'</div>'
      + '</div>').join('');
    }
    renderPagos();
  } catch(e) {
    if (body) body.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#f87171;padding:20px;">Error: '+e.message+'</td></tr>';
  }
}

function renderPagos() {
  const body = document.getElementById('pag-body');
  if (!body) return;
  const q = (document.getElementById('pag-search')||{value:''}).value.toLowerCase();
  const mes = (document.getElementById('pag-mes')||{value:''}).value;
  const estado = (document.getElementById('pag-estado')||{value:''}).value;
  const list = _PAGOS_INF_CACHE.filter(p => {
    if (estado && p.estado !== estado) return false;
    if (mes && (p.fecha||'').slice(0,7) !== mes) return false;
    if (q) {
      const hay = ((p.influencer_nombre||'')+(p.concepto||'')+(p.numero_oc||'')).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
  if (!list.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="7" style="color:#64748b;text-align:center;padding:24px;">Sin pagos para los filtros seleccionados.</td></tr>';
    return;
  }
  body.innerHTML = list.map(p => {
    const fecha = (p.fecha || '').slice(0,10);
    const estadoBadge = p.estado === 'Pagada'
      ? '<span style="background:#064e3b;color:#34d399;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x2713; Pagada</span>'
      : '<span style="background:#78350f;color:#fcd34d;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x23F3; Pendiente</span>';
    let comprobante = '<span style="color:#475569;font-size:11px;">—</span>';
    if (p.comprobante_id && p.numero_ce) {
      comprobante = '<a href="/api/comprobantes-pago/'+p.comprobante_id+'/pdf" target="_blank" '
        + 'style="color:#1F5F5B;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:4px;background:#f0fdfa;padding:3px 10px;border-radius:6px;font-size:12px;">'
        + '&#x1F4C4; '+p.numero_ce+'</a>';
    } else if (p.estado === 'Pagada') {
      comprobante = '<span style="color:#dc2626;font-size:11px;font-style:italic;" title="Pago hecho antes del feature de comprobantes">sin CE</span>';
    }
    // Botón regenerar siempre visible junto al comprobante (corrige PDFs viejos)
    if (p.comprobante_id) {
      comprobante += ' <button onclick="regenerarCE('+p.comprobante_id+',\''+(p.numero_ce||'')+'\')" '
        + 'title="Re-generar PDF (corrige empresa, banco, monto)" '
        + 'style="background:none;border:none;cursor:pointer;font-size:13px;padding:0 2px;opacity:0.55;" '
        + '>&#x1F504;</button>';
    }
    const ocStr = p.numero_oc
      ? '<span style="font-family:monospace;font-size:11px;color:#94a3b8;">'+p.numero_oc+'</span>'
      : '—';
    return '<tr>'
      + '<td style="font-size:12px;color:#cbd5e1;">'+fecha+'</td>'
      + '<td style="font-weight:700;">'+(p.influencer_nombre||'—')
        + (p.inf_email ? '<div style="font-size:11px;color:#64748b;font-weight:400;">'+p.inf_email+'</div>' : '')
      + '</td>'
      + '<td style="font-size:12px;color:#94a3b8;">'+(p.concepto||'—')+'</td>'
      + '<td style="text-align:right;font-weight:700;color:#1F5F5B;">'+fmtM(p.valor||0)+'</td>'
      + '<td>'+ocStr+'</td>'
      + '<td>'+comprobante+'</td>'
      + '<td>'+estadoBadge+'</td>'
      + '</tr>';
  }).join('');
}

// Cache global de influencers — verHistorial lookup. Antes se serializaba la
// fila completa en el atributo onclick, lo cual corrompía el HTML porque las
// comillas dobles del JSON cerraban el atributo prematuramente. Eso hacía
// que TODOS los botones de la fila (Editar, Pagar, Dar de baja) dejaran de
// funcionar visualmente.
let _INFLUENCERS_CACHE = {};

async function loadInfluencers() {
  const q = document.getElementById('inf-search').value;
  const url = '/api/marketing/influencers-panel'+(q?'?q='+encodeURIComponent(q):'');
  let data;
  try { data = await fetch(url).then(r=>r.json()); } catch(e) { data = {influencers:[], kpis:{}}; }
  // Show debug error if backend returned one
  if(data._error) { console.warn('[panel error]', data._error, data._trace); }
  const infs = data.influencers || [];
  // Llenar cache para verHistorial — pasamos solo ID por onclick, no JSON
  _INFLUENCERS_CACHE = {};
  for (const inf of infs) _INFLUENCERS_CACHE[inf.id] = inf;
  const kpis = data.kpis || {};
  const kpiBar = document.getElementById('inf-kpi-bar');
  if(kpiBar) {
    kpiBar.style.display = 'grid';
    kpiBar.innerHTML = [
      {label:'Influencers activos', val: kpis.total_activos||0, color:'#34d399'},
      {label:'Pagado 2025', val: fmtM(kpis.pagado_anio||0), color:'#818cf8'},
      {label:'Pagado este mes', val: fmtM(kpis.pagado_mes||0), color:'#60a5fa'},
      {label:'Pendiente pago', val: fmtM(kpis.total_pendiente||0), color:'#f59e0b'},
    ].map(k=>`<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:12px 16px;">`
      +`<div style="font-size:20px;font-weight:800;color:${k.color};">${k.val}</div>`
      +`<div style="font-size:11px;color:#64748b;margin-top:2px;">${k.label}</div>`
      +'</div>').join('');
  }
  const body = document.getElementById('inf-body');
  if(!infs.length) {
    const errMsg = data._error ? ` (error: ${data._error.substring(0,80)})` : '';
    body.innerHTML=`<tr class="empty-row"><td colspan="12">Sin influencers registrados${errMsg}.</td></tr>`;
    return;
  }
  body.innerHTML = infs.map((r, idx)=>{
    const seg = r.seguidores>=1000?(r.seguidores/1000).toFixed(1)+'K':r.seguidores;
    const banco = r.banco
      ? `<span style="color:#94a3b8;">${r.banco}</span><br><span style="font-size:11px;color:#64748b;">${r.cuenta_bancaria||'\u2014'}</span>`
      : '<span style="color:#475569;">Sin datos</span>';
    let estadoBadge;
    if(r.tiene_pendiente) {
      // Solicitud activa esperando pago (Jefferson la creo y aun no se transfirio)
      estadoBadge = '<span style="background:#78350f;color:#fcd34d;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">\u23f3 Pendiente</span>';
    } else if(r.toca_pagar) {
      // Ciclo de pago vencido y no hay solicitud activa todavia \u2192 recordatorio a Jefferson
      const dias = r.dias_desde_ultimo_pago || 0;
      estadoBadge = '<span style="background:#854d0e;color:#fde047;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;" title="Hace '+dias+' dias del ultimo pago. Ciclo: '+r.ciclo_pago+'">\u23f0 Toca pagar</span>';
    } else if(r.pagos_count>0) {
      // Tiene al menos un pago confirmado (OC pagada)
      estadoBadge = '<span style="background:#064e3b;color:#34d399;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">\u2713 Al d\u00eda</span>';
    } else {
      // Sin actividad relevante: no badge (decision Sebastian 2026-04-28)
      estadoBadge = '';
    }
    const ne = (r.nombre||'').replace(/'/g,"\\'");
    const be = (r.banco||'').replace(/'/g,"\\'");
    const ce = (r.cuenta_bancaria||'').replace(/'/g,"\\'");
    const de = (r.cedula_nit||'').replace(/'/g,"\\'");
    const te = (r.tipo_cuenta||'Ahorros').replace(/'/g,"\\'");
    return `<tr>`
      +`<td style="color:#64748b;">${idx+1}</td>`
      +`<td style="font-weight:700;">${r.nombre}</td>`
      +`<td><span class="badge badge-gray">${r.red_social}</span></td>`
      +`<td style="color:#818cf8;">${r.usuario_red||'\u2014'}</td>`
      +`<td>${seg}</td>`
      +`<td>${r.engagement_rate?r.engagement_rate+'%':'\u2014'}</td>`
      +`<td>${r.nicho||'\u2014'}</td>`
      +`<td>${r.tarifa?fmtM(r.tarifa):'\u2014'}</td>`
      +`<td style="font-size:12px;color:#94a3b8;">${r.email||'\u2014'}</td>`
      +`<td style="font-size:12px;">${banco}</td>`
      +`<td>${estadoBadge}</td>`
      +`<td style="white-space:nowrap;">`
        +`<button class="btn btn-outline btn-sm" onclick="verHistorial(${r.id})" title="Ver historial" style="color:#818cf8;border-color:#818cf8;">&#x1F4CB;</button> `
        +`<button class="btn btn-outline btn-sm" onclick="editInfluencer(${r.id})" title="Editar">&#x270F;&#xFE0F;</button> `
        +`<button class="btn btn-primary btn-sm" onclick="solicitarPagoInf(${r.id},'${ne}',${r.tarifa||0},'${be}','${ce}','${de}','${te}')" title="Solicitar pago">&#x1F4B8;</button> `
        +`<button class="btn btn-danger btn-sm" onclick="abrirDarDeBaja(${r.id},'${ne}')" title="Dar de baja">&#x26D4;</button>`
      +'</td>'
      +'</tr>';
  }).join('');
}

function openInfluencerModal() {
  document.getElementById('inf-edit-id').value='';
  document.getElementById('modal-inf-title').textContent='Nuevo Influencer';
  ['nombre','usuario','nicho','email','tel','notas','banco','cuenta','cedula'].forEach(f=>document.getElementById('inf-'+f).value='');
  ['seguidores','er','tarifa'].forEach(f=>document.getElementById('inf-'+f).value=0);
  document.getElementById('inf-red').value='Instagram';
  document.getElementById('inf-estado').value='Activo';
  document.getElementById('inf-tipo-cta').value='Ahorros';
  document.getElementById('modal-influencer').classList.add('open');
}

async function editInfluencer(id) {
  const r = await fetch(`/api/marketing/influencers/${id}`).then(r=>r.json());
  document.getElementById('inf-edit-id').value=id;
  document.getElementById('modal-inf-title').textContent='Editar Influencer';
  document.getElementById('inf-nombre').value=r.nombre||'';
  document.getElementById('inf-usuario').value=r.usuario_red||'';
  document.getElementById('inf-nicho').value=r.nicho||'';
  document.getElementById('inf-email').value=r.email||'';
  document.getElementById('inf-tel').value=r.telefono||'';
  document.getElementById('inf-notas').value=r.notas||'';
  document.getElementById('inf-seguidores').value=r.seguidores||0;
  document.getElementById('inf-er').value=r.engagement_rate||0;
  document.getElementById('inf-tarifa').value=r.tarifa||0;
  document.getElementById('inf-red').value=r.red_social||'Instagram';
  document.getElementById('inf-estado').value=r.estado||'Activo';
  document.getElementById('inf-banco').value=r.banco||'';
  document.getElementById('inf-tipo-cta').value=r.tipo_cuenta||'Ahorros';
  document.getElementById('inf-cuenta').value=r.cuenta_bancaria||'';
  document.getElementById('inf-cedula').value=r.cedula_nit||'';
  const dcEl = document.getElementById('inf-discount-code');
  if(dcEl) dcEl.value = r.discount_code || '';
  const ccEl = document.getElementById('inf-ciclo-pago');
  if(ccEl) ccEl.value = r.ciclo_pago || 'Mensual';
  document.getElementById('modal-influencer').classList.add('open');
}

async function saveInfluencer() {
  const id = document.getElementById('inf-edit-id').value;
  const body = {
    nombre: document.getElementById('inf-nombre').value.trim(),
    red_social: document.getElementById('inf-red').value,
    usuario_red: document.getElementById('inf-usuario').value.trim(),
    seguidores: parseInt(document.getElementById('inf-seguidores').value)||0,
    engagement_rate: parseFloat(document.getElementById('inf-er').value)||0,
    nicho: document.getElementById('inf-nicho').value.trim(),
    tarifa: parseFloat(document.getElementById('inf-tarifa').value)||0,
    estado: document.getElementById('inf-estado').value,
    email: document.getElementById('inf-email').value.trim(),
    telefono: document.getElementById('inf-tel').value.trim(),
    notas: document.getElementById('inf-notas').value.trim(),
    banco: document.getElementById('inf-banco').value.trim(),
    tipo_cuenta: document.getElementById('inf-tipo-cta').value,
    cuenta_bancaria: document.getElementById('inf-cuenta').value.trim(),
    cedula_nit: document.getElementById('inf-cedula').value.trim(),
    discount_code: (document.getElementById('inf-discount-code')||{value:''}).value.trim().toUpperCase(),
    ciclo_pago: (document.getElementById('inf-ciclo-pago')||{value:'Mensual'}).value
  };
  if(!body.nombre) { showAlert('inf-alert','El nombre es obligatorio','error'); return; }
  const url = id ? `/api/marketing/influencers/${id}` : '/api/marketing/influencers';
  const method = id?'PUT':'POST';
  const resp = await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await resp.json();
  if(data.ok||data.id) { closeModal('modal-influencer'); showAlert('inf-alert',id?'Influencer actualizado':'Influencer creado'); loadInfluencers(); }
  else showAlert('inf-alert',data.error||'Error','error');
}

function abrirDarDeBaja(id, nombre) {
  document.getElementById('baja-inf-id').value = id;
  document.getElementById('baja-inf-nombre').textContent = nombre;
  document.getElementById('baja-motivo-tipo').value = 'Pausa temporal';
  document.getElementById('baja-observacion').value = '';
  document.getElementById('modal-dar-baja').classList.add('open');
}
async function confirmarDarDeBaja() {
  const id = document.getElementById('baja-inf-id').value;
  const motivo = document.getElementById('baja-motivo-tipo').value;
  const obs    = document.getElementById('baja-observacion').value;
  const resp = await fetch(`/api/marketing/influencers/${id}/dar-baja`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({motivo, observacion: obs})
  });
  const data = await resp.json();
  if(data.ok) {
    closeModal('modal-dar-baja');
    showAlert('inf-alert',`Influencer dado de baja: ${motivo}`,'warning');
    loadInfluencers();
  } else showAlert('inf-alert', data.error||'Error','error');
}

function solicitarPagoInf(id, nombre, tarifa, banco, cuenta, cedula, tipoCta) {
  document.getElementById('pago-inf-id').value = id;
  document.getElementById('pago-inf-nombre').textContent = nombre;
  document.getElementById('pago-valor').value = tarifa||'';
  document.getElementById('pago-concepto').value = '';
  const prev = document.getElementById('pago-banco-preview');
  if(banco) {
    prev.innerHTML = '<b>Beneficiario:</b> '+nombre+'<br>'
      +'<b>Banco:</b> '+banco+'<br>'
      +'<b>Tipo:</b> '+(tipoCta||'Ahorros')+'<br>'
      +'<b>Cuenta/Cel:</b> '+(cuenta||'\u2014')+'<br>'
      +'<b>C\u00e9dula/NIT:</b> '+(cedula||'\u2014');
  } else {
    prev.innerHTML = '<span style="color:#f59e0b;">\u26a0\ufe0f Sin datos bancarios. Edita el influencer primero.</span>';
  }
  document.getElementById('pago-inf-alert').style.display='none';
  document.getElementById('modal-inf-pago').classList.add('open');
}

async function confirmarPagoInf() {
  const id = document.getElementById('pago-inf-id').value;
  const valor = parseFloat(document.getElementById('pago-valor').value)||0;
  const concepto = document.getElementById('pago-concepto').value.trim()||'Cuenta de cobro influencer';
  if(!valor) { showAlert('pago-inf-alert','Ingresa el valor a pagar','error'); return; }
  const fechaPub   = document.getElementById('pago-fecha-pub').value;
  const entregable = document.getElementById('pago-entregable').value;
  const resp = await fetch(`/api/marketing/influencers/${id}/solicitar-pago`,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({valor, concepto, fecha_publicacion:fechaPub, entregable})
  });
  const data = await resp.json();
  if(data.ok) {
    closeModal('modal-inf-pago');
    showAlert('inf-alert','Solicitud de pago creada correctamente');
    loadInfluencers();
  } else {
    showAlert('pago-inf-alert', data.error||'Error al crear solicitud','error');
  }
}


// ──────────────────────────────────────────────────────────────────────────────
// CONTENIDO
// ──────────────────────────────────────────────────────────────────────────────
// ─── Kanban de Contenido ───────────────────────────────────────────────
async function loadContenido() {
  try {
    const r = await fetch('/api/marketing/contenido/kanban');
    const d = await r.json();
    if (!d.ok) {
      showAlert('cont-alert', 'Error: ' + (d.error||'desconocido'), 'error');
      return;
    }
    const cols = d.columnas || [];
    cols.forEach(col => {
      const target = document.getElementById('kb-' + col.estado);
      const counter = document.getElementById('kb-c-' + col.estado);
      if (counter) counter.textContent = col.count;
      if (!target) return;
      if (!col.items.length) {
        target.innerHTML = '<div class="kanban-empty">Sin contenido</div>';
        return;
      }
      target.innerHTML = col.items.map(it => renderKanbanCard(it)).join('');
    });
  } catch (e) {
    showAlert('cont-alert', 'Error de red: ' + e.message, 'error');
  }
}

function renderKanbanCard(it) {
  const sku = it.sku_objetivo ? `<div class="sku">${esc(it.sku_objetivo)}</div>` : '';
  const titulo = it.mensaje_principal || it.caption || '(sin mensaje)';
  const tituloShort = titulo.length > 90 ? titulo.slice(0,90)+'…' : titulo;
  const meta = [];
  if (it.tipo) meta.push(`<span>${esc(it.tipo)}</span>`);
  if (it.plataforma && it.plataforma !== 'Instagram') meta.push(`<span>${esc(it.plataforma)}</span>`);
  if (it.influencer_nombre) {
    const code = it.influencer_code ? ` · <code style="color:#34d399;">${esc(it.influencer_code)}</code>` : '';
    meta.push(`<span>👤 ${esc(it.influencer_nombre)}${code}</span>`);
  }
  if (it.campana_nombre) meta.push(`<span>📢 ${esc(it.campana_nombre)}</span>`);
  if (it.fecha_programada) meta.push(`<span>📅 ${esc(it.fecha_programada)}</span>`);
  if (it.fecha_publicacion && it.estado === 'Publicado') meta.push(`<span>✅ ${esc(it.fecha_publicacion)}</span>`);

  let perf = '';
  if (it.estado === 'Performance' || it.estado === 'Publicado') {
    const stats = [];
    if (it.likes) stats.push(`❤️ <b>${fmt(it.likes)}</b>`);
    if (it.comentarios) stats.push(`💬 <b>${fmt(it.comentarios)}</b>`);
    if (it.alcance) stats.push(`👁 <b>${fmt(it.alcance)}</b>`);
    if (stats.length) perf = `<div class="perf">${stats.join(' · ')}</div>`;
  }

  let urlBtn = '';
  if (it.url_publicacion) {
    urlBtn = `<a href="${esc(it.url_publicacion)}" target="_blank" style="color:#60a5fa;font-size:11px;text-decoration:none;margin-right:8px;" onclick="event.stopPropagation();">🔗 Ver post</a>`;
  }

  return `<div class="kanban-card" onclick="editContenido(${it.id})">
    ${sku}
    <div class="titulo">${esc(tituloShort)}</div>
    <div class="meta">${meta.join('')}</div>
    ${perf}
    <div style="margin-top:6px;display:flex;justify-content:space-between;align-items:center;">
      ${urlBtn}
      <span style="margin-left:auto;">${kanbanMoveButtons(it)}</span>
    </div>
  </div>`;
}

function kanbanMoveButtons(it) {
  const seq = ['Brief','Produccion','Pendiente','Publicado','Performance'];
  const idx = seq.indexOf(it.estado_kanban || it.estado);
  let html = '';
  if (idx > 0) html += `<button onclick="event.stopPropagation();moveContenido(${it.id},'${seq[idx-1]}')" title="← ${seq[idx-1]}" style="background:none;border:none;color:#64748b;cursor:pointer;padding:2px 4px;font-size:13px;">←</button>`;
  if (idx >= 0 && idx < seq.length-1) html += `<button onclick="event.stopPropagation();moveContenido(${it.id},'${seq[idx+1]}')" title="→ ${seq[idx+1]}" style="background:none;border:none;color:#a78bfa;cursor:pointer;padding:2px 4px;font-size:13px;">→</button>`;
  return html;
}

async function moveContenido(id, nuevoEstado) {
  try {
    const r = await fetch(`/api/marketing/contenido/${id}`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({estado: nuevoEstado})
    });
    const d = await r.json();
    if (d.ok) {
      loadContenido();
    } else {
      showAlert('cont-alert', 'Error: ' + (d.error||'no se pudo mover'), 'error');
    }
  } catch (e) {
    showAlert('cont-alert', 'Error de red: ' + e.message, 'error');
  }
}

async function openContenidoModal(estadoInicial) {
  document.getElementById('cont-edit-id').value='';
  document.getElementById('modal-cont-title').textContent='Nueva pieza de contenido';
  ['url','caption','sku','mensaje'].forEach(f=>{const el=document.getElementById('cont-'+f);if(el)el.value='';});
  ['likes','comentarios','alcance','conversiones'].forEach(f=>document.getElementById('cont-'+f).value=0);
  document.getElementById('cont-fecha').value='';
  const fp = document.getElementById('cont-fecha-prog'); if(fp) fp.value='';
  document.getElementById('cont-tipo').value='Reel';
  document.getElementById('cont-plataforma').value='Instagram';
  document.getElementById('cont-estado').value = (typeof estadoInicial === 'string' ? estadoInicial : 'Brief');
  await loadCampanasForSelect('cont-campana-sel');
  await loadInfluencersForSelect('cont-influencer-sel');
  document.getElementById('modal-contenido').classList.add('open');
}

async function editContenido(id) {
  const r_ = await fetch('/api/marketing/contenido/kanban').then(r=>r.json());
  let r = null;
  for (const col of (r_.columnas||[])) {
    const found = (col.items||[]).find(x=>x.id===id);
    if (found) { r = found; break; }
  }
  if(!r) return;
  document.getElementById('cont-edit-id').value=id;
  document.getElementById('modal-cont-title').textContent='Editar contenido';
  document.getElementById('cont-url').value=r.url_publicacion||'';
  document.getElementById('cont-caption').value=r.caption||'';
  const sku = document.getElementById('cont-sku'); if(sku) sku.value = r.sku_objetivo||'';
  const mens = document.getElementById('cont-mensaje'); if(mens) mens.value = r.mensaje_principal||'';
  const fp = document.getElementById('cont-fecha-prog'); if(fp) fp.value = r.fecha_programada||'';
  document.getElementById('cont-likes').value=r.likes||0;
  document.getElementById('cont-comentarios').value=r.comentarios||0;
  document.getElementById('cont-alcance').value=r.alcance||0;
  document.getElementById('cont-conversiones').value=r.conversiones||0;
  document.getElementById('cont-fecha').value=r.fecha_publicacion||'';
  document.getElementById('cont-tipo').value=r.tipo||'Reel';
  document.getElementById('cont-plataforma').value=r.plataforma||'Instagram';
  document.getElementById('cont-estado').value=(r.estado_kanban||r.estado||'Brief');
  await loadCampanasForSelect('cont-campana-sel');
  await loadInfluencersForSelect('cont-influencer-sel');
  if(r.campana_id) document.getElementById('cont-campana-sel').value=r.campana_id;
  if(r.influencer_id) document.getElementById('cont-influencer-sel').value=r.influencer_id;
  document.getElementById('modal-contenido').classList.add('open');
}

async function saveContenido() {
  const id = document.getElementById('cont-edit-id').value;
  const campSel = document.getElementById('cont-campana-sel').value;
  const infSel = document.getElementById('cont-influencer-sel').value;
  const body = {
    tipo: document.getElementById('cont-tipo').value,
    plataforma: document.getElementById('cont-plataforma').value,
    campana_id: campSel ? parseInt(campSel) : null,
    influencer_id: infSel ? parseInt(infSel) : null,
    fecha_publicacion: document.getElementById('cont-fecha').value||null,
    fecha_programada: (document.getElementById('cont-fecha-prog')||{value:''}).value||'',
    estado: document.getElementById('cont-estado').value,
    sku_objetivo: ((document.getElementById('cont-sku')||{value:''}).value||'').trim().toUpperCase(),
    mensaje_principal: ((document.getElementById('cont-mensaje')||{value:''}).value||'').trim(),
    url_publicacion: document.getElementById('cont-url').value.trim(),
    caption: document.getElementById('cont-caption').value.trim(),
    likes: parseInt(document.getElementById('cont-likes').value)||0,
    comentarios: parseInt(document.getElementById('cont-comentarios').value)||0,
    alcance: parseInt(document.getElementById('cont-alcance').value)||0,
    conversiones: parseInt(document.getElementById('cont-conversiones').value)||0,
  };
  const url = id ? `/api/marketing/contenido/${id}` : '/api/marketing/contenido';
  const method = id?'PUT':'POST';
  const resp = await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await resp.json();
  if(data.ok||data.id) { closeModal('modal-contenido'); showAlert('cont-alert',id?'Contenido actualizado':'Contenido registrado'); loadContenido(); }
  else showAlert('cont-alert',data.error||'Error','error');
}

async function deleteContenido(id) {
  if(!confirm('¿Eliminar esta pieza de contenido?')) return;
  const data = await fetch(`/api/marketing/contenido/${id}`,{method:'DELETE'}).then(r=>r.json());
  if(data.ok) { showAlert('cont-alert','Contenido eliminado'); loadContenido(); }
}

// ──────────────────────────────────────────────────────────────────────────────
// HELPERS — SELECT POPULATES
// ──────────────────────────────────────────────────────────────────────────────
async function loadCampanasForSelect(selId='brief-campana-sel') {
  const camps = await fetch('/api/marketing/campanas').then(r=>r.json());
  const sel = document.getElementById(selId);
  if(!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="">Sin campaña</option>' +
    camps.map(c=>`<option value="${c.id}">${c.nombre}</option>`).join('');
  if(current) sel.value=current;
}
async function loadInfluencersForSelect(selId) {
  const infs = await fetch('/api/marketing/influencers').then(r=>r.json());
  const sel = document.getElementById(selId);
  if(!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="">Sin influencer (interno)</option>' +
    infs.map(i=>`<option value="${i.id}">${i.nombre} (${i.red_social})</option>`).join('');
  if(current) sel.value=current;
}

// ──────────────────────────────────────────────────────────────────────────────
// AGENTES IA
// ──────────────────────────────────────────────────────────────────────────────
const AGENT_LABELS = {
  estacionalidad: 'Analizar estacionalidad', oportunidad: 'Detectar oportunidades',
  roi: 'Calcular ROI', tendencias: 'Ver tendencias', brief: 'Generar brief',
  pricing: 'Calcular precios promo', reorden: 'Predecir reórdenes',
  canibal: 'Detectar conflictos', contenido_auto: 'Generar contenido',
  alerta_stock: 'Ver alertas stock',
  estrategia: 'Generar estrategia del mes'
};

async function syncPlatform(platform, full) {
  const btn = document.getElementById('btn-sync-'+platform);
  const status = document.getElementById('sync-status');
  btn.disabled = true; btn.textContent = 'Sincronizando...';
  status.textContent = '';
  try {
    const resp = await fetch(`/api/marketing/sync/${platform}${full?'?full=1':''}`, {method:'POST'});
    const data = await resp.json();
    if(data.ok) {
      status.style.color = '#34d399';
      status.textContent = `✓ ${platform}: ${data.synced} registros sincronizados`;
      loadConnections();
      setTimeout(loadDashboard, 600);
    } else {
      status.style.color = '#f87171';
      let errMsg = data.error || 'Error al sincronizar';
      let det = data.detalle || '';
      // Detectar token Meta expirado (code 190) y mostrar mensaje claro
      if(det.includes('190') || det.includes('Session has expired') || det.includes('OAuthException')){
        errMsg = '🔑 Token de Instagram expirado — genera uno nuevo en developers.facebook.com/tools/explorer y pégalo abajo';
        det = '';
      } else if(det.includes('400') || det.includes('401')){
        errMsg = '🔑 Error de autenticación Meta — token inválido';
        det = '';
      } else if(det.length > 120){
        det = ' → ' + det.slice(0,120) + '...';
      } else if(det){
        det = ' → ' + det;
      }
      status.textContent = errMsg + det;
      // Si falla Instagram por auth, mostrar formulario de token
      if (platform === 'instagram') {
        document.getElementById('ig-token-form').style.display = 'block';
      }
    }
  } catch(e) {
    status.style.color = '#f87171';
    let msg = e.message || 'Error desconocido';
    if(msg.includes('<!DOCTYPE') || msg.includes('JSON')){
      msg = 'La sesión expiró — recarga la página (F5)';
    }
    status.textContent = '⚠️ ' + msg;
  } finally {
    btn.disabled = false; btn.textContent = '↻ Sync ' + (platform==='instagram'?'IG':platform.charAt(0).toUpperCase()+platform.slice(1));
  }
}

async function loadConnections() {
  try {
    const data = await fetch('/api/marketing/connections').then(r=>r.json());
    const conn = data.connected || {};
    [['shopify','shopify'],['ghl','ghl'],['instagram','ig']].forEach(([k,pid])=>{
      const el = document.getElementById('pill-'+pid);
      if(!el) return;
      el.className = 'platform-pill ' + (conn[k] ? 'pill-'+pid : 'pill-off');
    });
  } catch(e) {}
}

// ─── Feedback loop sobre agentes IA ────────────────────────────────────
let _AGENT_FEEDBACK_STATS = {};

async function loadFeedbackStats() {
  try {
    const r = await fetch('/api/marketing/agentes/feedback/stats');
    const d = await r.json();
    if (!d.ok) return;
    _AGENT_FEEDBACK_STATS = d.agentes || {};
    // Para cada agente con stats, inyectar/actualizar un tag de tasa de acierto
    // dentro de su card. La card se identifica por el botón btn-<agente>.
    Object.keys(_AGENT_FEEDBACK_STATS).forEach(ag => {
      const stats = _AGENT_FEEDBACK_STATS[ag];
      if (stats.tasa_acierto_pct == null) return;
      const btn = document.getElementById('btn-' + ag);
      if (!btn) return;
      const card = btn.closest('.agent-card') || btn.parentElement;
      if (!card) return;
      let tag = card.querySelector('.agent-feedback-tag');
      if (!tag) {
        tag = document.createElement('div');
        tag.className = 'agent-feedback-tag';
        tag.style.cssText = 'font-size:10px;color:#94a3b8;margin-bottom:6px;padding:3px 8px;background:#0f172a;border-radius:6px;display:inline-block;';
        // Insertar antes del botón
        btn.parentElement.insertBefore(tag, btn);
      }
      const col = stats.tasa_acierto_pct >= 70 ? '#34d399' :
                  (stats.tasa_acierto_pct >= 40 ? '#fbbf24' : '#ef4444');
      tag.innerHTML = `<span style="color:${col};font-weight:700;">${stats.tasa_acierto_pct}%</span> útil · ${stats.total} feedback`;
    });
  } catch(e) { /* silencioso */ }
}

function renderFeedbackBar(logId) {
  if (!logId) return '';
  return `<div class="feedback-bar" id="fb-bar-${logId}" style="display:flex;align-items:center;gap:8px;margin-top:14px;padding:10px 14px;background:#0f172a;border:1px solid #334155;border-radius:8px;">
    <span style="font-size:11px;color:#94a3b8;font-weight:600;">¿Te sirvió este análisis?</span>
    <button onclick="sendFeedback(${logId},'util',event)" style="background:#064e3b;color:#34d399;border:1px solid #065f46;padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">👍 Útil</button>
    <button onclick="sendFeedback(${logId},'ejecutado',event)" style="background:#1e3a8a;color:#60a5fa;border:1px solid #1d4ed8;padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">⚡ Ejecuté la acción</button>
    <button onclick="sendFeedback(${logId},'no_util',event)" style="background:#7f1d1d;color:#f87171;border:1px solid #991b1b;padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">👎 No sirvió</button>
    <span id="fb-status-${logId}" style="font-size:10px;color:#64748b;margin-left:auto;"></span>
  </div>`;
}

async function sendFeedback(logId, fb, ev) {
  if (ev) ev.stopPropagation();
  const status = document.getElementById('fb-status-' + logId);
  const bar = document.getElementById('fb-bar-' + logId);
  if (status) status.textContent = 'Enviando...';
  try {
    const r = await fetch('/api/marketing/agentes/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({log_id: logId, feedback: fb})
    });
    const d = await r.json();
    if (d.ok) {
      const labels = {util:'👍 Marcado como útil', ejecutado:'⚡ Acción registrada', no_util:'👎 Feedback registrado'};
      if (bar) bar.style.opacity = '0.5';
      if (status) status.textContent = labels[fb] || 'Registrado';
      loadFeedbackStats();
    } else {
      if (status) status.textContent = 'Error: ' + (d.error || 'no se pudo guardar');
    }
  } catch (e) {
    if (status) status.textContent = 'Error de red';
  }
}

async function runAgent(agente) {
  const btn = document.getElementById('btn-'+agente);
  const resultDiv = document.getElementById('result-'+agente);
  if(!btn||!resultDiv) return;
  btn.classList.add('running');
  btn.innerHTML = '<span class="spin"></span> Ejecutando...';
  resultDiv.classList.remove('show');

  let body = {};
  if(agente==='brief') {
    const sel = document.getElementById('brief-campana-sel');
    if(sel && sel.value) body.campana_id = parseInt(sel.value);
  }

  try {
    const resp = await fetch(`/api/marketing/agentes/${agente}`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    });
    const data = await resp.json();
    if(data.error) {
      resultDiv.innerHTML = `<pre style="color:#f87171;">Error: ${data.error}</pre>`;
    } else {
      resultDiv.innerHTML = formatAgentResult(agente, data) + renderFeedbackBar(data.log_id);

      // Master agent Estrategia: redirige a la sub-tab dedicada con el output
      // persistente. Así el jefe puede volver luego sin re-generar.
      if (agente === 'estrategia') {
        // Marcar como cargada y refrescar la vista persistente
        _loaded.estrategia = false; // forzar re-render
        await loadUltimaEstrategia();
        // Ir a la sub-tab Estrategia (dentro de Inteligencia)
        showSub('estrategia');
        // Scroll al inicio de la vista
        setTimeout(() => {
          const view = document.getElementById('estrategia-vista');
          if (view) view.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 250);
        showToast('✅ Estrategia generada — revisá el calendario y oportunidades', 'success');
      }
    }
    resultDiv.classList.add('show');
    loadAgentLog();
    loadFeedbackStats();
  } catch(e) {
    resultDiv.innerHTML = `<pre style="color:#f87171;">Error: ${e.message}</pre>`;
    resultDiv.classList.add('show');
  } finally {
    btn.classList.remove('running');
    btn.innerHTML = `<span>&#x25B6; ${AGENT_LABELS[agente]||agente}</span>`;
  }
}

function fmtIA(data) {
  if(!data.analisis_ia) return '';
  return `<div style="margin-top:14px;padding:14px;background:linear-gradient(135deg,rgba(212,175,55,.08),rgba(212,175,55,.03));border:1px solid rgba(212,175,55,.25);border-radius:10px">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
      <span style="font-size:15px">🤖</span>
      <span style="font-size:11px;font-weight:700;color:#d4af37;letter-spacing:.5px;text-transform:uppercase">Análisis IA — Claude</span>
    </div>
    <div style="font-size:13px;color:#e2e8f0;line-height:1.7;white-space:pre-line">${data.analisis_ia}</div>
  </div>`;
}

function formatAgentResult(agente, data) {
  let out = '';

  if(agente==='estacionalidad') {
    if(!data.alertas||!data.alertas.length) { out='✅ Sin alertas de estacionalidad en los próximos 120 días.'; }
    else {
      out += `📅 ${data.titulo}\n${'─'.repeat(40)}\n`;
      out += `Total alertas: ${data.total_alertas} | Críticos: ${data.criticos}\n\n`;
      data.alertas.forEach(a=>{
        const icon = a.estado==='critico'?'🔴':a.estado==='advertencia'?'🟡':'🟢';
        out += `${icon} ${a.evento} (${a.fecha_evento}) — ${a.dias_restantes}d\n`;
        out += `   SKU: ${a.sku} | Stock: ${fmt(a.stock_actual)} | Demanda: ${fmt(a.demanda_proyectada)}\n`;
        if(a.deficit>0) out += `   Déficit: ${fmt(a.deficit)} uds | Deadline prod: ${a.deadline_produccion||'—'}\n`;
        out += '\n';
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='oportunidad') {
    if(!data.recomendaciones||!data.recomendaciones.length) { out='✅ Sin SKUs con oportunidad crítica identificados.'; }
    else {
      out += `🎯 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.recomendaciones.forEach((r,i)=>{
        out += `${i+1}. ${r.sku} — Score: ${r.score}\n`;
        out += `   Stock: ${fmt(r.stock)} uds | Rotación: ${r.rotacion_mes}/mes | ${r.meses_cobertura}m inventario\n`;
        out += `   Razones: ${r.razones.join(', ')}\n`;
        out += `   ➜ ${r.accion}\n\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='roi') {
    out += `💰 ${data.titulo}\n${'─'.repeat(40)}\n`;
    out += `Shopify revenue 30d: ${fmtM(data.shopify_revenue_30d||0)}\n\n`;
    if(data.campanas&&data.campanas.length) {
      out += 'CAMPAÑAS:\n';
      data.campanas.forEach(c=>{
        const icon = c.estado_roi==='excelente'?'🟢':c.estado_roi==='bueno'?'🟡':'🔴';
        out += `  ${icon} ${c.nombre}: ROI ${c.roi_pct}% | ${fmtM(c.presupuesto_gastado)} → ${fmtM(c.resultado_ventas)}\n`;
      });
    } else out += 'Sin campañas con inversión registrada.\n';
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='tendencias') {
    out += `📈 ${data.titulo}\n${'─'.repeat(40)}\n`;
    if(data.tendencias_erp&&data.tendencias_erp.length) {
      out += 'ERP — TOP VARIACIONES:\n';
      data.tendencias_erp.forEach(t=>{
        const icon = t.tendencia==='alza'?'🟢':t.tendencia==='baja'?'🔴':'⚪';
        out += `  ${icon} ${t.sku}: ${t.cambio_pct>0?'+':''}${t.cambio_pct}% (${t.reciente} vs ${t.anterior} uds)\n`;
      });
    }
    if(data.shopify_mensual&&data.shopify_mensual.length) {
      out += '\nSHOPIFY MENSUAL:\n';
      data.shopify_mensual.forEach(m=>out+=`  ${m.mes}: ${fmtM(m.ventas)} (${m.pedidos} pedidos)\n`);
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='brief') {
    if(!data.briefs||!data.briefs.length) { out='Sin SKUs con liberaciones recientes.'; }
    else {
      out += `📋 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.briefs.forEach(b=>{
        out += `\nSKU: ${b.sku} (${fmt(b.uds_90d)} uds / 90d)\n`;
        out += `Precio: ${fmtM(b.precio)} | Menciones IG: ${b.ig_menciones}\n`;
        out += `Brief: ${b.brief}\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='pricing') {
    if(!data.propuestas||!data.propuestas.length) { out='Sin SKUs elegibles para promoción.'; }
    else {
      out += `🏷️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.propuestas.forEach(p=>{
        out += `\n${p.sku} — ${p.meses_cobertura}m de inventario\n`;
        out += `  Precio normal: ${fmtM(p.precio_normal)} → Precio promo: ${fmtM(p.precio_promo)} (-${p.max_descuento_pct}%)\n`;
        out += `  ${p.razon}\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='reorden') {
    if(!data.predicciones||!data.predicciones.length) { out='Sin clientes B2B con 2+ pedidos detectados.'; }
    else {
      out += `🔄 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.predicciones.forEach(p=>{
        const icon = p.urgencia==='hoy'?'🔴':p.urgencia==='esta semana'?'🟡':'🟢';
        out += `\n${icon} ${p.email}\n`;
        out += `  Pedidos: ${p.pedidos} | Revenue: ${fmtM(p.revenue_total)} | Ticket: ${fmtM(p.ticket_promedio)}\n`;
        out += `  Intervalo: ${p.intervalo_dias}d | Próximo: ${p.proximo_reorden_estimado} (${p.dias_para_reorden}d) — ${p.urgencia}\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='canibal') {
    if(!data.conflictos||!data.conflictos.length) {
      out = `✅ Sin conflictos detectados. ${data.campanas_revisadas} campañas revisadas.`;
    } else {
      out += `⚠️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      out += `${data.conflictos.length} conflictos en ${data.campanas_revisadas} campañas.\n\n`;
      data.conflictos.forEach((c,i)=>{
        out += `${i+1}. "${c.campana_a}" vs "${c.campana_b}"\n`;
        out += `   Tipo: ${c.conflicto} | Canal: ${c.canal||'—'} | SKU: ${c.sku||'—'}\n`;
        out += `   ➜ ${c.recomendacion}\n\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='contenido_auto') {
    if(!data.piezas||!data.piezas.length) { out='Sin SKUs con liberaciones recientes.'; }
    else {
      out += `✍️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.piezas.forEach(p=>{
        out += `\n📦 ${p.sku} (${fmt(p.uds_30d)} uds / 30d | ${fmtM(p.precio)})\n`;
        out += `\nINSTAGRAM:\n${p.caption_instagram}\n`;
        out += `\nEMAIL — Asunto: ${p.asunto_email}\n`;
        out += `\nWHATSAPP: ${p.texto_whatsapp}\n`;
        out += '\n'+'─'.repeat(30)+'\n';
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='alerta_stock') {
    if(!data.alertas||!data.alertas.length) { out='✅ Sin alertas de stock. Todos los SKUs tienen cobertura adecuada.'; }
    else {
      out += `🚨 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.alertas.forEach(a=>{
        const icon = a.nivel==='critico'?'🔴':'🟡';
        out += `${icon} ${a.sku} — ${a.dias_cobertura_real}d de cobertura\n`;
        out += `   Stock: ${fmt(a.stock)} | ERP: ${fmt(a.rotacion_erp)} uds/mes | Shopify: ${fmt(a.demanda_shopify_30d)} uds/30d\n`;
        out += `   ➜ ${a.accion}\n\n`;
      });
    }
    return `<pre>${out}</pre>${fmtIA(data)}`;
  }

  if(agente==='estrategia') {
    const k = data.kpis || {};
    const snap = data.snapshot || {};
    // KPIs del snapshot
    let html = `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px;">`;
    const kpiCards = [
      {label:'SKUs para empujar', val:k.skus_a_empujar||0, color:'#fbbf24'},
      {label:'SKUs en riesgo',    val:k.skus_en_riesgo||0, color:'#ef4444'},
      {label:'Influencers activos', val:k.influencers_activos||0, color:'#34d399'},
      {label:'Eventos próx. 60d', val:k.eventos_en_60d||0, color:'#a78bfa'},
      {label:'Producción planificada', val:k.produccion_planificada||0, color:'#60a5fa'},
    ];
    html += kpiCards.map(c=>`
      <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:12px 14px;">
        <div style="font-size:22px;font-weight:800;color:${c.color};line-height:1;">${c.val}</div>
        <div style="font-size:11px;color:#64748b;margin-top:4px;">${c.label}</div>
      </div>`).join('');
    html += '</div>';
    // Análisis IA (markdown del modelo) — render con markdown básico
    if(data.analisis_ia) {
      html += `<div style="background:linear-gradient(135deg,rgba(124,58,237,.10),rgba(124,58,237,.03));border:1px solid rgba(124,58,237,.35);border-radius:12px;padding:18px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <span style="font-size:16px;">🧠</span>
          <span style="font-size:11px;font-weight:700;color:#a78bfa;letter-spacing:.5px;text-transform:uppercase;">Análisis estratégico — Claude Sonnet</span>
        </div>
        <div class="estrategia-md">${renderMarkdownBasic(data.analisis_ia)}</div>
      </div>`;
    } else {
      html += `<div style="padding:14px;color:#f59e0b;background:#78350f33;border:1px solid #f59e0b44;border-radius:8px;font-size:13px;">⚠️ Sin análisis IA — verificá que ANTHROPIC_API_KEY esté configurada en animus_config.</div>`;
    }
    // Datos crudos colapsables (para debug / power user)
    html += `<details style="margin-top:14px;">
      <summary style="cursor:pointer;color:#94a3b8;font-size:11px;">Ver snapshot crudo (debug)</summary>
      <pre style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;margin-top:8px;font-size:11px;color:#94a3b8;max-height:300px;overflow:auto;">${esc(JSON.stringify(snap, null, 2))}</pre>
    </details>`;
    return html;
  }

  return `<pre>${JSON.stringify(data, null, 2)}</pre>${fmtIA(data)}`;
}

// ─── Markdown muy básico para output del agente Estrategia ─────────────
function renderMarkdownBasic(md) {
  if(!md) return '';
  // Escape HTML primero
  let h = md.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Tablas markdown (| col | col |)
  h = h.replace(/((?:^\|.+\|\s*\n)+)/gm, function(block) {
    const lines = block.trim().split('\n');
    if(lines.length < 2) return block;
    const headers = lines[0].split('|').slice(1,-1).map(s=>s.trim());
    const rowsMd = lines.slice(2);
    let tbl = '<table style="width:100%;margin:10px 0;border-collapse:collapse;font-size:12px;">';
    tbl += '<thead><tr>'+headers.map(h=>`<th style="text-align:left;padding:8px;background:#0f172a;color:#a78bfa;border-bottom:1px solid #334155;">${h}</th>`).join('')+'</tr></thead>';
    tbl += '<tbody>'+rowsMd.map(r=>{
      const cols = r.split('|').slice(1,-1).map(s=>s.trim());
      return '<tr>'+cols.map(c=>`<td style="padding:7px 8px;color:#cbd5e1;border-bottom:1px solid #1e293b;">${c}</td>`).join('')+'</tr>';
    }).join('')+'</tbody></table>';
    return tbl;
  });
  // Headings
  h = h.replace(/^## (.+)$/gm, '<h3 style="font-size:14px;color:#a78bfa;margin:18px 0 8px;font-weight:700;">$1</h3>');
  h = h.replace(/^# (.+)$/gm, '<h2 style="font-size:16px;color:#f1f5f9;margin:18px 0 10px;font-weight:800;">$1</h2>');
  // Bold + italic
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong style="color:#f1f5f9;">$1</strong>');
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Listas numeradas
  h = h.replace(/^(\d+)\. (.+)$/gm, '<div style="margin:4px 0;"><span style="color:#a78bfa;font-weight:700;margin-right:6px;">$1.</span>$2</div>');
  // Listas bullets
  h = h.replace(/^[-*] (.+)$/gm, '<div style="margin:4px 0 4px 16px;"><span style="color:#a78bfa;margin-right:6px;">·</span>$1</div>');
  // Saltos de línea (no dentro de tablas/divs ya generados)
  h = h.replace(/\n\n+/g, '<div style="height:8px;"></div>');
  h = h.replace(/\n/g, '<br>');
  // Limpiar dobles <br> alrededor de tablas/headings/divs
  h = h.replace(/<br>\s*(<(?:h[123]|table|div|details))/g, '$1');
  h = h.replace(/(<\/(?:h[123]|table|div|details)>)\s*<br>/g, '$1');
  return `<div style="font-size:13px;color:#e2e8f0;line-height:1.7;">${h}</div>`;
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function loadAgentLog() {
  const rows = await fetch('/api/marketing/agentes/log').then(r=>r.json());
  const body = document.getElementById('agent-log-body');
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="5">Sin ejecuciones registradas</td></tr>'; return; }
  body.innerHTML = rows.map(r=>`
    <tr>
      <td style="color:#64748b;">${r.fecha?.substring(0,16)||'—'}</td>
      <td><span class="badge badge-purple">${r.agente}</span></td>
      <td style="color:#94a3b8;">${r.accion||'—'}</td>
      <td>${r.ejecutado_por||'—'}</td>
      <td><button class="btn btn-outline btn-sm" onclick="verResultadoLog(${r.id})">Ver</button></td>
    </tr>`).join('');
}

async function verResultadoLog(id) {
  const data = await fetch(`/api/marketing/agentes/log/${id}`).then(r=>r.json());
  document.getElementById('modal-agent-title').textContent = `Resultado: Agente ${data.agente} — ${data.fecha?.substring(0,16)}`;
  let content = '';
  if(typeof data.resultado === 'object') {
    content = formatAgentResult(data.agente?.toLowerCase(), data.resultado);
  } else {
    content = data.resultado || '(sin resultado)';
  }
  document.getElementById('modal-agent-content').innerHTML = content;
  document.getElementById('modal-agente-result').classList.add('open');
}

// ──────────────────────────────────────────────────────────────────────────────
// ANALYTICS
// ──────────────────────────────────────────────────────────────────────────────
async function loadAnalytics() {
  const fmt  = v => v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':String(Math.round(v||0));
  const fmtM = v => '$'+fmt(v||0);
  function svgBars(meses, valFn, colorFill, labelFn) {
    if(!meses.length) return '<div style="color:#64748b;text-align:center;padding:40px;">Sin datos</div>';
    const vals = meses.map(valFn);
    const maxV = Math.max(...vals, 1);
    const W=520, H=190, padL=8, padR=8, padB=32, padT=20;
    const n = meses.length;
    const slotW = (W-padL-padR)/n;
    const barW  = Math.max(10, Math.min(36, slotW-6));
    let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;display:block;">`;
    meses.forEach((m, i) => {
      const v = vals[i];
      const bh = Math.max(4, Math.round((v/maxV)*(H-padB-padT)));
      const x  = padL + i*slotW + (slotW-barW)/2;
      const by = H - padB - bh;
      svg += `<rect x="${x.toFixed(1)}" y="${by}" width="${barW}" height="${bh}" rx="3" fill="${colorFill}" opacity="0.88"/>`;
      // month label
      const lbl = (m.mes||'').slice(2); // YY-MM
      svg += `<text x="${(x+barW/2).toFixed(1)}" y="${H-10}" text-anchor="middle" font-size="9" fill="#64748b">${lbl}</text>`;
      // value label if bar is tall enough
      if(v>0) svg += `<text x="${(x+barW/2).toFixed(1)}" y="${Math.max(padT+2,by-4)}" text-anchor="middle" font-size="9" fill="${labelFn}" font-weight="600">${fmtM(v)}</text>`;
    });
    svg += '</svg>';
    return svg;
  }

  // Fetch in parallel
  const [data, roiData] = await Promise.all([
    fetch('/api/marketing/analytics/influencers').then(r=>r.json()).catch(()=>({})),
    fetch('/api/marketing/analytics/roi').then(r=>r.json()).catch(()=>({}))
  ]);

  // ── KPIs histórico ──
  document.getElementById('an-total-hist').textContent     = fmtM(data.total_pagado_historico||0);
  document.getElementById('an-colabs-hist').textContent    = data.colabs_historico||0;
  document.getElementById('an-creadores-hist').textContent = data.creadores_historico||0;
  document.getElementById('an-avg-colab').textContent      = fmtM(data.promedio_por_colab||0);
  document.getElementById('an-pendiente-total').textContent= fmtM(data.total_pendiente||0);
  document.getElementById('an-top-creador').textContent    = data.top_creador||'—';

  // ── KPIs Shopify ──
  const sh = roiData.shopify_kpis||{};
  document.getElementById('an-sh-30d').textContent    = fmtM(sh.revenue_30d||0);
  document.getElementById('an-sh-mes').textContent    = fmtM(sh.revenue_mes||0);
  document.getElementById('an-sh-orders').textContent = sh.pedidos_30d||'—';
  const crec = sh.crecimiento_pct;
  if(crec!=null) {
    const crecEl = document.getElementById('an-sh-crec');
    const crecCard = document.getElementById('an-sh-crec-card');
    const sign = crec>=0?'+':'';
    crecEl.textContent = sign+crec.toFixed(1)+'%';
    crecEl.style.color = crec>=0?'#34d399':'#f87171';
    crecCard.style.borderColor = crec>=0?'#34d399':'#f87171';
  }

  // ── Charts ──
  const meses = data.por_mes||[];
  document.getElementById('an-gasto-chart').innerHTML = svgBars(meses, m=>m.total_pagado, '#6366f1', '#a5b4fc');
  document.getElementById('an-total-label').textContent = 'Histórico: '+fmtM(data.total_pagado_historico||0);
  document.getElementById('an-nuevos-chart').innerHTML  = svgBars(meses, m=>m.nuevos_creadores||0, '#34d399', '#6ee7b7');

  // ── Ranking ALL TIME ──
  const ranking = data.ranking||[];
  const rb = document.getElementById('an-ranking-body');
  rb.innerHTML = ranking.length ? ranking.map((r,i)=>{
    const estadoBadge = r.estado==='Activo'
      ? '<span style="color:#34d399;">Activo</span>'
      : '<span style="color:#f87171;">'+r.estado+'</span>';
    const pendBadge = r.pendiente>0
      ? `<span style="color:#f59e0b;font-weight:700;">${fmtM(r.pendiente)}</span>`
      : '<span style="color:#475569;">—</span>';
    return `<tr>
      <td style="color:#64748b;font-weight:700;">${i+1}</td>
      <td style="font-weight:700;">${r.nombre||'—'}</td>
      <td style="color:#94a3b8;">${r.colabs||0}</td>
      <td style="color:#818cf8;font-weight:800;">${fmtM(r.total)}</td>
      <td>${pendBadge}</td>
      <td style="color:#94a3b8;">${fmtM(r.promedio)}</td>
      <td style="color:#64748b;font-size:12px;">${r.primer_pago||'—'}</td>
      <td style="color:#64748b;font-size:12px;">${r.ultimo_pago||'—'}</td>
      <td>${estadoBadge}</td>
    </tr>`;
  }).join('') : '<tr class="empty-row"><td colspan="9">Sin datos de pagos registrados.</td></tr>';

  // ── Detalle mensual ──
  const mb = document.getElementById('an-meses-body');
  mb.innerHTML = meses.length ? [...meses].reverse().map(m=>
    `<tr>
      <td style="font-weight:700;color:#e2e8f0;">${m.mes}</td>
      <td>${m.colabs}</td>
      <td>${m.creadores_unicos_mes}</td>
      <td style="color:#818cf8;font-weight:700;">${fmtM(m.total_pagado)}</td>
      <td style="color:#f59e0b;">${m.total_pendiente>0?fmtM(m.total_pendiente):'—'}</td>
      <td style="color:#34d399;">${m.nuevos_creadores||0}</td>
    </tr>`
  ).join('') : '<tr class="empty-row"><td colspan="6">Sin datos</td></tr>';
}


// ──────────────────────────────────────────────────────────────────────────────
// HISTORIAL INFLUENCER
// ──────────────────────────────────────────────────────────────────────────────
function verHistorial(id, infOptional) {
  // Resolver desde cache si no llega el objeto completo (caso normal ahora)
  const inf = infOptional || _INFLUENCERS_CACHE[id];
  if (!inf) {
    showToast('Datos del influencer no disponibles. Recargá la página.', 'error');
    return;
  }
  const fmtM = v => v>=1e6?'$'+(v/1e6).toFixed(1)+'M':v>=1e3?'$'+(v/1e3).toFixed(0)+'K':'$'+Number(v||0).toLocaleString('es-CO');
  document.getElementById('hist-title').textContent = '📋 ' + (inf.nombre||'Influencer');
  const pagos  = inf.pagos || [];
  const pagadas   = pagos.filter(p=>p.estado==='Pagada');
  const pendientes= pagos.filter(p=>p.estado==='Pendiente');

  let html = '';

  // ── KPI resumen ──
  html += `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#34d399;">${fmtM(inf.total_pagado||0)}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px;">Total pagado</div>
    </div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#818cf8;">${inf.pagos_count||0}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px;">Colaboraciones</div>
    </div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#f59e0b;">${fmtM(inf.total_pendiente||0)}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px;">Pendiente pago</div>
    </div>
  </div>`;

  // ── Pagos realizados ──
  if(pagadas.length) {
    html += `<div style="font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">✅ Pagos realizados</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #334155;">
        <th style="padding:6px 8px;text-align:left;color:#64748b;">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:#64748b;">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:#64748b;">Valor</th>
        <th style="padding:6px 8px;text-align:left;color:#64748b;">OC</th>
      </tr></thead>
      <tbody>`;
    pagadas.forEach(p=>{
      html += `<tr style="border-bottom:1px solid #1e293b;">
        <td style="padding:6px 8px;color:#94a3b8;">${p.fecha||'—'}</td>
        <td style="padding:6px 8px;">${p.concepto||'—'}</td>
        <td style="padding:6px 8px;text-align:right;color:#34d399;font-weight:700;">${fmtM(p.valor||0)}</td>
        <td style="padding:6px 8px;color:#64748b;font-size:11px;">${p.numero_oc||'—'}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  // ── Pendientes ──
  if(pendientes.length) {
    html += `<div style="font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">⏳ Pendientes de pago</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #334155;">
        <th style="padding:6px 8px;text-align:left;color:#64748b;">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:#64748b;">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:#64748b;">Valor</th>
      </tr></thead>
      <tbody>`;
    pendientes.forEach(p=>{
      html += `<tr style="border-bottom:1px solid #1e293b;">
        <td style="padding:6px 8px;color:#94a3b8;">${p.fecha||'—'}</td>
        <td style="padding:6px 8px;">${p.concepto||'—'}</td>
        <td style="padding:6px 8px;text-align:right;color:#f59e0b;font-weight:700;">${fmtM(p.valor||0)}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  if(!pagadas.length && !pendientes.length) {
    html += `<div style="text-align:center;color:#64748b;padding:32px;">Sin pagos registrados aún.</div>`;
  }

  document.getElementById('hist-content').innerHTML = html;
  document.getElementById('modal-historial').classList.add('open');
}

// ──────────────────────────────────────────────────────────────────────────────
// MODAL HELPERS
// ──────────────────────────────────────────────────────────────────────────────
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal-bg').forEach(m=>m.addEventListener('click',e=>{ if(e.target===m) m.classList.remove('open'); }));


// ──────────────────────────────────────────────────────────────────────────────
// AGENCIA
// ──────────────────────────────────────────────────────────────────────────────
let _agLoaded = false;

function scoreColor(s) {
  if (s >= 75) return '#34d399';
  if (s >= 50) return '#667eea';
  if (s >= 25) return '#f59e0b';
  return '#f87171';
}
function scoreBadge(s) {
  const c = scoreColor(s);
  return '<span style="display:inline-block;background:'+c+'22;color:'+c+';border:1px solid '+c+'44;border-radius:20px;padding:2px 10px;font-weight:700;font-size:13px;min-width:42px;text-align:center;">'+s+'</span>';
}
function sevColor(sev) {
  return {critical:'#f87171',high:'#fb923c',medium:'#f59e0b',low:'#34d399'}[sev]||'#94a3b8';
}
function sevLabel(sev) {
  return {critical:'CRITICO',high:'ALTO',medium:'MEDIO',low:'BAJO'}[sev]||sev.toUpperCase();
}

async function loadAgencia(force) {
  if (_agLoaded && !force) return;
  _agLoaded = true;
  var errHtml = '';
  try {
    document.getElementById('ag-scoring-tbody').innerHTML = '<tr class="empty-row"><td colspan="8">Analizando portafolio...</td></tr>';
    document.getElementById('ag-audit-list').innerHTML = '<div style="color:#64748b;font-size:13px;">Calculando...</div>';
    document.getElementById('ag-competition').innerHTML = '<div style="color:#64748b;font-size:13px;">Calculando...</div>';
    document.getElementById('ag-proposals').innerHTML = '<div style="color:#64748b;font-size:13px;">Generando propuestas...</div>';
  } catch(domErr) {
    console.error('[loadAgencia] DOM error:', domErr);
    _agLoaded = false;
    return;
  }
  try {
    var r = await fetch('/api/marketing/agencia/audit');
    var d = await r.json();
    if (!r.ok) { throw new Error(d.error || 'Error del servidor'); }
    renderAgencia(d);
  } catch(fetchErr) {
    errHtml = '<div style="color:#f87171;font-size:13px;padding:12px;background:#7f1d1d22;border-radius:8px;border:1px solid #f87171;">Error: '+fetchErr.message+'</div>';
    try { document.getElementById('ag-scoring-tbody').innerHTML = '<tr><td colspan="8">'+errHtml+'</td></tr>'; } catch(_){}
    try { document.getElementById('ag-audit-list').innerHTML = errHtml; } catch(_){}
    try { document.getElementById('ag-competition').innerHTML = errHtml; } catch(_){}
    try { document.getElementById('ag-proposals').innerHTML = errHtml; } catch(_){}
    console.error('[loadAgencia]', fetchErr);
    _agLoaded = false;
  }
}

function renderAgencia(d) {
  var influencers = d.influencers || [];
  var audit = d.audit || [];
  var competition = d.competition || {};
  var proposals = d.proposals || [];
  var portfolio = d.portfolio || {};

  // KPIs
  document.getElementById('ag-kpi-activos').textContent = portfolio.activos || 0;
  var avgScore = influencers.length ? Math.round(influencers.reduce(function(s,i){ return s+(i.score||0); },0)/influencers.length) : 0;
  document.getElementById('ag-kpi-score').textContent = avgScore+'/100';
  document.getElementById('ag-kpi-score').style.color = scoreColor(avgScore);
  document.getElementById('ag-kpi-riesgo').textContent = portfolio.en_riesgo || 0;
  var criticals = audit.filter(function(a){ return a.severity==='critical'; }).length;
  document.getElementById('ag-kpi-critical').textContent = criticals;
  var totalInv = influencers.reduce(function(s,i){ return s+(i.total_pagado||0); },0);
  document.getElementById('ag-kpi-inversion').textContent = fmtM(totalInv);

  // Scoring table
  var sorted = influencers.slice().sort(function(a,b){ return (b.score||0)-(a.score||0); });
  var rows = '';
  sorted.forEach(function(inf) {
    var est = inf.estado === 'Activo'
      ? '<span style="color:#34d399;font-size:11px;font-weight:700;">Activo</span>'
      : '<span style="color:#64748b;font-size:11px;">Inactivo</span>';
    var eng = inf.engagement_rate ? (inf.engagement_rate*100).toFixed(1)+'%' : '&#x2014;';
    var seg = inf.seguidores ? Number(inf.seguidores).toLocaleString('es-CO') : '&#x2014;';
    rows += '<tr style="border-bottom:1px solid #1e293b;">'
      +'<td style="padding:8px;font-weight:600;color:#e2e8f0;">'+(inf.nombre||'&#x2014;')+'</td>'
      +'<td style="padding:8px;color:#94a3b8;font-size:12px;">'+(inf.nicho||'&#x2014;')+'</td>'
      +'<td style="padding:8px;text-align:center;">'+scoreBadge(inf.score||0)+'</td>'
      +'<td style="padding:8px;text-align:right;color:#94a3b8;">'+eng+'</td>'
      +'<td style="padding:8px;text-align:right;color:#94a3b8;">'+seg+'</td>'
      +'<td style="padding:8px;text-align:right;color:#94a3b8;">'+(inf.campanas_count||0)+'</td>'
      +'<td style="padding:8px;text-align:right;color:#34d399;font-weight:600;">'+fmtM(inf.total_pagado||0)+'</td>'
      +'<td style="padding:8px;text-align:center;">'+est+'</td>'
      +'</tr>';
  });
  document.getElementById('ag-scoring-tbody').innerHTML = rows || '<tr class="empty-row"><td colspan="8">Sin influencers.</td></tr>';

  // Audit
  var bySev = {critical:[],high:[],medium:[],low:[]};
  audit.forEach(function(a) { if(bySev[a.severity]) bySev[a.severity].push(a); });
  var auditHtml = '';
  ['critical','high','medium','low'].forEach(function(sev) {
    if (!bySev[sev].length) return;
    var c = sevColor(sev);
    auditHtml += '<div style="margin-bottom:12px;">'
      +'<div style="font-size:11px;font-weight:700;color:'+c+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">'+sevLabel(sev)+' ('+bySev[sev].length+')</div>';
    bySev[sev].forEach(function(item) {
      auditHtml += '<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #1e293b;">'
        +'<span style="color:'+c+';margin-top:1px;flex-shrink:0;">&#x25CF;</span>'
        +'<div>'
        +'<div style="color:#e2e8f0;font-size:13px;">'+item.finding+'</div>'
        +(item.recommendation ? '<div style="color:#64748b;font-size:11px;margin-top:2px;">'+item.recommendation+'</div>' : '')
        +'</div></div>';
    });
    auditHtml += '</div>';
  });
  document.getElementById('ag-audit-list').innerHTML = auditHtml || '<div style="color:#34d399;font-size:13px;">Sin hallazgos.</div>';

  // Competition
  var niches = competition.niches || {};
  var gaps = competition.gaps || [];
  var compHtml = '';
  var nicheKeys = Object.keys(niches).sort(function(a,b){ return niches[b]-niches[a]; });
  if (nicheKeys.length) {
    var total = nicheKeys.reduce(function(s,k){ return s+niches[k]; },0);
    compHtml += '<div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Distribucion por nicho</div>';
    nicheKeys.forEach(function(nicho) {
      var cnt = niches[nicho];
      var pct = total ? Math.round(cnt/total*100) : 0;
      compHtml += '<div style="margin-bottom:8px;">'
        +'<div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;margin-bottom:3px;">'
        +'<span>'+nicho+'</span><span>'+cnt+' &middot; '+pct+'%</span></div>'
        +'<div style="background:#1e293b;border-radius:4px;height:6px;">'
        +'<div style="background:#667eea;width:'+pct+'%;height:6px;border-radius:4px;"></div></div></div>';
    });
  }
  if (gaps.length) {
    compHtml += '<div style="margin-top:14px;font-size:11px;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Brechas detectadas</div>';
    gaps.forEach(function(g) {
      compHtml += '<div style="padding:5px 0;border-bottom:1px solid #1e293b;font-size:12px;color:#e2e8f0;">&#x26A0; '+g+'</div>';
    });
  }
  document.getElementById('ag-competition').innerHTML = compHtml || '<div style="color:#64748b;font-size:13px;">Sin datos suficientes.</div>';

  // Proposals
  var propHtml = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;">';
  if (proposals.length) {
    proposals.forEach(function(p) {
      var priCol = p.priority==='alta' ? '#f87171' : (p.priority==='media' ? '#f59e0b' : '#34d399');
      propHtml += '<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;border-left:3px solid '+priCol+';">'
        +'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
        +'<div style="font-weight:700;color:#e2e8f0;font-size:14px;">'+(p.title||'')+'</div>'
        +'<span style="font-size:10px;font-weight:700;color:'+priCol+';text-transform:uppercase;background:'+priCol+'22;padding:2px 8px;border-radius:10px;">'+(p.priority||'media')+'</span></div>'
        +'<div style="color:#94a3b8;font-size:12px;line-height:1.5;margin-bottom:10px;">'+(p.description||'')+'</div>'
        +'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        +(p.budget_est ? '<span style="font-size:11px;color:#34d399;background:#34d39922;padding:2px 8px;border-radius:8px;">'+p.budget_est+'</span>' : '')
        +(p.influencers_needed ? '<span style="font-size:11px;color:#667eea;background:#667eea22;padding:2px 8px;border-radius:8px;">'+p.influencers_needed+' influencers</span>' : '')
        +(p.expected_reach ? '<span style="font-size:11px;color:#f59e0b;background:#f59e0b22;padding:2px 8px;border-radius:8px;">'+p.expected_reach+'</span>' : '')
        +'</div></div>';
    });
  } else {
    propHtml += '<div style="color:#64748b;font-size:13px;padding:20px;">Sin propuestas.</div>';
  }
  propHtml += '</div>';
  document.getElementById('ag-proposals').innerHTML = propHtml;
}

// ──────────────────────────────────────────────────────────────────────────────

// ══════════════════════════════════════════════════════════════════════════════
// AGENCIA ADS — Multi-plataforma con claude-ads skill
// ══════════════════════════════════════════════════════════════════════════════
const ADS_PLATFORMS = [
  {id:'google',    name:'Google Ads',     icon:'&#x1F50D;', color:'#4285F4', desc:'Search · PMax · YouTube'},
  {id:'meta',      name:'Meta Ads',       icon:'&#x1F4F1;', color:'#1877F2', desc:'Facebook · Instagram'},
  {id:'linkedin',  name:'LinkedIn Ads',   icon:'&#x1F4BC;', color:'#0A66C2', desc:'B2B · Lead Gen'},
  {id:'tiktok',    name:'TikTok Ads',     icon:'&#x1F3B5;', color:'#FE2C55', desc:'Creative · Smart+'},
  {id:'youtube',   name:'YouTube Ads',    icon:'&#x25B6;',  color:'#FF0000', desc:'Video · Shorts'},
  {id:'apple',     name:'Apple Search',   icon:'&#xF8FF;',  color:'#000000', desc:'iOS App Store'},
  {id:'microsoft', name:'Microsoft Ads',  icon:'&#x1F50E;', color:'#00A4EF', desc:'Bing · Edge · LinkedIn'},
];
const ADS_ACTIONS_PLATFORM = [
  {id:'audit',    label:'Audit',    icon:'&#x1F50D;', desc:'Diagnostico completo + score 0-100'},
  {id:'plan',     label:'Plan',     icon:'&#x1F5FA;', desc:'Estrategia 90 dias por industria'},
  {id:'creative', label:'Creative', icon:'&#x1F3A8;', desc:'Copy + briefs + specs por formato'},
  {id:'budget',   label:'Budget',   icon:'&#x1F4B0;', desc:'Asignacion + bidding strategy'},
];
const ADS_ACTIONS_GLOBAL = [
  {id:'competitor', label:'Competitor',  icon:'&#x1F575;', desc:'Inteligencia competitiva'},
  {id:'landing',    label:'Landing',     icon:'&#x1F310;', desc:'Auditoria de pagina destino'},
  {id:'test',       label:'A/B Test',    icon:'&#x1F9EA;', desc:'Diseno de experimentos'},
  {id:'dna',        label:'Brand DNA',   icon:'&#x1F9EC;', desc:'Extrae perfil de marca de URL'},
];
let ADS_STATE = { platform: 'meta', action: 'audit', running: false };

function renderAdsTab() {
  const root = document.getElementById('tab-ads');
  if (!root || root.dataset.rendered === '1') return;
  root.dataset.rendered = '1';

  const platCards = ADS_PLATFORMS.map(p =>
    `<div class="ads-plat-card" data-platform="${p.id}" onclick="selectAdsPlatform('${p.id}')" style="border-color:${p.color}33;">
       <div style="font-size:28px;line-height:1;color:${p.color};">${p.icon}</div>
       <div style="font-weight:700;color:#f1f5f9;font-size:13px;margin-top:8px;">${p.name}</div>
       <div style="font-size:10px;color:#64748b;margin-top:2px;">${p.desc}</div>
     </div>`).join('');

  const actPlatBtns = ADS_ACTIONS_PLATFORM.map(a =>
    `<div class="ads-act-card" data-action="${a.id}" onclick="selectAdsAction('${a.id}',false)">
       <div style="font-size:22px;">${a.icon}</div>
       <div style="font-weight:700;color:#f1f5f9;font-size:13px;margin-top:6px;">${a.label}</div>
       <div style="font-size:10px;color:#64748b;margin-top:2px;">${a.desc}</div>
     </div>`).join('');

  const actGlobBtns = ADS_ACTIONS_GLOBAL.map(a =>
    `<div class="ads-act-card global" data-action="${a.id}" onclick="selectAdsAction('${a.id}',true)">
       <div style="font-size:22px;">${a.icon}</div>
       <div style="font-weight:700;color:#f1f5f9;font-size:13px;margin-top:6px;">${a.label}</div>
       <div style="font-size:10px;color:#64748b;margin-top:2px;">${a.desc}</div>
     </div>`).join('');

  root.innerHTML = `
    <style>
      .ads-hero{background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 60%,#1e293b 100%);border:1px solid #4c1d95;border-radius:16px;padding:24px;margin-bottom:18px;position:relative;overflow:hidden;}
      .ads-hero:after{content:'';position:absolute;top:-50%;right:-10%;width:400px;height:400px;background:radial-gradient(circle,#7c3aed44 0%,transparent 70%);pointer-events:none;}
      .ads-hero h2{font-size:22px;font-weight:800;color:#fff;margin-bottom:6px;display:flex;align-items:center;gap:10px;}
      .ads-hero .sub{color:#a78bfa;font-size:13px;max-width:720px;line-height:1.5;}
      .ads-hero .stats{display:flex;gap:18px;margin-top:18px;flex-wrap:wrap;}
      .ads-hero .stat{background:#0f172a99;border:1px solid #334155;border-radius:10px;padding:10px 14px;}
      .ads-hero .stat .v{font-size:20px;font-weight:800;color:#a78bfa;line-height:1;}
      .ads-hero .stat .l{font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px;}

      .ads-section-title{font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;margin:18px 0 10px;display:flex;align-items:center;gap:8px;}
      .ads-section-title .num{display:inline-flex;width:20px;height:20px;border-radius:50%;background:#4c1d95;color:#fff;font-size:11px;font-weight:800;align-items:center;justify-content:center;}

      .ads-plat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;}
      .ads-plat-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:14px;cursor:pointer;text-align:center;transition:.2s;}
      .ads-plat-card:hover{transform:translateY(-2px);background:#263348;}
      .ads-plat-card.active{background:#1e1b4b;border-color:#7c3aed!important;box-shadow:0 0 0 3px #7c3aed33;}

      .ads-act-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;}
      .ads-act-card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;cursor:pointer;text-align:center;transition:.15s;}
      .ads-act-card:hover{background:#263348;border-color:#475569;}
      .ads-act-card.active{background:linear-gradient(135deg,#1e1b4b,#312e81);border-color:#7c3aed;}
      .ads-act-card.global{border-style:dashed;}

      .ads-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:10px;}
      .ads-input{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:9px 12px;border-radius:8px;font-size:13px;width:100%;font-family:inherit;}
      .ads-input:focus{outline:none;border-color:#7c3aed;}
      .ads-textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:12px;border-radius:8px;font-size:12px;width:100%;font-family:'Cascadia Code',Consolas,monospace;min-height:140px;resize:vertical;}
      .ads-textarea:focus{outline:none;border-color:#7c3aed;}
      .ads-label{font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;display:block;}

      .ads-run-btn{width:100%;padding:16px;border-radius:12px;border:none;cursor:pointer;background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;font-size:15px;font-weight:800;letter-spacing:.02em;text-transform:uppercase;transition:.2s;display:flex;align-items:center;justify-content:center;gap:10px;}
      .ads-run-btn:hover{filter:brightness(1.1);transform:translateY(-1px);box-shadow:0 8px 24px #7c3aed44;}
      .ads-run-btn:disabled{opacity:.5;cursor:wait;transform:none;}

      .ads-output{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:24px;margin-top:18px;}
      .ads-output h1{font-size:20px;color:#f1f5f9;margin:18px 0 10px;font-weight:800;border-bottom:1px solid #334155;padding-bottom:8px;}
      .ads-output h2{font-size:16px;color:#e2e8f0;margin:16px 0 8px;font-weight:700;}
      .ads-output h3{font-size:14px;color:#a78bfa;margin:14px 0 6px;font-weight:700;}
      .ads-output p{color:#cbd5e1;font-size:13px;line-height:1.65;margin:6px 0;}
      .ads-output ul,.ads-output ol{margin:8px 0 8px 22px;color:#cbd5e1;font-size:13px;line-height:1.7;}
      .ads-output li{margin:3px 0;}
      .ads-output strong{color:#f1f5f9;font-weight:700;}
      .ads-output code{background:#0f172a;color:#a78bfa;padding:1px 6px;border-radius:4px;font-size:12px;font-family:'Cascadia Code',Consolas,monospace;}
      .ads-output pre{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;overflow-x:auto;margin:10px 0;}
      .ads-output pre code{background:transparent;color:#e2e8f0;padding:0;font-size:12px;}
      .ads-output table{width:100%;margin:10px 0;border-collapse:collapse;}
      .ads-output th{background:#0f172a;text-align:left;padding:8px 10px;font-size:11px;color:#94a3b8;text-transform:uppercase;border-bottom:1px solid #334155;}
      .ads-output td{padding:8px 10px;font-size:12px;color:#cbd5e1;border-bottom:1px solid #1e293b;}
      .ads-output blockquote{border-left:3px solid #7c3aed;padding:6px 14px;margin:10px 0;color:#a78bfa;background:#1e1b4b33;font-style:italic;}
      .ads-meta{display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:#64748b;margin-top:14px;padding-top:12px;border-top:1px solid #334155;}
      .ads-meta span{background:#0f172a;padding:3px 9px;border-radius:6px;border:1px solid #334155;}

      .ads-loader{display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px 20px;}
      .ads-loader .ring{width:48px;height:48px;border:3px solid #334155;border-top-color:#7c3aed;border-radius:50%;animation:adsspin 0.9s linear infinite;}
      @keyframes adsspin{to{transform:rotate(360deg);}}
      .ads-loader .lbl{color:#a78bfa;font-size:13px;font-weight:600;}
      .ads-loader .sub{color:#64748b;font-size:11px;}

      .ads-history{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:14px;margin-top:18px;}
      .ads-history-item{display:flex;align-items:center;gap:10px;padding:8px 4px;border-bottom:1px solid #263348;cursor:pointer;font-size:12px;transition:.1s;}
      .ads-history-item:hover{background:#0f172a44;border-radius:6px;}
      .ads-history-item:last-child{border-bottom:none;}
    </style>

    <div class="ads-hero">
      <h2>&#x1F680; Agencia de Ads — Multi-plataforma</h2>
      <div class="sub">
        Auditoria, planning, creative y budget para 7 plataformas pagadas.
        Powered by claude-sonnet-4-5 con 250+ checks, scoring 0-100, benchmarks por industria,
        y biblioteca de specs creativos. Output en markdown listo para cliente.
      </div>
      <div class="stats">
        <div class="stat"><div class="v">7</div><div class="l">Plataformas</div></div>
        <div class="stat"><div class="v">32</div><div class="l">Capacidades</div></div>
        <div class="stat"><div class="v">~$0.06</div><div class="l">Por audit (con cache)</div></div>
        <div class="stat"><div class="v">~30s</div><div class="l">Tiempo respuesta</div></div>
      </div>
    </div>

    <div class="grid2" style="gap:18px;">
      <div>
        <div class="ads-section-title"><span class="num">1</span> Plataforma</div>
        <div class="ads-plat-grid">${platCards}</div>

        <div class="ads-section-title"><span class="num">2</span> Accion por plataforma</div>
        <div class="ads-act-grid">${actPlatBtns}</div>

        <div class="ads-section-title"><span class="num">2b</span> Acciones globales (sin plataforma)</div>
        <div class="ads-act-grid">${actGlobBtns}</div>

        <div class="ads-section-title"><span class="num">3</span> Contexto del cliente</div>
        <div class="ads-form-grid">
          <div><label class="ads-label">Cliente</label>
            <input class="ads-input" id="ads-client" placeholder="ej. ANIMUS Lab" /></div>
          <div><label class="ads-label">Industria</label>
            <select class="ads-input" id="ads-industry">
              <option value="">Seleccionar...</option>
              <option>SaaS</option><option>E-commerce</option><option>Skincare/Cosmetica</option>
              <option>Local Service</option><option>B2B Enterprise</option><option>Info Products</option>
              <option>Mobile App</option><option>Real Estate</option><option>Healthcare</option>
              <option>Finance</option><option>Agency</option><option>Other</option>
            </select></div>
          <div><label class="ads-label">Spend mensual (USD)</label>
            <input class="ads-input" id="ads-spend" type="number" placeholder="5000" /></div>
          <div><label class="ads-label">Objetivo principal</label>
            <select class="ads-input" id="ads-goal">
              <option value="">Seleccionar...</option>
              <option>Ventas / Revenue</option><option>Leads / Demos</option>
              <option>App Installs</option><option>Calls</option><option>Brand</option>
            </select></div>
        </div>

        <div class="ads-section-title"><span class="num">4</span> Datos / contexto (CSV, metricas, descripcion)</div>
        <textarea class="ads-textarea" id="ads-payload"
          placeholder="Pega aqui datos de la cuenta. Ejemplos:&#10;&#10;- Export CSV de Google Ads (campañas, keywords, search terms)&#10;- Screenshot de Events Manager / Pixel health&#10;- Metricas: CTR, CPC, CVR, CPA, ROAS, impressions, spend&#10;- URL de la landing page o competidor&#10;- Brief del cliente: 'tenemos 3 campañas activas, gastamos $5k/mes en Meta, CPA $35, target $20...'&#10;&#10;Mientras mas contexto, mejor el analisis."></textarea>

        <button class="ads-run-btn" id="ads-run-btn" onclick="runAdsSkill()">
          <span id="ads-run-icon">&#x26A1;</span>
          <span id="ads-run-lbl">Ejecutar analisis</span>
        </button>
      </div>

      <div>
        <div class="ads-section-title"><span class="num">&#x2728;</span> Resultado</div>
        <div id="ads-output-wrap" class="ads-output" style="min-height:300px;">
          <div style="text-align:center;padding:60px 20px;color:#64748b;">
            <div style="font-size:48px;margin-bottom:12px;">&#x1F680;</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8;">Configura los pasos 1-4 y ejecuta</div>
            <div style="font-size:11px;margin-top:8px;">El reporte aparecera aqui en markdown</div>
          </div>
        </div>

        <div class="ads-history">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:12px;font-weight:700;color:#94a3b8;">&#x23F1; Historial reciente</div>
            <button class="btn btn-outline btn-sm" onclick="loadAdsHistory()">Actualizar</button>
          </div>
          <div id="ads-history-list" style="font-size:12px;color:#64748b;">Cargando...</div>
        </div>
      </div>
    </div>
  `;

  selectAdsPlatform('meta');
  selectAdsAction('audit', false);
  loadAdsHistory();
}

function selectAdsPlatform(id) {
  ADS_STATE.platform = id;
  document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => {
    el.classList.toggle('active', el.dataset.platform === id);
  });
}
function selectAdsAction(id, isGlobal) {
  ADS_STATE.action = id;
  document.querySelectorAll('#tab-ads .ads-act-card').forEach(el => {
    el.classList.toggle('active', el.dataset.action === id);
  });
  if (isGlobal) {
    document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => el.style.opacity = '0.4');
  } else {
    document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => el.style.opacity = '1');
  }
}

// Markdown -> HTML minimal renderer (sin dependencias externas)
function adsRenderMarkdown(md) {
  if (!md) return '';
  let html = md;
  html = html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g,(m,l,c)=>'<pre><code>'+c.trim()+'</code></pre>');
  html = html.replace(/`([^`\n]+)`/g,'<code>$1</code>');
  html = html.replace(/^### (.+)$/gm,'<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,'<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,'<h1>$1</h1>');
  html = html.replace(/^&gt; (.+)$/gm,'<blockquote>$1</blockquote>');
  html = html.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*([^\*\n]+)\*(?!\*)/g,'<em>$1</em>');
  // tables
  html = html.replace(/(\|.+\|\n\|[\s\-:|]+\|\n(?:\|.+\|\n?)+)/g,(tbl)=>{
    const lines = tbl.trim().split('\n');
    const head = lines[0].split('|').slice(1,-1).map(s=>s.trim());
    const rows = lines.slice(2).map(r=>r.split('|').slice(1,-1).map(s=>s.trim()));
    let h='<table><thead><tr>'+head.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';
    rows.forEach(r=>h+='<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>');
    return h+'</tbody></table>';
  });
  // lists
  html = html.replace(/(^- .+(?:\n- .+)+)/gm,(m)=>'<ul>'+m.split('\n').map(l=>'<li>'+l.replace(/^- /,'')+'</li>').join('')+'</ul>');
  html = html.replace(/(^\d+\. .+(?:\n\d+\. .+)+)/gm,(m)=>'<ol>'+m.split('\n').map(l=>'<li>'+l.replace(/^\d+\. /,'')+'</li>').join('')+'</ol>');
  // paragraphs (lineas que no son ya bloque)
  html = html.split(/\n{2,}/).map(p=>{
    if (/^<(h[1-6]|ul|ol|pre|table|blockquote)/.test(p.trim())) return p;
    return p.trim() ? '<p>'+p.replace(/\n/g,'<br>')+'</p>' : '';
  }).join('\n');
  return html;
}

async function runAdsSkill() {
  if (ADS_STATE.running) return;
  const isGlobal = ['competitor','landing','test','dna'].includes(ADS_STATE.action);
  const platform = isGlobal ? null : ADS_STATE.platform;
  const action = ADS_STATE.action;
  const payload = (document.getElementById('ads-payload')||{}).value || '';
  if (payload.trim().length < 10) {
    alert('Pega al menos 10 caracteres de datos o contexto.');
    return;
  }
  const business_context = {
    client_name: (document.getElementById('ads-client')||{}).value || '',
    industry:    (document.getElementById('ads-industry')||{}).value || '',
    monthly_spend_usd: parseInt((document.getElementById('ads-spend')||{}).value || '0',10) || null,
    goal:        (document.getElementById('ads-goal')||{}).value || '',
    active_platforms: platform ? [platform] : [],
  };

  ADS_STATE.running = true;
  const btn = document.getElementById('ads-run-btn');
  btn.disabled = true;
  document.getElementById('ads-run-icon').innerHTML = '&#x231B;';
  document.getElementById('ads-run-lbl').textContent = 'Analizando con Claude...';

  const out = document.getElementById('ads-output-wrap');
  out.innerHTML = `
    <div class="ads-loader">
      <div class="ring"></div>
      <div class="lbl">Claude esta procesando ${(platform||'').toUpperCase()} ${action.toUpperCase()}</div>
      <div class="sub">Cargando skills (~30k tokens) + analizando tus datos. Suele tardar 20-40s.</div>
    </div>`;

  try {
    const r = await fetch('/api/marketing/ads/run', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({platform, action, payload, business_context}),
    });
    const data = await r.json();
    if (!r.ok || data.error) {
      out.innerHTML = `<div style="color:#f87171;font-weight:700;font-size:14px;">&#x26A0; Error</div>
        <div style="color:#fca5a5;font-size:12px;margin-top:8px;">${data.error||'Fallo desconocido'}</div>
        ${data.detail ? '<pre style="background:#0f172a;padding:10px;border-radius:8px;font-size:11px;color:#94a3b8;margin-top:10px;overflow-x:auto;">'+data.detail+'</pre>' : ''}`;
    } else {
      const cacheTag = data.cache_read_tokens ? ` <span style="color:#34d399;">cache hit ${data.cache_read_tokens.toLocaleString()} tok</span>` : '';
      out.innerHTML = adsRenderMarkdown(data.text || '(sin texto)') +
        `<div class="ads-meta">
          <span>&#x1F916; ${data.model||'?'}</span>
          <span>&#x21AA; in: ${(data.input_tokens||0).toLocaleString()}</span>
          <span>&#x21AA; out: ${(data.output_tokens||0).toLocaleString()}</span>
          ${cacheTag ? '<span>'+cacheTag+'</span>' : ''}
          <span>&#x1F4B5; ~$${(data.cost_usd_estimate||0).toFixed(4)}</span>
        </div>`;
      loadAdsHistory();
    }
  } catch (e) {
    out.innerHTML = `<div style="color:#f87171;">Error de red: ${e.message}</div>`;
  } finally {
    ADS_STATE.running = false;
    btn.disabled = false;
    document.getElementById('ads-run-icon').innerHTML = '&#x26A1;';
    document.getElementById('ads-run-lbl').textContent = 'Ejecutar analisis';
  }
}

async function loadAdsHistory() {
  const wrap = document.getElementById('ads-history-list');
  if (!wrap) return;
  try {
    const r = await fetch('/api/marketing/ads/log');
    const list = await r.json();
    if (!Array.isArray(list) || list.length === 0) {
      wrap.innerHTML = '<div style="color:#64748b;padding:8px;">Sin ejecuciones aun.</div>';
      return;
    }
    wrap.innerHTML = list.slice(0,12).map(x => {
      const cost = x.cost_usd != null ? '$'+Number(x.cost_usd).toFixed(3) : '';
      const plat = x.platform ? x.platform.toUpperCase() : 'GLOBAL';
      return `<div class="ads-history-item" onclick="loadAdsLogDetail(${x.id})">
        <span style="background:#4c1d95;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;">${plat}</span>
        <span style="color:#a78bfa;font-weight:600;">${x.accion||''}</span>
        <span style="color:#cbd5e1;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${x.client||x.preview||''}</span>
        <span style="color:#64748b;font-size:10px;">${(x.fecha||'').slice(5,16)}</span>
        <span style="color:#34d399;font-size:10px;">${cost}</span>
      </div>`;
    }).join('');
  } catch (e) {
    wrap.innerHTML = '<div style="color:#f87171;">Error: '+e.message+'</div>';
  }
}

async function loadAdsLogDetail(id) {
  const out = document.getElementById('ads-output-wrap');
  out.innerHTML = `<div class="ads-loader"><div class="ring"></div><div class="lbl">Cargando #${id}</div></div>`;
  try {
    const r = await fetch('/api/marketing/ads/log/'+id);
    const data = await r.json();
    if (!r.ok) {
      out.innerHTML = '<div style="color:#f87171;">No se pudo cargar</div>';
      return;
    }
    out.innerHTML = adsRenderMarkdown(data.text || '(vacio)') +
      `<div class="ads-meta">
        <span>&#x1F516; #${data.id}</span>
        <span>${(data.platform||'global').toUpperCase()} / ${data.accion}</span>
        <span>&#x1F464; ${data.ejecutado_por||'?'}</span>
        <span>&#x1F4C5; ${data.fecha||''}</span>
        <span>&#x1F4B5; ~$${(data.cost_usd||0).toFixed(4)}</span>
      </div>`;
  } catch (e) {
    out.innerHTML = '<div style="color:#f87171;">Error: '+e.message+'</div>';
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────────────────────────
loadDashboard();
</script>
</body>
</html>"""
