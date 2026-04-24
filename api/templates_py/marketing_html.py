MARKETING_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Marketing — ÁNIMUS Lab</title>
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
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-brand">
    <h1>&#x1F4E3; Marketing</h1>
    <span>ÁNIMUS Lab</span>
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
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: DASHBOARD -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-dashboard" class="tab-panel active">
  <div class="page-title">&#x1F3AF; Dashboard Marketing</div>
  <div class="page-sub" id="dash-fecha">Cargando...</div>

  <div class="kpi-grid" id="dash-kpis">
    <div class="kpi-card"><div class="kpi-label">Campañas</div><div class="kpi-val">—</div></div>
  </div>

  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0 20px;">
    <span style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px;">Integraciones</span>
    <div id="pill-shopify" class="platform-pill pill-off">🛍️ Shopify</div>
    <div id="pill-ghl" class="platform-pill pill-off">📋 GHL</div>
    <div id="pill-ig" class="platform-pill pill-off">📸 Instagram</div>
    <button id="btn-sync-shopify" class="btn btn-outline btn-sm" onclick="syncPlatform('shopify')" style="margin-left:8px;">↻ Sync Shopify</button>
    <button id="btn-sync-ghl" class="btn btn-outline btn-sm" onclick="syncPlatform('ghl')">↻ Sync GHL</button>
    <button id="btn-sync-ig" class="btn btn-outline btn-sm" onclick="syncPlatform('instagram')">↻ Sync IG</button>
    <span id="sync-status" style="font-size:11px;color:#64748b;"></span>
  </div>

  <div class="grid2" style="margin-bottom:20px;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4E2; Campañas Activas</span></div>
      <div class="card-body">
        <table><thead><tr><th>Nombre</th><th>Canal</th><th>Estado</th><th>Budget</th><th>Ventas</th></tr></thead>
        <tbody id="dash-campanas"><tr class="empty-row"><td colspan="5">Cargando...</td></tr></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4C8; Tendencias SKU (últimos 90d)</span></div>
      <div class="card-body" id="dash-tendencias">Cargando...</div>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4F1; Contenido Reciente</span></div>
      <div class="card-body">
        <table><thead><tr><th>Tipo</th><th>Plataforma</th><th>Estado</th><th>Alcance</th></tr></thead>
        <tbody id="dash-contenido"><tr class="empty-row"><td colspan="4">Cargando...</td></tr></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4B0; Presupuesto por Canal</span></div>
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
  <div id="inf-alert" style="display:none;"></div>
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>#</th><th>Nombre</th><th>Red</th><th>@Usuario</th><th>Seguidores</th><th>ER%</th><th>Nicho</th><th>Tarifa/post</th><th>Campañas</th><th>Conversiones</th><th>Estado</th><th>Acciones</th></tr></thead>
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
  <div class="page-title">&#x1F916; Agentes IA — ÁNIMUS Lab</div>
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
  <div class="page-title">&#x1F4CA; Analytics</div>
  <div class="page-sub">ROI, tendencias y análisis de rendimiento.</div>

  <div class="kpi-grid" id="analytics-kpis">
    <div class="kpi-card blue"><div class="kpi-label">ROI Global</div><div class="kpi-val" id="an-roi">—</div><div class="kpi-sub">Return on investment</div></div>
    <div class="kpi-card green"><div class="kpi-label">Ventas atribuidas</div><div class="kpi-val" id="an-ventas">—</div><div class="kpi-sub">Total campañas</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Mejor campaña</div><div class="kpi-val" id="an-mejor" style="font-size:14px;">—</div><div class="kpi-sub">Por ROI</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Mejor canal</div><div class="kpi-val" id="an-canal" style="font-size:14px;">—</div><div class="kpi-sub">Por ROI promedio</div></div>
  </div>

  <div class="grid2" style="margin-bottom:20px;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4E2; ROI por Campaña</span></div>
      <div class="card-body">
        <table>
          <thead><tr><th>Campaña</th><th>Canal</th><th>Invertido</th><th>Ventas</th><th>ROI</th><th>% Objetivo</th></tr></thead>
          <tbody id="an-campanas-body"><tr class="empty-row"><td colspan="6">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F465; ROI por Influencer</span></div>
      <div class="card-body">
        <table>
          <thead><tr><th>Influencer</th><th>Red</th><th>Campañas</th><th>Invertido</th><th>Conversiones</th><th>Costo/Conv</th></tr></thead>
          <tbody id="an-infl-body"><tr class="empty-row"><td colspan="6">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card" style="margin-bottom:20px;">
    <div class="card-hdr">
      <span class="card-title">&#x1F4C8; Tendencias SKU</span>
      <select id="an-meses-sel" onchange="loadAnalyticsTendencias()" style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:4px 8px;color:#e2e8f0;font-size:12px;">
        <option value="3">3 meses</option>
        <option value="6" selected>6 meses</option>
        <option value="12">12 meses</option>
      </select>
    </div>
    <div class="card-body">
      <div id="an-tendencias-body">Cargando...</div>
    </div>
  </div>

  <div class="card">
    <div class="card-hdr"><span class="card-title">&#x1F4B0; Rendimiento por Canal</span></div>
    <div class="card-body">
      <table>
        <thead><tr><th>Canal</th><th>Campañas</th><th>Total invertido</th><th>Total ventas</th><th>ROI%</th></tr></thead>
        <tbody id="an-canal-body"><tr class="empty-row"><td colspan="5">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- MODALS -->
<!-- ═══════════════════════════════════════════════════════════════ -->

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
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-influencer')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveInfluencer()">Guardar</button>
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
    const n = ['dashboard','campanas','influencers','contenido','agentes','analytics'][i];
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
}

// ──────────────────────────────────────────────────────────────────────────────
// DASHBOARD
// ──────────────────────────────────────────────────────────────────────────────
async function loadDashboard() {
  loadConnections();
  const data = await fetch('/api/marketing/dashboard').then(r=>r.json());
  const k = data.kpis;
  document.getElementById('dash-fecha').textContent = 'Actualizado: '+new Date().toLocaleString('es-CO');
  document.getElementById('dash-kpis').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Campañas totales</div><div class="kpi-val">${k.total_campanas}</div><div class="kpi-sub">${k.activas} activas</div></div>
    <div class="kpi-card blue"><div class="kpi-label">Presupuesto Total</div><div class="kpi-val" style="font-size:18px;">${fmtM(k.presupuesto_total)}</div><div class="kpi-sub">${fmtM(k.presupuesto_gastado)} ejecutado (${k.pct_ejecutado}%)</div></div>
    <div class="kpi-card ${k.roi_global>=0?'green':'red'}"><div class="kpi-label">ROI Global</div><div class="kpi-val">${k.roi_global>0?'+':''}${k.roi_global}%</div><div class="kpi-sub">Ventas ${fmtM(k.ventas_total)}</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Influencers activos</div><div class="kpi-val">${k.total_influencers}</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Contenido publicado</div><div class="kpi-val">${k.contenido_publicado}</div></div>
    <div class="kpi-card blue"><div class="kpi-label">Conversiones</div><div class="kpi-val">${fmt(k.total_conversiones)}</div><div class="kpi-sub">Alcance ${fmt(k.total_alcance)}</div></div>
  `;

  // Campañas activas
  const cBody = document.getElementById('dash-campanas');
  if(!data.campanas_activas.length) { cBody.innerHTML='<tr class="empty-row"><td colspan="5">Sin campañas</td></tr>'; }
  else cBody.innerHTML = data.campanas_activas.map(c=>`
    <tr>
      <td style="font-weight:700;">${c.nombre}</td>
      <td><span class="badge badge-gray">${c.canal||'—'}</span></td>
      <td>${badgeEstadoCamp(c.estado)}</td>
      <td>${fmtM(c.presupuesto)}</td>
      <td style="color:#34d399;">${fmtM(c.resultado_ventas)}</td>
    </tr>`).join('');

  // Tendencias
  const tends = {};
  data.tendencias.forEach(t=>{ if(!tends[t.sku]) tends[t.sku]=0; tends[t.sku]+=t.total_liberado; });
  const tendArr = Object.entries(tends).sort((a,b)=>b[1]-a[1]).slice(0,8);
  const maxVal = tendArr[0]?tendArr[0][1]:1;
  document.getElementById('dash-tendencias').innerHTML = tendArr.length
    ? tendArr.map(([sku,val])=>`
      <div class="trend-item">
        <span class="trend-sku">${sku}</span>
        <div class="trend-bar"><div class="progress-bar"><div class="progress-fill" style="width:${Math.round(val/maxVal*100)}%;"></div></div></div>
        <span class="trend-flat">${fmt(val)} uds</span>
      </div>`).join('')
    : '<div style="color:#64748b;text-align:center;padding:20px;">Sin datos de liberaciones</div>';

  // Contenido reciente
  const coBody = document.getElementById('dash-contenido');
  if(!data.contenido_reciente.length) { coBody.innerHTML='<tr class="empty-row"><td colspan="4">Sin contenido</td></tr>'; }
  else coBody.innerHTML = data.contenido_reciente.map(c=>`
    <tr><td>${c.tipo}</td><td>${c.plataforma}</td><td>${badgeEstadoCont(c.estado)}</td><td>${fmt(c.alcance)}</td></tr>`).join('');

  // Por canal
  const chEl = document.getElementById('dash-canales');
  if(!data.por_canal.length) { chEl.innerHTML='<div style="color:#64748b;text-align:center;padding:20px;">Sin datos de campañas por canal</div>'; }
  else chEl.innerHTML = data.por_canal.map(ch=>`
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
  const url = '/api/marketing/influencers'+(q?'?q='+encodeURIComponent(q):'');
  const rows = await fetch(url).then(r=>r.json());
  const body = document.getElementById('inf-body');
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="12">Sin influencers registrados.</td></tr>'; return; }
  body.innerHTML = rows.map(r=>`
    <tr>
      <td style="color:#64748b;">${r.id}</td>
      <td style="font-weight:700;">${r.nombre}</td>
      <td><span class="badge badge-gray">${r.red_social}</span></td>
      <td style="color:#818cf8;">${r.usuario_red||'—'}</td>
      <td>${r.seguidores>=1000?(r.seguidores/1000).toFixed(1)+'K':r.seguidores}</td>
      <td>${r.engagement_rate?r.engagement_rate+'%':'—'}</td>
      <td>${r.nicho||'—'}</td>
      <td>${r.tarifa?fmtM(r.tarifa):'—'}</td>
      <td>${r.stats?.campanas||0}</td>
      <td>${r.stats?.conversiones||0}</td>
      <td>${badgeEstadoInf(r.estado)}</td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="editInfluencer(${r.id})">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="deleteInfluencer(${r.id},'${r.nombre.replace(/'/g,"\\'")}')">🗑</button>
      </td>
    </tr>`).join('');
}

function openInfluencerModal() {
  document.getElementById('inf-edit-id').value='';
  document.getElementById('modal-inf-title').textContent='Nuevo Influencer';
  ['nombre','usuario','nicho','email','tel','notas'].forEach(f=>document.getElementById('inf-'+f).value='');
  ['seguidores','er','tarifa'].forEach(f=>document.getElementById('inf-'+f).value=0);
  document.getElementById('inf-red').value='Instagram';
  document.getElementById('inf-estado').value='Activo';
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
    notas: document.getElementById('inf-notas').value.trim()
  };
  if(!body.nombre) { showAlert('inf-alert','El nombre es obligatorio','error'); return; }
  const url = id ? `/api/marketing/influencers/${id}` : '/api/marketing/influencers';
  const method = id?'PUT':'POST';
  const resp = await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await resp.json();
  if(data.ok||data.id) { closeModal('modal-influencer'); showAlert('inf-alert',id?'Influencer actualizado':'Influencer creado'); loadInfluencers(); }
  else showAlert('inf-alert',data.error||'Error','error');
}

async function deleteInfluencer(id, nombre) {
  if(!confirm(`¿Eliminar influencer "${nombre}"?`)) return;
  const resp = await fetch(`/api/marketing/influencers/${id}`,{method:'DELETE'});
  const data = await resp.json();
  if(data.ok) { showAlert('inf-alert','Influencer eliminado'); loadInfluencers(); }
  else showAlert('inf-alert',data.error||'Error','error');
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

async function syncPlatform(platform) {
  const btn = document.getElementById('btn-sync-'+platform);
  const status = document.getElementById('sync-status');
  btn.disabled = true; btn.textContent = 'Sincronizando...';
  status.textContent = '';
  try {
    const resp = await fetch(`/api/marketing/sync/${platform}`, {method:'POST'});
    const data = await resp.json();
    if(data.ok) {
      status.style.color = '#34d399';
      status.textContent = `✓ ${platform}: ${data.synced} registros sincronizados`;
      loadConnections();
    } else {
      status.style.color = '#f87171';
      status.textContent = data.error || 'Error al sincronizar';
    }
  } catch(e) {
    status.style.color = '#f87171';
    status.textContent = 'Error: ' + e.message;
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
  document.getElementById('modal-agent-content').textContent = content;
  document.getElementById('modal-agente-result').classList.add('open');
}

// ──────────────────────────────────────────────────────────────────────────────
// ANALYTICS
// ──────────────────────────────────────────────────────────────────────────────
async function loadAnalytics() {
  await Promise.all([loadAnalyticsROI(), loadAnalyticsTendencias()]);
}

async function loadAnalyticsROI() {
  const data = await fetch('/api/marketing/analytics/roi').then(r=>r.json());

  // KPIs
  const totalInv = data.campanas.reduce((s,c)=>s+(c.presupuesto_gastado||0),0);
  const totalVentas = data.campanas.reduce((s,c)=>s+(c.resultado_ventas||0),0);
  const roiGlobal = totalInv>0 ? ((totalVentas-totalInv)/totalInv*100).toFixed(1) : 0;
  document.getElementById('an-roi').textContent = (roiGlobal>=0?'+':'')+roiGlobal+'%';
  document.getElementById('an-ventas').textContent = fmtM(totalVentas);
  const mejorCamp = data.campanas.find(c=>c.roi_pct!==null);
  document.getElementById('an-mejor').textContent = mejorCamp ? mejorCamp.nombre : '—';
  const mejorCanal = data.por_canal[0];
  document.getElementById('an-canal').textContent = mejorCanal ? mejorCanal.canal : '—';

  // Tabla campañas ROI
  const cBody = document.getElementById('an-campanas-body');
  if(!data.campanas.length) { cBody.innerHTML='<tr class="empty-row"><td colspan="6">Sin campañas con datos</td></tr>'; }
  else cBody.innerHTML = data.campanas.map(c=>`
    <tr>
      <td style="font-weight:700;">${c.nombre}</td>
      <td><span class="badge badge-gray">${c.canal||'—'}</span></td>
      <td>${fmtM(c.presupuesto_gastado)}</td>
      <td style="color:#34d399;">${fmtM(c.resultado_ventas)}</td>
      <td>${roiBadge(c.roi_pct)}</td>
      <td>${c.pct_objetivo?c.pct_objetivo+'%':'—'}</td>
    </tr>`).join('');

  // Tabla influencers ROI
  const iBody = document.getElementById('an-infl-body');
  if(!data.influencers.length) { iBody.innerHTML='<tr class="empty-row"><td colspan="6">Sin datos</td></tr>'; }
  else iBody.innerHTML = data.influencers.map(i=>`
    <tr>
      <td style="font-weight:700;">${i.nombre}</td>
      <td><span class="badge badge-gray">${i.red_social}</span></td>
      <td>${i.campanas}</td>
      <td>${fmtM(i.total_invertido)}</td>
      <td>${i.conversiones}</td>
      <td>${i.costo_por_conversion?fmtM(i.costo_por_conversion):'—'}</td>
    </tr>`).join('');

  // Tabla por canal
  const chBody = document.getElementById('an-canal-body');
  if(!data.por_canal.length) { chBody.innerHTML='<tr class="empty-row"><td colspan="5">Sin datos por canal</td></tr>'; }
  else chBody.innerHTML = data.por_canal.map(c=>`
    <tr>
      <td style="font-weight:700;">${c.canal}</td>
      <td>${c.campanas}</td>
      <td>${fmtM(c.total_invertido)}</td>
      <td style="color:#34d399;">${fmtM(c.total_ventas)}</td>
      <td>${roiBadge(c.roi_pct)}</td>
    </tr>`).join('');
}

async function loadAnalyticsTendencias() {
  const meses = document.getElementById('an-meses-sel').value;
  const data = await fetch(`/api/marketing/analytics/tendencias?meses=${meses}`).then(r=>r.json());
  const cont = document.getElementById('an-tendencias-body');
  if(!data.crecimiento.length) { cont.innerHTML='<div style="color:#64748b;padding:16px;">Sin datos de liberaciones</div>'; return; }
  const maxAbs = Math.max(...data.crecimiento.map(t=>Math.abs(t.variacion_pct)),1);
  cont.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;">` +
    data.crecimiento.map(t=>{
      const pct = t.variacion_pct;
      const color = pct>20?'#34d399':pct<-20?'#f87171':'#94a3b8';
      const barW = Math.round(Math.abs(pct)/maxAbs*100);
      return `<div style="background:#0f172a;border-radius:8px;padding:12px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-weight:700;">${t.sku}</span>
          <span style="color:${color};font-weight:700;">${pct>0?'+':''}${pct}%</span>
        </div>
        <div class="progress-bar"><div style="width:${barW}%;height:100%;background:${color};border-radius:4px;"></div></div>
        <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:11px;color:#64748b;">
          <span>Reciente: ${fmt(t.reciente_90d)}</span>
          <span>Anterior: ${fmt(t.anterior_90d)}</span>
        </div>
      </div>`;
    }).join('') + '</div>';
}

// ──────────────────────────────────────────────────────────────────────────────
// MODAL HELPERS
// ──────────────────────────────────────────────────────────────────────────────
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal-bg').forEach(m=>m.addEventListener('click',e=>{ if(e.target===m) m.classList.remove('open'); }));

// ──────────────────────────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────────────────────────
loadDashboard();
</script>
</body>
</html>"""
