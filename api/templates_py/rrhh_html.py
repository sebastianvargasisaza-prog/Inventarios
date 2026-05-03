# Auto-extraído de index.py — Fase A refactor
RRHH_HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RRHH — HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f0;color:#1C1917;font-size:14px;}
header{background:#fff;border-bottom:1px solid #e5e3e0;padding:0 24px;position:sticky;top:0;z-index:100;}
.header-top{display:flex;align-items:center;gap:12px;padding:12px 0 0;}
.header-top h1{font-size:17px;font-weight:700;color:#1C1917;flex:1;}
.header-top a{font-size:12px;color:#888;text-decoration:none;}
.header-top a:hover{color:#6d28d9;}
.user-chip{font-size:12px;background:#f0ede8;padding:4px 10px;border-radius:20px;color:#666;}
nav{display:flex;gap:0;overflow-x:auto;margin-top:4px;}
.tab{padding:11px 15px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;font-size:13px;color:#888;white-space:nowrap;font-weight:500;}
.tab:hover{color:#1C1917;}
.tab.active{color:#6d28d9;border-bottom-color:#6d28d9;font-weight:700;}
main{max-width:1150px;margin:0 auto;padding:24px 16px;}
.page{display:none;}.page.active{display:block;}
/* KPIs */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
@media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
.kpi{background:#fff;border-radius:12px;padding:18px 20px;border:1px solid #e8e5e0;border-left:4px solid #6d28d9;}
.kpi.green{border-left-color:#16a34a;}.kpi.amber{border-left-color:#d97706;}.kpi.red{border-left-color:#dc2626;}
.kpi-val{font-size:30px;font-weight:800;color:#1C1917;line-height:1;}
.kpi-lbl{font-size:11px;color:#888;margin-top:5px;text-transform:uppercase;letter-spacing:.4px;}
.kpi-sub{font-size:11px;color:#a8a29e;margin-top:2px;}
/* Cards */
.card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:20px;margin-bottom:18px;}
.card-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.card-hd h2{font-size:14px;font-weight:700;color:#1C1917;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px;}
@media(max-width:700px){.two-col{grid-template-columns:1fr;}}
/* Empleados grid */
.emp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;}
.emp-card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:18px;cursor:pointer;transition:all .2s;}
.emp-card:hover{border-color:#6d28d9;box-shadow:0 4px 16px rgba(109,40,217,.1);transform:translateY(-2px);}
.emp-avatar{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff;margin-bottom:12px;}
.emp-name{font-size:14px;font-weight:700;color:#1C1917;margin-bottom:2px;}
.emp-cargo{font-size:12px;color:#78716c;margin-bottom:8px;}
.emp-meta{display:flex;gap:6px;flex-wrap:wrap;}
/* Badges */
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;}
.badge-activo{background:#d1fae5;color:#065f46;}
.badge-inactivo{background:#fee2e2;color:#991b1b;}
.badge-esp{background:#ede9fe;color:#5b21b6;}
.badge-ani{background:#fef3c7;color:#92400e;}
.badge-hha{background:#dbeafe;color:#1e40af;}
.badge-indef{background:#f1f5f9;color:#475569;}
.badge-fijo{background:#fef9c3;color:#713f12;}
.badge-ps{background:#f0fdf4;color:#166534;}
/* Tables */
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f9f8f7;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
td{padding:9px 12px;border-bottom:1px solid #f5f4f2;vertical-align:middle;}
tr:hover td{background:#fafaf8;}
td input[type=number]{width:90px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;text-align:right;}
/* Buttons */
.btn{padding:8px 16px;border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;}
.btn-primary{background:#6d28d9;color:#fff;}.btn-primary:hover{background:#5b21b6;}
.btn-success{background:#16a34a;color:#fff;}.btn-success:hover{background:#15803d;}
.btn-outline{background:#fff;border:1.5px solid #6d28d9;color:#6d28d9;}
.btn-danger{background:#dc2626;color:#fff;}.btn-danger:hover{background:#b91c1c;}
.btn-ghost{background:none;border:1px solid #e0ddd8;color:#78716c;}
.btn-sm{padding:5px 10px;font-size:12px;}
/* Forms */
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.form-group{display:flex;flex-direction:column;gap:4px;}
.form-group label{font-size:12px;font-weight:600;color:#555;}
.form-group input,.form-group select,.form-group textarea{padding:8px 10px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;font-family:inherit;}
.form-group input:focus,.form-group select:focus{outline:none;border-color:#6d28d9;}
/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px;overflow-y:auto;}
.modal-overlay.open{display:flex;}
.modal{background:#fff;border-radius:14px;width:90%;max-width:680px;max-height:88vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.25);}
.modal-hd{padding:18px 22px;border-bottom:1px solid #f0ede8;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:#fff;z-index:1;}
.modal-hd h3{font-size:15px;font-weight:700;}
.modal-body{padding:22px;}
.close-btn{background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px 8px;border-radius:6px;}
.close-btn:hover{background:#f0ede8;color:#333;}
/* Nomina */
.nomina-summary{background:#f9f8f7;border:1px solid #e7e5e4;border-radius:10px;padding:16px;margin-top:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;}
.sum-item .sum-lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.4px;}
.sum-item .sum-val{font-size:18px;font-weight:700;color:#1C1917;margin-top:3px;}
.sum-item.purple .sum-val{color:#6d28d9;}
.sum-item.green .sum-val{color:#16a34a;}
.sum-item.red .sum-val{color:#dc2626;}
/* Alertas */
.alerta{padding:10px 14px;border-radius:8px;margin-bottom:8px;font-size:13px;display:flex;align-items:center;gap:8px;}
.alerta.warn{background:#fef9c3;color:#713f12;border:1px solid #fde68a;}
.alerta.danger{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
.alerta.info{background:#ede9fe;color:#4c1d95;border:1px solid #c4b5fd;}
/* Progress bar */
.prog-bar{background:#e7e5e4;border-radius:20px;height:8px;overflow:hidden;margin-top:4px;}
.prog-fill{height:100%;border-radius:20px;background:#6d28d9;transition:width .4s;}
.prog-fill.green{background:#16a34a;}.prog-fill.amber{background:#d97706;}.prog-fill.red{background:#dc2626;}
/* Rating inputs */
.rating-group{display:flex;align-items:center;gap:10px;}
.rating-group label{min-width:130px;font-size:13px;}
.rating-group input[type=range]{flex:1;accent-color:#6d28d9;}
.rating-group .rval{min-width:28px;text-align:right;font-weight:700;color:#6d28d9;}
/* SGSST */
.sgsst-cat{margin-bottom:20px;}
.sgsst-cat-hd{font-size:13px;font-weight:700;color:#1C1917;padding:10px 14px;background:#f5f4f0;border-radius:8px 8px 0 0;border:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.sgsst-item{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid #e7e5e4;border-top:none;background:#fff;}
.sgsst-item:last-child{border-radius:0 0 8px 8px;}
.sgsst-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.dot-cumplido{background:#16a34a;}.dot-pendiente{background:#d97706;}.dot-vencido{background:#dc2626;}
.empty-state{text-align:center;padding:40px;color:#a8a29e;font-size:13px;}
/* Eval score */
.eval-card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:18px;margin-bottom:12px;}
.score-bar-row{display:flex;align-items:center;gap:10px;margin-top:6px;}
.score-bar-row .lbl{min-width:110px;font-size:12px;color:#57534e;}
.score-bar-row .bar{flex:1;background:#e7e5e4;border-radius:20px;height:7px;overflow:hidden;}
.score-bar-row .fill{height:100%;border-radius:20px;background:#6d28d9;}
.score-bar-row .num{min-width:28px;text-align:right;font-size:12px;font-weight:700;}
.total-score{font-size:32px;font-weight:800;color:#6d28d9;}
/* Period selector */
.ctrl-bar{display:flex;gap:10px;align-items:center;margin-bottom:18px;flex-wrap:wrap;}
.ctrl-bar select,.ctrl-bar input{padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;}
.ctrl-bar select:focus{outline:none;border-color:#6d28d9;}
/* Distribution */
.dist-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #f5f4f2;}
.dist-row:last-child{border:none;}
.dist-lbl{min-width:130px;font-size:13px;font-weight:500;}
.dist-bar{flex:1;background:#e7e5e4;border-radius:10px;height:10px;overflow:hidden;}
.dist-fill{height:100%;border-radius:10px;background:#6d28d9;}
.dist-cnt{min-width:24px;text-align:right;font-size:13px;font-weight:700;color:#6d28d9;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8"/></svg>
      Recursos Humanos
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; empleados &middot; nómina &middot; SGSST &middot; <span style="color:#a8a29e">{usuario}</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<header>
  <nav>
    <button class="tab active" id="t-dash" onclick="goTo('dash',this)">&#128202; Dashboard</button>
    <button class="tab" id="t-notif" onclick="goTo('notif',this)">&#128276; Reportes Empleados <span id="notif-badge" style="display:none;background:#dc2626;color:#fff;border-radius:10px;padding:1px 7px;font-size:10px;font-weight:700;margin-left:4px;"></span></button>
    <button class="tab" id="t-emp" onclick="goTo('emp',this)">&#128100; Empleados</button>
    <button class="tab" id="t-eventos" onclick="goTo('eventos',this)">&#129496; Eventos &amp; Reportes</button>
    <button class="tab" id="t-llamados" onclick="goTo('llamados',this)">&#128226; Llamados de atenci&oacute;n</button>
    <button class="tab" id="t-compromisos" onclick="goTo('compromisos',this)">&#128221; Compromisos</button>
    <button class="tab" id="t-aus" onclick="goTo('aus',this)">&#128197; Ausencias</button>
    <button class="tab" id="t-cap" onclick="goTo('cap',this)">&#127891; Capacitaciones</button>
    <button class="tab" id="t-eva" onclick="goTo('eva',this)">&#11088; Evaluaciones</button>
    <button class="tab" id="t-sgsst" onclick="goTo('sgsst',this)">&#128737; SGSST</button>
  </nav>
</header>
<main>

<!-- ═══ DASHBOARD ═══ -->
<div id="dash" class="page active">
  <div class="kpi-grid" id="kpi-row">
    <div class="kpi"><div class="kpi-val" id="k-hc">—</div><div class="kpi-lbl">Empleados activos</div></div>
    <div class="kpi green"><div class="kpi-val" id="k-nom">—</div><div class="kpi-lbl">N&oacute;mina bruta / mes</div><div class="kpi-sub">Solo salarios base</div></div>
    <div class="kpi amber"><div class="kpi-val" id="k-aus">—</div><div class="kpi-lbl">Ausentismo este mes</div><div class="kpi-sub">% sobre d&iacute;as h&aacute;biles</div></div>
    <div class="kpi red"><div class="kpi-val" id="k-cap">—</div><div class="kpi-lbl">Capacitaciones pendientes</div></div>
  </div>
  <div class="two-col">
    <div class="card">
      <div class="card-hd"><h2>&#128680; Alertas</h2></div>
      <div id="alertas-list"><div class="empty-state">Cargando...</div></div>
    </div>
    <div class="card">
      <div class="card-hd"><h2>&#127970; Distribuci&oacute;n por empresa</h2></div>
      <div id="dist-empresa"></div>
      <div class="card-hd" style="margin-top:16px;"><h2>&#128204; Por &aacute;rea</h2></div>
      <div id="dist-area"></div>
    </div>
  </div>
</div>

<!-- ═══ REPORTES EMPLEADOS (notificaciones pendientes desde portal /reportar) ═══ -->
<div id="notif" class="page">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
    <div>
      <div style="font-size:1.4em;font-weight:700;color:#0f172a;">🔔 Reportes de empleados</div>
      <div style="font-size:13px;color:#64748b;">Reportes desde el portal público <code>/reportar</code> · permisos, salud, citas médicas, incapacidades</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <select id="notif-estado" onchange="cargarNotif()" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;">
        <option value="pendiente">Pendientes</option>
        <option value="">Todos los estados</option>
        <option value="aprobada">Aprobadas</option>
        <option value="rechazada">Rechazadas</option>
        <option value="vista">Vistas</option>
      </select>
      <button onclick="cargarNotif()" style="background:#0e7490;border:none;color:#fff;padding:8px 14px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;">↻</button>
    </div>
  </div>
  <div id="notif-content"><div class="empty">Cargando reportes...</div></div>
  <div style="background:#f0f9ff;border-left:4px solid #0e7490;padding:14px 18px;border-radius:8px;margin-top:18px;font-size:13px;color:#0c4a6e;">
    💡 <b>Comparte este link con los empleados:</b> <code style="background:#fff;padding:3px 8px;border-radius:4px;">eossuite.com/reportar</code> ·
    funciona en celular sin login (validan con cédula).
  </div>
</div>

<!-- ═══ EMPLEADOS ═══ -->
<div id="emp" class="page">
  <div class="card-hd" style="margin-bottom:16px;">
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="text" id="emp-search" placeholder="Buscar empleado..." style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;min-width:220px;" oninput="filterEmps()">
      <select id="emp-filter-empresa" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todas las empresas</option>
        <option>Espagiria</option><option>ÁNIMUS Lab</option><option>HHA Group</option>
      </select>
      <select id="emp-filter-estado" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todos</option><option>Activo</option><option>Inactivo</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="openEmpModal(null)">+ Nuevo</button>
  </div>
  <div id="emp-grid" class="emp-grid"></div>
  <div id="pg-emp"></div>
</div>

<!-- ═══ EVENTOS & REPORTES (incapacidad/accidente/licencia) ═══ -->
<div id="eventos" class="page">
  <div class="card-hd">
    <h2>&#129496; Eventos del personal · Incapacidad / Accidente / Licencia</h2>
    <div style="display:flex;gap:6px">
      <select id="ev-filtro-tipo" onchange="cargarEventosRH()" style="padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px">
        <option value="">Todos los tipos</option>
        <option value="incapacidad_comun">Incapacidad común</option>
        <option value="incapacidad_laboral">Incapacidad laboral</option>
        <option value="accidente_trabajo">Accidente trabajo</option>
        <option value="licencia_maternidad">Licencia maternidad</option>
        <option value="licencia_paternidad">Licencia paternidad</option>
        <option value="licencia_luto">Licencia luto</option>
        <option value="licencia_no_remunerada">Licencia no remunerada</option>
        <option value="vacaciones">Vacaciones</option>
        <option value="permiso_remunerado">Permiso remunerado</option>
      </select>
      <button class="btn btn-primary btn-sm" onclick="abrirModalEventoRH()">&#43; Registrar evento</button>
    </div>
  </div>
  <div id="eventos-lista"></div>
</div>

<!-- ═══ LLAMADOS DE ATENCIÓN ═══ -->
<div id="llamados" class="page">
  <div class="card-hd">
    <h2>&#128226; Llamados de atenci&oacute;n · Verbal · Escrito · Suspensi&oacute;n</h2>
    <button class="btn btn-primary btn-sm" onclick="abrirModalLlamado()">&#43; Registrar llamado</button>
  </div>
  <div id="llamados-lista"></div>
</div>

<!-- ═══ COMPROMISOS DE MEJORA / REINDUCCIONES ═══ -->
<div id="compromisos" class="page">
  <div class="card-hd">
    <h2>&#128221; Compromisos de mejora &amp; reinducciones</h2>
    <select id="comp-filtro" onchange="cargarCompromisos()" style="padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px">
      <option value="pendiente">Pendientes</option>
      <option value="en_progreso">En progreso</option>
      <option value="completado">Completados</option>
      <option value="">Todos</option>
    </select>
  </div>
  <div id="compromisos-lista"></div>
</div>

<!-- (Nómina movida a /tesoreria — 29-abr-2026) -->
<!-- ═══ AUSENCIAS ═══ -->
<div id="aus" class="page">
  <div class="ctrl-bar">
    <select id="aus-tipo" onchange="loadAusencias()">
      <option value="">Todos los tipos</option>
      <option>Vacaciones</option><option>Incapacidad</option>
      <option>Permiso</option><option>Licencia</option>
    </select>
    <select id="aus-estado" onchange="loadAusencias()">
      <option value="">Todos los estados</option>
      <option>Pendiente</option><option>Aprobada</option><option>Rechazada</option>
    </select>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openAusModal()">+ Registrar</button>
  </div>
  <div class="card" style="overflow-x:auto;">
    <table><thead><tr>
      <th>Empleado</th><th>Tipo</th><th>Desde</th><th>Hasta</th>
      <th>D&iacute;as</th><th>Estado</th><th>Observaciones</th><th>Acciones</th>
    </tr></thead>
    <tbody id="aus-body"></tbody>
    </table>
  </div>
</div>

<!-- ═══ CAPACITACIONES ═══ -->
<div id="cap" class="page">
  <div class="ctrl-bar">
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openCapModal()">+ Nueva Capacitaci&oacute;n</button>
  </div>
  <div id="cap-list"></div>
</div>

<!-- ═══ EVALUACIONES ═══ -->
<div id="eva" class="page">
  <div class="ctrl-bar">
    <label style="font-size:13px;font-weight:600;">Per&iacute;odo:</label>
    <select id="eva-periodo" onchange="loadEvaluaciones()">
      <option value="">Todos</option>
      <option value="2026-Q1">2026 — Q1</option><option value="2026-Q2">2026 — Q2</option>
      <option value="2026-Q3">2026 — Q3</option><option value="2026-Q4">2026 — Q4</option>
      <option value="2025-Q4">2025 — Q4</option>
    </select>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openEvaModal()">+ Nueva Evaluaci&oacute;n</button>
  </div>
  <div id="eva-grid"></div>
</div>

<!-- ═══ SGSST ═══ -->
<div id="sgsst" class="page">
  <div class="ctrl-bar">
    <div style="font-size:13px;color:#78716c;">Sistema de Gesti&oacute;n de Seguridad y Salud en el Trabajo &mdash; BPM Cosm&eacute;ticos</div>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openSgsstModal()">+ Agregar Requisito</button>
  </div>
  <div id="sgsst-body"></div>
</div>

</main>

<!-- MODAL EMPLEADO -->
<div class="modal-overlay" id="m-emp">
  <div class="modal">
    <div class="modal-hd">
      <h3 id="m-emp-title">Nuevo Empleado</h3>
      <button class="close-btn" onclick="closeModal('m-emp')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Nombre *</label><input id="f-nombre" type="text"></div>
        <div class="form-group"><label>Apellido *</label><input id="f-apellido" type="text"></div>
        <div class="form-group"><label>C&eacute;dula</label><input id="f-cedula" type="text"></div>
        <div class="form-group"><label>Cargo *</label><input id="f-cargo" type="text"></div>
        <div class="form-group"><label>&Aacute;rea</label>
          <select id="f-area">
            <option>Gerencia</option><option>Administraci&oacute;n</option><option>Producci&oacute;n</option>
            <option>Control de Calidad</option><option>Direcci&oacute;n T&eacute;cnica</option>
            <option>Log&iacute;stica</option><option>Bodega</option><option>Marketing</option>
            <option>Ventas</option><option>Servicios</option><option>Laboratorio</option>
            <option>Operaciones</option>
          </select>
        </div>
        <div class="form-group"><label>Empresa</label>
          <select id="f-empresa"><option>Espagiria</option><option>ÁNIMUS Lab</option><option>HHA Group</option></select>
        </div>
        <div class="form-group"><label>Tipo de contrato</label>
          <select id="f-contrato">
            <option>Indefinido</option><option>Fijo</option>
            <option>Prestaci&oacute;n de Servicios</option><option>Aprendizaje</option>
          </select>
        </div>
        <div class="form-group"><label>Fecha ingreso</label><input id="f-ingreso" type="date"></div>
        <div class="form-group"><label>Salario base (COP)</label><input id="f-salario" type="number" min="0" step="50000"></div>
        <div class="form-group"><label>Nivel de riesgo ARL (1-5)</label>
          <select id="f-riesgo"><option value="1">1 — M&iacute;nimo</option><option value="2">2 — Bajo</option><option value="3">3 — Medio</option><option value="4">4 — Alto</option><option value="5">5 — M&aacute;ximo</option></select>
        </div>
        <div class="form-group"><label>EPS</label><input id="f-eps" type="text" placeholder="Ej: Sura"></div>
        <div class="form-group"><label>AFP (Pens&iacute;on)</label><input id="f-afp" type="text" placeholder="Ej: Proteccion"></div>
        <div class="form-group"><label>ARL</label><input id="f-arl" type="text" placeholder="Ej: Sura"></div>
        <div class="form-group"><label>Caja de compensaci&oacute;n</label><input id="f-caja" type="text" placeholder="Ej: Comfenalco"></div>
        <div class="form-group"><label>Email</label><input id="f-email" type="email"></div>
        <div class="form-group"><label>Tel&eacute;fono</label><input id="f-tel" type="tel"></div>
        <div class="form-group"><label>Estado</label>
          <select id="f-estado"><option>Activo</option><option>Inactivo</option></select>
        </div>
      </div>
      <div style="margin-top:16px;padding:12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;">
        <div style="font-weight:700;color:#166534;margin-bottom:10px;font-size:13px;">&#127981; Datos Bancarios (para pago nómina)</div>
        <div class="form-grid">
          <div class="form-group"><label>Banco</label>
            <select id="f-banco">
              <option value="">— Sin registrar —</option>
              <option>BANCOLOMBIA</option><option>DAVIVIENDA</option><option>BANCO DE BOGOTA</option>
              <option>BBVA</option><option>AV VILLAS</option><option>BANCO CAJA SOCIAL</option>
              <option>NEQUI</option><option>DAVIPLATA</option><option>BANCO POPULAR</option>
              <option>SCOTIABANK COLPATRIA</option><option>GNB SUDAMERIS</option><option>Otro</option>
            </select>
          </div>
          <div class="form-group"><label>Tipo de cuenta</label>
            <select id="f-tipo-cta">
              <option value="">— Sin registrar —</option>
              <option>AHORROS</option><option>CORRIENTE</option><option>AHORROS DAMAS</option><option>NEQUI</option><option>DAVIPLATA</option>
            </select>
          </div>
          <div class="form-group"><label>N&uacute;mero de cuenta</label><input id="f-num-cta" type="text" placeholder="Ej: 06250043821"></div>
        </div>
      </div>
      <div class="form-group" style="margin-top:12px;"><label>Observaciones</label><textarea id="f-obs" rows="2" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-emp')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveEmp()">Guardar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL AUSENCIA -->
<div class="modal-overlay" id="m-aus">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Registrar Ausencia</h3>
      <button class="close-btn" onclick="closeModal('m-aus')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Empleado *</label><select id="a-emp"></select></div>
        <div class="form-group"><label>Tipo *</label>
          <select id="a-tipo"><option>Vacaciones</option><option>Incapacidad</option><option>Permiso</option><option>Licencia</option></select>
        </div>
        <div class="form-group"><label>Fecha inicio *</label><input id="a-inicio" type="date"></div>
        <div class="form-group"><label>Fecha fin *</label><input id="a-fin" type="date"></div>
        <div class="form-group"><label>D&iacute;as</label><input id="a-dias" type="number" min="1" value="1"></div>
      </div>
      <div class="form-group" style="margin-top:12px;"><label>Observaciones</label><textarea id="a-obs" rows="2" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-aus')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveAus()">Registrar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL CAPACITACION -->
<div class="modal-overlay" id="m-cap">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Nueva Capacitaci&oacute;n</h3>
      <button class="close-btn" onclick="closeModal('m-cap')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group" style="grid-column:span 2;"><label>Nombre *</label><input id="c-nombre" type="text"></div>
        <div class="form-group"><label>Tipo</label>
          <select id="c-tipo"><option>BPM</option><option>SGSST</option><option>T&eacute;cnica</option><option>Blanda</option><option>Regulatoria</option></select>
        </div>
        <div class="form-group"><label>Fecha</label><input id="c-fecha" type="date"></div>
        <div class="form-group"><label>Duraci&oacute;n (horas)</label><input id="c-horas" type="number" value="2" min="0.5" step="0.5"></div>
        <div class="form-group"><label>Instructor / Entidad</label><input id="c-instructor" type="text"></div>
      </div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-cap')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveCap()">Crear y asignar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL EVALUACION -->
<div class="modal-overlay" id="m-eva">
  <div class="modal" style="max-width:560px;">
    <div class="modal-hd">
      <h3>Nueva Evaluaci&oacute;n de Desempe&ntilde;o</h3>
      <button class="close-btn" onclick="closeModal('m-eva')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid" style="margin-bottom:16px;">
        <div class="form-group"><label>Empleado *</label><select id="e-emp"></select></div>
        <div class="form-group"><label>Per&iacute;odo *</label>
          <select id="e-per">
            <option value="2026-Q2">2026 — Q2</option><option value="2026-Q1">2026 — Q1</option>
            <option value="2025-Q4">2025 — Q4</option>
          </select>
        </div>
      </div>
      <p style="font-size:12px;color:#78716c;margin-bottom:14px;">Puntaje 1 (muy por debajo) a 5 (sobresaliente)</p>
      <div id="ev-criteria"></div>
      <div class="form-group" style="margin-top:14px;"><label>Comentarios</label><textarea id="e-comentarios" rows="3" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-eva')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveEva()">Publicar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL SGSST -->
<div class="modal-overlay" id="m-sgsst">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Agregar Requisito SGSST</h3>
      <button class="close-btn" onclick="closeModal('m-sgsst')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Categor&iacute;a</label>
          <select id="sg-cat">
            <option>Medicina del Trabajo</option><option>Higiene Industrial</option>
            <option>Seguridad</option><option>Emergencias</option>
            <option>Vigilancia Epidemiol&oacute;gica</option><option>Capacitaci&oacute;n SGSST</option>
          </select>
        </div>
        <div class="form-group"><label>Frecuencia</label>
          <select id="sg-freq"><option>Mensual</option><option>Trimestral</option><option>Semestral</option><option>Anual</option></select>
        </div>
        <div class="form-group" style="grid-column:span 2;"><label>Descripci&oacute;n *</label><input id="sg-desc" type="text"></div>
        <div class="form-group"><label>Responsable</label><input id="sg-resp" type="text"></div>
        <div class="form-group"><label>Pr&oacute;ximo vencimiento</label><input id="sg-prox" type="date"></div>
      </div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-sgsst')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveSgsst()">Agregar</button>
      </div>
    </div>
  </div>
</div>

<script>
// ── CSRF defense-in-depth · Sebastian 3-may-2026 ──────────────────
function _csrf() {
  var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
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

// ── Filtros + Paginacion (client-side) ────────────────────────────
var TBL_STATE = {
  emp:    {q: '', page: 1, size: 25, fields: ['codigo','nombre','apellido','cedula','cargo','area','empresa','estado']},
  evt:    {q: '', page: 1, size: 25, fields: ['empleado_nombre','tipo','estado','observaciones']},
  llam:   {q: '', page: 1, size: 25, fields: ['empleado_nombre','tipo','motivo','estado']},
  comp:   {q: '', page: 1, size: 25, fields: ['empleado_nombre','tipo','accion','estado']},
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
  if (info.total <= s.size && info.total < 26) {
    return '<div style="font-size:11px;color:#64748b;padding:6px 0;">' + info.total + ' filas</div>';
  }
  var html = '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;font-size:12px;color:#64748b;">';
  html += '<span>Pág ' + info.page + '/' + info.totalPages + ' · ' + info.total + '</span>';
  html += '<span style="flex:1"></span>';
  html += '<button data-act="prev" data-tbl="' + tabla + '"' +
          (info.page <= 1 ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid #cbd5e1;border-radius:5px;background:#fff;cursor:pointer">&larr;</button>';
  html += '<button data-act="next" data-tbl="' + tabla + '"' +
          (info.page >= info.totalPages ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid #cbd5e1;border-radius:5px;background:#fff;cursor:pointer">&rarr;</button>';
  html += '<select data-act="size" data-tbl="' + tabla + '" style="border:1px solid #cbd5e1;padding:4px 6px;border-radius:5px;font-size:12px;">';
  ['25','50','100','999'].forEach(function(o){
    var label = o === '999' ? 'Todas' : o;
    html += '<option value="' + o + '"' + (String(s.size)===o?' selected':'') + '>' + label + '</option>';
  });
  html += '</select></div>';
  return html;
}
var _PAG_REFRESH = {
  emp: function(){ if(window.renderEmpleados) renderEmpleados(); else if(window.cargarEmpleados) cargarEmpleados(); },
  evt: function(){ if(window.cargarEventos) cargarEventos(); },
  llam: function(){ if(window.cargarLlamados) cargarLlamados(); },
  comp: function(){ if(window.cargarCompromisos) cargarCompromisos(); },
};
function cambiarPag(tabla, delta){ TBL_STATE[tabla].page = Math.max(1, TBL_STATE[tabla].page + delta); if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function cambiarPagSize(tabla, valor){ TBL_STATE[tabla].size = parseInt(valor,10)||25; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function buscarTabla(tabla, valor){ TBL_STATE[tabla].q = valor||''; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
document.addEventListener('click', function(ev){
  var btn = ev.target.closest('[data-act][data-tbl]');
  if (!btn || btn.tagName === 'SELECT') return;
  var tbl = btn.dataset.tbl, act = btn.dataset.act;
  if (act === 'prev') cambiarPag(tbl, -1);
  else if (act === 'next') cambiarPag(tbl, 1);
});
document.addEventListener('change', function(ev){
  var sel = ev.target.closest('select[data-act="size"][data-tbl]');
  if (!sel) return;
  cambiarPagSize(sel.dataset.tbl, sel.value);
});

// ─── state ───────────────────────────────────────────
var USUARIO = "{usuario}";
var allEmps = [];
var currentEmpId = null;
var nominaData = [];

var CRITERIA = [
  {key:'calidad',   label:'Calidad del trabajo'},
  {key:'asistencia',label:'Puntualidad / Asistencia'},
  {key:'actitud',   label:'Actitud y trabajo en equipo'},
  {key:'conocimiento',label:'Conocimiento t\u00e9cnico'},
  {key:'productividad',label:'Productividad'}
];

// ─── navigation ──────────────────────────────────────
function goTo(id, btn) {
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  if (id==='dash') loadDashboard();
  else if (id==='emp') loadEmpleados();
  else if (id==='notif') cargarNotif();
  else if (id==='aus') loadAusencias();
  else if (id==='cap') loadCapacitaciones();
  else if (id==='eva') loadEvaluaciones();
  else if (id==='sgsst') loadSgsst();
  else if (id==='eventos') cargarEventosRH();
  else if (id==='llamados') cargarLlamadosAtencion();
  else if (id==='compromisos') cargarCompromisos();
}

// ════════════════════════════════════════════════════════════════
// REPORTES EMPLEADOS (desde portal publico /reportar)
// ════════════════════════════════════════════════════════════════
function tipoIcon(t) {
  return ({permiso:'🗓️', cita_medica:'🏥', salud:'💊', enfermedad:'🤒', licencia:'📄', otro:'📝'})[t] || '📋';
}
function tipoColor(t) {
  return ({permiso:'#3b82f6', cita_medica:'#8b5cf6', salud:'#ec4899', enfermedad:'#dc2626', licencia:'#0e7490', otro:'#64748b'})[t] || '#64748b';
}
async function cargarNotifBadge() {
  try {
    var r = await fetch('/api/bienestar/notificaciones?estado=pendiente');
    var d = await r.json();
    var n = (d.notificaciones || []).length;
    var b = document.getElementById('notif-badge');
    if (n > 0) { b.textContent = n; b.style.display = 'inline-block'; }
    else b.style.display = 'none';
  } catch(e){}
}
async function cargarNotif() {
  var estado = document.getElementById('notif-estado').value;
  var url = '/api/bienestar/notificaciones' + (estado ? '?estado=' + estado : '');
  try {
    var r = await fetch(url);
    var d = await r.json();
    var c = document.getElementById('notif-content');
    var lista = d.notificaciones || [];
    if (!lista.length) {
      c.innerHTML = '<div class="empty">Sin reportes ' + (estado ? 'con estado "' + estado + '"' : '') + '</div>';
      cargarNotifBadge();
      return;
    }
    c.innerHTML = lista.map(function(n){
      var col = tipoColor(n.tipo);
      var fechas = '';
      if (n.fecha_inicio || n.fecha_fin) {
        fechas = '<div style="font-size:11px;color:#64748b;margin-top:4px;">' +
          (n.fecha_inicio ? '<b>Desde:</b> ' + n.fecha_inicio + ' ' : '') +
          (n.fecha_fin ? '<b>Hasta:</b> ' + n.fecha_fin : '') + '</div>';
      }
      var adj = n.adjunto_url ? '<a href="' + n.adjunto_url + '" target="_blank" style="display:inline-block;margin-top:6px;color:#0e7490;font-size:12px;">📎 Ver evidencia</a>' : '';
      var btns = '';
      if (n.estado === 'pendiente') {
        btns = '<div style="margin-top:10px;display:flex;gap:6px;">' +
          '<button onclick="resolverNotif(' + n.id + ',\'aprobada\')" style="background:#10b981;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">✓ Aprobar</button>' +
          '<button onclick="resolverNotif(' + n.id + ',\'rechazada\')" style="background:#dc2626;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">✗ Rechazar</button>' +
          '<button onclick="resolverNotif(' + n.id + ',\'vista\')" style="background:#64748b;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">👁 Marcar vista</button>' +
          '</div>';
      }
      var estadoCol = ({pendiente:'#f59e0b', aprobada:'#10b981', rechazada:'#dc2626', vista:'#64748b'})[n.estado] || '#64748b';
      return '<div style="background:#fff;border:1.5px solid #e2e8f0;border-left:5px solid ' + col + ';border-radius:10px;padding:16px 18px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.04);">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">' +
          '<div>' +
            '<div style="font-weight:700;font-size:15px;color:#0f172a;">' + tipoIcon(n.tipo) + ' ' + (n.asunto||'') + '</div>' +
            '<div style="font-size:12px;color:#475569;margin-top:3px;"><b>' + (n.empleado_nombre||n.empleado_username) + '</b> · ' +
              '<span style="background:' + col + '22;color:' + col + ';padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">' + n.tipo + '</span></div>' +
            fechas +
            (n.descripcion ? '<div style="font-size:13px;color:#334155;margin-top:8px;background:#f8fafc;padding:10px 12px;border-radius:6px;">' + n.descripcion + '</div>' : '') +
            adj +
          '</div>' +
          '<div style="text-align:right;">' +
            '<span style="background:' + estadoCol + ';color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:700;text-transform:uppercase;">' + n.estado + '</span>' +
            '<div style="font-size:10px;color:#94a3b8;margin-top:6px;">' + (n.creado_en||'').substring(0,16) + '</div>' +
          '</div>' +
        '</div>' +
        btns +
        (n.comentario_jefe ? '<div style="margin-top:8px;padding:8px 12px;background:#fef9c3;border-radius:6px;font-size:12px;color:#713f12;"><b>Resp. RH:</b> ' + n.comentario_jefe + '</div>' : '') +
        '</div>';
    }).join('');
    cargarNotifBadge();
  } catch(e) {
    document.getElementById('notif-content').innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
  }
}
async function resolverNotif(id, estado) {
  var comentario = '';
  if (estado === 'rechazada') {
    comentario = prompt('Motivo del rechazo (opcional):') || '';
  } else if (estado === 'aprobada') {
    comentario = prompt('Comentario para el empleado (opcional):') || '';
  }
  try {
    var headers = {'Content-Type': 'application/json'};
    var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (m) headers['X-CSRF-Token'] = decodeURIComponent(m[1]);
    var r = await fetch('/api/bienestar/notificaciones/' + id + '/resolver', {
      method: 'POST', headers: headers, credentials: 'same-origin',
      body: JSON.stringify({estado: estado, comentario_jefe: comentario}),
    });
    var d = await r.json();
    if (d.ok) cargarNotif();
    else alert('Error: ' + (d.error || '?'));
  } catch(e) { alert('Error red: ' + e.message); }
}
// Auto-cargar badge al entrar a /rrhh
cargarNotifBadge();
setInterval(cargarNotifBadge, 60000);  // refresh badge cada 1 min

// ═══ EVENTOS / REPORTES ═════════════════════════════════════════════
async function cargarEventosRH(){
  var lista = document.getElementById('eventos-lista');
  if(!lista) return;
  lista.innerHTML = '<div style="text-align:center;color:#888;padding:20px">Cargando...</div>';
  var tipo = document.getElementById('ev-filtro-tipo').value;
  try {
    var qs = tipo ? '?tipo='+encodeURIComponent(tipo) : '';
    var r = await fetch('/api/rrhh/eventos'+qs);
    var d = await r.json();
    var items = d.eventos || [];
    if(!items.length){ lista.innerHTML = '<div style="text-align:center;color:#a8a29e;padding:40px">Sin eventos</div>'; return; }
    var tipoColors = {incapacidad_comun:'#d97706',incapacidad_laboral:'#dc2626',accidente_trabajo:'#dc2626',licencia_maternidad:'#7c3aed',licencia_paternidad:'#7c3aed',licencia_luto:'#1e293b',licencia_no_remunerada:'#64748b',vacaciones:'#16a34a',permiso_remunerado:'#16a34a',llamado_atencion_verbal:'#d97706',llamado_atencion_escrito:'#dc2626',suspension:'#7f1d1d'};
    lista.innerHTML = '<table><thead><tr>'+
      '<th>Empleado</th><th>Tipo</th><th>Fechas</th><th>Días</th><th>Pago empleador</th><th>Pago EPS</th><th>Pago ARL</th><th>Estado</th><th></th>'+
      '</tr></thead><tbody>'+
      items.map(function(e){
        var col = tipoColors[e.tipo]||'#64748b';
        var fechas = (e.fecha_inicio||'') + (e.fecha_fin?' → '+e.fecha_fin:'');
        return '<tr>'+
          '<td><b>#'+e.empleado_id+'</b></td>'+
          '<td><span style="background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:8px;font-size:11px;font-weight:700">'+e.tipo+'</span></td>'+
          '<td style="font-size:12px">'+fechas+'</td>'+
          '<td style="text-align:center;font-weight:700">'+(e.dias||0)+'</td>'+
          '<td style="text-align:right;font-family:monospace">'+(e.pago_empleador?'$'+Math.round(e.pago_empleador).toLocaleString('es-CO'):'—')+'</td>'+
          '<td style="text-align:right;font-family:monospace;color:#16a34a">'+(e.pago_eps?'$'+Math.round(e.pago_eps).toLocaleString('es-CO'):'—')+'</td>'+
          '<td style="text-align:right;font-family:monospace;color:#7c3aed">'+(e.pago_arl?'$'+Math.round(e.pago_arl).toLocaleString('es-CO'):'—')+'</td>'+
          '<td><span class="badge badge-'+(e.estado==='aprobada'?'activo':e.estado==='cerrada'?'indef':'inactivo')+'">'+e.estado+'</span></td>'+
          '<td>'+(e.estado==='registrada'?'<button class="btn btn-success btn-sm" onclick="aprobarEvento('+e.id+')">Aprobar</button>':'')+'</td>'+
          '</tr>';
      }).join('')+'</tbody></table>';
  } catch(e){ lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
}

function abrirModalEventoRH(){
  var html = '<div id="evt-modal" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px">'+
    '<div style="background:#fff;border-radius:14px;padding:24px;width:560px;max-width:100%;max-height:90vh;overflow-y:auto">'+
      '<h3 style="margin:0 0 14px">Registrar evento</h3>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
        '<div><label style="font-size:11px;color:#555">Empleado ID</label><input id="evt-emp" type="number" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
        '<div><label style="font-size:11px;color:#555">Tipo</label><select id="evt-tipo" onchange="evtRecalcular()" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px">'+
          '<option value="incapacidad_comun">Incapacidad común</option>'+
          '<option value="incapacidad_laboral">Incapacidad laboral</option>'+
          '<option value="accidente_trabajo">Accidente trabajo</option>'+
          '<option value="licencia_maternidad">Licencia maternidad</option>'+
          '<option value="licencia_paternidad">Licencia paternidad</option>'+
          '<option value="licencia_luto">Licencia luto</option>'+
          '<option value="licencia_no_remunerada">Licencia no remunerada</option>'+
          '<option value="vacaciones">Vacaciones</option>'+
          '<option value="permiso_remunerado">Permiso remunerado</option>'+
        '</select></div>'+
        '<div><label style="font-size:11px;color:#555">Fecha inicio</label><input id="evt-ini" type="date" onchange="evtRecalcular()" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
        '<div><label style="font-size:11px;color:#555">Fecha fin</label><input id="evt-fin" type="date" onchange="evtRecalcular()" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
        '<div><label style="font-size:11px;color:#555">Diagnóstico</label><input id="evt-diag" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px" placeholder="Ej. Gripa común"></div>'+
        '<div><label style="font-size:11px;color:#555">CIE-10</label><input id="evt-cie10" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px" placeholder="J00"></div>'+
        '<div><label style="font-size:11px;color:#555">Entidad emisora</label><input id="evt-entidad" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px" placeholder="Sura, Sanitas, ARL..."></div>'+
        '<div><label style="font-size:11px;color:#555">URL documento</label><input id="evt-doc" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
      '</div>'+
      '<div style="margin-top:10px"><label style="font-size:11px;color:#555">Descripción</label><textarea id="evt-desc" rows="2" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-family:inherit"></textarea></div>'+
      '<div id="evt-preview" style="margin-top:14px;background:#f9f8f7;border:1px solid #e7e5e4;border-radius:8px;padding:12px;font-size:12px;color:#475569;display:none"></div>'+
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">'+
        '<button class="btn btn-ghost btn-sm" onclick="document.getElementById(&quot;evt-modal&quot;).remove()">Cancelar</button>'+
        '<button class="btn btn-primary btn-sm" onclick="guardarEventoRH()">Guardar</button>'+
      '</div>'+
    '</div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
}

async function evtRecalcular(){
  var emp = parseInt(document.getElementById('evt-emp').value||0);
  if(!emp) return;
  var tipo = document.getElementById('evt-tipo').value;
  var ini = document.getElementById('evt-ini').value;
  var fin = document.getElementById('evt-fin').value;
  if(!ini || !fin) return;
  var dias = Math.floor((new Date(fin) - new Date(ini)) / 86400000) + 1;
  // Buscar salario del empleado
  var er = await fetch('/api/rrhh/empleados');
  var ed = await er.json();
  var emp_obj = (ed.empleados||[]).find(function(x){return x.id===emp});
  if(!emp_obj){ document.getElementById('evt-preview').style.display='none'; return; }
  var r = await fetch('/api/rrhh/calcular-pago-evento', _fetchOpts('POST', {salario_mensual: emp_obj.salario_base, tipo: tipo, dias: dias}));
  var d = await r.json();
  var html = '<b>📊 Cálculo legal automático ('+dias+' días)</b><br>';
  (d.detalle||[]).forEach(function(x){
    html += '<div style="margin-top:4px">• '+x.rango+': <b style="color:'+(x.pagador==='EMPLEADOR'?'#dc2626':x.pagador==='EPS'?'#16a34a':'#7c3aed')+'">'+x.pagador+'</b> ('+x.pct+'%) — '+x.dias+' días = $'+Math.round(x.monto).toLocaleString('es-CO')+'</div>';
  });
  html += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #e7e5e4">Total: <b>$'+Math.round(d.total||0).toLocaleString('es-CO')+'</b> · Descuento nómina: $'+Math.round(d.descuento_nomina||0).toLocaleString('es-CO')+'</div>';
  var pr = document.getElementById('evt-preview');
  pr.innerHTML = html; pr.style.display = 'block';
}

async function guardarEventoRH(){
  var body = {
    empleado_id: parseInt(document.getElementById('evt-emp').value||0),
    tipo: document.getElementById('evt-tipo').value,
    fecha_inicio: document.getElementById('evt-ini').value,
    fecha_fin: document.getElementById('evt-fin').value,
    diagnostico: document.getElementById('evt-diag').value,
    cie10: document.getElementById('evt-cie10').value,
    entidad_emisora: document.getElementById('evt-entidad').value,
    documento_url: document.getElementById('evt-doc').value,
    descripcion: document.getElementById('evt-desc').value,
  };
  var r = await fetch('/api/rrhh/eventos', _fetchOpts('POST', body));
  var d = await r.json();
  if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
  document.getElementById('evt-modal').remove();
  cargarEventosRH();
}

async function aprobarEvento(eid){
  if(!confirm('Aprobar este evento?')) return;
  var r = await fetch('/api/rrhh/eventos/'+eid+'/aprobar', _fetchOpts('POST'));
  if(r.ok) cargarEventosRH();
  else alert('Error');
}

// ═══ LLAMADOS DE ATENCIÓN ═══════════════════════════════════════════
async function cargarLlamadosAtencion(){
  var lista = document.getElementById('llamados-lista');
  lista.innerHTML = '<div style="text-align:center;color:#888;padding:20px">Cargando...</div>';
  try {
    var r = await fetch('/api/rrhh/llamados-atencion');
    var d = await r.json();
    var items = d.llamados || [];
    if(!items.length){ lista.innerHTML = '<div style="text-align:center;color:#a8a29e;padding:40px">Sin llamados de atención</div>'; return; }
    lista.innerHTML = '<table><thead><tr><th>Empleado</th><th>Severidad</th><th>Motivo</th><th>Jefe</th><th>Área</th><th>Fecha</th><th>Estado</th></tr></thead><tbody>'+
      items.map(function(l){
        var sevColor = l.severidad==='suspension'?'#7f1d1d':l.severidad==='escrito'?'#dc2626':'#d97706';
        return '<tr>'+
          '<td><b>#'+l.empleado_id+'</b></td>'+
          '<td><span style="background:'+sevColor+'22;color:'+sevColor+';padding:2px 8px;border-radius:8px;font-size:11px;font-weight:700">'+(l.severidad||'').toUpperCase()+'</span></td>'+
          '<td>'+(l.motivo||'')+'</td>'+
          '<td style="font-size:12px">'+(l.jefe_nombre||'')+'</td>'+
          '<td style="font-size:12px">'+(l.area||'')+'</td>'+
          '<td style="font-size:12px">'+(l.fecha_inicio||'')+'</td>'+
          '<td><span class="badge badge-indef">'+l.estado+'</span></td>'+
          '</tr>';
      }).join('')+'</tbody></table>';
  } catch(e){ lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
}

function abrirModalLlamado(){
  var html = '<div id="lla-modal" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px">'+
    '<div style="background:#fff;border-radius:14px;padding:24px;width:520px;max-width:100%;max-height:90vh;overflow-y:auto">'+
      '<h3 style="margin:0 0 14px">📢 Registrar llamado de atención</h3>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
        '<div><label style="font-size:11px;color:#555">Empleado ID</label><input id="lla-emp" type="number" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
        '<div><label style="font-size:11px;color:#555">Severidad</label><select id="lla-sev" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px">'+
          '<option value="verbal">Verbal</option><option value="escrito">Escrito</option><option value="suspension">Suspensión</option>'+
        '</select></div>'+
        '<div><label style="font-size:11px;color:#555">Área</label><input id="lla-area" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px" placeholder="Planta, Marketing..."></div>'+
        '<div><label style="font-size:11px;color:#555">Fecha</label><input id="lla-fecha" type="date" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
      '</div>'+
      '<div style="margin-top:10px"><label style="font-size:11px;color:#555">Motivo *</label><input id="lla-motivo" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px" placeholder="Llegó tarde 3 veces / Envasó mal el lote..."></div>'+
      '<div style="margin-top:10px"><label style="font-size:11px;color:#555">Descripción detallada</label><textarea id="lla-desc" rows="2" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-family:inherit"></textarea></div>'+
      '<div style="margin-top:10px"><label style="font-size:11px;color:#555">Plan de mejora (genera compromiso ligado)</label><textarea id="lla-plan" rows="2" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-family:inherit" placeholder="Ej: Reinducción de envasado, capacitación específica..."></textarea></div>'+
      '<div style="margin-top:10px"><label style="font-size:11px;color:#555">Fecha objetivo cumplimiento</label><input id="lla-obj" type="date" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px"></div>'+
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">'+
        '<button class="btn btn-ghost btn-sm" onclick="document.getElementById(&quot;lla-modal&quot;).remove()">Cancelar</button>'+
        '<button class="btn btn-primary btn-sm" onclick="guardarLlamado()">Guardar</button>'+
      '</div>'+
    '</div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
}

async function guardarLlamado(){
  var body = {
    empleado_id: parseInt(document.getElementById('lla-emp').value||0),
    severidad: document.getElementById('lla-sev').value,
    area: document.getElementById('lla-area').value,
    fecha: document.getElementById('lla-fecha').value,
    motivo: document.getElementById('lla-motivo').value,
    descripcion: document.getElementById('lla-desc').value,
    plan_mejora: document.getElementById('lla-plan').value,
    fecha_objetivo: document.getElementById('lla-obj').value,
  };
  if(!body.empleado_id || !body.motivo){ alert('Empleado y motivo requeridos'); return; }
  var r = await fetch('/api/rrhh/llamados-atencion', _fetchOpts('POST', body));
  var d = await r.json();
  if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
  document.getElementById('lla-modal').remove();
  alert('Llamado registrado'+(d.compromiso_id?' + compromiso #'+d.compromiso_id:''));
  cargarLlamadosAtencion();
}

// ═══ COMPROMISOS DE MEJORA ═══════════════════════════════════════════
async function cargarCompromisos(){
  var lista = document.getElementById('compromisos-lista');
  if(!lista) return;
  lista.innerHTML = '<div style="text-align:center;color:#888;padding:20px">Cargando...</div>';
  var estado = document.getElementById('comp-filtro').value;
  try {
    var qs = estado ? '?estado='+estado : '';
    var r = await fetch('/api/rrhh/compromisos-mejora'+qs);
    var d = await r.json();
    var items = d.compromisos || [];
    if(!items.length){ lista.innerHTML = '<div style="text-align:center;color:#a8a29e;padding:40px">Sin compromisos en este estado</div>'; return; }
    lista.innerHTML = items.map(function(c){
      var estCol = c.estado==='completado'?'#16a34a':c.estado==='vencido'?'#dc2626':c.estado==='en_progreso'?'#d97706':'#64748b';
      return '<div style="background:#fff;border:1px solid #e8e5e0;border-left:4px solid '+estCol+';border-radius:10px;padding:14px 18px;margin-bottom:10px">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">'+
          '<div><b style="font-size:14px">'+(c.titulo||'')+'</b> <span style="background:#f3f4f6;color:#475569;font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;margin-left:8px">'+c.tipo+'</span></div>'+
          '<span style="background:'+estCol+'22;color:'+estCol+';padding:2px 10px;border-radius:8px;font-size:11px;font-weight:700;text-transform:uppercase">'+c.estado+'</span>'+
        '</div>'+
        '<div style="font-size:12px;color:#475569;margin-top:4px">Empleado #'+c.empleado_id+' · Jefe: '+(c.jefe_responsable||'-')+' · Objetivo: '+(c.fecha_objetivo||'-')+'</div>'+
        (c.descripcion?'<div style="font-size:13px;color:#1c1917;margin-top:6px">'+c.descripcion+'</div>':'')+
        (c.plan_accion?'<div style="font-size:12px;color:#475569;margin-top:6px;font-style:italic">📋 Plan: '+c.plan_accion+'</div>':'')+
        (c.estado==='pendiente'||c.estado==='en_progreso' ? '<button class="btn btn-success btn-sm" style="margin-top:8px" onclick="completarCompromiso('+c.id+')">✓ Marcar completado</button>' : '')+
      '</div>';
    }).join('');
  } catch(e){ lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
}

async function completarCompromiso(cid){
  var ev = prompt('URL de evidencia (opcional):', '') || '';
  var r = await fetch('/api/rrhh/compromisos-mejora/'+cid+'/completar', _fetchOpts('POST', {evidencia_url: ev}));
  if(r.ok) cargarCompromisos();
  else alert('Error');
}

// ─── utils ───────────────────────────────────────────
function fmt(n){return '$'+Number(n||0).toLocaleString('es-CO');}
function fmtDate(s){return s?(String(s).slice(0,10)):'—';}
function closeModal(id){document.getElementById(id).classList.remove('open');}
function openModal(id){document.getElementById(id).classList.add('open');}

function avatarColor(name) {
  var colors=['#6d28d9','#0e7490','#16a34a','#d97706','#dc2626','#7c3aed','#0369a1','#065f46'];
  var h=0; for(var i=0;i<name.length;i++) h=(h<<5)-h+name.charCodeAt(i);
  return colors[Math.abs(h)%colors.length];
}

function badgeEmpresa(e) {
  var m={'Espagiria':'badge-esp','ÁNIMUS Lab':'badge-ani','HHA Group':'badge-hha'};
  return '<span class="badge '+(m[e]||'badge-indef')+'">'+e+'</span>';
}

function badgeContrato(t) {
  var m={'Indefinido':'badge-indef','Fijo':'badge-fijo','Prestaci\u00f3n de Servicios':'badge-ps','Aprendizaje':'badge-ps'};
  return '<span class="badge '+(m[t]||'badge-indef')+'">'+t+'</span>';
}

// ─── DASHBOARD ───────────────────────────────────────
async function loadDashboard() {
  try {
    var d = await fetch('/api/rrhh/dashboard').then(function(r){return r.json();});
    document.getElementById('k-hc').textContent = d.headcount||0;
    document.getElementById('k-nom').textContent = fmt(d.nomina_bruta);
    document.getElementById('k-aus').textContent = (d.ausentismo_pct||0)+'%';
    document.getElementById('k-cap').textContent = d.caps_pendientes||0;

    var al = document.getElementById('alertas-list');
    if (!d.alertas || d.alertas.length===0) {
      al.innerHTML = '<div class="alerta info">&#10003; Sin alertas cr\u00edticas por el momento.</div>';
    } else {
      al.innerHTML = d.alertas.map(function(a){
        return '<div class="alerta '+(a.tipo||'info')+'">&#9679; '+a.msg+'</div>';
      }).join('');
    }

    var maxE = Math.max.apply(null,(d.por_empresa||[]).map(function(x){return x.count;}),1);
    document.getElementById('dist-empresa').innerHTML = (d.por_empresa||[]).map(function(x){
      var pct=Math.round(x.count/maxE*100);
      return '<div class="dist-row"><span class="dist-lbl">'+x.empresa+'</span><div class="dist-bar"><div class="dist-fill" style="width:'+pct+'%"></div></div><span class="dist-cnt">'+x.count+'</span></div>';
    }).join('');

    var maxA = Math.max.apply(null,(d.por_area||[]).map(function(x){return x.count;}),1);
    document.getElementById('dist-area').innerHTML = (d.por_area||[]).map(function(x){
      var pct=Math.round(x.count/maxA*100);
      return '<div class="dist-row"><span class="dist-lbl">'+x.area+'</span><div class="dist-bar"><div class="dist-fill" style="width:'+pct+'%"></div></div><span class="dist-cnt">'+x.count+'</span></div>';
    }).join('');
  } catch(e){console.error(e);}
}

// ─── EMPLEADOS ────────────────────────────────────────
async function loadEmpleados() {
  try {
    allEmps = await fetch('/api/rrhh/empleados').then(function(r){return r.json();});
    renderEmpleados(allEmps);
  } catch(e){console.error(e);}
}

function renderEmpleados(list) {
  var g = document.getElementById('emp-grid');
  // Aplicar paginacion sobre la lista ya filtrada por filterEmps()
  var s = TBL_STATE.emp;
  var info = _paginar(list || [], s.page, s.size);
  s.page = info.page;
  var pgEl = document.getElementById('pg-emp');
  if (!info.items.length){
    g.innerHTML = '<div class="empty-state">' + (s.q ? 'Sin coincidencias' : 'Sin empleados registrados.') + '</div>';
    if(pgEl) pgEl.innerHTML = '';
    return;
  }
  if(pgEl) pgEl.innerHTML = _renderPag('emp', info);
  g.innerHTML = info.items.map(function(e){
    var initials = (e.nombre||'?').charAt(0)+(e.apellido||'').charAt(0);
    var color = avatarColor(e.nombre+e.apellido);
    return '<div class="emp-card">' +
      '<div class="emp-avatar" style="background:'+color+';">'+initials+'</div>' +
      '<div class="emp-name">'+e.nombre+' '+e.apellido+'</div>' +
      '<div class="emp-cargo">'+e.cargo+'</div>' +
      '<div class="emp-meta">'+badgeEmpresa(e.empresa)+' '+badgeContrato(e.tipo_contrato)+
      ' <span class="badge '+(e.estado==='Activo'?'badge-activo':'badge-inactivo')+'">'+e.estado+'</span></div>' +
      '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#6d28d9;">'+fmt(e.salario_base)+'</div>' +
      '<button onclick="openEmpModal('+e.id+')" style="margin-top:10px;width:100%;padding:7px;background:#f3f0ff;border:1px solid #c4b5fd;border-radius:7px;color:#6d28d9;font-weight:600;cursor:pointer;font-size:13px;">&#9998; Editar colaborador</button>' +
      '</div>';
  }).join('');
}

function filterEmps() {
  var q = (document.getElementById('emp-search').value||'').toLowerCase();
  var emp = document.getElementById('emp-filter-empresa').value;
  var est = document.getElementById('emp-filter-estado').value;
  var filtered = allEmps.filter(function(e){
    var name = (e.nombre+' '+e.apellido+' '+e.cargo).toLowerCase();
    return (name.includes(q)) && (!emp || e.empresa===emp) && (!est || e.estado===est);
  });
  renderEmpleados(filtered);
}

async function openEmpModal(id) {
  currentEmpId = id;
  document.getElementById('m-emp-title').textContent = id ? 'Editar Empleado' : 'Nuevo Empleado';
  var fields = ['nombre','apellido','cedula','cargo','area','empresa','contrato','ingreso','salario','riesgo','eps','afp','arl','caja','email','tel','estado','obs'];
  if (id) {
    try {
      var d = await fetch('/api/rrhh/empleados/'+id).then(function(r){return r.json();});
      document.getElementById('f-nombre').value = d.nombre||'';
      document.getElementById('f-apellido').value = d.apellido||'';
      document.getElementById('f-cedula').value = d.cedula||'';
      document.getElementById('f-cargo').value = d.cargo||'';
      document.getElementById('f-area').value = d.area||'Producción';
      document.getElementById('f-empresa').value = d.empresa||'Espagiria';
      document.getElementById('f-contrato').value = d.tipo_contrato||'Indefinido';
      document.getElementById('f-ingreso').value = (d.fecha_ingreso||'').slice(0,10);
      document.getElementById('f-salario').value = d.salario_base||0;
      document.getElementById('f-riesgo').value = d.nivel_riesgo||1;
      document.getElementById('f-eps').value = d.eps||'';
      document.getElementById('f-afp').value = d.afp||'';
      document.getElementById('f-arl').value = d.arl||'';
      document.getElementById('f-caja').value = d.caja_compensacion||'';
      document.getElementById('f-email').value = d.email||'';
      document.getElementById('f-tel').value = d.telefono||'';
      document.getElementById('f-estado').value = d.estado||'Activo';
      document.getElementById('f-obs').value = d.observaciones||'';
      document.getElementById('f-banco').value = d.banco||'';
      document.getElementById('f-tipo-cta').value = d.tipo_cuenta||'';
      document.getElementById('f-num-cta').value = d.numero_cuenta||'';
    } catch(e){console.error(e);}
  } else {
    fields.forEach(function(f){var el=document.getElementById('f-'+f);if(el)el.value='';});
    document.getElementById('f-empresa').value='Espagiria';
    document.getElementById('f-contrato').value='Indefinido';
    document.getElementById('f-area').value='Producción';
    document.getElementById('f-estado').value='Activo';
    document.getElementById('f-riesgo').value='1';
    document.getElementById('f-banco').value='';
    document.getElementById('f-tipo-cta').value='';
    document.getElementById('f-num-cta').value='';
  }
  openModal('m-emp');
}

async function saveEmp() {
  var payload = {
    nombre: document.getElementById('f-nombre').value.trim(),
    apellido: document.getElementById('f-apellido').value.trim(),
    cedula: document.getElementById('f-cedula').value.trim(),
    cargo: document.getElementById('f-cargo').value.trim(),
    area: document.getElementById('f-area').value,
    empresa: document.getElementById('f-empresa').value,
    tipo_contrato: document.getElementById('f-contrato').value,
    fecha_ingreso: document.getElementById('f-ingreso').value,
    salario_base: parseFloat(document.getElementById('f-salario').value)||0,
    nivel_riesgo: parseInt(document.getElementById('f-riesgo').value)||1,
    eps: document.getElementById('f-eps').value.trim(),
    afp: document.getElementById('f-afp').value.trim(),
    arl: document.getElementById('f-arl').value.trim(),
    caja: document.getElementById('f-caja').value.trim(),
    email: document.getElementById('f-email').value.trim(),
    telefono: document.getElementById('f-tel').value.trim(),
    estado: document.getElementById('f-estado').value,
    observaciones: document.getElementById('f-obs').value.trim(),
    banco: document.getElementById('f-banco').value.trim(),
    tipo_cuenta: document.getElementById('f-tipo-cta').value.trim(),
    numero_cuenta: document.getElementById('f-num-cta').value.trim()
  };
  if (!payload.nombre || !payload.cargo) {alert('Nombre y cargo son obligatorios.');return;}
  var url = currentEmpId ? '/api/rrhh/empleados/'+currentEmpId : '/api/rrhh/empleados';
  var method = currentEmpId ? 'PUT' : 'POST';
  try {
    var r = await fetch(url,{method:method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var d = await r.json();
    if (d.ok || d.id) {closeModal('m-emp'); loadEmpleados();}
    else alert(d.error||'Error al guardar');
  } catch(e){alert('Error: '+e.message);}
}

// ─── NÓMINA ──────────────────────────────────────────
// (Funciones de nomina movidas a /tesoreria — 29-abr-2026)

async function loadAusencias(){
  var tipo = document.getElementById('aus-tipo').value;
  var estado = document.getElementById('aus-estado').value;
  try {
    var all = await fetch('/api/rrhh/ausencias').then(function(r){return r.json();});
    var filtered = all.filter(function(a){
      return (!tipo||a.tipo===tipo)&&(!estado||a.estado===estado);
    });
    var tbody = document.getElementById('aus-body');
    if(!filtered.length){tbody.innerHTML='<tr><td colspan="8" class="empty-state">Sin registros.</td></tr>';return;}
    var estadoColors = {'Aprobada':'badge-activo','Pendiente':'badge-fijo','Rechazada':'badge-inactivo'};
    tbody.innerHTML = filtered.map(function(a){
      return '<tr>' +
        '<td><strong>'+a.empleado+'</strong></td>' +
        '<td>'+a.tipo+'</td><td>'+fmtDate(a.fecha_inicio)+'</td><td>'+fmtDate(a.fecha_fin)+'</td>' +
        '<td style="text-align:center;font-weight:700;">'+a.dias+'</td>' +
        '<td><span class="badge '+(estadoColors[a.estado]||'badge-indef')+'">'+a.estado+'</span></td>' +
        '<td style="color:#78716c;max-width:150px;">'+(a.observaciones||'—')+'</td>' +
        '<td>' +
          (a.estado==='Pendiente'?
            '<button class="btn btn-success btn-sm" onclick="aprobarAus('+a.id+',\'Aprobada\')">Aprobar</button> '+
            '<button class="btn btn-danger btn-sm" style="margin-left:4px;" onclick="aprobarAus('+a.id+',\'Rechazada\')">Rechazar</button>':
            '<span style="color:#a8a29e;font-size:12px;">'+a.aprobado_por+'</span>') +
        '</td></tr>';
    }).join('');
  } catch(e){console.error(e);}
}

async function aprobarAus(id, estado){
  await fetch('/api/rrhh/ausencias/'+id,_fetchOpts('PATCH', {estado:estado}));
  loadAusencias();
}

function openAusModal(){
  var sel = document.getElementById('a-emp');
  sel.innerHTML = allEmps.filter(function(e){return e.estado==='Activo';}).map(function(e){
    return '<option value="'+e.id+'">'+e.nombre+' '+e.apellido+'</option>';
  }).join('');
  openModal('m-aus');
}

async function saveAus(){
  var payload={
    empleado_id: document.getElementById('a-emp').value,
    tipo: document.getElementById('a-tipo').value,
    fecha_inicio: document.getElementById('a-inicio').value,
    fecha_fin: document.getElementById('a-fin').value,
    dias: parseInt(document.getElementById('a-dias').value)||1,
    observaciones: document.getElementById('a-obs').value.trim()
  };
  if(!payload.fecha_inicio){alert('Fecha de inicio obligatoria.');return;}
  try {
    await fetch('/api/rrhh/ausencias',_fetchOpts('POST', payload));
    closeModal('m-aus');
    loadAusencias();
  } catch(e){alert('Error: '+e.message);}
}

// ─── CAPACITACIONES ──────────────────────────────────
async function loadCapacitaciones(){
  try {
    var caps = await fetch('/api/rrhh/capacitaciones').then(function(r){return r.json();});
    var div = document.getElementById('cap-list');
    if(!caps.length){div.innerHTML='<div class="empty-state">Sin capacitaciones registradas.</div>';return;}
    var tipoColors={'BPM':'#6d28d9','SGSST':'#dc2626','T\u00e9cnica':'#0e7490','Blanda':'#16a34a','Regulatoria':'#d97706'};
    div.innerHTML = caps.map(function(c){
      var pct = c.total>0 ? Math.round((c.completados||0)/c.total*100) : 0;
      var color = pct>=100?'green':pct>=50?'':'red';
      return '<div class="card" style="margin-bottom:12px;">' +
        '<div class="card-hd">' +
          '<div>' +
            '<span style="font-size:11px;font-weight:700;text-transform:uppercase;color:'+(tipoColors[c.tipo]||'#888')+';letter-spacing:.5px;">'+c.tipo+'</span>' +
            '<div style="font-size:15px;font-weight:700;margin-top:2px;">'+c.nombre+'</div>' +
            '<div style="font-size:12px;color:#78716c;margin-top:2px;">'+fmtDate(c.fecha)+' &bull; '+c.horas+'h &bull; '+c.instructor+'</div>' +
          '</div>' +
          '<div style="text-align:right;">' +
            '<div style="font-size:24px;font-weight:800;color:'+(color==='green'?'#16a34a':color==='red'?'#dc2626':'#d97706')+'">'+pct+'%</div>' +
            '<div style="font-size:11px;color:#78716c;">'+(c.completados||0)+'/'+c.total+' completados</div>' +
          '</div>' +
        '</div>' +
        '<div class="prog-bar"><div class="prog-fill '+color+'" style="width:'+pct+'%"></div></div>' +
        '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

function openCapModal(){openModal('m-cap');}

async function saveCap(){
  var payload={
    nombre: document.getElementById('c-nombre').value.trim(),
    tipo: document.getElementById('c-tipo').value,
    fecha: document.getElementById('c-fecha').value,
    duracion_horas: parseFloat(document.getElementById('c-horas').value)||1,
    instructor: document.getElementById('c-instructor').value.trim(),
    obligatoria: true
  };
  if(!payload.nombre){alert('Nombre obligatorio.');return;}
  try {
    await fetch('/api/rrhh/capacitaciones',_fetchOpts('POST', payload));
    closeModal('m-cap');
    loadCapacitaciones();
  } catch(e){alert('Error: '+e.message);}
}

// ─── EVALUACIONES ────────────────────────────────────
async function loadEvaluaciones(){
  var periodo = document.getElementById('eva-periodo').value;
  var url = '/api/rrhh/evaluaciones'+(periodo?'?periodo='+periodo:'');
  try {
    var evals = await fetch(url).then(function(r){return r.json();});
    var div = document.getElementById('eva-grid');
    if(!evals.length){div.innerHTML='<div class="empty-state">Sin evaluaciones para este per\u00edodo.</div>';return;}
    div.innerHTML = evals.map(function(ev){
      var scores=[['Calidad',ev.calidad],['Asistencia',ev.asistencia],['Actitud',ev.actitud],['Conocimiento',ev.conocimiento],['Productividad',ev.productividad]];
      var color = ev.total>=4?'#16a34a':ev.total>=3?'#d97706':'#dc2626';
      return '<div class="eval-card">' +
        '<div style="display:flex;align-items:center;gap:16px;margin-bottom:14px;">' +
          '<div class="emp-avatar" style="background:'+avatarColor(ev.empleado)+';width:44px;height:44px;font-size:15px;flex-shrink:0;">'+ev.empleado.slice(0,2).toUpperCase()+'</div>' +
          '<div style="flex:1;">' +
            '<div style="font-size:14px;font-weight:700;">'+ev.empleado+'</div>' +
            '<div style="font-size:12px;color:#78716c;">'+ev.cargo+' &bull; '+ev.periodo+' &bull; Eval: '+ev.evaluador+'</div>' +
          '</div>' +
          '<div style="text-align:right;"><div class="total-score" style="color:'+color+';">'+ev.total+'</div><div style="font-size:11px;color:#78716c;">/ 5.0</div></div>' +
        '</div>' +
        scores.map(function(s){
          var pct=(s[1]/5)*100;
          return '<div class="score-bar-row"><span class="lbl">'+s[0]+'</span><div class="bar"><div class="fill" style="width:'+pct+'%;"></div></div><span class="num">'+s[1]+'</span></div>';
        }).join('') +
        (ev.comentarios?'<div style="margin-top:10px;font-size:12px;color:#57534e;background:#f9f8f7;padding:8px 10px;border-radius:6px;">'+ev.comentarios+'</div>':'') +
        '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

function openEvaModal(){
  var sel = document.getElementById('e-emp');
  sel.innerHTML = allEmps.filter(function(e){return e.estado==='Activo';}).map(function(e){
    return '<option value="'+e.id+'">'+e.nombre+' '+e.apellido+'</option>';
  }).join('');
  document.getElementById('ev-criteria').innerHTML = CRITERIA.map(function(c){
    return '<div class="rating-group" style="margin-bottom:10px;">' +
      '<label>'+c.label+'</label>' +
      '<input type="range" id="ev-'+c.key+'" min="1" max="5" step="0.5" value="3" oninput="document.getElementById(\'rv-'+c.key+'\').textContent=this.value;">' +
      '<span class="rval" id="rv-'+c.key+'">3</span>' +
      '</div>';
  }).join('');
  openModal('m-eva');
}

async function saveEva(){
  var payload={
    empleado_id: document.getElementById('e-emp').value,
    periodo: document.getElementById('e-per').value,
    comentarios: document.getElementById('e-comentarios').value.trim()
  };
  CRITERIA.forEach(function(c){payload[c.key]=parseFloat(document.getElementById('ev-'+c.key).value)||3;});
  try {
    await fetch('/api/rrhh/evaluaciones',_fetchOpts('POST', payload));
    closeModal('m-eva');
    loadEvaluaciones();
  } catch(e){alert('Error: '+e.message);}
}

// ─── SGSST ───────────────────────────────────────────
async function loadSgsst(){
  try {
    var items = await fetch('/api/rrhh/sgsst').then(function(r){return r.json();});
    var div = document.getElementById('sgsst-body');
    if(!items.length){div.innerHTML='<div class="empty-state">Sin requisitos SGSST registrados.</div>';return;}
    var bycat={};
    items.forEach(function(it){
      if(!bycat[it.categoria])bycat[it.categoria]=[];
      bycat[it.categoria].push(it);
    });
    div.innerHTML = Object.keys(bycat).map(function(cat){
      var its = bycat[cat];
      var cumplidos = its.filter(function(x){return x.estado==='Cumplido';}).length;
      var pct = Math.round(cumplidos/its.length*100);
      var col = pct===100?'green':pct>=60?'amber':'red';
      return '<div class="sgsst-cat">' +
        '<div class="sgsst-cat-hd">' +
          '<span>'+cat+'</span>' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:120px;"><div class="prog-bar"><div class="prog-fill '+col+'" style="width:'+pct+'%"></div></div></div>' +
            '<span style="font-size:12px;font-weight:700;color:'+(col==='green'?'#16a34a':col==='amber'?'#d97706':'#dc2626')+';">'+pct+'%</span>' +
          '</div>' +
        '</div>' +
        its.map(function(it){
          var dotCls = it.estado==='Cumplido'?'dot-cumplido':it.estado==='Vencido'?'dot-vencido':'dot-pendiente';
          return '<div class="sgsst-item">' +
            '<div class="sgsst-dot '+dotCls+'"></div>' +
            '<div style="flex:1;">' +
              '<div style="font-size:13px;font-weight:500;">'+it.descripcion+'</div>' +
              '<div style="font-size:11px;color:#78716c;margin-top:2px;">'+it.frecuencia+(it.responsable?' &bull; '+it.responsable:'')+(it.proximo?' &bull; Pr\u00f3ximo: '+fmtDate(it.proximo):'')+'</div>' +
            '</div>' +
            (it.estado!=='Cumplido'?'<button class="btn btn-success btn-sm" onclick="cumplirSgsst('+it.id+')">Marcar cumplido</button>':'<span style="font-size:12px;color:#16a34a;font-weight:600;">\u2713 '+fmtDate(it.ultimo)+'</span>') +
          '</div>';
        }).join('') +
      '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

async function cumplirSgsst(id){
  await fetch('/api/rrhh/sgsst/'+id,_fetchOpts('PATCH', {estado:'Cumplido'}));
  loadSgsst();
}

function openSgsstModal(){openModal('m-sgsst');}

async function saveSgsst(){
  var payload={
    categoria: document.getElementById('sg-cat').value,
    descripcion: document.getElementById('sg-desc').value.trim(),
    frecuencia: document.getElementById('sg-freq').value,
    responsable: document.getElementById('sg-resp').value.trim(),
    proximo_vencimiento: document.getElementById('sg-prox').value
  };
  if(!payload.descripcion){alert('Descripci\u00f3n obligatoria.');return;}
  try {
    await fetch('/api/rrhh/sgsst',_fetchOpts('POST', payload));
    closeModal('m-sgsst');
    loadSgsst();
  } catch(e){alert('Error: '+e.message);}
}

// ─── init ────────────────────────────────────────────
loadDashboard();
loadEmpleados();
</script>
</body>
</html>
"""
