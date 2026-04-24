ANIMUS_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ÁNIMUS Lab — Centro de Mando</title>
<style>
:root{
  --gold:#d4af37;--gold-light:#f0d060;--gold-dark:#a88a1e;
  --bg:#0a0a0c;--bg2:#111115;--bg3:#18181f;--bg4:#1e1e28;
  --border:#2a2a35;--border2:#333345;
  --text:#e8e8f0;--text2:#9999b0;--text3:#666680;
  --green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--blue:#3b82f6;
  --pink:#e91e8c;--purple:#8b5cf6;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;min-height:100vh;display:flex;flex-direction:column}

/* ── TOPBAR ── */
.topbar{height:56px;background:linear-gradient(135deg,var(--bg2) 0%,#0d0d14 100%);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:16px;position:sticky;top:0;z-index:100}
.topbar-logo{display:flex;align-items:center;gap:10px}
.topbar-logo .icon{width:32px;height:32px;background:linear-gradient(135deg,var(--gold),var(--gold-dark));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px}
.topbar-logo .brand{font-size:18px;font-weight:700;color:var(--gold);letter-spacing:.5px}
.topbar-logo .sub{font-size:11px;color:var(--text3);letter-spacing:2px;text-transform:uppercase;margin-top:1px}
.topbar-divider{width:1px;height:24px;background:var(--border2)}
.topbar-nav{display:flex;gap:4px;flex:1}
.tn-btn{padding:6px 14px;border-radius:6px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;transition:.2s;display:flex;align-items:center;gap:6px}
.tn-btn:hover{background:var(--bg3);color:var(--text)}
.tn-btn.active{background:linear-gradient(135deg,rgba(212,175,55,.15),rgba(212,175,55,.05));color:var(--gold);border:1px solid rgba(212,175,55,.2)}
.tn-btn .dot{width:6px;height:6px;border-radius:50%;background:var(--green);flex-shrink:0}
.topbar-right{display:flex;align-items:center;gap:12px;margin-left:auto}
.platform-pill{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.5px;border:1px solid}
.pill-shopify{background:rgba(150,191,75,.1);color:#96bf4b;border-color:rgba(150,191,75,.3)}
.pill-ghl{background:rgba(59,130,246,.1);color:#60a5fa;border-color:rgba(59,130,246,.3)}
.pill-ig{background:rgba(233,30,140,.1);color:#f472b6;border-color:rgba(233,30,140,.3)}
.pill-off{background:rgba(100,100,120,.1);color:var(--text3);border-color:var(--border)}
.user-chip{padding:4px 12px;background:var(--bg3);border:1px solid var(--border2);border-radius:20px;font-size:12px;color:var(--text2)}
.back-btn{padding:5px 12px;background:transparent;border:1px solid var(--border2);border-radius:6px;color:var(--text2);font-size:12px;cursor:pointer;text-decoration:none;display:flex;align-items:center;gap:6px}
.back-btn:hover{border-color:var(--gold);color:var(--gold)}

/* ── MAIN LAYOUT ── */
.main{flex:1;padding:24px;max-width:1600px;margin:0 auto;width:100%}
.section{display:none}
.section.active{display:block}

/* ── KPI GRID ── */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.kpi{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px;transition:.2s;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--kpi-color,var(--gold))}
.kpi:hover{border-color:var(--border2);transform:translateY(-1px)}
.kpi-label{font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.kpi-value{font-size:26px;font-weight:700;color:var(--text);line-height:1}
.kpi-sub{font-size:11px;color:var(--text2);margin-top:6px}
.kpi-icon{position:absolute;right:12px;top:12px;font-size:20px;opacity:.3}

/* ── CARDS ── */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.card-title{font-size:13px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card-title .badge{padding:2px 8px;border-radius:10px;font-size:10px;background:rgba(212,175,55,.15);color:var(--gold);border:1px solid rgba(212,175,55,.2)}

/* ── GRIDS ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
@media(max-width:900px){.grid-2,.grid-3{grid-template-columns:1fr}}

/* ── TABLES ── */
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{padding:8px 12px;text-align:left;font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text3);border-bottom:1px solid var(--border)}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text)}
.tbl tr:hover td{background:rgba(255,255,255,.02)}
.tbl tr:last-child td{border-bottom:none}

/* ── BADGES / PILLS ── */
.badge-ok{background:rgba(34,197,94,.1);color:var(--green);border:1px solid rgba(34,197,94,.2);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.badge-warn{background:rgba(245,158,11,.1);color:var(--yellow);border:1px solid rgba(245,158,11,.2);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.badge-crit{background:rgba(239,68,68,.1);color:var(--red);border:1px solid rgba(239,68,68,.2);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.badge-abc-a{background:rgba(212,175,55,.15);color:var(--gold);border:1px solid rgba(212,175,55,.3);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}
.badge-abc-b{background:rgba(59,130,246,.1);color:var(--blue);border:1px solid rgba(59,130,246,.3);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}
.badge-abc-c{background:rgba(100,100,120,.1);color:var(--text3);border:1px solid var(--border);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}

/* ── AGENT CARDS ── */
.agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.agent-card{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px;transition:.2s;cursor:pointer}
.agent-card:hover{border-color:var(--gold);background:var(--bg3);transform:translateY(-2px)}
.agent-card.running{border-color:var(--gold);animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(212,175,55,.3)}50%{box-shadow:0 0 0 8px rgba(212,175,55,0)}}
.agent-icon{font-size:32px;margin-bottom:12px}
.agent-name{font-size:15px;font-weight:700;color:var(--text);margin-bottom:6px}
.agent-desc{font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:16px}
.agent-btn{width:100%;padding:10px;background:linear-gradient(135deg,rgba(212,175,55,.15),rgba(212,175,55,.05));border:1px solid rgba(212,175,55,.3);border-radius:8px;color:var(--gold);font-size:13px;font-weight:600;cursor:pointer;transition:.2s}
.agent-btn:hover{background:rgba(212,175,55,.25);border-color:var(--gold)}
.agent-result{margin-top:16px;padding:14px;background:var(--bg3);border-radius:8px;font-size:12px;line-height:1.6;color:var(--text2);max-height:300px;overflow-y:auto;display:none}
.agent-result.visible{display:block}

/* ── CALENDAR ── */
.cal-events{display:flex;flex-direction:column;gap:8px}
.cal-event{display:flex;align-items:center;gap:12px;padding:10px 14px;background:var(--bg3);border-radius:8px;border-left:3px solid}
.cal-event-name{font-size:13px;font-weight:600;flex:1}
.cal-event-date{font-size:11px;color:var(--text2)}
.cal-event-days{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px}

/* ── PLATFORM SECTION ── */
.platform-header{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding:16px;background:var(--bg3);border-radius:10px;border:1px solid var(--border2)}
.platform-logo{font-size:28px}
.platform-name{font-size:16px;font-weight:700}
.platform-status{margin-left:auto;display:flex;align-items:center;gap:8px}
.connect-btn{padding:8px 18px;background:linear-gradient(135deg,var(--gold),var(--gold-dark));color:#000;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:.2s}
.connect-btn:hover{opacity:.85}
.sync-btn{padding:8px 14px;background:transparent;border:1px solid var(--border2);border-radius:8px;color:var(--text2);font-size:12px;cursor:pointer;transition:.2s}
.sync-btn:hover{border-color:var(--gold);color:var(--gold)}

/* ── CONTENT STUDIO ── */
.studio-panel{display:grid;grid-template-columns:300px 1fr;gap:20px}
@media(max-width:800px){.studio-panel{grid-template-columns:1fr}}
.studio-controls{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px}
.studio-output{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px}
.form-group{margin-bottom:16px}
.form-label{display:block;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text3);margin-bottom:6px}
.form-input,.form-select,.form-textarea{width:100%;background:var(--bg3);border:1px solid var(--border2);border-radius:8px;color:var(--text);padding:8px 12px;font-size:13px;outline:none;transition:.2s}
.form-input:focus,.form-select:focus,.form-textarea:focus{border-color:var(--gold)}
.form-select option{background:var(--bg3)}
.form-textarea{resize:vertical;min-height:80px;font-family:inherit}
.gen-btn{width:100%;padding:12px;background:linear-gradient(135deg,var(--gold),var(--gold-dark));color:#000;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:.2s;letter-spacing:.5px}
.gen-btn:hover{opacity:.85}
.content-output{background:var(--bg3);border:1px solid var(--border2);border-radius:10px;padding:16px;min-height:200px;white-space:pre-wrap;font-size:13px;line-height:1.7;color:var(--text);font-family:'Courier New',monospace}
.copy-btn{padding:8px 16px;background:transparent;border:1px solid var(--border2);border-radius:6px;color:var(--text2);font-size:12px;cursor:pointer;margin-top:10px;transition:.2s}
.copy-btn:hover{border-color:var(--gold);color:var(--gold)}

/* ── CONFIG FORM ── */
.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:700px){.config-grid{grid-template-columns:1fr}}
.config-card{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px}
.config-card-title{font-size:14px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.save-cfg-btn{padding:10px 20px;background:var(--gold);color:#000;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;margin-top:12px;width:100%}

/* ── SPINNERS / STATES ── */
.loading{display:flex;align-items:center;justify-content:center;padding:40px;color:var(--text3);font-size:13px;gap:8px}
.spinner{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--gold);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{text-align:center;padding:40px;color:var(--text3);font-size:13px}
.empty-icon{font-size:32px;margin-bottom:8px}

/* ── CHART BARS ── */
.bar-chart{display:flex;flex-direction:column;gap:8px}
.bar-row{display:flex;align-items:center;gap:10px}
.bar-label{font-size:12px;color:var(--text2);width:90px;text-align:right;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{flex:1;height:18px;background:var(--bg3);border-radius:4px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--gold),var(--gold-light));border-radius:4px;transition:width .6s ease;display:flex;align-items:center;padding:0 6px}
.bar-val{font-size:11px;font-weight:600;color:#000;white-space:nowrap}

/* ── SECTION HEADER ── */
.sec-header{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.sec-icon{font-size:28px}
.sec-title{font-size:22px;font-weight:700;color:var(--text)}
.sec-sub{font-size:13px;color:var(--text2);margin-top:2px}
.sec-actions{margin-left:auto;display:flex;gap:8px}

/* ── NOTIFICATION ── */
#toast{position:fixed;bottom:24px;right:24px;padding:12px 20px;background:var(--bg3);border:1px solid var(--border2);border-radius:10px;color:var(--text);font-size:13px;z-index:9999;transform:translateY(80px);opacity:0;transition:.3s;max-width:320px}
#toast.show{transform:translateY(0);opacity:1}
#toast.success{border-color:rgba(34,197,94,.4);background:rgba(34,197,94,.1)}
#toast.error{border-color:rgba(239,68,68,.4);background:rgba(239,68,68,.1)}
</style>
</head>
<body>

<!-- TOPBAR -->
<div class="topbar">
  <div class="topbar-logo">
    <div class="icon">✦</div>
    <div>
      <div class="brand">ÁNIMUS Lab</div>
      <div class="sub">Centro de Mando</div>
    </div>
  </div>
  <div class="topbar-divider"></div>
  <div class="topbar-nav">
    <button class="tn-btn active" onclick="showSection('comando')">⚡ Comando</button>
    <button class="tn-btn" onclick="showSection('mercado')">📢 Mercado</button>
    <button class="tn-btn" onclick="showSection('productos')">💎 Productos</button>
    <button class="tn-btn" onclick="showSection('clientes')">👥 Clientes</button>
    <button class="tn-btn" onclick="showSection('instagram')">📸 Instagram</button>
    <button class="tn-btn" onclick="showSection('agentes')">🤖 Agentes IA</button>
    <button class="tn-btn" onclick="showSection('studio')">✍️ Estudio</button>
    <button class="tn-btn" onclick="showSection('config')">⚙️ Config</button>
  </div>
  <div class="topbar-right">
    <span class="platform-pill pill-shopify" id="pill-shopify">Shopify ●</span>
    <span class="platform-pill pill-ghl" id="pill-ghl">GHL ●</span>
    <span class="platform-pill pill-ig" id="pill-ig">Instagram ●</span>
    <div class="topbar-divider"></div>
    <span class="user-chip">👤 {usuario}</span>
    <a class="back-btn" href="/modulos">← Módulos</a>
  </div>
</div>

<div class="main">

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 1 — COMANDO GENERAL
═══════════════════════════════════════════════════════════════ -->
<div class="section active" id="s-comando">
  <div class="sec-header">
    <div class="sec-icon">⚡</div>
    <div>
      <div class="sec-title">Comando General</div>
      <div class="sec-sub" id="cmd-updated">Cargando datos en tiempo real...</div>
    </div>
    <div class="sec-actions">
      <button class="sync-btn" onclick="loadComando()">↻ Actualizar</button>
    </div>
  </div>

  <!-- KPIs principales -->
  <div class="kpi-grid" id="kpi-main">
    <div class="kpi" style="--kpi-color:var(--green)"><div class="kpi-label">Liberaciones 30d</div><div class="kpi-value" id="k-lib">—</div><div class="kpi-sub">Unidades PT</div><div class="kpi-icon">📦</div></div>
    <div class="kpi" style="--kpi-color:var(--gold)"><div class="kpi-label">Revenue Shopify 30d</div><div class="kpi-value" id="k-rev">—</div><div class="kpi-sub" id="k-rev-sub">pedidos</div><div class="kpi-icon">🛍️</div></div>
    <div class="kpi" style="--kpi-color:var(--blue)"><div class="kpi-label">Contactos GHL</div><div class="kpi-value" id="k-ghl">—</div><div class="kpi-sub" id="k-ghl-sub">pipeline</div><div class="kpi-icon">🎯</div></div>
    <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Campañas Activas</div><div class="kpi-value" id="k-camp">—</div><div class="kpi-sub" id="k-inf">influencers</div><div class="kpi-icon">📢</div></div>
    <div class="kpi" style="--kpi-color:var(--purple)"><div class="kpi-label">Avg Likes IG</div><div class="kpi-value" id="k-likes">—</div><div class="kpi-sub" id="k-posts">posts sincronizados</div><div class="kpi-icon">📸</div></div>
    <div class="kpi" style="--kpi-color:var(--red)"><div class="kpi-label">Alertas Calidad</div><div class="kpi-value" id="k-qa">—</div><div class="kpi-sub">críticas/altas</div><div class="kpi-icon">⚠️</div></div>
  </div>

  <div class="grid-2">
    <!-- Stock PT -->
    <div class="card">
      <div class="card-title">💎 Stock Producto Terminado <span class="badge">ERP Live</span></div>
      <div id="stock-chart" class="bar-chart"><div class="loading"><div class="spinner"></div> Cargando...</div></div>
    </div>

    <!-- Calendario cosmético -->
    <div class="card">
      <div class="card-title">📅 Calendario Cosmético <span class="badge">Próximos 90d</span></div>
      <div id="cal-list" class="cal-events"><div class="loading"><div class="spinner"></div></div></div>
    </div>
  </div>

  <div class="grid-2">
    <!-- Top SKUs liberados -->
    <div class="card">
      <div class="card-title">📈 Top SKUs — Liberaciones 30d</div>
      <div id="lib-chart" class="bar-chart"><div class="loading"><div class="spinner"></div></div></div>
    </div>

    <!-- Campañas activas -->
    <div class="card">
      <div class="card-title">📢 Campañas Activas</div>
      <div id="cmd-campanas"><div class="loading"><div class="spinner"></div></div></div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 2 — MERCADO
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-mercado">
  <div class="sec-header">
    <div class="sec-icon">📢</div>
    <div><div class="sec-title">Mercado</div><div class="sec-sub">Campañas, influencers y contenido</div></div>
    <div class="sec-actions">
      <a href="/marketing" style="text-decoration:none">
        <button class="connect-btn">Abrir Marketing Completo →</button>
      </a>
    </div>
  </div>
  <div style="padding:60px;text-align:center;color:var(--text2)">
    <div style="font-size:48px;margin-bottom:16px">📢</div>
    <div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px">Módulo de Marketing</div>
    <div style="font-size:14px;margin-bottom:24px">El módulo completo de marketing está disponible en su propia sección con campañas, influencers, contenido y analytics.</div>
    <a href="/marketing"><button class="connect-btn" style="font-size:15px;padding:14px 28px">Ir a Marketing → </button></a>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 3 — PRODUCTOS
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-productos">
  <div class="sec-header">
    <div class="sec-icon">💎</div>
    <div><div class="sec-title">Inteligencia de Producto</div><div class="sec-sub">Matriz SKU, ABC, cobertura y revenue</div></div>
    <div class="sec-actions"><button class="sync-btn" onclick="loadProductos()">↻ Actualizar</button></div>
  </div>
  <div class="card">
    <div class="card-title">Matriz SKU × Rendimiento</div>
    <div id="prod-table"><div class="loading"><div class="spinner"></div> Analizando SKUs...</div></div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 4 — CLIENTES
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-clientes">
  <div class="sec-header">
    <div class="sec-icon">👥</div>
    <div><div class="sec-title">Inteligencia de Clientes</div><div class="sec-sub">Shopify + GHL CRM</div></div>
    <div class="sec-actions"><button class="sync-btn" onclick="loadClientes()">↻ Actualizar</button></div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🛍️ Top Clientes Shopify</div>
      <div id="top-shopify"><div class="loading"><div class="spinner"></div></div></div>
    </div>
    <div class="card">
      <div class="card-title">🎯 Pipeline GHL</div>
      <div id="ghl-pipeline"><div class="loading"><div class="spinner"></div></div></div>
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="card-title">📍 Distribución Geográfica</div>
      <div id="geo-chart" class="bar-chart"><div class="loading"><div class="spinner"></div></div></div>
    </div>
    <div class="card">
      <div class="card-title">😴 Clientes Dormidos</div>
      <div id="dormidos-panel" style="text-align:center;padding:30px"><div class="loading"><div class="spinner"></div></div></div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 5 — INSTAGRAM
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-instagram">
  <div class="sec-header">
    <div class="sec-icon">📸</div>
    <div><div class="sec-title">Instagram Analytics</div><div class="sec-sub">Posts, alcance y engagement de ÁNIMUS Lab</div></div>
    <div class="sec-actions">
      <button class="sync-btn" onclick="syncPlatform('instagram')">↻ Sincronizar</button>
    </div>
  </div>
  <div id="ig-section"><div class="loading"><div class="spinner"></div> Cargando posts...</div></div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 6 — AGENTES IA
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-agentes">
  <div class="sec-header">
    <div class="sec-icon">🤖</div>
    <div><div class="sec-title">Ejército de Agentes IA</div><div class="sec-sub">10 agentes que analizan datos reales de ERP + Shopify + GHL + Instagram</div></div>
  </div>
  <div class="agent-grid">
    <div class="agent-card" id="card-estacionalidad">
      <div class="agent-icon">📅</div>
      <div class="agent-name">Estacionalidad</div>
      <div class="agent-desc">Cruza campañas programadas con stock actual y el calendario cosmético. Calcula si habrá déficit para Día de la Madre, Black Friday, etc. y cuándo hay que arrancar producción.</div>
      <button class="agent-btn" onclick="runAgente('estacionalidad')">▶ Analizar Estacionalidad</button>
      <div class="agent-result" id="res-estacionalidad"></div>
    </div>
    <div class="agent-card" id="card-oportunidad">
      <div class="agent-icon">🔍</div>
      <div class="agent-name">Oportunidad</div>
      <div class="agent-desc">Detecta SKUs con alto inventario y baja rotación en ERP y Shopify. Genera lista priorizada de productos que necesitan campaña urgente.</div>
      <button class="agent-btn" onclick="runAgente('oportunidad')">▶ Buscar Oportunidades</button>
      <div class="agent-result" id="res-oportunidad"></div>
    </div>
    <div class="agent-card" id="card-roi">
      <div class="agent-icon">💰</div>
      <div class="agent-name">ROI de Campaña</div>
      <div class="agent-desc">Calcula el ROI real de cada campaña cruzando presupuesto ejecutado con ventas generadas en ERP y Shopify. Rankea canales por eficiencia.</div>
      <button class="agent-btn" onclick="runAgente('roi')">▶ Calcular ROI</button>
      <div class="agent-result" id="res-roi"></div>
    </div>
    <div class="agent-card" id="card-tendencias">
      <div class="agent-icon">📈</div>
      <div class="agent-name">Tendencias</div>
      <div class="agent-desc">Compara liberaciones y ventas Shopify de los últimos 90 días vs los 90 anteriores. Detecta momentum por SKU y tendencias del canal online.</div>
      <button class="agent-btn" onclick="runAgente('tendencias')">▶ Ver Tendencias</button>
      <div class="agent-result" id="res-tendencias"></div>
    </div>
    <div class="agent-card" id="card-brief">
      <div class="agent-icon">📋</div>
      <div class="agent-name">Brief de Contenido</div>
      <div class="agent-desc">Genera briefs de contenido para los top SKUs por volumen. Define canal recomendado, formato, claim principal y ángulo de comunicación.</div>
      <button class="agent-btn" onclick="runAgente('brief')">▶ Generar Briefs</button>
      <div class="agent-result" id="res-brief"></div>
    </div>
    <div class="agent-card" id="card-pricing">
      <div class="agent-icon">🏷️</div>
      <div class="agent-name">Pricing Seguro</div>
      <div class="agent-desc">Calcula el descuento máximo posible por SKU manteniendo margen ≥40%. Solo propone promos para productos con más de 4 meses de cobertura.</div>
      <button class="agent-btn" onclick="runAgente('pricing')">▶ Calcular Promos</button>
      <div class="agent-result" id="res-pricing"></div>
    </div>
    <div class="agent-card" id="card-reorden">
      <div class="agent-icon">🔄</div>
      <div class="agent-name">Predicción Reórdenes</div>
      <div class="agent-desc">Analiza el patrón de compra de clientes B2B en Shopify. Predice cuándo hará su próximo pedido y genera alerta de seguimiento proactivo.</div>
      <button class="agent-btn" onclick="runAgente('reorden')">▶ Predecir Reórdenes</button>
      <div class="agent-result" id="res-reorden"></div>
    </div>
    <div class="agent-card" id="card-canibal">
      <div class="agent-icon">⚔️</div>
      <div class="agent-name">Anti-Canibalización</div>
      <div class="agent-desc">Detecta conflictos entre campañas activas: mismo SKU, mismo canal, fechas solapadas. Sugiere escalonamiento para maximizar impacto de cada campaña.</div>
      <button class="agent-btn" onclick="runAgente('canibal')">▶ Detectar Conflictos</button>
      <div class="agent-result" id="res-canibal"></div>
    </div>
    <div class="agent-card" id="card-contenido_auto">
      <div class="agent-icon">✨</div>
      <div class="agent-name">Contenido Auto</div>
      <div class="agent-desc">Genera automáticamente caption de Instagram, asunto de email y texto de WhatsApp para los top 3 SKUs del último mes. Listo para copiar y publicar.</div>
      <button class="agent-btn" onclick="runAgente('contenido_auto')">▶ Auto-Generar</button>
      <div class="agent-result" id="res-contenido_auto"></div>
    </div>
    <div class="agent-card" id="card-alerta_stock">
      <div class="agent-icon">🚨</div>
      <div class="agent-name">Alerta Stock</div>
      <div class="agent-desc">Cruza stock ERP con demanda real de Shopify. Calcula días de cobertura real considerando ambos canales. Alerta crítica si queda menos de 7 días.</div>
      <button class="agent-btn" onclick="runAgente('alerta_stock')">▶ Revisar Stock</button>
      <div class="agent-result" id="res-alerta_stock"></div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 7 — ESTUDIO DE CONTENIDO
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-studio">
  <div class="sec-header">
    <div class="sec-icon">✍️</div>
    <div><div class="sec-title">Estudio de Contenido</div><div class="sec-sub">Generador IA de copy para todos los canales ÁNIMUS Lab</div></div>
  </div>
  <div class="studio-panel">
    <div class="studio-controls">
      <div class="card-title" style="margin-bottom:20px">⚙️ Configurar</div>
      <div class="form-group">
        <label class="form-label">SKU del Producto</label>
        <input class="form-input" id="st-sku" placeholder="Ej: SERA-VIT-C-30" oninput="this.value=this.value.toUpperCase()">
      </div>
      <div class="form-group">
        <label class="form-label">Tipo de Contenido</label>
        <select class="form-select" id="st-tipo">
          <option value="instagram_caption">Instagram Caption</option>
          <option value="tiktok">TikTok Script</option>
          <option value="email">Email Marketing</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="brief_influencer">Brief para Influencer</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Tono de Comunicación</label>
        <select class="form-select" id="st-tono">
          <option value="premium">Premium / Aspiracional</option>
          <option value="cercano">Cercano / Conversacional</option>
          <option value="cientifico">Científico / Técnico</option>
          <option value="urgente">Urgente / Escasez</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Contexto adicional (opcional)</label>
        <textarea class="form-textarea" id="st-ctx" placeholder="Ej: Nuevo lanzamiento, promoción 20% off, temporada Día de la Madre..."></textarea>
      </div>
      <button class="gen-btn" onclick="generarContenido()">✨ Generar Contenido</button>
      <div style="margin-top:16px;padding:12px;background:var(--bg3);border-radius:8px">
        <div style="font-size:11px;color:var(--text3);margin-bottom:8px;font-weight:600;letter-spacing:1px;text-transform:uppercase">Últimas Generaciones</div>
        <div id="historial-list" style="font-size:12px;color:var(--text2)">
          <div class="loading" style="padding:16px"><div class="spinner"></div></div>
        </div>
      </div>
    </div>
    <div class="studio-output">
      <div class="card-title" style="margin-bottom:20px">📝 Resultado</div>
      <div id="st-meta" style="margin-bottom:12px;font-size:12px;color:var(--text2)"></div>
      <div id="st-output" class="content-output">El contenido generado aparecerá aquí.\n\nSelecciona un SKU, tipo de contenido y tono, luego presiona "Generar Contenido".</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="copy-btn" onclick="copiarContenido()">📋 Copiar</button>
        <button class="copy-btn" onclick="generarContenido()" style="border-color:rgba(212,175,55,.3);color:var(--gold)">🔄 Regenerar</button>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     SECCIÓN 8 — CONFIGURACIÓN
═══════════════════════════════════════════════════════════════ -->
<div class="section" id="s-config">
  <div class="sec-header">
    <div class="sec-icon">⚙️</div>
    <div><div class="sec-title">Configuración de Integraciones</div><div class="sec-sub">Conecta Shopify, GHL e Instagram para datos en tiempo real</div></div>
  </div>
  <div class="config-grid">
    <!-- Shopify -->
    <div class="config-card">
      <div class="config-card-title"><span style="font-size:20px">🛍️</span> Shopify</div>
      <div class="form-group">
        <label class="form-label">Shop URL</label>
        <input class="form-input" id="cfg-shopify-shop" placeholder="tu-tienda.myshopify.com">
      </div>
      <div class="form-group">
        <label class="form-label">Access Token</label>
        <input class="form-input" id="cfg-shopify-token" type="password" placeholder="shpat_xxxxxxxxxxxxxxxx">
      </div>
      <button class="save-cfg-btn" onclick="saveCfg('shopify')">💾 Guardar y Sincronizar</button>
      <div id="cfg-shopify-status" style="margin-top:8px;font-size:12px;color:var(--text2)"></div>
    </div>
    <!-- GHL -->
    <div class="config-card">
      <div class="config-card-title"><span style="font-size:20px">🎯</span> GoHighLevel (GHL)</div>
      <div class="form-group">
        <label class="form-label">API Key</label>
        <input class="form-input" id="cfg-ghl-key" type="password" placeholder="eyJhbGc...">
      </div>
      <div class="form-group">
        <label class="form-label">Location ID</label>
        <input class="form-input" id="cfg-ghl-loc" placeholder="xxxxxxxx-xxxx-xxxx">
      </div>
      <button class="save-cfg-btn" onclick="saveCfg('ghl')">💾 Guardar y Sincronizar</button>
      <div id="cfg-ghl-status" style="margin-top:8px;font-size:12px;color:var(--text2)"></div>
    </div>
    <!-- Instagram -->
    <div class="config-card">
      <div class="config-card-title"><span style="font-size:20px">📸</span> Instagram Business</div>
      <div class="form-group">
        <label class="form-label">Access Token (Meta Graph API)</label>
        <input class="form-input" id="cfg-ig-token" type="password" placeholder="EAABsbCS...">
      </div>
      <div class="form-group">
        <label class="form-label">Instagram User ID</label>
        <input class="form-input" id="cfg-ig-uid" placeholder="17841400000000000">
      </div>
      <button class="save-cfg-btn" onclick="saveCfg('instagram')">💾 Guardar y Sincronizar</button>
      <div id="cfg-ig-status" style="margin-top:8px;font-size:12px;color:var(--text2)"></div>
      <div style="margin-top:12px;padding:10px;background:var(--bg3);border-radius:8px;font-size:11px;color:var(--text3);line-height:1.5">
        💡 Para obtener tu token: Meta Business Suite → Configuración → Instagram → API de Instagram Básica → Generar token
      </div>
    </div>
    <!-- Info -->
    <div class="config-card">
      <div class="config-card-title"><span style="font-size:20px">ℹ️</span> Estado de Conexiones</div>
      <div id="conn-status"><div class="loading"><div class="spinner"></div></div></div>
      <div style="margin-top:16px;padding:12px;background:var(--bg3);border-radius:8px;font-size:11px;color:var(--text3);line-height:1.6">
        🔒 Tus credenciales se almacenan de forma segura en la base de datos del servidor.<br><br>
        🔄 La sincronización se activa manualmente. Los datos se guardan localmente para consultas rápidas.<br><br>
        📊 Una vez conectadas, los agentes IA usan datos de TODAS las plataformas.
      </div>
    </div>
  </div>
</div>

</div><!-- /main -->

<div id="toast"></div>

<script>
const BASE = '';
let cmdData = null;

// ─── NAVIGATION ───────────────────────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tn-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('s-' + name).classList.add('active');
  const btns = document.querySelectorAll('.tn-btn');
  btns.forEach(b => { if(b.textContent.toLowerCase().includes(name.slice(0,4))) b.classList.add('active'); });
  if(name === 'comando' && !cmdData) loadComando();
  if(name === 'productos') loadProductos();
  if(name === 'clientes') loadClientes();
  if(name === 'instagram') loadInstagram();
  if(name === 'config') loadConfig();
  if(name === 'studio') loadHistorial();
}

// ─── TOAST ────────────────────────────────────────────────────────────────────
function toast(msg, type='') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show ' + type;
  clearTimeout(t._to);
  t._to = setTimeout(() => t.className = '', 3000);
}

// ─── FORMAT ───────────────────────────────────────────────────────────────────
const fmt = n => n == null ? '—' : n >= 1e6 ? '$' + (n/1e6).toFixed(1) + 'M' : n >= 1e3 ? '$' + (n/1e3).toFixed(0) + 'k' : '$' + Number(n).toLocaleString();
const fmtN = n => n == null ? '—' : Number(n).toLocaleString();

// ─── COMANDO ──────────────────────────────────────────────────────────────────
async function loadComando() {
  document.getElementById('cmd-updated').textContent = 'Actualizando...';
  try {
    const r = await fetch('/api/animus/comando');
    cmdData = await r.json();
    const k = cmdData.kpis;
    document.getElementById('k-lib').textContent = fmtN(k.lib_30d);
    document.getElementById('k-rev').textContent = fmt(k.shopify_ventas_30d);
    document.getElementById('k-rev-sub').textContent = (k.shopify_pedidos_30d||0) + ' pedidos · Total: ' + fmt(k.revenue_total);
    document.getElementById('k-ghl').textContent = fmtN(k.ghl_contactos);
    document.getElementById('k-ghl-sub').textContent = 'Pipeline: ' + fmt(k.ghl_pipeline_valor);
    document.getElementById('k-camp').textContent = k.campanas_activas;
    document.getElementById('k-inf').textContent = (k.influencers_activos||0) + ' influencers activos';
    document.getElementById('k-likes').textContent = fmtN(k.ig_avg_likes);
    document.getElementById('k-posts').textContent = (k.ig_total_posts||0) + ' posts';
    document.getElementById('k-qa').textContent = k.alertas_calidad;

    // Update platform pills
    const conn = cmdData.connected;
    [['shopify','shopify'],['ghl','ghl'],['instagram','ig']].forEach(([k,pid]) => {
      const el = document.getElementById('pill-' + pid);
      if(!el) return;
      if(conn[k]) el.className = 'platform-pill pill-' + pid;
      else el.className = 'platform-pill pill-off';
    });

    // Stock chart
    const sc = document.getElementById('stock-chart');
    if(cmdData.stock_pt && cmdData.stock_pt.length) {
      const max = Math.max(...cmdData.stock_pt.map(s=>s.stock));
      sc.innerHTML = cmdData.stock_pt.slice(0,8).map(s => {
        const pct = max > 0 ? Math.round(s.stock/max*100) : 0;
        return `<div class="bar-row">
          <div class="bar-label">${s.sku}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"><span class="bar-val">${fmtN(s.stock)}</span></div></div>
        </div>`;
      }).join('');
    } else { sc.innerHTML = '<div class="empty"><div class="empty-icon">📦</div>Sin stock registrado</div>'; }

    // Lib chart
    const lc = document.getElementById('lib-chart');
    if(cmdData.lib_30_top && cmdData.lib_30_top.length) {
      const max2 = Math.max(...cmdData.lib_30_top.map(s=>s.uds));
      lc.innerHTML = cmdData.lib_30_top.map(s => {
        const pct = max2 > 0 ? Math.round(s.uds/max2*100) : 0;
        return `<div class="bar-row">
          <div class="bar-label">${s.sku}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"><span class="bar-val">${fmtN(s.uds)}</span></div></div>
        </div>`;
      }).join('');
    } else { lc.innerHTML = '<div class="empty">Sin liberaciones en 30 días</div>'; }

    // Calendar
    const cl = document.getElementById('cal-list');
    if(cmdData.calendario && cmdData.calendario.length) {
      cl.innerHTML = cmdData.calendario.map(ev => {
        const d = ev.dias_restantes;
        const pill = d <= 0 ? '<span style="background:rgba(239,68,68,.2);color:#ef4444;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">HOY</span>'
                   : d <= 14 ? `<span style="background:rgba(245,158,11,.2);color:var(--yellow);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${d}d</span>`
                   : `<span style="background:rgba(100,100,120,.15);color:var(--text2);padding:2px 8px;border-radius:10px;font-size:11px">${d}d</span>`;
        return `<div class="cal-event" style="border-color:${ev.color}">
          <div class="cal-event-name">${ev.evento}</div>
          <div class="cal-event-date">${ev.fecha}</div>
          ${pill}
          <span style="font-size:11px;color:var(--text3)">×${ev.multiplicador}</span>
        </div>`;
      }).join('');
    } else { cl.innerHTML = '<div class="empty">No hay eventos próximos</div>'; }

    // Campañas activas
    const ca = document.getElementById('cmd-campanas');
    if(cmdData.campanas_activas && cmdData.campanas_activas.length) {
      ca.innerHTML = `<table class="tbl"><thead><tr><th>Campaña</th><th>Canal</th><th>Budget</th><th>Ventas</th></tr></thead><tbody>` +
        cmdData.campanas_activas.map(c => `<tr>
          <td><strong>${c.nombre}</strong><br><small style="color:var(--text3)">${c.sku_objetivo||''}</small></td>
          <td>${c.canal||'—'}</td>
          <td>${fmt(c.presupuesto)}</td>
          <td style="color:var(--green)">${fmt(c.resultado_ventas)}</td>
        </tr>`).join('') + '</tbody></table>';
    } else { ca.innerHTML = '<div class="empty"><div class="empty-icon">📢</div>Sin campañas activas</div>'; }

    document.getElementById('cmd-updated').textContent = 'Actualizado: ' + new Date().toLocaleTimeString('es-CO');
  } catch(e) { toast('Error cargando datos: ' + e.message, 'error'); }
}

// ─── PRODUCTOS ────────────────────────────────────────────────────────────────
async function loadProductos() {
  document.getElementById('prod-table').innerHTML = '<div class="loading"><div class="spinner"></div> Analizando SKUs...</div>';
  try {
    const d = await fetch('/api/animus/productos').then(r=>r.json());
    if(!d.skus || !d.skus.length) {
      document.getElementById('prod-table').innerHTML = '<div class="empty"><div class="empty-icon">💎</div>Sin datos de SKUs</div>';
      return;
    }
    document.getElementById('prod-table').innerHTML = `
      <table class="tbl">
        <thead><tr><th>SKU</th><th>Clase</th><th>Stock</th><th>Rotación/Mes</th><th>Cobertura</th><th>Revenue 30d</th><th>Shopify 30d</th><th>Precio</th><th>Estado</th></tr></thead>
        <tbody>` + d.skus.map(s => `<tr>
          <td><strong>${s.sku}</strong></td>
          <td><span class="badge-abc-${s.clase_abc.toLowerCase()}">${s.clase_abc}</span></td>
          <td>${fmtN(s.stock)}</td>
          <td>${s.rotacion_mes} uds</td>
          <td style="color:${s.meses_cobertura<=3?'var(--green)':s.meses_cobertura<=6?'var(--yellow)':'var(--red)'}">${s.meses_cobertura === 99 ? '∞' : s.meses_cobertura + ' meses'}</td>
          <td style="color:var(--gold)">${fmt(s.revenue_30d)}</td>
          <td>${s.shopify_uds_30d} uds</td>
          <td>$${Number(s.precio||0).toLocaleString()}</td>
          <td><span class="${s.estado==='ok'?'badge-ok':s.estado==='alerta'?'badge-warn':'badge-crit'}">${s.estado}</span></td>
        </tr>`).join('') + '</tbody></table>';
  } catch(e) { document.getElementById('prod-table').innerHTML = '<div class="empty">Error cargando productos</div>'; }
}

// ─── CLIENTES ─────────────────────────────────────────────────────────────────
async function loadClientes() {
  try {
    const d = await fetch('/api/animus/clientes').then(r=>r.json());
    // Top Shopify
    const ts = document.getElementById('top-shopify');
    ts.innerHTML = d.top_shopify && d.top_shopify.length
      ? `<table class="tbl"><thead><tr><th>Email</th><th>Pedidos</th><th>Revenue</th><th>Último</th></tr></thead><tbody>` +
        d.top_shopify.map(c=>`<tr><td>${c.email}</td><td>${c.pedidos}</td><td style="color:var(--gold)">${fmt(c.revenue)}</td><td>${(c.ultimo_pedido||'').slice(0,10)}</td></tr>`).join('') +
        '</tbody></table>'
      : '<div class="empty"><div class="empty-icon">🛍️</div>Sincroniza Shopify para ver clientes</div>';

    // GHL Pipeline
    const gp = document.getElementById('ghl-pipeline');
    gp.innerHTML = d.pipeline_ghl && d.pipeline_ghl.length
      ? `<table class="tbl"><thead><tr><th>Etapa</th><th>Contactos</th><th>Valor</th></tr></thead><tbody>` +
        d.pipeline_ghl.map(p=>`<tr><td>${p.etapa||'Sin etapa'}</td><td>${p.contactos}</td><td style="color:var(--blue)">${fmt(p.valor)}</td></tr>`).join('') +
        '</tbody></table>'
      : '<div class="empty"><div class="empty-icon">🎯</div>Conecta GHL para ver pipeline</div>';

    // Geo
    const gc = document.getElementById('geo-chart');
    if(d.geo && d.geo.length) {
      const maxR = Math.max(...d.geo.map(g=>g.revenue));
      gc.innerHTML = d.geo.map(g => {
        const pct = maxR > 0 ? Math.round(g.revenue/maxR*100) : 0;
        return `<div class="bar-row"><div class="bar-label">${g.ciudad}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"><span class="bar-val">${g.pedidos}p</span></div></div></div>`;
      }).join('');
    } else { gc.innerHTML = '<div class="empty">Sin datos geográficos</div>'; }

    // Dormidos
    document.getElementById('dormidos-panel').innerHTML = `
      <div style="font-size:48px;margin-bottom:8px">😴</div>
      <div style="font-size:32px;font-weight:700;color:var(--yellow)">${d.clientes_dormidos}</div>
      <div style="color:var(--text2);margin-top:8px">clientes sin comprar en 60+ días</div>
      <div style="margin-top:16px;font-size:12px;color:var(--text3)">Usa el Agente Reórdenes para identificar los más urgentes y activar campaña de reactivación.</div>`;
  } catch(e) { toast('Error clientes: '+e.message,'error'); }
}

// ─── INSTAGRAM ────────────────────────────────────────────────────────────────
async function loadInstagram() {
  document.getElementById('ig-section').innerHTML = '<div class="loading"><div class="spinner"></div> Cargando...</div>';
  try {
    const d = await fetch('/api/animus/instagram').then(r=>r.json());
    const s = d.stats || {};
    let html = `<div class="kpi-grid" style="grid-template-columns:repeat(5,1fr);margin-bottom:20px">
      <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Posts</div><div class="kpi-value">${s.total||0}</div></div>
      <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Avg Likes</div><div class="kpi-value">${Math.round(s.avg_likes||0)}</div></div>
      <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Avg Coment.</div><div class="kpi-value">${Math.round(s.avg_comentarios||0)}</div></div>
      <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Total Likes</div><div class="kpi-value">${fmtN(s.total_likes||0)}</div></div>
      <div class="kpi" style="--kpi-color:var(--pink)"><div class="kpi-label">Alcance Total</div><div class="kpi-value">${fmtN(s.total_alcance||0)}</div></div>
    </div>`;
    if(d.posts && d.posts.length) {
      html += `<div class="grid-2"><div class="card"><div class="card-title">📸 Posts Recientes</div>
        <table class="tbl"><thead><tr><th>Fecha</th><th>Tipo</th><th>Likes</th><th>Comentarios</th><th>Link</th></tr></thead><tbody>` +
        d.posts.slice(0,10).map(p=>`<tr>
          <td>${(p.publicado_en||'').slice(0,10)}</td>
          <td>${p.tipo||''}</td>
          <td style="color:var(--pink)">${fmtN(p.likes)}</td>
          <td>${fmtN(p.comentarios)}</td>
          <td>${p.url_permalink?`<a href="${p.url_permalink}" target="_blank" style="color:var(--gold)">Ver</a>`:'—'}</td>
        </tr>`).join('') + '</tbody></table></div>';
      html += `<div class="card"><div class="card-title">🏆 Top Posts por Engagement</div>
        <table class="tbl"><thead><tr><th>Post</th><th>Likes</th><th>Coment.</th><th>Guardados</th></tr></thead><tbody>` +
        (d.top_posts||[]).map(p=>`<tr>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(p.descripcion||'Sin descripción').slice(0,60)}...</td>
          <td style="color:var(--pink)">${fmtN(p.likes)}</td><td>${fmtN(p.comentarios)}</td><td>${fmtN(p.guardados)}</td>
        </tr>`).join('') + '</tbody></table></div></div>';
    } else {
      html += `<div class="empty" style="padding:60px"><div class="empty-icon">📸</div>
        <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:8px">Conecta Instagram para ver tus métricas</div>
        <div style="font-size:13px;margin-bottom:20px">Ve a Configuración y agrega tu Access Token de Meta Graph API</div>
        <button class="connect-btn" onclick="showSection('config')">⚙️ Ir a Configuración</button></div>`;
    }
    document.getElementById('ig-section').innerHTML = html;
  } catch(e) { document.getElementById('ig-section').innerHTML = '<div class="empty">Error cargando Instagram</div>'; }
}

// ─── AGENTES ──────────────────────────────────────────────────────────────────
async function runAgente(agente) {
  const card = document.getElementById('card-' + agente);
  const res  = document.getElementById('res-' + agente);
  const btn  = card.querySelector('.agent-btn');
  card.classList.add('running');
  btn.disabled = true; btn.textContent = '⏳ Analizando...';
  res.className = 'agent-result visible';
  res.innerHTML = '<div class="loading" style="padding:12px"><div class="spinner"></div> Ejecutando agente...</div>';
  try {
    const d = await fetch('/api/animus/agentes/' + agente, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.json());
    res.innerHTML = formatAgentResult(agente, d);
    toast('Agente ' + agente + ' completado ✓', 'success');
  } catch(e) {
    res.innerHTML = '<div style="color:var(--red)">Error: ' + e.message + '</div>';
  }
  card.classList.remove('running');
  btn.disabled = false;
  btn.textContent = '▶ ' + btn.textContent.replace('⏳ Analizando...','Ejecutar de nuevo');
  if(!btn.textContent.includes('▶')) btn.textContent = '▶ Ejecutar de nuevo';
}

function formatAgentResult(agente, d) {
  if(d.error) return `<div style="color:var(--red)">⚠️ ${d.error}</div>`;
  let html = '';
  if(d.titulo) html += `<div style="font-weight:700;color:var(--gold);margin-bottom:8px">${d.titulo}</div>`;
  if(d.resumen) html += `<div style="margin-bottom:10px;color:var(--text)">${d.resumen}</div>`;

  if(agente === 'estacionalidad' && d.alertas) {
    html += d.alertas.slice(0,8).map(a => `<div style="padding:8px;border-left:3px solid ${a.color||'var(--gold)'};margin-bottom:6px;background:rgba(255,255,255,.03);border-radius:0 6px 6px 0">
      <div style="font-weight:600;font-size:12px">${a.evento} · ${a.sku} · <span class="${a.estado==='ok'?'badge-ok':a.estado==='advertencia'?'badge-warn':'badge-crit'}">${a.estado}</span></div>
      <div style="font-size:11px;color:var(--text2);margin-top:3px">Stock: ${a.stock_actual} uds → Demanda proyectada: ${a.demanda_proyectada} uds · Déficit: ${a.deficit}</div>
      ${a.deadline_produccion?`<div style="font-size:11px;color:var(--yellow)">⚡ Arrancar producción antes del ${a.deadline_produccion}</div>`:''}
    </div>`).join('');
  } else if(agente === 'oportunidad' && d.recomendaciones) {
    html += d.recomendaciones.slice(0,5).map(r => `<div style="padding:8px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:6px">
      <div style="font-weight:600;font-size:12px;color:var(--gold)">${r.sku} — Score: ${'★'.repeat(r.score)}</div>
      <div style="font-size:11px;color:var(--text2)">Stock: ${r.stock} · Rotación: ${r.rotacion_mes}/mes · ${r.razones.join(' · ')}</div>
      <div style="font-size:11px;color:var(--text);margin-top:3px">${r.accion}</div>
    </div>`).join('');
  } else if(agente === 'roi' && d.campanas) {
    html += d.campanas.length
      ? d.campanas.slice(0,6).map(c=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="font-size:12px">${c.nombre}</span>
          <span style="font-size:12px;color:${c.roi_pct>=0?'var(--green)':'var(--red)'}">ROI ${c.roi_pct}%</span>
        </div>`).join('')
      : '<div style="font-size:12px;color:var(--text2)">Sin campañas con gasto registrado aún</div>';
  } else if(agente === 'tendencias' && d.tendencias_erp) {
    html += d.tendencias_erp.slice(0,6).map(t=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:12px">${t.sku}</span>
      <span style="font-size:12px;color:${t.cambio_pct>0?'var(--green)':'var(--red)'}">${t.cambio_pct>0?'▲':'▼'} ${Math.abs(t.cambio_pct)}%</span>
    </div>`).join('');
  } else if(agente === 'brief' && d.briefs) {
    html += d.briefs.map(b=>`<div style="padding:8px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:6px">
      <div style="font-weight:600;font-size:12px;color:var(--gold)">${b.sku}</div>
      <div style="font-size:11px;color:var(--text2);margin-top:3px">${b.brief}</div>
    </div>`).join('');
  } else if(agente === 'pricing' && d.propuestas) {
    html += d.propuestas.length
      ? d.propuestas.slice(0,5).map(p=>`<div style="padding:8px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px;color:var(--gold)">${p.sku} — ${p.max_descuento_pct}% OFF → $${Number(p.precio_promo).toLocaleString()}</div>
          <div style="font-size:11px;color:var(--text2)">${p.razon}</div>
        </div>`).join('')
      : '<div style="font-size:12px;color:var(--text2)">Sin SKUs que requieran promoción actualmente</div>';
  } else if(agente === 'reorden' && d.predicciones) {
    html += d.predicciones.length
      ? d.predicciones.slice(0,5).map(p=>`<div style="padding:8px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px">${p.email}</div>
          <div style="font-size:11px;color:var(--text2)">Próximo reorden: ${p.proximo_reorden_estimado} · Ticket prom: ${fmt(p.ticket_promedio)}</div>
          <div style="font-size:11px;color:var(--yellow)">⏱ ${p.urgencia}</div>
        </div>`).join('')
      : '<div style="font-size:12px;color:var(--text2)">Sincroniza Shopify para ver predicciones de reórdenes</div>';
  } else if(agente === 'canibal' && d.conflictos) {
    html += d.conflictos.length
      ? d.conflictos.map(c=>`<div style="padding:8px;background:rgba(239,68,68,.05);border-left:3px solid var(--red);border-radius:0 6px 6px 0;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px;color:var(--red)">${c.conflicto}: "${c.campana_a}" vs "${c.campana_b}"</div>
          <div style="font-size:11px;color:var(--text2);margin-top:3px">${c.recomendacion}</div>
        </div>`).join('')
      : '<div style="font-size:12px;color:var(--green)">✓ Sin conflictos detectados entre campañas activas</div>';
  } else if(agente === 'contenido_auto' && d.piezas) {
    html += d.piezas.map(p=>`<div style="padding:10px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:8px">
      <div style="font-weight:600;font-size:12px;color:var(--gold);margin-bottom:4px">${p.sku}</div>
      <div style="font-size:11px;color:var(--text2);white-space:pre-line">${p.caption_instagram.slice(0,200)}...</div>
    </div>`).join('');
  } else if(agente === 'alerta_stock' && d.alertas) {
    html += d.alertas.length
      ? d.alertas.map(a=>`<div style="padding:8px;border-left:3px solid ${a.nivel==='critico'?'var(--red)':'var(--yellow)'};background:rgba(255,255,255,.03);border-radius:0 6px 6px 0;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px">${a.sku} — <span class="${a.nivel==='critico'?'badge-crit':'badge-warn'}">${a.nivel}</span></div>
          <div style="font-size:11px;color:var(--text2)">${a.accion}</div>
        </div>`).join('')
      : '<div style="font-size:12px;color:var(--green)">✓ Todos los SKUs con cobertura suficiente</div>';
  } else {
    html += `<pre style="font-size:11px;white-space:pre-wrap;overflow:auto;max-height:200px">${JSON.stringify(d,null,2)}</pre>`;
  }
  return html;
}

// ─── GENERADOR DE CONTENIDO ───────────────────────────────────────────────────
async function generarContenido() {
  const sku = document.getElementById('st-sku').value.trim();
  const tipo = document.getElementById('st-tipo').value;
  const tono = document.getElementById('st-tono').value;
  const ctx  = document.getElementById('st-ctx').value.trim();
  if(!sku) { toast('Ingresa un SKU', 'error'); return; }
  document.getElementById('st-output').textContent = '⏳ Generando contenido...';
  document.getElementById('st-meta').textContent = '';
  try {
    const d = await fetch('/api/animus/contenido/generar', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({sku, tipo, tono, contexto: ctx})
    }).then(r=>r.json());
    if(d.error) { document.getElementById('st-output').textContent = 'Error: ' + d.error; return; }
    document.getElementById('st-output').textContent = d.contenido;
    document.getElementById('st-meta').innerHTML = `<span style="color:var(--gold)">✦ ${d.nombre_producto}</span> · Tipo: ${tipo} · Tono: ${tono} · Stock: ${d.stock_disponible} uds`;
    loadHistorial();
    toast('Contenido generado ✓','success');
  } catch(e) { document.getElementById('st-output').textContent = 'Error: ' + e.message; }
}

function copiarContenido() {
  const txt = document.getElementById('st-output').textContent;
  navigator.clipboard.writeText(txt).then(()=>toast('Copiado al portapapeles ✓','success'));
}

async function loadHistorial() {
  try {
    const d = await fetch('/api/animus/contenido/historial').then(r=>r.json());
    const el = document.getElementById('historial-list');
    el.innerHTML = d.length
      ? d.slice(0,6).map(h=>`<div style="padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="cargarContenidoId(${h.id})">
          <div style="font-weight:600;color:var(--text)">${h.sku} — ${h.tipo}</div>
          <div style="color:var(--text3);font-size:10px">${h.tono} · ${(h.creado_en||'').slice(0,16)}</div>
        </div>`).join('')
      : '<div style="color:var(--text3)">Sin generaciones previas</div>';
  } catch(e) {}
}

// ─── CONFIG ───────────────────────────────────────────────────────────────────
async function saveCfg(platform) {
  const statusEl = document.getElementById('cfg-' + platform + '-status');
  statusEl.textContent = 'Guardando...';
  let data = {};
  if(platform === 'shopify') {
    data = {shopify_shop: document.getElementById('cfg-shopify-shop').value.trim(), shopify_token: document.getElementById('cfg-shopify-token').value.trim()};
  } else if(platform === 'ghl') {
    data = {ghl_api_key: document.getElementById('cfg-ghl-key').value.trim(), ghl_location_id: document.getElementById('cfg-ghl-loc').value.trim()};
  } else if(platform === 'instagram') {
    data = {instagram_token: document.getElementById('cfg-ig-token').value.trim(), instagram_user_id: document.getElementById('cfg-ig-uid').value.trim()};
  }
  try {
    await fetch('/api/animus/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    statusEl.style.color='var(--green)'; statusEl.textContent = '✓ Guardado. Sincronizando...';
    const sr = await fetch('/api/animus/sync/' + platform, {method:'POST'}).then(r=>r.json());
    if(sr.error) { statusEl.style.color='var(--red)'; statusEl.textContent = '⚠ Error sync: ' + sr.error; }
    else { statusEl.textContent = `✓ Sincronizado: ${sr.synced} registros importados`; loadConfig(); }
  } catch(e) { statusEl.style.color='var(--red)'; statusEl.textContent = 'Error: ' + e.message; }
}

async function syncPlatform(platform) {
  toast('Sincronizando ' + platform + '...', '');
  try {
    const d = await fetch('/api/animus/sync/' + platform, {method:'POST'}).then(r=>r.json());
    if(d.error) toast('Error: ' + d.error, 'error');
    else { toast(`${platform} sincronizado: ${d.synced} registros ✓`, 'success'); loadInstagram(); }
  } catch(e) { toast('Error: '+e.message,'error'); }
}

async function loadConfig() {
  try {
    const d = await fetch('/api/animus/config').then(r=>r.json());
    const conn = d.connected || {};
    document.getElementById('conn-status').innerHTML = `
      <div style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg3);border-radius:8px">
          <span style="font-size:18px">🛍️</span>
          <div style="flex:1"><div style="font-weight:600;font-size:13px">Shopify</div><div style="font-size:11px;color:var(--text2)">${conn.shopify?'Conectado':'Sin configurar'}</div></div>
          <span style="color:${conn.shopify?'var(--green)':'var(--text3)'}">●</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg3);border-radius:8px">
          <span style="font-size:18px">🎯</span>
          <div style="flex:1"><div style="font-weight:600;font-size:13px">GoHighLevel</div><div style="font-size:11px;color:var(--text2)">${conn.ghl?'Conectado':'Sin configurar'}</div></div>
          <span style="color:${conn.ghl?'var(--green)':'var(--text3)'}">●</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg3);border-radius:8px">
          <span style="font-size:18px">📸</span>
          <div style="flex:1"><div style="font-weight:600;font-size:13px">Instagram</div><div style="font-size:11px;color:var(--text2)">${conn.instagram?'Conectado':'Sin configurar'}</div></div>
          <span style="color:${conn.instagram?'var(--green)':'var(--text3)'}">●</span>
        </div>
      </div>`;
  } catch(e) {}
}

// ─── INIT ─────────────────────────────────────────────────────────────────────
loadComando();
</script>
</body>
</html>"""
