# Auto-extraído de index.py — Fase A refactor
RRHH_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RRHH — HHA Group</title>
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
<header>
  <div class="header-top">
    <a href="/modulos" style="font-weight:700;">&#x1F4F1; M&#xF3;dulos</a>
    <h1>&#128101; Recursos Humanos &mdash; HHA Group</h1>
    <span class="user-chip">{usuario}</span>
  </div>
  <nav>
    <button class="tab active" id="t-dash" onclick="goTo('dash',this)">&#128202; Dashboard</button>
    <button class="tab" id="t-emp" onclick="goTo('emp',this)">&#128100; Empleados</button>
    <button class="tab" id="t-nom" onclick="goTo('nom',this)">&#128184; N&oacute;mina</button>
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

<!-- ═══ EMPLEADOS ═══ -->
<div id="emp" class="page">
  <div class="card-hd" style="margin-bottom:16px;">
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="text" id="emp-search" placeholder="Buscar empleado..." style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;min-width:220px;" oninput="filterEmps()">
      <select id="emp-filter-empresa" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todas las empresas</option>
        <option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option>
      </select>
      <select id="emp-filter-estado" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todos</option><option>Activo</option><option>Inactivo</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="openEmpModal(null)">+ Nuevo</button>
  </div>
  <div id="emp-grid" class="emp-grid"></div>
</div>

<!-- ═══ NÓMINA ═══ -->
<div id="nom" class="page">
  <div class="ctrl-bar">
    <select id="nom-mes">
      <option value="01">Enero</option><option value="02">Febrero</option>
      <option value="03">Marzo</option><option value="04">Abril</option>
      <option value="05">Mayo</option><option value="06">Junio</option>
      <option value="07">Julio</option><option value="08">Agosto</option>
      <option value="09">Septiembre</option><option value="10">Octubre</option>
      <option value="11">Noviembre</option><option value="12">Diciembre</option>
    </select>
    <select id="nom-anio"><option>2026</option><option>2025</option></select>
    <button class="btn btn-primary" onclick="loadNomina()">Calcular</button>
    <label class="btn" style="background:#7c3aed;color:#fff;cursor:pointer;margin-left:4px;" title="Importar Excel de nomina">&#128194; Importar Excel<input type="file" accept=".xlsx" style="display:none;" onchange="importarExcel(this)"></label>
    <button class="btn btn-success" onclick="guardarNomina()" style="margin-left:auto;">&#128190; Guardar</button>
    <button class="btn" id="btn-aprobar" style="display:none;background:#16a34a;color:#fff;" onclick="aprobarNomina()">&#10003; Aprobar</button>
    <button class="btn" onclick="exportarNomina()" style="background:#0284c7;color:#fff;" title="Descargar Excel">&#11015; Excel</button>
    <span id="nom-estado-badge" style="margin-left:8px;"></span>
  </div>
  <div class="card" style="overflow-x:auto;">
    <table id="nom-table">
      <thead><tr>
        <th>Empleado</th><th>Empresa</th><th>D&iacute;as</th>
        <th>Salario Base</th><th>Aux.Trans</th><th>H.Extras</th><th>Bonos</th>
        <th>-Salud(4%)</th><th>-Pens.(4%)</th><th>NETO</th><th></th>
      </tr></thead>
      <tbody id="nom-body"></tbody>
    </table>
  </div>
  <div class="nomina-summary" id="nom-summary" style="display:none;"></div>
  <div class="card" style="margin-top:16px;" id="nom-aportes" style="display:none;">
    <div class="card-hd"><h2>&#127968; Aportes Empleador (no deducidos del empleado)</h2></div>
    <div id="nom-aportes-body"></div>
  </div>
</div>

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
            <option>Gerencia</option><option>Operaciones</option><option>Control de Calidad</option>
            <option>Laboratorio</option><option>Planta</option><option>Administrativa</option>
            <option>Comercial</option><option>Log&iacute;stica</option>
          </select>
        </div>
        <div class="form-group"><label>Empresa</label>
          <select id="f-empresa"><option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option></select>
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
// ─── state ───────────────────────────────────────────
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
  else if (id==='nom') initNomina();
  else if (id==='aus') loadAusencias();
  else if (id==='cap') loadCapacitaciones();
  else if (id==='eva') loadEvaluaciones();
  else if (id==='sgsst') loadSgsst();
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
  var m={'Espagiria':'badge-esp','ANIMUS':'badge-ani','HHA Group':'badge-hha'};
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
  if (!list.length){g.innerHTML='<div class="empty-state">Sin empleados registrados.</div>';return;}
  g.innerHTML = list.map(function(e){
    var initials = (e.nombre||'?').charAt(0)+(e.apellido||'').charAt(0);
    var color = avatarColor(e.nombre+e.apellido);
    return '<div class="emp-card" onclick="openEmpModal('+e.id+')">' +
      '<div class="emp-avatar" style="background:'+color+';">'+initials+'</div>' +
      '<div class="emp-name">'+e.nombre+' '+e.apellido+'</div>' +
      '<div class="emp-cargo">'+e.cargo+'</div>' +
      '<div class="emp-meta">'+badgeEmpresa(e.empresa)+' '+badgeContrato(e.tipo_contrato)+
      ' <span class="badge '+(e.estado==='Activo'?'badge-activo':'badge-inactivo')+'">'+e.estado+'</span></div>' +
      '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#6d28d9;">'+fmt(e.salario_base)+'</div>' +
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
      document.getElementById('f-area').value = d.area||'Operaciones';
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
    } catch(e){console.error(e);}
  } else {
    fields.forEach(function(f){var el=document.getElementById('f-'+f);if(el)el.value='';});
    document.getElementById('f-empresa').value='Espagiria';
    document.getElementById('f-contrato').value='Indefinido';
    document.getElementById('f-area').value='Operaciones';
    document.getElementById('f-estado').value='Activo';
    document.getElementById('f-riesgo').value='1';
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
    observaciones: document.getElementById('f-obs').value.trim()
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
function initNomina(){
  var now = new Date();
  document.getElementById('nom-mes').value = String(now.getMonth()+1).padStart(2,'0');
  document.getElementById('nom-anio').value = String(now.getFullYear());
  window._esAdmin = (typeof USUARIO !== 'undefined' && (USUARIO==='Sebastian' || USUARIO==='Alejandro'));
  loadNomina();
  checkEstadoNomina();
}

async function loadNomina(){
  var mes = document.getElementById('nom-mes').value;
  var anio = document.getElementById('nom-anio').value;
  var periodo = anio+'-'+mes;
  try {
    nominaData = await fetch('/api/rrhh/nomina/'+periodo).then(function(r){return r.json();});
    renderNomina();
  } catch(e){console.error(e);}
}

function calcNeto(row){
  var base = parseFloat(row.salario_base)||0;
  var aux = parseFloat(row.aux_transporte)||0;
  var he = parseFloat(row.valor_horas_extras)||0;
  var bonos = parseFloat(row.bonificaciones)||0;
  var salud = Math.round(base*0.04);
  var pension = Math.round(base*0.04);
  var otros = parseFloat(row.otros_descuentos)||0;
  return base+aux+he+bonos-salud-pension-otros;
}

function renderNomina(){
  var tbody = document.getElementById('nom-body');
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
      '<td><strong>'+e.nombre+'</strong><br><small style="color:#78716c;">'+e.cargo+'</small></td>' +
      '<td>'+badgeEmpresa(e.empresa)+'</td>' +
      '<td><input type="number" value="'+e.dias_trabajados+'" min="0" max="31" style="width:60px;" onchange="nominaData['+i+'].dias_trabajados=this.value;renderNomina();"></td>' +
      '<td>'+fmt(e.salario_base)+'</td>' +
      '<td style="color:#16a34a;">'+fmt(e.aux_transporte)+'</td>' +
      '<td><input type="number" value="'+(e.valor_horas_extras||0)+'" min="0" step="10000" onchange="nominaData['+i+'].valor_horas_extras=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td><input type="number" value="'+(e.bonificaciones||0)+'" min="0" step="10000" onchange="nominaData['+i+'].bonificaciones=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td style="color:#dc2626;">-'+fmt(e.desc_salud)+'</td>' +
      '<td style="color:#dc2626;">-'+fmt(e.desc_pension)+'</td>' +
      '<td style="font-weight:700;color:#6d28d9;">'+fmt(neto)+'</td>' +
      '<td><button class="btn" style="padding:2px 8px;font-size:11px;" onclick="verComprobante('+e.id+')" title="Ver comprobante">&#128424;</button></td>' +
      '</tr>';
  }).join('');

  var s = document.getElementById('nom-summary');
  s.style.display='grid';
  s.innerHTML =
    '<div class="sum-item"><div class="sum-lbl">Total Devengado</div><div class="sum-val">'+fmt(totalBruto)+'</div></div>' +
    '<div class="sum-item red"><div class="sum-lbl">Total Deducciones</div><div class="sum-val">-'+fmt(totalDed)+'</div></div>' +
    '<div class="sum-item green"><div class="sum-lbl">Total Neto a Pagar</div><div class="sum-val">'+fmt(totalNeto)+'</div></div>' +
    '<div class="sum-item purple"><div class="sum-lbl">Aportes Empleador</div><div class="sum-val">'+fmt(aportesTot.total)+'</div></div>' +
    '<div class="sum-item purple"><div class="sum-lbl">Costo Total Empresa</div><div class="sum-val">'+fmt(totalBruto+aportesTot.total)+'</div></div>';

  var ap = document.getElementById('nom-aportes');
  ap.style.display='block';
  ap.querySelector('#nom-aportes-body').innerHTML =
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;">' +
    [['Salud (8.5%)',aportesTot.salud],['Pensi\u00f3n (12%)',aportesTot.pension],
     ['ARL',aportesTot.arl],['SENA (2%)',aportesTot.sena],
     ['ICBF (3%)',aportesTot.icbf],['Caja (4%)',aportesTot.caja],['TOTAL',aportesTot.total]].map(function(x){
      return '<div style="text-align:center;background:#f9f8f7;border-radius:8px;padding:10px;">' +
        '<div style="font-size:11px;color:#78716c;">'+x[0]+'</div>' +
        '<div style="font-size:16px;font-weight:700;color:'+(x[0]==='TOTAL'?'#6d28d9':'#1C1917')+';">'+fmt(x[1])+'</div></div>';
    }).join('') + '</div>';
}

async function guardarNomina(){
  var mes = document.getElementById('nom-mes').value;
  var anio = document.getElementById('nom-anio').value;
  var periodo = anio+'-'+mes;
  nominaData.forEach(function(e){e.neto=calcNeto(e);});
  try {
    var r = await fetch('/api/rrhh/nomina/guardar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({periodo:periodo,registros:nominaData})});
    var d = await r.json();
    if(d.ok){ alert('N\u00f3mina guardada: '+d.registros+' registros para '+periodo);
      checkEstadoNomina(); }
    else alert(d.error||'Error');
  } catch(e){alert('Error: '+e.message);}
}

async function checkEstadoNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value;
  var periodo=anio+'-'+mes;
  try{
    var res=await fetch('/api/rrhh/nomina/'+periodo).then(r=>r.json());
    var estados=res.map(e=>e.estado||'').filter(Boolean);
    var aprobadas=estados.filter(s=>s==='Aprobada').length;
    var badge=document.getElementById('nom-estado-badge');
    var btnAp=document.getElementById('btn-aprobar');
    if(aprobadas>0 && aprobadas===estados.length){
      badge.innerHTML='<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#10003; Aprobada</span>';
      if(btnAp) btnAp.style.display='none';
    } else if(estados.length>0){
      badge.innerHTML='<span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;">Pendiente aprobaci\u00f3n</span>';
      if(btnAp && window._esAdmin) btnAp.style.display='inline-block';
    } else { badge.innerHTML=''; }
  } catch(e){}
}

async function aprobarNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value;
  var periodo=anio+'-'+mes;
  if(!confirm('\u00bfAprobar n\u00f3mina '+periodo+'? Esta acci\u00f3n quedar\u00e1 registrada.')) return;
  try{
    var r=await fetch('/api/rrhh/nomina/'+periodo+'/aprobar',{method:'PATCH'});
    var d=await r.json();
    if(d.ok) { alert('\u2713 N\u00f3mina '+periodo+' aprobada por '+d.por+' ('+d.aprobados+' registros)'); checkEstadoNomina(); }
    else alert(d.error||'Sin permiso');
  } catch(e){alert('Error: '+e.message);}
}

function verComprobante(empId){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value;
  var periodo=anio+'-'+mes;
  window.open('/api/rrhh/nomina/'+periodo+'/comprobante/'+empId,'_blank','width=700,height=900');
}

function exportarNomina(){
  var mes=document.getElementById('nom-mes').value, anio=document.getElementById('nom-anio').value;
  window.location.href='/api/rrhh/nomina/'+anio+'-'+mes+'/export';
}

async function importarExcel(input){
  var file=input.files[0]; if(!file) return;
  var fd=new FormData(); fd.append('file',file);
  try{
    var r=await fetch('/api/rrhh/nomina/importar-excel',{method:'POST',body:fd});
    var d=await r.json();
    if(!d.ok){ alert(d.error||'Error al importar'); return; }
    var matched=d.data||[];
    matched.forEach(function(row){
      var idx=nominaData.findIndex(function(e){return e.id===row.empleado_id;});
      if(idx>=0) nominaData[idx].dias_trabajados=row.dias_trabajados;
    });
    renderNomina();
    alert('\u2713 Importado: '+matched.length+' empleados de '+d.total_excel+' en el Excel ('+
          (d.total_excel-matched.length)+' no coincidieron). Revisa y guarda.');
  } catch(e){alert('Error: '+e.message);}
  input.value='';
}

// ─── AUSENCIAS ───────────────────────────────────────
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
  await fetch('/api/rrhh/ausencias/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:estado})});
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
    await fetch('/api/rrhh/ausencias',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
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
    await fetch('/api/rrhh/capacitaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
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
    await fetch('/api/rrhh/evaluaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
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
  await fetch('/api/rrhh/sgsst/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Cumplido'})});
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
    await fetch('/api/rrhh/sgsst',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
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
