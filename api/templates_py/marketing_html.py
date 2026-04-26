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
  <button class="tab-btn active" onclick="switchTab('dashboard')">&#x1F3AF; Dashboard</button>
  <button class="tab-btn" onclick="switchTab('campanas')">&#x1F4E2; Campañas</button>
  <button class="tab-btn" onclick="switchTab('influencers')">&#x1F465; Influencers</button>
  <button class="tab-btn" onclick="switchTab('contenido')">&#x1F4C5; Contenido</button>
  <button class="tab-btn" onclick="switchTab('agentes')">&#x1F916; Agentes IA</button>
  <button class="tab-btn" onclick="switchTab('analytics')">&#x1F4CA; Analytics</button>
  <button class="tab-btn" onclick="switchTab('agencia')">&#x1F3E2; Agencia</button>
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
<!-- TAB: CONTENIDO -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-contenido" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4C5; Calendario de Contenido</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;">
      <select id="cont-filtro-estado" onchange="loadContenido()" style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;color:#e2e8f0;font-size:13px;">
        <option value="">Todos</option>
        <option value="Borrador">Borrador</option>
        <option value="Programado">Programado</option>
        <option value="Publicado">Publicado</option>
      </select>
      <button class="btn btn-primary btn-sm" onclick="openContenidoModal()">+ Nuevo</button>
    </div>
  </div>
  <div id="cont-alert" style="display:none;"></div>

  <!-- Vista tabla -->
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Tipo</th><th>Plataforma</th><th>Campaña</th><th>Influencer</th><th>Fecha</th><th>Estado</th><th>Likes</th><th>Alcance</th><th>Conversiones</th><th>Acciones</th></tr></thead>
        <tbody id="cont-body"><tr class="empty-row"><td colspan="10"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: AGENTES IA -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-agentes" class="tab-panel">
  <div class="page-title">&#x1F916; Agentes IA — Marketing</div>
  <div class="page-sub">10 agentes inteligentes con Claude AI — análisis real de datos ERP + Shopify + GHL + Instagram.</div>

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
<div id="tab-analytics" class="tab-panel">
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


<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- MODALS -->
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
      <div class="form-group"><label>Fecha Publicación</label><input type="date" id="cont-fecha"></div>
      <div class="form-group"><label>Estado</label>
        <select id="cont-estado"><option>Borrador</option><option>Programado</option><option>Publicado</option><option>Archivado</option></select>
      </div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>URL Publicación</label><input id="cont-url" placeholder="https://..."></div>
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
      <div class="form-group"><label>Caption / Descripción</label><textarea id="cont-caption"></textarea></div>
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
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: AGENCIA                                                   -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-agencia" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:6px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">&#x1F3E2; Agencia &#x2014; Inteligencia de Mercado</div>
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
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach((b,i)=>{
    const n = ['dashboard','campanas','influencers','contenido','agentes','analytics','agencia'][i];
    b.classList.toggle('active', n===name);
  });
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if(!_loaded[name]) { _loaded[name]=true; loadTab(name); }
}
function loadTab(name) {
  if(name==='dashboard') loadDashboard();
  else if(name==='campanas') loadCampanas();
  else if(name==='influencers') loadInfluencers();
  else if(name==='contenido') loadContenido();
  else if(name==='agentes') { loadAgentLog(); loadCampanasForSelect(); loadConnections(); }
  else if(name==='analytics') loadAnalytics();
  else if(name==='agencia') loadAgencia();
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
async function loadInfluencers() {
  const q = document.getElementById('inf-search').value;
  const url = '/api/marketing/influencers-panel'+(q?'?q='+encodeURIComponent(q):'');
  let data;
  try { data = await fetch(url).then(r=>r.json()); } catch(e) { data = {influencers:[], kpis:{}}; }
  // Show debug error if backend returned one
  if(data._error) { console.warn('[panel error]', data._error, data._trace); }
  const infs = data.influencers || [];
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
      estadoBadge = '<span style="background:#78350f;color:#fcd34d;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">\u23f3 Pendiente</span>';
    } else if(r.pagos_count>0) {
      estadoBadge = '<span style="background:#064e3b;color:#34d399;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">\u2713 Al d\u00eda</span>';
    } else {
      estadoBadge = '<span style="background:#1e293b;color:#64748b;padding:2px 8px;border-radius:12px;font-size:11px;">Sin pagos</span>';
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
        +`<button class="btn btn-outline btn-sm" onclick="verHistorial(${r.id},${JSON.stringify(r).replace(/`/g,'\`')})" title="Ver historial" style="color:#818cf8;border-color:#818cf8;">&#x1F4CB;</button> `
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
    cedula_nit: document.getElementById('inf-cedula').value.trim()
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
async function loadContenido() {
  const estado = document.getElementById('cont-filtro-estado').value;
  const url = '/api/marketing/contenido'+(estado?'?estado='+estado:'');
  const rows = await fetch(url).then(r=>r.json());
  const body = document.getElementById('cont-body');
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="10">Sin contenido registrado.</td></tr>'; return; }
  body.innerHTML = rows.map(r=>`
    <tr>
      <td><span class="badge badge-gray">${r.tipo}</span></td>
      <td>${r.plataforma}</td>
      <td style="color:#818cf8;">${r.campana_nombre||'—'}</td>
      <td>${r.influencer_nombre||'<span style="color:#64748b;">Interno</span>'}</td>
      <td>${r.fecha_publicacion||'—'}</td>
      <td>${badgeEstadoCont(r.estado)}</td>
      <td>❤️ ${fmt(r.likes)}</td>
      <td>👁 ${fmt(r.alcance)}</td>
      <td>🎯 ${r.conversiones}</td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="editContenido(${r.id})">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="deleteContenido(${r.id})">🗑</button>
      </td>
    </tr>`).join('');
}

async function openContenidoModal() {
  document.getElementById('cont-edit-id').value='';
  document.getElementById('modal-cont-title').textContent='Nueva Pieza de Contenido';
  ['url','caption'].forEach(f=>document.getElementById('cont-'+f).value='');
  ['likes','comentarios','alcance','conversiones'].forEach(f=>document.getElementById('cont-'+f).value=0);
  document.getElementById('cont-fecha').value='';
  document.getElementById('cont-tipo').value='Post';
  document.getElementById('cont-plataforma').value='Instagram';
  document.getElementById('cont-estado').value='Borrador';
  await loadCampanasForSelect('cont-campana-sel');
  await loadInfluencersForSelect('cont-influencer-sel');
  document.getElementById('modal-contenido').classList.add('open');
}

async function editContenido(id) {
  const rows = await fetch('/api/marketing/contenido').then(r=>r.json());
  const r = rows.find(x=>x.id===id);
  if(!r) return;
  document.getElementById('cont-edit-id').value=id;
  document.getElementById('modal-cont-title').textContent='Editar Contenido';
  document.getElementById('cont-url').value=r.url_publicacion||'';
  document.getElementById('cont-caption').value=r.caption||'';
  document.getElementById('cont-likes').value=r.likes||0;
  document.getElementById('cont-comentarios').value=r.comentarios||0;
  document.getElementById('cont-alcance').value=r.alcance||0;
  document.getElementById('cont-conversiones').value=r.conversiones||0;
  document.getElementById('cont-fecha').value=r.fecha_publicacion||'';
  document.getElementById('cont-tipo').value=r.tipo||'Post';
  document.getElementById('cont-plataforma').value=r.plataforma||'Instagram';
  document.getElementById('cont-estado').value=r.estado||'Borrador';
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
    estado: document.getElementById('cont-estado').value,
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
  alerta_stock: 'Ver alertas stock'
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
      resultDiv.innerHTML = formatAgentResult(agente, data);
    }
    resultDiv.classList.add('show');
    loadAgentLog();
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

  return `<pre>${JSON.stringify(data, null, 2)}</pre>${fmtIA(data)}`;
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
function verHistorial(id, inf) {
  const fmtM = v => v>=1e6?'$'+(v/1e6).toFixed(1)+'M':v>=1e3?'$'+(v/1e3).toFixed(0)+'K':'$'+Number(v||0).toLocaleString('es-CO');
  document.getElementById('hist-title').textContent = '📋 ' + inf.nombre;
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

// ──────────────────────────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────────────────────────
loadDashboard();
</script>
</body>
</html>"""
