"""Template HTML del módulo Aseguramiento (ASG).

Pestañas:
- Dashboard ASG (KPIs)
- SGD electrónico (los 124 docs centralizados)
- Capacitaciones (firma SOPs)
- Conflictos (códigos repetidos detectados)
- Mis capacitaciones (vista del usuario actual)

Pestañas que MIGRARÁN desde /calidad (futuro):
- No Conformidades
- Auditorías
- CAPA
"""

ASEGURAMIENTO_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="es">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
<title>Aseguramiento de Calidad · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--accent:#7ACFCC;--good:#15803d;--warn:#fbbf24;--crit:#ef4444}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;margin:0;color:#0f172a}
header{background:#0f172a;color:#f1f5f9;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
.logo{font-weight:800;letter-spacing:.5px;font-size:1.05em;color:#7ACFCC}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;flex-wrap:wrap;overflow-x:auto}
.tab{padding:11px 20px;font-size:0.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;white-space:nowrap}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC}
.tab:hover{color:#cbd5e1}
.main{padding:18px 24px;max-width:1400px;margin:0 auto}
.pane{display:none}.pane.active{display:block}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card-title{font-size:1em;font-weight:700;color:#0f172a;margin-bottom:8px}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px;text-align:center}
.kpi-label{font-size:0.72em;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:1.6em;font-weight:800;color:#0f172a;margin-top:2px}
.kpi-val.good{color:#15803d}.kpi-val.warn{color:#fbbf24}.kpi-val.crit{color:#ef4444}
.kpi-sub{font-size:0.7em;color:#94a3b8;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:0.85em}
th,td{padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:left;vertical-align:top}
th{background:#f8fafc;font-weight:700;color:#475569;font-size:0.76em;text-transform:uppercase;letter-spacing:.5px}
tr:hover{background:#fafafa}
.empty{text-align:center;color:#94a3b8;padding:14px;font-style:italic}
.btn{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:0.85em;font-weight:600}
.btn-primary{background:#7ACFCC;color:#0f172a}.btn-primary:hover{background:#5fb8b5}
.btn-ghost{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1}
.btn-ghost:hover{background:#e2e8f0}
.btn-sm{padding:4px 10px;font-size:0.78em}
.form-group{margin-bottom:8px}
.form-group label{display:block;font-size:0.78em;color:#475569;font-weight:600;margin-bottom:2px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:0.9em;background:#fff;box-sizing:border-box}
.form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}
.modal-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px}
.modal-overlay.open{display:flex}
.modal{background:#fff;border-radius:10px;padding:22px;max-width:600px;width:100%;max-height:88vh;overflow-y:auto;position:relative}
.modal-close{position:absolute;top:8px;right:8px;background:none;border:none;font-size:24px;cursor:pointer;color:#64748b;width:32px;height:32px;line-height:32px;border-radius:50%}
.modal-close:hover{background:#f1f5f9}
.modal-title{font-size:1.1em;font-weight:700;margin-bottom:14px;color:#0f172a}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.72em;font-weight:700;text-transform:uppercase}
.badge-vig{background:#d1fae5;color:#15803d}
.badge-venc{background:#fef2f2;color:#ef4444}
.badge-prox{background:#fef9c3;color:#a16207}
.badge-obs{background:#f3f4f6;color:#6b7280}
.badge-confl{background:#ffedd5;color:#c2410c}
.badge-bor{background:#dbeafe;color:#1e40af}
code{background:#f1f5f9;padding:1px 6px;border-radius:3px;font-family:SFMono-Regular,Consolas,monospace;font-size:0.85em}
/* Toast notifications · audit zero-error 2-may-2026 · reemplazo de alert() */
#_toast-container{position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:8px;pointer-events:none}
.toast{background:#fff;border-left:4px solid #7ACFCC;padding:12px 18px;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:260px;max-width:400px;font-size:0.9em;animation:slideIn .25s ease-out;pointer-events:auto;cursor:pointer}
.toast.success{border-left-color:#15803d}.toast.error{border-left-color:#ef4444}
.toast.warn{border-left-color:#fbbf24}.toast.fade-out{animation:fadeOut .25s ease-in forwards}
@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:none;opacity:1}}
@keyframes fadeOut{to{transform:translateX(120%);opacity:0}}
.btn[disabled]{opacity:.5;cursor:wait}
</style>
</head>
<body>
<div id="_toast-container" aria-live="polite" aria-atomic="true"></div>
<header>
  <div class="logo">EOS · ASEGURAMIENTO DE CALIDAD</div>
  <div style="display:flex;gap:10px;align-items:center">
    <a href="/calidad" class="btn btn-ghost btn-sm">&larr; Calidad</a>
    <a href="/" class="btn btn-ghost btn-sm">Inicio</a>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash')">&#x1F4CA; Dashboard</div>
  <div class="tab" onclick="goTab('tab-mis-tareas')">&#x1F464; Mis tareas</div>
  <div class="tab" onclick="goTab('tab-sgd')">&#x1F4DA; SGD electrónico</div>
  <div class="tab" onclick="goTab('tab-cap')">&#x1F393; Capacitaciones</div>
  <div class="tab" onclick="goTab('tab-mis-cap')">&#x270D;&#xFE0F; Mis firmas</div>
  <div class="tab" onclick="goTab('tab-desv')">&#x1F4E2; Desviaciones</div>
  <div class="tab" onclick="goTab('tab-cambios')">&#x1F504; Control de Cambios</div>
  <div class="tab" onclick="goTab('tab-quejas')">&#x1F4AC; Quejas Clientes</div>
  <div class="tab" onclick="goTab('tab-recalls')">&#x1F6A8; Recall</div>
  <div class="tab" onclick="goTab('tab-reportes')">&#x1F4CB; Reportes INVIMA</div>
  <div class="tab" onclick="goTab('tab-conf')">&#x26A0;&#xFE0F; Conflictos SGD</div>
</div>

<div class="main">

<!-- DASHBOARD -->
<div id="tab-dash" class="pane active">
  <!-- Alertas críticas (banner rojo si hay) -->
  <div id="dash-alertas-wrap" style="display:none">
    <div class="card" style="background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px;margin-bottom:14px">
      <div style="font-weight:700;color:#991b1b;margin-bottom:6px">🚨 Alertas críticas (acción requerida)</div>
      <div id="dash-alertas-list" style="font-size:0.85em"></div>
    </div>
  </div>

  <!-- SGD -->
  <div class="card-title" style="margin-top:6px">📚 SGD electrónico</div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Docs Vigentes</div><div class="kpi-val good" id="kp-vig">—</div></div>
    <div class="kpi"><div class="kpi-label">Vencen 30d</div><div class="kpi-val warn" id="kp-prox">—</div></div>
    <div class="kpi"><div class="kpi-label">Vencidos</div><div class="kpi-val crit" id="kp-venc">—</div></div>
    <div class="kpi"><div class="kpi-label">Conflictos</div><div class="kpi-val warn" id="kp-confl">—</div></div>
    <div class="kpi"><div class="kpi-label">Capacit. pendientes</div><div class="kpi-val warn" id="kp-cap">—</div></div>
  </div>

  <!-- Workflows ASG -->
  <div class="card-title" style="margin-top:14px">⚙️ Workflows ASG</div>
  <div class="kpi-row">
    <div class="kpi" onclick="goTab('tab-desv')" style="cursor:pointer"><div class="kpi-label">📢 Desviaciones</div>
      <div class="kpi-val" id="kp-desv-tot">—</div>
      <div class="kpi-sub"><span style="color:#ef4444" id="kp-desv-crit">—</span> críticas · <span id="kp-desv-sin">—</span> s/clasificar</div>
    </div>
    <div class="kpi" onclick="goTab('tab-cambios')" style="cursor:pointer"><div class="kpi-label">🔄 Cambios</div>
      <div class="kpi-val" id="kp-cam-tot">—</div>
      <div class="kpi-sub"><span style="color:#ef4444" id="kp-cam-inv">—</span> INVIMA · <span id="kp-cam-sin">—</span> s/evaluar</div>
    </div>
    <div class="kpi" onclick="goTab('tab-quejas')" style="cursor:pointer"><div class="kpi-label">💬 Quejas</div>
      <div class="kpi-val" id="kp-qc-tot">—</div>
      <div class="kpi-sub"><span style="color:#ef4444" id="kp-qc-crit">—</span> críticas · <span id="kp-qc-nue">—</span> nuevas</div>
    </div>
    <div class="kpi" onclick="goTab('tab-recalls')" style="cursor:pointer"><div class="kpi-label">🚨 Recalls</div>
      <div class="kpi-val" id="kp-rcl-tot">—</div>
      <div class="kpi-sub"><span style="color:#ef4444" id="kp-rcl-c1">—</span> Clase I · <span id="kp-rcl-inv">—</span> s/INVIMA</div>
    </div>
  </div>

  <!-- Otros -->
  <div class="card-title" style="margin-top:14px">📋 Otros</div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">NCs abiertas</div><div class="kpi-val" id="kp-nc">—</div></div>
    <div class="kpi"><div class="kpi-label">Auditorías 60d</div><div class="kpi-val" id="kp-aud">—</div></div>
  </div>

  <div class="card" style="margin-top:14px">
    <div class="card-title">Resumen del SGD por área</div>
    <div id="dash-areas"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- MIS TAREAS · vista personalizada por usuario -->
<div id="tab-mis-tareas" class="pane">
  <div id="mt-loading" style="text-align:center;padding:30px;color:#94a3b8">Cargando...</div>
  <div id="mt-content" style="display:none">
    <div style="margin-bottom:14px">
      <span style="font-size:1.1em;font-weight:700">Tareas para </span>
      <span id="mt-user" style="font-size:1.1em;font-weight:700;color:#7ACFCC"></span>
      <span id="mt-rol" style="font-size:0.78em;color:#94a3b8;margin-left:6px"></span>
    </div>

    <!-- Banner urgentes (rojo) -->
    <div id="mt-urgentes-wrap" style="display:none">
      <div class="card" style="background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px;margin-bottom:14px">
        <div style="font-weight:700;color:#991b1b;margin-bottom:6px">🚨 Urgente · acción inmediata</div>
        <div id="mt-urgentes-list" style="font-size:0.85em"></div>
      </div>
    </div>

    <!-- Capacitaciones pendientes -->
    <div class="card">
      <div class="card-title">🎓 Capacitaciones pendientes <span id="mt-cap-cnt" style="color:#94a3b8;font-weight:400;font-size:0.85em"></span></div>
      <div id="mt-cap-body"><p class="empty">Sin capacitaciones pendientes</p></div>
    </div>

    <!-- Mis ítems abiertos -->
    <div class="card">
      <div class="card-title">📋 Items que reporté/creé y siguen abiertos <span id="mt-mc-cnt" style="color:#94a3b8;font-weight:400;font-size:0.85em"></span></div>
      <div id="mt-mc-body"><p class="empty">Sin ítems abiertos</p></div>
    </div>

    <!-- Cola Calidad (solo si rol Calidad) -->
    <div class="card" id="mt-queue-card" style="display:none">
      <div class="card-title">⚙️ Cola de Calidad · pendientes de tu acción <span id="mt-q-cnt" style="color:#94a3b8;font-weight:400;font-size:0.85em"></span></div>
      <div id="mt-queue-body"><p class="empty">Cola vacía 👏</p></div>
    </div>
  </div>
</div>

<!-- SGD ELECTRÓNICO -->
<div id="tab-sgd" class="pane">
  <div class="card">
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px">
      <input id="sgd-q" placeholder="Buscar por código o título" style="flex:1;min-width:200px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
      <select id="sgd-area" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="">Todas áreas</option>
        <option value="COC">COC · Control Calidad</option>
        <option value="ASG">ASG · Aseguramiento</option>
        <option value="ADM">ADM · Administración</option>
        <option value="BDG">BDG · Bodega</option>
        <option value="GER">GER · Gerencia</option>
        <option value="PRD">PRD · Producción</option>
        <option value="RRH">RRH · Recursos Humanos</option>
        <option value="SST">SST · Seguridad</option>
      </select>
      <select id="sgd-tipo" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="">Todos tipos</option>
        <option value="PRO">Procedimientos</option>
        <option value="NOR">Normas</option>
        <option value="MAN">Manuales</option>
        <option value="INS">Instructivos</option>
        <option value="POL">Políticas</option>
        <option value="FOR">Formatos</option>
        <option value="LMA">Listados maestros</option>
      </select>
      <select id="sgd-estado" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="vigente">Vigentes</option>
        <option value="">Todos estados</option>
        <option value="borrador">Borrador</option>
        <option value="obsoleto">Obsoletos</option>
        <option value="conflicto">Conflicto</option>
      </select>
      <label style="display:flex;align-items:center;gap:4px;font-size:0.85em;color:#475569">
        <input type="checkbox" id="sgd-hijos" onchange="loadSGD()"> Incluir formatos hijos
      </label>
      <button class="btn btn-ghost btn-sm" onclick="loadSGD()">&#x1F50D; Buscar</button>
      <button class="btn btn-primary btn-sm" onclick="abrirNuevoSGD()">+ Nuevo</button>
    </div>
    <div id="sgd-resumen" style="font-size:0.78em;color:#64748b;margin-bottom:6px"></div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Título</th><th>Versión</th><th>Estado</th><th>Próx. revisión</th><th>Aprobado por</th><th></th></tr></thead>
        <tbody id="sgd-tbody"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- CAPACITACIONES (asignación / supervisión) -->
<div id="tab-cap" class="pane">
  <div class="card">
    <div class="card-title">Asignar lectura/firma de un SOP</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">
      <div class="form-group"><label>Código SGD *</label><input id="cap-codigo" placeholder="COC-PRO-001"></div>
      <div class="form-group"><label>Versión *</label><input id="cap-version" placeholder="v02"></div>
      <div class="form-group"><label>Fecha límite</label><input id="cap-fecha-lim" type="date"></div>
    </div>
    <div class="form-group"><label>Personas (usernames separados por coma)</label>
      <input id="cap-personas" placeholder="laura, miguel, yuliel">
    </div>
    <div style="text-align:right">
      <button class="btn btn-primary" onclick="asignarCap()">Asignar</button>
    </div>
    <div id="cap-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- MIS CAPACITACIONES (vista del usuario actual) -->
<div id="tab-mis-cap" class="pane">
  <div class="card">
    <div class="card-title">Mis capacitaciones pendientes</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Versión</th><th>Documento</th><th>Asignada</th><th>Estado</th><th>Acción</th></tr></thead>
        <tbody id="mis-cap-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- DESVIACIONES · ASG-PRO-001 -->
<div id="tab-desv" class="pane">
  <div class="kpi-row" id="desv-kpis">
    <div class="kpi"><div class="kpi-label">Total</div><div class="kpi-val" id="desv-kp-tot">—</div></div>
    <div class="kpi"><div class="kpi-label">Críticas abiertas</div><div class="kpi-val crit" id="desv-kp-crit">—</div></div>
    <div class="kpi"><div class="kpi-label">Sin clasificar</div><div class="kpi-val warn" id="desv-kp-sin">—</div></div>
    <div class="kpi"><div class="kpi-label">Investigando</div><div class="kpi-val" id="desv-kp-inv">—</div></div>
    <div class="kpi"><div class="kpi-label">Cerradas 30d</div><div class="kpi-val good" id="desv-kp-cer">—</div></div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Lista</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="desv-f-estado" onchange="loadDesviaciones()">
          <option value="">Todos estados</option>
          <option value="detectada">Detectadas</option>
          <option value="clasificada">Clasificadas</option>
          <option value="en_investigacion">En investigación</option>
          <option value="capa_propuesto">CAPA propuesto</option>
          <option value="capa_implementado">CAPA implementado</option>
          <option value="cerrada">Cerradas</option>
        </select>
        <select id="desv-f-clasif" onchange="loadDesviaciones()">
          <option value="">Toda clasificación</option>
          <option value="critica">Crítica</option>
          <option value="mayor">Mayor</option>
          <option value="menor">Menor</option>
          <option value="informativa">Informativa</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadDesviaciones()">↻</button>
        <button class="btn btn-primary btn-sm" onclick="abrirNuevaDesviacion()">+ Nueva</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Fecha</th><th>Tipo</th><th>Área</th><th>Descripción</th><th>Clasif.</th><th>Estado</th><th>Días</th><th></th></tr></thead>
        <tbody id="desv-tbody"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nueva desviación -->
<div class="modal-overlay" id="m-desv-new" role="dialog" aria-modal="true" aria-label="Reportar desviación">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-desv-new')">&times;</button>
    <div class="modal-title">Reportar desviación</div>
    <div class="form-group"><label>Tipo *</label>
      <select id="m-desv-tipo">
        <option value="proceso">Proceso</option>
        <option value="equipo">Equipo</option>
        <option value="instalacion">Instalación</option>
        <option value="sistema_agua">Sistema de agua</option>
        <option value="ambiental">Ambiental (T/HR)</option>
        <option value="documental">Documental</option>
        <option value="personal">Personal</option>
        <option value="materia_prima">Materia prima</option>
        <option value="envase">Envase/empaque</option>
        <option value="otra">Otra</option>
      </select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Área origen</label><input id="m-desv-area" placeholder="Fab1, Disp, Lab..."></div>
      <div class="form-group"><label>Hora detección</label><input id="m-desv-hora" type="time"></div>
    </div>
    <div class="form-group"><label>Descripción * (≥10 chars)</label><textarea id="m-desv-desc" style="min-height:70px" placeholder="Qué pasó · cuándo · cómo se detectó"></textarea></div>
    <div class="form-group"><label>Contención inmediata</label><textarea id="m-desv-cont" style="min-height:50px" placeholder="Qué se hizo de inmediato para contener"></textarea></div>
    <div class="form-group"><label><input type="checkbox" id="m-desv-impacto"> Impacta producto / lote en proceso</label></div>
    <div class="form-group"><label>Lotes afectados (si aplica)</label><input id="m-desv-lotes" placeholder="LOTE-001, LOTE-002..."></div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-desv-new')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarDesviacion()">Reportar</button>
    </div>
    <div id="m-desv-new-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle desviación + workflow -->
<div class="modal-overlay" id="m-desv-det" role="dialog" aria-modal="true" aria-label="Detalle desviación">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-desv-det')">&times;</button>
    <div class="modal-title" id="m-desv-det-title">Detalle</div>
    <input type="hidden" id="m-desv-det-id">
    <div id="m-desv-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- CONTROL DE CAMBIOS · ASG-PRO-007 -->
<div id="tab-cambios" class="pane">
  <div class="kpi-row" id="cam-kpis">
    <div class="kpi"><div class="kpi-label">Total</div><div class="kpi-val" id="cam-kp-tot">—</div></div>
    <div class="kpi"><div class="kpi-label">Sin evaluar</div><div class="kpi-val warn" id="cam-kp-sin">—</div></div>
    <div class="kpi"><div class="kpi-label">En evaluación</div><div class="kpi-val" id="cam-kp-eva">—</div></div>
    <div class="kpi"><div class="kpi-label">Aprobados pendientes</div><div class="kpi-val warn" id="cam-kp-apr">—</div></div>
    <div class="kpi"><div class="kpi-label">Requieren INVIMA</div><div class="kpi-val crit" id="cam-kp-inv">—</div></div>
    <div class="kpi"><div class="kpi-label">Cerrados 30d</div><div class="kpi-val good" id="cam-kp-cer">—</div></div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Solicitudes de cambio</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="cam-f-estado" onchange="loadCambios()">
          <option value="">Todos estados</option>
          <option value="solicitado">Solicitado</option>
          <option value="en_evaluacion">En evaluación</option>
          <option value="aprobado">Aprobado</option>
          <option value="rechazado">Rechazado</option>
          <option value="en_implementacion">En implementación</option>
          <option value="implementado">Implementado</option>
          <option value="cerrado">Cerrado</option>
        </select>
        <select id="cam-f-sev" onchange="loadCambios()">
          <option value="">Toda severidad</option>
          <option value="mayor">Mayor</option>
          <option value="menor">Menor</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadCambios()">↻</button>
        <button class="btn btn-primary btn-sm" onclick="abrirNuevoCambio()">+ Nueva solicitud</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Fecha</th><th>Tipo</th><th>Título</th><th>Sev.</th><th>Estado</th><th>INVIMA</th><th>Días</th><th></th></tr></thead>
        <tbody id="cam-tbody"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nueva solicitud -->
<div class="modal-overlay" id="m-cam-new" role="dialog" aria-modal="true" aria-label="Solicitar cambio">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-cam-new')">&times;</button>
    <div class="modal-title">Nueva solicitud de cambio</div>
    <div class="form-group"><label>Tipo *</label>
      <select id="m-cam-tipo">
        <option value="formulacion">Fórmula del producto</option>
        <option value="proceso">Proceso de fabricación</option>
        <option value="equipo">Equipo</option>
        <option value="instalacion">Instalación</option>
        <option value="proveedor">Proveedor / MP</option>
        <option value="documental">Documento (SOP/forma)</option>
        <option value="sistema">Sistema (HVAC/Agua/etc)</option>
        <option value="envase">Envase / empaque</option>
        <option value="otro" selected>Otro</option>
      </select>
    </div>
    <div class="form-group"><label>Título * (≥5 chars)</label>
      <input id="m-cam-titulo" placeholder="Ej: Cambio de proveedor de glicerina">
    </div>
    <div class="form-group"><label>Descripción del cambio * (≥20 chars)</label>
      <textarea id="m-cam-desc" style="min-height:70px" placeholder="Qué se quiere cambiar exactamente"></textarea>
    </div>
    <div class="form-group"><label>Justificación / motivo</label>
      <textarea id="m-cam-just" style="min-height:50px" placeholder="Por qué es necesario"></textarea>
    </div>
    <div class="form-group"><label>Áreas afectadas</label>
      <input id="m-cam-areas" placeholder="Producción, Calidad, Bodega...">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label><input type="checkbox" id="m-cam-bpm"> Impacto en BPM/GMP</label></div>
      <div class="form-group"><label><input type="checkbox" id="m-cam-reg"> Impacto regulatorio (INVIMA)</label></div>
    </div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-cam-new')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCambio()">Solicitar</button>
    </div>
    <div id="m-cam-new-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle cambio + workflow -->
<div class="modal-overlay" id="m-cam-det" role="dialog" aria-modal="true" aria-label="Detalle cambio">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-cam-det')">&times;</button>
    <div class="modal-title" id="m-cam-det-title">Detalle</div>
    <input type="hidden" id="m-cam-det-id">
    <div id="m-cam-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- QUEJAS CLIENTES · ASG-PRO-013 -->
<div id="tab-quejas" class="pane">
  <div class="kpi-row" id="qc-kpis">
    <div class="kpi"><div class="kpi-label">Total</div><div class="kpi-val" id="qc-kp-tot">—</div></div>
    <div class="kpi"><div class="kpi-label">Nuevas</div><div class="kpi-val warn" id="qc-kp-nue">—</div></div>
    <div class="kpi"><div class="kpi-label">Investigando</div><div class="kpi-val" id="qc-kp-inv">—</div></div>
    <div class="kpi"><div class="kpi-label">Pendiente cierre</div><div class="kpi-val warn" id="qc-kp-pen">—</div></div>
    <div class="kpi"><div class="kpi-label">Críticas abiertas</div><div class="kpi-val crit" id="qc-kp-crit">—</div></div>
    <div class="kpi"><div class="kpi-label">Cerradas 30d</div><div class="kpi-val good" id="qc-kp-cer">—</div></div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Quejas y reclamos</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="qc-f-estado" onchange="loadQuejas()">
          <option value="">Todos estados</option>
          <option value="nueva">Nueva</option>
          <option value="en_triaje">En triaje</option>
          <option value="en_investigacion">Investigando</option>
          <option value="respondida">Respondida</option>
          <option value="cerrada">Cerrada</option>
          <option value="rechazada">Rechazada</option>
        </select>
        <select id="qc-f-sev" onchange="loadQuejas()">
          <option value="">Toda severidad</option>
          <option value="critica">Crítica</option>
          <option value="mayor">Mayor</option>
          <option value="menor">Menor</option>
          <option value="informativa">Informativa</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadQuejas()">↻</button>
        <button class="btn btn-primary btn-sm" onclick="abrirNuevaQueja()">+ Nueva queja</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Fecha</th><th>Canal</th><th>Cliente</th><th>Producto / Lote</th><th>Tipo</th><th>Sev.</th><th>Estado</th><th>Días</th><th></th></tr></thead>
        <tbody id="qc-tbody"><tr><td colspan="10" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nueva queja -->
<div class="modal-overlay" id="m-qc-new" role="dialog" aria-modal="true" aria-label="Registrar queja de cliente">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-qc-new')">&times;</button>
    <div class="modal-title">Registrar queja de cliente</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Canal *</label>
        <select id="m-qc-canal">
          <option value="email">Email</option>
          <option value="telefono">Teléfono</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="redes_sociales">Redes sociales</option>
          <option value="presencial">Presencial</option>
          <option value="distribuidor">Distribuidor</option>
          <option value="formulario_web">Formulario web</option>
          <option value="otro" selected>Otro</option>
        </select>
      </div>
      <div class="form-group"><label>Tipo de queja *</label>
        <select id="m-qc-tipo">
          <option value="reaccion_adversa">Reacción adversa</option>
          <option value="calidad_producto">Calidad del producto</option>
          <option value="envase_empaque">Envase / empaque</option>
          <option value="cantidad_volumen">Cantidad / volumen</option>
          <option value="fecha_vencimiento">Fecha vencimiento</option>
          <option value="sabor_olor_textura">Sabor / olor / textura</option>
          <option value="eficacia">Eficacia</option>
          <option value="documentacion">Documentación</option>
          <option value="servicio">Servicio</option>
          <option value="otro" selected>Otro</option>
        </select>
      </div>
    </div>
    <div class="form-group"><label>Cliente · nombre *</label>
      <input id="m-qc-cli-nom" placeholder="Nombre del cliente o empresa">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Contacto (email/tel)</label><input id="m-qc-cli-cont"></div>
      <div class="form-group"><label>Tipo cliente</label>
        <select id="m-qc-cli-tipo">
          <option value="">—</option>
          <option value="consumidor_final">Consumidor final</option>
          <option value="distribuidor">Distribuidor</option>
          <option value="retail">Retail</option>
          <option value="medico">Médico</option>
          <option value="otro">Otro</option>
        </select>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
      <div class="form-group"><label>Producto</label><input id="m-qc-prod" placeholder="Ej: SAH-30ml"></div>
      <div class="form-group"><label>Lote</label><input id="m-qc-lote" placeholder="LOTE-2026-XXX"></div>
      <div class="form-group"><label>Fecha compra</label><input id="m-qc-fcompra" type="date"></div>
    </div>
    <div class="form-group"><label>Establecimiento de compra</label>
      <input id="m-qc-est" placeholder="Farmacia, retail, web...">
    </div>
    <div class="form-group"><label>Descripción de la queja * (≥10 chars)</label>
      <textarea id="m-qc-desc" style="min-height:70px" placeholder="Qué reportó el cliente · cuándo · cómo"></textarea>
    </div>
    <div class="form-group">
      <label style="color:#c2410c"><input type="checkbox" id="m-qc-salud"> ⚠ Impacto en salud (notifica inmediato)</label>
    </div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-qc-new')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarQueja()">Registrar</button>
    </div>
    <div id="m-qc-new-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle queja + workflow -->
<div class="modal-overlay" id="m-qc-det" role="dialog" aria-modal="true" aria-label="Detalle queja">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-qc-det')">&times;</button>
    <div class="modal-title" id="m-qc-det-title">Detalle</div>
    <input type="hidden" id="m-qc-det-id">
    <div id="m-qc-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- RECALL · ASG-PRO-004 -->
<div id="tab-recalls" class="pane">
  <div class="kpi-row" id="rcl-kpis">
    <div class="kpi"><div class="kpi-label">Total</div><div class="kpi-val" id="rcl-kp-tot">—</div></div>
    <div class="kpi"><div class="kpi-label">Sin clasificar</div><div class="kpi-val warn" id="rcl-kp-sin">—</div></div>
    <div class="kpi"><div class="kpi-label">Clase I abiertos</div><div class="kpi-val crit" id="rcl-kp-c1">—</div></div>
    <div class="kpi"><div class="kpi-label">INVIMA pendiente</div><div class="kpi-val crit" id="rcl-kp-inv">—</div></div>
    <div class="kpi"><div class="kpi-label">En recolección</div><div class="kpi-val" id="rcl-kp-rec">—</div></div>
    <div class="kpi"><div class="kpi-label">Cerrados 30d</div><div class="kpi-val good" id="rcl-kp-cer">—</div></div>
  </div>

  <div class="card" style="background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px">
    <div style="font-size:0.85em;color:#991b1b">⚠ <b>RECALL = decisión grave.</b> Solo iniciar tras confirmar que el producto en el mercado representa riesgo. Clase I requiere notificación INVIMA en <b>&lt;24h</b> (Resolución 2214/2021).</div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Recalls</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="rcl-f-estado" onchange="loadRecalls()">
          <option value="">Todos estados</option>
          <option value="iniciado">Iniciado</option>
          <option value="clasificado">Clasificado</option>
          <option value="invima_notificado">INVIMA notificado</option>
          <option value="distribuidores_notificados">Distribuidores notif.</option>
          <option value="en_recoleccion">En recolección</option>
          <option value="completado">Completado</option>
          <option value="cerrado">Cerrado</option>
          <option value="cancelado">Cancelado</option>
        </select>
        <select id="rcl-f-clase" onchange="loadRecalls()">
          <option value="">Toda clase</option>
          <option value="clase_I">Clase I</option>
          <option value="clase_II">Clase II</option>
          <option value="clase_III">Clase III</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadRecalls()">↻</button>
        <button class="btn btn-primary btn-sm" onclick="abrirNuevoRecall()" style="background:#ef4444;color:#fff">+ Iniciar recall</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Inicio</th><th>Producto / Lotes</th><th>Origen</th><th>Clase</th><th>Alcance</th><th>Estado</th><th>INVIMA</th><th>Días</th><th></th></tr></thead>
        <tbody id="rcl-tbody"><tr><td colspan="10" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nuevo recall -->
<div class="modal-overlay" id="m-rcl-new" role="dialog" aria-modal="true" aria-label="Iniciar recall">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-rcl-new')">&times;</button>
    <div class="modal-title" style="color:#ef4444">🚨 Iniciar recall de producto</div>
    <div style="background:#fef2f2;padding:8px 10px;border-radius:6px;font-size:0.78em;color:#991b1b;margin-bottom:10px">
      Esta acción inicia el proceso formal de retiro de producto del mercado y notifica inmediato a Calidad+Sebastián.
    </div>
    <div class="form-group"><label>Origen *</label>
      <select id="m-rcl-origen">
        <option value="desviacion">Desviación detectada</option>
        <option value="queja_cliente">Queja de cliente</option>
        <option value="hallazgo_interno">Hallazgo interno</option>
        <option value="auditoria">Auditoría</option>
        <option value="reaccion_adversa">Reacción adversa</option>
        <option value="invima">Solicitud INVIMA</option>
        <option value="otro" selected>Otro</option>
      </select>
    </div>
    <div class="form-group"><label>Referencia origen (código DESV/QC/etc)</label>
      <input id="m-rcl-origen-ref" placeholder="DESV-2026-0010 · QC-2026-0005 ...">
    </div>
    <div class="form-group"><label>Producto * </label>
      <input id="m-rcl-prod" placeholder="Ej: SAH-30ml · Sérum Niacinamida 4%">
    </div>
    <div class="form-group"><label>Lotes afectados * (separados por coma)</label>
      <input id="m-rcl-lotes" placeholder="LOTE-2026-001, LOTE-2026-005...">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Cantidad fabricada (uds)</label><input id="m-rcl-fab" type="number"></div>
      <div class="form-group"><label>Cantidad distribuida (uds)</label><input id="m-rcl-dist" type="number"></div>
    </div>
    <div class="form-group"><label>Motivo del recall * (≥20 chars)</label>
      <textarea id="m-rcl-motivo" style="min-height:60px" placeholder="Defecto detectado, riesgo identificado..."></textarea>
    </div>
    <div class="form-group"><label>Descripción del riesgo</label>
      <textarea id="m-rcl-riesgo" style="min-height:50px" placeholder="Cómo afecta al consumidor"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-rcl-new')">Cancelar</button>
      <button class="btn btn-primary" style="background:#ef4444;color:#fff" onclick="guardarRecall()">Iniciar recall</button>
    </div>
    <div id="m-rcl-new-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle recall + workflow -->
<div class="modal-overlay" id="m-rcl-det" role="dialog" aria-modal="true" aria-label="Detalle recall">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-rcl-det')">&times;</button>
    <div class="modal-title" id="m-rcl-det-title">Detalle</div>
    <input type="hidden" id="m-rcl-det-id">
    <div id="m-rcl-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- REPORTES INVIMA -->
<div id="tab-reportes" class="pane">
  <div class="card" style="background:#eff6ff;border-left:4px solid #0ea5e9">
    <div style="font-weight:700;color:#0c4a6e;margin-bottom:4px">📋 Reportes regulatorios INVIMA</div>
    <div style="font-size:0.85em;color:#0c4a6e">Consultas ad-hoc para auditoría INVIMA · acceso solo Calidad/Admin · descarga CSV disponible.</div>
  </div>

  <!-- Sub-pestañas dentro de Reportes -->
  <div style="display:flex;gap:0;border-bottom:1px solid #cbd5e1;margin-bottom:14px">
    <div class="rep-tab active" onclick="repGoTab('rep-audit')" style="padding:8px 16px;cursor:pointer;font-weight:600;border-bottom:2px solid #7ACFCC;color:#7ACFCC">Audit Trail</div>
    <div class="rep-tab" onclick="repGoTab('rep-lote')" style="padding:8px 16px;cursor:pointer;font-weight:600;color:#94a3b8">Trazabilidad Lote</div>
    <div class="rep-tab" onclick="repGoTab('rep-cliente')" style="padding:8px 16px;cursor:pointer;font-weight:600;color:#94a3b8">Trazabilidad Cliente</div>
  </div>

  <!-- Audit Trail -->
  <div id="rep-audit" class="rep-pane">
    <div class="card">
      <div class="card-title">Audit Trail · evidencia INVIMA de cambios regulatorios</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:10px">
        <div class="form-group"><label>Desde</label><input id="rep-at-desde" type="date"></div>
        <div class="form-group"><label>Hasta</label><input id="rep-at-hasta" type="date"></div>
        <div class="form-group"><label>Acción</label>
          <select id="rep-at-accion">
            <option value="">Todas</option>
            <option value="PAGAR_OC">PAGAR_OC</option>
            <option value="AUTORIZAR_OC">AUTORIZAR_OC</option>
            <option value="FACTURA_PAGO">FACTURA_PAGO</option>
            <option value="FACTURA_ANULAR">FACTURA_ANULAR</option>
            <option value="COMPLETAR_PRODUCCION">COMPLETAR_PRODUCCION</option>
            <option value="CERRAR_DESVIACION">CERRAR_DESVIACION</option>
            <option value="CAMBIO_APROBACION">CAMBIO_APROBACION</option>
            <option value="CERRAR_CAMBIO">CERRAR_CAMBIO</option>
            <option value="CAMBIO_NOTIFICAR_INVIMA">CAMBIO_NOTIFICAR_INVIMA</option>
            <option value="CERRAR_QUEJA">CERRAR_QUEJA</option>
            <option value="INICIAR_RECALL">INICIAR_RECALL</option>
            <option value="RECALL_CLASIFICAR">RECALL_CLASIFICAR</option>
            <option value="RECALL_NOTIFICAR_INVIMA">RECALL_NOTIFICAR_INVIMA</option>
            <option value="CERRAR_RECALL">CERRAR_RECALL</option>
            <option value="SGD_FIRMAR_CAP">SGD_FIRMAR_CAP</option>
            <option value="SGD_PDF">SGD_PDF</option>
            <option value="CREAR_NC">CREAR_NC</option>
            <option value="CREAR_COA">CREAR_COA</option>
            <option value="CREAR_OOS">CREAR_OOS</option>
            <option value="REGISTRAR_AGUA">REGISTRAR_AGUA</option>
            <option value="CREAR_CAPA">CREAR_CAPA</option>
            <option value="CREAR_AUDITORIA">CREAR_AUDITORIA</option>
            <option value="CREAR_HALLAZGO">CREAR_HALLAZGO</option>
            <option disabled>── Técnica/SGD ──</option>
            <option value="CREAR_FORMULA">CREAR_FORMULA</option>
            <option value="MODIFICAR_FORMULA">MODIFICAR_FORMULA</option>
            <option value="ELIMINAR_FORMULA">ELIMINAR_FORMULA</option>
            <option value="RESTAURAR_FORMULA">RESTAURAR_FORMULA</option>
            <option value="CREAR_FICHA">CREAR_FICHA</option>
            <option value="MODIFICAR_FICHA">MODIFICAR_FICHA</option>
            <option value="ELIMINAR_FICHA">ELIMINAR_FICHA</option>
            <option value="CREAR_REGISTRO_INVIMA">CREAR_REGISTRO_INVIMA</option>
            <option value="MODIFICAR_REGISTRO_INVIMA">MODIFICAR_REGISTRO_INVIMA</option>
            <option value="ELIMINAR_REGISTRO_INVIMA">ELIMINAR_REGISTRO_INVIMA</option>
            <option value="CREAR_SGD">CREAR_SGD</option>
            <option value="MODIFICAR_SGD">MODIFICAR_SGD</option>
            <option value="ELIMINAR_SGD">ELIMINAR_SGD</option>
            <option value="REVISAR_SGD">REVISAR_SGD</option>
            <option disabled>── Planta/Liberación ──</option>
            <option value="APROBAR_LOTE">APROBAR_LOTE</option>
            <option value="RECHAZAR_LOTE">RECHAZAR_LOTE</option>
            <option value="INICIAR_PRODUCCION">INICIAR_PRODUCCION</option>
            <option value="TERMINAR_PRODUCCION">TERMINAR_PRODUCCION</option>
            <option value="INICIAR_ENVASADO">INICIAR_ENVASADO</option>
            <option value="TERMINAR_ENVASADO">TERMINAR_ENVASADO</option>
            <option value="LIBERAR_LOTE_PT">LIBERAR_LOTE_PT</option>
            <option value="RECHAZAR_LOTE_PT">RECHAZAR_LOTE_PT</option>
            <option value="REANALIZAR_LOTE_PT">REANALIZAR_LOTE_PT</option>
          </select>
        </div>
        <div class="form-group"><label>Usuario</label><input id="rep-at-usuario" placeholder="laura, sebastian..."></div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
        <button class="btn btn-primary btn-sm" onclick="repAuditCargar()">Consultar</button>
        <button class="btn btn-ghost btn-sm" onclick="repAuditExport()">📥 Descargar CSV</button>
        <span id="rep-at-info" style="font-size:0.85em;color:#64748b"></span>
      </div>
      <div style="overflow-x:auto;max-height:60vh;overflow-y:auto">
        <table>
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Tabla</th><th>Registro</th><th>Detalle</th><th>IP</th></tr></thead>
          <tbody id="rep-at-tbody"><tr><td colspan="7" class="empty">Click "Consultar" para cargar audit log</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Lote trazabilidad -->
  <div id="rep-lote" class="rep-pane" style="display:none">
    <div class="card">
      <div class="card-title">Trazabilidad por Lote · cadena recepción → cliente</div>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
        <input id="rep-lote-input" placeholder="LOTE-2026-001" style="flex:1;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <button class="btn btn-primary btn-sm" onclick="repLoteCargar()">Consultar</button>
      </div>
      <div id="rep-lote-body"><p class="empty">Ingresa un código de lote para consultar</p></div>
    </div>
  </div>

  <!-- Cliente trazabilidad -->
  <div id="rep-cliente" class="rep-pane" style="display:none">
    <div class="card">
      <div class="card-title">Trazabilidad por Cliente · qué lotes recibió</div>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
        <input id="rep-cli-input" type="number" placeholder="ID cliente (ej. 1)" style="width:200px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <button class="btn btn-primary btn-sm" onclick="repClienteCargar()">Consultar</button>
        <span style="font-size:0.85em;color:#64748b">Encuentra el ID en la pestaña Clientes</span>
      </div>
      <div id="rep-cli-body"><p class="empty">Ingresa ID de cliente para consultar</p></div>
    </div>
  </div>
</div>

<!-- CONFLICTOS SGD -->
<div id="tab-conf" class="pane">
  <div class="card">
    <div class="card-title">&#x26A0;&#xFE0F; Conflictos detectados (códigos repetidos con temas distintos)</div>
    <div style="font-size:0.85em;color:#64748b;margin-bottom:8px">Estos códigos del SGD físico aparecen con temas diferentes en los archivos · resolver eligiendo qué tema queda con el código original.</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Temas detectados</th><th>Estado</th><th>Resolución</th><th></th></tr></thead>
        <tbody id="conf-tbody"><tr><td colspan="5" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nuevo SGD -->
<div class="modal-overlay" id="m-sgd" role="dialog" aria-modal="true" aria-label="Documento SGD">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-sgd')">&times;</button>
    <div class="modal-title" id="m-sgd-title">Nuevo documento SGD</div>
    <div class="form-group"><label>Código (AAA-BBB-NNN[-FNN]) *</label>
      <input id="m-sgd-codigo" placeholder="COC-PRO-018">
    </div>
    <div class="form-group"><label>Título *</label>
      <input id="m-sgd-titulo" placeholder="Ej: Control de envases primarios">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Versión</label><input id="m-sgd-version" value="1"></div>
      <div class="form-group"><label>Estado</label>
        <select id="m-sgd-estado">
          <option value="vigente">Vigente</option>
          <option value="borrador">Borrador</option>
          <option value="revision">En revisión</option>
        </select>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Vigente desde</label><input id="m-sgd-vigente" type="date"></div>
      <div class="form-group"><label>Próxima revisión</label><input id="m-sgd-proxrev" type="date"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
      <div class="form-group"><label>Elaborado por</label><input id="m-sgd-elab"></div>
      <div class="form-group"><label>Revisado por</label><input id="m-sgd-rev"></div>
      <div class="form-group"><label>Aprobado por</label><input id="m-sgd-apr"></div>
    </div>
    <div class="form-group"><label>URL del PDF</label><input id="m-sgd-url" placeholder="opcional"></div>
    <div class="form-group"><label>Observaciones / motivo del cambio</label><textarea id="m-sgd-obs" style="min-height:60px"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-sgd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSGD()">Guardar</button>
    </div>
    <div id="m-sgd-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle SGD -->
<div class="modal-overlay" id="m-sgd-det" role="dialog" aria-modal="true" aria-label="Detalle SGD">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-sgd-det')">&times;</button>
    <div class="modal-title" id="m-sgd-det-title">Detalle</div>
    <div id="m-sgd-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

</div>
<script>
function _esc(s){return String(s||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}

// Toast notifications · audit zero-error · reemplazo de alert() bloqueante
function toast(msg, type){
  type = type || 'info';
  var c = document.getElementById('_toast-container'); if(!c) return alert(msg);
  var t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  t.onclick = function(){ t.classList.add('fade-out'); setTimeout(function(){ t.remove(); }, 250); };
  c.appendChild(t);
  setTimeout(function(){ t.classList.add('fade-out'); setTimeout(function(){ t.remove(); }, 250); },
             type==='error' ? 6000 : 3500);
}

// withBusy: ejecuta async fn() con el botón deshabilitado · evita doble-click
async function withBusy(btn, fn){
  if(!btn || btn.disabled) return;
  btn.disabled = true;
  var prev = btn.textContent;
  try { return await fn(); }
  finally { btn.disabled = false; if(btn.textContent !== prev) btn.textContent = prev; }
}

var _tabIds = ['tab-dash','tab-mis-tareas','tab-sgd','tab-cap','tab-mis-cap','tab-desv','tab-cambios','tab-quejas','tab-recalls','tab-reportes','tab-conf'];
function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',_tabIds[i]===id);});
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-dash') loadDashboard();
  else if(id==='tab-mis-tareas') loadMisTareas();
  else if(id==='tab-sgd') loadSGD();
  else if(id==='tab-mis-cap') loadMisCapacitaciones();
  else if(id==='tab-desv') loadDesviaciones();
  else if(id==='tab-cambios') loadCambios();
  else if(id==='tab-quejas') loadQuejas();
  else if(id==='tab-recalls') loadRecalls();
  else if(id==='tab-reportes') repInit();
  else if(id==='tab-conf') loadConflictos();
}

// === MIS TAREAS · vista consolidada del usuario =======================
async function loadMisTareas(){
  document.getElementById('mt-loading').style.display = 'block';
  document.getElementById('mt-content').style.display = 'none';
  try{
    var r = await fetch('/api/aseguramiento/mis-tareas');
    var d = await r.json();
    document.getElementById('mt-user').textContent = d.usuario;
    document.getElementById('mt-rol').textContent = d.es_calidad ? '· Rol Calidad/Admin' : '';

    // Urgentes
    var urg = d.urgentes || [];
    var urgWrap = document.getElementById('mt-urgentes-wrap');
    if(urg.length){
      urgWrap.style.display = 'block';
      document.getElementById('mt-urgentes-list').innerHTML = urg.map(function(it){
        return '<div style="padding:4px 0;border-top:1px solid #fecaca;cursor:pointer" onclick="goTab(\'tab-'+_modBaseTab(it.modulo)+'\')">'
          +'<b><code>'+_esc(it.codigo)+'</code></b> · '+_esc(it.titulo||'')+' · '
          +'<span style="color:#991b1b">'+_esc(it.accion)+'</span> · '+(it.dias||0)+'d'
          +'</div>';
      }).join('');
    } else { urgWrap.style.display = 'none'; }

    // Capacitaciones
    var cap = d.capacitaciones || [];
    document.getElementById('mt-cap-cnt').textContent = cap.length ? '('+cap.length+')' : '';
    if(cap.length){
      document.getElementById('mt-cap-body').innerHTML =
        '<table><thead><tr><th>Código</th><th>SOP</th><th>Asignado</th><th>Plazo</th><th></th></tr></thead><tbody>'
        + cap.map(function(it){
          var pdfBtn = it.archivo_pdf_url
            ? '<a href="'+_esc(it.archivo_pdf_url)+'" target="_blank" rel="noopener" class="btn btn-primary btn-sm" onclick="_marcarPdfAbierto(\''+_esc(it.sgd_codigo)+'\',\''+_esc(it.sgd_version)+'\')">📎 Abrir PDF</a> '
            : '<span style="color:#94a3b8;font-size:0.78em">sin PDF · </span>';
          return '<tr>'
            +'<td><code>'+_esc(it.sgd_codigo)+'</code> v'+_esc(it.sgd_version)+'</td>'
            +'<td>'+_esc(it.titulo||'')+'</td>'
            +'<td>'+_esc(it.asignado_at||'')+' ('+(it.dias||0)+'d)</td>'
            +'<td>'+_esc(it.fecha_limite||'—')+'</td>'
            +'<td style="white-space:nowrap">'+pdfBtn+'<button class="btn btn-ghost btn-sm" onclick="goTab(\'tab-mis-cap\')">Ir a firmas</button></td>'
            +'</tr>';
        }).join('') + '</tbody></table>';
    } else {
      document.getElementById('mt-cap-body').innerHTML = '<p class="empty">Sin capacitaciones pendientes 👏</p>';
    }

    // Mis creados
    var mc = d.mis_creados || [];
    document.getElementById('mt-mc-cnt').textContent = mc.length ? '('+mc.length+')' : '';
    if(mc.length){
      document.getElementById('mt-mc-body').innerHTML =
        '<table><thead><tr><th>Módulo</th><th>Código</th><th>Título</th><th>Estado</th><th>Días</th><th>Próxima acción</th></tr></thead><tbody>'
        + mc.map(function(it){
          var modIcon = _modIcon(it.modulo);
          return '<tr style="cursor:pointer" onclick="goTab(\'tab-'+_modBaseTab(it.modulo)+'\')">'
            +'<td>'+modIcon+' '+_esc(it.modulo)+'</td>'
            +'<td><code>'+_esc(it.codigo)+'</code></td>'
            +'<td>'+_esc(it.titulo||'')+'</td>'
            +'<td><span style="font-size:0.85em">'+_esc((it.estado||'').replace(/_/g,' '))+'</span></td>'
            +'<td>'+(it.dias||0)+'d</td>'
            +'<td style="font-size:0.85em;color:#475569">'+_esc(it.accion||'')+'</td>'
            +'</tr>';
        }).join('') + '</tbody></table>';
    } else {
      document.getElementById('mt-mc-body').innerHTML = '<p class="empty">No reportaste nada que siga abierto</p>';
    }

    // Cola Calidad
    var queueCard = document.getElementById('mt-queue-card');
    if(d.es_calidad){
      queueCard.style.display = 'block';
      var q = d.calidad_queue || [];
      document.getElementById('mt-q-cnt').textContent = q.length ? '('+q.length+')' : '';
      if(q.length){
        // Ordenar por urgencia
        var orden = {'super_alta':0,'alta':1,'media':2};
        q.sort(function(a,b){return (orden[a.urgencia]||9) - (orden[b.urgencia]||9);});
        document.getElementById('mt-queue-body').innerHTML =
          '<table><thead><tr><th>Urgencia</th><th>Módulo</th><th>Código</th><th>Título</th><th>Días</th><th>Acción</th></tr></thead><tbody>'
          + q.map(function(it){
            var urgBadge = it.urgencia === 'super_alta' ? '<span class="badge badge-venc">URGENTE</span>'
              : it.urgencia === 'alta' ? '<span class="badge badge-prox">alta</span>'
              : '<span class="badge badge-bor">media</span>';
            var modIcon = _modIcon(it.modulo);
            return '<tr style="cursor:pointer" onclick="goTab(\'tab-'+_modBaseTab(it.modulo)+'\')">'
              +'<td>'+urgBadge+'</td>'
              +'<td>'+modIcon+' '+_esc(it.modulo)+'</td>'
              +'<td><code>'+_esc(it.codigo)+'</code></td>'
              +'<td>'+_esc(it.titulo||'')+'</td>'
              +'<td>'+(it.dias||0)+'d</td>'
              +'<td style="font-weight:600">'+_esc(it.accion||'')+'</td>'
              +'</tr>';
          }).join('') + '</tbody></table>';
      } else {
        document.getElementById('mt-queue-body').innerHTML = '<p class="empty">Cola vacía 👏</p>';
      }
    } else {
      queueCard.style.display = 'none';
    }

    document.getElementById('mt-loading').style.display = 'none';
    document.getElementById('mt-content').style.display = 'block';
  }catch(e){
    document.getElementById('mt-loading').innerHTML = '<span style="color:#c00">Error: '+_esc(e.message)+'</span>';
  }
}

function _modIcon(m){
  return {'desviaciones':'📢','cambios':'🔄','quejas':'💬','recalls':'🚨'}[m] || '•';
}
function _modBaseTab(m){
  return {'desviaciones':'desv','cambios':'cambios','quejas':'quejas','recalls':'recalls'}[m] || 'dash';
}

// === DESVIACIONES (ASG-PRO-001) ========================================
async function loadDesviaciones(){
  var estado = document.getElementById('desv-f-estado').value;
  var clasif = document.getElementById('desv-f-clasif').value;
  var qs = [];
  if(estado) qs.push('estado='+estado);
  if(clasif) qs.push('clasificacion='+clasif);
  var url = '/api/aseguramiento/desviaciones' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('desv-kp-tot').textContent = k.total || 0;
    document.getElementById('desv-kp-crit').textContent = k.criticas_abiertas || 0;
    document.getElementById('desv-kp-sin').textContent = k.sin_clasificar || 0;
    document.getElementById('desv-kp-inv').textContent = k.investigando || 0;
    document.getElementById('desv-kp-cer').textContent = k.cerradas_30d || 0;
    var tb = document.getElementById('desv-tbody');
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="9" class="empty">Sin desviaciones</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var clasifBadge = it.clasificacion === 'critica' ? '<span class="badge badge-venc">crítica</span>'
        : it.clasificacion === 'mayor' ? '<span class="badge badge-prox">mayor</span>'
        : it.clasificacion === 'menor' ? '<span class="badge badge-bor">menor</span>'
        : it.clasificacion === 'informativa' ? '<span class="badge badge-obs">info</span>'
        : '<span style="color:#94a3b8;font-size:0.78em">—</span>';
      var estadoLabel = (it.estado||'').replace('_',' ');
      var estadoCol = it.estado === 'cerrada' ? '#15803d'
        : it.estado === 'rechazada' ? '#94a3b8'
        : it.estado === 'detectada' ? '#ef4444'
        : '#fbbf24';
      var icono = it.impacto_producto ? '⚠ ' : '';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.fecha_deteccion||'')+(it.hora_deteccion?' '+_esc(it.hora_deteccion):'')+'</td>'
        +'<td>'+_esc(it.tipo||'')+'</td>'
        +'<td>'+_esc(it.area_origen||'')+'</td>'
        +'<td>'+icono+_esc((it.descripcion||'').slice(0,80))+(it.descripcion && it.descripcion.length > 80 ? '...' : '')+'</td>'
        +'<td>'+clasifBadge+'</td>'
        +'<td><span style="color:'+estadoCol+';font-weight:600;font-size:0.85em">'+_esc(estadoLabel)+'</span></td>'
        +'<td>'+(it.dias_abierta||0)+'d</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verDesviacion('+it.id+')">Abrir</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('desv-tbody').innerHTML = '<tr><td colspan="9" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function abrirNuevaDesviacion(){
  ['m-desv-area','m-desv-desc','m-desv-cont','m-desv-lotes','m-desv-new-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-desv-impacto').checked = false;
  document.getElementById('m-desv-hora').value = new Date().toTimeString().slice(0,5);
  openModal('m-desv-new');
}

async function guardarDesviacion(){
  var msg = document.getElementById('m-desv-new-msg');
  var body = {
    tipo: document.getElementById('m-desv-tipo').value,
    area_origen: document.getElementById('m-desv-area').value,
    hora_deteccion: document.getElementById('m-desv-hora').value,
    descripcion: document.getElementById('m-desv-desc').value,
    contencion_inmediata: document.getElementById('m-desv-cont').value,
    impacto_producto: document.getElementById('m-desv-impacto').checked,
    lotes_afectados: document.getElementById('m-desv-lotes').value,
  };
  if(!body.descripcion || body.descripcion.length < 10){
    msg.innerHTML = '<span style="color:#ef4444">Descripción requerida (≥10 chars)</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/desviaciones', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.codigo)+' creada</span>';
      setTimeout(function(){ closeModal('m-desv-new'); loadDesviaciones(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function verDesviacion(id){
  document.getElementById('m-desv-det-id').value = id;
  var body = document.getElementById('m-desv-det-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-desv-det');
  try{
    var r = await fetch('/api/aseguramiento/desviaciones/'+id);
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    document.getElementById('m-desv-det-title').textContent = d.codigo + ' · ' + (d.estado||'').replace('_',' ');

    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.85em;color:#475569"><b>Detectada:</b> '+_esc(d.fecha_deteccion||'')+' '+_esc(d.hora_deteccion||'')+' · por '+_esc(d.detectado_por||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Tipo:</b> '+_esc(d.tipo||'')+' · <b>Área:</b> '+_esc(d.area_origen||'—')+'</div>'
      +'<div style="margin-top:8px"><b>Descripción:</b><br>'+_esc(d.descripcion||'')+'</div>'
      +(d.contencion_inmediata ? '<div style="margin-top:6px"><b>Contención:</b><br>'+_esc(d.contencion_inmediata)+'</div>' : '')
      +(d.impacto_producto ? '<div style="margin-top:6px;color:#ef4444">⚠ <b>Impacta producto</b> · Lotes: '+_esc(d.lotes_afectados||'?')+'</div>' : '')
      +'</div>';

    // Workflow steps
    html += '<div class="card-title" style="margin-top:12px">Workflow</div>';

    // Paso 1: Clasificación
    if(d.clasificacion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>1. Clasificada</b> como <b>'+_esc(d.clasificacion)+'</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.justificacion_clasificacion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.clasificado_por||'')+' · '+_esc(d.clasificado_at||'')+'</div>'
        +'</div>';
    } else {
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>1. Clasificar</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">'
        +'<select id="cl-clasif" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">--</option><option value="critica">Crítica</option><option value="mayor">Mayor</option><option value="menor">Menor</option><option value="informativa">Informativa</option></select>'
        +'<input id="cl-just" placeholder="Justificación (≥10 chars)" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="clasificarDesv('+id+')">Clasificar</button></div>'
        +'</div>';
    }

    // Paso 2: Investigación
    if(d.causa_raiz_descripcion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>2. Investigada</b> · método: <b>'+_esc(d.metodo_investigacion||'')+'</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Causa raíz:</b><br>'+_esc(d.causa_raiz_descripcion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.investigado_por||'')+' · '+_esc(d.investigacion_at||'')+'</div>'
        +'</div>';
    } else if(d.clasificacion){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>2. Investigar causa raíz</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 2fr;gap:8px;margin-top:6px">'
        +'<select id="inv-metodo" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="5_porques">5 Porqués</option><option value="ishikawa">Ishikawa</option><option value="arbol_decision">Árbol decisión</option><option value="otro">Otro</option></select>'
        +'<textarea id="inv-causa" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px;min-height:50px" placeholder="Causa raíz (≥20 chars)"></textarea>'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="investigarDesv('+id+')">Registrar investigación</button></div>'
        +'</div>';
    }

    // Paso 3: CAPA
    if(d.capa_descripcion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>3. CAPA propuesto</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.capa_descripcion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">Resp: '+_esc(d.capa_responsable||'?')+' · Límite: '+_esc(d.capa_fecha_limite||'sin definir')+'</div>'
        +'</div>';
    } else if(d.causa_raiz_descripcion){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>3. Definir CAPA</b> (pendiente)</div>'
        +'<div class="form-group"><label>Descripción de acciones (≥20 chars)</label><textarea id="capa-desc" style="min-height:50px"></textarea></div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        +'<input id="capa-resp" placeholder="Responsable" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'<input id="capa-fecha" type="date" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="capaDesv('+id+')">Guardar CAPA</button></div>'
        +'</div>';
    }

    // Paso 4: Cierre
    if(d.estado === 'cerrada'){
      var efCol = d.efectividad_ok ? '#15803d' : '#ef4444';
      var efLabel = d.efectividad_ok ? '✅ EFECTIVIDAD OK' : '❌ EFECTIVIDAD NO OK';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+efCol+'">'
        +'<div style="font-size:1em;font-weight:700;color:'+efCol+'">'+efLabel+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Verificación:</b> '+_esc(d.verificacion_efectividad||'')+'</div>'
        +(d.observaciones_cierre ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Observaciones:</b> '+_esc(d.observaciones_cierre)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Cerrada '+_esc(d.fecha_cierre||'')+' por '+_esc(d.cerrado_por||'')+'</div>'
        +'</div>';
      // Sugerir recall si crítica + efectividad NO OK + lotes en mercado
      if(d.clasificacion === 'critica' && !d.efectividad_ok){
        html += '<div class="card" style="background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px;margin-top:10px">'
          +'<div style="font-weight:700;color:#991b1b">🚨 CAPA NO efectivo en desviación crítica</div>'
          +'<div style="font-size:0.85em;color:#991b1b;margin-top:4px">El producto/lote afectado podría seguir representando riesgo en el mercado. Considerar iniciar recall (Resolución 2214/2021).</div>'
          +'<div style="margin-top:8px"><button class="btn btn-primary btn-sm" style="background:#ef4444;color:#fff" onclick="iniciarRecallDesdeDesv('+id+')">🚨 Iniciar recall desde esta desviación</button></div>'
          +'</div>';
      }
    } else if(d.capa_descripcion){
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>4. Cerrar con verificación</b></div>'
        +'<div class="form-group"><label>Verificación de efectividad (≥20 chars)</label><textarea id="cer-verif" style="min-height:50px"></textarea></div>'
        +'<div class="form-group"><label><input type="checkbox" id="cer-ok"> CAPA fue efectiva</label></div>'
        +'<div class="form-group"><label>Observaciones cierre</label><input id="cer-obs"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="cerrarDesv('+id+')">Cerrar desviación</button></div>'
        +'</div>';
    }

    // Timeline
    if(d.timeline && d.timeline.length){
      html += '<div class="card-title" style="margin-top:12px">Timeline</div>';
      html += '<div style="font-size:0.85em">';
      d.timeline.forEach(function(ev){
        html += '<div style="border-left:2px solid #cbd5e1;padding:4px 0 4px 10px;margin-bottom:4px">'
          +'<div style="font-weight:600">'+_esc(ev.evento_tipo)+(ev.estado_anterior ? ' · '+_esc(ev.estado_anterior)+'→'+_esc(ev.estado_nuevo) : '')+'</div>'
          +'<div style="color:#475569">'+_esc(ev.comentario||'')+'</div>'
          +'<div style="color:#94a3b8;font-size:0.85em">'+_esc(ev.usuario||'')+' · '+_esc(ev.creado_en||'')+'</div>'
          +'</div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

async function clasificarDesv(id){
  var clasif = document.getElementById('cl-clasif').value;
  var just = document.getElementById('cl-just').value;
  if(!clasif){ alert('Elige clasificación'); return; }
  if(!just || just.length < 10){ alert('Justificación ≥10 chars'); return; }
  await _postDesvAccion(id, 'clasificar', {clasificacion: clasif, justificacion: just});
}

async function investigarDesv(id){
  var metodo = document.getElementById('inv-metodo').value;
  var causa = document.getElementById('inv-causa').value;
  if(!causa || causa.length < 20){ alert('Causa raíz ≥20 chars'); return; }
  await _postDesvAccion(id, 'investigar', {metodo_investigacion: metodo, causa_raiz: causa});
}

async function capaDesv(id){
  var desc = document.getElementById('capa-desc').value;
  var resp = document.getElementById('capa-resp').value;
  var fecha = document.getElementById('capa-fecha').value;
  if(!desc || desc.length < 20){ alert('Descripción CAPA ≥20 chars'); return; }
  if(!resp){ alert('Responsable requerido'); return; }
  await _postDesvAccion(id, 'capa', {capa_descripcion: desc, capa_responsable: resp, capa_fecha_limite: fecha});
}

async function cerrarDesv(id){
  var verif = document.getElementById('cer-verif').value;
  var ok = document.getElementById('cer-ok').checked;
  var obs = document.getElementById('cer-obs').value;
  if(!verif || verif.length < 20){ alert('Verificación efectividad ≥20 chars'); return; }
  if(!confirm('Confirmas cerrar esta desviación con efectividad ' + (ok ? 'OK' : 'NO OK') + '?')) return;
  await _postDesvAccion(id, 'cerrar', {efectividad_ok: ok, verificacion_efectividad: verif, observaciones_cierre: obs});
}

// Helper genérico unificado para los 4 workflows ASG.
// Maps módulo → {endpoint, refresh callbacks, hooks especiales}.
var _WORKFLOWS = {
  desviaciones: {path: 'desviaciones', view: function(id){verDesviacion(id);}, list: function(){loadDesviaciones();}},
  cambios:      {path: 'cambios',      view: function(id){verCambio(id);},     list: function(){loadCambios();}},
  quejas:       {path: 'quejas',       view: function(id){verQueja(id);},      list: function(){loadQuejas();}},
  recalls:      {path: 'recalls',      view: function(id){verRecall(id);},     list: function(){loadRecalls();}},
};

async function _postWorkflowAccion(modulo, id, accion, body){
  var cfg = _WORKFLOWS[modulo];
  if(!cfg){ toast('módulo desconocido: '+modulo, 'error'); return; }
  try{
    var r = await fetch('/api/aseguramiento/'+cfg.path+'/'+id+'/'+accion, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    var d = await r.json();
    if(!d.ok){ toast('Error: '+(d.error||'?'), 'error'); return; }
    // Hook: cross-link desv→recall si el backend lo sugiere
    if(modulo === 'desviaciones' && accion === 'cerrar' && d.sugiere_recall){
      if(confirm('⚠ CAPA NO efectivo en desviación crítica.\n\n¿Iniciar recall ahora con datos pre-rellenados?')){
        _abrirRecallPrefill(d.recall_prefill || {});
        cfg.list();
        return;
      }
    }
    toast('✓ '+accion+' OK', 'success');
    cfg.view(id); cfg.list();
  }catch(e){ toast('Error red: '+e.message, 'error'); }
}

// Wrappers para compatibilidad (referencias en HTML inline)
async function _postDesvAccion(id, accion, body){ return _postWorkflowAccion('desviaciones', id, accion, body); }

async function iniciarRecallDesdeDesv(desvId){
  if(!confirm('Iniciar recall desde esta desviación. ¿Confirmas?')) return;
  // Cargar la desv para extraer datos y pre-rellenar el modal de recall
  try{
    var r = await fetch('/api/aseguramiento/desviaciones/'+desvId);
    var d = await r.json();
    _abrirRecallPrefill({
      origen: 'desviacion',
      origen_referencia: d.codigo,
      desviacion_id: desvId,
      lotes_afectados: d.lotes_afectados || '',
      motivo: 'Desviación crítica '+d.codigo+' cerrada con CAPA no efectivo. '+((d.descripcion||'').slice(0,500)),
    });
  }catch(e){ alert('Error red: '+e.message); }
}

function _abrirRecallPrefill(prefill){
  closeModal('m-desv-det');
  goTab('tab-recalls');
  setTimeout(function(){
    abrirNuevoRecall();  // tiene confirm propio
    setTimeout(function(){
      var el;
      el = document.getElementById('m-rcl-origen'); if(el) el.value = prefill.origen || 'desviacion';
      el = document.getElementById('m-rcl-origen-ref'); if(el) el.value = prefill.origen_referencia || '';
      el = document.getElementById('m-rcl-lotes'); if(el) el.value = prefill.lotes_afectados || '';
      el = document.getElementById('m-rcl-motivo'); if(el) el.value = prefill.motivo || '';
    }, 250);
  }, 250);
}

// === CONTROL DE CAMBIOS (ASG-PRO-007) =================================
async function loadCambios(){
  var estado = document.getElementById('cam-f-estado').value;
  var sev = document.getElementById('cam-f-sev').value;
  var qs = [];
  if(estado) qs.push('estado='+estado);
  if(sev) qs.push('severidad='+sev);
  var url = '/api/aseguramiento/cambios' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('cam-kp-tot').textContent = k.total || 0;
    document.getElementById('cam-kp-sin').textContent = k.sin_evaluar || 0;
    document.getElementById('cam-kp-eva').textContent = k.en_evaluacion || 0;
    document.getElementById('cam-kp-apr').textContent = k.aprobados_pendientes || 0;
    document.getElementById('cam-kp-inv').textContent = k.requieren_invima || 0;
    document.getElementById('cam-kp-cer').textContent = k.cerrados_30d || 0;
    var tb = document.getElementById('cam-tbody');
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="9" class="empty">Sin solicitudes de cambio</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var sevBadge = it.severidad === 'mayor' ? '<span class="badge badge-prox">mayor</span>'
        : it.severidad === 'menor' ? '<span class="badge badge-bor">menor</span>'
        : '<span style="color:#94a3b8;font-size:0.78em">—</span>';
      var estadoLabel = (it.estado||'').replace('_',' ');
      var estadoCol = it.estado === 'cerrado' ? '#15803d'
        : it.estado === 'rechazado' ? '#94a3b8'
        : it.estado === 'solicitado' ? '#ef4444'
        : it.estado === 'implementado' ? '#0ea5e9'
        : '#fbbf24';
      var invimaIcon = it.requiere_invima ? '<span title="Requiere INVIMA" style="color:#c2410c">⚠</span>' : '';
      var bpmIcon = it.impacto_bpm ? '<span title="Impacta BPM" style="color:#a16207">●</span> ' : '';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.fecha_solicitud||'')+'</td>'
        +'<td>'+_esc(it.tipo||'')+'</td>'
        +'<td>'+bpmIcon+_esc((it.titulo||'').slice(0,80))+(it.titulo && it.titulo.length > 80 ? '...' : '')+'</td>'
        +'<td>'+sevBadge+'</td>'
        +'<td><span style="color:'+estadoCol+';font-weight:600;font-size:0.85em">'+_esc(estadoLabel)+'</span></td>'
        +'<td>'+invimaIcon+'</td>'
        +'<td>'+(it.dias_abierto||0)+'d</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verCambio('+it.id+')">Abrir</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('cam-tbody').innerHTML = '<tr><td colspan="9" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function abrirNuevoCambio(){
  ['m-cam-titulo','m-cam-desc','m-cam-just','m-cam-areas','m-cam-new-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-cam-bpm').checked = false;
  document.getElementById('m-cam-reg').checked = false;
  document.getElementById('m-cam-tipo').value = 'otro';
  openModal('m-cam-new');
}

async function guardarCambio(){
  var msg = document.getElementById('m-cam-new-msg');
  var body = {
    tipo: document.getElementById('m-cam-tipo').value,
    titulo: document.getElementById('m-cam-titulo').value,
    descripcion: document.getElementById('m-cam-desc').value,
    justificacion: document.getElementById('m-cam-just').value,
    areas_afectadas: document.getElementById('m-cam-areas').value,
    impacto_bpm: document.getElementById('m-cam-bpm').checked,
    impacto_regulatorio: document.getElementById('m-cam-reg').checked,
  };
  if(!body.titulo || body.titulo.length < 5){
    msg.innerHTML = '<span style="color:#ef4444">Título requerido (≥5 chars)</span>'; return;
  }
  if(!body.descripcion || body.descripcion.length < 20){
    msg.innerHTML = '<span style="color:#ef4444">Descripción requerida (≥20 chars)</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/cambios', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.codigo)+' creada</span>';
      setTimeout(function(){ closeModal('m-cam-new'); loadCambios(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function verCambio(id){
  document.getElementById('m-cam-det-id').value = id;
  var body = document.getElementById('m-cam-det-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-cam-det');
  try{
    var r = await fetch('/api/aseguramiento/cambios/'+id);
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    document.getElementById('m-cam-det-title').textContent = d.codigo + ' · ' + (d.estado||'').replace('_',' ');

    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.85em;color:#475569"><b>Solicitada:</b> '+_esc(d.fecha_solicitud||'')+' · por '+_esc(d.solicitado_por||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Tipo:</b> '+_esc(d.tipo||'')+(d.areas_afectadas ? ' · <b>Áreas:</b> '+_esc(d.areas_afectadas) : '')+'</div>'
      +'<div style="margin-top:8px;font-weight:600">'+_esc(d.titulo||'')+'</div>'
      +'<div style="margin-top:6px"><b>Descripción:</b><br>'+_esc(d.descripcion||'')+'</div>'
      +(d.justificacion ? '<div style="margin-top:6px"><b>Justificación:</b><br>'+_esc(d.justificacion)+'</div>' : '')
      +(d.impacto_bpm || d.impacto_regulatorio ? '<div style="margin-top:6px;color:#c2410c">'
          +(d.impacto_bpm?'⚠ Impacta BPM ':'')
          +(d.impacto_regulatorio?'⚠ Impacto regulatorio':'')+'</div>' : '')
      +'</div>';

    // Workflow steps
    html += '<div class="card-title" style="margin-top:12px">Workflow</div>';

    // Paso 1: Evaluación
    if(d.severidad){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>1. Evaluada</b> · severidad: <b>'+_esc(d.severidad)+'</b>'+(d.requiere_invima?' · <span style="color:#c2410c">REQUIERE INVIMA</span>':'')+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.evaluacion_descripcion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.evaluado_por||'')+' · '+_esc(d.evaluado_at||'')+'</div>'
        +'</div>';
    } else {
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>1. Evaluar impacto</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">'
        +'<select id="ev-sev" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">Severidad...</option><option value="mayor">Mayor</option><option value="menor">Menor</option></select>'
        +'<label style="display:flex;align-items:center;gap:4px;font-size:0.85em"><input type="checkbox" id="ev-invima"> Requiere INVIMA</label>'
        +'</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Evaluación de impacto (≥20 chars)</label><textarea id="ev-desc" style="min-height:50px"></textarea></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="evaluarCambio('+id+')">Registrar evaluación</button></div>'
        +'</div>';
    }

    // Paso 2: Aprobación
    if(d.aprobado_at){
      var apCol = d.estado === 'rechazado' ? '#94a3b8' : '#15803d';
      var apLabel = d.estado === 'rechazado' ? 'Rechazado' : 'Aprobado';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+apCol+'">'
        +'<div><b>2. '+apLabel+'</b> por '+_esc(d.aprobado_por||'')+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.aprobacion_observaciones||'')+'</div>'
        +(d.plan_implementacion ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Plan:</b> '+_esc(d.plan_implementacion)+'</div>' : '')
        +(d.fecha_implementacion_propuesta ? '<div style="font-size:0.78em;color:#94a3b8">Fecha propuesta: '+_esc(d.fecha_implementacion_propuesta)+(d.responsable_implementacion?' · Resp: '+_esc(d.responsable_implementacion):'')+'</div>' : '')
        +'</div>';
    } else if(d.severidad){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>2. Aprobar / Rechazar</b> (pendiente)</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Decisión</label>'
        +'<select id="ap-decision" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px;width:auto"><option value="aprobar">Aprobar</option><option value="rechazar">Rechazar</option></select>'
        +'</div>'
        +'<div class="form-group"><label>Observaciones (≥10 chars)</label><textarea id="ap-obs" style="min-height:40px"></textarea></div>'
        +'<div class="form-group"><label>Plan de implementación (≥20 chars · solo si aprueba)</label><textarea id="ap-plan" style="min-height:50px"></textarea></div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        +'<input id="ap-fecha" type="date" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'<input id="ap-resp" placeholder="Responsable implementación" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="aprobarCambio('+id+')">Decidir</button></div>'
        +'</div>';
    }

    // Paso 2b: Notificación INVIMA (si aplica)
    if(d.requiere_invima && d.estado !== 'rechazado'){
      if(d.notificacion_invima_at){
        html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
          +'<div><b>2b. INVIMA notificado</b> · ref: <code>'+_esc(d.notificacion_invima_ref||'')+'</code></div>'
          +'<div style="font-size:0.78em;color:#94a3b8">'+_esc(d.notificacion_invima_at||'')+'</div>'
          +'</div>';
      } else if(d.aprobado_at && d.estado !== 'rechazado'){
        html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
          +'<div><b>2b. Notificar a INVIMA</b> (Resolución 2214/2021)</div>'
          +'<div class="form-group" style="margin-top:6px"><label>Radicado / oficio</label><input id="inv-ref" placeholder="Ej: 2026123456"></div>'
          +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="notificarInvima('+id+')">Registrar notificación</button></div>'
          +'</div>';
      }
    }

    // Paso 3: Implementación
    if(d.implementado_at){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>3. Implementado</b> por '+_esc(d.implementado_por||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">'+_esc(d.implementado_at||'')+'</div>'
        +'</div>';
    } else if(d.estado === 'aprobado' || d.estado === 'en_implementacion'){
      var bloqInvima = d.requiere_invima && !d.notificacion_invima_at;
      html += '<div class="card" style="background:'+(bloqInvima?'#f3f4f6':'#fefce8')+';border-left:3px solid '+(bloqInvima?'#94a3b8':'#fbbf24')+'">'
        +'<div><b>3. Implementar cambio</b>'+(bloqInvima?' <span style="color:#94a3b8">(notifica INVIMA primero)</span>':'')+'</div>'
        +(bloqInvima?'':'<div class="form-group" style="margin-top:6px"><label>Observaciones implementación</label><input id="imp-obs"></div>'
          +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="implementarCambio('+id+')">Marcar implementado</button></div>')
        +'</div>';
    }

    // Paso 4: Cierre
    if(d.estado === 'cerrado'){
      var vfCol = d.verificacion_ok ? '#15803d' : '#ef4444';
      var vfLabel = d.verificacion_ok ? '✅ VERIFICACIÓN OK' : '❌ VERIFICACIÓN NO OK';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+vfCol+'">'
        +'<div style="font-size:1em;font-weight:700;color:'+vfCol+'">'+vfLabel+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Verificación post:</b> '+_esc(d.verificacion_post||'')+'</div>'
        +(d.observaciones_cierre ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Observaciones:</b> '+_esc(d.observaciones_cierre)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Cerrada '+_esc(d.fecha_cierre||'')+' por '+_esc(d.cerrado_por||'')+'</div>'
        +'</div>';
    } else if(d.estado === 'implementado'){
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>4. Cerrar con verificación post</b></div>'
        +'<div class="form-group"><label>Verificación post (≥20 chars)</label><textarea id="cer-cam-verif" style="min-height:50px" placeholder="Cómo se verificó que el cambio funcionó"></textarea></div>'
        +'<div class="form-group"><label><input type="checkbox" id="cer-cam-ok"> Verificación OK</label></div>'
        +'<div class="form-group"><label>Observaciones cierre</label><input id="cer-cam-obs"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="cerrarCambio('+id+')">Cerrar cambio</button></div>'
        +'</div>';
    }

    // Timeline
    if(d.timeline && d.timeline.length){
      html += '<div class="card-title" style="margin-top:12px">Timeline</div>';
      html += '<div style="font-size:0.85em">';
      d.timeline.forEach(function(ev){
        html += '<div style="border-left:2px solid #cbd5e1;padding:4px 0 4px 10px;margin-bottom:4px">'
          +'<div style="font-weight:600">'+_esc(ev.evento_tipo)+(ev.estado_anterior ? ' · '+_esc(ev.estado_anterior)+'→'+_esc(ev.estado_nuevo) : '')+'</div>'
          +'<div style="color:#475569">'+_esc(ev.comentario||'')+'</div>'
          +'<div style="color:#94a3b8;font-size:0.85em">'+_esc(ev.usuario||'')+' · '+_esc(ev.creado_en||'')+'</div>'
          +'</div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

async function evaluarCambio(id){
  var sev = document.getElementById('ev-sev').value;
  var inv = document.getElementById('ev-invima').checked;
  var desc = document.getElementById('ev-desc').value;
  if(!sev){ alert('Elige severidad'); return; }
  if(!desc || desc.length < 20){ alert('Evaluación ≥20 chars'); return; }
  await _postCambioAccion(id, 'evaluar', {severidad: sev, evaluacion_descripcion: desc, requiere_invima: inv});
}

async function aprobarCambio(id){
  var dec = document.getElementById('ap-decision').value;
  var obs = document.getElementById('ap-obs').value;
  var plan = document.getElementById('ap-plan').value;
  var fecha = document.getElementById('ap-fecha').value;
  var resp = document.getElementById('ap-resp').value;
  if(!obs || obs.length < 10){ alert('Observaciones ≥10 chars'); return; }
  if(dec === 'aprobar' && (!plan || plan.length < 20)){ alert('Plan implementación ≥20 chars si aprueba'); return; }
  if(!confirm('Confirmas '+(dec === 'aprobar' ? 'APROBAR' : 'RECHAZAR')+' este cambio?')) return;
  await _postCambioAccion(id, 'aprobar', {
    decision: dec, observaciones: obs, plan_implementacion: plan,
    fecha_implementacion_propuesta: fecha, responsable_implementacion: resp,
  });
}

async function notificarInvima(id){
  var ref = document.getElementById('inv-ref').value;
  if(!ref){ alert('Referencia requerida'); return; }
  await _postCambioAccion(id, 'notificar-invima', {referencia: ref});
}

async function implementarCambio(id){
  var obs = (document.getElementById('imp-obs')||{}).value || '';
  if(!confirm('Confirmas que el cambio fue implementado?')) return;
  await _postCambioAccion(id, 'implementar', {observaciones: obs});
}

async function cerrarCambio(id){
  var verif = document.getElementById('cer-cam-verif').value;
  var ok = document.getElementById('cer-cam-ok').checked;
  var obs = document.getElementById('cer-cam-obs').value;
  if(!verif || verif.length < 20){ alert('Verificación post ≥20 chars'); return; }
  if(!confirm('Confirmas cerrar este cambio con verificación ' + (ok ? 'OK' : 'NO OK') + '?')) return;
  await _postCambioAccion(id, 'cerrar', {verificacion_post: verif, verificacion_ok: ok, observaciones_cierre: obs});
}

async function _postCambioAccion(id, accion, body){ return _postWorkflowAccion('cambios', id, accion, body); }

// === QUEJAS DE CLIENTES (ASG-PRO-013) ==================================
async function loadQuejas(){
  var estado = document.getElementById('qc-f-estado').value;
  var sev = document.getElementById('qc-f-sev').value;
  var qs = [];
  if(estado) qs.push('estado='+estado);
  if(sev) qs.push('severidad='+sev);
  var url = '/api/aseguramiento/quejas' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('qc-kp-tot').textContent = k.total || 0;
    document.getElementById('qc-kp-nue').textContent = k.nuevas || 0;
    document.getElementById('qc-kp-inv').textContent = k.en_investigacion || 0;
    document.getElementById('qc-kp-pen').textContent = k.pendientes_cierre || 0;
    document.getElementById('qc-kp-crit').textContent = k.criticas_abiertas || 0;
    document.getElementById('qc-kp-cer').textContent = k.cerradas_30d || 0;
    var tb = document.getElementById('qc-tbody');
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="10" class="empty">Sin quejas</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var sevBadge = it.severidad === 'critica' ? '<span class="badge badge-venc">crítica</span>'
        : it.severidad === 'mayor' ? '<span class="badge badge-prox">mayor</span>'
        : it.severidad === 'menor' ? '<span class="badge badge-bor">menor</span>'
        : it.severidad === 'informativa' ? '<span class="badge badge-obs">info</span>'
        : '<span style="color:#94a3b8;font-size:0.78em">—</span>';
      var estadoLabel = (it.estado||'').replace('_',' ');
      var estadoCol = it.estado === 'cerrada' ? '#15803d'
        : it.estado === 'rechazada' ? '#94a3b8'
        : it.estado === 'nueva' ? '#ef4444'
        : it.estado === 'respondida' ? '#0ea5e9'
        : '#fbbf24';
      var saludIcon = it.impacto_salud ? '<span title="Impacto salud" style="color:#ef4444">⚠</span> ' : '';
      var recallIcon = it.requiere_recall ? '<span title="Recall" style="color:#c2410c">●</span> ' : '';
      var prodLote = (it.producto||'') + (it.lote ? ' / '+it.lote : '');
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.fecha_recepcion||'')+'</td>'
        +'<td>'+_esc(it.canal||'')+'</td>'
        +'<td>'+saludIcon+recallIcon+_esc((it.cliente_nombre||'').slice(0,40))+'</td>'
        +'<td>'+_esc(prodLote.slice(0,40))+'</td>'
        +'<td>'+_esc(it.tipo_queja||'')+'</td>'
        +'<td>'+sevBadge+'</td>'
        +'<td><span style="color:'+estadoCol+';font-weight:600;font-size:0.85em">'+_esc(estadoLabel)+'</span></td>'
        +'<td>'+(it.dias_abierta||0)+'d</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verQueja('+it.id+')">Abrir</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('qc-tbody').innerHTML = '<tr><td colspan="10" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function abrirNuevaQueja(){
  ['m-qc-cli-nom','m-qc-cli-cont','m-qc-prod','m-qc-lote','m-qc-fcompra',
   'm-qc-est','m-qc-desc','m-qc-new-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-qc-canal').value = 'otro';
  document.getElementById('m-qc-tipo').value = 'otro';
  document.getElementById('m-qc-cli-tipo').value = '';
  document.getElementById('m-qc-salud').checked = false;
  openModal('m-qc-new');
}

async function guardarQueja(){
  var msg = document.getElementById('m-qc-new-msg');
  var body = {
    canal: document.getElementById('m-qc-canal').value,
    tipo_queja: document.getElementById('m-qc-tipo').value,
    cliente_nombre: document.getElementById('m-qc-cli-nom').value,
    cliente_contacto: document.getElementById('m-qc-cli-cont').value,
    cliente_tipo: document.getElementById('m-qc-cli-tipo').value || null,
    producto: document.getElementById('m-qc-prod').value,
    lote: document.getElementById('m-qc-lote').value,
    fecha_compra: document.getElementById('m-qc-fcompra').value || null,
    establecimiento_compra: document.getElementById('m-qc-est').value,
    descripcion: document.getElementById('m-qc-desc').value,
    impacto_salud: document.getElementById('m-qc-salud').checked,
  };
  if(!body.cliente_nombre){ msg.innerHTML = '<span style="color:#ef4444">Cliente requerido</span>'; return; }
  if(!body.descripcion || body.descripcion.length < 10){
    msg.innerHTML = '<span style="color:#ef4444">Descripción ≥10 chars</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/quejas', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.codigo)+' registrada</span>';
      setTimeout(function(){ closeModal('m-qc-new'); loadQuejas(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function verQueja(id){
  document.getElementById('m-qc-det-id').value = id;
  var body = document.getElementById('m-qc-det-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-qc-det');
  try{
    var r = await fetch('/api/aseguramiento/quejas/'+id);
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    document.getElementById('m-qc-det-title').textContent = d.codigo + ' · ' + (d.estado||'').replace('_',' ');

    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.85em;color:#475569"><b>Recibida:</b> '+_esc(d.fecha_recepcion||'')+' vía <b>'+_esc(d.canal||'')+'</b> · por '+_esc(d.recibido_por||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Cliente:</b> '+_esc(d.cliente_nombre||'')+(d.cliente_contacto?' · '+_esc(d.cliente_contacto):'')+(d.cliente_tipo?' ['+_esc(d.cliente_tipo)+']':'')+'</div>'
      +(d.producto || d.lote ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Producto:</b> '+_esc(d.producto||'')+(d.lote?' · Lote '+_esc(d.lote):'')+(d.fecha_compra?' · compra '+_esc(d.fecha_compra):'')+'</div>' : '')
      +'<div style="margin-top:8px"><b>Tipo:</b> '+_esc(d.tipo_queja||'')+'</div>'
      +'<div style="margin-top:6px"><b>Descripción:</b><br>'+_esc(d.descripcion||'')+'</div>'
      +(d.impacto_salud ? '<div style="margin-top:6px;color:#ef4444">⚠ <b>IMPACTO EN SALUD declarado</b></div>' : '')
      +'</div>';

    // Workflow steps
    html += '<div class="card-title" style="margin-top:12px">Workflow</div>';

    // Paso 1: Triaje
    if(d.severidad){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>1. Triada</b> · severidad: <b>'+_esc(d.severidad)+'</b>'
        +(d.requiere_desviacion?' · <span style="color:#c2410c">requiere desviación</span>':'')
        +(d.requiere_recall?' · <span style="color:#c2410c">RECALL</span>':'')+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.triaje_descripcion||'')+'</div>'
        +(d.desviacion_id ? '<div style="font-size:0.85em;margin-top:6px"><b>📢 Desviación enlazada:</b> <a href="javascript:void(0)" onclick="closeModal(\'m-qc-det\');goTab(\'tab-desv\');setTimeout(function(){verDesviacion('+d.desviacion_id+')},300)" style="color:#0ea5e9">abrir DESV-#'+d.desviacion_id+' →</a></div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.triaje_por||'')+' · '+_esc(d.triaje_at||'')+'</div>'
        +'</div>';
    } else {
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>1. Triaje</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">'
        +'<select id="qc-tr-sev" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">Severidad...</option><option value="critica">Crítica</option><option value="mayor">Mayor</option><option value="menor">Menor</option><option value="informativa">Informativa</option></select>'
        +'<div style="display:flex;gap:8px;align-items:center;font-size:0.85em"><label><input type="checkbox" id="qc-tr-desv"> Crear desviación</label><label><input type="checkbox" id="qc-tr-recall"> Recall</label></div>'
        +'</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Análisis triaje (≥10 chars)</label><textarea id="qc-tr-desc" style="min-height:50px"></textarea></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="triarQueja('+id+')">Registrar triaje</button></div>'
        +'</div>';
    }

    // Paso 2: Investigación
    if(d.causa_raiz){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>2. Investigada</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Causa raíz:</b><br>'+_esc(d.causa_raiz||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.investigacion_por||'')+' · '+_esc(d.investigacion_at||'')+'</div>'
        +'</div>';
    } else if(d.severidad){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>2. Investigar causa raíz</b> (pendiente)</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Causa raíz (≥20 chars)</label><textarea id="qc-inv-causa" style="min-height:50px"></textarea></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="investigarQueja('+id+')">Registrar investigación</button></div>'
        +'</div>';
    }

    // Paso 3: Respuesta al cliente
    if(d.respuesta_descripcion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>3. Cliente respondido</b> vía <b>'+_esc(d.respuesta_canal||'')+'</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.respuesta_descripcion||'')+'</div>'
        +(d.fecha_compromiso ? '<div style="font-size:0.78em;color:#94a3b8">Compromiso: '+_esc(d.fecha_compromiso)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.respondido_por||'')+' · '+_esc(d.respondido_at||'')+'</div>'
        +'</div>';
    } else if(d.causa_raiz){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>3. Responder al cliente</b> (pendiente)</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Canal de respuesta</label>'
        +'<select id="qc-r-canal" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px;width:auto"><option value="email">Email</option><option value="telefono">Teléfono</option><option value="whatsapp">WhatsApp</option><option value="presencial">Presencial</option><option value="carta">Carta</option><option value="formulario_web">Formulario web</option><option value="otro">Otro</option></select>'
        +'</div>'
        +'<div class="form-group"><label>Respuesta al cliente (≥20 chars)</label><textarea id="qc-r-desc" style="min-height:60px"></textarea></div>'
        +'<div class="form-group"><label>Fecha compromiso (opcional)</label><input id="qc-r-comp" type="date"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="responderQueja('+id+')">Marcar respondido</button></div>'
        +'</div>';
    }

    // Paso 4: Cierre
    if(d.estado === 'cerrada'){
      var satCol = d.cliente_satisfecho ? '#15803d' : '#ef4444';
      var satLabel = d.cliente_satisfecho ? '✅ CLIENTE SATISFECHO' : '❌ CLIENTE NO SATISFECHO';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+satCol+'">'
        +'<div style="font-size:1em;font-weight:700;color:'+satCol+'">'+satLabel+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Acción correctiva:</b> '+_esc(d.accion_correctiva||'')+'</div>'
        +(d.observaciones_cierre ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Observaciones:</b> '+_esc(d.observaciones_cierre)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Cerrada '+_esc(d.fecha_cierre||'')+' por '+_esc(d.cerrado_por||'')+'</div>'
        +'</div>';
    } else if(d.estado === 'respondida'){
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>4. Cerrar con análisis efectividad</b></div>'
        +'<div class="form-group"><label>Acción correctiva tomada (≥20 chars)</label><textarea id="qc-c-accion" style="min-height:50px"></textarea></div>'
        +'<div class="form-group"><label><input type="checkbox" id="qc-c-sat"> Cliente satisfecho</label></div>'
        +'<div class="form-group"><label>Observaciones cierre</label><input id="qc-c-obs"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="cerrarQueja('+id+')">Cerrar queja</button></div>'
        +'</div>';
    }

    // Timeline
    if(d.timeline && d.timeline.length){
      html += '<div class="card-title" style="margin-top:12px">Timeline</div>';
      html += '<div style="font-size:0.85em">';
      d.timeline.forEach(function(ev){
        html += '<div style="border-left:2px solid #cbd5e1;padding:4px 0 4px 10px;margin-bottom:4px">'
          +'<div style="font-weight:600">'+_esc(ev.evento_tipo)+(ev.estado_anterior ? ' · '+_esc(ev.estado_anterior)+'→'+_esc(ev.estado_nuevo) : '')+'</div>'
          +'<div style="color:#475569">'+_esc(ev.comentario||'')+'</div>'
          +'<div style="color:#94a3b8;font-size:0.85em">'+_esc(ev.usuario||'')+' · '+_esc(ev.creado_en||'')+'</div>'
          +'</div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

async function triarQueja(id){
  var sev = document.getElementById('qc-tr-sev').value;
  var desv = document.getElementById('qc-tr-desv').checked;
  var recall = document.getElementById('qc-tr-recall').checked;
  var desc = document.getElementById('qc-tr-desc').value;
  if(!sev){ alert('Elige severidad'); return; }
  if(!desc || desc.length < 10){ alert('Análisis ≥10 chars'); return; }
  // Llamada directa para capturar respuesta con desviacion_codigo
  try{
    var r = await fetch('/api/aseguramiento/quejas/'+id+'/triaje', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({severidad: sev, triaje_descripcion: desc,
                              requiere_desviacion: desv, requiere_recall: recall}),
    });
    var d = await r.json();
    if(d.ok){
      if(d.desviacion_codigo){
        alert('✅ Triaje OK · Desviación auto-creada: '+d.desviacion_codigo);
      }
      verQueja(id); loadQuejas();
    } else { alert('Error: '+(d.error||'?')); }
  }catch(e){ alert('Error red: '+e.message); }
}

async function investigarQueja(id){
  var causa = document.getElementById('qc-inv-causa').value;
  if(!causa || causa.length < 20){ alert('Causa raíz ≥20 chars'); return; }
  await _postQuejaAccion(id, 'investigar', {causa_raiz: causa});
}

async function responderQueja(id){
  var canal = document.getElementById('qc-r-canal').value;
  var desc = document.getElementById('qc-r-desc').value;
  var comp = document.getElementById('qc-r-comp').value;
  if(!desc || desc.length < 20){ alert('Respuesta ≥20 chars'); return; }
  await _postQuejaAccion(id, 'responder', {respuesta_canal: canal, respuesta_descripcion: desc, fecha_compromiso: comp || null});
}

async function cerrarQueja(id){
  var accion = document.getElementById('qc-c-accion').value;
  var sat = document.getElementById('qc-c-sat').checked;
  var obs = document.getElementById('qc-c-obs').value;
  if(!accion || accion.length < 20){ alert('Acción correctiva ≥20 chars'); return; }
  if(!confirm('Confirmas cerrar esta queja con cliente ' + (sat ? 'satisfecho' : 'NO satisfecho') + '?')) return;
  await _postQuejaAccion(id, 'cerrar', {cliente_satisfecho: sat, accion_correctiva: accion, observaciones_cierre: obs});
}

async function _postQuejaAccion(id, accion, body){ return _postWorkflowAccion('quejas', id, accion, body); }

// === RECALL (ASG-PRO-004) =============================================
async function loadRecalls(){
  var estado = document.getElementById('rcl-f-estado').value;
  var clase = document.getElementById('rcl-f-clase').value;
  var qs = [];
  if(estado) qs.push('estado='+estado);
  if(clase) qs.push('clase='+clase);
  var url = '/api/aseguramiento/recalls' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('rcl-kp-tot').textContent = k.total || 0;
    document.getElementById('rcl-kp-sin').textContent = k.sin_clasificar || 0;
    document.getElementById('rcl-kp-c1').textContent = k.clase_I_abiertos || 0;
    document.getElementById('rcl-kp-inv').textContent = k.invima_pendiente || 0;
    document.getElementById('rcl-kp-rec').textContent = k.en_recoleccion || 0;
    document.getElementById('rcl-kp-cer').textContent = k.cerrados_30d || 0;
    var tb = document.getElementById('rcl-tbody');
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="10" class="empty">Sin recalls (lo cual es bueno 🙏)</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var claseBadge = it.clase_recall === 'clase_I' ? '<span class="badge badge-venc">CLASE I</span>'
        : it.clase_recall === 'clase_II' ? '<span class="badge badge-prox">Clase II</span>'
        : it.clase_recall === 'clase_III' ? '<span class="badge badge-bor">Clase III</span>'
        : '<span style="color:#94a3b8;font-size:0.78em">—</span>';
      var estadoLabel = (it.estado||'').replace(/_/g,' ');
      var estadoCol = it.estado === 'cerrado' ? '#15803d'
        : it.estado === 'cancelado' ? '#94a3b8'
        : it.estado === 'iniciado' ? '#ef4444'
        : it.estado === 'completado' ? '#0ea5e9'
        : '#fbbf24';
      var invimaIcon = it.notificacion_invima_at
        ? '<span title="INVIMA notificado" style="color:#15803d">✓</span>'
        : '<span title="INVIMA pendiente" style="color:#ef4444">✗</span>';
      var prodLote = (it.producto||'') + (it.lotes_afectados ? ' / '+it.lotes_afectados.slice(0,30) : '');
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.fecha_inicio||'')+'</td>'
        +'<td>'+_esc(prodLote.slice(0,60))+'</td>'
        +'<td>'+_esc((it.origen||'').replace(/_/g,' '))+'</td>'
        +'<td>'+claseBadge+'</td>'
        +'<td>'+_esc(it.alcance_geografico||'—')+'</td>'
        +'<td><span style="color:'+estadoCol+';font-weight:600;font-size:0.85em">'+_esc(estadoLabel)+'</span></td>'
        +'<td>'+invimaIcon+'</td>'
        +'<td>'+(it.dias_abierto||0)+'d</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verRecall('+it.id+')">Abrir</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('rcl-tbody').innerHTML = '<tr><td colspan="10" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function abrirNuevoRecall(){
  if(!confirm('Iniciar recall es una decisión grave que activa notificaciones inmediatas. ¿Confirmas que el producto en mercado representa riesgo y debes retirarlo?')) return;
  ['m-rcl-origen-ref','m-rcl-prod','m-rcl-lotes','m-rcl-fab','m-rcl-dist',
   'm-rcl-motivo','m-rcl-riesgo','m-rcl-new-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-rcl-origen').value = 'otro';
  openModal('m-rcl-new');
}

async function guardarRecall(){
  var msg = document.getElementById('m-rcl-new-msg');
  var body = {
    origen: document.getElementById('m-rcl-origen').value,
    origen_referencia: document.getElementById('m-rcl-origen-ref').value,
    producto: document.getElementById('m-rcl-prod').value,
    lotes_afectados: document.getElementById('m-rcl-lotes').value,
    cantidad_fabricada: parseInt(document.getElementById('m-rcl-fab').value) || null,
    cantidad_distribuida: parseInt(document.getElementById('m-rcl-dist').value) || null,
    motivo: document.getElementById('m-rcl-motivo').value,
    riesgo_descripcion: document.getElementById('m-rcl-riesgo').value,
  };
  if(!body.producto){ msg.innerHTML = '<span style="color:#ef4444">Producto requerido</span>'; return; }
  if(!body.lotes_afectados){ msg.innerHTML = '<span style="color:#ef4444">Lotes requeridos</span>'; return; }
  if(!body.motivo || body.motivo.length < 20){ msg.innerHTML = '<span style="color:#ef4444">Motivo ≥20 chars</span>'; return; }
  msg.innerHTML = '<span style="color:#64748b">Iniciando recall...</span>';
  try{
    var r = await fetch('/api/aseguramiento/recalls', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.codigo)+' iniciado</span>';
      setTimeout(function(){ closeModal('m-rcl-new'); loadRecalls(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function verRecall(id){
  document.getElementById('m-rcl-det-id').value = id;
  var body = document.getElementById('m-rcl-det-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-rcl-det');
  try{
    var r = await fetch('/api/aseguramiento/recalls/'+id);
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    document.getElementById('m-rcl-det-title').textContent = d.codigo + ' · ' + (d.estado||'').replace(/_/g,' ');

    var html = '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
      +'<div style="font-size:0.85em;color:#991b1b"><b>Iniciado:</b> '+_esc(d.fecha_inicio||'')+' por '+_esc(d.iniciado_por||'')+'</div>'
      +'<div style="font-size:0.85em;color:#991b1b;margin-top:4px"><b>Origen:</b> '+_esc((d.origen||'').replace(/_/g,' '))+(d.origen_referencia?' · ref: '+_esc(d.origen_referencia):'')+'</div>'
      +'<div style="margin-top:8px;font-weight:700">'+_esc(d.producto||'')+'</div>'
      +'<div style="font-size:0.9em;margin-top:4px"><b>Lotes:</b> '+_esc(d.lotes_afectados||'')+'</div>'
      +(d.cantidad_fabricada || d.cantidad_distribuida ? '<div style="font-size:0.85em;color:#475569;margin-top:4px">Fabricado: '+(d.cantidad_fabricada||'?')+' uds · Distribuido: '+(d.cantidad_distribuida||'?')+' uds</div>' : '')
      +'<div style="margin-top:8px"><b>Motivo:</b><br>'+_esc(d.motivo||'')+'</div>'
      +(d.riesgo_descripcion ? '<div style="margin-top:6px"><b>Riesgo:</b><br>'+_esc(d.riesgo_descripcion)+'</div>' : '')
      +'</div>';

    html += '<div class="card-title" style="margin-top:12px">Workflow</div>';

    // Paso 1: Clasificación
    if(d.clase_recall){
      var claseCol = d.clase_recall === 'clase_I' ? '#ef4444' : '#fbbf24';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+claseCol+'">'
        +'<div><b>1. Clasificado</b> como <b style="color:'+claseCol+'">'+_esc(d.clase_recall.replace('_',' ').toUpperCase())+'</b> · alcance '+_esc(d.alcance_geografico||'')+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.justificacion_clasificacion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.clasificado_por||'')+' · '+_esc(d.clasificado_at||'')+'</div>'
        +'</div>';
    } else {
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>1. Clasificar</b> (URGENTE · pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">'
        +'<select id="rcl-cl-clase" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">Clase...</option><option value="clase_I">Clase I (riesgo grave salud)</option><option value="clase_II">Clase II (temporal/reversible)</option><option value="clase_III">Clase III (improbable daño)</option></select>'
        +'<select id="rcl-cl-alcance" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">Alcance...</option><option value="local">Local</option><option value="regional">Regional</option><option value="nacional">Nacional</option><option value="internacional">Internacional</option></select>'
        +'</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Justificación (≥20 chars)</label><textarea id="rcl-cl-just" style="min-height:50px"></textarea></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="clasificarRecall('+id+')">Clasificar</button></div>'
        +'</div>';
    }

    // Paso 2: Notificación INVIMA
    if(d.notificacion_invima_at){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>2. INVIMA notificado</b> · ref: <code>'+_esc(d.notificacion_invima_ref||'')+'</code></div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.notificacion_invima_por||'')+' · '+_esc(d.notificacion_invima_at||'')+'</div>'
        +'</div>';
    } else if(d.clase_recall){
      var urgente = d.clase_recall === 'clase_I' ? ' <span style="color:#ef4444">⏰ <24h</span>' : '';
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>2. Notificar a INVIMA</b>'+urgente+'</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Radicado / oficio INVIMA</label><input id="rcl-inv-ref" placeholder="Ej: 2026-12345"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="recallNotifInvima('+id+')">Registrar notificación</button></div>'
        +'</div>';
    }

    // Paso 3: Notificación distribuidores
    if(d.notificacion_distribuidores_at){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>3. Distribuidores notificados</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.distribuidores_notificados||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.notificacion_distribuidores_por||'')+' · '+_esc(d.notificacion_distribuidores_at||'')+'</div>'
        +'</div>';
    } else if(d.notificacion_invima_at){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>3. Notificar a distribuidores y retail</b></div>'
        +'<div class="form-group" style="margin-top:6px"><label>Lista distribuidores notificados (≥5 chars)</label><textarea id="rcl-dist-list" style="min-height:50px" placeholder="Distribuidor A, Cadena retail B, ..."></textarea></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="recallNotifDist('+id+')">Marcar notificados</button></div>'
        +'</div>';
    }

    // Paso 4: Recolección
    if(d.recoleccion_completada_at){
      var pct = d.cantidad_distribuida ? Math.round((d.cantidad_recolectada / d.cantidad_distribuida) * 100) : null;
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>4. Recolección completada</b> · '+(d.cantidad_recolectada||0)+' uds'+(pct!==null?' ('+pct+'%)':'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">'+_esc(d.recoleccion_completada_at||'')+'</div>'
        +'</div>';
    } else if(d.notificacion_distribuidores_at){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>4. Recolección del producto</b> '+(d.cantidad_recolectada!==null?' · acumulado '+d.cantidad_recolectada+' uds':'')+'</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;align-items:center">'
        +'<input id="rcl-rec-cant" type="number" min="0" placeholder="Cantidad recolectada total" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'<label style="font-size:0.85em"><input type="checkbox" id="rcl-rec-fin"> Recolección COMPLETA</label>'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="recallRecoleccion('+id+')">Actualizar recolección</button></div>'
        +'</div>';
    }

    // Paso 5: Cierre
    if(d.estado === 'cerrado'){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div style="font-size:1em;font-weight:700;color:#15803d">✅ RECALL CERRADO</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Disposición:</b> '+_esc((d.disposicion_final||'').replace(/_/g,' '))+' · '+_esc(d.disposicion_descripcion||'')+'</div>'
        +(d.efectividad_porcentaje !== null ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Efectividad:</b> '+d.efectividad_porcentaje+'%'+(d.efectividad_descripcion?' · '+_esc(d.efectividad_descripcion):'')+'</div>' : '')
        +(d.observaciones_cierre ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Observaciones:</b> '+_esc(d.observaciones_cierre)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Cerrado '+_esc(d.fecha_cierre||'')+' por '+_esc(d.cerrado_por||'')+'</div>'
        +'</div>';
    } else if(d.estado === 'completado'){
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>5. Cerrar con disposición + efectividad</b></div>'
        +'<div class="form-group"><label>Disposición final</label>'
        +'<select id="rcl-c-disp" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px;width:auto"><option value="destruccion">Destrucción</option><option value="reproceso">Reproceso</option><option value="devolver_proveedor">Devolver a proveedor</option><option value="cuarentena">Cuarentena indefinida</option></select>'
        +'</div>'
        +'<div class="form-group"><label>Descripción disposición (≥20 chars)</label><textarea id="rcl-c-disp-desc" style="min-height:50px"></textarea></div>'
        +'<div style="display:grid;grid-template-columns:1fr 2fr;gap:8px">'
        +'<input id="rcl-c-ef-pct" type="number" min="0" max="100" placeholder="% efectividad" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'<input id="rcl-c-ef-desc" placeholder="Análisis de efectividad" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div class="form-group" style="margin-top:6px"><label>Observaciones cierre</label><input id="rcl-c-obs"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="cerrarRecall('+id+')">Cerrar recall</button></div>'
        +'</div>';
    }

    // Timeline
    if(d.timeline && d.timeline.length){
      html += '<div class="card-title" style="margin-top:12px">Timeline</div>';
      html += '<div style="font-size:0.85em">';
      d.timeline.forEach(function(ev){
        html += '<div style="border-left:2px solid #cbd5e1;padding:4px 0 4px 10px;margin-bottom:4px">'
          +'<div style="font-weight:600">'+_esc(ev.evento_tipo)+(ev.estado_anterior ? ' · '+_esc(ev.estado_anterior)+'→'+_esc(ev.estado_nuevo) : '')+'</div>'
          +'<div style="color:#475569">'+_esc(ev.comentario||'')+'</div>'
          +'<div style="color:#94a3b8;font-size:0.85em">'+_esc(ev.usuario||'')+' · '+_esc(ev.creado_en||'')+'</div>'
          +'</div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

async function clasificarRecall(id){
  var clase = document.getElementById('rcl-cl-clase').value;
  var alcance = document.getElementById('rcl-cl-alcance').value;
  var just = document.getElementById('rcl-cl-just').value;
  if(!clase){ alert('Elige clase'); return; }
  if(!alcance){ alert('Elige alcance'); return; }
  if(!just || just.length < 20){ alert('Justificación ≥20 chars'); return; }
  await _postRecallAccion(id, 'clasificar', {clase_recall: clase, alcance_geografico: alcance, justificacion_clasificacion: just});
}

async function recallNotifInvima(id){
  var ref = document.getElementById('rcl-inv-ref').value;
  if(!ref){ alert('Radicado requerido'); return; }
  await _postRecallAccion(id, 'notificar-invima', {referencia: ref});
}

async function recallNotifDist(id){
  var lista = document.getElementById('rcl-dist-list').value;
  if(!lista || lista.length < 5){ alert('Lista distribuidores requerida'); return; }
  await _postRecallAccion(id, 'notificar-distribuidores', {distribuidores_notificados: lista});
}

async function recallRecoleccion(id){
  var cant = document.getElementById('rcl-rec-cant').value;
  var fin = document.getElementById('rcl-rec-fin').checked;
  if(cant === '' || cant === null){ alert('Cantidad requerida'); return; }
  await _postRecallAccion(id, 'recoleccion', {cantidad_recolectada: parseInt(cant), completa: fin});
}

async function cerrarRecall(id){
  var disp = document.getElementById('rcl-c-disp').value;
  var dispDesc = document.getElementById('rcl-c-disp-desc').value;
  var efPct = document.getElementById('rcl-c-ef-pct').value;
  var efDesc = document.getElementById('rcl-c-ef-desc').value;
  var obs = document.getElementById('rcl-c-obs').value;
  if(!dispDesc || dispDesc.length < 20){ alert('Descripción disposición ≥20 chars'); return; }
  if(!confirm('Confirmas cerrar este recall?')) return;
  await _postRecallAccion(id, 'cerrar', {
    disposicion_final: disp, disposicion_descripcion: dispDesc,
    efectividad_porcentaje: efPct === '' ? null : parseInt(efPct),
    efectividad_descripcion: efDesc, observaciones_cierre: obs,
  });
}

async function _postRecallAccion(id, accion, body){ return _postWorkflowAccion('recalls', id, accion, body); }

async function loadDashboard(){
  try{
    var r = await fetch('/api/aseguramiento/dashboard');
    var d = await r.json();
    var sgd = d.sgd || {};
    var cap = d.capacitaciones || {};
    var dv = d.desviaciones || {};
    var cm = d.cambios || {};
    var qc = d.quejas || {};
    var rcl = d.recalls || {};

    // SGD
    document.getElementById('kp-vig').textContent = sgd.vigentes || 0;
    document.getElementById('kp-prox').textContent = sgd.vencen_30d || 0;
    document.getElementById('kp-venc').textContent = sgd.vencidos || 0;
    document.getElementById('kp-confl').textContent = sgd.conflictos || 0;
    document.getElementById('kp-cap').textContent = cap.pendientes || 0;

    // Workflows
    document.getElementById('kp-desv-tot').textContent = dv.total || 0;
    document.getElementById('kp-desv-crit').textContent = dv.criticas_abiertas || 0;
    document.getElementById('kp-desv-sin').textContent = dv.sin_clasificar || 0;
    document.getElementById('kp-cam-tot').textContent = cm.total || 0;
    document.getElementById('kp-cam-inv').textContent = cm.invima_pendiente || 0;
    document.getElementById('kp-cam-sin').textContent = cm.sin_evaluar || 0;
    document.getElementById('kp-qc-tot').textContent = qc.total || 0;
    document.getElementById('kp-qc-crit').textContent = qc.criticas_abiertas || 0;
    document.getElementById('kp-qc-nue').textContent = qc.nuevas || 0;
    document.getElementById('kp-rcl-tot').textContent = rcl.total || 0;
    document.getElementById('kp-rcl-c1').textContent = rcl.clase_I_abiertos || 0;
    document.getElementById('kp-rcl-inv').textContent = rcl.invima_pendiente || 0;

    // Otros
    document.getElementById('kp-nc').textContent = d.ncs_abiertas || 0;
    document.getElementById('kp-aud').textContent = d.auditorias_60d || 0;

    // Alertas críticas consolidadas
    var alertas = d.alertas_criticas || [];
    var wrap = document.getElementById('dash-alertas-wrap');
    var list = document.getElementById('dash-alertas-list');
    if(alertas.length){
      wrap.style.display = 'block';
      var tipoLabel = {
        'recall_clase_I_sin_invima': '🚨🚨 RECALL CLASE I SIN INVIMA',
        'desviacion_critica_sin_investigar': '⚠ Desviación crítica sin investigar',
        'queja_salud_sin_responder': '⚠ Queja salud sin responder',
        'cambio_invima_pendiente': '⚠ Cambio aprobado · INVIMA pendiente',
      };
      var tabFor = {
        'recalls': 'tab-recalls', 'desviaciones': 'tab-desv',
        'quejas': 'tab-quejas', 'cambios': 'tab-cambios',
      };
      list.innerHTML = alertas.map(function(a){
        var tab = tabFor[a.modulo] || 'tab-dash';
        return '<div style="padding:4px 0;border-top:1px solid #fecaca;cursor:pointer" onclick="goTab(\''+tab+'\')">'
          +'<b>'+_esc(tipoLabel[a.tipo] || a.tipo)+'</b> · <code>'+_esc(a.codigo)+'</code> · '+_esc(a.descripcion)
          +'</div>';
      }).join('');
    } else {
      wrap.style.display = 'none';
    }

    // Resumen áreas vendrá del listado
    var rArea = await fetch('/api/aseguramiento/sgd/listado?estado=vigente');
    var dArea = await rArea.json();
    var areas = dArea.resumen_por_area || {};
    var div = document.getElementById('dash-areas');
    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">';
    Object.keys(areas).sort().forEach(function(a){
      html += '<div style="background:#f8fafc;padding:10px;border-radius:6px;text-align:center">'
        +'<div style="font-size:0.72em;color:#64748b">'+_esc(dArea.areas[a]||a)+'</div>'
        +'<div style="font-size:1.4em;font-weight:700">'+areas[a]+'</div>'
        +'</div>';
    });
    html += '</div>';
    div.innerHTML = Object.keys(areas).length ? html : '<p class="empty">Sin documentos · importa el SGD primero</p>';
  }catch(e){ console.error(e); }
}

async function loadSGD(){
  var area = document.getElementById('sgd-area').value;
  var tipo = document.getElementById('sgd-tipo').value;
  var estado = document.getElementById('sgd-estado').value;
  var q = document.getElementById('sgd-q').value;
  var hijos = document.getElementById('sgd-hijos').checked ? '1' : '0';
  var qs = [];
  if(area) qs.push('area='+area);
  if(tipo) qs.push('tipo_doc='+tipo);
  if(estado) qs.push('estado='+estado);
  if(q) qs.push('q='+encodeURIComponent(q));
  qs.push('incluir_hijos='+hijos);
  try{
    var r = await fetch('/api/aseguramiento/sgd/listado?' + qs.join('&'));
    var d = await r.json();
    document.getElementById('sgd-resumen').textContent = (d.total||0) + ' documentos';
    var tb = document.getElementById('sgd-tbody');
    if(!d.items || d.items.length===0){
      tb.innerHTML = '<tr><td colspan="7" class="empty">Sin documentos</td></tr>';
      return;
    }
    tb.innerHTML = d.items.map(function(it){
      var bcls = 'badge-vig';
      if(it.estado_efectivo==='vencido') bcls='badge-venc';
      else if(it.estado_efectivo==='vence_pronto') bcls='badge-prox';
      else if(it.estado==='obsoleto') bcls='badge-obs';
      else if(it.estado==='conflicto') bcls='badge-confl';
      else if(it.estado==='borrador') bcls='badge-bor';
      var pdfBtn = it.archivo_pdf_url
        ? '<a href="'+_esc(it.archivo_pdf_url)+'" target="_blank" rel="noopener" class="btn btn-ghost btn-sm" title="Abrir PDF">📎</a>'
        : '<button class="btn btn-ghost btn-sm" title="Sin PDF · agregar" onclick="editarPdfSGD(\''+_esc(it.codigo)+'\', \'\')" style="opacity:.5">📎</button>';
      var editPdfBtn = it.archivo_pdf_url
        ? ' <button class="btn btn-ghost btn-sm" onclick="editarPdfSGD(\''+_esc(it.codigo)+'\', \''+_esc(it.archivo_pdf_url)+'\')" title="Editar PDF" style="font-size:0.7em;padding:2px 6px">✎</button>'
        : '';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.titulo||'')+(it.padre_codigo?' <span style="color:#94a3b8;font-size:0.85em">(hijo de '+_esc(it.padre_codigo)+')</span>':'')+'</td>'
        +'<td>'+_esc(it.version_actual||'')+'</td>'
        +'<td><span class="badge '+bcls+'">'+_esc(it.estado_efectivo||it.estado||'')+'</span></td>'
        +'<td>'+_esc(it.proxima_revision||'—')+'</td>'
        +'<td>'+_esc(it.aprobado_por||'')+'</td>'
        +'<td style="white-space:nowrap">'+pdfBtn+editPdfBtn+' <button class="btn btn-ghost btn-sm" onclick="verSGD(\''+_esc(it.codigo)+'\')">Ver</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('sgd-tbody').innerHTML = '<tr><td colspan="7" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function verSGD(codigo){
  var body = document.getElementById('m-sgd-det-body');
  document.getElementById('m-sgd-det-title').textContent = 'Detalle · ' + codigo;
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-sgd-det');
  try{
    var r = await fetch('/api/aseguramiento/sgd/'+encodeURIComponent(codigo));
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.78em;color:#64748b">'+_esc(d.codigo)+' · '+_esc(d.area)+'/'+_esc(d.tipo_doc)+'</div>'
      +'<div style="font-size:1.2em;font-weight:700;margin-top:4px">'+_esc(d.titulo||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:6px">'+_esc(d.descripcion||'')+'</div>'
      +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px;font-size:0.85em">'
      +'<div><b>Versión:</b> '+_esc(d.version_actual||'')+'</div>'
      +'<div><b>Estado:</b> '+_esc(d.estado||'')+'</div>'
      +'<div><b>Vigente desde:</b> '+_esc(d.vigente_desde||'—')+'</div>'
      +'<div><b>Próxima revisión:</b> '+_esc(d.proxima_revision||'—')+'</div>'
      +'<div><b>Elaborado:</b> '+_esc(d.elaborado_por||'—')+'</div>'
      +'<div><b>Revisado:</b> '+_esc(d.revisado_por||'—')+'</div>'
      +'<div><b>Aprobado:</b> '+_esc(d.aprobado_por||'—')+'</div>'
      +(d.archivo_pdf_url ? '<div><b>PDF:</b> <a href="'+_esc(d.archivo_pdf_url)+'" target="_blank">abrir &rarr;</a></div>' : '')
      +'</div>'
      +'</div>';
    if((d.hijos||[]).length>0){
      html += '<div class="card-title" style="margin-top:10px">Formatos hijos ('+d.hijos.length+')</div>';
      html += '<table><thead><tr><th>Código</th><th>Título</th><th>Versión</th><th>Estado</th></tr></thead><tbody>';
      d.hijos.forEach(function(h){
        html += '<tr><td><code>'+_esc(h.codigo)+'</code></td><td>'+_esc(h.titulo||'')+'</td><td>'+_esc(h.version||'')+'</td><td>'+_esc(h.estado||'')+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    if((d.versiones||[]).length>0){
      html += '<div class="card-title" style="margin-top:10px">Histórico de versiones</div>';
      html += '<table><thead><tr><th>Versión</th><th>Aprobada</th><th>Por</th><th>Motivo</th></tr></thead><tbody>';
      d.versiones.forEach(function(v){
        html += '<tr><td><b>'+_esc(v.version)+'</b></td><td>'+_esc(v.fecha_aprobacion||'—')+'</td><td>'+_esc(v.aprobado_por||'—')+'</td><td>'+_esc(v.motivo_cambio||'')+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

function abrirNuevoSGD(){
  ['m-sgd-codigo','m-sgd-titulo','m-sgd-vigente','m-sgd-proxrev','m-sgd-elab','m-sgd-rev','m-sgd-apr','m-sgd-url','m-sgd-obs','m-sgd-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-sgd-version').value = '1';
  document.getElementById('m-sgd-estado').value = 'vigente';
  openModal('m-sgd');
}

async function guardarSGD(){
  var msg = document.getElementById('m-sgd-msg');
  var body = {
    codigo: document.getElementById('m-sgd-codigo').value.trim().toUpperCase(),
    titulo: document.getElementById('m-sgd-titulo').value.trim(),
    version: document.getElementById('m-sgd-version').value || '1',
    estado: document.getElementById('m-sgd-estado').value,
    vigente_desde: document.getElementById('m-sgd-vigente').value || null,
    proxima_revision: document.getElementById('m-sgd-proxrev').value || null,
    elaborado_por: document.getElementById('m-sgd-elab').value || null,
    revisado_por: document.getElementById('m-sgd-rev').value || null,
    aprobado_por: document.getElementById('m-sgd-apr').value || null,
    archivo_pdf_url: document.getElementById('m-sgd-url').value || null,
    observaciones: document.getElementById('m-sgd-obs').value || null,
  };
  if(!body.codigo || !body.titulo){ msg.innerHTML='<span style="color:#ef4444">Código y título requeridos</span>'; return; }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/sgd', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.accion||'guardado')+'</span>';
      setTimeout(function(){ closeModal('m-sgd'); loadSGD(); loadDashboard(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function asignarCap(){
  var msg = document.getElementById('cap-msg');
  var personasRaw = document.getElementById('cap-personas').value || '';
  var personas = personasRaw.split(',').map(function(p){return p.trim().toLowerCase();}).filter(Boolean);
  var body = {
    sgd_codigo: document.getElementById('cap-codigo').value.trim().toUpperCase(),
    sgd_version: document.getElementById('cap-version').value.trim(),
    fecha_limite: document.getElementById('cap-fecha-lim').value || null,
    personas: personas,
  };
  if(!body.sgd_codigo || !body.sgd_version || !personas.length){
    msg.innerHTML = '<span style="color:#ef4444">Código, versión y personas requeridos</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Asignando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+d.asignados+' asignaciones · '+d.saltados_ya_existian+' ya existían</span>';
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

// Tracker de PDFs abiertos en esta sesión (para validar lectura antes de firmar)
function _pdfFueAbierto(codigo, version){
  try { return sessionStorage.getItem('pdf-leido:'+codigo+':'+version) === '1'; }
  catch(e){ return false; }
}
function _marcarPdfAbierto(codigo, version){
  try { sessionStorage.setItem('pdf-leido:'+codigo+':'+version, '1'); } catch(e){}
}

async function loadMisCapacitaciones(){
  var tb = document.getElementById('mis-cap-tbody');
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/mias');
    var d = await r.json();
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="6" class="empty">Sin capacitaciones asignadas</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var btn = '';
      if(it.estado === 'asignada' || it.estado === 'leida'){
        if(it.archivo_pdf_url){
          // 2 pasos: abrir PDF + firmar
          var pdfAbierto = _pdfFueAbierto(it.sgd_codigo, it.sgd_version);
          var firmaBtn = pdfAbierto
            ? '<button class="btn btn-primary btn-sm" onclick="firmarCap(\''+_esc(it.sgd_codigo)+'\',\''+_esc(it.sgd_version)+'\',true)">Firmar lectura</button>'
            : '<button class="btn btn-ghost btn-sm" disabled style="opacity:.5" title="Abre el PDF primero">Firmar lectura</button>';
          btn = '<a href="'+_esc(it.archivo_pdf_url)+'" target="_blank" rel="noopener" class="btn '+(pdfAbierto?'btn-ghost':'btn-primary')+' btn-sm" onclick="_marcarPdfAbierto(\''+_esc(it.sgd_codigo)+'\',\''+_esc(it.sgd_version)+'\');setTimeout(loadMisCapacitaciones,200)">📎 '+(pdfAbierto?'Releer':'1) Abrir PDF')+'</a> '+firmaBtn;
        } else {
          // Sin PDF: solo permitir firmar con warning
          btn = '<button class="btn btn-primary btn-sm" onclick="firmarCap(\''+_esc(it.sgd_codigo)+'\',\''+_esc(it.sgd_version)+'\',false)" title="No hay PDF adjunto">Firmar (sin PDF)</button>';
        }
      } else if(it.estado === 'firmada' || it.estado === 'aprobada'){
        btn = '<span style="color:#15803d">&#x2713; Firmada '+_esc(it.firmado_at||'')+'</span>';
      }
      return '<tr>'
        +'<td><code>'+_esc(it.sgd_codigo)+'</code></td>'
        +'<td>'+_esc(it.sgd_version)+'</td>'
        +'<td>'+_esc(it.titulo||'—')+'</td>'
        +'<td>'+_esc(it.asignado_at||'')+'</td>'
        +'<td><span class="badge badge-bor">'+_esc(it.estado)+'</span></td>'
        +'<td style="white-space:nowrap">'+btn+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="6" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function firmarCap(codigo, version, pdfDisponible){
  var msg = '¿Confirmas que leíste y comprendiste el SOP '+codigo+' v'+version+'?';
  if(!pdfDisponible){
    msg = '⚠ ATENCIÓN: este SOP NO tiene PDF adjunto.\n\n'+msg+'\n\n(Calidad debería adjuntar el PDF antes que firmes)';
  }
  if(!confirm(msg)) return;
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/firmar', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sgd_codigo: codigo, sgd_version: version})});
    var d = await r.json();
    if(d.ok){ alert('Firmada con hash '+d.firma_hash); loadMisCapacitaciones(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

async function editarPdfSGD(codigo, urlActual){
  var url = prompt('URL del PDF para '+codigo+'\n(http://... o https://... · vacío para quitar):', urlActual || '');
  if(url === null) return;  // canceló
  url = (url || '').trim();
  if(url && !url.match(/^https?:\/\//)){ alert('URL debe empezar con http:// o https://'); return; }
  try{
    var r = await fetch('/api/aseguramiento/sgd/'+encodeURIComponent(codigo)+'/pdf', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({archivo_pdf_url: url}),
    });
    var d = await r.json();
    if(d.ok){ alert(url ? '📎 PDF actualizado' : '📎 PDF removido'); loadSGD(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

// === REPORTES INVIMA · audit-trail + trazabilidad ============================
function repInit(){
  // Set defaults: hasta=hoy, desde=hace 30 días si están vacíos
  var hasta = document.getElementById('rep-at-hasta');
  var desde = document.getElementById('rep-at-desde');
  if(hasta && !hasta.value){
    var h = new Date();
    hasta.value = h.toISOString().slice(0,10);
  }
  if(desde && !desde.value){
    var d = new Date(); d.setDate(d.getDate()-30);
    desde.value = d.toISOString().slice(0,10);
  }
}

function repGoTab(subId){
  ['rep-audit','rep-lote','rep-cliente'].forEach(function(id){
    var p = document.getElementById(id);
    if(p) p.style.display = (id===subId ? '' : 'none');
  });
  document.querySelectorAll('.rep-tab').forEach(function(t){
    var active = t.getAttribute('onclick') && t.getAttribute('onclick').indexOf("'"+subId+"'") !== -1;
    t.style.borderBottom = active ? '2px solid #7ACFCC' : 'none';
    t.style.color = active ? '#7ACFCC' : '#94a3b8';
  });
}

async function repAuditCargar(){
  var qs = [];
  var desde = document.getElementById('rep-at-desde').value;
  var hasta = document.getElementById('rep-at-hasta').value;
  var accion = document.getElementById('rep-at-accion').value;
  var usuario = document.getElementById('rep-at-usuario').value.trim();
  if(desde) qs.push('desde='+encodeURIComponent(desde));
  if(hasta) qs.push('hasta='+encodeURIComponent(hasta));
  if(accion) qs.push('accion='+encodeURIComponent(accion));
  if(usuario) qs.push('usuario='+encodeURIComponent(usuario));
  var url = '/api/aseguramiento/reportes/audit-trail' + (qs.length ? '?'+qs.join('&') : '');
  var tb = document.getElementById('rep-at-tbody');
  var info = document.getElementById('rep-at-info');
  tb.innerHTML = '<tr><td colspan="7" class="empty">Cargando...</td></tr>';
  if(info) info.textContent = '';
  try{
    var r = await fetch(url);
    if(r.status === 403){ tb.innerHTML = '<tr><td colspan="7" class="empty">Acceso restringido a Calidad/Admin</td></tr>'; return; }
    var d = await r.json();
    if(!d.items || !d.items.length){
      tb.innerHTML = '<tr><td colspan="7" class="empty">Sin registros para los filtros</td></tr>';
      if(info) info.textContent = 'Total: 0';
      return;
    }
    if(info) info.textContent = 'Total: '+(d.total||d.items.length)+' · Rango '+(d.desde||'')+' → '+(d.hasta||'');
    tb.innerHTML = d.items.map(function(it){
      var det = it.detalle ? String(it.detalle).slice(0,80) : '';
      return '<tr>'
        +'<td style="white-space:nowrap;font-size:0.82em">'+_esc((it.fecha||'').slice(0,19))+'</td>'
        +'<td>'+_esc(it.usuario||'')+'</td>'
        +'<td><code style="font-size:0.78em">'+_esc(it.accion||'')+'</code></td>'
        +'<td style="font-size:0.82em">'+_esc(it.tabla||'—')+'</td>'
        +'<td style="font-size:0.82em">'+_esc(it.registro_id||'—')+'</td>'
        +'<td style="font-size:0.78em;color:#475569">'+_esc(det)+'</td>'
        +'<td style="font-size:0.78em;color:#94a3b8">'+_esc(it.ip||'—')+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="7" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function repAuditExport(){
  var qs = [];
  var desde = document.getElementById('rep-at-desde').value;
  var hasta = document.getElementById('rep-at-hasta').value;
  var accion = document.getElementById('rep-at-accion').value;
  var usuario = document.getElementById('rep-at-usuario').value.trim();
  if(desde) qs.push('desde='+encodeURIComponent(desde));
  if(hasta) qs.push('hasta='+encodeURIComponent(hasta));
  if(accion) qs.push('accion='+encodeURIComponent(accion));
  if(usuario) qs.push('usuario='+encodeURIComponent(usuario));
  var url = '/api/aseguramiento/reportes/audit-trail/csv' + (qs.length ? '?'+qs.join('&') : '');
  window.open(url, '_blank');
}

function _repBadge(n, label, color){
  return '<span style="display:inline-block;padding:3px 8px;border-radius:6px;background:'+color+';color:#fff;font-size:0.78em;font-weight:600;margin-right:6px;margin-bottom:4px">'+_esc(label)+': '+(n||0)+'</span>';
}

function _repSeccion(titulo, items, columnas, formatter){
  var rows = (items||[]).map(formatter).join('');
  if(!rows) rows = '<tr><td colspan="'+columnas.length+'" class="empty" style="font-size:0.82em">Sin registros</td></tr>';
  return '<div style="margin-top:14px"><div style="font-weight:600;margin-bottom:6px;color:#1e293b">'+_esc(titulo)+' ('+(items||[]).length+')</div>'
    +'<div style="overflow-x:auto"><table style="font-size:0.85em"><thead><tr>'
    +columnas.map(function(c){return '<th>'+_esc(c)+'</th>';}).join('')
    +'</tr></thead><tbody>'+rows+'</tbody></table></div></div>';
}

async function repLoteCargar(){
  var lote = document.getElementById('rep-lote-input').value.trim();
  if(!lote || lote.length < 3){ alert('Ingresa código de lote (mín 3 caracteres)'); return; }
  var body = document.getElementById('rep-lote-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  try{
    var r = await fetch('/api/aseguramiento/reportes/lote-trazabilidad/'+encodeURIComponent(lote));
    if(r.status === 403){ body.innerHTML = '<p class="empty">Acceso restringido a Calidad/Admin</p>'; return; }
    if(r.status === 400){ body.innerHTML = '<p class="empty">Lote demasiado corto</p>'; return; }
    var d = await r.json();
    var c = d.cadena || {};
    var rsm = d.resumen || {};
    var html = '<div class="card" style="background:#f8fafc;border-left:4px solid #7ACFCC">'
      +'<div style="font-weight:700;font-size:1.05em;margin-bottom:6px">Lote: <code>'+_esc(d.lote||lote)+'</code></div>'
      +'<div style="font-size:0.82em;color:#64748b;margin-bottom:8px">Consultado por <b>'+_esc(d.consultado_por||'')+'</b> · '+_esc((d.consulta_at||'').slice(0,19))+'</div>'
      +'<div>'
      +_repBadge(rsm.recepciones, 'Recepciones', '#0ea5e9')
      +_repBadge(rsm.producciones, 'Producciones', '#7ACFCC')
      +_repBadge(rsm.coas, 'COAs', '#15803d')
      +_repBadge(rsm.ncs, 'NCs', '#ef4444')
      +_repBadge(rsm.oos, 'OOS', '#f59e0b')
      +_repBadge(rsm.despachos, 'Despachos', '#8b5cf6')
      +_repBadge(rsm.desviaciones, 'Desviaciones', '#dc2626')
      +_repBadge(rsm.recalls, 'Recalls', '#991b1b')
      +'</div></div>';

    html += _repSeccion('📦 Recepciones MP', c.recepciones, ['Fecha','OC','Material','Cantidad','Proveedor','Vence'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td><code style="font-size:0.82em">'+_esc(it.numero_oc||'—')+'</code></td><td>'+_esc(it.material||'')+'</td><td>'+_esc(it.cantidad||'')+'</td><td>'+_esc(it.proveedor||'')+'</td><td>'+_esc((it.fecha_vencimiento||'').slice(0,10))+'</td></tr>';
    });
    html += _repSeccion('🏭 Producciones (uso de este lote)', c.producciones_uso, ['Fecha','Material','Cantidad','Operador','Observaciones'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td>'+_esc(it.material||'')+'</td><td>'+_esc(it.cantidad||'')+'</td><td>'+_esc(it.operador||'—')+'</td><td style="font-size:0.78em">'+_esc((it.observaciones||'').slice(0,80))+'</td></tr>';
    });
    html += _repSeccion('🧪 COAs', c.coas, ['Fecha','Parámetro','Valor','Conforme','Analista','Decisión'], function(it){
      var conforme = it.conforme ? '<span style="color:#15803d">✓</span>' : '<span style="color:#ef4444">✗</span>';
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td>'+_esc(it.parametro||'')+'</td><td>'+_esc(it.valor||'')+'</td><td>'+conforme+'</td><td>'+_esc(it.analista||'—')+'</td><td>'+_esc(it.decision||'—')+'</td></tr>';
    });
    html += _repSeccion('❌ No-conformidades', c.ncs, ['Fecha','Tipo','Descripción','Impacto','Estado'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td>'+_esc(it.tipo||'')+'</td><td>'+_esc((it.descripcion||'').slice(0,80))+'</td><td>'+_esc(it.impacto||'—')+'</td><td>'+_esc(it.estado||'')+'</td></tr>';
    });
    html += _repSeccion('⚠️ OOS', c.oos, ['Código','Fecha','Parámetro','Valor obtenido','Estado'], function(it){
      return '<tr><td><code style="font-size:0.82em">'+_esc(it.codigo||'')+'</code></td><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td>'+_esc(it.parametro||'')+'</td><td>'+_esc(it.valor_obtenido||'')+'</td><td>'+_esc(it.estado||'')+'</td></tr>';
    });
    html += _repSeccion('🚚 Despachos a clientes', c.despachos_clientes, ['Fecha','Despacho','Cliente','SKU','Cantidad'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td><code style="font-size:0.82em">'+_esc(it.numero_despacho||'')+'</code></td><td>'+_esc(it.cliente||'—')+'</td><td><code style="font-size:0.82em">'+_esc(it.sku||'')+'</code></td><td>'+_esc(it.cantidad||'')+'</td></tr>';
    });
    html += _repSeccion('📋 Desviaciones', c.desviaciones, ['Código','Fecha','Tipo','Clasificación','Estado'], function(it){
      return '<tr><td><code style="font-size:0.82em">'+_esc(it.codigo||'')+'</code></td><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td>'+_esc(it.tipo||'')+'</td><td>'+_esc(it.clasificacion||'—')+'</td><td>'+_esc(it.estado||'')+'</td></tr>';
    });
    html += _repSeccion('🚨 Recalls', c.recalls, ['Código','Fecha inicio','Producto','Clase','Estado'], function(it){
      return '<tr><td><code style="font-size:0.82em">'+_esc(it.codigo||'')+'</code></td><td>'+_esc((it.fecha_inicio||'').slice(0,10))+'</td><td>'+_esc(it.producto||'—')+'</td><td>'+_esc(it.clase_recall||'—')+'</td><td>'+_esc(it.estado||'')+'</td></tr>';
    });
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty">Error: '+_esc(e.message)+'</p>'; }
}

async function repClienteCargar(){
  var cid = document.getElementById('rep-cli-input').value.trim();
  if(!cid){ alert('Ingresa ID de cliente'); return; }
  var body = document.getElementById('rep-cli-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  try{
    var r = await fetch('/api/aseguramiento/reportes/cliente-trazabilidad/'+encodeURIComponent(cid));
    if(r.status === 403){ body.innerHTML = '<p class="empty">Acceso restringido a Calidad/Admin</p>'; return; }
    if(r.status === 404){ body.innerHTML = '<p class="empty">Cliente no encontrado</p>'; return; }
    var d = await r.json();
    var cli = d.cliente || {};
    var rsm = d.resumen || {};
    var html = '<div class="card" style="background:#f8fafc;border-left:4px solid #8b5cf6">'
      +'<div style="font-weight:700;font-size:1.05em;margin-bottom:6px">Cliente: '+_esc(cli.nombre||'')+'</div>'
      +'<div style="font-size:0.82em;color:#64748b;margin-bottom:8px">Código: <code>'+_esc(cli.codigo||'')+'</code> · Empresa: '+_esc(cli.empresa||'—')
      +(cli.email ? ' · '+_esc(cli.email) : '')
      +(cli.telefono ? ' · ☎ '+_esc(cli.telefono) : '')
      +' · Consultado por <b>'+_esc(d.consultado_por||'')+'</b></div>'
      +'<div>'
      +_repBadge(rsm.despachos, 'Despachos', '#0ea5e9')
      +_repBadge(rsm.pedidos, 'Pedidos', '#7ACFCC')
      +_repBadge(rsm.lotes_distintos, 'Lotes únicos', '#15803d')
      +'</div></div>';

    html += _repSeccion('🚚 Despachos al cliente', d.despachos, ['Fecha','Despacho','SKU','Descripción','Lote PT','Cantidad'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td><code style="font-size:0.82em">'+_esc(it.numero||'')+'</code></td><td><code style="font-size:0.82em">'+_esc(it.sku||'')+'</code></td><td>'+_esc((it.descripcion||'').slice(0,40))+'</td><td><code>'+_esc(it.lote_pt||'—')+'</code></td><td>'+_esc(it.cantidad||'')+'</td></tr>';
    });
    html += _repSeccion('📋 Pedidos', d.pedidos, ['Fecha','Pedido','Estado','Valor total'], function(it){
      return '<tr><td>'+_esc((it.fecha||'').slice(0,10))+'</td><td><code style="font-size:0.82em">'+_esc(it.numero||'')+'</code></td><td>'+_esc(it.estado||'')+'</td><td>'+_esc(it.valor_total||'')+'</td></tr>';
    });

    var lotes = d.lotes_unicos || [];
    if(lotes.length){
      html += '<div style="margin-top:14px"><div style="font-weight:600;margin-bottom:6px;color:#1e293b">📦 Lotes únicos recibidos ('+lotes.length+')</div>'
        +'<div style="display:flex;flex-wrap:wrap;gap:6px">'
        +lotes.map(function(l){ return '<code style="background:#f1f5f9;padding:3px 8px;border-radius:4px;font-size:0.82em">'+_esc(l)+'</code>'; }).join('')
        +'</div></div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty">Error: '+_esc(e.message)+'</p>'; }
}

async function loadConflictos(){
  var tb = document.getElementById('conf-tbody');
  try{
    var r = await fetch('/api/aseguramiento/sgd/conflictos');
    var d = await r.json();
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="5" class="empty">Sin conflictos detectados</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var btn = it.estado === 'pendiente'
        ? '<button class="btn btn-ghost btn-sm" onclick="resolverConf('+it.id+')">Marcar resuelto</button>'
        : '<span style="color:#94a3b8">'+_esc(it.estado)+'</span>';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.temas||'')+'</td>'
        +'<td>'+_esc(it.estado)+'</td>'
        +'<td>'+_esc(it.resolucion||'—')+'</td>'
        +'<td>'+btn+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="5" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function resolverConf(id){
  var resolucion = prompt('Describe cómo se resolvió (mín 10 chars):');
  if(!resolucion || resolucion.length < 10) return;
  try{
    var r = await fetch('/api/aseguramiento/sgd/conflictos/'+id+'/resolver', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({resolucion: resolucion})});
    var d = await r.json();
    if(d.ok){ loadConflictos(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

window.addEventListener('DOMContentLoaded', function(){ loadDashboard(); });
</script>
</body>
</html>'''
